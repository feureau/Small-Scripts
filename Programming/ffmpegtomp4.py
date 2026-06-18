#!/usr/bin/env python3
"""
Convert video files to MP4, re-encode audio to AAC (up to 5.1/8 channels),
and extract/package all embedded subtitle streams alongside the output.

- Recursively processes all subdirectories from the working folder.
- Re-encodes audio to AAC at 1536 kbps by default (configurable).
- Copies the video stream losslessly.
- Extracts text-based subtitles to .srt files in the file's own folder.
- Packages image-based subtitles to .mkv files in the file's own folder.
- Original files are safely moved into an "input" folder inside their own directory.
- New .mp4 output stays in the original file's location.
- Gracefully handles Ctrl-C by stopping FFmpeg and cleaning up partial files.
"""

import sys
import subprocess
import os
import argparse
import shutil
import fnmatch
import json

try:
    import chardet
except ImportError:
    print("Error: The 'chardet' library is required. Install it via: pip install chardet")
    sys.exit(1)

try:
    import pycountry
except ImportError:
    pycountry = None
    print("Warning: 'pycountry' library not found. Language codes will not be expanded. (pip install pycountry)")

# --------------------------------------------------------------------------------------------------
# CONFIGURATION & CONSTANTS
# --------------------------------------------------------------------------------------------------

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

KNOWN_TEXT_SUBTITLE_CODECS = [
    'srt', 'subrip', 'ass', 'ssa', 'webvtt', 'mov_text', 'tx3g',
    'subviewer', 'microdvd', 'eia_608', 'cea608',
]

# --------------------------------------------------------------------------------------------------
# SUBTITLE EXTRACTION HELPERS
# --------------------------------------------------------------------------------------------------

def _run_command_and_decode(command_args):
    """Runs a subprocess, detects encoding, and returns decoded stdout/stderr safely."""
    try:
        process = subprocess.run(command_args, capture_output=True, check=True)
        stdout_bytes, stderr_bytes = process.stdout, process.stderr
        
        stdout_enc = chardet.detect(stdout_bytes)['encoding'] or 'utf-8'
        decoded_stdout = stdout_bytes.decode(stdout_enc, errors='replace')

        stderr_enc = chardet.detect(stderr_bytes)['encoding'] or 'utf-8'
        decoded_stderr = stderr_bytes.decode(stderr_enc, errors='replace')

        return decoded_stdout, decoded_stderr, process.returncode
    except subprocess.CalledProcessError as e:
        error_output = e.stderr.decode('utf-8', errors='replace') if e.stderr else "No stderr output."
        last_line_of_error = error_output.strip().splitlines()[-1] if error_output.strip() else "Unknown FFmpeg error"
        return None, last_line_of_error, e.returncode

def _get_language_name(code):
    if not code or not pycountry:
        return code
    try:
        lang = pycountry.languages.get(alpha_3=code.lower()) or pycountry.languages.get(alpha_2=code.lower())
        return lang.name if lang else code
    except Exception:
        return code

def _probe_subtitle_streams(video_path):
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "s", "-show_streams",
        "-show_entries", "stream=index,codec_name,disposition,tags", "-of", "json", video_path
    ]
    try:
        process = subprocess.run(cmd, capture_output=True, check=True)
        try:
            decoded_stdout = process.stdout.decode('utf-8')
        except UnicodeDecodeError:
            enc = chardet.detect(process.stdout)['encoding'] or 'utf-8'
            decoded_stdout = process.stdout.decode(enc, errors='replace')
            
        return json.loads(decoded_stdout).get("streams", [])
    except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
        print(f"  Error probing subtitles: {e}")
        return None

def _generate_subtitle_filename(video_basename, stream_info, extension, output_dir):
    tags = stream_info.get('tags', {})
    disposition = stream_info.get('disposition', {})
    
    title, language = None, None
    for k, v in tags.items():
        if k.lower() == 'title': title = v
        if k.lower() == 'language': language = _get_language_name(v)

    is_forced = str(disposition.get('forced', '0')) == '1'
    tag = language if language else (title if title else "Unknown")

    if is_forced and "[Forced]" not in tag and "forced" not in tag.lower():
        tag = f"{tag} [Forced]"

    illegal_chars = r'\/:*?"<>|'
    sanitized_tag = "".join(c for c in tag if c not in illegal_chars).strip() or "Unknown"

    base_name_no_ext = f"{video_basename} - {sanitized_tag}"
    filename = f"{base_name_no_ext}.{extension}"
    
    counter = 1
    while os.path.exists(os.path.join(output_dir, filename)):
        filename = f"{base_name_no_ext} ({counter}).{extension}"
        counter += 1

    return filename

