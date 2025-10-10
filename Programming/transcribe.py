#!/usr/bin/env python3
"""
================================================================================================
transcribe.py - Advanced Transcription and Diarization with Faster Whisper
================================================================================================

DESCRIPTION:
This script provides a powerful command-line interface (CLI) for the `faster-whisper`
transcription library. It is designed to be a dual-purpose tool for both maximum readability
and maximum precision. The default behavior is optimized for READABILITY, creating well-formatted,
sentence-based subtitle entries suitable for viewing. For maximum TIMING PRECISION, an advanced
word-level timestamp mode (-wt) is available.

This script has been specifically engineered to solve common and difficult problems with
AI-generated timestamps, such as "lingering" subtitles and words appearing too early,
by implementing an advanced, multi-layered correction strategy.

This version uses the faster-whisper Python API directly for increased stability and does
not rely on any external CLI subprocesses.

------------------------------------------------------------------------------------------------
CORE FEATURES:
------------------------------------------------------------------------------------------------
- High-Quality Transcription: Utilizes `large-v3` by default, the best-in-class open-source
  model for transcription accuracy.

- Two Distinct Transcription Modes:
  1. Default (Sentence Mode): Creates readable, multi-line subtitle blocks that are
     grouped into logical sentences. This mode is controlled by a VAD silence cutoff
     (-vsc, default 1000ms) to define sentence breaks.
  2. Word-Level Mode (-wt): Generates a subtitle file with one word per entry for
     frame-accurate editing. This mode automatically uses a more sensitive VAD and
     includes a post-processing step to correct AI timestamping errors.

- Universal VAD Control: Provides a single, powerful VAD silence cutoff flag (-vsc) that
  applies to all transcription modes. This is the primary tool for controlling the timing
  and segmentation of subtitles, allowing users to aggressively fight "lingering" subtitles
  by using a low value (e.g., 150ms) or create more readable sentences with a higher value
  (e.g., 1000ms).

- Advanced Post-Processing (-wt mode only): Includes an intelligent sanity check (-mwd) that
  automatically finds and corrects flawed timestamps where a word appears too early
  before a long pause—a common AI error that VAD alone cannot fix.

- Full Formatting Control: Allows customization of line width (-w) and line count (-n) for
  standard subtitles to ensure they are well-formatted for any display.

- Speaker Diarization and Flexible Input.

------------------------------------------------------------------------------------------------
WORKFLOW & PHILOSOPHY: THE TWO-LAYER SOLUTION TO TIMESTAMP ACCURACY
------------------------------------------------------------------------------------------------
1. PROACTIVE CONTROL (Pre-processing with VAD):
   The script uses Voice Activity Detection (VAD) as its first line of defense. The `-vsc`
   (VAD Silence Cutoff) flag allows you to tell the VAD how sensitive it should be to
   pauses in speech. Feeding the AI smaller chunks dramatically prevents it from "smearing"
   timestamps across silent gaps.

2. REACTIVE CORRECTION (Post-processing Sanity Check in -wt mode):
   The `-mwd` (Max Word Duration) flag is our second line of defense.
   It runs *after* transcription and inspects the data. If it finds a word with an
   impossibly long duration, it intelligently corrects the timestamp by assuming the
   `end` time is the reliable anchor and adjusting the `start` time.

This combination of proactive audio segmentation and reactive data correction provides
a robust, state-of-the-art solution to achieving the most accurate timestamps possible.

------------------------------------------------------------------------------------------------
USAGE EXAMPLES:
------------------------------------------------------------------------------------------------
1. For READABLE, SENTENCE-LEVEL subtitles (Default Behavior):
   python3 transcribe.py "my_video.mp4"

2. For the MOST PRECISE word-by-word subtitles:
   python3 transcribe.py -wt "my_video.mp4"

3. For TIGHTER sentence-level subtitles with less lingering:
   python3 transcribe.py -vsc 500 "my_video.mp4"
"""

import sys, os, argparse, glob, re, json, textwrap
from faster_whisper import WhisperModel
import torch

