#!/usr/bin/env python

"""
subsplitter.py - A command-line utility for splitting video files based on subtitle timings.

Description:
    This script automates the process of cutting a video into smaller clips. Each
    cut point is determined by the start time of a line in a corresponding subtitle
    file (.srt or .txt). The resulting video clips are named after the subtitle text,
    making it easy to find specific moments in a video.

    The script is designed to be called from a working directory containing your
    video files. It organizes all output into a dedicated folder and creates
    sub-folders for each video processed, keeping the clips neatly organized.

Prerequisites:
    This script requires the `moviepy` and `srt` Python libraries. Before running,
    make sure you have them installed. You can install them using this command:

    pip install moviepy srt

    Additionally, for the AV1 encoding to work, you must have:
    1. A modern NVIDIA GPU (RTX 20-series or newer recommended).
    2. Up-to-date NVIDIA drivers.
    3. An FFmpeg build that supports the `av1_nvenc` encoder.

Usage:
    Run the script from your terminal inside the folder containing your media.

    1. Process a specific video and an explicitly named subtitle file:
       python /path/to/subsplitter.py video.mp4 subtitles.srt

    2. Process a specific video, auto-detecting the subtitle file:
       (This will look for 'video.srt' or 'video.txt' in the same folder)
       python /path/to/subsplitter.py video.mp4

    3. Process all videos of a certain type (e.g., .mp4) in the current folder:
       (For each video, it will look for a corresponding .srt or .txt file)
       python /path/to/subsplitter.py *.mp4
"""

import sys
import os
import re
import glob
from moviepy import VideoFileClip
import srt

# --- Configuration ---
OUTPUT_DIR = "subsplit_output"
SUPPORTED_VIDEO_EXTENSIONS = ['.mp4', '.mkv', '.mov', '.avi', '.flv']
SUBTITLE_EXTENSIONS = ['.srt', '.txt']
# -------------------

def sanitize_filename(text):
    """
    Sanitizes a string to be used as a valid filename by removing
    illegal characters and limiting its length.
    """
    text = re.sub(r'[^\w\s-]', '', text).strip()
    text = re.sub(r'\s+', '_', text)
    if not text:
        return "untitled"
    return text[:100]

def find_subtitle_file(video_path):
    """
    Tries to find a subtitle file corresponding to the given video file
    by checking for the same base name with .srt or .txt extensions.
    """
    base_name = os.path.splitext(video_path)[0]
    for ext in SUBTITLE_EXTENSIONS:
        sub_path = base_name + ext
        if os.path.exists(sub_path):
            return sub_path
    return None

def process_video(video_path, srt_path):
    """
    Splits a single video file based on a single SRT file, encoding in AV1.

    Returns: True if successful, False otherwise.
    """
    print(f"\nProcessing '{os.path.basename(video_path)}' with '{os.path.basename(srt_path)}'...")
    try:
        video_base_name = os.path.splitext(os.path.basename(video_path))[0]
        video_output_dir = os.path.join(OUTPUT_DIR, video_base_name)
        os.makedirs(video_output_dir, exist_ok=True)

        video = VideoFileClip(video_path)
        with open(srt_path, 'r', encoding='utf-8', errors='ignore') as f:
            subtitles = list(srt.parse(f.read()))

        if not subtitles:
            print("  -> Failure: No subtitles found in the SRT file.")
            video.close()
            return False

        print(f"  -> Found {len(subtitles)} subtitles. Splitting and encoding to AV1...")
        for i, sub in enumerate(subtitles):
            start_time = sub.start.total_seconds()
            end_time = subtitles[i + 1].start.total_seconds() if i < len(subtitles) - 1 else video.duration

            if end_time <= start_time:
                continue

            filename_text = sanitize_filename(sub.content)
            output_filename = f"{i+1:03d}_{filename_text}.mkv"
            output_path = os.path.join(video_output_dir, output_filename)

            print(f"    - Creating clip {i+1}: '{sub.content.strip()}'")
            new_clip = video.subclipped(start_time, end_time)

            # --- ROBUST FIX ---
            # To solve the FFmpeg errors, we will re-encode the audio to a clean
            # AAC stream instead of trying to copy it. This is the most reliable method.
            new_clip.write_videofile(
                output_path,
                codec="av1_nvenc",
                audio_codec="aac",  # Explicitly re-encode audio to AAC
                logger=None,
                ffmpeg_params=[
                    # Video parameters
                    "-preset", "p1",
                    "-rc", "vbr",
                    "-cq", "22",
                    # Audio parameter: Set a high bitrate to preserve quality
                    "-b:a", "256k"
                ]
            )
            
            new_clip.close()

        video.close()
        return True
    except Exception as e:
        print(f"  -> An error occurred while processing {os.path.basename(video_path)}: {e}")
        if 'video' in locals() and hasattr(video, 'reader') and video.reader:
            video.close()
        return False

def get_files_from_args():
    """Parses command-line arguments to handle wildcards and create a file list."""
    if len(sys.argv) < 2:
        return []
    
    files_to_process = []
    for arg in sys.argv[1:]:
        expanded_args = glob.glob(arg)
        if not expanded_args:
            print(f"Warning: Argument '{arg}' did not match any files.")
        files_to_process.extend(expanded_args)
    return files_to_process

def main():
    """Main function to parse arguments and orchestrate the splitting."""
    all_files = get_files_from_args()
    if not all_files:
        print("Usage: python subsplitter.py <video_file1> [subtitle_file1] <video_file2> ... or *.mp4")
        sys.exit(1)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    processed_files = []
    failed_files = []
    
    if len(all_files) == 2 and os.path.splitext(all_files[0])[1].lower() in SUPPORTED_VIDEO_EXTENSIONS and os.path.splitext(all_files[1])[1].lower() in SUBTITLE_EXTENSIONS:
        video_path, srt_path = all_files[0], all_files[1]
        if process_video(video_path, srt_path):
            processed_files.append((os.path.basename(video_path), "Successfully processed."))
        else:
            failed_files.append((os.path.basename(video_path), "Processing failed."))
    else:
        video_files = [f for f in all_files if os.path.splitext(f)[1].lower() in SUPPORTED_VIDEO_EXTENSIONS]
        for video_path in video_files:
            subtitle_path = find_subtitle_file(video_path)
            if subtitle_path:
                if process_video(video_path, subtitle_path):
                    processed_files.append((os.path.basename(video_path), "Successfully processed."))
                else:
                    failed_files.append((os.path.basename(video_path), "An error occurred during processing."))
            else:
                failed_files.append((os.path.basename(video_path), "Subtitle file (.srt or .txt) not found."))

    # --- Final Summary ---
    print("\n--------------------")
    print("--- Job Summary ---")
    print("--------------------")
    if processed_files:
        print("\n[SUCCESS]")
        for name, reason in processed_files:
            print(f"- {name}: {reason}")
    if failed_files:
        print("\n[SKIPPED / FAILED]")
        for name, reason in failed_files:
            print(f"- {name}: {reason}")
    print(f"\nOutput clips are located in the '{os.path.join(os.getcwd(), OUTPUT_DIR)}' folder.")


if __name__ == '__main__':
    main()