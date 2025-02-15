import os
import subprocess
import argparse
from typing import List

DEFAULT_LUT_PATH = r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\LUT\NBCU\5-NBCU_PQ2SDR_DL_RESOLVE17-VRT_v1.2.cube"

def process_file(input_file: str, output_dir: str, lut_path: str, embed_lut: bool) -> bool:
    """Process a single file with HDR metadata and optional LUT embedding"""
    try:
        # Validate input file
        if not os.path.isfile(input_file):
            print(f"Error: Input file not found: {input_file}")
            return False

        # Prepare output filename
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        suffix = "_HDR_CUBE" if embed_lut else "_HDR"
        output_filename = f"{base_name}{suffix}.mkv"
        
        # Create output directory if specified
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, output_filename)
        else:
            output_path = os.path.join(os.path.dirname(input_file), output_filename)

        # Build base command
        mkvmerge_command = [
            "mkvmerge",
            "-o", output_path,
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
            input_file
        ]

        # Add LUT attachment if enabled and available
        if embed_lut:
            if not os.path.exists(lut_path):
                print(f"Warning: LUT file not found at {lut_path}. Disabling LUT embedding.")
            else:
                mkvmerge_command[3:3] = [  # Insert before output path
                    "--attachment-mime-type", "application/x-cube",
                    "--attach-file", lut_path
                ]

        # Run mkvmerge
        print(f"Processing: {input_file}")
        result = subprocess.run(
            mkvmerge_command,
            capture_output=True,
            text=True,
            check=True
        )
        
        # Print results
        if result.stdout:
            print(f"Output:\n{result.stdout}")
        if result.stderr:
            print(f"Errors:\n{result.stderr}")

        print(f"Successfully created: {output_path}")
        return True

    except subprocess.CalledProcessError as e:
        print(f"Error processing {input_file}:")
        print(f"Command failed: {' '.join(e.cmd)}")
        print(f"Exit code: {e.returncode}")
        print(f"Error output:\n{e.stderr}")
        return False
    except Exception as e:
        print(f"Unexpected error processing {input_file}: {str(e)}")
        return False

def find_video_files(paths: List[str]) -> List[str]:
    """Find all video files in specified paths (files or directories)"""
    video_extensions = {'.mkv', '.mp4', '.avi', '.mov', '.wmv', '.ts', '.m2ts'}
    video_files = []

    for path in paths:
        if os.path.isfile(path):
            if os.path.splitext(path)[1].lower() in video_extensions:
                video_files.append(path)
        elif os.path.isdir(path):
            for root, _, files in os.walk(path):
                for file in files:
                    if os.path.splitext(file)[1].lower() in video_extensions:
                        video_files.append(os.path.join(root, file))
        else:
            print(f"Warning: Path not found - {path}")

    return video_files

def main():
    parser = argparse.ArgumentParser(
        description="Add HDR metadata to video files with optional LUT embedding",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        help="Input files/directories (supports wildcards)"
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
        help="Disable LUT embedding"
    )
    parser.add_argument(
        "-o", "--output-dir",
        help="Custom output directory (default: same as input file)"
    )
    parser.add_argument(
        "--mkvmerge-path",
        default="mkvmerge",
        help="Path to mkvmerge executable (default: system PATH)"
    )

    args = parser.parse_args()

    # Verify mkvmerge exists
    try:
        subprocess.run([args.mkvmerge_path, "--version"], capture_output=True, check=True)
    except Exception as e:
        print(f"Error: mkvmerge not found at '{args.mkvmerge_path}'. Please install MKVToolNix or specify correct path with --mkvmerge-path")
        return

    # Find all video files
    video_files = find_video_files(args.inputs)
    if not video_files:
        print("No video files found in specified paths")
        return

    print(f"Found {len(video_files)} video file(s) to process")
    if args.embed_lut:
        print(f"Using LUT file: {args.lut}")

    # Process files
    success_count = 0
    for file in video_files:
        if process_file(file, args.output_dir, args.lut, args.embed_lut):
            success_count += 1

    print("\nProcessing complete!")
    print(f"Successfully processed: {success_count}/{len(video_files)}")
    if success_count < len(video_files):
        print("Some files failed to process. Check error messages above.")

if __name__ == "__main__":
    main()