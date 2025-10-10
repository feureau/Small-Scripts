"""
====================================================================================================
                            YouTube Batch Video Processing Tool
====================================================================================================

----------------------------------------------------------------------------------------------------
                            PURPOSE AND DESIGN PHILOSOPHY
----------------------------------------------------------------------------------------------------

PURPOSE:
This script provides a Graphical User Interface (GUI) to batch process video files,
optimizing them for upload to YouTube and other social media platforms. It offers full control
over output orientation and aspect ratio handling for both horizontal and vertical formats.
It acts as a front-end for the powerful NVIDIA hardware-accelerated encoder, NVEncC.

DESIGN HISTORY AND TECHNICAL RATIONALE:
This script is the result of an iterative, empirical development process. Many of the
core design decisions were made in direct response to the specific, often non-obvious,
quirks and limitations discovered in the NVEncC encoder and its video processing (VPP)
filter chain. The primary goal of the current design is **stability and predictability**
above all else.

1.  **Aspect Ratio Geometry - The Core Technical Challenge:**
    The most complex part of this script is its handling of aspect ratio conversions.
    The final implementation was chosen after extensive testing revealed the following
    critical constraints of the NVEncC toolchain:
      a. YUV420 Colorspace: Most standard video requires dimensions (for crops, pads,
         and resolutions) to be even numbers. Odd numbers will cause a crash.
      b. Hardware Limits: The NVIDIA encoder has a maximum texture resolution, typically
         4096x4096 pixels. Any intermediate video stream that exceeds this limit will
         cause a hard failure.
      c. Build Dependencies: The available VPP filters and their syntax depend heavily
         on whether NVEncC was compiled with all optional libraries (NPP, libplacebo).
         Minimal builds have a more restricted feature set.

    To solve these challenges, each "Aspect Handling" mode uses a distinct method:
    -   **"Original with Upscale" Mode (v3.5+):**
        -   **Method:** Uses `--output-res` with automatic aspect ratio preservation.
            The encoder maintains the source aspect ratio while resizing to the target
            resolution, applying letterboxing/pillarboxing as needed.
        -   **Rationale:** Provides automatic aspect-ratio-safe upscaling while
            preserving the original composition and leveraging AI enhancement.
    -   **"Crop (Fill)" Mode uses a "Crop then Resize" Method:**
        -   **Method:** Uses `--crop` to trim the source, then `--output-res` to resize.
        -   **Rationale:** Stable and efficient for filling a frame.

    -   **"Pad (Fit)" Mode uses a "Pad then Final Resize" Method (v3.1+):**
        -   **Method:** This method is tailored for minimal NVEncC builds that lack
          `width`/`height` controls in `--vpp-resize`. The script applies `--vpp-pad`
          first and then sets the final, correct dimensions with `--output-res`.
        -   **Rationale & History:** This counter-intuitive "Pad then Resize" order is the
          only one that works reliably on limited NVEncC builds. The encoder engine is
          smart enough to see the final resolution and automatically perform an implicit
          "letterbox" resize *before* applying the explicit `--vpp-pad` filter, resulting
          in the correct output. This implicit resize uses the encoder's internal,
          non-configurable scaler (e.g., Bicubic).

    -   **"Stretch" Mode uses a "Direct Resize" Method:**
        -   **Method:** Uses a single `--output-res` command.
        -   **Rationale:** The simplest approach when aspect ratio is not preserved.

2.  **GUI Layout and User Experience:**
    -   **Rationale (v2.2+):** Redesigned into a two-column format for a more logical
      workflow on modern widescreen monitors.

3.  **Default File Scanning:**
    -   **Rationale (v2.5+):** Upgraded to use `os.walk()` for a "deep scan" of the
      entire directory tree, a more convenient default for a batch tool.

----------------------------------------------------------------------------------------------------
                                        CHANGELOG
----------------------------------------------------------------------------------------------------
v3.5 (2025-10-08) - Gemini/User Collaboration
  - FEATURE: Added "Original" orientation mode. This mode preserves the source video's
    exact aspect ratio while allowing resolution upscaling via AI algorithms.
  - FEATURE: When "Original" mode is active, the bitrate is automatically selected
    based on the target resolution (e.g., 4K target uses 4K bitrate).
  - UI/UX: The "Aspect Handling" GUI controls (Crop/Pad/Stretch) are disabled when
    "Original" orientation is selected, as aspect ratio preservation is automatic.
  - UI/UX: Resolution and Upscale Algo controls remain active in Original mode to 
    enable AI upscaling while maintaining aspect ratio.
  - BEHAVIOR: The encoder automatically preserves the source aspect ratio while 
    applying AI upscaling to the target resolution, using letterboxing/pillarboxing
    as needed.

v3.4 (2025-10-07) - Gemini/User Collaboration
  - REFACTOR: Implemented new settings logic. If no files are selected, changes apply
    globally. If files are selected, changes apply only to the selection.
  - UI/UX: App now starts with no files selected to support the new global settings mode.
  - UI/UX: The "Pad (Fit)" mode no longer forces the upscaler GUI to "Auto".
"""

