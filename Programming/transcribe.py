#!/usr/bin/env python3
"""
================================================================================================
transcribe.py - Advanced Transcription and Diarization with Faster Whisper XXL
================================================================================================

DESCRIPTION:
This script provides a powerful command-line interface (CLI) wrapper for the `faster-whisper-xxl`
transcription tool. It is designed to automate and enhance the process of transcribing audio
and video files by offering a rich set of features, robust error handling, and flexible
output options. It can process individual files, entire directories, or file patterns,
and it streams the transcription progress directly to the console in real-time.

This script has been specifically engineered to solve common and difficult problems with
AI-generated timestamps, such as "lingering" subtitles and words appearing too early,
by implementing an advanced, multi-layered correction strategy.

------------------------------------------------------------------------------------------------
CORE FEATURES:
------------------------------------------------------------------------------------------------
- High-Quality Transcription: Utilizes `large-v3` by default, the best-in-class open-source
  model for transcription accuracy.

- True Word-Level Timestamps: When enabled (-wt), the script generates a subtitle file with
  one word per entry. This is achieved through a sophisticated JSON-to-SRT conversion
  process that provides the highest level of timing granularity.

- Universal VAD Control: Provides a single, powerful VAD silence cutoff flag (-vsc) that
  applies to all transcription modes. This is the primary tool for controlling the timing
  and segmentation of subtitles, allowing users to aggressively fight "lingering" subtitles
  by using a low value (e.g., 150ms) or create more readable sentences with a higher value
  (e.g., 1000ms).

- Advanced Post-Processing: Includes an intelligent "sanity check" (-mwd) that runs after
  transcription in word-level mode. It automatically finds and corrects flawed timestamps
  where a word appears too early before a long pause, a common AI error that VAD alone
  cannot fix.

- Controllable Audio Filters: Allows enabling/disabling audio pre-processing filters
  (--ff_rnndn_xiph, --ff_speechnorm) to troubleshoot timestamp synchronization issues.
  While these filters improve accuracy on noisy audio, they can introduce a slight delay.

- Speaker Diarization, Flexible Input, Multiple Output Formats, and Real-Time Logging.

------------------------------------------------------------------------------------------------
WORKFLOW & PHILOSOPHY: THE TWO-LAYER SOLUTION TO TIMESTAMP ACCURACY
------------------------------------------------------------------------------------------------
The core challenge in automated transcription is the inherent inaccuracy of AI-generated
timestamps, which often results in subtitles that linger too long or appear out of sync.
This script solves this with a two-layer approach:

1. PROACTIVE CONTROL (Pre-processing with VAD):
   The script uses Voice Activity Detection (VAD) as its first line of defense. The `-vsc`
   (VAD Silence Cutoff) flag allows you to tell the VAD how sensitive it should be to
   pauses in speech. By setting a low value (e.g., 150ms), you instruct the VAD to
   "pre-chop" the audio into very small, clean segments whenever it detects a short
   silence. Feeding the AI these smaller chunks dramatically prevents it from "smearing"
   timestamps across silent gaps. This is our preventative care.

2. REACTIVE CORRECTION (Post-processing Sanity Check):
   Sometimes, even with a well-configured VAD, the AI makes a mistake, especially with
   a word that appears just before a long pause. It may create a timestamp that starts
   far too early. The `-mwd` (Max Word Duration) flag is our second line of defense.
   It runs *after* transcription and inspects the data. If it finds a word with an
   impossibly long duration, it intelligently corrects the timestamp by assuming the
   `end` time is the reliable anchor and adjusting the `start` time. This is our
   emergency surgery, fixing the specific errors the VAD couldn't prevent.

This combination of proactive audio segmentation and reactive data correction provides
a robust, state-of-the-art solution to achieving the most accurate timestamps possible.

------------------------------------------------------------------------------------------------
USAGE EXAMPLES:
------------------------------------------------------------------------------------------------
1. For the MOST PRECISE word-by-word subtitles (recommended for editing):
   # This uses the sensitive 150ms VAD default and the post-processing fix.
   python3 transcribe.py -wt "my_video.mp4"

2. For more readable, SENTENCE-LIKE subtitles (recommended for viewing):
   # We override the VAD cutoff with a larger value to prevent line breaks on short pauses.
   python3 transcribe.py -vsc 1000 "my_video.mp4"

3. TROUBLESHOOTING: If all subtitles seem consistently late by a fraction of a second:
   # This disables the audio normalization filter, which can introduce latency.
   python3 transcribe.py -wt --no-ff_speechnorm "my_video.mp4"

4. For word-level subtitles with an even MORE SENSITIVE silence cutoff:
   # This will create new segments after just 100ms of silence.
   python3 transcribe.py -wt -vsc 100 "my_video.mp4"

"""

