#!/usr/bin/env python3

"""
================================================================================
 SCRIPT NAME: Advanced Text File Merger
 VERSION: 3.3 (Fixed)
 AUTHOR: Contributor (Patched by ChatGPT)
 DATE: October 19, 2025
================================================================================

PURPOSE & DESCRIPTION:
----------------------
Merges multiple text-based files (e.g., .txt, .srt, .md, .log) into a single
output file, sorted numerically by the last number in each filename. Handles
LLM-generated artifacts like Markdown code fences and provides linebreak
clean-up options.

USAGE EXAMPLES:
---------------
1.  Merge all text files:
        python mergetext.py "*.txt"

2.  Merge multiple types:
        python mergetext.py "*.txt" "*.srt"

3.  Specify output file:
        python mergetext.py "*.txt" "*.srt" -o combined.txt

4.  Add blank lines between merged files:
        python mergetext.py "*.txt" -lb

5.  Strip extra linebreaks and hyphenation:
        python mergetext.py "*.txt" -strip
================================================================================
"""

import sys
import glob
import os
import argparse
import re


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


def merge_text_files(file_patterns, output_filename, add_linebreak=False, strip_linebreaks=False, remove_strings=True):
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

        # Correctly determine default output filename if necessary
        if output_filename == "merged_output.txt":
            base_output_name = "merged_output"
            # FIXED: Select the first element from the list, not the list itself
            first_pattern = file_patterns[0]
            pattern_parts = first_pattern.split('.')
            if len(pattern_parts) > 1 and pattern_parts[-1] != '*':
                output_extension = pattern_parts[-1]
                output_filename = f"{base_output_name}.{output_extension}"
            else:
                output_filename = "merged_output.txt"

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

                        outfile.write(content)
                        if add_linebreak:
                            outfile.write("\n\n")
                        else:
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
                    "By default, removes markdown fences (```markdown) that wrap entire files. "
                    "Output extension derives from the first input pattern if not specified with -o.",
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument("file_patterns", nargs='+', help="One or more file patterns to match (e.g., '*.txt', 'chapter-*.md')")
    parser.add_argument("-o", "--output", default="merged_output.txt", help="Name of the output file (default derives from first pattern).")
    parser.add_argument("-lb", "--linebreak", action="store_true", help="Add a blank line between merged files.")
    parser.add_argument("-strip", "--strip", action="store_true", help="Strip linebreaks within paragraphs and join hyphenated words.")
    parser.add_argument("--no-remove-strings", action="store_false", dest="remove_strings", default=True, help="Disable markdown fence removal.")

    args = parser.parse_args()

    merge_text_files(
        file_patterns=args.file_patterns,
        output_filename=args.output,
        add_linebreak=args.linebreak,
        strip_linebreaks=args.strip,
        remove_strings=args.remove_strings
    )
