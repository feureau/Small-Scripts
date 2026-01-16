#!/usr/bin/env python3
#
# Script: Text Processor - SRT Cleaner & OSPL Formatter
#
# Description:
# This script combines two text processing tools:
# 1. SRT Cleaner: Removes timestamps and line numbers from subtitle files
# 2. OSPL Formatter: Reformats text files to have one sentence per line
#
# Key Functionality:
# For SRT files:
# - Removes timestamp lines and line number lines
# - Reconstructs complete sentences from fragmented subtitles
# - Saves as clean text files
#
# For text files:
# - Ensures each sentence is on its own line
# - Preserves paragraph breaks
# - Normalizes line breaks within paragraphs
# - Splits decorative prefixes from sentences
#
# Dependencies:
# - Python 3.x
# - NLTK: The Natural Language Toolkit library (for text formatting)
#
# Usage:
# Run from the command line with file patterns or let it auto-detect files
#
# Examples:
#   python text_processor.py
#   python text_processor.py *.srt *.txt
#   python text_processor.py subtitles/*.srt documents/*.txt -s
#

import re
import sys
import glob
from pathlib import Path
import argparse
import nltk
from nltk.tokenize import sent_tokenize

def reconstruct_srt_text(input_file, output_file):
    """
    Reads an SRT file, removes timestamp lines and line number lines,
    reconstructs complete sentences from fragmented subtitles,
    and writes the clean text to an output file.
    """
    timestamp_pattern = re.compile(r'^\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}$')
    line_number_pattern = re.compile(r'^\d+$')

    subtitle_texts = []
    
    # Read all subtitle content first
    with open(input_file, 'r', encoding='utf-8') as infile:
        for line in infile:
            line = line.strip()
            # Skip timestamps, line numbers, and empty lines
            if not timestamp_pattern.match(line) and not line_number_pattern.match(line) and line != '':
                subtitle_texts.append(line)
    
    # Join subtitle fragments and reconstruct sentences
    reconstructed_text = reconstruct_sentences_from_fragments(subtitle_texts)
    
    # Write the reconstructed text
    with open(output_file, 'w', encoding='utf-8') as outfile:
        outfile.write(reconstructed_text)

def reconstruct_sentences_from_fragments(fragments):
    """
    Attempts to reconstruct complete sentences from subtitle fragments.
    """
    if not fragments:
        return ""
    
    # Join all fragments with spaces
    combined_text = " ".join(fragments)
    
    # Try to use NLTK to properly split into sentences
    try:
        sentences = sent_tokenize(combined_text)
        return "\n".join(sentences) + "\n" if sentences else ""
    except:
        # Fallback: if NLTK fails, just return the combined text
        # You might want to add more sophisticated logic here
        return combined_text + "\n"

def tokenize_text(text):
    """
    Tokenizes the given text into sentences.
    Handles NLTK's 'punkt' resource download if not found.
    """
    try:
        return sent_tokenize(text)
    except LookupError as e:
        # Check if the error is due to the missing 'punkt' resource.
        if "punkt" in str(e):
            print("Missing NLTK resource 'punkt'. Downloading now...")
            nltk.download('punkt')
            # Retry tokenizing after downloading.
            return sent_tokenize(text)
        else:
            # Re-raise other lookup errors.
            raise e

def split_decorative(sentence):
    """
    Checks if the sentence begins with extra decorative text.
    If so, splits the sentence into two parts:
      1. The extra text (e.g. asterisks or other non-sentence characters).
      2. The actual sentence starting with an alphanumeric character or a typical opening quote.
    If no such decorative prefix is found, returns the sentence as a single-item list.
    """
    # Look for the first occurrence of an alphanumeric character or a common opening quote.
    m = re.search(r'([A-Za-z“"])', sentence)
    if m and m.start() > 0:
        prefix = sentence[:m.start()].rstrip()
        rest = sentence[m.start():].lstrip()
        # Only split if there is a non-empty prefix.
        if prefix:
            return [prefix, rest]
    return [sentence]

def format_text_file(filepath):
    """
    Reads a text file, processes its content to put one sentence per line,
    and overwrites the original file with the result.
    """
    # Read the file using UTF-8 encoding
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()

    # Split text into paragraphs based on one or more blank lines.
    paragraphs = re.split(r'\n\s*\n', text.strip())

    processed_paragraphs = []
    for para in paragraphs:
        # Join broken lines within the paragraph (assuming soft line breaks) with a space.
        single_line_para = ' '.join(para.splitlines())
        # Tokenize the paragraph into sentences.
        sentences = tokenize_text(single_line_para)
        processed_lines = []
        for sentence in sentences:
            # Split the tokenized sentence if there is a decorative prefix.
            for line in split_decorative(sentence):
                # Append each part on its own line
                processed_lines.append(line)
        # Join processed sentences with a newline for the paragraph.
        processed_paragraphs.append("\n".join(processed_lines))

    # Rejoin paragraphs with two newlines to preserve paragraph breaks.
    output_text = "\n\n".join(processed_paragraphs)

    # Write the processed text back to the original file, overwriting it.
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(output_text)
    print(f"Formatted text file: {filepath}")

