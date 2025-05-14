#!/usr/bin/env python3
"""
sanitize_filenames.py

Place this script in a folder (e.g. "scripts/") and invoke it from any directory.
It will expand glob patterns you pass, sanitize filenames to include only letters, numbers, and spaces,
and then either rename files in-place or copy them into a specified output directory.

Usage:
  # Rename files in-place (default):
  python sanitize_filenames.py "*.txt" "data/*.csv"

  # Dry-run to see changes without modifying files:
  python sanitize_filenames.py -d "*.txt" "data/*.csv"

  # Copy sanitized files into a folder:
  python sanitize_filenames.py -o clean_files "*.txt" "data/*.csv"

  # Dry-run copy:
  python sanitize_filenames.py -d -o clean_files "*.txt" "data/*.csv"

  # Help:
  python sanitize_filenames.py -h
"""

import os
import re
import glob
import shutil
import argparse

# regex to match any character that is NOT A-Z, a-z, 0-9 or space
INVALID_CHARS = re.compile(r"[^A-Za-z0-9 ]+")

def sanitize_name(name: str) -> str:
    """
    Remove any invalid characters from `name`.
    """
    return INVALID_CHARS.sub("", name)


def process(patterns: list[str], execute: bool, output_dir: str | None) -> None:
    """
    For each glob pattern, find matching files and either rename them in-place or
    copy sanitized files into an output directory.

    :param patterns: List of glob patterns (e.g. ['*.jpg', 'data/*.png'])
    :param execute: If True, perform file operations; if False, only print planned actions.
    :param output_dir: Directory to copy sanitized files into. If None, files are renamed in-place.
    """
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    for pattern in patterns:
        for src in glob.glob(pattern):
            if not os.path.isfile(src):
                continue
            dirpath, filename = os.path.split(src)
            name, ext = os.path.splitext(filename)
            sanitized = sanitize_name(name)
            if sanitized != name:
                new_filename = sanitized + ext
                if output_dir:
                    dst = os.path.join(output_dir, new_filename)
                    action = "Copying"
                    if execute:
                        shutil.copy2(src, dst)
                else:
                    dst = os.path.join(dirpath, new_filename)
                    action = "Renaming"
                    if execute:
                        os.rename(src, dst)

                prefix = "" if execute else "[DRY-RUN] "
                print(f"{prefix}{action}: '{src}' -> '{dst}'")
            else:
                # No invalid characters; skip or echo
                print(f"No change required: '{src}'")


def main():
    parser = argparse.ArgumentParser(
        description="Sanitize filenames to include only letters, numbers, and spaces."
    )
    parser.add_argument(
        "patterns",
        nargs='+',
        help="Glob patterns for files to process (e.g. '*.mp3', 'photos/*.PNG')."
    )
    parser.add_argument(
        "-d", "--dry-run",
        action='store_true',
        help="Run in dry-run mode (no actual file modifications)."
    )
    parser.add_argument(
        "-o", "--output-dir",
        metavar="DIR",
        help="Copy sanitized files into specified directory instead of renaming in-place."
    )
    args = parser.parse_args()

    execute = not args.dry_run
    process(args.patterns, execute, args.output_dir)


if __name__ == "__main__":
    main()
