import sys
import os
import subprocess
import shutil

def main():
    # Check if any filenames were provided as arguments.
    if len(sys.argv) < 2:
        print("No files provided.")
        input("Press any key to exit...")
        return

    # Ensure the output directory exists.
    output_dir = "png"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Process each file provided as an argument.
    for filename in sys.argv[1:]:
        print(filename)
        # Define the output filename by appending .png to the original name.
        output_filename = f"{filename}.png"

        # Build and run the ImageMagick command.
        # The command resizes the image to 1024x1024, centers it with alpha background,
        # sets the extent, and sets the quality to 70.
        cmd = [
            "magick", filename,
            "-resize", "1024x1024",
            "-background", "alpha",
            "-gravity", "center",
            "-extent", "1024x1024",
            "-quality", "70",
            output_filename
        ]
        subprocess.run(cmd, check=True)

        # Move the output file to the png directory.
        shutil.move(output_filename, os.path.join(output_dir, output_filename))

    # End message similar to PAUSE in the batch script.
    input("Processing complete! Press any key to exit...")

if __name__ == "__main__":
    main()
