#!/usr/bin/env python3
"""
txt.py - Universal document to plain text converter.

This script extracts text from various document formats and applies
OSPL (One Sentence Per Line) formatting for readability.

Supported Formats:
- PDF (.pdf)
- EPUB (.epub)
- MOBI / AZW3 (.mobi, .azw, .azw3)
- Word (.docx)
- Text / HTML (.txt, .md, .html, .htm)
"""

import os
import sys
import re
import glob
import argparse
import shutil
from pathlib import Path

# Try importing required libraries
MISSING_LIBS = []
try:
    import fitz  # PyMuPDF
except ImportError:
    MISSING_LIBS.append("pymupdf")

try:
    import nltk
    from nltk.tokenize import sent_tokenize
except ImportError:
    MISSING_LIBS.append("nltk")

try:
    from ebooklib import epub, ITEM_DOCUMENT
except ImportError:
    MISSING_LIBS.append("EbookLib")

try:
    from bs4 import BeautifulSoup
except ImportError:
    MISSING_LIBS.append("beautifulsoup4")

# Optional libraries
try:
    import mobi
    MOBI_AVAILABLE = True
except ImportError:
    MOBI_AVAILABLE = False

try:
    import docx
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

if MISSING_LIBS:
    print(f"Error: Missing required libraries: {', '.join(MISSING_LIBS)}", file=sys.stderr)
    print(f"Please install them using: pip install {' '.join(MISSING_LIBS)}", file=sys.stderr)
    sys.exit(1)

# Ensure NLTK punkt is available
try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    print("Downloading NLTK tokenizer 'punkt'...")
    nltk.download("punkt", quiet=True)


# --- OSPL FORMATTING LOGIC ---

def tokenize_text(text):
    return sent_tokenize(text)

def split_decorative(sentence):
    match = re.search(r'([A-Za-z“"])', sentence)
    if match and match.start() > 0:
        prefix = sentence[:match.start()].rstrip()
        rest = sentence[match.start():].lstrip()
        if prefix:
            return [prefix, rest]
    return [sentence]

def ospl_format_text(text):
    paragraphs = re.split(r'\n\s*\n', text.strip())
    processed_paragraphs = []
    for para in paragraphs:
        if not para.strip():
            continue
        single_line = ' '.join(para.splitlines())
        sentences = tokenize_text(single_line)
        processed_lines = []
        for sentence in sentences:
            for line in split_decorative(sentence):
                processed_lines.append(line)
        processed_paragraphs.append("\n".join(processed_lines))
    return "\n\n".join(processed_paragraphs)

def save_output(output_path, text, force):
    """
    Saves text to output_path. Applies OSPL formatting right before writing.
    """
    output_path = Path(output_path)
    if output_path.exists() and not force:
        print(f"  Skipping: Output '{output_path}' already exists. Use -f to overwrite.", file=sys.stderr)
        return False
    try:
        if text.strip():
            formatted_text = ospl_format_text(text)
        else:
            formatted_text = ""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(formatted_text)
        return True
    except IOError as e:
        print(f"  Error: Could not write to '{output_path}'. {e}", file=sys.stderr)
        return False


# --- FORMAT HANDLERS ---

def process_pdf(file_path, output_dir, split, force):
    file_path = Path(file_path)
    base_name = file_path.stem
    out_dir = Path(output_dir) if output_dir else file_path.parent
    
    try:
        with fitz.open(file_path) as doc:
            if split:
                split_dir = out_dir / base_name
                split_dir.mkdir(parents=True, exist_ok=True)
                
                success = True
                for page_num in range(doc.page_count):
                    page = doc.load_page(page_num)
                    raw_text = page.get_text("text")
                    output_file = split_dir / f"page_{page_num + 1:04d}.txt"
                    if save_output(output_file, raw_text, force):
                        print(f"    -> Page {page_num + 1} saved as {output_file.name}")
                    else:
                        success = False
                if success:
                    print(f"  Successfully split '{file_path.name}' into '{split_dir}'")
                return success
            else:
                full_text = ''.join(page.get_text("text") for page in doc)
                output_file = out_dir / f"{base_name}.txt"
                if save_output(output_file, full_text, force):
                    print(f"  Successfully converted '{file_path.name}' to '{output_file}'")
                    return True
                return False
    except Exception as e:
        print(f"  Error processing PDF '{file_path.name}': {e}", file=sys.stderr)
        return False

