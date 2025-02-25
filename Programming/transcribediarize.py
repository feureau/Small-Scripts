#!/usr/bin/env python3
"""
transcribe_diarize_xxl.py - GPU-optimized version using Faster Whisper XXL and Pyannote.audio
---------------------------------------------------------------------------------------------
Modified to read HuggingFace token from HF_TOKEN environment variable
"""

import sys
import os
import subprocess
import uuid
import warnings
import torch
import tkinter as tk
from tkinter import filedialog
import json

# Pyannote pipeline
from pyannote.audio import Pipeline

# ------------------- CONFIGURATION ------------------- #
# Get token from environment variable
HUGGINGFACE_TOKEN = os.environ.get("HF_TOKEN")
if not HUGGINGFACE_TOKEN:
    raise RuntimeError(
        "HF_TOKEN environment variable not found.\n"
        "1. Create a HuggingFace token at https://huggingface.co/settings/tokens\n"
        "2. Accept model agreements:\n"
        "   - https://huggingface.co/pyannote/speaker-diarization\n"
        "   - https://huggingface.co/pyannote/segmentation\n"
        "3. Set the token in Windows with:\n"
        "   setx HF_TOKEN your_token_here"
    )

WHISPER_MODEL_SIZE = "large-v2"
BEAM_SIZE = 5
PYANNOTE_MODEL_ID = "pyannote/speaker-diarization@2.1"  # Specific versioned model
SUPPORTED_EXTENSIONS = {
    ".wav", ".mp3", ".flac", ".m4a", ".aac", ".ogg", ".wma",
    ".mp4", ".mkv", ".mov", ".avi", ".wmv", ".m4v"
}

# ------------------ GPU ENFORCEMENT ------------------ #
if not torch.cuda.is_available():
    raise RuntimeError("CUDA GPU not available - required for this script")

DEVICE = torch.device("cuda")
torch.cuda.empty_cache()

# ----------------------------------------------------- #

