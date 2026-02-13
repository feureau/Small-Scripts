"""
# Photo.py — RawTherapee Batch Processor with Optional Denoise and LUT

This script batch-processes RAW photos using RawTherapee CLI, with optional AI inference (NAFNet/Restormer),
optional LUT application, and lossless TIFF compression.

## Maintenance Rule
> [!IMPORTANT]
> This documentation block MUST be included and updated with every revision or update of the script.
> Do not remove any content from this block; only append or update it.

## Features
- RAW conversion via RawTherapee CLI (recursive folders or explicit files)
- Non-RAW image input support (JPG/JPEG/PNG/TIF/TIFF/BMP/WEBP)
- Output formats: TIFF (default) or JPEG
- Optional AI inference with model selection (`-d` shortcut for NAFNet, or `-i MODEL`)
- Optional DualDn RAW pre-denoising via external inference script (`-i DualDn-Big`)
- Optional LUT application using `.cube` files in `LUT/` or `lut/`
- Lossless TIFF compression (Deflate + Predictor + Level 9)
- Windows wildcard expansion for `*.arw` style inputs
- Optional RawTherapee bypass mode (`--skip-rt`)
- Verbose error output for RawTherapee failures

## Requirements
- Python 3.x
- RawTherapee CLI (`rawtherapee-cli`)
- For LUTs: `pillow` and `pillow_lut`
- For inference: `numpy`, `torch`, `tifffile`, local `nafnet_arch.py`, and `einops` (for Restormer)
- For DualDn: compatible DualDn inference script + checkpoint (external execution)

## Usage
```powershell
photo.py *.arw -m tif
photo.py *.jpg *.png -m tif
photo.py *.arw -m jpg -q 92
photo.py *.arw -m tif -d
photo.py *.arw -m tif -i NAFNet-SIDD
photo.py *.arw -m tif -i NAFNet-GoPro
photo.py *.arw -m tif -i Restormer
photo.py *.arw -m tif -i Restormer-motion_deblurring
photo.py *.arw -m tif -i Restormer -f
photo.py *.arw -m tif -i Restormer -tf
photo.py *.arw -m tif -l
photo.py *.arw -m tif -l C:\\path\\to\\MyLUT.cube
photo.py *.arw -m tif -l -d -k
photo.py input\\**\\* -m tif --skip-rt -d
```

## Arguments
- `paths`: Files or folders to process (supports wildcards on Windows)
- `-m, --format`: Output format (`tif` default, or `jpg`)
- `--rt-bit-depth`: RawTherapee output bit depth (`auto`, `8`, `16`, `16f`, `32`) for TIFF/PNG-capable paths
- `-q, --quality`: JPEG quality (only for JPG output)
- `-o, --output`: Output folder name (defaults to format)
- `-d, --denoise`: Run AI inference after conversion using default model (`Restormer-real_denoising`)
- `-i, --inference MODEL`: Run AI inference with a specific model name (e.g. `NAFNet-SIDD`)
- `--tile-size`: Optional manual tile size override for AI tiling (auto-rounded to model-required multiple)
- `--overlap`: Optional manual overlap override for AI tiling
- `--overlap-fit`: Keep tile size fixed and auto-fit X/Y overlaps so all tiles stay full size (default: on)
- `--no-overlap-fit`: Disable overlap-fit and use fixed nominal step tiling
- `--pp3`: Prompt to choose a `.pp3` profile from `pp3/` next to this script (includes RAW sidecar mode)
- `-f, --fit`: Fit image dimensions to an exact tile grid using uniform scaling + center crop (no aspect distortion)
- `-tf, --tile-fit`: Keep image size and auto-fit tile size to image dimensions where possible
- `--calibrate`: Run CUDA full-frame calibration and save/update `denoise_cache.json`
- `--calibrate-all`: Force recalibration for all supported models and overwrite cached limits
- `--ai-safety-fallback`: Enable automatic safe retry chain when AI output looks suspicious
- `--dualdn-python`: Python executable used to launch DualDn script
- `--dualdn-script`: Path to DualDn inference script if auto-detection fails
- `--dualdn-cmd`: Custom DualDn command template (`{python} {script} {weights} {input} {output_dir}`)
- `-l, --lut`: Prompt for LUT selection, or pass a direct `.cube` file path
- `--no-lut`: Skip LUT application
- `-k, --keep`: Keep every intermediate stage with a unique stage suffix
- `--skip-rt`: Skip RawTherapee conversion stage (RAW files will be skipped)

## LUT Behavior
- If `-l` is passed without a direct `.cube` file path, the script prompts for a LUT choice.
- LUTs are searched in `LUT/` or `lut/` next to this script.
- When a LUT is applied, its name is appended to the output filename.

## Inference Behavior
- `-d` uses Restormer-real_denoising.
- `-i MODEL` runs the same inference pipeline with the selected model.
- Checkpoints are loaded from `F:\\AI\\Inference\\NAFNet` and `F:\\AI\\Inference\\Restormer`.
- `DualDn-Big` runs through DualDn's native Real_captured inference flow and returns an sRGB output image.
- Auto mode attempts full-frame on CUDA if within calibrated limits, otherwise tiled.
- Calibration results are saved in `denoise_cache.json` and reused per model.
- Calibration is opt-in via `--calibrate`.
- If no model is selected, `--calibrate` calibrates each supported model that is not yet cached.
- `--calibrate-all` forces calibration of all supported models even when cached.
- With `--fit`, image size is adjusted to exact tile counts without changing aspect ratio (scale + center crop).
- With `--tile-fit`, tile size is adjusted (instead of image size) to best fit image dimensions.
- With `--overlap-fit` (enabled by default), tile size is preserved and tile starts are redistributed so edge tiles remain full-sized.
- RAW default profile is `pp3/auto_film.pp3` when present; use `--pp3` to interactively pick another profile or RAW sidecar mode (`*.ext.pp3`) with default fallback.

## Processing Order
1. RawTherapee conversion (or direct non-RAW conversion/copy)
2. LUT application (if enabled)
3. AI inference (if enabled; NAFNet/Restormer RGB path)
4. TIFF compression (only when output is TIFF and inference is not used)
5. Special case: `DualDn-Big` replaces step 1+3 for RAW files using DualDn's external inference flow.

## Notes
- TIFF compression uses Deflate + Predictor 2 + Level 9 (lossless).
- If inference is enabled, the output is re-saved using Pillow (currently 8-bit).
- With `-k/--keep`, each stage writes to a new file with a stage suffix:
  `_rt`, `_lut_<name>`, `_denoise` (for `-d`), `_infer_<model>` (for `-i`), `_tifcomp`.
"""

import os
import sys
import platform
import shutil
import subprocess
import argparse
import glob
import json
import importlib.util
import math
import time
import uuid
from pathlib import Path

# --- AI INFERENCE SETTINGS ---
SCRIPT_DIR = Path(__file__).parent
DENOISE_CACHE = os.path.join(SCRIPT_DIR, "denoise_cache.json")
PP3_DIR = SCRIPT_DIR / "pp3"
DEFAULT_PP3_PROFILE = PP3_DIR / "auto_film.pp3"
PP3_MODE_SIDECAR = "__USE_RAW_SIDECAR_PP3__"
CALIBRATE_ASPECT = "3:2"
CALIBRATE_MAX_MP = 200
LUT_DIR = os.path.join(SCRIPT_DIR, "LUT")
ALT_LUT_DIR = os.path.join(SCRIPT_DIR, "lut")
TIF_COMPRESSION = "tiff_deflate"
TIF_PREDICTOR = 2
TIF_LEVEL = 9
RAW_EXTENSIONS = {'.arw', '.cr2', '.cr3', '.nef', '.dng', '.orf', '.raf', '.srw'}
RASTER_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp', '.webp'}
SUPPORTED_INPUT_EXTENSIONS = RAW_EXTENSIONS | RASTER_EXTENSIONS
DEFAULT_INFERENCE_MODEL = "Restormer-real_denoising"
INFERENCE_ROOT = r"F:\AI\Inference"
NAFNET_DIR = os.path.join(INFERENCE_ROOT, "NAFNet")
RESTORMER_DIR = os.path.join(INFERENCE_ROOT, "Restormer")
DUALDN_DIR = os.path.join(INFERENCE_ROOT, "DualDn")
DUALDN_OUTPUT_DIR = os.path.join(DUALDN_DIR, "_output")
INFERENCE_MODELS = {
    "NAFNet-SIDD": {
        "loader": "nafnet_local",
        "model_path": os.path.join(NAFNET_DIR, "NAFNet-SIDD-width64.pth"),
        "init_kwargs": {
            "img_channel": 3,
            "width": 64,
            "middle_blk_num": 12,
            "enc_blk_nums": [2, 2, 4, 8],
            "dec_blk_nums": [2, 2, 2, 2],
        },
    },
    "NAFNet-GoPro": {
        "loader": "nafnet_local",
        "model_path": os.path.join(NAFNET_DIR, "NAFNet-GoPro-width64.pth"),
        "init_kwargs": {
            "img_channel": 3,
            "width": 64,
            "middle_blk_num": 12,
            "enc_blk_nums": [2, 2, 4, 8],
            "dec_blk_nums": [2, 2, 2, 2],
        },
    },
    "NAFNet-REDS": {
        "loader": "nafnet_local",
        "model_path": os.path.join(NAFNET_DIR, "NAFNet-REDS-width64.pth"),
        "init_kwargs": {
            "img_channel": 3,
            "width": 64,
            "middle_blk_num": 12,
            "enc_blk_nums": [2, 2, 4, 8],
            "dec_blk_nums": [2, 2, 2, 2],
        },
    },
    "Restormer-real_denoising": {
        "loader": "restormer_external",
        "model_path": os.path.join(RESTORMER_DIR, "real_denoising.pth"),
        "init_kwargs": {
            "LayerNorm_type": "BiasFree",
        },
    },
    "Restormer-motion_deblurring": {
        "loader": "restormer_external",
        "model_path": os.path.join(RESTORMER_DIR, "motion_deblurring.pth"),
        "init_kwargs": {
            "LayerNorm_type": "BiasFree",
        },
    },
    "Restormer-deraining": {
        "loader": "restormer_external",
        "model_path": os.path.join(RESTORMER_DIR, "deraining.pth"),
        "init_kwargs": {
            "LayerNorm_type": "BiasFree",
        },
    },
    "Restormer-single_image_defocus_deblurring": {
        "loader": "restormer_external",
        "model_path": os.path.join(RESTORMER_DIR, "single_image_defocus_deblurring.pth"),
        "init_kwargs": {
            "LayerNorm_type": "BiasFree",
        },
    },
    "Restormer-dual_pixel_defocus_deblurring": {
        "loader": "restormer_external",
        "model_path": os.path.join(RESTORMER_DIR, "dual_pixel_defocus_deblurring.pth"),
        "init_kwargs": {
            "inp_channels": 6,
            "dual_pixel_task": True,
        },
        "supported_input_channels": 6,
        "unsupported_reason": "This checkpoint requires 6-channel dual-pixel input, but Photo.py currently feeds RGB images.",
    },
    "DualDn-Big": {
        "loader": "dualdn_external",
        "model_path": os.path.join(DUALDN_DIR, "DualDn_Big.pth"),
        "raw_only": True,
    },
}

