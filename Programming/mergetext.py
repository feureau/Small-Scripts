#!/usr/bin/env python3

"""
================================================================================
 SCRIPT NAME: Advanced Text File Merger
 VERSION: 4.1 (UI Improvement)
 AUTHOR: Contributor (Patched by ChatGPT, Refactored by Gemini)
 DATE: October 22, 2025
================================================================================

PURPOSE & DESCRIPTION:
----------------------
This script merges multiple text-based files (e.g., .txt, .srt, .md, .log)
into a single, consolidated output file. It is designed with several advanced
features to handle common text processing tasks, such as intelligent numerical
sorting of filenames, cleaning up LLM-generated artifacts, and re-flowing
paragraph line breaks.

The script is highly configurable via the CONFIGURATION section below and
controllable via a rich set of command-line arguments.

NEW IN V4.1:
- Changed the -H/--headers flag to -m/--markers to avoid any potential
  conflict or confusion with the standard -h/--help flag.

--------------------------------------------------------------------------------
CORE FEATURES:
--------------------------------------------------------------------------------
-   Numerical Sorting: Sorts input files based on the last number found in
    each filename, ensuring `chapter-2.txt` comes before `chapter-10.txt`.
-   Content Sanitization: Automatically removes Markdown code fences
    (e.g., ```text ... ```) that often wrap LLM-generated text.
-   Linebreak & Hyphenation Stripping: Can reflow paragraphs by removing
    mid-sentence line breaks and automatically joining hyphenated words
    that were split across lines.
-   Customizable Markers: Can insert distinct, configurable markers (headers
    and footers) around the content of each merged file, clearly marking
    where each original file's content begins and ends.
-   Multi-Pattern Input: Accepts multiple file patterns at once (e.g.,
    "*.txt", "*.md").

--------------------------------------------------------------------------------
COMMAND-LINE ARGUMENTS:
--------------------------------------------------------------------------------
-   `file_patterns` (Required): One or more glob patterns (wildcard paths)
    used to find the files to merge. Must be enclosed in quotes if they
    contain wildcards.
    Example: `"*.txt" "chapter-*.md"`

-   `-o, --output` (Optional): Specifies the name of the final merged file.
    If not provided, a default name is generated based on the configuration
    variables `DEFAULT_OUTPUT_BASENAME` and the extension of the *first*
    file pattern.
    Example: `-o "final_document.md"`

-   `-lb, --linebreak` (Optional): Inserts an extra blank line between the
    contents of each merged file. Provides simple visual separation.

-   `-strip, --strip` (Optional): A powerful text-cleaning option that
    removes single line breaks within paragraphs and de-hyphenates words
    split across lines. Ideal for cleaning up copied/pasted text.

-   `-m, --markers` (Optional): Activates the insertion of formatted start
    and end markers around each file's content. The format of these is
    controlled by the configuration variables below.

-   `--no-remove-strings` (Optional): Disables the automatic removal of
    Markdown code fences. Use this if your source files legitimately use
    these fences and you want to preserve them.

--------------------------------------------------------------------------------
CONFIGURATION VARIABLES:
--------------------------------------------------------------------------------
The variables in the SCRIPT CONFIGURATION section below allow you to customize
the script's behavior without editing the core logic.

-   `MARKER_CHAR`: The character used to draw the horizontal lines in the
    markers (e.g., "=", "-", "*").
-   `MARKER_LENGTH`: The number of characters in each horizontal line.
-   `START_MARKER_FORMAT`: The f-string template for the marker that appears
    *before* each file's content. Must contain `{filename}`.
-   `END_MARKER_FORMAT`: The f-string template for the marker that appears
    *after* each file's content. Must contain `{filename}`.
-   `DEFAULT_OUTPUT_BASENAME`: The base name for the output file if `-o` is
    not specified.
-   `DEFAULT_OUTPUT_EXTENSION`: The fallback extension for the output file if
    it cannot be determined from the input patterns.

--------------------------------------------------------------------------------
FUNCTION REFERENCE:
--------------------------------------------------------------------------------
-   `get_numerical_sort_key(filename)`:
    The custom sorting key for the script. It uses a regular expression
    `r'\d+'` to find all sequences of digits in a filename, extracts the
    *last* one, and converts it to an integer for sorting. Files without
    numbers are placed at the end.

-   `sanitize_api_response(text)`:
    Cleans text by removing Markdown fences. The regex `r"^\s*```[a-z]*\s*
    \n?(.*?)\n?\s*```\s*$"` finds and extracts the content from within a
    code block that spans the entire string.

-   `merge_text_files(...)`:
    The main function that orchestrates the entire process. It gathers files,
    sorts them, and iterates through them, applying the selected processing
    options (stripping, markers, etc.) before writing to the output file.
    The hyphenation-stripping regex `r'(\w)-\n(\w?)'` finds a word character
    followed by a hyphen and a newline, and joins it with the word character
    on the next line. The paragraph-reflowing regex `r'(?<!\n)\n(?!\n)'`
    finds single newlines and replaces them with a space.

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
#================================================================================


def get_numerical_sort_key(filename):
    """Extracts the LAST numerical part from ANY filename for sorting."""
    try:
        numerical_parts_str = re.findall(r'\d+', filename)
        if numerical_parts_str:
            last_numerical_part_str = numerical_parts_str[-1]
            try:
                numerical_part = int(last_numerical_part_str)
                return (numerical_part, filename)
            except ValueError:
                return (float('inf'), filename)
        else:
            return (float('inf'), filename)
    except:
        return (float('inf'), filename)


def sanitize_api_response(text):
    """Removes Markdown code fences from the start and end of a string."""
    if not text:
        return ""
    pattern = re.compile(r"^\s*```[a-z]*\s*\n?(.*?)\n?\s*```\s*$", re.DOTALL)
    match = pattern.match(text.strip())
    if match:
        return match.group(1).strip()
    return text.strip()


def merge_text_files(file_patterns, output_filename, add_linebreak=False, strip_linebreaks=False, remove_strings=True, add_markers=False):
    """Merges all text files matching the given patterns into a single output file."""
    try:
        all_files = set()
        for pattern in file_patterns:
            matched_files = glob.glob(pattern)
            all_files.update(matched_files)

        files_to_merge = list(all_files)

        if not files_to_merge:
            print(f"No files found matching patterns: {file_patterns}")
            return

        default_output_file = f"{DEFAULT_OUTPUT_BASENAME}.{DEFAULT_OUTPUT_EXTENSION}"
        if output_filename == default_output_file:
            first_pattern = file_patterns[0]
            pattern_parts = first_pattern.split('.')
            if len(pattern_parts) > 1 and pattern_parts[-1] != '*':
                output_extension = pattern_parts[-1]
                output_filename = f"{DEFAULT_OUTPUT_BASENAME}.{output_extension}"
            else:
                output_filename = default_output_file

        files_to_merge.sort(key=get_numerical_sort_key)

        if output_filename in files_to_merge:
            files_to_merge.remove(output_filename)

        print(f"Merging files in numerical ascending order (by last number in filename):")
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
                            while True:
                                original_content = content
                                content = re.sub(r'(\w)-\n(\w?)', r'\1\2', content, flags=re.MULTILINE)
                                if content == original_content:
                                    break

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

    parser.add_argument("file_patterns", nargs='+', help="One or more file patterns to match (e.g., '*.txt', 'chapter-*.md')")
    parser.add_argument("-o", "--output", default=f"{DEFAULT_OUTPUT_BASENAME}.{DEFAULT_OUTPUT_EXTENSION}", help="Name of the output file (default derives from first pattern).")
    parser.add_argument("-lb", "--linebreak", action="store_true", help="Add a blank line between merged files.")
    parser.add_argument("-strip", "--strip", action="store_true", help="Strip linebreaks within paragraphs and join hyphenated words.")
    parser.add_argument("--no-remove-strings", action="store_false", dest="remove_strings", default=True, help="Disable markdown fence removal.")
    parser.add_argument("-m", "--markers", action="store_true", help="Add start and end markers for each merged file's content.")

    args = parser.parse_args()

    merge_text_files(
        file_patterns=args.file_patterns,
        output_filename=args.output,
        add_linebreak=args.linebreak,
        strip_linebreaks=args.strip,
        remove_strings=args.remove_strings,
        add_markers=args.markers
    )