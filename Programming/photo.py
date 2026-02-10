"""
# Photo.py — RawTherapee Batch Processor with Optional Denoise and LUT

This script batch-processes RAW photos using RawTherapee CLI, with optional AI denoise (NAFNet),
optional LUT application, and lossless TIFF compression.

## Maintenance Rule
> [!IMPORTANT]
> This documentation block MUST be included and updated with every revision or update of the script.
> Do not remove any content from this block; only append or update it.

## Features
- RAW conversion via RawTherapee CLI (recursive folders or explicit files)
- Output formats: TIFF (default) or JPEG
- Optional AI denoise (NAFNet) with CUDA + auto-calibrated max full-frame size
- Optional LUT application using `.cube` files in `LUT/` or `lut/`
- Lossless TIFF compression (Deflate + Predictor + Level 9)
- Windows wildcard expansion for `*.arw` style inputs
- Verbose error output for RawTherapee failures

## Requirements
- Python 3.x
- RawTherapee CLI (`rawtherapee-cli`)
- For LUTs: `pillow` and `pillow_lut`
- For denoise: `numpy`, `torch`, and `nafnet_arch.py` next to this script

## Usage
```powershell
photo.py *.arw -f tif
photo.py *.arw -f jpg -q 92
photo.py *.arw -f tif -d
photo.py *.arw -f tif -l
photo.py *.arw -f tif -l C:\path\to\MyLUT.cube
```

## Arguments
- `paths`: Files or folders to process (supports wildcards on Windows)
- `-f, --format`: Output format (`tif` default, or `jpg`)
- `-q, --quality`: JPEG quality (only for JPG output)
- `-o, --output`: Output folder name (defaults to format)
- `-d, --denoise`: Run AI denoise after conversion
- `-l, --lut`: Prompt for LUT selection, or pass a direct `.cube` file path
- `--no-lut`: Skip LUT application

## LUT Behavior
- If `-l` is passed without a direct `.cube` file path, the script prompts for a LUT choice.
- LUTs are searched in `LUT/` or `lut/` next to this script.
- When a LUT is applied, its name is appended to the output filename.

## Denoise Behavior
- Denoise uses NAFNet (SIDD weights).
- Auto mode attempts full-frame on CUDA if within calibrated limits, otherwise tiled.
- Calibration results are saved in `denoise_cache.json` and reused.

## Processing Order
1. RawTherapee conversion
2. LUT application (if enabled)
3. Denoise (if enabled)
4. TIFF compression (only when output is TIFF and denoise is not used)

## Notes
- TIFF compression uses Deflate + Predictor 2 + Level 9 (lossless).
- If denoise is enabled, the output is re-saved using Pillow (currently 8-bit).
"""

import os
import sys
import platform
import shutil
import subprocess
import argparse
import glob
import json
from pathlib import Path

# --- DENOISE (NAFNet) SETTINGS ---
MODEL_DIR = r"F:\AI\NAFNet"
MODEL_FILENAME = "NAFNet-SIDD-width64.pth"
SCRIPT_DIR = Path(__file__).parent
DENOISE_CACHE = os.path.join(SCRIPT_DIR, "denoise_cache.json")
CALIBRATE_ASPECT = "3:2"
CALIBRATE_MAX_MP = 200
LUT_DIR = os.path.join(SCRIPT_DIR, "LUT")
ALT_LUT_DIR = os.path.join(SCRIPT_DIR, "lut")
TIF_COMPRESSION = "tiff_deflate"
TIF_PREDICTOR = 2
TIF_LEVEL = 9

def _import_denoise_deps():
    try:
        import numpy as np
        import torch
        import torch.nn.functional as F
        from PIL import Image
        return np, torch, F, Image
    except Exception as e:
        return None, None, None, e

def _import_pil_only():
    try:
        from PIL import Image
        return Image, None
    except Exception as e:
        return None, e

def _import_lut_deps():
    try:
        from PIL import Image
        from pillow_lut import load_cube_file
        return Image, load_cube_file, None
    except Exception as e:
        return None, None, e

def _get_nafnet_arch():
    try:
        from nafnet_arch import NAFNet
        return NAFNet
    except Exception:
        return None

