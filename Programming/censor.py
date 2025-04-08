#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import csv
import math
import argparse
import os
import sys
import subprocess
import shlex

# --- Timecode Conversion Utilities ---
def srt_time_to_frames(time_str, frame_rate):
    time_parts = re.match(r'(\d{2}):(\d{2}):(\d{2}),(\d{3})', time_str)
    if not time_parts: raise ValueError(f"Invalid SRT time format: {time_str}")
    h, m, s, ms = map(int, time_parts.groups()); total_seconds = h * 3600 + m * 60 + s + ms / 1000.0
    return math.floor(total_seconds * frame_rate)

def frames_to_smpte(total_frames, frame_rate):
    if total_frames < 0: total_frames = 0
    frame_rate_float = float(frame_rate); int_frame_rate = int(round(frame_rate_float))
    frames = round(total_frames % frame_rate_float)
    if frames >= int_frame_rate: frames = int_frame_rate - 1
    total_seconds_int = int(total_frames // frame_rate_float)
    s = total_seconds_int % 60; total_minutes_int = total_seconds_int // 60
    m = total_minutes_int % 60; h = total_minutes_int // 60
    frame_digits = max(2, len(str(int_frame_rate - 1)))
    return f"{h:02d}:{m:02d}:{s:02d}:{int(frames):0{frame_digits}d}"

def duration_sec_to_frames(duration_sec, frame_rate):
    try: return math.floor(float(duration_sec) * frame_rate)
    except Exception: return None

# --- FCPXML Time Formatting Utilities ---
def frames_to_fcpxml_time(frames, frame_rate_num=60, frame_rate_den=1):
    return f"{int(frames) * frame_rate_den}/{frame_rate_num}s"

def duration_sec_to_fcpxml_time(seconds, frame_rate_num=60, frame_rate_den=1):
    total_frames = math.floor(float(seconds) * frame_rate_num / frame_rate_den)
    if total_frames <= 0: total_frames = 1
    return f"{total_frames * frame_rate_den}/{frame_rate_num}s"

# --- FFprobe Function ---
def get_video_duration_ffprobe(video_path):
    command = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", video_path]
    print(f"Attempting ffprobe...")
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True, timeout=10)
        duration_str = result.stdout.strip()
        if duration_str and duration_str != 'N/A': return float(duration_str)
        else: print("Warning: ffprobe returned no duration."); return None
    except FileNotFoundError: print("Warning: 'ffprobe' command not found."); return None
    except Exception as e: print(f"Warning: ffprobe failed: {e}"); return None

# --- SRT Parsing Function ---
def parse_srt(srt_file_path):
    srt_blocks = []; encodings_to_try = ['utf-8', 'utf-8-sig', 'iso-8859-1', 'cp1252']
    content = None; last_pos = 0
    if not os.path.isfile(srt_file_path): print(f"Error: SRT not found: {srt_file_path}"); return None
    for enc in encodings_to_try:
        try:
            with open(srt_file_path, 'r', encoding=enc) as f: content = f.read()
            print(f"Read SRT with encoding: {enc}"); break
        except Exception: print(f"Info: Failed encoding {enc}. Trying next...")
    if content is None: print(f"Error: Could not read SRT: {srt_file_path}."); return None
    block_pattern = re.compile(r'(\d+)\s+(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})\s*(.*?)(?=\n\s*\n|\n\s*\d+\s+\d{2}:\d{2}:\d{2},\d{3}|\Z)', re.DOTALL | re.MULTILINE)
    for match in block_pattern.finditer(content):
        try:
            seq_num=int(match.group(1)); start_time_str=match.group(2); end_time_str=match.group(3)
            text = match.group(4).strip().replace('\r\n', '\n')
            srt_blocks.append({'sequence': seq_num, 'start_time_str': start_time_str, 'end_time_str': end_time_str, 'text': text})
            last_pos = match.end()
        except Exception as e:
            seq_id_str=match.group(1) if match and match.group(1) else 'UNK'; print(f"Warn: Err parsing SRT block near '{seq_id_str}' at pos {match.start() if match else 'N/A'}. Err: {e}")
            next_block_match = re.search(r'\n\s*\n\s*(\d+)\s*\n', content[last_pos:])
            if next_block_match: last_pos += next_block_match.start()
            else: print("Warn: Could not recover parsing."); break
    if not srt_blocks: print("Warn: No valid SRT blocks parsed."); return None
    srt_blocks.sort(key=lambda x: x['sequence'])
    return srt_blocks

