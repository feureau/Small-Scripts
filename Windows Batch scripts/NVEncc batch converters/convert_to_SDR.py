import os
import sys
import subprocess
import msvcrt  # For capturing any key press on Windows

# Path to the .cube LUT file
LUT_FILE = r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\LUT\Colorspace LUTS\5-NBCU_PQ2SDR_DL_RESOLVE17-VRT_v1.2.cube"

# Check LUT file path
if not os.path.isfile(LUT_FILE):
    print(f"Error: LUT file not found at {LUT_FILE}")
    print("Press any key to exit...")
    msvcrt.getch()  # Wait for any key press
    sys.exit(1)

def process_video(file_path):
    input_dir = os.path.dirname(file_path)
    file_name = os.path.basename(file_path)
    output_subdir = os.path.join(input_dir, "avc")
    os.makedirs(output_subdir, exist_ok=True)  # Ensure the "avc" subfolder exists
    output_file = os.path.join(output_subdir, os.path.splitext(file_name)[0] + "_8bit.mp4")

    # NVEncC command
    command = [
        "NVEncC64",  # NVEncC is assumed to be registered in the Windows PATH
        "--avhw",
        "--codec", "h264",
        "--output-depth", "8",
        "--vpp-colorspace", f"lut3d={LUT_FILE},lut3d_interp=trilinear",
        "--audio-copy",  # Copy all audio streams
        "--sub-copy",    # Copy all subtitle streams
        "--chapter-copy",  # Copy chapters
        "--data-copy",   # Copy data streams (e.g., closed captions)
        "--metadata", "copy",  # Copy global metadata
        "-i", file_path,
        "-o", output_file
    ]

    print(f"Processing: {file_path}")
    try:
        subprocess.run(command, check=True)
        print(f"Success: Converted {file_path} to {output_file}")
    except subprocess.CalledProcessError as e:
        print(f"Error: Failed to process {file_path}")
        print(e)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Drag and drop video files onto this script to process them.")
        print("Press any key to exit...")
        msvcrt.getch()  # Wait for any key press
        sys.exit(0)

    for file_path in sys.argv[1:]:
        if os.path.isfile(file_path):
            process_video(file_path)
        else:
            print(f"Error: {file_path} is not a valid file.")

    print("Processing complete. Press any key to exit...")
    msvcrt.getch()  # Wait for any key press before exiting
