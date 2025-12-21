"""
Flatten Directory Tree Script
=============================

This script recursively moves all files from subdirectories into a specified 
root directory (the current working directory where the script is run).

Key Features:
-------------
1. Recursive Traversal: Walks through all nested subdirectories.
2. Self-Safety: Prevents processing files already in the root to avoid self-deletion.
3. Conflict Resolution: 
   - Content-Based Deletion: If a file with the same name exists and is identical 
     by content, the duplicate source file is deleted.
   - Name Collision Renaming: If a file with the same name exists but the content 
     is different, the source file is renamed (e.g., filename_1.ext).
4. Verbose Logging: Details every operation (move, rename, delete, skip) in the console.
5. Directory Cleanup: Deletes subdirectories after they have been emptied.

Usage:
------
Run the script from the directory you wish to flatten.
$ python flattenfiles.py
"""
import os
import shutil
import filecmp

def flatten_directory_tree(root_dir):
    """
    Moves all files from subdirectories into the root directory.
    Deletes empty subdirectories after moving files.
    """
    for dirpath, _, filenames in os.walk(root_dir, topdown=False):
        for filename in filenames:
            src_path = os.path.join(dirpath, filename)
            dest_path = os.path.join(root_dir, filename)

            # Skip if the file is already in the destination directory
            if src_path == dest_path:
                print(f"Skipping already flattened file: {src_path}")
                continue

            # Ensure we don't overwrite files with the same name
            if os.path.exists(dest_path):
                if filecmp.cmp(src_path, dest_path, shallow=False):
                    print(f"Duplicate found: {src_path} (identical to {dest_path}). Deleting source.")
                    os.remove(src_path)
                    continue

                base, ext = os.path.splitext(filename)
                counter = 1
                while os.path.exists(dest_path):
                    dest_path = os.path.join(root_dir, f"{base}_{counter}{ext}")
                    counter += 1
                print(f"Renaming duplicate: {src_path} -> {dest_path}")

            print(f"Moving: {src_path} -> {dest_path}")
            shutil.move(src_path, dest_path)

        # Remove empty directories after moving files
        if dirpath != root_dir:
            try:
                os.rmdir(dirpath)
                print(f"Removed empty directory: {dirpath}")
            except OSError:
                pass  # Ignore errors if the directory isn't empty

if __name__ == "__main__":
    current_dir = os.getcwd()  # The directory where the script is called
    flatten_directory_tree(current_dir)
