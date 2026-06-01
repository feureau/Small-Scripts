#!/usr/bin/env python3
import argparse
import concurrent.futures
import json
import math
import os
import re
import sys
import threading
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from PIL import Image


def sanitize_name(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*\x00-\x1F]+', "_", name).strip(" ._") or "item"


def parse_item_id(url: str) -> str:
    path = urlparse(url).path.strip("/")
    parts = [p for p in path.split("/") if p]

    if "view" in parts:
        idx = parts.index("view")
        if idx + 1 < len(parts):
            return parts[idx + 1]

    if "manifest" in parts:
        idx = parts.index("manifest")
        if idx - 1 >= 0:
            return parts[idx - 1]

    # Look for common MDZ ID patterns
    for part in parts:
        if part.startswith("bsb") or part.startswith("sbb") or "00" in part:
            return part

    if parts:
        return parts[-1]

    raise ValueError("Could not parse Digitale Sammlungen item id from URL.")


def fetch_manifest(session: requests.Session, item_id: str) -> dict:
    candidates = [
        f"https://api.digitale-sammlungen.de/iiif/presentation/v2/{item_id}/manifest",
    ]

    last_err = None
    for url in candidates:
        try:
            r = session.get(url, timeout=30)
            r.raise_for_status()
            data = r.json()
            if isinstance(data, dict):
                return data
        except Exception as e:
            last_err = e

    raise RuntimeError(f"Unable to fetch manifest/API data for {item_id}: {last_err}")


def get_label_text(label_obj, fallback: str) -> str:
    if isinstance(label_obj, str) and label_obj.strip():
        return label_obj.strip()
    if isinstance(label_obj, dict):
        for _, vals in label_obj.items():
            if isinstance(vals, list) and vals:
                if isinstance(vals[0], str):
                    return vals[0]
    return fallback


def extract_image_entries(manifest: dict):
    images = []

    canvases = manifest.get("sequences", [{}])[0].get("canvases", [])
    if not canvases:
        canvases = manifest.get("items", [])

    for i, canvas in enumerate(canvases, start=1):
        page_label = get_label_text(canvas.get("label"), f"{i:04d}")
        image_url = None
        service_id = None

        # IIIF Presentation v2
        v2_images = canvas.get("images", [])
        if v2_images:
            service_id = (
                v2_images[0]
                .get("resource", {})
                .get("service", {})
                .get("@id")
                or v2_images[0]
                .get("resource", {})
                .get("service", {})
                .get("id")
            )
            image_url = (
                v2_images[0]
                .get("resource", {})
                .get("@id")
                or v2_images[0]
                .get("resource", {})
                .get("id")
            )

        # IIIF Presentation v3
        if not image_url:
            annopages = canvas.get("items", [])
            if annopages:
                annos = annopages[0].get("items", [])
                if annos:
                    body = annos[0].get("body", {})
                    image_url = body.get("id")
                    svc = body.get("service")
                    if isinstance(svc, list) and svc:
                        service_id = svc[0].get("@id") or svc[0].get("id")
                    elif isinstance(svc, dict):
                        service_id = svc.get("@id") or svc.get("id")

        # If only image service exists, construct full image URL
        if not image_url:
            if service_id:
                image_url = f"{service_id}/full/full/0/default.jpg"

        if image_url:
            images.append(
                {
                    "index": i,
                    "label": page_label,
                    "image_url": image_url,
                    "service_id": service_id,
                }
            )

    return images


def choose_extension_from_url(url: str, default_ext: str = ".jpg") -> str:
    path = urlparse(url).path.lower()
    for ext in (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".jp2", ".webp"):
        if path.endswith(ext):
            return ext
    return default_ext


def download_file(session: requests.Session, url: str, out_path: str):
    first_chunk = b""
    with session.get(url, stream=True, timeout=90, allow_redirects=True) as r:
        r.raise_for_status()
        ctype = (r.headers.get("Content-Type") or "").lower()
        if "text/html" in ctype or "application/json" in ctype or "xml" in ctype:
            raise RuntimeError(f"Non-image response for {url} (Content-Type: {ctype})")
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 128):
                if chunk:
                    if not first_chunk:
                        first_chunk = chunk[:32]
                    f.write(chunk)
    if os.path.getsize(out_path) == 0:
        raise RuntimeError("Downloaded empty file")

    # If content-type is generic, reject clear HTML/XML payloads by signature.
    sniff = first_chunk.lstrip().lower()
    if sniff.startswith(b"<html") or sniff.startswith(b"<!doctype html") or sniff.startswith(b"<?xml"):
        raise RuntimeError(f"Non-image payload detected for {url}")


def fetch_info_json(session: requests.Session, service_id: str) -> dict:
    info_url = f"{service_id.rstrip('/')}/info.json"
    r = session.get(info_url, timeout=45)
    r.raise_for_status()
    return r.json()


