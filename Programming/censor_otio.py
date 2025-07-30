# -*- coding: utf-8 -*-
"""
================================================================================
 Automated Video Editor via Transcription and OTIO
================================================================================

- Version: 2.0
- Author: Gemini
- Last Updated: 2025-07-27

--------------------------------------------------------------------------------
 High-Level Purpose
--------------------------------------------------------------------------------
This script automates the tedious parts of video editing by programmatically
finding and marking sections for removal based on transcribed audio content.
Instead of re-encoding a new video file, it generates a professional edit
decision list (EDL) using the OpenTimelineIO (OTIO) standard. This file can be
imported into most Non-Linear Editing software (NLEs) like DaVinci Resolve,
Final Cut Pro, or Adobe Premiere Pro.

--------------------------------------------------------------------------------
 Core Features
--------------------------------------------------------------------------------
- GPU-Accelerated Transcription: Uses 'faster-whisper' with CUDA to rapidly
  transcribe video audio with word-level timestamps.
- Profanity Censorship: Automatically identifies and marks profane words or
  entire sentences for removal.
- Silence Removal: Detects and marks long pauses or silent sections for cutting.
- OTIO Export: Generates an edit file (defaulting to .fcpxml) that instructs
  an NLE how to assemble the final cut from the original media.
- Non-Destructive: The original video files are never modified.
- Caching System: Saves transcriptions to a temporary folder to make subsequent
  runs on the same file nearly instantaneous.
- Detailed Logging: Creates a human-readable log file for each video,
  documenting every decision made.

--------------------------------------------------------------------------------
 Requirements
--------------------------------------------------------------------------------
1.  Python 3.8+

2.  Required Python Packages:
    You can install all required packages with pip:
    pip install scikit-learn alt-profanity-check faster-whisper ffmpeg-python opentimelineio opentimelineio-contrib

3.  NVIDIA GPU with CUDA:
    This script is heavily optimized for an NVIDIA GPU. You MUST install
    PyTorch with CUDA support separately. Follow the official instructions on
    the PyTorch website: https://pytorch.org/get-started/locally/

4.  FFmpeg:
    FFmpeg must be installed and accessible in your system's PATH. For best
    results, use a recent, full build of FFmpeg that includes the common 'aac'
    audio encoder.

--------------------------------------------------------------------------------
 How to Use (Command Line)
--------------------------------------------------------------------------------
Run the script from your terminal, pointing it to your video files.

-   Process specific files:
    python your_script_name.py "video 1.mp4" "my video.mov"

-   Process all MP4 files in the current directory (using wildcards):
    python your_script_name.py *.mp4

-   Choose a different transcription model for higher accuracy (at the cost of speed):
    python your_script_name.py *.mp4 --model medium

-   Change censorship to cut the entire sentence instead of just the word:
    python your_script_name.py *.mp4 --sentence

-   Disable silence cutting:
    python your_script_name.py *.mp4 --no-silence

-   Export to a different format, like EDL or AAF:
    python your_script_name.py *.mp4 --edl
    python your_script_name.py *.mp4 --aaf

--------------------------------------------------------------------------------
 Workflow Explained (What the Script Does)
--------------------------------------------------------------------------------
1.  Setup: Creates two directories: `edited_output` (for final edit lists and
    logs) and `script_temp` (for intermediate files).

2.  Pre-processing (Clean): For each video, it first creates a standardized copy
    in `script_temp`. This step normalizes audio and ensures the container is
    compatible, preventing errors during transcription.

3.  Transcription & Caching: It transcribes the cleaned video's audio. The full
    result (with word timestamps) is saved as a `.json` file in `script_temp`.
    If this cache file already exists, this step is skipped.

4.  Analysis: The script reviews the transcription and builds a list of time
    ranges to cut based on your chosen censorship level and silence settings.

5.  OTIO Timeline Generation: It constructs a new timeline in memory. Instead of
    adding the 'cut' segments, it adds the 'keep' segments—the parts of the
    video that were NOT flagged for removal.

6.  Export Edit List: This OTIO timeline is then saved to a file in the
    `edited_output` directory in your chosen format (e.g., .fcpxml).

--------------------------------------------------------------------------------
 How to Use the Output File (in DaVinci Resolve)
--------------------------------------------------------------------------------
1.  IMPORTANT: Do NOT delete the `script_temp` directory. The generated edit
    file points directly to the cleaned video file inside it.

2.  Open DaVinci Resolve and your project.

3.  Go to the Media Pool. Right-click and choose "Timelines" -> "Import" ->
    "AAF, EDL, XML...".

4.  Navigate to the `edited_output` folder and select the generated file
    (e.g., `my_video_edited.fcpxml`).

5.  Resolve will open a dialog box. Usually, the default settings are fine.
    Click "OK".

6.  A new timeline will appear in your Media Pool. Double-click it to open it.
    You will see the edited video, with all the cuts applied, ready for further
    editing, color grading, or export. The timeline is linked to the media in
    the `script_temp` folder.

================================================================================
"""

