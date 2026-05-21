"""
transcribe_ultimate_v5.py
-------------------------
Production-Grade Transcription Pipeline
(Defaulted to Large-V2 for Maximum Stability)

Changelog v5:
- Changed Default Model to 'large-v2' per user request.
- Retains Smart Compute Type & Error Handling from v4.

Dependencies:
  pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118
  pip install faster-whisper yt-dlp tqdm av demucs silero-vad
  pip install nvidia-cublas-cu12 nvidia-cudnn-cu12
"""

import sys
import os
import argparse
import glob
import urllib.parse
import torch
import gc
import shutil
import yt_dlp
import subprocess
from tqdm import tqdm
import warnings
import numpy as np
import av  # PyAV
import re
import traceback
from datetime import datetime
from collections import Counter
import contextlib
import io
import threading
import time

# Suppress warnings
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

# --- DLL Injection for Windows ---
if sys.platform == "win32":
    import site
    packages_dirs = site.getsitepackages()
    if site.ENABLE_USER_SITE:
        packages_dirs.append(site.getusersitepackages())

    try:
        torch_lib_path = os.path.join(os.path.dirname(torch.__file__), "lib")
        if os.path.exists(torch_lib_path):
            os.add_dll_directory(torch_lib_path)
            if torch_lib_path not in os.environ['PATH']:
                os.environ['PATH'] = torch_lib_path + os.pathsep + os.environ['PATH']
    except Exception: pass

    for base in set(packages_dirs):
        if not base or not os.path.exists(base): continue
        nvidia_path = os.path.join(base, "nvidia")
        if os.path.exists(nvidia_path):
            for subfolder in os.listdir(nvidia_path):
                bin_path = os.path.join(nvidia_path, subfolder, "bin")
                if os.path.exists(bin_path):
                    try:
                        os.add_dll_directory(bin_path)
                        if bin_path not in os.environ['PATH']:
                            os.environ['PATH'] = bin_path + os.pathsep + os.environ['PATH']
                    except Exception: pass

from faster_whisper import WhisperModel

# --- Configuration ---
MODEL_ALIASES = {
    "default": "large-v2",  # CHANGED: Default is now stable large-v2
    "large-v2": "large-v2",
    "large-v3": "large-v3",
    "turbo": "deepdml/faster-whisper-large-v3-turbo-ct2",
    "distil": "Systran/faster-distil-whisper-large-v3",
    "medium": "medium",
    "small": "small",
    "qwen3-asr-0.6b": "Qwen/Qwen3-ASR-0.6B",
    "qwen3-asr-1.7b": "Qwen/Qwen3-ASR-1.7B"
}

DEFAULT_MODEL_KEY = "large-v2" # CHANGED
DEFAULT_TASK = "transcribe"
DEFAULT_VAD_THRESHOLD = 0.3
DEFAULT_VAD_MIN_SILENCE_MS = 300
DEFAULT_WHISPER_VAD_THRESHOLD = 0.2
DEFAULT_WHISPER_VAD_MIN_SILENCE_MS = 500
DEFAULT_MIN_SUB_DURATION = 0.7
DEFAULT_MAX_REPEAT_RUN = 8
DEFAULT_PHRASE_PAUSE_SPLIT_S = 0.65

# Global State
transcription_model = None
current_model_path = None
current_model_backend = None
current_qwen_aligner = None
PREFERRED_COMPUTE_TYPE = "auto" 

vad_model = None
vad_utils = None
_ydl_pbar = None
CURRENT_LOG_FILE = None

SUPPORTED_EXTENSIONS = {".wav", ".mp3", ".flac", ".m4a", ".aac", ".ogg", ".wma", ".mp4", ".mkv", ".mov", ".avi", ".wmv", ".m4v", ".webm"}

class PipelineAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if not hasattr(namespace, 'pipeline'):
            setattr(namespace, 'pipeline', [])
        if self.const is True:
            setattr(namespace, self.dest, True)
            if self.dest not in namespace.pipeline:
                namespace.pipeline.append(self.dest)
        elif self.const is False:
            setattr(namespace, self.dest, False)
            if self.dest in namespace.pipeline:
                namespace.pipeline.remove(self.dest)

def is_media_file(filepath: str) -> bool:
    return os.path.splitext(filepath)[1].lower() in SUPPORTED_EXTENSIONS

def is_text_file(filepath: str) -> bool:
    try:
        with open(filepath, 'rb') as f:
            chunk = f.read(1024)
        return b'\x00' not in chunk
    except Exception:
        return False

def clean_url(url: str) -> str:
    try:
        parsed = urllib.parse.urlparse(url)
        domain = parsed.netloc.lower()
        if "youtube.com" in domain or "m.youtube.com" in domain:
            query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
            allowed = {'v', 't', 'list', 'index'}
            new_query = {k: v for k, v in query.items() if k in allowed}
            return parsed._replace(query=urllib.parse.urlencode(new_query, doseq=True)).geturl()
        elif "youtu.be" in domain:
            return url.split('?')[0]
        return url
    except Exception:
        return url

def set_log_file(path: str):
    global CURRENT_LOG_FILE
    CURRENT_LOG_FILE = path

def log_event(message: str):
    if not CURRENT_LOG_FILE:
        return
    try:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        with open(CURRENT_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {message}\n")
    except Exception:
        pass

def resolve_model_backend(model_path: str) -> str:
    if isinstance(model_path, str) and model_path.lower().startswith("qwen/"):
        return "qwen"
    return "whisper"

# --- yt-dlp Integration ---
class YdlTqdmLogger:
    def debug(self, msg): pass
    def info(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): print(f"   ❌ {msg}")

def ydl_progress_hook(d):
    global _ydl_pbar
    if d['status'] == 'downloading':
        total = d.get('total_bytes') or d.get('total_bytes_estimate')
        downloaded = d.get('downloaded_bytes', 0)
        if total:
            if _ydl_pbar is None:
                _ydl_pbar = tqdm(total=total, unit='B', unit_scale=True, desc="   Downloading", leave=False, dynamic_ncols=True)
            _ydl_pbar.n = downloaded
            _ydl_pbar.refresh()
    elif d['status'] == 'finished':
        if _ydl_pbar is not None:
            _ydl_pbar.close()
            _ydl_pbar = None

def download_audio(url: str, output_dir: str = None) -> str:
    print(f"⬇️  Downloading audio from: {url}")
    log_event(f"download_audio start url={url}")
    target_dir = output_dir if output_dir else os.getcwd()
    global _ydl_pbar
    _ydl_pbar = None
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '192'}],
        'outtmpl': os.path.join(target_dir, '%(title)s [%(id)s].%(ext)s'),
        'noplaylist': True, 'quiet': True, 'no_warnings': True,
        'logger': YdlTqdmLogger(), 'progress_hooks': [ydl_progress_hook],
        'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            vid_id = info.get('id', '')
            possible_files = glob.glob(os.path.join(target_dir, f"*{vid_id}*.mp3"))
            if possible_files:
                final_filename = max(possible_files, key=os.path.getmtime)
                print(f"   ✅ Downloaded: {os.path.basename(final_filename)}")
                log_event(f"download_audio success file={final_filename}")
                return final_filename
            else:
                print(f"   ⚠️ Download reported success but file not found.")
                log_event("download_audio warning success reported but file not found")
                return None
    except Exception as e:
        print(f"   ❌ Download failed: {e}")
        log_event(f"download_audio error={e}\n{traceback.format_exc()}")
        return None

