r"""
===============================================================================
vid.py - Advanced Video Encoding and Audio Processing Utility
===============================================================================

DOCUMENTATION & MAINTENANCE POLICY
----------------------------------
This documentation block is a living document integrated directly into the 
script source. It MUST be updated with every feature addition, bug fix, or 
UI change to ensure that the source code remains the single source of truth 
for the tool's capabilities and logic.

Overview
--------
`vid.py` is a professional-grade, GUI-driven batch video processing utility 
built on FFmpeg. It focuses on high-quality production pipelines for content 
creators, featuring hardware-accelerated NVIDIA NVENC encoding, advanced 
audio mastering, and professional subtitle styling.

System Requirements & Dependencies
----------------------------------
*   **Hardware**: NVIDIA GPU (for CUDA/NVENC acceleration).
*   **Tools**: FFmpeg (with `cuda`, `nvenc`, `libass`, `loudnorm`, `dynaudnorm` support).
*   **Optional**: NVEncC (for NVEncC backend; uses FFmpeg preprocessing for unsupported filters).
*   **Library**: `tkinterdnd2` (for drag-and-drop support).
*   **Env Variables**: `FFMPEG_PATH` and `FFPROBE_PATH` (optional).

Core Feature Sets
-----------------

1. **Video Processing (Hardware Accelerated)**:
    *   **Encoders**: H.264, HEVC (H.265), and AV1 via NVIDIA NVENC.
    *   **Color Spaces**: Full SDR and HDR (BT.2020) support with automated tagging.
    *   **Scaling**: Smart upscaling (Nearest, Bilinear, Bicubic, Lanczos) with aspect 
        ratio handling (Crop/Fill, Pad/Fit, Stretch).
    *   **Sharpening (New)**: Integrated CAS (Contrast Adaptive Sharpen) and 
        matrix-based `unsharp` filters. Enabled by default for all jobs.
    *   **Motion**: FRUC (Frame Rate Up-Conversion) via `minterpolate` for 
        smooth 60+ FPS output.
    *   **Hybrid (Stacked) Mode**: Specialized layout for creating vertical 
        content from horizontal sources (e.g., facecam over gameplay).

2. **Audio Mastering & "Loudness War" Tools**:
    *   **Compression**: Multi-parameter `acompressor` for signal density.
    *   **Limiting**: Hard-knee `alimiter` to prevent clipping at 0dB.
    *   **Normalization**: Chained Dynamic Normalization (`dynaudnorm`) + 
        EBU R128 (`loudnorm`) for perfectly leveled signals.
    *   **Measurement**: Post-processing analysis that exports JSON reports 
        with YouTube target comparisons (-14 LUFS).
    *   **Binaural Mixing**: HRTF-based "Sofalizer" for immersive headphone 
        audio from surround sources.

3. **Subtitle Styling & Burning**:
    *   **Sources**: Automatic discovery of external `.srt` or embedded streams.
    *   **Styling**: Powered by `libass`. Customizable fonts, sizes, colors, 
        alpha, outlines, and drop shadows via the GUI.
    *   **Smart Alignment**: Positions subtitles relative to video content or 
        at the "Seam" in Hybrid layouts.

Workflow Logic
--------------
*   **Job Hashing**: Uses MD5 hashes of processing options to avoid redundant 
    encodes and manage unique file naming.
*   **Threaded Processing**: Offloads FFmpeg execution to background threads 
    to keep the GUI responsive.
*   **Graceful Exit**: Signal handling for Ctrl+C to kill FFmpeg processes 
    and purge temporary files immediately.

-------------------------------------------------------------------------------
Version History
-------------------------------------------------------------------------------
v8.9 - Codec Selection & Validation (2026-02-05)
    • FEATURE: Added explicit codec dropdown (H.264/HEVC/AV1) in the Encoder tab.
    • FEATURE: Codec list is linked to SDR/HDR output format (HDR requires HEVC/AV1).
    • UX: Warns before H.264 + 4320p encodes, with an option to continue anyway.
v8.10 - NVEncC Backend Option (2026-02-07)
    • FEATURE: Added Encoder Backend selection:
        - ffmpeg_only
        - nvencc_with_ffmpeg (FFmpeg preprocess + NVEncC encode)
        - nvencc_only (NVEncC only, FFmpeg-only features disabled)
        - nvencc_video_with_ffmpeg_audio (NVEncC video + FFmpeg audio prepass)
    • FEATURE: NVEncC-only Upscale options: NVVFX SuperRes + NGX VSR with per-algo settings.
    • NOTE: Output container remains MP4.
v8.11 - FFmpeg CPU Controls (2026-02-12)
    • FEATURE: Added FFmpeg CPU thread control (`-threads`) in Encoder tab.
    • FEATURE: Added FFmpeg process priority control for Windows (Idle to Realtime).
    • UX: New options are saved in presets and applied per job.
v8.12 - NVEncC Aspect Handling (2026-02-20)
    • FIX: Re-enabled Aspect Handling options (Crop/Pad/Stretch) for `nvencc_only`
           and `nvencc_video_with_ffmpeg_audio`.
    • FEATURE: NVEncC path now maps aspect mode to `--output-res` behavior:
           Crop -> `preserve_aspect_ratio=increase`, Pad/Fit -> `decrease`.
    • UX: `Blur` and `Pixelate` remain disabled on NVEncC-only video paths.
v8.13 - Merged Horizontal/Vertical Mode (2026-02-20)
    • UX: Merged Horizontal + Vertical into a single orientation mode.
    • FEATURE: Output orientation is derived from the selected aspect ratio.
    • UX: Horizontal and vertical aspect presets are shown together in merged mode.
v8.8 - Subtitle & Workflow Improvements (2025-12-29)
    • FEATURE: "Smart CJK Wrapping": Subtitles now treat straight/wide characters
               differently (Width 1 vs 2), fixing premature wrapping for English
               and late wrapping for Chinese/Japanese.
    • FEATURE: "Dynamic Wrap Limit": Auto-calculates safe line length based on
               Video Resolution and Font Size to prevent text runoff.
    • FIX: Dynamic Subtitle Resolution: Now sets correct PlayResX/Y for Vertical/4K/Hybrid
           formats, preventing subtitles from being cut off or scaling wrongly.
    • UI: Added "Select Matches Preset" button to queue for batch selection.
    • UI: Added "Suffix Override" to Preset UI.
    • UI: Moved Loudness/Normalization controls to dedicated "Loudness" tab.

v8.7 - Upscaling Algorithm Expansion (2025-12-26)
    • UI: Replaced upscale algorithm radio buttons with dropdown (Combobox).
    • FEATURE: Added "Nearest" algorithm option for fastest upscaling.
    • FEATURE: Exposed all 4 scale_cuda algorithms: nearest, bilinear, bicubic, lanczos.
    • UX: Added tooltip explaining quality/speed tradeoffs for each algorithm.

v8.6 - Sharpening & Docs Update (2025-12-26)
    • FEATURE: Integrated video sharpening with `cas` and `unsharp` filters.
    • FEATURE: Enabled sharpening by default (Algorithm: `cas`, Strength: `0.5`).
    • UI: Added Sharpening controls to the Color & Quality section.
    • DOCS: Expanded comprehensive documentation header and maintenance policy.

v8.5 - Loudness War & Measurement Update (2025-12-26)
    • FEATURE: "Loudness War" section with compressor and limiter.
    • FEATURE: Enhanced Loudness Measurement system with JSON export.
    • FEATURE: "Brickwall" normalization settings for maximum signal density.

v8.0 - Audio Normalization Update (2025-12-26)
    • FEATURE: Added chained audio normalization (Dynamic + EBU R128).
    • FEATURE: Enabled Dynamic Normalization by default.

v7.8 - Stability & Threading Update (2025-12-20)
    • FEATURE: Added Threading and Progress Bar.
    • FEATURE: Graceful Exit (Ctrl+C) handling.
    • BUGFIX: Hybrid jobs "Seam" alignment logic parity.
"""
import os
import subprocess
import shutil
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, font, colorchooser, simpledialog
from tkinterdnd2 import TkinterDnD, DND_FILES
import unicodedata
from ftfy import fix_text
import threading
import sys
import math
import argparse
import tempfile
import atexit
import re
import copy
import time
import glob
import textwrap
import hashlib
from collections import Counter, deque
import signal

# -------------------------- Configuration / Constants --------------------------
FFMPEG_CMD = os.environ.get("FFMPEG_PATH", "ffmpeg")
FFPROBE_CMD = os.environ.get("FFPROBE_PATH", "ffprobe")
NVENCC_CMD = os.environ.get("NVENCC_PATH", "NVEncC64")

# Audio settings (Bitrates for different track types)
AUDIO_SAMPLE_RATE = 48000                           # Sample rate for all audio outputs (Hz). Fixed: 48000
MONO_BITRATE_K = 128                                # Bitrate for mono tracks (kbps). Default: 128
STEREO_BITRATE_K = 384                              # Bitrate for stereo tracks (kbps). Default: 384
SURROUND_BITRATE_K = 512                            # Bitrate for 5.1 surround tracks (kbps). Default: 512
PASSTHROUGH_NORMALIZE_BITRATE_K = 192               # Bitrate when passthrough with normalization (kbps). Default: 192

# Video & General
# NOTE: Set these to empty strings or valid paths on your machine.
DEFAULT_LUT_PATH = ""                               # Path to 3D LUT file for HDR to SDR conversion. Default: "" (none)
DEFAULT_SOFA_PATH = r"E:\Small-Scripts\SOFALIZER\D1_48K_24bit_256tap_FIR_SOFA.sofa"  # Path to SOFA file for binaural audio (Sofalizer). Default: E:\\Small-Scripts\\SOFALIZER\\D1_48K_24bit_256tap_FIR_SOFA.sofa

DEFAULT_RESOLUTION = "2160p"                        # Output resolution. Default: 2160p (4k)
DEFAULT_UPSCALE_ALGO = "bicubic"                    # Upscaling algorithm. Default: bicubic, Options: nearest, bilinear, bicubic, lanczos, spline36 (NVEncC)
DEFAULT_OUTPUT_FORMAT = "sdr"                       # Output color format. Default: sdr, Options: sdr, hdr
DEFAULT_VIDEO_CODEC = "h264"                        # Output codec. Default: h264, Options: h264, hevc, av1
DEFAULT_ENCODER_BACKEND = "ffmpeg_only"             # Encoder backend. Default: ffmpeg_only, Options: ffmpeg_only, nvencc_with_ffmpeg, nvencc_only, nvencc_video_with_ffmpeg_audio
DEFAULT_NVENC_SUPERRES_MODE = "1"                   # NVVFX SuperRes mode. Default: 1, Range: 0-1
DEFAULT_NVENC_NVVFX_DENOISE = False                 # Enable NVVFX Video Denoising. Default: False
DEFAULT_NVENC_NGX_VSR_QUALITY = "1"                 # NGX VSR quality. Default: 1, Range: 1-4
DEFAULT_MAX_SIZE_MB = 0                             # Max file size in MB (0 = Disabled)
DEFAULT_MAX_DURATION = 0                            # Max duration in seconds (0 = Disabled)
DEFAULT_ORIENTATION = "horizontal + vertical"       # Video orientation. Default: horizontal + vertical, Options: horizontal + vertical, hybrid (stacked), hybrid-duo (dual source), original
DEFAULT_ASPECT_MODE = "crop"                        # Aspect ratio handling. Default: crop, Options: crop, pad, stretch, pixelate, blur, ambient
DEFAULT_PAD_COLOR = "#000000"                       # Padding color for Aspect Ratio Handling set to "pad" (Fit). Default: #000000
DEFAULT_PIXELATE_MULTIPLIER = "16"                  # Pixelation factor for background. Default: 16
DEFAULT_PIXELATE_BRIGHTNESS = "-0.4"                # Background brightness adjustment. Default: -0.4
DEFAULT_PIXELATE_SATURATION = "0.6"                  # Background saturation adjustment. Default: 0.6
DEFAULT_BLUR_SIGMA = "30"                           # Blur strength for background. Default: 30, Range: 0.5 to 100+
DEFAULT_BLUR_STEPS = "1"                            # Blur quality iterations. Default: 1, Range: 1 to 6
DEFAULT_AMBIENT_SPREAD = "2"                        # Ambient glow spread (downscale factor). Default: 2
DEFAULT_HORIZONTAL_ASPECT = "16:9"                  # Horizontal aspect ratio. Default: 16:9, Common: 16:9, 21:9, 4:3
DEFAULT_VERTICAL_ASPECT = "4:5"                     # Vertical aspect ratio. Default: 4:5, Common: 4:5, 9:16
DEFAULT_VIDEO_OFFSET_X = "0"                        # Horizontal video offset (pixels). Default: 0
DEFAULT_VIDEO_OFFSET_Y = "0"                        # Vertical video offset (pixels). Default: 0
DEFAULT_FRUC = False                                # Enable frame rate up-conversion. Default: False
DEFAULT_FRUC_FPS = "60"                             # Target FPS for FRUC. Default: 60, Range: 30 to 120
DEFAULT_BURN_SUBTITLES = True                       # Burn subtitles into video. Default: True
DEFAULT_RENDER_BY_CHAPTERS = False                 # Render video by chapters if available. Default: False
DEFAULT_SPLIT_SUBTITLES_BY_CHAPTER = False          # Split and export subtitles matching chapters. Default: False
DEFAULT_USE_SHARPENING = True                       # Enable video sharpening. Default: True
DEFAULT_FFMPEG_DENOISE_VULKAN = False               # Enable FFmpeg Vulkan Denoise. Default: False

# --- Encoder Config Group ---
DEFAULT_NVENC_PRESET = "p1"                         # NVENC preset. Options: p1 to p7 (p1 is fastest/lowest quality)
DEFAULT_NVENC_TUNE = "hq"                           # NVENC tuning. Options: hq, ll, ull, lossless
DEFAULT_NVENC_PROFILE_SDR = "high"                  # NVENC profile for SDR. Options: high, main, baseline
DEFAULT_NVENC_PROFILE_HDR = "main10"                # NVENC profile for HDR. Options: main10
DEFAULT_NVENC_RC_LOOKAHEAD = "32"                   # Rate control lookahead. Default: 32
DEFAULT_NVENC_MULTIPASS = "fullres"                 # Multipass mode. Options: disabled, qres, fullres
DEFAULT_NVENC_SPATIAL_AQ = "1"                      # Spatial AQ. Default: 1 (Enabled)
DEFAULT_NVENC_TEMPORAL_AQ = "1"                     # Temporal AQ. Default: 1 (Enabled)
DEFAULT_NVENC_BFRAMES = "4"                         # Number of B-frames. Default: 4
DEFAULT_NVENC_B_REF_MODE = "middle"                 # B-frame reference mode. Default: middle
DEFAULT_NVENCC_DECODE_MODE = "auto"                 # NVEncC decode mode. Options: auto, avhw, avsw
DEFAULT_NVENCC_COLOR_TAG_MODE = "auto"              # NVEncC color tag mode. Options: auto, custom
DEFAULT_NVENCC_COLOR_PRIM = "bt709"                 # NVEncC custom color primaries
DEFAULT_NVENCC_COLOR_TRANSFER = "bt709"             # NVEncC custom transfer characteristics
DEFAULT_NVENCC_COLOR_MATRIX = "bt709"               # NVEncC custom color matrix
DEFAULT_NVENCC_OUTPUT_DEPTH = "auto"                # NVEncC output depth. Options: auto, 8, 10
DEFAULT_NVENCC_STRICT_NO_COLOR_TAGGING = False      # Skip explicit --colorprim/--transfer/--colormatrix
DEFAULT_FFMPEG_THREADS = "0"                        # FFmpeg CPU threads. Default: 0 (auto)
DEFAULT_FFMPEG_PRIORITY = "normal"                  # FFmpeg process priority. Windows only. Default: normal
DEFAULT_SHARPENING_ALGO = "unsharp"                 # Sharpening algorithm. Default: cas, Options: cas, unsharp
DEFAULT_SHARPENING_STRENGTH = "0.5"                 # Sharpening strength. Default: 0.5, Range: 0.0 to 1.0

# -------------------------- Output Configuration --------------------------
DEFAULT_OUTPUT_TO_SUBFOLDERS = False                # Output to subfolders per video. Default: False
DEFAULT_SUBFOLDER_BY_SUBTITLE = False               # Output subtitle tag as subfolder. Default: False
DEFAULT_GROUP_BY_PRESET = False                     # Group output into preset subfolders. Default: False
DEFAULT_GROUP_BY_VIDEO = False                      # Group output into video subfolders. Default: False
DEFAULT_SUBFOLDER_OVERRIDE = ""                     # Custom override for subfolder name
DEFAULT_SINGLE_OUTPUT_DIR_NAME = "Output"           # Name of pooled output directory. Default: Output

# -------------------------- Workflow Presets --------------------------

# Audio normalization settings
DEFAULT_NORMALIZE_AUDIO = False                     # Enable EBU R128 normalization (loudnorm). Default: False
DEFAULT_USE_DYNAUDNORM = True                       # Enable dynamic normalization (dynaudnorm). Default: True

# EBU R128 (loudnorm) parameters
DEFAULT_LOUDNESS_TARGET = "-13"    # (i) Integrated loudness target. Default: -24, Range: -70 to -5
DEFAULT_LOUDNESS_RANGE = "7"      # (lra) Loudness range (dynamic range). Default: 7, Range: 1 to 50
DEFAULT_TRUE_PEAK = "-1.0"           # (tp) Maximum true peak level. Default: -2.0, Range: -9.0 to 0.0

# Dynamic Normalization (dynaudnorm) parameters
DEFAULT_DYNAUDNORM_FRAME_LEN = "100" # (f) Frame length in ms for gain calculation. Brickwall: 100, Default: 500
DEFAULT_DYNAUDNORM_GAUSS_WIN = "3"   # (g) Gaussian filter window size (must be odd). Brickwall: 3, Default: 31
DEFAULT_DYNAUDNORM_PEAK = "1.0"        # (p) Target peak value. Default: 0.95, Range: 0.0 to 1.0
DEFAULT_DYNAUDNORM_MAX_GAIN = "100.0" # (m) Maximum allowed gain factor. Default: 10.0, Range: 1.0 to 100.0

# Loudness War (Compression & Limiting)
DEFAULT_USE_LOUDNESS_WAR = True
DEFAULT_COMPRESSOR_THRESHOLD = "-60" # Level at which compression starts. Default: -24dB, Range: -60dB to 0dB
DEFAULT_COMPRESSOR_RATIO = "3"       # Ratio of input to output level. Default: 10, Range: 1 to 20
DEFAULT_COMPRESSOR_ATTACK = "0.7"   # Time until fully active. Total War: 0.01, Default: 1ms
DEFAULT_COMPRESSOR_RELEASE = "50"   # Time until compression stops. Total War: 10, Default: 100ms
DEFAULT_COMPRESSOR_MAKEUP = "12"     # Additional gain applied after compression. Total War: 40, Default: 12dB
DEFAULT_LIMITER_LIMIT = "0"          # Hard limit ceiling. Fixed: alimiter max is 0dB (1.0 linear)

# Measurement
DEFAULT_MEASURE_LOUDNESS = False                    # Measure output loudness and save JSON report. Default: False

# Audio track selection defaults
DEFAULT_AUDIO_MONO = False                          # Output mono track (downmix). Default: False
DEFAULT_AUDIO_STEREO_DOWNMIX = False                # Output stereo track (standard downmix). Default: False
DEFAULT_AUDIO_STEREO_SOFALIZER = False              # Output stereo track (binaural via Sofalizer). Default: False
DEFAULT_AUDIO_SURROUND_51 = False                   # Output 5.1 surround track. Default: False
DEFAULT_AUDIO_PASSTHROUGH = True                    # Passthrough original audio (no processing). Default: True

# Subtitle defaults
DEFAULT_SUBTITLE_FONT = "HelveticaNeueLT Std Blk"  # Font family name. Default: HelveticaNeueLT Std Blk
DEFAULT_SUBTITLE_FONT_SIZE = "32"                   # Font size in points. Default: 32, Range: 8 to 200
DEFAULT_SUBTITLE_ALIGNMENT = "bottom"               # Vertical alignment. Default: bottom, Options: top, middle, bottom, seam
DEFAULT_SUBTITLE_BOLD = True                        # Bold text style. Default: True
DEFAULT_SUBTITLE_ITALIC = False                     # Italic text style. Default: False
DEFAULT_SUBTITLE_UNDERLINE = False                  # Underline text style. Default: False
DEFAULT_SUBTITLE_MARGIN_V = "335"                   # Vertical margin from edge (pixels). Default: 335, Range: 0 to 1080
DEFAULT_SUBTITLE_MARGIN_L = "50"                    # Left margin from edge (pixels). Default: 50, Range: 0 to 960
DEFAULT_SUBTITLE_MARGIN_R = "100"                   # Right margin from edge (pixels). Default: 100, Range: 0 to 960
DEFAULT_SUBTITLE_SEAM_H_OFFSET = "0"                # Horizontal offset for Seam alignment. Default: 0
DEFAULT_SUBTITLE_SEAM_V_OFFSET = "0"                # Vertical offset for Seam alignment. Default: 0
DEFAULT_REFORMAT_SUBTITLES = True                   # Reformat to single wrapped line. Default: True
DEFAULT_WRAP_LIMIT = "42"                           # Characters per line before wrapping. Default: 42, Range: 20 to 100
DEFAULT_SUBTITLE_MAX_LINES = "0"                    # Max lines for a subtitle block after wrapping. 0 = unlimited.
DEFAULT_SUBTITLE_REPEAT_MIN_RUN = "12"              # Min repeat length to collapse (e.g., "whyyyy..."). Default: 12
DEFAULT_SUBTITLE_REPEAT_RATIO = "0.75"              # Skip line if single char dominates ratio. Default: 0.75

# Fill (Primary text color)
DEFAULT_FILL_COLOR = "#FFAA00"                      # Fill color (hex). Default: #FFAA00 (orange)
DEFAULT_FILL_ALPHA = 0                              # Fill transparency. Default: 0 (opaque), Range: 0 (opaque) to 255 (transparent)

# Outline (Border around text)
DEFAULT_OUTLINE_COLOR = "#000000"                   # Outline color (hex). Default: #000000 (black)
DEFAULT_OUTLINE_ALPHA = 0                           # Outline transparency. Default: 0 (opaque), Range: 0 (opaque) to 255 (transparent)
DEFAULT_OUTLINE_WIDTH = "9"                         # Outline thickness (pixels). Default: 9, Range: 0 to 20

# Shadow (Drop shadow behind text)
DEFAULT_SHADOW_COLOR = "#202020"                    # Shadow color (hex). Default: #202020 (dark gray)
DEFAULT_SHADOW_ALPHA = 120                          # Shadow transparency. Default: 120 (semi-transparent), Range: 0 (opaque) to 255 (transparent)
DEFAULT_SHADOW_OFFSET_X = "2"                       # Shadow horizontal offset (pixels). Default: 2, Range: -50 to 50
DEFAULT_SHADOW_OFFSET_Y = "4"                       # Shadow vertical offset (pixels). Default: 4, Range: -50 to 50
DEFAULT_SHADOW_BLUR = "5"                           # Shadow blur radius (pixels). Default: 5, Range: 0 to 20

# Title Burn defaults
DEFAULT_TITLE_BURN_ENABLED = False                  # Enable title burning. Default: False
DEFAULT_TITLE_JSON_SUFFIX = ""                      # JSON file suffix (e.g., "-yt", "-instagram"). Default: blank
DEFAULT_TITLE_REMOVE_HASHTAGS = True                # Remove hashtags from extracted title text. Default: True
DEFAULT_TITLE_ENABLE_EMOJI = True                   # Enable emoji rendering in title text. Default: True
DEFAULT_TITLE_AUTODETECT = True                     # Auto-detect title from JSON when available. Default: True
DEFAULT_TITLE_OVERRIDE_TEXT = ""                    # Manual title text override. Default: blank
DEFAULT_TITLE_START_TIME = "00:00:00.00"            # Title start time. Default: 00:00:00.00
DEFAULT_TITLE_END_TIME = "00:00:03.00"              # Title end time. Default: 00:00:03.00 (3 seconds)
DEFAULT_TITLE_FONT = "HelveticaNeueLT Std Blk"      # Title font family. Default: HelveticaNeueLT Std Blk
DEFAULT_TITLE_FONT_SIZE = "48"                      # Title font size. Default: 48
DEFAULT_TITLE_BOLD = True                           # Title bold style. Default: True
DEFAULT_TITLE_ITALIC = False                        # Title italic style. Default: False
DEFAULT_TITLE_UNDERLINE = False                     # Title underline style. Default: False
DEFAULT_TITLE_ALIGNMENT = "top"                     # Title alignment. Default: top, Options: top, middle, bottom
DEFAULT_TITLE_MARGIN_V = "50"                       # Title vertical margin. Default: 50
DEFAULT_TITLE_MARGIN_L = "50"                       # Title left margin. Default: 50
DEFAULT_TITLE_MARGIN_R = "50"                       # Title right margin. Default: 50
DEFAULT_TITLE_FILL_COLOR = "#FFFFFF"                # Title fill color. Default: #FFFFFF (white)
DEFAULT_TITLE_FILL_ALPHA = 0                        # Title fill transparency. Default: 0 (opaque)
DEFAULT_TITLE_OUTLINE_COLOR = "#000000"             # Title outline color. Default: #000000 (black)
DEFAULT_TITLE_OUTLINE_ALPHA = 0                     # Title outline transparency. Default: 0 (opaque)
DEFAULT_TITLE_OUTLINE_WIDTH = "3"                   # Title outline width. Default: 3
DEFAULT_TITLE_SHADOW_COLOR = "#000000"              # Title shadow color. Default: #000000 (black)
DEFAULT_TITLE_SHADOW_ALPHA = 128                    # Title shadow transparency. Default: 128
DEFAULT_TITLE_SHADOW_OFFSET_X = "2"                 # Title shadow X offset. Default: 2
DEFAULT_TITLE_SHADOW_OFFSET_Y = "3"                 # Title shadow Y offset. Default: 3
DEFAULT_TITLE_SHADOW_BLUR = "4"                     # Title shadow blur. Default: 4

DEBUG_MODE = False

# --- Global State for Graceful Exit ---
CURRENT_FFMPEG_PROCESS = None
CURRENT_TEMP_FILE = None
CURRENT_JOB_TEMP_DIR = None
TRACKED_TEMP_FILES = set()
TRACKED_TEMP_LOCK = threading.Lock()

def debug_print(*args, **kwargs):
    if DEBUG_MODE:
        print("[DEBUG]", *args, **kwargs)

env = os.environ.copy()
env["PYTHONIOENCODING"] = "utf-8"

FFMPEG_PRIORITY_LABELS = ["idle", "below_normal", "normal", "above_normal", "high", "realtime"]

class VideoProcessingError(Exception):
    pass

def normalize_ffmpeg_threads(value):
    """Returns validated FFmpeg thread count. 0 means auto."""
    try:
        n = int(str(value).strip())
        return n if n >= 0 else 0
    except Exception:
        return 0

def normalize_ffmpeg_priority(value):
    raw = str(value).strip().lower()
    return raw if raw in FFMPEG_PRIORITY_LABELS else DEFAULT_FFMPEG_PRIORITY

def get_windows_creationflags_for_priority(priority_label):
    """Maps a priority label to subprocess creationflags on Windows."""
    if os.name != "nt":
        return 0
    priority_map = {
        "idle": getattr(subprocess, "IDLE_PRIORITY_CLASS", 0),
        "below_normal": getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0),
        "normal": getattr(subprocess, "NORMAL_PRIORITY_CLASS", 0),
        "above_normal": getattr(subprocess, "ABOVE_NORMAL_PRIORITY_CLASS", 0),
        "high": getattr(subprocess, "HIGH_PRIORITY_CLASS", 0),
        "realtime": getattr(subprocess, "REALTIME_PRIORITY_CLASS", 0),
    }
    return priority_map.get(normalize_ffmpeg_priority(priority_label), 0)

def _normalize_temp_path(path):
    if not path:
        return ""
    if not os.path.isabs(path):
        path = os.path.join(os.getcwd(), path)
    return os.path.abspath(path)

def register_temp_file(path):
    norm = _normalize_temp_path(path)
    if not norm:
        return
    with TRACKED_TEMP_LOCK:
        TRACKED_TEMP_FILES.add(norm)

def unregister_temp_file(path):
    norm = _normalize_temp_path(path)
    if not norm:
        return
    with TRACKED_TEMP_LOCK:
        TRACKED_TEMP_FILES.discard(norm)

def cleanup_tracked_temp_files(verbose=False):
    with TRACKED_TEMP_LOCK:
        tracked = list(TRACKED_TEMP_FILES)
        TRACKED_TEMP_FILES.clear()
    for temp_path in tracked:
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
                if verbose:
                    print(f"[INFO] Cleaned up temp file: {temp_path}")
        except Exception as e:
            if verbose:
                print(f"[WARN] Could not delete temp file: {temp_path} ({e})")

def cleanup_single_temp_file(path, verbose=False):
    norm = _normalize_temp_path(path)
    if not norm:
        return
    try:
        if os.path.exists(norm):
            os.remove(norm)
            if verbose:
                print(f"[INFO] Cleaned up temp file: {norm}")
    except Exception as e:
        if verbose:
            print(f"[WARN] Could not delete temp file: {norm} ({e})")
    finally:
        unregister_temp_file(norm)

def get_temp_work_dir():
    if CURRENT_JOB_TEMP_DIR and os.path.isdir(CURRENT_JOB_TEMP_DIR):
        return CURRENT_JOB_TEMP_DIR
    return os.getcwd()

# --- Graceful Exit Handler ---
def handle_sigint(signum, frame):
    """Handles Ctrl+C to clean up subprocesses and temp files."""
    print("\n\n" + "!"*60)
    print("[WARN] Ctrl+C detected! Stopping immediately...")
    print("!"*60)
    
    global CURRENT_FFMPEG_PROCESS, CURRENT_TEMP_FILE

    if CURRENT_FFMPEG_PROCESS:
        try:
            print(f"[INFO] Terminating FFmpeg process (PID: {CURRENT_FFMPEG_PROCESS.pid})...")
            CURRENT_FFMPEG_PROCESS.kill()
            CURRENT_FFMPEG_PROCESS.wait()
        except Exception as e:
            print(f"[ERROR] Failed to kill process: {e}")

    if CURRENT_TEMP_FILE:
        cleanup_single_temp_file(CURRENT_TEMP_FILE, verbose=True)
    cleanup_tracked_temp_files(verbose=True)

    print("[INFO] Exiting.")
    sys.exit(0)

# --- Utility Functions ---
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
        capabilities['nvenc'] = any(x in result.stdout.lower() for x in ['h264_nvenc', 'hevc_nvenc', 'av1_nvenc'])
        cmd = [FFMPEG_CMD, "-filters"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        capabilities['filters'] = all(x in result.stdout.lower() for x in ['loudnorm', 'dynaudnorm', 'scale_cuda', 'lut3d'])
        return capabilities
    except Exception as e:
        print(f"[ERROR] Failed to check FFmpeg capabilities: {e}")
        return capabilities

def check_nvencc_availability():
    if os.path.isfile(NVENCC_CMD):
        return True
    return shutil.which(NVENCC_CMD) is not None

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

def get_safe_filter_path(path, base_dir=None):
    """
    Returns a path that is safe for use within an FFmpeg or NVEncC filter string.
    If base_dir is provided, it tries to calculate a relative path to avoid
    'poisoned' characters (like commas or colons) in parent directories.
    """
    if not path:
        return ""
    
    target_path = str(path)
    
    if base_dir:
        try:
            # Try to get relative path from base_dir to target_path
            rel = os.path.relpath(target_path, base_dir)
            # If the relative path starts with '..', it means it's outside the base_dir.
            # We only use relative paths if they go "deeper" or stay within the same tree.
            # However, for robustness, as long as it's the same drive, it's usually safer.
            if not rel.startswith(".."):
                target_path = rel
        except ValueError:
            # This happens on Windows if paths are on different drives
            pass

    # Convert \ to / and escape characters for the tool's parser
    p = target_path.replace('\\', '/')
    return p

def escape_ffmpeg_filter_path(path, base_dir=None):
    """
    Escapes a path for use within an FFmpeg filter (e.g., subtitles, lut3d).
    Uses a double-escaping strategy suitable for UNQUOTED filter arguments,
    ensuring delimiters like ':', ' ', and ',' survive both filtergraph 
    and option parsing on Windows.
    """
    if not path:
        return ""
    
    # Try getting a safe relative path first
    p = get_safe_filter_path(path, base_dir)
    
    # Double escape characters that FFmpeg uses as delimiters.
    # We use \\ so that after the first parse, a single \ remains
    # to protect the character during the second parse.
    p = p.replace(':', '\\\\:')
    p = p.replace(' ', '\\\\ ')
    p = p.replace(',', '\\\\,')
    p = p.replace("'", r"\\\'")
    p = p.replace('[', '\\\\[').replace(']', '\\\\]')
    
    return p

def get_file_duration(file_path):
    """Returns the duration of the file in seconds."""
    cmd = [FFPROBE_CMD, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", file_path]
    try:
        result = safe_ffprobe(cmd, "duration check")
        return float(result.stdout.strip())
    except Exception:
        return 0.0

def safe_ffmpeg_execution(cmd, operation="encoding", duration=None, progress_callback=None, priority="normal", cwd=None):
    global CURRENT_FFMPEG_PROCESS
    try:
        popen_kwargs = {
            "stdout": subprocess.PIPE,
            "stderr": subprocess.STDOUT,
            "stdin": subprocess.DEVNULL,
            "env": env,
            "text": True,
            "encoding": "utf-8",
            "errors": "replace",
            "bufsize": 1,
        }
        creationflags = get_windows_creationflags_for_priority(priority)
        if creationflags:
            popen_kwargs["creationflags"] = creationflags
        if cwd:
            popen_kwargs["cwd"] = cwd
        process = subprocess.Popen(cmd, **popen_kwargs)
        CURRENT_FFMPEG_PROCESS = process

        recent_lines = deque(maxlen=400)
        time_pattern = re.compile(r'time=(\d{2}):(\d{2}):(\d{2}(?:\.\d+)?)')
        carry = ""
        progress_line_active = False
        last_progress_len = 0

        while True:
            if process.stdout is None:
                break
            ch = process.stdout.read(1)
            if ch == "":
                if process.poll() is not None:
                    # Flush any trailing text that didn't end with newline.
                    if carry.strip():
                        line = carry.strip()
                        recent_lines.append(line)
                        sys.stdout.write(("\n" if progress_line_active else "") + line + "\n")
                        sys.stdout.flush()
                    break
                continue

            if ch in ("\r", "\n"):
                line = carry.strip()
                carry = ""
                if not line:
                    continue

                recent_lines.append(line)

                # Progress Parsing (for GUI progress bar)
                if duration and progress_callback and "time=" in line:
                    match = time_pattern.search(line)
                    if match:
                        h, m, s = match.groups()
                        current_seconds = int(h) * 3600 + int(m) * 60 + float(s)
                        percent = min(100, (current_seconds / duration) * 100)
                        progress_callback(percent)

                # Render progress-like lines dynamically with carriage return.
                is_progress_like = any(tok in line for tok in ("frame=", "fps=", "time=", "speed=", "bitrate="))
                if is_progress_like:
                    pad = " " * max(0, last_progress_len - len(line))
                    sys.stdout.write("\r" + line + pad)
                    sys.stdout.flush()
                    progress_line_active = True
                    last_progress_len = len(line)
                else:
                    if progress_line_active:
                        sys.stdout.write("\n")
                        progress_line_active = False
                        last_progress_len = 0
                    sys.stdout.write(line + "\n")
                    sys.stdout.flush()
            else:
                carry += ch

        if process.stdout is not None:
            process.stdout.close()
        return_code = process.wait()
        CURRENT_FFMPEG_PROCESS = None
        if progress_line_active:
            sys.stdout.write("\n")

        if return_code != 0:
            error_tail = "\n".join(recent_lines)
            raise VideoProcessingError(
                f"FFmpeg {operation} failed with return code {return_code}\n"
                f"--- Last FFmpeg output ---\n{error_tail}"
            )
        return return_code
    except VideoProcessingError:
        raise
    except FileNotFoundError:
        raise VideoProcessingError("FFmpeg not found. Please ensure FFmpeg is installed and in PATH")
    except Exception as e:
        raise VideoProcessingError(f"Unexpected error during {operation}: {e}")

def get_char_width(char):
    """Returns 2 for wide (CJK) characters, 1 otherwise."""
    # East Asian Widths: F (Fullwidth), W (Wide), A (Ambiguous - treat as Wide)
    w = unicodedata.east_asian_width(char)
    return 2 if w in ('F', 'W', 'A') else 1

def sanitize_title(raw_title, remove_hashtags=True, keep_emoji=True):
    """
    Normalize title text for burn-in.
    - Decodes unicode escape sequences to real characters (including emoji).
    - Optionally strips hashtags and trailing hashtag segment.
    Returns the cleaned title text.
    """
    title = raw_title or ""
    # Handle literal unicode escapes (e.g. "\\ud83d\\ude31") if present.
    if "\\u" in title:
        try:
            title = title.encode("utf-8").decode("unicode_escape")
        except Exception:
            pass

    if remove_hashtags:
        # Remove hashtags and everything after them (split on # preceded by optional space)
        title = re.split(r'\s*#', title)[0]
    if not keep_emoji:
        emoji_pattern = re.compile("["
            u"\U0001F600-\U0001F64F"  # emoticons
            u"\U0001F300-\U0001F5FF"  # symbols & pictographs
            u"\U0001F680-\U0001F6FF"  # transport & map
            u"\U0001F1E0-\U0001F1FF"  # flags
            u"\U00002702-\U000027B0"
            u"\U000024C2-\U0001F251"
            u"\U0001F900-\U0001F9FF"  # supplemental symbols
            u"\U0001FA00-\U0001FA6F"  # chess symbols
            u"\U0001FA70-\U0001FAFF"  # symbols and pictographs extended-A
            u"\U00002600-\U000026FF"  # misc symbols
            u"\U00002300-\U000023FF"  # misc technical
            u"\u200D"                 # zero width joiner
            u"\uFE0F"                 # variation selector-16
            "]+", flags=re.UNICODE)
        title = emoji_pattern.sub('', title)
    # Normalize punctuation/spaces that often cause missing glyph fallback in ASS fonts.
    title = title.translate(str.maketrans({
        "\u2010": "-",  # hyphen
        "\u2011": "-",  # non-breaking hyphen
        "\u2012": "-",  # figure dash
        "\u2013": "-",  # en dash
        "\u2014": "-",  # em dash
        "\u2015": "-",  # horizontal bar
        "\u2212": "-",  # minus sign
        "\u00A0": " ",  # non-breaking space
        "\u2018": "'",  # left single quote
        "\u2019": "'",  # right single quote
        "\u201C": "\"", # left double quote
        "\u201D": "\"", # right double quote
        "\u2026": "...",# ellipsis
    }))
    title = re.sub(r'\s+', ' ', title)
    return title.strip()

def find_title_json_file(video_path, subtitle_path, json_suffix, remove_hashtags=True, keep_emoji=True):
    """
    Find the associated JSON file containing the title.
    Looks for (in order):
    - {subtitle_basename}{json_suffix}.txt
    - {subtitle_basename}{json_suffix}.json
    - {subtitle_basename}.txt
    - {subtitle_basename}.json
    Returns: (json_path, sanitized_title) or (None, None)
    """
    if not subtitle_path or subtitle_path.startswith("embedded:"):
        return None, None

    srt_basename = os.path.splitext(subtitle_path)[0]

    candidate_bases = [f"{srt_basename}{json_suffix or ''}"]
    if json_suffix:
        candidate_bases.append(srt_basename)

    seen = set()
    candidate_paths = []
    for base in candidate_bases:
        for ext in (".txt", ".json"):
            path = f"{base}{ext}"
            if path not in seen:
                seen.add(path)
                candidate_paths.append(path)

    for json_path in candidate_paths:
        if not os.path.exists(json_path):
            continue
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            raw_title = data.get('title', '')
            if raw_title:
                return json_path, sanitize_title(raw_title, remove_hashtags=remove_hashtags, keep_emoji=keep_emoji)
        except Exception as e:
            debug_print(f"Failed to parse JSON title file {json_path}: {e}")
            continue
    return None, None

def smart_wrap_text(text, limit):
    """
    Advanced 'Human-Like' Text Wrapping.
    Features:
    - Mixed CJK/Latin support (Width based).
    - Kinsoku Shori (Prohibited line starts: closing punctuation).
    - Punctuation Priority (Prefers breaking at sentences/clauses).
    - Orphan Fighter (prevents very short last lines).
    """
    if not text: return []
    
    # 1. Tokenize (Split into atomic units)
    # English -> Words, CJK -> Words/Chars. 
    # For simplicity in mixed text, we split by spaces first, then handle CJK inside words if needed?
    # Actually, a better tokenizer for mixed text:
    # - CJK chars are individual tokens.
    # - Latin sequences are tokens.
    tokens = []
    current_token = ""
    
    # Prohibited Line Starts (Kinsoku Shori)
    prohibited_starts = set("!%),.:;?]}¢°'\"†‡℃、。〉》」』】〕〗〙〛！），．：；？］｝")
    
    for char in text:
        cw = get_char_width(char)
        is_cjk = cw == 2
        is_space = char == ' '
        
        if is_space:
            if current_token: 
                tokens.append({'text': current_token, 'width': sum(get_char_width(c) for c in current_token), 'type': 'word'})
                current_token = ""
            tokens.append({'text': ' ', 'width': 1, 'type': 'space'})
        elif is_cjk:
            if current_token:
                tokens.append({'text': current_token, 'width': sum(get_char_width(c) for c in current_token), 'type': 'word'})
                current_token = ""
            tokens.append({'text': char, 'width': 2, 'type': 'cjk'})
        else:
            current_token += char
            
    if current_token:
        tokens.append({'text': current_token, 'width': sum(get_char_width(c) for c in current_token), 'type': 'word'})

    # 2. Line Building with Backtracking
    lines = []
    current_line_tokens = []
    current_line_width = 0
    
    i = 0
    while i < len(tokens):
        token = tokens[i]
        
        # Check if adding this token exceeds limit
        if current_line_width + token['width'] <= limit:
            current_line_tokens.append(token)
            current_line_width += token['width']
            i += 1
            continue

        # Guard: single token longer than limit when line is empty.
        # Hard-wrap the token to avoid infinite loops (e.g., "whyyyyyyyy...").
        if current_line_width == 0 and token['width'] > limit and token['type'] != 'space':
            chunk = ""
            chunk_w = 0
            for ch in token['text']:
                w = get_char_width(ch)
                if chunk_w + w > limit and chunk:
                    lines.append(chunk)
                    chunk = ch
                    chunk_w = w
                else:
                    chunk += ch
                    chunk_w += w
            if chunk:
                lines.append(chunk)
            i += 1
            continue
            
        # --- Algorithm: LINE FULL, DECIDE WHERE TO BREAK ---
        
        # Candidate 1: Break exactly here (before this token)
        # Check Kinsoku Shori: Can we start a new line with this token?
        # If token is 'space', we just discard it and break.
        if token['type'] == 'space':
            lines.append("".join(t['text'] for t in current_line_tokens))
            current_line_tokens = []
            current_line_width = 0
            i += 1 # Skip the space
            continue
            
        first_char = token['text'][0]
        if first_char in prohibited_starts:
            # Kinsoku Violation! We cannot start new line here.
            # We MUST drag the previous token down to join this one.
            if current_line_tokens:
                last_token = current_line_tokens.pop()
                current_line_width -= last_token['width']
                i -= 1 # Re-process the popped token (it will be pushed to next line loop)
                
                # FIX: We must COMMIT the current line now, otherwise we loop forever trying to add the popped token back to this line.
                # If popping made the line empty (it was a 1-token line), we can't commit empty.
                if current_line_tokens:
                    lines.append("".join(t['text'] for t in current_line_tokens))
                    current_line_tokens = []
                    current_line_width = 0
                    continue # Restart loop, 'i' points to the popped token
                else:
                     # Special case: The line only had 1 token, and the NEXT one is prohibited start.
                     # We can't drag the single token down (nothing left).
                     # We must FORCE keep them together (violate limit).
                     # So we add the popped token back, ADD the current prohibited token, and THEN break.
                     current_line_tokens.append(last_token) # Put it back
                     current_line_tokens.append(token)      # Add the prohibited one
                     lines.append("".join(t['text'] for t in current_line_tokens))
                     current_line_tokens = []
                     current_line_width = 0
                     i += 2 # Skip both (we processed last_token again + current token)
                     continue
            else:
                 # Line empty, just push it (limit violation inevitable)
                 lines.append(token['text']) # Should rarely happen
                 i += 1
        else:
            # Safe to break here.
            # Optimization: Punctuation Priority (Backtrack lookahead)
            # If the break point is "weak" (mid-sentence), check if we passed a "Strong" break recently (comma/period).
            # e.g. "Hello world, how represent|ation" -> Break at comma instead?
            
            # Heuristic: If we are breaking at a space (weak), look back to see if we passed a Sentence Ender recently.
            # Only do this if the line is already reasonably long (avoid breaking very short lines).
            
            strong_break_found_idx = -1
            if current_line_width > limit * 0.7: # Only optimize if line is full-ish
                # Look back at the last ~8 tokens (arbitrary window)
                lookback_range = range(len(current_line_tokens) - 1, max(-1, len(current_line_tokens) - 10), -1)
                for idx in lookback_range:
                    t_text = current_line_tokens[idx]['text']
                    # Check if token ends with strong punctuation
                    if t_text and t_text[-1] in ".,;:!?":
                        # Found a strong break!
                        # But wait, is it *too* far back? (Leaving a tiny line?)
                        # We handled that with the loop range limited to 10 tokens.
                        strong_break_found_idx = idx
                        break
            
            if strong_break_found_idx != -1:
                # Break at the strong point!
                keep_tokens = current_line_tokens[:strong_break_found_idx+1]
                reject_tokens = current_line_tokens[strong_break_found_idx+1:]
                
                # Commit the keepers
                lines.append("".join(t['text'] for t in keep_tokens))
                
                # Rewind: The rejected tokens need to be processed again.
                # We simply move 'i' back by the number of rejected tokens.
                # AND we must not forget the *current* token 'token' (at index i) which caused the overflow.
                # Current loop flow: 'token' is *not* in current_line_tokens. It is waiting at 'i'.
                # So if we reject 3 tokens, we need to process those 3 + 'token'.
                # So we decrement i by len(reject_tokens).
                i -= len(reject_tokens)
                
                current_line_tokens = []
                current_line_width = 0
                # Continue loop, re-reading from new 'i'
                continue
            
            # No better break found, just break here as normal
            lines.append("".join(t['text'] for t in current_line_tokens))
            current_line_tokens = []
            current_line_width = 0
            # Token 'i' will be added in next iteration
            
    # Flush remaining
    if current_line_tokens:
        lines.append("".join(t['text'] for t in current_line_tokens))
        
    # 3. Orphan Fighting (Balancing)
    # If last line is remarkably short (< 20% limit) and we have multiple lines, 
    # try to pull words from prev line.
    if len(lines) > 1:
        last_line = lines[-1]
        last_width = sum(get_char_width(c) for c in last_line)
        if last_width < limit * 0.2:
            # Attempt balance? (Simple version: Not strictly required if wrapping is good, skipping for stability)
            pass

    return lines

def _collapse_repeats(text, min_run, suffix="..."):
    if not text or min_run <= 1:
        return text
    pattern = re.compile(r"(.)\1{" + str(max(1, min_run - 1)) + r",}")
    def repl(m):
        ch = m.group(1)
        return (ch * 3) + suffix
    return pattern.sub(repl, text)

def _is_spammy_line(text, ratio, min_len):
    if not text:
        return False
    chars = [c for c in text if not c.isspace()]
    if len(chars) < min_len:
        return False
    top = Counter(chars).most_common(1)[0][1]
    return (top / len(chars)) >= ratio

def sanitize_subtitle_line(text, repeat_min_run, repeat_ratio, truncate_suffix="..."):
    if not text:
        return ""
    cleaned = _collapse_repeats(text, repeat_min_run, truncate_suffix)
    if _is_spammy_line(cleaned, repeat_ratio, repeat_min_run):
        return ""
    return cleaned

def hex_to_libass_color(hex_color):
    if not hex_color or not hex_color.startswith("#"): return "&H000000"
    hex_val = hex_color.lstrip('#')
    if len(hex_val) != 6: return "&H000000"
    r, g, b = tuple(int(hex_val[i:i+2], 16) for i in (0, 2, 4))
    return f"&H{b:02X}{g:02X}{r:02X}"

def alpha_to_libass_alpha(alpha_val):
    return f"&H{alpha_val:02X}"

def create_temporary_ass_file(srt_path, options, target_res=None):
    global CURRENT_TEMP_FILE
    try:
        with open(srt_path, 'r', encoding='utf-8', errors='replace') as f:
            srt_content = f.read()
    except Exception as e:
        print(f"[ERROR] Could not read SRT file {srt_path}: {e}")
        return None

    # Determine PlayRes from target_res or default to 1920x1080
    play_res_x, play_res_y = target_res if target_res else (1920, 1080)

    font_name = options.get('subtitle_font', DEFAULT_SUBTITLE_FONT)
    font_size = options.get('subtitle_font_size', DEFAULT_SUBTITLE_FONT_SIZE)
    bold_flag = "-1" if options.get('subtitle_bold', DEFAULT_SUBTITLE_BOLD) else "0"
    italic_flag = "-1" if options.get('subtitle_italic', DEFAULT_SUBTITLE_ITALIC) else "0"
    underline_flag = "-1" if options.get('subtitle_underline', DEFAULT_SUBTITLE_UNDERLINE) else "0"
    margin_v = options.get('subtitle_margin_v', DEFAULT_SUBTITLE_MARGIN_V)
    margin_l = options.get('subtitle_margin_l', DEFAULT_SUBTITLE_MARGIN_L)
    margin_r = options.get('subtitle_margin_r', DEFAULT_SUBTITLE_MARGIN_R)
    seam_h_offset = options.get('subtitle_seam_h_offset', DEFAULT_SUBTITLE_SEAM_H_OFFSET)
    seam_v_offset = options.get('subtitle_seam_v_offset', DEFAULT_SUBTITLE_SEAM_V_OFFSET)
    align_map = {"top": 8, "middle": 5, "bottom": 2, "seam": 2}
    alignment = align_map.get(options.get('subtitle_alignment', 'bottom'), 2)
    reformat_subs = options.get('reformat_subtitles', DEFAULT_REFORMAT_SUBTITLES)
    try:
        user_wrap_limit = int(options.get('wrap_limit', DEFAULT_WRAP_LIMIT))
    except (ValueError, TypeError):
        user_wrap_limit = int(DEFAULT_WRAP_LIMIT)
        
    try:
        m_v_offset = float(margin_v)
    except (ValueError, TypeError):
        m_v_offset = 0.0
        
    # --- Dynamic Wrap Limit Calculation ---
    try:
        f_size = float(font_size)
        m_l = float(margin_l)
        m_r = float(margin_r)
    except (ValueError, TypeError):
        f_size, m_l, m_r = 32.0, 50.0, 50.0

    available_width = play_res_x - m_l - m_r
    # Heuristic: 1 "Unit" (Narrow char) is approx 0.5 * FontSize pixels wide.
    # Wide char (CJK) is 2 Units (~1.0 * FontSize).
    unit_width_px = f_size * 0.5
    if unit_width_px < 1: unit_width_px = 10
    
    calculated_limit = int(available_width / unit_width_px)
    
    # Use the stricter limit to prevent runoff, but don't go below a silly minimum (e.g. 10 chars)
    # We want to respect the user's limit unless the physical geometry forbids it.
    final_limit = min(user_limit for user_limit in [user_wrap_limit, calculated_limit] if user_limit > 5)
    
    # print(f"[DEBUG] Subtitle Wrap: User={user_wrap_limit}, Calc={calculated_limit} (W={available_width}), Final={final_limit}")
    try:
        max_lines = int(options.get('subtitle_max_lines', DEFAULT_SUBTITLE_MAX_LINES))
    except (ValueError, TypeError):
        max_lines = int(DEFAULT_SUBTITLE_MAX_LINES)
    try:
        repeat_min_run = int(options.get('subtitle_repeat_min_run', DEFAULT_SUBTITLE_REPEAT_MIN_RUN))
    except (ValueError, TypeError):
        repeat_min_run = int(DEFAULT_SUBTITLE_REPEAT_MIN_RUN)
    try:
        repeat_ratio = float(options.get('subtitle_repeat_ratio', DEFAULT_SUBTITLE_REPEAT_RATIO))
    except (ValueError, TypeError):
        repeat_ratio = float(DEFAULT_SUBTITLE_REPEAT_RATIO)
    truncate_suffix = "..."

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
        f"{outline_width},{shadow_offset_y},{alignment},{margin_l},{margin_r},{margin_v},1"
    )

    header = f"""[Script Info]
Title: Corrected Single-Layer Subtitle File
ScriptType: v4.00+
WrapStyle: 0
PlayResX: {play_res_x}
PlayResY: {play_res_y}
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
{style_main}
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    dialogue_lines = []
    # Updated Regex to handle both comma and period in timestamps
    srt_blocks = re.findall(r'(\d+)\s*\n(\d{2}:\d{2}:\d{2}[.,]\d{3}) --> (\d{2}:\d{2}:\d{2}[.,]\d{3})\s*\n(.*?)(?=\n\n|\Z)', srt_content, re.DOTALL)
    for block in srt_blocks:
        _, start_time, end_time, text = block
        clean_text = re.sub(r'<[^>]+>', '', text)
        start_ass = start_time.replace(',', '.')[:-1]
        end_ass = end_time.replace(',', '.')[:-1]
        if reformat_subs:
            single_line_text = ' '.join(clean_text.strip().split())
            single_line_text = sanitize_subtitle_line(single_line_text, repeat_min_run, repeat_ratio, truncate_suffix=truncate_suffix)
            if not single_line_text:
                continue
            wrapped_lines = smart_wrap_text(single_line_text, limit=final_limit)
            if max_lines > 0 and len(wrapped_lines) > max_lines:
                wrapped_lines = wrapped_lines[:max_lines]
                last = wrapped_lines[-1].rstrip()
                if len(last) + len(truncate_suffix) > final_limit:
                    last = last[:max(0, final_limit - len(truncate_suffix))]
                wrapped_lines[-1] = last + truncate_suffix
            text_ass = '\\N'.join(wrapped_lines)
        else:
            raw_lines = [line.strip() for line in clean_text.splitlines()]
            cleaned_lines = [
                sanitize_subtitle_line(line, repeat_min_run, repeat_ratio, truncate_suffix=truncate_suffix)
                for line in raw_lines
            ]
            cleaned_lines = [line for line in cleaned_lines if line]
            if not cleaned_lines:
                continue
            if max_lines > 0 and len(cleaned_lines) > max_lines:
                cleaned_lines = cleaned_lines[:max_lines]
                last = cleaned_lines[-1].rstrip()
                if len(last) + len(truncate_suffix) > final_limit:
                    last = last[:max(0, final_limit - len(truncate_suffix))]
                cleaned_lines[-1] = last + truncate_suffix
            text_ass = '\\N'.join(cleaned_lines)

        tags = (
            f"\\1a{alpha_to_libass_alpha(fill_alpha_val)}"
            f"\\3a{alpha_to_libass_alpha(outline_alpha_val)}"
            f"\\4a{alpha_to_libass_alpha(shadow_alpha_val)}"
            f"\\xshad{shadow_offset_x}"
            f"\\yshad{shadow_offset_y}"
            f"\\blur{shadow_blur}"
        )
        pos_override = ""
        # Calculate horizontal center based on user's desired "Active Box"
        cx = (m_l + (play_res_x - m_r)) / 2
        
        align_mode = options.get("subtitle_alignment", "bottom")
        if align_mode == "seam" and "calculated_pos" in options:
            x, y = options["calculated_pos"]
            try:
                ho = float(seam_h_offset)
                vo = float(seam_v_offset)
            except (ValueError, TypeError):
                ho = 0.0
                vo = 0.0
            x = x + ho
            y = y - vo
            pos_override = fr"{{\an5\pos({x:.1f},{y:.1f})}}"
        elif align_mode == "top":
            cy = m_v_offset
            pos_override = fr"{{\an8\pos({cx:.1f},{cy:.1f})}}"
        elif align_mode == "middle":
            cy = (play_res_y / 2) + m_v_offset
            pos_override = fr"{{\an5\pos({cx:.1f},{cy:.1f})}}"
        elif align_mode == "bottom":
            cy = play_res_y - m_v_offset
            pos_override = fr"{{\an2\pos({cx:.1f},{cy:.1f})}}"

        dialogue_lines.append(f"Dialogue: 0,{start_ass},{end_ass},Main,,0,0,0,,{{{tags}}}{pos_override}{text_ass}")

    full_ass_content = header + "\n".join(dialogue_lines)
    filename = f"vid_temp_sub_{int(time.time() * 1000)}.ass"
    filepath = os.path.join(get_temp_work_dir(), filename)
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(full_ass_content)
        CURRENT_TEMP_FILE = filepath
        register_temp_file(filepath)
        debug_print(f"Created temporary subtitle file: {filepath}")
        return filepath
    except Exception as e:
        print(f"[ERROR] Could not create temporary ASS file: {e}")
        return None

def create_temporary_ass_passthrough_file(ass_path):
    global CURRENT_TEMP_FILE
    if not ass_path or not os.path.exists(ass_path):
        return None
    try:
        with open(ass_path, "r", encoding="utf-8", errors="replace") as src:
            ass_content = src.read()
    except Exception as e:
        print(f"[ERROR] Could not read ASS file {ass_path}: {e}")
        return None

    filename = f"vid_temp_sub_passthrough_{int(time.time() * 1000)}.ass"
    filepath = os.path.join(get_temp_work_dir(), filename)
    try:
        with open(filepath, "w", encoding="utf-8") as dst:
            dst.write(ass_content)
        CURRENT_TEMP_FILE = filepath
        register_temp_file(filepath)
        debug_print(f"Created temporary passthrough ASS file: {filepath}")
        return filepath
    except Exception as e:
        print(f"[ERROR] Could not create temporary passthrough ASS file: {e}")
        return None

def _find_ass_section_bounds(lines, section_names):
    wanted = {name.lower() for name in section_names}
    start = None
    for i, line in enumerate(lines):
        stripped = line.strip().lower()
        if stripped in wanted:
            start = i
            break
    if start is None:
        return None, None
    end = len(lines)
    for j in range(start + 1, len(lines)):
        stripped = lines[j].strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            end = j
            break
    return start, end

def create_merged_ass_for_nvencc(sub_ass_path, title_ass_path):
    global CURRENT_TEMP_FILE
    if sub_ass_path and not title_ass_path:
        return sub_ass_path
    if title_ass_path and not sub_ass_path:
        return title_ass_path
    if not sub_ass_path or not title_ass_path:
        return None

    try:
        with open(sub_ass_path, "r", encoding="utf-8", errors="replace") as sf:
            sub_lines = sf.read().splitlines()
        with open(title_ass_path, "r", encoding="utf-8", errors="replace") as tf:
            title_lines = tf.read().splitlines()
    except Exception as e:
        print(f"[ERROR] Could not read ASS inputs for NVEncC merge: {e}")
        return sub_ass_path

    title_style_lines = [ln for ln in title_lines if ln.startswith("Style: ")]
    title_event_lines = [ln for ln in title_lines if ln.startswith("Dialogue: ")]
    if not title_style_lines and not title_event_lines:
        return sub_ass_path

    style_start, style_end = _find_ass_section_bounds(sub_lines, {"[v4+ styles]", "[v4 styles]"})
    if style_start is None:
        return sub_ass_path

    event_start, event_end = _find_ass_section_bounds(sub_lines, {"[events]"})
    if event_start is None:
        return sub_ass_path

    merged_lines = list(sub_lines)

    insert_at_styles = style_end
    for style_line in title_style_lines:
        if style_line not in merged_lines:
            merged_lines.insert(insert_at_styles, style_line)
            insert_at_styles += 1

    if insert_at_styles != style_end and event_start >= style_end:
        shift = insert_at_styles - style_end
        event_start += shift
        event_end += shift

    insert_at_events = event_end
    for event_line in title_event_lines:
        merged_lines.insert(insert_at_events, event_line)
        insert_at_events += 1

    filename = f"vid_temp_sub_merged_{int(time.time() * 1000)}.ass"
    filepath = os.path.join(get_temp_work_dir(), filename)
    try:
        with open(filepath, "w", encoding="utf-8") as out_f:
            out_f.write("\n".join(merged_lines) + "\n")
        CURRENT_TEMP_FILE = filepath
        register_temp_file(filepath)
        debug_print(f"Created merged ASS for NVEncC: {filepath}")
        return filepath
    except Exception as e:
        print(f"[ERROR] Could not create merged ASS file: {e}")
        return sub_ass_path

def create_title_ass_file(title_text, options, target_res=None):
    """
    Creates a temporary ASS file containing a single title entry.
    Uses title-specific styling options (title_font, title_font_size, etc.)
    Returns path to temp ASS file.
    """
    global CURRENT_TEMP_FILE
    
    # Determine PlayRes from target_res or default to 1920x1080
    play_res_x, play_res_y = target_res if target_res else (1920, 1080)
    
    # Get title-specific styling options
    font_name = options.get('title_font', DEFAULT_TITLE_FONT)
    font_size = options.get('title_font_size', DEFAULT_TITLE_FONT_SIZE)
    bold_flag = "-1" if options.get('title_bold', DEFAULT_TITLE_BOLD) else "0"
    italic_flag = "-1" if options.get('title_italic', DEFAULT_TITLE_ITALIC) else "0"
    underline_flag = "-1" if options.get('title_underline', DEFAULT_TITLE_UNDERLINE) else "0"
    margin_v = options.get('title_margin_v', DEFAULT_TITLE_MARGIN_V)
    margin_l = options.get('title_margin_l', DEFAULT_TITLE_MARGIN_L)
    margin_r = options.get('title_margin_r', DEFAULT_TITLE_MARGIN_R)
    align_map = {"top": 8, "middle": 5, "bottom": 2}
    alignment = align_map.get(options.get('title_alignment', 'top'), 8)
    
    fill_color_hex = options.get('title_fill_color', DEFAULT_TITLE_FILL_COLOR)
    fill_alpha_val = options.get('title_fill_alpha', DEFAULT_TITLE_FILL_ALPHA)
    outline_color_hex = options.get('title_outline_color', DEFAULT_TITLE_OUTLINE_COLOR)
    outline_alpha_val = options.get('title_outline_alpha', DEFAULT_TITLE_OUTLINE_ALPHA)
    outline_width = float(options.get('title_outline_width', DEFAULT_TITLE_OUTLINE_WIDTH))
    shadow_color_hex = options.get('title_shadow_color', DEFAULT_TITLE_SHADOW_COLOR)
    shadow_alpha_val = options.get('title_shadow_alpha', DEFAULT_TITLE_SHADOW_ALPHA)
    shadow_offset_y = float(options.get('title_shadow_offset_y', DEFAULT_TITLE_SHADOW_OFFSET_Y))
    
    # Get timing
    start_time = options.get('title_start_time', DEFAULT_TITLE_START_TIME)
    end_time = options.get('title_end_time', DEFAULT_TITLE_END_TIME)
    
    # Convert times to ASS format (h:mm:ss.cc)
    def time_to_ass(time_str):
        # Input format: HH:MM:SS.cc or H:MM:SS.cc
        parts = time_str.split(':')
        if len(parts) == 3:
            h = int(parts[0])
            m = int(parts[1])
            s_parts = parts[2].split('.')
            s = int(s_parts[0])
            cs = int(s_parts[1][:2]) if len(s_parts) > 1 else 0
            return f"{h}:{m:02d}:{s:02d}.{cs:02d}"
        return "0:00:00.00"
    
    start_ass = time_to_ass(start_time)
    end_ass = time_to_ass(end_time)
    
    # Build style
    style_title = (
        f"Style: __VID_TITLE__,{font_name},{font_size},"
        f"{hex_to_libass_color(fill_color_hex)},"
        "&HFF000000,"
        f"{hex_to_libass_color(outline_color_hex)},"
        f"{hex_to_libass_color(shadow_color_hex)},"
        f"{bold_flag},{italic_flag},{underline_flag},0,100,100,0,0,1,"
        f"{outline_width},{shadow_offset_y},{alignment},{margin_l},{margin_r},{margin_v},1"
    )
    
    header = f"""[Script Info]
Title: Title Burn Overlay
ScriptType: v4.00+
WrapStyle: 0
PlayResX: {play_res_x}
PlayResY: {play_res_y}
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
{style_title}
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    
    # Calculate position based on alignment
    try:
        m_v_offset = float(margin_v)
        m_l = float(margin_l)
        m_r = float(margin_r)
    except (ValueError, TypeError):
        m_v_offset, m_l, m_r = 50.0, 50.0, 50.0
    
    # Calculate horizontal center
    cx = (m_l + (play_res_x - m_r)) / 2
    
    align_mode = options.get("title_alignment", "top")
    if align_mode == "top":
        cy = m_v_offset
        pos_override = fr"{{\an8\pos({cx:.1f},{cy:.1f})}}"
    elif align_mode == "middle":
        cy = (play_res_y / 2) + m_v_offset
        pos_override = fr"{{\an5\pos({cx:.1f},{cy:.1f})}}"
    else:  # bottom
        cy = play_res_y - m_v_offset
        pos_override = fr"{{\an2\pos({cx:.1f},{cy:.1f})}}"
    
    # Escape special characters in title
    title_escaped = title_text.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")
    
    # Build dialogue line
    dialogue = f"Dialogue: 0,{start_ass},{end_ass},__VID_TITLE__,,0,0,0,,{pos_override}{title_escaped}"
    
    full_ass_content = header + dialogue
    filename = f"vid_temp_title_{int(time.time() * 1000)}.ass"
    filepath = os.path.join(get_temp_work_dir(), filename)
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(full_ass_content)
        register_temp_file(filepath)
        debug_print(f"Created temporary title file: {filepath}")
        return filepath
    except Exception as e:
        print(f"[ERROR] Could not create temporary title ASS file: {e}")
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

def compute_original_target_resolution(res_key, info):
    if not res_key:
        return info["width"], info["height"]
    res_key_norm = res_key.lower()
    if res_key_norm == "original":
        return info["width"], info["height"]
    width_map_landscape = {"720p": 1280, "1080p": 1920, "2160p": 3840, "4320p": 7680, "hd": 1920, "4k": 3840, "8k": 7680}
    width_map_portrait = {"720p": 720, "1080p": 1080, "2160p": 2160, "4320p": 4320, "hd": 1080, "4k": 2160, "8k": 4320}
    target_w = width_map_landscape.get(res_key_norm) if info["width"] >= info["height"] else width_map_portrait.get(res_key_norm)
    if not target_w:
        return None, None
    target_h = int(target_w * info["height"] / info["width"])
    return (target_w // 2) * 2, (target_h // 2) * 2

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

def get_video_chapters(file_path):
    """
    Extracts chapter markers from a video file using ffprobe.
    Returns a list of dicts: [{'start': 0.0, 'end': 10.0, 'title': 'Chapter 1'}, ...]
    """
    cmd = [FFPROBE_CMD, "-v", "error", "-show_chapters", "-print_format", "json", file_path]
    try:
        result = safe_ffprobe(cmd, "chapter extraction")
        data = json.loads(result.stdout)
        chapters = []
        for i, ch in enumerate(data.get("chapters", [])):
            start = float(ch.get("start_time", 0))
            end = float(ch.get("end_time", 0))
            tags = ch.get("tags", {})
            title = tags.get("title", "").strip() or f"Chapter {i+1}"
            chapters.append({"start_time": start, "end_time": end, "title": title})
        return chapters
    except Exception as e:
        print(f"[WARN] Could not extract chapters for {file_path}: {e}")
        return []

def extract_embedded_subtitle(video_path, subtitle_index, temp_dir=None):
    temp_subtitle_path = ""
    try:
        fd, temp_subtitle_path = tempfile.mkstemp(
            suffix=".srt",
            prefix="vid_temp_sub_extract_",
            dir=temp_dir if temp_dir and os.path.isdir(temp_dir) else None
        )
        os.close(fd)
        register_temp_file(temp_subtitle_path)
        cmd = [FFMPEG_CMD, '-y', '-hide_banner', '-i', video_path, '-map', f'0:s:{subtitle_index}', '-c:s', 'srt', temp_subtitle_path]
        print(f"[INFO] Extracting embedded subtitle stream {subtitle_index}...")
        subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30, env=env)
        if os.path.exists(temp_subtitle_path) and os.path.getsize(temp_subtitle_path) > 0:
            return temp_subtitle_path
        else:
            cleanup_single_temp_file(temp_subtitle_path)
            return None
    except subprocess.CalledProcessError:
        cleanup_single_temp_file(temp_subtitle_path)
        return None
    except Exception:
        cleanup_single_temp_file(temp_subtitle_path)
        return None

def split_srt_file(srt_file_path, output_path, chapter_start_sec, chapter_end_sec):
    try:
        with open(srt_file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
    except Exception as e:
        print(f"[ERROR] Could not read SRT {srt_file_path}: {e}")
        return False
        
    def parse_srt_time(t_str):
        h, m, s_ms = t_str.strip().split(':')
        s, ms = s_ms.replace('.', ',').split(',')
        return int(h)*3600 + int(m)*60 + int(s) + int(ms.ljust(3, '0')[:3])/1000.0

    def format_srt_time(sec):
        sec = max(0, sec)
        h = int(sec // 3600)
        m = int((sec % 3600) // 60)
        s = int(sec % 60)
        ms = int(round((sec % 1) * 1000))
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    blocks = content.strip().split('\n\n')
    new_blocks = []
    idx = 1
    end_limit = chapter_end_sec if chapter_end_sec is not None else float('inf')
    
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) >= 3:
            time_line = lines[1]
            if ' --> ' in time_line:
                start_str, end_str = time_line.split(' --> ')
                try:
                    start_sec = parse_srt_time(start_str)
                    end_sec = parse_srt_time(end_str)
                    
                    if start_sec >= end_limit or end_sec <= chapter_start_sec:
                        continue
                        
                    new_start = start_sec - chapter_start_sec
                    new_end = end_sec - chapter_start_sec
                    
                    new_start = max(0, new_start)
                    chapter_duration = end_limit - chapter_start_sec
                    new_end = min(new_end, chapter_duration) if chapter_duration != float('inf') else new_end
                    
                    if new_start >= new_end:
                        continue
                    
                    text = '\n'.join(lines[2:])
                    new_blocks.append(f"{idx}\n{format_srt_time(new_start)} --> {format_srt_time(new_end)}\n{text}")
                    idx += 1
                except Exception as e:
                    debug_print(f"Skipping block due to parse error: {e}")
        
    if not new_blocks:
        return False
        
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("\n\n".join(new_blocks) + "\n\n")
        return True
    except Exception as e:
        print(f"[ERROR] Could not write split SRT {output_path}: {e}")
        return False

def get_bitrate(output_resolution_key, framerate, is_hdr, source_height=None, source_width=None):
    # Revised Defaults (roughly 50% of previous high-quality defaults)
    BITRATES = {
        "SDR_NORMAL_FPS": {"720p": 5000, "1080p": 8000, "2160p": 45000, "4320p": 160000},
        "SDR_HIGH_FPS":   {"720p": 7500, "1080p": 12000, "2160p": 68000, "4320p": 240000},
        "HDR_NORMAL_FPS": {"720p": 6000, "1080p": 10000, "2160p": 56000, "4320p": 200000},
        "HDR_HIGH_FPS":   {"720p": 9000, "1080p": 15000, "2160p": 85000, "4320p": 300000}
    }
    fps_category = "HIGH_FPS" if framerate > 40 else "NORMAL_FPS"
    dr_category = "HDR" if is_hdr else "SDR"
    key = f"{dr_category}_{fps_category}"
    # Map old keys for backward compatibility if needed, though we primarily use the new ones now
    res_map = {"mobile": "720p", "hd": "1080p", "4k": "2160p", "8k": "4320p", "original": "original"}
    key_raw = output_resolution_key.lower() if isinstance(output_resolution_key, str) else output_resolution_key
    mapped_key = res_map.get(key_raw, key_raw)
    if mapped_key == "original":
        if source_height:
            if source_height <= 720: mapped_key = "720p"
            elif source_height <= 1080: mapped_key = "1080p"
            elif source_height <= 2160: mapped_key = "2160p"
            else: mapped_key = "4320p"
        else:
            mapped_key = "1080p"
    
    return BITRATES.get(key, {}).get(mapped_key, BITRATES["SDR_NORMAL_FPS"]["1080p"])

def get_job_hash(job_options, extra_data=""):
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
        str(job_options.get('render_by_chapters', False)),
        str(job_options.get('split_subtitles_by_chapter', False)),
        str(job_options.get('use_dynaudnorm', False)),
        job_options.get('dyn_frame_len', ''),
        job_options.get('dyn_gauss_win', ''),
        job_options.get('dyn_peak', ''),
        job_options.get('dyn_max_gain', ''),
        str(job_options.get('use_loudness_war', False)),
        job_options.get('comp_threshold', ''),
        job_options.get('comp_ratio', ''),
        job_options.get('comp_attack', ''),
        job_options.get('comp_release', ''),
        job_options.get('comp_makeup', ''),
        job_options.get('limit_limit', ''),
        str(job_options.get('measure_loudness', False)),
        str(job_options.get('normalize_audio', False)),
        job_options.get('sofa_file', ''),
        job_options.get('subtitle_alignment', ''),
        job_options.get('hybrid_top_aspect', ''),
        job_options.get('hybrid_top_path', ''),
        job_options.get('hybrid_bottom_aspect', ''),
        job_options.get('hybrid_bottom_path', ''),
        job_options.get('subtitle_font', ''),
        job_options.get('subtitle_font_size', ''),
        job_options.get('outline_width', ''),
        job_options.get('shadow_offset_x', ''),
        job_options.get('shadow_offset_y', ''),
        job_options.get('shadow_blur', ''),
        job_options.get('wrap_limit', ''),
        job_options.get('subtitle_max_lines', ''),
        job_options.get('subtitle_margin_l', ''),
        job_options.get('subtitle_margin_r', ''),
        job_options.get('audio_mono', False),
        job_options.get('audio_stereo_downmix', False),
        job_options.get('audio_stereo_sofalizer', False),
        job_options.get('audio_surround_51', False),
        job_options.get('audio_passthrough', False),
        str(job_options.get('use_sharpening', False)),
        job_options.get('sharpening_algo', ''),
        job_options.get('sharpening_strength', ''),
        # Title Burn options for unique hashing
        str(job_options.get('title_burn_enabled', False)),
        job_options.get('title_json_suffix', ''),
        str(job_options.get('title_remove_hashtags', DEFAULT_TITLE_REMOVE_HASHTAGS)),
        str(job_options.get('title_enable_emoji', DEFAULT_TITLE_ENABLE_EMOJI)),
        job_options.get('title_override_text', ''),
        job_options.get('title_start_time', ''),
        job_options.get('title_end_time', ''),
        job_options.get('title_font', ''),
        job_options.get('title_font_size', ''),
        str(job_options.get('title_bold', False)),
        str(job_options.get('title_italic', False)),
        str(job_options.get('title_underline', False)),
        job_options.get('title_alignment', ''),
        job_options.get('title_margin_v', ''),
        job_options.get('title_margin_l', ''),
        job_options.get('title_margin_r', ''),
        job_options.get('title_fill_color', ''),
        str(job_options.get('title_fill_alpha', 0)),
        job_options.get('title_outline_color', ''),
        str(job_options.get('title_outline_alpha', 0)),
        job_options.get('title_outline_width', ''),
        job_options.get('title_shadow_color', ''),
        str(job_options.get('title_shadow_alpha', 0)),
        job_options.get('title_shadow_offset_x', ''),
        job_options.get('title_shadow_offset_y', ''),
        job_options.get('title_shadow_blur', ''),
    ]
    hash_str = "|".join(str(k) for k in keys_to_hash)
    if extra_data:
        hash_str += f"|{extra_data}"
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

class ScrollableFrame(ttk.Frame):
    def __init__(self, container, padding=0, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        self.canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_window = ttk.Frame(self.canvas, padding=padding)

        self.scrollable_window.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )
        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfig(self._window_id, width=e.width)
        )

        self._window_id = self.canvas.create_window((0, 0), window=self.scrollable_window, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel, add="+")

    def _on_mousewheel(self, event):
        if self.winfo_ismapped():
            x, y = self.winfo_pointerxy()
            try:
                widget_under_mouse = self.winfo_containing(x, y)
            except (KeyError, tk.TclError):
                return

            if widget_under_mouse and str(widget_under_mouse).startswith(str(self)):
                if self.scrollbar.get() != (0.0, 1.0):
                    self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

class CollapsiblePane(ttk.Frame):
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

class WorkflowPresetManager:
    def __init__(self, filename="vid.py.preset.json"):
        self.filename = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
        self.presets = {}
        
        # Master dictionary of all possible options and their default values
        self.MASTER_OPTIONS = {
            "resolution": DEFAULT_RESOLUTION,
            "upscale_algo": DEFAULT_UPSCALE_ALGO,
            "output_format": DEFAULT_OUTPUT_FORMAT,
            "video_codec": DEFAULT_VIDEO_CODEC,
            "encoder_backend": DEFAULT_ENCODER_BACKEND,
            "nvenc_superres_mode": DEFAULT_NVENC_SUPERRES_MODE,
            "nvenc_ngx_vsr_quality": DEFAULT_NVENC_NGX_VSR_QUALITY,
            "orientation": DEFAULT_ORIENTATION,
            "render_by_chapters": DEFAULT_RENDER_BY_CHAPTERS,
            "split_subtitles_by_chapter": DEFAULT_SPLIT_SUBTITLES_BY_CHAPTER,
            "max_size_mb": DEFAULT_MAX_SIZE_MB,
            "max_duration": DEFAULT_MAX_DURATION,
            "manual_bitrate": "0",
            "override_bitrate": False,
            "aspect_mode": DEFAULT_ASPECT_MODE,
            "video_offset_x": DEFAULT_VIDEO_OFFSET_X,
            "video_offset_y": DEFAULT_VIDEO_OFFSET_Y,
            "pixelate_multiplier": DEFAULT_PIXELATE_MULTIPLIER,
            "pixelate_brightness": DEFAULT_PIXELATE_BRIGHTNESS,
            "pixelate_saturation": DEFAULT_PIXELATE_SATURATION,
            "blur_sigma": DEFAULT_BLUR_SIGMA,
            "blur_steps": DEFAULT_BLUR_STEPS,
            "horizontal_aspect": DEFAULT_HORIZONTAL_ASPECT,
            "vertical_aspect": DEFAULT_VERTICAL_ASPECT,
            "hybrid_top_aspect": "16:9",
            "hybrid_top_mode": "pad",
            "hybrid_top_path": "",
            "hybrid_bottom_aspect": "4:5",
            "hybrid_bottom_mode": "crop",
            "hybrid_bottom_path": "",
            "fruc": DEFAULT_FRUC,
            "fruc_fps": DEFAULT_FRUC_FPS,
            "generate_log": False,
            "close_gui_on_processing": True,
            "hibernate_when_done": False,
            "burn_subtitles": DEFAULT_BURN_SUBTITLES,
            "use_sharpening": DEFAULT_USE_SHARPENING,
            "sharpening_algo": DEFAULT_SHARPENING_ALGO,
            "sharpening_strength": DEFAULT_SHARPENING_STRENGTH,
            "output_to_subfolders": DEFAULT_OUTPUT_TO_SUBFOLDERS,
            "output_subfolder_by_subtitle": DEFAULT_SUBFOLDER_BY_SUBTITLE,
            "group_by_preset": DEFAULT_GROUP_BY_PRESET,
            "group_by_video": DEFAULT_GROUP_BY_VIDEO,
            "subfolder_override": DEFAULT_SUBFOLDER_OVERRIDE,
            "normalize_audio": DEFAULT_NORMALIZE_AUDIO,
            "use_dynaudnorm": DEFAULT_USE_DYNAUDNORM,
            "dyn_frame_len": DEFAULT_DYNAUDNORM_FRAME_LEN,
            "dyn_gauss_win": DEFAULT_DYNAUDNORM_GAUSS_WIN,
            "dyn_peak": DEFAULT_DYNAUDNORM_PEAK,
            "dyn_max_gain": DEFAULT_DYNAUDNORM_MAX_GAIN,
            "use_loudness_war": DEFAULT_USE_LOUDNESS_WAR,
            "comp_threshold": DEFAULT_COMPRESSOR_THRESHOLD,
            "comp_ratio": DEFAULT_COMPRESSOR_RATIO,
            "comp_attack": DEFAULT_COMPRESSOR_ATTACK,
            "comp_release": DEFAULT_COMPRESSOR_RELEASE,
            "comp_makeup": DEFAULT_COMPRESSOR_MAKEUP,
            "limit_limit": DEFAULT_LIMITER_LIMIT,
            "measure_loudness": DEFAULT_MEASURE_LOUDNESS,
            "loudness_target": DEFAULT_LOUDNESS_TARGET,
            "loudness_range": DEFAULT_LOUDNESS_RANGE,
            "true_peak": DEFAULT_TRUE_PEAK,
            "audio_mono": DEFAULT_AUDIO_MONO,
            "audio_stereo_downmix": DEFAULT_AUDIO_STEREO_DOWNMIX,
            "audio_stereo_sofalizer": DEFAULT_AUDIO_STEREO_SOFALIZER,
            "audio_surround_51": DEFAULT_AUDIO_SURROUND_51,
            "audio_passthrough": DEFAULT_AUDIO_PASSTHROUGH,
            "sofa_file": DEFAULT_SOFA_PATH,
            "lut_file": DEFAULT_LUT_PATH,
            "subtitle_font": DEFAULT_SUBTITLE_FONT,
            "subtitle_font_size": DEFAULT_SUBTITLE_FONT_SIZE,
            "subtitle_alignment": DEFAULT_SUBTITLE_ALIGNMENT,
            "subtitle_bold": DEFAULT_SUBTITLE_BOLD,
            "subtitle_italic": DEFAULT_SUBTITLE_ITALIC,
            "subtitle_underline": DEFAULT_SUBTITLE_UNDERLINE,
            "subtitle_margin_v": DEFAULT_SUBTITLE_MARGIN_V,
            "subtitle_margin_l": DEFAULT_SUBTITLE_MARGIN_L,
            "subtitle_margin_r": DEFAULT_SUBTITLE_MARGIN_R,
            "subtitle_seam_h_offset": DEFAULT_SUBTITLE_SEAM_H_OFFSET,
            "subtitle_seam_v_offset": DEFAULT_SUBTITLE_SEAM_V_OFFSET,
            "fill_color": DEFAULT_FILL_COLOR,
            "fill_alpha": DEFAULT_FILL_ALPHA,
            "outline_color": DEFAULT_OUTLINE_COLOR,
            "outline_alpha": DEFAULT_OUTLINE_ALPHA,
            "outline_width": DEFAULT_OUTLINE_WIDTH,
            "shadow_color": DEFAULT_SHADOW_COLOR,
            "shadow_alpha": DEFAULT_SHADOW_ALPHA,
            "shadow_offset_x": DEFAULT_SHADOW_OFFSET_X,
            "shadow_offset_y": DEFAULT_SHADOW_OFFSET_Y,
            "shadow_blur": DEFAULT_SHADOW_BLUR,
            "reformat_subtitles": DEFAULT_REFORMAT_SUBTITLES,
            "wrap_limit": DEFAULT_WRAP_LIMIT,
            "subtitle_max_lines": DEFAULT_SUBTITLE_MAX_LINES,
            "nvenc_preset": DEFAULT_NVENC_PRESET,
            "nvenc_tune": DEFAULT_NVENC_TUNE,
            "nvenc_profile_sdr": DEFAULT_NVENC_PROFILE_SDR,
            "nvenc_profile_hdr": DEFAULT_NVENC_PROFILE_HDR,
            "nvenc_rc_lookahead": DEFAULT_NVENC_RC_LOOKAHEAD,
            "nvenc_multipass": DEFAULT_NVENC_MULTIPASS,
            "nvenc_spatial_aq": DEFAULT_NVENC_SPATIAL_AQ,
            "nvenc_temporal_aq": DEFAULT_NVENC_TEMPORAL_AQ,
            "nvenc_bframes": DEFAULT_NVENC_BFRAMES,
            "nvenc_b_ref_mode": DEFAULT_NVENC_B_REF_MODE,
            "nvencc_decode_mode": DEFAULT_NVENCC_DECODE_MODE,
            "nvencc_color_tag_mode": DEFAULT_NVENCC_COLOR_TAG_MODE,
            "nvencc_color_prim": DEFAULT_NVENCC_COLOR_PRIM,
            "nvencc_color_transfer": DEFAULT_NVENCC_COLOR_TRANSFER,
            "nvencc_color_matrix": DEFAULT_NVENCC_COLOR_MATRIX,
            "nvencc_output_depth": DEFAULT_NVENCC_OUTPUT_DEPTH,
            "nvencc_strict_no_color_tagging": DEFAULT_NVENCC_STRICT_NO_COLOR_TAGGING,
            "ffmpeg_threads": DEFAULT_FFMPEG_THREADS,
            "ffmpeg_priority": DEFAULT_FFMPEG_PRIORITY,
            "override_bitrate": False,
            "manual_bitrate": "0",
            "output_suffix_override": "",
            # Title Burn defaults
            "title_burn_enabled": DEFAULT_TITLE_BURN_ENABLED,
            "title_json_suffix": DEFAULT_TITLE_JSON_SUFFIX,
            "title_remove_hashtags": DEFAULT_TITLE_REMOVE_HASHTAGS,
            "title_enable_emoji": DEFAULT_TITLE_ENABLE_EMOJI,
            "title_autodetect": DEFAULT_TITLE_AUTODETECT,
            "title_override_text": DEFAULT_TITLE_OVERRIDE_TEXT,
            "title_start_time": DEFAULT_TITLE_START_TIME,
            "title_end_time": DEFAULT_TITLE_END_TIME,
            "title_font": DEFAULT_TITLE_FONT,
            "title_font_size": DEFAULT_TITLE_FONT_SIZE,
            "title_bold": DEFAULT_TITLE_BOLD,
            "title_italic": DEFAULT_TITLE_ITALIC,
            "title_underline": DEFAULT_TITLE_UNDERLINE,
            "title_alignment": DEFAULT_TITLE_ALIGNMENT,
            "title_margin_v": DEFAULT_TITLE_MARGIN_V,
            "title_margin_l": DEFAULT_TITLE_MARGIN_L,
            "title_margin_r": DEFAULT_TITLE_MARGIN_R,
            "title_fill_color": DEFAULT_TITLE_FILL_COLOR,
            "title_fill_alpha": DEFAULT_TITLE_FILL_ALPHA,
            "title_outline_color": DEFAULT_TITLE_OUTLINE_COLOR,
            "title_outline_alpha": DEFAULT_TITLE_OUTLINE_ALPHA,
            "title_outline_width": DEFAULT_TITLE_OUTLINE_WIDTH,
            "title_shadow_color": DEFAULT_TITLE_SHADOW_COLOR,
            "title_shadow_alpha": DEFAULT_TITLE_SHADOW_ALPHA,
            "title_shadow_offset_x": DEFAULT_TITLE_SHADOW_OFFSET_X,
            "title_shadow_offset_y": DEFAULT_TITLE_SHADOW_OFFSET_Y,
            "title_shadow_blur": DEFAULT_TITLE_SHADOW_BLUR
        }
        self.load_presets()

    def load_presets(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r') as f:
                    self.presets = json.load(f)
                return
            except Exception as e:
                print(f"[WARN] Failed to load presets from {self.filename}: {e}. Loading defaults.")

        self.presets = self.get_default_presets()
        self.save_presets()

    def save_presets(self):
        try:
            with open(self.filename, 'w') as f:
                json.dump(self.presets, f, indent=4)
        except Exception as e:
            print(f"[ERROR] Failed to save presets to {self.filename}: {e}")

    def get_preset_names(self):
        return sorted(list(self.presets.keys()))

    def get_preset(self, name):
        preset = self.presets.get(name)
        if not preset: return None
        
        # Deepcopy and merge with MASTER_OPTIONS, strictly ignoring None values
        full_options = copy.deepcopy(self.MASTER_OPTIONS)
        preset_opts = preset.get('options', {})
        for k, v in preset_opts.items():
            if v is not None:
                full_options[k] = v
        
        return {
            "options": full_options,
            "triggers": preset.get('triggers', {})
        }

    def save_preset(self, name, options, triggers):
        # Clean up options to remove UI-specific transient keys if any
        clean_options = copy.deepcopy(options)
        self.presets[name] = {
            "options": clean_options,
            "triggers": triggers
        }
        self.save_presets()

    def delete_preset(self, name):
        if name in self.presets:
            del self.presets[name]
            self.save_presets()

    def rename_preset(self, old_name, new_name):
        if old_name not in self.presets: return False
        if new_name in self.presets: return False # Prevent overwrite
        
        self.presets[new_name] = self.presets.pop(old_name)
        self.save_presets()
        return True

    def get_default_presets(self):
        # 1. Horizontal Clean (Replaces PRESET_NO_SUBTITLES)
        h_clean_opts = {
            "orientation": "horizontal + vertical",
            "merged_aspect": "16:9",
            "resolution": "4k",
            "normalize_audio": True,
            "audio_type": "surround_51", 
            "burn_subtitles": False
        }
        
        h_clean = {
            "options": h_clean_opts,
            "triggers": {
                "video_trigger": "Always (Clean/Backup)",
                "on_scan_subs": False,
                "auto_detect_subs": False,
                "suffix_filter": None 
            }
        }
        
        # 2. Vertical Hybrid Seam Hardsub (Replaces PRESET_WITH_SUBTITLES)
        v_hybrid_opts = {
            "orientation": "hybrid (stacked)",
            "resolution": "4k",
            "normalize_audio": True,
            "audio_type": "mono",
            "burn_subtitles": True,
            "subtitle_alignment": "seam"
        }
        
        v_hybrid = {
            "options": v_hybrid_opts,
            "triggers": {
                "video_trigger": "Never",
                "on_scan_subs": True,
                "auto_detect_subs": False,
                "suffix_filter": None # Matches ALL (Wildcard)
            }
        }

        # 3. Horizontal Hardsub (New for -cn)
        h_hardsub_opts = copy.deepcopy(h_clean_opts) 
        h_hardsub_opts["burn_subtitles"] = True
        h_hardsub_opts["subtitle_alignment"] = "bottom"
        h_hardsub_opts["orientation"] = "horizontal + vertical"
        
        h_hardsub = {
            "options": h_hardsub_opts,
            "triggers": {
                "video_trigger": "Never",
                "on_scan_subs": True,
                "auto_detect_subs": False,
                "suffix_filter": "-cn" # Matches ONLY -cn
            }
        }

        return {
            "Horizontal Clean": h_clean,
            "Vertical Hybrid Seam Hardsub": v_hybrid,
            "Horizontal Hardsub (-cn)": h_hardsub
        }

class VideoProcessorApp:
    def __init__(self, root, initial_files, output_mode):
        self.root = root
        self.root.title("Video Processing Tool (vid.py)")
        self.root.geometry("1400x850")
        self.output_mode = output_mode
        self.processing_jobs = []
        self.input_files = [] # New: Staging area for files
        self.filtered_input_indices = [] # New: Indices for filtering
        self.preset_manager = WorkflowPresetManager()
        self._is_loading_job_to_gui = False

        # --- Initialize all tk Variables ---
        self.current_preset_var = tk.StringVar(value=self.preset_manager.get_preset_names()[0] if self.preset_manager.get_preset_names() else "")
        self.trigger_video_always_var = tk.BooleanVar(value=False)
        self.trigger_video_fallback_var = tk.BooleanVar(value=False)
        self.trigger_scan_subs_var = tk.BooleanVar(value=False)
        self.trigger_autodetect_subs_var = tk.BooleanVar(value=False)
        self.trigger_suffix_enable_var = tk.BooleanVar(value=False)
        self.trigger_include_suffix_var = tk.BooleanVar(value=False)
        self.trigger_suffix_var = tk.StringVar(value="")
        self.output_suffix_override_var = tk.StringVar(value="")
        self.output_suffix_override_var.trace_add("write", lambda *args: self._update_selected_jobs("output_suffix_override"))
        self.input_filter_var = tk.StringVar(value="")
        self.input_filter_inverse_var = tk.BooleanVar(value=False)
        self.input_filter_var.trace_add("write", lambda *args: self.refresh_input_listbox())
        self.input_filter_inverse_var.trace_add("write", lambda *args: self.refresh_input_listbox())

        self.output_mode_var = tk.StringVar(value=output_mode)
        self.resolution_var = tk.StringVar(value=DEFAULT_RESOLUTION)
        self.upscale_algo_var = tk.StringVar(value=DEFAULT_UPSCALE_ALGO)
        self.upscale_algo_var.trace_add('write', lambda *args: [self._toggle_superres_options(), self._apply_backend_constraints()])
        self.output_format_var = tk.StringVar(value=DEFAULT_OUTPUT_FORMAT)
        self.video_codec_var = tk.StringVar(value=DEFAULT_VIDEO_CODEC)
        self.video_codec_var.trace_add('write', lambda *args: self._update_selected_jobs('video_codec'))
        self.encoder_backend_var = tk.StringVar(value=DEFAULT_ENCODER_BACKEND)
        self.encoder_backend_var.trace_add('write', lambda *args: [self._update_selected_jobs('encoder_backend'), self._update_upscale_algo_options(), self._toggle_superres_options(), self._apply_backend_constraints()])
        self.nvenc_superres_mode_var = tk.StringVar(value=DEFAULT_NVENC_SUPERRES_MODE)
        self.nvenc_superres_mode_var.trace_add('write', lambda *args: self._update_selected_jobs('nvenc_superres_mode'))
        self.nvenc_nvvfx_denoise_var = tk.BooleanVar(value=DEFAULT_NVENC_NVVFX_DENOISE)
        self.nvenc_ngx_vsr_quality_var = tk.StringVar(value=DEFAULT_NVENC_NGX_VSR_QUALITY)
        self.nvenc_ngx_vsr_quality_var.trace_add('write', lambda *args: self._update_selected_jobs('nvenc_ngx_vsr_quality'))
        self.output_subfolders_var = tk.BooleanVar(value=DEFAULT_OUTPUT_TO_SUBFOLDERS)
        self.output_subfolder_by_subtitle_var = tk.BooleanVar(value=DEFAULT_SUBFOLDER_BY_SUBTITLE)
        self.group_by_preset_var = tk.BooleanVar(value=DEFAULT_GROUP_BY_PRESET)
        self.group_by_video_var = tk.BooleanVar(value=DEFAULT_GROUP_BY_VIDEO)
        self.subfolder_override_var = tk.StringVar(value=DEFAULT_SUBFOLDER_OVERRIDE)
        self.subfolder_override_var.trace_add('write', lambda *args: self._update_selected_jobs('subfolder_override'))
        self.render_by_chapters_var = tk.BooleanVar(value=DEFAULT_RENDER_BY_CHAPTERS)
        self.split_subtitles_by_chapter_var = tk.BooleanVar(value=DEFAULT_SPLIT_SUBTITLES_BY_CHAPTER)
        self.orientation_var = tk.StringVar(value=DEFAULT_ORIENTATION)
        self.aspect_mode_var = tk.StringVar(value=DEFAULT_ASPECT_MODE)
        self.pad_color_var = tk.StringVar(value=DEFAULT_PAD_COLOR)
        self.video_offset_x_var = tk.StringVar(value=DEFAULT_VIDEO_OFFSET_X)
        self.video_offset_x_var.trace_add('write', lambda *args: self._update_selected_jobs('video_offset_x'))
        self.video_offset_y_var = tk.StringVar(value=DEFAULT_VIDEO_OFFSET_Y)
        self.video_offset_y_var.trace_add('write', lambda *args: self._update_selected_jobs('video_offset_y'))
        self.pixelate_multiplier_var = tk.StringVar(value=DEFAULT_PIXELATE_MULTIPLIER)
        self.pixelate_multiplier_var.trace_add('write', lambda *args: self._update_selected_jobs('pixelate_multiplier'))
        self.ambient_spread_var = tk.StringVar(value=DEFAULT_AMBIENT_SPREAD)
        self.ambient_spread_var.trace_add('write', lambda *args: self._update_selected_jobs('ambient_spread'))
        self.pixelate_brightness_var = tk.StringVar(value=DEFAULT_PIXELATE_BRIGHTNESS)
        self.pixelate_brightness_var.trace_add('write', lambda *args: self._update_selected_jobs('pixelate_brightness'))
        self.pixelate_saturation_var = tk.StringVar(value=DEFAULT_PIXELATE_SATURATION)
        self.pixelate_saturation_var.trace_add('write', lambda *args: self._update_selected_jobs('pixelate_saturation'))
        self.blur_sigma_var = tk.StringVar(value=DEFAULT_BLUR_SIGMA)
        self.blur_sigma_var.trace_add('write', lambda *args: self._update_selected_jobs('blur_sigma'))
        self.blur_steps_var = tk.StringVar(value=DEFAULT_BLUR_STEPS)
        self.blur_steps_var.trace_add('write', lambda *args: self._update_selected_jobs('blur_steps'))
        self.horizontal_aspect_var = tk.StringVar(value=DEFAULT_HORIZONTAL_ASPECT)
        self.vertical_aspect_var = tk.StringVar(value=DEFAULT_VERTICAL_ASPECT)
        self.merged_aspect_var = tk.StringVar(value=DEFAULT_HORIZONTAL_ASPECT)
        self.fruc_var = tk.BooleanVar(value=DEFAULT_FRUC)
        self.fruc_fps_var = tk.StringVar(value=DEFAULT_FRUC_FPS)
        self.fruc_fps_var.trace_add('write', lambda *args: self._update_selected_jobs('fruc_fps'))
        self.generate_log_var = tk.BooleanVar(value=False)
        self.close_gui_var = tk.BooleanVar(value=True)
        self.hibernate_when_done_var = tk.BooleanVar(value=False)
        self.burn_subtitles_var = tk.BooleanVar(value=DEFAULT_BURN_SUBTITLES)
        self.override_bitrate_var = tk.BooleanVar(value=False)
        self.manual_bitrate_var = tk.StringVar(value="0")
        self.manual_bitrate_var.trace_add('write', lambda *args: self._update_selected_jobs('manual_bitrate'))
        self.max_size_mb_var = tk.StringVar(value=str(DEFAULT_MAX_SIZE_MB))
        self.max_size_mb_var.trace_add('write', lambda *args: self._update_selected_jobs('max_size_mb'))
        self.max_duration_var = tk.StringVar(value=str(DEFAULT_MAX_DURATION))
        self.max_duration_var.trace_add('write', lambda *args: self._update_selected_jobs('max_duration'))
        self.use_dynaudnorm_var = tk.BooleanVar(value=DEFAULT_USE_DYNAUDNORM)
        self.normalize_audio_var = tk.BooleanVar(value=DEFAULT_NORMALIZE_AUDIO)
        self.loudness_target_var = tk.StringVar(value=DEFAULT_LOUDNESS_TARGET)
        self.loudness_target_var.trace_add('write', lambda *args: self._update_selected_jobs('loudness_target'))
        self.loudness_range_var = tk.StringVar(value=DEFAULT_LOUDNESS_RANGE)
        self.loudness_range_var.trace_add('write', lambda *args: self._update_selected_jobs('loudness_range'))
        self.true_peak_var = tk.StringVar(value=DEFAULT_TRUE_PEAK)
        self.true_peak_var.trace_add('write', lambda *args: self._update_selected_jobs('true_peak'))
        self.dyn_frame_len_var = tk.StringVar(value=DEFAULT_DYNAUDNORM_FRAME_LEN)
        self.dyn_frame_len_var.trace_add('write', lambda *args: self._update_selected_jobs('dyn_frame_len'))
        self.dyn_gauss_win_var = tk.StringVar(value=DEFAULT_DYNAUDNORM_GAUSS_WIN)
        self.dyn_gauss_win_var.trace_add('write', lambda *args: self._update_selected_jobs('dyn_gauss_win'))
        self.dyn_peak_var = tk.StringVar(value=DEFAULT_DYNAUDNORM_PEAK)
        self.dyn_peak_var.trace_add('write', lambda *args: self._update_selected_jobs('dyn_peak'))
        self.dyn_max_gain_var = tk.StringVar(value=DEFAULT_DYNAUDNORM_MAX_GAIN)
        self.dyn_max_gain_var.trace_add('write', lambda *args: self._update_selected_jobs('dyn_max_gain'))

        # Loudness War variables
        self.use_loudness_war_var = tk.BooleanVar(value=DEFAULT_USE_LOUDNESS_WAR)
        self.comp_threshold_var = tk.StringVar(value=DEFAULT_COMPRESSOR_THRESHOLD)
        self.comp_threshold_var.trace_add('write', lambda *args: self._update_selected_jobs('comp_threshold'))
        self.comp_ratio_var = tk.StringVar(value=DEFAULT_COMPRESSOR_RATIO)
        self.comp_ratio_var.trace_add('write', lambda *args: self._update_selected_jobs('comp_ratio'))
        self.comp_attack_var = tk.StringVar(value=DEFAULT_COMPRESSOR_ATTACK)
        self.comp_attack_var.trace_add('write', lambda *args: self._update_selected_jobs('comp_attack'))
        self.comp_release_var = tk.StringVar(value=DEFAULT_COMPRESSOR_RELEASE)
        self.comp_release_var.trace_add('write', lambda *args: self._update_selected_jobs('comp_release'))
        self.comp_makeup_var = tk.StringVar(value=DEFAULT_COMPRESSOR_MAKEUP)
        self.comp_makeup_var.trace_add('write', lambda *args: self._update_selected_jobs('comp_makeup'))
        self.limit_limit_var = tk.StringVar(value=DEFAULT_LIMITER_LIMIT)
        self.limit_limit_var.trace_add('write', lambda *args: self._update_selected_jobs('limit_limit'))

        self.measure_loudness_var = tk.BooleanVar(value=DEFAULT_MEASURE_LOUDNESS)

        # Encoder Variables
        self.nvenc_preset_var = tk.StringVar(value=DEFAULT_NVENC_PRESET)
        self.nvenc_preset_var.trace_add('write', lambda *args: self._update_selected_jobs('nvenc_preset'))
        self.nvenc_tune_var = tk.StringVar(value=DEFAULT_NVENC_TUNE)
        self.nvenc_tune_var.trace_add('write', lambda *args: self._update_selected_jobs('nvenc_tune'))
        self.nvenc_profile_sdr_var = tk.StringVar(value=DEFAULT_NVENC_PROFILE_SDR)
        self.nvenc_profile_sdr_var.trace_add('write', lambda *args: self._update_selected_jobs('nvenc_profile_sdr'))
        self.nvenc_profile_hdr_var = tk.StringVar(value=DEFAULT_NVENC_PROFILE_HDR)
        self.nvenc_profile_hdr_var.trace_add('write', lambda *args: self._update_selected_jobs('nvenc_profile_hdr'))
        self.nvenc_rc_lookahead_var = tk.StringVar(value=DEFAULT_NVENC_RC_LOOKAHEAD)
        self.nvenc_rc_lookahead_var.trace_add('write', lambda *args: self._update_selected_jobs('nvenc_rc_lookahead'))
        self.nvenc_multipass_var = tk.StringVar(value=DEFAULT_NVENC_MULTIPASS)
        self.nvenc_multipass_var.trace_add('write', lambda *args: self._update_selected_jobs('nvenc_multipass'))
        self.nvenc_spatial_aq_var = tk.StringVar(value=DEFAULT_NVENC_SPATIAL_AQ)
        self.nvenc_spatial_aq_var.trace_add('write', lambda *args: self._update_selected_jobs('nvenc_spatial_aq'))
        self.nvenc_temporal_aq_var = tk.StringVar(value=DEFAULT_NVENC_TEMPORAL_AQ)
        self.nvenc_temporal_aq_var.trace_add('write', lambda *args: self._update_selected_jobs('nvenc_temporal_aq'))
        self.nvenc_bframes_var = tk.StringVar(value=DEFAULT_NVENC_BFRAMES)
        self.nvenc_bframes_var.trace_add('write', lambda *args: self._update_selected_jobs('nvenc_bframes'))
        self.nvenc_b_ref_mode_var = tk.StringVar(value=DEFAULT_NVENC_B_REF_MODE)
        self.nvenc_b_ref_mode_var.trace_add('write', lambda *args: self._update_selected_jobs('nvenc_b_ref_mode'))
        self.nvencc_decode_mode_var = tk.StringVar(value=DEFAULT_NVENCC_DECODE_MODE)
        self.nvencc_decode_mode_var.trace_add('write', lambda *args: self._update_selected_jobs('nvencc_decode_mode'))
        self.nvencc_color_tag_mode_var = tk.StringVar(value=DEFAULT_NVENCC_COLOR_TAG_MODE)
        self.nvencc_color_tag_mode_var.trace_add('write', lambda *args: [self._update_selected_jobs('nvencc_color_tag_mode'), self._toggle_nvencc_color_mode_controls()])
        self.nvencc_color_prim_var = tk.StringVar(value=DEFAULT_NVENCC_COLOR_PRIM)
        self.nvencc_color_prim_var.trace_add('write', lambda *args: self._update_selected_jobs('nvencc_color_prim'))
        self.nvencc_color_transfer_var = tk.StringVar(value=DEFAULT_NVENCC_COLOR_TRANSFER)
        self.nvencc_color_transfer_var.trace_add('write', lambda *args: self._update_selected_jobs('nvencc_color_transfer'))
        self.nvencc_color_matrix_var = tk.StringVar(value=DEFAULT_NVENCC_COLOR_MATRIX)
        self.nvencc_color_matrix_var.trace_add('write', lambda *args: self._update_selected_jobs('nvencc_color_matrix'))
        self.nvencc_output_depth_var = tk.StringVar(value=DEFAULT_NVENCC_OUTPUT_DEPTH)
        self.nvencc_output_depth_var.trace_add('write', lambda *args: self._update_selected_jobs('nvencc_output_depth'))
        self.nvencc_strict_no_color_tagging_var = tk.BooleanVar(value=DEFAULT_NVENCC_STRICT_NO_COLOR_TAGGING)
        self.ffmpeg_threads_var = tk.StringVar(value=DEFAULT_FFMPEG_THREADS)
        self.ffmpeg_threads_var.trace_add('write', lambda *args: self._update_selected_jobs('ffmpeg_threads'))
        self.ffmpeg_priority_var = tk.StringVar(value=DEFAULT_FFMPEG_PRIORITY)
        self.ffmpeg_priority_var.trace_add('write', lambda *args: self._update_selected_jobs('ffmpeg_priority'))

        self.sofa_file_var = tk.StringVar(value=DEFAULT_SOFA_PATH)
        self.lut_file_var = tk.StringVar(value=DEFAULT_LUT_PATH)
        self.status_var = tk.StringVar(value="Ready")
        self.hybrid_top_aspect_var = tk.StringVar(value="16:9")
        self.hybrid_top_mode_var = tk.StringVar(value="pad")
        self.hybrid_top_path_var = tk.StringVar(value="")
        self.hybrid_top_path_var.trace_add('write', lambda *args: self._update_selected_jobs('hybrid_top_path'))
        self.hybrid_bottom_aspect_var = tk.StringVar(value="4:5")
        self.hybrid_bottom_mode_var = tk.StringVar(value="crop")
        self.hybrid_bottom_path_var = tk.StringVar(value="")
        self.hybrid_bottom_path_var.trace_add('write', lambda *args: self._update_selected_jobs('hybrid_bottom_path'))
        self.subtitle_font_var = tk.StringVar(value=DEFAULT_SUBTITLE_FONT)
        self.subtitle_font_size_var = tk.StringVar(value=DEFAULT_SUBTITLE_FONT_SIZE)
        self.subtitle_font_size_var.trace_add('write', lambda *args: self._update_selected_jobs('subtitle_font_size'))
        self.subtitle_alignment_var = tk.StringVar(value=DEFAULT_SUBTITLE_ALIGNMENT)
        self.subtitle_bold_var = tk.BooleanVar(value=DEFAULT_SUBTITLE_BOLD)
        self.subtitle_italic_var = tk.BooleanVar(value=DEFAULT_SUBTITLE_ITALIC)
        self.subtitle_underline_var = tk.BooleanVar(value=DEFAULT_SUBTITLE_UNDERLINE)
        self.subtitle_margin_v_var = tk.StringVar(value=DEFAULT_SUBTITLE_MARGIN_V)
        self.subtitle_margin_v_var.trace_add('write', lambda *args: self._update_selected_jobs('subtitle_margin_v'))
        self.subtitle_margin_l_var = tk.StringVar(value=DEFAULT_SUBTITLE_MARGIN_L)
        self.subtitle_margin_l_var.trace_add('write', lambda *args: self._update_selected_jobs('subtitle_margin_l'))
        self.subtitle_margin_r_var = tk.StringVar(value=DEFAULT_SUBTITLE_MARGIN_R)
        self.subtitle_margin_r_var.trace_add('write', lambda *args: self._update_selected_jobs('subtitle_margin_r'))
        self.subtitle_seam_h_offset_var = tk.StringVar(value=DEFAULT_SUBTITLE_SEAM_H_OFFSET)
        self.subtitle_seam_h_offset_var.trace_add('write', lambda *args: self._update_selected_jobs('subtitle_seam_h_offset'))
        self.subtitle_seam_v_offset_var = tk.StringVar(value=DEFAULT_SUBTITLE_SEAM_V_OFFSET)
        self.subtitle_seam_v_offset_var.trace_add('write', lambda *args: self._update_selected_jobs('subtitle_seam_v_offset'))
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
        self.subtitle_max_lines_var = tk.StringVar(value=DEFAULT_SUBTITLE_MAX_LINES)
        self.subtitle_max_lines_var.trace_add('write', lambda *args: self._update_selected_jobs('subtitle_max_lines'))
        self.last_standard_alignment = tk.StringVar(value=DEFAULT_SUBTITLE_ALIGNMENT)
        self.subtitle_path_var = tk.StringVar(value="")
        self._suppress_subtitle_path_trace = False
        self.subtitle_path_var.trace_add('write', lambda *args: self._on_subtitle_path_change())

        # Title Burn Variables
        self.title_burn_var = tk.BooleanVar(value=DEFAULT_TITLE_BURN_ENABLED)
        self.title_json_suffix_var = tk.StringVar(value=DEFAULT_TITLE_JSON_SUFFIX)
        self.title_json_suffix_var.trace_add('write', lambda *args: self._update_selected_jobs('title_json_suffix'))
        self.title_remove_hashtags_var = tk.BooleanVar(value=DEFAULT_TITLE_REMOVE_HASHTAGS)
        self.title_enable_emoji_var = tk.BooleanVar(value=DEFAULT_TITLE_ENABLE_EMOJI)
        self.title_autodetect_var = tk.BooleanVar(value=DEFAULT_TITLE_AUTODETECT)
        self.title_override_var = tk.StringVar(value=DEFAULT_TITLE_OVERRIDE_TEXT)
        self.title_override_var.trace_add('write', lambda *args: self._update_selected_jobs('title_override_text'))
        self.title_start_time_var = tk.StringVar(value=DEFAULT_TITLE_START_TIME)
        self.title_start_time_var.trace_add('write', lambda *args: self._update_selected_jobs('title_start_time'))
        self.title_end_time_var = tk.StringVar(value=DEFAULT_TITLE_END_TIME)
        self.title_end_time_var.trace_add('write', lambda *args: self._update_selected_jobs('title_end_time'))
        self.title_font_var = tk.StringVar(value=DEFAULT_TITLE_FONT)
        self.title_font_size_var = tk.StringVar(value=DEFAULT_TITLE_FONT_SIZE)
        self.title_font_size_var.trace_add('write', lambda *args: self._update_selected_jobs('title_font_size'))
        self.title_bold_var = tk.BooleanVar(value=DEFAULT_TITLE_BOLD)
        self.title_italic_var = tk.BooleanVar(value=DEFAULT_TITLE_ITALIC)
        self.title_underline_var = tk.BooleanVar(value=DEFAULT_TITLE_UNDERLINE)
        self.title_alignment_var = tk.StringVar(value=DEFAULT_TITLE_ALIGNMENT)
        self.title_margin_v_var = tk.StringVar(value=DEFAULT_TITLE_MARGIN_V)
        self.title_margin_v_var.trace_add('write', lambda *args: self._update_selected_jobs('title_margin_v'))
        self.title_margin_l_var = tk.StringVar(value=DEFAULT_TITLE_MARGIN_L)
        self.title_margin_l_var.trace_add('write', lambda *args: self._update_selected_jobs('title_margin_l'))
        self.title_margin_r_var = tk.StringVar(value=DEFAULT_TITLE_MARGIN_R)
        self.title_margin_r_var.trace_add('write', lambda *args: self._update_selected_jobs('title_margin_r'))
        self.title_fill_color_var = tk.StringVar(value=DEFAULT_TITLE_FILL_COLOR)
        self.title_fill_alpha_var = tk.IntVar(value=DEFAULT_TITLE_FILL_ALPHA)
        self.title_outline_color_var = tk.StringVar(value=DEFAULT_TITLE_OUTLINE_COLOR)
        self.title_outline_alpha_var = tk.IntVar(value=DEFAULT_TITLE_OUTLINE_ALPHA)
        self.title_outline_width_var = tk.StringVar(value=DEFAULT_TITLE_OUTLINE_WIDTH)
        self.title_outline_width_var.trace_add('write', lambda *args: self._update_selected_jobs('title_outline_width'))
        self.title_shadow_color_var = tk.StringVar(value=DEFAULT_TITLE_SHADOW_COLOR)
        self.title_shadow_alpha_var = tk.IntVar(value=DEFAULT_TITLE_SHADOW_ALPHA)
        self.title_shadow_offset_x_var = tk.StringVar(value=DEFAULT_TITLE_SHADOW_OFFSET_X)
        self.title_shadow_offset_x_var.trace_add('write', lambda *args: self._update_selected_jobs('title_shadow_offset_x'))
        self.title_shadow_offset_y_var = tk.StringVar(value=DEFAULT_TITLE_SHADOW_OFFSET_Y)
        self.title_shadow_offset_y_var.trace_add('write', lambda *args: self._update_selected_jobs('title_shadow_offset_y'))
        self.title_shadow_blur_var = tk.StringVar(value=DEFAULT_TITLE_SHADOW_BLUR)
        self.title_shadow_blur_var.trace_add('write', lambda *args: self._update_selected_jobs('title_shadow_blur'))

        self.use_sharpening_var = tk.BooleanVar(value=DEFAULT_USE_SHARPENING)
        self.ffmpeg_denoise_vulkan_var = tk.BooleanVar(value=DEFAULT_FFMPEG_DENOISE_VULKAN)
        self.sharpening_algo_var = tk.StringVar(value=DEFAULT_SHARPENING_ALGO)
        self.sharpening_strength_var = tk.StringVar(value=DEFAULT_SHARPENING_STRENGTH)
        self.sharpening_strength_var.trace_add('write', lambda *args: self._update_selected_jobs('sharpening_strength'))

        self.audio_mono_var = tk.BooleanVar(value=DEFAULT_AUDIO_MONO)
        self.audio_stereo_downmix_var = tk.BooleanVar(value=DEFAULT_AUDIO_STEREO_DOWNMIX)
        self.audio_stereo_sofalizer_var = tk.BooleanVar(value=DEFAULT_AUDIO_STEREO_SOFALIZER)
        self.audio_surround_51_var = tk.BooleanVar(value=DEFAULT_AUDIO_SURROUND_51)
        self.audio_passthrough_var = tk.BooleanVar(value=DEFAULT_AUDIO_PASSTHROUGH)

        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind("<<Drop>>", self.handle_file_drop)
        self.setup_gui()
        if initial_files: self.process_added_files(initial_files)

    def setup_gui(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        main_pane = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_pane.grid(row=0, column=0, sticky="nsew")

        input_frame = ttk.Frame(main_pane, padding=5)
        main_pane.add(input_frame, weight=1)

        # Right Side Container (Presets + Settings)
        right_pane_frame = ttk.Frame(main_pane)
        main_pane.add(right_pane_frame, weight=2)
        
        self.setup_presets_ui(right_pane_frame)
        
        right_pane_frame.rowconfigure(1, weight=1)
        right_pane_frame.columnconfigure(0, weight=1)
        
        settings_notebook = ttk.Notebook(right_pane_frame)
        settings_notebook.pack(fill='both', expand=True, pady=(5,0))

        # Bottom Bar with Progress
        bottom_frame = ttk.Frame(self.root)
        bottom_frame.grid(row=2, column=0, columnspan=2, sticky="ew")

        button_frame = ttk.Frame(bottom_frame)
        button_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10, pady=5)
        
        # Progress Bar
        self.progress_bar = ttk.Progressbar(bottom_frame, orient=tk.HORIZONTAL, length=100, mode='determinate')
        self.progress_bar.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=2)

        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.grid(row=3, column=0, columnspan=2, sticky="ew", padx=5, pady=2)

        self.setup_input_pane(input_frame)

        self.video_tab = ScrollableFrame(settings_notebook, padding=10)
        self.audio_tab = ScrollableFrame(settings_notebook, padding=10)
        self.loudness_tab = ScrollableFrame(settings_notebook, padding=10)
        self.title_tab = ScrollableFrame(settings_notebook, padding=10)
        self.subtitle_tab = ScrollableFrame(settings_notebook, padding=10)
        self.encoder_tab = ScrollableFrame(settings_notebook, padding=10)

        settings_notebook.add(self.video_tab, text="Video")
        settings_notebook.add(self.audio_tab, text="Audio")
        settings_notebook.add(self.loudness_tab, text="Loudness")
        settings_notebook.add(self.title_tab, text="Title")
        settings_notebook.add(self.subtitle_tab, text="Subtitles")
        settings_notebook.add(self.encoder_tab, text="Encoder")

        self.setup_video_tab(self.video_tab.scrollable_window)
        self.setup_audio_tab(self.audio_tab.scrollable_window)
        self.setup_loudness_tab(self.loudness_tab.scrollable_window)
        self.setup_title_tab(self.title_tab.scrollable_window)
        self.setup_subtitle_tab(self.subtitle_tab.scrollable_window)
        self.setup_encoder_tab(self.encoder_tab.scrollable_window)
    
        # Add Apply Buttons below settings
        apply_frame = ttk.Frame(right_pane_frame)
        apply_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=5, padx=5)
        
        ttk.Button(apply_frame, text="Apply Preset & Settings to Selected Jobs", command=self.apply_preset_settings_to_selected).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        ttk.Button(apply_frame, text="Apply to ALL Jobs", command=self.apply_preset_settings_to_all).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
    
        self.setup_button_row(button_frame)

        self._toggle_orientation_options()
        self._toggle_upscale_options()
        self._update_upscale_algo_options()
        self._toggle_superres_options()
        self._toggle_nvencc_color_mode_controls()
        self._apply_backend_constraints()
        self._toggle_audio_norm_options()
        self._update_audio_options_ui() 
        self._update_codec_options(show_message=False)
        self._update_bitrate_display()
        
        # Load initial preset
        if self.current_preset_var.get():
            self.load_preset_to_gui(self.current_preset_var.get())

    def setup_encoder_tab(self, parent):
        scroll_canvas = tk.Canvas(parent, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=scroll_canvas.yview)
        scroll_frame = ttk.Frame(scroll_canvas)

        scroll_frame.bind("<Configure>", lambda e: scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all")))
        scroll_canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        scroll_canvas.configure(yscrollcommand=scrollbar.set)

        scroll_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Basic NVENC Settings
        basic_group = ttk.LabelFrame(scroll_frame, text="Basic NVENC Settings", padding=10)
        basic_group.pack(fill=tk.X, pady=5, padx=5)

        # Backend
        ttk.Label(basic_group, text="Backend:").grid(row=0, column=0, sticky=tk.W, pady=2)
        backend_combo = ttk.Combobox(
            basic_group,
            textvariable=self.encoder_backend_var,
            values=["ffmpeg_only", "nvencc_with_ffmpeg", "nvencc_only", "nvencc_video_with_ffmpeg_audio"],
            width=26,
            state="readonly"
        )
        backend_combo.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        ToolTip(backend_combo, "ffmpeg_only = all FFmpeg. nvencc_with_ffmpeg = preprocess + NVEncC encode. nvencc_only = NVEncC only. nvencc_video_with_ffmpeg_audio = NVEncC video + FFmpeg audio.")

        # Render by Chapters
        cb_chapters = ttk.Checkbutton(basic_group, text="Render by Chapters (Split by metadata markers)", variable=self.render_by_chapters_var, command=lambda: [self._update_audio_options_ui(), self._update_selected_jobs('render_by_chapters')])
        cb_chapters.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=2)
        ToolTip(cb_chapters, "Detects chapter markers in the input file and renders each as a separate file named after its title.")

        # Split Subtitles by Chapter
        cb_split_subs = ttk.Checkbutton(basic_group, text="Export Subtitle chunks per split", variable=self.split_subtitles_by_chapter_var, command=lambda: self._update_selected_jobs('split_subtitles_by_chapter'))
        cb_split_subs.grid(row=2, column=0, columnspan=2, sticky=tk.W, padx=20, pady=2)
        ToolTip(cb_split_subs, "Splits the mapped subtitle file per chapter and saves it as a separate .srt alongside the video segment.")

        # Preset
        ttk.Label(basic_group, text="Preset:").grid(row=3, column=0, sticky=tk.W, pady=2)
        preset_combo = ttk.Combobox(basic_group, textvariable=self.nvenc_preset_var, values=[f"p{i}" for i in range(1, 8)], width=10, state="readonly")
        preset_combo.grid(row=3, column=1, sticky=tk.W, padx=5, pady=2)
        ToolTip(preset_combo, "NVENC Preset. p1 is fastest, p7 is slowest/highest quality.")

        # Tune
        ttk.Label(basic_group, text="Tune:").grid(row=4, column=0, sticky=tk.W, pady=2)
        tune_combo = ttk.Combobox(basic_group, textvariable=self.nvenc_tune_var, values=["hq", "ll", "ull", "lossless"], width=10, state="readonly")
        tune_combo.grid(row=4, column=1, sticky=tk.W, padx=5, pady=2)
        ToolTip(tune_combo, "NVENC Tuning. hq=High Quality, ll=Low Latency, ull=Ultra Low Latency.")

        # Codec
        ttk.Label(basic_group, text="Codec:").grid(row=5, column=0, sticky=tk.W, pady=2)
        self.video_codec_combo = ttk.Combobox(basic_group, textvariable=self.video_codec_var, values=["h264", "hevc", "av1"], width=10, state="readonly")
        self.video_codec_combo.grid(row=5, column=1, sticky=tk.W, padx=5, pady=2)
        ToolTip(self.video_codec_combo, "Output codec. HDR requires HEVC or AV1.")

        # Profile SDR
        ttk.Label(basic_group, text="Profile (SDR):").grid(row=6, column=0, sticky=tk.W, pady=2)
        profile_sdr_combo = ttk.Combobox(basic_group, textvariable=self.nvenc_profile_sdr_var, values=["high", "main", "baseline"], width=10, state="readonly")
        profile_sdr_combo.grid(row=6, column=1, sticky=tk.W, padx=5, pady=2)
        ToolTip(profile_sdr_combo, "NVENC Profile for SDR output.")

        # Profile HDR
        ttk.Label(basic_group, text="Profile (HDR):").grid(row=7, column=0, sticky=tk.W, pady=2)
        profile_hdr_combo = ttk.Combobox(basic_group, textvariable=self.nvenc_profile_hdr_var, values=["main10"], width=10, state="readonly")
        profile_hdr_combo.grid(row=7, column=1, sticky=tk.W, padx=5, pady=2)
        ToolTip(profile_hdr_combo, "NVENC Profile for HDR output (must be main10).")

        # Decode Mode (NVEncC)
        ttk.Label(basic_group, text="Decode Mode:").grid(row=8, column=0, sticky=tk.W, pady=2)
        decode_mode_combo = ttk.Combobox(
            basic_group,
            textvariable=self.nvencc_decode_mode_var,
            values=["auto", "avhw", "avsw"],
            width=10,
            state="readonly"
        )
        decode_mode_combo.grid(row=8, column=1, sticky=tk.W, padx=5, pady=2)
        ToolTip(decode_mode_combo, "NVEncC input reader: auto (current logic), avhw (force hardware decode), avsw (force software decode).")

        # FFmpeg CPU Threads
        ttk.Label(basic_group, text="FFmpeg Threads:").grid(row=9, column=0, sticky=tk.W, pady=2)
        ffmpeg_threads_entry = ttk.Entry(basic_group, textvariable=self.ffmpeg_threads_var, width=10)
        ffmpeg_threads_entry.grid(row=9, column=1, sticky=tk.W, padx=5, pady=2)
        ToolTip(ffmpeg_threads_entry, "FFmpeg `-threads` value. Use 0 for auto, or a positive integer.")

        # FFmpeg Process Priority
        ttk.Label(basic_group, text="FFmpeg Priority:").grid(row=10, column=0, sticky=tk.W, pady=2)
        ffmpeg_priority_combo = ttk.Combobox(
            basic_group,
            textvariable=self.ffmpeg_priority_var,
            values=FFMPEG_PRIORITY_LABELS,
            width=14,
            state="readonly"
        )
        ffmpeg_priority_combo.grid(row=10, column=1, sticky=tk.W, padx=5, pady=2)
        ToolTip(ffmpeg_priority_combo, "FFmpeg process priority (Windows). Non-Windows systems ignore this setting.")

        # GOP & B-Frames
        gop_group = ttk.LabelFrame(scroll_frame, text="GOP & B-Frames", padding=10)
        gop_group.pack(fill=tk.X, pady=5, padx=5)

        # B-Frames
        ttk.Label(gop_group, text="B-Frames:").grid(row=0, column=0, sticky=tk.W, pady=2)
        bframes_entry = ttk.Entry(gop_group, textvariable=self.nvenc_bframes_var, width=5)
        bframes_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        ToolTip(bframes_entry, "Number of B-Frames. Default is 4.")

        # B-Ref Mode
        ttk.Label(gop_group, text="B-Ref Mode:").grid(row=1, column=0, sticky=tk.W, pady=2)
        bref_combo = ttk.Combobox(gop_group, textvariable=self.nvenc_b_ref_mode_var, values=["disabled", "each", "middle"], width=10, state="readonly")
        bref_combo.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        ToolTip(bref_combo, "B-Frame reference mode. middle is standard.")

        # Rate Control & AQ
        rc_group = ttk.LabelFrame(scroll_frame, text="Rate Control & Quality", padding=10)
        rc_group.pack(fill=tk.X, pady=5, padx=5)

        # RC Lookahead
        ttk.Label(rc_group, text="RC Lookahead:").grid(row=0, column=0, sticky=tk.W, pady=2)
        lookahead_entry = ttk.Entry(rc_group, textvariable=self.nvenc_rc_lookahead_var, width=5)
        lookahead_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        ToolTip(lookahead_entry, "Rate control lookahead frames. Default 32.")

        # Multipass
        ttk.Label(rc_group, text="Multipass:").grid(row=1, column=0, sticky=tk.W, pady=2)
        multipass_combo = ttk.Combobox(rc_group, textvariable=self.nvenc_multipass_var, values=["disabled", "qres", "fullres"], width=10, state="readonly")
        multipass_combo.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        ToolTip(multipass_combo, "Multipass encoding mode.")

        # Spatial AQ
        ttk.Label(rc_group, text="Spatial AQ:").grid(row=2, column=0, sticky=tk.W, pady=2)
        spatial_combo = ttk.Combobox(rc_group, textvariable=self.nvenc_spatial_aq_var, values=["0", "1"], width=5, state="readonly")
        spatial_combo.grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)
        ToolTip(spatial_combo, "Enable/Disable Spatial Adaptive Quantization.")

        # Temporal AQ
        ttk.Label(rc_group, text="Temporal AQ:").grid(row=3, column=0, sticky=tk.W, pady=2)
        temporal_combo = ttk.Combobox(rc_group, textvariable=self.nvenc_temporal_aq_var, values=["0", "1"], width=5, state="readonly")
        temporal_combo.grid(row=3, column=1, sticky=tk.W, padx=5, pady=2)
        ToolTip(temporal_combo, "Enable/Disable Temporal Adaptive Quantization.")


        # NVEncC Color (Details)
        color_group = ttk.LabelFrame(scroll_frame, text="NVEncC Color (Details)", padding=10)
        color_group.pack(fill=tk.X, pady=5, padx=5)

        ttk.Label(color_group, text="Color Tags:").grid(row=0, column=0, sticky=tk.W, pady=2)
        color_mode_combo = ttk.Combobox(
            color_group,
            textvariable=self.nvencc_color_tag_mode_var,
            values=["auto", "custom"],
            width=10,
            state="readonly"
        )
        color_mode_combo.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        ToolTip(color_mode_combo, "auto = derive SDR/HDR tags automatically. custom = use values below.")

        ttk.Label(color_group, text="Output Depth:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.nvencc_output_depth_combo = ttk.Combobox(
            color_group,
            textvariable=self.nvencc_output_depth_var,
            values=["auto", "8", "10"],
            width=10,
            state="readonly"
        )
        self.nvencc_output_depth_combo.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        ToolTip(self.nvencc_output_depth_combo, "Output bit depth used by NVEncC. auto follows SDR/HDR mode.")

        ttk.Label(color_group, text="Primaries:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.nvencc_color_prim_combo = ttk.Combobox(
            color_group,
            textvariable=self.nvencc_color_prim_var,
            values=["bt709", "bt2020"],
            width=12,
            state="readonly"
        )
        self.nvencc_color_prim_combo.grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)

        ttk.Label(color_group, text="Transfer:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.nvencc_color_transfer_combo = ttk.Combobox(
            color_group,
            textvariable=self.nvencc_color_transfer_var,
            values=["bt709", "smpte2084", "arib-std-b67"],
            width=12,
            state="readonly"
        )
        self.nvencc_color_transfer_combo.grid(row=3, column=1, sticky=tk.W, padx=5, pady=2)

        ttk.Label(color_group, text="Matrix:").grid(row=4, column=0, sticky=tk.W, pady=2)
        self.nvencc_color_matrix_combo = ttk.Combobox(
            color_group,
            textvariable=self.nvencc_color_matrix_var,
            values=["bt709", "bt2020nc"],
            width=12,
            state="readonly"
        )
        self.nvencc_color_matrix_combo.grid(row=4, column=1, sticky=tk.W, padx=5, pady=2)

        strict_color_tag_cb = ttk.Checkbutton(
            color_group,
            text="Strict: no extra color tagging",
            variable=self.nvencc_strict_no_color_tagging_var,
            command=lambda: self._update_selected_jobs('nvencc_strict_no_color_tagging')
        )
        strict_color_tag_cb.grid(row=5, column=0, columnspan=2, sticky=tk.W, pady=2)
        ToolTip(strict_color_tag_cb, "When enabled, omit --colorprim/--transfer/--colormatrix and keep only output depth.")

        self._toggle_nvencc_color_mode_controls()
    def setup_presets_ui(self, parent):
        preset_frame = ttk.LabelFrame(parent, text="Workflow Presets", padding=10)
        preset_frame.pack(fill=tk.X, side=tk.TOP)
        
        # Row 1: Selection and CRUD
        row1 = ttk.Frame(preset_frame)
        row1.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(row1, text="Active Preset:").pack(side=tk.LEFT, padx=(0, 5))
        self.preset_combo = ttk.Combobox(row1, textvariable=self.current_preset_var, values=self.preset_manager.get_preset_names(), state="readonly", width=30)
        self.preset_combo.pack(side=tk.LEFT, padx=5)
        self.preset_combo.bind("<<ComboboxSelected>>", lambda e: self.load_preset_to_gui(self.current_preset_var.get()))
        
        ttk.Button(row1, text="New Preset", command=self.create_new_preset).pack(side=tk.LEFT, padx=5)
        ttk.Button(row1, text="Save Changes", command=self.save_current_preset).pack(side=tk.LEFT, padx=5)
        ttk.Button(row1, text="Save As New...", command=self.save_preset_as_new).pack(side=tk.LEFT, padx=5)
        ttk.Button(row1, text="Rename", command=self.rename_current_preset).pack(side=tk.LEFT, padx=5)
        ttk.Button(row1, text="Delete", command=self.delete_current_preset).pack(side=tk.LEFT, padx=5)

        # Row 1.5: Suffix Override
        row_suffix = ttk.Frame(preset_frame)
        row_suffix.pack(fill=tk.X, pady=(2, 5))
        ttk.Label(row_suffix, text="Suffix Override:").pack(side=tk.LEFT, padx=(5, 5))
        suffix_entry = ttk.Entry(row_suffix, textvariable=self.output_suffix_override_var, width=30)
        suffix_entry.pack(side=tk.LEFT, padx=5)
        ToolTip(suffix_entry, "Override filename suffix (e.g., 'MyCut'). If empty, the Preset Name is used.")

        # Row 2: Auto-Add Triggers (Redesigned)
        row2 = ttk.LabelFrame(preset_frame, text="Auto-Add Triggers (Add to Job Queue)", padding=5)
        row2.pack(fill=tk.X, pady=5)
        
        # Trigger 1: Video File
        row2_1 = ttk.Frame(row2)
        row2_1.pack(fill=tk.X, pady=2)
        ttk.Label(row2_1, text="Trigger on Video:").pack(side=tk.LEFT, padx=(5, 5))
        
        # Variables are initialized in __init__
        
        # Logic to ensure logic or allow both?
        # If Always is checked, Fallback is redundant.
        # Let's just allow them to be toggled freely, but prioritize logic in Save.
        
        cb_always = ttk.Checkbutton(row2_1, text="Always (Clean/Backup)", variable=self.trigger_video_always_var)
        cb_always.pack(side=tk.LEFT, padx=5)
        ToolTip(cb_always, "Always auto-add this preset for the video file (e.g. for a Clean Copy), regardless of subtitles.")

        cb_fallback = ttk.Checkbutton(row2_1, text="Fallback (If No Subs)", variable=self.trigger_video_fallback_var)
        cb_fallback.pack(side=tk.LEFT, padx=5)
        ToolTip(cb_fallback, "Auto-add this preset ONLY if no subtitles matches are found.")

        # Trigger 2: Subtitle File
        row2_2 = ttk.Frame(row2)
        row2_2.pack(fill=tk.X, pady=2)
        
        self.trigger_scan_subs_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(row2_2, text="Trigger on Subtitle", variable=self.trigger_scan_subs_var).pack(side=tk.LEFT, padx=(5,5))

        cb_autodetect = ttk.Checkbutton(row2_2, text="Auto-detect Subtitles", variable=self.trigger_autodetect_subs_var)
        cb_autodetect.pack(side=tk.LEFT, padx=(10, 5))
        ToolTip(cb_autodetect, "Auto-pick a subtitle file/stream when adding jobs for this preset.")
        
        self.trigger_suffix_enable_var = tk.BooleanVar(value=False)
        self.trigger_include_suffix_var = tk.BooleanVar(value=False)
        cb_restrict = ttk.Checkbutton(row2_2, text="Restrict to Suffix:", variable=self.trigger_suffix_enable_var)
        cb_restrict.pack(side=tk.LEFT, padx=(10, 5))
        
        cb_include = ttk.Checkbutton(row2_2, text="Include Suffix:", variable=self.trigger_include_suffix_var)
        cb_include.pack(side=tk.LEFT, padx=(5, 5))

        self.trigger_suffix_var = tk.StringVar(value="")
        entry_widget = ttk.Entry(row2_2, textvariable=self.trigger_suffix_var, width=8)
        entry_widget.pack(side=tk.LEFT, padx=5)
        ToolTip(entry_widget, "If Restrict Checked: Matches ONLY subtitles with this suffix (e.g. '-cn').\nIf Include Checked: Matches main subtitle AND subtitles with this suffix.\nSupports multiple separated by commas: '-top, -bot'\nIf Unchecked: Matches ALL subtitles.")

        # Update Logic for UI states
        def update_trigger_ui(*args):
            scan_on = self.trigger_scan_subs_var.get()
            suffix_restrict = self.trigger_suffix_enable_var.get()
            suffix_include = self.trigger_include_suffix_var.get()
            
            entry_state = "normal" if (scan_on and (suffix_restrict or suffix_include)) else "disabled"
            entry_widget.config(state=entry_state)
            
        def on_restrict_toggle(*args):
            if self.trigger_suffix_enable_var.get():
                self.trigger_include_suffix_var.set(False)
            update_trigger_ui()
            
        def on_include_toggle(*args):
            if self.trigger_include_suffix_var.get():
                self.trigger_suffix_enable_var.set(False)
            update_trigger_ui()
        
        # Bind traces
        self.trigger_scan_subs_var.trace_add("write", lambda *a: update_trigger_ui())
        self.trigger_suffix_enable_var.trace_add("write", on_restrict_toggle)
        self.trigger_include_suffix_var.trace_add("write", on_include_toggle)
        
        # Initial call
        update_trigger_ui()
        
        # We need to manually invoke this once after loading a preset or init
        
    def setup_input_pane(self, parent):
        parent.rowconfigure(0, weight=1)
        parent.columnconfigure(0, weight=1)
        
        # Main container with PanedWindow
        file_group = ttk.LabelFrame(parent, text="Queues", padding=5)
        file_group.grid(row=0, column=0, sticky="nsew")
        file_group.rowconfigure(0, weight=1)
        file_group.columnconfigure(0, weight=1)

        paned = ttk.PanedWindow(file_group, orient=tk.VERTICAL)
        paned.grid(row=0, column=0, sticky="nsew")

        # --- Top Pane: Input Queue ---
        input_frame = ttk.LabelFrame(paned, text="Step 1: Input Files (Staging)", padding=5)
        paned.add(input_frame, weight=1)
        input_frame.rowconfigure(0, weight=1)
        input_frame.columnconfigure(0, weight=1)

        # Input Listbox
        il_container = ttk.Frame(input_frame)
        il_container.grid(row=0, column=0, sticky="nsew")
        il_container.rowconfigure(0, weight=1)
        il_container.columnconfigure(0, weight=1)

        self.input_scrollbar_v = ttk.Scrollbar(il_container, orient=tk.VERTICAL)
        self.input_scrollbar_v.grid(row=0, column=1, sticky="ns")
        self.input_scrollbar_h = ttk.Scrollbar(il_container, orient=tk.HORIZONTAL)
        self.input_scrollbar_h.grid(row=1, column=0, sticky="ew")
        
        self.input_listbox = tk.Listbox(il_container, selectmode=tk.EXTENDED, exportselection=False, 
                                      yscrollcommand=self.input_scrollbar_v.set, xscrollcommand=self.input_scrollbar_h.set)
        self.input_listbox.grid(row=0, column=0, sticky="nsew")
        
        self.input_scrollbar_v.config(command=self.input_listbox.yview)
        self.input_scrollbar_h.config(command=self.input_listbox.xview)
        self.input_listbox.bind("<Button-1>", lambda e: self._handle_listbox_empty_click(e, self.input_listbox))
        # self.input_listbox.bind("<<ListboxSelect>>", self.on_input_file_select) # Maybe needed later

        # Input Toolbar
        input_toolbar = ttk.Frame(input_frame)
        input_toolbar.grid(row=1, column=0, sticky="ew", pady=(5, 0))
        
        ttk.Button(input_toolbar, text="Add to Jobs (Scan Triggers)", command=self.promote_input_files_auto).pack(side=tk.LEFT, padx=2)
        ttk.Button(input_toolbar, text="Add to Jobs (Force Current Preset)", command=self.promote_input_files_manual).pack(side=tk.LEFT, padx=2)
        
        ttk.Label(input_toolbar, text="Filter:").pack(side=tk.LEFT, padx=(10, 2))
        self.input_filter_entry = ttk.Entry(input_toolbar, textvariable=self.input_filter_var, width=15)
        self.input_filter_entry.pack(side=tk.LEFT, padx=2)
        
        ttk.Checkbutton(input_toolbar, text="Inv", variable=self.input_filter_inverse_var).pack(side=tk.LEFT, padx=2)

        ttk.Button(input_toolbar, text="Remove Selected", command=self.remove_from_input_queue).pack(side=tk.RIGHT, padx=2)
        ttk.Button(input_toolbar, text="Clear Input", command=self.clear_input_queue).pack(side=tk.RIGHT, padx=2)

        # --- Bottom Pane: Job Queue ---
        job_frame = ttk.LabelFrame(paned, text="Step 2: Processing Jobs", padding=5)
        paned.add(job_frame, weight=1)
        job_frame.rowconfigure(0, weight=1)
        job_frame.columnconfigure(0, weight=1)

        # Job Listbox
        jl_container = ttk.Frame(job_frame)
        jl_container.grid(row=0, column=0, sticky="nsew")
        jl_container.rowconfigure(0, weight=1)
        jl_container.columnconfigure(0, weight=1)

        self.job_scrollbar_v = ttk.Scrollbar(jl_container, orient=tk.VERTICAL)
        self.job_scrollbar_v.grid(row=0, column=1, sticky="ns")
        self.job_scrollbar_h = ttk.Scrollbar(jl_container, orient=tk.HORIZONTAL)
        self.job_scrollbar_h.grid(row=1, column=0, sticky="ew")
        
        self.job_listbox = tk.Listbox(jl_container, selectmode=tk.EXTENDED, exportselection=False, 
                                    yscrollcommand=self.job_scrollbar_v.set, xscrollcommand=self.job_scrollbar_h.set)
        self.job_listbox.grid(row=0, column=0, sticky="nsew")
        
        self.job_scrollbar_v.config(command=self.job_listbox.yview)
        self.job_scrollbar_h.config(command=self.job_listbox.xview)
        self.job_listbox.bind("<<ListboxSelect>>", self.on_job_select)
        self.job_listbox.bind("<Button-1>", lambda e: self._handle_listbox_empty_click(e, self.job_listbox))

        # Job Toolbar
        job_toolbar = ttk.Frame(job_frame)
        job_toolbar.grid(row=1, column=0, sticky="ew", pady=(5, 0))
        
        ttk.Button(job_toolbar, text="Select All", command=self.select_all_jobs).pack(side=tk.LEFT, padx=2)
        ttk.Button(job_toolbar, text="Clear Jobs", command=self.clear_all_jobs).pack(side=tk.RIGHT, padx=2)
        ttk.Button(job_toolbar, text="Remove Selected", command=self.remove_selected_jobs).pack(side=tk.RIGHT, padx=2)
        
        # Extra Selection Tools (Optional, kept from old UI)
        extra_tools = ttk.Frame(job_toolbar)
        extra_tools.pack(side=tk.LEFT, padx=10)
        ttk.Button(extra_tools, text="Sel Preset", command=self.select_jobs_by_current_preset).pack(side=tk.LEFT, padx=1)


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
        self.orientation_both_rb = ttk.Radiobutton(orientation_frame, text="Horizontal / Vertical", variable=self.orientation_var, value="horizontal + vertical", command=self._toggle_orientation_options)
        self.orientation_both_rb.pack(side=tk.LEFT)
        self.orientation_original_rb = ttk.Radiobutton(orientation_frame, text="Original", variable=self.orientation_var, value="original", command=self._toggle_orientation_options)
        self.orientation_original_rb.pack(side=tk.LEFT, padx=5)
        self.orientation_hybrid_rb = ttk.Radiobutton(orientation_frame, text="Hybrid", variable=self.orientation_var, value="hybrid (stacked)", command=self._toggle_orientation_options)
        self.orientation_hybrid_rb.pack(side=tk.LEFT, padx=(5,0))
        self.orientation_hybrid_duo_rb = ttk.Radiobutton(orientation_frame, text="Hybrid Duo", variable=self.orientation_var, value="hybrid-duo (dual source)", command=self._toggle_orientation_options)
        self.orientation_hybrid_duo_rb.pack(side=tk.LEFT, padx=(5,0))

        self.aspect_ratio_frame = ttk.LabelFrame(geometry_group, text="Aspect Ratio", padding=10); self.aspect_ratio_frame.pack(fill=tk.X, pady=5)
        self.aspect_columns_frame = ttk.Frame(self.aspect_ratio_frame)
        self.horizontal_rb_frame = ttk.Frame(self.aspect_columns_frame)
        ttk.Label(self.horizontal_rb_frame, text="Horizontal").pack(anchor="w")
        ttk.Radiobutton(self.horizontal_rb_frame, text="16:9 (Widescreen)", variable=self.merged_aspect_var, value="16:9", command=lambda: self._on_merged_aspect_change("16:9")).pack(anchor="w")
        ttk.Radiobutton(self.horizontal_rb_frame, text="5:4", variable=self.merged_aspect_var, value="5:4", command=lambda: self._on_merged_aspect_change("5:4")).pack(anchor="w")
        ttk.Radiobutton(self.horizontal_rb_frame, text="4:3 (Classic TV)", variable=self.merged_aspect_var, value="4:3", command=lambda: self._on_merged_aspect_change("4:3")).pack(anchor="w")
        self.vertical_rb_frame = ttk.Frame(self.aspect_columns_frame)
        ttk.Label(self.vertical_rb_frame, text="Vertical").pack(anchor="w")
        ttk.Radiobutton(self.vertical_rb_frame, text="9:16 (Shorts/Reels)", variable=self.merged_aspect_var, value="9:16", command=lambda: self._on_merged_aspect_change("9:16")).pack(anchor="w")
        ttk.Radiobutton(self.vertical_rb_frame, text="4:5 (Instagram Post)", variable=self.merged_aspect_var, value="4:5", command=lambda: self._on_merged_aspect_change("4:5")).pack(anchor="w")
        ttk.Radiobutton(self.vertical_rb_frame, text="3:4 (Social Post)", variable=self.merged_aspect_var, value="3:4", command=lambda: self._on_merged_aspect_change("3:4")).pack(anchor="w")

        self.hybrid_frame = ttk.Frame(geometry_group)
        
        # --- Top Video Frame ---
        self.top_video_frame = ttk.LabelFrame(self.hybrid_frame, text="Top Video", padding=5)
        self.top_video_frame.pack(fill=tk.X, pady=(5,0))
        
        self.top_file_frame = ttk.Frame(self.top_video_frame)
        self.top_file_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(self.top_file_frame, text="File Override:").pack(side=tk.LEFT, padx=(0,5))
        top_entry = ttk.Entry(self.top_file_frame, textvariable=self.hybrid_top_path_var)
        top_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ToolTip(top_entry, "Leave blank to use primary job video, or browse to force a specific file.")
        ttk.Button(self.top_file_frame, text="Browse", command=lambda: self._browse_hybrid_file('top'), width=7).pack(side=tk.LEFT, padx=(5,0))
        ttk.Button(self.top_file_frame, text="Clear", command=lambda: self.hybrid_top_path_var.set(""), width=5).pack(side=tk.LEFT, padx=(5,0))

        top_aspect_frame = ttk.Frame(self.top_video_frame)
        top_aspect_frame.pack(fill=tk.X)
        ttk.Label(top_aspect_frame, text="Aspect:").pack(side=tk.LEFT, padx=(0,5))
        ttk.Radiobutton(top_aspect_frame, text="16:9", variable=self.hybrid_top_aspect_var, value="16:9", command=lambda: self._update_selected_jobs("hybrid_top_aspect")).pack(side=tk.LEFT)
        ttk.Radiobutton(top_aspect_frame, text="4:5", variable=self.hybrid_top_aspect_var, value="4:5", command=lambda: self._update_selected_jobs("hybrid_top_aspect")).pack(side=tk.LEFT)
        ttk.Radiobutton(top_aspect_frame, text="4:3", variable=self.hybrid_top_aspect_var, value="4:3", command=lambda: self._update_selected_jobs("hybrid_top_aspect")).pack(side=tk.LEFT, padx=5)
        ttk.Label(top_aspect_frame, text="Handling:").pack(side=tk.LEFT, padx=(15,5))
        ttk.Radiobutton(top_aspect_frame, text="Crop", variable=self.hybrid_top_mode_var, value="crop", command=lambda: self._update_selected_jobs("hybrid_top_mode")).pack(side=tk.LEFT)
        ttk.Radiobutton(top_aspect_frame, text="Pad", variable=self.hybrid_top_mode_var, value="pad", command=lambda: self._update_selected_jobs("hybrid_top_mode")).pack(side=tk.LEFT, padx=5)

        # --- Bottom Video Frame ---
        self.bottom_video_frame = ttk.LabelFrame(self.hybrid_frame, text="Bottom Video", padding=5)
        self.bottom_video_frame.pack(fill=tk.X, pady=5)
        
        self.bot_file_frame = ttk.Frame(self.bottom_video_frame)
        self.bot_file_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(self.bot_file_frame, text="File Override:").pack(side=tk.LEFT, padx=(0,5))
        bot_entry = ttk.Entry(self.bot_file_frame, textvariable=self.hybrid_bottom_path_var)
        bot_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ToolTip(bot_entry, "Leave blank to auto-detect '-bot' sibling, or browse to force a specific file.")
        ttk.Button(self.bot_file_frame, text="Browse", command=lambda: self._browse_hybrid_file('bottom'), width=7).pack(side=tk.LEFT, padx=(5,0))
        ttk.Button(self.bot_file_frame, text="Clear", command=lambda: self.hybrid_bottom_path_var.set(""), width=5).pack(side=tk.LEFT, padx=(5,0))

        bot_aspect_frame = ttk.Frame(self.bottom_video_frame)
        bot_aspect_frame.pack(fill=tk.X)
        ttk.Label(bot_aspect_frame, text="Aspect:").pack(side=tk.LEFT, padx=(0,5))
        ttk.Radiobutton(bot_aspect_frame, text="16:9", variable=self.hybrid_bottom_aspect_var, value="16:9", command=lambda: self._update_selected_jobs("hybrid_bottom_aspect")).pack(side=tk.LEFT)
        ttk.Radiobutton(bot_aspect_frame, text="4:5", variable=self.hybrid_bottom_aspect_var, value="4:5", command=lambda: self._update_selected_jobs("hybrid_bottom_aspect")).pack(side=tk.LEFT)
        ttk.Radiobutton(bot_aspect_frame, text="4:3", variable=self.hybrid_bottom_aspect_var, value="4:3", command=lambda: self._update_selected_jobs("hybrid_bottom_aspect")).pack(side=tk.LEFT, padx=5)
        ttk.Label(bot_aspect_frame, text="Handling:").pack(side=tk.LEFT, padx=(15,5))
        ttk.Radiobutton(bot_aspect_frame, text="Crop", variable=self.hybrid_bottom_mode_var, value="crop", command=lambda: self._update_selected_jobs("hybrid_bottom_mode")).pack(side=tk.LEFT)
        ttk.Radiobutton(bot_aspect_frame, text="Pad", variable=self.hybrid_bottom_mode_var, value="pad", command=lambda: self._update_selected_jobs("hybrid_bottom_mode")).pack(side=tk.LEFT, padx=5)
        aspect_handling_frame = ttk.Frame(geometry_group); aspect_handling_frame.pack(fill=tk.X, pady=5)
        ttk.Label(aspect_handling_frame, text="Handling:").pack(side=tk.LEFT, padx=(0,5))
        self.aspect_crop_rb = ttk.Radiobutton(aspect_handling_frame, text="Crop (Fill)", variable=self.aspect_mode_var, value="crop", command=self._toggle_upscale_options)
        self.aspect_crop_rb.pack(side=tk.LEFT)
        self.aspect_pad_rb = ttk.Radiobutton(aspect_handling_frame, text="Pad (Fit)", variable=self.aspect_mode_var, value="pad", command=self._toggle_upscale_options)
        self.aspect_pad_rb.pack(side=tk.LEFT, padx=(5, 2))
        self.pad_color_swatch = tk.Label(aspect_handling_frame, width=2, relief="solid", bg=self.pad_color_var.get())
        self.pad_color_swatch.pack(side=tk.LEFT)
        self.pad_color_btn = ttk.Button(aspect_handling_frame, text="..", command=lambda: self.choose_color(self.pad_color_var, self.pad_color_swatch, "pad_color"), width=2)
        self.pad_color_btn.pack(side=tk.LEFT, padx=(0, 5))
        ToolTip(self.pad_color_btn, "Padding Color (FFmpeg Only). Disabled if NVEncC handles padding.")
        self.aspect_stretch_rb = ttk.Radiobutton(aspect_handling_frame, text="Stretch", variable=self.aspect_mode_var, value="stretch", command=self._toggle_upscale_options)
        self.aspect_stretch_rb.pack(side=tk.LEFT)
        self.aspect_blur_rb = ttk.Radiobutton(aspect_handling_frame, text="Blur (Bg)", variable=self.aspect_mode_var, value="blur", command=self._toggle_upscale_options)
        self.aspect_blur_rb.pack(side=tk.LEFT, padx=5)
        self.aspect_pixelate_rb = ttk.Radiobutton(aspect_handling_frame, text="Pixelate (Bg)", variable=self.aspect_mode_var, value="pixelate", command=self._toggle_upscale_options)
        self.aspect_pixelate_rb.pack(side=tk.LEFT)
        self.aspect_ambient_rb = ttk.Radiobutton(aspect_handling_frame, text="Ambient (Glow)", variable=self.aspect_mode_var, value="ambient", command=self._toggle_upscale_options)
        self.aspect_ambient_rb.pack(side=tk.LEFT, padx=5)
        
        aspect_params_frame = ttk.Frame(geometry_group); aspect_params_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(aspect_params_frame, text="Mult:").pack(side=tk.LEFT, padx=(0, 2))
        self.pixelate_multiplier_entry = ttk.Entry(aspect_params_frame, textvariable=self.pixelate_multiplier_var, width=3)
        self.pixelate_multiplier_entry.pack(side=tk.LEFT)
        ToolTip(self.pixelate_multiplier_entry, "Pixelation factor. 16 is default.")

        ttk.Label(aspect_params_frame, text="Dark:").pack(side=tk.LEFT, padx=(5, 2))
        self.pixelate_brightness_entry = ttk.Entry(aspect_params_frame, textvariable=self.pixelate_brightness_var, width=4)
        self.pixelate_brightness_entry.pack(side=tk.LEFT)
        ToolTip(self.pixelate_brightness_entry, "Darkness level. -0.4 is default. Lower is darker.")

        ttk.Label(aspect_params_frame, text="Sat:").pack(side=tk.LEFT, padx=(5, 2))
        self.pixelate_saturation_entry = ttk.Entry(aspect_params_frame, textvariable=self.pixelate_saturation_var, width=3)
        self.pixelate_saturation_entry.pack(side=tk.LEFT)
        ToolTip(self.pixelate_saturation_entry, "Saturation boost. 0.6 is default. 1.0 is original.")

        ttk.Label(aspect_params_frame, text="Sigma:").pack(side=tk.LEFT, padx=(5, 2))
        self.blur_sigma_entry = ttk.Entry(aspect_params_frame, textvariable=self.blur_sigma_var, width=3)
        self.blur_sigma_entry.pack(side=tk.LEFT)
        ToolTip(self.blur_sigma_entry, "Blur strength. 30 is default. Higher = more blur.")

        ttk.Label(aspect_params_frame, text="Steps:").pack(side=tk.LEFT, padx=(5, 2))
        self.blur_steps_entry = ttk.Entry(aspect_params_frame, textvariable=self.blur_steps_var, width=2)
        self.blur_steps_entry.pack(side=tk.LEFT)
        ToolTip(self.blur_steps_entry, "Blur quality. 1 is default. Higher = smoother (1-6).")
        
        ttk.Label(aspect_params_frame, text="Spread:").pack(side=tk.LEFT, padx=(5, 2))
        self.ambient_spread_entry = ttk.Entry(aspect_params_frame, textvariable=self.ambient_spread_var, width=3)
        self.ambient_spread_entry.pack(side=tk.LEFT)
        ToolTip(self.ambient_spread_entry, "Ambient glow spread (downscale factor). 2 is default. Higher = wider glow.")

        ttk.Label(aspect_params_frame, text="X-Off:").pack(side=tk.LEFT, padx=(10, 2))
        self.video_offset_x_entry = ttk.Entry(aspect_params_frame, textvariable=self.video_offset_x_var, width=4)
        self.video_offset_x_entry.pack(side=tk.LEFT)
        ToolTip(self.video_offset_x_entry, "Horizontal video offset in pixels. Pos = Right, Neg = Left.")

        ttk.Label(aspect_params_frame, text="Y-Off:").pack(side=tk.LEFT, padx=(5, 2))
        self.video_offset_y_entry = ttk.Entry(aspect_params_frame, textvariable=self.video_offset_y_var, width=4)
        self.video_offset_y_entry.pack(side=tk.LEFT)
        ToolTip(self.video_offset_y_entry, "Vertical video offset in pixels. Pos = Down, Neg = Up.")

        quality_group = ttk.LabelFrame(parent, text="Format & Quality", padding=10); quality_group.pack(fill=tk.X, pady=(5, 5))
        resolution_options_frame = ttk.Frame(quality_group); resolution_options_frame.pack(fill=tk.X)
        ttk.Label(resolution_options_frame, text="Resolution:").pack(side=tk.LEFT, padx=(0,5))
        self.rb_original = ttk.Radiobutton(resolution_options_frame, text="Original", variable=self.resolution_var, value="original", command=lambda: self._update_selected_jobs("resolution")); self.rb_original.pack(side=tk.LEFT)
        self.rb_720p = ttk.Radiobutton(resolution_options_frame, text="720p", variable=self.resolution_var, value="720p", command=lambda: self._update_selected_jobs("resolution")); self.rb_720p.pack(side=tk.LEFT)
        self.rb_1080p = ttk.Radiobutton(resolution_options_frame, text="1080p", variable=self.resolution_var, value="1080p", command=lambda: self._update_selected_jobs("resolution")); self.rb_1080p.pack(side=tk.LEFT, padx=5)
        self.rb_2160p = ttk.Radiobutton(resolution_options_frame, text="2160p", variable=self.resolution_var, value="2160p", command=lambda: self._update_selected_jobs("resolution")); self.rb_2160p.pack(side=tk.LEFT)
        self.rb_4320p = ttk.Radiobutton(resolution_options_frame, text="4320p", variable=self.resolution_var, value="4320p", command=lambda: self._update_selected_jobs("resolution")); self.rb_4320p.pack(side=tk.LEFT, padx=5)
        
        upscale_frame = ttk.Frame(quality_group); upscale_frame.pack(fill=tk.X, pady=(5,0))
        ttk.Label(upscale_frame, text="Upscale Algo:").pack(side=tk.LEFT, padx=(0,5))
        self.upscale_algo_combo = ttk.Combobox(upscale_frame, textvariable=self.upscale_algo_var, values=["nearest", "bilinear", "bicubic", "lanczos", "spline36"], width=14, state="readonly")
        self.upscale_algo_combo.pack(side=tk.LEFT)
        self.upscale_algo_combo.bind("<<ComboboxSelected>>", lambda e: self._update_selected_jobs("upscale_algo"))
        ToolTip(self.upscale_algo_combo, "Nearest=Fastest, Bilinear=Fast, Bicubic=Default, Lanczos=Sharp, Spline36=Sharp/Smooth")

        # Super-Resolution Settings (NVEncC only)
        superres_frame = ttk.Frame(quality_group); superres_frame.pack(fill=tk.X, pady=(5,0))
        ttk.Label(superres_frame, text="NVVFX SuperRes Mode:").pack(side=tk.LEFT, padx=(0,5))
        self.superres_mode_combo = ttk.Combobox(superres_frame, textvariable=self.nvenc_superres_mode_var, values=["0", "1"], width=5, state="readonly")
        self.superres_mode_combo.pack(side=tk.LEFT)
        ToolTip(self.superres_mode_combo, "NVEncC nvvfx-superres mode (0=conservative, 1=aggressive).")

        ttk.Label(superres_frame, text="NGX VSR Quality:").pack(side=tk.LEFT, padx=(15,5))
        self.ngx_vsr_quality_combo = ttk.Combobox(superres_frame, textvariable=self.nvenc_ngx_vsr_quality_var, values=["1", "2", "3", "4"], width=5, state="readonly")
        self.ngx_vsr_quality_combo.pack(side=tk.LEFT)
        ToolTip(self.ngx_vsr_quality_combo, "NVEncC ngx vsr-quality (1-4).")

        self.nvvfx_denoise_check = ttk.Checkbutton(superres_frame, text="AI Video Denoising", variable=self.nvenc_nvvfx_denoise_var, command=lambda: self._update_selected_jobs("nvenc_nvvfx_denoise"))
        self.nvvfx_denoise_check.pack(side=tk.LEFT, padx=(15, 0))
        ToolTip(self.nvvfx_denoise_check, "Enable --vpp-nvvfx-denoise (NVEncC only).")

        self.ffmpeg_denoise_vulkan_check = ttk.Checkbutton(superres_frame, text="FFmpeg Vulkan Denoise", variable=self.ffmpeg_denoise_vulkan_var, command=lambda: self._update_selected_jobs("ffmpeg_denoise_vulkan"))
        self.ffmpeg_denoise_vulkan_check.pack(side=tk.LEFT, padx=(15, 0))
        ToolTip(self.ffmpeg_denoise_vulkan_check, "Enable nlmeans_vulkan noise reduction (FFmpeg backend).")

        output_format_frame = ttk.Frame(quality_group); output_format_frame.pack(fill=tk.X, pady=(5,0))
        ttk.Label(output_format_frame, text="Output Format:").pack(side=tk.LEFT, padx=(0,5))
        ttk.Radiobutton(output_format_frame, text="SDR", variable=self.output_format_var, value="sdr", command=self._on_output_format_change).pack(side=tk.LEFT)
        ttk.Radiobutton(output_format_frame, text="HDR", variable=self.output_format_var, value="hdr", command=self._on_output_format_change).pack(side=tk.LEFT, padx=5)
        ttk.Label(output_format_frame, text="Location:").pack(side=tk.LEFT, padx=(15,5))
        ttk.Radiobutton(output_format_frame, text="Local", variable=self.output_mode_var, value="local").pack(side=tk.LEFT)
        ttk.Radiobutton(output_format_frame, text="Pooled", variable=self.output_mode_var, value="pooled").pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(output_format_frame, text="Use Subfolders", variable=self.output_subfolders_var, 
                        command=lambda: self._update_selected_jobs("output_to_subfolders")).pack(side=tk.LEFT, padx=(15, 0))
        ttk.Checkbutton(output_format_frame, text="Include Subtitle Folder", variable=self.output_subfolder_by_subtitle_var, 
                        command=lambda: self._update_selected_jobs("output_subfolder_by_subtitle")).pack(side=tk.LEFT, padx=(10, 0))
        ttk.Checkbutton(output_format_frame, text="Group by Preset", variable=self.group_by_preset_var, 
                        command=lambda: self._update_selected_jobs("group_by_preset")).pack(side=tk.LEFT, padx=(10, 0))
        ttk.Checkbutton(output_format_frame, text="Group by Video", variable=self.group_by_video_var, 
                        command=lambda: self._update_selected_jobs("group_by_video")).pack(side=tk.LEFT, padx=(10, 0))
        
        ttk.Label(output_format_frame, text="Override:").pack(side=tk.LEFT, padx=(10, 2))
        override_entry = ttk.Entry(output_format_frame, textvariable=self.subfolder_override_var, width=12)
        override_entry.pack(side=tk.LEFT)
        ToolTip(override_entry, "Custom subfolder name to override Video/Preset names.")
        
        lut_frame = ttk.Frame(quality_group); lut_frame.pack(fill=tk.X, pady=(5,0))
        ttk.Label(lut_frame, text="LUT Path:").pack(side=tk.LEFT, padx=(0,5))
        self.lut_entry = ttk.Entry(lut_frame, textvariable=self.lut_file_var); self.lut_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(lut_frame, text="...", command=self.browse_lut_file, width=4).pack(side=tk.LEFT)
        
        # --- Target & Constraints Group ---
        constraints_group = ttk.LabelFrame(quality_group, text="Target & Constraints", padding=5)
        constraints_group.pack(fill=tk.X, pady=(5,0))
        
        con_row1 = ttk.Frame(constraints_group); con_row1.pack(fill=tk.X)
        ttk.Checkbutton(con_row1, text="Manual Bitrate", variable=self.override_bitrate_var, command=self._toggle_bitrate_override).pack(side=tk.LEFT)
        self.manual_bitrate_entry = ttk.Entry(con_row1, textvariable=self.manual_bitrate_var, width=8, state="disabled"); self.manual_bitrate_entry.pack(side=tk.LEFT, padx=5)
        ttk.Label(con_row1, text="kbps").pack(side=tk.LEFT)
        
        ttk.Label(con_row1, text="Max Size:").pack(side=tk.LEFT, padx=(20, 5))
        self.max_size_entry = ttk.Entry(con_row1, textvariable=self.max_size_mb_var, width=6); self.max_size_entry.pack(side=tk.LEFT)
        ToolTip(self.max_size_entry, "Max file size (MB). 0 = Disabled.")
        ttk.Label(con_row1, text="MB").pack(side=tk.LEFT, padx=(2,0))

        ttk.Label(con_row1, text="Max Dur:").pack(side=tk.LEFT, padx=(20, 5))
        self.max_dur_entry = ttk.Entry(con_row1, textvariable=self.max_duration_var, width=6); self.max_dur_entry.pack(side=tk.LEFT)
        ToolTip(self.max_dur_entry, "Max duration (s). 0 = Disabled.")
        ttk.Label(con_row1, text="s").pack(side=tk.LEFT, padx=(2,0))
        fruc_frame = ttk.Frame(quality_group); fruc_frame.pack(fill=tk.X, pady=(5,0))
        ttk.Checkbutton(fruc_frame, text="Enable FRUC", variable=self.fruc_var, command=lambda: [self.toggle_fruc_fps(), self._update_selected_jobs("fruc")]).pack(side=tk.LEFT)
        ttk.Label(fruc_frame, text="FRUC FPS:").pack(side=tk.LEFT, padx=(5,5))
        self.fruc_fps_entry = ttk.Entry(fruc_frame, textvariable=self.fruc_fps_var, width=5, state="disabled"); self.fruc_fps_entry.pack(side=tk.LEFT)

        # Sharpening Group
        sharpen_group = ttk.LabelFrame(quality_group, text="Sharpening", padding=10); sharpen_group.pack(fill=tk.X, pady=(5,0))
        ttk.Checkbutton(sharpen_group, text="Enable Sharpening", variable=self.use_sharpening_var, command=lambda: self._update_selected_jobs("use_sharpening")).pack(side=tk.LEFT)
        ttk.Label(sharpen_group, text="Algo:").pack(side=tk.LEFT, padx=(10, 5))
        self.sharpen_algo_combo = ttk.Combobox(sharpen_group, textvariable=self.sharpening_algo_var, values=["cas", "unsharp"], width=8, state="readonly")
        self.sharpen_algo_combo.pack(side=tk.LEFT)
        self.sharpen_algo_combo.bind("<<ComboboxSelected>>", lambda e: self._update_selected_jobs("sharpening_algo"))
        ttk.Label(sharpen_group, text="Strength:").pack(side=tk.LEFT, padx=(10, 5))
        self.sharpen_strength_entry = ttk.Entry(sharpen_group, textvariable=self.sharpening_strength_var, width=5)
        self.sharpen_strength_entry.pack(side=tk.LEFT)
        ToolTip(sharpen_group, "CAS: 0.5 is ideal. Unsharp: 0.5-1.0 is good.")
        
        self._toggle_upscale_options()

    def setup_loudness_tab(self, parent):
        # --- Loudness & Normalization (Combined Group) ---
        loudness_group = ttk.LabelFrame(parent, text="Loudness & Normalization", padding=10)
        loudness_group.pack(fill=tk.X, pady=(0, 5))

        # Loudness War Checkbox
        self.loudness_war_checkbox = ttk.Checkbutton(loudness_group, text="Enable Compression & Limiting (acompressor + alimiter)", 
                        variable=self.use_loudness_war_var, 
                        command=self._toggle_audio_norm_options)
        self.loudness_war_checkbox.pack(anchor="w")

        self.lw_frame = ttk.Frame(loudness_group)
        self.lw_frame.pack(fill=tk.X, padx=(20, 0), pady=(2, 8))
        self.lw_frame.columnconfigure(1, weight=1)
        self.lw_frame.columnconfigure(3, weight=1)
        self.lw_frame.columnconfigure(5, weight=1)

        ttk.Label(self.lw_frame, text="Threshold (dB):").grid(row=0, column=0, sticky="w", pady=2)
        self.comp_threshold_entry = ttk.Entry(self.lw_frame, textvariable=self.comp_threshold_var, width=8)
        self.comp_threshold_entry.grid(row=0, column=1, sticky="w", padx=5)

        ttk.Label(self.lw_frame, text="Ratio:").grid(row=0, column=2, sticky="w", pady=2, padx=(10, 0))
        self.comp_ratio_entry = ttk.Entry(self.lw_frame, textvariable=self.comp_ratio_var, width=8)
        self.comp_ratio_entry.grid(row=0, column=3, sticky="w", padx=5)

        ttk.Label(self.lw_frame, text="Makeup Gain (dB):").grid(row=0, column=4, sticky="w", pady=2, padx=(10, 0))
        self.comp_makeup_entry = ttk.Entry(self.lw_frame, textvariable=self.comp_makeup_var, width=8)
        self.comp_makeup_entry.grid(row=0, column=5, sticky="w", padx=5)

        ttk.Label(self.lw_frame, text="Attack (ms):").grid(row=1, column=0, sticky="w", pady=2)
        self.comp_attack_entry = ttk.Entry(self.lw_frame, textvariable=self.comp_attack_var, width=8)
        self.comp_attack_entry.grid(row=1, column=1, sticky="w", padx=5)

        ttk.Label(self.lw_frame, text="Release (ms):").grid(row=1, column=2, sticky="w", pady=2, padx=(10, 0))
        self.comp_release_entry = ttk.Entry(self.lw_frame, textvariable=self.comp_release_var, width=8)
        self.comp_release_entry.grid(row=1, column=3, sticky="w", padx=5)

        ttk.Label(self.lw_frame, text="Limit Peak (dB):").grid(row=1, column=4, sticky="w", pady=2, padx=(10, 0))
        self.limit_limit_entry = ttk.Entry(self.lw_frame, textvariable=self.limit_limit_var, width=8)
        self.limit_limit_entry.grid(row=1, column=5, sticky="w", padx=5)
        
        # Dynamic Normalization Checkbox
        self.dyn_norm_checkbox = ttk.Checkbutton(loudness_group, text="Dynamic Normalization (dynaudnorm)", variable=self.use_dynaudnorm_var, 
                        command=self._toggle_audio_norm_options)
        self.dyn_norm_checkbox.pack(anchor="w", pady=(5, 0))
        
        self.dyn_norm_frame = ttk.Frame(loudness_group)
        self.dyn_norm_frame.pack(fill=tk.X, padx=(20, 0), pady=(2, 8))
        self.dyn_norm_frame.columnconfigure(1, weight=1)
        ttk.Label(self.dyn_norm_frame, text="Frame Len (ms):").grid(row=0, column=0, sticky="w", pady=2)
        self.dyn_frame_len_entry = ttk.Entry(self.dyn_norm_frame, textvariable=self.dyn_frame_len_var, width=8)
        self.dyn_frame_len_entry.grid(row=0, column=1, sticky="w", padx=5)
        ttk.Label(self.dyn_norm_frame, text="Filter Window:").grid(row=0, column=2, sticky="w", pady=2, padx=(10, 0))
        self.dyn_gauss_win_entry = ttk.Entry(self.dyn_norm_frame, textvariable=self.dyn_gauss_win_var, width=8)
        self.dyn_gauss_win_entry.grid(row=0, column=3, sticky="w", padx=5)
        ttk.Label(self.dyn_norm_frame, text="Target Peak:").grid(row=1, column=0, sticky="w", pady=2)
        self.dyn_peak_entry = ttk.Entry(self.dyn_norm_frame, textvariable=self.dyn_peak_var, width=8)
        self.dyn_peak_entry.grid(row=1, column=1, sticky="w", padx=5)
        ttk.Label(self.dyn_norm_frame, text="Max Gain:").grid(row=1, column=2, sticky="w", pady=2, padx=(10, 0))
        self.dyn_max_gain_entry = ttk.Entry(self.dyn_norm_frame, textvariable=self.dyn_max_gain_var, width=8)
        self.dyn_max_gain_entry.grid(row=1, column=3, sticky="w", padx=5)

        # EBU R128 Normalization Checkbox
        self.audio_norm_checkbox = ttk.Checkbutton(loudness_group, text="EBU R128 Normalization (loudnorm)", variable=self.normalize_audio_var, 
                        command=self._toggle_audio_norm_options)
        self.audio_norm_checkbox.pack(anchor="w", pady=(5, 0))

        self.audio_norm_frame = ttk.Frame(loudness_group)
        self.audio_norm_frame.pack(fill=tk.X, padx=(20, 0), pady=(2, 8))
        self.audio_norm_frame.columnconfigure(1, weight=1)

        ttk.Label(self.audio_norm_frame, text="Loudness Target (LUFS):").grid(row=0, column=0, sticky="w", pady=2)
        self.loudness_target_entry = ttk.Entry(self.audio_norm_frame, textvariable=self.loudness_target_var, width=8)
        self.loudness_target_entry.grid(row=0, column=1, sticky="w", padx=5)

        ttk.Label(self.audio_norm_frame, text="Loudness Range (LRA):").grid(row=0, column=2, sticky="w", pady=2, padx=(10, 0))
        self.loudness_range_entry = ttk.Entry(self.audio_norm_frame, textvariable=self.loudness_range_var, width=8)
        self.loudness_range_entry.grid(row=0, column=3, sticky="w", padx=5)

        ttk.Label(self.audio_norm_frame, text="True Peak (dBTP):").grid(row=1, column=0, sticky="w", pady=2)
        self.true_peak_entry = ttk.Entry(self.audio_norm_frame, textvariable=self.true_peak_var, width=8)
        self.true_peak_entry.grid(row=1, column=1, sticky="w", padx=5)

        # Loudness Measurement Checkbox
        self.measure_loudness_checkbox = ttk.Checkbutton(loudness_group, text="Measure Output Loudness (Save JSON metadata)", 
                        variable=self.measure_loudness_var, 
                        command=lambda: self._update_selected_jobs("measure_loudness"))
        self.measure_loudness_checkbox.pack(anchor="w", pady=(5, 0))

    def setup_audio_tab(self, parent):
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

    def setup_title_tab(self, parent):
        # Enable Title Burn checkbox
        action_frame = ttk.Frame(parent)
        action_frame.pack(fill=tk.X, pady=(0, 10))
        self.title_burn_cb = ttk.Checkbutton(action_frame, text="Enable Title Burning", variable=self.title_burn_var, command=lambda: self._update_selected_jobs("title_burn_enabled"))
        self.title_burn_cb.pack(side=tk.LEFT)

        # Source Settings
        source_group = ttk.LabelFrame(parent, text="Title Source", padding=10)
        source_group.pack(fill=tk.X, pady=5)
        
        suffix_frame = ttk.Frame(source_group); suffix_frame.pack(fill=tk.X, pady=2)
        ttk.Label(suffix_frame, text="JSON Suffix:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Entry(suffix_frame, textvariable=self.title_json_suffix_var, width=15).pack(side=tk.LEFT)
        ttk.Label(suffix_frame, text="(e.g., -yt, -instagram, -tiktok)").pack(side=tk.LEFT, padx=(10, 0))

        sanitize_frame = ttk.Frame(source_group); sanitize_frame.pack(fill=tk.X, pady=2)
        ttk.Checkbutton(
            sanitize_frame,
            text="Remove hashtags from extracted title",
            variable=self.title_remove_hashtags_var,
            command=lambda: self._update_selected_jobs("title_remove_hashtags")
        ).pack(side=tk.LEFT)
        ttk.Checkbutton(
            sanitize_frame,
            text="Enable emoji in title",
            variable=self.title_enable_emoji_var,
            command=lambda: self._update_selected_jobs("title_enable_emoji")
        ).pack(side=tk.LEFT, padx=(15, 0))
        ttk.Checkbutton(
            sanitize_frame,
            text="Auto-detect title from JSON",
            variable=self.title_autodetect_var,
            command=self._on_title_autodetect_toggle
        ).pack(side=tk.LEFT, padx=(15, 0))
        
        override_frame = ttk.Frame(source_group); override_frame.pack(fill=tk.X, pady=2)
        ttk.Label(override_frame, text="Title:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Entry(override_frame, textvariable=self.title_override_var, width=50).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(override_frame, text="Detect", command=lambda: self.detect_title_for_selected(force=True), width=8).pack(side=tk.LEFT, padx=(5, 0))
        ToolTip(override_frame, "Auto-filled from detected JSON title when available. Edit this field to use your own title.")

        # Timing Settings
        timing_group = ttk.LabelFrame(parent, text="Display Timing", padding=10)
        timing_group.pack(fill=tk.X, pady=5)
        timing_frame = ttk.Frame(timing_group); timing_frame.pack(fill=tk.X)
        ttk.Label(timing_frame, text="Start Time:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Entry(timing_frame, textvariable=self.title_start_time_var, width=12).pack(side=tk.LEFT)
        ttk.Label(timing_frame, text="End Time:").pack(side=tk.LEFT, padx=(15, 5))
        ttk.Entry(timing_frame, textvariable=self.title_end_time_var, width=12).pack(side=tk.LEFT)
        ttk.Label(timing_frame, text="(Format: HH:MM:SS.cc)").pack(side=tk.LEFT, padx=(15, 0))

        # Styling
        main_style_group = ttk.LabelFrame(parent, text="Title Styling", padding=10)
        main_style_group.pack(fill=tk.BOTH, expand=True)

        # General Style
        general_style_frame = ttk.LabelFrame(main_style_group, text="General Style", padding=10)
        general_style_frame.pack(fill=tk.X, pady=5)
        font_frame = ttk.Frame(general_style_frame); font_frame.pack(fill=tk.X, pady=2)
        ttk.Label(font_frame, text="Font:").pack(side=tk.LEFT, padx=(0, 19))
        self.title_font_combo = ttk.Combobox(font_frame, textvariable=self.title_font_var, width=25)
        self.title_font_combo.pack(side=tk.LEFT, padx=5)
        self.title_font_combo.bind("<<ComboboxSelected>>", lambda e: self._update_selected_jobs("title_font"))
        # Populate fonts after the combo is created
        self.root.after(100, self._populate_title_fonts)
        ttk.Label(font_frame, text="Size:").pack(side=tk.LEFT, padx=(10, 5))
        ttk.Entry(font_frame, textvariable=self.title_font_size_var, width=5).pack(side=tk.LEFT)
        
        style_frame = ttk.Frame(general_style_frame); style_frame.pack(fill=tk.X, pady=2)
        ttk.Checkbutton(style_frame, text="Bold", variable=self.title_bold_var, command=lambda: self._update_selected_jobs("title_bold")).pack(side=tk.LEFT)
        ttk.Checkbutton(style_frame, text="Italic", variable=self.title_italic_var, command=lambda: self._update_selected_jobs("title_italic")).pack(side=tk.LEFT, padx=15)
        ttk.Checkbutton(style_frame, text="Underline", variable=self.title_underline_var, command=lambda: self._update_selected_jobs("title_underline")).pack(side=tk.LEFT)
        
        align_frame = ttk.Frame(general_style_frame); align_frame.pack(fill=tk.X, pady=2)
        ttk.Label(align_frame, text="Align:").pack(side=tk.LEFT, padx=(0, 15))
        ttk.Radiobutton(align_frame, text="Top", variable=self.title_alignment_var, value="top", command=lambda: self._update_selected_jobs("title_alignment")).pack(side=tk.LEFT)
        ttk.Radiobutton(align_frame, text="Mid", variable=self.title_alignment_var, value="middle", command=lambda: self._update_selected_jobs("title_alignment")).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(align_frame, text="Bot", variable=self.title_alignment_var, value="bottom", command=lambda: self._update_selected_jobs("title_alignment")).pack(side=tk.LEFT)
        ttk.Label(align_frame, text="V-Margin:").pack(side=tk.LEFT, padx=(10, 5))
        ttk.Entry(align_frame, textvariable=self.title_margin_v_var, width=5).pack(side=tk.LEFT)
        ttk.Label(align_frame, text="L-Margin:").pack(side=tk.LEFT, padx=(10, 5))
        ttk.Entry(align_frame, textvariable=self.title_margin_l_var, width=5).pack(side=tk.LEFT)
        ttk.Label(align_frame, text="R-Margin:").pack(side=tk.LEFT, padx=(10, 5))
        ttk.Entry(align_frame, textvariable=self.title_margin_r_var, width=5).pack(side=tk.LEFT)

        # Color Panes
        fill_pane = CollapsiblePane(main_style_group, "Fill Properties", initial_state='expanded')
        fill_pane.pack(fill=tk.X, pady=2, padx=2)
        outline_pane = CollapsiblePane(main_style_group, "Outline Properties")
        outline_pane.pack(fill=tk.X, pady=2, padx=2)
        shadow_pane = CollapsiblePane(main_style_group, "Shadow Properties")
        shadow_pane.pack(fill=tk.X, pady=2, padx=2)

        # Fill
        fill_pane.container.columnconfigure(3, weight=1)
        ttk.Label(fill_pane.container, text="Color:").grid(row=0, column=0, sticky="w", padx=(0,5))
        self.title_fill_swatch = tk.Label(fill_pane.container, text="    ", bg=self.title_fill_color_var.get(), relief="sunken"); self.title_fill_swatch.grid(row=0, column=1)
        ttk.Button(fill_pane.container, text="..", command=lambda: self.choose_color(self.title_fill_color_var, self.title_fill_swatch, "title_fill_color"), width=3).grid(row=0, column=2, padx=5)
        ttk.Label(fill_pane.container, text="Alpha:").grid(row=0, column=3, sticky="w", padx=(10,5))
        ttk.Scale(fill_pane.container, from_=0, to=255, variable=self.title_fill_alpha_var, orient=tk.HORIZONTAL, command=lambda v: self._update_selected_jobs("title_fill_alpha")).grid(row=0, column=4, sticky="ew")

        # Outline
        outline_pane.container.columnconfigure(3, weight=1)
        ttk.Label(outline_pane.container, text="Color:").grid(row=0, column=0, sticky="w", padx=(0,5))
        self.title_outline_swatch = tk.Label(outline_pane.container, text="    ", bg=self.title_outline_color_var.get(), relief="sunken"); self.title_outline_swatch.grid(row=0, column=1)
        ttk.Button(outline_pane.container, text="..", command=lambda: self.choose_color(self.title_outline_color_var, self.title_outline_swatch, "title_outline_color"), width=3).grid(row=0, column=2, padx=5)
        ttk.Label(outline_pane.container, text="Alpha:").grid(row=0, column=3, sticky="w", padx=(10,5))
        ttk.Scale(outline_pane.container, from_=0, to=255, variable=self.title_outline_alpha_var, orient=tk.HORIZONTAL, command=lambda v: self._update_selected_jobs("title_outline_alpha")).grid(row=0, column=4, sticky="ew")
        ttk.Label(outline_pane.container, text="Width:").grid(row=1, column=0, sticky="w", padx=(0,5), pady=(5,0))
        ttk.Entry(outline_pane.container, textvariable=self.title_outline_width_var, width=5).grid(row=1, column=1, pady=(5,0))

        # Shadow
        shadow_pane.container.columnconfigure(3, weight=1)
        ttk.Label(shadow_pane.container, text="Color:").grid(row=0, column=0, sticky="w", padx=(0,5))
        self.title_shadow_swatch = tk.Label(shadow_pane.container, text="    ", bg=self.title_shadow_color_var.get(), relief="sunken"); self.title_shadow_swatch.grid(row=0, column=1)
        ttk.Button(shadow_pane.container, text="..", command=lambda: self.choose_color(self.title_shadow_color_var, self.title_shadow_swatch, "title_shadow_color"), width=3).grid(row=0, column=2, padx=5)
        ttk.Label(shadow_pane.container, text="Alpha:").grid(row=0, column=3, sticky="w", padx=(10,5))
        ttk.Scale(shadow_pane.container, from_=0, to=255, variable=self.title_shadow_alpha_var, orient=tk.HORIZONTAL, command=lambda v: self._update_selected_jobs("title_shadow_alpha")).grid(row=0, column=4, sticky="ew")
        ttk.Label(shadow_pane.container, text="Offset X:").grid(row=1, column=0, sticky="w", padx=(0,5), pady=(5,0))
        ttk.Entry(shadow_pane.container, textvariable=self.title_shadow_offset_x_var, width=5).grid(row=1, column=1, pady=(5,0))
        ttk.Label(shadow_pane.container, text="Offset Y:").grid(row=1, column=2, sticky="w", padx=(10,5), pady=(5,0))
        ttk.Entry(shadow_pane.container, textvariable=self.title_shadow_offset_y_var, width=5).grid(row=1, column=3, pady=(5,0), sticky="w")
        ttk.Label(shadow_pane.container, text="Blur:").grid(row=2, column=0, sticky="w", padx=(0,5), pady=(5,0))
        ttk.Entry(shadow_pane.container, textvariable=self.title_shadow_blur_var, width=5).grid(row=2, column=1, pady=(5,0))

    def _populate_title_fonts(self):
        """Populate title font combo with available fonts."""
        try:
            import tkinter.font as tkFont
            fonts = sorted(set(tkFont.families()))
            self.title_font_combo['values'] = fonts
        except Exception:
            pass

    def setup_subtitle_tab(self, parent):
        action_frame = ttk.Frame(parent)
        action_frame.pack(fill=tk.X, pady=(0, 10))
        self.burn_subtitles_cb = ttk.Checkbutton(action_frame, text="Enable Subtitle Burning", variable=self.burn_subtitles_var, command=lambda: self._update_selected_jobs("burn_subtitles"))
        self.burn_subtitles_cb.pack(side=tk.LEFT)

        source_frame = ttk.LabelFrame(parent, text="Subtitle Source", padding=10)
        source_frame.pack(fill=tk.X, pady=(0, 10))
        source_row = ttk.Frame(source_frame); source_row.pack(fill=tk.X)
        ttk.Label(source_row, text="Subtitle File:").pack(side=tk.LEFT, padx=(0, 5))
        self.subtitle_path_entry = ttk.Entry(source_row, textvariable=self.subtitle_path_var, width=60)
        self.subtitle_path_entry.pack(side=tk.LEFT, padx=(0, 5), fill=tk.X, expand=True)
        self.subtitle_browse_btn = ttk.Button(source_row, text="Browse", command=self.browse_subtitle_file, width=8)
        self.subtitle_browse_btn.pack(side=tk.LEFT, padx=(0, 5))
        self.subtitle_detect_btn = ttk.Button(source_row, text="Detect", command=self.detect_subtitle_for_selected, width=8)
        self.subtitle_detect_btn.pack(side=tk.LEFT)

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
        
        self.seam_h_lbl = ttk.Label(align_frame, text="H-Offset:")
        self.seam_h_lbl.pack(side=tk.LEFT, padx=(5, 2))
        self.seam_h_entry = ttk.Entry(align_frame, textvariable=self.subtitle_seam_h_offset_var, width=5)
        self.seam_h_entry.pack(side=tk.LEFT)
        self.seam_v_lbl = ttk.Label(align_frame, text="V-Offset:")
        self.seam_v_lbl.pack(side=tk.LEFT, padx=(5, 2))
        self.seam_v_entry = ttk.Entry(align_frame, textvariable=self.subtitle_seam_v_offset_var, width=5)
        self.seam_v_entry.pack(side=tk.LEFT)

        ttk.Label(align_frame, text="V-Margin:").pack(side=tk.LEFT, padx=(10, 5))
        margin_v_entry = ttk.Entry(align_frame, textvariable=self.subtitle_margin_v_var, width=5)
        margin_v_entry.pack(side=tk.LEFT)
        ttk.Label(align_frame, text="L-Margin:").pack(side=tk.LEFT, padx=(10, 5))
        margin_l_entry = ttk.Entry(align_frame, textvariable=self.subtitle_margin_l_var, width=5)
        margin_l_entry.pack(side=tk.LEFT)
        ttk.Label(align_frame, text="R-Margin:").pack(side=tk.LEFT, padx=(10, 5))
        margin_r_entry = ttk.Entry(align_frame, textvariable=self.subtitle_margin_r_var, width=5)
        margin_r_entry.pack(side=tk.LEFT)
        reformat_frame = ttk.LabelFrame(main_style_group, text="Line Formatting", padding=10)
        reformat_frame.pack(fill=tk.X, pady=5)
        ttk.Checkbutton(reformat_frame, text="Reformat to Single Wrapped Line", variable=self.reformat_subtitles_var, command=lambda: self._update_selected_jobs("reformat_subtitles")).pack(side=tk.LEFT)
        ttk.Label(reformat_frame, text="Wrap at:").pack(side=tk.LEFT, padx=(10, 5))
        wrap_limit_entry = ttk.Entry(reformat_frame, textvariable=self.wrap_limit_var, width=5)
        wrap_limit_entry.pack(side=tk.LEFT)
        ttk.Label(reformat_frame, text="chars").pack(side=tk.LEFT, padx=(2,0))
        ttk.Label(reformat_frame, text="Max lines:").pack(side=tk.LEFT, padx=(12, 5))
        ttk.Entry(reformat_frame, textvariable=self.subtitle_max_lines_var, width=5).pack(side=tk.LEFT)
        ttk.Label(reformat_frame, text="(0 = unlimited)").pack(side=tk.LEFT, padx=(2,0))

        fill_pane = CollapsiblePane(main_style_group, "Fill Properties", initial_state='expanded')
        fill_pane.pack(fill=tk.X, pady=2, padx=2)
        outline_pane = CollapsiblePane(main_style_group, "Outline Properties")
        outline_pane.pack(fill=tk.X, pady=2, padx=2)
        shadow_pane = CollapsiblePane(main_style_group, "Shadow Properties")
        shadow_pane.pack(fill=tk.X, pady=2, padx=2)

        fill_pane.container.columnconfigure(3, weight=1)
        ttk.Label(fill_pane.container, text="Color:").grid(row=0, column=0, sticky="w", padx=(0,5))
        self.fill_swatch = tk.Label(fill_pane.container, text="    ", bg=self.fill_color_var.get(), relief="sunken"); self.fill_swatch.grid(row=0, column=1)
        ttk.Button(fill_pane.container, text="..", command=lambda: self.choose_color(self.fill_color_var, self.fill_swatch, "fill_color"), width=3).grid(row=0, column=2, padx=5)
        fill_alpha_scale = ttk.Scale(fill_pane.container, from_=0, to=255, orient=tk.HORIZONTAL, variable=self.fill_alpha_var, command=lambda val: self._update_selected_jobs("fill_alpha"))
        fill_alpha_scale.grid(row=0, column=3, sticky="ew")

        outline_pane.container.columnconfigure(3, weight=1)
        ttk.Label(outline_pane.container, text="Color:").grid(row=0, column=0, sticky="w", padx=(0,5))
        self.outline_swatch = tk.Label(outline_pane.container, text="    ", bg=self.outline_color_var.get(), relief="sunken"); self.outline_swatch.grid(row=0, column=1)
        ttk.Button(outline_pane.container, text="..", command=lambda: self.choose_color(self.outline_color_var, self.outline_swatch, "outline_color"), width=3).grid(row=0, column=2, padx=5)
        outline_alpha_scale = ttk.Scale(outline_pane.container, from_=0, to=255, orient=tk.HORIZONTAL, variable=self.outline_alpha_var, command=lambda val: self._update_selected_jobs("outline_alpha"))
        outline_alpha_scale.grid(row=0, column=3, sticky="ew")
        ttk.Label(outline_pane.container, text="Width:").grid(row=1, column=0, sticky="w", pady=(5,0))
        outline_width_entry = ttk.Entry(outline_pane.container, textvariable=self.outline_width_var, width=5)
        outline_width_entry.grid(row=1, column=1, columnspan=2, sticky="w", pady=(5,0), padx=(0, 5))

        shadow_pane.container.columnconfigure(3, weight=1)
        ttk.Label(shadow_pane.container, text="Color:").grid(row=0, column=0, sticky="w", padx=(0,5))
        self.shadow_swatch = tk.Label(shadow_pane.container, text="    ", bg=self.shadow_color_var.get(), relief="sunken"); self.shadow_swatch.grid(row=0, column=1)
        ttk.Button(shadow_pane.container, text="..", command=lambda: self.choose_color(self.shadow_color_var, self.shadow_swatch, "shadow_color"), width=3).grid(row=0, column=2, padx=5)
        shadow_alpha_scale = ttk.Scale(shadow_pane.container, from_=0, to=255, orient=tk.HORIZONTAL, variable=self.shadow_alpha_var, command=lambda val: self._update_selected_jobs("shadow_alpha"))
        shadow_alpha_scale.grid(row=0, column=3, sticky="ew")
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
        self.close_gui_checkbox = ttk.Checkbutton(parent, text="Close GUI on Processing", variable=self.close_gui_var, command=lambda: self._update_selected_jobs("close_gui_on_processing"))
        self.close_gui_checkbox.pack(side=tk.LEFT, padx=(10, 0))
        self.hibernate_checkbox = ttk.Checkbutton(parent, text="Hibernate When Done", variable=self.hibernate_when_done_var, command=lambda: self._update_selected_jobs("hibernate_when_done"))
        self.hibernate_checkbox.pack(side=tk.LEFT, padx=(10, 0))

    def populate_fonts(self):
        try:
            fonts = sorted(list(font.families()))
            self.font_combo['values'] = fonts
            if DEFAULT_SUBTITLE_FONT in fonts:
                self.font_combo.set(DEFAULT_SUBTITLE_FONT)
            elif fonts:
                self.font_combo.set(fonts[0])
        except Exception as e:
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

    def browse_subtitle_file(self):
        file_path = filedialog.askopenfilename(
            title="Select Subtitle File",
            filetypes=[("Subtitle files", "*.srt;*.ass;*.ssa"), ("All files", "*.*")]
        )
        if file_path:
            self.subtitle_path_var.set(file_path)

    def _on_subtitle_path_change(self):
        if self._suppress_subtitle_path_trace:
            return
        self._apply_subtitle_path_to_selected(self.subtitle_path_var.get())

    def _build_display_tag_for_subtitle(self, subtitle_path):
        if not subtitle_path:
            return "[No Subtitles]"
        if subtitle_path.startswith("embedded:"):
            return f"[Embedded: {subtitle_path.split(':', 1)[1]}]"
        return f"(Custom: {os.path.basename(subtitle_path)})"

    def _detect_title_text_for_job(self, job):
        options = job.get("options", {})
        _, detected_title = find_title_json_file(
            job.get("video_path"),
            job.get("subtitle_path"),
            options.get("title_json_suffix", ""),
            remove_hashtags=options.get("title_remove_hashtags", DEFAULT_TITLE_REMOVE_HASHTAGS),
            keep_emoji=options.get("title_enable_emoji", DEFAULT_TITLE_ENABLE_EMOJI)
        )
        return detected_title

    def _autofill_title_for_job(self, job, force=False):
        options = job.get("options", {})
        if not force and not options.get("title_autodetect", DEFAULT_TITLE_AUTODETECT):
            return False
        current_title = (options.get("title_override_text", "") or "").strip()
        if current_title and not force:
            return False
        detected_title = self._detect_title_text_for_job(job)
        if not detected_title:
            return False
        options["title_override_text"] = detected_title
        return True

    def detect_title_for_selected(self, force=False):
        selected_indices = self.job_listbox.curselection()
        if not selected_indices:
            return
        updated = 0
        for index in selected_indices:
            job = self.processing_jobs[index]
            if self._autofill_title_for_job(job, force=force):
                updated += 1
        if updated == 0:
            messagebox.showinfo("No Title Found", "No matching title was detected from JSON for the selected job(s).")
        else:
            if len(selected_indices) == 1:
                self.title_override_var.set(self.processing_jobs[selected_indices[0]]['options'].get("title_override_text", ""))
            self.update_status(f"Detected titles for {updated} job(s).")

    def _on_title_autodetect_toggle(self):
        self._update_selected_jobs("title_autodetect")
        if self.title_autodetect_var.get():
            self.detect_title_for_selected(force=False)

    def _apply_subtitle_to_job(self, index, subtitle_path, display_tag):
        job = self.processing_jobs[index]
        job["subtitle_path"] = subtitle_path
        # Keep the Title field populated from detected metadata unless user typed one.
        self._autofill_title_for_job(job, force=False)
        job["display_tag"] = display_tag
        base_name = os.path.basename(job["video_path"])
        preset_name = job.get("preset_name", "")
        job["display_name"] = f"{base_name} {display_tag} [{preset_name}]".strip()
        self.job_listbox.delete(index)
        self.job_listbox.insert(index, job["display_name"])
        self.job_listbox.selection_set(index)

    def _apply_subtitle_path_to_selected(self, raw_path, display_tag=None):
        selected_indices = self.job_listbox.curselection()
        if not selected_indices:
            return
        subtitle_path = raw_path.strip()
        if not subtitle_path:
            subtitle_path = None
        for index in selected_indices:
            tag = display_tag if display_tag is not None else self._build_display_tag_for_subtitle(subtitle_path)
            self._apply_subtitle_to_job(index, subtitle_path, tag)

    def _detect_subtitles_for_video_single(self, video_path):
        detected_subs = []
        if not video_path or not os.path.exists(video_path):
            return detected_subs
        dir_name = os.path.dirname(video_path)
        video_basename = os.path.splitext(os.path.basename(video_path))[0]
        
        prefixes = [video_basename]
        for i in range(len(video_basename)-1, 0, -1):
            if video_basename[i] in [' ', '.', '-', '_']:
                prefixes.append(video_basename[:i])
                
        best_subs_by_suffix = {}
        
        try:
            for item in sorted(os.listdir(dir_name)):
                item_lower = item.lower()
                if item_lower.endswith((".srt", ".ass", ".ssa")):
                    sub_basename = os.path.splitext(item)[0]
                    
                    matched_prefix = None
                    matched_suffix = None
                    for prefix in prefixes:
                        if sub_basename == prefix:
                            matched_prefix = prefix
                            matched_suffix = ""
                            break
                        elif sub_basename.startswith(prefix):
                            remainder = sub_basename[len(prefix):]
                            if remainder and remainder[0] in [' ', '.', '-', '_']:
                                matched_prefix = prefix
                                matched_suffix = remainder
                                break
                                
                    if matched_prefix is not None:
                        prefix_len = len(matched_prefix)
                        if matched_suffix not in best_subs_by_suffix or prefix_len > best_subs_by_suffix[matched_suffix]['prefix_len']:
                            full_path = os.path.join(dir_name, item)
                            display_tag = "(Default)" if matched_suffix == "" else f"({matched_suffix.strip()})"
                            best_subs_by_suffix[matched_suffix] = {
                                'path': full_path,
                                'suffix': matched_suffix,
                                'display_tag': display_tag,
                                'basename': sub_basename,
                                'prefix_len': prefix_len
                            }
        except Exception:
            pass

        for suffix in sorted(best_subs_by_suffix.keys()):
            sub_info = best_subs_by_suffix[suffix].copy()
            del sub_info['prefix_len']
            detected_subs.append(sub_info)

        embedded_subs = get_subtitle_stream_info(video_path)
        for relative_index, sub_stream in enumerate(embedded_subs):
            tags = sub_stream.get("tags", {})
            lang = tags.get("language", "und")
            title = tags.get("title", f"Track {sub_stream.get('index')}")
            detected_subs.append({'path': f"embedded:{relative_index}", 'suffix': "", 'display_tag': f"[Embedded: {lang} - {title}]", 'basename': ""})

        return detected_subs

    def _detect_subtitles_for_video(self, video_path):
        base, ext = os.path.splitext(video_path)
        suffixes_top = ["-top", "_top"]
        suffixes_bot = ["-bot", "_bot", "-bottom", "_bottom"]
        
        is_paired = False
        prefix = None
        for s in suffixes_top + suffixes_bot:
            if base.endswith(s):
                is_paired = True
                prefix = base[:-len(s)]
                break
        
        if is_paired:
            top_file = None
            bot_file = None
            for s in suffixes_top:
                candidate = prefix + s + ext
                if os.path.exists(candidate):
                    top_file = candidate
                    break
            if not top_file:
                top_file = prefix + "-top" + ext
                
            for s in suffixes_bot:
                candidate = prefix + s + ext
                if os.path.exists(candidate):
                    bot_file = candidate
                    break
            if not bot_file:
                bot_file = prefix + "-bot" + ext
                
            top_subs = self._detect_subtitles_for_video_single(top_file)
            bot_subs = self._detect_subtitles_for_video_single(bot_file)
            
            combined = []
            seen = set()
            for sub in top_subs + bot_subs:
                if sub['path'] not in seen:
                    seen.add(sub['path'])
                    combined.append(sub)
            return combined
        else:
            return self._detect_subtitles_for_video_single(video_path)

    def _pick_preferred_subtitle(self, detected_subs):
        if not detected_subs:
            return None
        for sub in detected_subs:
            if not sub.get("path", "").startswith("embedded:") and sub.get("suffix", "") == "":
                return sub
        for sub in detected_subs:
            if not sub.get("path", "").startswith("embedded:"):
                return sub
        return detected_subs[0]

    def detect_subtitle_for_selected(self):
        selected_indices = self.job_listbox.curselection()
        if not selected_indices:
            return
        updated = 0
        for index in selected_indices:
            job = self.processing_jobs[index]
            detected_subs = self._detect_subtitles_for_video(job["video_path"])
            preferred = self._pick_preferred_subtitle(detected_subs)
            if preferred:
                self._apply_subtitle_to_job(index, preferred["path"], preferred["display_tag"])
                updated += 1
        if updated == 0:
            messagebox.showinfo("No Subtitles Found", "No matching subtitles were detected for the selected job(s).")
        else:
            if len(selected_indices) == 1:
                self._suppress_subtitle_path_trace = True
                self.subtitle_path_var.set(self.processing_jobs[selected_indices[0]].get("subtitle_path") or "")
                self._suppress_subtitle_path_trace = False
            self.update_status(f"Detected subtitles for {updated} job(s).")

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
            bitrate = get_bitrate(self.resolution_var.get(), info["framerate"], self.output_format_var.get() == 'hdr', source_height=info["height"], source_width=info["width"])
            self.manual_bitrate_var.set(str(bitrate))
    
    def _get_allowed_codecs(self):
        return ["h264", "hevc", "av1"] if self.output_format_var.get() == "sdr" else ["hevc", "av1"]

    def _update_codec_options(self, show_message=True):
        allowed = self._get_allowed_codecs()
        if hasattr(self, "video_codec_combo"):
            self.video_codec_combo.config(values=allowed)
        current = self.video_codec_var.get()
        if current not in allowed:
            new_codec = allowed[0]
            self.video_codec_var.set(new_codec)
            if show_message:
                messagebox.showinfo(
                    "Codec Updated",
                    f"HDR output requires HEVC or AV1.\nCodec set to '{new_codec}'."
                )

    def _on_output_format_change(self):
        self._update_codec_options(show_message=True)
        self._update_selected_jobs("output_format", "video_codec")
        self._update_bitrate_display()

    def _browse_hybrid_file(self, position):
        file_path = filedialog.askopenfilename(
            title=f"Select {position.capitalize()} Video",
            filetypes=[("Video Files", "*.mp4;*.mkv;*.avi;*.mov;*.webm;*.flv;*.wmv"), ("All Files", "*.*")]
        )
        if file_path:
            if position == 'top':
                self.hybrid_top_path_var.set(file_path)
            else:
                self.hybrid_bottom_path_var.set(file_path)

    def _toggle_orientation_options(self):
        orientation = self.orientation_var.get()
        current_alignment = self.subtitle_alignment_var.get()

        # Migrate legacy orientation values to merged mode in GUI.
        if orientation in ["horizontal", "vertical"]:
            self.orientation_var.set("horizontal + vertical")
            if orientation == "vertical":
                self.merged_aspect_var.set(self.vertical_aspect_var.get() or DEFAULT_VERTICAL_ASPECT)
            else:
                self.merged_aspect_var.set(self.horizontal_aspect_var.get() or DEFAULT_HORIZONTAL_ASPECT)
            orientation = "horizontal + vertical"

        if orientation in ["hybrid (stacked)", "hybrid-duo (dual source)"]:
            if current_alignment != "seam":
                self.last_standard_alignment.set(current_alignment)
                self.subtitle_alignment_var.set("seam")
            self.seam_align_rb.config(state="normal")
            self.seam_h_entry.config(state="normal")
            self.seam_v_entry.config(state="normal")
        else:
            if current_alignment == "seam":
                self.subtitle_alignment_var.set(self.last_standard_alignment.get())
            self.seam_align_rb.config(state="disabled")
            self.seam_h_entry.config(state="disabled")
            self.seam_v_entry.config(state="disabled")
        
        self.aspect_ratio_frame.pack_forget()
        self.aspect_columns_frame.pack_forget()
        self.horizontal_rb_frame.pack_forget()
        self.vertical_rb_frame.pack_forget()
        self.hybrid_frame.pack_forget()
        
        if orientation == "horizontal + vertical":
            self.aspect_ratio_frame.config(text="Aspect Ratios (H & V)")
            self.aspect_columns_frame.pack(fill="x")
            self.horizontal_rb_frame.pack(side=tk.LEFT, fill="both", expand=True, padx=(0, 10))
            self.vertical_rb_frame.pack(side=tk.LEFT, fill="both", expand=True)
            self.aspect_ratio_frame.pack(fill=tk.X, pady=5)
        elif orientation in ["hybrid (stacked)", "hybrid-duo (dual source)"]:
            self.aspect_ratio_frame.config(text="Canvas Aspect Ratio (Overall)")
            self.aspect_columns_frame.pack(fill="x")
            self.horizontal_rb_frame.pack(side=tk.LEFT, fill="both", expand=True, padx=(0, 10))
            self.vertical_rb_frame.pack(side=tk.LEFT, fill="both", expand=True)
            self.aspect_ratio_frame.pack(fill=tk.X, pady=5)
            self.hybrid_frame.pack(fill=tk.X, pady=5)
        elif orientation == "original":
            self.aspect_ratio_frame.config(text="Aspect Ratio (Original – unchanged)")
            self.aspect_ratio_frame.pack(fill=tk.X, pady=5)

        if orientation == "hybrid-duo (dual source)":
            if hasattr(self, 'top_file_frame'): self._set_widget_state_recursive(self.top_file_frame, "normal")
            if hasattr(self, 'bot_file_frame'): self._set_widget_state_recursive(self.bot_file_frame, "normal")
        elif orientation == "hybrid (stacked)":
            if hasattr(self, 'top_file_frame'): self._set_widget_state_recursive(self.top_file_frame, "disabled")
            if hasattr(self, 'bot_file_frame'): self._set_widget_state_recursive(self.bot_file_frame, "disabled")

        self._update_selected_jobs("orientation", "subtitle_alignment", "burn_subtitles")

    def _resolve_to_top_sibling(self, video_path):
        if not video_path:
            return video_path
        base, ext = os.path.splitext(video_path)
        suffixes_top = ["-top", "_top"]
        suffixes_bot = ["-bot", "_bot", "-bottom", "_bottom"]
        
        for s in suffixes_top:
            if base.endswith(s):
                return video_path
                
        for s in suffixes_bot:
            if base.endswith(s):
                prefix = base[:-len(s)]
                for st in suffixes_top:
                    candidate = prefix + st + ext
                    if os.path.exists(candidate):
                        return candidate
                return prefix + "-top" + ext
        return video_path

    def _aspect_to_orientation(self, aspect_str, fallback="horizontal"):
        try:
            num, den = map(int, str(aspect_str).split(":"))
            return "horizontal" if num >= den else "vertical"
        except Exception:
            return fallback

    def _resolve_orientation(self, options, requested_orientation):
        if requested_orientation == "horizontal + vertical":
            merged_aspect = options.get("merged_aspect", options.get("horizontal_aspect", DEFAULT_HORIZONTAL_ASPECT))
            return self._aspect_to_orientation(merged_aspect, fallback="horizontal")
        return requested_orientation

    def _on_merged_aspect_change(self, aspect_value):
        self.merged_aspect_var.set(aspect_value)
        if self._aspect_to_orientation(aspect_value) == "vertical":
            self.vertical_aspect_var.set(aspect_value)
        else:
            self.horizontal_aspect_var.set(aspect_value)
        self._update_selected_jobs("merged_aspect", "horizontal_aspect", "vertical_aspect")

    def _toggle_upscale_options(self):
        aspect_mode = self.aspect_mode_var.get()
        
        # Auto-boost saturation if switching to ambient and it's left at default 0.6
        if aspect_mode == "ambient" and self.pixelate_saturation_var.get() == "0.6":
            self.pixelate_saturation_var.set("1.5")
            
        # Pixelate controls (Mult, Dark, Sat)
        pixelate_state = "normal" if aspect_mode == "pixelate" else "disabled"
        self.pixelate_multiplier_entry.config(state=pixelate_state)
        
        # Shared controls (Dark, Sat) - enabled for both blur and pixelate and ambient (saturation)
        shared_state = "normal" if aspect_mode in ["pixelate", "blur", "ambient"] else "disabled"
        self.pixelate_brightness_entry.config(state=shared_state)
        self.pixelate_saturation_entry.config(state=shared_state)
        
        # Blur controls (Sigma, Steps)
        blur_state = "normal" if aspect_mode in ["blur", "ambient"] else "disabled"
        self.blur_sigma_entry.config(state=blur_state)
        self.blur_steps_entry.config(state=blur_state)
        
        # Ambient controls (Spread)
        ambient_state = "normal" if aspect_mode == "ambient" else "disabled"
        self.ambient_spread_entry.config(state=ambient_state)
        
        self._update_selected_jobs("aspect_mode")

    def _update_upscale_algo_options(self):
        backend = self.encoder_backend_var.get()
        if backend in ["nvencc_with_ffmpeg", "nvencc_only", "nvencc_video_with_ffmpeg_audio"]:
            values = ["nearest", "bilinear", "bicubic", "lanczos", "spline36", "nvvfx-superres", "ngx-vsr"]
        else:
            values = ["nearest", "bilinear", "bicubic", "lanczos"]
        if hasattr(self, "upscale_algo_combo"):
            self.upscale_algo_combo.config(values=values)
        if self.upscale_algo_var.get() not in values:
            self.upscale_algo_var.set(DEFAULT_UPSCALE_ALGO)

    def _toggle_superres_options(self):
        backend = self.encoder_backend_var.get()
        algo = self.upscale_algo_var.get()
        enable_superres = backend in ["nvencc_with_ffmpeg", "nvencc_only", "nvencc_video_with_ffmpeg_audio"] and algo == "nvvfx-superres"
        enable_ngx = backend in ["nvencc_with_ffmpeg", "nvencc_only", "nvencc_video_with_ffmpeg_audio"] and algo == "ngx-vsr"
        enable_nvencc_features = backend in ["nvencc_with_ffmpeg", "nvencc_only", "nvencc_video_with_ffmpeg_audio"]
        enable_ffmpeg_features = backend in ["ffmpeg_only", "nvencc_with_ffmpeg"]
        if hasattr(self, "superres_mode_combo"):
            self.superres_mode_combo.config(state="readonly" if enable_superres else "disabled")
        if hasattr(self, "ngx_vsr_quality_combo"):
            self.ngx_vsr_quality_combo.config(state="readonly" if enable_ngx else "disabled")
        if hasattr(self, "nvvfx_denoise_check"):
            self._set_widget_state_recursive(self.nvvfx_denoise_check, "normal" if enable_nvencc_features else "disabled")
        if hasattr(self, "ffmpeg_denoise_vulkan_check"):
            self._set_widget_state_recursive(self.ffmpeg_denoise_vulkan_check, "normal" if enable_ffmpeg_features else "disabled")

    def _toggle_nvencc_color_mode_controls(self):
        is_custom = getattr(self, "nvencc_color_tag_mode_var", None) and self.nvencc_color_tag_mode_var.get() == "custom"
        state = "readonly" if is_custom else "disabled"
        for widget_name in [
            "nvencc_output_depth_combo",
            "nvencc_color_prim_combo",
            "nvencc_color_transfer_combo",
            "nvencc_color_matrix_combo",
        ]:
            widget = getattr(self, widget_name, None)
            if widget:
                widget.config(state=state)

    def _set_widget_state_recursive(self, widget, state):
        try:
            widget.configure(state=state)
        except Exception:
            pass
        for child in widget.winfo_children():
            self._set_widget_state_recursive(child, state)

    def _apply_backend_constraints(self):
        backend = self.encoder_backend_var.get()
        is_nvencc_only = backend == "nvencc_only"
        is_nvencc_video_audio = backend == "nvencc_video_with_ffmpeg_audio"
        is_ffmpeg_only = backend == "ffmpeg_only"
        is_nvencc_video_backend = is_nvencc_only or is_nvencc_video_audio
        use_nvencc_resize = is_nvencc_video_backend or (backend == "nvencc_with_ffmpeg" and self.upscale_algo_var.get() in ["nvvfx-superres", "ngx-vsr"])

        # NVEncC-only or NVEncC video + FFmpeg audio: disable unsupported FFmpeg video-only features.
        # Subtitle burning is supported via NVEncC vpp-subburn.
        if is_nvencc_video_backend:
            # We NO LONGER disable Hybrid Stacked here, because if requested with NVEncC, 
            # we will dynamically route it to nvencc_with_ffmpeg during process_file.
            if self.aspect_mode_var.get() in ["blur", "pixelate", "ambient"]:
                self.aspect_mode_var.set("pad")
            self.fruc_var.set(False)
            if is_nvencc_only:
                self.normalize_audio_var.set(False)
                self.use_dynaudnorm_var.set(False)
                self.use_loudness_war_var.set(False)
                self.measure_loudness_var.set(False)
                self.audio_mono_var.set(False)
                self.audio_stereo_downmix_var.set(False)
                self.audio_stereo_sofalizer_var.set(False)
                self.audio_surround_51_var.set(False)
                self.audio_passthrough_var.set(True)
            self._update_selected_jobs(
                "orientation", "aspect_mode",
                "fruc"
            )
            if is_nvencc_only:
                self._update_selected_jobs(
                    "normalize_audio", "use_dynaudnorm", "use_loudness_war", "measure_loudness",
                    "audio_mono", "audio_stereo_downmix", "audio_stereo_sofalizer", "audio_surround_51", "audio_passthrough"
                )
            # Do not mutate every queued job here. Backend constraints should affect
            # current GUI state and selected jobs only, so mixed queues preserve
            # per-job options (e.g., Hybrid FFmpeg jobs alongside NVEncC jobs).

        # Disable/enable widgets
        if hasattr(self, "burn_subtitles_cb"):
            self.burn_subtitles_cb.config(state="normal")
        if hasattr(self, "title_burn_cb"):
            self.title_burn_cb.config(state="normal")

        for rb in [getattr(self, "aspect_crop_rb", None), getattr(self, "aspect_pad_rb", None),
                   getattr(self, "aspect_stretch_rb", None), getattr(self, "aspect_blur_rb", None),
                   getattr(self, "aspect_pixelate_rb", None), getattr(self, "aspect_ambient_rb", None)]:
            if rb:
                if rb in [getattr(self, "aspect_blur_rb", None), getattr(self, "aspect_pixelate_rb", None), getattr(self, "aspect_ambient_rb", None)]:
                    rb.config(state="disabled" if is_nvencc_video_backend else "normal")
                else:
                    rb.config(state="normal")
                    
        if hasattr(self, "pad_color_btn"):
            self.pad_color_btn.config(state="disabled" if use_nvencc_resize else "normal")

        # Orientation options: disable hybrid in NVEncC-only paths NO LONGER APPLIES. We support it by routing to nvencc_with_ffmpeg.
        if hasattr(self, "orientation_both_rb"):
            self.orientation_both_rb.config(state="normal")
        if hasattr(self, "orientation_hybrid_rb"):
            self.orientation_hybrid_rb.config(state="normal")
        if hasattr(self, "orientation_hybrid_duo_rb"):
            self.orientation_hybrid_duo_rb.config(state="normal")

        # Disable FFmpeg-only tabs in NVEncC-only (and video-only tabs in video+audio mode)
        for tab in [getattr(self, "audio_tab", None), getattr(self, "loudness_tab", None),
                    getattr(self, "subtitle_tab", None), getattr(self, "title_tab", None)]:
            if tab:
                if is_nvencc_only:
                    if tab in [self.subtitle_tab, self.title_tab]:
                        self._set_widget_state_recursive(tab, "normal")
                    else:
                        self._set_widget_state_recursive(tab, "disabled")
                elif is_nvencc_video_audio:
                    self._set_widget_state_recursive(tab, "normal")
                else:
                    self._set_widget_state_recursive(tab, "normal")

        # Audio and loudness controls are handled by _update_audio_options_ui and _toggle_audio_norm_options
        self._update_audio_options_ui()
        self._toggle_audio_norm_options()

        # NVEncC-only/FFmpeg-only impact superres controls
        self._update_upscale_algo_options()
        self._toggle_superres_options()

    def _toggle_audio_norm_options(self):
        is_passthrough = self.audio_passthrough_var.get()
        
        # If Passthrough is enabled, FORCE DISABLE all loudness controls
        # regardless of their individual checkbox states.
        
        state_ln = "normal" if self.normalize_audio_var.get() and not is_passthrough else "disabled"
        for widget in [self.loudness_target_entry, self.loudness_range_entry, self.true_peak_entry]:
            widget.config(state=state_ln)
        
        state_dyn = "normal" if self.use_dynaudnorm_var.get() and not is_passthrough else "disabled"
        for widget in [self.dyn_frame_len_entry, self.dyn_gauss_win_entry, self.dyn_peak_entry, self.dyn_max_gain_entry]:
            widget.config(state=state_dyn)
            
        state_lw = "normal" if self.use_loudness_war_var.get() and not is_passthrough else "disabled"
        for widget in [self.comp_threshold_entry, self.comp_ratio_entry, self.comp_makeup_entry, 
                       self.comp_attack_entry, self.comp_release_entry, self.limit_limit_entry]:
            widget.config(state=state_lw)

        self._update_selected_jobs("normalize_audio", "use_dynaudnorm", "use_loudness_war")

    def _update_audio_options_ui(self):
        # Force disable passthrough if chapter splitting is enabled
        if hasattr(self, 'render_by_chapters_var') and hasattr(self, 'audio_cb_passthrough'):
            if self.render_by_chapters_var.get():
                if self.audio_passthrough_var.get():
                    self.audio_passthrough_var.set(False)
                    if not any([self.audio_mono_var.get(), self.audio_stereo_downmix_var.get(), self.audio_stereo_sofalizer_var.get(), self.audio_surround_51_var.get()]):
                        self.audio_stereo_downmix_var.set(True)
                self.audio_cb_passthrough.config(state="disabled")
            else:
                self.audio_cb_passthrough.config(state="normal")
                
        is_passthrough = self.audio_passthrough_var.get()
        is_sofalizer = self.audio_stereo_sofalizer_var.get()

        if is_passthrough:
            self.audio_mono_var.set(False)
            self.audio_stereo_downmix_var.set(False)
            self.audio_stereo_sofalizer_var.set(False)
            self.audio_surround_51_var.set(False)
            proc_state = "disabled"
            
            # Disable Loudness Controls
            if hasattr(self, 'loudness_war_checkbox'): self.loudness_war_checkbox.config(state="disabled")
            if hasattr(self, 'dyn_norm_checkbox'): self.dyn_norm_checkbox.config(state="disabled")
            if hasattr(self, 'audio_norm_checkbox'): self.audio_norm_checkbox.config(state="disabled")
            if hasattr(self, 'measure_loudness_checkbox'): self.measure_loudness_checkbox.config(state="disabled")
        else:
            proc_state = "normal"
            # Re-enable Loudness Controls
            if hasattr(self, 'loudness_war_checkbox'): self.loudness_war_checkbox.config(state="normal")
            if hasattr(self, 'dyn_norm_checkbox'): self.dyn_norm_checkbox.config(state="normal")
            if hasattr(self, 'audio_norm_checkbox'): self.audio_norm_checkbox.config(state="normal")
            if hasattr(self, 'measure_loudness_checkbox'): self.measure_loudness_checkbox.config(state="normal")
        
        # Update sub-widgets for loudness
        self._toggle_audio_norm_options()
        
        for cb in [self.audio_cb_mono, self.audio_cb_stereo, self.audio_cb_sofa, self.audio_cb_surround]:
            cb.config(state=proc_state)
            
        any_proc_selected = any([self.audio_mono_var.get(), self.audio_stereo_downmix_var.get(),
                                 self.audio_stereo_sofalizer_var.get(), self.audio_surround_51_var.get()])

        self.audio_cb_passthrough.config(state="disabled" if any_proc_selected else "normal")

        sofa_state = "normal" if is_sofalizer and not is_passthrough else "disabled"
        self.sofa_entry.config(state=sofa_state)
        self.sofa_browse_btn.config(state=sofa_state)

        self._update_selected_jobs(
            "audio_mono", "audio_stereo_downmix", "audio_stereo_sofalizer",
            "audio_surround_51", "audio_passthrough", "sofa_file"
        )

    def update_status(self, message):
        self.status_var.set(message)
        # self.root.update_idletasks() # Not safe in thread, rely on mainloop

    def update_progress(self, percent):
        """Updates the progress bar in the GUI."""
        # This is called from the thread, but assigning to a ttk.Progressbar variable 
        # or configuring it is generally handled well by tk, but using after() is safer.
        try:
            self.root.after(0, lambda: self.progress_bar.config(value=percent))
        except Exception:
            pass  # GUI already destroyed (console mode)

    def _update_selected_jobs(self, *keys_to_update):
        if self._is_loading_job_to_gui:
            return
        selected_indices = self.job_listbox.curselection()
        if not selected_indices:
            return
        current_options = self.get_current_gui_options()
        options_to_apply = {key: current_options[key] for key in keys_to_update if key in current_options}
        if options_to_apply:
             for index in selected_indices:
                job = self.processing_jobs[index]
                job['options'].update(options_to_apply)

    def get_current_gui_options(self):
        return {
            "resolution": self.resolution_var.get(), "upscale_algo": self.upscale_algo_var.get(),
            "output_format": self.output_format_var.get(), "video_codec": self.video_codec_var.get(),
            "encoder_backend": self.encoder_backend_var.get(),
            "nvenc_nvvfx_denoise": self.nvenc_nvvfx_denoise_var.get(),
            "nvenc_superres_mode": self.nvenc_superres_mode_var.get(),
            "nvenc_ngx_vsr_quality": self.nvenc_ngx_vsr_quality_var.get(),
            "fruc": self.fruc_var.get(),
            "fruc_fps": self.fruc_fps_var.get(), "generate_log": self.generate_log_var.get(),
            "close_gui_on_processing": self.close_gui_var.get(),
            "hibernate_when_done": self.hibernate_when_done_var.get(),
            "render_by_chapters": self.render_by_chapters_var.get(),
            "split_subtitles_by_chapter": self.split_subtitles_by_chapter_var.get(),
            "orientation": self.orientation_var.get(), "aspect_mode": self.aspect_mode_var.get(),
            "pad_color": self.pad_color_var.get(),
            "video_offset_x": self.video_offset_x_var.get(),
            "video_offset_y": self.video_offset_y_var.get(),
            "pixelate_multiplier": self.pixelate_multiplier_var.get(),
            "ambient_spread": self.ambient_spread_var.get(),
            "pixelate_brightness": self.pixelate_brightness_var.get(),
            "pixelate_saturation": self.pixelate_saturation_var.get(),
            "blur_sigma": self.blur_sigma_var.get(),
            "blur_steps": self.blur_steps_var.get(),
            "horizontal_aspect": self.horizontal_aspect_var.get(), "vertical_aspect": self.vertical_aspect_var.get(),
            "merged_aspect": self.merged_aspect_var.get(),
            "burn_subtitles": self.burn_subtitles_var.get(), "override_bitrate": self.override_bitrate_var.get(),
            "manual_bitrate": self.manual_bitrate_var.get(), 
            "max_size_mb": self.max_size_mb_var.get(),
            "max_duration": self.max_duration_var.get(),
            "use_dynaudnorm": self.use_dynaudnorm_var.get(),
            "dyn_frame_len": self.dyn_frame_len_var.get(), "dyn_gauss_win": self.dyn_gauss_win_var.get(),
            "dyn_peak": self.dyn_peak_var.get(), "dyn_max_gain": self.dyn_max_gain_var.get(),
            "use_loudness_war": self.use_loudness_war_var.get(),
            "comp_threshold": self.comp_threshold_var.get(), "comp_ratio": self.comp_ratio_var.get(),
            "comp_attack": self.comp_attack_var.get(), "comp_release": self.comp_release_var.get(),
            "comp_makeup": self.comp_makeup_var.get(), "limit_limit": self.limit_limit_var.get(),
            "measure_loudness": self.measure_loudness_var.get(),
            "normalize_audio": self.normalize_audio_var.get(),
            "loudness_target": self.loudness_target_var.get(), "loudness_range": self.loudness_range_var.get(),
            "true_peak": self.true_peak_var.get(), 
            "audio_mono": self.audio_mono_var.get(), "audio_stereo_downmix": self.audio_stereo_downmix_var.get(),
            "audio_stereo_sofalizer": self.audio_stereo_sofalizer_var.get(), "audio_surround_51": self.audio_surround_51_var.get(),
            "audio_passthrough": self.audio_passthrough_var.get(),
            "sofa_file": self.sofa_file_var.get(),
            "lut_file": self.lut_file_var.get(),
            "hybrid_top_aspect": self.hybrid_top_aspect_var.get(), "hybrid_top_mode": self.hybrid_top_mode_var.get(),
            "hybrid_top_path": self.hybrid_top_path_var.get(),
            "hybrid_bottom_aspect": self.hybrid_bottom_aspect_var.get(), "hybrid_bottom_mode": self.hybrid_bottom_mode_var.get(),
            "hybrid_bottom_path": self.hybrid_bottom_path_var.get(),
            "subtitle_font": self.subtitle_font_var.get(), "subtitle_font_size": self.subtitle_font_size_var.get(),
            "subtitle_alignment": self.subtitle_alignment_var.get(), "subtitle_bold": self.subtitle_bold_var.get(),
            "subtitle_italic": self.subtitle_italic_var.get(), "subtitle_underline": self.subtitle_underline_var.get(),
            "subtitle_margin_v": self.subtitle_margin_v_var.get(), 
            "subtitle_margin_l": self.subtitle_margin_l_var.get(),
            "subtitle_margin_r": self.subtitle_margin_r_var.get(),
            "subtitle_seam_h_offset": self.subtitle_seam_h_offset_var.get(),
            "subtitle_seam_v_offset": self.subtitle_seam_v_offset_var.get(),
            "fill_color": self.fill_color_var.get(),
            "fill_alpha": self.fill_alpha_var.get(), "outline_color": self.outline_color_var.get(),
            "outline_alpha": self.outline_alpha_var.get(), "outline_width": self.outline_width_var.get(),
            "shadow_color": self.shadow_color_var.get(), "shadow_alpha": self.shadow_alpha_var.get(),
            "shadow_offset_x": self.shadow_offset_x_var.get(), "shadow_offset_y": self.shadow_offset_y_var.get(),
            "shadow_blur": self.shadow_blur_var.get(),
            "reformat_subtitles": self.reformat_subtitles_var.get(), "wrap_limit": self.wrap_limit_var.get(),
            "subtitle_max_lines": self.subtitle_max_lines_var.get(),
            "output_to_subfolders": self.output_subfolders_var.get(),
            "output_subfolder_by_subtitle": self.output_subfolder_by_subtitle_var.get(),
            "group_by_preset": self.group_by_preset_var.get(),
            "group_by_video": self.group_by_video_var.get(),
            "subfolder_override": self.subfolder_override_var.get(),
            "use_sharpening": self.use_sharpening_var.get(),
            "ffmpeg_denoise_vulkan": self.ffmpeg_denoise_vulkan_var.get(),
            "sharpening_algo": self.sharpening_algo_var.get(),
            "sharpening_strength": self.sharpening_strength_var.get(),
            "nvenc_preset": self.nvenc_preset_var.get(),
            "nvenc_tune": self.nvenc_tune_var.get(),
            "nvenc_profile_sdr": self.nvenc_profile_sdr_var.get(),
            "nvenc_profile_hdr": self.nvenc_profile_hdr_var.get(),
            "nvenc_rc_lookahead": self.nvenc_rc_lookahead_var.get(),
            "nvenc_multipass": self.nvenc_multipass_var.get(),
            "nvenc_spatial_aq": self.nvenc_spatial_aq_var.get(),
            "nvenc_temporal_aq": self.nvenc_temporal_aq_var.get(),
            "nvenc_bframes": self.nvenc_bframes_var.get(),
            "nvenc_b_ref_mode": self.nvenc_b_ref_mode_var.get(),
            "nvencc_decode_mode": self.nvencc_decode_mode_var.get(),
            "nvencc_color_tag_mode": self.nvencc_color_tag_mode_var.get(),
            "nvencc_color_prim": self.nvencc_color_prim_var.get(),
            "nvencc_color_transfer": self.nvencc_color_transfer_var.get(),
            "nvencc_color_matrix": self.nvencc_color_matrix_var.get(),
            "nvencc_output_depth": self.nvencc_output_depth_var.get(),
            "nvencc_strict_no_color_tagging": self.nvencc_strict_no_color_tagging_var.get(),
            "ffmpeg_threads": self.ffmpeg_threads_var.get(),
            "ffmpeg_priority": self.ffmpeg_priority_var.get(),
            "output_suffix_override": self.output_suffix_override_var.get(),
            # Title Burn options
            "title_burn_enabled": self.title_burn_var.get(),
            "title_json_suffix": self.title_json_suffix_var.get(),
            "title_remove_hashtags": self.title_remove_hashtags_var.get(),
            "title_enable_emoji": self.title_enable_emoji_var.get(),
            "title_autodetect": self.title_autodetect_var.get(),
            "title_override_text": self.title_override_var.get(),
            "title_start_time": self.title_start_time_var.get(),
            "title_end_time": self.title_end_time_var.get(),
            "title_font": self.title_font_var.get(),
            "title_font_size": self.title_font_size_var.get(),
            "title_bold": self.title_bold_var.get(),
            "title_italic": self.title_italic_var.get(),
            "title_underline": self.title_underline_var.get(),
            "title_alignment": self.title_alignment_var.get(),
            "title_margin_v": self.title_margin_v_var.get(),
            "title_margin_l": self.title_margin_l_var.get(),
            "title_margin_r": self.title_margin_r_var.get(),
            "title_fill_color": self.title_fill_color_var.get(),
            "title_fill_alpha": self.title_fill_alpha_var.get(),
            "title_outline_color": self.title_outline_color_var.get(),
            "title_outline_alpha": self.title_outline_alpha_var.get(),
            "title_outline_width": self.title_outline_width_var.get(),
            "title_shadow_color": self.title_shadow_color_var.get(),
            "title_shadow_alpha": self.title_shadow_alpha_var.get(),
            "title_shadow_offset_x": self.title_shadow_offset_x_var.get(),
            "title_shadow_offset_y": self.title_shadow_offset_y_var.get(),
            "title_shadow_blur": self.title_shadow_blur_var.get(),
        }

    def load_preset_to_gui(self, preset_name):
        preset = self.preset_manager.get_preset(preset_name)
        if not preset: return
        
        # 1. Load Options
        # Wrap in a dummy job structure to reuse update_gui_from_job_options
        dummy_job = {'options': preset['options']}
        self.update_gui_from_job_options(dummy_job)
        
        # 2. Load Triggers
        triggers = preset['triggers']
        
        # Handle New Schema vs Old Schema (Migration logic)
        # Handle New Schema vs Old Schema (Migration logic)
        vid_trig = triggers.get('video_trigger')
        
        # Reset bits
        self.trigger_video_always_var.set(False)
        self.trigger_video_fallback_var.set(False)

        if vid_trig:
            if vid_trig == "Always (Clean/Backup)": self.trigger_video_always_var.set(True)
            elif vid_trig == "Fallback (If No Subs)": self.trigger_video_fallback_var.set(True)
        else:
            # Fallback for old presets
            on_no_sub = triggers.get('on_no_sub', False)
            on_clean_copy = triggers.get('on_clean_copy_if_subs', False)
            if on_no_sub and on_clean_copy: self.trigger_video_always_var.set(True)
            elif on_no_sub and not on_clean_copy: self.trigger_video_fallback_var.set(True)

        self.trigger_scan_subs_var.set(triggers.get('on_scan_subs', False))
        self.trigger_autodetect_subs_var.set(triggers.get('auto_detect_subs', False))

        suffix_val = triggers.get('suffix_filter')
        suffix_mode = triggers.get('suffix_mode', 'restrict' if suffix_val is not None else 'all')
        if suffix_val is not None or suffix_mode != 'all':
            if suffix_mode == 'include':
                self.trigger_include_suffix_var.set(True)
                self.trigger_suffix_enable_var.set(False)
                self.trigger_suffix_var.set(suffix_val if suffix_val else "")
            elif suffix_mode == 'restrict' or suffix_val is not None:
                self.trigger_suffix_enable_var.set(True)
                self.trigger_include_suffix_var.set(False)
                self.trigger_suffix_var.set(suffix_val if suffix_val else "")
        else:
            self.trigger_suffix_enable_var.set(False)
            self.trigger_include_suffix_var.set(False)
            self.trigger_suffix_var.set("")

        self.output_suffix_override_var.set(preset['options'].get("output_suffix_override", ""))

        self.current_preset_var.set(preset_name)
    
        # 3. Auto-Apply to Selected Jobs (Sync GUI -> Selection)
        # If jobs are selected, apply this preset to them immediately.
        selected_indices = self.job_listbox.curselection()
        if selected_indices:
            for index in selected_indices:
                job = self.processing_jobs[index]
                job['options'] = copy.deepcopy(preset['options'])
                job['preset_name'] = preset_name
                
                # Update display name
                tag = job.get('display_tag', "")
                base_name = os.path.basename(job['video_path'])
                job['display_name'] = f"{base_name} {tag} [{preset_name}]".strip()
                     
                self.job_listbox.delete(index)
                self.job_listbox.insert(index, job['display_name'])
                self.job_listbox.selection_set(index) # Reselect

    def apply_preset_settings_to_selected(self):
        """Applies current GUI settings (custom or preset) to selected jobs."""
        selected_indices = self.job_listbox.curselection()
        if not selected_indices:
            messagebox.showinfo("Info", "No jobs selected.")
            return
            
        current_options = self.get_current_gui_options()
        preset_name = self.current_preset_var.get()
        
        for index in selected_indices:
            self._update_job_at_index(index, current_options, preset_name)
            
        messagebox.showinfo("Success", f"Applied settings to {len(selected_indices)} job(s).")

    def apply_preset_settings_to_all(self):
        """Applies current GUI settings to ALL jobs."""
        if not self.processing_jobs: return
        
        current_options = self.get_current_gui_options()
        preset_name = self.current_preset_var.get()
        
        for index in range(len(self.processing_jobs)):
            self._update_job_at_index(index, current_options, preset_name)
            
        messagebox.showinfo("Success", f"Applied settings to all {len(self.processing_jobs)} job(s).")

    def _update_job_at_index(self, index, options, preset_name):
        job = self.processing_jobs[index]
        job['options'] = copy.deepcopy(options)
        job['preset_name'] = preset_name
        
        # Use stored tag
        tag = job.get('display_tag', "")
        # No fallback regex here needed if we ensure creation stores it. 
        # But for safety if old jobs exist in list (unlikely in this session flow):
        if not tag:
             import re
             match = re.search(r'(.*) (\[.*\]) \[.*\]', job['display_name'])
             if match: tag = match.group(2)
        
        base_name = os.path.basename(job['video_path'])
        job['display_name'] = f"{base_name} {tag} [{preset_name}]".strip()
        
        self.job_listbox.delete(index)
        self.job_listbox.insert(index, job['display_name'])
        self.job_listbox.selection_set(index)

    def save_current_preset(self):
        name = self.current_preset_var.get()
        if not name: return
        self._save_preset_internal(name)

    def save_preset_as_new(self):
        new_name = simpledialog.askstring("New Preset", "Enter name for new preset:")
        if new_name:
            if new_name in self.preset_manager.get_preset_names():
                if not messagebox.askyesno("Overwrite?", f"Preset '{new_name}' already exists. Overwrite?"):
                    return
            self._save_preset_internal(new_name)
            self.preset_combo['values'] = self.preset_manager.get_preset_names()
            self.current_preset_var.set(new_name)
            self.load_preset_to_gui(new_name)

    def _save_preset_internal(self, name):
        options = self.get_current_gui_options()
        
        # Map Dropdown back to Booleans
        # Map Checkboxes back to Schema String
        
        mode = "Never"
        if self.trigger_video_always_var.get():
            mode = "Always (Clean/Backup)"
        elif self.trigger_video_fallback_var.get():
             mode = "Fallback (If No Subs)"
        
        # Legacy Boolean Backfill (for compatibility if needed, though mostly using video_trigger now)
        on_no_sub = False
        on_clean_copy = False
        
        if mode == "Always (Clean + Backup)" or mode == "Always (Clean/Backup)": # Handle both variants
            on_no_sub = True
            on_clean_copy = True
        elif mode == "Only if No Subtitles (Fallback)" or mode == "Fallback (If No Subs)":
            on_no_sub = True
            on_clean_copy = False
            
        triggers = {
            "video_trigger": mode,
            "on_no_sub": on_no_sub,
            "on_clean_copy_if_subs": on_clean_copy,
            "on_scan_subs": self.trigger_scan_subs_var.get(),
            "auto_detect_subs": self.trigger_autodetect_subs_var.get(),
            "suffix_filter": self.trigger_suffix_var.get() if (self.trigger_suffix_enable_var.get() or getattr(self, 'trigger_include_suffix_var', tk.BooleanVar(value=False)).get()) else None,
            "suffix_mode": "restrict" if self.trigger_suffix_enable_var.get() else "include" if getattr(self, 'trigger_include_suffix_var', tk.BooleanVar(value=False)).get() else "all"
        }
        self.preset_manager.save_preset(name, options, triggers)
        messagebox.showinfo("Saved", f"Preset '{name}' saved successfully.")

    def create_new_preset(self):
        new_name = simpledialog.askstring("New Preset", "Enter name for new preset:")
        if not new_name: return
        
        if new_name in self.preset_manager.get_preset_names():
             messagebox.showerror("Error", f"Preset '{new_name}' already exists.")
             return

        # Load defaults from 'Horizontal Clean' as a safe base
        defaults = self.preset_manager.get_default_presets()["Horizontal Clean"]
        
        # Save new preset
        self.preset_manager.save_preset(new_name, defaults['options'], defaults['triggers'])
        
        # Update UI
        self.preset_combo['values'] = self.preset_manager.get_preset_names()
        self.current_preset_var.set(new_name)
        self.load_preset_to_gui(new_name)
        messagebox.showinfo("Success", f"Created new preset '{new_name}' from defaults.")

    def rename_current_preset(self):
        old_name = self.current_preset_var.get()
        if not old_name: return
        
        new_name = simpledialog.askstring("Rename Preset", f"Enter new name for '{old_name}':", initialvalue=old_name)
        if not new_name or new_name == old_name: return
        
        if new_name in self.preset_manager.get_preset_names():
            messagebox.showerror("Error", f"Preset '{new_name}' already exists.")
            return
            
        if self.preset_manager.rename_preset(old_name, new_name):
            self.preset_combo['values'] = self.preset_manager.get_preset_names()
            self.current_preset_var.set(new_name)
            messagebox.showinfo("Success", f"Renamed '{old_name}' to '{new_name}'.")
        else:
            messagebox.showerror("Error", "Failed to rename preset.")

    def delete_current_preset(self):
        name = self.current_preset_var.get()
        if not name: return
        if messagebox.askyesno("Delete Preset", f"Are you sure you want to delete '{name}'?"):
            self.preset_manager.delete_preset(name)
            self.preset_combo['values'] = self.preset_manager.get_preset_names()
            
            # Select another if available
            remaining = self.preset_manager.get_preset_names()
            if remaining:
                self.current_preset_var.set(remaining[0])
                self.load_preset_to_gui(remaining[0])
            else:
                self.current_preset_var.set("")

    def process_added_files(self, file_paths):
        # 1. Add files to Input Queue
        for video_path in file_paths:
            video_path = os.path.abspath(video_path)
            if video_path not in self.input_files:
                self.input_files.append(video_path)
        
        # Refresh visible list
        self.refresh_input_listbox()
        
        # 2. Trigger Auto-Add Logic
        self.promote_input_files_auto(only_for_paths=file_paths)

    def refresh_input_listbox(self):
        search_term = self.input_filter_var.get().lower()
        inverse = self.input_filter_inverse_var.get()
        self.input_listbox.delete(0, tk.END)
        self.filtered_input_indices = []
        
        for i, video_path in enumerate(self.input_files):
            display_name = os.path.basename(video_path)
            
            show = True
            if search_term:
                match = search_term in display_name.lower()
                show = not match if inverse else match
            
            if show:
                self.input_listbox.insert(tk.END, display_name)
                self.filtered_input_indices.append(i)

    def promote_input_files_auto(self, only_for_paths=None):
        # Scan triggers for files in Input Queue (or specific subset)
        # Note: We do NOT remove files from Input Queue anymore.
        
        targets = only_for_paths if only_for_paths else self.input_files
        
        # Pre-calculate Specific Suffix Filters for exclusivity logic
        specific_suffix_filters = set()
        for p_name in self.preset_manager.get_preset_names():
            p = self.preset_manager.get_preset(p_name)
            s_filter = p['triggers'].get('suffix_filter')
            s_mode = p['triggers'].get('suffix_mode', 'restrict' if s_filter is not None else 'all')
            if s_filter and (s_mode == 'restrict' or s_mode == 'include'): 
                for s in s_filter.split(','):
                    specific_suffix_filters.add(s.strip())

        files_processed_count = 0
        
        for video_path in targets:
            video_path = os.path.abspath(video_path)
            # Find in input_files to match context if needed, but video_path matches.
            
            dir_name = os.path.dirname(video_path)
            video_basename = os.path.splitext(os.path.basename(video_path))[0]
            
            # Detect Subtitles (Pair-Aware scanning)
            detected_subs = self._detect_subtitles_for_video(video_path)
            has_subs = len(detected_subs) > 0
            
            # Iterate Presets
            for preset_name in self.preset_manager.get_preset_names():
                preset = self.preset_manager.get_preset(preset_name)
                triggers = preset['triggers']
                video_trigger = triggers.get("video_trigger")
                is_hybrid_duo = preset['options'].get("orientation") == "hybrid-duo (dual source)"
                if is_hybrid_duo and not (video_basename.endswith("-top") or video_basename.endswith("_top")):
                    continue # Skip triggering on non-top files for hybrid-duo presets
                if not video_trigger:
                    # Fallback for legacy presets (pre-Update)
                    t_no_sub = triggers.get('on_no_sub', False)
                    t_clean = triggers.get('on_clean_copy_if_subs', False)
                    if t_no_sub and t_clean: video_trigger = "Always (Clean/Backup)"
                    elif t_no_sub and not t_clean: video_trigger = "Fallback (If No Subs)"
                    else: video_trigger = "Never"
                
                # --- Video Trigger ---
                if video_trigger == "Always (Clean/Backup)":
                     self._create_job_entry(video_path, None, preset['options'], preset_name, "[No Subtitles]")
                     files_processed_count += 1
                elif video_trigger == "Fallback (If No Subs)" and not has_subs:
                     self._create_job_entry(video_path, None, preset['options'], preset_name, "[No Subtitles]")
                     files_processed_count += 1
                
                # --- Subtitle Trigger ---
                if has_subs and triggers.get('on_scan_subs'):
                    filter_suffix = triggers.get('suffix_filter')
                    filter_mode = triggers.get('suffix_mode', 'restrict' if filter_suffix is not None else 'all')
                    
                    for sub in detected_subs:
                        match = False
                        if filter_mode == 'all' or (filter_mode == 'restrict' and filter_suffix is None): # Generic Wildcard
                             # Check Exclusivity
                             is_claimed_specifically = False
                             for specific in specific_suffix_filters:
                                 if specific == "":
                                     if sub['suffix'] == "": is_claimed_specifically = True
                                 else:
                                     # Exact match check
                                     if sub['basename'] and sub['basename'].endswith(specific): is_claimed_specifically = True
                                     elif sub['suffix'] == specific: is_claimed_specifically = True
                             
                             if not is_claimed_specifically: match = True
                        elif filter_mode == 'include':
                             is_specific_match = False
                             if filter_suffix:
                                 valid_suffixes = [s.strip() for s in filter_suffix.split(',')]
                                 for vs in valid_suffixes:
                                     if sub['basename'] and sub['basename'].endswith(vs): is_specific_match = True
                                     elif sub['suffix'] == vs: is_specific_match = True
                             
                             if is_specific_match:
                                 match = True
                             else:
                                 is_claimed_specifically = False
                                 for specific in specific_suffix_filters:
                                     if specific == "":
                                         if sub['suffix'] == "": is_claimed_specifically = True
                                     else:
                                         if sub['basename'] and sub['basename'].endswith(specific): is_claimed_specifically = True
                                         elif sub['suffix'] == specific: is_claimed_specifically = True
                                 
                                 if not is_claimed_specifically: match = True
                        elif filter_mode == 'restrict':
                             if filter_suffix == "": # Strict Empty
                                 if sub['suffix'] == "": match = True
                             else: # Specific Suffix (comma separated)
                                 valid_suffixes = [s.strip() for s in filter_suffix.split(',')]
                                 for vs in valid_suffixes:
                                     if sub['basename'] and sub['basename'].endswith(vs): match = True
                                     elif sub['suffix'] == vs: match = True
                        
                        if match:
                             self._create_job_entry(video_path, sub['path'], preset['options'], preset_name, sub['display_tag'])
                             files_processed_count += 1
                             
        if files_processed_count > 0 and not only_for_paths:
             self.update_status(f"Auto-added {files_processed_count} jobs from Input Queue.")

    def promote_input_files_manual(self):
        # Force current preset on selected input files
        selected_indices = self.input_listbox.curselection()
        if not selected_indices: return
        
        preset_name = self.current_preset_var.get()
        if not preset_name: 
             messagebox.showwarning("No Preset", "Please select a preset first.")
             return
             
        preset = self.preset_manager.get_preset(preset_name)
        if not preset: return
        
        for index in selected_indices:
             # Map listbox index to original input_files index
             actual_index = self.filtered_input_indices[index]
             video_path = self.input_files[actual_index]
             # Manual add should still auto-pick the best subtitle if one exists
             # so subtitle burn and JSON title discovery work without extra clicks.
             detected_subs = self._detect_subtitles_for_video(video_path)
             preferred_sub = self._pick_preferred_subtitle(detected_subs)
             if preferred_sub:
                 self._create_job_entry(
                     video_path,
                     preferred_sub["path"],
                     preset['options'],
                     preset_name,
                     preferred_sub["display_tag"]
                 )
             else:
                 self._create_job_entry(video_path, None, preset['options'], preset_name, "[No Subtitles]")
        
        self.update_status(f"Added {len(selected_indices)} jobs manually.")

    def remove_from_input_queue(self):
        selected_indices = list(self.input_listbox.curselection())
        selected_indices.sort(reverse=True)
        for index in selected_indices:
            actual_index = self.filtered_input_indices[index]
            del self.input_files[actual_index]
        
        # After deletion, refresh the filter/view
        self.refresh_input_listbox()

    def clear_input_queue(self):
        self.input_files.clear()
        self.input_filter_var.set("") # Clear filter when clearing all
        self.refresh_input_listbox()

    def select_all_jobs(self):
        self.job_listbox.selection_set(0, tk.END); self.on_job_select(None)
    
    def clear_all_jobs(self):
        self.processing_jobs.clear(); self.job_listbox.delete(0, tk.END)
    
    def remove_selected_jobs(self):
        for index in reversed(list(self.job_listbox.curselection())):
            del self.processing_jobs[index]; self.job_listbox.delete(index)
    
    def _create_job_entry(self, video_path, subtitle_path, options, preset_name, display_tag):
        orientation = options.get("orientation", DEFAULT_ORIENTATION)
        if orientation == "hybrid-duo (dual source)":
            resolved_top = self._resolve_to_top_sibling(video_path)
            new_job_hash = get_job_hash(options)
            # Check if this top video is already added with these EXACT SAME options
            for existing_job in self.processing_jobs:
                existing_path_resolved = self._resolve_to_top_sibling(existing_job.get("video_path"))
                if existing_path_resolved == resolved_top:
                    existing_job_hash = get_job_hash(existing_job.get("options"))
                    if existing_job_hash == new_job_hash:
                        print(f"[INFO] Skipping duplicate Hybrid Duo file for: {os.path.basename(video_path)}")
                        return # Deduplicated!
            video_path = resolved_top

            # Pre-fill specific path options so the GUI reflects the found pair
            if not options.get("hybrid_top_path"):
                options["hybrid_top_path"] = video_path

            if not options.get("hybrid_bottom_path"):
                base_name, ext = os.path.splitext(video_path)
                bot_path = ""
                if base_name.endswith("-top"):
                    bot_path = base_name[:-4] + "-bot" + ext
                elif base_name.endswith("_top"):
                    bot_path = base_name[:-4] + "_bot" + ext
                else:
                    bot_path = base_name + "-bot" + ext

                if not os.path.exists(bot_path):
                    bot_path_alt = video_path.replace("-top", "-bot").replace("_top", "_bot")
                    if os.path.exists(bot_path_alt): bot_path = bot_path_alt

                if os.path.exists(bot_path):
                    options["hybrid_bottom_path"] = bot_path

        if subtitle_path is None:
            preset = self.preset_manager.get_preset(preset_name) if preset_name else None
            triggers = preset.get('triggers', {}) if preset else {}
            if triggers.get('auto_detect_subs'):
                detected_subs = self._detect_subtitles_for_video(video_path)
                preferred = self._pick_preferred_subtitle(detected_subs)
                if preferred:
                    subtitle_path = preferred.get("path")
                    display_tag = preferred.get("display_tag", display_tag)
        new_job = {
            "job_id": f"job_{time.time()}_{len(self.processing_jobs)}_{preset_name}",
            "video_path": video_path,
            "subtitle_path": subtitle_path,
            "options": copy.deepcopy(options),
            "preset_name": preset_name, # Store preset name
            "display_tag": display_tag   # Store tag permanently
        }
        # Populate the Title field on add when metadata is available.
        self._autofill_title_for_job(new_job, force=False)
        new_job["display_name"] = f"{os.path.basename(video_path)} {display_tag} [{preset_name}]"
        self.processing_jobs.append(new_job)
        self.job_listbox.insert(tk.END, new_job["display_name"])

    def _handle_listbox_empty_click(self, event, listbox):
        if listbox.size() > 0:
            index = listbox.nearest(event.y)
            bbox = listbox.bbox(index)
            if bbox:
                _, y, _, height = bbox
                if event.y > y + height:
                    listbox.selection_clear(0, tk.END)
                    listbox.event_generate("<<ListboxSelect>>")
                    return "break"
        return None

    def on_job_select(self, event=None):
        sel = self.job_listbox.curselection()
        if not sel:
            return

        active_idx = self.job_listbox.index(tk.ACTIVE)
        if active_idx not in sel:
            active_idx = sel[-1]

        selected_job = self.processing_jobs[active_idx]
        self._autofill_title_for_job(selected_job, force=False)
        
        # Load the preset of this job into the GUI.
        # We avoid calling load_preset_to_gui because that applies settings to selection.
        preset_name = selected_job.get('preset_name')
        if preset_name and preset_name in self.preset_manager.get_preset_names():
            self.current_preset_var.set(preset_name)
            self.update_gui_from_job_options(selected_job)
            
            # Job stores preset name, not trigger settings.
            preset = self.preset_manager.get_preset(preset_name)
            if preset:
                triggers = preset['triggers']
                
                on_no_sub = triggers.get('on_no_sub', False)
                on_clean = triggers.get('on_clean_copy_if_subs', False)
                self.trigger_video_always_var.set(on_no_sub and on_clean)
                self.trigger_video_fallback_var.set(on_no_sub and not on_clean)
                    
                self.trigger_scan_subs_var.set(triggers.get('on_scan_subs', False))
                self.trigger_autodetect_subs_var.set(triggers.get('auto_detect_subs', False))
                suffix_val = triggers.get('suffix_filter')
                suffix_mode = triggers.get('suffix_mode', 'restrict' if suffix_val is not None else 'all')
                if suffix_val is not None or suffix_mode != 'all':
                    if suffix_mode == 'include':
                        self.trigger_include_suffix_var.set(True)
                        self.trigger_suffix_enable_var.set(False)
                        self.trigger_suffix_var.set(suffix_val if suffix_val else "")
                    elif suffix_mode == 'restrict' or suffix_val is not None:
                        self.trigger_suffix_enable_var.set(True)
                        self.trigger_include_suffix_var.set(False)
                        self.trigger_suffix_var.set(suffix_val if suffix_val else "")
                else:
                    self.trigger_suffix_enable_var.set(False)
                    self.trigger_include_suffix_var.set(False)
                    self.trigger_suffix_var.set("")
        else:
            self.current_preset_var.set("") # Custom or Unknown
            self.update_gui_from_job_options(selected_job)
            # Reset triggers
            self.trigger_video_always_var.set(False)
            self.trigger_video_fallback_var.set(False)
            self.trigger_scan_subs_var.set(False)
            self.trigger_autodetect_subs_var.set(False)
            self.trigger_suffix_enable_var.set(False)
            if hasattr(self, 'trigger_include_suffix_var'): self.trigger_include_suffix_var.set(False)
            self.trigger_suffix_var.set("")

        self._suppress_subtitle_path_trace = True
        self.subtitle_path_var.set(selected_job.get('subtitle_path') or "")
        self._suppress_subtitle_path_trace = False

    def update_gui_from_job_options(self, job):
        options = job['options']
        self._is_loading_job_to_gui = True
        self.resolution_var.set(options.get("resolution", DEFAULT_RESOLUTION)); self.upscale_algo_var.set(options.get("upscale_algo", DEFAULT_UPSCALE_ALGO)); self.output_format_var.set(options.get("output_format", DEFAULT_OUTPUT_FORMAT))
        self.video_codec_var.set(options.get("video_codec", DEFAULT_VIDEO_CODEC))
        self.encoder_backend_var.set(options.get("encoder_backend", DEFAULT_ENCODER_BACKEND))
        self.nvenc_nvvfx_denoise_var.set(options.get("nvenc_nvvfx_denoise", DEFAULT_NVENC_NVVFX_DENOISE))
        self.nvenc_superres_mode_var.set(options.get("nvenc_superres_mode", DEFAULT_NVENC_SUPERRES_MODE))
        self.nvenc_ngx_vsr_quality_var.set(options.get("nvenc_ngx_vsr_quality", DEFAULT_NVENC_NGX_VSR_QUALITY))
        self.output_subfolders_var.set(options.get("output_to_subfolders", DEFAULT_OUTPUT_TO_SUBFOLDERS))
        self.output_subfolder_by_subtitle_var.set(options.get("output_subfolder_by_subtitle", DEFAULT_SUBFOLDER_BY_SUBTITLE))
        self.group_by_preset_var.set(options.get("group_by_preset", DEFAULT_GROUP_BY_PRESET))
        self.group_by_video_var.set(options.get("group_by_video", DEFAULT_GROUP_BY_VIDEO))
        self.subfolder_override_var.set(options.get("subfolder_override", DEFAULT_SUBFOLDER_OVERRIDE))
        self.render_by_chapters_var.set(options.get("render_by_chapters", DEFAULT_RENDER_BY_CHAPTERS))
        self.split_subtitles_by_chapter_var.set(options.get("split_subtitles_by_chapter", DEFAULT_SPLIT_SUBTITLES_BY_CHAPTER))
        raw_orientation = options.get("orientation", DEFAULT_ORIENTATION)
        if raw_orientation == "vertical":
            self.merged_aspect_var.set(options.get("merged_aspect", options.get("vertical_aspect", DEFAULT_VERTICAL_ASPECT)))
            self.orientation_var.set("horizontal + vertical")
        elif raw_orientation == "horizontal":
            self.merged_aspect_var.set(options.get("merged_aspect", options.get("horizontal_aspect", DEFAULT_HORIZONTAL_ASPECT)))
            self.orientation_var.set("horizontal + vertical")
        else:
            self.merged_aspect_var.set(options.get("merged_aspect", options.get("horizontal_aspect", DEFAULT_HORIZONTAL_ASPECT)))
            self.orientation_var.set(raw_orientation)
        self.aspect_mode_var.set(options.get("aspect_mode", DEFAULT_ASPECT_MODE))
        self.pad_color_var.set(options.get("pad_color", DEFAULT_PAD_COLOR))
        self.video_offset_x_var.set(options.get("video_offset_x", DEFAULT_VIDEO_OFFSET_X))
        self.video_offset_y_var.set(options.get("video_offset_y", DEFAULT_VIDEO_OFFSET_Y))
        self.pixelate_multiplier_var.set(options.get("pixelate_multiplier", DEFAULT_PIXELATE_MULTIPLIER))
        self.ambient_spread_var.set(options.get("ambient_spread", DEFAULT_AMBIENT_SPREAD))
        self.pixelate_brightness_var.set(options.get("pixelate_brightness", DEFAULT_PIXELATE_BRIGHTNESS))
        self.pixelate_saturation_var.set(options.get("pixelate_saturation", DEFAULT_PIXELATE_SATURATION))
        self.blur_sigma_var.set(options.get("blur_sigma", DEFAULT_BLUR_SIGMA))
        self.blur_steps_var.set(options.get("blur_steps", DEFAULT_BLUR_STEPS))
        self.horizontal_aspect_var.set(options.get("horizontal_aspect", DEFAULT_HORIZONTAL_ASPECT))
        self.vertical_aspect_var.set(options.get("vertical_aspect", DEFAULT_VERTICAL_ASPECT)); self.fruc_var.set(options.get("fruc", DEFAULT_FRUC)); self.fruc_fps_var.set(options.get("fruc_fps", DEFAULT_FRUC_FPS))
        self._on_merged_aspect_change(self.merged_aspect_var.get())
        self.generate_log_var.set(options.get("generate_log", False)); self.close_gui_var.set(options.get("close_gui_on_processing", False)); self.hibernate_when_done_var.set(options.get("hibernate_when_done", False)); self.burn_subtitles_var.set(options.get("burn_subtitles", DEFAULT_BURN_SUBTITLES)); self.override_bitrate_var.set(options.get("override_bitrate", False))
        self.manual_bitrate_var.set(options.get("manual_bitrate", "0")); 
        self.use_dynaudnorm_var.set(options.get("use_dynaudnorm", DEFAULT_USE_DYNAUDNORM))
        self.dyn_frame_len_var.set(options.get("dyn_frame_len", DEFAULT_DYNAUDNORM_FRAME_LEN))
        self.dyn_gauss_win_var.set(options.get("dyn_gauss_win", DEFAULT_DYNAUDNORM_GAUSS_WIN))
        self.dyn_peak_var.set(options.get("dyn_peak", DEFAULT_DYNAUDNORM_PEAK))
        self.dyn_max_gain_var.set(options.get("dyn_max_gain", DEFAULT_DYNAUDNORM_MAX_GAIN))
        self.use_loudness_war_var.set(options.get("use_loudness_war", DEFAULT_USE_LOUDNESS_WAR))
        self.comp_threshold_var.set(options.get("comp_threshold", DEFAULT_COMPRESSOR_THRESHOLD))
        self.comp_ratio_var.set(options.get("comp_ratio", DEFAULT_COMPRESSOR_RATIO))
        self.comp_attack_var.set(options.get("comp_attack", DEFAULT_COMPRESSOR_ATTACK))
        self.comp_release_var.set(options.get("comp_release", DEFAULT_COMPRESSOR_RELEASE))
        self.comp_makeup_var.set(options.get("comp_makeup", DEFAULT_COMPRESSOR_MAKEUP))
        self.limit_limit_var.set(options.get("limit_limit", DEFAULT_LIMITER_LIMIT))
        self.measure_loudness_var.set(options.get("measure_loudness", DEFAULT_MEASURE_LOUDNESS))
        self.normalize_audio_var.set(options.get("normalize_audio", DEFAULT_NORMALIZE_AUDIO)); self.loudness_target_var.set(options.get("loudness_target", DEFAULT_LOUDNESS_TARGET))
        self.loudness_range_var.set(options.get("loudness_range", DEFAULT_LOUDNESS_RANGE)); self.true_peak_var.set(options.get("true_peak", DEFAULT_TRUE_PEAK)); 
        self.sofa_file_var.set(options.get("sofa_file", DEFAULT_SOFA_PATH))
        self.hybrid_top_aspect_var.set(options.get("hybrid_top_aspect", "16:9")); self.hybrid_top_mode_var.set(options.get("hybrid_top_mode", "crop"))
        self.hybrid_top_path_var.set(options.get("hybrid_top_path", ""))
        self.hybrid_bottom_aspect_var.set(options.get("hybrid_bottom_aspect", "4:5")); self.hybrid_bottom_mode_var.set(options.get("hybrid_bottom_mode", "crop"))
        self.hybrid_bottom_path_var.set(options.get("hybrid_bottom_path", ""))
        self.subtitle_font_var.set(options.get("subtitle_font", DEFAULT_SUBTITLE_FONT)); self.subtitle_font_size_var.set(options.get("subtitle_font_size", DEFAULT_SUBTITLE_FONT_SIZE)); self.subtitle_alignment_var.set(options.get("subtitle_alignment", DEFAULT_SUBTITLE_ALIGNMENT))
        self.subtitle_bold_var.set(options.get("subtitle_bold", DEFAULT_SUBTITLE_BOLD)); self.subtitle_italic_var.set(options.get("subtitle_italic", DEFAULT_SUBTITLE_ITALIC)); self.subtitle_underline_var.set(options.get("subtitle_underline", DEFAULT_SUBTITLE_UNDERLINE))
        self.subtitle_margin_v_var.set(options.get("subtitle_margin_v", DEFAULT_SUBTITLE_MARGIN_V))
        self.subtitle_margin_l_var.set(options.get("subtitle_margin_l", DEFAULT_SUBTITLE_MARGIN_L))
        self.subtitle_margin_r_var.set(options.get("subtitle_margin_r", DEFAULT_SUBTITLE_MARGIN_R))
        self.subtitle_seam_h_offset_var.set(options.get("subtitle_seam_h_offset", DEFAULT_SUBTITLE_SEAM_H_OFFSET))
        self.subtitle_seam_v_offset_var.set(options.get("subtitle_seam_v_offset", DEFAULT_SUBTITLE_SEAM_V_OFFSET))
        self.fill_color_var.set(options.get("fill_color", DEFAULT_FILL_COLOR)); self.fill_alpha_var.set(options.get("fill_alpha", DEFAULT_FILL_ALPHA))
        self.outline_color_var.set(options.get("outline_color", DEFAULT_OUTLINE_COLOR)); self.outline_alpha_var.set(options.get("outline_alpha", DEFAULT_OUTLINE_ALPHA))
        self.outline_width_var.set(options.get("outline_width", DEFAULT_OUTLINE_WIDTH)); self.shadow_color_var.set(options.get("shadow_color", DEFAULT_SHADOW_COLOR))
        self.shadow_alpha_var.set(options.get("shadow_alpha", DEFAULT_SHADOW_ALPHA)); self.shadow_offset_x_var.set(options.get("shadow_offset_x", DEFAULT_SHADOW_OFFSET_X)); self.shadow_offset_y_var.set(options.get("shadow_offset_y", DEFAULT_SHADOW_OFFSET_Y))
        self.shadow_blur_var.set(options.get("shadow_blur", DEFAULT_SHADOW_BLUR)); self.lut_file_var.set(options.get("lut_file", DEFAULT_LUT_PATH))
        self.reformat_subtitles_var.set(options.get("reformat_subtitles", DEFAULT_REFORMAT_SUBTITLES))
        self.wrap_limit_var.set(options.get("wrap_limit", DEFAULT_WRAP_LIMIT))
        self.subtitle_max_lines_var.set(options.get("subtitle_max_lines", DEFAULT_SUBTITLE_MAX_LINES))
        self.audio_mono_var.set(options.get("audio_mono", DEFAULT_AUDIO_MONO))
        self.audio_stereo_downmix_var.set(options.get("audio_stereo_downmix", DEFAULT_AUDIO_STEREO_DOWNMIX))
        self.audio_stereo_sofalizer_var.set(options.get("audio_stereo_sofalizer", DEFAULT_AUDIO_STEREO_SOFALIZER))
        self.audio_surround_51_var.set(options.get("audio_surround_51", DEFAULT_AUDIO_SURROUND_51))
        self.audio_passthrough_var.set(options.get("audio_passthrough", DEFAULT_AUDIO_PASSTHROUGH))
        self.use_sharpening_var.set(options.get("use_sharpening", DEFAULT_USE_SHARPENING))
        self.ffmpeg_denoise_vulkan_var.set(options.get("ffmpeg_denoise_vulkan", DEFAULT_FFMPEG_DENOISE_VULKAN))
        self.sharpening_algo_var.set(options.get("sharpening_algo", DEFAULT_SHARPENING_ALGO))
        self.sharpening_strength_var.set(options.get("sharpening_strength", DEFAULT_SHARPENING_STRENGTH))
        self.output_suffix_override_var.set(options.get("output_suffix_override", ""))
        
        self.nvenc_preset_var.set(options.get("nvenc_preset", DEFAULT_NVENC_PRESET))
        self.nvenc_tune_var.set(options.get("nvenc_tune", DEFAULT_NVENC_TUNE))
        self.nvenc_profile_sdr_var.set(options.get("nvenc_profile_sdr", DEFAULT_NVENC_PROFILE_SDR))
        self.nvenc_profile_hdr_var.set(options.get("nvenc_profile_hdr", DEFAULT_NVENC_PROFILE_HDR))
        self.nvenc_rc_lookahead_var.set(options.get("nvenc_rc_lookahead", DEFAULT_NVENC_RC_LOOKAHEAD))
        self.nvenc_multipass_var.set(options.get("nvenc_multipass", DEFAULT_NVENC_MULTIPASS))
        self.nvenc_spatial_aq_var.set(options.get("nvenc_spatial_aq", DEFAULT_NVENC_SPATIAL_AQ))
        self.nvenc_temporal_aq_var.set(options.get("nvenc_temporal_aq", DEFAULT_NVENC_TEMPORAL_AQ))
        self.nvenc_bframes_var.set(options.get("nvenc_bframes", DEFAULT_NVENC_BFRAMES))
        self.nvenc_b_ref_mode_var.set(options.get("nvenc_b_ref_mode", DEFAULT_NVENC_B_REF_MODE))
        self.nvencc_decode_mode_var.set(options.get("nvencc_decode_mode", DEFAULT_NVENCC_DECODE_MODE))
        self.nvencc_color_tag_mode_var.set(options.get("nvencc_color_tag_mode", DEFAULT_NVENCC_COLOR_TAG_MODE))
        self.nvencc_color_prim_var.set(options.get("nvencc_color_prim", DEFAULT_NVENCC_COLOR_PRIM))
        self.nvencc_color_transfer_var.set(options.get("nvencc_color_transfer", DEFAULT_NVENCC_COLOR_TRANSFER))
        self.nvencc_color_matrix_var.set(options.get("nvencc_color_matrix", DEFAULT_NVENCC_COLOR_MATRIX))
        self.nvencc_output_depth_var.set(options.get("nvencc_output_depth", DEFAULT_NVENCC_OUTPUT_DEPTH))
        self.nvencc_strict_no_color_tagging_var.set(options.get("nvencc_strict_no_color_tagging", DEFAULT_NVENCC_STRICT_NO_COLOR_TAGGING))
        self.ffmpeg_threads_var.set(options.get("ffmpeg_threads", DEFAULT_FFMPEG_THREADS))
        self.ffmpeg_priority_var.set(normalize_ffmpeg_priority(options.get("ffmpeg_priority", DEFAULT_FFMPEG_PRIORITY)))

        self.nvenc_b_ref_mode_var.set(options.get("nvenc_b_ref_mode", DEFAULT_NVENC_B_REF_MODE))
        self.max_size_mb_var.set(options.get("max_size_mb", str(DEFAULT_MAX_SIZE_MB)))
        self.max_duration_var.set(options.get("max_duration", str(DEFAULT_MAX_DURATION)))

        self._update_codec_options(show_message=False)
        self._apply_backend_constraints()
        self._update_upscale_algo_options()
        self._toggle_superres_options()

        # Title Burn options
        self.title_burn_var.set(options.get("title_burn_enabled", DEFAULT_TITLE_BURN_ENABLED))
        self.title_json_suffix_var.set(options.get("title_json_suffix", DEFAULT_TITLE_JSON_SUFFIX))
        self.title_remove_hashtags_var.set(options.get("title_remove_hashtags", DEFAULT_TITLE_REMOVE_HASHTAGS))
        self.title_enable_emoji_var.set(options.get("title_enable_emoji", DEFAULT_TITLE_ENABLE_EMOJI))
        self.title_autodetect_var.set(options.get("title_autodetect", DEFAULT_TITLE_AUTODETECT))
        self.title_override_var.set(options.get("title_override_text", DEFAULT_TITLE_OVERRIDE_TEXT))
        self.title_start_time_var.set(options.get("title_start_time", DEFAULT_TITLE_START_TIME))
        self.title_end_time_var.set(options.get("title_end_time", DEFAULT_TITLE_END_TIME))
        self.title_font_var.set(options.get("title_font", DEFAULT_TITLE_FONT))
        self.title_font_size_var.set(options.get("title_font_size", DEFAULT_TITLE_FONT_SIZE))
        self.title_bold_var.set(options.get("title_bold", DEFAULT_TITLE_BOLD))
        self.title_italic_var.set(options.get("title_italic", DEFAULT_TITLE_ITALIC))
        self.title_underline_var.set(options.get("title_underline", DEFAULT_TITLE_UNDERLINE))
        self.title_alignment_var.set(options.get("title_alignment", DEFAULT_TITLE_ALIGNMENT))
        self.title_margin_v_var.set(options.get("title_margin_v", DEFAULT_TITLE_MARGIN_V))
        self.title_margin_l_var.set(options.get("title_margin_l", DEFAULT_TITLE_MARGIN_L))
        self.title_margin_r_var.set(options.get("title_margin_r", DEFAULT_TITLE_MARGIN_R))
        self.title_fill_color_var.set(options.get("title_fill_color", DEFAULT_TITLE_FILL_COLOR))
        self.title_fill_alpha_var.set(options.get("title_fill_alpha", DEFAULT_TITLE_FILL_ALPHA))
        self.title_outline_color_var.set(options.get("title_outline_color", DEFAULT_TITLE_OUTLINE_COLOR))
        self.title_outline_alpha_var.set(options.get("title_outline_alpha", DEFAULT_TITLE_OUTLINE_ALPHA))
        self.title_outline_width_var.set(options.get("title_outline_width", DEFAULT_TITLE_OUTLINE_WIDTH))
        self.title_shadow_color_var.set(options.get("title_shadow_color", DEFAULT_TITLE_SHADOW_COLOR))
        self.title_shadow_alpha_var.set(options.get("title_shadow_alpha", DEFAULT_TITLE_SHADOW_ALPHA))
        self.title_shadow_offset_x_var.set(options.get("title_shadow_offset_x", DEFAULT_TITLE_SHADOW_OFFSET_X))
        self.title_shadow_offset_y_var.set(options.get("title_shadow_offset_y", DEFAULT_TITLE_SHADOW_OFFSET_Y))
        self.title_shadow_blur_var.set(options.get("title_shadow_blur", DEFAULT_TITLE_SHADOW_BLUR))

        self.fill_swatch.config(bg=self.fill_color_var.get()); self.outline_swatch.config(bg=self.outline_color_var.get()); self.shadow_swatch.config(bg=self.shadow_color_var.get())
        # Update title swatches if they exist
        if hasattr(self, 'title_fill_swatch'): self.title_fill_swatch.config(bg=self.title_fill_color_var.get())
        if hasattr(self, 'title_outline_swatch'): self.title_outline_swatch.config(bg=self.title_outline_color_var.get())
        if hasattr(self, 'title_shadow_swatch'): self.title_shadow_swatch.config(bg=self.title_shadow_color_var.get())
        self._toggle_bitrate_override(); self.toggle_fruc_fps(); self._toggle_orientation_options(); self._toggle_upscale_options(); self._toggle_audio_norm_options(); self._update_audio_options_ui()
        self._is_loading_job_to_gui = False

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

    def measure_loudnorm_first_pass(self, file_path, options, base_dir=None):
        """
        Runs a first-pass loudnorm analysis to measure audio loudness stats.
        Returns a dict with measured values (input_i, input_tp, input_lra,
        input_thresh, target_offset) that can be fed into the second pass
        for instant, frame-accurate normalization with no ramp-up.
        
        The analysis chain mirrors the actual processing chain (compressor,
        limiter, dynaudnorm) so loudnorm measures the signal it will actually
        receive in the encode pass.
        """
        if options.get("audio_passthrough") or not options.get("normalize_audio", False):
            return None

        print(f"--- Loudnorm Pass 1/2: Analyzing '{os.path.basename(file_path)}' ---")
        
        # Build the analysis filter chain (mirrors the encode chain minus loudnorm)
        af_parts = []
        
        # Compressor + Limiter (same as encode chain)
        if options.get("use_loudness_war", False):
            t = options.get("comp_threshold")
            r = options.get("comp_ratio")
            a = options.get("comp_attack")
            re_val = options.get("comp_release")
            m = options.get("comp_makeup")
            l = options.get("limit_limit")
            af_parts.append(f"acompressor=threshold={t}dB:ratio={r}:attack={a}:release={re_val}:makeup={m}")
            af_parts.append(f"alimiter=limit={l}dB")
        
        # Dynamic normalization (same as encode chain)
        if options.get("use_dynaudnorm", False):
            f = options.get("dyn_frame_len")
            g = options.get("dyn_gauss_win")
            p = options.get("dyn_peak")
            m = options.get("dyn_max_gain")
            af_parts.append(f"dynaudnorm=f={f}:g={g}:p={p}:m={m}")
        
        # Loudnorm in measurement-only mode
        lt = options.get("loudness_target")
        tp = options.get("true_peak")
        af_parts.append(f"loudnorm=I={lt}:LRA=1:tp={tp}:print_format=json")
        
        af_string = ",".join(af_parts)
        
        cmd = [FFMPEG_CMD, "-hide_banner"]
        
        seek_start = options.get("seek_start")
        if seek_start is not None:
            cmd.extend(["-ss", str(seek_start)])
            
        seek_duration = options.get("seek_duration")
        if seek_duration is not None:
            cmd.extend(["-t", str(seek_duration)])
            
        cmd.extend(["-i", file_path, "-vn", "-sn", "-dn",
               "-af", af_string, "-f", "null", "-"])
        
        debug_print("Loudnorm first-pass command:", " ".join(cmd))
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=600)
            output = (result.stdout or "") + (result.stderr or "")
            
            # FFmpeg outputs the JSON stats at the end of stderr
            json_match = re.search(r'\{[\s\S]*?"target_offset"[\s\S]*?\}', output)
            if not json_match:
                # Fallback: find any JSON block
                json_match = re.search(r'\{[\s\S]*?\}', output)
            
            if json_match:
                stats = json.loads(json_match.group(0))
                measured = {
                    "input_i": stats.get("input_i", "-24.0"),
                    "input_tp": stats.get("input_tp", "-2.0"),
                    "input_lra": stats.get("input_lra", "7.0"),
                    "input_thresh": stats.get("input_thresh", "-34.0"),
                    "target_offset": stats.get("target_offset", "0.0"),
                }
                print(f"[INFO] Loudnorm measured: I={measured['input_i']} LUFS, "
                      f"TP={measured['input_tp']} dBTP, LRA={measured['input_lra']}, "
                      f"Offset={measured['target_offset']}")
                return measured
            else:
                print("[WARN] Loudnorm first-pass: Could not parse measurement JSON. Falling back to single-pass.")
                return None
        except subprocess.TimeoutExpired:
            print("[WARN] Loudnorm first-pass timed out (>10min). Falling back to single-pass.")
            return None
        except Exception as e:
            print(f"[WARN] Loudnorm first-pass failed: {e}. Falling back to single-pass.")
            return None

    def build_audio_segment(self, file_path, options, base_dir=None, loudnorm_stats=None):
        if options.get("audio_passthrough"):
            return ["-map", "0:a?", "-c:a", "copy"]

        audio_streams = get_audio_stream_info(file_path)
        if not audio_streams:
            return ["-an"]

        stereo_streams = [s for s in audio_streams if int(s.get("channels", 0)) == 2]
        surround_streams = [s for s in audio_streams if int(s.get("channels", 0)) >= 6]
        
        src_for_mono = stereo_streams[0] if stereo_streams else (surround_streams[0] if surround_streams else audio_streams[0])
        src_for_hq = surround_streams[0] if surround_streams else (stereo_streams[0] if stereo_streams else audio_streams[0])

        tracks_config = []
        if options.get("audio_mono"):
            tracks_config.append({"type": "mono", "source_index": src_for_mono['index'], "source_channels": int(src_for_mono.get("channels", 0))})
        if options.get("audio_stereo_downmix"):
            tracks_config.append({"type": "stereo_downmix", "source_index": src_for_hq['index'], "source_channels": int(src_for_hq.get("channels", 0))})
        if options.get("audio_stereo_sofalizer"):
            if int(src_for_hq.get("channels", 0)) >= 6:
                tracks_config.append({"type": "stereo_sofalizer", "source_index": src_for_hq['index'], "source_channels": int(src_for_hq.get("channels", 0))})
            else:
                print(f"[WARN] Sofalizer skipped: Best source for {os.path.basename(file_path)} is not 5.1/Surround.")
        if options.get("audio_surround_51"):
            tracks_config.append({"type": "surround_51", "source_index": src_for_hq['index'], "source_channels": int(src_for_hq.get("channels", 0))})

        if not tracks_config:
            print("[WARN] No valid audio tracks selected. Disabling audio.")
            return ["-an"]

        source_counts = Counter(t['source_index'] for t in tracks_config)
        fc_parts, specific_pads = [], {}

        for src_idx, count in source_counts.items():
            if count > 1:
                out_pads = [f"[src{src_idx}_{i}]" for i in range(count)]
                fc_parts.append(f"[0:{src_idx}]asplit={count}{''.join(out_pads)}")
                specific_pads[src_idx] = out_pads
            else:
                specific_pads[src_idx] = [f"[0:{src_idx}]"]

        final_maps = []
        output_audio_index = 0

        for track in tracks_config:
            track_type = track['type']
            src_idx = track['source_index']
            input_tag = specific_pads[src_idx].pop(0)
            proc_tag = f"[{track_type}_proc]"
            final_tag = proc_tag

            # Prepend asetpts=PTS-STARTPTS to reset audio timestamps to 0.
            # This is critical for chapter splits where -ss before -i may leave
            # non-zero PTS values that cause some encoders to output silence.
            if track_type == "mono":
                fc_parts.append(f"{input_tag}asetpts=PTS-STARTPTS,aformat=channel_layouts=mono{proc_tag}")
            elif track_type == "stereo_downmix":
                fc_parts.append(f"{input_tag}asetpts=PTS-STARTPTS,aformat=channel_layouts=stereo{proc_tag}")
            elif track_type == "stereo_sofalizer":
                sofa_path = options.get("sofa_file", "").strip()
                if not sofa_path or not os.path.exists(sofa_path):
                    raise VideoProcessingError(f"Sofalizer enabled, but SOFA file not found: {sofa_path}")
                safe_sofa = escape_ffmpeg_filter_path(sofa_path, base_dir=base_dir)
                fc_parts.append(f"{input_tag}asetpts=PTS-STARTPTS,sofalizer=sofa='{safe_sofa}':normalize=enabled:speakers=FL 26|FR 334|FC 0|SL 100|SR 260|LFE 0|BL 142|BR 218{proc_tag}")
            elif track_type == "surround_51":
                if track['source_channels'] >= 6:
                     fc_parts.append(f"{input_tag}asetpts=PTS-STARTPTS,channelmap=channel_layout=5.1(side){proc_tag}")
                else:
                     fc_parts.append(f"{input_tag}asetpts=PTS-STARTPTS,aformat=channel_layouts=5.1{proc_tag}")

            # --- Loudness War (Compressor + Limiter) ---
            if options.get("use_loudness_war", False):
                t, r, a, re, m = options.get("comp_threshold"), options.get("comp_ratio"), options.get("comp_attack"), options.get("comp_release"), options.get("comp_makeup")
                l = options.get("limit_limit")
                lw_tag = f"[{track_type}_lw]"
                # FFmpeg attack/release for acompressor are in ms (but often expressed as floats). 
                # The user request specified attack=1 and release=100.
                fc_parts.append(f"{proc_tag}acompressor=threshold={t}dB:ratio={r}:attack={a}:release={re}:makeup={m},alimiter=limit={l}dB{lw_tag}")
                proc_tag = lw_tag

            if options.get("use_dynaudnorm", False):
                f, g, p, m = options.get("dyn_frame_len"), options.get("dyn_gauss_win"), options.get("dyn_peak"), options.get("dyn_max_gain")
                dyn_tag = f"[{track_type}_dyn]"
                fc_parts.append(f"{proc_tag}dynaudnorm=f={f}:g={g}:p={p}:m={m}{dyn_tag}")
                proc_tag = dyn_tag

            if options.get("normalize_audio", False):
                lt, lr, tp = options.get("loudness_target"), options.get("loudness_range"), options.get("true_peak")
                ln_tag = f"[{track_type}_ln]"
                if loudnorm_stats:
                    # Two-pass mode: use measured values for instant, frame-accurate normalization
                    mi = loudnorm_stats["input_i"]
                    mtp = loudnorm_stats["input_tp"]
                    mlra = loudnorm_stats["input_lra"]
                    mthresh = loudnorm_stats["input_thresh"]
                    moffset = loudnorm_stats["target_offset"]
                    fc_parts.append(
                        f"{proc_tag}loudnorm=I={lt}:LRA=1:tp={tp}:linear=true"
                        f":measured_I={mi}:measured_tp={mtp}:measured_LRA={mlra}"
                        f":measured_thresh={mthresh}:offset={moffset}{ln_tag}"
                    )
                else:
                    # Single-pass fallback (may have slow ramp-up at start)
                    fc_parts.append(f"{proc_tag}loudnorm=I={lt}:LRA=1:tp={tp}:linear=true{ln_tag}")
                proc_tag = ln_tag

            final_tag = proc_tag

            resample_tag = f"[{track_type}_final]"
            fc_parts.append(f"{final_tag}aresample={AUDIO_SAMPLE_RATE}{resample_tag}")
            final_maps.extend(["-map", resample_tag])
            
            if track_type == "mono":
                final_maps.extend([f"-c:a:{output_audio_index}", "aac", f"-b:a:{output_audio_index}", f"{MONO_BITRATE_K}k"])
                title = "Mono"
            elif "stereo" in track_type:
                final_maps.extend([f"-c:a:{output_audio_index}", "aac", f"-b:a:{output_audio_index}", f"{STEREO_BITRATE_K}k"])
                title = "Stereo (Binaural)" if track_type == "stereo_sofalizer" else "Stereo"
            elif track_type == "surround_51":
                final_maps.extend([f"-c:a:{output_audio_index}", "aac", f"-b:a:{output_audio_index}", f"{SURROUND_BITRATE_K}k"])
                title = "5.1 Surround"
            
            disposition = "default" if output_audio_index == 0 else "0"
            final_maps.extend([f"-disposition:a:{output_audio_index}", disposition, f"-metadata:s:a:{output_audio_index}", f"title={title}"])
            output_audio_index += 1
            
        return ["-filter_complex", ";".join(fc_parts)] + final_maps

    def build_ffmpeg_command_and_run(self, job, orientation):
        global CURRENT_TEMP_FILE, CURRENT_JOB_TEMP_DIR
        options = copy.deepcopy(job['options'])
        encoder_backend = options.get("encoder_backend", DEFAULT_ENCODER_BACKEND)
        requested_orientation = orientation
        orientation = self._resolve_orientation(options, requested_orientation)
        
        # --- Override backend for NVEncC + Hybrid Stacked ---
        # NVEncC lacks native vpp-stacking, so if the user requested an NVEncC-only pipeline
        # alongside Hybrid mode, we seamlessly route it through FFmpeg preprocessing.
        if orientation in ["hybrid (stacked)", "hybrid-duo (dual source)"] and encoder_backend in ["nvencc_only", "nvencc_video_with_ffmpeg_audio"]:
            print(f"[INFO] {orientation} requires FFmpeg preprocessing. Using 'nvencc_with_ffmpeg' for '{job['display_name']}'.")
            encoder_backend = "nvencc_with_ffmpeg"
            # Update the option so downstream functions use the correct backend path
            options["encoder_backend"] = encoder_backend

        if requested_orientation == "horizontal + vertical":
            merged_aspect = options.get("merged_aspect", DEFAULT_HORIZONTAL_ASPECT)
            if self._aspect_to_orientation(merged_aspect) == "vertical":
                options["vertical_aspect"] = merged_aspect
            else:
                options["horizontal_aspect"] = merged_aspect
        
        sub_paths = []
        override = options.get("subfolder_override", "").strip()
        
        if override:
            sub_paths.append(re.sub(r'[\\/*?:"<>|]', "", override).strip())
        elif not options.get("output_to_subfolders", DEFAULT_OUTPUT_TO_SUBFOLDERS) and \
           not options.get("group_by_video", DEFAULT_GROUP_BY_VIDEO) and \
           not options.get("group_by_preset", DEFAULT_GROUP_BY_PRESET):
            sub_paths.append(DEFAULT_SINGLE_OUTPUT_DIR_NAME)
        else:
            if options.get("output_to_subfolders", DEFAULT_OUTPUT_TO_SUBFOLDERS):
                folder_name = f"{options.get('resolution', DEFAULT_RESOLUTION)}_{options.get('output_format', DEFAULT_OUTPUT_FORMAT).upper()}"
                if orientation in ["hybrid (stacked)", "hybrid-duo (dual source)"]: folder_name += "_Hybrid_Stacked"
                elif orientation == "vertical": folder_name += f"_Vertical_{options.get('vertical_aspect').replace(':', 'x')}"
                elif orientation == "original": folder_name += "_Original"
                else:
                    h_aspect = options.get('horizontal_aspect').replace(':', 'x')
                    if h_aspect != "16x9": folder_name += f"_Horizontal_{h_aspect}"
                
                if options.get("output_subfolder_by_subtitle", DEFAULT_SUBFOLDER_BY_SUBTITLE):
                    tag = job.get('display_tag', "Subtitles")
                    safe_subtitle_folder_name = re.sub(r'[\\/*?:"<>|]', "", tag).strip()
                    sub_paths.append(os.path.join(folder_name, safe_subtitle_folder_name))
                else:
                    sub_paths.append(folder_name)
            else:
                sub_paths.append(DEFAULT_SINGLE_OUTPUT_DIR_NAME)

            if options.get("group_by_preset", DEFAULT_GROUP_BY_PRESET):
                preset_name = job.get('preset_name', "Default")
                safe_preset = re.sub(r'[\\/*?:"<>|]', "", preset_name).strip() or "Default_Preset"
                sub_paths.append(safe_preset)

            if options.get("group_by_video", DEFAULT_GROUP_BY_VIDEO):
                original_basename = os.path.splitext(os.path.basename(job['video_path']))[0]
                safe_video_name = re.sub(r'[\\/*?:"<>|]', "", original_basename).strip()
                sub_paths.append(safe_video_name)

        final_sub_path = os.path.join(*sub_paths) if sub_paths else DEFAULT_SINGLE_OUTPUT_DIR_NAME
        
        base_dir = os.path.dirname(job['video_path']) if self.output_mode == 'local' else os.getcwd()
        output_dir = os.path.join(base_dir, final_sub_path)
        os.makedirs(output_dir, exist_ok=True)
        CURRENT_JOB_TEMP_DIR = output_dir

        original_basename = os.path.splitext(os.path.basename(job['video_path']))[0]
        
        if orientation == "hybrid-duo (dual source)":
            explicit_top = options.get("hybrid_top_path", "").strip()
            if explicit_top and os.path.exists(explicit_top):
                original_basename = os.path.splitext(os.path.basename(explicit_top))[0]
            if original_basename.endswith("-top"):
                original_basename = original_basename[:-4] # Strip "-top" for a cleaner output name
            elif original_basename.endswith("_top"):
                original_basename = original_basename[:-4]
        
        # Tag
        tag = job.get('display_tag', "").strip()
        safe_tag = re.sub(r'[\\/*?:"<>|]', "", tag).strip().replace(" ", "_")

        # Suffix (Override or Preset Name)
        override = options.get("output_suffix_override", "").strip()
        suffix = override if override else job.get('preset_name', "")
        safe_suffix = re.sub(r'[\\/*?:"<>|]', "", suffix).strip().replace(" ", "_")

        # Construct: Base_Tag_Suffix
        name_parts = [original_basename]
        if safe_tag: name_parts.append(safe_tag)
        if safe_suffix: name_parts.append(safe_suffix)
        
        base_name_without_hash = "_".join(filter(None, name_parts))
        
        # --- Chapter Processing Loop ---
        chapters = []
        if options.get("render_by_chapters"):
            try:
                chapters = get_video_chapters(job['video_path'])
            except Exception as e:
                print(f"[ERROR] Failed to extract chapters for {job['video_path']}: {e}")
        
        if not chapters:
            chapters = [{
                'index': 0,
                'start_time': 0,
                'end_time': None,
                'title': None
            }]
        
        total_chapters = len(chapters) if options.get("render_by_chapters") else 1
        
        # Subtitle split by chapter preprocessing
        temp_extracted_srt = None
        do_subtitle_split = options.get("render_by_chapters") and options.get("split_subtitles_by_chapter") and job.get('subtitle_path')
        if do_subtitle_split:
            sub = job['subtitle_path']
            if sub.startswith("embedded:"):
                idx = sub.split(":")[1]
                temp_extracted_srt = extract_embedded_subtitle(job['video_path'], idx, output_dir)
            else:
                temp_extracted_srt = sub

        for i, chapter in enumerate(chapters):
            ch_options = copy.deepcopy(options)
            
            if options.get("render_by_chapters"):
                ch_title = chapter.get('title') or f"Chapter_{i+1}"
                # Sanitize chapter title for filename
                safe_ch_title = re.sub(r'[\\/*?:"<>|]', "", ch_title).strip().replace(" ", "_")
                
                # Compute hash unique to file and chapter
                extra_hash_data = f"{job['video_path']}_{i}_{safe_ch_title}"
                ch_job_hash = get_job_hash(ch_options, extra_hash_data)
                
                base_chunk = f"{base_name_without_hash}_{i+1:02d}_{safe_ch_title}_{ch_job_hash}"
                ch_output_file = os.path.join(output_dir, f"{base_chunk}.mp4")
                ch_srt_file = os.path.join(output_dir, f"{base_chunk}.srt")
                print(f"\n[INFO] Processing Chapter {i+1}/{total_chapters}: {ch_title}")
                
                ch_options["seek_start"] = chapter['start_time']
                if chapter['end_time'] is not None:
                    ch_options["seek_duration"] = chapter['end_time'] - chapter['start_time']
                    
                # Prevent silent audio on subsequent chapters due to MP4 edit lists / AAC priming loss
                # when copying streams with an input seek offset.
                if ch_options.get("audio_passthrough"):
                    ch_options["audio_passthrough"] = False
                    if not any([ch_options.get("audio_mono"), ch_options.get("audio_stereo_downmix"), ch_options.get("audio_stereo_sofalizer"), ch_options.get("audio_surround_51")]):
                        ch_options["audio_stereo_downmix"] = True
                        
                if do_subtitle_split and temp_extracted_srt and os.path.exists(temp_extracted_srt):
                    print(f"       -> Splitting subtitle chunk...")
                    success = split_srt_file(temp_extracted_srt, ch_srt_file, chapter['start_time'], chapter['end_time'])
                    if success:
                        print(f"       -> Exported {os.path.basename(ch_srt_file)}")
                        # Use chapter-local subtitle for burn-in on this segment.
                        ch_options["segment_subtitle_path"] = ch_srt_file
            else:
                # Compute hash unique to file
                extra_hash_data = f"{job['video_path']}"
                ch_job_hash = get_job_hash(ch_options, extra_hash_data)
                
                base_chunk = f"{base_name_without_hash}_{ch_job_hash}"
                ch_output_file = os.path.join(output_dir, f"{base_chunk}.mp4")
                ch_srt_file = os.path.join(output_dir, f"{base_chunk}.srt")
            
            base_dir = os.path.dirname(job['video_path']) if self.output_mode == 'local' else os.getcwd()
            self._process_single_render_segment(job, ch_output_file, orientation, ch_options, output_dir, base_dir=base_dir)

        if do_subtitle_split and temp_extracted_srt and job['subtitle_path'].startswith("embedded:"):
            cleanup_single_temp_file(temp_extracted_srt)

    def _process_single_render_segment(self, job, output_file, orientation, options, output_dir, base_dir=None):
        global CURRENT_TEMP_FILE, CURRENT_JOB_TEMP_DIR
        ass_burn_path, temp_extracted_srt_path = None, None
        nvencc_subburn_path = None
        encoder_backend = options.get("encoder_backend", DEFAULT_ENCODER_BACKEND)
        base_dir = base_dir or os.getcwd()
        try:
            info = get_video_info(job['video_path'])
            sub_target_w, sub_target_h = self.compute_target_resolution_for_options(options, info, orientation)

            segment_sub_path = options.get("segment_subtitle_path")
            # NVEncC backends that directly seek the original video (nvencc_only,
            # nvencc_video_with_ffmpeg_audio) render subtitles against the INPUT
            # timeline, not the output timeline.  The chapter-local SRT has
            # timestamps shifted to 0-based, which won't match the input PTS.
            # So for those backends, always use the original (non-time-shifted)
            # subtitle file; NVEncC's --seek/--seekto will naturally clip rendering
            # to the correct chapter range.
            nvencc_direct_backends = ("nvencc_only", "nvencc_video_with_ffmpeg_audio")
            if encoder_backend in nvencc_direct_backends and options.get("seek_start") is not None:
                subtitle_input = job.get('subtitle_path')
            else:
                subtitle_input = segment_sub_path or job.get('subtitle_path')
            if options.get("burn_subtitles") and subtitle_input:
                sub_identifier = subtitle_input
                subtitle_source_file = None
                if sub_identifier.startswith("embedded:"):
                    stream_index = int(sub_identifier.split(':')[1])
                    temp_extracted_srt_path = extract_embedded_subtitle(job['video_path'], stream_index, temp_dir=output_dir)
                    if temp_extracted_srt_path: subtitle_source_file = temp_extracted_srt_path
                    else: print(f"[WARN] Could not extract embedded subtitle for '{job['display_name']}'.")
                elif os.path.exists(sub_identifier): subtitle_source_file = sub_identifier
                if subtitle_source_file:
                    if orientation in ["hybrid (stacked)", "hybrid-duo (dual source)"] and options.get("subtitle_alignment") == "seam":
                         try:
                            num_top, den_top = map(int, options.get('hybrid_top_aspect', '16:9').split(':'))
                            top_h = (int(sub_target_w * den_top / num_top) // 2) * 2
                            options["calculated_pos"] = (sub_target_w // 2, top_h)
                         except (ValueError, AttributeError, ZeroDivisionError):
                            print(f"[WARN] Failed to parse hybrid aspect ratios for seam alignment in '{job['display_name']}'")
                    
                    sub_ext = os.path.splitext(subtitle_source_file)[1].lower()
                    if sub_ext in [".ass", ".ssa"]:
                        ass_burn_path = create_temporary_ass_passthrough_file(subtitle_source_file)
                        if not ass_burn_path:
                            raise VideoProcessingError("Failed to prepare ASS subtitle file.")
                    else:
                        ass_burn_path = create_temporary_ass_file(subtitle_source_file, options, target_res=(sub_target_w, sub_target_h))
                        if not ass_burn_path:
                            raise VideoProcessingError("Failed to create styled ASS file.")
            
            # --- Title Burn ASS Creation ---
            title_ass_path = None
            if options.get("title_burn_enabled"):
                # Get title text - priority: override > JSON
                title_text = options.get("title_override_text", "").strip()
                if not title_text:
                    # Try to find from JSON file
                    _, title_text = find_title_json_file(
                        job['video_path'],
                        job.get('subtitle_path'),
                        options.get('title_json_suffix', ''),
                        remove_hashtags=options.get('title_remove_hashtags', DEFAULT_TITLE_REMOVE_HASHTAGS),
                        keep_emoji=options.get('title_enable_emoji', DEFAULT_TITLE_ENABLE_EMOJI)
                    )
                else:
                    # Normalize manually typed title too (unicode decode + optional emoji stripping).
                    title_text = sanitize_title(
                        title_text,
                        remove_hashtags=False,
                        keep_emoji=options.get('title_enable_emoji', DEFAULT_TITLE_ENABLE_EMOJI)
                    )
                
                if title_text:
                    title_ass_path = create_title_ass_file(title_text, options, target_res=(sub_target_w, sub_target_h))
                    if title_ass_path:
                        print(f"[INFO] Title burn: '{title_text[:50]}...' " if len(title_text) > 50 else f"[INFO] Title burn: '{title_text}'")
                    else:
                        print("[WARN] Failed to create title ASS file.")
                else:
                    print("[WARN] Title burn enabled but no title text found (check JSON suffix or use override).")
            
            duration = options.get("seek_duration")
            if duration is None:
                duration = get_file_duration(job['video_path'])
                max_dur = float(options.get('max_duration', 0))
                if max_dur > 0: duration = min(duration, max_dur)

            # --- Two-Pass Loudnorm: Run first-pass analysis if loudnorm is enabled ---
            loudnorm_stats = None
            if options.get("normalize_audio", False) and not options.get("audio_passthrough"):
                loudnorm_stats = self.measure_loudnorm_first_pass(job['video_path'], options, base_dir=base_dir)
                if loudnorm_stats:
                    options["_loudnorm_stats"] = loudnorm_stats

            seek_start = options.get("seek_start")
            seek_duration = options.get("seek_duration")

            if encoder_backend == "nvencc_with_ffmpeg":
                fd, temp_preproc = tempfile.mkstemp(
                    suffix=".mkv",
                    prefix="vid_temp_preproc_",
                    dir=output_dir
                )
                os.close(fd)
                CURRENT_TEMP_FILE = temp_preproc
                register_temp_file(temp_preproc)
                pre_cmd = self.construct_ffmpeg_command(
                    job,
                    temp_preproc,
                    orientation,
                    ass_burn_path,
                    options,
                    title_ass_path,
                    encoder_backend="preprocess",
                    base_dir=base_dir
                )
                if self.run_ffmpeg_command(pre_cmd, duration, options=options, cwd=base_dir) != 0:
                    raise VideoProcessingError(f"Error preprocessing {job['video_path']}")

                # Copy options and strip seek_start/seek_duration so NVEncC doesn't double-seek
                nvencc_options = copy.deepcopy(options)
                nvencc_options.pop("seek_start", None)
                nvencc_options.pop("seek_duration", None)
                nvencc_cmd = self.construct_nvencc_command(temp_preproc, output_file, nvencc_options, orientation, info=get_video_info(temp_preproc), base_dir=base_dir)
                if self.run_nvencc_command(nvencc_cmd, duration=duration, progress_callback=self.update_progress, cwd=base_dir) != 0:
                    raise VideoProcessingError(f"Error encoding {job['video_path']} with NVEncC")
            elif encoder_backend == "nvencc_only":
                nvencc_subburn_path = create_merged_ass_for_nvencc(ass_burn_path, title_ass_path)
                nvencc_cmd = self.construct_nvencc_command(
                    job['video_path'],
                    output_file,
                    options,
                    orientation,
                    subtitle_burn_path=nvencc_subburn_path,
                    info=info,
                    base_dir=base_dir
                )
                if self.run_nvencc_command(nvencc_cmd, duration=duration, progress_callback=self.update_progress, cwd=base_dir) != 0:
                    raise VideoProcessingError(f"Error encoding {job['video_path']} with NVEncC")
            elif encoder_backend == "nvencc_video_with_ffmpeg_audio":
                fd, temp_audio = tempfile.mkstemp(
                    suffix=".mka",
                    prefix="vid_temp_audio_",
                    dir=output_dir
                )
                os.close(fd)
                CURRENT_TEMP_FILE = temp_audio
                register_temp_file(temp_audio)
                audio_cmd = self.construct_ffmpeg_audio_prepass(
                    job['video_path'], 
                    temp_audio, 
                    options, 
                    seek_start=seek_start, 
                    seek_duration=seek_duration
                )
                if self.run_ffmpeg_command(audio_cmd, duration, options=options, cwd=base_dir) != 0:
                    raise VideoProcessingError(f"Error preprocessing audio for {job['video_path']}")
                nvencc_subburn_path = create_merged_ass_for_nvencc(ass_burn_path, title_ass_path)
                nvencc_cmd = self.construct_nvencc_command(
                    job['video_path'],
                    output_file,
                    options,
                    orientation,
                    audio_source_path=temp_audio,
                    subtitle_burn_path=nvencc_subburn_path,
                    info=info,
                    base_dir=base_dir
                )
                if self.run_nvencc_command(nvencc_cmd, duration=duration, progress_callback=self.update_progress, cwd=base_dir) != 0:
                    raise VideoProcessingError(f"Error encoding {job['video_path']} with NVEncC")
            else:
                cmd = self.construct_ffmpeg_command(job, output_file, orientation, ass_burn_path, options, title_ass_path, base_dir=base_dir)
                if self.run_ffmpeg_command(cmd, duration, options=options, cwd=base_dir) != 0: 
                    raise VideoProcessingError(f"Error encoding {job['video_path']}")
            
            print(f"File finalized => {output_file}")
            self.verify_output_file(output_file, options)

            if options.get("measure_loudness"):
                self.measure_loudness(output_file, options)
        finally:
            if CURRENT_TEMP_FILE:
                cleanup_single_temp_file(CURRENT_TEMP_FILE)
                CURRENT_TEMP_FILE = None
            if temp_extracted_srt_path:
                cleanup_single_temp_file(temp_extracted_srt_path)
            if nvencc_subburn_path and nvencc_subburn_path not in [ass_burn_path, title_ass_path] and os.path.exists(nvencc_subburn_path):
                cleanup_single_temp_file(nvencc_subburn_path)
            if ass_burn_path and os.path.exists(ass_burn_path):
                cleanup_single_temp_file(ass_burn_path)
            # Clean up title ASS file
            if title_ass_path and os.path.exists(title_ass_path): 
                cleanup_single_temp_file(title_ass_path)
            CURRENT_JOB_TEMP_DIR = None

    def compute_target_bitrate_kbps(self, options, info, file_path):
        bitrate_kbps = int(options.get("manual_bitrate")) if options.get("override_bitrate") else get_bitrate(
            options.get('resolution'),
            info["framerate"],
            options.get("output_format") == "hdr",
            source_height=info["height"],
            source_width=info["width"]
        )

        max_size_mb = float(options.get('max_size_mb', 0))
        max_duration = float(options.get('max_duration', 0))
        input_duration = get_file_duration(file_path)

        calc_duration = input_duration
        if max_duration > 0 and input_duration > max_duration:
            calc_duration = max_duration

        if max_size_mb > 0:
            total_bits = max_size_mb * 8 * 1024 * 1024
            audio_deduction_kbps = 0
            if options.get("audio_mono"): audio_deduction_kbps += MONO_BITRATE_K
            if options.get("audio_stereo_downmix"): audio_deduction_kbps += STEREO_BITRATE_K
            if options.get("audio_stereo_sofalizer"): audio_deduction_kbps += STEREO_BITRATE_K
            if options.get("audio_surround_51"): audio_deduction_kbps += SURROUND_BITRATE_K
            if options.get("audio_passthrough"): audio_deduction_kbps += 384

            audio_bits = audio_deduction_kbps * 1000 * calc_duration
            available_video_bits = total_bits - audio_bits
            if available_video_bits > 0 and calc_duration > 0:
                max_video_rate_kbps = int((available_video_bits / calc_duration) / 1000)
                if max_video_rate_kbps < 100: max_video_rate_kbps = 100
                if bitrate_kbps > max_video_rate_kbps:
                    print(f"[INFO] Constraint: Limiting video bitrate from {bitrate_kbps}k to {max_video_rate_kbps}k to fit {max_size_mb}MB limit.")
                    bitrate_kbps = max_video_rate_kbps
            else:
                print("[WARN] Max Size too small for audio/duration! Using minimal video bitrate (100k).")
                bitrate_kbps = 100

        return bitrate_kbps, max_duration, input_duration

    def compute_target_resolution_for_options(self, options, info, orientation):
        orientation = self._resolve_orientation(options, orientation)
        res_key = options.get('resolution')
        if orientation in ["hybrid (stacked)", "hybrid-duo (dual source)"]:
            aspect_str = options.get("merged_aspect", "9:16")
            canvas_orient = self._aspect_to_orientation(aspect_str, fallback="vertical")
            if canvas_orient == "vertical":
                width_map = {"720p": 720, "1080p": 1080, "2160p": 2160, "4320p": 4320, "HD": 1080, "4k": 2160, "8k": 4320}
                target_w = width_map.get(res_key, 1080)
            else:
                width_map = {"720p": 1280, "1080p": 1920, "2160p": 3840, "4320p": 7680, "HD": 1920, "4k": 3840, "8k": 7680}
                target_w = width_map.get(res_key, 1920)
            try:
                num, den = map(int, aspect_str.split(':'))
                target_h = int(target_w * den / num)
            except Exception:
                target_h = int(target_w * 16 / 9) if canvas_orient == "vertical" else int(target_w * 9 / 16)
            return (target_w // 2) * 2, (target_h // 2) * 2
        if orientation == "vertical":
            width_map = {"720p": 720, "1080p": 1080, "2160p": 2160, "4320p": 4320, "HD": 1080, "4k": 2160, "8k": 4320}
            target_w = width_map.get(res_key, 1080)
            try:
                num, den = map(int, options.get('vertical_aspect', '9:16').split(':'))
                target_h = int(target_w * den / num)
            except Exception:
                target_h = 1920
            return (target_w // 2) * 2, (target_h // 2) * 2
        if orientation == "original":
            target_w, target_h = compute_original_target_resolution(res_key, info)
            if not target_w or not target_h:
                return info["width"], info["height"]
            return target_w, target_h

        width_map = {"720p": 1280, "1080p": 1920, "2160p": 3840, "4320p": 7680, "HD": 1920, "4k": 3840, "8k": 7680}
        target_w = width_map.get(res_key, 1920)
        try:
            num, den = map(int, options.get('horizontal_aspect', '16:9').split(':'))
            target_h = int(target_w * den / num)
        except Exception:
            target_h = 1080
        return (target_w // 2) * 2, (target_h // 2) * 2

    def construct_nvencc_command(self, input_file, output_file, options, orientation, audio_source_path=None, subtitle_burn_path=None, info=None, base_dir=None):
        if info is None:
            info = get_video_info(input_file)
        is_hdr_output = options.get("output_format") == "hdr"
        bitrate_kbps, _, _ = self.compute_target_bitrate_kbps(options, info, input_file)
        target_w, target_h = self.compute_target_resolution_for_options(options, info, orientation)
        aspect_mode = options.get("aspect_mode", "stretch")

        def _compute_center_crop(src_w, src_h, dst_w, dst_h):
            def _align_crop_dim(src_dim, crop_dim):
                # NVEncC requires even crop offsets on each side, so:
                # (src_dim - crop_dim) / 2 must be even -> (src_dim - crop_dim) % 4 == 0
                crop_dim = max(2, min(src_dim, (crop_dim // 2) * 2))
                if (src_dim - crop_dim) % 4 != 0:
                    for candidate in (crop_dim - 2, crop_dim + 2):
                        if 2 <= candidate <= src_dim and (src_dim - candidate) % 4 == 0:
                            crop_dim = candidate
                            break
                return crop_dim

            try:
                src_ar = float(src_w) / float(src_h)
                dst_ar = float(dst_w) / float(dst_h)
            except Exception:
                return None
            if abs(src_ar - dst_ar) < 1e-6:
                return None
            if src_ar > dst_ar:
                crop_h = src_h
                crop_w = int(round(crop_h * dst_ar))
            else:
                crop_w = src_w
                crop_h = int(round(crop_w / dst_ar))
            crop_w = _align_crop_dim(src_w, crop_w)
            crop_h = _align_crop_dim(src_h, crop_h)
            left = max(0, (src_w - crop_w) // 2)
            right = max(0, src_w - crop_w - left)
            top = max(0, (src_h - crop_h) // 2)
            bottom = max(0, src_h - crop_h - top)
            if any(v % 2 != 0 for v in (left, top, right, bottom)):
                return None
            if left == 0 and right == 0 and top == 0 and bottom == 0:
                return None
            return left, top, right, bottom

        def _compute_pad(src_w, src_h, dst_w, dst_h, ox=0, oy=0):
            try:
                src_ar = float(src_w) / float(src_h)
                dst_ar = float(dst_w) / float(dst_h)
            except Exception:
                return None
            if abs(src_ar - dst_ar) < 1e-6:
                return None
            if src_ar > dst_ar:
                fit_w = dst_w
                fit_h = int(round(dst_w / src_ar))
                fit_h = (fit_h // 2) * 2
            else:
                fit_h = dst_h
                fit_w = int(round(dst_h * src_ar))
                fit_w = (fit_w // 2) * 2
            
            base_pl = max(0, (dst_w - fit_w) // 2)
            base_pl = (base_pl // 2) * 2
            
            base_pt = max(0, (dst_h - fit_h) // 2)
            base_pt = (base_pt // 2) * 2

            pad_left = max(0, min(dst_w - fit_w, base_pl + ox))
            pad_left = (pad_left // 2) * 2
            pad_right = max(0, dst_w - fit_w - pad_left)
            pad_right = (pad_right // 2) * 2
            
            pad_top = max(0, min(dst_h - fit_h, base_pt + oy))
            pad_top = (pad_top // 2) * 2
            pad_bottom = max(0, dst_h - fit_h - pad_top)
            pad_bottom = (pad_bottom // 2) * 2
            
            if pad_left == 0 and pad_right == 0 and pad_top == 0 and pad_bottom == 0:
                return None
            return pad_left, pad_top, pad_right, pad_bottom, fit_w, fit_h

        precrop = None
        use_precrop = (
            aspect_mode == "crop"
            and (info["width"] != target_w or info["height"] != target_h)
        )
        if use_precrop:
            precrop = _compute_center_crop(info["width"], info["height"], target_w, target_h)
        cuvid_codecs = {"h264", "hevc", "av1", "vp9", "mpeg1", "mpeg2", "vc1", "vp8", "mjpeg"}
        input_codec = str(info.get("codec_name", "")).lower()
        # Auto decode mode should prefer hardware decode and only fall back
        # to software decode when the input codec is not supported by avhw.
        auto_use_avsw_reader = input_codec not in cuvid_codecs
        decode_mode = str(options.get("nvencc_decode_mode", DEFAULT_NVENCC_DECODE_MODE)).lower()
        if decode_mode == "avsw":
            use_avsw_reader = True
        elif decode_mode == "avhw":
            use_avsw_reader = False
        else:
            use_avsw_reader = auto_use_avsw_reader
        selected_codec = options.get("video_codec", DEFAULT_VIDEO_CODEC)
        codec_map = {"h264": "h264", "hevc": "hevc", "av1": "av1"}
        codec_name = codec_map.get(selected_codec, "h264")

        cmd = [
            NVENCC_CMD,
            "--avsw" if use_avsw_reader else "--avhw",
            "--codec", codec_name,
            "--output", output_file,
            "-i", input_file
        ]

        seek_start = options.get("seek_start")
        seek_duration = options.get("seek_duration")
        if seek_start is not None:
            # Use time-based seek boundaries for split renders.
            # Frame-based absolute trim (start:end) can force NVEncC to process
            # from frame 0 up to `end`, which makes later chapters progressively slower.
            cmd.extend(["--seek", str(seek_start)])
            if seek_duration is not None:
                seek_to = float(seek_start) + float(seek_duration)
                cmd.extend(["--seekto", str(seek_to)])

        cmd.extend(["--vbr", str(bitrate_kbps), "--max-bitrate", str(bitrate_kbps * 2)])
        # NVEncC preset mapping (FFmpeg p1..p7 -> NVEncC preset names)
        nv_preset = options.get("nvenc_preset", DEFAULT_NVENC_PRESET)
        preset_map = {
            "p1": "performance", "p2": "performance", "p3": "performance",
            "p4": "default",
            "p5": "quality", "p6": "quality", "p7": "quality"
        }
        cmd.extend(["--preset", preset_map.get(str(nv_preset).lower(), "default")])
        cmd.extend(["--lookahead", str(options.get("nvenc_rc_lookahead", DEFAULT_NVENC_RC_LOOKAHEAD))])
        cmd.extend(["--bframes", str(options.get("nvenc_bframes", DEFAULT_NVENC_BFRAMES))])

        multipass_map = {"disabled": "disabled", "qres": "2pass-quarter", "fullres": "2pass-full"}
        mp = multipass_map.get(options.get("nvenc_multipass", DEFAULT_NVENC_MULTIPASS))
        if mp:
            cmd.extend(["--multipass", mp])

        if options.get("nvenc_spatial_aq", DEFAULT_NVENC_SPATIAL_AQ) == "1":
            cmd.append("--aq")
        if options.get("nvenc_temporal_aq", DEFAULT_NVENC_TEMPORAL_AQ) == "1":
            cmd.append("--aq-temporal")

        bref = options.get("nvenc_b_ref_mode", DEFAULT_NVENC_B_REF_MODE)
        if bref in ["disabled", "each", "middle", "auto"]:
            cmd.extend(["--bref-mode", bref])

        color_tag_mode = str(options.get("nvencc_color_tag_mode", DEFAULT_NVENCC_COLOR_TAG_MODE)).lower()
        strict_no_color_tagging = bool(options.get("nvencc_strict_no_color_tagging", DEFAULT_NVENCC_STRICT_NO_COLOR_TAGGING))

        auto_apply_color_tags = False
        if color_tag_mode == "custom":
            resolved_depth = str(options.get("nvencc_output_depth", DEFAULT_NVENCC_OUTPUT_DEPTH)).strip().lower()
            if resolved_depth == "auto":
                resolved_depth = "10" if is_hdr_output else "8"
            if resolved_depth not in ["8", "10"]:
                resolved_depth = "10" if is_hdr_output else "8"

            color_prim = str(options.get("nvencc_color_prim", DEFAULT_NVENCC_COLOR_PRIM)).strip() or DEFAULT_NVENCC_COLOR_PRIM
            color_transfer = str(options.get("nvencc_color_transfer", DEFAULT_NVENCC_COLOR_TRANSFER)).strip() or DEFAULT_NVENCC_COLOR_TRANSFER
            color_matrix = str(options.get("nvencc_color_matrix", DEFAULT_NVENCC_COLOR_MATRIX)).strip() or DEFAULT_NVENCC_COLOR_MATRIX
            auto_apply_color_tags = True
        else:
            resolved_depth = "10" if is_hdr_output else "8"
            if is_hdr_output:
                color_prim, color_transfer, color_matrix = "bt2020", "smpte2084", "bt2020nc"
            else:
                color_prim, color_transfer, color_matrix = "bt709", "bt709", "bt709"
            # In auto mode, only apply explicit color tags when converting
            # between SDR and HDR. If input/output are same color domain,
            # keep tagging disabled by default.
            auto_apply_color_tags = bool(info.get("is_hdr", False)) != bool(is_hdr_output)

        cmd.extend(["--output-depth", resolved_depth])
        if not strict_no_color_tagging and auto_apply_color_tags:
            cmd.extend(["--colorprim", color_prim, "--transfer", color_transfer, "--colormatrix", color_matrix])
        upscale_algo = options.get("upscale_algo", DEFAULT_UPSCALE_ALGO)
        resize_algo = None
        if upscale_algo == "nvvfx-superres":
            mode = options.get("nvenc_superres_mode", DEFAULT_NVENC_SUPERRES_MODE)
            resize_algo = f"nvvfx-superres,superres-mode={mode}"
        elif upscale_algo == "ngx-vsr":
            q = options.get("nvenc_ngx_vsr_quality", DEFAULT_NVENC_NGX_VSR_QUALITY)
            resize_algo = f"ngx,vsr-quality={q}"
        elif upscale_algo in ["nearest", "bilinear", "bicubic", "lanczos", "spline36"]:
            resize_algo = upscale_algo

        if precrop:
            cmd.extend(["--crop", f"{precrop[0]},{precrop[1]},{precrop[2]},{precrop[3]}"])

        if resize_algo and (info["width"] != target_w or info["height"] != target_h):
            output_res = f"{target_w}x{target_h}"
            pad_args = None
            if aspect_mode == "pad":
                ox = int(options.get("video_offset_x", "0"))
                oy = int(options.get("video_offset_y", "0"))
                pad_res = _compute_pad(info["width"], info["height"], target_w, target_h, ox, oy)
                if not pad_res:
                    output_res = f"{output_res},preserve_aspect_ratio=decrease"
                else:
                    pad_args = pad_res[:4]
            elif aspect_mode == "crop" and not precrop:
                output_res = f"{output_res},preserve_aspect_ratio=increase"
            
            cmd.extend(["--vpp-resize", f"{resize_algo}", "--output-res", output_res])
            if pad_args:
                pad_color_hex = options.get("pad_color", DEFAULT_PAD_COLOR).lstrip('#')
                cmd.extend(["--vpp-pad", f"{pad_args[0]},{pad_args[1]},{pad_args[2]},{pad_args[3]},color={pad_color_hex}"])

        if options.get("nvenc_nvvfx_denoise"):
            cmd.append("--vpp-nvvfx-denoise")

        if options.get("generate_log"):
            log_path = os.path.join(os.path.dirname(output_file), f"{os.path.splitext(os.path.basename(output_file))[0]}_nvencc.log")
            cmd.extend(["--log", log_path, "--log-level", "info"])

        if audio_source_path:
            cmd.extend(["--audio-source", audio_source_path])
        else:
            cmd.extend(["--audio-copy"])

        if subtitle_burn_path:
            # Use relative path to avoid "poisoned" parent directory names
            safe_sub = get_safe_filter_path(subtitle_burn_path, base_dir=base_dir)
            cmd.extend(["--vpp-subburn", f"filename={safe_sub},charcode=utf-8"])
        return cmd

    def run_nvencc_command(self, cmd, duration=None, progress_callback=None, cwd=None):
        global CURRENT_FFMPEG_PROCESS
        print("Running NVEncC command:")
        print(" ".join(f'"{c}"' if " " in c else c for c in cmd))
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                   env=env, text=True, encoding='utf-8', errors='replace', bufsize=1,
                                   cwd=cwd)
        CURRENT_FFMPEG_PROCESS = process
        
        carry = ""
        progress_line_active = False
        last_progress_len = 0
        
        if process.stdout:
            while True:
                ch = process.stdout.read(1)
                if ch == "":
                    if process.poll() is not None:
                        # Flush any trailing text
                        if carry.strip():
                            line = carry.strip()
                            sys.stdout.write(("\n" if progress_line_active else "") + line + "\n")
                            sys.stdout.flush()
                        break
                    continue
                
                if ch in ("\r", "\n"):
                    line = carry.strip()
                    carry = ""
                    if not line:
                        continue
                    
                    # Progress Parsing for GUI
                    if progress_callback:
                        # Typical NVEncC progress: [ 10.5%] 1050/10000 frames...
                        match = re.search(r'\[\s*(\d+\.?\d*)%\]', line)
                        if match:
                             try:
                                 progress_callback(float(match.group(1)))
                             except Exception: pass

                    # Dynamic console update for progress-like lines
                    is_progress = any(tok in line for tok in ("fps", "frames", "%", "remaining"))
                    if is_progress:
                        pad = " " * max(0, last_progress_len - len(line))
                        sys.stdout.write("\r" + line + pad)
                        sys.stdout.flush()
                        progress_line_active = True
                        last_progress_len = len(line)
                    else:
                        if progress_line_active:
                            sys.stdout.write("\n")
                            progress_line_active = False
                            last_progress_len = 0
                        sys.stdout.write(line + "\n")
                        sys.stdout.flush()
                else:
                    carry += ch
                    
            process.stdout.close()
        ret_code = process.wait()
        CURRENT_FFMPEG_PROCESS = None
        if progress_line_active:
            sys.stdout.write("\n")
        return ret_code

    def construct_ffmpeg_audio_prepass(self, input_file, output_audio, options, seek_start=None, seek_duration=None):
        cmd = [FFMPEG_CMD, "-y"]
        if seek_start is not None:
            cmd.extend(["-ss", str(seek_start)])
        cmd.extend(["-i", input_file])
        if seek_duration is not None:
            cmd.extend(["-t", str(seek_duration)])
        cmd.extend(["-vn", "-sn", "-dn"])
        audio_cmd_parts = self.build_audio_segment(input_file, options, loudnorm_stats=options.get("_loudnorm_stats"))
        cmd.extend(audio_cmd_parts)
        cmd.append(output_audio)
        return cmd

    def construct_ffmpeg_command(self, job, output_file, orientation, ass_burn_path=None, options=None, title_ass_path=None, encoder_backend="ffmpeg", base_dir=None):
        options = options or job['options']
        file_path = job['video_path']
        
        # Override Top video for hybrid-duo
        if orientation == "hybrid-duo (dual source)":
            explicit_top = options.get("hybrid_top_path", "").strip()
            if explicit_top and os.path.exists(explicit_top):
                file_path = explicit_top
                
        info = get_video_info(file_path)
        decoder_available, _ = check_decoder_availability(info["codec_name"])
        decoder_map = {"h264": "h264_cuvid", "hevc": "hevc_cuvid", "av1": "av1_cuvid", "vp9": "vp9_cuvid"}
        decoder = decoder_map.get(info["codec_name"], info["codec_name"]) if decoder_available else info["codec_name"]
        use_cuda_decoder = "_cuvid" in decoder
        
        seek_start = options.get("seek_start")
        seek_duration = options.get("seek_duration")
        
        cmd = [FFMPEG_CMD, "-y", "-hide_banner"]
        if seek_start is not None:
            cmd.extend(["-ss", str(seek_start)])
            
        cmd += (["-hwaccel", "cuda", "-hwaccel_output_format", "cuda"] if use_cuda_decoder else []) + ["-c:v", decoder, "-i", file_path]

        # Second Input for Hybrid-Duo
        if orientation == "hybrid-duo (dual source)":
            explicit_bot = options.get("hybrid_bottom_path", "").strip()
            if explicit_bot and os.path.exists(explicit_bot):
                bot_path = explicit_bot
            else:
                base_name, ext = os.path.splitext(file_path)
                if base_name.endswith("-top"):
                    bot_path = base_name[:-4] + "-bot" + ext
                elif base_name.endswith("_top"):
                    bot_path = base_name[:-4] + "_bot" + ext
                else:
                    bot_path = base_name + "-bot" + ext
                    
                if not os.path.exists(bot_path):
                    # Fallback replacement
                    bot_path_alt = file_path.replace("-top", "-bot").replace("_top", "_bot")
                    if os.path.exists(bot_path_alt):
                        bot_path = bot_path_alt
                    else:
                        raise VideoProcessingError(f"Hybrid-Duo requires a bottom video. Could not find: {bot_path}")

            info_bot = get_video_info(bot_path)
            decoder_available_bot, _ = check_decoder_availability(info_bot["codec_name"])
            decoder_bot = decoder_map.get(info_bot["codec_name"], info_bot["codec_name"]) if decoder_available_bot else info_bot["codec_name"]
            use_cuda_decoder_bot = "_cuvid" in decoder_bot

            if seek_start is not None:
                cmd.extend(["-ss", str(seek_start)])
            cmd += (["-hwaccel", "cuda", "-hwaccel_output_format", "cuda"] if use_cuda_decoder_bot else []) + ["-c:v", decoder_bot, "-i", bot_path]

        if seek_duration is not None:
            cmd.extend(["-t", str(seek_duration)])

        filter_complex_parts, is_hdr_output = [], options.get("output_format") == 'hdr'
        # For codecs without CUVID support (e.g. ProRes), frames are software-decoded to CPU.
        # CUDA filters (scale_cuda, overlay_cuda, etc.) need GPU frames, so we convert
        # the pixel format and upload to CUDA at the start of the filter chain.
        if not use_cuda_decoder:
            upload_fmt = "p010le" if info["bit_depth"] == 10 else "nv12"
            filter_complex_parts.append(f"[0:v]format={upload_fmt},hwupload_cuda[v_cuda_in]")
            cuda_video_in = "[v_cuda_in]"
        else:
            cuda_video_in = "[0:v]"

        cuda_video_in_top = cuda_video_in
        if orientation == "hybrid-duo (dual source)":
            if not use_cuda_decoder_bot:
                upload_fmt_bot = "p010le" if info_bot["bit_depth"] == 10 else "nv12"
                filter_complex_parts.append(f"[1:v]format={upload_fmt_bot},hwupload_cuda[v_cuda_in_bot]")
                cuda_video_in_bot = "[v_cuda_in_bot]"
            else:
                cuda_video_in_bot = "[1:v]"

        upscale_algo = options.get("upscale_algo")
        use_nvencc_resize = encoder_backend == "preprocess" and upscale_algo in ["nvvfx-superres", "ngx-vsr"]
        ffmpeg_upscale_algo = upscale_algo if upscale_algo in ["nearest", "bilinear", "bicubic", "lanczos"] else DEFAULT_UPSCALE_ALGO
        eff_w, eff_h = None, None
        video_out_tag = "0:v:0"
        audio_cmd_parts = self.build_audio_segment(file_path, options, base_dir=base_dir, loudnorm_stats=options.get("_loudnorm_stats"))
        audio_fc_str = ""
        try:
            audio_fc_index = audio_cmd_parts.index("-filter_complex")
            audio_fc_str = audio_cmd_parts.pop(audio_fc_index + 1)
            audio_cmd_parts.pop(audio_fc_index)
        except ValueError: pass
        if orientation in ["hybrid (stacked)", "hybrid-duo (dual source)"]:
            target_w, total_h = self.compute_target_resolution_for_options(options, info, orientation)

            def get_block_filters(aspect_str, mode, upscale_algo, override_h=None):
                if not aspect_str: raise VideoProcessingError("Missing Aspect Ratio setting in preset (Hybrid block).")
                if not mode: raise VideoProcessingError("Missing Mode setting in preset (Hybrid block).")
                if not upscale_algo: raise VideoProcessingError("Missing Upscale Algorithm setting in preset.")
                
                try:
                    num, den = map(int, aspect_str.split(':'))
                except (ValueError, AttributeError):
                    raise VideoProcessingError(f"Invalid aspect ratio format: '{aspect_str}'. Expected 'num:den'.")
                
                target_h = override_h if override_h is not None else (int(target_w * den / num) // 2) * 2
                scale = f"scale_cuda=w={target_w}:h={target_h}:interp_algo={upscale_algo}"
                if mode == 'stretch': return scale, "", target_h
                vf = f"{scale}:force_original_aspect_ratio={'decrease' if mode == 'pad' else 'increase'}"
                pad_color = options.get("pad_color", DEFAULT_PAD_COLOR)
                cpu = f"pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2:{pad_color}" if mode == 'pad' else f"crop={target_w}:{target_h}"
                return vf, cpu, target_h

            safe_algo = ffmpeg_upscale_algo
            if not safe_algo: raise VideoProcessingError("Upscale algorithm not specified in preset.")
            
            # Top block uses its own aspect ratio to determine height
            top_vf, top_cpu, top_h = get_block_filters(options.get('hybrid_top_aspect'), options.get('hybrid_top_mode'), safe_algo)
            # Bottom block fills the remaining space
            bot_h_needed = total_h - top_h
            bot_vf, bot_cpu, bot_h = get_block_filters(options.get('hybrid_bottom_aspect'), options.get('hybrid_bottom_mode'), safe_algo, override_h=bot_h_needed)
            
            cpu_pix_fmt = "p010le" if info["bit_depth"] == 10 else "nv12"
            cpu_chain = []
            if info["is_hdr"] and not is_hdr_output and options.get("lut_file") and os.path.exists(options.get("lut_file")):
                safe_lut = escape_ffmpeg_filter_path(options.get("lut_file"), base_dir=base_dir)
                cpu_chain.append(f"lut3d=file={safe_lut}")
            if options.get("fruc"): cpu_chain.append(f"minterpolate=fps={options.get('fruc_fps')}")
            if options.get("use_sharpening"):
                algo = options.get("sharpening_algo")
                strength = options.get("sharpening_strength", "0.5")
                if algo == "cas": cpu_chain.append(f"cas=strength={strength}")
                else: cpu_chain.append(f"unsharp=luma_msize_x=3:luma_msize_y=3:luma_amount={strength}")
            if options.get("ffmpeg_denoise_vulkan"):
                fmt = "p010le" if info["bit_depth"] == 10 else "nv12"
                cpu_chain.append(f"hwupload=vulkan,nlmeans_vulkan,hwdownload,format={fmt}")
            if ass_burn_path:
                safe_ass = escape_ffmpeg_filter_path(ass_burn_path, base_dir=base_dir)
                cpu_chain.append(f"subtitles=filename={safe_ass}:original_size={target_w}x{total_h}") 
            if title_ass_path:
                safe_title_ass = escape_ffmpeg_filter_path(title_ass_path, base_dir=base_dir)
                cpu_chain.append(f"subtitles=filename={safe_title_ass}:original_size={target_w}x{total_h}")
            if not is_hdr_output: cpu_chain.append("format=nv12")
            
            # For "preprocess" backend, the output encoder is ffv1 (software), so we must NOT upload back to hardware.
            # Otherwise we'll get a format mismatch error.
            if encoder_backend == "preprocess":
                final_v_out = f"[stacked]{','.join(filter(None, cpu_chain))}[v_out]" if cpu_chain else "[stacked][v_out]"
            else:
                final_v_out = f"[stacked]{','.join(filter(None, cpu_chain))},hwupload_cuda[v_out]" if cpu_chain else "[stacked]hwupload_cuda[v_out]"

            if orientation == "hybrid-duo (dual source)":
                video_fc_parts = [
                    f"{cuda_video_in_top}{top_vf}[v_top_out]", 
                    f"{cuda_video_in_bot}{bot_vf}[v_bot_out]"
                ]
            else:
                video_fc_parts = [
                    f"{cuda_video_in}split=2[v_top_in][v_bot_in]",
                    f"[v_top_in]{top_vf}[v_top_out]", 
                    f"[v_bot_in]{bot_vf}[v_bot_out]"
                ]

            video_fc_parts.extend([
                f"[v_top_out]hwdownload,format={cpu_pix_fmt},setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709,{top_cpu}[cpu_top]", 
                f"[v_bot_out]hwdownload,format={cpu_pix_fmt},setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709,{bot_cpu}[cpu_bot]",
                "[cpu_top][cpu_bot]vstack=inputs=2[stacked]",
                final_v_out
            ])
            filter_complex_parts.extend(video_fc_parts)
            video_out_tag = "[v_out]"
        else:
            vf_filters, cpu_filters = [], []
            # Default input tag for cases like "original" orientation (no resize/aspect chain)
            video_in_tag = cuda_video_in
            if orientation == "original":
                res_key = options.get('resolution')
                if res_key and res_key.lower() != "original":
                    safe_algo = ffmpeg_upscale_algo
                    if not safe_algo: raise VideoProcessingError("Upscale algorithm not specified in preset.")
                    target_w, target_h = compute_original_target_resolution(res_key, info)
                    if not target_w or not target_h:
                        raise VideoProcessingError(f"Invalid resolution '{res_key}' for original mode.")
                    if not (use_nvencc_resize and options.get("aspect_mode") == "stretch"):
                        vf_filters.append(f"scale_cuda=w={target_w}:h={target_h}:interp_algo={safe_algo}")
                    else:
                        target_w, target_h = info["width"], info["height"]
            else:
                res_key = options.get('resolution')
                if orientation == "vertical":
                    aspect_str = options.get('vertical_aspect')
                    width_map = {"720p": 720, "1080p": 1080, "2160p": 2160, "4320p": 4320, "HD": 1080, "4k": 2160, "8k": 4320}
                    if not aspect_str: raise VideoProcessingError("Missing 'Vertical Aspect Ratio' in preset.")
                else:
                    aspect_str = options.get('horizontal_aspect')
                    width_map = {"720p": 1280, "1080p": 1920, "2160p": 3840, "4320p": 7680, "HD": 1920, "4k": 3840, "8k": 7680}
                    if not aspect_str: raise VideoProcessingError("Missing 'Horizontal Aspect Ratio' in preset.")
                
                ox = options.get("video_offset_x", "0")
                oy = options.get("video_offset_y", "0")

                target_w = width_map.get(res_key)
                if target_w is None:
                    raise VideoProcessingError(f"Invalid resolution '{res_key}' for {orientation} mode.")
                    
                try:
                    num, den = map(int, aspect_str.split(':'))
                except (ValueError, AttributeError):
                    raise VideoProcessingError(f"Invalid aspect ratio format: '{aspect_str}'. Expected 'num:den'.")
                    
                target_h = int(target_w * den / num)
                target_w, target_h = (target_w // 2) * 2, (target_h // 2) * 2
                
                safe_algo = ffmpeg_upscale_algo
                if not safe_algo: raise VideoProcessingError("Upscale algorithm not specified in preset.")
                
                scale_base = f"scale_cuda=w={target_w}:h={target_h}:interp_algo={safe_algo}"
                
                aspect_mode = options.get("aspect_mode", "pad")
                if aspect_mode == 'pixelate':
                    mult = options.get("pixelate_multiplier", DEFAULT_PIXELATE_MULTIPLIER)
                    try: m = max(1, int(mult))
                    except: m = 16
                    
                    bright = options.get("pixelate_brightness", DEFAULT_PIXELATE_BRIGHTNESS)
                    sat = options.get("pixelate_saturation", DEFAULT_PIXELATE_SATURATION)
                    
                    target_fmt = "p010le" if info["bit_depth"] == 10 else "nv12"
                    pixelate_fc = (
                        f"{video_in_tag}split=2[v_bg_in][v_fg_in];"
                        f"[v_bg_in]scale_cuda=w={target_w//m}:h={target_h//m}:interp_algo={safe_algo}:format={target_fmt},"
                        f"hwdownload,format={target_fmt},setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709,eq=brightness={bright}:saturation={sat},hwupload_cuda,"
                        f"scale_cuda=w={target_w}:h={target_h}:interp_algo=nearest:format={target_fmt}[v_bg_pixelated];"
                        f"[v_fg_in]scale_cuda=w={target_w}:h={target_h}:interp_algo={safe_algo}:force_original_aspect_ratio=decrease:format={target_fmt}[v_fg_scaled];"
                        f"[v_bg_pixelated][v_fg_scaled]overlay_cuda=x=floor(({target_w}-w)/2+{ox}):y=floor(({target_h}-h)/2+{oy}),setsar=1[v_pixelate_combined]"
                    )
                    filter_complex_parts.append(pixelate_fc)
                    video_in_tag = "[v_pixelate_combined]"
                elif aspect_mode == 'blur':
                    # Blur mode: Downscale, blur on CPU, upscale
                    sigma = options.get("blur_sigma", DEFAULT_BLUR_SIGMA)
                    steps = options.get("blur_steps", DEFAULT_BLUR_STEPS)
                    bright = options.get("pixelate_brightness", DEFAULT_PIXELATE_BRIGHTNESS)
                    sat = options.get("pixelate_saturation", DEFAULT_PIXELATE_SATURATION)
                    
                    target_fmt = "p010le" if info["bit_depth"] == 10 else "nv12"
                    # Downscale by 2x for performance
                    blur_fc = (
                        f"{video_in_tag}split=2[v_bg_in][v_fg_in];"
                        f"[v_bg_in]scale_cuda=w={target_w//2}:h={target_h//2}:interp_algo={safe_algo}:format={target_fmt},"
                        f"hwdownload,format={target_fmt},setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709,gblur=sigma={sigma}:steps={steps},eq=brightness={bright}:saturation={sat},format={target_fmt},hwupload_cuda,"
                        f"scale_cuda=w={target_w}:h={target_h}:interp_algo=bicubic:format={target_fmt}[v_bg_blurred];"
                        f"[v_fg_in]scale_cuda=w={target_w}:h={target_h}:interp_algo={safe_algo}:force_original_aspect_ratio=decrease:format={target_fmt}[v_fg_scaled];"
                        f"[v_bg_blurred][v_fg_scaled]overlay_cuda=x=floor(({target_w}-w)/2+{ox}):y=floor(({target_h}-h)/2+{oy}),setsar=1[v_blur_combined]"
                    )
                    filter_complex_parts.append(blur_fc)
                    video_in_tag = "[v_blur_combined]"
                elif aspect_mode == 'ambient':
                    # Ambient Glow mode: crop to fill, blur on CPU, saturation boost
                    sigma = options.get("blur_sigma", "25")
                    steps = options.get("blur_steps", "1")
                    sat = options.get("pixelate_saturation", "1.5")
                    spread_str = options.get("ambient_spread", DEFAULT_AMBIENT_SPREAD)
                    try:
                        spread = max(1, int(spread_str))
                    except ValueError:
                        spread = 2
                    
                    target_fmt = "p010le" if info["bit_depth"] == 10 else "nv12"
                    ambient_fc = (
                        f"{video_in_tag}split=2[v_bg_in][v_fg_in];"
                        f"[v_bg_in]scale_cuda=w={target_w}:h={target_h}:interp_algo={safe_algo}:force_original_aspect_ratio=decrease:format={target_fmt},"
                        f"pad_cuda={target_w}:{target_h}:floor(({target_w}-iw)/2+{ox}):floor(({target_h}-ih)/2+{oy}):black,"
                        f"scale_cuda=w={target_w//spread}:h={target_h//spread}:interp_algo=bilinear:format={target_fmt},"
                        f"hwdownload,format={target_fmt},setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709,gblur=sigma={sigma}:steps={steps},eq=saturation={sat},format={target_fmt},hwupload_cuda,"
                        f"scale_cuda=w={target_w}:h={target_h}:interp_algo=bicubic:format={target_fmt}[v_bg_ambient];"
                        f"[v_fg_in]scale_cuda=w={target_w}:h={target_h}:interp_algo={safe_algo}:force_original_aspect_ratio=decrease:format={target_fmt}[v_fg_scaled];"
                        f"[v_bg_ambient][v_fg_scaled]overlay_cuda=x=floor(({target_w}-w)/2+{ox}):y=floor(({target_h}-h)/2+{oy}),setsar=1[v_ambient_combined]"
                    )
                    filter_complex_parts.append(ambient_fc)
                    video_in_tag = "[v_ambient_combined]"
                elif aspect_mode == 'pad':
                    pad_color = options.get("pad_color", DEFAULT_PAD_COLOR)
                    vf_filters.append(f"{scale_base}:force_original_aspect_ratio=decrease")
                    vf_filters.append(f"pad_cuda={target_w}:{target_h}:floor(({target_w}-iw)/2+{ox}):floor(({target_h}-ih)/2+{oy}):{pad_color}")
                elif aspect_mode == 'crop':
                    vf_filters.append(f"{scale_base}:force_original_aspect_ratio=increase")
                    cpu_filters.append(f"crop={target_w}:{target_h}")
                else:
                    if use_nvencc_resize and aspect_mode == "stretch":
                        target_w, target_h = info["width"], info["height"]
                    else:
                        vf_filters.append(scale_base)
            if info["is_hdr"] and not is_hdr_output and options.get("lut_file") and os.path.exists(options.get("lut_file")):
                safe_lut = escape_ffmpeg_filter_path(options.get("lut_file"), base_dir=base_dir)
                cpu_filters.append(f"lut3d=file={safe_lut}")
            if options.get("fruc"): cpu_filters.append(f"minterpolate=fps={options.get('fruc_fps')}")
            if options.get("use_sharpening"):
                algo = options.get("sharpening_algo")
                strength = options.get("sharpening_strength", "0.5")
                if algo == "cas": cpu_filters.append(f"cas=strength={strength}")
                else: cpu_filters.append(f"unsharp=luma_msize_x=3:luma_msize_y=3:luma_amount={strength}")
            if options.get("ffmpeg_denoise_vulkan"):
                fmt = "p010le" if info["bit_depth"] == 10 else "nv12"
                cpu_filters.append(f"hwupload=vulkan,nlmeans_vulkan,hwdownload,format={fmt}")
            if ass_burn_path:
                safe_ass = escape_ffmpeg_filter_path(ass_burn_path, base_dir=base_dir)
                cpu_filters.append(f"subtitles=filename={safe_ass}:original_size={target_w}x{target_h}")
            if title_ass_path:
                safe_title_ass = escape_ffmpeg_filter_path(title_ass_path, base_dir=base_dir)
                cpu_filters.append(f"subtitles=filename={safe_title_ass}:original_size={target_w}x{target_h}")
            if cpu_filters:
                # One single trip to CPU for all the heavy lifting
                processing_chain = [f"hwdownload,format={'p010le' if info['bit_depth'] == 10 else 'nv12'}", "setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709"] + cpu_filters
                if not is_hdr_output: processing_chain.append("format=nv12")
                vf_filters.append(f"{','.join(processing_chain)},hwupload_cuda")
            if vf_filters:
                filter_complex_parts.append(f"{video_in_tag}{','.join(vf_filters)}[v_out]")
                video_out_tag = "[v_out]"
            elif video_in_tag != cuda_video_in:
                video_out_tag = video_in_tag
        
        # Track effective resolution for metadata/aspect forcing
        eff_w, eff_h = (target_w, target_h) if ('target_w' in locals() and 'target_h' in locals()) else (None, None)

        if filter_complex_parts or audio_fc_str:
            full_fc = ";".join(filter(None, filter_complex_parts + ([audio_fc_str] if audio_fc_str else [])))
            cmd.extend(["-filter_complex", full_fc])
        cmd.extend(["-map", video_out_tag])
        cmd.extend(audio_cmd_parts)
        
        bitrate_kbps, max_duration, input_duration = self.compute_target_bitrate_kbps(options, info, file_path)

        if max_duration > 0 and input_duration > max_duration and seek_duration is None:
            # Insert -t before output file (last arg) to trim output
            # Current cmd structure: [...encoder... -f mp4 output_file]
            cmd.insert(len(cmd)-2, "-t")
            cmd.insert(len(cmd)-2, str(max_duration))
        
        gop_len = math.ceil(info["framerate"] / 2) if info["framerate"] > 0 else 30

        if encoder_backend == "preprocess":
            # GPU-only intermediate: lossless NVENC so NVEncC can decode via CUVID.
            if is_hdr_output or info["bit_depth"] == 10:
                pix_fmt = "yuv420p10le"
                encoder_opts = [
                    "-c:v", "hevc_nvenc",
                    "-pix_fmt", pix_fmt,
                    "-preset", "p1",
                    "-tune", "lossless",
                    "-rc", "constqp",
                    "-qp", "0"
                ]
            else:
                pix_fmt = "yuv420p"
                encoder_opts = [
                    "-c:v", "h264_nvenc",
                    "-pix_fmt", pix_fmt,
                    "-preset", "p1",
                    "-tune", "lossless",
                    "-rc", "constqp",
                    "-qp", "0"
                ]
            cmd.extend(encoder_opts)
            cmd.extend(["-f", "matroska", output_file])
            return cmd
        
        # Base encoder options
        nv_preset = options.get("nvenc_preset", DEFAULT_NVENC_PRESET)
        nv_tune = options.get("nvenc_tune", DEFAULT_NVENC_TUNE)
        nv_lookahead = options.get("nvenc_rc_lookahead", DEFAULT_NVENC_RC_LOOKAHEAD)
        nv_multipass = options.get("nvenc_multipass", DEFAULT_NVENC_MULTIPASS)
        nv_spatial_aq = options.get("nvenc_spatial_aq", DEFAULT_NVENC_SPATIAL_AQ)
        nv_temporal_aq = options.get("nvenc_temporal_aq", DEFAULT_NVENC_TEMPORAL_AQ)
        nv_bframes = options.get("nvenc_bframes", DEFAULT_NVENC_BFRAMES)
        nv_b_ref_mode = options.get("nvenc_b_ref_mode", DEFAULT_NVENC_B_REF_MODE)

        selected_codec = options.get("video_codec", DEFAULT_VIDEO_CODEC)
        encoder_map = {"h264": "h264_nvenc", "hevc": "hevc_nvenc", "av1": "av1_nvenc"}
        encoder_name = encoder_map.get(selected_codec, "h264_nvenc")

        encoder_opts = ["-c:v", encoder_name, "-preset", nv_preset, "-tune", nv_tune]

        if selected_codec == "h264":
            nv_profile = options.get("nvenc_profile_sdr", DEFAULT_NVENC_PROFILE_SDR)
            encoder_opts.extend(["-profile:v", nv_profile])
        elif selected_codec == "hevc":
            if is_hdr_output:
                nv_profile = options.get("nvenc_profile_hdr", DEFAULT_NVENC_PROFILE_HDR)
            else:
                nv_profile = "main"
            encoder_opts.extend(["-profile:v", nv_profile])

        encoder_opts.extend([
            "-b:v", f"{bitrate_kbps}k", "-maxrate", f"{bitrate_kbps*2}k", "-bufsize", f"{bitrate_kbps*2}k",
            "-g", str(gop_len), "-bf", nv_bframes, "-b_ref_mode", nv_b_ref_mode,
            "-multipass", nv_multipass, "-spatial-aq", nv_spatial_aq, "-temporal-aq", nv_temporal_aq, "-rc-lookahead", nv_lookahead
        ])

        if is_hdr_output:
            encoder_opts.extend(["-color_primaries", "bt2020", "-color_trc", "smpte2084", "-colorspace", "bt2020nc"])
        else:
            encoder_opts.extend(["-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709"])

        # Force rotation strip and aspect ratio for landscape output if we had a vertical source
        if eff_w and eff_h:
            encoder_opts.extend(["-metadata:s:v", "rotate=0", "-aspect", f"{eff_w}:{eff_h}"])
        
        cmd.extend(encoder_opts)
        cmd.extend(["-f", "mp4", output_file])
        return cmd

    def validate_processing_settings(self):
        issues = []
        if self.encoder_backend_var.get() in ["nvencc_with_ffmpeg", "nvencc_only", "nvencc_video_with_ffmpeg_audio"] and not check_nvencc_availability():
            issues.append(f"NVEncC not found. Set NVENCC_PATH or ensure '{NVENCC_CMD}' is in PATH.")
        if self.output_format_var.get() == 'sdr':
             lut_path = self.lut_file_var.get()
             if lut_path and not os.path.exists(lut_path):
                 issues.append(f"LUT file path is set but file not found: {lut_path}")
        
        selected_codec = self.video_codec_var.get()
        if self.output_format_var.get() == "hdr" and selected_codec == "h264":
            issues.append("HDR output requires HEVC or AV1. H.264 cannot carry HDR.")
        
        if selected_codec == "h264" and self.resolution_var.get() == "4320p":
            proceed = messagebox.askyesno(
                "H.264 + 4320p Warning",
                "H.264 with 4320p output is likely to fail on most NVENC GPUs.\n"
                "Do you want to continue anyway?"
            )
            if not proceed:
                return False
        
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
        try:
            if int(self.ffmpeg_threads_var.get()) < 0:
                issues.append("FFmpeg threads must be 0 or a positive integer.")
        except ValueError:
            issues.append("FFmpeg threads must be an integer (0 = auto).")
        raw_priority = str(self.ffmpeg_priority_var.get()).strip().lower()
        if normalize_ffmpeg_priority(raw_priority) != raw_priority:
            issues.append("FFmpeg priority must be one of: idle, below_normal, normal, above_normal, high, realtime.")

        if issues:
            messagebox.showerror("Configuration Issues", "Please fix the following issues:\n" + "\n".join(f"• {issue}" for issue in issues))
            return False
        return True

    def start_processing(self):
        if not self.processing_jobs: messagebox.showwarning("No Jobs", "Please add files to the queue."); return
        if not self.validate_processing_settings(): return
        self.output_mode = self.output_mode_var.get()
        
        # Check if GUI should be closed for console-only processing
        close_gui = self.close_gui_var.get()
        
        if close_gui:
            # Snapshot jobs before destroying GUI (Tk vars won't survive root.destroy)
            jobs_snapshot = copy.deepcopy(self.processing_jobs)
            print("\n[INFO] 'Close GUI on Processing' enabled. Closing GUI and processing in console...")
            self.root.destroy()
            self._process_files_console(jobs_snapshot)
            return
        
        # Disable button to prevent re-entry
        self.start_button.config(state="disabled")
        
        # Start Thread
        threading.Thread(target=self._process_files_thread, daemon=True).start()

    def _process_files_console(self, jobs):
        """Process jobs in console without GUI (called after root.destroy)."""
        print("\n" + "="*80 + "\n--- Starting processing batch (Console Mode) ---")
        successful, failed = 0, 0
        total_jobs = len(jobs)
        
        for i, job in enumerate(jobs):
            print("\n" + "-"*80 + f"\nStarting job {i + 1}/{total_jobs}: {job['display_name']}\n" + "-"*80)
            try:
                orientation = job['options'].get("orientation", DEFAULT_ORIENTATION)
                resolution = job['options'].get("resolution", "Unknown")
                print(f"[DEBUG] Job: {job['display_name']}")
                print(f"[DEBUG] Orientation: {orientation}")
                print(f"[DEBUG] Resolution: {resolution}")
                
                self.build_ffmpeg_command_and_run(job, orientation)
                successful += 1; print(f"[SUCCESS] Job '{job['display_name']}' completed successfully.")
            except (VideoProcessingError, Exception) as e:
                failed += 1; print(f"\n[ERROR] Job failed for '{job['display_name']}': {e}")
        
        final_message = f"Processing Complete: {successful} successful, {failed} failed"
        print("\n" + "="*80 + "\n" + final_message)
        
        # Check if hibernate was requested
        hibernate = any(j.get('options', {}).get('hibernate_when_done', False) for j in jobs)
        if hibernate:
            print("\n[INFO] Hibernate requested. Hibernating system...")
            subprocess.run(["shutdown", "/h"], shell=True)
        sys.exit(0)

    def _process_files_thread(self):
        print("\n" + "="*80 + "\n--- Starting processing batch ---")
        successful, failed = 0, 0
        total_jobs = len(self.processing_jobs)
        
        for i, job in enumerate(self.processing_jobs):
            self.root.after(0, lambda m=f"Processing {i + 1}/{total_jobs}: {job['display_name']}": self.update_status(m))
            self.root.after(0, lambda: self.progress_bar.config(value=0))
            
            print("\n" + "-"*80 + f"\nStarting job {i + 1}/{total_jobs}: {job['display_name']}\n" + "-"*80)
            try:
                orientation = job['options'].get("orientation", DEFAULT_ORIENTATION)
                resolution = job['options'].get("resolution", "Unknown")
                print(f"[DEBUG] Job: {job['display_name']}")
                print(f"[DEBUG] Orientation: {orientation}")
                print(f"[DEBUG] Resolution: {resolution}")
                
                self.build_ffmpeg_command_and_run(job, orientation)
                successful += 1; print(f"[SUCCESS] Job '{job['display_name']}' completed successfully.")
            except (VideoProcessingError, Exception) as e:
                failed += 1; print(f"\n[ERROR] Job failed for '{job['display_name']}': {e}")
        
        final_message = f"Processing Complete: {successful} successful, {failed} failed"
        print("\n" + "="*80 + "\n" + final_message)
        
        self.root.after(0, lambda: self.update_status(final_message))
        self.root.after(0, lambda: self.progress_bar.config(value=0))
        self.root.after(0, lambda: self.start_button.config(state="normal"))
        
        # Check if hibernate was requested
        if self.hibernate_when_done_var.get():
            print("\n[INFO] Hibernate requested. Hibernating system...")
            subprocess.run(["shutdown", "/h"], shell=True)

    def run_ffmpeg_command(self, cmd, duration=None, options=None, cwd=None):
        # Force dynamic progress + verbose diagnostics in console for easier debugging.
        prepared_cmd = list(cmd)
        insert_flags = []
        ffmpeg_threads = normalize_ffmpeg_threads((options or {}).get("ffmpeg_threads", DEFAULT_FFMPEG_THREADS))
        ffmpeg_priority = normalize_ffmpeg_priority((options or {}).get("ffmpeg_priority", DEFAULT_FFMPEG_PRIORITY))
        if "-threads" not in prepared_cmd:
            insert_flags.extend(["-threads", str(ffmpeg_threads)])
        if "-loglevel" not in prepared_cmd:
            insert_flags.extend(["-loglevel", "verbose"])
        if "-stats" not in prepared_cmd and "-nostats" not in prepared_cmd:
            insert_flags.append("-stats")
        if "-stats_period" not in prepared_cmd:
            insert_flags.extend(["-stats_period", "0.5"])
        if insert_flags:
            prepared_cmd = [prepared_cmd[0]] + insert_flags + prepared_cmd[1:]

        print("Running FFmpeg command:")
        print(" ".join(f'"{c}"' if " " in c else c for c in prepared_cmd))
        print(f"[INFO] FFmpeg CPU settings: threads={ffmpeg_threads}, priority={ffmpeg_priority}")
        return safe_ffmpeg_execution(prepared_cmd, "video encoding", duration, self.update_progress, priority=ffmpeg_priority, cwd=cwd)

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

    def measure_loudness(self, file_path, options=None):
        """Measures the loudness of the output file and saves it to an enhanced JSON file."""
        print(f"--- Measuring loudness: {os.path.basename(file_path)} ---")
        try:
            # -vn -sn -dn to ignore video/subs/data and speed up the pass
            cmd = [FFMPEG_CMD, "-i", file_path, "-vn", "-sn", "-dn", "-af", "loudnorm=print_format=json", "-f", "null", "-"]
            debug_print("Loudness command:", " ".join(cmd))
            
            result = subprocess.run(cmd, capture_output=True, text=True, env=env)
            output = (result.stdout or "") + (result.stderr or "")
            
            json_match = re.search(r'\{[\s\S]*?\}', output)
            if json_match:
                raw_data = json.loads(json_match.group(0))
                
                # Extract the actual measurements (FFmpeg labels them as 'input' because they are input to the loudnorm filter)
                measured_i = float(raw_data.get('input_i', 0))
                measured_tp = float(raw_data.get('input_tp', 0))
                measured_lra = float(raw_data.get('input_lra', 0))
                
                yt_target = -14.0
                diff = measured_i - yt_target
                
                # Create a more human-readable dictionary
                enhanced_data = {
                    "__INFO__": "This JSON contains loudness data measured from the output file.",
                    "actual_integrated_loudness_lufs": f"{measured_i:.2f}",
                    "actual_true_peak_db": f"{measured_tp:.2f}",
                    "actual_loudness_range_lra": f"{measured_lra:.2f}",
                    "youtube_target_lufs": f"{yt_target:.1f}",
                    "status_vs_youtube": f"{abs(diff):.2f}dB {'louder' if diff > 0 else 'quieter'} than YouTube standard",
                    "raw_ffmpeg_output": raw_data
                }
                
                json_path = f"{file_path}.loudness.json"
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(enhanced_data, f, indent=4)
                
                print(f"[SUCCESS] Enhanced loudness report saved to: {os.path.basename(json_path)}")
                print(f"          Integrated: {measured_i:.2f} LUFS | Status: {enhanced_data['status_vs_youtube']}")
            else:
                print("[WARN] Could not find JSON loudness data in FFmpeg output.")
        except Exception as e:
            print(f"[ERROR] Loudness measurement failed: {e}")

    def add_files(self):
        files = filedialog.askopenfilenames(filetypes=[("Video Files", "*.mp4;*.mkv;*.avi;*.mov;*.webm;*.flv;*.wmv"), ("All Files", "*.*")])
        if files: self.process_added_files(files)

    def handle_file_drop(self, event):
        files = self.root.tk.splitlist(event.data);
        if files: self.process_added_files(files)

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

    def select_jobs_by_current_preset(self):
        target_preset = self.current_preset_var.get()
        if not target_preset: return
        
        self.job_listbox.selection_clear(0, tk.END)
        count = 0
        for i, job in enumerate(self.processing_jobs):
            if job.get('preset_name') == target_preset:
                self.job_listbox.selection_set(i)
                count += 1
        
        self.on_input_file_select(None)
        if count: self.update_status(f"Selected {count} jobs with preset '{target_preset}'")
        else: self.update_status(f"No jobs found with preset '{target_preset}'")

    def invert_selection(self):
        selected_indices = self.job_listbox.curselection()
        for i in range(self.job_listbox.size()):
            if i in selected_indices: self.job_listbox.selection_clear(i)
            else: self.job_listbox.selection_set(i)
        self.on_input_file_select(None)

    def toggle_fruc_fps(self): self.fruc_fps_entry.config(state="normal" if self.fruc_var.get() else "disabled")

if __name__ == "__main__":
    atexit.register(cleanup_tracked_temp_files)
    # Register the Ctrl+C handler
    signal.signal(signal.SIGINT, handle_sigint)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, handle_sigint)

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
    else: 
        supported_exts = {'.mp4', '.mkv', '.mov', '.avi', '.webm', '.flv', '.wmv'}
        print(f"[INFO] Scanning {os.getcwd()} and subdirectories...")
        for root_dir, _, filenames in os.walk(os.getcwd()):
            for filename in filenames:
                if os.path.splitext(filename)[1].lower() in supported_exts:
                    initial_files.append(os.path.join(root_dir, filename))
        print(f"[INFO] Found {len(initial_files)} files.")
        
    app = VideoProcessorApp(root, sorted(list(set(initial_files))), args.output_mode)

    root.mainloop()








