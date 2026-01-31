import os
import sys
import re
import json
import requests
import argparse

def get_bundle_metadata(archive_id, inv_nr):
    """Fetches the full list of file identifiers by scraping the archive page."""
    # We append pageSize=10000 to the page URL to get as many files as possible
    url = f"https://www.nationaalarchief.nl/onderzoeken/archief/{archive_id}/invnr/{inv_nr}/file?pageSize=10000"
    print(f"[*] Fetching archive page for Inventory {inv_nr}...")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"[!] Error: Could not fetch archive page. (Status: {response.status_code})")
            return None
        
        # Extract the drupal-settings-json script tag
        match = re.search(r'<script type="application/json" data-drupal-selector="drupal-settings-json">(.*?)</script>', response.text, re.DOTALL)
        if not match:
            print("[!] Error: Could not find metadata in page.")
            return None
        
        settings = json.loads(match.group(1))
        view_response_str = settings.get('na_viewer', {}).get('view_response')
        if not view_response_str:
            print("[!] Error: Could not find view_response in metadata.")
            return None
        
        return json.loads(view_response_str)
    except Exception as e:
        print(f"[!] Error during metadata extraction: {e}")
        return None

def download_files(archive_id, inv_nr, file_type):
    data = get_bundle_metadata(archive_id, inv_nr)
    if not data or 'files' not in data:
        print("[!] No files found.")
        return

    files = data['files']
    total = len(files)
    print(f"[*] Found {total} images. Starting download...")

    # Create directory for inventory
    if not os.path.exists(inv_nr):
        os.makedirs(inv_nr)

    for index, f in enumerate(files, 1):
        uuid = f['fileuuid']
        filename = f['filename'].replace('.tif', '.jpg') # NA serves JPGs via render API
        
        # Determine URL based on requested format
        if file_type == 'original_bestand':
            # This is the raw high-res render
            url = f"https://service.archief.nl/gaf/api/file/v1/render/{uuid}"
        elif file_type == 'klein':
            # Small preview
            url = f"https://service.archief.nl/gaf/api/file/v1/thumb/{uuid}"
        else: # original_formaat (Default)
            # High-res but standard render
            url = f"https://service.archief.nl/gaf/api/file/v1/render/{uuid}"

        save_path = os.path.join(inv_nr, f"{index:04d}_{filename}")
        
        if os.path.exists(save_path):
            print(f"[-] [{index}/{total}] Skipping {filename} (Already exists)")
            continue

        try:
            r = requests.get(url, stream=True)
            if r.status_code == 200:
                with open(save_path, 'wb') as fd:
                    for chunk in r.iter_content(chunk_size=1024*1024):
                        fd.write(chunk)
                print(f"[+] [{index}/{total}] Downloaded {filename}")
            else:
                print(f"[!] Failed to download {filename} (Status: {r.status_code})")
        except Exception as e:
            print(f"[!] Error downloading {filename}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download bundles from Nationaal Archief")
    parser.add_argument("url", help="The full URL of the archive page")
    parser.add_argument("--format", choices=['orig', 'small', 'file'], default='orig', 
                        help="orig: Original Formaat, small: Klein Formaat, file: Origineel Bestand")
    
    args = parser.parse_args()

    # Extract archive ID (e.g., 1.04.02) and inventory number (e.g., 1340) from the URL
    match = re.search(r'/archief/([^/]+)/invnr/(\d+)', args.url)
    if not match:
        print("[!] Could not find Archive ID or Inventory Number in URL.")
        sys.exit(1)
    
    archive_id = match.group(1)
    inv_id = match.group(2)
    
    # Map flags to API types
    type_map = {
        'orig': 'original_formaat',
        'small': 'klein',
        'file': 'original_bestand'
    }
    
    download_files(archive_id, inv_id, type_map[args.format])