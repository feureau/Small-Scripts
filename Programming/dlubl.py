#!/usr/bin/env python3
import argparse
import concurrent.futures
import json
import itertools
import math
import time
import os
import random
import re
import sys
import threading
from urllib.parse import urlparse

from curl_cffi import requests, CurlHttpVersion
from PIL import Image

stop_event = threading.Event()

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/126.0",
]
_ua_cycle = itertools.cycle(USER_AGENTS)

def get_user_agent():
    return next(_ua_cycle)

def timestamp():
    return time.strftime("%H:%M:%S")

_last_request_time = 0.0
_request_lock = threading.Lock()

def rate_limit(min_interval: float = 1.5):
    global _last_request_time
    with _request_lock:
        now = time.time()
        actual_interval = min_interval + random.uniform(0.5, 1.5)
        elapsed = now - _last_request_time
        if elapsed < actual_interval:
            time.sleep(actual_interval - elapsed)
        _last_request_time = time.time()

def sanitize_name(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*\x00-\x1F]+', "_", name).strip(" ._") or "item"

def detect_source(url: str) -> str:
    if "universiteitleiden" in urlparse(url).hostname or "":
        return "leiden"
    return "mdz"

def parse_item_id(url: str, source: str) -> str:
    parts = [p for p in urlparse(url).path.strip("/").split("/") if p]
    if source == "leiden":
        if "item" in parts and parts.index("item") + 1 < len(parts):
            return parts[parts.index("item") + 1]
        for p in reversed(parts):
            if p.isdigit(): return p
        if parts: return parts[-1]
    raise ValueError("Could not parse item id from URL.")

def fetch_leiden_pages(session, url: str, item_id: str):
    base = "https://digitalcollections.universiteitleiden.nl"
    r = session.get(f"{base}/view/item/{item_id}", timeout=30)
    r.raise_for_status()
    m = re.search(r'jQuery\.extend\(Drupal\.settings\s*,\s*', r.text)
    if not m: raise RuntimeError("Could not find Drupal.settings.")
    
    html = r.text
    json_start = html.index('{', m.end())
    depth = 0
    json_end = json_start
    for i in range(json_start, len(html)):
        if html[i] == '{': depth += 1
        elif html[i] == '}':
            depth -= 1
            if depth == 0:
                json_end = i + 1
                break

    settings = json.loads(html[json_start:json_end])
    pages_raw = settings.get("islandoraInternetArchiveBookReader", {}).get("pages", [])
    if not pages_raw: raise RuntimeError("No pages found.")

    iiif_base = settings.get("islandoraInternetArchiveBookReader", {}).get("iiifUri", "/iiif/2")
    if iiif_base.startswith("/"): iiif_base = base + iiif_base

    images = []
    for i, pg in enumerate(pages_raw, start=1):
        # CRITICAL FIX: Do NOT unquote the identifier to preserve WAF-friendly URL encoding (%3A, %7E)
        identifier = pg.get('identifier', '')
        service_id = f"{iiif_base}/{identifier}"
        page_label = (pg.get("label", "") or pg.get("page", f"{i:04d}")).strip("[]")
        images.append({
            "index": i, "label": page_label, 
            "image_url": f"{service_id}/full/full/0/default.jpg", "service_id": service_id
        })
    return images, settings.get("islandoraInternetArchiveBookReader", {}).get("label", f"item_{item_id}")

def fetch_manifest(session: requests.Session, item_id: str) -> dict:
    candidates = [f"https://api.digitale-sammlungen.de/iiif/presentation/v2/{item_id}/manifest"]
    last_err = None
    for url in candidates:
        try:
            r = session.get(url, timeout=30)
            r.raise_for_status()
            data = r.json()
            if isinstance(data, dict): return data
        except Exception as e:
            last_err = e
    raise RuntimeError(f"Unable to fetch manifest/API data for {item_id}: {last_err}")

def get_label_text(label_obj, fallback: str) -> str:
    if isinstance(label_obj, str) and label_obj.strip(): return label_obj.strip()
    if isinstance(label_obj, dict):
        for _, vals in label_obj.items():
            if isinstance(vals, list) and vals and isinstance(vals[0], str): return vals[0]
    return fallback

