#!/usr/bin/env python3
"""
# ASS to SRT Converter & Video Remuxer

A robust Python utility to convert Advanced SubStation Alpha (`.ass`) subtitle tracks to SubRip (`.srt`) format and optionally remux them back into their parent video containers.

## 🚀 Key Features

*   **Unicode Safe**: Bypasses Windows locale issues by using raw binary capture and manual UTF-8 decoding for all subprocess communications.
*   **Direct Conversion**: Converts subtitle tracks directly from the source video to SRT, avoiding unreliable intermediate files.
*   **Preserves Metadata**: Automatically detects and restores track titles and language codes in the remuxed output.
*   **Automatic Backup**: Moves original files to a dedicated `originals/` subfolder instead of modifying them in place.
*   **Verbose Logging**: Provides real-time, step-by-step diagnostic output for all operations (Probing, Extraction, Conversion, Remuxing).
*   **Recursive Scanning**: Scans directories recursively for both standalone `.ass` files and video containers.

## 🛠 Prerequisites

*   **Python 3.7+**
*   **FFmpeg & FFprobe**: Must be installed and accessible in your system `PATH`.

## 📖 Usage

### Standard Usage
Process the current directory:
```bash
python asstosrt.py
```

### Specify Directory
Process a specific folder or file:
```bash
python asstosrt.py /path/to/media
```

## ⚙️ How it Works

1.  **Scanning**: The script identifies video files (`.mkv`, `.mp4`, etc.) and standalone `.ass` files.
2.  **Probing**: Uses `ffprobe` to identify internal ASS/SSA subtitle streams and their metadata.
3.  **Conversion**: 
    - For videos: Extracts and converts tracks directly to SRT using FFmpeg.
    - For standalone files: Converts `.ass` to `.srt`.
4.  **Remuxing**: Creates a new video file replacing the internal ASS tracks with the new SRT versions, preserving stream order.
5.  **Reorganization**:
    - Creates an `originals/` subfolder in the source directory.
    - Moves the original video file into `originals/`.
    - Places the processed video at the original path with the original name.

---
"""

import argparse
import os
import tempfile
import shutil
import subprocess
from pathlib import Path
import json

# Supported file extensions
VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm'}
ASS_EXTENSION = '.ass'
BACKUP_FOLDER = "originals"

def scan_directory(directory):
    """Scan the directory recursively for video and .ass files."""
    videos = []
    ass_files = []
    for path in Path(directory).rglob('*'):
        # Skip files already inside a backup folder
        if BACKUP_FOLDER in path.parts:
            continue
        if path.is_file():
            if path.suffix.lower() in VIDEO_EXTENSIONS:
                videos.append(path)
            elif path.suffix.lower() == ASS_EXTENSION:
                ass_files.append(path)
    return videos, ass_files

def convert_ass_to_srt(ass_path, srt_path):
    """Convert .ass file to .srt using ffmpeg."""
    print(f"[CONVERT] Converting standalone ASS: {ass_path.name} -> {srt_path.name}")
    cmd = ['ffmpeg', '-y', '-hide_banner', '-i', str(ass_path), '-f', 'srt', str(srt_path)]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=60)
        if result.returncode != 0:
            stderr = result.stderr.decode('utf-8', errors='replace')
            print(f"[ERROR] FFmpeg failed for {ass_path.name}:\n{stderr}")
            return False
    except subprocess.TimeoutExpired:
        print(f"[TIMEOUT] Failed to convert {ass_path.name}")
        return False
    except Exception as e:
        print(f"[ERROR] Unexpected error converting {ass_path.name}: {e}")
        return False

    if not srt_path.exists() or srt_path.stat().st_size == 0:
        print(f"[ERROR] {srt_path.name} was not created or is empty.")
        return False
    return True

def probe_video(video_path):
    """Probe video for streams using ffprobe directly with binary capture to avoid Unicode errors."""
    print(f"[PROBE] Probing streams for: {video_path.name}")
    cmd = [
        'ffprobe', '-v', 'error', 
        '-show_entries', 'stream=index,codec_name,codec_type:stream_tags=language,title', 
        '-of', 'json', str(video_path)
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=30)
        if result.returncode != 0:
            stderr = result.stderr.decode('utf-8', errors='replace')
            print(f"[ERROR] ffprobe failed for {video_path.name}:\n{stderr}")
            return []
        
        # Manually decode binary output to UTF-8
        output_str = result.stdout.decode('utf-8', errors='replace')
        data = json.loads(output_str)
        return data.get('streams', [])
    except Exception as e:
        print(f"[ERROR] Failed to probe {video_path.name}: {e}")
        return []

def find_ass_subtitle_streams(streams):
    """Find indices of .ass/.ssa subtitle streams."""
    ass_streams = []
    for stream in streams:
        if stream.get('codec_type') == 'subtitle' and stream.get('codec_name') in ['ass', 'ssa', 'subrip']:
            # We also check for 'subrip' just in case, but primary goal is fixing ASS
            if stream.get('codec_name') in ['ass', 'ssa']:
                ass_streams.append((stream['index'], stream))
    return ass_streams

