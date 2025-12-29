"""
# ==================================================================================================
#
#                               COMPREHENSIVE DOCUMENTATION
#                                 FOR srtextract_v2.py
#
# ==================================================================================================
#
#  MAINTENANCE NOTE:
#  This documentation block MUST be included at the top of the script file in all its versions.
#  For every update or change made to the script's logic, this documentation MUST be updated
#  accordingly to reflect the changes accurately.
#
# --------------------------------------------------------------------------------------------------
#  1. CORE PURPOSE & FUNCTIONALITY
# --------------------------------------------------------------------------------------------------
#
#  This script is a command-line utility designed to automate the extraction of subtitle streams
#  from video files. It acts as an intelligent wrapper for the powerful command-line tools FFmpeg
#  and FFprobe. Its primary goal is to simplify the process of identifying all subtitle tracks
#  within a video and saving them as individual, usable files.
#
# --------------------------------------------------------------------------------------------------
#  2. PREREQUISITES
# --------------------------------------------------------------------------------------------------
#
#  To use this script, the following software must be installed and configured:
#
#  * Python 3: The script is written in Python 3.
#  * FFmpeg & FFprobe: These are the core multimedia tools that handle the actual probing and
#    extraction. They must be installed and their executable locations must be in the system's
#    PATH environment variable, so they can be called directly from the command line.
#  * chardet library: A Python library used for robust character encoding detection. It must be
#    installed via pip:
#      pip install chardet
#  * pycountry library: A Python library used for converting language codes to names.
#    It must be installed via pip:
#      pip install pycountry
#
# --------------------------------------------------------------------------------------------------
#  3. USAGE AND EXAMPLES
# --------------------------------------------------------------------------------------------------
#
#  The script is run from the command line.
#
#  - Basic Hybrid Mode (Default):
#    python srtextract_v2.py "my_movie.mkv"
#
#  - SRT-Only Mode on Multiple Files using a wildcard:
#    python srtextract_v2.py -f srt "videos/*.mp4"
#
#  - MKV-Packaging Mode for all subs in a directory tree:
#    python srtextract_v2.py --format=mkv "path/to/my/videos/**"
#
#  - Automatic Recursive Search (when no files are provided):
#    python srtextract_v2.py
#    (This will find all supported video files in the current directory and subdirectories)
#
# --------------------------------------------------------------------------------------------------
#  4. DETAILED CODE EXPLANATION & RATIONALE
# --------------------------------------------------------------------------------------------------
#
#  This section breaks down the script's components, explaining what each part does and why it was
#  designed in that specific way.
#
#  ---
#  4.1. Global Constants
#  ---
#
#  * `KNOWN_TEXT_SUBTITLE_CODECS`:
#    - WHAT: A list of subtitle codec names that are known to be text-based.
#    - WHY: This list is the core of the 'hybrid' mode logic. FFmpeg can successfully convert
#      these formats to the universal .srt format. By defining them here, we can easily
#      distinguish them from image-based formats (like PGS, DVD_SUB) which cannot be
#      converted to text and must be handled differently.
#
#  ---
#  4.2. Helper Function: `_run_command_and_decode(command_args)`
#  ---
#
#    - WHAT: This is a centralized function for running external commands (ffmpeg, ffprobe). It
#      captures the raw byte output, detects the character encoding, and safely decodes it.
#    - RATIONALE: This function is the solution to a critical problem. On Windows, command-line
#      tools like ffmpeg can output progress bars or messages using characters that are not
#      part of the default 'cp1252' codepage. When Python's `subprocess` module tries to read
#      this output as text, it results in a `UnicodeDecodeError`, crashing the script.
#      - By capturing raw bytes (`capture_output=True` without `text=True`), we get the
#        unadulterated output from the process.
#      - We use the `chardet` library to analyze these bytes and make an educated guess of the
#        encoding. This is far more reliable than assuming 'utf-8' or any other standard.
#      - We decode using the detected encoding with `errors='replace'`. This is a crucial
#        safety measure. If a character is still invalid even in the detected encoding, it will
#        be replaced with a placeholder ('?') instead of crashing the program.
#      - Centralizing this logic into one function follows the DRY (Don't Repeat Yourself)
#        principle, making the code cleaner and easier to maintain.
#
#  ---
#  4.3. Core Logic Function: `_probe_subtitle_streams(video_path)`
#  ---
#
#    - WHAT: Uses `ffprobe` to inspect a video file and return a structured list of all its
#      subtitle streams.
#    - RATIONALE:
#      - `-of json`: We explicitly ask ffprobe for JSON output. This is vital for reliability.
#        Parsing structured JSON is robust and simple, whereas scraping plain-text output is
#        fragile and prone to breaking if ffprobe's output formatting ever changes.
#      - `-select_streams s`: An optimization that tells ffprobe to only analyze subtitle ('s')
#        streams, ignoring video and audio. This makes the command run faster.
#      - It returns `None` on failure, which is a clear signal for the calling functions to halt
#        processing for that file.
#
#  ---
#  4.4. Filename Generation: `_generate_subtitle_filename(...)`
#  ---
#
#    - WHAT: Constructs a descriptive, human-readable filename for the extracted subtitle file.
#    - RATIONALE:
#      - `Readability`: The format `[VideoName] - [Tag].ext` mirrors standard naming conventions
#        and removes technical noise (like stream indices).
#      - `Smart Tag Selection`: It prioritizes the "Title" tag (e.g., "English [Forced]") first,
#        falling back to "Language", and finally "Unknown". This preserves vital context often
#        found in track titles.
#      - `Sanitization`: File-system unsafe characters are removed, but readable characters like
#        spaces, brackets [], and parentheses () are preserved.
#      - `Collision Handling`: Since unique stream IDs were removed for cleanliness, the function
#        automatically detects if a filename exists and appends a counter (e.g., " (1)") to
#        prevent overwriting.
#
#  ---
#  4.5. Extraction Functions: `_extract_subtitle_streams_as_srt(...)` and `_package_single_subtitle_to_mkv(...)`
#  ---
#
#    - WHAT: These functions construct and run the `ffmpeg` commands to perform the actual
#      extraction.
#    - RATIONALE:
#      - `-map 0:{stream_index}`: This is the key ffmpeg flag. It selects a specific stream from
#        the input file (0) for processing.
#      - For SRT extraction, we let ffmpeg handle the conversion. It will succeed for text-based
#        codecs and fail for others. The function captures this failure and reports it. It also
#        cleans up any empty files created by a failed attempt.
#      - For MKV packaging, we use `-c copy` (`-c` is for codec). This tells ffmpeg to "copy" the
#        stream bit-for-bit without any re-encoding. This is a lossless operation, perfectly
#        preserving the original image-based subtitle data in a new, clean MKV container.
#
#  ---
#  4.6. Processing Mode Functions: `process_to_srt_files`, `process_to_individual_mkv_subs`, `process_hybrid`
#  ---
#
#    - WHAT: These functions orchestrate the extraction process based on the user's chosen mode.
#    - RATIONALE:
#      - `process_hybrid` is the default because it's the "smartest" and most useful mode. It
#        applies the best extraction method for each subtitle type: conversion for text, and
#        lossless packaging for images. This provides the most desirable output for the user
#        without requiring them to know the technical details of the subtitle formats.
#      - The other modes (`srt`, `mkv`) provide direct control for users with specific needs.
#
#  ---
#  4.7. Main Execution Block: `if __name__ == "__main__":`
#  ---
#
#    - WHAT: This is the entry point of the script when it is run directly. It handles command-line
#      argument parsing, finding the video files, and looping through them.
#    - RATIONALE:
#      - `argparse`: This is Python's standard, powerful library for creating command-line
#        interfaces. It automatically handles argument validation, generates help messages
#        (`-h`), and makes the script's options clear and easy to use.
#      - `glob`: This library is used to handle file path patterns and wildcards (e.g., `*.mkv`,
#        `**/*.mp4`). This provides a huge amount of flexibility for batch processing files.
#      - Automatic Search Logic: If the user provides no input files, the script proactively
#        searches for videos using `os.walk`. This is a user-friendly feature for the common
#        use-case of dropping the script into a folder and running it.
#      - `sorted(list(set(video_files_to_process_paths)))`: This chain of commands ensures that
#        the final list of files to process is both unique (the `set` removes any duplicates)
#        and processed in a predictable, alphabetical order (due to `sorted`).
#
# ==================================================================================================
#  5. UPDATE HISTORY
# ==================================================================================================
#
#  - 2025-12-29 (Revision 3): Expanded language codes to full names.
#    - Integrated `pycountry` to convert 3-letter codes (eng, ara) to full names (English, Arabic).
#    - Implemented graceful fallback to original code if `pycountry` is missing or code unknown.
#    - Refined tag priority and stream selection (Revision 2).
#    - Maintained 'Forced' track detection and Unicode sanitization.
#
# ==================================================================================================
"""

