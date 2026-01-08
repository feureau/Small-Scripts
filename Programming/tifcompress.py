"""
# TIFF Compressor (Mission Control Dashboard Edition)

A professional-grade script for losslessly optimizing TIFF files.
Features a high-performance "Mission Control" Dashboard that provides 
real-time, flicker-free visualization of multi-core workloads.

## Maintenance Rule
> [!IMPORTANT]
> This documentation block MUST be included and updated with every revision or update of the script.

## Technical Structure & Rationale

### 1. Mission Control Dashboard (Centralized UI Painter)
- **Problem**: Parallel workers writing to stdout create a garbled mess.
- **Solution**: A dedicated "Painter" thread is the ONLY entity allowed to write 
  to the console. It draws a multi-line dashboard at the screen bottom using 
  ANSI escape sequences.

### 2. Thread-Safe State Management
- Workers are 100% silent. They update their status in a shared memory dictionary 
  managed by `multiprocessing.Manager`.

### 3. Dynamic Parallel Strategies
- **Batch mode**: Processes files in parallel (1 core per file).
- **Single Target**: Processes search variants in parallel (1 core per test).
- Both modes feed into the unified dashboard for real-time tracking.

## Usage
```powershell
python tifcompress.py . --best
```

## Requirements
- Python 3.x
- Pillow library (`pip install Pillow`)
"""

import os
import argparse
import sys
import time
import tempfile
import io
import threading
import multiprocessing
import shutil
import glob
from PIL import Image, __version__ as pil_version
from PIL import features
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed

# ==========================================
# GLOBAL CONFIGURATION
# ==========================================
DEFAULT_COMPRESSION = "tiff_deflate"
DEFAULT_PREDICTOR = 1
DEFAULT_LEVEL = 6
ALLOWED_EXTENSIONS = (".tif", ".tiff")
VERBOSE_OUTPUT = True
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
            # We move up and clear each line
            sys.stdout.write(f"\r{C_UP}{C_CLEAR}" * self.last_height)
            sys.stdout.flush()

    def _painter_loop(self):
        while self.running:
            self._set_term_size()
            
            # 1. Handle Logan Queue (Permanent Logs)
            has_logs = False
            while not self.log_queue.empty():
                log_block = self.log_queue.get()
                self._clear_dashboard()
                self.last_height = 0
                sys.stdout.write(log_block)
                if not log_block.endswith("\n"): sys.stdout.write("\n")
                sys.stdout.flush()
                has_logs = True

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

            # Worker Grid (2-column if many workers)
            worker_items = list(self.shared_state.items())
            worker_items.sort() # Ensure W01, W02...
            
            if self.worker_count > 8:
                # 2-column layout
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

            # Atomic Write
            self._clear_dashboard()
            output = "\n".join(lines) + "\n"
            sys.stdout.write(output)
            sys.stdout.flush()
            self.last_height = len(lines)
            
            time.sleep(0.1)

# --- Parallel Workers ---

def variant_worker(payload):
    """
    Tests a single variant.
    Payload: (worker_id, f_path, config, t_path, dpi, shared_state)
    """
    w_id, f_path, (comp, pred, lvl), t_path, dpi, shared_state = payload
    var_label = f"{comp}/P{pred}/L{lvl}"
    
    shared_state[w_id] = f"ENGAGED: {var_label}"
    start = time.time()
    try:
        with Image.open(f_path) as img:
            shared_state[w_id] = f"SAVING: {var_label}"
            sp = {"compression": comp, "predictor": pred, "dpi": dpi}
            if "deflate" in comp: sp["compress_level"] = lvl
            img.save(t_path, **sp)
            sz = os.path.getsize(t_path)
            dur = time.time() - start
            stats = f"      - {comp:18} | P{pred} | L{lvl:1} : {sz:,} bytes | {dur:.3f}s"
            shared_state[w_id] = f"IDLE - Just finished {comp}"
            return sz, dur, stats, (comp, pred, lvl)
    except Exception as e:
        shared_state[w_id] = f"ERROR: {var_label}"
        return float('inf'), 0, f"      [!] Failed {var_label}: {e}", None

