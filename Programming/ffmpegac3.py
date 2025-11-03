#!/usr/bin/env python3
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

def select_audio_encoder(channels: int) -> (str, str):
    if channels <= 6:
        return "ac3", "640k"
    elif channels <= 8:
        return "eac3", "640k"
    else:
        return None, None

def parse_arguments():
    parser = argparse.ArgumentParser(
        description=(
            "Convert video files by copying the video and re-encoding the audio.\n"
            "When using the '5.1' layout, this script specifically outputs the 'film' \n"
            "channel order (L, C, R, Ls, Rs, LFE) for compatibility with DaVinci Resolve."
        ),
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("pattern", nargs='?', default="*.[Mm][Pp]4|*.[Mm][Kk][Vv]|*.[Aa][Vv][Ii]|*.[Mm][Oo][Vv]|*.[Ww][Ee][Bb][Mm]|*.[Tt][Ss]", 
                        help="Input file pattern (e.g., \"*.mkv\"). If not provided, searches for common video formats.")
    parser.add_argument("-l", "--layout", default="5.1",
                        help="Desired audio channel layout. Possible values:\n" +
                             ", ".join(LAYOUTS) + "\n(default: 5.1)")
    return parser.parse_args()

def main():
    args = parse_arguments()
    file_pattern = args.pattern
    desired_layout = args.layout
    channels = calculate_channel_count(desired_layout)

    input_dir = "input"
    output_dir = "output"
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    
    if channels > 8:
        print(f"Error: Requested layout '{desired_layout}' implies {channels} channels, but maximum supported is 8.")
        sys.exit(1)
    
    audio_encoder, audio_bitrate = select_audio_encoder(channels)
    if audio_encoder is None:
        print(f"Error: No encoder available for {channels} channels.")
        sys.exit(1)
    
    print(f"Desired layout: {desired_layout} => {channels} channel(s)")
    if desired_layout == "5.1":
        print("Note: Forcing 5.1 (film) channel layout: L, C, R, Ls, Rs, LFE")
    print(f"Selected audio encoder: {audio_encoder} at bitrate {audio_bitrate}")
    
    # Handle pattern differently - if it's the default, expand it to actual file patterns
    if args.pattern == "*.[Mm][Pp]4|*.[Mm][Kk][Vv]|*.[Aa][Vv][Ii]|*.[Mm][Oo][Vv]|*.[Ww][Ee][Bb][Mm]|*.[Tt][Ss]":
        # Use glob with multiple extensions
        extensions = ['*.mp4', '*.MP4', '*.mkv', '*.MKV', '*.avi', '*.AVI', '*.mov', '*.MOV', '*.webm', '*.WEBM', '*.ts', '*.TS']
        files = []
        for ext in extensions:
            files.extend(glob.glob(ext))
        files = list(set(files))  # Remove duplicates
    else:
        files = glob.glob(file_pattern)
    
    if not files:
        print(f"No files found matching: {file_pattern}")
        sys.exit(1)
    
    for file in files:
        print(f"Processing: {file}")
        
        base, _ = os.path.splitext(os.path.basename(file))
        output_file = os.path.join(output_dir, base + ".mp4")
        
        command = [
            "ffmpeg", "-y",
            "-i", file,
            "-map", "0:v:0",
            "-c:v", "copy",
            "-map", "0:a:0",
            "-c:a", audio_encoder,
            "-b:a", audio_bitrate,
            "-ac", str(channels),
            output_file
        ]

        print("Running command: " + " ".join(command))
        try:
            result = subprocess.run(command, check=True, capture_output=True, text=True)
            print(f"Successfully created: {output_file}")
            
            shutil.move(file, os.path.join(input_dir, os.path.basename(file)))
            print(f"Moved original file to: {os.path.join(input_dir, os.path.basename(file))}")

        except subprocess.CalledProcessError as e:
            print(f"Error processing {file}: {e}")
            print(f"FFmpeg Error Output:\n{e.stderr}")

if __name__ == '__main__':
    main()