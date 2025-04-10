#!/usr/bin/env python
import argparse
import glob
import os
import subprocess
import sys

# List of common video file extensions (used for finding inputs if none specified)
VIDEO_EXTENSIONS = ['*.mp4', '*.mkv', '*.avi', '*.mov', '*.flv', '*.wmv', '*.webm']

def find_all_video_files():
    """Find all video files in the current directory based on common extensions."""
    files = []
    for ext in VIDEO_EXTENSIONS:
        # Use recursive=True if you want to search subdirectories as well
        files.extend(glob.glob(ext, recursive=False))
    # Remove duplicates in case a file matches multiple patterns.
    return list(set(files))

def build_ffmpeg_command(input_file, rotation, output_file):
    """
    Build the FFmpeg command to copy all streams and metadata to MKV,
    adding rotation metadata to the first video stream.

    Args:
        input_file (str): Path to the input video file.
        rotation (int): Rotation angle (90, 180, 270).
        output_file (str): Path to the target output MKV file.

    Returns:
        list: A list of strings representing the FFmpeg command.

    Command Breakdown:
    - -i input file
    - -map 0             : Maps all streams (video, audio, subs, data, attachments).
    - -map_metadata 0    : Maps global container-level metadata from input 0.
    - -map_chapters 0    : Maps chapters from input 0.
    - -c copy            : Copies all stream codecs (avoids re-encoding).
    - -metadata:s:v:0 rotate=<rotation> : Sets rotation on the first video stream.
                           (Applied after mapping metadata).
    - output_file        : The target MKV file path.
    """
    return [
        "ffmpeg",
        "-i", input_file,
        "-map", "0",           # Map all streams
        "-map_metadata", "0", # Map global metadata
        "-map_chapters", "0", # Map chapters
        "-c", "copy",         # Copy all stream codecs
        "-metadata:s:v:0", f"rotate={rotation}", # Set rotation on first video stream
        output_file           # Target MKV output file
    ]

def process_files(files, rotation):
    """Processes a list of video files using FFmpeg."""
    # Create output directory based on rotation value, indicating MKV output.
    output_dir = f"Rotation_{rotation}_MKV"
    if not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir)
            print(f"Created directory: {output_dir}")
        except OSError as e:
            print(f"Error creating directory {output_dir}: {e}")
            return # Stop if directory cannot be created

    processed_count = 0
    skipped_count = 0
    error_count = 0

    for file in files:
        # Build output file path, changing extension to .mkv
        base = os.path.basename(file)
        name_without_ext, _ = os.path.splitext(base)
        # Ensure the new filename ends with .mkv
        output_file = os.path.join(output_dir, f"{name_without_ext}.mkv")

        # Skip if output file already exists
        if os.path.exists(output_file):
            print(f"Skipping '{base}' because output '{os.path.basename(output_file)}' already exists.")
            skipped_count += 1
            continue # Skip processing this file

        # Build the FFmpeg command.
        cmd = build_ffmpeg_command(file, rotation, output_file)
        print(f"Processing '{base}' -> '{os.path.basename(output_file)}' with rotation {rotation} (Copy to MKV)")

        # Execute the command and print any errors.
        try:
            # Using capture_output=True to get stdout/stderr
            # Using text=True to get them as strings
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)

            if result.returncode != 0:
                error_count += 1
                print(f"Error processing {base}:")
                # Print the command that failed for easier debugging
                print(f"Command: {' '.join(cmd)}")
                print(f"FFmpeg STDERR:\n{result.stderr.strip()}")
            else:
                processed_count += 1
                print(f"Successfully processed {base}.")
                # Optional: print stdout if needed, though -c copy is usually quiet
                # if result.stdout.strip():
                #    print(f"FFmpeg STDOUT:\n{result.stdout.strip()}")

        except FileNotFoundError:
             print(f"\nError: 'ffmpeg' command not found.")
             print(f"Please ensure FFmpeg is installed and accessible in your system's PATH.")
             error_count += 1
             break # Stop processing if ffmpeg is not found
        except Exception as e:
            error_count += 1
            print(f"An unexpected error occurred processing {base}: {e}")
            # Also print the command here for unexpected errors
            print(f"Command: {' '.join(cmd)}")


    print("\n----- Processing Summary -----")
    print(f"Successfully processed: {processed_count}")
    print(f"Skipped (already exist): {skipped_count}")
    print(f"Errors: {error_count}")
    print("----------------------------")


def main():
    parser = argparse.ArgumentParser(
        description="Copies video files to MKV container, preserving all streams and metadata, "
                    "and adds a rotation flag to the first video stream using FFmpeg."
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="One or more input video files (supports glob patterns like *.mp4). "
             "If omitted, scans the current directory for common video files."
    )
    parser.add_argument(
        "-r", "--rotate",
        type=int,
        choices=[90, 180, 270],
        default=90,
        help="Rotation angle (degrees) to add as metadata. Allowed values: 90, 180, 270. Defaults to 90."
    )

    args = parser.parse_args()

    video_files = []

    if not args.files:
        print("No input files specified. Scanning current folder for video files...")
        video_files = find_all_video_files()
        if not video_files:
            print("No video files found in the current folder.")
            sys.exit(1)
        print(f"Found {len(video_files)} video file(s) in the current folder.")
    else:
        # Expand each given glob pattern and collect unique file paths.
        matched_files = set()
        for pattern in args.files:
            try:
                # Use glob to handle patterns like *.mp4
                found = glob.glob(pattern)
                if not found:
                     # If glob finds nothing, check if it's a literal existing file path
                     if os.path.isfile(pattern):
                         found = [pattern]
                     else:
                        print(f"Warning: No files found matching pattern/path: {pattern}")
                matched_files.update(found)
            except Exception as e:
                print(f"Error processing pattern/path {pattern}: {e}")

        video_files = sorted(list(matched_files)) # Sort for consistent processing order

    if not video_files:
        print("No video files to process. Exiting.")
        sys.exit(1)

    print(f"\nProcessing {len(video_files)} file(s) with rotation set to {args.rotate} degrees...")
    process_files(video_files, args.rotate)

if __name__ == "__main__":
    main()