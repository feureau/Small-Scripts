"""
SCRIPT: iaupload.py
PURPOSE: Internet Archive (archive.org) Smart Uploader & Syncer
AUTHOR: Assistant (AI)
DATE: 2026-01-19
VERSION: 2.4 (Streamlined Metadata Flow)

================================================================================
DOCUMENTATION & UPDATE POLICY
================================================================================
1. STRICT UPDATE RULE: 
   Any future modifications to this script MUST be documented in the "CHANGE LOG" 
   section below. ADDITIONALLY, the entire documentation block (including 
   "ARCHITECTURE & DESIGN RATIONALE", "DESCRIPTION", and "USAGE") must be 
   reviewed and updated to accurately reflect the current state of the script. 
   Do not just add a log entry; ensure the explanation of how the script works 
   remains accurate for every part of the code.
   
2. RECURSIVE NOTICE REQUIREMENT:
   This documentation block itself must be included in every version of the script.
   You must explicitly retain this notice stating that documentation is mandatory 
   and must be updated with every iteration.

3. EXPLANATION REQUIREMENT:
   Every change must include the "WHAT" (the code change) and the "WHY" (the 
   reasoning behind the change). Arbitrary changes without justification are 
   forbidden to prevent logic regression.

4. ARCHITECTURE PRESERVATION:
   If core logic (like path normalization or the smart sync diff) is altered, 
   the "ARCHITECTURE & DESIGN RATIONALE" section must be updated.

================================================================================
ARCHITECTURE & DESIGN RATIONALE
================================================================================
1. DEPENDENCY CHOICE: 'internetarchive' Library
   - REASON: We use the official Python library rather than raw HTTP requests 
     because it handles S3-like authentication, automatic retries on connection 
     failure, and large-file streaming natively.

2. PATH NORMALIZATION (The 'normalize_path' function)
   - REASON: Archive.org often converts spaces to underscores and lowercases 
     filenames. We simulate this locally to correctly compare local vs remote files.

3. SMART SYNC STRATEGY (The 'Diff' Logic)
   - REASON: Efficiency. We fetch the remote file list and only upload files 
     that are missing or new locally.

4. CONDITIONAL METADATA FLOW
   - REASON: UX. We only force the metadata interview if the item is NEW. 
     If it exists, we make it optional to speed up daily sync tasks.

================================================================================
CHANGE LOG
================================================================================
[2026-01-19] VERSION 2.4 UPDATE
   - MODIFIED: 'collect_metadata' function.
     - WHAT: Removed the "Press Enter to start entering data..." input pause.
     - WHY: User feedback indicated the pause was unnecessary. The script now 
       flows directly from the requirements list to the first prompt for smoother 
       UX.
   - MODIFIED: Documentation Policy.
     - WHAT: Expanded 'STRICT UPDATE RULE' to explicitly require updating the 
       entire documentation block (Rationale/Architecture), not just the log.
     - WHY: To ensure the documentation never becomes stale or out of sync 
       with the actual code logic.

[2026-01-19] VERSION 2.3 UPDATE
   - MODIFIED: 'collect_metadata' added briefing list.
   - MODIFIED: Added recursive documentation notice.

[2026-01-19] VERSION 2.2 UPDATE
   - ADDED: 'print_requirements()' and Rationale sections.

[2026-01-19] VERSION 2.1 UPDATE
   - REORDERED: Check IA existence *before* asking metadata.

[2026-01-19] VERSION 2.0 MERGE
   - MERGED: Logic from 'iauploadv0.py' (Smart Sync/Resume).

================================================================================
"""

import sys
import os
from pathlib import Path
from internetarchive import upload, get_session, get_item

# --- HELPER FUNCTIONS ---

def normalize_path(path_str):
    """
    Converts a path string to a consistent format for comparison.
    RATIONALE: Archive.org modifies uploaded filenames (spaces -> underscores).
    """
    return path_str.lower().replace('\\', '/').replace(' ', '_')

