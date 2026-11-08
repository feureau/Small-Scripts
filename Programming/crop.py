#!/usr/bin/env python3
"""
================================================================================================
Image Cropper and Converter (Multiprocessing Supported)
================================================================================================

This script is a robust command-line utility for batch processing images. It supports resizing,
cropping, padding, format conversion, and adding/removing borders.

--- Core Design & Reasoning ---

1. Multiprocessing (ProcessPoolExecutor)
   Image decoding, resampling, and encoding are heavily CPU-bound tasks. Python's Global
   Interpreter Lock (GIL) prevents threads from executing Python bytecodes in parallel. By using
   multiprocessing, the script spawns entirely separate Python processes, completely bypassing
   the GIL and achieving true parallelism across all available CPU cores.

2. EXIF Transpose (ImageOps.exif_transpose)
   Modern smartphones and cameras often save the raw image data exactly as it hit the sensor
   (e.g., sideways) and write an "Orientation" tag to the EXIF metadata. If we process the image
   and strip the EXIF data without reading it, the resulting output will appear sideways or upside
   down. This command bakes the EXIF rotation directly into the pixel data upon loading.

3. Color Space Normalization (RGB / RGBA)
   Images come in many color spaces (e.g., Grayscale 'L', Palette 'P', CMYK). If we attempt to
   draw a colored border (e.g., 'red') onto a Grayscale image, Pillow will crash because the image
   does not have color channels. Converting everything to RGB/RGBA immediately upon load ensures a
   predictable canvas for all subsequent operations.

4. High-Quality Resampling (LANCZOS)
   Lanczos resampling is hardcoded for resizing operations. While slightly slower than Nearest
   Neighbor or Bilinear, it provides vastly superior quality when downscaling images, effectively
   preventing jagged edges and moiré patterns (aliasing).

5. Auto Border Removal (ImageChops.difference)
   Instead of guessing border thickness, the `--remove-borders` flag uses mathematical differencing.
   It creates a solid image using the top-left pixel's color, subtracts the solid image from the
   original image, applies a tolerance threshold (to account for JPEG artifacts), and finds the
   bounding box of the non-zero pixels. This automatically and safely trims borders of varying
   thicknesses on all four sides simultaneously.
"""

import argparse
import ctypes
from ctypes import wintypes
import fnmatch
import glob
import os
import signal
import struct
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from PIL import Image, ImageColor, ImageOps, ImageChops

# Optional AVIF support
try:
    import pillow_avif  # noqa
except ImportError:
    pass

# --- Constants ---
DEFAULT_TARGET_WIDTH = 3840
DEFAULT_TARGET_HEIGHT = 2160
SUPPORTED_INPUT_EXTENSIONS = (
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".bmp",
    ".tiff",
    ".webp",
    ".avif",
)
DEFAULT_OUTPUT_FORMAT = "jpg"
DEFAULT_QUALITY = 85
DEFAULT_OUTPUT_SUBFOLDER = "cropped_output"
DEFAULT_BORDER_WIDTH = 120
DEFAULT_BORDER_COLOR = "red"

try:
    RESAMPLING_FILTER = Image.Resampling.LANCZOS
except AttributeError:
    RESAMPLING_FILTER = Image.LANCZOS

# --- Helpers ---


def validate_color_string(color_str: str) -> bool:
    try:
        ImageColor.getrgb(color_str)
        return True
    except ValueError:
        return False


def looks_like_file_token(token: str) -> bool:
    t = token.strip()
    if any(ch in t for ch in ("*", "?", "[", "]")):
        return True
    return Path(t).suffix.lower() in SUPPORTED_INPUT_EXTENSIONS


def remove_existing_borders(img, tolerance=15):
    bg_color = img.getpixel((0, 0))
    bg = Image.new(img.mode, img.size, bg_color)
    diff = ImageChops.difference(img, bg)
    mask = Image.eval(diff, lambda x: 255 if x > tolerance else 0)
    bbox = mask.getbbox()
    if bbox:
        return img.crop(bbox)
    return img


def calculate_dynamic_dimensions(img_width, img_height, rw, rh, box):
    in_ratio = img_width / img_height
    tgt_ratio = rw / rh

    if in_ratio > tgt_ratio:
        h = img_height
        w = int(h * tgt_ratio)
    else:
        w = img_width
        h = int(w / tgt_ratio)

    if box and (w > box or h > box):
        s = min(box / w, box / h)
        w = int(w * s)
        h = int(h * s)

    return w, h


