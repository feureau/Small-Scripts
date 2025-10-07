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
  - Centralized subprocess invocation via `run_command()` which sets:
      text=True, encoding='utf-8', errors='replace'
    This forces safe UTF-8 decoding and replaces undecodable bytes instead
    of raising exceptions.
  - Consistent handling of CompletedProcess objects and clearer error logs.
  - Safer cleanup of zero-byte outputs on failure.
  - Minor logging improvements for clarity.
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

--------------------------------------------------------------------------------
LICENSE / NOTES
--------------------------------------------------------------------------------
- Keep this header updated when changing behavior.
================================================================================
"""

import argparse
import os
import sys
import subprocess
import json
import traceback
from shutil import which

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

    print(f"Converting: {input_file} -> {output_file}")
    command = [
        "ffmpeg", "-hide_banner",
        "-i", input_file,
        "-map", "0:v?", "-map", "0:a?",
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

# ---------------------------------------------------------------------------
# Embedded Subtitle Extraction Module
# ---------------------------------------------------------------------------
KNOWN_TEXT_SUBTITLE_CODECS = [
    'srt', 'subrip', 'ass', 'ssa', 'webvtt', 'mov_text', 'tx3g',
    'subviewer', 'microdvd', 'eia_608', 'cea608'
]

def _probe_subtitle_streams(video_path):
    """Probe subtitle streams via ffprobe (returns list of stream dicts)."""
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "s",
        "-show_entries", "stream=index,codec_name,tags", "-of", "json", video_path
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

def _safe_filename(s):
    return "".join(c if c.isalnum() or c in "._-" else "_" for c in s)

def _generate_subtitle_filename(video_basename, stream_info, i, ext):
    codec = stream_info.get('codec_name', 'unknown').lower()
    lang = stream_info.get('tags', {}).get('language', 'und')
    name = f"{video_basename}_sub{i}_idx{stream_info['index']}_{lang}_{codec}.{ext}"
    return _safe_filename(name)[:180]

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
        output_path = os.path.join(output_dir, _generate_subtitle_filename(basename, s, i, "srt"))
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
        output_path = os.path.join(output_dir, _generate_subtitle_filename(basename, s, i, "mkv"))
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
            else:
                if os.path.isfile(pattern) and pattern.lower().endswith(supported_exts):
                    files_to_process.append(os.path.abspath(pattern))
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

    print("\nAll processing complete.")

if __name__ == "__main__":
    main()
