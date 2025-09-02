"""
=========================================================================================
 GPU-Accelerated Video Compression and Normalization Script
=========================================================================================

-----------------------------------------------------------------------------------------
 I. OVERVIEW
-----------------------------------------------------------------------------------------
This script is a powerful command-line tool designed to automate the process of video
compression. It can operate on a single file or batch-process an entire directory tree.
The primary goal is to produce video files that adhere to a strict set of modern web
and social media standards: a file size under 10MB, a square 1080x1080 resolution
(while preserving the original aspect ratio), a maximum duration, and normalized audio.

The script leverages the industry-standard FFmpeg library, but uses the `ffmpeg-python`
wrapper. This allows for more readable, maintainable, and robust command construction
compared to building raw command-line strings, which can become complex and error-prone.

-----------------------------------------------------------------------------------------
 II. KEY FEATURES
-----------------------------------------------------------------------------------------
- **Target Size Compression:** Intelligently calculates the exact video bitrate needed
  to ensure the final file size is under a specified target (e.g., 10MB).
- **GPU Acceleration:** Offloads the computationally intensive video encoding process to
  the GPU (NVIDIA NVENC, AMD AMF, Intel QSV) for significant speed improvements over
  CPU encoding.
- **Resolution Capping & Padding:** Resizes videos to fit within a 1080x1080 frame
  while maintaining the original aspect ratio by adding black bars (letterboxing/pillarboxing).
  This is a common requirement for social media platforms like Instagram.
- **Duration Limiting:** Automatically trims videos to a maximum specified length.
- **Audio Normalization:** Uses the 'loudnorm' filter to adjust audio to a standard
  loudness level (EBU R128). This prevents audio from being too quiet or clipping,
  ensuring a consistent listening experience.
- **Dual-Mode Operation:**
    - **Single File Mode:** Process a specific video file passed as a command-line argument.
    - **Batch Mode:** If no argument is given, it recursively scans the current
      directory and all subdirectories for video files and processes them all.
- **Robust Path Handling:** Can be executed from any directory, correctly handling
  relative paths and creating a dedicated output folder in the current working directory.

-----------------------------------------------------------------------------------------
 III. PREREQUISITES
-----------------------------------------------------------------------------------------
1.  **Python 3:** The script is written in Python 3.
2.  **FFmpeg:** A recent version of FFmpeg must be installed and accessible from your
    system's PATH.
    - **Crucially, your FFmpeg build must have support for your GPU's hardware
      encoder.** For example, to use 'h264_nvenc', FFmpeg needs to be compiled with
      the `--enable-nvenc` flag. Pre-built static versions often include this.
3.  **ffmpeg-python:** The Python wrapper for FFmpeg. Install it via pip:
    `pip install ffmpeg-python`

-----------------------------------------------------------------------------------------
 IV. HOW TO USE
-----------------------------------------------------------------------------------------
1. Save this code as a Python file (e.g., `compress_video.py`).
2. Open a terminal or command prompt.
3. Navigate (`cd`) to the folder containing the videos you want to process.
4. Execute the script in one of the following ways:

   **A) Single File Mode:**
   Provide the path to the video file as an argument. The script's location can be
   an absolute or relative path.

   Example:
   `python C:/path/to/compress_video.py "My Video.mp4"`

   **B) Batch Mode:**
   Run the script without any arguments. It will automatically find and process all
   videos in the current folder and its subfolders.

   Example:
   `python C:/path/to/compress_video.py`

An output folder named `compressed_videos` will be created in the directory from
which you ran the command.

-----------------------------------------------------------------------------------------
 V. SCRIPT CONFIGURATION (Global Variables)
-----------------------------------------------------------------------------------------
- **TARGET_MB:** The target file size in megabytes. It's set slightly below 10MB
  (e.g., 9.8MB) to create a safety margin. This accounts for minor variations in how
  muxing and metadata can affect the final file size.
- **MAX_DURATION_SECONDS:** The maximum length for any output video, in seconds.
- **OUTPUT_FOLDER_NAME:** The name of the directory where processed files will be saved.
- **VIDEO_EXTENSIONS:** A list of file extensions the script will search for in Batch Mode.

-----------------------------------------------------------------------------------------
 VI. CODE & DESIGN RATIONALE
-----------------------------------------------------------------------------------------

[ `process_video` function ]
This is the core engine of the script. It was designed as a separate function to be
reusable, whether called once (Single File Mode) or in a loop (Batch Mode).

- **Step 1: Analysis (`ffmpeg.probe`)**
  The script MUST first gather metadata. Without knowing the video's duration, we cannot
  calculate the bitrate needed to hit our target file size. `ffmpeg.probe` is used for
  this, as it provides a structured JSON/dictionary output of all stream information.
  `next(...)` is a Pythonic and efficient way to find the first video/audio stream.

- **Step 2: Duration Check (`min`)**
  Using `min(original_duration, MAX_DURATION_SECONDS)` is a concise and readable way to
  enforce the time limit. The result is stored in `processing_duration`, which becomes
  the basis for all subsequent calculations and the `-t` trim parameter for FFmpeg.

- **Step 3: Bitrate Calculation**
  This is the most critical calculation. The formula `bitrate = (size * 8) / duration`
  is fundamental to video encoding.
  - The script first calculates the *total* bitrate budget for the entire file.
  - It then subtracts a fixed budget for the audio stream (`audio_bitrate`).
  - The remainder is the budget allocated to the `video_bitrate`. This is why targeting
    a file size is a "two-pass" conceptual process: first calculate, then encode.

- **Step 4: FFmpeg Graph Construction**
  - **Video Chain (`.filter('scale', ...).filter('pad', ...)`):**
    A two-step filtering process is used to handle resolution.
    1. `scale`: The `force_original_aspect_ratio='decrease'` parameter is key. It scales
       the video until it fits *inside* the 1080x1080 box without distortion. For a
       1920x1080 video, it becomes 1080x607. For a 1080x1920 video, it becomes 607x1080.
    2. `pad`: This filter then takes the scaled video and adds black bars to fill the
       remaining space to reach the final 1080x1080 dimensions. The `x` and `y`
       expressions `(ow-iw)/2` and `(oh-ih)/2` mathematically center the video.

  - **Audio Chain (`.filter('loudnorm')`)**
    Audio normalization is vital for a good user experience. The `loudnorm` filter was
    chosen over older methods (like `normalize`) because it is based on modern loudness
    standards (EBU R128), which perceive loudness more like the human ear. It prevents
    both clipping and overly quiet audio more effectively. It is applied conditionally,
    only if an audio stream is detected.

- **Step 5: Execution (`.run`)**
  The `.run()` method executes the graph.
  - `c:v` is set to `h264_nvenc` for NVIDIA GPUs. This is the most common choice, but
    the documentation notes alternatives for AMD (`h264_amf`) and Intel (`h264_qsv`).
  - `overwrite_output()` is used for convenience, especially in batch processing, so
    re-running the script doesn't fail on existing files.
  - `capture_stdout/stderr` prevents FFmpeg's verbose logs from spamming the console
    and allows for programmatic error handling.

- **Step 6: Verification (`os.path.getsize`)**
  A final check is performed to confirm the file size. This provides clear feedback to
  the user about the success of the operation.

[ `main` function & Entry Point ]
This function acts as the script's controller.

- **Path Handling (`os.getcwd`, `os.path.join`):** The decision to use the "current
  working directory" (`os.getcwd()`) as the base for the output folder makes the script's
  behavior predictable and user-friendly. The user knows the output will always appear
  relative to where they are in the terminal, not relative to the script's location.

- **Mode Selection (`sys.argv`):** Checking `len(sys.argv)` is the standard Python
  idiom for parsing command-line arguments. It's a simple but effective way to switch
  between the script's two primary modes of operation.

- **Batch Discovery (`glob`):** For Batch Mode, `glob` is the ideal tool. The pattern
  `'**/*.ext'` combined with the `recursive=True` flag is a modern and powerful
  feature that simplifies searching through nested directories, making the script far
  more useful than if it only scanned a single folder.

- **`if __name__ == "__main__":`:** This is a standard Python best practice. It ensures
  that the `main()` function is only called when the script is executed directly by the
  user, not if it were to be imported as a module into another Python script.

"""

