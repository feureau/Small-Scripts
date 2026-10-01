import sys
import os
import io
import gc
import glob
import json
import struct
import shutil
import argparse
import base64
import tempfile
import hashlib
import sqlite3
import subprocess
import urllib.request
import urllib.error
import re
from concurrent.futures import ThreadPoolExecutor


# ==========================================
# CONFIGURATION
# ==========================================

TESSERACT_CONFIG = r'--psm 6'
LANG = 'eng'
OCR_ENGINE = 'easyocr'
LLM_API_URL = "http://127.0.0.1:11434/v1/chat/completions"
LLM_MODEL = "llava"
LLM_TIMEOUT = 120
LLM_PROMPT = (
    "Read only the subtitle text in this image. "
    "Return plain text only, no quotes, no explanation."
)

DEFAULT_CAPTION_DURATION = 4.0
MAX_CAPTION_DURATION = 10.0

BATCH_SIZE = 8
PGS_BACKEND = "fast"     # "fast" (in-process) or "ffmpeg"
CACHE_DIR = os.path.join(os.path.expanduser("~"), ".cache", "pgstosrt")
CACHE_DB = os.path.join(CACHE_DIR, "ocr.sqlite")
USE_CACHE = True


# ==========================================
# DEPENDENCY CHECKS
# ==========================================

def check_base_dependencies():
    missing = []
    try:
        from PIL import Image, ImageOps, ImageFilter  # noqa: F401
    except ImportError:
        missing.append("pillow")
    try:
        from tqdm import tqdm  # noqa: F401
    except ImportError:
        missing.append("tqdm")

    if missing:
        print("\n" + "!" * 50)
        print("ERROR: Missing required Python modules.")
        print(f"\n    pip install {' '.join(missing)}")
        print("!" * 50)
        sys.exit(1)


def check_runtime_dependencies():
    if OCR_ENGINE == "tesseract" and not HAS_PYTESSERACT:
        print("\n" + "!" * 50)
        print("ERROR: --ocr-engine tesseract requires 'pytesseract'.")
        print("\n    pip install pytesseract")
        print("!" * 50)
        sys.exit(1)
    if OCR_ENGINE == "easyocr" and not HAS_EASYOCR:
        print("   [WARN] EasyOCR not installed; will fall back to Tesseract.")
        if not HAS_PYTESSERACT:
            print("\n" + "!" * 50)
            print("ERROR: Neither EasyOCR nor pytesseract is available.")
            print("\n    pip install easyocr torch pytesseract")
            print("!" * 50)
            sys.exit(1)


def check_ffmpeg_tools():
    for tool in ("ffmpeg", "ffprobe"):
        if shutil.which(tool) is None:
            print(f"ERROR: '{tool}' not found in PATH. Please install FFmpeg.")
            sys.exit(1)


check_base_dependencies()

from PIL import Image, ImageOps, ImageFilter
from tqdm import tqdm

try:
    import pytesseract
    HAS_PYTESSERACT = True
except ImportError:
    pytesseract = None
    HAS_PYTESSERACT = False

HAS_EASYOCR = False
GPU_DEVICE = 'cpu'
try:
    import easyocr
    import torch
    HAS_EASYOCR = True
    GPU_DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'
except ImportError:
    easyocr = None
    torch = None


def print_runtime_diagnostics():
    print("\n--- Runtime Diagnostics ---")
    print(f"  OCR engine      : {OCR_ENGINE}")
    print(f"  Batch size      : {BATCH_SIZE}")
    print(f"  PGS backend     : {PGS_BACKEND}")

    if OCR_ENGINE == "easyocr":
        if not HAS_EASYOCR:
            print("  STATUS          : ! EasyOCR not installed — falling back to Tesseract")
        else:
            print(f"  PyTorch version : {torch.__version__}")
            print(f"  CUDA built-in   : {torch.version.cuda or 'NO (CPU-only PyTorch build)'}")
            if GPU_DEVICE == 'cuda':
                gpu_name = torch.cuda.get_device_name(0)
                vram_total = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
                print(f"  GPU detected    : {gpu_name}")
                print(f"  VRAM            : {vram_total:.1f} GB")
                print(f"  STATUS          : OK Using GPU")
            elif not torch.version.cuda:
                print(f"  STATUS          : X CPU-only (reinstall PyTorch with CUDA to enable GPU)")
            else:
                print(f"  STATUS          : X CUDA built-in but no GPU found")

    elif OCR_ENGINE == "tesseract":
        print(f"  STATUS          : {'OK' if HAS_PYTESSERACT else 'X pytesseract not installed'}")

    elif OCR_ENGINE in ("ollama", "lmstudio"):
        print(f"  Endpoint        : {LLM_API_URL}")
        print(f"  Model           : {LLM_MODEL}")

    if USE_CACHE:
        print(f"  OCR cache       : {CACHE_DB}")
    print("---------------------------\n")


# ==========================================
# IMAGE HELPERS
# ==========================================

def is_image_blank(img):
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    extrema = img.getextrema()
    return len(extrema) >= 4 and extrema[3][1] == 0


def autocrop_image(img, padding=20):
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    bbox = img.getbbox()
    if not bbox:
        return img
    left, upper, right, lower = bbox
    left = max(0, left - padding)
    upper = max(0, upper - padding)
    right = min(img.width, right + padding)
    lower = min(img.height, lower + padding)
    return img.crop((left, upper, right, lower))


# ==========================================
# OCR PREPROCESSING
# ==========================================

READER = None


