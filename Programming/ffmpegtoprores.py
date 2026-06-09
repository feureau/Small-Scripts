#!/usr/bin/env python3
"""
Convert video files to Apple ProRes in a MOV container.

- Fast Mode (GPU Decode + prores_aw) is enabled by default.
- Default profile is ProRes LT.
- Default audio exactly matches original script: AAC via `aac_mf` at 640k.
- Supports choosing between AAC (compressed) or PCM (uncompressed) audio.
- Original files are moved into a folder named after their extension (e.g. 'MP4').
- Converted files are placed in a folder named after the format (e.g. 'ProRes_LT').
- Recursively searches subdirectories for common video formats.
"""

import sys
import subprocess
import os
import argparse
import shutil
import fnmatch

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

def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Convert video files to ProRes (.mov) with flexible audio options.",
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
             "  aac - Compressed AAC (aac_mf) at 640kbps (Matches original script)\n"
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
    return parser.parse_args()

def find_video_files_recursive(base_dir, pattern):
    use_default = (pattern == "*.[Mm][Pp]4|*.[Mm][Kk][Vv]|*.[Aa][Vv][Ii]|*.[Mm][Oo][Vv]|*.[Ww][Ee][Bb][Mm]|*.[Tt][Ss]")
    found = []

    # Directories to ignore so we don't process previously moved files
    skip_exts = {'mp4', 'mkv', 'avi', 'mov', 'webm', 'ts', 'input', 'output'}

    for dirpath, dirnames, filenames in os.walk(base_dir):
        # Exclude directories named after extensions or starting with 'ProRes_'
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
        pix_fmt_args = [] 
    else:
        pix_fmt_args = ["-pix_fmt", "yuv422p10le"]

    # Fast Mode Logic (Enabled by default)
    is_fast = not args.slow
    video_encoder = "prores_ks"
    speed_mode = "High Quality (CPU Decode + prores_ks)"
    
    if is_fast:
        if args.profile in ["4444", "4444xq"]:
            speed_mode = "Mixed (GPU Decode + prores_ks for Alpha)"
        else:
            video_encoder = "prores_aw"
            speed_mode = "Fast (GPU Decode + prores_aw)"

    # Audio Logic (100% matched to original ffmpegtomp4.py)
    if args.audio == "aac":
        if channels > 8:
            print(f"Error: Requested layout '{desired_layout}' implies {channels} channels, but AAC supports at most 8 channels.")
            sys.exit(1)
        audio_encoder = "aac_mf"
        audio_bitrate = "640k"
        audio_args = [
            "-map", "0:a",
            "-c:a", audio_encoder,
            "-b:a", audio_bitrate
        ]
    else:
        audio_encoder = "pcm_s24le"
        audio_args = [
            "-map", "0:a",
            "-c:a", audio_encoder
        ]

    print(f"Target Video Codec: Apple ProRes ({args.profile.upper()})")
    print(f"Speed Profile     : {speed_mode}")
    print(f"Desired Audio     : {desired_layout} => {channels} channel(s) ({audio_encoder.upper()})")

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
        
        # Determine dynamic folder names
        ext = ext_with_dot.lstrip('.').upper()
        if not ext:
            ext = "INPUT"  # Fallback if a file has no extension
            
        prores_folder_name = f"ProRes_{args.profile.upper()}"

        # Assign Input and Output directories
        input_dir = os.path.join(file_dir, ext)
        output_dir = os.path.join(file_dir, prores_folder_name)
        output_file = os.path.join(output_dir, base + ".mov")

        if downmix_method == "5.1":
            layout_args = ["-ch_layout", desired_layout]
        else:
            layout_args = ["-ac", str(channels)]

        # --- Build Command Dynamically ---
        command = ["ffmpeg", "-y"]
        
        # 1. Add HW Accel flags BEFORE the input if fast mode is enabled
        if is_fast:
            command.extend(["-hwaccel", "auto"])
            
        # 2. Add Input and Video arguments
        command.extend([
            "-i", file,
            "-map", "0:v:0",
            "-c:v", video_encoder,
            "-profile:v", prores_profile_num,
            "-vendor", "ap10",
        ])
        
        # 3. Add Pixel Format args
        command.extend(pix_fmt_args)
        
        # 4. Add Audio arguments
        command.extend(audio_args)
        
        # 5. Add Layout and Output
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
            os.makedirs(input_dir, exist_ok=True)
            moved_path = os.path.join(input_dir, os.path.basename(file))
            shutil.move(file, moved_path)
            print(f"Moved original file to: {moved_path}")
            success_items.append({
                "source": file,
                "output": output_file,
                "status": "ok",
            })
        else:
            print(f"Error processing {file}: ffmpeg exited with code {proc.returncode}")
            stderr_output = "".join(stderr_lines).strip()
            if not stderr_output:
                stderr_output = "No stderr captured"
            print(f"FFmpeg Error Output:\n{stderr_output}")
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