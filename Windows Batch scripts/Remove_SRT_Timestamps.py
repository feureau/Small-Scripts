import re
import sys
from pathlib import Path

def remove_timestamps_and_line_numbers(input_file, output_file):
    # Regex pattern to match timestamp lines
    timestamp_pattern = re.compile(r'^\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}$')
    # Regex pattern to match line numbers
    line_number_pattern = re.compile(r'^\d+$')

    with open(input_file, 'r', encoding='utf-8') as infile, open(output_file, 'w', encoding='utf-8') as outfile:
        for line in infile:
            line = line.strip()
            # Skip timestamp lines and line numbers, write all others
            if not timestamp_pattern.match(line) and not line_number_pattern.match(line) and line != '':
                outfile.write(line + '\n')

def main():
    if len(sys.argv) < 2:
        print("Usage: drag and drop SRT files onto this script.")
        sys.exit(1)

    for input_path in sys.argv[1:]:
        input_file = Path(input_path)
        if not input_file.exists() or input_file.suffix.lower() != '.srt':
            print(f"Skipping invalid file: {input_path}")
            continue

        output_file = input_file.with_name(f"{input_file.stem}_no_timestamps{input_file.suffix}")
        print(f"Processing: {input_file} -> {output_file}")

        try:
            remove_timestamps_and_line_numbers(input_file, output_file)
            print(f"Processed: {output_file}")
        except Exception as e:
            print(f"Error processing {input_file}: {e}")

if __name__ == "__main__":
    main()