def extract_subtitles_hybrid(video_path, output_dir, video_basename):
    """Probes the video and extracts text subs to .srt and image subs to .mkv."""
    print("  Probing for subtitle streams...")
    streams = _probe_subtitle_streams(video_path)
    if not streams:
        print("  No subtitle streams found.")
        return

    text_subs = [s for s in streams if s.get('codec_name', '').lower() in KNOWN_TEXT_SUBTITLE_CODECS]
    image_subs = [s for s in streams if s.get('codec_name', '').lower() not in KNOWN_TEXT_SUBTITLE_CODECS]

    # Extract text subtitles into the exact same folder
    for stream in text_subs:
        out_name = _generate_subtitle_filename(video_basename, stream, "srt", output_dir)
        out_path = os.path.join(output_dir, out_name)
        cmd = ["ffmpeg", "-y", "-i", video_path, "-map", f"0:{stream['index']}", out_path]
        print(f"    Extracting SRT subtitle to: {out_name}")
        try:
            _, err, rc = _run_command_and_decode(cmd)
            if rc != 0:
                print(f"      Failed SRT extraction. Error: {err}")
                if os.path.exists(out_path) and os.path.getsize(out_path) < 20:
                    os.remove(out_path)
        except KeyboardInterrupt:
            # Clean up partial subtitle on Ctrl-C
            if os.path.exists(out_path):
                os.remove(out_path)
                print(f"      -> Cleaned up incomplete subtitle: {out_name}")
            raise # Bubble up to the main handler

    # Package image subtitles into the exact same folder
    for stream in image_subs:
        out_name = _generate_subtitle_filename(video_basename, stream, "mkv", output_dir)
        out_path = os.path.join(output_dir, out_name)
        cmd = ["ffmpeg", "-y", "-i", video_path, "-map", f"0:{stream['index']}", "-c", "copy", out_path]
        print(f"    Packaging MKV subtitle to: {out_name}")
        try:
            _, err, rc = _run_command_and_decode(cmd)
            if rc != 0:
                print(f"      Failed MKV packaging. Error: {err}")
        except KeyboardInterrupt:
            # Clean up partial subtitle on Ctrl-C
            if os.path.exists(out_path):
                os.remove(out_path)
                print(f"      -> Cleaned up incomplete subtitle: {out_name}")
            raise # Bubble up to the main handler

# --------------------------------------------------------------------------------------------------
# VIDEO PROCESSING HELPERS
# --------------------------------------------------------------------------------------------------

def calculate_channel_count(layout: str) -> int:
    parts = layout.split('.')
    try:
        return sum(int(p) for p in parts)
    except ValueError:
        return NAMED_LAYOUTS.get(layout, 6)

def find_video_files_recursive(base_dir, pattern):
    """Walk the directory tree recursively, matching the provided patterns."""
    patterns = pattern.split('|')
    found = []
    
    for dirpath, dirnames, filenames in os.walk(base_dir):
        dirnames[:] = [d for d in dirnames if d.lower() != 'input']
        
        for fname in filenames:
            if any(fnmatch.fnmatch(fname, p) for p in patterns):
                found.append(os.path.join(dirpath, fname))
    return found

def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Recursively convert video files to MP4 and extract subtitles in place.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "pattern", nargs='?',
        default="*.[Mm][Pp]4|*.[Mm][Kk][Vv]|*.[Aa][Vv][Ii]|*.[Mm][Oo][Vv]|*.[Ww][Ee][Bb][Mm]|*.[Tt][Ss]",
        help="Input file pattern (e.g., \"*.mkv|*.mp4\")."
    )
    parser.add_argument(
        "-l", "--layout", default="5.1",
        help=f"Desired audio channel layout. (default: 5.1)"
    )
    parser.add_argument(
        "-d", "--downmix", choices=["5.1", "6"], default="5.1",
        help="Downmix method: '5.1' (-ch_layout) or '6' (-ac). Default: 5.1"
    )
    parser.add_argument(
        "-b", "--bitrate", default="1536k",
        help="Total audio bitrate for the AAC encoder (e.g., 640k, 1536k). Default: 1536k"
    )
    return parser.parse_args()

# --------------------------------------------------------------------------------------------------
# MAIN PIPELINE
# --------------------------------------------------------------------------------------------------