import subprocess
import os
import sys
import glob
import argparse
import json
import chardet  # Required for encoding detection

try:
    import pycountry # Optional but recommended for language name expansion
except ImportError:
    pycountry = None

# Define known text-based subtitle codecs that ffmpeg can reasonably convert to SRT
KNOWN_TEXT_SUBTITLE_CODECS = [
    'srt', 'subrip',
    'ass', 'ssa',
    'webvtt',
    'mov_text', 'tx3g',
    'subviewer',
    'microdvd',
    'eia_608', 'cea608',
]


def _run_command_and_decode(command_args):
    """
    Runs a subprocess, captures its raw byte output, detects the encoding,
    and returns safely decoded stdout and stderr strings.
    """
    try:
        process = subprocess.run(
            command_args,
            capture_output=True,
            check=True  # Raise an error if the command returns a non-zero exit code
        )
        stdout_bytes = process.stdout
        stderr_bytes = process.stderr
        
        # Detect encoding and decode stdout safely
        detected_stdout_encoding = chardet.detect(stdout_bytes)['encoding'] or 'utf-8'
        decoded_stdout = stdout_bytes.decode(detected_stdout_encoding, errors='replace')

        # Detect encoding and decode stderr safely
        detected_stderr_encoding = chardet.detect(stderr_bytes)['encoding'] or 'utf-8'
        decoded_stderr = stderr_bytes.decode(detected_stderr_encoding, errors='replace')

        return decoded_stdout, decoded_stderr, process.returncode

    except subprocess.CalledProcessError as e:
        # If the process fails, its output is still valuable. Decode it for the error message.
        error_output = e.stderr.decode('utf-8', errors='replace') if e.stderr else "No stderr output."
        last_line_of_error = error_output.strip().splitlines()[-1] if error_output.strip() else "Unknown FFmpeg error"
        
        return None, last_line_of_error, e.returncode


