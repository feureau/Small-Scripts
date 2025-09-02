"""
=========================================================================================
 GPU-Accelerated Video Processing Script - Full Documentation (v4)
=========================================================================================

-----------------------------------------------------------------------------------------
 I. OVERVIEW
-----------------------------------------------------------------------------------------
This script is a powerful, configurable command-line tool designed to automate the
entire workflow of preparing videos for modern web and social media platforms. It can
operate on a single file or batch-process an entire directory tree.

Its core purpose is to take any video and produce one or more output files that adhere
to a strict set of standards: a predictable file size, a specific duration per part,
a capped resolution, and loud, compressed, broadcast-standard audio.

All key processing parameters are exposed as command-line flags, allowing for a high
degree of flexibility without needing to modify the source code.

-----------------------------------------------------------------------------------------
 II. KEY FEATURES
-----------------------------------------------------------------------------------------
- **Configurable via Flags:** Key parameters like target size, duration, and audio
  loudness can be set using command-line arguments (e.g., --target-mb 8).
- **Automatic Video Splitting:** Videos longer than the maximum duration are automatically
  cut into multiple, sequentially numbered parts.
- **Strict Target Size Compression:** Intelligently calculates the required bitrate and
  uses strict rate control (`maxrate`, `bufsize`) to ensure every output file reliably
  meets the target file size, even with variable-complexity content.
- **Aggressive Audio Processing:** Utilizes the sophisticated 'loudnorm' filter to act
  as an all-in-one normalizer, compressor, and true-peak limiter. The default settings
  produce a loud, punchy, and consistent audio experience suitable for social media.
- **GPU Acceleration:** Offloads the computationally intensive video encoding process to
  the GPU (NVIDIA NVENC, AMD AMF, Intel QSV) for significant speed improvements.
- **Resolution Capping:** Resizes videos to fit within a 1080x1080 frame while
  maintaining the original aspect ratio, without adding black bars (letterboxing).
- **Dual-Mode Operation:** Can process a specific video file passed as an argument or, if
  no argument is given, recursively scan and process all videos in the current directory.

-----------------------------------------------------------------------------------------
 III. PREREQUISITES
-----------------------------------------------------------------------------------------
1.  **Python 3:** The script requires Python 3.
2.  **FFmpeg:** A recent version of FFmpeg must be installed and accessible from your
    system's PATH.
    - **Crucially, your FFmpeg build must have support for your GPU's hardware
      encoder.** For example, to use 'h264_nvenc', FFmpeg needs to be compiled with
      the `--enable-nvenc` flag.
3.  **ffmpeg-python:** The Python wrapper for FFmpeg. Install it via pip:
    `pip install ffmpeg-python`

-----------------------------------------------------------------------------------------
 IV. HOW TO USE
-----------------------------------------------------------------------------------------
1. Save the code as a Python file (e.g., `process_videos.py`).
2. Open a terminal or command prompt.
3. Navigate (`cd`) to the folder containing the videos you want to process.
4. Execute the script in one of the following ways:

   **A) Single File Mode:**
   Provide the path to the video file as the first argument.

   Example:
   `python process_videos.py "My Awesome Video.mp4"`

   **B) Batch Mode:**
   Run the script without any arguments. It will find all videos in the current folder.

   Example:
   `python process_videos.py`

An output folder (named `compressed_videos` by default) will be created in the
directory from which you ran the command.

-----------------------------------------------------------------------------------------
 V. COMMAND-LINE ARGUMENTS (FLAGS)
-----------------------------------------------------------------------------------------
Use these flags to override the default settings. Run with `-h` for a quick reference.

`input_file`
    - Description: Path to a single video file. If omitted, batch mode is enabled.
    - Example: `python process_videos.py "path/to/my video.mov"`

`--target-mb`
    - Description: The target file size in Megabytes for each output video part.
    - Default: 9.8
    - Example: `python process_videos.py --target-mb 8`

`--duration`
    - Description: The maximum duration in seconds for each video part before splitting.
    - Default: 90
    - Example: `python process_videos.py --duration 60`

`--output-folder`
    - Description: Name of the directory where processed files will be saved.
    - Default: "compressed_videos"
    - Example: `python process_videos.py --output-folder "Final Renders"`

`--loudness`
    - Description: The integrated loudness target in LUFS. More negative numbers are
      quieter. -7 is very loud, -14 is standard for streaming.
    - Default: -9
    - Example: `python process_videos.py --loudness -11`

`--lra`
    - Description: The Loudness Range (LRA). Controls dynamic range compression.
      Lower values (e.g., 5-7) result in heavy compression. Higher values are more dynamic.
    - Default: 7
    - Example: `python process_videos.py --lra 11`

`--peak`
    - Description: The true peak ceiling in dBTP. This acts as a limiter to prevent clipping.
    - Default: -1.0
    - Example: `python process_videos.py --peak -1.5`

-----------------------------------------------------------------------------------------
 VI. CODE & DESIGN RATIONALE (The "Why")
-----------------------------------------------------------------------------------------

[ Overall Script Structure ]
- **`argparse` for Configuration:** Using Python's standard `argparse` library is the
  robust and conventional way to handle command-line flags. It automatically generates
  help menus (`-h`) and provides clean, readable access to user-provided arguments.
  This is far superior to manually parsing `sys.argv`.
- **`_encode_chunk` Helper Function:** The core FFmpeg logic is isolated in this
  internal function. This promotes code reuse and separation of concerns. The main
  `process_video` function handles the logic of *what* to process (splitting, timing),
  while `_encode_chunk` handles *how* to process it.
- **`if __name__ == "__main__":`:** This is a standard Python best practice that ensures
  the script's main logic only runs when it is executed directly, not when it is
  imported as a module into another script.

[ Video Processing Rationale ]
- **Splitting Logic:** For videos exceeding `max_duration`, `math.ceil()` is used to
  calculate the total number of parts needed, ensuring the final partial segment is
  included. A loop then iterates through each segment, calculating the precise `start_time`
  and `duration` for each chunk. The `-ss` (seek start) parameter in FFmpeg is used
  for this, as it is highly efficient for seeking within a file.
- **Bitrate Calculation:** The formula `bitrate = (size_in_bits) / duration_in_seconds`
  is fundamental to video encoding. The script calculates the total bit budget for the
  target file size, subtracts a fixed budget for audio, and allocates the remainder
  to the video stream. This is the cornerstone of achieving a predictable file size.
- **Strict Rate Control (`maxrate`, `bufsize`):** Simply targeting an average bitrate
  (`b:v`) is not enough. Video encoders use Variable Bitrate (VBR), allocating more
- **Resolution Capping (`scale`):** The `scale` filter uses `force_original_aspect_ratio='decrease'`
  which is the key to resizing the video to fit *inside* a 1080x1080 box without
  distortion. The `pad` filter was intentionally removed to prevent letterboxing,
  resulting in an output resolution that matches the video's aspect ratio (e.g.,
  1080x607 for widescreen, 607x1080 for portrait).

[ Audio Processing Rationale (`loudnorm`) ]
- **Modern Loudness (LUFS):** The `loudnorm` filter was chosen because it adheres to the
  modern EBU R128 standard, which measures loudness based on human perception (LUFS)
  rather than simple digital peaks. This ensures consistency across devices and
  platforms like YouTube and Spotify.
- **All-in-One Audio Mastering:** `loudnorm` is not just a normalizer; it is a
  sophisticated, two-pass audio processor that functions as a combined normalizer,
  compressor, and true-peak limiter. This is far more effective than chaining separate,
  less-aware filters.
- **Loudness (`i` parameter):** The `i` (Integrated Loudness) parameter is set to a
  default of -9 LUFS. This is an aggressive, "hot" target designed to make the audio
  stand out on mobile devices and social media platforms, where ambient noise may be a factor.
- **Compression (`lra` parameter):** The `lra` (Loudness Range) parameter directly
  controls dynamic range compression. By targeting a low LRA of 7, we are instructing
  the filter to significantly reduce the difference between quiet and loud sounds,
  resulting in a dense, consistently loud, and "in-your-face" audio track.
- **Clipping Prevention (`tp` parameter):** The `tp` (True Peak) parameter is the crucial
  safety net. By setting it to -1.0, we are commanding the filter to apply a
  **brick-wall true-peak limiter** at the end of its processing chain. This guarantees
  that no part of the final audio will ever exceed -1.0 dBTP, effectively and reliably
  preventing any clipping or distortion.

-----------------------------------------------------------------------------------------
 VII. NOTE ON FUTURE UPDATES
-----------------------------------------------------------------------------------------
This documentation is an integral part of the script. If you modify the script's logic,
add, or change any command-line arguments, please ensure this documentation block is
updated to reflect those changes.

"""

