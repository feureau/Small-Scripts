#!/usr/bin/env python3
"""
na-dl.py  --  Download high-resolution TIF files from Nationaal Archief
========================================================================
Usage (run from ANY working folder):
    python "C:\\Tools\\na-dl.py" [--debug] "<viewer URL>"

Example:
    python "C:\\Tools\\na-dl.py" "https://www.nationaalarchief.nl/onderzoeken/archief/1.04.02/invnr/2864/file/NL-HaNA_1.04.02_2864_0011?eadID=1.04.02&unitID=2864&query="

Output is saved to a sub-folder of the directory you run the command from.

!! WINDOWS CMD: always wrap the URL in double quotes -- & splits the command !!
    WRONG:  na-dl.py https://...?eadID=1.04.02&unitID=2864
    RIGHT:  na-dl.py "https://...?eadID=1.04.02&unitID=2864"

Options:
    --debug         Verbose output at every step
    --mets <URL>    Skip discovery, use this METS URL directly (fallback)
"""

import sys, re, os, time, json
import requests
import xml.etree.ElementTree as ET
from urllib.parse import urlparse, parse_qs

# ── Config ────────────────────────────────────────────────────────────────────
DELAY_SEC  = 0.5
CHUNK_SIZE = 64 * 1024
TIMEOUT    = 120
HEADERS    = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "nl,en;q=0.9",
}

FILE_BASE = "https://service.archief.nl/gaf/api/file/v1"
OAI_BASE  = "https://service.archief.nl/gaf/oai/!open_oai.OAIHandler"

DEBUG = False

def dbg(msg):
    if DEBUG:
        print(f"  [DEBUG] {msg}")

# ── UUID regex patterns ───────────────────────────────────────────────────────
UUID_PAT  = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
ORIG_RE   = re.compile(rf'file/v1/original/({UUID_PAT})', re.I)
DEFLT_RE  = re.compile(rf'file/v1/default/({UUID_PAT})',  re.I)
METS_RE   = re.compile(rf'api/mets/v\d+/({UUID_PAT})',    re.I)
# Scan-name pattern: NL-HaNA_1.04.02_2864_0011
SCAN_RE   = re.compile(r'NL-HaNA_([\d.]+)_(\w+)_(\d{4})', re.I)

# ── URL parsing ───────────────────────────────────────────────────────────────

def parse_viewer_url(raw: str):
    """Return (ead_id, unit_id, scan_name_or_None)."""
    parsed  = urlparse(raw)
    params  = parse_qs(parsed.query)
    ead_id  = params.get("eadID",  [None])[0]
    unit_id = params.get("unitID", [None])[0]
    parts   = parsed.path.strip("/").split("/")

    if not ead_id:
        try: ead_id = parts[parts.index("archief") + 1]
        except (ValueError, IndexError): pass
    if not unit_id:
        try: unit_id = parts[parts.index("invnr") + 1]
        except (ValueError, IndexError): pass

    scan_name = None
    try:
        fi = parts.index("file")
        cand = parts[fi + 1] if fi + 1 < len(parts) else ""
        if SCAN_RE.match(cand.split("?")[0]):
            scan_name = cand.split("?")[0]
    except ValueError:
        pass

    if not ead_id or not unit_id:
        raise ValueError(
            f"Cannot extract eadID/unitID from: {raw}\n\n"
            "HINT: On Windows CMD the & splits the command.\n"
            'Wrap the URL in double quotes:\n'
            '    na-dl.py "https://...?eadID=1.04.02&unitID=2864&query="'
        )
    return ead_id, unit_id, scan_name

# ── Page fetcher ──────────────────────────────────────────────────────────────

def fetch_page(url: str, label: str) -> str | None:
    dbg(f"GET {url}")
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        dbg(f"  -> {r.status_code}, {len(r.text):,} chars")
        return r.text
    except Exception as e:
        dbg(f"  -> FAILED: {e}")
        return None

# ── Method A: extract file UUIDs directly from HTML ──────────────────────────

