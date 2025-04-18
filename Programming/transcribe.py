#!/usr/bin/env python3
"""
transcribe_only_xxl.py - Transcription script using Faster Whisper XXL
---------------------------------------------------
- Saves the output (e.g., SRT) in the same directory as the video file with a unique timestamp.
- Uses Faster Whisper XXL's CLI.
- Includes robust error handling and logging.
- Supports optional speaker diarization using pyannote_v3.1 (GPU required) when the -d flag is passed.
- Implements options for model selection, task, language (auto-detect by default), output directory,
  sentence splitting, audio processing enhancements, and output format selection.
- When no output flag is passed, it defaults to SRT.
- Use --srt to output SRT, --text to output plain text (UTF-8, without timestamps), or both.
- Expects your Hugging Face token to be set in the environment variable HF_TOKEN.
- Streams transcribed output continuously as it is produced.
Python 3.7 or higher is required.
python>=3.7

External CLI and libraries:
faster-whisper       # Provides the faster-whisper-xxl CLI used for transcription.
torch                # Required for running Whisper models (and used by faster-whisper).
pyannote.audio       # Required for diarization when using the -d flag.
"""

import sys
import os
import subprocess
import tkinter as tk
from tkinter import filedialog
from datetime import datetime
import argparse
import glob
import re

# ------------------- DEFAULT CONFIGURATION ------------------- #
DEFAULT_MODEL = "large-v2"           # Options: "large-v2", "large-v3"
DEFAULT_TASK = "transcribe"          # Options: "transcribe", "translate"
# The default output will be SRT (unless overridden by output flags)
DEFAULT_ENABLE_DIARIZATION = False   # Diarization disabled by default
DEFAULT_LANGUAGE = None              # None means auto-detect language
DEFAULT_SENTENCE = True              # Sentence splitting enabled by default
DEFAULT_MAX_COMMA = 2                # Maximum comma count before splitting a sentence
DEFAULT_MAX_GAP = 0.1                # Maximum gap (in seconds) between sentences
DEFAULT_MAX_LINE_COUNT = 1           # One line per subtitle
DEFAULT_FF_RNNDN_XIPH = True         # Audio processing flag enabled by default
DEFAULT_FF_SPEECHNORM = True         # Audio processing flag enabled by default

# Fixed diarization method
ENABLE_DIARIZATION_METHOD = "pyannote_v3.1"

# The token should be set in the environment variable HF_TOKEN
HF_TOKEN = os.getenv("HF_TOKEN")         

# ------------------ FUNCTION DEFINITIONS ------------------ #
def is_media_file(filepath: str) -> bool:
    """Check if the file is a supported media type."""
    SUPPORTED_EXTENSIONS = {".wav", ".mp3", ".flac", ".m4a", ".aac", ".ogg", ".wma",
                            ".mp4", ".mkv", ".mov", ".avi", ".wmv", ".m4v"}
    return os.path.splitext(filepath)[1].lower() in SUPPORTED_EXTENSIONS

def get_files_from_args(args: list) -> list:
    """Process command-line arguments and return a list of media files.
    
    This function now expands wildcards automatically using glob.
    """
    collected_files = []
    for arg in args:
        # Check if the argument contains wildcard characters
        if '*' in arg or '?' in arg:
            expanded_paths = glob.glob(arg)
            if not expanded_paths:
                print(f"Warning: No files match the pattern {arg}, skipping...")
            for expanded in expanded_paths:
                expanded = os.path.abspath(expanded.strip('"').strip("'"))
                if os.path.exists(expanded):
                    if os.path.isdir(expanded):
                        collected_files.extend(
                            [os.path.join(expanded, f) for f in os.listdir(expanded) if is_media_file(f)]
                        )
                    elif is_media_file(expanded):
                        collected_files.append(expanded)
                else:
                    print(f"Warning: {expanded} does not exist, skipping...")
        else:
            arg = os.path.abspath(arg.strip('"').strip("'"))
            if os.path.exists(arg):
                if os.path.isdir(arg):
                    collected_files.extend(
                        [os.path.join(arg, f) for f in os.listdir(arg) if is_media_file(f)]
                    )
                elif is_media_file(arg):
                    collected_files.append(arg)
            else:
                print(f"Warning: {arg} does not exist, skipping...")
    return collected_files