def center_crop(img, new_w, new_h):
    w, h = img.size
    l = (w - new_w) // 2
    t = (h - new_h) // 2
    return img.crop((l, t, l + new_w, t + new_h))


def is_valid_input_path(path: Path, cwd: Path, output_dir_name: str, file_patterns: list[str]) -> bool:
    if path.suffix.lower() not in SUPPORTED_INPUT_EXTENSIONS:
        return False
    try:
        rel_path = path.relative_to(cwd)
        if output_dir_name in rel_path.parts:
            return False
    except ValueError:
        rel_path = path

    if file_patterns:
        rel_str = str(rel_path)
        name_str = path.name
        matched = any(
            fnmatch.fnmatch(rel_str, pat) or fnmatch.fnmatch(name_str, pat)
            for pat in file_patterns
        )
        if not matched:
            return False
    return True


def discover_files(args, cwd: Path) -> list[str]:
    files = []
    if not args.files:
        for p in cwd.rglob("*"):
            if p.is_file() and is_valid_input_path(p, cwd, args.output_dir, []):
                files.append(str(p))
    else:
        for f in args.files:
            for matched in glob.glob(f, recursive=True):
                p = Path(matched)
                if p.is_file() and is_valid_input_path(p, cwd, args.output_dir, []):
                    files.append(str(p))
    return sorted(set(files))


def _init_worker():
    """Ignore SIGINT in child worker processes so Ctrl+C is handled cleanly by main."""
    signal.signal(signal.SIGINT, signal.SIG_IGN)


def wait_until_file_ready(path: Path, retries: int = 25, delay: float = 0.05) -> bool:
    """
    Wait until a newly created/modified image file is completely written,
    its size/mtime have settled across a 150ms window, and it is readable.
    """
    for _ in range(retries):
        if not path.exists():
            return False
        try:
            st1 = path.stat()
            if st1.st_size == 0:
                time.sleep(delay)
                continue
            time.sleep(0.15)
            st2 = path.stat()
            if (st1.st_mtime_ns, st1.st_size) != (st2.st_mtime_ns, st2.st_size):
                continue
            with Image.open(path) as img:
                img.load()
            return True
        except Exception:
            time.sleep(delay)
    return False


# --- Event-Driven Directory Watcher (Windows ReadDirectoryChangesW) ---


class OVERLAPPED(ctypes.Structure):
    _fields_ = [
        ("Internal", ctypes.c_void_p),
        ("InternalHigh", ctypes.c_void_p),
        ("Offset", wintypes.DWORD),
        ("OffsetHigh", wintypes.DWORD),
        ("hEvent", wintypes.HANDLE),
    ]


