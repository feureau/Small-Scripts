import os
import subprocess
import shutil
import argparse

def process_png_to_jpg_and_move(args):
    """
    Converts images matching the input pattern in the current working directory to JPG using ImageMagick,
    and moves only the newly generated JPG files to a 'jpg' subfolder.

    Args:
        args: An argparse.Namespace object containing parsed command-line arguments.
    """

    print(f"Running script in working directory: {os.getcwd()}")

    print("Listing files in current directory:")
    files_in_dir = os.listdir('.')
    for file in files_in_dir:
        print(f"- {file}")

    # 1. List existing JPG files before conversion
    before_jpg_files = set([f for f in os.listdir('.') if f.lower().endswith('.jpg')])

    print("Converting images to JPG using ImageMagick...")
    magick_command = ['magick', 'mogrify', '-format', 'jpg']

    # Add JPG conversion options based on arguments
    if args.quality is not None:
        magick_command.extend(['-quality', str(args.quality)])
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

    magick_command.append(args.input_pattern)  # Use the input pattern from arguments

    print(f"Executing ImageMagick command: {' '.join(magick_command)}") # Print the full command

    try:
        # 2. Execute ImageMagick command to convert images to JPG
        subprocess.run(magick_command, check=True, capture_output=True)
        print("Image conversion to JPG completed.")
    except subprocess.CalledProcessError as e:
        print(f"Error during ImageMagick conversion:\nReturn Code: {e.returncode}\nStdout: {e.stdout.decode()}\nStderr: {e.stderr.decode()}")
        return
    except FileNotFoundError:
        print("Error: ImageMagick 'magick' command not found. Please ensure ImageMagick is installed and added to your system's PATH.")
        return

    # 3. List JPG files after conversion
    after_jpg_files = set([f for f in os.listdir('.') if f.lower().endswith('.jpg')])

    # 4. Identify newly created JPG files
    new_jpg_files = list(after_jpg_files - before_jpg_files)

    if not new_jpg_files:
        print("No new JPG files were generated (either no images were converted or something went wrong).")
        return

    print(f"Newly generated JPG files: {new_jpg_files}")

    # 5. Create 'jpg' directory if it doesn't exist
    jpg_folder = 'jpg'
    os.makedirs(jpg_folder, exist_ok=True)
    print(f"Created or ensured existence of '{jpg_folder}' folder.")

    # 6. Move newly created JPG files to 'jpg' directory
    print("Moving newly generated JPG files to 'jpg' folder...")
    for jpg_file in new_jpg_files:
        source_path = jpg_file
        destination_path = os.path.join(jpg_folder, jpg_file)
        try:
            shutil.move(source_path, destination_path)
            print(f"Moved '{jpg_file}' to '{jpg_folder}' folder.")
        except Exception as e:
            print(f"Error moving '{jpg_file}': {e}")
            return

    print("Script finished processing JPG files.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert images to JPG in the current directory using ImageMagick and move new JPGs to a 'jpg' folder.")

    # Positional argument for input pattern
    parser.add_argument('input_pattern', type=str, help="Input file pattern (e.g., '*.png', 'image*.tif', 'single_image.bmp').")

    # JPG Conversion Options (same as before)
    parser.add_argument('-q', '--quality', type=int, help="JPEG quality level (0-100, higher is better quality, larger file size). Default is ImageMagick's default.")
    parser.add_argument('--sampling-factor', type=str, help="JPEG chroma sampling factor (e.g., '4:2:0', '4:4:4').")
    parser.add_argument('--density', type=int, help="DPI density for the JPEG images.")
    parser.add_argument('--interlace', type=str, choices=['None', 'Plane', 'Line', 'Partition'], help="JPEG interlace mode ('None', 'Plane', 'Line', 'Partition'). 'Plane' for progressive JPEGs.")
    parser.add_argument('--strip', action='store_true', help="Strip metadata from JPEG images to reduce file size.")
    parser.add_argument('--profile', type=str, help="Path to an ICC profile file to embed in JPEG images.")
    parser.add_argument('--resize', type=str, help="ImageMagick geometry string for resizing images before conversion (e.g., '50%', '800x600', '800x>', etc.).")

    args = parser.parse_args()

    process_png_to_jpg_and_move(args)