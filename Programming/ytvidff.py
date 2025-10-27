r"""

===============================================================================
YouTube-Compliant Video Encoding and Audio Processing Utility
-------------------------------------------------------------------------------

Overview
--------
This script provides a GUI-based batch transcoding interface built on top of
FFmpeg. It is primarily intended for video creators who need to encode videos
with audio that meets YouTube's official and practical upload requirements.

The tool automates:
    • Video transcoding with FFmpeg
    • Audio normalization (EBU R128 via loudnorm)
    • Multi-track audio handling (Stereo + 5.1)
    • Bitrate, channel layout, and codec compliance for YouTube
    • Batch queue management through a Tkinter GUI
    • Advanced, multi-layer subtitle styling and burning

-------------------------------------------------------------------------------
Version History
-------------------------------------------------------------------------------

v4.9 - Subtitle Content Sanitization (2025-10-27)
    • FIXED: Added a sanitization step within `create_temporary_ass_file` to
      remove any HTML-like tags (e.g., <font>, <i>) from the subtitle text
      content before styling. This prevents these tags from being literally
      burned into the video, resolving a common issue with embedded subtitles.

v4.8 - Unified Subtitle Styling Engine (2025-10-27)
    • ADDED: A new function, `extract_embedded_subtitle`, which uses FFmpeg to
      extract any embedded subtitle track to a temporary .srt file on disk.
    • CHANGED: The core processing logic in `build_ffmpeg_command_and_run` has
      been rewritten. It now uses the new extraction function to treat embedded
      subtitles exactly like external ones.
    • FIXED: All subtitles, whether external or embedded, are now processed
      through the `create_temporary_ass_file` function, ensuring that all GUI
      styling options (font, color, shadow, etc.) are correctly applied.

v4.7 - QoL Improvement for Subtitle Jobs (2025-10-27)
    • CHANGED: When the script creates job entries for external or embedded
      subtitles, the "Enable Subtitle Burning" option is now set to TRUE by
      default for those specific jobs. "No Subtitle" jobs still default to FALSE.
      This improves the workflow by reducing manual checkbox clicks.

v4.6 - Job Creation and Embedded Subtitle Fixes (2025-10-27)
    • FIXED: A critical bug in the FFmpeg command for burning embedded subtitles.
      The script now correctly calculates the subtitle's relative stream index (si)
      instead of using its global index, resolving the "Unable to locate subtitle
      stream" error.
    • REVERTED: The job creation logic has been reverted to the more powerful
      "one job per subtitle variant" model. The script now automatically creates
      separate listbox entries for "No Subtitles" and each discovered external
      and embedded subtitle track for a given video file.
    • REMOVED: The subtitle selection combobox has been removed to simplify the
      GUI, as its functionality is now handled by the main job list.

v4.5 - Embedded Subtitle Detection and Burning (2025-10-27)
    • ADDED: The script now automatically detects embedded subtitle tracks (e.g.,
      SRT, ASS) within video files using ffprobe.
    • ADDED: Embedded subtitles are now listed as distinct jobs in the queue.
    • CHANGED: The FFmpeg command logic was updated to handle both external and
      embedded subtitle types.

v4.4 - Final Multi-Selection and State Management Rewrite (2025-10-27)
    • FIXED: A critical logic bug in the subtitle selection dropdown that has since
      been removed in favor of a better job management model.

v4.3 - Core Multi-Selection Logic Rewrite (2025-10-27)
    • REWRITTEN: The core event handling for all GUI controls has been rewritten.
      Changes are now applied with surgical precision, updating only the specific
      setting that was modified across all selected jobs.

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
import glob

# -------------------------- Configuration / Constants --------------------------
# If you have a custom ffmpeg binary, set environment variable FFMPEG_PATH to its path.
FFMPEG_CMD = os.environ.get("FFMPEG_PATH", "ffmpeg")
FFPROBE_CMD = os.environ.get("FFPROBE_PATH", "ffprobe")

# YouTube-audio recommended parameters (consolidated)
AUDIO_SAMPLE_RATE = 48000
STEREO_BITRATE_K = 384
SURROUND_BITRATE_K = 512
PASSTHROUGH_NORMALIZE_BITRATE_K = 192

# Video & General settings
DEFAULT_LUT_PATH = r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\LUT\NBCU\5-NBCU_PQ2SDR_DL_RESOLVE17-VRT_v1.2.cube"
DEFAULT_RESOLUTION = "4k"
DEFAULT_UPSCALE_ALGO = "lanczos"
DEFAULT_OUTPUT_FORMAT = "sdr"
DEFAULT_ORIENTATION = "horizontal"
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

# --- Audio output mode default ---
DEFAULT_AUDIO_MODE = "stereo+5.1"

# --- Subtitle defaults (Multi-Layer Engine) ---
# General settings that apply to all layers
DEFAULT_SUBTITLE_FONT = "HelveticaNeueLT Std Blk"
DEFAULT_SUBTITLE_FONT_SIZE = "64"
DEFAULT_SUBTITLE_ALIGNMENT = "bottom"
DEFAULT_SUBTITLE_BOLD = True
DEFAULT_SUBTITLE_ITALIC = False
DEFAULT_SUBTITLE_UNDERLINE = False
DEFAULT_SUBTITLE_MARGIN_V = "35"


# Layer 1: Fill (the main text)
DEFAULT_FILL_COLOR = "#FFAA00"
DEFAULT_FILL_ALPHA = 0  # 0 = Opaque, 255 = Invisible

# Layer 2: Outline
DEFAULT_OUTLINE_COLOR = "#000000"
DEFAULT_OUTLINE_ALPHA = 0
DEFAULT_OUTLINE_WIDTH = "9"

# Layer 3: Shadow
DEFAULT_SHADOW_COLOR = "#202020"
DEFAULT_SHADOW_ALPHA = 120 # A bit more transparent
DEFAULT_SHADOW_OFFSET_X = "2"
DEFAULT_SHADOW_OFFSET_Y = "4" # Further down
DEFAULT_SHADOW_BLUR = "5"     # More blur

# Debug mode flag
DEBUG_MODE = False

def debug_print(*args, **kwargs):
    if DEBUG_MODE:
        print("[DEBUG]", *args, **kwargs)

# ----------------------------------------------------------------------------------------------------
env = os.environ.copy()
env["PYTHONIOENCODING"] = "utf-8"

class VideoProcessingError(Exception):
    """Custom exception for video processing errors"""
    pass

def check_cuda_availability():
    try:
        cmd = [FFMPEG_CMD, "-hwaccels"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if "cuda" in result.stdout.lower():
            return True
        else:
            print("[ERROR] CUDA not available in FFmpeg. Available hardware accelerations:")
            print(result.stdout)
            return False
    except Exception as e:
        print(f"[ERROR] Failed to check CUDA availability: {e}")
        return False

def check_ffmpeg_capabilities():
    capabilities = {'cuda': False, 'nvenc': False, 'filters': False}
    try:
        cmd = [FFMPEG_CMD, "-hwaccels"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        capabilities['cuda'] = "cuda" in result.stdout.lower()
        cmd = [FFMPEG_CMD, "-encoders"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        capabilities['nvenc'] = any(x in result.stdout.lower() for x in ['h264_nvenc', 'hevc_nvenc'])
        cmd = [FFMPEG_CMD, "-filters"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        capabilities['filters'] = all(x in result.stdout.lower() for x in ['loudnorm', 'scale_cuda', 'lut3d'])
        return capabilities
    except Exception as e:
        print(f"[ERROR] Failed to check FFmpeg capabilities: {e}")
        return capabilities

def check_decoder_availability(codec_name):
    try:
        cmd = [FFMPEG_CMD, "-decoders"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        decoder_name = f"{codec_name}_cuvid"
        if decoder_name in result.stdout:
            return True, f"CUDA decoder available: {decoder_name}"
        elif codec_name in result.stdout:
            return True, f"Software decoder available: {codec_name}"
        else:
            return False, f"No decoder found for: {codec_name}"
    except Exception as e:
        return False, f"Error checking decoders: {e}"

def safe_ffprobe(cmd, operation="operation"):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30, env=env)
        return result
    except subprocess.TimeoutExpired:
        raise VideoProcessingError(f"FFprobe {operation} timed out after 30 seconds")
    except subprocess.CalledProcessError as e:
        raise VideoProcessingError(f"FFprobe {operation} failed: {e.stderr}")
    except FileNotFoundError:
        raise VideoProcessingError("FFprobe not found. Please ensure FFmpeg is installed and in PATH")
    except Exception as e:
        raise VideoProcessingError(f"Unexpected error during {operation}: {e}")

def safe_ffmpeg_execution(cmd, operation="encoding"):
    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                                 env=env, text=True, encoding='utf-8', errors='replace', bufsize=1)
        output_lines = []
        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            if line:
                output_lines.append(line)
                if "\r" in line:
                    progress = line.split("\r")[-1].strip()
                    sys.stdout.write("\r" + progress)
                else:
                    sys.stdout.write(line)
                sys.stdout.flush()
        process.stdout.close()
        return_code = process.wait()
        if return_code != 0:
            error_output = "".join(output_lines)
            raise VideoProcessingError(f"FFmpeg {operation} failed with return code {return_code}\nFull output:\n{error_output}")
        return return_code
    except FileNotFoundError:
        raise VideoProcessingError("FFmpeg not found. Please ensure FFmpeg is installed and in PATH")
    except Exception as e:
        raise VideoProcessingError(f"Unexpected error during {operation}: {e}")

def hex_to_libass_color(hex_color):
    if not hex_color or not hex_color.startswith("#"): return "&H000000"
    hex_val = hex_color.lstrip('#')
    if len(hex_val) != 6: return "&H000000"
    r, g, b = tuple(int(hex_val[i:i+2], 16) for i in (0, 2, 4))
    return f"&H{b:02X}{g:02X}{r:02X}"

def alpha_to_libass_alpha(alpha_val):
    # In ASS, &HFF is transparent, &H00 is opaque.
    return f"&H{alpha_val:02X}"

def create_temporary_ass_file(srt_path, options):
    """
    [CORRECTED REWRITE - Single Layer]
    This function has been completely rewritten to use a single, robust ASS style.
    It correctly defines outline and shadow properties and uses override tags
    for precise, per-line control of fill, outline, and shadow, including
    separate X/Y offsets and blur. This is the standard, correct approach.
    """
    try:
        with open(srt_path, 'r', encoding='utf-8', errors='replace') as f:
            srt_content = f.read()
    except Exception as e:
        print(f"[ERROR] Could not read SRT file {srt_path}: {e}")
        return None

    # --- 1. Gather all styling options from the GUI ---
    font_name = options.get('subtitle_font', DEFAULT_SUBTITLE_FONT)
    font_size = options.get('subtitle_font_size', DEFAULT_SUBTITLE_FONT_SIZE)
    bold_flag = "-1" if options.get('subtitle_bold', DEFAULT_SUBTITLE_BOLD) else "0"
    italic_flag = "-1" if options.get('subtitle_italic', DEFAULT_SUBTITLE_ITALIC) else "0"
    underline_flag = "-1" if options.get('subtitle_underline', DEFAULT_SUBTITLE_UNDERLINE) else "0"
    margin_v = options.get('subtitle_margin_v', DEFAULT_SUBTITLE_MARGIN_V)
    align_map = {"top": 8, "middle": 5, "bottom": 2}
    alignment = align_map.get(options.get('subtitle_alignment', 'bottom'), 2)

    # Component properties
    fill_color_hex = options.get('fill_color', DEFAULT_FILL_COLOR)
    fill_alpha_val = options.get('fill_alpha', DEFAULT_FILL_ALPHA)
    outline_color_hex = options.get('outline_color', DEFAULT_OUTLINE_COLOR)
    outline_alpha_val = options.get('outline_alpha', DEFAULT_OUTLINE_ALPHA)
    outline_width = float(options.get('outline_width', DEFAULT_OUTLINE_WIDTH))
    shadow_color_hex = options.get('shadow_color', DEFAULT_SHADOW_COLOR)
    shadow_alpha_val = options.get('shadow_alpha', DEFAULT_SHADOW_ALPHA)
    shadow_offset_x = float(options.get('shadow_offset_x', DEFAULT_SHADOW_OFFSET_X))
    shadow_offset_y = float(options.get('shadow_offset_y', DEFAULT_SHADOW_OFFSET_Y))
    shadow_blur = float(options.get('shadow_blur', DEFAULT_SHADOW_BLUR))

    # --- 2. Define a single, powerful style ---
    style_main = (
        f"Style: Main,{font_name},{font_size},"
        f"{hex_to_libass_color(fill_color_hex)},"      # PrimaryColour (Fill)
        "&HFF000000,"                                 # SecondaryColour (Transparent)
        f"{hex_to_libass_color(outline_color_hex)},"   # OutlineColour
        f"{hex_to_libass_color(shadow_color_hex)},"    # BackColour (Shadow Color)
        f"{bold_flag},{italic_flag},{underline_flag},0,100,100,0,0,1,"
        f"{outline_width},{shadow_offset_y},{alignment},10,10,{margin_v},1"
    )

    header = f"""[Script Info]
