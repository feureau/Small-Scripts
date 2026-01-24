
#!/usr/bin/env python3

r"""
================================================================================
 SCRIPT NAME: Advanced Text File Merger
 VERSION: 4.2 (Natural Sorting Fix)
 AUTHOR: Contributor (Patched by ChatGPT, Refactored by Gemini)
 DATE: December 13, 2025
================================================================================

PURPOSE & DESCRIPTION:
----------------------
This script merges multiple text-based files (e.g., .txt, .srt, .md, .log)
into a single, consolidated output file.

NEW IN V4.2:
- Fixed sorting logic. Now uses "Natural Sorting" (alphanumeric split) instead
  of just looking at the last number. This fixes issues where files ending in
  "(1).txt" were incorrectly sorted to the top.
- Fixed SyntaxWarning regarding escape sequences in documentation.

--------------------------------------------------------------------------------
CORE FEATURES:
--------------------------------------------------------------------------------
-   Natural Sorting: Sorts filenames like a human would (e.g., "File 9" comes
    before "File 10", and "Chapter 109 (1)" follows "Chapter 109").
-   Content Sanitization: Automatically removes Markdown code fences
    (e.g., ```text ... ```) that often wrap LLM-generated text.
-   Linebreak & Hyphenation Stripping: Can reflow paragraphs by removing
    mid-sentence line breaks and automatically joining hyphenated words.
-   Customizable Markers: Can insert distinct markers around content.

--------------------------------------------------------------------------------
COMMAND-LINE ARGUMENTS:
--------------------------------------------------------------------------------
-   `file_patterns` (Required): One or more glob patterns.
    Example: `"*.txt" "chapter-*.md"`

-   `-o, --output` (Optional): Output filename.
    Example: `-o "final_document.md"`

-   `-lb, --linebreak` (Optional): Inserts an extra blank line between files.

-   `-r, --recursive` (Optional): Scans subdirectories for matching files.

-   `-strip, --strip` (Optional): Removes single line breaks within paragraphs
    and de-hyphenates words.

-   `-m, --markers` (Optional): Inserts headers/footers around file content.

-   `--no-remove-strings` (Optional): Disables markdown code fence removal.

--------------------------------------------------------------------------------
CONFIGURATION VARIABLES:
--------------------------------------------------------------------------------
-   `MARKER_CHAR`: Character for marker lines (default "=").
-   `MARKER_LENGTH`: Length of marker lines.
-   `START_MARKER_FORMAT`: Template for start marker.
-   `END_MARKER_FORMAT`: Template for end marker.

--------------------------------------------------------------------------------
FUNCTION REFERENCE:
--------------------------------------------------------------------------------
-   `get_numerical_sort_key(filename)`:
    Splits a filename into text and numeric chunks to perform natural sorting.

-   `sanitize_api_response(text)`:
    Cleans text by removing Markdown fences.

-   `merge_text_files(...)`:
    Main orchestration function.
================================================================================
"""

import sys
import glob
import os
import argparse
import re

#================================================================================
# SCRIPT CONFIGURATION
#================================================================================
# --- Section Marker Settings (for -m/--markers flag) ---
MARKER_CHAR = "="
MARKER_LENGTH = 50
START_MARKER_FORMAT = f"\n{MARKER_CHAR * MARKER_LENGTH}\n>> START: {{filename}}\n{MARKER_CHAR * MARKER_LENGTH}\n"
END_MARKER_FORMAT = f"\n{MARKER_CHAR * MARKER_LENGTH}\n>> END OF LINE: {{filename}}\n{MARKER_CHAR * MARKER_LENGTH}\n"

# --- Default Output Settings ---
DEFAULT_OUTPUT_BASENAME = "merged_output"
DEFAULT_OUTPUT_EXTENSION = "txt"

# --- Default Plaintext Extensions (used when no file patterns provided) ---
DEFAULT_PLAINTEXT_EXTENSIONS = [
    "txt", "json", "md", "srt", "log", "csv", "xml", "yaml", "yml",
    "ini", "cfg", "conf", "html", "htm", "css", "js", "py", "sh", "bat"
]
#================================================================================


def get_numerical_sort_key(filename):
    """
    Generates a key for 'Natural Sorting'.
    Splits the filename into a list of integers and lowercase strings.
    This ensures that 'file2.txt' comes before 'file10.txt', and
    'Vol 1 (1).txt' comes after 'Vol 1.txt' if logically appropriate.
    """
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split(r'(\d+)', filename)]


def sanitize_api_response(text):
    """Removes Markdown code fences from the start and end of a string."""
    if not text:
        return ""
    pattern = re.compile(r"^\s*```[a-z]*\s*\n?(.*?)\n?\s*```\s*$", re.DOTALL)
    match = pattern.match(text.strip())
    if match:
        return match.group(1).strip()
    return text.strip()


