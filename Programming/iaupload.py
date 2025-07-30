#!/usr//bin/env python3
"""
iaupload.py

Batch upload utility for Internet Archive. This version recursively uploads all
files and shows individual file upload progress.

NOTE: Uploading files one-by-one is slower than a single batch upload but
provides more detailed feedback.

Usage:
  python iaupload.py [<identifier>]

If no <identifier> is provided, the script generates one from the directory name,
checks if the item exists, and then creates or updates it.

"""
import sys
from pathlib import Path
import internetarchive as ia

# --- NEW HELPER FUNCTION [MODIFIED] ---
def normalize_path(path_str):
    """
    Converts a path string to a consistent, comparable format by making it
    lowercase, ensuring forward slashes, and replacing spaces with underscores.
    """
    return path_str.lower().replace('\\', '/').replace(' ', '_')

def main():
    cwd = Path.cwd()

    # Get the script's own name to exclude it from the upload list
    script_name = Path(sys.argv[0]).name
    
    # Recursively find all local files
    print("Scanning for all files recursively...")
    all_local_files = [p for p in cwd.rglob('*') if p.is_file() and p.name != script_name]
    print(f"Found {len(all_local_files)} local files.")

    # Determine the target identifier
    if len(sys.argv) > 1:
        IDENT = sys.argv[1]
    else:
        IDENT = cwd.name.replace(' ', '_')
    
    print(f"Target Internet Archive identifier: '{IDENT}'")

    # Check if the item exists to decide between create/update
    item = ia.get_item(IDENT)
    to_upload = []

    # --- COMPARISON LOGIC [MODIFIED] ---
    if item.exists:
        print("Item exists. Comparing local and remote files for UPDATE mode.")
        
        # Create a set of NORMALIZED remote file paths for robust comparison.
        # This handles differences in case, path separators ('/' vs '\'), and spaces vs underscores.
        normalized_remote_names = {normalize_path(f['name']) for f in item.files}
        print(f"Found {len(normalized_remote_names)} remote files (after normalization).")

        # Add a local file to the upload list ONLY if its normalized path
        # is not found in the set of normalized remote paths.
        to_upload = [
            str(p.relative_to(cwd).as_posix()) for p in all_local_files
            if normalize_path(str(p.relative_to(cwd).as_posix())) not in normalized_remote_names
        ]
    else:
        print("Item does not exist. Preparing for CREATE mode.")
        to_upload = [str(p.relative_to(cwd).as_posix()) for p in all_local_files]

    # --- UPLOAD LOGIC (Unchanged) ---
    if to_upload:
        print(f"\nStarting upload of {len(to_upload)} file(s) to '{IDENT}'.\n")
        
        # This flag ensures metadata is only sent with the first file of a new item
        is_new_item_creation = not item.exists 

        for index, file_path in enumerate(to_upload):
            print(f"[{index + 1}/{len(to_upload)}] Uploading: {file_path}")
            
            # Prepare arguments for this single file
            upload_kwargs = {'retries': 3}
            
            # If we are creating a new item, add metadata ONLY for the very first file
            if is_new_item_creation:
                upload_kwargs['metadata'] = {'title': cwd.name, 'collection': 'opensource'}
                # After this first file, the item will exist, so we turn off the flag
                is_new_item_creation = False
            
            try:
                # The 'files' argument must be a list, even with just one file
                # We add verbose=True for potentially more detailed library output
                for status in ia.upload(IDENT, files=[file_path], verbose=True, **upload_kwargs):
                    # The status from a single file upload will likely just be a progress percentage
                    print(f"  -> Status: {status}")
                print(f"[{index + 1}/{len(to_upload)}] Completed: {file_path}\n")
            except Exception as e:
                print(f"[ERROR] Failed to upload {file_path}: {e}\n")

    else:
        if item.exists:
            print("No new files to upload. The item is already in sync.")
        else:
            print("No files found in this directory. Cannot create an empty item.")

    print("Done.")

if __name__ == '__main__':
    main()