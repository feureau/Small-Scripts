#!/usr/bin/env python3
"""
transcribe_only_xxl.py - Transcription script using Faster Whisper XXL
---------------------------------------------------
- Ensures the output SRT file is saved in the same directory as the video file
- Uses Faster Whisper XXL's CLI instead of unnecessary custom functions
- Proper error handling and logging
"""

import sys
import os
import subprocess
import tkinter as tk
from tkinter import filedialog

# ------------------- CONFIGURATION ------------------- #
WHISPER_MODEL_SIZE = "large-v2" #"large-v3-turbo"  # Change to "large-v3" for better quality
OUTPUT_FORMAT = "srt"  # Can be "json", "txt", "vtt", etc.

# Faster Whisper XXL CLI flags
WHISPER_FLAGS = [
    "--language", "en",
    "--task", "transcribe",                    # speech recognition
    "--sentence",                         # Enables sentence-based splitting
    "--max_comma", "128",             # After this line length, a comma is treated as the end of sentence
    "--max_gap", "0.1",                     # Max gap in seconds between sentences
    #"--max_line_width", "256",            # Max characters per subtitle line
    "--max_line_count", "1",              # Max number of lines per subtitle
    "--ff_rnndn_xiph",
    "--ff_speechnorm",
    "--hallucination_silence_threshold", "1",  # Reduces false positive transcriptions by ignoring long silences
    "--condition_on_previous_text", "False",
    #"--reprompt", "0",
    "--word_timestamps", "True",                 # Enables word-level timestamps for better alignment
    #"--no_speech_strict_lvl", "1"         # Stricter filtering for non-speech segments
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
        arg = os.path.abspath(arg.strip('"').strip("'"))  # Convert to absolute path
        if os.path.exists(arg):
            if os.path.isdir(arg):
                collected_files.extend([os.path.join(arg, f) for f in os.listdir(arg) if is_media_file(f)])
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

def run_whisper_xxl_transcription(file_path: str) -> bool:
    """
    Runs the Faster Whisper XXL CLI with specified flags on the given file.
    Saves the output SRT file in the same directory as the input file.
    """
    file_directory = os.path.dirname(file_path)  # Get the directory where the video file is located
    base_name = os.path.splitext(os.path.basename(file_path))[0]  # Extract filename without extension

    command = [
        "faster-whisper-xxl",   # Replace with the actual CLI command name if different
        file_path,
        "--model", WHISPER_MODEL_SIZE,
        "--task", "transcribe",
        "--output_format", OUTPUT_FORMAT,
        "--output_dir", file_directory  # Ensure output is saved in the same folder as the video
    ] + WHISPER_FLAGS

    print(f"\n🔥 Transcribing: {os.path.basename(file_path)}")
    print(f"📂 Saving subtitles in: {file_directory}")
    
    try:
        # Run the Faster Whisper XXL CLI command
        subprocess.run(command, check=True)
        print(f"✅ Transcription completed for: {os.path.basename(file_path)}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error during transcription of {file_path}: {e}")
        return False
    except FileNotFoundError:
        print("❌ Faster Whisper XXL CLI not found. Please ensure it is installed and in your PATH.")
        sys.exit(1)

# ------------------ MAIN EXECUTION ------------------ #
def main():
    print("\n🎙️  Faster Whisper XXL Transcription Script")

    # Get files from command-line arguments or prompt user for selection
    files = get_files_from_args(sys.argv[1:]) or prompt_user_for_files_or_folder()

    if not files:
        print("No files selected. Exiting.")
        sys.exit(0)

    # Process each file
    for file_path in files:
        success = run_whisper_xxl_transcription(file_path)
        if not success:
            print(f"⚠️ Skipping file due to transcription failure: {file_path}")

    print("\n✅ All processing completed successfully!")

if __name__ == "__main__":
    main()
