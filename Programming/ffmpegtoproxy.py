#!/usr/bin/env python3
"""
Generate DaVinci Resolve compliant Proxy files.
Fixes applied in this version:
- Fixed drop-frame timecode conversion (only last colon replaced).
- Fixed --slow to properly disable NVENC hardware encoding.
- Fixed per-codec qscale defaults.
- Changed default audio to PCM for .mov compatibility.
- Removed forced BT.709 color tagging; now copies source color metadata.
- Replaced -ch_layout with -ac for better compatibility.
- Removed hardcoded H.264 level 4.0 to support 4K proxies.
- Added validation for --scale > 0.
- Added FFmpeg/FFprobe existence check.
- Only warn about missing tmcd track when source actually had timecode.

NEW Resolve-compatibility fixes:
- Hard-fail (and delete output) if source has timecode but proxy lacks tmcd track.
- Verify output timecode matches source timecode.
- Detect variable frame rate (VFR) sources and force constant frame rate on the proxy.
- Match proxy container extension to source type (MOV for ProRes/DNxHR, MP4 for H.264).
- Log the resolved timecode, fps, and container so failures are diagnosable.
"""

import sys
import subprocess
import os
import argparse
import fnmatch
import shutil

# ==========================================
# USER CONFIGURATION
# ==========================================
# Set your preferred default proxy format here. 
# Options: "h264", "prores", or "dnxhr"
DEFAULT_FORMAT = "prores"

# Set your default resolution downscale multiplier.
# Example: 0.5 = Half resolution, 0.25 = Quarter resolution, 1.0 = Original resolution
DEFAULT_SCALE_MULTIPLIER = 0.5

# Default file search pattern if no -i is provided
DEFAULT_PATTERN = "*.[Mm][Pp]4|*.[Mm][Kk][Vv]|*.[Aa][Vv][Ii]|*.[Mm][Oo][Vv]|*.[Ww][Ee][Bb][Mm]|*.[Tt][Ss]"

# If the source has a timecode and the proxy fails to embed a tmcd track,
# delete the proxy so Resolve doesn't try to use an unusable file.
HARD_FAIL_ON_MISSING_TMCD = True

# Force constant frame rate on the proxy when the source is detected as VFR.
FORCE_CFR_ON_VFR = True
# ==========================================

def parse_arguments():
    if DEFAULT_FORMAT.lower() == "h264":
        def_codec = "h264"
    elif DEFAULT_FORMAT.lower() == "dnxhr":
        def_codec = "dnxhr"
    else:
        def_codec = "prores"

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
    parser.add_argument("-q", "--qscale", type=int, default=None,
                        help="ProRes quality (higher=smaller) or H.264 CRF/CQ. Default: 10 for ProRes/DNxHR, 22 for H.264")
    parser.add_argument("-a", "--audio", choices=["pcm","copy","aac"], default="pcm",
                        help="Audio codec. Default: pcm")
    parser.add_argument("--slow", action="store_true", help="Disable hardware acceleration.")
    parser.add_argument("--no-scale", action="store_true", help="Keep exact original resolution (bypasses multiplier entirely).")
    
    args = parser.parse_args()
    args.input = args.input or args.input_flag or DEFAULT_PATTERN

    if args.qscale is None:
        if args.codec == "h264":
            args.qscale = 22
        elif args.codec == "dnxhr":
            args.qscale = 10
        else:  # prores
            args.qscale = 10

    if args.scale <= 0:
        parser.error("--scale must be greater than 0")

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
    """
    Returns (r_frame_rate, avg_frame_rate) as floats.
    r_frame_rate is the nominal base rate; avg_frame_rate is the real average.
    If they diverge significantly, the source is likely VFR.
    """
    try:
        cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0",
               "-show_entries", "stream=r_frame_rate,avg_frame_rate",
               "-of", "default=noprint_wrappers=1:nokey=0", filepath]
        out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL).strip()
        r_rate = None
        avg_rate = None
        for line in out.splitlines():
            if line.startswith("r_frame_rate="):
                val = line.split("=", 1)[1]
                if '/' in val:
                    num, den = map(int, val.split('/'))
                    r_rate = num / den if den else None
                else:
                    r_rate = float(val)
            elif line.startswith("avg_frame_rate="):
                val = line.split("=", 1)[1]
                if '/' in val:
                    num, den = map(int, val.split('/'))
                    avg_rate = num / den if den else None
                else:
                    avg_rate = float(val)
        return r_rate, avg_rate
    except Exception:
        return None, None

