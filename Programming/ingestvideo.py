import os
import sys
import subprocess
import cv2
import platform
import json
import tkinter as tk
from tkinter import filedialog, messagebox
from collections import Counter
from multiprocessing import Pool
import glob  # Import the glob module

# ---------------------------------------------------------------------
# Step 1: ffprobe-based metadata extraction
# ---------------------------------------------------------------------
def get_video_color_info(video_file):
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
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "a",
        "-show_entries", "stream=index,codec_name,channels:stream_tags=language",
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
        channels = s.get("channels", 0)
        audio_info.append({"stream_index": idx, "codec": codec, "language": language, "channels": channels})

    # Assign track_number based on audio stream order
    for track_number, audio in enumerate(audio_info, start=1):
        audio['track_number'] = track_number

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
    cap.release()
    return (frame_count / fps) if fps else None


# ---------------------------------------------------------------------
# Step 2: Automatic Crop Detection
# ---------------------------------------------------------------------
def get_crop_parameters(video_file, input_width, input_height, limit_value):
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
                    try:
                        w, h, x, y = [int(v) for v in crop_str.split(':')]
                        print(f"Detected crop at {int(start_time)}s: width={w}, height={h}, x={x}, y={y}")
                    except ValueError:
                        print(f"Invalid crop parameters detected: {crop_str}")
            if len(crop_values) >= num_samples:
                break
        except Exception as e:
            print(f"Error while running cropdetect at {int(start_time)}s: {e}")
            continue

    if crop_values:
        crop_counter = Counter(crop_values)
        most_common_crop = crop_counter.most_common(1)[0][0]
        try:
            w, h, x, y = [int(v) for v in most_common_crop.split(':')]
            print(f"\nDetected optimal crop parameters: width={w}, height={h}, x={x}, y={y}")
        except ValueError:
            print(f"Invalid most common crop parameters: {most_common_crop}. Using full frame.")
            w, h, x, y = input_width, input_height, 0, 0
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


