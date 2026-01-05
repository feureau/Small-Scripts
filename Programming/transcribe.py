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
        import torch
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
    "small": "small"
}

DEFAULT_MODEL_KEY = "large-v2" # CHANGED
DEFAULT_TASK = "transcribe"
DEFAULT_VAD_THRESHOLD = 0.3

# Global State
transcription_model = None
current_model_path = None
PREFERRED_COMPUTE_TYPE = "auto" 

vad_model = None
vad_utils = None
_ydl_pbar = None

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
        return url.split('?')[0]
    except Exception:
        return url

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
                return final_filename
            else:
                print(f"   ⚠️ Download reported success but file not found.")
                return None
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
                    elif is_text_file(path):
                        try:
                            with open(path, 'r', encoding='utf-8') as f:
                                for line in f:
                                    if line.strip().startswith("http"): urls.add(clean_url(line.strip()))
                        except: pass
    all_items = sorted(list(urls)) + sorted(list(files))
    if not all_items: print("⚠️ No supported media files or URLs found.")
    return all_items

def format_srt_time(seconds: float) -> str:
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = int((seconds - int(seconds)) * 1000)
    return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02},{milliseconds:03}"

# --- Validation & Processing ---
def has_valid_audio_track(file_path: str) -> bool:
    try:
        with av.open(file_path) as container:
            if len(container.streams.audio) > 0: return True
        return False
    except: return False

def extract_audio_to_wav(input_path: str, output_dir: str = None) -> str:
    try:
        wd = output_dir if output_dir else os.path.dirname(input_path)
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        temp_wav = os.path.join(wd, f"{base_name}_base.wav")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", input_path, "-map", "0:a:0", "-ar", "16000", "-ac", "1", temp_wav], check=True)
        return temp_wav
    except: return None

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
            except: pass
            try: os.rmdir(os.path.join(wd, model))
            except: pass
            gc.collect()
            return final_wav
        return None
    except Exception as e:
        print(f"   ⚠️ Demucs Failed: {e}")
        return None

def preprocess_audio(input_path: str, output_dir: str = None) -> str:
    try:
        print(f"   🔊 Enhancing audio (DynAudNorm)...")
        wd = output_dir if output_dir else os.path.dirname(input_path)
        temp_wav = os.path.join(wd, f"{os.path.splitext(os.path.basename(input_path))[0]}_enhanced.wav")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", input_path, "-af", "dynaudnorm=f=200:g=5:m=40:p=0.95", "-ar", "16000", "-ac", "1", temp_wav], check=True)
        return temp_wav
    except Exception as e:
        print(f"   ⚠️ Enhancement Failed: {e}")
        return None

def apply_compression_limiter(input_path: str, output_dir: str = None, **kwargs) -> str:
    try:
        print(f"   🔊 Applying Compression/Limiter...")
        wd = output_dir if output_dir else os.path.dirname(input_path)
        temp_wav = os.path.join(wd, f"{os.path.splitext(os.path.basename(input_path))[0]}_cl.wav")
        filters = [f"acompressor=threshold={kwargs.get('threshold', 0.125)}:ratio={kwargs.get('ratio', 2.0)}:attack=20:release=250:makeup=1", "alimiter=level_in=1:level_out=1:limit=0.99:attack=5:release=50:asc=0:level=1"]
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", input_path, "-af", ",".join(filters), "-ar", "16000", "-ac", "1", temp_wav], check=True)
        return temp_wav
    except Exception as e:
        print(f"   ⚠️ Compression Failed: {e}")
        return None

# --- VAD ---
def load_vad_model():
    global vad_model, vad_utils
    if vad_model is None:
        try:
            vad_model, vad_utils = torch.hub.load(repo_or_dir='snakers4/silero-vad', model='silero_vad', trust_repo=True)
        except Exception: return False
    return True

