import subprocess
import os
import sys
import glob
import argparse
import json  # For parsing ffprobe JSON output

# Define known text-based subtitle codecs that ffmpeg can reasonably convert to SRT
KNOWN_TEXT_SUBTITLE_CODECS = [
    'srt', 'subrip',
    'ass', 'ssa',
    'webvtt',
    'mov_text', 'tx3g',
    'subviewer',
    'microdvd',
    'eia_608', 'cea608',
]


def _probe_subtitle_streams(video_path):
    ffprobe_command = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "s",
        "-show_entries", "stream=index,codec_name,tags",
        "-of", "json",
        video_path
    ]
    try:
        ffprobe_process = subprocess.run(ffprobe_command, capture_output=True, text=True, check=True)
        probe_data = json.loads(ffprobe_process.stdout)
        return probe_data.get("streams", [])
    except subprocess.CalledProcessError as e:
        print(f"  FFprobe error while probing subtitles in {video_path}:")
        error_msg = e.stderr.strip() if e.stderr else "No stderr output from ffprobe."
        print(f"    {error_msg}")
        return None
    except json.JSONDecodeError:
        print(f"  Error: Could not parse ffprobe JSON output for {video_path}.")
        return None
    except Exception as e:
        print(f"  Unexpected ffprobe error for {video_path}: {e}")
        return None


def _generate_subtitle_filename(video_basename, stream_info, subtitle_processing_order_num, extension):
    stream_index = stream_info['index']
    codec_name = stream_info.get('codec_name', 'unknown').lower()
    if codec_name == "hdmv_pgs_subtitle": codec_name = "pgs"
    if codec_name == "dvd_subtitle": codec_name = "dvdsub"

    lang_tag = stream_info.get('tags', {}).get('language', '')
    name_parts = [video_basename, f"sub{subtitle_processing_order_num}", f"idx{stream_index}"]
    if lang_tag:
        name_parts.append(lang_tag)
    name_parts.append(codec_name)

    filename_base = "_".join(name_parts)
    safe_chars = "._-"
    filename_base = "".join(c if c.isalnum() or c in safe_chars else '_' for c in filename_base)
    if len(filename_base) > 180:
        filename_base = filename_base[:180]

    return f"{filename_base}.{extension}"


