import os
import shutil
import re
import sys
import glob

def organize_files(file_list):
    # Prefer a month+year pattern; otherwise use the last 4-digit year in the name.
    month_year_pattern = re.compile(
        r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[ _-]*((?:19|20)\d{2})',
        re.IGNORECASE
    )
    year_pattern = re.compile(r'(?:19|20)\d{2}')

    for file_path in file_list:
        # Get filename and absolute directory
        if not os.path.isfile(file_path):
            continue
            
        abs_path = os.path.abspath(file_path)
        directory = os.path.dirname(abs_path)
        filename = os.path.basename(abs_path)

        # Only process PDF files
        if not filename.lower().endswith('.pdf'):
            continue

        match = month_year_pattern.search(filename)
        if match:
            year = match.group(2)
        else:
            years = year_pattern.findall(filename)
            year = years[-1] if years else None

        if year:
            year_path = os.path.join(directory, year)

            # Create the year folder if it doesn't exist
            if not os.path.exists(year_path):
                os.makedirs(year_path)

            dest_file = os.path.join(year_path, filename)

            # Move the file
            try:
                shutil.move(abs_path, dest_file)
                print(f"Moved: {filename} -> {year}/")
            except Exception as e:
                print(f"Error moving {filename}: {e}")
        else:
            print(f"Skipped: {filename} (No year found)")

if __name__ == "__main__":
    # Check if arguments were provided
    if len(sys.argv) < 2:
        print("Usage: python folderbyyear.py *.pdf")
    else:
        # sys.argv[1:] takes all arguments after the script name
        # On many shells, *.pdf is expanded automatically; 
        # glob.glob handles cases where it isn't.
        files = []
        for arg in sys.argv[1:]:
            files.extend(glob.glob(arg))
            
        organize_files(files)
