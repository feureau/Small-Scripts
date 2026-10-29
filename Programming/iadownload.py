#!/usr/bin/env python3
"""
iadownload.py

A unified downloader for Internet Archive.
Can download:
1. A list of URLs from a text file (Concurrent, with progress bars).
2. An entire Internet Archive Item by ID (using official `ia` tool).

Usage:
  python iadownload.py <input_file_or_id> [<destination_folder>] [--threads N]

Arguments:
  input_file_or_id     Path to a text file containing URLs OR an IA Item Identifier.
  destination_folder   (Optional) Folder to save downloads. Defaults to 'downloads' (for list) or item ID (for item).
  --threads            Number of concurrent download threads (default: 5).

Requirements:
  pip install internetarchive tqdm requests
"""

import sys
import os
import requests
import re
import argparse
import time
import queue
from pathlib import Path
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor, as_completed
import mimetypes

try:
    from tqdm import tqdm
except ImportError:
    print("Error: 'tqdm' module not found. Please install it:\n  pip install tqdm")
    sys.exit(1)

import internetarchive as ia
import zipfile
import tarfile
import hashlib
from urllib.parse import quote

# Optional imports for 7z and rar
try:
    import py7zr
except ImportError:
    py7zr = None

try:
    import rarfile
except ImportError:
    rarfile = None


# Global queue for managing tqdm positions for threads
# Positions: 0 is for the main total progress bar. 1..N are for threads.
position_queue = queue.Queue()


def get_filename_from_response(response, url):
    """Extracts filename from Content-Disposition header or URL. Adds extension if missing."""
    content_disposition = response.headers.get('content-disposition', '')
    filename = ""
    
    # Try to extract filename from Content-Disposition
    if content_disposition:
        # Look for filename="name" or filename=name
        # This regex handles quoted and unquoted roughly
        fname_match = re.search(r'filename=["\']?([^"\';]+)["\']?', content_disposition)
        if fname_match:
            filename = fname_match.group(1)
    
    # Fallback to URL
    if not filename:
        parsed_url = url.split('?')[0] # Remove query params
        filename = parsed_url.split('/')[-1]
    
    # Fallback to default
    if not filename:
        filename = "downloaded_file"
        
    # Attempt to guess extension if missing
    import os
    name, ext = os.path.splitext(filename)
    if not ext:
        content_type = response.headers.get('content-type')
        if content_type:
            # Clean content type (remove charset etc)
            content_type = content_type.split(';')[0].strip()
            guessed_ext = mimetypes.guess_extension(content_type)
            if guessed_ext:
                filename = f"{filename}{guessed_ext}"
    
    return filename


def verify_md5(filepath, expected_md5):
    """
    Verifies the MD5 checksum of a file if expected_md5 is provided.
    """
    if not expected_md5:
        return True
    if not os.path.exists(filepath):
        return False
    hash_md5 = hashlib.md5()
    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest().lower() == expected_md5.lower()
    except Exception as e:
        tqdm.write(f"MD5 check error for '{os.path.basename(filepath)}': {e}")
        return False


def verify_archive(filepath):
    """
    Verifies the integrity of an archive file.
    Returns True if valid, False if invalid.
    Returns True (with warning) if format not supported or module missing.
    """
    import os
    filename = os.path.basename(filepath)
    # Check if file exists and size > 0
    if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
        return False

    ext = os.path.splitext(filename)[1].lower()

    try:
        if ext == '.zip':
            with zipfile.ZipFile(filepath) as zf:
                bad_file = zf.testzip()
                if bad_file:
                    tqdm.write(f"Verification FAILED for '{filename}': Corrupt member '{bad_file}'")
                    return False
                return True
        
        elif ext in ('.tar', '.tgz', '.tar.gz'):
            try:
                with tarfile.open(filepath, 'r:*') as tf:
                    for _ in tf:
                        pass
                return True
            except (tarfile.TarError, EOFError) as e:
                tqdm.write(f"Verification FAILED for '{filename}': {e}")
                return False

        elif ext == '.7z':
            if py7zr:
                if not py7zr.is_7zfile(filepath):
                    tqdm.write(f"Verification FAILED for '{filename}': Not a valid 7z file.")
                    return False
                try:
                    with py7zr.SevenZipFile(filepath, mode='r') as z:
                         if z.test():
                             tqdm.write(f"Verification FAILED for '{filename}': checksum error")
                             return False
                    return True
                except Exception as e:
                    tqdm.write(f"Verification FAILED for '{filename}': {e}")
                    return False
            else:
                return True

        elif ext == '.rar':
            if rarfile:
                try:
                    with rarfile.RarFile(filepath) as rf:
                         rf.testrar()
                    return True
                except rarfile.RarExecError:
                    tqdm.write(f"Warning: unrar executable not found. Skipping verification for '{filename}'.")
                    return True
                except Exception as e:
                    tqdm.write(f"Verification FAILED for '{filename}': {e}")
                    return False
            else:
                return True

    except Exception as e:
        tqdm.write(f"Verification Error checking '{filename}': {e}")
        return False

    return True


