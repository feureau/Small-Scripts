#!/usr/bin/env python3

import sys
import glob
import os

def get_numerical_sort_key(filename):
    """
    Extracts the numerical part from the filename for sorting.
    Assumes the numerical part is between the second and third hyphens.
    If extraction fails or not a number, returns a tuple that ensures
    non-numerical filenames are sorted after numerical ones, while maintaining
    alphabetical order within each group.
    """
    try:
        parts = filename.split('-')
        if len(parts) >= 3:
            numerical_part_str = parts[2]
            try:
                numerical_part = int(numerical_part_str)
                return (numerical_part, filename) # Return tuple for numerical sort primarily
            except ValueError:
                # If the part is not an integer, treat as non-numerical for sorting purposes.
                return (float('inf'), filename) # Tuple with infinity ensures it sorts after numerical ones
    except: # catch any other errors during splitting or indexing
        pass # fall through to return default

    return (float('inf'), filename) # Default to non-numerical sort, and then by filename


def merge_text_files(file_pattern, output_filename="merged_output.txt"):
    """
    Merges all text files matching the given pattern in the current working directory
    into a single output text file, in ascending numerical order of filenames
    based on the number within the filename.

    Args:
        file_pattern (str): The file pattern to match (e.g., "*.txt").
        output_filename (str, optional): The name of the output file.
                                        Defaults to "merged_output.txt".
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
                        outfile.write(infile.read())
                        outfile.write("\n\n")  # Add a separator between files (optional)
                    print(f"  - Merged: {filename}")
                except Exception as e:
                    print(f"  - Error reading file: {filename} - {e}")

        print(f"\nSuccessfully merged files into: {output_filename}")

    except Exception as e:
        print(f"An error occurred: {e}")
        print("Usage: mergetext.py <file_pattern>")
        print("Example: mergetext.py *.txt")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: mergetext.py <file_pattern>")
        print("Example: mergetext.py *.txt")
        sys.exit(1)

    file_pattern = sys.argv[1]
    merge_text_files(file_pattern)