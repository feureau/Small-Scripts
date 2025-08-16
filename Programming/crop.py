#!/usr/bin/env python3
"""
================================================================================================
Image Cropper and Converter
================================================================================================

This script is a command-line utility for batch processing images. Its primary function
is to resize and center-crop images to a target resolution of 1920x1080 pixels. It also
serves as a powerful image format converter.

------------------------------------------------------------------------------------------------
Features
------------------------------------------------------------------------------------------------

- **Fixed Aspect Ratio Cropping**: Automatically resizes and center-crops images to
  a 16:9 aspect ratio (1920x1080).
- **Batch Processing**: Process multiple files at once using glob patterns (e.g., "*.jpg")
  or by scanning the current directory for all supported images.
- **EXIF Orientation Correction**: Automatically reads EXIF metadata from photos to
  correct their orientation before cropping.
- **Format Conversion**: Supports a wide range of input and output formats.
  - **Input**: JPG, JPEG, PNG, GIF, BMP, TIFF, WEBP, AVIF.
  - **Output**: JPG, JPEG, PNG, WEBP, TIFF, BMP, AVIF.
- **Quality Control**: Allows specifying the output quality for lossy formats like
  JPEG, WebP, and AVIF.
- **Transparency Handling**: Intelligently handles transparent images. When converting a
  PNG with transparency to JPEG, it adds a solid white background.
- **Flexible File Naming**: Saves processed files to a specified output directory
  (defaults to './cropped_output') and appends a customizable suffix (defaults to '_cropped').
- **High-Quality Resampling**: Uses the Lanczos resampling filter, which provides
  excellent detail retention when resizing images.

------------------------------------------------------------------------------------------------
Dependencies
------------------------------------------------------------------------------------------------

- Python 3.6+
- Pillow (Python Imaging Library fork): For core image processing.
- pillow-avif-plugin: To enable support for the AVIF image format.

------------------------------------------------------------------------------------------------
Installation
------------------------------------------------------------------------------------------------

Before running the script, ensure you have Python 3 installed. Then, install the
required libraries using pip:

.. code-block:: sh

   pip install Pillow pillow-avif-plugin

------------------------------------------------------------------------------------------------
How to Use (Command-Line Usage)
------------------------------------------------------------------------------------------------

Save the script as a Python file (e.g., `crop_images.py`) and run it from your terminal.

**Syntax:**

.. code-block:: sh

   python crop_images.py [FILES_OR_PATTERNS...] [OPTIONS]

**Arguments:**

- `FILE_OR_PATTERN` (Positional):
  One or more file paths or glob patterns.
  - If omitted, the script scans the current working directory for all supported image types.
  - Patterns like `*.jpg` or `images/*.png` should be quoted to prevent the shell
    from expanding them first.

**Options:**

- `-f, --output-format <format>`:
  The format for the output images.
  Choices: `jpg`, `jpeg`, `png`, `webp`, `tiff`, `bmp`, `avif`.
  Default: `jpg`.

- `-q, --quality <Q>`:
  The compression quality for JPEG, WebP, or AVIF formats (1-100).
  Higher values mean better quality and larger file sizes.
  Note: Pillow caps JPEG quality at 95.
  Default: `85`.

- `-o, --output-dir <path>`:
  The directory where the processed images will be saved.
  It will be created if it does not exist.
  Default: `./cropped_output` (a new folder in the current directory).

- `-s, --suffix <suffix>`:
  A string to append to the original filename (before the new extension).
  To keep the original name, use an empty string: `-s ""`.
  Default: `_cropped`.

------------------------------------------------------------------------------------------------
Usage Examples
------------------------------------------------------------------------------------------------

1.  **Crop a single image:**
    `python crop_images.py my_photo.png`
    (Saves `my_photo_cropped.jpg` in `./cropped_output`)

2.  **Crop all JPG and PNG files in the current directory:**
    `python crop_images.py "*.jpg" "*.png"`

3.  **Process all supported images in the current directory (no input files specified):**
    `python crop_images.py`

4.  **Convert an AVIF file to a high-quality WebP:**
    `python crop_images.py -f webp -q 95 my_image.avif`
    (Saves `my_image_cropped.webp`)

5.  **Process all images in a subdirectory and save them to a different folder:**
    `python crop_images.py "source_images/*.jpg" -o "processed_images"`

6.  **Keep the original filename but change the format:**
    `python crop_images.py -s "" -f png my_picture.jpg`
    (Saves `my_picture.png` in `./cropped_output`)

================================================================================================
"""

import argparse
import os
import sys
from pathlib import Path
from PIL import Image, ImageOps, UnidentifiedImageError
import glob # For handling '*' if passed as an argument
import pillow_avif  # Registers the AVIF plugin with Pillow