def process_file_worker(payload):
    """
    Processes a file in batch mode.
    Payload: (worker_id, input_path, output_path, args, shared_state)
    """
    w_id, in_path, out_path, args, shared_state = payload
    shared_state[w_id] = f"BUSY: {in_path.name}"
    
    log = io.StringIO()
    start = time.time()
    o_sz = os.path.getsize(in_path)
    log.write(f"\n[•] TARGET: {in_path.name}\n")
    
    try:
        with Image.open(in_path) as img:
            dpi = img.info.get('dpi')
            os.makedirs(out_path.parent, exist_ok=True)
            
            if args.best:
                log.write(f"    Sub-task variant search...\n")
                variants = [
                    ("tiff_deflate", 1, 1), ("tiff_deflate", 1, 6), ("tiff_deflate", 2, 6),
                    ("tiff_deflate", 1, 9), ("tiff_deflate", 2, 9), ("tiff_adobe_deflate", 1, 9),
                    ("tiff_adobe_deflate", 2, 9), ("tiff_lzw", 1, 0), ("tiff_lzw", 2, 0)
                ]
                best_sz, best_cfg = float('inf'), None
                for i, cfg in enumerate(variants, 1):
                    shared_state[w_id] = f"{in_path.name[:15]}.. Testing {i}/9"
                    t_out = Path(tempfile.gettempdir()) / f"v_{w_id}_{i}.tif"
                    # Call the same logic, passing shared_state as None to keep it silent nested
                    sz, dur, stats, res_cfg = variant_worker((w_id, in_path, cfg, t_out, dpi, {}))
                    pct = ((o_sz - sz) / o_sz * 100) if o_sz > 0 else 0
                    log.write(f"{stats} | {pct:+.2f}%\n")
                    if sz < best_sz: best_sz, best_cfg = sz, res_cfg
                    if t_out.exists(): os.remove(t_out)
                
                shared_state[w_id] = f"SAVING: {in_path.name}"
                sp = {"compression": best_cfg[0], "predictor": best_cfg[1], "dpi": dpi}
                if "deflate" in best_cfg[0]: sp["compress_level"] = best_cfg[2]
                img.save(out_path, **sp)
                log.write(f"    Winner: {best_cfg[0]} | P{best_cfg[1]} | L{best_cfg[2] if best_cfg[2]>0 else 'N/A'}\n")
            else:
                shared_state[w_id] = f"COMPRESSING: {in_path.name}"
                img.save(out_path, compression=args.compression or DEFAULT_COMPRESSION, 
                         predictor=args.predictor or DEFAULT_PREDICTOR, 
                         compress_level=args.level or DEFAULT_LEVEL, dpi=dpi)

            n_sz = os.path.getsize(out_path)
            red = ((o_sz - n_sz) / o_sz * 100) if o_sz > 0 else 0
            log.write(f"    Stats:  {get_size_format(o_sz)} -> {get_size_format(n_sz)} | -{red:.2f}% | {time.time()-start:.2f}s\n")
            shared_state[w_id] = f"IDLE - Task Done"
            return True, o_sz, n_sz, log.getvalue()
    except Exception as e:
        log.write(f"    [ERROR] {e}\n")
        shared_state[w_id] = f"ERROR: {in_path.name}"
        return False, 0, 0, log.getvalue()

# --- Main Logic ---

