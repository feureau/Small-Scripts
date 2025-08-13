import srt
import subprocess
import os
import re
from datetime import timedelta
import glob

def clean_filename(text):
    """
    Removes characters that are not allowed in filenames.
    """
    text = re.sub(r'[^\w\s-]', '', text)
    text = text.replace(' ', '_')
    return text

def get_video_duration(video_file):
    """
    Gets the duration of a video file in seconds using ffprobe.
    """
    # Use utf-8 encoding to prevent errors on Windows
    cmd = [
        'ffprobe',
        '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        video_file
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, encoding='utf-8', errors='ignore')
        return float(result.stdout)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: ffprobe not found or an error occurred while getting video duration.")
        return None

def split_video(video_file, srt_file):
    """
    Splits a video file based on the start times of subtitles in an SRT file.
    """
    print(f"\nProcessing video: {video_file}")
    if not os.path.exists(video_file):
        print(f"Error: Video file not found at {video_file}")
        return

    if not os.path.exists(srt_file):
        print(f"Error: SRT file not found at {srt_file}")
        return

    video_duration = get_video_duration(video_file)
    if video_duration is None:
        return

    try:
        with open(srt_file, 'r', encoding='utf-8') as f:
            subtitles = list(srt.parse(f.read()))
    except Exception as e:
        print(f"Error parsing SRT file {srt_file}: {e}")
        return

    if not subtitles:
        print("No subtitles found in the SRT file.")
        return

    subtitles.sort(key=lambda s: s.start)

    video_filename_without_ext = os.path.splitext(os.path.basename(video_file))[0]
    output_dir = os.path.join(os.getcwd(), video_filename_without_ext + "_split")
    os.makedirs(output_dir, exist_ok=True)
    print(f"Outputting segments to: {output_dir}")

    for i, sub in enumerate(subtitles):
        start_time = sub.start
        end_time = None

        if i + 1 < len(subtitles):
            end_time = subtitles[i+1].start
        else:
            end_time = timedelta(seconds=video_duration)

        output_filename = f"{clean_filename(sub.content)}.mp4"
        output_path = os.path.join(output_dir, output_filename)

        print(f"  - Creating segment: {output_filename}")

        cmd = [
            'ffmpeg',
            '-i', video_file,
            '-ss', str(start_time),
            '-to', str(end_time),
            '-c', 'copy',
            '-y',
            output_path
        ]

        try:
            # --- THIS IS THE FIX ---
            # Added encoding='utf-8' and errors='ignore' to prevent UnicodeDecodeError on Windows
            subprocess.run(cmd, check=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')
            # ----------------------
        except subprocess.CalledProcessError as e:
            print(f"    Error splitting video for segment: {output_filename}")
            print(f"    ffmpeg stderr: {e.stderr.strip()}")


def main():
    """
    Finds all video/SRT pairs in the current directory and processes them.
    """
    working_dir = os.getcwd()
    print(f"Searching for video and SRT files in: {working_dir}")

    video_files = glob.glob(os.path.join(working_dir, '*.mp4'))

    if not video_files:
        print("No .mp4 files found in this directory.")
        return

    print(f"Found {len(video_files)} video file(s).")
    for video_file in video_files:
        srt_file = os.path.splitext(video_file)[0] + '.srt'

        if os.path.exists(srt_file):
            split_video(video_file, srt_file)
        else:
            print(f"\nSkipping {os.path.basename(video_file)}: Corresponding SRT file not found.")

if __name__ == '__main__':
    main()