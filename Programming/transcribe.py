
"""
transcribe_ultimate_v2.py
-------------------------
Production-Grade Transcription with:
1. Robust Audio Validation (Switched to PyAV for 100% detection accuracy)
2. Modern Model Support (Turbo, Distil)
3. Auto-Fallback & Crash Recovery
4. Netflix-Style Phrase Grouping
"""

import sys
import os
import argparse
import re
import glob
import torch
import torchaudio
import torchaudio.transforms as T
import av  # PyAV - Much more robust than torchaudio for checking streams
from faster_whisper import WhisperModel
import gc
import shutil
import yt_dlp
import subprocess

# --- Configuration ---
MODEL_ALIASES = {
    "default": "deepdml/faster-whisper-large-v3-turbo-ct2",
    "turbo": "deepdml/faster-whisper-large-v3-turbo-ct2",
    "large-v3": "large-v3",
    "large-v2": "large-v2",
    "distil": "Systran/faster-distil-whisper-large-v3",
    "medium": "medium",
    "small": "small"
}

DEFAULT_MODEL_KEY = "large-v3"
DEFAULT_TASK = "transcribe"
DEFAULT_MIN_SILENCE_DURATION_WT = 100 # ms
DEFAULT_MAX_WORD_DURATION = 750       # ms

SUPPORTED_EXTENSIONS = {".wav", ".mp3", ".flac", ".m4a", ".aac", ".ogg", ".wma", ".mp4", ".mkv", ".mov", ".avi", ".wmv", ".m4v", ".webm"}

# Global State
transcription_model = None
current_model_path = None
vad_model = None
vad_utils = None

def is_media_file(filepath: str) -> bool:
    return os.path.splitext(filepath)[1].lower() in SUPPORTED_EXTENSIONS

def is_text_file(filepath: str) -> bool:
    """Checks if a file is text (not binary) by inspecting the beginning."""
    try:
        with open(filepath, 'rb') as f:
            chunk = f.read(1024)
        return b'\x00' not in chunk
    except Exception:
        return False

def download_audio(url: str, output_dir: str = None) -> str:
    print(f"⬇️  Downloading audio from: {url}")
    target_dir = output_dir if output_dir else os.getcwd()
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': os.path.join(target_dir, '%(channel)s - %(upload_date)s - %(title)s [%(id)s].%(ext)s'),
        'noplaylist': True,
        'quiet': False,     # Enable output for debugging
        'no_warnings': False,
        # Fix for 403 Forbidden: Impersonate Android client
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web'],
            }
        },
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            final_filename = os.path.splitext(filename)[0] + ".mp3"
            print(f"   ✅ Downloaded: {final_filename}")
            return final_filename
    except Exception as e:
        print(f"   ❌ Download failed: {e}")
        return None

def collect_input_files(paths_or_patterns):
    files = set()
    urls = set()
    
    if not paths_or_patterns:
        print("🔍 Scanning current directory for media files...")
        for ext in SUPPORTED_EXTENSIONS:
            for path in glob.glob(f"**/*{ext}", recursive=True):
                if os.path.isfile(path):
                    files.add(os.path.abspath(path))
    else:
        for pattern in paths_or_patterns:
            # 1. Direct URL (valid for any yt-dlp supported site)
            if pattern.startswith("http://") or pattern.startswith("https://"):
                urls.add(pattern)
                continue
                
            # 2. Files via Glob or Direct Path
            expanded = glob.glob(pattern, recursive=True)
            candidate_paths = expanded if expanded else ([pattern] if os.path.exists(pattern) else [])
            
            for path in candidate_paths:
                path = os.path.abspath(path)
                if os.path.isfile(path):
                    if is_media_file(path):
                        files.add(path)
                    elif is_text_file(path):
                        # Batch Mode: Read URLs from text file
                        print(f"📄 Reading batch list: {os.path.basename(path)}")
                        try:
                            with open(path, 'r', encoding='utf-8') as f:
                                for line in f:
                                    line = line.strip()
                                    if line and (line.startswith("http://") or line.startswith("https://")):
                                        urls.add(line)
                        except Exception as e:
                            print(f"   ⚠️  Could not read list file {path}: {e}")

    files = sorted(list(files))
    urls = sorted(list(urls))
    
    all_items = urls + files
    
    if not all_items:
        print("⚠️ No supported media files or URLs found.")
    else:
        print(f"✅ Found {len(all_items)} item(s) to process ({len(urls)} URLs, {len(files)} files).")
    return all_items

def format_srt_time(seconds: float) -> str:
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = int((seconds - int(seconds)) * 1000)
    return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02},{milliseconds:03}"

