#!/usr/bin/env python
import os
import subprocess
import argparse
import glob
import shutil  # For checking tool availability
import re      # For regex operations
from typing import List

# --- Constants ---
DEFAULT_LUT_PATH = r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\LUT\NBCU\5-NBCU_PQ2SDR_DL_RESOLVE17-VRT_v1.2.cube"
# The output folder is now a relative name, to be placed inside each source directory
DEFAULT_OUTPUT_FOLDER = "HDR"

# --- Function Definitions ---

def sanitize_filename(filename: str) -> str:
    """
    Sanitizes a filename by:
    1. Removing leading number and dash (e.g., '01-').
    2. Replacing illegal/problematic characters (except apostrophe) with an underscore.
    3. Removing leading/trailing whitespace and underscores.
    4. Collapsing multiple consecutive underscores into one.
    5. Providing a default name if the name becomes empty.
    """
    # 1. Remove leading number and dash
    sanitized_name = re.sub(r'^\d+-', '', filename)

    # 2. Define characters that are problematic in filenames (excluding apostrophe)
    problematic_chars_regex = r'[\\/:*?"<>|]' # Note: No apostrophe here
    sanitized_name = re.sub(problematic_chars_regex, '_', sanitized_name)

    # 3. Optional: Remove leading/trailing whitespace and underscores that might result from replacement
    sanitized_name = sanitized_name.strip(' _')

    # 4. Optional: Collapse multiple consecutive underscores into one
    sanitized_name = re.sub(r'_+', '_', sanitized_name)

    # 5. Optional: If the name becomes empty after sanitization, provide a default name.
    if not sanitized_name:
        sanitized_name = "sanitized_default_output"
        
    return sanitized_name


def process_file(input_file: str, output_dir: str, lut_path: str, embed_lut: bool, rotation: int, mkvmerge_path: str, ffmpeg_path: str) -> bool:
    """
    Process a single file with HDR metadata, optional LUT embedding, and optional rotation.
    Uses mkvmerge for HDR/LUT and ffmpeg for rotation.
    """
    mkv_success = False
    
    try:
        if not os.path.isfile(input_file):
            print(f"Error: Input file not found: {input_file}")
            return False

        original_base_name = os.path.splitext(os.path.basename(input_file))[0]
        sanitized_base_name = sanitize_filename(original_base_name)

        output_filename = f"{sanitized_base_name}.mkv"
        # The output_dir is now calculated per-file and passed in
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, output_filename)
        intermediate_path = output_path + ".intermediate"

        # --- Step 1: mkvmerge processing ---
        mkvmerge_command = [
            mkvmerge_path,
            "-o", output_path,
            "--colour-matrix", "0:9",
            "--colour-range", "0:1",
            "--colour-transfer-characteristics", "0:16",
            "--colour-primaries", "0:9",
            "--max-content-light", "0:1000",
            "--max-frame-light", "0:400",
            "--max-luminance", "0:1000",
            "--min-luminance", "0:0.0001",
            "--chromaticity-coordinates", "0:0.708,0.292,0.170,0.797,0.131,0.046",
            "--white-colour-coordinates", "0:0.3127,0.3290",
        ]

        if embed_lut:
            if not os.path.exists(lut_path):
                print(f"Warning: LUT file not found at {lut_path}. Disabling LUT embedding for {input_file}.")
            else:
                mkvmerge_command.extend([
                    "--attachment-name", os.path.basename(lut_path),
                    "--attachment-mime-type", "application/x-cube",
                    "--attach-file", lut_path
                ])
        mkvmerge_command.append(input_file)

        # <-- CHANGE START: Improved print statement for clarity -->
        print(f"Processing (mkvmerge): '{os.path.basename(input_file)}' -> '{output_path}'")
        # <-- CHANGE END -->
        
        result_mkv = subprocess.run(
            mkvmerge_command,
            capture_output=True,
            text=True,
            check=True,
            encoding='utf-8',
            errors='replace'
        )

        if result_mkv.stderr:
             print(f"mkvmerge Warnings/Errors:\n{result_mkv.stderr}")

        print(f"Successfully created base MKV: {output_path}")
        mkv_success = True

    except subprocess.CalledProcessError as e:
        print(f"Error processing {input_file} with mkvmerge:")
        print(f"Command failed: {' '.join(e.cmd)}")
        print(f"Exit code: {e.returncode}")
        stderr_decoded = e.stderr if isinstance(e.stderr, str) else e.stderr.decode('utf-8', errors='replace')
        print(f"Error output:\n{stderr_decoded}")
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except OSError as rm_err:
                print(f"Warning: Could not remove incomplete output file {output_path}: {rm_err}")
        return False
    except Exception as e:
        print(f"Unexpected error during mkvmerge processing of {input_file}: {str(e)}")
        return False

    # --- Step 2: ffmpeg rotation (only if mkvmerge succeeded and rotation requested) ---
    if mkv_success and rotation != 0 and ffmpeg_path:
        try:
            print(f"Renaming {output_path} to {intermediate_path} for rotation step.")
            os.rename(output_path, intermediate_path)
        except OSError as rename_err:
            print(f"Error: Could not rename file for rotation step: {rename_err}")
            print(f"Warning: Skipping rotation for {output_path}. File remains as created by mkvmerge.")
            return mkv_success

        print(f"Applying rotation ({rotation} degrees) using ffmpeg...")
        try:
            ffmpeg_command = [
                ffmpeg_path,
                "-i", intermediate_path,
                "-map", "0",
                "-c", "copy",
                "-metadata:s:v:0", f"rotate={rotation}",
                output_path
            ]

            result_ff = subprocess.run(
                ffmpeg_command,
                capture_output=True,
                text=True,
                check=True,
                encoding='utf-8',
                errors='replace'
            )

            if result_ff.stderr:
                 print(f"ffmpeg Output/Warnings:\n{result_ff.stderr}")

            print(f"Successfully applied rotation to: {output_path}")
            try:
                os.remove(intermediate_path)
                print(f"Removed intermediate file: {intermediate_path}")
            except OSError as rm_err:
                print(f"Warning: Could not remove intermediate file {intermediate_path}: {rm_err}")

        except subprocess.CalledProcessError as e:
            print(f"Error applying rotation using ffmpeg (intermediate input: {intermediate_path}):")
            print(f"Command failed: {' '.join(e.cmd)}")
            print(f"Exit code: {e.returncode}")
            stderr_decoded = e.stderr if isinstance(e.stderr, str) else e.stderr.decode('utf-8', errors='replace')
            print(f"Error output:\n{stderr_decoded}")
            print(f"Warning: Rotation failed.")
            try:
                if os.path.exists(output_path):
                    os.remove(output_path)
                os.rename(intermediate_path, output_path)
                print(f"Restored original (non-rotated) file: {output_path}")
            except OSError as restore_err:
                print(f"CRITICAL WARNING: Could not restore original file from {intermediate_path}: {restore_err}")
        except Exception as e:
            print(f"Unexpected error during ffmpeg rotation of {intermediate_path}: {str(e)}")
            print(f"Warning: Rotation failed.")
            try:
                if os.path.exists(output_path):
                    os.remove(output_path)
                os.rename(intermediate_path, output_path)
                print(f"Restored original (non-rotated) file: {output_path}")
            except OSError as restore_err:
                print(f"CRITICAL WARNING: Could not restore original file from {intermediate_path}: {restore_err}")

    return mkv_success


