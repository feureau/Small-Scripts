#!/usr/bin/env python3
import os
import sys
import requests
from concurrent.futures import ThreadPoolExecutor

def download_file(url):
    """Downloads a single file to the current working directory."""
    try:
        # Extract filename from URL (remove query parameters)
        filename = url.split('/')[-1].split('?')[0]
        if not filename:
            filename = "downloaded_file"
            
        # Define the path based on where you are running the command (CWD)
        target_path = os.path.join(os.getcwd(), filename)
        
        # Stream the download to optimize memory for large files
        with requests.get(url, stream=True, timeout=15) as r:
            r.raise_for_status()
            with open(target_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=16384): # 16KB chunks
                    if chunk:
                        f.write(chunk)
        return f"Done: {filename}"
    except Exception as e:
        return f"Error downloading {url}: {e}"

def main():
    # 1. Verify command line argument for the URL list
    if len(sys.argv) < 2:
        print("Usage: downloader.py <list.txt>")
        sys.exit(1)

    list_filename = sys.argv[1]

    # 2. Check if the file exists in the current directory
    if not os.path.isfile(list_filename):
        print(f"Error: File '{list_filename}' not found in the current directory.")
        sys.exit(1)

    # 3. Read URLs and filter out empty lines
    with open(list_filename, 'r') as f:
        urls = [line.strip() for line in f if line.strip()]

    if not urls:
        print("The provided list is empty.")
        return

    print(f"Starting parallel download of {len(urls)} files...")
    print(f"Saving files to: {os.getcwd()}\n")

    # 4. Use ThreadPoolExecutor for parallel speed
    # max_workers=10 is a good balance; increase for faster fiber connections
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(download_file, urls))

    # Print summary of results
    for res in results:
        print(res)

if __name__ == "__main__":
    main()