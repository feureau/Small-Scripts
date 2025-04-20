#!/usr/bin/env python3
"""
transcribe_with_yt_dlp.py - Download media from YouTube via yt-dlp and transcribe with Faster Whisper XXL
--------------------------------------------------------------------------------------------------
- Downloads audio (default) or video (with -v) from YouTube URLs.
- Transcribes with Whisper XXL, then (by default) cleans up downloads.
- Use -s/--save to keep downloaded files after completion.
- Saves SRT or text output in the same directory with timestamped filenames.
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
def download_media_from_youtube(url: str, download_dir: str, download_video: bool) -> str:
    """
    Download best audio (wav) or best video+audio (container) from YouTube URL.
    Returns the local path to the downloaded file.
    """
    if download_video:
        ydl_opts = {
            'format': 'bestvideo+bestaudio',
            'outtmpl': os.path.join(download_dir, '%(id)s.%(ext)s'),
            'quiet': True,
            'merge_output_format': 'mp4'
        }
    else:
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(download_dir, '%(id)s.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'wav',
                'preferredquality': '192',
            }],
            'quiet': True,
            'no_warnings': True
        }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        if download_video:
            # Media file is the downloaded container
            media_path = filename
        else:
            media_path = os.path.splitext(filename)[0] + '.wav'
        if os.path.exists(media_path):
            return media_path
        raise FileNotFoundError(f"Download failed, file not found: {media_path}")


def is_media_file(filepath: str) -> bool:
    SUPPORTED = {'.wav','.mp3','.flac','.m4a','.aac','.ogg','.wma',
                 '.mp4','.mkv','.mov','.avi','.wmv','.m4v'}
    return os.path.splitext(filepath)[1].lower() in SUPPORTED


def get_files_from_args(args: list) -> list:
    collected = []
    for arg in args:
        if '*' in arg or '?' in arg:
            for path in glob.glob(arg):
                path = os.path.abspath(path)
                if os.path.isdir(path):
                    for f in os.listdir(path):
                        if is_media_file(f): collected.append(os.path.join(path, f))
                elif is_media_file(path):
                    collected.append(path)
        else:
            path = os.path.abspath(arg)
            if os.path.isdir(path):
                for f in os.listdir(path):
                    if is_media_file(f): collected.append(os.path.join(path, f))
            elif is_media_file(path):
                collected.append(path)
    return collected


def prompt_user_for_files_or_folder() -> list:
    root = tk.Tk(); root.withdraw()
    choice = input("Press [F] for folder, [A] for files, [Q] to quit: ").lower()
    if choice == 'q': sys.exit(0)
    if choice == 'f':
        folder = filedialog.askdirectory(title="Select Folder")
        return [os.path.join(folder, f) for f in os.listdir(folder) if is_media_file(f)] if folder else []
    if choice == 'a':
        files = filedialog.askopenfilenames(title="Select Media Files")
        return list(files) if files else []
    print("Invalid choice. Exiting."); sys.exit(0)


def run_whisper_xxl_transcription(
    file_path, enable_diarization, language, model, task,
    output_dir, sentence, max_comma, max_gap, max_line_count,
    ff_rnndn_xiph, ff_speechnorm, produce_srt
) -> str:
    file_dir = output_dir or os.path.dirname(file_path)
    base = os.path.splitext(os.path.basename(file_path))[0]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_name = f"{base}_{timestamp}.srt"
    out_path = os.path.join(file_dir, out_name)

    cmd = ["faster-whisper-xxl", file_path, "--model", model,
           "--task", task, "--output_format", "srt", "--output_dir", file_dir]
    if language: cmd += ["--language", language]
    if sentence: cmd.append("--sentence")
    cmd += ["--max_comma", str(max_comma), "--max_gap", str(max_gap), "--max_line_count", str(max_line_count)]
    if ff_rnndn_xiph: cmd.append("--ff_rnndn_xiph")
    if ff_speechnorm: cmd.append("--ff_speechnorm")
    if enable_diarization: cmd += ["--diarize", ENABLE_DIARIZATION_METHOD]

    print(f"🔥 Transcribing: {os.path.basename(file_path)}")
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in proc.stdout:
        print(line, end="")
    if proc.wait() != 0:
        print(f"❌ Transcription failed ({proc.returncode})"); return ""

    default_srt = os.path.join(file_dir, f"{base}.srt")
    if os.path.exists(default_srt):
        os.rename(default_srt, out_path)
        print(f"✅ Output: {out_name}")
        return out_path
    print(f"❌ Expected SRT not found: {default_srt}"); return ""


def convert_srt_to_plaintext(srt_path: str) -> str:
    lines, pat = [], re.compile(r'\d{2}:\d{2}:\d{2}[,\.]\d{3}\s*-->')
    with open(srt_path, encoding="utf-8", errors="replace") as f:
        for ln in f:
            t = ln.strip()
            if t.isdigit() or pat.match(t) or not t: continue
            lines.append(t)
    return "\n".join(lines)


def print_help_message():
    lang = DEFAULT_LANGUAGE or "Auto-detect"
    print(f"""
