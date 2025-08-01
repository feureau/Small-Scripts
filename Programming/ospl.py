#
# Script: One Sentence Per Line (OSPL) Text Formatter
#
# Description:
# This script processes one or more text files to reformat their content
# for clarity and easier processing by other tools. It standardizes the
# text by ensuring each sentence is on its own line and by separating
# any decorative or non-textual prefixes from the sentences.
#
# Key Functionality:
# 1.  Encoding Detection: Uses the 'chardet' library to automatically
#     detect the input file's character encoding for robust reading.
# 2.  Text Cleaning: Uses the 'ftfy' library to fix mojibake, repair
#     encoding issues, and normalize characters like quotation marks.
# 3.  Paragraph Preservation: It identifies paragraphs separated by blank
#     lines and maintains these breaks in the output file.
# 4.  Line Break Normalization: It joins lines within a paragraph that have
#     been split by soft line breaks (e.g., in copied text).
# 5.  Sentence Tokenization: It uses the Natural Language Toolkit (NLTK)
#     to accurately split paragraphs into individual sentences.
# 6.  Decorative Prefix Splitting: It detects if a sentence starts with
#     non-alphanumeric characters (like '***', '---', or list markers)
#     and splits this prefix onto a separate line from the actual sentence.
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
#

import os
import sys
import re
import nltk
from nltk.tokenize import sent_tokenize
import glob
import ftfy
import chardet  # <-- NEW: Import for encoding detection

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
    Checks if the sentence begins with extra decorative text.
    If so, splits the sentence into two parts: the prefix and the actual sentence.
    """
    m = re.search(r'([A-Za-z“"])', sentence)
    if m and m.start() > 0:
        prefix = sentence[:m.start()].rstrip()
        rest = sentence[m.start():].lstrip()
        if prefix:
            return [prefix, rest]
    return [sentence]

def process_file(filepath):
    """
    Reads a file with auto-detected encoding, processes its content to put
    one sentence per line, and overwrites the original file in UTF-8.
    """
    # --- NEW: Robust file reading with encoding detection ---
    try:
        # 1. Read the file in binary mode to analyze its raw bytes.
        with open(filepath, 'rb') as f:
            raw_data = f.read()
            if not raw_data:
                print(f"Skipped empty file: {filepath}")
                return

        # 2. Detect the encoding from the raw bytes.
        detection = chardet.detect(raw_data)
        encoding = detection['encoding']

        # 3. Decode the raw bytes into a text string using the detected encoding.
        # Fallback to UTF-8 if detection is uncertain.
        if encoding is None or detection['confidence'] < 0.9:
            print(f"  - Info: Low confidence for detected encoding ({encoding}). Using UTF-8 for {filepath}.")
            encoding = 'utf-8'
        
        text = raw_data.decode(encoding, errors='replace')

    except Exception as e:
        print(f"Error reading or decoding file {filepath}: {e}")
        return

    # --- Text processing remains the same ---
    text = ftfy.fix_text(text)
    paragraphs = re.split(r'\n\s*\n', text.strip())
    processed_paragraphs = []
    for para in paragraphs:
        single_line_para = ' '.join(para.splitlines())
        sentences = tokenize_text(single_line_para)
        processed_lines = []
        for sentence in sentences:
            for line in split_decorative(sentence):
                processed_lines.append(line)
        processed_paragraphs.append("\n".join(processed_lines))

    output_text = "\n\n".join(processed_paragraphs)

    # --- NEW: Robust file writing, always guaranteeing UTF-8 output ---
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
            process_file(filepath) # Error handling is now inside process_file
    print("\nProcessing complete.")


if __name__ == "__main__":
    main()