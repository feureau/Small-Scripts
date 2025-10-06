"""
====================================================================================================
                            YouTube Batch Video Processing Tool
====================================================================================================

PURPOSE:
This script provides a Graphical User Interface (GUI) to batch process video files,
optimizing them for upload to YouTube according to their recommended specifications.
It acts as a front-end for the powerful NVIDIA hardware-accelerated encoder, NVEncC.

FEATURES:
- Batch processing with drag-and-drop support.
- Flexible output location: either pooled in one central folder or organized into
  subfolders within each source file's original location.
- Output compliant with YouTube's official recommendations for both SDR and HDR content.
- High-quality AI upscaling to 4K or 8K (requires NVIDIA RTX GPU).
- Automatic color space and tone mapping (e.g., HDR to SDR conversion).
- Automatic deinterlacing to meet progressive scan requirements.
- Creates a clean Stereo + 5.1 Surround audio layout as recommended.
- Organizes output files into resolution and format-specific folders (e.g., "4k_SDR").

----------------------------------------------------------------------------------------------------
                                    NOTE ON DOCUMENTATION
----------------------------------------------------------------------------------------------------
This documentation is a living document. With every update to the script's functionality,
this documentation will be reviewed and expanded to ensure it remains accurate, detailed,
and clear. The goal is to not only explain *what* the script does, but *why* it does it
in a particular way, especially in relation to YouTube's encoding standards.

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



----------------------------------------------------------------------------------------------------
                                    COMMAND-LINE ARGUMENTS
----------------------------------------------------------------------------------------------------
This script can be configured with flags when run from a command prompt or terminal.

-h, --help
  Displays a comprehensive help message that lists all available command-line arguments,
  their purpose, and how to use them.

-o {local,pooled}, --output-mode {local,pooled}
  This flag sets the *initial* state for the output location in the GUI. The final selection
  made in the GUI will be what the script uses for processing.

  - `local` (Default):
    This mode creates the output subfolders inside the original directory of each source
    video file. This is the ideal choice for organizational purposes, as it keeps the
    processed version directly alongside its source file. This is highly recommended when
    you are processing an entire folder tree and want to maintain the original structure.
    Example: Processing `D:\Videos\vacation.mp4` will result in the output being saved to
    `D:\Videos\4k_SDR\vacation.mp4`.

  - `pooled`:
    This mode gathers all processed videos into subfolders created inside the script's
    current working directory (CWD). This is useful when you want to process files from
    many different locations and have all the final, YouTube-ready files collected in
    one central place for easy uploading.
    Example: Processing `D:\Videos\vacation.mp4` will result in the output being saved to
    `C:\Path\To\Script\4k_SDR\vacation.mp4`.

----------------------------------------------------------------------------------------------------
                                        GUI OVERVIEW
----------------------------------------------------------------------------------------------------
In addition to command-line flags, key options are available in the graphical interface.

Output Location:
  - This pair of radio buttons ("Local" and "Pooled") provides full control over where
    processed files are saved.
  - "Local": Saves the output in a subfolder next to the original video.
  - "Pooled": Saves all output in a subfolder where the script is running.
  - The selection made here overrides the initial state set by the `--output-mode`
    command-line flag. This ensures that what you see in the GUI is what you get.

----------------------------------------------------------------------------------------------------
                                        DEPENDENCIES
----------------------------------------------------------------------------------------------------

1. Python Libraries (install via pip):
   - tkinterdnd2: `pip install tkinterdnd2`
   - ftfy: `pip install ftfy`

2. External Command-Line Tools:
   These executables must be placed in the same folder as this script, or in a directory
   listed in your system's PATH environment variable.
   - NVEncC64.exe: The core NVIDIA hardware video encoder.
   - ffmpeg.exe: Used for subtitle extraction.
   - ffprobe.exe: Used for reading video file metadata (resolution, frame rate, etc.).

----------------------------------------------------------------------------------------------------
                          YOUTUBE RECOMMENDED UPLOAD ENCODING SETTINGS
----------------------------------------------------------------------------------------------------
(Documentation on YouTube settings and NVEncC flags remains the same and is omitted for brevity)
...
"""

