#!/usr/bin/env python3
"""
Generate DaVinci Resolve compliant Proxy files.
Fixed: 
- Implemented mathematically safe resolution scaling to prevent odd-integer format crashes.
- Resolved token parsing failures for pipe-delimited custom user patterns.
- Added absolute validation on audio stream channels before executing channel mapping parameters.
- Standardized error redirection across all process communication pipelines.
"""

import sys
import subprocess
import os
import argparse
import fnmatch

DEFAULT_PATTERN = "*.[Mm][Pp]4|*.[Mm][Kk][Vv]|*.[Aa][Vv][Ii]|*.[Mm][Oo][Vv]|*.[Ww][Ee][Bb][Mm]|*.[Tt][Ss]"

def parse_arguments():
    parser = argparse.ArgumentParser(description="Generate DaVinci Resolve compliant Proxy files.")
    parser.add_argument("pattern", nargs="?", default=DEFAULT_PATTERN)
    parser.add_argument("--codec", choices=["dnxhr", "prores"], default="prores",
                        help="Proxy codec. Default: prores (most reliable).")
    parser.add_argument("-p", "--profile", choices=["proxy","lt","standard","hq","4444","4444xq"],
                        default="proxy", help="ProRes profile")
    parser.add_argument("-q", "--qscale", type=int, default=10,
                        help="ProRes quality (higher = smaller).")
    parser.add_argument("-a", "--audio", choices=["pcm","copy","aac"], default="pcm")
    parser.add_argument("--slow", action="store_true", help="Disable hardware acceleration.")
    parser.add_argument("--no-scale", action="store_true", help="Keep original resolution (no scaling).")
    return parser.parse_args()

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
    files = find_video_files_recursive(os.getcwd(), args.pattern)
    if not files:
        print("No files found.")
        sys.exit(1)

    for file in sorted(files):
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
                audio_args = ["-map", "0:a?", "-c:a", "aac", "-b:a", "640k", "-ch_layout", safe_layout]
        else:
            audio_args = ["-an"]

        # Base execution command initialization
        command = ["ffmpeg", "-y"]
        if not args.slow and not tc:
            command.extend(["-hwaccel", "auto"])

        command.extend(["-i", file, "-map", "0:v:0"])

        # Mathematically bounded macroblock filtering (divisible by 2)
        if not args.no_scale:
            command.extend(["-vf", "scale=2*trunc(iw/4):2*trunc(ih/4)"])

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
            if args.codec == "dnxhr":
                print("   DNxHR failed to write timecode. Please re-run with --codec prores.")

if __name__ == "__main__":
    main()