def get_tile_size(info: dict):
    tiles = info.get("tiles", [])
    if tiles:
        tile_w = int(tiles[0].get("width", 1024))
        tile_h = int(tiles[0].get("height", tile_w))
        return tile_w, tile_h
    # Fallback when server does not advertise tile geometry.
    return 1024, 1024


def get_preferred_formats(info: dict):
    formats = []
    for key in ("preferredFormats", "formats"):
        vals = info.get(key, [])
        if isinstance(vals, list):
            for v in vals:
                if isinstance(v, str):
                    vv = v.lower().strip(".")
                    if vv in ("jpg", "jpeg", "png", "jp2", "webp", "tif", "tiff"):
                        formats.append("jpg" if vv == "jpeg" else vv)
    if "jpg" not in formats:
        formats.insert(0, "jpg")
    seen = set()
    uniq = []
    for f in formats:
        if f not in seen:
            uniq.append(f)
            seen.add(f)
    return uniq


def tile_url_candidates(service_id: str, x: int, y: int, w: int, h: int, formats):
    region = f"{x},{y},{w},{h}"
    size_variants = [
        "full",
        "max",
        f"{w},",
        f"{w},{h}",
    ]
    urls = []
    for size in size_variants:
        for fmt in formats:
            urls.append(f"{service_id.rstrip('/')}/{region}/{size}/0/default.{fmt}")
    return urls


def download_page_tiles(session: requests.Session, service_id: str, out_dir: str, workers: int = 8):
    info = fetch_info_json(session, service_id)
    width = int(info["width"])
    height = int(info["height"])
    tile_w, tile_h = get_tile_size(info)
    formats = get_preferred_formats(info)

    cols = math.ceil(width / tile_w)
    rows = math.ceil(height / tile_h)
    total_tiles = rows * cols
    done = 0
    failed_tiles = []
    done_lock = threading.Lock()

    jobs = []
    tile_no = 0
    for row in range(rows):
        y = row * tile_h
        h = min(tile_h, height - y)
        for col in range(cols):
            x = col * tile_w
            w = min(tile_w, width - x)
            tile_no += 1
            tile_name = f"r{row:03d}_c{col:03d}.jpg"
            tile_path = os.path.join(out_dir, tile_name)
            jobs.append(
                {
                    "tile_no": tile_no,
                    "row": row,
                    "col": col,
                    "x": x,
                    "y": y,
                    "w": w,
                    "h": h,
                    "tile_name": tile_name,
                    "tile_path": tile_path,
                }
            )

    def process_tile(job):
        nonlocal done
        tile_no_local = job["tile_no"]
        tile_name_local = job["tile_name"]
        tile_path_local = job["tile_path"]

        if os.path.exists(tile_path_local) and os.path.getsize(tile_path_local) > 0:
            with done_lock:
                done += 1
            print(f"    [=] tile {tile_no_local}/{total_tiles} exists: {tile_name_local}")
            return

        print(f"    [>] tile {tile_no_local}/{total_tiles} download: {tile_name_local}")
        last_err = None
        ok = False
        for tile_url in tile_url_candidates(
            service_id, job["x"], job["y"], job["w"], job["h"], formats
        ):
            try:
                download_file(session, tile_url, tile_path_local)
                ok = True
                break
            except Exception as e:
                last_err = e
                if os.path.exists(tile_path_local):
                    try:
                        os.remove(tile_path_local)
                    except OSError:
                        pass

        if not ok:
            print(f"    [!] tile {tile_no_local}/{total_tiles} failed: {tile_name_local}")
            failed_tiles.append(
                {
                    "row": job["row"],
                    "col": job["col"],
                    "x": job["x"],
                    "y": job["y"],
                    "w": job["w"],
                    "h": job["h"],
                    "error": str(last_err),
                }
            )
        with done_lock:
            done += 1

    max_workers = max(1, workers)
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = [ex.submit(process_tile, job) for job in jobs]
        for f in concurrent.futures.as_completed(futures):
            f.result()

    return {
        "width": width,
        "height": height,
        "tile_width": tile_w,
        "tile_height": tile_h,
        "rows": rows,
        "cols": cols,
        "tiles": total_tiles,
        "downloaded_or_existing_tiles": done,
        "failed_tiles": len(failed_tiles),
        "failed_tiles_detail": failed_tiles,
    }


def stitch_tiles_to_image(tile_dir: str, merged_output_path: str, meta: dict, merged_format: str = "png"):
    width = int(meta["width"])
    height = int(meta["height"])
    tile_w = int(meta["tile_width"])
    tile_h = int(meta["tile_height"])
    rows = int(meta["rows"])
    cols = int(meta["cols"])

    canvas = Image.new("RGB", (width, height))
    pasted = 0
    missing = []

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
                    if tile_im.mode != "RGB":
                        tile_im = tile_im.convert("RGB")
                    canvas.paste(tile_im, (x, y))
                    pasted += 1
            except Exception:
                missing.append(tile_name)

    os.makedirs(os.path.dirname(merged_output_path), exist_ok=True)
    fmt = merged_format.lower()
    if fmt in ("jpg", "jpeg"):
        canvas.save(merged_output_path, "JPEG", quality=95, subsampling=0)
    elif fmt in ("tif", "tiff"):
        canvas.save(merged_output_path, "TIFF")
    elif fmt == "webp":
        canvas.save(merged_output_path, "WEBP", quality=95)
    else:
        canvas.save(merged_output_path, "PNG")
    return pasted, missing


