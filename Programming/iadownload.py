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
    """
    retries = 3
    for attempt in range(retries + 1):
        try:
            # Initial request to get headers/size
            with requests.get(url, stream=True, timeout=10) as response:
                if response.status_code != 200:
                    tqdm.write(f"Failed to connect: {url} (Status: {response.status_code})")
                    if attempt < retries:
                        time.sleep(2)
                        continue
                    return

                filename = get_filename_from_response(response, url)
                filepath = os.path.join(folder, filename)
                
                total_size = int(response.headers.get('content-length', 0))
                
                # Check existance
                if os.path.exists(filepath):
                    file_size = os.path.getsize(filepath)
                    if total_size > 0 and file_size == total_size:
                        tqdm.write(f"File exists: {filename}. Verifying...")
                        if verify_archive(filepath):
                            tqdm.write(f"Skipping (verified): {filename}")
                            return
                        else:
                            tqdm.write(f"Corrupt existing file, re-downloading: {filename}")
                    else:
                        tqdm.write(f"Overwriting/Resuming: {filename}")

                desc = f"Downloading {filename[:20]}..." # Truncate for display
                
                # The progress bar for this file
                with tqdm(total=total_size, unit='B', unit_scale=True, desc=desc, 
                          position=position, leave=False) as bar:
                    
                    with open(filepath, 'wb') as f:
                        chunk_size = 8192
                        for chunk in response.iter_content(chunk_size=chunk_size):
                            if chunk:
                                f.write(chunk)
                                bar.update(len(chunk))
            
            # Verify after download
            if verify_archive(filepath):
                return
            else:
                tqdm.write(f"Verification failed for {filename}")
                if attempt < retries:
                    tqdm.write(f"Retrying download ({attempt+1}/{retries})...")
                    if os.path.exists(filepath):
                        os.remove(filepath)
                    time.sleep(2)
                else:
                    tqdm.write(f"Failed to verify {filename} after all attempts.")
                    if os.path.exists(filepath):
                        os.remove(filepath)

        except Exception as e:
            tqdm.write(f"Error downloading {url}: {e}")
            if attempt < retries:
                time.sleep(2)


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

    # Initialize position queue
    # Position 0 is reserved for the 'formatted' total bar (or we just use print)
    # Actually, let's use position 0 for the Total Progress Bar
    for i in range(num_threads):
        position_queue.put(i + 1)

    # Main progress bar (Total Files)
    with tqdm(total=len(urls), unit='file', desc="Total Progress", position=0) as main_bar:
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            # Helper to manage position assignment
            def submit_job(url):
                pos = position_queue.get() # Block until a slot is free? No, queue has N items.
                # Actually, ThreadPool might start more tasks than workers? No, max_workers limits active threads.
                # But we need to ensure the worker releases the position.
                try:
                    download_url_worker(url, dest_folder, pos)
                finally:
                    position_queue.put(pos)
                    main_bar.update(1)

            # Submit all jobs
            # Note: We wrap the submission to ensure position reuse works correctly
            # Simpler: Map iterables? No, we need the `finally` block inside the thread.
            
            futures = [executor.submit(submit_job, url) for url in urls]
            concurrent.futures.wait(futures)

    print("\nAll downloads finished.")


def download_ia_file_worker(file_obj, identifier, dest_folder, position):
    """
    Worker function to download a single IA file with a progress bar at a specific screen position.
    """
    retries = 3
    for attempt in range(retries + 1):
        try:
            filename = file_obj.name
            # Create subdirectories as needed (files can be in subfolders like "identifier/subfolder/file.jpg")
            filepath = os.path.join(dest_folder, identifier, filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # Get file size from metadata
            total_size = int(file_obj.size) if file_obj.size else 0
            
            # Skip if exists and same size
            if os.path.exists(filepath):
                if total_size > 0 and os.path.getsize(filepath) == total_size:
                    # Skip verify? Or verify?
                    # Let's verify briefly if it's an archive
                    if verify_archive(filepath):
                        tqdm.write(f"Skipping (verified): {filename}")
                        return
                    else:
                         tqdm.write(f"File exists but corrupt: {filename}")
            
            # Build download URL
            url = f"https://archive.org/download/{identifier}/{filename}"
            
            desc = f"{identifier}/{filename}"
            if len(desc) > 50:
                desc = f"...{desc[-47:]}"
            
            with requests.get(url, stream=True, timeout=60) as response:
                if response.status_code != 200:
                    tqdm.write(f"Failed to download: {filename} (Status: {response.status_code})")
                    if attempt < retries:
                        time.sleep(2)
                        continue
                    return
                
                # Use content-length from response if available, otherwise use metadata
                response_size = int(response.headers.get('content-length', 0))
                if response_size > 0:
                    total_size = response_size
                
                with tqdm(total=total_size, unit='B', unit_scale=True, desc=desc,
                        position=position, leave=False) as bar:
                    with open(filepath, 'wb') as f:
                        chunk_size = 8192
                        for chunk in response.iter_content(chunk_size=chunk_size):
                            if chunk:
                                f.write(chunk)
                                bar.update(len(chunk))
            
            # Verify
            if verify_archive(filepath):
                return
            else:
                tqdm.write(f"Verification failed for {filename}")
                if attempt < retries:
                    tqdm.write(f"Retrying ({attempt+1}/{retries})...")
                    if os.path.exists(filepath):
                        os.remove(filepath)
                    time.sleep(2)
                else:
                    tqdm.write(f"Failed to verify {filename} after retries.")
                    if os.path.exists(filepath):
                        os.remove(filepath)

        except Exception as e:
            tqdm.write(f"Error downloading {file_obj.name}: {e}")
            if attempt < retries:
                time.sleep(2)


def process_ia_item(identifier, dest_folder, num_threads):
    """
    Downloads an IA Item using concurrent downloads.
    """
    print(f"Detected Input as Internet Archive Identifier: {identifier}")
    print(f"Downloading item to: {dest_folder}")
    
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
        os.makedirs(os.path.join(dest_folder, identifier), exist_ok=True)
        
        # Initialize position queue
        for i in range(num_threads):
            position_queue.put(i + 1)
        
        # Main progress bar (Total Files)
        with tqdm(total=len(files), unit='file', desc="Total Progress", position=0) as main_bar:
            
            with ThreadPoolExecutor(max_workers=num_threads) as executor:
                def submit_job(file_obj):
                    pos = position_queue.get()
                    try:
                        download_ia_file_worker(file_obj, identifier, dest_folder, pos)
                    finally:
                        position_queue.put(pos)
                        main_bar.update(1)
                
                futures = [executor.submit(submit_job, f) for f in files]
                concurrent.futures.wait(futures)
        
        print("\nItem download complete.")
    except Exception as e:
        print(f"Error downloading item '{identifier}': {e}")


def main():
    parser = argparse.ArgumentParser(description="Unified Internet Archive Downloader (ID or URL List)")
    parser.add_argument("input", help="URL list file path OR Internet Archive Identifier")
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
        # Mode: IA Item (Assume it's an ID if it's not a file)
        # Note: If the user intended a file that doesn't exist, this will try to download it as an IA item.
        # Use simple validation: IA IDs usually don't have extensions like .txt, but they can contain dots.
        # We'll assume the user knows.
        
        if not args.folder:
            # Default behavior for IA is usually creating a folder named ID.
            # We can pass the ID itself as dest logic or let None execute default.
            dest = input_arg
        else:
            dest = args.folder
            
        process_ia_item(input_arg, dest, args.threads)

if __name__ == "__main__":
    main()
