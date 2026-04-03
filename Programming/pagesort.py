# ==============================================================================
#
#                                Page Content Sorter
#
# ==============================================================================
#
# Author: Gemini
# Version: 3.4 (Fully Exposed Configuration)
#
# ------------------------------------------------------------------------------
#
# --- PURPOSE ---
#
# This script automatically identifies the content of scanned pages and sorts
# them into three categories:
#
#   1. Text   : Contain text (main book content).
#   2. Images : Contain illustrations, photos, or diagrams (no text).
#   3. Blanks : Contain neither (just noise, paper texture, or dust).
#
# Files are moved into a `sorted/` subdirectory with `text`, `images`, and `blanks` folders.
#
# ==============================================================================
# --- CONFIGURATION / PARAMETERS ---
# ==============================================================================

# --- 1. PREPROCESSING ---
# Kernel size for denoising (removing salt-and-pepper noise).
# Larger = more denoising but might lose fine detail.
MORPH_KERNEL_NOISE = (3, 3)

# --- 2. TEXT DETECTION ---
# Kernel to smear letters into words/lines.
# (Width, Height). Increase Width to connect letters further apart.
MORPH_KERNEL_TEXT_CONNECT = (25, 5)

# Filters for valid text "lines".
# A contour must meet ALL these criteria to be counted as a text line.
# Values are RELATIVE to image size to support various resolutions.
FACTOR_TEXT_MIN_WIDTH = 0.005  # 2.5% of Image Width (Increased from 1.5%)
FACTOR_TEXT_MIN_HEIGHT = 0.001  # 0.6% of Image Height (Increased from 0.3%)
TEXT_MIN_ASPECT_RATIO = 2.5  # Width / Height (Lines must be wide)
# Area factor roughly corresponds to a box of (min_w * min_h) * 0.8
FACTOR_TEXT_MIN_AREA_SCALE = 0.8

# --- 3. IMAGE DETECTION ---
# Canny Edge Detection thresholds.
CANNY_LOW = 30
CANNY_HIGH = 150

# Minimum area for a contour to count towards "Image Content".
# Ignores small dust specks.
IMAGE_CONTOUR_MIN_AREA = 100

# --- 4. CLASSIFICATION THRESHOLDS ---
# Profile-driven thresholds so we can tune per collection without changing
# existing behavior.
THRESHOLD_PROFILES = {
    # Existing behavior (kept as-is for backward compatibility).
    "duotone": {
        "blank_text_max": 1,
        "blank_image_max": 5000,
        "text_present_min": 2,
        "blank_std_max": 10.0,
        "text_strong_min": 20,
        "image_strong_min": 120000,
        "image_largest_min": 350000,
        "image_area_ratio_min": 0.18,
        "image_edge_density_min": 0.03,
        # Only allow edge-density path to force image on low-text pages.
        "image_text_guard_max": 10**9,
        "blank_largest_max": 60000,
        "blank_image_ratio_max": 0.02,
        "blank_edge_density_max": 0.02,
        "blank_text_soft_max": 35,
        "both_text_min": 100,
        "both_image_ratio_min": 0.13,
        "both_largest_min": 800000,
    },
    # Tuned for the next old-book set where many text pages have strong structure.
    "photoscan": {
        "blank_text_max": 1,
        "blank_image_max": 5000,
        "text_present_min": 2,
        "blank_std_max": 10.0,
        "text_strong_min": 20,
        "image_strong_min": 120000,
        "image_largest_min": 2400000,
        # Effectively disable ratio-only image detection for this profile.
        "image_area_ratio_min": 0.60,
        "image_edge_density_min": 0.033,
        "image_text_guard_max": 200,
        "blank_largest_max": 60000,
        "blank_image_ratio_max": 0.02,
        "blank_edge_density_max": 0.02,
        "blank_text_soft_max": 35,
        "both_text_min": 100,
        "both_image_ratio_min": 0.13,
        "both_largest_min": 800000,
    },
}

# ==============================================================================

import argparse
import glob
import os
import shutil
import sys

import cv2
import numpy as np
from PIL import Image

# Metadata tags we might care about
META_TAGS = ["dpi", "format", "mode"]


class Logger(object):
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log = open(filename, "w", encoding="utf-8")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)

    def flush(self):
        self.terminal.flush()
        self.log.flush()


