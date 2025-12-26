#!/usr/bin/env python3
"""
transcribe_with_yt_dlp.py - Download media via yt-dlp and transcribe with Faster Whisper XXL
--------------------------------------------------------------------------------------------------
- Downloads media from URLs using yt-dlp, allowing custom yt-dlp options via -Y/--ytdl-opt.
- Default download format is 'best,best' (usually merges to MKV).
- Downloads into a temporary directory within the current working directory.
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
import traceback
import json
# ** ADDED missing imports from typing **
from typing import Tuple, Optional, List, Dict, Any

# Attempt to import yt-dlp
try:
    from yt_dlp import YoutubeDL
except ImportError:
    print("❌ yt-dlp not found. Install via `pip install yt-dlp`.")
    sys.exit(1)

# ------------------- DEFAULT CONFIGURATION ------------------- #
# Script Defaults (can be overridden by args)
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

# yt-dlp Script Defaults (can be overridden by --ytdl-opt)
YDL_SCRIPT_DEFAULTS = {
    'noprogress': False,
    'verbose': False,
    'quiet': True,
    'logtostderr': False,
    'ignoreerrors': False,
    'progress': True,
}

# ------------------ FUNCTION DEFINITIONS ------------------ #

def parse_value(value_str: str) -> Any:
    """Attempts to convert string value to bool, int, float, or keep as string."""
    val_lower = value_str.lower()
    if val_lower == 'true': return True
    if val_lower == 'false': return False
    try: return int(value_str)
    except ValueError: pass
    try: return float(value_str)
    except ValueError: pass
    # Basic JSON check for lists/dicts needs careful handling or explicit flag
    # If needed, add a specific flag like --ytdl-opt-json key='[...]'.
    # For now, keep it simple.
    return value_str

# ==============================================================
# download_media_from_youtube FUNCTION (Defaults to 'best,best')
# ==============================================================
def download_media_from_youtube(
    url: str,
    download_dir: str,
    custom_ytdl_opts: Optional[Dict[str, Any]] = None
) -> Tuple[Optional[str], Optional[str]]:
    """
    Download media from URL using yt-dlp, applying custom options.
    Default format is now 'best,best'.
    Returns tuple: (local_path_to_downloaded_file, video_title).
    Returns (None, None) on failure.
    Custom format options override the script default.
    """
    print(f"--- Debug: Starting download for {url} into {download_dir}")
    os.makedirs(download_dir, exist_ok=True)

    ydl_opts = YDL_SCRIPT_DEFAULTS.copy()
    ydl_opts['outtmpl'] = os.path.join(download_dir, '%(id)s.%(ext)s')
    if ydl_opts.get('progress'):
        ydl_opts['progress_hooks'] = [
            lambda d: print(f"   yt-dlp status: {d.get('status', 'N/A')} - {d.get('_percent_str', '')} {d.get('_speed_str', '')} ETA {d.get('_eta_str', '')}", end='\r') if d.get('status') == 'downloading' else None,
            lambda d: print(f"\n   yt-dlp status: {d.get('status', 'finished')}{' (Postprocessing...)' if d.get('status') == 'finished' and d.get('postprocessor') else ''}      ") if d.get('status') == 'finished' else None
        ]

    effective_custom_opts = custom_ytdl_opts or {}
    ignored_keys = ['outtmpl', 'progress_hooks']
    for key in ignored_keys:
        if key in effective_custom_opts:
            print(f"⚠️ Warning: Custom yt-dlp option '{key}' ignored; script controls this.")
            effective_custom_opts.pop(key, None) # Use pop with default None
    ydl_opts.update(effective_custom_opts)

    target_ext = ".unknown"
    is_video_output_implied = False

    if 'format' in ydl_opts:
        final_format = ydl_opts['format']
        print(f"ℹ️ Using custom yt-dlp format: '{final_format}'")
        is_video_output_implied = '+' in str(final_format) or any(vf in str(final_format).lower() for vf in ['bestvideo', 'bv', 'mp4', 'mkv', 'webm'])

        # Determine target extension based on custom options
        if 'postprocessors' in ydl_opts:
            for pp in ydl_opts.get('postprocessors', []): # Iterate safely
                if isinstance(pp, dict) and pp.get('key') == 'FFmpegExtractAudio' and pp.get('preferredcodec'):
                    target_ext = f".{pp['preferredcodec']}"
                    is_video_output_implied = False # Explicit audio conversion
                    break # Assume first audio conversion dictates extension
        elif is_video_output_implied:
             target_ext = f".{ydl_opts.get('merge_output_format', 'mkv')}" # Guess mkv if merging unspecified
        elif any(af in str(final_format).lower() for af in ['bestaudio', 'ba', 'm4a', 'mp3', 'opus', 'ogg', 'wav']):
             target_ext = ".audio" # Placeholder, rely on fallback search
             is_video_output_implied = False
        else:
            target_ext = ".media" # Generic placeholder, rely on fallback

    else:
        # No custom format: Use NEW script default 'best,best'
        print("ℹ️ Using script default format: 'best,best' (usually merges to MKV)")
        ydl_opts['format'] = 'best,best'
        is_video_output_implied = True
        target_ext = ".mkv" # Set default guess for the new default format

    info = None
    video_title = "unknown_title"
    video_id = 'unknown_id'
    expected_media_path = None

    try:
        print(f"--- Debug: Final yt-dlp options: {ydl_opts}")
        with YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=True)
            except Exception as ydl_download_error:
                print(f"\n❌ yt-dlp Error during download/extraction for {url}: {ydl_download_error}")
                try: info = ydl.extract_info(url, download=False)
                except Exception: info = None
                raise

            if info is None: raise ValueError("yt-dlp extract_info returned None")

            video_title = info.get('title', 'unknown_title')
            video_id = info.get('id', 'unknown_id')
            print(f"--- Debug: Extracted Title: '{video_title}', ID: '{video_id}'")

            if target_ext not in [".unknown", ".audio", ".media"]:
                expected_media_path = os.path.join(download_dir, f"{video_id}{target_ext}")
                print(f"--- Debug: Initially expecting output file at: {expected_media_path}")
                if os.path.exists(expected_media_path):
                    print(f"--- Debug: Expected path found!")
                    return os.path.abspath(expected_media_path), video_title
                else:
                     print(f"--- Debug: Initial expected path '{expected_media_path}' not found. Proceeding to search...")
            else:
                 print(f"--- Debug: Target extension guess is '{target_ext}'. Proceeding directly to fallback search.")

            print(f"--- Debug: Searching download directory for file starting with '{video_id}'...")
            try: files_in_dir = os.listdir(download_dir)
            except Exception as list_e: print(f"--- Debug: Error listing directory {download_dir}: {list_e}"); files_in_dir = []

            potential_files = [f for f in files_in_dir if f.startswith(video_id)]
            if not potential_files:
                 raise FileNotFoundError(f"Download completed, but no file found starting with ID '{video_id}' in {download_dir}")

            media_files = [f for f in potential_files if is_media_file(os.path.join(download_dir, f))]

            if media_files:
                 media_files.sort(key=lambda f: os.path.getmtime(os.path.join(download_dir, f)), reverse=True)
                 found_path = os.path.join(download_dir, media_files[0])
                 print(f"--- Debug: Fallback search found media file: {found_path}")
                 return os.path.abspath(found_path), video_title
            else:
                 potential_files.sort(key=lambda f: os.path.getmtime(os.path.join(download_dir, f)), reverse=True)
                 found_path = os.path.join(download_dir, potential_files[0])
                 print(f"⚠️ WARNING: Fallback search found a file, but it doesn't have a recognized media extension: {found_path}. Attempting to proceed.")
                 return os.path.abspath(found_path), video_title

    except Exception as e:
        print(f"\n❌ Error processing URL {url}: {type(e).__name__}: {e}")
        video_id_cleanup = video_id
        if video_id_cleanup != 'unknown_id':
             print(f"--- Debug: Cleaning up potential partial files for ID {video_id_cleanup} in {download_dir}")
             try:
                 for partial_file in glob.glob(os.path.join(download_dir, f"{video_id_cleanup}*")):
                     try:
                         if os.path.isfile(partial_file): os.remove(partial_file)
                         elif os.path.isdir(partial_file): shutil.rmtree(partial_file)
                     except OSError as rm_e: print(f"--- Debug: Error removing {partial_file}: {rm_e}")
             except Exception as glob_e: print(f"--- Debug: Error during cleanup globbing: {glob_e}")
        return None, None
# ============================================================
# END OF download_media_from_youtube FUNCTION
# ============================================================

# --- Other helper functions (sanitize_filename, is_media_file, get_files_from_args, prompt_user_for_files_or_folder, run_whisper_xxl_transcription, convert_srt_to_plaintext) ---
# (These should be the same as the previous 'full updated script' response)

def sanitize_filename(name: str) -> str:
    """Removes or replaces characters invalid for filesystem paths."""
    if not name: return "untitled"
    name = re.sub(r'[\\/*?:"<>|]', '_', name)
    name = re.sub(r'\s+', '_', name)
    name = name.strip('_ .')
    max_len = 100
    if len(name) > max_len:
        truncated_name = name[:max_len]
        last_underscore = truncated_name.rfind('_')
        if last_underscore > max_len * 0.6: name = truncated_name[:last_underscore] + "_trunc"
        else: name = truncated_name.rstrip('_') + "_trunc"
    if not name: return "sanitized_untitled"
    return name

def is_media_file(filepath: str) -> bool:
    SUPPORTED = {'.wav','.mp3','.flac','.m4a','.aac','.ogg','.wma',
                 '.mp4','.mkv','.mov','.avi','.wmv','.m4v'}
    try:
        ext = os.path.splitext(filepath)[1]
        return isinstance(ext, str) and ext.lower() in SUPPORTED
    except Exception: return False

def get_files_from_args(args: List[str]) -> List[str]: # Added List type hint
    """Processes list of arguments (URLs, files, folders, globs) into a list of specific files/URLs."""
    collected = []
    processed_paths = set() # To avoid duplicates from globs/folders

    for arg in args:
        if not isinstance(arg, str):
             print(f"⚠️ Skipping non-string input argument: {arg}")
             continue
        if arg.startswith(('http://','https://')):
            if arg not in processed_paths:
                 collected.append(arg)
                 processed_paths.add(arg)
            continue
        try: abs_arg = os.path.abspath(arg)
        except Exception as abs_e: print(f"⚠️ Error resolving path '{arg}': {abs_e}. Skipping."); continue

        if '*' in abs_arg or '?' in abs_arg:
            try:
                glob_results = glob.glob(abs_arg, recursive=True)
                if not glob_results: print(f"⚠️ Glob pattern '{arg}' matched no files/dirs.")
                for path in glob_results:
                    path_abs = os.path.abspath(path)
                    if path_abs in processed_paths: continue # Skip already processed
                    if os.path.isdir(path_abs):
                        try:
                            for f in os.listdir(path_abs):
                                f_path = os.path.join(path_abs, f)
                                if os.path.isfile(f_path) and is_media_file(f_path) and f_path not in processed_paths:
                                    collected.append(f_path); processed_paths.add(f_path)
                        except OSError as e: print(f"⚠️ Error listing dir from glob '{path_abs}': {e}. Skipping.")
                    elif os.path.isfile(path_abs) and is_media_file(path_abs):
                        collected.append(path_abs); processed_paths.add(path_abs)
                    processed_paths.add(path_abs) # Add dir path itself to avoid re-listing
            except Exception as e: print(f"⚠️ Error processing glob pattern '{arg}': {e}. Skipping.")
        else:
            if abs_arg in processed_paths: continue # Skip already processed
            if os.path.isdir(abs_arg):
                 try:
                    found_in_dir = False
                    for f in os.listdir(abs_arg):
                         f_path = os.path.join(abs_arg, f)
                         if os.path.isfile(f_path) and is_media_file(f_path) and f_path not in processed_paths:
                             collected.append(f_path); processed_paths.add(f_path); found_in_dir = True
                    if not found_in_dir: print(f"ℹ️ No media files found in directory: {abs_arg}")
                 except OSError as e: print(f"⚠️ Error listing directory '{abs_arg}': {e}. Skipping.")
                 processed_paths.add(abs_arg) # Mark directory as processed
            elif os.path.isfile(abs_arg):
                 if is_media_file(abs_arg): collected.append(abs_arg)
                 else: print(f"⚠️ Skipping non-media file: {abs_arg}")
                 processed_paths.add(abs_arg) # Mark file as processed
            elif not os.path.exists(abs_arg):
                  print(f"⚠️ Input path not found: '{arg}' (resolved to '{abs_arg}'). Skipping.")
                  processed_paths.add(abs_arg) # Mark as processed to avoid re-check

    # Order is preserved by how items are added, duplicates handled by processed_paths set
    return collected


def prompt_user_for_files_or_folder() -> List[str]: # Added List type hint
    """Interactively prompts user for files or a folder via GUI dialogs."""
    root = tk.Tk(); root.withdraw(); root.update()
    files_or_folders = []
    processed_items = []
    while not processed_items:
        choice = input("Choose input: [F]older, [A]udio/Video Files, [Q]uit? ").lower().strip()
        if choice == 'q': print("Exiting."); sys.exit(0)
        elif choice == 'f':
            folder = filedialog.askdirectory(title="Select Folder Containing Media Files")
            root.update()
            if folder: files_or_folders.append(os.path.abspath(folder)); print(f"Selected folder: {files_or_folders[0]}")
            else: print("No folder selected.")
        elif choice == 'a':
            files = filedialog.askopenfilenames(title="Select Media File(s)")
            root.update()
            if files: files_or_folders.extend([os.path.abspath(f) for f in files]); print(f"Selected {len(files_or_folders)} file(s).")
            else: print("No files selected.")
        else: print("Invalid choice. Please enter F, A, or Q.")
        if files_or_folders:
            processed_items = get_files_from_args(files_or_folders)
            if not processed_items: print("⚠️ No valid media files found in the selection. Please try again."); files_or_folders = []
            else: break
    try: root.destroy()
    except tk.TclError: pass
    return processed_items

def run_whisper_xxl_transcription( file_path: str, file_title: str, enable_diarization: bool, language: Optional[str], model: str, task: str, output_dir: Optional[str], sentence: bool, max_comma: int, max_gap: float, max_line_count: int, ff_rnndn_xiph: bool, ff_speechnorm: bool ) -> str:
    """ Runs faster-whisper-xxl, generates SRT, renames it, returns final path or empty string. """
    effective_output_dir = os.path.abspath(output_dir if output_dir else os.getcwd())
    try: os.makedirs(effective_output_dir, exist_ok=True)
    except OSError as e: print(f"❌ Critical Error creating output dir: {e}", file=sys.stderr); return ""
    input_base = os.path.splitext(os.path.basename(file_path))[0]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    sanitized_title = sanitize_filename(file_title)
    output_base_name = f"{sanitized_title}_{input_base}_{timestamp}"
    final_srt_out_name = f"{output_base_name}.srt"
    final_srt_out_path = os.path.join(effective_output_dir, final_srt_out_name)
    default_srt_name = f"{input_base}.srt"
    default_srt_path = os.path.join(effective_output_dir, default_srt_name)
    cmd = ["faster-whisper-xxl", file_path, "--model", model, "--task", task, "--output_format", "srt", "--output_dir", effective_output_dir]
    if language: cmd += ["--language", language]
    if sentence: cmd.append("--sentence")
    cmd += ["--max_comma", str(max_comma), "--max_gap", str(max_gap), "--max_line_count", str(max_line_count)]
    if ff_rnndn_xiph: cmd.append("--ff_rnndn_xiph")
    if ff_speechnorm: cmd.append("--ff_speechnorm")
    if enable_diarization:
        if not HF_TOKEN: print("⚠️ Warning: Diarization enabled, but HF_TOKEN not set.")
        cmd += ["--diarize", ENABLE_DIARIZATION_METHOD]
    print(f"🔥 Transcribing: {os.path.basename(file_path)} (Title: {file_title})")
    print(f"   Model: {model}, Task: {task}, Lang: {language or 'auto'}")
    print(f"   Output Dir: {effective_output_dir}")
    process = None
    try:
        if os.path.exists(default_srt_path):
            print(f"   ℹ️ Removing existing intermediate file: {default_srt_path}")
            try: os.remove(default_srt_path)
            except OSError as rm_e: print(f"   ⚠️ Failed to remove existing intermediate file: {rm_e}")
        process = subprocess.Popen( cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace', bufsize=1, universal_newlines=True )
        print("--- faster-whisper-xxl live output ---")
        progress_pattern = re.compile(r'\[\d{2}:\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}:\d{2}\.\d{3}\]')
        last_line = ""
        for line in process.stdout:
            stripped_line = line.strip()
            if progress_pattern.match(stripped_line): print(f"   Progress: {stripped_line}", end='\r'); last_line = line
            else:
                if progress_pattern.match(last_line.strip()): print() # Newline after progress
                print(line, end=''); last_line = line
        if progress_pattern.match(last_line.strip()): print() # Final newline if needed
        print("--- end of live output ---")
        return_code = process.wait()
        if return_code != 0:
            print(f"\n❌ Transcription failed (exit code {return_code}) for {os.path.basename(file_path)}");
            if os.path.exists(default_srt_path):
                try: print(f"   Cleaning up failed intermediate file: {default_srt_path}"); os.remove(default_srt_path)
                except OSError as rm_e: print(f"   ⚠️ Failed cleanup: {rm_e}")
            return ""
        print(f"\n   Checking for transcription output: {default_srt_path}")
        if os.path.exists(default_srt_path):
            print(f"   Found: {default_srt_path}")
            try:
                if os.path.exists(final_srt_out_path): print(f"   ⚠️ Target path exists, overwriting: {final_srt_out_path}"); os.remove(final_srt_out_path)
                print(f"   Renaming to final path: {final_srt_out_path}")
                os.rename(default_srt_path, final_srt_out_path)
                print(f"✅ Transcription SRT saved to: {final_srt_out_path}")
                return final_srt_out_path
            except OSError as e:
                print(f"❌ Error renaming output file: {e}")
                if os.path.exists(default_srt_path): print(f"⚠️ Using non-titled output name: {default_srt_path}"); return default_srt_path
                return ""
        else:
            print(f"❌ Error: Expected output file not found after successful transcription: {default_srt_path}");
            if os.path.exists(final_srt_out_path): print(f"⚠️ Found final target file unexpectedly: {final_srt_out_path}"); return final_srt_out_path
            return ""
    except FileNotFoundError: print("❌ Critical Error: 'faster-whisper-xxl' command not found.", file=sys.stderr); return ""
    except Exception as e:
        print(f"❌ Unexpected error during transcription: {e}"); traceback.print_exc()
        if process and process.poll() is None: process.kill()
        if os.path.exists(default_srt_path):
            try: print(f"   Cleaning up intermediate file on error: {default_srt_path}"); os.remove(default_srt_path)
            except OSError as rm_e: print(f"   ⚠️ Failed cleanup: {rm_e}")
        return ""

def convert_srt_to_plaintext(srt_path: str) -> Optional[str]:
    """ Converts SRT to plain text, returns string or None on error."""
    lines = []
    timestamp_pattern = re.compile(r'^\d{2}:\d{2}:\d{2}[,.]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[,.]\d{3}$')
    sequence_pattern = re.compile(r'^\d+$')
    speaker_pattern = re.compile(r'^\[SPEAKER_\d+\]\s*')
    try:
        with open(srt_path, 'r', encoding="utf-8", errors="replace") as f:
            for line in f:
                stripped_line = line.strip()
                if not stripped_line or sequence_pattern.match(stripped_line) or timestamp_pattern.match(stripped_line): continue
                text_content = speaker_pattern.sub('', stripped_line)
                if text_content: lines.append(text_content)
        return "\n".join(lines)
    except FileNotFoundError: print(f"❌ Error: SRT not found for text conversion: {srt_path}"); return None
    except Exception as e: print(f"❌ Error converting SRT to text ({srt_path}): {e}"); return None
# --- End of helper functions ---


# === print_help_message (Reflects new default format) ===
def print_help_message():
    lang = DEFAULT_LANGUAGE or "Auto-detect"
    sentence_default = "Enabled" if DEFAULT_SENTENCE else "Disabled"
    rnndn_default = "Enabled" if DEFAULT_FF_RNNDN_XIPH else "Disabled"
    speechnorm_default = "Enabled" if DEFAULT_FF_SPEECHNORM else "Disabled"
    script_name = os.path.basename(sys.argv[0])
    if not script_name.lower().endswith(".py"): script_name = "yttranscribe"

    print(f"""
