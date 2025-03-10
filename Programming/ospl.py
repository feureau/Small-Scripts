import os
import sys
import re
import nltk
from nltk.tokenize import sent_tokenize

def tokenize_text(text):
    try:
        return sent_tokenize(text)
    except LookupError as e:
        if "punkt_tab" in str(e):
            print("Missing NLTK resource 'punkt_tab'. Downloading now...")
            nltk.download('punkt_tab')
            return sent_tokenize(text)
        else:
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

def process_file(filepath, output_dir):
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

    # Write the processed text to the output file using UTF-8 encoding.
    base = os.path.basename(filepath)
    output_path = os.path.join(output_dir, base)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(output_text)

def main():
    # Accept multiple text files from command-line arguments (e.g., ospl.py *.txt)
    input_files = sys.argv[1:]
    
    # Create an "output" folder in the current working directory.
    output_dir = os.path.join(os.getcwd(), "output")
    os.makedirs(output_dir, exist_ok=True)
    
    for filepath in input_files:
        process_file(filepath, output_dir)

if __name__ == "__main__":
    main()
