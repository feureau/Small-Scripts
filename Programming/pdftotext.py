import os
import sys
import glob
import subprocess
import argparse

# Define the subfolder name for output text files
OUTPUT_FOLDER = "extracted_text"

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

def extract_text_from_pdfs(pdf_pattern, per_page):
    """Extracts text from PDFs and saves them in a subfolder.

    If per_page is True, each page of the PDF will be saved as a separate
    UTF-8 encoded text file named <filename>_page1.txt, <filename>_page2.txt, etc.
    Otherwise, the entire PDF will be saved into a single UTF-8 text file.
    """
    # Get the current working directory
    cwd = os.getcwd()
    
    # Ensure the output directory exists
    output_dir = os.path.join(cwd, OUTPUT_FOLDER)
    os.makedirs(output_dir, exist_ok=True)

    # Find matching PDF files
    pdf_files = glob.glob(pdf_pattern)
    
    if not pdf_files:
        print("No PDF files found matching:", pdf_pattern)
        return
    
    print(f"Extracting text from {len(pdf_files)} PDF(s)...")

    for pdf_file in pdf_files:
        # Get the base filename without extension
        base_name = os.path.splitext(os.path.basename(pdf_file))[0]

        if per_page:
            # Get the total number of pages in the PDF
            num_pages = get_pdf_page_count(pdf_file)
            if num_pages == 0:
                print(f"Could not determine page count for {pdf_file}. Skipping.")
                continue

            print(f"Extracting {num_pages} pages from {pdf_file}...")

            for page in range(1, num_pages + 1):
                output_file = os.path.join(output_dir, f"{base_name}_page{page}.txt")
                command = [
                    "pdftotext", "-layout", "-enc", "UTF-8",
                    "-f", str(page), "-l", str(page),
                    pdf_file, output_file
                ]
                try:
                    subprocess.run(command, check=True)
                    print(f"Extracted page {page} of {pdf_file} -> {output_file}")
                except subprocess.CalledProcessError as e:
                    print(f"Error processing page {page} of {pdf_file}: {e}")
        else:
            # Extract the entire PDF into a single text file
            output_file = os.path.join(output_dir, f"{base_name}.txt")
            command = ["pdftotext", "-layout", "-enc", "UTF-8", pdf_file, output_file]
            try:
                subprocess.run(command, check=True)
                print(f"Extracted: {pdf_file} -> {output_file}")
            except subprocess.CalledProcessError as e:
                print(f"Error processing {pdf_file}: {e}")

if __name__ == "__main__":
    # Set up the argument parser with detailed help messages
    parser = argparse.ArgumentParser(
        description="Extract text from PDFs using pdftotext.",
        epilog=("Examples:\n"
                "  Extract entire PDFs into single text files:\n"
                "    python pdftotext.py '*.pdf'\n\n"
                "  Extract each page into individual text files:\n"
                "    python pdftotext.py '*.pdf' -p\n\n"
                "All output text files are encoded in UTF-8 and stored in the 'extracted_text' subfolder.")
    )
    parser.add_argument("pdf_pattern", help="Pattern to match PDF files (e.g., '*.pdf').")
    parser.add_argument("-p", "--page", action="store_true",
                        help="Extract each page into separate text files (e.g., filename_page1.txt, filename_page2.txt, etc.).")

    args = parser.parse_args()

    # Run the extraction process based on the provided arguments
    extract_text_from_pdfs(args.pdf_pattern, args.page)
