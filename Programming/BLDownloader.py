# -*- coding: utf-8 -*-
"""
================================================================================
 British Library EAP IIIF Downloader (BLDownloader.py)
================================================================================

Version: 1.1
Author: Gemini
Date: 2025-08-14

--------------------------------------------------------------------------------
PURPOSE
--------------------------------------------------------------------------------
This script is a comprehensive archival tool for downloading digital collections
from the British Library's Endangered Archives Programme (EAP). It provides
flexible options for downloading images at different quality levels and also
extracts and saves the essential metadata that describes the archive.

--------------------------------------------------------------------------------
FEATURES
--------------------------------------------------------------------------------
- Multiple Download Modes: Choose between fast previews, reliable high-resolution
  images, or an experimental fast high-resolution mode.
- Metadata Extraction:
  - By default, it automatically saves a human-readable `metadata.txt` file
    with every download session.
  - Option to download ONLY the full raw JSON manifest (`-m`).
  - Option to download ONLY the human-readable description (`-d`).
- Full Archival Mode (--all):
  - Creates 'Preview' and 'FullRes' subfolders for images.
  - Automatically saves the `metadata.txt` in the main directory.
- Smart Tiling for High Resolution:
  - Dynamically probes the server to determine the maximum reliable tile size,
    preventing visual artifacts like black borders.
- Two Tiling Strategies:
  - Safe Sequential (--full): Downloads tiles one by one. Slow but 100% reliable.
  - Fast Parallel (--fast-full): The default. Downloads tiles simultaneously.
    Much faster but can occasionally fail on this specific server.
- Resumable Downloads: Skips any files that already exist.

--------------------------------------------------------------------------------
REQUIREMENTS & USAGE
--------------------------------------------------------------------------------
- Python 3.6+
- requests: pip install requests
- Pillow:   pip install Pillow

Usage (from the command line):
  python BLDownloader.py [MODE_FLAG] "URL"

Examples:
  # Default: Download full-res images (fast) and create metadata.txt
  python BLDownloader.py "https://eap.bl.uk/archive-file/EAP1268-1-4"

  # Archive All: Create 'Preview' & 'FullRes' folders, plus metadata.txt
  python BLDownloader.py -a "https://eap.bl.uk/archive-file/EAP1268-1-4"

  # Full Res (Safe): Download full-res images reliably (slower)
  python BLDownloader.py -f "https://eap.bl.uk/archive-file/EAP1268-1-4"

  # Metadata Only: Save the full raw JSON manifest to 'manifest.json'
  python BLDownloader.py -m "https://eap.bl.uk/archive-file/EAP1268-1-4"

  # Description Only: Save the human-readable summary to 'metadata.txt'
  python BLDownloader.py -d "https://eap.bl.uk/archive-file/EAP1268-1-4"
"""

import requests
import sys
import os
import json
import re
import time
import argparse
from math import ceil
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None 
except ImportError:
    print("Error: Pillow library not found. Please install it using: pip install Pillow")
    sys.exit(1)

def determine_max_tile_size(session, image_service_id):
    """Probes the IIIF server to find the maximum dimension it will return."""
    probe_url = f"{image_service_id}/0,0,2000,2000/full/0/default.jpg"
    try:
        response = session.get(probe_url, stream=True, timeout=30)
        response.raise_for_status()
        with Image.open(response.raw) as img:
            return min(img.size[0], img.size[1], 2000)
    except Exception:
        return 1024

def download_tile(session, tile_info):
    """Downloads a single tile for the parallel executor."""
    url, left, top = tile_info['url'], tile_info['left'], tile_info['top']
    try:
        tile_response = session.get(url, stream=True, timeout=45)
        tile_response.raise_for_status()
        return left, top, Image.open(tile_response.raw)
    except requests.exceptions.RequestException:
        return left, top, None

