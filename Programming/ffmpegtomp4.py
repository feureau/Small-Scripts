import argparse
import glob
import subprocess
import os
import shutil
import sys
import traceback

def find_ffmpeg_tools():
    """Checks if ffmpeg and ffprobe are in PATH and executable."""
    # Use shutil.which for cross-platform compatibility
    ffmpeg_found = shutil.which("ffmpeg") is not None
    ffprobe_found = shutil.which("ffprobe") is not None

    if not ffmpeg_found:
        print("ERROR: ffmpeg not found in PATH. Please install ffmpeg and ensure it's accessible.")
        print("Download from: https://ffmpeg.org/download.html")
    if not ffprobe_found:
        print("ERROR: ffprobe not found in PATH. Please install ffprobe and ensure it's accessible.")
        print("ffprobe is usually included with ffmpeg.")
    
    return ffmpeg_found and ffprobe_found

def convert_to_subtitle_free_video(input_file, output_extension):
    """
    Converts a video file to a new container, copying video/audio streams only (no subtitles).
    Returns the path to the output file if successful, otherwise None.
    """
    if not os.path.isfile(input_file):
        print(f"Skipping non-file for conversion: {input_file}")
        return None

    base, old_ext = os.path.splitext(input_file)
    output_file = base + "." + output_extension.lstrip('.')

    if os.path.abspath(input_file) == os.path.abspath(output_file):
        print(f"Warning: Input and output file paths are identical ({input_file}).")
        print(f"To create a subtitle-free version of an existing {output_extension} file, ensure output path is different or rename input.")
        print("Skipping conversion for this file to prevent issues.")
        return None 

    print(f"Converting to subtitle-free {output_extension}: {input_file} -> {output_file}")

    command = [
        "ffmpeg",
        "-hide_banner", # Added to reduce clutter in output
        "-i", input_file,
        "-map", "0:v?",         # Map all video streams (optional)
        "-map", "0:a?",         # Map all audio streams (optional)
        "-c:v", "copy",
        "-c:a", "copy",
        "-sn",                  # Crucial: Strip (disable) all subtitle recording
        "-map_metadata", "0",
        "-map_chapters", "0",
        "-y", 
        # Add the experimental flag specifically for potential experimental codecs like TrueHD in MP4
        # This is safe for muxing TrueHD into MP4, which FFmpeg warns about but can do.
        "-strict", "experimental", # Using 'experimental' is equivalent to '-strict -2'
        output_file
    ]

    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()

        if process.returncode == 0:
            print(f"Successfully created subtitle-free {output_extension}: {output_file}")
            return output_file
        else:
            print(f"Error creating subtitle-free {output_extension} from {input_file}:")
            print("FFmpeg stdout:")
            # print(stdout.decode(errors='replace')) # FFmpeg usually outputs progress to stderr
            print("FFmpeg stderr:")
            print(stderr.decode(errors='replace'))
            if os.path.exists(output_file) and os.path.getsize(output_file) == 0:
                try:
                    os.remove(output_file)
                    print(f"Deleted zero-byte output file: {output_file}")
                except OSError as e:
                    print(f"Error deleting zero-byte file {output_file}: {e}")
            return None
    except FileNotFoundError:
        print("Error: ffmpeg command not found. Make sure it's installed and in your PATH.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while converting {input_file}: {e}")
        traceback.print_exc()
        return None