def print_requirements():
    """
    Displays a pre-interview checklist so the user knows what to expect.
    """
    print("\n" + "="*50)
    print("PRE-UPLOAD CHECKLIST")
    print("="*50)
    print("Before we begin, please ensure you have the following ready:")
    print("1. [TARGET FOLDER] The path to the files on your computer.")
    print("2. [IDENTIFIER]    A unique URL slug (e.g., 'my-vacation-2024').")
    print("3. [METADATA]      Title, Mediatype, Creator, Description, Tags.")
    print("-" * 50)
    print("Press Enter to continue, or Ctrl+C to cancel.")
    input()

def get_input(prompt_text, required=False, default=None, valid_options=None):
    """
    Helper to handle user input with validation and defaults.
    """
    while True:
        if default:
            display_prompt = f"{prompt_text} [{default}]: "
        else:
            display_prompt = f"{prompt_text}: "
        
        user_in = input(display_prompt).strip()

        # Handle Default
        if not user_in and default:
            return user_in if user_in else default

        # Handle Required
        if required and not user_in:
            print("  Error: This field is required.")
            continue

        # Handle Options
        if valid_options:
            if user_in not in valid_options:
                print(f"  Error: Invalid choice. Options are: {', '.join(valid_options)}")
                continue

        return user_in

def collect_metadata(default_title):
    """
    Interactively collects metadata from the user.
    """
    print("\n" + "-"*50)
    print("METADATA PREPARATION")
    print("-"*50)
    print("You will now be asked to provide the following details:")
    print("1. Title (Display Name)")
    print("2. Mediatype (Data, Image, Audio, etc.)")
    print("3. Creator (Author/Artist) [Optional]")
    print("4. Description [Optional]")
    print("5. Subject Tags [Optional]")
    print("-" * 50)
    
    # Removed input() pause here per v2.4 requirements

    print("\n--- Step 1: Basic Info ---")
    title = get_input("Title (Display Name)", required=True, default=default_title)
    
    print("\n--- Step 2: Media Type ---")
    print("Options: [data, image, audio, texts, movies, software]")
    mediatype = get_input("Mediatype", required=True, valid_options=['data', 'image', 'audio', 'texts', 'movies', 'software'])
    
    print("\n--- Step 3: Details (Optional) ---")
    creator = get_input("Creator (Author/Artist)", required=False)
    description = get_input("Description", required=False)
    
    print("\n--- Step 4: Categorization (Optional) ---")
    tags_input = get_input("Subject Tags (comma separated)", required=False)
    subjects = [tag.strip() for tag in tags_input.split(',')] if tags_input else []

    metadata = {
        'title': title,
        'mediatype': mediatype,
    }
    if creator: metadata['creator'] = creator
    if description: metadata['description'] = description
    if subjects: metadata['subject'] = subjects
    
    return metadata

