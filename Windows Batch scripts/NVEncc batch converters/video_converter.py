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

def main():
    # Parse user options
    resolution = input("Enter resolution (4k, 8k, 1 for 4k, 2 for 8k) [Default: 8k]: ") or "8k"
    resolution = resolution.replace("1", "4k").replace("2", "8k").lower()
    if resolution not in ["4k", "8k"]:
        resolution = "8k"
    
    horizontal = input("Do you want to convert to Horizontal? (y/n/1/0) [Default: y]: ") or "y"
    horizontal = horizontal.replace("1", "y").replace("0", "n").lower()
    if horizontal not in ["y", "n"]:
        horizontal = "y"
    
    vertical = input("Do you want to convert to Vertical? (y/n/1/0) [Default: y]: ") or "y"
    vertical = vertical.replace("1", "y").replace("0", "n").lower()
    if vertical not in ["y", "n"]:
        vertical = "y"
    
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
        
        # Handle upscaling for 8K
        intermediate_file = file_path
        if resolution == "8k" and (input_width < 3840 or input_height < 2160):
            intermediate_file = os.path.join(output_dir, f"{file_name}_4k_temp.mkv")
            cmd_4k = [
                "NVEncC64", "--avhw", "--codec", "av1", "--tier", "1", "--profile", "high",
                "--qvbr", str(qvbr_value), "--preset", "p1", "--output-depth", "10", "--multipass", "2pass-full",
                "--aq", "--aq-temporal", "--aq-strength", "0", "--lookahead", "32", "--lookahead-level", "auto",
                "--transfer", "auto", "--audio-copy", "--chapter-copy", "--key-on-chapter", "--sub-copy",
                "--metadata", "copy",
                "--vpp-resize", resize_algorithm_4k, "--output-res", f"{output_res_4k},preserve_aspect_ratio=increase",
                "-i", file_path, "-o", intermediate_file
            ]
            print("Executing 4K upscale command:", " ".join(cmd_4k))
            subprocess.run(cmd_4k, check=True)
            print(f"4K upscale completed for {file_path}.")

        # Horizontal conversion
        if horizontal == "y":
            output_file = os.path.join(output_dir, f"{file_name}_Horizontal_{resolution}.mkv")
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
            print(f"Horizontal conversion completed for {file_path}.")

        # Vertical conversion
        if vertical == "y":
            output_file = os.path.join(output_dir, f"{file_name}_Vertical_{resolution}.mkv")
            cmd = [
                "NVEncC64", "--avhw", "--codec", "hevc", "--tier", "high", "--profile", "main10",
                "--qvbr", str(qvbr_value), "--preset", "p1", "--output-depth", "10", "--multipass", "2pass-full",
                "--aq", "--aq-temporal", "--aq-strength", "0", "--lookahead", "32", "--lookahead-level", "auto",
                "--transfer", "auto", "--audio-copy", "--chapter-copy", "--key-on-chapter", "--sub-copy",
                "--metadata", "copy", "--crop", crop_value,
                "--vpp-resize", resize_algorithm, "--output-res",
                f"{output_res},preserve_aspect_ratio=increase",
                "-i", intermediate_file, "-o", output_file
            ]
            if fruc_option:  # Add FRUC option only if enabled
                cmd.extend(fruc_option.split())
            print("Executing command:", " ".join(cmd))
            subprocess.run(cmd, check=True)
            print(f"Vertical conversion completed for {file_path}.")

    print(f"Processing complete! All resulting videos have been moved to the '{resolution}' folder.")

if __name__ == "__main__":
    main()