# --- Constants ---
TARGET_WIDTH = 1920
TARGET_HEIGHT = 1080
SUPPORTED_INPUT_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.avif')
DEFAULT_OUTPUT_FORMAT = 'jpg'
DEFAULT_QUALITY = 85
DEFAULT_SUFFIX = '_cropped'
DEFAULT_OUTPUT_SUBFOLDER = 'cropped_output'

# Handle Pillow Resampling filter name change
try:
    RESAMPLING_FILTER = Image.Resampling.LANCZOS
except AttributeError:
    RESAMPLING_FILTER = Image.LANCZOS  # For older Pillow versions

# --- Helper Function: Process a single image ---
def process_image(input_image_path_str: str, output_dir_path_obj: Path,
                  output_format_str: str, quality_int: int, suffix_str: str) -> bool:
    """
    Processes a single image: loads, orients, crops, and saves it.
    Returns True on success, False on failure.
    """
    input_path = Path(input_image_path_str)
    print(f"Processing: {input_path}...")

    try:
        img = Image.open(input_path)
    except FileNotFoundError:
        print(f"  Error: File not found: {input_path}")
        return False
    except UnidentifiedImageError:
        print(f"  Error: Cannot identify image file (is it a valid image?): {input_path}")
        return False
    except Exception as e:
        print(f"  Error: Could not open image {input_path}: {e}")
        return False

    # 1. Fix orientation based on EXIF data (if any)
    try:
        img = ImageOps.exif_transpose(img)
    except Exception as e:
        print(f"  Warning: Could not apply EXIF transpose for {input_path}: {e}")

    # 2. Crop to target dimensions (1920x1080)
    try:
        cropped_img = ImageOps.fit(img, (TARGET_WIDTH, TARGET_HEIGHT), RESAMPLING_FILTER)
    except Exception as e:
        print(f"  Error: Could not crop image {input_path}: {e}")
        return False

    # 3. Prepare for saving: Handle image mode and save options
    image_to_save = cropped_img
    save_options = {}

    pillow_format_name = output_format_str.upper()
    output_extension = output_format_str.lower()
    if pillow_format_name == 'JPG':
        pillow_format_name = 'JPEG'
    if output_extension == 'jpeg':
        output_extension = 'jpg'

    if pillow_format_name == 'JPEG':
        current_quality = min(max(1, quality_int), 95)
        save_options['quality'] = current_quality
        save_options['optimize'] = True
        save_options['progressive'] = True
    elif pillow_format_name in ('WEBP', 'AVIF'):
        current_quality = min(max(1, quality_int), 100)
        save_options['quality'] = current_quality
    elif pillow_format_name == 'PNG':
        save_options['optimize'] = True

    # Handle transparency for formats that don't support it (like JPEG)
    if pillow_format_name == 'JPEG':
        if image_to_save.mode in ('RGBA', 'LA') or \
           (image_to_save.mode == 'P' and 'transparency' in image_to_save.info):
            background = Image.new("RGB", image_to_save.size, (255, 255, 255))
            image_with_alpha = image_to_save.convert("RGBA")
            background.paste(image_with_alpha, mask=image_with_alpha.split()[-1])
            image_to_save = background
            print(f"  Info: Converted transparent image to RGB with white background for JPEG output.")
        elif image_to_save.mode != 'RGB':
            image_to_save = image_to_save.convert('RGB')
            print(f"  Info: Converted image mode {img.mode} to RGB for JPEG output.")
    else: # For PNG, WEBP, AVIF, etc.
        if image_to_save.mode == 'P' and image_to_save.info.get('transparency') is not None:
            image_to_save = image_to_save.convert('RGBA')
            print(f"  Info: Converted paletted image with transparency to RGBA for {pillow_format_name} output.")
        elif image_to_save.mode == 'LA' and pillow_format_name in ('WEBP', 'TIFF', 'AVIF'):
             image_to_save = image_to_save.convert('RGBA')
             print(f"  Info: Converted LA image to RGBA for {pillow_format_name} output.")

    # 4. Determine output path and filename
    original_stem = input_path.stem
    output_filename = f"{original_stem}{suffix_str}.{output_extension}"

    try:
        output_dir_path_obj.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"  Error: Could not create output directory {output_dir_path_obj}: {e}")
        return False
    output_full_path = output_dir_path_obj / output_filename

    # 5. Save the image
    try:
        image_to_save.save(str(output_full_path), format=pillow_format_name, **save_options)
        print(f"  Successfully cropped and saved: {output_full_path}")
        return True
    except Exception as e:
        print(f"  Error: Could not save image {output_full_path} as {pillow_format_name}: {e}")
        return False

