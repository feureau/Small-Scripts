
"""
transcribe.py - Transcription with Netflix-Compliant Phrase Grouping, True VAD, and Recursive File Discovery
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

# --- Configuration ---
DEFAULT_MODEL = "large-v3"
DEFAULT_TASK = "transcribe"
DEFAULT_LANGUAGE = None
DEFAULT_MIN_SILENCE_DURATION_WT = 100 # ms
DEFAULT_MAX_WORD_DURATION = 750       # ms

SUPPORTED_EXTENSIONS = {".wav", ".mp3", ".flac", ".m4a", ".aac", ".ogg", ".wma", ".mp4", ".mkv", ".mov", ".avi", ".wmv", ".m4v"}

transcription_model = None

def is_media_file(filepath: str) -> bool:
    return os.path.splitext(filepath)[1].lower() in SUPPORTED_EXTENSIONS

def collect_input_files(paths_or_patterns):
    """Collect supported media files from patterns or recursively from current directory."""
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

def detect_true_speech_regions(audio_path: str, threshold=0.45, min_silence_ms=120):
    """
    Uses Silero VAD to detect speech. 
    Forces resampling to 16000Hz which Silero strictly requires.
    """
    try:
        # Load Silero VAD from Torch Hub
        model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad', model='silero_vad', trust_repo=True)
        (get_speech_timestamps, _, _, _, _) = utils

        # Load audio using torchaudio
        wav, sr = torchaudio.load(audio_path)
        
        # Resample if necessary (Silero requires 16000Hz)
        if sr != 16000:
            resampler = T.Resample(sr, 16000)
            wav = resampler(wav)
        
        # Downmix to mono if necessary
        if wav.shape[0] > 1:
            wav = wav.mean(dim=0, keepdim=True)

        speech_timestamps = get_speech_timestamps(
            wav, model,
            threshold=threshold,
            min_silence_duration_ms=min_silence_ms,
            window_size_samples=512
        )

        merged = []
        for ts in speech_timestamps:
            start_s = ts['start'] / 16000
            end_s = ts['end'] / 16000
            if not merged:
                merged.append([start_s, end_s])
            else:
                # Merge if gaps are very small (< 0.2s) to prevent jittery word snapping
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
    corrected_count = 0
    for segment in data.get('segments', []):
        for word in segment.get('words', []):
            start, end = word.get('start'), word.get('end')
            if start is not None and end is not None and (end - start) > max_duration_s:
                word['start'] = end - max_duration_s
                corrected_count += 1
    if corrected_count > 0:
        print(f"ℹ️ Corrected {corrected_count} overly long words.")
    return data

def smart_line_break(text: str, max_chars: int):
    """Break text into Netflix-compliant lines while keeping grammatical units together."""
    words = text.split()
    if not words:
        return [""]

    # Simple heuristic: finding the best split point
    mid_point = len(words) // 2
    best_split = mid_point
    best_score = float('inf')

    # Look for split points around the middle
    start_search = max(1, len(words) // 3)
    end_search = min(len(words) - 1, (len(words) * 2) // 3)

    for i in range(start_search, end_search + 1):
        left = ' '.join(words[:i])
        right = ' '.join(words[i:])
        
        if len(left) > max_chars or len(right) > max_chars:
            continue

        score = abs(len(left) - len(right)) # Balance length
        
        # Prefer breaking after punctuation or logical connectors
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
    """
    Optimized snap function. Uses sorted regions to exit early.
    """
    for start, end in regions:
        if end < word_start - 0.2: 
            continue # Region is too early
        if start > word_end + 0.2:
            break # Region is too late, stop searching
            
        # Overlap/proximity check (within 0.15s)
        if (start - 0.15) <= word_start and word_end <= (end + 0.15):
            return max(word_start, start - 0.15), min(word_end, end + 0.15)
            
    return word_start, word_end

def convert_data_to_phrase_level_srt(data: dict, srt_path: str,
                                   max_chars_per_line: int = 42,
                                   max_phrase_duration: float = 7.0):
    """
    Netflix-compliant phrase grouping.
    """
    try:
        all_words = [
            (w['start'], w['end'], w['word'].strip())
            for seg in data.get('segments', [])
            for w in seg.get('words', [])
            if w.get('word', '').strip()
        ]
        if not all_words:
            print("⚠️ No words to convert.")
            return False
        
        all_words.sort(key=lambda x: x[0])

        # Step 1: Initial phrase grouping
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
                if (next_start - end) > 0.8: # Long pause
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

        # Step 2: Write SRT
        os.makedirs(os.path.dirname(srt_path), exist_ok=True)

        with open(srt_path, 'w', encoding='utf-8') as f:
            srt_idx = 1
            previous_end_punctuated = True 

            for phrase in phrases:
                text = ' '.join(phrase['words'])
                # Regex clean: remove space before punctuation
                text = re.sub(r'\s+([.,!?])', r'\1', text)
                
                # Context-aware capitalization
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
        
        print(f"✅ SRT created: {os.path.basename(srt_path)}")
        return True

    except Exception as e:
        print(f"❌ Error in SRT conversion: {e}")
        return False

def run_transcription(file_path: str, args: argparse.Namespace) -> tuple[bool, str]:
    global transcription_model

    try:
        if transcription_model is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            compute_type = "float16" if device == "cuda" else "int8"
            print(f"🚀 Loading Whisper model '{args.model}' on {device}...")
            transcription_model = WhisperModel(args.model, device=device, compute_type=compute_type)

        file_directory = args.output_dir if args.output_dir else os.path.dirname(file_path)
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        final_srt_path = os.path.join(file_directory, f"{base_name}.srt")

        print(f"🎤 Transcribing: {base_name}...")
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
            print("🔍 Running True VAD alignment (Silero)...")
            true_regions = detect_true_speech_regions(file_path)
            if true_regions:
                # Snap words to VAD regions
                for seg in cleaned_data["segments"]:
                    for w in seg.get("words", []):
                        w["start"], w["end"] = snap_to_vad(w["start"], w["end"], true_regions)

        success = convert_data_to_phrase_level_srt(cleaned_data, final_srt_path)
        if success:
            return True, final_srt_path
        else:
            return False, "Subtitle write failed"

    except Exception as e:
        # We catch standard exceptions, but allow KeyboardInterrupt to bubble up
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

    successful_transcriptions = []
    failed_transcriptions = []

    print(f"🚀 Starting processing for {len(files_to_process)} files...")
    print("💡 Press Ctrl+C at any time to stop early and see the summary.\n")

    try:
        for i, file_path in enumerate(files_to_process, 1):
            print(f"🎯 Processing [{i}/{len(files_to_process)}]: {os.path.basename(file_path)}")
            
            # Wrap inner logic to separate user interrupt from file processing errors
            try:
                success, result = run_transcription(file_path, args)
                if success:
                    print(f"✅ Output saved: {result}")
                    successful_transcriptions.append((file_path, result))
                else:
                    print(f"❌ Failed: {file_path} - Reason: {result}")
                    failed_transcriptions.append((file_path, result))
            except KeyboardInterrupt:
                raise # Bubble up to the outer loop to stop everything
            
            print("-" * 50)

    except KeyboardInterrupt:
        print("\n\n🛑 Process cancelled by user [Ctrl+C].")
        print("⏳ Stopping gracefully and generating summary...\n")

    # --- Summary Section ---
    print("\n--- Transcription Summary ---")
    print(f"Total files in queue: {len(files_to_process)}")
    print(f"Successfully processed: {len(successful_transcriptions)}")
    print(f"Failed: {len(failed_transcriptions)}")
    
    skipped = len(files_to_process) - (len(successful_transcriptions) + len(failed_transcriptions))
    if skipped > 0:
        print(f"Skipped/Cancelled: {skipped}")

    if successful_transcriptions:
        print("\n✅ Successful files:")
        for original, output in successful_transcriptions:
            print(f"  - {os.path.basename(original)}")

    if failed_transcriptions:
        print("\n❌ Failed files:")
        for original, error in failed_transcriptions:
            print(f"  - {os.path.basename(original)}: {error}")

    print("\n--- End Summary ---")
    sys.exit(0)

if __name__ == "__main__":
    main()