def collect_input_files(paths_or_patterns):
    files = set()
    urls = set()
    if not paths_or_patterns:
        print("🔍 Scanning current directory for media files...")
        for ext in SUPPORTED_EXTENSIONS:
            for path in glob.glob(f"**/*{ext}", recursive=True):
                files.add(os.path.abspath(path))
    else:
        for pattern in paths_or_patterns:
            if pattern.startswith("http://") or pattern.startswith("https://"):
                urls.add(clean_url(pattern))
                continue
            expanded = glob.glob(pattern, recursive=True)
            candidate_paths = expanded if expanded else ([pattern] if os.path.exists(pattern) else [])
            for path in candidate_paths:
                path = os.path.abspath(path)
                if os.path.isfile(path):
                    if is_media_file(path): files.add(path)
                    elif path.lower().endswith(('.txt', '.lst')) and is_text_file(path):
                        try:
                            with open(path, 'r', encoding='utf-8') as f:
                                for line in f:
                                    if line.strip().startswith("http"): urls.add(clean_url(line.strip()))
                        except Exception: pass
    all_items = sorted(list(urls)) + sorted(list(files))
    if not all_items: print("⚠️ No supported media files or URLs found.")
    return all_items

def format_srt_time(seconds: float) -> str:
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = min(int((seconds - int(seconds)) * 1000), 999)
    return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02},{milliseconds:03}"

def get_audio_duration_seconds(file_path: str) -> float:
    try:
        with av.open(file_path) as container:
            if container.duration:
                return float(container.duration / av.time_base)
            if container.streams.audio and container.streams.audio[0].duration and container.streams.audio[0].time_base:
                stream = container.streams.audio[0]
                return float(stream.duration * stream.time_base)
    except Exception:
        pass
    return 0.0

# --- Validation & Processing ---
def has_valid_audio_track(file_path: str) -> bool:
    try:
        with av.open(file_path) as container:
            if len(container.streams.audio) > 0: return True
        return False
    except Exception: return False

def extract_audio_to_wav(input_path: str, output_dir: str = None) -> str:
    try:
        wd = output_dir if output_dir else os.path.dirname(input_path)
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        temp_wav = os.path.join(wd, f"{base_name}_base.wav")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", input_path, "-map", "0:a:0", "-ar", "16000", "-ac", "1", temp_wav], check=True)
        log_event(f"extract_audio_to_wav success input={input_path} output={temp_wav}")
        return temp_wav
    except Exception as e:
        print(f"   ⚠️ Audio extraction failed: {e}")
        log_event(f"extract_audio_to_wav error input={input_path} error={e}\n{traceback.format_exc()}")
        return None

def get_audio_duration_seconds(file_path: str) -> float:
    try:
        with av.open(file_path) as container:
            if container.duration is not None:
                return float(container.duration / 1_000_000.0)
            if container.streams.audio and container.streams.audio[0].duration is not None:
                s = container.streams.audio[0]
                return float(s.duration * s.time_base)
    except Exception:
        pass
    return 0.0

def extract_audio_chunk_to_wav(input_path: str, start_s: float, duration_s: float, output_path: str) -> bool:
    try:
        subprocess.run([
            "ffmpeg", "-y", "-v", "error",
            "-ss", f"{start_s:.3f}",
            "-t", f"{duration_s:.3f}",
            "-i", input_path,
            "-ar", "16000", "-ac", "1",
            output_path
        ], check=True)
        return os.path.exists(output_path)
    except Exception as e:
        log_event(f"extract_audio_chunk_to_wav error start={start_s} dur={duration_s} err={e}")
        return False

def isolate_audio_with_demucs(input_path: str, output_dir: str = None, model="htdemucs_ft", shifts=2) -> str:
    try:
        print(f"   🎸 Isolating vocals with Demucs ({model})...")
        wd = output_dir if output_dir else os.path.dirname(input_path)
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        cmd = [sys.executable, "-m", "demucs", "--two-stems=vocals", "-n", model, "-d", "cuda" if torch.cuda.is_available() else "cpu", "--shifts", str(shifts), "--overlap", "0.25", "--float32", "-o", wd, input_path]
        subprocess.run(cmd, check=True)
        expected_output = os.path.join(wd, model, base_name, "vocals.wav")
        final_wav = os.path.join(wd, f"{base_name}_isolated.wav")
        if os.path.exists(expected_output):
            if os.path.exists(final_wav): os.remove(final_wav)
            os.rename(expected_output, final_wav)
            try: shutil.rmtree(os.path.join(wd, model, base_name))
            except Exception: pass
            try: os.rmdir(os.path.join(wd, model))
            except Exception: pass
            gc.collect()
            log_event(f"isolate_audio_with_demucs success input={input_path} output={final_wav} model={model} shifts={shifts}")
            return final_wav
        return None
    except Exception as e:
        print(f"   ⚠️ Demucs Failed: {e}")
        log_event(f"isolate_audio_with_demucs error input={input_path} error={e}\n{traceback.format_exc()}")
        return None

def preprocess_audio(input_path: str, output_dir: str = None) -> str:
    try:
        print(f"   🔊 Enhancing audio (DynAudNorm)...")
        wd = output_dir if output_dir else os.path.dirname(input_path)
        temp_wav = os.path.join(wd, f"{os.path.splitext(os.path.basename(input_path))[0]}_enhanced.wav")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", input_path, "-af", "dynaudnorm=f=200:g=5:m=40:p=0.95", "-ar", "16000", "-ac", "1", temp_wav], check=True)
        log_event(f"preprocess_audio success input={input_path} output={temp_wav}")
        return temp_wav
    except Exception as e:
        print(f"   ⚠️ Enhancement Failed: {e}")
        log_event(f"preprocess_audio error input={input_path} error={e}\n{traceback.format_exc()}")
        return None

