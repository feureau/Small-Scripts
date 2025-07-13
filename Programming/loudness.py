# ----------------------
# Video Loudness Normalizer
#
# Purpose:
#   This script normalizes the loudness of the entire audio track in a video
#   file to a standard level (-16 LUFS). It creates a new video file with the
#   original video stream and the newly normalized audio.
#
# Requirements:
#   - Python 3
#   - FFmpeg: You must have ffmpeg installed and accessible in your system's PATH.
#     You can download it from https://ffmpeg.org/download.html
#
# Usage:
#   Run the script from your terminal, followed by the paths to one or more
#   video files.
#
#   Example:
#       python loudness.py "path/to/my video.mp4" another_video.mov
# ----------------------

import os
import sys
import argparse
import subprocess
import json
import shutil
from pathlib import Path

# ----------------------
# Config
# ----------------------
# Target loudness values (EBU R 128 standard is a good reference)
LOUDNORM_TARGETS = {"I": -16, "TP": -1.5, "LRA": 7}

# ----------------------
# Helpers
# ----------------------

def run(cmd, capture_output=False):
    """Executes a shell command and raises an error if it fails."""
    result = subprocess.run(cmd, shell=True, capture_output=capture_output, text=True)
    if result.returncode != 0:
        error_message = f"Command failed with exit code {result.returncode}\n"
        error_message += f"Command: {cmd}\n"
        if result.stdout: error_message += f"STDOUT: {result.stdout.strip()}\n"
        if result.stderr: error_message += f"STDERR: {result.stderr.strip()}\n"
        raise subprocess.CalledProcessError(result.returncode, cmd, output=result.stdout, stderr=result.stderr)
    return result.stdout if capture_output else None

def analyze_and_normalize_audio(input_video, output_audio):
    """
    Performs a robust two-pass loudness normalization on the video's audio track.
    """
    print("  -> Step 2: Analyzing audio loudness (Pass 1)...")
    # PASS 1: Run loudnorm filter to get the audio stats, but don't output a file.
    # The stats are printed to the stderr log.
    analysis_cmd = (
        f"ffmpeg -i \"{input_video}\" -hide_banner "
        f"-af loudnorm=I={LOUDNORM_TARGETS['I']}:TP={LOUDNORM_TARGETS['TP']}:"
        f"LRA={LOUDNORM_TARGETS['LRA']}:print_format=json -f null -"
    )
    
    # We expect an error because we are not creating an output file, but we capture the log.
    result = subprocess.run(analysis_cmd, shell=True, capture_output=True, text=True)
    
    # Find the JSON block within the ffmpeg stderr output.
    lines = result.stderr.splitlines()
    json_str = ""
    for line in lines:
        # The JSON data starts with '{' and is the last block in the output.
        if line.strip().startswith('{'):
            # The JSON block can span multiple lines, so we read until the end '}'
            json_str = "".join(lines[lines.index(line):])
            break
            
    if not json_str:
        raise RuntimeError(f"Could not find loudness analysis JSON in ffmpeg output.\n{result.stderr}")
    
    try:
        m = json.loads(json_str)
    except json.JSONDecodeError:
        raise RuntimeError(f"Could not parse JSON from ffmpeg output.\nInvalid JSON was: {json_str}")

    print("  -> Step 3: Applying normalization (Pass 2)...")
    # PASS 2: Now run the filter again, but feed the measured values from Pass 1
    # back into the filter to generate the perfectly normalized audio file.
    normalization_args = (
        f"loudnorm=I={LOUDNORM_TARGETS['I']}:TP={LOUDNORM_TARGETS['TP']}:LRA={LOUDNORM_TARGETS['LRA']}:"
        f"measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
        f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:"
        f"offset={m['target_offset']}:linear=true"
    )
    
    normalization_cmd = (
        f"ffmpeg -y -i \"{input_video}\" -hide_banner "
        f"-af \"{normalization_args}\" -vn -acodec pcm_s16le \"{output_audio}\""
    )
    
    run(normalization_cmd)

def remux_to_video(original_video, new_audio, output_video):
    """Combines a video stream with a new audio stream into a final video file."""
    print("  -> Step 4: Remuxing final audio into video...")
    run(f"ffmpeg -y -i \"{original_video}\" -i \"{new_audio}\" -map 0:v -map 1:a -c:v copy -shortest \"{output_video}\"")

def clean_dir(path):
    """Removes a directory and its contents."""
    if path.exists():
        shutil.rmtree(path)

# ----------------------
# Main Execution
# ----------------------
if __name__ == "__main__":
    if not shutil.which("ffmpeg"):
        print("ERROR: ffmpeg not found.")
        print("Please install ffmpeg and ensure it is in your system's PATH.")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Normalizes the audio track of video files.")
    parser.add_argument('inputs', nargs='+', help='One or more input video files (e.g., *.mp4)')
    args = parser.parse_args()

    for video_path in args.inputs:
        vp = Path(video_path)
        if not vp.exists():
            print(f"\nSkipping non-existent file: {vp}")
            continue

        base_name = vp.stem
        # We only need one temporary file now
        tmp_dir = Path('tmp') / base_name
        tmp_dir.mkdir(parents=True, exist_ok=True)
        
        output_dir = Path('output')
        output_dir.mkdir(exist_ok=True)
        output_video = output_dir / f"{base_name}_normalized.mp4"
        
        try:
            print(f"\nProcessing {vp.name}...")
            
            # The temporary file for the final, normalized audio
            normalized_audio_wav = tmp_dir / 'normalized_audio.wav'
            
            # The simplified and more robust workflow
            # Note: We no longer extract the audio first. The two-pass function handles it.
            analyze_and_normalize_audio(vp, normalized_audio_wav)
            remux_to_video(vp, normalized_audio_wav, output_video)
            
            print(f"✅ Successfully created -> {output_video}")
            
        except Exception as e:
            print(f"❌ Error processing {vp.name}: {e}")
        finally:
            print("  -> Cleaning up temporary files...")
            clean_dir(tmp_dir)