# =================================================================================================
#
#                                  NVEncC AV1 Batch Processor
#                                          Version: 4.5 (Final)
#
# =================================================================================================
"""
---------------------------------------------------------------------------------------------------
 SCRIPT DOCUMENTATION
---------------------------------------------------------------------------------------------------
**IMPORTANT**: This documentation block is an integral part of the script and must be reviewed and
             updated with each new version to accurately reflect the current codebase, features,
             and design philosophy.

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
- Automatic Crop Detection: Samples the video at multiple points and displays its findings in
  real-time in the console.
- Interactive GUI: Provides user-friendly controls for all major encoding options in a two-column
  layout designed for modern widescreen monitors.
- Dynamic Console Output: During encoding, the script displays NVEncC's progress (FPS, ETA, etc.)
  in real-time by explicitly handling carriage returns and using ANSI escape codes to cleanly
  overwrite the progress line in place.
- Flexible Sample Bracketing: Allows the user to generate a symmetrical set of test clips
  around a baseline quality setting. The user can define the number of "Bracket Steps" and the
  "Step Size" (the quality increment), similar to exposure bracketing in photography.
- Estimated File Size: After each sample is created, it is renamed to include a projection
  of the final video's file size (e.g., "..._~4.5GB.mp4"), allowing for easy quality vs. size
  comparison.
- Advanced Rate Control: Offers two main modes:
    1. QVBR: Quality-based Variable Bitrate, excellent for achieving a target file size.
    2. CQP: Constant Quantization Parameter, the recommended mode for preserving fine details
       like film grain at the cost of a larger file size.
- HDR Support: Correctly copies HDR10, HLG, and Dolby Vision metadata to ensure videos display
  correctly on compatible screens.
- Audio Control: Allows selection and passthrough (copy) of multiple audio tracks, or conversion
  to a compatible format like AC3.
- Multiprocessing: Can run multiple encoding jobs in parallel to leverage multi-core CPUs and
  significantly reduce the total processing time for large batches.

---------------------------------------------------------------------------------------------------
 III. PREREQUISITES
---------------------------------------------------------------------------------------------------
1. Python 3.x: With the following libraries installed:
   - opencv-python: `pip install opencv-python`
   - (Tkinter is usually included with standard Python installations)

2. FFmpeg & FFprobe: Must be installed and accessible in the system's PATH.

3. NVEncC: The NVIDIA Hardware Encoder command-line tool. The script is written for `NVEncC64.exe`
   and it must be accessible in the system's PATH.

---------------------------------------------------------------------------------------------------
 IV. HOW IT WORKS & DESIGN PHILOSOPHY
---------------------------------------------------------------------------------------------------
1. INITIALIZATION & ANALYSIS:
   - The script parses command-line arguments to build a list of video files to process.
   - It performs a detailed analysis of the *first* video file for intelligent GUI defaults.

2. THE GUI (TKINTER):
   - A GUI window is launched with a two-column layout to prevent an overly tall window and to
     separate interactive settings (left) from informational displays and lists (right).
   - A core design principle is the avoidance of blocking pop-up dialogs. All feedback,
     including errors and completion notices, is printed to the console. This ensures the user
     can always see the script's status in a log-friendly, non-blocking manner and is a
     mandatory feature for all future versions.

3. ENCODING PHILOSOPHY (`execute_nvencc` function):
   - This function uses `subprocess.Popen` to launch the NVEncC encoder. To provide real-time
     progress updates, it reads the encoder's stdout stream line-by-line. If a line is a
     progress update, it is printed with a preceding carriage return (`\r`) and a trailing
     ANSI escape code (`\x1b[K`) to erase any leftover characters from the previous, longer line.
   - The command is built around prioritizing quality. The reasoning for key arguments is as follows:
     - `--codec av1 --output-depth 10`: To use the modern AV1 codec for superior compression
       efficiency and 10-bit color to prevent color banding, crucial for HDR content.
     - `--preset p7`: The highest quality, slowest preset, enabling the most thorough analysis.
     - `--lookahead 32`: A large lookahead buffer for smarter bit allocation on complex scenes.
     - `--aq --aq-temporal`: Adaptive Quantization to maximize perceived visual quality.

4. SAMPLE GENERATION:
   - To guarantee samples are accurate previews, the script first uses FFmpeg to create a
     temporary, 10-second clip via a lossless stream copy. This clip is then fed into the
     exact same encoding function used for the final output, ensuring consistency.

---------------------------------------------------------------------------------------------------
"""
# =================================================================================================
#                                  USER-CONFIGURABLE VARIABLES
# =================================================================================================
# --- General Settings ---
NVENC_EXECUTABLE = "NVEncC64"
OUTPUT_SUBDIR = "processed_videos"

