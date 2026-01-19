#!/usr/bin/env python3
import sys
import os
import glob
from xhtml2pdf import pisa

def convert_html_to_pdf(file_patterns):
    # 1. Collect all files based on patterns
    files_to_process = []
    for pattern in file_patterns:
        # glob expands the wildcard pattern for Windows terminals
        matches = glob.glob(pattern)
        if not matches:
            print(f"Warning: No files found matching pattern '{pattern}'")
        files_to_process.extend(matches)

    files_to_process = sorted(list(set(files_to_process)))

    if not files_to_process:
        print("No files to process.")
        return

    print(f"Found {len(files_to_process)} files. Starting conversion...\n")

    # 2. Process files
    for input_file in files_to_process:
        base_name = os.path.splitext(input_file)[0]
        output_file = f"{base_name}.pdf"

        print(f"Converting: {input_file} -> {output_file}")
        
        try:
            # Open input file (HTML) and output file (PDF)
            with open(input_file, "r", encoding='utf-8') as source_html:
                with open(output_file, "wb") as result_pdf:
                    # Convert
                    pisa_status = pisa.CreatePDF(
                        source_html,                # the HTML file handle
                        dest=result_pdf             # the PDF file handle
                    )

            # Check for errors in the conversion log
            if pisa_status.err:
                print(f" [ERROR] Failed to convert {input_file}")
            else:
                print(f" [OK] Saved {output_file}")

        except Exception as e:
            print(f" [EXCEPTION] Error converting {input_file}: {e}")

    print("\nProcessing complete.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python htmltopdf.py <file_pattern>")
        print("Example: python htmltopdf.py *.html")
    else:
        convert_html_to_pdf(sys.argv[1:])