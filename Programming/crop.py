#!/usr/bin/env python3

import argparse
import os
import sys
from pathlib import Path
from PIL import Image, ImageOps, UnidentifiedImageError
import glob # For handling '*' if passed as an argument

# --- Constants ---
TARGET_WIDTH = 1920
TARGET_HEIGHT = 1080
SUPPORTED_INPUT_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp')
DEFAULT_OUTPUT_FORMAT = 'jpg'
DEFAULT_QUALITY = 85
DEFAULT_SUFFIX = '_cropped'
DEFAULT_OUTPUT_SUBFOLDER = 'cropped_output' # New default subfolder name

# Handle Pillow Resampling filter name change
try:
    RESAMPLING_FILTER = Image.Resampling.LANCZOS
except AttributeError:
    RESAMPLING_FILTER = Image.LANCZOS  # For older Pillow versions

# --- Helper Function: Process a single image ---
def process_image(input_image_path_str: str, output_dir_path_obj: Path, # Now expects a Path object
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
    elif pillow_format_name == 'WEBP':
        current_quality = min(max(1, quality_int), 100)
        save_options['quality'] = current_quality
    elif pillow_format_name == 'PNG':
        save_options['optimize'] = True

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
    else:
        if image_to_save.mode == 'P' and image_to_save.info.get('transparency') is not None:
            image_to_save = image_to_save.convert('RGBA')
            print(f"  Info: Converted paletted image with transparency to RGBA for {pillow_format_name} output.")
        elif image_to_save.mode == 'LA' and pillow_format_name in ('WEBP', 'TIFF'):
             image_to_save = image_to_save.convert('RGBA')
             print(f"  Info: Converted LA image to RGBA for {pillow_format_name} output.")

    # 4. Determine output path and filename
    original_stem = input_path.stem
    output_filename = f"{original_stem}{suffix_str}.{output_extension}"

    # Create output directory if it doesn't exist (now mandatory path)
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
    parser = argparse.ArgumentParser(
        description=f"Crop images to {TARGET_WIDTH}x{TARGET_HEIGHT}. Scales and center-crops to fit.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        'files',
        metavar='FILE_OR_PATTERN', # Updated metavar
        nargs='*',
        help='One or more image files or a glob pattern (e.g., "*.jpg").\nIf no files are specified, scans the current directory for all supported image types.'
    )
    parser.add_argument(
        '-f', '--output-format',
        type=str.lower,
        default=DEFAULT_OUTPUT_FORMAT,
        choices=['jpg', 'jpeg', 'png', 'webp', 'tiff', 'bmp'],
        help=f"Output image format. Default: {DEFAULT_OUTPUT_FORMAT}"
    )
    parser.add_argument(
        '-q', '--quality',
        type=int,
        default=DEFAULT_QUALITY,
        metavar='Q',
        help=f"Output quality for JPEG/WEBP (1-100).\nJPEG quality is effectively capped at 95 by Pillow.\nDefault: {DEFAULT_QUALITY}"
    )
    parser.add_argument(
        '-o', '--output-dir',
        type=str,
        # Default is now a subfolder in the CWD.
        # We'll resolve this to an absolute path later.
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

    # Resolve output directory to an absolute path relative to CWD if it's the default
    # or if a relative path was given.
    if args.output_dir == DEFAULT_OUTPUT_SUBFOLDER or not Path(args.output_dir).is_absolute():
        output_dir_path = Path(os.getcwd()) / args.output_dir
    else:
        output_dir_path = Path(args.output_dir)


    # Determine list of image files to process
    image_files_to_process = []
    if args.files:
        for file_or_pattern_str in args.files:
            # Check if it's a glob pattern (especially for Windows where shell might not expand)
            # A simple check: if it contains '*' or '?' it's likely a pattern
            if '*' in file_or_pattern_str or '?' in file_or_pattern_str:
                # Perform globbing relative to the CWD
                # Note: glob.glob returns paths relative to CWD if pattern is relative
                glob_path = Path(os.getcwd()) / file_or_pattern_str
                found_files = glob.glob(str(glob_path))
                if not found_files:
                    print(f"Warning: Glob pattern '{file_or_pattern_str}' (resolved to '{glob_path}') did not match any files.", file=sys.stderr)
                for f_str in found_files:
                    f_path = Path(f_str)
                    if f_path.is_file():
                        if f_path.suffix.lower() in SUPPORTED_INPUT_EXTENSIONS:
                            image_files_to_process.append(str(f_path))
                        else:
                            print(f"Warning: File from glob '{f_path}' does not have a supported extension. Skipping.", file=sys.stderr)
                    # else: it's a directory found by glob, ignore
            else: # Treat as a single file path
                f_path = Path(file_or_pattern_str)
                # If it's a relative path, make it absolute from CWD
                if not f_path.is_absolute():
                    f_path = Path(os.getcwd()) / f_path

                if not f_path.is_file():
                    print(f"Warning: Specified file not found or is not a file: {f_path}", file=sys.stderr)
                elif f_path.suffix.lower() not in SUPPORTED_INPUT_EXTENSIONS:
                    print(f"Warning: Specified file '{f_path}' does not have a supported extension. Will attempt to process if it's a valid image.", file=sys.stderr)
                    image_files_to_process.append(str(f_path)) # Add anyway, let Pillow try
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

    # Remove duplicates that might arise from mixed explicit paths and globs
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