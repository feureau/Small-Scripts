#!/usr/bin/env python3
"""
transcribe_with_yt_dlp.py - Download media from YouTube via yt-dlp and transcribe with Faster Whisper XXL
--------------------------------------------------------------------------------------------------
- Downloads audio (default) or video (with -v) from YouTube URLs into a temporary directory
  within the current working directory.
- Transcribes with Whisper XXL, showing live progress, then (by default) cleans up downloads.
- Use -s/--save to keep downloaded files (and the temp directory) after completion.
- Saves SRT or text output in the specified output directory (or CWD by default) with timestamped filenames
  that include the video title (sanitized) in the format: title_inputbase_timestamp.ext.
- Supports diarization, language, model, sentence splitting, audio enhancements, etc.

Requirements:
- Python >=3.7
- Packages: yt-dlp, faster-whisper, torch, pyannote.audio (if diarization)
- CLI Tools: ffmpeg (for postprocessing)

Environment:
- Set HF_TOKEN for Hugging Face access if required.
"""

import sys
import os
import subprocess
import tempfile
import shutil
import tkinter as tk
from tkinter import filedialog
from datetime import datetime
import argparse
import glob
import re
import traceback # Added for debug printing
from typing import Tuple, Optional # Added for type hinting

# Attempt to import yt-dlp
try:
    from yt_dlp import YoutubeDL
except ImportError:
    print("❌ yt-dlp not found. Install via `pip install yt-dlp`.")
    sys.exit(1)

# ------------------- DEFAULT CONFIGURATION ------------------- #
DEFAULT_MODEL = "large-v2"
DEFAULT_TASK = "transcribe"
DEFAULT_ENABLE_DIARIZATION = False
DEFAULT_LANGUAGE = None
DEFAULT_SENTENCE = True
DEFAULT_MAX_COMMA = 2
DEFAULT_MAX_GAP = 0.1
DEFAULT_MAX_LINE_COUNT = 1
DEFAULT_FF_RNNDN_XIPH = True
DEFAULT_FF_SPEECHNORM = True
ENABLE_DIARIZATION_METHOD = "pyannote_v3.1"
HF_TOKEN = os.getenv("HF_TOKEN")

# ------------------ FUNCTION DEFINITIONS ------------------ #

