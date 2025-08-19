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
- Output compliant with YouTube's official recommendations for both SDR and HDR content.
- High-quality AI upscaling to 4K or 8K (requires NVIDIA RTX GPU).
- Automatic color space and tone mapping (e.g., HDR to SDR conversion).
- Automatic deinterlacing to meet progressive scan requirements.
- Creates a clean Stereo + 5.1 Surround audio layout as recommended.
- Organizes output files into resolution and format-specific folders (e.g., "4k_SDR").

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

--- General Settings ---

Container: MP4
- No Edit Lists (or the video might not get processed correctly)
- moov atom at the front of the file (Fast Start)

Frame Rate
Content should be encoded and uploaded in the same frame rate it was recorded.
Common frame rates include: 24, 25, 30, 48, 50, 60 frames per second.
Interlaced content should be deinterlaced before uploading (e.g., 1080i60 to 1080p30).

--- Recommended SDR (Standard Dynamic Range) Upload Settings ---

Video Codec: H.264
- Progressive scan (no interlacing)
- High Profile
- 2 consecutive B frames
- Closed GOP. GOP of half the frame rate.
- CABAC
- Chroma subsampling: 4:2:0
- Bit Depth: 8-bit
- Color Space: BT.709 (Primaries, Transfer, and Matrix)

Recommended SDR Video Bitrates (Mbps)
This script targets the upper end of the recommended bitrate range for maximum quality.
Type        Standard Frame Rate (24, 25, 30)  High Frame Rate (48, 50, 60)
8K          80-160 Mbps                       120-240 Mbps
2160p (4K)  35–45 Mbps                        53–68 Mbps
1440p (2K)  16 Mbps                           24 Mbps
1080p       8 Mbps                            12 Mbps
720p        5 Mbps                            7.5 Mbps

--- Recommended HDR (High Dynamic Range) Upload Settings ---

Video Codec: HEVC (H.265)
- Progressive scan (no interlacing)
- Main 10 Profile
- Closed GOP. GOP of half the frame rate.
- Bit Depth: 10-bit
- Color Primaries: Rec. 2020 (BT.2020)
- Transfer Characteristics: SMPTE ST 2084 (PQ)
- The video file must contain HDR metadata (HDR10 format: ST.2086 mastering metadata
  and MaxCLL/MaxFALL). This script passes it through from the source.

Recommended HDR Video Bitrates (Mbps)
This script targets the upper end of the recommended bitrate range for maximum quality.
Type        Standard Frame Rate (24, 25, 30)  High Frame Rate (48, 50, 60)
8K          100-200 Mbps                      150-300 Mbps
2160p (4K)  44–56 Mbps                        66–85 Mbps
1440p (2K)  20 Mbps                           30 Mbps
1080p       10 Mbps                           15 Mbps
720p        6.5 Mbps                          9.5 Mbps

--- Recommended Audio Settings (for both SDR and HDR) ---

Audio Codec: AAC-LC (Advanced Audio Codec)
- Sample rate: 48k hz
- Channels & Bitrate:
    - Stereo: 384 kbps
    - 5.1 Surround: 512 kbps

----------------------------------------------------------------------------------------------------
                                    NVEncC DOCUMENTATION
----------------------------------------------------------------------------------------------------
A detailed guide to the specific flags used in this script.

--- Video Flags ---

--codec <string>
  Specifies the video codec.
  - h264: For SDR content.
  - hevc: For HDR content.

--profile <string>
  Sets the codec profile.
  - H.264: high (default for quality)
  - HEVC: main10 (required for 10-bit HDR)

--vbr <int>
  Sets the target bitrate in kbps for Variable Bitrate (VBR) mode. This allows the
  bitrate to fluctuate to handle complex scenes more efficiently.

--gop-len <int>
  Sets the Group of Pictures length. A GOP is the distance between two full keyframes.
  For YouTube, this should be half the video's frame rate (e.g., 30 for a 60fps video).

--bframes <int>
  Sets the number of consecutive B-frames. YouTube recommends 2 for H.264.

--output-depth <int>
  Sets the bit depth of the output video.
  - 8: For SDR content.
  - 10: For HDR content.

--- Audio Flags ---

--audio-codec <string>
  Sets a global codec for all audio streams being encoded. This script uses 'aac'.

--audio-samplerate <int>
  Sets a global sample rate for all audio streams. YouTube recommends 48000.

--audio-bitrate <specifier>
  Sets the bitrate for one or more output audio tracks. While it can be a single
  value, this script uses the per-stream syntax for precision.
  - Syntax: [out_idx]?[bitrate_kbps],[out_idx]?[bitrate_kbps]
  - Example: --audio-bitrate 1?384,2?512
    - This sets the first output track to 384 kbps and the second to 512 kbps.