# --- List File Parsing Function ---
def parse_list_file(list_file_path):
    sequences = set()
    if not os.path.isfile(list_file_path): print(f"Error: List file not found: {list_file_path}"); return None
    try:
        with open(list_file_path, 'r', encoding='utf-8') as f: content = f.read()
        numbers = re.findall(r'\d+', content)
        for num_str in numbers:
             try: sequences.add(int(num_str))
             except ValueError: print(f"Warn: Could not parse '{num_str}' as int in {list_file_path}.")
    except Exception as e: print(f"Error reading list file: {e}"); return None
    return sequences

# --- Get Blocks by Mode Function ---
def get_blocks_to_process(srt_data, sequence_list_set, mode='remove'):
    processed_blocks = []
    if not srt_data: return []
    for block in srt_data:
        in_list = block['sequence'] in sequence_list_set
        if mode == 'remove' and not in_list: processed_blocks.append(block)
        elif mode == 'censor' and in_list: processed_blocks.append(block)
    return processed_blocks

# --- Calculate Frames Function ---
def calculate_block_frames(blocks_data, frame_rate):
    blocks_with_frames = []
    for block in blocks_data:
        try:
            start_frames = srt_time_to_frames(block['start_time_str'], frame_rate)
            end_frames = srt_time_to_frames(block['end_time_str'], frame_rate)
            if end_frames <= start_frames: end_frames = start_frames + 1
            block['start_frames'] = start_frames; block['end_frames'] = end_frames
            blocks_with_frames.append(block)
        except ValueError as e: print(f"Warn: Skip block {block['sequence']} timecode err: {e}"); continue
    return blocks_with_frames

# --- Consolidate Continuous Blocks ---
def consolidate_continuous_blocks(blocks_with_frames, gap_tolerance_frames=1):
    if not blocks_with_frames: return []
    blocks_with_frames.sort(key=lambda x: x['start_frames'])
    consolidated = []; current_segment = blocks_with_frames[0].copy()
    current_segment['sequences'] = [current_segment['sequence']]
    for i in range(1, len(blocks_with_frames)):
        prev_block_end = current_segment['end_frames']; current_block = blocks_with_frames[i]
        if current_block['start_frames'] <= prev_block_end + gap_tolerance_frames:
            current_segment['end_frames'] = max(current_segment['end_frames'], current_block['end_frames'])
            current_segment['sequences'].append(current_block['sequence'])
        else:
            consolidated.append(current_segment); current_segment = current_block.copy()
            current_segment['sequences'] = [current_segment['sequence']]
    consolidated.append(current_segment)
    return consolidated

# --- Chapter Marker Logic for Segmented Timeline ---
def get_chapter_markers_segmented(consolidated_segments, frame_rate):
    chapters=[{"name":"Ch 1: Tariffs Announced, Initial Reactions & Economic Anxiety","time_sec":0},{"name":"Ch 2: Analyzing Tariffs - Motives, Global Reactions","time_sec":3600},{"name":"Ch 3: Tariff Calculations, Trump Mindset, Political Fallout","time_sec":7200},{"name":"Ch 4: Valuetainment Segment - Sam Cedar vs Vinny","time_sec":10800},{"name":"Ch 5: Debunking Misinformation & Miscellaneous Topics","time_sec":14400},{"name":"Ch 6: Ethan Klein Legal Threats & Fallout (Factual Focus)","time_sec":18000},{"name":"Ch 7: Final Discussions, Debunks, and Stream Outro","time_sec":21600}]
    markers_xml_list = []; placed_chapters = set()
    chapter_source_frames = {ch['name']: math.floor(ch['time_sec'] * frame_rate) for ch in chapters}
    if not consolidated_segments: return ""
    int_frame_rate = int(round(frame_rate)); cumulative_timeline_duration_frames = 0
    for segment in consolidated_segments:
        segment_start_timeline_frame = cumulative_timeline_duration_frames
        segment_duration_frames = max(1, segment['end_frames'] - segment['start_frames'])
        segment_start_source_frame = segment['start_frames']
        for ch_name, ch_start_source_frame_approx in chapter_source_frames.items(): # Corrected iteration
            if ch_name not in placed_chapters and segment_start_source_frame >= ch_start_source_frame_approx:
                safe_ch_name = ch_name.replace("&","&").replace("<","<").replace(">",">")
                marker_start_fcpxml = frames_to_fcpxml_time(segment_start_timeline_frame, int_frame_rate)
                marker_tag = f"""<marker start="{marker_start_fcpxml}" duration="1/{int_frame_rate}s" value="{safe_ch_name}">
                            <markerinfo><key>MarkerType</key><value>Chapter</value></markerinfo>
                        </marker>"""
                markers_xml_list.append(marker_tag)
                placed_chapters.add(ch_name)
        cumulative_timeline_duration_frames += segment_duration_frames
    if "Ch 1: Tariffs Announced, Initial Reactions & Economic Anxiety" not in placed_chapters and consolidated_segments:
         safe_ch_name="Ch 1: Tariffs Announced, Initial Reactions & Economic Anxiety".replace("&","&")
         marker_tag_ch1 = f"""<marker start="0s" duration="1/{int_frame_rate}s" value="{safe_ch_name}">
                            <markerinfo><key>MarkerType</key><value>Chapter</value></markerinfo>
                        </marker>"""
         markers_xml_list.insert(0, marker_tag_ch1)
    # Place markers at sequence level - requires adjustment in calling function
    return "".join([' ' * 20 + m + '\n' for m in markers_xml_list]) 

