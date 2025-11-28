
"""
transcribe_safe.py - Transcription with Netflix-Compliant Phrase Grouping, True VAD, Recursive File Discovery
Updates:
- Optimized VAD loading (Global)
- Memory leak protection
- GUARANTEED SRT OUTPUT (Creates placeholder if silence)
"""

import sys
import os
import argparse
import re
import glob
import torch
import torchaudio
import torchaudio.transforms as T
from faster_whisper import WhisperModel
import gc

# --- Configuration ---
DEFAULT_MODEL = "large-v3"
DEFAULT_TASK = "transcribe"
DEFAULT_LANGUAGE = None
DEFAULT_MIN_SILENCE_DURATION_WT = 100 # ms
DEFAULT_MAX_WORD_DURATION = 750       # ms

SUPPORTED_EXTENSIONS = {".wav", ".mp3", ".flac", ".m4a", ".aac", ".ogg", ".wma", ".mp4", ".mkv", ".mov", ".avi", ".wmv", ".m4v"}

# Global Models
transcription_model = None
vad_model = None
vad_utils = None

def is_media_file(filepath: str) -> bool:
    return os.path.splitext(filepath)[1].lower() in SUPPORTED_EXTENSIONS

def collect_input_files(paths_or_patterns):
    files = set()
    if not paths_or_patterns:
        print("🔍 Scanning current directory and subfolders for media files...")
        for ext in SUPPORTED_EXTENSIONS:
            for path in glob.glob(f"**/*{ext}", recursive=True):
                if os.path.isfile(path):
                    files.add(os.path.abspath(path))
    else:
        for pattern in paths_or_patterns:
            expanded = glob.glob(pattern, recursive=True)
            for path in expanded:
                if os.path.isfile(path) and is_media_file(path):
                    files.add(os.path.abspath(path))
            if not expanded and os.path.isfile(pattern) and is_media_file(pattern):
                files.add(os.path.abspath(pattern))

    files = sorted(list(files))
    if not files:
        print("⚠️ No supported media files found.")
    else:
        print(f"✅ Found {len(files)} file(s) to process.")
    return files

def format_srt_time(seconds: float) -> str:
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = int((seconds - int(seconds)) * 1000)
    return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02},{milliseconds:03}"

