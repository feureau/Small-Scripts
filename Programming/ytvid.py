
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
over output orientation, aspect ratio handling, and advanced subtitle burning for both
horizontal and vertical formats. It acts as a front-end for the powerful NVIDIA
hardware-accelerated encoder, NVEncC. For a full list of NVEncC's own command-line
options, please refer to the official documentation on its GitHub repository.

CORE FEATURES:
  - Batch Processing: Process multiple video files in a single session.
  - Hardware Acceleration: Leverages NVIDIA's NVENC for high-speed encoding.
  - Full Geometric Control: Independently set orientation (Horizontal, Vertical, Original) and
    aspect ratio handling (Crop, Pad, Stretch).
  - Advanced Subtitle Burning: Automatically detects sidecar SRT files and provides a full
    styling suite (font, size, color, alignment, margin) for burning them into the video.
  - Format Flexibility: Output to SDR (H.264) or HDR (HEVC) with automatic bitrate selection.
  - AI Upscaling: Integrates NVIDIA's Super Resolution and VSR for high-quality upscaling.
  - Self-Contained: Includes this detailed documentation about the script's own logic.

----------------------------------------------------------------------------------------------------
                        PART 2: DESIGN PHILOSOPHY & TECHNICAL RATIONALE
----------------------------------------------------------------------------------------------------

This script is the result of an iterative, empirical development process. Many of the
core design decisions were made in direct response to the specific, often non-obvious,
quirks and limitations discovered in the NVEncC encoder and its video processing (VPP)
filter chain. The primary goal of the current design is **stability and predictability**
above all else.

1.  **SUBTITLE HANDLING - The Second Core Challenge (v3.6+)**
    The implementation of subtitle burning was a significant development challenge. The final
    design was chosen after initial, simpler methods failed due to the specific constraints
    of the NVEncC toolchain.

    -   **Historical Reason - The Failed Approach:** The first attempt involved passing style
        overrides directly to the `--vpp-subburn` filter using a `force_style` parameter.
        This is a common and valid method in standard ffmpeg. However, extensive testing and
        debugging revealed that **NVEncC's `--vpp-subburn` implementation does NOT support the
        `force_style` parameter**. All attempts to pass style information on the command line,
        regardless of quoting or escaping, resulted in a parser error. This is a crucial
        limitation of the NVEncC tool itself.

    -   **Final, Robust Solution - On-the-Fly SRT-to-ASS Conversion (v3.8.0+):**
        To provide full styling control in a way that is 100% compatible with NVEncC,
        the script now uses a more sophisticated back-end process. This is the only
        reliable method.
        -   **Method:** When subtitle burning is enabled for a video with a detected `.srt`
            file, the script dynamically creates a temporary, styled `.ass` (Advanced
            SubStation Alpha) file in memory just before encoding.
        -   **Style Implementation:** All settings configured in the "Subtitle Styling"
            GUI (Font Family, Size, Colors, Bold, Italic, Alignment, and Vertical Margin)
            are written into the `[V4+ Styles]` header of this temporary `.ass` file. This
            embeds the styling information directly into the subtitle data.
        -   **Conversion:** The script then parses the simple text and timings from the
            original `.srt` file and converts each line into a styled `Dialogue:` event
            in the `.ass` format.
        -   **Execution:** This temporary, self-contained `.ass` file is then passed to
            NVEncC's `--vpp-subburn` filter using the standard `filename=` parameter. Because
            all styling is embedded within the file, the renderer processes it flawlessly.
        -   **Rationale:** This approach is the definitive and most reliable method. It
            leverages the native styling power of the `.ass` format, sidesteps the
            limitations of `NVEncC`'s filter parameters, and gives the user complete
            visual control over the final burned-in subtitles. The temporary file is
            automatically deleted after the encode is complete.