def format_timestamp(seconds: float) -> str:
    """Convert float seconds to SRT time format HH:MM:SS,mmm."""
    ms = int(round((seconds - int(seconds)) * 1000))
    hh = int(seconds // 3600)
    mm = int((seconds % 3600) // 60)
    ss = int(seconds % 60)
    return f"{hh:02}:{mm:02}:{ss:02},{ms:03}"

def is_media_file(filepath: str) -> bool:
    ext = os.path.splitext(filepath)[1].lower()
    return ext in SUPPORTED_EXTENSIONS

def get_files_in_folder(folder_path: str) -> list[str]:
    all_files = []
    for root, _, files in os.walk(folder_path):
        for filename in files:
            filepath = os.path.join(root, filename)
            if is_media_file(filepath):
                all_files.append(filepath)
    return all_files

def extract_audio_to_wav(src_path: str, dst_path: str) -> None:
    print(f"Extracting audio for diarization (ffmpeg) -> {dst_path}")
    command = [
        "ffmpeg", "-y", "-i", src_path,
        "-vn", "-acodec", "pcm_s16le",
        "-ar", "16000", "-ac", "1", dst_path
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        print(f"FFmpeg error: {result.stderr.decode('utf-8')}")
        raise RuntimeError(f"Failed to extract audio to WAV: {dst_path}")
    if not os.path.exists(dst_path):
        raise RuntimeError(f"Failed to extract audio to WAV: {dst_path}")

def transcribe_audio(filepath: str) -> list:
    """
    Transcribes the audio using Faster Whisper XXL CLI.
    Returns a list of tuples: (start_time, end_time, text)
    """
    file_directory = os.path.dirname(filepath)
    base_name = os.path.splitext(os.path.basename(filepath))[0]
    output_format = "json"
    output_file = os.path.join(file_directory, f"{base_name}.json")
    
    # Faster Whisper XXL CLI flags
    whisper_flags = [
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
        "--reprompt", "0",
        "--word_timestamps",                  # Enables word-level timestamps for better alignment
        "--no_speech_strict_lvl", "1"         # Stricter filtering for non-speech segments
        "--output_format", output_format,
        "--output_dir", file_directory
    ]
    
    command = [
        WHISPER_XXL_CLI,
        filepath,
        "--model", WHISPER_MODEL_SIZE,
        "--task", "transcribe"
    ] + whisper_flags
    
    print(f"\n🔥 Transcribing: {os.path.basename(filepath)}")
    print(f"📂 Saving transcription JSON to: {output_file}")
    
    try:
        # Run the Faster Whisper XXL CLI command
        subprocess.run(command, check=True)
        print(f"✅ Transcription completed for: {os.path.basename(filepath)}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error during transcription of {filepath}: {e}")
        return []
    except FileNotFoundError:
        print("❌ Faster Whisper XXL CLI not found. Please ensure it is installed and in your PATH.")
        sys.exit(1)
    
    # Parse the JSON output
    if not os.path.exists(output_file):
        print(f"❌ Transcription JSON file not found: {output_file}")
        return []
    
    try:
        with open(output_file, "r", encoding="utf-8") as f:
            transcription_data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse transcription JSON: {e}")
        return []
    
    segments = []
    for seg in transcription_data.get("segments", []):
        start = seg.get("start", 0.0)
        end = seg.get("end", 0.0)
        text = seg.get("text", "").strip()
        segments.append((start, end, text))
    
    return segments

def diarize_audio(filepath: str, diarization_pipeline) -> "Pipeline":
    ext = os.path.splitext(filepath)[1].lower()
    audio_temp_path = None

    if ext not in {".wav", ".flac", ".ogg"}:
        temp_wav_name = f"pyannote_temp_{uuid.uuid4().hex}.wav"
        audio_temp_path = os.path.join(os.path.dirname(filepath), temp_wav_name)
        try:
            extract_audio_to_wav(filepath, audio_temp_path)
        except RuntimeError as e:
            print(f"Error extracting audio: {e}")
            return None
        audio_path = audio_temp_path
    else:
        audio_path = filepath

    print(f"--- Diarizing: {audio_path} ---")
    try:
        diarization = diarization_pipeline(audio_path)
    except Exception as e:
        print(f"Error during diarization: {e}")
        return None

    print(f"Diarization completed for: {audio_path}")

    # Cleanup temp .wav
    if audio_temp_path and os.path.exists(audio_temp_path):
        os.remove(audio_temp_path)

    return diarization

def combine_transcript_and_diarization(transcript: list, diarization, filepath: str) -> list:
    srt_entries = []
    for i, (start, end, text) in enumerate(transcript, start=1):
        speaker_label = "Unknown"
        for turn, _, speaker_id in diarization.itertracks(yield_label=True):
            if turn.start <= start <= turn.end:
                # Extract numerical part of speaker_id if it's formatted like 'speaker_1'
                speaker_num = speaker_id.split('_')[-1] if '_' in speaker_id else speaker_id
                speaker_label = f"Speaker {speaker_num}"
                break
        srt_entries.append((i, start, end, speaker_label, text))
    return srt_entries

def write_srt(srt_entries: list, output_path: str) -> None:
    with open(output_path, "w", encoding="utf-8") as f:
        for index, start, end, speaker, text in srt_entries:
            f.write(f"{index}\n{format_timestamp(start)} --> {format_timestamp(end)}\n{speaker}: {text.strip()}\n\n")

def get_files_from_args(args: list[str]) -> list[str]:
    collected_files = []
    for arg in args:
        arg = os.path.abspath(arg.strip('"').strip("'"))  # Convert to absolute path
        if os.path.exists(arg):
            if os.path.isdir(arg):
                collected_files.extend(get_files_in_folder(arg))
            elif is_media_file(arg):
                collected_files.append(arg)
        else:
            print(f"Warning: {arg} does not exist, skipping...")
    return collected_files

def prompt_user_for_files_or_folder() -> list[str]:
    root = tk.Tk()
    root.withdraw()
    choice = input("Press [F] for folder, [A] for files, [Q] to quit: ").lower()
    if choice == 'q':
        sys.exit(0)
    elif choice == 'f':
        folder = filedialog.askdirectory(title="Select Folder")
        return get_files_in_folder(folder) if folder else []
    elif choice == 'a':
        files = filedialog.askopenfilenames(title="Select Media Files")
        return list(files) if files else []
    else:
        print("Invalid choice. Exiting.")
        sys.exit(0)

def main():
    warnings.filterwarnings("ignore")

    print(f"\n🎙️  Transcription and Diarization Script")
    print(f"GPU Available: {torch.cuda.is_available()}")
    print(f"Using device: {torch.cuda.get_device_name(0)}\n")

    # File selection
    files = get_files_from_args(sys.argv[1:]) or prompt_user_for_files_or_folder()
    if not files:
        print("No files selected. Exiting.")
        sys.exit(0)

    # Initialize Pyannote pipeline
    try:
        print("🎤 Initializing Pyannote diarization pipeline...")
        diarization_pipeline = Pipeline.from_pretrained(
            PYANNOTE_MODEL_ID,
            use_auth_token=HUGGINGFACE_TOKEN
        ).to(DEVICE)
    except Exception as e:
        print(f"❌ Pyannote initialization failed: {e}")
        sys.exit(1)

    # Processing loop
    for file_path in files:
        print(f"\n🚀 Processing: {os.path.basename(file_path)}")

        # Transcription
        transcript = transcribe_audio(file_path)
        if not transcript:
            print(f"⚠️ Skipping diarization and SRT creation due to transcription failure for {file_path}")
            continue

        # Diarization
        diarization = diarize_audio(file_path, diarization_pipeline)
        if not diarization:
            print(f"⚠️ Skipping SRT creation due to diarization failure for {file_path}")
            continue

        # Combine results
        srt_entries = combine_transcript_and_diarization(transcript, diarization, file_path)

        # Write to SRT
        output_path = os.path.splitext(file_path)[0] + ".srt"
        try:
            write_srt(srt_entries, output_path)
            print(f"✅ Saved subtitles to: {output_path}")
        except Exception as e:
            print(f"❌ Failed to write SRT: {e}")

    print("\n✅ All processing completed successfully!")

if __name__ == "__main__":
    main()
