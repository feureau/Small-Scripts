import os
import sys
import re
from pathlib import Path
from glob import glob
from datetime import datetime

def remove_timestamps_and_merge(files, output_file):
    """
    Process and merge text files, removing timestamps and line numbers.
    Timestamps are typically in the format HH:MM:SS or HH:MM:SS,mmm
    SRT numbering lines are purely numeric (1, 2, 3, ...).
    """
    print(f"DEBUG: Files to process: {[file.name for file in files]}")  # Debugging output

    # Regex for timestamps like "00:01:23" or "00:01:23,456"
    timestamp_pattern = re.compile(r'\b\d{2}:\d{2}:\d{2}(?:,\d{3})?\b')
    # Regex for lines that consist purely of digits (e.g., 1, 2, 300, etc.)
    line_number_pattern = re.compile(r'^\d+$')

    with open(output_file, 'w', encoding='utf-8') as outfile:
        for file_path in files:
            print(f"DEBUG: Processing file: {file_path}")  # Debugging output
            outfile.write(f"File: {file_path.name}\n\n")  # Add the file name at the start

            try:
                with open(file_path, 'r', encoding='utf-8-sig', errors='ignore') as infile:
                    for line in infile:
                        # Remove potential BOM or other hidden characters
                        line_no_bom = line.replace('\ufeff', '').replace('\xef\xbb\xbf', '')
                        stripped_line = line_no_bom.strip()

                        # Skip the line if it contains a timestamp or is purely a line number
                        if timestamp_pattern.search(stripped_line):
                            print(f"DEBUG: Removed timestamp line: {stripped_line}")
                            continue
                        if line_number_pattern.fullmatch(stripped_line):
                            print(f"DEBUG: Removed line number: {stripped_line}")
                            continue

                        # Otherwise, write the line as is (minus BOM)
                        outfile.write(line_no_bom)
                    
                    outfile.write("\n")  # Add a blank line after each file's content

            except Exception as e:
                print(f"ERROR: Error reading file {file_path}: {e}")

    print(f"Merged content saved to '{output_file}'.")

def get_unique_filename():
    """
    Generate a filename with a timestamp to ensure uniqueness.
    Format: merged_YYYYMMDD_HHMMSS.txt
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"merged_{timestamp}.txt"

def find_files_in_directory(directory, extensions, recursive=True):
    """
    Find all files with the given extensions in the specified directory.
    Supports recursive search.
    """
    path = Path(directory)
    files_found = []
    for ext in extensions:
        pattern = f'*.{ext}'
        if recursive:
            found = list(path.rglob(pattern))
        else:
            found = list(path.glob(pattern))
        files_found.extend(found)
    print(f"DEBUG: Found {len(files_found)} file(s) with extensions {extensions} in '{directory}'.")
    return files_found

def main():
    print("DEBUG: Entered main()...")

    # Generate the output filename
    output_file = get_unique_filename()
    print(f"DEBUG: Generated output file name: {output_file}")

    # Check if files were provided as arguments
    if len(sys.argv) > 1:
        input_paths = sys.argv[1:]
        print(f"DEBUG: Command-line arguments detected. input_paths = {input_paths}")
        files_to_process = []
        for path in input_paths:
            # Expand wildcard patterns (e.g., *.srt)
            expanded = glob(path, recursive=True)
            print(f"DEBUG: Expanded '{path}' to {expanded}")
            files_to_process.extend(expanded)
        # Convert to Path objects and remove duplicates
        files_to_process = list(set(Path(f) for f in files_to_process))
    else:
        # No arguments; process the current working directory
        current_dir = Path.cwd()
        print(f"DEBUG: No command-line arguments provided. Searching directory: {current_dir}")
        files_to_process = find_files_in_directory(current_dir, ['srt', 'txt'], recursive=True)

    print(f"DEBUG: Total files to process after collection: {len(files_to_process)}")

    if not files_to_process:
        print("No .srt or .txt files found to process.")
        return

    # Remove timestamps and merge files
    print("DEBUG: Starting the merge process...")
    remove_timestamps_and_merge(files_to_process, output_file)
    print("DEBUG: Merge process completed successfully.")

if __name__ == "__main__":
    main()
