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

------------------------------------------------------------------------------------------------
CORE FEATURES:
------------------------------------------------------------------------------------------------
- High-Quality Transcription: Utilizes the `faster-whisper` library with large models
  (e.g., `large-v2`, `large-v3`) for accurate and efficient transcription.
- Speaker Diarization: Integrates `pyannote.audio` (v3.1) to identify and label different
  speakers in the audio. This requires a GPU and a Hugging Face token.
- Flexible Input: Accepts individual media files, directories, or wildcard patterns
  (e.g., `*.mp4`). An interactive file/folder picker is available if no input is given.
- Multiple Output Formats: Can generate subtitle files (.srt) with timestamps and/or
  plain text files (.txt) without timestamps.
- Customizable Output: Saves output files with a filename matching the input file.
  Users can also specify a custom output directory.
- Real-Time Logging: Streams the live output from the transcription process to the console.
- Advanced Audio Processing: Includes options to enable audio filters for noise reduction
  (`ff_rnndn_xiph`) and speech normalization (`ff_speechnorm`) to improve accuracy.
- Granular Subtitle Formatting: Provides precise control over subtitles, including sentence
  splitting, maximum number of lines, maximum characters per line (`-w`, `--width`), and gap between sentences.

------------------------------------------------------------------------------------------------
PREREQUISITES:
------------------------------------------------------------------------------------------------
1. Python: Version 3.7 or higher.
2. Libraries: `faster-whisper`, `torch`, and `pyannote.audio`.
3. Hugging Face Token: A Hugging Face token is REQUIRED for speaker diarization. It must
   be set as an environment variable named `HF_TOKEN`.

------------------------------------------------------------------------------------------------
INSTALLATION & SETUP:
------------------------------------------------------------------------------------------------
1. Install Python: Ensure you have Python 3.7+ installed.

2. Create a Virtual Environment (Recommended):
   python3 -m venv whisper_env
   source whisper_env/bin/activate  # On Windows, use: whisper_env\\Scripts\\activate

3. Install Required Libraries:
   pip install faster-whisper torch pyannote.audio

4. Set Hugging Face Token:
   You need a Hugging Face account and an access token with 'read' permissions.
   - Go to https://huggingface.co/settings/tokens to get your token.
   - Set it as an environment variable.
     - On Linux/macOS (add to your .bashrc or .zshrc for permanence):
       export HF_TOKEN="your_token_here"
     - On Windows (Command Prompt):
       set HF_TOKEN="your_token_here"
     - On Windows (PowerShell):
       $env:HF_TOKEN="your_token_here"

------------------------------------------------------------------------------------------------
USAGE:
------------------------------------------------------------------------------------------------
Run the script from your terminal.

Syntax:
  python3 transcribe.py [options] [file_or_directory_paths...]

Examples:
  # 1. Transcribe a single video file with default settings (outputs an SRT file).
  python3 transcribe.py my_video.mp4

  # 2. Transcribe with speaker diarization, specifying English language and the large-v3 model.
  python3 transcribe.py -d -l en -m large-v3 my_video.mp4

  # 3. Transcribe an entire folder and output both SRT and plain text files.
  python3 transcribe.py --srt --text /path/to/my/media_folder/

  # 4. Transcribe a file and limit each subtitle line to 21 characters.
  python3 transcribe.py -w 21 my_video.mp4
  #    or using the long flag:
  python3 transcribe.py --width 21 my_video.mp4

  # 5. Translate a file to English and output only a plain text file.
  python3 transcribe.py --task translate --text my_foreign_video.mkv

  # 6. Run without file arguments to open an interactive file/folder selection prompt.
  python3 transcribe.py

------------------------------------------------------------------------------------------------
WORKFLOW:
------------------------------------------------------------------------------------------------
1. The script parses command-line arguments to set transcription parameters.
2. It collects all media files from the provided paths (or interactive prompt).
3. For each file, it builds and executes a command for the `faster-whisper-xxl` CLI tool.
4. It always generates an SRT file as an intermediate step. The output filename will
   match the input filename (e.g., `my_video.mp4` becomes `my_video.srt`).
