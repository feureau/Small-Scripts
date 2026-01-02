"""###############################################################################
Image Conversion Script - GIMP/XCF/RAW/JPG Batch Converter
-------------------------------------------------------------------------------
Version: 2.1.0 (2025-12-31)

PURPOSE:
    This script batch-converts images of many types (including GIMP 3 `.xcf` files)
    into `.jpg` files, using ImageMagick 7's `magick` CLI tool.

    It is designed to:
        • Handle GIMP `.xcf` files by automatically flattening with a white background.
        • Convert PSD, PSB, PNG with alpha, PDF, SVG, RAW, HDR, and more.
        • Output results to a dedicated `jpg/` subfolder, leaving originals untouched.
        • Allow quality, density, interlacing, profile stripping, resizing, etc.
        • Parallelize processing using a Mission Control Dashboard for real-time status.

IMPORTANT:
    ▸ This documentation MUST be kept at the top of the file and updated with every
      future revision. Include update history, rationale for changes, and reasoning.

DEPENDENCIES:
    ▸ Python 3.x
    ▸ ImageMagick 7.x (must be available in PATH as `magick`)
    ▸ Delegates for RAW (dcraw/libraw) if RAW support is needed.

USAGE:
    python convert_to_jpg.py [-q 85] [-d 300] [-i plane] [-s] [-r 1920x1080] \
                             [-j 4] [--profile sRGB.icc] [pattern]

ARGUMENTS:
    pattern: optional glob pattern (defaults to all supported image types)
    -q / --quality: JPEG quality (1–100)
    -d / --density: Density for vector formats (PDF/SVG)
    -i / --interlace: Interlace mode (none, line, plane, partition)
    -s / --strip: Strip metadata (EXIF, profiles)
    -r / --resize: Resize to WxH or percentage (e.g. 50%)
    -j / --jobs: Number of parallel jobs (default: auto, uses all cores)
    --sampling-factor: e.g. 4:2:0
    --profile: Path to ICC color profile to apply

SUPPORTED INPUT FORMATS:
    Web & Standard: PNG, JPEG, JPG, WEBP, BMP, TIFF, GIF
    Editable: XCF, PSD, PSB, ORA (flattened)
    Vector: SVG, EPS, PDF (first page rasterized)
    Camera RAW: CR2, CR3, NEF, ARW, RW2, DNG, RAF, SRW, ORF, KDC, PEF, IIQ
    HDR: EXR, HDR

WHY WE USE `magick input output` INSTEAD OF `mogrify`:
    • `mogrify` overwrites originals — not safe for destructive batch jobs.
    • This approach lets us control per-file output path (to `jpg/` folder).
    • Ensures flattening works per file (needed for XCF/PSD with transparency).

HISTORY:
-------------------------------------------------------------------------------
2025-12-31 (v2.1.0):
    ▸ Added parallel processing using `ProcessPoolExecutor`.
    ▸ Implemented "Mission Control Dashboard" for real-time, flicker-free status tracking.
    ▸ Added `-j` / `--jobs` argument to control parallelism.
    ▸ Added detailed batch summary report upon completion.

2025-09-22 (v2.0.0):
    ▸ Full rewrite by ChatGPT per Feureau request.
    ▸ Added `.xcf` support and automatic flattening.
    ▸ Switched from `mogrify` to `magick input output` style for safety.
    ▸ Added expanded format list (RAW, HDR, vector).
    ▸ Added detailed documentation block with history + rationale.
"""

import argparse
import glob
import os
import subprocess
import sys
import time
import threading
import multiprocessing
import shutil
import io
from concurrent.futures import ProcessPoolExecutor, as_completed

