import os
import sys
import subprocess
import time
import cv2
import platform
from collections import Counter
import json

def get_video_color_info(video_file):
    """
    Extract color-related metadata using ffprobe in JSON format:
    - color_range
    - color_primaries
    - color_transfer (transfer characteristics)
    - color_space (matrix coefficients)
    - mastering_display_metadata (if present)
    """
    cmd = [
        "ffprobe", "-v", "error", "-show_streams", "-of", "json", video_file
    ]
    try:
        output = subprocess.check_output(
            cmd,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
    except subprocess.CalledProcessError:
        return None, None, None, None, None

    data = json.loads(output)
    streams = data.get("streams", [])
    video_stream = None
    for s in streams:
        if s.get("codec_type") == "video":
            video_stream = s
            break

    if not video_stream:
        return None, None, None, None, None

    color_range = video_stream.get("color_range")
    color_primaries = video_stream.get("color_primaries")
    color_transfer = video_stream.get("color_transfer")
    color_space = video_stream.get("color_space")

    mastering_display_metadata = None
    if "side_data_list" in video_stream:
        for side_data in video_stream["side_data_list"]:
            if side_data.get("side_data_type") == "Mastering display metadata":
                mastering_display_metadata = side_data.get("display_primaries", side_data)
                break

    return color_range, color_primaries, color_transfer, color_space, mastering_display_metadata

def run_ffprobe_for_audio_streams(video_file):
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "a", 
        "-show_entries", "stream=index,codec_name:stream_tags=language",
        "-of", "json", video_file
    ]
    try:
        output = subprocess.check_output(
            cmd, 
            stderr=subprocess.STDOUT, 
            text=True, 
            encoding='utf-8', 
            errors='replace'
        )
    except subprocess.CalledProcessError:
        return []

    data = json.loads(output)
    streams = data.get("streams", [])
    audio_info = []
    for s in streams:
        idx = s.get("index")
        codec = s.get("codec_name")
        language = s.get("tags", {}).get("language", None)
        audio_info.append({"index": idx, "codec": codec, "language": language})
    return audio_info

def get_video_resolution(video_file):
    cap = cv2.VideoCapture(video_file)
    if not cap.isOpened():
        print(f"Unable to open video file: {video_file}")
        return None, None
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    return height, width

def get_video_duration(video_file):
    cap = cv2.VideoCapture(video_file)
    if not cap.isOpened():
        print(f"Unable to open video file: {video_file}")
        return None
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    duration = frame_count / fps if fps else None
    cap.release()
    return duration

def get_user_input(prompt, default=None):
    user_input = input(prompt)
    return user_input if user_input else default

