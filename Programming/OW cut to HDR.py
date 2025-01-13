import os
import subprocess

# Default configuration values
intro_trim = 293
outtro_trim = 1131
upscale = ""
trim_flags = ""

# User input prompts
def get_user_input(prompt, default):
    response = input(f"{prompt} (default: {default}): ").strip().lower()
    return response if response else default

# Get user preferences
cut_intro = get_user_input("Cut Intro? (y/n or 1/0)", "y")
if cut_intro in ["n", "0"]:
    intro_trim = 0

cut_outtro = get_user_input("Cut Outtro? (y/n or 1/0)", "y")
if cut_outtro in ["n", "0"]:
    outtro_trim = 0

if intro_trim != 0 or outtro_trim != 0:
    trim_flags = f"--trim {intro_trim}:{outtro_trim}"

convert_to_4k = get_user_input("Convert to 4K? (y/n or 1/0)", "n")
if convert_to_4k in ["y", "1"]:
    upscale = "--vpp-resize algo=nvvfx-superres,superres-mode=0 --output-res 2160x2160,preserve_aspect_ratio=increase"

# Get the list of files to process
print("Drag and drop the files to process (press Enter when done):")
files = []
while True:
    file_path = input().strip()
    if not file_path:
        break
    if os.path.isfile(file_path):
        files.append(file_path)
    else:
        print(f"File not found: {file_path}")

if not files:
    print("No valid files provided. Exiting.")
    exit()

# Process each file
for file in files:
    file = file.strip("\"'")  # Strip quotes if dragged-and-dropped
    print(f"Processing: {file}")

    output_file = f"{os.path.splitext(file)[0]}_HDR.mkv"
    command = (
        f"NVEncC64 --avhw {trim_flags} --codec av1 --tier 1 --profile high --cqp 43 --preset p7 --output-depth 10 "
        f"--multipass 2pass-full --lookahead 32 --gop-len 4 --nonrefp --aq --aq-temporal --aq-strength 0 "
        f"--transfer auto --audio-codec ac3 --audio-bitrate 640 --chapter-copy --key-on-chapter --metadata copy "
        f"--vpp-ngx-truehdr maxluminance=1000,middlegray=18,saturation=200,contrast=200 "
        f"--colormatrix bt2020nc --colorprim bt2020 --transfer smpte2084 {upscale} -i \"{file}\" -o \"{output_file}\""
    )

    try:
        subprocess.run(command, shell=True, check=True)
        # Check if the output file was created
        if os.path.exists(output_file):
            hdr_folder = "HDR"
            os.makedirs(hdr_folder, exist_ok=True)
            destination = os.path.join(hdr_folder, os.path.basename(output_file))
            os.rename(output_file, destination)
            print(f"Processed successfully: {destination}")
        else:
            print(f"Failed to process {file}")
    except subprocess.CalledProcessError as e:
        print(f"Error processing {file}: {e}")

print("Processing complete.")
