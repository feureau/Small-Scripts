#!/usr/bin/env python3
"""
dlsastra.py  –  Download text and images from a sastra.org collection entry.

Usage (run from any working directory):
    python /path/to/dlsastra.py <URL>

Example:
    python dlsastra.py https://www.sastra.org/kisah-cerita-dan-kronikal/babad/3343-babad-kartasura-british-library-mss-jav-49-1774-6-1010-pupuh-01-12

Output (created in the current working directory):
    <url-slug>/
        images/          ← manuscript page images (.jpg)
        <url-slug>.md    ← full transcription with Markdown footnotes [^N]
"""

import sys
import re
import time
import urllib.request
import urllib.parse
import urllib.error
from html.parser import HTMLParser
from pathlib import Path


# ──────────────────────────────────────────────────────────────────────────────
# Network helpers
# ──────────────────────────────────────────────────────────────────────────────

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def fetch_text(url: str, retries: int = 5, delay: float = 3.0) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                raw = resp.read()
                ct = resp.headers.get("Content-Type", "")
                m = re.search(r"charset=([^\s;]+)", ct)
                charset = m.group(1) if m else "utf-8"
                return raw.decode(charset, errors="replace")
        except Exception as exc:
            if attempt < retries - 1:
                print(f"    retry {attempt + 1}: {exc}")
                time.sleep(delay)
            else:
                raise


def download_file(url: str, dest: Path, retries: int = 5, delay: float = 2.0) -> bool:
    req = urllib.request.Request(url, headers=HEADERS)
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = resp.read()
            dest.write_bytes(data)
            return True
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return False
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                return False
        except Exception as exc:
            if attempt < retries - 1:
                print(f"    retry {attempt + 1}: {exc}")
                time.sleep(delay)
            else:
                return False
    return False


# ──────────────────────────────────────────────────────────────────────────────
# sastra.org page parsing
# ──────────────────────────────────────────────────────────────────────────────

def get_entry_id(html: str) -> str | None:
    for pat in [
        r'ti_id=(\d+)',
        r'katalog/(\d+)/big/',
        r'katalog/(\d+)/',
    ]:
        m = re.search(pat, html)
        if m:
            return m.group(1)
    return None


def get_title(html: str) -> str:
    m = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.S | re.I)
    if m:
        return re.sub(r'<[^>]+>', '', m.group(1)).strip()
    m = re.search(r'<title[^>]*>(.*?)</title>', html, re.S | re.I)
    if m:
        return re.sub(r'<[^>]+>', '', m.group(1)).strip()
    return "Untitled"


def get_total_images(html: str) -> int | None:
    m = re.search(r'Citra\s+\d+\s+dari\s+(\d+)', html)
    return int(m.group(1)) if m else None


def build_image_urls(html: str, entry_id: str,
                     base: str = "https://www.sastra.org") -> list:
    """
    Build image URL list for the entry.

    sastra.org stores scans at:
        /sastra/media/katalog/<entry_id>/big/ysl<entry_id>_f<NNN><r|v>.jpg

    Strategy 1: collect folio markers from the transcription text:
        --- [f. 1r] ---  /  [f. 2v]
    Strategy 2: generate r/v pairs up to the stated total image count.
    Strategy 3: generate a probe list (caller stops on run of 404s).
    """
    # Strategy 1 – folio markers
    seen: set = set()
    folios: list = []
    for num_str, side in re.findall(r'\[f\.\s*(\d+)([rv])\]', html):
        key = (num_str, side)
        if key not in seen:
            seen.add(key)
            folios.append((int(num_str), side))

    if folios:
        return [
            f"{base}/sastra/media/katalog/{entry_id}/big/"
            f"ysl{entry_id}_f{n:03d}{s}.jpg"
            for n, s in folios
        ]

    # Strategy 2 – total count
    total = get_total_images(html)
    if total:
        urls = []
        for i in range(1, 500):
            for side in ("r", "v"):
                urls.append(
                    f"{base}/sastra/media/katalog/{entry_id}/big/"
                    f"ysl{entry_id}_f{i:03d}{side}.jpg"
                )
                if len(urls) >= total:
                    return urls

    # Strategy 3 – blind probe (up to 400 candidates)
    urls = []
    for i in range(1, 201):
        for side in ("r", "v"):
            urls.append(
                f"{base}/sastra/media/katalog/{entry_id}/big/"
                f"ysl{entry_id}_f{i:03d}{side}.jpg"
            )
    return urls


# ──────────────────────────────────────────────────────────────────────────────
# HTML → Markdown converter
# ──────────────────────────────────────────────────────────────────────────────

_SKIP_TAGS = frozenset({
    "script", "style", "nav", "form", "input", "button",
    "select", "option", "noscript", "iframe",
})

_BLOCK_TAGS = frozenset({
    "p", "div", "section", "article", "main", "aside",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "li", "table", "thead", "tbody", "tr",
    "blockquote", "pre", "hr", "figure", "figcaption",
})