def launch_gui(file_list, crop_params, audio_streams, default_qvbr, default_hdr, input_width, input_height):
    root = tk.Tk()
    root.title("Video Processing Settings")

    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    main_frame = tk.Frame(root)
    main_frame.pack(fill='both', expand=True)

    canvas = tk.Canvas(main_frame)
    canvas.pack(side='left', fill='both', expand=True)

    scrollbar = tk.Scrollbar(main_frame, orient='vertical', command=canvas.yview)
    scrollbar.pack(side='right', fill='y')

    canvas.configure(yscrollcommand=scrollbar.set)

    def _on_mousewheel(event):
        if platform.system() == 'Windows':
            delta = int(-1 * (event.delta / 120))
        elif platform.system() == 'Darwin':
            delta = int(-1 * event.delta)
        else:
            delta = int(-1 * (event.delta / 120))
        canvas.yview_scroll(delta, "units")

    canvas.bind_all("<MouseWheel>", _on_mousewheel)

    inner_frame = tk.Frame(canvas)
    canvas.create_window((0, 0), window=inner_frame, anchor='nw')

    def _configure_event(event):
        canvas.configure(scrollregion=canvas.bbox("all"))

    inner_frame.bind("<Configure>", _configure_event)

    decoding_mode = tk.StringVar(value="Hardware")
    hdr_enable = tk.BooleanVar(value=default_hdr)
    sleep_enable = tk.BooleanVar(value=False)

    fruc_enable = tk.BooleanVar()
    denoise_enable = tk.BooleanVar()
    artifact_enable = tk.BooleanVar()

    resolution_var = tk.StringVar(value="No Resize")
    qvbr = tk.StringVar(value=default_qvbr)
    gop_len = tk.StringVar(value="6")

    # Multiprocessing "Max Processes" variable (default=1)
    max_processes = tk.StringVar(value="1")

    no_crop_var = tk.BooleanVar(value=False)
    metadata_text = None

    audio_vars = []
    convert_vars = []

    crop_w = tk.StringVar(value=str(crop_params[0]['crop_w']) if crop_params else "0")
    crop_h = tk.StringVar(value=str(crop_params[0]['crop_h']) if crop_params else "0")
    crop_x = tk.StringVar(value=str(crop_params[0]['crop_x']) if crop_params else "0")
    crop_y = tk.StringVar(value=str(crop_params[0]['crop_y']) if crop_params else "0")

    original_crop_w = crop_w.get()
    original_crop_h = crop_h.get()
    original_crop_x = crop_x.get()
    original_crop_y = crop_y.get()

    resolution_map = {
        "No Resize": (None, None, None),
        "HD 1080p":  (1920, 1080, "20"),
        "4K 2160p":  (3840, 2160, "30"),
        "8K 4320p":  (7680, 4320, "40")
    }

    def on_resolution_change(*args):
        selection = resolution_var.get()
        if selection in resolution_map:
            recommended_qvbr = resolution_map[selection][2]
            if recommended_qvbr is not None:
                qvbr.set(recommended_qvbr)

    resolution_var.trace("w", on_resolution_change)

    # -------------
    # Update Metadata
    # -------------
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

    # -------------------------
    # File List UI
    # -------------------------
    file_frame = tk.Frame(inner_frame)
    file_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
    file_frame.columnconfigure(0, weight=1)
    file_frame.rowconfigure(0, weight=1)

    file_listbox = tk.Listbox(file_frame, height=5, selectmode='extended')
    file_listbox.grid(row=0, column=0, sticky="nsew")

    for f in file_list:
        file_listbox.insert('end', f)

    def on_file_select(event):
        selection = file_listbox.curselection()
        if selection:
            selected_file = file_listbox.get(selection[0])
            update_metadata_display(selected_file)

    file_listbox.bind("<<ListboxSelect>>", on_file_select)

    file_controls = tk.Frame(file_frame)
    file_controls.grid(row=0, column=1, padx=5, sticky="ns")

    tk.Button(file_controls, text="Add Files", command=lambda: add_files(file_listbox)).pack(fill='x', pady=(0,5))
    tk.Button(file_controls, text="Clear List", command=lambda: file_listbox.delete(0, 'end')).pack(fill='x', pady=(0,5))
    tk.Button(file_controls, text="Move Up", command=lambda: move_up(file_listbox)).pack(fill='x', pady=(0,5))
    tk.Button(file_controls, text="Move Down", command=lambda: move_down(file_listbox)).pack(fill='x', pady=(0,5))
    tk.Button(file_controls, text="Delete Selected", command=lambda: delete_selected(file_listbox)).pack(fill='x', pady=(0,5))

    metadata_frame = tk.LabelFrame(inner_frame, text="Color Metadata")
    metadata_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
    metadata_frame.columnconfigure(0, weight=1)
    metadata_frame.rowconfigure(0, weight=1)

    metadata_text = tk.Text(metadata_frame, height=8, wrap="word", state='disabled', bg="#f0f0f0")
    metadata_text.grid(row=0, column=0, sticky="nsew")

    if file_list:
        update_metadata_display(file_list[0])

    # -------------------------
    # Video Options
    # -------------------------
    options_frame = tk.LabelFrame(inner_frame, text="Video Options")
    options_frame.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")
    options_frame.columnconfigure(0, weight=1)

    decode_mode_frame = tk.LabelFrame(options_frame, text="Decoding Mode")
    decode_mode_frame.pack(fill="x", padx=5, pady=5)

    tk.Radiobutton(
        decode_mode_frame,
        text="Hardware Decoding",
        variable=decoding_mode,
        value="Hardware"
    ).pack(anchor="w")

    tk.Radiobutton(
        decode_mode_frame,
        text="Software Decoding",
        variable=decoding_mode,
        value="Software"
    ).pack(anchor="w")

    # Multiprocessing input
    multi_frame = tk.Frame(options_frame)
    multi_frame.pack(anchor='w', pady=(5, 0))

    tk.Label(multi_frame, text="Max Processes:").pack(side='left')
    mp_entry = tk.Entry(multi_frame, textvariable=max_processes, width=3)
    mp_entry.pack(side='left', padx=(5, 0))

    tk.Checkbutton(options_frame, text="Enable HDR Conversion", variable=hdr_enable).pack(anchor='w')

    # Output resolution
    resolution_frame = tk.Frame(options_frame)
    resolution_frame.pack(anchor='w', pady=(10,0))

    tk.Label(resolution_frame, text="Output Resolution:").pack(side='left')
    resolution_menu = tk.OptionMenu(resolution_frame, resolution_var, *resolution_map.keys())
    resolution_menu.pack(side='left', padx=(5,0))

    tk.Checkbutton(options_frame, text="Enable FRUC (fps=60)", variable=fruc_enable).pack(anchor='w')
    tk.Checkbutton(options_frame, text="Enable Denoising", variable=denoise_enable).pack(anchor='w')
    tk.Checkbutton(options_frame, text="Enable Artifact Reduction", variable=artifact_enable).pack(anchor='w')

    # QVBR and GOP side-by-side
    qvbr_frame = tk.Frame(options_frame)
    qvbr_frame.pack(anchor='w', pady=(10, 0))
    tk.Label(qvbr_frame, text="Target QVBR:").pack(side='left', anchor='w')
    tk.Entry(qvbr_frame, textvariable=qvbr, width=6).pack(side='left', padx=(5, 0), anchor='w')

    gop_frame = tk.Frame(options_frame)
    gop_frame.pack(anchor='w', pady=(10, 0))
    tk.Label(gop_frame, text="GOP Length:").pack(side='left', anchor='w')
    tk.Entry(gop_frame, textvariable=gop_len, width=6).pack(side='left', padx=(5, 0), anchor='w')

    # -------------------------
    # Crop UI
    # -------------------------
    crop_frame = tk.LabelFrame(inner_frame, text="Crop Parameters (Modify if needed)")
    crop_frame.grid(row=3, column=0, padx=10, pady=10, sticky="nsew")
    crop_frame.columnconfigure(1, weight=1)

    tk.Label(crop_frame, text="Width:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
    width_entry = tk.Entry(crop_frame, textvariable=crop_w)
    width_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=2)

    tk.Label(crop_frame, text="Height:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
    height_entry = tk.Entry(crop_frame, textvariable=crop_h)
    height_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=2)

    tk.Label(crop_frame, text="X Offset:").grid(row=2, column=0, sticky="w", padx=5, pady=2)
    x_entry = tk.Entry(crop_frame, textvariable=crop_x)
    x_entry.grid(row=2, column=1, sticky="ew", padx=5, pady=2)

    tk.Label(crop_frame, text="Y Offset:").grid(row=3, column=0, sticky="w", padx=5, pady=2)
    y_entry = tk.Entry(crop_frame, textvariable=crop_y)
    y_entry.grid(row=3, column=1, sticky="ew", padx=5, pady=2)

    def on_no_crop_toggle():
        if no_crop_var.get():
            crop_w.set(str(input_width))
            crop_h.set(str(input_height))
            crop_x.set("0")
            crop_y.set("0")
            width_entry.config(state='disabled')
            height_entry.config(state='disabled')
            x_entry.config(state='disabled')
            y_entry.config(state='disabled')
        else:
            crop_w.set(str(original_crop_w))
            crop_h.set(str(original_crop_h))
            crop_x.set(str(original_crop_x))
            crop_y.set(str(original_crop_y))
            width_entry.config(state='normal')
            height_entry.config(state='normal')
            x_entry.config(state='normal')
            y_entry.config(state='normal')

    no_crop_checkbox = tk.Checkbutton(crop_frame, text="No Crop", variable=no_crop_var, command=on_no_crop_toggle)
    no_crop_checkbox.grid(row=4, column=0, columnspan=2, pady=(10, 0), sticky="w", padx=5)

    # -------------------------
    # Audio Tracks
    # -------------------------
    audio_tracks_frame = tk.LabelFrame(inner_frame, text="Audio Tracks")
    audio_tracks_frame.grid(row=4, column=0, padx=10, pady=10, sticky="nsew")
    audio_tracks_frame.columnconfigure(0, weight=1)
    audio_tracks_frame.columnconfigure(1, weight=1)

    button_frame = tk.Frame(audio_tracks_frame)
    button_frame.grid(row=0, column=0, columnspan=2, sticky="n", padx=5, pady=5)

    def on_select_all_audio():
        for var in audio_vars:
            var.set(True)

    def on_clear_all_audio():
        for var in audio_vars:
            var.set(False)

    def copy_all_audio():
        for var in convert_vars:
            var.set(False)

    def convert_all_audio():
        for var in convert_vars:
            var.set(True)

    tk.Button(button_frame, text="Select All", command=on_select_all_audio).pack(side='left', padx=2)
    tk.Button(button_frame, text="Clear All", command=on_clear_all_audio).pack(side='left', padx=2)
    tk.Button(button_frame, text="Copy All", command=copy_all_audio).pack(side='left', padx=2)
    tk.Button(button_frame, text="Convert All", command=convert_all_audio).pack(side='left', padx=2)

    if audio_streams:
        for idx, stream in enumerate(audio_streams, start=1):
            track_frame = tk.Frame(audio_tracks_frame)
            track_frame.grid(row=idx, column=0, padx=5, pady=2, sticky='e')

            # auto-select if english
            auto_selected = (stream['language'] == 'eng')

            track_label_text = f"Track {stream['track_number']}: {stream['codec']} ({stream['language'] or 'N/A'}, {stream.get('channels', 0)}-ch)"
            label = tk.Label(track_frame, text=track_label_text, anchor='e')
            label.pack(side='left')

            track_var = tk.BooleanVar(value=auto_selected)
            tk.Checkbutton(track_frame, variable=track_var).pack(side='right', padx=(5,0))
            audio_vars.append(track_var)

            convert_var = tk.BooleanVar(value=(stream['codec'] != 'ac3'))
            convert_check = tk.Checkbutton(audio_tracks_frame, text="Convert to AC3", variable=convert_var, anchor='w')
            convert_check.grid(row=idx, column=1, padx=5, pady=2, sticky='w')
            convert_vars.append(convert_var)
    else:
        tk.Label(audio_tracks_frame, text="No audio tracks found in the selected file.")\
            .grid(row=1, column=0, padx=5, pady=5, sticky='w')

    tk.Checkbutton(inner_frame, text="Put Computer to Sleep", variable=sleep_enable).grid(row=5, column=0, padx=10, pady=5, sticky="w")

    def start_processing():
        selected_files = list(file_listbox.get(0, 'end'))
        if not selected_files:
            messagebox.showerror("Error", "No video files selected.")
            return

        selected_tracks = []
        if audio_streams:
            for i, s in enumerate(audio_streams):
                if audio_vars[i].get():
                    s_copy = s.copy()
                    s_copy['convert_to_ac3'] = convert_vars[i].get()
                    selected_tracks.append(s_copy)

        try:
            crop_w_val = int(crop_w.get())
            crop_h_val = int(crop_h.get())
            crop_x_val = int(crop_x.get())
            crop_y_val = int(crop_y.get())

            if crop_w_val <= 0 or crop_h_val <= 0:
                messagebox.showerror("Error", "Crop width and height must be positive integers.")
                return

            if crop_x_val < 0 or crop_y_val < 0:
                messagebox.showerror("Error", "Crop X and Y offsets cannot be negative.")
                return

            if crop_x_val + crop_w_val > input_width or crop_y_val + crop_h_val > input_height:
                messagebox.showerror("Error", "Crop parameters exceed video dimensions.")
                return
        except ValueError:
            messagebox.showerror("Error", "Invalid crop parameters. Please enter integers.")
            return

        resolution_choice = resolution_var.get()

        settings = {
            "files": selected_files,
            "decode_mode": decoding_mode.get(),
            "hdr_enable": hdr_enable.get(),
            "resolution_choice": resolution_choice,
            "fruc_enable": fruc_enable.get(),
            "denoise_enable": denoise_enable.get(),
            "artifact_enable": artifact_enable.get(),
            "qvbr": qvbr.get(),
            "gop_len": gop_len.get(),
            "max_processes": max_processes.get(),
            "crop_params": {
                "crop_w": crop_w_val,
                "crop_h": crop_h_val,
                "crop_x": crop_x_val,
                "crop_y": crop_y_val
            },
            "audio_tracks": selected_tracks,
            "sleep_after_processing": sleep_enable.get()
        }

        root.destroy()
        print("\nSettings collected. Starting processing...\n")
        print(json.dumps(settings, indent=4))
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

    tk.Button(inner_frame, text="Start Processing", command=start_processing).grid(row=6, column=0, padx=10, pady=10, sticky="ew")

    root.update_idletasks()
    required_width = inner_frame.winfo_reqwidth()
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    window_width = min(required_width + 20, screen_width)
    window_height = int(screen_height * 2 / 3)

    root.geometry(f"{window_width}x{window_height}")
    root.mainloop()


