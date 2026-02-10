#!/usr/bin/env python3
import os
import sys
import glob
import argparse
import numpy as np
import rawpy
import colour
import torch
import torch.nn.functional as F
from PIL import Image
from pillow_lut import load_cube_file
import json
import inspect

# --- CONFIGURATION ---
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
LUT_DIR = os.path.join(SCRIPT_DIR, 'LUT')
ALT_LUT_DIR = os.path.join(SCRIPT_DIR, 'lut')

# Model Paths
MODEL_DIR = r"F:\AI\NAFNet"
MODEL_FILENAME = "NAFNet-SIDD-width64.pth"
DENOISE_CACHE = os.path.join(SCRIPT_DIR, "denoise_cache.json")

# --- ARCHITECTURE IMPORT ---
try:
    from nafnet_arch import NAFNet
    HAS_NAFNET_ARCH = True
except ImportError:
    HAS_NAFNET_ARCH = False
    print("Error: 'nafnet_arch.py' must be in the same directory as this script.")

# --- SEAMLESS TILING LOGIC (OVERLAP + BLEND) ---

def tile_process_overlap_blend(img_tensor, model, tile_size=512, overlap=64):
    """
    Processes the image in overlapping tiles and blends them to avoid seams.
    """
    b, c, h, w = img_tensor.shape
    output = torch.zeros_like(img_tensor)
    weight = torch.zeros_like(img_tensor)

    # Reflect-pad once to avoid boundary artifacts
    pad = overlap
    padded = F.pad(img_tensor, (pad, pad, pad, pad), mode='reflect')

    # Precompute blending weights for a tile
    tile_h = tile_size
    tile_w = tile_size
    wy = torch.linspace(0, 1, steps=tile_h, device=img_tensor.device)
    wx = torch.linspace(0, 1, steps=tile_w, device=img_tensor.device)
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

            # Extract tile with padding, then crop to current size
            tile = padded[:, :, y:y+curr_h+2*pad, x:x+curr_w+2*pad]
            with torch.no_grad():
                processed = model(tile)

            # Remove padding
            processed = processed[:, :, pad:pad+curr_h, pad:pad+curr_w]

            # Blend
            w_curr = w2d[:, :, :curr_h, :curr_w]
            output[:, :, y:y_end, x:x_end] += processed * w_curr
            weight[:, :, y:y_end, x:x_end] += w_curr

    return output / torch.clamp(weight, min=1e-6)

# --- CORE FUNCTIONS ---

def get_denoise_model(device):
    """
    Loads NAFNet SIDD weights with the correct block-parameters.
    """
    if not HAS_NAFNET_ARCH:
        return None
    model_path = os.path.join(MODEL_DIR, MODEL_FILENAME)

    if not os.path.exists(model_path):
        print(f"   [AI] Model not found at: {model_path}")
        return None

    # Architecture configuration for SIDD-width64
    model = NAFNet(img_channel=3, width=64, middle_blk_num=12,
                   enc_blk_nums=[2, 2, 4, 8], dec_blk_nums=[2, 2, 2, 2])

    try:
        checkpoint = torch.load(model_path, map_location=device)
        state_dict = checkpoint['params'] if 'params' in checkpoint else checkpoint
        model.load_state_dict(state_dict, strict=True)
        model.to(device).eval()
        return model
    except Exception as e:
        print(f"   [AI] Error loading model: {e}")
        return None

