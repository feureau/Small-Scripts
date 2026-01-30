#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
Comprehensive FFmpeg Batch Processor with Robust Subprocess Decoding
================================================================================

Author: (Your Name)
Version: 1.2
Date: 2025-10-07

SUMMARY OF FIX (v1.2)
--------------------------------------------------------------------------------
Primary problem fixed:
  - Windows `UnicodeDecodeError` raised in subprocess reader threads when
    Python attempted to decode ffmpeg/ffprobe output with the system default
    encoding (cp1252) and encountered bytes not representable in that codec.

Key changes in this release:
  - Synchronized subtitle naming logic with `srtextract.py`.
  - Expanded language codes to full names (e.g. `eng` -> `English`) using `pycountry`.
  - Prioritized `Language` tag over `Title` for consistent naming.
  - Added automatic detection of `[Forced]` tracks via stream disposition.
  - Implemented Unicode-safe filename sanitization (preserving characters like `Á`).
  - Added internal collision detection for duplicate track names.
  - Centralized subprocess invocation via `run_command()` which sets:
      text=True, encoding='utf-8', errors='replace'
    This forces safe UTF-8 decoding and replaces undecodable bytes instead
    of raising exceptions.
  - Consistent handling of CompletedProcess objects and clearer error logs.
  - Safer cleanup of zero-byte outputs on failure.
  - All existing behavior preserved unless otherwise stated.

RATIONALE
--------------------------------------------------------------------------------
- Using an explicit encoding and `errors='replace'` prevents
  `UnicodeDecodeError` while keeping stderr/stdout readable.
- Centralizing subprocess calls simplifies future changes such as streaming
  output or logging to file.

USAGE
--------------------------------------------------------------------------------
    python3 ffmpegtomp4.py [-e EXT] [-f FORMAT] [patterns...]

