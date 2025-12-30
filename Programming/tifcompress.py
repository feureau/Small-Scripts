"""
# TIFF Compressor

A Python script to losslessly compress TIFF files using the Deflate algorithm. 
It supports recursive directory scanning and multiple output strategies.

## Maintenance Rule
> [!IMPORTANT]
> This documentation block MUST be included and updated with every revision or update of the script.

## Technical Structure & Rationale

### 1. Global Configuration
- Settings like `DEFAULT_COMPRESSION` and `ALLOWED_EXTENSIONS` are placed at the top for easy 
  customization without modifying the functional code.

### 2. Argument Parsing (`argparse`)
- Provides a robust CLI with a "path" argument and mutually exclusive output modes.
- If no mode (`--overwrite`, `-p`, `--subfolder`) is provided, the script intelligently fallbacks 
  to `--overwrite` during processing logic rather than erroring out, making it more user-friendly.

### 3. File Discovery (`os.walk`)
- Recursively traverses directories. Using `os.walk` is standard for cross-platform 
  file tree traversal and handles large numbers of files efficiently.

### 4. Image Processing (`Pillow`)
- Uses the `Pillow` library specifically for its robust TIFF support.
- `tiff_deflate` (Adobe Deflate) is used as it provides the most efficient lossless 
  compression for standard 8-bit images.
- DPI preservation is handled by extracting info from the source image object.

### 5. Extreme Verbosity & Reporting
- Detailed logging for every file including full absolute paths, image metadata (dimensions, 
  mode, DPI), compression parameters, precise size changes, and processing time.
- A final summary provides aggregate statistics for the entire batch.

## Features
- **Lossless Compression**: Adobe Deflate (Zip) for maximum space saving.
- **Recursive Scanning**: Finds all TIFF files in the CWD/subfolders by default.
- **Output Modes**: Overwrite (default), Pool, or Subfolder.
- **Metadata**: Maintains original DPI attributes.

## Usage
```powershell
# Default (Recurse CWD + Overwrite)
python tifcompress.py

# Specify path (Defaults to Overwrite)
python tifcompress.py C:\\path\\to\\images

# Pool to folder
python tifcompress.py -p C:\\output_folder
```

## Requirements
- Python 3.x
- Pillow library (`pip install Pillow`)
"""

import os
import argparse
import sys
import time
from PIL import Image
from pathlib import Path

# ==========================================
# GLOBAL CONFIGURATION
# ==========================================
DEFAULT_COMPRESSION = "tiff_deflate"  # Options: tiff_lzw, tiff_deflate, packbits
ALLOWED_EXTENSIONS = (".tif", ".tiff")
VERBOSE_OUTPUT = True
# ==========================================

def get_size_format(b, factor=1024, suffix="B"):
    """Scale bytes to its proper format (K, M, G, etc)"""
    for unit in ["", "K", "M", "G", "T", "P"]:
        if b < factor:
            return f"{b:.2f} {unit}{suffix}"
        b /= factor

def compress_tif(input_path, output_path, dry_run=False):
    """
    Compresses a single TIFF file using the configured lossless algorithm.
    Logs extensive details about the process, metadata, and results.
    """
    start_time = time.time()
    input_abs = input_path.resolve()
    output_abs = output_path.resolve()
    original_size = os.path.getsize(input_abs)
    
    print(f"\n[•] TARGET FILE: {input_abs.name}")
    print(f"    Source: {input_abs.parent}")
    print(f"    Output: {output_abs}")
    
    if dry_run:
        print(f"    [DRY-RUN] No changes will be made.")
        return True, 0, 0
    
    try:
        with Image.open(input_abs) as img:
            width, height = img.size
            mode = img.mode
            dpi = img.info.get('dpi')
            compression_used = img.info.get('compression', 'unknown')
            
            print(f"    Metadata:")
            print(f"      - Dimensions: {width} x {height} pixels")
            print(f"      - Color Mode: {mode}")
            print(f"      - Source DPI: {dpi}")
            print(f"      - Source Comp: {compression_used}")
            print(f"      - Comp Goal:   {DEFAULT_COMPRESSION}")
            
            # Ensure output directory exists (needed for subfolder/pool modes)
            os.makedirs(output_abs.parent, exist_ok=True)
            
            # Perform saving with compression
            img.save(output_abs, compression=DEFAULT_COMPRESSION, dpi=dpi)
            
            # Calculate results
            new_size = os.path.getsize(output_abs)
            saved_bytes = original_size - new_size
            reduction_pct = (saved_bytes / original_size * 100) if original_size > 0 else 0
            
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"    Results:")
            print(f"      - Original Size: {get_size_format(original_size)} ({original_size} bytes)")
            print(f"      - Output Size:   {get_size_format(new_size)} ({new_size} bytes)")
            print(f"      - Net Savings:   {get_size_format(saved_bytes)} ({reduction_pct:.2f}%)")
            print(f"      - Duration:      {duration:.3f} seconds")
            
            return True, original_size, new_size
    except Exception as e:
        print(f"    [ERROR] Failed to process {input_path.name}: {e}")
        return False, 0, 0