# ==========================================
# GLOBAL CONFIGURATION
# ==========================================
DEFAULT_QUALITY = 65
DEFAULT_DENSITY = None         # e.g. 300 for vector rasterization
DEFAULT_INTERLACE = "plane"    # choices: none, line, plane, partition
DEFAULT_STRIP = False
DEFAULT_RESIZE = None          # e.g. "1920x1080" or "50%"
DEFAULT_SAMPLING_FACTOR = "4:2:0"
DEFAULT_PROFILE = None         # Path to ICC profile
DEFAULT_JOBS = "auto"          # "auto" uses all cores, or specify integer
DEFAULT_BACKGROUND = "white"   # Safe for transparency/GIMP/PSD
DEFAULT_OUTPUT_FOLDER = "jpg"

# Supported input formats removed from here and moved to GLOBAL CONFIGURATION
# ==========================================

# --- ANSI Constants ---
C_UP = "\033[F"      # Move cursor to start of previous line
C_CLEAR = "\033[K"   # Clear line from cursor to end
C_HIDE = "\033[?25l" # Hide cursor
C_SHOW = "\033[?25h" # Show cursor

if os.name == 'nt':
    os.system('') # Enable ANSI on Windows

def get_size_format(b, factor=1024, suffix="B"):
    if b == 0: return "0 B"
    for unit in ["", "K", "M", "G", "T", "P"]:
        if abs(b) < factor:
            if unit == "": return f"{b:.0f} {suffix}"
            return f"{b:.2f} {unit}{suffix}"
        b /= factor

# Supported input formats (extensions must be lowercase)
SUPPORTED_EXTENSIONS = [
    '.png', '.jpeg', '.jpg', '.webp', '.bmp', '.tiff', '.tif', '.gif',
    '.heic', '.heif', '.psd', '.psb', '.xcf', '.ora',
    '.svg', '.eps', '.pdf',
    '.cr2', '.cr3', '.nef', '.arw', '.rw2', '.dng', '.raf', '.srw', '.orf', '.kdc', '.pef', '.iiq',
    '.exr', '.hdr'
]

# --- UI Controller (The Painter) ---

