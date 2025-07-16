"""
================================
Batch HDR to SDR Video Converter
================================

Description:
------------
This script provides a powerful command-line interface to batch convert HDR (High
Dynamic Range) video files to SDR (Standard Dynamic Range). It is designed for
a professional post-production workflow where a specific 3D Look-Up Table (LUT)
is required for the color and tone mapping transformation.

The script leverages GPU acceleration for both decoding and encoding to achieve
maximum performance, offloading the most intensive tasks from the CPU.

Features:
---------
- Dual-Engine Support: Choose between two powerful conversion engines:
    - NVEncC: A highly optimized, command-line tool for NVIDIA encoders. (Default)
    - FFmpeg: The universal standard for video manipulation.
- Full GPU Acceleration: Utilizes NVIDIA's NVENC for encoding and CUDA for
  decoding (av1_cuvid), ensuring a fast, efficient pipeline.
- Flexible Input: Process videos in multiple ways:
    - A single video file.
    - Multiple specific video files.
    - An entire folder of videos.
    - A glob pattern (e.g., "*.mkv").
- Lossless Audio: Copies all audio tracks directly from the source to the
  destination without re-encoding, preserving full audio quality.
- Optimized & Correct: The parameters used for both engines have been carefully
  researched and tested to correctly apply the specified LUT according to the
  LUT author's own instructions (e.g., using tetrahedral interpolation).
- Robust File Handling: Includes a 'staging' system for the LUT file when using
  NVEncC to prevent command-line path and quoting issues.

Requirements:
-------------
1. Python 3.x
2. FFmpeg: A recent 'full' build (from gyan.dev or similar) must be installed
   and accessible via the system's PATH environment variable.
3. NVEncC: A recent version must be installed and accessible via the system's
   PATH environment variable.
4. NVIDIA GPU: A modern NVIDIA graphics card (RTX series recommended for full
   AV1 decoding support).
5. NVIDIA Graphics Driver: A recent version of the driver.
6. The specific .cube LUT file referenced in the script.

Configuration:
--------------
The `LUT_FILE_PATH` variable at the top of the script must be set to the correct
location of your '.cube' LUT file.

================================
HOW TO USE - EXAMPLES
================================

Open a command prompt (cmd.exe) or PowerShell in a folder containing your videos.

--- Basic Usage (using the default NVEncC engine) ---

# Convert all .mkv files in the current folder (.)
> python your_script_name.py .

# Convert a single specific video file
> python your_script_name.py "My HDR Video.mkv"

# Convert multiple specific video files
> python your_script_name.py "video1.mkv" "D:\folder 2\video2.mov"

# Convert all .mp4 files in the current folder
> python your_script_name.py . --ext mp4

--- Using the FFmpeg Engine ---

# Convert all .mkv files in the current folder using FFmpeg
> python your_script_name.py . -f

# Convert a single file using FFmpeg
> python your_script_name.py "My HDR Video.mkv" --ffmpeg

--- Advanced Usage ---

# Use a glob pattern to select files
> python your_script_name.py *.mkv

# Specify a custom suffix for the output files
> python your_script_name.py . --suffix _SDR_Final

================================
COMMAND-LINE ARGUMENTS
================================

- `input_paths`
  (Required) One or more positional arguments specifying the input.
  Can be a file path, a folder path, or a glob pattern.

- `-f`, `--ffmpeg`
  (Optional) Use the FFmpeg engine for conversion.

- `-n`, `--nvencc`
  (Optional) Use the NVEncC engine for conversion. This is the default
  behavior if neither -f nor -n is specified.

- `--ext <extension>`
  (Optional) The file extension to search for when a folder is provided
  as an input path. Default is "mkv".

- `--suffix <text>`
  (Optional) A custom text suffix to add to the output filenames before the
  extension. If not provided, it defaults to "_SDR_NVENCC" or "_SDR_FFMPEG"
  depending on the engine used.

"""

import argparse
import glob
import os
import subprocess
import sys
import shutil

# --- Configuration ---
# Updated to the new path you provided.
LUT_FILE_PATH = r"I:\LUT\NBCUniversal-UHD-HDR-SDR-Single-Master-Production-Workflow-Recommendation-LUTs-main\LUTS_for_Software_DaVinci_Premiere_Avid_FinalCutPro\DaVinci-Resolve-with-Video-Range-Tag\5-NBCU_PQ2SDR_DL_RESOLVE17-VRT_v1.2.cube"

# --- Dependency Check Functions ---
def check_ffmpeg():
    """Checks if ffmpeg.exe is available."""
    try:
        if not subprocess.check_output(["where", "ffmpeg"]).strip(): raise FileNotFoundError
        print("✅ ffmpeg.exe found.")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Error: 'ffmpeg.exe' not found in your system's PATH.")
        return False

def check_nvencc():
    """Checks if nvencc64.exe is available."""
    try:
        if not subprocess.check_output(["where", "nvencc64"]).strip(): raise FileNotFoundError
        print("✅ nvencc64.exe found.")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Error: 'nvencc64.exe' not found in your system's PATH.")
        return False

