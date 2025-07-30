#!/usr/bin/env python3
"""
Pandoc Batch Converter Script
============================

A Python script to convert multiple files between various document formats using pandoc.
This script uses pypandoc (Python wrapper for pandoc) to perform batch conversions.

Requirements:
-------------
- Python 3.x
- pypandoc: pip install pypandoc
- pandoc executable (will be downloaded automatically if missing)

Features:
---------
- Batch convert multiple files using glob patterns
- Support for various input and output formats
- Automatic pandoc installation if missing
- Progress reporting and error handling
- Cross-platform compatibility

Usage Examples:
--------------
1. Convert all markdown files to docx:
   python pandoc_converter.py "*.md" docx

2. Convert all text files to PDF:
   python pandoc_converter.py "*.txt" pdf

3. Convert files with specific pattern to HTML:
   python pandoc_converter.py "chapter*.md" html

4. Convert a single file:
   python pandoc_converter.py "document.md" epub

5. Convert all supported files in current directory to docx:
   python pandoc_converter.py "*" docx

Supported Input Formats:
-----------------------
.md, .markdown, .txt, .html, .htm, .rst, .tex, .latex, .doc, .docx, .odt

Supported Output Formats:
------------------------
docx, pdf, html, epub, odt, rst, markdown, txt, latex, etc.

Notes:
------
- The script will automatically download pandoc if it's not found
- Output files are created in the same directory as input files
- Existing files with the same name will be overwritten
- Use quotes around patterns with wildcards to prevent shell expansion

Author: Assistant
Version: 1.0
License: MIT
"""

import pypandoc
import sys
import os
import glob
from pathlib import Path

def ensure_pandoc():
    """
    Ensure pandoc is available by either finding an existing installation
    or downloading it automatically.
    
    Returns:
        bool: True if pandoc is available, False otherwise
    """
    try:
        # Try to ensure pandoc is installed
        pypandoc.ensure_pandoc_installed()
        print("✓ Pandoc is ready!")
        return True
    except Exception as e:
        print(f"! Pandoc not found: {e}")
        print("Attempting to download pandoc automatically...")
        try:
            pypandoc.download_pandoc()
            print("✓ Pandoc downloaded successfully!")
            return True
        except Exception as e2:
            print(f"✗ Failed to download pandoc: {e2}")
            print("\nPlease install pandoc manually:")
            print("- Visit: https://pandoc.org/installing.html")
            print("- Or run: conda install -c conda-forge pandoc")
            return False

def convert_files(input_pattern, output_format='docx'):
    """
    Convert files matching the input pattern to the specified format.
    
    Args:
        input_pattern (str): File pattern to match (e.g., "*.md", "file.txt")
        output_format (str): Target format for conversion (default: 'docx')
    """
    # First ensure pandoc is available
    if not ensure_pandoc():
        print("Cannot proceed without pandoc")
        return
    
    # Expand the pattern to get all matching files
    files = []
    if '*' in input_pattern or '?' in input_pattern or '[' in input_pattern:
        # Handle glob patterns
        files = glob.glob(input_pattern)
    else:
        # Handle single file or direct path
        path = Path(input_pattern)
        if path.is_file():
            files = [str(path)]
        elif path.is_dir():
            # If it's a directory, get all files in it
            files = [str(f) for f in path.iterdir() if f.is_file()]
        else:
            # Try glob anyway
            files = glob.glob(input_pattern)
    
    if not files:
        print(f"No files found matching pattern: {input_pattern}")
        return
    
    print(f"Found {len(files)} files to convert")
    
    # Supported input formats (common ones)
    supported_extensions = {
        '.md', '.markdown', '.txt', '.html', '.htm', '.rst', '.tex', '.latex',
        '.doc', '.docx', '.odt', '.pdf'
    }
    
    converted_count = 0
    failed_count = 0
    
    for file_path in files:
        try:
            file_path = Path(file_path)
            
            # Check if file exists
            if not file_path.exists():
                print(f"File not found: {file_path}")
                failed_count += 1
                continue
            
            # Check if it's a supported format
            if file_path.suffix.lower() not in supported_extensions:
                print(f"Skipping unsupported file type: {file_path}")
                continue
            
            # Generate output filename
            output_filename = file_path.with_suffix(f'.{output_format}')
            
            # Convert the file
            print(f"Converting {file_path.name} to {output_filename.name}...")
            pypandoc.convert_file(str(file_path), output_format, outputfile=str(output_filename))
            converted_count += 1
            print(f"  ✓ Success")
            
        except Exception as e:
            print(f"  ✗ Failed to convert {file_path}: {str(e)}")
            failed_count += 1
    
    print(f"\nConversion complete!")
    print(f"Successfully converted: {converted_count}")
    print(f"Failed: {failed_count}")

def show_help():
    """Display help information."""
    help_text = """
Pandoc Batch Converter
=====================

Usage: python pandoc_converter.py [input_pattern] [output_format]

Arguments:
  input_pattern    Pattern to match input files (use quotes for wildcards)
  output_format    Target format (docx, pdf, html, etc.) - default: docx

Examples:
  python pandoc_converter.py "*.md" docx          # Convert all .md files to .docx
  python pandoc_converter.py "chapter*.txt" pdf   # Convert txt files starting with 'chapter' to pdf
  python pandoc_converter.py "document.md" html   # Convert single file to html
  python pandoc_converter.py "*.rst"              # Convert all .rst files to .docx (default)
  python pandoc_converter.py "*" docx             # Convert all supported files to docx

Supported input formats: 
  .md, .markdown, .txt, .html, .htm, .rst, .tex, .latex, .doc, .docx, .odt, .pdf

Supported output formats:
  docx, pdf, html, epub, odt, rst, markdown, txt, latex, etc.

Notes:
  - Use quotes around patterns with wildcards
  - Output files are created in the same directory as input files
  - Existing files will be overwritten
"""
    print(help_text)

def main():
    """Main function to handle command line arguments and start conversion."""
    if len(sys.argv) < 2:
        show_help()
        return
    
    # Handle help flags
    if sys.argv[1] in ['-h', '--help', 'help']:
        show_help()
        return
    
    input_pattern = sys.argv[1]
    output_format = sys.argv[2] if len(sys.argv) > 2 else 'docx'
    
    convert_files(input_pattern, output_format)

if __name__ == "__main__":
    main()