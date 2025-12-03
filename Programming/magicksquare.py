import sys
import os
import subprocess
import shutil
import glob
import argparse

def scan_directory_for_images(directory="."):
    """Scan directory and all subdirectories for supported image files."""
    supported_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', 
                           '.webp', '.svg', '.heic', '.avif', '.ico', '.jfif']
    
    image_files = []
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            file_ext = os.path.splitext(file)[1].lower()
            if file_ext in supported_extensions:
                full_path = os.path.join(root, file)
                image_files.append(full_path)
    
    return image_files

def print_help():
    """Print help documentation."""
    help_text = """
ImageMagick Square Converter v2.0
=================================
Converts images to 1024x1024 PNG format with padding or cropping.

USAGE:
  magicksquare.py [OPTIONS] [FILES...]

OPTIONS:
  -h, --help      Show this help message and exit
  -c, --crop      Crop image to square (default: resize with padding)
  -d, --directory PATH  Process images in specified directory (instead of current)
  -o, --output DIR      Output directory name (default: 'png')
  -q, --quality NUM     Output quality (1-100, default: 70)
  -s, --size SIZE       Output size in pixels (default: 1024x1024)

EXAMPLES:
  magicksquare.py                         # Process all images in current folder
  magicksquare.py image.jpg               # Process single file
  magicksquare.py *.jpg *.png             # Process by wildcard
  magicksquare.py -c                      # Crop all images in folder
  magicksquare.py -c photo.jpg            # Crop single image
  magicksquare.py -o "processed" -q 80    # Custom output and quality
  magicksquare.py -s 512x512              # Create 512px squares
  magicksquare.py -d "C:\\my_images"      # Process images in different folder

NOTES:
  - Without arguments, scans current folder and all subfolders
  - Supports wildcards: *.jpg, *.png, image_*.webp, etc.
  - Requires ImageMagick to be installed and in PATH
  """
    print(help_text)

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description="Convert images to square PNG format",
        add_help=False  # We'll handle -h/--help manually
    )
    
    parser.add_argument(
        'files',
        nargs='*',  # Zero or more file arguments
        help='Image files to process (supports wildcards)'
    )
    parser.add_argument(
        '-h', '--help',
        action='store_true',
        help='Show help message'
    )
    parser.add_argument(
        '-c', '--crop',
        action='store_true',
        help='Crop image to square instead of padding'
    )
    parser.add_argument(
        '-o', '--output',
        default='png',
        help='Output directory name (default: png)'
    )
    parser.add_argument(
        '-q', '--quality',
        type=int,
        default=70,
        help='Output quality 1-100 (default: 70)'
    )
    parser.add_argument(
        '-s', '--size',
        default='1024x1024',
        help='Output size in WxH format (default: 1024x1024)'
    )
    parser.add_argument(
        '-d', '--directory',
        default='.',
        help='Directory to scan for images (when no files specified)'
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    # Handle help flag
    if args.help:
        print_help()
        input("Press any key to exit...")
        return
    
    # Set up output directory
    output_dir = args.output
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Get files to process
    files_to_process = []
    
    if args.files:
        # Expand wildcards in provided arguments
        for arg in args.files:
            if '*' in arg or '?' in arg:
                # Handle relative and absolute paths with wildcards
                expanded = glob.glob(arg, recursive=True)
                if not expanded:
                    print(f"Warning: No files found matching: {arg}")
                files_to_process.extend(expanded)
            else:
                # Check if file exists
                if os.path.isfile(arg):
                    files_to_process.append(arg)
                else:
                    print(f"Warning: File not found: {arg}")
    else:
        # No files specified, scan directory
        print(f"Scanning '{args.directory}' and subdirectories for images...")
        files_to_process = scan_directory_for_images(args.directory)
        
        if not files_to_process:
            print(f"No image files found in '{args.directory}'")
            input("Press any key to exit...")
            return
        
        print(f"Found {len(files_to_process)} image(s) to process")
    
    # Validate we have files to process
    if not files_to_process:
        print("No files to process.")
        input("Press any key to exit...")
        return
    
    # Validate quality
    quality = max(1, min(100, args.quality))
    if args.quality != quality:
        print(f"Quality adjusted to {quality} (must be between 1-100)")
    
    # Process each file
    processed_count = 0
    failed_count = 0
    
    for i, filename in enumerate(files_to_process, 1):
        if not os.path.isfile(filename):
            print(f"Skipping '{filename}': Not a file.")
            failed_count += 1
            continue
        
        # Progress indicator
        print(f"[{i}/{len(files_to_process)}] Processing {os.path.basename(filename)}...")
        
        # Create output filename
        base_name = os.path.splitext(os.path.basename(filename))[0]
        output_filename = f"{base_name}.png"
        output_filepath = os.path.join(output_dir, output_filename)
        
        # Handle duplicate names
        counter = 1
        while os.path.exists(output_filepath):
            output_filename = f"{base_name}_{counter}.png"
            output_filepath = os.path.join(output_dir, output_filename)
            counter += 1
        
        # Build ImageMagick command based on mode
        cmd = ["magick", filename]
        
        if args.crop:
            # Crop mode: resize to cover area, then crop
            cmd.extend([
                "-resize", f"{args.size}^",  # ^ means cover area (minimum fit)
                "-gravity", "center",
                "-extent", args.size
            ])
        else:
            # Default mode: resize to fit, then pad
            cmd.extend([
                "-resize", args.size,
                "-background", "transparent",  # Changed from "alpha" for better compatibility
                "-gravity", "center",
                "-extent", args.size
            ])
        
        cmd.extend([
            "-quality", str(quality),
            output_filepath
        ])
        
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(f"  ✓ Created {output_filename}")
            processed_count += 1
        except FileNotFoundError:
            print(f"Error: 'magick' command not found.")
            print("Please install ImageMagick from: https://imagemagick.org")
            break
        except subprocess.CalledProcessError as e:
            print(f"  ✗ Error processing {filename}")
            if e.stderr:
                print(f"    {e.stderr[:100]}...")  # Show first 100 chars of error
            failed_count += 1
        except Exception as e:
            print(f"  ✗ Unexpected error: {e}")
            failed_count += 1
    
    # Summary
    print("\n" + "="*50)
    print("PROCESSING COMPLETE")
    print("="*50)
    print(f"Total files processed: {processed_count}")
    if failed_count > 0:
        print(f"Files failed: {failed_count}")
    print(f"Output directory: {os.path.abspath(output_dir)}")
    
    if processed_count > 0:
        print(f"\nAll converted images saved to: {os.path.abspath(output_dir)}")
    
    input("\nPress any key to exit...")

if __name__ == "__main__":
    main()