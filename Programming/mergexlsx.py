import sys
import pandas as pd
from pathlib import Path

def merge_xlsx_files(input_files, output_file):
    # Initialize an empty list to hold DataFrames
    all_data = []

    # Loop through each input file
    for file in input_files:
        # Read the Excel file into a DataFrame
        df = pd.read_excel(file)
        # Append the DataFrame to the list
        all_data.append(df)

    # Combine all DataFrames into one
    merged_data = pd.concat(all_data, ignore_index=True)

    # Save the merged DataFrame to the output Excel file
    merged_data.to_excel(output_file, index=False)
    print(f"Files merged successfully into {output_file}")

if __name__ == "__main__":
    # Check if files are provided as arguments
    if len(sys.argv) < 2:
        print("Usage: python mergexlsx.py *.xlsx")
        sys.exit(1)

    # Get all input files from command-line arguments
    input_files = sys.argv[1:]

    # Define the output file name (in the current working directory)
    output_file = "combined.xlsx"

    # Merge the files
    merge_xlsx_files(input_files, output_file)