# NOTE: Required Python packages (install with pip)
# pip install scikit-learn alt-profanity-check faster-whisper ffmpeg-python opentimelineio opentimelineio-contrib
# NOTE: You must also install PyTorch with CUDA support separately if not already done.
# NOTE: For best results, ensure your FFmpeg build includes the 'aac' audio encoder.

import sys
import os
import glob
import torch
import argparse
import shutil
import logging
import datetime
import ffmpeg
import json
import pathlib
from collections import namedtuple
import opentimelineio as otio


# This list contains the specific words to be censored.
# You can add or remove words here. They should be lowercase.
PROFANE_WORDS = {
    "fuck", "fucking", "shit", "bitch", "cunt", "asshole", "motherfucker"
}

def clean_video(input_path, temp_dir):
    """Creates a clean, standardized copy of the video using ffmpeg-python with CUDA decoding."""
    print(f"  Cleaning '{os.path.basename(input_path)}' with ffmpeg-python (CUDA decoding enabled)...")
    output_path = os.path.join(temp_dir, os.path.basename(input_path))

    try:
        # Use CUDA for hardware-accelerated decoding
        stream = ffmpeg.input(input_path, **{'hwaccel': 'cuda'})
        
        video_stream = stream['v:0']
        audio_stream = stream['a:0']
        processed_audio = audio_stream.filter('loudnorm', I=-16, TP=-1.5, LRA=7)

        ffmpeg.output(
            video_stream,
            processed_audio,
            output_path,
            **{'c:v': 'copy'}, # Copy the video stream as-is since we only changed audio
            **{'c:a': 'aac'},
            dn=None,
            map_metadata=-1,
            map_chapters=-1
        ).overwrite_output().run(capture_stdout=True, capture_stderr=True)

        print(f"  Successfully cleaned. Using temporary file for processing.")
        return output_path

    except ffmpeg.Error as e:
        print("FATAL: ffmpeg-python failed during cleaning.")
        raise RuntimeError(f"FFmpeg failed with stderr:\n{e.stderr.decode('utf-8')}")

# Helper functions and objects for caching transcription data.
Word = namedtuple('Word', ['start', 'end', 'word'])
Segment = namedtuple('Segment', ['start', 'end', 'text', 'words'])

def save_transcription_cache(data, cache_path):
    """Saves the detailed transcription data to a JSON file."""
    serializable_data = []
    for segment in data:
        seg_dict = {
            'start': segment.start,
            'end': segment.end,
            'text': segment.text,
            'words': [{'start': w.start, 'end': w.end, 'word': w.word} for w in segment.words] if hasattr(segment, 'words') and segment.words else []
        }
        serializable_data.append(seg_dict)
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(serializable_data, f, indent=2)

def load_transcription_cache(cache_path):
    """Loads and reconstructs transcription data from a JSON file."""
    with open(cache_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    reconstructed_segments = []
    for seg_dict in data:
        words = [Word(w['start'], w['end'], w['word']) for w in seg_dict['words']]
        reconstructed_segments.append(Segment(seg_dict['start'], seg_dict['end'], seg_dict['text'], words))
    return reconstructed_segments


def merge_intervals(intervals):
    """Merges overlapping or adjacent time intervals into a single block."""
    if not intervals: return []
    intervals.sort(key=lambda x: x[0])
    merged = [intervals[0]]
    for current_start, current_end in intervals[1:]:
        last_start, last_end = merged[-1]
        if current_start <= last_end:
            merged[-1] = (last_start, max(last_end, current_end))
        else:
            merged.append((current_start, current_end))
    return merged

def setup_logger(name, log_file, level=logging.INFO):
    """Function to setup a logger for a specific video's log file."""
    handler = logging.FileHandler(log_file, mode='w')
    handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))

    logger = logging.getLogger(name)
    logger.setLevel(level)
    if logger.hasHandlers():
        logger.handlers.clear()
    logger.addHandler(handler)
    return logger

def format_srt_timestamp(seconds):
    """Converts seconds (float) to an SRT timestamp string 'HH:MM:SS,ms'."""
    td = datetime.timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = td.microseconds // 1000
    return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"

