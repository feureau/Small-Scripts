"""
magickrotate.py - GPU-Accelerated Image Rotation Script

A Python script for batch rotating images using ImageMagick with GPU acceleration support.
Processes multiple images in parallel, supporting rotation/flip transforms and glob patterns.

Features:
- GPU acceleration via ImageMagick's OpenCL support (if available)
- Parallel processing using multiple CPU cores
- Supports glob patterns (e.g., *.jpg, image*)
- Optional recursive file search through subfolder tree
- Custom rotation angles (positive: clockwise, negative: counterclockwise)
- Optional horizontal/vertical flipping
- Automatic output directory creation
- Graceful handling of Ctrl-C interruption
- Compatible with common image formats (JPG, PNG, GIF, BMP, TIFF, WebP, SVG, HEIC)

Requirements:
- Python 3.6+
- ImageMagick installed with OpenCL support (check with `magick -version | find "OpenCL"`)
- For GPU acceleration: NVIDIA/AMD GPU with OpenCL drivers

Usage:
    python magickrotate.py INPUT [INPUT ...] (-o OUTPUT_DIR | -w/--overwrite) [options]
    python magickrotate.py -i INPUT [INPUT ...] (-o OUTPUT_DIR | -w/--overwrite) [options]

Arguments:
    -d, --degree FLOAT       Rotation angle in degrees (optional)
    -H, --flip-horizontal    Flip image horizontally (mirror)
    -V, --flip-vertical      Flip image vertically
    INPUT                     Positional input image files/patterns (supports globs)
    -i, --inputs PATTERN      Optional flagged input files/patterns (supports globs)
    -r, --recursive          Search subfolders recursively for matching inputs
    -o, --output-dir DIR     Output directory for rotated images
    -w, --overwrite          Overwrite input files in place (no suffix/folder)
    -p, --parallel INT       Number of parallel processes (default: CPU cores)

Examples:
    # Rotate all JPG files in current dir by 90 degrees clockwise (positional)
    python magickrotate.py *.jpg -d 90 -o rotated

    # Equivalent using -i/--inputs
    python magickrotate.py -i *.jpg -d 90 -o rotated

    # Rotate multiple files by 45 degrees counterclockwise with 4 processes
    python magickrotate.py -i image1.png image2.jpg -d -45 -H -o output -p 4

    # Use glob for all images in subdir
    python magickrotate.py -i "subdir/*" -d 180 -o rotated

    # Recursively process all JPG files under a folder tree
    python magickrotate.py -i "photos/**/*.jpg" -r -H -o flipped

    # Rotate files in place (overwrite originals)
    python magickrotate.py -i *.png -d 90 -w

    # Flip vertically without rotation
    python magickrotate.py -i *.png -V -o flipped

Output:
    By default, transformed images are saved with a suffix based on selected operations
    (e.g., photo_rotated_90_fliph.jpg) in the specified output directory.
    With --overwrite, input files are replaced in place with no suffix/folder changes.
    Progress messages are printed for each completed image.

Notes:
    - GPU acceleration is enabled automatically if OpenCL is available.
    - Press Ctrl-C to cancel processing gracefully.
    - Invalid files or unsupported formats are skipped with error messages.
    - For every update to this script, the full documentation block at the top must be included and updated to reflect changes.
"""

import argparse
import concurrent.futures
import glob
import os
import subprocess
import tempfile

# Enable OpenCL GPU acceleration for ImageMagick if available
os.environ['MAGICK_OCL_DEVICE'] = 'true'


class FullHelpArgumentParser(argparse.ArgumentParser):
    """ArgumentParser variant that prints full help on errors."""
    def error(self, message):
        self.print_help()
        self.exit(2, f"\nError: {message}\n")

def process_file(input_file, degree=None, flip_horizontal=False, flip_vertical=False, output_dir=None, overwrite=False):
    """Process a single image file: apply transforms and save."""
    if not os.path.isfile(input_file):
        return f"Error: Input file '{input_file}' does not exist."

    temp_file = None
    try:
        ops = []
        if degree is not None:
            ops.extend(['-rotate', str(degree)])
        if flip_horizontal:
            ops.append('-flop')
        if flip_vertical:
            ops.append('-flip')

        op_label_parts = []
        if degree is not None:
            angle_str = str(degree).replace('.0', '') if str(degree).endswith('.0') else str(degree)
            op_label_parts.append(f"rotated_{angle_str}")
        if flip_horizontal:
            op_label_parts.append("fliph")
        if flip_vertical:
            op_label_parts.append("flipv")
        op_label = "_".join(op_label_parts)

        if overwrite:
            # Write to a temp file in the same directory, then atomically replace input.
            input_dir = os.path.dirname(input_file) or '.'
            _, ext = os.path.splitext(input_file)
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext, dir=input_dir) as tf:
                temp_file = tf.name
            subprocess.run(['magick', input_file, *ops, temp_file], check=True, capture_output=True)
            os.replace(temp_file, input_file)
            return f"Successfully transformed and overwrote '{input_file}'"

        # Construct output file path with operation suffix.
        base_name, ext = os.path.splitext(os.path.basename(input_file))
        output_file = os.path.join(output_dir, f"{base_name}_{op_label}{ext}")
        subprocess.run(['magick', input_file, *ops, output_file], check=True, capture_output=True)
        return f"Successfully transformed '{input_file}' and saved to '{output_file}'"
    except subprocess.CalledProcessError as e:
        return f"Error: Failed to rotate '{input_file}'. Subprocess returned code {e.returncode}."
    except Exception as e:
        return f"Unexpected error processing '{input_file}': {e}"
    finally:
        if temp_file and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except OSError:
                pass

