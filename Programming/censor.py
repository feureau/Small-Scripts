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

from faster_whisper import WhisperModel
from profanity_check import predict_prob
from moviepy import VideoFileClip, concatenate_videoclips

PROFANE_WORDS = {
    "fuck", "fucking", "shit", "bitch", "cunt", "asshole", "motherfucker"
    # Add any other words you want to censor here
}

def clean_video(input_path, temp_dir):
    """Creates a clean, standardized copy of the video to prevent processing errors."""
    print(f"  Cleaning '{os.path.basename(input_path)}'...")
    output_path = os.path.join(temp_dir, os.path.basename(input_path))
    command = [
        "ffmpeg", "-i", input_path, "-y",
        "-map", "0:v:0", "-map", "0:a:0",
        "-c", "copy",
        "-map_metadata", "-1",
        "-map_chapters", "-1",
        "-dn",
        output_path
    ]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
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

def process_video(processing_path, original_path, model, args, output_dir, temp_dir):
    """Processes a single video file for censorship and silence removal."""
    try:
        print(f"\nProcessing: {os.path.basename(original_path)}")
        
        # --- FASTER-WHISPER IMPLEMENTATION ---
        print("Transcribing with faster-whisper...")
        segments_iterator, info = model.transcribe(processing_path, word_timestamps=True)
        
        # Convert the iterator to a list so we can process it multiple times
        result_segments = list(segments_iterator)
        print(f"  Detected language '{info.language}' with probability {info.language_probability:.2f}")

        segments_to_cut = []

        # CENSORSHIP LOGIC
        if args.censor_level == 'word':
            print("  Checking for profanity (word-level)...")
            for segment in result_segments:
                text = segment.text.strip()
                if not text: continue
                prob = predict_prob([text])[0]
                if prob >= args.threshold:
                    # Note: faster-whisper gives a generator for words, so we loop through it
                    for word in segment.words:
                        clean_word = word.word.lower().strip('.,!?-')
                        if clean_word in PROFANE_WORDS:
                            print(f"  CENSOR WORD: '{word.word}'")
                            segments_to_cut.append((word.start, word.end))
        else: # Sentence-level censoring
            print("  Checking for profanity (sentence-level)...")
            for segment in result_segments:
                text = segment.text.strip()
                if not text: continue
                prob = predict_prob([text])[0]
                if prob >= args.threshold:
                    print(f"  CENSOR SENTENCE: '{text}' (score: {prob:.2f})")
                    segments_to_cut.append((segment.start, segment.end))

        # SILENCE CUTTING LOGIC
        if args.cut_silence:
            print(f"  Checking for silent sections longer than {args.min_silence_duration}s...")
            last_speech_end = 0.0
            for segment in result_segments:
                silence_duration = segment.start - last_speech_end
                if silence_duration >= args.min_silence_duration:
                    print(f"  SILENCE: Cutting from {last_speech_end:.2f}s to {segment.start:.2f}s")
                    segments_to_cut.append((last_speech_end, segment.start))
                last_speech_end = segment.end
        else:
            print("  Silence cutting is disabled.")
        
        # VIDEO CUTTING LOGIC
        if not segments_to_cut:
            print("  No segments to cut. Skipping video.")
            return
            
        merged_cuts = merge_intervals(segments_to_cut)
        print(f"  Original cut segments: {len(segments_to_cut)}, Merged cut segments: {len(merged_cuts)}")

        video = VideoFileClip(processing_path)
        keep_segments = []
        last_end = 0.0
        for start, end in merged_cuts:
            if last_end < start: keep_segments.append(video.subclipped(last_end, start))
            last_end = end
        if last_end < video.duration: keep_segments.append(video.subclipped(last_end, video.duration))

        if not keep_segments:
            print("  Skipped: entire video was flagged for cutting.")
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
            ffmpeg_params=["-pix_fmt", "yuv420p", "-gpu", "0", "-preset", "fast", "-rc", "vbr", "-cq", "28", "-b:v", "0"]
        )
        print(f"  Saved: {output_path}")

    except Exception as e:
        print(f"\n--- An error occurred while processing {os.path.basename(original_path)} ---")
        print(f"  ERROR: {e}")
        print("------------------------------------------------------------------")
    finally:
        if 'final_clip' in locals() and final_clip: final_clip.close()
        if 'video' in locals() and video: video.close()

def main():
    parser = argparse.ArgumentParser(
        description="A script to find and remove profanity and/or silent sections from video files using faster-whisper.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("input_files", nargs="*", help="Video files to process. Supports wildcards (e.g., *.mp4).")
    parser.add_argument('--no-clean', dest='clean', action='store_false', help="Disable the FFmpeg pre-cleaning step.")
    parser.add_argument('--model', default='base', choices=['tiny', 'base', 'small', 'medium', 'large', 'large-v2', 'large-v3'], help="The Whisper model to use. (Default: base)")
    parser.add_argument('--threshold', type=float, default=0.8, help="Profanity probability threshold. (Default: 0.8)")
    
    censor_group = parser.add_mutually_exclusive_group()
    censor_group.add_argument('-w', '--word', dest='censor_level', action='store_const', const='word', help="Censor on a word-by-word basis (Default).")
    censor_group.add_argument('-s', '--sentence', dest='censor_level', action='store_const', const='sentence', help="Censor the entire sentence containing a profane word.")
    
    parser.add_argument('--no-silence', dest='cut_silence', action='store_false', help="Disable the default behavior of cutting silent sections.")
    parser.add_argument('--min-silence-duration', type=float, default=1.0, help="Minimum duration (in seconds) of silence to cut. (Default: 1.0)")
    
    parser.set_defaults(clean=True, cut_silence=True, censor_level='word')
    args = parser.parse_args()

    INPUT_DIR = os.getcwd()
    OUTPUT_DIR = os.path.join(INPUT_DIR, "edited_output")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    TEMP_DIR = os.path.join(INPUT_DIR, "script_temp")
    if os.path.exists(TEMP_DIR): shutil.rmtree(TEMP_DIR)
    os.makedirs(TEMP_DIR, exist_ok=True)
    print(f"Temporary files will be stored in: {TEMP_DIR}")

    try:
        # Load the faster-whisper model
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