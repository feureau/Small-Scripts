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
                # Attempt to extract the display_primaries if present, else store entire side_data
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

    default_limit = "64"
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
        if w == input_width and h == input_height and x == 0 and y == 0:
            print("No cropping needed. Full frame detected.")
            return None, None, None, None
        return w, h, x, y
    else:
        print("No crop parameters found.")
        return None, None, None, None

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

if len(sys.argv) < 2:
    print("No video file specified. Please drag and drop a video file onto the script.")
    input("Press any key to exit...")
    sys.exit()

video_files = sys.argv[1:]

# Ask user to select decoding mode
decode_choice = get_user_input("Select decoding mode:\n[1] Hardware decoding (default)\n[2] Software decoding\nEnter choice (1 or 2) [1]: ", "1")
decode_flag = "--avhw" if decode_choice == "1" else "--avsw"

for video_file in video_files:
    # Get resolution of input video
    input_height, input_width = get_video_resolution(video_file)
    if input_height is None or input_width is None:
        continue

    # Automatically set resolution option based on input
    res_choice = "1" if input_height <= 1080 else "2"
    default_qvbr = "20" if res_choice == "1" else "30"

    # Define encoding variables
    FRUC_VAR = ["--vpp-fruc", "fps=60"]
    RESIZE_VAR = ["--vpp-resize", "algo=nvvfx-superres,superres-mode=0", "--output-res", "3840x2160,preserve_aspect_ratio=decrease"]

    HDR_VPP = ["--vpp-ngx-truehdr"]
    HDR_CM = ["--colormatrix", "bt2020nc"]
    HDR_CP = ["--colorprim", "bt2020"]
    HDR_TR = ["--transfer", "smpte2084"]

    FRUC_OPTION = []
    RESIZE_OPTION = []
    ARTIFACT_REDUCTION_OPTION = []
    DENOISE_OPTION = []
    HDR_OPTION_LIST = []

    # Crop detection with redo option
    while True:
        crop_w, crop_h, crop_x, crop_y = get_crop_parameters(video_file, input_width, input_height)
        if crop_w is None or crop_h is None:
            print("Using full frame without cropping.")
            crop_params = ""
            target_height = input_height
            target_width = input_width
            left = 0
            top = 0
            right = 0
            bottom = 0
        else:
            redo_crop = get_user_input("Are you satisfied with the detected crop parameters? [Y/N] (default is Y): ", "Y").lower()
            if redo_crop in ["n", "0"]:
                print("Redoing crop detection...")
                continue
            # Adjust crop values to be divisible by 4
            crop_w -= crop_w % 4
            crop_h -= crop_h % 4
            crop_x -= crop_x % 4
            crop_y -= crop_y % 4
            left = crop_x
            top = crop_y
            right = input_width - crop_w - crop_x
            bottom = input_height - crop_h - crop_y
            crop_params = f"{left},{top},{right},{bottom}"
            target_height = crop_h
            target_width = crop_w
        break

    # Ask user for target heights and widths
    target_height = int(get_user_input(f"Enter target vertical height (in pixels) [{target_height}]: ", str(target_height)))
    top = (input_height - target_height) // 2
    top -= top % 4
    bottom = input_height - target_height - top

    target_width = int(get_user_input(f"Enter target horizontal width (in pixels) [{target_width}]: ", str(target_width)))
    left = (input_width - target_width) // 2
    left -= left % 4
    right = input_width - target_width - left

    # Reconstruct crop_params if changed
    if left == 0 and top == 0 and right == 0 and bottom == 0:
        crop_params = ""
    else:
        crop_params = f"{left},{top},{right},{bottom}"

    qvbr = get_user_input(f"Enter target QVBR [{default_qvbr}]: ", default_qvbr)

    if res_choice == "1":
        resize_enable = get_user_input("Enable Resize to 4K? [Y/N/1/0] (default is N): ", "N").lower()
        if resize_enable in ["y", "1"]:
            RESIZE_OPTION = RESIZE_VAR

    fruc_enable = get_user_input("Enable FRUC (fps=60)? [Y/N/1/0] (default is N): ", "N").lower()
    if fruc_enable in ["y", "1"]:
        FRUC_OPTION = FRUC_VAR

    if res_choice == "1":
        artifact_enable = get_user_input("Enable Artifact Reduction? [Y/N/1/0] (default is N): ", "N").lower()
        if artifact_enable in ["y", "1"]:
            ARTIFACT_REDUCTION_OPTION = ["--vpp-nvvfx-artifact-reduction", "mode=0"]

        denoise_enable = get_user_input("Enable Denoise? [Y/N/1/0] (default is N): ", "N").lower()
        if denoise_enable in ["y", "1"]:
            DENOISE_OPTION = ["--vpp-nvvfx-denoise"]

    # Extract and print extended color info
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

    # HDR Conversion always default to N, user must explicitly choose
    hdr_default = "N"
    hdr_enable = get_user_input(f"Enable HDR Conversion? [Y/N/1/0] (default is {hdr_default}): ", hdr_default).lower()
    if hdr_enable in ["y", "1"]:
        HDR_OPTION_LIST.extend(HDR_VPP)
        HDR_OPTION_LIST.extend(HDR_CM)
        HDR_OPTION_LIST.extend(HDR_CP)
        HDR_OPTION_LIST.extend(HDR_TR)

    # Audio track handling
    audio_streams = run_ffprobe_for_audio_streams(video_file)
    if not audio_streams:
        print("No audio tracks found. Proceeding with no audio.")
        selected_tracks = []
        audio_choice = "1"
    else:
        print("\nDetected Audio Tracks:")
        for a in audio_streams:
            lang_str = f" [{a['language']}]" if a['language'] else ""
            print(f"Track {a['index']}: codec={a['codec']}{lang_str}")

        track_selection = get_user_input("Enter the audio track numbers you want to process (comma separated): ")
        if not track_selection:
            selected_tracks = [a['index'] for a in audio_streams]
            print("No specific tracks selected, defaulting to all tracks.")
        else:
            selected_tracks = [int(x.strip()) for x in track_selection.split(",") if x.strip().isdigit()]

        if selected_tracks:
            all_ac3 = all((s['codec'] == 'ac3' for s in audio_streams if s['index'] in selected_tracks))
            if all_ac3:
                audio_default = "1"
                print("All selected tracks are AC3. Defaulting to copy audio.")
            else:
                audio_default = "2"
                print("Not all selected tracks are AC3. Defaulting to convert to AC3.")
        else:
            audio_default = "1"

        if selected_tracks:
            audio_choice = get_user_input(
                "Do you want to copy the audio or convert it to AC3?\n[1] Copy Audio\n[2] Convert to AC3\n"
                f"Enter choice (1 or 2) [{audio_default}]: ", 
                audio_default
            )
        else:
            audio_choice = "1"

    if selected_tracks:
        if audio_choice == "1":
            audio_codec_options = ["--audio-copy"]
        else:
            audio_codec_options = [
                "--audio-codec", "ac3",
                "--audio-bitrate", "640",
                "--audio-stream", ":5.1"
            ]
    else:
        audio_codec_options = []

    for t in selected_tracks:
        audio_codec_options.append("--audio-stream")
        audio_codec_options.append(str(t))

    gop_len = get_user_input("Enter GOP length [6]: ", "6")

    # Display chosen options
    print("\n--- Selected Encoding Options ---")
    print(f"Input File: {video_file}")
    print(f"Input Resolution: {input_width}x{input_height}")
    if crop_params:
        print(f"Crop Settings: Left={left}, Top={top}, Right={right}, Bottom={bottom}")
    else:
        print("Crop Settings: None")
    print(f"Target Resolution: {target_width}x{target_height}")
    print(f"Decoding Mode: {decode_flag}")
    print(f"QVBR Quality Setting: {qvbr}")
    print(f"FRUC 60p: {' '.join(FRUC_OPTION) if FRUC_OPTION else 'None'}")
    print(f"Resize to 4K: {' '.join(RESIZE_OPTION) if RESIZE_OPTION else 'None'}")
    print(f"Artifact Reduction: {' '.join(ARTIFACT_REDUCTION_OPTION) if ARTIFACT_REDUCTION_OPTION else 'None'}")
    print(f"Denoise: {' '.join(DENOISE_OPTION) if DENOISE_OPTION else 'None'}")
    if HDR_OPTION_LIST:
        print("HDR Conversion: " + ' '.join(HDR_OPTION_LIST))
    else:
        print("HDR Conversion: None")
    if selected_tracks:
        print("Selected Audio Tracks:", selected_tracks)
        print(f"Audio: {'Copy' if audio_choice == '1' else 'Convert to AC3'}")
    else:
        print("No audio selected.")
    print(f"GOP Length: {gop_len}")
    print("-------------------------------\n")

    output_file = os.path.abspath(f"{os.path.splitext(video_file)[0]}_HDR_{int(time.time())}.mkv")
    command = [
        "NVEncC64", decode_flag, "--codec", "av1", "--tier", "1", "--profile", "high",
        "--qvbr", qvbr, "--preset", "p7",
        "--output-depth", "10", "--multipass", "2pass-full", "--nonrefp", "--aq", "--aq-temporal",
        "--aq-strength", "0", "--lookahead", "32", "--gop-len", gop_len, "--lookahead-level", "auto",
        "--transfer", "auto", "--chapter-copy", "--key-on-chapter", "--metadata", "copy"
    ] + FRUC_OPTION + RESIZE_OPTION + ARTIFACT_REDUCTION_OPTION + DENOISE_OPTION + HDR_OPTION_LIST + [
        "-i", video_file, "-o", output_file
    ] + audio_codec_options

    if crop_params:
        command.extend(["--crop", crop_params])

    command = [arg for arg in command if arg]

    try:
        process = subprocess.Popen(
            command, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT, 
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        for line in iter(process.stdout.readline, ""):
            if line:
                print(line.strip())
        process.wait()
        if process.returncode != 0:
            print(f"Error while processing {video_file}. Exit code: {process.returncode}")
            continue
    except Exception as e:
        print(f"Error while running NVEncC64 for {video_file}: {e}")
        continue

    if not os.path.exists(output_file):
        print(f"Output file {output_file} was not created.")
        continue

    hdr_folder = os.path.abspath("HDR")
    if not os.path.exists(hdr_folder):
        try:
            os.makedirs(hdr_folder)
        except OSError as e:
            print(f"Failed to create HDR folder: {e}")
            continue

    try:
        hdr_output_path = os.path.join(hdr_folder, os.path.basename(output_file))
        os.replace(output_file, hdr_output_path)
        print(f"File moved to HDR folder: {hdr_output_path}")
    except OSError as e:
        print(f"Failed to move {output_file} to HDR folder: {e}")
        continue

    # Write settings to log
    log_file_path = os.path.join("HDR", "encoding_log.txt")
    with open(log_file_path, "a", encoding='utf-8', errors='replace') as log_file:
        log_file.write("--- Selected Encoding Options ---\n")
        log_file.write(f"Input File: {video_file}\n")
        log_file.write(f"Input Resolution: {input_width}x{input_height}\n")
        if crop_params:
            log_file.write(f"Crop Settings: Left={left}, Top={top}, Right={right}, Bottom={bottom}\n")
        else:
            log_file.write("Crop Settings: None\n")
        log_file.write(f"Target Resolution: {target_width}x{target_height}\n")
        log_file.write(f"QVBR Quality Setting: {qvbr}\n")
        log_file.write(f"FRUC 60p: {' '.join(FRUC_OPTION) if FRUC_OPTION else 'None'}\n")
        log_file.write(f"Resize to 4K: {' '.join(RESIZE_OPTION) if RESIZE_OPTION else 'None'}\n")
        log_file.write(f"Artifact Reduction: {' '.join(ARTIFACT_REDUCTION_OPTION) if ARTIFACT_REDUCTION_OPTION else 'None'}\n")
        log_file.write(f"Denoise: {' '.join(DENOISE_OPTION) if DENOISE_OPTION else 'None'}\n")
        if HDR_OPTION_LIST:
            log_file.write("HDR Conversion: " + ' '.join(HDR_OPTION_LIST) + "\n")
        else:
            log_file.write("HDR Conversion: None\n")
        if selected_tracks:
            log_file.write("Selected Audio Tracks: " + ",".join(str(t) for t in selected_tracks) + "\n")
            log_file.write(f"Audio: {'Copy Audio' if audio_choice == '1' else 'Convert to AC3'}\n")
        else:
            log_file.write("No audio selected.\n")
        log_file.write(f"GOP Length: {gop_len}\n")
        log_file.write("-------------------------------\n\n")

    print(f"Processed file: {os.path.basename(hdr_output_path)}")

# Final message
wait_for_any_key()
