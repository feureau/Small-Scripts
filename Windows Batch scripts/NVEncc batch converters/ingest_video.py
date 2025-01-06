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
    Returns list of dicts with {track_number, stream_index, codec, language, channels}.
    """
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
                    try:
                        w, h, x, y = [int(v) for v in crop_str.split(':')]
                        print(f"Detected crop at {int(start_time)}s: width={w}, height={h}, x={x}, y={y}")
                    except ValueError:
                        print(f"Invalid crop parameters detected: {crop_str}")
            # If we've found enough crop values, break early
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
    """
    Build & launch the Tkinter GUI for user adjustments.
    Always default to Hardware decoding for the user.

    Audio logic:
      - Each track has a "Convert to AC3" checkbox
      - "Copy All" and "Convert All" buttons to set all tracks
      Also, if user selects "Resize to 4K", automatically set qvbr=30.
    """
    root = tk.Tk()
    root.title("Video Processing Settings")

    # Get screen dimensions
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    # Create a Canvas and Scrollbar
    main_frame = tk.Frame(root)
    main_frame.pack(fill='both', expand=True)

    canvas = tk.Canvas(main_frame)
    canvas.pack(side='left', fill='both', expand=True)

    scrollbar = tk.Scrollbar(main_frame, orient='vertical', command=canvas.yview)
    scrollbar.pack(side='right', fill='y')

    canvas.configure(yscrollcommand=scrollbar.set)

    # Bind mousewheel to scrollbar
    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    canvas.bind_all("<MouseWheel>", _on_mousewheel)

    # Create a frame inside the canvas
    inner_frame = tk.Frame(canvas)
    canvas.create_window((0, 0), window=inner_frame, anchor='nw')

    # Update scrollregion after adding all widgets
    def _configure_event(event):
        canvas.configure(scrollregion=canvas.bbox("all"))

    inner_frame.bind("<Configure>", _configure_event)

    # Initialize variables
    decoding_mode = tk.StringVar(value="Hardware")
    hdr_enable = tk.BooleanVar(value=default_hdr)
    sleep_enable = tk.BooleanVar(value=False)

    resize_enable = tk.BooleanVar()
    fruc_enable = tk.BooleanVar()
    denoise_enable = tk.BooleanVar()
    artifact_enable = tk.BooleanVar()

    qvbr = tk.StringVar(value=default_qvbr)
    gop_len = tk.StringVar(value="6")

    # No Crop Checkbox Variable
    no_crop_var = tk.BooleanVar(value=False)

    metadata_text = None

    # Audio Select All Variable and previous selection storage
    select_all_var = tk.BooleanVar(value=False)
    previous_audio_selections = []

    # Variable to store the previous QVBR value when "Resize to 4K" is toggled
    previous_qvbr = [None]  # Using list to make it mutable in nested function

    def on_resize_toggle():
        if resize_enable.get():
            # Remember the current QVBR value
            previous_qvbr[0] = qvbr.get()
            # Set QVBR to 30
            qvbr.set("30")
        else:
            # Restore the previous QVBR value if it exists
            if previous_qvbr[0] is not None:
                qvbr.set(previous_qvbr[0])
                previous_qvbr[0] = None
            else:
                # If no previous value stored, set based on resolution
                if input_width <= 1920 and input_height <= 1080:
                    qvbr.set("20")
                else:
                    qvbr.set("30")

    def on_no_crop_toggle():
        if no_crop_var.get():
            # "No Crop" is checked: reset crop parameters to input size
            crop_w.set(str(input_width))
            crop_h.set(str(input_height))
            crop_x.set("0")
            crop_y.set("0")
            # Disable crop entries
            width_entry.config(state='disabled')
            height_entry.config(state='disabled')
            x_entry.config(state='disabled')
            y_entry.config(state='disabled')
        else:
            # "No Crop" is unchecked: restore original crop parameters
            crop_w.set(str(original_crop_w))
            crop_h.set(str(original_crop_h))
            crop_x.set(str(original_crop_x))
            crop_y.set(str(original_crop_y))
            # Enable crop entries
            width_entry.config(state='normal')
            height_entry.config(state='normal')
            x_entry.config(state='normal')
            y_entry.config(state='normal')

    def on_select_all_toggle():
        nonlocal previous_audio_selections
        if select_all_var.get():
            # Store current selections
            previous_audio_selections = [var.get() for var in audio_vars]
            # Select all
            for var in audio_vars:
                var.set(True)
        else:
            # Restore previous selections
            for var, prev in zip(audio_vars, previous_audio_selections):
                var.set(prev)

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
    file_frame = tk.Frame(inner_frame)
    file_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
    file_frame.columnconfigure(0, weight=1)
    file_frame.rowconfigure(0, weight=1)

    file_listbox = tk.Listbox(file_frame, height=15, selectmode='extended')
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
    file_controls.grid(row=0, column=1, padx=5, sticky="ns")

    tk.Button(file_controls, text="Add Files", command=lambda: add_files(file_listbox)).pack(fill='x', pady=(0,5))
    tk.Button(file_controls, text="Clear List", command=lambda: file_listbox.delete(0, 'end')).pack(fill='x', pady=(0,5))
    tk.Button(file_controls, text="Move Up", command=lambda: move_up(file_listbox)).pack(fill='x', pady=(0,5))
    tk.Button(file_controls, text="Move Down", command=lambda: move_down(file_listbox)).pack(fill='x', pady=(0,5))
    tk.Button(file_controls, text="Delete Selected", command=lambda: delete_selected(file_listbox)).pack(fill='x', pady=(0,5))

    # Metadata Text
    metadata_frame = tk.LabelFrame(inner_frame, text="Color Metadata")
    metadata_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
    metadata_frame.columnconfigure(0, weight=1)
    metadata_frame.rowconfigure(0, weight=1)
    metadata_text = tk.Text(metadata_frame, height=8, wrap="word", state='disabled', bg="#f0f0f0")
    metadata_text.grid(row=0, column=0, sticky="nsew")

    if file_list:
        update_metadata_display(file_list[0])

    # Options
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

    tk.Checkbutton(options_frame, text="Enable HDR Conversion", variable=hdr_enable).pack(anchor='w')

    tk.Checkbutton(options_frame, text="Resize to 4K", variable=resize_enable, command=on_resize_toggle).pack(anchor='w')
    tk.Checkbutton(options_frame, text="Enable FRUC (fps=60)", variable=fruc_enable).pack(anchor='w')
    tk.Checkbutton(options_frame, text="Enable Denoising", variable=denoise_enable).pack(anchor='w')
    tk.Checkbutton(options_frame, text="Enable Artifact Reduction", variable=artifact_enable).pack(anchor='w')

    tk.Label(options_frame, text="Target QVBR:").pack(anchor='w', pady=(10,0))
    qvbr_entry = tk.Entry(options_frame, textvariable=qvbr)
    qvbr_entry.pack(anchor='w', fill='x')

    tk.Label(options_frame, text="GOP Length:").pack(anchor='w', pady=(10,0))
    tk.Entry(options_frame, textvariable=gop_len).pack(anchor='w', fill='x')

    # Crop UI
    crop_frame = tk.LabelFrame(inner_frame, text="Crop Parameters (Modify if needed)")
    crop_frame.grid(row=3, column=0, padx=10, pady=10, sticky="nsew")
    crop_frame.columnconfigure(1, weight=1)

    crop_w = tk.StringVar(value=str(crop_params[0]['crop_w']) if crop_params else "0")
    crop_h = tk.StringVar(value=str(crop_params[0]['crop_h']) if crop_params else "0")
    crop_x = tk.StringVar(value=str(crop_params[0]['crop_x']) if crop_params else "0")
    crop_y = tk.StringVar(value=str(crop_params[0]['crop_y']) if crop_params else "0")

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

    # "No Crop" Checkbox
    no_crop_checkbox = tk.Checkbutton(
        crop_frame,
        text="No Crop",
        variable=no_crop_var,
        command=on_no_crop_toggle
    )
    no_crop_checkbox.grid(row=4, column=0, columnspan=2, pady=(10, 0), sticky="w", padx=5)

    # Audio Tracks
    audio_tracks_frame = tk.LabelFrame(inner_frame, text="Audio Tracks")
    audio_tracks_frame.grid(row=5, column=0, padx=10, pady=10, sticky="nsew")
    audio_tracks_frame.columnconfigure(1, weight=1)

    if audio_streams:
        # "Select All" Checkbox in a separate column to the left
        select_all_checkbox = tk.Checkbutton(audio_tracks_frame, text="Select All", variable=select_all_var, command=on_select_all_toggle)
        select_all_checkbox.grid(row=0, column=0, padx=5, pady=2, sticky='nw')

        # "Copy All" and "Convert All" Buttons
        def copy_all_audio():
            for var in convert_vars:
                var.set(False)

        def convert_all_audio():
            for var in convert_vars:
                var.set(True)

        tk.Button(audio_tracks_frame, text="Copy All", command=copy_all_audio).grid(row=0, column=1, sticky='w', padx=5, pady=2)
        tk.Button(audio_tracks_frame, text="Convert All", command=convert_all_audio).grid(row=0, column=2, sticky='w', padx=5, pady=2)

        # Audio Track Checkboxes
        audio_vars = []
        convert_vars = []
        for idx, stream in enumerate(audio_streams, start=1):
            audio_var = tk.BooleanVar(value=False)
            convert_var = tk.BooleanVar(value=(stream['codec'] != 'ac3'))
            language = stream['language'] if stream['language'] else 'N/A'
            channels = stream.get('channels', 0)
            channel_desc = {1: 'Mono', 2: 'Stereo', 6: '5.1', 8: '7.1'}.get(channels, f'{channels}-channel')
            label_txt = f"Track {stream['track_number']}: {stream['codec']} ({language}, {channel_desc})"
            tk.Checkbutton(audio_tracks_frame, text=label_txt, variable=audio_var).grid(row=idx, column=1, sticky='w', padx=5, pady=2)
            tk.Checkbutton(audio_tracks_frame, text="Convert to AC3", variable=convert_var).grid(row=idx, column=2, sticky='w', padx=5, pady=2)
            audio_vars.append(audio_var)
            convert_vars.append(convert_var)
    else:
        # If there are no audio streams, display a message
        tk.Label(audio_tracks_frame, text="No audio tracks found in the selected file.").grid(row=0, column=0, padx=5, pady=5, sticky='w')

    tk.Checkbutton(inner_frame, text="Put Computer to Sleep", variable=sleep_enable).grid(row=6, column=0, padx=10, pady=5, sticky="w")

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

        # <-- Removed the strict requirement that at least one audio track must be selected
        # if not selected_tracks:
        #     messagebox.showerror("Error", "At least one audio track must be selected.")
        #     return

        # Validate crop parameters
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
            "crop_params": {
                "crop_w": crop_w_val,
                "crop_h": crop_h_val,
                "crop_x": crop_x_val,
                "crop_y": crop_y_val
            },
            # Allow zero selected audio tracks
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

    tk.Button(inner_frame, text="Start Processing", command=start_processing).grid(row=7, column=0, padx=10, pady=10, sticky="ew")

    # After all widgets are added, update the window size dynamically
    root.update_idletasks()  # Ensure all widgets are rendered

    # Calculate the required width
    required_width = inner_frame.winfo_reqwidth()
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    # Set the window width to the required width, but not exceeding the screen width
    window_width = min(required_width + 20, screen_width)  # Adding some padding
    window_height = int(screen_height * 2 / 3)  # Set to 2/3 of screen height

    root.geometry(f"{window_width}x{window_height}")

    root.mainloop()


# ---------------------------------------------------------------------
# Step 4: The main encode function
# ---------------------------------------------------------------------
def process_video(file_path, settings):
    """
    Audio logic:
      For each track:
        - If convert_to_ac3 is True:
            --audio-codec <trackNumber>?ac3
            --audio-bitrate <trackNumber>?640
            --audio-stream <trackNumber>?5.1
        - Else:
            Include in --audio-copy
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

    # hdr_convert and qvbr are already set via the GUI
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

    # Decode mode
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

    # Ensure crop_w and crop_h do not exceed input dimensions
    if left + crop_w > input_width:
        crop_w = input_width - left
    if top + crop_h > input_height:
        crop_h = input_height - top

    # Prevent negative crop values
    right = input_width - (left + crop_w)
    bottom = input_height - (top + crop_h)

    # Prevent negative crop values
    right = max(right, 0)
    bottom = max(bottom, 0)

    command.extend(["--crop", f"{left},{top},{right},{bottom}"])

    # Additional features
    if settings["resize_enable"]:
        command.extend(["--vpp-resize", "algo=nvvfx-superres,superres-mode=0", "--output-res", "3840x2160"])
    if settings["fruc_enable"]:
        command.extend(["--vpp-fruc", "fps=60"])
    if settings["denoise_enable"]:
        command.append("--vpp-nvvfx-denoise")
    if settings["artifact_enable"]:
        command.append("--vpp-nvvfx-artifact-reduction")

    # Audio logic
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

    # Print the command with quotes around arguments that contain spaces
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

    # Set default QVBR based on whether video is HD or not
    if first_h <= 1080 and first_w <= 1920:
        default_qvbr = "20"
    else:
        default_qvbr = "30"  # Set to 30 for non-HD videos

    # Crop detection on the first file
    crop_w, crop_h, crop_x, crop_y = get_crop_parameters(first_file, first_w, first_h, limit_value=limit_value)

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

    # Pass input_width and input_height to the GUI
    launch_gui(
        [d["file"] for d in detected_crop_params],
        detected_crop_params,
        all_audio_streams,
        default_qvbr,
        default_hdr,
        input_width=first_w,
        input_height=first_h
    )

    print("All processing complete. Press any key to exit...")
    input()