def extract_and_convert_to_srt(video_path, stream_index, output_srt_path):
    """Extract and convert a subtitle stream directly to SRT from the source video."""
    print(f"[EXTRACT] Converting stream {stream_index} directly to SRT...")
    cmd = ['ffmpeg', '-y', '-hide_banner', '-i', str(video_path), '-map', f'0:{stream_index}', '-f', 'srt', str(output_srt_path)]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=120)
        if result.returncode != 0:
            stderr = result.stderr.decode('utf-8', errors='replace')
            print(f"[ERROR] Extraction failed for stream {stream_index}:\n{stderr}")
            return False
    except subprocess.TimeoutExpired:
        print(f"[TIMEOUT] Extraction timed out for stream {stream_index}")
        return False
    
    if not output_srt_path.exists() or output_srt_path.stat().st_size == 0:
        print(f"[ERROR] Output SRT {output_srt_path.name} is empty or missing.")
        return False
    return True

def remux_video_with_multiple_srt(video_path, temp_srts, output_path):
    """Remux video replacing multiple .ass tracks with .srt, preserving stream order and metadata."""
    print(f"[REMUX] Starting remux for: {video_path.name}")
    streams = probe_video(video_path)
    if not streams:
        return False

    cmd = ['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-i', str(video_path)]
    for _, _, srt in temp_srts:
        cmd.extend(['-i', str(srt)])
    
    output_args = []
    sub_count = 0
    srt_input_index = 1
    
    for stream in streams:
        i = stream['index']
        if stream['codec_type'] == 'subtitle':
            replaced = False
            for idx, (ass_index, stream_info, _) in enumerate(temp_srts):
                if i == ass_index:
                    output_args.extend(['-map', f'{srt_input_index + idx}:0', '-c:s', 'srt'])
                    tags = stream_info.get('tags', {})
                    replaced = True
                    break
            
            if not replaced:
                output_args.extend(['-map', f'0:{i}'])
                tags = stream.get('tags', {})
            
            for key, value in tags.items():
                output_args.extend([f'-metadata:s:s:{sub_count}', f'{key}={value}'])
            sub_count += 1
        else:
            output_args.extend(['-map', f'0:{i}'])
    
    output_args.extend(['-c', 'copy'])
    cmd.extend(output_args)
    cmd.append(str(output_path))
    
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=600)
        if result.returncode != 0:
            stderr = result.stderr.decode('utf-8', errors='replace')
            print(f"[ERROR] Remux failed:\n{stderr}")
            return False
        return True
    except Exception as e:
        print(f"[ERROR] Remux error: {e}")
        return False

def process_ass_files(ass_files):
    """Process standalone .ass files."""
    if not ass_files:
        return
    print(f"--- Processing {len(ass_files)} standalone ASS files ---")
    for ass_path in ass_files:
        srt_path = ass_path.with_suffix('.srt')
        if convert_ass_to_srt(ass_path, srt_path):
            print(f"[DONE] Converted {ass_path.name}")

def process_video(video_path):
    """Process a video file for embedded .ass subtitles."""
    print(f"\n--- Processing Video: {video_path.name} ---")
    streams = probe_video(video_path)
    if not streams:
        return

    ass_streams = find_ass_subtitle_streams(streams)
    if not ass_streams:
        print(f"[SKIP] No ASS streams found in {video_path.name}")
        return

    print(f"[INFO] Found {len(ass_streams)} ASS stream(s)")
    for idx, info in ass_streams:
        title = info.get('tags', {}).get('title', 'No Title')
        lang = info.get('tags', {}).get('language', 'und')
        print(f"  - Stream {idx}: {info['codec_name']} [{lang}] ({title})")

    with tempfile.TemporaryDirectory() as tmpdir:
        temp_dir = Path(tmpdir)
        temp_srts = []
        for ass_index, stream_info in ass_streams:
            temp_srt = temp_dir / f"temp_{ass_index}.srt"
            if extract_and_convert_to_srt(video_path, ass_index, temp_srt):
                temp_srts.append((ass_index, stream_info, temp_srt))
            else:
                print(f"[WARN] Skipping track {ass_index} due to conversion failure.")
        
        if temp_srts:
            output_path = video_path.with_stem(f"{video_path.stem}_ass_to_srt")
            if remux_video_with_multiple_srt(video_path, temp_srts, output_path):
                print(f"[FINISH] Replaced {len(temp_srts)} track(s) in {video_path.name}")
                
                # Move original to backup folder and processed file to original path
                backup_dir = video_path.parent / BACKUP_FOLDER
                backup_dir.mkdir(exist_ok=True)
                backup_path = backup_dir / video_path.name
                
                try:
                    shutil.move(str(video_path), str(backup_path))
                    shutil.move(str(output_path), str(video_path))
                    print(f"[SUCCESS] Original moved to {BACKUP_FOLDER}/{video_path.name}")
                except Exception as e:
                    print(f"[ERROR] Failed to finalize file reorganization: {e}")
            else:
                print(f"[ERROR] Failed to remux {video_path.name}")
        else:
            print(f"[SKIP] No tracks were successfully converted for {video_path.name}")

def main():
    parser = argparse.ArgumentParser(description="Convert ASS to SRT in files and videos.")
    parser.add_argument('path', nargs='?', default='.', help="File or directory to process (default: current directory)")
    args = parser.parse_args()

    path = Path(args.path)
    if not path.exists():
        print(f"Path {path} does not exist.")
        return

    if path.is_file():
        if path.suffix.lower() == ASS_EXTENSION:
            process_ass_files([path])
        elif path.suffix.lower() in VIDEO_EXTENSIONS:
            process_video(path)
        else:
            print(f"Unsupported file type: {path}")
    else:
        videos, ass_files = scan_directory(path)
        print(f"Found {len(videos)} video files and {len(ass_files)} .ass files.")
        process_ass_files(ass_files)
        for video in videos:
            process_video(video)

if __name__ == "__main__":
    main()