class _H2MD(HTMLParser):

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._buf: list = []
        self._skip: int = 0
        self._sup: bool = False
        self._footref: bool = False
        self._stack: list = []

    def result(self) -> str:
        text = "".join(self._buf)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    def handle_starttag(self, tag, attrs):
        attr = dict(attrs)
        cls = attr.get("class", "")

        if self._skip:
            if tag in _SKIP_TAGS:
                self._skip += 1
            return
        if tag in _SKIP_TAGS:
            self._skip += 1
            return

        self._stack.append(tag)

        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._nl(2)
            self._buf.append("#" * int(tag[1]) + " ")
        elif tag == "p":
            self._nl(2)
        elif tag == "br":
            self._buf.append("  \n")
        elif tag in ("b", "strong"):
            self._buf.append("**")
        elif tag in ("i", "em"):
            self._buf.append("*")
        elif tag == "sup":
            self._sup = True
        elif tag == "a" and "footref" in cls:
            self._footref = True
        elif tag == "li":
            self._nl(1)
            parent = self._stack[-2] if len(self._stack) >= 2 else ""
            self._buf.append("- " if parent != "ol" else "1. ")
        elif tag == "hr":
            self._nl(2)
            self._buf.append("---")
            self._nl(2)
        elif tag in ("td", "th"):
            self._buf.append(" | ")
        elif tag == "tr":
            self._nl(1)
        elif tag in _BLOCK_TAGS:
            self._nl(2)

        # Footnote section dividers
        if any(k in cls.lower() for k in ("catatan", "footnote", "kaki")):
            self._nl(2)
            self._buf.append("---")
            self._nl(2)

    def handle_endtag(self, tag):
        if self._skip:
            if tag in _SKIP_TAGS:
                self._skip -= 1
            return
        if self._stack and self._stack[-1] == tag:
            self._stack.pop()

        if tag in ("b", "strong"):
            self._buf.append("**")
        elif tag in ("i", "em"):
            self._buf.append("*")
        elif tag == "sup":
            self._sup = False
        elif tag == "a":
            self._footref = False
        elif tag in _BLOCK_TAGS:
            self._nl(2)

    def handle_data(self, data):
        if self._skip:
            return
        if self._sup or self._footref:
            s = data.strip()
            if s.startswith('[') and s.endswith(']'):
                s = s[1:-1]
            if re.fullmatch(r'\d+', s):
                self._buf.append(f"[^{s}]")
                return
        self._buf.append(data)

    def _nl(self, n: int = 1):
        tail = "".join(self._buf)
        have = len(tail) - len(tail.rstrip('\n'))
        need = n - have
        if need > 0:
            self._buf.append('\n' * need)


def _strip_noise(html: str) -> str:
    for tag in ("script", "style", "nav", "form", "noscript",
                "header", "footer", "aside", "iframe"):
        html = re.sub(
            rf'<{tag}(\s[^>]*)?>.*?</{tag}>',
            '', html, flags=re.S | re.I
        )
    return html


def extract_main_content(html: str) -> str:
    """Isolate the transcription block from the full page HTML."""
    patterns = [
        r'<div[^>]*id="[^"]*mark_range[^"]*"[^>]*>(.*)',
        r'<div[^>]*itemprop="[^"]*articleBody[^"]*"[^>]*>(.*)',
        r'<div[^>]*class="[^"]*\bteks\b[^"]*"[^>]*>(.*)',
        r'<div[^>]*id="[^"]*(?:artikel|content|teks)[^"]*"[^>]*>(.*)',
        r'<article[^>]*>(.*)',
        r'<main[^>]*>(.*)',
    ]
    for pat in patterns:
        m = re.search(pat, html, re.S | re.I)
        if m:
            return m.group(1)
    m = re.search(r'<body[^>]*>(.*?)</body>', html, re.S | re.I)
    return m.group(1) if m else html


def _fix_footnotes(md: str) -> str:
    """
    Convert footnote list items to Markdown footnote definitions.

    sastra.org footnotes look like:
        1 Some text. (kembali)
    Output:
        [^1]: Some text.
    """
    def repl(m):
        num = m.group(1)
        text = m.group(2).strip()
        text = re.sub(r'\s*\(kembali\)\s*$', '', text).strip()
        text = re.sub(r'\|\s*$', '', text).strip()
        return f"[^{num}]: {text}"

    # First match Sastra footnotes that contain '(kembali)' explicitly (often inside tables)
    md = re.sub(
        r'^[\s\|]*(\d+)[\.\:\)\]\|\s]+(.*?\(kembali\).*)$',
        repl,
        md,
        flags=re.MULTILINE,
    )
    # Then match classic footnotes just in case
    md = re.sub(
        r'^\s*(\d+)\s*[\.:\)]\s+(.+?)\s*$',
        repl,
        md,
        flags=re.MULTILINE,
    )

    # Some Sastra pages emit the footnote twice: once in the table and once as a hidden tooltip span.
    # This deduplicates identical plain text lines immediately following a footnote definition.
    lines = md.split('\n')
    cleaned_lines = []
    last_footnote_text = None

    for line in lines:
        m = re.match(r'^\[\^\d+\]:\s*(.+)$', line)
        if m:
            last_footnote_text = m.group(1).strip()
            cleaned_lines.append(line)
        else:
            line_str = line.strip()
            if last_footnote_text and line_str == last_footnote_text:
                last_footnote_text = None
                continue
            if line_str != "":
                last_footnote_text = None
            cleaned_lines.append(line)

    return '\n'.join(cleaned_lines)


