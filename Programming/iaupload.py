"""
SCRIPT: iaupload.py
PURPOSE: Internet Archive (archive.org) Smart Uploader & Syncer
AUTHOR: Assistant (AI)
DATE: 2026-01-19
VERSION: 6.7 (Account Collection Hints)

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
[2026-04-11] VERSION 6.8 UPDATE
   - ADDED: Automatic detection and renaming of DJI .LRF files to .MP4 with '_s' suffix.
   - ADDED: --fix-lrf flag for automated LRF renaming without a prompt.

[2026-04-03] VERSION 6.7 UPDATE
   - ADDED: Best-effort display of collections available to the current account during metadata prompt.
   - MODIFIED: Collection prompt now shows account collection options (when retrievable) before input.

[2026-04-03] VERSION 6.6 UPDATE
   - ADDED: Empty (0-byte) local files are skipped during scan and never queued for upload.
   - ADDED: Summary now reports the number of skipped empty files.
   - ADDED: Defensive upload_worker guard to skip zero-byte files if encountered.
   - MODIFIED: Collection metadata is now explicitly prompted, with safer fallback for restricted prefilled collections.
[2026-03-24] VERSION 6.5 UPDATE
   - ADDED: --verbose / -v flag for detailed debug logging during uploads.
   - ADDED: HTTP socket timeout (30s connect, 300s read) to prevent infinite hangs.
   - ADDED: Periodic liveness reporting showing in-flight files during upload.
   - ADDED: Thread lifecycle, slot acquisition, and HTTP timing logs in verbose mode.
   - FIXED: Upload freeze caused by missing HTTP timeout on item.upload() calls.

[2026-03-24] VERSION 6.4 UPDATE
   - ADDED: Fast size comparison check during scan phase to identify incomplete uploads instantly.
   - MODIFIED: Size verification is now checked on all files. MD5 runs afterwards if enabled.

[2026-03-04] VERSION 6.3 UPDATE
   - ADDED: `--md5-verify` flag to enable same-path MD5 comparison during scan.
   - MODIFIED: Default scan now uses path-only matching unless MD5 flag is provided.
   - VERIFIED: `-h` / `--help` CLI help output works with argparse.

[2026-03-03] VERSION 6.2 UPDATE
   - MODIFIED: MD5 is now computed only when the same normalized path exists remotely.
   - REMOVED: Cross-path smart content matching during scan (MOVED/SMART checks).
   - MODIFIED: Orphan detection simplified to pure path-based comparison.

[2026-03-03] VERSION 6.1 UPDATE
   - ADDED: Support for metadata prefills from `metadata.json`.
   - ADDED: Unified metadata prefill loader for XML/JSON.
   - MODIFIED: Prefill source selection now checks XML first, then JSON.

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
import shutil
import os
import hashlib
import queue
import threading
import time
import argparse
import re
import json
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
VERBOSE = False  # Set by --verbose flag

# --- CONFIGURATION DEFAULTS ---
DEFAULT_THREADS = 3
MAX_RETRIES = 10
RETRY_BACKOFF_START = 30
MAX_BACKOFF_TIME = 300
CONNECT_TIMEOUT = 30
READ_TIMEOUT = 300

def vlog(msg):
    """Print a verbose debug message with timestamp and thread ID."""
    if VERBOSE:
        ts = time.strftime('%H:%M:%S')
        tid = threading.current_thread().name
        tqdm.write(f"  [VERBOSE {ts} {tid}] {msg}")

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

def get_account_collections(session):
    """
    Best-effort fetch of collections writable/available to the current account.
    Returns a sorted list of collection identifiers, or [] on failure.
    """
    if not session:
        return []

    endpoints = [
        "https://archive.org/services/xauthn/?op=userinfo",
        "https://archive.org/services/xauthn/?op=account"
    ]

    for url in endpoints:
        try:
            resp = session.get(url, timeout=(10, 30))
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            continue

        collections = []
        if isinstance(data, dict):
            if isinstance(data.get("collections"), list):
                collections = data["collections"]
            elif isinstance(data.get("user"), dict) and isinstance(data["user"].get("collections"), list):
                collections = data["user"]["collections"]

        out = []
        for c in collections:
            if isinstance(c, str) and c.strip():
                out.append(c.strip())
            elif isinstance(c, dict):
                val = c.get("identifier") or c.get("name")
                if isinstance(val, str) and val.strip():
                    out.append(val.strip())

        if out:
            return sorted(set(out))

    return []


def collect_metadata(default_title, prefills=None, account_collections=None):
    print("\n--- METADATA PREPARATION ---")
    print("Required: Title, Mediatype.")
    print("Title: Human-readable name shown on the item page; keep it clear and descriptive.")
    print("Mediatype: One of the allowed categories; choose the closest match for the content.")
    print("Creator: Person, group, or organization responsible (optional).")
    print("Description: Short summary of the item contents and context (optional).")
    print("Tags: Comma-separated keywords for search and discovery (optional).")
    if prefills:
        print("Found metadata file: fields are prefilled where available. Press Enter to keep defaults.")
    
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
    collection_default = prefills.get("collection") if prefills else None
    creator = get_input("Creator", required=False, default=creator_default)
    description = get_input("Description", required=False, default=description_default)
    subjects_val = get_input("Tags (comma sep)", required=False, default=tags_default)
    subjects = [t.strip() for t in subjects_val.split(',')] if subjects_val else []

    # --- LICENSE SELECTION ---
    print("\nSelect a License (Press Enter for GPLv3 default):")
    license_options = {
        '1': ('GPLv3', 'https://www.gnu.org/licenses/gpl-3.0.html'),
        '2': ('CC BY 4.0', 'https://creativecommons.org/licenses/by/4.0/'),
        '3': ('CC BY-SA 4.0', 'https://creativecommons.org/licenses/by-sa/4.0/'),
        '4': ('CC BY-ND 4.0', 'https://creativecommons.org/licenses/by-nd/4.0/'),
        '5': ('CC BY-NC 4.0', 'https://creativecommons.org/licenses/by-nc/4.0/'),
        '6': ('CC BY-NC-SA 4.0', 'https://creativecommons.org/licenses/by-nc-sa/4.0/'),
        '7': ('CC BY-NC-ND 4.0', 'https://creativecommons.org/licenses/by-nc-nd/4.0/'),
        '8': ('CC0 1.0 (Public Domain)', 'https://creativecommons.org/publicdomain/zero/1.0/'),
        '9': ('PDM 1.0 (Public Domain Mark)', 'https://creativecommons.org/publicdomain/mark/1.0/'),
        '0': ('Custom URL / None', None)
    }

    for key, (name, _) in license_options.items():
        print(f"  [{key}] {name}")

    license_default = prefills.get("licenseurl") if prefills else None
    
    # Map prefilled URL back to an option number if possible for display
    default_key = '1' # GPLv3 default
    if license_default:
        for k, (name, url) in license_options.items():
            if url == license_default:
                default_key = k
                break
        else:
            default_key = '0' # Custom

    choice = get_input("Choose license", default=default_key)
    
    selected_url = None
    if choice in license_options:
        selected_url = license_options[choice][1]
        
    if choice == '0' or (choice not in license_options and choice):
        # If they chose custom or typed a random string that isn't a key
        if choice not in license_options:
            selected_url = choice # Treat as custom URL if not a key
        else:
            selected_url = get_input("Custom License URL (leave empty for none)", default=license_default)

    metadata = {'title': title, 'mediatype': mediatype}
    if selected_url:
        metadata['licenseurl'] = selected_url

    # Map mediatype to default community collection
    collection_map = {
        'texts': 'opensource',
        'audio': 'opensource_audio',
        'movies': 'opensource_movies',
        'image': 'opensource_image',
        'software': 'open_source_software',
        'data': 'opensource_media'
    }
    
    public_collections = set(collection_map.values())
    suggested_collection = collection_default
    if suggested_collection and suggested_collection not in public_collections:
        print(f"Warning: Prefilled collection '{suggested_collection}' may be restricted for your account.")
        suggested_collection = collection_map.get(mediatype)
    if not suggested_collection:
        suggested_collection = collection_map.get(mediatype)

    if account_collections:
        print("Available collections for this account:")
        print("  " + ", ".join(account_collections))

    collection = get_input("Collection", required=False, default=suggested_collection)
    if collection:
        metadata['collection'] = collection

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
    collection = find_text(["collection", "Collection"])
    licenseurl = find_text(["licenseurl", "LicenseURL", "license", "License"])

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
    if collection: prefills["collection"] = collection
    if licenseurl: prefills["licenseurl"] = licenseurl

    return prefills or None

def load_metadata_json(folder_path):
    json_path = folder_path / "metadata.json"
    if not json_path.exists():
        return None
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return None

    if not isinstance(data, dict):
        return None
    if isinstance(data.get("metadata"), dict):
        data = data["metadata"]

    def get_str(keys):
        for key in keys:
            val = data.get(key)
            if isinstance(val, str):
                cleaned = val.strip()
                if cleaned:
                    return cleaned
        return None

    title = get_str(["title", "Title"])
    mediatype = get_str(["mediatype", "Mediatype"])
    creator = None
    creator_val = data.get("creator")
    if isinstance(creator_val, list):
        creators = [str(c).strip() for c in creator_val if str(c).strip()]
        if creators:
            creator = "; ".join(creators)
    elif isinstance(creator_val, str) and creator_val.strip():
        creator = creator_val.strip()
    if not creator:
        creator = get_str(["Creator"])
    description = get_str(["description", "Description"])
    collection = get_str(["collection", "Collection"])
    licenseurl = get_str(["licenseurl", "LicenseURL", "license", "License"])

    tags = None
    subjects_val = data.get("subject")
    if subjects_val is None:
        subjects_val = data.get("Subject")
        
    if isinstance(subjects_val, list):
        subjects = [str(s).strip() for s in subjects_val if str(s).strip()]
        if subjects:
            tags = ", ".join(subjects)
    elif isinstance(subjects_val, str) and subjects_val.strip():
        tags = subjects_val.strip()

    if not tags:
        tags_val = data.get("tags")
        if tags_val is None:
            tags_val = data.get("Tags")
            
        if isinstance(tags_val, list):
            tag_list = [str(s).strip() for s in tags_val if str(s).strip()]
            if tag_list:
                tags = ", ".join(tag_list)
        elif isinstance(tags_val, str) and tags_val.strip():
            tags = tags_val.strip()

    prefills = {}
    if title: prefills["title"] = title
    if mediatype: prefills["mediatype"] = mediatype
    if creator: prefills["creator"] = creator
    if description: prefills["description"] = description
    if tags: prefills["tags"] = tags
    if collection: prefills["collection"] = collection
    if licenseurl: prefills["licenseurl"] = licenseurl

    return prefills or None

def load_metadata_prefills(folder_path):
    # Prefer XML when both files exist to preserve existing behavior.
    prefills = load_metadata_xml(folder_path)
    if prefills:
        return prefills
    return load_metadata_json(folder_path)

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
    if file_size == 0:
        tqdm.write(f"Skipping empty file: {remote_key}")
        record_result('cancelled', remote_key)
        return (False, "Skipped empty file (0 bytes)")

    display_name = remote_key
    if len(display_name) > 20:
        display_name = "..." + display_name[-17:]

    vlog(f"START upload_worker for '{remote_key}' ({file_size:,} bytes)")

    # leave=False cleans up the bar line when done
    with tqdm(total=file_size, unit='B', unit_scale=True, unit_divisor=1024, desc=display_name, 
              position=position, leave=False, dynamic_ncols=True,
              bar_format="{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} | Speed: {rate_fmt} | Time: {elapsed}<{remaining}") as bar:
        
        # RETRY LOOP for Rate Limits
        max_retries = MAX_RETRIES
        attempt = 0
        backoff_time = RETRY_BACKOFF_START # Start wait for rate limits
        
        while attempt < max_retries:
            wrapped_file = None
            try:
                vlog(f"  Attempt {attempt+1}/{max_retries} for '{remote_key}'")
                wrapped_file = ProgressWrapper(local_path, bar)
                files_arg = {remote_key: wrapped_file}
                
                r = None
                upload_start = time.time()
                # Use the passed session if available to recycle connections
                if session:
                    # We must use the Item-level API to pass the session
                    # 'session' here is expected to be an ArchiveSession
                    vlog(f"  get_item('{identifier}') via session...")
                    item = get_item(identifier, archive_session=session)
                    vlog(f"  Calling item.upload() for '{remote_key}'...")
                    r = item.upload(files=files_arg, metadata=metadata, verbose=False, retries=3,
                                    request_kwargs={'timeout': (CONNECT_TIMEOUT, READ_TIMEOUT)})
                else:
                    # Fallback to default global upload
                    vlog(f"  Calling upload() (no session) for '{remote_key}'...")
                    r = upload(identifier, files=files_arg, metadata=metadata, verbose=False, retries=3,
                               request_kwargs={'timeout': (CONNECT_TIMEOUT, READ_TIMEOUT)})
                
                upload_elapsed = time.time() - upload_start
                vlog(f"  upload() returned for '{remote_key}' in {upload_elapsed:.1f}s")
                
                # CRITICAL LOOPHOLE FIX: Explicitly close responses to free connection pool slots immediately
                if r:
                    for resp in r:
                        vlog(f"  Response status={resp.status_code} for '{remote_key}'")
                        resp.close()

                if shutdown_event.is_set():
                    record_result('cancelled', remote_key)
                    return (False, "Cancelled")

                if r and r[0].status_code == 200:
                    vlog(f"  SUCCESS for '{remote_key}' (took {upload_elapsed:.1f}s)")
                    record_result('success', remote_key)
                    return (True, remote_key)
                
                # Check for rate limiting in status code (if 429 or 503 wasn't handled by custom adapter)
                if r and r[0].status_code in [429, 503, 509]:
                     tqdm.write(f"Rate limited ({r[0].status_code}) for {display_name}. Retrying in {backoff_time}s...")
                     vlog(f"  Rate limited ({r[0].status_code}), sleeping {backoff_time}s...")
                     time.sleep(backoff_time)
                     backoff_time = min(backoff_time * 1.5, MAX_BACKOFF_TIME) # Cap max sleep
                     attempt += 1
                     bar.reset() # Reset progress bar for retry
                     continue

                code = r[0].status_code if r else "Unknown"
                tqdm.write(f"FAILED {display_name}: HTTP {code}")
                vlog(f"  FAILED '{remote_key}' with HTTP {code}")
                record_result('failed', f"{remote_key} (Status {code})")
                return (False, f"Status {code}")
                
            except Exception as e:
                if shutdown_event.is_set():
                    record_result('cancelled', remote_key)
                    return (False, "Cancelled")
                
                error_str = str(e).lower()
                vlog(f"  EXCEPTION for '{remote_key}': {type(e).__name__}: {e}")
                
                # Check specifically for network issues, bucket limits, or timeouts
                retryable_errors = [
                    "bucket_tasks_queued", 
                    "reduce your request rate", 
                    "timed out", 
                    "connection aborted", 
                    "connection reset",
                    "remotely closed"
                ]
                
                if any(err in error_str for err in retryable_errors):
                    tqdm.write(f"Rate Limit/Network issue for {display_name}: {e}. Pausing {backoff_time}s...")
                    vlog(f"  Retryable error, sleeping {backoff_time}s...")
                    time.sleep(backoff_time)
                    backoff_time = min(backoff_time * 1.5, MAX_BACKOFF_TIME)
                    attempt += 1
                    bar.reset()
                    continue
                
                # Real error
                tqdm.write(f"Error uploading {remote_key}: {e}") # Print to console properly with tqdm
                record_result('failed', f"{remote_key} ({str(e)})")
                return (False, str(e))
            finally:
                if wrapped_file:
                    try:
                        wrapped_file.close()
                        vlog(f"  wrapped_file closed for '{remote_key}'")
                    except:
                        pass
        
        tqdm.write(f"FAILED {display_name}: Max retries exceeded")
        vlog(f"  Max retries exceeded for '{remote_key}'")
        record_result('failed', f"{remote_key} (Max Retries)")
        return (False, "Max Retries Exceeded (Rate Limit)")





def handle_dji_lrf(folder_path, auto_confirm=False):
    """
    Finds .LRF files, renames them to _s.MP4 for Archive.org compatibility.
    Checks for collisions to prevent overwriting.
    """
    lrf_files = list(folder_path.rglob('*.[lL][rR][fF]'))
    if not lrf_files:
        return

    print(f"\n[!] Detected {len(lrf_files)} DJI LRF files (unsupported by Archive.org).")
    
    if not auto_confirm:
        try:
            confirm = input("Rename them to .mp4 with '_s' suffix to allow upload? (y/n) [y]: ").strip().lower()
            if confirm and confirm not in ['y', 'yes']:
                print("Skipping LRF renaming.")
                return
        except KeyboardInterrupt:
            print("\nSkipping LRF renaming.")
            return

    renamed = 0
    skipped = 0
    for p in lrf_files:
        # DJI_0003.LRF -> DJI_0003_s.mp4
        new_name = p.stem + "_s.mp4"
        new_path = p.with_name(new_name)
        
        if new_path.exists():
            tqdm.write(f"  [SKIP] {p.name} -> {new_name} (File already exists)")
            skipped += 1
            continue
            
        try:
            p.rename(new_path)
            renamed += 1
        except Exception as e:
            tqdm.write(f"  [ERROR] Could not rename {p.name}: {e}")
            
    if renamed > 0:
        print(f"Successfully renamed {renamed} file(s).")
    if skipped > 0:
        print(f"Skipped {skipped} file(s) to avoid collisions.")


def safe_rmtree(path, retries=5, delay=1.0):
    """
    Attempts to delete a directory tree, retrying on failure (common on Windows).
    """
    for i in range(retries):
        try:
            shutil.rmtree(path)
            return True
        except PermissionError:
            if i < retries - 1:
                vlog(f"PermissionError during rmtree, retrying in {delay}s...")
                time.sleep(delay)
            else:
                raise
        except Exception:
            raise
    return False


def main():
    # --- ARGUMENT PARSING ---
    parser = argparse.ArgumentParser(description="Archive.org Smart Uploader & Syncer")
    parser.add_argument("folder", nargs="?", help="Path to local folder")
    parser.add_argument("identifier", nargs="?", help="Unique Archive.org identifier")
    parser.add_argument("-t", "--threads", type=int, default=DEFAULT_THREADS, help=f"Number of parallel upload/delete threads (default: {DEFAULT_THREADS})")
    parser.add_argument("-s", "--sync", action="store_true", help="Sync mode (Upload/Update only)")
    parser.add_argument("-o", "--orphan-deletion", action="store_true", help="Delete remote files that do not exist locally")
    parser.add_argument("-m", "--metadata", action="store_true", help="Force metadata update prompt for existing items")
    parser.add_argument("--md5-verify", action="store_true", help="Enable MD5 comparison for files that already exist remotely by path")
    parser.add_argument("--fix-lrf", action="store_true", help="Automatically rename DJI .LRF files to _s.MP4 without prompting")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable detailed debug logging for each upload step")
    args = parser.parse_args()

    global VERBOSE
    VERBOSE = args.verbose

    max_workers = args.threads

    print(f"--- Archive.org Smart Uploader (iaupload v6.7) ---")
    print(f"--- Threads: {max_workers} ---")
    print(f"--- MD5 Verify: {'ON' if args.md5_verify else 'OFF (Path-only)'} ---")
    if VERBOSE:
        print(f"--- Verbose: ON ---")
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
            # Suggest the folder name as default if possible
            default_id = Path(folder_path_str).name if folder_path_str else None
            identifier = get_input("Identifier", required=True, default=default_id)

        # Store the suggested title before sanitizing the identifier
        title_suggestion = identifier
        
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

        # --- PRE-UPLOAD FIXES ---
        handle_dji_lrf(folder_path, auto_confirm=args.fix_lrf)

        # 2. Remote Check
        print(f"\nChecking '{identifier}'...")
        item = get_item(identifier)
        metadata = {}
        is_new_item = False
        metadata_prefills = load_metadata_prefills(folder_path)
        account_collections = get_account_collections(session)

        if item.exists:
            # Only ask update question if -m flag is provided
            if args.metadata:
                if get_input("Update metadata? (y/n)", default='n').lower() == 'y':
                    metadata = collect_metadata(title_suggestion, prefills=metadata_prefills, account_collections=account_collections)
        else:
            print(f"  > New item detected.")
            is_new_item = True
            metadata = collect_metadata(title_suggestion, prefills=metadata_prefills, account_collections=account_collections)

        # 3. MD5 Scanning Phase
        print("\n" + "="*30)
        print("PHASE 1: CONTENT VERIFICATION" if args.md5_verify else "PHASE 1: PATH VERIFICATION")
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
        remote_map = {} # normalized_path -> dict with md5 and size
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
                        
                        remote_map[norm_path] = {
                            'md5': f.get('md5'),
                            'size': f.get('size')
                        }

        # 3c. Comparison
        files_to_upload = [] 
        orphaned_files = [] # List of remote keys to delete
        
        matched_count = 0
        upload_new_count = 0
        upload_update_count = 0
        skipped_empty_count = 0

        # Detect Uploads
        print(f"Scanning {len(local_file_map)} local files against {total_remote_originals} remote originals...")
        
        with tqdm(total=len(local_file_map), desc="Verifying", unit="file", dynamic_ncols=True) as scan_bar:
            for norm_name, info in local_file_map.items():
                if shutdown_event.is_set(): break
                
                local_file = info['path']
                rel_path = info['rel_path']
                local_size = os.path.getsize(local_file)

                if local_size == 0:
                    skipped_empty_count += 1
                    tqdm.write(f"[SKIP EMPTY]  {rel_path}")
                    scan_bar.update(1)
                    continue

                disp = rel_path if len(rel_path) < 30 else "..." + rel_path[-27:]
                scan_bar.set_description(f"Check: {disp}")
                
                should_upload = False
                status_msg = ""
                
                if norm_name not in remote_map:
                    # New path: no MD5 or size needed because there is no same-path remote file to compare against.
                    should_upload = True
                    status_msg = f"[NEW]         {rel_path}"
                    upload_new_count += 1

                else:
                    remote_info = remote_map[norm_name]
                    remote_size = remote_info['size']
                    remote_md5 = remote_info['md5']
                    # Fast size check first
                    if remote_size is not None and str(local_size) != str(remote_size):
                        should_upload = True
                        status_msg = f"[UPDATE SIZE] {rel_path}"
                        upload_update_count += 1
                    else:
                        if args.md5_verify:
                            # Sizes match (or remote unknown). Verify content hash if enabled.
                            local_md5 = calculate_md5(local_file)
                            if not local_md5:
                                break
    
                            if local_md5 != remote_md5:
                                should_upload = True
                                status_msg = f"[UPDATE MD5]  {rel_path}"
                                upload_update_count += 1
                            else:
                                matched_count += 1
                        else:
                            # Path and size match, treat as matched without downloading full file hash.
                            matched_count += 1
                
                if should_upload:
                    files_to_upload.append((rel_path, local_file))
                    tqdm.write(status_msg)
                
                scan_bar.update(1)
            
            scan_bar.set_description("Scan Complete")

        # Detect Orphans (path-based)
        if item.exists:
            for f in item.files:
                 if f['source'] == 'original' and f['name'] != script_name:
                     norm = normalize_path(f['name'])
                     
                     if norm in local_file_map:
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
        matched_label = "Matched (MD5 Exact)" if args.md5_verify else "Matched (Path Exists)"
        print(f"{matched_label}:".ljust(28) + f"{matched_count}")
        print(f"To Upload (New):         {upload_new_count}")
        print(f"To Upload (Update):      {upload_update_count}")
        print(f"Skipped Empty Files:     {skipped_empty_count}")
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
                
                vlog(f"Session configured: pool_connections={max_workers+5}, pool_maxsize={max_workers+5}")
                vlog(f"HTTP timeout: connect=30s, read=300s")
                
            except Exception as e:
                print(f"Warning: Could not configure connection pool: {e}")
                vlog(f"Session config exception: {type(e).__name__}: {e}")
                # Fallback to standard session if mounting fails
                if not custom_session:
                     custom_session = get_session()

            start_index = 0
            main_bar = tqdm(total=upload_count, desc="Uploading", position=0, unit="file", dynamic_ncols=True)

            if is_new_item:
                # Upload the first (smallest) file to initialize the item
                first_file = files_to_upload[0]
                vlog(f"Creating new item with first file: '{first_file[0]}'")
                success, msg = upload_worker(identifier, first_file, metadata, position=1, session=custom_session)
                main_bar.update(1)
                if not success:
                    main_bar.close()
                    print(f"\nCRITICAL ERROR on creation: {msg}")
                    sys.exit(1)
                vlog(f"Item created successfully, switching to parallel uploads")
                start_index = 1
                metadata = None

            remaining_files = files_to_upload[start_index:]
            
            if remaining_files:
                slot_queue = queue.Queue()
                for i in range(1, max_workers + 1):
                    slot_queue.put(i)

                def worker_wrapper(f_data):
                    vlog(f"worker_wrapper: waiting for slot for '{f_data[0]}'")
                    slot = slot_queue.get() 
                    vlog(f"worker_wrapper: got slot {slot} for '{f_data[0]}'")
                    try:
                        return upload_worker(identifier, f_data, None, position=slot, session=custom_session)
                    finally:
                        vlog(f"worker_wrapper: releasing slot {slot} (was '{f_data[0]}')")
                        slot_queue.put(slot)

                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_file = {
                        executor.submit(worker_wrapper, fdata): fdata 
                        for fdata in remaining_files
                    }
                    vlog(f"Submitted {len(future_to_file)} futures to executor")
                    
                    completed_count = 0
                    pending = set(future_to_file.keys())
                    last_liveness = time.time()
                    
                    while pending:
                        if shutdown_event.is_set():
                            executor.shutdown(wait=False, cancel_futures=True)
                            break
                        
                        # Use timeout so we can periodically report liveness
                        done_batch = set()
                        try:
                            for future in as_completed(pending, timeout=60):
                                done_batch.add(future)
                                completed_count += 1
                                fdata = future_to_file[future]
                                vlog(f"Future completed for '{fdata[0]}' ({completed_count}/{len(future_to_file)})")
                                main_bar.update(1)
                                # Break out after processing done ones to re-check liveness
                                if time.time() - last_liveness >= 60:
                                    break
                        except TimeoutError:
                            # Timeout fired with no new completions — this is expected,
                            # fall through to liveness reporting below
                            pass
                        
                        pending -= done_batch
                        
                        # Periodic liveness report if anything is still pending
                        if pending and time.time() - last_liveness >= 60:
                            last_liveness = time.time()
                            in_flight = [future_to_file[f][0] for f in pending]
                            if len(in_flight) <= 5:
                                tqdm.write(f"  [LIVENESS] {len(in_flight)} file(s) still in-flight: {in_flight}")
                            else:
                                tqdm.write(f"  [LIVENESS] {len(in_flight)} file(s) still in-flight (showing first 5): {in_flight[:5]}")
            
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

        # --- POST-UPLOAD: Offer to delete local folder on full success ---
        if not shutdown_event.is_set() and len(final_results['failed']) == 0 and len(final_results['cancelled']) == 0:
            try:
                answer = input(f"\nAll files uploaded successfully. Delete local folder '{folder_path}'? (y/n) [n]: ").strip().lower()
                if answer == 'y':
                    try:
                        safe_rmtree(folder_path)
                        print(f"Deleted: {folder_path}")
                    except Exception as e:
                        print(f"Error deleting folder: {e}")
                else:
                    print("Local folder kept.")
            except KeyboardInterrupt:
                print("\nSkipped deletion.")

    except KeyboardInterrupt:
        print("\n\n!!! KEYBOARD INTERRUPT DETECTED !!!")
        print("Stopping threads... (Forcing Exit)")
        shutdown_event.set()
        time.sleep(1)
        print_report()
        os._exit(1)

if __name__ == "__main__":
    main()




