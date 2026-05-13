import subprocess
import sys
import glob
import os
import argparse

DEFAULT_CHUNK_SECONDS = 1800


def parse_args():
    parser = argparse.ArgumentParser(
        description="Convert media files to WAV, optionally splitting into time chunks."
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        help="Input files or wildcard patterns (example: *.mp4).",
    )
    parser.add_argument(
        "-c",
        "--chunk-seconds",
        type=int,
        default=DEFAULT_CHUNK_SECONDS,
        help="Chunk duration in seconds when splitting is enabled.",
    )
    parser.add_argument(
        "-s",
        "--split",
        action="store_true",
        help="Enable chunk splitting.",
    )
    parser.add_argument(
        "-n",
        "--no-split",
        action="store_true",
        help="Disable chunk splitting and create one WAV per input.",
    )
    parser.add_argument(
        "-y",
        "--overwrite",
        action="store_true",
        help="Overwrite existing output files.",
    )
    return parser.parse_args()


def convert_to_wav():
    args = parse_args()

    if args.chunk_seconds <= 0:
        print("Error: --chunk-seconds must be greater than 0.")
        return

    should_split = args.split and not args.no_split

    files_to_process = []
    for arg in args.inputs:
        files_to_process.extend(glob.glob(arg))

    if not files_to_process:
        print("No matching files found.")
        return

    for file_path in files_to_process:
        # Skip directories
        if os.path.isdir(file_path):
            continue

        # Get file name and extension
        base_name = os.path.splitext(file_path)[0]
        output_file = f"{base_name}.wav"

        if should_split:
            output_pattern = f"{base_name}_part_%03d.wav"
            first_segment = f"{base_name}_part_000.wav"
            if os.path.exists(first_segment) and not args.overwrite:
                print(f"Skipping {file_path}: split output already exists ({first_segment}).")
                continue
            print(
                f"Processing with split: {file_path} -> {output_pattern} "
                f"(every {args.chunk_seconds}s)"
            )
            ffmpeg_cmd = [
                "ffmpeg",
                "-i",
                file_path,
                "-f",
                "segment",
                "-segment_time",
                str(args.chunk_seconds),
                "-reset_timestamps",
                "1",
                "-c:a",
                "pcm_s16le",
                output_pattern,
            ]
        else:
            if os.path.exists(output_file) and not args.overwrite:
                print(f"Skipping {file_path}: {output_file} already exists.")
                continue
            print(f"Processing: {file_path} -> {output_file}")
            ffmpeg_cmd = [
                "ffmpeg",
                "-i",
                file_path,
                "-c:a",
                "pcm_s16le",
                output_file,
            ]

        if args.overwrite:
            ffmpeg_cmd.insert(1, "-y")
        else:
            ffmpeg_cmd.insert(1, "-n")
        
        try:
            subprocess.run(
                ffmpeg_cmd,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.STDOUT
            )
        except subprocess.CalledProcessError:
            print(f"Error: Failed to convert {file_path}. Ensure FFmpeg is installed.")
        except FileNotFoundError:
            print("Error: FFmpeg not found in system PATH.")
            break

if __name__ == "__main__":
    convert_to_wav()
