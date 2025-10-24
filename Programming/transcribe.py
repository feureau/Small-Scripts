#!/usr/bin/env python3
"""
transcribe.py - Transcription with Netflix-Compliant Phrase Grouping, True VAD, and Recursive File Discovery
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

def smart_line_break(text: str, max_chars: int):
    """Break text into Netflix-compliant lines while keeping grammatical units together."""
    words = text.split()
    
    # First, try to break at sentence boundaries
    sentences = []
    current_sentence = []
    
    for word in words:
        current_sentence.append(word)
        if word.endswith(('.', '?', '!')):
            sentences.append(' '.join(current_sentence))
            current_sentence = []
    
    if current_sentence:
        sentences.append(' '.join(current_sentence))
    
    # If we have multiple sentences, handle each separately
    if len(sentences) > 1:
        all_lines = []
        for sentence in sentences:
            if len(sentence) <= max_chars:
                all_lines.append(sentence)
            else:
                all_lines.extend(break_single_sentence(sentence, max_chars))
        return all_lines
    
    # Single sentence case
    return break_single_sentence(text, max_chars)

def break_single_sentence(sentence: str, max_chars: int):
    """Break a single sentence into Netflix-compliant lines."""
    words = sentence.split()
    
    # Try to find natural break points
    break_points = []
    
    for i, word in enumerate(words[:-1]):
        next_word = words[i + 1]
        
        # Good break points (encourage breaks here)
        if (word.endswith(',') or
            word.lower() in {'and', 'but', 'or', 'so', 'because', 'although'} or
            next_word[0].isupper() and i > 0):  # Likely proper noun or new clause
            break_points.append(i)
    
    # If no natural break points, use middle
    if not break_points:
        mid_point = len(words) // 2
        break_points = [mid_point - 1]  # Break before middle word
    
    # Try each break point
    for break_at in break_points:
        line1 = ' '.join(words[:break_at + 1])
        line2 = ' '.join(words[break_at + 1:])
        
        if len(line1) <= max_chars and len(line2) <= max_chars:
            return [line1, line2]
    
    # If no ideal break found, force break at best available point
    for break_at in range(len(words) - 1, 0, -1):
        line1 = ' '.join(words[:break_at + 1])
        line2 = ' '.join(words[break_at + 1:])
        
        if len(line1) <= max_chars and len(line2) <= max_chars:
            return [line1, line2]
    
    # Last resort: simple midpoint break
    mid_point = len(words) // 2
    line1 = ' '.join(words[:mid_point])
    line2 = ' '.join(words[mid_point:])
    return [line1, line2]

def convert_data_to_phrase_level_srt(data: dict, srt_path: str,
                                   max_chars_per_line: int = 42,
                                   max_phrase_duration: float = 7.0):
    """
    Netflix-compliant phrase grouping that focuses on natural speech patterns.
    """
    try:
        # Collect all words with timestamps
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

        # Step 1: Create initial phrases based on natural speech patterns
        phrases = []
        current_phrase = []
        current_start = None
        
        for i, (start, end, word) in enumerate(all_words):
            if current_start is None:
                current_start = start
            
            current_phrase.append((start, end, word))
            current_end = end
            
            # Check if we should break here
            should_break = False
            
            # Break at strong punctuation
            if word.endswith(('.', '?', '!')):
                should_break = True
            
            # Break at natural pauses (long gaps)
            if i < len(all_words) - 1:
                next_start = all_words[i + 1][0]
                gap = next_start - end
                if gap > 0.8:  # Long pause
                    should_break = True
            
            # Break if phrase is getting too long
            current_text = ' '.join(w[2] for w in current_phrase)
            if len(current_text) > max_chars_per_line * 1.5:  # Allow some overflow
                should_break = True
            
            # Break if duration is too long
            phrase_duration = current_end - current_start
            if phrase_duration > max_phrase_duration:
                should_break = True
            
            if should_break:
                phrases.append({
                    'start': current_start,
                    'end': current_end,
                    'words': [w[2] for w in current_phrase]
                })
                current_phrase = []
                current_start = None
        
        # Add final phrase
        if current_phrase:
            phrases.append({
                'start': current_start,
                'end': current_end,
                'words': [w[2] for w in current_phrase]
            })

        # Step 2: Post-process phrases to fix common issues
        processed_phrases = []
        i = 0
        while i < len(phrases):
            current = phrases[i]
            current_text = ' '.join(current['words'])
            
            # Check if current phrase is incomplete (starts with lowercase or ends with lowercase article/preposition)
            is_incomplete = (
                i < len(phrases) - 1 and
                (current_text[0].islower() or 
                 current['words'][-1].lower() in {'a', 'an', 'the', 'of', 'in', 'on', 'at', 'to', 'for', 'and', 'but'})
            )
            
            if is_incomplete:
                # Try to merge with next phrase
                next_phrase = phrases[i + 1]
                merged_text = current_text + ' ' + ' '.join(next_phrase['words'])
                merged_duration = next_phrase['end'] - current['start']
                
                # Only merge if it makes sense (not too long and grammatically reasonable)
                if (len(merged_text) <= max_chars_per_line * 2 and 
                    merged_duration <= max_phrase_duration * 1.5):
                    merged_phrase = {
                        'start': current['start'],
                        'end': next_phrase['end'],
                        'words': current['words'] + next_phrase['words']
                    }
                    processed_phrases.append(merged_phrase)
                    i += 2
                    continue
            
            processed_phrases.append(current)
            i += 1

        # Step 3: Apply Netflix line breaking and text cleaning
        final_subtitles = []
        for phrase in processed_phrases:
            text = ' '.join(phrase['words'])
            
            # Clean up text
            text = re.sub(r'\s+([.,!?])', r'\1', text)  # Remove spaces before punctuation
            text = text.capitalize()
            
            # Apply Netflix line breaking
            if len(text) <= max_chars_per_line:
                final_subtitles.append({
                    'start': phrase['start'],
                    'end': phrase['end'],
                    'text': text
                })
            else:
                lines = smart_line_break(text, max_chars_per_line)
                final_subtitles.append({
                    'start': phrase['start'],
                    'end': phrase['end'], 
                    'text': '\n'.join(lines)
                })

        # Step 4: Final cleanup - merge very short subtitles
        cleaned_subtitles = []
        i = 0
        while i < len(final_subtitles):
            current = final_subtitles[i]
            
            if i + 1 < len(final_subtitles):
                next_sub = final_subtitles[i + 1]
                current_duration = current['end'] - current['start']
                current_text = current['text'].replace('\n', ' ')
                next_text = next_sub['text'].replace('\n', ' ')
                merged_text = current_text + ' ' + next_text
                
                # Merge if current subtitle is very short and merging makes sense
                should_merge = (
                    current_duration < 2.0 and  # Very short
                    len(merged_text) <= max_chars_per_line * 1.8 and  # Won't be too long
                    not current_text.endswith(('.', '?', '!'))  # Not a complete sentence
                )
                
                if should_merge:
                    cleaned_subtitles.append({
                        'start': current['start'],
                        'end': next_sub['end'],
                        'text': merged_text
                    })
                    i += 2
                    continue
            
            cleaned_subtitles.append(current)
            i += 1

        # Step 5: Write SRT file
        with open(srt_path, 'w', encoding='utf-8') as f:
            for idx, sub in enumerate(cleaned_subtitles, start=1):
                f.write(
                    f"{idx}\n"
                    f"{format_srt_time(sub['start'])} --> {format_srt_time(sub['end'])}\n"
                    f"{sub['text']}\n\n"
                )
        
        print(f"✅ Netflix-compliant SRT created: {os.path.basename(srt_path)}")

    except Exception as e:
        print(f"❌ Error in Netflix phrase conversion: {e}")

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
    parser = argparse.ArgumentParser(description="Transcription with Netflix-compliant phrase grouping and VAD")
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
        print(f"🎯 Processing: {os.path.basename(file_path)}")
        srt_path = run_transcription(file_path, args)
        print(f"✅ Output saved: {srt_path}\n")

if __name__ == "__main__":
    main()