Examples:
    python3 ffmpegtomp4.py
    python3 ffmpegtomp4.py -e mp4 -f hybrid
    python3 ffmpegtomp4.py -f srt **/*.mkv
    python3 ffmpegtomp4.py -e mov -f mkv /path/to/videos

DEPENDENCIES
--------------------------------------------------------------------------------
- FFmpeg and FFprobe must be installed and in system PATH.
  https://ffmpeg.org/download.html
- pycountry library (optional but recommended for full language names).
  Install via: pip install pycountry

--------------------------------------------------------------------------------
LICENSE / NOTES
--------------------------------------------------------------------------------
- Keep this header updated when changing behavior.
================================================================================
"""

import argparse
import glob
import os
import sys
import subprocess
import json
import traceback
import shutil
from shutil import which

try:
    import pycountry # For language name expansion
except ImportError:
    pycountry = None

# ---------------------------------------------------------------------------
# Configuration: change these if you need different decoding behavior
# ---------------------------------------------------------------------------
SUBPROCESS_ENCODING = "utf-8"
SUBPROCESS_ERRORS = "replace"  # 'replace' avoids exceptions, preserves logs

# ---------------------------------------------------------------------------
# Utility: central subprocess runner with safe decoding
# ---------------------------------------------------------------------------
def run_command(cmd, capture_output=True, check=False):
    """
    Run a subprocess command with safe decoding.
    - capture_output True returns CompletedProcess with stdout/stderr decoded
      using SUBPROCESS_ENCODING and SUBPROCESS_ERRORS.
    - check is kept for compatibility but exceptions are not raised here. The
      caller should inspect returncode.
    Returns CompletedProcess or None on unexpected exception.
    """
    try:
        if capture_output:
            return subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding=SUBPROCESS_ENCODING,
                errors=SUBPROCESS_ERRORS,
            )
        else:
            # Let subprocess print to console (stdout/stderr inherit from parent)
            return subprocess.run(cmd)
    except Exception:
        print(f"  Subprocess failed to start: {cmd}")
        traceback.print_exc()
        return None

# ---------------------------------------------------------------------------
# FFmpeg Utilities
# ---------------------------------------------------------------------------
def find_ffmpeg_tools():
    """Check that ffmpeg and ffprobe are installed and accessible."""
    ffmpeg_found = which("ffmpeg") is not None
    ffprobe_found = which("ffprobe") is not None

    if not ffmpeg_found:
        print("ERROR: ffmpeg not found in PATH.")
    if not ffprobe_found:
        print("ERROR: ffprobe not found in PATH.")
    return ffmpeg_found and ffprobe_found


def convert_to_subtitle_free_video(input_file, output_extension):
    """Converts a video to subtitle-free version (no re-encoding, same codecs)."""
    if not os.path.isfile(input_file):
        print(f"Skipping non-file: {input_file}")
        return None

    base, _ = os.path.splitext(input_file)
    output_file = base + "." + output_extension.lstrip('.')

    if os.path.abspath(input_file) == os.path.abspath(output_file):
        print(f"Skipping identical paths: {input_file}")
        return None

    dest_dir = os.path.dirname(output_file)
    if dest_dir:
        os.makedirs(dest_dir, exist_ok=True)

    print(f"Converting: {input_file} -> {output_file}")

    # Probe audio streams to prioritize English
    audio_streams = _probe_audio_streams(input_file)
    
    # Sort: 'eng' or 'en' first, then others
    def audio_sort_key(s):
        tags = s.get('tags', {})
        lang = ""
        for k, v in tags.items():
            if k.lower() == 'language':
                lang = v.lower()
                break
        # Prioritize English (eng or en)
        return 0 if lang in ('eng', 'en') else 1

    sorted_audio = sorted(audio_streams, key=audio_sort_key)
    
    audio_maps = []
    dispositions = []
    for i, s in enumerate(sorted_audio):
        audio_maps.extend(["-map", f"0:{s['index']}"])
        # Set first audio track (a:0 in output) as default, others not
        if i == 0:
            dispositions.extend(["-disposition:a:0", "default"])
        else:
            dispositions.extend([f"-disposition:a:{i}", "0"])
    
    # If no audio streams found by probe, fallback to mapping all audio
    if not audio_maps:
        audio_maps = ["-map", "0:a?"]

    command = [
        "ffmpeg", "-hide_banner",
        "-i", input_file,
        "-map", "0:v?", 
    ] + audio_maps + dispositions + [
        "-c:v", "copy", "-c:a", "copy",
        "-sn", "-map_metadata", "0", "-map_chapters", "0",
        "-strict", "experimental", "-y", output_file
    ]

    proc = run_command(command, capture_output=True)
    if proc is None:
        print(f"  Failed to start ffmpeg for {input_file}")
        return None

    if proc.returncode == 0:
        print(f"  Created: {output_file}")
        return output_file
    else:
        print(f"  FFmpeg error converting {input_file} (returncode {proc.returncode})")
        # print stderr if available
        if getattr(proc, "stderr", None):
            print(proc.stderr)
        # Remove empty output if created
        if os.path.exists(output_file) and os.path.getsize(output_file) == 0:
            try:
                os.remove(output_file)
            except Exception:
                pass
        return None


def _probe_audio_streams(video_path):
    """Probe audio streams via ffprobe (returns list of stream dicts)."""
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "a",
        "-show_streams",
        "-show_entries", "stream=index,codec_name,tags",
        "-of", "json", video_path
    ]
    proc = run_command(cmd, capture_output=True)
    if proc is None:
        print(f"  FFprobe failed to start for {video_path}")
        return []
    if proc.returncode != 0:
        print(f"  FFprobe returned non-zero for {video_path} (rc={proc.returncode})")
        return []

    try:
        data = json.loads(proc.stdout or "{}")
        return data.get("streams", []) or []
    except Exception:
        print(f"  Failed to parse audio streams for {video_path}")
        return []

# ---------------------------------------------------------------------------
# Embedded Subtitle Extraction Module
# ---------------------------------------------------------------------------
KNOWN_TEXT_SUBTITLE_CODECS = [
    'srt', 'subrip', 'ass', 'ssa', 'webvtt', 'mov_text', 'tx3g',
    'subviewer', 'microdvd', 'eia_608', 'cea608'
]

def _get_language_name(code):
    """
    Converts ISO 639-2 (3-letter) or ISO 639-1 (2-letter) codes to full names.
    Falls back to original code if pycountry missing or name not found.
    """
    if not code or not pycountry:
        return code
    try:
        lang = pycountry.languages.get(alpha_3=code.lower())
        if not lang:
            lang = pycountry.languages.get(alpha_2=code.lower())
        return lang.name if lang else code
    except Exception:
        return code

def _probe_subtitle_streams(video_path):
    """Probe subtitle streams via ffprobe (returns list of stream dicts)."""
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "s",
        "-show_streams",
        "-show_entries", "stream=index,codec_name,disposition,tags", 
        "-of", "json", video_path
    ]
    proc = run_command(cmd, capture_output=True)
    if proc is None:
        print(f"  FFprobe failed to start for {video_path}")
        return []
    if proc.returncode != 0:
        print(f"  FFprobe returned non-zero for {video_path} (rc={proc.returncode})")
        if getattr(proc, "stderr", None):
            print(proc.stderr)
        return []

    try:
        data = json.loads(proc.stdout or "{}")
        return data.get("streams", []) or []
    except json.JSONDecodeError:
        print(f"  Failed to parse ffprobe JSON for {video_path}")
        if getattr(proc, "stdout", None):
            # Dump raw (decoded with replacement) output to help debugging
            print(proc.stdout)
        return []
    except Exception:
        print(f"  Unexpected error parsing ffprobe output for {video_path}")
        traceback.print_exc()
        return []

def _generate_subtitle_filename(video_basename, stream_info, ext, output_dir):
    tags = stream_info.get('tags', {})
    disposition = stream_info.get('disposition', {})
    
    # Case-insensitive lookup for Title and Language
    title = None
    language = None
    for k, v in tags.items():
        if k.lower() == 'title':
            title = v
        if k.lower() == 'language':
            language = _get_language_name(v)

    # Check for Forced flag
    is_forced = str(disposition.get('forced', '0')) == '1'

    # Prioritize Language, then Title, then "Unknown"
    tag = language if language else (title if title else "Unknown")

    # Add [Forced] suffix if needed
    if is_forced and "[Forced]" not in tag and "forced" not in tag.lower():
        tag = f"{tag} [Forced]"

    # Sanitization
    illegal_chars = r'\/:*?"<>|'
    sanitized_tag = "".join(c for c in tag if c not in illegal_chars).strip()
    if not sanitized_tag:
        sanitized_tag = "Unknown"

    filename = f"{video_basename} - {sanitized_tag}.{ext}"
    
    # Collision detection
    base_name_no_ext = f"{video_basename} - {sanitized_tag}"
    counter = 1
    while os.path.exists(os.path.join(output_dir, filename)):
        filename = f"{base_name_no_ext} ({counter}).{ext}"
        counter += 1

    return filename

def _ensure_srt_subfolder(video_path):
    """Ensure a subfolder named 'SRT' exists in the same directory as the video."""
    folder = os.path.join(os.path.dirname(video_path), "SRT")
    os.makedirs(folder, exist_ok=True)
    return folder

def _extract_to_srt(video_path, streams, basename):
    if not streams:
        print("  No text-based subtitles found.")
        return
    output_dir = _ensure_srt_subfolder(video_path)
    for i, s in enumerate(streams, 1):
        output_filename = _generate_subtitle_filename(basename, s, "srt", output_dir)
        output_path = os.path.join(output_dir, output_filename)
        cmd = ["ffmpeg", "-hide_banner", "-i", video_path, "-map", f"0:{s['index']}", "-y", output_path]
        print(f"  Extracting stream {s['index']} to {output_path}")
        proc = run_command(cmd, capture_output=True)
        if proc is None:
            print(f"    Failed to start extraction for stream {s['index']}")
            continue
        if proc.returncode == 0:
            print(f"    OK: {output_path}")
        else:
            print(f"    Failed: {output_path} (rc={proc.returncode})")
            if getattr(proc, "stderr", None):
                print(proc.stderr)
            # If small/empty output created then remove it
            try:
                if os.path.exists(output_path) and os.path.getsize(output_path) < 20:
                    os.remove(output_path)
            except Exception:
                pass

def _package_bitmap_subs(video_path, streams, basename):
    if not streams:
        print("  No bitmap subtitles found.")
        return
    output_dir = _ensure_srt_subfolder(video_path)
    for i, s in enumerate(streams, 1):
        output_filename = _generate_subtitle_filename(basename, s, "mkv", output_dir)
        output_path = os.path.join(output_dir, output_filename)
        cmd = ["ffmpeg", "-hide_banner", "-i", video_path, "-map", f"0:{s['index']}", "-c", "copy", "-y", output_path]
        print(f"  Packaging stream {s['index']} to {output_path}")
        proc = run_command(cmd, capture_output=True)
        if proc is None:
            print(f"    Failed to start packaging for stream {s['index']}")
            continue
        if proc.returncode == 0:
            print(f"    OK: {output_path}")
        else:
            print(f"    Failed: {output_path} (rc={proc.returncode})")
            if getattr(proc, "stderr", None):
                print(proc.stderr)
            # Remove zero-byte or tiny files
            try:
                if os.path.exists(output_path) and os.path.getsize(output_path) < 20:
                    os.remove(output_path)
            except Exception:
                pass

def extract_subtitles(video_path, mode="hybrid"):
    """Main entry for subtitle extraction (hybrid/srt/mkv)."""
    basename = os.path.splitext(os.path.basename(video_path))[0]
    subs = _probe_subtitle_streams(video_path)
    if not subs:
        print("  No subtitles found.")
        return
    text_subs = [s for s in subs if s.get('codec_name', '').lower() in KNOWN_TEXT_SUBTITLE_CODECS]
    bitmap_subs = [s for s in subs if s not in text_subs]

    if mode == "srt":
        _extract_to_srt(video_path, subs, basename)
    elif mode == "mkv":
        _package_bitmap_subs(video_path, subs, basename)
    else:
        if text_subs:
            _extract_to_srt(video_path, text_subs, basename)
        if bitmap_subs:
            _package_bitmap_subs(video_path, bitmap_subs, basename)

def move_original_file(file_path):
    """
    Moves the original file to a subfolder named after its extension.
    Example: video.mkv -> mkv/video.mkv
    """
    if not os.path.isfile(file_path):
        return

    dir_path = os.path.dirname(file_path)
    filename = os.path.basename(file_path)
    _, ext = os.path.splitext(filename)
    
    # Normalize extension for folder name
    ext_folder = ext.lstrip('.').lower()
    if not ext_folder:
        ext_folder = "no_extension"
    
    # Check if we're already in a folder named after the extension
    parent_folder = os.path.basename(dir_path)
    if parent_folder.lower() == ext_folder:
        print(f"  File already in '{ext_folder}' folder. Skipping move.")
        return

    target_dir = os.path.join(dir_path, ext_folder)
    os.makedirs(target_dir, exist_ok=True)
    
    target_path = os.path.join(target_dir, filename)
    
    # Handle filename collisions
    if os.path.exists(target_path):
        base, extension = os.path.splitext(filename)
        counter = 1
        while os.path.exists(os.path.join(target_dir, f"{base}_{counter}{extension}")):
            counter += 1
        target_path = os.path.join(target_dir, f"{base}_{counter}{extension}")

    print(f"  Moving original file: {file_path} -> {target_path}")
    try:
        shutil.move(file_path, target_path)
    except Exception as e:
        print(f"  Error moving file: {e}")

# ---------------------------------------------------------------------------
# Main Control Flow
# ---------------------------------------------------------------------------
def main():
    if not find_ffmpeg_tools():
        sys.exit(1)

    parser = argparse.ArgumentParser(
        description="Recursively convert videos to subtitle-free format and extract subtitles."
    )
    parser.add_argument("-e", "--extension", default="mp4",
                        help="Target container extension (default: mp4)")
    parser.add_argument("-f", "--format",
                        choices=["hybrid", "srt", "mkv"], default="hybrid",
                        help="Subtitle extraction format (default: hybrid)")
    parser.add_argument("input_patterns", nargs="*",
                        help="Optional file patterns or directories (default: recursive scan)")
    args = parser.parse_args()

    supported_exts = (".mkv", ".mp4", ".avi", ".mov", ".flv", ".webm", ".wmv")
    files_to_process = []

    if args.input_patterns:
        for pattern in args.input_patterns:
            if os.path.isdir(pattern):
                for root, _, files in os.walk(pattern):
                    for f in files:
                        if f.lower().endswith(supported_exts):
                            files_to_process.append(os.path.join(root, f))
            elif os.path.isfile(pattern):
                # Direct file path
                if pattern.lower().endswith(supported_exts):
                    files_to_process.append(os.path.abspath(pattern))
            else:
                # Treat as glob pattern (e.g., *.mkv) - expands wildcards on Windows
                expanded = glob.glob(pattern)
                for match in expanded:
                    if os.path.isfile(match) and match.lower().endswith(supported_exts):
                        files_to_process.append(os.path.abspath(match))
    else:
        for root, _, files in os.walk(os.getcwd()):
            for f in files:
                if f.lower().endswith(supported_exts):
                    files_to_process.append(os.path.join(root, f))

    if not files_to_process:
        print("No supported video files found.")
        return

    print(f"Found {len(files_to_process)} video(s) to process.")

    for file_path in files_to_process:
        print(f"\n--- Processing: {file_path} ---")
        converted = convert_to_subtitle_free_video(file_path, args.extension)
        if converted:
            print("  Conversion done.")
        extract_subtitles(file_path, mode=args.format)
        move_original_file(file_path)

    print("\nAll processing complete.")

if __name__ == "__main__":
    main()