def load_vad_model():
    """Loads Silero VAD once globally."""
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
    
    if not load_vad_model():
        return []

    (get_speech_timestamps, _, _, _, _) = vad_utils

    try:
        # Check file size to prevent OOM
        file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
        if file_size_mb > 500:
            print(f"⚠️ File is large ({file_size_mb:.1f}MB). VAD processing might consume high RAM.")

        wav, sr = torchaudio.load(audio_path)
        
        if sr != 16000:
            resampler = T.Resample(sr, 16000)
            wav = resampler(wav)
        
        if wav.shape[0] > 1:
            wav = wav.mean(dim=0, keepdim=True)

        speech_timestamps = get_speech_timestamps(
            wav, vad_model,
            threshold=threshold,
            min_silence_duration_ms=min_silence_ms,
            window_size_samples=512
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
        print(f"⚠️ VAD Error: {e}. Proceeding without True VAD.")
        return []

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
    if not words:
        return [""]

    mid_point = len(words) // 2
    best_split = mid_point
    best_score = float('inf')

    start_search = max(1, len(words) // 3)
    end_search = min(len(words) - 1, (len(words) * 2) // 3)

    for i in range(start_search, end_search + 1):
        left = ' '.join(words[:i])
        right = ' '.join(words[i:])
        
        if len(left) > max_chars or len(right) > max_chars:
            continue

        score = abs(len(left) - len(right))
        
        word_before = words[i-1].lower()
        if word_before.endswith(','):
            score -= 10
        elif word_before in {'and', 'but', 'or', 'so', 'because'}:
            score -= 5
            
        if score < best_score:
            best_score = score
            best_split = i

    line1 = ' '.join(words[:best_split])
    line2 = ' '.join(words[best_split:])
    return [line1, line2]

def snap_to_vad(word_start, word_end, regions):
    for start, end in regions:
        if end < word_start - 0.2: 
            continue 
        if start > word_end + 0.2:
            break 
            
        if (start - 0.15) <= word_start and word_end <= (end + 0.15):
            return max(word_start, start - 0.15), min(word_end, end + 0.15)
            
    return word_start, word_end

def convert_data_to_phrase_level_srt(data: dict, srt_path: str, max_chars_per_line: int = 42, max_phrase_duration: float = 7.0):
    """
    Converts transcription data to SRT. 
    Guarantees file output even if data is empty.
    """
    try:
        # Prepare output directory
        os.makedirs(os.path.dirname(srt_path), exist_ok=True)

        all_words = [
            (w['start'], w['end'], w['word'].strip())
            for seg in data.get('segments', [])
            for w in seg.get('words', [])
            if w.get('word', '').strip()
        ]
        
        # --- FIX: Handle Empty Transcription ---
        if not all_words:
            print(f"⚠️ No words detected. Creating placeholder SRT at: {os.path.basename(srt_path)}")
            with open(srt_path, 'w', encoding='utf-8') as f:
                # Writes a 1-second hidden subtitle so the file is valid and has timestamps
                f.write("1\n00:00:00,000 --> 00:00:01,000\n[No speech detected]\n\n")
            return True
        # ---------------------------------------
        
        all_words.sort(key=lambda x: x[0])

        phrases = []
        current_phrase = []
        current_start = None
        
        for i, (start, end, word) in enumerate(all_words):
            if current_start is None:
                current_start = start
            
            current_phrase.append((start, end, word))
            current_end = end
            
            should_break = False
            
            if word.endswith(('.', '?', '!')):
                should_break = True
            elif i < len(all_words) - 1:
                next_start = all_words[i + 1][0]
                if (next_start - end) > 0.8: 
                    should_break = True
            
            current_text_len = sum(len(w[2]) for w in current_phrase) + len(current_phrase) - 1
            if current_text_len > max_chars_per_line * 1.5:
                should_break = True
                
            if (current_end - current_start) > max_phrase_duration:
                should_break = True
            
            if should_break:
                phrases.append({
                    'start': current_start,
                    'end': current_end,
                    'words': [w[2] for w in current_phrase]
                })
                current_phrase = []
                current_start = None
        
        if current_phrase:
            phrases.append({
                'start': current_start,
                'end': current_end,
                'words': [w[2] for w in current_phrase]
            })

        with open(srt_path, 'w', encoding='utf-8') as f:
            srt_idx = 1
            previous_end_punctuated = True 

            for phrase in phrases:
                text = ' '.join(phrase['words'])
                text = re.sub(r'\s+([.,!?])', r'\1', text)
                
                if previous_end_punctuated:
                    text = text[:1].upper() + text[1:]
                
                previous_end_punctuated = text.strip().endswith(('.', '?', '!'))

                start_t = format_srt_time(phrase['start'])
                end_t = format_srt_time(phrase['end'])
                
                if len(text) > max_chars_per_line:
                    lines = smart_line_break(text, max_chars_per_line)
                    final_text = '\n'.join(lines)
                else:
                    final_text = text

                f.write(f"{srt_idx}\n{start_t} --> {end_t}\n{final_text}\n\n")
                srt_idx += 1
        return True

    except Exception as e:
        print(f"❌ Error in SRT conversion: {e}")
        # Even on error, try to write a placeholder if the file doesn't exist
        if not os.path.exists(srt_path):
             with open(srt_path, 'w', encoding='utf-8') as f:
                f.write("1\n00:00:00,000 --> 00:00:01,000\n[Error during subtitle generation]\n\n")
        return False

def run_transcription(file_path: str, args: argparse.Namespace) -> tuple[bool, str]:
    global transcription_model

    try:
        if transcription_model is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            compute_type = "float16" if device == "cuda" else "int8"
            print(f"🚀 Loading Whisper model '{args.model}' on {device}...")
            transcription_model = WhisperModel(args.model, device=device, compute_type=compute_type)

        base_name = os.path.splitext(os.path.basename(file_path))[0]
        if args.output_dir:
            final_srt_path = os.path.join(args.output_dir, f"{base_name}.srt")
        else:
            final_srt_path = os.path.splitext(file_path)[0] + ".srt"

        print(f"🎤 Transcribing: {base_name}...")
        
        # We wrap the transcribe call. If it returns nothing, cleaned_data will be empty
        # and convert_data... will handle the placeholder generation.
        segments, info = transcription_model.transcribe(
            file_path,
            language=args.lang,
            task=args.task,
            vad_filter=True, 
            vad_parameters={"min_silence_duration_ms": DEFAULT_MIN_SILENCE_DURATION_WT},
            word_timestamps=True
        )

        results_data = {"segments": []}
        for segment in segments:
            seg_dict = {"start": segment.start, "end": segment.end, "text": segment.text}
            if segment.words:
                seg_dict["words"] = [{"start": w.start, "end": w.end, "word": w.word} for w in segment.words]
            results_data["segments"].append(seg_dict)

        cleaned_data = post_process_word_timestamps(results_data, DEFAULT_MAX_WORD_DURATION)

        if args.use_vad:
            # Only run VAD if we actually have segments, otherwise it's wasted time
            if cleaned_data["segments"]:
                print("🔍 Running True VAD alignment (Silero)...")
                true_regions = detect_true_speech_regions(file_path)
                if true_regions:
                    count = 0
                    for seg in cleaned_data["segments"]:
                        for w in seg.get("words", []):
                            old_s, old_e = w["start"], w["end"]
                            w["start"], w["end"] = snap_to_vad(w["start"], w["end"], true_regions)
                            if w["start"] != old_s or w["end"] != old_e:
                                count += 1
                    print(f"   ↳ Snapped {count} words to VAD regions.")

        success = convert_data_to_phrase_level_srt(cleaned_data, final_srt_path)
        
        del results_data
        gc.collect()
        
        if success:
            return True, final_srt_path
        else:
            return False, "Subtitle write failed"

    except Exception as e:
        return False, str(e)

def main():
    parser = argparse.ArgumentParser(description="Transcription with Netflix-compliant phrase grouping and VAD")
    parser.add_argument("files", nargs="*", help="Audio/video files or patterns to transcribe")
    parser.add_argument("-o", "--output_dir", type=str, default=None)
    parser.add_argument("-m", "--model", type=str, default=DEFAULT_MODEL)
    parser.add_argument("-l", "--lang", type=str, default=DEFAULT_LANGUAGE)
    parser.add_argument("--task", type=str, default=DEFAULT_TASK, choices=["transcribe", "translate"])
    parser.add_argument("--use_vad", action="store_true", help="Use true VAD correction (Silero).")

    args = parser.parse_args()
    files_to_process = collect_input_files(args.files)

    if not files_to_process:
        sys.exit(0)

    if args.output_dir:
        os.makedirs(args.output_dir, exist_ok=True)

    successful_transcriptions = []
    failed_transcriptions = []

    print(f"🚀 Starting processing for {len(files_to_process)} files...")
    print("💡 Press Ctrl+C at any time to stop early and see the summary.\n")

    try:
        for i, file_path in enumerate(files_to_process, 1):
            print(f"🎯 Processing [{i}/{len(files_to_process)}]: {os.path.basename(file_path)}")
            try:
                success, result = run_transcription(file_path, args)
                if success:
                    print(f"✅ Output saved: {result}")
                    successful_transcriptions.append((file_path, result))
                else:
                    print(f"❌ Failed: {file_path} - Reason: {result}")
                    failed_transcriptions.append((file_path, result))
            except KeyboardInterrupt:
                raise 
            print("-" * 50)

    except KeyboardInterrupt:
        print("\n\n🛑 Process cancelled by user [Ctrl+C].")

    print("\n--- Transcription Summary ---")
    print(f"Total files in queue: {len(files_to_process)}")
    print(f"Successfully processed: {len(successful_transcriptions)}")
    print(f"Failed: {len(failed_transcriptions)}")
    
    if successful_transcriptions:
        print("\n✅ Successful files:")
        for original, output in successful_transcriptions:
            print(f"  - {os.path.basename(original)}")

    if failed_transcriptions:
        print("\n❌ Failed files:")
        for original, error in failed_transcriptions:
            print(f"  - {os.path.basename(original)}: {error}")

    sys.exit(0)

if __name__ == "__main__":
    main()
