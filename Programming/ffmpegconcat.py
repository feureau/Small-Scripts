#!/usr/bin/env python
"""
--- ffmpegconcat.py ---

A Python script to losslessly concatenate multiple video files using FFmpeg.

This script automates the process of checking video file compatibility and
merging them sequentially without re-encoding.

--------------------
-- DOCUMENTATION --
--------------------

[ PURPOSE ]
The primary goal is to combine several video files into a single output file.
By default, it performs a critical check to ensure all input videos share the
same technical properties (codec, resolution, etc.) for a true lossless merge.
If they don't match, it aborts to prevent creating a broken file.

[ DEPENDENCIES ]
1. Python 3
2. FFmpeg: Must be installed and accessible in the system's PATH.
3. ffmpeg-python: The required Python library (`pip install ffmpeg-python`).

[ USAGE ]
python /path/to/ffmpegconcat.py [VIDEO_FILES] [OPTIONS]

Arguments:
  videos                A space-separated list of video files to concatenate.
  -o, --output          Optional. The name for the final merged video file.
                        Defaults to "output.mp4".
  -f, --force           Optional. Bypasses all metadata compatibility checks
                        and attempts to concatenate the files directly.

[ !!! WARNING ABOUT THE --force FLAG !!! ]
The `-f` or `--force` flag should only be used as a last resort for experimentation.
It tells FFmpeg to stitch the files together regardless of their properties.
This will almost certainly lead to issues like:
  - Severe audio/video desynchronization.
  - Incorrect playback speed or stuttering.
  - A corrupted or unplayable output file.
It does NOT magically fix metadata differences. The correct way to fix a
mismatch (like a VFR vs CFR frame rate error) is to re-encode the problematic
file to match the properties of the others, NOT to use force.

[ RECOMMENDED FIX FOR FRAME RATE ERRORS ]
If you get an error for 'avg_frame_rate' (e.g., '60/1' vs a long fraction),
you are mixing Constant (CFR) and Variable (VFR) frame rates. The proper fix is
to convert the VFR video to CFR:
> ffmpeg -i your_vfr_video.mp4 -r 60 -c:a copy your_cfr_video_fixed.mp4
Then, run this script on the new 'fixed' file and the other videos.

"""
import argparse
import subprocess
import ffmpeg
import os
import sys

def get_video_metadata(video_path):
    """Extracts essential video and audio metadata using ffprobe."""
    try:
        if not os.path.exists(video_path) or os.path.getsize(video_path) == 0:
            print(f"Error: File is missing or empty: {video_path}")
            return None
        probe = ffmpeg.probe(video_path)
        video_stream = next((s for s in probe['streams'] if s['codec_type'] == 'video'), None)
        audio_stream = next((s for s in probe['streams'] if s['codec_type'] == 'audio'), None)

        if not video_stream:
            print(f"Warning: Could not find a video stream in {video_path}")
            return None

        metadata = {
            'codec_name': video_stream.get('codec_name'),
            'width': video_stream.get('width'),
            'height': video_stream.get('height'),
            'pix_fmt': video_stream.get('pix_fmt'),
            'avg_frame_rate': video_stream.get('avg_frame_rate')
        }
        if audio_stream:
            metadata.update({
                'audio_codec_name': audio_stream.get('codec_name'),
                'sample_rate': audio_stream.get('sample_rate'),
                'channels': audio_stream.get('channels')
            })
        else:
            print(f"Info: No audio stream found in {video_path}")
            metadata.update({'audio_codec_name': None, 'sample_rate': None, 'channels': None})
        return metadata
    except ffmpeg.Error as e:
        print(f"Error probing file '{video_path}':", file=sys.stderr)
        print(e.stderr.decode(), file=sys.stderr)
        return None

def main():
    """Main function to parse arguments, check compatibility, and concatenate."""
    parser = argparse.ArgumentParser(
        description="A script to losslessly concatenate videos. Checks for compatibility by default.",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('videos', nargs='*', help="List of video files to concatenate.")
    parser.add_argument('-o', '--output', default='output.mp4', help="Name of the output video file (default: output.mp4).")
    parser.add_argument(
        '-f', '--force',
        action='store_true',
        help="Force concatenation by ignoring all metadata compatibility checks. NOT RECOMMENDED."
    )

    args = parser.parse_args()

    if not args.videos or len(args.videos) < 2:
        print("Error: You must provide at least two video files to concatenate.")
        parser.print_help()
        return

    # --- Compatibility Check (or skip if --force is used) ---
    can_proceed = True
    if args.force:
        print("\n" + "="*50)
        print("    WARNING: --force flag detected.".center(50))
        print("    Bypassing all compatibility checks.".center(50))
        print("    The output file will likely be corrupted or have".center(50))
        print("    audio/video desync.".center(50))
        print("="*50 + "\n")
    else:
        print("--- Starting Video Compatibility Check ---")
        first_video_metadata = get_video_metadata(args.videos[0])
        if not first_video_metadata:
            print(f"\nCould not get metadata for the first video '{args.videos[0]}'. Aborting.")
            return

        for video_file in args.videos[1:]:
            current_metadata = get_video_metadata(video_file)
            if not current_metadata:
                can_proceed = False
                break
            for key, value in first_video_metadata.items():
                if current_metadata.get(key) != value:
                    print("\n-------------------- ERROR --------------------")
                    print("Videos have different properties. Cannot concatenate without re-encoding.")
                    print(f"Property mismatch found in '{key}':")
                    print(f"  - '{args.videos[0]}': {value}")
                    print(f"  - '{video_file}': {current_metadata.get(key)}")
                    print("---------------------------------------------")
                    print("\nTo fix this properly, re-encode one file to match the other.")
                    print("To ignore this check, re-run with the -f or --force flag (not recommended).")
                    can_proceed = False
                    break
            if not can_proceed:
                break

    if not can_proceed:
        print("\nAborting concatenation due to incompatible video properties.")
        return

    if can_proceed and not args.force:
        print("\nSuccess: All videos are compatible for lossless concatenation.")

    # --- Concatenation Process ---
    list_filename = "mylist.txt"
    try:
        with open(list_filename, "w") as f:
            for video_file in args.videos:
                safe_path = os.path.abspath(video_file).replace("'", "'\\''")
                f.write(f"file '{safe_path}'\n")
    except IOError as e:
        print(f"Error: Could not write to temporary file list '{list_filename}': {e}")
        return

    ffmpeg_command = ['ffmpeg', '-f', 'concat', '-safe', '0', '-i', list_filename, '-c', 'copy', args.output]
    print("\nExecuting FFmpeg command...")
    print(f"  > {' '.join(ffmpeg_command)}")
    try:
        # Use -y to automatically overwrite the output file if it exists
        subprocess.run(['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', list_filename, '-c', 'copy', args.output], check=True, capture_output=True, text=True)
        print(f"\n--- SUCCESS ---")
        print(f"Successfully attempted to concatenate videos into '{args.output}'")
    except subprocess.CalledProcessError as e:
        print("\n--- FFMPEG ERROR ---")
        print("FFmpeg failed to execute. This is a common result when forcing incompatible files.")
        print(f"\n--- FFmpeg stderr ---\n{e.stderr}")
    except FileNotFoundError:
        print("\n--- SCRIPT ERROR ---")
        print("Error: 'ffmpeg' command not found. Make sure FFmpeg is installed and in your system's PATH.")
    finally:
        if os.path.exists(list_filename):
            os.remove(list_filename)
            print(f"\nCleaned up temporary file: {list_filename}")

if __name__ == "__main__":
    main()