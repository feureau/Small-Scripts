#!/usr/bin/env python3
"""
folderbylang.py - Organize files into language subfolders (e.g., en/, cn/, id/).

Detects language tags in filenames using two passes:
  1. Parenthesized tags anywhere in the filename: e.g. (-en), (-cn), (-id), (en), (.en), (_zh-cn)
  2. Trailing language suffixes before the file extension: e.g. video-en.srt, video_cn.mp4, video.id.srt

Files without a recognized language tag (e.g. Short_01_...-instagram.txt) are left untouched.

Usage:
    folderbylang.py                  # Sort all files in the current working directory
    folderbylang.py *                # Same (handles Windows CMD literal '*')
    folderbylang.py <dir_or_glob>    # Sort matching files or target directory
    folderbylang.py -n / --dry-run   # Preview changes without moving files
    folderbylang.py -r / --recursive # Recursively sort subdirectories
"""

import argparse
import glob
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Iterable, List, Optional, Set

ALL_FILE_PATTERNS = {"*", "*.*"}

# Comprehensive set of valid ISO 639-1 (2-letter), common ISO 639-2/3 (3-letter),
# and common regional/subtitle workflow language codes.
KNOWN_LANG_CODES: Set[str] = {
    # Common 2-letter ISO 639-1 & workflow shorthand codes
    "aa", "ab", "af", "ak", "am", "an", "ar", "as", "av", "ay", "az",
    "ba", "be", "bg", "bh", "bi", "bm", "bn", "bo", "br", "bs",
    "ca", "ce", "ch", "cn", "co", "cr", "cs", "cu", "cv", "cy", "cz",
    "da", "de", "dk", "dv", "dz",
    "ee", "el", "en", "eo", "es", "et", "eu",
    "fa", "ff", "fi", "fj", "fo", "fr", "fy",
    "ga", "gd", "gl", "gn", "gr", "gu", "gv",
    "ha", "he", "hi", "hk", "ho", "hr", "ht", "hu", "hy", "hz",
    "ia", "id", "ie", "ig", "ii", "ik", "in", "io", "is", "it", "iu", "iw",
    "ja", "jp", "jv", "jw",
    "ka", "kg", "ki", "kj", "kk", "kl", "km", "kn", "ko", "kr", "ks", "ku", "kv", "kw", "ky",
    "la", "lb", "lg", "li", "ln", "lo", "lt", "lu", "lv",
    "mg", "mh", "mi", "mk", "ml", "mn", "mo", "mr", "ms", "mt", "my",
    "na", "nb", "nd", "ne", "ng", "nl", "nn", "no", "nr", "nv", "ny",
    "oc", "oj", "om", "or", "os",
    "pa", "pi", "pl", "ps", "pt",
    "qu",
    "rm", "rn", "ro", "ru", "rw",
    "sa", "sc", "sd", "se", "sg", "sh", "si", "sk", "sl", "sm", "sn", "so", "sq", "sr", "ss", "st", "su", "sv", "sw",
    "ta", "te", "tg", "th", "ti", "tk", "tl", "tn", "to", "tr", "ts", "tt", "tw", "ty",
    "ua", "ug", "uk", "ur", "uz",
    "ve", "vi", "vo",
    "wa", "wo",
    "xh",
    "yi", "ji", "yo",
    "za", "zh", "zu",
    # Common 3-letter ISO 639-2/3 & subtitle codes
    "ara", "ben", "bul", "cat", "ces", "chi", "chs", "cht", "cmn", "cze",
    "dan", "deu", "dut", "ell", "eng", "est", "eus", "fas", "fil", "fin", "fra", "fre",
    "geo", "ger", "gre", "guj", "heb", "hin", "hrv", "hun", "hye",
    "ice", "ind", "isl", "ita", "jav", "jpn", "kan", "kat", "kaz", "khm", "kor",
    "lao", "lat", "lav", "lit", "mac", "mal", "mao", "mar", "may", "mkd", "mon", "mri", "msa", "mya",
    "nep", "nld", "nob", "nor", "pan", "per", "pol", "por", "pus",
    "ron", "rum", "rus", "san", "sin", "slk", "slo", "slv", "som", "spa", "sqi", "srp", "sun", "swa", "swe",
    "tam", "tel", "tgk", "tgl", "tha", "tib", "tur", "ukr", "urd", "uzb", "vie", "wel", "yid", "yue", "zho",
    # Common regional compound tags
    "zh-cn", "zh-tw", "zh-hk", "zh-sg", "zh-hans", "zh-hant",
    "en-us", "en-gb", "en-au", "en-ca", "en-in",
    "pt-br", "pt-pt",
    "es-es", "es-la", "es-mx", "es-419",
    "fr-fr", "fr-ca",
    "de-de", "de-at", "de-ch",
    "sr-latn", "sr-cyrl",
}

# Pass 1: Parenthesized tag anywhere in the stem, e.g. (-cn), (-en), (-id), (en), (.id), (_zh-cn)
PAREN_LANG_RE = re.compile(r"\(([-_.]?[a-zA-Z]{2,3}(?:[-_][a-zA-Z0-9]{2,4})?)\)")

# Pass 2: Trailing suffix at the end of the stem before extension, e.g. video-en, video_cn, video.id
TRAILING_LANG_RE = re.compile(r"(?:^|[-_. ])([a-zA-Z]{2,3}(?:[-_][a-zA-Z0-9]{2,4})?)$")


