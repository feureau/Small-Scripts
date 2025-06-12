#!/usr/bin/env python3
import argparse
import os
from pathlib import Path
from ebooklib import epub, ITEM_DOCUMENT # <-- MODIFIED IMPORT
from bs4 import BeautifulSoup
import sys
import glob # <--- IMPORT GLOB

def extract_text_from_html(html_content):
    """Extracts plain text from HTML content."""
    soup = BeautifulSoup(html_content, 'html.parser')
    # Remove script and style elements
    for script_or_style in soup(["script", "style"]):
        script_or_style.decompose()
    # Get text
    text = soup.get_text(separator='\n', strip=True)
    return text

def epub_to_text(epub_path, output_txt_path):
    """
    Converts an EPUB file to a TXT file.
    """
    try:
        # Address the UserWarning by being explicit with options
        # If you don't rely on NCX for ordering (spine is primary), True is fine.
        read_options = {'ignore_ncx': True} # <-- ADDED/MODIFIED for UserWarning
        book = epub.read_epub(epub_path, options=read_options)
    except Exception as e:
        print(f"Error: Could not read EPUB file '{epub_path}'. {e}", file=sys.stderr)
        return False

    full_text = []
    items_to_process = []

    if book.spine:
        for item_id, _ in book.spine:
            item = book.get_item_with_id(item_id)
            # MODIFIED CONDITION:
            if item and item.get_type() == ITEM_DOCUMENT: # <-- CORRECTED usage
                items_to_process.append(item)

    # Fallback or if spine items were not documents
    if not items_to_process:
        all_doc_items = list(book.get_items_of_type(ITEM_DOCUMENT)) # <-- CORRECTED usage and more robust fallback
        if all_doc_items:
            if book.spine: # If spine existed but had no docs
                 print(f"Warning: EPUB '{epub_path}' spine items are not documents. Processing all document items found.", file=sys.stderr)
            else: # If spine was empty
                 print(f"Warning: EPUB '{epub_path}' has no spine. Processing all document items found.", file=sys.stderr)
            items_to_process = all_doc_items
        else:
            print(f"Warning: No processable document items found in '{epub_path}'. Output will be empty.", file=sys.stderr)
            # Create an empty txt file
            try:
                with open(output_txt_path, 'w', encoding='utf-8') as f:
                    f.write("")
                print(f"Successfully created empty file: '{output_txt_path}' for '{epub_path}'")
            except IOError as e:
                print(f"Error: Could not write empty output file '{output_txt_path}'. {e}", file=sys.stderr)
            return True # Or False if an empty file is considered an error in some contexts

    for item in items_to_process:
        try:
            html_content = item.get_content()
            # Ebooklib usually returns bytes, decode if necessary
            if isinstance(html_content, bytes):
                # Try UTF-8 first
                try:
                    html_content = html_content.decode('utf-8')
                except UnicodeDecodeError:
                    # Fallback to item's encoding or a common one if not specified
                    encoding = item.encoding if item.encoding else 'latin-1' # Or 'cp1252' or other common fallback
                    try:
                        html_content = item.get_content().decode(encoding, errors='replace')
                        print(f"  Info: Decoded item {item.get_name()} using {encoding}.", file=sys.stderr)
                    except Exception as enc_e:
                        print(f"  Warning: Could not decode content from item {item.get_name()} with encoding {encoding} or UTF-8. Skipping. Error: {enc_e}", file=sys.stderr)
                        continue

            text = extract_text_from_html(html_content)
            if text:
                full_text.append(text)
        except Exception as e:
            print(f"  Warning: Could not process item {item.get_name()} in '{epub_path}'. {e}", file=sys.stderr)
            continue

    if not full_text and not items_to_process: # Case where items_to_process was initially empty
        pass # Already handled creating an empty file if no processable items
    elif not full_text and items_to_process: # Case where items were processed but yielded no text
        print(f"Warning: Processed items from '{epub_path}' yielded no text content.", file=sys.stderr)

    try:
        with open(output_txt_path, 'w', encoding='utf-8') as f:
            f.write("\n\n".join(full_text)) # Join chapters/sections with double newlines
        if full_text or not items_to_process: # Report success if text written or if empty file was intended
            print(f"Successfully converted '{epub_path}' to '{output_txt_path}'")
        return True
    except IOError as e:
        print(f"Error: Could not write to output file '{output_txt_path}'. {e}", file=sys.stderr)
        return False