def _tile_process_overlap_blend(img_tensor, model, tile_size=512, overlap=64, torch=None, F=None, np=None):
    """
    Processes the image in overlapping tiles and blends them to avoid seams.
    """
    b, c, h, w = img_tensor.shape
    output = torch.zeros_like(img_tensor)
    weight = torch.zeros_like(img_tensor)

    pad = overlap
    padded = F.pad(img_tensor, (pad, pad, pad, pad), mode='reflect')

    wy = torch.linspace(0, 1, steps=tile_size, device=img_tensor.device)
    wx = torch.linspace(0, 1, steps=tile_size, device=img_tensor.device)
    wy = 0.5 - 0.5 * torch.cos(np.pi * wy)  # Hann
    wx = 0.5 - 0.5 * torch.cos(np.pi * wx)
    w2d = (wy[:, None] * wx[None, :]).unsqueeze(0).unsqueeze(0)

    step = tile_size - overlap
    for y in range(0, h, step):
        for x in range(0, w, step):
            y_end = min(y + tile_size, h)
            x_end = min(x + tile_size, w)
            curr_h = y_end - y
            curr_w = x_end - x

            tile = padded[:, :, y:y+curr_h+2*pad, x:x+curr_w+2*pad]
            with torch.no_grad():
                processed = model(tile)

            processed = processed[:, :, pad:pad+curr_h, pad:pad+curr_w]
            w_curr = w2d[:, :, :curr_h, :curr_w]
            output[:, :, y:y_end, x:x_end] += processed * w_curr
            weight[:, :, y:y_end, x:x_end] += w_curr

    return output / torch.clamp(weight, min=1e-6)

def _pad_to_multiple(img_tensor, multiple=16, torch=None, F=None):
    _, _, h, w = img_tensor.shape
    pad_h = (multiple - (h % multiple)) % multiple
    pad_w = (multiple - (w % multiple)) % multiple
    if pad_h == 0 and pad_w == 0:
        return img_tensor, (0, 0, 0, 0)
    # pad: (left, right, top, bottom)
    pad = (0, pad_w, 0, pad_h)
    return F.pad(img_tensor, pad, mode='reflect'), pad

def _unpad(img_tensor, pad):
    left, right, top, bottom = pad
    if right == 0 and bottom == 0 and left == 0 and top == 0:
        return img_tensor
    _, _, h, w = img_tensor.shape
    return img_tensor[:, :, top:h-bottom, left:w-right]

def _get_denoise_model(torch=None):
    NAFNet = _get_nafnet_arch()
    if not NAFNet:
        print("   [AI] Missing nafnet_arch.py (required for denoise).")
        return None

    model_path = os.path.join(MODEL_DIR, MODEL_FILENAME)
    if not os.path.exists(model_path):
        print(f"   [AI] Model not found at: {model_path}")
        return None

    model = NAFNet(
        img_channel=3,
        width=64,
        middle_blk_num=12,
        enc_blk_nums=[2, 2, 4, 8],
        dec_blk_nums=[2, 2, 2, 2],
    )

    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    try:
        checkpoint = torch.load(model_path, map_location=device)
        state_dict = checkpoint['params'] if 'params' in checkpoint else checkpoint
        model.load_state_dict(state_dict, strict=True)
        model.to(device).eval()
        return model, device
    except Exception as e:
        print(f"   [AI] Error loading model: {e}")
        return None