def extract_image_entries(manifest: dict):
    images = []
    canvases = manifest.get("sequences", [{}])[0].get("canvases", [])
    if not canvases: canvases = manifest.get("items", [])
    for i, canvas in enumerate(canvases, start=1):
        page_label = get_label_text(canvas.get("label"), f"{i:04d}")
        image_url, service_id = None, None
        v2_images = canvas.get("images", [])
        if v2_images:
            service_id = v2_images[0].get("resource", {}).get("service", {}).get("@id") or v2_images[0].get("resource", {}).get("service", {}).get("id")
            image_url = v2_images[0].get("resource", {}).get("@id") or v2_images[0].get("resource", {}).get("id")
        if not image_url:
            annopages = canvas.get("items", [])
            if annopages:
                annos = annopages[0].get("items", [])
                if annos:
                    body = annos[0].get("body", {})
                    image_url = body.get("id")
                    svc = body.get("service")
                    if isinstance(svc, list) and svc: service_id = svc[0].get("@id") or svc[0].get("id")
                    elif isinstance(svc, dict): service_id = svc.get("@id") or svc.get("id")
        if not image_url and service_id:
            image_url = f"{service_id}/full/full/0/default.jpg"
        if image_url:
            images.append({
                "index": i, "label": page_label,
                "image_url": image_url, "service_id": service_id,
            })
    return images

def choose_extension_from_url(url: str, default_ext: str = ".jpg") -> str:
    path = urlparse(url).path.lower()
    for ext in (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".jp2", ".webp"):
        if path.endswith(ext): return ext
    return default_ext

# --- Completely Isolated Request engine ---

def download_file(session, url: str, out_path: str, referer_url: str):
    rate_limit(min_interval=1.5)
    
    browser_type = random.choice(["chrome", "safari", "edge"])
    print(f"      [{timestamp()}] [~] GET {url} (as {browser_type})")
    
    try:
        # Create a fresh session, but pass the active Drupal session cookies
        with requests.Session(impersonate=browser_type, http_version=CurlHttpVersion.V1_1) as temp_session:
            temp_session.cookies.update(session.cookies)
            
            r = temp_session.get(url, timeout=15, allow_redirects=True, headers={
                "Connection": "close",
                "Referer": referer_url,  # CRITICAL: Prove we came from the book viewer
                "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8"
            })
        
            if r.status_code != 200:
                raise RuntimeError(f"HTTP {r.status_code}")

            if b"<html" in r.content[:32].lower() or b"<!doctype" in r.content[:32].lower():
                raise RuntimeError("WAF Block Page detected (Check IP ban / Referer / Cookies)")

            with open(out_path, "wb") as f:
                f.write(r.content)

            if os.path.getsize(out_path) == 0:
                raise RuntimeError("Downloaded empty file")

    except Exception as e:
        raise RuntimeError(str(e))

def fetch_info_json(session, service_id: str, referer_url: str) -> dict:
    rate_limit(min_interval=1.5)
    url = f"{service_id.rstrip('/')}/info.json"
    last_err = None
    for attempt in range(5):
        if stop_event.is_set(): raise RuntimeError("Interrupted")
        try:
            with requests.Session(impersonate="chrome", http_version=CurlHttpVersion.V1_1) as temp_session:
                temp_session.cookies.update(session.cookies)
                r = temp_session.get(url, timeout=20, headers={
                    "Connection": "close",
                    "Referer": referer_url
                })
                r.raise_for_status()
                return r.json()
        except Exception as e:
            last_err = e
            time.sleep((3 ** attempt) + random.uniform(1, 3))
    raise RuntimeError(f"Failed info.json: {last_err}")