def extract_text_from_html(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    for script_or_style in soup(["script", "style"]):
        script_or_style.decompose()
    return soup.get_text(separator='\n', strip=True)

def _process_epub_internal(epub_source, original_file_path, output_dir, split, force):
    original_file_path = Path(original_file_path)
    base_name = original_file_path.stem
    out_dir = Path(output_dir) if output_dir else original_file_path.parent

    try:
        read_options = {'ignore_ncx': True}
        book = epub.read_epub(str(epub_source), options=read_options)
    except Exception as e:
        print(f"  Error: Could not read EPUB '{epub_source}'. {e}", file=sys.stderr)
        return False

    items_to_process = []
    if book.spine:
        for item_id, _ in book.spine:
            item = book.get_item_with_id(item_id)
            if item and item.get_type() == ITEM_DOCUMENT:
                items_to_process.append(item)

    if not items_to_process:
        all_doc_items = list(book.get_items_of_type(ITEM_DOCUMENT))
        if all_doc_items:
            items_to_process = all_doc_items
        else:
            print(f"  Warning: No document items found in '{epub_source}'.", file=sys.stderr)
            output_file = out_dir / f"{base_name}.txt"
            save_output(output_file, "", force)
            return True

    if split:
        split_dir = out_dir / base_name
        split_dir.mkdir(parents=True, exist_ok=True)
        success = True
        
        for i, item in enumerate(items_to_process):
            try:
                html_content = item.get_content()
                if isinstance(html_content, bytes):
                    try:
                        html_content = html_content.decode('utf-8')
                    except UnicodeDecodeError:
                        encoding = item.encoding if item.encoding else 'latin-1'
                        html_content = html_content.decode(encoding, errors='replace')
                
                text = extract_text_from_html(html_content)
                if text.strip():
                    chapter_file = split_dir / f"chapter_{i+1:03d}.txt"
                    if not save_output(chapter_file, text, force):
                        success = False
            except Exception as e:
                print(f"    Warning: Could not process item {item.get_name()}. {e}", file=sys.stderr)
                success = False
        if success:
            print(f"  Successfully split '{original_file_path.name}' into '{split_dir}'")
        return success
    else:
        full_text = []
        for item in items_to_process:
            try:
                html_content = item.get_content()
                if isinstance(html_content, bytes):
                    try:
                        html_content = html_content.decode('utf-8')
                    except UnicodeDecodeError:
                        encoding = item.encoding if item.encoding else 'latin-1'
                        html_content = item.get_content().decode(encoding, errors='replace')
                text = extract_text_from_html(html_content)
                if text.strip():
                    full_text.append(text)
            except Exception as e:
                print(f"    Warning: Could not process item {item.get_name()}. {e}", file=sys.stderr)
                
        output_file = out_dir / f"{base_name}.txt"
        if save_output(output_file, "\n\n".join(full_text), force):
            print(f"  Successfully converted '{original_file_path.name}' to '{output_file}'")
            return True
        return False

def process_epub(file_path, output_dir, split, force):
    return _process_epub_internal(file_path, file_path, output_dir, split, force)

def process_mobi(file_path, output_dir, split, force):
    if not MOBI_AVAILABLE:
        print(f"  Error: The 'mobi' library is not installed. Cannot process '{file_path.name}'.", file=sys.stderr)
        print("  Install it via: pip install mobi", file=sys.stderr)
        return False
    
    file_path = Path(file_path)
    base_name = file_path.stem
    out_dir = Path(output_dir) if output_dir else file_path.parent

    print(f"  Unpacking {file_path.suffix} file...")
    tempdir = None
    try:
        tempdir, extracted_path = mobi.extract(str(file_path))
        extracted_path = Path(extracted_path)
        
        if extracted_path.suffix.lower() == '.epub':
            print("  Extracted to EPUB. Processing as EPUB...")
            return _process_epub_internal(extracted_path, file_path, output_dir, split, force)
        elif extracted_path.suffix.lower() in ['.html', '.htm']:
            print("  Extracted to HTML. Processing HTML...")
            with open(extracted_path, 'r', encoding='utf-8', errors='replace') as f:
                html_content = f.read()
            text = extract_text_from_html(html_content)
            
            if split:
                split_dir = out_dir / base_name
                split_dir.mkdir(parents=True, exist_ok=True)
                output_file = split_dir / f"document_001.txt"
            else:
                output_file = out_dir / f"{base_name}.txt"
            
            if save_output(output_file, text, force):
                print(f"  Successfully converted '{file_path.name}' to '{output_file}'")
                return True
            return False
        else:
            print(f"  Error: Unrecognized unpacked format '{extracted_path.suffix}' for '{file_path.name}'.", file=sys.stderr)
            return False
    except Exception as e:
        print(f"  Error extracting mobi/azw3 '{file_path.name}': {e}", file=sys.stderr)
        return False
    finally:
        if tempdir and Path(tempdir).exists():
            shutil.rmtree(tempdir, ignore_errors=True)

def process_docx(file_path, output_dir, split, force):
    if not DOCX_AVAILABLE:
        print(f"  Error: The 'python-docx' library is not installed. Cannot process '{file_path.name}'.", file=sys.stderr)
        print("  Install it via: pip install python-docx", file=sys.stderr)
        return False
    
    file_path = Path(file_path)
    base_name = file_path.stem
    out_dir = Path(output_dir) if output_dir else file_path.parent

    try:
        doc = docx.Document(file_path)
        full_text = []
        for para in doc.paragraphs:
            if para.text.strip():
                full_text.append(para.text)
                
        if split:
            split_dir = out_dir / base_name
            split_dir.mkdir(parents=True, exist_ok=True)
            output_file = split_dir / f"document.txt"
        else:
            output_file = out_dir / f"{base_name}.txt"
            
        if save_output(output_file, "\n\n".join(full_text), force):
            print(f"  Successfully converted '{file_path.name}' to '{output_file}'")
            return True
        return False
    except Exception as e:
        print(f"  Error processing DOCX '{file_path.name}': {e}", file=sys.stderr)
        return False

def process_text_or_html(file_path, output_dir, split, force):
    file_path = Path(file_path)
    base_name = file_path.stem
    out_dir = Path(output_dir) if output_dir else file_path.parent

    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
            
        if file_path.suffix.lower() in ['.html', '.htm']:
            text = extract_text_from_html(content)
        else:
            text = content
            
        if split:
            split_dir = out_dir / base_name
            split_dir.mkdir(parents=True, exist_ok=True)
            output_file = split_dir / f"document.txt"
        else:
            output_file = out_dir / f"{base_name}.txt"
            
        if save_output(output_file, text, force):
            print(f"  Successfully converted '{file_path.name}' to '{output_file}'")
            return True
        return False
    except Exception as e:
        print(f"  Error processing '{file_path.name}': {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Universal document to plain text converter with OSPL formatting.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=(
            "Supported formats:\n"
            "  - .pdf\n"
            "  - .epub\n"
            "  - .mobi, .azw, .azw3 (requires 'mobi' package)\n"
            "  - .docx (requires 'python-docx' package)\n"
            "  - .txt, .md, .html, .htm\n\n"
            "Examples:\n"
            "  python txt.py \"*.epub\"              # Convert all EPUBs in current directory\n"
            "  python txt.py doc.pdf -s            # Convert PDF and split into pages\n"
            "  python txt.py book.mobi -o out_dir  # Convert MOBI and save to out_dir"
        )
    )
    parser.add_argument("files", nargs='+', help="Path(s) to one or more files or glob pattern(s) to convert.")
    parser.add_argument("-o", "--output-dir", help="Directory to save the TXT files.")
    parser.add_argument("-f", "--force", action="store_true", help="Overwrite output TXT file or directory if it already exists.")
    parser.add_argument("-s", "--split", action="store_true", help="Split output (e.g., one file per PDF page, or per EPUB chapter).")
    
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
        output_dir = None

    actual_files = []
    for pattern in args.files:
        expanded = glob.glob(pattern)
        if not expanded:
            if any(c in pattern for c in ['*', '?', '[', ']']):
                print(f"Warning: The pattern '{pattern}' did not match any files.", file=sys.stderr)
            else:
                actual_files.append(pattern)
        else:
            actual_files.extend(expanded)

    if not actual_files:
        print("Info: No files found to process.", file=sys.stderr)
        sys.exit(0)

    success_count = 0
    failure_count = 0

    for file_str in actual_files:
        file_path = Path(file_str).resolve()
        
        if not file_path.exists() or not file_path.is_file():
            print(f"Error: File '{file_path}' not found or is not a file.", file=sys.stderr)
            failure_count += 1
            continue
            
        ext = file_path.suffix.lower()
        print(f"Processing '{file_path.name}'...")
        
        if ext == '.pdf':
            success = process_pdf(file_path, output_dir, args.split, args.force)
        elif ext == '.epub':
            success = process_epub(file_path, output_dir, args.split, args.force)
        elif ext in ['.mobi', '.azw', '.azw3']:
            success = process_mobi(file_path, output_dir, args.split, args.force)
        elif ext == '.docx':
            success = process_docx(file_path, output_dir, args.split, args.force)
        elif ext in ['.txt', '.md', '.html', '.htm']:
            success = process_text_or_html(file_path, output_dir, args.split, args.force)
        else:
            print(f"Warning: Unrecognized extension '{ext}' for '{file_path.name}'. Attempting as plain text.", file=sys.stderr)
            success = process_text_or_html(file_path, output_dir, args.split, args.force)

        if success:
            success_count += 1
        else:
            failure_count += 1
        print("-" * 20)

    print("\nConversion Summary:")
    print(f"  Successfully converted: {success_count} file(s)")
    print(f"  Failed conversions:   {failure_count} file(s)")
    if failure_count > 0:
        sys.exit(1)

if __name__ == "__main__":
    main()
