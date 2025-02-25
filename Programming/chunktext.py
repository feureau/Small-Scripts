#!/usr/bin/env python3

import sys
import os
import argparse
import glob
import re

DEFAULT_CHUNK_SIZE_WORDS = 4500
OUTPUT_SUBFOLDER_PREFIX = "chunked_output"

FRENCH_MONTHS = {
    "janvier", "février", "fevrier", "mars", "avril", "mai", "juin",
    "juillet", "août", "aoust", "septembre", "octobre", "novembre", "décembre"
}

def chunk_text_into_paragraphs(text):
    """Enhanced date detection with ordinal support and alternate spellings"""
    paragraphs = []
    current_paragraph = []
    
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        
        # Extract potential date components
        parts = line.split(maxsplit=2)
        if len(parts) >= 2:
            # Handle ordinal indicators (1er, 2e, etc.)
            day_part = re.sub(r"\D", "", parts[0])  # Extract digits only
            month_part = parts[1].lower().rstrip(',.:;')
            
            # Check for valid day (1-31) and French month
            if day_part.isdigit() and 1 <= int(day_part) <= 31 and month_part in FRENCH_MONTHS:
                if current_paragraph:
                    paragraphs.append("\n".join(current_paragraph))
                    current_paragraph = []
        
        current_paragraph.append(line)
    
    if current_paragraph:
        paragraphs.append("\n".join(current_paragraph))
    
    return paragraphs

def chunk_paragraphs_into_segments(paragraphs, chunk_size_words):
    segments = []
    current_segment = []
    current_word_count = 0

    for para in paragraphs:
        word_count = len(para.split())
        
        if current_word_count + word_count > chunk_size_words and current_segment:
            segments.append("\n\n".join(current_segment))
            current_segment = [para]
            current_word_count = word_count
        else:
            current_segment.append(para)
            current_word_count += word_count

    if current_segment:
        segments.append("\n\n".join(current_segment))

    return segments

def main():
    parser = argparse.ArgumentParser(description="Chunk historical journals with robust date detection")
    parser.add_argument("input_files", nargs='+', help="Input files/patterns")
    parser.add_argument("-c", "--chunk_size", type=int, default=DEFAULT_CHUNK_SIZE_WORDS,
                      help=f"Target chunk size in words (default: {DEFAULT_CHUNK_SIZE_WORDS})")

    args = parser.parse_args()

    files_to_process = []
    for pattern in args.input_files:
        found_files = glob.glob(pattern)
        if found_files:
            files_to_process.extend(found_files)
        else:
            print(f"Warning: No matches for pattern '{pattern}'", file=sys.stderr)

    if not files_to_process:
        print("Error: No valid input files found", file=sys.stderr)
        sys.exit(1)

    for input_file in files_to_process:
        try:
            with open(input_file, "r", encoding='utf-8') as f:
                content = f.read()

            paragraphs = chunk_text_into_paragraphs(content)
            segments = chunk_paragraphs_into_segments(paragraphs, args.chunk_size)

            base_name = os.path.basename(input_file)
            name, ext = os.path.splitext(base_name)
            output_dir = f"{OUTPUT_SUBFOLDER_PREFIX}_{args.chunk_size}_{name}"
            os.makedirs(output_dir, exist_ok=True)

            for i, segment in enumerate(segments, 1):
                output_path = os.path.join(output_dir, f"{name}_chunk_{i}{ext}")
                with open(output_path, "w", encoding='utf-8') as f:
                    f.write(segment)
                print(f"Created: {output_path}")

            print(f"\nFile: {input_file}")
            print(f"Total paragraphs detected: {len(paragraphs)}")
            print(f"Total chunks created: {len(segments)}")
            print(f"Average words per chunk: {sum(len(s.split()) for s in segments)//len(segments) if segments else 0}\n")

        except Exception as e:
            print(f"\nERROR processing {input_file}: {str(e)}", file=sys.stderr)

if __name__ == "__main__":
    main()