def download_page_tiles(session, service_id: str, out_dir: str, referer_url: str, workers: int = 1):
    info = fetch_info_json(session, service_id, referer_url)
    width, height = int(info["width"]), int(info["height"])
    tiles_list = info.get("tiles", [{}])
    tile_w = int(tiles_list[0].get("width", 1024)) if tiles_list else 1024
    tile_h = int(tiles_list[0].get("height", tile_w)) if tiles_list else 1024

    cols, rows = math.ceil(width / tile_w), math.ceil(height / tile_h)
    total_tiles = rows * cols
    print(f"    [{timestamp()}] [*] Canvas {width}x{height}, grid {cols}x{rows} = {total_tiles} tiles")

    done, failed_tiles = 0, []
    done_lock = threading.Lock()
    jobs = []

    for row in range(rows):
        y, h = row * tile_h, min(tile_h, height - row * tile_h)
        for col in range(cols):
            x, w = col * tile_w, min(tile_w, width - col * tile_w)
            tile_name = f"r{row:03d}_c{col:03d}.jpg"
            jobs.append({
                "url": f"{service_id.rstrip('/')}/{x},{y},{w},{h}/full/0/default.jpg",
                "path": os.path.join(out_dir, tile_name),
                "name": tile_name
            })

    def process_tile(job):
        if stop_event.is_set(): return
        nonlocal done
        
        if os.path.exists(job["path"]) and os.path.getsize(job["path"]) > 0:
            with done_lock: done += 1
            return

        last_err = None
        ok = False
        for attempt in range(3):
            if stop_event.is_set(): return
            try:
                download_file(session, job["url"], job["path"], referer_url)
                ok = True
                break
            except Exception as e:
                last_err = e
                if os.path.exists(job["path"]): os.remove(job["path"])
                sleep_time = (4 ** attempt) + random.uniform(1, 4)
                print(f"    [{timestamp()}] [!] {job['name']} retry {attempt+1}/3 (sleep {sleep_time:.0f}s) {last_err}")
                stop_event.wait(sleep_time)

        with done_lock:
            done += 1
            cur = done
        if ok:
            print(f"    [{timestamp()}] [+] OK ({cur}/{total_tiles}): {job['name']}")
        else:
            print(f"    [{timestamp()}] [!] FAILED: {job['name']}")
            failed_tiles.append(job)

    ex = concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers))
    try:
        for f in [ex.submit(process_tile, j) for j in jobs]: f.result()
    except KeyboardInterrupt:
        stop_event.set()
        ex.shutdown(wait=False, cancel_futures=True) if sys.version_info >= (3, 9) else ex.shutdown(wait=False)
        raise
    finally:
        ex.shutdown(wait=False)

    return {
        "width": width, "height": height, "tile_width": tile_w, "tile_height": tile_h,
        "rows": rows, "cols": cols, "tiles": total_tiles, "failed_tiles": len(failed_tiles)
    }

def stitch_tiles_to_image(tile_dir: str, merged_output_path: str, meta: dict, merged_format: str = "png"):
    width, height = int(meta["width"]), int(meta["height"])
    tile_w, tile_h = int(meta["tile_width"]), int(meta["tile_height"])
    rows, cols = int(meta["rows"]), int(meta["cols"])

    canvas = Image.new("RGB", (width, height))
    pasted, missing = 0, []

    for row in range(rows):
        y = row * tile_h
        for col in range(cols):
            x = col * tile_w
            tile_name = f"r{row:03d}_c{col:03d}.jpg"
            tile_path = os.path.join(tile_dir, tile_name)
            if not os.path.exists(tile_path):
                missing.append(tile_name)
                continue
            try:
                with Image.open(tile_path) as tile_im:
                    if tile_im.mode != "RGB": tile_im = tile_im.convert("RGB")
                    canvas.paste(tile_im, (x, y))
                    pasted += 1
            except Exception:
                missing.append(tile_name)

    os.makedirs(os.path.dirname(merged_output_path), exist_ok=True)
    fmt = merged_format.lower()
    if fmt in ("jpg", "jpeg"): canvas.save(merged_output_path, "JPEG", quality=95, subsampling=0)
    elif fmt in ("tif", "tiff"): canvas.save(merged_output_path, "TIFF")
    elif fmt == "webp": canvas.save(merged_output_path, "WEBP", quality=95)
    else: canvas.save(merged_output_path, "PNG")
    return pasted, missing