def _get_language_name(code):
    """
    Converts ISO 639-2 (3-letter) or ISO 639-1 (2-letter) codes to full names.
    Falls back to the original code if pycountry is missing or name not found.
    """
    if not code or not pycountry:
        return code
    
    try:
        # Try finding by alpha_3 (3-letter) or alpha_2 (2-letter)
        lang = pycountry.languages.get(alpha_3=code.lower())
        if not lang:
            lang = pycountry.languages.get(alpha_2=code.lower())
        
        return lang.name if lang else code
    except Exception:
        return code


def _probe_subtitle_streams(video_path):
    ffprobe_command = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "s",
        "-show_streams",
        "-show_entries", "stream=index,codec_name,disposition,tags",
        "-of", "json",
        video_path
    ]
    
    # JSON output should always be UTF-8. 
    # We'll use a safer version of _run_command_and_decode logic for JSON specifically.
    try:
        process = subprocess.run(
            ffprobe_command,
            capture_output=True,
            check=True
        )
        # Try UTF-8 first for JSON
        try:
            decoded_stdout = process.stdout.decode('utf-8')
        except UnicodeDecodeError:
            # Fallback to chardet if UTF-8 fails (extremely rare for JSON)
            import chardet
            detected = chardet.detect(process.stdout)['encoding'] or 'utf-8'
            decoded_stdout = process.stdout.decode(detected, errors='replace')
            
        probe_data = json.loads(decoded_stdout)
        return probe_data.get("streams", [])

    except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
        print(f"  Error probing subtitles in {video_path}: {e}")
        return None