def main():
    args = parse_arguments()
    file_pattern = args.pattern
    desired_layout = args.layout
    downmix_method = args.downmix
    audio_bitrate = args.bitrate
    channels = calculate_channel_count(desired_layout)

    audio_encoder = "aac_mf"

    if channels > 8:
        print(f"Error: Layout '{desired_layout}' implies {channels} channels. AAC supports max 8.")
        sys.exit(1)

    base_dir = os.getcwd()
    files = find_video_files_recursive(base_dir, file_pattern)

    if not files:
        print(f"No files found matching: {file_pattern} in {base_dir} or its subdirectories.")
        sys.exit(1)

    files.sort()
    print(f"\nFound {len(files)} file(s) across directory tree:")
    for f in files:
        print(f"  {os.path.relpath(f, base_dir)}")

    success_items = []
    failed_items = []

    for file in files:
        print(f"\n{'='*60}\nProcessing: {file}")

        file_dir = os.path.dirname(file)
        base, _ = os.path.splitext(os.path.basename(file))
        
        input_dir = os.path.join(file_dir, "input")
        final_output_file = os.path.join(file_dir, base + ".mp4")

        is_same_file = (os.path.abspath(file).lower() == os.path.abspath(final_output_file).lower())
        if is_same_file:
            current_output_file = os.path.join(file_dir, base + "_temp_conv.mp4")
        else:
            current_output_file = final_output_file

        layout_args = ["-ch_layout", desired_layout] if downmix_method == "5.1" else ["-ac", str(channels)]

        command = [
            "ffmpeg", "-y",
            "-i", file,
            "-map", "0:v:0", "-c:v", "copy",
            "-map", "0:a", "-c:a", audio_encoder, "-b:a", audio_bitrate,
        ] + layout_args + [current_output_file]

        print(f"Running video/audio conversion (Audio: {audio_bitrate})...")
        
        stderr_lines = []
        try:
            proc = subprocess.Popen(
                command, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL,
                text=True, encoding="utf-8", errors="replace"
            )
            for line in proc.stderr:
                sys.stderr.write(line)
                sys.stderr.flush()
                stderr_lines.append(line)
            proc.wait()
            
        except KeyboardInterrupt:
            # Catch Ctrl-C specifically during FFmpeg conversion
            print("\n\n[!] Ctrl-C detected! Aborting conversion gracefully...")
            
            try:
                proc.terminate()
                proc.wait(timeout=3) # Allow ffmpeg a few seconds to close gracefully
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
            except Exception:
                pass

            # Ensure we delete the partial/incomplete video file
            if os.path.exists(current_output_file):
                try:
                    os.remove(current_output_file)
                    print(f"  -> Cleaned up incomplete file: {os.path.basename(current_output_file)}")
                except Exception as e:
                    print(f"  -> Could not remove {os.path.basename(current_output_file)}: {e}")
            
            # Exit to prevent moving on to the next file
            sys.exit(130) 

        except Exception as e:
            print(f"Unexpected error running ffmpeg: {e}")
            failed_items.append({"source": file, "status": "script_error", "reason": str(e)})
            continue

        if proc.returncode == 0:
            print(f"\nSuccessfully converted to MP4.")
            
            # 1. EXTRACT SUBTITLES
            extract_subtitles_hybrid(file, file_dir, base)

            # 2. MOVE ORIGINAL FILE
            os.makedirs(input_dir, exist_ok=True)
            moved_path = os.path.join(input_dir, os.path.basename(file))
            shutil.move(file, moved_path)
            print(f"  Moved original file to: {moved_path}")

            # 3. RENAME MP4
            if is_same_file:
                os.rename(current_output_file, final_output_file)

            success_items.append({"source": file, "output": final_output_file, "status": "ok"})
        else:
            print(f"\nError processing {file}: ffmpeg exited with code {proc.returncode}")
            stderr_output = "".join(stderr_lines).strip() or "No stderr captured"
            failed_items.append({"source": file, "status": "ffmpeg_error", "returncode": proc.returncode, "reason": stderr_output})

    print("\n" + "=" * 72)
    print("PROCESSING SUMMARY")
    print("=" * 72)
    print(f"Total files discovered : {len(files)}")
    print(f"Successful conversions : {len(success_items)}")
    print(f"Failed conversions     : {len(failed_items)}")

    if failed_items:
        print("\nFailed files:")
        for idx, item in enumerate(failed_items, 1):
            print(f"{idx}. {item['source']}")
            reason = item.get("reason", "").strip()
            if reason:
                for line in reason.splitlines()[-5:]: # Show last 5 lines of error
                    print(f"   {line}")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        # Final catch to prevent printing Python tracebacks on graceful exit
        print("\n\n[!] Script interrupted by user. Exiting...")
        sys.exit(130)