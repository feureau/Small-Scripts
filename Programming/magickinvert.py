#!/usr/bin/env python3
"""
magickinvert.py
Inverts all images (negative -> positive) using ImageMagick.

Overwrites originals by default. Use --copy to save as *_inverted.* instead.

Usage:
    python /path/to/magickinvert.py                  # all images, recursive (in-place)
    python /path/to/magickinvert.py *.png            # shell-expanded list
    python /path/to/magickinvert.py "**/*.jpg"       # quoted glob, all subdirs
    python /path/to/magickinvert.py --copy *.tif     # save copies instead
    python /path/to/magickinvert.py --dry-run        # preview only
"""

import os
import sys
import glob
import argparse
import subprocess
import platform
from pathlib import Path

# Supported image extensions
IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".tif", ".tiff",
    ".bmp", ".gif", ".webp", ".heic", ".heif",
    ".ppm", ".pgm", ".pbm", ".pnm", ".ico",
}

OUTPUT_SUFFIX = "_inverted"

# On Windows, 'convert' is a built-in disk utility — must use 'magick' instead.
# On Linux/macOS, 'magick' also works for ImageMagick 7+, falling back to 'convert' for v6.
def get_imagemagick_cmd() -> list[str]:
    if platform.system() == "Windows":
        return ["magick"]
    # On Linux/macOS try 'magick' first (IM7), fall back to 'convert' (IM6)
    try:
        result = subprocess.run(["magick", "--version"], capture_output=True)
        if result.returncode == 0:
            return ["magick"]
    except FileNotFoundError:
        pass
    return ["convert"]


def find_images_recursive(root: Path) -> list[Path]:
    """Recursively find all supported image files under root."""
    images = []
    for dirpath, _, filenames in os.walk(root):
        for filename in filenames:
            p = Path(dirpath) / filename
            if p.suffix.lower() in IMAGE_EXTENSIONS:
                if OUTPUT_SUFFIX not in p.stem:
                    images.append(p)
    return sorted(images)


def resolve_patterns(patterns: list[str]) -> list[Path]:
    """
    Resolve a list of file paths or glob patterns to a deduplicated list of Paths.
    Works whether the shell already expanded wildcards (e.g. *.png -> file1.png file2.png)
    or whether they were quoted and passed as-is (e.g. "**/*.png").
    """
    seen = set()
    images = []

    for pattern in patterns:
        matches = glob.glob(pattern, recursive=True)

        if not matches:
            p = Path(pattern)
            if p.exists():
                matches = [pattern]
            else:
                print(f"  [WARN] No files matched: {pattern}")
                continue

        for match in sorted(matches):
            p = Path(match).resolve()
            if p in seen:
                continue
            seen.add(p)
            if not p.is_file():
                continue
            if p.suffix.lower() not in IMAGE_EXTENSIONS:
                print(f"  [SKIP] Unsupported format: {p.name}")
                continue
            if OUTPUT_SUFFIX in p.stem:
                print(f"  [SKIP] Already inverted: {p.name}")
                continue
            images.append(p)

    return images


def invert_image(src: Path, im_cmd: list[str], copy: bool, dry_run: bool) -> bool:
    """
    Invert a single image using ImageMagick -negate.
    Returns True on success, False on failure.
    """
    dest = src.with_stem(src.stem + OUTPUT_SUFFIX) if copy else src

    # ImageMagick syntax: magick input -negate output
    cmd = im_cmd + [str(src), "-negate", str(dest)]

    if dry_run:
        action = "copy" if copy else "overwrite"
        print(f"  [dry-run] ({action}) {src.name}  ->  {dest.name}")
        return True

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            print(f"  [ERROR] {src.name}\n    {result.stderr.strip()}")
            return False
        if copy:
            print(f"  [OK]  {src.name}  ->  {dest.name}")
        else:
            print(f"  [OK]  {src.name}  (overwritten)")
        return True
    except FileNotFoundError:
        print("\n[FATAL] ImageMagick not found.")
        print("Install it from: https://imagemagick.org/script/download.php")
        print("  Windows : winget install ImageMagick.ImageMagick")
        print("  macOS   : brew install imagemagick")
        print("  Linux   : sudo apt install imagemagick")
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print(f"  [TIMEOUT] {src.name}")
        return False


def check_imagemagick(im_cmd: list[str]):
    """Verify ImageMagick is installed before processing."""
    try:
        result = subprocess.run(im_cmd + ["--version"], capture_output=True, text=True)
        if result.returncode == 0:
            version_line = result.stdout.splitlines()[0] if result.stdout else "unknown"
            print(f"ImageMagick detected: {version_line}")
    except FileNotFoundError:
        print(f"[FATAL] ImageMagick not found (tried: {' '.join(im_cmd)}).")
        print("Install it from: https://imagemagick.org/script/download.php")
        print("  Windows : winget install ImageMagick.ImageMagick")
        print("  macOS   : brew install imagemagick")
        print("  Linux   : sudo apt install imagemagick")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Invert images (negative film -> positive) using ImageMagick. Overwrites originals by default.",
        epilog=(
            "Examples:\n"
            "  magickinvert.py                  # all images in tree, overwrite\n"
            "  magickinvert.py *.png            # specific files (shell expands)\n"
            '  magickinvert.py "**/*.jpg"       # quoted glob, all subdirs\n'
            "  magickinvert.py --copy *.tif     # save as *_inverted.tif instead\n"
            "  magickinvert.py --dry-run        # preview only"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "patterns",
        nargs="*",
        help=(
            "Files or glob patterns to process (e.g. *.png or \"**/*.jpg\"). "
            "Omit to process ALL supported images recursively from the current folder."
        ),
    )
    parser.add_argument(
        "--copy", "-c",
        action="store_true",
        help="Save inverted files as *_inverted.* copies instead of overwriting originals.",
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Show what would be done without actually processing anything.",
    )
    args = parser.parse_args()

    im_cmd = get_imagemagick_cmd()
    cwd = Path.cwd()

    mode_label = (
        "DRY RUN" if args.dry_run
        else ("save as *_inverted.* (copy)" if args.copy else "overwrite originals (in-place)")
    )
    scope_label = (
        ", ".join(args.patterns) if args.patterns
        else "all supported images (recursive)"
    )

    print(f"\n{'='*60}")
    print(f"  magickinvert.py")
    print(f"  Working folder : {cwd}")
    print(f"  Scope          : {scope_label}")
    print(f"  Mode           : {mode_label}")
    print(f"  ImageMagick    : {' '.join(im_cmd)}")
    print(f"{'='*60}\n")

    check_imagemagick(im_cmd)

    if args.patterns:
        images = resolve_patterns(args.patterns)
    else:
        images = find_images_recursive(cwd)

    if not images:
        print("No supported image files found.")
        sys.exit(0)

    print(f"\nFound {len(images)} image(s):\n")

    ok = fail = 0
    for img in images:
        success = invert_image(img, im_cmd=im_cmd, copy=args.copy, dry_run=args.dry_run)
        if success:
            ok += 1
        else:
            fail += 1

    print(f"\n{'='*60}")
    if args.dry_run:
        print(f"  Dry run complete -- {ok} file(s) would be processed.")
    else:
        print(f"  Done -- {ok} succeeded, {fail} failed.")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
