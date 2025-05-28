#!/usr/bin/env python3
import sys
import glob
import subprocess
import os
import argparse

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
    "mono": 1,
    "stereo": 2,
    "2.1": 3,
    "3.0": 3,
    "3.0(back)": 3,
    "4.0": 4,
    "quad": 4,
    "quad(side)": 4,
    "3.1": 4,
    "5.0": 5,
    "5.0(side)": 5,
    "4.1": 5,
    "5.1": 6,
    "5.1(side)": 6,
    "6.0": 6,
    "6.0(front)": 6,
    "3.1.2": 6,
    "hexagonal": 6,
    "6.1": 7,
    "6.1(back)": 7,
    "6.1(front)": 7,
    "7.0": 7,
    "7.0(front)": 7,
    "7.1": 8,
    "7.1(wide)": 8,
    "7.1(wide-side)": 8,
    "5.1.2": 8,
    "octagonal": 8,
    "cube": 8,
    "5.1.4": 10,
    "7.1.2": 10,
    "7.1.4": 10,
    "7.2.3": 12,
    "9.1.4": 14,
    "hexadecagonal": 16,
    "downmix": 2,
    "22.2": 24
}

def calculate_channel_count(layout: str) -> int:
    """
    Try to calculate the channel count by splitting the layout string on dots.
    If all parts are numeric, we sum them. Otherwise, use a lookup table.
    """
    parts = layout.split('.')
    try:
        return sum(int(p) for p in parts)
    except ValueError:
        return NAMED_LAYOUTS.get(layout, 6)  # default to 6 channels if unknown

def select_audio_encoder(channels: int) -> (str, str):
    """
    Selects an audio encoder based on the desired channel count.
    Priority:
      - If channels <= 6: use AC3.
      - If channels <= 8: use E-AC3.
      - Otherwise, we currently do not support layouts with more than 8 channels.
    Returns a tuple: (encoder, bitrate)
    """
    if channels <= 6:
        return "ac3", "640k"
    elif channels <= 8:
        return "eac3", "640k"
    else:
        return None, None

def parse_arguments():
    parser = argparse.ArgumentParser(
        description=(
            "Convert video files so that the video stream is copied and "
            "the audio is converted to a specified codec at 640kbps with a given channel layout.\n\n"
            "Default encoder is AC3 for up to 6 channels; if more channels (up to 8) are requested, "
            "E-AC3 is used. Layouts requiring more than 8 channels are not supported by this script.\n\n"
            "Possible layout values include: " + ", ".join(LAYOUTS)
        ),
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("pattern", help="Input file pattern (e.g., \"*.mkv\")")
    parser.add_argument("-l", "--layout", default="5.1",
                        help="Desired audio channel layout. Possible values:\n" +
                             ", ".join(LAYOUTS) + "\n(default: 5.1)")
    return parser.parse_args()

def main():
    args = parse_arguments()
    file_pattern = args.pattern
    desired_layout = args.layout
    channels = calculate_channel_count(desired_layout)
    
    # Check if the requested channel count is supported by our available encoders.
    if channels > 8:
        print(f"Error: Requested layout '{desired_layout}' implies {channels} channels, but maximum supported is 8 channels.")
        sys.exit(1)
    
    audio_encoder, audio_bitrate = select_audio_encoder(channels)
    if audio_encoder is None:
        print(f"Error: No encoder available for {channels} channels.")
        sys.exit(1)
    
    print(f"Desired layout: {desired_layout} => {channels} channel(s)")
    print(f"Selected audio encoder: {audio_encoder} at bitrate {audio_bitrate}")
    
    files = glob.glob(file_pattern)
    if not files:
        print(f"No files found matching: {file_pattern}")
        sys.exit(1)
    
    for file in files:
        print(f"Processing: {file}")
        base, _ = os.path.splitext(file)
        output_file = base + ".mp4"
        
        # Build the ffmpeg command:
        # - Copy first video stream.
        # - Convert first audio stream using the chosen encoder, bitrate, and channel count.
        # - Set metadata for channel_layout to the desired layout.
        command = [
            "ffmpeg",
            "-i", file,
            "-map", "0:v:0",
            "-c:v", "copy",
            "-map", "0:a:0",
            "-c:a", audio_encoder,
            "-b:a", audio_bitrate,
            "-ac:a", str(channels),
            "-metadata:s:a:0", f"channel_layout={desired_layout}",
            output_file
        ]
        
        print("Running command: " + " ".join(command))
        try:
            subprocess.run(command, check=True)
            print(f"Created: {output_file}")
        except subprocess.CalledProcessError as e:
            print(f"Error processing {file}: {e}")

if __name__ == '__main__':
    main()