def get_easyocr_reader():
    global READER
    if READER is None and HAS_EASYOCR:
        try:
            print("   [INFO] Initializing EasyOCR model (this may take a moment)...")
            lang_code = 'en' if LANG == 'eng' else LANG
            use_gpu = (GPU_DEVICE == 'cuda')
            READER = easyocr.Reader([lang_code], gpu=use_gpu)
            print(f"   [INFO] EasyOCR ready ({'GPU' if use_gpu else 'CPU'})")
        except Exception as e:
            print(f"   [WARN] Failed to init EasyOCR: {e}. Falling back to Tesseract.")
            return None
    return READER


def preprocess_for_tesseract(img):
    bg_black = Image.new("RGB", img.size, (0, 0, 0))
    if img.mode in ("RGBA", "LA") or ("transparency" in img.info):
        bg_black.paste(img.convert("RGB"), mask=img.split()[-1])
    else:
        bg_black.paste(img.convert("RGB"))

    MIN_HEIGHT = 64       # was 80
    w, h = bg_black.size
    if h < MIN_HEIGHT:
        scale = MIN_HEIGHT / h
        bg_black = bg_black.resize((int(w * scale), MIN_HEIGHT), Image.LANCZOS)

    return ImageOps.invert(bg_black.convert('L'))


def preprocess_for_easyocr(img):
    bg_black = Image.new("RGB", img.size, (0, 0, 0))
    if img.mode in ("RGBA", "LA") or ("transparency" in img.info):
        bg_black.paste(img.convert("RGB"), mask=img.split()[-1])
    else:
        bg_black.paste(img.convert("RGB"))

    bg_black = ImageOps.autocontrast(bg_black.convert("L")).convert("RGB")

    MIN_HEIGHT = 96       # was 160
    w, h = bg_black.size
    if h < MIN_HEIGHT:
        scale = MIN_HEIGHT / h
        bg_black = bg_black.resize((int(w * scale), MIN_HEIGHT), Image.LANCZOS)

    return bg_black.filter(ImageFilter.SHARPEN)


# ==========================================
# OCR BACKENDS (per-image, used as fallback)
# ==========================================

def ocr_with_openai_compatible(img, api_url, model, timeout):
    proc_img = preprocess_for_easyocr(img)
    buf = io.BytesIO()
    proc_img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")

    payload = {
        "model": model,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": LLM_PROMPT},
                {"type": "image_url",
                 "image_url": {"url": f"data:image/png;base64,{b64}"}}
            ]
        }],
        "temperature": 0
    }

    req = urllib.request.Request(
        api_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8", errors="replace"))
    return data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()


def list_openai_compatible_models(api_url, timeout):
    base = api_url
    suffix = "/v1/chat/completions"
    if base.endswith(suffix):
        base = base[:-len(suffix)]
    models_url = base.rstrip("/") + "/v1/models"
    req = urllib.request.Request(models_url, headers={"Content-Type": "application/json"}, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8", errors="replace"))
    return [item["id"] for item in data.get("data", []) if item.get("id")]


def _ocr_easyocr_single(reader, img):
    import numpy as np
    proc_img = preprocess_for_easyocr(img)
    img_np = np.array(proc_img)
    try:
        results = reader.readtext(img_np, detail=0, paragraph=True,
                                  text_threshold=0.4, low_text=0.3, mag_ratio=1.5)
        return " ".join(results)
    except Exception:
        return ""
    finally:
        del proc_img, img_np


def _ocr_tesseract_single(img):
    if not HAS_PYTESSERACT:
        return ""
    proc_img = preprocess_for_tesseract(img)
    try:
        return pytesseract.image_to_string(proc_img, lang=LANG, config=TESSERACT_CONFIG)
    finally:
        del proc_img


def _ocr_llm_single(img):
    try:
        return ocr_with_openai_compatible(img, LLM_API_URL, LLM_MODEL, LLM_TIMEOUT)
    except urllib.error.URLError as e:
        print(f"   [ERR] {OCR_ENGINE} request failed: {e}")
        return ""
    except Exception as e:
        print(f"   [ERR] {OCR_ENGINE} OCR failed: {e}")
        return ""


# ==========================================
# BATCHED OCR DISPATCH
# ==========================================

def _join_easyocr_result(r):
    if r is None:
        return ""
    if isinstance(r, str):
        return r
    if isinstance(r, list):
        parts = []
        for item in r:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                parts.append(str(item[1]))
        return " ".join(parts)
    return str(r)


_BATCH_EASYOCR_WARNED = False


def _dispatch_batch_easyocr(reader, images):
    global _BATCH_EASYOCR_WARNED
    import numpy as np

    procs = [np.array(preprocess_for_easyocr(im)) for im in images]

    # EasyOCR's readtext_batched stacks all images into one tensor, so they
    # must share a shape. Subtitle crops vary in width, so pad to the max
    # size in this batch (black fill, which is what the detector expects).
    max_h = max(p.shape[0] for p in procs)
    max_w = max(p.shape[1] for p in procs)
    padded = []
    for p in procs:
        h, w = p.shape[:2]
        if h == max_h and w == max_w:
            padded.append(p)
            continue
        if p.ndim == 2:
            canvas = np.zeros((max_h, max_w), dtype=p.dtype)
            canvas[:h, :w] = p
        else:
            canvas = np.zeros((max_h, max_w, p.shape[2]), dtype=p.dtype)
            canvas[:h, :w] = p
        padded.append(canvas)

    try:
        if hasattr(reader, "readtext_batched"):
            results = reader.readtext_batched(
                padded, detail=0, paragraph=True,
                text_threshold=0.4, low_text=0.3, mag_ratio=1.5,
                batch_size=len(padded),
            )
            return [_join_easyocr_result(r) for r in results]
    except Exception as e:
        if not _BATCH_EASYOCR_WARNED:
            msg = str(e).splitlines()[0][:160]
            print(f"   [WARN] batched EasyOCR failed: {msg}; using per-image")
            _BATCH_EASYOCR_WARNED = True
    finally:
        del procs, padded

    return [_ocr_easyocr_single(reader, im) for im in images]


def _tesseract_worker(png_bytes):
    from PIL import Image
    import io as _io
    import pytesseract as _pt
    img = Image.open(_io.BytesIO(png_bytes)).convert("RGBA")
    proc = preprocess_for_tesseract(img)
    return _pt.image_to_string(proc, lang=LANG, config=TESSERACT_CONFIG)


def _dispatch_batch_tesseract(images):
    if not HAS_PYTESSERACT:
        return [""] * len(images)
    png_list = []
    for im in images:
        buf = io.BytesIO()
        im.save(buf, format="PNG")
        png_list.append(buf.getvalue())
    workers = min(os.cpu_count() or 4, max(1, len(images)))
    with ThreadPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(_tesseract_worker, png_list))


def _dispatch_batch_llm(images):
    workers = min(4, max(1, len(images)))
    with ThreadPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(_ocr_llm_single, images))