# --- Validation Logic (UPDATED) ---
def has_valid_audio_track(file_path: str) -> bool:
    """
    Checks if the file has an audio stream using PyAV (ffmpeg wrapper).
    This is extremely robust against different containers (MOV, MKV, MP4).
    """
    try:
        with av.open(file_path) as container:
            if len(container.streams.audio) > 0:
                return True
        return False
    except Exception as e:
        # If PyAV fails completely, the file might be corrupt, 
        # but let's return False to be safe and skip it.
        print(f"   ⚠️  Probe Error: {e}")
        return False

def preprocess_audio(input_path: str, output_dir: str = None) -> str:
    """
    Normalizes audio using FFmpeg's dynaudnorm filter to boost quiet parts (game audio) 
    relative to loud parts (commentary). Returns path to temporary WAV file.
    """
    try:
        print("   🔊 Enhancing audio levels (Dynamic Normalization)...")
        wd = output_dir if output_dir else os.path.dirname(input_path)
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        temp_wav = os.path.join(wd, f"{base_name}_enhanced.wav")
        
        # Audio Filter Chain:
        # 1. dynaudnorm: Dynamic Audio Normalizer (boosts quiet sections)
        #    f=200: Frame len 200ms
        #    g=5:  Small Gaussian window (5) for fast gain adaptation
        #    m=40: Max gain 40 (allow 40x boost for very quiet parts)
        # 2. aresample: Resample to 16k
        # 3. ac 1: Mix to mono (average)
        cmd = [
            "ffmpeg", "-y", "-v", "error",
            "-i", input_path,
            "-map", "0:a:0", # Map First Audio Track
            "-af", "dynaudnorm=f=200:g=5:m=40:p=0.95",
            "-ar", "16000",
            "-ac", "1",
            temp_wav
        ]
        
        subprocess.run(cmd, check=True)
        return temp_wav
    except subprocess.CalledProcessError as e:
        print(f"   ⚠️  Audio Enhancement Failed: {e}")
        return None
    except FileNotFoundError:
        print("   ⚠️  FFmpeg not found. Skipping enhancement.")
        return None

def isolate_audio_with_demucs(input_path: str, output_dir: str = None) -> str:
    """
    Uses Demucs to separate vocals from background noise/music.
    Returns path to the isolated 'vocals.wav'.
    """
    try:
        print("   🎸 Isolating vocals with Demucs...")
        wd = output_dir if output_dir else os.path.dirname(input_path)
        
        # Output structure: {wd}/htdemucs/{filename_no_ext}/vocals.wav
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        expected_output = os.path.join(wd, "htdemucs", base_name, "vocals.wav")
        
        # Demucs command (Ultimate Quality Settings):
        # --two-stems=vocals: Only separate vocals vs others
        # -n htdemucs_ft: Use Fine-Tuned Hybrid Transformer model
        # --shifts 10: Multi-pass prediction for better quality
        # --overlap 0.5: Healthier segment transitions
        # --float32: Preserve bit-depth fidelity
        cmd = [
            "demucs", "--two-stems=vocals", "-n", "htdemucs_ft",
            "--shifts", "10", "--overlap", "0.5", "--float32",
            "-o", wd, input_path
        ]
        
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        if os.path.exists(expected_output):
            # Move out of htdemucs/ folder to be in same dir as input
            final_isolated_wav = os.path.join(wd, f"{base_name}_isolated.wav")
            if os.path.exists(final_isolated_wav): os.remove(final_isolated_wav)
            os.rename(expected_output, final_isolated_wav)
            
            # Clean up the htdemucs folder immediately since we moved the file
            try: shutil.rmtree(os.path.join(wd, "htdemucs"))
            except: pass
            
            return final_isolated_wav
        else:
            print(f"   ⚠️  Demucs finished but output not found at: {expected_output}")
            return None
            
    except subprocess.CalledProcessError as e:
        print(f"   ⚠️  Demucs Failed: {e}")
        return None
    except FileNotFoundError:
        print("   ⚠️  Demucs not found (pip install demucs). Skipping isolation.")
        return None

# --- VAD (Silero) Functions ---
def load_vad_model():
    global vad_model, vad_utils
    if vad_model is None:
        print("🔌 Loading Silero VAD model...")
        try:
            vad_model, vad_utils = torch.hub.load(repo_or_dir='snakers4/silero-vad', model='silero_vad', trust_repo=True)
        except Exception as e:
            print(f"❌ Failed to load VAD model: {e}")
            return False
    return True