def uuids_from_html(html: str, label: str) -> tuple[list, list]:
    """
    Return (original_uuids, default_uuids) found in the HTML, in order,
    deduplicated while preserving first-occurrence order.
    """
    def ordered_unique(matches):
        seen, out = set(), []
        for m in matches:
            if m not in seen:
                seen.add(m)
                out.append(m)
        return out

    orig  = ordered_unique(ORIG_RE.findall(html))
    deflt = ordered_unique(DEFLT_RE.findall(html))
    dbg(f"  [{label}] /original/ UUIDs: {len(orig)}, /default/ UUIDs: {len(deflt)}")
    if DEBUG and orig:
        dbg(f"  First orig  UUID: {orig[0]}")
        dbg(f"  Last  orig  UUID: {orig[-1]}")
    return orig, deflt


def _find_deep_item_url(html: str, ead_id: str, unit_id: str) -> str | None:
    """
    The invnr page is a tree navigator. The actual scan viewer lives at a
    deep ~-separated hierarchical URL like:
      /onderzoeken/archief/1.04.02/invnr/%40Deel%20I~...~2864
    Find that link in the page HTML.
    """
    pattern = (
        rf'href="(/onderzoeken/archief/{re.escape(ead_id)}/invnr/'
        rf'[^"]*(?:~|%7E){re.escape(unit_id)}")' 
    )
    m = re.search(pattern, html, re.I)
    if m:
        path = m.group(1).rstrip('"')
        return f"https://www.nationaalarchief.nl{path}"
    return None


def files_from_invnr_page(ead_id: str, unit_id: str) -> list | None:
    """
    Primary method:
    1. Fetch the top-level invnr page (tree navigator)
    2. Find the deep ~-encoded item URL for unit_id within it
    3. Fetch that deep item page where scan UUIDs are actually embedded
    Returns list of file dicts or None.
    """
    # Step 1: top-level page to find the deep URL
    top_url  = f"https://www.nationaalarchief.nl/onderzoeken/archief/{ead_id}/invnr/{unit_id}"
    top_html = fetch_page(top_url, "invnr top page")
    if not top_html:
        return None

    save_debug_file("invnr_page.html", top_html, always=True)

    # Step 2: find and fetch the deep item page
    deep_url = _find_deep_item_url(top_html, ead_id, unit_id)
    if deep_url:
        print(f"    -> Deep item URL: {deep_url}")
        item_html = fetch_page(deep_url, "invnr item page")
        if item_html:
            save_debug_file("invnr_item_page.html", item_html, always=True)
        else:
            item_html = top_html
    else:
        print(f"    -> No deep URL found in tree page, searching tree page directly")
        item_html = top_html

    # Step 3: extract file UUIDs from the item page
    orig, deflt = uuids_from_html(item_html, "invnr item")

    # Prefer /default/ (JPEG) — confirmed working; /original/ (TIF) may 500
    if deflt:
        print(f"    -> Found {len(deflt)} /default/ (JPEG) UUIDs")
        entries = [{"url": f"{FILE_BASE}/default/{u}", "mimetype": "image/jpeg",
                    "size_bytes": 0, "label": _label_from_html(item_html, u, i+1)}
                   for i, u in enumerate(deflt)]
        for e, u in zip(entries, deflt):
            e["original_url"] = f"{FILE_BASE}/original/{u}"
        return entries

    if orig:
        print(f"    -> Found {len(orig)} /original/ UUIDs (no /default/ found)")
        return [{"url": f"{FILE_BASE}/original/{u}", "mimetype": "image/tiff",
                 "size_bytes": 0, "label": _label_from_html(item_html, u, i+1)}
                for i, u in enumerate(orig)]

    if DEBUG:
        any_uuids = re.findall(UUID_PAT, item_html)
        dbg(f"  Total UUID-like strings in item page: {len(any_uuids)}")
        if any_uuids:
            dbg(f"  First 5: {any_uuids[:5]}")
        fi = item_html.lower().find("/file/v1/")
        if fi >= 0:
            dbg(f"  Context around /file/v1/: ...{item_html[max(0,fi-50):fi+100]}...")
        else:
            dbg("  String '/file/v1/' not found in item page")

    return None


