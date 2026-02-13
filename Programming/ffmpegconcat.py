#!/usr/bin/env python
"""
--- ffmpegconcat.py ---

A Python script to losslessly concatenate multiple video files using FFmpeg,
with automatic embedding of subtitles and chapters from accompanying files.

---------------------------------
-- ARCHITECTURAL OVERVIEW --
---------------------------------

[ THE CORE PROBLEM ]
Simple FFmpeg concatenation methods fail on complex source files, such as screen
recordings that have a variable number of audio tracks.
  - The `concat` demuxer (using a file list) is fast and lossless but requires
    every input file to have the exact same number and type of streams. If one
    file has 5 audio tracks and another has 6, it will fail or silently drop
    streams.
  - The `concat` filter (using `-filter_complex`) can handle varied inputs by
    creating placeholder silent tracks, but this act of filtering makes the
    resulting streams ineligible for lossless stream copying (`-c copy`), forcing
    a slow and lossy re-encode.

[ THE ROBUST SOLUTION ]
This script solves the problem by implementing an intelligent, multi-stage
workflow that combines the best of all methods:

1.  **ANALYSIS FIRST:** The script begins by probing every input file to count its
    audio streams. It finds the most common layout (e.g., "6 audio tracks") and
    intelligently filters its working list to include ONLY the files that match
    this layout. This guarantees that all subsequent operations are performed on
    a consistent and compatible set of files.

2.  **METADATA PRE-PROCESSING:** Before touching FFmpeg, the script prepares all
    necessary metadata in temporary files. This includes:
    - Merging all SRT subtitle files into a single file, meticulously
      recalculating the timestamps of every entry to match the final concatenated
      timeline.
    - Reading accompanying JSON files (.txt) to extract chapter titles and
      generating a chapter metadata file for FFmpeg.
    - Generating a YouTube-formatted chapter list as a final text file.

3.  **TWO-PASS FFMPEG EXECUTION:** With a clean set of compatible files and all
    metadata prepared, the script uses a reliable two-pass FFmpeg process:
    - **Pass 1 (Lossless Concatenation):** Uses the fast and efficient `concat`
      demuxer (`mylist.txt` method). Because the file list has been pre-filtered
      for compatibility, this pass succeeds flawlessly, preserving ALL video and
      audio tracks without re-encoding. This creates a temporary, clean video file.
    - **Pass 2 (Muxing):** Performs a simple and fast "muxing" operation. It takes
      the temporary video from Pass 1 and adds the pre-processed subtitle and
      chapter tracks. Since no complex filtering is needed here, this can also be
      done via stream copying.

This architecture ensures the highest possible quality (true lossless copy) for
the vast majority of files while gracefully handling inconsistencies and complex
metadata requirements.

---------------------------------
-- EXECUTION WORKFLOW --
---------------------------------

1.  **File Discovery:** The script finds all video files, either from command-line
    arguments (which can include wildcards like `*.mp4`) or by automatically
    searching the current directory.

2.  **Audio Layout Analysis:** It loops through every found video, uses `ffprobe`
    to count the number of audio streams, and determines the most common count
    (the "mode"). It then filters its internal list to only include files that
    match this mode, printing a warning for any files that are skipped.

3.  **Metadata Aggregation Loop:** The script iterates through the new, filtered
    list of compatible files and:
    a. Gets the precise duration of each video clip.
    b. **Chapters:** Looks for a matching `.txt` file, parses it as JSON, and
       extracts the `title`. It stores this title along with the calculated start
       time (based on the cumulative duration of previous clips).
    c. **Subtitles:** Looks for a matching `.srt` file. If found and valid, it
       reads every subtitle entry and recalculates its start/end timestamps by
       adding the cumulative duration offset.

4.  **File Generation:** After the loop, the script writes its collected data:
    - A temporary, single, merged SRT file with all timestamps corrected.
    - A temporary FFmpeg metadata file defining all the embedded chapters.
    - A final, permanent `output.txt` file containing the YouTube-formatted
      chapter list for easy copy-pasting.

5.  **FFmpeg Pass 1 (Concatenation):**
    - A temporary `mylist.txt` is created.
    - FFmpeg is called with the `concat` demuxer to create a temporary, merged
      video file (`temp_concat_...mp4`). This contains all video and audio
      streams from the compatible source files, perfectly preserved.

6.  **FFmpeg Pass 2 (Muxing):**
    - FFmpeg is called a second time with multiple inputs: the temporary video,
      the temporary merged SRT, and the temporary chapter metadata file.
    - `-map` commands are used to pull in all streams from the video (`-map 0`),
      the subtitle stream (`-map 1`), and the chapter metadata (`-map_metadata 2`).
    - `-c copy` is used to ensure this final step is also lossless.
    - The final `output.mp4` is created.

7.  **Cleanup:** A `finally` block guarantees that all temporary files (the list,
    the merged SRT, the metadata file, and the large temporary video) are deleted,
    regardless of whether the script succeeded or failed.

---------------------------------
-- USAGE --
---------------------------------

# Auto-discover all compatible videos in the current folder and subfolders:
> python ffmpegconcat.py

# Use a wildcard to process only MP4 files in the current folder:
> python ffmpegconcat.py *.mp4

# Specify an output name and prevent the final SRT from being saved:
> python ffmpegconcat.py -o "My Movie.mkv" --no-extract-srt

Arguments:
  videos                Optional. A space-separated list of video files or
                        patterns (e.g., *.mp4). If omitted, searches the
                        current directory tree.
  -o, --output          Optional. The name for the final merged video file.
                        Defaults to the first compatible input filename.
  --no-extract-srt      Optional. By default, a final merged .srt file is
                        saved. Use this flag to disable this behavior.

---------------------------------
-- DEPENDENCIES --
---------------------------------
1. Python 3 (with standard libraries: re, shutil, json, uuid, collections)
2. FFmpeg: Must be installed and accessible in the system's PATH.
3. ffmpeg-python: The required Python library (`pip install ffmpeg-python`).

"""
import argparse
import subprocess
import ffmpeg
import os
import sys
import glob
import uuid
import re
import shutil
import json
from datetime import timedelta
from collections import Counter

