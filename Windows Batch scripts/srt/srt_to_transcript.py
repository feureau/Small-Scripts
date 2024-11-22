import sys
import os
import re

def process_srt_file(input_file, output_file):
    # Verify the input file exists
    if not os.path.exists(input_file):
        print(f"Error: File '{input_file}' not found!")
        sys.exit(1)

    # Open the input file and output file
    with open(input_file, 'r', encoding='utf-8') as infile, open(output_file, 'w', encoding='utf-8') as outfile:
        for line in infile:
            line = line.strip()

            # Skip blank lines
            if not line:
                continue

            # Skip sequence number lines (numeric only)
            if re.match(r'^\d+$', line):
                continue

            # Skip timecode lines (e.g., 00:01:20,000 --> 00:01:25,000)
            if re.match(r'^\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}$', line):
                continue

            # Write valid lines to the output file
            outfile.write(line + '\n')

    print(f"Conversion complete! Output saved to '{output_file}'.")


if __name__ == '__main__':
    # Check if the input file is provided
    if len(sys.argv) < 2:
        print("Error: No input file provided. Drag and drop an SRT file onto this script or provide it as a command-line argument.")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = os.path.splitext(input_file)[0] + '_transcript.txt'

    process_srt_file(input_file, output_file)