def _label_from_html(html: str, uuid: str, fallback_idx: int) -> str:
    """Try to find the scan name adjacent to a UUID in the HTML."""
    pos = html.find(uuid)
    if pos < 0:
        return f"scan_{fallback_idx:04d}"
    window = html[max(0, pos - 300): pos + 300]
    m = SCAN_RE.search(window)
    if m:
        return m.group(0)
    return f"scan_{fallback_idx:04d}"

# ── Method B: METS parsing (fallback) ────────────────────────────────────────

def files_from_mets(mets_url: str) -> list:
    """Parse a METS file and return ordered file list."""
    NS_METS  = "http://www.loc.gov/METS/"
    NS_XLINK = "http://www.w3.org/1999/xlink"

    dbg(f"Fetching METS: {mets_url}")
    r = requests.get(mets_url, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    # Save METS XML for debugging
    save_debug_file("mets.xml", r.content, always=True)
    root = ET.fromstring(r.content)

    file_index = {}
    file_sec = root.find(f".//{{{NS_METS}}}fileSec")
    if file_sec is None:
        raise RuntimeError("METS has no <fileSec>")

    for f in file_sec.iter(f"{{{NS_METS}}}file"):
        fid      = f.get("ID", "")
        mimetype = f.get("MIMETYPE", "")
        size     = int(f.get("SIZE", 0) or 0)
        use      = f.get("USE", "")
        flocat   = f.find(f"{{{NS_METS}}}FLocat")
        if flocat is None:
            continue
        href = (flocat.get(f"{{{NS_XLINK}}}href") or flocat.get("href", ""))
        if fid and href:
            file_index.setdefault(fid, {})[use] = {
                "url": href, "mimetype": mimetype,
                "size_bytes": size, "label": "",
            }

    ordered = []
    struct_map = root.find(f".//{{{NS_METS}}}structMap")
    if struct_map is not None:
        for div in struct_map.iter(f"{{{NS_METS}}}div"):
            label = div.get("LABEL", "")
            for fptr in div.findall(f"{{{NS_METS}}}fptr"):
                fid = fptr.get("FILEID", "")
                if fid in file_index:
                    variants = file_index[fid]
                    chosen = None
                    for pref in ("DISPLAY", "MASTER", ""):
                        v = variants.get(pref)
                        if v:
                            chosen = dict(v)
                            break
                    if chosen is None:
                        chosen = dict(next(iter(variants.values())))
                    chosen["label"] = label
                    ordered.append(chosen)

    if not ordered:
        for variants in file_index.values():
            ordered.extend(dict(v) for v in variants.values())

    tifs  = [e for e in ordered if "tiff" in e["mimetype"].lower()]
    jpegs = [e for e in ordered if "jpeg" in e["mimetype"].lower() or "jpg" in e["mimetype"].lower()]

    # Swap /default/ for /original/ to get TIF
    def to_original(entry):
        e = dict(entry)
        e["url"] = e["url"].replace("/file/v1/default/", "/file/v1/original/")
        e["mimetype"] = "image/tiff"
        return e

    if tifs:
        return tifs
    if jpegs:
        print(f"    -> METS has JPEG; requesting /original/ (TIF) equivalents")
        return [to_original(e) for e in jpegs]
    return ordered

# ── Debug file saver ─────────────────────────────────────────────────────────

# Set by main() to the output folder so debug files land next to the scans
_DEBUG_DIR: str = ""

def save_debug_file(name: str, data, always: bool = False) -> None:
    """
    Save data to <output_dir>/debug/<name>.
    Saved when always=True (regardless of --debug) or when DEBUG is on.
    """
    if not always and not DEBUG:
        return
    if not _DEBUG_DIR:
        return
    debug_dir = os.path.join(_DEBUG_DIR, "debug")
    os.makedirs(debug_dir, exist_ok=True)
    path = os.path.join(debug_dir, name)
    if isinstance(data, bytes):
        with open(path, "wb") as f:
            f.write(data)
    else:
        with open(path, "w", encoding="utf-8") as f:
            f.write(data)
    print(f"  [saved debug] {path}")


# ── Method C: find METS URL from EAD and use METS parser ─────────────────────

def _stream_bytes(url: str, label: str) -> bytes | None:
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT, stream=True)
        r.raise_for_status()
        chunks, total = [], 0
        for chunk in r.iter_content(256 * 1024):
            chunks.append(chunk)
            total += len(chunk)
            print(f"\r      {label}: {total/1e6:.1f} MB ...", end="", flush=True)
        print()
        return b"".join(chunks)
    except Exception as e:
        dbg(f"{label} fetch error: {e}")
        print()
        return None


