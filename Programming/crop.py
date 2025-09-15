#!/usr/bin/env python3
"""
================================================================================================
Image Cropper and Converter
================================================================================================

This script is a command-line utility for batch processing images. Its primary function
is to resize and center-crop images to a target resolution of 1920x1080 pixels. It also
serves as a powerful image format converter and can add customizable borders.

------------------------------------------------------------------------------------------------
Features
------------------------------------------------------------------------------------------------

- **Fixed Aspect Ratio Cropping**: Automatically resizes and center-crops images to
  a 16:9 aspect ratio (1920x1080).
- **Customizable Borders**: Add a colored border with adjustable thickness, perfect for
  framing images for thumbnails.
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
- webcolors: For validating CSS color names.

------------------------------------------------------------------------------------------------
Installation
------------------------------------------------------------------------------------------------

Before running the script, ensure you have Python 3 installed. Then, install the
required libraries using pip:

.. code-block:: sh

   pip install Pillow pillow-avif-plugin webcolors

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

- `-b, --border [COLOR] [WIDTH]`:
  Add a border. If used without arguments (`-b`), applies a default border.
  - `COLOR`: A CSS color name (e.g., 'red', 'steelblue') or hex code ('#333').
  - `WIDTH`: A border width in pixels.
  - Default (if only '-b' is used): red, 20px.
  - Default (if only COLOR is given): 20px width.

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

7.  **Add a border to an image:**
    - Apply the default border (red, 20px):
      `python crop_images.py -b my_photo.jpg`
    - Apply a slateblue border with the default width (20px):
      `python crop_images.py -b slateblue my_photo.jpg`
    - Apply a 30px thick white border:
      `python crop_images.py -b "#FFFFFF" 30 my_photo.jpg`

------------------------------------------------------------------------------------------------
Developer's Guide & Changelog
------------------------------------------------------------------------------------------------

**INSTRUCTION FOR FUTURE DEVELOPMENT:**
This script should be self-documenting. Any developer who modifies this script MUST
update this documentation in the same commit. Updates should include:
1.  Adding the new feature/fix to the 'Features' list.
2.  Updating 'Dependencies' and 'Installation' if new packages are added.
3.  Adding/modifying 'Options' and 'Usage Examples'.
4.  Adding a new entry to the 'Changelog' below, explaining WHAT was changed and
    WHY the specific design decisions were made.

---

**v1.3 (2025-09-15): Made Border Flag Even Smarter**
- **Change:** The logic for detecting misplaced filenames passed to the `-b` flag was
  enhanced. It now checks all arguments passed to `-b`, not just the first one.
- **Reasoning:**
  - **Primary Goal:** To further improve user experience and handle more complex
    command-line errors gracefully. The previous logic failed in cases like
    `crop.py -b yellow my_photo.jpg`, where the filename was the second
    argument to the flag.
  - **Implementation:** The logic was rewritten to iterate through all items provided
    to `--border`. Each item is checked to see if it has a supported file
    extension. If it does, it's moved to the file processing list; otherwise,
    it's kept as a valid border argument (color or width). This makes the order
    of color, width, and filename after the `-b` flag completely flexible.

**v1.2 (2025-09-14): Made Border Flag Smarter**
- **Change:** Added logic to detect if a filename was mistakenly passed as a parameter
  to the `-b` flag. The script now correctly interprets `crop.py -b my_photo.jpg` as
  applying a default border to `my_photo.jpg`.
- **Reasoning:**
  - **Primary Goal:** Improve user experience and prevent common command-line errors.
    Users unfamiliar with strict argument order were frequently causing errors by
    placing the filename after an option.
  - **Implementation:** After parsing arguments, a new block checks if the value
    passed to `--border` has a supported image extension. If so, it is moved from
    the `border` argument list to the `files` list. This is a robust and simple
    way to correct the user's input without a complex parser rewrite.

**v1.1 (2025-09-14): Added Image Border Functionality**

- **Change:** Implemented a `-b, --border` flag to add a colored border to images.
- **Reasoning:**
  - **Primary Goal:** The feature was requested to add a visible frame around images,
    specifically for use cases like YouTube thumbnails where a border helps the
    image stand out in a crowded feed.
  - **Flag Design (`-b [COLOR] [WIDTH]`):** The flag was designed for maximum
    flexibility. Using `nargs='*'` allows the user to simply type `-b` to get a
    sensible default, or to specify a custom color and/or width. This is more
    user-friendly than requiring multiple separate flags.
  - **Default Choice (red, 20px):** The default color 'red' was chosen for its high
    visibility and contrast. The default width of 20 pixels was chosen specifically
    so the border remains clearly visible even when the 1920x1080 image is scaled
    down to a small thumbnail size.
  - **Technology (`webcolors` package):** The `webcolors` library was explicitly added
    to the project dependencies to provide robust validation of user-supplied color
    names against the standard CSS3 color list, preventing errors from typos or
    unsupported color names.

================================================================================================
"""

import argparse
import os
import sys
from pathlib import Path
from PIL import Image, ImageOps, UnidentifiedImageError
import glob # For handling '*' if passed as an argument
import pillow_avif  # Registers the AVIF plugin with Pillow
import webcolors # For validating color names

