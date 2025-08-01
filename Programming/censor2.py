# ==================================================================================================
#
#                               VIDEO CENSORSHIP & EDITING SCRIPT
#
# ==================================================================================================
#
# OVERVIEW:
# This script is a powerful command-line tool for automatically editing video files. It uses
# AI-powered transcription (via faster-whisper) to detect and remove sections containing
# profanity and/or long periods of silence.
#
# It is highly optimized for speed, leveraging an NVIDIA GPU (CUDA) for transcription and
# hardware-accelerated encoding. The script's default mode is a lossless, stream-copy-based
# workflow that is extremely fast and preserves original video/audio quality.
#
#
# --- FEATURES ---
#
#   - MULTIPLE EDITING MODES:
#     - Default Lossless Mode: Extremely fast. Cuts video on keyframes without re-encoding.
#       Audio is also copied without modification. Zero quality loss.
#     - Optional Frame-Accurate Mode (`-p`): Slower, but allows for precise, frame-perfect
#       cuts. This requires a full re-encode of the video stream.
#
#   - MODULAR AUDIO PROCESSING:
#     - Audio Normalization (`--loudnorm`): Enabled by default to create consistent volume.
#       This can be disabled with the `--no-loudnorm` flag.
#
#   - ADVANCED CENSORSHIP LEVELS:
#     - Hybrid (Default): Uses sentence context to identify profanity, then precisely cuts
#       only the profane words within that sentence.
#     - Word: Cuts only the specific words found in the `PROFANE_WORDS` list.
#     - Sentence: Cuts the entire sentence segment if it's flagged as profane.
#
#   - AUTOMATIC SILENCE REMOVAL:
#     - Can detect and remove silent sections longer than a specified duration.
#
#   - PERFORMANCE & USABILITY:
#     - Transcription Caching: Saves transcription results to avoid re-transcribing on
#       subsequent runs with different settings.
#     - SRT Subtitle Generation: Automatically creates a `.srt` subtitle file for each video.
#     - Detailed Logging: Generates a `.log` file for each video, detailing every step
#       and decision made during processing.
#     - Robust Cleanup: Manages and removes all temporary files automatically.
#
#
# --- DEPENDENCIES ---
#
#   - PYTHON PACKAGES (install with pip):
#     `pip install moviepy scikit-learn alt-profanity-check faster-whisper ffmpeg-python`
#
#   - EXTERNAL SOFTWARE:
#     1. PyTorch with CUDA: You must install PyTorch with CUDA support separately from
#        the official PyTorch website (https://pytorch.org/get-started/locally/) to enable
#        GPU acceleration for transcription.
#     2. FFmpeg: A recent, full build of FFmpeg is required and must be in your system's PATH.
#        For best results, ensure your build includes the 'aac' audio encoder.
#
#
# --- MOVIEPY VERSION COMPATIBILITY ---
#
# This script is designed to be compatible with both stable and development versions of MoviePy.
#
# - MoviePy v2.0.0+ (from GitHub): Recent development versions have refactored the package
#   structure, moving main classes like `VideoFileClip` to the top-level `moviepy` package.
#
# - MoviePy v1.x (from PyPI): Stable versions use the `moviepy.editor` submodule as the
#   standard entry point for these classes.
#
# The script handles this by first attempting to import from the new top-level package (`from moviepy
# import ...`). If that fails with an `ImportError`, it falls back to the stable `moviepy.editor`
# path. This ensures maximum compatibility regardless of which version is installed.
#
#
# --- COMMAND-LINE USAGE EXAMPLES ---
#
# 1. NORMALIZED AUDIO (DEFAULT) & FAST VIDEO EDITING:
#    `python your_script_name.py my_video.mp4`
#
# 2. DISABLING LOUDNESS NORMALIZATION: For the absolute fastest performance (lossless audio).
#    `python your_script_name.py my_video.mp4 --no-loudnorm`
#
# 3. FRAME-PERFECT VIDEO EDITING: Slower, re-encodes video for precision. Audio is normalized by default.
#    `python your_script_name.py my_video.mp4 -p`
#    (or `python your_script_name.py my_video.mp4 --frame-accurate`)
#
# 4. HIGHEST PRECISION & NO AUDIO CHANGE: Re-encodes video, but keeps original audio.
#    `python your_script_name.py my_video.mp4 -p --no-loudnorm`
#
# 5. CENSOR ONLY SPECIFIC WORDS and disable silence cutting:
#    `python your_script_name.py my_video.mp4 -w --no-silence`
#
# ==================================================================================================

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
from collections import namedtuple