# --- FCPXML Generation Function (Segmented Clips - Handles Both Modes) ---
def generate_fcpxml_segmented_clips(output_path, video_path, frame_rate, consolidated_segments, mode, total_duration_sec=None):
    output_base_name = os.path.basename(output_path).replace('.fcpxml', '')
    video_base_name = os.path.basename(video_path)
    int_frame_rate = int(round(frame_rate))
    frame_duration_str = f"1/{int_frame_rate}s"
    format_id = "r0"; asset_id = "r1"
    if not consolidated_segments: print("No segments."); return
    final_sequence_duration_frames = sum(max(1, seg['end_frames'] - seg['start_frames']) for seg in consolidated_segments)
    total_source_duration_needed_frames = max(seg['end_frames'] for seg in consolidated_segments) if consolidated_segments else 0
    asset_tag_duration_sec = total_source_duration_needed_frames / frame_rate
    if total_duration_sec is not None: asset_tag_duration_sec = max(asset_tag_duration_sec, total_duration_sec)
    else: print("Asset duration based on last needed source frame.")
    asset_duration_fcpxml = duration_sec_to_fcpxml_time(asset_tag_duration_sec, int_frame_rate)
    sequence_duration_fcpxml = duration_sec_to_fcpxml_time(final_sequence_duration_frames / frame_rate, int_frame_rate)
    chapter_markers_str = ""
    if mode == 'remove': chapter_markers_str = get_chapter_markers_segmented(consolidated_segments, frame_rate)
    abs_video_path = os.path.abspath(video_path)
    video_path_url = abs_video_path.replace('\\', '/')
    if ':' in video_path_url: drive = video_path_url.split(':')[0]; path_part = video_path_url.split(':', 1)[1]
    if not path_part.startswith('/'): path_part = '/' + path_part
    video_path_url = f"/{drive.upper()}{path_part}"
    video_path_url = 'file://localhost' + video_path_url
    xml_content = f"""<?xml version="1.0" encoding="UTF-8"?><fcpxml version="1.9"><resources><format id="{format_id}" name="FFVideoFormat1080p{int_frame_rate}" frameDuration="{frame_duration_str}" width="1920" height="1080" colorSpace="1-1-1 (Rec. 709)"/><asset id="{asset_id}" name="{video_base_name}" start="0s" duration="{asset_duration_fcpxml}" hasVideo="1" hasAudio="1" audioSources="1" audioChannels="2" audioRate="48000"><media-rep kind="original-media" src="{video_path_url}"/></asset></resources><library><event name="{output_base_name}_Event"><project name="{output_base_name}"><sequence duration="{sequence_duration_fcpxml}" format="{format_id}" tcStart="0s" tcFormat="NDF" audioLayout="stereo" audioRate="48k">{chapter_markers_str}<spine>""" # Chapter markers at sequence level
    current_timeline_start_frame = 0; clip_count = 0
    for segment in consolidated_segments:
        clip_count += 1; source_in_frames = segment['start_frames']; source_out_frames = segment['end_frames']
        duration_frames = max(1, source_out_frames - source_in_frames)
        timeline_start_fcpxml = frames_to_fcpxml_time(current_timeline_start_frame, int_frame_rate)
        source_start_fcpxml = frames_to_fcpxml_time(source_in_frames, int_frame_rate)
        duration_fcpxml = frames_to_fcpxml_time(duration_frames, int_frame_rate)
        clip_name = f"Segment_{clip_count}"; seq_list = segment.get('sequences', [])
        seq_comment = f"SRT(s): {seq_list[0]}..{seq_list[-1]}" if len(seq_list)>1 else f"SRT: {seq_list[0]}"
        xml_content += f"""<asset-clip ref="{asset_id}" offset="{timeline_start_fcpxml}" name="{clip_name}" start="{source_start_fcpxml}" duration="{duration_fcpxml}" format="{format_id}"><marker start="0s" duration="{duration_fcpxml}" value="{seq_comment}"/><audio ref="{asset_id}" lane="-1" offset="{timeline_start_fcpxml}" name="{clip_name} Audio" start="{source_start_fcpxml}" duration="{duration_fcpxml}" role="dialogue"/></asset-clip>"""
        current_timeline_start_frame += duration_frames
    xml_content += """</spine></sequence></project></event></library></fcpxml>"""
    try:
        with open(output_path, 'w', encoding='utf-8') as f: f.write(xml_content)
        print(f"FCPXML v1.9 (Segmented, Gaps Removed) generated: {output_path}")
    except Exception as e: print(f"Error writing FCPXML file: {e}")

