#!/usr/bin/env python3
import sys
import os
import glob
import pandas as pd

def convert_to_csv(file_path):
    # Skip if it's somehow not a file
    if not os.path.isfile(file_path):
        return

    # Generate the output CSV filename by replacing .xlsx with .csv
    csv_file_path = os.path.splitext(file_path)[0] + '.csv'
    
    print(f"Converting: {file_path}  ->  {csv_file_path}")
    
    try:
        # Read the Excel file (Reads the first sheet by default)
        df = pd.read_excel(file_path)
        # Convert and save to CSV, ignoring the index column
        df.to_csv(csv_file_path, index=False)
        print("  [SUCCESS]")
    except Exception as e:
        print(f"  [ERROR] Failed to convert {file_path}: {e}")

def main():
    files_to_process = []
    
    # Check if the user passed arguments (e.g., file.xlsx or *.xlsx)
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            # We run glob on the argument to handle unexpanded wildcards 
            # (especially useful if running on Windows Command Prompt)
            matched_files = glob.glob(arg)
            if matched_files:
                files_to_process.extend(matched_files)
            else:
                print(f"Warning: No files matched '{arg}'")
    else:
        # No arguments passed: Default to all .xlsx files in the CURRENT directory
        files_to_process = glob.glob("*.xlsx")
        
    # Remove duplicates (in case wildcards overlap) and sort
    files_to_process = sorted(list(set(files_to_process)))
    
    if not files_to_process:
        print("No .xlsx files found or specified to convert.")
        sys.exit(1)
        
    # Process each found file
    for file in files_to_process:
        # Extra safety check to avoid trying to process non-excel files if 
        # a wildcard like *.* was passed
        if file.lower().endswith('.xlsx'):
            convert_to_csv(file)
        else:
            print(f"Skipping {file}: Not an .xlsx file")

if __name__ == "__main__":
    main()