VIDEO_EXTENSIONS = [
    '.mp4', '.mkv', '.mov', '.avi', '.flv', '.wmv', '.webm', '.mpeg', '.mpg', '.m4v'
]
INPUT_SUBDIR = 'input'

# --- Helper Functions for Time Conversion ---

def srt_time_to_seconds(time_str):
    """Converts an SRT timestamp string (HH:MM:SS,ms) to total seconds."""
    h, m, s, ms = map(int, re.split('[,:]', time_str))
    return h * 3600 + m * 60 + s + ms / 1000

def seconds_to_srt_time(seconds):
    """Converts total seconds to an SRT timestamp string (HH:MM:SS,ms)."""
    td = timedelta(seconds=seconds)
    minutes, sec = divmod(td.seconds, 60)
    hours, minutes = divmod(minutes, 60)
    milliseconds = int(td.microseconds / 1000)
    return f"{hours:02}:{minutes:02}:{sec:02},{milliseconds:03}"

def seconds_to_youtube_time(seconds):
    """Converts total seconds to a YouTube timestamp string (HH:MM:SS)."""
    # Floor the seconds to get a clean timestamp for YouTube
    td = timedelta(seconds=int(seconds))
    minutes, sec = divmod(td.seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        return f"{hours:d}:{minutes:02d}:{sec:02d}"
    else:
        return f"{minutes:02d}:{sec:02d}"

def move_processed_videos_to_input_folder(video_files, input_subdir, protected_paths=None):
    """Move processed source videos and sidecars into an input archive folder."""
    os.makedirs(input_subdir, exist_ok=True)
    input_abs = os.path.normcase(os.path.abspath(input_subdir))
    protected_abs = set()
    for path in (protected_paths or []):
        protected_abs.add(os.path.normcase(os.path.abspath(path)))
    moved_count = 0

    for source_path in video_files:
        if not os.path.isfile(source_path):
            continue

        source_abs = os.path.normcase(os.path.abspath(source_path))
        if source_abs.startswith(input_abs + os.sep):
            continue
        if source_abs in protected_abs:
            continue

        base_name = os.path.basename(source_path)
        destination_path = os.path.join(input_subdir, base_name)
        if os.path.exists(destination_path):
            name_root, name_ext = os.path.splitext(base_name)
            suffix = 1
            while True:
                candidate = os.path.join(input_subdir, f"{name_root}_{suffix}{name_ext}")
                if not os.path.exists(candidate):
                    destination_path = candidate
                    break
                suffix += 1

        source_base, _ = os.path.splitext(source_path)
        files_to_move = [source_path]
        for ext in ('.srt', '.txt'):
            sidecar = source_base + ext
            if os.path.isfile(sidecar):
                sidecar_abs = os.path.normcase(os.path.abspath(sidecar))
                if sidecar_abs not in protected_abs:
                    files_to_move.append(sidecar)

        target_video_base, _ = os.path.splitext(destination_path)
        for move_src in files_to_move:
            move_src_abs = os.path.normcase(os.path.abspath(move_src))
            if move_src_abs in protected_abs:
                continue
            src_ext = os.path.splitext(move_src)[1]
            move_dest = target_video_base + src_ext if move_src != source_path else destination_path
            try:
                shutil.move(move_src, move_dest)
                print(f"Moved processed input: {move_src} -> {move_dest}")
            except Exception as e:
                print(f"Warning: Could not move '{move_src}' to '{input_subdir}'. Error: {e}")
        moved_count += 1

    if moved_count:
        print(f"Moved {moved_count} processed input file(s) into '{input_subdir}'.")

def main():
    """The main function that orchestrates the entire concatenation process."""
    parser = argparse.ArgumentParser(
        description="A script to losslessly concatenate videos with subtitle and chapter support.",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('videos', nargs='*', help="List of video files or patterns (e.g., *.mp4).")
    parser.add_argument('-o', '--output', default=None, help="Name of the output video file. Defaults to the first compatible input filename.")
    parser.add_argument('--no-extract-srt', dest='extract_srt', action='store_false', help="Do not save the final merged subtitle track as a separate .srt file.")
    
    args = parser.parse_args()

    # --- File Discovery ---
    initial_video_files = []
    if args.videos:
        print("Processing input file patterns...")
        for pattern in args.videos:
            initial_video_files.extend(glob.glob(pattern))
        initial_video_files = sorted(list(dict.fromkeys(initial_video_files)))
    else:
        print("No video files provided. Searching current directory and subdirectories...")
        for ext in VIDEO_EXTENSIONS:
            initial_video_files.extend(glob.glob(f'**/*{ext}', recursive=True))
        initial_video_files = sorted(list(dict.fromkeys(initial_video_files)))
        input_abs = os.path.normcase(os.path.abspath(INPUT_SUBDIR))
        initial_video_files = [
            f for f in initial_video_files
            if not os.path.normcase(os.path.abspath(f)).startswith(input_abs + os.sep)
        ]

    if not initial_video_files:
        print("Error: No video files found to process.")
        return

    # --- Stage 1: Analyze and Filter Files by Audio Stream Count ---
    print(f"\n--- Analyzing Audio Stream Layouts for {len(initial_video_files)} files ---")
    stream_counts = {}
    for video_file in initial_video_files:
        try:
            probe = ffmpeg.probe(video_file)
            count = sum(1 for s in probe['streams'] if s['codec_type'] == 'audio')
            stream_counts[video_file] = count
        except Exception as e:
            print(f"Warning: Could not probe '{os.path.basename(video_file)}'. It will be skipped. Error: {e}")
            stream_counts[video_file] = -1

    valid_counts = [c for c in stream_counts.values() if c != -1]
    if not valid_counts:
        print("Error: Could not analyze any video files.")
        return

    mode_count = Counter(valid_counts).most_common(1)[0][0]
    
    video_files_to_process = [f for f, c in stream_counts.items() if c == mode_count]
    skipped_files = [f for f, c in stream_counts.items() if c != mode_count]

    print(f"Analysis complete. The most common layout has {mode_count} audio streams. Processing {len(video_files_to_process)} files.")
    if skipped_files:
        print("\nWarning: The following files have an incompatible audio stream count and will be SKIPPED:")
        for f in skipped_files:
            print(f" - {os.path.basename(f)} (has {stream_counts.get(f, 'N/A')} audio streams)")

    if len(video_files_to_process) < 1 and len(initial_video_files) > 0:
        print("\nError: No files with a consistent audio stream layout were found.")
        return
    elif len(video_files_to_process) < 2:
        print(f"\nError: Only {len(video_files_to_process)} compatible video file found. Cannot concatenate.")
        return
        
    if args.output:
        final_output = args.output
    else:
        final_output = os.path.basename(video_files_to_process[0])
        print(f"No output name provided. Using first compatible input filename: {final_output}")

    # Build sets of source paths so output artifacts do not overwrite source files.
    input_video_abs_paths = {os.path.normcase(os.path.abspath(p)) for p in video_files_to_process}
    input_sidecar_abs_paths = set()
    for video_path in video_files_to_process:
        source_base, _ = os.path.splitext(video_path)
        for ext in ('.srt', '.txt'):
            sidecar_path = source_base + ext
            if os.path.isfile(sidecar_path):
                input_sidecar_abs_paths.add(os.path.normcase(os.path.abspath(sidecar_path)))

    # --- Initialize temporary file paths ---
    merged_srt_file = None
    metadata_file = None
    list_filename = f"mylist_{uuid.uuid4()}.txt"
    temp_output_filename = f"temp_concat_{uuid.uuid4()}{os.path.splitext(final_output)[1]}"
    
    try:
        # --- Stage 2: Pre-process Subtitles and Chapters ---
        print("\n--- Pre-processing Subtitles and Chapters ---")
        srt_entries = []
        youtube_chapters = []
        ffmpeg_chapters = []
        total_duration_offset = 0.0

        for video_file in video_files_to_process:
            try:
                probe = ffmpeg.probe(video_file)
                duration = float(probe['format']['duration'])
            except Exception as e:
                print(f"CRITICAL: Could not probe duration for {video_file}. Aborting. Error: {e}")
                return

            base, _ = os.path.splitext(video_file)
            
            # --- Chapter Processing ---
            json_txt_file = base + ".txt"
            chapter_title = os.path.basename(base) # Default title
            if os.path.exists(json_txt_file):
                try:
                    with open(json_txt_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if data and 'title' in data:
                            chapter_title = data['title']
                            print(f"Found chapter title: '{chapter_title}'")
                        else:
                            print(f"Warning: JSON in {os.path.basename(json_txt_file)} is empty or has no 'title'. Using filename.")
                except Exception as e:
                    print(f"Warning: Could not parse JSON from {os.path.basename(json_txt_file)}. Using filename. Error: {e}")
            
            youtube_chapters.append((seconds_to_youtube_time(total_duration_offset), chapter_title))
            ffmpeg_chapters.append({
                'start': int(total_duration_offset * 1000),
                'end': int((total_duration_offset + duration) * 1000),
                'title': chapter_title.replace('=', '\\=').replace(';', '\\;').replace('#', '\\#').replace('\\', '\\\\')
            })

            # --- Subtitle Processing ---
            srt_file = base + ".srt"
            if os.path.exists(srt_file) and os.path.getsize(srt_file) > 0:
                with open(srt_file, 'r', encoding='utf-8') as f:
                    # Normalize newlines so both LF and CRLF .srt files parse consistently.
                    content = f.read().lstrip('\ufeff').replace('\r\n', '\n').replace('\r', '\n')
                blocks = re.finditer(
                    r'(\d+)\s*\n'
                    r'(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})\s*\n'
                    r'([\s\S]*?(?=\n\n|\Z))',
                    content
                )
                for block in blocks:
                    start_sec = srt_time_to_seconds(block.group(2)) + total_duration_offset
                    end_sec = srt_time_to_seconds(block.group(3)) + total_duration_offset
                    srt_entries.append({'start': start_sec, 'end': end_sec, 'text': block.group(4)})

            total_duration_offset += duration

        # --- Stage 3: Write Temporary & Permanent Files ---
        if srt_entries:
            merged_srt_file = f"merged_subs_{uuid.uuid4()}.srt"
            with open(merged_srt_file, 'w', encoding='utf-8') as f:
                for i, entry in enumerate(srt_entries, 1):
                    f.write(f"{i}\n{seconds_to_srt_time(entry['start'])} --> {seconds_to_srt_time(entry['end'])}\n{entry['text']}\n\n")
            print(f"\nSuccessfully created merged subtitle file: {merged_srt_file}")

        if ffmpeg_chapters:
            metadata_file = f"metadata_{uuid.uuid4()}.txt"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                f.write(";FFMETADATA1\n")
                for chap in ffmpeg_chapters:
                    f.write("[CHAPTER]\nTIMEBASE=1/1000\n")
                    f.write(f"START={chap['start']}\nEND={chap['end']}\n")
                    f.write(f"title={chap['title']}\n")
            print(f"Successfully created FFmpeg metadata file: {metadata_file}")
        
        desired_output_chapters_file = os.path.splitext(final_output)[0] + ".txt"
        desired_output_chapters_abs = os.path.normcase(os.path.abspath(desired_output_chapters_file))
        if desired_output_chapters_abs in input_sidecar_abs_paths or desired_output_chapters_abs in input_video_abs_paths:
            output_chapters_file = f"chapters_{uuid.uuid4()}.txt"
            print(
                f"Chapter output path '{desired_output_chapters_file}' conflicts with an input file. "
                f"Writing to temporary '{output_chapters_file}' first."
            )
        else:
            output_chapters_file = desired_output_chapters_file

        with open(output_chapters_file, 'w', encoding='utf-8') as f:
            for ts, title in youtube_chapters:
                f.write(f"{ts} - {title}\n")
        print(f"Successfully created YouTube chapter file: {desired_output_chapters_file}")

        # --- Stage 4: Execute FFmpeg Two-Pass Process ---
        print("\n--- Pass 1: Concatenating video and audio streams ---")
        with open(list_filename, "w", encoding='utf-8') as f:
            for video_file in video_files_to_process:
                safe_path = os.path.abspath(video_file).replace("'", "'\\''")
                f.write(f"file '{safe_path}'\n")

        concat_command = ['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', list_filename, '-c', 'copy', temp_output_filename]
        print(f"  > {' '.join(concat_command)}")
        subprocess.run(concat_command, check=True, capture_output=True, text=True, encoding='utf-8')
        print("Pass 1 completed successfully.")

        print("\n--- Pass 2: Muxing subtitles and chapters ---")
        mux_command = ['ffmpeg', '-y', '-i', temp_output_filename]
        # Build the command with inputs in the correct order
        input_map_counter = 1
        if merged_srt_file:
            mux_command.extend(['-i', merged_srt_file])
        if metadata_file:
            mux_command.extend(['-i', metadata_file])

        # Map streams
        mux_command.extend(['-map', '0:v', '-map', '0:a'])  # only video and audio
        if merged_srt_file:
            mux_command.extend(['-map', str(input_map_counter)])
            input_map_counter += 1
        if metadata_file:
            mux_command.extend(['-map_metadata', str(input_map_counter)])

        # Set codecs
        mux_command.extend(['-c', 'copy']) # Stream copy everything from the concatenated video
        if merged_srt_file:
            output_ext = os.path.splitext(final_output)[1].lower()
            sub_codec = 'mov_text' if output_ext == '.mp4' else 'srt'
            mux_command.extend(['-c:s', sub_codec]) # But encode the subtitle stream
        
        final_output_abs = os.path.normcase(os.path.abspath(final_output))
        if final_output_abs in input_video_abs_paths:
            safe_final_output = f"merged_{uuid.uuid4()}_{os.path.basename(final_output)}"
            print(
                f"Output name matches an input file path. "
                f"Writing to temporary '{safe_final_output}' first."
            )
        else:
            safe_final_output = final_output

        mux_command.append(safe_final_output)
        
        print(f"  > {' '.join(mux_command)}")
        subprocess.run(mux_command, check=True, capture_output=True, text=True, encoding='utf-8')
        print("Pass 2 completed successfully.")
        
        print(f"\n--- SUCCESS ---")
        print(f"Successfully created final video '{final_output}'")
        
        output_srt_file = None
        safe_output_srt_file = None
        if args.extract_srt and merged_srt_file:
            output_srt_base, _ = os.path.splitext(final_output)
            output_srt_file = output_srt_base + ".srt"
            output_srt_abs = os.path.normcase(os.path.abspath(output_srt_file))
            if output_srt_abs in input_sidecar_abs_paths or output_srt_abs in input_video_abs_paths:
                safe_output_srt_file = f"subs_{uuid.uuid4()}.srt"
                print(
                    f"Subtitle output path '{output_srt_file}' conflicts with an input file. "
                    f"Writing to temporary '{safe_output_srt_file}' first."
                )
            else:
                safe_output_srt_file = output_srt_file

            print(f"\nSaving final merged subtitles to: {output_srt_file}")
            shutil.copy(merged_srt_file, safe_output_srt_file)

        protected_paths = [safe_final_output, output_chapters_file]
        if args.extract_srt and merged_srt_file and safe_output_srt_file:
            protected_paths.append(safe_output_srt_file)
        move_processed_videos_to_input_folder(video_files_to_process, INPUT_SUBDIR, protected_paths=protected_paths)

        if safe_final_output != final_output:
            os.replace(safe_final_output, final_output)
            print(f"Placed final video at '{final_output}'")
        if output_chapters_file != desired_output_chapters_file:
            os.replace(output_chapters_file, desired_output_chapters_file)
            print(f"Placed chapter file at '{desired_output_chapters_file}'")
        if safe_output_srt_file and output_srt_file and safe_output_srt_file != output_srt_file:
            os.replace(safe_output_srt_file, output_srt_file)
            print(f"Placed final subtitles at '{output_srt_file}'")

    except subprocess.CalledProcessError as e:
        print("\n--- FFMPEG ERROR ---")
        print("FFmpeg failed to execute. Review the error message below.")
        print(f"\n--- FFmpeg stderr ---\n{e.stderr}")
    except Exception as e:
        print(f"\n--- AN UNEXPECTED SCRIPT ERROR OCCURRED --- \n{e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n--- Cleaning up temporary files ---")
        for temp_file in [list_filename, temp_output_filename, merged_srt_file, metadata_file]:
            if temp_file and os.path.exists(temp_file):
                os.remove(temp_file)
                print(f"Removed: {os.path.basename(temp_file)}")

if __name__ == "__main__":
    main()
