import os
import sys
import shutil
import glob
import argparse
from pathlib import Path
from moviepy.video.io.VideoFileClip import VideoFileClip

# Supported video extensions
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".flv"}

# Resolution categories based on the shorter dimension (e.g., 1080 for a 1920x1080 video)
# The keys are the minimum pixel count for that category. The list is checked from top to bottom.
RESOLUTION_TIERS = [
    (2160, "4K_UHD"),
    (1440, "1440p_QHD"),
    (1080, "1080p_FHD"),
    (720, "720p_HD"),
    (0, "SD_or_lower"), # Fallback for anything less than 720p
]


def get_resolution_category(width, height):
    """Determines a resolution category string based on video dimensions."""
    short_dimension = min(width, height)
    for threshold, name in RESOLUTION_TIERS:
        if short_dimension >= threshold:
            return name
    return "Unknown_Resolution"


def get_video_files_from_patterns(patterns):
    files = []
    for pat in patterns:
        matched = glob.glob(pat)
        files.extend(matched)
    return sorted(set(files))


def get_all_video_files(root_dir):
    files = []
    for dirpath, _, filenames in os.walk(root_dir):
        for fname in filenames:
            if Path(fname).suffix.lower() in VIDEO_EXTS:
                files.append(os.path.join(dirpath, fname))
    return files


def sort_videos(files, vertical_dir, horizontal_dir):
    """
    Sorts video files into subdirectories based on orientation and resolution.
    Directories are only created if a file needs to be moved into them.
    """
    for src_path in files:
        try:
            with VideoFileClip(src_path) as clip:
                width, height = clip.size
        except Exception as e:
            print(f"Skipping {src_path}: cannot read video ({e})", file=sys.stderr)
            continue

        # 1. Determine orientation directory
        orientation_dir = vertical_dir if height > width else horizontal_dir
        
        # 2. Determine resolution sub-directory
        resolution_subdir = get_resolution_category(width, height)
        
        # 3. Combine them to create the final target directory
        target_dir = os.path.join(orientation_dir, resolution_subdir)

        # 4. Create the directory path only when we are sure we have a file for it.
        #    os.makedirs is recursive and will create parent dirs (e.g., 'vertical') as needed.
        os.makedirs(target_dir, exist_ok=True)

        dest_path = os.path.join(target_dir, os.path.basename(src_path))
        try:
            shutil.move(src_path, dest_path)
            print(f"Moved {src_path} -> {dest_path}")
        except Exception as e:
            print(f"Failed to move {src_path}: {e}", file=sys.stderr)

# I've also slightly improved the video reading by using a 'with' statement,
# which ensures the clip is closed automatically, even if errors occur.
# This replaces the manual clip.close() call.

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Sort videos by orientation (vertical/horizontal) and resolution (4K/HD/etc.)"
    )
    parser.add_argument(
        'patterns', nargs='*',
        help='Optional glob patterns (e.g. *.mkv). If omitted, walks current directory.'
    )
    parser.add_argument(
        '--src', '-s', default='.',
        help='Source directory to walk when no patterns given (default: current dir)'
    )
    parser.add_argument(
        '--vertical', '-v', default='vertical',
        help='Folder name for vertical videos (default: vertical)'
    )
    parser.add_argument(
        '--horizontal', '-H', default='horizontal',
        help='Folder name for horizontal videos (default: horizontal)'
    )
    args = parser.parse_args()

    if args.patterns:
        video_files = get_video_files_from_patterns(args.patterns)
    else:
        video_files = get_all_video_files(args.src)

    if not video_files:
        print("No video files found.")
        sys.exit(0)

    sort_videos(video_files, args.vertical, args.horizontal)