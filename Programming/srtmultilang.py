#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import re
import argparse
from pathlib import Path

def parse_srt_content(content):
    """
    Parses a string content of an SRT file into a list of dictionaries.
    Each dictionary represents one subtitle block with start_time, end_time, and text.
    Time is converted to milliseconds for easier comparison.
    """
    subtitles = []
    
    # Split by empty lines to separate blocks
    raw_blocks = content.split('\n\n')
    
    for block in raw_blocks:
        lines = block.strip().split('\n')
        if not lines or len(lines) < 2:
            continue
            
        try:
            index_line = lines[0].strip()
            time_range = lines[1]
            text_lines = lines[2:]
            
            # Regex to match timestamp format HH:MM:SS,ms --> HH:MM:SS,ms
            time_match = re.match(r'(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})', time_range)
            
            if not time_match:
                continue
                
            start_str, end_str = time_match.groups()
            
            # Helper to convert "00:MM:SS,ms" to milliseconds (SRT format HH:MM:SS,ms)
            def str_to_ms(time_str):
                parts = time_str.split(':')
                hours = int(parts[0]) if len(parts) >= 1 else 0
                minutes = int(parts[1]) if len(parts) >= 2 else 0
                seconds_ms = parts[2] if len(parts) >= 3 else '0'
                if ',' in seconds_ms:
                    seconds, ms = seconds_ms.split(',')
                else:
                    seconds = seconds_ms
                    ms = '0'
                
                return (hours * 3600 + minutes * 60 + float(seconds)) * 1000 + int(ms)

            start_ms = str_to_ms(start_str)
            end_ms = str_to_ms(end_str)
            
            # Clean text (remove newlines, keep spaces within lines)
            text = " ".join([line.strip() for line in text_lines]) if text_lines else ""
            
            subtitles.append({
                'start_ms': start_ms,
                'end_ms': end_ms,
                'text': text
            })
        except Exception as e:
            # If parsing a specific block fails, skip it (don't crash the whole file)
            continue
            
    return subtitles

def merge_subtitles(input_files_list):
    """
    Merges multiple parsed subtitle lists into one multi-language subtitle.
    Returns a list of dictionaries with 'start_ms', 'end_ms' (max), and 'texts'.
    """
    
    # 1. Parse all input files
    parsed_data = [] 
    for file_path in input_files_list:
        try:
            fp = Path(file_path) if not isinstance(file_path, Path) else file_path
            
            with open(fp, 'r', encoding='utf-8') as f:
                content = f.read()
            subtitles = parse_srt_content(content)
            
            if not subtitles:
                continue
                
            # Store original text and source info separately for merging
            parsed_data.extend({
                'start_ms': subtitle['start_ms'],
                'end_ms': subtitle['end_ms'],
                'text': subtitle['text'],  # The actual text string
                'source_file': fp.name    # For debugging
            } for subtitle in subtitles)
        except FileNotFoundError:
            continue

    if not parsed_data:
        raise ValueError("No valid subtitle data found.")

    # 2. Group entries by START TIME match across all files (preserve exact end times)
    timestamp_groups = {}
    
    for item in parsed_data:
        key = round(item['start_ms'], -3)  # Only group by rounded start time
        if key not in timestamp_groups:
            timestamp_groups[key] = []
        
        # Store ALL necessary fields from original item including end_ms!
        timestamp_groups[key].append({
            'text': item['text'],
            'start_ms': item['start_ms'],  # Keep for sorting
            'end_ms': item['end_ms'],     # Keep for finding max!
            'source_file': item['source_file']
        })
    
    # Sort groups by start time for chronological order
    sorted_keys = sorted(timestamp_groups.keys())
    
    merged_output = []
    
    def finalize_group(key):
        """Save a merged subtitle block with texts sorted alphabetically by source file."""
        if not timestamp_groups[key]:
            return
        
        # Sort texts: main file (no language suffix) first, then others alphabetically by suffix (.cn before .id-vcd)
        def get_sort_key(item):
            filename = item['source_file']
            
            # Check for language code in the full filename path to find .cn, .kr, etc. suffixes
            all_parts = str(filename).split('.')
            
            # Look backwards from end to find a recognized language code
            has_lang = False
            lang_code = None
            
            for part in reversed(all_parts):
                if part.lower() in ['cn', 'kr', 'jp', 'tw', 'th', 'vi']:
                    if part == 'id':  # Special case for id-vcd / id-vdo format
                        has_lang = True
                        lang_code = 'id'
                    else:
                        has_lang = True
                        lang_code = part
                    break
            
            if not has_lang and len(all_parts) >= 3:
                # Check the second-to-last part (before .srt extension) for id-vcd pattern
                prefix_part = all_parts[-2]
                if 'vcd' in prefix_part.lower() or prefix_part == 'id':
                    has_lang = True
                    lang_code = prefix_part
            
            if has_lang:
                # Sort language files alphabetically by their suffix code
                return (1, f'{lang_code}')
            else:
                # Main file sorts first with empty tuple
                return (0, '')
        
        items = timestamp_groups[key]
        sorted_items = sorted(items, key=get_sort_key)
        
        merged_output.append({
            'start_ms': min(item['start_ms'] for item in items), 
            'end_ms': max(item['end_ms'] for item in items),
            'texts': [item['text'] for item in sorted_items]  # Extract just the text strings!
        })

    for key in sorted_keys:
        finalize_group(key)

    return merged_output

