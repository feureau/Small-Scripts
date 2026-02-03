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


# ---------------------------------------------------------------------------
# Session Layout Management
# ---------------------------------------------------------------------------
# Caches to ensure we use the same output/input folders for all files 
# in the same directory during a single script run.
OUTPUT_DIRS = {}        # Key: source_dir_path -> Value: output_dir_path
INPUT_BACKUP_DIRS = {}  # Key: (source_dir_path, extension) -> Value: input_backup_dir_path

def get_output_folder(source_dir, ext):
    """
    Returns a unique output folder for this session and source directory.
    E.g., source/mp4, or source/mp4 (1) if mp4 exists.
    """
    if source_dir in OUTPUT_DIRS:
        return OUTPUT_DIRS[source_dir]
    
    folder_name = ext.lstrip('.')
    base_path = os.path.join(source_dir, folder_name)
    
    # Logic: Always make a new folder. If it exists, increment.
    # Note: If the user runs the script, we check existence. 
    # If "mp4" exists, we try "mp4 (1)".
    final_path = base_path
    counter = 1
    while os.path.exists(final_path):
        final_path = f"{base_path} ({counter})"
        counter += 1
    
    try:
        os.makedirs(final_path, exist_ok=True)
    except OSError:
        pass # Handle race conditions or permission issues gracefully
        
    OUTPUT_DIRS[source_dir] = final_path
    return final_path

def get_input_backup_folder(source_dir, ext):
    """
    Returns a unique input backup folder for this session, directory, and extension.
    E.g., source/mp4-input, or source/mp4-input (1).
    """
    key = (source_dir, ext)
    if key in INPUT_BACKUP_DIRS:
        return INPUT_BACKUP_DIRS[key]
    
    folder_name = f"{ext.lstrip('.')}-input"
    base_path = os.path.join(source_dir, folder_name)
    
    final_path = base_path
    counter = 1
    while os.path.exists(final_path):
        final_path = f"{base_path} ({counter})"
        counter += 1
        
    try:
        os.makedirs(final_path, exist_ok=True)
    except OSError:
        pass
        
    INPUT_BACKUP_DIRS[key] = final_path
    return final_path

def move_input_to_backup(file_path):
    """Moves the input file to the session-allocated backup folder."""
    if not os.path.isfile(file_path):
        return

    source_dir = os.path.dirname(file_path)
    filename = os.path.basename(file_path)
    _, ext = os.path.splitext(filename)
    
    # Get the designated backup folder for this file type
    backup_dir = get_input_backup_folder(source_dir, ext)
    
    target_path = os.path.join(backup_dir, filename)
    
    # If specific filename exists in backup (rare given folder logic, but possible if mixed batches), increment
    if os.path.exists(target_path):
        base, extension = os.path.splitext(filename)
        counter = 1
        while os.path.exists(os.path.join(backup_dir, f"{base}_{counter}{extension}")):
            counter += 1
        target_path = os.path.join(backup_dir, f"{base}_{counter}{extension}")

    print(f"  Moving original file: {file_path} -> {target_path}")
    try:
        shutil.move(file_path, target_path)
        return target_path
    except Exception as e:
        print(f"  Error moving file: {e}")
        return None

# ---------------------------------------------------------------------------
# Audio Conversion Logic
# ---------------------------------------------------------------------------
def select_audio_encoder(channels):
    """
    Selects the appropriate encoder and bitrate based on channel count.
    Logic taken from ffmpegac3.py.
    """
    if channels <= 6:
        return "ac3", "640k"
    elif channels <= 8:
        return "eac3", "640k"
    else:
        return None, None

# ---------------------------------------------------------------------------
# Audio Conversion Logic
# ---------------------------------------------------------------------------
def select_audio_encoder(channels):
    """
    Selects the appropriate encoder and bitrate based on channel count.
    Logic taken from ffmpegac3.py.
    """
    if channels <= 6:
        return "ac3", "640k"
    elif channels <= 8:
        return "eac3", "640k"
    else:
        return None, None