def run_denoise(img_srgb_np, mode="auto", tile_size=512, overlap=64, use_amp=True, max_full_pixels=None):
    """
    Prepares the image for the AI and runs denoise.
    """
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    model = get_denoise_model(device)

    if model:
        print(f"   [AI] Running Seamless Denoise on {device.upper()}...")
        # (H, W, C) -> (1, C, H, W)
        img_tensor = torch.from_numpy(np.transpose(img_srgb_np, (2, 0, 1))).float().unsqueeze(0).to(device)
        pixels = img_tensor.shape[-1] * img_tensor.shape[-2]
        used_full = False

        # Determine if we should attempt full-frame denoise
        has_cache = max_full_pixels is not None
        try_full = (mode == "full") or (mode == "auto" and device == "cuda" and has_cache and pixels <= max_full_pixels)

        if try_full and device == "cuda":
            try:
                torch.cuda.reset_peak_memory_stats()
                with torch.no_grad():
                    if use_amp:
                        with torch.amp.autocast("cuda"):
                            restored = model(img_tensor)
                    else:
                        restored = model(img_tensor)
                used_full = True
            except RuntimeError as e:
                if "out of memory" in str(e).lower():
                    peak = torch.cuda.max_memory_allocated() / (1024 ** 2)
                    reserved = torch.cuda.max_memory_reserved() / (1024 ** 2)
                    print(f"   [AI] CUDA OOM. Peak alloc: {peak:.1f} MB, reserved: {reserved:.1f} MB.")
                    print("   [AI] Falling back to overlap-blended tiling.")
                    torch.cuda.empty_cache()
                    restored = tile_process_overlap_blend(img_tensor, model, tile_size=tile_size, overlap=overlap)
                else:
                    raise
        else:
            # Process with tiles
            restored = tile_process_overlap_blend(img_tensor, model, tile_size=tile_size, overlap=overlap)

        # Convert back to Numpy
        img_out = restored.clamp(0, 1).cpu().detach().permute(0, 2, 3, 1).squeeze(0).numpy()
        return img_out, used_full, pixels

    return img_srgb_np, False, 0

# --- DENOISE CALIBRATION CACHE ---

