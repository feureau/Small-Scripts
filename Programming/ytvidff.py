r"""
====================================================================================================
                            YouTube Batch Video Processing Tool
====================================================================================================

====================================================================================================
                                       SCRIPT DOCUMENTATION
====================================================================================================

----------------------------------------------------------------------------------------------------
                                    PART 1: HIGH-LEVEL OVERVIEW
----------------------------------------------------------------------------------------------------

PURPOSE:
This script provides a Graphical User Interface (GUI) to batch process video files,
optimizing them for upload to YouTube and other social media platforms. It offers full control
over output orientation, aspect ratio handling, advanced subtitle burning, and audio normalization
for both horizontal and vertical formats. It functions as a powerful front-end for a highly
optimized, fully hardware-accelerated, hybrid GPU/CPU FFmpeg pipeline that uses NVIDIA's CUDA.

CORE FEATURES:
  - Job-Based Batch Processing: Add the same video multiple times to create different output
    versions. Each processing task is managed as a separate "job" with its own settings.
  - Automatic Subtitle Discovery: Automatically finds all sidecar SRT files that match a video's
    basename (e.g., `video.en.srt`, `video-id.srt`) and creates a distinct processing job for each.
  - Conditional "No Subtitle" Job: A job without subtitles is only created by default if no
    matching sidecar subtitle files are found for a given video.
  - Duplicate Jobs on Demand: A "Duplicate" button allows for instant cloning of any job,
    making it easy to create A/B tests (e.g., SDR vs HDR) or other variations.
  - Optimized Hardware Acceleration: Leverages NVIDIA's CUDA for the entire video pipeline,
    from decoding to scaling and encoding. For filters that are CPU-only (like subtitles or
    audio processing), it intelligently and efficiently transfers frames between the GPU and CPU.
  - Full Geometric Control: Independently configure output orientation (Horizontal, Vertical,
    or both) and aspect ratio handling (Crop, Pad, Stretch) for each job.
  - Advanced Subtitle Burning: Generates a temporary, fully styled Advanced SubStation Alpha
    (.ass) file to ensure subtitles are rendered with maximum legibility and positioned correctly,
    even within padded black bars. A complete styling suite is provided.
  - Multi-Track Audio Normalization: Implements FFmpeg's sophisticated 'loudnorm' filter,
    acting as an all-in-one normalizer, compressor, and true-peak limiter. It brings audio to
    a consistent, broadcast-ready level and correctly processes ALL audio tracks from the
    source file, preserving multi-channel and multi-language setups.
  - Format and Quality Flexibility: Output to standard SDR (H.264) or HDR (HEVC/H.265) with
    automatic bitrate selection tailored to YouTube's recommendations. An expert option allows
    for manual bitrate override on any job.
  - Self-Contained & Fully Documented: This documentation is embedded directly within the script.

----------------------------------------------------------------------------------------------------
                        PART 2: DESIGN PHILOSOPHY & TECHNICAL RATIONALE
----------------------------------------------------------------------------------------------------
This script is the result of an iterative, empirical development process. The current design was
forged through extensive testing and debugging to overcome the specific, often non-obvious,
limitations of various command-line encoders. The primary goal of the current design is
**stability, performance, and predictability** above all else.

1.  **THE JOB-BASED ARCHITECTURE (v5.0+)**
    The script's core logic has been refactored from a file-centric to a job-centric model.
    Previously, there was a one-to-one relationship between a video file and its settings.
    The new architecture is built around a list of "processing jobs," where each job is an
    independent task with its own source video, subtitle file (optional), and a complete set
    of processing options. This allows the same video to be queued multiple times with
    different settings, or for different subtitle languages, all within a single batch.

2.  **THE ENCODING BACKEND: A ROBUST, FULLY HARDWARE-ACCELERATED PIPELINE (v4.7+)**
    The script's core uses a modern, fully hardware-accelerated FFmpeg pipeline. This ensures
    maximum performance by keeping video frames on the GPU for as long as possible.

    -   **The Problem:** Processing modern video formats (like 10-bit AV1) with GPU filters
        is not straightforward. Simply using `-hwaccel cuda` is not enough. FFmpeg may still
        decode the video on the CPU, leading to "Impossible to convert between formats" errors
        when trying to link a CPU-based frame to a GPU-based filter like `scale_cuda`.

    -   **The Solution: A True Hardware-First Approach:** The script now implements a complete,
        unbroken hardware pipeline by specifying the entire chain at the command line:
        1.  **Specify Decoder:** The command begins by explicitly selecting the correct CUDA
            decoder for the input file's codec (`-c:v av1_cuvid`, `-c:v h264_cuvid`, etc.).
            This is done *before* the `-i` input flag.
        2.  **Force GPU Output:** The crucial `-hwaccel_output_format cuda` flag is added.
            This instructs the CUDA decoder to keep the decoded frames in the GPU's VRAM.
        3.  **Process on GPU:** GPU-native filters like `scale_cuda` operate on the frames
            without any data transfer.
        4.  **Encode on GPU:** The fully processed frames are sent directly to the `h264_nvenc`
            or `hevc_nvenc` encoder.

    -   **Critical Implementation Detail: The Hybrid CPU "Detour"**
        -   For operations that do not have CUDA-accelerated filters (e.g., `subtitles`, `lut3d`),
            the script intelligently creates a "detour":
          1. **`hwdownload,format=nv12`**: Efficiently copies a video frame from GPU to CPU memory.
          2. **CPU Filters**: The `subtitles`, `lut3d`, etc., filters are applied on the CPU.
          3. **`format=nv12,hwupload_cuda`**: The processed frame is copied *back* to the GPU.
        -   This "hwdownload/hwupload sandwich" is NVIDIA's official best practice.

3.  **SUBTITLE HANDLING: HIERARCHICAL BASENAME MATCHING & ON-THE-FLY SRT-TO-ASS CONVERSION**
    -   **Discovery (v5.0+):** The script automatically associates subtitle files with video files.
        An SRT file is considered a match if its name **starts with** the video's complete
        basename, followed by a common separator (`.`, ` `, `-`, `_`) or the end of the string.
        This robustly handles various naming conventions (e.g., `video.en.srt`, `video - id.srt`).
    -   **Method:** The script dynamically generates a temporary, fully styled Advanced SubStation
        Alpha (`.ass`) file from the selected SRT.
    -   **Integration:** The `subtitles` filter is placed in the CPU portion of the hybrid
        pipeline. This allows the text to be rendered *after* any padding has been applied,
        ensuring subtitles appear correctly inside the black bars.

4.  **AUDIO PROCESSING: BROADCAST-STANDARD NORMALIZATION (v4.8+)**
    The optional audio normalization feature uses FFmpeg's `loudnorm` filter, which adheres
    to the modern EBU R128 standard for perceived loudness.
    -   **Method:** This is a sophisticated, single-filter solution that acts as a combined
        normalizer, compressor, and true-peak limiter.
    -   **Multi-Track Handling (v4.8.1+):** The script correctly handles files with multiple
        audio tracks. When normalization is enabled, it intelligently applies the `loudnorm`
        filter to *each audio track individually*, preserving the original channel layout.

----------------------------------------------------------------------------------------------------
                            PART 3: CODE ANNOTATION & EXPLANATION
----------------------------------------------------------------------------------------------------
(Code annotation section is unchanged and remains accurate)
----------------------------------------------------------------------------------------------------
                                        PART 4: CHANGELOG
----------------------------------------------------------------------------------------------------
v5.1.0 (2025-10-22) - Gemini/User Collaboration
  - BEHAVIOR CHANGE: Modified the job discovery logic. The script now only creates a "[No Subtitles]"
    job for a video if no matching sidecar .srt files are found. If subtitles are present, only
    jobs with subtitles will be created by default.

v5.0.1 (2025-10-22) - Gemini/User Collaboration
  - FIX: Resolved a critical file overwriting bug where a job with no subtitles and a job
    with an exact-match subtitle (e.g., `video.srt`) would generate the same output filename.
  - REFACTOR: Modified the filename generation logic. Jobs with no subtitles now have a `_NoSub`
    suffix appended to their output filename, guaranteeing uniqueness.

v5.0.0 (2025-10-22) - Gemini/User Collaboration
  - ARCHITECTURE: Replaced the file-based processing model with a more flexible "job-based"
    architecture. The core data structure is now a list of "processing jobs," where each job
    is a unique task with its own source files and settings.
  - FEATURE: The same video file can now be added to the queue multiple times to be processed
    with different settings in the same batch.
  - FEATURE: Implemented "Hierarchical Basename Matching" for subtitles. The script now
    automatically discovers ALL related SRT files for a video (e.g., `video.en.srt`,
    `video - id.srt`) and creates a separate processing job for each one.
  - FEATURE: A "No Subtitles" job is also automatically created for each video, allowing for
    encodes without burned-in text.
  - FEATURE: Added a "Duplicate Selected" button to the GUI. This allows for one-click
    cloning of any selected job(s), making it easy to create variations.
  - GUI: The file listbox is now a job list, with entries clearly labeled with their
    associated subtitle file (e.g., "MyVideo.mp4 [Sub: id.srt]").
  - REFACTOR: Overhauled all file handling, GUI state management, and processing logic to
    support the new job-based model. Removed `self.file_list` and `self.file_options`.
  - REFACTOR: The `detect_subtitle_tracks` function has been removed and its logic replaced
    by the new, more powerful discovery mechanism.

v4.9.0 (2025-10-21) - Gemini/User Collaboration
  - FEATURE: Added a manual bitrate override option.
  - GUI: The bitrate box is read-only by default and displays the automatically calculated bitrate.
  - REFACTOR: Modified the FFmpeg command builder to use the manual bitrate if the override is active.

(Older changelog entries remain the same)
----------------------------------------------------------------------------------------------------
"""



