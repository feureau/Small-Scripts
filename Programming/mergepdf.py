#!/usr/bin/env python3
"""
mergepdf.py

This script merges a set of PDF files specified on the command line (wildcards are supported)
into a single PDF file. The merged PDF is saved in the current working directory as "merged.pdf".

Usage:
    mergepdf.py *.pdf

If no PDF files are specified as arguments, it will try to merge all PDF files in the current directory.
"""

import os
import sys
import glob
from PyPDF2 import PdfReader, PdfWriter  # Requires PyPDF2 library

def merge_pdfs(paths, output):
    """Merge multiple PDF files.

    Args:
        paths (list of str): File paths to PDFs to merge.
        output (str): Path to the output PDF file.
    """
    pdf_writer = PdfWriter()
    for path in paths:
        try:
            pdf_reader = PdfReader(path)
        except Exception as e:
            print(f"Error reading {path}: {e}")
            continue

        for page in pdf_reader.pages:
            pdf_writer.add_page(page)

    try:
        with open(output, 'wb') as out_file:
            pdf_writer.write(out_file)
        print(f"Successfully merged {len(paths)} PDF file(s) into {output}")
    except Exception as e:
        print(f"Error writing the merged PDF: {e}")
        sys.exit(1)

def main():
    # Read command-line arguments (excluding the script name)
    args = sys.argv[1:]

    # If arguments are provided, use glob to process possible wildcards
    pdf_files = []
    if args:
        for arg in args:
            pdf_files.extend(glob.glob(arg))
    else:
        # If no command-line argument is provided, merge all PDFs in the current directory.
        pdf_files = glob.glob("*.pdf")

    if not pdf_files:
        print("No PDF files found to merge.")
        sys.exit(1)

    # Sort the files alphabetically
    pdf_files.sort()
    print("PDF files to be merged:")
    for pdf in pdf_files:
        print(f"  - {os.path.basename(pdf)}")

    output_file = os.path.join(os.getcwd(), "merged.pdf")
    merge_pdfs(pdf_files, output_file)

if __name__ == '__main__':
    main()
