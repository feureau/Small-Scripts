#!/usr/bin/env python3

import sys
import os
import argparse
import glob # Import the glob module

# --- Chunking Configuration ---
DEFAULT_CHUNK_SIZE_WORDS = 4500  # Default target chunk size in words
OUTPUT_SUBFOLDER_PREFIX = "chunked_output"  # Prefix for the output subfolder

def chunk_text_into_paragraphs(text):
    """Splits text into paragraphs, attempting to preserve paragraph structure."""
    return text.split("\n\n")

def chunk_paragraphs_into_segments(paragraphs, chunk_size_words):
    """
    Chunks paragraphs into segments of approximately chunk_size_words,
    WITHOUT overlap.
    """
    segments = []
    current_segment_words = []
    current_segment_paragraphs = []

    for paragraph in paragraphs:
        words = paragraph.split()
        paragraph_word_count = len(words)

        if not current_segment_words:
            current_segment_words.extend(words)
            current_segment_paragraphs.append(paragraph)
        elif len(current_segment_words) + paragraph_word_count <= chunk_size_words:
            current_segment_words.extend(words)
            current_segment_paragraphs.append(paragraph)
        else:
            segments.append("\n\n".join(current_segment_paragraphs))
            current_segment_words = words
            current_segment_paragraphs = [paragraph]

    if current_segment_paragraphs:
        segments.append("\n\n".join(current_segment_paragraphs))

    return segments

def main():
    parser = argparse.ArgumentParser(description="Batch chunk text files into paragraph-based segments (NO OVERLAP). Chunks for each file are saved to individual subfolders named with a suffix from the original filename.")
    parser.add_argument("input_files", nargs='+', help="Path to one or more input text files or wildcard patterns. You can provide multiple paths/patterns.") # Updated help text
    parser.add_argument("-c", "--chunk_size", type=int, default=DEFAULT_CHUNK_SIZE_WORDS, help=f"Target chunk size in words (default: {DEFAULT_CHUNK_SIZE_WORDS})")

    args = parser.parse_args()

    input_file_patterns = args.input_files # Renamed to input_file_patterns to reflect it can be patterns
    chunk_size = args.chunk_size

    files_to_process = []
    for pattern in input_file_patterns:
        found_files = glob.glob(pattern) # Use glob.glob to expand wildcard patterns
        if found_files:
            files_to_process.extend(found_files) # Add found files to the list
        elif os.path.isfile(pattern): # If glob returns empty and it's a file, add it (for single file input)
            files_to_process.append(pattern)
        else:
            print(f"Warning: No files found matching pattern '{pattern}'", file=sys.stderr) # Warn if no files found for a pattern

    if not files_to_process:
        print("Error: No input files specified or found.", file=sys.stderr)
        sys.exit(1)


    for input_file_path in files_to_process: # Loop through the expanded list of files
        try:
            with open(input_file_path, "r", encoding="utf-8") as infile:
                text_content = infile.read()

            paragraphs = chunk_text_into_paragraphs(text_content)
            segments = chunk_paragraphs_into_segments(paragraphs, chunk_size)

            base_name = os.path.basename(input_file_path)
            name, ext = os.path.splitext(base_name)
            output_dir = f"{OUTPUT_SUBFOLDER_PREFIX}_{chunk_size}_{name}" # Output subfolder name with filename suffix

            os.makedirs(output_dir, exist_ok=True)


            for i, segment in enumerate(segments):
                output_filename = os.path.join(output_dir, f"{name}_chunk_{i+1}{ext}")
                with open(output_filename, "w", encoding="utf-8") as outfile:
                    outfile.write(segment)
                print(f"Chunk {i+1} saved to: {output_filename}")
            print(f"Total {len(segments)} chunks for '{input_file_path}' saved to '{output_dir}'") # Added filename to summary

        except FileNotFoundError:
            print(f"Error: Input file not found: {input_file_path}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error processing file '{input_file_path}': {e}", file=sys.stderr) # Added filename to error
            sys.exit(1)

if __name__ == "__main__":
    main()