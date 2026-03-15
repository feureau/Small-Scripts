"""###############################################################################
to_jp2.py — Lossless JP2 Archival Batch Converter
-------------------------------------------------------------------------------
Version: 1.0.0 (2026-03-16)

PURPOSE:
    Batch-converts images to lossless JPEG2000 (.jp2) for archival use.
    Built around the constraints of JPEG2000 — not retrofitted from a
    general-purpose converter.

DESIGN PRINCIPLES:
    • JP2 lossless only. No lossy mode, no quality knobs.
    • Exposes ImageMagick's stderr on failure so you can actually debug it.
    • Preflight-checks that JP2 *write* support exists before processing anything
      (many ImageMagick builds lack the OpenJPEG delegate entirely).
    • Strips alpha and flattens before encode — JP2 with an alpha channel
      produces 4-component sRGB files that most viewers cannot open.
    • Never passes -interlace or -sampling-factor to JP2 (JPEG concepts,
      not JPEG2000 concepts — previous scripts were broken by both of these).
    • Uses the explicit JP2: output prefix so ImageMagick selects the right codec.
    • Parallel processing with clean per-file status output.

DEPENDENCIES:
    • Python 3.8+
    • ImageMagick 7.x with OpenJPEG delegate (verify: `magick -list format | grep JP2`)

USAGE:
    python to_jp2.py [OPTIONS] [PATTERN ...]

    Convert all supported images in current directory:
        python to_jp2.py

    Convert specific files or glob patterns:
        python to_jp2.py *.png *.tiff

    Recurse into subdirectories:
        python to_jp2.py -R

    Use 4 parallel workers:
        python to_jp2.py -j 4

    Resize to 4000px wide (long edge) before encoding:
        python to_jp2.py --resize 4000x4000>

OPTIONS:
    -j / --jobs     Parallel workers (default: 1, 'auto' = all CPU cores)
    -R / --recursive  Recurse into subdirectories
    -d / --density  DPI for rasterising vector/PDF inputs (default: 300)
    --resize        ImageMagick geometry string applied before encode
                    e.g. '4000x4000>' shrinks to fit 4000px, never upscales
    --strip         Strip EXIF / ICC metadata from output
    --background    Background colour for alpha compositing (default: white)
    --threads       ImageMagick internal thread limit per process (default: auto)
    --output-dir    Override output directory (default: ./jp2)

HISTORY:
-------------------------------------------------------------------------------
2026-03-16 (v1.0.0):
    ▸ Initial release. Rebuilt from scratch for JP2-only archival use.
    ▸ Removed all JPEG-specific flags (-interlace, -sampling-factor) that
      were silently corrupting JP2 output in the previous general converter.
    ▸ Added preflight JP2 write-support check.
    ▸ Replaced capture_output=True (hid IM errors) with explicit stderr capture
      that is printed on failure so failures are actually debuggable.
    ▸ Used explicit JP2: output prefix for reliable codec selection.
"""

import argparse
import glob
import multiprocessing
import os
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

# ---------------------------------------------------------------------------
# Configuration defaults
# ---------------------------------------------------------------------------

DEFAULT_JOBS        = 1
DEFAULT_THREADS     = "auto"
DEFAULT_DENSITY     = 300        # DPI used when rasterising PDF/SVG/EPS
DEFAULT_BACKGROUND  = "white"    # Composited under transparent pixels before encode
DEFAULT_OUTPUT_DIR  = "jp2"

SUPPORTED_EXTENSIONS = [
    # Raster
    ".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".webp", ".gif",
    ".heic", ".heif",
    # Layered / editable
    ".psd", ".psb", ".xcf", ".ora",
    # Vector / document (rasterised at --density DPI)
    ".svg", ".eps", ".pdf",
    # Camera RAW
    ".cr2", ".cr3", ".nef", ".arw", ".rw2", ".dng",
    ".raf", ".srw", ".orf", ".kdc", ".pef", ".iiq",
    # HDR
    ".exr", ".hdr",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def fmt_bytes(b):
    if b == 0:
        return "0 B"
    for unit in ("B", "KB", "MB", "GB"):
        if abs(b) < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} TB"


