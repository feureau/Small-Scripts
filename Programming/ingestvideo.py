# =================================================================================================
#
#                                  NVEncC AV1 Batch Processor
#                                          Version: 3.0
#
# =================================================================================================
"""
---------------------------------------------------------------------------------------------------
 SCRIPT DOCUMENTATION
---------------------------------------------------------------------------------------------------
**IMPORTANT**: This documentation block should be reviewed and updated with each new iteration of
             this script to ensure it accurately reflects the current codebase and features.

---------------------------------------------------------------------------------------------------
 I. OVERVIEW
---------------------------------------------------------------------------------------------------
This script is a comprehensive, GUI-based batch video encoding tool designed to automate the
process of converting video files to high-quality AV1 format using NVIDIA's NVEncC encoder.

It streamlines the entire workflow by performing pre-analysis (metadata, crop detection),
presenting the user with a clear set of options in a Tkinter GUI, and then processing a batch
of files with robust settings optimized for quality.

The primary goal is to produce archival-quality encodes that respect modern video standards like
HDR (HDR10, Dolby Vision) and can effectively handle challenging content such as film grain.

---------------------------------------------------------------------------------------------------
 II. CORE FEATURES
---------------------------------------------------------------------------------------------------
- Batch Processing: Add multiple files or use wildcards (e.g., *.mkv) for batch encoding.
- Pre-Analysis: Automatically detects HDR metadata, audio tracks, and video resolution from the
  first file to set sensible defaults.
- Automatic Crop Detection: Samples the video at multiple points to intelligently detect and
  remove black bars (letterboxing/pillarboxing), maximizing resolution.
- Interactive GUI: Provides user-friendly controls for all major encoding options, eliminating
  the need for complex command-line arguments.
- Advanced Rate Control: Offers two main modes:
    1. QVBR: Quality-based Variable Bitrate, excellent for achieving a target file size.
    2. CQP: Constant Quantization Parameter, the recommended mode for preserving fine details
       like film grain at the cost of a larger file size.
- Film Grain Preservation: The CQP mode, combined with high-quality presets, is specifically
  designed to retain the aesthetic of film grain, a common challenge for encoders.
- HDR Support: Correctly copies HDR10, HLG, and Dolby Vision metadata to ensure videos display
  correctly on compatible screens.
- Audio Control: Allows selection and passthrough (copy) of multiple audio tracks, or conversion
  to a compatible format like AC3.
- Multiprocessing: Can run multiple encoding jobs in parallel to significantly speed up the
  processing of large batches.

---------------------------------------------------------------------------------------------------
 III. PREREQUISITES
---------------------------------------------------------------------------------------------------
1. Python 3.x: With the following libraries installed:
   - opencv-python: `pip install opencv-python`
   - (Tkinter is usually included with standard Python installations)

2. FFmpeg & FFprobe: Must be installed and accessible in the system's PATH. These are used for
   metadata extraction and crop detection.

3. NVEncC: The NVIDIA Hardware Encoder command-line tool. The script is written for `NVEncC64.exe`
   and it must be accessible in the system's PATH.

---------------------------------------------------------------------------------------------------
 IV. HOW IT WORKS (TECHNICAL BREAKDOWN)
---------------------------------------------------------------------------------------------------
1. INITIALIZATION:
   - The script parses command-line arguments to build a list of video files to process.
   - It then performs a detailed analysis of the *first* video file in the list. This includes
     running `ffprobe` to get color/HDR info and audio stream details, and `ffmpeg` with the
     `cropdetect` filter to find the optimal crop parameters.
   - This initial analysis is used to populate the GUI with intelligent defaults.

2. THE GUI (TKINTER):
   - A GUI window is launched, presenting all configurable options to the user.
   - The user can adjust file lists, crop dimensions, resolution, rate control mode (QVBR/CQP),
     and select audio tracks.
   - The CQP fields include a ratio-locking feature: changing one QP value (for I, P, or B-frames)
     will automatically adjust the other two to maintain their proportional quality difference,
     making it intuitive to tune.
   - Once the user clicks "Start Processing", all selected settings are collected into a
     dictionary.

3. ENCODING PHILOSOPHY (`process_video` function):
   - For each video file, a new `NVEncC64` command is constructed based on the user's settings.
   - The command is built around a philosophy of prioritizing quality:
     - `--codec av1 --output-depth 10`: Uses the modern AV1 codec in 10-bit color for excellent
       compression and prevention of color banding, crucial for HDR.
     - `--preset p7`: This is the highest quality, slowest preset. It enables the most thorough
       analysis, motion estimation, and decision-making by the encoder, which is vital for
       preserving detail.
     - `--lookahead 32`: A large lookahead buffer (32 frames) allows the encoder to make much
       smarter decisions about bit allocation, anticipating complex scenes and distributing bits
       more effectively.
     - `--aq --aq-temporal`: Adaptive Quantization (spatial and temporal) is enabled. This feature
       intelligently distributes more bits to complex, detailed areas of a frame (like grainy
       textures) and fewer bits to flat, simple areas, maximizing perceived quality.
     - Rate Control (The User's Choice):
       - If CQP is selected (`--cqp <I:P:B>`): This is the key to film grain. Instead of targeting
         a bitrate, it targets a constant *quality* level. This forces the encoder to spend
         whatever bits are necessary to preserve the detail in the grain, preventing it from
         being smoothed away. The recommended values (e.g., 18:20:22) are low to ensure high
         fidelity.
       - If QVBR is selected (`--qvbr <value>`): This mode is better for controlling file size
         while still maintaining a quality baseline. It's paired with `--multipass 2pass-full`
         for a more optimized result.

4. BATCH & MULTIPROCESSING:
   - The script uses Python's `multiprocessing.Pool` to spawn a user-defined number of `NVEncC64`
     processes simultaneously, dramatically reducing total processing time for large batches.

---------------------------------------------------------------------------------------------------
"""
# =================================================================================================
#                                  USER-CONFIGURABLE VARIABLES
# =================================================================================================
# --- General Settings ---
NVENC_EXECUTABLE = "NVEncC64"        # Name of the NVEncC executable
OUTPUT_SUBDIR = "processed_videos" # Subdirectory where processed files will be saved

