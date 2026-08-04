#!/usr/bin/env python3
import sys
import glob
import csv
import os

def main():
    # The output file will be saved in the directory where you run the command
    output_filename = "merged_output.csv"
    output_filepath = os.path.abspath(output_filename)

    # 1. Determine which files to process
    input_files = []
    if len(sys.argv) > 1:
        # User provided arguments (e.g., "*.csv" or "file1.csv file2.csv")
        for arg in sys.argv[1:]:
            # Expand wildcards manually (useful for Windows CMD)
            if '*' in arg or '?' in arg:
                input_files.extend(glob.glob(arg))
            else:
                input_files.append(arg)
    else:
        # Default: No arguments provided, grab all CSVs in the current working directory
        input_files = glob.glob('*.csv')

    # Remove duplicates if any were passed
    input_files = list(set(input_files))

    # 2. Prevent the script from merging its own output if you run it twice
    valid_files = []
    for f in input_files:
        if os.path.abspath(f) != output_filepath:
            valid_files.append(f)

    if not valid_files:
        print("No CSV files found to merge.")
        return

    # Sort files for predictable merging order
    valid_files.sort()
    print(f"Found {len(valid_files)} files to merge.")

    # 3. First pass: Extract all unique headers across all files
    # This prevents errors if files have missing columns or columns in different orders
    fieldnames = []
    for file in valid_files:
        # utf-8-sig safely handles potential BOM (Byte Order Marks) often left by Excel
        with open(file, 'r', newline='', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            try:
                headers = next(reader)
                for h in headers:
                    if h and h not in fieldnames:
                        fieldnames.append(h)
            except StopIteration:
                pass # Skip empty files

    if not fieldnames:
        print("No data/headers found in the provided CSV files.")
        return

    # 4. Second pass: Merge the data
    with open(output_filename, 'w', newline='', encoding='utf-8') as out_f:
        writer = csv.DictWriter(out_f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()

        for file in valid_files:
            print(f" -> Merging: {file}")
            with open(file, 'r', newline='', encoding='utf-8-sig') as in_f:
                reader = csv.DictReader(in_f)
                for row in reader:
                    writer.writerow(row)

    print(f"\nSuccess! Merged {len(valid_files)} files into '{output_filename}'.")

if __name__ == "__main__":
    main()