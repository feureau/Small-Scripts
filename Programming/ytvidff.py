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

-------------------------------------------------------------------------------
Audio Processing Modes
-------------------------------------------------------------------------------

The script supports two primary audio output modes, configurable through the
GUI via a radio switch. These modes control how audio streams are generated
and encoded for each video output.

1. Stereo + 5.1 Mode (Default)
   ----------------------------
   Produces two separate audio tracks in the final container:
       - Track 1: Stereo mix (2 channels)
       - Track 2: Surround mix (5.1, 6 channels)

   Behavior:
       • If the input file contains only stereo:
             → A stereo track is copied/processed and a 5.1 track is
               upmixed using a pan-based formula.
       • If the input file contains only 5.1:
             → A stereo track is created via downmix and the original 5.1
               layout is preserved.
       • If the input file contains both stereo and 5.1:
             → Both are re-encoded and normalized to meet spec.

   Encoding details:
       - Codec:         AAC-LC (FFmpeg internal encoder)
       - Sample rate:   48 kHz (enforced)
       - Bitrates:      Stereo → 384 kbps, 5.1 → 512 kbps
       - Channel order: SMPTE standard L R C LFE Ls Rs
       - Loudness normalization (optional): EBU R128 `loudnorm`
         filter applied to both tracks if enabled.

   FFmpeg behavior:
       • Stereo and 5.1 tracks are generated via `filter_complex`.
       • Stereo downmix applies center and surround weighting.
       • 5.1 upmix distributes stereo signal across six channels with
         center and surround coefficients.
       • Resulting labeled outputs are mapped and encoded per track.

   Result:
       A YouTube-compliant MP4 file containing two audio streams.
       YouTube may choose to playback stereo or 5.1 depending on device
       and viewer capabilities, but the file remains spec-compliant.

2. Passthrough Mode
   ----------------
   This mode disables remixing and encoding enforcement. All audio streams
   are passed through unchanged unless normalization is requested.

   Behavior:
       • If normalization is disabled:
             → Audio streams are copied as-is using `-c:a copy`.
       • If normalization is enabled:
             → Each input audio stream is normalized individually and
               re-encoded to AAC-LC at 192 kbps, 48 kHz, preserving
               original channel count and layout.

-------------------------------------------------------------------------------
YouTube Audio Compliance
-------------------------------------------------------------------------------

The following technical parameters are enforced to ensure YouTube compatibility
for stereo and surround audio uploads.

    Audio Codec:     AAC-LC (Low Complexity)
    Container:       MP4 or MOV
    Sample Rate:     48,000 Hz (mandatory for 5.1)
    Channel Layout:  5.1 → L, R, C, LFE, Ls, Rs
    Bitrates:        Stereo → 384 kbps, 5.1 → 512 kbps
    Normalization:   EBU R128 loudnorm (optional)
    Playback:        Device-dependent; YouTube selects stereo or 5.1 based
                     on client capabilities.

Additional Notes:
    - Some desktop browsers and mobile devices only play stereo even when a
      5.1 track exists.
    - YouTube internally re-encodes uploads, so exact bitrates are preserved
      for compliance, not final playback quality.
    - Maintaining correct channel order (SMPTE layout) avoids channel mapping
      errors or YouTube defaulting to stereo.

-------------------------------------------------------------------------------
Implementation Details
-------------------------------------------------------------------------------

Core Components:
    • build_audio_segment(file_path, options)
        - Generates FFmpeg command arguments for all audio operations.
        - Dynamically creates filter graphs, downmixes, or upmixes.
        - Handles normalization logic per track or per mode.
        - Applies correct codec, bitrate, and sample rate flags.

    • verify_output_file(output_path)
        - After encoding, runs ffprobe to verify:
            - Channel count matches expected (2 and 6 for Stereo + 5.1)
            - Channel layout is correct (5.1(side))
            - Sample rate is 48,000 Hz
        - Logs warnings if results deviate from spec.

    • GUI Integration (Tkinter)
        - Provides batch queueing and encoding control.
        - Radio switch for "Stereo + 5.1" or "Passthrough".
        - Checkboxes for normalization and logging.
        - Options are serialized per-file in the encoding queue.

Constants (defined near top of file):
    YT_AUDIO_SAMPLE_RATE = 48000
    YT_STEREO_BITRATE    = 384000
    YT_5_1_BITRATE       = 512000

-------------------------------------------------------------------------------
Developer Notes
-------------------------------------------------------------------------------
- FFmpeg is expected to be in the system PATH. If not, update the variable
  FF_PATH or adjust the system environment accordingly.
- Logs and ffprobe outputs are used for debugging and quality assurance.
- The script automatically detects and handles inputs with:
      • No audio
      • Stereo-only audio
      • 5.1-only audio
      • Mixed stereo and 5.1 audio tracks
- Loudnorm targets can be adjusted globally:
      DEFAULT_LOUDNESS_TARGET = -14
      DEFAULT_LOUDNESS_RANGE  = 7
      DEFAULT_TRUE_PEAK       = -1.0

-------------------------------------------------------------------------------
Version History
-------------------------------------------------------------------------------

v2.5 - Enhanced File Management (2025-10-25)
    • Reintroduced multiple jobs per video file (no sub + each subtitle)
    • Added horizontal scrollbar to input file listbox
    • Reintroduced duplicate selected files button
    • Fixed long filename display issues

v2.4 - Simplified Single Output System (2025-10-25)
    • Removed complex output configuration system
    • Simplified job management - one job per video file
    • Fixed file selection highlighting in listbox
    • Fixed subtitle dropdown functionality
    • Streamlined GUI to 3 columns for better usability

v2.3 - Multi-Output Configuration System (2025-10-24)
    • Implemented four-column layout for better organization
    • Added multiple output configurations per input file
    • Separated Video Settings and Audio/Subtitle settings into dedicated columns
    • Enhanced output configuration management with add/remove/duplicate/reorder
    • Maintained backward compatibility with auto-migration from single to multi-output

v2.2 - Enhanced Subtitle Management (2025-10-24)
    • Added per-job subtitle file management with dropdown selector
    • Implemented Browse and Remove subtitle functionality
    • Maintained auto-discovery as default behavior
    • Added support for custom subtitle file additions
    • Enhanced multiple job selection support for subtitle operations

v2.1 - Full YouTube Audio Compliance Update (2025-10-24)
    • Added detailed developer documentation covering YouTube audio standards.
    • Introduced `build_audio_segment()` helper for modular audio handling.
    • Enforced official YouTube encoding parameters:
        - Codec: AAC-LC
        - Sample rate: 48 kHz
        - Channel layout: L R C LFE Ls Rs
        - Bitrates: Stereo 384 kbps, 5.1 512 kbps
    • Implemented "Stereo + 5.1" (default) and "Passthrough" audio modes.
    • Added loudness normalization to both stereo and 5.1 outputs (EBU R128).
    • Updated GUI with new radio switch for audio mode selection.
    • Integrated post-encode `ffprobe` verification for channels and layout.
    • Improved filter_complex ordering and per-stream mapping stability.
    • Added fallback logic for input files with no audio or malformed metadata.
    • Enhanced logging for better debugging and compliance confirmation.

v2.0 - YouTube Compliance Edition (2025-10-22)
    • Refactored audio handling to allow multi-track output.
    • Initial support for Stereo + 5.1 track generation.
    • Integrated EBU R128 loudness normalization filter.
    • Standardized AAC-LC encoding defaults.
    • Added GUI elements for normalization and logging.
    • Improved error handling for missing or invalid audio streams.

v1.9 - FFmpeg Queue Optimizations (2025-09)
    • Optimized multiprocessing job handling for faster queue throughput.
    • Reduced redundant FFprobe calls per job.
    • Improved temporary file cleanup and naming logic.
    • Added progress callbacks for GUI thread-safe updates.

v1.8 - Loudness Normalization + GUI Integration (2025-08)
    • Added loudness normalization settings (LUFS, LRA, True Peak).
    • GUI now includes adjustable normalization parameters.
    • Normalization integrated into FFmpeg command builder.
    • Introduced loudnorm filter with multi-pass analysis option.

v1.7 - FFprobe Metadata Handling (2025-07)
    • Added audio stream info parser (`get_audio_stream_info`).
    • Improved reliability of channel detection (2ch vs 6ch).
    • Enhanced error handling when FFprobe metadata is missing.
    • Implemented fallback for legacy AAC mono streams.

v1.6 - Queue Persistence and Logging (2025-06)
    • Added persistent queue state with JSON serialization.
    • Introduced job-level logging output.
    • Improved user feedback and log file naming consistency.

v1.5 - GUI Performance + Error Handling (2025-05)
    • Optimized Tkinter event loop for smoother responsiveness.
    • Added error dialog display for FFmpeg and IO issues.
    • Reduced blocking calls during queue operations.

v1.4 - Batch Encoding Framework (2025-04)
    • Introduced batch queue for multi-file encoding.
    • Added per-file progress display and status updates.
    • Integrated thread-safe job cancellation logic.

v1.3 - GUI Refactor (2025-03)
    • Improved layout, theming, and input validation.
    • Reorganized advanced settings sections.
    • Added per-job option persistence.

v1.2 - Initial Audio Normalization Support (2025-02)
    • Added EBU R128 loudnorm basic filter integration.
    • Introduced default normalization parameters.

v1.1 - Core Video Encoding Pipeline (2025-01)
    • Established main FFmpeg command generation.
    • Added codec, resolution, and CRF configuration.
    • Implemented progress parsing via FFmpeg stdout.

v1.0 - Initial Release (2024-12)
    • Basic GUI for file selection and single-file encoding.
    • Direct FFmpeg command construction for video output.
    • Initial logging and status message framework.
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

# -------------------------- Configuration / Constants --------------------------
# If you have a custom ffmpeg binary, set environment variable FFMPEG_PATH to its path.
FFMPEG_CMD = os.environ.get("FFMPEG_PATH", "ffmpeg")
FFPROBE_CMD = os.environ.get("FFPROBE_PATH", "ffprobe")

