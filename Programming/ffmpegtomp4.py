import argparse
import glob
import subprocess
import os
import shutil

def find_ffmpeg():
    """Checks if ffmpeg is in PATH and executable."""
    if shutil.which("ffmpeg") is None:
        print("ERROR: ffmpeg not found in PATH. Please install ffmpeg and ensure it's accessible.")
        return False
    return True

def wrap_video(input_file, output_extension):
    """
    Wraps a video file to a new container format using ffmpeg,
    copying all streams and metadata without re-encoding.
    """
    if not os.path.isfile(input_file):
        print(f"Skipping non-file: {input_file}")
        return

    base, old_ext = os.path.splitext(input_file)
    output_file = base + "." + output_extension.lstrip('.') # Ensure extension doesn't have leading dot

    if input_file == output_file:
        print(f"Skipping {input_file}: Input and output filenames are identical.")
        return

    print(f"Processing: {input_file} -> {output_file}")

    # Construct the ffmpeg command
    # -i : input file
    # -c copy : copy all codecs (video, audio, subtitles) without re-encoding
    # -map 0 : select all streams from the first input (input_file)
    #          This includes video, audio, subtitles, data streams, and attachments.
    # -map_metadata 0 : copy global metadata from the first input to the output
    # -map_chapters 0 : copy chapters from the first input to the output
    # -y : overwrite output file if it exists (optional, can be removed if you want manual confirmation)
    command = [
        "ffmpeg",
        "-i", input_file,
        "-c", "copy",
        "-map", "0",
        "-map_metadata", "0",
        "-map_chapters", "0", # This ensures chapters are copied
        "-y", # Overwrite output without asking
        output_file
    ]

    try:
        # Run the command
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()

        if process.returncode == 0:
            print(f"Successfully wrapped: {input_file} to {output_file}")
        else:
            print(f"Error wrapping {input_file}:")
            print("FFmpeg stdout:")
            print(stdout.decode(errors='replace')) # Use 'replace' for unknown characters
            print("FFmpeg stderr:")
            print(stderr.decode(errors='replace'))

    except FileNotFoundError:
        # This specific exception might not be caught here if shutil.which fails earlier,
        # but good practice if ffmpeg path was hardcoded or changed.
        print("Error: ffmpeg command not found. Make sure it's installed and in your PATH.")
    except Exception as e:
        print(f"An unexpected error occurred while processing {input_file}: {e}")

def main():
    if not find_ffmpeg():
        return

    parser = argparse.ArgumentParser(
        description="Batch wrap video files to a different container using ffmpeg, copying all content without re-encoding.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Examples:
  Batch process all MKV files in the current directory and wrap to MP4:
    %(prog)s *.mkv

  Process specific files and wrap to MOV:
    %(prog)s video1.avi video2.webm -e mov

  Process all MP4 files and wrap them to MKV (script placed in a different folder):
    /path/to/script/ffmpegwrapto.py *.mp4 -e mkv

Notes:
- This script requires ffmpeg to be installed and in your system's PATH.
- It copies all video, audio, subtitle streams, metadata, chapters, and attachments.
- No re-encoding occurs, so the process is fast and preserves quality.
"""
    )
    parser.add_argument(
        "-e", "--extension",
        default="mp4",
        help="Target container extension (e.g., mp4, mkv, mov). Default is 'mp4'."
    )
    parser.add_argument(
        "input_files",
        nargs="*", # 0 or more arguments
        help="Video files or glob patterns to process (e.g., *.mkv video.avi)."
    )

    args = parser.parse_args()

    target_extension = args.extension.lstrip('.') # Remove leading dot if present

    files_to_process = []
    if not args.input_files:
        # If no input files are specified, you might want to default to a common glob
        # or print a help message. For now, let's require input files.
        # You could use glob.glob('*.*') but that might pick up non-video files.
        # A safer default might be to glob for common video types if you want to add that.
        # print("No input files specified. Globbing for common video files in current directory...")
        # common_video_extensions = ["*.mkv", "*.mp4", "*.avi", "*.mov", "*.webm", "*.flv"]
        # for pattern in common_video_extensions:
        #     files_to_process.extend(glob.glob(pattern))
        # if not files_to_process:
        #     print("No video files found in the current directory.")
        #     parser.print_help()
        #     return
        print("No input files or patterns provided.")
        parser.print_help()
        return
    else:
        for pattern in args.input_files:
            expanded_files = glob.glob(pattern)
            if not expanded_files:
                print(f"Warning: Pattern '{pattern}' did not match any files.")
            files_to_process.extend(expanded_files)

    if not files_to_process:
        print("No files matched the input patterns.")
        return

    # Deduplicate list in case of overlapping globs, preserving order
    seen = set()
    unique_files = []
    for f in files_to_process:
        if f not in seen:
            seen.add(f)
            unique_files.append(f)

    for input_file_path in unique_files:
        # Ensure the script processes files relative to the current working directory
        # from where the script is called, not where the script is located.
        # glob.glob already returns paths that can be relative to CWD or absolute.
        wrap_video(input_file_path, target_extension)

if __name__ == "__main__":
    main()