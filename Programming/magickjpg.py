"""###############################################################################
Image Conversion Script - GIMP/XCF/RAW/JPG Batch Converter
-------------------------------------------------------------------------------
Version: 2.0.0 (2025-09-22)
Author: Feureau + ChatGPT

PURPOSE:
    This script batch-converts images of many types (including GIMP 3 `.xcf` files)
    into `.jpg` files, using ImageMagick 7's `magick` CLI tool.

    It is designed to:
        • Handle GIMP `.xcf` files by automatically flattening with a white background.
        • Convert PSD, PSB, PNG with alpha, PDF, SVG, RAW, HDR, and more.
        • Output results to a dedicated `jpg/` subfolder, leaving originals untouched.
        • Allow quality, density, interlacing, profile stripping, resizing, etc.

IMPORTANT:
    ▸ This documentation MUST be kept at the top of the file and updated with every
      future revision. Include update history, rationale for changes, and reasoning.

DEPENDENCIES:
    ▸ Python 3.x
    ▸ ImageMagick 7.x (must be available in PATH as `magick`)
    ▸ Delegates for RAW (dcraw/libraw) if RAW support is needed.

USAGE:
    python convert_to_jpg.py [-q 85] [-d 300] [-i plane] [-s] [-r 1920x1080] \
                             [--profile sRGB.icc] [pattern]

ARGUMENTS:
    pattern: optional glob pattern (defaults to all supported image types)
    -q / --quality: JPEG quality (1–100)
    -d / --density: Density for vector formats (PDF/SVG)
    -i / --interlace: Interlace mode (none, line, plane, partition)
    -s / --strip: Strip metadata (EXIF, profiles)
    -r / --resize: Resize to WxH or percentage (e.g. 50%)
    --sampling-factor: e.g. 4:2:0
    --profile: Path to ICC color profile to apply

SUPPORTED INPUT FORMATS:
    Web & Standard: PNG, JPEG, JPG, WEBP, BMP, TIFF, GIF
    Editable: XCF, PSD, PSB, ORA (flattened)
    Vector: SVG, EPS, PDF (first page rasterized)
    Camera RAW: CR2, CR3, NEF, ARW, RW2, DNG, RAF, SRW, ORF, KDC, PEF, IIQ
    HDR: EXR, HDR

WHY WE USE `magick input output` INSTEAD OF `mogrify`:
    • `mogrify` overwrites originals — not safe for destructive batch jobs.
    • This approach lets us control per-file output path (to `jpg/` folder).
    • Ensures flattening works per file (needed for XCF/PSD with transparency).

HISTORY:
-------------------------------------------------------------------------------
2025-09-22 (v2.0.0):
    ▸ Full rewrite by ChatGPT per Feureau request.
    ▸ Added `.xcf` support and automatic flattening.
    ▸ Switched from `mogrify` to `magick input output` style for safety.
    ▸ Added expanded format list (RAW, HDR, vector).
    ▸ Added detailed documentation block with history + rationale.
"""

import argparse
import glob
import os
import subprocess
import sys

# Supported input formats (extensions must be lowercase)
SUPPORTED_EXTENSIONS = [
    '.png', '.jpeg', '.jpg', '.webp', '.bmp', '.tiff', '.tif', '.gif',
    '.heic', '.heif', '.psd', '.psb', '.xcf', '.ora',
    '.svg', '.eps', '.pdf',
    '.cr2', '.cr3', '.nef', '.arw', '.rw2', '.dng', '.raf', '.srw', '.orf', '.kdc', '.pef', '.iiq',
    '.exr', '.hdr'
]

def main():
    parser = argparse.ArgumentParser(description="Convert images to JPG using ImageMagick")
    parser.add_argument("pattern", nargs="?", help="Glob pattern for input files (default: all supported types)")
    parser.add_argument("-q", "--quality", type=int, help="JPEG quality (1-100)")
    parser.add_argument("-d", "--density", type=int, help="Density (DPI) for vector formats")
    parser.add_argument("-i", "--interlace", choices=["none", "line", "plane", "partition"], help="JPEG interlace mode")
    parser.add_argument("-s", "--strip", action="store_true", help="Strip metadata and profiles")
    parser.add_argument("-r", "--resize", help="Resize geometry (e.g. 1920x1080, 50%%)")
    parser.add_argument("--sampling-factor", help="Chroma subsampling factor (e.g. 4:2:0)")
    parser.add_argument("--profile", help="Path to ICC color profile")
    args = parser.parse_args()

    # Build file list
    if args.pattern:
        input_files = glob.glob(args.pattern)
    else:
        input_files = []
        for ext in SUPPORTED_EXTENSIONS:
            input_files.extend(glob.glob(f"*{ext}"))

    if not input_files:
        print("No matching input files found.")
        sys.exit(1)

    jpg_folder_path = os.path.join(os.getcwd(), "jpg")
    os.makedirs(jpg_folder_path, exist_ok=True)

    for input_file in input_files:
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        output_file = os.path.join(jpg_folder_path, f"{base_name}.jpg")

        magick_command = ["magick", input_file]

        if args.quality is not None:
            magick_command.extend(["-quality", str(args.quality)])

        # Always flatten with white background (safe for alpha, xcf, psd)
        magick_command.extend(["-background", "white", "-flatten"])

        if args.sampling_factor:
            magick_command.extend(["-sampling-factor", args.sampling_factor])
        if args.density:
            magick_command.extend(["-density", str(args.density)])
        if args.interlace:
            magick_command.extend(["-interlace", args.interlace])
        if args.strip:
            magick_command.append("-strip")
        if args.profile:
            magick_command.extend(["-profile", args.profile])
        if args.resize:
            magick_command.extend(["-resize", args.resize])

        magick_command.append(output_file)

        print(f"Converting: {input_file} → {output_file}")
        try:
            subprocess.run(magick_command, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error converting {input_file}: {e}")

if __name__ == "__main__":
    main()