# YouTube-audio recommended parameters (consolidated)
AUDIO_SAMPLE_RATE = 48000                 # 48 kHz recommended for 5.1
STEREO_BITRATE_K = 384                    # stereo ~384 kbps
SURROUND_BITRATE_K = 512                  # 5.1 ~512 kbps
PASSTHROUGH_NORMALIZE_BITRATE_K = 192     # per-track bitrate when normalizing in passthrough mode

# LUT configuration
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
DEFAULT_AUDIO_MODE = "stereo+5.1"  # "stereo+5.1" or "passthrough"

# --- Subtitle defaults ---
DEFAULT_SUBTITLE_FONT = "Impact"
DEFAULT_SUBTITLE_FONT_SIZE = "64"
DEFAULT_SUBTITLE_ALIGNMENT = "bottom"
DEFAULT_SUBTITLE_BOLD = True
DEFAULT_SUBTITLE_ITALIC = False
DEFAULT_SUBTITLE_PRIMARY_COLOR = "#FFAA00"
DEFAULT_SUBTITLE_OUTLINE_COLOR = "#000000"
DEFAULT_SUBTITLE_SHADOW_COLOR = "#202020"
DEFAULT_SUBTITLE_MARGIN_V = "65"

# Debug mode flag
DEBUG_MODE = False

def debug_print(*args, **kwargs):
    if DEBUG_MODE:
        print("[DEBUG]", *args, **kwargs)

# ----------------------------------------------------------------------------------------------------
env = os.environ.copy()
env["PYTHONIOENCODING"] = "utf-8"

# Custom exception for video processing errors
class VideoProcessingError(Exception):
    """Custom exception for video processing errors"""
    pass