# ==============================================================================================
# --- DEFAULT CONFIGURATION ---
# ==============================================================================================
DEFAULT_MODEL = "large-v3"
DEFAULT_TASK = "transcribe"
DEFAULT_LANGUAGE = None
DEFAULT_ENABLE_DIARIZATION = False
DEFAULT_VAD_SILENCE_CUTOFF = 1000
DEFAULT_MIN_SILENCE_DURATION_WT = 150
DEFAULT_MAX_WORD_DURATION = 1500
DEFAULT_SENTENCE_MODE = True
DEFAULT_MAX_LINE_LENGTH = 42
DEFAULT_MAX_LINE_COUNT = 2
# ==============================================================================================

HF_TOKEN = os.getenv("HF_TOKEN")
transcription_model = None # Global variable to hold the loaded model

def is_media_file(filepath: str) -> bool:
    SUPPORTED_EXTENSIONS = {".wav", ".mp3", ".flac", ".m4a", ".aac", ".ogg", ".wma",
                            ".mp4", ".mkv", ".mov", ".avi", ".wmv", ".m4v"}
    return os.path.splitext(filepath)[1].lower() in SUPPORTED_EXTENSIONS

def get_files_from_args(args: list) -> list:
    collected_files = []
    for arg in args:
        if '*' in arg or '?' in arg:
            expanded_paths = glob.glob(arg)
            if not expanded_paths: print(f"Warning: No files match the pattern {arg}, skipping...")
            for expanded in expanded_paths:
                expanded = os.path.abspath(expanded.strip('"').strip("'"))
                if os.path.exists(expanded):
                    if os.path.isdir(expanded): collected_files.extend([os.path.join(expanded, f) for f in os.listdir(expanded) if is_media_file(f)])
                    elif is_media_file(expanded): collected_files.append(expanded)
                else: print(f"Warning: {expanded} does not exist, skipping...")
        else:
            arg = os.path.abspath(arg.strip('"').strip("'"))
            if os.path.exists(arg):
                if os.path.isdir(arg): collected_files.extend([os.path.join(arg, f) for f in os.listdir(arg) if is_media_file(f)])
                elif is_media_file(arg): collected_files.append(arg)
            else: print(f"Warning: {arg} does not exist, skipping...")
    return collected_files

def scan_current_directory_recursively() -> list:
    """Scans the current working directory and all subdirectories for media files."""
    print("ℹ️ No input files provided. Scanning current directory and subdirectories...")
    media_files = []
    current_directory = os.getcwd()
    for root, _, filenames in os.walk(current_directory):
        for filename in filenames:
            filepath = os.path.join(root, filename)
            if is_media_file(filepath):
                media_files.append(filepath)
    if media_files:
        print(f"✅ Found {len(media_files)} media file(s) to process.")
    else:
        print("⚠️ No media files found in the current directory or its subdirectories.")
    return media_files

def format_srt_time(seconds: float) -> str:
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = int((seconds - int(seconds)) * 1000)
    return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02},{milliseconds:03}"

def post_process_word_timestamps(data: dict, max_duration_ms: int) -> dict:
    max_duration_s = max_duration_ms / 1000.0
    corrected_count = 0
    for segment in data.get('segments', []):
        for word in segment.get('words', []):
            start, end = word.get('start'), word.get('end')
            if start is not None and end is not None:
                if (end - start) > max_duration_s:
                    corrected_count += 1
                    word['start'] = end - max_duration_s
    if corrected_count > 0:
        print(f"ℹ️ Post-processing: Corrected {corrected_count} early/lingering word(s) with durations > {max_duration_ms}ms.")
    return data

