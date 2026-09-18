import os
import sys
from datetime import datetime
import re # <-- We need to import the regular expression module

def rename_files_with_date(file_paths):
    """
    Renames a list of files by prefixing them with their modification date, 
    but only if they do not already contain the YYYY-MM-DD - pattern.
    Format: YYYY-MM-DD - ORIGINALFILENAME.EXT
    """
    print("--- Starting File Renaming Process ---")

    # Regex Pattern Explanation:
    # ^          -> Starts at the beginning of the string (filename)
    # \d{4}      -> Exactly four digits (Year)
    # -\d{2}-\d{2} -> Hyphen, two digits, hyphen, two digits (Month-Day)
    # \s-\s      -> A space, a hyphen, and another space (" - ")
    DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}\s-\s")

    if not file_paths:
        print("Error: No file paths were provided.")
        return

    for old_filepath in file_paths:
        # 1. Check if the path exists before trying to process it
        if not os.path.exists(old_filepath):
            print(f"[SKIP] File not found: {old_filepath}")
            continue

        try:
            # Extract filename and extension for pattern checking
            directory, filename_with_ext = os.path.split(old_filepath)

            # 2. NEW LOGIC: Check if the filename already matches the date pattern
            if DATE_PATTERN.search(filename_with_ext):
                print(f"[SKIP] Already dated: '{filename_with_ext}' - Skipping rename.")
                continue # Skip to the next file in the loop

            # --- If we reach here, the filename is NOT already dated, so we proceed with renaming ---

            # 3. Get file modification time (timestamp)
            timestamp = os.path.getmtime(old_filepath)
            dt_object = datetime.fromtimestamp(timestamp)
            date_str = dt_object.strftime('%Y-%m-%d')

            # 4. Extract original name and extension
            filename, ext = os.path.splitext(filename_with_ext)
            
            # 5. Construct the new file name
            new_filename = f"{date_str} - {filename}{ext}"
            new_filepath = os.path.join(directory, new_filename)

            # Safety check: Prevent renaming if the target already exists (optional but safe)
            if os.path.exists(new_filepath):
                print(f"[WARNING] Target file already exists. Skipping rename for {old_filepath}")
                continue

            # 6. Perform the rename operation
            os.rename(old_filepath, new_filepath)
            print(f"[SUCCESS] Renamed: '{filename_with_ext}' -> '{new_filename}'")

        except PermissionError:
            print(f"[ERROR] Permission denied for file: {old_filepath}")
        except Exception as e:
            print(f"[CRITICAL ERROR] Could not process {old_filepath}. Reason: {e}")


if __name__ == "__main__":
    files_to_process = sys.argv[1:]
    rename_files_with_date(files_to_process)

