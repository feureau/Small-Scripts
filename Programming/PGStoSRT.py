import sys
import os
import subprocess
import glob
import json
import struct
import io
import gc
import shutil
import argparse
import sys
import base64
import urllib.request
import urllib.error
import re

# ==========================================
# DEPENDENCY CHECK
# ==========================================
def check_dependencies():
    missing = []
    try:
        from PIL import Image, ImageOps
    except ImportError:
        missing.append("pillow")
    
    try:
        import pytesseract
    except ImportError:
        missing.append("pytesseract")

    try:
        from tqdm import tqdm
    except ImportError:
        missing.append("tqdm")

    # EasyOCR is optional, so we don't add it to 'missing' that forces exit.
    # We just check for Tesseract dependencies if EasyOCR isn't the only goal.
    # But for this script, we need at least ONE OCR engine.
    
    # We will soft-check Tesseract (pytesseract itself is a python wrapper, but needs tesseract-ocr)
    try:
        import pytesseract
    except ImportError:
        # If user doesn't have pytesseract, they MUST have easyocr later, 
        # but let's enforce pytesseract as baseline requirements for now to match old behavior
        # unless we want to fully decouple. 
        # For now, let's keep pytesseract as required fallback.
        pass # missing.append("pytesseract") was already handled above

    if missing:
        print("\n" + "!" * 50)
        print("ERROR: Missing required Python modules.")
        print("Please run the following command to install them:")
        print(f"\n    pip install {' '.join(missing)}")
        print("\n" + "!" * 50)
        sys.exit(1)

# Run check before importing
check_dependencies()

from PIL import Image, ImageOps, ImageFilter
import pytesseract
from tqdm import tqdm

# Optional EasyOCR Import & GPU Diagnostics
HAS_EASYOCR = False
GPU_DEVICE = 'cpu'
try:
    import easyocr
    import torch
    HAS_EASYOCR = True

    gpu_available = torch.cuda.is_available()
    GPU_DEVICE = 'cuda' if gpu_available else 'cpu'

    print(f"\n--- GPU Diagnostics ---")
    print(f"  PyTorch version : {torch.__version__}")
    print(f"  CUDA built-in   : {torch.version.cuda or 'NO (CPU-only PyTorch build)'}")

    if gpu_available:
        gpu_name = torch.cuda.get_device_name(0)
        vram_total = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        print(f"  GPU detected    : {gpu_name}")
        print(f"  VRAM            : {vram_total:.1f} GB")
        print(f"  OCR Engine      : EasyOCR (GPU)")
        print(f"  STATUS          : ✅ Using GPU")
    else:
        if not torch.version.cuda:
            print(f"  OCR Engine      : EasyOCR (CPU)")
            print(f"  STATUS          : ❌ CPU-only (reinstall PyTorch with CUDA to enable GPU)")
            print(f"  Fix             : pip install torch --index-url https://download.pytorch.org/whl/cu121")
        else:
            print(f"  OCR Engine      : EasyOCR (CPU)")
            print(f"  STATUS          : ❌ CUDA built-in but no GPU found")
    print(f"-----------------------\n")
except ImportError:
    print("\n--- GPU Diagnostics ---")
    print(f"  OCR Engine      : Tesseract (CPU only)")
    print(f"  STATUS          : ⚠️  EasyOCR not installed, using Tesseract fallback")
    print(f"  Tip             : pip install easyocr torch  (for GPU acceleration)")
    print(f"-----------------------\n")


# ==========================================
# CONFIGURATION
# ==========================================

# Tesseract Configuration
TESSERACT_CONFIG = r'--psm 6'
LANG = 'eng'
OCR_ENGINE = 'easyocr'
LLM_API_URL = "http://127.0.0.1:11434/v1/chat/completions"
LLM_MODEL = "llava"
LLM_TIMEOUT = 120
LLM_PROMPT = "Read only the subtitle text in this image. Return plain text only, no quotes, no explanation."

# ==========================================
# CORE PGS PARSER & DECODER
# ==========================================

class BitReader:
    def __init__(self, data):
        self.data = data
        self.pos = 0

    def read_byte(self):
        if self.pos >= len(self.data):
            return None
        b = self.data[self.pos]
        self.pos += 1
        return b
def is_image_blank(img):
    """Check if an image is entirely transparent or empty."""
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    extrema = img.getextrema()
    # extrema[3] is the (min, max) of the alpha channel
    if len(extrema) >= 4 and extrema[3][1] == 0:
        return True
    return False