def convert_to_subtitle_free_video(input_file, output_extension, force_output_dir=None):
    """Converts a video to subtitle-free version (smart audio conversion)."""
    if not os.path.isfile(input_file):
        print(f"Skipping non-file: {input_file}")
        return None

    base, _ = os.path.splitext(input_file)
    
    if force_output_dir:
        dest_dir = force_output_dir
    else:
        # Use session-based output folder logic
        source_dir = os.path.dirname(input_file)
        dest_dir = get_output_folder(source_dir, output_extension)
    
    # Output filename matches input basename + new extension
    # Per request: "output file will always match"
    output_filename = os.path.basename(base) + "." + output_extension.lstrip('.')
    output_file = os.path.join(dest_dir, output_filename)

    # Collision check within the NEW folder (shouldn't happen often if folder is new, but safety check)
    if os.path.exists(output_file):
        # Even if folder is new, if we process two files named 'video.mp4' in same source? 
        # Unlikely but possible if globbing weirdly.
        print(f"  Warning: Output file {output_file} already exists.")
        # Safe bet: Increment to avoid data loss.
        base_name, ext = os.path.splitext(output_filename)
        counter = 1
        while os.path.exists(output_file):
            output_file = os.path.join(dest_dir, f"{base_name} ({counter}){ext}")
            counter += 1

    print(f"Converting: {input_file} -> {output_file}")

    # Probe audio streams with expanded details
    audio_streams = _probe_audio_streams(input_file)
    
    if not audio_streams:
        print("  WARNING: Probing returned 0 audio streams. Using safety fallback (Copy All).")
        print("  This file will NOT be strictly converted to AC3 5.1 because details could not be read.")

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
    
    # Process each audio stream
    for i, s in enumerate(sorted_audio):
        idx = s['index']
        codec = s.get('codec_name', 'unknown').lower()
        
        # Ensure channels is an int
        try:
            channels = int(s.get('channels', 2))
        except (ValueError, TypeError):
            channels = 2
            
        layout = s.get('channel_layout', 'unknown')

        # Map the stream
        audio_maps.extend(["-map", f"0:{idx}"])

        # Determine if we can copy (Passthrough) or need to convert
        # Strict 5.1 LCR enforcement:
        # Must be AC3, 6 channels, and layout strictly '5.1' (not 5.1(side) etc)
        is_compliant = (codec == 'ac3' and channels == 6 and layout == '5.1')

        if is_compliant:
            print(f"  [Stream {idx}] Pass: {codec}, {channels}ch, layout='{layout}' -> Copy")
            audio_maps.extend([f"-c:a:{i}", "copy"])
        else:
            print(f"  [Stream {idx}] Fail: {codec}, {channels}ch, layout='{layout}' -> Converting to AC3 5.1")
            # Force AC3 5.1 (6 channels) implementation match ffmpegac3.py logic
            audio_maps.extend([
                f"-c:a:{i}", "ac3",
                f"-b:a:{i}", "640k",
                f"-ac:{i}", "6"
            ])

        # Disposition handling
        # Set first audio track (a:0 in output) as default, others not
        if i == 0:
            dispositions.extend([f"-disposition:a:0", "default"])
        else:
            dispositions.extend([f"-disposition:a:{i}", "0"])
    
    # If no audio streams found by probe, fallback (risky but keeps existing fallback logic)
    if not audio_maps:
        audio_maps = ["-map", "0:a?", "-c:a", "copy"]

    command = [
        "ffmpeg", "-hide_banner",
        "-i", input_file,
        "-map", "0:v?", 
    ] + audio_maps + dispositions + [
        "-c:v", "copy",
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
    # Added channels and channel_layout to the query
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "a",
        "-show_streams",
        "-show_entries", "stream=index,codec_name,channels,channel_layout,tags",
        "-of", "json", video_path
    ]
    proc = run_command(cmd, capture_output=True)
    if proc is None:
        print(f"  FFprobe failed to start for {video_path}")
        return []
    if proc.returncode != 0:
        print(f"  FFprobe returned non-zero for {video_path} (rc={proc.returncode})")
        # Print stderr to help diagnose why probe failed
        if getattr(proc, "stderr", None):
             print(f"  FFprobe stderr: {proc.stderr}")
        return []

    try:
        data = json.loads(proc.stdout or "{}")
        streams = data.get("streams", [])
        if not streams:
             print(f"  Frame probe successful but returned 0 audio streams.")
        return streams
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

def _ensure_srt_subfolder(video_path, base_dir=None):
    """Ensure a subfolder named 'SRT' exists. Uses base_dir if provided, else video_path dir."""
    parent = base_dir if base_dir else os.path.dirname(video_path)
    folder = os.path.join(parent, "SRT")
    os.makedirs(folder, exist_ok=True)
    return folder

def _extract_to_srt(video_path, streams, basename, output_dir_override=None):
    if not streams:
        print("  No text-based subtitles found.")
        return
    output_dir = _ensure_srt_subfolder(video_path, base_dir=output_dir_override)
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

def _package_bitmap_subs(video_path, streams, basename, output_dir_override=None):
    if not streams:
        print("  No bitmap subtitles found.")
        return
    output_dir = _ensure_srt_subfolder(video_path, base_dir=output_dir_override)
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

