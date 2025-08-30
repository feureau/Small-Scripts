#!/usr/bin/env python3

"""
# yt-dlp Downloader: A Robust Parallel Downloader

A powerful, multi-purpose wrapper script for the command-line tool 'yt-dlp'.
It can download video, audio-only, subtitles, thumbnails, and metadata for every video
within a given YouTube playlist (or for a single video). It is optimized for
handling very large playlists by processing downloads in parallel.

## Key Features

- **Multi-Purpose Downloading**: Download exactly what you need with simple command-line flags for video, audio, SRT files, thumbnails, and metadata.
- **Powerful Default**: If no flags are specified, the script performs a "full-package" download: the best quality video and audio are merged into an MP4, with the thumbnail embedded, metadata included, and English SRT subtitles saved alongside.
- **High-Speed Parallelism**: Utilizes a thread pool to download multiple files concurrently, dramatically speeding up the process for large playlists.
- **Clean & Sequential Logging**: Prints progress to the console in a clean, scrolling format. Each task's start and end status is printed on its own line without messy, overlapping text from other threads.
- **Robust Shutdown**: Implements a powerful signal handler for `Ctrl-C` (KeyboardInterrupt). It immediately terminates all running `yt-dlp` subprocesses, cancels all pending downloads, and forces the script to exit cleanly, preventing orphaned processes.
- **Intelligent Playlist Parsing**: Efficiently fetches a list of all video IDs from a playlist URL without downloading any video data first, making it fast to start.

---

## Requirements

1.  **Python 3**: The script is written for Python 3.
2.  **yt-dlp**: The core command-line tool. It must be installed and accessible.
    - Installation instructions: https://github.com/yt-dlp/yt-dlp#installation
3.  **FFmpeg**: Required by `yt-dlp` for merging video and audio streams (essential for the default and `--video` downloads) and for audio conversions (`--audio`).
    - Installation instructions: https://ffmpeg.org/download.html

---

## Installation & Configuration

1.  **Save the Script**: Save the code as a Python file, for example, `yt-dlp-downloader.py`.

2.  **Configure Variables**: Open the script and edit the `USER CONFIGURABLE VARIABLES` section at the top:
    - `YTDLP_PATH`: The path to your `yt-dlp` executable. If it's in your system's PATH, the default value `"yt-dlp"` is sufficient. Otherwise, provide the full path (e.g., `"C:/Tools/yt-dlp.exe"` or `"/usr/local/bin/yt-dlp"`).
    - `OUTPUT_TEMPLATE`: The filename pattern for the downloaded files. The default saves them to the current directory with the video's title. You can customize this using `yt-dlp` output template variables.
    - `PARALLEL_DOWNLOADS`: The number of files to download at the same time. `6` is a good starting point. Increase it if you have a fast internet connection, or decrease it if you experience network issues.

---

## Usage

Run the script from your terminal. The basic syntax is:
python3 yt-dlp-downloader.py <playlist-or-video-url> [OPTIONS]
Default Behavior (No Flags)

If you run the script with only a URL, it performs a full-package download for each video. This is the most comprehensive option and includes:

Best quality video (preferring AV1 codec) and best quality audio, merged into a single MP4 file.

English auto-captions downloaded and converted to an SRT subtitle file.

The video thumbnail downloaded as a separate .webp or .jpg file.

The thumbnail is also embedded into the final MP4 file.

Video metadata (title, author, etc.) is written into the MP4 file.

Example:
python3 yt-dlp-downloader.py "https://www.youtube.com/playlist?list=PL..."
Command-Line Options

Use flags to download only the specific components you need. Using any flag will override the default behavior.

Flag	Short	Description
--video	-v	Video Only: Downloads the best video and audio streams and merges them into a single MP4 file. No extras.
--audio	-a	Audio Only: Extracts the best available audio and converts it to a high-quality MP3 file.
--srt		Subtitles Only: Downloads and converts subtitles to SRT format. Does not download the video or audio.
--thumbnail		Thumbnail Only: Downloads the video thumbnail as a separate image file.
--metadata		Metadata Only: Downloads the video's metadata and saves it as a .json file.
Usage Examples

Download only the video and audio for a single video:
python3 yt-dlp-downloader.py "https://www.youtube.com/watch?v=..." --video

Download only the MP3 audio for an entire playlist:
python3 yt-dlp-downloader.py "https://www.youtube.com/playlist?list=PL..." --audio

Download both the video file AND the SRT subtitles for a playlist:
python3 yt-dlp-downloader.py "https://www.youtube.com/playlist?list=PL..." --video --srt

Get just the thumbnails and metadata JSON files for a playlist:
python3 yt-dlp-downloader.py "https://www.youtube.com/playlist?list=PL..." --thumbnail --metadata

Design Philosophy

This script has been intentionally designed for robustness and reliability, especially with large playlists where errors or interruptions are more likely.

Granular Control: Instead of one massive yt-dlp job, the script first fetches a list of all video IDs and then launches a separate, dedicated process for each video. This provides better error handling and progress tracking.

Thread-Safe Logging: A threading.Lock is used for all print() calls. This simple but effective mechanism prevents the console output from becoming a scrambled, unreadable mess when multiple threads are logging their status simultaneously.

Forceful Shutdown: The Ctrl-C signal handler is designed to be forceful (os._exit(1)) to guarantee that the user immediately regains control of their terminal, preventing the script from hanging while waiting for threads or subprocesses that may not terminate gracefully on their own.

"""

