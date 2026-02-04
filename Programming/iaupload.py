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
import re
import xml.etree.ElementTree as ET
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
        display = f"{prompt_text} [{default}]: " if default is not None else f"{prompt_text}: "
        try:
            val = input(display).strip()
        except KeyboardInterrupt:
            sys.exit(1) 
            
        if not val and default is not None: return default
        if required and not val:
            print("  Error: Required.")
            continue
        if valid_options and val not in valid_options:
            print(f"  Error: Choose from {valid_options}")
            continue
        return val

def collect_metadata(default_title, prefills=None):
    print("\n--- METADATA PREPARATION ---")
    print("Required: Title, Mediatype.")
    print("Title: Human-readable name shown on the item page; keep it clear and descriptive.")
    print("Mediatype: One of the allowed categories; choose the closest match for the content.")
    print("Creator: Person, group, or organization responsible (optional).")
    print("Description: Short summary of the item contents and context (optional).")
    print("Tags: Comma-separated keywords for search and discovery (optional).")
    if prefills:
        print("Found metadata.xml: fields are prefilled where available. Press Enter to keep defaults.")
    
    title_default = prefills.get("title") if prefills else None
    if not title_default:
        title_default = default_title
    title = get_input("Title", required=True, default=title_default)

    mediatype_default = prefills.get("mediatype") if prefills else None
    mediatype = get_input(
        "Mediatype (data|image|audio|texts|movies|software)",
        required=True,
        default=mediatype_default,
        valid_options=['data', 'image', 'audio', 'texts', 'movies', 'software']
    )
    
    creator_default = prefills.get("creator") if prefills else None
    description_default = prefills.get("description") if prefills else None
    tags_default = prefills.get("tags") if prefills else None
    creator = get_input("Creator", required=False, default=creator_default)
    description = get_input("Description", required=False, default=description_default)
    tags_input = get_input("Tags (comma sep)", required=False, default=tags_default)
    subjects = [t.strip() for t in tags_input.split(',')] if tags_input else []

    metadata = {'title': title, 'mediatype': mediatype}
    if creator: metadata['creator'] = creator
    if description: metadata['description'] = description
    if subjects: metadata['subject'] = subjects
    return metadata

def _xml_text(node):
    if node is None:
        return None
    text = (node.text or "").strip()
    return text if text else None

def load_metadata_xml(folder_path):
    xml_path = folder_path / "metadata.xml"
    if not xml_path.exists():
        return None
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except Exception:
        return None

    def find_text(tag_names):
        for name in tag_names:
            node = root.find(f".//{name}")
            txt = _xml_text(node)
            if txt:
                return txt
        return None

    title = find_text(["title", "Title"])
    mediatype = find_text(["mediatype", "Mediatype"])
    creator = find_text(["creator", "Creator"])
    description = find_text(["description", "Description"])

    # subjects/tags: support repeated <subject> or <tag> nodes
    subjects = [(_xml_text(n) or "") for n in root.findall(".//subject")]
    subjects += [(_xml_text(n) or "") for n in root.findall(".//tag")]
    subjects = [s for s in subjects if s]
    tags = ", ".join(subjects) if subjects else None

    prefills = {}
    if title: prefills["title"] = title
    if mediatype: prefills["mediatype"] = mediatype
    if creator: prefills["creator"] = creator
    if description: prefills["description"] = description
    if tags: prefills["tags"] = tags

    return prefills or None

def sanitize_identifier(raw_identifier):
    # Normalize to ASCII, replace spaces with underscores, and strip invalid chars
    import unicodedata
    norm = unicodedata.normalize("NFKD", raw_identifier)
    ascii_only = norm.encode("ascii", "ignore").decode("ascii")
    cleaned = ascii_only.replace(" ", "_")
    cleaned = "".join(ch for ch in cleaned if ch.isalnum() or ch in "._-")
    cleaned = cleaned.strip("._-")
    if len(cleaned) < 5:
        return cleaned
    return cleaned[:100]

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