Title: Corrected Single-Layer Subtitle File
ScriptType: v4.00+
WrapStyle: 0
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
{style_main}

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    dialogue_lines = []
    srt_blocks = re.findall(r'(\d+)\s*\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\s*\n(.*?)(?=\n\n|\Z)', srt_content, re.DOTALL)

    for block in srt_blocks:
        _, start_time, end_time, text = block
        
        # --- SANITIZE TEXT: STRIP ANY HTML-LIKE TAGS ---
        clean_text = re.sub(r'<[^>]+>', '', text)
        
        start_ass = start_time.replace(',', '.')[:-1]
        end_ass = end_time.replace(',', '.')[:-1]
        
        # Use the cleaned text for ASS conversion
        text_ass = clean_text.strip().replace('\n', '\\N')

        tags = (
            f"\\1a{alpha_to_libass_alpha(fill_alpha_val)}"      # Fill alpha
            f"\\3a{alpha_to_libass_alpha(outline_alpha_val)}"   # Outline alpha
            f"\\4a{alpha_to_libass_alpha(shadow_alpha_val)}"    # Shadow alpha
            f"\\xshad{shadow_offset_x}"                         # Shadow X offset
            f"\\yshad{shadow_offset_y}"                         # Shadow Y offset
            f"\\blur{shadow_blur}"                              # Blur (applies to edges of all components)
        )
        
        dialogue_lines.append(f"Dialogue: 0,{start_ass},{end_ass},Main,,0,0,0,,{{{tags}}}{text_ass}")

    full_ass_content = header + "\n".join(dialogue_lines)

    # Create a uniquely named file in the current working directory.
    filename = f"temp_subtitle_{int(time.time() * 1000)}.ass"
    filepath = os.path.join(os.getcwd(), filename)
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(full_ass_content)
        debug_print(f"Created temporary subtitle file: {filepath}")
        return filepath
    except Exception as e:
        print(f"[ERROR] Could not create temporary ASS file in working directory: {e}")
        return None

def get_video_info(file_path):
    cmd = [FFPROBE_CMD, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=pix_fmt,r_frame_rate,height,width,color_transfer,color_primaries,codec_name,codec_tag_string", "-of", "json", file_path]
    try:
        result = safe_ffprobe(cmd, "video info extraction")
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
        codec_tag = data.get("codec_tag_string", "").lower()
        if codec_tag == "av01" or "av1" in codec_name.lower():
            codec_name = "av1"
        return {"bit_depth": bit_depth, "framerate": framerate, "height": height, "width": width, "is_hdr": is_hdr, "codec_name": codec_name}
    except Exception as e:
        print(f"[WARN] Could not get video info for {file_path}, using defaults: {e}")
        return {"bit_depth": 8, "framerate": 30.0, "height": 1080, "width": 1920, "is_hdr": False, "codec_name": "h264"}

def get_audio_stream_info(file_path):
    cmd = [FFPROBE_CMD, "-v", "error", "-select_streams", "a", "-show_entries", "stream=index,channels,channel_layout", "-of", "json", file_path]
    try:
        result = safe_ffprobe(cmd, "audio stream info extraction")
        return json.loads(result.stdout).get("streams", [])
    except Exception as e:
        print(f"[WARN] Could not get detailed audio stream info for {file_path}: {e}")
        return []

def get_subtitle_stream_info(file_path):
    """Probes a video file for embedded subtitle streams."""
    cmd = [FFPROBE_CMD, "-v", "error", "-select_streams", "s", "-show_entries", 
           "stream=index,codec_name:stream_tags=title,language", "-of", "json", file_path]
    try:
        result = safe_ffprobe(cmd, "subtitle stream info extraction")
        return json.loads(result.stdout).get("streams", [])
    except Exception as e:
        print(f"[WARN] Could not get embedded subtitle info for {file_path}: {e}")
        return []

def extract_embedded_subtitle(video_path, subtitle_index):
    """
    Extracts an embedded subtitle stream to a temporary SRT file.
    """
    try:
        # Create a temporary file to store the extracted subtitle
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.srt', encoding='utf-8') as temp_f:
            temp_subtitle_path = temp_f.name

        # Construct the FFmpeg command to extract the specified subtitle stream
        cmd = [
            FFMPEG_CMD,
            '-y', '-hide_banner',
            '-i', video_path,
            '-map', f'0:s:{subtitle_index}', # Map the specific subtitle stream
            '-c:s', 'srt',                   # Convert to SRT format for consistency
            temp_subtitle_path
        ]

        print(f"[INFO] Extracting embedded subtitle stream {subtitle_index} to temporary file...")
        # Use a simple subprocess run for this quick operation
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30, env=env)
        
        # Check if the file was created and is not empty
        if os.path.exists(temp_subtitle_path) and os.path.getsize(temp_subtitle_path) > 0:
            debug_print(f"Successfully extracted subtitle to {temp_subtitle_path}")
            return temp_subtitle_path
        else:
            print(f"[WARN] FFmpeg ran but the extracted subtitle file is empty or missing.")
            os.remove(temp_subtitle_path) # Clean up empty file
            return None

    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Failed to extract subtitle stream {subtitle_index} from {video_path}.")
        print(f"FFmpeg stderr: {e.stderr}")
        if 'temp_subtitle_path' in locals() and os.path.exists(temp_subtitle_path):
            os.remove(temp_subtitle_path)
        return None
    except Exception as e:
        print(f"[ERROR] An unexpected error occurred during subtitle extraction: {e}")
        if 'temp_subtitle_path' in locals() and os.path.exists(temp_subtitle_path):
            os.remove(temp_subtitle_path)
        return None

