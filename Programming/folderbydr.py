#!/usr/bin/env python3
"""
folderbydr.py - Organize files into dynamic range subfolders (HDR/, SDR/, HDR10/, HLG/, DV/).

Detects standalone dynamic range tokens in filenames and uses the LAST occurrence in the stem
so that source prefixes like "1. Assembly 24p HDR_..._-_SDR_..." are accurately sorted into "SDR/".

Files without a recognized dynamic range token are left untouched.

Usage:
    folderbydr.py                  # Sort all files in the current working directory
    folderbydr.py *                # Same (handles Windows CMD literal '*')
    folderbydr.py <dir_or_glob>    # Sort matching files or target directory
    folderbydr.py -n / --dry-run   # Preview changes without moving files
    folderbydr.py -r / --recursive # Recursively sort subdirectories
"""

import argparse
import glob
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set

ALL_FILE_PATTERNS = {"*", "*.*"}

# Map normalized uppercase token -> canonical folder name
DR_CANONICAL_MAP: Dict[str, str] = {
    "HDR": "HDR",
    "SDR": "SDR",
    "HDR10+": "HDR10+",
    "HDR10PLUS": "HDR10+",
    "HDR10": "HDR10",
    "HLG": "HLG",
    "DV": "DV",
    "DOVI": "DV",
}

KNOWN_DR_FOLDERS: Set[str] = {v.lower() for v in DR_CANONICAL_MAP.values()}

# Matches standalone dynamic range tokens bounded by start/end or non-alphanumeric separators
# Order longer tokens (HDR10+, HDR10PLUS, HDR10, DOVI) before shorter ones (HDR, SDR, HLG, DV)
DR_TOKEN_RE = re.compile(
    r"(?:^|(?<=[^a-zA-Z0-9]))"
    r"(HDR10\+|HDR10PLUS|HDR10|DOVI|HDR|SDR|HLG|DV)"
    r"(?=$|[^a-zA-Z0-9])",
    re.IGNORECASE,
)


def detect_dynamic_range(filename: str) -> Optional[str]:
    """
    Return the canonical uppercase dynamic range folder name (e.g. 'HDR', 'SDR')
    corresponding to the LAST dynamic range token in the filename stem, or None if none found.
    """
    stem = os.path.splitext(filename)[0]
    matches = list(DR_TOKEN_RE.finditer(stem))
    if not matches:
        return None
    last_raw = matches[-1].group(1).upper()
    return DR_CANONICAL_MAP.get(last_raw)


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
                # Avoid recursing into existing dynamic range subfolders
                if entry.name.lower() not in KNOWN_DR_FOLDERS:
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
            if not base.is_absolute():
                base = Path.cwd() / base
            if base.is_dir():
                scan_dir(base)
                continue

        # Wildcard patterns like *.mkv, *.mp4, etc.
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
        description="Sort files into dynamic range subfolders (HDR, SDR, etc.) based on filename tags."
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
        help="Recursively scan subdirectories (skips existing dynamic range folders).",
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

        dr_folder = detect_dynamic_range(src.name)
        if not dr_folder:
            skipped_unmatched += 1
            continue

        dest_dir = src.parent / dr_folder
        dest_file = dest_dir / src.name

        if dest_file.exists():
            print(f"[SKIP - EXISTS] {src.name} -> {dr_folder}/{src.name} already exists")
            skipped_collision += 1
            continue

        if args.dry_run:
            if dest_dir not in created_folders and not dest_dir.exists():
                print(f"[DRY RUN] Would create folder: {dr_folder}/")
                created_folders.add(dest_dir)
            print(f"[DRY RUN] {src.name} -> {dr_folder}/")
            moved_count += 1
        else:
            if not dest_dir.exists():
                try:
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    if dest_dir not in created_folders:
                        print(f"[CREATED] {dr_folder}/")
                        created_folders.add(dest_dir)
                except OSError as e:
                    print(f"[ERROR] Failed to create folder {dest_dir}: {e}", file=sys.stderr)
                    continue

            try:
                shutil.move(str(src), str(dest_file))
                print(f"[MOVED] {src.name} -> {dr_folder}/")
                moved_count += 1
            except (OSError, shutil.Error) as e:
                print(f"[ERROR] Could not move {src.name}: {e}", file=sys.stderr)

    print("-" * 60)
    action_word = "Would move" if args.dry_run else "Moved"
    summary = f"Done! {action_word} {moved_count} file(s) into dynamic range folder(s). Left {skipped_unmatched} unmatched file(s) untouched."
    if skipped_collision:
        summary += f" Skipped {skipped_collision} existing file(s)."
    print(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
