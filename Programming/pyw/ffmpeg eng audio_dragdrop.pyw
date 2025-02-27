import os
import subprocess
import sys
from tkinter import messagebox

def process_file(file_path):
    """Process a single file with ffmpeg to copy all content and include only English audio tracks."""
    output_file = os.path.splitext(file_path)[0] + "_EnglishOnly.mkv"
    try:
        # Build the ffmpeg command
        ffmpeg_cmd = [
            "ffmpeg", "-i", file_path,
            "-map", "0:v",  # Map all video streams
            "-map", "0:s",  # Map all subtitle streams
            "-map", "0:m:language:eng",  # Map only English audio tracks
            "-c", "copy",  # Copy without re-encoding
            output_file
        ]

        # Execute the ffmpeg command
        subprocess.run(ffmpeg_cmd, check=True)
        print(f"Processed successfully: {file_path} -> {output_file}")
    except subprocess.CalledProcessError as e:
        print(f"Failed to process file: {file_path}\nError: {e}")
        messagebox.showerror("Error", f"Failed to process file: {file_path}\nError: {e}")

def main():
    """Main function to handle drag-and-drop files."""
    if len(sys.argv) < 2:
        messagebox.showinfo("Drag and Drop", "Drag and drop files onto this script to process them.")
        return

    # Process each dropped file
    for file_path in sys.argv[1:]:
        if os.path.isfile(file_path):
            print(f"Processing file: {file_path}")
            process_file(file_path)
        else:
            print(f"Skipped invalid file: {file_path}")

    messagebox.showinfo("Batch Processing Complete", "All files have been processed.")

if __name__ == "__main__":
    main()