# ---------------------------------------------------------------------
# Step 4: The main encode function
# ---------------------------------------------------------------------
def process_video(file_path, settings):
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

    hdr_convert = settings["hdr_enable"]

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
        # "--tier", "1",
        "--profile", "high",
        "--multipass", "2pass-full",
        "--aq",
        "--aq-temporal",
        "--aq-strength", "5",
        "--lookahead", "32",
        "-i", file_path,
        "-o", output_file
    ]

    # Decoding
    if settings["decode_mode"] == "Hardware":
        command.append("--avhw")
    else:
        command.append("--avsw")

    # Always set color tags
    command.extend(["--colormatrix", "bt2020nc"])
    command.extend(["--colorprim", "bt2020"])
    command.extend(["--transfer", "smpte2084"])

    # HDR logic
    if hdr_convert:
        command.append("--vpp-ngx-truehdr")
    else:
        command.extend(["--dhdr10-info", "copy"])
        command.extend(["--dolby-vision-profile", "copy"])
        command.extend(["--dolby-vision-rpu", "copy"])

    # Crop
    crop = settings["crop_params"]
    left = crop["crop_x"]
    top = crop["crop_y"]
    crop_w = crop["crop_w"]
    crop_h = crop["crop_h"]

    if left + crop_w > input_width:
        crop_w = input_width - left
    if top + crop_h > input_height:
        crop_h = input_height - top

    right = input_width - (left + crop_w)
    bottom = input_height - (top + crop_h)
    right = max(right, 0)
    bottom = max(bottom, 0)

    command.extend(["--crop", f"{left},{top},{right},{bottom}"])

    # Additional features
    if settings["fruc_enable"]:
        command.extend(["--vpp-fruc", "fps=60"])
    if settings["denoise_enable"]:
        command.append("--vpp-nvvfx-denoise")
    if settings["artifact_enable"]:
        command.append("--vpp-nvvfx-artifact-reduction")

    chosen_res = settings["resolution_choice"]
    resolution_map = {
        "No Resize": (None, None),
        "HD 1080p":  (1080, 1080),
        "4K 2160p":  (2160, 2160),
        "8K 4320p":  (4320, 4320)
    }
    if chosen_res in resolution_map:
        target_width, target_height = resolution_map[chosen_res]
        # If not "No Resize" => check up vs down scale
        if target_width is not None and target_height is not None:
            if target_width > input_width or target_height > input_height:
                # Up-scaling => use superres
                command.extend([
                    "--vpp-resize",
                    "algo=nvvfx-superres,superres-mode=0",
                    "--output-res", f"{target_width}x{target_height}"
                ])
            else:
                # Down-scaling or same scale => use simpler method (e.g., bilinear)
                if (target_width < input_width) or (target_height < input_height):
                    command.extend([
                        "--vpp-resize",
                        "algo=bilinear",
                        "--output-res", f"{target_width}x{target_height}"
                    ])
                # If exactly same size, do nothing => "No Resize"

    # Audio
    selected_tracks = settings["audio_tracks"]
    tracks_to_copy = []
    tracks_to_convert = []
    for s in selected_tracks:
        track_number = str(s["track_number"])
        if s.get("convert_to_ac3"):
            tracks_to_convert.append(track_number)
        else:
            tracks_to_copy.append(track_number)

    if tracks_to_copy:
        track_str = ",".join(tracks_to_copy)
        command.extend(["--audio-copy", track_str])

    if tracks_to_convert:
        for track_number in tracks_to_convert:
            command.extend(["--audio-codec", f"{track_number}?ac3"])
            command.extend(["--audio-bitrate", f"{track_number}?640"])
            command.extend(["--audio-stream", f"{track_number}?5.1"])

    # Print the command
    quoted_command = ' '.join(f'"{arg}"' if ' ' in arg else arg for arg in command)
    print(f"\nProcessing: {file_path}")
    print("NVEncC command:\n" + quoted_command)
    try:
        subprocess.run(command, check=True)
        print(f"Success: Processed {file_path} -> {output_file}")
        status = "Success"
    except subprocess.CalledProcessError as e:
        print(f"Error: Failed to process {file_path}")
        status = f"Error: {e}"

    # Logging
    with open(log_file, "w", encoding='utf-8') as log:
        log.write("Command:\n" + quoted_command + "\n\n")
        log.write(f"Processing file: {file_path}\n")
        log.write(f"Output file: {output_file}\n")
        log.write(f"Status: {status}\n")


