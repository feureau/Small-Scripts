#!/usr/bin/env python3
"""
Convert video files to Apple ProRes in a MOV container.

- Fast Mode (GPU Decode + prores_aw) is enabled by default.
- Default profile is ProRes LT.
- Supports Auto-Cropping (--autocrop) to remove pillarbox/letterbox black bars.
- Supports Manual Cropping (--crop-res WIDTHxHEIGHT) to designate target pixel dimensions.
- Supports Output Scaling (--scale WIDTHxHEIGHT).
- Cross-platform audio fallback (aac_mf on Windows, native aac on Linux/macOS).
- Original files are moved safely into a folder named after their extension (e.g. 'MP4').
- Converted files are placed in a folder named after the format (e.g. 'ProRes_LT').
- Recursively searches subdirectories for common video formats.
"""

import sys
import subprocess
import os
import re
import argparse
import shutil
import fnmatch
from collections import Counter

# List of standard layout names as reported by "ffmpeg -layouts"
LAYOUTS = [
    "mono", "stereo", "2.1", "3.0", "3.0(back)", "4.0", "quad", "quad(side)",
    "3.1", "5.0", "5.0(side)", "4.1", "5.1", "5.1(side)", "6.0", "6.0(front)",
    "3.1.2", "hexagonal", "6.1", "6.1(back)", "6.1(front)", "7.0", "7.0(front)",
    "7.1", "7.1(wide)", "7.1(wide-side)", "5.1.2", "octagonal", "cube", "5.1.4",
    "7.1.2", "7.1.4", "7.2.3", "9.1.4", "hexadecagonal", "downmix", "22.2"
]

NAMED_LAYOUTS = {
    "mono": 1, "stereo": 2, "2.1": 3, "3.0": 3, "3.0(back)": 3, "4.0": 4,
    "quad": 4, "quad(side)": 4, "3.1": 4, "5.0": 5, "5.0(side)": 5, "4.1": 5,
    "5.1": 6, "5.1(side)": 6, "6.0": 6, "6.0(front)": 6, "3.1.2": 6,
    "hexagonal": 6, "6.1": 7, "6.1(back)": 7, "6.1(front)": 7, "7.0": 7,
    "7.0(front)": 7, "7.1": 8, "7.1(wide)": 8, "7.1(wide-side)": 8,
    "5.1.2": 8, "octagonal": 8, "cube": 8, "5.1.4": 10, "7.1.2": 10,
    "7.1.4": 10, "7.2.3": 12, "9.1.4": 14, "hexadecagonal": 16,
    "downmix": 2, "22.2": 24
}

def calculate_channel_count(layout: str) -> int:
    parts = layout.split('.')
    try:
        return sum(int(p) for p in parts)
    except ValueError:
        return NAMED_LAYOUTS.get(layout, 6)

def parse_crop_resolution(res_str: str) -> str:
    """
    Parses 'WIDTHxHEIGHT' or 'WIDTH:HEIGHT:X:Y' and ensures even dimensions.
    """
    s = res_str.strip().lower()
    if s.startswith("crop="):
        return s
    
    parts = re.split(r'[:x]', s)
    if len(parts) == 2:
        w, h = int(parts[0]), int(parts[1])
        w = w if w % 2 == 0 else w - 1
        h = h if h % 2 == 0 else h - 1
        return f"crop={w}:{h}"
    elif len(parts) == 4:
        w, h, x, y = int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])
        w = w if w % 2 == 0 else w - 1
        h = h if h % 2 == 0 else h - 1
        x = x if x % 2 == 0 else x - 1
        y = y if y % 2 == 0 else y - 1
        return f"crop={w}:{h}:{x}:{y}"
    else:
        raise argparse.ArgumentTypeError(
            f"Invalid crop resolution '{res_str}'. Expected WIDTHxHEIGHT (e.g. 1920x800) or W:H:X:Y."
        )

def parse_scale_resolution(res_str: str) -> str:
    """
    Parses 'WIDTHxHEIGHT' for scaling.
    """
    s = res_str.strip().lower()
    parts = re.split(r'[:x]', s)
    if len(parts) == 2:
        w, h = int(parts[0]), int(parts[1])
        w = w if w % 2 == 0 else w - 1
        h = h if h % 2 == 0 else h - 1
        return f"scale={w}:{h}"
    else:
        raise argparse.ArgumentTypeError(
            f"Invalid scale resolution '{res_str}'. Expected WIDTHxHEIGHT (e.g. 1920x1080)."
        )