# --- Encoder Quality Settings ---
ENCODER_PRESET = "p7"
LOOKAHEAD = "32"
GOP_LENGTH = "6"
AQ_STRENGTH = "5"

# --- Rate Control Defaults ---
DEFAULT_CQP_I = "20"
DEFAULT_CQP_P = "22"
DEFAULT_CQP_B = "24"
DEFAULT_QVBR_1080P = "22"
DEFAULT_QVBR_4K = "30"
DEFAULT_QVBR_8K = "40"

# --- Audio Settings ---
AUDIO_CONVERT_BITRATE = "640"

# --- Crop Detection Settings ---
CROP_DETECT_SAMPLES = 12
CROP_DETECT_INTERVAL_S = 300

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
from tkinter import filedialog
from collections import Counter
from multiprocessing import Pool
import glob
import tempfile
import math

# ---------------------------------------------------------------------
# Step 1: ffprobe-based metadata extraction
# ---------------------------------------------------------------------
def get_video_color_info(video_file):
    cmd = ["ffprobe", "-v", "error", "-show_streams", "-of", "json", video_file]
    try:
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
        data = json.loads(output)
        for s in data.get("streams", []):
            if s.get("codec_type") == "video":
                color_info = {k: s.get(k) for k in ["color_range", "color_primaries", "color_transfer", "color_space"]}
                color_info["mastering_display_metadata"] = None
                color_info["max_cll"] = None
                for side_data in s.get("side_data_list", []):
                    if side_data.get("side_data_type") == "Mastering display metadata":
                        color_info["mastering_display_metadata"] = side_data
                    elif side_data.get("side_data_type") == "Content light level metadata":
                        max_c, max_a = side_data.get("max_content"), side_data.get("max_average")
                        if max_c or max_a: color_info["max_cll"] = f"{max_c},{max_a}"
                return color_info
    except (subprocess.CalledProcessError, json.JSONDecodeError): pass
    return {k: None for k in ["color_range", "color_primaries", "color_transfer", "color_space", "mastering_display_metadata", "max_cll"]}

def run_ffprobe_for_audio_streams(video_file):
    cmd = ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index,codec_name,channels:stream_tags=language", "-of", "json", video_file]
    try:
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
        streams = json.loads(output).get("streams", [])
        for i, s in enumerate(streams, 1): s['track_number'] = i
        return streams
    except (subprocess.CalledProcessError, json.JSONDecodeError): return []

def get_video_resolution(video_file):
    cap = cv2.VideoCapture(video_file)
    if not cap.isOpened(): return None, None
    width, height = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    return height, width

def get_video_duration(video_file):
    cap = cv2.VideoCapture(video_file)
    if not cap.isOpened(): return None
    fps, frame_count = cap.get(cv2.CAP_PROP_FPS), cap.get(cv2.CAP_PROP_FRAME_COUNT)
    cap.release()
    return (frame_count / fps) if fps and frame_count else None