def check_cuda_availability():
    """Check if CUDA is available in FFmpeg"""
    try:
        cmd = [FFMPEG_CMD, "-hwaccels"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if "cuda" in result.stdout.lower():
            return True
        else:
            print("[ERROR] CUDA not available in FFmpeg. Available hardware accelerations:")
            print(result.stdout)
            return False
    except subprocess.TimeoutExpired:
        print("[ERROR] FFmpeg timeout while checking CUDA availability")
        return False
    except FileNotFoundError:
        print(f"[ERROR] FFmpeg not found at: {FFMPEG_CMD}")
        return False
    except Exception as e:
        print(f"[ERROR] Failed to check CUDA availability: {e}")
        return False

def check_ffmpeg_capabilities():
    """Check if required FFmpeg features are available"""
    capabilities = {
        'cuda': False,
        'nvenc': False,
        'filters': False
    }
    
    try:
        # Check CUDA
        cmd = [FFMPEG_CMD, "-hwaccels"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        capabilities['cuda'] = "cuda" in result.stdout.lower()
        
        # Check NVENC encoders
        cmd = [FFMPEG_CMD, "-encoders"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        capabilities['nvenc'] = any(x in result.stdout.lower() for x in ['h264_nvenc', 'hevc_nvenc'])
        
        # Check filters
        cmd = [FFMPEG_CMD, "-filters"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        capabilities['filters'] = all(x in result.stdout.lower() for x in ['loudnorm', 'scale_cuda', 'lut3d'])
        
        return capabilities
    except Exception as e:
        print(f"[ERROR] Failed to check FFmpeg capabilities: {e}")
        return capabilities

def check_decoder_availability(codec_name):
    """Check if a specific decoder is available"""
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
    """Safe wrapper for ffprobe commands with error handling"""
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
    """Safe wrapper for FFmpeg execution"""
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
            error_output = "".join(output_lines[-10:])  # Last 10 lines for context
            raise VideoProcessingError(f"FFmpeg {operation} failed with return code {return_code}\nLast output:\n{error_output}")
        
        return return_code
        
    except FileNotFoundError:
        raise VideoProcessingError("FFmpeg not found. Please ensure FFmpeg is installed and in PATH")
    except Exception as e:
        raise VideoProcessingError(f"Unexpected error during {operation}: {e}")

def safe_file_operations(operation, file_path, fallback_path=None):
    """Safe file operations with error handling and cleanup"""
    try:
        return operation(file_path, fallback_path)
    except PermissionError as e:
        raise VideoProcessingError(f"Permission denied: {file_path} - {e}")
    except OSError as e:
        raise VideoProcessingError(f"File system error: {file_path} - {e}")
    except Exception as e:
        raise VideoProcessingError(f"File operation failed: {file_path} - {e}")

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
Style: {style_name},{font_name},{font_size},{primary_color},&H000000FF,{outline_color},{shadow_color},{bold_flag},{italic_flag},0,0,100,100,0,0,1,2,2,{alignment},10,10,{margin_v},1

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
        
        # More accurate codec detection
        codec_name = data.get("codec_name", "h264")
        codec_tag = data.get("codec_tag_string", "").lower()
        
        # Handle AV1 detection
        if codec_tag == "av01" or "av1" in codec_name.lower():
            codec_name = "av1"
        
        return {"bit_depth": bit_depth, "framerate": framerate, "height": height, "width": width, "is_hdr": is_hdr, "codec_name": codec_name}
    except VideoProcessingError as e:
        print(f"[WARN] Could not get video info for {file_path}: {e}")
        return {"bit_depth": 8, "framerate": 30.0, "height": 1080, "width": 1920, "is_hdr": False, "codec_name": "h264"}
    except Exception as e:
        print(f"[WARN] Could not get video info for {file_path}, using defaults: {e}")
        return {"bit_depth": 8, "framerate": 30.0, "height": 1080, "width": 1920, "is_hdr": False, "codec_name": "h264"}

def get_audio_stream_info(file_path):
    cmd = [FFPROBE_CMD, "-v", "error", "-select_streams", "a", "-show_entries", "stream=index,channels", "-of", "json", file_path]
    try:
        result = safe_ffprobe(cmd, "audio stream info extraction")
        streams = json.loads(result.stdout).get("streams", [])
        return [{"channels": s.get("channels", 2)} for s in streams]
    except VideoProcessingError as e:
        print(f"[WARN] Could not get detailed audio stream info for {file_path}: {e}")
        return []
    except Exception as e:
        print(f"[WARN] Could not get detailed audio stream info for {file_path}: {e}")
        return []

def get_bitrate(output_resolution_key, framerate, is_hdr):
    BITRATES = {
        "SDR_NORMAL_FPS": { "HD": 16000, "4k": 90000, "8k": 320000 },
        "SDR_HIGH_FPS":   { "HD": 24000, "4k": 136000, "8k": 480000 },
        "HDR_NORMAL_FPS": { "HD": 20000, "4k": 112000, "8k": 400000 },
        "HDR_HIGH_FPS":   { "HD": 30000, "4k": 170000, "8k": 600000 }
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
        
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                        background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                        font=("Arial", 10))
        label.pack()
    
    def leave(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None

class VideoProcessorApp:
    def __init__(self, root, initial_files, output_mode):
        debug_print("VideoProcessorApp __init__ started")
        self.root = root; self.root.title("Video Processing Tool")
        self.output_mode = output_mode
        self.processing_jobs = []

        # Initialize GUI variables
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
        
        self.subtitle_font_var = tk.StringVar(value=DEFAULT_SUBTITLE_FONT)
        self.subtitle_font_size_var = tk.StringVar(value=DEFAULT_SUBTITLE_FONT_SIZE)
        self.subtitle_alignment_var = tk.StringVar(value=DEFAULT_SUBTITLE_ALIGNMENT)
        self.subtitle_bold_var = tk.BooleanVar(value=DEFAULT_SUBTITLE_BOLD)
        self.subtitle_italic_var = tk.BooleanVar(value=DEFAULT_SUBTITLE_ITALIC)
        self.subtitle_primary_color_var = tk.StringVar(value=DEFAULT_SUBTITLE_PRIMARY_COLOR)
        self.subtitle_outline_color_var = tk.StringVar(value=DEFAULT_SUBTITLE_OUTLINE_COLOR)
        self.subtitle_shadow_color_var = tk.StringVar(value=DEFAULT_SUBTITLE_SHADOW_COLOR)
        self.subtitle_margin_v_var = tk.StringVar(value=DEFAULT_SUBTITLE_MARGIN_V)

        # LUT configuration
        self.lut_file_var = tk.StringVar(value=DEFAULT_LUT_PATH)

        # Status bar
        self.status_var = tk.StringVar(value="Ready")

        self.root.drop_target_register(DND_FILES); self.root.dnd_bind("<<Drop>>", self.handle_file_drop)
        
        self.setup_gui()
        debug_print("GUI setup completed")
        
        # Only call this once - remove any other calls to this method
        if initial_files:
            self.add_video_files_and_discover_jobs(initial_files)
        
        debug_print("Initial file loading completed")
        debug_print(f"Total processing jobs: {len(self.processing_jobs)}")

    def setup_gui(self):
        # Configure main window grid - now 3 columns
        self.root.columnconfigure(0, weight=1, minsize=250)  # Input Files
        self.root.columnconfigure(1, weight=2, minsize=400)  # Video Settings
        self.root.columnconfigure(2, weight=2, minsize=400)  # Audio & Subtitles
        
        # Create main frames for each column
        input_frame = tk.Frame(self.root); input_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        video_frame = tk.Frame(self.root); video_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        audio_frame = tk.Frame(self.root); audio_frame.grid(row=0, column=2, sticky="nsew", padx=5, pady=5)
        
        # Bottom buttons frame (spans all columns)
        button_frame = tk.Frame(self.root); button_frame.grid(row=1, column=0, columnspan=3, sticky="ew", padx=10, pady=10)
        
        # Status bar at bottom
        status_bar = tk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.grid(row=2, column=0, columnspan=3, sticky="ew", padx=5, pady=2)
        
        # Setup each column
        self.setup_input_column(input_frame)
        self.setup_video_column(video_frame)
        self.setup_audio_column(audio_frame)
        self.setup_button_row(button_frame)
        
        # Initialize state
        self._toggle_orientation_options()
        self._toggle_upscale_options()
        self._toggle_audio_norm_options()
        self._update_bitrate_display()

    def setup_input_column(self, parent):
        """Column 1: Input Files"""
        file_group = tk.LabelFrame(parent, text="Input Files", padx=10, pady=10)
        file_group.pack(fill=tk.BOTH, expand=True)
        
        # Create frame for listbox with both scrollbars
        listbox_container = tk.Frame(file_group)
        listbox_container.pack(fill=tk.BOTH, expand=True)
        
        # Vertical scrollbar
        self.job_scrollbar_v = tk.Scrollbar(listbox_container, orient=tk.VERTICAL)
        self.job_scrollbar_v.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Horizontal scrollbar
        self.job_scrollbar_h = tk.Scrollbar(listbox_container, orient=tk.HORIZONTAL)
        self.job_scrollbar_h.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Listbox with both scrollbars
        self.job_listbox = tk.Listbox(
            listbox_container, 
            selectmode=tk.EXTENDED, 
            exportselection=False,
            yscrollcommand=self.job_scrollbar_v.set,
            xscrollcommand=self.job_scrollbar_h.set
        )
        self.job_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Configure scrollbars
        self.job_scrollbar_v.config(command=self.job_listbox.yview)
        self.job_scrollbar_h.config(command=self.job_listbox.xview)
        
        self.job_listbox.bind("<<ListboxSelect>>", self.on_input_file_select)
        
        selection_buttons_frame = tk.Frame(file_group)
        selection_buttons_frame.pack(fill=tk.X, pady=(5, 0))
        tk.Button(selection_buttons_frame, text="Select All", command=self.select_all_files).pack(side=tk.LEFT)
        tk.Button(selection_buttons_frame, text="Clear Selection", command=self.clear_file_selection).pack(side=tk.LEFT, padx=5)

        file_buttons_frame = tk.Frame(file_group)
        file_buttons_frame.pack(fill=tk.X, pady=(5, 0))
        tk.Button(file_buttons_frame, text="Add Files...", command=self.add_files).pack(side=tk.LEFT, padx=(0,5))
        tk.Button(file_buttons_frame, text="Remove Selected", command=self.remove_selected).pack(side=tk.LEFT, padx=5)
        tk.Button(file_buttons_frame, text="Duplicate Selected", command=self.duplicate_selected_jobs).pack(side=tk.LEFT, padx=5)
        tk.Button(file_buttons_frame, text="Clear All", command=self.clear_all).pack(side=tk.LEFT, padx=5)

    def setup_video_column(self, parent):
        """Column 2: Video Settings"""
        # Output & Geometry
        geometry_group = tk.LabelFrame(parent, text="Output & Geometry", padx=10, pady=10)
        geometry_group.pack(fill=tk.X, pady=(0, 5))
        
        orientation_frame = tk.Frame(geometry_group)
        orientation_frame.pack(fill=tk.X)
        tk.Label(orientation_frame, text="Orientation:").pack(side=tk.LEFT, padx=(0,5))
        tk.Radiobutton(orientation_frame, text="Horizontal", variable=self.orientation_var, value="horizontal", command=self._toggle_orientation_options).pack(side=tk.LEFT)
        tk.Radiobutton(orientation_frame, text="Vertical", variable=self.orientation_var, value="vertical", command=self._toggle_orientation_options).pack(side=tk.LEFT)
        tk.Radiobutton(orientation_frame, text="Both", variable=self.orientation_var, value="horizontal + vertical", command=self._toggle_orientation_options).pack(side=tk.LEFT)
        tk.Radiobutton(orientation_frame, text="Original", variable=self.orientation_var, value="original", command=self._toggle_orientation_options).pack(side=tk.LEFT)

        self.aspect_ratio_frame = tk.LabelFrame(geometry_group, text="Aspect Ratio", padx=10, pady=5)
        self.aspect_ratio_frame.pack(fill=tk.X, pady=5)
        
        self.horizontal_rb_frame = tk.Frame(self.aspect_ratio_frame)
        tk.Radiobutton(self.horizontal_rb_frame, text="16:9 (Widescreen)", variable=self.horizontal_aspect_var, value="16:9", command=self.apply_gui_options_to_selected_jobs).pack(anchor="w")
        tk.Radiobutton(self.horizontal_rb_frame, text="5:4", variable=self.horizontal_aspect_var, value="5:4", command=self.apply_gui_options_to_selected_jobs).pack(anchor="w")
        tk.Radiobutton(self.horizontal_rb_frame, text="4:3 (Classic TV)", variable=self.horizontal_aspect_var, value="4:3", command=self.apply_gui_options_to_selected_jobs).pack(anchor="w")
        
        self.vertical_rb_frame = tk.Frame(self.aspect_ratio_frame)
        tk.Radiobutton(self.vertical_rb_frame, text="9:16 (Shorts/Reels)", variable=self.vertical_aspect_var, value="9:16", command=self.apply_gui_options_to_selected_jobs).pack(anchor="w")
        tk.Radiobutton(self.vertical_rb_frame, text="4:5 (Instagram Post)", variable=self.vertical_aspect_var, value="4:5", command=self.apply_gui_options_to_selected_jobs).pack(anchor="w")
        tk.Radiobutton(self.vertical_rb_frame, text="3:4 (Social Post)", variable=self.vertical_aspect_var, value="3:4", command=self.apply_gui_options_to_selected_jobs).pack(anchor="w")

        aspect_handling_frame = tk.Frame(geometry_group)
        aspect_handling_frame.pack(fill=tk.X)
        tk.Label(aspect_handling_frame, text="Handling:").pack(side=tk.LEFT, padx=(0,5))
        self.rb_crop = tk.Radiobutton(aspect_handling_frame, text="Crop (Fill)", variable=self.aspect_mode_var, value="crop", command=self._toggle_upscale_options)
        self.rb_crop.pack(side=tk.LEFT)
        self.rb_pad = tk.Radiobutton(aspect_handling_frame, text="Pad (Fit)", variable=self.aspect_mode_var, value="pad", command=self._toggle_upscale_options)
        self.rb_pad.pack(side=tk.LEFT)
        self.rb_stretch = tk.Radiobutton(aspect_handling_frame, text="Stretch", variable=self.aspect_mode_var, value="stretch", command=self._toggle_upscale_options)
        self.rb_stretch.pack(side=tk.LEFT)

        # Format & Quality
        quality_group = tk.LabelFrame(parent, text="Format & Quality", padx=10, pady=10)
        quality_group.pack(fill=tk.X, pady=(0, 5))
        
        resolution_options_frame = tk.Frame(quality_group)
        resolution_options_frame.pack(fill=tk.X)
        tk.Label(resolution_options_frame, text="Resolution:").pack(side=tk.LEFT, padx=(0,5))
        self.rb_hd = tk.Radiobutton(resolution_options_frame, text="HD", variable=self.resolution_var, value="HD", command=self.apply_gui_options_to_selected_jobs)
        self.rb_hd.pack(side=tk.LEFT)
        self.rb_4k = tk.Radiobutton(resolution_options_frame, text="4k", variable=self.resolution_var, value="4k", command=self.apply_gui_options_to_selected_jobs)
        self.rb_4k.pack(side=tk.LEFT)
        self.rb_8k = tk.Radiobutton(resolution_options_frame, text="8k", variable=self.resolution_var, value="8k", command=self.apply_gui_options_to_selected_jobs)
        self.rb_8k.pack(side=tk.LEFT)
        
        # Add tooltips for resolution
        ToolTip(self.rb_hd, "HD: 1920x1080 resolution")
        ToolTip(self.rb_4k, "4K: 3840x2160 resolution")
        ToolTip(self.rb_8k, "8K: 7680x4320 resolution")
        
        upscale_frame = tk.Frame(quality_group)
        upscale_frame.pack(fill=tk.X, pady=(5,0))
        tk.Label(upscale_frame, text="Upscale Algo:").pack(side=tk.LEFT, padx=(0,5))
        self.rb_lanczos = tk.Radiobutton(upscale_frame, text="Lanczos (Sharp)", variable=self.upscale_algo_var, value="lanczos", command=self.apply_gui_options_to_selected_jobs)
        self.rb_lanczos.pack(side=tk.LEFT)
        self.rb_bicubic = tk.Radiobutton(upscale_frame, text="Bicubic (Balanced)", variable=self.upscale_algo_var, value="bicubic", command=self.apply_gui_options_to_selected_jobs)
        self.rb_bicubic.pack(side=tk.LEFT)
        self.rb_bilinear = tk.Radiobutton(upscale_frame, text="Bilinear (Fast)", variable=self.upscale_algo_var, value="bilinear", command=self.apply_gui_options_to_selected_jobs)
        self.rb_bilinear.pack(side=tk.LEFT)

        output_format_frame = tk.Frame(quality_group)
        output_format_frame.pack(fill=tk.X, pady=(5,0))
        tk.Label(output_format_frame, text="Output Format:").pack(side=tk.LEFT, padx=(0,5))
        tk.Radiobutton(output_format_frame, text="SDR", variable=self.output_format_var, value="sdr", command=self.apply_gui_options_to_selected_jobs).pack(side=tk.LEFT)
        tk.Radiobutton(output_format_frame, text="HDR", variable=self.output_format_var, value="hdr", command=self.apply_gui_options_to_selected_jobs).pack(side=tk.LEFT)
        tk.Label(output_format_frame, text="Location:").pack(side=tk.LEFT, padx=(15,5))
        tk.Radiobutton(output_format_frame, text="Local", variable=self.output_mode_var, value="local").pack(side=tk.LEFT)
        tk.Radiobutton(output_format_frame, text="Pooled", variable=self.output_mode_var, value="pooled").pack(side=tk.LEFT)

        # LUT Configuration
        lut_frame = tk.Frame(quality_group)
        lut_frame.pack(fill=tk.X, pady=(5,0))
        tk.Label(lut_frame, text="LUT Path:").pack(side=tk.LEFT, padx=(0,5))
        self.lut_entry = tk.Entry(lut_frame, textvariable=self.lut_file_var, width=30)
        self.lut_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.lut_entry.bind("<FocusOut>", self.apply_gui_options_to_selected_jobs_event)
        tk.Button(lut_frame, text="Browse", command=self.browse_lut_file).pack(side=tk.LEFT)
        ToolTip(self.lut_entry, "Path to LUT file for HDR to SDR conversion")

        # Bitrate & FRUC
        bitrate_frame = tk.Frame(quality_group)
        bitrate_frame.pack(fill=tk.X, pady=(5,0))
        tk.Checkbutton(bitrate_frame, text="Override Bitrate", variable=self.override_bitrate_var, command=self._toggle_bitrate_override).pack(side=tk.LEFT)
        self.manual_bitrate_entry = tk.Entry(bitrate_frame, textvariable=self.manual_bitrate_var, width=10, state="disabled")
        self.manual_bitrate_entry.pack(side=tk.LEFT, padx=5)
        self.manual_bitrate_entry.bind("<FocusOut>", self.apply_gui_options_to_selected_jobs_event)
        tk.Label(bitrate_frame, text="kbps").pack(side=tk.LEFT)
        
        fruc_frame = tk.Frame(quality_group)
        fruc_frame.pack(fill=tk.X, pady=(5,0))
        tk.Checkbutton(fruc_frame, text="Enable FRUC", variable=self.fruc_var, command=lambda: [self.toggle_fruc_fps(), self.apply_gui_options_to_selected_jobs()]).pack(side=tk.LEFT)
        tk.Label(fruc_frame, text="FRUC FPS:").pack(side=tk.LEFT, padx=(5,5))
        self.fruc_fps_entry = tk.Entry(fruc_frame, textvariable=self.fruc_fps_var, width=5, state="disabled")
        self.fruc_fps_entry.pack(side=tk.LEFT)
        self.fruc_fps_entry.bind("<FocusOut>", self.apply_gui_options_to_selected_jobs_event)

    def setup_audio_column(self, parent):
        """Column 3: Audio & Subtitles"""
        # Subtitle Management
        subtitle_group = tk.LabelFrame(parent, text="Subtitle Management & Styling", padx=10, pady=10)
        subtitle_group.pack(fill=tk.X, pady=(0, 5))
        
        subtitle_file_frame = tk.Frame(subtitle_group)
        subtitle_file_frame.pack(fill=tk.X, pady=(0, 10))
        tk.Label(subtitle_file_frame, text="Subtitle File:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.subtitle_combobox = ttk.Combobox(subtitle_file_frame, state="readonly", width=25)
        self.subtitle_combobox.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.subtitle_combobox.bind("<<ComboboxSelected>>", self.on_subtitle_selected)
        
        self.browse_subtitle_btn = tk.Button(subtitle_file_frame, text="Browse...", command=self.browse_custom_subtitle)
        self.browse_subtitle_btn.pack(side=tk.LEFT, padx=2)
        
        self.remove_subtitle_btn = tk.Button(subtitle_file_frame, text="Remove", command=self.remove_subtitle)
        self.remove_subtitle_btn.pack(side=tk.LEFT, padx=2)
        
        # Subtitle Styling
        font_frame = tk.Frame(subtitle_group)
        font_frame.pack(fill=tk.X, pady=2)
        tk.Label(font_frame, text="Font Family:").pack(side=tk.LEFT, padx=(0, 5))
        self.font_combo = ttk.Combobox(font_frame, textvariable=self.subtitle_font_var, width=15)
        self.font_combo.pack(side=tk.LEFT, padx=5)
        self.font_combo.bind("<<ComboboxSelected>>", self.apply_gui_options_to_selected_jobs)
        self.populate_fonts()
        tk.Label(font_frame, text="Size:").pack(side=tk.LEFT, padx=(10, 5))
        self.subtitle_font_size_entry = tk.Entry(font_frame, textvariable=self.subtitle_font_size_var, width=5)
        self.subtitle_font_size_entry.pack(side=tk.LEFT)
        self.subtitle_font_size_entry.bind("<FocusOut>", self.apply_gui_options_to_selected_jobs_event)

        style_frame = tk.Frame(subtitle_group)
        style_frame.pack(fill=tk.X, pady=2)
        tk.Checkbutton(style_frame, text="Bold", variable=self.subtitle_bold_var, command=self.apply_gui_options_to_selected_jobs).pack(side=tk.LEFT)
        tk.Checkbutton(style_frame, text="Italic", variable=self.subtitle_italic_var, command=self.apply_gui_options_to_selected_jobs).pack(side=tk.LEFT, padx=10)
        
        align_frame = tk.Frame(subtitle_group)
        align_frame.pack(fill=tk.X, pady=2)
        tk.Label(align_frame, text="Align:").pack(side=tk.LEFT)
        tk.Radiobutton(align_frame, text="Top", variable=self.subtitle_alignment_var, value="top", command=self.apply_gui_options_to_selected_jobs).pack(side=tk.LEFT)
        tk.Radiobutton(align_frame, text="Middle", variable=self.subtitle_alignment_var, value="middle", command=self.apply_gui_options_to_selected_jobs).pack(side=tk.LEFT)
        tk.Radiobutton(align_frame, text="Bottom", variable=self.subtitle_alignment_var, value="bottom", command=self.apply_gui_options_to_selected_jobs).pack(side=tk.LEFT)
        tk.Label(align_frame, text="Margin V:").pack(side=tk.LEFT, padx=(10, 5))
        self.subtitle_margin_v_entry = tk.Entry(align_frame, textvariable=self.subtitle_margin_v_var, width=5)
        self.subtitle_margin_v_entry.pack(side=tk.LEFT)
        self.subtitle_margin_v_entry.bind("<FocusOut>", self.apply_gui_options_to_selected_jobs_event)

        color_frame = tk.Frame(subtitle_group)
        color_frame.pack(fill=tk.X, pady=5)
        tk.Label(color_frame, text="Text:").pack(side=tk.LEFT)
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
        
        tk.Checkbutton(subtitle_group, text="Enable Subtitle Burning", variable=self.burn_subtitles_var, command=self.apply_gui_options_to_selected_jobs).pack(anchor="w", pady=(5,0))

        # Audio Processing
        audio_group = tk.LabelFrame(parent, text="Audio Processing", padx=10, pady=10)
        audio_group.pack(fill=tk.X, pady=(0, 5))
        
        tk.Checkbutton(audio_group, text="Normalize Audio", variable=self.normalize_audio_var, command=self._toggle_audio_norm_options).pack(anchor="w")
        
        self.audio_mode_frame = tk.Frame(audio_group)
        self.audio_mode_frame.pack(fill=tk.X, padx=(20,0), pady=(4,0))
        tk.Label(self.audio_mode_frame, text="Output Mode:").pack(side=tk.LEFT)
        tk.Radiobutton(self.audio_mode_frame, text="Stereo + 5.1", variable=self.audio_mode_var, value="stereo+5.1", command=self.apply_gui_options_to_selected_jobs).pack(side=tk.LEFT)
        tk.Radiobutton(self.audio_mode_frame, text="Passthrough", variable=self.audio_mode_var, value="passthrough", command=self.apply_gui_options_to_selected_jobs).pack(side=tk.LEFT)

        self.audio_norm_frame = tk.Frame(audio_group)
        self.audio_norm_frame.pack(fill=tk.X, padx=(20, 0))
        
        lufs_frame = tk.Frame(self.audio_norm_frame)
        lufs_frame.pack(fill=tk.X, pady=1)
        tk.Label(lufs_frame, text="Loudness Target (LUFS):").pack(side=tk.LEFT)
        self.loudness_target_entry = tk.Entry(lufs_frame, textvariable=self.loudness_target_var, width=6)
        self.loudness_target_entry.pack(side=tk.LEFT, padx=5)
        self.loudness_target_entry.bind("<FocusOut>", self.apply_gui_options_to_selected_jobs_event)
        
        lra_frame = tk.Frame(self.audio_norm_frame)
        lra_frame.pack(fill=tk.X, pady=1)
        tk.Label(lra_frame, text="Loudness Range (LRA):").pack(side=tk.LEFT)
        self.loudness_range_entry = tk.Entry(lra_frame, textvariable=self.loudness_range_var, width=6)
        self.loudness_range_entry.pack(side=tk.LEFT, padx=5)
        self.loudness_range_entry.bind("<FocusOut>", self.apply_gui_options_to_selected_jobs_event)
        
        peak_frame = tk.Frame(self.audio_norm_frame)
        peak_frame.pack(fill=tk.X, pady=1)
        tk.Label(peak_frame, text="True Peak (dBTP):").pack(side=tk.LEFT)
        self.true_peak_entry = tk.Entry(peak_frame, textvariable=self.true_peak_var, width=6)
        self.true_peak_entry.pack(side=tk.LEFT, padx=5)
        self.true_peak_entry.bind("<FocusOut>", self.apply_gui_options_to_selected_jobs_event)

    def setup_button_row(self, parent):
        """Bottom buttons spanning all columns"""
        self.start_button = tk.Button(parent, text="Start Processing", command=self.start_processing, bg="#4CAF50", fg="white", font=font.Font(weight="bold"))
        self.start_button.pack(side=tk.LEFT, padx=5, ipady=5)
        self.generate_log_checkbox = tk.Checkbutton(parent, text="Generate Log File", variable=self.generate_log_var, command=self.apply_gui_options_to_selected_jobs)
        self.generate_log_checkbox.pack(side=tk.LEFT, padx=(10, 0))

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
            self.apply_gui_options_to_selected_jobs()

    def browse_lut_file(self):
        """Browse for a custom LUT file"""
        file_path = filedialog.askopenfilename(
            title="Select LUT File",
            filetypes=[("LUT files", "*.cube;*.3dl;*.dat"), ("All files", "*.*")]
        )
        if file_path:
            self.lut_file_var.set(file_path)
            self.apply_gui_options_to_selected_jobs()

    def _toggle_bitrate_override(self):
        is_override = self.override_bitrate_var.get()
        new_state = "normal" if is_override else "disabled"
        self.manual_bitrate_entry.config(state=new_state)
        if not is_override:
            self._update_bitrate_display()
        self.apply_gui_options_to_selected_jobs()

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
        
        self.apply_gui_options_to_selected_jobs()

    def _toggle_upscale_options(self): 
        self.apply_gui_options_to_selected_jobs()

    def _toggle_audio_norm_options(self):
        state = "normal" if self.normalize_audio_var.get() else "disabled"
        for widget in [self.loudness_target_entry, self.loudness_range_entry, self.true_peak_entry]:
            widget.config(state=state)
        self.apply_gui_options_to_selected_jobs()

    def update_status(self, message):
        """Update status bar safely"""
        self.status_var.set(message)
        self.root.update_idletasks()

    def apply_gui_options_to_selected_jobs(self, event=None):
        selected_indices = self.job_listbox.curselection()
        
        if not selected_indices:
            return
            
        options_state = self.get_current_gui_options()
        
        for index in selected_indices:
            job = self.processing_jobs[index]
            job['options'].update(options_state)
            
            # Update display name if subtitle changed
            if 'subtitle_path' in options_state:
                self.update_job_display_name(job)

    def apply_gui_options_to_selected_jobs_event(self, event):
        self.apply_gui_options_to_selected_jobs()

    def get_current_gui_options(self):
        """Get current GUI options as a dictionary"""
        return {
            "resolution": self.resolution_var.get(),
            "upscale_algo": self.upscale_algo_var.get(),
            "output_format": self.output_format_var.get(),
            "fruc": self.fruc_var.get(),
            "fruc_fps": self.fruc_fps_var.get(),
            "generate_log": self.generate_log_var.get(),
            "orientation": self.orientation_var.get(),
            "aspect_mode": self.aspect_mode_var.get(),
            "horizontal_aspect": self.horizontal_aspect_var.get(),
            "vertical_aspect": self.vertical_aspect_var.get(),
            "burn_subtitles": self.burn_subtitles_var.get(),
            "override_bitrate": self.override_bitrate_var.get(),
            "manual_bitrate": self.manual_bitrate_var.get(),
            "normalize_audio": self.normalize_audio_var.get(),
            "loudness_target": self.loudness_target_var.get(),
            "loudness_range": self.loudness_range_var.get(),
            "true_peak": self.true_peak_var.get(),
            "audio_mode": self.audio_mode_var.get(),
            "subtitle_font": self.subtitle_font_var.get(),
            "subtitle_font_size": self.subtitle_font_size_var.get(),
            "subtitle_alignment": self.subtitle_alignment_var.get(),
            "subtitle_bold": self.subtitle_bold_var.get(),
            "subtitle_italic": self.subtitle_italic_var.get(),
            "subtitle_primary_color": self.subtitle_primary_color_var.get(),
            "subtitle_outline_color": self.subtitle_outline_color_var.get(),
            "subtitle_shadow_color": self.subtitle_shadow_color_var.get(),
            "subtitle_margin_v": self.subtitle_margin_v_var.get(),
            "lut_file": self.lut_file_var.get(),
            "subtitle_path": self.get_current_subtitle_path()
        }

    def get_current_subtitle_path(self):
        """Get the currently selected subtitle path from combobox"""
        selected_display = self.subtitle_combobox.get()
        if not selected_display or selected_display == "No Subtitles":
            return None
        
        # Extract the actual file path from the display text
        # Format is "tag (filename.srt)" - we need to find the matching file
        selected_indices = self.job_listbox.curselection()
        if not selected_indices:
            return None
            
        job = self.processing_jobs[selected_indices[0]]
        for sub_path in job['available_subtitles']:
            if sub_path is None:
                display = "No Subtitles"
            else:
                video_basename = os.path.splitext(os.path.basename(job['video_path']))[0]
                srt_basename = os.path.splitext(os.path.basename(sub_path))[0]
                tag = srt_basename[len(video_basename):].strip(' .-_')
                if not tag:
                    tag = "(exact match)"
                display = f"{tag} ({os.path.basename(sub_path)})"
            
            if display == selected_display:
                return sub_path
                
        return None

    def add_video_files_and_discover_jobs(self, file_paths):
        """Create multiple jobs per video file (no sub + each subtitle)"""
        debug_print(f"add_video_files_and_discover_jobs called with {len(file_paths)} files")
        for video_path in file_paths:
            # Handle both relative and absolute paths
            video_path = os.path.abspath(video_path)
            dir_name = os.path.dirname(video_path)
            video_basename, _ = os.path.splitext(os.path.basename(video_path))
            
            debug_print(f"Processing video: {video_basename}")
            debug_print(f"Video path: {video_path}")
            debug_print(f"Directory: {dir_name}")

            # Discover all matching SRT files
            matched_srts = []
            try:
                for item in os.listdir(dir_name):
                    if item.lower().endswith('.srt'):
                        srt_basename, _ = os.path.splitext(item)
                        # Exact match
                        if srt_basename == video_basename:
                            matched_srts.append(os.path.join(dir_name, item))
                            debug_print(f"Found exact match subtitle: {item}")
                        # Pattern match (video name followed by separator and language code)
                        elif srt_basename.startswith(video_basename) and len(srt_basename) > len(video_basename):
                            # Check if the next character is a common separator
                            separator = srt_basename[len(video_basename)]
                            if separator in [' ', '.', '-', '_']:
                                matched_srts.append(os.path.join(dir_name, item))
                                debug_print(f"Found pattern match subtitle: {item}")
            except Exception as e:
                print(f"[WARN] Could not scan for subtitles in {dir_name}: {e}")

            debug_print(f"Found {len(matched_srts)} subtitles for {video_basename}: {[os.path.basename(s) for s in matched_srts]}")

            # Create available subtitles list - always include "No Subtitles"
            available_subtitles = [None]  # Start with "No Subtitles" option
            available_subtitles.extend(sorted(matched_srts))
            
            debug_print(f"Available subtitles: {available_subtitles}")
            
            # Create MULTIPLE jobs: one for "No Subtitles" and one for each subtitle
            current_options = self.get_current_gui_options()
            
            # Job for "No Subtitles"
            no_sub_job = {
                "job_id": f"job_{time.time()}_{len(self.processing_jobs)}",
                "video_path": video_path, 
                "subtitle_path": None,  # No subtitles
                "available_subtitles": available_subtitles,
                "options": copy.deepcopy(current_options)
            }
            no_sub_job["display_name"] = f"{os.path.basename(video_path)} [No Subtitles]"
            
            debug_print(f"Creating 'No Subtitles' job: {no_sub_job['display_name']}")
            
            self.processing_jobs.append(no_sub_job)
            self.job_listbox.insert(tk.END, no_sub_job["display_name"])
            debug_print(f"Added job to listbox. Total jobs: {len(self.processing_jobs)}")
            
            # Jobs for each subtitle
            for sub_path in matched_srts:
                sub_job = {
                    "job_id": f"job_{time.time()}_{len(self.processing_jobs)}",
                    "video_path": video_path,
                    "subtitle_path": sub_path,
                    "available_subtitles": available_subtitles,
                    "options": copy.deepcopy(current_options)
                }
                
                # Generate display name with subtitle tag
                srt_basename = os.path.splitext(os.path.basename(sub_path))[0]
                tag = srt_basename[len(video_basename):].strip(' .-_')
                if not tag:
                    tag = "(exact match)"
                sub_job["display_name"] = f"{os.path.basename(video_path)} [Sub: {tag}]"
                
                debug_print(f"Creating subtitle job: {sub_job['display_name']}")
                
                self.processing_jobs.append(sub_job)
                self.job_listbox.insert(tk.END, sub_job["display_name"])
                debug_print(f"Added job to listbox. Total jobs: {len(self.processing_jobs)}")
        
        # After creating all jobs, update the UI
        if self.processing_jobs:
            # Select the first job and update the UI
            self.job_listbox.selection_clear(0, tk.END)
            self.job_listbox.selection_set(0)
            self.on_input_file_select(None)  # Force UI update
    
        debug_print(f"Final job count: {len(self.processing_jobs)}")
        debug_print(f"Job listbox items: {self.job_listbox.size()}")
        self._update_bitrate_display()

    def on_input_file_select(self, event):
        sel = self.job_listbox.curselection()
        debug_print(f"on_input_file_select: selection = {sel}")
        if sel:
            selected_job = self.processing_jobs[sel[0]]
            debug_print(f"Selected job: {selected_job['display_name']}")
            debug_print(f"Selected job subtitle_path: {selected_job['subtitle_path']}")
            debug_print(f"Selected job available_subtitles: {[os.path.basename(s) if s else 'None' for s in selected_job['available_subtitles']]}")
            
            # Update GUI with selected job's options
            self.update_gui_from_job_options(selected_job)
            
            # Update subtitle combobox
            self.update_subtitle_combobox(selected_job)

    def update_gui_from_job_options(self, job):
        """Update GUI controls from job options"""
        options = job['options']
        self.resolution_var.set(options.get("resolution", DEFAULT_RESOLUTION))
        self.upscale_algo_var.set(options.get("upscale_algo", DEFAULT_UPSCALE_ALGO))
        self.output_format_var.set(options.get("output_format", DEFAULT_OUTPUT_FORMAT))
        self.orientation_var.set(options.get("orientation", DEFAULT_ORIENTATION))
        self.aspect_mode_var.set(options.get("aspect_mode", DEFAULT_ASPECT_MODE))
        self.horizontal_aspect_var.set(options.get("horizontal_aspect", DEFAULT_HORIZONTAL_ASPECT))
        self.vertical_aspect_var.set(options.get("vertical_aspect", DEFAULT_VERTICAL_ASPECT))
        self.fruc_var.set(options.get("fruc", DEFAULT_FRUC))
        self.fruc_fps_var.set(options.get("fruc_fps", DEFAULT_FRUC_FPS))
        self.generate_log_var.set(options.get("generate_log", False))
        self.burn_subtitles_var.set(options.get("burn_subtitles", DEFAULT_BURN_SUBTITLES))
        self.override_bitrate_var.set(options.get("override_bitrate", False))
        self.manual_bitrate_var.set(options.get("manual_bitrate", "0"))
        self.normalize_audio_var.set(options.get("normalize_audio", DEFAULT_NORMALIZE_AUDIO))
        self.loudness_target_var.set(options.get("loudness_target", DEFAULT_LOUDNESS_TARGET))
        self.loudness_range_var.set(options.get("loudness_range", DEFAULT_LOUDNESS_RANGE))
        self.true_peak_var.set(options.get("true_peak", DEFAULT_TRUE_PEAK))
        self.audio_mode_var.set(options.get("audio_mode", DEFAULT_AUDIO_MODE))
        self.subtitle_font_var.set(options.get("subtitle_font", DEFAULT_SUBTITLE_FONT))
        self.subtitle_font_size_var.set(options.get("subtitle_font_size", DEFAULT_SUBTITLE_FONT_SIZE))
        self.subtitle_alignment_var.set(options.get("subtitle_alignment", DEFAULT_SUBTITLE_ALIGNMENT))
        self.subtitle_bold_var.set(options.get("subtitle_bold", DEFAULT_SUBTITLE_BOLD))
        self.subtitle_italic_var.set(options.get("subtitle_italic", DEFAULT_SUBTITLE_ITALIC))
        self.subtitle_primary_color_var.set(options.get("subtitle_primary_color", DEFAULT_SUBTITLE_PRIMARY_COLOR))
        self.subtitle_outline_color_var.set(options.get("subtitle_outline_color", DEFAULT_SUBTITLE_OUTLINE_COLOR))
        self.subtitle_shadow_color_var.set(options.get("subtitle_shadow_color", DEFAULT_SUBTITLE_SHADOW_COLOR))
        self.subtitle_margin_v_var.set(options.get("subtitle_margin_v", DEFAULT_SUBTITLE_MARGIN_V))
        self.lut_file_var.set(options.get("lut_file", DEFAULT_LUT_PATH))
        
        # Update color swatches
        self.primary_color_swatch.config(bg=self.subtitle_primary_color_var.get())
        self.outline_color_swatch.config(bg=self.subtitle_outline_color_var.get())
        self.shadow_color_swatch.config(bg=self.subtitle_shadow_color_var.get())

        # Update toggle states
        self._toggle_bitrate_override()
        self.toggle_fruc_fps()
        self._toggle_orientation_options()
        self._toggle_upscale_options()
        self._toggle_audio_norm_options()

    def update_subtitle_combobox(self, job):
        """Update the subtitle combobox with available subtitles for the selected job"""
        debug_print(f"update_subtitle_combobox called for job: {job['display_name']}")
        if not job or 'available_subtitles' not in job:
            debug_print("No job or no available_subtitles, skipping")
            return
            
        display_values = []
        current_display = ""
        
        for sub_path in job['available_subtitles']:
            if sub_path is None:
                display = "No Subtitles"
            else:
                video_basename = os.path.splitext(os.path.basename(job['video_path']))[0]
                srt_basename = os.path.splitext(os.path.basename(sub_path))[0]
                tag = srt_basename[len(video_basename):].strip(' .-_')
                if not tag:
                    tag = "(exact match)"
                display = f"{tag} ({os.path.basename(sub_path)})"
            
            display_values.append(display)
            
            # Find current selection
            if sub_path == job['subtitle_path']:
                current_display = display
                debug_print(f"Current subtitle selection: {current_display}")
        
        debug_print(f"Setting subtitle combobox values: {display_values}")
        self.subtitle_combobox['values'] = display_values
        if current_display:
            self.subtitle_combobox.set(current_display)
            debug_print(f"Set combobox to: {current_display}")
        else:
            self.subtitle_combobox.set("No Subtitles")
            debug_print("No current display, set to 'No Subtitles'")

    def update_job_display_name(self, job):
        """Update job display name based on subtitle selection"""
        video_basename = os.path.basename(job['video_path'])
        if job['subtitle_path'] is None:
            job['display_name'] = f"{video_basename} [No Subtitles]"
        else:
            srt_basename = os.path.splitext(os.path.basename(job['subtitle_path']))[0]
            video_base = os.path.splitext(video_basename)[0]
            tag = srt_basename[len(video_base):].strip(' .-_')
            if not tag:
                tag = "(exact match)"
            job['display_name'] = f"{video_basename} [Sub: {tag}]"
        
        # Update listbox
        if job in self.processing_jobs:
            index = self.processing_jobs.index(job)
            self.job_listbox.delete(index)
            self.job_listbox.insert(index, job['display_name'])
            # Restore selection
            self.job_listbox.selection_set(index)

    def on_subtitle_selected(self, event):
        """Handle subtitle selection from combobox - FIXED VERSION"""
        selected_indices = self.job_listbox.curselection()
        if not selected_indices:
            return
            
        selected_display = self.subtitle_combobox.get()
        debug_print(f"Subtitle selected: {selected_display}")
        
        for index in selected_indices:
            job = self.processing_jobs[index]
            
            # Find the subtitle path that matches the selected display
            selected_sub_path = None
            for sub_path in job['available_subtitles']:
                if sub_path is None:
                    display = "No Subtitles"
                else:
                    video_basename = os.path.splitext(os.path.basename(job['video_path']))[0]
                    srt_basename = os.path.splitext(os.path.basename(sub_path))[0]
                    tag = srt_basename[len(video_basename):].strip(' .-_')
                    if not tag:
                        tag = "(exact match)"
                    display = f"{tag} ({os.path.basename(sub_path)})"
                
                if display == selected_display:
                    selected_sub_path = sub_path
                    break
            
            debug_print(f"Selected subtitle path: {selected_sub_path}")
            
            if selected_sub_path is not None:
                # Update job subtitle
                job['subtitle_path'] = selected_sub_path
                job['options']['subtitle_path'] = selected_sub_path
                
                # Update display name
                self.update_job_display_name(job)

    def browse_custom_subtitle(self):
        """Browse for a custom subtitle file and add it to selected jobs"""
        selected_indices = self.job_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("No Selection", "Please select one or more jobs to add subtitles to.")
            return
            
        file_path = filedialog.askopenfilename(
            title="Select Subtitle File",
            filetypes=[("Subtitle files", "*.srt"), ("All files", "*.*")]
        )
        
        if not file_path:
            return
            
        for index in selected_indices:
            job = self.processing_jobs[index]
            
            # Add to available subtitles if not already present
            if file_path not in job['available_subtitles']:
                job['available_subtitles'].append(file_path)
            
            # Set as current subtitle
            job['subtitle_path'] = file_path
            job['options']['subtitle_path'] = file_path
            
            # Update display name
            self.update_job_display_name(job)
        
        # Update combobox for current selection
        if selected_indices:
            self.update_subtitle_combobox(self.processing_jobs[selected_indices[0]])

    def remove_subtitle(self):
        """Remove subtitle from selected jobs (set to No Subtitles)"""
        selected_indices = self.job_listbox.curselection()
        if not selected_indices:
            return
            
        for index in selected_indices:
            job = self.processing_jobs[index]
            
            # Set to no subtitles
            job['subtitle_path'] = None
            job['options']['subtitle_path'] = None
            
            # Update display name
            self.update_job_display_name(job)
        
        # Update combobox for current selection
        if selected_indices:
            self.update_subtitle_combobox(self.processing_jobs[selected_indices[0]])

    def duplicate_selected_jobs(self):
        """Duplicate selected jobs in the input list"""
        selected_indices = self.job_listbox.curselection()
        if not selected_indices: 
            return
        
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

    # ---------------------- Audio helper (YouTube-compliant) ----------------------
    def build_audio_segment(self, file_path, options):
        """
        Returns: list of ffmpeg args to append for audio handling.
        Modes:
          - stereo+5.1: enforce creation of two outputs: stereo (AAC-LC @ STEREO_BITRATE_K, 48k) and
                        5.1 (AAC-LC @ SURROUND_BITRATE_K, 48k). Uses first audio stream as canonical source.
          - passthrough: copy audio streams unless normalization requested; when normalize is enabled,
                        run loudnorm per input stream and re-encode preserving channel counts.
        """
        audio_streams = get_audio_stream_info(file_path)
        audio_mode = options.get("audio_mode", DEFAULT_AUDIO_MODE)
        normalize = options.get("normalize_audio", False)
        lufs = options.get('loudness_target', DEFAULT_LOUDNESS_TARGET)
        lra = options.get('loudness_range', DEFAULT_LOUDNESS_RANGE)
        peak = options.get('true_peak', DEFAULT_TRUE_PEAK)

        args = []

        if not audio_streams:
            args.extend(["-an"])
            return args

        # PASSTHROUGH
        if audio_mode == "passthrough":
            if not normalize:
                args.extend(["-map", "0:a?"])
                args.extend(["-c:a", "copy"])
                return args
            else:
                # Normalize each input audio stream individually
                num = len(audio_streams)
                fc_parts = []
                map_labels = []
                codec_cfg = []
                for i in range(num):
                    fc_parts.append(f"[0:a:{i}]loudnorm=i={lufs}:lra={lra}:tp={peak}[an{i}]")
                    map_labels.extend(["-map", f"[an{i}]"])
                    ch_count = audio_streams[i].get("channels", 2)
                    codec_cfg.extend([f"-c:a:{i}", "aac", f"-b:a:{i}", f"{PASSTHROUGH_NORMALIZE_BITRATE_K}k", f"-ar:{i}", str(AUDIO_SAMPLE_RATE), f"-ac:{i}", str(ch_count)])
                args.extend(["-filter_complex", ";".join(fc_parts)] + map_labels + codec_cfg)
                return args

        # STEREO + 5.1 mode with FIXED channel mapping
        if audio_mode == "stereo+5.1":
            src_index = 0
            src_channels = audio_streams[0].get("channels", 2)

            # CORRECTED: Proper SMPTE 5.1 channel layout: L, R, C, LFE, Ls, Rs
            # Downmix to stereo (for sources with 6+ channels)
            stereo_downmix = "pan=stereo|FL=0.5*FC+0.707*FL+0.707*BL+0.5*LFE|FR=0.5*FC+0.707*FR+0.707*BR+0.5*LFE"
            
            # Upmix stereo to 5.1 with proper channel assignment
            upmix_5_1_enhanced = (
                "pan=5.1|"
                "FL=1.0*FL|"      # Front Left
                "FR=1.0*FR|"      # Front Right
                "FC=0.707*FL+0.707*FR|"  # Center
                "LFE=0.118*FL+0.118*FR|" # LFE (reduced level)
                "BL=0.816*FL|"    # Rear Left  
                "BR=0.816*FR"     # Rear Right
            )

            fc_parts = []
            map_stereo = "a_stereo"
            map_5ch = "a_5ch"

            if src_channels >= 6:
                # Source has 6+ channels - assume it's 5.1
                print(f"[AUDIO] Source has {src_channels} channels, using as 5.1 source")
                fc_parts.append(f"[0:a:{src_index}]{stereo_downmix}[{map_stereo}]")
                fc_parts.append(f"[0:a:{src_index}]pan=5.1|FL<FL|FR<FR|FC<FC|LFE<LFE|BL<BL|BR<BR[{map_5ch}]")
            else:
                # Source has fewer channels - upmix to 5.1
                print(f"[AUDIO] Source has {src_channels} channels, upmixing to 5.1")
                if src_channels == 1:
                    # Handle mono source
                    fc_parts.append(f"[0:a:{src_index}]pan=stereo|c0=1.0*c0|c1=1.0*c0[{map_stereo}]")
                    fc_parts.append(f"[0:a:{src_index}]pan=5.1|FL=1.0*c0|FR=1.0*c0|FC=1.0*c0|LFE=0.1*c0|BL=0.7*c0|BR=0.7*c0[{map_5ch}]")
                else:
                    # Stereo source
                    fc_parts.append(f"[0:a:{src_index}]anull[{map_stereo}]")
                    fc_parts.append(f"[0:a:{src_index}]{upmix_5_1_enhanced}[{map_5ch}]")

            if normalize:
                # Apply normalization to both tracks
                lnorm = f"loudnorm=i={lufs}:lra={lra}:tp={peak}"
                fc_parts.append(f"[{map_stereo}]{lnorm}[a_stereo_n]")
                fc_parts.append(f"[{map_5ch}]{lnorm}[a_5ch_n]")
                filter_complex = ";".join(fc_parts)
                args.extend(["-filter_complex", filter_complex, "-map", "[a_stereo_n]", "-map", "[a_5ch_n]"])
            else:
                filter_complex = ";".join(fc_parts)
                args.extend(["-filter_complex", filter_complex, "-map", f"[{map_stereo}]", "-map", f"[{map_5ch}]"])

            # Audio encoding parameters
            args.extend([
                "-c:a:0", "aac", "-b:a:0", f"{STEREO_BITRATE_K}k", 
                "-ar:0", str(AUDIO_SAMPLE_RATE), "-ac:0", "2",
                "-c:a:1", "aac", "-b:a:1", f"{SURROUND_BITRATE_K}k", 
                "-ar:1", str(AUDIO_SAMPLE_RATE), "-ac:1", "6",
                "-disposition:a:0", "default",
                "-disposition:a:1", "0",
                "-metadata:s:a:0", "title=Stereo",
                "-metadata:s:a:1", "title=5.1 Surround"
            ])
            return args

        # fallback
        args.extend(["-map", "0:a?", "-c:a", "copy"])
        return args
    # ---------------------- end audio helper ----------------------

    def build_ffmpeg_command_and_run(self, job, orientation, ass_burn=None):
        file_path = job['video_path']
        options = job['options']
        resolution_mode = options.get("resolution", DEFAULT_RESOLUTION)
        output_format = options.get("output_format", DEFAULT_OUTPUT_FORMAT)
        
        # Generate folder name based on output configuration
        folder_name = f"{resolution_mode}_{output_format.upper()}"
        if orientation == "vertical": 
            folder_name += f"_Vertical_{options.get('vertical_aspect').replace(':', 'x')}"
        elif orientation == "original": 
            folder_name += "_Original"
        else:
            horizontal_aspect = options.get('horizontal_aspect').replace(':', 'x')
            if horizontal_aspect != "16x9": 
                folder_name += f"_Horizontal_{horizontal_aspect}"
        
        base_dir = os.path.dirname(file_path) if self.output_mode == 'local' else os.getcwd()
        output_dir = os.path.join(base_dir, folder_name)
        os.makedirs(output_dir, exist_ok=True)
        
        base_name, _ = os.path.splitext(os.path.basename(file_path))
        
        # Generate output filename
        output_name_suffix = ""
        if job['subtitle_path']:
            srt_basename, _ = os.path.splitext(os.path.basename(job['subtitle_path']))
            tag = srt_basename[len(base_name):].strip(' .-_')
            if tag:
                output_name_suffix = f"_{tag}"
        else:
            output_name_suffix = "_NoSub"

        output_file = os.path.join(output_dir, f"{base_name}{output_name_suffix}.mp4")
        
        cmd = self.construct_ffmpeg_command(file_path, output_file, orientation, ass_burn, options)
        ret = self.run_ffmpeg_command(cmd)
        
        if ret == 0:
            print(f"File finalized => {output_file}")
            self.verify_output_file(output_file, options)
        else: 
            print(f"[ERROR] Error encoding {file_path}: return code {ret}")

    def construct_ffmpeg_command(self, file_path, output_file, orientation, ass_burn, options):
        info = get_video_info(file_path)
        
        # Check decoder availability
        decoder_available, decoder_msg = check_decoder_availability(info["codec_name"])
        print(f"[DECODER] {decoder_msg}")
        
        decoder_map = {
            "h264": "h264_cuvid", "hevc": "hevc_cuvid", "av1": "av1_cuvid",
            "vp9": "vp9_cuvid", "mpeg2video": "mpeg2_cuvid", "vc1": "vc1_cuvid", "mjpeg": "mjpeg_cuvid"
        }
        
        # Fallback to software decoding if CUDA decoder not available
        decoder = decoder_map.get(info["codec_name"])
        use_cuda_decoder = True
        
        if not decoder or not decoder_available:
            # Use software decoder as fallback
            decoder = info["codec_name"]
            use_cuda_decoder = False
            print(f"[INFO] Falling back to software decoder: {decoder}")

        if use_cuda_decoder:
            cmd = [
                FFMPEG_CMD, "-y", "-hide_banner",
                "-hwaccel", "cuda",
                "-hwaccel_output_format", "cuda",
                "-c:v", decoder,
                "-i", file_path
            ]
        else:
            # If not using CUDA decoder, remove hwaccel parameters
            cmd = [
                FFMPEG_CMD, "-y", "-hide_banner",
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
                aspect_str = options.get('vertical_aspect')
                width_map = {"HD": 1080, "4k": 2160, "8k": 4320}
                target_width = width_map.get(resolution_key, 1080)
                try: 
                    num, den = map(int, aspect_str.split(':'))
                    target_height = int(target_width * den / num)
                except: 
                    target_height = int(target_width * 16 / 9)
            else: # horizontal
                aspect_str = options.get('horizontal_aspect')
                width_map = {"HD": 1920, "4k": 3840, "8k": 7680}
                target_width = width_map.get(resolution_key, 1920)
                try: 
                    num, den = map(int, aspect_str.split(':'))
                    target_height = int(target_width * den / num)
                except: 
                    target_height = int(target_width * 9 / 16)
            
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

        # Use the LUT file from options
        lut_file = options.get("lut_file", DEFAULT_LUT_PATH)
        if info["is_hdr"] and not is_hdr_output and os.path.exists(lut_file):
            lut_path_escaped = lut_file.replace('\\', '/').replace(':', '\\:')
            cpu_filters.append(f"lut3d=file='{lut_path_escaped}':interp=trilinear")
        
        if options.get("fruc"):
            cpu_filters.append(f"minterpolate=fps={options.get('fruc_fps')}")

        if ass_burn:
            subtitle_path_escaped = ass_burn.replace('\\', '/').replace(':', '\\:')
            cpu_filters.append(f"subtitles=filename='{subtitle_path_escaped}'")
        
        if cpu_filters:
            if vf_filters: 
                vf_filters.append("hwdownload,format=nv12")
            else: 
                vf_filters.append("hwdownload,format=nv12")
            vf_filters.append(",".join(cpu_filters))
            vf_filters.append("format=nv12,hwupload_cuda")
        
        cmd.extend(["-map", "0:v:0"])

        if vf_filters:
            vf_string = ",".join(vf_filters)
            cmd.extend(["-vf", vf_string])

        # Audio handling
        audio_args = self.build_audio_segment(file_path, options)
        cmd.extend(audio_args)

        # Bitrate calculation
        if options.get("override_bitrate", False):
            try:
                bitrate_kbps = int(options.get("manual_bitrate"))
                print(f"[INFO] Manual bitrate override active: {bitrate_kbps} kbps")
            except (ValueError, TypeError):
                print(f"[WARN] Invalid manual bitrate value. Falling back to automatic calculation.")
                bitrate_kbps = get_bitrate("HD", info["framerate"], is_hdr_output)
        else:
            if orientation == "original":
                if info["height"] <= 1080: 
                    bitrate_res_key = "HD"
                elif info["height"] <= 2160: 
                    bitrate_res_key = "4k"
                else: 
                    bitrate_res_key = "8k"
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

    def validate_processing_settings(self):
        """Validate all settings before starting processing"""
        issues = []
        
        # Check LUT file if HDR to SDR conversion might be needed
        lut_file = self.lut_file_var.get()
        if lut_file and not os.path.exists(lut_file):
            issues.append(f"LUT file not found: {lut_file}")
        
        # Check output directories are writable
        try:
            test_dir = tempfile.mkdtemp()
            os.rmdir(test_dir)
        except Exception as e:
            issues.append(f"Cannot create temporary directories: {e}")
        
        # Check audio settings
        try:
            lufs = float(self.loudness_target_var.get())
            if not -50 <= lufs <= 0:
                issues.append("Loudness target should be between -50 and 0 LUFS")
        except ValueError:
            issues.append("Invalid loudness target value")
        
        if issues:
            messagebox.showerror(
                "Configuration Issues", 
                "Please fix the following issues before processing:\n\n" + 
                "\n".join(f"• {issue}" for issue in issues)
            )
            return False
        
        return True

    def start_processing(self):
        if not self.processing_jobs: 
            messagebox.showwarning("No Jobs", "Please add at least one file to create processing jobs.")
            return
        
        # Validate settings before processing
        if not self.validate_processing_settings():
            return
        
        self.output_mode = self.output_mode_var.get()
        print("\n" + "="*80 + "\n--- Starting processing batch ---")
        
        successful_jobs = 0
        failed_jobs = 0
        
        for job_index, job in enumerate(self.processing_jobs):
            try:
                print(f"\nProcessing job {job_index + 1}/{len(self.processing_jobs)}: {job['display_name']}")
                self.update_status(f"Processing {job_index + 1}/{len(self.processing_jobs)}: {job['display_name']}")
                
                subtitle_path = job['subtitle_path']
                temp_ass_path = None
                
                try:
                    if job['options'].get("burn_subtitles", DEFAULT_BURN_SUBTITLES) and subtitle_path:
                        print(f"[INFO] Creating styled subtitle file...")
                        temp_ass_path = create_temporary_ass_file(subtitle_path, job['options'])
                    
                    options = job['options']
                    orientation_mode = options.get("orientation", "horizontal")
                    
                    print("-" * 80)
                    print(f"Processing: {job['display_name']}")
                    
                    if orientation_mode == "horizontal + vertical":
                        print(f"\n--- Processing HORIZONTAL ---")
                        self.build_ffmpeg_command_and_run(job, "horizontal", ass_burn=temp_ass_path)
                        print(f"\n--- Processing VERTICAL ---")
                        self.build_ffmpeg_command_and_run(job, "vertical", ass_burn=temp_ass_path)
                    else:
                        self.build_ffmpeg_command_and_run(job, orientation_mode, ass_burn=temp_ass_path)
                    
                    successful_jobs += 1
                        
                except VideoProcessingError as e:
                    failed_jobs += 1
                    print(f"[ERROR] Failed to process job: {e}")
                    continue
                except Exception as e:
                    failed_jobs += 1
                    print(f"[ERROR] Unexpected error processing job: {e}")
                    continue
                finally:
                    if temp_ass_path and os.path.exists(temp_ass_path):
                        try:
                            os.remove(temp_ass_path)
                            print(f"[INFO] Cleaned up temporary subtitle file.")
                        except Exception as e:
                            print(f"[WARN] Could not clean up temporary file {temp_ass_path}: {e}")
                            
            except Exception as e:
                failed_jobs += 1
                print(f"[ERROR] Critical error processing job: {e}")
                continue
        
        # Final summary
        print("\n" + "="*80)
        print(f"Processing Complete: {successful_jobs} successful, {failed_jobs} failed")
        self.update_status(f"Processing Complete: {successful_jobs} successful, {failed_jobs} failed")
        if failed_jobs > 0:
            print("Check the error messages above for details on failed jobs.")

    def run_ffmpeg_command(self, cmd):
        """Run FFmpeg command with comprehensive error handling"""
        print("Running FFmpeg command:\n" + " ".join(f'"{c}"' if " " in c else c for c in cmd))
        
        try:
            return safe_ffmpeg_execution(cmd, "video encoding")
        except VideoProcessingError as e:
            print(f"\n[ERROR] {e}")
            return 1
        except Exception as e:
            print(f"\n[ERROR] Unexpected error: {e}")
            return 1

    def verify_output_file(self, file_path, options=None):
        print("-" * 80 + f"\n--- Verifying output file: {os.path.basename(file_path)} ---")
        try:
            # Basic video verification
            cmd = [FFPROBE_CMD, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,display_aspect_ratio", "-of", "default=noprint_wrappers=1:nokey=1", file_path]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, env=env)
            output = result.stdout.strip().split('\n')
            if len(output) >= 3: 
                print(f"[VERIFIED] Output Specs: {output[0]}x{output[1]} (Aspect Ratio: {output[2]})")
            else: 
                print(f"[WARN] Could not parse ffprobe output for verification: {output}")
        except FileNotFoundError: 
            print("[WARN] ffprobe not found. Cannot verify output.")
        except subprocess.CalledProcessError as e: 
            print(f"[ERROR] ffprobe failed to verify the file. It may be corrupt. Error: {e.stderr}")
        except Exception as e: 
            print(f"[ERROR] An unexpected error occurred during verification: {e}")

        # Audio-specific verification
        try:
            cmd_audio = [FFPROBE_CMD, "-v", "error", "-select_streams", "a", "-show_entries", "stream=index,channels,channel_layout,sample_rate,codec_name", "-of", "json", file_path]
            res_audio = subprocess.run(cmd_audio, capture_output=True, text=True, check=True, env=env)
            audio_info = json.loads(res_audio.stdout).get("streams", [])
            if not audio_info:
                print("[WARN] No audio streams detected in output.")
            else:
                for i, s in enumerate(audio_info):
                    ch = s.get("channels")
                    layout = s.get("channel_layout", "")
                    sr = s.get("sample_rate", "")
                    codec = s.get("codec_name", "")
                    print(f"[AUDIO VER] Stream #{i}: channels={ch}, layout='{layout}', samplerate={sr}, codec={codec}")
                
                if options and options.get("audio_mode", DEFAULT_AUDIO_MODE) == "stereo+5.1":
                    has_stereo = any((s.get("channels") == 2) for s in audio_info)
                    has_5ch = any((s.get("channels") == 6) for s in audio_info)
                    if not has_stereo or not has_5ch:
                        print("[WARN] Expected both stereo and 5.1 audio streams but did not find both.")
                    else:
                        for s in audio_info:
                            if s.get("channels") == 6 and str(AUDIO_SAMPLE_RATE) not in str(s.get("sample_rate", "")):
                                print(f"[WARN] 5.1 stream sample rate != {AUDIO_SAMPLE_RATE}. YouTube recommends 48 kHz for 5.1.")
        except Exception as e:
            print(f"[WARN] Could not run audio ffprobe verification: {e}")
        finally:
            print("-" * 80)
    
    # File management methods
    def add_files(self): 
        files = filedialog.askopenfilenames(
            title="Select Video Files", 
            filetypes=[("Video Files", "*.mp4;*.mkv;*.avi;*.mov;*.webm;*.flv;*.wmv"), ("All Files", "*.*")]
        )
        self.add_video_files_and_discover_jobs(files)
    
    def handle_file_drop(self, event): 
        files = self.root.tk.splitlist(event.data)
        self.add_video_files_and_discover_jobs(files)
    
    def remove_selected(self):
        selected_indices = list(self.job_listbox.curselection())
        for index in reversed(selected_indices):
            del self.processing_jobs[index]
            self.job_listbox.delete(index)
    
    def clear_all(self): 
        self.processing_jobs.clear()
        self.job_listbox.delete(0, tk.END)
    
    def select_all_files(self): 
        self.job_listbox.select_set(0, tk.END)
        self.on_input_file_select(None)
    
    def clear_file_selection(self): 
        self.job_listbox.select_clear(0, tk.END)
    
    def toggle_fruc_fps(self): 
        self.fruc_fps_entry.config(state="normal" if self.fruc_var.get() else "disabled")

if __name__ == "__main__":
    import glob
    from tkinterdnd2 import TkinterDnD
    
    parser = argparse.ArgumentParser(description="YouTube Batch Video Processing Tool", formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-o', '--output-mode', dest='output_mode', choices=['local', 'pooled'], default='local', help="Set the initial output directory mode. 'local' (default) or 'pooled'.")
    parser.add_argument('input_files', nargs='*', help="Optional: Paths to video files or glob patterns (e.g., 'C:\\Videos\\*.mp4').")
    parser.add_argument('-d', '--debug', action='store_true', help="Enable debug mode with verbose output")
    args = parser.parse_args()
    
    # Set debug mode globally
    DEBUG_MODE = args.debug
    
    debug_print(f"Command line args: output_mode={args.output_mode}, input_files={args.input_files}, debug={args.debug}")
    
    # Check CUDA availability
    print("Checking CUDA availability...")
    if not check_cuda_availability():
        messagebox.showerror(
            "CUDA Not Available", 
            "CUDA hardware acceleration is required but not available.\n\n"
            "Please ensure:\n"
            "1. NVIDIA GPU with CUDA support is installed\n"
            "2. Latest NVIDIA drivers are installed\n"
            "3. FFmpeg with CUDA support is available\n\n"
            "The application will now exit."
        )
        sys.exit(1)
    
    # Check FFmpeg capabilities
    print("Checking FFmpeg capabilities...")
    capabilities = check_ffmpeg_capabilities()
    if not capabilities['nvenc']:
        messagebox.showwarning(
            "NVENC Not Available",
            "NVENC encoders not found in FFmpeg. Video encoding may fail.\n"
            "Continuing anyway..."
        )
    
    root = TkinterDnD.Tk()
    initial_files = []
    
    if args.input_files:
        for pattern in args.input_files: 
            found_files = glob.glob(pattern)
            initial_files.extend(found_files)
            debug_print(f"Pattern '{pattern}' matched {len(found_files)} files: {found_files}")
    else:
        current_dir = os.getcwd()
        video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv', '.wmv']
        print(f"No input files provided. Performing a deep scan of current directory: {current_dir}...")
        files_found = []
        for root_dir, dirs, files in os.walk(current_dir):
            if any(x in root_dir for x in ["SDR_Vertical", "HDR_Vertical", "SDR_Original"]):
                continue
            for filename in files:
                if os.path.splitext(filename)[1].lower() in video_extensions:
                    files_found.append(os.path.join(root_dir, filename))
        initial_files.extend(sorted(files_found))
        debug_print(f"Deep scan found {len(files_found)} video files")
    
    debug_print(f"Total initial files: {len(initial_files)}")
    debug_print(f"Files: {initial_files}")
    
    app = VideoProcessorApp(root, sorted(list(set(initial_files))), args.output_mode)
    debug_print("Starting main loop...")
    root.mainloop()
    debug_print("Main loop ended")