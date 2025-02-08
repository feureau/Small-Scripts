import sys
import glob
import os

def strip_header(filepath):
    """
    Removes the header from a text file, keeping only content below the line
    starting with '## p. ' or '----'.

    Args:
        filepath (str): The path to the text file.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        found_delimiter = False
        content_lines = []
        for line in lines:
            if not found_delimiter:
                if line.strip().startswith('## p. ') or line.strip().startswith('----'):
                    found_delimiter = True
            else:
                content_lines.append(line)

        if found_delimiter:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.writelines(content_lines)
            print(f"Processed and updated: {filepath}")
        else:
            print(f"Delimiter not found in: {filepath}, file unchanged.")

    except FileNotFoundError:
        print(f"Error: File not found: {filepath}")
    except Exception as e:
        print(f"An error occurred processing {filepath}: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        file_patterns = sys.argv[1:]
        files_to_process = []
        for pattern in file_patterns:
            files_to_process.extend(glob.glob(pattern))

        if not files_to_process:
            print("No files found matching the provided patterns.")
        else:
            for filepath in files_to_process:
                if os.path.isfile(filepath):
                    strip_header(filepath)
                else:
                    print(f"Warning: '{filepath}' is not a file and will be skipped.")
    else:
        print("Usage: strip.py <file_pattern1> <file_pattern2> ...")
        print("  e.g., strip.py *.txt")
        print("  This script will process all files matching the patterns in the current directory.")