def convert_data_to_word_level_srt(data: dict, srt_path: str):
    try:
        with open(srt_path, 'w', encoding='utf-8') as f:
            counter = 1
            for segment in data.get('segments', []):
                for word in segment.get('words', []):
                    start_time, end_time, text = word.get('start'), word.get('end'), word.get('word', '').strip()
                    if start_time is not None and end_time is not None and text:
                        f.write(f"{counter}\n{format_srt_time(start_time)} --> {format_srt_time(end_time)}\n{text}\n\n")
                        counter += 1
        print(f"✅ Word-level SRT file created: {os.path.basename(srt_path)}")
    except Exception as e: print(f"❌ An unexpected error occurred during data to SRT conversion: {e}")

def convert_segments_to_sentence_srt(segments, srt_path, max_line_length, max_line_count):
    """Generates a standard sentence-based SRT file from transcription segments."""
    try:
        with open(srt_path, 'w', encoding='utf-8') as f:
            counter = 1
            for segment in segments:
                start_time = format_srt_time(segment.start)
                end_time = format_srt_time(segment.end)
                text = segment.text.strip()
                
                # Use textwrap to format lines
                wrapped_lines = textwrap.wrap(
                    text,
                    width=max_line_length,
                    expand_tabs=False,
                    replace_whitespace=False,
                    drop_whitespace=True,
                    break_long_words=False,
                    break_on_hyphens=False
                )
                
                # Ensure we don't exceed the max line count
                formatted_text = "\n".join(wrapped_lines[:max_line_count])
                
                f.write(f"{counter}\n{start_time} --> {end_time}\n{formatted_text}\n\n")
                counter += 1
        print(f"✅ Sentence-based SRT file created: {os.path.basename(srt_path)}")
    except Exception as e: print(f"❌ An unexpected error occurred during SRT generation: {e}")

def run_transcription(file_path: str, args: argparse.Namespace) -> str:
    """
    Runs transcription on a single file using the faster-whisper API.
    """
    global transcription_model
    
    # Load the model only if it hasn't been loaded yet
    if transcription_model is None:
        print(f"🔥 Loading Whisper model '{args.model}'...")
        try:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            compute_type = "float16" if device == "cuda" else "int8"
            transcription_model = WhisperModel(args.model, device=device, compute_type=compute_type)
            print(f"✅ Model loaded successfully on device: {device}")
        except Exception as e:
            print(f"❌ Failed to load model: {e}")
            return ""

    file_directory = args.output_dir if args.output_dir else os.path.dirname(file_path)
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    final_srt_path = os.path.join(file_directory, f"{base_name}.srt")

    actual_vad_cutoff = DEFAULT_MIN_SILENCE_DURATION_WT if args.word_timestamps else args.vad_silence_cutoff
    print(f"\n🔥 Transcribing: {os.path.basename(file_path)} (VAD: {actual_vad_cutoff}ms)")

    try:
        diarize_options = {}
        if args.diarization:
            if not HF_TOKEN:
                print("❌ Error: Diarization requires the HF_TOKEN environment variable.")
                return ""
            diarize_options = {"diarize": True, "hf_token": HF_TOKEN}

        segments, info = transcription_model.transcribe(
            file_path,
            language=args.lang,
            task=args.task,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": actual_vad_cutoff},
            word_timestamps=True if args.word_timestamps else False,
            **diarize_options
        )
        
        print(f"✅ Transcription complete. Detected language: {info.language} (Confidence: {info.language_probability:.2f})")

        if args.word_timestamps:
            # Build a dictionary to be compatible with existing post-processing functions
            results_data = {"segments": []}
            for segment in segments:
                seg_dict = {"start": segment.start, "end": segment.end, "text": segment.text}
                if segment.words:
                    seg_dict["words"] = [{"start": w.start, "end": w.end, "word": w.word} for w in segment.words]
                results_data["segments"].append(seg_dict)

            cleaned_data = post_process_word_timestamps(results_data, args.max_word_duration)
            convert_data_to_word_level_srt(cleaned_data, final_srt_path)
        else:
            # For sentence mode, we can directly generate the SRT
            convert_segments_to_sentence_srt(segments, final_srt_path, args.max_line_length, args.max_line_count)
        
        return final_srt_path

    except Exception as e:
        print(f"❌ An unexpected error occurred during transcription: {e}")
        return ""