# ==============================================================
# START OF MODIFIED download_media_from_youtube FUNCTION (Returns path and title)
# ==============================================================
def download_media_from_youtube(url: str, download_dir: str, download_video: bool) -> Tuple[Optional[str], Optional[str]]:
    """
    Download best audio (wav) or best video+audio (container) from YouTube URL.
    Returns a tuple: (local_path_to_downloaded_file, video_title).
    Returns (None, None) on failure.
    Includes enhanced debugging and file finding.
    """
    print(f"--- Debug: Starting download for {url} into {download_dir}")
    os.makedirs(download_dir, exist_ok=True)

    # --- ydl_opts for Debugging (verbose) ---
    if download_video:
        ydl_opts = {
            'format': 'bestvideo+bestaudio',
            'outtmpl': os.path.join(download_dir, '%(id)s.%(ext)s'),
            'merge_output_format': 'mp4',
            'noprogress': False,
            'verbose': True,
            'logtostderr': True,
            'ignoreerrors': False,
        }
    else:
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(download_dir, '%(id)s.%(ext)s'), # Download with original ext
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'wav',
                'preferredquality': '192',
            }],
            'noprogress': False,
            'verbose': True,
            'logtostderr': True,
            'ignoreerrors': False,
        }
    # --- End ydl_opts ---

    expected_media_path = None
    info = None # Initialize info
    prepared_filename_base = None # Initialize
    video_title = "unknown_title" # Default title

    try:
        print(f"--- Debug: Initializing YoutubeDL with opts: {ydl_opts}")
        with YoutubeDL(ydl_opts) as ydl:
            print(f"--- Debug: Calling extract_info for {url}")
            # Ensure download happens
            info = ydl.extract_info(url, download=True)

            if info is None:
                 print(f"--- Debug: extract_info returned None")
                 raise ValueError("yt-dlp extract_info returned None, cannot determine filenames.")
            else:
                 print(f"--- Debug: extract_info successful. Info dict keys: {list(info.keys())}")
                 # --- GET TITLE HERE ---
                 video_title = info.get('title', 'unknown_title') # Extract title
                 print(f"--- Debug: Extracted Title: {video_title}")
                 # --- END GET TITLE ---
                 try:
                     print(f"--- Debug: Calling prepare_filename(info) without explicit outtmpl")
                     prepared_filename_base = ydl.prepare_filename(info)
                     print(f"--- Debug: prepare_filename returned: {prepared_filename_base}")
                 except AttributeError as ae:
                     print(f"--- Debug: AttributeError occurred even without explicit outtmpl in prepare_filename: {ae}")
                     traceback.print_exc()
                     raise # Re-raise the original error
                 except Exception as prep_e:
                      print(f"--- Debug: Error during prepare_filename(info): {prep_e}")
                      traceback.print_exc()
                      prepared_filename_base = None # Reset on error


            # Construct the expected final path
            video_id = 'unknown_id'
            if info and info.get('id'):
                video_id = info.get('id')
            elif 'youtube.com' in url or 'youtu.be' in url:
                 try: video_id = url.split('v=')[-1].split('&')[0]
                 except: pass

            if not download_video:
                expected_media_path = os.path.join(download_dir, f"{video_id}.wav")
                print(f"--- Debug: Expecting audio output at: {expected_media_path}")
            else:
                expected_media_path = os.path.join(download_dir, f"{video_id}.mp4")
                print(f"--- Debug: Expecting video output at: {expected_media_path}")

            print(f"--- Debug: Checking existence of expected path: {expected_media_path}")
            if expected_media_path and os.path.exists(expected_media_path):
                print(f"--- Debug: Expected path found!")
                # --- RETURN PATH AND TITLE ---
                return os.path.abspath(expected_media_path), video_title
            else:
                if prepared_filename_base and os.path.exists(prepared_filename_base):
                     target_ext = ".wav" if not download_video else "." + ydl_opts.get('merge_output_format', 'mp4')
                     if prepared_filename_base.lower().endswith(target_ext):
                          print(f"--- Debug: Found file matching prepare_filename result: {prepared_filename_base}")
                          # --- RETURN PATH AND TITLE ---
                          return os.path.abspath(prepared_filename_base), video_title

                print(f"--- Debug: Expected path ({expected_media_path}) NOT found.")
                # --- Fallback Search ---
                print(f"--- Debug: Listing contents of download directory: {download_dir}")
                try:
                    files_in_dir = os.listdir(download_dir)
                    print(f"--- Debug: Files found: {files_in_dir}")
                except Exception as list_e:
                    print(f"--- Debug: Error listing directory {download_dir}: {list_e}")
                    files_in_dir = []

                target_ext = ".wav" if not download_video else "." + ydl_opts.get('merge_output_format', 'mp4')
                id_potential_files = [f for f in files_in_dir if f.startswith(video_id) and f.lower().endswith(target_ext)]

                if id_potential_files:
                    found_path = os.path.join(download_dir, id_potential_files[0])
                    print(f"--- Debug: Fallback found a file matching ID and extension: {found_path}")
                    # --- RETURN PATH AND TITLE ---
                    return os.path.abspath(found_path), video_title
                else:
                     potential_files = [f for f in files_in_dir if f.lower().endswith(target_ext)]
                     if potential_files:
                        found_path = os.path.join(download_dir, potential_files[0])
                        print(f"--- Debug: Fallback found a file matching extension (no ID match): {found_path}")
                        # --- RETURN PATH AND TITLE ---
                        return os.path.abspath(found_path), video_title
                     else:
                        if not download_video:
                             original_audio_files = [f for f in files_in_dir if f.startswith(video_id) and f.lower().endswith(('.m4a', '.webm', '.mp3', '.ogg', '.opus'))]
                             if original_audio_files:
                                  print(f"--- Debug: WARNING! Expected {target_ext} not found, but original audio download might exist: {original_audio_files}")
                                  print(f"--- Debug: This likely indicates an FFMPEG post-processing error.")
                             else:
                                  print(f"--- Debug: Fallback search failed. No suitable file found with extension {target_ext} (ID: {video_id}).")

                raise FileNotFoundError(f"Download/Postprocessing failed. Expected file not found: {expected_media_path} (or similar) in {download_dir}")

    except Exception as e:
        if isinstance(e, AttributeError) and "'dict' object has no attribute 'replace'" in str(e):
             print("--- Debug: The AttributeError occurred again, likely indicating an internal issue in the installed yt-dlp version.")
        else:
             print(f"--- Debug: An exception occurred during YoutubeDL processing: {type(e).__name__}: {e}")
        traceback.print_exc()
        # --- Cleanup logic (unchanged, find potential partial files and remove) ---
        video_id_cleanup = 'unknown_id'
        if info and info.get('id'): video_id_cleanup = info.get('id')
        elif 'youtube.com' in url or 'youtu.be' in url:
            try: video_id_cleanup = url.split('v=')[-1].split('&')[0]
            except: pass
        print(f"--- Debug: Cleaning up potential partial files for ID {video_id_cleanup} in {download_dir}")
        for partial_file in glob.glob(os.path.join(download_dir, f"{video_id_cleanup}*")):
             print(f"--- Debug: Attempting to remove: {partial_file}")
             try:
                 if os.path.isfile(partial_file): os.remove(partial_file)
                 elif os.path.isdir(partial_file): shutil.rmtree(partial_file)
             except OSError as rm_e: print(f"--- Debug: Error removing {partial_file}: {rm_e}")
        # --- RETURN FAILURE ---
        return None, None # Indicate failure
# ============================================================
# END OF MODIFIED download_media_from_youtube FUNCTION
# ============================================================

def sanitize_filename(name: str) -> str:
    """Removes or replaces characters invalid for filesystem paths."""
    if not name:
        return "untitled"
    # Remove characters invalid in most filesystems
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    # Replace sequences of whitespace with a single underscore
    name = re.sub(r'\s+', '_', name)
    # Remove leading/trailing underscores/whitespace
    name = name.strip('_ ')
    # Limit length (optional, but good practice)
    max_len = 100 # Limit the title part length
    if len(name) > max_len:
        # Try to truncate cleanly at the last underscore before max_len
        truncated_name = name[:max_len]
        last_underscore = truncated_name.rfind('_')
        if last_underscore > max_len * 0.6: # Only cut at underscore if it's reasonably far in
            name = truncated_name[:last_underscore] + "_trunc"
        else: # Otherwise just truncate hard
            name = truncated_name + "_trunc"
    # Handle case where name becomes empty after sanitization
    if not name:
        return "sanitized_untitled"
    return name


def is_media_file(filepath: str) -> bool:
    SUPPORTED = {'.wav','.mp3','.flac','.m4a','.aac','.ogg','.wma',
                 '.mp4','.mkv','.mov','.avi','.wmv','.m4v'}
    # Ensure filepath is a string before calling lower()
    ext = os.path.splitext(filepath)[1]
    return isinstance(ext, str) and ext.lower() in SUPPORTED