# --- Main Function ---
def main():
    """
    Parses command-line arguments, finds images to process, and calls the
    processing function for each image.
    """
    parser = argparse.ArgumentParser(
        description=f"Crop images to {TARGET_WIDTH}x{TARGET_HEIGHT}. Scales and center-crops to fit.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        'files',
        metavar='FILE_OR_PATTERN',
        nargs='*',
        help='One or more image files or a glob pattern (e.g., "*.avif").\nIf no files are specified, scans the current directory for all supported image types.'
    )
    parser.add_argument(
        '-f', '--output-format',
        type=str.lower,
        default=DEFAULT_OUTPUT_FORMAT,
        choices=['jpg', 'jpeg', 'png', 'webp', 'tiff', 'bmp', 'avif'],
        help=f"Output image format. Default: {DEFAULT_OUTPUT_FORMAT}"
    )
    parser.add_argument(
        '-q', '--quality',
        type=int,
        default=DEFAULT_QUALITY,
        metavar='Q',
        help=f"Output quality for JPEG/WEBP/AVIF (1-100).\nJPEG quality is effectively capped at 95 by Pillow.\nDefault: {DEFAULT_QUALITY}"
    )
    parser.add_argument(
        '-o', '--output-dir',
        type=str,
        default=DEFAULT_OUTPUT_SUBFOLDER,
        help=f"Directory to save cropped images.\nDefault: ./{DEFAULT_OUTPUT_SUBFOLDER} (a subfolder in the current working directory).\nDirectory will be created if it doesn't exist."
    )
    parser.add_argument(
        '-s', '--suffix',
        type=str,
        default=DEFAULT_SUFFIX,
        help=f"Suffix for cropped filenames (before extension).\nDefault: '{DEFAULT_SUFFIX}'.\nSet to an empty string (e.g., -s \"\") to keep original name (with new extension)."
    )

    args = parser.parse_args()

    # Resolve output directory path
    if args.output_dir == DEFAULT_OUTPUT_SUBFOLDER or not Path(args.output_dir).is_absolute():
        output_dir_path = Path(os.getcwd()) / args.output_dir
    else:
        output_dir_path = Path(args.output_dir)

    # Determine list of image files to process
    image_files_to_process = []
    if args.files:
        for file_or_pattern_str in args.files:
            if '*' in file_or_pattern_str or '?' in file_or_pattern_str:
                glob_path = Path(os.getcwd()) / file_or_pattern_str
                found_files = glob.glob(str(glob_path))
                if not found_files:
                    print(f"Warning: Glob pattern '{file_or_pattern_str}' (resolved to '{glob_path}') did not match any files.", file=sys.stderr)
                for f_str in found_files:
                    f_path = Path(f_str)
                    if f_path.is_file() and f_path.suffix.lower() in SUPPORTED_INPUT_EXTENSIONS:
                        image_files_to_process.append(str(f_path))
                    else:
                        print(f"Warning: File from glob '{f_path}' does not have a supported extension. Skipping.", file=sys.stderr)
            else: # Treat as a single file path
                f_path = Path(file_or_pattern_str)
                if not f_path.is_absolute():
                    f_path = Path(os.getcwd()) / f_path

                if not f_path.is_file():
                    print(f"Warning: Specified file not found or is not a file: {f_path}", file=sys.stderr)
                elif f_path.suffix.lower() not in SUPPORTED_INPUT_EXTENSIONS:
                    print(f"Warning: Specified file '{f_path}' does not have a supported extension. Will attempt to process if it's a valid image.", file=sys.stderr)
                    image_files_to_process.append(str(f_path))
                else:
                    image_files_to_process.append(str(f_path))
    else: # No files or patterns given, scan CWD
        print(f"No files specified. Scanning current directory ({os.getcwd()}) for images...")
        for item in Path(os.getcwd()).iterdir():
            if item.is_file() and item.suffix.lower() in SUPPORTED_INPUT_EXTENSIONS:
                image_files_to_process.append(str(item))
        if not image_files_to_process:
            print("No image files found in the current directory.")
            sys.exit(0)

    image_files_to_process = sorted(list(set(image_files_to_process)))

    if not image_files_to_process:
        print("No valid image files to process.", file=sys.stderr)
        sys.exit(1)

    print(f"\nFound {len(image_files_to_process)} image(s) to process.")
    print(f"Output will be saved to: {output_dir_path}\n")

    processed_count = 0
    error_count = 0

    for img_path_str in image_files_to_process:
        if process_image(img_path_str, output_dir_path, args.output_format, args.quality, args.suffix):
            processed_count += 1
        else:
            error_count += 1
        print("-" * 20)

    print("\n--- Summary ---")
    print(f"Successfully processed: {processed_count} image(s)")
    print(f"Errors encountered:   {error_count} image(s)")

    if error_count > 0:
        sys.exit(1)

# --- Entry Point ---
if __name__ == "__main__":
    main()