import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import os
import sys  # Import the sys module

def split_epub_to_chapters(epub_filepath, output_dir):
    """
    Splits an EPUB file into individual chapter TXT files.

    Args:
        epub_filepath (str): Path to the EPUB file.
        output_dir (str): Directory to save the chapter TXT files.
    """

    try:
        book = epub.read_epub(epub_filepath)
    except FileNotFoundError:
        print(f"Error: EPUB file not found at '{epub_filepath}'")
        return
    except Exception as e:
        print(f"Error reading EPUB file: {e}")
        return

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    chapter_count = 1
    for item in book.spine:  # Iterate through items in the spine (reading order)
        item_id = item[0]
        item_type = item[1] # 'yes' likely means it's part of the reading flow

        if item_type == 'yes': # Process items that are part of the reading flow
            chapter_item = book.get_item_with_id(item_id)
            if chapter_item:
                if chapter_item.get_type() == ebooklib.ITEM_DOCUMENT: # Ensure it's a document (HTML/XHTML)
                    chapter_content = chapter_item.get_content()
                    soup = BeautifulSoup(chapter_content, 'html.parser')

                    # Extract text from the HTML content (you might need to adjust this)
                    chapter_text = soup.get_text(separator='\n', strip=True)

                    output_filename = f"chapter_{chapter_count:03d}.txt" # Format as chapter_001.txt, etc.
                    output_filepath = os.path.join(output_dir, output_filename)

                    with open(output_filepath, 'w', encoding='utf-8') as outfile:
                        outfile.write(chapter_text)

                    print(f"Saved chapter {chapter_count} to {output_filepath}")
                    chapter_count += 1

    print("EPUB splitting complete.")


if __name__ == "__main__":
    if len(sys.argv) != 2:  # Check if exactly one argument (epub file path) is provided
        print("Usage: python epubsplitter.py <epub_file_path>")
        sys.exit(1)  # Exit with an error code

    epub_file = sys.argv[1]  # Get the epub file path from the command line
    output_directory = "output_chapters"  # Directory to save TXT files (can keep this hardcoded or make it another argument)

    split_epub_to_chapters(epub_file, output_directory)
    print(f"Chapters saved to: {output_directory}")