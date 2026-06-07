#!/usr/bin/env python3
"""
Convert video files by copying the video and re‑encoding the audio.

- Uses AAC at 640 kbps.
- Supports two downmix methods:
    `5.1` (default) – explicit channel layout via `-ch_layout <layout>`
    `6`           – channel count only via `-ac <channels>`
- Only processes layouts up to 8 channels (AAC limitation).
- By default searches for common video formats in the current directory.
"""

import sys
import glob
import subprocess
import os
import argparse
import shutil

# List of standard layout names as reported by "ffmpeg -layouts"
LAYOUTS = [
    "mono", "stereo", "2.1", "3.0", "3.0(back)", "4.0", "quad", "quad(side)",
    "3.1", "5.0", "5.0(side)", "4.1", "5.1", "5.1(side)", "6.0", "6.0(front)",
    "3.1.2", "hexagonal", "6.1", "6.1(back)", "6.1(front)", "7.0", "7.0(front)",
    "7.1", "7.1(wide)", "7.1(wide-side)", "5.1.2", "octagonal", "cube", "5.1.4",
    "7.1.2", "7.1.4", "7.2.3", "9.1.4", "hexadecagonal", "downmix", "22.2"
]

# Predefined mapping for common layout names to channel counts.
NAMED_LAYOUTS = {
    "mono": 1, "stereo": 2, "2.1": 3, "3.0": 3, "3.0(back)": 3, "4.0": 4,
    "quad": 4, "quad(side)": 4, "3.1": 4, "5.0": 5, "5.0(side)": 5, "4.1": 5,
    "5.1": 6, "5.1(side)": 6, "6.0": 6, "6.0(front)": 6, "3.1.2": 6,
    "hexagonal": 6, "6.1": 7, "6.1(back)": 7, "6.1(front)": 7, "7.0": 7,
    "7.0(front)": 7, "7.1": 8, "7.1(wide)": 8, "7.1(wide-side)": 8,
    "5.1.2": 8, "octagonal": 8, "cube": 8, "5.1.4": 10, "7.1.2": 10,
    "7.1.4": 10, "7.2.3": 12, "9.1.4": 14, "hexadecagonal": 16,
    "downmix": 2, "22.2": 24
}

def calculate_channel_count(layout: str) -> int:
    parts = layout.split('.')
    try:
        return sum(int(p) for p in parts)
    except ValueError:
        return NAMED_LAYOUTS.get(layout, 6)

def parse_arguments():
    parser = argparse.ArgumentParser(
        description=(
            "Convert video files by copying the video and re-encoding the audio.\n"
            "Utilizes native FFmpeg channel scaling via command-line options down to standard layouts."
        ),
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "pattern", nargs='?',
        default="*.[Mm][Pp]4|*.[Mm][Kk][Vv]|*.[Aa][Vv][Ii]|*.[Mm][Oo][Vv]|*.[Ww][Ee][Bb][Mm]|*.[Tt][Ss]",
        help="Input file pattern (e.g., \"*.mkv\"). If not provided, searches for common video formats."
    )
    parser.add_argument(
        "-l", "--layout", default="5.1",
        help="Desired audio channel layout. Possible values:\n" +
             ", ".join(LAYOUTS) + "\n(default: 5.1)"
    )
    parser.add_argument(
        "-d", "--downmix", choices=["5.1", "6"], default="5.1",
        help="Downmix method: '5.1' uses explicit channel layout (-ch_layout), "
             "'6' uses channel count only (-ac). Default: 5.1"
    )
    return parser.parse_args()

