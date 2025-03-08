import os
import sys
import re
import subprocess
import glob
import argparse

def fix_optional_args(argv):
    """
    Preprocess sys.argv so that if -s/--silence or -sr/--sample-rate is
    provided without a valid numeric value immediately following, insert
    the default value.
    """
    new_argv = [argv[0]]
    i = 1
    while i < len(argv):
        arg = argv[i]
        if arg in ("-s", "--silence"):
            if i + 1 < len(argv) and not argv[i+1].startswith('-'):
                try:
                    float(argv[i+1])
                    new_argv.append(arg)
                    new_argv.append(argv[i+1])
                    i += 2
                except ValueError:
                    new_argv.append(arg)
                    new_argv.append("5")
                    i += 1
            else:
                new_argv.append(arg)
                new_argv.append("5")
                i += 1
        elif arg in ("-sr", "--sample-rate"):
            if i + 1 < len(argv) and not argv[i+1].startswith('-'):
                try:
                    int(argv[i+1])
                    new_argv.append(arg)
                    new_argv.append(argv[i+1])
                    i += 2
                except ValueError:
                    new_argv.append(arg)
                    new_argv.append("48000")
                    i += 1
            else:
                new_argv.append(arg)
                new_argv.append("48000")
                i += 1
        else:
            new_argv.append(arg)
            i += 1
    return new_argv

# Preprocess sys.argv before parsing with argparse.
sys.argv = fix_optional_args(sys.argv)

def numeric_sort_key(filename):
    """
    Returns the first number found in the base filename as an integer.
    If no number is found, returns the lowercased filename.
    """
    base = os.path.splitext(os.path.basename(filename))[0]
    match = re.search(r'\d+', base)
    if match:
        return int(match.group(0))
    else:
        return base.lower()

def get_audio_properties(filename):
    """
    Uses ffprobe to extract sample rate and channel count from an audio file.
    """
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "a:0",
            "-show_entries", "stream=sample_rate,channels",
            "-of", "default=noprint_wrappers=1:nokey=1",
            filename
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        lines = result.stdout.strip().split('\n')
        if len(lines) >= 2:
            sample_rate = int(lines[0])
            channels = int(lines[1])
            return sample_rate, channels
        else:
            return None, None
    except Exception as e:
        print(f"Error getting audio properties from {filename}: {e}")
        return None, None

def get_duration(filename):
    """
    Uses ffprobe to return the duration of an audio file in seconds.
    Works for WAV, MP3, and most other formats.
    """
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "a:0",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            filename
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        duration = float(result.stdout.strip())
        return duration
    except Exception as e:
        print(f"Error reading {filename} with ffprobe: {e}")
        return 0