def download_url_worker(url, folder, position):
    """
    Worker function to download a single URL with a progress bar at a specific screen position.
    Returns True if downloaded/verified, False otherwise.
    """
    retries = 5
    filename = ""
    filepath = ""
    total_size = 0

    for attempt in range(retries + 1):
        try:
            existing_size = os.path.getsize(filepath) if filepath and os.path.exists(filepath) else 0
            headers = {}
            if existing_size > 0 and (total_size == 0 or existing_size < total_size):
                headers['Range'] = f'bytes={existing_size}-'

            with requests.get(url, headers=headers, stream=True, timeout=30) as response:
                if response.status_code == 416:
                    # Range not satisfiable - reset and retry from 0
                    if filepath and os.path.exists(filepath):
                        os.remove(filepath)
                    continue

                if response.status_code not in (200, 206):
                    tqdm.write(f"Failed to connect: {url} (Status: {response.status_code})")
                    if attempt < retries:
                        time.sleep(min(2 ** attempt, 30))
                        continue
                    return False

                if not filename:
                    filename = get_filename_from_response(response, url)
                    filepath = os.path.join(folder, filename)

                is_resume = (response.status_code == 206)
                content_len = int(response.headers.get('content-length', 0))

                if is_resume:
                    if total_size == 0 and content_len > 0:
                        total_size = existing_size + content_len
                else:
                    existing_size = 0
                    if content_len > 0:
                        total_size = content_len

                    # Check if already completely downloaded before overwriting
                    if os.path.exists(filepath):
                        file_size = os.path.getsize(filepath)
                        if total_size > 0 and file_size == total_size:
                            if verify_archive(filepath):
                                tqdm.write(f"Skipping (verified): {filename}")
                                return True
                            else:
                                tqdm.write(f"Corrupt existing file, re-downloading: {filename}")

                desc = f"Downloading {filename[:20]}..."
                mode = 'ab' if is_resume else 'wb'

                with tqdm(total=total_size, initial=existing_size, unit='B', unit_scale=True, desc=desc,
                          position=position, leave=False) as bar:
                    with open(filepath, mode) as f:
                        for chunk in response.iter_content(chunk_size=65536):
                            if chunk:
                                f.write(chunk)
                                bar.update(len(chunk))

            # Verify size and archive integrity after download
            actual_size = os.path.getsize(filepath) if os.path.exists(filepath) else 0
            if total_size > 0 and actual_size != total_size:
                tqdm.write(f"Size mismatch for {filename}: got {actual_size}/{total_size} bytes")
                if attempt < retries:
                    time.sleep(min(2 ** attempt, 30))
                    continue
                return False

            if verify_archive(filepath):
                return True
            else:
                tqdm.write(f"Verification failed for {filename}")
                if os.path.exists(filepath):
                    os.remove(filepath)
                if attempt < retries:
                    tqdm.write(f"Retrying download ({attempt+1}/{retries})...")
                    time.sleep(min(2 ** attempt, 30))
                else:
                    tqdm.write(f"Failed to verify {filename} after all attempts.")
                    return False

        except Exception as e:
            tqdm.write(f"Error downloading {url} (attempt {attempt+1}/{retries+1}): {e}")
            if attempt < retries:
                time.sleep(min(2 ** attempt, 30))

    return False


def process_url_list(input_file, dest_folder, num_threads):
    """
    Reads URLs from a file and downloads them concurrently.
    """
    if not os.path.exists(dest_folder):
        os.makedirs(dest_folder)
        
    print(f"Reading URLs from '{input_file}'...")
    with open(input_file, 'r') as f:
        urls = [line.strip() for line in f if line.strip()]

    if not urls:
        print("No URLs found.")
        return

    print(f"Found {len(urls)} URLs. Downloading to '{dest_folder}/' with {num_threads} threads...")
    print("-" * 40)

    for i in range(num_threads):
        position_queue.put(i + 1)

    failed_urls = []

    with tqdm(total=len(urls), unit='file', desc="Total Progress", position=0) as main_bar:
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            def submit_job(url):
                pos = position_queue.get()
                try:
                    return url, download_url_worker(url, dest_folder, pos)
                finally:
                    position_queue.put(pos)
                    main_bar.update(1)

            futures = [executor.submit(submit_job, url) for url in urls]
            for future in as_completed(futures):
                url, ok = future.result()
                if not ok:
                    failed_urls.append(url)

    if failed_urls:
        print(f"\nWARNING: {len(failed_urls)} URL(s) failed to download:")
        for u in failed_urls:
            print(f"  - {u}")
    else:
        print("\nAll downloads finished and verified successfully.")


