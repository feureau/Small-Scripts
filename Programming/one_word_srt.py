import sys
import os
from datetime import timedelta

def parse_timestamp(timestamp):
    """Convert SRT timestamp string to timedelta."""
    hours, minutes, seconds = timestamp.split(':')
    seconds, milliseconds = seconds.split(',')
    return timedelta(hours=int(hours), minutes=int(minutes), seconds=int(seconds), milliseconds=int(milliseconds))

def format_timestamp(delta):
    """Convert timedelta to SRT timestamp string."""
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = delta.microseconds // 1000
    return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"

def convert_to_one_word_srt(input_file, output_file):
    """Convert an SRT file to one-word SRT format."""
    with open(input_file, 'r', encoding='utf-8') as infile, open(output_file, 'w', encoding='utf-8') as outfile:
        lines = infile.readlines()
        i = 0
        block_number = 1

        while i < len(lines):
            # Read block number
            if lines[i].strip().isdigit():
                block_number = int(lines[i].strip())
                i += 1

            # Read timestamps
            start_time, end_time = lines[i].strip().split(' --> ')
            start_time = parse_timestamp(start_time)
            end_time = parse_timestamp(end_time)
            i += 1

            # Read text
            text = lines[i].strip()
            i += 1

            # Split text into words
            words = text.split()
            word_count = len(words)
            duration = (end_time - start_time) / word_count

            # Write one-word SRT blocks
            for word in words:
                word_start = start_time
                word_end = word_start + duration

                outfile.write(f"{block_number}\n")
                outfile.write(f"{format_timestamp(word_start)} --> {format_timestamp(word_end)}\n")
                outfile.write(f"{word}\n\n")

                block_number += 1
                start_time = word_end

def process_srt_file(input_path):
    """Process a single SRT file."""
    if not input_path.lower().endswith('.srt'):
        print(f"Skipping non-SRT file: {input_path}")
        return

    output_path = os.path.splitext(input_path)[0] + "_one_word.srt"
    convert_to_one_word_srt(input_path, output_path)
    print(f"Processed: {input_path} -> {output_path}")

def process_folder(folder_path):
    """Process all SRT files in a folder."""
    if not os.path.isdir(folder_path):
        print(f"Invalid folder path: {folder_path}")
        return

    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if os.path.isfile(file_path) and filename.lower().endswith('.srt'):
            process_srt_file(file_path)

def main():
    """Main function to handle command-line arguments."""
    if len(sys.argv) > 1:
        # Process all arguments (files or folders)
        for path in sys.argv[1:]:
            if os.path.isfile(path):
                process_srt_file(path)
            elif os.path.isdir(path):
                process_folder(path)
            else:
                print(f"Invalid path: {path}")
    else:
        # No input provided, ask for a folder
        folder_path = input("Enter the folder path containing SRT files: ").strip()
        if os.path.isdir(folder_path):
            process_folder(folder_path)
        else:
            print("Invalid folder path.")

if __name__ == "__main__":
    main()