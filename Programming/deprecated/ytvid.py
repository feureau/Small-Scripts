
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
    • Multi-track audio handling with mix-and-match outputs (Mono, Stereo, 5.1)
    • Binaural (Sofalizer) downmixing for headphones
    • Bitrate, channel layout, and codec compliance for YouTube
    • Batch queue management through a Tkinter GUI
    • Advanced, multi-layer subtitle styling and burning
    • Hybrid stacked video creation for vertical formats
-------------------------------------------------------------------------------
Version History
-------------------------------------------------------------------------------
v7.2 - Intelligent Subtitle Defaulting (2025-11-13)
    • ADDED: Logic to automatically enable "Enable Subtitle Burning" when a
      job with an available subtitle source is switched to a vertical, hybrid,
      or "horizontal + vertical" orientation.
    • CHANGED: The script now provides immediate visual feedback by checking
      the GUI box and saves this state change to all selected jobs.
    • FIXED: Prevents enabling burn subtitles for jobs without a subtitle source.

v7.1 - User Default Configuration (2025-11-11)
    • CHANGED: Default audio selection is now "Stereo (Sofalizer)" and "5.1
      Surround" to match user preference for high-quality headphone and
      surround outputs.
    • CHANGED: Re-instated the default SOFA file path to streamline the user's
      primary workflow. The field is no longer blank on startup.

v7.0 - Flexible Audio Track Building (2025-11-11)
    • REFACTORED: The audio processing backend (`build_audio_segment`) has been
      completely rewritten to support a flexible track-building system.
    • CHANGED: The GUI's audio tab now uses five checkboxes (Mono, Stereo,
      Stereo Sofalizer, 5.1 Surround, Passthrough) instead of radio buttons.
    • ADDED: Logic to make the "Passthrough" option mutually exclusive with all
      other audio processing options to ensure valid commands.
    • ADDED: Intelligent source analysis. The script now checks the source
      audio channels and will only generate tracks that are possible.
    • FIXED: Audio normalization is now applied independently to each generated
      track, ensuring loudness targets are met for all outputs.
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
import textwrap
import hashlib

# -------------------------- Configuration / Constants --------------------------
FFMPEG_CMD = os.environ.get("FFMPEG_PATH", "ffmpeg")
FFPROBE_CMD = os.environ.get("FFPROBE_PATH", "ffprobe")

# Audio settings
AUDIO_SAMPLE_RATE = 48000
MONO_BITRATE_K = 128
STEREO_BITRATE_K = 384
SURROUND_BITRATE_K = 512
PASSTHROUGH_NORMALIZE_BITRATE_K = 192

# Video & General
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

# Audio normalization
DEFAULT_NORMALIZE_AUDIO = False
DEFAULT_LOUDNESS_TARGET = "-9"
DEFAULT_LOUDNESS_RANGE = "7"
DEFAULT_TRUE_PEAK = "-1.0"

# Audio track selection defaults (User preference update)
DEFAULT_AUDIO_MONO = False
DEFAULT_AUDIO_STEREO_DOWNMIX = False
DEFAULT_AUDIO_STEREO_SOFALIZER = False
DEFAULT_AUDIO_SURROUND_51 = False
DEFAULT_AUDIO_PASSTHROUGH = True

# Subtitle defaults
DEFAULT_SUBTITLE_FONT = "HelveticaNeueLT Std Blk"
DEFAULT_SUBTITLE_FONT_SIZE = "32"
DEFAULT_SUBTITLE_ALIGNMENT = "bottom"
DEFAULT_SUBTITLE_BOLD = True
DEFAULT_SUBTITLE_ITALIC = False
DEFAULT_SUBTITLE_UNDERLINE = False
DEFAULT_SUBTITLE_MARGIN_V = "335"
DEFAULT_REFORMAT_SUBTITLES = True
DEFAULT_WRAP_LIMIT = "42"

# Fill
DEFAULT_FILL_COLOR = "#FFAA00"
DEFAULT_FILL_ALPHA = 0

# Outline
DEFAULT_OUTLINE_COLOR = "#000000"
DEFAULT_OUTLINE_ALPHA = 0
DEFAULT_OUTLINE_WIDTH = "9"

# Shadow
DEFAULT_SHADOW_COLOR = "#202020"
DEFAULT_SHADOW_ALPHA = 120
DEFAULT_SHADOW_OFFSET_X = "2"
DEFAULT_SHADOW_OFFSET_Y = "4"
DEFAULT_SHADOW_BLUR = "5"

DEBUG_MODE = False  # or True

def debug_print(*args, **kwargs):
    if DEBUG_MODE:
        print("[DEBUG]", *args, **kwargs)

env = os.environ.copy()
env["PYTHONIOENCODING"] = "utf-8"

class VideoProcessingError(Exception):
    pass

