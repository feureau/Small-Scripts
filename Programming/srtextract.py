import subprocess
import os
import sys
import glob

def extract_srt_from_video(video_path):
    """
    Extracts all SRT subtitle streams from a video file using FFmpeg.

    Args:
        video_path: The path to the video file.
    """

    if not os.path.exists(video_path):
        print(f"Error: Video file not found: {video_path}")
        return

    try:
        # 1. Probe the video file to get subtitle stream information
        ffprobe_command = [
            "ffprobe",
            "-v", "error",  # Only show errors
            "-select_streams", "s",  # Select only subtitle streams
            "-show_entries", "stream=index", # Show only index
            "-of", "default=noprint_wrappers=1:nokey=1", # Format output nicely
            video_path
        ]
        ffprobe_output = subprocess.run(ffprobe_command, capture_output=True, text=True, check=True)
        subtitle_stream_indices_str = ffprobe_output.stdout.strip().split('\n')

        if not subtitle_stream_indices_str or not subtitle_stream_indices_str[0]:
            print(f"No subtitle streams found in: {video_path}")
            return

        print(f"Found subtitle streams in: {video_path}")

        # Convert indices to integers
        subtitle_stream_indices = []
        for index_str in subtitle_stream_indices_str:
            try:
                subtitle_stream_indices.append(int(index_str))
            except ValueError:
                print(f"Warning: Could not parse subtitle stream index: {index_str}")
                continue # Skip to the next index if parsing fails

        # 2. Extract each subtitle stream
        for i, stream_index in enumerate(subtitle_stream_indices):
            output_srt_filename = os.path.splitext(os.path.basename(video_path))[0] + f"_subtitle_{i+1}.srt"
            output_srt_path = os.path.join(".", output_srt_filename) # Save in the current working directory

            # Modified ffmpeg_command - using stream index directly in -map
            ffmpeg_command = [
                "ffmpeg",
                "-i", video_path,
                "-map", f"0:{stream_index}",  # Changed from "-map", f"0:s:{stream_index}"
                output_srt_path
            ]

            print(f"  Extracting subtitle stream {i+1} (index {stream_index}) to: {output_srt_path}")
            subprocess.run(ffmpeg_command, check=True)
            print(f"  Subtitle stream {i+1} extracted successfully to: {output_srt_path}")

    except subprocess.CalledProcessError as e:
        print(f"FFmpeg error while processing {video_path}:")
        print(e.stderr)
    except Exception as e:
        print(f"An unexpected error occurred while processing {video_path}: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        video_files = []
        for arg in sys.argv[1:]: # Iterate through command line arguments
            glob_files = glob.glob(arg) # Expand wildcards like *.mkv
            if glob_files:
                video_files.extend(glob_files) # Add expanded files to the list
            elif os.path.isfile(arg): # If not a wildcard and a file, add it directly
                video_files.append(arg)
            else:
                print(f"Warning: Argument '{arg}' is not a valid file or wildcard pattern.")

    else:
        # If no arguments provided, process all video files in the current directory
        video_files = [f for f in os.listdir('.') if os.path.isfile(f) and f.lower().endswith(('.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm'))] # Add more extensions if needed

    if not video_files:
        print("No video files found to process in the current directory or provided as arguments.")
    else:
        print("Starting subtitle extraction...")
        for video_file in video_files:
            print(f"\nProcessing video file: {video_file}")
            extract_srt_from_video(video_file)
        print("\nSubtitle extraction completed.")