import os
import sys
import glob
import subprocess

# Define the subfolder name
OUTPUT_FOLDER = "extracted_text"

def extract_text_from_pdfs(pdf_pattern):
    """Extracts text from PDFs and saves them in a subfolder."""
    
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
    
    print(f"Extracting text from {len(pdf_files)} PDFs...")
    
    for pdf_file in pdf_files:
        # Get the base filename without extension
        base_name = os.path.splitext(os.path.basename(pdf_file))[0]
        
        # Define output text file path
        txt_file = os.path.join(output_dir, f"{base_name}.txt")
        
        # Run pdftotext command
        try:
            subprocess.run(["pdftotext", "-layout", pdf_file, txt_file], check=True)
            print(f"Extracted: {pdf_file} -> {txt_file}")
        except subprocess.CalledProcessError as e:
            print(f"Error processing {pdf_file}: {e}")

if __name__ == "__main__":
    # Ensure a pattern is provided
    if len(sys.argv) < 2:
        print("Usage: python pdftotext.py <pdf_pattern>")
        sys.exit(1)
    
    # Get the PDF file pattern (e.g., "*.pdf")
    pdf_pattern = sys.argv[1]

    # Run the extraction
    extract_text_from_pdfs(pdf_pattern)
