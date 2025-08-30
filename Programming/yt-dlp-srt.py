#!/usr/bin/env python3
"""
yt-dlp-srt.py
-----------------------------------

PURPOSE:
A robust wrapper script for the command-line tool 'yt-dlp'. Its primary function
is to efficiently download subtitles in SRT format for every video within a given
YouTube playlist (or for a single video). It is optimized for handling very large
playlists by processing downloads in parallel.

KEY FEATURES:
- Playlist Parsing: Intelligently fetches a list of all video IDs from a
  playlist URL without downloading any video data first.
- Parallel Downloads: Utilizes a thread pool to download multiple subtitle files
  concurrently, dramatically speeding up the process for large playlists.
- Clean & Sequential Logging: Prints progress to the console in a clean,
  scrolling format. Each task's start and end status is printed on its own
  line without messy, overlapping text from other threads.
- Robust Shutdown: Implements a powerful signal handler for Ctrl-C
  (KeyboardInterrupt). When pressed, it immediately terminates all running
  yt-dlp subprocesses, cancels all pending downloads, and forces the script
  to exit cleanly, preventing it from hanging or leaving orphaned processes.
- User Configuration: Key settings like the path to yt-dlp and the number of
  parallel workers can be easily changed in the configuration section.

-------------------------------------------------------------------------------
HISTORY OF CHOICES / DESIGN EVOLUTION:
This script has undergone several revisions, with each change addressing problems
discovered in the previous version. Understanding this evolution explains why the
script is designed the way it is today.

1. INITIAL APPROACH: THE SINGLE COMMAND PROBLEM
   - The first idea was to simply wrap a single yt-dlp command with the right flags.
   - PROBLEM: yt-dlp processes an entire playlist as a single job. This offered
     poor control. If one subtitle failed, it could complicate the entire batch.
     It also made implementing custom progress logging difficult.

2. GRANULAR CONTROL: PER-VIDEO PROCESSING
   - DECISION: The script was changed to first fetch a list of all video IDs
     in the playlist using `yt-dlp --flat-playlist --dump-json`.
   - JUSTIFICATION: This pivotal change allowed the script to iterate through
     the videos and launch a separate, dedicated `yt-dlp` process for each one.
     This provides granular control, better error handling (one failure doesn't
     stop everything), and enables custom progress tracking (e.g., "[5/1998]").

3. PERFORMANCE: ADDING PARALLELISM
   - DECISION: To handle large playlists efficiently, Python's
     `concurrent.futures.ThreadPoolExecutor` was introduced.
   - JUSTIFICATION: This allows multiple `yt-dlp` subprocesses to run at the
     same time, limited by the `PARALLEL_DOWNLOADS` variable. This turns a slow,
     sequential process into a much faster, parallel one.

4. THE CONSOLE OUTPUT CHALLENGE: A Multi-Stage Evolution
   - PROBLEM: With multiple threads printing to the console simultaneously, the
     output became a jumbled, overlapping, and unreadable mess.
   - ATTEMPT 1 (FAILED): A dynamic, full-screen display was created using ANSI
     escape codes to clear the screen and redraw the status of N workers in fixed
     positions.
     - WHY IT FAILED: This was overly complex, caused flickering, and behaved
       inconsistently across different operating systems and terminal emulators.
   - ATTEMPT 2 (FAILED): A simpler approach using the carriage return `\r` to
     overwrite a single line in-place was tried.
     - WHY IT FAILED: This also proved unreliable. When the console scrolled,
       threads would fight to update the same line, resulting in garbled text.
       The `]]]]]]]` progress bar artifacts from yt-dlp also interfered with it.
   - FINAL SOLUTION (ROBUST AND SIMPLE): All complex cursor manipulation was
     abandoned. The current design uses a simple `threading.Lock` around every
     `print()` call.
     - JUSTIFICATION: This is the most reliable solution. While it doesn't offer
       fancy in-place updates, it guarantees that every line printed to the
       console is a complete, atomic message. This results in a clean, universally
       compatible scrolling log that is easy to read and impossible to corrupt.
       The `]]]]]]` artifacts were also removed by adding the `--no-progress`
       flag to the yt-dlp command.

5. THE GRACEFUL SHUTDOWN CHALLENGE
   - PROBLEM: Simply catching `KeyboardInterrupt` was not enough. The main thread
     would exit, but the `ThreadPoolExecutor` and the child `yt-dlp.exe` processes
     would continue running in the background, leaving the script "stuck".
   - FINAL SOLUTION (FORCEFUL AND CLEAN): A custom `signal_handler` for SIGINT
     (the signal sent by Ctrl-C) was implemented.
     - JUSTIFICATION: This handler does three things to guarantee a clean exit:
       1. It terminates all known running `yt-dlp` subprocesses directly.
       2. It calls `executor.shutdown(wait=False, cancel_futures=True)` to
          immediately cancel all queued tasks in the thread pool.
       3. It calls `os._exit(1)` for an immediate, non-negotiable termination of
          the Python script itself. This is a deliberate choice to prevent the
          script from hanging while waiting for threads that might not close
          cleanly, ensuring the user regains control of their terminal instantly.

-------------------------------------------------------------------------------
USER-CONFIGURABLE VARIABLES:
 - YTDLP_PATH: The path to your yt-dlp executable. If it's in your system's
   PATH, "yt-dlp" is sufficient. Otherwise, use a full path.
 - OUTPUT_TEMPLATE: The filename pattern for the downloaded SRT files. The
   default saves them to the current directory with the video's title.
 - PARALLEL_DOWNLOADS: The number of videos to download at the same time. A
   good default is 6, but this can be tuned based on your network and CPU.

USAGE:
   python3 yt-dlp-srt.py <playlist-or-video-url>
"""