def convert_srt_to_plaintext(srt_path: str) -> str:
    plaintext_lines = []
    timestamp_pattern = re.compile(r'\d{2}:\d{2}:\d{2}[,\.]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[,\.]\d{3}')
    try:
        with open(srt_path, "r", encoding="utf-8", errors="replace") as infile:
            for line in infile:
                line = line.strip()
                if line.isdigit() or timestamp_pattern.match(line) or line == "": continue
                plaintext_lines.append(line)
    except FileNotFoundError:
        print(f"⚠️ Could not find SRT file to convert to text: {srt_path}")
        return ""
    return " ".join(plaintext_lines)

def main():
    parser = argparse.ArgumentParser(
        prog="transcribe.py", 
        description="Advanced Transcription and Diarization with Faster Whisper. If no files are provided, scans the current directory tree.", 
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("files", nargs="*", help="One or more media files, directories, or wildcard patterns.")
    parser.add_argument("-o", "--output_dir", type=str, default=None, help="Directory to save output files.")
    parser.add_argument("--srt", action="store_true", help="Generate an SRT subtitle file.")
    parser.add_argument("--text", action="store_true", help="Generate a plain text file.")
    parser.add_argument("-m", "--model", type=str, default=DEFAULT_MODEL, help="Whisper model to use.")
    parser.add_argument("-l", "--lang", type=str, default=DEFAULT_LANGUAGE, help="Language code (e.g., 'en'). Default is auto-detect.")
    parser.add_argument("--task", type=str, default=DEFAULT_TASK, choices=["transcribe", "translate"])
    parser.add_argument("-d", "--diarization", action="store_true", default=DEFAULT_ENABLE_DIARIZATION, help="Enable speaker diarization.")
    
    parser.add_argument("-vsc", "--vad_silence_cutoff", type=int, default=DEFAULT_VAD_SILENCE_CUTOFF, help="VAD silence cutoff in ms for standard (segment) mode.")
    parser.add_argument("-wt", "--word_timestamps", action="store_true", help="Enable precise word-level timestamps. Overrides -vsc with a more sensitive internal value and enables post-processing.")
    parser.add_argument("-mwd", "--max_word_duration", type=int, default=DEFAULT_MAX_WORD_DURATION, help="Sanity check to cap word duration in ms (used only with -wt).")

    parser.add_argument("-w", "--width", dest="max_line_length", type=int, default=DEFAULT_MAX_LINE_LENGTH, help="Max characters per line (ignored if -wt is used).")
    parser.add_argument("-n", "--max_line_count", type=int, default=DEFAULT_MAX_LINE_COUNT, help="Max number of lines per subtitle block (ignored if -wt is used).")
    
    args = parser.parse_args()
    
    files = get_files_from_args(args.files) if args.files else scan_current_directory_recursively()
    
    if not files: 
        print("No media files found to process. Exiting.")
        sys.exit(0)
    
    produce_srt = args.srt or (not args.srt and not args.text)
    produce_text = args.text
    
    for file_path in files:
        srt_path = run_transcription(file_path, args)
        
        if not srt_path: 
            print(f"⚠️ Skipping file due to transcription failure: {os.path.basename(file_path)}")
            continue
            
        if produce_text:
            plain_text = convert_srt_to_plaintext(srt_path)
            if plain_text:
                txt_path = os.path.splitext(srt_path)[0] + ".txt"
                try:
                    with open(txt_path, "w", encoding="utf-8") as f: f.write(plain_text)
                    print(f"✅ Plain text output created: {os.path.basename(txt_path)}")
                except Exception as e: 
                    print(f"❌ Failed to write plain text file: {e}")
                
        if not produce_srt and os.path.exists(srt_path):
            try:
                os.remove(srt_path)
                print(f"ℹ️ Final SRT file removed as only text was requested: {os.path.basename(srt_path)}")
            except Exception as e: 
                print(f"❌ Could not remove final SRT file: {e}")
                
    print("\n✅ All processing completed!")

if __name__ == "__main__":
    main()