def autocrop_image(img, padding=20):
    """Crop the image to its non-transparent content with some padding."""
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    bbox = img.getbbox()
    if not bbox:
        return img
    
    # Expand bbox with padding
    left, upper, right, lower = bbox
    left = max(0, left - padding)
    upper = max(0, upper - padding)
    right = min(img.width, right + padding)
    lower = min(img.height, lower + padding)
    
    return img.crop((left, upper, right, lower))

class PGSDecoder:
    def __init__(self, sup_file, mkv_timings=None, frames_dir=None):
        self.sup_file = sup_file
        self.palette = {} 
        self.captions = []  # timing entries (no images in memory)
        self.mkv_timings = mkv_timings or {}
        self.frames_dir = frames_dir
        self.frame_count = 0
        self._ods_buffer = bytearray()
        self._ods_expected_len = None
        self._ods_width = 0
        self._ods_height = 0
        if frames_dir:
            os.makedirs(frames_dir, exist_ok=True)

    def parse(self):
        file_size = os.path.getsize(self.sup_file)
        
        with open(self.sup_file, 'rb') as f:
            with tqdm(total=file_size, unit='B', unit_scale=True, desc="[1/2] Decoding Binary Stream") as pbar:
                while True:
                    header = f.read(13)
                    if len(header) < 13:
                        break
                    
                    pbar.update(13)

                    magic, pts, dts, seg_type, seg_size = struct.unpack('>2sIIBH', header)
                    
                    if magic != b'PG':
                        # Valid sync recovery might be needed here in complex cases
                        f.seek(-12, 1)
                        continue

                    payload = f.read(seg_size)
                    pbar.update(seg_size)
                    
                    pts_secs = pts / 90000.0

                    if seg_type == 0x14:   # PDS
                        self._parse_pds(payload)
                    elif seg_type == 0x15: # ODS
                        self._parse_ods(payload)
                    elif seg_type == 0x16: # PCS
                        res = self._parse_pcs(payload, pts_secs)
                        if res:
                            yield res
                    elif seg_type == 0x80: # END
                        pass

    def _parse_pds(self, data):
        pos = 2 
        while pos + 4 < len(data):
            idx = data[pos]
            y = data[pos+1]
            cr = data[pos+2]
            cb = data[pos+3]
            a_raw = data[pos+4]
            # PGS stores opacity in the palette alpha byte; Pillow uses the same
            # 0 transparent .. 255 opaque convention.
            a = a_raw
            r = y + 1.402 * (cr - 128)
            g = y - 0.34414 * (cb - 128) - 0.71414 * (cr - 128)
            b = y + 1.772 * (cb - 128)
            self.palette[idx] = (min(255, max(0, int(r))), min(255, max(0, int(g))), min(255, max(0, int(b))), a)
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
            width = self._ods_width
            height = self._ods_height
            rle_data = bytes(self._ods_buffer[:self._ods_expected_len])
            self.current_bitmap_idx = self._decode_rle(rle_data, width, height)
            self.current_width = width
            self.current_height = height
            self._ods_buffer = bytearray()
            self._ods_expected_len = None

    def _decode_rle(self, data, width, height):
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
                # End of line. PGS RLE rows may be shorter than the bitmap width.
                if x:
                    x = 0
                    y += 1
                else:
                    y += 1
            elif flags < 0x40:
                write_run(0, flags)
            elif flags < 0x80:
                length_lo = reader.read_byte()
                if length_lo is None:
                    break
                write_run(0, ((flags & 0x3F) << 8) | length_lo)
            elif flags < 0xC0:
                color = reader.read_byte()
                if color is None:
                    break
                write_run(color, flags & 0x3F)
            else:
                length_lo = reader.read_byte()
                color = reader.read_byte()
                if length_lo is None or color is None:
                    break
                write_run(color, ((flags & 0x3F) << 8) | length_lo)
        return pixels

    def _parse_pcs(self, data, pts):
        # ... (headers parsing same as before)
        if len(data) < 11:
            return None

        obj_count = data[10]

        if obj_count == 0:
            # This is a "Clear Screen" or empty state
            item = {'start': pts, 'type': 'clear'}
            self.captions.append(item)
            return item
        else:
            # It has objects. If we have a pending bitmap, assemble it.
            if hasattr(self, 'current_bitmap_idx') and hasattr(self, 'current_width') and self.palette:
                tqdm.write(f"    -> Frame assembled at PTS: {format_time(pts)}")

                img = Image.new('RGBA', (self.current_width, self.current_height))
                pixels = img.load()
                idx_list = self.current_bitmap_idx
                
                for i in range(len(idx_list)):
                    idx = idx_list[i]
                    x = i % self.current_width
                    y = i // self.current_width
                    if y >= self.current_height: break
                    if idx in self.palette:
                        pixels[x, y] = self.palette[idx]
                    else:
                        pixels[x, y] = (0, 0, 0, 0)
                
                # Attempt to find duration from MKV timings
                pts_key = round(pts, 3)
                duration = self.mkv_timings.get(pts_key)
                
                if duration is None:
                    for offset in [-0.001, 0.001, -0.002, 0.002]:
                        duration = self.mkv_timings.get(round(pts + offset, 3))
                        if duration: break
                
                start = pts
                end = None
                if duration:
                    end = start + duration
                
                item = None
                # Save frame to disk immediately if we have a frames_dir
                if self.frames_dir:
                    if not is_image_blank(img):
                        # Dynamic crop with padding
                        img = autocrop_image(img, padding=20)
                        
                        frame_filename = f"frame_{self.frame_count:04d}.png"
                        frame_path = os.path.join(self.frames_dir, frame_filename)
                        img.save(frame_path)
                        item = {'start': start, 'end': end, 'type': 'caption', 'frame': frame_filename}
                        self.captions.append(item)
                        self.frame_count += 1
                    else:
                        # Log but don't save or add to frame count if it's blank
                        tqdm.write(f"    [SKIP] Found empty PGS frame at {format_time(start)}")
                else:
                    item = {'start': start, 'end': end, 'type': 'caption', 'image': img}
                    self.captions.append(item)
                
                # Clear the pending bitmap data
                del self.current_bitmap_idx
                return item
        return None