def get_files_from_args(args: list) -> list:
    # This function remains the same, it just collects URLs and local paths/folders
    collected = []
    for arg in args:
        if not isinstance(arg, str):
             print(f"⚠️ Skipping non-string input argument: {arg}")
             continue

        if arg.startswith(('http://','https://')):
             collected.append(arg)
             continue

        abs_arg = os.path.abspath(arg)
        if '*' in abs_arg or '?' in abs_arg:
            try:
                glob_results = glob.glob(abs_arg)
                for path in glob_results:
                    path_abs = os.path.abspath(path)
                    if os.path.isdir(path_abs):
                        try:
                            for f in os.listdir(path_abs):
                                f_path = os.path.join(path_abs, f)
                                if os.path.isfile(f_path) and is_media_file(f_path):
                                    collected.append(f_path)
                        except OSError as e:
                            print(f"⚠️ Error listing directory {path_abs}: {e}. Skipping.")
                    elif os.path.isfile(path_abs) and is_media_file(path_abs):
                        collected.append(path_abs)
            except Exception as e:
                 print(f"⚠️ Error processing glob pattern {abs_arg}: {e}. Skipping.")
        else: # Not a glob pattern
            if os.path.isdir(abs_arg):
                 try:
                    for f in os.listdir(abs_arg):
                         f_path = os.path.join(abs_arg, f)
                         if os.path.isfile(f_path) and is_media_file(f_path):
                             collected.append(f_path)
                 except OSError as e:
                     print(f"⚠️ Error listing directory {abs_arg}: {e}. Skipping.")
            elif os.path.isfile(abs_arg) and is_media_file(abs_arg):
                 collected.append(abs_arg)
            elif not os.path.exists(abs_arg):
                  print(f"⚠️ Input path not found and not a URL/glob: {arg} (resolved to {abs_arg}). Skipping.")
    return list(dict.fromkeys(collected))


def prompt_user_for_files_or_folder() -> list:
    # This function remains the same, returning URLs or local paths/folders
    root = tk.Tk(); root.withdraw()
    files_or_folders = []
    while not files_or_folders:
        choice = input("Choose input: [F]older, [A]udio/Video Files, [Q]uit? ").lower().strip()
        if choice == 'q':
            print("Exiting.")
            sys.exit(0)
        elif choice == 'f':
            folder = filedialog.askdirectory(title="Select Folder Containing Media Files")
            if folder:
                files_or_folders.append(os.path.abspath(folder))
                print(f"Selected folder: {files_or_folders[0]}")
            else:
                print("No folder selected.")
        elif choice == 'a':
            files = filedialog.askopenfilenames(title="Select Media File(s)")
            if files:
                files_or_folders.extend([os.path.abspath(f) for f in files])
                print(f"Selected {len(files_or_folders)} file(s).")
            else:
                print("No files selected.")
        else:
            print("Invalid choice. Please enter F, A, or Q.")
    return get_files_from_args(files_or_folders)

