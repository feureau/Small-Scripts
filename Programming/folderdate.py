import os
import sys
from datetime import datetime
import re


def rename_folders_with_date(folder_paths):
    """
    Renames a list of folders by prefixing them with the current date (ISO 8601),
    but only if they do not already start with the YYYY-MM-DD - pattern.
    Format: YYYY-MM-DD - ORIGINALFOLDERNAME
    """
    print("--- Starting Folder Renaming Process ---")

    # Regex Pattern Explanation:
    # ^            -> Starts at the beginning of the string (folder name)
    # \d{4}        -> Exactly four digits (Year)
    # -\d{2}-\d{2} -> Hyphen, two digits, hyphen, two digits (Month-Day)
    # \s-\s        -> A space, a hyphen, and another space (" - ")
    DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}\s-\s")

    if not folder_paths:
        print("Error: No folder paths were provided.")
        return

    date_str = datetime.now().strftime("%Y-%m-%d")

    for raw_path in folder_paths:
        # Normalize path to strip any trailing slashes (e.g., from shell tab-completion)
        old_folderpath = os.path.normpath(raw_path)

        # 1. Check if the path exists and is a directory
        if not os.path.exists(old_folderpath):
            print(f"[SKIP] Folder not found: {old_folderpath}")
            continue

        if not os.path.isdir(old_folderpath):
            print(f"[SKIP] Not a folder: {old_folderpath}")
            continue

        try:
            # Extract parent directory and folder name
            parent_dir, folder_name = os.path.split(os.path.abspath(old_folderpath))

            if not folder_name:
                print(f"[SKIP] Cannot rename root or invalid folder path: {old_folderpath}")
                continue

            # 2. Check if the folder name already matches the date pattern
            if DATE_PATTERN.search(folder_name):
                print(f"[SKIP] Already dated: '{folder_name}' - Skipping rename.")
                continue

            # 3. Construct the new folder name and path
            new_folder_name = f"{date_str} - {folder_name}"
            new_folderpath = os.path.join(parent_dir, new_folder_name)

            # Safety check: Prevent renaming if the target already exists
            if os.path.exists(new_folderpath):
                print(f"[WARNING] Target folder already exists. Skipping rename for {old_folderpath}")
                continue

            # 4. Perform the rename operation
            os.rename(old_folderpath, new_folderpath)
            print(f"[SUCCESS] Renamed: '{folder_name}' -> '{new_folder_name}'")

        except PermissionError:
            print(f"[ERROR] Permission denied for folder: {old_folderpath}")
        except Exception as e:
            print(f"[CRITICAL ERROR] Could not process {old_folderpath}. Reason: {e}")


if __name__ == "__main__":
    folders_to_process = sys.argv[1:]
    rename_folders_with_date(folders_to_process)