def apply_compression_limiter(input_path: str, output_dir: str = None, **kwargs) -> str:
    try:
        print(f"   🔊 Applying Compression/Limiter...")
        wd = output_dir if output_dir else os.path.dirname(input_path)
        temp_wav = os.path.join(wd, f"{os.path.splitext(os.path.basename(input_path))[0]}_cl.wav")
        filters = [f"acompressor=threshold={kwargs.get('threshold', 0.125)}:ratio={kwargs.get('ratio', 2.0)}:attack=20:release=250:makeup=1", "alimiter=level_in=1:level_out=1:limit=0.99:attack=5:release=50:asc=0:level=1"]
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", input_path, "-af", ",".join(filters), "-ar", "16000", "-ac", "1", temp_wav], check=True)
        log_event(f"apply_compression_limiter success input={input_path} output={temp_wav} threshold={kwargs.get('threshold', 0.125)} ratio={kwargs.get('ratio', 2.0)}")
        return temp_wav
    except Exception as e:
        print(f"   ⚠️ Compression Failed: {e}")
        log_event(f"apply_compression_limiter error input={input_path} error={e}\n{traceback.format_exc()}")
        return None

# --- VAD ---
def load_vad_model():
    global vad_model, vad_utils
    if vad_model is None:
        try:
            vad_model, vad_utils = torch.hub.load(repo_or_dir='snakers4/silero-vad', model='silero_vad', trust_repo=True)
        except Exception: return False
    return True

def detect_true_speech_regions(audio_path: str, threshold=DEFAULT_VAD_THRESHOLD, min_silence_duration_ms=100):
    global vad_model, vad_utils
    if not load_vad_model(): return []
    (get_speech_timestamps, _, _, _, _) = vad_utils
    try:
        with av.open(audio_path) as container:
            audio_stream = container.streams.audio[0]
            resampler = av.AudioResampler(format='fltp', layout='mono', rate=16000)
            frames = []
            for frame in container.decode(audio_stream):
                frame.pts = None
                for rf in resampler.resample(frame):
                    frames.append(rf.to_ndarray())
        if not frames: return []
        wav_np = np.concatenate(frames, axis=1)
        wav = torch.from_numpy(wav_np)
        if wav.dim() > 1 and wav.shape[0] == 1: wav = wav.squeeze(0)
        if wav.dim() == 0: return []
        timestamps = get_speech_timestamps(
            wav,
            vad_model,
            threshold=threshold,
            min_silence_duration_ms=min_silence_duration_ms
        )
        del wav
        merged = []
        for ts in timestamps:
            start, end = ts['start'] / 16000, ts['end'] / 16000
            if merged and (start - merged[-1][1] <= 0.2): merged[-1][1] = end
            else: merged.append([start, end])
        log_event(f"silero_vad regions={len(merged)} threshold={threshold} min_silence_ms={min_silence_duration_ms} audio={audio_path}")
        return merged
    except Exception as e:
        print(f"   ⚠️ VAD Error: {e}")
        log_event(f"silero_vad error audio={audio_path} error={e}\n{traceback.format_exc()}")
        return []

def snap_to_vad(word_start, word_end, regions):
    # Whisper typically stretches the *start* of the word backwards into preceding silence.
    # Because of this, a single word might incorrectly overlap multiple early static/noise regions.
    # By searching the speech regions in reverse, we lock onto the chunk where the word
    # actually ends (which is when it was actually spoken), ignoring any earlier noise chunks.
    for start, end in reversed(regions):
        if max(word_start, start) < min(word_end, end):
            return max(word_start - 0.1, start), min(word_end + 0.1, end)
            
    # Fallback to proximity checking
    for start, end in reversed(regions):
        if abs(word_start - end) < 0.2: return word_start, word_end 
        if abs(word_end - start) < 0.2: return word_start, word_end
        
    return word_start, word_end

# --- Processing Logic ---
def ensure_model_loaded(model_alias):
    global transcription_model, current_model_path, current_model_backend, current_qwen_aligner, PREFERRED_COMPUTE_TYPE
    model_path = MODEL_ALIASES.get(model_alias, model_alias)
    backend = resolve_model_backend(model_path)
    qwen_aligner = os.environ.get("QWEN_ASR_ALIGNER", "").strip() if backend == "qwen" else None
    
    # Don't reload if already loaded
    if (
        transcription_model is not None
        and current_model_path == model_path
        and current_model_backend == backend
        and (backend != "qwen" or current_qwen_aligner == qwen_aligner)
    ):
        return

    if transcription_model is not None:
        transcription_model = None
        current_qwen_aligner = None
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    # Determine Compute Type
    if PREFERRED_COMPUTE_TYPE == "auto":
        compute_type = "float16" if device == "cuda" else "int8"
    else:
        compute_type = PREFERRED_COMPUTE_TYPE

    if backend == "whisper":
        print(f"🚀 Loading Whisper model '{model_path}' on {device} ({compute_type})...")
        log_event(f"ensure_model_loaded backend=whisper path={model_path} device={device} compute_type={compute_type}")
        
        try:
            transcription_model = WhisperModel(model_path, device=device, compute_type=compute_type)
            current_model_path = model_path
            current_model_backend = backend
        except Exception as e:
            err_str = str(e).lower()
            
            # 1. Catch Brotli/Download Corruption specifically
            if "brotli" in err_str or "end of file" in err_str or "invalid header" in err_str:
                print("\n❌ CRITICAL ERROR: Model file is corrupted.")
                print(f"   Please delete the HuggingFace cache folder for: {model_path}")
                print(f"   Path: {os.path.join(os.path.expanduser('~'), '.cache', 'huggingface', 'hub')}")
                sys.exit(1)

            # 2. Handle Compute Type mismatch (Float16 not supported)
            if "compute type" in err_str or "cublas" in err_str:
                if compute_type == "float16":
                    print("   ⚠️  Float16 failed, switching to int8 globally...")
                    PREFERRED_COMPUTE_TYPE = "int8" # Remember this decision
                    try:
                        transcription_model = WhisperModel(model_path, device=device, compute_type="int8")
                        current_model_path = model_path
                        current_model_backend = backend
                        return
                    except Exception as inner_e:
                        # If int8 also fails, check for corruption again
                        if "brotli" in str(inner_e).lower():
                            print("\n❌ CRITICAL ERROR: Model file is corrupted (detected during int8 fallback).")
                            print(f"   Please delete the HuggingFace cache folder for: {model_path}")
                            sys.exit(1)
                        raise inner_e # Real error
            raise e
    else:
        print(f"🚀 Loading Qwen3-ASR model '{model_path}' on {device}...")
        log_event(f"ensure_model_loaded backend=qwen path={model_path} device={device} aligner={qwen_aligner}")
        if not qwen_aligner:
            raise RuntimeError(
                "Qwen mode requires forced aligner at model initialization. "
                "Set env var QWEN_ASR_ALIGNER (example: Qwen/Qwen3-ASR-Aligner)."
            )
        try:
            from qwen_asr import Qwen3ASRModel
        except Exception as e:
            raise RuntimeError(
                "Qwen backend selected but qwen-asr is not installed. "
                "Install with: pip install qwen-asr"
            ) from e
        try:
            # qwen-asr handles device/dtype internally.
            transcription_model = Qwen3ASRModel.from_pretrained(model_path, forced_aligner=qwen_aligner)
            current_model_path = model_path
            current_model_backend = backend
            current_qwen_aligner = qwen_aligner
        except Exception as e:
            raise RuntimeError(f"Failed to load Qwen model '{model_path}': {e}") from e