import os
import subprocess
import shutil
import json
import tkinter as tk
from tkinter import filedialog, messagebox, font
from tkinterdnd2 import TkinterDnD, DND_FILES
import unicodedata
from ftfy import fix_text
import threading
import sys
import math
import argparse

# ----------------------------------------------------------------------------------------------------
#                                     --- USER CONFIGURATION ---
# ----------------------------------------------------------------------------------------------------
LUT_FILE_PATH = r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\LUT\NBCU\5-NBCU_PQ2SDR_DL_RESOLVE17-VRT_v1.2.cube"
DEFAULT_RESOLUTION = "4k"
DEFAULT_UPSCALE_ALGO = "nvvfx-superres"
DEFAULT_OUTPUT_FORMAT = "sdr"
DEFAULT_ORIENTATION = "original"
DEFAULT_ASPECT_MODE = "crop"
DEFAULT_HORIZONTAL_ASPECT = "16:9"
DEFAULT_VERTICAL_ASPECT = "4:5"
DEFAULT_FRUC = False
DEFAULT_FRUC_FPS = "60"
DEFAULT_SUBTITLE_ALIGNMENT = "bottom"
DEFAULT_SUBTITLE_FONT_SIZE = "24"

# --- CUSTOMIZABLE BITRATES (in kbps) ---
BITRATES = {
    "SDR_NORMAL_FPS": { "HD": 16000, "4k": 90000, "8k": 320000 },
    "SDR_HIGH_FPS":   { "HD": 24000, "4k": 136000, "8k": 480000 },
    "HDR_NORMAL_FPS": { "HD": 20000, "4k": 112000, "8k": 400000 },
    "HDR_HIGH_FPS":   { "HD": 30000, "4k": 170000, "8k": 600000 }
}
# ----------------------------------------------------------------------------------------------------

env = os.environ.copy()
env["PYTHONIOENCODING"] = "utf-8"

def get_video_info(file_path):
    cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=pix_fmt,r_frame_rate,height,width,color_transfer,color_primaries", "-of", "json", file_path]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, env=env)
        data = json.loads(result.stdout)["streams"][0]
        pix_fmt = data.get("pix_fmt", "yuv420p")
        bit_depth = 10 if pix_fmt in ["yuv420p10le", "p010le"] else 8
        fr_str = data.get("r_frame_rate", "30/1")
        num, den = map(int, fr_str.split('/'))
        framerate = num / den if den != 0 else 30.0
        height = int(data.get("height", 1080))
        width = int(data.get("width", 1920))
        color_transfer = data.get("color_transfer", "").lower()
        color_primaries = data.get("color_primaries", "").lower()
        is_hdr = color_transfer in ["smpte2084", "arib-std-b67"] or color_primaries == "bt2020"
        return {"bit_depth": bit_depth, "framerate": framerate, "height": height, "width": width, "is_hdr": is_hdr}
    except Exception as e:
        print(f"[WARN] Could not get video info for {file_path}, using defaults: {e}")
        return {"bit_depth": 8, "framerate": 30.0, "height": 1080, "width": 1920, "is_hdr": False}

def get_audio_stream_info(file_path):
    cmd = ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index,channels", "-of", "json", file_path]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, env=env)
        streams = json.loads(result.stdout).get("streams", [])
        return [{"channels": s.get("channels", 2)} for s in streams]
    except Exception as e:
        print(f"[WARN] Could not get detailed audio stream info for {file_path}: {e}")
        return []

def get_bitrate(output_resolution_key, framerate, is_hdr):
    fps_category = "HIGH_FPS" if framerate > 40 else "NORMAL_FPS"
    dr_category = "HDR" if is_hdr else "SDR"
    key = f"{dr_category}_{fps_category}"
    mapped_resolution_key = "HD" if output_resolution_key == "HD" else output_resolution_key.lower()
    return BITRATES.get(key, {}).get(mapped_resolution_key, BITRATES["SDR_NORMAL_FPS"]["HD"])