def is_vfr(r_rate, avg_rate):
    """
    Returns True if the source appears to be variable frame rate.
    Uses a 2% tolerance between nominal and average frame rate.
    """
    if r_rate is None or avg_rate is None or avg_rate == 0:
        return False
    return abs(r_rate - avg_rate) / avg_rate > 0.02

def get_color_info(filepath):
    """Probe source color metadata to copy into the proxy."""
    try:
        cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0",
               "-show_entries", "stream=color_range,color_primaries,color_trc,colorspace",
               "-of", "default=noprint_wrappers=1:nokey=0", filepath]
        out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL).strip()
        info = {}
        for line in out.splitlines():
            if '=' in line:
                key, val = line.split('=', 1)
                if val and val != 'unknown':
                    info[key] = val
        return info
    except Exception:
        return {}

def to_dropframe_tc(tc_str, fps):
    if not tc_str or fps is None:
        return tc_str
    if (abs(fps - 29.97) < 0.1 or abs(fps - 59.94) < 0.1) and ':' in tc_str and ';' not in tc_str:
        # Only replace the last colon with a semicolon for drop-frame
        head, frames = tc_str.rsplit(':', 1)
        return f"{head};{frames}"
    return tc_str

def find_video_files_recursive(base_dir, pattern_str):
    if os.path.isfile(pattern_str):
        return [os.path.abspath(pattern_str)]
    exact_path = os.path.join(base_dir, pattern_str)
    if os.path.isfile(exact_path):
        return [os.path.abspath(exact_path)]

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
    """
    Returns (has_track, timecode_value_or_None).
    Checks for a real QuickTime tmcd track, which is what Resolve reads.
    """
    try:
        cmd = ["ffprobe", "-v", "error", "-select_streams", "d",
               "-show_entries", "stream=codec_tag_string:stream_tags=timecode",
               "-of", "default=noprint_wrappers=1:nokey=0", filepath]
        out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL).strip()
        has_track = "tmcd" in out
        tc_value = None
        for line in out.splitlines():
            if line.startswith("TAG:timecode="):
                tc_value = line.split("=", 1)[1].strip()
        return has_track, tc_value
    except Exception:
        return False, None

def pick_output_extension(codec):
    """
    Match the proxy container to what Resolve expects for the codec family.
    ProRes and DNxHR are MOV-native. H.264 works best as MP4 with avc1 tag.
    """
    if codec == "h264":
        return ".mp4"
    return ".mov"

