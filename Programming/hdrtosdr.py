"""
===================================================================
Batch HDR to SDR Video Converter (YouTube Optimized - Verified)
===================================================================

Description:
------------
This script provides a powerful command-line interface to batch convert HDR (High
Dynamic Range) video files to SDR (Standard Dynamic Range) files that are
highly optimized for uploading to YouTube. It is designed for a professional
post-production workflow where a specific 3D Look-Up Table (LUT) is required for
the color and tone mapping transformation.

The script leverages GPU acceleration for both decoding and encoding to achieve
maximum performance.

Features:
---------
- YouTube SDR Specification Adherence: Automatically detects input resolution
  and frame rate to apply YouTube's recommended settings.
- Manual Bitrate Override: Use the -b / --bitrate flag to set your own
  target bitrate in Mbps, bypassing the automatic YouTube calculation.
- Flexible Resizing: Use the -r / --resize flag to set the output's shortest
  dimension, preserving aspect ratio (e.g., --resize 1080 for 1920x1080 or 1080x1920).
- Dual-Engine Support: Choose between NVEncC (default) or FFmpeg.
- Full GPU Acceleration: Utilizes NVIDIA's NVENC for encoding and CUDA for
  decoding, ensuring a fast, efficient pipeline.
- Flexible Input: Process a single video file, multiple files, a folder, or a glob pattern.
- Optimized & Correct: The parameters used for both engines have been carefully
  researched and verified, including correct color range and space tagging for SDR.
- Robust File Handling: Includes a 'staging' system for the LUT file when using
  NVEncC to prevent command-line path and quoting issues.

Requirements:
-------------
1. Python 3.x
2. FFmpeg & ffprobe: A recent 'full' build must be in the system's PATH.
3. NVEncC: A recent version must be in the system's PATH.
4. NVIDIA GPU and a recent graphics driver.
5. The specific .cube LUT file referenced in the script.

"""

import argparse
import glob
import os
import subprocess
import sys
import shutil
import json
import math

# --- Configuration ---
LUT_FILE_PATH = r"I:\LUT\NBCUniversal-UHD-HDR-SDR-Single-Master-Production-Workflow-Recommendation-LUTs-main\LUTS_for_Software_DaVinci_Premiere_Avid_FinalCutPro\DaVinci-Resolve-with-Video-Range-Tag\5-NBCU_PQ2SDR_DL_RESOLVE17-VRT_v1.2.cube"

# --- YouTube SDR Bitrate Table ---
YOUTUBE_SDR_BITRATES = {
    2160: [40, 60], # 4K
    1440: [16, 24], # 2K
    1080: [8, 12],
    720:  [5, 7.5],
    480:  [2.5, 4],
    360:  [1, 1.5]
}

# --- Metadata and Settings Functions ---
def get_video_metadata(input_file):
    """Probes the video file with ffprobe to get resolution and frame rate."""
    print(f"   -> Probing video metadata for {os.path.basename(input_file)}...")
    command = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,avg_frame_rate",
        "-of", "json", input_file
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True, encoding='utf-8')
        metadata = json.loads(result.stdout)['streams'][0]
        
        num, den = metadata['avg_frame_rate'].split('/')
        denominator = float(den)
        if denominator == 0:
            frame_rate = float(num)
        else:
            frame_rate = float(num) / denominator
        
        return {
            "width": int(metadata['width']),
            "height": int(metadata['height']),
            "frame_rate": frame_rate
        }
    except (subprocess.CalledProcessError, KeyError, IndexError, ZeroDivisionError) as e:
        print(f"   ❌ Could not probe video metadata for {os.path.basename(input_file)}. Skipping. Error: {e}")
        return None

def get_youtube_sdr_settings(height, frame_rate):
    """Calculates encoding settings based on YouTube's recommendations."""
    closest_res = min(YOUTUBE_SDR_BITRATES.keys(), key=lambda x: abs(x - height))
    is_high_fps = frame_rate > 30.0
    bitrate_mbps = YOUTUBE_SDR_BITRATES[closest_res][1 if is_high_fps else 0]
    
    bitrate_kbps = int(bitrate_mbps * 1000)
    
    settings = {
        "bitrate_str": f"{bitrate_mbps}M",
        "max_bitrate_str": f"{bitrate_mbps * 1.5}M",
        "bitrate_kbps": bitrate_kbps,
        "max_bitrate_kbps": int(bitrate_kbps * 1.5)
    }
    print(f"   -> Auto-determined settings: {height}p@{round(frame_rate, 2)}fps -> Target Bitrate: {settings['bitrate_str']}")
    return settings