# ---------------------------------------------------------------------
# Step 2: Automatic Crop Detection
# ---------------------------------------------------------------------
def get_crop_parameters(video_file, input_width, input_height, limit_value):
    print("Detecting optimal crop parameters throughout the video...")
    duration = get_video_duration(video_file)
    if not duration or duration < 1:
        print("Video too short for crop detection.")
        return input_width, input_height, 0, 0
    num_samples = max(CROP_DETECT_SAMPLES, min(72, int(duration // CROP_DETECT_INTERVAL_S)))
    start_offset = min(300, duration * 0.05)
    interval = (duration - start_offset) / num_samples
    crop_values = []
    for i in range(num_samples):
        start_time = start_offset + i * interval
        if start_time >= duration: continue
        print(f"Analyzing frame at {int(start_time)}s ({i+1}/{num_samples})...")
        cmd = ["ffmpeg", "-hide_banner", "-ss", str(int(start_time)), "-i", video_file, "-vframes", "3", "-vf", f"cropdetect={limit_value}:2:0", "-f", "null", "-"]
        try:
            proc = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, text=True, encoding='utf-8', errors='replace')
            for line in proc.stderr:
                if 'crop=' in line:
                    crop_str = line.split('crop=')[-1].strip()
                    try:
                        w, h, x, y = [int(v) for v in crop_str.split(':')]
                        print(f"  -> Detected: width={w}, height={h}, x={x}, y={y}")
                        crop_values.append(crop_str)
                    except ValueError:
                        print(f"  -> Could not parse crop string: {crop_str}")
            proc.wait()
        except Exception as e: print(f"Error during cropdetect: {e}")
    if crop_values:
        try:
            w, h, x, y = [int(v) for v in Counter(crop_values).most_common(1)[0][0].split(':')]
            print(f"\nDetected optimal crop parameters: width={w}, height={h}, x={x}, y={y}")
            return w, h, x, y
        except ValueError: pass
    print("No crop parameters found. Using full frame.")
    return input_width, input_height, 0, 0

# ---------------------------------------------------------------------
# Step 3: GUI
# ---------------------------------------------------------------------
def launch_gui(file_list, crop_params, audio_streams, default_qvbr, default_hdr, input_width, input_height):
    root = tk.Tk()
    root.title("NVEncC AV1 Batch Processor")
    
    main_frame = tk.Frame(root)
    main_frame.pack(fill='both', expand=True, padx=10, pady=5)
    canvas = tk.Canvas(main_frame)
    canvas.pack(side='left', fill='both', expand=True)
    scrollbar = tk.Scrollbar(main_frame, orient='vertical', command=canvas.yview)
    scrollbar.pack(side='right', fill='y')
    canvas.configure(yscrollcommand=scrollbar.set)
    inner_frame = tk.Frame(canvas)
    canvas.create_window((0, 0), window=inner_frame, anchor='nw')
    inner_frame.columnconfigure(0, weight=1, minsize=350)
    inner_frame.columnconfigure(1, weight=1, minsize=350)
    
    # --- Tkinter Variables ---
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
    audio_vars, convert_vars = [], []
    crop_w, crop_h, crop_x, crop_y = (tk.StringVar(value=str(v)) for v in crop_params)
    original_crop_w, original_crop_h, original_crop_x, original_crop_y = crop_w.get(), crop_h.get(), crop_x.get(), crop_y.get()
    rate_control_mode = tk.StringVar(value="QVBR")
    cqp_i, cqp_p, cqp_b = (tk.StringVar(value=v) for v in [DEFAULT_CQP_I, DEFAULT_CQP_P, DEFAULT_CQP_B])
    bracket_steps = tk.StringVar(value="2")
    step_size = tk.StringVar(value="3")

    # --- GUI Helper Functions (defined before use) ---
    def update_metadata_display(selected_file):
        if not selected_file:
            meta_text.config(state='normal'); meta_text.delete("1.0", "end"); meta_text.insert("1.0", "No file selected."); meta_text.config(state='disabled')
            return
        meta = get_video_color_info(selected_file)
        txt = (f"File: {os.path.basename(selected_file)}\n"
               f"Color Range: {meta.get('color_range') or 'N/A'}\n"
               f"Color Primaries: {meta.get('color_primaries') or 'N/A'}\n"
               f"Color Transfer: {meta.get('color_transfer') or 'N/A'}\n"
               f"Color Space: {meta.get('color_space') or 'N/A'}\n"
               f"Mastering Display: {bool(meta.get('mastering_display_metadata'))}\n"
               f"Max CLL: {meta.get('max_cll') or 'N/A'}\n")
        meta_text.config(state='normal'); meta_text.delete("1.0", "end"); meta_text.insert("1.0", txt); meta_text.config(state='disabled')

    def on_file_select(event):
        if file_listbox.curselection():
            update_metadata_display(file_listbox.get(file_listbox.curselection()[0]))
    
    # --- Top Frame: File List ---
    file_frame = tk.LabelFrame(inner_frame, text="Input Files")
    file_frame.grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky="nsew")
    file_frame.columnconfigure(0, weight=1)
    file_listbox = tk.Listbox(file_frame, height=6, selectmode='extended')
    file_listbox.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
    for f in file_list: file_listbox.insert('end', f)
    file_controls = tk.Frame(file_frame)
    file_controls.grid(row=0, column=1, padx=5, sticky="ns")
    tk.Button(file_controls, text="Add Files", command=lambda: add_files(file_listbox)).pack(fill='x', pady=2)
    tk.Button(file_controls, text="Clear List", command=lambda: file_listbox.delete(0, 'end')).pack(fill='x', pady=2)
    tk.Button(file_controls, text="Move Up", command=lambda: move_up(file_listbox)).pack(fill='x', pady=2)
    tk.Button(file_controls, text="Move Down", command=lambda: move_down(file_listbox)).pack(fill='x', pady=2)
    tk.Button(file_controls, text="Delete Selected", command=lambda: delete_selected(file_listbox)).pack(fill='x', pady=2)

    # --- Column Frames ---
    left_column = tk.Frame(inner_frame)
    left_column.grid(row=1, column=0, sticky="new", padx=(5,2))
    right_column = tk.Frame(inner_frame)
    right_column.grid(row=1, column=1, sticky="new", padx=(2,5))
    bottom_frame = tk.Frame(inner_frame)
    bottom_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
    bottom_frame.columnconfigure(0, weight=1); bottom_frame.columnconfigure(1, weight=1)

    # --- Left Column Widgets ---
    options_frame = tk.LabelFrame(left_column, text="Video Options")
    options_frame.pack(fill="x", pady=5)
    decode_frame = tk.LabelFrame(options_frame, text="Decoding Mode")
    decode_frame.pack(fill="x", padx=5, pady=5)
    tk.Radiobutton(decode_frame, text="Hardware", variable=decoding_mode, value="Hardware").pack(anchor="w")
    tk.Radiobutton(decode_frame, text="Software", variable=decoding_mode, value="Software").pack(anchor="w")
    proc_frame = tk.Frame(options_frame)
    proc_frame.pack(anchor='w', pady=5, padx=5)
    tk.Label(proc_frame, text="Max Processes:").pack(side='left')
    tk.Entry(proc_frame, textvariable=max_processes, width=3).pack(side='left', padx=5)
    tk.Checkbutton(options_frame, text="Enable HDR Conversion (SDR to HDR)", variable=hdr_enable).pack(anchor='w', padx=5)
    res_frame = tk.Frame(options_frame)
    res_frame.pack(anchor='w', pady=10, padx=5)
    tk.Label(res_frame, text="Output Resolution:").pack(side='left')
    tk.OptionMenu(res_frame, resolution_var, *["No Resize", "HD 1080p", "4K 2160p", "8K 4320p"]).pack(side='left', padx=5)
    tk.Checkbutton(options_frame, text="Enable FRUC (fps=60)", variable=fruc_enable).pack(anchor='w', padx=5)
    denoise_check = tk.Checkbutton(options_frame, text="Enable Denoising (NVVFX - for < 1080p)", variable=nvvfx_denoise_var)
    denoise_check.pack(anchor='w', padx=5)
    if input_height >= 1080: denoise_check.config(state='disabled')
    tk.Checkbutton(options_frame, text="Enable Artifact Reduction (NVVFX)", variable=artifact_enable).pack(anchor='w', padx=5, pady=(0,5))
    
    rc_frame = tk.LabelFrame(left_column, text="Rate Control")
    rc_frame.pack(fill='x', pady=5)
    radio_frame = tk.Frame(rc_frame)
    radio_frame.pack(anchor='w', pady=5, padx=5)
    tk.Radiobutton(radio_frame, text="QVBR", variable=rate_control_mode, value="QVBR").pack(side='left')
    tk.Radiobutton(radio_frame, text="CQP (Film Grain)", variable=rate_control_mode, value="CQP").pack(side='left', padx=10)
    qvbr_frame = tk.Frame(rc_frame)
    tk.Label(qvbr_frame, text="Target QVBR:").pack(side='left')
    tk.Entry(qvbr_frame, textvariable=qvbr, width=5).pack(side='left', padx=5)
    cqp_frame = tk.Frame(rc_frame)
    tk.Label(cqp_frame, text="QP (I):").pack(side='left')
    tk.Entry(cqp_frame, textvariable=cqp_i, width=4).pack(side='left', padx=2)
    tk.Label(cqp_frame, text="QP (P):").pack(side='left', padx=(5,0))
    tk.Entry(cqp_frame, textvariable=cqp_p, width=4).pack(side='left', padx=2)
    tk.Label(cqp_frame, text="QP (B):").pack(side='left', padx=(5,0))
    tk.Entry(cqp_frame, textvariable=cqp_b, width=4).pack(side='left', padx=2)
    gop_frame = tk.Frame(rc_frame)
    tk.Label(gop_frame, text="GOP Length (sec):").pack(side='left')
    tk.Entry(gop_frame, textvariable=gop_len, width=6).pack(side='left', padx=5)
    bracket_frame = tk.Frame(rc_frame)
    tk.Label(bracket_frame, text="Sample Bracketing:").pack(side='left')
    tk.Label(bracket_frame, text="Steps:").pack(side='left', padx=(10, 0))
    tk.Entry(bracket_frame, textvariable=bracket_steps, width=3).pack(side='left')
    tk.Label(bracket_frame, text="Step Size:").pack(side='left', padx=(10, 0))
    tk.Entry(bracket_frame, textvariable=step_size, width=4).pack(side='left')

    # --- Right Column Widgets ---
    meta_frame = tk.LabelFrame(right_column, text="Color Metadata")
    meta_frame.pack(fill="x", pady=5)
    meta_text = tk.Text(meta_frame, height=8, wrap="word", state='disabled', bg="#f0f0f0")
    meta_text.pack(fill="x", expand=True, padx=5, pady=5)
    crop_frame = tk.LabelFrame(right_column, text="Crop Parameters")
    crop_frame.pack(fill="x", pady=5)
    crop_frame.columnconfigure(1, weight=1)
    tk.Label(crop_frame, text="Width:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
    width_entry = tk.Entry(crop_frame, textvariable=crop_w); width_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=2)
    tk.Label(crop_frame, text="Height:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
    height_entry = tk.Entry(crop_frame, textvariable=crop_h); height_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=2)
    tk.Label(crop_frame, text="X Offset:").grid(row=2, column=0, sticky="w", padx=5, pady=2)
    x_entry = tk.Entry(crop_frame, textvariable=crop_x); x_entry.grid(row=2, column=1, sticky="ew", padx=5, pady=2)
    tk.Label(crop_frame, text="Y Offset:").grid(row=3, column=0, sticky="w", padx=5, pady=2)
    y_entry = tk.Entry(crop_frame, textvariable=crop_y); y_entry.grid(row=3, column=1, sticky="ew", padx=5, pady=2)
    tk.Checkbutton(crop_frame, text="No Crop", variable=no_crop_var).grid(row=4, column=0, columnspan=2, pady=5, sticky="w", padx=5)
    audio_frame = tk.LabelFrame(right_column, text="Audio Tracks")
    audio_frame.pack(fill="x", pady=5)
    btn_frame = tk.Frame(audio_frame); btn_frame.pack(fill='x', padx=5, pady=5)
    tk.Button(btn_frame, text="Select All", command=lambda: [v.set(True) for v in audio_vars]).pack(side='left', padx=2)
    tk.Button(btn_frame, text="Clear All", command=lambda: [v.set(False) for v in audio_vars]).pack(side='left', padx=2)
    tk.Button(btn_frame, text="Copy All", command=lambda: [v.set(False) for v in convert_vars]).pack(side='left', padx=2)
    tk.Button(btn_frame, text="Convert All", command=lambda: [v.set(True) for v in convert_vars]).pack(side='left', padx=2)
    if audio_streams:
        for s in audio_streams:
            f = tk.Frame(audio_frame); f.pack(fill='x', padx=5, pady=2)
            lbl = f"Track {s['track_number']}: {s.get('codec_name','N/A')} ({s.get('tags',{}).get('language','N/A')}, {s.get('channels',0)}-ch)"
            var = tk.BooleanVar(value=(s.get('tags',{}).get('language') == 'eng')); audio_vars.append(var)
            tk.Checkbutton(f, text=lbl, variable=var).pack(side='left')
            c_var = tk.BooleanVar(value=(s.get('codec_name') != 'ac3')); convert_vars.append(c_var)
            tk.Checkbutton(f, text="Convert to AC3", variable=c_var).pack(side='right')
    else: tk.Label(audio_frame, text="No audio tracks found.").pack(padx=5, pady=5)

    # --- Bottom Frame and Bindings ---
    tk.Checkbutton(bottom_frame, text="Put Computer to Sleep on Completion", variable=sleep_enable).grid(row=0, column=0, columnspan=2, pady=5, sticky="w")
    tk.Button(bottom_frame, text="Generate Quality Samples", command=lambda: gather_and_run(generate_samples)).grid(row=1, column=0, sticky="ew", padx=(0,2), pady=2)
    tk.Button(bottom_frame, text="Start Processing", command=lambda: gather_and_run(start_processing)).grid(row=1, column=1, sticky="ew", padx=(2,0), pady=2)
    
    file_listbox.bind("<<ListboxSelect>>", on_file_select)
    if file_list: file_listbox.select_set(0); on_file_select(None)

    def on_no_crop_toggle(*args):
        state = 'disabled' if no_crop_var.get() else 'normal'
        if no_crop_var.get(): crop_w.set(input_width); crop_h.set(input_height); crop_x.set("0"); crop_y.set("0")
        else: crop_w.set(original_crop_w); crop_h.set(original_crop_h); crop_x.set(original_crop_x); crop_y.set(original_crop_y)
        for entry in [width_entry, height_entry, x_entry, y_entry]: entry.config(state=state)
    no_crop_var.trace_add("write", on_no_crop_toggle)

    def update_rate_control_ui(*args):
        for w in [cqp_frame, qvbr_frame, gop_frame, bracket_frame]: w.pack_forget()
        if rate_control_mode.get() == "CQP":
            step_size.set("10")
            cqp_frame.pack(anchor='w', pady=(0,5), padx=5)
        else:
            step_size.set("3")
            qvbr_frame.pack(anchor='w', pady=(0,5), padx=5)
        gop_frame.pack(anchor='w', pady=5, padx=5)
        bracket_frame.pack(anchor='w', pady=5, padx=5)
    rate_control_mode.trace_add("write", update_rate_control_ui); update_rate_control_ui()

    _is_updating_cqp = False
    def _update_cqp_ratios(*args, source_var):
        nonlocal _is_updating_cqp
        if _is_updating_cqp: return
        _is_updating_cqp = True
        try:
            r_p, r_b = float(DEFAULT_CQP_P) / float(DEFAULT_CQP_I), float(DEFAULT_CQP_B) / float(DEFAULT_CQP_I)
            if source_var == 'i': base = int(cqp_i.get()); cqp_p.set(round(base * r_p)); cqp_b.set(round(base * r_b))
            elif source_var == 'p': base = round(int(cqp_p.get()) / r_p); cqp_i.set(base); cqp_b.set(round(base * r_b))
            else: base = round(int(cqp_b.get()) / r_b); cqp_i.set(base); cqp_p.set(round(base * r_p))
        except (ValueError, ZeroDivisionError): pass
        finally: _is_updating_cqp = False
    cqp_i.trace_add("write", lambda *a: _update_cqp_ratios(*a, source_var='i'))
    cqp_p.trace_add("write", lambda *a: _update_cqp_ratios(*a, source_var='p'))
    cqp_b.trace_add("write", lambda *a: _update_cqp_ratios(*a, source_var='b'))
    
    def gather_and_run(action_function):
        files = list(file_listbox.get(0, 'end'))
        if not files: print("ERROR: No video files selected."); return
        tracks = [dict(s, convert_to_ac3=convert_vars[i].get()) for i, s in enumerate(audio_streams) if audio_vars[i].get()]
        try:
            w, h, x, y = (int(v.get()) for v in [crop_w, crop_h, crop_x, crop_y])
            w -= w % 2; h -= h % 2; x -= x % 2; y -= y % 2
            if any(v < 0 for v in [w,h,x,y]) or (x+w > input_width) or (y+h > input_height): raise ValueError
        except ValueError: print("ERROR: Invalid crop parameters."); return
        
        settings = {
            "files": files, "decode_mode": decoding_mode.get(), "hdr_enable": hdr_enable.get(),
            "resolution_choice": resolution_var.get(), "fruc_enable": fruc_enable.get(),
            "denoise_enable": nvvfx_denoise_var.get(), "artifact_enable": artifact_enable.get(),
            "rate_control_mode": rate_control_mode.get(), "qvbr": qvbr.get(),
            "cqp_i": cqp_i.get(), "cqp_p": cqp_p.get(), "cqp_b": cqp_b.get(),
            "gop_len": gop_len.get(), "max_processes": max_processes.get(),
            "crop_params": {"crop_w":w, "crop_h":h, "crop_x":x, "crop_y":y},
            "audio_tracks": tracks, "sleep_after_processing": sleep_enable.get(),
            "bracket_steps": bracket_steps.get(), "step_size": step_size.get()
        }
        action_function(settings)
        
    def start_processing(settings):
        root.destroy()
        print("\nSettings collected. Starting processing...")
        process_batch(settings["files"], settings)
        if settings.get("sleep_after_processing"):
            print("Putting the computer to sleep...")
            cmd = {"Windows": "rundll32.exe powrprof.dll,SetSuspendState 0,1,0", "Linux": "systemctl suspend", "Darwin": "pmset sleepnow"}.get(platform.system())
            if cmd: os.system(cmd)
    
    inner_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    def _on_mousewheel(event):
        delta = -1 * (event.delta // 120) if platform.system() == 'Windows' else -1 * event.delta
        canvas.yview_scroll(delta, "units")
    canvas.bind_all("<MouseWheel>", _on_mousewheel)
    root.update_idletasks()
    root.geometry(f"{inner_frame.winfo_reqwidth() + 40}x{min(inner_frame.winfo_reqheight() + 40, int(root.winfo_screenheight() * 0.95))}")
    root.mainloop()

# ---------------------------------------------------------------------
# Step 4: Encoding Logic
# ---------------------------------------------------------------------
def format_bytes(byte_count):
    if byte_count is None or byte_count == 0: return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(byte_count, 1024)))
    p = math.pow(1024, i)
    s = round(byte_count / p, 2)
    return f"{s} {size_name[i]}"