def main():
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        print("Error: ffmpeg and ffprobe must be installed and in PATH.")
        sys.exit(1)

    args = parse_arguments()
    profile_map = {"proxy":"0","lt":"1","standard":"2","hq":"3","4444":"4","4444xq":"5"}
    
    files = find_video_files_recursive(os.getcwd(), args.input)
    if not files:
        print("No files found.")
        sys.exit(1)

    # Hardware detection for H.264 
    use_nvenc = False
    if args.codec == "h264":
        if args.slow:
            print("🚫 Hardware acceleration disabled by --slow. Using software encoder.")
        else:
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

    out_ext = pick_output_extension(args.codec)

    for file in sorted(files):
        if not has_video_stream(file):
            continue

        print(f"\nProcessing: {file}")
        file_dir = os.path.dirname(file)
        base = os.path.splitext(os.path.basename(file))[0]
        output_dir = os.path.join(file_dir, "Proxy")
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, base + out_ext)

        # Timecode extraction and normalization
        tc = extract_timecode(file)
        r_rate, avg_rate = get_frame_rate(file)
        fps = r_rate  # nominal fps used for timecode drop-frame decision
        tc = to_dropframe_tc(tc, fps)
        vfr = is_vfr(r_rate, avg_rate)

        # Report resolved media properties for diagnosis
        print(f"  ↳ fps: r={r_rate} avg={avg_rate}  VFR={vfr}  TC={tc}")

        # Color metadata from source
        color_info = get_color_info(file)
        color_args = []
        if 'color_range' in color_info:
            color_args.extend(["-color_range", color_info['color_range']])
        if 'color_primaries' in color_info:
            color_args.extend(["-color_primaries", color_info['color_primaries']])
        if 'color_trc' in color_info:
            color_args.extend(["-color_trc", color_info['color_trc']])
        if 'colorspace' in color_info:
            color_args.extend(["-colorspace", color_info['colorspace']])

        # Audio stream evaluation and configuration routing
        aud_channels, aud_layout = get_audio_info(file)
        if aud_channels and aud_channels.isdigit() and int(aud_channels) > 0:
            if args.audio == "copy":
                audio_args = ["-map", "0:a?", "-c:a", "copy"]
            else:
                if args.audio == "pcm":
                    audio_args = ["-map", "0:a?", "-c:a", "pcm_s16le", "-ac", aud_channels]
                else:
                    aac_codec = "aac_mf" if use_aac_mf else "aac"
                    audio_args = ["-map", "0:a?", "-c:a", aac_codec, "-b:a", "640k", "-ac", aud_channels]
        else:
            audio_args = ["-an"]

        # Base execution command
        command = ["ffmpeg", "-y"]
        if not args.slow and not tc:
            command.extend(["-hwaccel", "auto"])

        command.extend(["-i", file, "-map", "0:v:0"])

        # Scale filter
        if not args.no_scale:
            command.extend(["-vf", f"scale=2*trunc(iw*{args.scale}/2):2*trunc(ih*{args.scale}/2)"])

        # Force constant frame rate for VFR sources so Resolve can link the proxy
        if vfr and FORCE_CFR_ON_VFR and avg_rate:
            command.extend(["-r", f"{avg_rate:.6f}"])

        # Video encoder setup
        if args.codec == "dnxhr":
            command.extend([
                "-c:v", "dnxhd", "-profile:v", "dnxhr_lb", "-pix_fmt", "yuv422p"
            ])
            command.extend(color_args)
            if tc:
                command.extend(["-timecode", tc, "-metadata:s:v:0", f"timecode={tc}"])
            command.extend(["-write_tmcd", "1", "-movflags", "+write_colr"])
            
        elif args.codec == "h264":
            if use_nvenc:
                command.extend([
                    "-c:v", "h264_nvenc", "-preset", "p4", "-profile:v", "main",
                    "-pix_fmt", "yuv420p", "-cq", str(args.qscale), "-b:v", "0",
                    "-tag:v", "avc1"
                ])
            else:
                command.extend([
                    "-c:v", "libx264", "-profile:v", "main",
                    "-pix_fmt", "yuv420p", "-refs", "4", "-crf", str(args.qscale),
                    "-tag:v", "avc1"
                ])
            command.extend(color_args)
            if tc:
                command.extend(["-timecode", tc, "-metadata:s:v:0", f"timecode={tc}"])
            command.extend(["-write_tmcd", "1", "-movflags", "+write_colr"])

        else:  # prores
            command.extend([
                "-c:v", "prores_ks", "-profile:v", profile_map[args.profile],
                "-qscale:v", str(args.qscale), "-vendor", "ap10"
            ])
            if args.profile not in ["4444","4444xq"]:
                command.extend(["-pix_fmt", "yuv422p10le"])
            command.extend(color_args)
            if tc:
                command.extend(["-timecode", tc, "-metadata:s:v:0", f"timecode={tc}"])
            command.extend(["-write_tmcd", "1", "-movflags", "+write_colr"])

        command.extend(audio_args)
        command.append(output_file)

        result = subprocess.run(command)
        if result.returncode != 0:
            print(f"❌ Failed: {file}")
            continue

        # Post-encode verification
        out_has_tmcd, out_tc = has_tmcd_track(output_file)

        if tc:
            # Source had timecode — proxy must have a tmcd track and matching TC
            if not out_has_tmcd:
                print(f"❌ INCOMPATIBLE: {output_file} has no tmcd track (source TC = {tc}).")
                if HARD_FAIL_ON_MISSING_TMCD:
                    try:
                        os.remove(output_file)
                        print("   Output deleted — Resolve would not link it.")
                    except OSError:
                        pass
                continue

            if out_tc and out_tc != tc:
                print(f"❌ INCOMPATIBLE: proxy TC ({out_tc}) does not match source TC ({tc}).")
                try:
                    os.remove(output_file)
                    print("   Output deleted — Resolve would not link it.")
                except OSError:
                    pass
                continue

            print(f"✅ Created: {output_file}  (tmcd = {out_tc or tc})")
        else:
            # Source had no timecode — proxy linking relies on filename + fps overlap
            if out_has_tmcd:
                print(f"✅ Created: {output_file}  (tmcd present, source had none)")
            else:
                print(f"✅ Created: {output_file}  (no timecode in source, tmcd not expected)")

if __name__ == "__main__":
    main()