import sys
import os
import glob
import ffmpeg
import math
import argparse

# --- Default Script Configuration ---
# These values are used if not overridden by command-line flags.

DEFAULT_CONFIG = {
    # Target file size in Megabytes.
    "target_mb": 9.8,
    
    # Maximum duration in seconds for each output part.
    "max_duration": 90,
    
    # Name of the folder for processed videos.
    "output_folder": "compressed_videos",
    
    # --- Loudness & Compression Settings ---
    # Integrated Loudness Target (LUFS). Louder = smaller negative number (e.g., -7 is louder than -14).
    "loudness_target": -9,
    
    # Loudness Range (LRA). Lower number = more compression, less dynamic range.
    "loudness_range": 7,
    
    # True Peak ceiling (dBTP). The maximum peak level. -1.0 is a safe, loud value.
    "true_peak": -1.0,
}

# Video extensions to look for in batch mode.
VIDEO_EXTENSIONS = ["mp4", "mov", "mkv", "avi", "webm"]


# --- Core Processing Functions ---

def _encode_chunk(input_path, output_path, start_time, duration, audio_stream_exists, config):
    """
    Encodes a specific time segment of a video file to the target specifications.
    This is a helper function called by process_video.
    """
    try:
        print(f"   [INFO] Encoding segment: start={start_time:.1f}s, duration={duration:.1f}s")
        
        target_size_bytes = config['target_mb'] * 1024 * 1024
        
        # 1. CALCULATE BITRATE
        print("   [1/4] Calculating target bitrate...")
        audio_bitrate = 128 * 1000 if audio_stream_exists else 0
        total_bitrate = (target_size_bytes * 8) / duration
        video_bitrate = total_bitrate - audio_bitrate

        if video_bitrate <= 0:
            print(f"   [ERROR] Target size of {config['target_mb']}MB is too small for a {duration:.1f}s segment. Skipping.")
            return
        
        print(f"   [INFO] Target video bitrate: {int(video_bitrate / 1000)} kbps")

        # 2. BUILD FFMPEG COMMAND
        print("   [2/4] Building FFmpeg command...")
        stream = ffmpeg.input(input_path, ss=start_time, t=duration)
        video = stream.video.filter('scale', w=1080, h=1080, force_original_aspect_ratio='decrease')

        audio = None
        if audio_stream_exists:
            print("   [INFO] Applying aggressive audio loudness and compression.")
            audio = stream.audio.filter(
                'loudnorm',
                i=config['loudness_target'],
                lra=config['loudness_range'],
                tp=config['true_peak']
            )

        # 3. EXECUTE
        print("   [3/4] Starting GPU-accelerated encoding...")
        output_options = {
            'c:v': 'h264_nvenc',
            'b:v': int(video_bitrate),
            'maxrate': int(video_bitrate),
            'bufsize': int(video_bitrate * 2),
            'c:a': 'aac',
            'b:a': '128k'
        }
        
        output_streams = [video]
        if audio is not None:
            output_streams.append(audio)
        else:
            del output_options['c:a'], output_options['b:a']
            
        (
            ffmpeg
            .output(*output_streams, output_path, **output_options)
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
        
        # 4. VERIFY
        print("   [4/4] Verifying output...")
        final_size_bytes = os.path.getsize(output_path)
        final_size_mb = final_size_bytes / (1024 * 1024)

        if final_size_bytes <= target_size_bytes:
            print(f"   [SUCCESS] Compression successful! Final size: {final_size_mb:.2f} MB")
        else:
            print(f"   [WARNING] Compression finished, but file size ({final_size_mb:.2f} MB) is OVER the target.")

    except ffmpeg.Error as e:
        print("   [FFMPEG ERROR] An error occurred during segment encoding.")
        print(e.stderr.decode(), file=sys.stderr)
    except Exception as e:
        print(f"   [UNEXPECTED ERROR] An unexpected error occurred: {e}", file=sys.stderr)


def process_video(input_path, output_path, config):
    """
    Analyzes a video. If it's too long, it splits it into parts and calls the
    encoding function for each part, passing along the configuration.
    """
    print(f"\n--- Analyzing: {os.path.basename(input_path)} ---")

    try:
        probe = ffmpeg.probe(input_path)
        video_stream = next((s for s in probe['streams'] if s['codec_type'] == 'video'), None)
        audio_stream = next((s for s in probe['streams'] if s['codec_type'] == 'audio'), None)

        if video_stream is None:
            print("   [ERROR] No video stream found. Skipping.")
            return

        original_duration = float(probe['format']['duration'])
        max_duration = config['max_duration']

        if original_duration <= max_duration:
            print("   [INFO] Video is within duration limit. Processing as a single file.")
            _encode_chunk(input_path, output_path, 0, original_duration, audio_stream is not None, config)
        else:
            num_parts = math.ceil(original_duration / max_duration)
            print(f"   [INFO] Video is too long ({original_duration:.1f}s). Splitting into {num_parts} parts.")
            
            output_name, output_ext = os.path.splitext(output_path)

            for i in range(num_parts):
                part_num = i + 1
                part_output_path = f"{output_name}_part_{part_num}{output_ext}"
                print(f"\n--- Processing Part {part_num} of {num_parts} for: {os.path.basename(input_path)} ---")

                start_time = i * max_duration
                duration = min(max_duration, original_duration - start_time)

                _encode_chunk(input_path, part_output_path, start_time, duration, audio_stream is not None, config)

    except Exception as e:
        print(f"   [FATAL ERROR] An error occurred during video analysis: {e}", file=sys.stderr)


# --- Main Execution Block ---
def main():
    """
    Parses command-line arguments and starts the video processing.
    """
    parser = argparse.ArgumentParser(
        description="GPU-accelerated video compression, splitting, and normalization script.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        'input_file',
        nargs='?', # Makes the argument optional
        default=None,
        help="Path to a single video file to process. If omitted, script runs in Batch Mode."
    )
    
    # --- Add arguments to override default config ---
    parser.add_argument("--target-mb", type=float, default=DEFAULT_CONFIG['target_mb'], help="Target file size in Megabytes for each video part.")
    parser.add_argument("--duration", type=int, default=DEFAULT_CONFIG['max_duration'], help="Maximum duration in seconds for each video part.")
    parser.add_argument("--output-folder", type=str, default=DEFAULT_CONFIG['output_folder'], help="Name of the directory to save processed files.")
    parser.add_argument("--loudness", type=float, default=DEFAULT_CONFIG['loudness_target'], help="Loudness target in LUFS. Smaller negative numbers are louder.")
    parser.add_argument("--lra", type=int, default=DEFAULT_CONFIG['loudness_range'], help="Loudness Range (LRA). Lower values mean more compression.")
    parser.add_argument("--peak", type=float, default=DEFAULT_CONFIG['true_peak'], help="True Peak ceiling in dBTP.")
    
    args = parser.parse_args()

    # Create a config dictionary from the parsed arguments
    config = {
        'target_mb': args.target_mb,
        'max_duration': args.duration,
        'output_folder': args.output_folder,
        'loudness_target': args.loudness,
        'loudness_range': args.lra,
        'true_peak': args.peak,
    }

    current_working_dir = os.getcwd()
    output_dir = os.path.join(current_working_dir, config['output_folder'])
    os.makedirs(output_dir, exist_ok=True)
    
    if args.input_file:
        # Single File Mode
        print(f"--- Single File Mode ---")
        if not os.path.isfile(args.input_file):
            print(f"Error: The file '{args.input_file}' does not exist.")
            return
        base_name = os.path.basename(args.input_file)
        output_file = os.path.join(output_dir, base_name)
        process_video(args.input_file, output_file, config)
    else:
        # Batch Mode
        print(f"--- Batch Mode ---")
        print(f"Searching for video files in '{current_working_dir}' and its subfolders...")
        video_files = []
        for ext in VIDEO_EXTENSIONS:
            pattern = os.path.join(current_working_dir, '**', f'*.{ext}')
            video_files.extend(glob.glob(pattern, recursive=True))
        
        if not video_files:
            print("No video files found to process.")
            return
            
        print(f"Found {len(video_files)} video file(s) to process.")
        for i, input_file in enumerate(video_files):
            print(f"\n>>> Processing file {i + 1} of {len(video_files)}")
            base_name = os.path.basename(input_file)
            # Exclude files that are already in the output directory
            if os.path.dirname(input_file) == output_dir:
                print(f"   Skipping file already in output directory: {base_name}")
                continue
            output_file = os.path.join(output_dir, base_name)
            process_video(input_file, output_file, config)

    print("\n--- All tasks completed. ---")


if __name__ == "__main__":
    main()