def watch_directory_events(watch_dir: Path):
    """
    Generator yielding sets of Path objects whenever the OS kernel notifies of
    added, modified, or renamed files in watch_dir (and subdirectories).
    Uses Win32 ReadDirectoryChangesW with OVERLAPPED I/O for zero-polling wait
    while remaining responsive to Ctrl+C (KeyboardInterrupt).
    """
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    kernel32.CreateFileW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    kernel32.CreateFileW.restype = wintypes.HANDLE

    kernel32.CreateEventW.argtypes = [
        wintypes.LPVOID,
        wintypes.BOOL,
        wintypes.BOOL,
        wintypes.LPCWSTR,
    ]
    kernel32.CreateEventW.restype = wintypes.HANDLE

    kernel32.ResetEvent.argtypes = [wintypes.HANDLE]
    kernel32.ResetEvent.restype = wintypes.BOOL

    kernel32.ReadDirectoryChangesW.argtypes = [
        wintypes.HANDLE,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.BOOL,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
        ctypes.POINTER(OVERLAPPED),
        wintypes.LPVOID,
    ]
    kernel32.ReadDirectoryChangesW.restype = wintypes.BOOL

    kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel32.WaitForSingleObject.restype = wintypes.DWORD

    kernel32.GetOverlappedResult.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(OVERLAPPED),
        ctypes.POINTER(wintypes.DWORD),
        wintypes.BOOL,
    ]
    kernel32.GetOverlappedResult.restype = wintypes.BOOL

    kernel32.CancelIo.argtypes = [wintypes.HANDLE]
    kernel32.CancelIo.restype = wintypes.BOOL

    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL

    FILE_LIST_DIRECTORY = 0x0001
    FILE_SHARE_READ = 0x00000001
    FILE_SHARE_WRITE = 0x00000002
    FILE_SHARE_DELETE = 0x00000004
    OPEN_EXISTING = 3
    FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
    FILE_FLAG_OVERLAPPED = 0x40000000

    FILE_NOTIFY_CHANGE_FILE_NAME = 0x00000001
    FILE_NOTIFY_CHANGE_SIZE = 0x00000008
    FILE_NOTIFY_CHANGE_LAST_WRITE = 0x00000010

    FILE_ACTION_ADDED = 0x00000001
    FILE_ACTION_MODIFIED = 0x00000003
    FILE_ACTION_RENAMED_NEW_NAME = 0x00000005

    WAIT_OBJECT_0 = 0x00000000
    WAIT_TIMEOUT = 0x00000102
    ERROR_IO_PENDING = 997
    INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

    h_dir = kernel32.CreateFileW(
        str(watch_dir),
        FILE_LIST_DIRECTORY,
        FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
        None,
        OPEN_EXISTING,
        FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OVERLAPPED,
        None,
    )
    if h_dir == INVALID_HANDLE_VALUE or not h_dir:
        err = ctypes.get_last_error()
        raise OSError(err, f"Failed to open directory handle for {watch_dir}")

    h_event = kernel32.CreateEventW(None, True, False, None)
    if not h_event:
        err = ctypes.get_last_error()
        kernel32.CloseHandle(h_dir)
        raise OSError(err, "Failed to create event handle")

    buf_size = 65536
    buf = ctypes.create_string_buffer(buf_size)
    overlapped = OVERLAPPED()
    overlapped.hEvent = h_event
    bytes_returned = wintypes.DWORD(0)

    notify_filter = (
        FILE_NOTIFY_CHANGE_FILE_NAME
        | FILE_NOTIFY_CHANGE_SIZE
        | FILE_NOTIFY_CHANGE_LAST_WRITE
    )

    def arm_read():
        kernel32.ResetEvent(h_event)
        ok = kernel32.ReadDirectoryChangesW(
            h_dir,
            buf,
            buf_size,
            True,  # Watch subtree
            notify_filter,
            None,
            ctypes.byref(overlapped),
            None,
        )
        if not ok:
            err = ctypes.get_last_error()
            if err != ERROR_IO_PENDING:
                raise OSError(err, "ReadDirectoryChangesW failed")

    try:
        arm_read()
        while True:
            # Wait in kernel on the event handle; yield every 400ms only so Python
            # can process Ctrl+C (SIGINT) without touching the filesystem.
            while True:
                wait_res = kernel32.WaitForSingleObject(h_event, 400)
                if wait_res == WAIT_OBJECT_0:
                    break
                if wait_res != WAIT_TIMEOUT:
                    err = ctypes.get_last_error()
                    raise OSError(err, "WaitForSingleObject failed")

            if not kernel32.GetOverlappedResult(
                h_dir, ctypes.byref(overlapped), ctypes.byref(bytes_returned), False
            ):
                err = ctypes.get_last_error()
                raise OSError(err, "GetOverlappedResult failed")

            n_bytes = bytes_returned.value
            raw = buf.raw[:n_bytes] if n_bytes > 0 else b""

            # Re-arm immediately so kernel continues buffering events while we process
            arm_read()

            if not raw:
                continue

            offset = 0
            changed_paths = set()

            while offset < n_bytes:
                next_offset, action, name_len = struct.unpack_from("<III", raw, offset)
                name_start = offset + 12
                rel_name = raw[name_start : name_start + name_len].decode(
                    "utf-16-le", errors="replace"
                )
                if action in (
                    FILE_ACTION_ADDED,
                    FILE_ACTION_MODIFIED,
                    FILE_ACTION_RENAMED_NEW_NAME,
                ):
                    changed_paths.add(watch_dir / rel_name)

                if next_offset == 0:
                    break
                offset += next_offset

            if changed_paths:
                yield changed_paths
    finally:
        kernel32.CancelIo(h_dir)
        kernel32.CloseHandle(h_event)
        kernel32.CloseHandle(h_dir)


# --- Core Processing ---


