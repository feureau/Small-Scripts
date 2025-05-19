import argparse
import glob
import subprocess
import os
import shutil
import sys

def find_ffmpeg_tools():
    """Checks if ffmpeg and ffprobe are in PATH and executable."""
    ffmpeg_found = shutil.which("ffmpeg") is not None
    ffprobe_found = shutil.which("ffprobe") is not None

    if not ffmpeg_found:
        print("ERROR: ffmpeg not found in PATH. Please install ffmpeg and ensure it's accessible.")
    if not ffprobe_found:
        print("ERROR: ffprobe not found in PATH. Please install ffprobe and ensure it's accessible.")
    
    return ffmpeg_found and ffprobe_found

def convert_video_no_subs(input_file, output_extension):
    """
    Converts a video file to a new container format using ffmpeg,
    copying only video and audio streams (no subtitles).
    Returns the path to the output file if successful, otherwise None.
    """
    if not os.path.isfile(input_file):
        print(f"Skipping non-file for conversion: {input_file}")
        return None

    base, old_ext = os.path.splitext(input_file)
    output_file = base + "." + output_extension.lstrip('.')

    if os.path.abspath(input_file) == os.path.abspath(output_file):
        print(f"Warning: Input and output file paths are identical ({input_file}).")
        print(f"To create a subtitle-free version of an existing {output_extension} file, ensure the output path is different or rename the input.")
        print("Skipping conversion for this file to prevent issues.")
        return None 

    print(f"Converting to subtitle-free {output_extension}: {input_file} -> {output_file}")

    command = [
        "ffmpeg",
        "-i", input_file,
        "-map", "0:v",
        "-map", "0:a",
        "-c:v", "copy",
        "-c:a", "copy",
        "-sn", 
        "-map_metadata", "0",
        "-map_chapters", "0",
        "-y", 
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
            print(stdout.decode(errors='replace'))
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
        return None

def extract_subtitles_from_original(video_path, output_dir="."):
    """
    Extracts all convertible subtitle streams from the original video file to SRT format.
    Saves SRT files in the specified output_dir with unique names per track.
    """
    if not video_path or not os.path.isfile(video_path):
        print(f"Error: Original video file for subtitle extraction not found: {video_path}")
        return False

    base_name = os.path.splitext(os.path.basename(video_path))[0]
    print(f"Attempting to extract SRT subtitles from original: {video_path} into {output_dir}")

    try:
        ffprobe_command = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "s",
            "-show_entries", "stream=index,codec_name:stream_tags=language", 
            "-of", "csv=p=0",
            video_path
        ]
        # Using subprocess.run for potentially better handling of text output
        process_ffprobe = subprocess.run(ffprobe_command, capture_output=True, text=True, check=False)
        
        if process_ffprobe.returncode != 0:
            print(f"DEBUG: ffprobe command failed for {video_path}")
            print(f"DEBUG: ffprobe stderr:\n>>>\n{process_ffprobe.stderr}\n<<<")
            if "No match for section" in process_ffprobe.stderr or "Invalid argument" in process_ffprobe.stderr:
                 print("ERROR: Your version of ffprobe may not support the '-show_entries stream=index,codec_name:stream_tags=language' format.")
                 print("       Please check your ffprobe version or try a simpler ffprobe command structure if issues persist.")
            # Fallback or error based on ffprobe failure
            print(f"Tool (ffprobe) failed for {video_path} during subtitle check. Return code: {process_ffprobe.returncode}")
            return False


        ffprobe_output = process_ffprobe.stdout.strip()
        
        print(f"DEBUG: Raw ffprobe output for {video_path}:\n>>>\n{ffprobe_output}\n<<<")
        
        subtitle_lines = ffprobe_output.split('\n')
        # Handle case where ffprobe_output is empty, split('\n') on empty string yields ['']
        if not ffprobe_output: # If ffprobe_output was empty, subtitle_lines will be ['']
            subtitle_lines = [] 

        print(f"DEBUG: Number of subtitle lines found: {len(subtitle_lines)}")
        print(f"DEBUG: Subtitle lines content: {subtitle_lines}")

        if not subtitle_lines:
            print(f"No subtitle streams reported by ffprobe in original: {video_path}")
            return True
        
        subtitle_stream_info = []
        for i, line in enumerate(subtitle_lines):
            if not line.strip(): # Skip empty lines that might result from split if ffprobe output is weird
                print(f"DEBUG: Skipping empty line from ffprobe output at index {i}")
                continue
            parts = line.split(',')
            try:
                ffmpeg_idx = int(parts[0])
                codec_name = parts[1] if len(parts) > 1 and parts[1] else "unknown_codec"
                lang = parts[2] if len(parts) > 2 and parts[2] else "und" 
                subtitle_stream_info.append({"ffmpeg_index": ffmpeg_idx, "lang": lang, "codec": codec_name})
            except ValueError:
                print(f"Warning: Could not parse subtitle stream info from line: '{line}' in {video_path}")
                continue
            except IndexError:
                print(f"Warning: Line '{line}' from ffprobe has fewer parts than expected. Skipping.")
                continue
        
        print(f"DEBUG: Parsed subtitle_stream_info: {subtitle_stream_info}")

        if not subtitle_stream_info:
            print(f"No valid subtitle streams could be parsed for SRT extraction from original: {video_path}")
            return True

        extracted_any = False
        for stream_data in subtitle_stream_info:
            ffmpeg_stream_idx = stream_data['ffmpeg_index']
            lang_code = stream_data['lang']
            codec = stream_data['codec']
            
            unique_track_suffix = f"idx{ffmpeg_stream_idx}_{lang_code}"
            output_srt_filename = f"{base_name}_sub.{unique_track_suffix}.srt"
            output_srt_path = os.path.join(output_dir, output_srt_filename)

            print(f"DEBUG: Processing stream_data: {stream_data}")
            print(f"DEBUG: Generated output_srt_filename: {output_srt_filename}")
            print(f"DEBUG: Full output_srt_path: {output_srt_path}")


            ffmpeg_command = [
                "ffmpeg",
                "-i", video_path,
                "-map", f"0:{ffmpeg_stream_idx}",
                "-c:s", "srt", 
                "-y", 
                output_srt_path
            ]

            print(f"  Extracting subtitle stream (original FFmpeg index {ffmpeg_stream_idx}, codec: {codec}, lang: {lang_code}) to: {output_srt_path}")
            extract_process = subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            s_stdout, s_stderr = extract_process.communicate()

            if extract_process.returncode == 0:
                if os.path.exists(output_srt_path) and os.path.getsize(output_srt_path) > 0:
                    print(f"  SRT extracted successfully: {output_srt_path}")
                    extracted_any = True
                else:
                    print(f"  SRT extraction resulted in an empty file for stream (original FFmpeg index {ffmpeg_stream_idx}). File: {output_srt_path}")
                    if os.path.exists(output_srt_path):
                        try: os.remove(output_srt_path)
                        except OSError: pass
            else:
                print(f"  Error extracting SRT (original FFmpeg index {ffmpeg_stream_idx}):")
                print(f"  FFmpeg stderr: {s_stderr.decode(errors='replace')}")
        
        if not extracted_any:
            print(f"No subtitles were successfully extracted as non-empty SRT from {video_path}.")
        return True

    except subprocess.CalledProcessError as e: # Should not be hit if check=False with subprocess.run
        print(f"Tool (ffprobe) execution failed unexpectedly for {video_path}:")
        print(f"Command: {' '.join(e.cmd)}")
        if e.stdout: print(f"Stdout: {e.stdout}") # stdout for CalledProcessError
        if e.stderr: print(f"Stderr: {e.stderr}") # stderr for CalledProcessError
        return False
    except Exception as e:
        print(f"Unexpected error extracting subtitles from {video_path}: {type(e).__name__} - {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    if not find_ffmpeg_tools():
        sys.exit(1)

    parser = argparse.ArgumentParser(
        description="Extracts SRT subtitles from original videos (unique file per track) and batch converts videos to a subtitle-free MP4 (or other specified format).",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Examples:
  Extract SRTs (e.g., movie_sub.idx2_eng.srt) and convert MKVs to subtitle-free MP4s:
    %(prog)s *.mkv

  Specify a custom output directory for extracted SRT files:
    %(prog)s video.mkv -s_dir ./my_subtitles

Notes:
- Requires ffmpeg and ffprobe to be installed and in your system's PATH.
- SRT subtitles are extracted from the *original* video files. Each track becomes a separate .srt file
  named like: {basename}_sub.idx{ffmpeg_stream_index}_{language}.srt
- Video conversion creates new files (e.g., MP4) *without any embedded subtitles*, copying video & audio.
"""
    )
    parser.add_argument(
        "-e", "--extension",
        default="mp4",
        help="Target container extension for subtitle-free conversion (e.g., mp4, mkv, mov). Default is 'mp4'."
    )
    parser.add_argument(
        "-s_dir", "--subtitle_dir",
        default=".",
        help="Directory to save extracted SRT files. Default is the directory of the input video file."
    )
    parser.add_argument(
        "input_files",
        nargs="*",
        help="Video files or glob patterns to process (e.g., *.mkv video.avi)."
    )

    args = parser.parse_args()
    target_extension = args.extension.lstrip('.')
    
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
        print("No files matched input patterns or found in current directory.")
        return

    processed_paths = set()
    unique_files = []
    for f in files_to_process:
        abs_f = os.path.abspath(f)
        if abs_f not in processed_paths:
            processed_paths.add(abs_f)
            unique_files.append(f)

    print(f"\nFound {len(unique_files)} unique video file(s) to process.")

    for input_file_path in unique_files:
        print(f"\n--- Processing file: {input_file_path} ---")
        
        if args.subtitle_dir == ".":
            current_subtitle_output_dir = os.path.dirname(os.path.abspath(input_file_path))
            if not current_subtitle_output_dir: 
                current_subtitle_output_dir = "."
        else:
            current_subtitle_output_dir = args.subtitle_dir

        if not os.path.isdir(current_subtitle_output_dir):
            try:
                os.makedirs(current_subtitle_output_dir, exist_ok=True)
                print(f"Created subtitle output directory: {current_subtitle_output_dir}")
            except OSError as e:
                print(f"Error: Could not create subtitle output directory '{current_subtitle_output_dir}': {e}.")
                print("Skipping subtitle extraction for this file. Conversion will still be attempted.")
        
        extract_subtitles_from_original(input_file_path, current_subtitle_output_dir)
        
        converted_file_path = convert_video_no_subs(input_file_path, target_extension)
        if converted_file_path:
            print(f"Subtitle-free conversion completed: {converted_file_path}")
        else:
            print(f"Subtitle-free conversion failed or was skipped for: {input_file_path}")
        
    print("\n--- All processing finished. ---")

if __name__ == "__main__":
    main()