import sys, os, subprocess, tkinter as tk, argparse, glob, re, json
from tkinter import filedialog

# ==============================================================================================
# --- DEFAULT CONFIGURATION ---
# (Tweak these default values to your liking)
# ==============================================================================================
DEFAULT_MODEL = "large-v3"
DEFAULT_TASK = "transcribe"
DEFAULT_LANGUAGE = None
DEFAULT_ENABLE_DIARIZATION = False

# --- VAD & Timestamp Settings ---
# Universal VAD silence cutoff. Controls how long a pause creates a new segment.
# Applies to BOTH default (segment) mode and word-level (-wt) mode.
DEFAULT_VAD_SILENCE_CUTOFF = 150      # In milliseconds.

# For word-level (-wt) mode only: sanity check to fix early/lingering words.
DEFAULT_MAX_WORD_DURATION = 1500

# --- Formatting Settings (when -wt is NOT used) ---
DEFAULT_SENTENCE_MODE = True
DEFAULT_MAX_LINE_LENGTH = 21

# --- Audio Pre-processing Filters ---
DEFAULT_ENABLE_FF_RNNDN_XIPH = True
DEFAULT_ENABLE_FF_SPEECHNORM = True
# ==============================================================================================

HF_TOKEN = os.getenv("HF_TOKEN")
ENABLE_DIARIZATION_METHOD = "pyannote_v3.1"

# ------------------ FUNCTION DEFINITIONS ------------------ #
def is_media_file(filepath: str) -> bool:
    """Check if the file is a supported media type."""
    SUPPORTED_EXTENSIONS = {".wav", ".mp3", ".flac", ".m4a", ".aac", ".ogg", ".wma",
                            ".mp4", ".mkv", ".mov", ".avi", ".wmv", ".m4v"}
    return os.path.splitext(filepath)[1].lower() in SUPPORTED_EXTENSIONS

def get_files_from_args(args: list) -> list:
    """Process command-line arguments and return a list of media files."""
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

def prompt_user_for_files_or_folder() -> list:
    """Prompt the user to select media files or a folder."""
    root = tk.Tk()
    root.withdraw()
    choice = input("Press [F] for folder, [A] for files, [Q] to quit: ").lower()
    if choice == 'q': sys.exit(0)
    elif choice == 'f':
        folder = filedialog.askdirectory(title="Select Folder")
        return [os.path.join(folder, f) for f in os.listdir(folder) if is_media_file(f)] if folder else []
    elif choice == 'a':
        files = filedialog.askopenfilenames(title="Select Media Files")
        return list(files) if files else []
    else:
        print("Invalid choice. Exiting.")
        sys.exit(0)

def format_srt_time(seconds: float) -> str:
    """Converts a float number of seconds to the SRT time format HH:MM:SS,ms"""
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = int((seconds - int(seconds)) * 1000)
    return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02},{milliseconds:03}"

def post_process_word_timestamps(data: dict, max_duration_ms: int) -> dict:
    """
    Performs a sanity check on word timestamps. If a word's duration is
    impossibly long, it corrects the START time, assuming the END time is
    the more reliable anchor.
    """
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
    """
    Takes a Python dictionary of transcription data and converts it to a
    word-by-word SRT file.
    """
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