def load_denoise_cache():
    if not os.path.exists(DENOISE_CACHE):
        return None
    try:
        with open(DENOISE_CACHE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def save_denoise_cache(cache):
    try:
        with open(DENOISE_CACHE, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2)
    except Exception as e:
        print(f"   [AI] Warning: failed to write denoise cache: {e}")

def aspect_to_ratio(text):
    parts = text.split(":")
    if len(parts) != 2:
        raise ValueError("Aspect must be like 3:2")
    w = float(parts[0].strip())
    h = float(parts[1].strip())
    if w <= 0 or h <= 0:
        raise ValueError("Aspect must be positive")
    return w / h

def calibrate_max_full_frame(model, device, aspect_ratio=3/2, use_amp=True, max_mp=200, verbose=False):
    """
    Binary search maximum megapixels that fit for full-frame denoise.
    """
    if device != "cuda":
        print("   [AI] Calibration requires CUDA.")
        return None

    def try_mp(mp):
        # Compute width/height for the given MP and aspect ratio
        total_pixels = int(mp * 1_000_000)
        h = int((total_pixels / aspect_ratio) ** 0.5)
        w = int(h * aspect_ratio)
        # Align to 16 pixels to satisfy model down/up-sampling
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

# --- COLOUR HELPERS (API COMPAT) ---

def xyz_to_rgb_compat(img_xyz, colourspace):
    """
    Convert XYZ to RGB with compatibility across colour-science versions.
    """
    try:
        return colour.XYZ_to_RGB(img_xyz, colourspace=colourspace)
    except TypeError:
        return colour.XYZ_to_RGB(
            img_xyz,
            colourspace.whitepoint,
            colourspace.whitepoint,
            colourspace.matrix_XYZ_to_RGB
        )

def oetf_srgb_compat(img_lin):
    """
    sRGB OETF across colour-science versions.
    """
    if hasattr(colour, "oetf_sRGB"):
        return colour.oetf_sRGB(img_lin)
    if hasattr(colour.models, "oetf_sRGB"):
        return colour.models.oetf_sRGB(img_lin)
    # Fallback to sRGB-specific module if present
    try:
        return colour.models.rgb.transfer_functions.srgb.oetf_sRGB(img_lin)
    except Exception:
        pass
    # Fallback using generic transfer function API (IEC 61966-2 / H.273 naming)
    if hasattr(colour.models.rgb.transfer_functions, "oetf"):
        return colour.models.rgb.transfer_functions.oetf(
            img_lin, function="ITU-T H.273 IEC 61966-2"
        )
    raise AttributeError("No sRGB OETF found in colour-science.")

def eotf_srgb_compat(img_srgb):
    """
    sRGB EOTF across colour-science versions.
    """
    if hasattr(colour, "eotf_sRGB"):
        return colour.eotf_sRGB(img_srgb)
    if hasattr(colour.models, "eotf_sRGB"):
        return colour.models.eotf_sRGB(img_srgb)
    # Fallback to sRGB-specific module if present
    try:
        return colour.models.rgb.transfer_functions.srgb.eotf_sRGB(img_srgb)
    except Exception:
        pass
    # Fallback using generic transfer function API (IEC 61966-2 / H.273 naming)
    if hasattr(colour.models.rgb.transfer_functions, "eotf"):
        return colour.models.rgb.transfer_functions.eotf(
            img_srgb, function="ITU-T H.273 IEC 61966-2"
        )
    raise AttributeError("No sRGB EOTF found in colour-science.")

def get_working_colourspace(transform):
    """
    Pick working RGB colourspace based on the selected transform.
    """
    # Map transforms to matching RGB colourspaces when available.
    mapping = {
        "flog": "F-Gamut",
        "flog2": "F-Gamut",
        "flog2c": "F-Gamut C",
        "ARIB STD-B67": "ITU-R BT.2020",
        "ITU-R BT.2100 HLG": "ITU-R BT.2020",
        "ITU-R BT.2100 PQ": "ITU-R BT.2020",
        "ITU-R BT.2020": "ITU-R BT.2020",
        "ITU-R BT.709": "ITU-R BT.709",
        "ITU-R BT.601": "ITU-R BT.601",
        "SMPTE 240M": "SMPTE 240M",
        "ITU-T H.273 IEC 61966-2": "sRGB",
    }

    # Default to sRGB if unknown
    cs_name = mapping.get(transform, "sRGB")
    # Try direct lookup
    if cs_name in colour.models.RGB_COLOURSPACES:
        return colour.models.RGB_COLOURSPACES[cs_name]
    # F-Log2C fallback to F-Gamut if F-Gamut C is missing
    if cs_name == "F-Gamut C" and "F-Gamut" in colour.models.RGB_COLOURSPACES:
        return colour.models.RGB_COLOURSPACES["F-Gamut"]
    # Fallback if colourspace not found in this version
    return colour.models.RGB_COLOURSPACES["sRGB"]

# --- FUJI F-LOG OETF ---

def apply_fuji_flog_oetf(img_linear):
    """
    Apply Fujifilm's official F-Log OETF to linear light RGB.
    This expects input in [0, 1] linear light (scene reflection).
    """
    # Avoid log of 0
    x = np.clip(img_linear, 0.0, 1.0)

    # Fujifilm F-Log Data Sheet Ver.1.2 (Scene Linear Reflection to F-Log)
    a = 0.555556
    b = 0.009468
    c = 0.344676
    d = 0.790453
    e = 8.735631
    f = 0.092864
    cut1 = 0.00089

    y = np.empty_like(x)
    mask = x < cut1
    # Linear toe
    y[mask] = e * x[mask] + f
    # Log segment
    y[~mask] = c * np.log10(a * x[~mask] + b) + d

    return np.clip(y, 0.0, 1.0)

# --- FUJI F-LOG2 OETF ---

def apply_fuji_flog2_oetf(img_linear):
    """
    Apply Fujifilm's official F-Log2 OETF to linear light RGB.
    This expects input in [0, 1] linear light (scene reflection).
    """
    x = np.clip(img_linear, 0.0, 1.0)

    # Fujifilm F-Log2 Data Sheet Ver.1.1 (Scene Linear Reflection to F-Log2)
    a = 5.555556
    b = 0.064829
    c = 0.245281
    d = 0.384316
    e = 8.799461
    f = 0.092864
    cut1 = 0.000889

    y = np.empty_like(x)
    mask = x < cut1
    # Linear toe
    y[mask] = e * x[mask] + f
    # Log segment
    y[~mask] = c * np.log10(a * x[~mask] + b) + d

    return np.clip(y, 0.0, 1.0)

# --- FUJI F-LOG2C OETF ---

def apply_fuji_flog2c_oetf(img_linear):
    """
    Apply Fujifilm's F-Log2C OETF to linear light RGB.
    The published conversion formula matches F-Log2C / F-Log2.
    """
    x = np.clip(img_linear, 0.0, 1.0)

    # Fujifilm F-Log2C / F-Log2 conversion formula
    a = 5.555556
    b = 0.064829
    c = 0.245281
    d = 0.384316
    e = 8.799461
    f = 0.092864
    cut1 = 0.000889

    y = np.empty_like(x)
    mask = x < cut1
    y[mask] = e * x[mask] + f
    y[~mask] = c * np.log10(a * x[~mask] + b) + d

    return np.clip(y, 0.0, 1.0)

# --- LUT SELECTION ---

def find_lut_files():
    """
    Returns a sorted list of .cube files from LUT_DIR (or ALT_LUT_DIR).
    """
    search_dirs = []
    if os.path.isdir(LUT_DIR):
        search_dirs.append(LUT_DIR)
    if os.path.isdir(ALT_LUT_DIR) and ALT_LUT_DIR not in search_dirs:
        search_dirs.append(ALT_LUT_DIR)

    lut_files = []
    for d in search_dirs:
        lut_files.extend(glob.glob(os.path.join(d, "*.cube")))

    # De-dupe by base name to avoid duplicates across LUT/lut folders
    seen = {}
    for p in lut_files:
        base = os.path.basename(p)
        if base.lower() not in seen:
            seen[base.lower()] = p
    return [seen[k] for k in sorted(seen.keys())]

def select_lut(lut_files, cli_lut=None):
    """
    Select a LUT from the list. If cli_lut is provided, try to resolve it.
    Otherwise, prompt the user.
    """
    if not lut_files:
        return None

    if cli_lut:
        cli_lut = cli_lut.strip()
        if cli_lut.lower() in {"none", "off", "skip"}:
            return None

        if cli_lut.isdigit():
            idx = int(cli_lut) - 1
            if 0 <= idx < len(lut_files):
                return lut_files[idx]
        else:
            # Match by base name (case-insensitive), with or without extension
            for lut_path in lut_files:
                base = os.path.basename(lut_path)
                stem = os.path.splitext(base)[0]
                if cli_lut.lower() in {base.lower(), stem.lower()}:
                    return lut_path

        print(f"[LUT] Warning: Could not find '{cli_lut}'. Using first LUT.")
        return lut_files[0]

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

def select_transform(cli_transform=None):
    """
    Select a color transform: none, gfx, flog, flog2, flog2c, and transfer curves.
    """
    options = [
        "none", "gfx", "flog", "flog2", "flog2c",
        "ARIB STD-B67", "Blackmagic Film Generation 5", "DaVinci Intermediate",
        "ITU-R BT.2020", "ITU-R BT.2100 HLG", "ITU-R BT.2100 PQ",
        "ITU-R BT.601", "ITU-R BT.709", "ITU-T H.273 Log",
        "ITU-T H.273 Log Sqrt", "ITU-T H.273 IEC 61966-2", "SMPTE 240M"
    ]
    if cli_transform:
        val = cli_transform.strip()
        if val in options:
            return val
        # Case-insensitive match
        for opt in options:
            if val.lower() == opt.lower():
                return opt
        print(f"[Color] Warning: Unknown transform '{cli_transform}'. Using 'none'.")
        return "none"

    print("\nAvailable Color Transforms:")
    print("  1. none")
    print("  2. gfx")
    print("  3. flog")
    print("  4. flog2")
    print("  5. flog2c")
    print("  6. ARIB STD-B67")
    print("  7. Blackmagic Film Generation 5")
    print("  8. DaVinci Intermediate")
    print("  9. ITU-R BT.2020")
    print("  10. ITU-R BT.2100 HLG")
    print("  11. ITU-R BT.2100 PQ")
    print("  12. ITU-R BT.601")
    print("  13. ITU-R BT.709")
    print("  14. ITU-T H.273 Log")
    print("  15. ITU-T H.273 Log Sqrt")
    print("  16. ITU-T H.273 IEC 61966-2")
    print("  17. SMPTE 240M")
    choice = input("Select transform number (Enter for none): ").strip()
    if not choice:
        return "none"
    if choice.isdigit():
        idx = int(choice)
        if idx == 1:
            return "none"
        if idx == 2:
            return "gfx"
        if idx == 3:
            return "flog"
        if idx == 4:
            return "flog2"
        if idx == 5:
            return "flog2c"
        if idx == 6:
            return "ARIB STD-B67"
        if idx == 7:
            return "Blackmagic Film Generation 5"
        if idx == 8:
            return "DaVinci Intermediate"
        if idx == 9:
            return "ITU-R BT.2020"
        if idx == 10:
            return "ITU-R BT.2100 HLG"
        if idx == 11:
            return "ITU-R BT.2100 PQ"
        if idx == 12:
            return "ITU-R BT.601"
        if idx == 13:
            return "ITU-R BT.709"
        if idx == 14:
            return "ITU-T H.273 Log"
        if idx == 15:
            return "ITU-T H.273 Log Sqrt"
        if idx == 16:
            return "ITU-T H.273 IEC 61966-2"
        if idx == 17:
            return "SMPTE 240M"
    print("[Color] Invalid selection. Using 'none'.")
    return "none"

def select_yes_no(prompt, default=False):
    """
    Prompt user for yes/no. Enter returns default.
    """
    suffix = "Y/n" if default else "y/N"
    choice = input(f"{prompt} ({suffix}): ").strip().lower()
    if not choice:
        return default
    return choice in {"y", "yes", "1", "true", "on"}

def select_denoise_enabled(cli_denoise=None):
    """
    Determine whether denoise is enabled.
    """
    if cli_denoise is not None:
        return cli_denoise
    return select_yes_no("Enable denoise?", default=True)

def select_auto_exposure(cli_auto_bright=None):
    """
    Determine whether auto exposure (auto-bright) is enabled.
    """
    if cli_auto_bright is not None:
        return cli_auto_bright
    return select_yes_no("Enable auto exposure (auto-bright)?", default=False)

# --- MAIN PIPELINE ---

def process_file(filepath, lut_path=None, transform="none", denoise_mode="auto", tile_size=512, overlap=64, max_full_pixels=None, auto_bright=False, denoise_enabled=True):
    filename = os.path.basename(filepath)
    print(f"\n--- Processing: {filename} ---")

    try:
        # 1. DEVELOP RAW
        # We use 8-bit sRGB because the SIDD model was trained on sRGB data.
        # This prevents the 'messed up tiles' caused by feeding linear data to the AI.
        with rawpy.imread(filepath) as raw:
            print("   [Raw] Developing Raw to linear XYZ...")
            rgb = raw.postprocess(
                use_camera_wb=True,
                no_auto_bright=not auto_bright,
                bright=1.0,
                output_bps=16,
                gamma=(1, 1),
                output_color=rawpy.ColorSpace.XYZ
            )

        # Convert to linear sRGB for processing
        img_xyz = rgb.astype(np.float32) / 65535.0
        cs_work = get_working_colourspace(transform)
        print(f"   [Color] Working gamut: {cs_work.name}")
        img_lin = xyz_to_rgb_compat(img_xyz, cs_work)
        img_lin = np.clip(img_lin, 0.0, 1.0)

        # 2. SEAMLESS AI DENOISE (model expects sRGB encoded)
        if denoise_enabled:
            img_srgb = oetf_srgb_compat(img_lin)
            img_srgb = np.clip(img_srgb, 0.0, 1.0)
            img_denoised, used_full, pixels = run_denoise(
                img_srgb,
                mode=denoise_mode,
                tile_size=tile_size,
                overlap=overlap,
                max_full_pixels=max_full_pixels
            )
            img_lin = eotf_srgb_compat(img_denoised)
            img_lin = np.clip(img_lin, 0.0, 1.0)
        else:
            used_full, pixels = False, 0

        # 3. COLOR TRANSFORMS
        img_final = img_lin
        if transform == "gfx":
            print("   [Color] Applying GFX Matrix...")
            # Simulated GFX 100 color science matrix
            fuji_matrix = np.array([
                [0.94, 0.04, 0.02],
                [0.02, 1.02, -0.04],
                [0.01, -0.02, 1.01]
            ])
            img_final = np.dot(img_final.reshape(-1, 3), fuji_matrix.T).reshape(img_final.shape)
            img_final = np.clip(img_final, 0, 1)
        elif transform == "flog":
            print("   [Color] Applying Fuji F-Log OETF...")
            img_final = apply_fuji_flog_oetf(img_final)
        elif transform == "flog2":
            print("   [Color] Applying Fuji F-Log2 OETF...")
            img_final = apply_fuji_flog2_oetf(img_final)
        elif transform == "flog2c":
            print("   [Color] Applying Fuji F-Log2C OETF...")
            img_final = apply_fuji_flog2c_oetf(img_final)
        elif transform in {
            "ARIB STD-B67", "Blackmagic Film Generation 5", "DaVinci Intermediate",
            "ITU-R BT.2020", "ITU-R BT.2100 HLG", "ITU-R BT.2100 PQ",
            "ITU-R BT.601", "ITU-R BT.709", "ITU-T H.273 Log",
            "ITU-T H.273 Log Sqrt", "ITU-T H.273 IEC 61966-2", "SMPTE 240M"
        }:
            print(f"   [Color] Applying transfer function: {transform}...")
            img_final = colour.models.rgb.transfer_functions.oetf(img_final, function=transform)

        # 4. LUT APPLICATION
        img_uint8 = (img_final * 255).astype(np.uint8)
        pil_image = Image.fromarray(img_uint8)

        if lut_path:
            print(f"   [LUT] Applying: {os.path.basename(lut_path)}")
            pil_image = pil_image.filter(load_cube_file(lut_path))

        # 5. SAVE OUTPUT
        # Outputting to TIF with Deflate compression as requested
        out_name = os.path.splitext(filename)[0] + ".tif"
        out_path = os.path.join(os.getcwd(), out_name)

        pil_image.save(out_path, compression="tiff_deflate")
        print(f"   [Success] Saved: {out_name}")
        return used_full, pixels

    except Exception as e:
        print(f"   [ERROR] Failed to process {filename}: {e}")
        return False, 0

# --- CLI ENTRY ---

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Professional Raw to TIF Pipeline")
    parser.add_argument("files", nargs='+', help="Input files or wildcards (e.g., *.arw)")
    parser.add_argument("--lut", help="LUT name or number. Use 'none' to skip.")
    parser.add_argument("--no-lut", action="store_true", help="Skip LUT application.")
    parser.add_argument("--transform", help="Color transform: none, gfx, flog.")
    parser.add_argument("--denoise", choices=["auto", "full", "tiles"], default="auto",
                        help="Denoise mode: auto (default), full (CUDA), or tiles.")
    parser.add_argument("--tile-size", type=int, default=512, help="Tile size for tiled denoise.")
    parser.add_argument("--overlap", type=int, default=64, help="Tile overlap for blended denoise.")
    parser.add_argument("-d", "--default", action="store_true", help="Use default settings and skip prompts.")
    parser.add_argument("--auto-bright", action="store_true", help="Enable RAW auto-brightness.")
    parser.add_argument("--no-auto-bright", action="store_true", help="Disable RAW auto-brightness.")
    parser.add_argument("--no-denoise", action="store_true", help="Disable denoise.")
    parser.add_argument("--calibrate-denoise", action="store_true",
                        help="Benchmark max full-frame size on CUDA and cache it.")
    parser.add_argument("--calibrate-aspect", default="3:2",
                        help="Aspect ratio for calibration (e.g., 3:2).")
    parser.add_argument("--calibrate-max-mp", type=int, default=200,
                        help="Upper bound megapixels for calibration search.")
    args = parser.parse_args()

    # Expand wildcards for Windows
    input_files = []
    for f in args.files:
        if '*' in f:
            input_files.extend(glob.glob(f))
        else:
            input_files.append(f)

    if not input_files:
        print("No files found. Check your file path or wildcard.")
    else:
        cache = load_denoise_cache() or {}
        if args.calibrate_denoise:
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
            model = get_denoise_model(device)
            if model and device == "cuda":
                try:
                    aspect = aspect_to_ratio(args.calibrate_aspect)
                    result = calibrate_max_full_frame(
                        model,
                        device,
                        aspect_ratio=aspect,
                        use_amp=True,
                        max_mp=args.calibrate_max_mp,
                        verbose=True
                    )
                    if result:
                        mp, w, h = result
                        props = torch.cuda.get_device_properties(0)
                        cache = {
                            "gpu_name": props.name,
                            "total_vram_mb": int(props.total_memory / (1024 ** 2)),
                            "max_full_pixels": int(w * h),
                            "max_full_mp": round(mp, 2),
                            "aspect": args.calibrate_aspect
                        }
                        save_denoise_cache(cache)
                        print(f"   [AI] Calibration saved: ~{cache['max_full_mp']} MP ({w}x{h})")
                except Exception as e:
                    print(f"   [AI] Calibration failed: {e}")

        max_full_pixels = cache.get("max_full_pixels")
        if max_full_pixels is None:
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
            model = get_denoise_model(device)
            if model and device == "cuda":
                try:
                    aspect = aspect_to_ratio(args.calibrate_aspect)
                    result = calibrate_max_full_frame(
                        model,
                        device,
                        aspect_ratio=aspect,
                        use_amp=True,
                        max_mp=args.calibrate_max_mp,
                        verbose=True
                    )
                    if result:
                        mp, w, h = result
                        props = torch.cuda.get_device_properties(0)
                        cache = {
                            "gpu_name": props.name,
                            "total_vram_mb": int(props.total_memory / (1024 ** 2)),
                            "max_full_pixels": int(w * h),
                            "max_full_mp": round(mp, 2),
                            "aspect": args.calibrate_aspect
                        }
                        save_denoise_cache(cache)
                        max_full_pixels = cache.get("max_full_pixels")
                        print(f"   [AI] Auto calibration saved: ~{cache['max_full_mp']} MP ({w}x{h})")
                except Exception as e:
                    print(f"   [AI] Auto calibration failed: {e}")
        if args.default:
            auto_bright = True
            denoise_enabled = True
            transform = "none"
            lut_path = None
        else:
            auto_bright = None
            if args.auto_bright and not args.no_auto_bright:
                auto_bright = True
            elif args.no_auto_bright and not args.auto_bright:
                auto_bright = False

            denoise_enabled = None
            if args.no_denoise:
                denoise_enabled = False

            auto_bright = select_auto_exposure(cli_auto_bright=auto_bright)
            denoise_enabled = select_denoise_enabled(cli_denoise=denoise_enabled)
            transform = select_transform(cli_transform=args.transform)

        lut_files = find_lut_files()
        if args.default:
            lut_path = None
        else:
            lut_path = None if args.no_lut else select_lut(lut_files, cli_lut=args.lut)

        # transform/lut already set above
        print(f"Found {len(input_files)} images. Starting pipeline...")
        updated = False
        for f in input_files:
            used_full, pixels = process_file(
                f,
                lut_path=lut_path,
                transform=transform,
                denoise_mode=args.denoise,
                tile_size=args.tile_size,
                overlap=args.overlap,
                max_full_pixels=max_full_pixels,
                auto_bright=auto_bright,
                denoise_enabled=denoise_enabled
            )
            if args.denoise == "auto" and used_full and pixels:
                if max_full_pixels is None or pixels > max_full_pixels:
                    max_full_pixels = pixels
                    cache["max_full_pixels"] = int(pixels)
                    updated = True
        if updated:
            save_denoise_cache(cache)