def download_full_resolution(session, image_service_id, filepath, use_fast_mode):
    """Downloads and stitches all tiles for a single image."""
    mode_string = "FAST-PARALLEL" if use_fast_mode else "SAFE-SEQUENTIAL"
    print(f"Requesting FULL resolution ({mode_string}) for '{os.path.basename(filepath)}'")
    
    try:
        info_response = session.get(f"{image_service_id}/info.json", timeout=20)
        info_response.raise_for_status()
        info_data = info_response.json()
    except Exception as e:
        print(f"  -> Error fetching info.json: {e}. Skipping image.")
        return False

    full_width, full_height = info_data.get('width'), info_data.get('height')
    tile_size = determine_max_tile_size(session, image_service_id)
    print(f"  -> Assembling {full_width}x{full_height} from {tile_size}x{tile_size} tiles...")
    stitched_image = Image.new('RGB', (full_width, full_height))
    
    tasks = [{'url': f"{image_service_id}/{x},{y},{min(tile_size, full_width-x)},{min(tile_size, full_height-y)}/full/0/default.jpg", 'left': x, 'top': y}
             for y in range(0, full_height, tile_size)
             for x in range(0, full_width, tile_size)]

    all_successful = True
    if use_fast_mode:
        with ThreadPoolExecutor(max_workers=len(tasks)) as executor:
            futures = {executor.submit(download_tile, session, task): task for task in tasks}
            for future in as_completed(futures):
                left, top, tile_image = future.result()
                if tile_image:
                    stitched_image.paste(tile_image, (left, top))
                else:
                    all_successful = False
    else: # Safe sequential mode
        for i, task in enumerate(tasks):
            print(f"    -> Tile {i + 1}/{len(tasks)}...", end='', flush=True)
            left, top, tile_image = download_tile(session, task)
            if tile_image:
                stitched_image.paste(tile_image, (left, top))
                print(" Done.")
            else:
                print(" FAILED.")
                all_successful = False
                break
            time.sleep(0.1)
            
    if all_successful:
        try:
            stitched_image.save(filepath, "jpeg", quality=95, subsampling=0)
            print(f"  -> Successfully saved '{os.path.basename(filepath)}'")
            return True
        except Exception as e:
            print(f"  -> Error saving stitched image: {e}")
            return False
    else:
        print("  -> Aborted saving due to failed tile downloads.")
        return False

def download_preview_resolution(session, image_service_id, filepath):
    """Downloads the smaller, server-provided preview image."""
    print(f"Requesting PREVIEW for '{os.path.basename(filepath)}'...")
    image_url = f"{image_service_id}/full/full/0/default.jpg"
    try:
        response = session.get(image_url, stream=True, timeout=60)
        response.raise_for_status()
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        with Image.open(filepath) as img:
            print(f"  -> Successfully downloaded preview. Dimensions: {img.size[0]}x{img.size[1]}")
        return True
    except Exception as e:
        print(f"  -> Error downloading preview image: {e}")
        return False

def save_descriptive_metadata(manifest_data, filepath):
    """Extracts human-readable metadata and saves it to a text file."""
    print(f"Saving descriptive metadata to '{os.path.basename(filepath)}'...")
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"Title: {manifest_data.get('label', 'N/A')}\n")
            f.write(f"IIIF Manifest: {manifest_data.get('@id', 'N/A')}\n")
            f.write("="*80 + "\n\n")

            f.write("Description:\n")
            f.write(f"{manifest_data.get('description', 'N/A')}\n\n")
            f.write("="*80 + "\n\n")

            f.write("Attribution and Rights:\n")
            f.write(f"  Attribution: {manifest_data.get('attribution', 'N/A')}\n")
            f.write(f"  License: {manifest_data.get('license', 'N/A')}\n\n")
            f.write("="*80 + "\n\n")

            f.write("Metadata Fields:\n")
            for item in manifest_data.get('metadata', []):
                # Clean up HTML tags for readability
                value = re.sub('<[^<]+?>', '', item.get('value', 'N/A'))
                f.write(f"  - {item.get('label', 'N/A')}: {value}\n")
        return True
    except Exception as e:
        print(f"  -> Error saving metadata file: {e}")
        return False

