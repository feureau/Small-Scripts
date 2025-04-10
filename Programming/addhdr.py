#!/usr/bin/env python
import os
import subprocess
import argparse
import glob
import shutil  # For checking tool availability
from typing import List

# --- Constants ---
DEFAULT_LUT_PATH = r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\LUT\NBCU\5-NBCU_PQ2SDR_DL_RESOLVE17-VRT_v1.2.cube"
DEFAULT_OUTPUT_SUBDIR = "HDR_Processed"

# --- Function Definitions ---

def process_file(input_file: str, output_dir: str, lut_path: str, embed_lut: bool, rotation: int, mkvmerge_path: str, ffmpeg_path: str) -> bool:
    """
    Process a single file with HDR metadata, optional LUT embedding, and optional rotation.
    Uses mkvmerge for HDR/LUT and ffmpeg for rotation.
    """
    mkv_success = False
    rotation_applied = (rotation == 0) # Consider rotation successful if 0 (not needed)

    try:
        if not os.path.isfile(input_file):
            print(f"Error: Input file not found: {input_file}")
            return False

        base_name = os.path.splitext(os.path.basename(input_file))[0]
        suffix = "_HDR_CUBE" if embed_lut else "_HDR"
        output_filename = f"{base_name}{suffix}.mkv"
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, output_filename)
        # Define a name for the intermediate file *after* mkvmerge succeeds
        intermediate_path = output_path + ".intermediate"

        # --- Step 1: mkvmerge processing ---
        mkvmerge_command = [
            mkvmerge_path,
            "-o", output_path, # Output directly to final name initially
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
                    "--attachment-name", os.path.basename(lut_path), # Give attachment a name
                    "--attachment-mime-type", "application/x-cube",
                    "--attach-file", lut_path
                ])
        mkvmerge_command.append(input_file) # Add input file at the end

        print(f"Processing (mkvmerge): {input_file} -> {output_filename}")
        result_mkv = subprocess.run(
            mkvmerge_command,
            capture_output=True,
            text=True,
            check=True, # Raise error on failure
            encoding='utf-8', # Specify encoding
            errors='replace' # Handle potential encoding errors in output
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
        return False # mkvmerge step failed, cannot proceed
    except Exception as e:
        print(f"Unexpected error during mkvmerge processing of {input_file}: {str(e)}")
        return False # mkvmerge step failed

    # --- Step 2: ffmpeg rotation (only if mkvmerge succeeded and rotation requested) ---
    if mkv_success and rotation != 0 and ffmpeg_path: # Also check if ffmpeg path is valid
        # Rename the successful mkvmerge output to the intermediate name
        try:
            print(f"Renaming {output_path} to {intermediate_path} for rotation step.")
            os.rename(output_path, intermediate_path)
        except OSError as rename_err:
            print(f"Error: Could not rename file for rotation step: {rename_err}")
            print(f"Warning: Skipping rotation for {output_path}. File remains as created by mkvmerge.")
            # Return True as mkvmerge succeeded, but log the issue. Rotation didn't happen.
            # No need to set rotation_applied = False here, it defaults based on rotation value
            return mkv_success

        print(f"Applying rotation ({rotation} degrees) using ffmpeg...")
        try:
            ffmpeg_command = [
                ffmpeg_path,
                "-i", intermediate_path, # INPUT is the intermediate file
                "-map", "0",             # Ensure all streams are mapped
                "-c", "copy",            # Copy all codecs
                "-metadata:s:v:0", f"rotate={rotation}", # Add rotation metadata
                output_path              # OUTPUT is the final desired filename (ending in .mkv)
            ]

            result_ff = subprocess.run(
                ffmpeg_command,
                capture_output=True,
                text=True,
                check=True, # Raise error on failure
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
                # This is not critical, but good to know
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
                if os.path.exists(output_path): # Delete potentially incomplete ffmpeg output
                    os.remove(output_path)
                os.rename(intermediate_path, output_path) # Rename intermediate back to final
                print(f"Restored original (non-rotated) file: {output_path}")
            except OSError as restore_err:
                print(f"CRITICAL WARNING: Could not restore original file from {intermediate_path}: {restore_err}")
                print(f"The intermediate file may still exist, but the final output {output_path} might be missing or incomplete.")

        except Exception as e:
            print(f"Unexpected error during ffmpeg rotation of {intermediate_path}: {str(e)}")
            print(f"Warning: Rotation failed.")
            rotation_applied = False
            # Attempt to restore the original mkvmerge output (similar logic as above)
            try:
                if os.path.exists(output_path): os.remove(output_path)
                os.rename(intermediate_path, output_path)
                print(f"Restored original (non-rotated) file: {output_path}")
            except OSError as restore_err:
                 print(f"CRITICAL WARNING: Could not restore original file from {intermediate_path}: {restore_err}")

    # Return True if mkvmerge succeeded, regardless of rotation success/failure
    return mkv_success


def find_video_files(paths: List[str]) -> List[str]:
    """Find all video files in specified paths (supports wildcards and directories)"""
    video_extensions = {'.mkv', '.mp4', '.avi', '.mov', '.wmv', '.ts', '.m2ts'}
    video_files = set() # Use a set to avoid duplicates
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
            # else: # Avoid warning if glob returns nothing for a pattern
            #     print(f"Warning: Path specified by pattern not found - {path}")

    return sorted(list(video_files)) # Return sorted list


def main():
    parser = argparse.ArgumentParser(
        description="Add HDR metadata and optional rotation to video files using mkvmerge and ffmpeg.",
        formatter_class=argparse.RawTextHelpFormatter # Allows newline characters in help text
    )
    parser.add_argument(
        "inputs",
        nargs="*", # 0 or more arguments
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
        action="store_false", # Sets embed_lut to False if flag is present
        dest="embed_lut",
        help="Add HDR metadata without LUT embedding (default: embed LUT if available)"
    )
    parser.add_argument(
        "-r", "--rotate",
        type=int,
        choices=[0, 90, 180, 270],
        default=0, # Default to 0 (no rotation)
        help="Rotation angle (degrees) to add as metadata using ffmpeg after mkvmerge.\n"
             "Requires ffmpeg. Allowed values: 0, 90, 180, 270. Default: 0 (no rotation)."
    )
    parser.add_argument(
        "-o", "--output-dir",
        help=f"Custom output directory\n(default: Create '{DEFAULT_OUTPUT_SUBDIR}' if multiple files/dirs processed,\n otherwise use current directory for single file input)"
    )
    parser.add_argument(
        "--mkvmerge-path",
        default="mkvmerge", # Assume it's in PATH by default
        help="Path to mkvmerge executable (default: check system PATH)"
    )
    parser.add_argument(
        "--ffmpeg-path",
        default="ffmpeg", # Assume it's in PATH by default
        help="Path to ffmpeg executable (default: check system PATH). Required if --rotate is not 0."
    )

    args = parser.parse_args()

    # --- Verify Tool Paths ---
    mkvmerge_exe = shutil.which(args.mkvmerge_path)
    if not mkvmerge_exe:
        print(f"Error: mkvmerge not found using path '{args.mkvmerge_path}'.")
        print("Please install MKVToolNix or specify the correct path with --mkvmerge-path")
        return
    else:
        # Update args.mkvmerge_path to the full path found, important for subprocess calls
        args.mkvmerge_path = mkvmerge_exe
        print(f"Using mkvmerge: {args.mkvmerge_path}")


    ffmpeg_exe = None
    if args.rotate != 0: # Only check for ffmpeg if rotation is requested
        ffmpeg_exe = shutil.which(args.ffmpeg_path)
        if not ffmpeg_exe:
             print(f"Error: Rotation ({args.rotate} deg) requested, but ffmpeg not found using path '{args.ffmpeg_path}'.")
             print("Please install ffmpeg, specify the correct path with --ffmpeg-path, or use --rotate 0.")
             return
        else:
             # Update args.ffmpeg_path to the full path found
             args.ffmpeg_path = ffmpeg_exe
             print(f"Using ffmpeg: {args.ffmpeg_path}")
    # No need for an else here, ffmpeg_path remains None if not needed/not found when rotate=0

    # --- Find Input Files ---
    if not args.inputs:
        print("No input paths provided. Searching current directory and subdirectories...")
        args.inputs = ['.'] # Default to current directory if no inputs given

    video_files = find_video_files(args.inputs)
    if not video_files:
        print("No video files found matching the specified inputs.")
        return

    # --- Determine Output Directory ---
    # Use absolute path for output directory
    if not args.output_dir:
        # Determine if multiple sources or a directory was specified
        multiple_sources = len(video_files) > 1
        input_was_dir = any(os.path.isdir(p) for p in args.inputs)

        if multiple_sources or input_was_dir:
            # Use default subdir if multiple files found OR if any input was a directory
             output_dir_abs = os.path.abspath(os.path.join(os.getcwd(), DEFAULT_OUTPUT_SUBDIR))
        else:
             # Use current dir if single file input and input was not a directory path
             output_dir_abs = os.path.abspath(os.getcwd())
    else:
        # Use user-provided path, make it absolute
        output_dir_abs = os.path.abspath(args.output_dir)

    print(f"\nFound {len(video_files)} video file(s) to process.")
    print(f"Output directory: {output_dir_abs}")
    print(f"Processing mode: {'HDR with LUT' if args.embed_lut else 'HDR only'}")
    if args.rotate != 0 and ffmpeg_exe: # Check ffmpeg_exe is valid here
        print(f"Rotation requested: {args.rotate} degrees (using ffmpeg)")
    else:
        print("Rotation: None")


    # --- Process Files ---
    success_count = 0
    total_files = len(video_files)
    for i, file in enumerate(video_files, 1):
        print(f"\n--- Processing file {i}/{total_files} ---")
        if process_file(file, output_dir_abs, args.lut, args.embed_lut, args.rotate, args.mkvmerge_path, ffmpeg_exe): # Pass found ffmpeg_exe path
            success_count += 1
        print("-" * 40) # Separator between files

    print("\nProcessing complete!")
    print(f"Successfully processed (mkvmerge step): {success_count}/{total_files}")
    if success_count < total_files:
        print("Some files failed during the mkvmerge step. Check error messages above.")
    # Note: Success count only reflects mkvmerge success. Rotation failures are logged as warnings during processing.

# --- Script Entry Point ---
if __name__ == "__main__":
    main()