Usage: {script_name} [options] [URLs | local_files | folders ...]
   or: {script_name} [options] -i INPUT_FILE

Downloads and transcribes media using yt-dlp and faster-whisper-xxl.
Output filenames use the format: Title_InputBaseName_Timestamp.ext

Arguments:
  URLs / local_files / folders
                          One or more YouTube URLs, local media file paths,
                          or folders containing media files. Glob patterns
                          (e.g., *.mp4) are supported.
                          Ignored if -i/--input-file is used. If neither is
                          provided, you will be prompted interactively.

Options:
  -h, --help              Show this help message and exit.

Input File Option:
  -i, --input-file FILE   Specify a text file containing one YouTube URL per line.
                          Overrides positional arguments. Lines starting with #
                          are treated as comments.

Download Options (for URLs):
  -s, --save              Keep downloaded media files in a temporary directory
                          after processing. Default is to delete them.
  -Y, --ytdl-opt OPT      Specify a yt-dlp option as key=value. Can be used
                          multiple times. Keys match yt-dlp Python API options.
                          Overrides script defaults.
                          Default Download Format: 'best,best' (usually merges to MKV).
                          Example Override: -Y format=bestaudio/best
                          Example Merge MP4: -Y merge_output_format=mp4
                          (Note: outtmpl and progress_hooks are controlled by script)

