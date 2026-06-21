import numpy as np
import colour
import argparse
import os
import warnings

# Suppress warnings
from colour.utilities import ColourUsageWarning
warnings.filterwarnings("ignore", category=ColourUsageWarning)
os.environ["OPENCV_IO_ENABLE_OPENEXR"] = "1"

from colour_checker_detection import detect_colour_checkers_segmentation


def get_correction_parameters(chart_image_path):
    print(f"Processing reference image: {chart_image_path}")

    if not os.path.exists(chart_image_path):
        raise FileNotFoundError(f"Could not find the file: {chart_image_path}")

    img = colour.io.read_image(chart_image_path)
    print("Searching for ColorChecker in image...")
    checkers = detect_colour_checkers_segmentation(img)

    if not checkers:
        raise ValueError(
            "Could not detect a ColorChecker. Make sure the chart fills a good "
            "portion of the frame and is well-lit."
        )

    extracted_swatches = checkers[0]

    # Convert swatches to linear light for mathematically accurate scaling
    extracted_swatches_linear = colour.cctf_decoding(extracted_swatches)
    print(f"Successfully extracted {len(extracted_swatches_linear)} swatches.")

    # ---------------------------------------------------------------
    # FIX 1: Identify white/black by luminance instead of hardcoded
    # indices.  The detection library's patch ordering depends on how
    # the chart is oriented in the photo, so index 23 / 18 are ONLY
    # correct when the chart is perfectly upright.  Your scan is
    # rotated 180°, which swapped them onto colour patches → gain
    # of 870 000 and a black output image.
    # ---------------------------------------------------------------
    luminances = extracted_swatches_linear.mean(axis=1)  # per-patch mean brightness

    white_idx = int(np.argmax(luminances))
    black_idx = int(np.argmin(luminances))
    white_patch = extracted_swatches_linear[white_idx]
    black_patch = extracted_swatches_linear[black_idx]

    print(f"  White patch → index {white_idx}, linear RGB {np.round(white_patch, 4)}")
    print(f"  Black patch → index {black_idx}, linear RGB {np.round(black_patch, 4)}")

    # Sanity check: the two patches must be meaningfully different
    delta = (white_patch - black_patch).mean()
    if delta < 0.05:
        raise ValueError(
            f"White and black patches are too similar (mean delta = {delta:.4f}). "
            "The ColorChecker may not have been detected correctly, or the image "
            "is severely underexposed. Check that the chart is clearly visible."
        )

    # Target values in linear sRGB
    target_white = np.array([0.90, 0.90, 0.90])
    target_black = np.array([0.03, 0.03, 0.03])

    # Lift/Gain (per-channel offset + multiplier)
    denominator = np.maximum(white_patch - black_patch, 1e-6)
    gain = (target_white - target_black) / denominator
    offset = target_black - (black_patch * gain)

    return gain, offset


def apply_correction(target_image_path, output_path, gain, offset):
    print(f"Applying correction to: {target_image_path}")

    if not os.path.exists(target_image_path):
        raise FileNotFoundError(f"Could not find target image: {target_image_path}")

    target_img = colour.io.read_image(target_image_path)          # float32 [0, 1]
    target_img_linear = colour.cctf_decoding(target_img)          # linearise

    corrected_linear = target_img_linear * gain + offset
    corrected_linear = np.clip(corrected_linear, 0.0, 1.0)

    corrected_img = colour.cctf_encoding(corrected_linear)        # back to sRGB gamma

    # ---------------------------------------------------------------
    # FIX 2: write_image expects float [0, 1], NOT uint8 [0, 255].
    # Passing uint8 previously produced the corrupted blue/magenta
    # output because the values (0-255) were interpreted as floats
    # and then clipped / mangled by the encoder.
    # ---------------------------------------------------------------
    colour.io.write_image(corrected_img, output_path)
    print(f"Saved corrected image to: {output_path}")


# ==========================================
# Command Line Interface
# ==========================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract White/Black balance from a ColorChecker and apply it."
    )
    parser.add_argument("chart", help="Path to the image containing the ColorChecker")
    parser.add_argument(
        "--target",
        help="Path to another image to apply the correction to",
        default=None,
    )
    parser.add_argument(
        "--output",
        help="Path to save the corrected image",
        default="corrected.jpg",
    )

    args = parser.parse_args()

    try:
        gain, offset = get_correction_parameters(args.chart)

        print("\n--- Calculated Correction Parameters ---")
        print(f"RGB Gain Multipliers : {np.round(gain, 4)}")
        print(f"RGB Black Offsets    : {np.round(offset, 4)}")
        print("----------------------------------------\n")

        if args.target:
            apply_correction(args.target, args.output, gain, offset)
        else:
            print("No --target provided. Applying correction to the chart image as a test...")
            apply_correction(args.chart, args.output, gain, offset)

    except Exception as e:
        print(f"\n[ERROR] {e}")