5. If plain text output (`--text`) is requested, the SRT is converted to a .txt file.
6. If SRT output was NOT explicitly requested (`--srt`), the intermediate SRT file is
   deleted to keep the output directory clean, leaving only the .txt file.

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
DEFAULT_MAX_LINE_LENGTH = 21         # Maximum characters per line
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
    max_line_length: int,
    ff_rnndn_xiph: bool,
    ff_speechnorm: bool,
    produce_srt: bool
) -> str:
    """
    Runs the Faster Whisper XXL CLI with specified flags on the given file.
    Streams the output continuously to the console.
    Saves the output file in the specified output directory (or the file's directory if not provided)
    with a filename matching the input file.
    
    Returns the full path to the generated SRT file if successful, or an empty string if failure.
    
    The 'produce_srt' parameter controls the status messages:
      - If True, the console shows the SRT output file name.
      - If False (i.e. only plaintext is requested), a status message indicates that
        an intermediate SRT will be generated for conversion.
    """
    # Determine output directory: user-specified or the file's directory.
    file_directory = output_dir if output_dir else os.path.dirname(file_path)
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    # The output filename will now match the input filename.
    output_filename = f"{base_name}.srt"
    output_path = os.path.join(file_directory, output_filename)

    # Warn the user if the output file already exists and will be overwritten.
    if os.path.exists(output_path):
        print(f"⚠️ Warning: The output file '{output_filename}' already exists and will be overwritten.")

    # Status update based on requested output.
    if produce_srt:
        print(f"📂 Expected output file: {output_filename}")
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
        "--max_line_width", str(max_line_length),
    ])

    # Audio processing flags
    if ff_rnndn_xiph:
        command.append("--ff_rnndn_xiph")
    if ff_speechnorm:
        command.append("--ff_speechnorm")

    # Diarization support
    if enable_diarization:
        if not HF_TOKEN:
            print("❌ Error: Diarization requires the HF_TOKEN environment variable to be set.")
            print("Please get a token from https://huggingface.co/settings/tokens and set the variable.")
            return ""
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
        
        # New robust success check: the primary condition for success is that the output file exists.
        if os.path.exists(output_path):
            print(f"\n✅ Output file created: {os.path.basename(output_path)}")
            # If the file exists but the exit code was non-zero, print a warning but continue.
            if return_code != 0:
                print(f"⚠️ Warning: The transcription process finished with a non-zero exit code ({return_code}).")
                print("   This might indicate an internal error, but the output file was generated successfully.")
            return output_path
        else:
            # If the output file does not exist, it's a genuine failure.
            print(f"\n❌ Error: Expected output file not found: {output_path}")
            if return_code != 0:
                 print(f"   The process returned non-zero exit code {return_code}")
            return ""

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

