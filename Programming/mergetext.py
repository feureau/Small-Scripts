#!/usr/bin/env python3

import sys
import glob
import os
import argparse  # Import argparse for argument parsing
import re

def get_numerical_sort_key(filename):
    """
    Extracts the numerical part from the filename for sorting.
    Assumes the numerical part is between 'chunk_' and '_translated'.
    If extraction fails or not a number, returns a tuple that ensures
    non-numerical filenames are sorted after numerical ones, while maintaining
    alphabetical order within each group.
    """
    try:
        start_index = filename.find('chunk_')
        end_index = filename.find('_translated', start_index + len('chunk_'))
        if start_index != -1 and end_index != -1:
            numerical_part_str = filename[start_index + len('chunk_'):end_index]
            try:
                numerical_part = int(numerical_part_str)
                return (numerical_part, filename) # Return tuple for numerical sort primarily
            except ValueError:
                # If the part is not an integer, treat as non-numerical for sorting purposes.
                return (float('inf'), filename) # Tuple with infinity ensures it sorts after numerical ones
    except: # catch any other errors during string operations
        pass # fall through to return default

    return (float('inf'), filename) # Default to non-numerical sort, and then by filename

def remove_default_strings(content):
    """
    Removes default strings '```markdown' and '```' from the content.
    """
    content = content.replace('```markdown', '')
    content = content.replace('```', '')
    return content


def merge_text_files(file_pattern, output_filename="merged_output.txt", add_linebreak=False, strip_linebreaks=False, remove_strings=True):
    """
    Merges all text files matching the given pattern in the current working directory
    into a single output text file, in ascending numerical order of filenames
    based on the number within the filename.

    Args:
        file_pattern (str): The file pattern to match (e.g., "*.txt").
        output_filename (str, optional): The name of the output file.
                                        Defaults to "merged_output.txt".
        add_linebreak (bool, optional):  If True, adds a blank line between merged files.
                                        Defaults to False.
        strip_linebreaks (bool, optional): If True, strips extra linebreaks within paragraphs.
                                        Defaults to False.  Now defaults to False (no strip).
        remove_strings (bool, optional): If True, removes default strings (```markdown and ```).
                                        Defaults to True.
    """
    try:
        # Get a list of files matching the pattern in the current directory
        files_to_merge = glob.glob(file_pattern)

        if not files_to_merge:
            print(f"No files found matching pattern: {file_pattern}")
            return

        # Sort the files list numerically based on the number in filename
        files_to_merge.sort(key=get_numerical_sort_key)

        # Remove 'merged_output.txt' from the list if it's present and not intended to be merged.
        # This prevents merging the output file into itself on subsequent runs if the pattern matches it.
        if output_filename in files_to_merge:
            files_to_merge.remove(output_filename)


        print(f"Merging files in numerical ascending order: {files_to_merge}")

        with open(output_filename, 'w', encoding='utf-8') as outfile:
            for filename in files_to_merge:
                try:
                    with open(filename, 'r', encoding='utf-8') as infile:
                        content = infile.read()

                        if remove_strings:
                            content = remove_default_strings(content)

                        if strip_linebreaks:
                            # Normalize linebreaks: replace multiple newlines with double newlines for paragraph separation
                            content = re.sub(r'\n{3,}', '\n\n', content)
                            # Replace single newlines within paragraphs with spaces
                            paragraphs = content.split('\n\n')
                            processed_paragraphs = []
                            for paragraph in paragraphs:
                                processed_paragraph = paragraph.replace('\n', ' ').strip()
                                processed_paragraphs.append(processed_paragraph)
                            content = '\n\n'.join(processed_paragraphs)

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
    parser = argparse.ArgumentParser(description="Merge text files matching a pattern. By default, it removes '```markdown' and '```' strings and does not strip linebreaks within paragraphs.\nUse --strip to enable stripping linebreaks while maintaining paragraph separation.",
                                     formatter_class=argparse.RawTextHelpFormatter) # for multiline help text
    parser.add_argument("file_pattern", help="The file pattern to match (e.g., '*.txt')")
    parser.add_argument("-lb", "--linebreak", action="store_true", help="Add a blank line between merged files.")
    parser.add_argument("-strip", "--strip", action="store_true", help="Enable stripping of linebreaks within paragraphs.\nWhen used, the script strips extra linebreaks within paragraphs\nand maintains paragraph separation.")
    parser.add_argument("--no-remove-strings", action="store_false", dest="remove_strings", default=True, help="Disable removal of default strings ('```markdown' and '```').")
    # Removed the explicit -h/--help argument causing conflict
    # parser.add_argument("-h", "--help", action="help", help="Show this help message and exit.")

    args = parser.parse_args()

    file_pattern = args.file_pattern
    add_linebreak = args.linebreak  # Get the flag value from arguments
    strip_linebreaks = args.strip # strip_linebreaks is True only if --strip is used, default is False
    remove_strings = args.remove_strings # remove_strings is True by default, can be set to False with --no-remove-strings

    merge_text_files(file_pattern, output_filename="merged_output.txt", add_linebreak=add_linebreak, strip_linebreaks=strip_linebreaks, remove_strings=remove_strings)