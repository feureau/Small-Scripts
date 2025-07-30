#!/usr/bin/env python3
"""
debug_compare.py

A special script to debug file comparison issues with Internet Archive.
This script DOES NOT UPLOAD any files. It only scans local and remote files,
compares them, and prints a detailed report of the comparison logic.

Usage:
  python debug_compare.py <identifier>
"""
import sys
from pathlib import Path
import internetarchive as ia

def normalize_path(path_str):
    """
    Converts a path string to a consistent, comparable format by making it
    lowercase, ensuring forward slashes, and replacing spaces with underscores.
    """
    return path_str.lower().replace('\\', '/').replace(' ', '_')

def main():
    cwd = Path.cwd()
    script_name = Path(sys.argv[0]).name
    
    print("Scanning for all files recursively...")
    all_local_files = [p for p in cwd.rglob('*') if p.is_file() and p.name != script_name]
    print(f"Found {len(all_local_files)} local files.")

    if len(sys.argv) > 1:
        IDENT = sys.argv[1]
    else:
        print("ERROR: Please provide the Internet Archive identifier as an argument.")
        return
    
    print(f"Target Internet Archive identifier: '{IDENT}'")

    item = ia.get_item(IDENT)
    to_upload = []
    skipped_count = 0

    if not item.exists:
        print("Item does not exist. No comparison to perform.")
        return

    print("\n--- STARTING DEBUG COMPARISON ---")
    
    # 1. Get and normalize remote files
    print("\n[1/3] Fetching and normalizing remote file list...")
    normalized_remote_names = {normalize_path(f['name']) for f in item.files}
    print(f"Found {len(normalized_remote_names)} unique normalized remote files.")
    
    # Print the first 20 remote names to see their format
    print("\nSample of the first 20 NORMALIZED remote names:")
    for i, name in enumerate(list(normalized_remote_names)[:20]):
        print(f"  - \"{name}\"")
    
    # 2. Iterate through local files and compare
    print("\n[2/3] Comparing every local file to the remote list...")
    for p in all_local_files:
        local_relative_path = str(p.relative_to(cwd).as_posix())
        normalized_local_path = normalize_path(local_relative_path)
        
        # Check if the normalized local path is in the remote set
        if normalized_local_path not in normalized_remote_names:
            to_upload.append(local_relative_path)
            status = "NOT FOUND in remote set -> MARKED FOR UPLOAD"
        else:
            skipped_count += 1
            status = "FOUND in remote set -> SKIPPED"
            
        # Print the detailed comparison for the FIRST 20 files that FAILED the check
        if status.endswith("UPLOAD") and len(to_upload) <= 20:
             print(f"\n- Local File: \"{local_relative_path}\"")
             print(f"  - Normalized to: \"{normalized_local_path}\"")
             print(f"  - Status: {status}")

    # 3. Print summary
    print("\n\n[3/3] --- DEBUG COMPARISON COMPLETE ---")
    print(f"\nSummary:")
    print(f"  - Total local files checked: {len(all_local_files)}")
    print(f"  - Files MARKED FOR UPLOAD: {len(to_upload)}")
    print(f"  - Files MARKED FOR SKIP:   {skipped_count}")

    if len(to_upload) > 0:
        print("\nFirst 10 files that would have been uploaded:")
        for file_path in to_upload[:10]:
            print(f"  - {file_path}")

    print("\nDebug script finished. No files were uploaded.")

if __name__ == '__main__':
    main()