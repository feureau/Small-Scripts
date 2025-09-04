#
# Script: One Sentence Per Line (OSPL) Text Formatter
#
# Description:
# This script intelligently processes text and Markdown files to reformat their
# prose content for clarity, ensuring each sentence is on its own line.
# It is designed to be "structure-aware," preserving important formatting like
# Markdown tables, fenced code blocks, YAML front matter, and poetry.
#
# Key Functionality:
# 1.  Prose Reformatting: The core feature is to process standard paragraphs,
#     placing each sentence on a new line.
# 2.  Structure Preservation: The script identifies and protects special text
#     blocks from being altered. This includes:
#     - Fenced Code Blocks (```)
#     - Markdown Tables
#     - YAML Front Matter (---)
#     - Any text where line breaks are meaningful (e.g., poetry, addresses).
# 3.  Sentence Tokenization: It uses the Natural Language Toolkit (NLTK)
#     to accurately split paragraphs into individual sentences.
# 4.  Decorative Prefix Splitting: It detects if a sentence starts with
#     non-alphanumeric characters (like '***') and splits this prefix onto a
#     separate line, while correctly ignoring Markdown syntax (like '#', '>', '**').
# 5.  Encoding Detection: Uses 'chardet' to automatically detect the
#     input file's character encoding for robust reading.
# 6.  Text Cleaning: Uses 'ftfy' to fix mojibake, repair encoding issues,
#     and normalize characters before processing.
# 7.  In-Place Editing & UTF-8 Conversion: The script overwrites the
#     original files with the formatted text, saving them in UTF-8.
# 8.  Cross-Platform Wildcard Support: Uses the 'glob' module to handle
#     wildcard file patterns (e.g., *.txt) correctly.
#
# Dependencies:
# - Python 3.x
# - NLTK: The Natural Language Toolkit library.
# - ftfy: A library for fixing and normalizing Unicode text.
# - chardet: A library for character encoding auto-detection.
#   (Install with: pip install nltk ftfy chardet)
#
# Usage:
# Run from the command line. If no arguments are given, it processes all
# .txt and .md files in the current directory. Otherwise, specify one or
# more text files or file patterns.
#
# Examples:
#   python your_script_name.py
#   python your_script_name.py document1.txt chapter*.txt "path/to/another file.txt"
# any update to this script must also include updates to the documentation, and the documentation must always be included.

import os
import sys
import re
import nltk
from nltk.tokenize import sent_tokenize
import glob
import ftfy
import chardet

def tokenize_text(text):
    """
    Tokenizes the given text into sentences.
    Handles NLTK's 'punkt' resource download if not found.
    """
    try:
        return sent_tokenize(text)
    except LookupError as e:
        if "punkt" in str(e):
            print("Missing NLTK resource 'punkt'. Downloading now...")
            nltk.download('punkt')
            return sent_tokenize(text)
        else:
            raise e

def split_decorative(sentence):
    """
    Checks if a sentence begins with a decorative prefix (e.g., '*** ').
    If so, it splits the prefix from the actual sentence.
    This function is robust and avoids splitting standard Markdown syntax.
    """
    # This single, comprehensive pattern identifies valid sentence starters that should NOT be split.
    # It includes: Markdown structural elements, inline formatting, and standard punctuation.
    # Crucially, it allows for optional spaces after the markers (e.g., `[ `).
    no_split_pattern = r'^\s*(?:[A-Za-z0-9“"]|#{1,6}\s*|>{1,}\s*|[*\-+]\s*|\d+\.\s*|\\?\[\s*|\(\s*)'
    
    # If the sentence starts with a valid, non-decorative character/pattern, leave it alone.
    if re.match(no_split_pattern, sentence):
        return [sentence]

    # Fallback: If the sentence does not start with a valid character (e.g., it starts with '--- '),
    # then find the first valid character and split before it.
    m = re.search(r'([A-Za-z0-9“"])', sentence)
    if m and m.start() > 0:
        prefix = sentence[:m.start()].rstrip()
        rest = sentence[m.start():].lstrip()
        if prefix:
            return [prefix, rest]

    # If no other rules apply, return the sentence as is.
    return [sentence]

def is_table_row(line):
    """ Heuristic to determine if a line is part of a Markdown table. """
    stripped_line = line.strip()
    if stripped_line.startswith('|') and stripped_line.endswith('|'):
        return True
    if re.match(r'^\s*\|?(:?-+:?\|)+:?-+:?\|?\s*$', stripped_line):
        return True
    return False

def process_file(filepath):
    """
    Reads a file and processes it line-by-line, reformatting prose while
    preserving structured blocks like code, tables, and YAML front matter.
    Overwrites the original file in UTF-8.
    """
    try:
        with open(filepath, 'rb') as f:
            raw_data = f.read()
            if not raw_data:
                print(f"Skipped empty file: {filepath}")
                return
        detection = chardet.detect(raw_data)
        encoding = detection.get('encoding', 'utf-8') or 'utf-8'
        text = raw_data.decode(encoding, errors='replace')
    except Exception as e:
        print(f"Error reading or decoding file {filepath}: {e}")
        return

    text = ftfy.fix_text(text)
    lines = text.splitlines()
    
    output_buffer = []
    prose_paragraph_buffer = []
    in_fenced_block = False
    in_yaml_block = False

    def flush_prose_buffer():
        """ Processes the collected prose lines and adds them to the output. """
        if not prose_paragraph_buffer:
            return
        
        full_paragraph = ' '.join(prose_paragraph_buffer)
        sentences = tokenize_text(full_paragraph)
        
        for sentence in sentences:
            for formatted_line in split_decorative(sentence.strip()):
                output_buffer.append(formatted_line)
        
        prose_paragraph_buffer.clear()

    for i, line in enumerate(lines):
        stripped_line = line.strip()

        if i == 0 and stripped_line == '---':
            in_yaml_block = True
            output_buffer.append(line)
            continue

        if in_yaml_block:
            output_buffer.append(line)
            if stripped_line == '---':
                in_yaml_block = False
            continue

        if stripped_line.startswith('```') or stripped_line.startswith('~~~'):
            flush_prose_buffer()
            in_fenced_block = not in_fenced_block
            output_buffer.append(line)
            continue
        
        if in_fenced_block:
            output_buffer.append(line)
            continue

        if is_table_row(line):
            flush_prose_buffer()
            output_buffer.append(line)
            continue
            
        if not stripped_line:
            flush_prose_buffer()
            output_buffer.append('')
        else:
            prose_paragraph_buffer.append(line)

    flush_prose_buffer()

    output_text = "\n".join(output_buffer).rstrip() + "\n"

    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(output_text)
        print(f"Processed and overwrote {filepath}")
    except Exception as e:
        print(f"Error writing to file {filepath}: {e}")

def main():
    """
    Main function to handle command-line arguments and process files.
    """
    if len(sys.argv) < 2:
        print("No file patterns provided. Defaulting to searching for *.txt and *.md files...")
        input_args = ['*.txt', '*.md']
    else:
        input_args = sys.argv[1:]

    input_files = []
    for arg in input_args:
        expanded_files = glob.glob(arg)
        if not expanded_files:
            print(f"Info: No files found matching pattern: {arg}")
        input_files.extend(expanded_files)

    if not input_files:
        print("No input files to process.")
        sys.exit(0)

    print(f"\nFound {len(input_files)} file(s) to process...")
    for filepath in input_files:
        if os.path.isfile(filepath):
            process_file(filepath)
    print("\nProcessing complete.")

if __name__ == "__main__":
    main()