Usage: transcribe_with_yt_dlp.py [options] [URLs/files/...]
Options:
  -h, --help              Show help
  -v, --video             Download video instead of audio
  -s, --save              Keep downloaded media files (skip cleanup)
  --srt                   Produce SRT output (default)
  -t, --text              Produce plaintext output
  -d, --diarization       Enable speaker diarization (pyannote_v3.1)
  -l, --lang LANG         Language code (Default: {lang})
  -m, --model MODEL       Model size (Default: {DEFAULT_MODEL})
  --task TASK             transcribe or translate (Default: {DEFAULT_TASK})
  -o, --output_dir DIR    Output directory (default: same as input)
  --sentence              Enable sentence splitting
  --no-sentence           Disable sentence splitting
  -c, --max_comma N       Max commas before split ({DEFAULT_MAX_COMMA})
  -g, --max_gap G         Max gap in seconds ({DEFAULT_MAX_GAP})
  -n, --max_line_count N  Max lines per subtitle ({DEFAULT_MAX_LINE_COUNT})
  -x, --ff_rnndn_xiph     Enable RNNDN XIPH processing
  -X, --no-ff_rnndn_xiph  Disable RNNDN XIPH
  -p, --ff_speechnorm     Enable speechnorm processing
  -P, --no-ff_speechnorm  Disable speechnorm
Examples:
  python3 transcribe_with_yt_dlp.py -v -s https://youtu.be/... -t
"""
)


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('-h','--help', action='store_true')
    parser.add_argument('-v','--video', dest='download_video', action='store_true')
    parser.add_argument('-s','--save', dest='keep_downloads', action='store_true')
    parser.add_argument('--srt', action='store_true')
    parser.add_argument('-t','--text', action='store_true')
    parser.add_argument('-d','--diarization', action='store_true')
    parser.add_argument('-l','--lang', type=str, default=DEFAULT_LANGUAGE)
    parser.add_argument('-m','--model', type=str, default=DEFAULT_MODEL)
    parser.add_argument('--task', type=str, default=DEFAULT_TASK)
    parser.add_argument('-o','--output_dir', type=str, default=None)
    parser.add_argument('--sentence', dest='sentence', action='store_true')
    parser.add_argument('--no-sentence', dest='sentence', action='store_false')
    parser.set_defaults(sentence=DEFAULT_SENTENCE)
    parser.add_argument('-c','--max_comma', type=int, default=DEFAULT_MAX_COMMA)
    parser.add_argument('-g','--max_gap', type=float, default=DEFAULT_MAX_GAP)
    parser.add_argument('-n','--max_line_count', type=int, default=DEFAULT_MAX_LINE_COUNT)
    parser.add_argument('-x','--ff_rnndn_xiph', dest='ff_rnndn_xiph', action='store_true')
    parser.add_argument('-X','--no-ff_rnndn_xiph', dest='ff_rnndn_xiph', action='store_false')
    parser.set_defaults(ff_rnndn_xiph=DEFAULT_FF_RNNDN_XIPH)
    parser.add_argument('-p','--ff_speechnorm', dest='ff_speechnorm', action='store_true')
    parser.add_argument('-P','--no-ff_speechnorm', dest='ff_speechnorm', action='store_false')
    parser.set_defaults(ff_speechnorm=DEFAULT_FF_SPEECHNORM)
    parser.add_argument('inputs', nargs='*')
    args = parser.parse_args()

    if args.help:
        print_help_message(); sys.exit(0)

    temp_dir = tempfile.mkdtemp(prefix='yt_')
    downloaded = []
    local_inputs = []

    for inp in args.inputs:
        if inp.startswith(('http://','https://')):
            print(f"⬇️ Downloading: {inp}")
            try:
                path = download_media_from_youtube(inp, temp_dir, args.download_video)
                downloaded.append(path)
                local_inputs.append(path)
            except Exception as e:
                print(f"❌ Download failed: {e}")
        else:
            local_inputs.append(inp)

    files = get_files_from_args(local_inputs) if local_inputs else prompt_user_for_files_or_folder()
    if not files:
        print("No files to process. Exiting.")
        if not args.keep_downloads:
            shutil.rmtree(temp_dir, ignore_errors=True)
        sys.exit(0)

    produce_srt = args.srt or (not args.srt and not args.text)
    produce_text = args.text

    for f in files:
        srt = run_whisper_xxl_transcription(
            f, args.diarization, args.lang, args.model, args.task,
            args.output_dir, args.sentence, args.max_comma, args.max_gap,
            args.max_line_count, args.ff_rnndn_xiph, args.ff_speechnorm,
            produce_srt
        )
        if not srt:
            print(f"⚠️ Skipping {f}")
            continue
        if produce_text:
            txt_path = os.path.splitext(srt)[0] + '.txt'
            try:
                pt = convert_srt_to_plaintext(srt)
                with open(txt_path, 'w', encoding='utf-8') as out: out.write(pt)
                print(f"✅ Text: {os.path.basename(txt_path)}")
            except Exception as e:
                print(f"❌ Txt write failed: {e}")
        if not produce_srt:
            try: os.remove(srt)
            except: pass

    # Cleanup downloads unless saving
    if not args.keep_downloads:
        for dl in downloaded:
            try: os.remove(dl)
            except: pass
        shutil.rmtree(temp_dir, ignore_errors=True)
    else:
        print(f"ℹ️ Downloads retained in temp directory: {temp_dir}")

    print("\n✅ All processing completed successfully!")

if __name__ == '__main__':
    main()
