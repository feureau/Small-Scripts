#!/usr/bin/env python3
"""
Batch converter to remux .ts files into proper MKV containers.
Handles corrupted streams and missing timestamps without re-encoding.
Designed to work when called from any folder.

Example usage (from command prompt):
    tstomkv.py *.ts
    Or specify paths:
    tstomkv.py "video1.ts" "video2.ts"
"""

import os
import subprocess
import sys
from pathlib import Path

def get_input_files(args):
    """Get list of .ts file paths from command line."""
    if not args:
        # Look in current working directory for wildcards or all .ts files
        ts_files = []
        cwd = Path.cwd()
        
        # Check for explicit *.ts pattern in arguments first
        for arg in args:
            p = Path(arg)
            if "*" in str(p):
                matches = list(cwd.glob(str(p)))
                ts_files.extend([str(m.resolve()) for m in sorted(matches)])
            elif "?" in str(p):
                matches = list(cwd.glob(str(p)))
                ts_files.extend([str(m.resolve()) for m in sorted(matches)])
        
        # If no wildcards, glob all .ts files
        if not ts_files:
            for f in cwd.glob("*.ts"):
                ts_files.append(str(f.resolve()))
            for f in cwd.glob("*.TS"):
                ts_files.append(str(f.resolve()))
    else:
        # Arguments provided - handle paths and wildcards
        ts_files = []
        for arg in args:
            p = Path(arg)
            
            if "*" in str(p) or "?" in str(p):
                # Wildcard pattern - expand relative to current directory
                matches = list(Path.cwd().glob(str(p)))
                ts_files.extend([str(m.resolve()) for m in sorted(matches)])
            elif p.exists():
                # Absolute path or existing file
                ts_files.append(str(p.resolve()))
            else:
                print(f"[Warning] Skipping non-existent file: {arg}", flush=True)
        
        if not ts_files:
            print("[Error]: No valid .ts files found.", flush=True)
            return None

    # Filter only .ts files from any wildcards
    filtered = [f for f in ts_files if Path(f).suffix.lower() == ".ts"]
    
    if not filtered:
        print("[Error]: No .ts files found after filtering.", flush=True)
        return None
    
    return filtered

def convert_to_mkv(input_path):
    """Remux .ts file to MKV using ffmpeg with corruption fixes."""
    try:
        output_base = os.path.splitext(os.path.basename(input_path))[0]
        output_path = f"{output_base}.mkv"
        full_output = str(Path.cwd() / output_path)

        print(f"Processing: {os.path.basename(input_path)}...")
        
        result = subprocess.run(
            [
                'ffmpeg', '-i', input_path,
                '-fflags', '+genpts',
                '-avoid_negative_ts', '1',
                '-c:v', 'copy',
                '-c:a', 'aac',
                '-map', '0:v?',  # Video (optional)
                '-map', '0:a?',  # Audio (optional)
                '-map', '0:s?',  # Subtitle (optional - arlibcaption format)
                full_output,
                '-y'
            ],
            capture_output=True,
            text=True
        )
        
        stderr_output = result.stderr.strip()
        if result.returncode != 0:
            lines = stderr_output.split('\n')[-5:] if len(stderr_output.split('\n')) > 5 else [stderr_output]
            for line in lines:
                print(f"    {line}", flush=True)
        
        success = Path(full_output).exists() and result.returncode == 0
        
        if success:
            file_size = os.path.getsize(full_output) / (1024 * 1024)
            print(f"  [OK] Created {output_path} ({file_size:.1f} MB)")
            return True
        else:
            if result.returncode != 0:
                print(f"  [FAIL] Conversion failed (exit code {result.returncode}).")
            elif not Path(full_output).exists():
                print(f"  [FAIL] Output file was not created.")
            else:
                print(f"  [WARN] File size is 0 bytes - likely corrupted source.")
            return False
            
    except Exception as e:
        print(f"  [ERROR] Unexpected error: {e}")
        return False

def main():
    if len(sys.argv) < 2:
        # No arguments passed, let the function handle current directory globbing
        ts_files = get_input_files([])
    else:
        # Arguments provided
        ts_files = get_input_files(sys.argv[1:])

    if not ts_files:
        print("No .ts files found to process.")
        return

    total = len(ts_files)
    success_count = 0
    
    print(f"\nFound {total} TS file(s). Starting remux...\n")

    for f in ts_files:
        if convert_to_mkv(str(f)):
            success_count += 1
        else:
            # Optional: Log failed files to a separate log or just continue
            pass
    
    print(f"\nDone! Success: {success_count}/{total}")

if __name__ == "__main__":
    main()