# =========================================================
# START OF UPDATED run_whisper_xxl_transcription FUNCTION (Title Prefixed Filename)
# =========================================================
def run_whisper_xxl_transcription(
    file_path: str,
    file_title: str, # Title for filename generation
    enable_diarization: bool,
    language: Optional[str],
    model: str,
    task: str,
    output_dir: Optional[str],
    sentence: bool,
    max_comma: int,
    max_gap: float,
    max_line_count: int,
    ff_rnndn_xiph: bool,
    ff_speechnorm: bool,
    produce_srt: bool
) -> str:
    """
    Runs faster-whisper-xxl, showing live output, and returns the path
    to the generated SRT file (with title prefixed in filename).
    """
    effective_output_dir = os.path.abspath(output_dir if output_dir else os.getcwd())
    try:
        os.makedirs(effective_output_dir, exist_ok=True)
    except OSError as e:
         print(f"❌ Critical Error: Cannot create output directory: {effective_output_dir}", file=sys.stderr)
         print(f"   Error details: {e}", file=sys.stderr)
         print( "   Please check permissions or specify a different directory with -o.", file=sys.stderr)
         return ""

    # Base filename *of the input file* (used by faster-whisper-xxl for its default output)
    input_base = os.path.splitext(os.path.basename(file_path))[0]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # --- Sanitize the title ---
    sanitized_title = sanitize_filename(file_title)

    # --- Create the NEW final base name with TITLE PREFIX ---
    # Format: {sanitized_title}_{input_base}_{timestamp}
    output_base_name = f"{sanitized_title}_{input_base}_{timestamp}"

    # Target timestamped SRT filename in the effective output directory
    final_srt_out_name = f"{output_base_name}.srt"
    final_srt_out_path = os.path.join(effective_output_dir, final_srt_out_name)

    # --- faster-whisper-xxl STILL generates output based on input name ---
    # We will rename this file *to* final_srt_out_path afterwards.
    default_srt_name = f"{input_base}.srt"
    default_srt_path = os.path.join(effective_output_dir, default_srt_name)
    # ---

    cmd = ["faster-whisper-xxl", file_path, "--model", model,
           "--task", task, "--output_format", "srt", "--output_dir", effective_output_dir]
    if language: cmd += ["--language", language]
    if sentence: cmd.append("--sentence")
    cmd += ["--max_comma", str(max_comma), "--max_gap", str(max_gap), "--max_line_count", str(max_line_count)]
    if ff_rnndn_xiph: cmd.append("--ff_rnndn_xiph")
    if ff_speechnorm: cmd.append("--ff_speechnorm")
    if enable_diarization:
        if not HF_TOKEN:
            print("⚠️ Warning: Diarization enabled, but HF_TOKEN environment variable is not set.")
            print("⚠️ This might be required to download the pyannote/speaker-diarization model.")
        cmd += ["--diarize", ENABLE_DIARIZATION_METHOD]

    print(f"🔥 Transcribing: {os.path.basename(file_path)} (Title: {file_title})")
    print(f"   Model: {model}, Task: {task}")
    print(f"   Command: {' '.join(cmd)}")

    process = None
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace'
        )

        print("--- faster-whisper-xxl live output ---")
        while True:
            line = process.stdout.readline()
            if not line: break
            print(line, end='')
        print("--- end of live output ---")

        return_code = process.wait()

        if return_code != 0:
            print(f"\n❌ Transcription failed with exit code {return_code} for {os.path.basename(file_path)}");
            # Clean up the expected intermediate file if it exists on failure
            if os.path.exists(default_srt_path):
                try:
                    print(f"   Cleaning up intermediate file: {default_srt_path}")
                    os.remove(default_srt_path)
                except OSError as rm_e:
                    print(f"   ⚠️ Failed to clean up intermediate file {default_srt_path}: {rm_e}")
            return ""

        # --- Renaming Logic (Target name uses title prefix) ---
        print(f"\n   Checking for expected intermediate output: {default_srt_path}")
        if os.path.exists(default_srt_path):
            print(f"   Found: {default_srt_path}")
            try:
                print(f"   Renaming to final (title prefixed) path: {final_srt_out_path}") # Updated message
                os.rename(default_srt_path, final_srt_out_path)
                print(f"✅ Output saved to: {final_srt_out_path}")
                return final_srt_out_path # Return the path of the *final* renamed SRT file
            except OSError as e:
                print(f"❌ Error renaming output file {default_srt_path} to {final_srt_out_path}: {e}")
                if os.path.exists(default_srt_path):
                    print(f"⚠️ Using non-titled/timestamped output: {default_srt_path}")
                    return default_srt_path
                return ""
        else:
            print(f"❌ Expected intermediate SRT file not found after transcription: {default_srt_path}");
            # Fallback: Check if the *target* filename already exists (e.g., if rename somehow happened but wasn't detected)
            if os.path.exists(final_srt_out_path):
                print(f"⚠️ Found final target file already exists, assuming success: {final_srt_out_path}")
                return final_srt_out_path

            # Fallback search for other SRTs based on input base (less likely now)
            potential_srts = glob.glob(os.path.join(effective_output_dir, f"{input_base}*.srt"))
            if potential_srts:
                 print(f"⚠️ Found potential SRT files: {potential_srts}. Using the first one: {potential_srts[0]}")
                 try:
                     # Try renaming the found one to the desired final name
                     os.rename(potential_srts[0], final_srt_out_path)
                     print(f"✅ Output saved to: {final_srt_out_path}")
                     return final_srt_out_path
                 except OSError as e:
                    print(f"❌ Error renaming found SRT file {potential_srts[0]} to {final_srt_out_path}: {e}")
                    print(f"⚠️ Using originally found name: {potential_srts[0]}")
                    return potential_srts[0] # Return the path of the file we found but couldn't rename
            return "" # Indicate failure

    except FileNotFoundError:
        print("❌ Critical Error: 'faster-whisper-xxl' command not found.", file=sys.stderr)
        print("   Please ensure it's installed and in your system's PATH.", file=sys.stderr)
        print("   Installation: pip install faster-whisper-xxl", file=sys.stderr)
        return ""
    except Exception as e:
        print(f"❌ An unexpected error occurred during transcription process execution: {e}")
        traceback.print_exc()
        if process and process.poll() is None:
            print("   Terminating transcription process...")
            process.terminate()
            try: process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print("   Process did not terminate gracefully, killing...")
                process.kill()
        # Clean up the expected intermediate file if it exists on failure
        if os.path.exists(default_srt_path):
            try:
                print(f"   Cleaning up intermediate file: {default_srt_path}")
                os.remove(default_srt_path)
            except OSError as rm_e:
                print(f"   ⚠️ Failed to clean up intermediate file {default_srt_path}: {rm_e}")
        return ""
# =========================================================
# END OF UPDATED run_whisper_xxl_transcription FUNCTION
# =========================================================


def convert_srt_to_plaintext(srt_path: str) -> str:
    # This function remains the same. It derives the TXT path from the final SRT path.
    lines, pat = [], re.compile(r'\d{2}:\d{2}:\d{2}[,\.]\d{3}\s*-->')
    try:
        with open(srt_path, 'r', encoding="utf-8", errors="replace") as f:
            for ln in f:
                t = ln.strip()
                if t.isdigit() or pat.match(t) or not t: continue
                t = re.sub(r'^\[SPEAKER_\d+\]\s*', '', t) # Remove speaker tags
                lines.append(t)
        return "\n".join(lines) if lines else ""
    except FileNotFoundError:
        print(f"❌ Error: SRT file not found for text conversion: {srt_path}")
        return ""
    except Exception as e:
        print(f"❌ Error converting SRT to text ({srt_path}): {e}")
        return ""