2.  **ASPECT RATIO GEOMETRY - The First Core Challenge**
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

    To solve these challenges, each "Aspect Handling" mode uses a distinct method:
    -   **"Original with Upscale" Mode (v3.5+):**
        -   **Method:** Uses `--output-res` with automatic aspect ratio preservation.
        -   **Rationale:** The simplest, most direct way to upscale while letting the
            encoder handle letter/pillarboxing automatically.
    -   **"Crop (Fill)" Mode uses a "Crop then Resize" Method:**
        -   **Method:** Uses `--crop` to trim the source, then `--output-res` to resize.
        -   **Rationale:** Stable and efficient for filling a frame.
    -   **"Pad (Fit)" Mode uses a "Pad then Final Resize" Method (v3.1+):**
        -   **Method:** Applies `--vpp-pad` first and then sets the final dimensions with `--output-res`.
        -   **Historical Rationale:** This counter-intuitive order is the only one that works
            reliably on limited NVEncC builds. The encoder engine is smart enough to see the
            final resolution from `--output-res` and performs an implicit "letterbox" resize
            *before* applying the explicit `--vpp-pad` filter, resulting in the correct output.
    -   **"Stretch" Mode uses a "Direct Resize" Method:**
        -   **Method:** Uses a single `--output-res` command.
        -   **Rationale:** The simplest approach when aspect ratio preservation is not needed.

3.  **GUI & WORKFLOW**
    -   **Rationale (v2.2+):** Redesigned into a two-column format for a more logical
        workflow on modern widescreen monitors (Files on left, Options on right).
    -   **Rationale (v3.4+):** The settings logic was updated so that if no files are
        selected, any change in the GUI applies globally to all files in the list. If one
        or more files are selected, changes only apply to the selection. This provides
        both batch and per-file flexibility.

----------------------------------------------------------------------------------------------------
                            PART 3: CODE ANNOTATION & EXPLANATION
----------------------------------------------------------------------------------------------------

This section explains the purpose of the main components of the Python script.

1.  **USER CONFIGURATION BLOCK**
    This block at the top of the script contains all default values for the GUI.
    -   `DEFAULT_...`: Each of these variables sets the initial state of a GUI element, such
        as the default resolution, font, or color. This makes it easy to customize the
        application's starting configuration without digging into the main code.
    -   `BITRATES`: A dictionary defining the target video bitrates in kilobits per second (kbps).
        It is structured to provide different values based on the output format (SDR/HDR),
        frame rate (Normal/High FPS), and resolution (HD/4k/8k). This allows for nuanced
        quality control that aligns with YouTube's recommendations.

2.  **CORE FUNCTIONS**
    -   `hex_to_libass_color()`: A helper function that converts a standard HTML hex color
        (e.g., `#FFFF00`) into the specific `&H00BBGGRR` format required by the ASS subtitle
        standard.
    -   `create_temporary_ass_file()`: The core of the modern subtitle system. It takes an
        SRT file path and the GUI options, constructs a complete, styled ASS file as a string,
        and writes it to a temporary file on disk, returning the path to that file.
    -   `get_video_info()`: Uses `ffprobe` (part of the ffmpeg suite) to inspect a video file
        and extract essential metadata. This data (resolution, frame rate, HDR status) is
        critical for making automatic decisions later, such as calculating the correct
        aspect ratio for cropping or selecting the appropriate bitrate.
    -   `VideoProcessorApp` Class: The main class that encapsulates the entire GUI application.
        -   `__init__()`: Initializes all Tkinter variables that link the GUI widgets to
            the script's internal state.
        -   `setup_gui()`: Contains all the code for creating and arranging the visual
            elements (buttons, labels, checkboxes) of the application window.
        -   `populate_fonts()`: Scans the user's operating system for available fonts and
            populates the font selection dropdown, making any installed font usable.
        -   `apply_gui_options_to_selected_files()`: The central logic for saving settings.
            It reads the current state of all GUI widgets and saves them to the `file_options`
            dictionary, keyed by the video file path.
        -   `construct_nvencc_command()`: This is the "brain" of the operation. It takes a
            file path and its associated options and builds the final command-line string to
            be executed. It logically adds arguments for geometry, quality, codecs, and,
            most importantly, points to the temporary `.ass` file for subtitle burning.
        -   `start_processing()`: The main execution loop. When the "Start" button is clicked,
            this function iterates through each file in the list. For each file, it creates
            the temporary `.ass` subtitle file (if needed), calls the command constructor,
            runs the `NVEncC64.exe` process, and then—crucially—cleans up the temporary
            subtitle file in a `finally` block to ensure no garbage is left behind, even if
            an error occurs.
        -   `run_nvenc_command()`: A helper function that uses Python's `subprocess` module to
            execute the generated NVEncC command. It captures the command's output in real-time
            and prints it to the console, so the user can see the progress.
    -   `if __name__ == "__main__":` Block: This is the entry point of the script.
        -   It uses `argparse` to handle command-line arguments (like `--output-mode`).
        -   If no files are provided via the command line, it performs a "deep scan" using
            `os.walk()` to find all video files in the current directory and its subdirectories,
            making it convenient for batch work.
        -   Finally, it creates the main application window and starts the Tkinter event loop.