def main():
    parser = argparse.ArgumentParser(description="Download page images.")
    parser.add_argument("url")
    parser.add_argument("-o", "--out", default=None)
    parser.add_argument("--mode", choices=["tiles", "image"], default=None)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--merged-format", choices=["png", "jpg", "jpeg", "tiff", "tif", "webp"], default="png")
    args = parser.parse_args()

    source = detect_source(args.url)
    item_id = parse_item_id(args.url, source)

    out_dir = args.out or sanitize_name(item_id)
    os.makedirs(out_dir, exist_ok=True)
    tiles_root = os.path.join(out_dir, "Tiles")
    merged_root = os.path.join(out_dir, "Merged")

    # This session will visit the main Leiden viewer to fetch pages and harvest valid cookies!
    with requests.Session(impersonate="chrome") as session:
        print(f"[*] Source: {source} | Item ID: {item_id}")
        if source == "leiden":
            images, doc_label = fetch_leiden_pages(session, args.url, item_id)
            if not args.out:
                out_dir = sanitize_name(doc_label)
                os.makedirs(out_dir, exist_ok=True)
                tiles_root = os.path.join(out_dir, "Tiles")
                merged_root = os.path.join(out_dir, "Merged")
        else:
            images = extract_image_entries(fetch_manifest(session, item_id))

    total = len(images)
    print(f"[*] Found {total} pages.")

    selected_mode = args.mode
    if not selected_mode:
        print("\nSelect download mode:")
        print("  [1] Tiles mode (deep-zoom tile sets, stitched into max-res images)")
        print("  [2] Image mode (download single full images, e.g., /full/full/0/default.jpg)")
        while True:
            choice = input("Enter choice (1 or 2): ").strip()
            if choice == "1":
                selected_mode = "tiles"
                break
            elif choice == "2":
                selected_mode = "image"
                break
            else:
                print("Invalid choice. Please enter 1 or 2.")

    if selected_mode == "tiles":
        os.makedirs(tiles_root, exist_ok=True)
        os.makedirs(merged_root, exist_ok=True)

    start_time_total = time.time()
    for entry in images:
        if stop_event.is_set(): break
        idx, page_label, service_id = entry["index"], entry["label"], entry["service_id"]
        image_url = entry.get("image_url")
        base_name = f"{idx:04d}_{sanitize_name(page_label)}"
        page_start = time.time()

        if selected_mode == "tiles":
            if not service_id: continue
            page_tile_dir = os.path.join(tiles_root, base_name)
            os.makedirs(page_tile_dir, exist_ok=True)
            meta_path = os.path.join(page_tile_dir, "tileset.json")
            
            merged_ext = "jpg" if args.merged_format in ("jpg", "jpeg") else args.merged_format
            merged_page_path = os.path.join(merged_root, f"{base_name}.{merged_ext}")

            if os.path.exists(merged_page_path) and os.path.exists(meta_path):
                try:
                    with open(meta_path, "r", encoding="utf-8") as f:
                        if json.load(f).get("failed_tiles", -1) == 0:
                            print(f"[{timestamp()}] [=] Page {idx} already complete.")
                            continue
                except: pass

            print(f"[{timestamp()}] [>] [{idx}/{total}] tiles: {base_name}")
            try:
                meta = download_page_tiles(session, service_id, page_tile_dir, args.url, workers=args.workers)
                with open(meta_path, "w", encoding="utf-8") as f: json.dump(meta, f, indent=2)
                
                pasted, missing = stitch_tiles_to_image(page_tile_dir, merged_page_path, meta, args.merged_format)
                print(f"[{timestamp()}] [+] page {idx}/{total} done: {pasted}/{meta['tiles']} tiles, elapsed: {time.time() - page_start:.1f}s")
            except Exception as e:
                print(f"[{timestamp()}] [!] Failed page {idx}: {e}")

        elif selected_mode == "image":
            # Formulate the correct encoded full-image URLs
            primary_url = f"{service_id}/full/full/0/default.jpg" if service_id else image_url
            fallback_urls = []
            if service_id: fallback_urls.append(f"{service_id}/full/max/0/default.jpg")
            if image_url and image_url not in (primary_url, fallback_urls):
                fallback_urls.append(image_url)

            ext = choose_extension_from_url(primary_url, default_ext=".jpg")
            filename = f"{base_name}{ext}"
            out_path = os.path.join(out_dir, filename)

            if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
                print(f"[{timestamp()}] [=] {idx}/{total} exists, skip: {filename}")
                continue

            print(f"[{timestamp()}] [>] [{idx}/{total}] image: {filename}")
            tried = [primary_url] + fallback_urls
            for n, candidate in enumerate(tried, start=1):
                try:
                    download_file(session, candidate, out_path, args.url)
                    print(f"[{timestamp()}] [+] page {idx}/{total} done in {time.time() - page_start:.1f}s")
                    break
                except Exception as e:
                    if os.path.exists(out_path):
                        try: os.remove(out_path)
                        except OSError: pass
                    if n == len(tried):
                        print(f"[{timestamp()}] [!] Failed page {idx}: {e}")
                    else:
                        print(f"[{timestamp()}] [!] Retry {idx} with fallback URL ({n}/{len(tried)-1})")

    print(f"[+] Done. Total elapsed: {time.time() - start_time_total:.1f}s")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        stop_event.set()
        print(f"\n[{timestamp()}] [!] Interrupted by user. Forcing exit...")
        os._exit(1)