def prompt_user_for_files_or_folder() -> list:
    """Prompt the user to select media files or a folder."""
    root = tk.Tk()
    root.withdraw()
    choice = input("Press [F] for folder, [A] for files, [Q] to quit: ").lower()
    if choice == 'q':
        sys.exit(0)
    elif choice == 'f':
        folder = filedialog.askdirectory(title="Select Folder")
        return [os.path.join(folder, f) for f in os.listdir(folder) if is_media_file(f)] if folder else []
    elif choice == 'a':
        files = filedialog.askopenfilenames(title="Select Media Files")
        return list(files) if files else []
    else:
        print("Invalid choice. Exiting.")
        sys.exit(0)

def run_whisper_xxl_transcription(
    file_path: str,
    enable_diarization: bool,
    language: str,
    model: str,
    task: str,
    output_dir: str,
    sentence: bool,
    max_comma: int,
    max_gap: float,
    max_line_count: int,
    ff_rnndn_xiph: bool,
    ff_speechnorm: bool,
    produce_srt: bool
) -> str:
    """
    Runs the Faster Whisper XXL CLI with specified flags on the given file.
    Streams the output continuously to the console.
    Saves the output file in the specified output directory (or the file's directory if not provided)
    with a unique timestamp.
    
    Returns the full path to the generated SRT file if successful, or an empty string if failure.
    
    The 'produce_srt' parameter controls the status messages:
      - If True, the console shows the SRT output file name.
      - If False (i.e. only plaintext is requested), a status message indicates that
        an intermediate SRT will be generated for conversion.
    """
    # Determine output directory: user-specified or the file's directory.
    file_directory = output_dir if output_dir else os.path.dirname(file_path)
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # We always generate SRT as intermediate output.
    output_filename = f"{base_name}_{timestamp}.srt"
    output_path = os.path.join(file_directory, output_filename)

    # Status update based on requested output.
    if produce_srt:
        print(f"📂 Expected output file will be renamed to: {output_filename}")
    else:
        print("📂 Transcription will generate an intermediate SRT file which will be converted to plain text output.")

    # Build the command for transcription
    command = [
        "faster-whisper-xxl",  # Ensure this command is available in your PATH.
        file_path,
        "--model", model,
    ]
    # Add language flag if provided; otherwise, auto-detection is assumed.
    if language:
        command.extend(["--language", language])
    command.extend([
        "--task", task,
        "--output_format", "srt",  # Always output SRT for further processing.
        "--output_dir", file_directory,
    ])

    # Sentence splitting and formatting options
    if sentence:
        command.append("--sentence")
    command.extend([
        "--max_comma", str(max_comma),
        "--max_gap", str(max_gap),
        "--max_line_count", str(max_line_count),
    ])

    # Audio processing flags
    if ff_rnndn_xiph:
        command.append("--ff_rnndn_xiph")
    if ff_speechnorm:
        command.append("--ff_speechnorm")

    # Diarization support
    if enable_diarization:
        command.extend(["--diarize", ENABLE_DIARIZATION_METHOD])
    
    print(f"\n🔥 Transcribing: {os.path.basename(file_path)}")
    # Uncomment the line below for debugging the full command:
    # print("DEBUG Command:", " ".join(command))

    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",       # Specify UTF-8 encoding
            errors="replace"        # Replace problematic characters
        )
        # Stream output line-by-line as it's produced
        while True:
            line = process.stdout.readline()
            if line == "" and process.poll() is not None:
                break
            if line:
                print(line, end="")
        return_code = process.poll()
        if return_code != 0:
            print(f"\n❌ Error: Process returned non-zero exit code {return_code}")
            return ""
        
        # Rename the output file if it exists (default output is base_name.srt)
        expected_output = os.path.join(file_directory, f"{base_name}.srt")
        if os.path.exists(expected_output):
            os.rename(expected_output, output_path)
            print(f"\n✅ Output file renamed to: {os.path.basename(output_path)}")
        else:
            print(f"\n❌ Expected output file not found: {expected_output}")
            return ""
        
        return output_path
    except FileNotFoundError:
        print("❌ Faster Whisper XXL CLI not found. Please ensure it is installed and in your PATH.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error during transcription: {e}")
        return ""