def preflight():
    """
    Verify that `magick` is available and has JP2 *write* support.
    Exits with a clear diagnostic if either check fails.
    """
    # 1. Is magick on PATH?
    result = subprocess.run(
        ["magick", "--version"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print("ERROR: `magick` not found on PATH.")
        print("       Install ImageMagick 7.x: https://imagemagick.org/script/download.php")
        sys.exit(1)

    # 2. Does this build have the OpenJPEG delegate for JP2 write?
    fmt_result = subprocess.run(
        ["magick", "-list", "format"],
        capture_output=True, text=True
    )
    lines = fmt_result.stdout.splitlines()

    # We need a line that mentions JP2 and includes 'w' (write) in the mode column.
    # Format list columns: "  JP2  JPEG-2000 File Interchange  rw-  ..."
    jp2_write = False
    for line in lines:
        stripped = line.strip()
        if not stripped.upper().startswith("JP2"):
            continue
        # The mode field is the 3rd token (e.g. "rw-" or "r--")
        parts = stripped.split()
        if len(parts) >= 3 and "w" in parts[2].lower():
            jp2_write = True
            break

    if not jp2_write:
        print("ERROR: Your ImageMagick build does not have JP2 write support.")
        print()
        print("  To verify yourself:  magick -list format | grep JP2")
        print("  You need a line like:  JP2  JPEG-2000 ...  rw-")
        print()
        print("  Fix options:")
        print("  • Linux:   sudo apt install libopenjp2-7-dev  then rebuild ImageMagick,")
        print("             OR install a pre-built version that includes OpenJPEG:")
        print("             https://imagemagick.org/script/download.php")
        print("  • macOS:   brew install imagemagick  (includes OpenJPEG by default)")
        print("  • Windows: use the official installer with 'Install legacy utilities' checked")
        sys.exit(1)

    # Print the IM version line for reference
    version_line = next((l.strip() for l in result.stdout.splitlines() if "ImageMagick" in l), "")
    print(f"ImageMagick: {version_line}")
    print("JP2 write support: OK")


# ---------------------------------------------------------------------------
# Command builder
# ---------------------------------------------------------------------------

def build_command(input_file, output_file, args):
    """
    Constructs the magick command list for a single file.

    JP2-specific rules applied here:
      • -quality 0           → lossless (OpenJPEG semantics via ImageMagick)
      • -define jp2:rate=1.0 → lossless compression ratio (belt-and-suspenders)
      • -alpha off           → remove alpha AFTER flattening; prevents 4-component
                               sRGB files that most JP2 viewers cannot open
      • NO -interlace        → JPEG concept, not JPEG2000; passing it corrupts output
      • NO -sampling-factor  → chroma subsampling is a JPEG concept, not JPEG2000
      • JP2: prefix          → explicitly selects the JP2 codec, not inferred from ext
    """
    cmd = ["magick"]

    # Thread limit (per-process ImageMagick parallelism)
    if str(args.threads).lower() != "auto":
        cmd += ["-limit", "thread", str(args.threads)]

    # Density for vector / PDF rasterisation (ignored for raster inputs)
    cmd += ["-density", str(args.density)]

    cmd.append(input_file)

    # Flatten all layers onto a solid background, then kill alpha.
    # Order matters: flatten first (composites layers), then alpha off.
    cmd += ["-background", args.background, "-flatten", "-alpha", "off"]

    # Optional resize (applied after flatten, before encode)
    if args.resize:
        cmd += ["-resize", args.resize]

    # Strip metadata if requested
    if args.strip:
        cmd.append("-strip")

    # JP2 lossless encode flags
    cmd += [
        "-quality", "0",           # 0 = lossless in ImageMagick's OpenJPEG interface
        "-define", "jp2:rate=1.0", # Explicitly request lossless compression ratio
    ]

    # Explicit JP2: prefix tells ImageMagick which codec to use
    cmd.append(f"JP2:{output_file}")

    return cmd


# ---------------------------------------------------------------------------
# Worker (runs in a separate process)
# ---------------------------------------------------------------------------

def convert_worker(payload):
    """
    Converts one file. Returns a result tuple:
        (success, input_path, output_path, orig_bytes, new_bytes, elapsed, error_msg)
    """
    input_file, output_file, cmd = payload

    t0 = time.time()
    orig_size = os.path.getsize(input_file)

    result = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.time() - t0

    if result.returncode != 0:
        # Include ImageMagick's actual error message so the user can debug it
        err = result.stderr.strip() or result.stdout.strip() or "(no output from magick)"
        return (False, input_file, output_file, orig_size, 0, elapsed, err)

    if not os.path.exists(output_file):
        return (False, input_file, output_file, orig_size, 0, elapsed,
                "magick exited 0 but output file was not created")

    new_size = os.path.getsize(output_file)
    return (True, input_file, output_file, orig_size, new_size, elapsed, "")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Batch-convert images to lossless JP2 for archival use.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "patterns", nargs="*",
        help="Glob pattern(s) or file paths. Default: all supported types in current dir."
    )
    parser.add_argument("-j", "--jobs", default=DEFAULT_JOBS,
        help=f"Parallel workers (default: {DEFAULT_JOBS}, 'auto' = all CPU cores)")
    parser.add_argument("-R", "--recursive", action="store_true",
        help="Recurse into subdirectories")
    parser.add_argument("-d", "--density", type=int, default=DEFAULT_DENSITY,
        help=f"DPI for rasterising vector/PDF inputs (default: {DEFAULT_DENSITY})")
    parser.add_argument("--resize", default=None,
        help="ImageMagick geometry applied before encode, e.g. '4000x4000>'")
    parser.add_argument("--strip", action="store_true",
        help="Strip EXIF / ICC metadata from output")
    parser.add_argument("--background", default=DEFAULT_BACKGROUND,
        help=f"Background colour for alpha compositing (default: {DEFAULT_BACKGROUND})")
    parser.add_argument("--threads", default=DEFAULT_THREADS,
        help="ImageMagick internal threads per process (default: auto)")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory (default: ./{DEFAULT_OUTPUT_DIR})")
    args = parser.parse_args()

    # --- Preflight ---
    preflight()
    print()

    # --- Collect input files ---
    input_files = []

    if args.recursive:
        patterns = args.patterns or [f"*{ext}" for ext in SUPPORTED_EXTENSIONS]
        for p in patterns:
            base = p if "**" in p else os.path.join("**", p)
            input_files.extend(glob.glob(base, recursive=True))
        # If no patterns given, recursive scan for all supported exts
        if not args.patterns:
            input_files = []
            for ext in SUPPORTED_EXTENSIONS:
                input_files.extend(glob.glob(os.path.join("**", f"*{ext}"), recursive=True))
    else:
        if args.patterns:
            for p in args.patterns:
                input_files.extend(glob.glob(p))
        else:
            for ext in SUPPORTED_EXTENSIONS:
                input_files.extend(glob.glob(f"*{ext}"))

    # Deduplicate, normalise, sort
    input_files = sorted(set(os.path.normpath(f) for f in input_files))

    if not input_files:
        print("No matching input files found.")
        sys.exit(1)

    # --- Set up output directory ---
    output_dir = os.path.abspath(args.output_dir)
    os.makedirs(output_dir, exist_ok=True)

    # --- Resolve worker count ---
    if str(args.jobs).lower() == "auto":
        max_workers = os.cpu_count() or 1
    else:
        max_workers = int(args.jobs)

    # --- Build job list ---
    jobs = []
    for f in input_files:
        base = os.path.splitext(os.path.basename(f))[0]
        out  = os.path.join(output_dir, f"{base}.jp2")
        cmd  = build_command(f, out, args)
        jobs.append((f, out, cmd))

    # --- Print run summary ---
    print("=" * 72)
    print(f"  to_jp2.py  —  Lossless JP2 Archival Converter  (v1.0.0)")
    print("=" * 72)
    print(f"  Input files : {len(input_files)}")
    print(f"  Output dir  : {output_dir}")
    print(f"  Workers     : {max_workers}")
    print(f"  Density     : {args.density} DPI  (vector/PDF only)")
    if args.resize:
        print(f"  Resize      : {args.resize}")
    if args.strip:
        print(f"  Strip meta  : yes")
    print("-" * 72)
    print()

    # --- Process ---
    results = []
    t_batch = time.time()

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        future_map = {executor.submit(convert_worker, j): j for j in jobs}
        done = 0
        for future in as_completed(future_map):
            done += 1
            r = future.result()
            success, inp, out, orig, new, elapsed, err = r
            results.append(r)

            name = os.path.basename(inp)
            pct  = done / len(jobs) * 100

            if success:
                ratio = new / orig if orig > 0 else 1
                print(f"  [{done:>{len(str(len(jobs)))}}/{len(jobs)}]  OK   "
                      f"{name}  →  {fmt_bytes(new)}  ({ratio:.2%} of orig)  {elapsed:.1f}s")
            else:
                print(f"  [{done:>{len(str(len(jobs)))}}/{len(jobs)}]  FAIL "
                      f"{name}")
                # Indent the actual IM error so it's easy to read
                for line in err.splitlines():
                    print(f"         {line}")

    # --- Batch summary ---
    batch_elapsed = time.time() - t_batch
    ok      = [r for r in results if r[0]]
    failed  = [r for r in results if not r[0]]
    tot_in  = sum(r[3] for r in ok)
    tot_out = sum(r[4] for r in ok)

    print()
    print("=" * 72)
    print(f"  Completed: {len(ok)} succeeded, {len(failed)} failed  —  {batch_elapsed:.1f}s total")
    if ok:
        print(f"  Input size : {fmt_bytes(tot_in)}")
        print(f"  Output size: {fmt_bytes(tot_out)}  ({tot_out/tot_in:.2%} of orig)" if tot_in else "")
    if failed:
        print()
        print("  Failed files:")
        for r in failed:
            print(f"    • {r[1]}")
    print("=" * 72)

    sys.exit(0 if not failed else 1)


if __name__ == "__main__":
    main()
