#!/usr/bin/env python3
import argparse
import glob
import os
import sys

def count_words(filepath):
    """Counts words in a single file line-by-line."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            return sum(len(line.split()) for line in f)
    except Exception as e:
        # Print error to stderr so it doesn't mess up piped output
        print(f"Error reading {filepath}: {e}", file=sys.stderr)
        return 0

def main():
    # 1. Setup Argparse to handle the -h flag automatically
    parser = argparse.ArgumentParser(
        description="Reads one or more files and generates a word count report."
    )
    
    parser.add_argument(
        "files", 
        nargs='+', 
        help="The file path or pattern to analyze (e.g., *.txt)"
    )

    args = parser.parse_args()

    # 2. Collect files (Handling Wildcards for Windows compatibility)
    # argparse gives us a list, but on Windows "*.txt" comes in as a literal string.
    # We must run glob on every argument provided.
    target_files = []
    for pattern in args.files:
        matched = glob.glob(pattern)
        if not matched and not any(c in pattern for c in '*?['):
            # If glob returns nothing but it wasn't a pattern (just a specific filename),
            # append it anyway so the file reader can throw a "File not found" error naturally,
            # or skip it.
            matched = [pattern]
        target_files.extend(matched)

    # Remove duplicates and sort
    target_files = sorted(list(set(target_files)))
    
    # Filter for actual existing files
    valid_files = [f for f in target_files if os.path.isfile(f)]

    if not valid_files:
        print("No valid files found matching your pattern.")
        sys.exit(0)

    # 3. Print Report Header
    print(f"{'FILENAME':<40} | {'WORDS':>10}")
    print("-" * 53)

    total_words = 0
    file_count = 0

    for filepath in valid_files:
        w_count = count_words(filepath)
        total_words += w_count
        file_count += 1
        print(f"{os.path.basename(filepath):<40} | {w_count:>10,}")

    # 4. Print Footer
    print("-" * 53)
    print(f"{'TOTAL':<40} | {total_words:>10,}")
    print(f"Processed {file_count} files.")

if __name__ == "__main__":
    main()