# Force UTF-8 for stdout/stderr if needed (especially on Windows)
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

# Set environment variable for UTF-8 (can help subprocesses like ffmpeg)
os.environ["PYTHONIOENCODING"] = "utf-8"

# --- Library Imports ---
from faster_whisper import WhisperModel
from profanity_check import predict_prob

# =========================================================================
# --- UNIVERSAL MOVIEPY IMPORT ---
# Tries the new, simplified v2.0 import first, then falls back to the
# stable v1.x 'editor' module for maximum compatibility.
# =========================================================================
try:
    # Path for bleeding-edge v2.0.0+ (imports from top-level)
    from moviepy import VideoFileClip, concatenate_videoclips
    print("--- Successfully imported from MoviePy v2.0.0+ structure. ---")
except ImportError:
    try:
        # Fallback path for stable versions from PyPI (v1.0+)
        from moviepy.editor import VideoFileClip, concatenate_videoclips
        print("--- Imported from stable 'moviepy.editor' module. ---")
    except ImportError:
        print("FATAL: MoviePy library not found or installation is corrupt.", file=sys.stderr)
        print("Please ensure MoviePy is installed correctly ('pip install moviepy').", file=sys.stderr)
        sys.exit(1)


# This list contains the specific words to be censored.
PROFANE_WORDS = {
    "fuck", "fucking", "shit", "bitch", "cunt", "asshole", "motherfucker"
}

# =================================================================================
# --- HELPER FUNCTIONS FOR LOSSLESS WORKFLOW ---
# =================================================================================

def lossless_extract_segment(input_path, output_path, start_time, end_time, logger):
    """Extracts a video segment using ffmpeg-python with a lossless stream copy."""
    logger.info(f"Losslessly extracting segment from {start_time:.2f}s to {end_time:.2f}s.")
    try:
        ffmpeg.input(input_path, ss=start_time, to=end_time).output(
            output_path, c='copy', hide_banner=None, loglevel='error'
        ).overwrite_output().run(capture_stdout=True, capture_stderr=True)
        return True
    except ffmpeg.Error as e:
        logger.error(f"Lossless segment extraction failed: {e.stderr.decode('utf-8')}")
        return False

def lossless_concatenate_segments(clip_paths, final_output_path, temp_dir, logger):
    """Joins multiple video clips losslessly using ffmpeg's concat demuxer."""
    logger.info(f"Losslessly concatenating {len(clip_paths)} clips.")
    concat_list_path = os.path.join(temp_dir, "concat_list.txt")
    
    try:
        with open(concat_list_path, 'w', encoding='utf-8') as f:
            for path in clip_paths:
                f.write(f"file '{os.path.abspath(path)}'\n")

        ffmpeg.input(concat_list_path, f='concat', safe=0).output(
            final_output_path, c='copy', hide_banner=None, loglevel='error'
        ).overwrite_output().run(capture_stdout=True, capture_stderr=True)
        return True
    except ffmpeg.Error as e:
        logger.error(f"Lossless concatenation failed: {e.stderr.decode('utf-8')}")
        return False

# =================================================================================
# --- CORE FUNCTIONS ---
# =================================================================================