def html_to_markdown(html: str) -> str:
    html = _strip_noise(html)
    content = extract_main_content(html)
    parser = _H2MD()
    parser.feed(content)
    md = parser.result()
    return _fix_footnotes(md)


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────

def url_slug(url: str) -> str:
    path = urllib.parse.urlparse(url).path.rstrip("/")
    return path.split("/")[-1] or "sastra"


def extract_catalog_links(url: str, html: str) -> list[str]:
    parsed = urllib.parse.urlparse(url)
    qs = urllib.parse.parse_qs(parsed.query)
    ti_id = qs.get("ti_id", [None])[0]
    
    html_clean = _strip_noise(html)
    base_url = "https://www.sastra.org"
    links = []
    
    for match in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html_clean, re.I):
        href = match.group(1)
        text = match.group(2)
        full_url = urllib.parse.urljoin(base_url, href)
        path = urllib.parse.urlparse(full_url).path
        parts = [p for p in path.split('/') if p]
        
        if len(parts) >= 2 and re.match(r'^\d+-', parts[-1]):
            if ti_id:
                if f"-{ti_id}" not in parts[-1] and f"{ti_id}" not in parts[-1] and f"#{ti_id}" not in text:
                    continue
            if full_url not in links:
                links.append(full_url)
                
    return links


def process_single_url(url: str):
    slug = url_slug(url)
    base_url = "https://www.sastra.org"

    out_dir = Path.cwd() / slug
    img_dir = out_dir / "images"
    out_dir.mkdir(parents=True, exist_ok=True)
    img_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n──────────────────────────────────────────────────")
    print(f"URL    : {url}")
    print(f"Output : {out_dir}\n")

    # 1. Fetch
    print("[1/3] Fetching page…")
    try:
        html = fetch_text(url)
    except Exception as exc:
        print(f"ERROR fetching page: {exc}")
        return

    # 2. Text
    print("[2/3] Extracting text…")
    title = get_title(html)
    entry_id = get_entry_id(html)
    print(f"  Title    : {title}")
    print(f"  Entry ID : {entry_id}")

    md_body = html_to_markdown(html)
    full_md = f"# {title}\n\nSource: <{url}>\n\n---\n\n{md_body}\n"
    md_path = out_dir / f"{slug}.md"
    md_path.write_text(full_md, encoding="utf-8")
    print(f"  Saved  → {md_path}")

    # 3. Images
    if not entry_id:
        print("\n[3/3] WARNING: Could not determine entry ID — skipping images.")
        print(f"\nDone.  Text saved at: {md_path}")
        return

    image_urls = build_image_urls(html, entry_id, base_url)
    total_expected = get_total_images(html)
    label = f"{total_expected} expected" if total_expected else f"{len(image_urls)} candidates"
    print(f"\n[3/3] Downloading images ({label})…")

    downloaded = 0
    consecutive_miss = 0

    for i, img_url in enumerate(image_urls, 1):
        fname = img_url.rsplit("/", 1)[-1]
        dest = img_dir / fname

        if dest.exists() and dest.stat().st_size > 500:
            print(f"  [{i:>4}] {fname}  (cached)")
            downloaded += 1
            consecutive_miss = 0
            continue

        ok = download_file(img_url, dest)
        if ok and dest.exists() and dest.stat().st_size > 500:
            size_kb = dest.stat().st_size // 1024
            print(f"  [{i:>4}] {fname}  {size_kb} KB")
            downloaded += 1
            consecutive_miss = 0
        else:
            dest.unlink(missing_ok=True)
            print(f"  [{i:>4}] {fname}  — not found")
            consecutive_miss += 1
            if consecutive_miss >= 8:
                print("  8 consecutive misses — stopping.")
                break

        time.sleep(0.25)

    print(f"\nDone.")
    print(f"  Text   : {md_path}")
    print(f"  Images : {downloaded} files in {img_dir}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    url = sys.argv[1].strip()
    
    if "katalog/judul" in url or "katalog" in url:
        print(f"Fetching catalog page: {url}")
        try:
            html = fetch_text(url)
        except Exception as exc:
            sys.exit(f"ERROR fetching catalog: {exc}")
            
        links = extract_catalog_links(url, html)
        if not links:
            print("No valid article links found in the catalog!")
            sys.exit(1)
            
        print(f"Found {len(links)} parts in catalog. Starting batch download...")
        for i, link in enumerate(links, 1):
            print(f"\n{'='*60}\nPart {i} of {len(links)}")
            process_single_url(link)
    else:
        process_single_url(url)

if __name__ == "__main__":
    main()