def _load_denoise_cache():
    if not os.path.exists(DENOISE_CACHE):
        return None
    try:
        with open(DENOISE_CACHE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def _save_denoise_cache(cache):
    try:
        with open(DENOISE_CACHE, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2)
    except Exception as e:
        print(f"   [AI] Warning: failed to write denoise cache: {e}")

def _aspect_to_ratio(text):
    parts = text.split(":")
    if len(parts) != 2:
        raise ValueError("Aspect must be like 3:2")
    w = float(parts[0].strip())
    h = float(parts[1].strip())
    if w <= 0 or h <= 0:
        raise ValueError("Aspect must be positive")
    return w / h

def _calibrate_max_full_frame(model, device, torch=None, aspect_ratio=3/2, use_amp=True, max_mp=200, verbose=False):
    if device != "cuda":
        print("   [AI] Calibration requires CUDA.")
        return None

    def try_mp(mp):
        total_pixels = int(mp * 1_000_000)
        h = int((total_pixels / aspect_ratio) ** 0.5)
        w = int(h * aspect_ratio)
        w = max(16, (w // 16) * 16)
        h = max(16, (h // 16) * 16)
        x = torch.zeros((1, 3, h, w), device=device, dtype=torch.float32)
        try:
            torch.cuda.reset_peak_memory_stats()
            with torch.no_grad():
                if use_amp:
                    with torch.amp.autocast("cuda"):
                        _ = model(x)
                else:
                    _ = model(x)
            if verbose:
                peak = torch.cuda.max_memory_allocated() / (1024 ** 2)
                reserved = torch.cuda.max_memory_reserved() / (1024 ** 2)
                print(f"   [AI] Calib OK: {w}x{h} (~{mp:.2f} MP) | peak {peak:.1f} MB, reserved {reserved:.1f} MB")
            return True, w, h
        except RuntimeError as e:
            if "out of memory" in str(e).lower():
                torch.cuda.empty_cache()
                if verbose:
                    print(f"   [AI] Calib OOM: {w}x{h} (~{mp:.2f} MP)")
                return False, w, h
            raise

    lo = 1.0
    hi = float(max_mp)
    best = None
    if verbose:
        print(f"   [AI] Calibrating max full-frame size (aspect {aspect_ratio:.4f}, max {max_mp} MP)")
    for _ in range(12):
        mid = (lo + hi) / 2.0
        ok, w, h = try_mp(mid)
        if ok:
            best = (mid, w, h)
            lo = mid
        else:
            hi = mid

    return best

def _run_denoise_srgb_with_model(img_srgb_np, model, device, torch=None, F=None, np=None, denoise_mode="auto", tile_size=512, overlap=64, max_full_pixels=None):
    print(f"   [AI] Running denoise on {device.upper()}...")
    img_tensor = torch.from_numpy(np.transpose(img_srgb_np, (2, 0, 1))).float().unsqueeze(0).to(device)
    img_tensor, pad = _pad_to_multiple(img_tensor, multiple=16, torch=torch, F=F)
    pixels = img_tensor.shape[-1] * img_tensor.shape[-2]

    try_full = (denoise_mode == "full") or (
        denoise_mode == "auto"
        and device == "cuda"
        and (max_full_pixels is None or pixels <= max_full_pixels)
    )
    used_full = False

    if try_full and device == "cuda":
        try:
            with torch.no_grad():
                with torch.amp.autocast("cuda"):
                    restored = model(img_tensor)
            used_full = True
        except RuntimeError as e:
            if "out of memory" in str(e).lower():
                print("   [AI] CUDA OOM. Falling back to overlap-blended tiling.")
                torch.cuda.empty_cache()
                restored = _tile_process_overlap_blend(img_tensor, model, tile_size=tile_size, overlap=overlap, torch=torch, F=F, np=np)
            else:
                raise
    else:
        restored = _tile_process_overlap_blend(img_tensor, model, tile_size=tile_size, overlap=overlap, torch=torch, F=F, np=np)

    restored = _unpad(restored, pad)
    img_out = restored.clamp(0, 1).cpu().detach().permute(0, 2, 3, 1).squeeze(0).numpy()
    return img_out, used_full, pixels

def _denoise_image_file(image_path, out_format="jpg", quality=92, denoise_mode="auto", tile_size=512, overlap=64):
    np, torch, F, Image = _import_denoise_deps()
    if np is None:
        print(f"   [AI] Missing denoise dependencies: {Image}")
        return False

    try:
        with Image.open(image_path) as im:
            im = im.convert("RGB")
            img = np.asarray(im).astype(np.float32) / 255.0
    except Exception as e:
        print(f"   [AI] Failed to read image: {e}")
        return False

    model_info = _get_denoise_model(torch=torch)
    if not model_info:
        return False
    model, device = model_info

    cache = _load_denoise_cache() or {}
    max_full_pixels = cache.get("max_full_pixels")
    if denoise_mode == "auto" and device == "cuda" and max_full_pixels is None:
        try:
            aspect = _aspect_to_ratio(CALIBRATE_ASPECT)
            result = _calibrate_max_full_frame(
                model,
                device,
                torch=torch,
                aspect_ratio=aspect,
                use_amp=True,
                max_mp=CALIBRATE_MAX_MP,
                verbose=True,
            )
            if result:
                mp, w, h = result
                props = torch.cuda.get_device_properties(0)
                cache = {
                    "gpu_name": props.name,
                    "total_vram_mb": int(props.total_memory / (1024 ** 2)),
                    "max_full_pixels": int(w * h),
                    "max_full_mp": round(mp, 2),
                    "aspect": CALIBRATE_ASPECT,
                }
                _save_denoise_cache(cache)
                max_full_pixels = cache.get("max_full_pixels")
                print(f"   [AI] Calibration saved: ~{cache['max_full_mp']} MP ({w}x{h})")
        except Exception as e:
            print(f"   [AI] Calibration failed: {e}")

    denoised, used_full, pixels = _run_denoise_srgb_with_model(
        img,
        model,
        device,
        torch=torch,
        F=F,
        np=np,
        denoise_mode=denoise_mode,
        tile_size=tile_size,
        overlap=overlap,
        max_full_pixels=max_full_pixels,
    )

    out_img = (denoised * 255.0).clip(0, 255).astype(np.uint8)
    out_pil = Image.fromarray(out_img)

    if denoise_mode == "auto" and used_full and pixels:
        if max_full_pixels is None or pixels > max_full_pixels:
            cache["max_full_pixels"] = int(pixels)
            _save_denoise_cache(cache)

    try:
        if out_format == "jpg":
            out_pil.save(image_path, quality=quality)
        else:
            out_pil.save(
                image_path,
                compression=TIF_COMPRESSION,
                predictor=TIF_PREDICTOR,
                compress_level=TIF_LEVEL,
            )
        return True
    except Exception as e:
        print(f"   [AI] Failed to write denoised image: {e}")
        return False

def _compress_tif_inplace(image_path):
    Image, err = _import_pil_only()
    if Image is None:
        print(f"   [TIFF] Compression skipped (Pillow missing): {err}")
        return False
    try:
        with Image.open(image_path) as im:
            im.save(
                image_path,
                compression=TIF_COMPRESSION,
                predictor=TIF_PREDICTOR,
                compress_level=TIF_LEVEL,
            )
        return True
    except Exception as e:
        print(f"   [TIFF] Compression failed: {e}")
        return False

def _find_lut_files():
    search_dirs = []
    if os.path.isdir(LUT_DIR):
        search_dirs.append(LUT_DIR)
    if os.path.isdir(ALT_LUT_DIR) and ALT_LUT_DIR not in search_dirs:
        search_dirs.append(ALT_LUT_DIR)

    lut_files = []
    for d in search_dirs:
        lut_files.extend(glob.glob(os.path.join(d, "*.cube")))

    seen = {}
    for p in lut_files:
        base = os.path.basename(p)
        if base.lower() not in seen:
            seen[base.lower()] = p
    return [seen[k] for k in sorted(seen.keys())]

def _select_lut(lut_files, cli_lut=None):
    if not lut_files:
        return None

    if cli_lut:
        cli_lut = cli_lut.strip()
        if cli_lut.lower() in {"none", "off", "skip"}:
            return None
        # Only accept a direct LUT file path when provided via -l/--lut
        if os.path.isfile(cli_lut) and cli_lut.lower().endswith(".cube"):
            return cli_lut

    print("\nAvailable LUTs:")
    for i, lut_path in enumerate(lut_files, 1):
        print(f"  {i}. {os.path.basename(lut_path)}")
    choice = input("Select LUT number (Enter to skip, or type 'none' to skip): ").strip()
    if not choice:
        return None
    if choice.lower() in {"none", "off", "skip"}:
        return None
    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(lut_files):
            return lut_files[idx]
    print("[LUT] Invalid selection. Using first LUT.")
    return lut_files[0]

def _apply_lut_inplace(image_path, lut_path):
    Image, load_cube_file, err = _import_lut_deps()
    if Image is None:
        print(f"   [LUT] LUT skipped (missing dependencies): {err}")
        return False
    try:
        with Image.open(image_path) as im:
            im = im.convert("RGB")
            im = im.filter(load_cube_file(lut_path))
            im.save(image_path)
        return True
    except Exception as e:
        print(f"   [LUT] LUT apply failed: {e}")
        return False

def _sanitize_tag(text):
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
    return "".join(ch if ch in allowed else "_" for ch in text)

def _append_lut_to_filename(image_path, lut_path):
    base = os.path.splitext(os.path.basename(lut_path))[0]
    tag = _sanitize_tag(base)
    p = Path(image_path)
    new_name = f"{p.stem}_{tag}{p.suffix}"
    new_path = p.with_name(new_name)
    try:
        if new_path.exists():
            return str(new_path)
        os.replace(image_path, new_path)
        return str(new_path)
    except Exception:
        return image_path

class RawConverter:
    def __init__(self, executable_path=None):
        self.rt_path = executable_path or self._find_rt_binary()
        if not self.rt_path:
            raise FileNotFoundError("Could not find rawtherapee-cli. Please check your installation.")
        self.extensions = {'.arw', '.cr2', '.cr3', '.nef', '.dng', '.orf', '.raf', '.srw'}

    def _find_rt_binary(self):
        exe_name = "rawtherapee-cli.exe" if platform.system() == "Windows" else "rawtherapee-cli"
        path_check = shutil.which(exe_name)
        if path_check: return path_check
        system = platform.system()
        if system == "Windows":
            roots = [r"C:\Program Files", r"C:\Program Files (x86)"]
            for root in roots:
                if not os.path.exists(root): continue
                for entry in os.scandir(root):
                    if entry.is_dir() and "rawtherapee" in entry.name.lower():
                        for dirpath, _, filenames in os.walk(entry.path):
                            if exe_name in filenames:
                                return os.path.join(dirpath, exe_name)
        return None

    def process_file(self, file_path, output_dir, profile=None, quality=92, out_format="jpg"):
        abs_input = os.path.abspath(file_path)
        abs_output = os.path.abspath(output_dir)
        os.makedirs(abs_output, exist_ok=True)

        cmd = [self.rt_path, "-o", abs_output, "-Y"]
        if out_format == "jpg":
            cmd.append(f"-j{quality}")
        elif out_format in {"tif", "tiff"}:
            cmd.append("-t")
        else:
            raise ValueError(f"Unsupported output format: {out_format}")
        if profile:
            cmd.extend(["-p", os.path.abspath(profile)])
        else:
            cmd.append("-d")
        
        cmd.extend(["-c", abs_input])
        return subprocess.run(cmd, capture_output=True, text=True), cmd

def select_profile():
    """Looks for .pp3 files in a 'profiles' subfolder next to the script."""
    script_dir = Path(__file__).parent
    profile_dir = script_dir / "profiles"
    
    if not profile_dir.exists():
        return None

    pp3_files = list(profile_dir.glob("*.pp3"))
    if not pp3_files:
        return None

    print("\n--- Available Profiles ---")
    print("0: [Default/Neutral]")
    for i, p in enumerate(pp3_files, 1):
        print(f"{i}: {p.name}")
    
    while True:
        try:
            choice = int(input("\nSelect a profile number to apply: "))
            if choice == 0:
                return None
            if 1 <= choice <= len(pp3_files):
                return str(pp3_files[choice - 1])
        except ValueError:
            pass
        print("Invalid choice. Try again.")

def main():
    parser = argparse.ArgumentParser(description="Recursive RAW processor with Profile Selection")
    parser.add_argument("paths", nargs="*", default=["."], help="Files/folders to process")
    parser.add_argument("--format", "-f", dest="out_format", default="tif", choices=["jpg", "tif", "tiff"], help="Output format")
    parser.add_argument("-q", "--quality", type=int, default=92, help="JPEG quality")
    parser.add_argument("-o", "--output", default=None, help="Output folder name (defaults to format)")
    parser.add_argument("-d", "--denoise", action="store_true", help="Run AI denoise after conversion")
    parser.add_argument("--lut", "-l", help="LUT name or number. Use 'none' to skip.")
    parser.add_argument("--no-lut", action="store_true", help="Skip LUT application.")
    
    args = parser.parse_args()

    try:
        converter = RawConverter()
        print(f"⚙️  Using: {converter.rt_path}")
    except Exception as e:
        print(f"❌ {e}")
        return

    # Interactive Profile Selection
    selected_pp3 = select_profile()
    if selected_pp3:
        print(f"🎨 Selected Profile: {Path(selected_pp3).name}")
    else:
        print("💡 No profile selected. Using RawTherapee defaults.")

    lut_files = _find_lut_files()
    lut_path = None if args.no_lut else _select_lut(lut_files, cli_lut=args.lut)
    if lut_path:
        print(f"🎨 LUT Selected: {os.path.basename(lut_path)}")

    # Gather targets (expand wildcards on Windows)
    raw_paths = set()
    output_dir = args.output or args.out_format
    expanded_inputs = []
    for p in args.paths:
        if "*" in p or "?" in p:
            matches = glob.glob(p)
            if matches:
                expanded_inputs.extend(matches)
            else:
                expanded_inputs.append(p)
        else:
            expanded_inputs.append(p)

    stray_format_tokens = []
    for p in expanded_inputs:
        if p.lower() in {"jpg", "tif", "tiff"} and not Path(p).exists():
            stray_format_tokens.append(p)
            continue
        path_obj = Path(p)
        if path_obj.is_dir():
            for ext in converter.extensions:
                raw_paths.update(path_obj.rglob(f"*{ext}"))
                raw_paths.update(path_obj.rglob(f"*{ext.upper()}"))
        elif path_obj.suffix.lower() in converter.extensions and path_obj.exists():
            raw_paths.add(path_obj)
        elif path_obj.suffix.lower() in converter.extensions and not path_obj.exists():
            print(f"⚠️  Skipping missing file: {path_obj}")

    if stray_format_tokens:
        print(f"❌ Unrecognized argument(s): {', '.join(stray_format_tokens)}")
        print("   Use -f/--format, e.g. `photo.py *.arw -f tif`")
        return

    if not raw_paths:
        print("No RAW files found.")
        return

    print(f"📸 Files to process: {len(raw_paths)}")

    for photo in sorted(raw_paths):
        print(f"⏳ Processing {photo.name}...", end=" ", flush=True)
        try:
            res, cmd = converter.process_file(photo, output_dir, selected_pp3, args.quality, args.out_format)
        except Exception as e:
            print(f"❌ FAILED. {e}")
            continue
        if res.returncode == 0:
            print("✅ Done.")
            out_ext = ".jpg" if args.out_format == "jpg" else ".tif"
            out_file = os.path.join(output_dir, photo.with_suffix(out_ext).name)
            if lut_path:
                print(f"   [LUT] Applying {os.path.basename(lut_path)}...")
                l_ok = _apply_lut_inplace(out_file, lut_path)
                if l_ok:
                    out_file = _append_lut_to_filename(out_file, lut_path)
                    print(f"   [LUT] ✅ Applied. Renamed to {os.path.basename(out_file)}")
                else:
                    print("   [LUT] ❌ Failed.")

            if args.denoise:
                print(f"   [AI] Denoising {os.path.basename(out_file)}...")
                ok = _denoise_image_file(out_file, out_format=args.out_format, quality=args.quality)
                if ok:
                    print("   [AI] ✅ Denoise complete.")
                else:
                    print("   [AI] ❌ Denoise failed.")
            elif args.out_format in {"tif", "tiff"}:
                print(f"   [TIFF] Compressing {os.path.basename(out_file)}...")
                ok = _compress_tif_inplace(out_file)
                if ok:
                    print("   [TIFF] ✅ Compression complete.")
                else:
                    print("   [TIFF] ❌ Compression failed.")
        else:
            print("❌ FAILED.")
            print(f"   [RT] Command: {' '.join(cmd)}")
            if res.stdout:
                print("   [RT] STDOUT:")
                print(res.stdout.strip())
            if res.stderr:
                print("   [RT] STDERR:")
                print(res.stderr.strip())

    print("\nBatch Complete.")

if __name__ == "__main__":
    main()