def main():
    parser = argparse.ArgumentParser(
        description="Losslessly compress TIFF files recursively. Defaults to overwriting if no mode is specified.",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("path", nargs="?", default=".", help="File or directory to process (default: current directory)")
    
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--overwrite", action="store_true", help="Overwrite the original files (default)")
    group.add_argument("-p", "--pool", help="Output directory to pool all results")
    group.add_argument("--subfolder", help="Name of subfolder in each source directory for output")
    
    parser.add_argument("--dry-run", action="store_true", help="Log paths without performing compression")

    args = parser.parse_args()

    # Path Resolution
    input_base = Path(args.path).resolve()
    if not input_base.exists():
        print(f"Error: Path '{input_base}' does not exist.")
        sys.exit(1)

    # Determine Output Mode
    selected_mode = "overwrite"
    if args.pool:
        selected_mode = "pool"
    elif args.subfolder:
        selected_mode = "subfolder"
    elif args.overwrite:
        selected_mode = "overwrite"

    # File Discovery
    files_to_process = []
    if input_base.is_file():
        if input_base.suffix.lower() in ALLOWED_EXTENSIONS:
            files_to_process.append(input_base)
    else:
        for root, _, files in os.walk(input_base):
            for f in files:
                if f.lower().endswith(ALLOWED_EXTENSIONS):
                    files_to_process.append(Path(root) / f)

    if not files_to_process:
        print(f"No TIFF files found in {input_base}")
        return

    print("=" * 60)
    print(f"TIFF COMPRESSION WORKFLOW")
    print("-" * 60)
    print(f"Target Path: {input_base}")
    print(f"Strategy:    {selected_mode}")
    print(f"Files Found: {len(files_to_process)}")
    print("=" * 60)

    total_start = time.time()
    success_count = 0
    total_original = 0
    total_new = 0

    for f_path in files_to_process:
        # Calculate Output Path based on mode
        if selected_mode == "overwrite":
            out_path = f_path
        elif selected_mode == "pool":
            out_path = Path(args.pool).resolve() / f_path.name
        elif selected_mode == "subfolder":
            out_path = f_path.parent / args.subfolder / f_path.name
            
        success, o_size, n_size = compress_tif(f_path, out_path, dry_run=args.dry_run)
        if success:
            success_count += 1
            total_original += o_size
            total_new += n_size

    total_duration = time.time() - total_start
    total_saved = total_original - total_new
    total_reduction = (total_saved / total_original * 100) if total_original > 0 else 0

    print("\n" + "=" * 60)
    print(f"BATCH SUMMARY")
    print("-" * 60)
    print(f"Status:          {success_count} / {len(files_to_process)} successful")
    print(f"Total Original:  {get_size_format(total_original)}")
    print(f"Total Output:    {get_size_format(total_new)}")
    print(f"Total Saved:     {get_size_format(total_saved)} ({total_reduction:.2f}% reduction)")
    print(f"Total Time:      {total_duration:.2f} seconds")
    print("=" * 60)

if __name__ == "__main__":
    main()