def run_whisper_xxl_transcription(
    file_path: str, enable_diarization: bool, language: str, model: str, task: str,
    output_dir: str, sentence: bool, max_line_length: int, word_timestamps: bool,
    vad_silence_cutoff: int, max_word_duration: int, 
    ff_rnndn_xiph: bool, ff_speechnorm: bool
) -> str:
    file_directory = output_dir if output_dir else os.path.dirname(file_path)
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    output_format = "json" if word_timestamps else "srt"
    temp_output_path = os.path.join(file_directory, f"{base_name}.{output_format}")
    final_srt_path = os.path.join(file_directory, f"{base_name}.srt")

    if os.path.exists(temp_output_path): print(f"⚠️ Warning: Intermediate file '{os.path.basename(temp_output_path)}' will be overwritten.")

    command = ["faster-whisper-xxl", file_path, "--model", model, "--output_format", output_format, "--output_dir", file_directory]
    if language: command.extend(["--language", language])
    command.extend(["--task", task])

    # The VAD silence cutoff is now applied universally to all transcription modes.
    print(f"ℹ️ Using universal VAD silence cutoff of {vad_silence_cutoff}ms.")
    command.extend(["--vad_min_silence_duration_ms", str(vad_silence_cutoff)])

    if not word_timestamps:
        if sentence: command.append("--sentence")
        command.extend(["--max_line_width", str(max_line_length)])

    if enable_diarization:
        if not HF_TOKEN: print("❌ Error: Diarization requires the HF_TOKEN environment variable."); return ""
        command.extend(["--diarize", ENABLE_DIARIZATION_METHOD])

    if word_timestamps: command.extend(["--word_timestamps", "True"])
    if ff_rnndn_xiph: command.append("--ff_rnndn_xiph")
    if ff_speechnorm: command.append("--ff_speechnorm")

    print(f"\n🔥 Transcribing: {os.path.basename(file_path)}")
    # print("DEBUG Command:", " ".join(command))
    
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None: break
            if line: print(line.strip())
        if os.path.exists(temp_output_path):
            print(f"\n✅ Transcription output created: {os.path.basename(temp_output_path)}")
            if word_timestamps:
                try:
                    with open(temp_output_path, 'r', encoding='utf-8') as f: transcription_data = json.load(f)
                    cleaned_data = post_process_word_timestamps(transcription_data, max_word_duration)
                    convert_data_to_word_level_srt(cleaned_data, final_srt_path)
                    os.remove(temp_output_path); print(f"ℹ️ Intermediate JSON file removed: {os.path.basename(temp_output_path)}")
                except Exception as e: print(f"❌ Error during post-processing or conversion: {e}"); return ""
            return final_srt_path
        else: print(f"\n❌ Error: Expected transcription output not found: {temp_output_path}"); return ""
    except FileNotFoundError: print("❌ Faster Whisper XXL CLI not found. Please ensure it is installed in your PATH."); sys.exit(1)
    except Exception as e: print(f"❌ Unexpected error during transcription: {e}"); return ""

def convert_srt_to_plaintext(srt_path: str) -> str:
    plaintext_lines = []
    timestamp_pattern = re.compile(r'\d{2}:\d{2}:\d{2}[,\.]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[,\.]\d{3}')
    with open(srt_path, "r", encoding="utf-8", errors="replace") as infile:
        for line in infile:
            line = line.strip()
            if line.isdigit() or timestamp_pattern.match(line) or line == "": continue
            plaintext_lines.append(line)
    return " ".join(plaintext_lines)