def extract_subtitles(video_path, mode="hybrid", output_dir_override=None):
    """Main entry for subtitle extraction (hybrid/srt/mkv)."""
    basename = os.path.splitext(os.path.basename(video_path))[0]
    subs = _probe_subtitle_streams(video_path)
    if not subs:
        print("  No subtitles found.")
        return
    text_subs = [s for s in subs if s.get('codec_name', '').lower() in KNOWN_TEXT_SUBTITLE_CODECS]
    bitmap_subs = [s for s in subs if s not in text_subs]

    if mode == "srt":
        _extract_to_srt(video_path, subs, basename, output_dir_override)
    elif mode == "mkv":
        _package_bitmap_subs(video_path, subs, basename, output_dir_override)
    else:
        if text_subs:
            _extract_to_srt(video_path, text_subs, basename, output_dir_override)
        if bitmap_subs:
            _package_bitmap_subs(video_path, bitmap_subs, basename, output_dir_override)

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

    # Strict list of supported video extensions
    supported_exts = (".mkv", ".mp4", ".avi", ".mov", ".flv", ".webm", ".wmv", ".m4v", ".ts", ".mts")

    # Directories to ignore during recursive scan (generated folders)
    # We ignore generic output/input generated names to avoid re-processing outputs
    ignored_dirs = {"SRT", "subs", "subtitles"}
    
    files_to_process = []
    
    # Helper to check if file is supported video
    def is_supported_video(f_path):
        return os.path.isfile(f_path) and f_path.lower().endswith(supported_exts)

    if args.input_patterns:
        for pattern in args.input_patterns:
            if os.path.isdir(pattern):
                for root, dirs, files in os.walk(pattern):
                    # Smart prune: Modify dirs in-place to skip ignored folders
                    # skips folders like 'SRT', 'mp4', or any '*-input'
                    dirs[:] = [
                        d for d in dirs 
                        if d not in ignored_dirs 
                        and not d.endswith("-input") 
                        and not (d == args.extension.lstrip('.')) # ignore output folder e.g. 'mp4'
                        # handle incremented folders too e.g. 'mp4 (1)'
                        and not (d.startswith(args.extension.lstrip('.') + " ("))
                    ]
                    
                    for f in files:
                        if f.lower().endswith(supported_exts):
                            files_to_process.append(os.path.join(root, f))
                            
            elif os.path.isfile(pattern):
                # Direct file path - strict check
                if is_supported_video(pattern):
                    files_to_process.append(os.path.abspath(pattern))
                else:
                    print(f"Skipping unsupported file type: {pattern}")
            else:
                # Treat as glob pattern
                expanded = glob.glob(pattern)
                for match in expanded:
                    # Filter glob results strictly
                    if is_supported_video(match):
                        files_to_process.append(os.path.abspath(match))
                    elif os.path.isfile(match):
                         # Verbose skip for clarity
                         pass 
    else:
        # Recursive scan of CWD
        print("Scanning current directory recursively for video files...")
        for root, dirs, files in os.walk(os.getcwd()):
            # Smart prune here as well
            dirs[:] = [
                d for d in dirs 
                if d not in ignored_dirs 
                and not d.endswith("-input") 
                and not (d == args.extension.lstrip('.'))
                and not (d.startswith(args.extension.lstrip('.') + " ("))
            ]
            
            for f in files:
                if f.lower().endswith(supported_exts):
                    files_to_process.append(os.path.join(root, f))

    if not files_to_process:
        print("No supported video files found.")
        return

    print(f"Found {len(files_to_process)} video(s) to process.")

    for file_path in files_to_process:
        print(f"\n--- Processing: {file_path} ---")
        
        # Double check before processing (redundant but safe)
        if not is_supported_video(file_path):
             print(f"  Skipping non-video file: {file_path}")
             continue
        
        # 1. Move Original File to Backup FIRST
        # Returns the new path of the file in the backup folder
        backup_file_path = move_input_to_backup(file_path)
        
        if not backup_file_path:
             print("  Skipping file due to move failure.")
             continue
             
        # 2. Convert from Backup -> Original Location
        # force_output_dir = where the file ORIGINALLY was
        original_dir = os.path.dirname(file_path)
        
        converted_file = convert_to_subtitle_free_video(
            backup_file_path, 
            args.extension, 
            force_output_dir=original_dir
        )
        
        if converted_file:
            print("  Conversion done.")
            
        # 3. Extract Subtitles from the Backup file
        # Force explicit output to original dir so 'SRT' folder attempts to be in root
        extract_subtitles(backup_file_path, mode=args.format, output_dir_override=original_dir)

    print("\nAll processing complete.")

if __name__ == "__main__":
    main()