_ARCH_MODULE_CACHE = {}
_LUT_CACHE = {}
TILING_DEFAULTS_BY_LOADER = {
    "nafnet_local": {
        "tile_size": 512,
        "overlap": 64,
        "tile_multiple": 16,
        "min_fit_tile": 128,
        "fallback_tiles": [512, 384, 320, 256, 224, 192, 160, 128],
    },
    "restormer_external": {
        "tile_size": 384,
        "overlap": 64,
        "tile_multiple": 8,
        "min_fit_tile": 128,
        "fallback_tiles": [384, 320, 288, 256, 224, 192, 160, 128],
    },
}

INFERENCE_MODEL_ALIASES = {}

def _import_module_from_file(module_name, file_path):
    cache_key = f"{module_name}::{file_path}"
    cached = _ARCH_MODULE_CACHE.get(cache_key)
    if cached is not None:
        return cached, None

    if not os.path.exists(file_path):
        return None, f"Module file not found: {file_path}"

    module_dir = str(Path(file_path).parent)
    added_path = False
    if module_dir not in sys.path:
        sys.path.insert(0, module_dir)
        added_path = True

    try:
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            return None, f"Failed to create import spec for: {file_path}"
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _ARCH_MODULE_CACHE[cache_key] = module
        return module, None
    except Exception as e:
        return None, str(e)
    finally:
        if added_path:
            try:
                sys.path.remove(module_dir)
            except ValueError:
                pass
 

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

def _import_tifffile():
    try:
        import tifffile
        return tifffile, None
    except Exception as e:
        return None, e

def _get_nafnet_arch():
    try:
        from nafnet_arch import NAFNet
        return NAFNet
    except Exception:
        return None

def _get_restormer_arch():
    module_path = os.path.join(RESTORMER_DIR, "restormer_arch.py")
    module, err = _import_module_from_file("photo_restormer_arch", module_path)
    if not module:
        print(f"   [AI] Failed to import Restormer architecture: {err}")
        return None
    restormer_cls = getattr(module, "Restormer", None)
    if not restormer_cls:
        print(f"   [AI] restormer_arch.py does not export Restormer class: {module_path}")
        return None
    return restormer_cls

def _resolve_inference_model_name(model_name):
    if not model_name:
        return None
    wanted = model_name.strip().lower()
    for canonical in INFERENCE_MODELS:
        if canonical.lower() == wanted:
            return canonical
    return None

def _get_inference_model_cfg(model_name):
    canonical = _resolve_inference_model_name(model_name)
    if not canonical:
        return None, None
    return canonical, INFERENCE_MODELS.get(canonical, {})

def _find_dualdn_script(override_path=None):
    candidates = []
    if override_path:
        candidates.append(override_path)
    candidates.extend([
        os.path.join(DUALDN_DIR, "inference_dualdn.py"),
        os.path.join(DUALDN_DIR, "test_dualdn.py"),
        os.path.join(DUALDN_DIR, "inference.py"),
        os.path.join(DUALDN_DIR, "test.py"),
        os.path.join(DUALDN_DIR, "scripts", "inference.py"),
        os.path.join(DUALDN_DIR, "scripts", "test.py"),
    ])
    for p in candidates:
        if p and os.path.isfile(p):
            return p
    return None

def _read_exif_noise_profile(raw_path):
    try:
        res = subprocess.run(
            ["exiftool", "-j", "-NoiseProfile", raw_path],
            capture_output=True,
            text=True,
        )
        if res.returncode != 0 or not res.stdout.strip():
            return None
        payload = json.loads(res.stdout)
        if not payload or not isinstance(payload, list):
            return None
        val = payload[0].get("NoiseProfile")
        if val is None:
            return None
        text = str(val).strip()
        if not text:
            return None
        return text
    except Exception:
        return None

def _run_dualdn_external_raw(raw_input_path, model_name, dualdn_python=None, dualdn_script=None, dualdn_cmd=None):
    canonical, cfg = _get_inference_model_cfg(model_name)
    if not canonical or not cfg:
        print(f"   [DualDn] Unknown model: {model_name}")
        return None
    if cfg.get("loader") != "dualdn_external":
        print(f"   [DualDn] Model is not a DualDn external model: {canonical}")
        return None

    weights = cfg.get("model_path")
    if not weights or not os.path.isfile(weights):
        print(f"   [DualDn] Checkpoint not found: {weights}")
        return None
    if not os.path.isfile(raw_input_path):
        print(f"   [DualDn] RAW input not found: {raw_input_path}")
        return None

    script_path = _find_dualdn_script(dualdn_script)
    if not script_path:
        print("   [DualDn] Could not find DualDn inference script.")
        print("   [DualDn] Pass --dualdn-script <path-to-script.py>.")
        return None

    python_exe = dualdn_python or sys.executable
    repo_root = DUALDN_DIR
    started = time.time()

    # Stage single-file inference into DualDn's expected Real_captured dataset layout.
    ds_root = os.path.join(repo_root, "datasets", "real_capture")
    raw_dir = os.path.join(ds_root, "Raw")
    ref_dir = os.path.join(ds_root, "ref_sRGB")
    list_dir = os.path.join(ds_root, "list_file")
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(ref_dir, exist_ok=True)
    os.makedirs(list_dir, exist_ok=True)

    src = Path(raw_input_path)
    tag = f"{src.stem}_{uuid.uuid4().hex[:8]}"
    staged_raw_name = f"{tag}{src.suffix.lower()}"
    staged_raw_path = os.path.join(raw_dir, staged_raw_name)
    staged_ref_path = os.path.join(ref_dir, f"{tag}.jpg")
    staged_list = os.path.join(list_dir, "val_list.txt")

    try:
        shutil.copy2(raw_input_path, staged_raw_path)
    except Exception as e:
        print(f"   [DualDn] Failed to stage RAW input: {e}")
        return None

    noise_profile = _read_exif_noise_profile(staged_raw_path)
    if not noise_profile:
        print("   [DualDn] Missing EXIF NoiseProfile in RAW file.")
        print("   [DualDn] DualDn Real_captured path requires NoiseProfile metadata.")
        print("   [DualDn] Use smartphone Pro RAW (as in DualDn docs), or use another model for this file.")
        return None

    # Optional same-prefix JPG for BGU color alignment. If absent, we disable BGU via force_yml.
    ref_src = None
    for ext in (".jpg", ".jpeg", ".JPG", ".JPEG"):
        p = src.with_suffix(ext)
        if p.exists():
            ref_src = str(p)
            break
    has_ref = False
    if ref_src:
        try:
            shutil.copy2(ref_src, staged_ref_path)
            has_ref = True
        except Exception as e:
            print(f"   [DualDn] Warning: failed to stage reference JPG ({e}); disabling BGU.")

    try:
        with open(staged_list, "w", encoding="utf-8") as f:
            f.write(staged_raw_name + "\n")
    except Exception as e:
        print(f"   [DualDn] Failed to update val list: {e}")
        return None

    if dualdn_cmd:
        try:
            cmd = dualdn_cmd.format(
                python=python_exe,
                script=script_path,
                weights=weights,
                input=staged_raw_path,
                output_dir=os.path.join(repo_root, "results"),
            )
        except Exception as e:
            print(f"   [DualDn] Invalid --dualdn-cmd template: {e}")
            return None
        res = subprocess.run(
            cmd,
            shell=True,
            cwd=os.path.dirname(script_path),
        )
        cmd_desc = cmd
    else:
        option_path = os.path.join(repo_root, "options", "DualDn_Big.yml")
        if not os.path.isfile(option_path):
            print(f"   [DualDn] Option file not found: {option_path}")
            return None
        cmd = [
            python_exe,
            script_path,
            "-opt",
            option_path,
            "--pretrained_model",
            weights,
            "--val_datasets",
            "Real_captured",
            "--force_yml",
            "datasets:val:val_datasets:Real_captured:data_path=datasets/real_capture",
        ]
        if not has_ref:
            cmd.append("datasets:val:val_datasets:Real_captured:BGU=false")
        res = subprocess.run(
            cmd,
            cwd=repo_root,
        )
        cmd_desc = " ".join(cmd)

    if res.returncode != 0:
        print("   [DualDn] Inference failed.")
        print(f"   [DualDn] Command: {cmd_desc}")
        return None

    best = None
    results_root = Path(repo_root) / "results"
    for p in results_root.rglob("*_ours.png"):
        if not p.is_file():
            continue
        try:
            mtime = p.stat().st_mtime
        except Exception:
            continue
        if mtime + 1.0 < started:
            continue
        # Prefer output that contains our staged stem.
        if tag not in p.name and best is not None:
            continue
        if best is None or mtime > best[0]:
            best = (mtime, p)
    if best:
        return str(best[1])

    print("   [DualDn] Inference ran, but no output image was found.")
    print(f"   [DualDn] Checked results root: {results_root}")
    return None

def _extract_state_dict_from_checkpoint(checkpoint):
    if isinstance(checkpoint, dict):
        for key in ("params_ema", "params", "state_dict", "model", "netG", "generator"):
            value = checkpoint.get(key)
            if isinstance(value, dict):
                checkpoint = value
                break
    if not isinstance(checkpoint, dict):
        return checkpoint
    if checkpoint and all(str(k).startswith("module.") for k in checkpoint.keys()):
        return {str(k)[7:]: v for k, v in checkpoint.items()}
    return checkpoint