# --- Dependency Check Functions ---
def check_dependencies(use_ffmpeg):
    """Checks if required executables are available."""
    try:
        if not shutil.which("ffprobe"): raise FileNotFoundError("ffprobe")
        print("✅ ffprobe.exe found.")
        if use_ffmpeg:
            if not shutil.which("ffmpeg"): raise FileNotFoundError("ffmpeg")
            print("✅ ffmpeg.exe found.")
        else:
            if not shutil.which("nvencc64"): raise FileNotFoundError("nvencc64")
            print("✅ nvencc64.exe found.")
        return True
    except FileNotFoundError as e:
        print(f"❌ Error: '{e}' not found in your system's PATH.")
        return False

# --- FFmpeg Conversion Function (Verified Correct) ---
def process_file_ffmpeg(input_file, output_suffix, override_bitrate_mbps=None, resize_target=None):
    metadata = get_video_metadata(input_file)
    if not metadata: return
    
    gop_size = math.ceil(metadata['frame_rate'] / 2)
    
    if override_bitrate_mbps:
        print(f"   -> Using manual bitrate override: {override_bitrate_mbps} Mbps")
        bitrate_kbps = int(override_bitrate_mbps * 1000)
        settings = {
            "bitrate_str": f"{override_bitrate_mbps}M",
            "max_bitrate_str": f"{override_bitrate_mbps * 1.5}M",
            "bitrate_kbps": bitrate_kbps
        }
    else:
        settings = get_youtube_sdr_settings(metadata['height'], metadata['frame_rate'])
    
    directory = os.path.dirname(os.path.abspath(input_file))
    base, _ = os.path.splitext(os.path.basename(input_file))
    output_filename = f"{base}{output_suffix}.mp4"
    output_file = os.path.join(directory, output_filename)
    
    print(f"\n🎬 Processing with FFmpeg: {os.path.basename(input_file)}")
    
    # Build video filter chain
    filter_chain = [f"lut3d=file='{LUT_FILE_PATH.replace('\\', '/').replace(':', '\\:')}'"]
    if resize_target:
        w, h = metadata['width'], metadata['height']
        if w < h: # Portrait
            new_w = resize_target
            new_h = round((h * new_w) / w)
        else: # Landscape or Square
            new_h = resize_target
            new_w = round((w * new_h) / h)
        
        # Ensure dimensions are even
        new_w = round(new_w / 2) * 2
        new_h = round(new_h / 2) * 2
        print(f"   -> Resizing output to {new_w}x{new_h}")
        filter_chain.append(f"scale={new_w}:{new_h}")

    filter_chain.append("format=yuv420p")
    video_filter_str = ",".join(filter_chain)
    
    command = [
        "ffmpeg", "-y", "-hwaccel", "cuda", "-c:v", "av1_cuvid", "-i", input_file,
        "-vf", video_filter_str,
        "-c:v", "h264_nvenc", "-profile:v", "high", "-preset", "p7",
        "-b:v", settings['bitrate_str'], "-maxrate", settings['max_bitrate_str'],
        "-bufsize", f"{int(settings['bitrate_kbps'] * 2)}k",
        "-bf", "2", "-g", str(gop_size), "-closed_gop", "1",
        "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv",
        "-c:a", "aac", "-b:a", "384k", "-ac", "2", "-ar", "48000",
        "-movflags", "+faststart", output_file
    ]
    execute_command(command, input_file)