def mets_url_from_ead(ead_bytes: bytes, unit_id: str, label: str) -> str | None:
    text = ead_bytes.decode("utf-8", errors="replace")
    text = re.sub(r'\sxmlns\s*=\s*"[^"]*"', '', text)
    text = re.sub(r"\sxmlns\s*=\s*'[^']*'", '', text)
    try:
        root = ET.fromstring(text)
    except ET.ParseError as e:
        dbg(f"XML parse error: {e}")
        return None

    parent_map = {c: p for p in root.iter() for c in p}
    def local(el):
        t = el.tag
        return t.split("}")[-1] if "}" in t else t

    C_TAGS = {f"c{i:02d}" for i in range(13)} | {"c", "archdesc"}

    candidates = []
    for el in root.iter():
        if local(el) != "unitid":
            continue
        val = (el.text or "").strip()
        if val != unit_id:
            continue
        t = el.get("type", "").lower()
        if t in ("handle", "uri") or val.startswith("http"):
            continue
        candidates.append(el)

    dbg(f"{label}: {len(candidates)} <unitid>{unit_id}</unitid> found")

    for uid_el in candidates:
        component = uid_el
        for _ in range(25):
            p = parent_map.get(component)
            if p is None:
                break
            if local(p) in C_TAGS:
                component = p
                break
            component = p
        for dao in component.iter():
            if local(dao) != "dao":
                continue
            href = (dao.get("{http://www.w3.org/1999/xlink}href") or dao.get("href", "")).strip()
            if href and "/mets/" in href:
                dbg(f"  dao href: {href}")
                return href
    return None


def validate_url(url: str) -> bool:
    try:
        r = requests.head(url, headers=HEADERS, timeout=20, allow_redirects=True)
        dbg(f"  HEAD {url} -> {r.status_code}")
        return r.status_code == 200
    except Exception as e:
        dbg(f"  HEAD error: {e}")
        return False


def files_via_ead(ead_id: str, unit_id: str, use_oai: bool) -> list | None:
    if use_oai:
        url   = f"{OAI_BASE}?verb=GetRecord&metadataPrefix=oai_ead&identifier={ead_id}"
        label = "OAI-PMH EAD"
    else:
        url   = f"https://www.nationaalarchief.nl/onderzoeken/archief/{ead_id}/download/xml"
        label = "website EAD XML"

    print(f"    -> Fetching {label} ...")
    raw = _stream_bytes(url, label)
    if not raw:
        return None

    # Save the EAD XML for debugging
    safe_label = label.lower().replace(" ", "_").replace("-", "_")
    save_debug_file(f"ead_{safe_label}.xml", raw, always=True)

    mets_url = mets_url_from_ead(raw, unit_id, label)
    if not mets_url:
        print(f"    -> No METS URL found in {label}")
        return None

    print(f"    -> METS URL: {mets_url}")
    print(f"    -> Validating ...")
    if not validate_url(mets_url):
        print(f"    -> 404 - stale UUID")
        return None

    print(f"    -> METS is live, parsing ...")
    try:
        return files_from_mets(mets_url)
    except Exception as e:
        print(f"    -> METS parse failed: {e}")
        return None

# ── Master discovery ──────────────────────────────────────────────────────────