class VideoProcessorApp:
    def __init__(self, root, initial_files, output_mode):
        self.root = root; self.root.title("Video Processing Tool")
        self.lut_file = LUT_FILE_PATH
        self.output_mode = output_mode
        self.subtitles_by_file = {}; self.file_list = []
        self.subtitle_id_counter = 0; self.current_subtitle_checkbuttons = []
        self.file_options = {}

        self.output_mode_var = tk.StringVar(value=output_mode)
        self.resolution_var = tk.StringVar(value=DEFAULT_RESOLUTION)
        self.upscale_algo_var = tk.StringVar(value=DEFAULT_UPSCALE_ALGO)
        self.output_format_var = tk.StringVar(value=DEFAULT_OUTPUT_FORMAT)
        self.orientation_var = tk.StringVar(value=DEFAULT_ORIENTATION)
        self.aspect_mode_var = tk.StringVar(value=DEFAULT_ASPECT_MODE)
        self.horizontal_aspect_var = tk.StringVar(value=DEFAULT_HORIZONTAL_ASPECT)
        self.vertical_aspect_var = tk.StringVar(value=DEFAULT_VERTICAL_ASPECT)
        self.fruc_var = tk.BooleanVar(value=DEFAULT_FRUC)
        self.fruc_fps_var = tk.StringVar(value=DEFAULT_FRUC_FPS)
        self.alignment_var = tk.StringVar(value=DEFAULT_SUBTITLE_ALIGNMENT)
        self.subtitle_font_size_var = tk.StringVar(value=DEFAULT_SUBTITLE_FONT_SIZE)
        self.generate_log_var = tk.BooleanVar(value=False)
        self.root.drop_target_register(DND_FILES); self.root.dnd_bind("<<Drop>>", self.handle_file_drop)
        
        self.setup_gui()
        self.update_file_list(initial_files)
    
    def setup_gui(self):
        # --- Main Window Structure ---
        self.root.columnconfigure(0, weight=1); self.root.columnconfigure(1, weight=1)
        main_frame = tk.Frame(self.root); main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        left_frame = tk.Frame(main_frame); left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        right_frame = tk.Frame(main_frame); right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))

        # --- LEFT COLUMN: Input Panel ---
        file_group = tk.LabelFrame(left_frame, text="Files", padx=10, pady=10); file_group.pack(fill=tk.BOTH, expand=True)
        listbox_frame = tk.Frame(file_group); listbox_frame.pack(fill=tk.BOTH, expand=True)
        self.file_listbox = tk.Listbox(listbox_frame, selectmode=tk.EXTENDED); self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.file_scrollbar = tk.Scrollbar(listbox_frame, orient=tk.VERTICAL, command=self.file_listbox.yview); self.file_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_listbox.config(yscrollcommand=self.file_scrollbar.set); self.file_listbox.bind("<<ListboxSelect>>", self.on_file_select)
        
        selection_buttons_frame = tk.Frame(file_group); selection_buttons_frame.pack(fill=tk.X, pady=(5, 0))
        tk.Button(selection_buttons_frame, text="Select All", command=self.select_all_files).pack(side=tk.LEFT)
        tk.Button(selection_buttons_frame, text="Clear Selection", command=self.clear_file_selection).pack(side=tk.LEFT, padx=5)

        file_buttons_frame = tk.Frame(file_group); file_buttons_frame.pack(fill=tk.X, pady=(5, 0))
        tk.Button(file_buttons_frame, text="Add Files...", command=self.add_files).pack(side=tk.LEFT, padx=(0,5))
        tk.Button(file_buttons_frame, text="Remove Selected", command=self.remove_selected).pack(side=tk.LEFT, padx=5)
        tk.Button(file_buttons_frame, text="Clear All", command=self.clear_all).pack(side=tk.LEFT, padx=5)

        subtitle_group = tk.LabelFrame(left_frame, text="Burn Subtitle Tracks", padx=10, pady=10); subtitle_group.pack(fill=tk.X, pady=(10, 0))
        self.subtitle_tracks_buttons_frame = tk.Frame(subtitle_group); self.subtitle_tracks_buttons_frame.pack(fill=tk.X, pady=5)
        tk.Button(self.subtitle_tracks_buttons_frame, text="Load Embedded", command=self.load_embedded_srt_all).pack(side=tk.LEFT)
        tk.Button(self.subtitle_tracks_buttons_frame, text="Add External", command=self.add_external_srt).pack(side=tk.LEFT, padx=5)
        tk.Button(self.subtitle_tracks_buttons_frame, text="Remove Selected", command=self.remove_selected_srt).pack(side=tk.LEFT)
        self.subtitle_tracks_list_frame = tk.Frame(subtitle_group); self.subtitle_tracks_list_frame.pack(fill=tk.X, pady=5)

        # --- RIGHT COLUMN: Settings Panel ---
        geometry_group = tk.LabelFrame(right_frame, text="Output & Geometry", padx=10, pady=10); geometry_group.pack(fill=tk.X)
        orientation_frame = tk.Frame(geometry_group); orientation_frame.pack(fill=tk.X)
        tk.Label(orientation_frame, text="Orientation:").pack(side=tk.LEFT, padx=(0,5))
        tk.Radiobutton(orientation_frame, text="Horizontal", variable=self.orientation_var, value="horizontal", command=self._toggle_orientation_options).pack(side=tk.LEFT)
        tk.Radiobutton(orientation_frame, text="Vertical", variable=self.orientation_var, value="vertical", command=self._toggle_orientation_options).pack(side=tk.LEFT)
        tk.Radiobutton(orientation_frame, text="Horizontal + Vertical", variable=self.orientation_var, value="horizontal + vertical", command=self._toggle_orientation_options).pack(side=tk.LEFT)
        tk.Radiobutton(orientation_frame, text="Original", variable=self.orientation_var, value="original", command=self._toggle_orientation_options).pack(side=tk.LEFT)

        self.aspect_ratio_frame = tk.LabelFrame(geometry_group, text="Aspect Ratio", padx=10, pady=5); self.aspect_ratio_frame.pack(fill=tk.X, pady=5)
        self.horizontal_rb_frame = tk.Frame(self.aspect_ratio_frame)
        tk.Radiobutton(self.horizontal_rb_frame, text="16:9 (Widescreen)", variable=self.horizontal_aspect_var, value="16:9", command=self.apply_gui_options_to_selected_files).pack(anchor="w")
        tk.Radiobutton(self.horizontal_rb_frame, text="5:4", variable=self.horizontal_aspect_var, value="5:4", command=self.apply_gui_options_to_selected_files).pack(anchor="w")
        tk.Radiobutton(self.horizontal_rb_frame, text="4:3 (Classic TV)", variable=self.horizontal_aspect_var, value="4:3", command=self.apply_gui_options_to_selected_files).pack(anchor="w")
        self.vertical_rb_frame = tk.Frame(self.aspect_ratio_frame)
        tk.Radiobutton(self.vertical_rb_frame, text="9:16 (Shorts/Reels)", variable=self.vertical_aspect_var, value="9:16", command=self.apply_gui_options_to_selected_files).pack(anchor="w")
        tk.Radiobutton(self.vertical_rb_frame, text="4:5 (Instagram Post)", variable=self.vertical_aspect_var, value="4:5", command=self.apply_gui_options_to_selected_files).pack(anchor="w")
        tk.Radiobutton(self.vertical_rb_frame, text="3:4 (Social Post)", variable=self.vertical_aspect_var, value="3:4", command=self.apply_gui_options_to_selected_files).pack(anchor="w")

        aspect_handling_frame = tk.Frame(geometry_group); aspect_handling_frame.pack(fill=tk.X)
        tk.Label(aspect_handling_frame, text="Handling:").pack(side=tk.LEFT, padx=(0,5))
        self.rb_crop = tk.Radiobutton(aspect_handling_frame, text="Crop (Fill)", variable=self.aspect_mode_var, value="crop", command=self._toggle_upscale_options); self.rb_crop.pack(side=tk.LEFT)
        self.rb_pad = tk.Radiobutton(aspect_handling_frame, text="Pad (Fit)", variable=self.aspect_mode_var, value="pad", command=self._toggle_upscale_options); self.rb_pad.pack(side=tk.LEFT)
        self.rb_stretch = tk.Radiobutton(aspect_handling_frame, text="Stretch", variable=self.aspect_mode_var, value="stretch", command=self._toggle_upscale_options); self.rb_stretch.pack(side=tk.LEFT)

        quality_group = tk.LabelFrame(right_frame, text="Format & Quality", padx=10, pady=10); quality_group.pack(fill=tk.X, pady=10)
        resolution_options_frame = tk.Frame(quality_group); resolution_options_frame.pack(fill=tk.X)
        tk.Label(resolution_options_frame, text="Resolution:").pack(side=tk.LEFT, padx=(0,5))
        self.rb_hd = tk.Radiobutton(resolution_options_frame, text="HD", variable=self.resolution_var, value="HD", command=self.apply_gui_options_to_selected_files); self.rb_hd.pack(side=tk.LEFT)
        self.rb_4k = tk.Radiobutton(resolution_options_frame, text="4k", variable=self.resolution_var, value="4k", command=self.apply_gui_options_to_selected_files); self.rb_4k.pack(side=tk.LEFT)
        self.rb_8k = tk.Radiobutton(resolution_options_frame, text="8k", variable=self.resolution_var, value="8k", command=self.apply_gui_options_to_selected_files); self.rb_8k.pack(side=tk.LEFT)
        upscale_frame = tk.Frame(quality_group); upscale_frame.pack(fill=tk.X, pady=(5,0))
        tk.Label(upscale_frame, text="Upscale Algo:").pack(side=tk.LEFT, padx=(0,5))
        self.rb_superres = tk.Radiobutton(upscale_frame, text="SuperRes (AI)", variable=self.upscale_algo_var, value="nvvfx-superres", command=self.apply_gui_options_to_selected_files); self.rb_superres.pack(side=tk.LEFT)
        self.rb_vsr = tk.Radiobutton(upscale_frame, text="VSR (AI)", variable=self.upscale_algo_var, value="ngx-vsr", command=self.apply_gui_options_to_selected_files); self.rb_vsr.pack(side=tk.LEFT)
        self.rb_auto = tk.Radiobutton(upscale_frame, text="Auto (Default)", variable=self.upscale_algo_var, value="auto", command=self.apply_gui_options_to_selected_files); self.rb_auto.pack(side=tk.LEFT)
        output_format_frame = tk.Frame(quality_group); output_format_frame.pack(fill=tk.X, pady=(5,0))
        tk.Label(output_format_frame, text="Output Format:").pack(side=tk.LEFT, padx=(0,5))
        tk.Radiobutton(output_format_frame, text="SDR", variable=self.output_format_var, value="sdr", command=self.apply_gui_options_to_selected_files).pack(side=tk.LEFT)
        tk.Radiobutton(output_format_frame, text="HDR", variable=self.output_format_var, value="hdr", command=self.apply_gui_options_to_selected_files).pack(side=tk.LEFT)
        tk.Label(output_format_frame, text="Location:").pack(side=tk.LEFT, padx=(15,5))
        tk.Radiobutton(output_format_frame, text="Local", variable=self.output_mode_var, value="local").pack(side=tk.LEFT)
        tk.Radiobutton(output_format_frame, text="Pooled", variable=self.output_mode_var, value="pooled").pack(side=tk.LEFT)

        other_opts_group = tk.LabelFrame(right_frame, text="Other Options", padx=10, pady=10); other_opts_group.pack(fill=tk.X)
        sub_opts_frame = tk.Frame(other_opts_group); sub_opts_frame.pack(fill=tk.X)
        tk.Label(sub_opts_frame, text="Subtitle Align:").pack(side=tk.LEFT)
        tk.Radiobutton(sub_opts_frame, text="Top", variable=self.alignment_var, value="top", command=self.apply_gui_options_to_selected_files).pack(side=tk.LEFT)
        tk.Radiobutton(sub_opts_frame, text="Middle", variable=self.alignment_var, value="middle", command=self.apply_gui_options_to_selected_files).pack(side=tk.LEFT)
        tk.Radiobutton(sub_opts_frame, text="Bottom", variable=self.alignment_var, value="bottom", command=self.apply_gui_options_to_selected_files).pack(side=tk.LEFT)
        tk.Label(sub_opts_frame, text="Font Size:").pack(side=tk.LEFT, padx=(10,5))
        self.subtitle_font_size_entry = tk.Entry(sub_opts_frame, textvariable=self.subtitle_font_size_var, width=5); self.subtitle_font_size_entry.pack(side=tk.LEFT)
        self.subtitle_font_size_entry.bind("<FocusOut>", self.apply_gui_options_to_selected_files_event)
        fruc_frame = tk.Frame(other_opts_group); fruc_frame.pack(fill=tk.X, pady=(5,0))
        tk.Checkbutton(fruc_frame, text="Enable FRUC", variable=self.fruc_var, command=lambda: [self.toggle_fruc_fps(), self.apply_gui_options_to_selected_files()]).pack(side=tk.LEFT)
        tk.Label(fruc_frame, text="FRUC FPS:").pack(side=tk.LEFT, padx=(5,5))
        self.fruc_fps_entry = tk.Entry(fruc_frame, textvariable=self.fruc_fps_var, width=5, state="disabled"); self.fruc_fps_entry.pack(side=tk.LEFT)
        self.fruc_fps_entry.bind("<FocusOut>", self.apply_gui_options_to_selected_files_event)

        # --- BOTTOM BAR ---
        bottom_frame = tk.Frame(self.root); bottom_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        self.start_button = tk.Button(bottom_frame, text="Start Processing", command=self.start_processing, bg="#4CAF50", fg="white", font=font.Font(weight="bold")); self.start_button.pack(side=tk.LEFT, padx=5, ipady=5)
        self.generate_log_checkbox = tk.Checkbutton(bottom_frame, text="Generate Log File", variable=self.generate_log_var, command=self.apply_gui_options_to_selected_files); self.generate_log_checkbox.pack(side=tk.LEFT, padx=(10, 0))
        self._toggle_orientation_options(); self._toggle_upscale_options()

    def _toggle_orientation_options(self):
        orientation = self.orientation_var.get()
        self.horizontal_rb_frame.pack_forget()
        self.vertical_rb_frame.pack_forget()

        # Define lists of widgets to manage
        resolution_widgets = [self.rb_hd, self.rb_4k, self.rb_8k]
        upscale_widgets = [self.rb_superres, self.rb_vsr, self.rb_auto]
        aspect_handling_widgets = [self.rb_crop, self.rb_pad, self.rb_stretch]

        # Default state: enable all controls
        for widget_list in [resolution_widgets, upscale_widgets, aspect_handling_widgets]:
            for widget in widget_list:
                widget.config(state="normal")
        
        if orientation == "horizontal":
            self.aspect_ratio_frame.config(text="Horizontal Aspect Ratio")
            self.horizontal_rb_frame.pack(fill="x")
        elif orientation == "vertical":
            self.aspect_ratio_frame.config(text="Vertical Aspect Ratio")
            self.vertical_rb_frame.pack(fill="x")
        elif orientation == "horizontal + vertical":
            self.aspect_ratio_frame.config(text="Aspect Ratios (H & V)")
            self.horizontal_rb_frame.pack(fill="x", pady=(0, 5))
            self.vertical_rb_frame.pack(fill="x")
        elif orientation == "original":
            self.aspect_ratio_frame.config(text="Aspect Ratio (Original – unchanged)")
            # For "Original" mode, only disable aspect handling controls
            for widget in aspect_handling_widgets:
                widget.config(state="disabled")
            # Keep resolution and upscale controls enabled
            for widget in resolution_widgets:
                widget.config(state="normal")
            for widget in upscale_widgets:
                widget.config(state="normal")





        self.apply_gui_options_to_selected_files()

    def _toggle_upscale_options(self):
        self.apply_gui_options_to_selected_files()

    def apply_gui_options_to_selected_files(self, event=None):
        selected_indices = self.file_listbox.curselection()
        options_state = {
            "resolution": self.resolution_var.get(), "upscale_algo": self.upscale_algo_var.get(),
            "output_format": self.output_format_var.get(), "fruc": self.fruc_var.get(),
            "fruc_fps": self.fruc_fps_var.get(), "alignment": self.alignment_var.get(),
            "subtitle_font_size": self.subtitle_font_size_var.get(), "generate_log": self.generate_log_var.get(),
            "orientation": self.orientation_var.get(), "aspect_mode": self.aspect_mode_var.get(),
            "horizontal_aspect": self.horizontal_aspect_var.get(),
            "vertical_aspect": self.vertical_aspect_var.get()
        }
        target_indices = selected_indices if selected_indices else range(len(self.file_list))
        for index in target_indices:
            self.file_options[self.file_list[index]] = options_state

    def update_file_list(self, files):
        for file_path in files:
            if file_path not in self.file_list:
                self.file_list.append(file_path); self.file_listbox.insert(tk.END, os.path.basename(file_path)); self.subtitles_by_file[file_path] = []
                self.detect_subtitle_tracks(file_path)
                self.file_options[file_path] = { "resolution": self.resolution_var.get(), "upscale_algo": self.upscale_algo_var.get(), "output_format": self.output_format_var.get(), "fruc": self.fruc_var.get(), "fruc_fps": self.fruc_fps_var.get(), "alignment": self.alignment_var.get(), "subtitle_font_size": self.subtitle_font_size_var.get(), "generate_log": self.generate_log_var.get(), "orientation": self.orientation_var.get(), "aspect_mode": self.aspect_mode_var.get(), "horizontal_aspect": self.horizontal_aspect_var.get(), "vertical_aspect": self.vertical_aspect_var.get() }

    def on_file_select(self, event):
        sel = self.file_listbox.curselection()
        if sel:
            selected_file = self.file_list[sel[0]]
            if selected_file in self.file_options:
                options = self.file_options[selected_file]
                self.resolution_var.set(options.get("resolution", DEFAULT_RESOLUTION)); self.upscale_algo_var.set(options.get("upscale_algo", DEFAULT_UPSCALE_ALGO)); self.output_format_var.set(options.get("output_format", DEFAULT_OUTPUT_FORMAT)); self.orientation_var.set(options.get("orientation", DEFAULT_ORIENTATION)); self.aspect_mode_var.set(options.get("aspect_mode", DEFAULT_ASPECT_MODE)); self.horizontal_aspect_var.set(options.get("horizontal_aspect", DEFAULT_HORIZONTAL_ASPECT)); self.vertical_aspect_var.set(options.get("vertical_aspect", DEFAULT_VERTICAL_ASPECT)); self.alignment_var.set(options.get("alignment", DEFAULT_SUBTITLE_ALIGNMENT)); self.subtitle_font_size_var.set(options.get("subtitle_font_size", DEFAULT_SUBTITLE_FONT_SIZE)); self.fruc_var.set(options.get("fruc", DEFAULT_FRUC)); self.fruc_fps_var.set(options.get("fruc_fps", DEFAULT_FRUC_FPS)); self.generate_log_var.set(options.get("generate_log", False))
                self.toggle_fruc_fps(); self._toggle_orientation_options(); self._toggle_upscale_options()
        self.refresh_subtitle_list()

    def build_nvenc_command_and_run(self, file_path, orientation, ass_burn=None):
        options = self.file_options.get(file_path, {})
        resolution_mode = options.get("resolution", DEFAULT_RESOLUTION)
        output_format = options.get("output_format", DEFAULT_OUTPUT_FORMAT)
        folder_name = f"{resolution_mode}_{output_format.upper()}"
        if orientation == "vertical": folder_name += f"_Vertical_{options.get('vertical_aspect').replace(':', 'x')}"
        elif orientation == "original": folder_name += "_Original"
        else:
            horizontal_aspect = options.get('horizontal_aspect').replace(':', 'x')
            if horizontal_aspect != "16x9": folder_name += f"_Horizontal_{horizontal_aspect}"
        base_dir = os.path.dirname(file_path) if self.output_mode == 'local' else os.getcwd()
        output_dir = os.path.join(base_dir, folder_name); os.makedirs(output_dir, exist_ok=True)
        base_name, _ = os.path.splitext(os.path.basename(file_path))
        output_file = os.path.join(output_dir, f"{base_name}_temp.mp4")
        cmd = self.construct_nvencc_command(file_path, output_file, orientation, ass_burn, options)
        ret = self.run_nvenc_command(cmd)
        if ret == 0:
            final_name = output_file.replace("_temp.mp4", ".mp4")
            try:
                if os.path.exists(final_name): os.remove(final_name)
                os.rename(output_file, final_name); print(f"File finalized => {final_name}"); self.verify_output_file(final_name)
            except Exception as e: print(f"[ERROR] Could not rename temp file {output_file}: {e}")
        else: print(f"[ERROR] Error encoding {file_path}: return code {ret}")

    def construct_nvencc_command(self, file_path, output_file, orientation, ass_burn, options):
        info = get_video_info(file_path); cmd = ["NVEncC64", "--avhw", "--preset", "p1", "--log-level", "info"]
        
        if orientation != "original":
            aspect_mode = options.get("aspect_mode"); resolution_key = options.get('resolution'); upscale_algo = options.get("upscale_algo")
            if orientation == "vertical":
                aspect_str = options.get('vertical_aspect'); width_map = {"HD": 1080, "4k": 2160, "8k": 4320}
                target_width = width_map.get(resolution_key, 1080)
                try: num, den = map(int, aspect_str.split(':')); target_height = int(target_width * den / num)
                except: target_height = int(target_width * 16 / 9)
            else:
                aspect_str = options.get('horizontal_aspect'); width_map = {"HD": 1920, "4k": 3840, "8k": 7680}
                target_width = width_map.get(resolution_key, 1920)
                try: num, den = map(int, aspect_str.split(':')); target_height = int(target_width * den / num)
                except: target_height = int(target_width * 9 / 16)
            target_width = (target_width // 2) * 2; target_height = (target_height // 2) * 2
            if aspect_mode == 'pad':
                if info['height'] > 0 and info['width'] > 0:
                    source_aspect = info['width'] / info['height']; target_aspect = target_width / target_height
                    if source_aspect > target_aspect: resized_w = target_width; resized_h = int(target_width / source_aspect)
                    else: resized_h = target_height; resized_w = int(target_height * source_aspect)
                    sanitized_w = resized_w - (resized_w % 2); sanitized_h = resized_h - (resized_h % 2)
                    total_pad_w = target_width - sanitized_w; total_pad_h = target_height - sanitized_h
                    pad_l = (total_pad_w // 2) - ((total_pad_w // 2) % 2); pad_r = total_pad_w - pad_l
                    pad_t = (total_pad_h // 2) - ((total_pad_h // 2) % 2); pad_b = total_pad_h - pad_t
                    if pad_l > 0 or pad_t > 0 or pad_r > 0 or pad_b > 0: cmd.extend(["--vpp-pad", f"{pad_l},{pad_t},{pad_r},{pad_b}"])
                cmd.extend(["--output-res", f"{target_width}x{target_height}"])
            else:
                cmd.extend(["--output-res", f"{target_width}x{target_height}"])
                if aspect_mode == 'crop':
                    if info['height'] > 0 and info['width'] > 0:
                        source_aspect = info['width'] / info['height']; target_aspect = target_width / target_height; crop_str = "0,0,0,0"
                        if source_aspect > target_aspect:
                            new_width_in_source = int(info['height'] * target_aspect); crop_val = (info['width'] - new_width_in_source) // 2
                            if (crop_val := crop_val - crop_val % 2) > 0: crop_str = f"{crop_val},0,{crop_val},0"
                        elif source_aspect < target_aspect:
                            new_height_in_source = int(info['width'] / target_aspect); crop_val = (info['height'] - new_height_in_source) // 2
                            if (crop_val := crop_val - crop_val % 2) > 0: crop_str = f"0,{crop_val},0,{crop_val}"
                        if crop_str != "0,0,0,0": cmd.extend(["--crop", crop_str])
                resize_params = f"algo={upscale_algo}";
                if upscale_algo == "ngx-vsr": resize_params += ",vsr-quality=1"
                cmd.extend(["--vpp-resize", resize_params])

        # --- Standard Encoder Settings ---
        output_format = options.get("output_format"); is_hdr_output = output_format == 'hdr'
        
        if orientation == "original":
            if info["height"] <= 1080: bitrate_res_key = "HD"
            elif info["height"] <= 2160: bitrate_res_key = "4k"
            else: bitrate_res_key = "8k"
        else:
            resolution_key = options.get('resolution', DEFAULT_RESOLUTION)
            bitrate_res_key = "HD" if resolution_key == "HD" else resolution_key.lower()

        bitrate_kbps = get_bitrate(bitrate_res_key, info["framerate"], is_hdr_output)
        gop_len = 0 if info["framerate"] == 0 else math.ceil(info["framerate"] / 2)
        cmd.extend(["--vbr", str(bitrate_kbps), "--gop-len", str(gop_len)])
        audio_streams = get_audio_stream_info(file_path)
        if len(audio_streams) > 0:
            cmd.extend(["--audio-codec", "copy"])
        if is_hdr_output: cmd.extend(["--codec", "hevc", "--profile", "main10", "--output-depth", "10", "--colorprim", "bt2020", "--transfer", "smpte2084", "--colormatrix", "bt2020nc", "--dhdr10-info", "pass"])
        else:
            cmd.extend(["--codec", "h264", "--profile", "high", "--output-depth", "8", "--bframes", "2", "--colorprim", "bt709", "--transfer", "bt709", "--colormatrix", "bt709"])
            if info["is_hdr"] and os.path.exists(self.lut_file): cmd.extend(["--vpp-colorspace", f"lut3d={self.lut_file},lut3d_interp=trilinear"])
        cmd.extend(["--vpp-deinterlace", "adaptive"])
        if options.get("fruc"): cmd.extend(["--vpp-fruc", f"fps={options.get('fruc_fps')}"])
        if options.get("generate_log"): cmd.extend(["--log", "log.log", "--log-level", "debug"])
        if ass_burn: cmd.extend(["--vpp-subburn", f"filename={ass_burn},charcode=utf-8"])
        cmd.extend(["--output", output_file, "-i", file_path])
        return cmd

    def start_processing(self):
        if not self.file_list: messagebox.showwarning("No Files", "Please add at least one file to process."); return
        self.output_mode = self.output_mode_var.get()
        print("\n" + "="*80 + "\n--- Starting processing batch ---")
        self.root.destroy()
        for file_path in self.file_list:
            options = self.file_options.get(file_path, {})
            orientation_mode = options.get("orientation", "horizontal")
            base_name = os.path.basename(file_path)
            print("-" * 80)
            print(f"Processing: {base_name} (Mode: {orientation_mode})")
            if orientation_mode == "horizontal + vertical":
                print(f"\n--- Processing HORIZONTAL for: {base_name} ---")
                self.build_nvenc_command_and_run(file_path, "horizontal")
                print(f"\n--- Processing VERTICAL for: {base_name} ---")
                self.build_nvenc_command_and_run(file_path, "vertical")
            else:
                self.build_nvenc_command_and_run(file_path, orientation_mode)
        print("\n================== Processing Complete. ==================")

    def run_nvenc_command(self, cmd):
        print("Running NVEnc command:\n" + " ".join(f'"{c}"' if " " in c else c for c in cmd))
        process = subprocess.Popen(cmd,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env, text=True,encoding='utf-8',errors='replace',bufsize=1)
        while True:
            line = process.stdout.readline();
            if not line and process.poll() is not None: break
            if line:
                if "\r" in line: progress = line.split("\r")[-1].strip(); sys.stdout.write("\r" + progress); sys.stdout.flush()
                else: sys.stdout.write(line); sys.stdout.flush()
        process.stdout.close(); ret = process.wait(); print("\nNVEnc conversion finished."); return ret

    def verify_output_file(self, file_path):
        print("-" * 80 + f"\n--- Verifying output file: {os.path.basename(file_path)} ---")
        try:
            cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,display_aspect_ratio", "-of", "default=noprint_wrappers=1:nokey=1", file_path]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, env=env)
            output = result.stdout.strip().split('\n')
            if len(output) >= 3: print(f"[VERIFIED] Output Specs: {output[0]}x{output[1]} (Aspect Ratio: {output[2]})")
            else: print(f"[WARN] Could not parse ffprobe output for verification: {output}")
        except FileNotFoundError: print("[WARN] ffprobe not found. Cannot verify output.")
        except subprocess.CalledProcessError as e: print(f"[ERROR] ffprobe failed to verify the file. It may be corrupt. Error: {e.stderr}")
        except Exception as e: print(f"[ERROR] An unexpected error occurred during verification: {e}")
        finally: print("-" * 80)
    
    def apply_gui_options_to_selected_files_event(self, event): self.apply_gui_options_to_selected_files()
    def load_embedded_srt_all(self): pass
    def add_files(self):
        files = filedialog.askopenfilenames(title="Select Video Files", filetypes=[("Video Files", "*.mp4;*.mkv;*.avi;*.mov;*.webm;*.flv;*.wmv"), ("All Files", "*.*")])
        self.update_file_list(files)
    def handle_file_drop(self, event):
        files = self.root.tk.splitlist(event.data); self.update_file_list(files)
    def remove_selected(self):
        selected_indices = list(self.file_listbox.curselection())
        for index in reversed(selected_indices):
            file_to_remove = self.file_list[index]
            del self.subtitles_by_file[file_to_remove], self.file_options[file_to_remove], self.file_list[index]
            self.file_listbox.delete(index)
        self.refresh_subtitle_list()
    def clear_all(self):
        self.file_list.clear(); self.file_listbox.delete(0, tk.END); self.subtitles_by_file.clear(); self.file_options.clear(); self.refresh_subtitle_list()
    def select_all_files(self):
        self.file_listbox.select_set(0, tk.END); self.on_file_select(None)
    def clear_file_selection(self):
        self.file_listbox.select_clear(0, tk.END); self.on_file_select(None)
    def detect_subtitle_tracks(self, file_path): pass
    def add_external_srt(self): pass
    def remove_selected_srt(self): pass
    def refresh_subtitle_list(self): pass
    def on_subtitle_check(self, sub, var): pass
    def toggle_fruc_fps(self): self.fruc_fps_entry.config(state="normal" if self.fruc_var.get() else "disabled")
    def extract_embedded_subtitle_to_ass(self, input_file, output_ass, sub_track_id, final_width, final_height): pass
    def extract_subtitle_to_srt(self, input_file, output_srt, sub_track_id=None): pass

if __name__ == "__main__":
    import glob
    from tkinterdnd2 import TkinterDnD
    parser = argparse.ArgumentParser(description="YouTube Batch Video Processing Tool", formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-o', '--output-mode', dest='output_mode', choices=['local', 'pooled'], default='local', help="Set the initial output directory mode. 'local' (default) or 'pooled'.")
    parser.add_argument('input_files', nargs='*', help="Optional: Paths to video files or glob patterns (e.g., 'C:\\Videos\\*.mp4').")
    args = parser.parse_args()
    root = TkinterDnD.Tk()
    initial_files = []
    if args.input_files:
        for pattern in args.input_files: initial_files.extend(glob.glob(pattern))
    else:
        current_dir = os.getcwd()
        video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv', '.wmv']
        print(f"No input files provided. Performing a deep scan of current directory: {current_dir}...")
        files_found = []
        for root_dir, dirs, files in os.walk(current_dir):
            for filename in files:
                if os.path.splitext(filename)[1].lower() in video_extensions:
                    files_found.append(os.path.join(root_dir, filename))
        initial_files.extend(sorted(files_found))
    app = VideoProcessorApp(root, sorted(list(set(initial_files))), args.output_mode)
    root.mainloop()