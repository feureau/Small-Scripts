#!/usr/bin/env python
import os
import subprocess
import argparse
import glob
import shutil  # For checking tool availability
import re      # For regex operations to remove leading number and dash
from typing import List

# --- Constants ---
DEFAULT_LUT_PATH = r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\LUT\NBCU\5-NBCU_PQ2SDR_DL_RESOLVE17-VRT_v1.2.cube"
# The output folder is now fixed to "HDR"
DEFAULT_OUTPUT_FOLDER = "HDR"

# --- Function Definitions ---

def process_file(input_file: str, output_dir: str, lut_path: str, embed_lut: bool, rotation: int, mkvmerge_path: str, ffmpeg_path: str) -> bool:
    """
    Process a single file with HDR metadata, optional LUT embedding, and optional rotation.
    Uses mkvmerge for HDR/LUT and ffmpeg for rotation.
    """
    mkv_success = False
    rotation_applied = (rotation == 0)  # Consider rotation successful if 0 (not needed)

    try:
        if not os.path.isfile(input_file):
            print(f"Error: Input file not found: {input_file}")
            return False

        # Get base name from input file, remove any leading number and dash (e.g., '01-')
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        base_name = re.sub(r'^\d+-', '', base_name)
        # Do not add any suffix; simply use the base name with .mkv extension.
        output_filename = f"{base_name}.mkv"
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, output_filename)
        # Define a name for the intermediate file *after* mkvmerge succeeds
        intermediate_path = output_path + ".intermediate"

        # --- Step 1: mkvmerge processing ---
        mkvmerge_command = [
            mkvmerge_path,
            "-o", output_path,  # Output directly to final name initially
            "--colour-matrix", "0:9",
            "--colour-range", "0:1",
            "--colour-transfer-characteristics", "0:16",
            "--colour-primaries", "0:9",
            "--max-content-light", "0:1000",
            "--max-frame-light", "0:300",
            "--max-luminance", "0:1000",
            "--min-luminance", "0:0.01",
            "--chromaticity-coordinates", "0:0.68,0.32,0.265,0.690,0.15,0.06",
            "--white-colour-coordinates", "0:0.3127,0.3290",
        ]
        if embed_lut:
            if not os.path.exists(lut_path):
                print(f"Warning: LUT file not found at {lut_path}. Disabling LUT embedding for {input_file}.")
            else:
                mkvmerge_command.extend([
                    "--attachment-name", os.path.basename(lut_path),  # Give attachment a name
                    "--attachment-mime-type", "application/x-cube",
                    "--attach-file", lut_path
                ])
        mkvmerge_command.append(input_file)  # Add input file at the end

        print(f"Processing (mkvmerge): {input_file} -> {output_filename}")
        result_mkv = subprocess.run(
            mkvmerge_command,
            capture_output=True,
            text=True,
            check=True,  # Raise error on failure
            encoding='utf-8',  # Specify encoding
            errors='replace'  # Handle potential encoding errors in output
        )

        # Print mkvmerge warnings/errors if any
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
        # Clean up potentially incomplete output file
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except OSError as rm_err:
                print(f"Warning: Could not remove incomplete output file {output_path}: {rm_err}")
        return False  # mkvmerge step failed, cannot proceed
    except Exception as e:
        print(f"Unexpected error during mkvmerge processing of {input_file}: {str(e)}")
        return False  # mkvmerge step failed

    # --- Step 2: ffmpeg rotation (only if mkvmerge succeeded and rotation requested) ---
    if mkv_success and rotation != 0 and ffmpeg_path:  # Also check if ffmpeg path is valid
        # Rename the successful mkvmerge output to the intermediate name
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
                "-i", intermediate_path,  # INPUT is the intermediate file
                "-map", "0",              # Ensure all streams are mapped
                "-c", "copy",             # Copy all codecs
                "-metadata:s:v:0", f"rotate={rotation}",  # Add rotation metadata
                output_path               # OUTPUT is the final desired filename (ending in .mkv)
            ]

            result_ff = subprocess.run(
                ffmpeg_command,
                capture_output=True,
                text=True,
                check=True,  # Raise error on failure
                encoding='utf-8',
                errors='replace'
            )

            # Print ffmpeg output/warnings if any
            if result_ff.stderr:
                 print(f"ffmpeg Output/Warnings:\n{result_ff.stderr}")

            # If ffmpeg succeeded, remove the intermediate file
            print(f"Successfully applied rotation to: {output_path}")
            try:
                os.remove(intermediate_path)
                print(f"Removed intermediate file: {intermediate_path}")
            except OSError as rm_err:
                print(f"Warning: Could not remove intermediate file {intermediate_path}: {rm_err}")
            rotation_applied = True

        except subprocess.CalledProcessError as e:
            print(f"Error applying rotation using ffmpeg (intermediate input: {intermediate_path}):")
            print(f"Command failed: {' '.join(e.cmd)}")
            print(f"Exit code: {e.returncode}")
            stderr_decoded = e.stderr if isinstance(e.stderr, str) else e.stderr.decode('utf-8', errors='replace')
            print(f"Error output:\n{stderr_decoded}")
            print(f"Warning: Rotation failed.")
            rotation_applied = False
            # Attempt to restore the original mkvmerge output
            try:
                if os.path.exists(output_path):  # Delete potentially incomplete ffmpeg output
                    os.remove(output_path)
                os.rename(intermediate_path, output_path)  # Rename intermediate back to final
                print(f"Restored original (non-rotated) file: {output_path}")
            except OSError as restore_err:
                print(f"CRITICAL WARNING: Could not restore original file from {intermediate_path}: {restore_err}")
                print(f"The intermediate file may still exist, but the final output {output_path} might be missing or incomplete.")
        except Exception as e:
            print(f"Unexpected error during ffmpeg rotation of {intermediate_path}: {str(e)}")
            print(f"Warning: Rotation failed.")
            rotation_applied = False
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
    video_files = set()  # Use a set to avoid duplicates
    for pattern in paths:
        # Use glob to handle wildcards in the pattern itself, search recursively
        expanded_paths = glob.glob(pattern, recursive=True)
        # Handle case where pattern is a single file/dir not matched by glob (e.g., no wildcard used)
        if not expanded_paths and os.path.exists(pattern):
             expanded_paths = [pattern]

        for path in expanded_paths:
            # Make path absolute for consistency and easier handling
            abs_path = os.path.abspath(path)
            if os.path.isfile(abs_path):
                if os.path.splitext(abs_path)[1].lower() in video_extensions:
                    video_files.add(abs_path)
            elif os.path.isdir(abs_path):
                for root, _, files in os.walk(abs_path):
                    for file in files:
                        if os.path.splitext(file)[1].lower() in video_extensions:
                            video_files.add(os.path.abspath(os.path.join(root, file)))

    return sorted(list(video_files))  # Return sorted list


