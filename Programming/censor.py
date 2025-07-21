# NOTE: Required Python packages (install with pip)
# pip install moviepy scikit-learn alt-profanity-check faster-whisper
# NOTE: You must also install PyTorch with CUDA support separately if not already done.

import sys
import os
import glob
import torch
import argparse
import subprocess
import shutil
import logging
import datetime

from faster_whisper import WhisperModel
from profanity_check import predict_prob
# --- CORRECTED IMPORT for modern MoviePy versions ---
from moviepy import VideoFileClip, concatenate_videoclips


# This list contains the specific words to be censored.
# You can add or remove words here. They should be lowercase.
PROFANE_WORDS = {
    "fuck", "fucking", "shit", "bitch", "cunt", "asshole", "motherfucker"
}

def clean_video(input_path, temp_dir):
    """Creates a clean, standardized copy of the video to prevent processing errors."""
    print(f"  Cleaning '{os.path.basename(input_path)}'...")
    output_path = os.path.join(temp_dir, os.path.basename(input_path))
    
    command = [
        "ffmpeg", "-i", input_path, "-y",
        "-map", "0:v:0", "-map", "0:a:0",
        "-c:v", "copy",
        "-c:a", "aac",
        "-af", "loudnorm=I=-16:TP=-1.5:LRA=7",
        "-map_metadata", "-1",
        "-map_chapters", "-1",
        "-dn",
        output_path
    ]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        print(f"  Successfully cleaned. Using temporary file for processing.")
        return output_path
    except FileNotFoundError:
        print("FATAL: 'ffmpeg' not found. Please ensure it's installed and in your system's PATH.")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"FFmpeg failed during cleaning with stderr:\n{e.stderr}")

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
    """Processes a single video file for censorship and silence removal."""
    
    base_name = os.path.splitext(os.path.basename(original_path))[0]
    log_path = os.path.join(output_dir, f"{base_name}.log")
    logger = setup_logger(base_name, log_path)

    try:
        print(f"\nProcessing: {os.path.basename(original_path)}")
        logger.info(f"--- Starting processing for {original_path} ---")
        
        print("Transcribing with faster-whisper (this may take a while)...")
        segments_iterator, info = model.transcribe(processing_path, word_timestamps=True)
        
        lang_info = f"Detected language '{info.language}' with probability {info.language_probability:.2f}"
        print(f"  {lang_info}")
        logger.info(lang_info)
        
        print("--- Real-Time Transcription ---")
        logger.info("--- Real-Time Transcription ---")

        result_segments = []
        for segment in segments_iterator:
            line = f"[{segment.start:0>7.2f}s -> {segment.end:0>7.2f}s] {segment.text.strip()}"
            print(line)
            logger.info(line)
            result_segments.append(segment)

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
            print("  No segments to cut. Skipping video editing.")
            logger.info("No segments to cut. Skipping video editing.")
            return
            
        merged_cuts = merge_intervals(segments_to_cut)
        log_msg = f"Found {len(segments_to_cut)} segments to cut. Merged into {len(merged_cuts)} distinct cuts."
        print(f"  {log_msg}")
        logger.info(log_msg)

        video = VideoFileClip(processing_path)
        keep_segments = []
        last_end = 0.0
        for start, end in merged_cuts:
            if last_end < start: keep_segments.append(video.subclip(last_end, start))
            last_end = end
        if last_end < video.duration: keep_segments.append(video.subclip(last_end, video.duration))

        if not keep_segments:
            print("  Skipped: entire video was flagged for cutting.")
            logger.warning("Entire video was flagged for cutting. No output file generated.")
            video.close()
            return
            
        final_clip = concatenate_videoclips(keep_segments)
        base_name = os.path.splitext(os.path.basename(original_path))[0]
        output_path = os.path.join(output_dir, f"{base_name}_edited.mp4")
        
        print(f"  Exporting edited video...")
        temp_audio_path = os.path.join(temp_dir, "temp-audio.m4a")
        final_clip.write_videofile(
            output_path, codec="av1_nvenc", audio_codec="aac", temp_audiofile=temp_audio_path,
            remove_temp=True, threads=4,
            ffmpeg_params=["-pix_fmt", "yuv420p", "-gpu", "0", "-preset", "p1", "-rc", "vbr", "-cq", "28", "-b:v", "0"]
        )
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
        if 'final_clip' in locals() and 'close' in dir(final_clip): final_clip.close()
        if 'video' in locals() and 'close' in dir(video): video.close()
        if 'logger' in locals():
            logging.shutdown()

def main():
    parser = argparse.ArgumentParser(
        description="A script to find and remove profanity and/or silent sections from video files using faster-whisper.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("input_files", nargs="*", help="Video files to process. Supports wildcards (e.g., *.mp4).")
    parser.add_argument('--no-clean', dest='clean', action='store_false', help="Disable the FFmpeg pre-cleaning step.")
    parser.add_argument('--model', default='base', choices=['tiny', 'base', 'small', 'medium', 'large', 'large-v2', 'large-v3'], help="The Whisper model to use. (Default: base)")
    parser.add_argument('--threshold', type=float, default=0.8, help="Profanity probability threshold for sentence and hybrid modes. (Default: 0.8)")
    
    censor_group = parser.add_mutually_exclusive_group()
    censor_group.add_argument('-w', '--word', dest='censor_level', action='store_const', const='word', help="Censor specific words from the list only.")
    censor_group.add_argument('-s', '--sentence', dest='censor_level', action='store_const', const='sentence', help="Censor the entire sentence containing a profane word.")
    censor_group.add_argument('-hy', '--hybrid', dest='censor_level', action='store_const', const='hybrid', help="Use sentence-context to find and censor specific words (Default).")
    
    parser.add_argument('--no-silence', dest='cut_silence', action='store_false', help="Disable the default behavior of cutting silent sections.")
    parser.add_argument('--min-silence-duration', type=float, default=1.0, help="Minimum duration (in seconds) of silence to cut. (Default: 1.0)")
    
    # --- MODIFIED DEFAULTS: 'hybrid' is now the default censorship level ---
    parser.set_defaults(clean=True, cut_silence=True, censor_level='hybrid')
    args = parser.parse_args()

    INPUT_DIR = os.getcwd()
    OUTPUT_DIR = os.path.join(INPUT_DIR, "edited_output")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    TEMP_DIR = os.path.join(INPUT_DIR, "script_temp")
    if os.path.exists(TEMP_DIR): shutil.rmtree(TEMP_DIR)
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
            
            processing_path = clean_video(path, TEMP_DIR) if args.clean else path
            process_video(processing_path, path, model, args, OUTPUT_DIR, TEMP_DIR)

        print("\nProcessing complete.")

    finally:
        if os.path.exists(TEMP_DIR):
            print(f"Cleaning up temporary directory: {TEMP_DIR}")
            shutil.rmtree(TEMP_DIR)

if __name__ == "__main__":
    main()