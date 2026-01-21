import fitz  # PyMuPDF

import pathlib
import os
import sys

def extract_images_from_pdfs(pdf_files):
    """
    Extracts embedded images from each PDF in the provided list
    and saves them into dedicated subfolders relative to the PDF's location.

    Args:
        pdf_files (list of pathlib.Path): List of PDF files to process.
    """
    pdf_count = 0
    total_images_extracted = 0

    if not pdf_files:
        print("No PDF files to process.")
        return

    print(f"Found {len(pdf_files)} PDF file(s) to process.")

    for pdf_path in pdf_files:
        pdf_count += 1
        images_in_pdf = 0
        print(f"\n--- Processing PDF ({pdf_count}/{len(pdf_files)}): {pdf_path.name} ---")

        # Create a subdirectory for the images from this PDF
        output_folder_name = f"{pdf_path.stem}_images"
        output_path = pdf_path.parent / output_folder_name
        output_path.mkdir(exist_ok=True) # Create folder, ignore if already exists

        try:
            # Open the PDF file
            pdf_document = fitz.open(pdf_path)

            # Iterate through each page to find images
            for page_index in range(len(pdf_document)):
                page = pdf_document.load_page(page_index)
                image_list = page.get_images(full=True) # Get list of images on the page

                if not image_list:
                    continue # No images on this page

                print(f"  Page {page_index + 1}: Found {len(image_list)} image reference(s).")

                for img_index, img_info in enumerate(image_list):
                    # img_info is a tuple, the first element is the xref of the image
                    xref = img_info[0]

                    try:
                        # Extract the base image dictionary
                        base_image = pdf_document.extract_image(xref)
                        if not base_image:
                           print(f"    - Could not extract image data for xref {xref} on page {page_index + 1}.")
                           continue

                        image_bytes = base_image["image"]
                        image_ext = base_image["ext"]

                        # Generate a filename
                        image_filename = f"page{page_index + 1:03d}_img{img_index + 1:03d}.{image_ext}"
                        save_path = output_path / image_filename

                        # --- Method: Direct Save (Extracts content as-is) ---
                        print(f"    - Saving image {img_index + 1} (xref {xref}) as {save_path.name}")
                        with open(save_path, "wb") as img_file:
                            img_file.write(image_bytes)
                        images_in_pdf += 1

                    except Exception as img_err:
                        print(f"    - ERROR processing image {img_index + 1} (xref {xref}) on page {page_index + 1}: {img_err}")

            pdf_document.close()
            print(f"  -> Extracted {images_in_pdf} image(s) to folder '{output_folder_name}'")
            total_images_extracted += images_in_pdf

        except Exception as pdf_err:
            print(f"  ERROR: Could not process PDF file {pdf_path.name}. Reason: {pdf_err}")

    print(f"\n--- Finished ---")
    print(f"Processed {pdf_count} PDF file(s).")
    print(f"Total images extracted: {total_images_extracted}")


if __name__ == "__main__":
    args = sys.argv[1:]
    pdf_to_process = []

    if not args:
        # Default behavior: scan current working directory
        cwd = pathlib.Path.cwd()
        print(f"No arguments provided. Scanning for PDF files in: {cwd}")
        pdf_to_process.extend(cwd.glob('*.pdf'))
    else:
        for arg in args:
            path = pathlib.Path(arg)
            if path.is_file():
                if path.suffix.lower() == '.pdf':
                    pdf_to_process.append(path)
                else:
                    print(f"Skipping non-PDF file: {path}")
            elif path.is_dir():
                print(f"Scanning directory: {path}")
                pdf_to_process.extend(path.glob('*.pdf'))
            else:
                print(f"Argument not found (skipping): {arg}")

    if pdf_to_process:
        # Sort to ensure consistent processing order
        pdf_to_process.sort()
        extract_images_from_pdfs(pdf_to_process)
    else:
        print("No valid PDF files found to process.")