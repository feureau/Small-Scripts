#!/usr/bin/env python3

import sys
import glob
import os
import argparse  # Import argparse for argument parsing
import re

def get_numerical_sort_key(filename):
    """
    Extracts the LAST numerical part from ANY filename for sorting.
    Uses regular expressions to find all sequences of digits and takes the last one.
    If extraction fails or not a number, returns a tuple that ensures
    non-numerical filenames are sorted after numerical ones, while maintaining
    alphabetical order within each group.
    """
    try:
        numerical_parts_str = re.findall(r'\d+', filename) # Find ALL sequences of digits
        if numerical_parts_str:
            last_numerical_part_str = numerical_parts_str[-1] # Get the last one from the list
            try:
                numerical_part = int(last_numerical_part_str)
                return (numerical_part, filename) # Return tuple for numerical sort primarily
            except ValueError:
                # If the part is not an integer (shouldn't happen with \d+, but for robustness)
                return (float('inf'), filename) # Treat as non-numerical
        else:
            # No numerical part found
            return (float('inf'), filename) # Treat as non-numerical
    except: # Catch any errors during regex or string operations
        return (float('inf'), filename) # Default to non-numerical


def remove_default_strings(content):
    """
    Removes default strings '```markdown' and '```' from the content.
    """
    content = content.replace('```markdown', '')
    content = content.replace('```', '')
    return content


def merge_text_files(file_pattern, output_filename, add_linebreak=False, strip_linebreaks=False, remove_strings=True):
    """
    Merges all text files matching the given pattern in the current working directory
    into a single output text file, in ascending numerical order of filenames
    based on the LAST number within the filename. The output file extension
    will be the same as the input file extension if not explicitly specified.

    Args:
        file_pattern (str): The file pattern to match (e.g., "*.txt").
        output_filename (str): The name of the output file. If None, defaults to "merged_output.txt",
                                     but the extension will be derived from the input file pattern.
        add_linebreak (bool, optional):  If True, adds a blank line between merged files.
                                        Defaults to False.
        strip_linebreaks (bool, optional): If True, enables stripping of linebreaks within paragraphs,
                                        joining hyphenated words split across lines. Replaces single newlines
                                        within paragraphs with spaces, joins hyphenated words split across lines,
                                        and normalizes multiple newlines to paragraph breaks. Defaults to False.
        remove_strings (bool, optional): If True, removes default strings (```markdown and ```).
                                        Defaults to True.
    """
    try:
        # Get a list of files matching the pattern in the current directory
        files_to_merge = glob.glob(file_pattern)

        if not files_to_merge:
            print(f"No files found matching pattern: {file_pattern}")
            return

        # Determine output extension from file_pattern if output_filename is not provided or is still default
        if output_filename is None or output_filename == "merged_output.txt":
            base_output_name = "merged_output"
            pattern_parts = file_pattern.split('.')
            if len(pattern_parts) > 1:
                output_extension = pattern_parts[-1] # Take the last part after the dot as extension
                output_filename = f"{base_output_name}.{output_extension}"
            else:
                output_filename = "merged_output.txt" # Default to .txt if no extension in pattern
        elif output_filename: # if output_filename is provided from command line, use it as is
            pass # use the provided output_filename

        # Sort the files list numerically based on the LAST number in filename
        files_to_merge.sort(key=get_numerical_sort_key)

        # Remove the automatically named 'merged_output.ext' or user provided output_filename from the list if it's present and not intended to be merged.
        # This prevents merging the output file into itself on subsequent runs if the pattern matches it.
        if output_filename in files_to_merge:
            files_to_merge.remove(output_filename)


        print(f"Merging files in numerical ascending order (by last number in filename): {files_to_merge}")
        print(f"Output file will be: {output_filename}")

        with open(output_filename, 'w', encoding='utf-8') as outfile:
            for filename in files_to_merge:
                try:
                    with open(filename, 'r', encoding='utf-8') as infile:
                        content = infile.read()

                        if remove_strings:
                            content = remove_default_strings(content)

                        if strip_linebreaks:
                            # 1. Join hyphenated words across lines
                            while True: # Loop to handle multiple hyphenated words in sequence
                                original_content = content
                                content = re.sub(r'(\w)-\n(\w?)', r'\1\2', content, flags=re.MULTILINE)
                                if content == original_content: # No more hyphenated words found in this pass
                                    break

                            # 2. Normalize paragraph breaks (ensure double newlines for paragraphs)
                            content = re.sub(r'\n{2,}', '\n\n', content)

                            # 3. Remove single newlines within paragraphs (replace with spaces)
                            content = re.sub(r'(?<!\n)\n(?!\n)', ' ', content)


                        outfile.write(content)
                        if add_linebreak:
                            outfile.write("\n\n")  # Add a separator (blank line) if the flag is set
                        else:
                            outfile.write("\n") # Add a separator (newline)

                    print(f"  - Merged: {filename}")
                except Exception as e:
                    print(f"  - Error reading file: {filename} - {e}")

        print(f"\nSuccessfully merged files into: {output_filename}")

    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Merge text files matching a pattern. By default, it removes '```markdown' and '```' strings and does not strip linebreaks within paragraphs.\nOutput file extension is the same as input extension by default (e.g., merged_output.md for '*.md').\nFilenames are sorted based on the LAST number found in the filename.\nYou can specify the output filename as a second positional argument after the file pattern, or using -o/--output.",
                                     formatter_class=argparse.RawTextHelpFormatter) # for multiline help text
    parser.add_argument("file_pattern", help="The file pattern to match (e.g., '*.txt', '*.md')")
    parser.add_argument("output_filename_pos", nargs='?', default=None, help="Optional output filename. If provided, overrides default output name and -o/--output.") # Positional argument for output filename
    parser.add_argument("-o", "--output", default="merged_output.txt", help="The name of the output file (default: merged_output.txt, extension derived from input pattern if not specified). Positional output filename argument takes precedence.")
    parser.add_argument("-lb", "--linebreak", action="store_true", help="Add a blank line between merged files.")
    parser.add_argument("-strip", "--strip", action="store_true", help="Enable stripping of linebreaks within paragraphs, joining hyphenated words.\nReplaces single newlines within paragraphs with spaces, joins hyphenated\nwords split across lines, and normalizes multiple newlines to paragraph breaks.")
    parser.add_argument("--no-remove-strings", action="store_false", dest="remove_strings", default=True, help="Disable removal of '```markdown' and '```' strings.")

    args = parser.parse_args()

    file_pattern = args.file_pattern
    # Determine output filename priority: positional arg > -o/--output > default/derived
    output_filename = args.output_filename_pos if args.output_filename_pos else args.output
    add_linebreak = args.linebreak
    strip_linebreaks = args.strip
    remove_strings = args.remove_strings

    merge_text_files(file_pattern, output_filename=output_filename, add_linebreak=add_linebreak, strip_linebreaks=strip_linebreaks, remove_strings=remove_strings)