def process_wrapper(args):
    """
    Top-level function so it can be pickled by multiprocessing on Windows.
    Expects (video_file, settings) as a tuple.
    """
    vf, settings = args
    process_video(vf, settings)


def process_batch(video_files, settings):
    try:
        mp = int(settings.get("max_processes", "1"))
    except ValueError:
        mp = 1

    if mp <= 1:
        for vf in video_files:
            process_video(vf, settings)
        return

    print(f"Using multiprocessing with {mp} processes...")

    tasks = [(vf, settings) for vf in video_files]

    with Pool(mp) as p:
        p.map(process_wrapper, tasks)


# ---------------------------------------------------------------------
# Main Script Logic (Batch + GUI)
# ---------------------------------------------------------------------
if __name__ == "__main__":
    video_files = []
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            files_from_glob = glob.glob(arg)  # Expand wildcard patterns
            video_files.extend(files_from_glob) # Add expanded files to the list

    if not video_files: # Check if any files were found after expansion
        print("No video file specified or no files found matching the input patterns.")
        input("Press any key to exit...")
        sys.exit()

    first_file = video_files[0]

    color_data_first = get_video_color_info(first_file)
    cp_first = (color_data_first["color_primaries"] or "").lower()
    cs_first = (color_data_first["color_space"] or "").lower()

    # HDR check
    if cp_first == "bt2020" or cs_first == "bt2020nc":
        default_hdr = False
        limit_value = "128"
    else:
        default_hdr = True
        limit_value = "24"

    first_h, first_w = get_video_resolution(first_file)
    if first_h is None or first_w is None:
        print(f"Error: Could not retrieve resolution for {first_file}. Exiting.")
        sys.exit()

    # Automatic crop detection
    crop_w_val, crop_h_val, crop_x_val, crop_y_val = get_crop_parameters(first_file, first_w, first_h, limit_value=limit_value)
    detected_crop_params = []
    for vf in video_files:
        detected_crop_params.append({
            "file": vf,
            "crop_w": crop_w_val,
            "crop_h": crop_h_val,
            "crop_x": crop_x_val,
            "crop_y": crop_y_val
        })

    print("\nCrop detection complete (only for the first file). Launching GUI...\n")

    # Audio
    all_audio_streams = run_ffprobe_for_audio_streams(first_file)

    # Decide default QVBR
    if first_h >= 4320 or first_w >= 7680:
        default_qvbr = "44"
    elif first_h >= 2160 or first_w >= 3840:
        default_qvbr = "33"
    else:
        default_qvbr = "22"

    # Launch GUI
    launch_gui(
        [d["file"] for d in detected_crop_params],
        detected_crop_params,
        all_audio_streams,
        default_qvbr,
        default_hdr,
        input_width=first_w,
        input_height=first_h
    )

    print("Processing Complete.")
    os.system("pause")