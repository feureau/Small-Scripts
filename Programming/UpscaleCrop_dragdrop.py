import os
import sys
import subprocess

def get_video_resolution(file_path):
    """Detect the resolution of the input video using ffprobe."""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error", "-select_streams", "v:0",
                "-show_entries", "stream=width,height", "-of", "csv=p=0", file_path
            ],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True
        )
        width, height = map(int, result.stdout.strip().split(","))
        return width, height
    except Exception as e:
        print(f"Error detecting resolution: {e}")
        return None, None

def apply_hdr_settings(file_path):
    """Apply HDR settings using mkvmerge and delete the original file if successful."""
    hdr_file = os.path.splitext(file_path)[0] + "_HDR_CUBE.mkv"
    lut_path = r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\LUT\Colorspace LUTS\5-NBCU_PQ2SDR_DL_RESOLVE17-VRT_v1.2.cube"
    try:
        if not os.path.exists(lut_path):
            raise FileNotFoundError(f"LUT file not found: {lut_path}")

        cmd = [
            "mkvmerge.exe", "-o", hdr_file,
            "--colour-matrix", "0:9", "--colour-range", "0:1",
            "--colour-transfer-characteristics", "0:16", "--colour-primaries", "0:9",
            "--max-content-light", "0:1000", "--max-frame-light", "0:300",
            "--max-luminance", "0:1000", "--min-luminance", "0:0.01",
            "--chromaticity-coordinates", "0:0.68,0.32,0.265,0.690,0.15,0.06",
            "--white-colour-coordinates", "0:0.3127,0.3290",
            "--attachment-mime-type", "application/x-cube",
            "--attach-file", lut_path,
            file_path
        ]

        print("Applying HDR settings with command:", " ".join(cmd))
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        print("mkvmerge stdout:", result.stdout)
        print("mkvmerge stderr:", result.stderr)

        if result.returncode != 0:
            raise Exception(f"mkvmerge failed: {result.stderr.strip()}")

        print(f"HDR settings applied to {hdr_file}.")

        # Delete the original file if HDR was applied successfully
        if os.path.exists(hdr_file):
            try:
                os.remove(file_path)
                print(f"Deleted original file: {file_path}")
            except Exception as delete_error:
                print(f"Error deleting original file: {delete_error}")
        else:
            print(f"HDR file not created, original file retained: {file_path}")

        return hdr_file
    except Exception as e:
        print(f"Error applying HDR settings: {e}")
        return file_path

