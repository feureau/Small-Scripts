#!/usr/bin/env python3
"""
Generate DaVinci Resolve compliant Proxy files.
Fixed: 
- Implemented mathematically safe resolution scaling to prevent odd-integer format crashes.
- Resolved token parsing failures for pipe-delimited custom user patterns.
- Added absolute validation on audio stream channels before executing channel mapping parameters.
- Standardized error redirection across all process communication pipelines.
- Added Resolve-compliant H.264 proxy with NVIDIA NVENC auto-detection and libx264 fallback.
- Added AAC-MF (Windows Media Foundation) auto-detection with native AAC fallback.
- Bypassed fnmatch wildcard interpretation for exact, literal filenames (fixes bracket [] bugs).
- Changed input pattern to use the -i / --input flag.
- Added top-level variable block for easy default format switching (Video, Audio, Quality).
- Added dynamic scale multiplier variable with dynamic math bounding.
- Added a pre-validation check to skip files without a video stream.
"""

import sys
import subprocess
import os
import argparse
import fnmatch

# ==========================================
# USER CONFIGURATION
# ==========================================
# Set your preferred default proxy format here. 
# Options: "h264", "prores", or "dnxhr"
DEFAULT_FORMAT = "h264"

# Set your default resolution downscale multiplier.
# Example: 0.5 = Half resolution, 0.25 = Quarter resolution, 1.0 = Original resolution
DEFAULT_SCALE_MULTIPLIER = 0.5

# Default file search pattern if no -i is provided
DEFAULT_PATTERN = "*.[Mm][Pp]4|*.[Mm][Kk][Vv]|*.[Aa][Vv][Ii]|*.[Mm][Oo][Vv]|*.[Ww][Ee][Bb][Mm]|*.[Tt][Ss]"
# ==========================================

def parse_arguments():
    # Automatically route ideal settings based on the user's DEFAULT_FORMAT choice above
    if DEFAULT_FORMAT.lower() == "h264":
        def_codec = "h264"
        def_audio = "aac"
        def_qscale = 22
    elif DEFAULT_FORMAT.lower() == "dnxhr":
        def_codec = "dnxhr"
        def_audio = "pcm"
        def_qscale = 10
    else:  # prores
        def_codec = "prores"
        def_audio = "pcm"
        def_qscale = 10

    parser = argparse.ArgumentParser(description="Generate DaVinci Resolve compliant Proxy files.")
    parser.add_argument("input", nargs="?", default=None,
                        help="Input file or wildcard pattern (e.g. *.mp4). Default searches all videos.")
    parser.add_argument("-i", "--input", dest="input_flag", default=None, metavar="INPUT",
                        help="Input file or wildcard pattern (alternative to positional argument).")
    parser.add_argument("--codec", choices=["dnxhr", "prores", "h264"], default=def_codec,
                        help=f"Proxy codec. Default: {def_codec}")
    parser.add_argument("-s", "--scale", type=float, default=DEFAULT_SCALE_MULTIPLIER,
                        help=f"Resolution multiplier (e.g. 0.5 for half). Default: {DEFAULT_SCALE_MULTIPLIER}")
    parser.add_argument("-p", "--profile", choices=["proxy","lt","standard","hq","4444","4444xq"],
                        default="proxy", help="ProRes profile")
    parser.add_argument("-q", "--qscale", type=int, default=def_qscale,
                        help=f"ProRes quality (higher=smaller) or H.264 CRF/CQ. Default: {def_qscale}")
    parser.add_argument("-a", "--audio", choices=["pcm","copy","aac"], default=def_audio,
                        help=f"Audio codec. Default: {def_audio}")
    parser.add_argument("--slow", action="store_true", help="Disable hardware acceleration.")
    parser.add_argument("--no-scale", action="store_true", help="Keep exact original resolution (bypasses multiplier entirely).")
    
    args = parser.parse_args()
    args.input = args.input or args.input_flag or DEFAULT_PATTERN
    return args

def is_nvenc_available():
    """
    Runs a microscopic test encode to verify if h264_nvenc is compiled 
    AND functional (checking for active NVIDIA hardware/drivers).
    """
    try:
        cmd = [
            "ffmpeg", "-v", "error", 
            "-f", "lavfi", "-i", "color=black:s=16x16:d=0.1", 
            "-c:v", "h264_nvenc", 
            "-f", "null", "-"
        ]
        result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return result.returncode == 0
    except Exception:
        return False

def is_aac_mf_available():
    """
    Checks if Windows Media Foundation AAC encoder is available and working.
    Defaults to False on non-Windows platforms.
    """
    if os.name != 'nt':
        return False
    try:
        cmd = [
            "ffmpeg", "-v", "error", 
            "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", 
            "-t", "0.1",
            "-c:a", "aac_mf", 
            "-f", "null", "-"
        ]
        result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return result.returncode == 0
    except Exception:
        return False

