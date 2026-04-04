import os
import sys
import re
import json
import time
import shutil
import requests
import argparse

def get_bundle_metadata(archive_id, inv_nr):
    """Fetches the full list of file identifiers by scraping the archive page."""
    # Use the @-prefixed inventory URL to get the viewer page with embedded metadata
    url = f"https://www.nationaalarchief.nl/onderzoeken/archief/{archive_id}/invnr/@{inv_nr}/file?pageSize=10000"
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
        # Try new structure first: viewer.response
        viewer_data = settings.get('viewer', {}).get('response')
        if viewer_data:
            if isinstance(viewer_data, str):
                return json.loads(viewer_data)
            return viewer_data
        # Fallback to old structure: na_viewer.view_response (JSON string)
        view_response_str = settings.get('na_viewer', {}).get('view_response')
        if view_response_str:
            return json.loads(view_response_str)
        print("[!] Error: Could not find viewer metadata in page.")
        return None
    except Exception as e:
        print(f"[!] Error during metadata extraction: {e}")
        return None

def is_valid_image(filepath):
    """Check if a file is a valid, non-corrupt image (JPEG or PNG)."""
    try:
        size = os.path.getsize(filepath)
        if size == 0:
            return False
        # Check for valid image headers
        with open(filepath, 'rb') as f:
            header = f.read(8)
            if len(header) < 3:
                return False
            # JPEG: starts with FF D8 FF
            if header[:3] == b'\xff\xd8\xff':
                # Also check the file ends with FF D9 (JPEG end marker)
                f.seek(-2, 2)
                return f.read(2) == b'\xff\xd9'
            # PNG: starts with 89 50 4E 47 0D 0A 1A 0A
            if header[:8] == b'\x89PNG\r\n\x1a\n':
                return True
            # Unknown format — accept if non-empty
            return size > 1024
    except Exception:
        return False

def format_size(num_bytes):
    """Format bytes into a human-readable string."""
    for unit in ('B', 'KB', 'MB', 'GB'):
        if abs(num_bytes) < 1024:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f} TB"

