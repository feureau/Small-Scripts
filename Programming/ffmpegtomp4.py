#!/usr/bin/env python3
"""
Convert video files to MP4, re-encode audio to AAC (up to 5.1/8 channels),
and extract/package all embedded subtitle streams alongside the output.

- Recursively processes all subdirectories from the working folder.
- Re-encodes audio to AAC at 1536 kbps by default (configurable).
- Copies the video stream losslessly.
- Extracts text-based subtitles to .srt files in a "srt" subfolder (English subtitles placed in "srt/English").
- Automatically generates a combined_english.txt transcript in "srt/English" if multiple videos have English subtitles.
- Packages image-based subtitles to .mkv files in the "srt" subfolder.
- Original files are safely moved into an "input" folder inside their own directory.
- New .mp4 output stays in the original file's location.
- Gracefully handles Ctrl-C by stopping FFmpeg and cleaning up partial files.
"""

import sys
import subprocess
import os
import re
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

def _is_english_stream(stream_info):
    """Checks tags and metadata to determine if a stream is English."""
    tags = stream_info.get('tags') or {}
    lang_code = tags.get('language', '').strip().lower()
    if lang_code in ('eng', 'en', 'english'):
        return True
    if pycountry and lang_code:
        try:
            lang = pycountry.languages.get(alpha_3=lang_code) or pycountry.languages.get(alpha_2=lang_code)
            if lang and lang.name.lower() == 'english':
                return True
        except Exception:
            pass
    title = tags.get('title', '').strip().lower()
    if 'english' in title or title == 'eng':
        return True
    return False

def _probe_streams(video_path, stream_type="s"):
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", stream_type, "-show_streams",
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
        print(f"  Error probing streams ({stream_type}): {e}")
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
    """Probes the video and extracts text subs to .srt (English in srt/English) and image subs to .mkv."""
    print("  Probing for subtitle streams...")
    streams = _probe_streams(video_path, "s")
    if not streams:
        print("  No subtitle streams found.")
        return

    text_subs = [s for s in streams if s.get('codec_name', '').lower() in KNOWN_TEXT_SUBTITLE_CODECS]
    image_subs = [s for s in streams if s.get('codec_name', '').lower() not in KNOWN_TEXT_SUBTITLE_CODECS]

    if not text_subs and not image_subs:
        print("  No extractable subtitle streams found.")
        return

    srt_base_dir = os.path.join(output_dir, "srt")
    english_dir = os.path.join(srt_base_dir, "English")

    # Extract text subtitles into the 'srt' (or 'srt/English') subfolder
    for stream in text_subs:
        is_english = _is_english_stream(stream)
        target_dir = english_dir if is_english else srt_base_dir
        os.makedirs(target_dir, exist_ok=True)
        out_name = _generate_subtitle_filename(video_basename, stream, "srt", target_dir)
        out_path = os.path.join(target_dir, out_name)
        display_subfolder = "srt/English" if is_english else "srt"
        cmd = ["ffmpeg", "-y", "-i", video_path, "-map", f"0:{stream['index']}", out_path]
        print(f"    Extracting SRT subtitle to: {display_subfolder}/{out_name}")
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
            for d in [english_dir, srt_base_dir]:
                if os.path.exists(d) and not os.listdir(d):
                    try:
                        os.rmdir(d)
                    except OSError:
                        pass
            raise # Bubble up to the main handler

    # Package image subtitles into the 'srt' subfolder
    for stream in image_subs:
        os.makedirs(srt_base_dir, exist_ok=True)
        out_name = _generate_subtitle_filename(video_basename, stream, "mkv", srt_base_dir)
        out_path = os.path.join(srt_base_dir, out_name)
        cmd = ["ffmpeg", "-y", "-i", video_path, "-map", f"0:{stream['index']}", "-c", "copy", out_path]
        print(f"    Packaging MKV subtitle to: srt/{out_name}")
        try:
            _, err, rc = _run_command_and_decode(cmd)
            if rc != 0:
                print(f"      Failed MKV packaging. Error: {err}")
        except KeyboardInterrupt:
            # Clean up partial subtitle on Ctrl-C
            if os.path.exists(out_path):
                os.remove(out_path)
                print(f"      -> Cleaned up incomplete subtitle: {out_name}")
            for d in [english_dir, srt_base_dir]:
                if os.path.exists(d) and not os.listdir(d):
                    try:
                        os.rmdir(d)
                    except OSError:
                        pass
            raise # Bubble up to the main handler

    # Cleanup directories if they ended up empty
    for d in [english_dir, srt_base_dir]:
        if os.path.exists(d) and not os.listdir(d):
            try:
                os.rmdir(d)
            except OSError:
                pass