def convert_srt_to_plaintext(srt_path: str) -> str:
    """
    Converts an SRT file into plain text by stripping out line numbers,
    timestamps, and blank lines.
    
    Returns the plain text content.
    """
    plaintext_lines = []
    timestamp_pattern = re.compile(r'\d{2}:\d{2}:\d{2}[,\.]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[,\.]\d{3}')
    with open(srt_path, "r", encoding="utf-8", errors="replace") as infile:
        for line in infile:
            line = line.strip()
            # Skip index lines (only digits) and timestamp lines
            if line.isdigit() or timestamp_pattern.match(line) or line == "":
                continue
            plaintext_lines.append(line)
    return "\n".join(plaintext_lines)

def print_help_message():
    """Print the help message detailing the script usage and options."""
    default_lang = DEFAULT_LANGUAGE if DEFAULT_LANGUAGE is not None else "Auto-detect"
    help_text = f"""
Usage: transcribe_only_xxl.py [options] [files or directories]

Options:
  -h, --help                Show this help message and exit.
  -d, --diarization         Enable diarization using {ENABLE_DIARIZATION_METHOD} (GPU required). (Default: Disabled)
  -l, --lang LANGUAGE       Specify language code for transcription (e.g., "en", "es"). 
                            Default: {default_lang}
  -m, --model MODEL         Specify model size (e.g., "large-v2", "large-v3"). (Default: {DEFAULT_MODEL})
  --task TASK               Specify task: transcribe or translate. (Default: {DEFAULT_TASK})
  -o, --output_dir DIRECTORY
                            Specify output directory. (Default: same as input file's directory)
  --srt                     Output SRT file. (Default if no output flag is provided)
  --text                    Output plaintext file (UTF-8, without timestamps).
  --sentence                Enable sentence splitting. (Default: Enabled)
  --no-sentence             Disable sentence splitting.
  -c, --max_comma COUNT     Maximum number of commas before splitting a sentence. (Default: {DEFAULT_MAX_COMMA})
  -g, --max_gap GAP         Maximum gap in seconds between sentences. (Default: {DEFAULT_MAX_GAP})
  -n, --max_line_count COUNT
                            Maximum number of lines per subtitle. (Default: {DEFAULT_MAX_LINE_COUNT})
  -x, --ff_rnndn_xiph       Enable ff_rnndn_xiph audio processing flag. (Default: Enabled)
  -X, --no-ff_rnndn_xiph    Disable ff_rnndn_xiph.
  -p, --ff_speechnorm       Enable ff_speechnorm audio processing flag. (Default: Enabled)
  -P, --no-ff_speechnorm    Disable ff_speechnorm.

Examples:
  python3 transcribe_only_xxl.py myvideo.mp4
  python3 transcribe_only_xxl.py --diarization --lang en --model large-v3 myvideo.mp4
  python3 transcribe_only_xxl.py --text myvideo.mp4
  python3 transcribe_only_xxl.py --srt --text /path/to/directory
    """
    print(help_text)