def detect_true_speech_regions(audio_path: str, threshold=DEFAULT_VAD_THRESHOLD):
    global vad_model, vad_utils
    if not load_vad_model(): return []
    (get_speech_timestamps, _, _, _, _) = vad_utils
    try:
        container = av.open(audio_path)
        audio_stream = container.streams.audio[0]
        resampler = av.AudioResampler(format='fltp', layout='mono', rate=16000)
        frames = []
        for frame in container.decode(audio_stream):
            frame.pts = None
            for rf in resampler.resample(frame):
                frames.append(rf.to_ndarray())
        container.close()
        if not frames: return []
        wav_np = np.concatenate(frames, axis=1)
        wav = torch.from_numpy(wav_np)
        if wav.dim() > 1 and wav.shape[0] == 1: wav = wav.squeeze(0)
        if wav.dim() == 0: return []
        timestamps = get_speech_timestamps(wav, vad_model, threshold=threshold, min_silence_duration_ms=100)
        del wav
        merged = []
        for ts in timestamps:
            start, end = ts['start'] / 16000, ts['end'] / 16000
            if merged and (start - merged[-1][1] <= 0.2): merged[-1][1] = end
            else: merged.append([start, end])
        return merged
    except Exception as e:
        print(f"   ⚠️ VAD Error: {e}")
        return []

def snap_to_vad(word_start, word_end, regions):
    for start, end in regions:
        if max(word_start, start) < min(word_end, end):
            return max(word_start - 0.1, start), min(word_end + 0.1, end)
        if abs(word_start - end) < 0.2: return word_start, word_end 
        if abs(word_end - start) < 0.2: return word_start, word_end
    return word_start, word_end

# --- Processing Logic ---
def ensure_model_loaded(model_alias):
    global transcription_model, current_model_path, PREFERRED_COMPUTE_TYPE
    model_path = MODEL_ALIASES.get(model_alias, model_alias)
    
    # Don't reload if already loaded
    if transcription_model is not None and current_model_path == model_path: return

    if transcription_model is not None:
        transcription_model = None
        gc.collect()
        torch.cuda.empty_cache()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    # Determine Compute Type
    if PREFERRED_COMPUTE_TYPE == "auto":
        compute_type = "float16" if device == "cuda" else "int8"
    else:
        compute_type = PREFERRED_COMPUTE_TYPE

    print(f"🚀 Loading Whisper model '{model_path}' on {device} ({compute_type})...")
    
    try:
        transcription_model = WhisperModel(model_path, device=device, compute_type=compute_type)
        current_model_path = model_path
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
                    return
                except Exception as inner_e:
                    # If int8 also fails, check for corruption again
                    if "brotli" in str(inner_e).lower():
                        print("\n❌ CRITICAL ERROR: Model file is corrupted (detected during int8 fallback).")
                        print(f"   Please delete the HuggingFace cache folder for: {model_path}")
                        sys.exit(1)
                    raise inner_e # Real error
        
        # 3. Unknown Error
        raise e

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
    except: return False

def run_transcription(file_path: str, args: argparse.Namespace) -> tuple[bool, str]:
    global transcription_model
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    final_srt_path = os.path.join(args.output_dir if args.output_dir else os.path.dirname(file_path), f"{base_name}.srt")

    print(f"🎤 Processing: {base_name}")

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

    def try_transcribe(vad_filt):
        segments, info = transcription_model.transcribe(
            transcription_source, language=args.lang, task=args.task,
            vad_filter=vad_filt,
            vad_parameters=dict(min_silence_duration_ms=100, threshold=args.vad_threshold),
            beam_size=args.beam_size, best_of=args.best_of, temperature=args.temperature,
            word_timestamps=True
        )
        res = {"segments": []}
        with tqdm(total=round(info.duration, 2), unit='s', desc="   Whisper", dynamic_ncols=True, leave=False) as pbar:
            for seg in segments:
                res["segments"].append({"start": seg.start, "end": seg.end, "text": seg.text, "words": [{"start": w.start, "end": w.end, "word": w.word} for w in seg.words]})
                pbar.update(seg.end - pbar.n)
            pbar.update(info.duration - pbar.n)
        return res

    try:
        ensure_model_loaded(args.model)
        vad_param = args.vad_filter if args.vad_filter is not None else True
        cleaned_data = try_transcribe(vad_param)
    except Exception as e:
        print(f"   ⚠️  Model Error: {e}")
        # Fallback Logic
        for fb in ["large-v3", "large-v2"]:
            if args.model == fb: continue
            print(f"   ⚠️  Switching to fallback: {fb}")
            try:
                ensure_model_loaded(fb)
                cleaned_data = try_transcribe(True)
                if cleaned_data: break
            except: pass

    if not cleaned_data: return False, "Transcription failed"

    if args.use_vad and not args.isolate:
        print("   🔍 Aligning with Silero VAD...")
        true_regions = detect_true_speech_regions(transcription_source, args.vad_threshold)
        if true_regions:
            c = 0
            for seg in cleaned_data["segments"]:
                for w in seg.get("words", []):
                    old_s = w["start"]
                    w["start"], w["end"] = snap_to_vad(w["start"], w["end"], true_regions)
                    if w["start"] != old_s: c += 1
            print(f"      ↳ Aligned {c} words.")

    success = convert_data_to_srt(cleaned_data, final_srt_path)

    if not args.keep:
        for tmp in temp_files:
            try:
                if os.path.exists(tmp): os.remove(tmp)
            except: pass

    return success, final_srt_path