def resegment_by_phrase(data: dict, pause_split_s: float = DEFAULT_PHRASE_PAUSE_SPLIT_S) -> dict:
    """Re-segment transcription data so each SRT entry contains one complete phrase/sentence.
    Uses word-level timestamps to split on punctuation and natural speech pauses."""
    
    # Heuristic Fix for Whisper Attention Stretching:
    # Whisper often stretches the *start* of the very first word in a segment 
    # backwards across any preceding background noise or silence. 
    # We heuristically clamp any single word to a maximum of 1.0 second.
    MAX_WORD_DURATION = 1.0
    for seg in data.get('segments', []):
        for w in seg.get('words', []):
            if w['end'] - w['start'] > MAX_WORD_DURATION:
                w['start'] = max(w['start'], w['end'] - MAX_WORD_DURATION)

    # Flatten all words from all segments
    all_words = []
    for seg in data.get('segments', []):
        for w in seg.get('words', []):
            if w.get('word', '').strip():
                all_words.append(w)

    if not all_words:
        # Some segments can come back without word timestamps.
        # Preserve original segment text instead of returning an empty SRT.
        fallback_segments = []
        for seg in data.get('segments', []):
            text = (seg.get('text') or '').strip()
            if not text:
                continue
            start = seg.get('start', 0.0)
            end = seg.get('end', start)
            fallback_segments.append({
                'start': start,
                'end': end,
                'text': text,
                'words': seg.get('words', [])
            })
        return {'segments': fallback_segments}

    # Punctuation that marks phrase/clause boundaries
    phrase_end_chars = {'.', ',', '!', '?', ';', ':'}

    new_segments = []
    current_words = []

    def process_and_add_phrase(words_list):
        if not words_list: return
        
        # 2. Heuristic Fix for DTW rogue alignment gaps:
        # If Whisper aligned a word to early background noise, there will be a massive 
        # time gap between that word and the rest of the sentence. We sweep these 
        # rogue early words forward to rest naturally right before the real speech.
        for i in range(len(words_list) - 2, -1, -1):
            w_curr = words_list[i]
            w_next = words_list[i+1]
            if w_next['start'] - w_curr['end'] > 1.5:
                # Gap is excessively large. Pull current word forward.
                dur = w_curr['end'] - w_curr['start']
                w_curr['end'] = w_next['start'] - 0.05
                w_curr['start'] = max(0.0, w_curr['end'] - dur)
                
        phrase_text = ''.join(w['word'] for w in words_list).strip()
        if phrase_text:
            new_segments.append({
                'start': words_list[0]['start'],
                'end': words_list[-1]['end'],
                'text': phrase_text,
                'words': list(words_list)
            })

    for i, word in enumerate(all_words):
        if i > 0 and current_words:
            prev = all_words[i - 1]
            gap = float(word.get("start", 0.0)) - float(prev.get("end", 0.0))
            # Split when there is a real pause between spoken words.
            if gap >= pause_split_s:
                process_and_add_phrase(current_words)
                current_words = []

        current_words.append(word)
        text = word['word'].strip()

        if text and text[-1] in phrase_end_chars:
            process_and_add_phrase(current_words)
            current_words = []

    # Remaining words with no trailing punctuation
    process_and_add_phrase(current_words)

    return {'segments': new_segments}

def convert_data_to_srt(data: dict, srt_path: str):
    try:
        with open(srt_path, 'w', encoding='utf-8') as f:
            idx = 1
            for seg in data.get('segments', []):
                text = seg['text'].strip()
                if not text: continue
                start, end = format_srt_time(seg['start']), format_srt_time(seg['end'])
                f.write(f"{idx}\n{start} --> {end}\n{text}\n\n")
                idx += 1
        return True
    except Exception: return False

def sanitize_subtitle_segments(
    data: dict,
    min_duration: float = DEFAULT_MIN_SUB_DURATION,
    max_repeat_run: int = DEFAULT_MAX_REPEAT_RUN
) -> dict:
    segments = sorted(
        list(data.get("segments", [])),
        key=lambda s: (float(s.get("start", 0.0)), float(s.get("end", 0.0)))
    )
    if not segments:
        return data

    norm_counts = Counter()
    for seg in segments:
        norm = _normalize_text_for_compare((seg.get("text") or "").strip())
        if norm:
            norm_counts[norm] += 1

    # Detect likely hallucinated loops (short phrases repeated many times).
    dominant_norms = {
        n for n, c in norm_counts.items()
        if c >= 10 and len(n.split()) <= 4 and len(n) <= 24
    }

    cleaned = []
    last_norm = None
    repeat_run = 0

    for seg in segments:
        text = (seg.get("text") or "").strip()
        if not text:
            continue

        norm = _normalize_text_for_compare(text)

        # Drop standalone dominant-loop lines.
        if norm in dominant_norms:
            continue

        # Drop near-duplicate short lines that occur within 1 second.
        if cleaned:
            prev = cleaned[-1]
            prev_norm = _normalize_text_for_compare(prev.get("text", ""))
            if norm and norm == prev_norm and (float(seg.get("start", 0.0)) - prev["start"]) <= 1.0:
                continue

        if norm and norm == last_norm:
            repeat_run += 1
        else:
            repeat_run = 1
            last_norm = norm

        # Guard against catastrophic repetition loops (e.g., hundreds of "Vamos.")
        if repeat_run > max_repeat_run:
            continue

        start = float(seg.get("start", 0.0))
        end = float(seg.get("end", start))
        if end < start:
            end = start

        cleaned.append({
            "start": start,
            "end": end,
            "text": text,
            "words": seg.get("words", [])
        })

    if not cleaned:
        return {"segments": []}

    # Enforce readable minimum durations by extending end time
    # without crossing into the next segment start.
    for i in range(len(cleaned)):
        cur = cleaned[i]
        desired_end = cur["start"] + min_duration
        if cur["end"] < desired_end:
            if i < len(cleaned) - 1:
                next_start = cleaned[i + 1]["start"]
                cur["end"] = min(desired_end, max(cur["end"], next_start - 0.02))
            else:
                cur["end"] = desired_end
        if cur["end"] <= cur["start"]:
            cur["end"] = cur["start"] + 0.20

    cleaned.sort(key=lambda s: (s["start"], s["end"]))
    return {"segments": cleaned}