----------------------------------------------------------------------------------------------------
                                        PART 4: CHANGELOG
----------------------------------------------------------------------------------------------------
v3.9.1 (2025-10-16) - Gemini/User Collaboration
  - FIX: Corrected a `SyntaxError` within the documentation text itself by rephrasing a
    changelog entry to avoid using characters that would conflict with the docstring parser.

v3.9.0 (2025-10-16) - Gemini/User Collaboration
  - DOCS: Revised and streamlined the internal documentation. The full NVEncC command-line
    documentation appendix has been removed to significantly reduce file size and improve
    readability. The script's own detailed technical and historical rationale is preserved.

v3.8.2 (2025-10-16) - Gemini/User Collaboration
  - FIX: Corrected a fatal `SyntaxError: (unicode error)` on script startup by converting the
    main documentation block into a raw string by prefixing it with an 'r'.

v3.8.1 (2025-10-16) - Gemini/User Collaboration
  - FEATURE: Added a "Vertical Margin" input field to the GUI for precise subtitle positioning.
  - BEHAVIOR: The `MarginV` value is now written into the temporary .ass style definition.

v3.8.0 (2025-10-16) - Gemini/User Collaboration
  - REFACTOR: Overhauled the subtitle burning mechanism to use on-the-fly SRT-to-ASS conversion.
  - FIX: Corrected the fundamental flaw of trying to use the unsupported `force_style` parameter.
  

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
DEFAULT_BURN_SUBTITLES = False

