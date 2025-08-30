#!/usr/bin/env python
"""
================================================================================
Command-Line File Sanitizer (sanitizer.py)
================================================================================

Purpose:
--------
A versatile command-line tool to clean text content by removing Markdown code
fences (```) that often surround AI-generated output. The script is designed
to be highly flexible and can operate in three distinct modes: processing piped
input, sanitizing specific files provided as arguments, or automatically
scanning the current directory for all supported file types.

Key Features:
-------------
- Triple-Mode Operation: Can be used seamlessly in command-line pipes, on
  specific files, or in a fully automatic directory-scan mode.
- In-Place File Modification: When operating on files, it directly modifies
  them to apply the sanitization.
- Automatic Backups: For safety, it automatically creates a backup copy
  (e.g., `myfile.txt.bak`) of any file it is about to modify. This feature
  can be disabled with a command-line flag.
- Intelligent Sanitization: Uses a regular expression that correctly handles
  code blocks with or without language identifiers (e.g., ```json or ```).
  It only cleans the file if the *entire content* is wrapped in a code block.
- Configurable File Types: The list of file extensions for the auto-scan mode
  can be easily customized by editing the `SUPPORTED_TEXT_EXTENSIONS` variable.
- Cross-Platform: Built with standard Python libraries, ensuring it runs on
  Windows, macOS, and Linux without modification.
- No Dependencies: Requires only a standard Python 3 installation.

Setup:
------
1. Save this script as `sanitizer.py`.
2. (Recommended) Place the script in a central folder that is included in your
   system's PATH environment variable. This allows you to call `sanitizer.py`
   from any directory without typing the full path to the script.

--------------------------------------------------------------------------------
Usage / Operating Modes
--------------------------------------------------------------------------------

The script will automatically select one of the following modes based on how
it is executed.

---
Mode 1: Processing Piped Input
---
Use this mode to sanitize text streams "on the fly." It reads from standard
input and writes the sanitized result to standard output.

Syntax:
  <command_that_produces_text> | python sanitizer.py

Examples:
  # Sanitize the content of a file and print the result to the terminal
  cat file_to_clean.txt | python sanitizer.py

  # Sanitize a file and save the clean output to a new file
  cat file_to_clean.txt | python sanitizer.py > sanitized_version.txt

---
Mode 2: Processing Specific Files as Arguments
---
Provide one or more file paths as arguments to sanitize only those specific
files. This mode modifies the files in-place and creates backups by default.

Syntax:
  python sanitizer.py [options] <file1> <file2> ...

Examples:
  # Sanitize two specific files in the current directory
  python sanitizer.py report.md notes.txt

  # Sanitize a file located in a different directory
  python sanitizer.py /path/to/data/output.json

---
Mode 3: Automatic Directory Scan
---
If the script is run with no file arguments and no piped input, it will
automatically scan the current directory for all files matching the extensions
defined in the `SUPPORTED_TEXT_EXTENSIONS` list.

Syntax:
  python sanitizer.py [options]

Example:
  # Navigate to a folder and run the script to clean all supported files
  cd /path/to/my/ai_outputs/
  python sanitizer.py

--------------------------------------------------------------------------------
Command-Line Options
--------------------------------------------------------------------------------

  files (positional)
    Zero or more file paths to process. If omitted, triggers Mode 3.

  --no-backup
    Disables the creation of .bak files before modification. Use with caution.

    Example:
      python sanitizer.py --no-backup report.md

--------------------------------------------------------------------------------
Customization
--------------------------------------------------------------------------------

To change which files are processed during the Automatic Directory Scan (Mode 3),
simply add or remove extensions from the `SUPPORTED_TEXT_EXTENSIONS` list
at the top of this script.
"""

import sys
import os
import re
import glob
import argparse
import shutil

# This list defines the file extensions the script will look for
# when scanning a directory.
SUPPORTED_TEXT_EXTENSIONS = ['.txt', '.srt', '.md', '.py', '.js', '.html', '.css']

def sanitize_content(text):
    """
    Removes Markdown code fences from the start and end of a string.
    Handles optional language identifiers like 'json' or 'markdown'.
    If the entire string is not a code block, it returns the original text.
    """
    if not text:
        return ""
    
    # Use re.DOTALL so that '.' matches newline characters
    pattern = re.compile(r"^\s*```[a-z]*\s*\n?(.*?)\n?\s*```\s*$", re.DOTALL)
    
    # We use match() because we only care if the *entire* string is a code block
    match = pattern.match(text.strip())
    
    if match:
        # If it matches, return the captured group (the content inside the fences)
        return match.group(1).strip()
    else:
        # Otherwise, return the original text, just stripped of whitespace
        return text.strip()

def process_file(filepath, create_backup=True):
    """
    Reads a file, sanitizes its content, and overwrites the original file.
    Creates a backup (.bak) by default.
    """
    try:
        if create_backup:
            backup_path = filepath + ".bak"
            shutil.copy2(filepath, backup_path)
            print(f"Sanitizing '{os.path.basename(filepath)}'... (backup created at '{os.path.basename(backup_path)}')")
        else:
            print(f"Sanitizing '{os.path.basename(filepath)}'... (no backup)")

        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            original_content = f.read()
            
        sanitized_content = sanitize_content(original_content)
        
        # Only write back if content has changed to avoid unnecessary modifications
        if sanitized_content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(sanitized_content)
        else:
            print(f"- No changes needed for '{os.path.basename(filepath)}'.")

    except FileNotFoundError:
        print(f"Error: File not found at '{filepath}'", file=sys.stderr)
    except Exception as e:
        print(f"Error processing file '{filepath}': {e}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="Sanitizes text files by removing surrounding Markdown code fences (```). "
                    "Can process piped input, specific files, or all supported files in a directory.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        'files', 
        nargs='*', 
        help='Optional. One or more specific file paths to process.'
    )
    parser.add_argument(
        '--no-backup', 
        action='store_true', 
        help="Disable the creation of .bak backup files before overwriting."
    )
    args = parser.parse_args()

    # --- Mode 1: Process piped input ---
    # sys.stdin.isatty() is True if the script is run in an interactive terminal,
    # and False if it's receiving piped input.
    if not sys.stdin.isatty():
        piped_text = sys.stdin.read()
        sanitized_text = sanitize_content(piped_text)
        print(sanitized_text, end='')
        return

    # --- Mode 2: Process specific files given as arguments ---
    if args.files:
        for f in args.files:
            process_file(f, create_backup=not args.no_backup)
        return

    # --- Mode 3: No other input, so scan the current directory ---
    print("No input detected. Scanning current directory for supported files...")
    found_files = []
    for ext in SUPPORTED_TEXT_EXTENSIONS:
        # We search for '*ext' and '*EXT' to be case-insensitive on some systems
        found_files.extend(glob.glob(f"*{ext}"))
        found_files.extend(glob.glob(f"*{ext.upper()}"))
    
    # Remove duplicates
    unique_files = sorted(list(set(found_files)))

    if not unique_files:
        print("No supported files found in this directory.")
        return
        
    print(f"Found {len(unique_files)} supported files to process.")
    for f in unique_files:
        process_file(f, create_backup=not args.no_backup)

if __name__ == "__main__":
    main()