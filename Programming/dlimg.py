#!/usr/bin/env python3
"""
Download images from a list of URLs.
Handles Wikimedia Commons file/category pages, Alamy, Louvre, Met Museum,
Historic England, WHO, UN Women, and generic sites.

For gallery pages (Louvre, Met, WHO, UN Women, Historic England, generic),
ALL content-area images are downloaded rather than just the first one.

Includes polite rate-limiting and 429 retry logic.
"""

import os
import sys
import argparse
import requests
import re
import time
import warnings
from urllib.parse import urlparse, unquote, urljoin
import io

from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

# Force UTF-8 encoding for stdout/stderr on Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True
    )
    sys.stderr = io.TextIOWrapper(
        sys.stderr.buffer, encoding="utf-8", errors="replace", line_buffering=True
    )

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:136.0) "
        "Gecko/20100101 Firefox/136.0"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}

# Lazy-load attributes checked in order when src is absent/tiny
LAZY_ATTRS = ("data-src", "data-lazy-src", "data-original", "data-srcset", "srcset")

DOWNLOAD_DELAY   = 1.5      # seconds between successful downloads
MAX_RETRIES      = 5        # maximum retries for 429 errors
MIN_GALLERY_AREA = 10_000   # 100x100 px minimum declared area to count as a photo

# Shared session -- reuses TCP connections across all requests
SESSION = requests.Session()
SESSION.headers.update(HEADERS)


# ----------------------------------------------------------------------
# Core helpers
# ----------------------------------------------------------------------

def sanitize_filename(name: str) -> str:
    """Remove unsafe characters and fix percent-encoding."""
    name = unquote(name)
    return re.sub(r'[\\/*?:"<>|]', "_", name).strip()


def download_file(url: str, save_path: str, retry_count: int = 0) -> bool:
    """Download *url* to *save_path* with exponential back-off on HTTP 429."""
    if os.path.exists(save_path):
        print(f"    - Already exists: {os.path.basename(save_path)}. Skipping.")
        return True
    try:
        resp = SESSION.get(url, stream=True, timeout=30)
        if resp.status_code == 429:
            retry_after = resp.headers.get("Retry-After")
            wait = (int(retry_after) if retry_after and retry_after.isdigit()
                    else min(2 ** retry_count, 60))
            print(f"    Rate limited (429). Waiting {wait}s ...")
            time.sleep(wait)
            if retry_count < MAX_RETRIES:
                return download_file(url, save_path, retry_count + 1)
            print(f"    Max retries exceeded for {url}")
            return False
        resp.raise_for_status()
        with open(save_path, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=8192):
                fh.write(chunk)
        return True
    except Exception as exc:
        print(f"    Download error: {exc}")
        return False


