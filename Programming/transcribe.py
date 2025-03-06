#!/usr/bin/env python3
"""
transcribe_only_xxl.py - Transcription script using Faster Whisper XXL
---------------------------------------------------
- Ensures the output SRT file is saved in the same directory as the video file with a unique timestamp.
- Uses Faster Whisper XXL's CLI instead of unnecessary custom functions.
- Proper error handling and logging.
- Adds support for diarization using pyannote_v3.1 (GPU) only when the -d flag is passed.
- Expects your Hugging Face token to be set in the environment variable HF_TOKEN.
- Streams the transcribed output continuously as it is produced.
- Splits the transcription into one sentence per SRT line using the original settings.
"""

import sys
import os
import subprocess
import tkinter as tk
from tkinter import filedialog
from datetime import datetime

# ------------------- CONFIGURATION ------------------- #
WHISPER_MODEL_SIZE = "large-v2"         # Change to "large-v3" for better quality
OUTPUT_FORMAT = "srt"                   # Can be "json", "txt", "vtt", etc.
ENABLE_DIARIZATION = "pyannote_v3.1"      # Diarization method to use when enabled
# The token should be set in the environment variable HF_TOKEN
HF_TOKEN = os.getenv("HF_TOKEN")         

# Faster Whisper XXL CLI flags (same as original for one sentence per subtitle)
WHISPER_FLAGS = [
    "--language", "en",
    "--task", "transcribe",
    "--sentence",              # Enables sentence-based splitting
    "--max_comma", "128",      # Comma beyond this count ends the sentence
    "--max_gap", "0.1",        # Maximum gap in seconds between sentences
    "--max_line_count", "1",   # One line per subtitle (one sentence per SRT)
    "--ff_rnndn_xiph",
    "--ff_speechnorm",
]

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

def run_whisper_xxl_transcription(file_path: str, enable_diarization: bool) -> bool:
    """
    Runs the Faster Whisper XXL CLI with specified flags on the given file.
    Streams the output continuously to the console.
    Saves the output SRT file in the same directory as the input file with a unique timestamp.
    """
    file_directory = os.path.dirname(file_path)
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"{base_name}_{timestamp}.{OUTPUT_FORMAT}"
    output_path = os.path.join(file_directory, output_filename)

    command = [
        "faster-whisper-xxl",  # Make sure this command is available in your PATH.
        file_path,
        "--model", WHISPER_MODEL_SIZE,
        "--task", "transcribe",
        "--output_format", OUTPUT_FORMAT,
        "--output_dir", file_directory,
    ] + WHISPER_FLAGS

    if enable_diarization:
        command += ["--diarize", ENABLE_DIARIZATION]
    
    # Do not pass any token flag; the CLI should read HF_TOKEN from the environment.
    print(f"\n🔥 Transcribing: {os.path.basename(file_path)}")
    print(f"📂 Expected output file will be renamed to: {output_filename}")

    try:
        process = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
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
            return False
        
        # Rename the output file if it exists (default output is base_name.srt)
        expected_output = os.path.join(file_directory, f"{base_name}.{OUTPUT_FORMAT}")
        if os.path.exists(expected_output):
            os.rename(expected_output, output_path)
            print(f"\n✅ Output file renamed to: {os.path.basename(output_path)}")
        else:
            print(f"\n❌ Expected output file not found: {expected_output}")
        
        return True
    except FileNotFoundError:
        print("❌ Faster Whisper XXL CLI not found. Please ensure it is installed and in your PATH.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error during transcription: {e}")
        return False

# ------------------ MAIN EXECUTION ------------------ #
def main():
    print("\n🎙️  Faster Whisper XXL Transcription Script")

    # Remove the -d flag from arguments before processing file paths.
    args = [arg for arg in sys.argv[1:] if arg != "-d"]
    files = get_files_from_args(args) or prompt_user_for_files_or_folder()
    if not files:
        print("No files selected. Exiting.")
        sys.exit(0)

    # Enable diarization only if the user provided the -d flag.
    enable_diarization = "-d" in sys.argv

    for file_path in files:
        success = run_whisper_xxl_transcription(file_path, enable_diarization)
        if not success:
            print(f"⚠️ Skipping file due to transcription failure: {file_path}")

    print("\n✅ All processing completed successfully!")

if __name__ == "__main__":
    main()
