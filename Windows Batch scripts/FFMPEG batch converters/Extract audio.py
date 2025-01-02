import os
import sys
import subprocess

def is_ffmpeg_installed():
    """Check if ffmpeg is installed and accessible."""
    try:
        subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def convert_to_aac(input_file):
    """Convert the input file's audio to AAC using ffmpeg."""
    # Get the directory and base name of the input file
    dir_name = os.path.dirname(input_file)
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    output_file = os.path.join(dir_name, f"{base_name}.aac")

    # Construct the ffmpeg command
    command = [
        'ffmpeg',
        '-i', input_file,
        '-vn',               # No video
        '-acodec', 'aac',    # AAC audio codec
        '-b:a', '192k',      # Audio bitrate
        output_file
    ]

    print(f"Processing: {input_file}")
    try:
        # Run the ffmpeg command
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"Successfully created: {output_file}\n")
    except subprocess.CalledProcessError as e:
        print(f"Error processing {input_file}: {e}\n")

def main():
    # Check if ffmpeg is installed
    if not is_ffmpeg_installed():
        print("FFmpeg is not installed or not found in PATH.")
        print("Please install FFmpeg and ensure it's added to the system PATH.")
        sys.exit(1)

    # Check if any files were dragged and dropped
    if len(sys.argv) < 2:
        print("No files were provided.")
        print("Drag and drop files onto the script to convert their audio to AAC.")
        sys.exit(1)

    # Iterate over each file provided as an argument
    for input_file in sys.argv[1:]:
        # Check if the file exists
        if not os.path.isfile(input_file):
            print(f"File not found: {input_file}\n")
            continue

        convert_to_aac(input_file)

    print("All files have been processed.")

if __name__ == "__main__":
    main()
