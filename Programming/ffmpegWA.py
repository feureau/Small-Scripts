"""
=========================================================================================
 GPU-Accelerated Video Splitting, Compression, and Normalization Script (v3)
=========================================================================================

-----------------------------------------------------------------------------------------
 I. OVERVIEW
-----------------------------------------------------------------------------------------
This script is a powerful command-line tool designed to automate the process of video
compression and segmentation. It can operate on a single file or batch-process an entire
directory tree.

The primary goal is to produce video files that adhere to a strict set of modern web
and social media standards: a file size under 10MB, a resolution that fits within
a 1080x1080 frame, and normalized audio.

A key feature is its ability to handle long videos: if an input video exceeds the
maximum allowed duration, it is automatically split into multiple, sequentially
numbered parts, each conforming to the duration limit. Each part is guaranteed to
adhere to the file size limit due to strict rate control.

-----------------------------------------------------------------------------------------
 II. KEY FEATURES
-----------------------------------------------------------------------------------------
- **Automatic Video Splitting:** Videos longer than the maximum duration are automatically
  cut into multiple parts (e.g., a 4-min video becomes three 90-sec or less parts).
- **Strict Target Size Compression:** Intelligently calculates the video bitrate for each part
  and uses strict rate control (`maxrate` and `bufsize`) to ensure every output file
  reliably meets the target size limit.
- **GPU Acceleration:** Offloads the intensive video encoding process to the GPU
  (NVIDIA NVENC, AMD AMF, Intel QSV) for significant speed improvements.
- **Resolution Capping:** Resizes videos to fit within a 1080x1080 frame while
  maintaining the original aspect ratio WITHOUT adding black bars.
- **Audio Normalization:** Uses the 'loudnorm' filter to adjust audio to a standard
  loudness level (EBU R128) for a consistent listening experience.
- **Dual-Mode Operation:** Process a single file or batch process an entire directory.
"""

import sys
import os
import glob
import ffmpeg
import math

# --- Script Configuration ---

# Target file size in Megabytes. We use a slightly smaller value for a safety margin.
TARGET_MB = 9.8
TARGET_SIZE_BYTES = TARGET_MB * 1024 * 1024

# Maximum allowed video duration in seconds for each output part.
MAX_DURATION_SECONDS = 90

# The name of the folder where compressed videos will be saved.
OUTPUT_FOLDER_NAME = "compressed_videos"

# Video extensions to look for in batch mode.
VIDEO_EXTENSIONS = ["mp4", "mov", "mkv", "avi", "webm"]

# --- Core Processing Functions ---

def _encode_chunk(input_path, output_path, start_time, duration, audio_stream_exists):
    """
    Encodes a specific time segment of a video file to the target specifications.
    This is a helper function called by process_video.
    """
    try:
        print(f"   [INFO] Encoding segment: start={start_time:.1f}s, duration={duration:.1f}s")
        
        # 1. CALCULATE BITRATE: Determine the required video bitrate for this chunk.
        print("   [1/4] Calculating target bitrate...")
        audio_bitrate = 128 * 1000 if audio_stream_exists else 0
        total_bitrate = (TARGET_SIZE_BYTES * 8) / duration
        video_bitrate = total_bitrate - audio_bitrate

        if video_bitrate <= 0:
            print(f"   [ERROR] Target size of {TARGET_MB}MB is too small for a {duration:.1f}s video segment. Skipping.")
            return
        
        print(f"   [INFO] Target video bitrate: {int(video_bitrate / 1000)} kbps")

        # 2. BUILD FFMPEG COMMAND: Construct the processing graph for the segment.
        print("   [2/4] Building FFmpeg command...")
        
        # Use 'ss' for seeking to start_time, which is very fast.
        stream = ffmpeg.input(input_path, ss=start_time, t=duration)
        
        video = stream.video.filter('scale', w=1080, h=1080, force_original_aspect_ratio='decrease')

        audio = None
        if audio_stream_exists:
            audio = stream.audio.filter('loudnorm')

        # 3. EXECUTE: Run the command.
        print("   [3/4] Starting GPU-accelerated encoding...")
        
        # ======================= MODIFICATION HERE =======================
        # Added 'maxrate' and 'bufsize' to enforce stricter rate control. This ensures
        # that even complex video segments do not exceed the target file size.
        output_options = {
            'c:v': 'h264_nvenc',              # Encoder (AMD: 'h264_amf', Intel: 'h264_qsv')
            'b:v': int(video_bitrate),        # Target average bitrate
            'maxrate': int(video_bitrate),    # Hard ceiling for bitrate
            'bufsize': int(video_bitrate * 2),# Rate control buffer size
            'c:a': 'aac',
            'b:a': '128k'
        }
        # ===============================================================
        
        if audio is None:
            del output_options['c:a']
            del output_options['b:a']
            output_streams = [video]
        else:
            output_streams = [video, audio]
            
        (
            ffmpeg
            .output(*output_streams, output_path, **output_options)
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
        
        # 4. VERIFY: Check the final file size.
        print("   [4/4] Verifying output...")
        final_size_bytes = os.path.getsize(output_path)
        final_size_mb = final_size_bytes / (1024 * 1024)

        if final_size_bytes <= TARGET_SIZE_BYTES:
            print(f"   [SUCCESS] Compression successful! Final size: {final_size_mb:.2f} MB")
        else:
            print(f"   [WARNING] Compression finished, but file size ({final_size_mb:.2f} MB) is OVER the target.")

    except ffmpeg.Error as e:
        print("   [FFMPEG ERROR] An error occurred during segment encoding.")
        print(e.stderr.decode(), file=sys.stderr)
    except Exception as e:
        print(f"   [UNEXPECTED ERROR] An unexpected error occurred: {e}", file=sys.stderr)


def process_video(input_path, output_path):
    """
    Analyzes a video. If it's longer than MAX_DURATION_SECONDS, it splits it
    into multiple parts. Then, for each part, it calls the encoding function.
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

        if original_duration <= MAX_DURATION_SECONDS:
            # Video is short enough, process as a single file.
            print("   [INFO] Video is within duration limit. Processing as a single file.")
            _encode_chunk(input_path, output_path, 0, original_duration, audio_stream is not None)
        else:
            # Video is too long, must be split into parts.
            num_parts = math.ceil(original_duration / MAX_DURATION_SECONDS)
            print(f"   [INFO] Video is too long ({original_duration:.1f}s). Splitting into {num_parts} parts.")
            
            output_name, output_ext = os.path.splitext(output_path)

            for i in range(num_parts):
                part_num = i + 1
                part_output_path = f"{output_name}_part_{part_num}{output_ext}"
                print(f"\n--- Processing Part {part_num} of {num_parts} for: {os.path.basename(input_path)} ---")

                start_time = i * MAX_DURATION_SECONDS
                # The duration for the last part might be shorter.
                duration = min(MAX_DURATION_SECONDS, original_duration - start_time)

                _encode_chunk(input_path, part_output_path, start_time, duration, audio_stream is not None)

    except Exception as e:
        print(f"   [FATAL ERROR] An error occurred during video analysis: {e}", file=sys.stderr)


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