#!/usr/bin/env python

"""
FFmpeg Cleanup Script

This script cleans video files by creating a new version with only the first
video and first audio stream. This is useful for normalizing files downloaded
from online sources that may have multiple video/audio or data tracks, which
can confuse video editing libraries.

Requirements:
- FFmpeg must be installed and accessible in the system's PATH.

Usage:
1. Place this script in a folder.
2. Open a terminal in the folder containing your videos.
3. Run the script, passing the video files as arguments.

Examples:
# Clean a single file
python path/to/ffmpeg_cleanup.py my_video.mp4

# Clean all .mp4 files in the current folder
python path/to/ffmpeg_cleanup.py *.mp4

# Clean all .mkv and .mov files
python path/to/ffmpeg_cleanup.py *.mkv *.mov
"""

import subprocess
import argparse
import os
import sys

def clean_video(video_path, output_dir, suffix, ffmpeg_path):
    """
    Cleans a single video file using FFmpeg.

    Args:
        video_path (str): Path to the input video file.
        output_dir (str): Directory to save the cleaned file.
        suffix (str): Suffix to add to the cleaned filename.
        ffmpeg_path (str): Path to the ffmpeg executable.
    """
    if not os.path.exists(video_path):
        print(f"Warning: Input file not found, skipping: {video_path}")
        return

    # Construct the output path
    base, ext = os.path.splitext(os.path.basename(video_path))
    output_filename = f"{base}{suffix}{ext}"
    output_path = os.path.join(output_dir, output_filename)

    # Skip if the cleaned file already exists
    if os.path.exists(output_path):
        print(f"Skipped: Cleaned file already exists for '{os.path.basename(video_path)}'")
        return

    print(f"Processing: {os.path.basename(video_path)} -> {output_filename}")

    # The FFmpeg command to execute
    # -i: input file
    # -map 0:v:0: Select the first video stream from the first input
    # -map 0:a:0: Select the first audio stream from the first input
    # -c copy: Copy streams without re-encoding (fast, preserves quality)
    command = [
        ffmpeg_path,
        "-i", video_path,
        "-map", "0:v:0",
        "-map", "0:a:0",
        "-c", "copy",
        output_path
    ]

    try:
        # Run the command
        result = subprocess.run(
            command,
            check=True,         # Raise an exception if ffmpeg fails
            capture_output=True,# Capture stdout and stderr
            text=True           # Decode stdout/stderr as text
        )

    except FileNotFoundError:
        print(
            f"FATAL: The 'ffmpeg' command was not found.\n"
            f"Please ensure FFmpeg is installed and in your system's PATH, "
            f"or specify its location with the --ffmpeg-path argument."
        )
        sys.exit(1)

    except subprocess.CalledProcessError as e:
        # This catches errors from FFmpeg itself (e.g., invalid file)
        print(f"\n--- FFmpeg Error ---")
        print(f"Failed to process: {os.path.basename(video_path)}")
        print(f"FFmpeg stderr:\n{e.stderr}")
        print(f"--------------------\n")
        # Clean up the potentially corrupted output file
        if os.path.exists(output_path):
            os.remove(output_path)

def main():
    parser = argparse.ArgumentParser(
        description="A script to clean video files using FFmpeg by keeping only the primary video and audio streams.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
This tool is ideal for fixing videos downloaded from online sources that have
extra data streams which can cause issues with other video software.
"""
    )
    parser.add_argument(
        "input_files",
        nargs="+",
        help="One or more video files to process. Supports shell wildcards (e.g., *.mp4)."
    )
    parser.add_argument(
        "--output-dir",
        default="cleaned_videos",
        help="The directory where cleaned videos will be saved. (Default: 'cleaned_videos')"
    )
    parser.add_argument(
        "--suffix",
        default="_clean",
        help="The suffix to add to the end of cleaned filenames. (Default: '_clean')"
    )
    parser.add_argument(
        "--ffmpeg-path",
        default="ffmpeg",
        help="The path to the ffmpeg executable, if not in system PATH. (Default: 'ffmpeg')"
    )
    args = parser.parse_args()

    # Create the output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    print(f"Cleaned files will be saved in: '{os.path.abspath(args.output_dir)}'")

    # Process each file provided on the command line
    for video_file in args.input_files:
        clean_video(video_file, args.output_dir, args.suffix, args.ffmpeg_path)

    print("\nCleanup complete.")

if __name__ == "__main__":
    main()