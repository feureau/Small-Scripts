"""
SCRIPT: iaupload.py
PURPOSE: Internet Archive (archive.org) Smart Uploader & Syncer
AUTHOR: Assistant (AI)
DATE: 2026-08-22
VERSION: 6.35 (URL-Encoded Path in SigV2)

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
[2026-10-08] VERSION 6.35 UPDATE
   - FIXED: IAS3Client signed the raw path but requests sent the path
            percent-encoded on the wire. IA's SigV2 verifier rebuilds
            the StringToSign from the encoded wire request, so keys
            containing spaces/brackets failed with 403 SignatureDoes
            NotMatch (simple keys like `_s3v2diag.bin` happened to work).
            The path is now percent-encoded (preserving '/') before
            signing and before URL construction.
   - IMPROVED: initiate/upload_part/complete errors now print the exact
            StringToSign we sent and the full IA error body.

[2026-10-08] VERSION 6.34 UPDATE
   - FIXED: IAS3Client cached the 307 storage-node redirect from the
            preflight HEAD and reused it for the initiate POST. IA's
            redirect body explicitly says to keep using the original
            endpoint for future requests. Writes now always go to the
            master; only GET/HEAD follow the 307 (once, without caching).
   - FIXED: preflight HEAD now treats 307 as success (bucket exists on
            a storage node) instead of caching the node.

[2026-10-08] VERSION 6.33 UPDATE
   - FIXED: IAS3Client._sign_v2 sent both Date and x-amz-date headers,
            but signed with an empty Date line (SigV2 rule: x-amz-date
            supersedes Date). IA's verifier rebuilt the StringToSign with
            the wire Date header and returned 403 SignatureDoesNotMatch.
            The Date header is no longer sent; only x-amz-date is used.

[2026-10-08] VERSION 6.32 UPDATE
   - FIXED: v6.31 accidentally deleted _filter_ia_s3_dns (it lived between
            multipart_upload_worker and handle_dji_lrf, and v6.31 replaced
            that whole span). Function restored; DNS pinning active again.
   - FIXED: IAS3Client doubled the path when following IA's 307 redirect,
            because Location already contains the bucket path. Now only
            scheme://host:port is extracted from Location.

[2026-10-08] VERSION 6.31 UPDATE
   - REWRITTEN: multipart_upload_worker no longer uses boto3/botocore.
                IA's S3 endpoint requires SigV2 signatures (rejects SigV4),
                and botocore's S3 region-redirect handler mishandled IA's
                307 storage-node redirects, causing an infinite loop.
   - ADDED: IAS3Client: minimal SigV2 signer + manual 307 follow with
            per-bucket storage-node caching. Supports initiate/upload_part/
            complete/abort. Parallel part uploads via ThreadPoolExecutor.
   - ADDED: Automatic chunk-size scaling for S3's 10,000-part limit.
   - ADDED: Post-upload server-side verification before recording success.
   - MODIFIED: Progress bar tracks server-confirmed bytes, not local reads.

[2026-10-08] VERSION 6.30 UPDATE
   - FIXED: s3.us.archive.org occasionally resolves to a dead IP that
            blackholes TCP/443. New startup DNS filter probes each IP
            and monkey-patches socket.getaddrinfo to return only the
            reachable ones. Self-heals as IA rotates IPs.
   - FIXED: boto3 client now sets connect_timeout=30 and read_timeout=120
            with retries max_attempts=2, so stuck connects fail in
            seconds instead of hanging for many minutes.
   - ADDED: Preflight list_objects_v2 before each multipart PUT to
            surface unreachable endpoints at startup.
   - FIXED: Ctrl+C could not interrupt blocked network calls on Windows.
            socket.setdefaulttimeout(30) now applies at import time, and
            a SIGINT handler sets shutdown_event immediately.
   - ADDED: botocore debug logging when -v is passed.

[2026-10-08] VERSION 6.27 UPDATE
   - FIXED: TransferConfig was constructed with 'max_request_queue_size',
            which is not a valid parameter; the real name is 'max_io_queue'.
            This caused multipart uploads to fail immediately on v6.25/v6.26.
   - MODIFIED: TransferConfig construction now introspects s3transfer at
            runtime and only passes max_io_queue when the installed version
            actually accepts it. Future parameter renames won't break us.

[2026-10-08] VERSION 6.26 UPDATE
   - FIXED: Main loop discarded future results, so a worker could return
            success/failure without recording either. Every future is now
            read, exceptions captured, and unrecorded failures logged.
   - FIXED: multipart_upload_worker could return in <1s without uploading.
            It now verifies (a) the reader consumed the full file, and
            (b) the file appears on the server with the correct size.
   - ADDED: MULTIPART_VERIFY_TIMEOUT (default 300s) for post-upload
            server-side confirmation.
   - ADDED: _SilentReader tracks bytes_read for sanity checks.
   - ADDED: _progress_callback wrapped so a callback error cannot abort
            the upload.

[2026-10-08] VERSION 6.25 UPDATE
   - FIXED: Multipart progress bar was tracking local disk read speed, not
            network upload speed, because s3transfer's use_threads=True mode
            runs the file reader ahead of the network uploaders.
   - MODIFIED: Progress is now driven by the Callback= parameter of
            s3.upload_fileobj, which fires after each part is confirmed
            uploaded by the server.
   - ADDED: max_request_queue_size capped at max_concurrency*2 to prevent
            s3transfer from buffering many GB of read-ahead data in RAM.

[2026-10-08] VERSION 6.24 UPDATE
   - FIXED: 'S3Transfer' object has no attribute 'upload_fileobj' on
            s3transfer >= 0.19.x. Switched to the stable client-level
            s3.upload_fileobj() API, which is compatible across all boto3
            versions and delegates to whichever transfer backend is current.

[2026-10-08] VERSION 6.23 UPDATE
   - MODIFIED: Multipart upload is now ON BY DEFAULT. Use --no-multipart to
               disable it. --multipart is kept as a no-op for compatibility.
   - MODIFIED: Default multipart threshold lowered 256 MB -> 128 MB.
   - FIXED: New-item first file now honors multipart routing; previously it
            was hard-coded to single-stream upload_worker even for huge files.
   - FIXED: multipart_upload_worker now attaches full metadata via
            item.modify_metadata() after the S3 PUT, so list-valued fields
            (subject, format, relation) are preserved.
   - ADDED: Automatic chunk-size scaling when file/chunk would exceed S3's
            10,000-part limit (up to 5 GB per part).

[2026-10-08] VERSION 6.22 UPDATE
   - ADDED: S3 multipart upload path for large files (--multipart flag).
           Large files are split into parallel chunks and reassembled into a
           single object on Archive.org's servers.
   - ADDED: --chunk-size MB flag (default 64 MB per part).
   - ADDED: --multipart-threshold MB flag (default 256 MB).
   - ADDED: --multipart-concurrency N flag (default 4 parallel parts/file).
   - ADDED: multipart_upload_worker() using boto3 + IA's S3 API.
   - MODIFIED: worker_wrapper now routes files by size.

[2026-08-22] VERSION 6.21 UPDATE
   - FIXED: Added explicit timeout and try/except block to initial `get_item()` call to prevent crashes when Archive.org's metadata API is slow.
   - CLEANUP: Removed leftover unreachable GUI code inside the metadata collection block.

[2026-04-15] VERSION 6.20 UPDATE
   - ADDED: Automatic filename truncation for path components exceeding 230 bytes.
   - ADDED: IA rejects uploads with path components > 230 bytes; script now auto-truncates
           while preserving extension and appending a short hash for uniqueness.
   - ADDED: Warning printed when a filename is truncated during the scan phase.

[2026-04-15] VERSION 6.19 UPDATE
   - ADDED: "Skip to Defaults" shortcut during metadata questionnaire.
   - ADDED: Typing '!!' at any prompt auto-accepts all remaining fields with their defaults.
   - ADDED: Descriptive hint shown at the start of METADATA PREPARATION section.

[2026-04-13] VERSION 6.18 UPDATE
   - REMOVED: Entire Tkinter GUI system and --gui flag.
   - CLEANUP: Codebase is now strictly console-only for minimal weight.

[2026-04-13] VERSION 6.17 UPDATE
   - MODIFIED: Major GUI v2.0 overhaul. (REMOVED in 6.18)

[2026-04-13] VERSION 6.16 UPDATE
   - ADDED: Advanced range detection in folder names (e.g., 1900-1950).
   - MODIFIED: Date field defaults to full YYYY-MM-DD.
   - MODIFIED: Coverage and Temporal fields default to Year or Year Range.

[2026-04-13] VERSION 6.15 UPDATE

[2026-04-13] VERSION 6.14 UPDATE

[2026-04-13] VERSION 6.13 UPDATE

[2026-04-13] VERSION 6.12 UPDATE
   - MODIFIED: GUI disabled by default. Console-only mode is now the default for metadata entry.
   - ADDED: --gui flag to enable the Tkinter GUI for metadata entry.

[2026-04-13] VERSION 6.11 UPDATE
   - ADDED: --no-gui flag to disable GUI and use console-only mode for metadata entry.

[2026-04-13] VERSION 6.10 UPDATE
   - ADDED: Tkinter GUI for metadata entry with dark mode theme.
   - ADDED: All basic and extended metadata fields in GUI.
   - ADDED: Custom fields section with add/remove functionality.
   - ADDED: Reset to Defaults, Clear buttons for each field.
   - ADDED: Proceed to Upload and Cancel buttons.

[2026-04-13] VERSION 6.9 UPDATE
   - ADDED: Support for _meta.xml alongside metadata.xml for metadata file detection.
   - ADDED: Extended metadata field support for XML and JSON: language, date, publisher, rights, contributor, source, coverage, temporal, spatial, citation, type, relation, format, and custom fields.
   - ADDED: Interactive prompts for all additional metadata fields during upload.

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

import argparse
import datetime
import hashlib
import io
import json
import os
import queue
import re
import shutil
import sys
import threading
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# --- v6.29: global socket timeout so blocked connects raise and can be
# interrupted by Ctrl+C on Windows (which otherwise ignores SIGINT during
# a blocking connect()). Must run before boto3/requests load.
import socket as _socket
_socket.setdefaulttimeout(30)

from internetarchive import get_item, get_session, upload

# --- OPTIONAL: boto3 for S3 multipart uploads (v6.22) ---
try:
    import boto3
    from boto3.s3.transfer import TransferConfig, S3Transfer
    from botocore.config import Config as BotoConfig
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

# Import iazip's process_directory for -z/--zip flag integration
try:
    from iazip import process_directory as iazip_process
except ImportError:
    iazip_process = None



# Fix Windows console encoding for special characters
if sys.platform == "win32":
    try:
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True
        )
        sys.stdin = io.TextIOWrapper(
            sys.stdin.buffer, encoding="utf-8", errors="replace"
        )
    except Exception:
        pass

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
final_results = {"success": [], "failed": [], "cancelled": []}
VERBOSE = False  # Set by --verbose flag
_MULTIPART_ENABLED = False  # v6.23: on by default; --no-multipart disables
COMMON_LANGUAGES = ["en", "de", "fr", "es", "it", "ja", "zh", "pt", "ru", "ar", "zxx"]
_skip_to_defaults = False  # Set to True when user types '!!' at any metadata prompt

# --- CONFIGURATION DEFAULTS ---
DEFAULT_THREADS = 6
MAX_RETRIES = 20
RETRY_BACKOFF_START = 30
MAX_BACKOFF_TIME = 300
CONNECT_TIMEOUT = 30
READ_TIMEOUT = 300

# --- MULTIPART UPLOAD DEFAULTS (v6.23) ---
DEFAULT_MULTIPART_THRESHOLD_MB = 128  # Files >= this size use S3 multipart
DEFAULT_CHUNK_SIZE_MB = 64            # Size of each multipart chunk
DEFAULT_MULTIPART_CONCURRENCY = 4     # Parallel chunk uploads per file
MULTIPART_VERIFY_TIMEOUT = 300        # Seconds to wait for server-side confirm
IA_S3_ENDPOINT = "https://s3.us.archive.org"


def vlog(msg):
    """Print a verbose debug message with timestamp and thread ID."""
    if VERBOSE:
        ts = time.strftime("%H:%M:%S")
        tid = threading.current_thread().name
        tqdm.write(f"  [VERBOSE {ts} {tid}] {msg}")


# --- HELPER CLASSES ---


class ProgressWrapper:
    """Wraps file object to update tqdm bar on read."""

    def __init__(self, filepath, bar):
        self._file = open(filepath, "rb")
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


# --- CONSTANTS ---
IA_MAX_PATH_COMPONENT_BYTES = 230  # IA rejects path components longer than 230 bytes

# --- HELPER FUNCTIONS ---


def normalize_path(path_str):
    return path_str.lower().replace("\\", "/").replace(" ", "_")


def truncate_path_components(rel_path, max_bytes=IA_MAX_PATH_COMPONENT_BYTES):
    """
    Ensure every component of a relative path is at most `max_bytes` bytes (UTF-8).
    If a component (typically a filename) is too long, it is truncated while
    preserving the file extension and appending a short hash for uniqueness.
    Returns (new_path, was_truncated).
    """
    parts = rel_path.replace("\\", "/").split("/")
    changed = False
    new_parts = []

    for part in parts:
        encoded = part.encode("utf-8")
        if len(encoded) <= max_bytes:
            new_parts.append(part)
            continue

        # Need to truncate this component
        changed = True

        # Separate stem and extension (keep extension intact)
        dot_idx = part.rfind(".")
        if dot_idx > 0:
            stem = part[:dot_idx]
            ext = part[dot_idx:]  # e.g. ".jpg"
        else:
            stem = part
            ext = ""

        # Build a short hash from the ORIGINAL full name for uniqueness
        short_hash = hashlib.md5(encoded).hexdigest()[:8]
        suffix = f"_{short_hash}{ext}"  # e.g. "_a1b2c3d4.jpg"
        suffix_bytes = len(suffix.encode("utf-8"))

        # Truncate the stem so that stem + suffix fits within max_bytes
        budget = max_bytes - suffix_bytes
        stem_encoded = stem.encode("utf-8")
        # Trim byte-by-byte then decode safely (avoid splitting multi-byte chars)
        truncated_stem = stem_encoded[:budget].decode("utf-8", errors="ignore").rstrip()
        new_part = truncated_stem + suffix
        new_parts.append(new_part)

    return "/".join(new_parts), changed


def extract_date_from_string(text):
    """
    Attempts to find dates and ranges in the string.
    Returns a dict with 'date' (full YYYY-MM-DD or partial) and 'period' (Year or Range).
    """
    if not text:
        return {"date": None, "period": None}

    clean_text = text.strip().strip("\"").strip("'")

    # 1. Look for year ranges: 1900-1950 or 1900/1950
    range_match = re.search(r"(\d{4}[-/]\d{4})", clean_text)

    # 2. Look for full date: YYYY-MM-DD
    full_date_match = re.search(r"(\d{4}-\d{2}-\d{2})", clean_text)

    # 3. Look for partial dates: YYYY-MM or YYYY
    month_match = re.search(r"(\d{4}-\d{2})", clean_text)
    year_match = re.search(r"(\d{4})", clean_text)

    # Determine full_date
    date_val = None
    if full_date_match:
        date_val = full_date_match.group(1)
    elif month_match:
        date_val = month_match.group(1)
    elif year_match:
        date_val = year_match.group(1)

    # Determine period (Priority to Range, then Year)
    period_val = None
    if range_match:
        # Standardize range to YYYY-YYYY or YYYY/YYYY (using dash as default for IA)
        period_val = range_match.group(1).replace("/", "-")
    elif year_match:
        period_val = year_match.group(1)

    return {"date": date_val, "period": period_val}


def calculate_md5(filepath, block_size=8192):
    md5 = hashlib.md5()
    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(block_size), b""):
                if shutdown_event.is_set():
                    return None
                md5.update(chunk)
        return md5.hexdigest()
    except Exception:
        return None


def print_requirements():
    print("\n" + "=" * 50)
    print("PRE-UPLOAD CHECKLIST")
    print("=" * 50)
    print("1. [TARGET FOLDER] Path to files.")
    print("2. [IDENTIFIER]    Unique URL slug.")
    print("3. [METADATA]      Title, Mediatype, etc.")
    print("-" * 50)
    input("Press Enter to continue...")


def get_input(prompt_text, required=False, default=None, valid_options=None):
    global _skip_to_defaults

    # If skip mode is active, immediately return the default (or empty string)
    if _skip_to_defaults:
        val = default if default is not None else ""
        print(f"  {prompt_text}: {val}  [default]")
        return val

    while True:
        display = (
            f"{prompt_text} [{default}]: "
            if default is not None
            else f"{prompt_text}: "
        )
        try:
            val = input(display).strip()
        except KeyboardInterrupt:
            sys.exit(1)

        # '!!' triggers skip-to-defaults for this and all remaining prompts
        if val == "!!":
            _skip_to_defaults = True
            val = default if default is not None else ""
            print(f"  >> Skipping to defaults. Remaining fields will use their default values.")
            print(f"  >> {prompt_text}: {val}")
            return val

        if not val and default is not None:
            return default
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
        "https://archive.org/services/xauthn/?op=account",
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
            elif isinstance(data.get("user"), dict) and isinstance(
                data["user"].get("collections"), list
            ):
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


def collect_metadata(
    default_title,
    prefills=None,
    account_collections=None,
    suggested_date=None,
    suggested_period=None,
):
    global _skip_to_defaults
    _skip_to_defaults = False  # Reset at the start of each metadata collection

    print("\n--- METADATA PREPARATION ---")
    print("Required: Title, Mediatype.")
    print(
        "Title: Human-readable name shown on the item page; keep it clear and descriptive."
    )
    print(
        "Mediatype: One of the allowed categories; choose the closest match for the content."
    )
    print("Creator: Person, group, or organization responsible (optional).")
    print("Description: Short summary of the item contents and context (optional).")
    print("Tags: Comma-separated keywords for search and discovery (optional).")
    print()
    print("  TIP: Type !! at any prompt to skip all remaining fields and use their defaults.")
    if prefills:
        print(
            "Found metadata file: fields are prefilled where available. Press Enter to keep defaults."
        )

    title_default = prefills.get("title") if prefills else None
    if not title_default:
        title_default = default_title
    title = get_input("Title", required=True, default=title_default)

    mediatype_default = prefills.get("mediatype") if prefills else None
    mediatype = get_input(
        "Mediatype (data|image|audio|texts|movies|software)",
        required=True,
        default=mediatype_default,
        valid_options=["data", "image", "audio", "texts", "movies", "software"],
    )

    creator_default = prefills.get("creator") if prefills else None
    description_default = prefills.get("description") if prefills else None
    tags_default = prefills.get("tags") if prefills else None
    collection_default = prefills.get("collection") if prefills else None
    creator = get_input("Creator", required=False, default=creator_default)
    description = get_input("Description", required=False, default=description_default)
    subjects_val = get_input("Tags (comma sep)", required=False, default=tags_default)
    subjects = [t.strip() for t in subjects_val.split(",")] if subjects_val else []

    # --- LICENSE SELECTION ---
    print("\nSelect a License (Press Enter for GPLv3 default):")
    license_options = {
        "1": ("GPLv3", "https://www.gnu.org/licenses/gpl-3.0.html"),
        "2": ("CC BY 4.0", "https://creativecommons.org/licenses/by/4.0/"),
        "3": ("CC BY-SA 4.0", "https://creativecommons.org/licenses/by-sa/4.0/"),
        "4": ("CC BY-ND 4.0", "https://creativecommons.org/licenses/by-nd/4.0/"),
        "5": ("CC BY-NC 4.0", "https://creativecommons.org/licenses/by-nc/4.0/"),
        "6": ("CC BY-NC-SA 4.0", "https://creativecommons.org/licenses/by-nc-sa/4.0/"),
        "7": ("CC BY-NC-ND 4.0", "https://creativecommons.org/licenses/by-nc-nd/4.0/"),
        "8": (
            "CC0 1.0 (Public Domain)",
            "https://creativecommons.org/publicdomain/zero/1.0/",
        ),
        "9": (
            "PDM 1.0 (Public Domain Mark)",
            "https://creativecommons.org/publicdomain/mark/1.0/",
        ),
        "0": ("Custom URL / None", None),
    }

    for key, (name, _) in license_options.items():
        print(f"  [{key}] {name}")

    license_default = prefills.get("licenseurl") if prefills else None

    # Map prefilled URL back to an option number if possible for display
    default_key = "1"  # GPLv3 default
    if license_default:
        for k, (name, url) in license_options.items():
            if url == license_default:
                default_key = k
                break
        else:
            default_key = "0"  # Custom

    choice = get_input("Choose license", default=default_key)

    selected_url = None
    if choice in license_options:
        selected_url = license_options[choice][1]

    if choice == "0" or (choice not in license_options and choice):
        # If they chose custom or typed a random string that isn't a key
        if choice not in license_options:
            selected_url = choice  # Treat as custom URL if not a key
        else:
            selected_url = get_input(
                "Custom License URL (leave empty for none)", default=license_default
            )

    metadata = {"title": title, "mediatype": mediatype}
    if selected_url:
        metadata["licenseurl"] = selected_url

    # Map mediatype to default community collection
    collection_map = {
        "texts": "opensource",
        "audio": "opensource_audio",
        "movies": "opensource_movies",
        "image": "opensource_image",
        "software": "open_source_software",
        "data": "opensource_media",
    }

    public_collections = set(collection_map.values())
    suggested_collection = collection_default
    if suggested_collection and suggested_collection not in public_collections:
        print(
            f"Warning: Prefilled collection '{suggested_collection}' may be restricted for your account."
        )
        suggested_collection = collection_map.get(mediatype)
    if not suggested_collection:
        suggested_collection = collection_map.get(mediatype)

    if account_collections:
        print("Available collections for this account:")
        print("  " + ", ".join(account_collections))

    collection = get_input("Collection", required=False, default=suggested_collection)
    if collection:
        metadata["collection"] = collection

    if creator:
        metadata["creator"] = creator
    if description:
        metadata["description"] = description
    if subjects:
        metadata["subject"] = subjects

    # Additional optional fields from prefills
    language_default = prefills.get("language") if prefills else "en"
    date_default = prefills.get("date") if prefills else suggested_date
    publisher_default = prefills.get("publisher") if prefills else None
    rights_default = prefills.get("rights") if prefills else None
    contributor_default = prefills.get("contributor") if prefills else None
    source_default = prefills.get("source") if prefills else None

    # Sync Rights with License selection if not prefilled
    if choice in license_options and not rights_default:
        rights_default = license_options[choice][0]

    coverage_default = prefills.get("coverage") if prefills else suggested_period
    temporal_default = prefills.get("temporal") if prefills else suggested_period
    spatial_default = prefills.get("spatial") if prefills else None
    citation_default = prefills.get("citation") if prefills else None
    type_default = prefills.get("type") if prefills else None
    relation_default = prefills.get("relation") if prefills else None
    format_list = prefills.get("format") if prefills else None
    custom_fields = prefills.get("_custom") if prefills else None

    language = get_input(
        "Language (e.g., en, zxx)", required=False, default=language_default
    )
    date = get_input("Date (e.g., 2024, 2024-01)", required=False, default=date_default)
    publisher = get_input("Publisher", required=False, default=publisher_default)
    rights = get_input(
        "Rights (e.g., CC BY 4.0)", required=False, default=rights_default
    )
    contributor = get_input("Contributor", required=False, default=contributor_default)
    source = get_input("Source", required=False, default=source_default)
    coverage = get_input(
        "Coverage (e.g., World, 1900-1950)", required=False, default=coverage_default
    )
    temporal = get_input(
        "Temporal (e.g., 1900/1950)", required=False, default=temporal_default
    )
    spatial = get_input(
        "Spatial (e.g., USA, Germany)", required=False, default=spatial_default
    )
    citation = get_input("Citation", required=False, default=citation_default)
    item_type = get_input("Type", required=False, default=type_default)
    relation = get_input(
        "Relation (comma-separated URLs)", required=False, default=relation_default
    )

    if language:
        metadata["language"] = language
    if date:
        metadata["date"] = date
    if publisher:
        metadata["publisher"] = publisher
    if rights:
        metadata["rights"] = rights
    if contributor:
        metadata["contributor"] = contributor
    if source:
        metadata["source"] = source
    if coverage:
        metadata["coverage"] = coverage
    if temporal:
        metadata["temporal"] = temporal
    if spatial:
        metadata["spatial"] = spatial
    if citation:
        metadata["citation"] = citation
    if item_type:
        metadata["type"] = item_type
    if relation:
        rel_list = [r.strip() for r in relation.split(",")]
        metadata["relation"] = rel_list

    if format_list:
        if isinstance(format_list, list):
            metadata["format"] = format_list

    if custom_fields:
        for key, val in custom_fields.items():
            metadata[key] = val

    return metadata


def _xml_text(node):
    if node is None:
        return None
    text = (node.text or "").strip()
    return text if text else None


def load_metadata_xml(folder_path):
    # Check for metadata.xml first, then _meta.xml
    xml_path = folder_path / "metadata.xml"
    if not xml_path.exists():
        xml_path = folder_path / "_meta.xml"
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
    identifier_xml = find_text(["identifier", "Identifier"])
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

    # Additional common fields
    language = find_text(["language", "Language"])
    date = find_text(["date", "Date"])
    publisher = find_text(["publisher", "Publisher"])
    rights = find_text(["rights", "Rights"])
    contributor = find_text(["contributor", "Contributor"])
    source = find_text(["source", "Source"])
    coverage = find_text(["coverage", "Coverage"])
    temporal = find_text(["temporal", "Temporal"])
    spatial = find_text(["spatial", "Spatial"])
    citation = find_text(["citation", "Citation"])
    item_type = find_text(["type", "Type"])

    # relation: support repeated nodes
    relations = [_xml_text(n) for n in root.findall(".//relation")]
    relations = [r for r in relations if r]
    relation = ", ".join(relations) if relations else None

    # format: support repeated nodes (list)
    formats = [_xml_text(n) for n in root.findall(".//format")]
    formats = [f for f in formats if f]

    # Custom fields: capture any additional elements not in the standard list
    custom_fields = {}
    standard_fields = {
        "title",
        "Title",
        "identifier",
        "Identifier",
        "mediatype",
        "Mediatype",
        "creator",
        "Creator",
        "description",
        "Description",
        "collection",
        "Collection",
        "licenseurl",
        "LicenseURL",
        "license",
        "License",
        "subject",
        "tag",
        "language",
        "Language",
        "date",
        "Date",
        "publisher",
        "Publisher",
        "rights",
        "Rights",
        "contributor",
        "Contributor",
        "relation",
        "citation",
        "Coverage",
        "coverage",
        "temporal",
        "Temporal",
        "spatial",
        "Spatial",
        "source",
        "Source",
        "type",
        "Type",
        "format",
    }
    for child in root:
        if child.tag not in standard_fields and not child.tag.startswith("{"):
            val = _xml_text(child)
            if val:
                custom_fields[child.tag] = val

    prefills = {}
    if title:
        prefills["title"] = title
    if identifier_xml:
        prefills["identifier"] = identifier_xml
    if mediatype:
        prefills["mediatype"] = mediatype
    if creator:
        prefills["creator"] = creator
    if description:
        prefills["description"] = description
    if tags:
        prefills["tags"] = tags
    if collection:
        prefills["collection"] = collection
    if licenseurl:
        prefills["licenseurl"] = licenseurl
    if language:
        prefills["language"] = language
    if date:
        prefills["date"] = date
    if publisher:
        prefills["publisher"] = publisher
    if rights:
        prefills["rights"] = rights
    if contributor:
        prefills["contributor"] = contributor
    if source:
        prefills["source"] = source
    if coverage:
        prefills["coverage"] = coverage
    if temporal:
        prefills["temporal"] = temporal
    if spatial:
        prefills["spatial"] = spatial
    if citation:
        prefills["citation"] = citation
    if item_type:
        prefills["type"] = item_type
    if relation:
        prefills["relation"] = relation
    if formats:
        prefills["format"] = formats
    if custom_fields:
        prefills["_custom"] = custom_fields

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
    identifier_json = get_str(["identifier", "Identifier"])
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

    # Additional common fields
    language = get_str(["language", "Language"])
    date = get_str(["date", "Date"])
    publisher = get_str(["publisher", "Publisher"])
    rights = get_str(["rights", "Rights"])
    contributor = get_str(["contributor", "Contributor"])
    source = get_str(["source", "Source"])
    coverage = get_str(["coverage", "Coverage"])
    temporal = get_str(["temporal", "Temporal"])
    spatial = get_str(["spatial", "Spatial"])
    citation = get_str(["citation", "Citation"])
    item_type = get_str(["type", "Type"])

    # relation: list or comma-separated string
    relation_val = data.get("relation")
    if relation_val is None:
        relation_val = data.get("Relation")
    relation = None
    if isinstance(relation_val, list):
        rels = [str(r).strip() for r in relation_val if str(r).strip()]
        if rels:
            relation = ", ".join(rels)
    elif isinstance(relation_val, str) and relation_val.strip():
        relation = relation_val.strip()

    # format: list
    format_val = data.get("format")
    if format_val is None:
        format_val = data.get("Format")
    formats = None
    if isinstance(format_val, list):
        fmt_list = [str(f).strip() for f in format_val if str(f).strip()]
        if fmt_list:
            formats = fmt_list
    elif isinstance(format_val, str) and format_val.strip():
        formats = [format_val.strip()]

    # Custom fields: everything else
    standard_keys = {
        "title",
        "Title",
        "identifier",
        "Identifier",
        "mediatype",
        "Mediatype",
        "creator",
        "Creator",
        "description",
        "Description",
        "collection",
        "Collection",
        "licenseurl",
        "LicenseURL",
        "license",
        "License",
        "subject",
        "Subject",
        "tags",
        "Tags",
        "language",
        "Language",
        "date",
        "Date",
        "publisher",
        "Publisher",
        "rights",
        "Rights",
        "contributor",
        "Contributor",
        "relation",
        "Relation",
        "citation",
        "Coverage",
        "coverage",
        "temporal",
        "Temporal",
        "spatial",
        "Spatial",
        "source",
        "Source",
        "type",
        "Type",
        "format",
        "Format",
    }
    custom_fields = {}
    for key, val in data.items():
        if key not in standard_keys:
            if isinstance(val, str) and val.strip():
                custom_fields[key] = val.strip()
            elif isinstance(val, list) and val:
                custom_fields[key] = [str(v).strip() for v in val if str(v).strip()]

    prefills = {}
    if title:
        prefills["title"] = title
    if identifier_json:
        prefills["identifier"] = identifier_json
    if mediatype:
        prefills["mediatype"] = mediatype
    if creator:
        prefills["creator"] = creator
    if description:
        prefills["description"] = description
    if tags:
        prefills["tags"] = tags
    if collection:
        prefills["collection"] = collection
    if licenseurl:
        prefills["licenseurl"] = licenseurl
    if language:
        prefills["language"] = language
    if date:
        prefills["date"] = date
    if publisher:
        prefills["publisher"] = publisher
    if rights:
        prefills["rights"] = rights
    if contributor:
        prefills["contributor"] = contributor
    if source:
        prefills["source"] = source
    if coverage:
        prefills["coverage"] = coverage
    if temporal:
        prefills["temporal"] = temporal
    if spatial:
        prefills["spatial"] = spatial
    if citation:
        prefills["citation"] = citation
    if item_type:
        prefills["type"] = item_type
    if relation:
        prefills["relation"] = relation
    if formats:
        prefills["format"] = formats
    if custom_fields:
        prefills["_custom"] = custom_fields

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
    print("\n" + "=" * 60)
    print("FINAL REPORT")
    print("=" * 60)

    s_count = len(final_results["success"])
    f_count = len(final_results["failed"])
    c_count = len(final_results["cancelled"])

    print(f"Successful: {s_count}")
    print(f"Failed:     {f_count}")
    print(f"Cancelled:  {c_count}")

    if f_count > 0:
        print("-" * 60)
        print("FAILED FILES:")
        for name in final_results["failed"]:
            print(f" [x] {name}")

    if c_count > 0:
        print("-" * 60)
        print("CANCELLED FILES (Not uploaded):")
        for i, name in enumerate(final_results["cancelled"]):
            if i >= 10:
                print(f" ... and {c_count - 10} more.")
                break
            print(f" [-] {name}")

    print("=" * 60)


try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    pass  # Managed in main check

# ... (Previous imports)


def upload_worker(identifier, file_data, metadata=None, position=0, session=None):
    remote_key, local_path = file_data

    if shutdown_event.is_set():
        record_result("cancelled", remote_key)
        return (False, "Cancelled by user")

    file_size = os.path.getsize(local_path)
    if file_size == 0:
        tqdm.write(f"Skipping empty file: {remote_key}")
        record_result("cancelled", remote_key)
        return (False, "Skipped empty file (0 bytes)")

    display_name = remote_key
    if len(display_name) > 20:
        display_name = "..." + display_name[-17:]

    vlog(f"START upload_worker for '{remote_key}' ({file_size:,} bytes)")

    # leave=False cleans up the bar line when done
    with tqdm(
        total=file_size,
        unit="B",
        unit_scale=True,
        unit_divisor=1024,
        desc=display_name,
        position=position,
        leave=False,
        dynamic_ncols=True,
        bar_format="{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} | Speed: {rate_fmt} | Time: {elapsed}<{remaining}",
    ) as bar:
        # RETRY LOOP for Rate Limits
        max_retries = MAX_RETRIES
        attempt = 0
        backoff_time = RETRY_BACKOFF_START  # Start wait for rate limits

        while attempt < max_retries:
            wrapped_file = None
            try:
                vlog(f"  Attempt {attempt + 1}/{max_retries} for '{remote_key}'")
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
                    r = item.upload(
                        files=files_arg,
                        metadata=metadata,
                        verbose=False,
                        retries=3,
                        request_kwargs={"timeout": (CONNECT_TIMEOUT, READ_TIMEOUT)},
                    )
                else:
                    # Fallback to default global upload
                    vlog(f"  Calling upload() (no session) for '{remote_key}'...")
                    r = upload(
                        identifier,
                        files=files_arg,
                        metadata=metadata,
                        verbose=False,
                        retries=3,
                        request_kwargs={"timeout": (CONNECT_TIMEOUT, READ_TIMEOUT)},
                    )

                upload_elapsed = time.time() - upload_start
                vlog(f"  upload() returned for '{remote_key}' in {upload_elapsed:.1f}s")

                # CRITICAL LOOPHOLE FIX: Explicitly close responses to free connection pool slots immediately
                if r:
                    for resp in r:
                        vlog(f"  Response status={resp.status_code} for '{remote_key}'")
                        resp.close()

                if shutdown_event.is_set():
                    record_result("cancelled", remote_key)
                    return (False, "Cancelled")

                if r and r[0].status_code == 200:
                    vlog(f"  SUCCESS for '{remote_key}' (took {upload_elapsed:.1f}s)")
                    record_result("success", remote_key)
                    return (True, remote_key)

                # Check for rate limiting in status code (if 429 or 503 wasn't handled by custom adapter)
                if r and r[0].status_code in [429, 503, 509]:
                    tqdm.write(
                        f"Rate limited ({r[0].status_code}) for {display_name}. Retrying in {backoff_time}s..."
                    )
                    vlog(
                        f"  Rate limited ({r[0].status_code}), sleeping {backoff_time}s..."
                    )
                    time.sleep(backoff_time)
                    backoff_time = min(
                        backoff_time * 1.5, MAX_BACKOFF_TIME
                    )  # Cap max sleep
                    attempt += 1
                    bar.reset()  # Reset progress bar for retry
                    continue

                code = r[0].status_code if r else "Unknown"
                tqdm.write(f"FAILED {display_name}: HTTP {code}")
                vlog(f"  FAILED '{remote_key}' with HTTP {code}")
                record_result("failed", f"{remote_key} (Status {code})")
                return (False, f"Status {code}")

            except Exception as e:
                if shutdown_event.is_set():
                    record_result("cancelled", remote_key)
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
                    "remotely closed",
                ]

                if any(err in error_str for err in retryable_errors):
                    tqdm.write(
                        f"Rate Limit/Network issue for {display_name}: {e}. Pausing {backoff_time}s..."
                    )
                    vlog(f"  Retryable error, sleeping {backoff_time}s...")
                    time.sleep(backoff_time)
                    backoff_time = min(backoff_time * 1.5, MAX_BACKOFF_TIME)
                    attempt += 1
                    bar.reset()
                    continue

                # Real error
                tqdm.write(
                    f"Error uploading {remote_key}: {e}"
                )  # Print to console properly with tqdm
                record_result("failed", f"{remote_key} ({str(e)})")
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
        record_result("failed", f"{remote_key} (Max Retries)")
        return (False, "Max Retries Exceeded (Rate Limit)")


class IAS3Client:
    """
    v6.31: Minimal SigV2 S3 client for Internet Archive's endpoint.

    - Signs with AWS SigV2 (IA does not accept SigV4).
    - Follows the 307 storage-node redirect once per bucket, then caches it.
    - Supports multipart uploads: initiate / upload_part / complete / abort.
    - Depends only on `requests`, which is already imported by iaupload.

    The canonical resource used in signing is path + query only; the host
    is not signed. That's why the same Authorization header works on both
    s3.us.archive.org and the storage node it redirects to.
    """

    ENDPOINT = "https://s3.us.archive.org"

    def __init__(self, access_key, secret_key, timeout=(15, 300)):
        import requests
        from requests.adapters import HTTPAdapter

        self.ak = access_key
        self.sk = secret_key
        self.timeout = timeout
        self._node_cache = {}
        self._session = requests.Session()
        adapter = HTTPAdapter(pool_connections=32, pool_maxsize=32)
        self._session.mount("http://", adapter)
        self._session.mount("https://", adapter)

    def _sign_v2(self, method, path, query="", content_md5="",
                 content_type="", extra_amz=None):
        import base64, hashlib, hmac
        from email.utils import formatdate

        date_str = formatdate(usegmt=True)
        amz = dict(extra_amz or {})
        amz["x-amz-date"] = date_str

        canon_amz = "".join(
            f"{k.lower()}:{v}\n" for k, v in sorted(amz.items())
        )
        canon_res = path + (f"?{query}" if query else "")

        # SigV2 string-to-sign: Date line is EMPTY when x-amz-date is set.
        string_to_sign = (
            f"{method}\n"
            f"{content_md5}\n"
            f"{content_type}\n"
            f"\n"
            f"{canon_amz}"
            f"{canon_res}"
        )
        # v6.35: stash the exact StringToSign for error reporting.
        self._last_string_to_sign = string_to_sign

        sig = base64.b64encode(
            hmac.new(self.sk.encode(), string_to_sign.encode(),
                     hashlib.sha1).digest()
        ).decode()

        # SigV2 rule: when x-amz-date is present, the Date header must be
        # omitted, and the StringToSign's Date line must be empty (which it
        # already is above). Sending both caused IA's verifier to rebuild a
        # different StringToSign and reject with 403 SignatureDoesNotMatch.
        headers = {
            "Authorization": f"AWS {self.ak}:{sig}",
        }
        headers.update(amz)
        if content_md5:
            headers["Content-MD5"] = content_md5
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    def _do(self, method, url, path, query, data, content_type, stream):
        headers = self._sign_v2(
            method, path, query, content_type=content_type
        )
        return self._session.request(
            method, url, headers=headers, data=data,
            allow_redirects=False, timeout=self.timeout, stream=stream,
        )

    def request(self, method, path, query="", data=b"", content_type="",
                stream=False):
        """
        v6.35: percent-encode the path ourselves (preserving '/') and use
        the encoded form for BOTH the signature and the URL. IA's SigV2
        verifier rebuilds the StringToSign from the wire request, which is
        percent-encoded; signing the raw path produced 403
        SignatureDoesNotMatch on any key containing spaces or brackets.

        Writes always go to the master endpoint. IA redirects only reads
        (GET/HEAD) to storage nodes via 307, and the redirect body tells
        us to keep using the original endpoint for future requests.
        """
        from urllib.parse import quote, urlparse
        enc_path = quote(path, safe="/")

        url = self.ENDPOINT + enc_path + (f"?{query}" if query else "")
        r = self._do(method, url, enc_path, query, data, content_type, stream)

        if r.status_code == 307 and method in ("GET", "HEAD"):
            loc = r.headers.get("location")
            if not loc:
                return r
            parsed = urlparse(loc)
            node_root = f"{parsed.scheme}://{parsed.netloc}"
            url = node_root + enc_path + (f"?{query}" if query else "")
            r = self._do(method, url, enc_path, query, data,
                         content_type, stream)

        return r

    def initiate_multipart(self, bucket, key, content_type=""):
        r = self.request("POST", f"/{bucket}/{key}", query="uploads",
                         content_type=content_type)
        if r.status_code != 200:
            raise RuntimeError(
                f"initiate failed: HTTP {r.status_code}\n"
                f"--- StringToSign sent ---\n"
                f"{getattr(self, '_last_string_to_sign', '(none)')}\n"
                f"--- IA response ---\n"
                f"{r.text[:1200]}"
            )
        import xml.etree.ElementTree as ET
        try:
            root = ET.fromstring(r.content)
        except Exception as e:
            raise RuntimeError(f"initiate parse failed: {e}")
        for el in root.iter():
            if el.tag.endswith("UploadId") and el.text:
                return el.text
        raise RuntimeError(f"no UploadId in response: {r.text[:200]}")

    def upload_part(self, bucket, key, upload_id, part_number, data):
        from urllib.parse import quote
        q = f"partNumber={part_number}&uploadId={quote(upload_id, safe='')}"
        r = self.request("PUT", f"/{bucket}/{key}", query=q, data=data)
        if r.status_code not in (200, 201):
            raise RuntimeError(
                f"part {part_number} failed: HTTP {r.status_code}\n"
                f"--- StringToSign sent ---\n"
                f"{getattr(self, '_last_string_to_sign', '(none)')}\n"
                f"--- IA response ---\n"
                f"{r.text[:1200]}"
            )
        etag = r.headers.get("etag") or r.headers.get("ETag")
        if not etag:
            raise RuntimeError(f"part {part_number} returned no ETag")
        return etag.strip('"')

    def complete_multipart(self, bucket, key, upload_id, parts):
        from urllib.parse import quote
        q = f"uploadId={quote(upload_id, safe='')}"
        xml = ('<?xml version="1.0" encoding="UTF-8"?>'
               '<CompleteMultipartUpload>')
        for pnum, etag in sorted(parts):
            xml += (f"<Part><PartNumber>{pnum}</PartNumber>"
                    f"<ETag>\"{etag}\"</ETag></Part>")
        xml += "</CompleteMultipartUpload>"
        r = self.request("POST", f"/{bucket}/{key}", query=q,
                         data=xml.encode(),
                         content_type="application/xml")
        if r.status_code not in (200, 201):
            raise RuntimeError(
                f"complete failed: HTTP {r.status_code}\n"
                f"--- StringToSign sent ---\n"
                f"{getattr(self, '_last_string_to_sign', '(none)')}\n"
                f"--- IA response ---\n"
                f"{r.text[:1200]}"
            )
        return r

    def abort_multipart(self, bucket, key, upload_id):
        from urllib.parse import quote
        q = f"uploadId={quote(upload_id, safe='')}"
        try:
            self.request("DELETE", f"/{bucket}/{key}", query=q)
        except Exception:
            pass


def multipart_upload_worker(
    identifier,
    file_data,
    metadata=None,
    position=0,
    session=None,
    chunk_size_mb=DEFAULT_CHUNK_SIZE_MB,
    max_concurrency=DEFAULT_MULTIPART_CONCURRENCY,
):
    """
    v6.31: Upload a large file using IA's S3 multipart API with SigV2
    signing and manual 307-follow, bypassing boto3/botocore entirely.

    Same signature/return contract as upload_worker, so the caller's
    thread-pool and result-recording logic works unchanged.
    """
    remote_key, local_path = file_data

    if shutdown_event.is_set():
        record_result("cancelled", remote_key)
        return (False, "Cancelled by user")

    file_size = os.path.getsize(local_path)
    if file_size == 0:
        record_result("cancelled", remote_key)
        return (False, "Skipped empty file (0 bytes)")

    # --- credentials (same fallback chain as before) ---
    access_key = os.environ.get("IAS3_ACCESS_KEY")
    secret_key = os.environ.get("IAS3_SECRET_KEY")
    if not access_key and session is not None:
        access_key = getattr(session, "access_key", None)
    if not secret_key and session is not None:
        secret_key = getattr(session, "secret_key", None)
    if not access_key or not secret_key:
        err = "missing IA S3 credentials (run 'ia configure')"
        tqdm.write(f"[multipart] {remote_key}: {err}")
        record_result("failed", f"{remote_key} ({err})")
        return (False, err)

    display_name = remote_key
    if len(display_name) > 20:
        display_name = "..." + display_name[-17:]

    vlog(f"MULTIPART START for '{remote_key}' ({file_size:,} bytes, "
         f"chunk={chunk_size_mb}MB, concurrency={max_concurrency})")

    # --- auto-scale chunk size to respect S3's 10,000-part limit ---
    MAX_S3_PARTS = 10000
    chunk_bytes = max(5, chunk_size_mb) * 1024 * 1024
    min_chunk_bytes = -(-file_size // MAX_S3_PARTS)  # ceil div
    if chunk_bytes < min_chunk_bytes:
        new_mb = -(-min_chunk_bytes // (1024 * 1024))
        tqdm.write(
            f"[multipart] {remote_key}: file is {file_size/1e9:.1f} GB; "
            f"auto-scaling chunk {chunk_size_mb} MB -> {new_mb} MB"
        )
        chunk_bytes = new_mb * 1024 * 1024
    n_parts = -(-file_size // chunk_bytes)  # ceil div
    vlog(f"  chunk_bytes={chunk_bytes:,}  n_parts={n_parts}")

    client = IAS3Client(access_key, secret_key)

    # --- preflight: HEAD bucket (read; 307 is expected and OK) ---
    try:
        pf_t0 = time.time()
        vlog(f"  preflight: HEAD /{identifier} ...")
        pf = client.request("HEAD", f"/{identifier}")
        # 200/204 = bucket answered directly.
        # 307 = master redirected us to a storage node; request() followed it.
        if pf.status_code not in (200, 204, 307):
            raise RuntimeError(f"HTTP {pf.status_code}")
        vlog(f"  preflight OK in {time.time()-pf_t0:.2f}s "
             f"(status={pf.status_code})")
    except Exception as e_pf:
        err = f"preflight failed: {e_pf}"
        tqdm.write(f"[multipart] {remote_key}: {err}")
        record_result("failed", f"{remote_key} ({err})")
        return (False, err)

    upload_id = None
    parts = []

    try:
        # --- initiate ---
        vlog(f"  initiate multipart ...")
        t_init = time.time()
        upload_id = client.initiate_multipart(identifier, remote_key)
        vlog(f"  upload_id={upload_id}  ({time.time()-t_init:.2f}s)")

        # --- upload parts (parallel) with progress ---
        with tqdm(
            total=file_size, unit="B", unit_scale=True, unit_divisor=1024,
            desc=display_name, position=position, leave=False,
            dynamic_ncols=True,
            bar_format=("{desc}: {percentage:3.0f}%|{bar}| "
                        "{n_fmt}/{total_fmt} | Speed: {rate_fmt} | "
                        "Time: {elapsed}<{remaining}"),
        ) as bar:
            pbar_lock = threading.Lock()

            def upload_one(part_num, offset, size):
                if shutdown_event.is_set():
                    return None
                with open(local_path, "rb") as f:
                    f.seek(offset)
                    data = f.read(size)
                etag = client.upload_part(
                    identifier, remote_key, upload_id, part_num, data
                )
                with pbar_lock:
                    bar.update(size)
                vlog(f"  part {part_num}/{n_parts} OK "
                     f"({size:,} bytes, etag={etag[:12]}...)")
                return (part_num, etag)

            with ThreadPoolExecutor(max_workers=max_concurrency) as executor:
                futures = {}
                for i in range(n_parts):
                    pnum = i + 1
                    offset = i * chunk_bytes
                    size = min(chunk_bytes, file_size - offset)
                    futures[executor.submit(
                        upload_one, pnum, offset, size
                    )] = pnum

                for fut in as_completed(futures):
                    if shutdown_event.is_set():
                        break
                    res = fut.result()  # propagates exceptions
                    if res is not None:
                        parts.append(res)

        if shutdown_event.is_set():
            if upload_id:
                client.abort_multipart(identifier, remote_key, upload_id)
            record_result("cancelled", remote_key)
            return (False, "Cancelled")

        if len(parts) != n_parts:
            raise RuntimeError(
                f"only {len(parts)}/{n_parts} parts uploaded"
            )

        # --- complete ---
        vlog(f"  completing multipart ({len(parts)} parts) ...")
        t_complete = time.time()
        client.complete_multipart(identifier, remote_key, upload_id, parts)
        vlog(f"  complete returned ({time.time()-t_complete:.2f}s); "
             f"server may still be reassembling")

        # --- verify on the server before declaring success ---
        tqdm.write(
            f"[multipart] Data sent for {remote_key}; "
            f"waiting for server-side confirmation "
            f"(up to {MULTIPART_VERIFY_TIMEOUT}s)..."
        )
        deadline = time.time() + MULTIPART_VERIFY_TIMEOUT
        last_seen_size = None
        verified = False
        attempt = 0
        while time.time() < deadline:
            if shutdown_event.is_set():
                record_result("cancelled", remote_key)
                return (False, "Cancelled")
            attempt += 1
            try:
                vi = get_item(
                    identifier, archive_session=session,
                    request_kwargs={
                        "timeout": (CONNECT_TIMEOUT, READ_TIMEOUT)
                    },
                )
                for _f in vi.files:
                    if _f.get("name") == remote_key:
                        last_seen_size = _f.get("size")
                        if (last_seen_size is not None
                                and str(last_seen_size) == str(file_size)):
                            verified = True
                            break
                if verified:
                    break
            except Exception as e_v:
                vlog(f"  verify attempt {attempt} exception: {e_v}")
            vlog(f"  verify attempt {attempt}: last_seen_size="
                 f"{last_seen_size} (expected {file_size})")
            time.sleep(5)

        if not verified:
            err = (f"upload sent but file not visible after "
                   f"{MULTIPART_VERIFY_TIMEOUT}s "
                   f"(last size seen: {last_seen_size}, "
                   f"expected: {file_size})")
            tqdm.write(f"[multipart] {remote_key}: {err}")
            record_result("failed", f"{remote_key} ({err})")
            return (False, err)

        vlog(f"MULTIPART VERIFIED on server for '{remote_key}'")

        # --- metadata ---
        if metadata:
            try:
                vlog(f"  applying metadata via modify_metadata() ...")
                md_item = get_item(
                    identifier, archive_session=session,
                    request_kwargs={
                        "timeout": (CONNECT_TIMEOUT, READ_TIMEOUT)
                    },
                )
                md_item.modify_metadata(metadata)
            except Exception as e_md:
                tqdm.write(f"[multipart] {remote_key}: data OK but "
                           f"metadata failed: {e_md}")
                record_result("failed",
                              f"{remote_key} (metadata: {e_md})")
                return (False, f"metadata: {e_md}")

        vlog(f"MULTIPART SUCCESS for '{remote_key}'")
        record_result("success", remote_key)
        return (True, remote_key)

    except Exception as e:
        err = f"{type(e).__name__}: {e}"
        tqdm.write(f"[multipart] {remote_key}: {err}")
        vlog(f"  multipart exception: {err}")
        if upload_id:
            try:
                client.abort_multipart(identifier, remote_key, upload_id)
            except Exception:
                pass
        record_result("failed", f"{remote_key} (multipart: {err})")
        return (False, err)


def _filter_ia_s3_dns(host="s3.us.archive.org", port=443, probe_timeout=3):
    """
    s3.us.archive.org sometimes resolves to multiple IPs, some of which
    blackhole TCP/443. Probe each resolved IP and monkey-patch
    socket.getaddrinfo to return only reachable ones for that host.

    Idempotent. No-op if all IPs are reachable or none are.
    """
    import socket as _sock

    try:
        infos = _sock.getaddrinfo(host, port, proto=_sock.IPPROTO_TCP)
    except Exception as e:
        print(f"[dns-filter] {host}: resolution failed: {e}")
        return

    seen = set()
    candidates = []
    for info in infos:
        ip = info[4][0]
        if ip not in seen:
            seen.add(ip)
            candidates.append((ip, info))

    good_infos = []
    bad_ips = []
    for ip, info in candidates:
        try:
            s = _sock.create_connection((ip, port), timeout=probe_timeout)
            s.close()
            good_infos.append(info)
        except Exception:
            bad_ips.append(ip)

    good_ips = [i[4][0] for i in good_infos]

    if not good_infos:
        print(
            f"[dns-filter] WARNING: no reachable IPs for {host} "
            f"(probed: {[ip for ip, _ in candidates]})"
        )
        return

    if not bad_ips:
        return

    print(
        f"[dns-filter] {host}: pinning to reachable IP(s) {good_ips} "
        f"(dropped dead: {bad_ips})"
    )

    _orig_gai = _sock.getaddrinfo
    _good_set = set(good_ips)
    _patched_marker = "_iaupload_v630_patched"

    if getattr(_orig_gai, _patched_marker, False):
        return

    def _patched_gai(host_arg, port_arg, family=0, type=0, proto=0, flags=0):
        results = _orig_gai(host_arg, port_arg, family, type, proto, flags)
        if host_arg == host:
            filtered = [r for r in results if r[4][0] in _good_set]
            if filtered:
                return filtered
        return results

    setattr(_patched_gai, _patched_marker, True)
    _sock.getaddrinfo = _patched_gai


def handle_dji_lrf(folder_path, auto_confirm=False):
    """
    Finds .LRF files, renames them to _s.MP4 for Archive.org compatibility.
    Checks for collisions to prevent overwriting.
    """
    lrf_files = list(folder_path.rglob("*.[lL][rR][fF]"))
    if not lrf_files:
        return

    print(
        f"\n[!] Detected {len(lrf_files)} DJI LRF files (unsupported by Archive.org)."
    )

    if not auto_confirm:
        try:
            confirm = (
                input(
                    "Rename them to .mp4 with '_s' suffix to allow upload? (y/n) [y]: "
                )
                .strip()
                .lower()
            )
            if confirm and confirm not in ["y", "yes"]:
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
    # --- v6.29: SIGINT handler ---
    try:
        import signal as _signal

        def _sigint_handler(signum, frame):
            print("\n\n!!! CTRL+C RECEIVED !!!")
            print("Setting shutdown flag; in-flight calls will abort shortly...")
            shutdown_event.set()

        _signal.signal(_signal.SIGINT, _sigint_handler)
    except Exception as _sig_err:
        print(f"Warning: could not install SIGINT handler: {_sig_err}")

    # --- v6.30: filter dead s3.us.archive.org IPs before any S3 call ---
    try:
        _filter_ia_s3_dns()
    except Exception as _dns_err:
        print(f"[dns-filter] setup error (continuing): {_dns_err}")

    # --- ARGUMENT PARSING ---
    parser = argparse.ArgumentParser(description="Archive.org Smart Uploader & Syncer")
    parser.add_argument("folder", nargs="?", help="Path to local folder")
    parser.add_argument("identifier", nargs="?", help="Unique Archive.org identifier")
    parser.add_argument(
        "-t",
        "--threads",
        type=int,
        default=DEFAULT_THREADS,
        help=f"Number of parallel upload/delete threads (default: {DEFAULT_THREADS})",
    )
    parser.add_argument(
        "-s", "--sync", action="store_true", help="Sync mode (Upload/Update only)"
    )
    parser.add_argument(
        "-o",
        "--orphan-deletion",
        action="store_true",
        help="Delete remote files that do not exist locally",
    )
    parser.add_argument(
        "-m",
        "--metadata",
        action="store_true",
        help="Force metadata update prompt for existing items",
    )
    parser.add_argument(
        "--md5-verify",
        action="store_true",
        help="Enable MD5 comparison for files that already exist remotely by path",
    )
    parser.add_argument(
        "--fix-lrf",
        action="store_true",
        help="Automatically rename DJI .LRF files to _s.MP4 without prompting",
    )
    parser.add_argument(
        "-z",
        "--zip",
        action="store_true",
        help="Run iazip.py packaging on the folder before uploading (keeps originals, processes all types)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable detailed debug logging for each upload step",
    )
    parser.add_argument(
        "--no-multipart",
        action="store_true",
        help="Disable S3 multipart uploads (use single-stream uploads for all files)",
    )
    # Kept for backwards compatibility; multipart is already the default.
    parser.add_argument(
        "--multipart",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=DEFAULT_CHUNK_SIZE_MB,
        help=f"Chunk size in MB for multipart uploads (default: {DEFAULT_CHUNK_SIZE_MB})",
    )
    parser.add_argument(
        "--multipart-threshold",
        type=int,
        default=DEFAULT_MULTIPART_THRESHOLD_MB,
        help=f"Files >= this many MB use multipart (default: {DEFAULT_MULTIPART_THRESHOLD_MB})",
    )
    parser.add_argument(
        "--multipart-concurrency",
        type=int,
        default=DEFAULT_MULTIPART_CONCURRENCY,
        help=f"Parallel chunk uploads per large file (default: {DEFAULT_MULTIPART_CONCURRENCY})",
    )
    args = parser.parse_args()

    global VERBOSE, _MULTIPART_ENABLED
    VERBOSE = args.verbose

    # v6.23: multipart is on by default; --no-multipart disables it.
    _MULTIPART_ENABLED = (not args.no_multipart) and BOTO3_AVAILABLE

    max_workers = args.threads

    print(f"--- Archive.org Smart Uploader (iaupload v6.35) ---")
    print(f"--- Threads: {max_workers} ---")
    print(f"--- MD5 Verify: {'ON' if args.md5_verify else 'OFF (Path-only)'} ---")
    if _MULTIPART_ENABLED:
        print(f"--- Multipart: ON  (threshold {args.multipart_threshold} MB, chunk {args.chunk_size} MB, {args.multipart_concurrency} parts/file) ---")
    elif args.no_multipart:
        print(f"--- Multipart: OFF (--no-multipart) ---")
    else:
        print(f"--- Multipart: OFF (boto3 not installed; run: pip install boto3) ---")
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
            folder_path_str = (
                get_input("Target Folder", required=True).strip('"').strip("'")
            )

        if not os.path.isdir(folder_path_str):
            print("Error: Folder not found.")
            sys.exit(1)

        folder_path = Path(folder_path_str)

        # --- ZIP FILES BEFORE UPLOAD (if -z flag) ---
        if args.zip:
            if iazip_process is None:
                print("Error: iazip.py not found in the same directory. Cannot use -z flag.")
                sys.exit(1)
            print("\n--- Running iazip packaging before upload (keep originals, all types) ---")
            iazip_process(str(folder_path), move_mode=False, delete_mode=False)

        # Extract suggested date and period from folder name early
        date_info = extract_date_from_string(folder_path.name)
        suggested_date = date_info["date"]
        suggested_period = date_info["period"]

        # Default to today if no date found
        if not suggested_date:
            suggested_date = datetime.date.today().strftime("%Y-%m-%d")
        if not suggested_period:
            suggested_period = datetime.date.today().strftime("%Y")

        # Load metadata prefills early to get identifier suggestion
        metadata_prefills = load_metadata_prefills(folder_path)

        if not identifier:
            # Suggest from metadata file first, then folder name
            default_id = (
                metadata_prefills.get("identifier") if metadata_prefills else None
            )
            if not default_id:
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
            print(
                "Please provide a valid identifier matching: ^[A-Za-z0-9][A-Za-z0-9_.-]{4,100}$"
            )
            sys.exit(1)

        folder_path = Path(folder_path_str)

        # --- PRE-UPLOAD FIXES ---
        handle_dji_lrf(folder_path, auto_confirm=args.fix_lrf)

        # 2. Remote Check
        print(f"\nChecking '{identifier}'...")
        try:
            item = get_item(
                identifier, 
                archive_session=session, 
                request_kwargs={"timeout": (CONNECT_TIMEOUT, READ_TIMEOUT)}
            )
        except Exception as e:
            print(f"\n[!] Network Error while checking item: {e}")
            print("Archive.org's API is currently slow or unavailable. Please try again in a few minutes.")
            sys.exit(1)
            
        metadata = {}
        is_new_item = False
        account_collections = get_account_collections(session)

        if item.exists:
            if args.metadata:
                if get_input("Update metadata? (y/n)", default="n").lower() == "y":
                    metadata = collect_metadata(
                        title_suggestion,
                        prefills=metadata_prefills,
                        account_collections=account_collections,
                        suggested_date=suggested_date,
                        suggested_period=suggested_period,
                    )
        else:
            print(f"  > New item detected.")
            is_new_item = True
            metadata = collect_metadata(
                title_suggestion,
                prefills=metadata_prefills,
                account_collections=account_collections,
                suggested_date=suggested_date,
                suggested_period=suggested_period,
            )

        # 3. MD5 Scanning Phase
        print("\n" + "=" * 30)
        print(
            "PHASE 1: CONTENT VERIFICATION"
            if args.md5_verify
            else "PHASE 1: PATH VERIFICATION"
        )
        print("=" * 30)

        script_name = Path(sys.argv[0]).name

        # 3a. Index Local Files
        print("Indexing local files...")
        local_file_map = {}  # normalized_path -> Path obj
        for p in folder_path.rglob("*"):
            if p.is_file() and p.name != script_name:
                rel_path = p.relative_to(folder_path).as_posix()
                norm = normalize_path(rel_path)
                local_file_map[norm] = {"path": p, "rel_path": rel_path}

        # 3b. Index Remote Files
        remote_map = {}  # normalized_path -> dict with md5 and size
        total_remote_files = 0
        total_remote_originals = 0

        if item.exists:
            print("Fetching remote signatures...")
            total_remote_files = len(item.files)
            for f in item.files:
                if "name" in f and f["name"] != script_name:
                    if f["source"] == "original":  # Only consider original files
                        total_remote_originals += 1
                        norm_path = normalize_path(f["name"])

                        remote_map[norm_path] = {
                            "md5": f.get("md5"),
                            "size": f.get("size"),
                        }

        # 3c. Comparison
        files_to_upload = []
        orphaned_files = []  # List of remote keys to delete

        matched_count = 0
        upload_new_count = 0
        upload_update_count = 0
        skipped_empty_count = 0

        # Detect Uploads
        print(
            f"Scanning {len(local_file_map)} local files against {total_remote_originals} remote originals..."
        )

        with tqdm(
            total=len(local_file_map), desc="Verifying", unit="file", dynamic_ncols=True
        ) as scan_bar:
            for norm_name, info in local_file_map.items():
                if shutdown_event.is_set():
                    break

                local_file = info["path"]
                rel_path = info["rel_path"]
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
                    remote_size = remote_info["size"]
                    remote_md5 = remote_info["md5"]
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
                    # Truncate path components that exceed IA's 230-byte limit
                    safe_rel_path, was_truncated = truncate_path_components(rel_path)
                    if was_truncated:
                        tqdm.write(
                            f"[TRUNCATED]   '{rel_path}'\n"
                            f"           -> '{safe_rel_path}'"
                        )
                    files_to_upload.append((safe_rel_path, local_file))
                    tqdm.write(status_msg)

                scan_bar.update(1)

            scan_bar.set_description("Scan Complete")

        # Detect Orphans (path-based)
        if item.exists:
            for f in item.files:
                if f["source"] == "original" and f["name"] != script_name:
                    norm = normalize_path(f["name"])

                    if norm in local_file_map:
                        continue

                    orphaned_files.append(f["name"])

        if shutdown_event.is_set():
            print("\nScan Cancelled.")
            print_report()
            sys.exit(0)

        # 4. Confirm Actions
        upload_count = len(files_to_upload)
        orphan_count = len(orphaned_files)
        total_local = len(local_file_map)

        print("\n" + "=" * 40)
        print("SUMMARY")
        print("=" * 40)
        print(f"Total Local Files:       {total_local}")
        print(
            f"Total Remote Originals:  {total_remote_originals} (of {total_remote_files} total items)"
        )
        print("-" * 40)
        matched_label = (
            "Matched (MD5 Exact)" if args.md5_verify else "Matched (Path Exists)"
        )
        print(f"{matched_label}:".ljust(28) + f"{matched_count}")
        print(f"To Upload (New):         {upload_new_count}")
        print(f"To Upload (Update):      {upload_update_count}")
        print(f"Skipped Empty Files:     {skipped_empty_count}")
        print(f"Orphans (To Delete):     {orphan_count}")
        print("=" * 40)

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
                    allowed_methods=[
                        "HEAD",
                        "GET",
                        "PUT",
                        "POST",
                        "DELETE",
                        "OPTIONS",
                        "TRACE",
                    ],
                )

                # Pool size must handle all threads + extra for overhead
                adapter = HTTPAdapter(
                    pool_connections=max_workers + 5,
                    pool_maxsize=max_workers + 5,
                    max_retries=retry_strategy,
                )

                # Helper to mount adapter to ArchiveSession which might behave differently than requests.Session
                if hasattr(custom_session, "mount_http_adapter"):
                    # Newer IA library support
                    custom_session.mount_http_adapter("https://", adapter)
                    custom_session.mount_http_adapter("http://", adapter)
                else:
                    # Fallback: hope it inherits from Session or has .mount
                    custom_session.mount("https://", adapter)
                    custom_session.mount("http://", adapter)

                vlog(
                    f"Session configured: pool_connections={max_workers + 5}, pool_maxsize={max_workers + 5}"
                )
                vlog(f"HTTP timeout: connect=30s, read=300s")

            except Exception as e:
                print(f"Warning: Could not configure connection pool: {e}")
                vlog(f"Session config exception: {type(e).__name__}: {e}")
                # Fallback to standard session if mounting fails
                if not custom_session:
                    custom_session = get_session()

            start_index = 0
            main_bar = tqdm(
                total=upload_count,
                desc="Uploading",
                position=0,
                unit="file",
                dynamic_ncols=True,
            )

            if is_new_item:
                # Upload the first (smallest) file to initialize the item
                first_file = files_to_upload[0]
                vlog(f"Creating new item with first file: '{first_file[0]}'")

                # --- v6.23: honor multipart for the first file of a new item too ---
                first_size = os.path.getsize(first_file[1])
                _first_threshold = args.multipart_threshold * 1024 * 1024
                _first_use_mp = _MULTIPART_ENABLED and first_size >= _first_threshold

                if _first_use_mp:
                    vlog(
                        f"Creating new item via MULTIPART with first file: "
                        f"'{first_file[0]}' ({first_size:,} bytes)"
                    )
                    success, msg = multipart_upload_worker(
                        identifier,
                        first_file,
                        metadata,
                        position=1,
                        session=custom_session,
                        chunk_size_mb=args.chunk_size,
                        max_concurrency=args.multipart_concurrency,
                    )
                else:
                    success, msg = upload_worker(
                        identifier, first_file, metadata,
                        position=1, session=custom_session,
                    )

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
                        # --- v6.23: multipart is on by default ---
                        f_size = os.path.getsize(f_data[1])
                        threshold_bytes = args.multipart_threshold * 1024 * 1024
                        use_multipart = _MULTIPART_ENABLED and f_size >= threshold_bytes
                        if use_multipart:
                            vlog(
                                f"worker_wrapper: routing '{f_data[0]}' "
                                f"({f_size:,} bytes) to multipart_upload_worker"
                            )
                            return multipart_upload_worker(
                                identifier,
                                f_data,
                                None,
                                position=slot,
                                session=custom_session,
                                chunk_size_mb=args.chunk_size,
                                max_concurrency=args.multipart_concurrency,
                            )
                        return upload_worker(
                            identifier,
                            f_data,
                            None,
                            position=slot,
                            session=custom_session,
                        )
                    finally:
                        vlog(
                            f"worker_wrapper: releasing slot {slot} (was '{f_data[0]}')"
                        )
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

                                # --- v6.26: read result; surface silent failures ---
                                try:
                                    res = future.result(timeout=0.1)
                                except Exception as e_fut:
                                    tqdm.write(
                                        f"[error] Worker raised for {fdata[0]}: {e_fut}"
                                    )
                                    record_result(
                                        "failed",
                                        f"{fdata[0]} (worker exception: {e_fut})",
                                    )
                                else:
                                    if isinstance(res, tuple) and len(res) == 2:
                                        ok, msg = res
                                        if not ok:
                                            already = (
                                                any(
                                                    fdata[0] in x
                                                    for x in final_results["failed"]
                                                )
                                                or any(
                                                    fdata[0] in x
                                                    for x in final_results["cancelled"]
                                                )
                                            )
                                            if not already:
                                                record_result(
                                                    "failed",
                                                    f"{fdata[0]} ({msg})",
                                                )

                                vlog(
                                    f"Future completed for '{fdata[0]}' "
                                    f"({completed_count}/{len(future_to_file)})"
                                )
                                main_bar.update(1)
                                if time.time() - last_liveness >= 60:
                                    break
                        except TimeoutError:
                            pass

                        pending -= done_batch

                        # Periodic liveness report if anything is still pending
                        if pending and time.time() - last_liveness >= 60:
                            last_liveness = time.time()
                            in_flight = [future_to_file[f][0] for f in pending]
                            if len(in_flight) <= 5:
                                tqdm.write(
                                    f"  [LIVENESS] {len(in_flight)} file(s) still in-flight: {in_flight}"
                                )
                            else:
                                tqdm.write(
                                    f"  [LIVENESS] {len(in_flight)} file(s) still in-flight (showing first 5): {in_flight[:5]}"
                                )

            main_bar.close()

        # --- DELETIONS ---
        if len(files_to_delete) > 0 and not shutdown_event.is_set():
            print("\nStarting Deletions...")
            # Deletes are fast but we can thread them too

            del_bar = tqdm(
                total=len(files_to_delete),
                desc="Deleting",
                position=0,
                unit="file",
                dynamic_ncols=True,
            )

            def delete_worker(fname):
                if shutdown_event.is_set():
                    return
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
        if (
            not shutdown_event.is_set()
            and len(final_results["failed"]) == 0
            and len(final_results["cancelled"]) == 0
        ):
            try:
                answer = (
                    input(
                        f"\nAll files uploaded successfully. Delete local folder '{folder_path}'? (y/n) [n]: "
                    )
                    .strip()
                    .lower()
                )
                if answer == "y":
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