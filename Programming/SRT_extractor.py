import sys
import subprocess
import os

def has_subtitles(input_file):
    """
    Check if the input file has subtitle streams.
    """
    try:
        command = ["ffmpeg", "-i", input_file]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        # Look for "Subtitle" in the ffmpeg output
        if "Stream #0:" in result.stderr and "Subtitle" in result.stderr:
            return True
        return False
    except Exception as e:
        print(f"Error checking subtitles in {input_file}: {e}")
        return False

def extract_subtitles(input_file):
    """
    Extract subtitles using ffmpeg and save them as a .srt file.
    """
    # Ensure the input_file path is valid and properly escaped
    if not os.path.exists(input_file):
        print(f"Error: File not found - {input_file}")
        return None

    # Check if the file has subtitles
    if not has_subtitles(input_file):
        print(f"No subtitles found in {input_file}. Skipping...")
        return None

    output_file = f"{input_file}.srt"
    command = ["ffmpeg", "-i", input_file, "-map", "0:s:0", output_file]
    try:
        # Run the ffmpeg command
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"Subtitles extracted to {output_file}")
        return output_file  # Return the output file name to indicate success
    except subprocess.CalledProcessError as e:
        print(f"Error processing {input_file}: {e}")
        print(f"ffmpeg command: {' '.join(command)}")
        print("Check if the file contains subtitles or if the ffmpeg command is correct.")
        return None  # Return None to indicate failure

def main():
    if len(sys.argv) < 2:
        print("Usage: python SRT_extractor.py <input_file> [<input_file> ...]")
        sys.exit(1)

    processed_files = []  # List to store successfully processed files

    for input_file in sys.argv[1:]:
        input_file = input_file.strip('"')  # Ensure any surrounding quotes are removed
        print(f"Processing file: {input_file}")
        result = extract_subtitles(input_file)
        if result:
            processed_files.append(input_file)  # Add successful file to the list

    # Write the summary of processed files
    if processed_files:
        print("\nProcessing complete!")
        print("The following files were processed:")
        for file in processed_files:
            print(f" - {file}")
    else:
        print("\nNo files were successfully processed.")

if __name__ == "__main__":
    main()