def _clean_srt_text(srt_path):
    """Reads an SRT file, strips timestamps and subtitle index numbers, and returns clean text."""
    timestamp_pattern = re.compile(r'^\d{2}:\d{2}:\d{2}[,\.]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[,\.]\d{3}')
    line_number_pattern = re.compile(r'^\d+$')

    try:
        with open(srt_path, 'rb') as f:
            raw_data = f.read()
        enc = chardet.detect(raw_data)['encoding'] or 'utf-8'
        content = raw_data.decode(enc, errors='replace')
    except Exception:
        with open(srt_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()

    cleaned_lines = []
    for line in content.splitlines():
        line_str = line.strip()
        if not line_str:
            if cleaned_lines and cleaned_lines[-1] != "":
                cleaned_lines.append("")
            continue
        if line_number_pattern.match(line_str):
            continue
        if timestamp_pattern.match(line_str):
            continue
        cleaned_lines.append(line_str)

    return "\n".join(cleaned_lines).strip()

def _check_and_generate_combined_english_txt(folder):
    """If there are English SRTs from multiple videos in srt/English/, create combined_english.txt."""
    english_dir = os.path.join(folder, "srt", "English")
    if not os.path.isdir(english_dir):
        return

    srt_files = [
        os.path.join(english_dir, f) for f in os.listdir(english_dir)
        if f.lower().endswith(".srt") and not f.lower().startswith("combined_")
    ]
    if len(srt_files) < 2:
        return

    # Group SRTs by video basename to determine distinct videos
    # Filename format: <video_basename> - <tag>.srt
    video_map = {}
    for srt_path in sorted(srt_files):
        fname = os.path.splitext(os.path.basename(srt_path))[0]
        if " - " in fname:
            v_base = fname.rsplit(" - ", 1)[0]
        else:
            v_base = fname
        if v_base not in video_map:
            video_map[v_base] = []
        video_map[v_base].append(srt_path)

    # Only generate if there are multiple distinct videos
    if len(video_map) < 2:
        return

    # Select best SRT per video: prefer non-[Forced] if available
    selected_srts = []
    for v_base, s_list in sorted(video_map.items()):
        non_forced = [s for s in s_list if "[forced]" not in os.path.basename(s).lower()]
        best_srt = non_forced[0] if non_forced else s_list[0]
        selected_srts.append((v_base, best_srt))

    combined_path = os.path.join(english_dir, "combined_english.txt")
    rel_path = os.path.relpath(combined_path, folder).replace(os.sep, '/')
    print(f"\nGenerating combined English transcript for {len(selected_srts)} videos:")
    print(f"  -> {rel_path}")

    try:
        with open(combined_path, 'w', encoding='utf-8') as out_f:
            for idx, (v_base, srt_file) in enumerate(selected_srts):
                cleaned_text = _clean_srt_text(srt_file)
                if idx > 0:
                    out_f.write("\n\n" + "=" * 80 + "\n")
                else:
                    out_f.write("=" * 80 + "\n")
                out_f.write(f"Source: {os.path.splitext(os.path.basename(srt_file))[0]}\n")
                out_f.write("=" * 80 + "\n\n")
                out_f.write(cleaned_text + "\n")
    except Exception as e:
        print(f"  Error writing combined English transcript: {e}")

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
    # First check if this is an exact file path
    if os.path.isfile(pattern):
        return [os.path.abspath(pattern)]
    exact_path = os.path.join(base_dir, pattern)
    if os.path.isfile(exact_path):
        return [os.path.abspath(exact_path)]

    # Fallback for literal paths with Unicode encoding differences (only if not a glob pattern)
    is_glob = any(c in pattern for c in ('*', '?', '['))
    if not is_glob and '|' not in pattern:
        for dirpath, dirnames, filenames in os.walk(base_dir):
            dirnames[:] = [d for d in dirnames if d.lower() not in ('input', 'srt')]
            for fname in filenames:
                full_path = os.path.join(dirpath, fname)
                if pattern.casefold() in full_path.casefold() or full_path.casefold() in pattern.casefold():
                    return [full_path]

    found = []
    patterns = [p.strip() for p in pattern.split('|') if p.strip()]

    for dirpath, dirnames, filenames in os.walk(base_dir):
        dirnames[:] = [d for d in dirnames if d.lower() not in ('input', 'srt')]
        
        for fname in filenames:
            for p in patterns:
                if fnmatch.fnmatch(fname, p):
                    found.append(os.path.join(dirpath, fname))
                    break
    
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
    processed_dirs = set()

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

        # Identify audio streams, sort English first, and keep metadata
        audio_streams = _probe_streams(file, "a")
        audio_maps_and_metadata = []

        if audio_streams and len(audio_streams) > 0:
            english_streams = []
            other_streams = []
            for s in audio_streams:
                tags = s.get('tags') or {}
                lang = tags.get('language', '').lower()

                if lang in ('eng', 'en', 'english'):
                    english_streams.append(s)
                else:
                    other_streams.append(s)

            sorted_streams = english_streams + other_streams

            for i, s in enumerate(sorted_streams):
                audio_maps_and_metadata.extend(["-map", f"0:{s['index']}"])

                tags = s.get('tags') or {}
                lang = tags.get('language')
                if lang:
                    audio_maps_and_metadata.extend([f"-metadata:s:a:{i}", f"language={lang}"])

                title = tags.get('title')
                if title:
                    audio_maps_and_metadata.extend([f"-metadata:s:a:{i}", f"title={title}"])

                # Make the first stream default
                disp = "default" if i == 0 else "0"
                audio_maps_and_metadata.extend([f"-disposition:a:{i}", disp])
        else:
            # Fallback if no specific streams found
            audio_maps_and_metadata = ["-map", "0:a"]

        layout_args = ["-ch_layout", desired_layout] if downmix_method == "5.1" else ["-ac", str(channels)]

        command = [
            "ffmpeg", "-y",
            "-i", file,
            "-map", "0:v:0", "-c:v", "copy"
        ] + audio_maps_and_metadata + [
            "-c:a", audio_encoder, "-b:a", audio_bitrate
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
            processed_dirs.add(file_dir)
        else:
            print(f"\nError processing {file}: ffmpeg exited with code {proc.returncode}")
            stderr_output = "".join(stderr_lines).strip() or "No stderr captured"
            failed_items.append({"source": file, "status": "ffmpeg_error", "returncode": proc.returncode, "reason": stderr_output})

    # Generate combined English transcripts for directories with multiple videos having English SRTs
    for p_dir in sorted(processed_dirs):
        _check_and_generate_combined_english_txt(p_dir)

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