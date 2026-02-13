import sys
import os
import subprocess
import glob
import json
import struct
import io

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

from PIL import Image, ImageOps
import pytesseract
from tqdm import tqdm

# Optional EasyOCR Import
try:
    import easyocr
    import torch
    HAS_EASYOCR = True
    print("\n[INFO] EasyOCR module found. GPU acceleration enabled if available.")
except ImportError:
    HAS_EASYOCR = False
    print("\n[INFO] EasyOCR not found. Falling back to Tesseract (CPU).")


# ==========================================
# CONFIGURATION
# ==========================================

# Tesseract Configuration
TESSERACT_CONFIG = r'--psm 6'
LANG = 'eng'

# ==========================================
# CORE PGS PARSER & DECODER
# ==========================================

class BitReader:
    def __init__(self, data):
        self.data = data
        self.pos = 0

    def read_byte(self):
        if self.pos >= len(self.data):
            return 0
        b = self.data[self.pos]
        self.pos += 1
        return b

class PGSDecoder:
    def __init__(self, sup_file, mkv_timings=None):
        self.sup_file = sup_file
        self.palette = {} 
        self.captions = [] 
        self.mkv_timings = mkv_timings or {}

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
                        self._parse_pcs(payload, pts_secs)
                    elif seg_type == 0x80: # END
                        pass

        return self.captions

    def _parse_pds(self, data):
        pos = 2 
        while pos < len(data):
            idx = data[pos]
            y = data[pos+1]
            cr = data[pos+2]
            cb = data[pos+3]
            a = data[pos+4]
            r = y + 1.402 * (cr - 128)
            g = y - 0.34414 * (cb - 128) - 0.71414 * (cr - 128)
            b = y + 1.772 * (cb - 128)
            self.palette[idx] = (min(255, max(0, int(r))), min(255, max(0, int(g))), min(255, max(0, int(b))), a)
            pos += 5

    def _parse_ods(self, data):
        width = (data[7] << 8) | data[8]
        height = (data[9] << 8) | data[10]
        rle_data = data[11:]
        self.current_bitmap_idx = self._decode_rle(rle_data, width, height)
        self.current_width = width
        self.current_height = height

    def _decode_rle(self, data, width, height):
        pixels = []
        reader = BitReader(data)
        while len(pixels) < width * height:
            b = reader.read_byte()
            if b != 0:
                pixels.append(b)
            else:
                flags = reader.read_byte()
                if flags == 0: pass
                elif flags < 64: pixels.extend([0] * flags)
                elif flags & 0x40:
                    if flags & 0x80:
                        if flags & 0xC0 == 0xC0:
                            length = ((flags & 0x3F) << 8) | reader.read_byte()
                            color = reader.read_byte()
                            pixels.extend([color] * length)
                        else: pass
                    else:
                        length = ((flags & 0x3F) << 8) | reader.read_byte()
                        pixels.extend([0] * length)
                else:
                    length = flags & 0x3F
                    color = reader.read_byte()
                    pixels.extend([color] * length)
        return pixels

    def _parse_pcs(self, data, pts):
        # Parse PCS Header to detect Object Count
        # Structure:
        # Width (2), Height (2), FrameRate (1), Comp Num (2), State (1), Palette Flag (1), Palette ID (1), Obj Count (1)
        # Total header size before objects = 11 bytes
        if len(data) < 11:
            return

        # Manual extraction to avoid struct alignment confusion
        # We mainly care about obj_count at offset 10
        obj_count = data[10]

        if obj_count == 0:
            # This is a "Clear Screen" or empty state
            self.captions.append({'start': pts, 'type': 'clear'})
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
                # Check neighbors: pts, pts-0.001, pts+0.001
                pts_key = round(pts, 3)
                duration = self.mkv_timings.get(pts_key)
                
                # If exact match fails, try minimal fuzzy search
                if duration is None:
                    for offset in [-0.001, 0.001, -0.002, 0.002]:
                        duration = self.mkv_timings.get(round(pts + offset, 3))
                        if duration: break
                
                start = pts
                end = None
                if duration:
                    end = start + duration
                
                self.captions.append({'start': start, 'end': end, 'type': 'caption', 'image': img})
                # Clear the pending bitmap data
                del self.current_bitmap_idx

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
            # Suppress verbose output from easyocr init if possible, but standard is fine
            READER = easyocr.Reader([lang_code], gpu=True)
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
    return bg_black