# ==========================================
# OCR & SRT GENERATION
# ==========================================

READER = None

def get_easyocr_reader():
    global READER
    if READER is None and HAS_EASYOCR:
        try:
            print("   [INFO] Initializing EasyOCR model (this may take a moment)...")
            # EasyOCR uses 2-letter codes. 'eng' -> 'en'
            lang_code = 'en' if LANG == 'eng' else LANG 
            use_gpu = (GPU_DEVICE == 'cuda')
            READER = easyocr.Reader([lang_code], gpu=use_gpu)
            engine_label = "GPU" if use_gpu else "CPU"
            print(f"   [INFO] EasyOCR ready ({engine_label})")
        except Exception as e:
            print(f"   [WARN] Failed to init EasyOCR: {e}. Fallback to Tesseract.")
            return None
    return READER

def preprocess_image(img):
    bg_black = Image.new("RGB", img.size, (0, 0, 0))
    if img.mode in ("RGBA", "LA") or ("transparency" in img.info):
        bg_black.paste(img.convert("RGB"), mask=img.split()[-1])
    else:
        bg_black.paste(img.convert("RGB"))
    
    # Scale up small text for better Tesseract detection
    MIN_HEIGHT = 80
    w, h = bg_black.size
    if h < MIN_HEIGHT:
        scale = MIN_HEIGHT / h
        new_w = int(w * scale)
        bg_black = bg_black.resize((new_w, MIN_HEIGHT), Image.LANCZOS)
    
    # For Tesseract: We want Black Text on White Background -> Invert
    gray = bg_black.convert('L')
    gray = ImageOps.invert(gray)
    return gray

def preprocess_for_easyocr(img):
    # EasyOCR loves contrast. White text on Black background (standard PGS) is usually fine.
    # But just to be safe, let's composite onto black like we do for Tesseract,
    # but skip the inversion (keep text white, BG black).
    bg_black = Image.new("RGB", img.size, (0, 0, 0))
    if img.mode in ("RGBA", "LA") or ("transparency" in img.info):
        bg_black.paste(img.convert("RGB"), mask=img.split()[-1])
    else:
        bg_black.paste(img.convert("RGB"))
    
    bg_black = ImageOps.autocontrast(bg_black.convert("L")).convert("RGB")

    # Upscale subtitle bitmaps aggressively; Blu-ray subtitle glyphs are often
    # only 25-45 px tall after cropping, which is too soft for EasyOCR.
    MIN_HEIGHT = 160
    w, h = bg_black.size
    if h < MIN_HEIGHT:
        scale = MIN_HEIGHT / h
        new_w = int(w * scale)
        bg_black = bg_black.resize((new_w, MIN_HEIGHT), Image.LANCZOS)
    bg_black = bg_black.filter(ImageFilter.SHARPEN)
    
    return bg_black