def execute_nvencc(input_file, output_file, settings, is_sample=False):
    h, w = get_video_resolution(input_file)
    if not h:
        print(f"Could not get resolution for {input_file}. Skipping.")
        return False
        
    command = [
        NVENC_EXECUTABLE, "--codec", "av1", "--preset", ENCODER_PRESET, "--output-depth", "10",
        "--gop-len", settings["gop_len"], "--metadata", "copy", "--chapter-copy",
        "--bframes", "4", "--tf-level", "4", "--max-bitrate", "100000",
        "--split-enc", "disable", "--profile", "main", "--aq", "--aq-temporal",
        "--aq-strength", AQ_STRENGTH, "--lookahead", LOOKAHEAD
    ]
    command.append("--avhw" if settings["decode_mode"] == "Hardware" else "--avsw")
    command.extend(["--colormatrix", "bt2020nc", "--colorprim", "bt2020", "--transfer", "smpte2084"])

    if settings["hdr_enable"]: command.append("--vpp-ngx-truehdr")
    else: command.extend(["--dhdr10-info", "copy", "--dolby-vision-profile", "copy", "--dolby-vision-rpu", "copy"])
    
    crop = settings["crop_params"]
    if not is_sample and not (crop["crop_w"] == w and crop["crop_h"] == h):
        right, bottom = w - (crop["crop_x"] + crop["crop_w"]), h - (crop["crop_y"] + crop["crop_h"])
        command.extend(["--crop", f'{crop["crop_x"]},{crop["crop_y"]},{max(0, right)},{max(0, bottom)}'])

    if settings["fruc_enable"]: command.extend(["--vpp-fruc", "fps=60"])
    if settings["denoise_enable"]: command.append("--vpp-nvvfx-denoise")
    if settings["artifact_enable"]: command.append("--vpp-nvvfx-artifact-reduction")
    
    res_map = {"No Resize": None, "HD 1080p": 1080, "4K 2160p": 2160, "8K 4320p": 4320}
    target_h = res_map.get(settings["resolution_choice"])
    if target_h:
        cw, ch = (crop["crop_w"], crop["crop_h"])
        ow, oh = int(cw * (target_h / ch)), target_h; ow -= ow % 2
        algo = "algo=nvvfx-superres,superres-mode=0" if ow > cw or oh > ch else "algo=spline36"
        command.extend(["--vpp-resize", algo, "--output-res", f"{ow}x{oh}"])
    
    if not is_sample:
        copy = [s["track_number"] for s in settings["audio_tracks"] if not s.get("convert_to_ac3")]
        conv = [s["track_number"] for s in settings["audio_tracks"] if s.get("convert_to_ac3")]
        if copy: command.extend(["--audio-copy", ",".join(map(str, copy))])
        for t in conv: command.extend([f"--audio-codec", f"{t}?ac3", f"--audio-bitrate", f"{t}?{AUDIO_CONVERT_BITRATE}"])

    if settings["rate_control_mode"] == "CQP":
        command.extend(["--cqp", f'{settings["cqp_i"]}:{settings["cqp_p"]}:{settings["cqp_b"]}'])
    else:
        command.extend(["--qvbr", settings["qvbr"], "--multipass", "2pass-full"])

    command.extend(["-i", input_file, "-o", output_file])
    
    quoted_cmd = ' '.join(f'"{arg}"' if ' ' in arg else arg for arg in command)
    print(f"\nExecuting NVEncC command:\n{quoted_cmd}")
    
    try:
        proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
        for line in iter(proc.stdout.readline, ''):
            clean_line = line.strip()
            if clean_line.startswith('['):
                # Use carriage return and ANSI escape code to overwrite the line
                print(f'\r{clean_line}\x1b[K', end='', flush=True)
            else:
                print(clean_line)
        
        proc.wait()
        print() # Add a final newline to move past the progress line
        if proc.returncode != 0:
            print(f"Error executing NVEncC. Return code: {proc.returncode}")
            return False
        return True
    except FileNotFoundError:
        print(f"\nERROR: Could not find '{NVENC_EXECUTABLE}'. Is it in your system's PATH?")
        return False
    except Exception as e:
        print(f"\nAn unexpected error occurred while running NVEncC: {e}")
        return False