def main():
    parser = argparse.ArgumentParser(
        description="Add HDR metadata and optional rotation to video files using mkvmerge and ffmpeg.",
        formatter_class=argparse.RawTextHelpFormatter
    )
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
    # Optionally, you can remove the --output-dir argument as the output folder is now fixed.
    # parser.add_argument(
    #     "-o", "--output-dir",
    #     help="Custom output directory"
    # )
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
    if args.rotate != 0:  # Only check for ffmpeg if rotation is actually needed
        ffmpeg_exe = shutil.which(args.ffmpeg_path)
        if not ffmpeg_exe:
             print(f"Error: Rotation ({args.rotate} deg) requested, but ffmpeg not found using path '{args.ffmpeg_path}'.")
             print("Please install ffmpeg, specify the correct path with --ffmpeg-path, or use --rotate 0.")
             return
        else:
             args.ffmpeg_path = ffmpeg_exe
             print(f"Using ffmpeg: {args.ffmpeg_path}")

    # --- Find Input Files ---
    if not args.inputs:
        print("No input paths provided. Searching current directory and subdirectories...")
        args.inputs = ['.']

    video_files = find_video_files(args.inputs)
    if not video_files:
        print("No video files found matching the specified inputs.")
        return

    # --- Force Output Directory to "HDR" ---
    output_dir_abs = os.path.abspath(os.path.join(os.getcwd(), "HDR"))
    print(f"\nFound {len(video_files)} video file(s) to process.")
    print(f"Output directory: {output_dir_abs}")
    print(f"Processing mode: {'HDR with LUT' if args.embed_lut else 'HDR only'}")
    if args.rotate != 0 and ffmpeg_exe:
        print(f"Rotation requested: {args.rotate} degrees (using ffmpeg)")
    elif args.rotate != 0 and not ffmpeg_exe:
         print(f"Rotation requested ({args.rotate}) but ffmpeg not found/validated. Rotation will be skipped.")
    else:
        print("Rotation: None")

    # --- Process Files ---
    success_count = 0
    total_files = len(video_files)
    for i, file in enumerate(video_files, 1):
        print(f"\n--- Processing file {i}/{total_files} ---")
        if process_file(file, output_dir_abs, args.lut, args.embed_lut, args.rotate, args.mkvmerge_path, ffmpeg_exe):
            success_count += 1
        print("-" * 40)

    print("\nProcessing complete!")
    print(f"Successfully processed (mkvmerge step): {success_count}/{total_files}")
    if success_count < total_files:
        print("Some files failed during the mkvmerge step. Check error messages above.")

if __name__ == "__main__":
    main()