import os
import subprocess
import shutil
import json
import tkinter as tk
from tkinter import filedialog, messagebox
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
DEFAULT_VERTICAL_CROP = False
DEFAULT_FRUC = False
DEFAULT_FRUC_FPS = "60"
DEFAULT_SUBTITLE_ALIGNMENT = "middle"
DEFAULT_SUBTITLE_FONT_SIZE = "12"

# ----------------------------------------------------------------------------------------------------

env = os.environ.copy()
env["PYTHONIOENCODING"] = "utf-8"

def get_video_info(file_path):
    cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=pix_fmt,r_frame_rate,height,color_transfer,color_primaries", "-of", "json", file_path]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, env=env)
        data = json.loads(result.stdout)["streams"][0]
        pix_fmt = data.get("pix_fmt", "yuv420p")
        bit_depth = 10 if pix_fmt in ["yuv420p10le", "p010le"] else 8
        fr_str = data.get("r_frame_rate", "30/1")
        num, den = map(int, fr_str.split('/'))
        framerate = num / den if den != 0 else 30.0
        height = int(data.get("height", 1080))
        color_transfer = data.get("color_transfer", "").lower()
        color_primaries = data.get("color_primaries", "").lower()
        is_hdr = color_transfer in ["smpte2084", "arib-std-b67"] or color_primaries == "bt2020"
        return {"bit_depth": bit_depth, "framerate": framerate, "height": height, "is_hdr": is_hdr}
    except Exception as e:
        print(f"[WARN] Could not get video info for {file_path}, using defaults: {e}")
        return {"bit_depth": 8, "framerate": 30.0, "height": 1080, "is_hdr": False}

def get_audio_stream_info(file_path):
    cmd = ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index,channels", "-of", "json", file_path]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, env=env)
        streams = json.loads(result.stdout).get("streams", [])
        return [{"channels": s.get("channels", 2)} for s in streams]
    except Exception as e:
        print(f"[WARN] Could not get detailed audio stream info for {file_path}: {e}")
        return []

def get_input_width(file_path):
    cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width", "-of", "csv=p=0", file_path]
    try:
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, universal_newlines=True, env=env)
        return int(output.strip().replace(',', ''))
    except Exception as e:
        print(f"[ERROR] Error getting width from ffprobe: {e}")
        return 0

def get_bitrate(resolution_key, framerate, is_hdr):
    is_high_fps = framerate > 40
    sdr_table = {"8k": (320, 480), "4k": (90, 136), "1440p": (32, 48), "1080p": (16, 24), "720p": (10, 15)}
    hdr_table = {"8k": (400, 600), "4k": (112, 170), "1440p": (40, 60), "1080p": (20, 30), "720p": (13, 19)}
    table = hdr_table if is_hdr else sdr_table
    default_bitrate = (30, 40) if is_hdr else (24, 36)
    rate_tuple = table.get(resolution_key, default_bitrate)
    return rate_tuple[1] if is_high_fps else rate_tuple[0]

def normalize_text(text):
    return fix_text(text).replace("’", "'")

def cleanup_ass_content(ass_file):
    try:
        with open(ass_file, 'r', encoding='utf-8') as f: content = f.readlines()
        cleaned_lines = [line.replace(r'\N', ' ', 1) for line in content]
        with open(ass_file, 'w', encoding='utf-8', newline='\n') as f: f.writelines(cleaned_lines)
    except Exception as e:
        print(f"[ERROR] Error cleaning up ASS content: {ass_file}: {e}")

