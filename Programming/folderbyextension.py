# ====================================================================================
#
# SCRIPT: Local File Sorter
#
# DESCRIPTION:
# This script organizes files within a directory structure by moving them into
# subfolders named after their respective file extensions. Unlike a typical file
# sorter that consolidates all files into a single top-level location, this
# script performs the sorting "in-place." This means the new extension folders
# (e.g., 'pdf', 'jpg') are created inside the same subdirectory where the files
# were originally located.
#
# The script can operate in two modes:
# 1. Default Mode: Sorts all files in the current directory and all of its
#    subdirectories.
# 2. Targeted Mode: Sorts only the files of a specific extension provided as a
#    command-line argument.
#
# HOW TO USE:
# 1. Place this script in the root folder you wish to organize.
# 2. Open a terminal or command prompt in that same folder.
# 3. To sort ALL files in all subfolders:
#    $ python your_script_name.py
#
# 4. To sort ONLY files with a specific extension (e.g., 'mp4'):
#    $ python your_script_name.py mp4
#
# --- SCRIPT LOGIC AND REASONING ---
#
# KEY MODULES USED:
# - os:     Essential for interacting with the operating system. It's used here
#           for path manipulation (os.path.join, os.path.splitext), checking for
#           the existence of files/directories (os.path.exists), creating
#           directories (os.makedirs), and walking the directory tree (os.walk).
#
# - shutil: The "shell utilities" module. Its 'move' function is used to safely
#           move files from their original location to the new destination folder.
#
# - sys:    The "system-specific parameters and functions" module. 'sys.argv' is
#           used to access command-line arguments, which allows the user to
#           specify a particular file extension to sort.
#
# CORE FUNCTION: sort_files_locally()
#
# 1. WALKING THE DIRECTORY TREE:
#    - The script uses `for dirpath, dirnames, filenames in os.walk(root_dir):`.
#    - `os.walk()` is a generator that yields a 3-tuple for each directory it
#      visits, including the root directory itself. The tuple contains:
#        - dirpath: The path of the current directory being scanned.
#        - dirnames: A list of subdirectories within `dirpath`.
#        - filenames: A list of files within `dirpath`.
#    - This is the ideal method for recursively processing a folder and all its
#      subfolders, as it handles the traversal logic automatically.
#
# 2. DETERMINING THE DESTINATION (THE "LOCAL" LOGIC):
#    - The destination folder path is constructed using:
#      `destination_folder_path = os.path.join(dirpath, extension_folder_name)`
#    - REASONING: This is the most critical part of the "local sorting" logic.
#      By using `dirpath` (the path of the current folder being scanned) as the
#      base, we ensure that the new extension folder (e.g., 'pdf') is created
#      inside the same folder where the PDF files were found, rather than in the
#      top-level root directory.
#
# 3. HANDLING COMMAND-LINE ARGUMENTS:
#    - The `if __name__ == "__main__":` block checks `len(sys.argv)`.
#    - `sys.argv` is a list containing the script name at index 0, followed by
#      any arguments.
#    - REASONING: If `len(sys.argv)` is greater than 1, it means the user provided
#      an argument (like 'mp4'). This argument is passed to the main function,
#      which then uses an `if` condition to only process files matching that
#      specific extension. If no argument is given, the function runs in its
#      default mode, processing all files.
#
# 4. SAFETY CHECKS:
#    - `if not os.path.exists(destination_folder_path): os.makedirs(...)`
#      This check prevents errors by only attempting to create a directory if it
#      doesn't already exist.
#
#    - `if parent_folder_name == current_extension: continue`
#      REASONING: This is a crucial self-preservation check. Once the script moves
#      'image.jpg' into a 'jpg' folder, on a subsequent run `os.walk()` will
#      eventually scan inside that 'jpg' folder. Without this check, the script
#      would try to create another 'jpg' folder inside the existing 'jpg' folder
#      and move the file again, leading to redundant processing or errors. This
#      line makes the script idempotent (running it multiple times has the same
#      effect as running it once).
#
# ====================================================================================

import os
import shutil
import sys

def sort_files_locally(target_extension=None):
    """
    Sorts files into extension-based subfolders within the same directory
    where the files are found. It processes the current directory and all
    of its subdirectories.

    Args:
        target_extension (str, optional): If provided, only files with this
                                          extension will be sorted.
                                          Defaults to None, which sorts all files.
    """
    root_dir = os.getcwd()

    if target_extension:
        # Normalize the target extension (e.g., ".mp4" becomes "mp4")
        target_extension = target_extension.lstrip('.').lower()
        print(f"Searching for '.{target_extension}' files to sort into their local subfolders...")
    else:
        print(f"Sorting all files into their local subfolders...")

    print(f"Starting in directory: '{root_dir}'\n")

    # Walk through the directory tree, starting from the root directory.
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for filename in filenames:
            # Get the file's extension and normalize it (lowercase, no dot).
            name, extension = os.path.splitext(filename)
            current_extension = extension.lstrip('.').lower()

            # --- Logic to decide if we should process this file ---

            # 1. If a specific extension is targeted, skip any files that do not match.
            if target_extension and current_extension != target_extension:
                continue

            # 2. If the file is already in a folder named after its extension, skip it.
            #    This prevents the script from re-processing its own output folders.
            parent_folder_name = os.path.basename(dirpath)
            if parent_folder_name == current_extension:
                continue

            # --- Logic to move the file ---

            # Determine the name of the folder based on the extension.
            if not current_extension:
                extension_folder_name = 'no_extension'
            else:
                extension_folder_name = current_extension

            # Construct the destination folder path to be INSIDE the current directory (dirpath).
            destination_folder_path = os.path.join(dirpath, extension_folder_name)

            # Create the local destination folder if it doesn't already exist.
            if not os.path.exists(destination_folder_path):
                print(f"Creating folder: '{destination_folder_path}'")
                os.makedirs(destination_folder_path)

            # Define the full source and destination file paths.
            source_filepath = os.path.join(dirpath, filename)
            destination_filepath = os.path.join(destination_folder_path, filename)

            # Move the file from its original location to the new extension subfolder.
            try:
                shutil.move(source_filepath, destination_filepath)
                print(f"Moved '{filename}' -> '{destination_folder_path}'")
            except Exception as e:
                print(f"Error moving '{filename}': {e}")

    print("\nLocal file sorting complete.")


if __name__ == "__main__":
    # The __name__ == "__main__" block ensures this code only runs when the script
    # is executed directly, not when imported as a module into another script.

    # Check if a command-line argument was provided.
    if len(sys.argv) > 1:
        # If yes, use the first argument as the target extension.
        ext_to_sort = sys.argv[1]
        sort_files_locally(target_extension=ext_to_sort)
    else:
        # If no argument is provided, call the function without a target to sort all files.
        sort_files_locally()