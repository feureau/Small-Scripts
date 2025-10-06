"""
====================================================================================================
                            YouTube Batch Video Processing Tool
====================================================================================================

----------------------------------------------------------------------------------------------------
                        DEVELOPER'S PLEDGE AND CHANGELOG
----------------------------------------------------------------------------------------------------
This script's documentation is considered an integral part of the codebase. It is a
living document that must be maintained with the same care as the code itself.

Before committing any changes to this script, you must complete the following checklist:

[ ] 1. Have you tested the functional code changes and confirmed they work as expected?
[ ] 2. Have you located the section(s) in the documentation that describe the feature you modified?
[ ] 3. Have you updated those sections to reflect the new logic, parameters, or behavior?
[ ] 4. Have you explained not just *what* changed, but *why* the change was necessary?
[ ] 5. Have you added an entry to the changelog below?

Failure to update this documentation with every code change is a failure of the change itself.

--- CHANGELOG ---

v2.2 (2025-10-06) - Gemini/User Collaboration
  - REFACTOR: The GUI has been completely redesigned into a two-column horizontal layout.
  - REASON: The previous single-column layout was becoming too tall for standard monitor
    resolutions as more features were added.
  - UI/UX: The new layout splits the interface into a left "Input Panel" (for files and
    subtitles) and a right "Settings Panel". Settings on the right are further grouped
    into logical sections ("Output & Geometry", "Format & Quality", "Other Options").
  - BENEFIT: This new design significantly reduces the window's height, improves the
    logical workflow, and makes better use of horizontal screen space.

v2.1 (2025-10-06) - Gemini/User Collaboration
  - FIX: "Pad (Fit)" mode was fundamentally broken and behaved identically to "Crop (Fill)".
  - REASON: The v2.0 refactor mistakenly routed both "pad" and "crop" modes through the same
    "crop then resize" logic, eliminating the padding feature entirely.
  - FIX: Re-implemented a distinct and robust logic path for "Pad (Fit)" mode. The script
    now uses a "Pad then Resize" method. It first calculates the necessary padding to
    change the source's aspect ratio to match the target, adding black bars with `--vpp-pad`.
    It then resizes the entire padded result to the final dimensions with `--output-res`.
  - FIX: All padding calculations are sanitized to be even numbers, ensuring compatibility
    and preventing YUV420 errors. "Pad (Fit)" mode now correctly produces letterboxed or
    pillarboxed videos as intended.

v2.0 (2025-10-06) - Gemini/User Collaboration
  - REFACTORED: The core geometry logic has been completely rewritten.
  - REASON: Extensive testing proved that the "resize then pad" method is fundamentally
    incompatible with NVEncC's filter chain.
  - FIX: "Crop (Fill)" mode uses the robust "crop then resize" backend.
  - FIX: The definition of vertical resolution is now definitively locked to be based on
    WIDTH (e.g., a "4K Vertical" video has a width of 2160 pixels).
  - FIX: All mathematical calculations for geometry now enforce that values are even
    numbers, preventing all `YUV420` related errors.
  - DOCS: All documentation has been updated to reflect this final, unified, and correct logic.

v1.0 (Initial Release)
  - Initial creation of the batch processing tool.
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
DEFAULT_ORIENTATION = "horizontal"
DEFAULT_ASPECT_MODE = "crop" # Universal aspect mode
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
        if self.file_listbox.size() > 0: self.file_listbox.select_set(0); self.on_file_select(None)
    
    def setup_gui(self):
        # --- Main Window Structure ---
        self.root.columnconfigure(0, weight=1)
        self.root.columnconfigure(1, weight=1)
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        left_frame = tk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        right_frame = tk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))

        # --- LEFT COLUMN: Input Panel ---

        # 1. Files Group
        file_group = tk.LabelFrame(left_frame, text="Files", padx=10, pady=10)
        file_group.pack(fill=tk.BOTH, expand=True)

        listbox_frame = tk.Frame(file_group)
        listbox_frame.pack(fill=tk.BOTH, expand=True)
        self.file_listbox = tk.Listbox(listbox_frame, selectmode=tk.EXTENDED)
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.file_scrollbar = tk.Scrollbar(listbox_frame, orient=tk.VERTICAL, command=self.file_listbox.yview)
        self.file_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_listbox.config(yscrollcommand=self.file_scrollbar.set)
        self.file_listbox.bind("<<ListboxSelect>>", self.on_file_select)
        
        file_buttons_frame = tk.Frame(file_group)
        file_buttons_frame.pack(fill=tk.X, pady=(5, 0))
        tk.Button(file_buttons_frame, text="Add Files...", command=self.add_files).pack(side=tk.LEFT, padx=(0,5))
        tk.Button(file_buttons_frame, text="Remove Selected", command=self.remove_selected).pack(side=tk.LEFT, padx=5)
        tk.Button(file_buttons_frame, text="Clear All", command=self.clear_all).pack(side=tk.LEFT, padx=5)

        # 2. Subtitles Group
        subtitle_group = tk.LabelFrame(left_frame, text="Burn Subtitle Tracks", padx=10, pady=10)
        subtitle_group.pack(fill=tk.X, pady=(10, 0))
        self.subtitle_tracks_buttons_frame = tk.Frame(subtitle_group)
        self.subtitle_tracks_buttons_frame.pack(fill=tk.X, pady=5)
        tk.Button(self.subtitle_tracks_buttons_frame, text="Load Embedded", command=self.load_embedded_srt_all).pack(side=tk.LEFT)
        tk.Button(self.subtitle_tracks_buttons_frame, text="Add External", command=self.add_external_srt).pack(side=tk.LEFT, padx=5)
        tk.Button(self.subtitle_tracks_buttons_frame, text="Remove Selected", command=self.remove_selected_srt).pack(side=tk.LEFT)
        self.subtitle_tracks_list_frame = tk.Frame(subtitle_group)
        self.subtitle_tracks_list_frame.pack(fill=tk.X, pady=5)

        # --- RIGHT COLUMN: Settings Panel ---
        
        # 1. Geometry Group
        geometry_group = tk.LabelFrame(right_frame, text="Output & Geometry", padx=10, pady=10)
        geometry_group.pack(fill=tk.X)
        
        orientation_frame = tk.Frame(geometry_group)
        orientation_frame.pack(fill=tk.X)
        tk.Label(orientation_frame, text="Orientation:").pack(side=tk.LEFT, padx=(0,5))
        tk.Radiobutton(orientation_frame, text="H", variable=self.orientation_var, value="horizontal", command=self._toggle_orientation_options).pack(side=tk.LEFT)
        tk.Radiobutton(orientation_frame, text="V", variable=self.orientation_var, value="vertical", command=self._toggle_orientation_options).pack(side=tk.LEFT)
        tk.Radiobutton(orientation_frame, text="H+V", variable=self.orientation_var, value="horizontal + vertical", command=self._toggle_orientation_options).pack(side=tk.LEFT)

        aspect_ratio_container = tk.Frame(geometry_group)
        aspect_ratio_container.pack(fill=tk.X, pady=5)
        aspect_ratio_container.columnconfigure(0, weight=1)
        aspect_ratio_container.columnconfigure(1, weight=1)

        self.horizontal_aspect_frame = tk.LabelFrame(aspect_ratio_container, text="Horizontal Aspect", padx=10, pady=5)
        self.horizontal_aspect_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        tk.Radiobutton(self.horizontal_aspect_frame, text="16:9", variable=self.horizontal_aspect_var, value="16:9", command=self.apply_gui_options_to_selected_files).pack(anchor="w")
        tk.Radiobutton(self.horizontal_aspect_frame, text="5:4", variable=self.horizontal_aspect_var, value="5:4", command=self.apply_gui_options_to_selected_files).pack(anchor="w")
        tk.Radiobutton(self.horizontal_aspect_frame, text="4:3", variable=self.horizontal_aspect_var, value="4:3", command=self.apply_gui_options_to_selected_files).pack(anchor="w")

        self.vertical_aspect_frame = tk.LabelFrame(aspect_ratio_container, text="Vertical Aspect", padx=10, pady=5)
        self.vertical_aspect_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        tk.Radiobutton(self.vertical_aspect_frame, text="9:16", variable=self.vertical_aspect_var, value="9:16", command=self.apply_gui_options_to_selected_files).pack(anchor="w")
        tk.Radiobutton(self.vertical_aspect_frame, text="4:5", variable=self.vertical_aspect_var, value="4:5", command=self.apply_gui_options_to_selected_files).pack(anchor="w")
        tk.Radiobutton(self.vertical_aspect_frame, text="3:4", variable=self.vertical_aspect_var, value="3:4", command=self.apply_gui_options_to_selected_files).pack(anchor="w")

        aspect_handling_frame = tk.Frame(geometry_group)
        aspect_handling_frame.pack(fill=tk.X)
        tk.Label(aspect_handling_frame, text="Handling:").pack(side=tk.LEFT, padx=(0,5))
        tk.Radiobutton(aspect_handling_frame, text="Crop (Fill)", variable=self.aspect_mode_var, value="crop", command=self._toggle_upscale_options).pack(side=tk.LEFT)
        tk.Radiobutton(aspect_handling_frame, text="Pad (Fit)", variable=self.aspect_mode_var, value="pad", command=self._toggle_upscale_options).pack(side=tk.LEFT)
        tk.Radiobutton(aspect_handling_frame, text="Stretch", variable=self.aspect_mode_var, value="stretch", command=self._toggle_upscale_options).pack(side=tk.LEFT)

        # 2. Format & Quality Group
        quality_group = tk.LabelFrame(right_frame, text="Format & Quality", padx=10, pady=10)
        quality_group.pack(fill=tk.X, pady=10)

        resolution_options_frame = tk.Frame(quality_group)
        resolution_options_frame.pack(fill=tk.X)
        tk.Label(resolution_options_frame, text="Resolution:").pack(side=tk.LEFT, padx=(0,5))
        tk.Radiobutton(resolution_options_frame, text="HD", variable=self.resolution_var, value="HD", command=self.apply_gui_options_to_selected_files).pack(side=tk.LEFT)
        tk.Radiobutton(resolution_options_frame, text="4k", variable=self.resolution_var, value="4k", command=self.apply_gui_options_to_selected_files).pack(side=tk.LEFT)
        tk.Radiobutton(resolution_options_frame, text="8k", variable=self.resolution_var, value="8k", command=self.apply_gui_options_to_selected_files).pack(side=tk.LEFT)
        
        upscale_frame = tk.Frame(quality_group)
        upscale_frame.pack(fill=tk.X, pady=(5,0))
        tk.Label(upscale_frame, text="Upscale Algo:").pack(side=tk.LEFT, padx=(0,5))
        self.rb_superres = tk.Radiobutton(upscale_frame, text="SuperRes", variable=self.upscale_algo_var, value="nvvfx-superres", command=self.apply_gui_options_to_selected_files)
        self.rb_superres.pack(side=tk.LEFT)
        self.rb_vsr = tk.Radiobutton(upscale_frame, text="VSR", variable=self.upscale_algo_var, value="ngx-vsr", command=self.apply_gui_options_to_selected_files)
        self.rb_vsr.pack(side=tk.LEFT)
        self.rb_lanczos = tk.Radiobutton(upscale_frame, text="Lanczos", variable=self.upscale_algo_var, value="lanczos", command=self.apply_gui_options_to_selected_files)
        self.rb_lanczos.pack(side=tk.LEFT)

        output_format_frame = tk.Frame(quality_group)
        output_format_frame.pack(fill=tk.X, pady=(5,0))
        tk.Label(output_format_frame, text="Output Format:").pack(side=tk.LEFT, padx=(0,5))
        tk.Radiobutton(output_format_frame, text="SDR", variable=self.output_format_var, value="sdr", command=self.apply_gui_options_to_selected_files).pack(side=tk.LEFT)
        tk.Radiobutton(output_format_frame, text="HDR", variable=self.output_format_var, value="hdr", command=self.apply_gui_options_to_selected_files).pack(side=tk.LEFT)
        tk.Label(output_format_frame, text="Location:").pack(side=tk.LEFT, padx=(15,5))
        tk.Radiobutton(output_format_frame, text="Local", variable=self.output_mode_var, value="local").pack(side=tk.LEFT)
        tk.Radiobutton(output_format_frame, text="Pooled", variable=self.output_mode_var, value="pooled").pack(side=tk.LEFT)

        # 3. Other Options Group
        other_opts_group = tk.LabelFrame(right_frame, text="Other Options", padx=10, pady=10)
        other_opts_group.pack(fill=tk.X)
        
        sub_opts_frame = tk.Frame(other_opts_group)
        sub_opts_frame.pack(fill=tk.X)
        tk.Label(sub_opts_frame, text="Subtitle Align:").pack(side=tk.LEFT)
        tk.Radiobutton(sub_opts_frame, text="T", variable=self.alignment_var, value="top", command=self.apply_gui_options_to_selected_files).pack(side=tk.LEFT)
        tk.Radiobutton(sub_opts_frame, text="M", variable=self.alignment_var, value="middle", command=self.apply_gui_options_to_selected_files).pack(side=tk.LEFT)
        tk.Radiobutton(sub_opts_frame, text="B", variable=self.alignment_var, value="bottom", command=self.apply_gui_options_to_selected_files).pack(side=tk.LEFT)
        tk.Label(sub_opts_frame, text="Font Size:").pack(side=tk.LEFT, padx=(10,5))
        self.subtitle_font_size_entry = tk.Entry(sub_opts_frame, textvariable=self.subtitle_font_size_var, width=5)
        self.subtitle_font_size_entry.pack(side=tk.LEFT)
        self.subtitle_font_size_entry.bind("<FocusOut>", self.apply_gui_options_to_selected_files_event)

        fruc_frame = tk.Frame(other_opts_group)
        fruc_frame.pack(fill=tk.X, pady=(5,0))
        tk.Checkbutton(fruc_frame, text="Enable FRUC", variable=self.fruc_var, command=lambda: [self.toggle_fruc_fps(), self.apply_gui_options_to_selected_files()]).pack(side=tk.LEFT)
        tk.Label(fruc_frame, text="FRUC FPS:").pack(side=tk.LEFT, padx=(5,5))
        self.fruc_fps_entry = tk.Entry(fruc_frame, textvariable=self.fruc_fps_var, width=5, state="disabled")
        self.fruc_fps_entry.pack(side=tk.LEFT)
        self.fruc_fps_entry.bind("<FocusOut>", self.apply_gui_options_to_selected_files_event)

        # --- BOTTOM BAR ---
        bottom_frame = tk.Frame(self.root)
        bottom_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        self.start_button = tk.Button(bottom_frame, text="Start Processing", command=self.start_processing, bg="#4CAF50", fg="white", font=font.Font(weight="bold"))
        self.start_button.pack(side=tk.LEFT, padx=5, ipady=5)
        self.generate_log_checkbox = tk.Checkbutton(bottom_frame, text="Generate Log File", variable=self.generate_log_var, command=self.apply_gui_options_to_selected_files)
        self.generate_log_checkbox.pack(side=tk.LEFT, padx=(10, 0))

        # --- Initial State Updates ---
        self._toggle_orientation_options()
        self._toggle_upscale_options()

    def _toggle_orientation_options(self):
        orientation = self.orientation_var.get()
        show_h_aspect = "horizontal" in orientation
        show_v_aspect = "vertical" in orientation
        
        if show_h_aspect: self.horizontal_aspect_frame.grid()
        else: self.horizontal_aspect_frame.grid_remove()
        if show_v_aspect: self.vertical_aspect_frame.grid()
        else: self.vertical_aspect_frame.grid_remove()

        self.apply_gui_options_to_selected_files()

    def _toggle_upscale_options(self):
        state = tk.NORMAL
        self.rb_superres.config(state=state)
        self.rb_vsr.config(state=state)
        self.rb_lanczos.config(state=state)
        self.apply_gui_options_to_selected_files()

    def apply_gui_options_to_selected_files(self, event=None):
        selected_indices = self.file_listbox.curselection()
        if not selected_indices: return
        options_state = {
            "resolution": self.resolution_var.get(), "upscale_algo": self.upscale_algo_var.get(),
            "output_format": self.output_format_var.get(), "fruc": self.fruc_var.get(),
            "fruc_fps": self.fruc_fps_var.get(), "alignment": self.alignment_var.get(),
            "subtitle_font_size": self.subtitle_font_size_var.get(), "generate_log": self.generate_log_var.get(),
            "orientation": self.orientation_var.get(), "aspect_mode": self.aspect_mode_var.get(),
            "horizontal_aspect": self.horizontal_aspect_var.get(),
            "vertical_aspect": self.vertical_aspect_var.get()
        }
        for index in selected_indices:
            self.file_options[self.file_list[index]] = options_state

    def update_file_list(self, files):
        for file_path in files:
            if file_path not in self.file_list:
                self.file_list.append(file_path)
                self.file_listbox.insert(tk.END, os.path.basename(file_path))
                self.subtitles_by_file[file_path] = []
                self.detect_subtitle_tracks(file_path)
                self.file_options[file_path] = {
                    "resolution": self.resolution_var.get(), "upscale_algo": self.upscale_algo_var.get(),
                    "output_format": self.output_format_var.get(), "fruc": self.fruc_var.get(),
                    "fruc_fps": self.fruc_fps_var.get(), "alignment": self.alignment_var.get(),
                    "subtitle_font_size": self.subtitle_font_size_var.get(), "generate_log": self.generate_log_var.get(),
                    "orientation": self.orientation_var.get(), "aspect_mode": self.aspect_mode_var.get(),
                    "horizontal_aspect": self.horizontal_aspect_var.get(),
                    "vertical_aspect": self.vertical_aspect_var.get()
                }

    def on_file_select(self, event):
        sel = self.file_listbox.curselection()
        if sel:
            selected_file = self.file_list[sel[0]]
            if selected_file in self.file_options:
                options = self.file_options[selected_file]
                self.resolution_var.set(options.get("resolution", DEFAULT_RESOLUTION))
                self.upscale_algo_var.set(options.get("upscale_algo", DEFAULT_UPSCALE_ALGO))
                self.output_format_var.set(options.get("output_format", DEFAULT_OUTPUT_FORMAT))
                self.orientation_var.set(options.get("orientation", DEFAULT_ORIENTATION))
                self.aspect_mode_var.set(options.get("aspect_mode", DEFAULT_ASPECT_MODE))
                self.horizontal_aspect_var.set(options.get("horizontal_aspect", DEFAULT_HORIZONTAL_ASPECT))
                self.vertical_aspect_var.set(options.get("vertical_aspect", DEFAULT_VERTICAL_ASPECT))
                self.alignment_var.set(options.get("alignment", DEFAULT_SUBTITLE_ALIGNMENT))
                self.subtitle_font_size_var.set(options.get("subtitle_font_size", DEFAULT_SUBTITLE_FONT_SIZE))
                self.fruc_var.set(options.get("fruc", DEFAULT_FRUC))
                self.fruc_fps_var.set(options.get("fruc_fps", DEFAULT_FRUC_FPS))
                self.generate_log_var.set(options.get("generate_log", False))
                self.toggle_fruc_fps()
                self._toggle_orientation_options()
                self._toggle_upscale_options() 
        self.refresh_subtitle_list()

    def build_nvenc_command_and_run(self, file_path, orientation, ass_burn=None):
        options = self.file_options.get(file_path, {})
        resolution_mode = options.get("resolution")
        output_format = options.get("output_format")
        
        folder_name = f"{resolution_mode}_{output_format.upper()}"
        if orientation == "vertical":
            vertical_aspect = options.get("vertical_aspect").replace(':', 'x')
            folder_name += f"_Vertical_{vertical_aspect}"
        else: # Horizontal
            horizontal_aspect = options.get("horizontal_aspect").replace(':', 'x')
            if horizontal_aspect != "16x9":
                folder_name += f"_Horizontal_{horizontal_aspect}"

        if self.output_mode == 'local': base_dir = os.path.dirname(file_path)
        else: base_dir = os.getcwd()
        output_dir = os.path.join(base_dir, folder_name)
        
        os.makedirs(output_dir, exist_ok=True)
        base_name, _ = os.path.splitext(os.path.basename(file_path))
        output_file = os.path.join(output_dir, f"{base_name}_temp.mp4")

        cmd = self.construct_nvencc_command(file_path, output_file, orientation, ass_burn, options)
        ret = self.run_nvenc_command(cmd)
        if ret == 0:
            final_name = output_file.replace("_temp.mp4", ".mp4")
            try:
                if os.path.exists(final_name): os.remove(final_name)
                os.rename(output_file, final_name)
                print(f"File finalized => {final_name}")
                self.verify_output_file(final_name)
            except Exception as e:
                print(f"[ERROR] Could not rename temp file {output_file}: {e}")
        else:
            print(f"[ERROR] Error encoding {file_path}: return code {ret}")

    def construct_nvencc_command(self, file_path, output_file, orientation, ass_burn, options):
        info = get_video_info(file_path)
        cmd = ["NVEncC64", "--avhw", "--preset", "p1", "--log-level", "info"]
        
        aspect_mode = options.get("aspect_mode")
        resolution_key = options.get('resolution')
        upscale_algo = options.get("upscale_algo")

        if orientation == "vertical":
            aspect_str = options.get('vertical_aspect')
            width_map = {"HD": 1080, "4k": 2160, "8k": 4320}
            target_width = width_map.get(resolution_key, 1080)
            try: num, den = map(int, aspect_str.split(':')); target_height = int(target_width * den / num)
            except: target_height = int(target_width * 16 / 9)
        else: # Horizontal
            aspect_str = options.get('horizontal_aspect')
            width_map = {"HD": 1920, "4k": 3840, "8k": 7680}
            target_width = width_map.get(resolution_key, 1920)
            try: num, den = map(int, aspect_str.split(':')); target_height = int(target_width * den / num)
            except: target_height = int(target_width * 9 / 16)

        target_width = (target_width // 2) * 2
        target_height = (target_height // 2) * 2
        
        if aspect_mode == 'stretch':
            cmd.extend(["--output-res", f"{target_width}x{target_height}"])
            resize_params = f"algo={upscale_algo}"
            if upscale_algo == "ngx-vsr": resize_params += ",vsr-quality=1"
            cmd.extend(["--vpp-resize", resize_params])
        
        elif aspect_mode == 'pad':
            if info['height'] > 0 and info['width'] > 0:
                source_aspect = info['width'] / info['height']
                target_aspect = target_width / target_height
                pad_str = "0,0,0,0"
                if source_aspect > target_aspect:
                    new_height = int(info['width'] / target_aspect)
                    total_pad = new_height - info['height']
                    pad_val = (total_pad // 2) - ((total_pad // 2) % 2)
                    if pad_val > 0: pad_str = f"0,{pad_val},0,{pad_val}"
                elif source_aspect < target_aspect:
                    new_width = int(info['height'] * target_aspect)
                    total_pad = new_width - info['width']
                    pad_val = (total_pad // 2) - ((total_pad // 2) % 2)
                    if pad_val > 0: pad_str = f"{pad_val},0,{pad_val},0"
                if pad_str != "0,0,0,0": cmd.extend(["--vpp-pad", pad_str])
            cmd.extend(["--output-res", f"{target_width}x{target_height}"])
            resize_params = f"algo={upscale_algo}"
            if upscale_algo == "ngx-vsr": resize_params += ",vsr-quality=1"
            cmd.extend(["--vpp-resize", resize_params])

        else: # aspect_mode == 'crop'
            cmd.extend(["--output-res", f"{target_width}x{target_height}"])
            if info['height'] > 0 and info['width'] > 0:
                source_aspect = info['width'] / info['height']
                target_aspect = target_width / target_height
                crop_str = "0,0,0,0"
                if source_aspect > target_aspect:
                    new_width_in_source = int(info['height'] * target_aspect)
                    crop_val = (info['width'] - new_width_in_source) // 2
                    crop_val -= crop_val % 2 
                    if crop_val > 0: crop_str = f"{crop_val},0,{crop_val},0"
                elif source_aspect < target_aspect:
                    new_height_in_source = int(info['width'] / target_aspect)
                    crop_val = (info['height'] - new_height_in_source) // 2
                    crop_val -= crop_val % 2
                    if crop_val > 0: crop_str = f"0,{crop_val},0,{crop_val}"
                if crop_str != "0,0,0,0": cmd.extend(["--crop", crop_str])
            resize_params = f"algo={upscale_algo}"
            if upscale_algo == "ngx-vsr": resize_params += ",vsr-quality=1"
            cmd.extend(["--vpp-resize", resize_params])

        output_format = options.get("output_format"); is_hdr_output = output_format == 'hdr'
        bitrate_res_key = "HD" if resolution_key == "HD" else resolution_key.lower()
        bitrate_kbps = get_bitrate(bitrate_res_key, info["framerate"], is_hdr_output)
        gop_len = 0 if info["framerate"] == 0 else math.ceil(info["framerate"] / 2)
        cmd.extend(["--vbr", str(bitrate_kbps), "--gop-len", str(gop_len)])
        audio_streams = get_audio_stream_info(file_path)
        if len(audio_streams) > 0:
            cmd.extend(["--audio-codec", "aac", "--audio-samplerate", "48000", "--audio-bitrate", "512"])
            if len(audio_streams) >= 2: cmd.extend(["--audio-stream", "1?1:stereo", "--audio-stream", "2?2:5.1"])
            else: cmd.extend(["--audio-stream", "1?1:stereo", "--audio-stream", "2?1:5.1"])
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
        orientation_mode = self.orientation_var.get()
        print("\n" + "="*80)
        print("--- Starting processing with the following settings ---")
        try:
            options = self.file_options.get(self.file_list[0], {})
            print(f"  Output Mode: {self.output_mode}")
            print(f"  Orientation: {orientation_mode}")
            print(f"  Resolution: {options.get('resolution')}")
            print(f"  Aspect Handling: {options.get('aspect_mode')}")
            if "horizontal" in orientation_mode: print(f"  Horizontal Aspect: {options.get('horizontal_aspect')}")
            if "vertical" in orientation_mode: print(f"  Vertical Aspect: {options.get('vertical_aspect')}")
            print(f"  Upscale Algorithm: {options.get('upscale_algo')}")
            print(f"  Output Format: {options.get('output_format')}")
        except IndexError: print("  No files in list to show settings for.")
        print("="*80 + "\n")
        self.root.destroy()
        for file_path in self.file_list:
            base_name = os.path.basename(file_path)
            if orientation_mode == "horizontal": self.build_nvenc_command_and_run(file_path, "horizontal")
            elif orientation_mode == "vertical": self.build_nvenc_command_and_run(file_path, "vertical")
            elif orientation_mode == "horizontal + vertical":
                print(f"\n--- Processing HORIZONTAL for: {base_name} ---")
                self.build_nvenc_command_and_run(file_path, "horizontal")
                print(f"\n--- Processing VERTICAL for: {base_name} ---")
                self.build_nvenc_command_and_run(file_path, "vertical")
        print("\n================== Processing Complete. ==================")

    def run_nvenc_command(self, cmd):
        print("Running NVEnc command:")
        print(" ".join(f'"{c}"' if " " in c else c for c in cmd))
        process = subprocess.Popen(cmd,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env, text=True,encoding='utf-8',errors='replace',bufsize=1)
        while True:
            line = process.stdout.readline()
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
        if self.file_listbox.size() > 0 and not self.file_listbox.curselection(): self.file_listbox.select_set(0); self.on_file_select(None)
    def handle_file_drop(self, event):
        files = self.root.tk.splitlist(event.data); self.update_file_list(files)
        if self.file_listbox.size() > 0 and not self.file_listbox.curselection(): self.file_listbox.select_set(0); self.on_file_select(None)
    def remove_selected(self):
        selected_indices = list(self.file_listbox.curselection())
        for index in reversed(selected_indices):
            file_to_remove = self.file_list[index]
            if file_to_remove in self.subtitles_by_file: del self.subtitles_by_file[file_to_remove]
            if file_to_remove in self.file_options: del self.file_options[file_to_remove]
            del self.file_list[index]; self.file_listbox.delete(index)
        self.refresh_subtitle_list()
    def clear_all(self):
        self.file_list.clear(); self.file_listbox.delete(0, tk.END); self.subtitles_by_file.clear(); self.file_options.clear(); self.refresh_subtitle_list()
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
        print(f"No input files provided. Scanning current directory: {current_dir}...")
        files_from_cwd = [f for f in os.listdir(current_dir) if os.path.isfile(os.path.join(current_dir, f)) and os.path.splitext(f)[1].lower() in video_extensions]
        initial_files.extend(sorted([os.path.join(current_dir, f) for f in files_from_cwd]))
    app = VideoProcessorApp(root, sorted(list(set(initial_files))), args.output_mode)
    root.mainloop()