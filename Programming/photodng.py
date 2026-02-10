#!/usr/bin/env python3
import os
import glob
import argparse
import subprocess

# --- CONFIGURATION ---
# Path updated to your specific installation location
DNG_CONVERTER_PATH = r"C:\Program Files\Adobe\Adobe DNG Converter\Adobe DNG Converter.exe"

# Common RAW extensions to look for
RAW_EXTENSIONS = {'.arw', '.cr2', '.cr3', '.nef', '.orf', '.raf', '.srw', '.dcr'}

def convert_to_dng_adobe(filepath):
    """
    Calls Adobe DNG Converter CLI to create a Resolve-compatible DNG.
    """
    if not os.path.exists(DNG_CONVERTER_PATH):
        print(f"   [ERROR] Adobe DNG Converter not found at: {DNG_CONVERTER_PATH}")
        return False

    filename = os.path.basename(filepath)
    output_dir = os.path.dirname(filepath)
    
    print(f"   [Processing] {filename}")

    try:
        # -c : lossless compression
        # -d : output directory (same as source)
        # filepath : the source raw file
        cmd = [
            DNG_CONVERTER_PATH,
            "-c",
            "-d", output_dir,
            filepath
        ]
        
        # Run process; capture_output=True keeps the console clean
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            return True
        else:
            print(f"   [ERROR] Converter failed for {filename}: {result.stderr}")
            return False

    except Exception as e:
        print(f"   [ERROR] System error during {filename}: {e}")
        return False

def get_all_raw_files(start_dir):
    """
    Recursively scans for raw files.
    """
    raw_files = []
    for root, _, files in os.walk(start_dir):
        for file in files:
            if os.path.splitext(file)[1].lower() in RAW_EXTENSIONS:
                raw_files.append(os.path.join(root, file))
    return raw_files

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Adobe-Powered Raw to DNG Converter")
    parser.add_argument("files", nargs='*', help="Input files, wildcards, or leave empty for recursive folder scan.")
    args = parser.parse_args()

    input_paths = []
    
    # Logic: If no arguments, scan the current directory tree
    if not args.files:
        current_dir = os.getcwd()
        print(f"No files specified. Searching recursively in: {current_dir}")
        input_paths = get_all_raw_files(current_dir)
    else:
        for f in args.files:
            if '*' in f:
                input_paths.extend(glob.glob(f, recursive=True))
            elif os.path.isdir(f):
                input_paths.extend(get_all_raw_files(f))
            else:
                input_paths.append(f)

    if not input_paths:
        print("No raw files found. Check your extensions or current folder.")
    else:
        print(f"Found {len(input_paths)} images. Starting Adobe DNG Conversion...")
        success_count = 0
        for f in input_paths:
            if convert_to_dng_adobe(f):
                success_count += 1
        
        print(f"\nFinished! Converted {success_count} of {len(input_paths)} files.")