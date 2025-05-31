import subprocess
import os
import sys
import glob
import argparse
import json # For parsing ffprobe JSON output

# Define known text-based subtitle codecs that ffmpeg can reasonably convert to SRT
KNOWN_TEXT_SUBTITLE_CODECS = [
    'srt', 'subrip',        # SubRip
    'ass', 'ssa',           # Advanced SubStation Alpha / SubStation Alpha
    'webvtt',               # Web Video Text Tracks
    'mov_text', 'tx3g',     # QuickTime text / 3GPP Timed Text
    'subviewer',            # SubViewer
    'microdvd',             # MicroDVD
    'eia_608', 'cea608',    # EIA-608 / CEA-608 (often text-convertible)
]


def _probe_subtitle_streams(video_path):
    """
    Probes video file for subtitle streams and returns their info.
    Returns: list of dicts [{'index': int, 'codec_name': str, 'tags': {}}, ...] or None if critical error.
    """
    ffprobe_command = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "s",  # Select only subtitle streams
        "-show_entries", "stream=index,codec_name,tags", # Get index, codec, and tags
        "-of", "json", # Output as JSON
        video_path
    ]
    try:
        ffprobe_process = subprocess.run(ffprobe_command, capture_output=True, text=True, check=True)
        probe_data = json.loads(ffprobe_process.stdout)
        return probe_data.get("streams", []) # Returns empty list if no "streams" key or streams list is empty
    except subprocess.CalledProcessError as e:
        print(f"  FFprobe error while probing subtitles in {video_path}:")
        error_msg = e.stderr.strip() if e.stderr else "No stderr output from ffprobe."
        print(f"    {error_msg}")
        return None # Indicate a critical failure in probing
    except json.JSONDecodeError:
        print(f"  Error: Could not parse ffprobe JSON output for {video_path}.")
        return None
    except Exception as e:
        print(f"  An unexpected error occurred during ffprobe for {video_path}: {e}")
        return None


def _generate_subtitle_filename(video_basename, stream_info, subtitle_processing_order_num, extension):
    """
    Generates a descriptive filename for an extracted/packaged subtitle.
    Args:
        video_basename: Basename of the video file.
        stream_info: Dict containing 'index', 'codec_name', and optionally 'tags'.
        subtitle_processing_order_num: 1-based Nth subtitle of its type being processed.
        extension: File extension (e.g., 'srt', 'mkv').
    """
    stream_index = stream_info['index']
    codec_name = stream_info.get('codec_name', 'unknown').lower()
    # Common aliases for brevity
    if codec_name == "hdmv_pgs_subtitle": codec_name = "pgs"
    if codec_name == "dvd_subtitle": codec_name = "dvdsub"

    lang_tag = stream_info.get('tags', {}).get('language', '')
    # title_tag = stream_info.get('tags', {}).get('title', '') # Titles can be long/messy; omitting for simplicity

    name_parts = [video_basename, f"sub{subtitle_processing_order_num}", f"idx{stream_index}"]
    if lang_tag: name_parts.append(lang_tag)
    name_parts.append(codec_name)
    
    filename_base = "_".join(name_parts)
    # Basic sanitization for problematic characters in filenames
    safe_chars = "._-" # Characters allowed in addition to alphanumerics
    filename_base = "".join(c if c.isalnum() or c in safe_chars else '_' for c in filename_base)
    
    # Truncate if filename (without extension) is too long
    max_base_len = 180 
    if len(filename_base) > max_base_len:
        filename_base = filename_base[:max_base_len]

    return f"{filename_base}.{extension}"


def _extract_subtitle_streams_as_srt(video_path, subtitle_streams_info, video_basename):
    """
    Extracts specified subtitle streams to individual .srt files.
    Returns: True if any extraction was successful, False otherwise.
    """
    if not subtitle_streams_info:
        return False

    extracted_count = 0
    print(f"  Attempting to extract {len(subtitle_streams_info)} text-based stream(s) to SRT format...")

    for i, stream_info in enumerate(subtitle_streams_info):
        # Use (i+1) for 1-based numbering in filename for this batch of text subs
        output_srt_filename = _generate_subtitle_filename(video_basename, stream_info, i + 1, "srt")
        output_srt_path = os.path.join(os.getcwd(), output_srt_filename)

        ffmpeg_command = [
            "ffmpeg", "-i", video_path,
            "-map", f"0:{stream_info['index']}",
            "-y", # Overwrite output file without asking
            output_srt_path # FFmpeg infers SRT format from extension
        ]

        print(f"    Extracting stream idx {stream_info['index']} ({stream_info.get('codec_name', 'unknown')}) to: {output_srt_path}")
        try:
            subprocess.run(ffmpeg_command, capture_output=True, text=True, check=True)
            print(f"      Successfully extracted: {output_srt_path}")
            extracted_count += 1
        except subprocess.CalledProcessError as e_stream:
            print(f"      Failed to extract subtitle stream idx {stream_info['index']} as SRT.")
            error_output = e_stream.stderr.strip().splitlines()[-1] if e_stream.stderr and e_stream.stderr.strip() else 'Unknown FFmpeg error'
            print(f"        FFmpeg error: {error_output}")
            # Clean up partially created/empty SRT file if extraction failed
            if os.path.exists(output_srt_path):
                try:
                    if os.path.getsize(output_srt_path) < 20: # Small threshold for BOM or minimal data
                         os.remove(output_srt_path)
                         print(f"        Removed empty/failed SRT file: {output_srt_path}")
                except OSError as ose:
                    print(f"        Warning: Could not check/remove failed SRT file {output_srt_path}: {ose}")
    
    if extracted_count > 0:
        print(f"  Successfully extracted {extracted_count} text-based subtitle stream(s) to SRT.")
    elif subtitle_streams_info: # If attempts were made but none succeeded
        print(f"  No text-based subtitle streams could be successfully extracted as SRT from the selection.")
    return extracted_count > 0


