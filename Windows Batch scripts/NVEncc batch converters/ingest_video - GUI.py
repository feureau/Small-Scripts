import os
import sys
import subprocess
import cv2
import platform
from collections import Counter
import json
import tkinter as tk
from tkinter import filedialog, messagebox

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
    """
    Extract audio stream information from a video file using ffprobe.
    - Includes index, codec_name, and language (if available).
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
    Extract the resolution of a video file using OpenCV.
    - Returns height and width.
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
    Calculate the duration of a video file using OpenCV.
    - Returns duration in seconds.
    """
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
    """
    Detect optimal crop parameters for a video using ffmpeg.
    - Analyzes frames at intervals and detects cropping areas.
    """
    print("Detecting optimal crop parameters throughout the video...")
    duration = get_video_duration(video_file)
    if duration is None or duration < 1:
        print("Unable to determine video duration or video is too short.")
        return None, None, None, None

    default_limit = "48"
    limit_value = default_limit
    default_round = "4"
    round_value = default_round

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

    return w, h, x, y

def add_files(file_listbox):
    """
    Open a file dialog to add video files to the listbox.
    """
    files = filedialog.askopenfilenames(filetypes=[("Video Files", "*.mp4 *.mkv *.avi *.mov")])
    for file in files:
        file_listbox.insert('end', file)

def delete_selected(file_listbox):
    """
    Remove selected files from the listbox.
    """
    for index in reversed(file_listbox.curselection()):
        file_listbox.delete(index)

def move_up(file_listbox):
    """
    Move the selected file(s) up in the listbox.
    """
    selected = file_listbox.curselection()
    for idx in selected:
        if idx > 0:
            value = file_listbox.get(idx)
            file_listbox.delete(idx)
            file_listbox.insert(idx - 1, value)
            file_listbox.select_set(idx - 1)

def move_down(file_listbox):
    """
    Move the selected file(s) down in the listbox.
    """
    selected = file_listbox.curselection()
    for idx in reversed(selected):
        if idx < file_listbox.size() - 1:
            value = file_listbox.get(idx)
            file_listbox.delete(idx)
            file_listbox.insert(idx + 1, value)
            file_listbox.select_set(idx + 1)
