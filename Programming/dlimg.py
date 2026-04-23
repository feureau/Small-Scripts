#!/usr/bin/env python3
"""
Download main images from a list of URLs.
Handles Wikimedia Commons file/category pages, Alamy, and generic sites.
Includes polite rate‑limiting and 429 retry logic.
"""

import os
import sys
import argparse
import requests
import re
import time
from urllib.parse import urlparse, unquote, urljoin
import pathlib
import io

# Force UTF-8 encoding for stdout and stderr on Windows with line buffering
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:136.0) Gecko/20100101 Firefox/136.0"
}
DOWNLOAD_DELAY = 1.5          # seconds between successful downloads
MAX_RETRIES = 5               # maximum retries for 429 errors

# ----------------------------------------------------------------------
# Helper Functions
# ----------------------------------------------------------------------
def sanitize_filename(name):
    """Remove unsafe characters and fix percent encoding."""
    name = unquote(name)
    return re.sub(r'[\\/*?:"<>|]', "_", name).strip()

def download_file(url, save_path, retry_count=0):
    """Download file with exponential backoff on 429 errors."""
    if os.path.exists(save_path):
        print(f"    - File already exists: {os.path.basename(save_path)}. Skipping.")
        return True
    try:
        resp = requests.get(url, headers=HEADERS, stream=True, timeout=30)
        if resp.status_code == 429:
            retry_after = resp.headers.get("Retry-After")
            if retry_after:
                try:
                    wait = int(retry_after)
                except ValueError:
                    wait = 60
            else:
                wait = min(2 ** retry_count, 60)
            print(f"    Rate limited (429). Waiting {wait} seconds...")
            time.sleep(wait)
            if retry_count < MAX_RETRIES:
                return download_file(url, save_path, retry_count + 1)
            else:
                print(f"    ✗ Max retries exceeded for {url}")
                return False
        resp.raise_for_status()
        with open(save_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"    Download error: {e}")
        return False