def normalize_lang_code(raw_code: str) -> Optional[str]:
    """
    Strip leading punctuation (-, _, .) and normalize a candidate language code.
    Returns the lowercase normalized code if it is in KNOWN_LANG_CODES, otherwise None.
    """
    cleaned = raw_code.lstrip("-_.").strip().lower().replace("_", "-")
    if cleaned in KNOWN_LANG_CODES:
        return cleaned
    return None


def detect_language_code(filename: str) -> Optional[str]:
    """
    Detect a language code from a filename.

    Priority 1: Parenthesized tags anywhere in the stem, e.g. `(-cn)`, `(-en)`, `(-id)`.
    Priority 2: Trailing language suffix on the stem before the extension, e.g. `-en.srt`, `_cn.mp4`, `.id.srt`.
    """
    stem = os.path.splitext(filename)[0]

    # Pass 1: Check parenthesized tags in the stem
    for match in PAREN_LANG_RE.finditer(stem):
        code = normalize_lang_code(match.group(1))
        if code:
            return code

    # Pass 2: Check trailing language suffix on the stem
    trailing_match = TRAILING_LANG_RE.search(stem)
    if trailing_match:
        code = normalize_lang_code(trailing_match.group(1))
        if code:
            return code

    return None


def collect_files(patterns: Iterable[str], recursive: bool = False) -> List[Path]:
    """Collect unique files from CLI patterns or directory paths."""
    seen: Set[Path] = set()
    files: List[Path] = []

    def add_file(p: Path):
        try:
            resolved = p.resolve()
        except OSError:
            return
        if resolved.is_file() and resolved not in seen:
            seen.add(resolved)
            files.append(resolved)

    def scan_dir(d: Path):
        try:
            entries = sorted(d.iterdir(), key=lambda x: x.name.lower())
        except OSError:
            return
        for entry in entries:
            if entry.is_file():
                add_file(entry)
            elif recursive and entry.is_dir():
                # Avoid recursing into existing language subfolders
                if entry.name.lower() not in KNOWN_LANG_CODES:
                    scan_dir(entry)

    for pattern in patterns:
        p = Path(pattern).expanduser()

        if p.is_file():
            add_file(p)
            continue

        if p.is_dir():
            scan_dir(p)
            continue

        if p.name in ALL_FILE_PATTERNS:
            base = p.parent if str(p.parent) != "" else Path.cwd()
            if not base.is_Absolute() if hasattr(base, "is_Absolute") else not base.is_absolute():
                base = Path.cwd() / base
            if base.is_dir():
                scan_dir(base)
                continue

        # Wildcard patterns like *.mkv, *(-cn)*, etc.
        matched = glob.glob(str(p), recursive=recursive)
        for m in sorted(matched, key=lambda x: x.lower()):
            mp = Path(m)
            if mp.is_file():
                add_file(mp)
            elif mp.is_dir():
                scan_dir(mp)

    return files


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sort files into language subfolders (en, cn, id, etc.) based on filename language tags."
    )
    parser.add_argument(
        "paths",
        nargs="*",
        default=["*"],
        help="Files, directories, or glob patterns to process (default: current working directory).",
    )
    parser.add_argument(
        "-n", "--dry-run", "-p", "--preview",
        dest="dry_run",
        action="store_true",
        help="Preview how files will be sorted without moving them.",
    )
    parser.add_argument(
        "-r", "--recursive",
        action="store_true",
        help="Recursively scan subdirectories (skips existing language code folders).",
    )
    args = parser.parse_args()

    script_path = Path(__file__).resolve()
    files = collect_files(args.paths, recursive=args.recursive)

    if not files:
        print("No files found to scan.")
        return 0

    mode_label = "[DRY RUN] " if args.dry_run else ""
    print(f"{mode_label}Scanning {len(files)} file(s)...")
    print("-" * 60)

    moved_count = 0
    skipped_unmatched = 0
    skipped_collision = 0
    created_folders: Set[Path] = set()

    for src in files:
        if src == script_path:
            continue

        lang_code = detect_language_code(src.name)
        if not lang_code:
            skipped_unmatched += 1
            continue

        dest_dir = src.parent / lang_code
        dest_file = dest_dir / src.name

        if dest_file.exists():
            print(f"[SKIP - EXISTS] {src.name} -> {lang_code}/{src.name} already exists")
            skipped_collision += 1
            continue

        if args.dry_run:
            if dest_dir not in created_folders and not dest_dir.exists():
                print(f"[DRY RUN] Would create folder: {lang_code}/")
                created_folders.add(dest_dir)
            print(f"[DRY RUN] {src.name} -> {lang_code}/")
            moved_count += 1
        else:
            if not dest_dir.exists():
                try:
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    if dest_dir not in created_folders:
                        print(f"[CREATED] {lang_code}/")
                        created_folders.add(dest_dir)
                except OSError as e:
                    print(f"[ERROR] Failed to create folder {dest_dir}: {e}", file=sys.stderr)
                    continue

            try:
                shutil.move(str(src), str(dest_file))
                print(f"[MOVED] {src.name} -> {lang_code}/")
                moved_count += 1
            except (OSError, shutil.Error) as e:
                print(f"[ERROR] Could not move {src.name}: {e}", file=sys.stderr)

    print("-" * 60)
    action_word = "Would move" if args.dry_run else "Moved"
    summary = f"Done! {action_word} {moved_count} file(s) into language folder(s). Left {skipped_unmatched} unmatched file(s) untouched."
    if skipped_collision:
        summary += f" Skipped {skipped_collision} existing file(s)."
    print(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