def get_video_info(file_path: str):
    """
    Extracts duration (seconds) and dimensions (width, height) using FFmpeg.
    """
    cmd = ["ffmpeg", "-hide_banner", "-i", file_path]
    try:
        res = subprocess.run(
            cmd,
            stderr=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        stderr = res.stderr
    except Exception:
        return 0.0, None, None

    duration = 0.0
    dur_match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", stderr)
    if dur_match:
        h, m, s = dur_match.groups()
        duration = int(h) * 3600 + int(m) * 60 + float(s)

    dim_match = re.search(r"Stream #0:\d.*?Video:.*?,\s*(\d{2,5})x(\d{2,5})", stderr)
    width, height = None, None
    if dim_match:
        width = int(dim_match.group(1))
        height = int(dim_match.group(2))

    return duration, width, height

def detect_crop(file_path: str) -> str:
    """
    Detects black bars (letterboxing/pillarboxing) using cropdetect filter.
    Returns FFmpeg crop parameter (e.g. '1920:800:0:140') or None if full frame.
    """
    duration, orig_w, orig_h = get_video_info(file_path)

    # Seek past studio intros / logos (around 20% into the video if long enough)
    if duration > 60:
        seek_time = duration * 0.2
        sample_time = 10
    elif duration > 10:
        seek_time = duration * 0.1
        sample_time = min(5, duration - seek_time)
    else:
        seek_time = 0
        sample_time = 5

    cmd = ["ffmpeg", "-hide_banner"]
    if seek_time > 0:
        cmd.extend(["-ss", f"{seek_time:.2f}"])
    
    # cropdetect=limit:round:reset
    # limit=24 (black threshold), round=2 (even dims for ProRes 4:2:2), reset=1 (evaluate per-frame)
    cmd.extend([
        "-i", file_path,
        "-t", str(sample_time),
        "-vf", "cropdetect=24:2:1",
        "-an", "-sn",
        "-f", "null", "-"
    ])

    try:
        proc = subprocess.run(
            cmd,
            stderr=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
    except Exception as e:
        print(f"  [AutoCrop] Warning: Failed to probe for crop values: {e}")
        return None

    matches = re.findall(r"crop=(\d+:\d+:\d+:\d+)", proc.stderr)
    if not matches:
        return None

    # Filter out tiny/black boxes
    valid_crops = []
    for m in matches:
        w, h, x, y = map(int, m.split(":"))
        if w >= 64 and h >= 64:
            valid_crops.append(m)

    if not valid_crops:
        return None

    # Determine dominant aspect ratio via statistical mode
    most_common_crop, _ = Counter(valid_crops).most_common(1)[0]
    w, h, x, y = map(int, most_common_crop.split(":"))

    # If detected area is full frame, skip cropping
    if orig_w and orig_h and w == orig_w and h == orig_h and x == 0 and y == 0:
        return None

    return most_common_crop

def safe_move(src_path: str, dst_dir: str) -> str:
    """
    Moves file to destination directory without overwriting collisions.
    """
    os.makedirs(dst_dir, exist_ok=True)
    base, ext = os.path.splitext(os.path.basename(src_path))
    dest = os.path.join(dst_dir, os.path.basename(src_path))
    counter = 1
    while os.path.exists(dest):
        dest = os.path.join(dst_dir, f"{base}_{counter}{ext}")
        counter += 1
    shutil.move(src_path, dest)
    return dest

def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Convert video files to ProRes (.mov) with cropping, scaling, and flexible audio options.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "pattern", nargs='?',
        default="*.[Mm][Pp]4|*.[Mm][Kk][Vv]|*.[Aa][Vv][Ii]|*.[Mm][Oo][Vv]|*.[Ww][Ee][Bb][Mm]|*.[Tt][Ss]",
        help="Input file pattern (e.g., \"*.mkv\"). If not provided, searches for common video formats."
    )
    parser.add_argument(
        "-p", "--profile", choices=["proxy", "lt", "standard", "hq", "4444", "4444xq"],
        default="lt",
        help="ProRes profile to use. Default: lt\n"
             "  proxy    - ProRes 422 Proxy (Profile 0)\n"
             "  lt       - ProRes 422 LT (Profile 1)\n"
             "  standard - ProRes 422 (Profile 2)\n"
             "  hq       - ProRes 422 HQ (Profile 3)\n"
             "  4444     - ProRes 4444 (Profile 4)\n"
             "  4444xq   - ProRes 4444 XQ (Profile 5)"
    )
    parser.add_argument(
        "-a", "--audio", choices=["aac", "pcm"], default="aac",
        help="Audio format to use. Default: aac\n"
             "  aac - Compressed AAC at 640kbps\n"
             "  pcm - Uncompressed 24-bit PCM (Industry standard for ProRes)"
    )
    parser.add_argument(
        "--slow", action="store_true",
        help="Disable default Fast Mode. Forces CPU decoding and uses the slower 'prores_ks' encoder."
    )
    parser.add_argument(
        "-l", "--layout", default="5.1",
        help="Desired audio channel layout (default: 5.1)"
    )
    parser.add_argument(
        "-d", "--downmix", choices=["5.1", "6"], default="5.1",
        help="Downmix method: '5.1' (-ch_layout) or '6' (-ac). Default: 5.1"
    )

    # --- Cropping & Resolution Options ---
    crop_group = parser.add_mutually_exclusive_group()
    crop_group.add_argument(
        "--autocrop", action="store_true",
        help="Automatically detect and crop out letterbox / pillarbox black bars."
    )
    crop_group.add_argument(
        "--crop-res", "--crop", dest="crop_res", type=str, default=None,
        help="Manually crop image to specified resolution (WIDTHxHEIGHT, e.g. 1920x800).\n"
             "Centers the crop automatically. Can also accept WIDTHxHEIGHT:X:Y."
    )
    parser.add_argument(
        "--scale", "--resolution", dest="scale_res", type=str, default=None,
        help="Scale output to designated resolution (WIDTHxHEIGHT, e.g. 1920x1080)."
    )

    return parser.parse_args()

def find_video_files_recursive(base_dir, pattern):
    use_default = (pattern == "*.[Mm][Pp]4|*.[Mm][Kk][Vv]|*.[Aa][Vv][Ii]|*.[Mm][Oo][Vv]|*.[Ww][Ee][Bb][Mm]|*.[Tt][Ss]")
    found = []
    skip_exts = {'mp4', 'mkv', 'avi', 'mov', 'webm', 'ts', 'input', 'output'}

    for dirpath, dirnames, filenames in os.walk(base_dir):
        dirnames[:] = [
            d for d in dirnames 
            if d.lower() not in skip_exts and not d.lower().startswith('prores_')
        ]
        
        for fname in filenames:
            if use_default:
                if os.path.splitext(fname)[1].lower() in {f".{ext}" for ext in skip_exts}:
                    found.append(os.path.join(dirpath, fname))
            else:
                if fnmatch.fnmatch(fname, pattern):
                    found.append(os.path.join(dirpath, fname))

    return found

def main():
    args = parse_arguments()
    file_pattern = args.pattern
    desired_layout = args.layout
    downmix_method = args.downmix
    channels = calculate_channel_count(desired_layout)
    
    profile_map = {
        "proxy": "0", "lt": "1", "standard": "2", 
        "hq": "3", "4444": "4", "4444xq": "5"
    }
    prores_profile_num = profile_map[args.profile]

    # Pixel Format handling
    if args.profile in ["4444", "4444xq"]:
        pix_fmt_args = ["-pix_fmt", "yuv444p10le"]
    else:
        pix_fmt_args = ["-pix_fmt", "yuv422p10le"]

    # Fast Mode Logic
    is_fast = not args.slow
    video_encoder = "prores_ks"
    speed_mode = "High Quality (CPU Decode + prores_ks)"
    
    if is_fast:
        if args.profile in ["4444", "4444xq"]:
            speed_mode = "Mixed (GPU Decode + prores_ks for Alpha)"
        else:
            video_encoder = "prores_aw"
            speed_mode = "Fast (GPU Decode + prores_aw)"

    # Audio Logic
    if args.audio == "aac":
        if channels > 8:
            print(f"Error: Requested layout '{desired_layout}' implies {channels} channels, but AAC supports at most 8 channels.")
            sys.exit(1)
        # Windows uses aac_mf; macOS/Linux fall back to native aac
        audio_encoder = "aac_mf" if sys.platform == "win32" else "aac"
        audio_bitrate = "640k"
        audio_args = [
            "-map", "0:a?",
            "-c:a", audio_encoder,
            "-b:a", audio_bitrate
        ]
    else:
        audio_encoder = "pcm_s24le"
        audio_args = [
            "-map", "0:a?",
            "-c:a", audio_encoder
        ]

    print(f"Target Video Codec: Apple ProRes ({args.profile.upper()})")
    print(f"Speed Profile     : {speed_mode}")
    print(f"Desired Audio     : {desired_layout} => {channels} channel(s) ({audio_encoder.upper()})")
    if args.autocrop:
        print(f"Crop Setting      : Auto-detect (Remove pillarbox/letterbox)")
    elif args.crop_res:
        print(f"Crop Setting      : Manual ({args.crop_res})")
    if args.scale_res:
        print(f"Scale Setting     : Output scaled to ({args.scale_res})")

    base_dir = os.getcwd()
    files = find_video_files_recursive(base_dir, file_pattern)

    if not files:
        print(f"No files found matching: {file_pattern}")
        sys.exit(1)

    files.sort()
    print(f"\nFound {len(files)} file(s) across directory tree:")
    for f in files:
        print(f"  {os.path.relpath(f, base_dir)}")

    success_items = []
    failed_items = []

    for file in files:
        print(f"\nProcessing: {file}")

        file_dir = os.path.dirname(file)
        base, ext_with_dot = os.path.splitext(os.path.basename(file))
        ext = ext_with_dot.lstrip('.').upper() or "INPUT"
            
        prores_folder_name = f"ProRes_{args.profile.upper()}"
        input_dir = os.path.join(file_dir, ext)
        output_dir = os.path.join(file_dir, prores_folder_name)
        output_file = os.path.join(output_dir, base + ".mov")

        if downmix_method == "5.1":
            layout_args = ["-ch_layout", desired_layout]
        else:
            layout_args = ["-ac", str(channels)]

        # --- Video Filters Setup (Crop & Scale) ---
        vf_filters = []
        if args.autocrop:
            print("  Analyzing black bars...")
            detected = detect_crop(file)
            if detected:
                print(f"  Applying Auto-Crop: crop={detected}")
                vf_filters.append(f"crop={detected}")
            else:
                print("  No black bars detected (full frame). Skipping crop.")
        elif args.crop_res:
            crop_cmd = parse_crop_resolution(args.crop_res)
            print(f"  Applying Manual Crop: {crop_cmd}")
            vf_filters.append(crop_cmd)

        if args.scale_res:
            scale_cmd = parse_scale_resolution(args.scale_res)
            print(f"  Applying Scaling: {scale_cmd}")
            vf_filters.append(scale_cmd)

        # --- Build FFmpeg Command ---
        command = ["ffmpeg", "-y"]
        
        if is_fast:
            command.extend(["-hwaccel", "auto"])
            
        command.extend([
            "-i", file,
            "-map", "0:v:0",
            "-c:v", video_encoder,
            "-profile:v", prores_profile_num,
            "-vendor", "ap10",
        ])
        
        # Insert video filters if defined
        if vf_filters:
            command.extend(["-vf", ",".join(vf_filters)])

        command.extend(pix_fmt_args)
        command.extend(audio_args)
        command.extend(layout_args)
        command.append(output_file)

        print("Running command: " + " ".join(command))
        os.makedirs(output_dir, exist_ok=True)

        stderr_lines = []
        try:
            proc = subprocess.Popen(
                command,
                stderr=subprocess.PIPE,
                stdout=subprocess.DEVNULL,   
                text=True,
                encoding="utf-8",
                errors="replace"
            )
            for line in proc.stderr:
                sys.stderr.write(line)       
                sys.stderr.flush()
                stderr_lines.append(line)    
            proc.wait()
        except Exception as e:
            print(f"Unexpected error running ffmpeg: {e}")
            failed_items.append({
                "source": file,
                "status": "script_error",
                "reason": str(e),
            })
            continue

        if proc.returncode == 0:
            print(f"Successfully created: {output_file}")
            moved_path = safe_move(file, input_dir)
            print(f"Moved original file to: {moved_path}")
            success_items.append({
                "source": file,
                "output": output_file,
                "status": "ok",
            })
        else:
            print(f"Error processing {file}: ffmpeg exited with code {proc.returncode}")
            stderr_output = "".join(stderr_lines).strip() or "No stderr captured"
            failed_items.append({
                "source": file,
                "status": "ffmpeg_error",
                "returncode": proc.returncode,
                "reason": stderr_output,
            })

    print("\n" + "=" * 72)
    print("Processing summary")
    print("=" * 72)
    print(f"Total files discovered : {len(files)}")
    print(f"Successful conversions : {len(success_items)}")
    print(f"Not processed / failed : {len(failed_items)}")

    if success_items:
        print("\nSuccessful files:")
        for idx, item in enumerate(success_items, 1):
            print(f"{idx}. {item['source']}")
            print(f"   Output: {item['output']}")

if __name__ == '__main__':
    main()