def format_time(seconds):
    ms = int((seconds % 1) * 1000)
    s = int(seconds)
    m = s // 60
    h = m // 60
    s = s % 60
    m = m % 60
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def perform_ocr(captions):
    srt_lines = []
    counter = 1
    
    # Filter only actual caption events for the progress bar count
    caption_events = [c for c in captions if c.get('type') == 'caption']
    pbar = tqdm(total=len(caption_events), desc="[2/2] Running OCR", unit="frame")
    
    try:
        # We process the full list (including clears) to determine timing
        for i in range(len(captions)):
            item = captions[i]
            
            if item.get('type') != 'caption':
                continue
                
            start_time = item['start']
            
            # Find the end time
            # Priority 1: Use explicit usage from MKV packet (item['end'])
            # Priority 2: Use "Clear" event if available
            # Priority 3: Fallback heuristic
            
            end_time = item.get('end')
            
            if not end_time:
                 # Fallback logic
                end_time = start_time + 4 # Default fallback
                
                found_end = False
                for j in range(i + 1, len(captions)):
                    next_event = captions[j]
                    
                    if next_event.get('type') == 'clear':
                        end_time = next_event['start']
                        found_end = True
                        break
                    
                    if next_event.get('type') == 'caption':
                        end_time = next_event['start'] - 0.1
                        found_end = True
                        break
            
            # Sanity checks
            if end_time <= start_time: end_time = start_time + 1.0
            
            # Max duration cap (only if we didn't find an explicit clear, or even if we did? 
            # explicit clear should probably be trusted unless it's insane)
            if end_time - start_time > 10: 
                end_time = start_time + 10 # Cap at 10s just in case of missed clears
                
            text = ""
            reader = get_easyocr_reader()
            
            if reader:
                # --- EasyOCR Path ---
                import numpy as np
                # Use White-on-Black image for EasyOCR
                proc_img = preprocess_for_easyocr(item['image'])
                img_np = np.array(proc_img)
                
                try:
                    # detail=0 returns simple list of strings
                    # paragraph=True combines them into lines
                    results = reader.readtext(img_np, detail=0, paragraph=True)
                    text = " ".join(results)
                except Exception as e:
                    print(f"   [ERR] EasyOCR failed on frame: {e}")
                    text = ""
            else:
                # --- Tesseract Path ---
                proc_img = preprocess_image(item['image'])
                text = pytesseract.image_to_string(proc_img, lang=LANG, config=TESSERACT_CONFIG)
            
            # Common Cleanup
            text = text.strip().replace('|', 'I') 
            
            time_str = f"{format_time(start_time)} --> {format_time(end_time)}"
            clean_text = text.replace('\n', ' ')
            
            if text:
                tqdm.write(f"    [{time_str}] {clean_text}")
                
                srt_lines.append(f"{counter}")
                srt_lines.append(time_str)
                srt_lines.append(text)
                srt_lines.append("")
                counter += 1
            
            pbar.update(1)
    finally:
        pbar.close()
        
    return "\n".join(srt_lines)

# ==========================================
# MAIN PIPELINE
# ==========================================

def get_subtitle_tracks(mkv_path):
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
                'width': stream.get('width'),
                'height': stream.get('height')
            })
    return tracks

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

