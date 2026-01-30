# ==================================================================================================
#
#                                        File Finder & Mover
#
# --------------------------------------------------------------------------------------------------
#   - Author:      Gemini, Google AI
#   - Version:     5.0
#   - Last Updated: August 19, 2025
# --------------------------------------------------------------------------------------------------
#
# ## PURPOSE ##
#
# This script is a command-line utility designed to find a specific list of files within a
# directory and move them into a single, consolidated subfolder. Its primary goal is to provide a
# quick and efficient way to gather a subset of files from a larger collection into one place.
#
# It is a portable tool. You can store this script in one central folder (e.g., `E:\Small-Scripts\`)
# and call it from any other folder on your system (your "working directory"). The script will
# operate on the files within that working directory.
#
# ## FEATURES ##
#
#   - Dual Input Methods: Accepts file lists either as a direct command-line string or from a
#     text file where each line is a filename.
#
#   - Self-Aware List File Handling: If you generate a file list using a command like
#     `dir /b > list.txt`, the script is smart enough to recognize the list file's own name
#     in its contents and will automatically avoid moving it.
#
#   - Flexible Filename Matching (Extension Agnostic): You don't need the full filename.
#     The script finds and moves the first file that **starts with** the name you provide.
#     *Example:* A list entry of "IMG_101" will match "IMG_101.jpg" or "IMG_101_final.png".
#
#   - Consolidated Output Folder: The script moves all found files into a single, consistently
#     named subfolder (`found_files` by default). If the folder doesn't exist, it's created.
#     If it already exists, files are simply added to it, allowing you to run the script
#     multiple times to gather files into one location.
#
#   - Detailed Reporting: Provides a clear summary of which files were moved and which target
#     names from the list could not be matched.
#
# --------------------------------------------------------------------------------------------------
#
# ## SCRIPT HISTORY & DESIGN RATIONALE ##
#
#   - V1.0: Initial concept. Flawed logic used the script's own directory as the source.
#   - V2.0: Corrected logic to use `os.getcwd()`, making the script a portable tool.
#   - V3.0: Introduced extension-agnostic ("starts with") matching for greater flexibility.
#   - V4.0: Added self-aware list file handling to automatically ignore the input list file.
#   - V5.0 (Current Version): Removed the timestamp from the destination folder name. The script
#     now uses a single, static folder, creating it if it doesn't exist and adding to it if
#     it does. This allows for consolidating files from multiple runs into one location.
#
# --------------------------------------------------------------------------------------------------
#
# ## USAGE ##
#
# 1. Open a command prompt and navigate (`cd`) to the folder with the files you want to move.
# 2. Create your list file: `dir /b > list.txt`
# 3. Call the script using its full path: `python E:\path\to\your\scripts\findfile.py list.txt`
#
# ==================================================================================================

import os
import sys
import shutil

# ==================================================================================================
#                                        CONFIGURATION
# --------------------------------------------------------------------------------------------------
#      Customize the script's behavior by changing the variables in this section.
# ==================================================================================================

# Set the name for the subfolder where files will be moved.
# If this folder already exists, files will be added to it.
DESTINATION_SUBFOLDER_NAME = "found_files"


# ==================================================================================================
#                                      SCRIPT LOGIC
# --------------------------------------------------------------------------------------------------
#                 It is not recommended to modify code beyond this point
#                      unless you are familiar with Python.
# ==================================================================================================

def move_files(target_list, source_folder, ignore_file=None):
    """
    Finds and moves files from a source folder to a new subfolder based on a target list.

    Args:
        target_list (list): A list of base filenames to find.
        source_folder (str): The absolute path to the folder containing the files.
        ignore_file (str, optional): A filename to explicitly ignore. Defaults to None.
    """
    # Define the static destination subfolder name from the configuration.
    destination_folder = os.path.join(source_folder, DESTINATION_SUBFOLDER_NAME)

    # Check if the destination exists. If not, create it and inform the user.
    if not os.path.exists(destination_folder):
        os.makedirs(destination_folder)
        print(f"Created destination folder: {destination_folder}")
    else:
        # If it exists, inform the user that files will be added to it.
        print(f"Adding files to existing folder: {destination_folder}")

    moved_files_report = []
    not_found_targets = []
    
    all_files_in_dir = [f for f in os.listdir(source_folder) if os.path.isfile(os.path.join(source_folder, f))]

    for target_name in target_list:
        if ignore_file and target_name == ignore_file:
            continue

        match_found = False
        for real_filename in all_files_in_dir:
            if real_filename.startswith(target_name):
                # Ensure we don't try to move the destination folder itself if it's listed
                if real_filename == DESTINATION_SUBFOLDER_NAME:
                    continue

                source_path = os.path.join(source_folder, real_filename)
                try:
                    shutil.move(source_path, destination_folder)
                    moved_files_report.append(real_filename)
                    match_found = True
                    break 
                except Exception as e:
                    print(f"Error moving {real_filename}: {e}")
                    break
        
        if not match_found:
            not_found_targets.append(target_name)

    # --- Reporting ---
    if moved_files_report:
        print("\nSuccessfully found and moved the following files:")
        for f in moved_files_report:
            print(f"- {f}")

    if not_found_targets:
        print("\nThe following names from your list could not be matched to any file:")
        for f in not_found_targets:
            print(f"- {f}")

def main():
    """
    Main function to parse command-line arguments and initiate the file moving process.
    """
    source_folder = os.getcwd()
    list_file_name = None

    if len(sys.argv) < 2:
        script_name = os.path.basename(sys.argv[0])
        print("Usage:")
        print(f"1. Pass a list of filenames in quotes: python {script_name} \"file1 file2\"")
        print(f"2. Pass a text file with a list of filenames: python {script_name} list.txt")
        return

    argument = sys.argv[1]
    files_to_find = []
    
    if os.path.isfile(argument):
        try:
            list_file_name = os.path.basename(argument)
            with open(argument, 'r') as f:
                files_to_find = [line.strip() for line in f if line.strip()]
        except Exception as e:
            print(f"Error reading the file list: {e}")
            return
    else:
        files_to_find = argument.split()

    if files_to_find:
        move_files(files_to_find, source_folder, ignore_file=list_file_name)
    else:
        print("No files specified to find.")

if __name__ == "__main__":
    main()