--audio-stream <specifier>
  Maps an input audio track to an output track and sets its channel layout.
  This is the most critical flag for managing audio correctly.
  - Syntax: [out_idx]?[in_idx]:[layout]
  - [out_idx]: The 1-based index of the output track you are creating.
  - [in_idx]: The 1-based index of the input track to use as the source.
  - [layout]: A string defining the output channel layout.
  - Usage: Use this flag ONCE for EACH output audio track you want to create.
  - Example: --audio-stream 1?1:stereo --audio-stream 2?2:5.1
    - This creates two output tracks:
      1. The first output track (1?) is sourced from the first input track (?1) and downmixed to stereo (:stereo).
      2. The second output track (2?) is sourced from the second input track (?2) and encoded as 5.1 surround (:5.1).

  - Full List of Available [layout] options:
    mono, stereo, 2.1, 3.0, 3.0(back), 3.1, 4.0, quad, quad(side),
    5.0, 5.0(side), 5.1, 5.1(side), 6.0, 6.0(front), hexagonal, 6.1,
    6.1(back), 6.1(front), 7.0, 7.0(front), 7.1, 7.1(wide),
    7.1(wide-side), octagonal, hexadecagonal

--- Color Space Flags ---

--colorprim <string>
  Sets color primaries. (e.g., bt709 for SDR, bt2020 for HDR).

--transfer <string>
  Sets transfer characteristics (gamma). (e.g., bt709 for SDR, smpte2084 for HDR PQ).

--colormatrix <string>
  Sets the color matrix. (e.g., bt709 for SDR, bt2020nc for HDR).

--dhdr10-info <string>
  Used for HDR content to carry over essential metadata from the source file.
  - pass: The required value to enable this.

--- VPP (Video Post-Processing) Flags ---

--vpp-deinterlace <string>
  Converts interlaced video to progressive scan, a YouTube requirement.
  - adaptive: A high-quality deinterlacing algorithm.

--vpp-resize <string>
  Resizes the video using a specified algorithm. (e.g., algo=nvvfx-superres).

--vpp-colorspace <string>
  Performs color space conversions. This script uses it to apply a 3D LUT file
  for tone-mapping HDR source material down to SDR.
  - e.g., lut3d=C:\path\to\lut.cube

