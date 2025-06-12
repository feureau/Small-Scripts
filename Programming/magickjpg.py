import os
import subprocess
import shutil
import argparse
import glob
import sys

# Define a list of common image extensions to look for when no pattern is given
SUPPORTED_EXTENSIONS = [
    '.png', '.jpeg', '.jpg', '.tiff', '.tif', '.bmp', '.gif', '.webp', 
    '.heic', '.heif', '.psd', '.svg', '.eps', '.pdf' 
    # Note: Rasterizing vector formats like SVG, EPS, PDF might need specific
    # ImageMagick options (e.g., -density) for optimal results.
]

def compression_type(value):
    """Custom type for argparse to validate compression level."""
    try:
        ivalue = int(value)
        if not (0 <= ivalue <= 100):
            raise argparse.ArgumentTypeError(f"Compression level must be between 0 and 100, got {value}")
        return ivalue
    except ValueError:
        raise argparse.ArgumentTypeError(f"Compression level must be an integer, got {value}")

def process_images(args):
    """
    Converts images to JPG using ImageMagick based on provided arguments.
    If no input pattern is given, processes all supported image types in the current directory.
    Moves processed JPG files to a 'jpg' subfolder.
    """
    print(f"Running script in working directory: {os.getcwd()}")

    # 1. Determine input files
    actual_input_files_for_processing = []
    magick_input_specifier = [] # What to pass to magick command

    if args.input_pattern:
        print(f"Using input pattern: {args.input_pattern}")
        # Globbing here helps confirm files exist and get a list for moving.
        actual_input_files_for_processing = glob.glob(args.input_pattern)
        if not actual_input_files_for_processing:
            print(f"No files found matching pattern: {args.input_pattern}")
            return
        magick_input_specifier = [args.input_pattern] # Pass pattern directly to mogrify
        print(f"Files matched by pattern: {actual_input_files_for_processing}")
    else:
        print("No input pattern provided. Scanning for all supported image files in the current directory...")
        all_files_in_dir = os.listdir('.')
        for f in all_files_in_dir:
            if os.path.isfile(f) and os.path.splitext(f)[1].lower() in SUPPORTED_EXTENSIONS:
                actual_input_files_for_processing.append(f)
        
        if not actual_input_files_for_processing:
            print("No supported image files found in the current directory to process.")
            return
        magick_input_specifier = actual_input_files_for_processing # Pass list of files to mogrify
        print(f"Found the following image files to process: {actual_input_files_for_processing}")

    # 2. Determine JPEG quality from compression or quality arguments
    quality_val = None
    if args.compression is not None:
        quality_val = max(1, 100 - args.compression) # Ensure quality is at least 1
        print(f"Using compression level {args.compression}, setting JPEG quality to {quality_val}.")
    elif args.quality is not None: # Original quality flag
        quality_val = args.quality
        print(f"Using JPEG quality level {quality_val}.")
    else:
        print("No specific compression or quality set, using ImageMagick's default JPEG quality.")

    # 3. Build ImageMagick command
    # 'mogrify' modifies files in place or creates new ones based on -format.
    magick_command = ['magick', 'mogrify', '-format', 'jpg']

    if quality_val is not None:
        magick_command.extend(['-quality', str(quality_val)])
    
    # Add other existing ImageMagick options from arguments
    if args.sampling_factor is not None:
        magick_command.extend(['-sampling-factor', args.sampling_factor])
    if args.density is not None:
        magick_command.extend(['-density', str(args.density)])
    if args.interlace is not None:
        magick_command.extend(['-interlace', args.interlace])
    if args.strip:
        magick_command.append('-strip')
    if args.profile is not None:
        magick_command.extend(['-profile', args.profile])
    if args.resize is not None:
        magick_command.extend(['-resize', args.resize])

    # Add the input files/pattern to the command
    magick_command.extend(magick_input_specifier)

    print(f"Executing ImageMagick command: {' '.join(magick_command)}")
    try:
        # Using text=True for Python 3.7+ for stdout/stderr decoding
        result = subprocess.run(magick_command, check=True, capture_output=True, text=True)
        if result.stdout:
            print(f"ImageMagick STDOUT:\n{result.stdout}")
        if result.stderr:
            print(f"ImageMagick STDERR:\n{result.stderr}") # Mogrify often prints info to stderr
        print("ImageMagick processing completed.")
    except subprocess.CalledProcessError as e:
        print(f"Error during ImageMagick conversion:\nReturn Code: {e.returncode}")
        if e.stdout:
            print(f"Stdout:\n{e.stdout}")
        if e.stderr:
            print(f"Stderr:\n{e.stderr}")
        return
    except FileNotFoundError:
        print("Error: ImageMagick 'magick' command not found. Please ensure ImageMagick is installed and in your system's PATH.")
        return
    except Exception as e:
        print(f"An unexpected error occurred during ImageMagick execution: {e}")
        return

    # 4. Move processed files to 'jpg' subfolder
    jpg_folder_name = 'jpg'
    jpg_folder_path = os.path.join(os.getcwd(), jpg_folder_name)
    os.makedirs(jpg_folder_path, exist_ok=True)
    print(f"Ensuring '{jpg_folder_name}' directory exists at '{jpg_folder_path}'.")

    moved_files_count = 0
    processed_but_not_found_for_move = []

    for original_file_rel_path in actual_input_files_for_processing:
        # original_file_rel_path could be 'image.png' or 'subdir/image.png' if pattern included subdirs
        
        # Determine the path of the JPG file after mogrify (relative to CWD)
        # e.g., if original_file_rel_path was 'data/input.png', processed_jpg_rel_path is 'data/input.jpg'
        base_path_part, _ = os.path.splitext(original_file_rel_path)
        processed_jpg_rel_path = base_path_part + ".jpg"
        
        # Full path to the source JPG file (that was just processed by mogrify)
        source_jpg_full_path = os.path.abspath(processed_jpg_rel_path)

        if os.path.exists(source_jpg_full_path):
            # Destination path: jpg/basename.jpg (flat structure in jpg_folder)
            # e.g., if processed_jpg_rel_path was 'data/input.jpg', destination is 'jpg/input.jpg'
            destination_jpg_full_path = os.path.join(jpg_folder_path, os.path.basename(processed_jpg_rel_path))
            
            try:
                # Prevent moving if source and destination are effectively the same
                # (e.g. if script is run inside 'jpg' folder, or file is already there and processed)
                if source_jpg_full_path == destination_jpg_full_path:
                    print(f"Skipping move for '{os.path.basename(processed_jpg_rel_path)}' as it is already in the target destination structure or would overwrite itself.")
                    continue

                shutil.move(source_jpg_full_path, destination_jpg_full_path)
                print(f"Moved '{os.path.basename(processed_jpg_rel_path)}' (from '{processed_jpg_rel_path}') to '{destination_jpg_full_path}'")
                moved_files_count += 1
            except Exception as e:
                print(f"Error moving '{os.path.basename(processed_jpg_rel_path)}' (from '{processed_jpg_rel_path}') to '{destination_jpg_full_path}': {e}")
        else:
            # This might happen if mogrify handled a file type it couldn't output as jpg,
            # or if the input file was deleted by another process, or naming issues.
            processed_but_not_found_for_move.append(original_file_rel_path)

    if moved_files_count > 0:
        print(f"Successfully moved {moved_files_count} JPG file(s) to '{jpg_folder_name}' folder.")
    else:
        print(f"No JPG files were moved to '{jpg_folder_name}'. This could be due to no images processed, issues finding them post-conversion, or they were already in the target structure.")

    if processed_but_not_found_for_move:
        print("\nWarning: The following input files were targeted for processing, but their expected JPG counterparts were not found for moving:")
        for f_path in processed_but_not_found_for_move:
            base_p, _ = os.path.splitext(f_path)
            print(f"  - Original: {f_path} (Expected JPG: {base_p + '.jpg'})")
        print("This could indicate an issue with ImageMagick's conversion for these specific files or an unexpected output naming.")

    print("Script finished.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Converts images to JPG in the current directory using ImageMagick and moves them to a 'jpg' subfolder.\n"
            "If no input pattern is specified, it processes all supported image types found in the current directory.\n"
            "Existing JPG files will also be processed (e.g., re-compressed) if they match the criteria."
        ),
        formatter_class=argparse.RawTextHelpFormatter # For better help text formatting
    )

    # Optional positional argument for input pattern
    parser.add_argument(
        'input_pattern', 
        type=str, 
        nargs='?',  # Makes it optional
        default=None, # Default value if not provided
        help=(
            "Optional input file pattern (e.g., '*.png', 'image*.tif', 'subdir/*.jpeg').\n"
            "If not provided, all supported image files in the current working directory will be processed.\n"
            f"Supported extensions when scanning: {', '.join(SUPPORTED_EXTENSIONS)}"
        )
    )

    # New compression flag
    parser.add_argument(
        '-c', '--compression', 
        type=compression_type, # Custom type for 0-100 validation
        metavar='LEVEL',
        help=(
            "JPEG compression level (0-100).\n"
            "  0   = lowest compression (best quality, largest file).\n"
            "  100 = highest compression (lowest quality, smallest file).\n"
            "This maps to ImageMagick's -quality option. Overrides --quality if both are used."
        )
    )

    # Existing JPG Conversion Options (from original script)
    parser.add_argument(
        '-q', '--quality', 
        type=int, 
        metavar='QLTY',
        help=(
            "JPEG quality level (1-100, ImageMagick's default if not set).\n"
            "Higher is better quality, larger file size.\n"
            "If -c/--compression is also used, --compression takes precedence."
        )
    )
    parser.add_argument(
        '--sampling-factor', 
        type=str, 
        help="JPEG chroma sampling factor (e.g., '4:2:0', '4:4:4')."
    )
    parser.add_argument(
        '--density', 
        type=str, # Changed to str to allow '300' or '300x300'
        help="DPI density for the JPEG images (e.g., '300', '72x72')."
    )
    parser.add_argument(
        '--interlace', 
        type=str, 
        choices=['None', 'Plane', 'Line', 'Partition'], 
        help="JPEG interlace mode ('None', 'Plane', 'Line', 'Partition'). 'Plane' for progressive JPEGs."
    )
    parser.add_argument(
        '--strip', 
        action='store_true', 
        help="Strip metadata from JPEG images to reduce file size."
    )
    parser.add_argument(
        '--profile', 
        type=str, 
        help="Path to an ICC profile file to embed in JPEG images."
    )
    parser.add_argument(
        '--resize', 
        type=str, 
        help="ImageMagick geometry string for resizing images before conversion (e.g., '50%%', '800x600', 'x600', '800x>')."
    )

    # --- Add a verbosity flag ---
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help="Enable verbose output from ImageMagick (shows stdout/stderr)."
    )


    if len(sys.argv) == 1: # No arguments provided
        # Check if it's just -h or --help, argparse handles this
        if not any(arg in sys.argv for arg in ['-h', '--help']):
             print("No input pattern or options specified. Processing all supported images in the current directory with default settings.")
             print("Use -h or --help for more options.\n")
        # Args will be parsed with defaults
        
    args = parser.parse_args()

    # Modify density if it's just a number to be NxN
    if args.density and args.density.isdigit():
        args.density = f"{args.density}x{args.density}"

    # Adjust ImageMagick output verbosity based on the flag
    # The script already prints stdout/stderr on error or if they exist.
    # This flag is more of a conceptual toggle for future, more detailed logging if needed.
    # For now, the script prints ImageMagick's output if it's non-empty.
    # If args.verbose is True, we ensure it's printed.
    # The current logic for printing stdout/stderr from subprocess.run is already quite verbose.

    process_images(args)
