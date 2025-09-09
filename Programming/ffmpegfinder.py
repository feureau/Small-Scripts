"""
================================================================================
 FFmpeg SRT Subtitle Video Splitter (ffmpeg_srt_splitter.py)
================================================================================

Version: 4.1
Last Updated: 2025-09-07
Author: Gemini AI Assistant & User Collaboration

--------------------------------------------------------------------------------

 I. DESCRIPTION
--------------------------------------------------------------------------------

This script automates the process of cutting video clips from a source video
file based on a keyword search within a corresponding SRT subtitle file. It
leverages FFmpeg and NVIDIA's NVENC hardware acceleration for both decoding
and encoding to perform the splitting process as fast as possible.

The script is designed to be called from the command line, providing a video
file and a keyword. It will then find all subtitle entries containing that
keyword, extract the associated video segments, and save them as new MP4 files
with descriptive names that include the timestamp and the full subtitle quote.

--------------------------------------------------------------------------------

 II. PREREQUISITES
--------------------------------------------------------------------------------

1.  **Python 3:** The script is written in Python 3.
2.  **FFmpeg:** FFmpeg must be installed and accessible in the system's PATH.
    You can check this by typing `ffmpeg -version` in your terminal.
3.  **NVIDIA GPU:** An NVIDIA graphics card that supports NVENC is required for
    hardware acceleration. Ensure the latest NVIDIA drivers are installed.
4.  **Python `srt` library:** This is required for parsing the SRT file.
    Install it via pip:
    `pip install srt`

--------------------------------------------------------------------------------

 III. USAGE
--------------------------------------------------------------------------------

The script can be called from any directory, but it's typically run from the
directory containing the media files.

**Scenario 1: SRT file has the same name as the video file**
(e.g., `MyMovie.mp4` and `MyMovie.srt`)

> python /path/to/ffmpeg_srt_splitter.py "MyMovie.mp4" "keyword"

**Scenario 2: SRT file has a different name**

> python /path/to/ffmpeg_srt_splitter.py "MyMovie.mp4" "MyMovie_subs.srt" "keyword"

The output clips will be saved in a newly created sub-directory named
`[VideoFileName]_clips`.

--------------------------------------------------------------------------------

 IV. REVISION HISTORY & TECHNICAL RATIONALE
--------------------------------------------------------------------------------

This script has undergone several iterations to fix bugs and improve
performance. Understanding this history is key to understanding its structure.

**v1.0 - Initial Concept:**
-   **Goal:** Create a basic script to split a video using SRT timestamps.
-   **Implementation:** Used the `subprocess` module to call FFmpeg. The FFmpeg
    command used `-ss` (seek) *after* the `-i` (input) flag.
-   **Problem:** This "output seeking" was extremely slow because FFmpeg had
    to decode the video from the beginning for every single clip.

**v2.0 - Flexibility & Pathing Fix:**
-   **Goal:** Allow the script to be called from a different folder and make
    the SRT file argument optional.
-   **Implementation:** Added logic to infer the SRT filename if not provided.
-   **Problem:** FFmpeg started failing with a "Permission denied" error.
-   **Rationale for Fix:** This error was misleading. The root cause was that
    relative paths to files with complex names (containing many dots) were
    not being resolved correctly by the subprocess call. The fix was to use
    `os.path.abspath()` on all input file paths to provide FFmpeg with a
    full, unambiguous path, which solved the issue.

**v3.0 - Major Performance Overhaul (Hardware Acceleration):**
-   **Goal:** Drastically increase the export speed.
-   **Implementation:** Two key changes were made to the FFmpeg command.
    1.  **Fast Seeking:** The `-ss` flag was moved *before* the `-i` flag. This
        enables "input seeking," which uses the video's keyframe index to
        jump almost instantly to the start time instead of decoding the whole
        file. This was the single biggest speed improvement.
    2.  **Hardware Decoding:** The flag `-c:v hevc_cuvid` was added as an
        input option. This tells FFmpeg to use the GPU's dedicated hardware
        to decode the source H.265 (x265) video, offloading a massive amount
        of work from the CPU.
-   **Problem:** This led to a new error: `Invalid argument`. The hardware
    decoder and encoder were not communicating correctly.

**v3.1 - HDR to SDR Conversion Fix:**
-   **Goal:** Fix the hardware acceleration pipeline.
-   **Problem:** The FFmpeg log revealed the true error:
    `10 bit encode not supported`. The source video was 10-bit HDR (as
    confirmed by the `yuv420p10le` pixel format), but the target encoder
    (`h264_nvenc`) only supports 8-bit color for standard H.264 profiles.
-   **Rationale for Fix:** A video filter (`-vf`) was added to the FFmpeg
    command: `format=yuv420p`. This filter is inserted into the pipeline
    after decoding but before encoding. It correctly converts the 10-bit
    pixel format to the 8-bit format that `h264_nvenc` can handle. FFmpeg is
    often able to perform this conversion on the GPU, maintaining high speed.

**v4.0 - Feature: Descriptive Filenames:**
-   **Goal:** Make output filenames more useful, including the timestamp and
    the full subtitle quote.
-   **Implementation:** A `sanitize_filename` function was created to remove
    illegal characters (`/ \ : * ? " < > |`) and control the filename length
    to avoid OS errors.
-   **Problem:** This introduced a Python `AttributeError`.

**v4.1 - Bug Fix: Timestamp Formatting:**
-   **Goal:** Fix the crash from the new filename logic.
-   **Problem:** The error `AttributeError: 'timedelta' object has no attribute
    'minutes'` occurred.
-   **Rationale for Fix:** A `timedelta` object from the `srt` library does
    not have separate `.hour` or `.minute` attributes. The fix was to create
    a dedicated helper function (`format_timedelta_for_filename`) that
    correctly calculates the hours, minutes, and seconds from the
    `timedelta.total_seconds()` method.

--------------------------------------------------------------------------------

 V. FUTURE MAINTENANCE
--------------------------------------------------------------------------------

Any developer modifying this script in the future is required to update this
documentation block, especially the "Revision History & Technical Rationale"
section. This will ensure that the reasons for specific, non-obvious code
(like the FFmpeg flags) are preserved for future maintenance and debugging.

================================================================================
"""