class DashboardPainter:
    def __init__(self, worker_count, total_tasks):
        self.worker_count = worker_count
        self.total_tasks = total_tasks
        self.completed_tasks = 0
        self.shared_state = None 
        self.log_queue = multiprocessing.Queue()
        self.running = True
        self.last_height = 0
        self.term_width = 80 # Default
        self._set_term_size()

    def _set_term_size(self):
        self.term_width = shutil.get_terminal_size((80, 20)).columns

    def start(self, shared_dict):
        self.shared_state = shared_dict
        sys.stdout.write(C_HIDE)
        sys.stdout.flush()
        self.thread = threading.Thread(target=self._painter_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        self.thread.join()
        # Final flush
        while not self.log_queue.empty():
            sys.stdout.write("\r" + C_CLEAR + self.log_queue.get() + "\n")
        sys.stdout.write(C_SHOW)
        sys.stdout.flush()

    def add_log(self, text):
        self.log_queue.put(text)

    def _clear_dashboard(self):
        """Erases the previously drawn dashboard lines."""
        if self.last_height > 0:
            sys.stdout.write(f"\r{C_UP}{C_CLEAR}" * self.last_height)
            sys.stdout.flush()

    def _painter_loop(self):
        while self.running:
            self._set_term_size()
            
            # 1. Handle Log Queue
            while not self.log_queue.empty():
                log_block = self.log_queue.get()
                self._clear_dashboard()
                self.last_height = 0
                sys.stdout.write(log_block)
                if not log_block.endswith("\n"): sys.stdout.write("\n")
                sys.stdout.flush()

            # 2. Draw Dashboard
            lines = []
            sep = "-" * self.term_width
            lines.append(sep)
            
            pct = (self.completed_tasks / self.total_tasks * 100) if self.total_tasks > 0 else 0
            bar_w = min(60, self.term_width - 30)
            filled = int(bar_w * pct / 100) if bar_w > 0 else 0
            bar = f"[{'#' * filled}{'.' * (bar_w - filled)}]" if bar_w > 0 else ""
            lines.append(f"GLOBAL PROGRESS: {bar} {pct:3.0f}% | {self.completed_tasks}/{self.total_tasks}")
            lines.append(sep)

            # Worker Grid
            worker_items = list(self.shared_state.items())
            worker_items.sort()
            
            if self.worker_count > 8:
                mid = (len(worker_items) + 1) // 2
                left_col = worker_items[:mid]
                right_col = worker_items[mid:]
                col_w = self.term_width // 2 - 2
                
                for i in range(mid):
                    l_id, l_msg = left_col[i]
                    r_id, r_msg = right_col[i] if i < len(right_col) else ("", "")
                    l_part = f"[{l_id:^7}] {l_msg[:col_w-10]:<{col_w-10}}"
                    r_part = f"[{r_id:^7}] {r_msg[:col_w-10]:<{col_w-10}}"
                    lines.append(f"{l_part} | {r_part}")
            else:
                for w_id, w_msg in worker_items:
                    lines.append(f"[{w_id:^7}] {w_msg[:self.term_width-11]}")

            lines.append("=" * self.term_width)

            self._clear_dashboard()
            output = "\n".join(lines) + "\n"
            sys.stdout.write(output)
            sys.stdout.flush()
            self.last_height = len(lines)
            
            time.sleep(0.1)

# --- Parallel Workers ---

def convert_worker(payload):
    """
    Processes a single file conversion.
    Payload: (worker_id, input_file, output_file, magick_command, shared_state)
    """
    w_id, input_file, output_file, magick_command, shared_state = payload
    shared_state[w_id] = f"BUSY: {os.path.basename(input_file)}"
    
    start = time.time()
    try:
        o_sz = os.path.getsize(input_file)
        subprocess.run(magick_command, check=True, capture_output=True)
        n_sz = os.path.getsize(output_file)
        dur = time.time() - start
        
        red = ((o_sz - n_sz) / o_sz * 100) if o_sz > 0 else 0
        log = f" [OK] {os.path.basename(input_file)} -> {get_size_format(n_sz)} | {dur:.2f}s | {red:+.2f}%"
        
        shared_state[w_id] = "IDLE - Task Done"
        return True, o_sz, n_sz, log, os.path.basename(input_file)
    except Exception as e:
        shared_state[w_id] = f"ERROR: {os.path.basename(input_file)}"
        error_msg = f"[!] Error converting {input_file}: {e}"
        return False, 0, 0, error_msg, os.path.basename(input_file)

def main():
    parser = argparse.ArgumentParser(description="Convert images to JPG using ImageMagick")
    parser.add_argument("patterns", nargs="*", help="Glob pattern(s) or file paths (default: all supported types)")
    parser.add_argument("-q", "--quality", type=int, default=DEFAULT_QUALITY, help="JPEG quality (1-100)")
    parser.add_argument("-d", "--density", type=int, default=DEFAULT_DENSITY, help="Density (DPI) for vector formats")
    parser.add_argument("-i", "--interlace", choices=["none", "line", "plane", "partition"], default=DEFAULT_INTERLACE, help="JPEG interlace mode")
    parser.add_argument("-s", "--strip", action="store_true" if not DEFAULT_STRIP else "store_false", help="Strip metadata and profiles")
    parser.add_argument("-r", "--resize", default=DEFAULT_RESIZE, help="Resize geometry (e.g. 1920x1080, 50%%)")
    parser.add_argument("--sampling-factor", default=DEFAULT_SAMPLING_FACTOR, help="Chroma subsampling factor (e.g. 4:2:0)")
    parser.add_argument("--profile", default=DEFAULT_PROFILE, help="Path to ICC color profile")
    parser.add_argument("-j", "--jobs", default=DEFAULT_JOBS, help="Number of parallel jobs (default: auto)")
    args = parser.parse_args()

    # Build file list
    # Filter out potential empty strings from Windows shell/registry associations
    valid_patterns = [p for p in args.patterns if p.strip()] if args.patterns else []

    if valid_patterns:
        input_files = []
        for p in valid_patterns:
            input_files.extend(glob.glob(p))
    else:
        input_files = []
        for ext in SUPPORTED_EXTENSIONS:
            input_files.extend(glob.glob(f"*{ext}"))

    if not input_files:
        print("No matching input files found.")
        sys.exit(1)

    jpg_folder_path = os.path.join(os.getcwd(), DEFAULT_OUTPUT_FOLDER)
    os.makedirs(jpg_folder_path, exist_ok=True)

    sys_cores = os.cpu_count() or 1
    max_workers = int(args.jobs) if args.jobs != "auto" else sys_cores

    # Initialize Shared UI State
    manager = multiprocessing.Manager()
    shared_dict = manager.dict()
    for i in range(1, max_workers + 1):
        shared_dict[f"W{i:02}"] = "IDLE - Waiting for task"

    print("=" * 80)
    print(f"IMAGE CONVERSION ENGINE (v2.1.0)")
    print("-" * 80)
    print(f"Workload: {len(input_files)} files | Parallelism: {max_workers} Cores")
    print("-" * 80)

    painter = DashboardPainter(max_workers, len(input_files))
    painter.start(shared_dict)

    total_o, total_n, processed_count = 0, 0, 0
    file_results = []
    start_batch = time.time()

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for i, input_file in enumerate(input_files):
            base_name = os.path.splitext(os.path.basename(input_file))[0]
            output_file = os.path.join(jpg_folder_path, f"{base_name}.jpg")

            magick_command = ["magick", input_file]

            if args.quality is not None:
                magick_command.extend(["-quality", str(args.quality)])

            # Always flatten with background (safe for alpha, xcf, psd)
            magick_command.extend(["-background", DEFAULT_BACKGROUND, "-flatten"])

            if args.sampling_factor:
                magick_command.extend(["-sampling-factor", args.sampling_factor])
            if args.density:
                magick_command.extend(["-density", str(args.density)])
            if args.interlace:
                magick_command.extend(["-interlace", args.interlace])
            if args.strip:
                magick_command.append("-strip")
            if args.profile:
                magick_command.extend(["-profile", args.profile])
            if args.resize:
                magick_command.extend(["-resize", args.resize])

            magick_command.append(output_file)

            w_id = f"W{ (i % max_workers) + 1:02}"
            payload = (w_id, input_file, output_file, magick_command, shared_dict)
            futures.append(executor.submit(convert_worker, payload))

        for fut in as_completed(futures):
            suc, o_sz, n_sz, log_data, f_name = fut.result()
            painter.add_log(log_data)
            painter.completed_tasks += 1
            if suc:
                total_o += o_sz
                total_n += n_sz
                processed_count += 1
                file_results.append((f_name, o_sz, n_sz))

    painter.stop()

    # Batch Summary Report
    dur = time.time() - start_batch
    red = ((total_o - total_n) / total_o * 100) if total_o > 0 else 0
    
    print("\n" + "=" * 80)
    print(f"{'IMAGE CONVERSION BATCH REPORT':^80}")
    print("-" * 80)
    print(f"{'Filename':<40} | {'Original':>12} | {'New Size':>12} | {'Savings':>8}")
    print("-" * 80)
    for f_name, o, n in sorted(file_results):
        s_red = ((o - n) / o * 100) if o > 0 else 0
        print(f"{f_name:<40.40} | {get_size_format(o):>12} | {get_size_format(n):>12} | {s_red:>7.2f}%")
    
    print("-" * 80)
    print(f"Files Processed: {processed_count} / {len(input_files)}")
    print(f"Total Original:  {get_size_format(total_o)}")
    print(f"Total New Size:  {get_size_format(total_n)}")
    print(f"Total Savings:   {get_size_format(total_o - total_n)} (-{red:.2f}%)")
    print(f"Total Time:      {dur:.2f}s")
    print("=" * 80)

if __name__ == "__main__":
    main()