def seconds_to_timestamp(seconds):
    """
    Converts a float seconds value to an SRT-formatted timestamp string.
    Format: HH:MM:SS,mmm
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds - int(seconds)) * 1000))
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

def generate_silence_file(filename, duration, in_sample_rate, channels):
    """
    Uses ffmpeg to generate a WAV file containing silence.
    The silence file is generated with the same sample rate and channel count as the input files.
    """
    channel_layout = "mono" if channels == 1 else "stereo" if channels == 2 else "stereo"
    cmd = [
        "ffmpeg", "-y",  # Overwrite if exists
        "-f", "lavfi",
        "-i", f"anullsrc=r={in_sample_rate}:cl={channel_layout}",
        "-t", str(duration),
        "-ac", str(channels),
        "-c:a", "pcm_s16le",
        filename
    ]
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print("Error generating silence file:", e)
        sys.exit(1)

def convert_to_wav(input_file, output_file, sample_rate, channels):
    """
    Converts an input audio file to WAV with the given sample rate and channel count.
    """
    cmd = [
        "ffmpeg", "-y",
        "-i", input_file,
        "-ar", str(sample_rate),
        "-ac", str(channels),
        "-c:a", "pcm_s16le",
        output_file
    ]
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error converting {input_file} to WAV:", e)
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description="Merge WAV/MP3 files with chapter markers and optional silence gaps."
    )
    parser.add_argument("files", nargs="+", help="Input WAV/MP3 files (wildcards allowed)")
    parser.add_argument("-s", "--silence", nargs="?", type=float,
                        help="Add silence (in seconds) after every file (default: 5 seconds if flag is used without a value)")
    parser.add_argument("-sr", "--sample-rate", type=int, default=48000,
                        help="Target sample rate for output (default: 48000)")
    args = parser.parse_args()

    # Expand wildcards for input files.
    input_files = []
    for pattern in args.files:
        if '*' in pattern or '?' in pattern:
            expanded = glob.glob(pattern)
            input_files.extend(expanded)
        else:
            input_files.append(pattern)

    if not input_files:
        print("No files found matching the given pattern(s).")
        sys.exit(1)

    # Sort files numerically.
    sorted_files = sorted(input_files, key=numeric_sort_key)
    print("Merging the following files in order:")
    for f in sorted_files:
        print("  ", f)

    # Get audio properties from the first input file.
    in_sample_rate, channels = get_audio_properties(sorted_files[0])
    if in_sample_rate is None or channels is None:
        print("Could not determine audio properties from the first input file.")
        sys.exit(1)

    # Convert all input files to temporary WAV files with identical parameters.
    converted_files = []
    for idx, infile in enumerate(sorted_files, start=1):
        temp_wav = f"temp_{idx:03d}.wav"
        print(f"Converting {infile} to {temp_wav} with {in_sample_rate} Hz and {channels} channel(s)")
        convert_to_wav(infile, temp_wav, in_sample_rate, channels)
        converted_files.append(temp_wav)

    # If silence is enabled, generate a temporary silence file.
    silence_file = None
    if args.silence is not None:
        silence_duration = args.silence
        silence_file = "silence.wav"
        print(f"Generating {silence_duration} seconds of silence in file: {silence_file} with {in_sample_rate} Hz and {channels} channel(s)")
        generate_silence_file(silence_file, silence_duration, in_sample_rate, channels)

    # Create a temporary file list for ffmpeg's concat demuxer.
    # Use the converted WAV files and interleave the silence file if enabled.
    filelist_name = "filelist.txt"
    try:
        with open(filelist_name, "w", encoding="utf-8") as f:
            for wav_file in converted_files:
                f.write("file '{}'\n".format(wav_file))
                if silence_file is not None:
                    f.write("file '{}'\n".format(silence_file))
    except Exception as e:
        print("Error writing filelist.txt:", e)
        sys.exit(1)

    # Compute chapters based on each converted file's duration and update cumulative time.
    chapters = []
    cumulative = 0.0
    for wav_file in converted_files:
        duration = get_duration(wav_file)
        chapter = {
            "title": os.path.basename(wav_file),
            "start": cumulative,
            "end": cumulative + duration
        }
        chapters.append(chapter)
        cumulative += duration
        if args.silence is not None:
            cumulative += args.silence

    # Generate ffmetadata file for chapter markers.
    metadata_file = "metadata.txt"
    try:
        with open(metadata_file, "w", encoding="utf-8") as f:
            f.write(";FFMETADATA1\n")
            for chapter in chapters:
                f.write("[CHAPTER]\n")
                f.write("TIMEBASE=1/1000\n")
                f.write("START={}\n".format(int(chapter["start"] * 1000)))
                f.write("END={}\n".format(int(chapter["end"] * 1000)))
                f.write("title={}\n".format(chapter["title"]))
    except Exception as e:
        print("Error writing metadata.txt:", e)
        sys.exit(1)

    # Generate an SRT file with chapter markers.
    srt_file = "merged.srt"
    try:
        with open(srt_file, "w", encoding="utf-8") as f:
            for idx, chapter in enumerate(chapters, start=1):
                start_ts = seconds_to_timestamp(chapter["start"])
                end_ts = seconds_to_timestamp(chapter["end"])
                f.write(f"{idx}\n")
                f.write(f"{start_ts} --> {end_ts}\n")
                f.write(f"{chapter['title']}\n\n")
    except Exception as e:
        print("Error writing SRT file:", e)
        sys.exit(1)

    # Define the output file.
    output_file = "merged.wav"
    target_sample_rate = args.sample_rate

    # Build the ffmpeg command.
    # Re-encode the audio (instead of copying) to force a uniform output sample rate.
    cmd = [
        "ffmpeg",
        "-f", "concat",
        "-safe", "0",
        "-i", filelist_name,
        "-i", metadata_file,
        "-map_metadata", "1",
        "-ar", str(target_sample_rate),
        "-c:a", "pcm_s16le",
        output_file
    ]
    try:
        print("\nRunning ffmpeg command to merge files and embed chapter markers with sample rate conversion...")
        subprocess.run(cmd, check=True)
        print("\nMerged file created:", output_file)
        print("SRT file with chapter markers created:", srt_file)
    except subprocess.CalledProcessError as e:
        print("ffmpeg encountered an error:", e)
    except Exception as err:
        print("An error occurred:", err)
    finally:
        # Clean up temporary files.
        for tmp in [filelist_name, metadata_file]:
            if os.path.exists(tmp):
                os.remove(tmp)
        if silence_file is not None and os.path.exists(silence_file):
            os.remove(silence_file)
        # Remove temporary converted files.
        for tmp in converted_files:
            if os.path.exists(tmp):
                os.remove(tmp)

if __name__ == '__main__':
    main()