def ocr_with_openai_compatible(img, api_url, model, timeout):
    proc_img = preprocess_for_easyocr(img)
    buf = io.BytesIO()
    proc_img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": LLM_PROMPT},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}
                ]
            }
        ],
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

    req = urllib.request.Request(
        models_url,
        headers={"Content-Type": "application/json"},
        method="GET"
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8", errors="replace"))

    model_ids = []
    for item in data.get("data", []):
        mid = item.get("id")
        if mid:
            model_ids.append(mid)
    return model_ids

def ocr_image(img):
    if OCR_ENGINE == "easyocr":
        reader = get_easyocr_reader()
        if reader:
            import numpy as np
            proc_img = preprocess_for_easyocr(img)
            img_np = np.array(proc_img)
            try:
                results = reader.readtext(img_np, detail=0, paragraph=True,
                                          text_threshold=0.4, low_text=0.3,
                                          mag_ratio=1.5)
                return " ".join(results)
            except Exception:
                return ""
            finally:
                del proc_img, img_np
        proc_img = preprocess_image(img)
        try:
            return pytesseract.image_to_string(proc_img, lang=LANG, config=TESSERACT_CONFIG)
        finally:
            del proc_img

    if OCR_ENGINE == "tesseract":
        proc_img = preprocess_image(img)
        try:
            return pytesseract.image_to_string(proc_img, lang=LANG, config=TESSERACT_CONFIG)
        finally:
            del proc_img

    if OCR_ENGINE in ("ollama", "lmstudio"):
        try:
            return ocr_with_openai_compatible(img, LLM_API_URL, LLM_MODEL, LLM_TIMEOUT)
        except urllib.error.URLError as e:
            print(f"   [ERR] {OCR_ENGINE} request failed: {e}")
            return ""
        except Exception as e:
            print(f"   [ERR] {OCR_ENGINE} OCR failed: {e}")
            return ""

    return ""

def clean_ocr_text(text):
    text = text.strip()
    if not text:
        return ""

    text = text.replace('|', 'I').replace('\n', ' ')
    text = re.sub(r'\s+', ' ', text)

    # Common EasyOCR confusions on white PGS subtitles.
    replacements = {
        "AIl": "All",
        "aIl": "all",
        "IlI": "I'll",
        "III": "I'll",
        "They'Il": "They'll",
        "they'Il": "they'll",
        "you'Il": "you'll",
        "we'Il": "we'll",
        "I'Il": "I'll",
        "Iegal": "legal",
        "Iaunch": "launch",
        "out off": "cut off",
        "uS": "us",
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)

    text = re.sub(r'\bI(?=(?:wish|want|need|can|can\'t|could|couldn\'t|just|don\'t|didn\'t|doubt|know|knew|thought|hope|had|have|am|was|will|would)\b)', 'I ', text)
    text = re.sub(r'\b([Tt]hey|[Ww]e|[Yy]ou|[Ss]he|[Hh]e)' + r"'Il\b", r"\1'll", text)
    text = re.sub(r'(?<![-\w.])(?:0|9)(?![-\w.%])', '', text)

    # Subtitle outlines/shadows are often read as junk at line ends.
    text = re.sub(r'\s*(?:[_"“”\'`]+|\d+|[0O])+\s*$', '', text)
    text = re.sub(r'([A-Za-z])_\b', r'\1', text)
    text = re.sub(r'\s+([,.;:!?])', r'\1', text)
    text = re.sub(r'([.!?])\s*[._]+$', r'\1', text)
    text = re.sub(r'_\s*$', '.', text)

    # EasyOCR frequently reads a final exclamation mark as lowercase L.
    text = re.sub(r'\b([A-Za-z]{2,})l([.!?]?)$', lambda m: m.group(1) + ('!' if not m.group(2) else m.group(2)), text)
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



def perform_ocr_from_folder(frames_dir, output_srt):
    """
    Run OCR on frames previously dumped to a folder.
    Reads timings.json and frame PNGs from the folder.
    """
    timings_path = os.path.join(frames_dir, 'timings.json')
    with open(timings_path, 'r', encoding='utf-8') as f:
        timing_entries = json.load(f)
    
    # Filter to caption entries only
    caption_entries = [e for e in timing_entries if e.get('type') == 'caption']
    
    srt_lines = []
    counter = 1
    
    pbar = tqdm(total=len(caption_entries), desc="[2/2] Running OCR", unit="frame")
    
    try:
        for entry in caption_entries:
            start_time = entry['start']
            end_time = entry['end']
            frame_path = os.path.join(frames_dir, entry['frame'])
            
            if not os.path.exists(frame_path):
                pbar.update(1)
                continue
            
            # Load the frame from disk
            img = Image.open(frame_path).convert('RGBA')
            
            text = clean_ocr_text(ocr_image(img))
            
            time_str = f"{format_time(start_time)} --> {format_time(end_time)}"
            clean_text = text.replace('\n', ' ')
            
            if text:
                tqdm.write(f"    [{time_str}] {clean_text}")
                
                srt_lines.append(f"{counter}")
                srt_lines.append(time_str)
                srt_lines.append(text)
                srt_lines.append("")
                counter += 1
            else:
                tqdm.write(f"    [{time_str}] (empty - no text detected)")
            
            # Free memory after each frame
            del img
            
            if counter % 20 == 0:
                gc.collect()
                if GPU_DEVICE == 'cuda':
                    try:
                        torch.cuda.empty_cache()
                    except Exception:
                        pass
            
            pbar.update(1)
    finally:
        pbar.close()
    
    # Write SRT
    srt_content = "\n".join(srt_lines)
    with open(output_srt, 'w', encoding='utf-8') as f:
        f.write(srt_content)
    
    print(f"\n   SUCCESS! Saved: {output_srt}")
    return srt_content

# ==========================================
# MAIN PIPELINE
# ==========================================

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
                'height': stream.get('height') or video_height
            })
    return tracks

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
        width = int(stream.get("width") or 1920)
        height = int(stream.get("height") or 1080)
        return width, height
    except Exception:
        return 1920, 1080

