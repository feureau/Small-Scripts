
#!/usr/bin/env python3
"""
================================================================================================
Image Cropper and Converter (Multiprocessing Supported)
================================================================================================
"""

import argparse
import sys
import os
from pathlib import Path
from PIL import Image, ImageOps
import glob
from concurrent.futures import ProcessPoolExecutor, as_completed

# Optional AVIF support
try:
    import pillow_avif  # noqa
except ImportError:
    pass

# Optional Webcolors support
try:
    import webcolors
    HAS_WEBCOLORS = True
except ImportError:
    HAS_WEBCOLORS = False

# --- Constants ---
DEFAULT_TARGET_WIDTH = 1920
DEFAULT_TARGET_HEIGHT = 1080
SUPPORTED_INPUT_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.avif')
DEFAULT_OUTPUT_FORMAT = 'jpg'
DEFAULT_QUALITY = 85
DEFAULT_OUTPUT_SUBFOLDER = 'cropped_output'
DEFAULT_BORDER_WIDTH = 60

try:
    RESAMPLING_FILTER = Image.Resampling.LANCZOS
except AttributeError:
    RESAMPLING_FILTER = Image.LANCZOS

# --- Helpers ---

def validate_color_string(color_str: str) -> bool:
    if color_str.startswith('#'):
        return True
    if HAS_WEBCOLORS:
        try:
            webcolors.name_to_rgb(color_str.lower())
            return True
        except ValueError:
            return False
    return True

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

# --- Core Processing ---

