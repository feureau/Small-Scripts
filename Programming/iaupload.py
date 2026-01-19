"""
SCRIPT: iaupload.py
PURPOSE: Internet Archive (archive.org) Smart Uploader & Syncer
AUTHOR: Assistant (AI)
DATE: 2026-01-19
VERSION: 6.0 (CLI Args & Custom Threads)

================================================================================
DOCUMENTATION & UPDATE POLICY
================================================================================
1. STRICT UPDATE RULE: 
   Any future modifications to this script MUST be documented in the "CHANGE LOG".
   
2. RECURSIVE NOTICE REQUIREMENT:
   This documentation block must be included in every version of the script.

================================================================================
ARCHITECTURE & DESIGN RATIONALE
================================================================================
1. ARGUMENT PARSING (argparse)
   - REASON: To support standard flags like -h and custom configurations without
     fragile manual list index checking of sys.argv.
   - LOGIC: We use 'argparse' to handle positional arguments (folder, id) optionally,
     while adding flagged arguments for settings (threads).

2. CUSTOM THREADING
   - REASON: Different users have different bandwidths. 5 threads might be too slow
     for a Gigabit connection, or too fast for a weak CPU.
   - LOGIC: The user can now override MAX_WORKERS via the '-t' flag.

3. CORE LOGIC (Inherited)
   - Graceful Shutdown (Event-based).
   - MD5 Verification (Content-based sync).
   - ProgressWrapper (Seek/Tell compliant).
   - Visual Dashboard (tqdm).

================================================================================
CHANGE LOG
================================================================================
[2026-01-19] VERSION 6.0 UPDATE
   - ADDED: 'argparse' library integration.
   - ADDED: '-t' / '--threads' flag to customize upload concurrency.
   - ADDED: '-h' / '--help' automatic generation.
   - MODIFIED: Replaced manual sys.argv parsing with args object.
   - MODIFIED: Dynamic UI spacing based on variable thread count.

[2026-01-19] VERSION 5.1 UPDATE
   - Fixed 'seek' error in ProgressWrapper.

[2026-01-19] VERSION 5.0 UPDATE
   - Graceful Exit & Reporting.

================================================================================
"""

import sys
import os
import hashlib
import queue
import threading
import time
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from internetarchive import upload, get_session, get_item

# --- TRY IMPORTING TQDM ---
try:
    from tqdm import tqdm
except ImportError:
    print("Error: This version requires 'tqdm'.")
    print("Please run: pip install tqdm")
    sys.exit(1)

# --- GLOBALS ---
shutdown_event = threading.Event()
results_lock = threading.Lock()
final_results = {
    'success': [],
    'failed': [],
    'cancelled': []
}

# --- HELPER CLASSES ---

class ProgressWrapper:
    """Wraps file object to update tqdm bar on read."""
    def __init__(self, filepath, bar):
        self._file = open(filepath, 'rb')
        self._bar = bar
        self._len = os.path.getsize(filepath)

    def read(self, size=-1):
        if shutdown_event.is_set():
            return b"" 
        data = self._file.read(size)
        self._bar.update(len(data))
        return data

    def seek(self, offset, whence=0):
        return self._file.seek(offset, whence)

    def tell(self):
        return self._file.tell()

    def __len__(self):
        return self._len

    def close(self):
        self._file.close()

# --- HELPER FUNCTIONS ---

def normalize_path(path_str):
    return path_str.lower().replace('\\', '/').replace(' ', '_')

def calculate_md5(filepath, block_size=8192):
    md5 = hashlib.md5()
    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(block_size), b""):
                if shutdown_event.is_set(): return None
                md5.update(chunk)
        return md5.hexdigest()
    except Exception:
        return None

def print_requirements():
    print("\n" + "="*50)
    print("PRE-UPLOAD CHECKLIST")
    print("="*50)
    print("1. [TARGET FOLDER] Path to files.")
    print("2. [IDENTIFIER]    Unique URL slug.")
    print("3. [METADATA]      Title, Mediatype, etc.")
    print("-" * 50)
    input("Press Enter to continue...")

def get_input(prompt_text, required=False, default=None, valid_options=None):
    while True:
        display = f"{prompt_text} [{default}]: " if default else f"{prompt_text}: "
        try:
            val = input(display).strip()
        except KeyboardInterrupt:
            sys.exit(1) 
            
        if not val and default: return default
        if required and not val:
            print("  Error: Required.")
            continue
        if valid_options and val not in valid_options:
            print(f"  Error: Choose from {valid_options}")
            continue
        return val