def main():
    parser = argparse.ArgumentParser(description="Whisper Transcription Ultimate V5")
    parser.add_argument("files", nargs="*", help="Files/URLs to process")
    parser.add_argument("-u", "--url", action="append", help="URLs")
    parser.add_argument("-o", "--output_dir", type=str)
    parser.add_argument("-m", "--model", type=str, default=DEFAULT_MODEL_KEY)
    parser.add_argument("-l", "--lang", type=str)
    parser.add_argument("--task", type=str, default=DEFAULT_TASK)
    parser.add_argument("--precision", type=str, default="auto", choices=["auto", "float16", "int8", "float32"], help="Force compute type")

    parser.add_argument("-hq", "--high-quality", action="store_true", help="Enable large-v3 + isolate + enhance + limiter")
    parser.add_argument("-cl", "--compression-limiter", action=PipelineAction, nargs=0, const=True, dest="cl")
    parser.add_argument("-e", "--enhance", action=PipelineAction, nargs=0, const=True, dest="enhance")
    parser.add_argument("-i", "--isolate", action=PipelineAction, nargs=0, const=True, dest="isolate")
    parser.add_argument("-k", "--keep", action="store_true", help="Keep temp files")
    parser.add_argument("-c", "--clipboard", action="store_true")

    parser.add_argument("--use_vad", action="store_true", default=True)
    parser.add_argument("--vad_threshold", type=float, default=DEFAULT_VAD_THRESHOLD)
    parser.add_argument("--vad_filter", action="store_true", default=None)
    parser.add_argument("--beam_size", type=int, default=5)
    parser.add_argument("--best_of", type=int, default=5)
    parser.add_argument("--temperature", type=float, default=0)
    parser.add_argument("--cl_threshold", type=float, default=0.125)
    parser.add_argument("--cl_ratio", type=float, default=2.0)
    parser.add_argument("--demucs_model", type=str, default="htdemucs_ft")
    parser.add_argument("--demucs_shifts", type=int, default=2)

    args = parser.parse_args()
    
    global PREFERRED_COMPUTE_TYPE
    PREFERRED_COMPUTE_TYPE = args.precision

    if not hasattr(args, 'pipeline'): args.pipeline = []

    if args.high_quality:
        args.model = "large-v3"
        args.isolate = True
        args.enhance = True
        args.cl = True
        args.use_vad = False 
        if 'isolate' not in args.pipeline: args.pipeline.append('isolate')
        if 'enhance' not in args.pipeline: args.pipeline.append('enhance')
        if 'cl' not in args.pipeline: args.pipeline.append('cl')

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
                    if not args.files: sys.exit(1)
            except: pass

    files_to_process = collect_input_files(args.files)
    if not files_to_process: return

    if args.output_dir: os.makedirs(args.output_dir, exist_ok=True)

    print(f"🚀 Starting Batch: {len(files_to_process)} files using {args.model}")
    print(f"   Pipeline: {' -> '.join(args.pipeline) if args.pipeline else 'Direct'}")

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
            torch.cuda.empty_cache()
            
        except KeyboardInterrupt:
            print("\n🛑 Stopped by user."); sys.exit(0)
        except Exception as e:
            print(f"❌ Critical: {e}")

    print(f"\nDone. {success_c}/{len(files_to_process)} successful.")

if __name__ == "__main__":
    main()