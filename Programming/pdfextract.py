import fitz  # PyMuPDF
import argparse
import pathlib
import sys

def extract_images_from_pdfs(pdf_files, output_dir=None):
    """
    Extracts embedded images from each PDF in the provided list
    and saves them into dedicated subfolders.

    Args:
        pdf_files (list of pathlib.Path): List of PDF files to process.
        output_dir (pathlib.Path, optional): Optional output directory override.
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

        # Determine output path logic
        if output_dir:
            if len(pdf_files) == 1:
                # Single file with explicit output -> Use exactly as provided
                output_path = output_dir
            else:
                # Multiple files with output root -> Create subfolder inside root
                output_folder_name = f"{pdf_path.stem}_extract"
                output_path = output_dir / output_folder_name
        else:
            # No output flag -> Create folder alongside PDF
            output_folder_name = f"{pdf_path.stem}_extract"
            output_path = pdf_path.parent / output_folder_name

        output_path.mkdir(parents=True, exist_ok=True)

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
            print(f"  -> Extracted {images_in_pdf} image(s) to folder '{output_path}'")
            total_images_extracted += images_in_pdf

        except Exception as pdf_err:
            print(f"  ERROR: Could not process PDF file {pdf_path.name}. Reason: {pdf_err}")

    print(f"\n--- Finished ---")
    print(f"Processed {pdf_count} PDF file(s).")
    print(f"Total images extracted: {total_images_extracted}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract images from PDF files.")
    parser.add_argument("files", nargs="*", help="PDF files to process. If empty, scans current directory.")
    parser.add_argument("-o", "--output", help="Output directory. For single files, this is the destination folder. For multiple files, this is the root folder.")

    args = parser.parse_args()

    pdf_to_process = []
    
    # Resolve output directory if provided
    output_dir = pathlib.Path(args.output) if args.output else None

    if not args.files:
        # Default behavior: scan current working directory
        cwd = pathlib.Path.cwd()
        print(f"No arguments provided. Scanning for PDF files in: {cwd}")
        pdf_to_process.extend(cwd.glob('*.pdf'))
    else:
        for arg in args.files:
            path = pathlib.Path(arg)
            # Glob expansion support for shells that don't do it automatically (like Windows CMD)
            # However, argparse usually receives expanded lists if the shell handles it (bash/zsh/powershell).
            # For robustness, we check if it contains wildcards or just treat as file/dir.
            if '*' in arg or '?' in arg:
                 # Manually globbing if passed as string literal or from non-expanding shell
                 # This is a bit of an edge case but good for robustness
                 parent = pathlib.Path(arg).parent
                 if parent.name == '': parent = pathlib.Path('.')
                 pattern = pathlib.Path(arg).name
                 pdf_to_process.extend(parent.glob(pattern))
            elif path.is_file():
                if path.suffix.lower() == '.pdf':
                    pdf_to_process.append(path)
                else:
                    print(f"Skipping non-PDF file: {path}")
            elif path.is_dir():
                print(f"Scanning directory: {path}")
                pdf_to_process.extend(path.glob('*.pdf'))
            elif not path.exists():
                 # Attempt to treat as glob pattern if path doesn't exist
                 # e.g. user typed *.pdf in a shell that didn't expand it
                 parent = path.parent
                 if str(parent) == '.': parent = pathlib.Path.cwd()
                 pattern = path.name
                 found = list(parent.glob(pattern))
                 if found:
                     pdf_to_process.extend([p for p in found if p.suffix.lower() == '.pdf'])
                 else:
                     print(f"Argument not found (skipping): {arg}")

    if pdf_to_process:
        # Sort to ensure consistent processing order
        pdf_to_process.sort()
        # Filter duplicates just in case
        pdf_to_process = list(dict.fromkeys(pdf_to_process))
        extract_images_from_pdfs(pdf_to_process, output_dir)
    else:
        print("No valid PDF files found to process.")