Transcription Options:
  -m, --model MODEL       Whisper model size (Default: {DEFAULT_MODEL})
  -l, --lang LANG         Language code (Default: {lang} auto-detect)
  --task TASK             Task: 'transcribe' or 'translate' (Default: {DEFAULT_TASK})
  -d, --diarization       Enable speaker diarization (Default: {'Enabled' if DEFAULT_ENABLE_DIARIZATION else 'Disabled'})
  -o, --output_dir DIR    Directory to save output files (Default: CWD).

Output Formatting:
  --srt                   Produce SRT output (default if no format specified).
  -t, --text              Produce clean plaintext output.
  --sentence / --no-sentence
                          Enable/disable sentence splitting (Default: {sentence_default})
  -c, --max_comma N       Max commas before split (Default: {DEFAULT_MAX_COMMA})
  -g, --max_gap G         Max gap (sec) for split (Default: {DEFAULT_MAX_GAP})
  -n, --max_line_count N  Max lines per subtitle (Default: {DEFAULT_MAX_LINE_COUNT})

Audio Enhancement Options (Applied by faster-whisper-xxl via ffmpeg):
  -x, --ff_rnndn_xiph / -X, --no-ff_rnndn_xiph
                          Enable/disable FFmpeg RNNoise (Default: {rnndn_default})
  -p, --ff_speechnorm / -P, --no-ff_speechnorm
                          Enable/disable FFmpeg Speechnorm (Default: {speechnorm_default})