def main():
    args = parse_arguments()
    file_pattern = args.pattern
    desired_layout = args.layout
    downmix_method = args.downmix
    channels = calculate_channel_count(desired_layout)

    input_dir = "input"
    output_dir = "output"
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    # AAC encoding for all channel counts (up to 8 channels)
    audio_encoder = "aac_mf"
    audio_bitrate = "640k"

    if channels > 8:
        print(f"Error: Requested layout '{desired_layout}' implies {channels} channels, but AAC supports at most 8 channels.")
        sys.exit(1)

    print(f"Desired layout: {desired_layout} => {channels} channel(s)")
    if desired_layout == "5.1":
        print("Note: Forcing standard 5.1 channel layout sequence: FL, FR, FC, LFE, BL, BR")
    print(f"Selected audio encoder: {audio_encoder} at bitrate {audio_bitrate}")
    print(f"Downmix method: {downmix_method}")

    if args.pattern == "*.[Mm][Pp]4|*.[Mm][Kk][Vv]|*.[Aa][Vv][Ii]|*.[Mm][Oo][Vv]|*.[Ww][Ee][Bb][Mm]|*.[Tt][Ss]":
        extensions = ['*.mp4', '*.MP4', '*.mkv', '*.MKV', '*.avi', '*.AVI', '*.mov', '*.MOV', '*.webm', '*.WEBM', '*.ts', '*.TS']
        files = []
        for ext in extensions:
            files.extend(glob.glob(ext))
        files = list(set(files))
    else:
        files = glob.glob(file_pattern)

    if not files:
        print(f"No files found matching: {file_pattern}")
        sys.exit(1)

    success_items = []
    failed_items = []

    for file in files:
        print(f"\nProcessing: {file}")

        base, _ = os.path.splitext(os.path.basename(file))
        output_file = os.path.join(output_dir, base + ".mp4")

        # Build the downmix arguments based on the chosen method
        if downmix_method == "5.1":
            # Explicit channel layout (e.g. -ch_layout 5.1)
            layout_args = ["-ch_layout", desired_layout]
        else:  # "6"
            # Channel count only (e.g. -ac 6)
            layout_args = ["-ac", str(channels)]

        command = [
            "ffmpeg", "-y",
            "-i", file,
            "-map", "0:v:0",
            "-c:v", "copy",
            "-map", "0:a",
            "-c:a", audio_encoder,
            "-b:a", audio_bitrate,
        ] + layout_args + [
            output_file
        ]

        print("Running command: " + " ".join(command))

        # --- Run ffmpeg with real‑time stderr output ---
        stderr_lines = []
        try:
            proc = subprocess.Popen(
                command,
                stderr=subprocess.PIPE,
                stdout=subprocess.DEVNULL,   # ignore stdout (ffmpeg uses stderr for progress)
                text=True,
                encoding="utf-8",
                errors="replace"
            )
            # Stream stderr line by line, printing to console and collecting for later
            for line in proc.stderr:
                sys.stderr.write(line)        # display progress live
                sys.stderr.flush()
                stderr_lines.append(line)     # save for error reporting
            proc.wait()
        except Exception as e:
            print(f"Unexpected error running ffmpeg: {e}")
            failed_items.append({
                "source": file,
                "status": "script_error",
                "reason": str(e),
            })
            continue

        if proc.returncode == 0:
            print(f"Successfully created: {output_file}")
            shutil.move(file, os.path.join(input_dir, os.path.basename(file)))
            print(f"Moved original file to: {os.path.join(input_dir, os.path.basename(file))}")
            success_items.append({
                "source": file,
                "output": output_file,
                "status": "ok",
            })
        else:
            print(f"Error processing {file}: ffmpeg exited with code {proc.returncode}")
            stderr_output = "".join(stderr_lines).strip()
            if not stderr_output:
                stderr_output = "No stderr captured"
            print(f"FFmpeg Error Output:\n{stderr_output}")
            failed_items.append({
                "source": file,
                "status": "ffmpeg_error",
                "returncode": proc.returncode,
                "reason": stderr_output,
            })

    print("\n" + "=" * 72)
    print("Processing summary")
    print("=" * 72)
    print(f"Total files discovered : {len(files)}")
    print(f"Successful conversions : {len(success_items)}")
    print(f"Not processed / failed : {len(failed_items)}")

    if success_items:
        print("\nSuccessful files:")
        for idx, item in enumerate(success_items, 1):
            print(f"{idx}. {item['source']}")
            print(f"   Output: {item['output']}")

    if failed_items:
        print("\nFailed files:")
        for idx, item in enumerate(failed_items, 1):
            print(f"{idx}. {item['source']}")
            if "returncode" in item:
                print(f"   Return code: {item['returncode']}")
            print(f"   Type: {item['status']}")
            reason = item.get("reason", "").strip()
            if reason:
                print("   Reason:")
                for line in reason.splitlines()[:12]:
                    print(f"   {line}")
                if len(reason.splitlines()) > 12:
                    print("   ... (truncated)")

if __name__ == '__main__':
    main()