def _extract_subtitle_streams_as_srt(video_path, subtitle_streams_info, video_basename):
    if not subtitle_streams_info:
        return False

    extracted_count = 0
    print(f"  Attempting to extract {len(subtitle_streams_info)} text-based stream(s) to SRT format...")
    output_dir = os.path.dirname(video_path)

    for i, stream_info in enumerate(subtitle_streams_info):
        output_srt_filename = _generate_subtitle_filename(video_basename, stream_info, i + 1, "srt")
        output_srt_path = os.path.join(output_dir, output_srt_filename)

        ffmpeg_command = [
            "ffmpeg", "-i", video_path,
            "-map", f"0:{stream_info['index']}",
            "-y",
            output_srt_path
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
            if os.path.exists(output_srt_path):
                try:
                    if os.path.getsize(output_srt_path) < 20:
                        os.remove(output_srt_path)
                        print(f"        Removed empty/failed SRT file: {output_srt_path}")
                except OSError as ose:
                    print(f"        Warning: Could not remove failed file {output_srt_path}: {ose}")

    if extracted_count > 0:
        print(f"  Successfully extracted {extracted_count} text-based subtitle stream(s) to SRT.")
    elif subtitle_streams_info:
        print(f"  No text-based subtitle streams could be successfully extracted.")
    return extracted_count > 0


def _package_single_subtitle_to_mkv(video_path, stream_info, subtitle_order_num, video_basename):
    output_mkv_filename = _generate_subtitle_filename(video_basename, stream_info, subtitle_order_num, "mkv")
    output_dir = os.path.dirname(video_path)
    output_mkv_path = os.path.join(output_dir, output_mkv_filename)

    ffmpeg_command = [
        "ffmpeg", "-i", video_path,
        "-map", f"0:{stream_info['index']}",
        "-c", "copy",
        "-y",
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
        print(f"      Unexpected MKV packaging error for idx {stream_info['index']}: {e_gen}")
        return False


def process_to_srt_files(video_path, video_basename):
    print(f"Mode: SRT")
    all_subtitle_streams_info = _probe_subtitle_streams(video_path)
    if all_subtitle_streams_info is None:
        return
    if not all_subtitle_streams_info:
        print(f"  No subtitle streams found in: {video_path}")
        return
    _extract_subtitle_streams_as_srt(video_path, all_subtitle_streams_info, video_basename)


def process_to_individual_mkv_subs(video_path, video_basename):
    print(f"Mode: MKV")
    all_subtitle_streams_info = _probe_subtitle_streams(video_path)
    if all_subtitle_streams_info is None:
        return
    if not all_subtitle_streams_info:
        print(f"  No subtitle streams found in: {video_path}")
        return

    packaged_count = 0
    for i, stream_info in enumerate(all_subtitle_streams_info):
        if _package_single_subtitle_to_mkv(video_path, stream_info, i + 1, video_basename):
            packaged_count += 1

    if packaged_count > 0:
        print(f"  Successfully packaged {packaged_count} subtitle stream(s).")


def process_hybrid(video_path, video_basename):
    print(f"Mode: HYBRID")
    all_subtitle_streams_info = _probe_subtitle_streams(video_path)
    if all_subtitle_streams_info is None:
        return
    if not all_subtitle_streams_info:
        print(f"  No subtitle streams found in: {video_path}")
        return

    text_subs_info = []
    non_text_subs_info = []
    for stream_info in all_subtitle_streams_info:
        codec_name = stream_info.get('codec_name', 'unknown').lower()
        if codec_name in KNOWN_TEXT_SUBTITLE_CODECS:
            text_subs_info.append(stream_info)
        else:
            non_text_subs_info.append(stream_info)

    if text_subs_info:
        _extract_subtitle_streams_as_srt(video_path, text_subs_info, video_basename)
    else:
        print(f"  No text-based subtitles found.")

    if non_text_subs_info:
        for i, stream_info in enumerate(non_text_subs_info):
            _package_single_subtitle_to_mkv(video_path, stream_info, i + 1, video_basename)
    else:
        print(f"  No non-text subtitles found.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extracts or packages subtitles from video files. Default is 'hybrid' mode.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "-f", "--format",
        choices=['hybrid', 'srt', 'mkv'],
        default='hybrid',
        help="Processing mode: hybrid (default), srt, or mkv."
    )
    parser.add_argument(
        "video_files_input",
        nargs='*',
        metavar='VIDEO_FILE_OR_PATTERN',
        help="Video files or patterns. If omitted, scans recursively from current directory."
    )

    parsed_args = parser.parse_args()
    input_items = parsed_args.video_files_input
    video_files_to_process_paths = []

    if input_items:
        for item in input_items:
            expanded_paths = glob.glob(item, recursive=True)
            for path in expanded_paths:
                if os.path.isfile(path):
                    video_files_to_process_paths.append(os.path.abspath(path))
    else:
        print("No video files provided. Recursively searching for supported video files...")
        supported_extensions = ('.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm')
        for root, _, files in os.walk(os.getcwd()):
            for f_name in files:
                if f_name.lower().endswith(supported_extensions):
                    full_path = os.path.join(root, f_name)
                    video_files_to_process_paths.append(os.path.abspath(full_path))

        if not video_files_to_process_paths:
            print("No supported video files found in this folder tree.")

    if not video_files_to_process_paths:
        print("No video files found to process.")
    else:
        unique_video_files = sorted(list(set(video_files_to_process_paths)))
        print(f"\nStarting subtitle processing (mode: {parsed_args.format.upper()})...")
        print(f"Found {len(unique_video_files)} video file(s) to process.")

        for video_file_path in unique_video_files:
            print(f"\n>>> Processing video file: {video_file_path}")
            if not os.path.exists(video_file_path):
                print(f"Error: File not found: {video_file_path}. Skipping.")
                continue

            video_basename_for_output = os.path.splitext(os.path.basename(video_file_path))[0]

            if parsed_args.format == 'srt':
                process_to_srt_files(video_file_path, video_basename_for_output)
            elif parsed_args.format == 'mkv':
                process_to_individual_mkv_subs(video_file_path, video_basename_for_output)
            elif parsed_args.format == 'hybrid':
                process_hybrid(video_file_path, video_basename_for_output)

        print(f"\nSubtitle processing (mode: {parsed_args.format.upper()}) completed.")