def main():
    parser = argparse.ArgumentParser(description="High-Performance Mission Control TIFF Optimizer.")
    parser.add_argument("path", nargs="?", default=".", help="Target path")
    out_group = parser.add_mutually_exclusive_group()
    out_group.add_argument("--overwrite", action="store_true")
    out_group.add_argument("-p", "--pool")
    out_group.add_argument("--subfolder")
    parser.add_argument("--best", action="store_true")
    parser.add_argument("-c", "--compression")
    parser.add_argument("-r", "--predictor", type=int)
    parser.add_argument("-l", "--level", type=int)
    parser.add_argument("-j", "--jobs", default="auto")
    args = parser.parse_args()

    # Environmental Check
    print("=" * 80)
    print(f"TIFF MISSION CONTROL ENGINE")
    print("-" * 80)
    print(f"Pillow: {pil_version} | LibTIFF: {features.check('libtiff')}")
    print(f"Deflate: {features.check('zlib')}")

    input_path = args.path
    
    # Expand glob patterns (Windows doesn't expand wildcards in shell)
    expanded_paths = glob.glob(input_path)
    
    files_to_process = []
    
    if expanded_paths:
        # Glob matched something - process each match
        for p in expanded_paths:
            path_obj = Path(p).resolve()
            if path_obj.is_file() and path_obj.suffix.lower() in ALLOWED_EXTENSIONS:
                files_to_process.append(path_obj)
            elif path_obj.is_dir():
                for root, _, files in os.walk(path_obj):
                    for f in files:
                        if f.lower().endswith(ALLOWED_EXTENSIONS):
                            files_to_process.append(Path(root) / f)
    else:
        # No glob match - treat as literal path
        input_base = Path(input_path).resolve()
        if not input_base.exists():
            print(f"Path not found: {input_path}")
            sys.exit(1)
        
        if input_base.is_file():
            if input_base.suffix.lower() in ALLOWED_EXTENSIONS:
                files_to_process.append(input_base)
        else:
            for root, _, files in os.walk(input_base):
                for f in files:
                    if f.lower().endswith(ALLOWED_EXTENSIONS):
                        files_to_process.append(Path(root) / f)

    if not files_to_process:
        print("No TIFF files found.")
        return

    selected_strategy = "overwrite"
    if args.pool: selected_strategy = "pool"
    elif args.subfolder: selected_strategy = "subfolder"

    sys_cores = os.cpu_count() or 1
    max_workers = int(args.jobs) if args.jobs != "auto" else sys_cores
    
    # Initialize Shared UI State
    manager = multiprocessing.Manager()
    shared_dict = manager.dict()
    for i in range(1, max_workers + 1):
        shared_dict[f"W{i:02}"] = "IDLE - Waiting for task"

    if len(files_to_process) == 1 and args.best:
        # --- SINGLE FILE VARIANT PARALLELISM ---
        f_path = files_to_process[0]
        if selected_strategy == "overwrite": out_path = f_path
        elif selected_strategy == "pool": out_path = Path(args.pool).resolve() / f_path.name
        elif selected_strategy == "subfolder": out_path = f_path.parent / args.subfolder / f_path.name

        variants = [
            ("tiff_deflate", 1, 1), ("tiff_deflate", 1, 6), ("tiff_deflate", 2, 6),
            ("tiff_deflate", 1, 9), ("tiff_deflate", 2, 9), ("tiff_adobe_deflate", 1, 9),
            ("tiff_adobe_deflate", 2, 9), ("tiff_lzw", 1, 0), ("tiff_lzw", 2, 0)
        ]
        
        print(f"Target:   {f_path.name}")
        print(f"Strategy: Variant-Parallelism ({max_workers} Cores)")
        print("-" * 80)

        painter = DashboardPainter(max_workers, len(variants))
        painter.start(shared_dict)

        with Image.open(f_path) as img:
            dpi, o_sz = img.info.get('dpi'), os.path.getsize(f_path)
            best_sz, best_cfg = float('inf'), None
            with tempfile.TemporaryDirectory() as tmpdir:
                with ProcessPoolExecutor(max_workers=max_workers) as executor:
                    futures = []
                    for i, cfg in enumerate(variants):
                        t_path = Path(tmpdir) / f"v{i}.tif"
                        w_id = f"W{ (i % max_workers) + 1:02}"
                        futures.append(executor.submit(variant_worker, (w_id, f_path, cfg, t_path, dpi, shared_dict)))

                    for fut in as_completed(futures):
                        sz, dur, log, cfg = fut.result()
                        painter.add_log(f"{log} | {((o_sz-sz)/o_sz*100):+.2f}%")
                        painter.completed_tasks += 1
                        if sz < best_sz: best_sz, best_cfg = sz, cfg

            final_sp = {"compression": best_cfg[0], "predictor": best_cfg[1], "dpi": dpi}
            if best_cfg[2]>0: final_sp["compress_level"] = best_cfg[2]
            img.save(out_path, **final_sp)
            n_sz = os.path.getsize(out_path)
            painter.add_log(f"\nWinner: {best_cfg[0]} | P{best_cfg[1]} | L{best_cfg[2] if best_cfg[2]>0 else 'N/A'}")
            painter.add_log(f"Final: {get_size_format(o_sz)} -> {get_size_format(n_sz)} | -{(o_sz-n_sz)/o_sz*100:.2f}%")

        painter.stop()

    else:
        # --- BATCH FILE PARALLELISM ---
        print(f"Workload: {len(files_to_process)} files | Strategy: Batch-Parallel ({max_workers} Cores)")
        print("-" * 80)
        
        painter = DashboardPainter(max_workers, len(files_to_process))
        painter.start(shared_dict)

        total_o, total_n, processed_count = 0, 0, 0
        file_results = []
        start_batch = time.time()
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            task_map = {}
            for i, f_p in enumerate(files_to_process):
                if selected_strategy == "overwrite": out_p = f_p
                elif selected_strategy == "pool": out_p = Path(args.pool).resolve() / f_p.name
                elif selected_strategy == "subfolder": out_p = f_p.parent / args.subfolder / f_p.name
                w_id = f"W{ (i % max_workers) + 1:02}"
                fut = executor.submit(process_file_worker, (w_id, f_p, out_p, args, shared_dict))
                task_map[fut] = f_p.name

            for fut in as_completed(task_map):
                suc, o_sz, n_sz, log_data = fut.result()
                f_name = task_map[fut]
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
        print(f"{'DETAILED BATCH REPORT':^80}")
        print("-" * 80)
        print(f"{'Filename':<40} | {'Original':>12} | {'New Size':>12} | {'Savings':>8}")
        print("-" * 80)
        for f_name, o, n in sorted(file_results):
            s_red = ((o - n) / o * 100) if o > 0 else 0
            print(f"{f_name:<40.40} | {get_size_format(o):>12} | {get_size_format(n):>12} | {s_red:>7.2f}%")
        
        print("-" * 80)
        print(f"Files Processed: {processed_count} / {len(files_to_process)}")
        print(f"Total Original:  {get_size_format(total_o)}")
        print(f"Total New Size:  {get_size_format(total_n)}")
        print(f"Total Savings:   {get_size_format(total_o - total_n)} (-{red:.2f}%)")
        print(f"Total Time:      {dur:.2f}s")
        print("=" * 80)

if __name__ == "__main__":
    main()