def format_time(seconds):
    """Format seconds into a human-readable duration."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        m, s = divmod(int(seconds), 60)
        return f"{m}m {s}s"
    else:
        h, rem = divmod(int(seconds), 3600)
        m, s = divmod(rem, 60)
        return f"{h}h {m}m {s}s"

def print_progress(index, total, stats, start_time):
    """Print a dynamic progress bar that updates in place."""
    elapsed = time.time() - start_time
    processed = stats['downloaded'] + stats['skipped'] + stats['redownloaded'] + stats['failed'] + stats['corrupt']
    pct = (index / total) * 100 if total else 0

    # Calculate speed from downloaded bytes
    speed = stats['bytes_downloaded'] / elapsed if elapsed > 0 else 0
    speed_str = f"{format_size(speed)}/s" if speed > 0 else "--"

    # ETA based on items processed
    if processed > 0 and elapsed > 0:
        items_per_sec = processed / elapsed
        remaining = (total - index) / items_per_sec if items_per_sec > 0 else 0
        eta_str = format_time(remaining)
    else:
        eta_str = "--"

    # Build progress bar
    try:
        term_width = shutil.get_terminal_size().columns
    except Exception:
        term_width = 80
    bar_width = max(10, term_width - 55)
    filled = int(bar_width * index / total) if total else 0
    bar = '█' * filled + '░' * (bar_width - filled)

    line = f"\r  {bar} {pct:5.1f}% | {index}/{total} | {speed_str} | ETA: {eta_str}"
    # Pad to clear previous line, truncate to terminal width
    line = line.ljust(term_width)[:term_width]
    sys.stdout.write(line)
    sys.stdout.flush()

def download_files(archive_id, inv_nr, file_type):
    data = get_bundle_metadata(archive_id, inv_nr)
    if not data:
        print("[!] No data found.")
        return

    # Support both new ('scans') and old ('files') data structures
    scans = data.get('scans', data.get('files', []))
    if not scans:
        print("[!] No files found.")
        return

    total = len(scans)
    print(f"[*] Found {total} images. Starting download...")
    print()  # blank line before progress bar

    # Create directory for inventory
    if not os.path.exists(inv_nr):
        os.makedirs(inv_nr)

    # Tracking stats
    stats = {
        'downloaded': 0,
        'skipped': 0,
        'redownloaded': 0,
        'failed': 0,
        'corrupt': 0,
        'bytes_downloaded': 0,
    }
    failed_files = []
    start_time = time.time()

    for index, f in enumerate(scans, 1):
        # Support both new ('id'/'label') and old ('fileuuid'/'filename') keys
        uuid = f.get('id', f.get('fileuuid', ''))
        raw_filename = f.get('label', f.get('filename', f'scan_{index:04d}.jpg'))
        filename = raw_filename.replace('.tif', '.jpg')  # NA serves JPGs via render API
        
        # Determine URL based on requested format
        if file_type == 'original_bestand':
            url = f"https://service.archief.nl/api/file/v1/default/{uuid}"
        elif file_type == 'klein':
            url = f"https://service.archief.nl/api/file/v1/thumb/{uuid}"
        else:  # original_formaat (Default)
            url = f"https://service.archief.nl/api/file/v1/default/{uuid}"

        save_path = os.path.join(inv_nr, f"{index:04d}_{filename}")
        is_redownload = False

        if os.path.exists(save_path):
            if is_valid_image(save_path):
                stats['skipped'] += 1
                print_progress(index, total, stats, start_time)
                continue
            else:
                is_redownload = True
                os.remove(save_path)

        try:
            r = requests.get(url, stream=True)
            if r.status_code == 200:
                with open(save_path, 'wb') as fd:
                    for chunk in r.iter_content(chunk_size=1024*1024):
                        fd.write(chunk)
                file_size = os.path.getsize(save_path)
                stats['bytes_downloaded'] += file_size
                # Verify the downloaded file is valid
                if is_valid_image(save_path):
                    if is_redownload:
                        stats['redownloaded'] += 1
                        sys.stdout.write('\r' + ' ' * shutil.get_terminal_size().columns + '\r')
                        print(f"[~] [{index}/{total}] Re-downloaded {filename}")
                    else:
                        stats['downloaded'] += 1
                        sys.stdout.write('\r' + ' ' * shutil.get_terminal_size().columns + '\r')
                        print(f"[+] [{index}/{total}] Downloaded {filename}")
                else:
                    stats['corrupt'] += 1
                    failed_files.append((filename, 'corrupt after download'))
                    sys.stdout.write('\r' + ' ' * shutil.get_terminal_size().columns + '\r')
                    print(f"[!] [{index}/{total}] Downloaded {filename} but file appears corrupt")
            else:
                stats['failed'] += 1
                failed_files.append((filename, f'HTTP {r.status_code}'))
                sys.stdout.write('\r' + ' ' * shutil.get_terminal_size().columns + '\r')
                print(f"[!] Failed to download {filename} (Status: {r.status_code})")
        except Exception as e:
            stats['failed'] += 1
            failed_files.append((filename, str(e)))
            sys.stdout.write('\r' + ' ' * shutil.get_terminal_size().columns + '\r')
            print(f"[!] Error downloading {filename}: {e}")
            # Clean up partial downloads
            if os.path.exists(save_path):
                os.remove(save_path)

        print_progress(index, total, stats, start_time)

    # Clear progress bar and print summary
    sys.stdout.write('\r' + ' ' * shutil.get_terminal_size().columns + '\r')
    elapsed = time.time() - start_time

    print()
    print('=' * 50)
    print('  DOWNLOAD SUMMARY')
    print('=' * 50)
    print(f'  Total files:       {total}')
    print(f'  Downloaded:        {stats["downloaded"]}')
    print(f'  Re-downloaded:     {stats["redownloaded"]}')
    print(f'  Skipped (valid):   {stats["skipped"]}')
    print(f'  Failed:            {stats["failed"]}')
    print(f'  Corrupt:           {stats["corrupt"]}')
    print(f'  Total size:        {format_size(stats["bytes_downloaded"])}')
    print(f'  Elapsed time:      {format_time(elapsed)}')
    if elapsed > 0 and stats['bytes_downloaded'] > 0:
        print(f'  Avg speed:         {format_size(stats["bytes_downloaded"] / elapsed)}/s')
    print('=' * 50)

    if failed_files:
        print()
        print(f'  Failed files ({len(failed_files)}):')
        for fname, reason in failed_files:
            print(f'    - {fname}: {reason}')
        print()
        print('  Tip: Re-run the script to retry failed downloads.')
        print()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download bundles from Nationaal Archief")
    parser.add_argument("url", nargs='+', help="The full URL of the archive page (quotes optional)")
    parser.add_argument("--format", choices=['orig', 'small', 'file'], default='orig', 
                        help="orig: Original Formaat, small: Klein Formaat, file: Origineel Bestand")
    
    args = parser.parse_args()

    # Rejoin URL fragments in case the shell split them at '&'
    raw_url = '&'.join(args.url)

    # Warn if the URL appears to have been truncated by the shell
    if '?' in raw_url:
        print("[!] Note: Your URL contains query parameters. If you see errors like")
        print('    "\'...\' is not recognized as an internal or external command",')
        print('    wrap the URL in double quotes: dlna.py "https://..."')

    # Strip query parameters — only the path is needed
    url_clean = raw_url.split('?')[0]

    # Extract archive ID (e.g., 1.04.02) and inventory number (e.g., 1340) from the URL
    match = re.search(r'/archief/([^/]+)/invnr/@?(\d+)', url_clean)
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