def process_srt_file(input_path, output_file_path):
    """
    Process an SRT file and create a clean text file.
    """
    print(f"Processing SRT: {input_path} -> {output_file_path}")
    try:
        reconstruct_srt_text(input_path, output_file_path)
        print(f"Successfully processed SRT: {output_file_path}")
        return True
    except Exception as e:
        print(f"Error processing SRT {input_path}: {e}")
        return False

def process_text_file(filepath):
    """
    Process a text file for sentence formatting.
    """
    print(f"Formatting text file: {filepath}")
    try:
        format_text_file(filepath)
        print(f"Successfully formatted: {filepath}")
        return True
    except Exception as e:
        print(f"Error formatting {filepath}: {e}")
        return False

def main():
    """
    Main function to handle command-line arguments and process files.
    """
    parser = argparse.ArgumentParser(
        description="Process SRT subtitle files and text files. Cleans SRT files and formats text files with one sentence per line.",
        epilog="Example: text_processor.py *.srt *.txt -s --output-ext .txt"
    )
    parser.add_argument(
        'files',
        nargs='*', # 0 or more file arguments
        help="One or more files to process. Supports wildcards (e.g., *.srt, *.txt)."
    )
    parser.add_argument(
        '-s', '--subfolder',
        action='store_true', # This is a flag
        help="Place SRT output files in a 'no_timestamps' subfolder."
    )
    parser.add_argument(
        '--skip-text-formatting',
        action='store_true',
        help="Skip the sentence-per-line formatting for text files."
    )
    parser.add_argument(
        '--output-ext',
        default='.md',
        help="Specify the output file extension for SRT files (default: .md)"
    )
    args = parser.parse_args()

    # Ensure output extension starts with a dot
    if not args.output_ext.startswith('.'):
        args.output_ext = '.' + args.output_ext

    input_files = args.files
    
    # If no files were passed as arguments, glob for .srt and .txt files in the current directory.
    if not input_files:
        print("No input files provided. Searching for .srt and .txt files in the current directory...")
        input_files = glob.glob('*.srt') + glob.glob('*.txt') + glob.glob('*.md')

    file_paths = []
    # Expand wildcards from arguments, if any.
    for arg in input_files:
        # Use glob to handle potential wildcards (*, ?) in filenames
        if '*' in arg or '?' in arg:
            expanded = glob.glob(arg)
            file_paths.extend(expanded)
        else:
            file_paths.append(arg)
    
    if not file_paths:
        print("No valid files found.")
        sys.exit(1)

    srt_processed = 0
    text_processed = 0
    errors = 0

    for input_path in file_paths:
        input_file = Path(input_path)

        # Check if the path is a file and exists
        if not input_file.is_file():
            print(f"Skipping invalid file: {input_path} (Does not exist)")
            errors += 1
            continue

        # Process based on file extension
        suffix = input_file.suffix.lower()
        
        if suffix == '.srt':
            # Handle SRT files
            # Determine the output path based on the --subfolder flag
            if args.subfolder:
                # Define the output folder path
                output_folder = input_file.parent / "no_timestamps"
                # Create the output folder if it doesn't exist
                output_folder.mkdir(exist_ok=True)
                output_file_path = output_folder / f"{input_file.stem}_no_timestamps{args.output_ext}"
            else:
                # Place output in the same directory as the input file
                output_file_path = input_file.parent / f"{input_file.stem}_no_timestamps{args.output_ext}"

            if process_srt_file(input_path, output_file_path):
                srt_processed += 1
            else:
                errors += 1
                
        elif suffix in ['.txt', '.md']:
            # Handle text files
            if not args.skip_text_formatting:
                if process_text_file(input_path):
                    text_processed += 1
                else:
                    errors += 1
            else:
                print(f"Skipped text formatting for: {input_path}")
        else:
            print(f"Skipping unsupported file type: {input_path} (Not SRT, TXT, or MD)")
            errors += 1

    # Summary
    print(f"\nProcessing complete!")
    print(f"SRT files processed: {srt_processed}")
    print(f"Text files formatted: {text_processed}")
    if errors > 0:
        print(f"Files with errors: {errors}")

if __name__ == "__main__":
    main()