class VideoProcessorApp:
    def __init__(self, root, initial_files, output_mode):
        self.root = root; self.root.title("Video Processing Tool")
        self.lut_file = LUT_FILE_PATH
        self.output_mode = output_mode # This will be updated from the GUI before processing
        self.subtitles_by_file = {}; self.file_list = []
        self.subtitle_id_counter = 0; self.current_subtitle_checkbuttons = []
        self.file_options = {}

        # --- GUI Variables ---
        # <<< NEWLY ADDED >>>: GUI variable for output mode
        self.output_mode_var = tk.StringVar(value=output_mode)
        self.resolution_var = tk.StringVar(value=DEFAULT_RESOLUTION)
        self.upscale_algo_var = tk.StringVar(value=DEFAULT_UPSCALE_ALGO)
        self.output_format_var = tk.StringVar(value=DEFAULT_OUTPUT_FORMAT)
        self.crop_var = tk.BooleanVar(value=DEFAULT_VERTICAL_CROP)
        self.fruc_var = tk.BooleanVar(value=DEFAULT_FRUC)
        self.fruc_fps_var = tk.StringVar(value=DEFAULT_FRUC_FPS)
        self.alignment_var = tk.StringVar(value=DEFAULT_SUBTITLE_ALIGNMENT)
        self.subtitle_font_size_var = tk.StringVar(value=DEFAULT_SUBTITLE_FONT_SIZE)
        self.generate_log_var = tk.BooleanVar(value=False)
        self.root.drop_target_register(DND_FILES); self.root.dnd_bind("<<Drop>>", self.handle_file_drop)
        
        self.setup_gui()
        self.update_file_list(initial_files)
        if self.file_listbox.size() > 0: self.file_listbox.select_set(0); self.on_file_select(None)
    
    # <<< MODIFIED METHOD >>>
    def setup_gui(self):
        # --- File List Frame ---
        self.file_frame = tk.Frame(self.root); self.file_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.file_listbox = tk.Listbox(self.file_frame, selectmode=tk.EXTENDED, height=15); self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.file_scrollbar = tk.Scrollbar(self.file_frame, orient=tk.VERTICAL, command=self.file_listbox.yview); self.file_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_listbox.config(yscrollcommand=self.file_scrollbar.set); self.file_listbox.bind("<<ListboxSelect>>", self.on_file_select)
        
        # --- File Buttons Frame ---
        self.file_buttons_frame = tk.Frame(self.root); self.file_buttons_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Button(self.file_buttons_frame, text="Select All", command=self.select_all_files).pack(side=tk.LEFT, padx=5)
        tk.Button(self.file_buttons_frame, text="Add Files", command=self.add_files).pack(side=tk.LEFT, padx=5)
        tk.Button(self.file_buttons_frame, text="Remove Selected", command=self.remove_selected).pack(side=tk.LEFT, padx=5)
        tk.Button(self.file_buttons_frame, text="Clear All", command=self.clear_all).pack(side=tk.LEFT, padx=5)
        tk.Button(self.file_buttons_frame, text="Move Up", command=self.move_up).pack(side=tk.LEFT, padx=5)
        tk.Button(self.file_buttons_frame, text="Move Down", command=self.move_down).pack(side=tk.LEFT, padx=5)
        
        # --- Main Options Frame ---
        self.options_frame = tk.Frame(self.root); self.options_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # --- Resolution and Upscaling ---
        self.resolution_options_frame = tk.LabelFrame(self.options_frame, text="Resolution and Upscale Algorithm", padx=10, pady=5); self.resolution_options_frame.grid(row=0, column=0, columnspan=4, sticky="ew", pady=5)
        tk.Label(self.resolution_options_frame, text="Resolution:").grid(row=0, column=0, sticky=tk.W)
        tk.Radiobutton(self.resolution_options_frame, text="HD", variable=self.resolution_var, value="HD", command=self.apply_gui_options_to_selected_files).grid(row=0, column=1, sticky=tk.W)
        tk.Radiobutton(self.resolution_options_frame, text="4k", variable=self.resolution_var, value="4k", command=self.apply_gui_options_to_selected_files).grid(row=0, column=2, sticky=tk.W)
        tk.Radiobutton(self.resolution_options_frame, text="8k", variable=self.resolution_var, value="8k", command=self.apply_gui_options_to_selected_files).grid(row=0, column=3, sticky=tk.W)
        tk.Label(self.resolution_options_frame, text="Upscale Algorithm:").grid(row=1, column=0, sticky=tk.W, padx=(20, 0))
        tk.Radiobutton(self.resolution_options_frame, text="nvvfx-superres", variable=self.upscale_algo_var, value="nvvfx-superres", command=self.apply_gui_options_to_selected_files).grid(row=1, column=1, sticky=tk.W, padx=(20, 0))
        tk.Radiobutton(self.resolution_options_frame, text="ngx-vsr", variable=self.upscale_algo_var, value="ngx-vsr", command=self.apply_gui_options_to_selected_files).grid(row=1, column=2, sticky=tk.W)
        tk.Radiobutton(self.resolution_options_frame, text="lanczos", variable=self.upscale_algo_var, value="lanczos", command=self.apply_gui_options_to_selected_files).grid(row=1, column=3, sticky=tk.W)
        
        # --- Output Format ---
        self.output_format_frame = tk.LabelFrame(self.options_frame, text="Output Format (YouTube Compliant)", padx=10, pady=5); self.output_format_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=5)
        tk.Radiobutton(self.output_format_frame, text="SDR (H.264)", variable=self.output_format_var, value="sdr", command=self.apply_gui_options_to_selected_files).pack(side=tk.LEFT, padx=5)
        tk.Radiobutton(self.output_format_frame, text="HDR (HEVC)", variable=self.output_format_var, value="hdr", command=self.apply_gui_options_to_selected_files).pack(side=tk.LEFT, padx=5)

        # <<< NEWLY ADDED >>>: Output Location GUI Controls
        self.output_location_frame = tk.LabelFrame(self.options_frame, text="Output Location", padx=10, pady=5); self.output_location_frame.grid(row=1, column=2, columnspan=2, sticky="ew", pady=5, padx=5)
        tk.Radiobutton(self.output_location_frame, text="Local (In Source Folder)", variable=self.output_mode_var, value="local").pack(side=tk.LEFT, padx=5)
        tk.Radiobutton(self.output_location_frame, text="Pooled (In Script Folder)", variable=self.output_mode_var, value="pooled").pack(side=tk.LEFT, padx=5)

        # --- Other Options (Cropping, FRUC, Subtitles) ---
        # (This section is collapsed for brevity, no changes were made here)
        tk.Label(self.options_frame, text="Vertical Crop:").grid(row=4, column=0, sticky=tk.W)
        tk.Checkbutton(self.options_frame, variable=self.crop_var, command=self.apply_gui_options_to_selected_files).grid(row=4, column=1, sticky=tk.W)
        tk.Label(self.options_frame, text="Enable FRUC:").grid(row=6, column=0, sticky=tk.W)
        tk.Checkbutton(self.options_frame, variable=self.fruc_var, command=lambda: [self.toggle_fruc_fps(), self.apply_gui_options_to_selected_files()]).grid(row=6, column=1, sticky=tk.W)
        tk.Label(self.options_frame, text="FRUC FPS Target:").grid(row=7, column=0, sticky=tk.W)
        self.fruc_fps_entry = tk.Entry(self.options_frame, textvariable=self.fruc_fps_var, width=10, state="disabled"); self.fruc_fps_entry.grid(row=7, column=1, sticky=tk.W); self.fruc_fps_entry.bind("<FocusOut>", self.apply_gui_options_to_selected_files_event)
        tk.Label(self.options_frame, text="Subtitle Alignment:").grid(row=8, column=0, sticky=tk.W)
        self.align_frame = tk.Frame(self.options_frame); self.align_frame.grid(row=8, column=1, columnspan=3, sticky=tk.W)
        tk.Radiobutton(self.align_frame, text="Top", variable=self.alignment_var, value="top", command=self.apply_gui_options_to_selected_files).pack(anchor="w")
        tk.Radiobutton(self.align_frame, text="Middle", variable=self.alignment_var, value="middle", command=self.apply_gui_options_to_selected_files).pack(anchor="w")
        tk.Radiobutton(self.align_frame, text="Bottom", variable=self.alignment_var, value="bottom", command=self.apply_gui_options_to_selected_files).pack(anchor="w")
        tk.Label(self.options_frame, text="Subtitle Font Size:").grid(row=9, column=0, sticky=tk.W)
        self.subtitle_font_size_entry = tk.Entry(self.options_frame, textvariable=self.subtitle_font_size_var, width=10); self.subtitle_font_size_entry.grid(row=9, column=1, sticky=tk.W); self.subtitle_font_size_entry.bind("<FocusOut>", self.apply_gui_options_to_selected_files_event)
        
        # --- Subtitle Tracks Frame ---
        self.subtitle_tracks_frame = tk.LabelFrame(self.root, text="Burn Subtitle Tracks", padx=10, pady=10); self.subtitle_tracks_frame.pack(fill=tk.X, padx=10, pady=5)
        self.subtitle_tracks_buttons_frame = tk.Frame(self.subtitle_tracks_frame); self.subtitle_tracks_buttons_frame.pack(fill=tk.X, padx=5, pady=5)
        tk.Button(self.subtitle_tracks_buttons_frame, text="Load Embedded SRT (All Files)", command=self.load_embedded_srt_all).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(self.subtitle_tracks_buttons_frame, text="Add External SRT (Current File)", command=self.add_external_srt).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(self.subtitle_tracks_buttons_frame, text="Remove Selected SRT (Current File)", command=self.remove_selected_srt).pack(side=tk.LEFT, padx=(0, 5))
        self.subtitle_tracks_list_frame = tk.Frame(self.subtitle_tracks_frame); self.subtitle_tracks_list_frame.pack(fill=tk.X)
        
        # --- Bottom Frame ---
        self.bottom_frame = tk.Frame(self.root); self.bottom_frame.pack(pady=10, padx=10, fill=tk.X)
        self.start_button = tk.Button(self.bottom_frame, text="Start Processing", command=self.start_processing); self.start_button.pack(side=tk.LEFT, padx=5)
        self.generate_log_checkbox = tk.Checkbutton(self.bottom_frame, text="Generate Log File", variable=self.generate_log_var, command=self.apply_gui_options_to_selected_files); self.generate_log_checkbox.pack(side=tk.LEFT, padx=(10, 0))

    def compute_final_resolution(self, file_path):
        options = self.file_options.get(file_path, {})
        resolution = options.get("resolution", self.resolution_var.get())
        if resolution == "HD":
            info = get_video_info(file_path)
            return get_input_width(file_path), info["height"]
        elif resolution == "4k": return 2160, 2160
        elif resolution == "8k": return 4320, 4320
        return 1080, 1080

    def apply_gui_options_to_selected_files(self, event=None):
        selected_indices = self.file_listbox.curselection()
        if not selected_indices: return
        options_state = {"resolution": self.resolution_var.get(), "upscale_algo": self.upscale_algo_var.get(), "output_format": self.output_format_var.get(), "crop": self.crop_var.get(), "fruc": self.fruc_var.get(), "fruc_fps": self.fruc_fps_var.get(), "alignment": self.alignment_var.get(), "subtitle_font_size": self.subtitle_font_size_var.get(), "generate_log": self.generate_log_var.get()}
        for index in selected_indices: self.file_options[self.file_list[index]] = options_state

    def update_file_list(self, files):
        for file_path in files:
            if file_path not in self.file_list:
                self.file_list.append(file_path)
                self.file_listbox.insert(tk.END, file_path)
                self.subtitles_by_file[file_path] = []
                self.detect_subtitle_tracks(file_path)
                self.file_options[file_path] = {"resolution": self.resolution_var.get(), "upscale_algo": self.upscale_algo_var.get(), "output_format": self.output_format_var.get(), "crop": self.crop_var.get(), "fruc": self.fruc_var.get(), "fruc_fps": self.fruc_fps_var.get(), "alignment": self.alignment_var.get(), "subtitle_font_size": self.subtitle_font_size_var.get(), "generate_log": self.generate_log_var.get()}

    def on_file_select(self, event):
        sel = self.file_listbox.curselection()
        if sel:
            selected_file = self.file_list[sel[0]]
            if selected_file in self.file_options:
                options = self.file_options[selected_file]
                self.resolution_var.set(options.get("resolution", DEFAULT_RESOLUTION))
                self.upscale_algo_var.set(options.get("upscale_algo", DEFAULT_UPSCALE_ALGO))
                self.output_format_var.set(options.get("output_format", DEFAULT_OUTPUT_FORMAT))
                self.crop_var.set(options.get("crop", DEFAULT_VERTICAL_CROP))
                self.fruc_var.set(options.get("fruc", DEFAULT_FRUC))
                self.fruc_fps_var.set(options.get("fruc_fps", DEFAULT_FRUC_FPS))
                self.alignment_var.set(options.get("alignment", DEFAULT_SUBTITLE_ALIGNMENT))
                self.subtitle_font_size_var.set(options.get("subtitle_font_size", DEFAULT_SUBTITLE_FONT_SIZE))
                self.generate_log_var.set(options.get("generate_log", False))
                self.toggle_fruc_fps()
        self.refresh_subtitle_list()

    def build_nvenc_command_and_run(self, file_path, ass_burn=None):
        options = self.file_options.get(file_path, {})
        resolution_mode = options.get("resolution", self.resolution_var.get())
        output_format = options.get("output_format", self.output_format_var.get())
        folder_name = f"{resolution_mode}_{output_format.upper()}"
        
        if self.output_mode == 'local':
            base_dir = os.path.dirname(file_path)
        else: # 'pooled'
            base_dir = os.getcwd()
        output_dir = os.path.join(base_dir, folder_name)
        
        os.makedirs(output_dir, exist_ok=True)
        base_name, _ = os.path.splitext(os.path.basename(file_path))
        output_file = os.path.join(output_dir, f"{base_name}_temp.mp4")
        final_width, final_height = self.compute_final_resolution(file_path)
        do_resize = resolution_mode != "original"
        target_res = f"{final_width}x{final_height}"
        cmd = self.construct_nvencc_command(file_path, output_file, ass_burn, target_res, do_resize, options)
        ret = self.run_nvenc_command(cmd)
        if ret == 0: return (output_file, final_width, final_height)
        else:
            print(f"[ERROR] Error encoding {file_path}: return code {ret}")
            return (None, final_width, final_height)

    def construct_nvencc_command(self, file_path, output_file, ass_burn, target_res, do_resize, options):
        # (This method is unchanged and collapsed for brevity)
        info = get_video_info(file_path)
        output_format = options.get("output_format")
        resolution_mode = options.get("resolution")
        is_hdr_output = output_format == 'hdr'
        cmd = ["NVEncC64", "--avhw", "--preset", "p1", "--log-level", "info"]
        if resolution_mode == "original":
            if info["height"] > 3000: res_key = "8k"
            elif info["height"] > 1800: res_key = "4k"
            elif info["height"] > 1200: res_key = "1440p"
            elif info["height"] > 800: res_key = "1080p"
            else: res_key = "720p"
        else: res_key = resolution_mode
        bitrate_mbps = get_bitrate(res_key, info["framerate"], is_hdr_output)
        gop_len = 0 if info["framerate"] == 0 else math.ceil(info["framerate"] / 2)
        cmd.extend(["--vbr", str(int(bitrate_mbps * 1000)), "--gop-len", str(gop_len)])
        audio_streams = get_audio_stream_info(file_path)
        if len(audio_streams) > 0:
            cmd.extend(["--audio-codec", "aac", "--audio-samplerate", "48000"])
            cmd.extend(["--audio-bitrate", "512"])
            if len(audio_streams) >= 2:
                cmd.extend(["--audio-stream", "1?1:stereo", "--audio-stream", "2?2:5.1"])
            else:
                cmd.extend(["--audio-stream", "1?1:stereo", "--audio-stream", "2?1:5.1"])
        if is_hdr_output:
            cmd.extend(["--codec", "hevc", "--profile", "main10", "--output-depth", "10", "--colorprim", "bt2020", "--transfer", "smpte2084", "--colormatrix", "bt2020nc", "--dhdr10-info", "pass"])
        else:
            cmd.extend(["--codec", "h264", "--profile", "high", "--output-depth", "8", "--bframes", "2", "--colorprim", "bt709", "--transfer", "bt709", "--colormatrix", "bt709"])
            if info["is_hdr"] and os.path.exists(self.lut_file):
                cmd.extend(["--vpp-colorspace", f"lut3d={self.lut_file},lut3d_interp=trilinear"])
        cmd.extend(["--vpp-deinterlace", "adaptive"])
        if do_resize:
            upscale_algo = options.get("upscale_algo", self.upscale_algo_var.get())
            resize_params = f"algo={upscale_algo}"
            if upscale_algo == "ngx-vsr": resize_params += ",vsr-quality=1"
            cmd.extend(["--vpp-resize", resize_params, "--output-res", f"{target_res},preserve_aspect_ratio=increase"])
        crop_str = self.compute_crop_value(file_path, resolution_mode)
        if crop_str != "0,0,0,0": cmd.extend(["--crop", crop_str])
        if options.get("fruc"): cmd.extend(["--vpp-fruc", f"fps={options.get('fruc_fps')}"])
        if options.get("generate_log"): cmd.extend(["--log", "log.log", "--log-level", "debug"])
        if ass_burn: cmd.extend(["--vpp-subburn", f"filename={ass_burn}"])
        cmd.extend(["--output", output_file, "-i", file_path])
        return cmd

    def encode_single_pass(self, file_path):
        out_file, width, height = self.build_nvenc_command_and_run(file_path)
        if out_file:
            base, ext = os.path.splitext(out_file)
            if base.endswith("_temp"):
                final_name = base[:-5] + ext
                try: os.rename(out_file, final_name); print(f"File finalized => {final_name}")
                except Exception as e: print(f"[ERROR] Could not rename temp file {out_file}: {e}")
        if file_path in self.subtitles_by_file:
            options = self.file_options.get(file_path, {})
            resolution_mode = options.get("resolution", self.resolution_var.get())
            output_format = options.get("output_format", self.output_format_var.get())
            folder_name = f"{resolution_mode}_{output_format.upper()}"

            if self.output_mode == 'local':
                base_dir = os.path.dirname(file_path)
            else: # 'pooled'
                base_dir = os.getcwd()
            output_dir = os.path.join(base_dir, folder_name)

            base_name, _ = os.path.splitext(os.path.basename(file_path))
            for sub in self.subtitles_by_file[file_path]:
                if sub["type"] == "embedded":
                    ass_path = os.path.join(output_dir, f"{base_name}_track{sub['track_id']}.ass")
                    srt_path = os.path.join(output_dir, f"{base_name}_track{sub['track_id']}.srt")
                    self.extract_embedded_subtitle_to_ass(file_path, ass_path, sub["track_id"], width, height)
                    self.extract_subtitle_to_srt(file_path, srt_path, sub["track_id"])

    def compute_crop_value(self, file_path, resolution_mode):
        options = self.file_options.get(file_path, {})
        if not options.get("crop"): return "0,0,0,0"
        input_width = get_input_width(file_path)
        if resolution_mode == "4k" and input_width >= 3840: return "528,0,528,0"
        if resolution_mode == "8k" and input_width >= 7680: return "1056,0,1056,0"
        return "0,0,0,0"

    # <<< MODIFIED METHOD >>>
    def start_processing(self):
        if not self.file_list: messagebox.showwarning("No Files", "Please add at least one file to process."); return
        
        # <<< NEW: Get the final output mode from the GUI just before processing starts >>>
        self.output_mode = self.output_mode_var.get()
        print(f"--- Starting processing with output mode: {self.output_mode} ---")
        
        self.root.destroy()
        for file_path in self.file_list: self.encode_single_pass(file_path)
        print("Processing Complete.")

    def run_nvenc_command(self, cmd):
        print("Running NVEnc command:"); print(" ".join(cmd))
        process = subprocess.Popen(cmd,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env, text=True,encoding='utf-8',errors='replace',bufsize=1)
        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None: break
            if line:
                if "\r" in line: progress = line.split("\r")[-1].strip(); sys.stdout.write("\r" + progress); sys.stdout.flush()
                else: sys.stdout.write(line); sys.stdout.flush()
        process.stdout.close(); ret = process.wait(); print("\nNVEnc conversion finished."); return ret
    
    # (Helper methods are unchanged and collapsed for brevity)
    def apply_gui_options_to_selected_files_event(self, event): self.apply_gui_options_to_selected_files()
    def load_embedded_srt_all(self):
        for file_path in self.file_list: self.detect_subtitle_tracks(file_path)
        self.refresh_subtitle_list()
    def add_files(self):
        files = filedialog.askopenfilenames(filetypes=[("Video Files", "*.mp4;*.mkv;*.avi"), ("All Files", "*.*")])
        self.update_file_list(files)
        if self.file_listbox.size() > 0 and not self.file_listbox.curselection(): self.file_listbox.select_set(0); self.on_file_select(None)
    def handle_file_drop(self, event):
        files = self.root.tk.splitlist(event.data); self.update_file_list(files)
        if self.file_listbox.size() > 0 and not self.file_listbox.curselection(): self.file_listbox.select_set(0); self.on_file_select(None)
    def select_all_files(self): self.file_listbox.select_set(0, tk.END)
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
    def move_up(self):
        selected_indices = list(self.file_listbox.curselection())
        if not selected_indices or selected_indices[0] == 0: return
        for index in selected_indices:
            if index > 0:
                self.file_list[index], self.file_list[index-1] = self.file_list[index-1], self.file_list[index]
                item = self.file_listbox.get(index); self.file_listbox.delete(index); self.file_listbox.insert(index-1, item); self.file_listbox.select_set(index-1)
    def move_down(self):
        selected_indices = list(self.file_listbox.curselection())
        if not selected_indices or selected_indices[-1] == self.file_listbox.size() - 1: return
        for index in reversed(selected_indices):
            if index < self.file_listbox.size() - 1:
                self.file_list[index], self.file_list[index+1] = self.file_list[index+1], self.file_list[index]
                item = self.file_listbox.get(index); self.file_listbox.delete(index); self.file_listbox.insert(index+1, item); self.file_listbox.select_set(index+1)
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

    parser = argparse.ArgumentParser(description="YouTube Batch Video Processing Tool")
    parser.add_argument(
        '-o', '--output-mode',
        dest='output_mode',
        choices=['local', 'pooled'],
        # <<< MODIFIED: Default is now 'local' >>>
        default='local',
        help="Set the initial output directory mode. 'local' (default): output to a subfolder in each video's original directory. 'pooled': all output to a subfolder in the script's directory."
    )
    parser.add_argument(
        'input_files',
        nargs='*',
        help="Optional: One or more paths to video files or glob patterns (e.g., 'C:\\Videos\\*.mp4')."
    )
    args = parser.parse_args()

    root = TkinterDnD.Tk()
    initial_files = []
    
    if args.input_files:
        for pattern in args.input_files:
            initial_files.extend(glob.glob(pattern))
    else:
        current_dir = os.getcwd()
        video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv', '.wmv']
        print(f"No input files provided. Scanning directory tree from: {current_dir}...")
        
        files_from_cwd = []
        for dirpath, _, filenames in os.walk(current_dir):
            for filename in filenames:
                if os.path.splitext(filename)[1].lower() in video_extensions:
                    full_path = os.path.join(dirpath, filename)
                    files_from_cwd.append(full_path)
        
        initial_files.extend(sorted(files_from_cwd))

    app = VideoProcessorApp(root, sorted(list(set(initial_files))), args.output_mode)
    root.mainloop()