def _generate_subtitle_filename(video_basename, stream_info, extension, output_dir):
    tags = stream_info.get('tags', {})
    disposition = stream_info.get('disposition', {})
    
    # Case-insensitive lookup for Title and Language in tags
    title = None
    language = None
    for k, v in tags.items():
        if k.lower() == 'title':
            title = v
        if k.lower() == 'language':
            language = _get_language_name(v)

    # Check for Forced flag in disposition (not tags)
    is_forced = str(disposition.get('forced', '0')) == '1'

    # Prioritize Language, then Title, then "Unknown"
    tag = language if language else (title if title else "Unknown")

    # Add [Forced] suffix if not already in the title
    if is_forced and "[Forced]" not in tag and "forced" not in tag.lower():
        tag = f"{tag} [Forced]"

    # Sanitize the tag
    # Allow alphanumeric (including Unicode letters like Á), spaces, (), [], -, _
    # Disallow typically risky chars for filenames: \ / : * ? " < > |
    illegal_chars = r'\/:*?"<>|'
    sanitized_tag = "".join(c for c in tag if c not in illegal_chars)
    sanitized_tag = sanitized_tag.strip()
    
    # Fallback if sanitization completely emptied the string
    if not sanitized_tag:
        sanitized_tag = "Unknown"

    filename = f"{video_basename} - {sanitized_tag}.{extension}"
    
    # Collision Handling: Append (1), (2), etc. if file exists
    base_name_no_ext = f"{video_basename} - {sanitized_tag}"
    counter = 1
    while os.path.exists(os.path.join(output_dir, filename)):
        filename = f"{base_name_no_ext} ({counter}).{extension}"
        counter += 1

    return filename


def _extract_subtitle_streams_as_srt(video_path, subtitle_streams_info, video_basename):
    if not subtitle_streams_info:
        return False

    extracted_count = 0
    print(f"  Attempting to extract {len(subtitle_streams_info)} text-based stream(s) to SRT format...")
    output_dir = os.path.dirname(video_path)

    for i, stream_info in enumerate(subtitle_streams_info):
        output_srt_filename = _generate_subtitle_filename(video_basename, stream_info, "srt", output_dir)
        output_srt_path = os.path.join(output_dir, output_srt_filename)

        ffmpeg_command = [
            "ffmpeg", "-i", video_path,
            "-map", f"0:{stream_info['index']}",
            "-y",
            output_srt_path
        ]

        print(f"    Extracting stream idx {stream_info['index']} ({stream_info.get('codec_name', 'unknown')}) to: {output_srt_path}")
        
        _, decoded_stderr, returncode = _run_command_and_decode(ffmpeg_command)
        
        if returncode == 0:
            print(f"      Successfully extracted: {output_srt_path}")
            extracted_count += 1
        else:
            print(f"      Failed to extract subtitle stream idx {stream_info['index']} as SRT.")
            print(f"        FFmpeg error: {decoded_stderr}")
            if os.path.exists(output_srt_path):
                try:
                    if os.path.getsize(output_srt_path) < 20:
                        os.remove(output_srt_path)
                        print(f"        Removed empty/failed SRT file: {output_srt_path}")
                except OSError as ose:
                    print(f"        Warning: Could not remove failed file {output_srt_path}: {ose}")

    if extracted_count > 0:
        print(f"  Successfully extracted {extracted_count} text-based subtitle stream(s) to SRT.")
    elif subtitle_streams_info:
        print(f"  No text-based subtitle streams could be successfully extracted.")
    return extracted_count > 0


def _package_single_subtitle_to_mkv(video_path, stream_info, subtitle_order_num, video_basename):
    output_dir = os.path.dirname(video_path)
    output_mkv_filename = _generate_subtitle_filename(video_basename, stream_info, "mkv", output_dir)
    output_mkv_path = os.path.join(output_dir, output_mkv_filename)

    ffmpeg_command = [
        "ffmpeg", "-i", video_path,
        "-map", f"0:{stream_info['index']}",
        "-c", "copy",
        "-y",
        output_mkv_path
    ]

    print(f"    Packaging stream idx {stream_info['index']} ({stream_info.get('codec_name', 'unknown')}) into MKV: {output_mkv_path}")
    
    _, decoded_stderr, returncode = _run_command_and_decode(ffmpeg_command)

    if returncode == 0:
        print(f"      Successfully packaged to: {output_mkv_path}")
        return True
    else:
        print(f"      Failed to package subtitle stream idx {stream_info['index']} into MKV.")
        print(f"        FFmpeg error: {decoded_stderr}")
        return False


def process_to_srt_files(video_path, video_basename):
    print(f"Mode: SRT")
    all_subtitle_streams_info = _probe_subtitle_streams(video_path)
    if all_subtitle_streams_info is None:
        return
    if not all_subtitle_streams_info:
        print(f"  No subtitle streams found in: {video_path}")
        return
    _extract_subtitle_streams_as_srt(video_path, all_subtitle_streams_info, video_basename)


