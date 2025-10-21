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
nlp = None # Stanza pipeline

SUPPORTED_EXTENSIONS = {".wav", ".mp3", ".flac", ".m4a", ".aac", ".ogg", ".wma", ".mp4", ".mkv", ".mov", ".avi", ".wmv", ".m4v"}

def initialize_stanza():
    """Initializes the Stanza pipeline if not already loaded."""
    global nlp
    if nlp is not None:
        return

    try:
        import stanza
        print("🧠 Initializing Stanza for linguistic phrase splitting...")
        stanza.download('en', processors='tokenize,pos,lemma,depparse', verbose=False)
        nlp = stanza.Pipeline('en', processors='tokenize,pos,lemma,depparse', use_gpu=torch.cuda.is_available())
        print("✅ Stanza initialized.")
    except (ImportError, Exception) as e:
        print(f"⚠️ Could not initialize Stanza, falling back to default splitting. Error: {e}")
        nlp = False

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
                                     base_gap_s: float = 0.20,
                                     orphan_merge_max_s: float = 0.90,
                                     orphan_max_words: int = 2):
    """
    Enhanced phrase-level conversion using a refined cost-based Stanza model.
    Balances grammatical rules, timing, and line length for the most natural subtitles.
    """
    try:
        initialize_stanza()

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

        split_costs = [0] * len(all_words)

        if nlp:
            print("🧠 Using refined cost-based Stanza model for linguistic phrase splitting.")
            full_text = " ".join(w[2] for w in all_words)
            char_to_word_idx = []
            current_pos = 0
            for i, (_, _, word_text) in enumerate(all_words):
                start_char = full_text.find(word_text, current_pos)
                if start_char != -1:
                    end_char = start_char + len(word_text)
                    char_to_word_idx.extend([i] * (end_char - len(char_to_word_idx)))
                    current_pos = end_char

            def get_word_idx(char_pos):
                if char_pos < len(char_to_word_idx):
                    return char_to_word_idx[char_pos]
                return len(all_words) - 1

            doc = nlp(full_text)
            
            # --- Assign costs and benefits to potential split points ---
            for sentence in doc.sentences:
                for word in sentence.words:
                    word_idx = get_word_idx(word.start_char)
                    head_idx = get_word_idx(sentence.words[word.head - 1].start_char) if word.head > 0 else -1

                    # --- Forbidden Splits (Infinite Cost) ---
                    # Never split after prepositions, determiners, possessives, or within compound/fixed expressions.
                    if word.deprel in {'case', 'det', 'nmod:poss', 'fixed', 'compound', 'mwe'}:
                        split_costs[word_idx] = float('inf')
                    # Never split a verb from its direct object.
                    if word.deprel in {'obj', 'iobj'}:
                        if head_idx != -1: split_costs[head_idx] = float('inf')

                    # --- High-Cost Splits (Strongly Discouraged) ---
                    # Penalize splitting after auxiliaries, copulas, or adjectives.
                    if word.deprel in {'aux', 'cop', 'amod'}:
                        split_costs[word_idx] += 150
                    # Penalize splitting a verb from its subject or adverbial modifier.
                    if word.deprel in {'nsubj', 'advmod', 'appos'}:
                        if head_idx != -1: split_costs[head_idx] += 100
                    # Penalize splitting after a relative pronoun to prevent dangling.
                    if word.upos == 'PRON' and word.deprel.startswith('acl'):
                        split_costs[word_idx] += 200

                    # --- Ideal Splits (Benefit) ---
                    # Encourage splitting BEFORE major clause boundaries (markers, conjunctions).
                    if word.deprel in {'mark', 'cc'} or word.deprel.startswith('acl'):
                        if word_idx > 0: split_costs[word_idx - 1] -= 100
                    # Encourage splitting after commas.
                    if word.text == ',' and word.upos == 'PUNCT':
                        split_costs[word_idx] -= 50
        else:
            print("ℹ️ Using default punctuation-based phrase splitting.")

        # --- Final Grouping Loop ---
        phrases = []
        phrase_words = []
        phrase_start, phrase_end, prev_end = None, None, None

        for i, (start, end, text) in enumerate(all_words):
            split_here = False
            if i > 0:
                prev_word_idx = i - 1
                prev_text = all_words[prev_word_idx][2]
                gap = start - prev_end if prev_end is not None else 0
                
                # --- Dynamic Split Decision ---
                current_cost = split_costs[prev_word_idx]
                
                # Add pressure to split as the line gets longer.
                if len(phrase_words) > 7: current_cost -= 30
                if len(phrase_words) > 10: current_cost -= 60
                
                # Add a strong benefit to splitting at significant pauses.
                if gap > 0.5: current_cost -= 100
                elif gap > 0.25: current_cost -= 50
                
                if prev_text.endswith((".", "?", "!")):
                    split_here = True
                elif current_cost < 0:
                    split_here = True

            if split_here and phrase_words:
                phrases.append({'start': phrase_start, 'end': phrase_end, 'words': phrase_words})
                phrase_words, phrase_start = [], None

            if phrase_start is None:
                phrase_start = start
            phrase_end = end
            phrase_words.append(text)
            prev_end = end

        if phrase_words:
            phrases.append({'start': phrase_start, 'end': phrase_end, 'words': phrase_words})

        # Merge short orphans, but not if they end in a comma (likely intentional list items).
        merged_phrases = []
        i = 0
        while i < len(phrases):
            cur = phrases[i]
            if i + 1 < len(phrases):
                nxt = phrases[i + 1]
                gap = nxt['start'] - cur['end']
                if (len(cur['words']) <= orphan_max_words and
                    gap <= orphan_merge_max_s and
                    not cur['words'][-1].strip().endswith((".", "?", "!", ";", ":", ","))):
                    nxt['start'] = min(cur['start'], nxt['start'])
                    nxt['words'] = cur['words'] + nxt['words']
                    nxt['end'] = max(cur['end'], nxt['end'])
                    i += 1
                    continue
            merged_phrases.append(cur)
            i += 1
        
        with open(srt_path, 'w', encoding='utf-8') as f:
            for idx, p in enumerate(merged_phrases, start=1):
                text = ' '.join(p['words']).strip()
                if not text: continue
                f.write(
                    f"{idx}\n"
                    f"{format_srt_time(p['start'])} --> {format_srt_time(p['end'])}\n"
                    f"{text}\n\n"
                )
        print(f"✅ Enhanced phrase-level SRT created: {os.path.basename(srt_path)}")

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