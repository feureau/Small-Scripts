import os
import sys
import subprocess
import time
import platform
import logging
from multiprocessing import Pool
from collections import Counter
import shutil

def get_user_input(prompt, default=None):
    user_input = input(prompt)
    return user_input.strip() if user_input.strip() else default

def check_nvencc_availability():
    """Check if NVEncC64 is available on the system."""
    try:
        subprocess.run(["NVEncC64", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logging.info("NVEncC64 is available.")
    except FileNotFoundError:
        logging.error("NVEncC64 not found. Please ensure it is installed and accessible.")
        sys.exit(1)

def get_video_duration(video_file):
    """Get the duration of the video in seconds."""
    command = ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=duration", "-of", "default=noprint_wrappers=1:nokey=1", video_file]
    try:
        duration = subprocess.check_output(command, stderr=subprocess.STDOUT, text=True).strip()
        return float(duration)
    except Exception as e:
        logging.error(f"Error retrieving video duration: {e}")
        return None

def get_crop_parameters(video_file):
    """Run FFmpeg cropdetect to determine optimal cropping parameters."""
    duration = get_video_duration(video_file)
    if not duration or duration < 1:
        print("Invalid video duration.")
        return None

    default_limit = "64"
    limit_value = get_user_input(f"Enter cropdetect limit value (higher detects more black areas) [{default_limit}]: ", default_limit)
    default_round = "4"
    round_value = get_user_input(f"Enter cropdetect round value (controls precision) [{default_round}]: ", default_round)

    sample_interval = max(10, duration // 12)  # Analyze at least 12 samples or one every 10 seconds
    crop_values = []

    for i in range(0, int(duration), int(sample_interval)):
        command = [
            "ffmpeg", "-ss", str(i), "-i", video_file, "-vframes", "1", "-vf",
            f"cropdetect={limit_value}:{round_value}:0", "-f", "null", "-"
        ]
        try:
            process = subprocess.run(command, stderr=subprocess.PIPE, text=True, encoding="utf-8")
            stderr_output = process.stderr

            for line in stderr_output.splitlines():
                if "crop=" in line:
                    crop_values.append(line.split("crop=")[-1].strip())
                    break
        except Exception as e:
            logging.error(f"Error during cropdetect at {i}s: {e}")

    if not crop_values:
        print("No crop parameters detected.")
        return None

    most_common_crop = Counter(crop_values).most_common(1)[0][0]
    print(f"Optimal crop parameters detected: {most_common_crop}")
    return most_common_crop

def encode_video(video_file, output_file, encode_params):
    """Encode video with NVEncC64."""
    command = [
        "NVEncC64",
        encode_params["decode_flag"],
        "--codec", "av1",
        "--qvbr", encode_params["qvbr"],
        "--output-depth", "10",
        "--gop-len", encode_params["gop_len"],
        "--multipass", "2pass-full",
        "--preset", "p7",
        "--output-res", encode_params["resize"],
        "-i", video_file,
        "-o", output_file
    ]

    if encode_params["crop"]:
        command.extend(["--crop", encode_params["crop"]])
    if encode_params["hdr"]:
        command.extend(encode_params["hdr"])
    if encode_params["audio"]:
        command.extend(encode_params["audio"])

    try:
        logging.info(f"Encoding {video_file} to {output_file}...")
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1
        )

        for line in iter(process.stdout.readline, ""):
            if "frames:" in line.strip():
                print(f"\r{line.strip()}", end="", flush=True)

        process.wait()
        if process.returncode != 0:
            logging.error(f"NVEncC64 exited with code {process.returncode}")
            return False
        return True
    except Exception as e:
        logging.error(f"Error during encoding: {e}")
        return False

def wait_for_any_key():
    """Pause the script until any key is pressed."""
    print("Processing complete. Press any key to exit...")
    if platform.system() == "Windows":
        import msvcrt
        msvcrt.getch()
    else:
        os.system("stty -echo -icanon")
        try:
            os.read(0, 1)
        finally:
            os.system("stty sane")

DEFAULTS = {
    "width": "1080",
    "height": "1920",
    "gop_length": "6",
    "qvbr": "20"
}

if __name__ == "__main__":
    logging.basicConfig(filename="ingest.log", level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    check_nvencc_availability()

    if len(sys.argv) < 2:
        logging.error("No video file specified. Please drag and drop a video file onto the script.")
        input("Press any key to exit...")
        sys.exit()

    video_files = sys.argv[1:]

    decode_choice = get_user_input("Select decoding mode:\n[1] Hardware decoding (default)\n[2] Software decoding\nEnter choice (1 or 2) [1]: ", "1")
    decode_flag = "--avhw" if decode_choice == "1" else "--avsw"

    hdr_enable = get_user_input("Enable HDR conversion? [Y/N] (default N): ", "N").lower()
    hdr = ["--vpp-ngx-truehdr", "--colormatrix", "bt2020nc", "--colorprim", "bt2020", "--transfer", "smpte2084"] if hdr_enable in ["y", "yes"] else []

    resize_width = get_user_input(f"Enter target horizontal width [{DEFAULTS['width']}]: ", DEFAULTS["width"])
    resize_height = get_user_input(f"Enter target vertical height [{DEFAULTS['height']}]: ", DEFAULTS["height"])
    resize = f"{resize_width}x{resize_height},preserve_aspect_ratio=increase"

    gop_len = get_user_input(f"Enter GOP length [{DEFAULTS['gop_length']}]: ", DEFAULTS["gop_length"])

    audio = ["--audio-codec", "ac3", "--audio-bitrate", "640"]

    for video_file in video_files:
        crop_params = get_crop_parameters(video_file)

        encode_params = {
            "decode_flag": decode_flag,
            "qvbr": DEFAULTS["qvbr"],
            "gop_len": gop_len,
            "resize": resize,
            "hdr": hdr,
            "audio": audio,
            "crop": crop_params
        }

        output_file = os.path.abspath(f"{os.path.splitext(video_file)[0]}_encoded_{int(time.time())}.mkv")
        success = encode_video(video_file, output_file, encode_params)

        if success:
            print(f"Encoding completed successfully: {output_file}")
        else:
            print(f"Encoding failed for: {video_file}")

    wait_for_any_key()