try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    pass # Managed in main check

# ... (Previous imports)

def upload_worker(identifier, file_data, metadata=None, position=0, session=None):
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
        
        # RETRY LOOP for Rate Limits
        max_retries = 10
        attempt = 0
        backoff_time = 30 # Start with 30s wait for rate limits
        
        while attempt < max_retries:
            wrapped_file = None
            try:
                wrapped_file = ProgressWrapper(local_path, bar)
                files_arg = {remote_key: wrapped_file}
                
                r = None
                # Use the passed session if available to recycle connections
                if session:
                    # We must use the Item-level API to pass the session
                    # 'session' here is expected to be an ArchiveSession
                    item = get_item(identifier, archive_session=session)
                    r = item.upload(files=files_arg, metadata=metadata, verbose=False, retries=3)
                else:
                    # Fallback to default global upload
                    r = upload(identifier, files=files_arg, metadata=metadata, verbose=False, retries=3)
                
                wrapped_file.close()

                # CRITICAL LOOPHOLE FIX: Explicitly close responses to free connection pool slots immediately
                if r:
                    for resp in r:
                        resp.close()

                if shutdown_event.is_set():
                    record_result('cancelled', remote_key)
                    return (False, "Cancelled")

                if r and r[0].status_code == 200:
                    record_result('success', remote_key)
                    return (True, remote_key)
                
                # Check for rate limiting in status code (if 429 or 503 wasn't handled by custom adapter)
                if r and r[0].status_code in [429, 503, 509]:
                     tqdm.write(f"Rate limited ({r[0].status_code}) for {display_name}. Retrying in {backoff_time}s...")
                     time.sleep(backoff_time)
                     backoff_time = min(backoff_time * 1.5, 300) # Cap at 5 mins
                     attempt += 1
                     bar.reset() # Reset progress bar for retry
                     continue

                code = r[0].status_code if r else "Unknown"
                record_result('failed', f"{remote_key} (Status {code})")
                return (False, f"Status {code}")
                
            except Exception as e:
                # Ensure file is closed on exception
                if wrapped_file: 
                    try: wrapped_file.close()
                    except: pass
                
                if shutdown_event.is_set():
                    record_result('cancelled', remote_key)
                    return (False, "Cancelled")
                
                error_str = str(e).lower()
                # Check specifically for the bucket queue limit or generic rate requests
                if "bucket_tasks_queued" in error_str or "reduce your request rate" in error_str or "read timed out" in error_str:
                    tqdm.write(f"Rate Limit/Timeout hit for {display_name}: {e}. Pausing {backoff_time}s...")
                    time.sleep(backoff_time)
                    backoff_time = min(backoff_time * 1.5, 300)
                    attempt += 1
                    bar.reset()
                    continue
                
                # Real error
                tqdm.write(f"Error uploading {remote_key}: {e}") # Print to console properly with tqdm
                record_result('failed', f"{remote_key} ({str(e)})")
                return (False, str(e))
        
        return (False, "Max Retries Exceeded (Rate Limit)")