import os
import subprocess
import shutil
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, font, colorchooser
from tkinterdnd2 import TkinterDnD, DND_FILES
import unicodedata
from ftfy import fix_text
import threading
import sys
import math
import argparse
import tempfile
import re
import copy
import time

# ----------------------------------------------------------------------------------------------------
#                                     --- USER CONFIGURATION ---
# ----------------------------------------------------------------------------------------------------
LUT_FILE_PATH = r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\LUT\NBCU\5-NBCU_PQ2SDR_DL_RESOLVE17-VRT_v1.2.cube"
DEFAULT_RESOLUTION = "4k"
DEFAULT_UPSCALE_ALGO = "lanczos"
DEFAULT_OUTPUT_FORMAT = "sdr"
DEFAULT_ORIENTATION = "original"
DEFAULT_ASPECT_MODE = "crop"
DEFAULT_HORIZONTAL_ASPECT = "16:9"
DEFAULT_VERTICAL_ASPECT = "4:5"
DEFAULT_FRUC = False
DEFAULT_FRUC_FPS = "60"
DEFAULT_BURN_SUBTITLES = False

# --- Audio normalization settings ---
DEFAULT_NORMALIZE_AUDIO = False
DEFAULT_LOUDNESS_TARGET = "-9"
DEFAULT_LOUDNESS_RANGE = "7"
DEFAULT_TRUE_PEAK = "-1.0"

# --- Default subtitle style settings ---
DEFAULT_SUBTITLE_FONT = "Impact"
DEFAULT_SUBTITLE_FONT_SIZE = "64"
DEFAULT_SUBTITLE_ALIGNMENT = "bottom"
DEFAULT_SUBTITLE_BOLD = True
DEFAULT_SUBTITLE_ITALIC = False
DEFAULT_SUBTITLE_PRIMARY_COLOR = "#FFAA00"  # Vibrant Orange-Yellow
DEFAULT_SUBTITLE_OUTLINE_COLOR = "#000000" # Black
DEFAULT_SUBTITLE_SHADOW_COLOR = "#202020"  # Gray
DEFAULT_SUBTITLE_MARGIN_V = "65"

# --- Advanced ASS (Advanced SubStation Alpha) Style Overrides ---
DEFAULT_SUBTITLE_BORDERSTYLE = "1"      # 1 = Outline + Drop Shadow, 3 = Opaque Box.
DEFAULT_SUBTITLE_OUTLINE_WIDTH = "12"    # Width of the text border in pixels.
DEFAULT_SUBTITLE_SHADOW_DEPTH = "6"     # Depth of the drop shadow in pixels.
DEFAULT_SUBTITLE_MARGIN_L = "10"        # Left margin in pixels.
DEFAULT_SUBTITLE_MARGIN_R = "10"        # Right margin in pixels.
DEFAULT_SUBTITLE_ENCODING = "1"         # ASS font encoding. 1 is the standard for Unicode.
DEFAULT_SUBTITLE_SECONDARY_COLOR = "&H000000FF" # Color for karaoke effects.
DEFAULT_SUBTITLE_UNDERLINE = "0"        # 0 = Off, -1 = On.
DEFAULT_SUBTITLE_STRIKEOUT = "0"        # 0 = Off, -1 = On.
DEFAULT_SUBTITLE_SCALE_X = "100"        # Horizontal text scaling in percent.
DEFAULT_SUBTITLE_SCALE_Y = "100"        # Vertical text scaling in percent.
DEFAULT_SUBTITLE_SPACING = "0"          # Extra space between characters in pixels.
DEFAULT_SUBTITLE_ANGLE = "0"            # Text rotation in degrees.


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

def hex_to_libass_color(hex_color):
    if not hex_color or not hex_color.startswith("#"): return "&H00000000"
    hex_val = hex_color.lstrip('#')
    if len(hex_val) != 6: return "&H00000000"
    r, g, b = tuple(int(hex_val[i:i+2], 16) for i in (0, 2, 4))
    return f"&H00{b:02X}{g:02X}{r:02X}"

