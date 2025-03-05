#!/usr/bin/env python3
import os
import sys
import subprocess
import glob

def main():
    if len(sys.argv) < 2:
        print("Usage: croptransp.py <image1.png> <image2.png> ...")
        sys.exit(1)

    # Expand wildcard patterns into a list of filenames
    files = []
    for pattern in sys.argv[1:]:
        expanded = glob.glob(pattern)
        if expanded:
            files.extend(expanded)
        else:
            print(f"No files found for pattern: {pattern}")

    if not files:
        sys.exit("No files to process.")

    # Create output subfolder in the current working directory
    working_folder = os.getcwd()
    output_folder = os.path.join(working_folder, "TranspCrop")
    os.makedirs(output_folder, exist_ok=True)

    for image in files:
        if not os.path.isfile(image):
            print(f"File not found: {image}")
            continue

        # Use ImageMagick's mogrify to trim the transparent borders
        cmd = ["magick", "mogrify", "-trim", "+repage", "-path", output_folder, image]
        try:
            subprocess.run(cmd, check=True)
            print(f"Processed {image}")
        except subprocess.CalledProcessError as e:
            print(f"Error processing {image}: {e}")

if __name__ == "__main__":
    main()
