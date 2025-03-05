import re
import sys
import glob
from pathlib import Path
import shutil

def remove_timestamps_and_line_numbers(input_file, output_file):
    timestamp_pattern = re.compile(r'^\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}$')
    line_number_pattern = re.compile(r'^\d+$')

    with open(input_file, 'r', encoding='utf-8') as infile, open(output_file, 'w', encoding='utf-8') as outfile:
        for line in infile:
            line = line.strip()
            if not timestamp_pattern.match(line) and not line_number_pattern.match(line) and line != '':
                outfile.write(line + '\n')

def main():
    if len(sys.argv) < 2:
        print("Usage: drag and drop SRT files or use: script.py *.srt")
        sys.exit(1)

    # Expand wildcards in command-line arguments
    file_paths = []
    for arg in sys.argv[1:]:
        file_paths.extend(glob.glob(arg, recursive=False))

    for input_path in file_paths:
        input_file = Path(input_path)
        if not input_file.is_file() or input_file.suffix.lower() != '.srt':
            print(f"Skipping invalid file: {input_path}")
            continue

        output_folder = input_file.parent / "no_timestamps"
        output_folder.mkdir(exist_ok=True)

        output_file = output_folder / f"{input_file.stem}_no_timestamps{input_file.suffix}"
        print(f"Processing: {input_file} -> {output_file}")

        try:
            remove_timestamps_and_line_numbers(input_file, output_file)
            print(f"Successfully processed: {output_file}")
        except Exception as e:
            print(f"Error processing {input_file}: {e}")

if __name__ == "__main__":
    main()