# --- NVEncC Conversion Function (Verified Correct) ---
def process_file_nvencc(input_file, output_suffix, override_bitrate_mbps=None, resize_target=None):
    metadata = get_video_metadata(input_file)
    if not metadata: return

    gop_size = math.ceil(metadata['frame_rate'] / 2)

    if override_bitrate_mbps:
        print(f"   -> Using manual bitrate override: {override_bitrate_mbps} Mbps")
        bitrate_kbps = int(override_bitrate_mbps * 1000)
        settings = {
            "bitrate_kbps": bitrate_kbps,
            "max_bitrate_kbps": int(bitrate_kbps * 1.5)
        }
    else:
        settings = get_youtube_sdr_settings(metadata['height'], metadata['frame_rate'])
    
    resize_flags = []
    if resize_target:
        w, h = metadata['width'], metadata['height']
        if w < h: # Portrait
            new_w = resize_target
            new_h = round((h * new_w) / w)
        else: # Landscape or Square
            new_h = resize_target
            new_w = round((w * new_h) / h)

        new_w = round(new_w / 2) * 2
        new_h = round(new_h / 2) * 2
        print(f"   -> Resizing output to {new_w}x{new_h}")
        resize_flags = ["--output-res", f"{new_w}x{new_h}"]

    directory = os.path.dirname(os.path.abspath(input_file))
    base, _ = os.path.splitext(os.path.basename(input_file))
    output_filename = f"{base}{output_suffix}.mp4"
    output_file = os.path.join(directory, output_filename)
    
    lut_basename = os.path.basename(LUT_FILE_PATH)
    temp_lut_path = os.path.join(directory, lut_basename)
    
    print(f"   -> Staging LUT file in video directory...")
    shutil.copy(LUT_FILE_PATH, temp_lut_path)
    
    print(f"\n🎬 Processing with NVEncC: {os.path.basename(input_file)}")
    
    colorspace_argument = f'lut3d={lut_basename},lut3d_interp=tetrahedral'
    
    command = [
        "nvencc64", "--avhw", "-i", input_file,
        *resize_flags,
        "--vpp-colorspace", colorspace_argument,
        "--codec", "h264", "--profile", "high", "--preset", "quality",
        "--output-csp", "yuv420",
        "--vbr", str(settings['bitrate_kbps']),
        "--max-bitrate", str(settings['max_bitrate_kbps']),
        "--vbv-bufsize", str(settings['bitrate_kbps'] * 2),
        "--gop-len", str(gop_size),
        "--bframes", "2",
        "--colormatrix", "bt709", "--colorprim", "bt709", "--transfer", "bt709", "--colorrange", "limited",
        "--audio-codec", "aac", "--audio-bitrate", "384", "--audio-samplerate", "48000",
        "--audio-stream", ":stereo",
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
    print("🚀 Executing command...")
    print("   " + subprocess.list2cmdline(command))
    try:
        result = subprocess.run(command, check=True, text=True, capture_output=True, encoding='utf-8')
        print(f"\n✅ Successfully converted: {os.path.basename(input_file_for_error_msg)}")
        if result.stdout: print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"\n❌ An error occurred during conversion of {os.path.basename(input_file_for_error_msg)}.")
        print(f"   The application exited with a non-zero error code: {e.returncode}.")
        print("\n--- NVEncC/FFmpeg Output ---")
        print(e.stderr)
        print("--------------------------")
    except Exception as e:
        print(f"An unexpected Python error occurred: {e}")

# --- Main Program Logic ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Batch convert HDR videos to SDR, optimized for YouTube uploads.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    encoder_group = parser.add_mutually_exclusive_group()
    encoder_group.add_argument("-f", "--ffmpeg", action='store_true', help="Use FFmpeg for conversion.")
    encoder_group.add_argument("-n", "--nvencc", action='store_true', help="Use NVEncC for conversion (default).")
    parser.add_argument("input_paths", nargs='+', help="One or more paths to video files, folders, or glob patterns.")
    parser.add_argument("--ext", default="mkv", help="File extension to process in folders.")
    parser.add_argument("--suffix", default=None, help="Suffix for output files (default: _SDR_NVENCC_YT or _SDR_FFMPEG_YT).")
    parser.add_argument("-b", "--bitrate", type=float, default=None, help="Override bitrate calculation. Specify target bitrate in Mbps (e.g., 20.5).")
    parser.add_argument("-r", "--resize", type=int, default=None, help="Resize output so the shortest side matches this value (e.g., 1080).")
    
    args = parser.parse_args()

    # Determine which engine and suffix to use
    if args.ffmpeg:
        encoder_name = "FFmpeg"
        if not check_dependencies(use_ffmpeg=True): sys.exit(1)
        suffix = args.suffix if args.suffix is not None else "_SDR_FFMPEG_YT"
        process_function = lambda video_file, suffix: process_file_ffmpeg(video_file, suffix, args.bitrate, args.resize)
    else:
        encoder_name = "NVEncC"
        if not check_dependencies(use_ffmpeg=False): sys.exit(1)
        suffix = args.suffix if args.suffix is not None else "_SDR_NVENCC_YT"
        process_function = lambda video_file, suffix: process_file_nvencc(video_file, suffix, args.bitrate, args.resize)

    if not os.path.isfile(LUT_FILE_PATH):
        print(f"❌ Critical Error: The LUT file was not found at:\n   {LUT_FILE_PATH}")
        sys.exit(1)
        
    # Discover files to process
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

    # Process each file
    for video_file in unique_files:
        process_function(video_file, suffix)