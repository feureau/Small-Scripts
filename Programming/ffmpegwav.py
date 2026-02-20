import subprocess
import sys
import glob
import os

def convert_to_wav():
    # Check if arguments were provided (the * from your command line)
    if len(sys.argv) < 2:
        print("Usage: python ffmpegwav.py <files or *>")
        return

    # Expansion of wildcards provided in the command line
    files_to_process = []
    for arg in sys.argv[1:]:
        files_to_process.extend(glob.glob(arg))

    if not files_to_process:
        print("No matching files found.")
        return

    for file_path in files_to_process:
        # Skip directories
        if os.path.isdir(file_path):
            continue

        # Get file name and extension
        base_name = os.path.splitext(file_path)[0]
        output_file = f"{base_name}.wav"

        # Check if output already exists to avoid overwriting accidentally
        if os.path.exists(output_file):
            print(f"Skipping {file_path}: {output_file} already exists.")
            continue

        print(f"Processing: {file_path} -> {output_file}")
        
        try:
            # ffmpeg command: -i (input), -y (overwrite if exists)
            subprocess.run([
                'ffmpeg', 
                '-i', file_path, 
                output_file
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError:
            print(f"Error: Failed to convert {file_path}. Ensure FFmpeg is installed.")
        except FileNotFoundError:
            print("Error: FFmpeg not found in system PATH.")
            break

if __name__ == "__main__":
    convert_to_wav()