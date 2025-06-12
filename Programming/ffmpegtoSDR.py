#!/usr/bin/env python3
import os
import glob
import subprocess
import argparse
import sys
import time
import tempfile # For temporary files

# --- Configuration ---
DEFAULT_LUT_PATH = r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\LUT\NBCU\5-NBCU_PQ2SDR_DL_RESOLVE17-VRT_v1.2.cube"
DEFAULT_OUTPUT_SUBFOLDER = "SDR_Output"
DEFAULT_VIDEO_EXTENSIONS = ["mp4", "mov", "mkv", "avi", "m2ts", "ts"]
DEFAULT_ENCODER = "h264_nvenc"
DEFAULT_QUALITY = "22"
DEFAULT_X264_PRESET = "medium"
DEFAULT_NVENC_PRESET = "medium"
DEFAULT_H264_PROFILE = "high"
DEFAULT_H264_LEVEL = "4.0"
DEFAULT_GOP_SIZE = "0"
DEFAULT_AUDIO_CODEC = "aac"
DEFAULT_AUDIO_BITRATE = "192k"
DEFAULT_OUTPUT_FORMAT = "mp4"
MKVMERGE_PATH = "mkvmerge" # Assume mkvmerge is in PATH (can be overridden by arg)

NVENC_PRESET_CHOICES = ['default', 'slow', 'medium', 'fast', 'hp', 'hq', 'bd', 'll', 'llhq', 'llhp', 'lossless', 'losslesshp', 'p1', 'p2', 'p3', 'p4', 'p5', 'p6', 'p7']
X264_PRESET_CHOICES = ['ultrafast', 'superfast', 'veryfast', 'faster', 'fast', 'medium', 'slow', 'slower', 'veryslow']
H264_PROFILE_CHOICES = ['auto', 'baseline', 'main', 'high', 'high10', 'high422', 'high444']
H264_LEVEL_CHOICES = ['auto', '1.0', '1b', '1.1', '1.2', '1.3', '2.0', '2.1', '2.2', '3.0', '3.1', '3.2', '4.0', '4.1', '4.2', '5.0', '5.1', '5.2', '6.0', '6.1', '6.2']


def run_mkvmerge_strip(original_input_path, temp_output_mkv_path):
    mkvmerge_cmd = [
        MKVMERGE_PATH, # Uses the (potentially updated) global MKVMERGE_PATH
        '-o', temp_output_mkv_path,
        '--no-global-tags',
        '--no-track-tags',
        '--no-attachments',
        '--disable-track-statistics-tags',
        # To be very sure, explicitly select only video and audio tracks.
        # This implicitly drops other track types (like data tracks carrying metadata).
        '--video-tracks', '0', # Assuming first video track is the one we want
        '--audio-tracks', '1', # Assuming first audio track is the one we want
                               # Adjust if your files have multiple video/audio streams
        original_input_path
    ]
    # If source has multiple audio tracks and you want all:
    # mkvmerge_cmd = [MKVMERGE_PATH, '-o', temp_output_mkv_path, '--no-global-tags', '--no-track-tags', original_input_path]
    # This simpler command is often enough to strip problematic container-level metadata.

    print(f"\n--- Running mkvmerge to create a clean intermediate file ---")
    # print(f"mkvmerge command: {' '.join(mkvmerge_cmd)}") # Debugging
    print(f"Outputting to: {temp_output_mkv_path}")

    try:
        process = subprocess.run(mkvmerge_cmd, capture_output=True, text=True, check=False, encoding='utf-8')
        if process.returncode == 0 or process.returncode == 1: # 1 is for warnings
            print(f"mkvmerge completed (Code: {process.returncode}). Output: {os.path.basename(temp_output_mkv_path)}")
            # if process.stdout: print("mkvmerge stdout:", process.stdout.strip()) # Can be verbose
            if process.stderr: print("mkvmerge stderr:", process.stderr.strip())
            if not os.path.exists(temp_output_mkv_path) or os.path.getsize(temp_output_mkv_path) == 0:
                print(f"ERROR: mkvmerge ran but temporary file '{temp_output_mkv_path}' was not created or is empty.")
                return False
            return True
        else:
            print(f"ERROR: mkvmerge failed (Code: {process.returncode}) for {os.path.basename(original_input_path)}.")
            print("mkvmerge stdout:", process.stdout)
            print("mkvmerge stderr:", process.stderr)
            return False
    except FileNotFoundError:
        print(f"ERROR: '{MKVMERGE_PATH}' command not found. Make sure mkvtoolnix is installed and mkvmerge is in your system's PATH, or use --mkvmerge_path argument.")
        return False
    except Exception as e:
        print(f"An unexpected error occurred during mkvmerge execution: {e}")
        return False