def main():
    parser = argparse.ArgumentParser(prog="transcribe.py", description="Advanced Transcription and Diarization with Faster Whisper XXL.", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("files", nargs="*", help="One or more media files, directories, or wildcard patterns.")
    parser.add_argument("-o", "--output_dir", type=str, default=None, help="Directory to save output files.")
    parser.add_argument("--srt", action="store_true", help="Generate an SRT subtitle file.")
    parser.add_argument("--text", action="store_true", help="Generate a plain text file.")
    parser.add_argument("-m", "--model", type=str, default=DEFAULT_MODEL, help="Whisper model to use.")
    parser.add_argument("-l", "--lang", type=str, default=DEFAULT_LANGUAGE, help="Language code (e.g., 'en'). Default is auto-detect.")
    parser.add_argument("--task", type=str, default=DEFAULT_TASK, choices=["transcribe", "translate"])
    parser.add_argument("-d", "--diarization", action="store_true", default=DEFAULT_ENABLE_DIARIZATION, help="Enable speaker diarization.")
    
    # VAD & Timestamp Arguments
    parser.add_argument("-vsc", "--vad_silence_cutoff", type=int, default=DEFAULT_VAD_SILENCE_CUTOFF, help="Universal VAD silence cutoff in ms. Shorter values create more/smaller subtitle segments and can improve accuracy.")
    parser.add_argument("-wt", "--word_timestamps", action="store_true", help="Enable precise word-level timestamps with post-processing.")
    parser.add_argument("-mwd", "--max_word_duration", type=int, default=DEFAULT_MAX_WORD_DURATION, help="Sanity check to cap word duration in ms (used with -wt).")

    # Formatting Arguments
    parser.add_argument("--sentence", dest="sentence", action="store_true", help="Enable sentence splitting (ignored if -wt is used).")
    parser.add_argument("--no-sentence", dest="sentence", action="store_false")
    parser.set_defaults(sentence=DEFAULT_SENTENCE_MODE)
    parser.add_argument("-w", "--width", dest="max_line_length", type=int, default=DEFAULT_MAX_LINE_LENGTH, help="Max characters per line (ignored if -wt is used).")
    
    # Filter Arguments
    parser.add_argument("--ff_rnndn_xiph", dest="ff_rnndn_xiph", action="store_true", help="Enable rnndn-based noise reduction filter.")
    parser.add_argument("--no-ff_rnndn_xiph", dest="ff_rnndn_xiph", action="store_false")
    parser.set_defaults(ff_rnndn_xiph=DEFAULT_ENABLE_FF_RNNDN_XIPH)
    parser.add_argument("--ff_speechnorm", dest="ff_speechnorm", action="store_true", help="Enable speechnorm-based audio normalization filter.")
    parser.add_argument("--no-ff_speechnorm", dest="ff_speechnorm", action="store_false")
    parser.set_defaults(ff_speechnorm=DEFAULT_ENABLE_FF_SPEECHNORM)

    args = parser.parse_args()
    files = get_files_from_args(args.files) if args.files else prompt_user_for_files_or_folder()
    if not files: print("No media files selected or found. Exiting."); sys.exit(0)
    produce_srt = args.srt or (not args.srt and not args.text)
    produce_text = args.text
    for file_path in files:
        srt_path = run_whisper_xxl_transcription(
            file_path=file_path, enable_diarization=args.diarization, language=args.lang,
            model=args.model, task=args.task, output_dir=args.output_dir, sentence=args.sentence,
            max_line_length=args.max_line_length, word_timestamps=args.word_timestamps,
            vad_silence_cutoff=args.vad_silence_cutoff,
            max_word_duration=args.max_word_duration, ff_rnndn_xiph=args.ff_rnndn_xiph,
            ff_speechnorm=args.ff_speechnorm
        )
        if not srt_path: print(f"⚠️ Skipping file due to transcription failure: {os.path.basename(file_path)}"); continue
        if produce_text:
            plain_text = convert_srt_to_plaintext(srt_path)
            txt_path = os.path.splitext(srt_path)[0] + ".txt"
            try:
                with open(txt_path, "w", encoding="utf-8") as f: f.write(plain_text)
                print(f"✅ Plain text output created: {os.path.basename(txt_path)}")
            except Exception as e: print(f"❌ Failed to write plain text file: {e}")
        if not produce_srt and os.path.exists(srt_path):
            try:
                os.remove(srt_path); print(f"ℹ️ Final SRT file removed as only text was requested: {os.path.basename(srt_path)}")
            except Exception as e: print(f"❌ Could not remove final SRT file: {e}")
    print("\n✅ All processing completed!")

if __name__ == "__main__":
    main()