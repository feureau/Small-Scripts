import argparse
import subprocess
import os
import sys

def main():
    parser = argparse.ArgumentParser(description="Replace audio in a video file with a new audio track using ffmpeg.")
    parser.add_argument("-i", "--input", required=True, help="Input video file")
    parser.add_argument("-a", "--audio", required=True, help="Input audio file")
    parser.add_argument("-o", "--output", help="Output video file (optional). If not specified, '_swapped' is appended to the input filename.")
    
    args = parser.parse_args()
    
    video_in = args.input
    audio_in = args.audio
    
    if not os.path.exists(video_in):
        print(f"Error: Video file '{video_in}' not found.")
        sys.exit(1)
        
    if not os.path.exists(audio_in):
        print(f"Error: Audio file '{audio_in}' not found.")
        sys.exit(1)
        
    if args.output:
        video_out = args.output
    else:
        # Generate output filename (e.g. inputvideo_swapped.mov)
        base, ext = os.path.splitext(video_in)
        video_out = f"{base}_swapped{ext}"
        
    print(f"Input Video:  {video_in}")
    print(f"Input Audio:  {audio_in}")
    print(f"Output Video: {video_out}")
    print("-" * 40)
    
    # ffmpeg command explanation:
    # -y: overwrite output file if it exists
    # -i video_in: first input (index 0)
    # -i audio_in: second input (index 1)
    # -c:v copy: copy the video stream without re-encoding (very fast)
    # -c:a copy: copy the audio stream without re-encoding
    # -map 0:v:0: map the first video stream from the first input
    # -map 1:a:0: map the first audio stream from the second input
    cmd = [
        "ffmpeg",
        "-y", 
        "-i", video_in,
        "-i", audio_in,
        "-c:v", "copy",
        "-c:a", "copy",
        "-map", "0:v:0", 
        "-map", "1:a:0", 
        video_out
    ]
    
    try:
        # Run the ffmpeg command
        subprocess.run(cmd, check=True)
        print(f"\nSuccess! The new video with swapped audio has been saved to: {video_out}")
    except subprocess.CalledProcessError as e:
        print(f"\nError: ffmpeg command failed with exit code {e.returncode}.")
        sys.exit(1)
    except FileNotFoundError:
        print("\nError: 'ffmpeg' command not found. Please ensure ffmpeg is installed and added to your system's PATH.")
        sys.exit(1)

if __name__ == "__main__":
    main()
