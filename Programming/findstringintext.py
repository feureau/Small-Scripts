# ==============================================================================
# SCRIPT DOCUMENTATION
# ==============================================================================
#
# NAME: findstringintext.py
#
# PURPOSE:
# This script is designed to search for a specific string within a set of text
# files that match a given pattern (e.g., all *.txt files). If the specified
# string is found in a file, that file is automatically moved to a designated
# subfolder.
#
# HOW IT WORKS:
# 1.  Configuration: Reads customizable variables set at the top of the script,
#     such as the name of the folder for found files.
# 2.  Argument Parsing: The script accepts two command-line arguments:
#     - The first argument is a file pattern (e.g., "*.txt", "report-*.log").
#     - The second argument is the exact string to search for (e.g., "ERROR").
# 3.  Folder Creation: It checks if the designated subfolder (e.g., "Found_String")
#     exists in the current working directory. If not, it creates it.
# 4.  File Discovery: It uses the `glob` module to find all files in the
#     current directory that match the provided file pattern.
# 5.  Search and Move Loop: The script iterates through each file found:
#     a. It opens the file in read-only mode, ensuring the file is properly
#        closed afterward using a `with` statement. This prevents file-locking
#        errors.
#     b. It reads the entire content of the file.
#     c. It checks if the search string exists within the file's content.
#     d. If the string is found, it sets a flag.
#     e. After the file is closed, it checks the flag. If the flag is set,
#        it moves the file to the designated subfolder using `shutil.move()`.
# 6.  Error Handling: A `try...except` block is used to catch and report any
#     errors that occur during file processing, preventing the script from
#     crashing on a single problematic file.
#
# USAGE:
# Run this script from the command line in the directory containing the files
# you want to search.
#
# Syntax:
# python <path_to_script>\findstringintext.py "<file_pattern>" "<search_string>"
#
# Example 1: Find "completed" in all .log files and move them.
# C:\my_logs> python C:\scripts\findstringintext.py "*.log" "completed"
#
# Example 2: Find "Project Phoenix" in all text files.
# C:\documents> python ..\scripts\findstringintext.py "*.txt" "Project Phoenix"
#
# IMPORTANT:
# - Always enclose the file pattern and the search string in double quotes ("")
#   to handle spaces and special characters correctly.
# - The script moves files relative to the directory where you run the command,
#   not where the script itself is located.
#
# ==============================================================================

# ==============================================================================
# CUSTOMIZABLE VARIABLES
# ==============================================================================

# The name of the subfolder where files containing the string will be moved.
# You can change this to anything you like, e.g., "Matches", "Sorted_Files", etc.
FOUND_FILES_FOLDER_NAME = "Found_String"

# ==============================================================================
# SCRIPT CODE
# ==============================================================================

import os
import sys
import glob
import shutil

def find_string_and_move_files(file_pattern, search_string):
    """
    Finds a string in files matching a pattern and moves them.

    Args:
        file_pattern: A file pattern to match (e.g., "*.txt").
        search_string: The string to search for in the files.
    """
    # Create the "Found_String" subfolder if it doesn't exist, using the
    # customizable variable from the top of the script.
    if not os.path.exists(FOUND_FILES_FOLDER_NAME):
        os.makedirs(FOUND_FILES_FOLDER_NAME)
        print(f"Created directory: {FOUND_FILES_FOLDER_NAME}")

    # Use glob to find all files that match the user-provided pattern.
    files = glob.glob(file_pattern)

    # If no files are found, inform the user and exit the function.
    if not files:
        print(f"No files found matching the pattern: {file_pattern}")
        return

    print(f"Searching for '{search_string}' in {len(files)} file(s)...")

    # Loop through each file path returned by glob.
    for file_path in files:
        try:
            # A flag to check if the string was found in the file.
            string_was_found = False

            # Open the file for reading. The `with` statement ensures the file
            # is automatically closed when the block is exited, even if errors occur.
            # 'encoding' and 'errors' parameters help prevent crashes on files with
            # unusual characters.
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                if search_string in content:
                    print(f"Found '{search_string}' in: {file_path}")
                    # Set the flag to True if the string is in the file's content.
                    string_was_found = True

            # IMPORTANT: This check happens *after* the `with` block has finished.
            # This means the file is now closed and can be safely moved.
            if string_was_found:
                # Construct the destination path inside the 'Found_String' folder.
                destination_path = os.path.join(FOUND_FILES_FOLDER_NAME, os.path.basename(file_path))
                # Move the file.
                shutil.move(file_path, destination_path)
                print(f"Moved '{file_path}' to '{FOUND_FILES_FOLDER_NAME}'")

        except Exception as e:
            # If any other error occurs during the process, print it out.
            print(f"Error processing file {file_path}: {e}")

# This standard Python construct ensures that the code inside this block only
# runs when the script is executed directly (not when imported as a module).
if __name__ == "__main__":
    # The script expects exactly two arguments from the command line,
    # plus the script name itself (which is sys.argv[0]).
    if len(sys.argv) != 3:
        print("Usage: python findstringintext.py <file_pattern> \"<search_string>\"")
        # Exit the script if the number of arguments is incorrect.
        sys.exit(1)

    # Assign the command-line arguments to variables for clarity.
    file_pattern_arg = sys.argv[1]
    search_string_arg = sys.argv[2]

    # Call the main function with the provided arguments.
    find_string_and_move_files(file_pattern_arg, search_string_arg)