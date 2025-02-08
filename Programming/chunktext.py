#!/usr/bin/env python3

import sys
import os
import argparse

# --- Chunking Configuration ---
DEFAULT_CHUNK_SIZE_WORDS = 500  # Default target chunk size in words
# Overlap is now DISABLED - removed DEFAULT_CHUNK_OVERLAP_WORDS

OUTPUT_SUBFOLDER_NAME = "chunked_output" # Subfolder to save chunk files

def chunk_text_into_paragraphs(text):
    """Splits text into paragraphs, attempting to preserve paragraph structure."""
    return text.split("\n\n") # Split by double newlines, common paragraph separator

def chunk_paragraphs_into_segments(paragraphs, chunk_size_words=DEFAULT_CHUNK_SIZE_WORDS): # Removed overlap_words parameter
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

        if not current_segment_words: # If segment is empty, start with the new paragraph
            current_segment_words.extend(words)
            current_segment_paragraphs.append(paragraph)
        elif len(current_segment_words) + paragraph_word_count <= chunk_size_words:
            # If paragraph fits within the chunk size, append it
            current_segment_words.extend(words)
            current_segment_paragraphs.append(paragraph)
        else:
            # Segment is full, finalize it and start a new one WITHOUT overlap
            segments.append("\n\n".join(current_segment_paragraphs)) # Join paragraphs with paragraph breaks for segment

            # Start a new segment WITHOUT overlap - just start with the current paragraph
            current_segment_words = words
            current_segment_paragraphs = [paragraph]


    # Add the last segment if it's not empty
    if current_segment_paragraphs:
        segments.append("\n\n".join(current_segment_paragraphs))

    return segments


def main():
    parser = argparse.ArgumentParser(description="Chunk a text file into paragraph-based segments for translation (NO OVERLAP). Chunks are saved to a subfolder.") # Updated description
    parser.add_argument("input_file", help="Path to the input text file.")
    parser.add_argument("--chunk_size", type=int, default=DEFAULT_CHUNK_SIZE_WORDS, help=f"Target chunk size in words (default: {DEFAULT_CHUNK_SIZE_WORDS})")
    # Removed --chunk_overlap argument as overlap is disabled

    args = parser.parse_args()

    input_file_path = args.input_file
    chunk_size = args.chunk_size
    # chunk_overlap is no longer used

    output_dir = OUTPUT_SUBFOLDER_NAME # Fixed output subfolder name

    try:
        with open(input_file_path, "r", encoding="utf-8") as infile:
            text_content = infile.read()

        paragraphs = chunk_text_into_paragraphs(text_content)
        segments = chunk_paragraphs_into_segments(paragraphs, chunk_size) # Removed overlap_words argument

        os.makedirs(output_dir, exist_ok=True) # Create output subfolder
        base_name = os.path.basename(input_file_path)
        name, ext = os.path.splitext(base_name)

        for i, segment in enumerate(segments):
            output_filename = os.path.join(output_dir, f"{name}_chunk_{i+1}{ext}")
            with open(output_filename, "w", encoding="utf-8") as outfile:
                outfile.write(segment)
            print(f"Chunk {i+1} saved to: {output_filename}")
        print(f"Total {len(segments)} chunks saved to '{output_dir}'")


    except FileNotFoundError:
        print(f"Error: Input file not found: {input_file_path}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error processing file: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()