def main():
    parser = FullHelpArgumentParser(description='Transform images (rotate/flip) using ImageMagick with GPU acceleration (if available).')
    parser.add_argument('positional_inputs', nargs='*',
                        help='One or more input image file paths (supports globs like *)')
    parser.add_argument('-d', '--degree', type=float, default=None,
                        help='Rotation angle in degrees (positive for clockwise, negative for counterclockwise)')
    parser.add_argument('-H', '--flip-horizontal', action='store_true',
                        help='Flip image horizontally (mirror)')
    parser.add_argument('-V', '--flip-vertical', action='store_true',
                        help='Flip image vertically')
    parser.add_argument('-i', '--inputs', nargs='+', default=None,
                        help='One or more input image file paths (supports globs like *)')
    parser.add_argument('-r', '--recursive', action='store_true',
                        help='Search subfolders recursively for matching inputs')
    output_mode_group = parser.add_mutually_exclusive_group(required=True)
    output_mode_group.add_argument('-o', '--output-dir',
                                   help='Output directory for rotated images')
    output_mode_group.add_argument('-w', '--overwrite', action='store_true',
                                   help='Overwrite input files in place (no suffix/folder)')
    parser.add_argument('-p', '--parallel', type=int, default=None,
                        help='Number of parallel processes (default: number of CPU cores)')
    
    args = parser.parse_args()

    # Support both positional inputs and -i/--inputs
    collected_inputs = []
    if args.positional_inputs:
        collected_inputs.extend(args.positional_inputs)
    if args.inputs:
        collected_inputs.extend(args.inputs)
    if not collected_inputs:
        parser.error("at least one input is required (provide positional INPUTS and/or -i/--inputs).")

    if args.degree is None and not args.flip_horizontal and not args.flip_vertical:
        parser.error("At least one transform is required: use --degree and/or --flip-horizontal/--flip-vertical.")
    
    # Expand input paths/patterns and filter for image files
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp', '.svg', '.heic'}
    expanded_inputs = []
    wildcard_chars = set('*?[]')
    for input_item in collected_inputs:
        matches = []
        if os.path.isdir(input_item):
            search_pattern = os.path.join(input_item, '**', '*') if args.recursive else os.path.join(input_item, '*')
            matches = glob.glob(search_pattern, recursive=args.recursive)
        elif os.path.isfile(input_item):
            matches = [input_item]
        else:
            has_wildcards = any(char in input_item for char in wildcard_chars)
            if args.recursive and has_wildcards:
                # For patterns like "*.png", recurse through the full subtree.
                if '**' in input_item:
                    matches = glob.glob(input_item, recursive=True)
                else:
                    pattern_dir = os.path.dirname(input_item)
                    pattern_name = os.path.basename(input_item)
                    recursive_pattern = os.path.join(pattern_dir, '**', pattern_name) if pattern_dir else os.path.join('**', pattern_name)
                    matches = glob.glob(recursive_pattern, recursive=True)
            else:
                matches = glob.glob(input_item)

        for file in matches:
            if os.path.isfile(file) and os.path.splitext(file)[1].lower() in image_extensions:
                expanded_inputs.append(file)

    # Remove duplicates while preserving order
    expanded_inputs = list(dict.fromkeys(expanded_inputs))
    
    if not expanded_inputs:
        print("Error: No compatible image files found matching the provided patterns.")
        return
    
    # Ensure output directory exists (only for non-overwrite mode)
    if args.output_dir:
        os.makedirs(args.output_dir, exist_ok=True)
    
    try:
        # Process files in parallel
        with concurrent.futures.ProcessPoolExecutor(max_workers=args.parallel) as executor:
            futures = [
                executor.submit(
                    process_file,
                    input_file,
                    args.degree,
                    args.flip_horizontal,
                    args.flip_vertical,
                    args.output_dir,
                    args.overwrite,
                )
                for input_file in expanded_inputs
            ]
            for future in concurrent.futures.as_completed(futures):
                print(future.result())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == '__main__':
    main()