def is_direct_image(url):
    """Check if the URL points directly to an image based on its extension."""
    parsed = urlparse(url)
    path = parsed.path.lower()
    return any(path.endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"])

# ----------------------------------------------------------------------
# Wikimedia Commons API Helpers
# ----------------------------------------------------------------------
def get_original_image_url(file_title):
    """
    Fetch the original image URL for a single File: title.
    Returns URL string or None.
    """
    api_url = "https://commons.wikimedia.org/w/api.php"
    params = {
        "action": "query",
        "titles": file_title,
        "prop": "imageinfo",
        "iiprop": "url",
        "format": "json"
    }
    try:
        resp = requests.get(api_url, params=params, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        pages = data.get("query", {}).get("pages", {})
        for page_id, page_data in pages.items():
            if page_id == "-1":
                continue
            imageinfo = page_data.get("imageinfo", [])
            if imageinfo:
                return imageinfo[0]["url"]
    except Exception as e:
        print(f"    API error for {file_title}: {e}")
    return None

def get_original_image_urls_batch(file_titles):
    """
    Fetch original image URLs for multiple File: titles in one API call.
    Returns a dict mapping original title → URL (also includes normalized keys).
    """
    if not file_titles:
        return {}
    api_url = "https://commons.wikimedia.org/w/api.php"
    titles_param = "|".join(file_titles)
    params = {
        "action": "query",
        "titles": titles_param,
        "prop": "imageinfo",
        "iiprop": "url",
        "format": "json"
    }
    try:
        resp = requests.get(api_url, params=params, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        pages = data.get("query", {}).get("pages", {})
        result = {}
        # Build a lookup from normalized title to original title
        normalized_map = {}
        if "normalized" in data.get("query", {}):
            for norm in data["query"]["normalized"]:
                normalized_map[norm["to"]] = norm["from"]
        for page_id, page_data in pages.items():
            if page_id == "-1":
                continue
            title = page_data.get("title")            # normalized title
            imageinfo = page_data.get("imageinfo", [])
            if imageinfo:
                url = imageinfo[0]["url"]
                result[title] = url
                # Also map back to original title if it was normalized
                original = normalized_map.get(title, title)
                if original != title:
                    result[original] = url
        return result
    except Exception as e:
        print(f"    Batch API error: {e}")
        return {}

def get_category_files(category_title):
    """Yield all file titles in a category (handles pagination)."""
    api_url = "https://commons.wikimedia.org/w/api.php"
    params = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": category_title,
        "cmtype": "file",
        "cmlimit": "max",
        "format": "json"
    }
    while True:
        try:
            resp = requests.get(api_url, params=params, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            for member in data.get("query", {}).get("categorymembers", []):
                yield member["title"]
            if "continue" in data:
                params["cmcontinue"] = data["continue"]["cmcontinue"]
            else:
                break
        except Exception as e:
            print(f"    Error fetching category members: {e}")
            break

def process_commons_page(url, output_dir, index_prefix=""):
    """Handle both file and category pages. Returns count of downloaded files."""
    match = re.search(r"/wiki/([^?#]+)", url)
    if not match:
        print(f"    ✗ Could not extract page title from {url}")
        return 0
    page_title = unquote(match.group(1))

    if page_title.startswith("Category:"):
        print(f"    Category detected: {page_title}")
        files = list(get_category_files(page_title))
        print(f"    Found {len(files)} files. Downloading...")
        count = 0

        batch_size = 50
        for i in range(0, len(files), batch_size):
            batch = files[i:i + batch_size]
            url_map = get_original_image_urls_batch(batch)
            for file_title in batch:
                # Use the file_title directly (it's already normalized from categorymembers)
                img_url = url_map.get(file_title)
                if not img_url:
                    # Fallback: try single-file API if batch missed it
                    img_url = get_original_image_url(file_title)
                if not img_url:
                    print(f"      ✗ Skipping {file_title} (no URL found)")
                    continue
                filename = os.path.basename(urlparse(img_url).path)
                if not filename or "." not in filename:
                    filename = f"{file_title.replace('File:', '').replace('/', '_')}_{int(time.time())}.jpg"
                filename = sanitize_filename(filename)
                save_path = os.path.join(output_dir, filename)
                print(f"      Downloading: {filename}")
                if download_file(img_url, save_path):
                    print(f"        ✓ Saved")
                    count += 1
                else:
                    print(f"        ✗ Failed")
                time.sleep(DOWNLOAD_DELAY)
        return count

    elif page_title.startswith("File:"):
        # Use the reliable single-file function
        img_url = get_original_image_url(page_title)
        if not img_url:
            print(f"    ✗ Could not get image URL")
            return 0
        filename = os.path.basename(urlparse(img_url).path)
        if not filename or "." not in filename:
            filename = f"{page_title.replace('File:', '').replace('/', '_')}_{int(time.time())}.jpg"
        filename = sanitize_filename(filename)
        save_path = os.path.join(output_dir, filename)
        print(f"    Downloading: {filename}")
        if download_file(img_url, save_path):
            print(f"    ✓ Saved to {save_path}")
            return 1
        else:
            print(f"    ✗ Download failed")
            return 0
    else:
        print(f"    ✗ Not a File: or Category: page. Skipping.")
        return 0

# ----------------------------------------------------------------------
# Other Domain Handlers
# ----------------------------------------------------------------------
def get_alamy_url(page_url):
    try:
        resp = requests.get(page_url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.content, "html.parser")
        meta = soup.find("meta", property="og:image")
        if meta and meta.get("content"):
            return meta["content"]
    except Exception as e:
        print(f"    Alamy page error: {e}")
    return None

def get_generic_url(page_url):
    try:
        resp = requests.get(page_url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        
        # Suppress XMLParsedAsHTMLWarning if it's likely an SVG or XML
        content_type = resp.headers.get("Content-Type", "").lower()
        from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
        import warnings
        
        if "xml" in content_type or "svg" in content_type:
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
                soup = BeautifulSoup(resp.content, "xml")
        else:
            soup = BeautifulSoup(resp.content, "html.parser")
            
        meta = soup.find("meta", property="og:image")
        if meta and meta.get("content"):
            img_url = urljoin(page_url, meta["content"])
            # Basic check to avoid known tracking pixels in og:image
            if not any(x in img_url.lower() for x in ["facebook.com/tr", "googletagmanager.com"]):
                return img_url
        
        best_img = None
        best_area = 0
        
        # Filter for tracking pixels and tiny icons
        def is_likely_pixel(url):
            return any(x in url.lower() for x in ["pixel", "tracking", "/tr?", "analytics", "sprite"])

        for img in soup.find_all("img"):
            src = img.get("src")
            if not src or is_likely_pixel(src):
                continue
                
            src = urljoin(page_url, src)
            
            width = img.get("width")
            height = img.get("height")
            if width and height:
                try:
                    area = int(width) * int(height)
                    if area > best_area:
                        best_area = area
                        best_img = src
                except ValueError:
                    pass
        
        if best_img:
            return best_img
            
        for img in soup.find_all("img"):
            src = img.get("src")
            if src and any(src.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp"]):
                if is_likely_pixel(src):
                    continue
                return urljoin(page_url, src)
                
    except Exception as e:
        print(f"    Generic page error: {e}")
    return None

# ----------------------------------------------------------------------
# Main Dispatcher
# ----------------------------------------------------------------------
def process_url(url, output_dir, index):
    print(f"[{index}] Processing: {url}")
    parsed = urlparse(url)
    domain = parsed.netloc.lower()

    if is_direct_image(url) or "upload.wikimedia.org" in domain:
        img_url = url
        print(f"    Direct image link detected.")
        filename = os.path.basename(urlparse(img_url).path)
        if not filename or "." not in filename:
            filename = f"image_{index}_{int(time.time())}.jpg"
        filename = sanitize_filename(filename)
        save_path = os.path.join(output_dir, filename)
        if download_file(img_url, save_path):
            print(f"    ✓ Saved to {save_path}")
            return 1
        else:
            # Fallback for Wikimedia: try to find the correct URL via API if direct link failed
            if "upload.wikimedia.org" in domain:
                extracted_filename = unquote(os.path.basename(urlparse(img_url).path))
                print(f"    - Direct link failed. Attempting to recover {extracted_filename} via Commons API...")
                recovered_url = get_original_image_url(f"File:{extracted_filename}")
                if recovered_url and recovered_url != img_url:
                    print(f"    - Recovered new URL: {recovered_url}")
                    if download_file(recovered_url, save_path):
                        print(f"    ✓ Saved to {save_path} (Recovered)")
                        return 1
            print(f"    ✗ Download failed.")
            return 0

    if "commons.wikimedia.org" in domain:
        return process_commons_page(url, output_dir)
    elif "alamy" in domain:
        img_url = get_alamy_url(url)
        if not img_url:
            print(f"    ✗ Could not find main image.")
            return 0
        print(f"    Image URL: {img_url}")
        filename = os.path.basename(urlparse(img_url).path)
        if not filename or "." not in filename:
            filename = f"image_{index}_{int(time.time())}.jpg"
        filename = sanitize_filename(filename)
        save_path = os.path.join(output_dir, filename)
        if download_file(img_url, save_path):
            print(f"    ✓ Saved to {save_path}")
            return 1
        else:
            print(f"    ✗ Download failed.")
            return 0
    else:
        img_url = get_generic_url(url)
        if not img_url:
            print(f"    ✗ Could not find main image.")
            return 0
        print(f"    Image URL: {img_url}")
        filename = os.path.basename(urlparse(img_url).path)
        if not filename or "." not in filename:
            filename = f"image_{index}_{int(time.time())}.jpg"
        filename = sanitize_filename(filename)
        save_path = os.path.join(output_dir, filename)
        if download_file(img_url, save_path):
            print(f"    ✓ Saved to {save_path}")
            return 1
        else:
            print(f"    ✗ Download failed.")
            return 0

# ----------------------------------------------------------------------
# Command Line Interface
# ----------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Download main images from URLs.")
    parser.add_argument("url_file", nargs="?", default=None,
                        help="File with one URL per line. If omitted, read from stdin.")
    parser.add_argument("--output-dir", "-o", default="./downloaded_images",
                        help="Output directory (default: ./downloaded_images).")
    args = parser.parse_args()

    urls = []
    if args.url_file:
        try:
            with open(args.url_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        urls.append(line)
        except FileNotFoundError:
            print(f"Error: File '{args.url_file}' not found.")
            sys.exit(1)
    else:
        print("Reading URLs from stdin. Paste and press Ctrl+D (Linux/Mac) or Ctrl+Z+Enter (Windows).", flush=True)
        try:
            for line in sys.stdin:
                line = line.strip()
                if line and not line.startswith("#"):
                    urls.append(line)
        except KeyboardInterrupt:
            print("\nInterrupted.")
            sys.exit(0)

    if not urls:
        print("No URLs provided.")
        sys.exit(0)

    os.makedirs(args.output_dir, exist_ok=True)

    total_files = 0
    total_urls = len(urls)
    for i, url in enumerate(urls, 1):
        files_downloaded = process_url(url, args.output_dir, i)
        total_files += files_downloaded
        if i < total_urls:
            time.sleep(DOWNLOAD_DELAY)

    print(f"\nDone. Downloaded {total_files} file(s) from {total_urls} URL(s).")

if __name__ == "__main__":
    main()