def main():
    # Ensure there are files dragged to the script
    if len(sys.argv) <= 1:
        print("Drag and drop video files onto this script to process them.")
        return

    # Parse user options
    resolution = input("Enter resolution (4k, 8k, 1 for 4k, 2 for 8k) [Default: 8k]: ") or "8k"
    resolution = resolution.replace("1", "4k").replace("2", "8k").lower()
    if resolution not in ["4k", "8k"]:
        resolution = "8k"
    
    upscale_only = input("Do you want to upscale only? (y/n/1/0) [Default: y]: ") or "y"
    upscale_only = upscale_only.replace("1", "y").replace("0", "n").lower()
    if upscale_only not in ["y", "n"]:
        upscale_only = "y"
    
    vertical_crop = input("Do you want to also create vertical crop? (y/n/1/0) [Default: y]: ") or "y"
    vertical_crop = vertical_crop.replace("1", "y").replace("0", "n").lower()
    if vertical_crop not in ["y", "n"]:
        vertical_crop = "y"
    
    qvbr_value = input("Enter qvbr value (default is 18): ") or "18"
    try:
        qvbr_value = int(qvbr_value)
    except ValueError:
        qvbr_value = 18
    
    fruc_enable = input("Enable FRUC (fps=60)? (y/n/1/0) [Default: n]: ") or "n"
    fruc_enable = fruc_enable.replace("1", "y").replace("0", "n").lower()
    fruc_option = "--vpp-fruc fps=60" if fruc_enable == "y" else ""
    
    # Resolution-specific settings
    crop_value_4k = "528,0,528,0"
    crop_value_8k = "1056,0,1056,0"
    resize_algorithm_4k = "algo=nvvfx-superres,superres-mode=0"
    resize_algorithm_8k = "algo=ngx-vsr,vsr-quality=1"
    output_res_4k = "2160x2160"
    output_res_8k = "4320x4320"
    
    # Ensure output folder exists
    output_dir = resolution
    os.makedirs(output_dir, exist_ok=True)
    
    # Process each file provided as arguments
    for file_path in sys.argv[1:]:
        file_path = os.path.abspath(file_path)  # Ensure the file path is absolute
        if not os.path.isfile(file_path):
            print(f"Skipping invalid file: {file_path}")
            continue

        file_name = os.path.splitext(os.path.basename(file_path))[0]
        print(f"Processing file: {file_path}")

        input_width, input_height = get_video_resolution(file_path)
        if input_width is None or input_height is None:
            print(f"Skipping {file_path} due to resolution detection error.")
            continue

        # Resolution-specific setup
        if resolution == "4k":
            output_res = output_res_4k
            crop_value = crop_value_4k
            resize_algorithm = resize_algorithm_4k
        else:  # 8k
            output_res = output_res_8k
            crop_value = crop_value_8k
            resize_algorithm = resize_algorithm_8k
        
        intermediate_file = file_path

        # Upscale only
        if upscale_only == "y":
            output_file = os.path.join(output_dir, f"{file_name}_Up_{resolution}.mkv")
            cmd = [
                "NVEncC64", "--avhw", "--codec", "av1", "--tier", "1", "--profile", "high",
                "--qvbr", str(qvbr_value), "--preset", "p1", "--output-depth", "10", "--multipass", "2pass-full",
                "--aq", "--aq-temporal", "--aq-strength", "0", "--lookahead", "32", "--lookahead-level", "auto",
                "--transfer", "auto", "--audio-copy", "--chapter-copy", "--key-on-chapter", "--sub-copy",
                "--metadata", "copy",
                "--vpp-resize", resize_algorithm, "--output-res", f"{output_res},preserve_aspect_ratio=increase",
                "-i", intermediate_file, "-o", output_file
            ]
            if fruc_option:  # Add FRUC option only if enabled
                cmd.extend(fruc_option.split())
            print("Executing command:", " ".join(cmd))
            subprocess.run(cmd, check=True)
            # Apply HDR settings
            output_file = apply_hdr_settings(output_file)
            print(f"Upscale-only conversion completed for {file_path}.")

        # Vertical crop
        if vertical_crop == "y":
            output_file = os.path.join(output_dir, f"{file_name}_Crop_{resolution}.mkv")
            cmd = [
                "NVEncC64", "--avhw", "--codec", "av1", "--tier", "1", "--profile", "high",
                "--qvbr", str(qvbr_value), "--preset", "p1", "--output-depth", "10", "--multipass", "2pass-full",
                "--aq", "--aq-temporal", "--aq-strength", "0", "--lookahead", "32", "--lookahead-level", "auto",
                "--transfer", "auto", "--audio-copy", "--chapter-copy", "--key-on-chapter", "--sub-copy",
                "--metadata", "copy", "--crop", crop_value,
                "--vpp-resize", resize_algorithm, "--output-res", f"{output_res},preserve_aspect_ratio=increase",
                "-i", intermediate_file, "-o", output_file
            ]
            if fruc_option:  # Add FRUC option only if enabled
                cmd.extend(fruc_option.split())
            print("Executing command:", " ".join(cmd))
            subprocess.run(cmd, check=True)
            # Apply HDR settings
            output_file = apply_hdr_settings(output_file)
            print(f"Vertical crop conversion completed for {file_path}.")

    print(f"Processing complete! All resulting videos have been moved to the '{resolution}' folder.")

if __name__ == "__main__":
    main()