def get_mkv_packet_entries(mkv_path, track_selector):
    """
    Extract packet timings for one subtitle track and preserve packet order.
    Returns a list of dicts: [{'start': float, 'duration': float_or_none}, ...]
    """
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
                    entries.append({'start': pts, 'duration': dur if dur and dur > 0 else None})
            except (ValueError, TypeError):
                continue
        return entries
    except Exception as e:
        print(f"   [WARN] Could not extract packet timing list: {e}")
        return []

def get_mkv_timings(mkv_path, track_selector):
    """
    Extracts packet timings (pts_time, duration_time) for a specific track.
    Returns a dictionary mapping start_time -> end_time (approx).
    Or better, a list of (start, end) tuples we can search.
    """
    print(f"   [SYNC] extraction packet timings from MKV ({track_selector})...")
    cmd = [
        "ffprobe", "-v", "error", 
        "-select_streams", str(track_selector),
        "-show_entries", "packet=pts_time,duration_time",
        "-of", "json", mkv_path
    ]
    try:
        # This might be large for long movies, but usually manageable (few MB of JSON)
        result = subprocess.run(cmd, capture_output=True, text=True)
        data = json.loads(result.stdout)
        
        timings = {} 
        # We Map: PTS (float) -> Duration (float)
        # Note: PTS in ffprobe is usually seconds (pts_time).
        # We need to match this with 'pts' from PGSDecoder which is converted to seconds.
        # Floating point matching require epsilon.
        
        for p in data.get('packets', []):
            try:
                pts = float(p.get('pts_time', 0))
                dur = float(p.get('duration_time', 0))
                if dur > 0:
                    # Rounding to 3 decimals to match our format_time logic often helps key stability
                    key = round(pts, 3) 
                    timings[key] = dur
            except (ValueError, TypeError):
                continue
                
        print(f"   [SYNC] Found {len(timings)} timed packets.")
        return timings
    except Exception as e:
        print(f"   [WARN] Could not extract packet timings: {e}")
        return {}

def render_image_subtitle_frame(mkv_path, sub_idx, start_time, width=720, height=480):
    # Small offset helps ensure we sample during the subtitle duration, not at the boundary.
    # 0.1s is usually safe for VobSub/PGS.
    sample_time = start_time + 0.1
    
    # Seek to 2 seconds before target to ensure we catch the subtitle packet even if
    # timestamps are slightly jittery.
    seek_time = max(0.0, sample_time - 2.0)
    fine_offset = sample_time - seek_time
    
    # We use Input 0 for MKV and Input 1 for the transparent background.
    # We force format=rgba on the overlay to ensure our blank-check works.
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
    """
    Small perceptual-ish fingerprint used only to skip repeated rendered states.
    Exact OCR text comparison is too expensive because OCR is the slow part.
    """
    sample = img.convert("L").resize((64, 36), Image.Resampling.BILINEAR)
    return sample.tobytes()

def get_pgs_display_events(sup_file):
    """
    Read only PGS presentation composition segments for display/clear timing.
    Bitmap decoding stays delegated to ffmpeg so OCR sees player-rendered frames.
    """
    events = []
    try:
        file_size = os.path.getsize(sup_file)
        with open(sup_file, 'rb') as f:
            with tqdm(total=file_size, unit='B', unit_scale=True, desc="[1/2] Reading PGS Events") as pbar:
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
                    start = pts / 90000.0
                    obj_count = payload[10]
                    events.append({'start': start, 'type': 'caption' if obj_count else 'clear'})
    except Exception as e:
        print(f"   [WARN] Could not read PGS display events: {e}")
    return events

