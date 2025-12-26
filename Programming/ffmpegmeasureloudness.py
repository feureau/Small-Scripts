#!/usr/bin/env python3
"""
ffmpegmeasureloudness.py

Usage:
    python ffmpegmeasureloudness.py "C:/path/to/video_or_audio.mp4"

Outputs a JSON with Integrated LUFS, Loudness Range (LU), and True Peak (dBTP).
"""

import subprocess
import json
import sys
import os

def measure_loudness(file_path):
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    # FFmpeg command to measure loudness
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-i", file_path,
        "-af", "loudnorm=print_format=json",
        "-f", "null",
        "-"
    ]

    try:
        # Run FFmpeg and capture stderr as bytes
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # Decode stderr safely with UTF-8, ignore errors from non-UTF8 bytes
        stderr = result.stderr.decode('utf-8', errors='ignore')

        # Extract JSON from stderr
        json_start = stderr.find("{")
        json_end = stderr.rfind("}") + 1
        if json_start == -1 or json_end == -1:
            raise ValueError("Could not find loudnorm JSON output in FFmpeg stderr")

        loudness_json = stderr[json_start:json_end]
        data = json.loads(loudness_json)

        # Return all loudnorm metrics
        output = {
            "Integrated_LUFS": data.get("input_i"),
            "Loudness_Range_LU": data.get("input_lra"),
            "True_Peak_dBTP": data.get("input_tp"),
            "Threshold_LUFS": data.get("input_thresh"),
            "Target_Offset_LU": data.get("target_offset"),
            "LRA_Low_LUFS": data.get("input_lra_low"),
            "LRA_High_LUFS": data.get("input_lra_high")
        }
        return output

    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"FFmpeg failed: {e.stderr}") from e

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python measure_loudness.py \"C:/path/to/file\"")
        sys.exit(1)

    file_path = sys.argv[1]
    try:
        result = measure_loudness(file_path)
        print(json.dumps(result, indent=4))
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