import subprocess
import sys
import json
import os
import signal
import threading
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

def run_download_task(video_id, title, index, total):
    """
    Runs a single yt-dlp download task, printing its status cleanly.
    """
    display_title = (title[:80] + '...') if len(title) > 80 else title

    with print_lock:
        print(f"[{index:>4}/{total}] ▶️ Starting: {display_title}")

    command = build_command(video_id)
    process = None
    try:
        process = subprocess.Popen(
            command,
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

def build_command(video_id):
    """Build yt-dlp command for downloading subtitles of a single video."""
    # Added --no-progress to prevent the `]]]]]]` progress bar output
    return (
        f"{YTDLP_PATH} --no-progress --skip-download --write-subs --convert-subs srt "
        f"-o \"{OUTPUT_TEMPLATE}\" \"https://www.youtube.com/watch?v={video_id}\""
    )

def signal_handler(sig, frame):
    """Handle Ctrl-C: shut down executor, terminate processes, and force exit."""
    with print_lock:
        print("\n\n⚠️ Ctrl-C detected! Forcing shutdown...", flush=True)

    # Terminate all running yt-dlp subprocesses
    with process_lock:
        for proc in list(running_processes):
            proc.terminate()

    # Forcefully shut down the thread pool
    # This cancels pending tasks and does not wait for running ones
    if executor:
        executor.shutdown(wait=False, cancel_futures=True)

    # Use os._exit for an immediate, forceful exit.
    # This is necessary because some threads might be stuck waiting.
    print("Graceful shutdown complete. Exiting.", flush=True)
    os._exit(1)

def main():
    global executor
    if len(sys.argv) < 2:
        print("Usage: yt-dlp-srt.py <playlist-or-video-url>")
        sys.exit(1)

    # Register the robust signal handler immediately
    signal.signal(signal.SIGINT, signal_handler)

    url = sys.argv[1]
    videos = get_playlist_videos(url)
    total = len(videos)
    
    print(f"✅ Found {total} videos. Starting parallel download ({PARALLEL_DOWNLOADS} workers).\n")

    with ThreadPoolExecutor(max_workers=PARALLEL_DOWNLOADS) as exec_instance:
        executor = exec_instance # Make the executor instance globally accessible to the signal handler
        
        # Submit all tasks
        for i, (vid, title) in enumerate(videos, start=1):
            executor.submit(run_download_task, vid, title, i, total)

    # This part will only be reached if all tasks complete without Ctrl-C
    print("\n🎉 All tasks completed.")


if __name__ == "__main__":
    main()