import subprocess
import sys
import json
import os
import signal
import threading
import argparse
from concurrent.futures import ThreadPoolExecutor

# ================== USER CONFIGURABLE VARIABLES ==================
YTDLP_PATH = "yt-dlp"  # Path to yt-dlp executable (use full path if needed)
OUTPUT_TEMPLATE = os.path.join(os.getcwd(), "%(title)s.%(ext)s")
PARALLEL_DOWNLOADS = 6  # Number of yt-dlp processes to run in parallel
# ================================================================

# --- Globals for State Management and Shutdown ---
running_processes = set()
process_lock = threading.Lock()
print_lock = threading.Lock()
executor = None # Will hold the ThreadPoolExecutor instance

def run_download_task(video_id, title, index, total, args):
    """
    Runs a single yt-dlp download task, printing its status cleanly.
    """
    display_title = (title[:80] + '...') if len(title) > 80 else title

    with print_lock:
        print(f"[{index:>4}/{total}] ▶️ Starting: {display_title}")

    command_str = build_command(video_id, args)
    process = None
    try:
        process = subprocess.Popen(
            command_str,
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        with process_lock:
            running_processes.add(process)

        process.wait()

        if process.returncode == 0:
            final_status = f"[{index:>4}/{total}] ✅ Finished: {display_title}"
        else:
            final_status = f"[{index:>4}/{total}] ❌ Failed:   {display_title}"

    except Exception as e:
        final_status = f"[{index:>4}/{total}] ❌ Error:    {e}"
    finally:
        if process:
            with process_lock:
                running_processes.discard(process)
        with print_lock:
            print(final_status)


def get_playlist_videos(url):
    """Get a list of video IDs and titles from a playlist or single video."""
    print("📋 Fetching playlist information, please wait...")
    command = [YTDLP_PATH, "--flat-playlist", "--dump-json", url]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to fetch playlist info. Is yt-dlp installed and in your PATH?")
        print(f"   Error: {e.stderr}")
        sys.exit(1)

    videos = []
    for line in result.stdout.strip().splitlines():
        data = json.loads(line)
        videos.append((data["id"], data.get("title", f"Video_{data['id']}")))
    return videos

### MODIFIED: This function has been significantly refactored to handle the
### new default "full package" download vs. specific flag-based downloads.
def build_command(video_id, args):
    """Build the full yt-dlp command based on parsed command-line arguments."""
    base_command = (
        f'{YTDLP_PATH} --no-progress --no-warnings '
        f'-o "{OUTPUT_TEMPLATE}" "https://www.youtube.com/watch?v={video_id}"'
    )
    
    # This format string is used for both the default and --video flags.
    # It prioritizes AV1 video and M4A audio, with fallbacks.
    video_format_selector = '-f "bestvideo[vcodec^=av01]+bestaudio[ext=m4a]/bestvideo+bestaudio[ext=m4a]/bestvideo+bestaudio"'
    
    command_parts = [base_command]

    # Check for the special default case (no flags specified)
    if getattr(args, 'default_download', False):
        command_parts.extend([
            video_format_selector,
            "--audio-multistreams",
            "--audio-format aac",
            "--embed-thumbnail",
            "--add-metadata",
            "--merge-output-format mp4",
            "--write-thumbnail",
            "--write-auto-sub",
            "--sub-lang en",
            "--convert-subs srt"
        ])
    else: # Handle individual flags if the default is not used
        if args.video:
            command_parts.append(video_format_selector)
            command_parts.append("--merge-output-format mp4")

        if args.audio:
            command_parts.append("--extract-audio --audio-format mp3 --audio-quality 0")

        if args.srt:
            command_parts.append("--write-subs --convert-subs srt")
            # If ONLY subs are requested, we should skip the video download part.
            if not args.video and not args.audio:
                command_parts.append("--skip-download")

        if args.thumbnail:
            command_parts.append("--write-thumbnail")
            # If ONLY the thumbnail is requested, skip the main download.
            if not args.video and not args.audio and not args.srt:
                 command_parts.append("--skip-download")
                 
        if args.metadata:
            command_parts.append("--write-json")
            # If ONLY metadata is requested, skip the main download.
            if not args.video and not args.audio and not args.srt and not args.thumbnail:
                command_parts.append("--skip-download")
                
    return " ".join(command_parts)


def signal_handler(sig, frame):
    """Handle Ctrl-C: shut down executor, terminate processes, and force exit."""
    with print_lock:
        print("\n\n⚠️ Ctrl-C detected! Forcing shutdown...", flush=True)

    with process_lock:
        for proc in list(running_processes):
            proc.terminate()

    if executor:
        executor.shutdown(wait=False, cancel_futures=True)

    print("Graceful shutdown complete. Exiting.", flush=True)
    os._exit(1)

def main():
    global executor

    ### MODIFIED: Updated argparse help messages to be clearer.
    parser = argparse.ArgumentParser(
        description="A robust, parallel downloader for YouTube playlists using yt-dlp.",
        epilog="If no download type flag is specified, a full package (video, subs, thumbnail, metadata) is downloaded."
    )
    parser.add_argument("url", help="The URL of the YouTube playlist or single video.")
    parser.add_argument(
        "-v", "--video", action="store_true", help="Download video only (best video + best audio merged into MP4)."
    )
    parser.add_argument(
        "-a", "--audio", action="store_true", help="Download audio-only (best quality, converted to MP3)."
    )
    parser.add_argument(
        "--srt", action="store_true", help="Download subtitles in SRT format."
    )
    parser.add_argument(
        "--thumbnail", action="store_true", help="Download the video thumbnail as a separate file."
    )
    parser.add_argument(
        "--metadata", action="store_true", help="Write video metadata to a .json file."
    )
    args = parser.parse_args()

    ### MODIFIED: Logic to set a 'default_download' flag if no other type is selected.
    is_any_type_selected = any([args.video, args.audio, args.srt, args.thumbnail, args.metadata])
    if not is_any_type_selected:
        print("No download type specified. Using default full-package download (video, subs, thumbnail, metadata).")
        args.default_download = True
    else:
        args.default_download = False

    # Register the robust signal handler immediately
    signal.signal(signal.SIGINT, signal_handler)

    videos = get_playlist_videos(args.url)
    total = len(videos)
    
    print(f"✅ Found {total} videos. Starting parallel download ({PARALLEL_DOWNLOADS} workers).\n")

    with ThreadPoolExecutor(max_workers=PARALLEL_DOWNLOADS) as exec_instance:
        executor = exec_instance
        
        for i, (vid, title) in enumerate(videos, start=1):
            executor.submit(run_download_task, vid, title, i, total, args)

    print("\n🎉 All tasks completed.")


if __name__ == "__main__":
    main()