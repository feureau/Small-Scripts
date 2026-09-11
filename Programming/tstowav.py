#!/usr/bin/env python3
"""
Batch converter to extract audio from .ts files and save as WAV.
No external dependencies required (only ffmpeg).
Designed to work when called from any folder.
"""

import os
import subprocess
import sys
from pathlib import Path

def get_input_files(args):
    """Get list of .ts file paths."""
    if not args:
        # No arguments provided, look in current working directory
        ts_files = [str(f.resolve()) for f in (Path.cwd().glob("*.ts") | Path.cwd().glob("*.TS"))]
    else:
        # Arguments provided, try to resolve them
        ts_files = []
        for arg in args:
            p = Path(arg)
            if "*" in str(p) or "?" in str(p):
                # If wildcard is used, resolve relative to current directory
                matches = list(Path.cwd().glob(str(p)))
                ts_files.extend([str(m.resolve()) for m in matches])
            elif p.exists():
                # Absolute path or existing file
                ts_files.append(str(p.resolve()))
        
        if not ts_files:
            print("[Error]: No valid .ts files found or provided.")
            return None

    return ts_files

def convert_file(input_path):
    """Extract audio to WAV using ffmpeg."""
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    output_path = f"{base_name}.wav"
    
    # Full path for output (saved in current directory)
    full_output = str(Path.cwd() / output_path)

    cmd = [
        'ffmpeg', '-i', input_path,
        '-vn',           # Disable video stream
        '-c:a', 'pcm_s16le',   # Audio codec for WAV
        '-ar', '48000',       # Sample rate
        '-ac', '2',           # Channels
        full_output
    ]

    print(f"Processing: {os.path.basename(input_path)}...")
    
    try:
        subprocess.run(cmd, check=True)
        print(f"  [OK] Saved as {output_path}")
        return True
    except subprocess.CalledProcessError:
        print(f"  [FAIL] Conversion failed.")
        return False
    except Exception as e:
        print(f"  [ERROR] Unexpected error: {e}")
        return False

def main():
    if len(sys.argv) < 2:
        # Check for no arguments first, then handle logic inside get_input_files
        files = get_input_files(None)
    else:
        files = get_input_files(sys.argv[1:])

    if not files:
        print("No .ts files found to process.")
        return

    print(f"\nFound {len(files)} TS file(s). Starting conversion...\n")

    success_count = 0
    for f in files:
        if convert_file(f):
            success_count += 1
        else:
            # Optional: Log failed files to a separate log or just skip
            pass
    
    print(f"\nDone! Success: {success_count}/{len(files)}")

if __name__ == "__main__":
    main()
