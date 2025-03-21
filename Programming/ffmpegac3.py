import sys
import glob
import subprocess
import os

def main():
    # Check if file pattern is provided
    if len(sys.argv) < 2:
        print("Usage: python ffmpegconvertac3.py *.mkv")
        sys.exit(1)

    # Expand the file pattern using glob (works on Windows)
    file_pattern = sys.argv[1]
    files = glob.glob(file_pattern)
    
    if not files:
        print(f"No files found matching: {file_pattern}")
        sys.exit(1)
    
    for file in files:
        print(f"Processing: {file}")
        
        # Create output filename by appending .mov to the original filename
        # (alternatively, you can replace the extension if needed)
        output_file = file + ".mov"
        
        # Build the ffmpeg command
        command = [
            "ffmpeg",
            "-i", file,
            "-c:v", "copy",
            "-c:a", "ac3",
            "-ac", "6",
            "-b:a", "640k",
            "-map", "0:v:?",
            "-map", "0:a:?",
            "-mapping_family", "1",
            output_file
        ]
        
        # Execute the command and wait for it to complete
        try:
            subprocess.run(command, check=True)
            print(f"Created: {output_file}")
        except subprocess.CalledProcessError as e:
            print(f"Error processing {file}: {e}")

if __name__ == '__main__':
    main()
