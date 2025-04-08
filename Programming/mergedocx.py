#!/usr/bin/env python
import sys
import glob
import os
from docx import Document

def merge_docx(file_list, output="merged_document.docx"):
    """
    Merge a list of DOCX files into a single document.
    
    :param file_list: List of input DOCX file paths.
    :param output: Output file name for the merged document.
    """
    if not file_list:
        print("No DOCX files provided for merging.")
        sys.exit(1)

    # Start with the first document.
    print(f"Processing file: {file_list[0]}")
    merged_document = Document(file_list[0])
    
    # For every other document, append its contents.
    for file in file_list[1:]:
        print(f"Processing file: {file}")
        sub_doc = Document(file)
        # Iterate through all elements in the sub-document's body and append them.
        for element in sub_doc.element.body:
            merged_document.element.body.append(element)
        
        # Optionally, add a page break between documents.
        merged_document.add_page_break()

    # Save the merged document in the current working directory.
    merged_document.save(output)
    print(f"Merged {len(file_list)} documents into '{output}'.")

if __name__ == "__main__":
    # Collect arguments passed to the script (which may contain wildcards).
    args = sys.argv[1:]
    if not args:
        print("Usage: mergedocx.py <docx_file_pattern1> [<docx_file_pattern2> ...]")
        sys.exit(1)

    # Expand file patterns using glob.
    docx_files = []
    for pattern in args:
        matched_files = glob.glob(pattern)
        if matched_files:
            docx_files.extend(matched_files)
        else:
            # If glob doesn't find a match, use the literal argument (could be a direct file name)
            docx_files.append(pattern)

    # Remove duplicates and sort the list for consistent order.
    docx_files = sorted(set(docx_files))
    
    # Check that the files exist.
    docx_files = [f for f in docx_files if os.path.isfile(f) and f.lower().endswith('.docx')]
    if not docx_files:
        print("No valid DOCX files found. Please check your patterns and files.")
        sys.exit(1)
    
    merge_docx(docx_files)