def get_crop_parameters(video_file, input_width, input_height):
    print("Detecting optimal crop parameters...")
    duration = get_video_duration(video_file)
    if duration is None or duration < 1:
        print("Unable to determine video duration or video is too short.")
        return None, None, None, None

    crop_values = []
    for i in range(12):  # Sampling 12 frames
        start_time = (duration / 12) * i
        command = [
            "ffmpeg",
            "-ss", str(start_time),
            "-i", video_file,
            "-vframes", "3",
            "-vf", "cropdetect=64:4:0",
            "-f", "null",
            "-",
            "-hide_banner",
            "-loglevel", "verbose"
        ]
        try:
            process = subprocess.Popen(
                command,
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            stdout, stderr = process.communicate()
            ffmpeg_output = (stdout or '') + (stderr or '')
            for line in ffmpeg_output.split('\n'):
                if 'crop=' in line:
                    crop_str = line.split('crop=')[1].strip()
                    crop_values.append(crop_str)
        except Exception as e:
            print(f"Error while running cropdetect: {e}")
            continue

    if crop_values:
        most_common_crop = Counter(crop_values).most_common(1)[0][0]
        w, h, x, y = [int(v) for v in most_common_crop.split(':')]
        if w == input_width and h == input_height and x == 0 and y == 0:
            print("No cropping needed. Full frame detected.")
            return None, None, None, None

        print(f"Detected crop parameters: width={w}, height={h}, x={x}, y={y}")
        redo = get_user_input("Are you satisfied with the detected crop parameters? [Y/N]: ", "Y").lower()
        if redo == "n":
            return get_crop_parameters(video_file, input_width, input_height)

        return w, h, x, y

    print("No crop parameters found.")
    return None, None, None, None

def main():
    if len(sys.argv) < 2:
        print("No video file specified. Please drag and drop a video file onto the script.")
        sys.exit()

    video_files = sys.argv[1:]

    for video_file in video_files:
        input_height, input_width = get_video_resolution(video_file)
        if input_height is None or input_width is None:
            continue

        crop_w, crop_h, crop_x, crop_y = get_crop_parameters(video_file, input_width, input_height)
        crop_params = f"{crop_x},{crop_y},{input_width - crop_w - crop_x},{input_height - crop_h - crop_y}" if crop_w else ""

        target_height = int(get_user_input(f"Enter target vertical height (in pixels) [{input_height}]: ", str(input_height)))
        target_width = int(get_user_input(f"Enter target horizontal width (in pixels) [{input_width}]: ", str(input_width)))

        qvbr = get_user_input(f"Enter target QVBR quality setting (lower is better) [20]: ", "20")

        hdr_enable = get_user_input("Enable HDR conversion? [Y/N]: ", "N").lower()
        hdr_options = []
        if hdr_enable == "y":
            hdr_options = ["--vpp-ngx-truehdr", "--colormatrix", "bt2020nc", "--colorprim", "bt2020", "--transfer", "smpte2084"]

        fruc_enable = get_user_input("Enable frame rate upconversion to 60 fps? [Y/N]: ", "N").lower()
        fruc_options = ["--vpp-fruc", "fps=60"] if fruc_enable == "y" else []

        audio_streams = run_ffprobe_for_audio_streams(video_file)
        if audio_streams:
            print("Detected Audio Tracks:")
            for a in audio_streams:
                lang_str = f" [{a['language']}]" if a['language'] else ""
                print(f"Track {a['index']}: codec={a['codec']}{lang_str}")

            selected_tracks = get_user_input("Enter the audio track numbers to include (comma separated, default all): ", "")
            if selected_tracks:
                selected_tracks = [int(x.strip()) for x in selected_tracks.split(",") if x.strip().isdigit()]
            else:
                selected_tracks = [a['index'] for a in audio_streams]

            audio_options = []
            audio_choice = get_user_input("Copy audio or convert to AC3? [1: Copy, 2: Convert]: ", "1")
            if audio_choice == "1":
                audio_options = ["--audio-copy"]
            else:
                audio_options = ["--audio-codec", "ac3", "--audio-bitrate", "640"]

            for track in selected_tracks:
                audio_options.extend(["--audio-stream", str(track)])
        else:
            print("No audio tracks found.")
            audio_options = []

        gop_len = get_user_input("Enter GOP length [6]: ", "6")

        output_file = os.path.abspath(f"{os.path.splitext(video_file)[0]}_HDR_{int(time.time())}.mkv")

        command = [
            "NVEncC64", "--codec", "av1", "--qvbr", qvbr, "--preset", "p4",
            "--output-depth", "10", "--multipass", "2pass-full", "--gop-len", gop_len,
            "--chapter-copy", "--key-on-chapter", "--metadata", "copy",
            "-i", video_file, "-o", output_file
        ] + fruc_options + hdr_options + audio_options

        if crop_params:
            command.extend(["--crop", crop_params])

        try:
            print("Running command:", " ".join(command))
            subprocess.run(command, check=True, text=True)
            print(f"Processed file: {output_file}")
        except subprocess.CalledProcessError as e:
            print(f"Error processing {video_file}: {e}")

if __name__ == "__main__":
    main()