def create_temporary_ass_file(srt_path, options):
    try:
        with open(srt_path, 'r', encoding='utf-8', errors='replace') as f:
            srt_content = f.read()
    except Exception as e:
        print(f"[ERROR] Could not read SRT file {srt_path}: {e}")
        return None

    style_name = "CustomStyle"
    font_name = options.get('subtitle_font', DEFAULT_SUBTITLE_FONT)
    font_size = options.get('subtitle_font_size', DEFAULT_SUBTITLE_FONT_SIZE)
    primary_color = hex_to_libass_color(options.get('subtitle_primary_color', DEFAULT_SUBTITLE_PRIMARY_COLOR))
    outline_color = hex_to_libass_color(options.get('subtitle_outline_color', DEFAULT_SUBTITLE_OUTLINE_COLOR))
    shadow_color = hex_to_libass_color(options.get('subtitle_shadow_color', DEFAULT_SUBTITLE_SHADOW_COLOR))
    bold_flag = "-1" if options.get('subtitle_bold', False) else "0"
    italic_flag = "-1" if options.get('subtitle_italic', False) else "0"
    margin_v = options.get('subtitle_margin_v', DEFAULT_SUBTITLE_MARGIN_V)
    
    align_map = {"top": 8, "middle": 5, "bottom": 2}
    alignment = align_map.get(options.get('subtitle_alignment', 'bottom'), 2)
    
    header = f"""[Script Info]
Title: Temporary Subtitle File
ScriptType: v4.00+
WrapStyle: 0
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: {style_name},{font_name},{font_size},{primary_color},{DEFAULT_SUBTITLE_SECONDARY_COLOR},{outline_color},{shadow_color},{bold_flag},{italic_flag},{DEFAULT_SUBTITLE_UNDERLINE},{DEFAULT_SUBTITLE_STRIKEOUT},{DEFAULT_SUBTITLE_SCALE_X},{DEFAULT_SUBTITLE_SCALE_Y},{DEFAULT_SUBTITLE_SPACING},{DEFAULT_SUBTITLE_ANGLE},{DEFAULT_SUBTITLE_BORDERSTYLE},{DEFAULT_SUBTITLE_OUTLINE_WIDTH},{DEFAULT_SUBTITLE_SHADOW_DEPTH},{alignment},{DEFAULT_SUBTITLE_MARGIN_L},{DEFAULT_SUBTITLE_MARGIN_R},{margin_v},{DEFAULT_SUBTITLE_ENCODING}

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    
    dialogue_lines = []
    srt_blocks = re.findall(r'(\d+)\s*\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\s*\n(.*?)(?=\n\n|\Z)', srt_content, re.DOTALL)

    for block in srt_blocks:
        _, start_time, end_time, text = block
        start_ass = start_time.replace(',', '.')[:-1]
        end_ass = end_time.replace(',', '.')[:-1]
        text_ass = text.strip().replace('\n', '\\N')
        dialogue_lines.append(f"Dialogue: 0,{start_ass},{end_ass},{style_name},,0,0,0,,  {text_ass}")

    full_ass_content = header + "\n".join(dialogue_lines)

    try:
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.ass', encoding='utf-8')
        temp_file.write(full_ass_content)
        temp_file.close()
        return temp_file.name
    except Exception as e:
        print(f"[ERROR] Could not create temporary ASS file: {e}")
        return None

def get_video_info(file_path):
    cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=pix_fmt,r_frame_rate,height,width,color_transfer,color_primaries,codec_name", "-of", "json", file_path]
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
        codec_name = data.get("codec_name", "h264")
        return {"bit_depth": bit_depth, "framerate": framerate, "height": height, "width": width, "is_hdr": is_hdr, "codec_name": codec_name}
    except Exception as e:
        print(f"[WARN] Could not get video info for {file_path}, using defaults: {e}")
        return {"bit_depth": 8, "framerate": 30.0, "height": 1080, "width": 1920, "is_hdr": False, "codec_name": "h264"}

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
        self.processing_jobs = []

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
        self.generate_log_var = tk.BooleanVar(value=False)
        self.burn_subtitles_var = tk.BooleanVar(value=DEFAULT_BURN_SUBTITLES)
        
        self.override_bitrate_var = tk.BooleanVar(value=False)
        self.manual_bitrate_var = tk.StringVar()

        self.normalize_audio_var = tk.BooleanVar(value=DEFAULT_NORMALIZE_AUDIO)
        self.loudness_target_var = tk.StringVar(value=DEFAULT_LOUDNESS_TARGET)
        self.loudness_range_var = tk.StringVar(value=DEFAULT_LOUDNESS_RANGE)
        self.true_peak_var = tk.StringVar(value=DEFAULT_TRUE_PEAK)
        
        self.subtitle_font_var = tk.StringVar(value=DEFAULT_SUBTITLE_FONT)
        self.subtitle_font_size_var = tk.StringVar(value=DEFAULT_SUBTITLE_FONT_SIZE)
        self.subtitle_alignment_var = tk.StringVar(value=DEFAULT_SUBTITLE_ALIGNMENT)
        self.subtitle_bold_var = tk.BooleanVar(value=DEFAULT_SUBTITLE_BOLD)
        self.subtitle_italic_var = tk.BooleanVar(value=DEFAULT_SUBTITLE_ITALIC)
        self.subtitle_primary_color_var = tk.StringVar(value=DEFAULT_SUBTITLE_PRIMARY_COLOR)
        self.subtitle_outline_color_var = tk.StringVar(value=DEFAULT_SUBTITLE_OUTLINE_COLOR)
        self.subtitle_shadow_color_var = tk.StringVar(value=DEFAULT_SUBTITLE_SHADOW_COLOR)
        self.subtitle_margin_v_var = tk.StringVar(value=DEFAULT_SUBTITLE_MARGIN_V)

        self.root.drop_target_register(DND_FILES); self.root.dnd_bind("<<Drop>>", self.handle_file_drop)
        
        self.setup_gui()
        self.add_video_files_and_discover_jobs(initial_files)

    def setup_gui(self):
        self.root.columnconfigure(0, weight=1); self.root.columnconfigure(1, weight=1)
        main_frame = tk.Frame(self.root); main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        left_frame = tk.Frame(main_frame); left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        right_frame = tk.Frame(main_frame); right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))

        file_group = tk.LabelFrame(left_frame, text="Processing Jobs", padx=10, pady=10); file_group.pack(fill=tk.BOTH, expand=True)
        listbox_frame = tk.Frame(file_group); listbox_frame.pack(fill=tk.BOTH, expand=True)
        self.job_listbox = tk.Listbox(listbox_frame, selectmode=tk.EXTENDED); self.job_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.job_scrollbar = tk.Scrollbar(listbox_frame, orient=tk.VERTICAL, command=self.job_listbox.yview); self.job_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.job_listbox.config(yscrollcommand=self.job_scrollbar.set); self.job_listbox.bind("<<ListboxSelect>>", self.on_file_select)
        
        selection_buttons_frame = tk.Frame(file_group); selection_buttons_frame.pack(fill=tk.X, pady=(5, 0))
        tk.Button(selection_buttons_frame, text="Select All", command=self.select_all_files).pack(side=tk.LEFT)
        tk.Button(selection_buttons_frame, text="Clear Selection", command=self.clear_file_selection).pack(side=tk.LEFT, padx=5)

        file_buttons_frame = tk.Frame(file_group); file_buttons_frame.pack(fill=tk.X, pady=(5, 0))
        tk.Button(file_buttons_frame, text="Add Files...", command=self.add_files).pack(side=tk.LEFT, padx=(0,5))
        tk.Button(file_buttons_frame, text="Remove Selected", command=self.remove_selected).pack(side=tk.LEFT, padx=5)
        tk.Button(file_buttons_frame, text="Duplicate Selected", command=self.duplicate_selected_jobs).pack(side=tk.LEFT, padx=5)
        tk.Button(file_buttons_frame, text="Clear All", command=self.clear_all).pack(side=tk.LEFT, padx=5)

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

        quality_group = tk.LabelFrame(right_frame, text="Format & Quality", padx=10, pady=10); quality_group.pack(fill=tk.X, pady=5)
        resolution_options_frame = tk.Frame(quality_group); resolution_options_frame.pack(fill=tk.X)
        tk.Label(resolution_options_frame, text="Resolution:").pack(side=tk.LEFT, padx=(0,5))
        self.rb_hd = tk.Radiobutton(resolution_options_frame, text="HD", variable=self.resolution_var, value="HD", command=self.apply_gui_options_to_selected_files); self.rb_hd.pack(side=tk.LEFT)
        self.rb_4k = tk.Radiobutton(resolution_options_frame, text="4k", variable=self.resolution_var, value="4k", command=self.apply_gui_options_to_selected_files); self.rb_4k.pack(side=tk.LEFT)
        self.rb_8k = tk.Radiobutton(resolution_options_frame, text="8k", variable=self.resolution_var, value="8k", command=self.apply_gui_options_to_selected_files); self.rb_8k.pack(side=tk.LEFT)
        
        upscale_frame = tk.Frame(quality_group); upscale_frame.pack(fill=tk.X, pady=(5,0))
        tk.Label(upscale_frame, text="Upscale Algo:").pack(side=tk.LEFT, padx=(0,5))
        self.rb_lanczos = tk.Radiobutton(upscale_frame, text="Lanczos (Sharp)", variable=self.upscale_algo_var, value="lanczos", command=self.apply_gui_options_to_selected_files)
        self.rb_lanczos.pack(side=tk.LEFT)
        self.rb_bicubic = tk.Radiobutton(upscale_frame, text="Bicubic (Balanced)", variable=self.upscale_algo_var, value="bicubic", command=self.apply_gui_options_to_selected_files)
        self.rb_bicubic.pack(side=tk.LEFT)
        self.rb_bilinear = tk.Radiobutton(upscale_frame, text="Bilinear (Fast)", variable=self.upscale_algo_var, value="bilinear", command=self.apply_gui_options_to_selected_files)
        self.rb_bilinear.pack(side=tk.LEFT)

        output_format_frame = tk.Frame(quality_group); output_format_frame.pack(fill=tk.X, pady=(5,0))
        tk.Label(output_format_frame, text="Output Format:").pack(side=tk.LEFT, padx=(0,5))
        tk.Radiobutton(output_format_frame, text="SDR", variable=self.output_format_var, value="sdr", command=self.apply_gui_options_to_selected_files).pack(side=tk.LEFT)
        tk.Radiobutton(output_format_frame, text="HDR", variable=self.output_format_var, value="hdr", command=self.apply_gui_options_to_selected_files).pack(side=tk.LEFT)
        tk.Label(output_format_frame, text="Location:").pack(side=tk.LEFT, padx=(15,5))
        tk.Radiobutton(output_format_frame, text="Local", variable=self.output_mode_var, value="local").pack(side=tk.LEFT)
        tk.Radiobutton(output_format_frame, text="Pooled", variable=self.output_mode_var, value="pooled").pack(side=tk.LEFT)

        bitrate_frame = tk.Frame(quality_group); bitrate_frame.pack(fill=tk.X, pady=(5,0))
        tk.Checkbutton(bitrate_frame, text="Override Bitrate", variable=self.override_bitrate_var, command=self._toggle_bitrate_override).pack(side=tk.LEFT)
        self.manual_bitrate_entry = tk.Entry(bitrate_frame, textvariable=self.manual_bitrate_var, width=10, state="disabled")
        self.manual_bitrate_entry.pack(side=tk.LEFT, padx=5)
        self.manual_bitrate_entry.bind("<FocusOut>", self.apply_gui_options_to_selected_files_event)
        tk.Label(bitrate_frame, text="kbps").pack(side=tk.LEFT)

        subtitle_style_group = tk.LabelFrame(right_frame, text="Subtitle Styling", padx=10, pady=10)
        subtitle_style_group.pack(fill=tk.X, pady=5)
        
        font_frame = tk.Frame(subtitle_style_group); font_frame.pack(fill=tk.X, pady=2)
        tk.Label(font_frame, text="Font Family:").pack(side=tk.LEFT, padx=(0, 5))
        self.font_combo = ttk.Combobox(font_frame, textvariable=self.subtitle_font_var, width=20)
        self.font_combo.pack(side=tk.LEFT, padx=5)
        self.font_combo.bind("<<ComboboxSelected>>", self.apply_gui_options_to_selected_files)
        self.populate_fonts()
        tk.Label(font_frame, text="Size:").pack(side=tk.LEFT, padx=(10, 5))
        self.subtitle_font_size_entry = tk.Entry(font_frame, textvariable=self.subtitle_font_size_var, width=5)
        self.subtitle_font_size_entry.pack(side=tk.LEFT)
        self.subtitle_font_size_entry.bind("<FocusOut>", self.apply_gui_options_to_selected_files_event)

        style_frame = tk.Frame(subtitle_style_group); style_frame.pack(fill=tk.X, pady=2)
        tk.Checkbutton(style_frame, text="Bold", variable=self.subtitle_bold_var, command=self.apply_gui_options_to_selected_files).pack(side=tk.LEFT)
        tk.Checkbutton(style_frame, text="Italic", variable=self.subtitle_italic_var, command=self.apply_gui_options_to_selected_files).pack(side=tk.LEFT, padx=10)
        
        align_frame = tk.Frame(subtitle_style_group); align_frame.pack(fill=tk.X, pady=2)
        tk.Label(align_frame, text="Align:").pack(side=tk.LEFT)
        tk.Radiobutton(align_frame, text="Top", variable=self.subtitle_alignment_var, value="top", command=self.apply_gui_options_to_selected_files).pack(side=tk.LEFT)
        tk.Radiobutton(align_frame, text="Middle", variable=self.subtitle_alignment_var, value="middle", command=self.apply_gui_options_to_selected_files).pack(side=tk.LEFT)
        tk.Radiobutton(align_frame, text="Bottom", variable=self.subtitle_alignment_var, value="bottom", command=self.apply_gui_options_to_selected_files).pack(side=tk.LEFT)
        tk.Label(align_frame, text="Vertical Margin (pixels):").pack(side=tk.LEFT, padx=(10, 5))
        self.subtitle_margin_v_entry = tk.Entry(align_frame, textvariable=self.subtitle_margin_v_var, width=5)
        self.subtitle_margin_v_entry.pack(side=tk.LEFT)
        self.subtitle_margin_v_entry.bind("<FocusOut>", self.apply_gui_options_to_selected_files_event)


        color_frame = tk.Frame(subtitle_style_group); color_frame.pack(fill=tk.X, pady=5)
        tk.Label(color_frame, text="Text Color:").pack(side=tk.LEFT)
        self.primary_color_swatch = tk.Label(color_frame, text="    ", bg=self.subtitle_primary_color_var.get(), relief="sunken")
        self.primary_color_swatch.pack(side=tk.LEFT, padx=5)
        tk.Button(color_frame, text="Choose...", command=lambda: self.choose_color(self.subtitle_primary_color_var, self.primary_color_swatch)).pack(side=tk.LEFT)
        tk.Label(color_frame, text="Outline:").pack(side=tk.LEFT, padx=(10, 0))
        self.outline_color_swatch = tk.Label(color_frame, text="    ", bg=self.subtitle_outline_color_var.get(), relief="sunken")
        self.outline_color_swatch.pack(side=tk.LEFT, padx=5)
        tk.Button(color_frame, text="Choose...", command=lambda: self.choose_color(self.subtitle_outline_color_var, self.outline_color_swatch)).pack(side=tk.LEFT)
        tk.Label(color_frame, text="Shadow:").pack(side=tk.LEFT, padx=(10, 0))
        self.shadow_color_swatch = tk.Label(color_frame, text="    ", bg=self.subtitle_shadow_color_var.get(), relief="sunken")
        self.shadow_color_swatch.pack(side=tk.LEFT, padx=5)
        tk.Button(color_frame, text="Choose...", command=lambda: self.choose_color(self.subtitle_shadow_color_var, self.shadow_color_swatch)).pack(side=tk.LEFT)
        
        other_opts_group = tk.LabelFrame(right_frame, text="Other Options", padx=10, pady=10); other_opts_group.pack(fill=tk.X, pady=5)
        tk.Checkbutton(other_opts_group, text="Enable Subtitle Burning", variable=self.burn_subtitles_var, command=self.apply_gui_options_to_selected_files).pack(anchor="w")

        audio_group = tk.LabelFrame(other_opts_group, text="Audio Processing", padx=5, pady=5); audio_group.pack(fill=tk.X, pady=5)
        tk.Checkbutton(audio_group, text="Normalize Audio", variable=self.normalize_audio_var, command=self._toggle_audio_norm_options).pack(anchor="w")
        
        self.audio_norm_frame = tk.Frame(audio_group)
        self.audio_norm_frame.pack(fill=tk.X, padx=(20, 0))
        
        lufs_frame = tk.Frame(self.audio_norm_frame); lufs_frame.pack(fill=tk.X, pady=1)
        tk.Label(lufs_frame, text="Loudness Target (LUFS):").pack(side=tk.LEFT)
        self.loudness_target_entry = tk.Entry(lufs_frame, textvariable=self.loudness_target_var, width=6)
        self.loudness_target_entry.pack(side=tk.LEFT, padx=5)
        self.loudness_target_entry.bind("<FocusOut>", self.apply_gui_options_to_selected_files_event)
        
        lra_frame = tk.Frame(self.audio_norm_frame); lra_frame.pack(fill=tk.X, pady=1)
        tk.Label(lra_frame, text="Loudness Range (LRA):   ").pack(side=tk.LEFT)
        self.loudness_range_entry = tk.Entry(lra_frame, textvariable=self.loudness_range_var, width=6)
        self.loudness_range_entry.pack(side=tk.LEFT, padx=5)
        self.loudness_range_entry.bind("<FocusOut>", self.apply_gui_options_to_selected_files_event)
        
        peak_frame = tk.Frame(self.audio_norm_frame); peak_frame.pack(fill=tk.X, pady=1)
        tk.Label(peak_frame, text="True Peak (dBTP):            ").pack(side=tk.LEFT)
        self.true_peak_entry = tk.Entry(peak_frame, textvariable=self.true_peak_var, width=6)
        self.true_peak_entry.pack(side=tk.LEFT, padx=5)
        self.true_peak_entry.bind("<FocusOut>", self.apply_gui_options_to_selected_files_event)
        
        fruc_frame = tk.Frame(other_opts_group); fruc_frame.pack(fill=tk.X, pady=(5,0))
        tk.Checkbutton(fruc_frame, text="Enable FRUC", variable=self.fruc_var, command=lambda: [self.toggle_fruc_fps(), self.apply_gui_options_to_selected_files()]).pack(side=tk.LEFT)
        tk.Label(fruc_frame, text="FRUC FPS:").pack(side=tk.LEFT, padx=(5,5))
        self.fruc_fps_entry = tk.Entry(fruc_frame, textvariable=self.fruc_fps_var, width=5, state="disabled"); self.fruc_fps_entry.pack(side=tk.LEFT)
        self.fruc_fps_entry.bind("<FocusOut>", self.apply_gui_options_to_selected_files_event)

        bottom_frame = tk.Frame(self.root); bottom_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        self.start_button = tk.Button(bottom_frame, text="Start Processing", command=self.start_processing, bg="#4CAF50", fg="white", font=font.Font(weight="bold")); self.start_button.pack(side=tk.LEFT, padx=5, ipady=5)
        self.generate_log_checkbox = tk.Checkbutton(bottom_frame, text="Generate Log File", variable=self.generate_log_var, command=self.apply_gui_options_to_selected_files); self.generate_log_checkbox.pack(side=tk.LEFT, padx=(10, 0))
        
        self._toggle_orientation_options(); self._toggle_upscale_options(); self._toggle_audio_norm_options()
        self._update_bitrate_display()

    def populate_fonts(self):
        try:
            fonts = sorted(list(font.families()))
            self.font_combo['values'] = fonts
            if DEFAULT_SUBTITLE_FONT in fonts:
                self.subtitle_font_var.set(DEFAULT_SUBTITLE_FONT)
            elif fonts:
                self.subtitle_font_var.set(fonts[0])
        except Exception as e:
            print(f"[WARN] Could not load system fonts: {e}")
            self.font_combo['values'] = [DEFAULT_SUBTITLE_FONT]
            self.subtitle_font_var.set(DEFAULT_SUBTITLE_FONT)

    def choose_color(self, color_var, swatch_label):
        initial_color = color_var.get()
        color_code = colorchooser.askcolor(title="Choose color", initialcolor=initial_color)
        if color_code and color_code[1]:
            hex_color = color_code[1]
            color_var.set(hex_color)
            swatch_label.config(bg=hex_color)
            self.apply_gui_options_to_selected_files()

    def _toggle_bitrate_override(self):
        is_override = self.override_bitrate_var.get()
        new_state = "normal" if is_override else "disabled"
        self.manual_bitrate_entry.config(state=new_state)
        if not is_override:
            self._update_bitrate_display()
        self.apply_gui_options_to_selected_files()

    def _update_bitrate_display(self):
        if self.override_bitrate_var.get():
            return

        selected_indices = self.job_listbox.curselection()
        ref_job = None
        if selected_indices:
            ref_job = self.processing_jobs[selected_indices[0]]
        elif self.processing_jobs:
            ref_job = self.processing_jobs[0]
        
        if ref_job:
            info = get_video_info(ref_job['video_path'])
            resolution_key = self.resolution_var.get()
            is_hdr = self.output_format_var.get() == 'hdr'
            bitrate = get_bitrate(resolution_key, info["framerate"], is_hdr)
            self.manual_bitrate_var.set(str(bitrate))

    def _toggle_orientation_options(self):
        orientation = self.orientation_var.get()
        self.horizontal_rb_frame.pack_forget()
        self.vertical_rb_frame.pack_forget()
        resolution_widgets = [self.rb_hd, self.rb_4k, self.rb_8k]
        upscale_widgets = [self.rb_lanczos, self.rb_bicubic, self.rb_bilinear]
        aspect_handling_widgets = [self.rb_crop, self.rb_pad, self.rb_stretch]
        for widget_list in [resolution_widgets, upscale_widgets, aspect_handling_widgets]:
            for widget in widget_list:
                widget.config(state="normal")
        if orientation == "horizontal": self.aspect_ratio_frame.config(text="Horizontal Aspect Ratio"); self.horizontal_rb_frame.pack(fill="x")
        elif orientation == "vertical": self.aspect_ratio_frame.config(text="Vertical Aspect Ratio"); self.vertical_rb_frame.pack(fill="x")
        elif orientation == "horizontal + vertical": self.aspect_ratio_frame.config(text="Aspect Ratios (H & V)"); self.horizontal_rb_frame.pack(fill="x", pady=(0, 5)); self.vertical_rb_frame.pack(fill="x")
        elif orientation == "original":
            self.aspect_ratio_frame.config(text="Aspect Ratio (Original – unchanged)")
            for widget in aspect_handling_widgets: widget.config(state="disabled")
            for widget in resolution_widgets: widget.config(state="normal")
            for widget in upscale_widgets: widget.config(state="normal")
        self.apply_gui_options_to_selected_files()

    def _toggle_upscale_options(self): self.apply_gui_options_to_selected_files()

    def _toggle_audio_norm_options(self):
        state = "normal" if self.normalize_audio_var.get() else "disabled"
        for widget in [self.loudness_target_entry, self.loudness_range_entry, self.true_peak_entry]:
            widget.config(state=state)
        self.apply_gui_options_to_selected_files()

    def apply_gui_options_to_selected_files(self, event=None):
        self._update_bitrate_display()
        selected_indices = self.job_listbox.curselection()
        options_state = {
            "resolution": self.resolution_var.get(), "upscale_algo": self.upscale_algo_var.get(),
            "output_format": self.output_format_var.get(), "fruc": self.fruc_var.get(),
            "fruc_fps": self.fruc_fps_var.get(), "generate_log": self.generate_log_var.get(),
            "orientation": self.orientation_var.get(), "aspect_mode": self.aspect_mode_var.get(),
            "horizontal_aspect": self.horizontal_aspect_var.get(),
            "vertical_aspect": self.vertical_aspect_var.get(),
            "burn_subtitles": self.burn_subtitles_var.get(),
            "override_bitrate": self.override_bitrate_var.get(),
            "manual_bitrate": self.manual_bitrate_var.get(),
            "normalize_audio": self.normalize_audio_var.get(),
            "loudness_target": self.loudness_target_var.get(),
            "loudness_range": self.loudness_range_var.get(),
            "true_peak": self.true_peak_var.get(),
            "subtitle_font": self.subtitle_font_var.get(),
            "subtitle_font_size": self.subtitle_font_size_var.get(),
            "subtitle_alignment": self.subtitle_alignment_var.get(),
            "subtitle_bold": self.subtitle_bold_var.get(),
            "subtitle_italic": self.subtitle_italic_var.get(),
            "subtitle_primary_color": self.subtitle_primary_color_var.get(),
            "subtitle_outline_color": self.subtitle_outline_color_var.get(),
            "subtitle_shadow_color": self.subtitle_shadow_color_var.get(),
            "subtitle_margin_v": self.subtitle_margin_v_var.get()
        }
        target_indices = selected_indices if selected_indices else range(len(self.processing_jobs))
        for index in target_indices: 
            self.processing_jobs[index]['options'].update(options_state)

    def add_video_files_and_discover_jobs(self, file_paths):
        default_options = {
            "resolution": self.resolution_var.get(), "upscale_algo": self.upscale_algo_var.get(),
            "output_format": self.output_format_var.get(), "fruc": self.fruc_var.get(),
            "fruc_fps": self.fruc_fps_var.get(), "generate_log": self.generate_log_var.get(),
            "orientation": self.orientation_var.get(), "aspect_mode": self.aspect_mode_var.get(),
            "horizontal_aspect": self.horizontal_aspect_var.get(),
            "vertical_aspect": self.vertical_aspect_var.get(),
            "burn_subtitles": self.burn_subtitles_var.get(),
            "override_bitrate": self.override_bitrate_var.get(),
            "manual_bitrate": self.manual_bitrate_var.get(),
            "normalize_audio": self.normalize_audio_var.get(),
            "loudness_target": self.loudness_target_var.get(),
            "loudness_range": self.loudness_range_var.get(),
            "true_peak": self.true_peak_var.get(),
            "subtitle_font": self.subtitle_font_var.get(),
            "subtitle_font_size": self.subtitle_font_size_var.get(),
            "subtitle_alignment": self.subtitle_alignment_var.get(),
            "subtitle_bold": self.subtitle_bold_var.get(),
            "subtitle_italic": self.subtitle_italic_var.get(),
            "subtitle_primary_color": self.subtitle_primary_color_var.get(),
            "subtitle_outline_color": self.subtitle_outline_color_var.get(),
            "subtitle_shadow_color": self.subtitle_shadow_color_var.get(),
            "subtitle_margin_v": self.subtitle_margin_v_var.get()
        }
        
        for video_path in file_paths:
            dir_name = os.path.dirname(video_path)
            video_basename, _ = os.path.splitext(os.path.basename(video_path))
            
            # 1. Discover all matching SRT files
            matched_srts = []
            try:
                for item in os.listdir(dir_name):
                    if item.lower().endswith('.srt'):
                        srt_basename, _ = os.path.splitext(item)
                        if srt_basename == video_basename:
                            matched_srts.append(os.path.join(dir_name, item))
                        elif srt_basename.startswith(video_basename):
                            separator = srt_basename[len(video_basename)]
                            if separator in [' ', '.', '-', '_']:
                                matched_srts.append(os.path.join(dir_name, item))
            except Exception as e:
                print(f"[WARN] Could not scan for subtitles in {dir_name}: {e}")

            # 2. If no subtitles were found, create the "No Subtitles" job.
            if not matched_srts:
                job_no_sub = {
                    "job_id": f"job_{time.time()}", "video_path": video_path, "subtitle_path": None,
                    "display_name": f"{os.path.basename(video_path)} [No Subtitles]",
                    "options": copy.deepcopy(default_options)
                }
                self.processing_jobs.append(job_no_sub)
                self.job_listbox.insert(tk.END, job_no_sub["display_name"])

            # 3. Create a job for each found SRT. This loop will not run if matched_srts is empty.
            for srt_path in sorted(matched_srts):
                srt_basename, _ = os.path.splitext(os.path.basename(srt_path))
                tag = srt_basename[len(video_basename):].strip(' .-_')
                if not tag: tag = "(exact match)"

                job_with_sub = {
                    "job_id": f"job_{time.time()}", "video_path": video_path, "subtitle_path": srt_path,
                    "display_name": f"{os.path.basename(video_path)} [Sub: {tag}]",
                    "options": copy.deepcopy(default_options)
                }
                self.processing_jobs.append(job_with_sub)
                self.job_listbox.insert(tk.END, job_with_sub["display_name"])
        
        self._update_bitrate_display()

    def on_file_select(self, event):
        sel = self.job_listbox.curselection()
        if sel:
            selected_job = self.processing_jobs[sel[0]]
            options = selected_job['options']
            self.resolution_var.set(options.get("resolution", DEFAULT_RESOLUTION)); self.upscale_algo_var.set(options.get("upscale_algo", DEFAULT_UPSCALE_ALGO)); self.output_format_var.set(options.get("output_format", DEFAULT_OUTPUT_FORMAT)); self.orientation_var.set(options.get("orientation", DEFAULT_ORIENTATION)); self.aspect_mode_var.set(options.get("aspect_mode", DEFAULT_ASPECT_MODE)); self.horizontal_aspect_var.set(options.get("horizontal_aspect", DEFAULT_HORIZONTAL_ASPECT)); self.vertical_aspect_var.set(options.get("vertical_aspect", DEFAULT_VERTICAL_ASPECT)); self.fruc_var.set(options.get("fruc", DEFAULT_FRUC)); self.fruc_fps_var.set(options.get("fruc_fps", DEFAULT_FRUC_FPS)); self.generate_log_var.set(options.get("generate_log", False))
            self.burn_subtitles_var.set(options.get("burn_subtitles", DEFAULT_BURN_SUBTITLES))
            self.override_bitrate_var.set(options.get("override_bitrate", False))
            self.manual_bitrate_var.set(options.get("manual_bitrate", "0"))
            self.normalize_audio_var.set(options.get("normalize_audio", DEFAULT_NORMALIZE_AUDIO))
            self.loudness_target_var.set(options.get("loudness_target", DEFAULT_LOUDNESS_TARGET))
            self.loudness_range_var.set(options.get("loudness_range", DEFAULT_LOUDNESS_RANGE))
            self.true_peak_var.set(options.get("true_peak", DEFAULT_TRUE_PEAK))
            self.subtitle_font_var.set(options.get("subtitle_font", DEFAULT_SUBTITLE_FONT))
            self.subtitle_font_size_var.set(options.get("subtitle_font_size", DEFAULT_SUBTITLE_FONT_SIZE))
            self.subtitle_alignment_var.set(options.get("subtitle_alignment", DEFAULT_SUBTITLE_ALIGNMENT))
            self.subtitle_bold_var.set(options.get("subtitle_bold", DEFAULT_SUBTITLE_BOLD))
            self.subtitle_italic_var.set(options.get("subtitle_italic", DEFAULT_SUBTITLE_ITALIC))
            self.subtitle_primary_color_var.set(options.get("subtitle_primary_color", DEFAULT_SUBTITLE_PRIMARY_COLOR))
            self.subtitle_outline_color_var.set(options.get("subtitle_outline_color", DEFAULT_SUBTITLE_OUTLINE_COLOR))
            self.subtitle_shadow_color_var.set(options.get("subtitle_shadow_color", DEFAULT_SUBTITLE_SHADOW_COLOR))
            self.subtitle_margin_v_var.set(options.get("subtitle_margin_v", DEFAULT_SUBTITLE_MARGIN_V))
            self.primary_color_swatch.config(bg=self.subtitle_primary_color_var.get())
            self.outline_color_swatch.config(bg=self.subtitle_outline_color_var.get())
            self.shadow_color_swatch.config(bg=self.subtitle_shadow_color_var.get())

            self._toggle_bitrate_override()
            self.toggle_fruc_fps(); self._toggle_orientation_options(); self._toggle_upscale_options(); self._toggle_audio_norm_options()

    def build_ffmpeg_command_and_run(self, job, orientation, ass_burn=None):
        file_path = job['video_path']
        options = job['options']
        resolution_mode = options.get("resolution", DEFAULT_RESOLUTION); output_format = options.get("output_format", DEFAULT_OUTPUT_FORMAT)
        folder_name = f"{resolution_mode}_{output_format.upper()}"
        if orientation == "vertical": folder_name += f"_Vertical_{options.get('vertical_aspect').replace(':', 'x')}"
        elif orientation == "original": folder_name += "_Original"
        else:
            horizontal_aspect = options.get('horizontal_aspect').replace(':', 'x')
            if horizontal_aspect != "16x9": folder_name += f"_Horizontal_{horizontal_aspect}"
        base_dir = os.path.dirname(file_path) if self.output_mode == 'local' else os.getcwd()
        output_dir = os.path.join(base_dir, folder_name); os.makedirs(output_dir, exist_ok=True)
        base_name, _ = os.path.splitext(os.path.basename(file_path))
        
        # BUG FIX: Modified filename generation to prevent overwrites
        output_name_suffix = ""
        if job['subtitle_path']:
             srt_basename, _ = os.path.splitext(os.path.basename(job['subtitle_path']))
             tag = srt_basename[len(base_name):].strip(' .-_')
             if tag:
                 output_name_suffix = f"_{tag}"
             # If tag is empty, it's an exact match, so no suffix is added.
        else:
            # This is the "No Subtitles" job, so we explicitly mark it.
            output_name_suffix = "_NoSub"

        output_file = os.path.join(output_dir, f"{base_name}{output_name_suffix}_temp.mp4")
        cmd = self.construct_ffmpeg_command(file_path, output_file, orientation, ass_burn, options)
        ret = self.run_ffmpeg_command(cmd)
        if ret == 0:
            final_name = output_file.replace("_temp.mp4", ".mp4")
            try:
                if os.path.exists(final_name): os.remove(final_name)
                os.rename(output_file, final_name); print(f"File finalized => {final_name}"); self.verify_output_file(final_name)
            except Exception as e: print(f"[ERROR] Could not rename temp file {output_file}: {e}")
        else: print(f"[ERROR] Error encoding {file_path}: return code {ret}")

    def construct_ffmpeg_command(self, file_path, output_file, orientation, ass_burn, options):
        info = get_video_info(file_path)
        
        decoder_map = {
            "h264": "h264_cuvid", "hevc": "hevc_cuvid", "av1": "av1_cuvid",
            "vp9": "vp9_cuvid", "mpeg2video": "mpeg2_cuvid", "vc1": "vc1_cuvid", "mjpeg": "mjpeg_cuvid"
        }
        decoder = decoder_map.get(info["codec_name"], "h264_cuvid")

        cmd = [
            "ffmpeg", "-y", "-hide_banner",
            "-hwaccel", "cuda",
            "-hwaccel_output_format", "cuda",
            "-c:v", decoder,
            "-i", file_path
        ]
        
        vf_filters = []
        cpu_filters = []
        output_format = options.get("output_format")
        is_hdr_output = output_format == 'hdr'
        
        sdr_format_conversion_str = "" if is_hdr_output else ":format=nv12"
        upscale_algo = options.get("upscale_algo", DEFAULT_UPSCALE_ALGO)
        
        if orientation != "original":
            aspect_mode = options.get("aspect_mode")
            resolution_key = options.get('resolution')

            if orientation == "vertical":
                aspect_str = options.get('vertical_aspect'); width_map = {"HD": 1080, "4k": 2160, "8k": 4320}
                target_width = width_map.get(resolution_key, 1080)
                try: num, den = map(int, aspect_str.split(':')); target_height = int(target_width * den / num)
                except: target_height = int(target_width * 16 / 9)
            else: # horizontal
                aspect_str = options.get('horizontal_aspect'); width_map = {"HD": 1920, "4k": 3840, "8k": 7680}
                target_width = width_map.get(resolution_key, 1920)
                try: num, den = map(int, aspect_str.split(':')); target_height = int(target_width * den / num)
                except: target_height = int(target_width * 9 / 16)
            
            target_width = (target_width // 2) * 2
            target_height = (target_height // 2) * 2

            if aspect_mode == 'pad':
                vf_filters.append(f"scale_cuda=w={target_width}:h={target_height}:interp_algo={upscale_algo}:force_original_aspect_ratio=decrease{sdr_format_conversion_str}")
                cpu_filters.append(f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2:black")
            elif aspect_mode == 'crop':
                vf_filters.append(f"scale_cuda=w={target_width}:h={target_height}:interp_algo={upscale_algo}:force_original_aspect_ratio=increase{sdr_format_conversion_str}")
                cpu_filters.append(f"crop={target_width}:{target_height}")
            elif aspect_mode == 'stretch':
                vf_filters.append(f"scale_cuda=w={target_width}:h={target_height}:interp_algo={upscale_algo}{sdr_format_conversion_str}")
        
        else: # orientation is "original"
            if not is_hdr_output and info["bit_depth"] == 10:
                vf_filters.append(f"scale_cuda=format=nv12")

        if info["is_hdr"] and not is_hdr_output and os.path.exists(self.lut_file):
            lut_path_escaped = self.lut_file.replace('\\', '/').replace(':', '\\:')
            cpu_filters.append(f"lut3d=file='{lut_path_escaped}':interp=trilinear")
        
        if options.get("fruc"):
            cpu_filters.append(f"minterpolate=fps={options.get('fruc_fps')}")

        if ass_burn:
            subtitle_path_escaped = ass_burn.replace('\\', '/').replace(':', '\\:')
            cpu_filters.append(f"subtitles=filename='{subtitle_path_escaped}'")
        
        if cpu_filters:
            if vf_filters: vf_filters.append("hwdownload,format=nv12")
            else: vf_filters.append("hwdownload,format=nv12")
            vf_filters.append(",".join(cpu_filters))
            vf_filters.append("format=nv12,hwupload_cuda")
        
        cmd.extend(["-map", "0:v:0"])

        if vf_filters:
            vf_string = ",".join(vf_filters)
            cmd.extend(["-vf", vf_string])

        audio_streams = get_audio_stream_info(file_path)
        if not audio_streams:
            cmd.extend(["-an"])
        elif options.get("normalize_audio"):
            num_audio_streams = len(audio_streams)
            print(f"[INFO] Audio Normalization enabled. Processing all {num_audio_streams} audio track(s).")
            cmd.extend(["-map", "0:a?"])
            lufs = options.get('loudness_target', DEFAULT_LOUDNESS_TARGET)
            lra = options.get('loudness_range', DEFAULT_LOUDNESS_RANGE)
            peak = options.get('true_peak', DEFAULT_TRUE_PEAK)
            audio_filter = f"loudnorm=i={lufs}:lra={lra}:tp={peak}"
            for i in range(num_audio_streams):
                cmd.extend([
                    f"-af:a:{i}", audio_filter, f"-c:a:{i}", "aac", f"-b:a:{i}", "192k"
                ])
        else:
            cmd.extend(["-map", "0:a?"])
            cmd.extend(["-c:a", "copy"])

        if options.get("override_bitrate", False):
            try:
                bitrate_kbps = int(options.get("manual_bitrate"))
                print(f"[INFO] Manual bitrate override active: {bitrate_kbps} kbps")
            except (ValueError, TypeError):
                print(f"[WARN] Invalid manual bitrate value. Falling back to automatic calculation.")
                bitrate_kbps = get_bitrate("HD", info["framerate"], is_hdr_output)
        else:
            if orientation == "original":
                if info["height"] <= 1080: bitrate_res_key = "HD"
                elif info["height"] <= 2160: bitrate_res_key = "4k"
                else: bitrate_res_key = "8k"
            else:
                resolution_key = options.get('resolution', DEFAULT_RESOLUTION)
                bitrate_res_key = "HD" if resolution_key == "HD" else resolution_key.lower()
            bitrate_kbps = get_bitrate(bitrate_res_key, info["framerate"], is_hdr_output)

        gop_len = 0 if info["framerate"] == 0 else math.ceil(info["framerate"] / 2)
        
        if is_hdr_output:
            cmd.extend([
                "-c:v", "hevc_nvenc", "-preset", "p1", "-profile:v", "main10",
                "-b:v", f"{bitrate_kbps}k", "-g", str(gop_len),
                "-color_primaries", "bt2020", "-color_trc", "smpte2084", "-colorspace", "bt2020nc"
            ])
        else:
            cmd.extend([
                "-c:v", "h264_nvenc", "-preset", "p1", "-profile:v", "high",
                "-b:v", f"{bitrate_kbps}k", "-g", str(gop_len),
                "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709"
            ])

        cmd.extend(["-f", "mp4", output_file])
        return cmd

    def start_processing(self):
        if not self.processing_jobs: messagebox.showwarning("No Jobs", "Please add at least one file to create processing jobs."); return
        self.output_mode = self.output_mode_var.get()
        print("\n" + "="*80 + "\n--- Starting processing batch ---")
        self.root.destroy()
        
        for job in self.processing_jobs:
            options = job['options']
            subtitle_path = job['subtitle_path']
            orientation_mode = options.get("orientation", "horizontal")
            
            temp_ass_path = None
            try:
                if options.get("burn_subtitles") and subtitle_path:
                    print(f"[INFO] Creating styled subtitle file for {job['display_name']}...")
                    temp_ass_path = create_temporary_ass_file(subtitle_path, options)
                    if temp_ass_path:
                        print(f"[INFO] Subtitle burning enabled for this job.")
                
                print("-" * 80); print(f"Processing Job: {job['display_name']} (Mode: {orientation_mode})")
                if orientation_mode == "horizontal + vertical":
                    print(f"\n--- Processing HORIZONTAL ---")
                    self.build_ffmpeg_command_and_run(job, "horizontal", ass_burn=temp_ass_path)
                    print(f"\n--- Processing VERTICAL ---")
                    self.build_ffmpeg_command_and_run(job, "vertical", ass_burn=temp_ass_path)
                else:
                    self.build_ffmpeg_command_and_run(job, orientation_mode, ass_burn=temp_ass_path)
            
            finally:
                if temp_ass_path and os.path.exists(temp_ass_path):
                    os.remove(temp_ass_path)
                    print(f"[INFO] Cleaned up temporary subtitle file.")
                    
        print("\n================== Processing Complete. ==================")

    def run_ffmpeg_command(self, cmd):
        print("Running FFmpeg command:\n" + " ".join(f'"{c}"' if " " in c else c for c in cmd))
        process = subprocess.Popen(cmd,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env, text=True,encoding='utf-8',errors='replace',bufsize=1)
        while True:
            line = process.stdout.readline();
            if not line and process.poll() is not None: break
            if line:
                if "\r" in line: progress = line.split("\r")[-1].strip(); sys.stdout.write("\r" + progress); sys.stdout.flush()
                else: sys.stdout.write(line); sys.stdout.flush()
        process.stdout.close(); ret = process.wait(); print("\nFFmpeg conversion finished."); return ret

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
    def add_files(self): files = filedialog.askopenfilenames(title="Select Video Files", filetypes=[("Video Files", "*.mp4;*.mkv;*.avi;*.mov;*.webm;*.flv;*.wmv"), ("All Files", "*.*")]); self.add_video_files_and_discover_jobs(files)
    def handle_file_drop(self, event): files = self.root.tk.splitlist(event.data); self.add_video_files_and_discover_jobs(files)
    def remove_selected(self):
        selected_indices = list(self.job_listbox.curselection())
        for index in reversed(selected_indices):
            del self.processing_jobs[index]
            self.job_listbox.delete(index)
    def clear_all(self): self.processing_jobs.clear(); self.job_listbox.delete(0, tk.END)
    def select_all_files(self): self.job_listbox.select_set(0, tk.END); self.on_file_select(None)
    def clear_file_selection(self): self.job_listbox.select_clear(0, tk.END); self.on_file_select(None)
    def toggle_fruc_fps(self): self.fruc_fps_entry.config(state="normal" if self.fruc_var.get() else "disabled")
    
    def duplicate_selected_jobs(self):
        selected_indices = self.job_listbox.curselection()
        if not selected_indices: return
        offset = 0
        for index in selected_indices:
            actual_index = index + offset
            original_job = self.processing_jobs[actual_index]
            new_job = copy.deepcopy(original_job)
            new_job['job_id'] = f"{original_job['job_id']}_copy_{time.time()}"
            new_job['display_name'] = f"{original_job['display_name']} (Copy)"
            insert_at = actual_index + 1
            self.processing_jobs.insert(insert_at, new_job)
            self.job_listbox.insert(insert_at, new_job['display_name'])
            offset += 1

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
            if "SDR_Vertical" in root_dir or "HDR_Vertical" in root_dir or "SDR_Original" in root_dir:
                continue
            for filename in files:
                if os.path.splitext(filename)[1].lower() in video_extensions:
                    files_found.append(os.path.join(root_dir, filename))
        initial_files.extend(sorted(files_found))
    app = VideoProcessorApp(root, sorted(list(set(initial_files))), args.output_mode)
    root.mainloop()