def _resolve_tiling_config(cfg, tile_size=None, overlap=None):
    loader = cfg.get("loader", "")
    defaults = TILING_DEFAULTS_BY_LOADER.get(loader, {})

    user_tile = int(tile_size) if tile_size is not None else None
    user_overlap = int(overlap) if overlap is not None else None

    resolved_tile = int(user_tile if user_tile is not None else cfg.get("tile_size", defaults.get("tile_size", 512)))
    resolved_overlap = int(user_overlap if user_overlap is not None else cfg.get("overlap", defaults.get("overlap", 64)))
    tile_multiple = int(cfg.get("tile_multiple", defaults.get("tile_multiple", 16)))
    fallback_tiles = list(cfg.get("fallback_tiles", defaults.get("fallback_tiles", [resolved_tile, 384, 320, 256, 192, 128])))
    notes = []

    if resolved_tile < tile_multiple:
        resolved_tile = tile_multiple
    resolved_tile = max(tile_multiple, (resolved_tile // tile_multiple) * tile_multiple)
    if user_tile is not None and resolved_tile != user_tile:
        notes.append(f"tile size adjusted from {user_tile} to {resolved_tile} to match required multiple {tile_multiple}")

    max_overlap = max(0, resolved_tile - tile_multiple)
    resolved_overlap = max(0, min(resolved_overlap, max_overlap))
    if user_overlap is not None and resolved_overlap != user_overlap:
        notes.append(f"overlap adjusted from {user_overlap} to {resolved_overlap} (must be >=0 and < tile size)")

    normalized_fallbacks = []
    for t in [resolved_tile] + fallback_tiles:
        try:
            t = int(t)
        except Exception:
            continue
        if t < tile_multiple:
            continue
        t = max(tile_multiple, (t // tile_multiple) * tile_multiple)
        if t not in normalized_fallbacks:
            normalized_fallbacks.append(t)

    if not normalized_fallbacks:
        normalized_fallbacks = [resolved_tile]

    return resolved_tile, resolved_overlap, tile_multiple, normalized_fallbacks, notes

def _fit_image_to_tile_grid_pil(im, tile_size):
    from PIL import Image

    w, h = im.size
    if tile_size <= 0:
        return im, {"changed": False, "reason": "invalid_tile_size"}
    if (w % tile_size == 0) and (h % tile_size == 0):
        return im, {"changed": False, "reason": "already_aligned"}

    nx0 = max(1, int(round(w / tile_size)))
    ny0 = max(1, int(round(h / tile_size)))

    nx_candidates = {
        max(1, int(math.floor(w / tile_size))),
        max(1, int(math.ceil(w / tile_size))),
        nx0,
    }
    ny_candidates = {
        max(1, int(math.floor(h / tile_size))),
        max(1, int(math.ceil(h / tile_size))),
        ny0,
    }
    for d in range(-2, 3):
        nx_candidates.add(max(1, nx0 + d))
        ny_candidates.add(max(1, ny0 + d))

    best = None
    for nx in sorted(nx_candidates):
        for ny in sorted(ny_candidates):
            tw = nx * tile_size
            th = ny * tile_size

            # Keep aspect ratio: scale uniformly, then crop center to exact tile grid.
            scale = max(tw / w, th / h)
            sw = max(tw, int(round(w * scale)))
            sh = max(th, int(round(h * scale)))
            crop_w = sw - tw
            crop_h = sh - th

            scale_cost = abs(math.log(scale)) if scale > 0 else 1e9
            crop_cost = (crop_w / max(1, sw)) + (crop_h / max(1, sh))
            score = scale_cost + 0.3 * crop_cost

            cand = {
                "score": score,
                "nx": nx,
                "ny": ny,
                "target_w": tw,
                "target_h": th,
                "scaled_w": sw,
                "scaled_h": sh,
            }
            if best is None or cand["score"] < best["score"]:
                best = cand

    if best is None:
        return im, {"changed": False, "reason": "no_candidate"}

    tw = best["target_w"]
    th = best["target_h"]
    sw = best["scaled_w"]
    sh = best["scaled_h"]

    out = im
    if (sw, sh) != (w, h):
        out = out.resize((sw, sh), Image.Resampling.LANCZOS)

    left = max(0, (sw - tw) // 2)
    top = max(0, (sh - th) // 2)
    out = out.crop((left, top, left + tw, top + th))

    return out, {
        "changed": True,
        "orig_w": w,
        "orig_h": h,
        "scaled_w": sw,
        "scaled_h": sh,
        "final_w": tw,
        "final_h": th,
        "tile_size": tile_size,
        "tiles_x": best["nx"],
        "tiles_y": best["ny"],
        "crop_left": left,
        "crop_top": top,
        "crop_right": max(0, sw - (left + tw)),
        "crop_bottom": max(0, sh - (top + th)),
        "crop_total_w": max(0, sw - tw),
        "crop_total_h": max(0, sh - th),
    }

def _fit_image_to_tile_grid_np(img_np, tile_size, torch=None, F=None):
    h, w = img_np.shape[:2]
    if tile_size <= 0:
        return img_np, {"changed": False, "reason": "invalid_tile_size"}
    if (w % tile_size == 0) and (h % tile_size == 0):
        return img_np, {"changed": False, "reason": "already_aligned"}

    nx0 = max(1, int(round(w / tile_size)))
    ny0 = max(1, int(round(h / tile_size)))

    nx_candidates = {
        max(1, int(math.floor(w / tile_size))),
        max(1, int(math.ceil(w / tile_size))),
        nx0,
    }
    ny_candidates = {
        max(1, int(math.floor(h / tile_size))),
        max(1, int(math.ceil(h / tile_size))),
        ny0,
    }
    for d in range(-2, 3):
        nx_candidates.add(max(1, nx0 + d))
        ny_candidates.add(max(1, ny0 + d))

    best = None
    for nx in sorted(nx_candidates):
        for ny in sorted(ny_candidates):
            tw = nx * tile_size
            th = ny * tile_size

            scale = max(tw / w, th / h)
            sw = max(tw, int(round(w * scale)))
            sh = max(th, int(round(h * scale)))
            crop_w = sw - tw
            crop_h = sh - th

            scale_cost = abs(math.log(scale)) if scale > 0 else 1e9
            crop_cost = (crop_w / max(1, sw)) + (crop_h / max(1, sh))
            score = scale_cost + 0.3 * crop_cost

            cand = {
                "score": score,
                "nx": nx,
                "ny": ny,
                "target_w": tw,
                "target_h": th,
                "scaled_w": sw,
                "scaled_h": sh,
            }
            if best is None or cand["score"] < best["score"]:
                best = cand

    if best is None:
        return img_np, {"changed": False, "reason": "no_candidate"}

    tw = best["target_w"]
    th = best["target_h"]
    sw = best["scaled_w"]
    sh = best["scaled_h"]

    out = img_np
    if (sw, sh) != (w, h):
        # Use torch interpolate so this works for float tensors independent of PIL image modes/bit depth.
        t = torch.from_numpy(out.transpose(2, 0, 1)).unsqueeze(0)
        t = F.interpolate(t, size=(sh, sw), mode="bicubic", align_corners=False)
        out = t.squeeze(0).permute(1, 2, 0).cpu().numpy()

    left = max(0, (sw - tw) // 2)
    top = max(0, (sh - th) // 2)
    out = out[top:top + th, left:left + tw, :]

    return out, {
        "changed": True,
        "orig_w": w,
        "orig_h": h,
        "scaled_w": sw,
        "scaled_h": sh,
        "final_w": tw,
        "final_h": th,
        "tile_size": tile_size,
        "tiles_x": best["nx"],
        "tiles_y": best["ny"],
        "crop_left": left,
        "crop_top": top,
        "crop_right": max(0, sw - (left + tw)),
        "crop_bottom": max(0, sh - (top + th)),
        "crop_total_w": max(0, sw - tw),
        "crop_total_h": max(0, sh - th),
    }

def _read_image_for_ai(image_path, np):
    ext = Path(image_path).suffix.lower()
    tifffile, tf_err = _import_tifffile()

    if ext in {".tif", ".tiff"} and tifffile is not None:
        try:
            arr = tifffile.imread(image_path)
        except Exception as e:
            print(f"   [AI] Failed to read TIFF with tifffile: {e}")
            return None, None

        if arr.ndim == 2:
            arr = np.stack([arr, arr, arr], axis=-1)
        elif arr.ndim == 3 and arr.shape[0] in {3, 4} and arr.shape[-1] not in {3, 4}:
            arr = np.transpose(arr, (1, 2, 0))
        if arr.ndim != 3:
            print(f"   [AI] Unsupported TIFF shape: {arr.shape}")
            return None, None
        if arr.shape[-1] == 4:
            arr = arr[:, :, :3]
        elif arr.shape[-1] == 1:
            arr = np.repeat(arr, 3, axis=-1)

        src_dtype = arr.dtype
        if np.issubdtype(src_dtype, np.integer):
            maxv = np.iinfo(src_dtype).max
            img = arr.astype(np.float32) / float(maxv)
            target_dtype = np.uint16 if maxv > 255 else np.uint8
            scale_max = 65535.0 if target_dtype == np.uint16 else 255.0
        elif np.issubdtype(src_dtype, np.floating):
            img = arr.astype(np.float32)
            if img.max() > 1.0 or img.min() < 0.0:
                img = np.clip(img, 0.0, 1.0)
            target_dtype = np.float32
            scale_max = 1.0
        else:
            print(f"   [AI] Unsupported TIFF dtype: {src_dtype}")
            return None, None

        return img, {
            "source": "tiff",
            "src_dtype": str(src_dtype),
            "target_dtype": target_dtype,
            "scale_max": scale_max,
            "tifffile": tifffile,
        }

    # Fallback path: Pillow (8-bit RGB path).
    Image, pil_err = _import_pil_only()
    if Image is None:
        print(f"   [AI] Failed to import Pillow for image read: {pil_err}")
        if tf_err:
            print(f"   [AI] tifffile unavailable: {tf_err}")
        return None, None
    try:
        with Image.open(image_path) as im:
            im = im.convert("RGB")
            img = np.asarray(im).astype(np.float32) / 255.0
        return img, {
            "source": "pil",
            "src_dtype": "uint8",
            "target_dtype": np.uint8,
            "scale_max": 255.0,
            "tifffile": tifffile,
        }
    except Exception as e:
        print(f"   [AI] Failed to read image: {e}")
        return None, None

def _write_ai_output(image_path, img_float, out_format, quality, io_info, np):
    img_float = np.clip(img_float.astype(np.float32), 0.0, 1.0)

    if out_format == "jpg":
        Image, err = _import_pil_only()
        if Image is None:
            print(f"   [AI] Failed to import Pillow for JPG write: {err}")
            return False
        out_img = (img_float * 255.0 + 0.5).clip(0, 255).astype(np.uint8)
        try:
            Image.fromarray(out_img, mode="RGB").save(image_path, quality=quality)
            return True
        except Exception as e:
            print(f"   [AI] Failed to write JPG: {e}")
            return False

    # TIFF output path: preserve source precision where possible.
    target_dtype = io_info.get("target_dtype", np.uint8)
    tifffile = io_info.get("tifffile")

    if target_dtype == np.uint16:
        out_arr = (img_float * 65535.0 + 0.5).clip(0, 65535).astype(np.uint16)
    elif target_dtype == np.float32:
        out_arr = img_float.astype(np.float32)
    else:
        out_arr = (img_float * 255.0 + 0.5).clip(0, 255).astype(np.uint8)

    if tifffile is None:
        # Final fallback to Pillow if tifffile import failed.
        Image, err = _import_pil_only()
        if Image is None:
            print(f"   [AI] Failed to import tifffile and Pillow for TIFF write: {err}")
            return False
        try:
            pil_out = out_arr
            if pil_out.dtype != np.uint8:
                # Pillow fallback cannot reliably store RGB uint16; degrade as last resort.
                pil_out = (img_float * 255.0 + 0.5).clip(0, 255).astype(np.uint8)
            Image.fromarray(pil_out, mode="RGB").save(
                image_path,
                compression=TIF_COMPRESSION,
                predictor=TIF_PREDICTOR,
                compress_level=TIF_LEVEL,
            )
            print("   [AI] Warning: TIFF writer fallback used 8-bit Pillow path.")
            return True
        except Exception as e:
            print(f"   [AI] Failed to write TIFF: {e}")
            return False

    try:
        tifffile.imwrite(
            image_path,
            out_arr,
            compression="deflate",
            compressionargs={"level": TIF_LEVEL},
            predictor=TIF_PREDICTOR,
            photometric="rgb",
        )
        return True
    except Exception as e:
        print(f"   [AI] Failed to write TIFF with tifffile: {e}")
        return False

def _load_cube_lut(path, np):
    cached = _LUT_CACHE.get(path)
    if cached is not None:
        return cached

    size = None
    domain_min = np.array([0.0, 0.0, 0.0], dtype=np.float32)
    domain_max = np.array([1.0, 1.0, 1.0], dtype=np.float32)
    values = []

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            key = parts[0].upper()
            if key == "TITLE":
                continue
            if key == "LUT_1D_SIZE":
                raise ValueError("1D LUT is not supported. Provide a 3D .cube LUT.")
            if key == "LUT_3D_SIZE":
                if len(parts) != 2:
                    raise ValueError("Invalid LUT_3D_SIZE line.")
                size = int(parts[1])
                continue
            if key == "DOMAIN_MIN" and len(parts) >= 4:
                domain_min = np.array([float(parts[1]), float(parts[2]), float(parts[3])], dtype=np.float32)
                continue
            if key == "DOMAIN_MAX" and len(parts) >= 4:
                domain_max = np.array([float(parts[1]), float(parts[2]), float(parts[3])], dtype=np.float32)
                continue

            if len(parts) >= 3:
                try:
                    values.append([float(parts[0]), float(parts[1]), float(parts[2])])
                except Exception:
                    continue

    if size is None or size < 2:
        raise ValueError("Missing or invalid LUT_3D_SIZE.")

    expected = size * size * size
    if len(values) != expected:
        raise ValueError(f"LUT value count mismatch: expected {expected}, got {len(values)}.")

    table = np.asarray(values, dtype=np.float32).reshape((size, size, size, 3))
    # .cube commonly stores red-fastest order; reshape makes axes [blue, green, red, channels].
    lut = {
        "size": size,
        "table_bgr": table,
        "domain_min": domain_min,
        "domain_max": domain_max,
    }
    _LUT_CACHE[path] = lut
    return lut

def _apply_lut_np(img, lut, np):
    table = lut["table_bgr"]
    size = lut["size"]
    dmin = lut["domain_min"]
    dmax = lut["domain_max"]

    den = np.maximum(dmax - dmin, 1e-8)
    x = (img.astype(np.float32) - dmin) / den
    x = np.clip(x, 0.0, 1.0)
    x = x * float(size - 1)

    r = x[..., 0]
    g = x[..., 1]
    b = x[..., 2]

    r0 = np.floor(r).astype(np.int32)
    g0 = np.floor(g).astype(np.int32)
    b0 = np.floor(b).astype(np.int32)
    r1 = np.minimum(r0 + 1, size - 1)
    g1 = np.minimum(g0 + 1, size - 1)
    b1 = np.minimum(b0 + 1, size - 1)

    fr = (r - r0).astype(np.float32)[..., None]
    fg = (g - g0).astype(np.float32)[..., None]
    fb = (b - b0).astype(np.float32)[..., None]

    c000 = table[b0, g0, r0]
    c100 = table[b0, g0, r1]
    c010 = table[b0, g1, r0]
    c110 = table[b0, g1, r1]
    c001 = table[b1, g0, r0]
    c101 = table[b1, g0, r1]
    c011 = table[b1, g1, r0]
    c111 = table[b1, g1, r1]

    c00 = c000 * (1.0 - fr) + c100 * fr
    c10 = c010 * (1.0 - fr) + c110 * fr
    c01 = c001 * (1.0 - fr) + c101 * fr
    c11 = c011 * (1.0 - fr) + c111 * fr
    c0 = c00 * (1.0 - fg) + c10 * fg
    c1 = c01 * (1.0 - fg) + c11 * fg
    out = c0 * (1.0 - fb) + c1 * fb

    return np.clip(out.astype(np.float32), 0.0, 1.0)

def _fit_tile_size_to_image_dims(width, height, base_tile, tile_multiple, min_tile=128):
    base_tile = max(tile_multiple, int(base_tile))
    min_tile = max(tile_multiple, int(min_tile))
    gcd_wh = math.gcd(int(width), int(height))

    # Exact-fit candidates: divisors of gcd(width, height) that honor tile multiple.
    candidates = set()
    limit = int(math.isqrt(gcd_wh))
    for i in range(1, limit + 1):
        if gcd_wh % i == 0:
            a = i
            b = gcd_wh // i
            if a % tile_multiple == 0 and a >= min_tile:
                candidates.add(a)
            if b % tile_multiple == 0 and b >= min_tile:
                candidates.add(b)

    if candidates:
        sorted_cands = sorted(candidates)
        best = min(sorted_cands, key=lambda t: (abs(t - base_tile), -t))
        return best, True, {"gcd": gcd_wh, "candidates": len(sorted_cands)}

    # No exact tile exists under required multiple; keep current tile.
    return base_tile, False, {"gcd": gcd_wh, "candidates": 0, "min_tile": min_tile}

def _run_tiled_with_fallback(img_tensor, model, tile_candidates, overlap=64, overlap_fit=False, torch=None, F=None, np=None, model_name="model"):
    last_error = None
    attempted = False
    for tile in tile_candidates:
        use_overlap = min(overlap, max(0, tile - 16))
        try:
            fit_tag = ", overlap-fit" if overlap_fit else ""
            if not attempted:
                print(f"   [AI] Tiled pass: tile {tile}, overlap {use_overlap}{fit_tag}")
            else:
                print(f"   [AI] Retrying {model_name} with tile {tile}, overlap {use_overlap}{fit_tag}")
            attempted = True
            restored = _tile_process_overlap_blend(
                img_tensor,
                model,
                tile_size=tile,
                overlap=use_overlap,
                overlap_fit=overlap_fit,
                torch=torch,
                F=F,
                np=np,
            )
            return restored, tile, use_overlap
        except RuntimeError as e:
            if "out of memory" in str(e).lower():
                last_error = e
                print(f"   [AI] Tile {tile} OOM. Trying next candidate.")
                if torch is not None and torch.cuda.is_available():
                    torch.cuda.empty_cache()
                continue
            raise
    if last_error:
        raise last_error
    raise RuntimeError("Tiled inference failed with no candidates.")

def _compute_ai_stats(img_in, img_out, np):
    finite = np.isfinite(img_out).all()
    out_min = float(np.nanmin(img_out))
    out_max = float(np.nanmax(img_out))
    out_mean = float(np.nanmean(img_out))
    out_std = float(np.nanstd(img_out))
    delta = img_out - img_in
    delta_abs_mean = float(np.nanmean(np.abs(delta)))
    delta_std = float(np.nanstd(delta))
    return {
        "finite": finite,
        "out_min": out_min,
        "out_max": out_max,
        "out_mean": out_mean,
        "out_std": out_std,
        "delta_abs_mean": delta_abs_mean,
        "delta_std": delta_std,
    }

def _is_ai_output_suspicious(stats):
    reasons = []
    if not stats["finite"]:
        reasons.append("non-finite values detected")
    if stats["out_min"] < -0.05 or stats["out_max"] > 1.05:
        reasons.append("output out of expected [0,1] range")
    if stats["delta_std"] > 0.30 and stats["delta_abs_mean"] > 0.18:
        reasons.append("very large high-frequency residual change")
    if stats["out_std"] > 0.45:
        reasons.append("very high output variance")
    return (len(reasons) > 0), reasons

def _compute_fitted_tile_starts(length, tile_size, overlap, overlap_fit):
    if length <= tile_size:
        return [0]

    nominal_step = max(1, tile_size - overlap)
    if not overlap_fit:
        return list(range(0, length, nominal_step))

    # Keep tile size fixed and redistribute starts so first tile starts at 0 and
    # last tile ends exactly at image boundary (no partial edge tile).
    tile_count = int(math.ceil((length - tile_size) / nominal_step)) + 1
    max_start = max(0, length - tile_size)
    if tile_count <= 1 or max_start == 0:
        return [0]
    return [(i * max_start) // (tile_count - 1) for i in range(tile_count)]

def _analyze_axis_tiling(length, tile_size, overlap, overlap_fit):
    starts = _compute_fitted_tile_starts(length, tile_size, overlap, overlap_fit)
    lengths = []
    deficits = []
    for s in starts:
        end = min(s + tile_size, length)
        curr = max(0, end - s)
        lengths.append(curr)
        deficits.append(max(0, tile_size - curr))
    full_count = sum(1 for v in lengths if v == tile_size)
    partial_count = len(lengths) - full_count
    ends = [min(s + tile_size, length) for s in starts]
    max_end = max(ends) if ends else 0
    steps = [starts[i + 1] - starts[i] for i in range(len(starts) - 1)]
    return {
        "starts": starts,
        "count": len(starts),
        "full_count": full_count,
        "partial_count": partial_count,
        "uncovered_px": max(0, length - max_end),
        "total_deficit_px": int(sum(deficits)),
        "last_deficit_px": int(deficits[-1] if deficits else 0),
        "step_min": int(min(steps)) if steps else 0,
        "step_max": int(max(steps)) if steps else 0,
    }

def _report_tiling_math(width, height, tile_size, overlap, overlap_fit, label="active"):
    nominal_step = max(1, tile_size - overlap)
    x = _analyze_axis_tiling(width, tile_size, overlap, overlap_fit)
    y = _analyze_axis_tiling(height, tile_size, overlap, overlap_fit)
    total_tiles = x["count"] * y["count"]
    full_tiles = x["full_count"] * y["full_count"]
    nonfull_tiles = total_tiles - full_tiles
    print(f"   [AI] Tiling math ({label}): image {width}x{height}, tile={tile_size}, overlap={overlap}, nominal_step={nominal_step}, overlap_fit={overlap_fit}")
    print(
        f"   [AI]   X-axis: tiles={x['count']} full={x['full_count']} partial={x['partial_count']} "
        f"starts={x['starts'][0]}..{x['starts'][-1]} step[min,max]={x['step_min']},{x['step_max']} "
        f"uncovered_px={x['uncovered_px']} spare_deficit_px={x['total_deficit_px']} right_edge_deficit_px={x['last_deficit_px']}"
    )
    print(
        f"   [AI]   Y-axis: tiles={y['count']} full={y['full_count']} partial={y['partial_count']} "
        f"starts={y['starts'][0]}..{y['starts'][-1]} step[min,max]={y['step_min']},{y['step_max']} "
        f"uncovered_px={y['uncovered_px']} spare_deficit_px={y['total_deficit_px']} bottom_edge_deficit_px={y['last_deficit_px']}"
    )
    print(f"   [AI]   Grid: {x['count']}x{y['count']} => total_tiles={total_tiles}, full_tiles={full_tiles}, nonfull_tiles={nonfull_tiles}")
    return {"x": x, "y": y, "total_tiles": total_tiles, "full_tiles": full_tiles, "nonfull_tiles": nonfull_tiles}

def _tile_process_overlap_blend(img_tensor, model, tile_size=512, overlap=64, overlap_fit=False, torch=None, F=None, np=None):
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

    y_starts = _compute_fitted_tile_starts(h, tile_size, overlap, overlap_fit)
    x_starts = _compute_fitted_tile_starts(w, tile_size, overlap, overlap_fit)
    for y in y_starts:
        for x in x_starts:
            if overlap_fit and (y + tile_size <= h) and (x + tile_size <= w):
                y_end = y + tile_size
                x_end = x + tile_size
                curr_h = tile_size
                curr_w = tile_size
            else:
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

def _get_inference_model(model_name, torch=None):
    canonical = _resolve_inference_model_name(model_name)
    if not canonical:
        available = ", ".join(sorted(INFERENCE_MODELS.keys()))
        print(f"   [AI] Unknown inference model: {model_name}")
        print(f"   [AI] Available models: {available}")
        return None

    cfg = INFERENCE_MODELS[canonical]
    loader = cfg.get("loader")
    if loader == "nafnet_local":
        ModelClass = _get_nafnet_arch()
        if not ModelClass:
            print("   [AI] Missing nafnet_arch.py (required for NAFNet).")
            return None
    elif loader == "restormer_external":
        ModelClass = _get_restormer_arch()
        if not ModelClass:
            return None
    else:
        print(f"   [AI] Model loader not implemented for: {canonical}")
        return None

    supported_input_channels = cfg.get("supported_input_channels", 3)
    if supported_input_channels != 3:
        reason = cfg.get("unsupported_reason") or f"Model expects {supported_input_channels} input channels."
        print(f"   [AI] Model not supported in current RGB pipeline: {canonical}")
        print(f"   [AI] {reason}")
        return None

    model_path = cfg["model_path"]
    if not os.path.exists(model_path):
        print(f"   [AI] Model not found at: {model_path}")
        return None

    model = ModelClass(**cfg.get("init_kwargs", {}))

    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    try:
        checkpoint = torch.load(model_path, map_location=device)
        state_dict = _extract_state_dict_from_checkpoint(checkpoint)
        try:
            model.load_state_dict(state_dict, strict=True)
        except Exception as strict_err:
            # Fallback for minor key mismatches between released checkpoints and local arch variants.
            missing, unexpected = model.load_state_dict(state_dict, strict=False)
            if missing or unexpected:
                print(f"   [AI] Warning loading {canonical} with relaxed key match.")
                if missing:
                    print(f"   [AI] Missing keys: {len(missing)}")
                if unexpected:
                    print(f"   [AI] Unexpected keys: {len(unexpected)}")
            else:
                print(f"   [AI] Warning: strict load failed, relaxed load used ({strict_err}).")
        model.to(device).eval()
        return model, device, canonical, cfg
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

def _get_calibratable_model_names():
    names = []
    for name, cfg in INFERENCE_MODELS.items():
        loader = cfg.get("loader")
        if loader not in {"nafnet_local", "restormer_external"}:
            continue
        if cfg.get("supported_input_channels", 3) == 3:
            names.append(name)
    return sorted(names)

def _calibrate_model_cache_entry(model_name, force=False):
    np, torch, F, Image = _import_denoise_deps()
    if np is None:
        print(f"   [AI] Calibration skipped for {model_name} (missing dependencies): {Image}")
        return False

    model_info = _get_inference_model(model_name=model_name, torch=torch)
    if not model_info:
        print(f"   [AI] Calibration skipped for {model_name} (model load failed).")
        return False
    model, device, canonical_model_name, _ = model_info

    cache = _load_denoise_cache() or {}
    models_cache = cache.setdefault("models", {})
    model_cache = models_cache.get(canonical_model_name, {})
    if model_cache.get("max_full_pixels") and not force:
        print(f"   [AI] Calibration cached for {canonical_model_name}; skipping (use --calibrate-all to force).")
        return True

    if device != "cuda":
        print(f"   [AI] Calibration for {canonical_model_name} requires CUDA; current device: {device}.")
        return False

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
        if not result:
            print(f"   [AI] Calibration failed for {canonical_model_name}: no valid size found.")
            return False

        mp, w, h = result
        props = torch.cuda.get_device_properties(0)
        models_cache[canonical_model_name] = {
            "gpu_name": props.name,
            "total_vram_mb": int(props.total_memory / (1024 ** 2)),
            "max_full_pixels": int(w * h),
            "max_full_mp": round(mp, 2),
            "aspect": CALIBRATE_ASPECT,
        }
        _save_denoise_cache(cache)
        print(f"   [AI] Calibration saved for {canonical_model_name}: ~{round(mp, 2)} MP ({w}x{h})")
        return True
    except Exception as e:
        print(f"   [AI] Calibration failed for {canonical_model_name}: {e}")
        return False

def _run_denoise_srgb_with_model(img_srgb_np, model, device, torch=None, F=None, np=None, denoise_mode="auto", tile_size=512, overlap=64, overlap_fit=False, max_full_pixels=None, input_multiple=16, tile_candidates=None, model_name="model", allow_full_without_limit=False, safety_fallback=False):
    print(f"   [AI] Running denoise on {device.upper()}...")
    img_tensor = torch.from_numpy(np.transpose(img_srgb_np, (2, 0, 1))).float().unsqueeze(0).to(device)
    img_tensor, pad = _pad_to_multiple(img_tensor, multiple=input_multiple, torch=torch, F=F)
    pixels = img_tensor.shape[-1] * img_tensor.shape[-2]

    try_full = (denoise_mode == "full") or (
        denoise_mode == "auto"
        and device == "cuda"
        and (
            (max_full_pixels is not None and pixels <= max_full_pixels)
            or (max_full_pixels is None and allow_full_without_limit)
        )
    )
    used_full = False
    tile_candidates = tile_candidates or [tile_size]

    def run_attempt(label, prefer_full, use_amp, attempt_overlap, attempt_tile_candidates):
        nonlocal used_full
        print(
            f"   [AI] Attempt '{label}': "
            f"prefer_full={prefer_full}, amp={use_amp}, overlap={attempt_overlap}, "
            f"tiles={attempt_tile_candidates[:4]}{'...' if len(attempt_tile_candidates) > 4 else ''}"
        )
        local_used_full = False
        local_used_tile = None
        local_used_overlap = None
        if prefer_full and device == "cuda":
            try:
                with torch.no_grad():
                    if use_amp:
                        with torch.amp.autocast("cuda"):
                            restored_local = model(img_tensor)
                    else:
                        restored_local = model(img_tensor)
                local_used_full = True
            except RuntimeError as e:
                if "out of memory" in str(e).lower():
                    print("   [AI] Full-frame OOM, switching to tiled for this attempt.")
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                    restored_local, local_used_tile, local_used_overlap = _run_tiled_with_fallback(
                        img_tensor,
                        model,
                        tile_candidates=attempt_tile_candidates,
                        overlap=attempt_overlap,
                        overlap_fit=overlap_fit,
                        torch=torch,
                        F=F,
                        np=np,
                        model_name=model_name,
                    )
                else:
                    raise
        else:
            restored_local, local_used_tile, local_used_overlap = _run_tiled_with_fallback(
                img_tensor,
                model,
                tile_candidates=attempt_tile_candidates,
                overlap=attempt_overlap,
                overlap_fit=overlap_fit,
                torch=torch,
                F=F,
                np=np,
                model_name=model_name,
            )

        restored_local = _unpad(restored_local, pad)
        img_local = restored_local.clamp(0, 1).cpu().detach().permute(0, 2, 3, 1).squeeze(0).numpy()
        stats = _compute_ai_stats(img_srgb_np, img_local, np=np)
        print(
            f"   [AI] Attempt '{label}' stats: "
            f"finite={stats['finite']}, out[min={stats['out_min']:.4f}, max={stats['out_max']:.4f}, std={stats['out_std']:.4f}], "
            f"delta[abs_mean={stats['delta_abs_mean']:.4f}, std={stats['delta_std']:.4f}]"
        )
        suspicious, reasons = _is_ai_output_suspicious(stats)
        if suspicious:
            print(f"   [AI] Attempt '{label}' flagged suspicious: {', '.join(reasons)}")
        used_full = local_used_full
        return img_local, suspicious, reasons, local_used_tile, local_used_overlap, local_used_full

    attempts = []
    attempts.append({
        "label": "primary",
        "prefer_full": bool(try_full and device == "cuda"),
        "use_amp": True,
        "overlap": overlap,
        "tile_candidates": list(tile_candidates),
    })
    if safety_fallback:
        safer_overlap = min(max(overlap, 96), max(0, tile_candidates[0] - 16))
        safer_tiles = sorted(set(tile_candidates), reverse=True)
        attempts.append({
            "label": "safety_fp32_wider_overlap",
            "prefer_full": False,
            "use_amp": False,
            "overlap": safer_overlap,
            "tile_candidates": safer_tiles,
        })
        attempts.append({
            "label": "safety_small_tiles_fp32",
            "prefer_full": False,
            "use_amp": False,
            "overlap": min(max(safer_overlap, 96), max(0, 320 - 16)),
            "tile_candidates": [t for t in safer_tiles if t <= 320] or safer_tiles[-3:],
        })

    chosen = None
    for idx, attempt in enumerate(attempts, 1):
        img_candidate, suspicious, reasons, used_tile, used_ov, used_full_local = run_attempt(
            attempt["label"],
            attempt["prefer_full"],
            attempt["use_amp"],
            attempt["overlap"],
            attempt["tile_candidates"],
        )
        if not suspicious:
            if idx > 1:
                print(f"   [AI] Safety fallback succeeded on attempt '{attempt['label']}'.")
            chosen = img_candidate
            break
        else:
            if idx == 1 and not safety_fallback:
                print("   [AI] Suspicious output detected, but safety fallback is disabled.")
                print("   [AI] Re-run with --ai-safety-fallback to enable automatic safe retries.")
                chosen = img_candidate
                break
            print(f"   [AI] Attempt '{attempt['label']}' rejected; continuing fallback chain.")
            chosen = img_candidate

    if chosen is None:
        raise RuntimeError("AI denoise produced no output.")

    return chosen, used_full, pixels

def _denoise_image_file(image_path, out_format="jpg", quality=92, denoise_mode="auto", tile_size=None, overlap=None, model_name=DEFAULT_INFERENCE_MODEL, calibrate=False, fit=False, tile_fit=False, overlap_fit=False, safety_fallback=False):
    np, torch, F, Image = _import_denoise_deps()
    if np is None:
        print(f"   [AI] Missing denoise dependencies: {Image}")
        return False

    model_info = _get_inference_model(model_name=model_name, torch=torch)
    if not model_info:
        return False
    model, device, canonical_model_name, model_cfg = model_info
    tile_size, overlap, tile_multiple, tile_candidates, tiling_notes = _resolve_tiling_config(
        model_cfg,
        tile_size=tile_size,
        overlap=overlap,
    )
    for note in tiling_notes:
        print(f"   [AI] Note: {note}")

    img, io_info = _read_image_for_ai(image_path, np=np)
    if img is None:
        return False

    h, w = img.shape[:2]
    if tile_fit:
        orig_tile = tile_size
        min_fit_tile = model_cfg.get(
            "min_fit_tile",
            TILING_DEFAULTS_BY_LOADER.get(model_cfg.get("loader", ""), {}).get("min_fit_tile", 128),
        )
        fitted_tile, exact, meta = _fit_tile_size_to_image_dims(
            w,
            h,
            base_tile=tile_size,
            tile_multiple=tile_multiple,
            min_tile=min_fit_tile,
        )
        tile_size = fitted_tile
        max_overlap = max(0, tile_size - tile_multiple)
        overlap = max(0, min(overlap, max_overlap))
        tile_candidates = [tile_size] + [t for t in tile_candidates if t != tile_size]
        if exact:
            print(
                f"   [AI] Tile-fit: image {w}x{h}, tile {orig_tile} -> {tile_size} "
                f"(exact grid, gcd={meta['gcd']})"
            )
        else:
            print(
                f"   [AI] Tile-fit: no exact tile found for {w}x{h} with multiple {tile_multiple} "
                f"and min tile {min_fit_tile}; using tile {tile_size} (gcd={meta['gcd']})"
            )
        nx = (w + tile_size - 1) // tile_size
        ny = (h + tile_size - 1) // tile_size
        spare_w = (tile_size - (w % tile_size)) % tile_size
        spare_h = (tile_size - (h % tile_size)) % tile_size
        print(
            f"   [AI] Tile-fit math: nx=ceil({w}/{tile_size})={nx}, ny=ceil({h}/{tile_size})={ny}, "
            f"spare_if_grid_aligned=+{spare_w}px right, +{spare_h}px bottom"
        )

    if fit:
        img, fit_info = _fit_image_to_tile_grid_np(img, tile_size=tile_size, torch=torch, F=F)
        if fit_info.get("changed"):
            print(
                f"   [AI] Fit applied: "
                f"{fit_info['orig_w']}x{fit_info['orig_h']} -> "
                f"{fit_info['scaled_w']}x{fit_info['scaled_h']} -> "
                f"{fit_info['final_w']}x{fit_info['final_h']} "
                f"({fit_info['tiles_x']}x{fit_info['tiles_y']} tiles @ {fit_info['tile_size']})"
            )
            print(
                f"   [AI] Fit math: scale={fit_info['scaled_w']}/{fit_info['orig_w']} and {fit_info['scaled_h']}/{fit_info['orig_h']} (uniform), "
                f"crop_total=({fit_info['crop_total_w']}px, {fit_info['crop_total_h']}px), "
                f"crop_ltrb=({fit_info['crop_left']},{fit_info['crop_top']},{fit_info['crop_right']},{fit_info['crop_bottom']})"
            )
    h, w = img.shape[:2]

    fit_mode = ", overlap-fit on" if overlap_fit else ""
    print(f"   [AI] Tiling config for {canonical_model_name}: tile {tile_size}, overlap {overlap}, multiple {tile_multiple}{fit_mode}")
    if fit or tile_fit or overlap_fit:
        _report_tiling_math(w, h, tile_size, overlap, overlap_fit, label="post-fit")

    cache = _load_denoise_cache() or {}
    models_cache = cache.setdefault("models", {})
    model_cache = models_cache.get(canonical_model_name, {})
    if not model_cache and canonical_model_name == DEFAULT_INFERENCE_MODEL and cache.get("max_full_pixels"):
        # Backward compatibility for legacy flat cache format.
        model_cache = {
            "max_full_pixels": cache.get("max_full_pixels"),
            "max_full_mp": cache.get("max_full_mp"),
            "aspect": cache.get("aspect"),
            "gpu_name": cache.get("gpu_name"),
            "total_vram_mb": cache.get("total_vram_mb"),
        }
        models_cache[canonical_model_name] = model_cache
    max_full_pixels = model_cache.get("max_full_pixels")
    if denoise_mode == "auto" and device == "cuda" and max_full_pixels is None and calibrate:
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
                model_cache = {
                    "gpu_name": props.name,
                    "total_vram_mb": int(props.total_memory / (1024 ** 2)),
                    "max_full_pixels": int(w * h),
                    "max_full_mp": round(mp, 2),
                    "aspect": CALIBRATE_ASPECT,
                }
                models_cache[canonical_model_name] = model_cache
                _save_denoise_cache(cache)
                max_full_pixels = model_cache.get("max_full_pixels")
                print(f"   [AI] Calibration saved for {canonical_model_name}: ~{model_cache['max_full_mp']} MP ({w}x{h})")
        except Exception as e:
            print(f"   [AI] Calibration failed: {e}")
    elif denoise_mode == "auto" and device == "cuda" and max_full_pixels is None and not calibrate:
        print("   [AI] No calibration limit found; using tiled inference. Use --calibrate to measure and cache full-frame limits.")

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
        overlap_fit=overlap_fit,
        max_full_pixels=max_full_pixels,
        input_multiple=tile_multiple,
        tile_candidates=tile_candidates,
        model_name=canonical_model_name,
        allow_full_without_limit=False,
        safety_fallback=safety_fallback,
    )

    if denoise_mode == "auto" and used_full and pixels:
        if max_full_pixels is None or pixels > max_full_pixels:
            model_cache["max_full_pixels"] = int(pixels)
            models_cache[canonical_model_name] = model_cache
            _save_denoise_cache(cache)
    return _write_ai_output(image_path, denoised, out_format=out_format, quality=quality, io_info=io_info, np=np)

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

def _select_inference_model(cli_model=None):
    if cli_model:
        canonical = _resolve_inference_model_name(cli_model)
        if canonical:
            return canonical
        print(f"❌ Unknown inference model: {cli_model}")

    model_names = sorted(INFERENCE_MODELS.keys())
    if not model_names:
        print("❌ No inference models are configured.")
        return None

    print("\nAvailable inference models:")
    for i, name in enumerate(model_names, 1):
        print(f"  {i}. {name}")

    choice = input("Select model number (Enter to cancel): ").strip()
    if not choice:
        print("Inference selection cancelled.")
        return None
    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(model_names):
            return model_names[idx]

    print("Invalid selection.")
    return None

def _apply_lut_inplace(image_path, lut_path, out_format=None, quality=92):
    np, _, _, dep_err = _import_denoise_deps()
    if np is None:
        print(f"   [LUT] LUT skipped (missing dependencies): {dep_err}")
        return False

    try:
        lut = _load_cube_lut(lut_path, np=np)
    except Exception as e:
        print(f"   [LUT] Failed to load LUT: {e}")
        return False

    img, io_info = _read_image_for_ai(image_path, np=np)
    if img is None:
        return False

    try:
        out = _apply_lut_np(img, lut, np=np)
    except Exception as e:
        print(f"   [LUT] LUT apply failed: {e}")
        return False

    effective_format = out_format
    if not effective_format:
        ext = Path(image_path).suffix.lower()
        effective_format = "jpg" if ext in {".jpg", ".jpeg"} else "tif"
    return _write_ai_output(
        image_path,
        out,
        out_format=effective_format,
        quality=quality,
        io_info=io_info,
        np=np,
    )

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

def _ensure_unique_path(path):
    p = Path(path)
    if not p.exists():
        return p
    for i in range(1, 1000):
        candidate = p.with_name(f"{p.stem}_{i}{p.suffix}")
        if not candidate.exists():
            return candidate
    return p

def _stage_path(image_path, stage_tag):
    p = Path(image_path)
    tag = _sanitize_tag(stage_tag)
    staged = p.with_name(f"{p.stem}_{tag}{p.suffix}")
    return str(_ensure_unique_path(staged))

def _rename_with_stage(image_path, stage_tag):
    new_path = _stage_path(image_path, stage_tag)
    try:
        os.replace(image_path, new_path)
        return new_path
    except Exception:
        return image_path

def _copy_to_stage(image_path, stage_tag):
    new_path = _stage_path(image_path, stage_tag)
    try:
        shutil.copy2(image_path, new_path)
        return new_path
    except Exception:
        return None

def _prepare_nonraw_image(file_path, output_dir, out_format="jpg", quality=92):
    abs_output = os.path.abspath(output_dir)
    os.makedirs(abs_output, exist_ok=True)
    src = Path(file_path)
    out_ext = ".jpg" if out_format == "jpg" else ".tif"
    dest = Path(abs_output) / src.with_suffix(out_ext).name

    try:
        same_file = src.resolve() == dest.resolve()
    except Exception:
        same_file = False
    if same_file:
        dest = _ensure_unique_path(dest)

    if out_format == "jpg" and src.suffix.lower() in {".jpg", ".jpeg"}:
        try:
            shutil.copy2(src, dest)
            return str(dest), True
        except Exception as e:
            print(f"   [INPUT] Failed to copy image: {e}")
            return str(dest), False
    if out_format in {"tif", "tiff"} and src.suffix.lower() in {".tif", ".tiff"}:
        try:
            shutil.copy2(src, dest)
            return str(dest), True
        except Exception as e:
            print(f"   [INPUT] Failed to copy image: {e}")
            return str(dest), False

    Image, err = _import_pil_only()
    if Image is None:
        print(f"   [INPUT] Pillow required for non-RAW conversion: {err}")
        return str(dest), False

    try:
        with Image.open(src) as im:
            im = im.convert("RGB")
            if out_format == "jpg":
                im.save(dest, quality=quality)
            else:
                im.save(
                    dest,
                    compression=TIF_COMPRESSION,
                    predictor=TIF_PREDICTOR,
                    compress_level=TIF_LEVEL,
                )
        return str(dest), True
    except Exception as e:
        print(f"   [INPUT] Failed to convert image: {e}")
        return str(dest), False

class RawConverter:
    def __init__(self, executable_path=None):
        self.rt_path = executable_path or self._find_rt_binary()
        if not self.rt_path:
            raise FileNotFoundError("Could not find rawtherapee-cli. Please check your installation.")
        self.extensions = set(RAW_EXTENSIONS)

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

    def process_file(self, file_path, output_dir, profile=None, quality=92, out_format="jpg", rt_bit_depth="auto"):
        abs_input = os.path.abspath(file_path)
        abs_output = os.path.abspath(output_dir)
        os.makedirs(abs_output, exist_ok=True)

        cmd = [self.rt_path, "-o", abs_output, "-Y"]
        if out_format == "jpg":
            cmd.append(f"-j{quality}")
        elif out_format in {"tif", "tiff"}:
            cmd.append("-t")
            # TIFF has no common 12-bit integer export mode; use 16-bit as nearest for 12/14-bit RAW.
            bit_depth = "16" if rt_bit_depth == "auto" else str(rt_bit_depth)
            cmd.append(f"-b{bit_depth}")
        else:
            raise ValueError(f"Unsupported output format: {out_format}")
        if profile:
            cmd.extend(["-p", os.path.abspath(profile)])
        else:
            cmd.append("-d")
        
        cmd.extend(["-c", abs_input])
        return subprocess.run(cmd, capture_output=True, text=True), cmd

def select_profile(profile_dir=PP3_DIR, default_profile=None):
    """Prompt user to choose a .pp3 profile from profile_dir."""
    profile_dir = Path(profile_dir)
    if not profile_dir.exists():
        print(f"⚠️  PP3 folder not found: {profile_dir}")
        return str(default_profile) if default_profile and Path(default_profile).exists() else None

    pp3_files = sorted(profile_dir.glob("*.pp3"), key=lambda p: p.name.lower())
    if not pp3_files:
        print(f"⚠️  No .pp3 files found in: {profile_dir}")
        return str(default_profile) if default_profile and Path(default_profile).exists() else None

    default_path = Path(default_profile) if default_profile else None
    default_exists = bool(default_path and default_path.exists())
    default_label = default_path.name if default_exists else "RawTherapee defaults"

    print("\n--- Available PP3 Profiles ---")
    print(f"Folder: {profile_dir}")
    print(f"0: [Use default: {default_label}]")
    sidecar_choice = len(pp3_files) + 1
    print(f"{sidecar_choice}: [Use RAW sidecar (*.ext.pp3), fallback default]")
    for i, p in enumerate(pp3_files, 1):
        print(f"{i}: {p.name}")

    while True:
        try:
            choice = int(input("\nSelect a profile number: "))
            if choice == 0:
                return str(default_path) if default_exists else None
            if choice == sidecar_choice:
                return PP3_MODE_SIDECAR
            if 1 <= choice <= len(pp3_files):
                return str(pp3_files[choice - 1])
        except ValueError:
            pass
        print("Invalid choice. Try again.")

def main():
    parser = argparse.ArgumentParser(description="Recursive RAW processor with Profile Selection")
    parser.add_argument("paths", nargs="*", default=["."], help="Files/folders to process")
    parser.add_argument("--format", "-m", dest="out_format", default="tif", choices=["jpg", "tif", "tiff"], help="Output format")
    parser.add_argument("--rt-bit-depth", default="auto", choices=["auto", "8", "16", "16f", "32"], help="RawTherapee export bit depth (TIFF); auto uses 16-bit")
    parser.add_argument("-q", "--quality", type=int, default=92, help="JPEG quality")
    parser.add_argument("-o", "--output", default=None, help="Output folder name (defaults to format)")
    parser.add_argument("-d", "--denoise", action="store_true", help=f"Run AI inference after conversion using default model ({DEFAULT_INFERENCE_MODEL})")
    parser.add_argument("-i", "--inference", nargs="?", const="__PROMPT__", metavar="MODEL", default=None, help="Run AI inference with a specific model (or prompt if omitted)")
    parser.add_argument("--tile-size", type=int, default=None, help="Override AI tile size (auto-rounded to model multiple: NAFNet=16, Restormer=8)")
    parser.add_argument("--overlap", type=int, default=None, help="Override AI tile overlap")
    parser.add_argument("--overlap-fit", dest="overlap_fit", action="store_true", default=True, help="Keep tile size fixed and auto-fit X/Y overlap so all tiles are full-size (default: enabled)")
    parser.add_argument("--no-overlap-fit", dest="overlap_fit", action="store_false", help="Disable overlap-fit and use fixed nominal tile step")
    fit_group = parser.add_mutually_exclusive_group()
    fit_group.add_argument("-f", "--fit", action="store_true", help="Fit image dimensions to exact tile grid (uniform scale + center crop, no aspect distortion)")
    fit_group.add_argument("-tf", "--tile-fit", action="store_true", help="Fit tile size to image dimensions (keeps image size)")
    parser.add_argument("--calibrate", action="store_true", help="Run CUDA calibration for AI full-frame limits and save denoise_cache.json")
    parser.add_argument("--calibrate-all", action="store_true", help="Force calibration of all supported models and refresh denoise_cache.json")
    parser.add_argument("--ai-safety-fallback", action="store_true", help="Enable automatic safe retry chain when AI output is flagged suspicious")
    parser.add_argument("--dualdn-python", default=None, help="Python executable for DualDn external inference (default: current Python)")
    parser.add_argument("--dualdn-script", default=None, help="Path to DualDn inference script (if auto-detect fails)")
    parser.add_argument("--dualdn-cmd", default=None, help="Optional DualDn command template with placeholders: {python} {script} {weights} {input} {output_dir}")
    parser.add_argument("--lut", "-l", nargs="?", const="__PROMPT__", help="Prompt for LUT selection or pass a .cube path")
    parser.add_argument("--no-lut", action="store_true", help="Skip LUT application.")
    parser.add_argument("--pp3", action="store_true", help="Prompt to choose a .pp3 profile from pp3/ (includes sidecar mode; default RAW profile is pp3/auto_film.pp3 if present)")
    parser.add_argument("-k", "--keep", action="store_true", help="Keep every intermediate stage with a unique stage suffix")
    parser.add_argument("--skip-rt", action="store_true", help="Skip RawTherapee stage (RAW files will be skipped).")
    
    args = parser.parse_args()
    if args.out_format == "jpg" and args.rt_bit_depth != "auto":
        print(f"ℹ️  --rt-bit-depth {args.rt_bit_depth} ignored for JPG output (always 8-bit).")
    if args.calibrate and args.calibrate_all:
        print("ℹ️  Both --calibrate and --calibrate-all provided. Using --calibrate-all behavior.")
    if args.denoise and args.inference:
        print(f"ℹ️  Both -d and -i provided. Using --inference {args.inference}.")
    selected_model = None
    if args.inference is not None:
        cli_model = None if args.inference == "__PROMPT__" else args.inference
        selected_model = _select_inference_model(cli_model)
        if not selected_model:
            return
    elif args.denoise:
        selected_model = DEFAULT_INFERENCE_MODEL
    selected_model_cfg = INFERENCE_MODELS.get(selected_model, {}) if selected_model else {}
    selected_loader = selected_model_cfg.get("loader") if selected_model_cfg else None
    is_dualdn_selected = selected_loader == "dualdn_external"
    if is_dualdn_selected and (args.calibrate or args.calibrate_all):
        print("ℹ️  --calibrate/--calibrate-all are ignored for DualDn external models.")

    # Calibration pre-pass:
    # - --calibrate-all: force recalibrate every supported model
    # - --calibrate with no selected model: calibrate every supported model missing cache
    if (args.calibrate_all or (args.calibrate and selected_model is None)) and not is_dualdn_selected:
        targets = _get_calibratable_model_names()
        if not targets:
            print("   [AI] No calibratable models configured.")
        else:
            force = bool(args.calibrate_all)
            mode = "force-all" if force else "missing-only"
            print(f"   [AI] Starting calibration pass ({mode}) for {len(targets)} model(s)...")
            ok_count = 0
            for model_name in targets:
                print(f"   [AI] Calibrating model: {model_name}")
                if _calibrate_model_cache_entry(model_name, force=force):
                    ok_count += 1
            print(f"   [AI] Calibration pass complete: {ok_count}/{len(targets)} model(s) ready.")

    # Gather targets (expand wildcards on Windows)
    input_paths = set()
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
            for ext in SUPPORTED_INPUT_EXTENSIONS:
                input_paths.update(path_obj.rglob(f"*{ext}"))
                input_paths.update(path_obj.rglob(f"*{ext.upper()}"))
        elif path_obj.suffix.lower() in SUPPORTED_INPUT_EXTENSIONS and path_obj.exists():
            input_paths.add(path_obj)
        elif path_obj.suffix.lower() in SUPPORTED_INPUT_EXTENSIONS and not path_obj.exists():
            print(f"⚠️  Skipping missing file: {path_obj}")

    if stray_format_tokens:
        print(f"❌ Unrecognized argument(s): {', '.join(stray_format_tokens)}")
        print("   Use -m/--format, e.g. `photo.py *.arw -m tif`")
        return

    if not input_paths:
        print("No supported input files found.")
        return

    raw_paths = sorted(p for p in input_paths if p.suffix.lower() in RAW_EXTENSIONS)
    nonraw_paths = sorted(p for p in input_paths if p.suffix.lower() in RASTER_EXTENSIONS)
    processable_raw = [p for p in raw_paths if not args.skip_rt]
    skipped_raw = [p for p in raw_paths if args.skip_rt]

    converter = None
    selected_pp3 = None
    default_pp3 = str(DEFAULT_PP3_PROFILE) if DEFAULT_PP3_PROFILE.exists() else None
    if processable_raw:
        try:
            converter = RawConverter()
            print(f"⚙️  Using: {converter.rt_path}")
        except Exception as e:
            print(f"❌ {e}")
            return
        if args.pp3:
            selected_pp3 = select_profile(profile_dir=PP3_DIR, default_profile=default_pp3)
        else:
            selected_pp3 = default_pp3
        if selected_pp3 == PP3_MODE_SIDECAR:
            fallback_label = Path(default_pp3).name if default_pp3 else "RawTherapee defaults"
            print(f"🎨 Using PP3 Mode: RAW sidecar (*.ext.pp3), fallback={fallback_label}")
        elif selected_pp3:
            print(f"🎨 Using PP3 Profile: {Path(selected_pp3).name}")
        else:
            if args.pp3:
                print("💡 No PP3 profile selected. Using RawTherapee defaults.")
            else:
                print("💡 Default PP3 not found. Using RawTherapee defaults.")
    else:
        if args.skip_rt:
            print("⚙️  RawTherapee stage bypassed via --skip-rt.")
        else:
            print("⚙️  No RAW files detected; RawTherapee not needed.")

    if skipped_raw:
        print(f"⚠️  RAW skipped due to --skip-rt: {len(skipped_raw)} file(s)")

    lut_path = None
    if not args.no_lut and args.lut is not None:
        lut_files = _find_lut_files()
        lut_arg = None if args.lut == "__PROMPT__" else args.lut
        lut_path = _select_lut(lut_files, cli_lut=lut_arg)
    if lut_path:
        print(f"🎨 LUT Selected: {os.path.basename(lut_path)}")

    process_list = sorted(nonraw_paths + processable_raw)
    if not process_list:
        print("No files left to process.")
        return

    print(f"📸 Files to process: {len(process_list)}")

    for photo in process_list:
        print(f"⏳ Processing {photo.name}...", end=" ", flush=True)
        is_raw = photo.suffix.lower() in RAW_EXTENSIONS
        if is_dualdn_selected and not is_raw:
            print("❌ FAILED.")
            print("   [DualDn] This model only supports RAW input files.")
            continue
        if is_raw:
            if is_dualdn_selected:
                print("✅ Done.")
                print(f"   [DualDn] Running {selected_model} on RAW input...")
                dualdn_out = _run_dualdn_external_raw(
                    str(photo),
                    model_name=selected_model,
                    dualdn_python=args.dualdn_python,
                    dualdn_script=args.dualdn_script,
                    dualdn_cmd=args.dualdn_cmd,
                )
                if not dualdn_out:
                    print(f"   [DualDn] ❌ {selected_model} inference failed.")
                    continue
                print(f"   [DualDn] ✅ Output: {os.path.basename(dualdn_out)}")
                out_file, ok = _prepare_nonraw_image(
                    dualdn_out,
                    output_dir,
                    out_format=args.out_format,
                    quality=args.quality,
                )
                if not ok:
                    print("   [DualDn] ❌ Failed to convert DualDn output.")
                    continue
                if args.keep:
                    out_file = _rename_with_stage(out_file, f"infer_{selected_model.lower()}")
            else:
                profile_for_file = selected_pp3
                if selected_pp3 == PP3_MODE_SIDECAR:
                    sidecar_pp3 = Path(str(photo) + ".pp3")
                    if sidecar_pp3.exists():
                        profile_for_file = str(sidecar_pp3)
                        print(f"   [RT] PP3: sidecar {sidecar_pp3.name}")
                    else:
                        profile_for_file = default_pp3
                        if profile_for_file:
                            print(f"   [RT] PP3: sidecar missing, fallback {Path(profile_for_file).name}")
                        else:
                            print("   [RT] PP3: sidecar missing, fallback RawTherapee defaults")
                try:
                    res, cmd = converter.process_file(
                        photo,
                        output_dir,
                        profile_for_file,
                        args.quality,
                        args.out_format,
                        args.rt_bit_depth,
                    )
                except Exception as e:
                    print(f"❌ FAILED. {e}")
                    continue
                if res.returncode != 0:
                    print("❌ FAILED.")
                    print(f"   [RT] Command: {' '.join(cmd)}")
                    if res.stdout:
                        print("   [RT] STDOUT:")
                        print(res.stdout.strip())
                    if res.stderr:
                        print("   [RT] STDERR:")
                        print(res.stderr.strip())
                    continue
                print("✅ Done.")
                out_ext = ".jpg" if args.out_format == "jpg" else ".tif"
                out_file = os.path.join(output_dir, photo.with_suffix(out_ext).name)
                if args.keep:
                    out_file = _rename_with_stage(out_file, "rt")
        else:
            out_file, ok = _prepare_nonraw_image(photo, output_dir, out_format=args.out_format, quality=args.quality)
            if not ok:
                print("❌ FAILED.")
                continue
            print("✅ Done.")
        if lut_path:
            print(f"   [LUT] Applying {os.path.basename(lut_path)}...")
            if args.keep:
                lut_tag = f"lut_{Path(lut_path).stem}"
                lut_file = _copy_to_stage(out_file, lut_tag)
                if lut_file:
                    l_ok = _apply_lut_inplace(
                        lut_file,
                        lut_path,
                        out_format=args.out_format,
                        quality=args.quality,
                    )
                    if l_ok:
                        out_file = lut_file
                        print(f"   [LUT] ✅ Applied. Saved as {os.path.basename(out_file)}")
                    else:
                        print("   [LUT] ❌ Failed.")
                else:
                    print("   [LUT] ❌ Failed to create LUT stage file.")
            else:
                l_ok = _apply_lut_inplace(
                    out_file,
                    lut_path,
                    out_format=args.out_format,
                    quality=args.quality,
                )
                if l_ok:
                    out_file = _append_lut_to_filename(out_file, lut_path)
                    print(f"   [LUT] ✅ Applied. Renamed to {os.path.basename(out_file)}")
                else:
                    print("   [LUT] ❌ Failed.")

        if selected_model and not is_dualdn_selected:
            print(f"   [AI] Running {selected_model} on {os.path.basename(out_file)}...")
            if args.keep:
                stage_tag = "denoise" if args.denoise and not args.inference else f"infer_{selected_model.lower()}"
                denoise_file = _copy_to_stage(out_file, stage_tag)
                if denoise_file:
                    ok = _denoise_image_file(
                        denoise_file,
                        out_format=args.out_format,
                        quality=args.quality,
                        tile_size=args.tile_size,
                        overlap=args.overlap,
                        calibrate=args.calibrate,
                        fit=args.fit,
                        tile_fit=args.tile_fit,
                        overlap_fit=args.overlap_fit,
                        safety_fallback=args.ai_safety_fallback,
                        model_name=selected_model,
                    )
                    if ok:
                        out_file = denoise_file
                else:
                    ok = False
            else:
                ok = _denoise_image_file(
                    out_file,
                    out_format=args.out_format,
                    quality=args.quality,
                    tile_size=args.tile_size,
                    overlap=args.overlap,
                    calibrate=args.calibrate,
                    fit=args.fit,
                    tile_fit=args.tile_fit,
                    overlap_fit=args.overlap_fit,
                    safety_fallback=args.ai_safety_fallback,
                    model_name=selected_model,
                )
            if ok:
                print(f"   [AI] ✅ {selected_model} inference complete.")
            else:
                print(f"   [AI] ❌ {selected_model} inference failed.")
        elif selected_model and is_dualdn_selected:
            print(f"   [DualDn] ✅ {selected_model} inference complete (RAW pre-processing stage).")
        elif args.out_format in {"tif", "tiff"}:
            print(f"   [TIFF] Compressing {os.path.basename(out_file)}...")
            if args.keep:
                comp_file = _copy_to_stage(out_file, "tifcomp")
                if comp_file:
                    ok = _compress_tif_inplace(comp_file)
                    if ok:
                        out_file = comp_file
                else:
                    ok = False
            else:
                ok = _compress_tif_inplace(out_file)
            if ok:
                print("   [TIFF] ✅ Compression complete.")
            else:
                print("   [TIFF] ❌ Compression failed.")

    print("\nBatch Complete.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled by user (Ctrl+C). Exiting.")
        sys.exit(130)
