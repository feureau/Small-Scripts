import re
import sys
import glob
from pathlib import Path

def remove_timestamps_and_line_numbers(input_file, output_file):
    """
    Reads an SRT file, removes timestamp lines and line number lines,
    and writes the remaining text to an output file.
    """
    timestamp_pattern = re.compile(r'^\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}$')
    line_number_pattern = re.compile(r'^\d+$')

    # Ensure both input and output are handled with UTF-8 encoding
    with open(input_file, 'r', encoding='utf-8') as infile, open(output_file, 'w', encoding='utf-8') as outfile:
        for line in infile:
            line = line.strip()
            # Write the line if it's not a timestamp, not a line number, and not an empty line
            if not timestamp_pattern.match(line) and not line_number_pattern.match(line) and line != '':
                outfile.write(line + '\n')

def main():
    """
    Handles command-line arguments for input files and processes them.
    """
    if len(sys.argv) < 2:
        print("Usage: drag and drop SRT files or use: srtcleanup.py *.srt")
        sys.exit(1)

    file_paths = []
    # Expand wildcards if present, otherwise treat the argument as a literal file name.
    for arg in sys.argv[1:]:
        # Use glob to handle potential wildcards (*, ?) in filenames
        if '*' in arg or '?' in arg:
            expanded = glob.glob(arg)
            file_paths.extend(expanded)
        else:
            # If no wildcards, just add the argument as a direct file path
            file_paths.append(arg)

    if not file_paths:
        print("No valid files found.")
        sys.exit(1)

    for input_path in file_paths:
        input_file = Path(input_path)

        # Check if the path is a file and has a .srt extension (case-insensitive)
        if not input_file.is_file() or input_file.suffix.lower() != '.srt':
            print(f"Skipping invalid file: {input_path} (Not an SRT file or does not exist)")
            continue

        # Define the output folder path
        output_folder = input_file.parent / "no_timestamps"
        # Create the output folder if it doesn't exist
        output_folder.mkdir(exist_ok=True)

        # Define the output file path with a .txt extension
        # Changed: input_file.suffix is replaced with ".txt"
        output_file = output_folder / f"{input_file.stem}_no_timestamps.txt"
        print(f"Processing: {input_file} -> {output_file}")

        try:
            # Call the function to process the file
            remove_timestamps_and_line_numbers(input_file, output_file)
            print(f"Successfully processed: {output_file}")
        except Exception as e:
            # Catch and print any errors during processing
            print(f"Error processing {input_file}: {e}")

if __name__ == "__main__":
    main()