def run_downloader(url, mode):
    """Main function to orchestrate the download process."""
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36'})

    manifest_url = f"{url.rstrip('/')}/manifest"
    print(f"Fetching manifest: {manifest_url}")
    try:
        manifest_response = session.get(manifest_url, timeout=20)
        manifest_response.raise_for_status()
        manifest_data = manifest_response.json()
    except Exception as e:
        print(f"FATAL: Could not fetch or parse the main manifest: {e}. Exiting.")
        return

    # Handle metadata-only modes first
    if mode == 'metadata':
        filepath = os.path.join(os.getcwd(), 'manifest.json')
        print(f"Saving full JSON manifest to '{os.path.basename(filepath)}'...")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(manifest_data, f, indent=2, ensure_ascii=False)
        print("Done.")
        return

    if mode == 'description':
        filepath = os.path.join(os.getcwd(), 'metadata.txt')
        save_descriptive_metadata(manifest_data, filepath)
        print("Done.")
        return

    # --- For all image-downloading modes, first save the metadata text file ---
    metadata_path = os.path.join(os.getcwd(), 'metadata.txt')
    if mode == 'all':
        # For 'all' mode, place metadata alongside the subfolders
        os.makedirs("Preview", exist_ok=True)
        os.makedirs("FullRes", exist_ok=True)
    save_descriptive_metadata(manifest_data, metadata_path)

    canvases = manifest_data.get('sequences', [{}])[0].get('canvases', []) or manifest_data.get('items', [])
    if not canvases:
        print("No image data found in manifest. Metadata has been saved.")
        return

    total_images = len(canvases)
    eap_identifier = os.path.basename(url.rstrip('/'))
    print(f"\nFound {total_images} images to process. Mode: '{mode.upper()}'")

    for i, canvas in enumerate(canvases):
        print("\n" + "="*60)
        print(f"Processing Image {i + 1} of {total_images}")

        image_service_id = canvas.get('images', [{}])[0].get('resource', {}).get('service', {}).get('@id')
        if not image_service_id:
            print("Warning: Could not find image service ID. Skipping.")
            continue

        page_label = canvas.get('label', str(i + 1))
        sanitized_label = re.sub(r'[^\w\-_\.]', '_', page_label)
        filename = f"{eap_identifier}_{sanitized_label}.jpg"
        
        # Determine paths based on mode
        if mode == 'all':
            preview_path = os.path.join("Preview", filename)
            full_path = os.path.join("FullRes", filename)
            
            if not os.path.exists(preview_path):
                download_preview_resolution(session, image_service_id, preview_path)
            else:
                print(f"Preview '{filename}' already exists. Skipping.")
            
            if not os.path.exists(full_path):
                download_full_resolution(session, image_service_id, full_path, use_fast_mode=True)
            else:
                print(f"FullRes '{filename}' already exists. Skipping.")
        else:
            # For single-mode downloads, save to current directory
            filepath = os.path.join(os.getcwd(), filename)
            if os.path.exists(filepath):
                print(f"'{filename}' already exists. Skipping.")
                continue
            
            if mode == 'preview':
                download_preview_resolution(session, image_service_id, filepath)
            elif mode == 'full' or mode == 'fast-full':
                download_full_resolution(session, image_service_id, filepath, use_fast_mode=(mode == 'fast-full'))
                
    print("\n" + "="*60 + "\nDownload process finished.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Download images and metadata from the British Library EAP archives.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Examples:
  # Default: Download full-res (fast) and create metadata.txt
  python BLDownloader.py "https://eap.bl.uk/archive-file/EAP1268-1-4"

  # Archive All: Creates 'Preview/' & 'FullRes/' folders, plus metadata.txt
  python BLDownloader.py -a "https://eap.bl.uk/archive-file/EAP1268-1-4"

  # Full Res (Safe): Downloads full-res reliably (slower)
  python BLDownloader.py -f "https://eap.bl.uk/archive-file/EAP1268-1-4"

  # Previews Only: Download fast, low-res preview images
  python BLDownloader.py -p "https://eap.bl.uk/archive-file/EAP1268-1-4"

  # Metadata Only: Save the full raw JSON manifest to 'manifest.json'
  python BLDownloader.py -m "https://eap.bl.uk/archive-file/EAP1268-1-4"

  # Description Only: Save the human-readable summary to 'metadata.txt'
  python BLDownloader.py -d "https://eap.bl.uk/archive-file/EAP1268-1-4"
"""
    )
    parser.add_argument("url", help="The EAP archive-file URL to download from.")
    
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("-p", "--preview", action="store_true", help="Download low-resolution previews only.")
    mode_group.add_argument("-f", "--full", action="store_true", help="Download full-res using safe sequential tiling.")
    mode_group.add_argument("--fast-full", action="store_true", help="Download full-res using fast parallel tiling (default).")
    mode_group.add_argument("-a", "--all", action="store_true", help="Archive both previews and fast full-res into subfolders.")
    mode_group.add_argument("-m", "--metadata", action="store_true", help="Download only the full raw JSON manifest.")
    mode_group.add_argument("-d", "--description", action="store_true", help="Download only the descriptive metadata text file.")

    args = parser.parse_args()
    
    if args.preview:
        download_mode = 'preview'
    elif args.full:
        download_mode = 'full'
    elif args.all:
        download_mode = 'all'
    elif args.metadata:
        download_mode = 'metadata'
    elif args.description:
        download_mode = 'description'
    else: # Default behavior if no specific mode flag is given
        download_mode = 'fast-full'
    
    try:
        run_downloader(args.url, download_mode)
    except KeyboardInterrupt:
        print("\nDownload interrupted by user. Exiting.")
        sys.exit(0)