def generate_srt_file(segments, output_path):
    """Generates an SRT subtitle file from a list of Whisper segments."""
    with open(output_path, 'w', encoding='utf-8') as srt_file:
        for i, segment in enumerate(segments, 1):
            start_time = format_srt_timestamp(segment.start)
            end_time = format_srt_timestamp(segment.end)
            text = segment.text.strip()
            
            srt_file.write(f"{i}\n")
            srt_file.write(f"{start_time} --> {end_time}\n")
            srt_file.write(f"{text}\n\n")

def process_video(processing_path, original_path, model, args, output_dir, temp_dir):
    """Processes a single video file to generate a censorship/silence edit list (OTIO)."""
    
    base_name = os.path.splitext(os.path.basename(original_path))[0]
    log_path = os.path.join(output_dir, f"{base_name}.log")
    logger = setup_logger(base_name, log_path)

    transcription_cache_path = os.path.join(temp_dir, f"{base_name}_transcription.json")

    try:
        print(f"\nProcessing: {os.path.basename(original_path)}")
        logger.info(f"--- Starting processing for {original_path} ---")
        
        result_segments = []
        if os.path.exists(transcription_cache_path):
            print("  Found existing transcription cache. Loading from file...")
            logger.info("Loading transcription from cache.")
            result_segments = load_transcription_cache(transcription_cache_path)
            print("  Successfully loaded transcription from cache.")
        else:
            print("  Transcribing with faster-whisper (this may take a while)...")
            logger.info("No cache found. Starting new transcription.")
            segments_iterator, info = model.transcribe(processing_path, word_timestamps=True)
            
            lang_info = f"Detected language '{info.language}' with probability {info.language_probability:.2f}"
            print(f"  {lang_info}")
            logger.info(lang_info)
            
            result_segments = list(segments_iterator)

            print("  Saving transcription to cache for future runs...")
            save_transcription_cache(result_segments, transcription_cache_path)
            logger.info(f"Saved transcription cache to {transcription_cache_path}")

        print("--- Real-Time Transcription Log ---")
        logger.info("--- Real-Time Transcription Log ---")

        for segment in result_segments:
            line = f"[{segment.start:0>7.2f}s -> {segment.end:0>7.2f}s] {segment.text.strip()}"
            print(line)
            logger.info(line)

        print("--- Transcription Complete ---")
        logger.info("--- Transcription Complete ---")

        srt_path = os.path.join(output_dir, f"{base_name}.srt")
        generate_srt_file(result_segments, srt_path)
        srt_saved_msg = f"Saved transcription to: {srt_path}"
        print(f"  {srt_saved_msg}")
        logger.info(srt_saved_msg)
        
        segments_to_cut = []

        if args.censor_level == 'word':
            print("  Checking for profanity (word-level)...")
            logger.info("Checking for profanity (word-level)...")
            for segment in result_segments:
                if not hasattr(segment, 'words') or not segment.words: continue
                for word in segment.words:
                    clean_word = word.word.strip().lower().strip('.,!?-')
                    if clean_word in PROFANE_WORDS:
                        log_msg = f"CENSOR WORD: '{word.word}' at [{word.start:.2f}s -> {word.end:.2f}s]"
                        print(f"  {log_msg}")
                        logger.info(log_msg)
                        segments_to_cut.append((word.start, word.end))

        elif args.censor_level == 'hybrid':
            print("  Checking for profanity (hybrid mode)...")
            logger.info("Checking for profanity (hybrid mode)...")
            for segment in result_segments:
                text = segment.text.strip()
                if not text or not hasattr(segment, 'words') or not segment.words: continue
                # The predict_prob function expects a list of strings
                prob = predict_prob([text])[0]
                if prob >= args.threshold:
                    log_msg_sentence = f"SENTENCE FLAGGED: '{text}' (score: {prob:.2f}). Checking for specific words..."
                    print(f"  {log_msg_sentence}")
                    logger.info(log_msg_sentence)
                    for word in segment.words:
                        clean_word = word.word.strip().lower().strip('.,!?-')
                        if clean_word in PROFANE_WORDS:
                            log_msg_word = f"  -> CENSORING WORD: '{word.word}' at [{word.start:.2f}s -> {word.end:.2f}s]"
                            print(log_msg_word)
                            logger.info(log_msg_word)
                            segments_to_cut.append((word.start, word.end))

        else: # 'sentence' level
            print("  Checking for profanity (sentence-level)...")
            logger.info("Checking for profanity (sentence-level)...")
            for segment in result_segments:
                text = segment.text.strip()
                if not text: continue
                prob = predict_prob([text])[0]
                if prob >= args.threshold:
                    log_msg = f"CENSOR SENTENCE: '{text}' (score: {prob:.2f}) at [{segment.start:.2f}s -> {segment.end:.2f}s]"
                    print(f"  {log_msg}")
                    logger.info(log_msg)
                    segments_to_cut.append((segment.start, segment.end))

        if args.cut_silence:
            print(f"  Checking for silent sections longer than {args.min_silence_duration}s...")
            logger.info(f"Checking for silent sections longer than {args.min_silence_duration}s...")
            last_speech_end = 0.0
            for segment in result_segments:
                silence_duration = segment.start - last_speech_end
                if silence_duration >= args.min_silence_duration:
                    log_msg = f"CUT SILENCE: from {last_speech_end:.2f}s to {segment.start:.2f}s"
                    print(f"  {log_msg}")
                    logger.info(log_msg)
                    segments_to_cut.append((last_speech_end, segment.start))
                last_speech_end = segment.end
        else:
            print("  Silence cutting is disabled.")
            logger.info("Silence cutting is disabled.")
        
        if not segments_to_cut:
            print("  No segments to cut. Skipping edit file generation.")
            logger.info("No segments to cut. Skipping edit file generation.")
            return
            
        merged_cuts = merge_intervals(segments_to_cut)
        log_msg = f"Found {len(segments_to_cut)} segments to cut. Merged into {len(merged_cuts)} distinct cuts."
        print(f"  {log_msg}")
        logger.info(log_msg)

        # =======================================================================
        # --- OTIO EDITING AND EXPORT LOGIC ---
        # =======================================================================
        print("  Generating OTIO timeline for NLE...")
        logger.info("Generating OTIO timeline...")

        try:
            # Get the total duration of the source video using ffmpeg
            probe = ffmpeg.probe(processing_path)
            duration = float(probe['format']['duration'])
        except (ffmpeg.Error, KeyError):
            error_msg = "Could not get video duration with ffmpeg. Skipping OTIO generation."
            print(f"  ERROR: {error_msg}")
            logger.error(error_msg)
            return
        
        # Calculate the time ranges of the clips to KEEP
        keep_segments = []
        last_end = 0.0
        for start_cut, end_cut in merged_cuts:
            if last_end < start_cut:
                keep_segments.append((last_end, start_cut))
            last_end = end_cut
        if last_end < duration:
            keep_segments.append((last_end, duration))

        if not keep_segments:
            print("  Skipped: entire video was flagged for cutting.")
            logger.warning("Entire video was flagged for cutting. No edit file generated.")
            return
            
        # Create an OTIO timeline
        timeline = otio.schema.Timeline(name=f"{base_name}_Edited")
        track = otio.schema.Track(kind=otio.schema.TrackKind.Video)
        
        # The OTIO file will reference the 'cleaned' video file in the temp directory.
        # This ensures frame accuracy with the transcription.
        media_path = os.path.abspath(processing_path)
        media_reference = otio.schema.ExternalReference(
            target_url=pathlib.Path(media_path).as_uri(),
            available_range=otio.opentime.TimeRange(
                start_time=otio.opentime.from_seconds(0),
                duration=otio.opentime.from_seconds(duration)
            )
        )
        
        # For each segment to keep, create an OTIO clip and add it to the track
        for start_sec, end_sec in keep_segments:
            clip_duration = end_sec - start_sec
            clip = otio.schema.Clip(
                name=f"Clip @ {start_sec:.2f}s",
                media_reference=media_reference,
                source_range=otio.opentime.TimeRange(
                    start_time=otio.opentime.from_seconds(start_sec),
                    duration=otio.opentime.from_seconds(clip_duration)
                )
            )
            track.append(clip)
            
        timeline.tracks.append(track)
        
        # Determine output format and file extension
        adapter_name = args.output_format
        extension = f".{adapter_name}"
        if adapter_name == 'fcpxml': # FCPXML has a different extension
            extension = '.fcpxml'

        output_path = os.path.join(output_dir, f"{base_name}_edited{extension}")
        
        print(f"  Exporting edit file as '{adapter_name.upper()}'...")
        otio.adapters.write_to_file(timeline, output_path, adapter_name=adapter_name)

        saved_msg = f"Saved: {output_path}"
        print(f"  {saved_msg}")
        logger.info(saved_msg)

    except Exception as e:
        error_msg = f"An error occurred while processing {os.path.basename(original_path)}: {e}"
        print(f"\n--- {error_msg} ---")
        if 'logger' in locals():
            logger.error(error_msg, exc_info=True)
        print("------------------------------------------------------------------")
    finally:
        if 'logger' in locals():
            logging.shutdown()


