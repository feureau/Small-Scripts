import os
import sys
import subprocess
import time
import cv2

def get_user_input(prompt, default=None):
    user_input = input(prompt)
    return user_input if user_input else default

def get_video_resolution(video_file):
    cap = cv2.VideoCapture(video_file)
    if not cap.isOpened():
        print(f"Unable to open video file: {video_file}")
        return None, None
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    return height, width

if len(sys.argv) < 2:
    print("No video file specified. Please drag and drop a video file onto the script.")
    input("Press any key to exit...")
    sys.exit()

video_files = sys.argv[1:]

# Ask user to select decoding mode
decode_choice = get_user_input("Select decoding mode:\n[1] Hardware decoding (default)\n[2] Software decoding\nEnter choice (1 or 2) [1]: ", "1")
decode_flag = "--avhw" if decode_choice == "1" else "--avsw"

for video_file in video_files:
    # Get resolution of input video
    input_height, input_width = get_video_resolution(video_file)
    if input_height is None or input_width is None:
        continue

    # Automatically set resolution option based on input
    res_choice = "1" if input_height <= 1080 else "2"
    default_qvbr = "23" if res_choice == "1" else "30"

    # Define encoding variables
    FRUC_VAR = "--vpp-fruc fps=60"
    RESIZE_VAR = "--vpp-resize algo=nvvfx-superres,superres-mode=0 --output-res 3840x2160,preserve_aspect_ratio=decrease"
    HDR_VAR = "--vpp-ngx-truehdr --colormatrix bt2020nc --colorprim bt2020 --transfer smpte2084"

    # Initialize options
    FRUC_OPTION = ""
    RESIZE_OPTION = ""
    HDR_OPTION = ""
    ARTIFACT_REDUCTION_OPTION = ""
    DENOISE_OPTION = ""

    # Ask for custom crop parameters
    target_height = int(get_user_input(f"Enter target vertical height (in pixels) [{input_height}]: ", str(input_height)))
    top = (input_height - target_height) // 2
    top -= top % 4

    bottom = (input_height - target_height) // 2
    bottom -= bottom % 4

    target_width = int(get_user_input(f"Enter target horizontal width (in pixels) [{input_width}]: ", str(input_width)))
    left = (input_width - target_width) // 2
    left -= left % 4

    right = (input_width - target_width) // 2
    right -= right % 4

    # Ask for QVBR target value
    qvbr = get_user_input(f"Enter target QVBR [{default_qvbr}]: ", default_qvbr)

    # Prompt user for Resize to 4K only if input resolution is 1080p
    if res_choice == "1":  # Input resolution is 1080p
        resize_enable = get_user_input("Enable Resize to 4K? [Y/N/1/0] (default is N): ", "N").lower()
        if resize_enable in ["y", "1"]:
            RESIZE_OPTION = RESIZE_VAR

    # Prompt user for FRUC
    fruc_enable = get_user_input("Enable FRUC (fps=60)? [Y/N/1/0] (default is N): ", "N").lower()
    if fruc_enable in ["y", "1"]:
        FRUC_OPTION = FRUC_VAR

    # Prompt user for Artifact Reduction and Denoise only if resolution <= 1080p
    if res_choice == "1":
        artifact_enable = get_user_input("Enable Artifact Reduction? [Y/N/1/0] (default is N): ", "N").lower()
        if artifact_enable in ["y", "1"]:
            ARTIFACT_REDUCTION_OPTION = "--vpp-nvvfx-artifact-reduction mode=0"

        denoise_enable = get_user_input("Enable Denoise? [Y/N/1/0] (default is N): ", "N").lower()
        if denoise_enable in ["y", "1"]:
            DENOISE_OPTION = "--vpp-nvvfx-denoise"

    # Prompt user for HDR conversion
    hdr_enable = get_user_input("Enable HDR Conversion? [Y/N/1/0] (default is N): ", "N").lower()
    if hdr_enable in ["y", "1"]:
        HDR_OPTION = HDR_VAR

    # Ask user if they want to copy audio or convert it to ac3
    audio_choice = get_user_input("Do you want to copy the audio or convert it to AC3?\n[1] Copy Audio (default)\n[2] Convert to AC3\nEnter choice (1 or 2) [1]: ", "1")
    if audio_choice == "1":
        audio_codec_options = ["--audio-copy"]
    else:
        # Split audio options for proper parsing
        audio_codec_options = [
            "--audio-codec", "ac3",
            "--audio-bitrate", "640",
            "--audio-stream", ":5.1"
        ]

    # Ask user for GOP length
    gop_len = get_user_input("Enter GOP length [6]: ", "6")

    # Display all options before starting
    print("\n--- Selected Encoding Options ---")
    print(f"Input File: {video_file}")
    print(f"Input Resolution: {input_width}x{input_height}")
    print(f"Target Resolution: {target_width}x{target_height}")
    print(f"Decoding Mode: {decode_flag}")
    print(f"Crop Settings: Top={top}, Bottom={bottom}, Left={left}, Right={right}")
    print(f"QVBR Quality Setting: {qvbr}")
    print(f"FRUC 60p: {FRUC_OPTION}")
    print(f"Resize to 4K: {RESIZE_OPTION}")
    print(f"Artifact Reduction: {ARTIFACT_REDUCTION_OPTION}")
    print(f"Denoise: {DENOISE_OPTION}")
    print(f"HDR Conversion: {HDR_OPTION}")
    print(f"Audio: {'Copy Audio' if audio_choice == '1' else 'Convert to AC3'}")
    print(f"GOP Length: {gop_len}")
    print("-------------------------------\n")

    # Process each video file
    output_file = os.path.abspath(f"{os.path.splitext(video_file)[0]}_HDR_{int(time.time())}.mkv")
    command = [
        "NVEncC64", decode_flag, "--codec", "av1", "--tier", "1", "--profile", "high",
        "--crop", f"{left},{top},{right},{bottom}", "--qvbr", qvbr, "--preset", "p7",
        "--output-depth", "10", "--multipass", "2pass-full", "--nonrefp", "--aq", "--aq-temporal",
        "--aq-strength", "0", "--lookahead", "32", "--gop-len", gop_len, "--lookahead-level", "auto",
        "--transfer", "auto", "--chapter-copy", "--key-on-chapter", "--metadata", "copy",
        FRUC_OPTION, RESIZE_OPTION, ARTIFACT_REDUCTION_OPTION, DENOISE_OPTION, HDR_OPTION,
        "-i", video_file, "-o", output_file
    ] + audio_codec_options  # Append audio options
    command = [arg for arg in command if arg]  # Remove empty arguments

    # Run encoding command with real-time output
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in iter(process.stdout.readline, ""):
            if line:
                print(line.strip())
        process.wait()
        if process.returncode != 0:
            print(f"Error while processing {video_file}. Exit code: {process.returncode}")
            continue
    except Exception as e:
        print(f"Error while running NVEncC64 for {video_file}: {e}")
        continue

    # Check if output file was created
    if not os.path.exists(output_file):
        print(f"Output file {output_file} was not created.")
        continue

    # Ensure HDR folder exists
    hdr_folder = os.path.abspath("HDR")
    if not os.path.exists(hdr_folder):
        try:
            os.makedirs(hdr_folder)
        except OSError as e:
            print(f"Failed to create HDR folder: {e}")
            continue

    # Move the output file to HDR folder
    try:
        hdr_output_path = os.path.join(hdr_folder, os.path.basename(output_file))
        os.replace(output_file, hdr_output_path)
        print(f"File moved to HDR folder: {hdr_output_path}")
    except OSError as e:
        print(f"Failed to move {output_file} to HDR folder: {e}")
        continue

    # Write settings to a log file in the HDR folder
    log_file_path = os.path.join("HDR", "encoding_log.txt")
    with open(log_file_path, "a") as log_file:  # Use append mode
        log_file.write("--- Selected Encoding Options ---\n")
        log_file.write(f"Input File: {video_file}\n")
        log_file.write(f"Input Resolution: {input_width}x{input_height}\n")
        log_file.write(f"Target Resolution: Height={target_height}, Width={target_width}\n")
        log_file.write(f"Crop Settings: Top={top}, Bottom={bottom}, Left={left}, Right={right}\n")
        log_file.write(f"QVBR Quality Setting: {qvbr}\n")
        log_file.write(f"FRUC 60p: {FRUC_OPTION}\n")
        log_file.write(f"Resize to 4K: {RESIZE_OPTION}\n")
        log_file.write(f"Artifact Reduction: {ARTIFACT_REDUCTION_OPTION}\n")
        log_file.write(f"Denoise: {DENOISE_OPTION}\n")
        log_file.write(f"HDR Conversion: {HDR_OPTION}\n")
        log_file.write(f"Audio: {'Copy Audio' if audio_choice == '1' else 'Convert to AC3'}\n")
        log_file.write(f"GOP Length: {gop_len}\n")
        log_file.write("-------------------------------\n\n")

    print(f"Processed file: {os.path.basename(output_file)}")

# Final message
import platform

def wait_for_any_key():
    if platform.system() == "Windows":
        import msvcrt
        print("Processing complete. Press any key to exit...")
        msvcrt.getch()  # Waits for a key press
    else:
        print("Processing complete. Press any key to exit...")
        os.system("stty -echo -icanon")  # Configure terminal to read single keypress
        try:
            os.read(0, 1)  # Wait for any key press
        finally:
            os.system("stty sane")  # Reset terminal to normal mode

# Call the wait_for_any_key function
wait_for_any_key()
