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