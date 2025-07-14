# NOTE: Required Python packages (install with pip)
# pip install moviepy openai-whisper torch torchvision torchaudio scikit-learn alt-profanity-check
#
# System requirements:
# - FFmpeg must be installed and accessible in the system's PATH.
# - A CUDA-compatible NVIDIA GPU is REQUIRED for Whisper GPU acceleration.

import sys
import os
import glob
import torch
import argparse
import subprocess
import shutil # --- NEW ---: Needed for deleting the temp directory

import whisper
from profanity_check import predict_prob
from moviepy import VideoFileClip, concatenate_videoclips

PROFANE_WORDS = {
    "fuck", "fucking", "shit", "bitch", "cunt", "asshole", "motherfucker"
    # Add any other words you want to censor here
}

def clean_video(input_path, temp_dir):
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
    if not intervals:
        return []
    intervals.sort(key=lambda x: x[0])
    merged = [intervals[0]]
    for current_start, current_end in intervals[1:]:
        last_start, last_end = merged[-1]
        if current_start <= last_end:
            merged[-1] = (last_start, max(last_end, current_end))
        else:
            merged.append((current_start, current_end))
    return merged

# --- MODIFIED ---: Added 'temp_dir' to pass our central temp path
def process_video(processing_path, original_path, model, args, output_dir, temp_dir):
    try:
        print(f"\nProcessing: {os.path.basename(original_path)}")
        result = model.transcribe(processing_path, fp16=torch.cuda.is_available(), word_timestamps=True)

        segments_to_cut = []
        
        print("  Checking for profanity (word-level)...")
        for segment in result['segments']:
            text = segment['text'].strip()
            if not text: continue
            
            prob = predict_prob([text])[0]
            if prob >= args.threshold:
                for word_data in segment.get('words', []):
                    clean_word = word_data['word'].lower().strip('.,!?-')
                    if clean_word in PROFANE_WORDS:
                        print(f"  CENSOR WORD: '{word_data['word']}' in segment '{text}'")
                        segments_to_cut.append((word_data['start'], word_data['end']))

        if args.cut_silence:
            print(f"  Checking for silent sections longer than {args.min_silence_duration}s...")
            last_speech_end = 0.0
            for segment in result['segments']:
                silence_duration = segment['start'] - last_speech_end
                if silence_duration >= args.min_silence_duration:
                    print(f"  SILENCE: Cutting from {last_speech_end:.2f}s to {segment['start']:.2f}s")
                    segments_to_cut.append((last_speech_end, segment['start']))
                last_speech_end = segment['end']
        else:
            print("  Silence cutting is disabled.")
        
        if not segments_to_cut:
            print("  No segments to cut. Skipping video.")
            return
            
        merged_cuts = merge_intervals(segments_to_cut)
        print(f"  Original cut segments: {len(segments_to_cut)}, Merged cut segments: {len(merged_cuts)}")

        video = VideoFileClip(processing_path)
        
        keep_segments = []
        last_end = 0.0
        for start, end in merged_cuts:
            if last_end < start:
                keep_segments.append(video.subclipped(last_end, start))
            last_end = end
        if last_end < video.duration:
            keep_segments.append(video.subclipped(last_end, video.duration))

        if not keep_segments:
            print("  Skipped: entire video was flagged for cutting.")
            video.close()
            return
            
        final_clip = concatenate_videoclips(keep_segments)
        base_name = os.path.splitext(os.path.basename(original_path))[0]
        output_path = os.path.join(output_dir, f"{base_name}_edited.mp4")
        
        print(f"  Exporting edited video...")
        # --- MODIFIED ---: Direct MoviePy's temp file to our central temp folder
        temp_audio_path = os.path.join(temp_dir, "temp-audio.m4a")
        final_clip.write_videofile(
            output_path,
            codec="av1_nvenc",
            audio_codec="aac",
            temp_audiofile=temp_audio_path,
            remove_temp=True,
            threads=4,
            ffmpeg_params=[
                "-pix_fmt", "yuv420p",
                "-gpu", "0",
                "-preset", "fast",
                "-rc", "vbr",
                "-cq", "28",
                "-b:v", "0"
            ]
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
        description="A script to find and remove profanity and/or silent sections from video files.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    # ... (all other arguments are the same)
    parser.add_argument("input_files", nargs="*", help="Video files to process. Supports wildcards (e.g., *.mp4).")
    parser.add_argument('--no-clean', dest='clean', action='store_false', help="Disable the FFmpeg pre-cleaning step.")
    parser.add_argument('--model', default='base', choices=['tiny', 'base', 'small', 'medium', 'large'], help="The Whisper model to use. (Default: base)")
    parser.add_argument('--threshold', type=float, default=0.8, help="Profanity probability threshold. (Default: 0.8)")
    parser.add_argument('--no-silence', dest='cut_silence', action='store_false', help="Disable the default behavior of cutting silent sections.")
    parser.add_argument('--min-silence-duration', type=float, default=1.0, help="Minimum duration (in seconds) of silence to cut. (Default: 1.0)")
    # --- NEW ---
    parser.add_argument(
        '--temp-cache',
        action='store_true',
        help="Store the Whisper model cache in the temporary folder.\n(WARNING: This will re-download the model on every run!)"
    )

    parser.set_defaults(clean=True, cut_silence=True, temp_cache=False)
    args = parser.parse_args()

    INPUT_DIR = os.getcwd()
    OUTPUT_DIR = os.path.join(INPUT_DIR, "edited_output")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # --- MODIFIED ---: Centralized temporary directory management
    TEMP_DIR = os.path.join(INPUT_DIR, "script_temp")
    if os.path.exists(TEMP_DIR):
        print(f"Warning: Found existing temp directory. Removing: {TEMP_DIR}")
        shutil.rmtree(TEMP_DIR)
    os.makedirs(TEMP_DIR, exist_ok=True)
    print(f"Temporary files will be stored in: {TEMP_DIR}")

    try:
        # --- MODIFIED ---: Logic for Whisper cache location
        whisper_cache_path = None
        if args.temp_cache:
            whisper_cache_path = os.path.join(TEMP_DIR, "whisper_cache")
            print("Whisper model cache will be downloaded to the temporary folder.")
        
        if torch.cuda.is_available():
            device = "cuda"
            print(f"Loading Whisper model '{args.model}'... (using device: {device})")
            model = whisper.load_model(args.model, device=device, download_root=whisper_cache_path)
        else:
            print("ERROR: No CUDA-enabled GPU detected. Aborting.")
            sys.exit(1)

        video_files = args.input_files
        if not video_files:
            print(f"No files specified. Searching for videos in: {INPUT_DIR}")
            for ext in [".mp4", ".mov", ".mkv"]:
                video_files.extend(glob.glob(os.path.join(INPUT_DIR, f"*{ext}")))

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
        # --- NEW ---: This block runs always, ensuring cleanup
        if os.path.exists(TEMP_DIR):
            print(f"Cleaning up temporary directory: {TEMP_DIR}")
            shutil.rmtree(TEMP_DIR)

if __name__ == "__main__":
    main()