"""
magickrotate.py - GPU-Accelerated Image Rotation Script

A Python script for batch rotating images using ImageMagick with GPU acceleration support.
Processes multiple images in parallel, supporting custom rotation angles and glob patterns.

Features:
- GPU acceleration via ImageMagick's OpenCL support (if available)
- Parallel processing using multiple CPU cores
- Supports glob patterns (e.g., *.jpg, image*)
- Custom rotation angles (positive: clockwise, negative: counterclockwise)
- Automatic output directory creation
- Graceful handling of Ctrl-C interruption
- Compatible with common image formats (JPG, PNG, GIF, BMP, TIFF, WebP, SVG, HEIC)

Requirements:
- Python 3.6+
- ImageMagick installed with OpenCL support (check with `magick -version | find "OpenCL"`)
- For GPU acceleration: NVIDIA/AMD GPU with OpenCL drivers

Usage:
    python magickrotate.py -r ROTATE -i INPUT [INPUT ...] -o OUTPUT_DIR [options]

Arguments:
    -r, --rotate FLOAT       Rotation angle in degrees (required)
    -i, --inputs PATTERN     Input image files/patterns (required, supports globs)
    -o, --output-dir DIR     Output directory for rotated images (required)
    -p, --parallel INT       Number of parallel processes (default: CPU cores)

Examples:
    # Rotate all JPG files in current dir by 90 degrees clockwise
    python magickrotate.py -i *.jpg -r 90 -o rotated

    # Rotate multiple files by 45 degrees counterclockwise with 4 processes
    python magickrotate.py -i image1.png image2.jpg -r -45 -o output -p 4

    # Use glob for all images in subdir
    python magickrotate.py -i "subdir/*" -r 180 -o rotated

Output:
    Rotated images are saved with '_rotated_ANGLE' suffix (e.g., photo_rotated_90.jpg).
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

# Enable OpenCL GPU acceleration for ImageMagick if available
os.environ['MAGICK_OCL_DEVICE'] = 'true'

def process_file(input_file, rotate, output_dir):
    """Process a single image file: rotate and save."""
    if not os.path.isfile(input_file):
        return f"Error: Input file '{input_file}' does not exist."
    
    # Construct output file path with '_rotated_degrees' suffix
    base_name, ext = os.path.splitext(os.path.basename(input_file))
    angle_str = str(rotate).replace('.0', '') if str(rotate).endswith('.0') else str(rotate)
    output_file = os.path.join(output_dir, f"{base_name}_rotated_{angle_str}{ext}")
    
    # Run magick command (uses GPU if OpenCL is available and enabled)
    try:
        subprocess.run(['magick', input_file, '-rotate', str(rotate), output_file], check=True, capture_output=True)
        return f"Successfully rotated '{input_file}' by {rotate} degrees and saved to '{output_file}'"
    except subprocess.CalledProcessError as e:
        return f"Error: Failed to rotate '{input_file}'. Subprocess returned code {e.returncode}."
    except Exception as e:
        return f"Unexpected error processing '{input_file}': {e}"

def main():
    parser = argparse.ArgumentParser(description='Rotate images using ImageMagick with GPU acceleration (if available).')
    parser.add_argument('-r', '--rotate', type=float, required=True,
                        help='Rotation angle in degrees (positive for clockwise, negative for counterclockwise)')
    parser.add_argument('-i', '--inputs', nargs='+', required=True,
                        help='One or more input image file paths (supports globs like *)')
    parser.add_argument('-o', '--output-dir', required=True,
                        help='Output directory for rotated images')
    parser.add_argument('-p', '--parallel', type=int, default=None,
                        help='Number of parallel processes (default: number of CPU cores)')
    
    args = parser.parse_args()
    
    # Expand glob patterns in inputs and filter for image files
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp', '.svg', '.heic'}
    expanded_inputs = []
    for pattern in args.inputs:
        for file in glob.glob(pattern):
            if os.path.splitext(file)[1].lower() in image_extensions:
                expanded_inputs.append(file)
    
    if not expanded_inputs:
        print("Error: No compatible image files found matching the provided patterns.")
        return
    
    # Ensure output directory exists
    os.makedirs(args.output_dir, exist_ok=True)
    
    try:
        # Process files in parallel
        with concurrent.futures.ProcessPoolExecutor(max_workers=args.parallel) as executor:
            futures = [executor.submit(process_file, input_file, args.rotate, args.output_dir) for input_file in expanded_inputs]
            for future in concurrent.futures.as_completed(futures):
                print(future.result())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == '__main__':
    main()