def classify_page_content(image_path, params, verbose=True):
    """
    Analyzes an image to determine if it contains Text, Images, or is Blank.

    Returns:
        dict: classification metrics and results
    """
    try:
        # Read image safely (handle unicode paths)
        with open(image_path, "rb") as f:
            chunk = np.frombuffer(f.read(), dtype=np.uint8)
        img = cv2.imdecode(chunk, cv2.IMREAD_COLOR)

        if img is None:
            if verbose:
                print(f"    - Warning: Could not decode {os.path.basename(image_path)}")
            return None

        # 1. Preprocessing
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Optional StdDev Check
        std_val = 0.0
        if params.get("std_threshold") is not None:
            (mean, std) = cv2.meanStdDev(gray)
            std_val = std[0][0]

            if std_val < params["std_threshold"]:
                if verbose:
                    print(
                        f"      -> METRICS: StdDev={std_val:.2f} < {params['std_threshold']} (Fast Blank)"
                    )
                return {
                    "has_text": False,
                    "has_image": False,
                    "text_lines": 0,
                    "image_area": 0,
                    "std": std_val,
                }

        cfg = params["thresholds"]

        # Denoise
        kernel_noise = cv2.getStructuringElement(cv2.MORPH_RECT, MORPH_KERNEL_NOISE)
        denoised = cv2.morphologyEx(gray, cv2.MORPH_OPEN, kernel_noise)

        # ----------------------------------------------------------------------
        # DETECT TEXT LINES
        # ----------------------------------------------------------------------
        gradX = cv2.Sobel(denoised, ddepth=cv2.CV_32F, dx=1, dy=0, ksize=-1)
        gradX = np.absolute(gradX)
        (minVal, maxVal) = (np.min(gradX), np.max(gradX))

        if maxVal - minVal > 0:
            gradX = (255 * ((gradX - minVal) / (maxVal - minVal))).astype("uint8")
        else:
            gradX = np.zeros_like(gradX, dtype="uint8")

        _, thresh_text = cv2.threshold(
            gradX, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU
        )

        kernel_text_connect = cv2.getStructuringElement(
            cv2.MORPH_RECT, MORPH_KERNEL_TEXT_CONNECT
        )
        connected_text = cv2.morphologyEx(
            thresh_text, cv2.MORPH_CLOSE, kernel_text_connect
        )

        cnts_text, _ = cv2.findContours(
            connected_text.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        text_lines_found = 0
        total_text_area = 0

        # Calculate Thresholds
        h_img, w_img = img.shape[:2]

        if params.get("width_px") and params.get("height_px"):
            thresh_min_w = params["width_px"]
            thresh_min_h = params["height_px"]
            mode_desc = "Fixed Pixels"
        else:
            thresh_min_w = int(w_img * params["width_pct"])
            thresh_min_h = int(h_img * params["height_pct"])
            mode_desc = f"Dynamic ({params['width_pct'] * 100:.2f}%W, {params['height_pct'] * 100:.2f}%H)"

        thresh_min_area = int(thresh_min_w * thresh_min_h * FACTOR_TEXT_MIN_AREA_SCALE)

        # Safety clamp to avoid 0
        thresh_min_w = max(thresh_min_w, 5)
        thresh_min_h = max(thresh_min_h, 2)
        thresh_min_area = max(thresh_min_area, 10)

        if verbose:
            print(
                f"      -> Text Detection ({mode_desc}): W>{thresh_min_w}px, H>{thresh_min_h}px, Area>{thresh_min_area}px"
            )

        for c in cnts_text:
            (x, y, w, h) = cv2.boundingRect(c)
            if h > 0:
                aspect_ratio = w / float(h)
            else:
                aspect_ratio = 0
            area = cv2.contourArea(c)

            # Text Filter
            if (
                w > thresh_min_w
                and h > thresh_min_h
                and aspect_ratio > TEXT_MIN_ASPECT_RATIO
                and area > thresh_min_area
            ):
                text_lines_found += 1
                total_text_area += area

        # Secondary text pass for old-book pages with weak contrast:
        # adaptive thresholding recovers text missed by Sobel-only logic.
        adaptive = cv2.adaptiveThreshold(
            denoised,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            35,
            15,
        )
        adaptive_connected = cv2.morphologyEx(
            adaptive,
            cv2.MORPH_CLOSE,
            cv2.getStructuringElement(cv2.MORPH_RECT, (17, 3)),
        )
        cnts_text_adaptive, _ = cv2.findContours(
            adaptive_connected.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        adaptive_text_lines = 0
        for c in cnts_text_adaptive:
            (x, y, w, h) = cv2.boundingRect(c)
            if h <= 0:
                continue
            aspect_ratio = w / float(h)
            area = cv2.contourArea(c)
            if (
                w > thresh_min_w
                and h > thresh_min_h
                and aspect_ratio > 1.8
                and area > int(thresh_min_area * 0.8)
            ):
                adaptive_text_lines += 1

        text_lines_found = max(text_lines_found, adaptive_text_lines)

        if verbose:
            print(
                f"      -> METRIC: Text Lines Found: {text_lines_found} (Adaptive: {adaptive_text_lines})"
            )

        # ----------------------------------------------------------------------
        # DETECT IMAGE CONTENT
        # ----------------------------------------------------------------------
        edges = cv2.Canny(denoised, CANNY_LOW, CANNY_HIGH)

        kernel_edge_connect = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        closed_edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel_edge_connect)

        cnts_img, _ = cv2.findContours(
            closed_edges.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        image_content_area = 0
        largest_contour_area = 0

        for c in cnts_img:
            area = cv2.contourArea(c)
            if area > IMAGE_CONTOUR_MIN_AREA:
                image_content_area += area
                if area > largest_contour_area:
                    largest_contour_area = area

        edge_density = float(np.count_nonzero(edges)) / float(h_img * w_img)
        image_area_ratio = float(image_content_area) / float(h_img * w_img)

        # Compute structure metrics used by conservative blank/image decisions.

        if verbose:
            print(
                f"      -> METRIC: Image Content Area: {image_content_area} (Largest: {largest_contour_area}, Ratio: {image_area_ratio:.4f}, EdgeDensity: {edge_density:.4f})"
            )

        # ----------------------------------------------------------------------
        # DECISION LOGIC
        # ----------------------------------------------------------------------

        # ----------------------------------------------------------------------
        # DECISION LOGIC
        # ----------------------------------------------------------------------

        has_text = text_lines_found >= cfg["text_present_min"]

        # Image detection: require strong, coherent image structure.
        has_image = (
            largest_contour_area >= cfg["image_largest_min"]
            and (
                image_area_ratio >= cfg["image_area_ratio_min"]
                or (
                    edge_density >= cfg["image_edge_density_min"]
                    and text_lines_found <= cfg["image_text_guard_max"]
                )
            )
        )

        is_blank = (
            largest_contour_area <= cfg["blank_largest_max"]
            and image_area_ratio <= cfg["blank_image_ratio_max"]
            and edge_density <= cfg["blank_edge_density_max"]
            and text_lines_found <= cfg["blank_text_soft_max"]
        )

        if is_blank:
            has_text = False
            has_image = False

        result = {
            "has_text": has_text,
            "has_image": has_image,
            "text_lines": text_lines_found,
            "image_area": image_content_area,
            "image_area_ratio": image_area_ratio,
            "largest_contour_area": largest_contour_area,
            "edge_density": edge_density,
            "is_blank": is_blank,
            "std": std_val,
        }

        if verbose:
            print(
                f"      -> METRICS: Text={has_text} ({text_lines_found}), Image={has_image} (Area={image_content_area}, Largest={largest_contour_area}, Ratio={image_area_ratio:.4f}, EdgeDensity={edge_density:.4f}), Blank={is_blank}, StdDev={std_val:.2f}"
            )

        return result

    except Exception as e:
        print(f"    - Error analyzing {os.path.basename(image_path)}: {e}")
        return None


def process_images(target_dir, params, verbose=True):
    cfg = params["thresholds"]
    image_extensions = ("*.png", "*.jpg", "*.jpeg", "*.tif", "*.tiff", "*.bmp")
    image_files = []

    abs_target = os.path.abspath(target_dir)
    print(f"Searching in: {abs_target}\n")

    if verbose:
        print("--- CURRENT CONFIGURATION ---")
        print(f"  Profile            = {params.get('profile', 'photoscan')}")
        if params.get("width_px"):
            print(f"  MODE               = Fixed Thresholds")
            print(f"  Width Requirement  = {params['width_px']} px")
            print(f"  Height Requirement = {params['height_px']} px")
        else:
            print(f"  MODE               = Dynamic Thresholds")
            print(f"  Width Factor       = {params['width_pct'] * 100:.2f}%")
            print(f"  Height Factor      = {params['height_pct'] * 100:.2f}%")

        if params.get("std_threshold"):
            print(
                f"  StdDev Blank Check = Enabled (Threshold: {params['std_threshold']})"
            )
        else:
            print(f"  StdDev Blank Check = Disabled")

        print(f"  TH_BLANK_TEXT_MAX   = {cfg['blank_text_max']}")
        print(f"  TH_TEXT_PRESENT_MIN = {cfg['text_present_min']}")
        print(f"  TH_IMAGE_LARGEST_MIN = {cfg['image_largest_min']}")
        print(f"  TH_IMAGE_AREA_RATIO_MIN = {cfg['image_area_ratio_min']}")
        print(f"  TH_IMAGE_EDGE_DENSITY_MIN = {cfg['image_edge_density_min']}")
        print(f"  TH_IMAGE_TEXT_GUARD_MAX = {cfg['image_text_guard_max']}")
        print(f"  TH_BLANK_LARGEST_MAX = {cfg['blank_largest_max']}")
        print(f"  TH_BLANK_IMAGE_RATIO_MAX = {cfg['blank_image_ratio_max']}")
        print(f"  TH_BLANK_EDGE_DENSITY_MAX = {cfg['blank_edge_density_max']}")
        print(f"  TH_BLANK_TEXT_SOFT_MAX = {cfg['blank_text_soft_max']}")
        print(f"  TH_BOTH_TEXT_MIN = {cfg['both_text_min']}")
        print(f"  TH_BOTH_IMAGE_RATIO_MIN = {cfg['both_image_ratio_min']}")
        print(f"  TH_BOTH_LARGEST_MIN = {cfg['both_largest_min']}")
        print("-" * 30 + "\n")

    for ext in image_extensions:
        image_files.extend(
            glob.glob(os.path.join(abs_target, "**", ext), recursive=True)
        )

    if not image_files:
        print("No images found.")
        return

    print(f"Found {len(image_files)} images.\n")

    # Stats
    stats = {"text": 0, "images": 0, "blanks": 0, "both": 0, "error": 0, "skipped": 0}

    # Setup Sorted Folders
    sorted_root = os.path.join(abs_target, "sorted")
    dirs = {
        "text": os.path.join(sorted_root, "text"),
        "images": os.path.join(sorted_root, "images"),
        "blanks": os.path.join(sorted_root, "blanks"),
    }

    # Create them if they don't exist
    for d in dirs.values():
        os.makedirs(d, exist_ok=True)

    for image_path in image_files:
        # Skip files already in 'sorted' to avoid double-processing if re-run
        if "sorted" in image_path.split(os.sep):
            continue

        if verbose:
            print("-" * 40)
            print(f"    [Diagnostics] Analyzing: {os.path.basename(image_path)}")
            # Detailed Metadata Extraction
            try:
                with Image.open(image_path) as pil_img:
                    w, h = pil_img.size
                    fmt = pil_img.format
                    mode = pil_img.mode
                    dpi = pil_img.info.get("dpi", ("Unknown", "Unknown"))
                    print(
                        f"      -> Metadata: {fmt} {mode}, {w}x{h} ({(w * h) / 1e6:.1f} MP), DPI: {dpi}"
                    )
            except Exception as e:
                print(f"      -> Metadata: Error reading metadata ({e})")
        else:
            print(f"Processing: {os.path.basename(image_path)}")

        analysis = classify_page_content(image_path, params, verbose=verbose)

        if analysis is None:
            stats["error"] += 1
            continue

        has_text = analysis["has_text"]
        has_image = analysis["has_image"]

        try:
            # Logic:
            # 1. Blank
            # 2. Both (Copy to Image, Move to Text)
            # 3. Image Only (Move to Image)
            # 4. Text Only (Move to Pages)

            if analysis.get("is_blank"):
                # BLANK (structural override)
                dest = dirs["blanks"]
                shutil.move(image_path, dest)
                if verbose:
                    print(f"      -> Action: Moved to sorted/blanks")
                stats["blanks"] += 1

            elif has_text and has_image:
                # BOTH only when both text and image are clearly substantial.
                strong_image_for_both = (
                    analysis.get("image_area_ratio", 0.0) >= cfg["both_image_ratio_min"]
                    or analysis.get("largest_contour_area", 0.0) >= cfg["both_largest_min"]
                )
                if analysis["text_lines"] >= cfg["both_text_min"] and strong_image_for_both:
                    shutil.copy2(image_path, dirs["images"])
                    if verbose:
                        print(f"      -> Action: Copied to sorted/images")

                    shutil.move(image_path, dirs["text"])
                    if verbose:
                        print(f"      -> Action: Moved to sorted/text")
                    stats["both"] += 1
                elif analysis["text_lines"] >= cfg["both_text_min"]:
                    dest = dirs["text"]
                    shutil.move(image_path, dest)
                    if verbose:
                        print(f"      -> Action: Moved to sorted/text")
                    stats["text"] += 1
                else:
                    dest = dirs["images"]
                    shutil.move(image_path, dest)
                    if verbose:
                        print(f"      -> Action: Moved to sorted/images")
                    stats["images"] += 1

            elif has_image:
                dest = dirs["images"]
                shutil.move(image_path, dest)
                if verbose:
                    print(f"      -> Action: Moved to sorted/images")
                stats["images"] += 1

            elif has_text:
                dest = dirs["text"]
                shutil.move(image_path, dest)
                if verbose:
                    print(f"      -> Action: Moved to sorted/text")
                stats["text"] += 1

            else:
                dest = dirs["blanks"]
                shutil.move(image_path, dest)
                if verbose:
                    print(f"      -> Action: Moved to sorted/blanks")
                stats["blanks"] += 1

        except Exception as e:
            print(f"    -> Error processing file: {e}")
            stats["error"] += 1

        if not verbose:
            print("")

    print("=" * 30)
    print("Sorting Complete Check 'sorted/' folder.")
    print(f"  Text Only         : {stats['text']}")
    print(f"  Images Only       : {stats['images']}")
    print(f"  Both (Split)      : {stats['both']}")
    print(f"  Blanks            : {stats['blanks']}")
    print("=" * 30)


def main():
    parser = argparse.ArgumentParser(
        description="Sorts scanned pages into Text, Images, and Blanks."
    )
    parser.add_argument(
        "target_directory", nargs="?", default=os.getcwd(), help="Directory to process"
    )
    parser.add_argument(
        "-q", "--quiet", action="store_true", help="Disable verbose diagnostic output"
    )
    parser.add_argument(
        "-r",
        "--report",
        action="store_true",
        default=False,
        help="Save console output to pagesort_report.txt",
    )

    # New Configurable Parameters
    parser.add_argument(
        "--std",
        type=float,
        nargs="?",
        const=10.0,
        default=None,
        help="Enable StdDev blank check. Optional: set custom threshold (default: 10.0)",
    )
    parser.add_argument(
        "--wp",
        "--width-pct",
        type=float,
        default=0.015,
        help="Text detection width percentage (default: 0.015 / 1.5%%)",
    )
    parser.add_argument(
        "--hp",
        "--height-pct",
        type=float,
        default=0.005,
        help="Text detection height percentage (default: 0.005 / 0.5%%)",
    )
    parser.add_argument(
        "--wx", "--width-px", type=int, help="Override width with fixed pixels"
    )
    parser.add_argument(
        "--hx", "--height-px", type=int, help="Override height with fixed pixels"
    )
    parser.add_argument(
        "--profile",
        choices=sorted(THRESHOLD_PROFILES.keys()),
        default="photoscan",
        help="Threshold profile. Use 'duotone' for previous behavior, 'photoscan' for stricter image gating.",
    )

    args = parser.parse_args()

    if not os.path.isdir(args.target_directory):
        print("Invalid directory.")
        return

    # Package params for clean passing
    thresholds = THRESHOLD_PROFILES[args.profile].copy()
    params = {
        "std_threshold": args.std,
        "width_pct": args.wp,
        "height_pct": args.hp,
        "width_px": args.wx,
        "height_px": args.hx,
        "profile": args.profile,
        "thresholds": thresholds,
    }

    if args.report:
        report_path = os.path.join(args.target_directory, "pagesort_report.txt")
        sys.stdout = Logger(report_path)
        print(f"--- REPORT STARTED: {report_path} ---")

    try:
        process_images(args.target_directory, params, verbose=not args.quiet)
    finally:
        # Restore stdout just in case, though script is ending
        if args.report:
            sys.stdout = sys.__stdout__


if __name__ == "__main__":
    main()