def main():
    # --- ARGUMENT PARSING ---
    parser = argparse.ArgumentParser(description="Archive.org Smart Uploader & Syncer")
    parser.add_argument("folder", nargs="?", help="Path to local folder")
    parser.add_argument("identifier", nargs="?", help="Unique Archive.org identifier")
    parser.add_argument("-t", "--threads", type=int, default=5, help="Number of parallel upload/delete threads (default: 5)")
    parser.add_argument("-s", "--sync", action="store_true", help="Sync mode (Upload/Update only)")
    parser.add_argument("-o", "--orphan-deletion", action="store_true", help="Delete remote files that do not exist locally")
    parser.add_argument("-m", "--metadata", action="store_true", help="Force metadata update prompt for existing items")
    args = parser.parse_args()

    max_workers = args.threads

    print(f"--- Archive.org Smart Uploader (iaupload v6.0) ---")
    print(f"--- Threads: {max_workers} ---")
    if args.sync:
        print("--- Mode: SYNC (Uploads) ---")
    if args.orphan_deletion:
        print("--- Mode: DELETE (Orphan Removal Enabled) ---")
    
    # 0. Auth
    try:
        session = get_session()
        if not session.access_key:
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

        # Sanitize identifier to ensure IA-accepted bucket name
        sanitized_identifier = sanitize_identifier(identifier)
        if sanitized_identifier != identifier:
            print(f"Sanitized identifier: {sanitized_identifier}")
            identifier = sanitized_identifier

        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{4,100}", identifier):
            print("Error: Identifier is still invalid after sanitization.")
            print("Please provide a valid identifier matching: ^[A-Za-z0-9][A-Za-z0-9_.-]{4,100}$")
            sys.exit(1)

        folder_path = Path(folder_path_str)

        # 2. Remote Check
        print(f"\nChecking '{identifier}'...")
        item = get_item(identifier)
        metadata = {}
        is_new_item = False
        xml_prefills = load_metadata_xml(folder_path)

        if item.exists:
            # Only ask update question if -m flag is provided
            if args.metadata:
                if get_input("Update metadata? (y/n)", default='n').lower() == 'y':
                    metadata = collect_metadata(identifier, prefills=xml_prefills)
        else:
            print(f"  > New item detected.")
            is_new_item = True
            metadata = collect_metadata(identifier, prefills=xml_prefills)

        # 3. MD5 Scanning Phase
        print("\n" + "="*30)
        print("PHASE 1: CONTENT VERIFICATION")
        print("="*30)
        
        script_name = Path(sys.argv[0]).name
        
        # 3a. Index Local Files
        print("Indexing local files...")
        local_file_map = {} # normalized_path -> Path obj
        for p in folder_path.rglob('*'):
            if p.is_file() and p.name != script_name:
                rel_path = p.relative_to(folder_path).as_posix()
                norm = normalize_path(rel_path)
                local_file_map[norm] = {'path': p, 'rel_path': rel_path}

        # 3b. Index Remote Files
        remote_map = {} # normalized_path -> md5
        remote_content_map = {} # (filename, md5) -> set(normalized_paths)
        remote_pure_md5_map = {} # md5 -> set(normalized_paths)
        total_remote_files = 0
        total_remote_originals = 0
        
        if item.exists:
            print("Fetching remote signatures...")
            total_remote_files = len(item.files)
            for f in item.files:
                if 'name' in f and f['name'] != script_name:
                    if f['source'] == 'original': # Only consider original files
                        total_remote_originals += 1
                        norm_path = normalize_path(f['name'])
                        f_md5 = f.get('md5')
                        
                        remote_map[norm_path] = f_md5
                        
                        # Populate content map for smart matching
                        if f_md5:
                            f_name = os.path.basename(norm_path)
                            key = (f_name, f_md5)
                            if key not in remote_content_map:
                                remote_content_map[key] = set()
                            remote_content_map[key].add(norm_path)

                            # Populate pure md5 map for loose smart matching (different identifier/name)
                            if f_md5 not in remote_pure_md5_map:
                                remote_pure_md5_map[f_md5] = set()
                            remote_pure_md5_map[f_md5].add(norm_path)

        # 3c. Comparison
        files_to_upload = [] 
        orphaned_files = [] # List of remote keys to delete
        accounted_for_remotes = set() # Remote paths that are "kept" due to smart match
        
        matched_count = 0
        moved_count = 0
        smart_count = 0
        upload_new_count = 0
        upload_update_count = 0
        
        # Detect Uploads
        print(f"Scanning {len(local_file_map)} local files against {total_remote_originals} remote originals...")
        
        with tqdm(total=len(local_file_map), desc="Verifying", unit="file", dynamic_ncols=True) as scan_bar:
            for norm_name, info in local_file_map.items():
                if shutdown_event.is_set(): break
                
                local_file = info['path']
                rel_path = info['rel_path']
                
                disp = rel_path if len(rel_path) < 30 else "..." + rel_path[-27:]
                scan_bar.set_description(f"Check: {disp}")
                
                should_upload = False
                status_msg = ""
                
                if norm_name not in remote_map:
                    # Path doesn't exist. Check for Smart Match (if NOT strict mode)
                    is_smart_match = False
                    
                    # Strict mode = -s OR -o. If either is set, we strictly enforce structure (re-upload).
                    if not args.sync and not args.orphan_deletion:
                        local_md5 = calculate_md5(local_file)
                        if local_md5:
                            f_name = os.path.basename(norm_name)
                            key = (f_name, local_md5)
                            
                            # 1. MOVED Check (Same Name, Same Content)
                            if key in remote_content_map:
                                matches = remote_content_map[key]
                                match_path = next(iter(matches))
                                
                                is_smart_match = True
                                status_msg = f"[MOVED]   Found at {match_path} (Skipping)"
                                accounted_for_remotes.add(match_path)
                                moved_count += 1
                            
                            # 2. SMART Check (Different Name, Same Content)
                            elif local_md5 in remote_pure_md5_map:
                                matches = remote_pure_md5_map[local_md5]
                                match_path = next(iter(matches))

                                is_smart_match = True
                                status_msg = f"[SMART]   Found at {match_path} (Skipping)"
                                accounted_for_remotes.add(match_path)
                                smart_count += 1

                    if not is_smart_match:
                        should_upload = True
                        status_msg = f"[NEW]    {rel_path}"
                        upload_new_count += 1
                    else:
                        tqdm.write(status_msg)

                else:
                    # Check MD5
                    local_md5 = calculate_md5(local_file)
                    if not local_md5: break 
                        
                    remote_md5 = remote_map[norm_name]
                    if local_md5 != remote_md5:
                        should_upload = True
                        status_msg = f"[UPDATE] {rel_path}"
                        upload_update_count += 1
                    else:
                        matched_count += 1
                
                if should_upload:
                    files_to_upload.append((rel_path, local_file))
                    tqdm.write(status_msg)
                
                scan_bar.update(1)
            
            scan_bar.set_description("Scan Complete")

        # Detect Orphans
        for r_norm, r_md5 in remote_map.items():
            if r_norm not in local_file_map:
                if r_norm not in accounted_for_remotes:
                     pass
        
        # Re-pass for orphans to get correct casing key
        if item.exists:
            for f in item.files:
                 if f['source'] == 'original' and f['name'] != script_name:
                     norm = normalize_path(f['name'])
                     
                     if norm in local_file_map:
                         continue 
                     if norm in accounted_for_remotes:
                         continue 
                         
                     orphaned_files.append(f['name'])

        if shutdown_event.is_set():
            print("\nScan Cancelled.")
            print_report()
            sys.exit(0)

        # 4. Confirm Actions
        upload_count = len(files_to_upload)
        orphan_count = len(orphaned_files)
        total_local = len(local_file_map)
        
        print("\n" + "="*40)
        print("SUMMARY")
        print("="*40)
        print(f"Total Local Files:       {total_local}")
        print(f"Total Remote Originals:  {total_remote_originals} (of {total_remote_files} total items)")
        print("-" * 40)
        print(f"Matched (Exact):         {matched_count}")
        print(f"Matched (Moved):         {moved_count}")
        print(f"Matched (Smart):         {smart_count}")
        print(f"To Upload (New):         {upload_new_count}")
        print(f"To Upload (Update):      {upload_update_count}")
        print(f"Orphans (To Delete):     {orphan_count}")
        print("="*40)

        files_to_delete = []

        if orphan_count > 0:
            if args.orphan_deletion:
                print(f"\n[DELETE] Auto-selecting {orphan_count} files for deletion.")
                files_to_delete = orphaned_files
            else:
                print("\n[!] Orphaned files found on remote (not in local folder).")
                print("    Use -o / --orphan-deletion to remove them.")

        if upload_count == 0 and len(files_to_delete) == 0:
            if metadata:
                print("\nUpdating metadata only...")
                item.modify_metadata(metadata)
                print("Metadata updated.")
                sys.exit(0)
            print("\nSync complete. No changes needed.")
            sys.exit(0)

        if upload_count > 0:
            print(f"\nQueued {upload_count} files for upload...")
        if len(files_to_delete) > 0:
            print(f"Queued {len(files_to_delete)} files for DELETION...")
        
        # 5. Execution Phase
        print("\n" * 1)
        
        # --- UPLOADS ---
        if upload_count > 0:
            # OPTIMIZATION: Sort by size (Smallest First)
            files_to_upload.sort(key=lambda x: os.path.getsize(x[1]))

            # OPTIMIZATION: Configure Persistent Session (Connection Pooling)
            # Use the official get_session() so we have an ArchiveSession compatible with get_item()
            custom_session = None
            try:
                import requests
                from requests.adapters import HTTPAdapter
                from urllib3.util.retry import Retry
                
                # Get a proper ArchiveSession
                custom_session = get_session()
                
                # Configure Retry and Pooling
                retry_strategy = Retry(
                    total=5,
                    backoff_factor=1,
                    status_forcelist=[429, 500, 502, 503, 504],
                    allowed_methods=["HEAD", "GET", "PUT", "POST", "DELETE", "OPTIONS", "TRACE"]
                )
                
                # Pool size must handle all threads + extra for overhead
                adapter = HTTPAdapter(pool_connections=max_workers+5, pool_maxsize=max_workers+5, max_retries=retry_strategy)
                
                # Helper to mount adapter to ArchiveSession which might behave differently than requests.Session
                if hasattr(custom_session, 'mount_http_adapter'):
                    # Newer IA library support
                    custom_session.mount_http_adapter("https://", adapter)
                    custom_session.mount_http_adapter("http://", adapter)
                else:
                    # Fallback: hope it inherits from Session or has .mount
                    custom_session.mount("https://", adapter)
                    custom_session.mount("http://", adapter)
                
            except Exception as e:
                print(f"Warning: Could not configure connection pool: {e}")
                # Fallback to standard session if mounting fails
                if not custom_session:
                     custom_session = get_session()

            start_index = 0
            main_bar = tqdm(total=upload_count, desc="Uploading", position=0, unit="file", dynamic_ncols=True)

            if is_new_item:
                # Upload the first (smallest) file to initialize the item
                first_file = files_to_upload[0]
                success, msg = upload_worker(identifier, first_file, metadata, position=1, session=custom_session)
                main_bar.update(1)
                if not success:
                    main_bar.close()
                    print(f"\nCRITICAL ERROR on creation: {msg}")
                    sys.exit(1)
                start_index = 1
                metadata = None

            remaining_files = files_to_upload[start_index:]
            
            if remaining_files:
                slot_queue = queue.Queue()
                for i in range(1, max_workers + 1):
                    slot_queue.put(i)

                def worker_wrapper(f_data):
                    slot = slot_queue.get() 
                    try:
                        return upload_worker(identifier, f_data, None, position=slot, session=custom_session)
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



        # --- DELETIONS ---
        if len(files_to_delete) > 0 and not shutdown_event.is_set():
            print("\nStarting Deletions...")
            # Deletes are fast but we can thread them too
            
            del_bar = tqdm(total=len(files_to_delete), desc="Deleting", position=0, unit="file", dynamic_ncols=True)
            
            def delete_worker(fname):
                if shutdown_event.is_set(): return
                try:
                    # item.delete_file is synchronous
                    item.delete_file(fname)
                    # We might want to record success??
                except Exception as e:
                    tqdm.write(f"Failed to delete {fname}: {e}")

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(delete_worker, f) for f in files_to_delete]
                for f in as_completed(futures):
                    del_bar.update(1)
            
            del_bar.close()

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
        print("Stopping threads... (Forcing Exit)")
        shutdown_event.set()
        time.sleep(1)
        print_report()
        os._exit(1)

if __name__ == "__main__":
    main()
