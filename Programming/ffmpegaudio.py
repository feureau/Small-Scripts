#!/usr/bin/env python3

import argparse
import os
import glob
import subprocess
import shutil
import sys

# Default patterns to scan for if no input files are provided
DEFAULT_SCAN_PATTERNS = [
    '*.mp4', '*.mkv', '*.avi', '*.mov', '*.flv', '*.webm', '*.wmv',
    '*.mpeg', '*.mpg', '*.ts', '*.vob', '*.m2ts', '*.mts',  # Video formats
    '*.aac', '*.flac', '*.ogg', '*.m4a', '*.mp3', '*.wav'   # Audio formats
]

# Allowed output formats
ALLOWED_OUTPUT_FORMATS = ['mp3', 'wav']

def check_ffmpeg_installed():
    """Checks if ffmpeg is installed and in PATH."""
    if shutil.which("ffmpeg") is None:
        print("Error: ffmpeg command not found.")
        print("Please install ffmpeg and ensure it is in your system's PATH.")
        return False
    return True

def convert_media_to_audio(input_file_path, output_dir_path, target_formats, mp3_bitrate):
    """
    Converts a single media file to the specified audio formats.

    Args:
        input_file_path (str): Absolute path to the input media file.
        output_dir_path (str): Absolute path to the directory where converted files will be saved.
        target_formats (list): A list of strings representing target audio formats (e.g., ['mp3', 'wav']).
        mp3_bitrate (str): The bitrate for MP3 conversion (e.g., '192k').
    """
    base_name = os.path.splitext(os.path.basename(input_file_path))[0]
    print(f"\nProcessing: {input_file_path}")

    for target_format in target_formats:
        output_filename = f"{base_name}.{target_format}"
        output_file_path = os.path.join(output_dir_path, output_filename)

        print(f"  Converting to {target_format.upper()} -> {output_file_path}...")

        # Base ffmpeg command: input, overwrite, no video, 48kHz audio sample rate
        # Using -y to automatically overwrite output files if they exist.
        ffmpeg_cmd = [
            'ffmpeg',
            '-i', input_file_path,
            '-y',  # Overwrite output files without asking
            '-vn',  # Disable video recording
            '-ar', '48000'  # Set audio sampling frequency to 48kHz
        ]

        if target_format == 'mp3':
            ffmpeg_cmd.extend(['-c:a', 'libmp3lame']) # Audio codec for MP3
            if mp3_bitrate:
                ffmpeg_cmd.extend(['-b:a', mp3_bitrate]) # Audio bitrate
        elif target_format == 'wav':
            # Standard PCM signed 16-bit little-endian for WAV
            ffmpeg_cmd.extend(['-c:a', 'pcm_s16le'])
        else:
            print(f"  Skipping unsupported format: {target_format}")
            continue

        ffmpeg_cmd.append(output_file_path)

        try:
            # Execute ffmpeg command
            process = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, check=False)
            if process.returncode == 0:
                print(f"  Successfully converted to {output_file_path}")
            else:
                print(f"  Error converting to {target_format.upper()}:")
                print(f"    FFmpeg stdout: {process.stdout.strip()}")
                print(f"    FFmpeg stderr: {process.stderr.strip()}")
        except FileNotFoundError: # Should be caught by check_ffmpeg_installed, but as a safeguard
            print("  Error: ffmpeg command not found during conversion. Please ensure it's installed and in PATH.")
            return # Stop processing this file if ffmpeg is suddenly not found
        except Exception as e:
            print(f"  An unexpected error occurred during conversion: {e}")