def merge_text_files(file_patterns, output_filename, add_linebreak=False, strip_linebreaks=False, remove_strings=True, add_markers=False, recursive=False):
    """Merges all text files matching the given patterns into a single output file."""
    try:
        all_files = set()
        for pattern in file_patterns:
            # If recursive is True and pattern doesn't already have recursive syntax, adapt it
            if recursive and '**' not in pattern:
                # Check if it's already a path-like pattern
                if os.path.sep in pattern or '/' in pattern:
                    # It's a path, but might need ** insertion
                    # This is a bit tricky, but simple strategy: replace last segment if it has wildcards
                    dirname, basename = os.path.split(pattern)
                    if '*' in basename:
                        pattern = os.path.join(dirname, '**', basename)
                else:
                    # It's just a glob like *.txt in current dir
                    pattern = os.path.join('**', pattern)

            matched_files = glob.glob(pattern, recursive=recursive)
            all_files.update(matched_files)

        files_to_merge = list(all_files)

        if not files_to_merge:
            print(f"No files found matching patterns: {file_patterns}")
            return

        default_output_file = f"{DEFAULT_OUTPUT_BASENAME}.{DEFAULT_OUTPUT_EXTENSION}"
        # Intelligent output naming if -o is not provided
        if output_filename == default_output_file:
            first_pattern = file_patterns[0]
            pattern_parts = first_pattern.split('.')
            if len(pattern_parts) > 1 and pattern_parts[-1] != '*':
                output_extension = pattern_parts[-1]
                output_filename = f"{DEFAULT_OUTPUT_BASENAME}.{output_extension}"
            else:
                output_filename = default_output_file

        # Apply Natural Sorting
        files_to_merge.sort(key=get_numerical_sort_key)

        # Ensure we don't try to merge the output file into itself
        if output_filename in files_to_merge:
            files_to_merge.remove(output_filename)

        print(f"Merging files in Natural Sort order:")
        for f in files_to_merge:
            print(f"  - {f}")
        print(f"Output file will be: {output_filename}\n")

        with open(output_filename, 'w', encoding='utf-8') as outfile:
            for filename in files_to_merge:
                try:
                    with open(filename, 'r', encoding='utf-8') as infile:
                        content = infile.read()

                        if remove_strings:
                            content = sanitize_api_response(content)

                        if strip_linebreaks:
                            # De-hyphenate words split across lines
                            while True:
                                original_content = content
                                content = re.sub(r'(\w)-\n(\w?)', r'\1\2', content, flags=re.MULTILINE)
                                if content == original_content:
                                    break
                            
                            # Reflow paragraphs
                            content = re.sub(r'\n{2,}', '\n\n', content)
                            content = re.sub(r'(?<!\n)\n(?!\n)', ' ', content)

                        if add_markers:
                            base_name = os.path.basename(filename)
                            outfile.write(START_MARKER_FORMAT.format(filename=base_name))

                        outfile.write(content)

                        if add_markers:
                            base_name = os.path.basename(filename)
                            outfile.write(END_MARKER_FORMAT.format(filename=base_name))

                        if add_linebreak:
                            outfile.write("\n\n")
                        else:
                            if not add_markers:
                                outfile.write("\n")

                    print(f"  ✓ Merged: {filename}")
                except Exception as e:
                    print(f"  ⚠ Error reading file: {filename} - {e}")

        print(f"\n✅ Successfully merged files into: {output_filename}")

    except Exception as e:
        print(f"❌ An error occurred: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Merge text files matching one or more patterns. "
                    "See the extensive documentation at the top of the script for full details.",
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument("file_patterns", nargs='*', help="One or more file patterns to match (e.g., '*.txt', 'chapter-*.md'). If not provided, processes all common plaintext files.")
    parser.add_argument("-o", "--output", default=f"{DEFAULT_OUTPUT_BASENAME}.{DEFAULT_OUTPUT_EXTENSION}", help="Name of the output file (default derives from first pattern).")
    parser.add_argument("-lb", "--linebreak", action="store_true", help="Add a blank line between merged files.")
    parser.add_argument("-r", "--recursive", action="store_true", help="Scan subdirectories for matching files.")
    parser.add_argument("-strip", "--strip", action="store_true", help="Strip linebreaks within paragraphs and join hyphenated words.")
    parser.add_argument("--no-remove-strings", action="store_false", dest="remove_strings", default=True, help="Disable markdown fence removal.")
    parser.add_argument("-m", "--markers", action="store_true", help="Add start and end markers for each merged file's content.")

    args = parser.parse_args()

    # Use default plaintext extensions if no patterns provided
    if not args.file_patterns:
        args.file_patterns = [f"*.{ext}" for ext in DEFAULT_PLAINTEXT_EXTENSIONS]
        print(f"No file patterns specified. Using default plaintext extensions:")
        print(f"  {', '.join(DEFAULT_PLAINTEXT_EXTENSIONS)}\n")

    # Heuristic: If -o wasn't used, and we have multiple patterns, and the last pattern
    # doesn't look like a glob AND doesn't exist as a file, treat it as output.
    # This supports usage like: mergetext.py *.md output.md
    if args.output == f"{DEFAULT_OUTPUT_BASENAME}.{DEFAULT_OUTPUT_EXTENSION}" and len(args.file_patterns) >= 2:
        last_arg = args.file_patterns[-1]
        is_glob = any(char in last_arg for char in "*?[]")
        if not is_glob and not os.path.exists(last_arg):
            print(f"ℹ️  Implicit output detected: '{last_arg}' (treating as output file)")
            args.output = last_arg
            args.file_patterns.pop()

    merge_text_files(
        file_patterns=args.file_patterns,
        output_filename=args.output,
        add_linebreak=args.linebreak,
        strip_linebreaks=args.strip,
        remove_strings=args.remove_strings,
        add_markers=args.markers,
        recursive=args.recursive
    )