# ------------------ MAIN EXECUTION ------------------ #
def main():
    # Use ArgumentDefaultsHelpFormatter to show default values in help message
    parser = argparse.ArgumentParser(
        prog="transcribe.py",
        description="Advanced Transcription and Diarization with Faster Whisper XXL.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        epilog="""
Examples:
  # Transcribe a single video file (outputs SRT by default)
  python3 %(prog)s my_video.mp4

  # Transcribe with speaker diarization and specify English language
  python3 %(prog)s -d -l en my_video.mp4

  # Transcribe a folder and get both SRT and plain text files
  python3 %(prog)s --srt --text /path/to/media/

  # Transcribe and limit subtitle lines to 21 characters
  python3 %(prog)s -w 21 my_video.mp4
"""
    )
    
    # --- Input/Output Arguments ---
    parser.add_argument("files", nargs="*", help="One or more media files, directories, or wildcard patterns to transcribe.")
    parser.add_argument("-o", "--output_dir", type=str, default=None, help="Directory to save output files. (Default: same as input file's directory)")
    parser.add_argument("--srt", action="store_true", help="Generate an SRT subtitle file.")
    parser.add_argument("--text", action="store_true", help="Generate a plain text file.")

    # --- Transcription Model and Task Arguments ---
    parser.add_argument("-m", "--model", type=str, default=DEFAULT_MODEL, help="Whisper model to use (e.g., 'large-v2', 'large-v3').")
    parser.add_argument("-l", "--lang", type=str, default=DEFAULT_LANGUAGE, help="Language code for transcription (e.g., 'en', 'es'). Default is auto-detect.")
    parser.add_argument("--task", type=str, default=DEFAULT_TASK, choices=["transcribe", "translate"], help="Task to perform: transcribe or translate to English.")
    
    # --- Diarization ---
    parser.add_argument("-d", "--diarization", action="store_true", default=DEFAULT_ENABLE_DIARIZATION, help=f"Enable speaker diarization using {ENABLE_DIARIZATION_METHOD} (GPU and HF_TOKEN required).")

    # --- Subtitle Formatting Arguments ---
    parser.add_argument("--sentence", dest="sentence", action="store_true", help="Enable sentence splitting (recommended).")
    parser.add_argument("--no-sentence", dest="sentence", action="store_false", help="Disable sentence splitting.")
    parser.set_defaults(sentence=DEFAULT_SENTENCE)
    parser.add_argument("-c", "--max_comma", type=int, default=DEFAULT_MAX_COMMA, help="Max commas before forcing a sentence split.")
    parser.add_argument("-g", "--max_gap", type=float, default=DEFAULT_MAX_GAP, help="Max gap (in seconds) between words before forcing a sentence split.")
    parser.add_argument("-n", "--max_line_count", type=int, default=DEFAULT_MAX_LINE_COUNT, help="Maximum number of lines per subtitle block.")
    # **UPDATED**: Changed flags to -w and --width for consistency
    parser.add_argument("-w", "--width", dest="max_line_length", type=int, default=DEFAULT_MAX_LINE_LENGTH, help="Maximum number of characters per subtitle line.")
    
    # --- Audio Processing Arguments ---
    parser.add_argument("--ff_rnndn_xiph", dest="ff_rnndn_xiph", action="store_true", help="Enable rnndn-based noise reduction filter.")
    parser.add_argument("--no-ff_rnndn_xiph", dest="ff_rnndn_xiph", action="store_false", help="Disable rnndn-based noise reduction filter.")
    parser.set_defaults(ff_rnndn_xiph=DEFAULT_FF_RNNDN_XIPH)
    parser.add_argument("--ff_speechnorm", dest="ff_speechnorm", action="store_true", help="Enable speechnorm-based audio normalization filter.")
    parser.add_argument("--no-ff_speechnorm", dest="ff_speechnorm", action="store_false", help="Disable speechnorm-based audio normalization filter.")
    parser.set_defaults(ff_speechnorm=DEFAULT_FF_SPEECHNORM)

    args = parser.parse_args()

    files = get_files_from_args(args.files) if args.files else prompt_user_for_files_or_folder()
    if not files:
        print("No media files selected or found. Exiting.")
        sys.exit(0)

    # If neither --srt nor --text is specified, default to producing an SRT file.
    produce_srt = args.srt or (not args.srt and not args.text)
    produce_text = args.text

    for file_path in files:
        # Run transcription, which always generates an SRT file initially.
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
            max_line_length=args.max_line_length,
            ff_rnndn_xiph=args.ff_rnndn_xiph,
            ff_speechnorm=args.ff_speechnorm,
            produce_srt=produce_srt
        )
        if not srt_path:
            print(f"⚠️ Skipping file due to transcription failure: {os.path.basename(file_path)}")
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
        
        # If SRT output is not requested, remove the intermediate SRT file.
        if not produce_srt and os.path.exists(srt_path):
            try:
                os.remove(srt_path)
                print(f"ℹ️ Intermediate SRT file removed: {os.path.basename(srt_path)}")
            except Exception as e:
                print(f"❌ Could not remove intermediate SRT file: {e}")

    print("\n✅ All processing completed!")

if __name__ == "__main__":
    main()