def collect_metadata(default_title):
    print("\n--- METADATA PREPARATION ---")
    print("Required: Title, Mediatype.")
    
    title = get_input("Title", required=True, default=default_title)
    mediatype = get_input("Mediatype", required=True, valid_options=['data', 'image', 'audio', 'texts', 'movies', 'software'])
    
    creator = get_input("Creator", required=False)
    description = get_input("Description", required=False)
    tags_input = get_input("Tags (comma sep)", required=False)
    subjects = [t.strip() for t in tags_input.split(',')] if tags_input else []

    metadata = {'title': title, 'mediatype': mediatype}
    if creator: metadata['creator'] = creator
    if description: metadata['description'] = description
    if subjects: metadata['subject'] = subjects
    return metadata

def record_result(category, name):
    with results_lock:
        final_results[category].append(name)

def print_report():
    print("\n" + "="*60)
    print("FINAL REPORT")
    print("="*60)
    
    s_count = len(final_results['success'])
    f_count = len(final_results['failed'])
    c_count = len(final_results['cancelled'])
    
    print(f"Successful: {s_count}")
    print(f"Failed:     {f_count}")
    print(f"Cancelled:  {c_count}")
    
    if f_count > 0:
        print("-" * 60)
        print("FAILED FILES:")
        for name in final_results['failed']:
            print(f" [x] {name}")
            
    if c_count > 0:
        print("-" * 60)
        print("CANCELLED FILES (Not uploaded):")
        for i, name in enumerate(final_results['cancelled']):
            if i >= 10:
                print(f" ... and {c_count - 10} more.")
                break
            print(f" [-] {name}")

    print("="*60)

def upload_worker(identifier, file_data, metadata=None, position=0):
    remote_key, local_path = file_data
    
    if shutdown_event.is_set():
        record_result('cancelled', remote_key)
        return (False, "Cancelled by user")

    file_size = os.path.getsize(local_path)
    
    display_name = remote_key
    if len(display_name) > 20:
        display_name = "..." + display_name[-17:]

    # leave=False cleans up the bar line when done
    with tqdm(total=file_size, unit='B', unit_scale=True, desc=display_name, 
              position=position, leave=False, dynamic_ncols=True) as bar:
        try:
            wrapped_file = ProgressWrapper(local_path, bar)
            files_arg = {remote_key: wrapped_file}
            
            r = upload(identifier, files=files_arg, metadata=metadata, verbose=False, retries=5)
            
            wrapped_file.close()

            if shutdown_event.is_set():
                record_result('cancelled', remote_key)
                return (False, "Cancelled")

            if r and r[0].status_code == 200:
                record_result('success', remote_key)
                return (True, remote_key)
            else:
                code = r[0].status_code if r else "Unknown"
                record_result('failed', f"{remote_key} (Status {code})")
                return (False, f"Status {code}")
                
        except Exception as e:
            if shutdown_event.is_set():
                record_result('cancelled', remote_key)
                return (False, "Cancelled")
            
            record_result('failed', f"{remote_key} ({str(e)})")
            return (False, str(e))

