"""
# FFmpeg Audio-Video Combiner

A Python script to combine audio and video files using FFmpeg.

## Description

This script automates the process of merging audio and video files that have matching base names. It supports batch processing of entire directories or merging specific file pairs. The script uses FFmpeg to combine streams without re-encoding, ensuring fast processing and no quality loss. It now includes content verification to confirm files contain the expected streams.

## Features

- **Batch Processing**: Automatically detects and combines pairs of video (.mp4) and audio (.mp3, .m4a) files in a directory.
- **Single File Merging**: Merge specific video and audio files passed as command-line arguments.
- **Content Verification**: Uses FFprobe to ensure files have the correct streams (video for .mp4, audio for .mp3/.m4a).
- **Efficient**: Uses FFmpeg's stream copying to avoid re-encoding, preserving original quality.
- **Flexible**: Works on current directory, specified directory, or individual files.

## Requirements

- Python 3.x
- FFmpeg (with FFprobe) installed and available in system PATH

## Installation

1. Ensure FFmpeg is installed on your system.
2. Download or copy this script to your desired location.

## Usage

### Process Current Directory
```bash
python ffmpegcombine.py
```

### Process Specified Directory
```bash
python ffmpegcombine.py /path/to/directory
```

### Merge Specific Files
```bash
python ffmpegcombine.py video.mp4 audio.mp3
```

## Output

- For directory processing: Creates a 'combined' subdirectory with merged MP4 files.
- For single files: Outputs a '_combined.mp4' file in the same directory as the video.

## Examples

Given files:
- `video1.mp4` (has video stream) and `video1.mp3` (has audio stream)
- `video2.mp4` (has video stream) and `video2.m4a` (has audio stream)

Running on directory will produce:
- `combined/video1.mp4` (merged)
- `combined/video2.mp4` (merged)

If a file doesn't match (e.g., .mp4 with no video), it will be skipped with a warning.

## Error Handling

The script checks for valid directories and files, verifies content streams, and reports errors if FFmpeg fails.

## Notes

- Assumes video files end with .mp4 and audio with .mp3 or .m4a, but now verifies content.
- Does not overwrite existing files; resolves naming clashes by appending numbers (e.g., _combined_1.mp4).
- No re-encoding: relies on compatible codecs.
- **Documentation**: This README and inline comments must be included and updated with every change to the script to maintain clarity and usability.
"""

# Import the os module for operating system interactions like path handling and directory operations
import os

# Import subprocess to run external commands like FFmpeg and FFprobe
import subprocess

# Import sys to access command-line arguments
import sys

# Import json to parse FFprobe output
import json

# Define a function to resolve output path without overwriting
def resolve_output_path(base_path):
    # If the file doesn't exist, return as is
    if not os.path.exists(base_path):
        return base_path
    # Split into directory, base name, extension
    dir_name = os.path.dirname(base_path)
    base_name = os.path.splitext(os.path.basename(base_path))[0]
    ext = os.path.splitext(base_path)[1]
    # Find a unique name by appending numbers
    counter = 1
    while True:
        new_path = os.path.join(dir_name, f"{base_name}_{counter}{ext}")
        if not os.path.exists(new_path):
            return new_path
        counter += 1

# Define a function to check if a file has the expected stream type
def check_file_type(file_path, expected_type):
    # expected_type: 'video' or 'audio'
    # Run FFprobe to get stream info in JSON format
    command = [
        'ffprobe',
        '-v', 'quiet',
        '-print_format', 'json',
        '-show_streams',
        file_path
    ]
    try:
        # Execute the command and capture output
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        # Parse the JSON output
        data = json.loads(result.stdout)
        # Check streams for the expected type
        for stream in data.get('streams', []):
            if stream['codec_type'] == expected_type:
                return True
        return False
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        # If FFprobe fails or output invalid, assume not matching
        return False