def convert_video(input_file_path_for_ffmpeg, output_file_path, lut_path,
                  encoder, quality, x264_preset, nvenc_preset,
                  h264_profile, h264_level, gop_size,
                  audio_codec, audio_bitrate, output_format):
    if not os.path.exists(lut_path):
        print(f"ERROR: LUT file not found at '{lut_path}'")
        return False

    lut_filter_path = lut_path.replace('\\', '\\\\').replace(':', '\\:')

    ffmpeg_cmd = [
        'ffmpeg', '-y',
        '-i', input_file_path_for_ffmpeg,
        '-map_metadata', '-1', 
        '-vf', (
            f'lut3d=file=\'{lut_filter_path}\','
            'zscale=t=bt709:m=bt709:p=bt709,format=yuv420p'
        ),
        '-color_primaries', 'bt709',
        '-colorspace', 'bt709',
        '-color_trc', 'bt709',
        '-color_range', 'tv',
    ]

    if encoder == 'h264_nvenc':
        nvenc_specific_opts_list = []
        if h264_profile.lower() != 'auto': nvenc_specific_opts_list.extend(['-profile:v', h264_profile])
        if h264_level.lower() != 'auto': nvenc_specific_opts_list.extend(['-level:v', h264_level])
        if int(gop_size) > 0: nvenc_specific_opts_list.extend(['-g', str(gop_size)])

        ffmpeg_cmd.extend(['-c:v', 'h264_nvenc', '-cq', str(quality), '-preset:v', nvenc_preset])
        ffmpeg_cmd.extend(nvenc_specific_opts_list)
        
        print(f"Using NVENC CQ:{quality}, Preset:{nvenc_preset}, Profile:{h264_profile}, Level:{h264_level}, GOP:{gop_size or 'auto'}")
        print("INFO: (FFmpeg) Discarding source metadata with -map_metadata -1. Using zscale for SDR stream.")
        # Relying on mkvmerge + clean input to ffmpeg + zscale + color flags to prevent HDR SEI.
        # If NVENC *still* adds HDR SEI, a BSF here would be the next step for NVENC.
        # bsf_remove_types = "6+137+144+147"
        # ffmpeg_cmd.extend(['-bsf:v', f'filter_units=remove_types={bsf_remove_types}'])
        # print(f"NVENC: Applying bitstream filter to remove HDR SEI types: {bsf_remove_types}")

    elif encoder == 'libx264':
        x264_params_list = ['colorprim=bt709', 'transfer=bt709', 'colormatrix=bt709', 'range=tv']
        libx264_opts_str = ":".join(x264_params_list)
        ffmpeg_cmd.extend(['-c:v', 'libx264', '-crf', str(quality), '-preset', x264_preset])
        if h264_profile.lower() != 'auto': ffmpeg_cmd.extend(['-profile:v', h264_profile])
        if h264_level.lower() != 'auto': ffmpeg_cmd.extend(['-level:v', h264_level])
        if int(gop_size) > 0: ffmpeg_cmd.extend(['-g', str(gop_size)])
        ffmpeg_cmd.extend(['-x264-params', libx264_opts_str])
        print(f"Using libx264 CRF:{quality}, Preset:{x264_preset}, Profile:{h264_profile}, Level:{h264_level}, GOP:{gop_size or 'auto'}")
        print(f"libx264 params: {libx264_opts_str}")
        print("INFO: (FFmpeg) Discarding all source metadata using -map_metadata -1.")
    else:
        print(f"ERROR: Unsupported encoder '{encoder}'")
        return False

    ffmpeg_cmd.extend(['-pix_fmt', 'yuv420p'])
    ffmpeg_cmd.extend(['-c:a', audio_codec])
    if audio_codec != "copy": ffmpeg_cmd.extend(['-b:a', audio_bitrate])
    if output_format.lower() == "mp4": ffmpeg_cmd.extend(['-movflags', '+faststart'])
    ffmpeg_cmd.append(output_file_path)

    print(f"\n--- Running FFmpeg command ---")
    print(f"Converting: {os.path.basename(input_file_path_for_ffmpeg)} (temp)  ->  {os.path.basename(output_file_path)}")

    try:
        process = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, check=False, encoding='utf-8')
        if process.returncode == 0:
            print(f"Successfully converted: {os.path.basename(output_file_path)}")
            print("\n--- Verifying output video stream color metadata with ffprobe: ---")
            try:
                ffprobe_cmd_simple = [
                    'ffprobe', '-v', 'error',
                    '-select_streams', 'v:0',
                    '-show_entries', 'stream=color_range,color_space,color_transfer,color_primaries:stream_tags=master_display,max_cll:format=tags',
                    '-of', 'default=nw=1:nk=1',
                    output_file_path
                ]
                print("--- Quick ffprobe check (key color fields & HDR tags): ---")
                probe_process_simple = subprocess.run(ffprobe_cmd_simple, capture_output=True, text=True, check=False, encoding='utf-8')
                if probe_process_simple.stdout: print(probe_process_simple.stdout.strip())
                else: print("Could not retrieve color metadata with simple ffprobe or no specific color tags found.")
                if probe_process_simple.stderr: print("Simple ffprobe stderr:", probe_process_simple.stderr.strip())
            except FileNotFoundError: print("WARNING: ffprobe not found. Cannot verify output metadata. Ensure ffprobe is in your PATH.")
            except Exception as e_probe: print(f"WARNING: Error running ffprobe: {e_probe}")
            print("------------------------------------------------------------------\n")
            return True
        else:
            print(f"ERROR: FFmpeg failed for {os.path.basename(input_file_path_for_ffmpeg)} (return code {process.returncode}).")
            print("FFmpeg stdout:\n", process.stdout)
            print("FFmpeg stderr:\n", process.stderr)
            return False
    except FileNotFoundError:
        print("ERROR: ffmpeg command not found. Make sure FFmpeg is installed and in your system's PATH.")
        return False
    except Exception as e:
        print(f"An unexpected error occurred during FFmpeg execution: {e}")
        return False