def discover_files(ead_id: str, unit_id: str, mets_override: str | None) -> list:

    # ── Supplied METS URL (--mets flag) ───────────────────────────────────────
    if mets_override:
        print(f"  Using --mets override: {mets_override}")
        return files_from_mets(mets_override)

    methods = [
        (
            "invnr HTML page (direct file UUIDs)",
            lambda: files_from_invnr_page(ead_id, unit_id),
        ),
        (
            "website EAD XML -> METS",
            lambda: files_via_ead(ead_id, unit_id, use_oai=False),
        ),
        (
            "OAI-PMH EAD -> METS",
            lambda: files_via_ead(ead_id, unit_id, use_oai=True),
        ),
    ]

    for label, fn in methods:
        print(f"  Trying: {label} ...")
        try:
            result = fn()
        except Exception as e:
            print(f"    -> Error: {e}")
            continue

        if result:
            return result
        print(f"    -> No files found, trying next method ...")

    raise RuntimeError(
        f"\nAll discovery methods failed for unitID='{unit_id}' in archive '{ead_id}'.\n\n"
        "MANUAL FALLBACK:\n"
        "  1. Open the viewer in your browser\n"
        "  2. Press F12 -> Network tab\n"
        "  3. Click through the scans; look for requests to service.archief.nl/gaf/api/mets/\n"
        "  4. Copy that URL and run:\n"
        f'     na-dl.py --mets "https://service.archief.nl/gaf/api/mets/v1/..." \\\n'
        f'              "https://www.nationaalarchief.nl/onderzoeken/archief/{ead_id}/invnr/{unit_id}/..."\n\n'
        "  Or if you have a /file/v1/original/<uuid> URL from the download button,\n"
        "  the UUID pattern for that inventory is what we need to find.\n"
        "  Run with --debug and paste the output so we can diagnose further."
    )

# ── Downloading ───────────────────────────────────────────────────────────────

def safe_filename(label: str, index: int, unit_id: str, ext: str) -> str:
    if label and label != f"scan_{index:04d}":
        name = re.sub(r'[^\w\-_.]', '_', label).strip("_")
    else:
        name = f"{unit_id}_{index:04d}"
    return f"{name}{ext}"


def download_one(session, url: str, fallback_url: str, fpath: str) -> tuple[bool, str, str]:
    """
    Download url -> fpath.  If url fails (non-200 / error), try fallback_url.
    Returns (success, used_url, error_msg).
    """
    tmp = fpath + ".part"
    for attempt_url, attempt_path in [(url, fpath), (fallback_url, fpath.replace(".tif", ".jpg"))]:
        if not attempt_url:
            continue
        try:
            r = session.get(attempt_url, stream=True, timeout=TIMEOUT)
            if r.status_code != 200:
                dbg(f"  {attempt_url} -> {r.status_code}")
                continue
            with open(tmp, "wb") as fh:
                for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                    fh.write(chunk)
            os.rename(tmp, attempt_path)
            return True, attempt_url, ""
        except Exception as e:
            dbg(f"  {attempt_url} error: {e}")
            if os.path.exists(tmp):
                os.remove(tmp)
    return False, url, "All URLs failed"


