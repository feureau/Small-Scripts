#!/usr/bin/env python3
"""
Batch-convert (or extract pages from) PDF files in a directory to DOCX format using glob.

Usage examples:
    # Convert all pages of each PDF in current directory:
    python pdf_to_docx_batch.py --dir .

    # Convert all pages, output to specific folder:
    python pdf_to_docx_batch.py --dir . --out ./docx_output

    # Extract pages 10,14,20 from each PDF:
    python pdf_to_docx_batch.py --dir . --page 10,14,20 --out ./docx_pages

    # Extract page range 10-20 from each PDF:
    python pdf_to_docx_batch.py --dir . --page 10-20

Prerequisite:
    pip install pdf2docx
"""
import os
import glob
import argparse
from pdf2docx import Converter


def parse_page_spec(spec: str):
    """Parse page spec like '10,14,20' or '10-20' into zero-based (start, end) tuples."""
    ranges = []
    for part in spec.split(','):
        part = part.strip()
        if '-' in part:
            start_str, end_str = part.split('-', 1)
            start, end = int(start_str), int(end_str)
            ranges.append((start - 1, end - 1))
        else:
            page = int(part)
            ranges.append((page - 1, page - 1))
    return ranges


def convert_pdf_to_docx(pdf_file: str, docx_file: str, start: int = 0, end: int = None) -> None:
    """Convert pages [start:end] of a single PDF file to DOCX."""
    cv = Converter(pdf_file)
    cv.convert(docx_file, start=start, end=end)
    cv.close()


def main():
    parser = argparse.ArgumentParser(
        description="Batch convert or extract pages from PDF files in a directory to DOCX format."
    )
    parser.add_argument(
        '--dir', '-d',
        default=os.getcwd(),
        help='Directory containing PDFs (default: current working directory)'
    )
    parser.add_argument(
        '--out', '-o',
        default=None,
        help=('Output directory for DOCX files. ' 
              'If omitted, DOCX files are placed alongside source PDFs.')
    )
    parser.add_argument(
        '--page', '-p',
        dest='page_spec',
        default=None,
        help=('Pages to extract, e.g. "10,14,20" or a range "10-20". ' 
              'If omitted, all pages are converted.')
    )
    parser.add_argument(
        '--ext', '-e',
        default='pdf',
        help='File extension to search for (default: pdf)'
    )
    args = parser.parse_args()

    # Find PDF files
    pattern = os.path.join(args.dir, f'*.{args.ext}')
    pdf_files = glob.glob(pattern)

    if not pdf_files:
        print(f"No .{args.ext} files found in {args.dir}")
        return

    # Prepare output directory
    if args.out:
        os.makedirs(args.out, exist_ok=True)

    # Determine page ranges
    page_ranges = None
    if args.page_spec:
        page_ranges = parse_page_spec(args.page_spec)

    # Process each PDF
    for pdf_file in pdf_files:
        basename = os.path.splitext(os.path.basename(pdf_file))[0]

        if page_ranges:
            # Extract specified pages/ranges into separate DOCX files
            for start, end in page_ranges:
                if start == end:
                    suffix = f"_p{start+1}"
                else:
                    suffix = f"_{start+1}-{end+1}"
                if args.out:
                    docx_path = os.path.join(args.out, f"{basename}{suffix}.docx")
                else:
                    docx_path = os.path.join(args.dir, f"{basename}{suffix}.docx")
                print(f"Extracting pages {start+1}-{end+1} from '{pdf_file}' -> '{docx_path}'...")
                try:
                    convert_pdf_to_docx(pdf_file, docx_path, start=start, end=end)
                except Exception as e:
                    print(f"Failed to extract pages from {pdf_file}: {e}")
        else:
            # Convert entire document
            if args.out:
                docx_path = os.path.join(args.out, f"{basename}.docx")
            else:
                docx_path = os.path.join(args.dir, f"{basename}.docx")
            print(f"Converting entire '{pdf_file}' -> '{docx_path}'...")
            try:
                convert_pdf_to_docx(pdf_file, docx_path)
            except Exception as e:
                print(f"Failed to convert {pdf_file}: {e}")

    print("Batch processing complete.")

if __name__ == '__main__':
    main()
