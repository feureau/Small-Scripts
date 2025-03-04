#!/usr/bin/env python3
import sys
import os
import glob
import subprocess

def main():
    # Check if at least one argument is given
    if len(sys.argv) < 2:
        script_name = os.path.basename(sys.argv[0])
        print(f"Usage: {script_name} file1.md [file2.md ...]")
        sys.exit(1)

    # Expand wildcards for each argument
    file_list = []
    for arg in sys.argv[1:]:
        # Use glob to expand patterns
        matches = glob.glob(arg)
        if matches:
            file_list.extend(matches)
        else:
            # If no matches, add the literal arg (to show "File not found")
            file_list.append(arg)

    # Process each file in the expanded list
    for filepath in file_list:
        if os.path.exists(filepath):
            base_name, _ = os.path.splitext(os.path.basename(filepath))
            output_file = f"{base_name}.docx"
            print(f"Converting {filepath} to {output_file}...")
            subprocess.run(["pandoc", filepath, "-t", "docx", "-o", output_file])
        else:
            print(f"File not found: {filepath}")

    print("Conversion complete!")

if __name__ == '__main__':
    main()
