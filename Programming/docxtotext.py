# docxtotext.py

import sys
import glob
import os
from docx import Document # Requires python-docx library

def convert_docx_to_md(docx_path):
    """
    Converts a single DOCX file's text content to a Markdown formatted string.
    Includes basic paragraph separation (double newline).
    Does NOT convert complex formatting (headings, lists, tables, etc.).
    """
    try:
        document = Document(docx_path)
        
        # Extract text content, joining paragraphs with double newlines
        # This mimics how paragraphs are often represented in simple Markdown text
        markdown_content = "\n\n".join([paragraph.text for paragraph in document.paragraphs])
        
        return markdown_content
    except Exception as e:
        print(f"Error processing {docx_path}: {e}")
        return None

def main():
    """
    Main function to process command-line arguments and convert files.
    """
    # sys.argv[0] is the script name
    # sys.argv[1] should be the glob pattern (e.g., *.docx)
    if len(sys.argv) < 2:
        print("Usage: python /path/to/docxtotext.py <glob_pattern>")
        print("Example: python /opt/scripts/docxtotext.py *.docx")
        sys.exit(1)

    # The glob pattern is the first command-line argument
    glob_pattern = sys.argv[1]

    # glob.glob finds files matching the pattern in the *current working directory*
    # where the script is *called* from, not where the script file itself is located.
    docx_files = glob.glob(glob_pattern)

    if not docx_files:
        print(f"No files found matching '{glob_pattern}' in the current directory.")
        sys.exit(0) # Exit successfully, just nothing to do

    print(f"Found {len(docx_files)} file(s) matching '{glob_pattern}'.")

    processed_count = 0
    for docx_file in docx_files:
        # Basic check if it's likely a docx file and actually a file
        if os.path.isfile(docx_file) and docx_file.lower().endswith('.docx'):
            print(f"Converting '{docx_file}'...")

            markdown_content = convert_docx_to_md(docx_file)

            if markdown_content is not None:
                # Create the output filename by changing the extension to .md
                base_name, _ = os.path.splitext(docx_file)
                markdown_file = base_name + '.md'

                try:
                    # Write the markdown content to the new file
                    # Use utf-8 encoding to handle various characters
                    with open(markdown_file, 'w', encoding='utf-8') as f:
                        f.write(markdown_content)
                    print(f"Successfully created '{markdown_file}'.")
                    processed_count += 1
                except Exception as e:
                    print(f"Error writing to file '{markdown_file}': {e}")
            # If markdown_content is None, an error was already printed by convert_docx_to_md
        else:
            print(f"Skipping '{docx_file}' as it doesn't seem to be a .docx file or is not a regular file.")

    print("-" * 20)
    print(f"Finished processing. Successfully converted {processed_count} file(s).")

# This ensures the main function is called when the script is executed directly
if __name__ == "__main__":
    main()