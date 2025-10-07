#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
Comprehensive FFmpeg Batch Processor with Embedded Subtitle Extraction
================================================================================

Author: (Your Name)
Version: 1.1
Date: 2025-10-07

--------------------------------------------------------------------------------
UPDATE SUMMARY (v1.1)
--------------------------------------------------------------------------------
• Subtitle outputs are now placed in a subfolder named “SRT” inside the same
  directory as each video input.
  Example:
      /Movies/Action/Movie1.mkv
      /Movies/Action/SRT/Movie1_sub1_idx0_eng_srt.srt

• All SRT and MKV subtitle outputs use this subfolder.
• The folder is created automatically if it does not exist.
--------------------------------------------------------------------------------
DOCUMENTATION & IMPLEMENTATION NOTES
--------------------------------------------------------------------------------

This script automates **video processing and subtitle extraction** for entire
directory trees. It is designed for batch workflows involving `.mkv`, `.mp4`,
and other video containers. It performs two primary operations per file:

  1. **Conversion to subtitle-free video** (default: `.mp4`):
       - Uses FFmpeg to remove all subtitle streams while copying
         video/audio tracks losslessly.
       - Keeps original codecs to ensure zero-quality degradation.
       - Outputs into the same folder as the original file.

  2. **Subtitle extraction** (default: hybrid mode):
       - Uses FFprobe to detect subtitle streams.
       - Extracts text-based subtitles (e.g., SRT, ASS, WebVTT) directly
         into `.srt` format.
       - Packages non-text (bitmap) subtitles (e.g., PGS, VobSub)
         into `.mkv` files.
       - Places all outputs in the same folder as the source video.

--------------------------------------------------------------------------------
RATIONALE & DESIGN DECISIONS
--------------------------------------------------------------------------------

• **Recursive scanning via os.walk**
    Instead of relying on `glob.glob` (non-recursive by default), this script
    uses `os.walk` to ensure every subdirectory under the working directory is
    scanned for supported video files. This supports large and nested libraries.

• **Direct FFmpeg/FFprobe invocation**
    The script calls FFmpeg and FFprobe directly through `subprocess` for
    maximum control and portability. Using libraries like `ffmpeg-python` would
    add dependencies and restrict cross-platform compatibility.

• **Lossless video/audio copy**
    The conversion uses `-c:v copy -c:a copy -sn`, which means video and audio
    are *not* re-encoded. This ensures speed and prevents quality loss.
    Subtitles are stripped via `-sn`.

• **Hybrid subtitle extraction logic**
    The embedded module from `srtextract.py` provides robust handling of both
    text and bitmap subtitle codecs. The hybrid mode extracts `.srt` for text
    and `.mkv` for non-text subtitles automatically.

• **Embedded design**
    The subtitle extraction system is embedded within this script so users can
    run a single file without managing multiple modules. This simplifies
    deployment across systems.

• **Command-line customization**
    Users can specify:
        - Target extension (default `.mp4`) with `-e`
        - Subtitle extraction format (default `hybrid`) with `-f`
        - Custom file patterns or directories

• **Safety mechanisms**
    - Skips processing when input and output paths are identical.
    - Deletes zero-byte outputs on failure.
    - Warns when FFmpeg or FFprobe are missing.

--------------------------------------------------------------------------------
USAGE
--------------------------------------------------------------------------------

    python3 ffmpegtomp4_full.py [-e EXT] [-f FORMAT] [patterns...]

Examples:
    python3 ffmpegtomp4_full.py
    python3 ffmpegtomp4_full.py -e mp4 -f hybrid
    python3 ffmpegtomp4_full.py -f srt **/*.mkv
    python3 ffmpegtomp4_full.py -e mov -f mkv /path/to/videos

--------------------------------------------------------------------------------
DEPENDENCIES
--------------------------------------------------------------------------------
    • FFmpeg and FFprobe must be installed and in system PATH.
      Download: https://ffmpeg.org/download.html

--------------------------------------------------------------------------------
UPDATE POLICY
--------------------------------------------------------------------------------
For every script revision or feature update:
    - This documentation block MUST be retained and updated.
    - Any new behavior or design change must be documented with rationale.
================================================================================
"""

import argparse
import os
import sys
import subprocess
import json
import traceback

# ==============================================================================
# FFmpeg Utilities
# ==============================================================================

def find_ffmpeg_tools():
    """Check that ffmpeg and ffprobe are installed and accessible."""
    from shutil import which
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

    try:
        process = subprocess.run(command, capture_output=True, text=True)
        if process.returncode == 0:
            print(f"  Created: {output_file}")
            return output_file
        else:
            print(f"  FFmpeg error converting {input_file}")
            print(process.stderr)
            if os.path.exists(output_file) and os.path.getsize(output_file) == 0:
                os.remove(output_file)
            return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        traceback.print_exc()
        return None

# ==============================================================================
# Embedded Subtitle Extraction Module (modified to use /SRT subfolder)
# ==============================================================================

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
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(proc.stdout)
        return data.get("streams", [])
    except Exception as e:
        print(f"  FFprobe error for {video_path}: {e}")
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
        cmd = ["ffmpeg", "-i", video_path, "-map", f"0:{s['index']}", "-y", output_path]
        print(f"  Extracting stream {s['index']} to {output_path}")
        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            print(f"    OK: {output_path}")
        except subprocess.CalledProcessError as e:
            print(f"    Failed: {output_path}")
            if os.path.exists(output_path) and os.path.getsize(output_path) < 20:
                os.remove(output_path)

def _package_bitmap_subs(video_path, streams, basename):
    if not streams:
        print("  No bitmap subtitles found.")
        return
    output_dir = _ensure_srt_subfolder(video_path)
    for i, s in enumerate(streams, 1):
        output_path = os.path.join(output_dir, _generate_subtitle_filename(basename, s, i, "mkv"))
        cmd = ["ffmpeg", "-i", video_path, "-map", f"0:{s['index']}", "-c", "copy", "-y", output_path]
        print(f"  Packaging stream {s['index']} to {output_path}")
        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            print(f"    OK: {output_path}")
        except subprocess.CalledProcessError:
            print(f"    Failed: {output_path}")

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

# ==============================================================================
# Main Control Flow
# ==============================================================================

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
