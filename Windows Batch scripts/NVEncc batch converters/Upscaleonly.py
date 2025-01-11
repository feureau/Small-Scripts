import os
import sys
import subprocess

def upscale_video(file_path, resolution, resize_algo, output_res, qvbr):
    """Runs NVEncC64 command to upscale the given video file."""
    base_name, ext = os.path.splitext(os.path.basename(file_path))
    output_dir = os.path.join(os.path.dirname(file_path), resolution)
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"{base_name}_{resolution}{ext}")

    # Build NVEncC64 command
    cmd = [
        "NVEncC64",
        "--avhw",
        "--codec", "av1",
        "--qvbr", str(qvbr),
        "--preset", "p1",
        "--output-depth", "10",
        "--audio-copy",
        "--sub-copy",
        "--chapter-copy",
        "--key-on-chapter",
        "--transfer", "auto",
        "--colorprim", "auto",
        "--colormatrix", "auto",
        "--lookahead", "32",
        "--aq-temporal",
        "--multipass", "2pass-full",
        "--log-level", "info",
        "--output", output_file,
        "-i", file_path,
        "--vpp-resize", f"algo={resize_algo}",
        "--output-res", output_res
    ]

    print(f"Running command for {file_path}: {' '.join(cmd)}")
    
    try:
        subprocess.run(cmd, check=True)
        print(f"Processing complete for {file_path}. Output: {output_file}")
    except subprocess.CalledProcessError as e:
        print(f"Error processing {file_path}: {e}")

def main():
    if len(sys.argv) < 2:
        print("Please drag and drop one or more video files onto this script.")
        return

    # Ask user for upscaling resolution
    while True:
        print("Select upscaling resolution:")
        print("[1] 4K (2160p)")
        print("[2] 8K (4320p)")
        choice = input("Enter 1 for 4K or 2 for 8K: ").strip()
        if choice == "1":
            resolution = "4k"
            resize_algo = "nvvfx-superres"
            output_res = "2160x2160,preserve_aspect_ratio=increase"
            qvbr = 18
            break
        elif choice == "2":
            resolution = "8k"
            resize_algo = "ngx-vsr"
            output_res = "4320x4320,preserve_aspect_ratio=increase"
            qvbr = 28
            break
        else:
            print("Invalid input. Please enter 1 or 2.")

    # Process each file provided as a command-line argument
    for file_path in sys.argv[1:]:
        if os.path.isfile(file_path):
            upscale_video(file_path, resolution, resize_algo, output_res, qvbr)
        else:
            print(f"Invalid file: {file_path}")

    print("All files processed.")

if __name__ == "__main__":
    main()