def print_help_message():
    lang = DEFAULT_LANGUAGE or "Auto-detect"
    sentence_default = "Enabled" if DEFAULT_SENTENCE else "Disabled"
    rnndn_default = "Enabled" if DEFAULT_FF_RNNDN_XIPH else "Disabled"
    speechnorm_default = "Enabled" if DEFAULT_FF_SPEECHNORM else "Disabled"

    script_name = os.path.basename(sys.argv[0])
    if not script_name.lower().endswith(".py"):
        script_name = "yttranscribe"

    print(f"""
Usage: {script_name} [options] [URLs | local_files | folders ...]

Downloads and transcribes media using yt-dlp and faster-whisper-xxl.
Output filenames use the format: Title_InputBaseName_Timestamp.ext

Arguments:
  URLs / local_files / folders
                          One or more YouTube URLs, local media file paths,
                          or folders containing media files. Glob patterns
                          (e.g., *.mp4, /path/to/vids/*) are supported for
                          local files/folders. If no inputs are provided,
                          you will be prompted to select files or a folder.

Options:
  -h, --help              Show this help message and exit.

Download Options (for URLs):
  -v, --video             Download video (bestvideo+bestaudio MP4) instead of
                          audio-only (WAV). Default is audio-only.
  -s, --save              Keep downloaded media files in a temporary directory
                          within the current working directory after processing.
                          Default is to delete them.

Transcription Options:
  -m, --model MODEL       Whisper model size (e.g., tiny, base, small, medium,
                          large, large-v2, large-v3).
                          Default: {DEFAULT_MODEL}
  -l, --lang LANG         Language code (e.g., en, es, fr, ja) for transcription.
                          Default: {lang} (auto-detect)
  --task TASK             Task to perform: 'transcribe' or 'translate'.
                          Default: {DEFAULT_TASK}
  -d, --diarization       Enable speaker diarization using Pyannote v3.1.
                          Requires `pyannote.audio` and potentially HF_TOKEN.
                          Default: {'Enabled' if DEFAULT_ENABLE_DIARIZATION else 'Disabled'}
  -o, --output_dir DIR    Directory to save output SRT/text files.
                          Default: Current working directory.

Output Formatting:
  --srt                   Produce SRT subtitle file output (default).
  -t, --text              Produce clean plaintext file output (removes timestamps
                          and speaker tags). Can be used with --srt.
  --sentence / --no-sentence
                          Enable/disable sentence splitting post-processing.
                          Default: {sentence_default}
  -c, --max_comma N       Maximum number of commas allowed before forcing a split.
                          Used with --sentence. Default: {DEFAULT_MAX_COMMA}
  -g, --max_gap G         Maximum gap in seconds between words to consider for
                          sentence splitting. Default: {DEFAULT_MAX_GAP}
  -n, --max_line_count N  Maximum number of lines per subtitle block in SRT.
                          Default: {DEFAULT_MAX_LINE_COUNT}

Audio Enhancement Options (Applied before transcription):
  -x, --ff_rnndn_xiph / -X, --no-ff_rnndn_xiph
                          Enable/disable FFmpeg RNNoise denoising (Xiph model).
                          Requires ffmpeg. Default: {rnndn_default}
  -p, --ff_speechnorm / -P, --no-ff_speechnorm
                          Enable/disable FFmpeg Speechnorm audio normalization.
                          Requires ffmpeg. Default: {speechnorm_default}

Examples:
  # Download audio from YouTube URL, transcribe (SRT), cleanup download
  {script_name} https://www.youtube.com/watch?v=dQw4w9WgXcQ

  # Download video, keep download, transcribe to English text, output to 'transcripts' folder
  {script_name} -v -s -l en -t -o transcripts https://youtu.be/some_video_id

  # Transcribe a local file with diarization and sentence splitting disabled
  {script_name} -d --no-sentence local_audio.mp3

  # Transcribe all MP4 files in the current directory
  {script_name} *.mp4

  # Transcribe all media files in a specific folder
  {script_name} /path/to/my/media/
"""
)