# --- Default subtitle style settings ---
DEFAULT_SUBTITLE_FONT = "Helvetica World"
DEFAULT_SUBTITLE_FONT_SIZE = "64"
DEFAULT_SUBTITLE_ALIGNMENT = "bottom"
DEFAULT_SUBTITLE_BOLD = False
DEFAULT_SUBTITLE_ITALIC = False
DEFAULT_SUBTITLE_PRIMARY_COLOR = "#FFFF00"  # Yellow
DEFAULT_SUBTITLE_OUTLINE_COLOR = "#000000" # Black
DEFAULT_SUBTITLE_SHADOW_COLOR = "#808080"  # Gray
# --- MODIFICATION: Add default for Vertical Margin ---
DEFAULT_SUBTITLE_MARGIN_V = "115"


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
    # --- MODIFICATION: Get MarginV from options ---
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
Style: {style_name},{font_name},{font_size},{primary_color},&H000000FF,{outline_color},{shadow_color},{bold_flag},{italic_flag},0,0,100,100,0,0,1,2,1,{alignment},10,10,{margin_v},1

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
        dialogue_lines.append(f"Dialogue: 0,{start_ass},{end_ass},{style_name},,0,0,0,,{text_ass}")

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
        self.file_list = []
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
        self.generate_log_var = tk.BooleanVar(value=False)
        self.burn_subtitles_var = tk.BooleanVar(value=DEFAULT_BURN_SUBTITLES)
        
        self.subtitle_font_var = tk.StringVar(value=DEFAULT_SUBTITLE_FONT)
        self.subtitle_font_size_var = tk.StringVar(value=DEFAULT_SUBTITLE_FONT_SIZE)
        self.subtitle_alignment_var = tk.StringVar(value=DEFAULT_SUBTITLE_ALIGNMENT)
        self.subtitle_bold_var = tk.BooleanVar(value=DEFAULT_SUBTITLE_BOLD)
        self.subtitle_italic_var = tk.BooleanVar(value=DEFAULT_SUBTITLE_ITALIC)
        self.subtitle_primary_color_var = tk.StringVar(value=DEFAULT_SUBTITLE_PRIMARY_COLOR)
        self.subtitle_outline_color_var = tk.StringVar(value=DEFAULT_SUBTITLE_OUTLINE_COLOR)
        self.subtitle_shadow_color_var = tk.StringVar(value=DEFAULT_SUBTITLE_SHADOW_COLOR)
        # --- MODIFICATION: Add variable for MarginV ---
        self.subtitle_margin_v_var = tk.StringVar(value=DEFAULT_SUBTITLE_MARGIN_V)

        self.root.drop_target_register(DND_FILES); self.root.dnd_bind("<<Drop>>", self.handle_file_drop)
        
        self.setup_gui()
        self.update_file_list(initial_files)

    def setup_gui(self):
        self.root.columnconfigure(0, weight=1); self.root.columnconfigure(1, weight=1)
        main_frame = tk.Frame(self.root); main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        left_frame = tk.Frame(main_frame); left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        right_frame = tk.Frame(main_frame); right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))

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
        # --- MODIFICATION: Add GUI elements for Vertical Margin ---
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
        misc_frame = tk.Frame(other_opts_group); misc_frame.pack(fill=tk.X)
        tk.Checkbutton(misc_frame, text="Enable Subtitle Burning", variable=self.burn_subtitles_var, command=self.apply_gui_options_to_selected_files).pack(side=tk.LEFT)
        fruc_frame = tk.Frame(other_opts_group); fruc_frame.pack(fill=tk.X, pady=(5,0))
        tk.Checkbutton(fruc_frame, text="Enable FRUC", variable=self.fruc_var, command=lambda: [self.toggle_fruc_fps(), self.apply_gui_options_to_selected_files()]).pack(side=tk.LEFT)
        tk.Label(fruc_frame, text="FRUC FPS:").pack(side=tk.LEFT, padx=(5,5))
        self.fruc_fps_entry = tk.Entry(fruc_frame, textvariable=self.fruc_fps_var, width=5, state="disabled"); self.fruc_fps_entry.pack(side=tk.LEFT)
        self.fruc_fps_entry.bind("<FocusOut>", self.apply_gui_options_to_selected_files_event)

        bottom_frame = tk.Frame(self.root); bottom_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        self.start_button = tk.Button(bottom_frame, text="Start Processing", command=self.start_processing, bg="#4CAF50", fg="white", font=font.Font(weight="bold")); self.start_button.pack(side=tk.LEFT, padx=5, ipady=5)
        self.generate_log_checkbox = tk.Checkbutton(bottom_frame, text="Generate Log File", variable=self.generate_log_var, command=self.apply_gui_options_to_selected_files); self.generate_log_checkbox.pack(side=tk.LEFT, padx=(10, 0))
        self._toggle_orientation_options(); self._toggle_upscale_options()

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

    def _toggle_orientation_options(self):
        orientation = self.orientation_var.get()
        self.horizontal_rb_frame.pack_forget()
        self.vertical_rb_frame.pack_forget()
        resolution_widgets = [self.rb_hd, self.rb_4k, self.rb_8k]
        upscale_widgets = [self.rb_superres, self.rb_vsr, self.rb_auto]
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

    def apply_gui_options_to_selected_files(self, event=None):
        selected_indices = self.file_listbox.curselection()
        options_state = {
            "resolution": self.resolution_var.get(), "upscale_algo": self.upscale_algo_var.get(),
            "output_format": self.output_format_var.get(), "fruc": self.fruc_var.get(),
            "fruc_fps": self.fruc_fps_var.get(), "generate_log": self.generate_log_var.get(),
            "orientation": self.orientation_var.get(), "aspect_mode": self.aspect_mode_var.get(),
            "horizontal_aspect": self.horizontal_aspect_var.get(),
            "vertical_aspect": self.vertical_aspect_var.get(),
            "burn_subtitles": self.burn_subtitles_var.get(),
            "subtitle_font": self.subtitle_font_var.get(),
            "subtitle_font_size": self.subtitle_font_size_var.get(),
            "subtitle_alignment": self.subtitle_alignment_var.get(),
            "subtitle_bold": self.subtitle_bold_var.get(),
            "subtitle_italic": self.subtitle_italic_var.get(),
            "subtitle_primary_color": self.subtitle_primary_color_var.get(),
            "subtitle_outline_color": self.subtitle_outline_color_var.get(),
            "subtitle_shadow_color": self.subtitle_shadow_color_var.get(),
            # --- MODIFICATION: Save MarginV setting ---
            "subtitle_margin_v": self.subtitle_margin_v_var.get()
        }
        target_indices = selected_indices if selected_indices else range(len(self.file_list))
        for index in target_indices: self.file_options[self.file_list[index]].update(options_state)

    def update_file_list(self, files):
        for file_path in files:
            if file_path not in self.file_list:
                self.file_list.append(file_path); self.file_listbox.insert(tk.END, os.path.basename(file_path))
                self.file_options[file_path] = {
                    "resolution": self.resolution_var.get(), "upscale_algo": self.upscale_algo_var.get(),
                    "output_format": self.output_format_var.get(), "fruc": self.fruc_var.get(),
                    "fruc_fps": self.fruc_fps_var.get(), "generate_log": self.generate_log_var.get(),
                    "orientation": self.orientation_var.get(), "aspect_mode": self.aspect_mode_var.get(),
                    "horizontal_aspect": self.horizontal_aspect_var.get(),
                    "vertical_aspect": self.vertical_aspect_var.get(),
                    "burn_subtitles": self.burn_subtitles_var.get(), "subtitle_file": None,
                    "subtitle_font": self.subtitle_font_var.get(),
                    "subtitle_font_size": self.subtitle_font_size_var.get(),
                    "subtitle_alignment": self.subtitle_alignment_var.get(),
                    "subtitle_bold": self.subtitle_bold_var.get(),
                    "subtitle_italic": self.subtitle_italic_var.get(),
                    "subtitle_primary_color": self.subtitle_primary_color_var.get(),
                    "subtitle_outline_color": self.subtitle_outline_color_var.get(),
                    "subtitle_shadow_color": self.subtitle_shadow_color_var.get(),
                    # --- MODIFICATION: Initialize MarginV for new file ---
                    "subtitle_margin_v": self.subtitle_margin_v_var.get()
                }
                self.detect_subtitle_tracks(file_path)

    def on_file_select(self, event):
        sel = self.file_listbox.curselection()
        if sel:
            selected_file = self.file_list[sel[0]]
            if selected_file in self.file_options:
                options = self.file_options[selected_file]
                self.resolution_var.set(options.get("resolution", DEFAULT_RESOLUTION)); self.upscale_algo_var.set(options.get("upscale_algo", DEFAULT_UPSCALE_ALGO)); self.output_format_var.set(options.get("output_format", DEFAULT_OUTPUT_FORMAT)); self.orientation_var.set(options.get("orientation", DEFAULT_ORIENTATION)); self.aspect_mode_var.set(options.get("aspect_mode", DEFAULT_ASPECT_MODE)); self.horizontal_aspect_var.set(options.get("horizontal_aspect", DEFAULT_HORIZONTAL_ASPECT)); self.vertical_aspect_var.set(options.get("vertical_aspect", DEFAULT_VERTICAL_ASPECT)); self.fruc_var.set(options.get("fruc", DEFAULT_FRUC)); self.fruc_fps_var.set(options.get("fruc_fps", DEFAULT_FRUC_FPS)); self.generate_log_var.set(options.get("generate_log", False))
                self.burn_subtitles_var.set(options.get("burn_subtitles", DEFAULT_BURN_SUBTITLES))
                self.subtitle_font_var.set(options.get("subtitle_font", DEFAULT_SUBTITLE_FONT))
                self.subtitle_font_size_var.set(options.get("subtitle_font_size", DEFAULT_SUBTITLE_FONT_SIZE))
                self.subtitle_alignment_var.set(options.get("subtitle_alignment", DEFAULT_SUBTITLE_ALIGNMENT))
                self.subtitle_bold_var.set(options.get("subtitle_bold", DEFAULT_SUBTITLE_BOLD))
                self.subtitle_italic_var.set(options.get("subtitle_italic", DEFAULT_SUBTITLE_ITALIC))
                self.subtitle_primary_color_var.set(options.get("subtitle_primary_color", DEFAULT_SUBTITLE_PRIMARY_COLOR))
                self.subtitle_outline_color_var.set(options.get("subtitle_outline_color", DEFAULT_SUBTITLE_OUTLINE_COLOR))
                self.subtitle_shadow_color_var.set(options.get("subtitle_shadow_color", DEFAULT_SUBTITLE_SHADOW_COLOR))
                # --- MODIFICATION: Update MarginV GUI on selection ---
                self.subtitle_margin_v_var.set(options.get("subtitle_margin_v", DEFAULT_SUBTITLE_MARGIN_V))
                self.primary_color_swatch.config(bg=self.subtitle_primary_color_var.get())
                self.outline_color_swatch.config(bg=self.subtitle_outline_color_var.get())
                self.shadow_color_swatch.config(bg=self.subtitle_shadow_color_var.get())
                self.toggle_fruc_fps(); self._toggle_orientation_options(); self._toggle_upscale_options()

    def build_nvenc_command_and_run(self, file_path, orientation, ass_burn=None):
        options = self.file_options.get(file_path, {})
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
        if len(audio_streams) > 0: cmd.extend(["--audio-codec", "copy"])
        if is_hdr_output: cmd.extend(["--codec", "hevc", "--profile", "main10", "--output-depth", "10", "--colorprim", "bt2020", "--transfer", "smpte2084", "--colormatrix", "bt2020nc", "--dhdr10-info", "pass"])
        else:
            cmd.extend(["--codec", "h264", "--profile", "high", "--output-depth", "8", "--bframes", "2", "--colorprim", "bt709", "--transfer", "bt709", "--colormatrix", "bt709"])
            if info["is_hdr"] and os.path.exists(self.lut_file): cmd.extend(["--vpp-colorspace", f"lut3d={self.lut_file},lut3d_interp=trilinear"])
        cmd.extend(["--vpp-deinterlace", "adaptive"])
        if options.get("fruc"): cmd.extend(["--vpp-fruc", f"fps={options.get('fruc_fps')}"])
        if options.get("generate_log"): cmd.extend(["--log", "log.log", "--log-level", "debug"])
        
        if ass_burn:
            cmd.extend(["--vpp-subburn", f"filename={ass_burn}"])

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
            
            temp_ass_path = None
            try:
                if options.get("burn_subtitles") and options.get("subtitle_file"):
                    print(f"[INFO] Creating styled subtitle file for {base_name}...")
                    temp_ass_path = create_temporary_ass_file(options["subtitle_file"], options)
                    if temp_ass_path:
                        print(f"[INFO] Subtitle burning enabled for {base_name}.")
                
                print("-" * 80); print(f"Processing: {base_name} (Mode: {orientation_mode})")
                if orientation_mode == "horizontal + vertical":
                    print(f"\n--- Processing HORIZONTAL for: {base_name} ---")
                    self.build_nvenc_command_and_run(file_path, "horizontal", ass_burn=temp_ass_path)
                    print(f"\n--- Processing VERTICAL for: {base_name} ---")
                    self.build_nvenc_command_and_run(file_path, "vertical", ass_burn=temp_ass_path)
                else:
                    self.build_nvenc_command_and_run(file_path, orientation_mode, ass_burn=temp_ass_path)
            
            finally:
                if temp_ass_path and os.path.exists(temp_ass_path):
                    os.remove(temp_ass_path)
                    print(f"[INFO] Cleaned up temporary subtitle file.")
                    
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
    def add_files(self): files = filedialog.askopenfilenames(title="Select Video Files", filetypes=[("Video Files", "*.mp4;*.mkv;*.avi;*.mov;*.webm;*.flv;*.wmv"), ("All Files", "*.*")]); self.update_file_list(files)
    def handle_file_drop(self, event): files = self.root.tk.splitlist(event.data); self.update_file_list(files)
    def remove_selected(self):
        selected_indices = list(self.file_listbox.curselection())
        for index in reversed(selected_indices):
            file_to_remove = self.file_list[index]
            del self.file_options[file_to_remove]
            del self.file_list[index]
            self.file_listbox.delete(index)
    def clear_all(self): self.file_list.clear(); self.file_listbox.delete(0, tk.END); self.file_options.clear()
    def select_all_files(self): self.file_listbox.select_set(0, tk.END); self.on_file_select(None)
    def clear_file_selection(self): self.file_listbox.select_clear(0, tk.END); self.on_file_select(None)
    def detect_subtitle_tracks(self, file_path):
        base_name, _ = os.path.splitext(file_path)
        srt_path = base_name + ".srt"
        if os.path.exists(srt_path) and os.path.getsize(srt_path) > 0:
            self.file_options[file_path]["subtitle_file"] = srt_path
            print(f"[INFO] Found valid subtitle file for {os.path.basename(file_path)}")
        else: self.file_options[file_path]["subtitle_file"] = None
    def toggle_fruc_fps(self): self.fruc_fps_entry.config(state="normal" if self.fruc_var.get() else "disabled")

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