def detect_true_speech_regions(audio_path: str, threshold=0.45, min_silence_ms=120):
    global vad_model, vad_utils
    if not load_vad_model(): return []
    (get_speech_timestamps, _, _, _, _) = vad_utils

    try:
        file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
        if file_size_mb > 500:
            print(f"⚠️ File is large ({file_size_mb:.1f}MB). VAD might use high RAM.")

        wav, sr = torchaudio.load(audio_path)
        if sr != 16000:
            wav = T.Resample(sr, 16000)(wav)
        if wav.shape[0] > 1:
            wav = wav.mean(dim=0, keepdim=True)

        speech_timestamps = get_speech_timestamps(
            wav, vad_model, threshold=threshold, min_silence_duration_ms=min_silence_ms, window_size_samples=512
        )
        del wav
        gc.collect()

        merged = []
        for ts in speech_timestamps:
            start_s = ts['start'] / 16000
            end_s = ts['end'] / 16000
            if not merged:
                merged.append([start_s, end_s])
            else:
                if start_s - merged[-1][1] <= 0.2:
                    merged[-1][1] = end_s
                else:
                    merged.append([start_s, end_s])
        return merged
    except Exception as e:
        print(f"⚠️ VAD Error (Skipping True VAD): {e}")
        return []

def snap_to_vad(word_start, word_end, regions):
    for start, end in regions:
        if end < word_start - 0.2: continue 
        if start > word_end + 0.2: break 
        if (start - 0.15) <= word_start and word_end <= (end + 0.15):
            return max(word_start, start - 0.15), min(word_end, end + 0.15)
    return word_start, word_end

# --- Processing Logic ---
def post_process_word_timestamps(data: dict, max_duration_ms: int) -> dict:
    max_duration_s = max_duration_ms / 1000.0
    for segment in data.get('segments', []):
        for word in segment.get('words', []):
            start, end = word.get('start'), word.get('end')
            if start is not None and end is not None and (end - start) > max_duration_s:
                word['start'] = end - max_duration_s
    return data

