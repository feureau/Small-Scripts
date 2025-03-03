import os
import sys
import re
import subprocess
import wave
import glob

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

def get_duration(filename):
    """
    Uses the wave module to return the duration of a WAV file in seconds.
    """
    try:
        with wave.open(filename, 'rb') as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            duration = frames / float(rate)
        return duration
    except Exception as e:
        print(f"Error reading {filename} with wave module: {e}")
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

def main():
    if len(sys.argv) < 2:
        print("Usage: mergewav.py *.wav")
        sys.exit(1)

    # Expand wildcards using glob. Windows command-line doesn't auto-expand wildcards.
    input_patterns = sys.argv[1:]
    wav_files = []
    for pattern in input_patterns:
        # If the argument contains wildcards, expand it.
        if '*' in pattern or '?' in pattern:
            expanded = glob.glob(pattern)
            wav_files.extend(expanded)
        else:
            wav_files.append(pattern)
    
    if not wav_files:
        print("No WAV files found matching the given pattern(s).")
        sys.exit(1)

    # Sort files numerically based on the first number found in the filename
    sorted_files = sorted(wav_files, key=numeric_sort_key)
    print("Merging the following files in order:")
    for f in sorted_files:
        print("  ", f)

    # Create a temporary file list for ffmpeg's concat demuxer
    filelist_name = "filelist.txt"
    try:
        with open(filelist_name, "w", encoding="utf-8") as f:
            for wav_file in sorted_files:
                # ffmpeg expects each line to be: file 'filename'
                f.write("file '{}'\n".format(wav_file))
    except Exception as e:
        print("Error writing filelist.txt:", e)
        sys.exit(1)

    # Compute chapters (start and end times) based on each file's duration.
    chapters = []
    cumulative = 0.0
    for wav_file in sorted_files:
        duration = get_duration(wav_file)
        chapter = {
            "title": os.path.basename(wav_file),
            "start": cumulative,
            "end": cumulative + duration
        }
        chapters.append(chapter)
        cumulative += duration

    # Generate ffmetadata file (metadata.txt) for chapter markers.
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

    # Define the output file name.
    output_file = "merged.wav"

    # Build the ffmpeg command.
    cmd = [
        "ffmpeg",
        "-f", "concat",
        "-safe", "0",
        "-i", filelist_name,
        "-i", metadata_file,
        "-map_metadata", "1",
        "-c", "copy",
        output_file
    ]
    try:
        print("\nRunning ffmpeg command to merge files and embed chapter markers...")
        subprocess.run(cmd, check=True)
        print("\nMerged file created:", output_file)
        print("SRT file with chapter markers created:", srt_file)
    except subprocess.CalledProcessError as e:
        print("ffmpeg encountered an error:", e)
    except Exception as err:
        print("An error occurred:", err)
    finally:
        # Clean up temporary files.
        if os.path.exists(filelist_name):
            os.remove(filelist_name)
        if os.path.exists(metadata_file):
            os.remove(metadata_file)

if __name__ == '__main__':
    main()