def decode_pgs_captions(mkv_path, track, sup_file, frames_dir=None):
    print(f"   [PGS] Reading display events from stream {track['index']}...")
    events = get_pgs_display_events(sup_file)
    if not events:
        print("   [PGS] No display events found.")
        return

    width = int(track.get('width') or 1920)
    height = int(track.get('height') or 1080)
    print(f"   [PGS] Render canvas: {width}x{height}")

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
                yield {'start': start, 'end': None, 'type': 'caption', 'frame': frame_filename}
                frame_num += 1
            else:
                yield {'start': start, 'end': None, 'type': 'caption', 'image': img}
            pbar.update(1)

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
    with tqdm(total=len(packet_entries), desc=f"[1/2] Rendering {codec_label} Stream", unit="pkt") as pbar:
        for item in packet_entries:
            start = item['start']
            duration = item.get('duration')
            end = start + duration if duration else None
            img = render_image_subtitle_frame(mkv_path, track['sub_idx'], start, width, height)
            if img:
                if is_image_blank(img):
                    last_caption_fp = None
                    if was_showing_caption:
                        was_showing_caption = False
                        yield {'start': start, 'type': 'clear'}
                    pbar.update(1)
                    continue

                fp = subtitle_image_fingerprint(img)
                if fp == last_caption_fp:
                    pbar.update(1)
                    continue
                last_caption_fp = fp
                was_showing_caption = True

                if frames_dir:
                    # Dynamic crop with padding to avoid massive disk usage
                    img = autocrop_image(img, padding=20)

                    frame_filename = f"frame_{frame_num:04d}.png"
                    img.save(os.path.join(frames_dir, frame_filename))
                    res = {'start': start, 'end': end, 'type': 'caption', 'frame': frame_filename}
                    yield res
                    frame_num += 1
                else:
                    img = autocrop_image(img, padding=20)
                    res = {'start': start, 'end': end, 'type': 'caption', 'image': img}
                    yield res
            pbar.update(1)

