#!/usr/bin/env python3
import os
import re
import argparse
from pypdf import PdfReader, PdfWriter

def sanitize_filename(name):
    """
    Remove characters that are not allowed in Windows file names.
    """
    return re.sub(r'[<>:"/\\|?*]', '', name)

def split_pdf_by_bookmarks(pdf_path, output_dir):
    print(f"Processing {pdf_path}...")
    reader = PdfReader(pdf_path)
    try:
        outlines = reader.outlines  # Retrieve the bookmarks/outlines
    except Exception as e:
        print(f"Could not retrieve bookmarks from {pdf_path}: {e}")
        return

    # Flatten outlines in case some bookmarks are nested
    def flatten(outline_list):
        for item in outline_list:
            if isinstance(item, list):
                yield from flatten(item)
            else:
                yield item

    flat_outlines = list(flatten(outlines))
    chapters = []
    for item in flat_outlines:
        try:
            # Get the page number associated with the bookmark
            page_num = reader.get_destination_page_number(item)
            chapters.append((page_num, item.title))
        except Exception as e:
            print(f"Skipping an outline item: {e}")
            continue

    if not chapters:
        print(f"No bookmarks (chapter markers) found in {pdf_path}")
        return

    # Sort chapters by page number
    chapters.sort(key=lambda x: x[0])
    total_pages = len(reader.pages)
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]

    # Iterate over chapters; the chapter extends to the start of the next bookmark,
    # or to the end of the document for the last chapter.
    for i, (start_page, title) in enumerate(chapters):
        end_page = chapters[i+1][0] if i < len(chapters)-1 else total_pages
        writer = PdfWriter()
        for p in range(start_page, end_page):
            writer.add_page(reader.pages[p])
        safe_title = sanitize_filename(title)
        output_filename = f"{base_name}_chapter_{i+1}_{safe_title}.pdf"
        output_path = os.path.join(output_dir, output_filename)
        with open(output_path, "wb") as out_file:
            writer.write(out_file)
        print(f"Saved chapter: {output_path}")

def main():
    parser = argparse.ArgumentParser(
        description="Split PDFs into chapters based on bookmarks."
    )
    parser.add_argument("input_folder", help="Folder containing PDF files to split")
    parser.add_argument("output_folder", help="Folder where split chapters will be saved")
    args = parser.parse_args()

    input_folder = args.input_folder
    output_folder = args.output_folder

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Process each PDF file in the input folder
    for file_name in os.listdir(input_folder):
        if file_name.lower().endswith(".pdf"):
            pdf_path = os.path.join(input_folder, file_name)
            split_pdf_by_bookmarks(pdf_path, output_folder)

if __name__ == "__main__":
    main()