def main():
    parser = argparse.ArgumentParser(
        description="A script to find profanity/silence in videos and generate an edit list (e.g., FCPXML, EDL) for an NLE.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("input_files", nargs="*", help="Video files to process. Supports wildcards (e.g., *.mp4).")
    parser.add_argument('--no-clean', dest='clean', action='store_false', help="Disable the FFmpeg pre-cleaning step.")
    parser.add_argument('--model', default='base', choices=['tiny', 'base', 'small', 'medium', 'large', 'large-v2', 'large-v3'], help="The Whisper model to use. (Default: base)")
    parser.add_argument('--threshold', type=float, default=0.8, help="Profanity probability threshold for sentence and hybrid modes. (Default: 0.8)")
    
    # --- CENSORSHIP LEVEL FLAGS ---
    censor_group = parser.add_mutually_exclusive_group()
    censor_group.add_argument('-w', '--word', dest='censor_level', action='store_const', const='word', help="Mark specific words from the list for cutting.")
    censor_group.add_argument('-s', '--sentence', dest='censor_level', action='store_const', const='sentence', help="Mark the entire sentence containing a profane word for cutting.")
    censor_group.add_argument('-hy', '--hybrid', dest='censor_level', action='store_const', const='hybrid', help="Use sentence-context to find and mark specific words (Default).")
    
    # --- SILENCE CUTTING FLAGS ---
    parser.add_argument('--no-silence', dest='cut_silence', action='store_false', help="Disable the default behavior of cutting silent sections.")
    parser.add_argument('--min-silence-duration', type=float, default=1.0, help="Minimum duration (in seconds) of silence to cut. (Default: 1.0)")
    
    # --- OTIO OUTPUT FORMAT FLAGS ---
    output_format_group = parser.add_mutually_exclusive_group()
    output_format_group.add_argument('--fcpxml', dest='output_format', action='store_const', const='fcpxml', help="Output a Final Cut Pro XML file (.fcpxml). [DEFAULT]")
    output_format_group.add_argument('--edl', dest='output_format', action='store_const', const='edl', help="Output a CMX 3600 Edit Decision List (.edl).")
    output_format_group.add_argument('--aaf', dest='output_format', action='store_const', const='aaf', help="Output an Advanced Authoring Format file (.aaf).")
    output_format_group.add_argument('--otio', dest='output_format', action='store_const', const='otio', help="Output a native OpenTimelineIO file (.otio).")

    parser.set_defaults(clean=True, cut_silence=True, censor_level='hybrid', output_format='fcpxml')
    args = parser.parse_args()

    INPUT_DIR = os.getcwd()
    OUTPUT_DIR = os.path.join(INPUT_DIR, "edited_output")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    TEMP_DIR = os.path.join(INPUT_DIR, "script_temp")
    os.makedirs(TEMP_DIR, exist_ok=True)
    print(f"Temporary files will be stored in: {TEMP_DIR}")

    try:
        print(f"Loading faster-whisper model '{args.model}'...")
        model = WhisperModel(args.model, device="cuda", compute_type="float16")
        
        video_files = args.input_files
        if not video_files:
            print(f"No files specified. Searching for videos in: {INPUT_DIR}")
            for ext in [".mp4", ".mov", ".mkv"]: video_files.extend(glob.glob(os.path.join(INPUT_DIR, f"*{ext}")))
        
        if not video_files:
            print("No video files found to process. Exiting.")
            sys.exit()

        for path in video_files:
            if not os.path.exists(path):
                print(f"\nWarning: File not found, skipping: {path}")
                continue

            base_name = os.path.splitext(os.path.basename(path))[0]
            
            # Determine expected output path based on format
            ext = f".{args.output_format}"
            if args.output_format == 'fcpxml': ext = '.fcpxml'
            expected_output_path = os.path.join(OUTPUT_DIR, f"{base_name}_edited{ext}")

            if os.path.exists(expected_output_path):
                print(f"\nOutput file already exists for '{os.path.basename(path)}'. Skipping.")
                continue
            
            processing_path = clean_video(path, TEMP_DIR) if args.clean else path
            process_video(processing_path, path, model, args, OUTPUT_DIR, TEMP_DIR)

        print("\nProcessing complete.")

    finally:
        # MODIFICATION: No longer cleans up the temp directory.
        if os.path.exists(TEMP_DIR):
            print(f"\nCleanup step skipped. Temporary files are preserved in: {TEMP_DIR}")

if __name__ == "__main__":
    main()