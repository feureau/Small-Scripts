import os
import subprocess
import json
import platform

def get_video_metadata(video_file):
    """
    Retrieve video metadata such as color primaries, transfer characteristics, and color space using ffprobe.
    """
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v", "-show_entries",
        "stream=color_primaries,color_trc,color_space", "-of", "json", video_file
    ]
    try:
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
        metadata = json.loads(output)
        streams = metadata.get("streams", [])
        if streams:
            return {
                "color_primaries": streams[0].get("color_primaries"),
                "color_trc": streams[0].get("color_trc"),
                "color_space": streams[0].get("color_space")
            }
    except subprocess.CalledProcessError as e:
        print(f"Error retrieving metadata: {e}")
    return None

def construct_ffmpeg_command(input_file, output_file, cq, enable_hdr, audio_tracks):
    """
    Construct the ffmpeg command based on user inputs and detected metadata.
    """
    filters = "hwupload_cuda"
    metadata = get_video_metadata(input_file)

    if enable_hdr:
        if metadata and metadata.get("color_primaries") == "bt709":
            print("Applying NVIDIA True HDR Conversion (SDR to HDR)...")
            filters += ",vpp-truehdr"
        else:
            print("HDR conversion enabled without SDR source detection.")

    command = [
        "ffmpeg", "-hwaccel", "cuda", "-i", input_file,
        "-vf", filters,
        "-c:v", "av1_nvenc", "-cq", str(cq), "-preset", "p5", "-pix_fmt", "yuv420p10le",
        "-color_primaries", "bt2020", "-color_trc", "smpte2084", "-colorspace", "bt2020nc",
        "-y", output_file
    ]

    # Add audio track mapping
    if audio_tracks:
        for track in audio_tracks:
            command.extend(["-map", f"0:a:{track}?"])
    else:
        command.append("-map")
        command.append("0:a")

    # Map video
    command.extend(["-map", "0:v:0"])

    return command

def main():
    input_file = input("Enter the path to the video file: ").strip()
    if not os.path.exists(input_file):
        print("Error: File does not exist.")
        return

    output_file = os.path.splitext(input_file)[0] + "_AV1_HDR.mkv"

    cq = input("Enter target CQ value (lower is better quality) [Default: 28]: ").strip()
    cq = int(cq) if cq.isdigit() else 28

    enable_hdr = input("Enable HDR conversion? [Y/N, Default: N]: ").strip().lower() == 'y'

    audio_tracks = input(
        "Enter the audio track numbers to include (comma separated, Default: All tracks): "
    ).strip()
    audio_tracks = [int(track.strip()) for track in audio_tracks.split(',') if track.strip().isdigit()] if audio_tracks else None

    # Construct and execute command
    command = construct_ffmpeg_command(input_file, output_file, cq, enable_hdr, audio_tracks)

    print("Constructed command:", " ".join(command))

    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in process.stdout:
            print(line, end="")
        process.wait()
        if process.returncode == 0:
            print("\nEncoding completed successfully.")
        else:
            print("\nEncoding failed with exit code:", process.returncode)
    except Exception as e:
        print(f"Error during encoding: {e}")

if __name__ == "__main__":
    main()
