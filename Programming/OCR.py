#!/usr/bin/env python3
import argparse
import easyocr
import sys
import glob
import logging
from pathlib import Path
from PIL import Image
import numpy as np

# Silence verbose EasyOCR logs
logging.getLogger('easyocr').setLevel(logging.ERROR)

def get_unique_path(base_path):
    """Returns base_path if it doesn't exist, otherwise appends ' 1', ' 2', etc."""
    if not base_path.exists():
        return base_path
    
    parent = base_path.parent
    name = base_path.name
    counter = 1
    while True:
        target = parent / f"{name} {counter}"
        if not target.exists():
            return target
        counter += 1

def process_images(input_patterns, output_folder=None, threshold=0.4, use_lines_mode=False):
    print("Loading EasyOCR model... (this may take a moment)")
    
    # Auto-detect GPU
    try:
        import torch
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f"Running on: {device.upper()}")
    except ImportError:
        device = 'cpu'

    try:
        reader = easyocr.Reader(['en'], gpu=(device=='cuda'))
    except Exception as e:
        print(f"Error loading EasyOCR: {e}")
        sys.exit(1)

    # Setup Output Path Logic
    # We determine the final path per parent folder to support incremental naming
    if output_folder:
        global_out_path = get_unique_path(Path(output_folder))
        global_out_path.mkdir(parents=True, exist_ok=True)
    else:
        global_out_path = None
    
    folder_cache = {}

    # Expand Wildcards
    files_to_process = []
    for pattern in input_patterns:
        expanded = glob.glob(pattern)
        files_to_process.extend(expanded)
    files_to_process = sorted(list(set(files_to_process)))

    if not files_to_process:
        print("No files to process.")
        sys.exit()

    mode_name = "RAW LINES" if use_lines_mode else "PARAGRAPH"
    print(f"Found {len(files_to_process)} file(s). Mode: {mode_name}")
    
    for file_path in files_to_process:
        p = Path(file_path)
        if not p.exists() or not p.is_file():
            continue

        print(f"Processing: {p.name}...", end='\r')
        
        # Determine output path
        if global_out_path:
            current_out_path = global_out_path
        else:
            parent_dir = p.parent
            if parent_dir not in folder_cache:
                unique_path = get_unique_path(parent_dir / "OCR")
                unique_path.mkdir(parents=True, exist_ok=True)
                folder_cache[parent_dir] = unique_path
            current_out_path = folder_cache[parent_dir]
        
        try:
            full_text = ""
            
            # Load image with PIL to support more formats (including complex TIFFs)
            # Convert to RGB to ensure consistency for EasyOCR
            with Image.open(p) as img:
                img_input = np.array(img.convert('RGB'))

            # --- MODE 1: RAW LINES (Opt-in via --lines) ---
            # Good for receipts, lists, and strict 'gibberish' filtering
            if use_lines_mode:
                # detail=1 returns [box, text, confidence]
                result = reader.readtext(img_input, detail=1, paragraph=False)
                
                valid_lines = []
                for (box, text, conf) in result:
                    if conf > threshold:
                        valid_lines.append(text)
                full_text = "\n".join(valid_lines)

            # --- MODE 2: PARAGRAPH (Default) ---
            # Good for books, articles, documents. 
            # Note: EasyOCR's paragraph mode handles merging internally, 
            # so individual line confidence scores are not available for filtering.
            else:
                result = reader.readtext(img_input, detail=1, paragraph=True)
                # result format is [[box, text], [box, text]]
                text_blocks = []
                for (box, text) in result:
                    text_blocks.append(text)
                full_text = "\n\n".join(text_blocks)

            # Save
            output_file = current_out_path / f"{p.stem}.txt"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(full_text)
                
            print(f"Done: {p.name} -> {output_file.name}      ")
            
        except Exception as e:
            print(f"\nFailed to process {p.name}: {e}")

    print("\nAll tasks completed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch OCR with default Paragraph formatting.")
    
    parser.add_argument('input', nargs='+', help='Input images (e.g. *.jpg)')
    parser.add_argument('-f', '--folder', type=str, help='Output folder')
    
    # CHANGED: Added -l/--lines flag. 
    # The script now DEFAULTS to Paragraph mode. 
    # Use --lines to go back to raw line output + confidence filtering.
    parser.add_argument('-l', '--lines', action='store_true', 
                        help='Switch to line-by-line mode. (Disables paragraph merging, but enables strict gibberish filtering via --confidence).')

    parser.add_argument('-c', '--confidence', type=float, default=0.4, 
                        help='Confidence threshold (Only works in --lines mode). Default: 0.4')

    args = parser.parse_args()
    
    # We pass 'args.lines' to decide the mode
    process_images(args.input, args.folder, args.confidence, args.lines)