def main():
    script_name = os.path.basename(sys.argv[0])
    if not script_name.lower().endswith(".py"): script_name = "yttranscribe"
    parser = argparse.ArgumentParser(
        description="Download media via yt-dlp and transcribe with Faster Whisper XXL.",
        usage=f"{script_name} [options] [URLs | local_files | folders ...]",
        add_help=False
    )
    # --- Argument Definitions (Grouped) ---
    parser.add_argument('-h', '--help', action='store_true', help='Show this help message and exit')
    # Download
    download_group = parser.add_argument_group('Download Options (for URLs)')
    download_group.add_argument('-v','--video', dest='download_video', action='store_true', help='Download video instead of audio-only')
    download_group.add_argument('-s','--save', dest='keep_downloads', action='store_true', help='Keep downloaded files in a temp dir in CWD')
    # Transcription
    transcribe_group = parser.add_argument_group('Transcription Options')
    transcribe_group.add_argument('-m','--model', type=str, default=DEFAULT_MODEL, help=f'Whisper model size (Default: {DEFAULT_MODEL})')
    transcribe_group.add_argument('-l','--lang', type=str, default=DEFAULT_LANGUAGE, help='Language code (Default: Auto-detect)')
    transcribe_group.add_argument('--task', type=str, default=DEFAULT_TASK, choices=['transcribe', 'translate'], help=f'Task: transcribe or translate (Default: {DEFAULT_TASK})')
    transcribe_group.add_argument('-d','--diarization', dest='enable_diarization', action='store_true', default=DEFAULT_ENABLE_DIARIZATION, help='Enable speaker diarization (Pyannote v3.1)')
    transcribe_group.add_argument('-o','--output_dir', type=str, default=None, help='Output directory (Default: current working directory)')
    # Output Formatting
    output_group = parser.add_argument_group('Output Formatting')
    output_group.add_argument('--srt', dest='produce_srt', action='store_true', help='Produce SRT output (default if no format specified)')
    output_group.add_argument('-t','--text', dest='produce_text', action='store_true', help='Produce plaintext output')
    sentence_group = output_group.add_mutually_exclusive_group()
    sentence_group.add_argument('--sentence', dest='sentence', action='store_true', help=f'Enable sentence splitting (Default: {"Yes" if DEFAULT_SENTENCE else "No"})')
    sentence_group.add_argument('--no-sentence', dest='sentence', action='store_false', help='Disable sentence splitting')
    parser.set_defaults(sentence=DEFAULT_SENTENCE)
    output_group.add_argument('-c','--max_comma', type=int, default=DEFAULT_MAX_COMMA, help=f'Max commas before split (Default: {DEFAULT_MAX_COMMA})')
    output_group.add_argument('-g','--max_gap', type=float, default=DEFAULT_MAX_GAP, help=f'Max gap in seconds for split (Default: {DEFAULT_MAX_GAP})')
    output_group.add_argument('-n','--max_line_count', type=int, default=DEFAULT_MAX_LINE_COUNT, help=f'Max lines per subtitle (Default: {DEFAULT_MAX_LINE_COUNT})')
    # Audio Enhancement
    audio_enhance_group = parser.add_argument_group('Audio Enhancement Options (Requires ffmpeg)')
    rnndn_group = audio_enhance_group.add_mutually_exclusive_group()
    rnndn_group.add_argument('-x','--ff_rnndn_xiph', dest='ff_rnndn_xiph', action='store_true', help=f'Enable FFmpeg RNNoise denoising (Default: {"Yes" if DEFAULT_FF_RNNDN_XIPH else "No"})')
    rnndn_group.add_argument('-X','--no-ff_rnndn_xiph', dest='ff_rnndn_xiph', action='store_false', help='Disable FFmpeg RNNoise denoising')
    parser.set_defaults(ff_rnndn_xiph=DEFAULT_FF_RNNDN_XIPH)
    speechnorm_group = audio_enhance_group.add_mutually_exclusive_group()
    speechnorm_group.add_argument('-p','--ff_speechnorm', dest='ff_speechnorm', action='store_true', help=f'Enable FFmpeg Speechnorm normalization (Default: {"Yes" if DEFAULT_FF_SPEECHNORM else "No"})')
    speechnorm_group.add_argument('-P','--no-ff_speechnorm', dest='ff_speechnorm', action='store_false', help='Disable FFmpeg Speechnorm normalization')
    parser.set_defaults(ff_speechnorm=DEFAULT_FF_SPEECHNORM)
    # Positional Inputs
    parser.add_argument('inputs', nargs='*', help='URLs, local files, or folders')

    args = parser.parse_args()
    if args.help: print_help_message(); sys.exit(0)

    # --- Determine inputs ---
    input_items_raw = args.inputs
    if not input_items_raw:
        print("No input URLs, files, or folders provided via arguments.")
        input_items_processed = prompt_user_for_files_or_folder()
        if not input_items_processed: sys.exit(0) # Exit if user quit prompt
    else:
        input_items_processed = get_files_from_args(input_items_raw)

    # --- Separate URLs and Local Files ---
    urls_to_process = [item for item in input_items_processed if isinstance(item, str) and item.startswith(('http://','https://'))]
    local_files_initial = [item for item in input_items_processed if not (isinstance(item, str) and item.startswith(('http://','https://')))]

    temp_dir = None
    successfully_downloaded_items = [] # List of (path, title) tuples

    # --- Set up temporary download directory in CWD ---
    if urls_to_process:
        try:
            temp_dir = tempfile.mkdtemp(prefix='yt_dlp_download_', dir=os.getcwd())
            print(f"ℹ️ Using temporary download directory: {temp_dir}")
        except Exception as e:
            print(f"❌ Failed to create temporary directory in CWD ({os.getcwd()}): {e}", file=sys.stderr)
            if not local_files_initial: sys.exit(1)
            else: print("⚠️ Proceeding with local files only.", file=sys.stderr); urls_to_process = []

    # --- Download phase ---
    if urls_to_process and temp_dir:
        for url in urls_to_process:
            print("-" * 60)
            print(f"⬇️ Processing URL: {url}")
            try:
                downloaded_path, video_title = download_media_from_youtube(url, temp_dir, args.download_video)
                if downloaded_path and video_title and os.path.exists(downloaded_path):
                    print(f"✅ Download successful: {downloaded_path} (Title: {video_title})")
                    successfully_downloaded_items.append((downloaded_path, video_title))
                else:
                    # Error should have been raised or (None, None) returned by download_media_from_youtube
                    print(f"⚠️ Download function returned invalid path or title for {url}. Skipping.")
            except Exception as download_exc:
                # Error details already printed within download_media_from_youtube's handler
                print(f"❌ Skipping URL due to download error: {url}")

    # --- Prepare final list of items (path, title) for transcription ---
    items_to_transcribe = []
    seen_paths = set()

    # Add local files (use filename base as title)
    for f_path in local_files_initial:
        try:
            abs_f_path = os.path.abspath(f_path)
            if abs_f_path not in seen_paths:
                if os.path.exists(abs_f_path):
                    if is_media_file(abs_f_path):
                        # Use base filename (without ext) as the "title" for local files
                        local_title = os.path.splitext(os.path.basename(abs_f_path))[0]
                        items_to_transcribe.append((abs_f_path, local_title))
                        seen_paths.add(abs_f_path)
                    else:
                        print(f"⚠️ Skipping non-media file: {abs_f_path}")
                else:
                    print(f"⚠️ Skipping non-existent file path: {abs_f_path}")
                # Add to seen even if skipped to avoid re-processing attempts if listed multiple ways
                seen_paths.add(abs_f_path)
        except Exception as path_e:
            print(f"⚠️ Error processing local file path {f_path}: {path_e}. Skipping.")

    # Add successfully downloaded files (already have path and title)
    for dl_path, dl_title in successfully_downloaded_items:
        abs_dl_path = os.path.abspath(dl_path) # Ensure absolute
        if abs_dl_path not in seen_paths:
            if os.path.exists(abs_dl_path): # Double check existence
                 if is_media_file(abs_dl_path): # Double check media type
                     items_to_transcribe.append((abs_dl_path, dl_title))
                     seen_paths.add(abs_dl_path)
                 else:
                      print(f"⚠️ Skipping downloaded non-media file: {abs_dl_path}")
            else:
                 print(f"⚠️ Skipping non-existent downloaded file path: {abs_dl_path}")
            # Add to seen even if skipped
            seen_paths.add(abs_dl_path)


    if not items_to_transcribe:
        print("-" * 60)
        print("❌ No valid media files found or successfully downloaded to process. Exiting.")
        if temp_dir and not args.keep_downloads:
            try:
                if os.path.exists(temp_dir) and not os.listdir(temp_dir):
                    print(f"🧹 Cleaning up empty temporary directory: {temp_dir}")
                    shutil.rmtree(temp_dir, ignore_errors=True)
            except OSError: pass
        sys.exit(1)

    # --- Determine output formats ---
    produce_srt = args.produce_srt or (not args.produce_srt and not args.produce_text)
    produce_text = args.produce_text

    print("-" * 60)
    print(f"▶️ Starting transcription for {len(items_to_transcribe)} item(s)...")
    print(f"   Output Dir: {os.path.abspath(args.output_dir or os.getcwd())}")
    print(f"   Format(s): {'SRT' if produce_srt else ''}{' + ' if produce_srt and produce_text else ''}{'Text' if produce_text else ''}")
    print(f"   Model: {args.model}, Lang: {args.lang or 'auto'}, Task: {args.task}")
    print(f"   Diarization: {'Enabled' if args.enable_diarization else 'Disabled'}")
    print(f"   Sentence Split: {'Enabled' if args.sentence else 'Disabled'} (Comma:{args.max_comma}, Gap:{args.max_gap}s, Lines:{args.max_line_count})")
    print(f"   RNNoise: {'Enabled' if args.ff_rnndn_xiph else 'Disabled'}, Speechnorm: {'Enabled' if args.ff_speechnorm else 'Disabled'}")

    # --- Transcription and Post-processing phase ---
    success_count = 0
    fail_count = 0
    processed_files_outputs = {} # Keyed by input f_path: [list_of_output_paths]

    for f_path, f_title in items_to_transcribe:
        print("-" * 60)
        print(f"Processing file: {f_path}") # f_path is absolute and exists

        output_paths_for_file = []

        # Run transcription, get the path to the generated SRT file (now title-prefixed)
        generated_srt_path = run_whisper_xxl_transcription(
            f_path, f_title, # Pass title
            args.enable_diarization, args.lang, args.model, args.task,
            args.output_dir, args.sentence, args.max_comma, args.max_gap,
            args.max_line_count, args.ff_rnndn_xiph, args.ff_speechnorm,
            produce_srt
        )

        if not generated_srt_path:
            # Error message already printed by run_whisper_xxl_transcription
            fail_count += 1
            processed_files_outputs[f_path] = [] # Record failure against the input path
            continue # Skip to next file

        # --- Text Conversion (if requested) ---
        text_conversion_successful = False
        if produce_text:
            # Derive text filename from the final SRT filename
            txt_path = os.path.splitext(generated_srt_path)[0] + '.txt'
            print(f"   Converting SRT to Text: {os.path.basename(txt_path)}")
            plain_text = convert_srt_to_plaintext(generated_srt_path)
            # Check if conversion returned a non-empty string
            if plain_text:
                try:
                    with open(txt_path, 'w', encoding='utf-8') as out_f:
                        out_f.write(plain_text)
                    print(f"   ✅ Text output saved: {txt_path}")
                    output_paths_for_file.append(txt_path)
                    text_conversion_successful = True
                except Exception as e:
                    print(f"   ❌ Failed to write text file {txt_path}: {e}")
            elif plain_text == "": # Conversion returned empty string (e.g., empty SRT)
                 print(f"   ℹ️ Text conversion resulted in an empty file (source SRT might be empty or only contain formatting). Skipping empty text file write for {os.path.basename(txt_path)}")
            else: # Conversion returned None or "" indicating error
                 print(f"   ⚠️ Text conversion failed for {os.path.basename(generated_srt_path)}")


        # --- SRT File Handling ---
        srt_kept = False
        if produce_srt:
            # Keep the SRT file if SRT output was requested
            if os.path.exists(generated_srt_path): # Double check it exists
                 output_paths_for_file.append(generated_srt_path)
                 srt_kept = True
            else:
                 # This case should be rare now due to checks in run_whisper_xxl_transcription
                 print(f"   ⚠️ Expected SRT file {generated_srt_path} was not found after transcription function returned success.")
        elif produce_text and os.path.exists(generated_srt_path):
            # If ONLY text was requested, remove the intermediate SRT file
             # This check needs to happen *before* assuming the SRT is the only output
             if text_conversion_successful: # Only remove SRT if text conversion WORKED
                 try:
                     os.remove(generated_srt_path)
                     print(f"   ℹ️ Removed intermediate SRT file: {os.path.basename(generated_srt_path)}")
                 except OSError as e:
                     print(f"   ⚠️ Could not remove intermediate SRT file {generated_srt_path}: {e}")
                     # If removal fails, it might still be present
                     if os.path.exists(generated_srt_path):
                         output_paths_for_file.append(generated_srt_path) # Record it if deletion failed
                         srt_kept = True
             else: # Text conversion failed, but SRT exists, keep the SRT
                 print(f"   ℹ️ Keeping SRT file because text conversion failed: {generated_srt_path}")
                 output_paths_for_file.append(generated_srt_path)
                 srt_kept = True
        elif os.path.exists(generated_srt_path):
             # If neither SRT nor Text was explicitly requested (should default to SRT)
             # OR if text failed and SRT wasn't requested. Keep the SRT as it's the only output.
             print(f"   ℹ️ Keeping SRT file (fallback): {generated_srt_path}")
             output_paths_for_file.append(generated_srt_path)
             srt_kept = True


        # --- Update Counts and Records ---
        # Consider successful if at least one output file was generated and recorded
        if output_paths_for_file:
             success_count += 1
             processed_files_outputs[f_path] = output_paths_for_file # Store outputs against input path
        else:
             # This might occur if transcription succeeded but renaming/conversion/deletion failed
             print(f"⚠️ Transcription may have succeeded for {os.path.basename(f_path)}, but no final output files were confirmed.")
             fail_count += 1 # Count as failure if no usable output confirmed
             processed_files_outputs[f_path] = []


    # --- Cleanup phase ---
    print("-" * 60)
    if temp_dir and os.path.exists(temp_dir): # Only attempt cleanup if a temp dir was created and exists
        if not args.keep_downloads:
            print(f"🧹 Cleaning up temporary download directory: {temp_dir}")
            try:
                shutil.rmtree(temp_dir)
                print(f"   ✅ Temporary directory removed.")
            except Exception as e:
                print(f"   ⚠️ Error removing temporary directory {temp_dir}: {e}")
                print(f"   You may need to remove it manually.")
        else:
            # Only print retention message if items were actually downloaded successfully
            if successfully_downloaded_items:
                 print(f"✅ Downloads retained in directory (--save specified): {temp_dir}")
            else:
                 # If temp_dir exists but no files were successfully downloaded into it
                 try:
                     if os.path.exists(temp_dir) and not os.listdir(temp_dir): # Check if directory is empty
                          print(f"ℹ️ Temporary directory is empty. Removing: {temp_dir}")
                          shutil.rmtree(temp_dir, ignore_errors=True)
                     elif os.path.exists(temp_dir):
                         # --save used, but downloads failed or only local files were processed.
                         # If the dir has *anything* (like failed parts), keep it if --save was used.
                         print(f"ℹ️ Files retained in directory (--save specified): {temp_dir}")
                 except OSError:
                      # Error listing directory, assume we should keep it if --save was used
                      print(f"ℹ️ Files retained in directory (--save specified, error checking contents): {temp_dir}")


    # --- Final Summary ---
    print("\n🏁 Processing finished.")
    if success_count > 0: print(f"✅ Successfully processed {success_count} item(s).")
    if fail_count > 0: print(f"❌ Failed to process {fail_count} item(s). Check logs above for details.")

    # Exit codes: 0 = all success, 1 = all failed or nothing to process, 2 = partial success
    if success_count > 0 and fail_count == 0: sys.exit(0)
    elif success_count > 0 and fail_count > 0: sys.exit(2)
    else: sys.exit(1)


