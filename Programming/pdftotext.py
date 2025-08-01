"""
PDF-to-OSPL Converter
=====================

Description:
------------
This script extracts text from PDF files and reformats it using the One Sentence Per Line (OSPL) style:
- Each sentence appears on its own line.
- Decorative or non-textual prefixes (like list bullets or section headers) are separated.
- Paragraph breaks are preserved.

The script uses:
- **PyMuPDF (fitz)** to read and extract raw text from PDF files.
- **NLTK** (Natural Language Toolkit) to split paragraphs into individual sentences using the 'punkt' tokenizer.

Key Features:
-------------
1. PDF Text Extraction:
   - Extracts text from PDF documents, either per-page or entire file.
   - Uses `fitz` from the PyMuPDF library for fast and accurate parsing.

2. Sentence Tokenization:
   - Each paragraph is split into individual sentences using NLTK's `sent_tokenize`.
   - Ensures natural language sentence boundaries are respected.

3. Decorative Prefix Handling:
   - Detects and splits common prefixes like list markers (e.g., "***", "--", "1. ", "•").
   - Ensures they are placed on separate lines from the main sentence.

4. OSPL Formatting:
   - Paragraphs separated by blank lines are preserved.
   - Within each paragraph, all sentences appear one per line for readability and tool compatibility.

5. Flexible Output:
   - Outputs `.txt` files are saved in the **same directory as their source `.pdf`** files.
   - Filenames match the PDF source (e.g., `file.pdf` ➝ `file.txt`, or `file_page2.txt` if split by page).

6. Command-Line Interface:
   - Use `-p` or `--page` to split each PDF page into its own `.txt` file.
   - Supports wildcard file patterns like `"*.pdf"`.

Dependencies:
-------------
- Python 3.x
- `PyMuPDF` (install via `pip install pymupdf`)
- `nltk` (install via `pip install nltk`)
  - On first run, the 'punkt' tokenizer will be downloaded if not present.

Usage:
------
# Process entire PDFs into one OSPL-formatted text file per PDF:
    python script.py "*.pdf"

# Process PDFs and split output into one OSPL-formatted text file per page:
    python script.py "*.pdf" -p

Notes:
------
- The script will automatically download the NLTK `punkt` tokenizer if missing.
- Use quotes (`"*.pdf"`) around patterns to ensure shell compatibility on Windows/macOS/Linux.
"""

import os
import sys
import re
import glob
import argparse
import fitz  # PyMuPDF
import nltk
from nltk.tokenize import sent_tokenize

# Ensure the NLTK 'punkt' tokenizer is available
try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    print("Downloading NLTK tokenizer 'punkt'...")
    nltk.download("punkt")


def tokenize_text(text):
    """
    Splits a block of text into individual sentences using NLTK's sentence tokenizer.
    """
    return sent_tokenize(text)


def split_decorative(sentence):
    """
    Detects and splits decorative prefixes (like "***" or "--") from the start of a sentence.
    If found, returns a list with the prefix and the remaining sentence.
    Otherwise, returns a single-item list with the original sentence.
    """
    match = re.search(r'([A-Za-z“"])', sentence)
    if match and match.start() > 0:
        prefix = sentence[:match.start()].rstrip()
        rest = sentence[match.start():].lstrip()
        if prefix:
            return [prefix, rest]
    return [sentence]


def ospl_format_text(text):
    """
    Reformats raw text into the One Sentence Per Line (OSPL) style.

    Steps:
    1. Split the text into paragraphs using blank lines.
    2. Flatten soft line breaks within paragraphs.
    3. Split paragraphs into sentences using NLTK.
    4. Split decorative prefixes if found.
    5. Return all sentences with paragraph breaks preserved.
    """
    paragraphs = re.split(r'\n\s*\n', text.strip())
    processed_paragraphs = []

    for para in paragraphs:
        # Normalize soft line breaks inside paragraphs
        single_line = ' '.join(para.splitlines())
        # Tokenize into sentences
        sentences = tokenize_text(single_line)
        processed_lines = []

        for sentence in sentences:
            for line in split_decorative(sentence):
                processed_lines.append(line)

        processed_paragraphs.append("\n".join(processed_lines))

    return "\n\n".join(processed_paragraphs)


def extract_text_from_pdfs(pdf_pattern, per_page):
    """
    Extracts text from PDF files matching a given pattern and applies OSPL formatting.

    Args:
    - pdf_pattern: Glob pattern for selecting PDF files (e.g., "*.pdf").
    - per_page: If True, splits output per page; otherwise, processes entire document.

    Output:
    - One or more .txt files, saved in the same folder as each source .pdf file.
    """
    pdf_files = glob.glob(pdf_pattern)

    if not pdf_files:
        print("No PDF files found matching:", pdf_pattern)
        return

    print(f"Extracting and formatting text from {len(pdf_files)} PDF(s)...")

    for pdf_file in pdf_files:
        base_name = os.path.splitext(os.path.basename(pdf_file))[0]
        pdf_dir = os.path.dirname(pdf_file) or os.getcwd()  # handle relative paths

        try:
            with fitz.open(pdf_file) as doc:
                if per_page:
                    for page_num in range(doc.page_count):
                        page = doc.load_page(page_num)
                        raw_text = page.get_text("text")
                        formatted_text = ospl_format_text(raw_text)

                        output_file = os.path.join(pdf_dir, f"{base_name}_page{page_num + 1}.txt")
                        with open(output_file, 'w', encoding='utf-8') as out_f:
                            out_f.write(formatted_text)

                        print(f"  -> Page {page_num + 1} saved as {os.path.basename(output_file)}")
                else:
                    full_text = ''.join(page.get_text("text") for page in doc)
                    formatted_text = ospl_format_text(full_text)

                    output_file = os.path.join(pdf_dir, f"{base_name}.txt")
                    with open(output_file, 'w', encoding='utf-8') as out_f:
                        out_f.write(formatted_text)

                    print(f"Extracted and formatted: {os.path.basename(output_file)}")

        except Exception as e:
            print(f"Error processing {pdf_file}: {e}", file=sys.stderr)


def main():
    """
    CLI entry point. Parses command-line arguments and launches the extraction/formatting.
    """
    parser = argparse.ArgumentParser(
        description="Extract text from PDFs and format using OSPL (One Sentence Per Line).",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python script.py \"*.pdf\"           # One file per PDF\n"
            "  python script.py \"*.pdf\" -p        # One file per page\n"
            "\nDependencies:\n"
            "  pip install pymupdf nltk"
        )
    )
    parser.add_argument("pdf_pattern", help="Glob pattern for PDF files (e.g., \"*.pdf\")")
    parser.add_argument("-p", "--page", action="store_true",
                        help="Split output into one file per PDF page")

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    args = parser.parse_args()
    extract_text_from_pdfs(args.pdf_pattern, args.page)


if __name__ == "__main__":
    main()