def smart_line_break(text: str, max_chars: int):
    words = text.split()
    if not words: return [""]
    mid = len(words) // 2
    best_split = mid
    best_score = float('inf')
    
    start_s = max(1, len(words) // 3)
    end_s = min(len(words) - 1, (len(words) * 2) // 3)

    for i in range(start_s, end_s + 1):
        left = ' '.join(words[:i])
        right = ' '.join(words[i:])
        if len(left) > max_chars or len(right) > max_chars: continue
        score = abs(len(left) - len(right))
        if words[i-1].lower().endswith(','): score -= 10
        elif words[i-1] in {'and', 'but', 'or', 'so', 'because'}: score -= 5
        if score < best_score:
            best_score = score
            best_split = i
    return [' '.join(words[:best_split]), ' '.join(words[best_split:])]

def convert_data_to_srt(data: dict, srt_path: str, max_chars: int = 42):
    try:
        os.makedirs(os.path.dirname(srt_path), exist_ok=True)
        all_words = [
            (w['start'], w['end'], w['word'].strip())
            for seg in data.get('segments', [])
            for w in seg.get('words', [])
            if w.get('word', '').strip()
        ]
        
        if not all_words:
            print(f"⚠️  Silence detected. Creating placeholder SRT.")
            with open(srt_path, 'w', encoding='utf-8') as f:
                 f.write(f"1\n00:00:00,000 --> 00:00:05,000\n[No speech detected]\n\n")
            return True
        
        all_words.sort(key=lambda x: x[0])
        phrases = []
        current_phrase = []
        current_start = None
        
        for i, (start, end, word) in enumerate(all_words):
            if current_start is None: current_start = start
            current_phrase.append((start, end, word))
            current_end = end
            
            should_break = False
            if word.endswith(('.', '?', '!')): should_break = True
            elif i < len(all_words) - 1 and (all_words[i+1][0] - end) > 0.8: should_break = True
            if (sum(len(w[2]) for w in current_phrase) + len(current_phrase)) > max_chars * 1.5: should_break = True
            if (current_end - current_start) > 7.0: should_break = True
            
            if should_break:
                phrases.append({'start': current_start, 'end': current_end, 'words': [w[2] for w in current_phrase]})
                current_phrase = []
                current_start = None
        
        if current_phrase:
            phrases.append({'start': current_start, 'end': current_end, 'words': [w[2] for w in current_phrase]})

        with open(srt_path, 'w', encoding='utf-8') as f:
            idx = 1
            cap_next = True
            for p in phrases:
                text = ' '.join(p['words'])
                text = re.sub(r'\s+([.,!?])', r'\1', text)
                if cap_next: text = text[:1].upper() + text[1:]
                cap_next = text.strip().endswith(('.', '?', '!'))
                
                final_text = '\n'.join(smart_line_break(text, max_chars)) if len(text) > max_chars else text
                f.write(f"{idx}\n{format_srt_time(p['start'])} --> {format_srt_time(p['end'])}\n{final_text}\n\n")
                idx += 1
        return True
    except Exception as e:
        print(f"❌ Error writing SRT: {e}")
        return False

# --- Robust Model Manager ---
def ensure_model_loaded(model_alias):
    global transcription_model, current_model_path
    
    # Resolve alias to full path
    model_path = MODEL_ALIASES.get(model_alias, model_alias)
    
    if transcription_model is not None and current_model_path == model_path:
        return
        
    if transcription_model is not None:
        print(f"♻️  Switching models: Unloading '{current_model_path}'...")
        del transcription_model
        gc.collect()
        torch.cuda.empty_cache()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"🚀 Loading Whisper model '{model_path}' on {device}...")
    transcription_model = WhisperModel(model_path, device=device, compute_type="float16" if device == "cuda" else "int8")
    current_model_path = model_path

def run_transcription(file_path: str, args: argparse.Namespace) -> tuple[bool, str]:
    global transcription_model
    
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    final_srt_path = os.path.join(args.output_dir, f"{base_name}.srt") if args.output_dir else os.path.splitext(file_path)[0] + ".srt"

    print(f"🎤 Processing: {base_name}")

    # 1. Pre-Check Audio (Using PyAV)
    if not has_valid_audio_track(file_path):
        print(f"   🔇 WARNING: No audio track detected! Skipping.")
        return False, "Skipped (No Audio)"

        return False, "Skipped (No Audio)"

    # 1.5 Optional Preprocessing Chain
    # Order matters: Enhance/Normalize -> Isolate Vocals
    # Enhancing first helps Demucs detect quiet voices.
    
    transcription_source = file_path
    temp_files_to_cleanup = []

    # Step A: Enhancement (Normalization)
    if args.enhance:
        enhanced = preprocess_audio(transcription_source, args.output_dir)
        if enhanced and os.path.exists(enhanced):
            transcription_source = enhanced
            temp_files_to_cleanup.append(enhanced)

    # Step B: Isolation
    if args.isolate:
        isolated = isolate_audio_with_demucs(transcription_source, args.output_dir)
        if isolated and os.path.exists(isolated):
            transcription_source = isolated
            temp_files_to_cleanup.append(isolated)
            # Demucs creates a folder structure we might want to clean up later, 
            # but for now we just track the file.

    # 2. Transcribe with Fallbacks
    cleaned_data = None
    
    def try_transcribe(use_vad_filter):
        s, _ = transcription_model.transcribe(
            transcription_source, language=args.lang, task=args.task, vad_filter=use_vad_filter, 
            vad_parameters={"min_silence_duration_ms": DEFAULT_MIN_SILENCE_DURATION_WT}, word_timestamps=True
        )
        res = {"segments": []}
        for seg in s:
            res["segments"].append({
                "start": seg.start, "end": seg.end, "text": seg.text, 
                "words": [{"start": w.start, "end": w.end, "word": w.word} for w in seg.words] if seg.words else []
            })
        return res

    try:
        # Attempt 1: Requested Model + Internal VAD settings
        # If enhanced, DISABLE VAD to prevent suppression of normalized game dialog
        ensure_model_loaded(args.model)
        default_vad = False if args.enhance else True
        cleaned_data = try_transcribe(default_vad)
    except Exception as e:
        err = str(e).lower()
        if "tuple index" in err or "indexerror" in err:
            print("   ⚠️  Internal VAD bug detected. Retrying with VAD disabled...")
            try:
                # Attempt 2: Same Model + No VAD
                cleaned_data = try_transcribe(False)
            except Exception as e2:
                print(f"   ❌ Retry failed: {e2}")
        else:
            print(f"   ⚠️  Model Error: {e}")

    # Attempt 3: Fallback to Large-V2 if everything else failed
    if cleaned_data is None and args.model != "large-v2":
        print("   ⚠️  Switching to fallback model 'large-v2'...")
        try:
            ensure_model_loaded("large-v2")
            cleaned_data = try_transcribe(True)
        except Exception as e3:
            return False, f"All strategies failed: {e3}"

    if not cleaned_data: return False, "No data produced"

    # 3. Post-Process
    cleaned_data = post_process_word_timestamps(cleaned_data, DEFAULT_MAX_WORD_DURATION)

    # 4. True VAD Alignment (Silero)
    if args.use_vad:
        print("   🔍 Aligning with Silero VAD...")
        # Use the enhanced file for VAD if available, as it might help detection too
        vad_source = transcription_source 
        true_regions = detect_true_speech_regions(vad_source)
        if true_regions:
            c = 0
            for seg in cleaned_data["segments"]:
                for w in seg.get("words", []):
                    os_t, oe_t = w["start"], w["end"]
                    w["start"], w["end"] = snap_to_vad(w["start"], w["end"], true_regions)
                    if w["start"] != os_t or w["end"] != oe_t: c += 1
            print(f"      ↳ Aligned {c} words.")

    success = convert_data_to_srt(cleaned_data, final_srt_path)
    del cleaned_data
    gc.collect()

    # Cleanup temp files
    if not args.keep:
        for tmp in temp_files_to_cleanup:
            if os.path.exists(tmp):
                try:
                    os.remove(tmp)
                    print(f"   🧹 Removed temp file: {os.path.basename(tmp)}")
                except: pass
        # Cleanup Demucs folder (deprecated by move-rename but kept for safety)
        if args.isolate:
            # {output_dir}/htdemucs/{base_name}
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            wd = args.output_dir if args.output_dir else os.path.dirname(file_path)
            demucs_folder = os.path.join(wd, "htdemucs")
            if os.path.exists(demucs_folder):
                 try: shutil.rmtree(demucs_folder)
                 except: pass
    elif temp_files_to_cleanup:
        print(f"   💾 Keeping temp files (due to -k):")
        for tmp in temp_files_to_cleanup:
            print(f"      - {tmp}")
    
    return success, final_srt_path if success else "Write failed"

def main():
    parser = argparse.ArgumentParser(description="Whisper Transcription Ultimate")
    parser.add_argument("files", nargs="*", help="Files to process")
    parser.add_argument("-o", "--output_dir", type=str)
    parser.add_argument("-m", "--model", type=str, default=DEFAULT_MODEL_KEY, help=f"Model: {', '.join(MODEL_ALIASES.keys())}")
    parser.add_argument("-l", "--lang", type=str)
    parser.add_argument("--task", type=str, default=DEFAULT_TASK, choices=["transcribe", "translate"])

    parser.add_argument("--use_vad", action="store_true", help="Enable Silero VAD alignment")
    parser.add_argument("-e", "--enhance", action="store_true", default=True, help="Normalize audio levels (Default: ON)")
    parser.add_argument("-ne", "--no-enhance", action="store_false", dest="enhance", help="Disable audio normalization")
    parser.add_argument("-i", "--isolate", action="store_true", default=True, help="Use Demucs to isolate vocals (Default: ON)")
    parser.add_argument("-ni", "--no-isolate", action="store_false", dest="isolate", help="Disable vocal isolation")
    parser.add_argument("-k", "--keep", action="store_true", help="Keep downloaded audio files (default: delete)")

    args = parser.parse_args()
    files_to_process = collect_input_files(args.files)
    if not files_to_process: sys.exit(0)

    if args.output_dir: os.makedirs(args.output_dir, exist_ok=True)

    print(f"🚀 Processing {len(files_to_process)} files using model: {args.model}")
    
    success_count = 0
    fail_count = 0
    
    for i, fpath in enumerate(files_to_process, 1):
        print(f"\n[{i}/{len(files_to_process)}]", end=" ")
        try:
            is_url = fpath.startswith("http://") or fpath.startswith("https://")
            current_file = fpath
            temp_file_created = False
            
            if is_url:
                downloaded = download_audio(fpath, args.output_dir)
                if not downloaded:
                    fail_count += 1
                    continue
                current_file = downloaded
                temp_file_created = True

            ok, msg = run_transcription(current_file, args)
            
            if ok:
                print(f"✅ Saved: {os.path.basename(msg)}")
                success_count += 1
            elif "Skipped" in msg:
                print(f"⚠️  {msg}")
            else:
                print(f"❌ Failed: {msg}")
                fail_count += 1
            
            if temp_file_created and not args.keep:
                try:
                    os.remove(current_file)
                    print(f"   🗑️  Deleted temporary audio: {os.path.basename(current_file)}")
                except OSError as e:
                    print(f"   ⚠️  Failed to delete temp file: {e}")
                    
        except KeyboardInterrupt:
            print("\n🛑 Stopped by user.")
            break
        except Exception as e:
            print(f"❌ Critical Error: {e}")
            fail_count += 1
    
    print(f"\nDone. Success: {success_count}, Failed: {fail_count}")

if __name__ == "__main__":
    main()