def _dispatch_batch_ocr(images):
    """Raw backend dispatch, no cache."""
    if not images:
        return []
    if OCR_ENGINE == "easyocr":
        reader = get_easyocr_reader()
        if reader:
            return _dispatch_batch_easyocr(reader, images)
        return _dispatch_batch_tesseract(images)
    if OCR_ENGINE == "tesseract":
        return _dispatch_batch_tesseract(images)
    if OCR_ENGINE in ("ollama", "lmstudio"):
        return _dispatch_batch_llm(images)
    return [""] * len(images)


# ==========================================
# OCR CACHE
# ==========================================

_CACHE_CON = None


def _cache_conn():
    global _CACHE_CON
    if _CACHE_CON is None:
        os.makedirs(CACHE_DIR, exist_ok=True)
        _CACHE_CON = sqlite3.connect(CACHE_DB)
        _CACHE_CON.execute(
            "CREATE TABLE IF NOT EXISTS ocr (hash TEXT PRIMARY KEY, text TEXT)"
        )
        _CACHE_CON.commit()
    return _CACHE_CON


def _cache_key(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return f"{OCR_ENGINE}:{LANG}:{hashlib.sha1(buf.getvalue()).hexdigest()}"


def batch_ocr(images):
    """Batched OCR with persistent content-hash cache."""
    if not images:
        return []

    if not USE_CACHE:
        return _dispatch_batch_ocr(images)

    try:
        con = _cache_conn()
    except Exception:
        return _dispatch_batch_ocr(images)

    keys = [_cache_key(im) for im in images]
    results = [None] * len(images)
    to_ocr_idx = []
    to_ocr_imgs = []

    for i, k in enumerate(keys):
        row = con.execute("SELECT text FROM ocr WHERE hash=?", (k,)).fetchone()
        if row is not None:
            results[i] = row[0]
        else:
            to_ocr_idx.append(i)
            to_ocr_imgs.append(images[i])

    if to_ocr_imgs:
        new_texts = _dispatch_batch_ocr(to_ocr_imgs)
        for i, text in zip(to_ocr_idx, new_texts):
            results[i] = text
            try:
                con.execute("INSERT OR REPLACE INTO ocr VALUES (?, ?)", (keys[i], text))
            except Exception:
                pass
        try:
            con.commit()
        except Exception:
            pass

    return results


# ==========================================
# TEXT CLEANUP
# ==========================================

def clean_ocr_text(text):
    text = text.strip()
    if not text:
        return ""

    # Reject noise like "[Pr]" or single-char garbage from graphics/watermarks.
    stripped = text.strip("[](){}<>\"'` \t")
    if len(stripped) <= 3 and not any(c.islower() for c in stripped):
        return ""

    text = text.replace('|', 'I').replace('\n', ' ')
    text = re.sub(r'\s+', ' ', text)

    replacements = {
        "AIl": "All", "aIl": "all", "IlI": "I'll", "III": "I'll",
        "They'Il": "They'll", "they'Il": "they'll",
        "you'Il": "you'll", "we'Il": "we'll", "I'Il": "I'll",
        "Iegal": "legal", "Iaunch": "launch", "out off": "cut off", "uS": "us",
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)

    text = re.sub(
        r'\bI(?=(?:wish|want|need|can|can\'t|could|couldn\'t|just|don\'t|didn\'t|'
        r'doubt|know|knew|thought|hope|had|have|am|was|will|would)\b)',
        'I ', text
    )
    text = re.sub(r'\b([Tt]hey|[Ww]e|[Yy]ou|[Ss]he|[Hh]e)' + r"'Il\b", r"\1'll", text)
    text = re.sub(r'(?<![-\w.])(?:0|9)(?![-\w.%])', '', text)
    text = re.sub(r'\s*(?:[_"“”\'`]+|\d+|[0O])+\s*$', '', text)
    text = re.sub(r'([A-Za-z])_\b', r'\1', text)
    text = re.sub(r'\s+([,.;:!?])', r'\1', text)
    text = re.sub(r'([.!?])\s*[._]+$', r'\1', text)
    text = re.sub(r'_\s*$', '.', text)
    text = re.sub(r'\b([A-Za-z]{2,})l([.!?]?)$',
                  lambda m: m.group(1) + ('!' if not m.group(2) else m.group(2)),
                  text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def format_time(seconds):
    ms = int((seconds % 1) * 1000)
    s = int(seconds)
    m = s // 60
    h = m // 60
    s = s % 60
    m = m % 60
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


# ==========================================
# MKV / FFMPEG HELPERS
# ==========================================

def get_video_dimensions(mkv_path):
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "json", mkv_path
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        data = json.loads(result.stdout)
        stream = (data.get("streams") or [{}])[0]
        return int(stream.get("width") or 1920), int(stream.get("height") or 1080)
    except Exception:
        return 1920, 1080


def get_subtitle_tracks(mkv_path):
    video_width, video_height = get_video_dimensions(mkv_path)
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "s",
        "-show_entries", "stream=index,codec_name,width,height:stream_tags=language",
        "-of", "json", mkv_path
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        data = json.loads(result.stdout)
    except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError):
        print("Error: Could not probe file. Is ffmpeg installed and in PATH?")
        return []

    tracks = []
    for sub_idx, stream in enumerate(data.get('streams', [])):
        codec = stream.get('codec_name')
        if codec in ("hdmv_pgs_subtitle", "dvd_subtitle"):
            tracks.append({
                'index': stream['index'],
                'sub_idx': sub_idx,
                'codec': codec,
                'lang': stream.get('tags', {}).get('language', 'und'),
                'width': stream.get('width') or video_width,
                'height': stream.get('height') or video_height,
            })
    return tracks


def get_mkv_packet_entries(mkv_path, track_selector):
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", track_selector,
        "-show_entries", "packet=pts_time,duration_time",
        "-of", "json", mkv_path
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        data = json.loads(result.stdout)
        entries = []
        for p in data.get('packets', []):
            try:
                pts = float(p.get('pts_time', 0))
                dur_raw = p.get('duration_time')
                dur = float(dur_raw) if dur_raw is not None else None
                if pts >= 0:
                    entries.append({'start': pts,
                                    'duration': dur if dur and dur > 0 else None})
            except (ValueError, TypeError):
                continue
        return entries
    except Exception as e:
        print(f"   [WARN] Could not extract packet timing list: {e}")
        return []


def render_image_subtitle_frame(mkv_path, sub_idx, start_time, width=720, height=480):
    sample_time = start_time + 0.1
    seek_time = max(0.0, sample_time - 2.0)
    fine_offset = sample_time - seek_time

    cmd = [
        "ffmpeg", "-nostdin", "-v", "error",
        "-ss", str(seek_time),
        "-i", mkv_path,
        "-f", "lavfi", "-i", f"color=c=black@0:s={width}x{height}:d=5,format=rgba",
        "-filter_complex", f"[1:v][0:s:{sub_idx}]overlay=eof_action=pass,format=rgba",
        "-ss", str(fine_offset),
        "-frames:v", "1",
        "-f", "image2pipe", "-vcodec", "png", "-"
    ]
    try:
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0 or not result.stdout:
            if not getattr(render_image_subtitle_frame, "_warned", False):
                err = result.stderr.decode("utf-8", errors="replace").strip()
                if err:
                    tqdm.write(f"   [WARN] ffmpeg subtitle render failed: {err.splitlines()[-1]}")
                render_image_subtitle_frame._warned = True
            return None
        return Image.open(io.BytesIO(result.stdout)).convert('RGBA')
    except Exception as e:
        if not getattr(render_image_subtitle_frame, "_warned", False):
            tqdm.write(f"   [WARN] ffmpeg subtitle render failed: {e}")
            render_image_subtitle_frame._warned = True
        return None


def subtitle_image_fingerprint(img):
    sample = img.convert("L").resize((64, 36), Image.Resampling.BILINEAR)
    return sample.tobytes()


def extract_sup(mkv_path, track_index, output_sup):
    cmd = [
        "ffmpeg", "-y", "-i", mkv_path,
        "-map", f"0:{track_index}",
        "-c", "copy", output_sup
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


# ==========================================
# PGS IN-PROCESS DECODER  (fast path)
# ==========================================

class BitReader:
    __slots__ = ("data", "pos")
    def __init__(self, data):
        self.data = data
        self.pos = 0
    def read_byte(self):
        if self.pos >= len(self.data):
            return None
        b = self.data[self.pos]
        self.pos += 1
        return b


def _pgs_decode_rle(data, width, height):
    if width <= 0 or height <= 0:
        return []
    pixels = [0] * (width * height)
    reader = BitReader(data)
    x = 0
    y = 0

    def write_run(color, length):
        nonlocal x, y
        while length > 0 and y < height:
            room = width - x
            count = min(length, room)
            start = y * width + x
            pixels[start:start + count] = [color] * count
            x += count
            length -= count
            if x >= width:
                x = 0
                y += 1

    while y < height:
        b = reader.read_byte()
        if b is None:
            break
        if b != 0:
            write_run(b, 1)
            continue
        flags = reader.read_byte()
        if flags is None:
            break
        if flags == 0:
            x = 0
            y += 1
        elif flags < 0x40:
            write_run(0, flags)
        elif flags < 0x80:
            lo = reader.read_byte()
            if lo is None: break
            write_run(0, ((flags & 0x3F) << 8) | lo)
        elif flags < 0xC0:
            color = reader.read_byte()
            if color is None: break
            write_run(color, flags & 0x3F)
        else:
            lo = reader.read_byte()
            color = reader.read_byte()
            if lo is None or color is None: break
            write_run(color, ((flags & 0x3F) << 8) | lo)
    return pixels


class PGSBitmapDecoder:
    """
    Decodes a .sup file fully in-process, yielding caption/clear events.
    Emits at END segment so the ODS for the current display set has been seen.
    """
    def __init__(self, sup_file):
        self.sup_file = sup_file
        self.palette = {}
        self._ods_buffer = bytearray()
        self._ods_expected_len = None
        self._ods_width = 0
        self._ods_height = 0
        self._bitmap_indices = None
        self._bitmap_w = 0
        self._bitmap_h = 0
        self._pending_pcs = None  # (obj_count, start_secs)
        self._lut = None

    def _parse_pds(self, data):
        palette = self.palette
        pos = 2
        n = len(data)
        while pos + 4 < n:
            idx = data[pos]
            y = data[pos + 1]
            cr = data[pos + 2]
            cb = data[pos + 3]
            a = data[pos + 4]
            r = y + 1.402 * (cr - 128)
            g = y - 0.34414 * (cb - 128) - 0.71414 * (cr - 128)
            b = y + 1.772 * (cb - 128)
            palette[idx] = (
                min(255, max(0, int(r))),
                min(255, max(0, int(g))),
                min(255, max(0, int(b))),
                a,
            )
            pos += 5

    def _parse_ods(self, data):
        if len(data) < 4:
            return
        sequence = data[3]
        is_first = bool(sequence & 0x80)
        is_last = bool(sequence & 0x40)

        if is_first:
            if len(data) < 11:
                return
            self._ods_expected_len = (data[4] << 16) | (data[5] << 8) | data[6]
            self._ods_width = (data[7] << 8) | data[8]
            self._ods_height = (data[9] << 8) | data[10]
            self._ods_buffer = bytearray(data[11:])
        else:
            if self._ods_expected_len is None:
                return
            self._ods_buffer.extend(data[4:])

        if is_last:
            rle = bytes(self._ods_buffer[:self._ods_expected_len])
            self._bitmap_indices = _pgs_decode_rle(rle, self._ods_width, self._ods_height)
            self._bitmap_w = self._ods_width
            self._bitmap_h = self._ods_height
            self._ods_buffer = bytearray()
            self._ods_expected_len = None

    def _render_bitmap(self):
        w, h = self._bitmap_w, self._bitmap_h
        idx_list = self._bitmap_indices
        if w <= 0 or h <= 0 or idx_list is None:
            return None

        palette = self.palette
        lut = [palette.get(i, (0, 0, 0, 0)) for i in range(256)]
        flat = bytearray(4 * len(idx_list))
        for i, idx in enumerate(idx_list):
            r, g, b, a = lut[idx]
            off = i * 4
            flat[off] = r
            flat[off + 1] = g
            flat[off + 2] = b
            flat[off + 3] = a
        return Image.frombytes('RGBA', (w, h), bytes(flat))

    def _emit_pending(self):
        if self._pending_pcs is None:
            return
        obj_count, start = self._pending_pcs
        self._pending_pcs = None
        if obj_count == 0:
            yield {'start': start, 'type': 'clear'}
            return
        img = self._render_bitmap()
        if img is None or is_image_blank(img):
            yield {'start': start, 'type': 'clear'}
            return
        img = autocrop_image(img, padding=20)
        yield {'start': start, 'type': 'caption', 'image': img}

    def parse(self):
        file_size = os.path.getsize(self.sup_file)
        with open(self.sup_file, 'rb') as f:
            with tqdm(total=file_size, unit='B', unit_scale=True,
                      desc="[1/2] Decoding PGS Stream") as pbar:
                while True:
                    header = f.read(13)
                    if len(header) < 13:
                        break
                    pbar.update(13)
                    magic, pts, _dts, seg_type, seg_size = struct.unpack('>2sIIBH', header)
                    if magic != b'PG':
                        f.seek(-12, 1)
                        continue
                    payload = f.read(seg_size)
                    pbar.update(seg_size)
                    pts_secs = pts / 90000.0

                    if seg_type == 0x14:
                        self._parse_pds(payload)
                    elif seg_type == 0x15:
                        self._parse_ods(payload)
                    elif seg_type == 0x16:
                        if self._pending_pcs is not None:
                            # Malformed / missing END; flush the previous one.
                            yield from self._emit_pending()
                        if len(payload) >= 11:
                            self._pending_pcs = (payload[10], pts_secs)
                    elif seg_type == 0x80:
                        if self._pending_pcs is not None:
                            yield from self._emit_pending()


def decode_pgs_captions(mkv_path, track, sup_file, frames_dir=None):
    """Yield events from the in-process decoder; optionally dump PNGs."""
    decoder = PGSBitmapDecoder(sup_file)
    frame_num = 0
    if frames_dir:
        os.makedirs(frames_dir, exist_ok=True)

    for ev in decoder.parse():
        if ev['type'] == 'clear':
            yield ev
            continue
        img = ev['image']
        if frames_dir:
            frame_filename = f"frame_{frame_num:04d}.png"
            img.save(os.path.join(frames_dir, frame_filename))
            yield {'start': ev['start'], 'end': None, 'type': 'caption',
                   'frame': frame_filename}
            frame_num += 1
        else:
            yield ev


# ==========================================
# FFMPEG-BASED DECODERS (VobSub + PGS fallback)
# ==========================================

def get_pgs_display_events(sup_file):
    events = []
    try:
        file_size = os.path.getsize(sup_file)
        with open(sup_file, 'rb') as f:
            with tqdm(total=file_size, unit='B', unit_scale=True,
                      desc="[1/2] Reading PGS Events") as pbar:
                while True:
                    header = f.read(13)
                    if len(header) < 13:
                        break
                    pbar.update(13)
                    magic, pts, _dts, seg_type, seg_size = struct.unpack('>2sIIBH', header)
                    if magic != b'PG':
                        f.seek(-12, 1)
                        continue
                    payload = f.read(seg_size)
                    pbar.update(seg_size)
                    if seg_type != 0x16 or len(payload) < 11:
                        continue
                    events.append({'start': pts / 90000.0,
                                   'type': 'caption' if payload[10] else 'clear'})
    except Exception as e:
        print(f"   [WARN] Could not read PGS display events: {e}")
    return events


def decode_pgs_captions_ffmpeg(mkv_path, track, sup_file, frames_dir=None):
    print(f"   [PGS/ffmpeg] Reading display events from stream {track['index']}...")
    events = get_pgs_display_events(sup_file)
    if not events:
        print("   [PGS] No display events found.")
        return

    width = int(track.get('width') or 1920)
    height = int(track.get('height') or 1080)
    if frames_dir:
        os.makedirs(frames_dir, exist_ok=True)

    frame_num = 0
    last_caption_fp = None
    with tqdm(total=len(events), desc="[1/2] Rendering PGS Events", unit="evt") as pbar:
        for event in events:
            start = event['start']
            if event['type'] == 'clear':
                last_caption_fp = None
                yield event
                pbar.update(1)
                continue

            img = render_image_subtitle_frame(mkv_path, track['sub_idx'], start, width, height)
            if not img or is_image_blank(img):
                pbar.update(1)
                continue

            fp = subtitle_image_fingerprint(img)
            if fp == last_caption_fp:
                pbar.update(1)
                continue
            last_caption_fp = fp

            img = autocrop_image(img, padding=20)
            if frames_dir:
                frame_filename = f"frame_{frame_num:04d}.png"
                img.save(os.path.join(frames_dir, frame_filename))
                yield {'start': start, 'end': None, 'type': 'caption',
                       'frame': frame_filename}
                frame_num += 1
            else:
                yield {'start': start, 'end': None, 'type': 'caption',
                       'image': img}
            pbar.update(1)


def _render_parallel(mkv_path, sub_idx, packet_entries, width, height,
                     max_workers=None):
    """Render every subtitle bitmap, running multiple ffmpeg processes at once.

    Yields (item, img) in the original packet order. img may be None on error.
    """
    if not packet_entries:
        return
    if max_workers is None:
        # ffmpeg is I/O- and CPU-bound; oversubscribe slightly.
        max_workers = min(12, max(2, (os.cpu_count() or 4)))

    # Small chunks so progress is visible and memory stays bounded.
    chunk_size = max_workers * 2

    def _render_one(item):
        try:
            return render_image_subtitle_frame(
                mkv_path, sub_idx, item['start'], width, height)
        except Exception:
            return None

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        for chunk_start in range(0, len(packet_entries), chunk_size):
            chunk = packet_entries[chunk_start:chunk_start + chunk_size]
            futures = [ex.submit(_render_one, item) for item in chunk]
            for item, fut in zip(chunk, futures):
                try:
                    img = fut.result()
                except Exception:
                    img = None
                yield item, img


def decode_image_subtitle_captions(mkv_path, track, frames_dir=None):
    codec_label = "PGS" if track.get('codec') == "hdmv_pgs_subtitle" else "VobSub"
    print(f"   [{codec_label}] Rendering subtitle bitmaps from stream {track['index']}...")

    width = int(track.get('width') or 720)
    height = int(track.get('height') or 480)
    print(f"   [{codec_label}] Render canvas: {width}x{height}")

    packet_entries = get_mkv_packet_entries(mkv_path, f"s:{track['sub_idx']}")
    if not packet_entries:
        print(f"   [{codec_label}] No packet timings found for this stream.")
        return

    if frames_dir:
        os.makedirs(frames_dir, exist_ok=True)

    frame_num = 0
    last_caption_fp = None
    was_showing_caption = False

    with tqdm(total=len(packet_entries),
              desc=f"[1/2] Rendering {codec_label} Stream", unit="pkt") as pbar:
        for item, img in _render_parallel(
                mkv_path, track['sub_idx'], packet_entries, width, height):
            start = item['start']
            duration = item.get('duration')
            end = start + duration if duration else None

            if img is not None:
                if is_image_blank(img):
                    last_caption_fp = None
                    if was_showing_caption:
                        was_showing_caption = False
                        yield {'start': start, 'type': 'clear'}
                    pbar.update(1)
                    continue

                fp = subtitle_image_fingerprint(img)
                if fp == last_caption_fp:
                    del img
                    pbar.update(1)
                    continue
                last_caption_fp = fp
                was_showing_caption = True

                img = autocrop_image(img, padding=30)
                if frames_dir:
                    frame_filename = f"frame_{frame_num:04d}.png"
                    img.save(os.path.join(frames_dir, frame_filename))
                    yield {'start': start, 'end': end, 'type': 'caption',
                           'frame': frame_filename}
                    frame_num += 1
                else:
                    yield {'start': start, 'end': end, 'type': 'caption',
                           'image': img}
                del img
            pbar.update(1)


# ==========================================
# EVENT RESOLUTION + BATCHED OCR PIPELINE
# ==========================================

def _clamp_end(start, end):
    if end is None or end <= start:
        end = start + DEFAULT_CAPTION_DURATION
    if end - start > MAX_CAPTION_DURATION:
        end = start + MAX_CAPTION_DURATION
    return end


def resolve_events(generator):
    """Consume decoder events, yield (start, end, image) with end resolved."""
    pending = None
    for ev in generator:
        if ev['type'] == 'caption':
            if pending is not None:
                pending_end = pending.get('end')
                if pending_end is None or pending_end > ev['start']:
                    pending_end = ev['start']
                yield pending['start'], _clamp_end(pending['start'], pending_end), pending['image']
            pending = ev
        elif ev['type'] == 'clear':
            if pending is not None:
                pending_end = pending.get('end')
                if pending_end is None or pending_end > ev['start']:
                    pending_end = ev['start']
                yield pending['start'], _clamp_end(pending['start'], pending_end), pending['image']
                pending = None
    if pending is not None:
        yield pending['start'], _clamp_end(pending['start'], pending.get('end')), pending['image']


def _count_iter(gen, desc):
    pbar = tqdm(desc=desc, unit="evt")
    try:
        for item in gen:
            yield item
            pbar.update(1)
    finally:
        pbar.close()


def perform_ocr_batched(generator, output_srt):
    """Two-pass: resolve events, then OCR in batches."""
    srt_lines = []
    counter = 1
    buf = []

    def flush():
        nonlocal counter
        if not buf:
            return
        images = [b[2] for b in buf]
        texts = batch_ocr(images)
        for (start, end, _), raw in zip(buf, texts):
            text = clean_ocr_text(raw or "")
            time_str = f"{format_time(start)} --> {format_time(end)}"
            if text:
                tqdm.write(f"    [{time_str}] {text}")
                srt_lines.extend([str(counter), time_str, text, ""])
                counter += 1
            else:
                tqdm.write(f"    [{time_str}] (empty - no text detected)")
        for _, _, im in buf:
            del im
        buf.clear()
        gc.collect()
        if GPU_DEVICE == 'cuda':
            try:
                torch.cuda.empty_cache()
            except Exception:
                pass

    for start, end, image in _count_iter(resolve_events(generator), "[2/2] OCR"):
        buf.append((start, end, image))
        if len(buf) >= BATCH_SIZE:
            flush()
    flush()

    with open(output_srt, 'w', encoding='utf-8') as f:
        f.write("\n".join(srt_lines))
    print(f"\n   SUCCESS! Saved: {output_srt}")


def perform_ocr_from_folder(frames_dir, output_srt):
    """Dump mode: OCR pre-rendered PNGs using timings.json."""
    timings_path = os.path.join(frames_dir, 'timings.json')
    with open(timings_path, 'r', encoding='utf-8') as f:
        timing_entries = json.load(f)

    caption_entries = [e for e in timing_entries if e.get('type') == 'caption']

    def _gen():
        for entry in caption_entries:
            frame_path = os.path.join(frames_dir, entry['frame'])
            if not os.path.exists(frame_path):
                continue
            img = Image.open(frame_path).convert('RGBA')
            yield entry['start'], entry['end'], img

    perform_ocr_batched(_gen(), output_srt)


# ==========================================
# MAIN PIPELINE
# ==========================================

def process_file(mkv_path, args):
    print(f"\n{'=' * 60}")
    print(f"Processing MKV: {mkv_path}")
    print(f"{'=' * 60}")

    tracks = get_subtitle_tracks(mkv_path)
    if not tracks:
        print("No supported image subtitle tracks found (PGS/VobSub).")
        return

    base_name = os.path.splitext(mkv_path)[0]
    used_outputs = set()

    for track in tracks:
        lang = track['lang']
        idx = track['index']
        codec = track['codec']
        codec_label = "PGS" if codec == "hdmv_pgs_subtitle" else "VobSub"
        print(f"\n-> Found {codec_label} Track {idx} ({lang})")

        output_srt = f"{base_name}.{lang}.srt"
        if output_srt in used_outputs:
            output_srt = f"{base_name}.{lang}.{idx}.srt"
        used_outputs.add(output_srt)

        frames_dir = f"{base_name}.track{idx}_frames"

        temp_sup = None
        try:
            if codec == "hdmv_pgs_subtitle":
                fd, temp_sup = tempfile.mkstemp(prefix="pgs_", suffix=".sup")
                os.close(fd)

            if not args.dump:
                print("   [STREAM] Starting in-memory OCR stream...")
                if codec == "hdmv_pgs_subtitle":
                    extract_sup(mkv_path, idx, temp_sup)
                    if PGS_BACKEND == "fast":
                        gen = decode_pgs_captions(mkv_path, track, temp_sup)
                    else:
                        gen = decode_pgs_captions_ffmpeg(mkv_path, track, temp_sup)
                else:
                    gen = decode_image_subtitle_captions(mkv_path, track)
                perform_ocr_batched(gen, output_srt)
            else:
                timings_file = os.path.join(frames_dir, 'timings.json')
                if os.path.exists(timings_file):
                    print(f"   [CACHE] Found existing frames in: {frames_dir}")
                    perform_ocr_from_folder(frames_dir, output_srt)
                else:
                    print("   [DISK] Decoding and dumping frames to disk...")
                    if codec == "hdmv_pgs_subtitle":
                        extract_sup(mkv_path, idx, temp_sup)
                        if PGS_BACKEND == "fast":
                            gen = decode_pgs_captions(mkv_path, track, temp_sup,
                                                      frames_dir=frames_dir)
                        else:
                            gen = decode_pgs_captions_ffmpeg(mkv_path, track, temp_sup,
                                                             frames_dir=frames_dir)
                    else:
                        gen = decode_image_subtitle_captions(
                            mkv_path, track, frames_dir=frames_dir)

                    captions = list(gen)
                    if not captions:
                        print("   Warning: No captions decoded.")
                        continue

                    timing_entries = []
                    for i, item in enumerate(captions):
                        if item.get('type') == 'clear':
                            timing_entries.append({'type': 'clear', 'start': item['start']})
                            continue
                        start_time = item['start']
                        end_time = item.get('end')
                        if not end_time:
                            end_time = start_time + DEFAULT_CAPTION_DURATION
                            for j in range(i + 1, len(captions)):
                                nxt = captions[j]
                                if nxt.get('type') in ('clear', 'caption'):
                                    end_time = nxt['start']
                                    if nxt.get('type') == 'caption':
                                        end_time -= 0.1
                                    break
                        timing_entries.append({
                            'type': 'caption',
                            'frame': item.get('frame'),
                            'start': start_time,
                            'end': end_time,
                        })

                    with open(timings_file, 'w', encoding='utf-8') as f:
                        json.dump(timing_entries, f, indent=2)

                    del captions
                    gc.collect()
                    perform_ocr_from_folder(frames_dir, output_srt)

        except KeyboardInterrupt:
            raise
        except Exception as e:
            print(f"   Error processing track {idx}: {e}")
        finally:
            if temp_sup and os.path.exists(temp_sup):
                try:
                    os.remove(temp_sup)
                except Exception:
                    pass


# ==========================================
# CLI
# ==========================================

def parse_args():
    parser = argparse.ArgumentParser(
        description="Extract PGS/VobSub subtitles from MKV and convert to SRT using OCR/LLM."
    )
    parser.add_argument("patterns", nargs="*",
                        help="File patterns (e.g., *.mkv). Defaults to common video types.")
    parser.add_argument("--dump", "-d", action="store_true",
                        help="Dump frame bitmaps to disk instead of streaming.")
    parser.add_argument("--ocr-engine",
                        choices=["easyocr", "tesseract", "ollama", "lmstudio"],
                        default="easyocr")
    parser.add_argument("--llm-url", default=None)
    parser.add_argument("--llm-model", default=None)
    parser.add_argument("--llm-timeout", type=int, default=120)
    parser.add_argument("--batch-size", type=int, default=8,
                        help="Batch size for OCR. Larger = faster, more memory.")
    parser.add_argument("--pgs-backend", choices=["fast", "ffmpeg"], default="fast",
                        help="PGS decoding backend. 'fast' uses the in-process decoder.")
    parser.add_argument("--no-cache", action="store_true",
                        help="Disable the persistent OCR cache.")
    return parser.parse_args()


def resolve_llm_settings(args):
    global LLM_API_URL, LLM_MODEL, LLM_TIMEOUT
    LLM_TIMEOUT = max(10, args.llm_timeout)

    if OCR_ENGINE == "ollama":
        LLM_API_URL = args.llm_url or "http://127.0.0.1:11434/v1/chat/completions"
        LLM_MODEL = args.llm_model
    elif OCR_ENGINE == "lmstudio":
        LLM_API_URL = args.llm_url or "http://127.0.0.1:1234/v1/chat/completions"
        LLM_MODEL = args.llm_model
    else:
        return

    if not LLM_MODEL:
        print("[INFO] --llm-model not provided. Querying available models...")
        try:
            model_ids = list_openai_compatible_models(LLM_API_URL, LLM_TIMEOUT)
        except Exception as e:
            print(f"[ERROR] Could not list models: {e}")
            sys.exit(1)
        if not model_ids:
            print("No models returned by endpoint.")
            sys.exit(1)

        print("\nAvailable models:")
        for i, mid in enumerate(model_ids, start=1):
            print(f"  {i}. {mid}")

        while True:
            choice = input("\nSelect model number (or 'q' to quit): ").strip()
            if choice.lower() in ("q", "quit", "exit"):
                sys.exit(0)
            if choice.isdigit():
                i = int(choice)
                if 1 <= i <= len(model_ids):
                    LLM_MODEL = model_ids[i - 1]
                    print(f"[INFO] Selected model: {LLM_MODEL}")
                    break
            print("Invalid selection.")

    print(f"[INFO] LLM endpoint: {LLM_API_URL}")
    print(f"[INFO] LLM model: {LLM_MODEL}")


def find_input_files(patterns):
    if not patterns:
        patterns = ["*.mkv", "*.mp4", "*.m4v", "*.mov", "*.avi", "*.ts", "*.m2ts", "*.webm"]
        print("[INFO] No pattern provided. Scanning current directory...")

    files = []
    for p in patterns:
        p = p.strip()
        if not p:
            continue
        matched = [p] if os.path.isfile(p) else glob.glob(p)
        if not matched and ('*' in p or '?' in p):
            import fnmatch
            try:
                matched = [f for f in os.listdir('.') if fnmatch.fnmatch(f, p)]
            except Exception:
                matched = []
        files.extend(matched)
    return sorted({f for f in files if os.path.isfile(f)})


def main():
    global OCR_ENGINE, BATCH_SIZE, PGS_BACKEND, USE_CACHE

    args = parse_args()
    OCR_ENGINE = args.ocr_engine
    BATCH_SIZE = max(1, args.batch_size)
    PGS_BACKEND = args.pgs_backend
    USE_CACHE = not args.no_cache

    check_runtime_dependencies()
    check_ffmpeg_tools()
    resolve_llm_settings(args)
    print_runtime_diagnostics()

    try:
        files = find_input_files(args.patterns)
        if not files:
            print(f"\n[ERROR] No files found matching: {args.patterns}")
            sys.exit(1)

        compatible_files = [f for f in files if get_subtitle_tracks(f)]
        if not compatible_files:
            print("\n[INFO] No compatible subtitle tracks found.")
            sys.exit(0)

        print(f"\n[INFO] Found {len(compatible_files)} compatible file(s).")
        for f in compatible_files:
            process_file(f, args)

    except KeyboardInterrupt:
        print("\n\n" + "!" * 30)
        print(" [!] Cancelled (Ctrl+C)")
        print("!" * 30)
        sys.exit(0)


if __name__ == "__main__":
    main()