def generate_samples(settings):
    source_file = settings["files"][0]
    base_name = os.path.splitext(os.path.basename(source_file))[0]
    output_dir = os.path.join(os.path.dirname(source_file), OUTPUT_SUBDIR)
    os.makedirs(output_dir, exist_ok=True)
    duration = get_video_duration(source_file)
    if not duration or duration < 20:
        print("ERROR: Video is too short for a sample."); return

    start_time = max(0, (duration / 2) - 5)
    
    try:
        bracket_steps, step_size = int(settings["bracket_steps"]), int(settings["step_size"])
    except ValueError:
        print("ERROR: Invalid bracket steps or step size. Must be integers."); return
        
    tasks = []
    if settings["rate_control_mode"] == "QVBR":
        try:
            base_qvbr = int(settings["qvbr"])
            for i in range(1, bracket_steps + 1):
                var = i * step_size
                tasks.append({'qvbr': str(base_qvbr - var), 'name': f"QVBR_{base_qvbr - var}"})
                tasks.append({'qvbr': str(base_qvbr + var), 'name': f"QVBR_{base_qvbr + var}"})
        except ValueError: print("ERROR: Invalid base QVBR value."); return
    else: # CQP
        try:
            i, p, b = int(settings["cqp_i"]), int(settings["cqp_p"]), int(settings["cqp_b"])
            r_p, r_b = (p / i) if i else 1.1, (b / i) if i else 1.2
            for j in range(1, bracket_steps + 1):
                var = j * step_size
                ni_l, ni_h = max(0, i - var), i + var
                np_l, nb_l = round(ni_l * r_p), round(ni_l * r_b)
                np_h, nb_h = round(ni_h * r_p), round(ni_h * r_b)
                tasks.append({'cqp_i':str(ni_l), 'cqp_p':str(np_l), 'cqp_b':str(nb_l), 'name':f"CQP_{ni_l}-{np_l}-{nb_l}"})
                tasks.append({'cqp_i':str(ni_h), 'cqp_p':str(np_h), 'cqp_b':str(nb_h), 'name':f"CQP_{ni_h}-{np_h}-{nb_h}"})
        except (ValueError, ZeroDivisionError): print("ERROR: Invalid base CQP values."); return

    print(f"\n--- Generating {len(tasks)} sample clips... ---")
    
    temp_clip = None
    try:
        temp_clip = os.path.join(output_dir, f"temp_clip_{os.getpid()}.mkv")
        
        print(f"Creating temporary 10-second clip...")
        ffmpeg_cmd = ["ffmpeg", "-hide_banner", "-y", "-ss", str(start_time), "-i", source_file, "-t", "10", "-map", "0", "-c", "copy", temp_clip]
        subprocess.run(ffmpeg_cmd, check=True, capture_output=True)
        
        for task in sorted(tasks, key=lambda x: int(x.get('qvbr', x.get('cqp_i')))):
            sample_settings = settings.copy()
            sample_settings.update(task)
            output_file = os.path.join(output_dir, f"{base_name}_Sample_{task['name']}.mp4")
            
            success = execute_nvencc(temp_clip, output_file, sample_settings, is_sample=True)

            if success and os.path.exists(output_file):
                sample_size = os.path.getsize(output_file)
                estimated_size = sample_size * (duration / 10.0)
                formatted_size = format_bytes(estimated_size)
                
                base, ext = os.path.splitext(output_file)
                new_name = f"{base}_~{formatted_size}{ext}"
                os.rename(output_file, new_name)
                print(f"\nSample created successfully: {os.path.basename(new_name)}")
            else:
                print(f"\nFailed to create sample: {os.path.basename(output_file)}")

    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        err_out = e.stderr if isinstance(e, subprocess.CalledProcessError) else str(e)
        print(f"ERROR during sample creation process: {err_out}\nEnsure FFmpeg is installed and accessible in your system's PATH.")
    finally:
        if temp_clip and os.path.exists(temp_clip):
            os.remove(temp_clip)
            print(f"\nCleaned up temporary clip.")
    
    print("\n--- Sample Generation Complete ---")

