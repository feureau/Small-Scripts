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
6. Selective Flattening: Optionally flatten only specified folders.
7. Folder Prefixing: Optionally prefix filenames with their folder name.

Usage:
------
Run the script from the directory you wish to flatten.
$ python flattenfiles.py [--prefix-folder | -p] [--folders | -f FOLDER [FOLDER ...]]

Optional arguments:
- -p, --prefix-folder: Prefix filenames with their folder name.
- -f, --folders: Only flatten the specified folder names (multiple allowed).
"""
import os
import shutil
import filecmp
import argparse

def get_long_path(path):
    """Handle long paths on Windows by prepending \\\\?\\ to absolute paths."""
    abs_path = os.path.abspath(path)
    if os.name == 'nt' and len(abs_path) > 260 and not abs_path.startswith('\\\\?\\'):
        return '\\\\?\\' + abs_path
    return abs_path

def safe_exists(path):
    """Check if path exists, handling long paths on Windows."""
    return os.path.exists(get_long_path(path))

def safe_cmp(src, dst):
    """Compare files, handling long paths on Windows."""
    return filecmp.cmp(get_long_path(src), get_long_path(dst), shallow=False)

def safe_move(src, dst):
    """Move file, handling long paths on Windows."""
    shutil.move(get_long_path(src), get_long_path(dst))

def flatten_directory_tree(root_dir, prefix=False, folders=None):
    """
    Moves all files from subdirectories into the root directory.
    If prefix is True, prepends the folder name to the filename.
    If folders is provided, only flattens directories whose basename is in folders.
    Deletes empty subdirectories after moving files.
    """
    for dirpath, _, filenames in os.walk(root_dir, topdown=False):
        if folders and os.path.basename(dirpath) not in folders:
            continue
        for filename in filenames:
            src_path = os.path.join(dirpath, filename)
            if prefix:
                folder_name = os.path.basename(dirpath)
                new_filename = f"{folder_name} - {filename}"
            else:
                new_filename = filename
            dest_path = os.path.join(root_dir, new_filename)

            # Skip if the file is already in the destination directory
            if src_path == dest_path:
                print(f"Skipping already flattened file: {src_path}")
                continue

            # Ensure we don't overwrite files with the same name
            if safe_exists(dest_path):
                if safe_cmp(src_path, dest_path):
                    print(f"Duplicate found: {src_path} (identical to {dest_path}). Deleting source.")
                    try:
                        os.remove(get_long_path(src_path))
                    except OSError as e:
                        print(f"Error deleting duplicate {src_path}: {e}")
                    continue

                base, ext = os.path.splitext(new_filename)
                counter = 1
                while safe_exists(dest_path):
                    dest_path = os.path.join(root_dir, f"{base}_{counter}{ext}")
                    counter += 1
                print(f"Renaming duplicate: {src_path} -> {dest_path}")

            print(f"Moving: {src_path} -> {dest_path}")
            try:
                safe_move(src_path, dest_path)
            except OSError as e:
                print(f"Error moving {src_path} to {dest_path}: {e}")
                continue

        # Remove empty directories after moving files
        if dirpath != root_dir:
            try:
                os.rmdir(get_long_path(dirpath))
                print(f"Removed empty directory: {dirpath}")
            except OSError as e:
                print(f"Could not remove directory {dirpath}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Flatten directory tree with optional folder prefixing and selection.")
    parser.add_argument('-p', '--prefix-folder', action='store_true', help="Prefix filenames with their folder name.")
    parser.add_argument('-f', '--folders', nargs='+', help="Only flatten the specified folder names (multiple allowed).")
    args, unknown = parser.parse_known_args()

    current_dir = os.getcwd()  # The directory where the script is called
    flatten_directory_tree(current_dir, args.prefix_folder, args.folders)