# --- FCPXML Generation Function (Censor Mode - No Video - Gaps) ---
def generate_fcpxml_censored_gaps(output_path, frame_rate, censored_blocks):
    output_base_name = os.path.basename(output_path).replace('.fcpxml', '')
    int_frame_rate = int(round(frame_rate)); format_id = "r0"
    if not censored_blocks: print("No blocks for censor mode."); return
    censored_blocks.sort(key=lambda x: x['start_frames'])
    final_sequence_duration_frames = sum(max(1, block['end_frames'] - block['start_frames']) for block in censored_blocks)
    sequence_duration_fcpxml = duration_sec_to_fcpxml_time(final_sequence_duration_frames / frame_rate, int_frame_rate)
    xml_content = f"""<?xml version="1.0" encoding="UTF-8"?><fcpxml version="1.9"><resources><format id="{format_id}" name="FFVideoFormat1080p{int_frame_rate}" frameDuration="1/{int_frame_rate}s" width="1920" height="1080"/></resources><library><event name="{output_base_name}_Event"><project name="{output_base_name}"><sequence duration="{sequence_duration_fcpxml}" format="{format_id}" tcStart="0s" tcFormat="NDF"><spine>"""
    current_timeline_start_frame = 0; clip_count = 0
    for block in censored_blocks:
        clip_count += 1
        duration_frames = max(1, block['end_frames'] - block['start_frames'])
        timeline_offset_fcpxml = frames_to_fcpxml_time(current_timeline_start_frame, int_frame_rate)
        duration_fcpxml = frames_to_fcpxml_time(duration_frames, int_frame_rate)
        gap_name = f"Censored_SRT_{block['sequence']}" 
        xml_content += f"""<gap offset="{timeline_offset_fcpxml}" name="{gap_name}" duration="{duration_fcpxml}" start="{timeline_offset_fcpxml}"/>"""
        current_timeline_start_frame += duration_frames
    xml_content += """</spine></sequence></project></event></library></fcpxml>"""
    try:
        with open(output_path, 'w', encoding='utf-8') as f: f.write(xml_content)
        print(f"FCPXML v1.9 (Censored Gaps Only) generated: {output_path}")
    except Exception as e: print(f"Error writing FCPXML file: {e}")

