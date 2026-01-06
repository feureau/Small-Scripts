import sys
import os
import requests
import re
import time

def download_file(url, folder="."):
    try:
        print(f"Connecting to: {url}")
        print("Requesting compression (this may take a while for large items)...")
        
        # Stream=True is crucial for large files
        with requests.get(url, stream=True) as response:
            response.raise_for_status()
            
            # Try to get the filename from the Content-Disposition header
            # The header usually looks like: attachment; filename="identifier.zip"
            content_disposition = response.headers.get('content-disposition')
            
            filename = ""
            if content_disposition:
                fname_match = re.findall('filename="(.+)"', content_disposition)
                if fname_match:
                    filename = fname_match[0]
            
            # Fallback if no header name found
            if not filename:
                # Take the last part of the URL (the identifier) and add .zip
                filename = url.split('/')[-1] + ".zip"

            # Create full path
            filepath = os.path.join(folder, filename)

            # Check if file already exists to avoid re-downloading
            if os.path.exists(filepath):
                print(f"Skipping: '{filename}' already exists.")
                return

            total_size = int(response.headers.get('content-length', 0))
            
            print(f"Downloading: {filename}")
            
            # Download and write to file in chunks
            with open(filepath, 'wb') as f:
                downloaded = 0
                chunk_size = 8192
                
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Simple text-based progress bar
                        if total_size > 0:
                            percent = int(100 * downloaded / total_size)
                            sys.stdout.write(f"\rProgress: {percent}% - {downloaded / (1024*1024):.2f} MB")
                            sys.stdout.flush()
                        else:
                            # If server doesn't report size, just show downloaded amount
                            sys.stdout.write(f"\rDownloaded: {downloaded / (1024*1024):.2f} MB")
                            sys.stdout.flush()
            
            print(f"\nCompleted: {filename}\n" + "-"*30)

    except KeyboardInterrupt:
        print("\nDownload canceled by user.")
        sys.exit()
    except Exception as e:
        print(f"\nError downloading {url}: {e}\n" + "-"*30)

def main(input_file):
    if not os.path.exists(input_file):
        print(f"Error: File list '{input_file}' not found.")
        sys.exit(1)

    # Optional: Create a 'downloads' folder so files don't clutter the script folder
    download_dir = "downloads"
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)

    print(f"Reading links from {input_file}...")
    print(f"Saving files to folder: ./{download_dir}/")
    print("-" * 30)

    with open(input_file, 'r') as f:
        urls = f.readlines()

    for url in urls:
        url = url.strip()
        if url: # Make sure line isn't empty
            download_file(url, download_dir)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python archiveorgdownloader.py <path_to_link_list.txt>")
    else:
        file_list = sys.argv[1]
        main(file_list)