def _package_single_subtitle_to_mkv(video_path, stream_info, subtitle_order_num, video_basename):
    """
    Packages a single subtitle stream into its own MKV file (subtitle track only).
    Returns: True if successful, False otherwise.
    """
    # Use subtitle_order_num for 1-based numbering in filename for this batch of non-text subs
    output_mkv_filename = _generate_subtitle_filename(video_basename, stream_info, subtitle_order_num, "mkv")
    output_mkv_path = os.path.join(os.getcwd(), output_mkv_filename)
    
    ffmpeg_command = [
        "ffmpeg", "-i", video_path,
        "-map", f"0:{stream_info['index']}", # Map only this specific subtitle stream
        "-c", "copy",                       # Copy the stream as-is
        "-y", # Overwrite output file without asking
        output_mkv_path
    ]

    print(f"    Packaging stream idx {stream_info['index']} ({stream_info.get('codec_name', 'unknown')}) into MKV: {output_mkv_path}")
    try:
        subprocess.run(ffmpeg_command, capture_output=True, text=True, check=True)
        print(f"      Successfully packaged to: {output_mkv_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"      Failed to package subtitle stream idx {stream_info['index']} into MKV.")
        error_msg = e.stderr.strip().splitlines()[-1] if e.stderr and e.stderr.strip() else 'Unknown FFmpeg error'
        print(f"        FFmpeg error: {error_msg}")
        return False
    except Exception as e_gen:
        print(f"      An unexpected error occurred during MKV packaging for stream idx {stream_info['index']}: {e_gen}")
        return False

# --- Main Processing Functions ---
def process_to_srt_files(video_path, video_basename):
    print(f"Mode: SRT (extracting all subtitles as SRT, best effort)")
    all_subtitle_streams_info = _probe_subtitle_streams(video_path)
    if all_subtitle_streams_info is None: # Probe failed critically
        return
    if not all_subtitle_streams_info:
        print(f"  No subtitle streams found in: {video_path}")
        return
    _extract_subtitle_streams_as_srt(video_path, all_subtitle_streams_info, video_basename)

def process_to_individual_mkv_subs(video_path, video_basename):
    print(f"Mode: MKV (packaging each subtitle into its own MKV file)")
    all_subtitle_streams_info = _probe_subtitle_streams(video_path)
    if all_subtitle_streams_info is None: return
    if not all_subtitle_streams_info:
        print(f"  No subtitle streams found in: {video_path}")
        return

    packaged_count = 0
    print(f"  Found {len(all_subtitle_streams_info)} subtitle stream(s) to package into individual MKVs...")
    for i, stream_info in enumerate(all_subtitle_streams_info):
        if _package_single_subtitle_to_mkv(video_path, stream_info, i + 1, video_basename):
            packaged_count +=1
    
    if packaged_count > 0:
        print(f"  Successfully packaged {packaged_count} subtitle stream(s) into individual MKV files.")
    elif all_subtitle_streams_info: # If attempts were made but none succeeded
        print(f"  No subtitle streams could be successfully packaged into MKV files from the selection.")


def process_hybrid(video_path, video_basename):
    print(f"Mode: HYBRID (SRT for text, individual MKV for non-text subs)")
    all_subtitle_streams_info = _probe_subtitle_streams(video_path)
    if all_subtitle_streams_info is None: return # Probe failed critically
    if not all_subtitle_streams_info:
        print(f"  No subtitle streams found in: {video_path}")
        return

    text_subs_info = []
    non_text_subs_info = []
    for stream_info in all_subtitle_streams_info:
        # Ensure codec_name exists and is lowercase for comparison
        codec_name = stream_info.get('codec_name', 'unknown').lower()
        if codec_name in KNOWN_TEXT_SUBTITLE_CODECS:
            text_subs_info.append(stream_info)
        else:
            non_text_subs_info.append(stream_info)

    # Process text-based subtitles
    if text_subs_info:
        _extract_subtitle_streams_as_srt(video_path, text_subs_info, video_basename)
    else:
        print(f"  No text-based subtitle streams found for SRT extraction.")

    # Process non-text-based subtitles
    if non_text_subs_info:
        print(f"  Found {len(non_text_subs_info)} non-text-based subtitle stream(s) for individual MKV packaging...")
        packaged_mkv_count = 0
        for i, stream_info in enumerate(non_text_subs_info):
             if _package_single_subtitle_to_mkv(video_path, stream_info, i + 1, video_basename):
                 packaged_mkv_count += 1
        
        if packaged_mkv_count > 0:
             print(f"  Successfully packaged {packaged_mkv_count} non-text subtitle stream(s) into individual MKV files.")
        elif non_text_subs_info: # If attempts were made but none succeeded
             print(f"  No non-text subtitle streams could be successfully packaged into MKV files from the selection.")
    else:
        print(f"  No non-text-based subtitle streams found for MKV packaging.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extracts or packages subtitles from video files. Default is 'hybrid' mode.",
        formatter_class=argparse.RawTextHelpFormatter # For better help text formatting
    )
    parser.add_argument(
        "-f", "--format",
        choices=['hybrid', 'srt', 'mkv'], # 'hybrid' is first for help text order
        default='hybrid', # <<<< DEFAULT BEHAVIOR SET TO HYBRID >>>>
        help=(
            "Processing mode:\n"
            "  hybrid: (Default) Smart processing. Text-based subtitles (SRT, ASS, etc.)\n"
            "          are extracted to individual .srt files. Non-text/image-based\n"
            "          subtitles (PGS, VobSub, etc.) are packaged, each into its own\n"
            "          separate .mkv file (containing only the subtitle track, copied as-is).\n\n"
            "  srt:    Extract ALL found subtitle streams to individual .srt files.\n"
            "          (Note: Extraction to .srt may fail for image-based subtitles).\n\n"
            "  mkv:    Package EACH found subtitle stream into its own separate .mkv file.\n"
            "          The MKV will contain only that single subtitle track (copied as-is)."
        )
    )
    parser.add_argument(
        "video_files_input",
        nargs='*', # 0 or more arguments
        metavar='VIDEO_FILE_OR_PATTERN',
        help="Video file(s) or glob pattern(s) to process (e.g., video.mp4, \"*.mkv\").\n"
             "If not provided, processes supported video files in the current directory."
    )

    parsed_args = parser.parse_args()
    input_items = parsed_args.video_files_input
    video_files_to_process_paths = []

    if input_items:
        for item in input_items:
            expanded_paths = glob.glob(item)
            if expanded_paths:
                for path in expanded_paths:
                    if os.path.isfile(path):
                        video_files_to_process_paths.append(os.path.abspath(path))
            elif os.path.isfile(item): # If not a glob and a file, add it directly
                video_files_to_process_paths.append(os.path.abspath(item))
            else:
                print(f"Warning: Input '{item}' is not a valid file or pattern, or did not match any files. Skipping.")
    else:
        # Default: process supported video files in the current directory
        print("No video files provided as arguments. Searching for supported video files in the current directory...")
        supported_extensions = ('.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm') # Tuple for endswith
        found_in_cwd = False
        for f_name in os.listdir('.'):
            if os.path.isfile(f_name) and f_name.lower().endswith(supported_extensions):
                video_files_to_process_paths.append(os.path.abspath(f_name))
                found_in_cwd = True
        if not found_in_cwd:
             print("No supported video files found in the current directory.")


    if not video_files_to_process_paths:
        print("No video files found to process.")
    else:
        unique_video_files = sorted(list(set(video_files_to_process_paths)))
        
        print(f"\nStarting subtitle processing (mode: {parsed_args.format.upper()})...")
        print(f"Found {len(unique_video_files)} video file(s) to process.")

        for video_file_path in unique_video_files:
            print(f"\n>>> Processing video file: {video_file_path}")
            if not os.path.exists(video_file_path):
                print(f"Error: Video file not found: {video_file_path}. Skipping.")
                continue
            
            # video_basename for output files, without original extension
            video_basename_for_output = os.path.splitext(os.path.basename(video_file_path))[0]

            if parsed_args.format == 'srt':
                process_to_srt_files(video_file_path, video_basename_for_output)
            elif parsed_args.format == 'mkv':
                process_to_individual_mkv_subs(video_file_path, video_basename_for_output)
            elif parsed_args.format == 'hybrid': # This will be the default if no -f flag
                process_hybrid(video_file_path, video_basename_for_output)
        
        print(f"\nSubtitle processing (mode: {parsed_args.format.upper()}) completed for all files.")