# --- Argument Parser Definition ---
def setup_parser():
    parser = argparse.ArgumentParser(
        description="Generate FCPXML v1.9 from SRT. Use -r to remove listed SRT blocks + gaps, or -c to keep ONLY listed blocks (video optional). Flags are required.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    # Flagged arguments ARE NOW REQUIRED
    parser.add_argument("-s", "--srt", required=True, help="Path to input SRT file.")
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument("-r", "--remove", metavar='LIST_FILE', help="CSV/Text file listing sequence numbers to REMOVE.")
    mode_group.add_argument("-c", "--censor", metavar='LIST_FILE', help="CSV/Text file listing sequence numbers to KEEP (output only these).")
    parser.add_argument("-v", "--video", help="Path to source video file (Required for -r mode).")
    parser.add_argument("-o", "--output", required=True, help="Path for output FCPXML file.")
    parser.add_argument("-f", "--framerate", type=float, default=60.0, help="Video frame rate.")
    parser.add_argument("-d", "--duration", type=float, default=None, help="Optional: Total source video duration (seconds). Detects via ffprobe if omitted.")
    return parser

# --- Main Execution Logic ---
def main():
    parser = setup_parser()
    
    # Enforce flag usage
    if any(not arg.startswith('-') for arg in sys.argv[1:] if arg not in ['-h', '--help']):
         # Check if there are non-flag args other than potential values *after* flags
         first_non_flag_index = -1
         for i, arg in enumerate(sys.argv[1:]):
             if not arg.startswith('-'):
                  # Is the preceding arg a flag that expects a value?
                  if i > 0 and sys.argv[i] in ['-s', '--srt', '-r', '--remove', '-c', '--censor', '-v', '--video', '-o', '--output', '-f', '--framerate', '-d', '--duration']:
                      continue # This is likely a value for a flag
                  else:
                      first_non_flag_index = i
                      break
         if first_non_flag_index != -1:
            print("Error: Positional arguments are no longer supported. Please use flags (-s, -r/-c, -v, -o).")
            parser.print_help()
            sys.exit(1)
            
    try:
        args = parser.parse_args()
    except SystemExit as e:
        sys.exit(e.code) # Let argparse handle help/errors

    # Determine mode and list file path from parsed args
    mode = 'remove' if args.remove else 'censor'
    list_file = args.remove if args.remove else args.censor
    output_file = args.output
    video_file = args.video
    framerate = args.framerate
    duration = args.duration

    # Validate video requirement based on mode
    if mode == 'remove' and not video_file:
        parser.error("Argument -v/--video is required when using -r/--remove mode.")

    # --- Validate paths ---
    abs_video_path = os.path.abspath(video_file) if video_file else None
    if not os.path.isfile(args.srt): print(f"Error: Input SRT not found: {args.srt}"); exit(1)
    if not os.path.isfile(list_file): print(f"Error: List file not found: {list_file}"); exit(1)
    if video_file and not os.path.isfile(abs_video_path): print(f"Error: Video file not found: {abs_video_path}"); exit(1)

    print(f"\n--- Processing ---")
    print(f"Mode: {mode.upper()}")
    if abs_video_path: print(f"Video Path: {abs_video_path}")
    else: print("Video Path: None")
    print(f"SRT File: {args.srt}")
    print(f"List File: {list_file}")
    print(f"Output FCPXML: {output_file}")
    print(f"Frame Rate: {framerate}")

    # --- Get Video Duration ---
    video_duration_sec = duration
    if video_duration_sec is None and abs_video_path:
        video_duration_sec = get_video_duration_ffprobe(abs_video_path)
        if video_duration_sec: print(f"Detected duration: {video_duration_sec:.2f}s.")
        else: print("Could not detect duration.")

    # --- Process ---
    srt_data = parse_srt(args.srt)
    list_set = parse_list_file(list_file)
    if srt_data is None or list_set is None: print("Exiting due to parse errors."); exit(1)

    print(f"Parsed {len(srt_data)} SRT blocks. Using {len(list_set)} sequences from list file for {mode}ing.")

    blocks_to_process_orig = get_blocks_to_process(srt_data, list_set, mode)
    if not blocks_to_process_orig: print(f"Error: No blocks found to {mode}. Output will be empty."); exit(1)

    blocks_with_frames = calculate_block_frames(blocks_to_process_orig, framerate)
    if not blocks_with_frames: print(f"Error: Failed frame calculation."); exit(1)
    print(f"Processing {len(blocks_with_frames)} relevant SRT blocks.")

    # --- Generate FCPXML ---
    if mode == 'censor' and not video_file:
        print("Generating FCPXML with gap elements...")
        generate_fcpxml_censored_gaps(output_file, framerate, blocks_with_frames)
    elif abs_video_path:
        print("Consolidating continuous segments...")
        consolidated_segments = consolidate_continuous_blocks(blocks_with_frames)
        if not consolidated_segments: print("Error: Failed to consolidate segments."); exit(1)
        print(f"Consolidated into {len(consolidated_segments)} continuous segments.")
        print("Generating FCPXML with asset clips...")
        generate_fcpxml_segmented_clips(output_file, abs_video_path, framerate, consolidated_segments, mode, video_duration_sec)
    else: # Should be caught by initial checks
         print("Error: Cannot generate video clips for remove mode without a video file (-v/--video).")
         exit(1)

if __name__ == "__main__":
    main()