def download_files(files: list, output_dir: str, unit_id: str):
    os.makedirs(output_dir, exist_ok=True)
    total = len(files)
    print(f"  Saving {total} file(s) to: {output_dir}\n")

    session = requests.Session()
    session.headers.update(HEADERS)
    failed = []

    for i, info in enumerate(files, start=1):
        label    = info.get("label", "")
        orig_url = info.get("original_url", "")
        def_url  = info.get("url", "")

        # Skip if either version already downloaded
        tif_path = os.path.join(output_dir, safe_filename(label, i, unit_id, ".tif"))
        jpg_path = os.path.join(output_dir, safe_filename(label, i, unit_id, ".jpg"))
        if os.path.exists(tif_path) or os.path.exists(jpg_path):
            print(f"  [{i:>4}/{total}] SKIP  (already exists)")
            continue

        # Try TIF first, fall back to JPEG
        primary  = orig_url or def_url
        fallback = def_url if orig_url else ""
        primary_ext  = ".tif" if orig_url else ".jpg"
        primary_path = os.path.join(output_dir, safe_filename(label, i, unit_id, primary_ext))

        print(f"  [{i:>4}/{total}] {safe_filename(label, i, unit_id, primary_ext)} ...", end="", flush=True)
        dbg(f"\n           primary : {primary}")
        dbg(f"           fallback: {fallback}")

        success, used_url, err = download_one(session, primary, fallback, primary_path)
        if success:
            saved_path = primary_path if used_url == primary else primary_path.replace(".tif", ".jpg")
            actual_mb  = os.path.getsize(saved_path) / 1_048_576
            qual = "TIF" if used_url == orig_url else "JPEG"
            print(f" OK  ({actual_mb:.1f} MB, {qual})")
        else:
            print(f" FAILED: {err}")
            failed.append((safe_filename(label, i, unit_id, primary_ext), err))

        time.sleep(DELAY_SEC)

    print()
    if failed:
        print(f"WARNING: {len(failed)} file(s) had problems:")
        for name, reason in failed:
            print(f"   - {name}: {reason}")
    else:
        print(f"All {total} file(s) downloaded successfully.")

# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    global DEBUG

    args = [a for a in sys.argv[1:] if a]
    if not args:
        print(__doc__)
        sys.exit(1)

    mets_override = None
    clean_args    = []
    i = 0
    while i < len(args):
        if args[i] == "--debug":
            DEBUG = True
        elif args[i] == "--mets" and i + 1 < len(args):
            mets_override = args[i + 1]
            i += 1
        else:
            clean_args.append(args[i])
        i += 1

    if not clean_args:
        print("Error: no URL provided.")
        sys.exit(1)

    raw_url = clean_args[0].strip()

    # Detect unquoted URL split by & on Windows CMD
    if (raw_url.startswith("http") and "&" not in raw_url
            and "eadID" not in raw_url and "invnr" not in raw_url):
        print(
            "ERROR: URL looks incomplete — probably split by & in Windows CMD.\n"
            "Wrap the URL in double quotes:\n"
            '    na-dl.py "https://...?eadID=1.04.02&unitID=2864&query="'
        )
        sys.exit(1)

    try:
        ead_id, unit_id, scan_name = parse_viewer_url(raw_url)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    output_dir = os.path.join(
        os.getcwd(), f"NA_{ead_id.replace('.', '-')}_{unit_id}"
    )

    SEP = "=" * 64
    print(SEP)
    print("  Nationaal Archief High-Res TIF Downloader  v1.5")
    print(SEP)
    print(f"  Archive   (eadID)  : {ead_id}")
    print(f"  Inventory (unitID) : {unit_id}")
    print(f"  Output folder      : {output_dir}")
    if mets_override:
        print(f"  METS override      : {mets_override}")
    if DEBUG:
        print("  Mode               : DEBUG (verbose)")
    print()

    # Point debug saver at the output folder (created on first save if needed)
    global _DEBUG_DIR
    _DEBUG_DIR = output_dir

    # ── Step 1: discover files ────────────────────────────────────────────────
    print("[1/3] Discovering files ...")
    try:
        files = discover_files(ead_id, unit_id, mets_override)
    except RuntimeError as e:
        print(f"\nERROR: {e}")
        sys.exit(1)

    print(f"      -> {len(files)} file(s) found")
    print()

    # ── Step 2: report ────────────────────────────────────────────────────────
    print("[2/3] File list:")
    for i, f in enumerate(files[:5], 1):
        print(f"      {i}. {f['url']}")
    if len(files) > 5:
        print(f"      ... ({len(files) - 5} more)")
    print()

    # ── Step 3: download ──────────────────────────────────────────────────────
    print("[3/3] Downloading ...")
    download_files(files, output_dir, unit_id)
    print(f"\n  Files saved to: {output_dir}")


if __name__ == "__main__":
    main()