def find_video_files(paths: List[str]) -> List[str]:
    """Find all video files in specified paths (supports wildcards and directories)"""
    video_extensions = {'.mkv', '.mp4', '.avi', '.mov', '.wmv', '.ts', '.m2ts'}
    video_files = set()
    for pattern in paths:
        expanded_paths = glob.glob(pattern, recursive=True)
        if not expanded_paths and os.path.exists(pattern):
             expanded_paths = [pattern]

        for path in expanded_paths:
            abs_path = os.path.abspath(path)
            if os.path.isfile(abs_path):
                if os.path.splitext(abs_path)[1].lower() in video_extensions:
                    video_files.add(abs_path)
            elif os.path.isdir(abs_path):
                for root, _, files in os.walk(abs_path):
                    for file in files:
                        if os.path.splitext(file)[1].lower() in video_extensions:
                            video_files.add(os.path.abspath(os.path.join(root, file)))

    return sorted(list(video_files))


def main():
    parser = argparse.ArgumentParser(
        description="Add HDR metadata and optional rotation to video files using mkvmerge and ffmpeg.\n"
                    "Creates an 'HDR' subfolder within each source file's directory for the output.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    # ... (rest of parser arguments are unchanged)
    parser.add_argument(
        "inputs",
        nargs="*",
        help="Input files/directories (supports wildcards like *.mp4 or folder/**.mkv)\n"
             "If none provided, processes all video files in current directory and subfolders."
    )
    parser.add_argument(
        "--lut",
        default=DEFAULT_LUT_PATH,
        help=f"Custom LUT file path (default: {DEFAULT_LUT_PATH})"
    )
    parser.add_argument(
        "--no-lut",
        action="store_false",
        dest="embed_lut",
        help="Add HDR metadata without LUT embedding (default: embed LUT if available)"
    )
    parser.add_argument(
        "-r", "--rotate",
        nargs='?',
        const=90,
        default=0,
        metavar='ANGLE',
        help="Rotation angle (degrees) to add as metadata using ffmpeg.\n"
             "Allowed: 0, 90, 180, 270.\n"
             "If flag is present without a value (-r), defaults to 90.\n"
             "If flag is absent, defaults to 0 (no rotation)."
    )
    parser.add_argument(
        "--mkvmerge-path",
        default="mkvmerge",
        help="Path to mkvmerge executable (default: check system PATH)"
    )
    parser.add_argument(
        "--ffmpeg-path",
        default="ffmpeg",
        help="Path to ffmpeg executable (default: check system PATH). Required if rotation is applied."
    )
    args = parser.parse_args()

    # --- Manually Validate Rotation Argument ---
    valid_rotations = [0, 90, 180, 270]
    try:
        rotation_angle = int(args.rotate)
        if rotation_angle not in valid_rotations:
            parser.error(f"argument -r/--rotate: invalid choice: {args.rotate} (choose from {', '.join(map(str, valid_rotations))})")
        args.rotate = rotation_angle
    except ValueError:
        parser.error(f"argument -r/--rotate: invalid integer value: '{args.rotate}'")
    except TypeError:
        parser.error(f"argument -r/--rotate: unexpected value type processing '{args.rotate}'")

    # --- Verify Tool Paths ---
    mkvmerge_exe = shutil.which(args.mkvmerge_path)
    if not mkvmerge_exe:
        print(f"Error: mkvmerge not found using path '{args.mkvmerge_path}'.")
        print("Please install MKVToolNix or specify the correct path with --mkvmerge-path")
        return
    else:
        args.mkvmerge_path = mkvmerge_exe
        print(f"Using mkvmerge: {args.mkvmerge_path}")

    ffmpeg_exe = None
    if args.rotate != 0:
        ffmpeg_exe_check = shutil.which(args.ffmpeg_path)
        if not ffmpeg_exe_check:
             print(f"Error: Rotation ({args.rotate} deg) requested, but ffmpeg not found using path '{args.ffmpeg_path}'.")
             print("Please install ffmpeg, specify the correct path with --ffmpeg-path, or use --rotate 0.")
             return
        else:
             args.ffmpeg_path = ffmpeg_exe_check
             ffmpeg_exe = args.ffmpeg_path
             print(f"Using ffmpeg: {args.ffmpeg_path}")
    else:
        args.ffmpeg_path = None

    # --- Find Input Files ---
    if not args.inputs:
        print("No input paths provided. Searching current directory and subdirectories...")
        args.inputs = ['.']

    video_files = find_video_files(args.inputs)
    if not video_files:
        print("No video files found matching the specified inputs.")
        return

    # <-- CHANGE START: Removed the old fixed output directory logic -->
    # The output directory will now be determined on a per-file basis inside the loop.
    print(f"\nFound {len(video_files)} video file(s) to process.")
    print(f"Outputting to an '{DEFAULT_OUTPUT_FOLDER}' subfolder within each source directory.")
    print(f"Processing mode: {'HDR with LUT' if args.embed_lut else 'HDR only'}")
    # <-- CHANGE END -->
    
    if args.rotate != 0 and ffmpeg_exe:
        print(f"Rotation requested: {args.rotate} degrees (using ffmpeg)")
    elif args.rotate != 0 and not ffmpeg_exe:
         print(f"Rotation requested ({args.rotate}) but ffmpeg not found/validated. Rotation will be skipped.")
    else:
        print("Rotation: None")

    # --- Process Files ---
    success_count = 0
    total_files = len(video_files)
    for i, file_path in enumerate(video_files, 1):
        print(f"\n--- Processing file {i}/{total_files} ---")

        # <-- CHANGE START: Per-file output directory calculation -->
        # Get the directory where the source file is located.
        source_directory = os.path.dirname(file_path)
        # Create the path for the 'HDR' subfolder within that source directory.
        output_dir_for_file = os.path.join(source_directory, DEFAULT_OUTPUT_FOLDER)
        # <-- CHANGE END -->
        
        # Pass the dynamically determined output directory to the processing function
        if process_file(file_path, output_dir_for_file, args.lut, args.embed_lut, args.rotate, args.mkvmerge_path, ffmpeg_exe):
            success_count += 1
        print("-" * 40)

    print("\nProcessing complete!")
    print(f"Successfully processed (mkvmerge step): {success_count}/{total_files}")
    if success_count < total_files:
        print("Some files may have failed during mkvmerge or rotation steps. Check error messages above.")

if __name__ == "__main__":
    main()