# --- Encoder Quality Settings ---
# These are high-quality defaults. Changing them may impact quality or compatibility.
ENCODER_PRESET = "p7"              # p7 is the highest quality preset.
LOOKAHEAD = "32"                   # Max lookahead for better bitrate control.
GOP_LENGTH = "6"                   # GOP length in seconds.
AQ_STRENGTH = "5"                  # Adaptive Quantization strength (1-15).

# --- Rate Control Defaults ---
# Default CQP values for preserving film grain (I-Frame:P-Frame:B-Frame)
DEFAULT_CQP_I = "20"
DEFAULT_CQP_P = "22"
DEFAULT_CQP_B = "24"

# Default QVBR quality levels based on input video resolution
DEFAULT_QVBR_1080P = "22"
DEFAULT_QVBR_4K = "30"
DEFAULT_QVBR_8K = "40"

# --- Audio Settings ---
AUDIO_CONVERT_BITRATE = "640"      # Bitrate in kbps for AC3 audio conversion.

# --- Crop Detection Settings ---
# More samples are more accurate but take longer.
CROP_DETECT_SAMPLES = 12           # Minimum number of samples to take for crop detection.
CROP_DETECT_INTERVAL_S = 300       # Interval in seconds between samples (e.g., 300 = 5 minutes).