def process_image(path_str, output_dir, args, border_color, border_width):
    """
    Returns a tuple: (Success_Bool, Message_String)
    We do NOT print inside here to avoid scrambled text in multiprocessing.
    """
    path = Path(path_str)

    try:
        with Image.open(path) as src_img:
            img = ImageOps.exif_transpose(src_img)

            # Ensure we are in a color mode (RGB or RGBA) so that color borders
            # and color output work even if the input is grayscale.
            if img.mode not in ("RGB", "RGBA"):
                if "transparency" in img.info or img.mode in ("LA", "PA"):
                    img = img.convert("RGBA")
                else:
                    img = img.convert("RGB")
            else:
                img = img.copy()

        if args.remove_borders:
            img = remove_existing_borders(img, tolerance=args.crop_tolerance)

    except Exception as e:
        return False, f"[Error] {path.name}: Open failed ({e})"

    # --- Target sizing ---
    if img.height > img.width:
        target_w, target_h = DEFAULT_TARGET_HEIGHT, DEFAULT_TARGET_WIDTH
    else:
        target_w, target_h = DEFAULT_TARGET_WIDTH, DEFAULT_TARGET_HEIGHT

    if args.fixed:
        target_w, target_h = args.fixed
    elif args.square or args.portrait or args.landscape or args.ratio:
        rw, rh = 16, 9
        if args.square:
            rw, rh = 1, 1
        elif args.portrait:
            rw, rh = 9, 16
        elif args.landscape:
            rw, rh = 16, 9
        elif args.ratio:
            rw, rh = map(float, args.ratio.split(":"))

        target_w, target_h = calculate_dynamic_dimensions(
            img.width, img.height, rw, rh, args.box
        )

    # --- Crop / resize to target ---
    if args.fit and border_color:
        inner_w = target_w - (2 * border_width)
        inner_h = target_h - (2 * border_width)
        if inner_w > 0 and inner_h > 0:
            scale = min(inner_w / img.width, inner_h / img.height)
            new_w = int(img.width * scale)
            new_h = int(img.height * scale)
            img = img.resize((new_w, new_h), RESAMPLING_FILTER)
    elif args.fit:
        scale = min(target_w / img.width, target_h / img.height)
        new_w = int(img.width * scale)
        new_h = int(img.height * scale)
        img = img.resize((new_w, new_h), RESAMPLING_FILTER)
    else:
        img = ImageOps.fit(img, (target_w, target_h), RESAMPLING_FILTER)

    # --- Crop Percent ---
    if args.crop_percent:
        scale = args.crop_percent / 100.0
        img = center_crop(img, int(target_w * scale), int(target_h * scale))

    # --- Zoom Percent ---
    if args.zoom_percent:
        scale = args.zoom_percent / 100.0
        cropped = center_crop(img, int(target_w * scale), int(target_h * scale))
        img = cropped.resize((target_w, target_h), RESAMPLING_FILTER)

    # --- Scale Percent ---
    if args.scale_percent:
        scale = args.scale_percent / 100.0
        new_w = int(img.width * scale)
        new_h = int(img.height * scale)
        img = img.resize((new_w, new_h), RESAMPLING_FILTER)

    # --- Border ---
    final = img
    if border_color:
        try:
            tw, th = target_w, target_h
            iw = tw - (2 * border_width)
            ih = th - (2 * border_width)
            if iw > 0 and ih > 0:
                canvas = Image.new(img.mode, (tw, th), border_color)
                if args.fit:
                    content = img
                    px = (tw - content.width) // 2
                    py = (th - content.height) // 2
                else:
                    content = ImageOps.fit(img, (iw, ih), RESAMPLING_FILTER)
                    px = (tw - content.width) // 2
                    py = (th - content.height) // 2
                if content.mode in ("RGBA", "LA"):
                    canvas.paste(content, (px, py), content)
                else:
                    canvas.paste(content, (px, py))
                final = canvas
        except Exception:
            pass

    # --- Save ---
    out_fmt = args.output_format.upper()
    out_ext = args.output_format.lower()
    if out_fmt == "JPG":
        out_fmt = "JPEG"
    if out_ext == "jpeg":
        out_ext = "jpg"

    opts = {}
    if out_fmt in ("JPEG", "WEBP", "AVIF"):
        opts["quality"] = min(max(1, args.quality), 95 if out_fmt == "JPEG" else 100)

    if out_fmt == "JPEG" and final.mode != "RGB":
        bg = Image.new("RGB", final.size, (255, 255, 255))
        bg.paste(final, mask=final.split()[-1] if final.mode == "RGBA" else None)
        final = bg

    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{path.stem}{args.suffix}.{out_ext}"

    try:
        final.save(out_path, format=out_fmt, **opts)
        # Calculate relative path for cleaner display
        try:
            display_path = out_path.relative_to(Path.cwd())
        except ValueError:
            display_path = out_path.name
        return True, f"[OK] {path.name} -> {display_path}"
    except Exception as e:
        return False, f"[Error] {path.name}: Save failed ({e})"


