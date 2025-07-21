#!/usr/bin/env python3
"""
iaconsolidate.py

A utility script to reorganize and consolidate files within an Internet Archive item.
This script is resumable. If it's interrupted, it will skip any steps that
have already been completed (downloading, staging, uploading).

Functionality:
 1. Downloads all files from the specified IA item, skipping any already present locally.
 2. Stages all downloaded files under a single subfolder, skipping any already staged.
 3. Checks for files already on the Internet Archive in the target folder.
 4. Reuploads only the missing staged files into the same IA item, using the prefix as a virtual folder.

Usage:
    python iaconsolidate.py <identifier> [<folder_name>]

Arguments:
    identifier   (required) Archive.org item identifier to process.
    folder_name  (optional) Name of the target virtual folder; defaults to the identifier if omitted.

Example:
    python iaconsolidate.py eap-1268-babad-diponegoro-v-1-0001 "Babad Diponegoro Jilid 1"

Requirements:
  - Python 3.x
  - internetarchive module (pip install internetarchive)
  - Internet connectivity and valid IA credentials (ia.configure)

Behavior:
  - Creates download and staging directories if they don't exist.
  - Skips downloading, staging, and uploading of files that are already in place.
  - Prints progress and status at each step.

Caution:
  - Reuploading large items may take time and count against upload quotas.
  - This script is designed to consolidate. It does not delete the original root-level files.
"""
import sys
import shutil
from pathlib import Path
import internetarchive as ia

def main():
    if len(sys.argv) < 2:
        print("Usage: python iaconsolidate.py <identifier> [<folder_name>]")
        sys.exit(1)

    IDENT = sys.argv[1]
    TARGET_FOLDER = sys.argv[2] if len(sys.argv) > 2 else IDENT

    # Directories
    download_dir = Path(IDENT)
    stage_dir = Path("stage_upload") / TARGET_FOLDER

    # --- Step 1: Download all files for the item locally ---
    # The download function automatically skips files that already exist and are complete.
    print(f"--- Step 1: Downloading item '{IDENT}' ---")
    print("(Will skip any files already downloaded)")
    download_dir.mkdir(exist_ok=True)
    ia.download(IDENT, destdir=str(download_dir), verbose=True)
    print("Download check complete.")

    # --- Step 2: Stage files under a single folder prefix ---
    print(f"\n--- Step 2: Staging files for upload under '{TARGET_FOLDER}/' ---")
    stage_dir.mkdir(parents=True, exist_ok=True)
    for file_path in download_dir.iterdir():
        if file_path.is_file():
            dest = stage_dir / file_path.name
            if dest.exists():
                print(f"Already staged, skipping: {file_path.name}")
                continue
            
            shutil.copy2(file_path, dest)
            print(f"Staged: {file_path.name}")
    print("Staging complete.")

    # --- Step 3: Reupload staged files into the item with folder prefix ---
    print(f"\n--- Step 3: Uploading to '{IDENT}/{TARGET_FOLDER}/' ---")
    
    # First, get a list of files already present on the Internet Archive item
    print("Checking for already uploaded files...")
    try:
        item = ia.get_item(IDENT)
        remote_files = {f['name'] for f in item.files}
        print(f"Found {len(remote_files)} files on the remote item.")
    except Exception as e:
        print(f"Could not retrieve item details from Internet Archive: {e}")
        sys.exit(1)

    # Then, create a map of {local_path: remote_key} for files that need uploading
    files_to_upload_map = {}
    for local_path in stage_dir.rglob('*'):
        if local_path.is_file():
            # The remote 'key' is the full path inside the IA item
            remote_key = f"{TARGET_FOLDER}/{local_path.name}"
            
            if remote_key in remote_files:
                print(f"Already on server, skipping: {local_path.name}")
            else:
                print(f"Queued for upload: {local_path.name}")
                # The key must be the local file path, value is the remote name
                files_to_upload_map[str(local_path)] = remote_key

    # Finally, upload the files that are not on the server yet
    if not files_to_upload_map:
        print("\nAll files are already consolidated on the Internet Archive. No upload needed.")
    else:
        print(f"\nUploading {len(files_to_upload_map)} new files...")
        try:
            # The 'files' argument can be a dictionary mapping local paths to remote keys
            response = ia.upload(IDENT, files=files_to_upload_map)
            # The response object in modern versions is a requests.Response array
            if isinstance(response, list) and len(response) > 0 and hasattr(response[0], 'status_code'):
                 for r in response:
                    print(f"Upload Status {r.status_code}: {r.reason}")
            else: # Fallback for other response types
                 print("Upload request sent. Check item page for progress.")

        except Exception as e:
            print(f"An error occurred during upload: {e}")

    print("\nDone.")

if __name__ == '__main__':
    main()