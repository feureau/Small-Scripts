#!/usr/bin/env python3
import os
import sys
import subprocess
import glob
import argparse

# Try to import tqdm for a progress bar; if not available, proceed without it.
try:
    from tqdm import tqdm
    has_tqdm = True
except ImportError:
    has_tqdm = False

def main():
    parser = argparse.ArgumentParser(
        description="Crop transparent borders from images using ImageMagick."
    )
    parser.add_argument(
        "images",
        nargs="+",
        help="Input image file(s) or wildcard patterns (e.g., '*.png')"
    )
    parser.add_argument(
        "-f", "--fuzz",
        help="Transparency threshold as a percentage (e.g., 10 or 10%% for 10 percent). Defaults to 30%%.",
        default="30"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output directory. Default is 'TranspCrop'.",
        default="TranspCrop"
    )
    args = parser.parse_args()

    # Expand wildcard patterns into a list of filenames
    files = []
    for pattern in args.images:
        expanded = glob.glob(pattern)
        if expanded:
            files.extend(expanded)
        else:
            print(f"No files found for pattern: {pattern}")
    if not files:
        sys.exit("No files to process.")

    # Create output directory in the current working directory
    output_folder = os.path.join(os.getcwd(), args.output)
    os.makedirs(output_folder, exist_ok=True)

    # Prepare fuzz option; ensure it ends with '%'
    fuzz = args.fuzz
    if not fuzz.endswith('%'):
        fuzz += '%'

    # Set up progress indicator if tqdm is available
    if has_tqdm:
        iterator = tqdm(files, desc="Processing images")
    else:
        iterator = files

    for image in iterator:
        if not os.path.isfile(image):
            print(f"File not found: {image}")
            continue

        # Construct output file path
        output_image = os.path.join(output_folder, os.path.basename(image))

        # Build the command using ImageMagick's magick command.
        cmd = ["magick", image, "-fuzz", fuzz, "-trim", "+repage", output_image]

        try:
            subprocess.run(cmd, check=True)
            print(f"Processed {image} -> {output_image}")
        except subprocess.CalledProcessError as e:
            print(f"Error processing {image}: {e}")

if __name__ == "__main__":
    main()
