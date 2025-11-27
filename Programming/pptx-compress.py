#!/usr/bin/env python3
import os
import sys
import zipfile
import tempfile
import argparse
from PIL import Image

# ============================================================
#  USER-ADJUSTABLE DEFAULTS — EDIT THESE AS YOU LIKE
# ============================================================
DEFAULT_QUALITY    = 60      # JPEG quality (1–100)
DEFAULT_MAX_WIDTH  = 1920    # e.g., 1920 — or None to disable
DEFAULT_MAX_HEIGHT = 1080    # e.g., 1080 — or None to disable
DEFAULT_MAX_MPX    = 2.0     # e.g., 2.0 for ~2 megapixels — or None
DEFAULT_OVERWRITE  = False   # Replace original file? True/False
SKIP_SMALL_PIXELS  = 50_000  # Skip compressing icons/logos

# ============================================================
#  IMAGE RESIZING LOGIC
# ============================================================
def resize_if_needed(img, max_width, max_height, max_mpx):
    w, h = img.size

    # Limit by megapixels
    if max_mpx:
        mpx = (w * h) / 1_000_000
        if mpx > max_mpx:
            scale = (max_mpx * 1_000_000 / (w * h)) ** 0.5
            return img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    # Limit width
    if max_width and w > max_width:
        scale = max_width / w
        return img.resize((max_width, int(h * scale)), Image.LANCZOS)

    # Limit height
    if max_height and h > max_height:
        scale = max_height / h
        return img.resize((int(w * scale), max_height), Image.LANCZOS)

    return img


# ============================================================
#  IMAGE COMPRESSION LOGIC
# ============================================================
def compress_image(path, quality, max_width, max_height, max_mpx):
    try:
        img = Image.open(path)

        # Skip tiny images (icons, UI elements)
        if img.size[0] * img.size[1] < SKIP_SMALL_PIXELS:
            return

        # Detect transparency (avoid PNG → JPEG if transparent)
        has_transparency = (img.mode in ("RGBA", "LA"))

        # Resize first (if needed)
        img = resize_if_needed(img, max_width, max_height, max_mpx)

        # Convert PNG → JPEG when safe
        if path.lower().endswith(".png") and not has_transparency:
            img = img.convert("RGB")
            img.save(path, "JPEG", quality=quality, optimize=True)
            return

        # Standard JPEG save
        if img.mode in ("RGBA", "LA"):
            img = img.convert("RGB")

        img.save(path, "JPEG", quality=quality, optimize=True)

    except Exception as e:
        print(f"  [!] Could not compress image ({path}): {e}")


# ============================================================
#  COMPRESS A SINGLE PPTX
# ============================================================
def compress_pptx(pptx_path, args):
    print(f"\n[+] Processing: {pptx_path}")

    if not pptx_path.lower().endswith(".pptx"):
        print("  [!] Not a PPTX file.")
        return

    # Output file
    if args.overwrite:
        output_path = pptx_path
    else:
        base, ext = os.path.splitext(pptx_path)
        output_path = base + "_compressed.pptx"

    with tempfile.TemporaryDirectory() as tmpdir:

        # Extract
        with zipfile.ZipFile(pptx_path, "r") as z:
            z.extractall(tmpdir)

        # Compress images in ppt/media/
        media_dir = os.path.join(tmpdir, "ppt", "media")
        if os.path.exists(media_dir):
            for fname in os.listdir(media_dir):
                if fname.lower().endswith((".png", ".jpg", ".jpeg", ".tif", ".tiff")):
                    print(f"  → {fname}")
                    compress_image(
                        os.path.join(media_dir, fname),
                        args.quality,
                        args.max_width,
                        args.max_height,
                        args.max_mpx
                    )

        # Repack
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as outzip:
            for root, _, files in os.walk(tmpdir):
                for f in files:
                    abs_path = os.path.join(root, f)
                    rel_path = os.path.relpath(abs_path, tmpdir)
                    outzip.write(abs_path, rel_path)

    print(f"[✓] Saved: {output_path}")


# ============================================================
#  FIND PPTX IN FOLDER TREE
# ============================================================
def find_pptx(dir):
    matches = []
    for root, _, files in os.walk(dir):
        for f in files:
            if f.lower().endswith(".pptx"):
                matches.append(os.path.join(root, f))
    return matches


# ============================================================
#  ARGUMENT PARSER
# ============================================================
def parse_args():
    parser = argparse.ArgumentParser(description="PPTX compressor with resize options.")
    parser.add_argument("files", nargs="*", help="PPTX file(s). If omitted, auto-scan directories.")

    # Defaults inherited from the editable constants above:
    parser.add_argument("--quality", type=int, default=DEFAULT_QUALITY)
    parser.add_argument("--max-width", type=int, default=DEFAULT_MAX_WIDTH)
    parser.add_argument("--max-height", type=int, default=DEFAULT_MAX_HEIGHT)
    parser.add_argument("--max-mpx", type=float, default=DEFAULT_MAX_MPX)
    parser.add_argument("--overwrite", action="store_true", default=DEFAULT_OVERWRITE)

    return parser.parse_args()


# ============================================================
#  MAIN
# ============================================================
if __name__ == "__main__":
    args = parse_args()

    if args.files:
        for f in args.files:
            compress_pptx(f, args)
    else:
        print("[i] No input files supplied — scanning directory tree…")
        files = find_pptx(os.getcwd())
        if not files:
            print("[!] No PPTX files found.")
            sys.exit(0)
        for f in files:
            compress_pptx(f, args)