def main():
    parser = argparse.ArgumentParser(
        description="Download all page images from a Digitale Sammlungen (MDZ) item URL."
    )
    parser.add_argument("url", help="Example: https://www.digitale-sammlungen.de/en/view/bsb00045957")
    parser.add_argument(
        "-o",
        "--out",
        default=None,
        help="Output folder (default: <item_id>)",
    )
    parser.add_argument(
        "--mode",
        choices=["tiles", "image"],
        default=None,
        help="`tiles` = download max-res IIIF tile set, `image` = single full image per page. If not specified, will prompt interactively.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=8,
        help="Parallel tile download workers per page in `tiles` mode (default: 8).",
    )
    parser.add_argument(
        "--merged-format",
        choices=["png", "jpg", "jpeg", "tiff", "tif", "webp"],
        default="png",
        help="Merged page image format in `tiles` mode (default: png).",
    )
    args = parser.parse_args()

    try:
        item_id = parse_item_id(args.url)
    except ValueError as e:
        print(f"[!] {e}")
        sys.exit(1)

    out_dir = args.out or sanitize_name(item_id)
    os.makedirs(out_dir, exist_ok=True)
    tiles_root = os.path.join(out_dir, "Tiles")
    merged_root = os.path.join(out_dir, "Merged")

    session = requests.Session()
    retry = Retry(
        total=5,
        connect=5,
        read=5,
        backoff_factor=1.0,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=20, pool_maxsize=20)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Referer": "https://www.digitale-sammlungen.de/",
            "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        }
    )

    print(f"[*] Item ID: {item_id}")
    print("[*] Fetching manifest...")
    manifest = fetch_manifest(session, item_id)

    manifest_path = os.path.join(out_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"[*] Saved manifest: {manifest_path}")

    images = extract_image_entries(manifest)
    if not images:
        print("[!] No page images found in manifest.")
        sys.exit(1)

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

    for entry in images:
        idx = entry["index"]
        page_label = entry["label"]
        image_url = entry["image_url"]
        service_id = entry["service_id"]

        safe_label = sanitize_name(page_label)
        base_name = f"{idx:04d}_{safe_label}"

        if selected_mode == "tiles":
            if not service_id:
                print(f"[!] {idx}/{total} no IIIF service id, skip")
                continue
            page_tile_dir = os.path.join(tiles_root, base_name)
            os.makedirs(page_tile_dir, exist_ok=True)
            meta_path = os.path.join(page_tile_dir, "tileset.json")
            print(f"[>] {idx}/{total} tiles: {base_name}")
            try:
                meta = download_page_tiles(session, service_id, page_tile_dir, workers=args.workers)
                with open(meta_path, "w", encoding="utf-8") as f:
                    json.dump(meta, f, ensure_ascii=False, indent=2)
                merged_ext = "jpg" if args.merged_format in ("jpg", "jpeg") else args.merged_format
                merged_page_path = os.path.join(merged_root, f"{base_name}.{merged_ext}")
                print(f"    [*] merging tiles -> {os.path.basename(merged_page_path)}")
                pasted, missing = stitch_tiles_to_image(
                    page_tile_dir,
                    merged_page_path,
                    meta,
                    merged_format=args.merged_format,
                )
                print(
                    f"    [+] merged tiles pasted: {pasted}/{meta['tiles']}, "
                    f"missing: {len(missing)}"
                )
            except Exception as e:
                print(f"[!] Failed page {idx}: {e}")
            continue

        # image mode
        primary_url = f"{service_id}/full/full/0/default.jpg" if service_id else image_url
        fallback_urls = []
        if image_url and image_url != primary_url:
            fallback_urls.append(image_url)
        if service_id:
            fallback_urls.append(f"{service_id}/full/max/0/default.jpg")

        ext = choose_extension_from_url(primary_url, default_ext=".jpg")
        filename = f"{base_name}{ext}"
        out_path = os.path.join(out_dir, filename)
        if os.path.exists(out_path):
            print(f"[=] {idx}/{total} exists, skip: {filename}")
            continue
        print(f"[>] {idx}/{total} downloading: {filename}")
        tried = [primary_url] + fallback_urls
        for n, candidate in enumerate(tried, start=1):
            try:
                download_file(session, candidate, out_path)
                break
            except Exception as e:
                if os.path.exists(out_path):
                    try:
                        os.remove(out_path)
                    except OSError:
                        pass
                if n == len(tried):
                    print(f"[!] Failed page {idx}: {e}")
                else:
                    print(f"[!] Retry {idx} with fallback URL ({n}/{len(tried)-1})")

    print("[+] Done.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[!] Interrupted by user.")
