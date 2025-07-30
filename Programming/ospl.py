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
# 1.  Paragraph Preservation: It identifies paragraphs separated by blank
#     lines and maintains these breaks in the output file.
# 2.  Line Break Normalization: It joins lines within a paragraph that have
#     been split by soft line breaks (e.g., in copied text).
# 3.  Sentence Tokenization: It uses the Natural Language Toolkit (NLTK)
#     to accurately split paragraphs into individual sentences.
# 4.  Decorative Prefix Splitting: It detects if a sentence starts with
#     non-alphanumeric characters (like '***', '---', or list markers)
#     and splits this prefix onto a separate line from the actual sentence.
# 5.  In-Place Editing: The script overwrites the original files with the
#     formatted text. Always make a backup of your original files if you
#     need to preserve them.
# 6.  Cross-Platform Wildcard Support: Uses the 'glob' module to handle
#     wildcard file patterns (e.g., *.txt) correctly on all operating
#     systems, including Windows.
#
# Dependencies:
# - Python 3.x
# - NLTK: The Natural Language Toolkit library. The script will prompt
#   to download the required 'punkt' tokenizer data on its first run if
#   it is not already installed.
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

def process_file(filepath):
    """
    Reads a file, processes its content to put one sentence per line,
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
    print(f"Processed and overwrote {filepath}")

def main():
    """
    Main function to handle command-line arguments and process files.
    If no arguments are given, it defaults to processing all .txt and .md files
    in the current directory.
    """
    # If no command-line arguments are provided, default to processing
    # all common text files in the current directory.
    if len(sys.argv) < 2:
        print("No file patterns provided. Defaulting to searching for *.txt and *.md files...")
        # Define the default file patterns to search for.
        input_args = ['*.txt', '*.md']
    else:
        # Otherwise, use the file patterns provided by the user.
        input_args = sys.argv[1:]

    input_files = []
    # Loop through each argument/pattern provided.
    for arg in input_args:
        # glob.glob expands the pattern (like *.txt) into a list of files.
        # It also works for regular filenames, returning a list with one item.
        expanded_files = glob.glob(arg)
        if not expanded_files:
            # This is now an informational message, not a warning.
            print(f"Info: No files found matching pattern: {arg}")
        input_files.extend(expanded_files)

    if not input_files:
        print("No input files to process.")
        sys.exit(0)

    # Process each file found.
    print(f"\nFound {len(input_files)} file(s) to process...")
    for filepath in input_files:
        if os.path.isfile(filepath):
            try:
                process_file(filepath)
            except Exception as e:
                print(f"Error processing {filepath}: {e}")
    print("\nProcessing complete.")


if __name__ == "__main__":
    main()