def process_image(path_str, output_dir, args, border_color, border_width):
    """
    Returns a tuple: (Success_Bool, Message_String)
    We do NOT print inside here to avoid scrambled text in multiprocessing.
    """
    path = Path(path_str)
    # Prepare basic info for valid return
    
    try:
        img = Image.open(path)
        img = ImageOps.exif_transpose(img)
    except Exception as e:
        return False, f"[Error] {path.name}: Open failed ({e})"

    # --- Target sizing ---
    target_w, target_h = DEFAULT_TARGET_WIDTH, DEFAULT_TARGET_HEIGHT
    
    if args.fixed:
        target_w, target_h = args.fixed
    elif args.square or args.portrait or args.landscape or args.ratio:
        rw, rh = 16, 9
        if args.square: rw, rh = 1, 1
        elif args.portrait: rw, rh = 9, 16
        elif args.landscape: rw, rh = 16, 9
        elif args.ratio:
            rw, rh = map(float, args.ratio.split(':'))

        target_w, target_h = calculate_dynamic_dimensions(
            img.width, img.height, rw, rh, args.box
        )

    # --- Crop / resize to target ---
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
            tw, th = final.size
            iw = tw - (2 * border_width)
            ih = th - (2 * border_width)
            if iw > 0 and ih > 0:
                content = final.copy()
                content.thumbnail((iw, ih), RESAMPLING_FILTER)
                canvas = Image.new(final.mode, (tw, th), border_color)
                px = (tw - content.width) // 2
                py = (th - content.height) // 2
                if content.mode in ('RGBA', 'LA'):
                    canvas.paste(content, (px, py), content)
                else:
                    canvas.paste(content, (px, py))
                final = canvas
        except Exception:
            pass

    # --- Save ---
    out_fmt = args.output_format.upper()
    out_ext = args.output_format.lower()
    if out_fmt == 'JPG': out_fmt = 'JPEG'
    if out_ext == 'jpeg': out_ext = 'jpg'

    opts = {}
    if out_fmt in ('JPEG', 'WEBP', 'AVIF'):
        opts['quality'] = min(max(1, args.quality), 95 if out_fmt == 'JPEG' else 100)

    if out_fmt == 'JPEG' and final.mode != 'RGB':
        bg = Image.new("RGB", final.size, (255, 255, 255))
        bg.paste(final, mask=final.split()[-1] if final.mode == 'RGBA' else None)
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
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('files', nargs='*')
    parser.add_argument('-o', '--output-dir', default=DEFAULT_OUTPUT_SUBFOLDER, help="Subfolder name for output")
    parser.add_argument('--pool', action='store_true', help="Flatten all outputs to one single directory")
    
    # NEW ARGUMENT
    parser.add_argument('-w', '--workers', type=int, default=os.cpu_count(), help="Number of parallel processes")

    parser.add_argument('-x', '--suffix', help="Custom filename suffix")
    parser.add_argument('-f', '--output-format', default=DEFAULT_OUTPUT_FORMAT,
                        choices=['jpg','png','webp','tiff','bmp','avif'])
    parser.add_argument('-q', '--quality', type=int, default=DEFAULT_QUALITY)
    parser.add_argument('-b', '--border', nargs='*', help="Color [Width]")

    dim = parser.add_argument_group('Dimensions')
    dim.add_argument('-d', '--fixed', type=int, nargs=2, help="Fixed W H")
    dim.add_argument('-s', '--square', action='store_true')
    dim.add_argument('-p', '--portrait', action='store_true')
    dim.add_argument('-l', '--landscape', action='store_true')
    dim.add_argument('-r', '--ratio', help="Aspect Ratio (e.g., 21:9)")
    dim.add_argument('-m', '--box', type=int, help="Max dimension (contains within box)")

    dim.add_argument('-c', '--crop-percent', type=int)
    dim.add_argument('-z', '--zoom-percent', type=int)
    dim.add_argument('-S', '--scale-percent', type=int)

    args = parser.parse_args()

    # --- Validation ---
    if args.crop_percent and args.zoom_percent:
        print("[Error] --crop-percent and --zoom-percent are mutually exclusive.")
        sys.exit(1)

    for name in ('crop_percent', 'zoom_percent', 'scale_percent'):
        val = getattr(args, name)
        if val is not None and not (1 <= val <= 200):
            print(f"[Error] {name.replace('_','-')} must be between 1 and 200.")
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

    if args.crop_percent: args.suffix += f"_crop{args.crop_percent}"
    if args.zoom_percent: args.suffix += f"_zoom{args.zoom_percent}"
    if args.scale_percent: args.suffix += f"_scale{args.scale_percent}"

    # --- Border ---
    border_color = None
    border_width = DEFAULT_BORDER_WIDTH
    if args.border:
        if len(args.border) > 0 and validate_color_string(args.border[0]):
            border_color = args.border[0]
            if len(args.border) > 1 and args.border[1].isdigit():
                border_width = int(args.border[1])
        else:
            print("[Warning] Invalid border color. Skipping border.")

    # --- Files ---
    files = []
    global_out = Path.cwd() / args.output_dir

    if not args.files:
        for p in Path.cwd().rglob('*'):
            if p.suffix.lower() in SUPPORTED_INPUT_EXTENSIONS:
                try:
                    rel_parts = p.relative_to(Path.cwd()).parts
                    if args.output_dir not in rel_parts:
                        files.append(str(p))
                except ValueError:
                    files.append(str(p))
    else:
        for f in args.files:
            files.extend(glob.glob(f, recursive=True))

    files = sorted(set(files))
    if not files:
        print(f"No images found in {Path.cwd()}.")
        sys.exit(1)

    print(f"Starting processing on {len(files)} files using {args.workers} workers...")
    
    ok_count = 0
    
    # --- Multiprocessing Execution ---
    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        futures = []
        for f in files:
            # Determine output directory for this specific file
            # If --pool is set, everything goes to global_out. 
            # If not, it goes to a subfolder relative to the source file.
            out_dir = global_out if args.pool else Path(f).parent / args.output_dir
            
            # Submit task to the pool
            futures.append(
                executor.submit(process_image, f, out_dir, args, border_color, border_width)
            )

        # Process results as they complete
        for future in as_completed(futures):
            success, message = future.result()
            print(message)
            if success:
                ok_count += 1

    print(f"\nDone. {ok_count}/{len(files)} successful.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(1)