def get_bitrate(output_resolution_key, framerate, is_hdr):
    BITRATES = {
        "SDR_NORMAL_FPS": {"HD": 16000, "4k": 90000, "8k": 320000},
        "SDR_HIGH_FPS": {"HD": 24000, "4k": 136000, "8k": 480000},
        "HDR_NORMAL_FPS": {"HD": 20000, "4k": 112000, "8k": 400000},
        "HDR_HIGH_FPS": {"HD": 30000, "4k": 170000, "8k": 600000}
    }
    fps_category = "HIGH_FPS" if framerate > 40 else "NORMAL_FPS"
    dr_category = "HDR" if is_hdr else "SDR"
    key = f"{dr_category}_{fps_category}"
    mapped_resolution_key = "HD" if output_resolution_key == "HD" else output_resolution_key.lower()
    return BITRATES.get(key, {}).get(mapped_resolution_key, BITRATES["SDR_NORMAL_FPS"]["HD"])

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)
        self.tip_window = None
    
    def enter(self, event=None):
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify=tk.LEFT, background="#ffffe0", relief=tk.SOLID, borderwidth=1, font=("Arial", 10))
        label.pack()
    
    def leave(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None

class VideoProcessorApp:
    def __init__(self, root, initial_files, output_mode):
        self.root = root
        self.root.title("Video Processing Tool")
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
        self.audio_mode_var = tk.StringVar(value=DEFAULT_AUDIO_MODE)
        self.lut_file_var = tk.StringVar(value=DEFAULT_LUT_PATH)
        self.status_var = tk.StringVar(value="Ready")

        self.subtitle_font_var = tk.StringVar(value=DEFAULT_SUBTITLE_FONT)
        self.subtitle_font_size_var = tk.StringVar(value=DEFAULT_SUBTITLE_FONT_SIZE)
        self.subtitle_alignment_var = tk.StringVar(value=DEFAULT_SUBTITLE_ALIGNMENT)
        self.subtitle_bold_var = tk.BooleanVar(value=DEFAULT_SUBTITLE_BOLD)
        self.subtitle_italic_var = tk.BooleanVar(value=DEFAULT_SUBTITLE_ITALIC)
        self.subtitle_underline_var = tk.BooleanVar(value=DEFAULT_SUBTITLE_UNDERLINE)
        self.subtitle_margin_v_var = tk.StringVar(value=DEFAULT_SUBTITLE_MARGIN_V)
        self.fill_color_var = tk.StringVar(value=DEFAULT_FILL_COLOR)
        self.fill_alpha_var = tk.IntVar(value=DEFAULT_FILL_ALPHA)
        self.outline_color_var = tk.StringVar(value=DEFAULT_OUTLINE_COLOR)
        self.outline_alpha_var = tk.IntVar(value=DEFAULT_OUTLINE_ALPHA)
        self.outline_width_var = tk.StringVar(value=DEFAULT_OUTLINE_WIDTH)
        self.shadow_color_var = tk.StringVar(value=DEFAULT_SHADOW_COLOR)
        self.shadow_alpha_var = tk.IntVar(value=DEFAULT_SHADOW_ALPHA)
        self.shadow_offset_x_var = tk.StringVar(value=DEFAULT_SHADOW_OFFSET_X)
        self.shadow_offset_y_var = tk.StringVar(value=DEFAULT_SHADOW_OFFSET_Y)
        self.shadow_blur_var = tk.StringVar(value=DEFAULT_SHADOW_BLUR)
        
        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind("<<Drop>>", self.handle_file_drop)
        self.setup_gui()
        if initial_files: self.add_video_files_and_discover_jobs(initial_files)

    def setup_gui(self):
        self.root.columnconfigure(0, weight=1, minsize=250)
        self.root.columnconfigure(1, weight=2, minsize=400)
        self.root.columnconfigure(2, weight=2, minsize=400)
        
        input_frame = tk.Frame(self.root); input_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        video_frame = tk.Frame(self.root); video_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        audio_frame = tk.Frame(self.root); audio_frame.grid(row=0, column=2, sticky="nsew", padx=5, pady=5)
        button_frame = tk.Frame(self.root); button_frame.grid(row=1, column=0, columnspan=3, sticky="ew", padx=10, pady=10)
        status_bar = tk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W); status_bar.grid(row=2, column=0, columnspan=3, sticky="ew", padx=5, pady=2)
        
        self.setup_input_column(input_frame)
        self.setup_video_column(video_frame)
        self.setup_audio_column(audio_frame)
        self.setup_button_row(button_frame)
        
        self._toggle_orientation_options()
        self._toggle_upscale_options()
        self._toggle_audio_norm_options()
        self._update_bitrate_display()

    def setup_input_column(self, parent):
        file_group = tk.LabelFrame(parent, text="Input Files", padx=10, pady=10); file_group.pack(fill=tk.BOTH, expand=True)
        listbox_container = tk.Frame(file_group); listbox_container.pack(fill=tk.BOTH, expand=True)
        self.job_scrollbar_v = tk.Scrollbar(listbox_container, orient=tk.VERTICAL); self.job_scrollbar_v.pack(side=tk.RIGHT, fill=tk.Y)
        self.job_scrollbar_h = tk.Scrollbar(listbox_container, orient=tk.HORIZONTAL); self.job_scrollbar_h.pack(side=tk.BOTTOM, fill=tk.X)
        self.job_listbox = tk.Listbox(listbox_container, selectmode=tk.EXTENDED, exportselection=False, yscrollcommand=self.job_scrollbar_v.set, xscrollcommand=self.job_scrollbar_h.set); self.job_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.job_scrollbar_v.config(command=self.job_listbox.yview)
        self.job_scrollbar_h.config(command=self.job_listbox.xview)
        self.job_listbox.bind("<<ListboxSelect>>", self.on_input_file_select)
        selection_buttons_frame = tk.Frame(file_group); selection_buttons_frame.pack(fill=tk.X, pady=(5, 0))
        tk.Button(selection_buttons_frame, text="Select All", command=self.select_all_files).pack(side=tk.LEFT)
        tk.Button(selection_buttons_frame, text="Clear Selection", command=self.clear_file_selection).pack(side=tk.LEFT, padx=5)
        file_buttons_frame = tk.Frame(file_group); file_buttons_frame.pack(fill=tk.X, pady=(5, 0))
        tk.Button(file_buttons_frame, text="Add Files...", command=self.add_files).pack(side=tk.LEFT, padx=(0,5))
        tk.Button(file_buttons_frame, text="Remove Selected", command=self.remove_selected).pack(side=tk.LEFT, padx=5)
        tk.Button(file_buttons_frame, text="Duplicate Selected", command=self.duplicate_selected_jobs).pack(side=tk.LEFT, padx=5)
        tk.Button(file_buttons_frame, text="Clear All", command=self.clear_all).pack(side=tk.LEFT, padx=5)

    def setup_video_column(self, parent):
        geometry_group = tk.LabelFrame(parent, text="Output & Geometry", padx=10, pady=10); geometry_group.pack(fill=tk.X, pady=(0, 5))
        orientation_frame = tk.Frame(geometry_group); orientation_frame.pack(fill=tk.X)
        tk.Label(orientation_frame, text="Orientation:").pack(side=tk.LEFT, padx=(0,5))
        tk.Radiobutton(orientation_frame, text="Horizontal", variable=self.orientation_var, value="horizontal", command=self._toggle_orientation_options).pack(side=tk.LEFT)
        tk.Radiobutton(orientation_frame, text="Vertical", variable=self.orientation_var, value="vertical", command=self._toggle_orientation_options).pack(side=tk.LEFT)
        tk.Radiobutton(orientation_frame, text="Both", variable=self.orientation_var, value="horizontal + vertical", command=self._toggle_orientation_options).pack(side=tk.LEFT)
        tk.Radiobutton(orientation_frame, text="Original", variable=self.orientation_var, value="original", command=self._toggle_orientation_options).pack(side=tk.LEFT)
        self.aspect_ratio_frame = tk.LabelFrame(geometry_group, text="Aspect Ratio", padx=10, pady=5); self.aspect_ratio_frame.pack(fill=tk.X, pady=5)
        self.horizontal_rb_frame = tk.Frame(self.aspect_ratio_frame)
        tk.Radiobutton(self.horizontal_rb_frame, text="16:9 (Widescreen)", variable=self.horizontal_aspect_var, value="16:9", command=lambda: self._update_selected_jobs("horizontal_aspect")).pack(anchor="w")
        tk.Radiobutton(self.horizontal_rb_frame, text="5:4", variable=self.horizontal_aspect_var, value="5:4", command=lambda: self._update_selected_jobs("horizontal_aspect")).pack(anchor="w")
        tk.Radiobutton(self.horizontal_rb_frame, text="4:3 (Classic TV)", variable=self.horizontal_aspect_var, value="4:3", command=lambda: self._update_selected_jobs("horizontal_aspect")).pack(anchor="w")
        self.vertical_rb_frame = tk.Frame(self.aspect_ratio_frame)
        tk.Radiobutton(self.vertical_rb_frame, text="9:16 (Shorts/Reels)", variable=self.vertical_aspect_var, value="9:16", command=lambda: self._update_selected_jobs("vertical_aspect")).pack(anchor="w")
        tk.Radiobutton(self.vertical_rb_frame, text="4:5 (Instagram Post)", variable=self.vertical_aspect_var, value="4:5", command=lambda: self._update_selected_jobs("vertical_aspect")).pack(anchor="w")
        tk.Radiobutton(self.vertical_rb_frame, text="3:4 (Social Post)", variable=self.vertical_aspect_var, value="3:4", command=lambda: self._update_selected_jobs("vertical_aspect")).pack(anchor="w")
        aspect_handling_frame = tk.Frame(geometry_group); aspect_handling_frame.pack(fill=tk.X)
        tk.Label(aspect_handling_frame, text="Handling:").pack(side=tk.LEFT, padx=(0,5))
        tk.Radiobutton(aspect_handling_frame, text="Crop (Fill)", variable=self.aspect_mode_var, value="crop", command=self._toggle_upscale_options).pack(side=tk.LEFT)
        tk.Radiobutton(aspect_handling_frame, text="Pad (Fit)", variable=self.aspect_mode_var, value="pad", command=self._toggle_upscale_options).pack(side=tk.LEFT)
        tk.Radiobutton(aspect_handling_frame, text="Stretch", variable=self.aspect_mode_var, value="stretch", command=self._toggle_upscale_options).pack(side=tk.LEFT)
        quality_group = tk.LabelFrame(parent, text="Format & Quality", padx=10, pady=10); quality_group.pack(fill=tk.X, pady=(0, 5))
        resolution_options_frame = tk.Frame(quality_group); resolution_options_frame.pack(fill=tk.X)
        tk.Label(resolution_options_frame, text="Resolution:").pack(side=tk.LEFT, padx=(0,5))
        self.rb_hd = tk.Radiobutton(resolution_options_frame, text="HD", variable=self.resolution_var, value="HD", command=lambda: self._update_selected_jobs("resolution")); self.rb_hd.pack(side=tk.LEFT)
        self.rb_4k = tk.Radiobutton(resolution_options_frame, text="4k", variable=self.resolution_var, value="4k", command=lambda: self._update_selected_jobs("resolution")); self.rb_4k.pack(side=tk.LEFT)
        self.rb_8k = tk.Radiobutton(resolution_options_frame, text="8k", variable=self.resolution_var, value="8k", command=lambda: self._update_selected_jobs("resolution")); self.rb_8k.pack(side=tk.LEFT)
        ToolTip(self.rb_hd, "HD: 1920x1080 resolution"); ToolTip(self.rb_4k, "4K: 3840x2160 resolution"); ToolTip(self.rb_8k, "8K: 7680x4320 resolution")
        upscale_frame = tk.Frame(quality_group); upscale_frame.pack(fill=tk.X, pady=(5,0))
        tk.Label(upscale_frame, text="Upscale Algo:").pack(side=tk.LEFT, padx=(0,5))
        tk.Radiobutton(upscale_frame, text="Lanczos (Sharp)", variable=self.upscale_algo_var, value="lanczos", command=lambda: self._update_selected_jobs("upscale_algo")).pack(side=tk.LEFT)
        tk.Radiobutton(upscale_frame, text="Bicubic (Balanced)", variable=self.upscale_algo_var, value="bicubic", command=lambda: self._update_selected_jobs("upscale_algo")).pack(side=tk.LEFT)
        tk.Radiobutton(upscale_frame, text="Bilinear (Fast)", variable=self.upscale_algo_var, value="bilinear", command=lambda: self._update_selected_jobs("upscale_algo")).pack(side=tk.LEFT)
        output_format_frame = tk.Frame(quality_group); output_format_frame.pack(fill=tk.X, pady=(5,0))
        tk.Label(output_format_frame, text="Output Format:").pack(side=tk.LEFT, padx=(0,5))
        tk.Radiobutton(output_format_frame, text="SDR", variable=self.output_format_var, value="sdr", command=lambda: self._update_selected_jobs("output_format")).pack(side=tk.LEFT)
        tk.Radiobutton(output_format_frame, text="HDR", variable=self.output_format_var, value="hdr", command=lambda: self._update_selected_jobs("output_format")).pack(side=tk.LEFT)
        tk.Label(output_format_frame, text="Location:").pack(side=tk.LEFT, padx=(15,5))
        tk.Radiobutton(output_format_frame, text="Local", variable=self.output_mode_var, value="local").pack(side=tk.LEFT)
        tk.Radiobutton(output_format_frame, text="Pooled", variable=self.output_mode_var, value="pooled").pack(side=tk.LEFT)
        lut_frame = tk.Frame(quality_group); lut_frame.pack(fill=tk.X, pady=(5,0))
        tk.Label(lut_frame, text="LUT Path:").pack(side=tk.LEFT, padx=(0,5))
        self.lut_entry = tk.Entry(lut_frame, textvariable=self.lut_file_var, width=30); self.lut_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.lut_entry.bind("<FocusOut>", lambda e: self._update_selected_jobs_event(e, "lut_file"))
        tk.Button(lut_frame, text="Browse", command=self.browse_lut_file).pack(side=tk.LEFT)
        ToolTip(self.lut_entry, "Path to LUT file for HDR to SDR conversion")
        bitrate_frame = tk.Frame(quality_group); bitrate_frame.pack(fill=tk.X, pady=(5,0))
        tk.Checkbutton(bitrate_frame, text="Override Bitrate", variable=self.override_bitrate_var, command=self._toggle_bitrate_override).pack(side=tk.LEFT)
        self.manual_bitrate_entry = tk.Entry(bitrate_frame, textvariable=self.manual_bitrate_var, width=10, state="disabled"); self.manual_bitrate_entry.pack(side=tk.LEFT, padx=5)
        self.manual_bitrate_entry.bind("<FocusOut>", lambda e: self._update_selected_jobs_event(e, "manual_bitrate"))
        tk.Label(bitrate_frame, text="kbps").pack(side=tk.LEFT)
        fruc_frame = tk.Frame(quality_group); fruc_frame.pack(fill=tk.X, pady=(5,0))
        tk.Checkbutton(fruc_frame, text="Enable FRUC", variable=self.fruc_var, command=lambda: [self.toggle_fruc_fps(), self._update_selected_jobs("fruc")]).pack(side=tk.LEFT)
        tk.Label(fruc_frame, text="FRUC FPS:").pack(side=tk.LEFT, padx=(5,5))
        self.fruc_fps_entry = tk.Entry(fruc_frame, textvariable=self.fruc_fps_var, width=5, state="disabled"); self.fruc_fps_entry.pack(side=tk.LEFT)
        self.fruc_fps_entry.bind("<FocusOut>", lambda e: self._update_selected_jobs_event(e, "fruc_fps"))

    def setup_audio_column(self, parent):
        subtitle_group = tk.LabelFrame(parent, text="Subtitle Styling", padx=10, pady=10)
        subtitle_group.pack(fill=tk.X, pady=(0, 5), expand=True)

        # --- General Styling ---
        general_style_frame = tk.LabelFrame(subtitle_group, text="General Style", padx=5, pady=5)
        general_style_frame.pack(fill=tk.X, pady=5)
        
        font_frame = tk.Frame(general_style_frame); font_frame.pack(fill=tk.X, pady=2)
        tk.Label(font_frame, text="Font:").pack(side=tk.LEFT, padx=(0, 19))
        self.font_combo = ttk.Combobox(font_frame, textvariable=self.subtitle_font_var, width=20)
        self.font_combo.pack(side=tk.LEFT, padx=5)
        self.font_combo.bind("<<ComboboxSelected>>", lambda e: self._update_selected_jobs_event(e, "subtitle_font"))
        self.populate_fonts()
        tk.Label(font_frame, text="Size:").pack(side=tk.LEFT, padx=(10, 5))
        font_size_entry = tk.Entry(font_frame, textvariable=self.subtitle_font_size_var, width=5)
        font_size_entry.pack(side=tk.LEFT)
        font_size_entry.bind("<FocusOut>", lambda e: self._update_selected_jobs_event(e, "subtitle_font_size"))

        style_frame = tk.Frame(general_style_frame); style_frame.pack(fill=tk.X, pady=2)
        tk.Checkbutton(style_frame, text="Bold", variable=self.subtitle_bold_var, command=lambda: self._update_selected_jobs("subtitle_bold")).pack(side=tk.LEFT)
        tk.Checkbutton(style_frame, text="Italic", variable=self.subtitle_italic_var, command=lambda: self._update_selected_jobs("subtitle_italic")).pack(side=tk.LEFT, padx=15)
        tk.Checkbutton(style_frame, text="Underline", variable=self.subtitle_underline_var, command=lambda: self._update_selected_jobs("subtitle_underline")).pack(side=tk.LEFT)
        
        align_frame = tk.Frame(general_style_frame); align_frame.pack(fill=tk.X, pady=2)
        tk.Label(align_frame, text="Align:").pack(side=tk.LEFT, padx=(0, 15))
        tk.Radiobutton(align_frame, text="Top", variable=self.subtitle_alignment_var, value="top", command=lambda: self._update_selected_jobs("subtitle_alignment")).pack(side=tk.LEFT)
        tk.Radiobutton(align_frame, text="Mid", variable=self.subtitle_alignment_var, value="middle", command=lambda: self._update_selected_jobs("subtitle_alignment")).pack(side=tk.LEFT, padx=5)
        tk.Radiobutton(align_frame, text="Bot", variable=self.subtitle_alignment_var, value="bottom", command=lambda: self._update_selected_jobs("subtitle_alignment")).pack(side=tk.LEFT)
        tk.Label(align_frame, text="V-Margin:").pack(side=tk.LEFT, padx=(10, 5))
        margin_v_entry = tk.Entry(align_frame, textvariable=self.subtitle_margin_v_var, width=5)
        margin_v_entry.pack(side=tk.LEFT)
        margin_v_entry.bind("<FocusOut>", lambda e: self._update_selected_jobs_event(e, "subtitle_margin_v"))
        
        # --- Fill Properties ---
        fill_props_frame = tk.LabelFrame(subtitle_group, text="Fill Properties", padx=5, pady=5)
        fill_props_frame.pack(fill=tk.X, pady=5)
        fill_props_frame.columnconfigure(3, weight=1)
        tk.Label(fill_props_frame, text="Color:").grid(row=0, column=0, sticky="w", padx=(0,5))
        self.fill_swatch = tk.Label(fill_props_frame, text="    ", bg=self.fill_color_var.get(), relief="sunken"); self.fill_swatch.grid(row=0, column=1)
        tk.Button(fill_props_frame, text="..", command=lambda: self.choose_color(self.fill_color_var, self.fill_swatch, "fill_color")).grid(row=0, column=2, padx=5)
        fill_alpha_scale = tk.Scale(fill_props_frame, from_=0, to=255, orient=tk.HORIZONTAL, variable=self.fill_alpha_var, showvalue=0, command=lambda val: self._update_selected_jobs("fill_alpha"))
        fill_alpha_scale.grid(row=0, column=3, sticky="ew")
        ToolTip(fill_alpha_scale, "Fill Alpha (Transparency)")

        # --- Outline Properties ---
        outline_props_frame = tk.LabelFrame(subtitle_group, text="Outline Properties", padx=5, pady=5)
        outline_props_frame.pack(fill=tk.X, pady=5)
        outline_props_frame.columnconfigure(3, weight=1)
        tk.Label(outline_props_frame, text="Color:").grid(row=0, column=0, sticky="w", padx=(0,5))
        self.outline_swatch = tk.Label(outline_props_frame, text="    ", bg=self.outline_color_var.get(), relief="sunken"); self.outline_swatch.grid(row=0, column=1)
        tk.Button(outline_props_frame, text="..", command=lambda: self.choose_color(self.outline_color_var, self.outline_swatch, "outline_color")).grid(row=0, column=2, padx=5)
        outline_alpha_scale = tk.Scale(outline_props_frame, from_=0, to=255, orient=tk.HORIZONTAL, variable=self.outline_alpha_var, showvalue=0, command=lambda val: self._update_selected_jobs("outline_alpha"))
        outline_alpha_scale.grid(row=0, column=3, sticky="ew")
        ToolTip(outline_alpha_scale, "Outline Alpha (Transparency)")
        tk.Label(outline_props_frame, text="Width:").grid(row=1, column=0, sticky="w", pady=(5,0))
        outline_width_entry = tk.Entry(outline_props_frame, textvariable=self.outline_width_var, width=5)
        outline_width_entry.grid(row=1, column=1, columnspan=2, sticky="w", pady=(5,0))
        outline_width_entry.bind("<FocusOut>", lambda e: self._update_selected_jobs_event(e, "outline_width"))

        # --- Shadow Properties ---
        shadow_props_frame = tk.LabelFrame(subtitle_group, text="Shadow Properties", padx=5, pady=5)
        shadow_props_frame.pack(fill=tk.X, pady=5)
        shadow_props_frame.columnconfigure(3, weight=1)
        tk.Label(shadow_props_frame, text="Color:").grid(row=0, column=0, sticky="w", padx=(0,5))
        self.shadow_swatch = tk.Label(shadow_props_frame, text="    ", bg=self.shadow_color_var.get(), relief="sunken"); self.shadow_swatch.grid(row=0, column=1)
        tk.Button(shadow_props_frame, text="..", command=lambda: self.choose_color(self.shadow_color_var, self.shadow_swatch, "shadow_color")).grid(row=0, column=2, padx=5)
        shadow_alpha_scale = tk.Scale(shadow_props_frame, from_=0, to=255, orient=tk.HORIZONTAL, variable=self.shadow_alpha_var, showvalue=0, command=lambda val: self._update_selected_jobs("shadow_alpha"))
        shadow_alpha_scale.grid(row=0, column=3, sticky="ew")
        ToolTip(shadow_alpha_scale, "Shadow Alpha (Transparency)")
        
        offset_frame = tk.Frame(shadow_props_frame); offset_frame.grid(row=1, column=0, columnspan=4, sticky="w", pady=(5,0))
        tk.Label(offset_frame, text="Offset X:").pack(side=tk.LEFT)
        shadow_offset_x_entry = tk.Entry(offset_frame, textvariable=self.shadow_offset_x_var, width=5)
        shadow_offset_x_entry.pack(side=tk.LEFT, padx=(5,10))
        shadow_offset_x_entry.bind("<FocusOut>", lambda e: self._update_selected_jobs_event(e, "shadow_offset_x"))
        tk.Label(offset_frame, text="Y:").pack(side=tk.LEFT)
        shadow_offset_y_entry = tk.Entry(offset_frame, textvariable=self.shadow_offset_y_var, width=5)
        shadow_offset_y_entry.pack(side=tk.LEFT, padx=5)
        shadow_offset_y_entry.bind("<FocusOut>", lambda e: self._update_selected_jobs_event(e, "shadow_offset_y"))
        tk.Label(offset_frame, text="Edge Blur:").pack(side=tk.LEFT, padx=(10,5))
        shadow_blur_entry = tk.Entry(offset_frame, textvariable=self.shadow_blur_var, width=5)
        shadow_blur_entry.pack(side=tk.LEFT, padx=5)
        shadow_blur_entry.bind("<FocusOut>", lambda e: self._update_selected_jobs_event(e, "shadow_blur"))
        ToolTip(shadow_blur_entry, "Applies a blur to the edges of the text, outline, and shadow.")

        action_frame = tk.Frame(subtitle_group)
        action_frame.pack(fill=tk.X, pady=(10,0))
        
        tk.Checkbutton(action_frame, text="Enable Subtitle Burning", variable=self.burn_subtitles_var, command=lambda: self._update_selected_jobs("burn_subtitles")).pack(side=tk.LEFT)
        
        # --- Audio Processing Section ---
        audio_group = tk.LabelFrame(parent, text="Audio Processing", padx=10, pady=10)
        audio_group.pack(fill=tk.X, pady=(5, 0))
        tk.Checkbutton(audio_group, text="Normalize Audio", variable=self.normalize_audio_var, command=self._toggle_audio_norm_options).pack(anchor="w")
        self.audio_mode_frame = tk.Frame(audio_group)
        self.audio_mode_frame.pack(fill=tk.X, padx=(20,0), pady=(4,0))
        tk.Label(self.audio_mode_frame, text="Output Mode:").pack(side=tk.LEFT)
        tk.Radiobutton(self.audio_mode_frame, text="Stereo + 5.1", variable=self.audio_mode_var, value="stereo+5.1", command=lambda: self._update_selected_jobs("audio_mode")).pack(side=tk.LEFT)
        tk.Radiobutton(self.audio_mode_frame, text="Passthrough", variable=self.audio_mode_var, value="passthrough", command=lambda: self._update_selected_jobs("audio_mode")).pack(side=tk.LEFT)
        self.audio_norm_frame = tk.Frame(audio_group)
        self.audio_norm_frame.pack(fill=tk.X, padx=(20, 0))
        
        lufs_frame = tk.Frame(self.audio_norm_frame); lufs_frame.pack(fill=tk.X, pady=1)
        tk.Label(lufs_frame, text="Loudness Target (LUFS):").pack(side=tk.LEFT)
        self.loudness_target_entry = tk.Entry(lufs_frame, textvariable=self.loudness_target_var, width=6)
        self.loudness_target_entry.pack(side=tk.LEFT, padx=5)
        self.loudness_target_entry.bind("<FocusOut>", lambda e: self._update_selected_jobs_event(e, "loudness_target"))
        
        lra_frame = tk.Frame(self.audio_norm_frame); lra_frame.pack(fill=tk.X, pady=1)
        tk.Label(lra_frame, text="Loudness Range (LRA):").pack(side=tk.LEFT)
        self.loudness_range_entry = tk.Entry(lra_frame, textvariable=self.loudness_range_var, width=6)
        self.loudness_range_entry.pack(side=tk.LEFT, padx=5)
        self.loudness_range_entry.bind("<FocusOut>", lambda e: self._update_selected_jobs_event(e, "loudness_range"))
        
        peak_frame = tk.Frame(self.audio_norm_frame); peak_frame.pack(fill=tk.X, pady=1)
        tk.Label(peak_frame, text="True Peak (dBTP):").pack(side=tk.LEFT)
        self.true_peak_entry = tk.Entry(peak_frame, textvariable=self.true_peak_var, width=6)
        self.true_peak_entry.pack(side=tk.LEFT, padx=5)
        self.true_peak_entry.bind("<FocusOut>", lambda e: self._update_selected_jobs_event(e, "true_peak"))

    def setup_button_row(self, parent):
        self.start_button = tk.Button(parent, text="Start Processing", command=self.start_processing, bg="#4CAF50", fg="white", font=font.Font(weight="bold")); self.start_button.pack(side=tk.LEFT, padx=5, ipady=5)
        self.generate_log_checkbox = tk.Checkbutton(parent, text="Generate Log File", variable=self.generate_log_var, command=lambda: self._update_selected_jobs("generate_log")); self.generate_log_checkbox.pack(side=tk.LEFT, padx=(10, 0))

    def populate_fonts(self):
        try:
            fonts = sorted(list(font.families()))
            self.font_combo['values'] = fonts
            if DEFAULT_SUBTITLE_FONT in fonts:
                self.font_combo.set(DEFAULT_SUBTITLE_FONT)
            elif fonts:
                self.font_combo.set(fonts[0])
        except Exception as e:
            print(f"[WARN] Could not load system fonts: {e}")
            self.font_combo['values'] = [DEFAULT_SUBTITLE_FONT]
            self.font_combo.set(DEFAULT_SUBTITLE_FONT)

    def choose_color(self, color_var, swatch_label, key_to_update):
        initial_color = color_var.get()
        color_code = colorchooser.askcolor(title="Choose color", initialcolor=initial_color)
        if color_code and color_code[1]:
            hex_color = color_code[1]
            color_var.set(hex_color)
            swatch_label.config(bg=hex_color)
            self._update_selected_jobs(key_to_update)

    def browse_lut_file(self):
        file_path = filedialog.askopenfilename(title="Select LUT File", filetypes=[("LUT files", "*.cube;*.3dl;*.dat"), ("All files", "*.*")])
        if file_path:
            self.lut_file_var.set(file_path)
            self._update_selected_jobs("lut_file")

    def _toggle_bitrate_override(self):
        is_override = self.override_bitrate_var.get()
        self.manual_bitrate_entry.config(state="normal" if is_override else "disabled")
        if not is_override:
            self._update_bitrate_display()
        self._update_selected_jobs("override_bitrate", "manual_bitrate")

    def _update_bitrate_display(self):
        if self.override_bitrate_var.get(): return
        selected_indices = self.job_listbox.curselection()
        ref_job = self.processing_jobs[selected_indices[0]] if selected_indices else (self.processing_jobs[0] if self.processing_jobs else None)
        if ref_job:
            info = get_video_info(ref_job['video_path'])
            bitrate = get_bitrate(self.resolution_var.get(), info["framerate"], self.output_format_var.get() == 'hdr')
            self.manual_bitrate_var.set(str(bitrate))

    def _toggle_orientation_options(self):
        orientation = self.orientation_var.get()
        self.horizontal_rb_frame.pack_forget(); self.vertical_rb_frame.pack_forget()
        if orientation == "horizontal": self.aspect_ratio_frame.config(text="Horizontal Aspect Ratio"); self.horizontal_rb_frame.pack(fill="x")
        elif orientation == "vertical": self.aspect_ratio_frame.config(text="Vertical Aspect Ratio"); self.vertical_rb_frame.pack(fill="x")
        elif orientation == "horizontal + vertical": self.aspect_ratio_frame.config(text="Aspect Ratios (H & V)"); self.horizontal_rb_frame.pack(fill="x", pady=(0, 5)); self.vertical_rb_frame.pack(fill="x")
        elif orientation == "original": self.aspect_ratio_frame.config(text="Aspect Ratio (Original – unchanged)")
        self._update_selected_jobs("orientation")

    def _toggle_upscale_options(self): 
        self._update_selected_jobs("aspect_mode")
        
    def _toggle_audio_norm_options(self):
        state = "normal" if self.normalize_audio_var.get() else "disabled"
        for widget in [self.loudness_target_entry, self.loudness_range_entry, self.true_peak_entry]:
            widget.config(state=state)
        self._update_selected_jobs("normalize_audio")

    def update_status(self, message): self.status_var.set(message); self.root.update_idletasks()

    def _update_selected_jobs_event(self, event, *keys_to_update):
        """Helper for event bindings that call _update_selected_jobs."""
        self._update_selected_jobs(*keys_to_update)

    def _update_selected_jobs(self, *keys_to_update):
        """
        [CORRECTED LOGIC]
        Applies only the specified GUI options to the selected jobs.
        This prevents overwriting unrelated settings during bulk edits.
        """
        selected_indices = self.job_listbox.curselection()
        if not selected_indices:
            return

        current_options = self.get_current_gui_options()
        
        options_to_apply = {key: current_options[key] for key in keys_to_update if key in current_options}

        for index in selected_indices:
            job = self.processing_jobs[index]
            job['options'].update(options_to_apply)
            
        debug_print(f"Applied {options_to_apply} to {len(selected_indices)} jobs.")
    
    def get_current_gui_options(self):
        return {
            "resolution": self.resolution_var.get(), "upscale_algo": self.upscale_algo_var.get(),
            "output_format": self.output_format_var.get(), "fruc": self.fruc_var.get(),
            "fruc_fps": self.fruc_fps_var.get(), "generate_log": self.generate_log_var.get(),
            "orientation": self.orientation_var.get(), "aspect_mode": self.aspect_mode_var.get(),
            "horizontal_aspect": self.horizontal_aspect_var.get(), "vertical_aspect": self.vertical_aspect_var.get(),
            "burn_subtitles": self.burn_subtitles_var.get(), "override_bitrate": self.override_bitrate_var.get(),
            "manual_bitrate": self.manual_bitrate_var.get(), "normalize_audio": self.normalize_audio_var.get(),
            "loudness_target": self.loudness_target_var.get(), "loudness_range": self.loudness_range_var.get(),
            "true_peak": self.true_peak_var.get(), "audio_mode": self.audio_mode_var.get(),
            "lut_file": self.lut_file_var.get(), 
            
            "subtitle_font": self.subtitle_font_var.get(), "subtitle_font_size": self.subtitle_font_size_var.get(),
            "subtitle_alignment": self.subtitle_alignment_var.get(), "subtitle_bold": self.subtitle_bold_var.get(),
            "subtitle_italic": self.subtitle_italic_var.get(), "subtitle_underline": self.subtitle_underline_var.get(),
            "subtitle_margin_v": self.subtitle_margin_v_var.get(), "fill_color": self.fill_color_var.get(),
            "fill_alpha": self.fill_alpha_var.get(), "outline_color": self.outline_color_var.get(),
            "outline_alpha": self.outline_alpha_var.get(), "outline_width": self.outline_width_var.get(),
            "shadow_color": self.shadow_color_var.get(), "shadow_alpha": self.shadow_alpha_var.get(),
            "shadow_offset_x": self.shadow_offset_x_var.get(), "shadow_offset_y": self.shadow_offset_y_var.get(),
            "shadow_blur": self.shadow_blur_var.get(),
        }

    def add_video_files_and_discover_jobs(self, file_paths):
        for video_path in file_paths:
            video_path = os.path.abspath(video_path)
            dir_name, video_basename = os.path.dirname(video_path), os.path.splitext(os.path.basename(video_path))[0]
            current_options = self.get_current_gui_options()

            # Create and add the "No Subtitles" job first
            no_sub_job = {
                "job_id": f"job_{time.time()}_{len(self.processing_jobs)}",
                "video_path": video_path,
                "subtitle_path": None,
                "options": copy.deepcopy(current_options)
            }
            no_sub_job["display_name"] = f"{os.path.basename(video_path)} [No Subtitles]"
            self.processing_jobs.append(no_sub_job)
            self.job_listbox.insert(tk.END, no_sub_job["display_name"])

            # Discover and add jobs for external .srt files
            try:
                for item in os.listdir(dir_name):
                    if item.lower().endswith('.srt'):
                        srt_basename = os.path.splitext(item)[0]
                        if srt_basename == video_basename or (srt_basename.startswith(video_basename) and len(srt_basename) > len(video_basename) and srt_basename[len(video_basename)] in [' ', '.', '-', '_']):
                            full_path = os.path.join(dir_name, item)
                            tag = srt_basename[len(video_basename):].strip(' .-_') or "(exact match)"
                            
                            sub_job = copy.deepcopy(no_sub_job) # Create job from base
                            sub_job['job_id'] = f"job_{time.time()}_{len(self.processing_jobs)}"
                            sub_job['subtitle_path'] = full_path
                            sub_job['options']['burn_subtitles'] = True # Enable burn by default
                            sub_job['display_name'] = f"{os.path.basename(video_path)} [Sub: {tag}]"
                            self.processing_jobs.append(sub_job)
                            self.job_listbox.insert(tk.END, sub_job['display_name'])
            except Exception as e:
                print(f"[WARN] Could not scan for external subtitles in {dir_name}: {e}")

            # Discover and add jobs for embedded subtitle streams
            embedded_subs = get_subtitle_stream_info(video_path)
            for relative_index, sub_stream in enumerate(embedded_subs):
                tags = sub_stream.get("tags", {})
                lang = tags.get("language", "und")
                title = tags.get("title", f"Track {sub_stream.get('index')}")
                codec = sub_stream.get('codec_name', 'sub').upper()
                
                sub_job = copy.deepcopy(no_sub_job) # Create job from base
                sub_job['job_id'] = f"job_{time.time()}_{len(self.processing_jobs)}"
                sub_job['subtitle_path'] = f"embedded:{relative_index}" # Store the CORRECT relative index
                sub_job['options']['burn_subtitles'] = True # Enable burn by default
                sub_job['display_name'] = f"{os.path.basename(video_path)} [Embedded: {lang.title()} - {title} ({codec})]"
                self.processing_jobs.append(sub_job)
                self.job_listbox.insert(tk.END, sub_job['display_name'])

        if self.processing_jobs:
            self.job_listbox.selection_clear(0, tk.END)
            self.job_listbox.selection_set(0)
            self.on_input_file_select(None)
        self._update_bitrate_display()

    def on_input_file_select(self, event):
        sel = self.job_listbox.curselection()
        if len(sel) == 1:
            selected_job = self.processing_jobs[sel[0]]
            self.update_gui_from_job_options(selected_job)

    def update_gui_from_job_options(self, job):
        options = job['options']
        self.resolution_var.set(options.get("resolution", DEFAULT_RESOLUTION)); self.upscale_algo_var.set(options.get("upscale_algo", DEFAULT_UPSCALE_ALGO)); self.output_format_var.set(options.get("output_format", DEFAULT_OUTPUT_FORMAT))
        self.orientation_var.set(options.get("orientation", DEFAULT_ORIENTATION)); self.aspect_mode_var.set(options.get("aspect_mode", DEFAULT_ASPECT_MODE)); self.horizontal_aspect_var.set(options.get("horizontal_aspect", DEFAULT_HORIZONTAL_ASPECT))
        self.vertical_aspect_var.set(options.get("vertical_aspect", DEFAULT_VERTICAL_ASPECT)); self.fruc_var.set(options.get("fruc", DEFAULT_FRUC)); self.fruc_fps_var.set(options.get("fruc_fps", DEFAULT_FRUC_FPS))
        self.generate_log_var.set(options.get("generate_log", False)); self.burn_subtitles_var.set(options.get("burn_subtitles", DEFAULT_BURN_SUBTITLES)); self.override_bitrate_var.set(options.get("override_bitrate", False))
        self.manual_bitrate_var.set(options.get("manual_bitrate", "0")); self.normalize_audio_var.set(options.get("normalize_audio", DEFAULT_NORMALIZE_AUDIO)); self.loudness_target_var.set(options.get("loudness_target", DEFAULT_LOUDNESS_TARGET))
        self.loudness_range_var.set(options.get("loudness_range", DEFAULT_LOUDNESS_RANGE)); self.true_peak_var.set(options.get("true_peak", DEFAULT_TRUE_PEAK)); self.audio_mode_var.set(options.get("audio_mode", DEFAULT_AUDIO_MODE))
        
        self.subtitle_font_var.set(options.get("subtitle_font", DEFAULT_SUBTITLE_FONT)); self.subtitle_font_size_var.set(options.get("subtitle_font_size", DEFAULT_SUBTITLE_FONT_SIZE)); self.subtitle_alignment_var.set(options.get("subtitle_alignment", DEFAULT_SUBTITLE_ALIGNMENT))
        self.subtitle_bold_var.set(options.get("subtitle_bold", DEFAULT_SUBTITLE_BOLD)); self.subtitle_italic_var.set(options.get("subtitle_italic", DEFAULT_SUBTITLE_ITALIC)); self.subtitle_underline_var.set(options.get("subtitle_underline", DEFAULT_SUBTITLE_UNDERLINE))
        self.subtitle_margin_v_var.set(options.get("subtitle_margin_v", DEFAULT_SUBTITLE_MARGIN_V)); self.fill_color_var.set(options.get("fill_color", DEFAULT_FILL_COLOR)); self.fill_alpha_var.set(options.get("fill_alpha", DEFAULT_FILL_ALPHA))
        self.outline_color_var.set(options.get("outline_color", DEFAULT_OUTLINE_COLOR)); self.outline_alpha_var.set(options.get("outline_alpha", DEFAULT_OUTLINE_ALPHA))
        self.outline_width_var.set(options.get("outline_width", DEFAULT_OUTLINE_WIDTH)); self.shadow_color_var.set(options.get("shadow_color", DEFAULT_SHADOW_COLOR))
        self.shadow_alpha_var.set(options.get("shadow_alpha", DEFAULT_SHADOW_ALPHA)); self.shadow_offset_x_var.set(options.get("shadow_offset_x", DEFAULT_SHADOW_OFFSET_X)); self.shadow_offset_y_var.set(options.get("shadow_offset_y", DEFAULT_SHADOW_OFFSET_Y))
        self.shadow_blur_var.set(options.get("shadow_blur", DEFAULT_SHADOW_BLUR)); self.lut_file_var.set(options.get("lut_file", DEFAULT_LUT_PATH))
        
        self.fill_swatch.config(bg=self.fill_color_var.get()); self.outline_swatch.config(bg=self.outline_color_var.get()); self.shadow_swatch.config(bg=self.shadow_color_var.get())
        self._toggle_bitrate_override(); self.toggle_fruc_fps(); self._toggle_orientation_options(); self._toggle_upscale_options(); self._toggle_audio_norm_options()

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
            self.processing_jobs.insert(actual_index + 1, new_job)
            self.job_listbox.insert(actual_index + 1, new_job['display_name'])
            offset += 1

    def build_audio_segment(self, file_path, options):
        def normalize_layout(layout_raw: str) -> list:
            s = layout_raw.replace('+', ' ').replace(',', ' ').lower()
            return [t.strip() for t in re.sub(r'\b l \b', ' fl ', ' ' + s + ' ').replace(r'\b r \b', ' fr ').split() if t.strip()]
        def generate_pan_expression(ch_count: int, layout_tokens: list, target: str) -> str:
            tokens = ' '.join(layout_tokens)
            if target == "stereo": return "pan=stereo|FL=c0|FR=c0" if ch_count == 1 else "pan=stereo|FL=c0|FR=c1"
            if target == "5.1(side)":
                if ch_count == 1: return "pan=5.1(side)|FL=c0|FR=c0|FC=c0|LFE=0.0|SL=c0|SR=c0"
                if ch_count == 2: return "pan=5.1(side)|FL=c0|FR=c1|FC=0.707*c0+0.707*c1|LFE=0.118*c0+0.118*c1|SL=0.816*c0|SR=0.816*c1"
                if ch_count >= 6:
                    if all(x in tokens for x in ("fl", "fr", "fc", "lfe", "sl", "sr")): return "pan=5.1(side)|FL<FL|FR<FR|FC<FC|LFE<LFE|SL<SL|SR<SR"
                    if all(x in tokens for x in ("c", "l", "r", "ls", "rs", "lfe")): return "pan=5.1(side)|FL<L|FR<R|FC<C|LFE<LFE|SL<Ls|SR<Rs"
                    return "pan=5.1(side)|FL=c0|FR=c1|FC=c2|LFE=c3|SL=c4|SR=c5"
                return "pan=5.1(side)|FL=c0|FR=c1|FC=c0|LFE=0.0|SL=c0|SR=c1"
            return "pan=stereo|FL=c0|FR=c1"

        audio_streams = get_audio_stream_info(file_path)
        if not audio_streams: return ["-an"]
        audio_mode, normalize_flag = options.get("audio_mode", DEFAULT_AUDIO_MODE), options.get("normalize_audio", DEFAULT_NORMALIZE_AUDIO)
        loudness_target, loudness_range, true_peak = options.get("loudness_target", DEFAULT_LOUDNESS_TARGET), options.get("loudness_range", DEFAULT_LOUDNESS_RANGE), options.get("true_peak", DEFAULT_TRUE_PEAK)
        stereo_idx, surround_idx = None, None
        for s in audio_streams:
            idx, ch, layout = int(s.get("index", 0)), int(s.get("channels", 0)), s.get("channel_layout", "").lower()
            if stereo_idx is None and (ch == 2 or "stereo" in layout): stereo_idx = idx
            if surround_idx is None and (ch == 6 or "5.1" in layout): surround_idx = idx
        stereo_idx = stereo_idx if stereo_idx is not None else (surround_idx if surround_idx is not None else int(audio_streams[0].get("index", 0)))
        surround_idx = surround_idx if surround_idx is not None else stereo_idx
        
        fc_parts = [f"[0:{stereo_idx}]anull,pan=stereo|FL=c0|FR=c1[a_stereo]"]
        s_info = next((s for s in audio_streams if int(s.get("index", 0)) == surround_idx), {})
        fc_parts.append(f"[0:{surround_idx}]{generate_pan_expression(int(s_info.get('channels', 0)), normalize_layout(s_info.get('channel_layout', '')), '5.1(side)')}[a_5ch]")
        
        map_stereo, map_5ch = "a_stereo", "a_5ch"
        if normalize_flag:
            fc_parts.extend([f"[{map_stereo}]loudnorm=i={loudness_target}:lra={loudness_range}:tp={true_peak}[{map_stereo}_ln]", f"[{map_5ch}]loudnorm=i={loudness_target}:lra={loudness_range}:tp={true_peak}[{map_5ch}_ln]"])
            map_stereo, map_5ch = f"{map_stereo}_ln", f"{map_5ch}_ln"
        fc_parts.extend([f"[{map_stereo}]aresample={AUDIO_SAMPLE_RATE}[{map_stereo}_r]", f"[{map_5ch}]aresample={AUDIO_SAMPLE_RATE}[{map_5ch}_r]"])
        map_stereo, map_5ch = f"{map_stereo}_r", f"{map_5ch}_r"

        return ["-filter_complex", ";".join(fc_parts), "-map", f"[{map_stereo}]", "-map", f"[{map_5ch}]",
                "-c:a:0", "aac", "-b:a:0", f"{STEREO_BITRATE_K}k", "-ar:a:0", str(AUDIO_SAMPLE_RATE), "-ac:a:0", "2",
                "-c:a:1", "aac", "-b:a:1", f"{SURROUND_BITRATE_K}k", "-ar:a:1", str(AUDIO_SAMPLE_RATE), "-ac:a:1", "6",
                "-channel_layout:a:1", "5.1(side)", "-disposition:a:0", "default", "-disposition:a:1", "0",
                "-metadata:s:a:0", "title=Stereo", "-metadata:s:a:1", "title=5.1 Surround"]

    def build_ffmpeg_command_and_run(self, job, orientation):
        options = job['options']
        folder_name = f"{options.get('resolution', DEFAULT_RESOLUTION)}_{options.get('output_format', DEFAULT_OUTPUT_FORMAT).upper()}"
        if orientation == "vertical": folder_name += f"_Vertical_{options.get('vertical_aspect').replace(':', 'x')}"
        elif orientation == "original": folder_name += "_Original"
        else:
            h_aspect = options.get('horizontal_aspect').replace(':', 'x')
            if h_aspect != "16x9": folder_name += f"_Horizontal_{h_aspect}"
        
        base_name = os.path.splitext(os.path.basename(job['video_path']))[0]
        
        tag_match = re.search(r'(\[.*\])', job['display_name'])
        tag = tag_match.group(1) if tag_match else "Subtitles"
        safe_subtitle_folder_name = re.sub(r'[\\/*?:"<>|]', "", tag).strip()

        base_dir = os.path.dirname(job['video_path']) if self.output_mode == 'local' else os.getcwd()
        output_dir = os.path.join(base_dir, folder_name, safe_subtitle_folder_name)
        os.makedirs(output_dir, exist_ok=True)
        
        output_file = os.path.join(output_dir, f"{base_name}.mp4")
        
        ass_burn_path = None
        temp_extracted_srt_path = None # Keep track of the extracted SRT for cleanup
        
        try:
            if job['options'].get("burn_subtitles") and job.get('subtitle_path'):
                sub_identifier = job.get('subtitle_path')
                subtitle_source_file = None

                if sub_identifier.startswith("embedded:"):
                    # Step 1: Extract the embedded subtitle to a temporary file
                    stream_index = int(sub_identifier.split(':')[1])
                    temp_extracted_srt_path = extract_embedded_subtitle(job['video_path'], stream_index)
                    if temp_extracted_srt_path:
                        subtitle_source_file = temp_extracted_srt_path
                    else:
                        print(f"[WARN] Could not extract embedded subtitle for '{job['display_name']}'. Proceeding without subtitles.")
                
                elif os.path.exists(sub_identifier):
                    # For external files, the source is the file itself
                    subtitle_source_file = sub_identifier
                
                # Step 2: If we have a source file (either external or extracted), create the styled ASS file
                if subtitle_source_file:
                    ass_burn_path = create_temporary_ass_file(subtitle_source_file, options)
                    if not ass_burn_path:
                        raise VideoProcessingError(f"Failed to create styled ASS file from {subtitle_source_file}")

            cmd = self.construct_ffmpeg_command(job['video_path'], output_file, orientation, ass_burn_path, options)
            
            if self.run_ffmpeg_command(cmd) == 0:
                print(f"File finalized => {output_file}")
                self.verify_output_file(output_file, options)
            else:
                raise VideoProcessingError(f"Error encoding {job['video_path']}")
        
        finally:
            # Clean up ALL temporary files
            if ass_burn_path and os.path.exists(ass_burn_path):
                try:
                    os.remove(ass_burn_path)
                    debug_print(f"Cleaned up temp styled ASS file: {ass_burn_path}")
                except Exception as e:
                    print(f"[WARN] Failed to clean up temp file {ass_burn_path}: {e}")
            
            if temp_extracted_srt_path and os.path.exists(temp_extracted_srt_path):
                try:
                    os.remove(temp_extracted_srt_path)
                    debug_print(f"Cleaned up temp extracted SRT file: {temp_extracted_srt_path}")
                except Exception as e:
                    print(f"[WARN] Failed to clean up temp file {temp_extracted_srt_path}: {e}")

    def construct_ffmpeg_command(self, file_path, output_file, orientation, ass_burn_path, options):
        info = get_video_info(file_path)
        decoder_available, _ = check_decoder_availability(info["codec_name"])
        decoder_map = {"h264": "h264_cuvid", "hevc": "hevc_cuvid", "av1": "av1_cuvid", "vp9": "vp9_cuvid"}
        decoder = decoder_map.get(info["codec_name"]) if decoder_available else info["codec_name"]
        use_cuda_decoder = "_cuvid" in decoder
        
        cmd = [FFMPEG_CMD, "-y", "-hide_banner"] + (["-hwaccel", "cuda", "-hwaccel_output_format", "cuda"] if use_cuda_decoder else []) + ["-c:v", decoder, "-i", file_path]
        
        vf_filters, cpu_filters = [], []
        is_hdr_output = options.get("output_format") == 'hdr'
        if orientation != "original":
            res_key, aspect_str = (options.get('resolution'), options.get('vertical_aspect')) if orientation == "vertical" else (options.get('resolution'), options.get('horizontal_aspect'))
            width_map = {"HD": 1080, "4k": 2160, "8k": 4320} if orientation == "vertical" else {"HD": 1920, "4k": 3840, "8k": 7680}
            target_w = width_map.get(res_key, 1920); num, den = map(int, aspect_str.split(':')); target_h = int(target_w * den / num)
            target_w, target_h = (target_w // 2) * 2, (target_h // 2) * 2
            
            scale_base = f"scale_cuda=w={target_w}:h={target_h}:interp_algo={options.get('upscale_algo', DEFAULT_UPSCALE_ALGO)}"
            if options.get("aspect_mode") == 'pad':
                vf_filters.append(f"{scale_base}:force_original_aspect_ratio=decrease" + ("" if is_hdr_output else ":format=nv12"))
                cpu_filters.append(f"pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2:black")
            elif options.get("aspect_mode") == 'crop':
                vf_filters.append(f"{scale_base}:force_original_aspect_ratio=increase" + ("" if is_hdr_output else ":format=nv12"))
                cpu_filters.append(f"crop={target_w}:{target_h}")
            else: vf_filters.append(scale_base + ("" if is_hdr_output else ":format=nv12"))
        elif not is_hdr_output and info["bit_depth"] == 10: vf_filters.append("scale_cuda=format=nv12")

        lut_file = options.get("lut_file", DEFAULT_LUT_PATH)
        if info["is_hdr"] and not is_hdr_output and os.path.exists(lut_file):
            cpu_filters.append(f"lut3d=file='{lut_file.replace(':', '\\:').replace('\\\\', '/')}'")
        if options.get("fruc"): cpu_filters.append(f"minterpolate=fps={options.get('fruc_fps')}")
        
        if ass_burn_path:
            safe_path = ass_burn_path.replace('\\', '/').replace(':', '\\:')
            cpu_filters.append(f"subtitles=filename='{safe_path}'")
        
        if cpu_filters:
            cpu_pix_fmt = "p010le" if info["bit_depth"] == 10 else "nv12"
            vf_filters.extend([f"hwdownload,format={cpu_pix_fmt}", ",".join(cpu_filters), f"format={cpu_pix_fmt},hwupload_cuda"])

        cmd.extend(["-map", "0:v:0"])
        if vf_filters: cmd.extend(["-vf", ",".join(vf_filters)])
        cmd.extend(self.build_audio_segment(file_path, options))

        bitrate_kbps = int(options.get("manual_bitrate")) if options.get("override_bitrate") else get_bitrate(options.get('resolution', DEFAULT_RESOLUTION), info["framerate"], is_hdr_output)
        gop_len = 0 if info["framerate"] == 0 else math.ceil(info["framerate"] / 2)
        
        if is_hdr_output: cmd.extend(["-c:v", "hevc_nvenc", "-preset", "p1", "-profile:v", "main10", "-b:v", f"{bitrate_kbps}k", "-g", str(gop_len), "-color_primaries", "bt2020", "-color_trc", "smpte2084", "-colorspace", "bt2020nc"])
        else: cmd.extend(["-c:v", "h264_nvenc", "-preset", "p1", "-profile:v", "high", "-b:v", f"{bitrate_kbps}k", "-g", str(gop_len), "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709"])
        cmd.extend(["-f", "mp4", output_file])
        return cmd

    def validate_processing_settings(self):
        issues = []
        if self.output_format_var.get() == 'sdr' and not os.path.exists(self.lut_file_var.get()): issues.append(f"LUT file not found: {self.lut_file_var.get()}")
        try:
            test_file = os.path.join(os.getcwd(), f"temp_permission_test_{int(time.time())}.tmp")
            with open(test_file, "w") as f: f.write("test")
            os.remove(test_file)
        except Exception as e:
            issues.append(f"Cannot write to working directory (for temp subtitle files): {e}")

        try:
            if not -70 <= float(self.loudness_target_var.get()) <= 0: issues.append("Loudness target should be between -70 and 0 LUFS")
        except ValueError: issues.append("Invalid loudness target value")
        if issues: messagebox.showerror("Configuration Issues", "Please fix the following issues:\n\n" + "\n".join(f"• {issue}" for issue in issues)); return False
        return True

    def start_processing(self):
        if not self.processing_jobs: messagebox.showwarning("No Jobs", "Please add files."); return
        if not self.validate_processing_settings(): return
        self.output_mode = self.output_mode_var.get()
        print("\n" + "="*80 + "\n--- Starting processing batch ---")
        successful, failed = 0, 0
        total_jobs = len(self.processing_jobs)

        for i, job in enumerate(self.processing_jobs):
            self.update_status(f"Processing {i + 1}/{total_jobs}: {job['display_name']}")
            print("\n" + "-"*80)
            print(f"Starting job {i + 1}/{total_jobs}: {job['display_name']}")
            try:
                orientation = job['options'].get("orientation", "horizontal")
                
                if orientation == "horizontal + vertical":
                    self.build_ffmpeg_command_and_run(job, "horizontal")
                    self.build_ffmpeg_command_and_run(job, "vertical")
                else:
                    self.build_ffmpeg_command_and_run(job, orientation)
                
                successful += 1
                print(f"[SUCCESS] Job '{job['display_name']}' completed successfully.")

            except (VideoProcessingError, Exception) as e:
                failed += 1
                print(f"\n[ERROR] Job failed for '{job['display_name']}': {e}")
        
        final_message = f"Processing Complete: {successful} successful, {failed} failed"
        print("\n" + "="*80 + "\n" + final_message)
        self.update_status(final_message)

    def run_ffmpeg_command(self, cmd):
        print("Running FFmpeg command:")
        print(" ".join(f'"{c}"' if " " in c else c for c in cmd))
        try:
            return safe_ffmpeg_execution(cmd, "video encoding")
        except VideoProcessingError as e:
            print(f"\n[ERROR] FFmpeg execution failed. See details below:\n{e}")
            return 1

    def verify_output_file(self, file_path, options=None):
        print(f"--- Verifying output file: {os.path.basename(file_path)} ---")
        try:
            cmd = [FFPROBE_CMD, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,display_aspect_ratio", "-of", "default=noprint_wrappers=1:nokey=1", file_path]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, env=env)
            print(f"[VERIFIED] Output Specs: {'x'.join(result.stdout.strip().splitlines()[:2])}")
        except Exception as e: print(f"[ERROR] Verification failed: {e}")
        try:
            cmd_audio = [FFPROBE_CMD, "-v", "error", "-select_streams", "a", "-show_entries", "stream=index,channels,channel_layout,sample_rate,codec_name,bit_rate", "-of", "json", file_path]
            audio_info = json.loads(subprocess.run(cmd_audio, capture_output=True, text=True, check=True, env=env).stdout).get("streams", [])
            for i, s in enumerate(audio_info):
                print(f"[AUDIO VER] Stream #{i}: channels={s.get('channels')}, layout='{s.get('channel_layout', 'None')}', samplerate={s.get('sample_rate')}")
            
            if options and options.get("audio_mode") == "stereo+5.1":
                is_layout_issue = False
                for s in audio_info:
                    if s.get('channels') == 6:
                        layout = s.get('channel_layout')
                        if layout is not None and layout != '5.1(side)':
                            is_layout_issue = True
                            break
                if is_layout_issue:
                    print("[WARN] 5.1 stream layout is not '5.1(side)', which YouTube requires.")

        except Exception as e: print(f"[WARN] Could not run audio verification: {e}")
    
    def add_files(self):
        files = filedialog.askopenfilenames(filetypes=[("Video Files", "*.mp4;*.mkv;*.avi;*.mov;*.webm;*.flv;*.wmv"), ("All Files", "*.*")])
        if files: self.add_video_files_and_discover_jobs(files)
    def handle_file_drop(self, event):
        files = self.root.tk.splitlist(event.data);
        if files: self.add_video_files_and_discover_jobs(files)
    def remove_selected(self):
        for index in reversed(list(self.job_listbox.curselection())):
            del self.processing_jobs[index]; self.job_listbox.delete(index)
    def clear_all(self): self.processing_jobs.clear(); self.job_listbox.delete(0, tk.END)
    def select_all_files(self): self.job_listbox.select_set(0, tk.END); self.on_input_file_select(None)
    def clear_file_selection(self): self.job_listbox.select_clear(0, tk.END)
    def toggle_fruc_fps(self): self.fruc_fps_entry.config(state="normal" if self.fruc_var.get() else "disabled")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YouTube Batch Video Processing Tool", formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-o', '--output-mode', dest='output_mode', choices=['local', 'pooled'], default='local', help="Set initial output directory mode.")
    parser.add_argument('input_files', nargs='*', help="Optional: Paths to video files or glob patterns.")
    parser.add_argument('-d', '--debug', action='store_true', help="Enable debug mode.")
    args = parser.parse_args()
    DEBUG_MODE = args.debug
    
    if not check_cuda_availability():
        messagebox.showerror("CUDA Not Available", "CUDA hardware acceleration is not available or not detected in FFmpeg. The application requires CUDA to run.\n\nPlease ensure your NVIDIA drivers are installed and you have a compatible FFmpeg build.")
        sys.exit(1)
    
    capabilities = check_ffmpeg_capabilities()
    if not capabilities['nvenc']:
        messagebox.showwarning(
            "NVENC Not Available",
            "NVENC encoders not found in FFmpeg. Video encoding may fail.\nContinuing anyway..."
        )
    
    root = TkinterDnD.Tk()
    initial_files = []
    if args.input_files:
        for pattern in args.input_files: initial_files.extend(glob.glob(pattern))
    else:
        for root_dir, _, files in os.walk(os.getcwd()):
            if not any(x in root_dir for x in ["_SDR", "_HDR", "_Vertical", "_Original"]):
                for filename in files:
                    if os.path.splitext(filename)[1].lower() in ['.mp4', '.mkv', '.mov']:
                        initial_files.append(os.path.join(root_dir, filename))
    
    app = VideoProcessorApp(root, sorted(list(set(initial_files))), args.output_mode)
    root.mainloop()