def extract_sup(mkv_path, track_index, output_sup):
    cmd = [
        "ffmpeg", "-y", "-i", mkv_path,
        "-map", f"0:{track_index}",
        "-c", "copy", output_sup
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def process_file(mkv_path, args):
    print(f"\n{'='*60}")
    print(f"Processing MKV: {mkv_path}")
    print(f"{'='*60}")
    
    tracks = get_subtitle_tracks(mkv_path)
    if not tracks:
        print("No supported image subtitle tracks found (PGS/VobSub).")
        return

    base_name = os.path.splitext(mkv_path)[0]
    
    for track in tracks:
        lang = track['lang']
        idx = track['index']
        codec = track['codec']
        codec_label = "PGS" if codec == "hdmv_pgs_subtitle" else "VobSub"
        print(f"\n-> Found {codec_label} Track {idx} ({lang})")
        
        temp_sup = f"temp_{idx}.sup"
        output_srt = f"{base_name}.{lang}.srt"
        frames_dir = f"{base_name}.track{idx}_frames"
        
def perform_ocr_streaming(generator, output_srt):
    """
    Run OCR on frames directly from a generator (no disk dump).
    Buffers events to resolve timing.
    """
    srt_lines = []
    counter = 1
    
    pbar = tqdm(desc="[1/1] Streaming OCR", unit="frame")
    pending_caption = None
    
    def write_caption(cap, end_time):
        nonlocal counter
        start_time = cap['start']
        img = cap['image']
        
        if not end_time or end_time <= start_time:
            end_time = start_time + 4.0
        if end_time - start_time > 10:
            end_time = start_time + 10
            
        time_str = f"{format_time(start_time)} --> {format_time(end_time)}"
        
        text = clean_ocr_text(ocr_image(img))
        clean_text = text.replace('\n', ' ')
        
        if text:
            tqdm.write(f"    [{time_str}] {clean_text}")
            srt_lines.append(f"{counter}")
            srt_lines.append(time_str)
            srt_lines.append(text)
            srt_lines.append("")
            counter += 1
        else:
            tqdm.write(f"    [{time_str}] (empty - no text detected)")
        del img

    try:
        for event in generator:
            if event['type'] == 'caption':
                if pending_caption:
                    end = pending_caption.get('end') or event['start']
                    write_caption(pending_caption, end)
                    pbar.update(1)
                pending_caption = event
            elif event['type'] == 'clear':
                if pending_caption:
                    end = event['start']
                    write_caption(pending_caption, end)
                    pending_caption = None
                    pbar.update(1)
            
            if counter % 20 == 0:
                gc.collect()
                if GPU_DEVICE == 'cuda':
                    try: torch.cuda.empty_cache()
                    except Exception:
                        pass
        if pending_caption:
            write_caption(pending_caption, pending_caption.get('end'))
            pbar.update(1)
    finally:
        pbar.close()
        
    srt_content = "\n".join(srt_lines)
    with open(output_srt, 'w', encoding='utf-8') as f:
        f.write(srt_content)
    print(f"\n   SUCCESS! Saved: {output_srt}")


def process_file(mkv_path, args):
    print(f"\n{'='*60}")
    print(f"Processing MKV: {mkv_path}")
    print(f"{'='*60}")
    
    tracks = get_subtitle_tracks(mkv_path)
    if not tracks:
        print("No supported image subtitle tracks found (PGS/VobSub).")
        return

    base_name = os.path.splitext(mkv_path)[0]
    
    for track in tracks:
        lang = track['lang']
        idx = track['index']
        codec = track['codec']
        codec_label = "PGS" if codec == "hdmv_pgs_subtitle" else "VobSub"
        print(f"\n-> Found {codec_label} Track {idx} ({lang})")
        
        temp_sup = f"temp_{idx}.sup"
        output_srt = f"{base_name}.{lang}.srt"
        frames_dir = f"{base_name}.track{idx}_frames"
        
        try:
            if not args.dump:
                # === STREAM MODE (Default) ===
                print("   [STREAM] Starting in-memory OCR stream...")
                if codec == "hdmv_pgs_subtitle":
                    extract_sup(mkv_path, idx, temp_sup)
                    perform_ocr_streaming(decode_pgs_captions(mkv_path, track, temp_sup), output_srt)
                else:
                    perform_ocr_streaming(decode_image_subtitle_captions(mkv_path, track), output_srt)
            else:
                # === DISK MODE (Flagged via --dump) ===
                timings_file = os.path.join(frames_dir, 'timings.json')
                if os.path.exists(timings_file):
                    print(f"   [CACHE] Found existing frames in: {frames_dir}")
                    print(f"   [CACHE] Skipping decode.")
                    perform_ocr_from_folder(frames_dir, output_srt)
                else:
                    print("   [DISK] Decoding and dumping frames to disk...")
                    if codec == "hdmv_pgs_subtitle":
                        extract_sup(mkv_path, idx, temp_sup)
                        captions = list(decode_pgs_captions(mkv_path, track, temp_sup, frames_dir=frames_dir))
                    else:
                        captions = list(decode_image_subtitle_captions(mkv_path, track, frames_dir=frames_dir))
                    
                    if not captions:
                         print("   Warning: No captions decoded.")
                         continue
                         
                    # Save timings.json
                    timing_entries = []
                    for i, item in enumerate(captions):
                        if item.get('type') == 'clear':
                            timing_entries.append({'type': 'clear', 'start': item['start']})
                            continue
                        
                        start_time = item['start']
                        end_time = item.get('end')
                        if not end_time:
                            end_time = start_time + 4
                            for j in range(i + 1, len(captions)):
                                nxt = captions[j]
                                if nxt.get('type') in ['clear', 'caption']:
                                    end_time = nxt['start']
                                    if nxt.get('type') == 'caption': end_time -= 0.1
                                    break
                        timing_entries.append({'type': 'caption', 'frame': item.get('frame'), 'start': start_time, 'end': end_time})
                    
                    with open(timings_file, 'w', encoding='utf-8') as f:
                        json.dump(timing_entries, f, indent=2)
                    
                    del captions
                    gc.collect()
                    perform_ocr_from_folder(frames_dir, output_srt)
                
        except KeyboardInterrupt:
            raise  # Pass it up to main
        except Exception as e:
            print(f"   Error processing track {idx}: {e}")
        finally:
            # Clean up the temp .sup file (but keep the frames folder for re-runs)
            if os.path.exists(temp_sup):
                try:
                    os.remove(temp_sup)
                except Exception:
                    pass

def main():
    global OCR_ENGINE, LLM_API_URL, LLM_MODEL, LLM_TIMEOUT
    parser = argparse.ArgumentParser(description="Extract PGS/VobSub subtitles from MKV and convert to SRT using OCR/LLM.")
    parser.add_argument("patterns", nargs="*", help="File patterns to search for (e.g., *.mkv). Defaults to common video types if omitted.")
    parser.add_argument("--dump", "-d", action="store_true", help="Dump mode: Save all frame bitmaps to a folder (useful for debugging/caching). Streaming is default.")
    parser.add_argument("--ocr-engine", choices=["easyocr", "tesseract", "ollama", "lmstudio"], default="easyocr", help="OCR backend to use.")
    parser.add_argument("--llm-url", default=None, help="OpenAI-compatible chat/completions URL for ollama/lmstudio.")
    parser.add_argument("--llm-model", default=None, help="Vision model name for ollama/lmstudio.")
    parser.add_argument("--llm-timeout", type=int, default=120, help="HTTP timeout in seconds for ollama/lmstudio requests.")
    
    args = parser.parse_args()
    OCR_ENGINE = args.ocr_engine
    LLM_TIMEOUT = max(10, args.llm_timeout)
    if OCR_ENGINE == "ollama":
        LLM_API_URL = args.llm_url or "http://127.0.0.1:11434/v1/chat/completions"
        LLM_MODEL = args.llm_model
    elif OCR_ENGINE == "lmstudio":
        LLM_API_URL = args.llm_url or "http://127.0.0.1:1234/v1/chat/completions"
        LLM_MODEL = args.llm_model
    else:
        if args.llm_url:
            LLM_API_URL = args.llm_url
        if args.llm_model:
            LLM_MODEL = args.llm_model

    print(f"[INFO] OCR engine: {OCR_ENGINE}")
    if OCR_ENGINE in ("ollama", "lmstudio"):
        if not LLM_MODEL:
            print("[INFO] --llm-model not provided. Querying available models...")
            try:
                model_ids = list_openai_compatible_models(LLM_API_URL, LLM_TIMEOUT)
                if model_ids:
                    print("\nAvailable models:")
                    for i, mid in enumerate(model_ids, start=1):
                        print(f"  {i}. {mid}")

                    while True:
                        choice = input("\nSelect model number (or 'q' to quit): ").strip()
                        if choice.lower() in ("q", "quit", "exit"):
                            print("Cancelled by user.")
                            sys.exit(0)
                        if choice.isdigit():
                            idx = int(choice)
                            if 1 <= idx <= len(model_ids):
                                LLM_MODEL = model_ids[idx - 1]
                                print(f"[INFO] Selected model: {LLM_MODEL}")
                                break
                        print("Invalid selection. Enter a valid number or 'q'.")
                else:
                    print("No models returned by endpoint.")
                    sys.exit(1)
            except Exception as e:
                print(f"[ERROR] Could not list models: {e}")
                print("\nPlease rerun with --llm-model <model_id>.")
                sys.exit(1)
        print(f"[INFO] LLM endpoint: {LLM_API_URL}")
        print(f"[INFO] LLM model: {LLM_MODEL}")
    
    try:
        # If no args are provided, scan common video containers in CWD.
        patterns = args.patterns
        if not patterns:
            patterns = ["*.mkv", "*.mp4", "*.m4v", "*.mov", "*.avi", "*.ts", "*.m2ts", "*.webm"]
            print("[INFO] No pattern provided. Scanning current directory for compatible files...")
        
        files = []
        cwd = os.getcwd()
        
        for p in patterns:
            p = p.strip()
            if not p: continue
            if os.path.isfile(p):
                matched = [p]
            else:
                matched = glob.glob(p)
            if not matched and ('*' in p or '?' in p):
                import fnmatch
                try:
                    all_files = os.listdir('.')
                    matched = [f for f in all_files if fnmatch.fnmatch(f, p)]
                except Exception: pass
            files.extend(matched)
        
        files = sorted([f for f in set(files) if os.path.isfile(f)])
        
        if not files:
            print(f"\n[ERROR] No files found matching the pattern(s): {patterns}")
            sys.exit(1)

        compatible_files = []
        for f in files:
            tracks = get_subtitle_tracks(f)
            if tracks:
                compatible_files.append(f)

        if not compatible_files:
            print("\n[INFO] No compatible subtitle tracks (PGS/VobSub) found in matched files.")
            sys.exit(0)

        print(f"\n[INFO] Found {len(compatible_files)} compatible file(s) to process.")
        for f in compatible_files:
            process_file(f, args)
            
    except KeyboardInterrupt:
        print("\n\n" + "!"*30)
        print(" [!] Process Cancelled by User (Ctrl+C)")
        print("!"*30)
        sys.exit(0)

if __name__ == "__main__":
    main()