def _normalize_text_for_compare(text: str) -> str:
    t = (text or "").lower().strip()
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"[^\w\s]", "", t)
    return t

def _segment_quality(seg: dict) -> float:
    txt = (seg.get("text") or "").strip()
    if not txt:
        return -10.0
    avg_logprob = float(seg.get("avg_logprob", -1.2))
    no_speech_prob = float(seg.get("no_speech_prob", 0.0))
    compression_ratio = float(seg.get("compression_ratio", 1.5))
    # Higher is better. Penalize likely hallucination signatures.
    return avg_logprob - (0.8 * no_speech_prob) - (0.15 * max(0.0, compression_ratio - 2.2))

def _build_suspicious_windows(segments: list, window_s: float = 45.0) -> set:
    if not segments:
        return set()
    buckets = {}
    for s in segments:
        start = float(s.get("start", 0.0))
        end = float(s.get("end", start))
        txt = (s.get("text") or "").strip()
        norm = _normalize_text_for_compare(txt)
        b = int(start // window_s)
        if b not in buckets:
            buckets[b] = {"count": 0, "short": 0, "norms": Counter(), "micro": 0}
        buckets[b]["count"] += 1
        if len(norm.split()) <= 3:
            buckets[b]["short"] += 1
        if norm:
            buckets[b]["norms"][norm] += 1
        if (end - start) < 0.35:
            buckets[b]["micro"] += 1

    bad = set()
    for b, m in buckets.items():
        total = max(1, m["count"])
        top_repeat = m["norms"].most_common(1)[0][1] if m["norms"] else 0
        short_ratio = m["short"] / total
        micro_ratio = m["micro"] / total
        repeat_ratio = top_repeat / total
        if (total >= 8 and repeat_ratio > 0.35 and short_ratio > 0.50) or (total >= 8 and micro_ratio > 0.45):
            bad.add(b)
    return bad

def normalize_timeline(data: dict, min_duration: float = DEFAULT_MIN_SUB_DURATION) -> dict:
    segs = sorted(list(data.get("segments", [])), key=lambda s: (float(s.get("start", 0.0)), float(s.get("end", 0.0))))
    if not segs:
        return {"segments": []}
    out = []
    prev_end = 0.0
    for seg in segs:
        text = (seg.get("text") or "").strip()
        if not text:
            continue
        start = float(seg.get("start", 0.0))
        end = float(seg.get("end", start))
        start = max(start, prev_end - 0.05)
        if end <= start:
            end = start + min_duration
        out.append({**seg, "start": start, "end": end, "text": text})
        prev_end = end

    for i in range(len(out)):
        desired_end = out[i]["start"] + min_duration
        if i < len(out) - 1:
            next_start = out[i + 1]["start"]
            out[i]["end"] = max(out[i]["end"], min(desired_end, max(out[i]["start"] + 0.20, next_start - 0.02)))
        else:
            out[i]["end"] = max(out[i]["end"], desired_end)
    return {"segments": out}

def merge_missed_segments(primary: dict, rescue: dict) -> dict:
    p = sorted(list(primary.get("segments", [])), key=lambda x: (x.get("start", 0.0), x.get("end", 0.0)))
    r = sorted(list(rescue.get("segments", [])), key=lambda x: (x.get("start", 0.0), x.get("end", 0.0)))
    if not p:
        return {"segments": r}
    if not r:
        return {"segments": p}

    def overlap_ratio(a, b):
        inter = max(0.0, min(a["end"], b["end"]) - max(a["start"], b["start"]))
        if inter <= 0:
            return 0.0
        dur = max(0.001, b["end"] - b["start"])
        return inter / dur

    existing_norm = {_normalize_text_for_compare(s.get("text", "")) for s in p}
    bad_windows = _build_suspicious_windows(p)
    adds = []
    for seg in r:
        txt = (seg.get("text") or "").strip()
        if len(txt) < 3:
            continue
        bucket = int(float(seg.get("start", 0.0)) // 45.0)
        norm = _normalize_text_for_compare(txt)
        if norm and norm in existing_norm and bucket not in bad_windows:
            continue
        max_ov = 0.0
        best_overlap_seg = None
        for ps in p:
            ov = overlap_ratio(ps, seg)
            if ov > max_ov:
                max_ov = ov
                best_overlap_seg = ps

        # In suspicious windows, prefer rescue when it has better confidence score.
        if max_ov >= 0.30 and bucket in bad_windows and best_overlap_seg is not None:
            if _segment_quality(seg) > _segment_quality(best_overlap_seg) + 0.08:
                best_overlap_seg["text"] = seg.get("text", best_overlap_seg.get("text", ""))
                best_overlap_seg["start"] = min(float(best_overlap_seg.get("start", 0.0)), float(seg.get("start", 0.0)))
                best_overlap_seg["end"] = max(float(best_overlap_seg.get("end", 0.0)), float(seg.get("end", 0.0)))
                best_overlap_seg["avg_logprob"] = seg.get("avg_logprob", best_overlap_seg.get("avg_logprob", -1.2))
                best_overlap_seg["no_speech_prob"] = seg.get("no_speech_prob", best_overlap_seg.get("no_speech_prob", 0.0))
                best_overlap_seg["compression_ratio"] = seg.get("compression_ratio", best_overlap_seg.get("compression_ratio", 1.5))
            continue

        if max_ov < 0.30:
            adds.append(seg)

    merged = sorted(p + adds, key=lambda x: (x.get("start", 0.0), x.get("end", 0.0)))
    log_event(f"merge_missed_segments primary={len(p)} rescue={len(r)} suspicious_windows={len(bad_windows)} added={len(adds)} merged={len(merged)}")
    return {"segments": merged}

def run_transcription(file_path: str, args: argparse.Namespace) -> tuple[bool, str]:
    global transcription_model
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    final_srt_path = os.path.join(args.output_dir if args.output_dir else os.path.dirname(file_path), f"{base_name}.srt")

    print(f"🎤 Processing: {base_name}")
    model_path = MODEL_ALIASES.get(args.model, args.model)
    backend = resolve_model_backend(model_path)
    log_event(f"run_transcription start file={file_path} model={args.model} model_path={model_path} backend={backend} lang={args.lang} task={args.task} "
              f"vad_filter={args.vad_filter} whisper_vad_threshold={args.whisper_vad_threshold} "
              f"whisper_vad_min_silence_ms={args.whisper_vad_min_silence_ms} "
              f"use_vad={args.use_vad} silero_vad_threshold={args.vad_threshold} "
              f"silero_vad_min_silence_ms={args.vad_min_silence_ms} pipeline={getattr(args, 'pipeline', [])}")

    if not has_valid_audio_track(file_path):
        return False, "Skipped (No Audio)"

    transcription_source = file_path
    temp_files = []

    if not file_path.lower().endswith(".wav"):
        base_wav = extract_audio_to_wav(file_path, args.output_dir)
        if base_wav:
            transcription_source = base_wav
            temp_files.append(base_wav)

    for step in getattr(args, 'pipeline', []):
        new_source = None
        if step == 'isolate' and args.isolate:
            new_source = isolate_audio_with_demucs(transcription_source, args.output_dir, model=getattr(args, 'demucs_model', "htdemucs_ft"), shifts=getattr(args, 'demucs_shifts', 2))
        elif step == 'enhance' and args.enhance:
            new_source = preprocess_audio(transcription_source, args.output_dir)
        elif step == 'cl' and args.cl:
            new_source = apply_compression_limiter(transcription_source, args.output_dir, threshold=getattr(args, 'cl_threshold', 0.125), ratio=getattr(args, 'cl_ratio', 2.0))

        if new_source and os.path.exists(new_source):
            transcription_source = new_source
            temp_files.append(new_source)

    cleaned_data = None

    def _normalize_qwen_result(result):
        segments_out = []
        if isinstance(result, dict):
            if isinstance(result.get("segments"), list):
                source_segments = result.get("segments")
            elif isinstance(result.get("timestamps"), list):
                source_segments = result.get("timestamps")
            elif isinstance(result.get("chunks"), list):
                source_segments = result.get("chunks")
            else:
                source_segments = []
        elif isinstance(result, list) and result and hasattr(result[0], "text") and hasattr(result[0], "time_stamps"):
            # qwen-asr ASRTranscription objects
            source_segments = []
            for item in result:
                ts = getattr(item, "time_stamps", None)
                txt = str(getattr(item, "text", "") or "").strip()
                if not txt:
                    continue
                if not ts:
                    source_segments.append({"text": txt})
                    continue
                if isinstance(ts, list):
                    for ent in ts:
                        if isinstance(ent, dict):
                            source_segments.append({
                                "start": ent.get("start", ent.get("begin", ent.get("from", 0.0))),
                                "end": ent.get("end", ent.get("stop", ent.get("to", 0.0))),
                                "text": str(ent.get("text", txt) or "").strip()
                            })
                        elif isinstance(ent, (list, tuple)) and len(ent) >= 3:
                            source_segments.append({"start": ent[0], "end": ent[1], "text": str(ent[2] or "").strip()})
                else:
                    source_segments.append({"text": txt})
        elif isinstance(result, list):
            source_segments = result
        else:
            source_segments = []

        for seg in source_segments:
            if not isinstance(seg, dict):
                continue
            text = str(seg.get("text", "") or "").strip()
            if not text:
                continue
            start = seg.get("start", seg.get("begin", seg.get("from", 0.0)))
            end = seg.get("end", seg.get("stop", seg.get("to", start)))
            try:
                start = float(start)
                end = float(end)
            except Exception:
                continue
            words = []
            raw_words = seg.get("words", seg.get("tokens", []))
            if isinstance(raw_words, list):
                for w in raw_words:
                    if not isinstance(w, dict):
                        continue
                    wtxt = str(w.get("word", w.get("text", "")) or "")
                    ws = w.get("start", w.get("begin", start))
                    we = w.get("end", w.get("stop", end))
                    try:
                        ws = float(ws)
                        we = float(we)
                    except Exception:
                        continue
                    words.append({"start": ws, "end": we, "word": wtxt})

            segments_out.append({
                "start": start,
                "end": end,
                "text": text,
                "avg_logprob": float(seg.get("avg_logprob", -1.2)),
                "no_speech_prob": float(seg.get("no_speech_prob", 0.0)),
                "compression_ratio": float(seg.get("compression_ratio", 1.5)),
                "words": words
            })

        if not segments_out and isinstance(result, dict):
            if str(result.get("text", "")).strip():
                raise RuntimeError("Qwen returned text without timestamps. Enable timestamp output in qwen-asr.")
        if not segments_out and isinstance(result, list):
            txt_parts = [str(getattr(x, "text", "")).strip() for x in result if hasattr(x, "text")]
            if any(txt_parts):
                raise RuntimeError("Qwen returned text without timestamps. This qwen-asr build may not support timestamp output for your config.")
        return {"segments": segments_out}

    def try_transcribe_whisper(vad_filt):
        vad_params = dict(
            min_silence_duration_ms=args.whisper_vad_min_silence_ms,
            threshold=args.whisper_vad_threshold
        )
        segments, info = transcription_model.transcribe(
            transcription_source, language=args.lang, task=args.task,
            vad_filter=vad_filt,
            vad_parameters=vad_params,
            beam_size=args.beam_size, best_of=args.best_of, temperature=args.temperature,
            word_timestamps=True
        )
        res = {"segments": []}
        with tqdm(total=round(info.duration, 2), unit='s', desc="   Whisper", dynamic_ncols=True, leave=False) as pbar:
            for seg in segments:
                res["segments"].append({
                    "start": seg.start,
                    "end": seg.end,
                    "text": seg.text,
                    "avg_logprob": getattr(seg, "avg_logprob", -1.2),
                    "no_speech_prob": getattr(seg, "no_speech_prob", 0.0),
                    "compression_ratio": getattr(seg, "compression_ratio", 1.5),
                    "words": [{"start": w.start, "end": w.end, "word": w.word} for w in seg.words]
                })
                pbar.update(seg.end - pbar.n)
            pbar.update(info.duration - pbar.n)
        log_event(f"try_transcribe done vad_filter={vad_filt} segments={len(res['segments'])} duration={round(info.duration, 2)}")
        return res

    def try_transcribe_qwen(vad_filt):
        aligner_name = os.environ.get("QWEN_ASR_ALIGNER", "").strip()
        log_event(f"try_transcribe_qwen aligner_env={aligner_name}")
        total_duration = get_audio_duration_seconds(transcription_source)
        if total_duration <= 0:
            # Fallback to single-shot if duration probe fails.
            result = transcription_model.transcribe(
                audio=transcription_source,
                context="",
                language=args.lang,
                return_time_stamps=True
            )
            normalized = _normalize_qwen_result(result)
            if not normalized["segments"]:
                raise RuntimeError("Qwen returned no timestamped segments.")
            log_event(f"try_transcribe_qwen done(single) segments={len(normalized['segments'])}")
            return normalized

        chunk_s = 60.0
        overlap_s = 1.5
        merged_segments = []
        tmp_qwen_chunks = []
        processed = 0.0

        with tqdm(total=round(total_duration, 2), unit='s', desc="   Qwen", dynamic_ncols=True, leave=False) as pbar:
            chunk_index = 0
            while processed < total_duration:
                start = max(0.0, processed - (overlap_s if chunk_index > 0 else 0.0))
                remaining = total_duration - start
                dur = min(chunk_s + (overlap_s if chunk_index > 0 else 0.0), remaining)
                chunk_path = os.path.join(
                    args.output_dir if args.output_dir else os.path.dirname(transcription_source),
                    f"{base_name}_qwen_chunk_{chunk_index:04d}.wav"
                )
                if not extract_audio_chunk_to_wav(transcription_source, start, dur, chunk_path):
                    raise RuntimeError(f"Failed to extract chunk {chunk_index} ({start:.2f}s +{dur:.2f}s)")
                tmp_qwen_chunks.append(chunk_path)

                # qwen-asr/transformers can spam per-chunk generation notices to stdout,
                # which visually breaks tqdm rendering. Silence only this call's stdout.
                with contextlib.redirect_stdout(io.StringIO()):
                    result = transcription_model.transcribe(
                        audio=chunk_path,
                        context="",
                        language=args.lang,
                        return_time_stamps=True
                    )
                normalized = _normalize_qwen_result(result)

                # Shift chunk-local timestamps to file timeline and trim overlap duplicates.
                trim_before = processed - 0.2 if chunk_index > 0 else -1.0
                for seg in normalized.get("segments", []):
                    seg_start = float(seg.get("start", 0.0)) + start
                    seg_end = float(seg.get("end", seg_start)) + start
                    if seg_end <= trim_before:
                        continue
                    seg["start"] = max(seg_start, 0.0)
                    seg["end"] = max(seg_end, seg["start"])
                    merged_segments.append(seg)

                next_processed = min(total_duration, processed + chunk_s)
                delta = max(0.0, next_processed - processed)
                # Prevent tqdm overflow/clamp warnings from float drift/overshoot.
                if pbar.n + delta > pbar.total:
                    delta = max(0.0, pbar.total - pbar.n)
                if delta > 0:
                    pbar.update(delta)
                processed = next_processed
                chunk_index += 1
            # Explicitly land on 100% to avoid fractional residue.
            if pbar.n < pbar.total:
                pbar.update(pbar.total - pbar.n)

        for tmp in tmp_qwen_chunks:
            if not args.keep:
                try:
                    if os.path.exists(tmp):
                        os.remove(tmp)
                except Exception:
                    pass

        if not merged_segments:
            raise RuntimeError("Qwen returned no timestamped segments.")
        merged_segments.sort(key=lambda s: (s.get("start", 0.0), s.get("end", 0.0)))
        log_event(f"try_transcribe_qwen done(chunked) segments={len(merged_segments)} duration={round(total_duration,2)} chunks={int((total_duration + chunk_s - 1)//chunk_s)}")
        return {"segments": merged_segments}

    def try_transcribe(vad_filt):
        if backend == "qwen":
            return try_transcribe_qwen(vad_filt)
        return try_transcribe_whisper(vad_filt)

    try:
        ensure_model_loaded(args.model)
        cleaned_data = try_transcribe(args.vad_filter)
    except Exception as e:
        print(f"   ⚠️  Model Error: {e}")
        log_event(f"transcribe primary model error={e}\n{traceback.format_exc()}")
        # Fallback Logic (Whisper only; Qwen must not silently switch backends)
        if backend == "whisper":
            for fb in ["large-v3", "large-v2"]:
                if args.model == fb:
                    continue
                print(f"   ⚠️  Switching to fallback: {fb}")
                try:
                    ensure_model_loaded(fb)
                    cleaned_data = try_transcribe(True)
                    if cleaned_data:
                        break
                except Exception as fb_e:
                    log_event(f"fallback model={fb} failed error={fb_e}\n{traceback.format_exc()}")
                    pass
        else:
            return False, f"Qwen transcription failed: {e}"

    if not cleaned_data: return False, "Transcription failed"

    if args.rescue_missed:
        print("   🛟 Running rescue pass (no Whisper VAD) for quiet/missed lines...")
        try:
            rescue_data = try_transcribe(False)
            before_count = len(cleaned_data.get("segments", []))
            cleaned_data = merge_missed_segments(cleaned_data, rescue_data)
            after_count = len(cleaned_data.get("segments", []))
            if after_count > before_count:
                print(f"      ↳ Recovered {after_count - before_count} additional segments.")
            else:
                print("      ↳ No additional segments recovered.")
        except Exception as e:
            print(f"      ⚠️ Rescue pass failed: {e}")
            log_event(f"rescue pass error={e}\n{traceback.format_exc()}")

    if args.use_vad:
        print("   🔍 Aligning with Silero VAD...")
        true_regions = detect_true_speech_regions(
            transcription_source,
            args.vad_threshold,
            args.vad_min_silence_ms
        )
        if true_regions:
            c = 0
            for seg in cleaned_data["segments"]:
                for w in seg.get("words", []):
                    old_s = w["start"]
                    w["start"], w["end"] = snap_to_vad(w["start"], w["end"], true_regions)
                    if w["start"] != old_s: c += 1
            print(f"      ↳ Aligned {c} words.")

    # Re-segment so each SRT entry is one phrase/sentence
    cleaned_data = resegment_by_phrase(cleaned_data, pause_split_s=args.phrase_pause_split_s)
    cleaned_data = sanitize_subtitle_segments(
        cleaned_data,
        min_duration=args.min_sub_duration,
        max_repeat_run=args.max_repeat_run
    )
    cleaned_data = normalize_timeline(cleaned_data, min_duration=args.min_sub_duration)

    success = convert_data_to_srt(cleaned_data, final_srt_path)
    log_event(f"run_transcription finished success={success} output={final_srt_path} final_segments={len(cleaned_data.get('segments', []))}")

    if not args.keep:
        for tmp in temp_files:
            try:
                if os.path.exists(tmp): os.remove(tmp)
            except Exception: pass

    return success, final_srt_path

def main():
    parser = argparse.ArgumentParser(description="Whisper Transcription Ultimate V5")
    parser.add_argument('--version', action='version', version='%(prog)s 5.0')
    parser.add_argument("files", nargs="*", help="Files/URLs to process")
    parser.add_argument("-u", "--url", action="append", help="URLs")
    parser.add_argument("-o", "--output_dir", type=str)
    parser.add_argument(
        "-m", "--model", type=str, default=DEFAULT_MODEL_KEY,
        help=(
            "Model alias/path. Supported aliases: "
            "default, large-v2, large-v3, turbo, distil, medium, small, "
            "qwen3-asr-0.6b, qwen3-asr-1.7b"
        )
    )
    parser.add_argument("-l", "--lang", type=str)
    parser.add_argument("--task", type=str, default=DEFAULT_TASK)
    parser.add_argument("--precision", type=str, default="auto", choices=["auto", "float16", "int8", "float32"], help="Force compute type")

    parser.add_argument("-hq", "--high-quality", action="store_true", help="Enable large-v3 + isolate + enhance + limiter")
    parser.add_argument("-cl", "--compression-limiter", action=PipelineAction, nargs=0, const=True, dest="cl")
    parser.add_argument("-e", "--enhance", action=PipelineAction, nargs=0, const=True, dest="enhance")
    parser.add_argument("-i", "--isolate", action=PipelineAction, nargs=0, const=True, dest="isolate")
    parser.add_argument("-k", "--keep", action="store_true", help="Keep temp files")
    parser.add_argument("-c", "--clipboard", action="store_true")
    parser.add_argument("--low-volume-mode", action="store_true", help="Bias toward keeping quiet speech (less aggressive Whisper VAD)")
    parser.add_argument("--rescue-missed", action=argparse.BooleanOptionalAction, default=True, help="Run a second no-VAD pass and merge likely-missed lines")

    parser.add_argument("--use_vad", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--whisper_vad_threshold", type=float, default=DEFAULT_WHISPER_VAD_THRESHOLD)
    parser.add_argument("--whisper_vad_min_silence_ms", type=int, default=DEFAULT_WHISPER_VAD_MIN_SILENCE_MS)
    parser.add_argument("--min_sub_duration", type=float, default=DEFAULT_MIN_SUB_DURATION)
    parser.add_argument(
        "--phrase_pause_split_s",
        type=float,
        default=DEFAULT_PHRASE_PAUSE_SPLIT_S,
        help="Split subtitle phrase when inter-word pause is at least this many seconds."
    )
    parser.add_argument("--max_repeat_run", type=int, default=DEFAULT_MAX_REPEAT_RUN)
    parser.add_argument("--vad_threshold", type=float, default=DEFAULT_VAD_THRESHOLD)
    parser.add_argument("--vad_min_silence_ms", type=int, default=DEFAULT_VAD_MIN_SILENCE_MS)
    parser.add_argument("--vad_filter", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--beam_size", type=int, default=5)
    parser.add_argument("--best_of", type=int, default=5)
    parser.add_argument("--temperature", type=float, default=0)
    parser.add_argument("--cl_threshold", type=float, default=0.125)
    parser.add_argument("--cl_ratio", type=float, default=2.0)
    parser.add_argument("--demucs_model", type=str, default="htdemucs_ft")
    parser.add_argument("--demucs_shifts", type=int, default=2)
    parser.add_argument("--debug-log", action=argparse.BooleanOptionalAction, default=True, help="Write detailed per-run debug log")

    args = parser.parse_args()
    
    global PREFERRED_COMPUTE_TYPE
    PREFERRED_COMPUTE_TYPE = args.precision

    if not hasattr(args, 'pipeline'): args.pipeline = []

    if args.high_quality:
        args.model = "large-v3"
        args.isolate = True
        args.enhance = True
        args.cl = True
        args.use_vad = True  # CHANGED: We want VAD enabled in HQ to snap timestamps!
        if 'isolate' not in args.pipeline: args.pipeline.append('isolate')
        if 'enhance' not in args.pipeline: args.pipeline.append('enhance')
        if 'cl' not in args.pipeline: args.pipeline.append('cl')

    if args.low_volume_mode:
        # Keep quieter speech by making Whisper's pre-transcription VAD less aggressive.
        # This does not disable Silero timestamp snapping.
        args.vad_filter = True
        args.whisper_vad_threshold = min(args.whisper_vad_threshold, 0.15)
        args.whisper_vad_min_silence_ms = max(args.whisper_vad_min_silence_ms, 700)

    pipeline_priority = {'isolate': 1, 'enhance': 2, 'cl': 3}
    args.pipeline.sort(key=lambda x: pipeline_priority.get(x, 99))

    if args.url:
        for u in args.url: args.files.append(u)

    if args.clipboard:
        if sys.platform == 'win32':
            try:
                cb = subprocess.check_output(['powershell', '-NoProfile', '-Command', 'Get-Clipboard'], text=True).strip()
                if cb.startswith(('http', 'www')): args.files.append(cb)
                else:
                    if not args.files:
                        print("❌ Clipboard does not contain a URL and no files were specified.")
                        sys.exit(1)
            except Exception: pass

    files_to_process = collect_input_files(args.files)
    if not files_to_process: return

    if args.output_dir: os.makedirs(args.output_dir, exist_ok=True)

    if args.debug_log:
        log_dir = args.output_dir if args.output_dir else os.getcwd()
        log_name = f"transcribe_debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        log_path = os.path.join(log_dir, log_name)
        set_log_file(log_path)
        log_event("=== Transcription run started ===")
        log_event(f"cwd={os.getcwd()}")
        log_event(f"python={sys.version}")
        log_event(f"argv={' '.join(sys.argv)}")
        log_event(f"args={vars(args)}")
        log_event(f"files_to_process_count={len(files_to_process)}")
        print(f"📝 Debug log: {log_path}")

    print(f"🚀 Starting Batch: {len(files_to_process)} files using {args.model}")
    print(f"   Pipeline: {' -> '.join(args.pipeline) if args.pipeline else 'Direct'}")
    log_event(f"batch start model={args.model} pipeline={args.pipeline if args.pipeline else ['Direct']}")

    success_c = 0
    for i, fpath in enumerate(files_to_process, 1):
        print(f"\n--- [{i}/{len(files_to_process)}] ---")
        try:
            target = fpath
            is_tmp = False
            if fpath.startswith("http"):
                dl = download_audio(fpath, args.output_dir)
                if not dl: continue
                target = dl
                is_tmp = True

            ok, msg = run_transcription(target, args)
            if ok:
                print(f"✅ Finished: {os.path.basename(msg)}")
                success_c += 1
            else:
                print(f"❌ Failed: {msg}")

            if is_tmp and not args.keep and os.path.exists(target):
                os.remove(target)
                
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
        except KeyboardInterrupt:
            print("\n🛑 Stopped by user."); sys.exit(0)
        except Exception as e:
            print(f"❌ Critical: {e}")
            log_event(f"critical file={fpath} error={e}\n{traceback.format_exc()}")

    print(f"\nDone. {success_c}/{len(files_to_process)} successful.")
    log_event(f"batch finished success={success_c}/{len(files_to_process)}")
    log_event("=== Transcription run finished ===")

if __name__ == "__main__":
    main()
