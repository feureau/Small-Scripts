"""
foldersplitter.py

Description:
    Organizes files in the current directory into subfolders. Each subfolder will contain 
    a specified maximum number of files. Subfolders are named numerically (0, 1, 2, ...).
    If files or patterns are provided as arguments, only those matching items will be 
    processed. Otherwise, all files in the current directory (excluding the script 
    itself) are processed.

Usage:
    python foldersplitter.py [files/patterns] [-l LIMIT]

Arguments:
    files               (Optional) One or more files or wildcard patterns (e.g., *.mp4, 
                        image_*.png). If not provided, the script processes all files 
                        in the current directory.
    -l, --limit LIMIT   (Optional) The maximum number of files per folder. 
                        Default is 15.

Examples:
    python foldersplitter.py
    python foldersplitter.py *.mp4
    python foldersplitter.py -l 10
    python foldersplitter.py file1.txt file2.txt -l 5
    python foldersplitter.py *.jpg *.png --limit 20

Note:
    This documentation must be included and updated with every change to the script.
"""

import os
import shutil
import argparse
import glob

def main():
    parser = argparse.ArgumentParser(
        description="Organizes files in the current directory into subfolders.",
        formatter_class=argparse.RawTextHelpFormatter, # Allows for better formatting of the help message
        epilog="""Example usage:
  python your_script_name.py
  python your_script_name.py -l 10
  python your_script_name.py --limit 20"""
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="Files or patterns to process (e.g., *.mp4). If omitted, processes all files in CWD."
    )
    parser.add_argument(
        "-l", "--limit",
        type=int,
        default=15,
        help="Number of files per folder. Default is 15."
    )
    
    # In a standard command-line execution, parse_args() will use sys.argv[1:]
    # The error in the previous execution step was due to the environment
    # passing its own arguments. This will work correctly when you run it.
    try:
        args = parser.parse_args()
    except SystemExit as e:
        # This allows the help message to be displayed and then exits cleanly
        # if -h or --help is used, or if there's an argument parsing error.
        return


    # The folder from which the script is called (current working directory)
    cwd = os.getcwd()
    script_name = os.path.basename(__file__)

    if args.files:
        files_to_process = []
        for pattern in args.files:
            # Expand tokens that might contain wildcards
            expanded = glob.glob(pattern)
            for f in expanded:
                # We only want files that exist and are not the script itself
                if os.path.isfile(f) and os.path.basename(f) != script_name:
                    files_to_process.append(os.path.basename(f))
        
        # Remove duplicates while preserving order
        files_to_process = list(dict.fromkeys(files_to_process))
    else:
        # Gather all files (excluding this script itself)
        all_items = os.listdir(cwd)
        files_to_process = [
            f for f in all_items
            if os.path.isfile(os.path.join(cwd, f)) and f != script_name
        ]
    
    # Sort them for consistent ordering
    files_to_process.sort()
    
    if not files_to_process:
        print(f"No files found to process in the current directory (excluding '{script_name}').")
        return

    # Start the folder index at -1 so the first check moves it to 0
    dir_n = -1
    
    idx = 0
    limit = args.limit

    if limit <= 0:
        print("Error: The limit for files per folder must be a positive integer.")
        parser.print_help() # Show help if the limit is invalid
        return

    print(f"Processing {len(files_to_process)} files with a limit of {limit} files per folder.")

    # While we still have files to move
    while idx < len(files_to_process):
        # Find the next numeric directory name that does not exist
        dir_n += 1
        while os.path.exists(str(dir_n)):
            dir_n += 1
        
        # Create the new folder
        try:
            os.mkdir(str(dir_n))
            print(f"Created folder: {dir_n}")
        except OSError as e:
            print(f"Error creating folder {dir_n}: {e}")
            print("Stopping script due to folder creation error.")
            return # Stop if folder creation fails
        
        # Slice the next `limit` files
        chunk = files_to_process[idx : idx + limit]
        idx += limit
        
        # Move those files into the newly created folder
        for filename in chunk:
            src_path = os.path.join(cwd, filename)
            dst_path = os.path.join(cwd, str(dir_n), filename)
            try:
                shutil.move(src_path, dst_path)
                print(f"Moved: {filename} -> {dir_n}/{filename}")
            except Exception as e:
                print(f"Error moving {filename} to {dir_n}/: {e}")
                # Decide if you want to stop or continue if a single file move fails
                # For now, it will print the error and continue with other files/folders
    
    print("\nTask Done!")

if __name__ == "__main__":
    main()