def has_video_stream(filepath):
    """
    Checks if the targeted file contains a valid video stream track.
    This prevents FFmpeg failures on subtitle-only Matroska files.
    """
    try:
        cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0",
               "-show_entries", "stream=codec_type",
               "-of", "default=noprint_wrappers=1:nokey=1", filepath]
        out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL).strip()
        return out == "video"
    except Exception:
        return False

def extract_timecode(filepath):
    queries = [
        ["-select_streams", "d", "-show_entries", "stream_tags=timecode"],
        ["-select_streams", "v", "-show_entries", "stream_tags=timecode"],
        ["-show_entries", "format_tags=timecode"]
    ]
    for query in queries:
        try:
            cmd = ["ffprobe", "-v", "error"] + query + [
                "-of", "default=noprint_wrappers=1:nokey=1", filepath
            ]
            out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL).strip()
            if out:
                return out
        except Exception:
            pass
    return None

def get_audio_info(filepath):
    try:
        cmd = ["ffprobe", "-v", "error", "-select_streams", "a:0",
               "-show_entries", "stream=channels,channel_layout",
               "-of", "csv=p=0", filepath]
        out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL).strip()
        if not out:
            return None, None
        parts = out.split(",")
        channels = parts[0].strip() if len(parts) > 0 else None
        layout = parts[1].strip() if len(parts) > 1 else "unknown"
        return channels, layout
    except Exception:
        return None, None

def get_frame_rate(filepath):
    try:
        cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0",
               "-show_entries", "stream=r_frame_rate",
               "-of", "default=noprint_wrappers=1:nokey=1", filepath]
        out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL).strip()
        if '/' in out:
            num, den = map(int, out.split('/'))
            return num / den if den else None
        return float(out)
    except Exception:
        return None

def to_dropframe_tc(tc_str, fps):
    if not tc_str or fps is None:
        return tc_str
    if (abs(fps - 29.97) < 0.1 or abs(fps - 59.94) < 0.1) and ':' in tc_str and ';' not in tc_str:
        return tc_str.replace(':', ';')
    return tc_str

def find_video_files_recursive(base_dir, pattern_str):
    # Bypass wildcard parsing if the exact literal file exists (fixes [] brackets issue)
    if os.path.isfile(pattern_str):
        return [os.path.abspath(pattern_str)]
    exact_path = os.path.join(base_dir, pattern_str)
    if os.path.isfile(exact_path):
        return [os.path.abspath(exact_path)]

    # Otherwise run wildcard pattern matching
    found = []
    skip_dirs = {"proxy", "input", "output"}
    patterns = [p.strip() for p in pattern_str.split("|") if p.strip()]
    
    for dirpath, dirnames, filenames in os.walk(base_dir):
        dirnames[:] = [d for d in dirnames if d.lower() not in skip_dirs]
        for fname in filenames:
            for pattern in patterns:
                if fnmatch.fnmatch(fname, pattern):
                    found.append(os.path.join(dirpath, fname))
                    break
    return found

def has_tmcd_track(filepath):
    try:
        cmd = ["ffprobe", "-v", "error", "-select_streams", "d",
               "-show_entries", "stream=codec_tag_string",
               "-of", "default=noprint_wrappers=1:nokey=1", filepath]
        out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL).strip()
        return "tmcd" in out
    except Exception:
        return False