def clean_video(input_path, temp_dir, args):
    """Creates a clean copy of the video. Behavior depends on --no-loudnorm flag."""
    output_path = os.path.join(temp_dir, f"cleaned_{os.path.basename(input_path)}")
    
    stream = ffmpeg.input(input_path)
    video_stream = stream['v:0']
    audio_stream = stream['a:0']

    ffmpeg_output_args = {'c:v': 'copy', 'dn': None, 'map_metadata': -1, 'map_chapters': -1, 'hide_banner': None, 'loglevel': 'error'}

    if args.loudnorm:
        print(f"  Cleaning '{os.path.basename(input_path)}' with audio normalization (re-encoding audio)...")
        processed_audio = audio_stream.filter('loudnorm', i=-16, tp=-1.5, lra=7)
        ffmpeg_output_args['c:a'] = 'aac' # Re-encode audio
    else:
        print(f"  Creating fast, lossless copy of '{os.path.basename(input_path)}' (no audio change)...")
        processed_audio = audio_stream
        ffmpeg_output_args['c:a'] = 'copy' # Copy audio as-is

    try:
        ffmpeg.output(video_stream, processed_audio, output_path, **ffmpeg_output_args).overwrite_output().run(capture_stdout=True, capture_stderr=True)
        print("  Successfully created temporary file for processing.")
        return output_path
    except ffmpeg.Error as e:
        print("FATAL: ffmpeg-python failed during cleaning/copying.", file=sys.stderr)
        raise RuntimeError(f"FFmpeg failed with stderr:\n{e.stderr.decode('utf-8')}")

Word = namedtuple('Word', ['start', 'end', 'word'])
Segment = namedtuple('Segment', ['start', 'end', 'text', 'words'])

def save_transcription_cache(data, cache_path):
    serializable_data = []
    for segment in data:
        seg_dict = {'start': segment.start, 'end': segment.end, 'text': segment.text, 'words': [{'start': w.start, 'end': w.end, 'word': w.word} for w in segment.words] if hasattr(segment, 'words') and segment.words else []}
        serializable_data.append(seg_dict)
    with open(cache_path, 'w', encoding='utf-8') as f: json.dump(serializable_data, f, indent=2)

def load_transcription_cache(cache_path):
    with open(cache_path, 'r', encoding='utf-8') as f: data = json.load(f)
    reconstructed = [Segment(s['start'], s['end'], s['text'], [Word(w['start'], w['end'], w['word']) for w in s['words']]) for s in data]
    return reconstructed

def merge_intervals(intervals):
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
    handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
    logger = logging.getLogger(name)
    logger.setLevel(level)
    if logger.hasHandlers(): logger.handlers.clear()
    logger.addHandler(handler)
    return logger