# --- Utility Functions (Unchanged) ---
def check_cuda_availability():
    try:
        cmd = [FFMPEG_CMD, "-hwaccels"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return "cuda" in result.stdout.lower()
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
    return f"&H{alpha_val:02X}"

def create_temporary_ass_file(srt_path, options):
    try:
        with open(srt_path, 'r', encoding='utf-8', errors='replace') as f:
            srt_content = f.read()
    except Exception as e:
        print(f"[ERROR] Could not read SRT file {srt_path}: {e}")
        return None

    font_name = options.get('subtitle_font', DEFAULT_SUBTITLE_FONT)
    font_size = options.get('subtitle_font_size', DEFAULT_SUBTITLE_FONT_SIZE)
    bold_flag = "-1" if options.get('subtitle_bold', DEFAULT_SUBTITLE_BOLD) else "0"
    italic_flag = "-1" if options.get('subtitle_italic', DEFAULT_SUBTITLE_ITALIC) else "0"
    underline_flag = "-1" if options.get('subtitle_underline', DEFAULT_SUBTITLE_UNDERLINE) else "0"
    margin_v = options.get('subtitle_margin_v', DEFAULT_SUBTITLE_MARGIN_V)
    align_map = {"top": 8, "middle": 5, "bottom": 2, "seam": 2}
    alignment = align_map.get(options.get('subtitle_alignment', 'bottom'), 2)
    reformat_subs = options.get('reformat_subtitles', DEFAULT_REFORMAT_SUBTITLES)
    try:
        wrap_limit = int(options.get('wrap_limit', DEFAULT_WRAP_LIMIT))
    except (ValueError, TypeError):
        wrap_limit = int(DEFAULT_WRAP_LIMIT)

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

    style_main = (
        f"Style: Main,{font_name},{font_size},"
        f"{hex_to_libass_color(fill_color_hex)},"
        "&HFF000000,"
        f"{hex_to_libass_color(outline_color_hex)},"
        f"{hex_to_libass_color(shadow_color_hex)},"
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
        clean_text = re.sub(r'<[^>]+>', '', text)
        start_ass = start_time.replace(',', '.')[:-1]
        end_ass = end_time.replace(',', '.')[:-1]
        if reformat_subs:
            single_line_text = ' '.join(clean_text.strip().split())
            wrapped_lines = textwrap.wrap(single_line_text, width=wrap_limit)
            text_ass = '\\N'.join(wrapped_lines)
        else:
            text_ass = clean_text.strip().replace('\n', '\\N')

        tags = (
            f"\\1a{alpha_to_libass_alpha(fill_alpha_val)}"
            f"\\3a{alpha_to_libass_alpha(outline_alpha_val)}"
            f"\\4a{alpha_to_libass_alpha(shadow_alpha_val)}"
            f"\\xshad{shadow_offset_x}"
            f"\\yshad{shadow_offset_y}"
            f"\\blur{shadow_blur}"
        )
        pos_override = ""
        if options.get("subtitle_alignment") == "seam" and "calculated_pos" in options:
            x, y = options["calculated_pos"]
            pos_override = fr"{{\an5\pos({x},{y})}}"
            debug_print(f"Applying position override: {pos_override}")
        dialogue_lines.append(f"Dialogue: 0,{start_ass},{end_ass},Main,,0,0,0,,{{{tags}}}{pos_override}{text_ass}")

    full_ass_content = header + "\n".join(dialogue_lines)
    filename = f"temp_subtitle_{int(time.time() * 1000)}.ass"
    filepath = os.path.join(os.getcwd(), filename)
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(full_ass_content)
        debug_print(f"Created temporary subtitle file: {filepath}")
        return filepath
    except Exception as e:
        print(f"[ERROR] Could not create temporary ASS file: {e}")
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
    cmd = [FFPROBE_CMD, "-v", "error", "-select_streams", "s", "-show_entries",
           "stream=index,codec_name:stream_tags=title,language", "-of", "json", file_path]
    try:
        result = safe_ffprobe(cmd, "subtitle stream info extraction")
        return json.loads(result.stdout).get("streams", [])
    except Exception as e:
        print(f"[WARN] Could not get embedded subtitle info for {file_path}: {e}")
        return []

def extract_embedded_subtitle(video_path, subtitle_index):
    temp_subtitle_path = ""
    try:
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.srt', encoding='utf-8') as temp_f:
            temp_subtitle_path = temp_f.name
        cmd = [FFMPEG_CMD, '-y', '-hide_banner', '-i', video_path, '-map', f'0:s:{subtitle_index}', '-c:s', 'srt', temp_subtitle_path]
        print(f"[INFO] Extracting embedded subtitle stream {subtitle_index}...")
        subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30, env=env)
        if os.path.exists(temp_subtitle_path) and os.path.getsize(temp_subtitle_path) > 0:
            debug_print(f"Successfully extracted subtitle to {temp_subtitle_path}")
            return temp_subtitle_path
        else:
            print(f"[WARN] Extracted subtitle file is empty or missing.")
            if os.path.exists(temp_subtitle_path): os.remove(temp_subtitle_path)
            return None
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Failed to extract subtitle stream {subtitle_index}.")
        if os.path.exists(temp_subtitle_path): os.remove(temp_subtitle_path)
        return None
    except Exception as e:
        print(f"[ERROR] Unexpected error during subtitle extraction: {e}")
        if os.path.exists(temp_subtitle_path): os.remove(temp_subtitle_path)
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

def get_job_hash(job_options):
    keys_to_hash = [
        job_options.get('manual_bitrate', ''),
        str(job_options.get('override_bitrate', False)),
        job_options.get('orientation', ''),
        job_options.get('resolution', ''),
        job_options.get('output_format', ''),
        str(job_options.get('burn_subtitles', False)),
        job_options.get('horizontal_aspect', ''),
        job_options.get('vertical_aspect', ''),
        job_options.get('aspect_mode', ''),
        job_options.get('fruc', False),
        job_options.get('fruc_fps', ''),
        str(job_options.get('normalize_audio', False)),
        job_options.get('sofa_file', ''),
        job_options.get('subtitle_alignment', ''),
        job_options.get('hybrid_top_aspect', ''),
        job_options.get('hybrid_bottom_aspect', ''),
        job_options.get('subtitle_font', ''),
        job_options.get('subtitle_font_size', ''),
        job_options.get('outline_width', ''),
        job_options.get('shadow_offset_x', ''),
        job_options.get('shadow_offset_y', ''),
        job_options.get('shadow_blur', ''),
        job_options.get('wrap_limit', ''),
        # Add new audio options
        job_options.get('audio_mono', False),
        job_options.get('audio_stereo_downmix', False),
        job_options.get('audio_stereo_sofalizer', False),
        job_options.get('audio_surround_51', False),
        job_options.get('audio_passthrough', False),
    ]
    hash_str = "|".join(str(k) for k in keys_to_hash)
    return hashlib.md5(hash_str.encode()).hexdigest()[:8]

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

class CollapsiblePane(ttk.Frame):
    """A collapsible pane widget for tkinter."""
    def __init__(self, parent, text="", initial_state='collapsed'):
        super().__init__(parent, padding=5)
        self.columnconfigure(0, weight=1)
        self.text = text
        self._is_collapsed = tk.BooleanVar(value=(initial_state == 'collapsed'))

        self.header_frame = ttk.Frame(self, style='Header.TFrame')
        self.header_frame.grid(row=0, column=0, sticky='ew')
        self.header_frame.columnconfigure(1, weight=1)

        self.toggle_button = ttk.Label(self.header_frame, text=f"{'►' if self._is_collapsed.get() else '▼'} {self.text}", style='Header.TLabel')
        self.toggle_button.grid(row=0, column=0, sticky='w')
        self.toggle_button.bind("<Button-1>", self._toggle)

        self.container = ttk.Frame(self)
        self.container.grid(row=1, column=0, sticky='nsew', padx=5, pady=5)

        self.style = ttk.Style(self)
        self.style.configure('Header.TFrame', background='lightgray')
        self.style.configure('Header.TLabel', background='lightgray', font=('Arial', 10, 'bold'))

        if self._is_collapsed.get():
            self.container.grid_remove()

    def _toggle(self, event=None):
        self._is_collapsed.set(not self._is_collapsed.get())
        if self._is_collapsed.get():
            self.container.grid_remove()
            self.toggle_button.config(text=f"► {self.text}")
        else:
            self.container.grid()
            self.toggle_button.config(text=f"▼ {self.text}")

class VideoProcessorApp:
    def __init__(self, root, initial_files, output_mode):
        self.root = root
        self.root.title("Video Processing Tool")
        self.root.geometry("1200x800") # Set a reasonable default size
        self.output_mode = output_mode
        self.processing_jobs = []

        # --- Initialize all tk Variables ---
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
        self.fruc_fps_var.trace_add('write', lambda *args: self._update_selected_jobs('fruc_fps'))
        self.generate_log_var = tk.BooleanVar(value=False)
        self.burn_subtitles_var = tk.BooleanVar(value=DEFAULT_BURN_SUBTITLES)
        self.override_bitrate_var = tk.BooleanVar(value=False)
        self.manual_bitrate_var = tk.StringVar()
        self.manual_bitrate_var.trace_add('write', lambda *args: self._update_selected_jobs('manual_bitrate'))
        self.normalize_audio_var = tk.BooleanVar(value=DEFAULT_NORMALIZE_AUDIO)
        self.loudness_target_var = tk.StringVar(value=DEFAULT_LOUDNESS_TARGET)
        self.loudness_target_var.trace_add('write', lambda *args: self._update_selected_jobs('loudness_target'))
        self.loudness_range_var = tk.StringVar(value=DEFAULT_LOUDNESS_RANGE)
        self.loudness_range_var.trace_add('write', lambda *args: self._update_selected_jobs('loudness_range'))
        self.true_peak_var = tk.StringVar(value=DEFAULT_TRUE_PEAK)
        self.true_peak_var.trace_add('write', lambda *args: self._update_selected_jobs('true_peak'))
        self.sofa_file_var = tk.StringVar(value=r"E:\Small-Scripts\SOFALIZER\D1_48K_24bit_256tap_FIR_SOFA.sofa")
        self.lut_file_var = tk.StringVar(value=DEFAULT_LUT_PATH)
        self.status_var = tk.StringVar(value="Ready")
        self.hybrid_top_aspect_var = tk.StringVar(value="16:9")
        self.hybrid_top_mode_var = tk.StringVar(value="crop")
        self.hybrid_bottom_aspect_var = tk.StringVar(value="4:5")
        self.hybrid_bottom_mode_var = tk.StringVar(value="crop")
        self.subtitle_font_var = tk.StringVar(value=DEFAULT_SUBTITLE_FONT)
        self.subtitle_font_size_var = tk.StringVar(value=DEFAULT_SUBTITLE_FONT_SIZE)
        self.subtitle_font_size_var.trace_add('write', lambda *args: self._update_selected_jobs('subtitle_font_size'))
        self.subtitle_alignment_var = tk.StringVar(value=DEFAULT_SUBTITLE_ALIGNMENT)
        self.subtitle_bold_var = tk.BooleanVar(value=DEFAULT_SUBTITLE_BOLD)
        self.subtitle_italic_var = tk.BooleanVar(value=DEFAULT_SUBTITLE_ITALIC)
        self.subtitle_underline_var = tk.BooleanVar(value=DEFAULT_SUBTITLE_UNDERLINE)
        self.subtitle_margin_v_var = tk.StringVar(value=DEFAULT_SUBTITLE_MARGIN_V)
        self.subtitle_margin_v_var.trace_add('write', lambda *args: self._update_selected_jobs('subtitle_margin_v'))
        self.fill_color_var = tk.StringVar(value=DEFAULT_FILL_COLOR)
        self.fill_alpha_var = tk.IntVar(value=DEFAULT_FILL_ALPHA)
        self.outline_color_var = tk.StringVar(value=DEFAULT_OUTLINE_COLOR)
        self.outline_alpha_var = tk.IntVar(value=DEFAULT_OUTLINE_ALPHA)
        self.outline_width_var = tk.StringVar(value=DEFAULT_OUTLINE_WIDTH)
        self.outline_width_var.trace_add('write', lambda *args: self._update_selected_jobs('outline_width'))
        self.shadow_color_var = tk.StringVar(value=DEFAULT_SHADOW_COLOR)
        self.shadow_alpha_var = tk.IntVar(value=DEFAULT_SHADOW_ALPHA)
        self.shadow_offset_x_var = tk.StringVar(value=DEFAULT_SHADOW_OFFSET_X)
        self.shadow_offset_x_var.trace_add('write', lambda *args: self._update_selected_jobs('shadow_offset_x'))
        self.shadow_offset_y_var = tk.StringVar(value=DEFAULT_SHADOW_OFFSET_Y)
        self.shadow_offset_y_var.trace_add('write', lambda *args: self._update_selected_jobs('shadow_offset_y'))
        self.shadow_blur_var = tk.StringVar(value=DEFAULT_SHADOW_BLUR)
        self.shadow_blur_var.trace_add('write', lambda *args: self._update_selected_jobs('shadow_blur'))
        self.reformat_subtitles_var = tk.BooleanVar(value=DEFAULT_REFORMAT_SUBTITLES)
        self.wrap_limit_var = tk.StringVar(value=DEFAULT_WRAP_LIMIT)
        self.wrap_limit_var.trace_add('write', lambda *args: self._update_selected_jobs('wrap_limit'))
        self.last_standard_alignment = tk.StringVar(value=DEFAULT_SUBTITLE_ALIGNMENT)

        # New audio track booleans
        self.audio_mono_var = tk.BooleanVar(value=DEFAULT_AUDIO_MONO)
        self.audio_stereo_downmix_var = tk.BooleanVar(value=DEFAULT_AUDIO_STEREO_DOWNMIX)
        self.audio_stereo_sofalizer_var = tk.BooleanVar(value=DEFAULT_AUDIO_STEREO_SOFALIZER)
        self.audio_surround_51_var = tk.BooleanVar(value=DEFAULT_AUDIO_SURROUND_51)
        self.audio_passthrough_var = tk.BooleanVar(value=DEFAULT_AUDIO_PASSTHROUGH)

        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind("<<Drop>>", self.handle_file_drop)
        self.setup_gui()
        if initial_files: self.add_video_files_and_discover_jobs(initial_files)

    def setup_gui(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # --- Main Layout ---
        main_pane = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_pane.grid(row=0, column=0, sticky="nsew")

        input_frame = ttk.Frame(main_pane, padding=5)
        main_pane.add(input_frame, weight=1)

        settings_notebook = ttk.Notebook(main_pane)
        main_pane.add(settings_notebook, weight=2)

        # --- Bottom Bar ---
        bottom_frame = ttk.Frame(self.root)
        bottom_frame.grid(row=2, column=0, columnspan=2, sticky="ew")

        button_frame = ttk.Frame(bottom_frame)
        button_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10, pady=5)

        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.grid(row=3, column=0, columnspan=2, sticky="ew", padx=5, pady=2)

        # --- Populate Panes and Tabs ---
        self.setup_input_pane(input_frame)

        video_tab = ttk.Frame(settings_notebook, padding=10)
        audio_tab = ttk.Frame(settings_notebook, padding=10)
        subtitle_tab = ttk.Frame(settings_notebook, padding=10)

        settings_notebook.add(video_tab, text="Video")
        settings_notebook.add(audio_tab, text="Audio")
        settings_notebook.add(subtitle_tab, text="Subtitles")

        self.setup_video_tab(video_tab)
        self.setup_audio_tab(audio_tab)
        self.setup_subtitle_tab(subtitle_tab)
        self.setup_button_row(button_frame)

        # --- Initial State Updates ---
        self._toggle_orientation_options()
        self._toggle_upscale_options()
        self._toggle_audio_norm_options()
        self._update_audio_options_ui() # New unified audio UI updater
        self._update_bitrate_display()

    def setup_input_pane(self, parent):
        parent.rowconfigure(0, weight=1)
        parent.columnconfigure(0, weight=1)
        file_group = ttk.LabelFrame(parent, text="Input Files / Queue", padding=10)
        file_group.grid(row=0, column=0, sticky="nsew")
        file_group.rowconfigure(0, weight=1)
        file_group.columnconfigure(0, weight=1)

        listbox_container = ttk.Frame(file_group)
        listbox_container.grid(row=0, column=0, sticky="nsew", columnspan=2)
        listbox_container.rowconfigure(0, weight=1)
        listbox_container.columnconfigure(0, weight=1)

        self.job_scrollbar_v = ttk.Scrollbar(listbox_container, orient=tk.VERTICAL)
        self.job_scrollbar_v.grid(row=0, column=1, sticky="ns")
        self.job_scrollbar_h = ttk.Scrollbar(listbox_container, orient=tk.HORIZONTAL)
        self.job_scrollbar_h.grid(row=1, column=0, sticky="ew")
        self.job_listbox = tk.Listbox(listbox_container, selectmode=tk.EXTENDED, exportselection=False, yscrollcommand=self.job_scrollbar_v.set, xscrollcommand=self.job_scrollbar_h.set)
        self.job_listbox.grid(row=0, column=0, sticky="nsew")
        self.job_scrollbar_v.config(command=self.job_listbox.yview)
        self.job_scrollbar_h.config(command=self.job_listbox.xview)
        self.job_listbox.bind("<<ListboxSelect>>", self.on_input_file_select)

        # --- Action Buttons ---
        selection_buttons_frame = ttk.Frame(file_group)
        selection_buttons_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 5))
        ttk.Button(selection_buttons_frame, text="Select All", command=self.select_all_files).pack(side=tk.LEFT)
        ttk.Button(selection_buttons_frame, text="Clear", command=self.clear_file_selection).pack(side=tk.LEFT, padx=5)
        ttk.Button(selection_buttons_frame, text="Select No Sub", command=self.select_all_no_sub).pack(side=tk.LEFT)
        ttk.Button(selection_buttons_frame, text="Select Subbed", command=self.select_all_subbed).pack(side=tk.LEFT, padx=5)
        ttk.Button(selection_buttons_frame, text="Invert", command=self.invert_selection).pack(side=tk.LEFT)

        file_buttons_frame = ttk.Frame(file_group)
        file_buttons_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(5, 0))
        ttk.Button(file_buttons_frame, text="Add Files...", command=self.add_files).pack(side=tk.LEFT)
        ttk.Button(file_buttons_frame, text="Duplicate", command=self.duplicate_selected_jobs).pack(side=tk.LEFT, padx=5)
        ttk.Button(file_buttons_frame, text="Remove Sel.", command=self.remove_selected).pack(side=tk.LEFT)
        ttk.Button(file_buttons_frame, text="Clear All", command=self.clear_all).pack(side=tk.LEFT, padx=5)

    def setup_video_tab(self, parent):
        geometry_group = ttk.LabelFrame(parent, text="Output & Geometry", padding=10)
        geometry_group.pack(fill=tk.X, pady=(0, 5))
        orientation_frame = ttk.Frame(geometry_group); orientation_frame.pack(fill=tk.X)
        ttk.Label(orientation_frame, text="Orientation:").pack(side=tk.LEFT, padx=(0,5))
        ttk.Radiobutton(orientation_frame, text="Horizontal", variable=self.orientation_var, value="horizontal", command=self._toggle_orientation_options).pack(side=tk.LEFT)
        ttk.Radiobutton(orientation_frame, text="Vertical", variable=self.orientation_var, value="vertical", command=self._toggle_orientation_options).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(orientation_frame, text="Both", variable=self.orientation_var, value="horizontal + vertical", command=self._toggle_orientation_options).pack(side=tk.LEFT)
        ttk.Radiobutton(orientation_frame, text="Original", variable=self.orientation_var, value="original", command=self._toggle_orientation_options).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(orientation_frame, text="Hybrid", variable=self.orientation_var, value="hybrid (stacked)", command=self._toggle_orientation_options).pack(side=tk.LEFT, padx=(5,0))

        self.aspect_ratio_frame = ttk.LabelFrame(geometry_group, text="Aspect Ratio", padding=10); self.aspect_ratio_frame.pack(fill=tk.X, pady=5)
        self.horizontal_rb_frame = ttk.Frame(self.aspect_ratio_frame)
        ttk.Radiobutton(self.horizontal_rb_frame, text="16:9 (Widescreen)", variable=self.horizontal_aspect_var, value="16:9", command=lambda: self._update_selected_jobs("horizontal_aspect")).pack(anchor="w")
        ttk.Radiobutton(self.horizontal_rb_frame, text="5:4", variable=self.horizontal_aspect_var, value="5:4", command=lambda: self._update_selected_jobs("horizontal_aspect")).pack(anchor="w")
        ttk.Radiobutton(self.horizontal_rb_frame, text="4:3 (Classic TV)", variable=self.horizontal_aspect_var, value="4:3", command=lambda: self._update_selected_jobs("horizontal_aspect")).pack(anchor="w")
        self.vertical_rb_frame = ttk.Frame(self.aspect_ratio_frame)
        ttk.Radiobutton(self.vertical_rb_frame, text="9:16 (Shorts/Reels)", variable=self.vertical_aspect_var, value="9:16", command=lambda: self._update_selected_jobs("vertical_aspect")).pack(anchor="w")
        ttk.Radiobutton(self.vertical_rb_frame, text="4:5 (Instagram Post)", variable=self.vertical_aspect_var, value="4:5", command=lambda: self._update_selected_jobs("vertical_aspect")).pack(anchor="w")
        ttk.Radiobutton(self.vertical_rb_frame, text="3:4 (Social Post)", variable=self.vertical_aspect_var, value="3:4", command=lambda: self._update_selected_jobs("vertical_aspect")).pack(anchor="w")

        self.hybrid_frame = ttk.Frame(geometry_group)
        self.top_video_frame = ttk.LabelFrame(self.hybrid_frame, text="Top Video", padding=5); self.top_video_frame.pack(fill=tk.X, pady=(5,0))
        ttk.Label(self.top_video_frame, text="Aspect:").pack(side=tk.LEFT, padx=(0,5))
        ttk.Radiobutton(self.top_video_frame, text="16:9", variable=self.hybrid_top_aspect_var, value="16:9", command=lambda: self._update_selected_jobs("hybrid_top_aspect")).pack(side=tk.LEFT)
        ttk.Radiobutton(self.top_video_frame, text="4:5", variable=self.hybrid_top_aspect_var, value="4:5", command=lambda: self._update_selected_jobs("hybrid_top_aspect")).pack(side=tk.LEFT)
        ttk.Radiobutton(self.top_video_frame, text="4:3", variable=self.hybrid_top_aspect_var, value="4:3", command=lambda: self._update_selected_jobs("hybrid_top_aspect")).pack(side=tk.LEFT, padx=5)
        ttk.Label(self.top_video_frame, text="Handling:").pack(side=tk.LEFT, padx=(15,5))
        ttk.Radiobutton(self.top_video_frame, text="Crop", variable=self.hybrid_top_mode_var, value="crop", command=lambda: self._update_selected_jobs("hybrid_top_mode")).pack(side=tk.LEFT)
        ttk.Radiobutton(self.top_video_frame, text="Pad", variable=self.hybrid_top_mode_var, value="pad", command=lambda: self._update_selected_jobs("hybrid_top_mode")).pack(side=tk.LEFT, padx=5)
        self.bottom_video_frame = ttk.LabelFrame(self.hybrid_frame, text="Bottom Video", padding=5); self.bottom_video_frame.pack(fill=tk.X, pady=5)
        ttk.Label(self.bottom_video_frame, text="Aspect:").pack(side=tk.LEFT, padx=(0,5))
        ttk.Radiobutton(self.bottom_video_frame, text="16:9", variable=self.hybrid_bottom_aspect_var, value="16:9", command=lambda: self._update_selected_jobs("hybrid_bottom_aspect")).pack(side=tk.LEFT)
        ttk.Radiobutton(self.bottom_video_frame, text="4:5", variable=self.hybrid_bottom_aspect_var, value="4:5", command=lambda: self._update_selected_jobs("hybrid_bottom_aspect")).pack(side=tk.LEFT)
        ttk.Radiobutton(self.bottom_video_frame, text="4:3", variable=self.hybrid_bottom_aspect_var, value="4:3", command=lambda: self._update_selected_jobs("hybrid_bottom_aspect")).pack(side=tk.LEFT, padx=5)
        ttk.Label(self.bottom_video_frame, text="Handling:").pack(side=tk.LEFT, padx=(15,5))
        ttk.Radiobutton(self.bottom_video_frame, text="Crop", variable=self.hybrid_bottom_mode_var, value="crop", command=lambda: self._update_selected_jobs("hybrid_bottom_mode")).pack(side=tk.LEFT)
        ttk.Radiobutton(self.bottom_video_frame, text="Pad", variable=self.hybrid_bottom_mode_var, value="pad", command=lambda: self._update_selected_jobs("hybrid_bottom_mode")).pack(side=tk.LEFT, padx=5)
        aspect_handling_frame = ttk.Frame(geometry_group); aspect_handling_frame.pack(fill=tk.X, pady=5)
        ttk.Label(aspect_handling_frame, text="Handling:").pack(side=tk.LEFT, padx=(0,5))
        ttk.Radiobutton(aspect_handling_frame, text="Crop (Fill)", variable=self.aspect_mode_var, value="crop", command=self._toggle_upscale_options).pack(side=tk.LEFT)
        ttk.Radiobutton(aspect_handling_frame, text="Pad (Fit)", variable=self.aspect_mode_var, value="pad", command=self._toggle_upscale_options).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(aspect_handling_frame, text="Stretch", variable=self.aspect_mode_var, value="stretch", command=self._toggle_upscale_options).pack(side=tk.LEFT)

        quality_group = ttk.LabelFrame(parent, text="Format & Quality", padding=10); quality_group.pack(fill=tk.X, pady=(5, 5))
        resolution_options_frame = ttk.Frame(quality_group); resolution_options_frame.pack(fill=tk.X)
        ttk.Label(resolution_options_frame, text="Resolution:").pack(side=tk.LEFT, padx=(0,5))
        self.rb_hd = ttk.Radiobutton(resolution_options_frame, text="HD", variable=self.resolution_var, value="HD", command=lambda: self._update_selected_jobs("resolution")); self.rb_hd.pack(side=tk.LEFT)
        self.rb_4k = ttk.Radiobutton(resolution_options_frame, text="4k", variable=self.resolution_var, value="4k", command=lambda: self._update_selected_jobs("resolution")); self.rb_4k.pack(side=tk.LEFT, padx=5)
        self.rb_8k = ttk.Radiobutton(resolution_options_frame, text="8k", variable=self.resolution_var, value="8k", command=lambda: self._update_selected_jobs("resolution")); self.rb_8k.pack(side=tk.LEFT)
        ToolTip(self.rb_hd, "HD: 1920x1080 (H) or 1080px wide (V/Hybrid)."); ToolTip(self.rb_4k, "4K: 3840x2160 (H) or 2160px wide (V/Hybrid)."); ToolTip(self.rb_8k, "8K: 7680x4320 (H) or 4320px wide (V/Hybrid).")
        upscale_frame = ttk.Frame(quality_group); upscale_frame.pack(fill=tk.X, pady=(5,0))
        ttk.Label(upscale_frame, text="Upscale Algo:").pack(side=tk.LEFT, padx=(0,5))
        ttk.Radiobutton(upscale_frame, text="Lanczos", variable=self.upscale_algo_var, value="lanczos", command=lambda: self._update_selected_jobs("upscale_algo")).pack(side=tk.LEFT)
        ttk.Radiobutton(upscale_frame, text="Bicubic", variable=self.upscale_algo_var, value="bicubic", command=lambda: self._update_selected_jobs("upscale_algo")).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(upscale_frame, text="Bilinear", variable=self.upscale_algo_var, value="bilinear", command=lambda: self._update_selected_jobs("upscale_algo")).pack(side=tk.LEFT)
        output_format_frame = ttk.Frame(quality_group); output_format_frame.pack(fill=tk.X, pady=(5,0))
        ttk.Label(output_format_frame, text="Output Format:").pack(side=tk.LEFT, padx=(0,5))
        ttk.Radiobutton(output_format_frame, text="SDR", variable=self.output_format_var, value="sdr", command=lambda: self._update_selected_jobs("output_format")).pack(side=tk.LEFT)
        ttk.Radiobutton(output_format_frame, text="HDR", variable=self.output_format_var, value="hdr", command=lambda: self._update_selected_jobs("output_format")).pack(side=tk.LEFT, padx=5)
        ttk.Label(output_format_frame, text="Location:").pack(side=tk.LEFT, padx=(15,5))
        ttk.Radiobutton(output_format_frame, text="Local", variable=self.output_mode_var, value="local").pack(side=tk.LEFT)
        ttk.Radiobutton(output_format_frame, text="Pooled", variable=self.output_mode_var, value="pooled").pack(side=tk.LEFT, padx=5)
        lut_frame = ttk.Frame(quality_group); lut_frame.pack(fill=tk.X, pady=(5,0))
        ttk.Label(lut_frame, text="LUT Path:").pack(side=tk.LEFT, padx=(0,5))
        self.lut_entry = ttk.Entry(lut_frame, textvariable=self.lut_file_var); self.lut_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(lut_frame, text="...", command=self.browse_lut_file, width=4).pack(side=tk.LEFT)
        ToolTip(self.lut_entry, "Path to LUT file for HDR to SDR conversion")
        bitrate_frame = ttk.Frame(quality_group); bitrate_frame.pack(fill=tk.X, pady=(5,0))
        ttk.Checkbutton(bitrate_frame, text="Override Bitrate", variable=self.override_bitrate_var, command=self._toggle_bitrate_override).pack(side=tk.LEFT)
        self.manual_bitrate_entry = ttk.Entry(bitrate_frame, textvariable=self.manual_bitrate_var, width=10, state="disabled"); self.manual_bitrate_entry.pack(side=tk.LEFT, padx=5)
        ttk.Label(bitrate_frame, text="kbps").pack(side=tk.LEFT)
        fruc_frame = ttk.Frame(quality_group); fruc_frame.pack(fill=tk.X, pady=(5,0))
        ttk.Checkbutton(fruc_frame, text="Enable FRUC", variable=self.fruc_var, command=lambda: [self.toggle_fruc_fps(), self._update_selected_jobs("fruc")]).pack(side=tk.LEFT)
        ttk.Label(fruc_frame, text="FRUC FPS:").pack(side=tk.LEFT, padx=(5,5))
        self.fruc_fps_entry = ttk.Entry(fruc_frame, textvariable=self.fruc_fps_var, width=5, state="disabled"); self.fruc_fps_entry.pack(side=tk.LEFT)

    def setup_audio_tab(self, parent):
        # Normalization Group
        norm_group = ttk.LabelFrame(parent, text="Normalization", padding=10)
        norm_group.pack(fill=tk.X, pady=(0, 5))
        ttk.Checkbutton(norm_group, text="Normalize Audio (EBU R128)", variable=self.normalize_audio_var, command=self._toggle_audio_norm_options).pack(anchor="w")

        self.audio_norm_frame = ttk.Frame(norm_group)
        self.audio_norm_frame.pack(fill=tk.X, padx=(20, 0), pady=5)
        self.audio_norm_frame.columnconfigure(1, weight=1)

        ttk.Label(self.audio_norm_frame, text="Loudness Target (LUFS):").grid(row=0, column=0, sticky="w", pady=2)
        self.loudness_target_entry = ttk.Entry(self.audio_norm_frame, textvariable=self.loudness_target_var, width=8)
        self.loudness_target_entry.grid(row=0, column=1, sticky="w", padx=5)

        ttk.Label(self.audio_norm_frame, text="Loudness Range (LRA):").grid(row=1, column=0, sticky="w", pady=2)
        self.loudness_range_entry = ttk.Entry(self.audio_norm_frame, textvariable=self.loudness_range_var, width=8)
        self.loudness_range_entry.grid(row=1, column=1, sticky="w", padx=5)

        ttk.Label(self.audio_norm_frame, text="True Peak (dBTP):").grid(row=2, column=0, sticky="w", pady=2)
        self.true_peak_entry = ttk.Entry(self.audio_norm_frame, textvariable=self.true_peak_var, width=8)
        self.true_peak_entry.grid(row=2, column=1, sticky="w", padx=5)

        # Output Tracks Group
        tracks_group = ttk.LabelFrame(parent, text="Output Audio Tracks", padding=10)
        tracks_group.pack(fill=tk.X, pady=5)

        self.audio_cb_mono = ttk.Checkbutton(tracks_group, text="Mono (Downmix)", variable=self.audio_mono_var, command=self._update_audio_options_ui)
        self.audio_cb_mono.pack(anchor="w")

        self.audio_cb_stereo = ttk.Checkbutton(tracks_group, text="Stereo (Standard Downmix)", variable=self.audio_stereo_downmix_var, command=self._update_audio_options_ui)
        self.audio_cb_stereo.pack(anchor="w")

        self.audio_cb_sofa = ttk.Checkbutton(tracks_group, text="Stereo (Sofalizer for Headphones)", variable=self.audio_stereo_sofalizer_var, command=self._update_audio_options_ui)
        self.audio_cb_sofa.pack(anchor="w")

        sofa_frame = ttk.Frame(tracks_group)
        sofa_frame.pack(fill=tk.X, padx=(20, 0))
        ttk.Label(sofa_frame, text="SOFA File:").pack(side=tk.LEFT)
        self.sofa_entry = ttk.Entry(sofa_frame, textvariable=self.sofa_file_var)
        self.sofa_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.sofa_browse_btn = ttk.Button(sofa_frame, text="...", command=self.browse_sofa_file, width=4)
        self.sofa_browse_btn.pack(side=tk.LEFT)

        self.audio_cb_surround = ttk.Checkbutton(tracks_group, text="5.1 Surround", variable=self.audio_surround_51_var, command=self._update_audio_options_ui)
        self.audio_cb_surround.pack(anchor="w", pady=(5,0))

        ttk.Separator(tracks_group, orient='horizontal').pack(fill='x', pady=10)

        self.audio_cb_passthrough = ttk.Checkbutton(tracks_group, text="Passthrough (Copy Original Audio)", variable=self.audio_passthrough_var, command=self._update_audio_options_ui)
        self.audio_cb_passthrough.pack(anchor="w")

    def setup_subtitle_tab(self, parent):
        action_frame = ttk.Frame(parent)
        action_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Checkbutton(action_frame, text="Enable Subtitle Burning", variable=self.burn_subtitles_var, command=lambda: self._update_selected_jobs("burn_subtitles")).pack(side=tk.LEFT)

        main_style_group = ttk.LabelFrame(parent, text="Subtitle Styling", padding=10)
        main_style_group.pack(fill=tk.BOTH, expand=True)

        general_style_frame = ttk.LabelFrame(main_style_group, text="General Style", padding=10)
        general_style_frame.pack(fill=tk.X, pady=5)
        font_frame = ttk.Frame(general_style_frame); font_frame.pack(fill=tk.X, pady=2)
        ttk.Label(font_frame, text="Font:").pack(side=tk.LEFT, padx=(0, 19))
        self.font_combo = ttk.Combobox(font_frame, textvariable=self.subtitle_font_var, width=25)
        self.font_combo.pack(side=tk.LEFT, padx=5)
        self.font_combo.bind("<<ComboboxSelected>>", lambda e: self._update_selected_jobs("subtitle_font"))
        self.populate_fonts()
        ttk.Label(font_frame, text="Size:").pack(side=tk.LEFT, padx=(10, 5))
        font_size_entry = ttk.Entry(font_frame, textvariable=self.subtitle_font_size_var, width=5)
        font_size_entry.pack(side=tk.LEFT)
        style_frame = ttk.Frame(general_style_frame); style_frame.pack(fill=tk.X, pady=2)
        ttk.Checkbutton(style_frame, text="Bold", variable=self.subtitle_bold_var, command=lambda: self._update_selected_jobs("subtitle_bold")).pack(side=tk.LEFT)
        ttk.Checkbutton(style_frame, text="Italic", variable=self.subtitle_italic_var, command=lambda: self._update_selected_jobs("subtitle_italic")).pack(side=tk.LEFT, padx=15)
        ttk.Checkbutton(style_frame, text="Underline", variable=self.subtitle_underline_var, command=lambda: self._update_selected_jobs("subtitle_underline")).pack(side=tk.LEFT)
        align_frame = ttk.Frame(general_style_frame); align_frame.pack(fill=tk.X, pady=2)
        ttk.Label(align_frame, text="Align:").pack(side=tk.LEFT, padx=(0, 15))
        ttk.Radiobutton(align_frame, text="Top", variable=self.subtitle_alignment_var, value="top", command=lambda: self._update_selected_jobs("subtitle_alignment")).pack(side=tk.LEFT)
        ttk.Radiobutton(align_frame, text="Mid", variable=self.subtitle_alignment_var, value="middle", command=lambda: self._update_selected_jobs("subtitle_alignment")).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(align_frame, text="Bot", variable=self.subtitle_alignment_var, value="bottom", command=lambda: self._update_selected_jobs("subtitle_alignment")).pack(side=tk.LEFT)
        self.seam_align_rb = ttk.Radiobutton(align_frame, text="At Seam (Hybrid Only)", variable=self.subtitle_alignment_var, value="seam", command=lambda: self._update_selected_jobs("subtitle_alignment"))
        self.seam_align_rb.pack(side=tk.LEFT, padx=5)
        self.seam_align_rb.config(state="disabled")
        ttk.Label(align_frame, text="V-Margin:").pack(side=tk.LEFT, padx=(10, 5))
        margin_v_entry = ttk.Entry(align_frame, textvariable=self.subtitle_margin_v_var, width=5)
        margin_v_entry.pack(side=tk.LEFT)
        reformat_frame = ttk.LabelFrame(main_style_group, text="Line Formatting", padding=10)
        reformat_frame.pack(fill=tk.X, pady=5)
        ttk.Checkbutton(reformat_frame, text="Reformat to Single Wrapped Line", variable=self.reformat_subtitles_var, command=lambda: self._update_selected_jobs("reformat_subtitles")).pack(side=tk.LEFT)
        ttk.Label(reformat_frame, text="Wrap at:").pack(side=tk.LEFT, padx=(10, 5))
        wrap_limit_entry = ttk.Entry(reformat_frame, textvariable=self.wrap_limit_var, width=5)
        wrap_limit_entry.pack(side=tk.LEFT)
        ttk.Label(reformat_frame, text="chars").pack(side=tk.LEFT, padx=(2,0))

        # --- Collapsible Panes for Color Properties ---
        fill_pane = CollapsiblePane(main_style_group, "Fill Properties", initial_state='expanded')
        fill_pane.pack(fill=tk.X, pady=2, padx=2)
        outline_pane = CollapsiblePane(main_style_group, "Outline Properties")
        outline_pane.pack(fill=tk.X, pady=2, padx=2)
        shadow_pane = CollapsiblePane(main_style_group, "Shadow Properties")
        shadow_pane.pack(fill=tk.X, pady=2, padx=2)

        # Fill Properties
        fill_pane.container.columnconfigure(3, weight=1)
        ttk.Label(fill_pane.container, text="Color:").grid(row=0, column=0, sticky="w", padx=(0,5))
        self.fill_swatch = tk.Label(fill_pane.container, text="    ", bg=self.fill_color_var.get(), relief="sunken"); self.fill_swatch.grid(row=0, column=1)
        ttk.Button(fill_pane.container, text="..", command=lambda: self.choose_color(self.fill_color_var, self.fill_swatch, "fill_color"), width=3).grid(row=0, column=2, padx=5)
        fill_alpha_scale = ttk.Scale(fill_pane.container, from_=0, to=255, orient=tk.HORIZONTAL, variable=self.fill_alpha_var, command=lambda val: self._update_selected_jobs("fill_alpha"))
        fill_alpha_scale.grid(row=0, column=3, sticky="ew")
        ToolTip(fill_alpha_scale, "Fill Alpha (Transparency)")

        # Outline Properties
        outline_pane.container.columnconfigure(3, weight=1)
        ttk.Label(outline_pane.container, text="Color:").grid(row=0, column=0, sticky="w", padx=(0,5))
        self.outline_swatch = tk.Label(outline_pane.container, text="    ", bg=self.outline_color_var.get(), relief="sunken"); self.outline_swatch.grid(row=0, column=1)
        ttk.Button(outline_pane.container, text="..", command=lambda: self.choose_color(self.outline_color_var, self.outline_swatch, "outline_color"), width=3).grid(row=0, column=2, padx=5)
        outline_alpha_scale = ttk.Scale(outline_pane.container, from_=0, to=255, orient=tk.HORIZONTAL, variable=self.outline_alpha_var, command=lambda val: self._update_selected_jobs("outline_alpha"))
        outline_alpha_scale.grid(row=0, column=3, sticky="ew")
        ToolTip(outline_alpha_scale, "Outline Alpha (Transparency)")
        ttk.Label(outline_pane.container, text="Width:").grid(row=1, column=0, sticky="w", pady=(5,0))
        outline_width_entry = ttk.Entry(outline_pane.container, textvariable=self.outline_width_var, width=5)
        outline_width_entry.grid(row=1, column=1, columnspan=2, sticky="w", pady=(5,0), padx=(0, 5))

        # Shadow Properties
        shadow_pane.container.columnconfigure(3, weight=1)
        ttk.Label(shadow_pane.container, text="Color:").grid(row=0, column=0, sticky="w", padx=(0,5))
        self.shadow_swatch = tk.Label(shadow_pane.container, text="    ", bg=self.shadow_color_var.get(), relief="sunken"); self.shadow_swatch.grid(row=0, column=1)
        ttk.Button(shadow_pane.container, text="..", command=lambda: self.choose_color(self.shadow_color_var, self.shadow_swatch, "shadow_color"), width=3).grid(row=0, column=2, padx=5)
        shadow_alpha_scale = ttk.Scale(shadow_pane.container, from_=0, to=255, orient=tk.HORIZONTAL, variable=self.shadow_alpha_var, command=lambda val: self._update_selected_jobs("shadow_alpha"))
        shadow_alpha_scale.grid(row=0, column=3, sticky="ew")
        ToolTip(shadow_alpha_scale, "Shadow Alpha (Transparency)")
        offset_frame = ttk.Frame(shadow_pane.container); offset_frame.grid(row=1, column=0, columnspan=4, sticky="w", pady=(5,0))
        ttk.Label(offset_frame, text="Offset X:").pack(side=tk.LEFT)
        shadow_offset_x_entry = ttk.Entry(offset_frame, textvariable=self.shadow_offset_x_var, width=5)
        shadow_offset_x_entry.pack(side=tk.LEFT, padx=(5,10))
        ttk.Label(offset_frame, text="Y:").pack(side=tk.LEFT)
        shadow_offset_y_entry = ttk.Entry(offset_frame, textvariable=self.shadow_offset_y_var, width=5)
        shadow_offset_y_entry.pack(side=tk.LEFT, padx=5)
        ttk.Label(offset_frame, text="Blur:").pack(side=tk.LEFT, padx=(10,5))
        shadow_blur_entry = ttk.Entry(offset_frame, textvariable=self.shadow_blur_var, width=5)
        shadow_blur_entry.pack(side=tk.LEFT, padx=5)

    def setup_button_row(self, parent):
        # FIX: Use style.map() for robust button coloring
        style = ttk.Style(self.root)
        style.configure("Start.TButton", font=("Arial", 10, "bold"), padding=5)
        style.map("Start.TButton",
            foreground=[('!disabled', 'green')],
            background=[('!disabled', '#4CAF50'), ('active', '#58c05c')]
        )
        
        self.start_button = ttk.Button(parent, text="Start Processing", command=self.start_processing, style="Start.TButton")
        self.start_button.pack(side=tk.LEFT, padx=5, ipady=5)
        self.generate_log_checkbox = ttk.Checkbutton(parent, text="Generate Log File", variable=self.generate_log_var, command=lambda: self._update_selected_jobs("generate_log"))
        self.generate_log_checkbox.pack(side=tk.LEFT, padx=(10, 0))

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

    def browse_sofa_file(self):
        file_path = filedialog.askopenfilename(title="Select SOFA File", filetypes=[("SOFA Files", "*.sofa"), ("All Files", "*.*")])
        if file_path:
            self.sofa_file_var.set(file_path)
            self._update_selected_jobs("sofa_file")

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
        current_alignment = self.subtitle_alignment_var.get()

        # --- Manage UI visibility and seam alignment ---
        if orientation == "hybrid (stacked)":
            if current_alignment != "seam":
                self.last_standard_alignment.set(current_alignment)
                self.subtitle_alignment_var.set("seam")
            self.seam_align_rb.config(state="normal")
        else:
            if current_alignment == "seam":
                self.subtitle_alignment_var.set(self.last_standard_alignment.get())
            self.seam_align_rb.config(state="disabled")
        
        self.aspect_ratio_frame.pack_forget()
        self.horizontal_rb_frame.pack_forget()
        self.vertical_rb_frame.pack_forget()
        self.hybrid_frame.pack_forget()
        
        if orientation == "horizontal":
            self.aspect_ratio_frame.config(text="Horizontal Aspect Ratio")
            self.horizontal_rb_frame.pack(fill="x")
            self.aspect_ratio_frame.pack(fill=tk.X, pady=5)
        elif orientation == "vertical":
            self.aspect_ratio_frame.config(text="Vertical Aspect Ratio")
            self.vertical_rb_frame.pack(fill="x")
            self.aspect_ratio_frame.pack(fill=tk.X, pady=5)
        elif orientation == "horizontal + vertical":
            self.aspect_ratio_frame.config(text="Aspect Ratios (H & V)")
            self.horizontal_rb_frame.pack(fill="x", pady=(0, 5))
            self.vertical_rb_frame.pack(fill="x")
            self.aspect_ratio_frame.pack(fill=tk.X, pady=5)
        elif orientation == "hybrid (stacked)":
            self.hybrid_frame.pack(fill=tk.X, pady=5)
        elif orientation == "original":
            self.aspect_ratio_frame.config(text="Aspect Ratio (Original – unchanged)")
            self.aspect_ratio_frame.pack(fill=tk.X, pady=5)

        # --- IMPLEMENTED: Intelligent Subtitle Burning Workflow ---
        is_vertical_target = orientation in ["vertical", "hybrid (stacked)", "horizontal + vertical"]

        if is_vertical_target:
            selected_indices = self.job_listbox.curselection()
            should_enable_burn = False
            if selected_indices:
                for index in selected_indices:
                    job = self.processing_jobs[index]
                    if job.get('subtitle_path') is not None:
                        should_enable_burn = True
                        break 
            
            if should_enable_burn:
                self.burn_subtitles_var.set(True)
        
        # Update the selected jobs with all relevant changes
        self._update_selected_jobs("orientation", "subtitle_alignment", "burn_subtitles")

    def _toggle_upscale_options(self):
        self._update_selected_jobs("aspect_mode")

    def _toggle_audio_norm_options(self):
        state = "normal" if self.normalize_audio_var.get() else "disabled"
        for widget in [self.loudness_target_entry, self.loudness_range_entry, self.true_peak_entry]:
            widget.config(state=state)
        self._update_selected_jobs("normalize_audio")

    def _update_audio_options_ui(self):
        """Manages the state of all audio UI elements based on selections."""
        is_passthrough = self.audio_passthrough_var.get()
        is_sofalizer = self.audio_stereo_sofalizer_var.get()

        # Mutual exclusivity for passthrough
        if is_passthrough:
            self.audio_mono_var.set(False)
            self.audio_stereo_downmix_var.set(False)
            self.audio_stereo_sofalizer_var.set(False)
            self.audio_surround_51_var.set(False)
            proc_state = "disabled"
        else:
            proc_state = "normal"
        
        for cb in [self.audio_cb_mono, self.audio_cb_stereo, self.audio_cb_sofa, self.audio_cb_surround]:
            cb.config(state=proc_state)
            
        any_proc_selected = any([self.audio_mono_var.get(), self.audio_stereo_downmix_var.get(),
                                 self.audio_stereo_sofalizer_var.get(), self.audio_surround_51_var.get()])

        self.audio_cb_passthrough.config(state="disabled" if any_proc_selected else "normal")

        # Contextual SOFA file input
        sofa_state = "normal" if is_sofalizer and not is_passthrough else "disabled"
        self.sofa_entry.config(state=sofa_state)
        self.sofa_browse_btn.config(state=sofa_state)

        # Update job options for any changes
        self._update_selected_jobs(
            "audio_mono", "audio_stereo_downmix", "audio_stereo_sofalizer",
            "audio_surround_51", "audio_passthrough", "sofa_file"
        )

    def update_status(self, message):
        self.status_var.set(message)
        self.root.update_idletasks()

    def _update_selected_jobs(self, *keys_to_update):
        selected_indices = self.job_listbox.curselection()
        if not selected_indices:
            return
        current_options = self.get_current_gui_options()
        options_to_apply = {key: current_options[key] for key in keys_to_update if key in current_options}
        if options_to_apply:
             debug_print(f"[GUI ACTION] Applied {options_to_apply} to {len(selected_indices)} selected job(s).")
             for index in selected_indices:
                job = self.processing_jobs[index]
                job['options'].update(options_to_apply)

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
            "true_peak": self.true_peak_var.get(), 
            "audio_mono": self.audio_mono_var.get(), "audio_stereo_downmix": self.audio_stereo_downmix_var.get(),
            "audio_stereo_sofalizer": self.audio_stereo_sofalizer_var.get(), "audio_surround_51": self.audio_surround_51_var.get(),
            "audio_passthrough": self.audio_passthrough_var.get(),
            "sofa_file": self.sofa_file_var.get(),
            "lut_file": self.lut_file_var.get(),
            "hybrid_top_aspect": self.hybrid_top_aspect_var.get(), "hybrid_top_mode": self.hybrid_top_mode_var.get(),
            "hybrid_bottom_aspect": self.hybrid_bottom_aspect_var.get(), "hybrid_bottom_mode": self.hybrid_bottom_mode_var.get(),
            "subtitle_font": self.subtitle_font_var.get(), "subtitle_font_size": self.subtitle_font_size_var.get(),
            "subtitle_alignment": self.subtitle_alignment_var.get(), "subtitle_bold": self.subtitle_bold_var.get(),
            "subtitle_italic": self.subtitle_italic_var.get(), "subtitle_underline": self.subtitle_underline_var.get(),
            "subtitle_margin_v": self.subtitle_margin_v_var.get(), "fill_color": self.fill_color_var.get(),
            "fill_alpha": self.fill_alpha_var.get(), "outline_color": self.outline_color_var.get(),
            "outline_alpha": self.outline_alpha_var.get(), "outline_width": self.outline_width_var.get(),
            "shadow_color": self.shadow_color_var.get(), "shadow_alpha": self.shadow_alpha_var.get(),
            "shadow_offset_x": self.shadow_offset_x_var.get(), "shadow_offset_y": self.shadow_offset_y_var.get(),
            "shadow_blur": self.shadow_blur_var.get(),
            "reformat_subtitles": self.reformat_subtitles_var.get(), "wrap_limit": self.wrap_limit_var.get(),
        }

    def add_video_files_and_discover_jobs(self, file_paths):
        for video_path in file_paths:
            video_path = os.path.abspath(video_path)
            dir_name, video_basename = os.path.dirname(video_path), os.path.splitext(os.path.basename(video_path))[0]
            current_options = self.get_current_gui_options()
            no_sub_job = {
                "job_id": f"job_{time.time()}_{len(self.processing_jobs)}",
                "video_path": video_path,
                "subtitle_path": None,
                "options": copy.deepcopy(current_options)
            }
            no_sub_job["display_name"] = f"{os.path.basename(video_path)} [No Subtitles]"
            self.processing_jobs.append(no_sub_job)
            self.job_listbox.insert(tk.END, no_sub_job["display_name"])
            try:
                for item in os.listdir(dir_name):
                    if item.lower().endswith('.srt'):
                        srt_basename = os.path.splitext(item)[0]
                        if srt_basename == video_basename or (srt_basename.startswith(video_basename) and len(srt_basename) > len(video_basename) and srt_basename[len(video_basename)] in [' ', '.', '-', '_']):
                            full_path = os.path.join(dir_name, item)
                            tag = srt_basename[len(video_basename):].strip(' .-_') or "(exact match)"
                            sub_job = copy.deepcopy(no_sub_job)
                            sub_job['job_id'] = f"job_{time.time()}_{len(self.processing_jobs)}"
                            sub_job['subtitle_path'] = full_path
                            sub_job['options']['burn_subtitles'] = True
                            sub_job['display_name'] = f"{os.path.basename(video_path)} [Sub: {tag}]"
                            self.processing_jobs.append(sub_job)
                            self.job_listbox.insert(tk.END, sub_job['display_name'])
            except Exception as e:
                print(f"[WARN] Could not scan for external subtitles in {dir_name}: {e}")
            embedded_subs = get_subtitle_stream_info(video_path)
            for relative_index, sub_stream in enumerate(embedded_subs):
                tags = sub_stream.get("tags", {})
                lang = tags.get("language", "und")
                title = tags.get("title", f"Track {sub_stream.get('index')}")
                codec = sub_stream.get('codec_name', 'sub').upper()
                sub_job = copy.deepcopy(no_sub_job)
                sub_job['job_id'] = f"job_{time.time()}_{len(self.processing_jobs)}"
                sub_job['subtitle_path'] = f"embedded:{relative_index}"
                sub_job['options']['burn_subtitles'] = True
                sub_job['display_name'] = f"{os.path.basename(video_path)} [Embedded: {lang.title()} - {title} ({codec})]"
                self.processing_jobs.append(sub_job)
                self.job_listbox.insert(tk.END, sub_job['display_name'])
        if self.processing_jobs:
            self.job_listbox.selection_clear(0, tk.END)
            self.job_listbox.selection_set(0)
            self.on_input_file_select(None)
        self._update_bitrate_display()

    def on_input_file_select(self, event=None):
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
        self.loudness_range_var.set(options.get("loudness_range", DEFAULT_LOUDNESS_RANGE)); self.true_peak_var.set(options.get("true_peak", DEFAULT_TRUE_PEAK)); 
        self.sofa_file_var.set(options.get("sofa_file", r"E:\Small-Scripts\SOFALIZER\D1_48K_24bit_256tap_FIR_SOFA.sofa"))
        self.hybrid_top_aspect_var.set(options.get("hybrid_top_aspect", "16:9")); self.hybrid_top_mode_var.set(options.get("hybrid_top_mode", "crop"))
        self.hybrid_bottom_aspect_var.set(options.get("hybrid_bottom_aspect", "4:5")); self.hybrid_bottom_mode_var.set(options.get("hybrid_bottom_mode", "crop"))
        self.subtitle_font_var.set(options.get("subtitle_font", DEFAULT_SUBTITLE_FONT)); self.subtitle_font_size_var.set(options.get("subtitle_font_size", DEFAULT_SUBTITLE_FONT_SIZE)); self.subtitle_alignment_var.set(options.get("subtitle_alignment", DEFAULT_SUBTITLE_ALIGNMENT))
        self.subtitle_bold_var.set(options.get("subtitle_bold", DEFAULT_SUBTITLE_BOLD)); self.subtitle_italic_var.set(options.get("subtitle_italic", DEFAULT_SUBTITLE_ITALIC)); self.subtitle_underline_var.set(options.get("subtitle_underline", DEFAULT_SUBTITLE_UNDERLINE))
        self.subtitle_margin_v_var.set(options.get("subtitle_margin_v", DEFAULT_SUBTITLE_MARGIN_V)); self.fill_color_var.set(options.get("fill_color", DEFAULT_FILL_COLOR)); self.fill_alpha_var.set(options.get("fill_alpha", DEFAULT_FILL_ALPHA))
        self.outline_color_var.set(options.get("outline_color", DEFAULT_OUTLINE_COLOR)); self.outline_alpha_var.set(options.get("outline_alpha", DEFAULT_OUTLINE_ALPHA))
        self.outline_width_var.set(options.get("outline_width", DEFAULT_OUTLINE_WIDTH)); self.shadow_color_var.set(options.get("shadow_color", DEFAULT_SHADOW_COLOR))
        self.shadow_alpha_var.set(options.get("shadow_alpha", DEFAULT_SHADOW_ALPHA)); self.shadow_offset_x_var.set(options.get("shadow_offset_x", DEFAULT_SHADOW_OFFSET_X)); self.shadow_offset_y_var.set(options.get("shadow_offset_y", DEFAULT_SHADOW_OFFSET_Y))
        self.shadow_blur_var.set(options.get("shadow_blur", DEFAULT_SHADOW_BLUR)); self.lut_file_var.set(options.get("lut_file", DEFAULT_LUT_PATH))
        self.reformat_subtitles_var.set(options.get("reformat_subtitles", DEFAULT_REFORMAT_SUBTITLES))
        self.wrap_limit_var.set(options.get("wrap_limit", DEFAULT_WRAP_LIMIT))
        self.audio_mono_var.set(options.get("audio_mono", DEFAULT_AUDIO_MONO))
        self.audio_stereo_downmix_var.set(options.get("audio_stereo_downmix", DEFAULT_AUDIO_STEREO_DOWNMIX))
        self.audio_stereo_sofalizer_var.set(options.get("audio_stereo_sofalizer", DEFAULT_AUDIO_STEREO_SOFALIZER))
        self.audio_surround_51_var.set(options.get("audio_surround_51", DEFAULT_AUDIO_SURROUND_51))
        self.audio_passthrough_var.set(options.get("audio_passthrough", DEFAULT_AUDIO_PASSTHROUGH))

        self.fill_swatch.config(bg=self.fill_color_var.get()); self.outline_swatch.config(bg=self.outline_color_var.get()); self.shadow_swatch.config(bg=self.shadow_color_var.get())
        self._toggle_bitrate_override(); self.toggle_fruc_fps(); self._toggle_orientation_options(); self._toggle_upscale_options(); self._toggle_audio_norm_options(); self._update_audio_options_ui()

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
        # 1. Handle Passthrough mode first as it's exclusive
        if options.get("audio_passthrough"):
            return ["-map", "0:a?", "-c:a", "copy"]

        # 2. Get info on available audio streams
        audio_streams = get_audio_stream_info(file_path)
        if not audio_streams:
            return ["-an"]  # No audio streams found, so disable audio

        # Prioritize surround, then stereo, then first available
        source_stream = next((s for s in audio_streams if int(s.get("channels", 0)) >= 6),
                             next((s for s in audio_streams if int(s.get("channels", 0)) == 2),
                                  audio_streams[0]))
        source_idx = source_stream['index']
        source_channels = int(source_stream.get("channels", 0))
        is_surround_source = source_channels >= 6

        # 3. Determine which tracks to build
        tracks_to_build = []
        if options.get("audio_mono"):
            tracks_to_build.append("mono")
        if options.get("audio_stereo_downmix"):
            tracks_to_build.append("stereo_downmix")
        if options.get("audio_stereo_sofalizer"):
            if is_surround_source:
                tracks_to_build.append("stereo_sofalizer")
            else:
                print(f"[WARN] Sofalizer requires a 5.1+ source. Skipping Sofalizer track for {os.path.basename(file_path)}.")
        if options.get("audio_surround_51"):
            if is_surround_source:
                tracks_to_build.append("surround_51")
            else:
                print(f"[WARN] 5.1 Surround output requires a 5.1+ source. Skipping 5.1 track for {os.path.basename(file_path)}.")

        if not tracks_to_build:
            print("[WARN] No valid audio tracks selected or possible for the source. Disabling audio.")
            return ["-an"]

        # 4. Build the filter_complex graph
        fc_parts = []
        final_maps = []
        base_input_tag = f"[0:{source_idx}]"
        
        # Create a split for each track to process them in parallel
        split_outputs = "".join(f"[s{i}]" for i in range(len(tracks_to_build)))
        fc_parts.append(f"{base_input_tag}asplit={len(tracks_to_build)}{split_outputs}")

        is_first_track = True
        output_audio_index = 0

        for i, track_type in enumerate(tracks_to_build):
            input_tag = f"[s{i}]"
            proc_tag = f"[{track_type}_proc]"
            final_tag = proc_tag

            # A. Build processing chain for this track type
            if track_type == "mono":
                fc_parts.append(f"{input_tag}pan=mono|c0=FC+0.707*FL+0.707*FR+0.5*LFE+0.707*SL+0.707*SR{proc_tag}")
            elif track_type == "stereo_downmix":
                fc_parts.append(f"{input_tag}pan=stereo|c0=0.707*c0+0.707*c2+0.707*c4+0.5*c3|c1=0.707*c1+0.707*c2+0.707*c5+0.5*c3{proc_tag}")
            elif track_type == "stereo_sofalizer":
                sofa_path = options.get("sofa_file", "").strip()
                if not sofa_path or not os.path.exists(sofa_path):
                    raise VideoProcessingError(f"Sofalizer enabled, but SOFA file not found or invalid: {sofa_path}")
                safe_sofa = sofa_path.replace("\\", "/").replace(":", "\\:")
                fc_parts.append(f"{input_tag}sofalizer=sofa='{safe_sofa}':normalize=enabled:speakers=FL 26|FR 334|FC 0|SL 100|SR 260|LFE 0|BL 142|BR 218{proc_tag}")
            elif track_type == "surround_51":
                fc_parts.append(f"{input_tag}channelmap=channel_layout=5.1(side){proc_tag}")

            # B. Apply normalization if enabled
            if options.get("normalize_audio", False):
                lt = options.get("loudness_target")
                lr = options.get("loudness_range")
                tp = options.get("true_peak")
                ln_tag = f"[{track_type}_ln]"
                fc_parts.append(f"{proc_tag}loudnorm=i={lt}:lra={lr}:tp={tp}{ln_tag}")
                final_tag = ln_tag

            # C. Resample and prepare for mapping
            resample_tag = f"[{track_type}_final]"
            fc_parts.append(f"{final_tag}aresample={AUDIO_SAMPLE_RATE}{resample_tag}")

            # D. Add mapping and metadata for this track
            final_maps.extend(["-map", resample_tag])
            
            # Codec and Bitrate
            if track_type == "mono":
                final_maps.extend([f"-c:a:{output_audio_index}", "aac", f"-b:a:{output_audio_index}", f"{MONO_BITRATE_K}k"])
                title = "Mono"
            elif "stereo" in track_type:
                final_maps.extend([f"-c:a:{output_audio_index}", "aac", f"-b:a:{output_audio_index}", f"{STEREO_BITRATE_K}k"])
                title = "Stereo (Binaural)" if track_type == "stereo_sofalizer" else "Stereo"
            elif track_type == "surround_51":
                final_maps.extend([f"-c:a:{output_audio_index}", "aac", f"-b:a:{output_audio_index}", f"{SURROUND_BITRATE_K}k"])
                title = "5.1 Surround"
            
            # Disposition and Title Metadata
            disposition = "default" if is_first_track else "0"
            final_maps.extend([f"-disposition:a:{output_audio_index}", disposition, f"-metadata:s:a:{output_audio_index}", f"title={title}"])
            
            is_first_track = False
            output_audio_index += 1
            
        return ["-filter_complex", ";".join(fc_parts)] + final_maps

    def build_ffmpeg_command_and_run(self, job, orientation):
        options = copy.deepcopy(job['options'])
        folder_name = f"{options.get('resolution', DEFAULT_RESOLUTION)}_{options.get('output_format', DEFAULT_OUTPUT_FORMAT).upper()}"
        if orientation == "hybrid (stacked)": folder_name += "_Hybrid_Stacked"
        elif orientation == "vertical": folder_name += f"_Vertical_{options.get('vertical_aspect').replace(':', 'x')}"
        elif orientation == "original": folder_name += "_Original"
        else:
            h_aspect = options.get('horizontal_aspect').replace(':', 'x')
            if h_aspect != "16x9": folder_name += f"_Horizontal_{h_aspect}"
        unique_base_name = os.path.splitext(job['display_name'])[0]
        safe_base_name = re.sub(r'[\\/*?:"<>|]', "_", unique_base_name)
        job_hash = get_job_hash(options)
        safe_base_name = f"{safe_base_name}_{job_hash}"
        tag_match = re.search(r'(\[.*\])', job['display_name'])
        tag = tag_match.group(1) if tag_match else "Subtitles"
        safe_subtitle_folder_name = re.sub(r'[\\/*?:"<>|]', "", tag).strip()
        base_dir = os.path.dirname(job['video_path']) if self.output_mode == 'local' else os.getcwd()
        output_dir = os.path.join(base_dir, folder_name, safe_subtitle_folder_name)
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f"{safe_base_name}.mp4")
        ass_burn_path, temp_extracted_srt_path = None, None
        try:
            if options.get("burn_subtitles") and job.get('subtitle_path'):
                sub_identifier = job.get('subtitle_path')
                subtitle_source_file = None
                if sub_identifier.startswith("embedded:"):
                    stream_index = int(sub_identifier.split(':')[1])
                    temp_extracted_srt_path = extract_embedded_subtitle(job['video_path'], stream_index)
                    if temp_extracted_srt_path: subtitle_source_file = temp_extracted_srt_path
                    else: print(f"[WARN] Could not extract embedded subtitle for '{job['display_name']}'.")
                elif os.path.exists(sub_identifier): subtitle_source_file = sub_identifier
                if subtitle_source_file:
                    if orientation == "hybrid (stacked)" and options.get("subtitle_alignment") == "seam":
                        res_key = options.get('resolution'); width_map = {"HD": 1080, "4k": 2160, "8k": 4320}
                        target_w = width_map.get(res_key, 1080)
                        num_top, den_top = map(int, options.get('hybrid_top_aspect').split(':')); top_h = (int(target_w * den_top / num_top) // 2) * 2
                        num_bot, den_bot = map(int, options.get('hybrid_bottom_aspect').split(':')); bot_h = (int(target_w * den_bot / num_bot) // 2) * 2
                        total_real_h = top_h + bot_h
                        if total_real_h > 0:
                            seam_y_on_canvas = int((top_h / total_real_h) * 1080)
                            options["calculated_pos"] = (960, seam_y_on_canvas)
                    ass_burn_path = create_temporary_ass_file(subtitle_source_file, options)
                    if not ass_burn_path: raise VideoProcessingError("Failed to create styled ASS file.")
            cmd = self.construct_ffmpeg_command(job, output_file, orientation, ass_burn_path, options)
            if self.run_ffmpeg_command(cmd) != 0: raise VideoProcessingError(f"Error encoding {job['video_path']}")
            print(f"File finalized => {output_file}")
            self.verify_output_file(output_file, options)
        finally:
            if ass_burn_path and os.path.exists(ass_burn_path): os.remove(ass_burn_path)
            if temp_extracted_srt_path and os.path.exists(temp_extracted_srt_path): os.remove(temp_extracted_srt_path)

    def construct_ffmpeg_command(self, job, output_file, orientation, ass_burn_path=None, options=None):
        options = options or job['options']
        file_path = job['video_path']
        info = get_video_info(file_path)
        decoder_available, _ = check_decoder_availability(info["codec_name"])
        decoder_map = {"h264": "h264_cuvid", "hevc": "hevc_cuvid", "av1": "av1_cuvid", "vp9": "vp9_cuvid"}
        decoder = decoder_map.get(info["codec_name"]) if decoder_available else info["codec_name"]
        use_cuda_decoder = "_cuvid" in decoder
        cmd = [FFMPEG_CMD, "-y", "-hide_banner"] + (["-hwaccel", "cuda", "-hwaccel_output_format", "cuda"] if use_cuda_decoder else []) + ["-c:v", decoder, "-i", file_path]
        filter_complex_parts, is_hdr_output = [], options.get("output_format") == 'hdr'
        video_out_tag = "0:v:0"
        audio_cmd_parts = self.build_audio_segment(file_path, options)
        audio_fc_str = ""
        try:
            audio_fc_index = audio_cmd_parts.index("-filter_complex")
            audio_fc_str = audio_cmd_parts.pop(audio_fc_index + 1)
            audio_cmd_parts.pop(audio_fc_index)
        except ValueError: pass
        if orientation == "hybrid (stacked)":
            res_key = options.get('resolution'); width_map = {"HD": 1080, "4k": 2160, "8k": 4320}
            target_w = width_map.get(res_key, 1080)
            def get_block_filters(aspect_str, mode, upscale_algo):
                num, den = map(int, aspect_str.split(':')); target_h = (int(target_w * den / num) // 2) * 2
                scale = f"scale_cuda=w={target_w}:h={target_h}:interp_algo={upscale_algo}"
                if mode == 'stretch': return scale, "", target_h
                vf = f"{scale}:force_original_aspect_ratio={'decrease' if mode == 'pad' else 'increase'}"
                cpu = f"pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2:black" if mode == 'pad' else f"crop={target_w}:{target_h}"
                return vf, cpu, target_h
            top_vf, top_cpu, _ = get_block_filters(options.get('hybrid_top_aspect'), options.get('hybrid_top_mode'), options.get('upscale_algo'))
            bot_vf, bot_cpu, _ = get_block_filters(options.get('hybrid_bottom_aspect'), options.get('hybrid_bottom_mode'), options.get('upscale_algo'))
            cpu_pix_fmt = "p010le" if info["bit_depth"] == 10 else "nv12"
            cpu_chain = []
            if info["is_hdr"] and not is_hdr_output and os.path.exists(options.get("lut_file")): cpu_chain.append(f"lut3d=file='{options.get('lut_file').replace(':', '\\:').replace('\\\\', '/')}'")
            if options.get("fruc"): cpu_chain.append(f"minterpolate=fps={options.get('fruc_fps')}")
            if ass_burn_path: cpu_chain.append(f"subtitles=filename='{ass_burn_path.replace('\\', '/').replace(':', '\\:')}'")
            if not is_hdr_output: cpu_chain.append("format=nv12")
            video_fc_parts = [
                "[0:v]split=2[v_top_in][v_bot_in]", f"[v_top_in]{top_vf}[v_top_out]", f"[v_bot_in]{bot_vf}[v_bot_out]",
                f"[v_top_out]hwdownload,format={cpu_pix_fmt},{top_cpu}[cpu_top]", f"[v_bot_out]hwdownload,format={cpu_pix_fmt},{bot_cpu}[cpu_bot]",
                "[cpu_top][cpu_bot]vstack=inputs=2[stacked]",
                f"[stacked]{','.join(filter(None, cpu_chain))},hwupload_cuda[v_out]" if cpu_chain else "[stacked]hwupload_cuda[v_out]"
            ]
            filter_complex_parts.extend(video_fc_parts)
            video_out_tag = "[v_out]"
        else:
            vf_filters, cpu_filters = [], []
            if orientation != "original":
                res_key, aspect_str = (options.get('resolution'), options.get('vertical_aspect')) if orientation == "vertical" else (options.get('resolution'), options.get('horizontal_aspect'))
                width_map = {"HD": 1080, "4k": 2160, "8k": 4320} if orientation == "vertical" else {"HD": 1920, "4k": 3840, "8k": 7680}
                target_w = width_map.get(res_key, 1920); num, den = map(int, aspect_str.split(':')); target_h = int(target_w * den / num)
                target_w, target_h = (target_w // 2) * 2, (target_h // 2) * 2
                scale_base = f"scale_cuda=w={target_w}:h={target_h}:interp_algo={options.get('upscale_algo')}"
                if options.get("aspect_mode") == 'pad': vf_filters.append(f"{scale_base}:force_original_aspect_ratio=decrease"); cpu_filters.append(f"pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2:black")
                elif options.get("aspect_mode") == 'crop': vf_filters.append(f"{scale_base}:force_original_aspect_ratio=increase"); cpu_filters.append(f"crop={target_w}:{target_h}")
                else: vf_filters.append(scale_base)
            if info["is_hdr"] and not is_hdr_output and os.path.exists(options.get("lut_file")): cpu_filters.append(f"lut3d=file='{options.get('lut_file').replace(':', '\\:').replace('\\\\', '/')}'")
            if options.get("fruc"): cpu_filters.append(f"minterpolate=fps={options.get('fruc_fps')}")
            if ass_burn_path: cpu_filters.append(f"subtitles=filename='{ass_burn_path.replace('\\', '/').replace(':', '\\:')}'")
            if cpu_filters:
                processing_chain = [f"hwdownload,format={'p010le' if info['bit_depth'] == 10 else 'nv12'}"] + cpu_filters
                if not is_hdr_output: processing_chain.append("format=nv12")
                vf_filters.append(f"{','.join(processing_chain)},hwupload_cuda")
            if vf_filters:
                filter_complex_parts.append(f"[0:v]{','.join(vf_filters)}[v_out]")
                video_out_tag = "[v_out]"
        if filter_complex_parts or audio_fc_str:
            full_fc = ";".join(filter(None, filter_complex_parts + ([audio_fc_str] if audio_fc_str else [])))
            cmd.extend(["-filter_complex", full_fc])
        cmd.extend(["-map", video_out_tag])
        cmd.extend(audio_cmd_parts)
        bitrate_kbps = int(options.get("manual_bitrate")) if options.get("override_bitrate") else get_bitrate(options.get('resolution'), info["framerate"], is_hdr_output)
        gop_len = math.ceil(info["framerate"] / 2) if info["framerate"] > 0 else 30
        encoder_opts = ["-c:v", "hevc_nvenc", "-preset", "p1", "-profile:v", "main10", "-b:v", f"{bitrate_kbps}k", "-g", str(gop_len), "-color_primaries", "bt2020", "-color_trc", "smpte2084", "-colorspace", "bt2020nc"] if is_hdr_output else ["-c:v", "h264_nvenc", "-preset", "p1", "-profile:v", "high", "-b:v", f"{bitrate_kbps}k", "-g", str(gop_len), "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709"]
        cmd.extend(encoder_opts)
        cmd.extend(["-f", "mp4", output_file])
        return cmd

    def validate_processing_settings(self):
        issues = []
        if self.output_format_var.get() == 'sdr' and not os.path.exists(self.lut_file_var.get()):
            issues.append(f"LUT file not found for HDR->SDR conversion: {self.lut_file_var.get()}")
        try:
            if not -70 <= float(self.loudness_target_var.get()) <= 0:
                issues.append("Loudness target must be between -70 and 0 LUFS.")
        except ValueError:
            issues.append("Invalid loudness target. Must be a number.")
        
        if self.audio_stereo_sofalizer_var.get() and not self.audio_passthrough_var.get():
            sofa_path = self.sofa_file_var.get()
            if not sofa_path:
                issues.append("Sofalizer audio is enabled, but no SOFA file has been selected.")
            elif not os.path.exists(sofa_path):
                issues.append(f"The selected SOFA file does not exist: {sofa_path}")
        
        if not self.audio_passthrough_var.get():
            any_proc_selected = any([self.audio_mono_var.get(), self.audio_stereo_downmix_var.get(),
                                     self.audio_stereo_sofalizer_var.get(), self.audio_surround_51_var.get()])
            if not any_proc_selected:
                issues.append("No audio processing tracks are selected. Choose at least one or select Passthrough.")

        if issues:
            messagebox.showerror("Configuration Issues", "Please fix the following issues:\n" + "\n".join(f"• {issue}" for issue in issues))
            return False
        return True

    def start_processing(self):
        if not self.processing_jobs: messagebox.showwarning("No Jobs", "Please add files to the queue."); return
        if not self.validate_processing_settings(): return
        self.output_mode = self.output_mode_var.get()
        print("\n" + "="*80 + "\n--- Starting processing batch ---")
        successful, failed = 0, 0
        total_jobs = len(self.processing_jobs)
        for i, job in enumerate(self.processing_jobs):
            self.update_status(f"Processing {i + 1}/{total_jobs}: {job['display_name']}")
            print("\n" + "-"*80 + f"\nStarting job {i + 1}/{total_jobs}: {job['display_name']}\n" + "-"*80)
            try:
                orientation = job['options'].get("orientation", "horizontal")
                if orientation == "horizontal + vertical":
                    self.build_ffmpeg_command_and_run(job, "horizontal")
                    self.build_ffmpeg_command_and_run(job, "vertical")
                else:
                    self.build_ffmpeg_command_and_run(job, orientation)
                successful += 1; print(f"[SUCCESS] Job '{job['display_name']}' completed successfully.")
            except (VideoProcessingError, Exception) as e:
                failed += 1; print(f"\n[ERROR] Job failed for '{job['display_name']}': {e}")
        final_message = f"Processing Complete: {successful} successful, {failed} failed"
        print("\n" + "="*80 + "\n" + final_message); self.update_status(final_message)

    def run_ffmpeg_command(self, cmd):
        print("Running FFmpeg command:")
        print(" ".join(f'"{c}"' if " " in c else c for c in cmd))
        return safe_ffmpeg_execution(cmd, "video encoding")

    def verify_output_file(self, file_path, options=None):
        print(f"--- Verifying output: {os.path.basename(file_path)} ---")
        try:
            cmd = [FFPROBE_CMD, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,codec_name", "-of", "json", file_path]
            video_info = json.loads(safe_ffprobe(cmd, "output video verification").stdout)["streams"][0]
            print(f"[VIDEO VER] {video_info.get('width')}x{video_info.get('height')} using {video_info.get('codec_name')}")
            cmd_audio = [FFPROBE_CMD, "-v", "error", "-select_streams", "a", "-show_entries", "stream=index,channels,channel_layout,codec_name:stream_tags=title", "-of", "json", file_path]
            audio_info = json.loads(safe_ffprobe(cmd_audio, "output audio verification").stdout).get("streams", [])
            for s in audio_info:
                title = s.get('tags', {}).get('title', 'N/A')
                print(f"[AUDIO VER] Stream #{s.get('index')}: '{title}' ({s.get('codec_name')}, {s.get('channels')} channels, '{s.get('channel_layout')}')")
        except Exception as e: print(f"[ERROR] Verification failed: {e}")

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

    def clear_file_selection(self): self.job_listbox.select_clear(0, tk.END); self.on_input_file_select(None)

    def select_all_no_sub(self):
        self.job_listbox.selection_clear(0, tk.END)
        for i, job in enumerate(self.processing_jobs):
            if job.get('subtitle_path') is None: self.job_listbox.selection_set(i)
        self.on_input_file_select(None)

    def select_all_subbed(self):
        self.job_listbox.selection_clear(0, tk.END)
        for i, job in enumerate(self.processing_jobs):
            if job.get('subtitle_path') is not None: self.job_listbox.selection_set(i)
        self.on_input_file_select(None)

    def invert_selection(self):
        selected_indices = self.job_listbox.curselection()
        for i in range(self.job_listbox.size()):
            if i in selected_indices: self.job_listbox.selection_clear(i)
            else: self.job_listbox.selection_set(i)
        self.on_input_file_select(None)

    def toggle_fruc_fps(self): self.fruc_fps_entry.config(state="normal" if self.fruc_var.get() else "disabled")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YouTube Batch Video Processing Tool", formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-o', '--output-mode', dest='output_mode', choices=['local', 'pooled'], default='local', help="Set initial output directory mode.")
    parser.add_argument('input_files', nargs='*', help="Optional: Paths to video files or glob patterns.")
    parser.add_argument('-d', '--debug', action='store_true', help="Enable debug mode.")
    args = parser.parse_args()
    DEBUG_MODE = args.debug
    if not check_cuda_availability():
        messagebox.showerror("CUDA Not Available", "CUDA hardware acceleration is not available or not detected in FFmpeg. The application requires CUDA to run.\nPlease ensure your NVIDIA drivers are installed and you have a compatible FFmpeg build.")
        sys.exit(1)
    capabilities = check_ffmpeg_capabilities()
    if not capabilities['nvenc']:
        messagebox.showwarning("NVENC Not Available", "NVENC encoders not found in FFmpeg. Video encoding may fail.\nContinuing anyway...")
    root = TkinterDnD.Tk()
    initial_files = []
    if args.input_files:
        for pattern in args.input_files: initial_files.extend(glob.glob(pattern))
    else: # Auto-discover files in cwd if none are provided
        for filename in os.listdir(os.getcwd()):
            if os.path.splitext(filename)[1].lower() in ['.mp4', '.mkv', '.mov', '.avi', '.webm']:
                initial_files.append(os.path.join(os.getcwd(), filename))
    app = VideoProcessorApp(root, sorted(list(set(initial_files))), args.output_mode)
    root.mainloop()