def main():
    args = parse_arguments()
    profile_map = {"proxy":"0","lt":"1","standard":"2","hq":"3","4444":"4","4444xq":"5"}
    
    # args.input replaces the old args.pattern
    files = find_video_files_recursive(os.getcwd(), args.input)
    if not files:
        print("No files found.")
        sys.exit(1)

    # Hardware detection for H.264 
    use_nvenc = False
    if args.codec == "h264":
        print("Detecting video hardware encoding capabilities...")
        use_nvenc = is_nvenc_available()
        if use_nvenc:
            print("🚀 NVIDIA GPU detected! Using hardware encoder (h264_nvenc).")
        else:
            print("💻 No compatible NVIDIA GPU found. Falling back to software encoder (libx264).")

    # Hardware detection for AAC
    use_aac_mf = False
    if args.audio == "aac":
        print("Detecting AAC audio encoding capabilities...")
        use_aac_mf = is_aac_mf_available()
        if use_aac_mf:
            print("🎵 Windows Media Foundation detected! Using AAC-MF encoder (aac_mf).")
        else:
            print("🎵 Using native FFmpeg AAC encoder (aac).")

    for file in sorted(files):
        # Pre-Validation Check: Skip if file doesn't actually have video (like subtitle mkv files)
        if not has_video_stream(file):
            continue

        print(f"\nProcessing: {file}")
        file_dir = os.path.dirname(file)
        base = os.path.splitext(os.path.basename(file))[0]
        output_dir = os.path.join(file_dir, "Proxy")
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, base + ".mov")

        # Timecode extraction and normalization
        tc = extract_timecode(file)
        fps = get_frame_rate(file)
        tc = to_dropframe_tc(tc, fps)

        # Audio stream evaluation and configuration routing
        aud_channels, aud_layout = get_audio_info(file)
        if aud_channels and aud_channels.isdigit() and int(aud_channels) > 0:
            is_sony = aud_layout and aud_layout.lower() in ["unknown", "", "null"]
            safe_layout = "stereo" if is_sony else (aud_layout or "stereo")
            if is_sony or args.audio == "pcm":
                audio_args = ["-map", "0:a?", "-c:a", "pcm_s16le", "-ch_layout", safe_layout]
            elif args.audio == "copy":
                audio_args = ["-map", "0:a?", "-c:a", "copy"]
            else:
                aac_codec = "aac_mf" if use_aac_mf else "aac"
                audio_args = ["-map", "0:a?", "-c:a", aac_codec, "-b:a", "640k", "-ch_layout", safe_layout]
        else:
            audio_args = ["-an"]

        # Base execution command initialization
        command = ["ffmpeg", "-y"]
        if not args.slow and not tc:
            command.extend(["-hwaccel", "auto"])

        command.extend(["-i", file, "-map", "0:v:0"])

        # Dynamically scaled and mathematically bounded macroblock filtering (divisible by 2)
        if not args.no_scale:
            command.extend(["-vf", f"scale=2*trunc(iw*{args.scale}/2):2*trunc(ih*{args.scale}/2)"])

        # Video encoder specification setup
        if args.codec == "dnxhr":
            command.extend([
                "-c:v", "dnxhd", "-profile:v", "dnxhr_lb", "-pix_fmt", "yuv422p",
                "-color_range", "tv", "-color_primaries", "bt709",
                "-color_trc", "bt709", "-colorspace", "bt709"
            ])
            if tc:
                command.extend(["-timecode", tc, "-metadata:s:v:0", f"timecode={tc}"])
            command.extend(["-write_tmcd", "1", "-movflags", "+write_colr"])
            
        elif args.codec == "h264":
            # If default ProRes qscale (10) slips through via CLI flags, remap to CRF 22 safely
            crf = 22 if args.qscale == 10 else args.qscale
            
            if use_nvenc:
                # NVENC uses -cq for Constant Quality. -b:v 0 allows unrestricted VBR up to target quality
                command.extend([
                    "-c:v", "h264_nvenc", "-preset", "p4", "-profile:v", "main", "-level", "4.0",
                    "-pix_fmt", "yuv420p", "-cq", str(crf), "-b:v", "0",
                    "-color_range", "tv", "-color_primaries", "bt709",
                    "-color_trc", "bt709", "-colorspace", "bt709",
                    "-tag:v", "avc1"
                ])
            else:
                # libx264 software fallback
                command.extend([
                    "-c:v", "libx264", "-profile:v", "main", "-level", "4.0",
                    "-pix_fmt", "yuv420p", "-refs", "4", "-crf", str(crf),
                    "-color_range", "tv", "-color_primaries", "bt709",
                    "-color_trc", "bt709", "-colorspace", "bt709",
                    "-tag:v", "avc1"
                ])

            if tc:
                command.extend(["-timecode", tc, "-metadata:s:v:0", f"timecode={tc}"])
            command.extend(["-write_tmcd", "1", "-movflags", "+write_colr"])

        else:  # prores
            command.extend([
                "-c:v", "prores_ks", "-profile:v", profile_map[args.profile],
                "-qscale:v", str(args.qscale), "-vendor", "ap10",
                "-color_range", "tv", "-color_primaries", "bt709",
                "-color_trc", "bt709", "-colorspace", "bt709"
            ])
            if args.profile not in ["4444","4444xq"]:
                command.extend(["-pix_fmt", "yuv422p10le"])
            if tc:
                command.extend(["-timecode", tc, "-metadata:s:v:0", f"timecode={tc}"])
            command.extend(["-write_tmcd", "1", "-movflags", "+write_colr"])

        # Append audio arguments and target path output
        command.extend(audio_args)
        command.append(output_file)

        # Subprocess execution and evaluation loop
        result = subprocess.run(command)
        if result.returncode != 0:
            print(f"Failed: {file}")
            continue

        # Verification of timecode track signature
        if has_tmcd_track(output_file):
            print(f"✅ Created: {output_file} (tmcd track present)")
        else:
            print(f"❌ WARNING: {output_file} has no tmcd track! Resolve will NOT recognise it.")
            if args.codec in ["dnxhr", "h264"]:
                print("   Timecode write failed. Check your source file or re-run with --codec prores.")

if __name__ == "__main__":
    main()