import os
import sys
import glob
import argparse
import fitz  # PyMuPDF library

# Define the subfolder name for output text files
OUTPUT_FOLDER = "extracted_text"

def extract_text_from_pdfs(pdf_pattern, per_page):
    """
    Extracts text from PDFs using PyMuPDF and saves the text in a subfolder.

    If per_page is True, each page of the PDF will be saved as a separate
    UTF-8 encoded text file named <filename>_page1.txt, <filename>_page2.txt, etc.
    Otherwise, the entire PDF's text will be saved into a single UTF-8 text file.
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
    
    print(f"Extracting text from {len(pdf_files)} PDF(s) using PyMuPDF...")

    for pdf_file in pdf_files:
        # Get the base filename without extension
        base_name = os.path.splitext(os.path.basename(pdf_file))[0]

        try:
            # Use a 'with' statement to ensure the document is properly closed
            with fitz.open(pdf_file) as doc:
                if per_page:
                    num_pages = doc.page_count
                    print(f"Extracting {num_pages} pages from {pdf_file}...")

                    for page_num in range(num_pages):
                        page = doc.load_page(page_num)  # Load the page
                        text = page.get_text("text")   # Extract text
                        
                        output_file = os.path.join(output_dir, f"{base_name}_page{page_num + 1}.txt")
                        with open(output_file, 'w', encoding='utf-8') as out_f:
                            out_f.write(text)
                        
                        print(f"  -> Extracted page {page_num + 1} to {os.path.basename(output_file)}")

                else:
                    # Extract the entire PDF into a single text file
                    output_file = os.path.join(output_dir, f"{base_name}.txt")
                    with open(output_file, 'w', encoding='utf-8') as out_f:
                        for page in doc:  # Iterate through pages
                            out_f.write(page.get_text("text"))
                    
                    print(f"Extracted: {pdf_file} -> {os.path.basename(output_file)}")

        except Exception as e:
            print(f"Error processing {pdf_file}: {e}", file=sys.stderr)

if __name__ == "__main__":
    # Set up the argument parser with detailed help messages
    parser = argparse.ArgumentParser(
        description="Extract text from PDFs using the PyMuPDF library.",
        formatter_class=argparse.RawTextHelpFormatter, # Allows for newlines in epilog
        epilog=(
            "Prerequisite: This script requires PyMuPDF. Install it with:\n"
            "  pip install PyMuPDF\n\n"
            "Examples:\n"
            "  # Extract entire PDFs into single text files:\n"
            "  python pdftotext_pymupdf.py \"*.pdf\"\n\n"
            "  # Extract each page into individual text files:\n"
            "  python pdftotext_pymupdf.py \"*.pdf\" -p\n\n"
            "All output text files are encoded in UTF-8 and stored in the 'extracted_text' subfolder."
        )
    )
    parser.add_argument("pdf_pattern", help="Pattern to match PDF files (e.g., \"*.pdf\").\nUse quotes if your pattern includes wildcards.")
    parser.add_argument("-p", "--page", action="store_true",
                        help="Extract each page into separate text files (e.g., filename_page1.txt).")

    # If no arguments are provided, print help and exit
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()

    # Run the extraction process based on the provided arguments
    extract_text_from_pdfs(args.pdf_pattern, args.page)