# =================================================================================================
#                                        SCRIPT CORE LOGIC
# =================================================================================================

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
import glob

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
    round_value = "2"
    num_samples = max(CROP_DETECT_SAMPLES, min(72, int(duration // CROP_DETECT_INTERVAL_S)))
    if num_samples < CROP_DETECT_SAMPLES:
        num_samples = CROP_DETECT_SAMPLES
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
    nvvfx_denoise_var = tk.BooleanVar()
    artifact_enable = tk.BooleanVar(value=False)
    resolution_var = tk.StringVar(value="No Resize")
    qvbr = tk.StringVar(value=default_qvbr)
    gop_len = tk.StringVar(value=str(GOP_LENGTH))
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

    def update_crop_offsets(*args):
        try:
            new_crop_w = int(crop_w.get())
            new_crop_h = int(crop_h.get())
            new_crop_w = new_crop_w - (new_crop_w % 2)
            new_crop_h = new_crop_h - (new_crop_h % 2)
            new_crop_x = (input_width - new_crop_w) // 2
            new_crop_y = (input_height - new_crop_h) // 2
            new_crop_x = new_crop_x - (new_crop_x % 2)
            new_crop_y = new_crop_y - (new_crop_y % 2)
            crop_w.set(str(new_crop_w))
            crop_h.set(str(new_crop_h))
            crop_x.set(str(new_crop_x))
            crop_y.set(str(new_crop_y))
        except ValueError:
            pass
    crop_w.trace("w", update_crop_offsets)
    crop_h.trace("w", update_crop_offsets)

    resolution_map = {
        "No Resize": (None, None, None),
        "HD 1080p":  (1920, 1080, DEFAULT_QVBR_1080P),
        "4K 2160p":  (3840, 2160, DEFAULT_QVBR_4K),
        "8K 4320p":  (7680, 4320, DEFAULT_QVBR_8K)
    }
    def on_resolution_change(*args):
        selection = resolution_var.get()
        if selection in resolution_map:
            recommended_qvbr = resolution_map[selection][2]
            if recommended_qvbr is not None:
                qvbr.set(recommended_qvbr)
    resolution_var.trace("w", on_resolution_change)

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
            f"File: {os.path.basename(selected_file)}\n"
            f"Color Range: {color_data['color_range'] or 'N/A'}\n"
            f"Color Primaries: {color_data['color_primaries'] or 'N/A'}\n"
            f"Color Transfer: {color_data['color_transfer'] or 'N/A'}\n"
            f"Color Space: {color_data['color_space'] or 'N/A'}\n"
            f"Mastering Display: {bool(color_data['mastering_display_metadata'])}\n"
            f"Max CLL: {color_data['max_cll'] or 'N/A'}\n"
        )
        metadata_text.config(state='normal')
        metadata_text.delete("1.0", "end")
        metadata_text.insert("1.0", meta_txt)
        metadata_text.config(state='disabled')

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
        file_listbox.select_set(0)

    options_frame = tk.LabelFrame(inner_frame, text="Video Options")
    options_frame.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")
    options_frame.columnconfigure(0, weight=1)
    decode_mode_frame = tk.LabelFrame(options_frame, text="Decoding Mode")
    decode_mode_frame.pack(fill="x", padx=5, pady=5)
    tk.Radiobutton(decode_mode_frame, text="Hardware Decoding", variable=decoding_mode, value="Hardware").pack(anchor="w")
    tk.Radiobutton(decode_mode_frame, text="Software Decoding", variable=decoding_mode, value="Software").pack(anchor="w")

    multi_frame = tk.Frame(options_frame)
    multi_frame.pack(anchor='w', pady=(5, 0))
    tk.Label(multi_frame, text="Max Processes:").pack(side='left')
    tk.Entry(multi_frame, textvariable=max_processes, width=3).pack(side='left', padx=(5, 0))
    tk.Checkbutton(options_frame, text="Enable HDR Conversion (SDR to HDR)", variable=hdr_enable).pack(anchor='w')
    
    resolution_frame = tk.Frame(options_frame)
    resolution_frame.pack(anchor='w', pady=(10,0))
    tk.Label(resolution_frame, text="Output Resolution:").pack(side='left')
    tk.OptionMenu(resolution_frame, resolution_var, *resolution_map.keys()).pack(side='left', padx=(5,0))
    tk.Checkbutton(options_frame, text="Enable FRUC (fps=60)", variable=fruc_enable).pack(anchor='w')
    
    nvvfx_denoise_check = tk.Checkbutton(options_frame, text="Enable Denoising (NVVFX - for < 1080p)", variable=nvvfx_denoise_var)
    nvvfx_denoise_check.pack(anchor='w')
    if input_height >= 1080 and input_width >= 1920:
        nvvfx_denoise_check.config(state='disabled')
    
    artifact_reduction_var = tk.BooleanVar(value=False)
    tk.Checkbutton(options_frame, text="Enable Artifact Reduction (NVVFX)", variable=artifact_reduction_var).pack(anchor='w')
    
    rate_control_mode = tk.StringVar(value="QVBR")
    cqp_i = tk.StringVar(value=DEFAULT_CQP_I)
    cqp_p = tk.StringVar(value=DEFAULT_CQP_P)
    cqp_b = tk.StringVar(value=DEFAULT_CQP_B)
    _is_updating_cqp = False

    def _update_cqp_ratios(*args, source_var=None):
        nonlocal _is_updating_cqp
        if _is_updating_cqp: return
        _is_updating_cqp = True
        
        ratio_p_to_i = int(DEFAULT_CQP_P) / int(DEFAULT_CQP_I)
        ratio_b_to_i = int(DEFAULT_CQP_B) / int(DEFAULT_CQP_I)

        try:
            if source_var == 'i':
                base_val = int(cqp_i.get())
                cqp_p.set(str(round(base_val * ratio_p_to_i)))
                cqp_b.set(str(round(base_val * ratio_b_to_i)))
            elif source_var == 'p':
                p_val = int(cqp_p.get())
                base_val = round(p_val / ratio_p_to_i)
                cqp_i.set(str(base_val))
                cqp_b.set(str(round(base_val * ratio_b_to_i)))
            elif source_var == 'b':
                b_val = int(cqp_b.get())
                base_val = round(b_val / ratio_b_to_i)
                cqp_i.set(str(base_val))
                cqp_p.set(str(round(base_val * ratio_p_to_i)))
        except (ValueError, ZeroDivisionError): pass
        finally: _is_updating_cqp = False

    cqp_i.trace_add("write", lambda *args: _update_cqp_ratios(*args, source_var='i'))
    cqp_p.trace_add("write", lambda *args: _update_cqp_ratios(*args, source_var='p'))
    cqp_b.trace_add("write", lambda *args: _update_cqp_ratios(*args, source_var='b'))

    rc_frame = tk.LabelFrame(options_frame, text="Rate Control")
    rc_frame.pack(fill='x', padx=5, pady=5)
    qvbr_options_frame = tk.Frame(rc_frame)
    cqp_options_frame = tk.Frame(rc_frame)

    tk.Label(qvbr_options_frame, text="Target QVBR:").grid(row=0, column=0, sticky='w')
    tk.Entry(qvbr_options_frame, textvariable=qvbr, width=5).grid(row=0, column=1, padx=5, sticky='w')
    tk.Label(cqp_options_frame, text="QP (I):").grid(row=0, column=0, sticky='w')
    tk.Entry(cqp_options_frame, textvariable=cqp_i, width=5).grid(row=0, column=1, padx=5, sticky='w')
    tk.Label(cqp_options_frame, text="QP (P):").grid(row=0, column=2, sticky='w', padx=(10,0))
    tk.Entry(cqp_options_frame, textvariable=cqp_p, width=5).grid(row=0, column=3, padx=5, sticky='w')
    tk.Label(cqp_options_frame, text="QP (B):").grid(row=0, column=4, sticky='w', padx=(10,0))
    tk.Entry(cqp_options_frame, textvariable=cqp_b, width=5).grid(row=0, column=5, padx=5, sticky='w')

    def update_rate_control_ui(*args):
        if rate_control_mode.get() == "CQP":
            qvbr_options_frame.pack_forget()
            cqp_options_frame.pack(anchor='w', pady=5)
        else:
            cqp_options_frame.pack_forget()
            qvbr_options_frame.pack(anchor='w', pady=5)

    radio_frame = tk.Frame(rc_frame)
    radio_frame.pack(anchor='w', pady=(0, 5))
    tk.Radiobutton(radio_frame, text="QVBR (Target Bitrate)", variable=rate_control_mode, value="QVBR", command=update_rate_control_ui).pack(side='left')
    tk.Radiobutton(radio_frame, text="CQP (Target Quality / Film Grain)", variable=rate_control_mode, value="CQP", command=update_rate_control_ui).pack(side='left', padx=10)
    update_rate_control_ui()

    gop_frame = tk.Frame(options_frame)
    gop_frame.pack(anchor='w', pady=(5, 0))
    tk.Label(gop_frame, text="GOP Length (sec):").pack(side='left', anchor='w')
    tk.Entry(gop_frame, textvariable=gop_len, width=6).pack(side='left', padx=(5, 0), anchor='w')

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
        state = 'disabled' if no_crop_var.get() else 'normal'
        if no_crop_var.get():
            crop_w.set(str(input_width))
            crop_h.set(str(input_height))
            crop_x.set("0")
            crop_y.set("0")
        else:
            crop_w.set(str(original_crop_w))
            crop_h.set(str(original_crop_h))
            crop_x.set(str(original_crop_x))
            crop_y.set(str(original_crop_y))
        for entry in [width_entry, height_entry, x_entry, y_entry]:
            entry.config(state=state)

    tk.Checkbutton(crop_frame, text="No Crop", variable=no_crop_var, command=on_no_crop_toggle).grid(row=4, column=0, columnspan=2, pady=(10, 0), sticky="w", padx=5)

    audio_tracks_frame = tk.LabelFrame(inner_frame, text="Audio Tracks")
    audio_tracks_frame.grid(row=4, column=0, padx=10, pady=10, sticky="nsew")
    audio_tracks_frame.columnconfigure(0, weight=1)
    audio_tracks_frame.columnconfigure(1, weight=1)
    button_frame = tk.Frame(audio_tracks_frame)
    button_frame.grid(row=0, column=0, columnspan=2, sticky="n", padx=5, pady=5)
    def on_select_all_audio(): [var.set(True) for var in audio_vars]
    def on_clear_all_audio(): [var.set(False) for var in audio_vars]
    def copy_all_audio(): [var.set(False) for var in convert_vars]
    def convert_all_audio(): [var.set(True) for var in convert_vars]
    tk.Button(button_frame, text="Select All", command=on_select_all_audio).pack(side='left', padx=2)
    tk.Button(button_frame, text="Clear All", command=on_clear_all_audio).pack(side='left', padx=2)
    tk.Button(button_frame, text="Copy All", command=copy_all_audio).pack(side='left', padx=2)
    tk.Button(button_frame, text="Convert All", command=convert_all_audio).pack(side='left', padx=2)
    if audio_streams:
        for idx, stream in enumerate(audio_streams, start=1):
            track_frame = tk.Frame(audio_tracks_frame)
            track_frame.grid(row=idx, column=0, padx=5, pady=2, sticky='e')
            auto_selected = (stream['language'] == 'eng')
            track_label = f"Track {stream['track_number']}: {stream['codec']} ({stream['language'] or 'N/A'}, {stream.get('channels', 0)}-ch)"
            tk.Label(track_frame, text=track_label, anchor='e').pack(side='left')
            track_var = tk.BooleanVar(value=auto_selected)
            tk.Checkbutton(track_frame, variable=track_var).pack(side='right', padx=(5,0))
            audio_vars.append(track_var)
            convert_var = tk.BooleanVar(value=(stream['codec'] != 'ac3'))
            tk.Checkbutton(audio_tracks_frame, text="Convert to AC3", variable=convert_var, anchor='w').grid(row=idx, column=1, padx=5, pady=2, sticky='w')
            convert_vars.append(convert_var)
    else:
        tk.Label(audio_tracks_frame, text="No audio tracks found.").grid(row=1, column=0, padx=5, pady=5, sticky='w')
    
    tk.Checkbutton(inner_frame, text="Put Computer to Sleep on Completion", variable=sleep_enable).grid(row=5, column=0, padx=10, pady=5, sticky="w")
    
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
            crop_w_val = int(crop_w.get()) - (int(crop_w.get()) % 2)
            crop_h_val = int(crop_h.get()) - (int(crop_h.get()) % 2)
            crop_x_val = int(crop_x.get()) - (int(crop_x.get()) % 2)
            crop_y_val = int(crop_y.get()) - (int(crop_y.get()) % 2)
            if any(v <= 0 for v in [crop_w_val, crop_h_val]) or any(v < 0 for v in [crop_x_val, crop_y_val]):
                raise ValueError("Invalid dimensions or offsets")
            if crop_x_val + crop_w_val > input_width or crop_y_val + crop_h_val > input_height:
                messagebox.showerror("Error", "Crop parameters exceed video dimensions.")
                return
        except ValueError:
            messagebox.showerror("Error", "Invalid crop parameters. Please enter positive integers.")
            return
        
        settings = {
            "files": selected_files,
            "decode_mode": decoding_mode.get(),
            "hdr_enable": hdr_enable.get(),
            "resolution_choice": resolution_var.get(),
            "fruc_enable": fruc_enable.get(),
            "denoise_enable": nvvfx_denoise_var.get(),
            "artifact_enable": artifact_reduction_var.get(),
            "rate_control_mode": rate_control_mode.get(),
            "qvbr": qvbr.get(),
            "cqp_i": cqp_i.get(),
            "cqp_p": cqp_p.get(),
            "cqp_b": cqp_b.get(),
            "gop_len": gop_len.get(),
            "max_processes": max_processes.get(),
            "crop_params": {"crop_w": crop_w_val, "crop_h": crop_h_val, "crop_x": crop_x_val, "crop_y": crop_y_val},
            "audio_tracks": selected_tracks,
            "sleep_after_processing": sleep_enable.get()
        }
        root.destroy()
        print("\nSettings collected. Starting processing...\n" + json.dumps(settings, indent=4))
        process_batch(settings["files"], settings)
        if settings.get("sleep_after_processing"):
            print("Putting the computer to sleep...")
            if platform.system() == "Windows": os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
            elif platform.system() == "Linux": os.system("systemctl suspend")
            elif platform.system() == "Darwin": os.system("pmset sleepnow")
            else: print("Sleep command not supported on this platform.")
            
    tk.Button(inner_frame, text="Start Processing", command=start_processing).grid(row=6, column=0, padx=10, pady=10, sticky="ew")
    root.update_idletasks()
    window_width = min(inner_frame.winfo_reqwidth() + 40, root.winfo_screenwidth())
    window_height = min(inner_frame.winfo_reqheight() + 40, int(root.winfo_screenheight() * 0.9))
    root.geometry(f"{window_width}x{window_height}")
    root.mainloop()

# ---------------------------------------------------------------------
# Step 4: The main encode function
# ---------------------------------------------------------------------
def process_video(file_path, settings):
    input_dir = os.path.dirname(file_path)
    file_name = os.path.basename(file_path)
    output_subdir = os.path.join(input_dir, OUTPUT_SUBDIR)
    os.makedirs(output_subdir, exist_ok=True)
    output_file = os.path.join(output_subdir, os.path.splitext(file_name)[0] + ".mp4")
    log_file = os.path.join(output_subdir, os.path.splitext(file_name)[0] + "_encoding.log")
    input_height, input_width = get_video_resolution(file_path)
    if input_height is None:
        print(f"Error: Could not retrieve resolution for {file_path}. Skipping.")
        return

    command = [
        NVENC_EXECUTABLE,
        "--codec", "av1",
        "--preset", ENCODER_PRESET,
        "--output-depth", "10",
        "--gop-len", settings["gop_len"],
        "--metadata", "copy",
        "--chapter-copy",
        "--bframes", "4",
        "--tf-level", "4",
        "--max-bitrate", "100000",
        "--split-enc", "disable",
        "--profile", "main",
        "--aq",
        "--aq-temporal",
        "--aq-strength", AQ_STRENGTH,
        "--lookahead", LOOKAHEAD,
    ]

    if settings["rate_control_mode"] == "CQP":
        print("Using CQP mode for preserving film grain.")
        cqp_values = f'{settings["cqp_i"]}:{settings["cqp_p"]}:{settings["cqp_b"]}'
        command.extend(["--cqp", cqp_values])
    else:
        print("Using QVBR mode.")
        command.extend(["--qvbr", settings["qvbr"], "--multipass", "2pass-full"])

    command.extend(["-i", file_path, "-o", output_file])
    
    command.append("--avhw" if settings["decode_mode"] == "Hardware" else "--avsw")
    
    command.extend(["--colormatrix", "bt2020nc", "--colorprim", "bt2020", "--transfer", "smpte2084"])
    
    if settings["hdr_enable"]:
        command.append("--vpp-ngx-truehdr")
    else:
        command.extend(["--dhdr10-info", "copy", "--dolby-vision-profile", "copy", "--dolby-vision-rpu", "copy"])

    crop = settings["crop_params"]
    right = input_width - (crop["crop_x"] + crop["crop_w"])
    bottom = input_height - (crop["crop_y"] + crop["crop_h"])
    command.extend(["--crop", f'{crop["crop_x"]},{crop["crop_y"]},{max(0, right)},{max(0, bottom)}'])

    if settings["fruc_enable"]: command.extend(["--vpp-fruc", "fps=60"])
    if settings["denoise_enable"]: command.append("--vpp-nvvfx-denoise")
    if settings["artifact_enable"]: command.append("--vpp-nvvfx-artifact-reduction")
    
    chosen_res = settings["resolution_choice"]
    resolution_map = {
        "No Resize": None, "HD 1080p": 1080, "4K 2160p": 2160, "8K 4320p": 4320
    }
    target_h = resolution_map.get(chosen_res)
    if target_h:
        current_w, current_h = crop["crop_w"], crop["crop_h"]
        output_h = target_h
        output_w = int(current_w * (output_h / current_h)) - (int(current_w * (output_h / current_h)) % 2)
        
        if output_w > current_w or output_h > current_h:
            command.extend(["--vpp-resize", "algo=nvvfx-superres,superres-mode=0", "--output-res", f"{output_w}x{output_h}"])
        elif output_w < current_w or output_h < current_h:
            command.extend(["--vpp-resize", "algo=spline36", "--output-res", f"{output_w}x{output_h}"])

    audio_to_copy = [s["track_number"] for s in settings["audio_tracks"] if not s.get("convert_to_ac3")]
    audio_to_convert = [s["track_number"] for s in settings["audio_tracks"] if s.get("convert_to_ac3")]
    if audio_to_copy: command.extend(["--audio-copy", ",".join(map(str, audio_to_copy))])
    for track in audio_to_convert:
        command.extend([f"--audio-codec", f"{track}?ac3", f"--audio-bitrate", f"{track}?{AUDIO_CONVERT_BITRATE}", f"--audio-stream", f"{track}?5.1", f"--audio-samplerate", f"{track}?48000"])

    quoted_command = ' '.join(f'"{arg}"' if ' ' in arg else arg for arg in command)
    print(f"\nProcessing: {file_name}\nNVEncC command:\n{quoted_command}")
    try:
        subprocess.run(command, check=True)
        status = "Success"
    except subprocess.CalledProcessError as e:
        status = f"Error: {e}"
    
    print(f"{status}: Processed {file_name} -> {os.path.basename(output_file)}")
    with open(log_file, "w", encoding='utf-8') as log:
        log.write(f"Command:\n{quoted_command}\n\nStatus: {status}\n")

def process_wrapper(args):
    process_video(*args)

def process_batch(video_files, settings):
    mp = int(settings.get("max_processes", "1"))
    tasks = [(vf, settings) for vf in video_files]
    if mp > 1:
        print(f"Using multiprocessing with {mp} processes...")
        with Pool(mp) as p:
            p.map(process_wrapper, tasks)
    else:
        for task in tasks:
            process_wrapper(task)

# ---------------------------------------------------------------------
# Main Script Logic
# ---------------------------------------------------------------------
if __name__ == "__main__":
    video_files = [f for arg in sys.argv[1:] for f in glob.glob(arg)]
    if not video_files:
        print("No video file specified or no files found matching input patterns.")
        input("Press Enter to exit...")
        sys.exit()

    first_file = video_files[0]
    color_data = get_video_color_info(first_file)
    is_hdr = (color_data.get("color_primaries") == "bt2020" or color_data.get("color_space") == "bt2020nc")
    
    first_h, first_w = get_video_resolution(first_file)
    if first_h is None:
        print(f"Error: Could not retrieve resolution for {first_file}. Exiting.")
        sys.exit()

    crop_params = get_crop_parameters(first_file, first_w, first_h, limit_value="128" if is_hdr else "24")
    
    if first_h >= 4320 or first_w >= 7680: default_qvbr = DEFAULT_QVBR_8K
    elif first_h >= 2160 or first_w >= 3840: default_qvbr = DEFAULT_QVBR_4K
    else: default_qvbr = DEFAULT_QVBR_1080P

    launch_gui(
        file_list=video_files,
        crop_params=[{"file": vf, **dict(zip(["crop_w", "crop_h", "crop_x", "crop_y"], crop_params))} for vf in video_files],
        audio_streams=run_ffprobe_for_audio_streams(first_file),
        default_qvbr=default_qvbr,
        default_hdr=not is_hdr,
        input_width=first_w,
        input_height=first_h
    )
    print("Processing Complete.")
    os.system("pause")