# --- Main ---


def main():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("files", nargs="*")
    parser.add_argument(
        "-d",
        "--output-dir",
        default=DEFAULT_OUTPUT_SUBFOLDER,
        help="Subfolder name for output",
    )
    parser.add_argument(
        "--pool",
        action="store_true",
        help="Flatten all outputs to one single directory",
    )

    parser.add_argument(
        "-w",
        "--workers",
        type=int,
        default=os.cpu_count(),
        help="Number of parallel processes",
    )
    parser.add_argument(
        "-W",
        "--watch",
        "--monitor",
        dest="watch",
        action="store_true",
        help="Monitor folder for new/modified images and process automatically until Ctrl+C",
    )

    parser.add_argument("-x", "--suffix", help="Custom filename suffix")
    parser.add_argument(
        "-o",
        "--output-format",
        default=DEFAULT_OUTPUT_FORMAT,
        choices=["jpg", "png", "webp", "tiff", "bmp", "avif"],
    )
    parser.add_argument("-q", "--quality", type=int, default=DEFAULT_QUALITY)

    border_mgmt = parser.add_mutually_exclusive_group()
    border_mgmt.add_argument(
        "-R",
        "--remove-borders",
        action="store_true",
        help="Automatically crop out existing borders (enabled by default with -b)",
    )
    border_mgmt.add_argument(
        "-K",
        "--keep-borders",
        action="store_true",
        help="Disable automatic border removal when using -b",
    )

    parser.add_argument(
        "-T",
        "--crop-tolerance",
        type=int,
        default=15,
        help="Color tolerance for border removal (0-255) to handle JPEG artifacts",
    )
    parser.add_argument(
        "-b",
        "--border",
        nargs="?",
        const=DEFAULT_BORDER_COLOR,
        help="Border spec: COLOR or COLOR:WIDTH (e.g. black or #ffffff:40). If value omitted, defaults to black.",
    )

    dim = parser.add_argument_group("Dimensions")
    dim.add_argument("-D", "--fixed", type=int, nargs=2, help="Fixed W H")
    dim.add_argument("-s", "--square", action="store_true")
    dim.add_argument("-p", "--portrait", action="store_true")
    dim.add_argument("-l", "--landscape", action="store_true")
    dim.add_argument("-r", "--ratio", help="Aspect Ratio (e.g., 21:9)")
    dim.add_argument(
        "-m", "--box", type=int, help="Max dimension (contains within box)"
    )

    dim.add_argument(
        "-f",
        "--fit",
        action="store_true",
        help="Fit image by padding instead of cropping",
    )
    dim.add_argument("-c", "--crop-percent", type=int)
    dim.add_argument("-z", "--zoom-percent", type=int)
    dim.add_argument("-S", "--scale-percent", type=int)

    args = parser.parse_args()

    # Compatibility: allow patterns like `-b *.png`.
    # If -b consumed a file token, treat it as an input file and keep border enabled with default color.
    if (
        args.border
        and not validate_color_string(args.border.split(":", 1)[0].strip())
        and looks_like_file_token(args.border)
    ):
        args.files.insert(0, args.border)
        args.border = DEFAULT_BORDER_COLOR

    if args.border and not args.keep_borders:
        args.remove_borders = True

    # --- Validation ---
    if args.crop_percent and args.zoom_percent:
        print("[Error] --crop-percent and --zoom-percent are mutually exclusive.")
        sys.exit(1)

    for name in ("crop_percent", "zoom_percent", "scale_percent"):
        val = getattr(args, name)
        if val is not None and not (1 <= val <= 200):
            print(f"[Error] {name.replace('_', '-')} must be between 1 and 200.")
            sys.exit(1)

    # --- Suffix ---
    if args.suffix is None:
        if args.fixed:
            args.suffix = f"_{args.fixed[0]}x{args.fixed[1]}"
        elif args.box:
            shape = "sq" if args.square else ("port" if args.portrait else "land")
            args.suffix = f"_{shape}_{args.box}px"
        else:
            args.suffix = "_processed"

    if args.crop_percent:
        args.suffix += f"_crop{args.crop_percent}"
    if args.zoom_percent:
        args.suffix += f"_zoom{args.zoom_percent}"
    if args.scale_percent:
        args.suffix += f"_scale{args.scale_percent}"

    # --- Border ---
    border_color = None
    border_width = DEFAULT_BORDER_WIDTH
    if args.border:
        spec = args.border.strip()
        color_candidate = spec
        width_candidate = None
        if ":" in spec:
            color_candidate, width_candidate = spec.rsplit(":", 1)
            color_candidate = color_candidate.strip()
            width_candidate = width_candidate.strip()

        if validate_color_string(color_candidate):
            border_color = color_candidate
            if width_candidate:
                if width_candidate.isdigit():
                    border_width = int(width_candidate)
                else:
                    print(
                        f"[Warning] Invalid border width '{width_candidate}'. Using default {DEFAULT_BORDER_WIDTH}."
                    )
        else:
            print("[Warning] Invalid border color. Skipping border.")

    # --- Files ---
    cwd = Path.cwd()
    global_out = cwd / args.output_dir
    files = discover_files(args, cwd)

    if not files and not args.watch:
        print(f"No images found in {cwd}.")
        sys.exit(1)

    ok_count = 0
    total_count = 0
    processed_signatures = {}

    # --- Multiprocessing Execution ---
    executor = ProcessPoolExecutor(
        max_workers=args.workers, initializer=_init_worker
    )
    try:
        if files:
            print(
                f"Starting processing on {len(files)} files using {args.workers} workers..."
            )
            futures = []
            now_init = time.monotonic()
            for f in files:
                p = Path(f)
                try:
                    st = p.stat()
                    processed_signatures[p.resolve()] = (
                        st.st_mtime_ns,
                        st.st_size,
                        now_init,
                    )
                except OSError:
                    pass
                out_dir = global_out if args.pool else p.parent / args.output_dir
                futures.append(
                    executor.submit(
                        process_image, f, out_dir, args, border_color, border_width
                    )
                )

            for future in as_completed(futures):
                success, message = future.result()
                print(message, flush=True)
                total_count += 1
                if success:
                    ok_count += 1

            if not args.watch:
                print(f"\nDone. {ok_count}/{len(files)} successful.")

        if args.watch:
            print(
                f"\nWatching {cwd} for new images... (Press Ctrl+C to stop)",
                flush=True,
            )
            try:
                for changed_paths in watch_directory_events(cwd):
                    batch = []
                    for p in sorted(changed_paths):
                        if not is_valid_input_path(
                            p, cwd, args.output_dir, args.files
                        ):
                            continue
                        if not wait_until_file_ready(p):
                            continue
                        try:
                            resolved = p.resolve()
                            st = p.stat()
                        except OSError:
                            continue

                        now = time.monotonic()
                        prev = processed_signatures.get(resolved)
                        if prev is not None:
                            prev_mtime, prev_size, prev_time = prev
                            if prev_mtime == st.st_mtime_ns and prev_size == st.st_size:
                                continue
                            # Ignore post-save metadata/ADS timestamp updates when size is unchanged
                            if prev_size == st.st_size and (now - prev_time) < 3.0:
                                processed_signatures[resolved] = (
                                    st.st_mtime_ns,
                                    st.st_size,
                                    now,
                                )
                                continue

                        processed_signatures[resolved] = (
                            st.st_mtime_ns,
                            st.st_size,
                            now,
                        )
                        batch.append(p)

                    if batch:
                        futures = []
                        for p in batch:
                            out_dir = (
                                global_out
                                if args.pool
                                else p.parent / args.output_dir
                            )
                            futures.append(
                                executor.submit(
                                    process_image,
                                    str(p),
                                    out_dir,
                                    args,
                                    border_color,
                                    border_width,
                                )
                            )
                        for future in as_completed(futures):
                            success, message = future.result()
                            print(message, flush=True)
                            total_count += 1
                            if success:
                                ok_count += 1
            except KeyboardInterrupt:
                print(
                    f"\nStopped watching. {ok_count}/{total_count} total processed."
                )
                executor.shutdown(wait=False, cancel_futures=True)
                return
    except KeyboardInterrupt:
        executor.shutdown(wait=False, cancel_futures=True)
        raise
    else:
        executor.shutdown(wait=True)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(1)
