import os
import sys
import subprocess
import cv2
import platform
import json
import tkinter as tk
from tkinter import filedialog, messagebox
from collections import Counter

# ---------------------------------------------------------------------
# Step 1: ffprobe-based metadata extraction
# ---------------------------------------------------------------------
def get_video_color_info(video_file):
    """
    Extract basic color-related metadata using ffprobe in JSON format:
    - color_range
    - color_primaries
    - color_transfer
    - color_space
    - mastering_display_metadata (if present)
    - max_cll (if present)
    """
    cmd = ["ffprobe", "-v", "error", "-show_streams", "-of", "json", video_file]
    try:
        output = subprocess.check_output(
            cmd,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
    except subprocess.CalledProcessError:
        return {
            "color_range": None,
            "color_primaries": None,
            "color_transfer": None,
            "color_space": None,
            "mastering_display_metadata": None,
            "max_cll": None
        }

    data = json.loads(output)
    streams = data.get("streams", [])
    video_stream = None
    for s in streams:
        if s.get("codec_type") == "video":
            video_stream = s
            break

    if not video_stream:
        return {
            "color_range": None,
            "color_primaries": None,
            "color_transfer": None,
            "color_space": None,
            "mastering_display_metadata": None,
            "max_cll": None
        }

    color_range = video_stream.get("color_range")
    color_primaries = video_stream.get("color_primaries")
    color_transfer = video_stream.get("color_transfer")
    color_space = video_stream.get("color_space")

    mastering_display_metadata = None
    max_cll = None
    if "side_data_list" in video_stream:
        for side_data in video_stream["side_data_list"]:
            side_type = side_data.get("side_data_type", "")
            if side_type == "Mastering display metadata":
                mastering_display_metadata = side_data
            elif side_type == "Content light level metadata":
                max_content = side_data.get("max_content")
                max_average = side_data.get("max_average")
                if max_content or max_average:
                    vals = []
                    if max_content is not None:
                        vals.append(str(max_content))
                    if max_average is not None:
                        vals.append(str(max_average))
                    max_cll = ",".join(vals)

    return {
        "color_range": color_range,
        "color_primaries": color_primaries,
        "color_transfer": color_transfer,
        "color_space": color_space,
        "mastering_display_metadata": mastering_display_metadata,
        "max_cll": max_cll
    }


def run_ffprobe_for_audio_streams(video_file):
    """
    Extract audio stream info using ffprobe.
    Returns list of dicts with {index, codec, language}.
    """
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
    """
    Extract resolution (height, width) using OpenCV.
    """
    cap = cv2.VideoCapture(video_file)
    if not cap.isOpened():
        print(f"Unable to open video file: {video_file}")
        return None, None
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    return height, width


def get_video_duration(video_file):
    """
    Get duration (in seconds) using OpenCV.
    """
    cap = cv2.VideoCapture(video_file)
    if not cap.isOpened():
        print(f"Unable to open video file: {video_file}")
        return None
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    cap.release()
    return (frame_count / fps) if fps else None


# ---------------------------------------------------------------------
# Step 2: Automatic Crop Detection
# ---------------------------------------------------------------------
def get_crop_parameters(video_file, input_width, input_height, limit_value):
    """
    Detect optimal crop parameters using ffmpeg's cropdetect filter.
    - limit_value often "64" (HDR) or "24" (SDR).
    """
    print("Detecting optimal crop parameters throughout the video...")
    duration = get_video_duration(video_file)
    if duration is None or duration < 1:
        print("Unable to determine video duration or video is too short.")
        return None, None, None, None

    round_value = "4"
    sample_interval = 300  # 5 minutes
    num_samples = max(12, min(72, int(duration // sample_interval)))
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
            "-ss", str(int(start_time)),
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
        print("No crop parameters found. Using full frame.")
        w, h, x, y = input_width, input_height, 0, 0

    return w, h, x, y


# ---------------------------------------------------------------------
# Step 3: Basic Tkinter GUI for user settings
# ---------------------------------------------------------------------
def add_files(file_listbox):
    files = filedialog.askopenfilenames(filetypes=[("Video Files", "*.mp4 *.mkv *.avi *.mov")])
    for file in files:
        file_listbox.insert('end', file)


def delete_selected(file_listbox):
    for index in reversed(file_listbox.curselection()):
        file_listbox.delete(index)


def move_up(file_listbox):
    selected = file_listbox.curselection()
    for idx in selected:
        if idx > 0:
            value = file_listbox.get(idx)
            file_listbox.delete(idx)
            file_listbox.insert(idx - 1, value)
            file_listbox.select_set(idx - 1)


def move_down(file_listbox):
    selected = file_listbox.curselection()
    for idx in reversed(selected):
        if idx < file_listbox.size() - 1:
            value = file_listbox.get(idx)
            file_listbox.delete(idx)
            file_listbox.insert(idx + 1, value)
            file_listbox.select_set(idx + 1)


def launch_gui(file_list, crop_params, audio_streams, default_qvbr, default_hdr):
    """
    Build & launch the Tkinter GUI for user adjustments.

    If HDR is selected => default decode mode = Hardware.
    If HDR is not selected => default decode mode = Software.

    Then we provide radio buttons for the user, but we also auto-update
    the decode mode radio if the user toggles "HDR Conversion".
    """
    root = tk.Tk()
    root.title("Video Processing Settings")

    root.geometry("1024x768")
    root.minsize(800, 600)

    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)

    # We'll track HDR conversion with a bool var
    hdr_enable = tk.BooleanVar()
    hdr_enable.set(default_hdr)

    # We'll track decoding mode with a string var: "Hardware" or "Software"
    decoding_mode = tk.StringVar()

    # Initial auto-set
    if default_hdr:
        decoding_mode.set("Hardware")
    else:
        decoding_mode.set("Software")

    sleep_enable = tk.BooleanVar(value=False)
    metadata_text = None

    def update_decode_mode_based_on_hdr():
        """
        If HDR is enabled => set decode_mode to "Hardware"
        If HDR is disabled => set decode_mode to "Software"
        """
        if hdr_enable.get():
            decoding_mode.set("Hardware")
        else:
            decoding_mode.set("Software")

    def on_hdr_toggle():
        update_decode_mode_based_on_hdr()

    def on_decode_mode_select():
        pass  # user override

    def update_metadata_display(selected_file):
        nonlocal metadata_text
        if not selected_file:
            metadata_text.config(state='normal')
            metadata_text.delete("1.0", "end")
            metadata_text.insert("1.0", "No file selected or metadata available.")
            metadata_text.config(state='disabled')
            return

        color_data = get_video_color_info(selected_file)
        meta_txt = (
            f"File: {selected_file}\n"
            f"Color Range: {color_data['color_range'] or 'N/A'}\n"
            f"Color Primaries: {color_data['color_primaries'] or 'N/A'}\n"
            f"Color Transfer: {color_data['color_transfer'] or 'N/A'}\n"
            f"Color Space: {color_data['color_space'] or 'N/A'}\n"
            f"Mastering Display Metadata: {color_data['mastering_display_metadata'] or 'N/A'}\n"
            f"Max CLL: {color_data['max_cll'] or 'N/A'}\n"
        )

        metadata_text.config(state='normal')
        metadata_text.delete("1.0", "end")
        metadata_text.insert("1.0", meta_txt)
        metadata_text.config(state='disabled')

    # File List UI
    file_frame = tk.Frame(root)
    file_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
    file_frame.columnconfigure(0, weight=1)
    file_frame.rowconfigure(0, weight=1)

    file_listbox = tk.Listbox(file_frame, height=10, selectmode='extended')
    file_listbox.grid(row=0, column=0, sticky="nsew")

    for file in file_list:
        file_listbox.insert('end', file)

    def on_file_select(event):
        selection = file_listbox.curselection()
        if selection:
            selected_file = file_listbox.get(selection[0])
            update_metadata_display(selected_file)

    file_listbox.bind("<<ListboxSelect>>", on_file_select)

    file_controls = tk.Frame(file_frame)
    file_controls.grid(row=0, column=1, padx=5)

    tk.Button(file_controls, text="Add Files", command=lambda: add_files(file_listbox)).pack(fill='x')
    tk.Button(file_controls, text="Clear List", command=lambda: file_listbox.delete(0, 'end')).pack(fill='x')
    tk.Button(file_controls, text="Move Up", command=lambda: move_up(file_listbox)).pack(fill='x')
    tk.Button(file_controls, text="Move Down", command=lambda: move_down(file_listbox)).pack(fill='x')
    tk.Button(file_controls, text="Delete Selected", command=lambda: delete_selected(file_listbox)).pack(fill='x')

    # Metadata Text
    metadata_frame = tk.LabelFrame(root, text="Color Metadata")
    metadata_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
    metadata_text = tk.Text(metadata_frame, height=8, wrap="word", state='disabled', bg="#f0f0f0")
    metadata_text.pack(padx=5, pady=5, fill='both', expand=True)

    if file_list:
        update_metadata_display(file_list[0])

    # Options
    options_frame = tk.LabelFrame(root, text="Video Options")
    options_frame.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")

    # Decoding Mode Frame (Radio Buttons)
    decode_mode_frame = tk.LabelFrame(options_frame, text="Decoding Mode")
    decode_mode_frame.pack(fill="x", padx=5, pady=5)

    tk.Radiobutton(
        decode_mode_frame,
        text="Hardware Decoding",
        variable=decoding_mode,
        value="Hardware",
        command=on_decode_mode_select
    ).pack(anchor="w")

    tk.Radiobutton(
        decode_mode_frame,
        text="Software Decoding",
        variable=decoding_mode,
        value="Software",
        command=on_decode_mode_select
    ).pack(anchor="w")

    # HDR Check
    tk.Checkbutton(
        options_frame,
        text="Enable HDR Conversion",
        variable=hdr_enable,
        command=on_hdr_toggle
    ).pack(anchor='w')

    resize_enable = tk.BooleanVar()
    tk.Checkbutton(options_frame, text="Resize to 4K", variable=resize_enable).pack(anchor='w')

    fruc_enable = tk.BooleanVar()
    tk.Checkbutton(options_frame, text="Enable FRUC (fps=60)", variable=fruc_enable).pack(anchor='w')

    denoise_enable = tk.BooleanVar()
    tk.Checkbutton(options_frame, text="Enable Denoising", variable=denoise_enable).pack(anchor='w')

    artifact_enable = tk.BooleanVar()
    tk.Checkbutton(options_frame, text="Enable Artifact Reduction", variable=artifact_enable).pack(anchor='w')

    qvbr = tk.StringVar(value=default_qvbr)
    tk.Label(options_frame, text="Enter target QVBR:").pack(anchor='w')
    tk.Entry(options_frame, textvariable=qvbr).pack(anchor='w')

    gop_len = tk.StringVar(value="6")
    tk.Label(options_frame, text="Enter GOP length:").pack(anchor='w')
    tk.Entry(options_frame, textvariable=gop_len).pack(anchor='w')

    # Crop UI
    crop_frame = tk.LabelFrame(root, text="Crop Parameters (Modify if needed)")
    crop_frame.grid(row=2, column=1, padx=10, pady=10, sticky="nsew")

    crop_w = tk.StringVar(value="0")
    crop_h = tk.StringVar(value="0")
    crop_x = tk.StringVar(value="0")
    crop_y = tk.StringVar(value="0")

    tk.Label(crop_frame, text="Width:").grid(row=0, column=0, sticky="w")
    tk.Entry(crop_frame, textvariable=crop_w).grid(row=0, column=1, sticky="ew")

    tk.Label(crop_frame, text="Height:").grid(row=1, column=0, sticky="w")
    tk.Entry(crop_frame, textvariable=crop_h).grid(row=1, column=1, sticky="ew")

    tk.Label(crop_frame, text="X Offset:").grid(row=2, column=0, sticky="w")
    tk.Entry(crop_frame, textvariable=crop_x).grid(row=2, column=1, sticky="ew")

    tk.Label(crop_frame, text="Y Offset:").grid(row=3, column=0, sticky="w")
    tk.Entry(crop_frame, textvariable=crop_y).grid(row=3, column=1, sticky="ew")

    detected_crop = crop_params[0] if crop_params else {}
    crop_w.set(detected_crop.get("crop_w", 0))
    crop_h.set(detected_crop.get("crop_h", 0))
    crop_x.set(detected_crop.get("crop_x", 0))
    crop_y.set(detected_crop.get("crop_y", 0))

    # Audio UI
    audio_frame = tk.LabelFrame(root, text="Audio Options")
    audio_frame.grid(row=3, column=0, padx=10, pady=10, sticky="nsew")

    audio_vars = []
    for stream in audio_streams:
        audio_var = tk.BooleanVar(value=(stream['language'] == 'eng'))
        label_txt = f"Track {stream['index']}: {stream['codec']} ({stream['language'] or 'N/A'})"
        tk.Checkbutton(audio_frame, text=label_txt, variable=audio_var).pack(anchor='w')
        audio_vars.append(audio_var)

    tk.Checkbutton(root, text="Put Computer to Sleep", variable=sleep_enable).grid(row=4, column=0, padx=10, pady=5, sticky="w")

    def start_processing():
        selected_files = list(file_listbox.get(0, 'end'))
        if not selected_files:
            messagebox.showerror("Error", "No video files selected.")
            return

        selected_tracks = []
        for i, s in enumerate(audio_streams):
            if audio_vars[i].get():
                selected_tracks.append(s)
        if not selected_tracks:
            messagebox.showerror("Error", "At least one audio track must be selected.")
            return

        settings = {
            "files": selected_files,
            "decode_mode": decoding_mode.get(),   # "Hardware" or "Software"
            "hdr_enable": hdr_enable.get(),       # bool
            "resize_enable": resize_enable.get(),
            "fruc_enable": fruc_enable.get(),
            "denoise_enable": denoise_enable.get(),
            "artifact_enable": artifact_enable.get(),
            "qvbr": qvbr.get(),
            "gop_len": gop_len.get(),
            "crop_params": {
                "crop_w": int(crop_w.get()),
                "crop_h": int(crop_h.get()),
                "crop_x": int(crop_x.get()),
                "crop_y": int(crop_y.get())
            },
            "audio_tracks": selected_tracks,
            "sleep_after_processing": sleep_enable.get()
        }

        root.destroy()
        print("\nSettings collected. Starting processing...\n")
        print(settings)
        process_batch(settings["files"], settings)

        if settings.get("sleep_after_processing"):
            print("Putting the computer to sleep...")
            if platform.system() == "Windows":
                os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
            elif platform.system() == "Linux":
                os.system("systemctl suspend")
            elif platform.system() == "Darwin":
                os.system("pmset sleepnow")
            else:
                print("Sleep command not supported on this platform.")

    tk.Button(root, text="Start Processing", command=start_processing).grid(row=5, column=0, pady=10, sticky="ew")
    root.mainloop()


# ---------------------------------------------------------------------
# Step 4: The main encode function
# ---------------------------------------------------------------------
def process_video(file_path, settings):
    """
    Encode a single video file with NVEncC according to 'settings'.

    If convert-to-HDR is not selected:
      - add: --dhdr10-info copy, --dolby-vision-profile copy, --dolby-vision-rpu copy
    If convert-to-HDR is selected:
      - add: --vpp-ngx-truehdr
      - also add: --colormatrix bt2020nc --colorprim bt2020 --transfer smpte2084
    """
    input_dir = os.path.dirname(file_path)
    file_name = os.path.basename(file_path)
    output_subdir = os.path.join(input_dir, "processed_videos")
    os.makedirs(output_subdir, exist_ok=True)
    output_file = os.path.join(output_subdir, os.path.splitext(file_name)[0] + "_AV1.mkv")

    log_file = os.path.join(output_subdir, os.path.splitext(file_name)[0] + "_encoding.log")

    input_height, input_width = get_video_resolution(file_path)
    if input_height is None or input_width is None:
        print(f"Error: Could not retrieve resolution for {file_path}. Skipping.")
        return

    hdr_convert = settings["hdr_enable"]  # bool

    command = [
        "NVEncC64",
        "--codec", "av1",
        "--qvbr", settings["qvbr"],
        "--preset", "p4",
        "--output-depth", "10",
        "--gop-len", settings["gop_len"],
        "--metadata", "copy",
        "--chapter-copy",
        "--key-on-chapter",
        "--sub-copy",
        "--tier", "1",
        "--profile", "high",
        "--multipass", "2pass-full",
        "--aq",
        "--aq-temporal",
        "--aq-strength", "5",
        "--lookahead", "32",
        "--lookahead-level", "auto",
        "-i", file_path,
        "-o", output_file
    ]

    # decode mode
    if settings["decode_mode"] == "Hardware":
        command.append("--avhw")
    else:
        command.append("--avsw")

    if hdr_convert:
        # Convert to HDR
        command.append("--vpp-ngx-truehdr")
        # Add color tags for HDR
        command.extend(["--colormatrix", "bt2020nc"])
        command.extend(["--colorprim", "bt2020"])
        command.extend(["--transfer", "smpte2084"])
    else:
        # Not converting to HDR => copy dynamic metadata
        command.extend(["--dhdr10-info", "copy"])
        command.extend(["--dolby-vision-profile", "copy"])
        command.extend(["--dolby-vision-rpu", "copy"])

    # Additional features
    if settings["resize_enable"]:
        command.extend(["--vpp-resize", "algo=nvvfx-superres,superres-mode=0", "--output-res", "3840x2160"])
    if settings["fruc_enable"]:
        command.extend(["--vpp-fruc", "fps=60"])
    if settings["denoise_enable"]:
        command.append("--vpp-nvvfx-denoise")
    if settings["artifact_enable"]:
        command.append("--vpp-nvvfx-artifact-reduction")

    # Crop
    crop = settings["crop_params"]
    left = crop["crop_x"]
    top = crop["crop_y"]
    right = input_width - (left + crop["crop_w"])
    bottom = input_height - (top + crop["crop_h"])
    command.extend(["--crop", f"{left},{top},{right},{bottom}"])

    # Audio track selection, e.g. "--audio-codec 2?ac3"
    for track in settings["audio_tracks"]:
        track_idx = track["index"]
        audio_param = f"{track_idx}?ac3"
        command.extend(["--audio-codec", audio_param])

    print(f"\nProcessing: {file_path}")
    print("NVEncC command:\n" + " ".join(command))
    try:
        subprocess.run(command, check=True)
        print(f"Success: Processed {file_path} -> {output_file}")
        status = "Success"
    except subprocess.CalledProcessError as e:
        print(f"Error: Failed to process {file_path}")
        status = f"Error: {e}"

    with open(log_file, "w", encoding='utf-8') as log:
        log.write("Command:\n" + " ".join(command) + "\n\n")
        log.write(f"Processing file: {file_path}\n")
        log.write(f"Output file: {output_file}\n")
        log.write(f"Status: {status}\n")


def process_batch(video_files, settings):
    for vf in video_files:
        process_video(vf, settings)


# ---------------------------------------------------------------------
# Main Script Logic (Batch + GUI)
# ---------------------------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("No video file specified. Please drag and drop a video file onto the script.")
        input("Press any key to exit...")
        sys.exit()

    video_files = sys.argv[1:]
    first_file = video_files[0]

    # Decide if default HDR is on or off
    color_data_first = get_video_color_info(first_file)
    cp_first = (color_data_first["color_primaries"] or "").lower()
    cs_first = (color_data_first["color_space"] or "").lower()

    # If the content is in BT.2020, guess user might not want to do "HDR conversion" by default
    if cp_first == "bt2020" or cs_first == "bt2020nc":
        default_hdr = False
        limit_value = "64"
    else:
        default_hdr = True
        limit_value = "24"

    # Check resolution for default QVBR
    first_h, first_w = get_video_resolution(first_file)
    if first_h is None or first_w is None:
        print(f"Error: Could not retrieve resolution for {first_file}. Exiting.")
        sys.exit()

    if (first_h >= 2160) and (first_w >= 3840):
        default_qvbr = "30"
    else:
        default_qvbr = "20"

    # Crop detection on the first file
    crop_w, crop_h, crop_x, crop_y = get_crop_parameters(first_file, first_w, first_h, limit_value=limit_value)

    # Build a default crop dict for each file
    detected_crop_params = []
    for vf in video_files:
        detected_crop_params.append({
            "file": vf,
            "crop_w": crop_w,
            "crop_h": crop_h,
            "crop_x": crop_x,
            "crop_y": crop_y
        })

    print("\nCrop detection complete (only for the first file). Launching GUI...\n")

    all_audio_streams = run_ffprobe_for_audio_streams(first_file)

    # Launch the GUI
    launch_gui(
        [d["file"] for d in detected_crop_params],
        detected_crop_params,
        all_audio_streams,
        default_qvbr,
        default_hdr
    )

    print("All processing complete. Press any key to exit...")
    input()