def format_time(ms):
    """Formats milliseconds back to SRT string 00:00:00,000"""
    hours = int(ms) // 3600000
    remaining = int(ms) % 3600000
    minutes = remaining // 60000
    seconds = (remaining % 60000) // 1000
    millis = remaining % 1000
    
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"

def write_srt(output_file, data):
    """Writes the merged data to a file."""
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            for i, block in enumerate(data, 1):
                start_str = format_time(block['start_ms'])
                end_str = format_time(block['end_ms'])
                
                f.write(f"{i}\n")
                f.write(f"{start_str} --> {end_str}\n")
                
                # Write each language's text on a new line
                for lang_text in block['texts']:
                    f.write(f"{lang_text.strip()}\n")
                
                f.write("\n") # Blank line between entries
        print(f"Success! Merged subtitles saved to: {output_file}")
    except Exception as e:
        print(f"Error writing file: {e}")

def main():
    parser = argparse.ArgumentParser(description="Merge multiple SRT files into one multi-language subtitle.")
    parser.add_argument("--input", "-i", nargs='+', help="Path(s) to input .srt files")
    parser.add_argument("--folder", "-f", help="Folder containing .srt files. Script will find all .srt in here.")
    parser.add_argument("--output", "-o", help="Name of the output merged file (e.g., merged.srt). If not specified, derived from first input file.")
    
    args = parser.parse_args()

    # Determine input sources
    input_files = []
    
    if args.input:
        for path in args.input:
            try:
                path_obj = Path(path)
                if path_obj.is_dir():
                    files = list(path_obj.rglob("*.srt"))
                elif path_obj.exists() and str(path_obj).lower().endswith('.srt'):
                    files = [path]
                else:
                    continue
                input_files.extend(files)
            except Exception as e:
                print(f"Warning: Could not process {path}: {e}")
    elif args.folder:
        # Find all .srt in the specified folder (rglob finds subdirectories too)
        p_folder = Path(args.folder).resolve()
        srt_files = list(p_folder.rglob("*.srt"))
        
        input_files.extend(srt_files)
    else:
        # Auto-detect: find all .srt files in current working directory (use rglob to include subdirectories)
        cwd = Path.cwd().resolve()
        srt_files = list(cwd.rglob("*.srt"))
        
        if srt_files:
            input_files.extend(srt_files)
        else:
            print("Error: No .srt files found in current directory.")
            sys.exit(1)

    # Filter out files that don't exist or aren't SRT files with content
    valid_files = []
    
    output_arg_str = str(args.output) if args.output else None
    
    # Exclude .multilang files (already merged outputs from previous runs)
    input_files = [fp for fp in input_files if '.multilang' not in Path(fp).stem]
    
    for fp in input_files:
        try:
            path = Path(fp) if not isinstance(fp, Path) else fp
            
            # Skip output file from current run (only if --output was provided)
            if output_arg_str and output_arg_str.lower().endswith('.srt'):
                if str(path).lower().endswith(output_arg_str):
                    continue
                    
            # Only process files that exist and are .srt files
            if not path.exists():
                continue
            if not path.is_file() or not str(path).lower().endswith('.srt'):
                continue
            
            valid_files.append(fp)
        except Exception as e:
            pass
    if not valid_files:
        print("No SRT files found to merge. Exiting.")
        sys.exit(1)
    
    input_paths = valid_files
    
    # Run Merge Logic
    merged_data = merge_subtitles(valid_files)
    
    # Determine output path
    if args.output:
        # User explicitly specified an output file
        if Path(args.output).is_absolute():
            output_path = Path(args.output)
        else:
            output_path = Path.cwd().joinpath(args.output)
    elif input_files:
        # Derive output filename from the main/original file
        # Prefer files without regional/language codes (.cn, .kr, .id-vcd, etc.)
        
        path_objects = []
        for fp in input_files:
            po = Path(fp) if not isinstance(fp, Path) else fp
            stem = po.stem.lower()
            
            # Check if this looks like a main/original file (no regional codes)
            is_main = all(
                code.lower() not in stem 
                for code in ['cn', 'kr', 'jp', 'tw', 'th', 'vi', 'id-vcd', 'id-vdo']
            )
            
            path_objects.append((fp, po, stem, is_main))
        
        # Sort: main files first, then by name within each group
        def sort_key(item):
            fp, po, stem, is_main = item
            return (0 if is_main else 1, str(po).lower())
        
        path_objects.sort(key=sort_key)
        
        # Use the first file as base
        if path_objects:
            _, base_file, _, _ = path_objects[0]
            
            # Handle different suffix patterns (e.g., .multilang.srt or just .srt)
            str_path = str(base_file).lower()
            if '.multilang' in str_path and '.srt' not in str_path:
                # Already has .multilang but no .srt - add .srt
                new_name = f"{base_file.stem}.multilang.srt"
            else:
                normal_stem = base_file.stem
                normal_suffix = base_file.suffix if base_file.suffix else '.srt'
                new_name = f"{normal_stem}.multilang{normal_suffix}"
            
            output_path = base_file.parent.joinpath(new_name)

    # Write the merged data to the determined output file
    write_srt(str(output_path), merged_data)

if __name__ == "__main__":
    main()