def launch_gui(file_list, crop_params, audio_streams):
    """
    Launch the GUI for configuring video processing options.
    - Displays the color-related metadata for selected videos.
    - Allows users to modify settings and start processing.
    """
    # Initialize main window
    root = tk.Tk()
    root.title("Video Processing Settings")

    # Set default size and minimum size for the window
    root.geometry("1024x768")  # Default size
    root.minsize(800, 600)     # Minimum size to ensure elements are visible

    # Allow dynamic resizing
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)

    # Declare HDR enable variable before `update_metadata_display`
    hdr_enable = tk.BooleanVar(value=False)  # Set HDR conversion disabled by default

    # Function to update metadata display
    def update_metadata_display(selected_file):
        if not selected_file:
            metadata_text.config(state='normal')
            metadata_text.delete("1.0", "end")
            metadata_text.insert("1.0", "No file selected or metadata available.")
            metadata_text.config(state='disabled')
            return

        # Fetch color-related metadata
        color_range, color_primaries, color_transfer, color_space, mastering_metadata = get_video_color_info(selected_file)
        metadata = (
            f"File: {selected_file}\n"
            f"Color Range: {color_range or 'N/A'}\n"
            f"Color Primaries: {color_primaries or 'N/A'}\n"
            f"Color Transfer: {color_transfer or 'N/A'}\n"
            f"Color Space: {color_space or 'N/A'}\n"
            f"Mastering Display Metadata: {mastering_metadata or 'N/A'}\n"
        )
        metadata_text.config(state='normal')
        metadata_text.delete("1.0", "end")
        metadata_text.insert("1.0", metadata)
        metadata_text.config(state='disabled')

        # Automatically enable HDR if metadata shows SDR or missing HDR data
        if not color_primaries or "BT.2020" not in color_primaries:
            hdr_enable.set(True)

    # File list section
    file_frame = tk.Frame(root)
    file_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
    file_frame.columnconfigure(0, weight=1)  # Allow Listbox to stretch horizontally
    file_frame.rowconfigure(0, weight=1)    # Allow Listbox to stretch vertically

    file_listbox = tk.Listbox(file_frame, height=10, selectmode='extended')
    file_listbox.grid(row=0, column=0, sticky="nsew")

    for file in file_list:
        file_listbox.insert('end', file)

    def on_file_select(event):
        # Update metadata display for the selected file
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

    # Metadata display
    metadata_frame = tk.LabelFrame(root, text="Color Metadata")
    metadata_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

    metadata_text = tk.Text(metadata_frame, height=8, wrap="word", state='disabled', bg="#f0f0f0")
    metadata_text.pack(padx=5, pady=5, fill='both', expand=True)

    # Populate metadata for the first file
    if file_list:
        update_metadata_display(file_list[0])

    # Video options section
    options_frame = tk.LabelFrame(root, text="Video Options")
    options_frame.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")

    # Decoding mode grouping
    decoding_frame = tk.LabelFrame(options_frame, text="Decoding Mode")
    decoding_frame.pack(fill="x", padx=5, pady=5)

    decoding_mode = tk.StringVar(value="Hardware")
    tk.Radiobutton(decoding_frame, text="Hardware Decoding", variable=decoding_mode, value="Hardware").pack(anchor="w")
    tk.Radiobutton(decoding_frame, text="Software Decoding", variable=decoding_mode, value="Software").pack(anchor="w")

    tk.Checkbutton(options_frame, text="Enable HDR Conversion", variable=hdr_enable).pack(anchor='w')

    resize_enable = tk.BooleanVar()
    tk.Checkbutton(options_frame, text="Resize to 4K", variable=resize_enable).pack(anchor='w')

    fruc_enable = tk.BooleanVar()
    tk.Checkbutton(options_frame, text="Enable FRUC (fps=60)", variable=fruc_enable).pack(anchor='w')

    denoise_enable = tk.BooleanVar()
    tk.Checkbutton(options_frame, text="Enable Denoising", variable=denoise_enable).pack(anchor='w')

    artifact_enable = tk.BooleanVar()
    tk.Checkbutton(options_frame, text="Enable Artifact Reduction", variable=artifact_enable).pack(anchor='w')

    qvbr = tk.StringVar(value="20")
    tk.Label(options_frame, text="Enter target QVBR:").pack(anchor='w')
    tk.Entry(options_frame, textvariable=qvbr).pack(anchor='w')

    gop_len = tk.StringVar(value="6")
    tk.Label(options_frame, text="Enter GOP length:").pack(anchor='w')
    tk.Entry(options_frame, textvariable=gop_len).pack(anchor='w')

    # Audio options section
    audio_frame = tk.LabelFrame(root, text="Audio Options")
    audio_frame.grid(row=3, column=0, padx=10, pady=10, sticky="nsew")

    audio_vars = []
    for stream in audio_streams:
        audio_var = tk.BooleanVar(value=(stream['language'] == 'eng'))
        tk.Checkbutton(audio_frame, text=f"Track {stream['index']}: {stream['codec']} ({stream['language']})",
                       variable=audio_var).pack(anchor='w')
        audio_vars.append(audio_var)

    # Action buttons
    def start_processing():
        # Validate and collect settings
        selected_files = list(file_listbox.get(0, 'end'))
        if not selected_files:
            messagebox.showerror("Error", "No video files selected.")
            return

        settings = {
            "files": selected_files,
            "decode_mode": decoding_mode.get(),
            "hdr_enable": hdr_enable.get(),
            "resize_enable": resize_enable.get(),
            "fruc_enable": fruc_enable.get(),
            "denoise_enable": denoise_enable.get(),
            "artifact_enable": artifact_enable.get(),
            "qvbr": qvbr.get(),
            "gop_len": gop_len.get(),
            "audio_tracks": [stream for i, stream in enumerate(audio_streams) if audio_vars[i].get()]
        }

        if not settings["audio_tracks"]:
            messagebox.showerror("Error", "At least one audio track must be selected.")
            return

        root.destroy()  # Close the GUI
        print("\nSettings collected. Starting processing...")
        print(settings)
        process_batch(settings["files"], settings)

    tk.Button(root, text="Start Processing", command=start_processing).grid(row=4, column=0, pady=10, sticky="ew")

    root.mainloop()
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
        "--codec", "av1",
        "--qvbr", settings['qvbr'],
        "--preset", "p4",
        "--output-depth", "10",
        "--gop-len", settings['gop_len'],
        "--metadata", "copy",
        "-i", file_path,
        "-o", output_file
    ]

    if settings["decode_mode"] == "Hardware":
        command.append("--avhw")
    else:
        command.append("--avsw")

    if settings['hdr_enable']:
        command.append("--vpp-ngx-truehdr")

    if settings['resize_enable']:
        command.extend(["--vpp-resize", "algo=nvvfx-superres,superres-mode=0", "--output-res", "3840x2160"])

    if settings['fruc_enable']:
        command.extend(["--vpp-fruc", "fps=60"])

    if settings['denoise_enable']:
        command.append("--vpp-nvvfx-denoise")

    if settings['artifact_enable']:
        command.append("--vpp-nvvfx-artifact-reduction")

    if settings.get("crop_params"):
        crop = settings["crop_params"]
        command.extend(["--crop", f"{crop['crop_x']},{crop['crop_y']},{crop['crop_w']},{crop['crop_h']}"])

    if settings['audio_tracks']:
        for track in settings['audio_tracks']:
            command.extend(["--audio-stream", str(track['index'])])
        command.append("--audio-copy")

    print(f"Processing: {file_path}")
    try:
        subprocess.run(command, check=True)
        print(f"Success: Processed {file_path} -> {output_file}")
    except subprocess.CalledProcessError as e:
        print(f"Error: Failed to process {file_path}")
        print(e)

def process_batch(video_files, settings):
    """
    Process a batch of video files with the provided settings.
    """
    for file_path in video_files:
        process_video(file_path, settings)
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("No video file specified. Please drag and drop a video file onto the script.")
        input("Press any key to exit...")
        sys.exit()

    video_files = sys.argv[1:]
    detected_crop_params = []

    for video_file in video_files:
        input_height, input_width = get_video_resolution(video_file)
        if input_height is None or input_width is None:
            print(f"Error: Could not retrieve resolution for {video_file}. Skipping.")
            continue

        crop_w, crop_h, crop_x, crop_y = get_crop_parameters(video_file, input_width, input_height)
        detected_crop_params.append({
            "file": video_file,
            "crop_w": crop_w,
            "crop_h": crop_h,
            "crop_x": crop_x,
            "crop_y": crop_y
        })

    print("\nCrop detection complete. Launching GUI for additional settings...\n")
    all_audio_streams = [
        stream for file in detected_crop_params for stream in run_ffprobe_for_audio_streams(file["file"])
    ]
    launch_gui([d["file"] for d in detected_crop_params], detected_crop_params, all_audio_streams)