def format_srt_timestamp(seconds):
    td = datetime.timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    hours, rem = divmod(total_seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    milliseconds = td.microseconds // 1000
    return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"

def generate_srt_file(segments, output_path):
    with open(output_path, 'w', encoding='utf-8') as srt_file:
        for i, segment in enumerate(segments, 1):
            srt_file.write(f"{i}\n{format_srt_timestamp(segment.start)} --> {format_srt_timestamp(segment.end)}\n{segment.text.strip()}\n\n")

def process_video(processing_path, original_path, model, args, output_dir, temp_dir):
    base_name = os.path.splitext(os.path.basename(original_path))[0]
    log_path = os.path.join(output_dir, f"{base_name}.log")
    logger = setup_logger(base_name, log_path)
    transcription_cache_path = os.path.join(temp_dir, f"{base_name}_transcription.json")
    
    final_clip = None
    video = None

    try:
        print(f"\nProcessing: {os.path.basename(original_path)}")
        logger.info(f"--- Starting processing for {original_path} ---")
        
        if os.path.exists(transcription_cache_path):
            print("  Found existing transcription cache. Loading from file...")
            result_segments = load_transcription_cache(transcription_cache_path)
        else:
            print("  Transcribing with faster-whisper...")
            segments_iterator, info = model.transcribe(processing_path, word_timestamps=True)
            lang_info = f"Detected language '{info.language}' with probability {info.language_probability:.2f}"
            print(f"  {lang_info}"); logger.info(lang_info)
            result_segments = list(segments_iterator)
            save_transcription_cache(result_segments, transcription_cache_path)
            logger.info(f"Saved transcription cache to {transcription_cache_path}")

        srt_path = os.path.join(output_dir, f"{base_name}.srt")
        generate_srt_file(result_segments, srt_path)
        print(f"  Saved transcription to: {srt_path}")

        segments_to_cut = []
        if args.censor_level == 'word':
            for seg in result_segments:
                if not hasattr(seg, 'words'): continue
                for word in seg.words:
                    if word.word.strip().lower().strip('.,!?-') in PROFANE_WORDS: segments_to_cut.append((word.start, word.end))
        elif args.censor_level == 'hybrid':
            for seg in result_segments:
                if not seg.text.strip() or not hasattr(seg, 'words'): continue
                if predict_prob([seg.text.strip()])[0] >= args.threshold:
                    for word in seg.words:
                        if word.word.strip().lower().strip('.,!?-') in PROFANE_WORDS: segments_to_cut.append((word.start, word.end))
        else:
            for seg in result_segments:
                if seg.text.strip() and predict_prob([seg.text.strip()])[0] >= args.threshold: segments_to_cut.append((seg.start, seg.end))

        if args.cut_silence:
            last_speech_end = 0.0
            for segment in result_segments:
                if segment.start - last_speech_end >= args.min_silence_duration: segments_to_cut.append((last_speech_end, segment.start))
                last_speech_end = segment.end
        
        if not segments_to_cut:
            print("  No segments to cut. Copying original file to output.")
            shutil.copy(processing_path, os.path.join(output_dir, f"{base_name}_edited.mp4"))
            return
            
        merged_cuts = merge_intervals(segments_to_cut)
        logger.info(f"Found {len(segments_to_cut)} segments to cut. Merged into {len(merged_cuts)} distinct cuts.")
        print(f"  Found {len(merged_cuts)} distinct time intervals to remove.")
        
        if args.frame_accurate:
            print("  Using frame-accurate mode. This will re-encode the entire video.")
            logger.info("Using frame-accurate (re-encoding) mode.")
            video = VideoFileClip(processing_path)
            keep_clips = []
            last_end = 0.0
            for start, end in merged_cuts:
                if last_end < start: keep_clips.append(video.subclip(last_end, start))
                last_end = end
            if last_end < video.duration: keep_clips.append(video.subclip(last_end, video.duration))

            if not keep_clips:
                print("  Skipped: entire video was flagged for cutting."); logger.warning("Entire video flagged for cutting.")
                return
                
            final_clip = concatenate_videoclips(keep_clips)
            output_path = os.path.join(output_dir, f"{base_name}_edited.mp4")
            
            print("  Exporting edited video (CUDA encoding enabled)...")
            final_clip.write_videofile(
                output_path, codec="hevc_nvenc", audio_codec="aac", audio_bitrate="192k",
                temp_audiofile=os.path.join(temp_dir, f"{base_name}_temp_audio.m4a"),
                threads=4, ffmpeg_params=["-pix_fmt", "yuv420p", "-preset", "p1", "-rc", "vbr", "-cq", "28", "-b:v", "0"]
            )
            print(f"  Saved: {output_path}"); logger.info(f"Saved: {output_path}")
        else:
            print("  Using default lossless mode. This will be fast and not re-encode video/audio.")
            logger.info("Using default lossless (stream copy) mode.")
            keep_times = []
            last_end = 0.0
            video_duration = float(ffmpeg.probe(processing_path)['format']['duration'])
            for start, end in merged_cuts:
                if last_end < start: keep_times.append((last_end, start))
                last_end = end
            if last_end < video_duration: keep_times.append((last_end, video_duration))

            if not keep_times:
                print("  Skipped: entire video was flagged for cutting."); logger.warning("Entire video flagged for cutting.")
                return

            temp_clips = []
            for i, (start, end) in enumerate(keep_times):
                clip_path = os.path.join(temp_dir, f"{base_name}_clip_{i}.mp4")
                if lossless_extract_segment(processing_path, clip_path, start, end, logger): temp_clips.append(clip_path)
            
            if not temp_clips:
                print("  Error: Failed to extract any video segments for lossless processing.", file=sys.stderr); logger.error("Failed to extract clips in lossless mode.")
                return

            output_path = os.path.join(output_dir, f"{base_name}_edited.mp4")
            if len(temp_clips) == 1:
                print("  Only one segment to keep. Copying directly.")
                shutil.move(temp_clips[0], output_path)
            else:
                print(f"  Joining {len(temp_clips)} clips losslessly...")
                lossless_concatenate_segments(temp_clips, output_path, temp_dir, logger)
            print(f"  Saved: {output_path}"); logger.info(f"Saved: {output_path}")
    except Exception as e:
        print(f"\n--- FATAL ERROR processing {os.path.basename(original_path)}: {e} ---", file=sys.stderr)
        if 'logger' in locals(): logger.error(f"FATAL ERROR", exc_info=True)
    finally:
        if final_clip: final_clip.close()
        if video: video.close()
        if 'logger' in locals(): logging.shutdown()

def main():
    # Use our extensive docstring as the help text for the script
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("input_files", nargs="*", help="Video files/wildcards to process (e.g., *.mp4). If empty, searches current dir.")
    parser.add_argument('--model', default='base', choices=['tiny', 'base', 'small', 'medium', 'large-v2', 'large-v3'], help="Whisper model (default: base).")
    parser.add_argument('--threshold', type=float, default=0.8, help="Profanity probability threshold (default: 0.8).")
    
    censor_group = parser.add_mutually_exclusive_group()
    censor_group.add_argument('-w', '--word', dest='censor_level', action='store_const', const='word', help="Censor specific words only.")
    censor_group.add_argument('-s', '--sentence', dest='censor_level', action='store_const', const='sentence', help="Censor the entire profane sentence.")
    censor_group.add_argument('-hy', '--hybrid', dest='censor_level', action='store_const', const='hybrid', help="Use sentence context to find and censor words (Default).")
    
    parser.add_argument('--no-silence', dest='cut_silence', action='store_false', help="Disable cutting silent sections.")
    parser.add_argument('--min-silence-duration', type=float, default=1.0, help="Minimum duration of silence to cut (secs, default: 1.0).")
    
    parser.add_argument('-p', '--frame-accurate', action='store_true', help="Use frame-perfect but slow re-encoding mode.")
    
    # --- MODIFIED: Loudnorm is now opt-out ---
    parser.add_argument('--no-loudnorm', dest='loudnorm', action='store_false', help="Disable the default audio loudness normalization.")
    
    parser.add_argument('--no-clean', dest='clean', action='store_false', help="Disable the initial video cleaning/copying step.")

    # --- MODIFIED: loudnorm default is now True ---
    parser.set_defaults(cut_silence=True, censor_level='hybrid', frame_accurate=False, loudnorm=True, clean=True)
    
    args = parser.parse_args()

    INPUT_DIR = os.getcwd()
    OUTPUT_DIR = os.path.join(INPUT_DIR, "edited_output")
    TEMP_DIR = os.path.join(INPUT_DIR, "script_temp")
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(TEMP_DIR, exist_ok=True)
    print(f"Temporary files will be stored in: {TEMP_DIR}")

    try:
        print(f"Loading faster-whisper model '{args.model}'...")
        model = WhisperModel(args.model, device="cuda", compute_type="float16")
        
        video_files = args.input_files
        if not video_files:
            print(f"No files specified. Searching for videos in: {INPUT_DIR}")
            video_files = [f for ext in ["*.mp4", "*.mov", "*.mkv"] for f in glob.glob(os.path.join(INPUT_DIR, ext))]

        if not video_files: print("No video files found. Exiting."); sys.exit()

        for path in video_files:
            if not os.path.exists(path): print(f"\nWarning: File not found, skipping: {path}"); continue
            
            base_name = os.path.splitext(os.path.basename(path))[0]
            if os.path.exists(os.path.join(OUTPUT_DIR, f"{base_name}_edited.mp4")):
                print(f"\nOutput file already exists for '{os.path.basename(path)}'. Skipping."); continue
            
            processing_path = clean_video(path, TEMP_DIR, args) if args.clean else path
            process_video(processing_path, path, model, args, OUTPUT_DIR, TEMP_DIR)

        print("\nAll processing complete.")
    except Exception as e:
        print(f"\n--- A CRITICAL ERROR OCCURRED: {e} ---", file=sys.stderr)
    finally:
        if os.path.exists(TEMP_DIR):
            print(f"Cleaning up temporary directory: {TEMP_DIR}")
            shutil.rmtree(TEMP_DIR)

if __name__ == "__main__":
    # Add our extensive docstring to the script's help message
    __doc__ = """
==================================================================================================

                              VIDEO CENSORSHIP & EDITING SCRIPT

==================================================================================================

OVERVIEW:
This script is a powerful command-line tool for automatically editing video files. It uses
AI-powered transcription (via faster-whisper) to detect and remove sections containing
profanity and/or long periods of silence.

It is highly optimized for speed, leveraging an NVIDIA GPU (CUDA) for transcription and
hardware-accelerated encoding. The script's default mode is a lossless, stream-copy-based
workflow that is extremely fast and preserves original video/audio quality.


--- FEATURES ---

  - MULTIPLE EDITING MODES:
    - Default Lossless Mode: Extremely fast. Cuts video on keyframes without re-encoding.
    - Optional Frame-Accurate Mode (`-p`): Slower, but allows for precise, frame-perfect
      cuts. This requires a full re-encode of the video stream.

  - MODULAR AUDIO PROCESSING:
    - Audio Normalization (`--loudnorm`): Enabled by default to create consistent volume.
      This can be disabled with the `--no-loudnorm` flag.

  - ADVANCED CENSORSHIP LEVELS:
    - Hybrid (Default): Uses sentence context to identify profanity, then precisely cuts
      only the profane words within that sentence.
    - Word: Cuts only the specific words found in the `PROFANE_WORDS` list.
    - Sentence: Cuts the entire sentence segment if it's flagged as profane.

  - AUTOMATIC SILENCE REMOVAL:
    - Can detect and remove silent sections longer than a specified duration.

  - PERFORMANCE & USABILITY:
    - Transcription Caching: Saves transcription results to avoid re-transcribing on
      subsequent runs with different settings.
    - SRT Subtitle Generation: Automatically creates a `.srt` subtitle file for each video.
    - Detailed Logging: Generates a `.log` file for each video, detailing every step
      and decision made during processing.
    - Robust Cleanup: Manages and removes all temporary files automatically.


--- DEPENDENCIES ---

  - PYTHON PACKAGES (install with pip):
    `pip install moviepy scikit-learn alt-profanity-check faster-whisper ffmpeg-python`

  - EXTERNAL SOFTWARE:
    1. PyTorch with CUDA: You must install PyTorch with CUDA support separately from
       the official PyTorch website (https://pytorch.org/get-started/locally/) to enable
       GPU acceleration for transcription.
    2. FFmpeg: A recent, full build of FFmpeg is required and must be in your system's PATH.
       For best results, ensure your build includes the 'aac' audio encoder.


--- MOVIEPY VERSION COMPATIBILITY ---

This script is designed to be compatible with both stable and development versions of MoviePy.

- MoviePy v2.0.0+ (from GitHub): Recent development versions have refactored the package
  structure, moving main classes like `VideoFileClip` to the top-level `moviepy` package.

- MoviePy v1.x (from PyPI): Stable versions use the `moviepy.editor` submodule as the
  standard entry point for these classes.

The script handles this by first attempting to import from the new top-level package (`from moviepy
import ...`). If that fails with an `ImportError`, it falls back to the stable `moviepy.editor`
path. This ensures maximum compatibility regardless of which version is installed.
"""
    main()