def is_direct_image(url: str) -> bool:
    """True when the URL path ends with a recognised image extension."""
    path = urlparse(url).path.lower()
    return any(path.endswith(ext)
               for ext in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"))


def _fetch_soup(page_url: str):
    """GET *page_url* and return a BeautifulSoup. Returns None on error."""
    try:
        resp = SESSION.get(page_url, timeout=30)
        resp.raise_for_status()
        ct = resp.headers.get("Content-Type", "").lower()
        if "xml" in ct or "svg" in ct:
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
                return BeautifulSoup(resp.content, "xml")
        return BeautifulSoup(resp.content, "html.parser")
    except Exception as exc:
        print(f"    Fetch error for {page_url}: {exc}")
        return None


def _best_src(img_tag, base_url: str):
    """
    Return the best image URL from an <img> tag.
    Checks src first, then common lazy-load attributes.
    For srcset-style values, picks the last (usually highest-res) candidate.
    """
    for attr in ("src",) + LAZY_ATTRS:
        raw = img_tag.get(attr, "")
        if not raw:
            continue
        if "srcset" in attr:
            candidates = [s.split()[0] for s in raw.split(",") if s.strip()]
            raw = candidates[-1] if candidates else ""
        raw = raw.strip()
        if raw and not raw.startswith("data:"):
            return urljoin(base_url, raw)
    return None


def _is_tracking_url(url: str) -> bool:
    """True for known tracking pixels and analytics noise."""
    noise = (
        "facebook.com/tr", "googletagmanager.com", "/pixel", "/tracking",
        "/tr?", "analytics", "sprite", "blank.", "1x1.", "placeholder",
    )
    return any(n in url.lower() for n in noise)


def _collect_content_images(soup, page_url: str, content_selectors=(),
                             min_area: int = MIN_GALLERY_AREA) -> list:
    """
    Collect all meaningful image URLs from *soup*, deduplicated.

    Pass 1 -- targeted: scan every <img> inside any element matching
              *content_selectors*. No size filter (these are trusted containers).
    Pass 2 -- whole-page fallback (used only when pass 1 finds nothing):
              include <img> tags whose declared area >= *min_area* OR whose
              URL has a photo-like extension.

    Returns an ordered, deduplicated list of URL strings.
    """
    seen = set()
    results = []

    def _add(url):
        if url and not _is_tracking_url(url) and url not in seen:
            seen.add(url)
            results.append(url)

    # Pass 1: trusted content containers
    for selector in content_selectors:
        for img in soup.select(selector):
            src = _best_src(img, page_url)
            if src:
                _add(src)

    if results:
        return results

    # Pass 2: whole-page scan with size/extension guard
    for img in soup.find_all("img"):
        src = _best_src(img, page_url)
        if not src:
            continue
        try:
            area = int(img.get("width", 0)) * int(img.get("height", 0))
        except (ValueError, TypeError):
            area = 0
        if area >= min_area or is_direct_image(src):
            _add(src)

    return results


# ----------------------------------------------------------------------
# Wikimedia Commons API helpers
# (categories already download full galleries;
#  individual File: pages have exactly one image)
# ----------------------------------------------------------------------

def get_original_image_url(file_title: str):
    """Return the full-resolution URL for a single Commons File: title."""
    api_url = "https://commons.wikimedia.org/w/api.php"
    params = {
        "action": "query", "titles": file_title,
        "prop": "imageinfo", "iiprop": "url", "format": "json",
    }
    try:
        resp = SESSION.get(api_url, params=params, timeout=30)
        resp.raise_for_status()
        for page_id, page in resp.json().get("query", {}).get("pages", {}).items():
            if page_id == "-1":
                continue
            info = page.get("imageinfo", [])
            if info:
                return info[0]["url"]
    except Exception as exc:
        print(f"    API error for {file_title}: {exc}")
    return None


def get_original_image_urls_batch(file_titles: list) -> dict:
    """
    Fetch full-resolution URLs for up to 50 File: titles in one API call.
    Returns {title: url}; handles Commons title normalisation.
    """
    if not file_titles:
        return {}
    api_url = "https://commons.wikimedia.org/w/api.php"
    params = {
        "action": "query", "titles": "|".join(file_titles),
        "prop": "imageinfo", "iiprop": "url", "format": "json",
    }
    try:
        resp  = SESSION.get(api_url, params=params, timeout=30)
        resp.raise_for_status()
        query = resp.json().get("query", {})
        norm_map = {n["to"]: n["from"] for n in query.get("normalized", [])}
        result = {}
        for page_id, page in query.get("pages", {}).items():
            if page_id == "-1":
                continue
            title     = page.get("title", "")
            imageinfo = page.get("imageinfo", [])
            if imageinfo:
                url = imageinfo[0]["url"]
                result[title] = url
                original = norm_map.get(title, title)
                if original != title:
                    result[original] = url
        return result
    except Exception as exc:
        print(f"    Batch API error: {exc}")
        return {}


def get_category_files(category_title: str):
    """Yield every File: title in a Commons category (handles pagination)."""
    api_url = "https://commons.wikimedia.org/w/api.php"
    params  = {
        "action": "query", "list": "categorymembers",
        "cmtitle": category_title, "cmtype": "file",
        "cmlimit": "max", "format": "json",
    }
    while True:
        try:
            resp = SESSION.get(api_url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            for member in data.get("query", {}).get("categorymembers", []):
                yield member["title"]
            if "continue" in data:
                params["cmcontinue"] = data["continue"]["cmcontinue"]
            else:
                break
        except Exception as exc:
            print(f"    Error fetching category members: {exc}")
            break


def process_commons_page(url: str, output_dir: str) -> int:
    """Handle Commons File: and Category: pages. Returns files downloaded."""
    match = re.search(r"/wiki/([^?#]+)", url)
    if not match:
        print(f"    Could not extract page title from {url}")
        return 0
    page_title = unquote(match.group(1))

    if page_title.startswith("Category:"):
        print(f"    Category detected: {page_title}")
        files = list(get_category_files(page_title))
        print(f"    Found {len(files)} files. Downloading ...")
        count = 0
        for i in range(0, len(files), 50):
            batch   = files[i:i + 50]
            url_map = get_original_image_urls_batch(batch)
            for file_title in batch:
                img_url = url_map.get(file_title) or get_original_image_url(file_title)
                if not img_url:
                    print(f"      Skipping {file_title} (no URL found)")
                    continue
                filename  = sanitize_filename(
                    os.path.basename(urlparse(img_url).path)
                    or f"{file_title.replace('File:', '').replace('/', '_')}_{int(time.time())}.jpg"
                )
                save_path = os.path.join(output_dir, filename)
                print(f"      Downloading: {filename}")
                if download_file(img_url, save_path):
                    print("        Saved")
                    count += 1
                else:
                    print("        Failed")
                time.sleep(DOWNLOAD_DELAY)
        return count

    elif page_title.startswith("File:"):
        img_url = get_original_image_url(page_title)
        if not img_url:
            print("    Could not get image URL")
            return 0
        filename  = sanitize_filename(
            os.path.basename(urlparse(img_url).path)
            or f"{page_title.replace('File:', '').replace('/', '_')}_{int(time.time())}.jpg"
        )
        save_path = os.path.join(output_dir, filename)
        print(f"    Downloading: {filename}")
        if download_file(img_url, save_path):
            print(f"    Saved to {save_path}")
            return 1
        print("    Download failed")
        return 0

    else:
        print("    Not a File: or Category: page. Skipping.")
        return 0


# ----------------------------------------------------------------------
# Domain-specific scrapers
# Each returns list[str] -- all gallery images found, deduplicated.
# ----------------------------------------------------------------------

def get_alamy_urls(page_url: str) -> list:
    """Alamy: single watermarked preview via og:image."""
    soup = _fetch_soup(page_url)
    if soup:
        meta = soup.find("meta", property="og:image")
        if meta and meta.get("content"):
            return [meta["content"]]
    return []


def get_louvre_urls(page_url: str) -> list:
    """
    Louvre collections: append .json to the page URL to hit the object API.
    The 'image' array contains every gallery view (face, back, detail, etc.).
    """
    json_url = page_url.rstrip("/")
    if not json_url.endswith(".json"):
        json_url += ".json"
    print(f"    Querying Louvre API: {json_url}")
    try:
        resp = SESSION.get(json_url, timeout=30)
        resp.raise_for_status()
        data   = resp.json()
        images = data.get("image", [])
        urls   = [img["urlImage"] for img in images if img.get("urlImage")]
        print(f"    Found {len(urls)} image(s) in Louvre API response.")
        return urls
    except Exception as exc:
        print(f"    Louvre API error: {exc}")
    return []


def get_met_museum_urls(page_url: str) -> list:
    """
    Met Museum: use the public REST API.
    primaryImage is the hero shot; additionalImages holds the full gallery.
    Falls back to generic og:image scraping if the API returns nothing.
    """
    match = re.search(r"/art/collection/search/(\d+)", page_url)
    if not match:
        print("    Could not extract object ID from Met Museum URL")
        return get_generic_urls(page_url)
    object_id = match.group(1)
    api_url   = (
        f"https://collectionapi.metmuseum.org/public/collection/v1/objects/{object_id}"
    )
    print(f"    Querying Met Museum API: object {object_id}")
    try:
        resp = SESSION.get(api_url, timeout=30)
        resp.raise_for_status()
        data  = resp.json()
        urls  = []
        primary = data.get("primaryImage", "")
        if primary:
            urls.append(primary)
        urls.extend(img for img in data.get("additionalImages", []) if img)
        if urls:
            print(f"    Found {len(urls)} image(s) in Met API response.")
            return urls
        print(
            f"    Object {object_id} has no images "
            f"(isPublicDomain={data.get('isPublicDomain')})"
        )
    except requests.exceptions.HTTPError as exc:
        code = exc.response.status_code if exc.response is not None else "?"
        print(f"    Met Museum API HTTP {code}: {exc}")
    except Exception as exc:
        print(f"    Met Museum API error: {exc}")
    print("    Trying og:image fallback ...")
    return get_generic_urls(page_url)


def get_historic_england_urls(page_url: str) -> list:
    """Historic England photo pages -- targets archive viewer and article body."""
    soup = _fetch_soup(page_url)
    if not soup:
        return []
    return _collect_content_images(
        soup, page_url,
        content_selectors=(
            ".archive-image img",
            ".image-viewer img",
            ".photo-detail img",
            ".main-image img",
            "figure img",
            "article img",
            "#content img",
        ),
    )


def get_who_urls(page_url: str) -> list:
    """
    WHO multimedia pages.
    Images are lazy-loaded; CDN lives at cdn.who.int.
    Targets media-detail and hero containers; falls back to CDN URL sniffing.
    """
    soup = _fetch_soup(page_url)
    if not soup:
        return []

    urls = _collect_content_images(
        soup, page_url,
        content_selectors=(
            ".sf-media img",
            ".multimedia-detail img",
            ".media-gallery img",
            "figure img",
            ".hero img",
            ".page-header img",
            "article img",
            "#content img",
        ),
    )

    # Extra pass: any img whose resolved URL references the WHO CDN
    if not urls:
        seen = set()
        for img in soup.find_all("img"):
            src = _best_src(img, page_url)
            if src and "cdn.who.int" in src and not _is_tracking_url(src) and src not in seen:
                seen.add(src)
                urls.append(src)

    return urls


def get_unwomen_urls(page_url: str) -> list:
    """UN Women news/feature-story pages (Drupal CMS)."""
    soup = _fetch_soup(page_url)
    if not soup:
        return []
    return _collect_content_images(
        soup, page_url,
        content_selectors=(
            ".field--name-field-image img",
            ".article-hero img",
            ".node__content .field--type-image img",
            ".hero-image img",
            ".featured-image img",
            "article .field img",
            "figure img",
            "article img",
        ),
    )


def get_generic_urls(page_url: str) -> list:
    """
    Fallback scraper for unknown sites.
    Prepends og:image as the canonical hero, then collects all content images.
    """
    soup = _fetch_soup(page_url)
    if not soup:
        return []

    og_url = None
    meta = soup.find("meta", property="og:image")
    if meta and meta.get("content"):
        candidate = urljoin(page_url, meta["content"])
        if not _is_tracking_url(candidate):
            og_url = candidate

    gallery = _collect_content_images(
        soup, page_url,
        content_selectors=(
            ".gallery img", ".slideshow img", ".carousel img",
            "figure img", "article img", ".content img",
            "#content img", "main img",
        ),
    )

    seen = set()
    result = []
    for url in ([og_url] if og_url else []) + gallery:
        if url and url not in seen:
            seen.add(url)
            result.append(url)
    return result


# ----------------------------------------------------------------------
# Download helper -- operates on a list of image URLs
# ----------------------------------------------------------------------

def _download_all(img_urls: list, output_dir: str, index: int) -> int:
    """
    Download every URL in *img_urls* into *output_dir*.

    Filenames are derived from the URL path.  When two URLs would produce the
    same filename a numeric suffix is appended to avoid collisions.
    Returns the number of successfully saved files.
    """
    if not img_urls:
        print("    Could not find any images.")
        return 0

    print(f"    Found {len(img_urls)} image(s) to download.")
    count      = 0
    used_names = set()

    for img_url in img_urls:
        print(f"    Image URL: {img_url}")
        base = sanitize_filename(
            os.path.basename(urlparse(img_url).path)
            or f"image_{index}_{int(time.time())}.jpg"
        )
        # Avoid filename collisions within this batch
        filename = base
        stem, _, ext = base.rpartition(".")
        n = 1
        while filename in used_names:
            filename = f"{stem}_{n}.{ext}" if ext else f"{base}_{n}"
            n += 1
        used_names.add(filename)

        save_path = os.path.join(output_dir, filename)
        if download_file(img_url, save_path):
            print(f"    Saved to {save_path}")
            count += 1
        else:
            print("    Download failed.")
        time.sleep(DOWNLOAD_DELAY)

    return count


# ----------------------------------------------------------------------
# Main dispatcher
# ----------------------------------------------------------------------

def process_url(url: str, output_dir: str, index: int) -> int:
    """Route *url* to the appropriate handler and download all found images."""
    print(f"[{index}] Processing: {url}")
    parsed = urlparse(url)
    domain = parsed.netloc.lower()

    # Direct image link or Wikimedia upload CDN
    if is_direct_image(url) or "upload.wikimedia.org" in domain:
        print("    Direct image link detected.")
        filename  = sanitize_filename(
            os.path.basename(urlparse(url).path)
            or f"image_{index}_{int(time.time())}.jpg"
        )
        save_path = os.path.join(output_dir, filename)
        if download_file(url, save_path):
            print(f"    Saved to {save_path}")
            return 1
        # Recovery path: ask Commons API for the canonical URL
        if "upload.wikimedia.org" in domain:
            extracted = unquote(os.path.basename(urlparse(url).path))
            print(f"    Direct link failed. Recovering {extracted} via Commons API ...")
            recovered = get_original_image_url(f"File:{extracted}")
            if recovered and recovered != url:
                print(f"    Recovered URL: {recovered}")
                if download_file(recovered, save_path):
                    print(f"    Saved to {save_path} (recovered)")
                    return 1
        print("    Download failed.")
        return 0

    # Per-domain routing
    if "commons.wikimedia.org" in domain:
        return process_commons_page(url, output_dir)
    elif "alamy" in domain:
        return _download_all(get_alamy_urls(url), output_dir, index)
    elif "collections.louvre.fr" in domain:
        return _download_all(get_louvre_urls(url), output_dir, index)
    elif "metmuseum.org" in domain:
        return _download_all(get_met_museum_urls(url), output_dir, index)
    elif "historicengland.org.uk" in domain:
        return _download_all(get_historic_england_urls(url), output_dir, index)
    elif "who.int" in domain:
        return _download_all(get_who_urls(url), output_dir, index)
    elif "unwomen.org" in domain:
        return _download_all(get_unwomen_urls(url), output_dir, index)
    else:
        return _download_all(get_generic_urls(url), output_dir, index)


# ----------------------------------------------------------------------
# Command-line interface
# ----------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Download images (including full galleries) from URLs."
    )
    parser.add_argument(
        "input_value", nargs="?", default=None,
        help="Single URL or file with one URL per line. Omit to read from stdin.",
    )
    parser.add_argument(
        "--output-dir", "-o", default="./downloaded_images",
        help="Output directory (default: ./downloaded_images).",
    )
    args = parser.parse_args()

    urls = []
    if args.input_value:
        candidate = args.input_value.strip()
        parsed = urlparse(candidate)
        if parsed.scheme in ("http", "https") and parsed.netloc:
            urls = [candidate]
        else:
            try:
                with open(candidate, encoding="utf-8") as fh:
                    urls = [
                        line.strip() for line in fh
                        if line.strip() and not line.startswith("#")
                    ]
            except OSError as exc:
                print(f"Error: could not read input file '{candidate}': {exc}")
                sys.exit(1)
    else:
        print(
            "Reading URLs from stdin. "
            "Paste URLs and press Ctrl+D (Linux/Mac) or Ctrl+Z+Enter (Windows).",
            flush=True,
        )
        try:
            urls = [
                line.strip() for line in sys.stdin
                if line.strip() and not line.startswith("#")
            ]
        except KeyboardInterrupt:
            print("\nInterrupted.")
            sys.exit(0)

    if not urls:
        print("No URLs provided.")
        sys.exit(0)

    os.makedirs(args.output_dir, exist_ok=True)

    total_files = 0
    for i, url in enumerate(urls, 1):
        total_files += process_url(url, args.output_dir, i)
        if i < len(urls):
            time.sleep(DOWNLOAD_DELAY)

    print(f"\nDone. Downloaded {total_files} file(s) from {len(urls)} URL(s).")


if __name__ == "__main__":
    main()
