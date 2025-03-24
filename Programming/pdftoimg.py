#!/usr/bin/env python3
import os
import sys
import glob
import subprocess
import argparse

# Define the subfolder name for output image files
OUTPUT_FOLDER = "converted_images"

def get_pdf_page_count(pdf_file):
    """Returns the number of pages in a PDF file using pdfinfo."""
    try:
        result = subprocess.run(["pdfinfo", pdf_file], capture_output=True, text=True, check=True)
        for line in result.stdout.splitlines():
            if line.startswith("Pages:"):
                parts = line.split(":")
                if len(parts) >= 2:
                    return int(parts[1].strip())
    except subprocess.CalledProcessError as e:
        print(f"Error running pdfinfo on {pdf_file}: {e}")
    except Exception as e:
        print(f"Unexpected error while getting page count for {pdf_file}: {e}")
    return 0

def convert_pdf_to_images(pdf_pattern, pdf_flag, ext):
    """
    Converts each page of matching PDF files to an individual image.
    Uses pdftoppm with the provided format flag (e.g., '-png' or '-jpeg').
    The output image files are saved in the OUTPUT_FOLDER with names like:
    <basename>_page-<pagenumber>.<ext>
    """
    cwd = os.getcwd()
    output_dir = os.path.join(cwd, OUTPUT_FOLDER)
    os.makedirs(output_dir, exist_ok=True)

    pdf_files = glob.glob(pdf_pattern)
    if not pdf_files:
        print("No PDF files found matching:", pdf_pattern)
        return

    print(f"Converting {len(pdf_files)} PDF(s) to {ext.upper()} images...")

    for pdf_file in pdf_files:
        base_name = os.path.splitext(os.path.basename(pdf_file))[0]
        num_pages = get_pdf_page_count(pdf_file)
        if num_pages == 0:
            print(f"Could not determine page count for {pdf_file}. Skipping.")
            continue

        print(f"Converting {num_pages} pages of {pdf_file}...")

        for page in range(1, num_pages + 1):
            # Set output prefix (pdftoppm will append "-<page>" to the prefix)
            output_prefix = os.path.join(output_dir, f"{base_name}_page")
            command = [
                "pdftoppm", f"-{pdf_flag}",
                "-f", str(page), "-l", str(page),
                pdf_file, output_prefix
            ]
            try:
                subprocess.run(command, check=True)
                # The output file will be named like <prefix>-<page>.<ext>
                output_file = f"{output_prefix}-{page}.{ext}"
                print(f"Converted page {page} of {pdf_file} -> {output_file}")
            except subprocess.CalledProcessError as e:
                print(f"Error converting page {page} of {pdf_file}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert each page of PDF files to individual images.",
        epilog=("Examples:\n"
                "  Convert PDF pages to PNG images:\n"
                "    python pdf2img.py '*.pdf' --png\n\n"
                "  Convert PDF pages to JPEG images:\n"
                "    python pdf2img.py '*.pdf' --jpg")
    )
    parser.add_argument("pdf_pattern", help="Pattern to match PDF files (e.g., '*.pdf').")
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument("--jpg", action="store_true", help="Output images in JPEG format.")
    group.add_argument("--png", action="store_true", help="Output images in PNG format (default).")
    args = parser.parse_args()

    # Determine which output format flag to use
    if args.jpg:
        pdf_flag = "jpeg"  # pdftoppm flag for JPEG
        ext = "jpg"        # Use .jpg extension for output files
    else:
        pdf_flag = "png"   # pdftoppm flag for PNG
        ext = "png"

    convert_pdf_to_images(args.pdf_pattern, pdf_flag, ext)