def extract_srt_from_original_file(original_video_path, srt_output_folder):
    """
    Extracts all convertible subtitle streams from the ORIGINAL video file to SRT format.
    Saves SRT files in the specified srt_output_folder.
    Bitmap subtitles (like PGS/VobSub) cannot be converted to SRT directly and will be skipped.
    """
    if not original_video_path or not os.path.isfile(original_video_path):
        print(f"Error: Original video file for subtitle extraction not found: {original_video_path}")
        return False

    base_name = os.path.splitext(os.path.basename(original_video_path))[0]
    print(f"Proceeding to extract subtitles from original file: {original_video_path} into {srt_output_folder}")

    try:
        ffprobe_command = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "s",
            "-show_entries", "stream=index,codec_name:stream_tags=language",
            "-of", "csv=p=0",
            original_video_path # Probe the original file
        ]
        
        process_ffprobe = subprocess.run(ffprobe_command, capture_output=True, text=True, check=False)
        
        if process_ffprobe.returncode != 0:
            print(f"ffprobe command failed for {original_video_path}. Return code: {process_ffprobe.returncode}")
            print(f"ffprobe stderr:\n>>>\n{process_ffprobe.stderr}\n<<<")
            return False

        ffprobe_output = process_ffprobe.stdout.strip()
        subtitle_lines = ffprobe_output.split('\n')
        if not ffprobe_output:
             subtitle_lines = []

        if not subtitle_lines:
            print(f"No subtitle streams found by ffprobe in original: {original_video_path}")
            return True
        
        subtitle_stream_info = []
        for line in subtitle_lines:
            if not line.strip():
                continue
            parts = line.split(',')
            try:
                ffmpeg_idx = int(parts[0])
                codec_name = parts[1] if len(parts) > 1 and parts[1] else "unknown_codec"
                lang = parts[2] if len(parts) > 2 and parts[2] else "und"
                subtitle_stream_info.append({"ffmpeg_index": ffmpeg_idx, "lang": lang, "codec": codec_name})
            except (ValueError, IndexError):
                print(f"Warning: Could not parse subtitle stream info from line: '{line}' in {original_video_path}")
                continue
        
        if not subtitle_stream_info:
            print(f"No valid subtitle streams could be parsed from original: {original_video_path}")
            return True

        extracted_any = False
        for stream_data in subtitle_stream_info:
            ffmpeg_stream_idx = stream_data['ffmpeg_index']
            lang_code = stream_data['lang']
            original_codec = stream_data['codec']
            
            # Check if the codec is image-based (bitmap) and cannot be converted to SRT directly
            # Common bitmap subtitle codecs include hdmv_pgs_subtitle (PGS) and vobsub
            if original_codec in ["hdmv_pgs_subtitle", "vobsub"]:
                 print(f"  Skipping subtitle stream (FFmpeg index {ffmpeg_stream_idx}, codec: {original_codec}, lang: {lang_code}): Cannot convert bitmap subtitles directly to SRT with ffmpeg.")
                 print("  You need an external OCR tool for this.")
                 continue # Skip this stream

            unique_track_suffix = f"idx{ffmpeg_stream_idx}_{lang_code}"
            output_srt_filename = f"{base_name}_sub.{unique_track_suffix}.srt"
            output_srt_path = os.path.join(srt_output_folder, output_srt_filename)

            # Proceed with extraction for potentially text-based formats
            ffmpeg_extract_command = [
                "ffmpeg",
                "-hide_banner", # Added to reduce clutter
                "-i", original_video_path, # Extract from the ORIGINAL file
                "-map", f"0:s:{ffmpeg_stream_idx}", # Explicitly map stream as subtitle
                "-c:s", "srt", # Attempt to convert to SRT
                "-y",
                output_srt_path
            ]

            print(f"  Extracting subtitle stream (FFmpeg index {ffmpeg_stream_idx} from ORIGINAL '{os.path.basename(original_video_path)}', original codec: {original_codec}, lang: {lang_code}) to: {output_srt_path}")
            extract_process = subprocess.Popen(ffmpeg_extract_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            s_stdout, s_stderr = extract_process.communicate()

            if extract_process.returncode == 0:
                if os.path.exists(output_srt_path) and os.path.getsize(output_srt_path) > 0:
                    print(f"  SRT extracted successfully: {output_srt_path}")
                    extracted_any = True
                else:
                    # This might happen if the stream was empty or not actually text,
                    # or if the conversion failed silently in FFmpeg's stderr.
                    # Check stderr for clues if needed, but reporting empty file is key.
                    print(f"  SRT extraction resulted in an empty or missing file for stream (FFmpeg index {ffmpeg_stream_idx}). Original codec was {original_codec}. File: {output_srt_path}")
                    # If a zero-byte file was created, delete it
                    if os.path.exists(output_srt_path) and os.path.getsize(output_srt_path) == 0:
                         try: os.remove(output_srt_path)
                         except OSError: pass

            else:
                print(f"  Error extracting SRT (FFmpeg index {ffmpeg_stream_idx} from original):")
                # print(f"  FFmpeg stdout: {s_stdout.decode(errors='replace')}") # Usually empty for extraction errors
                print(f"  FFmpeg stderr: {s_stderr.decode(errors='replace')}")
                if os.path.exists(output_srt_path) and os.path.getsize(output_srt_path) == 0:
                    try:
                        os.remove(output_srt_path)
                        print(f"  Deleted zero-byte output file: {output_srt_path}")
                    except OSError as e:
                        print(f"  Error deleting zero-byte file {output_srt_path}: {e}")


        if not extracted_any and any(s['codec'] not in ["hdmv_pgs_subtitle", "vobsub"] for s in subtitle_stream_info):
             # Only report this if there were non-bitmap subtitles that weren't extracted
             print(f"No *convertible* subtitles were successfully extracted as non-empty SRT from {original_video_path}. Check FFmpeg errors above.")
        elif all(s['codec'] in ["hdmv_pgs_subtitle", "vobsub"] for s in subtitle_stream_info):
             print(f"All subtitle streams in {original_video_path} were bitmap formats (like PGS/VobSub) and cannot be converted to SRT directly by this script.")


        return True # Return True even if no SRTs were extracted, if the process completed without crashing

    except Exception as e:
        print(f"Unexpected error extracting subtitles from {original_video_path}: {type(e).__name__} - {e}")
        traceback.print_exc()
        return False

def main():
    if not find_ffmpeg_tools():
        sys.exit(1)

    parser = argparse.ArgumentParser(
        description="Converts videos to a subtitle-free MP4 (or other specified format), then extracts SRT subtitles from the ORIGINAL input file into an 'SRT' subfolder.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Notes:
- Requires ffmpeg and ffprobe to be installed and in your system's PATH.
- Video conversion creates new files (e.g., MP4) *without any embedded subtitles*.
- SRT subtitles are then extracted from the *original input* video files.
- Extracted SRTs are saved in a subfolder named 'SRT' in the current working directory.
  SRT filenames: {original_basename}_sub.idx{ffmpeg_stream_index}_{language}.srt
- This script CANNOT convert image-based subtitles (like PGS/VobSub from Blu-rays) to text-based SRT.
  These streams will be identified but skipped for SRT extraction, and a message will be printed.
- Uses '-strict experimental' for MP4 conversion to handle experimental codecs like TrueHD audio.
"""
    )
    parser.add_argument(
        "-e", "--extension",
        default="mp4",
        help="Target container extension for subtitle-free conversion (e.g., mp4, mkv, mov). Default is 'mp4'."
    )
    parser.add_argument(
        "input_files",
        nargs="*",
        help="Video files or glob patterns to process (e.g., *.mkv video.avi)."
    )

    args = parser.parse_args()
    target_extension = args.extension.lstrip('.')
    
    srt_main_output_folder = os.path.join(os.getcwd(), "SRT")
    try:
        # Ensure the SRT output directory exists
        os.makedirs(srt_main_output_folder, exist_ok=True)
        print(f"SRT files (if extractable) will be saved in: {srt_main_output_folder}")
    except OSError as e:
        print(f"Error: Could not create SRT output directory '{srt_main_output_folder}': {e}")
        sys.exit(1)

    files_to_process = []
    if not args.input_files:
        print("No input files provided. Trying common video files in current directory...")
        common_video_extensions = ["*.mkv", "*.mp4", "*.avi", "*.mov", "*.webm", "*.flv"]
        for pattern in common_video_extensions: files_to_process.extend(glob.glob(pattern))
        if not files_to_process:
            print("No common video files found in current directory.")
            parser.print_help()
            return
    else:
        for pattern in args.input_files:
            expanded_files = glob.glob(pattern)
            if not expanded_files: print(f"Warning: Pattern '{pattern}' did not match any files.")
            files_to_process.extend(expanded_files)

    if not files_to_process:
        print("No files matched input patterns or found in current directory. Exiting.")
        return

    # Use absolute paths and a set to handle duplicates from glob patterns
    processed_paths = set()
    unique_files = []
    for f in files_to_process:
        abs_f = os.path.abspath(f)
        if abs_f not in processed_paths:
            processed_paths.add(abs_f)
            unique_files.append(f)

    print(f"\nFound {len(unique_files)} unique video file(s) to process.")

    for input_file_path in unique_files: # This is the path to the original MKV or other input
        print(f"\n--- Processing file: {input_file_path} ---")
        
        # 1. Convert original video to a subtitle-free MP4 (or specified extension)
        # The function already handles printing errors.
        converted_video_path = convert_to_subtitle_free_video(input_file_path, target_extension)
        
        if converted_video_path:
             print(f"Subtitle-free conversion process finished (check logs above for success/failure).")
        else:
             print(f"Subtitle-free conversion process failed or was skipped for: {input_file_path}")

        # 2. Extract SRT subtitles from the ORIGINAL input file
        # The function now checks codec types and skips non-convertible ones.
        extract_srt_from_original_file(input_file_path, srt_main_output_folder)
        
    print("\n--- All processing finished. ---")

if __name__ == "__main__":
    main()