import sys
import os
import glob
import ffmpeg

# --- Script Configuration ---

# Target file size in Megabytes. We use a slightly smaller value for a safety margin.
TARGET_MB = 9.8
TARGET_SIZE_BYTES = TARGET_MB * 1024 * 1024

# Maximum allowed video duration in seconds. (1.5 minutes = 90 seconds)
MAX_DURATION_SECONDS = 90

# The name of the folder where compressed videos will be saved.
OUTPUT_FOLDER_NAME = "compressed_videos"

# Video extensions to look for in batch mode.
VIDEO_EXTENSIONS = ["mp4", "mov", "mkv", "avi", "webm"]

# --- Core Processing Function ---

def process_video(input_path, output_path):
    """
    Analyzes and compresses a single video file to meet specific requirements
    using GPU-accelerated ffmpeg. Audio will be normalized.
    """
    print(f"\n--- Processing: {os.path.basename(input_path)} ---")

    try:
        # 1. ANALYZE: Probe the video file for its metadata.
        print("   [1/5] Analyzing video properties...")
        probe = ffmpeg.probe(input_path)
        video_stream = next((s for s in probe['streams'] if s['codec_type'] == 'video'), None)
        audio_stream = next((s for s in probe['streams'] if s['codec_type'] == 'audio'), None)

        if video_stream is None:
            print("   [ERROR] No video stream found. Skipping.")
            return

        original_duration = float(probe['format']['duration'])

        # 2. DURATION CHECK: Trim video if it exceeds the maximum allowed length.
        processing_duration = min(original_duration, MAX_DURATION_SECONDS)
        if original_duration > MAX_DURATION_SECONDS:
            print(f"   [INFO] Video is too long ({original_duration:.1f}s). Trimming to {MAX_DURATION_SECONDS}s.")
        
        # 3. CALCULATE BITRATE: Determine the required video bitrate to meet the target size.
        print("   [2/5] Calculating target bitrate...")
        
        # Standard audio bitrate (e.g., 128kbps).
        audio_bitrate = 128 * 1000  # in bits per second
        if audio_stream is None:
            audio_bitrate = 0 # No audio stream present

        # Calculate the total bitrate needed to hit the target file size.
        total_bitrate = (TARGET_SIZE_BYTES * 8) / processing_duration
        
        # Subtract the audio bitrate to find the video bitrate budget.
        video_bitrate = total_bitrate - audio_bitrate

        if video_bitrate <= 0:
            print(f"   [ERROR] Target size of {TARGET_MB}MB is too small for a {processing_duration:.1f}s video. Skipping.")
            return
        
        print(f"   [INFO] Target video bitrate: {int(video_bitrate / 1000)} kbps")

        # 4. BUILD FFMPEG COMMAND: Construct the processing graph.
        print("   [3/5] Building FFmpeg command...")
        
        stream = ffmpeg.input(input_path, t=processing_duration)
        
        video = stream.video.filter('scale', w=1080, h=1080, force_original_aspect_ratio='decrease') \
                           .filter('pad', w=1080, h=1080, x='(ow-iw)/2', y='(oh-ih)/2', color='black')

        # If an audio stream exists, apply the loudness normalization filter.
        audio = None
        if audio_stream:
            print("   [INFO] Audio normalization filter enabled.") # <-- ADDED
            audio = stream.audio.filter('loudnorm') # <-- MODIFIED

        # 5. EXECUTE: Run the command.
        print("   [4/5] Starting GPU-accelerated encoding...")
        
        # Note: Change 'h264_nvenc' if you use a different GPU
        # AMD: 'h264_amf'
        # Intel: 'h264_qsv'
        output_options = {
            'c:v': 'h264_nvenc',  
            'b:v': int(video_bitrate),
            'c:a': 'aac',
            'b:a': '128k'
        }
        
        # If there's no audio, we pass different arguments to the output function
        if audio is None:
            del output_options['c:a']
            del output_options['b:a']
            output_streams = [video]
        else:
            output_streams = [video, audio]
            
        (
            ffmpeg
            .output(*output_streams, output_path, **output_options) # <-- MODIFIED
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
        
        # 6. VERIFY: Check the final file size.
        print("   [5/5] Verifying output...")
        final_size_bytes = os.path.getsize(output_path)
        final_size_mb = final_size_bytes / (1024 * 1024)

        if final_size_bytes <= TARGET_SIZE_BYTES:
            print(f"   [SUCCESS] Compression successful! Final size: {final_size_mb:.2f} MB")
        else:
            print(f"   [WARNING] Compression finished, but file size ({final_size_mb:.2f} MB) is over the target.")

    except ffmpeg.Error as e:
        print("   [FFMPEG ERROR] An error occurred during processing.")
        print(e.stderr.decode(), file=sys.stderr)
    except Exception as e:
        print(f"   [UNEXPECTED ERROR] An unexpected error occurred: {e}", file=sys.stderr)


# --- Main Execution Block ---
def main():
    """
    Main function to handle command-line arguments and start the processing.
    """
    current_working_dir = os.getcwd()
    output_dir = os.path.join(current_working_dir, OUTPUT_FOLDER_NAME)
    os.makedirs(output_dir, exist_ok=True)
    
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        print(f"--- Single File Mode ---")
        if not os.path.isfile(input_file):
            print(f"Error: The file '{input_file}' does not exist.")
            return
        base_name = os.path.basename(input_file)
        output_file = os.path.join(output_dir, base_name)
        process_video(input_file, output_file)
    else:
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
            output_file = os.path.join(output_dir, base_name)
            process_video(input_file, output_file)

    print("\n--- All tasks completed. ---")


if __name__ == "__main__":
    main()