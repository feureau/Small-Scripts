#!/usr/bin/env python3
import os
import sys
import glob
import subprocess
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import cpu_count
from tqdm import tqdm

# Define the subfolder name for output image files
# OUTPUT_FOLDER = "converted_images"  <-- Removed

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

def convert_single_page(args):
    """Worker function to convert a single page of a PDF."""
    pdf_file, page, pdf_flag, output_prefix, ext = args
    command = [
        "pdftoppm", f"-{pdf_flag}",
        "-f", str(page), "-l", str(page),
        pdf_file, output_prefix
    ]
    try:
        # pdftoppm appends -<page> to the prefix automatically
        subprocess.run(command, check=True, capture_output=True)
        return True, None
    except subprocess.CalledProcessError as e:
        return False, f"Error converting page {page} of {pdf_file}: {e.stderr.decode() if e.stderr else str(e)}"

def convert_pdf_to_images(pdf_pattern, pdf_flag, ext, user_output_folder=None):
    """
    Converts each page of matching PDF files to an individual image.
    Uses pdftoppm with the provided format flag (e.g., '-png' or '-jpeg').
    """
    cwd = os.getcwd()
    
    pdf_files = glob.glob(pdf_pattern)
    if not pdf_files:
        print("No PDF files found matching:", pdf_pattern)
        return

    print(f"Converting {len(pdf_files)} PDF(s) to {ext.upper()} images...")
    
    num_cores = cpu_count()
    print(f"Using {num_cores} cores.")

    total_tasks = []
    for pdf_file in pdf_files:
        base_name = os.path.splitext(os.path.basename(pdf_file))[0]
        num_pages = get_pdf_page_count(pdf_file)
        if num_pages == 0:
            print(f"Could not determine page count for {pdf_file}. Skipping.")
            continue
        
        # Determine output directory
        if user_output_folder:
            # Use the user-provided folder exactly as is
            output_dir = user_output_folder
        else:
            # Default behavior: {filename}_images
            output_dir = f"{base_name}_images"
            
        output_dir = os.path.join(cwd, output_dir)
        os.makedirs(output_dir, exist_ok=True)

        output_prefix = os.path.join(output_dir, f"{base_name}_page")
        for page in range(1, num_pages + 1):
            total_tasks.append((pdf_file, page, pdf_flag, output_prefix, ext))

    # Progress bar for overall progress
    with tqdm(total=len(total_tasks), desc="Total Progress", unit="page") as pbar:
        with ProcessPoolExecutor(max_workers=num_cores) as executor:
            futures = [executor.submit(convert_single_page, task) for task in total_tasks]
            
            for future in as_completed(futures):
                success, error = future.result()
                if not success:
                    tqdm.write(error)
                pbar.update(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert each page of PDF files to individual images.",
        epilog=("Examples:\n"
                "  Convert PDF pages to PNG images:\n"
                "    python pdftoimages.py '*.pdf' --png\n\n"
                "  Convert PDF pages to JPEG images:\n"
                "    python pdftoimages.py '*.pdf' --jpg")
    )
    parser.add_argument("pdf_pattern", help="Pattern to match PDF files (e.g., '*.pdf').")
    parser.add_argument("-o", "--output", help="Specify output directory (files inside will not have '_images' suffix if this is used).")
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

    convert_pdf_to_images(args.pdf_pattern, pdf_flag, ext, args.output)