def process_to_individual_mkv_subs(video_path, video_basename):
    print(f"Mode: MKV")
    all_subtitle_streams_info = _probe_subtitle_streams(video_path)
    if all_subtitle_streams_info is None:
        return
    if not all_subtitle_streams_info:
        print(f"  No subtitle streams found in: {video_path}")
        return

    packaged_count = 0
    for i, stream_info in enumerate(all_subtitle_streams_info):
        if _package_single_subtitle_to_mkv(video_path, stream_info, i + 1, video_basename):
            packaged_count += 1

    if packaged_count > 0:
        print(f"  Successfully packaged {packaged_count} subtitle stream(s).")


def process_hybrid(video_path, video_basename):
    print(f"Mode: HYBRID")
    all_subtitle_streams_info = _probe_subtitle_streams(video_path)
    if all_subtitle_streams_info is None:
        return
    if not all_subtitle_streams_info:
        print(f"  No subtitle streams found in: {video_path}")
        return

    text_subs_info = []
    non_text_subs_info = []
    for stream_info in all_subtitle_streams_info:
        codec_name = stream_info.get('codec_name', 'unknown').lower()
        if codec_name in KNOWN_TEXT_SUBTITLE_CODECS:
            text_subs_info.append(stream_info)
        else:
            non_text_subs_info.append(stream_info)

    if text_subs_info:
        _extract_subtitle_streams_as_srt(video_path, text_subs_info, video_basename)
    else:
        print(f"  No text-based subtitles found.")

    if non_text_subs_info:
        print(f"\n  Processing {len(non_text_subs_info)} non-text stream(s) to MKV format...")
        packaged_count = 0
        for i, stream_info in enumerate(non_text_subs_info):
            if _package_single_subtitle_to_mkv(video_path, stream_info, i + 1, video_basename):
                packaged_count += 1
        if packaged_count > 0:
            print(f"  Successfully packaged {packaged_count} non-text subtitle stream(s).")

    else:
        print(f"  No non-text subtitles found.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extracts or packages subtitles from video files. Default is 'hybrid' mode.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "-f", "--format",
        choices=['hybrid', 'srt', 'mkv'],
        default='hybrid',
        help="Processing mode:\n"
             "  hybrid (default): Extracts text subs to .srt, packages image subs to .mkv\n"
             "  srt: Attempts to convert ALL subs to .srt (will fail for image-based)\n"
             "  mkv: Packages ALL subs into individual .mkv files (lossless copy)"
    )
    parser.add_argument(
        "video_files_input",
        nargs='*',
        metavar='VIDEO_FILE_OR_PATTERN',
        help="Video files or patterns (e.g., 'folder/*.mkv').\n"
             "If omitted, scans recursively from the current directory."
    )

    parsed_args = parser.parse_args()
    input_items = parsed_args.video_files_input
    video_files_to_process_paths = []

    if input_items:
        for item in input_items:
            expanded_paths = glob.glob(item, recursive=True)
            for path in expanded_paths:
                if os.path.isfile(path):
                    video_files_to_process_paths.append(os.path.abspath(path))
    else:
        print("No video files provided. Recursively searching for supported video files...")
        supported_extensions = ('.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm')
        for root, _, files in os.walk(os.getcwd()):
            for f_name in files:
                if f_name.lower().endswith(supported_extensions):
                    full_path = os.path.join(root, f_name)
                    video_files_to_process_paths.append(os.path.abspath(full_path))

        if not video_files_to_process_paths:
            print("No supported video files found in this folder tree.")

    if not video_files_to_process_paths:
        print("No video files found to process.")
        sys.exit(0)

    unique_video_files = sorted(list(set(video_files_to_process_paths)))
    print(f"\nStarting subtitle processing (mode: {parsed_args.format.upper()})...")
    print(f"Found {len(unique_video_files)} video file(s) to process.")

    for video_file_path in unique_video_files:
        print(f"\n>>> Processing video file: {video_file_path}")
        if not os.path.exists(video_file_path):
            print(f"Error: File not found: {video_file_path}. Skipping.")
            continue

        video_basename_for_output = os.path.splitext(os.path.basename(video_file_path))[0]

        if parsed_args.format == 'srt':
            process_to_srt_files(video_file_path, video_basename_for_output)
        elif parsed_args.format == 'mkv':
            process_to_individual_mkv_subs(video_file_path, video_basename_for_output)
        elif parsed_args.format == 'hybrid':
            process_hybrid(video_file_path, video_basename_for_output)

    print(f"\nSubtitle processing (mode: {parsed_args.format.upper()}) completed.")