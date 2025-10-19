#!/usr/bin/env python3
"""
transcribe.py - Transcription with Phrase-Level Grouping, True VAD, Punctuation-Aware Splitting, and Recursive File Discovery
"""

import sys, os, argparse, re, glob, torch
from faster_whisper import WhisperModel
from silero_vad import get_speech_timestamps, read_audio

DEFAULT_MODEL = "large-v3"
DEFAULT_TASK = "transcribe"
DEFAULT_LANGUAGE = None
DEFAULT_MIN_SILENCE_DURATION_WT = 100
DEFAULT_MAX_WORD_DURATION = 750

transcription_model = None

SUPPORTED_EXTENSIONS = {".wav", ".mp3", ".flac", ".m4a", ".aac", ".ogg", ".wma", ".mp4", ".mkv", ".mov", ".avi", ".wmv", ".m4v"}

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

    files = sorted(files)
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
    model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad', model='silero_vad', trust_repo=True)
    (get_speech_timestamps, save_audio, read_audio, VADIterator, collect_chunks) = utils

    wav = read_audio(audio_path)
    sample_rate = 16000
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
        start_s = ts['start'] / sample_rate
        end_s = ts['end'] / sample_rate
        if not merged:
            merged.append([start_s, end_s])
        else:
            if start_s - merged[-1][1] <= 0.18:
                merged[-1][1] = end_s
            else:
                merged.append([start_s, end_s])
    return merged

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

def convert_data_to_phrase_level_srt(data: dict, srt_path: str,
                                     base_gap_s: float = 0.30,
                                     orphan_merge_max_s: float = 0.90,
                                     orphan_max_words: int = 2):
    try:
        all_words = [
            (w['start'], w['end'], w['word'].strip())
            for seg in data.get('segments', [])
            for w in seg.get('words', [])
            if w.get('word', '').strip()
        ]
        if not all_words:
            print("⚠️ No words to convert.")
            return
        all_words.sort(key=lambda x: x[0])

        phrases = []
        phrase_words = []
        phrase_start = None
        phrase_end = None
        prev_end = None
        prev_text = ""

        for start, end, text in all_words:
            gap = start - prev_end if prev_end is not None else 0
            split_here = False

            if prev_end is not None:
                # Determine punctuation-based thresholds
                if prev_text.endswith((",", ";", ":")):
                    threshold = base_gap_s * 0.5
                elif prev_text.endswith((".", "?", "!")):
                    threshold = 0  # force split
                else:
                    threshold = base_gap_s

                # Split either if timing gap exceeds threshold or punctuation forces it
                if gap > threshold or threshold == 0:
                    split_here = True

            if split_here and phrase_words:
                phrases.append({'start': phrase_start, 'end': phrase_end, 'words': phrase_words})
                phrase_words = []
                phrase_start = None

            if phrase_start is None:
                phrase_start = start
            phrase_end = end
            phrase_words.append(text)

            prev_end = end
            prev_text = text

        if phrase_words:
            phrases.append({'start': phrase_start, 'end': phrase_end, 'words': phrase_words})

        # Merge short orphan phrases forward if needed
        merged_phrases = []
        i = 0
        while i < len(phrases):
            cur = phrases[i]
            if i + 1 < len(phrases):
                nxt = phrases[i + 1]
                gap = nxt['start'] - cur['end']
                if (len(cur['words']) <= orphan_max_words and
                    gap <= orphan_merge_max_s and
                    not cur['words'][-1].endswith((",", ".", "?", "!", ";", ":"))):
                    nxt['start'] = min(cur['start'], nxt['start'])
                    nxt['words'] = cur['words'] + nxt['words']
                    nxt['end'] = max(nxt['end'], cur['end'], nxt['end'])
                    i += 1
                    continue
            merged_phrases.append(cur)
            i += 1

        with open(srt_path, 'w', encoding='utf-8') as f:
            for idx, p in enumerate(merged_phrases, start=1):
                text = ' '.join(p['words'])
                f.write(
                    f"{idx}\n"
                    f"{format_srt_time(p['start'])} --> {format_srt_time(p['end'])}\n"
                    f"{text}\n\n"
                )
        print(f"✅ Phrase-level SRT created: {os.path.basename(srt_path)}")

    except Exception as e:
        print(f"❌ Error in phrase conversion: {e}")

def run_transcription(file_path: str, args: argparse.Namespace) -> str:
    global transcription_model

    if transcription_model is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        compute_type = "float16" if device == "cuda" else "int8"
        transcription_model = WhisperModel(args.model, device=device, compute_type=compute_type)
        print(f"✅ Model loaded on {device}.")

    file_directory = args.output_dir if args.output_dir else os.path.dirname(file_path)
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    final_srt_path = os.path.join(file_directory, f"{base_name}.srt")

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
        print("🔍 Running true VAD alignment (tuned)...")
        true_regions = detect_true_speech_regions(file_path)

        def snap_to_vad(word_start, word_end, regions):
            for start, end in regions:
                if (start - 0.15) <= word_start <= (end + 0.15):
                    return max(word_start, start - 0.15), min(word_end, end + 0.15)
            return word_start, word_end

        for seg in cleaned_data["segments"]:
            for w in seg.get("words", []):
                s, e = snap_to_vad(w["start"], w["end"], true_regions)
                w["start"], w["end"] = s, e

    convert_data_to_phrase_level_srt(cleaned_data, final_srt_path)
    return final_srt_path

def main():
    parser = argparse.ArgumentParser(description="Transcription with VAD and punctuation-aware phrase grouping")
    parser.add_argument("files", nargs="*", help="Audio/video files or patterns to transcribe")
    parser.add_argument("-o", "--output_dir", type=str, default=None)
    parser.add_argument("-m", "--model", type=str, default=DEFAULT_MODEL)
    parser.add_argument("-l", "--lang", type=str, default=DEFAULT_LANGUAGE)
    parser.add_argument("--task", type=str, default=DEFAULT_TASK, choices=["transcribe", "translate"])
    parser.add_argument("--use_vad", action="store_true", help="Use true VAD correction.")

    args = parser.parse_args()
    files_to_process = collect_input_files(args.files)

    if not files_to_process:
        sys.exit(0)

    for file_path in files_to_process:
        srt_path = run_transcription(file_path, args)
        print(f"✅ Output saved: {srt_path}")

if __name__ == "__main__":
    main()