def main():
    # --- ARGUMENT PARSING ---
    parser = argparse.ArgumentParser(description="Archive.org Smart Uploader & Syncer")
    parser.add_argument("folder", nargs="?", help="Path to local folder")
    parser.add_argument("identifier", nargs="?", help="Unique Archive.org identifier")
    parser.add_argument("-t", "--threads", type=int, default=5, help="Number of parallel upload threads (default: 5)")
    args = parser.parse_args()

    max_workers = args.threads

    print(f"--- Archive.org Smart Uploader (iaupload v6.0) ---")
    print(f"--- Threads: {max_workers} ---")
    
    # 0. Auth
    try:
        if not get_session().access_key:
            print("Error: Not logged in. Run 'ia configure'.")
            sys.exit(1)
    except:
        sys.exit(1)

    try:
        # 1. Inputs (Using args if available, else interactive)
        folder_path_str = args.folder
        identifier = args.identifier

        if folder_path_str:
            folder_path_str = folder_path_str.strip('"').strip("'")
        else:
            print_requirements()
            folder_path_str = get_input("Target Folder", required=True).strip('"').strip("'")
        
        if not os.path.isdir(folder_path_str):
            print("Error: Folder not found.")
            sys.exit(1)

        if not identifier:
            while True:
                identifier = get_input("Identifier", required=True)
                if " " not in identifier and identifier.isascii(): break
                print("Error: Invalid identifier.")

        folder_path = Path(folder_path_str)

        # 2. Remote Check
        print(f"\nChecking '{identifier}'...")
        item = get_item(identifier)
        metadata = {}
        is_new_item = False

        if item.exists:
            # Only ask update question if interactive args were not fully provided 
            # OR just always ask because metadata updates are rare? 
            # Decision: Always ask, but default to 'n'.
            if get_input("Update metadata? (y/n)", default='n').lower() == 'y':
                metadata = collect_metadata(identifier)
        else:
            print(f"  > New item detected.")
            is_new_item = True
            metadata = collect_metadata(identifier)

        # 3. MD5 Scanning Phase
        print("\n" + "="*30)
        print("PHASE 1: CONTENT VERIFICATION")
        print("="*30)
        
        script_name = Path(sys.argv[0]).name
        all_local_files = [p for p in folder_path.rglob('*') if p.is_file() and p.name != script_name]
        
        remote_map = {}
        if item.exists:
            print("Fetching remote signatures...")
            for f in item.files:
                if 'md5' in f:
                    remote_map[normalize_path(f['name'])] = f['md5']

        files_to_upload = [] 
        
        print(f"Scanning {len(all_local_files)} local files...")
        
        with tqdm(total=len(all_local_files), desc="Verifying", unit="file", dynamic_ncols=True) as scan_bar:
            for local_file in all_local_files:
                if shutdown_event.is_set(): break
                
                rel_path = local_file.relative_to(folder_path).as_posix()
                norm_name = normalize_path(rel_path)
                
                disp = rel_path if len(rel_path) < 30 else "..." + rel_path[-27:]
                scan_bar.set_description(f"Check: {disp}")
                
                should_upload = False
                status_msg = ""
                
                if norm_name not in remote_map:
                    should_upload = True
                    status_msg = f"[NEW]    {rel_path}"
                else:
                    local_md5 = calculate_md5(local_file)
                    if not local_md5: break 
                        
                    remote_md5 = remote_map[norm_name]
                    if local_md5 != remote_md5:
                        should_upload = True
                        status_msg = f"[UPDATE] {rel_path}"
                
                if should_upload:
                    files_to_upload.append((rel_path, local_file))
                    tqdm.write(status_msg)
                
                scan_bar.update(1)
            
            scan_bar.set_description("Scan Complete")
            scan_bar.refresh()

        if shutdown_event.is_set():
            print("\nScan Cancelled.")
            print_report()
            sys.exit(0)

        count = len(files_to_upload)
        
        if count == 0:
            if metadata:
                print("\nUpdating metadata only...")
                item.modify_metadata(metadata)
                print("Metadata updated.")
                sys.exit(0)
            print("\nAll files match perfectly. Nothing to do.")
            sys.exit(0)

        print(f"\nQueued {count} files for upload. Starting immediately...")
        print("\n" * 2)

        # 4. Upload Phase
        start_index = 0
        main_bar = tqdm(total=count, desc="Total Uploads", position=0, unit="file", dynamic_ncols=True)

        if is_new_item:
            first_file = files_to_upload[0]
            success, msg = upload_worker(identifier, first_file, metadata, position=1)
            main_bar.update(1)
            if not success:
                main_bar.close()
                print(f"\nCRITICAL ERROR on creation: {msg}")
                sys.exit(1)
            start_index = 1
            metadata = None

        remaining_files = files_to_upload[start_index:]
        
        if remaining_files:
            # Create slots equal to thread count
            slot_queue = queue.Queue()
            for i in range(1, max_workers + 1):
                slot_queue.put(i)

            def worker_wrapper(f_data):
                slot = slot_queue.get() 
                try:
                    return upload_worker(identifier, f_data, None, position=slot)
                finally:
                    slot_queue.put(slot)

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_file = {
                    executor.submit(worker_wrapper, fdata): fdata 
                    for fdata in remaining_files
                }
                
                for future in as_completed(future_to_file):
                    if shutdown_event.is_set():
                        executor.shutdown(wait=False, cancel_futures=True)
                        break
                    main_bar.update(1)

        main_bar.close()
        
        # Ensure enough newline space based on thread count
        print("\n" * (max_workers + 1))
        
        if shutdown_event.is_set():
            print("\nOperation Aborted by User.")
        else:
            print("Operation Complete.")
            print(f"URL: https://archive.org/details/{identifier}")

        print_report()

    except KeyboardInterrupt:
        print("\n\n!!! KEYBOARD INTERRUPT DETECTED !!!")
        print("Stopping threads... Please wait a moment...")
        shutdown_event.set()
        time.sleep(1)
        print_report()
        sys.exit(0)

if __name__ == "__main__":
    main()