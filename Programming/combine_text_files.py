import sys
import os

# Check if files were dragged and dropped
if len(sys.argv) <= 1:
    print("No files were dragged and dropped!")
    sys.exit()

# Get the directory of the first file to determine the output file location
output_dir = os.path.dirname(sys.argv[1])
output_file = os.path.join(output_dir, "combined_output.txt")

# Delete the output file if it already exists
if os.path.exists(output_file):
    os.remove(output_file)

# Loop through all the dragged files
for file_path in sys.argv[1:]:
    try:
        print(f"Adding: {file_path}")
        with open(output_file, 'a', encoding='utf-8') as outfile:
            outfile.write(f"--- {os.path.basename(file_path)} ---\n")  # Adds the file name as a separator
            with open(file_path, 'r', encoding='utf-8') as infile:
                outfile.write(infile.read())
                outfile.write("\n")  # Adds a blank line between files
    except Exception as e:
        print(f"Error processing file {file_path}: {e}")

print(f"Files combined successfully into {output_file}")