if __name__ == '__main__':
    # --- Initial Dependency Checks ---
    whisper_ok = False
    try:
        subprocess.run(["faster-whisper-xxl", "--help"], capture_output=True, check=True, text=True, encoding='utf-8', errors='replace', timeout=10)
        whisper_ok = True
    except FileNotFoundError:
        print("❌ Critical Error: 'faster-whisper-xxl' command not found.", file=sys.stderr)
        print("   Please ensure it's installed and in your system's PATH.", file=sys.stderr)
        print("   Installation: pip install faster-whisper-xxl", file=sys.stderr)
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print("⚠️ Warning: 'faster-whisper-xxl --help' timed out. Proceeding cautiously.", file=sys.stderr)
        whisper_ok = True # Assume it exists if it didn't raise FileNotFoundError
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Warning: 'faster-whisper-xxl --help' failed (code {e.returncode}). Check installation.", file=sys.stderr)
        whisper_ok = True # Proceed cautiously
    except Exception as check_e:
         print(f"⚠️ Unexpected error checking faster-whisper-xxl: {check_e}", file=sys.stderr)
         whisper_ok = True # Proceed cautiously

    ffmpeg_ok = False
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True, text=True, encoding='utf-8', errors='replace', timeout=5)
        if "ffmpeg version" in result.stdout.lower():
            ffmpeg_ok = True
        else:
            print("⚠️ Warning: 'ffmpeg -version' ran but output unexpected. FFMPEG functionality may fail.", file=sys.stderr)
            ffmpeg_ok = True # Assume available if command ran
    except FileNotFoundError:
         print("❌ Critical Error: 'ffmpeg' command not found.", file=sys.stderr)
         print("   ffmpeg is required for audio extraction/conversion.", file=sys.stderr)
         print("   Please install ffmpeg (from ffmpeg.org) and ensure it's in your system's PATH.", file=sys.stderr)
         sys.exit(1) # Exit because default operation (audio download) will fail
    except subprocess.TimeoutExpired:
         print("⚠️ Warning: 'ffmpeg -version' command timed out.", file=sys.stderr)
    except subprocess.CalledProcessError as e:
         print(f"⚠️ Warning: 'ffmpeg -version' failed (code {e.returncode}).", file=sys.stderr)
    except Exception as check_e:
         print(f"⚠️ Unexpected error checking ffmpeg: {check_e}", file=sys.stderr)

    if not ffmpeg_ok and whisper_ok: # Only warn if ffmpeg failed but whisper seems ok
         print("⚠️ Proceeding without confirmed ffmpeg functionality. Audio processing may fail.", file=sys.stderr)

    # --- Run Main Function with Error Handling ---
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Operation cancelled by user (Ctrl+C). Cleaning up...")
        # Attempt cleanup of temp dirs matching the prefix in CWD
        try:
            potential_temp_dirs = glob.glob(os.path.join(os.getcwd(), 'yt_dlp_download_*'))
            for p_dir in potential_temp_dirs:
                if os.path.isdir(p_dir):
                     print(f"   Removing potential temporary directory: {p_dir}")
                     shutil.rmtree(p_dir, ignore_errors=True)
        except Exception as cleanup_e:
             print(f"   ⚠️ Error during cleanup: {cleanup_e}")
        sys.exit(130) # Standard exit code for SIGINT
    except Exception as e:
        print("\n❌ An unexpected critical error occurred in the main execution flow:", file=sys.stderr)
        traceback.print_exc()
        sys.exit(3) # General script error code