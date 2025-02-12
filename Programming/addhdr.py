import os
import subprocess
import shutil
import argparse

def add_hdr_metadata(input_file, embed_cube_lut=True):
    """Adds HDR metadata to an MKV file using mkvmerge and optionally embeds a .cube LUT.
       Output MKV file is placed in the same directory as the input file.
    """

    lut_path = r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\LUT\Colorspace LUTS\5-NBCU_PQ2SDR_DL_RESOLVE17-VRT_v1.2.cube" # Raw string for Windows paths

    output_filename_base = os.path.splitext(os.path.basename(input_file))[0]
    if embed_cube_lut:
        output_filename = f"{output_filename_base}_HDR_CUBE.mkv"
    else:
        output_filename = f"{output_filename_base}_HDR.mkv"

    output_path = os.path.join(os.path.dirname(input_file), output_filename) # Output in the same directory as input

    mkvmerge_command = [
        "mkvmerge.exe",
        "-o", output_filename,  # Output filename only, will be created in current directory
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
        os.path.basename(input_file)  # Use basename here
    ]

    print(f"Processing: {input_file}")
    print(f"Output file: {output_path}")

    try:
        print("Running mkvmerge for HDR metadata...")
        result = subprocess.run(mkvmerge_command, capture_output=True, text=True, check=True, cwd=os.path.dirname(input_file))  # Run in input file's directory
        print(result.stdout)
        if result.stderr:
            print(f"mkvmerge STDERR:\n{result.stderr}")

        if embed_cube_lut:
            if not os.path.exists(lut_path):
                print(f"Warning: LUT file not found at: {lut_path}. Skipping LUT embedding.")
            else:
                print("Running mkvmerge to embed CUBE LUT...")
                lut_mkvmerge_command = [
                    "mkvmerge.exe",
                    "-o", output_filename,  # Output filename only, in current directory
                    "--attachment-mime-type", "application/x-cube",
                    "--attach-file", lut_path,
                    output_filename,  # Input is the already created HDR MKV file in the same directory
                    "--no-video", "--no-audio", "--no-subtitles", "--no-chapters", "--no-attachments"
                ]
                result_lut = subprocess.run(lut_mkvmerge_command, capture_output=True, text=True, check=True, cwd=os.path.dirname(input_file))  # Run in input file's directory
                print(result_lut.stdout)
                if result_lut.stderr:
                    print(f"mkvmerge LUT STDERR:\n{result_lut.stderr}")

        print("Running mkvinfo...")
        mkvinfo_command = ["mkvinfo.exe", output_filename]
        result_info = subprocess.run(mkvinfo_command, capture_output=True, text=True, cwd=os.path.dirname(input_file))  # Run in input file's directory # Don't check=True for info, just warn
        print(result_info.stdout)
        if result_info.stderr:
            print(f"mkvinfo STDERR:\n{result_info.stderr}")

        # No need to create folder or move, output is already in the same directory

    except subprocess.CalledProcessError as e:
        print(f"Error processing {input_file}: mkvmerge failed with return code {e.returncode}")
        if e.stderr:
            print(f"STDERR:\n{e.stderr}")
        if e.stdout:
            print(f"STDOUT:\n{e.stdout}")
        print("-" * 30)  # Separator for errors
        return False  # Indicate failure

    except Exception as e:
        print(f"An unexpected error occurred while processing {input_file}: {e}")
        print("-" * 30)  # Separator for errors
        return False  # Indicate failure

    return True  # Indicate success


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Add HDR metadata to video files and optionally embed a .cube LUT.")
    parser.add_argument("-nocube", action="store_true", help="Disable embedding the .cube LUT.")
    args = parser.parse_args()

    video_extensions = ['.mkv', '.mp4', '.avi', '.mov', '.wmv', '.ts', '.m2ts']  # Add more if needed
    processed_count = 0
    error_count = 0

    print("Starting HDR metadata processing...")
    if args.nocube:
        print("Cube LUT embedding is disabled.")
    else:
        print("Cube LUT embedding is enabled (default).")

    for root, _, files in os.walk('.'):  # Start from current directory
        for file in files:
            if any(file.lower().endswith(ext) for ext in video_extensions):
                input_file_path = os.path.join(root, file)
                if add_hdr_metadata(input_file_path, embed_cube_lut=not args.nocube):
                    processed_count += 1
                else:
                    error_count += 1

    print("\nProcessing complete!")
    print(f"Processed files: {processed_count}")
    if error_count > 0:
        print(f"Files with errors: {error_count}")
        print("Please review the error messages above.")
    else:
        print("All files processed successfully.")

    print("Output files are in the same folders as the original files.")  # Updated message