def main():
    parser = argparse.ArgumentParser(
        description="Convert EPUB files to TXT format.",
        formatter_class=argparse.RawTextHelpFormatter # For better help text formatting
    )
    parser.add_argument("epub_files", nargs='+', help="Path(s) to one or more EPUB file(s) or glob pattern(s) to convert.") # MODIFIED HELP
    parser.add_argument(
        "-o", "--output-dir",
        help="Directory to save the TXT files.\n"
             "If not specified, TXT files are saved in the same directory as their respective EPUBs."
    )
    parser.add_argument(
        "-f", "--force",
        action="store_true",
        help="Overwrite output TXT file if it already exists."
    )

    args = parser.parse_args()

    if args.output_dir:
        output_dir = Path(args.output_dir)
        if not output_dir.exists():
            try:
                output_dir.mkdir(parents=True, exist_ok=True)
                print(f"Created output directory: {output_dir}")
            except OSError as e:
                print(f"Error: Could not create output directory '{output_dir}'. {e}", file=sys.stderr)
                sys.exit(1)
        elif not output_dir.is_dir():
            print(f"Error: Specified output path '{output_dir}' is not a directory.", file=sys.stderr)
            sys.exit(1)
    else:
        output_dir = None # Will use input file's directory

    success_count = 0
    failure_count = 0

    # --- START OF MODIFICATION for wildcard handling ---
    actual_epub_files_to_process = []
    for path_or_pattern in args.epub_files:
        # glob.glob expands the pattern.
        # If path_or_pattern is a literal filename that exists, glob returns [filename].
        # If path_or_pattern is a literal filename that doesn't exist, glob returns [].
        # If path_or_pattern is a pattern, glob returns matched files or [].
        expanded_paths = glob.glob(path_or_pattern)
        
        if not expanded_paths:
            # If glob found nothing, it could be:
            # 1. A pattern that matched no files (e.g., "*.nonexistent")
            # 2. A literal filename that doesn't exist (e.g., "myfile.epub" when it's not there)
            
            # Check if the input string itself looks like a pattern
            # A simple check for common wildcard characters
            is_likely_pattern = any(char in path_or_pattern for char in ['*', '?', '[', ']'])

            if is_likely_pattern:
                # It was a pattern, but it matched no files.
                print(f"Warning: The pattern '{path_or_pattern}' did not match any files.", file=sys.stderr)
            else:
                # It was likely a literal filename that doesn't exist.
                # Add it to the list so the existing error handling below catches it.
                actual_epub_files_to_process.append(path_or_pattern)
        else:
            actual_epub_files_to_process.extend(expanded_paths)
    
    if not actual_epub_files_to_process and args.epub_files:
        # This can happen if all inputs were patterns that matched nothing,
        # or if args.epub_files contained only non-existent literal files
        # that didn't look like patterns (though the latter is less likely
        # to result in an empty list here due to the 'else' branch above).
        # More accurately, this hits if ALL input patterns resolved to nothing.
        print("Info: No EPUB files found to process based on the input arguments.", file=sys.stderr)
    # --- END OF MODIFICATION ---


    for epub_file_path_str in actual_epub_files_to_process: # MODIFIED: iterate over expanded list
        epub_file_path = Path(epub_file_path_str).resolve() # Resolve to absolute path for clarity

        if not epub_file_path.exists():
            print(f"Error: EPUB file '{epub_file_path}' not found.", file=sys.stderr)
            failure_count += 1
            continue
        if not epub_file_path.is_file():
            print(f"Error: EPUB path '{epub_file_path}' is not a file.", file=sys.stderr)
            failure_count += 1
            continue

        if epub_file_path.suffix.lower() != '.epub':
            print(f"Warning: File '{epub_file_path}' does not have an .epub extension. Attempting to process anyway.", file=sys.stderr)

        # Determine output path
        txt_filename = epub_file_path.stem + ".txt"
        if output_dir:
            output_txt_path = output_dir / txt_filename
        else:
            output_txt_path = epub_file_path.with_name(txt_filename) # More robust than with_suffix for this

        if output_txt_path.exists() and not args.force:
            print(f"Skipping '{epub_file_path}': Output file '{output_txt_path}' already exists. Use -f to overwrite.", file=sys.stderr)
            # Consider this a "skip" not a failure for summary.
            continue

        if epub_to_text(epub_file_path, output_txt_path):
            success_count += 1
        else:
            failure_count += 1
        print("-" * 20) # Separator for multiple files

    print("\nConversion Summary:")
    print(f"  Successfully converted: {success_count} file(s)")
    print(f"  Failed conversions:   {failure_count} file(s)")
    if failure_count > 0:
        sys.exit(1) # Exit with error code if any failures

if __name__ == "__main__":
    main()