import srt
import subprocess
import sys
import os
import re
from datetime import timedelta

def sanitize_filename(text: str, max_length: int = 150) -> str:
    """
    Sanitizes a string to be used as a valid filename.
    - Removes illegal characters.
    - Replaces newlines and tabs with spaces.
    - Truncates to a maximum length.
    - Strips leading/trailing whitespace.
    """
    text = re.sub(r'[\r\n\t]+', ' ', text)
    text = re.sub(r'[\\/*?:"<>|]', "", text)
    if len(text) > max_length:
        text = text[:max_length].rsplit(' ', 1)[0] + '...'
    return text.strip()

def format_time_for_ffmpeg(td: timedelta) -> str:
    """Converts a timedelta object to an FFmpeg-compatible HH:MM:SS.ms string."""
    total_seconds = td.total_seconds()
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = td.microseconds // 1000
    return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}.{milliseconds:03}"

def format_timedelta_for_filename(td: timedelta) -> str:
    """
    FIXED: Correctly formats a timedelta into a HHhMMmSSs string for filenames.
    """
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02}h{minutes:02}m{seconds:02}s"

def main():
    """
    Finds a keyword in an SRT file and splits a video based on the timestamps.
    This version uses descriptive filenames and is optimized for speed, handling
    10-bit to 8-bit conversion.
    """
    if len(sys.argv) not in [3, 4]:
        print("Usage: python /path/to/ffmpegfinder.py <video_file> [srt_file] \"<keyword>\"")
        sys.exit(1)

    video_file = os.path.abspath(sys.argv[1])

    if len(sys.argv) == 4:
        srt_file = os.path.abspath(sys.argv[2])
        keyword = sys.argv[3]
    else:
        keyword = sys.argv[2]
        base_name, _ = os.path.splitext(video_file)
        srt_file = base_name + ".srt"
        print(f"SRT file not specified. Attempting to use '{os.path.basename(srt_file)}'...")

    if not os.path.exists(video_file) or not os.path.exists(srt_file):
        print(f"Error: Could not find video or SRT file.")
        sys.exit(1)

    try:
        with open(srt_file, 'r', encoding='utf-8') as f:
            subtitles = list(srt.parse(f.read()))
    except Exception as e:
        print(f"Error reading or parsing SRT file: {e}")
        sys.exit(1)

    video_parent_dir = os.path.dirname(video_file)
    output_dir_name = f"{os.path.splitext(os.path.basename(video_file))[0]}_clips"
    output_path = os.path.join(video_parent_dir, output_dir_name)
    os.makedirs(output_path, exist_ok=True)

    print(f"Searching for keyword '{keyword}' in '{os.path.basename(srt_file)}'...")

    found_subs = [sub for sub in subtitles if keyword.lower() in sub.content.lower()]
    total_clips = len(found_subs)
    clip_count = 0

    for sub in found_subs:
        clip_count += 1
        start = sub.start
        end = sub.end
        duration = end - start

        # --- REVISED FILENAME LOGIC ---
        # 1. Use the new helper function to format timestamps correctly
        start_fn_str = format_timedelta_for_filename(start)
        end_fn_str = format_timedelta_for_filename(end)
        timestamp_for_name = f"[{start_fn_str}] to [{end_fn_str}]"
        
        # 2. Sanitize the full quote
        quote_for_name = sanitize_filename(sub.content)

        # 3. Combine into the final filename
        base_filename = f"{timestamp_for_name} {quote_for_name}.mp4"
        output_filename = os.path.join(output_path, base_filename)

        # --- FFmpeg Timestamps ---
        start_time_str = format_time_for_ffmpeg(start)
        duration_str = format_time_for_ffmpeg(duration)

        print(f"\n[Clip {clip_count}/{total_clips}] Found keyword in subtitle #{sub.index}:")
        print(f"  Timestamp: {format_time_for_ffmpeg(start)} --> {format_time_for_ffmpeg(end)}")
        print(f"  Exporting to '{base_filename}'...")

        command = [
            'ffmpeg',
            '-y',
            '-loglevel', 'error',
            '-c:v', 'hevc_cuvid',
            '-ss', start_time_str,
            '-i', video_file,
            '-t', duration_str,
            '-vf', 'format=yuv420p',
            '-c:v', 'h264_nvenc',
            '-preset', 'fast',
            '-c:a', 'copy',
            output_filename
        ]

        try:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace')
            stdout, stderr = process.communicate()
            if process.returncode != 0:
                print(f"  ERROR: FFmpeg failed for clip {clip_count}.")
                print("  " + "="*30)
                print(f"  FFmpeg stderr output:\n{stderr}")
                print("  " + "="*30)
            else:
                print("  Successfully created video clip.")
        except FileNotFoundError:
            print("\nError: 'ffmpeg' command not found. Is it in your system's PATH?")
            sys.exit(1)
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

    if clip_count > 0:
        print(f"\nProcessing complete. Found and exported {clip_count} clip(s) to the '{output_path}' directory.")
    else:
        print(f"\nNo subtitles containing the keyword '{keyword}' were found.")

if __name__ == "__main__":
    main()