def download_ia_file_worker(file_obj, identifier, dest_folder, position, retries=5):
    """
    Worker function to download a single IA file with HTTP Range resume,
    size/MD5/archive verification, and exponential backoff.
    Returns True if downloaded and verified, False otherwise.
    """
    filename = file_obj.name
    filepath = os.path.join(dest_folder, identifier, filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    total_size = int(file_obj.size) if getattr(file_obj, 'size', None) else 0
    expected_md5 = getattr(file_obj, 'md5', None)

    # Check if already completely downloaded and valid
    if os.path.exists(filepath):
        current_size = os.path.getsize(filepath)
        if total_size > 0 and current_size == total_size:
            if verify_md5(filepath, expected_md5) and verify_archive(filepath):
                tqdm.write(f"Skipping (verified): {filename}")
                return True
            else:
                tqdm.write(f"Existing file corrupt/mismatch, re-downloading: {filename}")
                os.remove(filepath)
        elif total_size > 0 and current_size > total_size:
            os.remove(filepath)

    # URL-encode path segments while preserving '/'
    encoded_filename = quote(filename, safe='/')
    url = f"https://archive.org/download/{identifier}/{encoded_filename}"

    desc = f"{identifier}/{filename}"
    if len(desc) > 50:
        desc = f"...{desc[-47:]}"

    for attempt in range(retries + 1):
        try:
            existing_size = os.path.getsize(filepath) if os.path.exists(filepath) else 0
            headers = {}
            if existing_size > 0 and (total_size == 0 or existing_size < total_size):
                headers['Range'] = f'bytes={existing_size}-'

            with requests.get(url, headers=headers, stream=True, timeout=60) as response:
                if response.status_code == 416:
                    # Range not satisfiable; delete partial file and retry from 0
                    if os.path.exists(filepath):
                        os.remove(filepath)
                    continue

                if response.status_code not in (200, 206):
                    tqdm.write(f"Failed to download: {filename} (Status: {response.status_code}, attempt {attempt+1}/{retries+1})")
                    if attempt < retries:
                        time.sleep(min(2 ** attempt, 30))
                        continue
                    return False

                is_resume = (response.status_code == 206)
                content_len = int(response.headers.get('content-length', 0))

                if is_resume:
                    if total_size == 0 and content_len > 0:
                        total_size = existing_size + content_len
                else:
                    existing_size = 0
                    if content_len > 0 and total_size == 0:
                        total_size = content_len

                mode = 'ab' if is_resume else 'wb'

                with tqdm(total=total_size, initial=existing_size, unit='B', unit_scale=True, desc=desc,
                          position=position, leave=False) as bar:
                    with open(filepath, mode) as f:
                        for chunk in response.iter_content(chunk_size=65536):
                            if chunk:
                                f.write(chunk)
                                bar.update(len(chunk))

            # 1. Verify exact byte size
            actual_size = os.path.getsize(filepath) if os.path.exists(filepath) else 0
            if total_size > 0 and actual_size < total_size:
                tqdm.write(f"Incomplete download for {filename} ({actual_size}/{total_size} bytes). Resuming...")
                if attempt < retries:
                    time.sleep(min(2 ** attempt, 30))
                    continue
                return False
            elif total_size > 0 and actual_size > total_size:
                tqdm.write(f"Size overflow for {filename} ({actual_size}/{total_size} bytes). Resetting...")
                os.remove(filepath)
                if attempt < retries:
                    time.sleep(min(2 ** attempt, 30))
                    continue
                return False

            # 2. Verify MD5 checksum (from IA metadata) & archive structure
            if verify_md5(filepath, expected_md5) and verify_archive(filepath):
                return True
            else:
                tqdm.write(f"Verification (MD5/Archive) failed for {filename}")
                if os.path.exists(filepath):
                    os.remove(filepath)
                if attempt < retries:
                    tqdm.write(f"Retrying from scratch ({attempt+1}/{retries})...")
                    time.sleep(min(2 ** attempt, 30))
                else:
                    tqdm.write(f"Failed to verify {filename} after all retries.")
                    return False

        except Exception as e:
            tqdm.write(f"Connection interrupted for {filename} (attempt {attempt+1}/{retries+1}): {e}")
            if attempt < retries:
                wait_sec = min(2 ** attempt, 30)
                tqdm.write(f"Resuming {filename} in {wait_sec}s...")
                time.sleep(wait_sec)

    tqdm.write(f"Giving up on {filename} after {retries+1} attempts.")
    return False


def extract_ia_identifier(input_str):
    """
    Extracts the Internet Archive identifier if an archive.org URL is provided.
    """
    match = re.match(r'^https?://(?:www\.)?archive\.org/(?:details|download|metadata)/([^/?#]+)', input_str.strip())
    if match:
        return match.group(1)
    return input_str.strip()


def process_ia_item(identifier, dest_folder, num_threads):
    """
    Downloads an IA Item using concurrent downloads with automatic retry rounds for any failed files.
    """
    target_dir = os.path.join(dest_folder, identifier) if dest_folder else identifier
    print(f"Detected Input as Internet Archive Identifier: {identifier}")
    print(f"Downloading item to: {target_dir}")
    
    try:
        # Fetch item metadata
        item = ia.get_item(identifier)
        files = list(item.get_files())
        
        if not files:
            print(f"No files found for item '{identifier}'")
            return
        
        print(f"Found {len(files)} files. Downloading with {num_threads} threads...")
        print("-" * 40)
        
        # Create destination folder
        os.makedirs(target_dir, exist_ok=True)
        
        # Clear and initialize position queue
        while not position_queue.empty():
            position_queue.get()
        for i in range(num_threads):
            position_queue.put(i + 1)
        
        failed_files = []

        # Main progress bar (Total Files)
        with tqdm(total=len(files), unit='file', desc="Total Progress", position=0) as main_bar:
            with ThreadPoolExecutor(max_workers=num_threads) as executor:
                def submit_job(file_obj):
                    pos = position_queue.get()
                    try:
                        return file_obj, download_ia_file_worker(file_obj, identifier, dest_folder, pos)
                    finally:
                        position_queue.put(pos)
                        main_bar.update(1)
                
                futures = [executor.submit(submit_job, f) for f in files]
                for future in as_completed(futures):
                    file_obj, ok = future.result()
                    if not ok:
                        failed_files.append(file_obj)

        # Final recovery pass (fewer threads, more retries) if any files still failed
        if failed_files:
            print(f"\n{len(failed_files)} file(s) had persistent errors. Running recovery pass with 2 threads...")
            still_failed = []
            with tqdm(total=len(failed_files), unit='file', desc="Recovery Pass", position=0) as retry_bar:
                with ThreadPoolExecutor(max_workers=min(2, num_threads)) as executor:
                    def submit_retry(file_obj):
                        pos = position_queue.get()
                        try:
                            return file_obj, download_ia_file_worker(file_obj, identifier, dest_folder, pos, retries=8)
                        finally:
                            position_queue.put(pos)
                            retry_bar.update(1)

                    futures = [executor.submit(submit_retry, f) for f in failed_files]
                    for future in as_completed(futures):
                        file_obj, ok = future.result()
                        if not ok:
                            still_failed.append(file_obj)
            failed_files = still_failed

        if failed_files:
            print(f"\nWARNING: {len(failed_files)} file(s) could not be completed:")
            for f in failed_files:
                print(f"  - {f.name}")
            sys.exit(1)
        else:
            print(f"\nItem download complete! All {len(files)} files verified (size + MD5).")
    except Exception as e:
        print(f"Error downloading item '{identifier}': {e}")


def main():
    parser = argparse.ArgumentParser(description="Unified Internet Archive Downloader (ID, IA URL, or URL List)")
    parser.add_argument("input", help="URL list file path OR Internet Archive Identifier / URL")
    parser.add_argument("folder", nargs="?", help="Destination folder (Optional)")
    parser.add_argument("--threads", type=int, default=5, help="Number of threads for URL list download (default: 5)")
    
    args = parser.parse_args()

    input_arg = args.input
    
    # Logic to determine mode
    if os.path.isfile(input_arg):
        # Mode: File List
        dest = args.folder if args.folder else "downloads"
        process_url_list(input_arg, dest, args.threads)
    else:
        # Mode: IA Item (Assume it's an ID or IA URL if it's not a file)
        # Note: If the user intended a file that doesn't exist, this will try to download it as an IA item.
        # Use simple validation: IA IDs usually don't have extensions like .txt, but they can contain dots.
        # We'll assume the user knows.
        identifier = extract_ia_identifier(input_arg)
        dest = args.folder if args.folder else ""
            
        process_ia_item(identifier, dest, args.threads)

if __name__ == "__main__":
    main()