def main():
    # --- Corrected global statement placement ---
    global MKVMERGE_PATH 
    # --- End Correction ---

    parser = argparse.ArgumentParser(
        description="Batch convert HDR to SDR using mkvmerge pre-processing and FFmpeg.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("input_items", nargs="*", help="Video file(s) or glob pattern(s) to process.\nIf empty, scans current dir for default extensions.")
    parser.add_argument("--lut", default=DEFAULT_LUT_PATH, help=f"Path to .cube LUT (default: {DEFAULT_LUT_PATH})")
    parser.add_argument("--out_subdir", default=DEFAULT_OUTPUT_SUBFOLDER, help=f"Output subfolder (default: {DEFAULT_OUTPUT_SUBFOLDER})")
    parser.add_argument("--ext", nargs="+", default=DEFAULT_VIDEO_EXTENSIONS, help=f"Extensions if no input_items (default: {' '.join(DEFAULT_VIDEO_EXTENSIONS)})")
    parser.add_argument("--encoder", default=DEFAULT_ENCODER, choices=['libx264', 'h264_nvenc'], help=f"Video encoder (default: {DEFAULT_ENCODER})")
    parser.add_argument("--quality", default=DEFAULT_QUALITY, help=f"Quality (CRF for libx264, CQ for NVENC) (default: {DEFAULT_QUALITY})")
    parser.add_argument("--x264_preset", default=DEFAULT_X264_PRESET, choices=X264_PRESET_CHOICES, help=f"Preset for libx264 (default: {DEFAULT_X264_PRESET})")
    parser.add_argument("--nvenc_preset", default=DEFAULT_NVENC_PRESET, choices=NVENC_PRESET_CHOICES, help=f"Preset for h264_nvenc (default: {DEFAULT_NVENC_PRESET})")
    parser.add_argument("--h264_profile", default=DEFAULT_H264_PROFILE, choices=H264_PROFILE_CHOICES, help=f"H.264 profile (default: {DEFAULT_H264_PROFILE}). 'auto' lets encoder choose.")
    parser.add_argument("--h264_level", default=DEFAULT_H264_LEVEL, choices=H264_LEVEL_CHOICES, help=f"H.264 level (default: {DEFAULT_H264_LEVEL}). 'auto' lets encoder choose.")
    parser.add_argument("--gop_size", default=DEFAULT_GOP_SIZE, type=int, help=f"Keyframe interval (GOP size). 0 for auto (default: {DEFAULT_GOP_SIZE}).")
    parser.add_argument("--acodec", default=DEFAULT_AUDIO_CODEC, choices=['aac', 'copy'], help=f"Audio codec (default: {DEFAULT_AUDIO_CODEC})")
    parser.add_argument("--abitrate", default=DEFAULT_AUDIO_BITRATE, help=f"Audio bitrate if re-encoding (default: {DEFAULT_AUDIO_BITRATE})")
    parser.add_argument("--output_format", default=DEFAULT_OUTPUT_FORMAT, choices=['mp4', 'mkv'], help=f"Output container format (default: {DEFAULT_OUTPUT_FORMAT})")
    parser.add_argument("--mkvmerge_path", default=MKVMERGE_PATH, help=f"Path to mkvmerge executable (default: '{MKVMERGE_PATH}')")

    args = parser.parse_args()
    MKVMERGE_PATH = args.mkvmerge_path # Update global from args if provided

    files_to_process_raw = []
    if not args.input_items:
        print(f"No input items specified. Scanning current directory for files with extensions: {', '.join(args.ext)}")
        current_dir = os.getcwd()
        for extension in args.ext:
            glob_pattern = os.path.join(current_dir, f"*.{extension.lstrip('.')}")
            files_to_process_raw.extend(glob.glob(glob_pattern))
    else:
        for item in args.input_items:
            expanded_items = glob.glob(item)
            if not expanded_items: print(f"Warning: No files found matching '{item}'")
            files_to_process_raw.extend(expanded_items)

    files_to_process = []
    seen_files = set()
    for f_path in files_to_process_raw:
        abs_f_path = os.path.abspath(f_path)
        if os.path.isfile(abs_f_path) and abs_f_path not in seen_files:
            files_to_process.append(abs_f_path)
            seen_files.add(abs_f_path)

    if not files_to_process:
        print("No video files found to process.")
        sys.exit(0)

    print(f"\nFound {len(files_to_process)} unique video file(s) to process:")
    for f in files_to_process: print(f"  - {f}")
    print(f"LUT: {args.lut}, Encoder: {args.encoder}, Output Format: {args.output_format}")
    if args.encoder == 'h264_nvenc':
        print(f"NVENC Quality:{args.quality}, Preset:{args.nvenc_preset}, Profile:{args.h264_profile}, Level:{args.h264_level}, GOP:{args.gop_size or 'auto'}")
    elif args.encoder == 'libx264':
        print(f"libx264 Quality:{args.quality}, Preset:{args.x264_preset}, Profile:{args.h264_profile}, Level:{args.h264_level}, GOP:{args.gop_size or 'auto'}")
    print("-" * 30)

    successful_conversions = 0
    created_output_dirs = set()

    for video_file_path_original in files_to_process:
        temp_mkv_fd, temp_mkv_path = tempfile.mkstemp(suffix='_temp_clean.mkv', dir=os.path.dirname(video_file_path_original) or '.')
        os.close(temp_mkv_fd)

        if not run_mkvmerge_strip(video_file_path_original, temp_mkv_path):
            print(f"Skipping FFmpeg conversion for {os.path.basename(video_file_path_original)} due to mkvmerge failure.")
            if os.path.exists(temp_mkv_path): os.remove(temp_mkv_path)
            continue

        input_for_ffmpeg = temp_mkv_path
        input_file_dir = os.path.dirname(video_file_path_original)
        base_name = os.path.basename(video_file_path_original)
        name_no_ext, _ = os.path.splitext(base_name)
        output_folder_path = os.path.join(input_file_dir, args.out_subdir)

        if output_folder_path not in created_output_dirs:
            try:
                os.makedirs(output_folder_path, exist_ok=True)
                created_output_dirs.add(output_folder_path)
                print(f"Ensured output directory exists: {output_folder_path}")
            except OSError as e:
                print(f"ERROR: Could not create output directory '{output_folder_path}': {e}")
                if os.path.exists(temp_mkv_path): os.remove(temp_mkv_path)
                continue
        
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        output_file_name = f"{name_no_ext}_SDR_{timestamp}.{args.output_format.lstrip('.')}"
        output_file_path = os.path.join(output_folder_path, output_file_name)

        if os.path.abspath(video_file_path_original) == os.path.abspath(output_file_path):
            print(f"ERROR: Input and output paths are identical for '{video_file_path_original}'. Skipping.")
            if os.path.exists(temp_mkv_path): os.remove(temp_mkv_path)
            continue
        if os.path.exists(output_file_path): 
            print(f"Skipping '{base_name}', output file '{output_file_name}' already exists.")
            if os.path.exists(temp_mkv_path): os.remove(temp_mkv_path)
            continue

        if convert_video(input_for_ffmpeg, output_file_path, args.lut,
                         args.encoder, args.quality, args.x264_preset, args.nvenc_preset,
                         args.h264_profile, args.h264_level, str(args.gop_size),
                         args.acodec, args.abitrate, args.output_format):
            successful_conversions += 1
        
        if os.path.exists(temp_mkv_path):
            try:
                os.remove(temp_mkv_path)
                print(f"Removed temporary file: {temp_mkv_path}")
            except OSError as e:
                print(f"Warning: Could not remove temporary file '{temp_mkv_path}': {e}")

    print("-" * 30)
    if not files_to_process: print("No video files were identified for processing.")
    else: print(f"Batch processing complete. Attempted {len(files_to_process)} files. Successfully converted {successful_conversions} files.")

if __name__ == "__main__":
    main()