# --- Constants ---
TARGET_WIDTH = 1920
TARGET_HEIGHT = 1080
SUPPORTED_INPUT_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.avif')
DEFAULT_OUTPUT_FORMAT = 'jpg'
DEFAULT_QUALITY = 85
DEFAULT_SUFFIX = '_cropped'
DEFAULT_OUTPUT_SUBFOLDER = 'cropped_output'
DEFAULT_BORDER_WIDTH = 60
DEFAULT_BORDER_COLOR = 'red'

# Handle Pillow Resampling filter name change
try:
    RESAMPLING_FILTER = Image.Resampling.LANCZOS
except AttributeError:
    RESAMPLING_FILTER = Image.LANCZOS  # For older Pillow versions

# --- Helper Functions ---

def validate_color_string(color_str: str) -> bool:
    """Uses webcolors to validate a color name or hex string."""
    try:
        # webcolors functions will raise an exception if the format is invalid.
        if color_str.startswith('#'):
            webcolors.hex_to_rgb(color_str)
        else:
            webcolors.name_to_rgb(color_str.lower())
        return True
    except (ValueError, KeyError):
        # ValueError for bad hex/rgb, KeyError for unknown name
        return False

def process_image(input_image_path_str: str, output_dir_path_obj: Path,
                  output_format_str: str, quality_int: int, suffix_str: str,
                  border_color_str: str, border_width_int: int) -> bool:
    """
    Processes a single image: loads, orients, crops, adds a border, and saves it.
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

    # 3. Add border if a color was specified
    image_to_process = cropped_img
    if border_color_str:
        try:
            print(f"  Info: Adding a {border_width_int}px border ({border_color_str}).")
            image_to_process = ImageOps.expand(
                image_to_process,
                border=border_width_int,
                fill=border_color_str
            )
        except Exception as e:
            print(f"  Warning: Could not add border: {e}. (Is '{border_color_str}' a valid color?)")

    # 4. Prepare for saving: Handle image mode and save options
    image_to_save = image_to_process
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

    # 5. Determine output path and filename
    original_stem = input_path.stem
    output_filename = f"{original_stem}{suffix_str}.{output_extension}"

    try:
        output_dir_path_obj.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"  Error: Could not create output directory {output_dir_path_obj}: {e}")
        return False
    output_full_path = output_dir_path_obj / output_filename

    # 6. Save the image
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
    parser.add_argument(
        '-b', '--border',
        nargs='*',
        metavar=('COLOR', 'WIDTH'),
        help="Add a border. If used without arguments, applies the default border.\n"
             "COLOR: A CSS color name (e.g., 'red', 'steelblue') or hex code ('#333').\n"
             "WIDTH: A border width in pixels.\n"
             f"Default (if only '-b' is used): {DEFAULT_BORDER_COLOR} {DEFAULT_BORDER_WIDTH}px\n"
             f"Default (if only COLOR is given): {DEFAULT_BORDER_WIDTH}px"
    )

    args = parser.parse_args()

    # ========================================================================
    # NEW LOGIC BLOCK TO HANDLE MISPLACED FILENAMES (v1.3)
    # This makes the script even "smarter" about the -b flag.
    # ========================================================================
    if args.border is not None:
        actual_border_args = []
        # Iterate over all items passed to --border.
        # Any item that looks like a supported filename will be moved to the
        # main file list. Anything else is assumed to be a border argument.
        for item in args.border:
            if Path(item).suffix.lower() in SUPPORTED_INPUT_EXTENSIONS:
                print(f"Info: Detected filename '{item}' passed to '-b' flag. Treating it as an input file.")
                # It's a file! Add it to the list of files to process.
                args.files.append(item)
            else:
                # It's not a filename, so it must be a real border argument (color/width).
                actual_border_args.append(item)
        
        # Replace the original border list with the cleaned one, which now only
        # contains actual border arguments.
        args.border = actual_border_args
    # ========================================================================
    # END OF NEW LOGIC BLOCK
    # ========================================================================

    # --- Process Border Arguments ---
    border_color_to_use = None
    border_width_to_use = DEFAULT_BORDER_WIDTH

    # This condition checks if the -b flag was used at all
    if args.border is not None:
        if len(args.border) == 0:
            # Case: `crop.py -b my_photo.jpg` (after our new logic block runs)
            # OR `crop.py my_photo.jpg -b`
            print(f"Info: Border flag used. Applying default border ({DEFAULT_BORDER_COLOR}, {DEFAULT_BORDER_WIDTH}px).")
            border_color_to_use = DEFAULT_BORDER_COLOR
            # width is already set to default
        
        elif len(args.border) >= 1:
            # Case: `crop.py -b <color> [width]`
            user_color = args.border[0]
            if not validate_color_string(user_color):
                print(f"Error: Invalid border color '{user_color}'. Must be a CSS name or hex code.", file=sys.stderr)
                sys.exit(1)
            border_color_to_use = user_color
            
            if len(args.border) > 1:
                try:
                    border_width_to_use = int(args.border[1])
                except ValueError:
                    print(f"Error: Invalid border width '{args.border[1]}'. Must be a number.", file=sys.stderr)
                    sys.exit(1)
        
        if len(args.border) > 2:
            print(f"Warning: Ignoring extra border arguments: {args.border[2:]}", file=sys.stderr)


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
        if process_image(img_path_str, output_dir_path, args.output_format, args.quality, args.suffix,
                         border_color_to_use, border_width_to_use):
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