# --- FFmpeg Conversion Function ---
def process_file_ffmpeg(input_file, output_suffix):
    """Converts a video using the robust, hybrid GPU/CPU FFmpeg pipeline."""
    directory = os.path.dirname(os.path.abspath(input_file))
    base, ext = os.path.splitext(os.path.basename(input_file))
    output_filename = f"{base}{output_suffix}.mkv"
    output_file = os.path.join(directory, output_filename)
    print(f"\n🎬 Processing with FFmpeg: {os.path.basename(input_file)}")
    filter_lut_path = LUT_FILE_PATH.replace('\\', '/').replace(':', '\\:')
    video_filter = f"lut3d=file='{filter_lut_path}'"
    command = [
        "ffmpeg", "-y", "-hwaccel", "cuda", "-c:v", "av1_cuvid", "-i", input_file,
        "-vf", video_filter, "-c:v", "h264_nvenc", "-preset", "p7", "-cq", "23",
        "-b:v", "0", "-c:a", "copy", output_file
    ]
    execute_command(command, input_file)

# --- NVEncC Conversion Function ---
def process_file_nvencc(input_file, output_suffix):
    """Converts a video using NVEncC, copying the LUT locally to avoid path issues."""
    directory = os.path.dirname(os.path.abspath(input_file))
    base, ext = os.path.splitext(os.path.basename(input_file))
    output_filename = f"{base}{output_suffix}{ext}"
    output_file = os.path.join(directory, output_filename)
    
    lut_basename = os.path.basename(LUT_FILE_PATH)
    temp_lut_path = os.path.join(directory, lut_basename)
    
    print(f"   -> Staging LUT file in video directory...")
    shutil.copy(LUT_FILE_PATH, temp_lut_path)
    
    print(f"\n🎬 Processing with NVEncC: {os.path.basename(input_file)}")

    colorspace_argument = f'lut3d={lut_basename},lut3d_interp=tetrahedral'
    
    command = [
        "nvencc64",
        "--avhw", "-i", input_file,
        "--vpp-colorspace", colorspace_argument,
        "--codec", "h264",
        "--colormatrix", "bt709", "--colorprim", "bt709", "--transfer", "bt709",
        "--colorrange", "limited",
        "--preset", "quality",
        "--audio-copy",
        "-o", output_file
    ]

    try:
        execute_command(command, input_file)
    finally:
        print(f"   -> Cleaning up staged LUT file...")
        if os.path.exists(temp_lut_path):
            os.remove(temp_lut_path)

# --- Universal Command Executor ---
def execute_command(command, input_file_for_error_msg):
    """A helper function to run a command and display its output dynamically."""
    print("🚀 Executing command...")
    print("   " + subprocess.list2cmdline(command))
    try:
        # By removing stdout/stderr pipes, output goes directly to the console in real-time.
        subprocess.run(command, check=True)
        print(f"\n✅ Successfully converted: {os.path.basename(input_file_for_error_msg)}")
    except subprocess.CalledProcessError as e:
        # The error log from the tool is already on the screen.
        print(f"\n❌ An error occurred during conversion of {os.path.basename(input_file_for_error_msg)}.")
        print(f"   The application exited with a non-zero error code: {e.returncode}. Please review the console output above for details.")
    except Exception as e:
        print(f"An unexpected Python error occurred: {e}")

# --- Main Program Logic ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Batch convert HDR videos to SDR using either FFmpeg or NVEncC.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    encoder_group = parser.add_mutually_exclusive_group()
    encoder_group.add_argument("-f", "--ffmpeg", action='store_true', help="Use FFmpeg for conversion.")
    encoder_group.add_argument("-n", "--nvencc", action='store_true', help="Use NVEncC for conversion (default).")
    parser.add_argument("input_paths", nargs='+', help="One or more paths to video files, folders, or glob patterns.")
    parser.add_argument("--ext", default="mkv", help="File extension to process in folders.")
    parser.add_argument("--suffix", default=None, help="Suffix for output files (default: _SDR_NVENCC or _SDR_FFMPEG).")
    args = parser.parse_args()

    if args.ffmpeg:
        encoder_name = "FFmpeg"
        process_function = process_file_ffmpeg
        if not check_ffmpeg(): sys.exit(1)
        suffix = args.suffix if args.suffix is not None else "_SDR_FFMPEG"
    else:
        encoder_name = "NVEncC"
        process_function = process_file_nvencc
        if not check_nvencc(): sys.exit(1)
        suffix = args.suffix if args.suffix is not None else "_SDR_NVENCC"

    if not os.path.isfile(LUT_FILE_PATH):
        print(f"❌ Critical Error: The LUT file was not found at:\n   {LUT_FILE_PATH}")
        sys.exit(1)
        
    files_to_process = []
    for path in args.input_paths:
        for expanded_path in glob.glob(path):
            if os.path.isfile(expanded_path):
                files_to_process.append(expanded_path)
            elif os.path.isdir(expanded_path):
                search_pattern = os.path.join(expanded_path, f"*.{args.ext}")
                files_to_process.extend(glob.glob(search_pattern))

    unique_files = sorted(list(set(files_to_process)))
    if not unique_files:
        print("\nNo video files found to convert.")
        sys.exit(0)

    print(f"\nEngine Selected: {encoder_name}")
    print(f"Found {len(unique_files)} unique video(s) to process.")
    print(f"🎨 Using conversion LUT: {os.path.basename(LUT_FILE_PATH)}")

    for video_file in unique_files:
        process_function(video_file, suffix)