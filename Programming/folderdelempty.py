import os
import sys

def remove_empty_folders(path):
    print(f"Scanning for empty folders in: {path} ...\n")
    deleted_count = 0

    # os.walk with topdown=False is crucial. 
    # It scans deepest subdirectories first, then moves up to the parent.
    # This allows us to delete a parent directory if it becomes empty 
    # after its subdirectories are deleted.
    for root, dirs, files in os.walk(path, topdown=False):
        for name in dirs:
            folder_path = os.path.join(root, name)

            try:
                # os.rmdir() is the safest method.
                # It inherently ONLY deletes a directory if it is empty.
                # If the directory contains even one file, it throws an OSError,
                # which we catch and ignore.
                os.rmdir(folder_path)
                print(f"[DELETED] {folder_path}")
                deleted_count += 1
            except OSError:
                # This error occurs if the folder is not empty 
                # or if there are permission issues. We stick to the rule:
                # "Must not change anything else," so we skip it.
                pass

    print("-" * 30)
    if deleted_count == 0:
        print("No empty folders were found.")
    else:
        print(f"Cleanup complete. Removed {deleted_count} empty folders.")

if __name__ == "__main__":
    # os.getcwd() gets the folder where you ran the command,
    # NOT the folder where this script file lives.
    current_working_directory = os.getcwd()
    
    try:
        remove_empty_folders(current_working_directory)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")