def main():
    """Main function to parse arguments and orchestrate conversion."""
    parser = argparse.ArgumentParser(
        description="Batch convert media files to specified audio formats (MP3, WAV) using ffmpeg.",
        epilog="Example: ffmpegaudio.py *.mkv -f mp3,wav -b 192k -d my_audio_exports"
    )
    parser.add_argument(
        'inputs',
        metavar='INPUT',
        type=str,
        nargs='*',
        help="One or more input media files or glob patterns (e.g., video.mp4, '*.mkv'). "
             "If omitted, scans the current directory for common media files."
    )
    parser.add_argument(
        '-f', '--formats',
        type=str,
        default=','.join(ALLOWED_OUTPUT_FORMATS),
        help=f"Comma-separated list of output audio formats. Supported: {', '.join(ALLOWED_OUTPUT_FORMATS)}. "
             f"Default: {','.join(ALLOWED_OUTPUT_FORMATS)}"
    )
    parser.add_argument(
        '-b', '--bitrate',
        type=str,
        default='192k',
        help="Audio bitrate for MP3 conversion (e.g., '128k', '192k', '320k'). Default: 192k. "
             "Not used for WAV."
    )
    parser.add_argument(
        '-d', '--dir',
        dest='output_subdir',
        type=str,
        default='converted_audio',
        help="Name of the subdirectory in the current working directory to save converted files. "
             "Default: converted_audio"
    )

    args = parser.parse_args()

    if not check_ffmpeg_installed():
        sys.exit(1)

    # Parse target formats
    try:
        target_formats_list = [fmt.strip().lower() for fmt in args.formats.split(',') if fmt.strip()]
        if not target_formats_list:
            raise ValueError("No output formats specified.")
        for fmt in target_formats_list:
            if fmt not in ALLOWED_OUTPUT_FORMATS:
                raise ValueError(f"Unsupported format '{fmt}'. Allowed are: {', '.join(ALLOWED_OUTPUT_FORMATS)}")
    except ValueError as e:
        print(f"Error in --formats argument: {e}")
        parser.print_help()
        sys.exit(1)


    # Gather all input files
    potential_files = []
    if not args.inputs:
        print(f"No input files specified. Scanning current directory for media files using patterns: {', '.join(DEFAULT_SCAN_PATTERNS)}")
        for pattern in DEFAULT_SCAN_PATTERNS:
            potential_files.extend(glob.glob(pattern))
    else:
        for user_input_pattern in args.inputs:
            matched_files = glob.glob(user_input_pattern)
            if not matched_files:
                # Check if it was a specific file path that didn't exist, or a pattern that matched nothing
                is_pattern = any(c in user_input_pattern for c in '*?[]')
                if not is_pattern and not os.path.exists(user_input_pattern):
                     print(f"Warning: Specified input file '{user_input_pattern}' not found.")
                elif is_pattern : # It was a pattern that matched nothing
                    print(f"Warning: Pattern '{user_input_pattern}' did not match any files.")
                # If it's an existing file but glob didn't pick it (e.g. no special chars), it should be fine.
                # os.path.isfile will filter later.
            potential_files.extend(matched_files)

    # Get absolute paths, filter out directories, and remove duplicates
    # This ensures that even if the script is called from elsewhere, paths are correct.
    # And that we only process actual files.
    files_to_process = sorted(list(set(
        os.path.abspath(f) for f in potential_files if os.path.isfile(f)
    )))

    if not files_to_process:
        print("No valid media files found to process.")
        if not args.inputs: # If scanning failed to find anything
            print(f"Consider placing media files in the current directory or specifying them directly.")
        sys.exit(0)

    # Create output directory (relative to current working directory)
    # os.getcwd() is where the script is *called* from.
    output_dir_abs_path = os.path.join(os.getcwd(), args.output_subdir)
    try:
        os.makedirs(output_dir_abs_path, exist_ok=True)
        print(f"Output directory: {output_dir_abs_path}")
    except OSError as e:
        print(f"Error creating output directory '{output_dir_abs_path}': {e}")
        sys.exit(1)

    print(f"\nFound {len(files_to_process)} file(s) to process.")
    print(f"Target formats: {', '.join(f.upper() for f in target_formats_list)}")
    if 'mp3' in target_formats_list:
        print(f"MP3 Bitrate: {args.bitrate}")

    # Process each file
    for input_file in files_to_process:
        convert_media_to_audio(input_file, output_dir_abs_path, target_formats_list, args.bitrate)

    print("\nBatch conversion finished.")

if __name__ == '__main__':
    main()
