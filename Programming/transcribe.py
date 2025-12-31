
"""
transcribe_ultimate_v2.py
-------------------------
Production-Grade Transcription & Audio Processing Pipeline

Features:
1. Robust Audio Validation: Uses PyAV for 100% stream detection accuracy across MOV, MKV, MP4, etc.
2. Modern Model Support: Optimized for Faster-Whisper (Turbo, Distil, Large-v3).
3. Auto-Fallback & Recovery: Switches to fallback models (Large-v2) on internal VAD crashes.
4. Compression Limiter: Integrated Compressor (acompressor) and Limiter (alimiter) for consistent loudness.
5. Vocal Isolation (Demucs): Forced GPU isolation using htdemucs_ft to separate speech from background.
6. Audio Enhancement: Dynamic normalization via FFmpeg (dynaudnorm) to balance quiet/loud audio.
7. Multi-Stage VAD: 
   - Internal Whisper VAD filter for hallucination reduction.
   - External Silero VAD for precise word-level subtitle alignment (--use_vad).
   - Adjustable sensitivity via --vad_threshold.
8. Dynamic Feedback: Real-time progress bars for Whisper (tqdm), FFmpeg, and Demucs isolation.
9. Intelligent SRT Generation: Netflix-style grouping, smart line breaks, and punctuation-aware casing.
10. Batch Processing: Supports direct files, glob patterns, YouTube/URL downloads, and URL lists in TXT.
11. Headless/Remote Ready: Top-level DEFAULT constants for easy default behavior customization.
12. Ordered Pipeline: Flags like -cl, -e, and -i respect command-line order (Default: -cl -e -i).

Dependencies:
- ffmpeg, faster-whisper, demucs, yt-dlp, tqdm, av, torch, torchaudio, silero-vad
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
from tqdm import tqdm

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

DEFAULT_MODEL_KEY = "turbo"
DEFAULT_TASK = "transcribe"
DEFAULT_MIN_SILENCE_DURATION_WT = 100 # ms
DEFAULT_VAD_THRESHOLD = 0.3
DEFAULT_MAX_WORD_DURATION = 750       # ms

DEFAULT_ENHANCE = False  # Normalize / Pre-process audio levels
DEFAULT_ISOLATE = False # Use Demucs to isolate vocals
DEFAULT_CL = False # Use compression limiter to prevent clipping
DEFAULT_VAD_ALIGN = True # Enable Silero VAD alignment (heavy)
DEFAULT_VAD_FILTER = False  # Enable Whisper internal VAD filter

# --- Custom Pipeline Tracking for Argparse ---
class PipelineAction(argparse.Action):
    """Custom action to track the order of pipeline flags (-e, -i)."""
    def __call__(self, parser, namespace, values, option_string=None):
        if not hasattr(namespace, 'pipeline'):
            setattr(namespace, 'pipeline', [])
        
        # If the option is a positive flag (e.g., -e, -i)
        if self.const is True:
            setattr(namespace, self.dest, True)
            if self.dest not in namespace.pipeline:
                namespace.pipeline.append(self.dest)
        # If it's a negative flag (e.g., -ne, -ni)
        elif self.const is False:
            setattr(namespace, self.dest, False)
            if self.dest in namespace.pipeline:
                namespace.pipeline.remove(self.dest)

# --- Advanced Whisper Tuning ---
DEFAULT_BEAM_SIZE = 20                   # Number of paths to explore (Higher = more accurate, slower. Range: 1-20+. Default: 5)
DEFAULT_BEST_OF = 20                     # Number of candidates to sample (Range: 1-20+. Default: 5)
DEFAULT_PATIENCE = 2.0                  # Beam search patience (Range: 0.0-2.0+. Default: 1.0)
DEFAULT_TEMPERATURE = 0                 # Randomness (0 = deterministic, 1.0 = creative. Range: 0.0-1.0. Default: 0)
DEFAULT_CONDITION_ON_PREVIOUS_TEXT = False # Use previous segment as context (Setting to True can cause loops. Default: False)
DEFAULT_INITIAL_PROMPT = None           # Hint/Context for the model (e.g., "Overwatch technical terms". Default: None)
DEFAULT_NO_SPEECH_THRESHOLD = 0.3       # Silence detection threshold (Range: 0.0-1.0. Default: 0.6)
DEFAULT_LOGPROB_THRESHOLD = -1.0        # Log probability threshold for speech detection (Range: -20.0 to 0.0. Default: -1.0)
DEFAULT_COMPRESSION_RATIO_THRESHOLD = 2.4 # Repetition filter (Filters out "the the the" loops. Range: 1.0-5.0+. Default: 2.4)

# --- Advanced Audio Enhancement Tuning ---
DEFAULT_ENHANCE_NORMALIZE = False      # Enable dynaudnorm (True/False)
DEFAULT_ENHANCE_MONO = True           # Downmix to mono (True/False)
DEFAULT_ENHANCE_FRAME_LEN = 200        # Frame length in ms (Lower = more reactive, higher = smoother. Range: 10-2000. Default: 200)
DEFAULT_ENHANCE_GAUSSIAN = 5           # Gaussian filter window size (Higher = smoother gain transitions. Range: 3-301, must be odd. Default: 5)
DEFAULT_ENHANCE_MAX_GAIN = 40          # Maximum gain factor (How much to boost quiet parts. Range: 1.0-100.0. Default: 40)
DEFAULT_ENHANCE_PEAK = 0.95            # Target peak volume (Normalization level. Range: 0.0-1.0. Default: 0.95)

# --- Advanced Demucs Tuning ---
DEFAULT_DEMUCS_MODEL = "htdemucs_ft"      # Demucs model to use (Options: htdemucs, htdemucs_ft, htdemucs_6s. Default: htdemucs_ft)
DEFAULT_DEMUCS_SHIFTS = 5               # Number of random shifts (Higher = better quality, slower. Range: 1-20+. Default: 5)
DEFAULT_DEMUCS_OVERLAP = 0.25             # Overlap between segments (Range: 0.0-1.0. Default: 0.25)
DEFAULT_DEMUCS_FLOAT32 = True            # Use float32 for output (Default: True)

# --- Advanced Compression Limiter Tuning ---
DEFAULT_CL_C_ENABLE = True          # Enable compressor stage
DEFAULT_CL_L_ENABLE = True          # Enable limiter stage

# Compressor Stage (acompressor)
DEFAULT_CL_THRESHOLD = 0.125        # Threshold (Range: 0.000976563-1.0. Default: 0.125)
DEFAULT_CL_RATIO = 2.0              # Ratio (Range: 1.0-20.0. Default: 2.0)
DEFAULT_CL_C_ATTACK = 20.0          # Compressor Attack ms (Range: 0.01-2000.0. Default: 20.0)
DEFAULT_CL_C_RELEASE = 250.0        # Compressor Release ms (Range: 0.01-9000.0. Default: 250.0)
DEFAULT_CL_MAKEUP = 1.0             # Make-up gain (Range: 1.0-64.0. Default: 1.0)
DEFAULT_CL_KNEE = 2.828             # Knee (Range: 1.0-8.0. Default: 2.828)

# Limiter Stage (alimiter)
DEFAULT_CL_L_LEVEL_IN = 1.0         # Limiter Input gain (Range: 0.015625-64.0. Default: 1.0)
DEFAULT_CL_L_LEVEL_OUT = 1.0        # Limiter Output gain (Range: 0.015625-64.0. Default: 1.0)
DEFAULT_CL_L_LIMIT = 0.99           # Ceiling (Range: 0.0625-1.0. Default: 0.99)
DEFAULT_CL_L_ATTACK = 5.0           # Limiter Attack ms (Range: 0.1-80.0. Default: 5.0)
DEFAULT_CL_L_RELEASE = 50.0         # Limiter Release ms (Range: 1.0-8000.0. Default: 50.0)
DEFAULT_CL_ASC = False              # Enable Auto Slow Control (True/False)
DEFAULT_CL_ASC_LEVEL = 0.5          # ASC Level (Range: 0.0-1.0. Default: 0.5)
DEFAULT_CL_AUTO_LEVEL = True        # Auto level (True/False)
DEFAULT_CL_LATENCY = False          # Compensate delay (True/False)

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

def preprocess_audio(input_path: str, output_dir: str = None, 
                     do_normalize=DEFAULT_ENHANCE_NORMALIZE,
                     do_mono=DEFAULT_ENHANCE_MONO,
                     frame_len=DEFAULT_ENHANCE_FRAME_LEN, 
                     gaussian=DEFAULT_ENHANCE_GAUSSIAN, 
                     max_gain=DEFAULT_ENHANCE_MAX_GAIN, 
                     peak=DEFAULT_ENHANCE_PEAK) -> str:
    """
    Pre-processes audio using FFmpeg. Optional dynamic normalization and mono downmix.
    Returns path to temporary WAV file.
    """
    try:
        mode_desc = []
        if do_normalize: mode_desc.append("Normalization")
        if do_mono: mode_desc.append("Mono Downmix")
        print(f"   🔊 Enhancing audio ({' + '.join(mode_desc) if mode_desc else 'Passthrough'})...")
        
        wd = output_dir if output_dir else os.path.dirname(input_path)
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        temp_wav = os.path.join(wd, f"{base_name}_enhanced.wav")
        
        # Build Filter Chain
        filters = []
        if do_normalize:
            filters.append(f"dynaudnorm=f={frame_len}:g={gaussian}:m={max_gain}:p={peak}")
        
        # Combine filters
        filter_str = ",".join(filters) if filters else "anull" # anull is a no-op audio filter
        
        # FFmpeg command
        cmd = [
            "ffmpeg", "-y", "-v", "info", "-stats",
            "-i", input_path,
            "-map", "0:a:0", # Map First Audio Track
            "-af", filter_str,
            "-ar", "16000",
        ]
        
        if do_mono:
            cmd.extend(["-ac", "1"])
            
        cmd.append(temp_wav)
        
        subprocess.run(cmd, check=True)
        return temp_wav
    except subprocess.CalledProcessError as e:
        print(f"   ⚠️  Audio Enhancement Failed: {e}")
        return None
    except FileNotFoundError:
        print("   ⚠️  FFmpeg not found. Skipping enhancement.")
        return None

def apply_compression_limiter(input_path: str, output_dir: str = None, 
                             threshold=DEFAULT_CL_THRESHOLD,
                             ratio=DEFAULT_CL_RATIO,
                             c_attack=DEFAULT_CL_C_ATTACK,
                             c_release=DEFAULT_CL_C_RELEASE,
                             makeup=DEFAULT_CL_MAKEUP,
                             knee=DEFAULT_CL_KNEE,
                             l_level_in=DEFAULT_CL_L_LEVEL_IN,
                             l_level_out=DEFAULT_CL_L_LEVEL_OUT,
                             l_limit=DEFAULT_CL_L_LIMIT,
                             l_attack=DEFAULT_CL_L_ATTACK,
                             l_release=DEFAULT_CL_L_RELEASE,
                             asc=DEFAULT_CL_ASC,
                             asc_level=DEFAULT_CL_ASC_LEVEL,
                             level=DEFAULT_CL_AUTO_LEVEL,
                             latency=DEFAULT_CL_LATENCY,
                             enable_compressor=DEFAULT_CL_C_ENABLE,
                             enable_limiter=DEFAULT_CL_L_ENABLE) -> str:
    """
    Applies a compression limiter using a chain of acompressor and/or alimiter.
    Returns path to temporary WAV file.
    """
    try:
        mode_desc = []
        if enable_compressor: mode_desc.append("Compressor")
        if enable_limiter: mode_desc.append("Limiter")
        
        if not mode_desc:
            return input_path # No-op if both disabled
            
        print(f"   🔊 Applying compression limiter ({' + '.join(mode_desc)})...")
        
        wd = output_dir if output_dir else os.path.dirname(input_path)
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        temp_wav = os.path.join(wd, f"{base_name}_cl.wav")
        
        # Build filter chain
        filters = []
        if enable_compressor:
            filters.append(f"acompressor=threshold={threshold}:ratio={ratio}:attack={c_attack}:release={c_release}:makeup={makeup}:knee={knee}")
        if enable_limiter:
            filters.append(
                f"alimiter=level_in={l_level_in}:level_out={l_level_out}:limit={l_limit}:"
                f"attack={l_attack}:release={l_release}:asc={1 if asc else 0}:"
                f"asc_level={asc_level}:level={1 if level else 0}:latency={1 if latency else 0}"
            )
        
        filter_str = ",".join(filters)
        
        cmd = [
            "ffmpeg", "-y", "-v", "info", "-stats",
            "-i", input_path,
            "-af", filter_str,
            "-ar", "16000",
            "-ac", "1", # Ensure mono for consistent processing
            temp_wav
        ]
        
        subprocess.run(cmd, check=True)
        return temp_wav
    except subprocess.CalledProcessError as e:
        print(f"   ⚠️  Compression Limiter Failed: {e}")
        return None
    except FileNotFoundError:
        print("   ⚠️  FFmpeg not found. Skipping limiter.")
        return None

def isolate_audio_with_demucs(input_path: str, output_dir: str = None, 
                              model=DEFAULT_DEMUCS_MODEL, 
                              shifts=DEFAULT_DEMUCS_SHIFTS, 
                              overlap=DEFAULT_DEMUCS_OVERLAP, 
                              use_float32=DEFAULT_DEMUCS_FLOAT32) -> str:
    """
    Uses Demucs to separate vocals from background noise/music.
    Returns path to the isolated 'vocals.wav'.
    """
    try:
        print(f"   🎸 Isolating vocals with Demucs ({model})...")
        wd = output_dir if output_dir else os.path.dirname(input_path)
        
        # Output structure: {wd}/{model_name}/{filename_no_ext}/vocals.wav
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        expected_output = os.path.join(wd, model, base_name, "vocals.wav")
        
        # Demucs command:
        # --two-stems=vocals: Only separate vocals vs others
        # -n {model}: Demucs model to use
        # --shifts: Multi-pass prediction for better quality
        # --overlap: Segment transition overlap
        # --float32: Bit-depth fidelity
        cmd = [
            "demucs", "--two-stems=vocals", "-n", model,
            "-d", "cuda" if torch.cuda.is_available() else "cpu",
            "--shifts", str(shifts), "--overlap", str(overlap),
        ]
        if use_float32:
            cmd.append("--float32")
            
        cmd.extend(["-o", wd, input_path])
        
        subprocess.run(cmd, check=True)
        
        if os.path.exists(expected_output):
            # Move out of model folder to be in same dir as input
            final_isolated_wav = os.path.join(wd, f"{base_name}_isolated.wav")
            if os.path.exists(final_isolated_wav): os.remove(final_isolated_wav)
            os.rename(expected_output, final_isolated_wav)
            
            # Clean up the model folder immediately
            try: shutil.rmtree(os.path.join(wd, model))
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

    # Step: Dynamic Preprocessing Pipeline
    # Follow the order specified in args.pipeline (or the default order)
    for step in getattr(args, 'pipeline', []):
        if step == 'cl' and args.cl:
            cl_processed = apply_compression_limiter(
                transcription_source,
                args.output_dir,
                threshold=getattr(args, 'cl_threshold', DEFAULT_CL_THRESHOLD),
                ratio=getattr(args, 'cl_ratio', DEFAULT_CL_RATIO),
                c_attack=getattr(args, 'cl_c_attack', DEFAULT_CL_C_ATTACK),
                c_release=getattr(args, 'cl_c_release', DEFAULT_CL_C_RELEASE),
                makeup=getattr(args, 'cl_makeup', DEFAULT_CL_MAKEUP),
                knee=getattr(args, 'cl_knee', DEFAULT_CL_KNEE),
                l_level_in=getattr(args, 'cl_l_level_in', DEFAULT_CL_L_LEVEL_IN),
                l_level_out=getattr(args, 'cl_l_level_out', DEFAULT_CL_L_LEVEL_OUT),
                l_limit=getattr(args, 'cl_l_limit', DEFAULT_CL_L_LIMIT),
                l_attack=getattr(args, 'cl_l_attack', DEFAULT_CL_L_ATTACK),
                l_release=getattr(args, 'cl_l_release', DEFAULT_CL_L_RELEASE),
                asc=getattr(args, 'cl_asc', DEFAULT_CL_ASC),
                asc_level=getattr(args, 'cl_asc_level', DEFAULT_CL_ASC_LEVEL),
                level=getattr(args, 'cl_auto_level', DEFAULT_CL_AUTO_LEVEL),
                latency=getattr(args, 'cl_latency', DEFAULT_CL_LATENCY),
                enable_compressor=getattr(args, 'cl_compressor', DEFAULT_CL_C_ENABLE),
                enable_limiter=getattr(args, 'cl_limiter', DEFAULT_CL_L_ENABLE)
            )
            if cl_processed and os.path.exists(cl_processed):
                transcription_source = cl_processed
                temp_files_to_cleanup.append(cl_processed)

        elif step == 'enhance' and args.enhance:
            enhanced = preprocess_audio(
                transcription_source, 
                args.output_dir,
                do_normalize=getattr(args, 'enhance_normalize', DEFAULT_ENHANCE_NORMALIZE),
                do_mono=getattr(args, 'enhance_mono', DEFAULT_ENHANCE_MONO),
                frame_len=getattr(args, 'enhance_frame_len', DEFAULT_ENHANCE_FRAME_LEN),
                gaussian=getattr(args, 'enhance_gaussian', DEFAULT_ENHANCE_GAUSSIAN),
                max_gain=getattr(args, 'enhance_max_gain', DEFAULT_ENHANCE_MAX_GAIN),
                peak=getattr(args, 'enhance_peak', DEFAULT_ENHANCE_PEAK)
            )
            if enhanced and os.path.exists(enhanced):
                transcription_source = enhanced
                temp_files_to_cleanup.append(enhanced)
        
        elif step == 'isolate' and args.isolate:
            isolated = isolate_audio_with_demucs(
                transcription_source, 
                args.output_dir,
                model=getattr(args, 'demucs_model', DEFAULT_DEMUCS_MODEL),
                shifts=getattr(args, 'demucs_shifts', DEFAULT_DEMUCS_SHIFTS),
                overlap=getattr(args, 'demucs_overlap', DEFAULT_DEMUCS_OVERLAP),
                use_float32=getattr(args, 'demucs_float32', DEFAULT_DEMUCS_FLOAT32)
            )
            if isolated and os.path.exists(isolated):
                transcription_source = isolated
                temp_files_to_cleanup.append(isolated)

    # 2. Transcribe with Fallbacks
    cleaned_data = None
    
    def try_transcribe(use_vad_filter):
        segments, info = transcription_model.transcribe(
            transcription_source, 
            language=args.lang, 
            task=args.task, 
            
            # VAD Settings
            vad_filter=use_vad_filter, 
            vad_parameters={
                "threshold": args.vad_threshold,
                "min_silence_duration_ms": DEFAULT_MIN_SILENCE_DURATION_WT
            }, 
            
            # Advanced Decoding Settings
            beam_size=args.beam_size,
            best_of=args.best_of,
            patience=args.patience,
            temperature=args.temperature,
            condition_on_previous_text=args.condition_on_previous_text,
            initial_prompt=args.initial_prompt,
            
            # Hallucination Control
            no_speech_threshold=args.no_speech_threshold,
            log_prob_threshold=args.logprob_threshold,
            compression_ratio_threshold=args.compression_ratio_threshold,
            
            word_timestamps=True
        )
        res = {"segments": []}
        
        with tqdm(total=round(info.duration, 2), unit='s', desc="   Whisper", dynamic_ncols=True, leave=False) as pbar:
            for seg in segments:
                res["segments"].append({
                    "start": seg.start, "end": seg.end, "text": seg.text, 
                    "words": [{"start": w.start, "end": w.end, "word": w.word} for w in seg.words] if seg.words else []
                })
                pbar.update(min(seg.end - pbar.n, info.duration - pbar.n))
            pbar.update(info.duration - pbar.n)
            
        return res

    try:
        # Attempt 1: Requested Model + Internal VAD settings
        # 1. Attempt 1: Requested Model + VAD settings
        # Use explicit CLI arg if provided, otherwise use the top-level default
        # Note: We still automatically disable it if enhancement is ON UNLESS explicitly set.
        ensure_model_loaded(args.model)
        vad_to_use = args.vad_filter if args.vad_filter is not None else (False if args.enhance else DEFAULT_VAD_FILTER)
        cleaned_data = try_transcribe(vad_to_use)
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
        # Cleanup Demucs folder
        if args.isolate:
            model = getattr(args, 'demucs_model', DEFAULT_DEMUCS_MODEL)
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            wd = args.output_dir if args.output_dir else os.path.dirname(file_path)
            demucs_folder = os.path.join(wd, model)
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

    parser.add_argument("--use_vad", action="store_true", default=DEFAULT_VAD_ALIGN, help=f"Enable Silero VAD alignment (Default: {'ON' if DEFAULT_VAD_ALIGN else 'OFF'})")
    parser.add_argument("--vad_threshold", type=float, default=DEFAULT_VAD_THRESHOLD, help="VAD threshold (0-1). Lower is more sensitive. Default: 0.5")
    parser.add_argument("--vad_filter", action="store_true", default=None, help="Enable Whisper internal VAD filter")
    parser.add_argument("--no_vad_filter", action="store_false", dest="vad_filter", help="Disable Whisper internal VAD filter")
    
    # Ordered Pipeline Flags
    parser.add_argument("-e", "--enhance", action=PipelineAction, nargs=0, const=True, default=DEFAULT_ENHANCE, help=f"Normalize audio levels (Default: {'ON' if DEFAULT_ENHANCE else 'OFF'})")
    parser.add_argument("-ne", "--no-enhance", action=PipelineAction, nargs=0, const=False, dest="enhance", help="Disable audio normalization")
    
    # Advanced Audio Enhancement Tuning
    parser.add_argument("-en", "--enhance_normalize", action="store_true", default=DEFAULT_ENHANCE_NORMALIZE, help="Enable dynamic normalization")
    parser.add_argument("-nen", "--no_enhance_normalize", action="store_false", dest="enhance_normalize", help="Disable dynamic normalization")
    parser.add_argument("-em", "--enhance_mono", action="store_true", default=DEFAULT_ENHANCE_MONO, help="Downmix to mono")
    parser.add_argument("-nem", "--no_enhance_mono", action="store_false", dest="enhance_mono", help="Disable mono downmix")
    
    parser.add_argument("--enhance_frame_len", type=int, default=DEFAULT_ENHANCE_FRAME_LEN, help=f"Frame length in ms (Default: {DEFAULT_ENHANCE_FRAME_LEN})")
    parser.add_argument("--enhance_gaussian", type=int, default=DEFAULT_ENHANCE_GAUSSIAN, help=f"Gaussian window size (Default: {DEFAULT_ENHANCE_GAUSSIAN})")
    parser.add_argument("--enhance_max_gain", type=float, default=DEFAULT_ENHANCE_MAX_GAIN, help=f"Max gain factor (Default: {DEFAULT_ENHANCE_MAX_GAIN})")
    parser.add_argument("--enhance_peak", type=float, default=DEFAULT_ENHANCE_PEAK, help=f"Target peak volume (Default: {DEFAULT_ENHANCE_PEAK})")
    
    # Ordered Pipeline Flags
    parser.add_argument("-cl", "--compression-limiter", action=PipelineAction, nargs=0, const=True, default=DEFAULT_CL, dest="cl", help=f"Use compression limiter (Default: {'ON' if DEFAULT_CL else 'OFF'})")
    parser.add_argument("-ncl", "--no-compression-limiter", action=PipelineAction, nargs=0, const=False, dest="cl", help="Disable compression limiter")

    # Advanced Compression Limiter Tuning
    # Compressor Tuning
    parser.add_argument("--cl_threshold", type=float, default=DEFAULT_CL_THRESHOLD, help=f"Compressor threshold (Default: {DEFAULT_CL_THRESHOLD})")
    parser.add_argument("--cl_ratio", type=float, default=DEFAULT_CL_RATIO, help=f"Compressor ratio (Default: {DEFAULT_CL_RATIO})")
    parser.add_argument("--cl_c_attack", type=float, default=DEFAULT_CL_C_ATTACK, help=f"Compressor attack ms (Default: {DEFAULT_CL_C_ATTACK})")
    parser.add_argument("--cl_c_release", type=float, default=DEFAULT_CL_C_RELEASE, help=f"Compressor release ms (Default: {DEFAULT_CL_C_RELEASE})")
    parser.add_argument("--cl_makeup", type=float, default=DEFAULT_CL_MAKEUP, help=f"Compressor makeup gain (Default: {DEFAULT_CL_MAKEUP})")
    parser.add_argument("--cl_knee", type=float, default=DEFAULT_CL_KNEE, help=f"Compressor knee (Default: {DEFAULT_CL_KNEE})")
    
    # Limiter Tuning
    parser.add_argument("--cl_l_level_in", type=float, default=DEFAULT_CL_L_LEVEL_IN, help=f"Limiter input gain (Default: {DEFAULT_CL_L_LEVEL_IN})", dest="cl_l_level_in")
    parser.add_argument("--cl_l_level_out", type=float, default=DEFAULT_CL_L_LEVEL_OUT, help=f"Limiter output gain (Default: {DEFAULT_CL_L_LEVEL_OUT})", dest="cl_l_level_out")
    parser.add_argument("--cl_l_limit", type=float, default=DEFAULT_CL_L_LIMIT, help=f"Limiter ceiling (Default: {DEFAULT_CL_L_LIMIT})", dest="cl_l_limit")
    parser.add_argument("--cl_l_attack", type=float, default=DEFAULT_CL_L_ATTACK, help=f"Limiter attack ms (Default: {DEFAULT_CL_L_ATTACK})", dest="cl_l_attack")
    parser.add_argument("--cl_l_release", type=float, default=DEFAULT_CL_L_RELEASE, help=f"Limiter release ms (Default: {DEFAULT_CL_L_RELEASE})", dest="cl_l_release")
    
    parser.add_argument("--cl_asc", action="store_true", default=DEFAULT_CL_ASC, help="Enable Auto Slow Control")
    parser.add_argument("--cl_asc_level", type=float, default=DEFAULT_CL_ASC_LEVEL, help=f"ASC Level (Default: {DEFAULT_CL_ASC_LEVEL})")
    parser.add_argument("--cl_auto_level", action="store_true", default=DEFAULT_CL_AUTO_LEVEL, help="Enable Auto Level")
    parser.add_argument("--no_cl_auto_level", action="store_false", dest="cl_auto_level", help="Disable Auto Level")
    parser.add_argument("--cl_latency", action="store_true", default=DEFAULT_CL_LATENCY, help="Compensate delay")
    
    parser.add_argument("--cl_compressor", action="store_true", default=DEFAULT_CL_C_ENABLE, help="Enable compressor component")
    parser.add_argument("--no_cl_compressor", action="store_false", dest="cl_compressor", help="Disable compressor component")
    parser.add_argument("--cl_limiter", action="store_true", default=DEFAULT_CL_L_ENABLE, help="Enable limiter component")
    parser.add_argument("--no_cl_limiter", action="store_false", dest="cl_limiter", help="Disable limiter component")

    parser.add_argument("-i", "--isolate", action=PipelineAction, nargs=0, const=True, default=DEFAULT_ISOLATE, help=f"Use Demucs to isolate vocals (Default: {'ON' if DEFAULT_ISOLATE else 'OFF'})")
    parser.add_argument("-ni", "--no-isolate", action=PipelineAction, nargs=0, const=False, dest="isolate", help="Disable vocal isolation")
    parser.add_argument("-k", "--keep", action="store_true", help="Keep downloaded audio files (default: delete)")
    
    # Advanced Demucs Tuning
    parser.add_argument("--demucs_model", type=str, default=DEFAULT_DEMUCS_MODEL, help=f"Demucs model (Default: {DEFAULT_DEMUCS_MODEL})")
    parser.add_argument("--demucs_shifts", type=int, default=DEFAULT_DEMUCS_SHIFTS, help=f"Number of shifts (Default: {DEFAULT_DEMUCS_SHIFTS})")
    parser.add_argument("--demucs_overlap", type=float, default=DEFAULT_DEMUCS_OVERLAP, help=f"Overlap (Default: {DEFAULT_DEMUCS_OVERLAP})")
    parser.add_argument("--demucs_float32", action="store_true", default=DEFAULT_DEMUCS_FLOAT32, help=f"Use float32 (Default: {DEFAULT_DEMUCS_FLOAT32})")
    parser.add_argument("--no_demucs_float32", action="store_false", dest="demucs_float32", help="Disable float32 for Demucs")

    # Advanced Whisper CLI Overrides
    parser.add_argument("--beam_size", type=int, default=DEFAULT_BEAM_SIZE)
    parser.add_argument("--best_of", type=int, default=DEFAULT_BEST_OF)
    parser.add_argument("--patience", type=float, default=DEFAULT_PATIENCE)
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    parser.add_argument("--condition_on_previous_text", action="store_true", default=DEFAULT_CONDITION_ON_PREVIOUS_TEXT)
    parser.add_argument("--initial_prompt", type=str, default=DEFAULT_INITIAL_PROMPT)
    parser.add_argument("--no_speech_threshold", type=float, default=DEFAULT_NO_SPEECH_THRESHOLD)
    parser.add_argument("--logprob_threshold", type=float, default=DEFAULT_LOGPROB_THRESHOLD)
    parser.add_argument("--compression_ratio_threshold", type=float, default=DEFAULT_COMPRESSION_RATIO_THRESHOLD)

    # Quick mode flag
    # High Quality mode flag
    parser.add_argument("-hq", "--high-quality", action="store_true", help="High Quality: use large-v3 model, enable enhancement, isolation, and limiter")

    args = parser.parse_args()

    # Apply quick mode settings
    # Apply high-quality mode settings
    if args.high_quality:
        args.model = "large-v3"
        args.use_vad = False
        args.enhance = True
        args.isolate = True
        args.cl = True

    # Finalize pipeline for default behaviors if no flags were passed
    if not hasattr(args, 'pipeline'):
        args.pipeline = []
        if args.cl: args.pipeline.append('cl')
        if args.enhance: args.pipeline.append('enhance')
        if args.isolate: args.pipeline.append('isolate')

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
