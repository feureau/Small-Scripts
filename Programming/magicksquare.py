import sys
import os
import subprocess
import shutil
import glob # Import the glob module

def main():
    if len(sys.argv) < 2:
        print("No files provided.")
        input("Press any key to exit...")
        return

    output_dir = "png"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Use glob to expand the arguments if they are patterns
    files_to_process = []
    for arg in sys.argv[1:]:
        if '*' in arg or '?' in arg: # Check if the argument contains a wildcard
            files_to_process.extend(glob.glob(arg))
        else:
            files_to_process.append(arg) # Add the argument directly if no wildcard

    if not files_to_process:
         print("No files found matching the provided arguments.")
         input("Press any key to exit...")
         return

    # Process each file found by glob or provided explicitly
    for filename in files_to_process:
        if not os.path.isfile(filename): # Basic check if it's actually a file
             print(f"Skipping '{filename}': Not a file.")
             continue

        print(f"Processing {filename}...") # Improved print message
        # Define the output filename by appending .png to the original name.
        # Use os.path.splitext to handle extensions correctly
        base_name = os.path.splitext(os.path.basename(filename))[0]
        output_filename = f"{base_name}.png"
        output_filepath = os.path.join(output_dir, output_filename) # Save directly to output dir

        # Build and run the ImageMagick command.
        cmd = [
            "magick", filename,
            "-resize", "1024x1024",
            "-background", "alpha",
            "-gravity", "center",
            "-extent", "1024x1024",
            "-quality", "70",
            output_filepath # Output directly to the target path
        ]

        try:
            # Use check=True to raise an error on failure
            subprocess.run(cmd, check=True, capture_output=True, text=True) # Capture output for debugging
            print(f"Successfully created {output_filepath}")
        except FileNotFoundError:
             print(f"Error: 'magick' command not found. Is ImageMagick installed and in your PATH?")
             break # Exit if magick is not found
        except subprocess.CalledProcessError as e:
            print(f"Error processing {filename}: {e}")
            print(f"ImageMagick Output (stderr): {e.stderr}")
            print(f"ImageMagick Output (stdout): {e.stdout}")
            # Continue processing other files despite this error
        except Exception as e:
             print(f"An unexpected error occurred with {filename}: {e}")
             # Continue processing other files

    # End message similar to PAUSE in the batch script.
    input("Processing complete! Press any key to exit...")

if __name__ == "__main__":
    main()