def main():
    print("--- Archive.org Smart Uploader (iaupload v2.4) ---")
    
    # ---------------------------------------------------------
    # 0. Check Authentication
    # ---------------------------------------------------------
    try:
        if not get_session().access_key:
            print("Error: You are not logged in.")
            print("Please run 'ia configure' in your terminal first.")
            sys.exit(1)
    except Exception as e:
        print(f"Error checking session: {e}")
        sys.exit(1)

    folder_path_str = None
    identifier = None

    # ---------------------------------------------------------
    # 1. Check Command Line Arguments
    # ---------------------------------------------------------
    if len(sys.argv) >= 3:
        folder_path_str = sys.argv[1]
        identifier = sys.argv[2]
        folder_path_str = folder_path_str.strip('"').strip("'")
        
        print(f"Command line arguments detected:")
        print(f"  > Target Folder: {folder_path_str}")
        print(f"  > Identifier:    {identifier}")

        if not os.path.isdir(folder_path_str):
            print(f"\nError: The folder '{folder_path_str}' does not exist.")
            sys.exit(1)
        print("-" * 30)

    # ---------------------------------------------------------
    # 2. Interactive Inputs (Conditional)
    # ---------------------------------------------------------
    if not folder_path_str:
        print_requirements()
        
        while True:
            folder_path_str = get_input("Enter the path to the folder to upload", required=True)
            folder_path_str = folder_path_str.strip('"').strip("'")
            if os.path.isdir(folder_path_str):
                break
            else:
                print("  Error: That folder does not exist.")

    if not identifier:
        print("\n--- Identifier Configuration ---")
        while True:
            identifier = get_input("Desired Unique Identifier", required=True)
            if " " in identifier:
                print("  Error: Spaces are not allowed in identifiers.")
            elif not identifier.isascii():
                print("  Error: Identifier must be standard ASCII characters.")
            else:
                break

    # Convert to Path object
    folder_path = Path(folder_path_str)

    # ---------------------------------------------------------
    # 3. Check Remote Item & Conditional Metadata
    # ---------------------------------------------------------
    print(f"\nChecking status of '{identifier}' on Archive.org...")
    
    try:
        item = get_item(identifier)
        metadata = {} 
        
        if item.exists:
            print(f"  > Item found!")
            update_md = get_input("Do you want to update the metadata (Title, Description, etc)? (y/n)", default='n').lower()
            if update_md == 'y':
                metadata = collect_metadata(default_title=identifier)
            else:
                print("  > Skipping metadata setup.")
        else:
            print(f"  > Item '{identifier}' does not exist yet.")
            print("  > Creating a new item requires metadata.")
            metadata = collect_metadata(default_title=identifier)
            
    except Exception as e:
        print(f"Error checking item status: {e}")
        sys.exit(1)

    # ---------------------------------------------------------
    # 4. Smart Sync Logic (The Diff)
    # ---------------------------------------------------------
    print("\n" + "="*30)
    print("CHECKING FILE STATUS...")
    print("="*30)

    # A. Scan Local Files
    print("Scanning local directory...")
    script_name = Path(sys.argv[0]).name
    all_local_files = [p for p in folder_path.rglob('*') if p.is_file() and p.name != script_name]
    print(f"Found {len(all_local_files)} local files.")

    # B. Scan Remote Files
    remote_file_hashes = set()
    if item.exists:
        print("Fetching remote file list for comparison...")
        for f in item.files:
            remote_file_hashes.add(normalize_path(f['name']))
        print(f"Remote item contains {len(remote_file_hashes)} files (normalized).")
    
    # C. Calculate Diff
    files_to_upload = []
    
    for local_file in all_local_files:
        rel_path = local_file.relative_to(folder_path).as_posix()
        norm_path = normalize_path(rel_path)
        
        if norm_path not in remote_file_hashes:
            files_to_upload.append(local_file)

    count_diff = len(files_to_upload)
    count_skip = len(all_local_files) - count_diff

    print("-" * 30)
    print(f"Skipping: {count_skip} files (Already exist).")
    print(f"Uploading: {count_diff} files (New or missing).")
    print("-" * 30)

    # 5. Review and Confirm
    if count_diff == 0:
        if not metadata:
            print("No new files and no metadata changes. Nothing to do.")
            sys.exit(0)
        else:
            print("No new files, but metadata changes detected.")
    
    confirm = input("Ready to proceed? (y/n): ").lower()
    if confirm != 'y':
        print("Cancelled.")
        sys.exit()

    # ---------------------------------------------------------
    # 6. Perform Upload / Update
    # ---------------------------------------------------------
    print(f"\nStarting process for '{identifier}'...")
    
    try:
        # Scenario A: Metadata Update Only
        if count_diff == 0 and metadata:
            print("Updating metadata...")
            item.modify_metadata(metadata)
            print("Metadata updated successfully.")
            sys.exit(0)

        # Scenario B: File Upload (Batched)
        upload_dict = {}
        for fpath in files_to_upload:
            rel_key = fpath.relative_to(folder_path).as_posix()
            upload_dict[rel_key] = str(fpath)

        print(f"Uploading {len(upload_dict)} files...")
        
        responses = upload(
            identifier, 
            files=upload_dict, 
            metadata=metadata, 
            verbose=True, 
            retries=3
        )

        if responses:
            success_codes = [r.status_code for r in responses]
            if 200 in success_codes:
                print("\n" + "*"*40)
                print("SUCCESS!")
                print(f"View your item at: https://archive.org/details/{identifier}")
                print("Note: Processing may take a few minutes.")
                print("*"*40)
            else:
                print(f"Upload finished with codes: {success_codes}")

    except Exception as e:
        print(f"\nError: {e}")
        if "item already exists" in str(e).lower():
            print("Tip: You might not have permission to edit this identifier.")

if __name__ == "__main__":
    main()