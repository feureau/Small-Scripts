#!/usr/bin/env python3
import glob
import subprocess
import os
import sys

# Define the file extensions you want to process.
# Feel free to add or remove extensions as needed.
video_extensions = ('*.mkv', '*.mp4', '*.avi', '*.mov', '*.flv')

def find_video_files():
    files = []
    for ext in video_extensions:
        files.extend(glob.glob(ext))
    return files

def encode_file(input_file):
    # Create an output file name by appending '_encoded' before the extension.
    base, ext = os.path.splitext(input_file)
    output_file = f"{base}_encoded.mkv"

    # Build the ffmpeg command.
    # Adjust parameters if you need different quality or file size.
    cmd = [
        "ffmpeg",
        "-i", input_file,
        "-c:v", "libx264",
        "-preset", "slow",       # Use a slower preset for better compression.
        "-crf", "18",            # CRF value; lower means higher quality and larger file size.
        "-tune", "animation",    # Optimize for animated content.
        "-profile:v", "high",
        "-level", "4.1",
        "-c:a", "copy",          # Copy the audio stream.
        output_file
    ]

    print(f"Encoding: {input_file} -> {output_file}")
    try:
        # Run the command and wait for it to finish.
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error encoding {input_file}: {e}", file=sys.stderr)

def main():
    video_files = find_video_files()
    if not video_files:
        print("No video files found in the current folder.")
        return

    for video in video_files:
        encode_file(video)

if __name__ == "__main__":
    main()