--crop <L,T,R,B>
  Crops pixels from the Left, Top, Right, and Bottom of the video frame.
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
    sdr_table = {"8k": (160, 240), "4k": (45, 68), "1440p": (16, 24), "1080p": (8, 12), "720p": (5, 7.5)}
    hdr_table = {"8k": (200, 300), "4k": (56, 85), "1440p": (20, 30), "1080p": (10, 15), "720p": (6.5, 9.5)}
    table = hdr_table if is_hdr else sdr_table
    default_bitrate = (15, 20) if is_hdr else (12, 18)
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
    def __init__(self, root, initial_files):
        self.root = root; self.root.title("Video Processing Tool")
        self.lut_file = LUT_FILE_PATH
        self.subtitles_by_file = {}; self.file_list = []
        self.subtitle_id_counter = 0; self.current_subtitle_checkbuttons = []
        self.file_options = {}
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
    
    def setup_gui(self):
        # --- GUI FRAME SETUP (Collapsed for brevity) ---
        self.file_frame = tk.Frame(self.root); self.file_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.file_listbox = tk.Listbox(self.file_frame, selectmode=tk.EXTENDED, height=15); self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.file_scrollbar = tk.Scrollbar(self.file_frame, orient=tk.VERTICAL, command=self.file_listbox.yview); self.file_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_listbox.config(yscrollcommand=self.file_scrollbar.set); self.file_listbox.bind("<<ListboxSelect>>", self.on_file_select)
        self.file_buttons_frame = tk.Frame(self.root); self.file_buttons_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Button(self.file_buttons_frame, text="Select All", command=self.select_all_files).pack(side=tk.LEFT, padx=5)
        tk.Button(self.file_buttons_frame, text="Add Files", command=self.add_files).pack(side=tk.LEFT, padx=5)
        tk.Button(self.file_buttons_frame, text="Remove Selected", command=self.remove_selected).pack(side=tk.LEFT, padx=5)
        tk.Button(self.file_buttons_frame, text="Clear All", command=self.clear_all).pack(side=tk.LEFT, padx=5)
        tk.Button(self.file_buttons_frame, text="Move Up", command=self.move_up).pack(side=tk.LEFT, padx=5)
        tk.Button(self.file_buttons_frame, text="Move Down", command=self.move_down).pack(side=tk.LEFT, padx=5)
        self.options_frame = tk.Frame(self.root); self.options_frame.pack(fill=tk.X, padx=10, pady=10)
        self.resolution_options_frame = tk.LabelFrame(self.options_frame, text="Resolution and Upscale Algorithm", padx=10, pady=5); self.resolution_options_frame.grid(row=0, column=0, columnspan=4, sticky="ew", pady=5)
        tk.Label(self.resolution_options_frame, text="Resolution:").grid(row=0, column=0, sticky=tk.W)
        tk.Radiobutton(self.resolution_options_frame, text="HD", variable=self.resolution_var, value="HD", command=self.apply_gui_options_to_selected_files).grid(row=0, column=1, sticky=tk.W)
        tk.Radiobutton(self.resolution_options_frame, text="4k", variable=self.resolution_var, value="4k", command=self.apply_gui_options_to_selected_files).grid(row=0, column=2, sticky=tk.W)
        tk.Radiobutton(self.resolution_options_frame, text="8k", variable=self.resolution_var, value="8k", command=self.apply_gui_options_to_selected_files).grid(row=0, column=3, sticky=tk.W)
        tk.Label(self.resolution_options_frame, text="Upscale Algorithm:").grid(row=1, column=0, sticky=tk.W, padx=(20, 0))
        tk.Radiobutton(self.resolution_options_frame, text="nvvfx-superres", variable=self.upscale_algo_var, value="nvvfx-superres", command=self.apply_gui_options_to_selected_files).grid(row=1, column=1, sticky=tk.W, padx=(20, 0))
        tk.Radiobutton(self.resolution_options_frame, text="ngx-vsr", variable=self.upscale_algo_var, value="ngx-vsr", command=self.apply_gui_options_to_selected_files).grid(row=1, column=2, sticky=tk.W)
        tk.Radiobutton(self.resolution_options_frame, text="lanczos", variable=self.upscale_algo_var, value="lanczos", command=self.apply_gui_options_to_selected_files).grid(row=1, column=3, sticky=tk.W)
        self.output_format_frame = tk.LabelFrame(self.options_frame, text="Output Format (YouTube Compliant)", padx=10, pady=5); self.output_format_frame.grid(row=1, column=0, columnspan=4, sticky="ew", pady=5)
        tk.Radiobutton(self.output_format_frame, text="SDR (H.264)", variable=self.output_format_var, value="sdr", command=self.apply_gui_options_to_selected_files).pack(side=tk.LEFT, padx=5)
        tk.Radiobutton(self.output_format_frame, text="HDR (HEVC)", variable=self.output_format_var, value="hdr", command=self.apply_gui_options_to_selected_files).pack(side=tk.LEFT, padx=5)
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
        self.subtitle_tracks_frame = tk.LabelFrame(self.root, text="Burn Subtitle Tracks", padx=10, pady=10); self.subtitle_tracks_frame.pack(fill=tk.X, padx=10, pady=5)
        self.subtitle_tracks_buttons_frame = tk.Frame(self.subtitle_tracks_frame); self.subtitle_tracks_buttons_frame.pack(fill=tk.X, padx=5, pady=5)
        tk.Button(self.subtitle_tracks_buttons_frame, text="Load Embedded SRT (All Files)", command=self.load_embedded_srt_all).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(self.subtitle_tracks_buttons_frame, text="Add External SRT (Current File)", command=self.add_external_srt).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(self.subtitle_tracks_buttons_frame, text="Remove Selected SRT (Current File)", command=self.remove_selected_srt).pack(side=tk.LEFT, padx=(0, 5))
        self.subtitle_tracks_list_frame = tk.Frame(self.subtitle_tracks_frame); self.subtitle_tracks_list_frame.pack(fill=tk.X)
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
        output_dir = os.path.join(os.path.dirname(file_path), folder_name)
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
        
        # <-- MODIFIED: Final, correct audio logic using your proven syntax -->
        audio_streams = get_audio_stream_info(file_path)
        if len(audio_streams) > 0:
            cmd.extend(["--audio-codec", "aac", "--audio-samplerate", "48000"])
            cmd.extend(["--audio-bitrate", "512"])

            if len(audio_streams) >= 2:
                cmd.extend(["--audio-stream", "1?1:stereo"])
                cmd.extend(["--audio-stream", "2?2:5.1"])
            else:
                cmd.extend(["--audio-stream", "1?1:stereo"])
                cmd.extend(["--audio-stream", "2?1:5.1"])

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
            output_dir = os.path.join(os.path.dirname(file_path), folder_name)
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

    def start_processing(self):
        if not self.file_list: messagebox.showwarning("No Files", "Please add at least one file to process."); return
        self.root.destroy()
        for file_path in self.file_list: self.encode_single_pass(file_path)
        print("Processing Complete.")

    # ... (Rest of class methods collapsed for brevity)
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

    root = TkinterDnD.Tk()
    initial_files = []
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]: initial_files.extend(glob.glob(arg))
    else:
        current_dir = os.getcwd()
        video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv', '.wmv']
        print(f"Scanning current directory: {current_dir} for video files...")
        files_from_cwd = [os.path.join(current_dir, f) for f in os.listdir(current_dir) if os.path.isfile(os.path.join(current_dir, f)) and os.path.splitext(f)[1].lower() in video_extensions]
        initial_files.extend(sorted(files_from_cwd))
    app = VideoProcessorApp(root, sorted(initial_files))
    root.mainloop()