# Define a function to combine audio and video files in a given directory
def combine_audio_video(directory):
    # Docstring explaining the function's purpose
    """
    Combines audio and video files in the given directory that have the same base name.
    Assumes video files are .mp4 and audio files are .mp3 or .m4a, but verifies content.
    Outputs combined .mp4 files in a 'combined' subdirectory.
    """
    # Check if the provided path is a valid directory
    if not os.path.isdir(directory):
        # Print an error message if not a directory
        print(f"Error: {directory} is not a valid directory.")
        # Return early if invalid
        return

    # Create the output directory path by joining the input directory with 'combined'
    output_dir = os.path.join(directory, 'combined')
    # Create the output directory if it doesn't exist, without error if it does
    os.makedirs(output_dir, exist_ok=True)

    # Initialize an empty dictionary to group files by their base name
    file_groups = {}
    # Iterate over each file in the directory
    for filename in os.listdir(directory):
        # Check if the file has one of the target extensions
        if filename.endswith(('.mp4', '.mp3', '.m4a')):
            # Get the base name without extension
            base_name = os.path.splitext(filename)[0]
            # Get the file extension
            ext = os.path.splitext(filename)[1]
            # If this base name hasn't been seen, initialize a sub-dictionary
            if base_name not in file_groups:
                file_groups[base_name] = {}
            # Store the filename under its extension for this base name
            file_groups[base_name][ext] = filename

    # Iterate over each group of files by base name
    for base_name, files in file_groups.items():
        # Attempt to get the video file (.mp4) for this group
        video_file = files.get('.mp4')
        # Attempt to get the audio file (.mp3 or .m4a, preferring .mp3)
        audio_file = files.get('.mp3') or files.get('.m4a')
        # If both video and audio files are present
        if video_file and audio_file:
            # Construct full path to the video file
            video_path = os.path.join(directory, video_file)
            # Construct full path to the audio file
            audio_path = os.path.join(directory, audio_file)
            # Verify the video file has a video stream
            if not check_file_type(video_path, 'video'):
                print(f"Skipping {base_name}: {video_file} does not contain a video stream.")
                continue
            # Verify the audio file has an audio stream
            if not check_file_type(audio_path, 'audio'):
                print(f"Skipping {base_name}: {audio_file} does not contain an audio stream.")
                continue
            # Construct initial output path in the combined directory
            initial_output_path = os.path.join(output_dir, f"{base_name}.mp4")
            # Resolve to avoid overwriting existing files
            output_path = resolve_output_path(initial_output_path)
            # Print a message indicating the files being combined
            print(f"Combining {video_file} and {audio_file} into {os.path.basename(output_path)}")
            # Define the FFmpeg command as a list for subprocess
            command = [
                'ffmpeg',  # Call FFmpeg
                '-i', video_path,  # Input video file
                '-i', audio_path,  # Input audio file
                '-c', 'copy',  # Copy streams without re-encoding
                '-map', '0:v',  # Map video stream from first input
                '-map', '1:a',  # Map audio stream from second input
                output_path  # Output file path (no -y to avoid overwriting)
            ]
            # Try to run the command
            try:
                subprocess.run(command, check=True)
                # Print success message if no error
                print(f"Successfully combined: {base_name}")
            # Catch any errors from subprocess
            except subprocess.CalledProcessError as e:
                # Print error message with details
                print(f"Error combining {base_name}: {e}")
        # If either video or audio is missing
        else:
            # Print skip message
            print(f"Skipping {base_name}: Missing video or audio file.")

# Define a function to combine a single pair of video and audio files
def combine_single_video_audio(video_path, audio_path, initial_output_path):
    # Docstring explaining this function
    """Combines a single video and audio file into one MP4, with content verification."""
    # Verify the video file has a video stream
    if not check_file_type(video_path, 'video'):
        print(f"Error: {video_path} does not contain a video stream.")
        return
    # Verify the audio file has an audio stream
    if not check_file_type(audio_path, 'audio'):
        print(f"Error: {audio_path} does not contain an audio stream.")
        return
    # Resolve output path to avoid overwriting
    output_path = resolve_output_path(initial_output_path)
    # Print a message showing the files being combined and output name
    print(f"Combining {os.path.basename(video_path)} and {os.path.basename(audio_path)} into {os.path.basename(output_path)}")
    # Build the FFmpeg command list for merging
    command = [
        'ffmpeg',  # FFmpeg executable
        '-i', video_path,  # First input: video file
        '-i', audio_path,  # Second input: audio file
        '-c', 'copy',  # Copy codec for no re-encoding
        '-map', '0:v',  # Map video from input 0
        '-map', '1:a',  # Map audio from input 1
        output_path  # Specify output file (no -y)
    ]
    # Attempt to execute the command
    try:
        subprocess.run(command, check=True)
        # Print success on completion
        print("Successfully combined.")
    # Handle any subprocess errors
    except subprocess.CalledProcessError as e:
        # Print error details
        print(f"Error combining: {e}")

# Check if this script is being run directly (not imported)
if __name__ == "__main__":
    # If no command-line arguments provided
    if len(sys.argv) == 1:
        # Use the current working directory
        directory = os.getcwd()
        # Process the current directory for pairs
        combine_audio_video(directory)
    # If one argument provided
    elif len(sys.argv) == 2:
        # Store the argument as path
        path = sys.argv[1]
        # Check if the path is a directory
        if os.path.isdir(path):
            # Process the directory for pairs
            combine_audio_video(path)
        # If not a directory
        else:
            # Print usage error
            print("Usage: python ffmpegcombine.py [<directory_path>] or [<video_file> <audio_file>]")
            print("If directory, processes all pairs in it.")
            print("If files, combines the two files.")
            # Exit with error code
            sys.exit(1)
    # If two arguments provided (presumed files)
    elif len(sys.argv) == 3:
        # First argument is video file
        video_file = sys.argv[1]
        # Second argument is audio file
        audio_file = sys.argv[2]
        # Validate both are existing files
        if not (os.path.isfile(video_file) and os.path.isfile(audio_file)):
            # Print error if not
            print("Both arguments must be existing files.")
            # Exit with error
            sys.exit(1)
        # Extract base name from video file
        base_name = os.path.splitext(os.path.basename(video_file))[0]
        # Get the directory of the video file
        output_dir = os.path.dirname(video_file)
        # Construct initial output path with '_combined' suffix
        initial_output_path = os.path.join(output_dir, f"{base_name}_combined.mp4")
        # Call the function to combine the files (it will resolve the path)
        combine_single_video_audio(video_file, audio_file, initial_output_path)
    # If more than 3 arguments
    else:
        # Print general usage
        print("Usage: python ffmpegcombine.py [<directory_path>] or [<video_file> <audio_file>]")
        print("If no arguments, processes the current directory.")
        # Exit with error
        sys.exit(1)