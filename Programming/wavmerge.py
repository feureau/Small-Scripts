#!/usr/bin/env python3
import sys
import glob
import os
from pydub import AudioSegment

def mix_wav_files(file_patterns, output_filename_base="mixed"):
    """
    Mixes multiple WAV files based on glob patterns into a single WAV file.

    Args:
        file_patterns: A list of glob patterns to find WAV files.
        output_filename_base: Base for the output filename.
    """
    mixed_audio = None  # Initialize to None to handle the first audio file differently
    input_filenames_base = []
    found_files = False

    for pattern in file_patterns:
        for filepath in glob.glob(pattern):
            if filepath.lower().endswith(".wav"):
                found_files = True
                print(f"Adding file for mixing: {filepath}")
                try:
                    audio = AudioSegment.from_wav(filepath)
                    # For the first audio file, initialize mixed_audio.
                    # For subsequent files, overlay them onto mixed_audio.
                    if mixed_audio is None:
                        mixed_audio = audio
                    else:
                        mixed_audio = mixed_audio.overlay(audio)

                    # Extract base filename for output name
                    base_name = os.path.splitext(os.path.basename(filepath))[0]
                    input_filenames_base.append(base_name)

                except Exception as e:
                    print(f"Error loading {filepath}: {e}")
            else:
                print(f"Skipping non-wav file: {filepath}")

    if not found_files:
        print("No WAV files found matching the provided patterns.")
        return

    if mixed_audio is not None: # Check if any audio was actually loaded and mixed
        # Construct output filename from input filenames' base names
        if input_filenames_base:
            output_filename = "_".join(input_filenames_base) + "_mixed.wav"
            if len(output_filename) > 255: # Example max filename length
                output_filename = input_filenames_base[0] + "_and_others_mixed.wav"
        else:
            output_filename = output_filename_base + ".wav" # Fallback if no filenames captured

        try:
            mixed_audio.export(output_filename, format="wav")
            print(f"Mixed audio saved to: {output_filename}")
        except Exception as e:
            print(f"Error exporting mixed audio: {e}")
    else:
        print("No audio segments to mix.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: wavmix.py <wav_file_pattern1> <wav_file_pattern2> ...") # Changed usage message to wavmix.py
        sys.exit(1)

    file_patterns = sys.argv[1:]
    mix_wav_files(file_patterns) # Using the mix_wav_files function