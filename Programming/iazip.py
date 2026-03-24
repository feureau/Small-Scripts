#!/usr/bin/env python3

r"""
INTERNET ARCHIVE COMPATIBILITY DOCUMENTATION AND SCRIPT SPECIFICATION

1. Internet Archive (IA) Derivation Protocol:
The Internet Archive utilizes an automated derivation engine. When an archive file 
bearing the suffix _images.zip (or _images.tar) is uploaded, the server initiates
an extraction sequence. The system identifies files with specific image extensions 
(.jp2, .jpg, .jpeg, .tif, .tiff, .bmp, .png), matching case-insensitively. 
Files possessing non-compliant extensions (e.g., .xml, .txt) are bypassed during 
this derivation. The compliant image files are subsequently sorted alphabetically, 
converted into JPEG2000 format, and repacked into a _jp2.zip archive to facilitate 
the online BookReader interface.

2. Script Updates (Current Version):
- Argument Parsing: Integrated `argparse` to handle the new execution logic. 
  The script now defaults to deleting original files after successful ZIP creation.
- Move Flag (-m, --move): If this flag is toggled, the script reverts to the 
  previous behavior of relocating originals to an external sibling folder 
  suffixed with "_original".
- Path Logic: Remains standardized to use absolute paths, ensuring that 
  deletion and movement operations target the correct filesystem nodes.
- Safety: Files are only deleted or moved AFTER the `zipfile` context manager 
  successfully closes, ensuring the archive is written to disk first.

3. Script Operational Logic and Line-by-Line Elucidation:
- import argparse: Standard library for parsing command-line options and flags.
- parser.add_argument('-m', '--move', action='store_true'): Defines the toggle 
  for the relocation logic.
- def process_directory(base_dir, move_mode):: Accepts the boolean flag to 
  determine post-archival file handling.
- os.remove(source_file): The default operation; performs unrecoverable 
  deletion of the source images to save local storage.
- shutil.move(...): Triggered only if `move_mode` is True; preserves files 
  externally.
- sys.exit(130): Standard exit code for user-initiated termination.
"""

import os
import shutil
import zipfile
import re
import sys
import argparse

def process_directory(base_dir, move_mode):
    base_dir = os.path.abspath(base_dir)
    valid_exts = ('.jpg', '.jpeg', '.jp2', '.tif', '.tiff', '.bmp', '.png')
    
    # Setup pool directory only if move_mode is enabled
    pool_dir = None
    if move_mode:
        parent_dir = os.path.dirname(base_dir)
        folder_name = os.path.basename(base_dir)
        pool_dir = os.path.join(parent_dir, f"{folder_name}_original")

    for root, dirs, files in os.walk(base_dir):
        file_groups = {}

        for f in files:
            if f.lower().endswith(valid_exts):
                # Regex isolates prefix (e.g., Scan_001.jpg -> Scan)
                match = re.search(r'^(.*?)(?:_|-)?\d+\.[a-zA-Z0-9]+$', f)
                
                if match and match.group(1):
                    prefix = match.group(1).strip('_-')
                else:
                    prefix = os.path.basename(root)
                
                if not prefix:
                    prefix = "ia_archive_set"

                file_groups.setdefault(prefix, []).append(f)

        for prefix, group_files in file_groups.items():
            if not group_files:
                continue

            group_files.sort()
            zip_name = f"{prefix}_images.zip"
            zip_path = os.path.join(root, zip_name)

            print(f"Archiving {len(group_files)} files to {zip_name}...")
            
            # Create the ZIP archive
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
                for gf in group_files:
                    zf.write(os.path.join(root, gf), arcname=gf)

            # Post-Archival Handling
            if move_mode:
                rel_path = os.path.relpath(root, base_dir)
                target_dir = os.path.normpath(os.path.join(pool_dir, rel_path))
                os.makedirs(target_dir, exist_ok=True)
                
                for gf in group_files:
                    source_file = os.path.join(root, gf)
                    destination_file = os.path.join(target_dir, gf)
                    shutil.move(source_file, destination_file)
                print(f"Done. Originals moved to: {target_dir}")
            else:
                for gf in group_files:
                    source_file = os.path.join(root, gf)
                    os.remove(source_file)
                print(f"Done. Originals deleted.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IA Image Zipper: Archive image sets for Internet Archive unpacking.")
    parser.add_argument('-m', '--move', action='store_true', 
                        help="Move original files to an external '_original' folder instead of deleting them.")
    
    args = parser.parse_args()
    
    current_working_directory = os.getcwd()
    try:
        process_directory(current_working_directory, args.move)
    except KeyboardInterrupt:
        print("\n\nUser interrupted (Ctrl+C). Exiting gracefully...")
        sys.exit(130)