def get_mkv_timings(mkv_path, track_index):
    """
    Extracts packet timings (pts_time, duration_time) for a specific track.
    Returns a dictionary mapping start_time -> end_time (approx).
    Or better, a list of (start, end) tuples we can search.
    """
    print(f"   [SYNC] extraction packet timings from MKV (track {track_index})...")
    cmd = [
        "ffprobe", "-v", "error", 
        "-select_streams", f"{track_index}",
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

def render_vobsub_frame(mkv_path, sub_idx, start_time, width=720, height=480):
    # Small offset helps ensure we sample after subtitle start, not on the boundary.
    sample_time = max(0.0, start_time + 0.05)
    filter_graph = f"[0:v][1:s:{sub_idx}]overlay"
    cmd = [
        "ffmpeg", "-v", "error",
        "-f", "lavfi", "-i", f"color=black:s={width}x{height}:r=25:d=1",
        "-itsoffset", str(-sample_time), "-i", mkv_path,
        "-filter_complex", filter_graph,
        "-frames:v", "1",
        "-f", "image2pipe", "-vcodec", "png", "-"
    ]
    try:
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0 or not result.stdout:
            return None
        return Image.open(io.BytesIO(result.stdout)).convert('RGBA')
    except Exception:
        return None

def decode_vobsub_captions(mkv_path, track):
    print(f"   [VOBSUB] Rendering subtitle bitmaps from stream {track['index']}...")
    width = int(track.get('width') or 720)
    height = int(track.get('height') or 480)
    packet_entries = get_mkv_packet_entries(mkv_path, f"s:{track['sub_idx']}")
    if not packet_entries:
        print("   [VOBSUB] No packet timings found for this stream.")
        return []

    captions = []
    with tqdm(total=len(packet_entries), desc="[1/2] Decoding VobSub Stream", unit="pkt") as pbar:
        for item in packet_entries:
            start = item['start']
            duration = item.get('duration')
            end = start + duration if duration else None
            img = render_vobsub_frame(mkv_path, track['sub_idx'], start, width, height)
            if img:
                captions.append({'start': start, 'end': end, 'type': 'caption', 'image': img})
            pbar.update(1)
    return captions

def extract_sup(mkv_path, track_index, output_sup):
    cmd = [
        "ffmpeg", "-y", "-i", mkv_path,
        "-map", f"0:{track_index}",
        "-c", "copy", output_sup
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def process_file(mkv_path):
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
        
        try:
            if codec == "hdmv_pgs_subtitle":
                # 1. Extract
                print("   Extracting stream using ffmpeg (please wait)...")
                extract_sup(mkv_path, idx, temp_sup)
                
                if os.path.exists(temp_sup):
                    size_mb = os.path.getsize(temp_sup) / (1024 * 1024)
                    print(f"   Stream extracted successfully: {size_mb:.2f} MB")
                else:
                    print("   Error: Extraction failed.")
                    continue
                
                # 2. Extract MKV Timings (Container Truth)
                packet_timings = get_mkv_timings(mkv_path, idx)

                # 3. Parse & Decode
                decoder = PGSDecoder(temp_sup, mkv_timings=packet_timings)
                captions = decoder.parse()
            else:
                captions = decode_vobsub_captions(mkv_path, track)
            
            print(f"   Decoded {len(captions)} unique caption images.")
            
            # 3. OCR & Write
            if captions:
                srt_content = perform_ocr(captions)
                with open(output_srt, 'w', encoding='utf-8') as f:
                    f.write(srt_content)
                print(f"\n   SUCCESS! Saved: {output_srt}")
            else:
                print("   Warning: No captions decoded.")
                
        except KeyboardInterrupt:
            raise # Pass it up to main
        except Exception as e:
            print(f"   Error processing track {idx}: {e}")
        finally:
            # Always clean up the temp file for this track
            if os.path.exists(temp_sup):
                try:
                    os.remove(temp_sup)
                except:
                    pass

def main():
    try:
        # If no args are provided, scan common video containers in CWD.
        if len(sys.argv) < 2:
            patterns = ["*.mkv", "*.mp4", "*.m4v", "*.mov", "*.avi", "*.ts", "*.m2ts", "*.webm"]
            print("[INFO] No pattern provided. Scanning current directory for compatible files...")
        else:
            # Get all arguments after the script name
            # On some Windows shells, non-breaking spaces or weird characters might be present
            patterns = sys.argv[1:]
        files = []
        
        cwd = os.getcwd()
        
        for p in patterns:
            # Clean up the pattern (remove leading/trailing whitespace which can happen in some shells)
            p = p.strip()
            if not p:
                continue
                
            matched = glob.glob(p)
            
            # If glob fails, but the pattern is just '*' or '*.extension', 
            # let's try a more manual approach as a fallback.
            if not matched and ('*' in p or '?' in p):
                import fnmatch
                try:
                    all_files = os.listdir('.')
                    matched = [f for f in all_files if fnmatch.fnmatch(f, p)]
                except Exception:
                    pass
                    
            files.extend(matched)
        
        # Remove duplicates, keep files only, and sort
        files = sorted([f for f in set(files) if os.path.isfile(f)])
        
        if not files:
            print(f"\n[ERROR] No files found matching the pattern(s): {patterns}")
            print(f"Current Directory: {cwd}")
            print(f"Files in directory: {os.listdir(cwd)[:10]} ... (total {len(os.listdir(cwd))} files)")
            sys.exit(1)

        # Keep only files that actually contain supported image subtitle tracks.
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
            process_file(f)
            
    except KeyboardInterrupt:
        print("\n\n" + "!"*30)
        print(" [!] Process Cancelled by User (Ctrl+C)")
        print("!"*30)
        sys.exit(0)

if __name__ == "__main__":
    main()