# ------------------ MAIN EXECUTION ------------------ #
def main():
    parser = argparse.ArgumentParser(add_help=False)
    # Help flag
    parser.add_argument("-h", "--help", action="store_true", help="Show help message and exit")
    # Diarization flag
    parser.add_argument("-d", "--diarization", action="store_true", help="Enable diarization using pyannote_v3.1 (GPU required)")
    # Language override with short flag -l
    parser.add_argument("-l", "--lang", type=str, default=DEFAULT_LANGUAGE, help="Specify language code for transcription. Default is auto-detect.")
    # Model selection with short flag -m
    parser.add_argument("-m", "--model", type=str, default=DEFAULT_MODEL, help=f"Specify model size (e.g., 'large-v2', 'large-v3'). (Default: {DEFAULT_MODEL})")
    # Task specification with --task (note: not to be confused with --text output flag)
    parser.add_argument("--task", type=str, default=DEFAULT_TASK, help=f"Specify task: transcribe or translate. (Default: {DEFAULT_TASK})")
    # Output directory override with short flag -o
    parser.add_argument("-o", "--output_dir", type=str, default=None, help="Specify output directory. (Default: same as input file's directory)")
    # New output format flags: --srt and --text
    parser.add_argument("-s", "--srt", action="store_true", help="Output SRT file.")
    parser.add_argument("-t", "--text", action="store_true", help="Output plaintext file (without timestamps).")
    # Sentence splitting: use long flags to avoid conflict with --srt flag
    parser.add_argument("--sentence", dest="sentence", action="store_true", help="Enable sentence splitting. (Default: Enabled)")
    parser.add_argument("--no-sentence", dest="sentence", action="store_false", help="Disable sentence splitting.")
    parser.set_defaults(sentence=DEFAULT_SENTENCE)
    # Sentence splitting parameters with short flags -c, -g, -n
    parser.add_argument("-c", "--max_comma", type=int, default=DEFAULT_MAX_COMMA, help=f"Maximum number of commas before splitting a sentence. (Default: {DEFAULT_MAX_COMMA})")
    parser.add_argument("-g", "--max_gap", type=float, default=DEFAULT_MAX_GAP, help=f"Maximum gap in seconds between sentences. (Default: {DEFAULT_MAX_GAP})")
    parser.add_argument("-n", "--max_line_count", type=int, default=DEFAULT_MAX_LINE_COUNT, help=f"Maximum number of lines per subtitle. (Default: {DEFAULT_MAX_LINE_COUNT})")
    # Audio processing flags with short flags -x/-X and -p/-P
    parser.add_argument("-x", "--ff_rnndn_xiph", dest="ff_rnndn_xiph", action="store_true", help="Enable ff_rnndn_xiph audio processing flag. (Default: Enabled)")
    parser.add_argument("-X", "--no-ff_rnndn_xiph", dest="ff_rnndn_xiph", action="store_false", help="Disable ff_rnndn_xiph.")
    parser.set_defaults(ff_rnndn_xiph=DEFAULT_FF_RNNDN_XIPH)
    parser.add_argument("-p", "--ff_speechnorm", dest="ff_speechnorm", action="store_true", help="Enable ff_speechnorm audio processing flag. (Default: Enabled)")
    parser.add_argument("-P", "--no-ff_speechnorm", dest="ff_speechnorm", action="store_false", help="Disable ff_speechnorm.")
    parser.set_defaults(ff_speechnorm=DEFAULT_FF_SPEECHNORM)
    # Positional arguments for files and directories
    parser.add_argument("files", nargs="*", help="Media files or directories to transcribe")
    args = parser.parse_args()

    if args.help:
        print_help_message()
        sys.exit(0)

    files = get_files_from_args(args.files) if args.files else prompt_user_for_files_or_folder()
    if not files:
        print("No files selected. Exiting.")
        sys.exit(0)

    # Determine output flags:
    # Default is to output SRT if neither flag is provided.
    produce_srt = args.srt or (not args.srt and not args.text)
    produce_text = args.text

    for file_path in files:
        # Run transcription (always generates SRT)
        srt_path = run_whisper_xxl_transcription(
            file_path=file_path,
            enable_diarization=args.diarization,
            language=args.lang,
            model=args.model,
            task=args.task,
            output_dir=args.output_dir,
            sentence=args.sentence,
            max_comma=args.max_comma,
            max_gap=args.max_gap,
            max_line_count=args.max_line_count,
            ff_rnndn_xiph=args.ff_rnndn_xiph,
            ff_speechnorm=args.ff_speechnorm,
            produce_srt=produce_srt
        )
        if not srt_path:
            print(f"⚠️ Skipping file due to transcription failure: {file_path}")
            continue

        # If plain text output is requested, convert the SRT file.
        if produce_text:
            plain_text = convert_srt_to_plaintext(srt_path)
            base, _ = os.path.splitext(srt_path)
            txt_path = base + ".txt"
            try:
                with open(txt_path, "w", encoding="utf-8") as txt_file:
                    txt_file.write(plain_text)
                print(f"✅ Plain text output created: {os.path.basename(txt_path)}")
            except Exception as e:
                print(f"❌ Failed to write plain text file: {e}")
        
        # If SRT output is not requested (i.e. only plain text was desired), remove the SRT file.
        if not produce_srt:
            try:
                os.remove(srt_path)
                print(f"ℹ️ Intermediate SRT file removed as only plain text was requested.")
            except Exception as e:
                print(f"❌ Could not remove intermediate SRT file: {e}")

    print("\n✅ All processing completed successfully!")

if __name__ == "__main__":
    main()
