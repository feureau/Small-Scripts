import os
import sys
import subprocess
import time
import cv2
import platform
from collections import Counter
import json
import re

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

def get_user_input(prompt, default=None):
    user_input = input(prompt)
    return user_input if user_input else default

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
def get_crop_parameters(video_file, input_width, input_height):
    print("Detecting optimal crop parameters throughout the video...")
    duration = get_video_duration(video_file)
    if duration is None or duration < 1:
        print("Unable to determine video duration or video is too short.")
        return None, None, None, None

    default_limit = "48"  # Updated default cropdetect limit value
    limit_value = get_user_input(f"Enter cropdetect limit value (higher detects more black areas) [{default_limit}]: ", default_limit)
    default_round = "4"
    round_value = get_user_input(f"Enter cropdetect round value (controls precision) [{default_round}]: ", default_round)

    sample_interval = 300  # 5 minutes in seconds
    num_samples = max(12, min(72, int(duration / sample_interval)))
    if num_samples < 12:
        num_samples = 12

    start_offset = min(300, duration * 0.05)
    interval = (duration - start_offset) / num_samples if duration > start_offset else duration / num_samples

    crop_values = []
    for i in range(num_samples):
        start_time = start_offset + i * interval if duration > start_offset else i * interval
        if start_time >= duration:
            start_time = duration - 1
        print(f"Analyzing frame at {int(start_time)}s ({i+1}/{num_samples})...")
        command = [
            "ffmpeg",
            "-ss", str(start_time),
            "-i", video_file,
            "-vframes", "3",
            "-vf", f"cropdetect={limit_value}:{round_value}:0",
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
                    idx = line.index('crop=')
                    crop_str = line[idx+5:].strip()
                    crop_values.append(crop_str)
                    w, h, x, y = [int(v) for v in crop_str.split(':')]
                    print(f"Detected crop at {int(start_time)}s: width={w}, height={h}, x={x}, y={y}")
        except Exception as e:
            print(f"Error while running cropdetect at {int(start_time)}s: {e}")
            continue

    if crop_values:
        crop_counter = Counter(crop_values)
        most_common_crop = crop_counter.most_common(1)[0][0]
        w, h, x, y = [int(v) for v in most_common_crop.split(':')]
        print(f"\nDetected optimal crop parameters: width={w}, height={h}, x={x}, y={y}")
    else:
        print("No crop parameters found.")
        w, h, x, y = input_width, input_height, 0, 0  # Default to full frame if none detected

    print(f"Detected crop parameters: width={w}, height={h}, x={x}, y={y}")
    redo_crop = get_user_input("Are you satisfied with the detected crop parameters? [Y/N] (default is Y): ", "Y").lower()
    if redo_crop in ["n", "0"]:
        print("Redoing crop detection...")
        return get_crop_parameters(video_file, input_width, input_height)

    return w, h, x, y
def collect_user_settings(video_file, input_width, input_height):
    """
    Collect settings from the user for the first file and return them as a dictionary.
    """
    settings = {}

    # Select decoding mode
    decode_choice = get_user_input(
        "Select decoding mode:\n[1] Hardware decoding (default)\n[2] Software decoding\nEnter choice (1 or 2) [1]: ", 
        "1"
    )
    settings['decode_flag'] = "--avhw" if decode_choice == "1" else "--avsw"

    # Crop detection
    crop_w, crop_h, crop_x, crop_y = get_crop_parameters(video_file, input_width, input_height)
    settings['crop_params'] = f"{crop_x},{crop_y},{input_width - crop_w - crop_x},{input_height - crop_h - crop_y}" if crop_w else ""

    # Print color-related metadata before HDR query
    color_range, color_primaries, color_transfer, color_space, mastering_display_metadata = get_video_color_info(video_file)
    print(f"Detected color_range: {color_range}")
    print(f"Detected color_primaries: {color_primaries}")
    print(f"Detected color_transfer (transfer characteristics): {color_transfer}")
    print(f"Detected color_space (matrix coefficients): {color_space}")
    if mastering_display_metadata:
        print("Detected mastering display metadata:")
        print(mastering_display_metadata)
    else:
        print("No mastering display metadata found.")

    # HDR Conversion
    settings['hdr_enable'] = get_user_input("Enable HDR Conversion? [Y/N/1/0] (default is N): ", "N").lower()

    # Resize to 4K
    settings['resize_enable'] = get_user_input("Enable Resize to 4K? [Y/N/1/0] (default is N): ", "N").lower()

    # FRUC (Frame Rate Up Conversion)
    settings['fruc_enable'] = get_user_input("Enable FRUC (fps=60)? [Y/N/1/0] (default is N): ", "N").lower()

    # Denoise
    settings['denoise_enable'] = get_user_input("Enable Denoise? [Y/N/1/0] (default is N): ", "N").lower()

    # Artifact Reduction
    settings['artifact_enable'] = get_user_input("Enable Artifact Reduction? [Y/N/1/0] (default is N): ", "N").lower()

    # Audio Handling
    audio_streams = run_ffprobe_for_audio_streams(video_file)
    settings['audio_tracks'] = []
    if audio_streams:
        track_selection = get_user_input("Enter the audio track numbers you want to process (comma separated): ")
        if track_selection:
            settings['audio_tracks'] = [int(x.strip()) for x in track_selection.split(",") if x.strip().isdigit()]
        else:
            settings['audio_tracks'] = [s['index'] for s in audio_streams]  # Default to all tracks

        if all(s['codec'] == 'ac3' for s in audio_streams if s['index'] in settings['audio_tracks']):
            audio_default = "1"
            print("All selected tracks are AC3. Defaulting to copy audio.")
        else:
            audio_default = "2"
            print("Not all selected tracks are AC3. Defaulting to convert to AC3.")

        settings['audio_choice'] = get_user_input(
            "Do you want to copy the audio or convert it to AC3?\n[1] Copy Audio\n[2] Convert to AC3\n"
            f"Enter choice (1 or 2) [{audio_default}]: ",
            audio_default
        )
    else:
        print("No audio tracks found. Proceeding with no audio.")
        settings['audio_choice'] = "1"  # Default to no conversion

    # QVBR and GOP
    settings['qvbr'] = get_user_input("Enter target QVBR [20]: ", "20")
    settings['gop_len'] = get_user_input("Enter GOP length [6]: ", "6")

    return settings
def process_video(file_path, settings):
    """
    Process a single video file using NVEncC with the provided settings.
    """
    input_dir = os.path.dirname(file_path)
    file_name = os.path.basename(file_path)
    output_subdir = os.path.join(input_dir, "processed_videos")
    os.makedirs(output_subdir, exist_ok=True)  # Ensure the output subfolder exists
    output_file = os.path.join(output_subdir, os.path.splitext(file_name)[0] + "_AV1.mkv")  # Updated suffix

    # Construct the command
    command = [
        "NVEncC64",
        settings['decode_flag'],  # Use hardware or software decoding based on user input
        "--codec", "av1",
        "--qvbr", settings['qvbr'],
        "--preset", "p4",
        "--output-depth", "10",
        "--gop-len", settings['gop_len'],
        "--metadata", "copy",
        "--audio-copy",  # Copy all audio streams
        "--sub-copy",  # Copy all subtitle streams
        "--chapter-copy",  # Copy chapters
        "--data-copy",  # Copy data streams
        "-i", file_path,
        "-o", output_file
    ]

    if settings['crop_params']:
        command.extend(["--crop", settings['crop_params']])

    if settings['resize_enable'] in ["y", "1"]:
        command.extend(["--vpp-resize", "algo=nvvfx-superres,superres-mode=0", "--output-res", "3840x2160"])

    if settings['fruc_enable'] in ["y", "1"]:
        command.extend(["--vpp-fruc", "fps=60"])

    if settings['artifact_enable'] in ["y", "1"]:
        command.extend(["--vpp-nvvfx-artifact-reduction", "mode=0"])

    if settings['denoise_enable'] in ["y", "1"]:
        command.extend(["--vpp-nvvfx-denoise"])

    if settings['hdr_enable'] in ["y", "1"]:
        command.extend(["--vpp-ngx-truehdr"])

    if settings['audio_tracks']:
        for track in settings['audio_tracks']:
            command.extend(["--audio-stream", str(track)])
        if settings['audio_choice'] == "2":
            command.extend(["--audio-codec", "ac3", "--audio-bitrate", "640"])

    print(f"Processing: {file_path}")
    try:
        subprocess.run(command, check=True)
        print(f"Success: Processed {file_path} -> {output_file}")
    except subprocess.CalledProcessError as e:
        print(f"Error: Failed to process {file_path}")
        print(e)

def process_batch(video_files):
    """
    Process a batch of video files, reusing settings from the first file.
    """
    settings = None

    for index, file_path in enumerate(video_files):
        if index == 0:
            input_height, input_width = get_video_resolution(file_path)
            if input_height is None or input_width is None:
                print(f"Error: Could not retrieve resolution for {file_path}. Skipping.")
                continue
            settings = collect_user_settings(file_path, input_width, input_height)
        else:
            print(f"Reusing settings for: {file_path}")

        process_video(file_path, settings)

def wait_for_any_key():
    if platform.system() == "Windows":
        import msvcrt
        print("Processing complete. Press any key to exit...")
        msvcrt.getch()
    else:
        print("Processing complete. Press any key to exit...")
        os.system("stty -echo -icanon")
        try:
            os.read(0, 1)
        finally:
            os.system("stty sane")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("No video file specified. Please drag and drop a video file onto the script.")
        input("Press any key to exit...")
        sys.exit()

    video_files = sys.argv[1:]
    process_batch(video_files)
    wait_for_any_key()