def process_video(file_path, settings):
    output_dir = os.path.join(os.path.dirname(file_path), OUTPUT_SUBDIR)
    os.makedirs(output_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    output_file = os.path.join(output_dir, f"{base_name}.mp4")
    log_file = os.path.join(output_dir, f"{base_name}_encoding.log")
    
    print(f"\nProcessing: {os.path.basename(file_path)}")
    success = execute_nvencc(file_path, output_file, settings)
    status = "Success" if success else "Error"
    
    print(f"\n{status}: Processed {os.path.basename(file_path)} -> {os.path.basename(output_file)}")
    with open(log_file, "w", encoding='utf-8') as log:
        log.write(f"Status: {status}\n")

def process_wrapper(args):
    process_video(*args)

def process_batch(video_files, settings):
    pool_size = 1
    try: pool_size = int(settings.get("max_processes", "1"))
    except ValueError: pass
        
    tasks = [(vf, settings) for vf in video_files]
    if pool_size > 1:
        print(f"Using multiprocessing with {pool_size} processes...")
        with Pool(pool_size) as p: p.map(process_wrapper, tasks)
    else:
        for task in tasks: process_wrapper(task)

if __name__ == "__main__":
    files = [f for arg in sys.argv[1:] for f in glob.glob(arg)]
    if not files: print("No video files specified."); sys.exit()

    first_file = files[0]
    h, w = get_video_resolution(first_file)
    if h is None: print(f"Error: Could not get resolution for {first_file}. Exiting."); sys.exit()

    color = get_video_color_info(first_file)
    is_hdr = "bt2020" in (color.get("color_primaries","") or "")
    
    crop_w, crop_h, crop_x, crop_y = get_crop_parameters(first_file, w, h, "128" if is_hdr else "24")
    
    qvbr = DEFAULT_QVBR_8K if h >= 4320 else DEFAULT_QVBR_4K if h >= 2160 else DEFAULT_QVBR_1080P

    launch_gui(
        file_list=files,
        crop_params=(crop_w, crop_h, crop_x, crop_y),
        audio_streams=run_ffprobe_for_audio_streams(first_file),
        default_qvbr=qvbr,
        default_hdr=not is_hdr,
        input_width=w,
        input_height=h
    )
    print("\nProcessing Complete.")
    os.system("pause")