Examples:
  {script_name} https://www.youtube.com/watch?v=dQw4w9WgXcQ
  {script_name} -i my_list.txt -s -t
  {script_name} -Y format=bestaudio/best -Y postprocessors=[{{"key":"FFmpegExtractAudio","preferredcodec":"opus"}}] https://...
  {script_name} -Y merge_output_format=mp4 https://youtu.be/some_video_id
  {script_name} local_audio.mp3 -d --no-sentence
  {script_name} *.mp4
"""
)
# === END: Modified print_help_message ===


def main():
    # === Argument Parser Setup (Removed -v flag) ===
    script_name = os.path.basename(sys.argv[0])
    if not script_name.lower().endswith(".py"): script_name = "yttranscribe"
    parser = argparse.ArgumentParser(
        description="Download media via yt-dlp and transcribe with Faster Whisper XXL.",
        usage=f"{script_name} [options] [URLs | local_files | folders ...]\n   or: {script_name} [options] -i INPUT_FILE",
        add_help=False,
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('-h', '--help', action='store_true', help='Show this help message and exit')
    input_group = parser.add_argument_group('Input Source')
    input_group.add_argument('-i', '--input-file', type=str, default=None, help='Text file with URLs')
    input_group.add_argument('inputs', nargs='*', help='URLs, files, folders')
    download_group = parser.add_argument_group('Download Options (for URLs)')
    # -v flag removed here
    download_group.add_argument('-s','--save', dest='keep_downloads', action='store_true', help='Keep downloaded files')
    download_group.add_argument('-Y', '--ytdl-opt', action='append', metavar='key=value', help='Add yt-dlp option')
    transcribe_group = parser.add_argument_group('Transcription Options')
    transcribe_group.add_argument('-m','--model', type=str, default=DEFAULT_MODEL, help=f'Whisper model (Default: {DEFAULT_MODEL})')
    transcribe_group.add_argument('-l','--lang', type=str, default=DEFAULT_LANGUAGE, help='Language code (Default: Auto-detect)')
    transcribe_group.add_argument('--task', type=str, default=DEFAULT_TASK, choices=['transcribe', 'translate'], help=f'Task (Default: {DEFAULT_TASK})')
    transcribe_group.add_argument('-d','--diarization', dest='enable_diarization', action='store_true', default=DEFAULT_ENABLE_DIARIZATION, help='Enable speaker diarization')
    transcribe_group.add_argument('-o','--output_dir', type=str, default=None, help='Output directory (Default: CWD)')
    output_group = parser.add_argument_group('Output Formatting')
    output_group.add_argument('--srt', dest='produce_srt', action='store_true', help='Produce SRT output (default if no format specified)')
    output_group.add_argument('-t','--text', dest='produce_text', action='store_true', help='Produce plaintext output')
    sentence_group = output_group.add_mutually_exclusive_group()
    sentence_group.add_argument('--sentence', dest='sentence', action='store_true', default=DEFAULT_SENTENCE, help=f'Enable sentence splitting (Default: {"Yes" if DEFAULT_SENTENCE else "No"})')
    sentence_group.add_argument('--no-sentence', dest='sentence', action='store_false', help='Disable sentence splitting')
    output_group.add_argument('-c','--max_comma', type=int, default=DEFAULT_MAX_COMMA, help=f'Max commas (Default: {DEFAULT_MAX_COMMA})')
    output_group.add_argument('-g','--max_gap', type=float, default=DEFAULT_MAX_GAP, help=f'Max gap (sec) (Default: {DEFAULT_MAX_GAP})')
    output_group.add_argument('-n','--max_line_count', type=int, default=DEFAULT_MAX_LINE_COUNT, help=f'Max lines/sub (Default: {DEFAULT_MAX_LINE_COUNT})')
    audio_enhance_group = parser.add_argument_group('Audio Enhancement Options (faster-whisper-xxl/ffmpeg)')
    rnndn_group = audio_enhance_group.add_mutually_exclusive_group()
    rnndn_group.add_argument('-x','--ff_rnndn_xiph', dest='ff_rnndn_xiph', action='store_true', default=DEFAULT_FF_RNNDN_XIPH, help=f'Enable FFmpeg RNNoise (Default: {"Yes" if DEFAULT_FF_RNNDN_XIPH else "No"})')
    rnndn_group.add_argument('-X','--no-ff_rnndn_xiph', dest='ff_rnndn_xiph', action='store_false', help='Disable FFmpeg RNNoise')
    speechnorm_group = audio_enhance_group.add_mutually_exclusive_group()
    speechnorm_group.add_argument('-p','--ff_speechnorm', dest='ff_speechnorm', action='store_true', default=DEFAULT_FF_SPEECHNORM, help=f'Enable FFmpeg Speechnorm (Default: {"Yes" if DEFAULT_FF_SPEECHNORM else "No"})')
    speechnorm_group.add_argument('-P','--no-ff_speechnorm', dest='ff_speechnorm', action='store_false', help='Disable FFmpeg Speechnorm')
    # === END: Argument Parser Setup ===

    try: args = parser.parse_args()
    except Exception as parse_err: print(f"Error parsing args: {parse_err}", file=sys.stderr); print_help_message(); sys.exit(2)
    if args.help: print_help_message(); sys.exit(0)

    # --- Process Custom yt-dlp Options ---
    custom_ytdl_opts = {}
    if args.ytdl_opt:
        print("--- Processing Custom yt-dlp Options ---")
        for opt_str in args.ytdl_opt:
            if '=' not in opt_str: print(f"⚠️ Skipping invalid yt-dlp option (missing '='): {opt_str}"); continue
            key, value_str = opt_str.split('=', 1)
            key = key.strip().replace('-', '_')
            value = parse_value(value_str.strip())
            print(f"   Parsed: {key} = {value} ({type(value).__name__})")
            custom_ytdl_opts[key] = value
        print("--- End Custom yt-dlp Options ---")

    # --- Determine Inputs ---
    input_items_raw = []
    input_items_processed = []
    if args.input_file:
        if args.inputs: print(f"⚠️ Warning: --input-file specified; ignoring positional arguments: {args.inputs}")
        try:
            abs_input_file = os.path.abspath(args.input_file)
            print(f"ℹ️ Reading URLs from input file: {abs_input_file}")
            with open(abs_input_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    url = line.strip()
                    if url and not url.startswith('#'):
                         if url.startswith(('http://', 'https://')): input_items_raw.append(url)
                         else: print(f"⚠️ Skipping invalid line {line_num}: Not a URL - '{url}'")
            if not input_items_raw: print(f"❌ Error: Input file '{abs_input_file}' contains no valid URLs.", file=sys.stderr); sys.exit(1)
            input_items_processed = input_items_raw
        except FileNotFoundError: print(f"❌ Error: Input file not found: {abs_input_file}", file=sys.stderr); sys.exit(1)
        except Exception as e: print(f"❌ Error reading input file {abs_input_file}: {e}", file=sys.stderr); traceback.print_exc(); sys.exit(1)
    elif args.inputs:
        input_items_raw = args.inputs
        input_items_processed = get_files_from_args(input_items_raw)
    else:
        print("No input URLs, files, folders, or input file provided via arguments.")
        input_items_processed = prompt_user_for_files_or_folder()
    if not input_items_processed: print("❌ No valid input items found to process. Exiting."); sys.exit(1)

    # --- Separate URLs and Local Files ---
    urls_to_process = [item for item in input_items_processed if isinstance(item, str) and item.startswith(('http://','https://'))]
    local_files_initial = [item for item in input_items_processed if item not in urls_to_process]

    # --- Temp Dir Setup ---
    temp_dir = None
    successfully_downloaded_items = []
    if urls_to_process:
        try:
            temp_dir = tempfile.mkdtemp(prefix='yt_dlp_download_', dir=os.getcwd())
            print(f"ℹ️ Using temporary download directory: {temp_dir}")
        except Exception as e:
            print(f"❌ Failed to create temp directory: {e}", file=sys.stderr)
            if not local_files_initial: sys.exit(1)
            else: print("⚠️ Cannot download URLs. Proceeding with local files only.", file=sys.stderr); urls_to_process = []

    # --- Download phase (Call updated download function) ---
    if urls_to_process and temp_dir:
        print(f"--- Starting downloads for {len(urls_to_process)} URL(s) ---")
        for i, url in enumerate(urls_to_process, 1):
            print("-" * 60)
            print(f"⬇️ Processing URL {i}/{len(urls_to_process)}: {url}")
            # ** CALL UPDATED FUNCTION (no args.download_video) **
            downloaded_path, video_title = download_media_from_youtube(
                url, temp_dir, custom_ytdl_opts
            )
            if downloaded_path and video_title and os.path.exists(downloaded_path):
                print(f"✅ Download successful: {downloaded_path} (Title: {video_title})")
                successfully_downloaded_items.append((downloaded_path, video_title))
            else:
                print(f"⚠️ Download failed or file missing for URL: {url}. Skipping.")
        print("--- Download phase finished ---")

    # --- Prepare final list for transcription ---
    items_to_transcribe = []
    seen_paths = set()
    for f_path in local_files_initial: # Add local files first
        abs_f_path = os.path.abspath(f_path)
        if abs_f_path not in seen_paths:
            if os.path.exists(abs_f_path) and is_media_file(abs_f_path):
                 local_title = os.path.splitext(os.path.basename(abs_f_path))[0]
                 items_to_transcribe.append((abs_f_path, local_title))
                 seen_paths.add(abs_f_path)
    for dl_path, dl_title in successfully_downloaded_items: # Add downloaded files
        abs_dl_path = os.path.abspath(dl_path)
        if abs_dl_path not in seen_paths:
             if os.path.exists(abs_dl_path) and is_media_file(abs_dl_path):
                 items_to_transcribe.append((abs_dl_path, dl_title))
                 seen_paths.add(abs_dl_path)
             else: print(f"⚠️ Skipping downloaded item (invalid/missing path): {abs_dl_path}")
    if not items_to_transcribe:
        print("❌ No valid media items to process. Exiting.")
        if temp_dir and os.path.exists(temp_dir) and not args.keep_downloads:
             try: shutil.rmtree(temp_dir, ignore_errors=True)
             except OSError: pass
        sys.exit(1)

    # --- Determine output formats ---
    produce_srt = args.produce_srt or (not args.produce_srt and not args.produce_text)
    produce_text = args.produce_text

    # --- Print Run Summary ---
    print("-" * 60)
    print(f"▶️ Starting transcription for {len(items_to_transcribe)} item(s)...")
    print(f"   Output Dir: {os.path.abspath(args.output_dir or os.getcwd())}")
    print(f"   Format(s): {'SRT' if produce_srt else ''}{' + ' if produce_srt and produce_text else ''}{'Text' if produce_text else ''}")
    print(f"   Model: {args.model}, Lang: {args.lang or 'auto'}, Task: {args.task}")
    print(f"   Diarization: {'Enabled' if args.enable_diarization else 'Disabled'}")
    print(f"   Sentence Split: {'Enabled' if args.sentence else 'Disabled'} (Comma:{args.max_comma}, Gap:{args.max_gap}s, Lines:{args.max_line_count})")
    print(f"   RNNoise: {'Enabled' if args.ff_rnndn_xiph else 'Disabled'}, Speechnorm: {'Enabled' if args.ff_speechnorm else 'Disabled'}")

    # --- Transcription and Post-processing loop ---
    # (This loop remains the same as previous correct versions)
    success_count = 0
    fail_count = 0
    processed_files_outputs = {}
    for i, (f_path, f_title) in enumerate(items_to_transcribe, 1):
        print("-" * 60)
        print(f"Processing Item {i}/{len(items_to_transcribe)}: {f_path}")
        output_paths_for_file = []
        generated_srt_path = run_whisper_xxl_transcription( f_path, f_title, args.enable_diarization, args.lang, args.model, args.task, args.output_dir, args.sentence, args.max_comma, args.max_gap, args.max_line_count, args.ff_rnndn_xiph, args.ff_speechnorm )
        if not generated_srt_path:
            fail_count += 1; processed_files_outputs[f_path] = []; continue
        text_conversion_successful = False
        if produce_text:
            txt_path = os.path.splitext(generated_srt_path)[0] + '.txt'
            print(f"   Converting SRT to Text: {os.path.basename(txt_path)}")
            plain_text = convert_srt_to_plaintext(generated_srt_path)
            if plain_text is not None:
                if plain_text:
                    try:
                        with open(txt_path, 'w', encoding='utf-8') as out_f: out_f.write(plain_text)
                        print(f"   ✅ Text output saved: {txt_path}"); output_paths_for_file.append(txt_path); text_conversion_successful = True
                    except Exception as e: print(f"   ❌ Failed to write text file {txt_path}: {e}"); text_conversion_successful = False
                else: print(f"   ℹ️ Text conversion resulted in empty file. Skipping write."); text_conversion_successful = True
            else: print(f"   ⚠️ Text conversion failed for {os.path.basename(generated_srt_path)}"); text_conversion_successful = False
        srt_kept = False
        if produce_srt:
            if os.path.exists(generated_srt_path): output_paths_for_file.append(generated_srt_path); srt_kept = True
            else: print(f"   ⚠️ Error: SRT file {generated_srt_path} expected but not found.")
        elif produce_text and os.path.exists(generated_srt_path):
             if text_conversion_successful:
                 try: os.remove(generated_srt_path); print(f"   ℹ️ Removed intermediate SRT file: {os.path.basename(generated_srt_path)}")
                 except OSError as e: print(f"   ⚠️ Could not remove intermediate SRT file {generated_srt_path}: {e}"); output_paths_for_file.append(generated_srt_path); srt_kept = True
             else: print(f"   ℹ️ Keeping SRT file (text conversion failed): {os.path.basename(generated_srt_path)}"); output_paths_for_file.append(generated_srt_path); srt_kept = True
        elif os.path.exists(generated_srt_path): print(f"   ℹ️ Keeping SRT file (fallback): {os.path.basename(generated_srt_path)}"); output_paths_for_file.append(generated_srt_path); srt_kept = True
        if output_paths_for_file: success_count += 1; processed_files_outputs[f_path] = output_paths_for_file
        else: print(f"⚠️ No final output files confirmed for {os.path.basename(f_path)}."); fail_count += 1; processed_files_outputs[f_path] = []

    # --- Cleanup phase ---
    # (Remains the same)
    print("-" * 60)
    if temp_dir and os.path.exists(temp_dir):
        if not args.keep_downloads:
            print(f"🧹 Cleaning up temporary download directory: {temp_dir}")
            try: shutil.rmtree(temp_dir); print(f"   ✅ Temporary directory removed.")
            except Exception as e: print(f"   ⚠️ Error removing temp dir {temp_dir}: {e}")
        else:
            try:
                if os.listdir(temp_dir): print(f"✅ Downloads retained in directory (--save): {temp_dir}")
                else: print(f"ℹ️ Temporary directory is empty but kept (--save): {temp_dir}")
            except OSError: print(f"✅ Downloads retained in directory (--save, contents check failed): {temp_dir}")

    # --- Final Summary ---
    # (Remains the same)
    print("\n" + "=" * 60)
    print("🏁 Processing Summary:")
    print(f"   Total Items Processed: {len(items_to_transcribe)}")
    if success_count > 0: print(f"✅ Successful Transcriptions: {success_count}")
    if fail_count > 0: print(f"❌ Failed Items: {fail_count}")
    print("=" * 60)
    if success_count > 0 and fail_count == 0: sys.exit(0)
    elif success_count > 0 and fail_count > 0: sys.exit(2)
    else: sys.exit(1)


# --- Main execution block ---
if __name__ == '__main__':
    # (Dependency checks remain the same)
    print("--- Dependency Checks ---")
    whisper_ok = False
    try: result = subprocess.run(["faster-whisper-xxl", "--version"], capture_output=True, check=True, text=True, encoding='utf-8', errors='replace', timeout=5); print(f"✅ faster-whisper-xxl found: {result.stdout.strip()}"); whisper_ok = True
    except FileNotFoundError: print("❌ Critical Error: 'faster-whisper-xxl' not found.", file=sys.stderr); sys.exit(1)
    except Exception as check_e: print(f"⚠️ Warning checking faster-whisper-xxl: {check_e}", file=sys.stderr); whisper_ok = True
    ffmpeg_ok = False
    try: result = subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True, text=True, encoding='utf-8', errors='replace', timeout=5); print(f"✅ ffmpeg found: {result.stdout.splitlines()[0].strip()}"); ffmpeg_ok = True
    except FileNotFoundError: print("❌ Critical Error: 'ffmpeg' not found.", file=sys.stderr); sys.exit(1)
    except Exception as check_e: print(f"⚠️ Warning checking ffmpeg: {check_e}", file=sys.stderr); ffmpeg_ok = True
    print("--- Dependency Checks Complete ---")

    # (Error handling around main() remains the same)
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Operation cancelled. Cleaning up...")
        try:
            potential_temp_dirs = glob.glob(os.path.join(os.getcwd(), 'yt_dlp_download_*'))
            for p_dir in potential_temp_dirs:
                 if os.path.isdir(p_dir): print(f"   Removing temp dir: {p_dir}"); shutil.rmtree(p_dir, ignore_errors=True)
        except Exception as cleanup_e: print(f"   ⚠️ Error during cleanup: {cleanup_e}")
        sys.exit(130)
    except Exception as e:
        print("\n" + "="*60, file=sys.stderr); print("❌ Unexpected critical error:", file=sys.stderr); traceback.print_exc(); print("="*60, file=sys.stderr); sys.exit(3)