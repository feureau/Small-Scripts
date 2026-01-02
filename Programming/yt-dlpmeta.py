"""
SCRIPT DOCUMENTATION AND USAGE GUIDE
====================================

Overview
--------
This script (`yt-meta.py`) is a utility for extracting metadata from YouTube channels, playlists, 
or individual videos using the `yt-dlp` library. It exports video lists to CSV files and supports 
extracting detailed metadata (including comments) for individual videos into JSON files.
It also supports downloading subtitles and heatmaps as separate files and integrated into metadata.

Features
--------
1. Channel/Playlist Export:
   - FAST mode (Default): Rapidly scrapes video lists without visiting every video page. 
     Extracts ID, Title, URL, Duration.
   - FULL mode (`-f/--full`): Visits every video page to extract enriched metadata like view counts, 
     upload dates, and descriptions (slower).
   
2. Single Video Export:
   - Automatically detects if the input URL is a single video.
   - Always fetches full metadata for the single video.
   - Exports a detailed JSON file containing all available metadata (tags, description, heatmaps, etc.).
   
3. Comment Extraction (`-c/--comment`):
   - Downloads all available comments for the video(s).
   - For single videos: Comments are saved in the metadata JSON.
   - For channels: WARNING - This is extremely slow as it downloads comments for EVERY video.

4. Subtitle Downloading (`-s/--sub`):
   - Downloads subtitles (manual or auto-generated) as separate files (.srt/.vtt).
   - Also integrates subtitle metadata tracks into the JSON output.

5. Heatmap Extraction (`-H/--heatmap`):
   - Extracts heatmap data to a separate JSON file.
   - Also integrates heatmap keys into the metadata JSON output.

Usage
-----
Run the script from the command line:

    python yt-meta.py [URL] [OPTIONS]

Arguments:
    URL             The URL of the YouTube channel, playlist, or single video (or a path to a list file).
    -f, --full      (Channel/Playlist only) Fetch FULL metadata. Slower, but provides more details.
    -c, --comment   Download ALL comments.
    -s, --sub       Download Subtitles as separate files and include in metadata.
    -H, --heatmap   Extract Heatmap to separate JSON and include in metadata.
    -k, --condensed Clean & Condensed Output (Default for Single Videos).
    -r, --raw       Full Raw Output (Disables Condensed Mode).
    -C, --csv       Force CSV output (Default for FAST mode).
    -j, --json      Force JSON output (Default for DEEP mode).

Output
------
- CSV Files: Generated for channels/playlists (summary of videos).
- JSON Files: Generated for single videos (comprehensive metadata) or for channels if forced.
- Subtitle Files: .srt or .vtt files if --sub is used.
- Heatmap Files: _heatmap.json files if --heatmap is used.

Dependencies
------------
- python 3.x
- yt_dlp (`pip install yt-dlp`)

Version History & Notes
-----------------------
- Revision: 2.1 (Subtitles & Heatmaps)
- documentation must be included and updated with every revision.
"""

import yt_dlp
import sys
import os
import json
import csv
import argparse
import re
import glob
from datetime import datetime

# ==========================================
# Helper Function: Condense Metadata
# ==========================================
def condense_metadata(info):
    """
    Simplifies the metadata to only essential fields.
    """
    # Desired fields to keep
    keys_to_keep = [
        'id', 'title', 'description', 'uploader', 'uploader_id', 'uploader_url',
        'upload_date', 'timestamp', 'duration', 'view_count', 'like_count', 
        'comment_count', 'channel', 'channel_id', 'channel_url', 
        'categories', 'tags', 'heatmaps', 'webpage_url', 'transcript',
        'subtitles', 'automatic_captions' # Added for integrated metadata
    ]
    
    condensed = {k: info.get(k) for k in keys_to_keep if info.get(k) is not None}
    
    # Clean up Subtitles/Captions metadata (too noisy)
    # Just keep the language keys if available
    for key in ['subtitles', 'automatic_captions']:
        if key in condensed and isinstance(condensed[key], dict):
            condensed[key] = list(condensed[key].keys())

    # Simplify Comments
    if 'comments' in info and info['comments']:
        simplified_comments = []
        for c in info['comments']:
            # Keep only requested fields
            simplified_comments.append({
                'author': c.get('author'),
                'text': c.get('text'),
                'like_count': c.get('like_count')
            })
        condensed['comments'] = simplified_comments
    
    return condensed

# ==========================================
# Helper Function: Clean SRT Content
# ==========================================
def clean_srt(content):
    """
    Strips timestamps and sequence numbers from SRT content.
    """
    # Remove sequence numbers and timestamps
    # Pattern: \d+\n\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}
    content = re.sub(r'\d+\n\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}', '', content)
    
    # Remove remaining VTT-style timestamps if any
    content = re.sub(r'\d{2}:\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}:\d{2}\.\d{3}', '', content)
    
    # Remove HTML tags
    content = re.sub(r'<[^>]*>', '', content)
    
    # Clean up whitespace
    lines = [line.strip() for line in content.split('\n') if line.strip()]
    
    # Remove potential duplicates (common in auto-captions)
    unique_lines = []
    for line in lines:
        if not unique_lines or line != unique_lines[-1]:
            unique_lines.append(line)
            
    return " ".join(unique_lines)

# ==========================================
# Helper Function: Get Subtitle Content
# ==========================================
def get_subtitle_content(video_id, title, output_dir=None):
    """
    Locates and reads the primary subtitle file for a video.
    Returns cleaned text.
    """
    # Sanitize title as per outtmpl
    # ydl_opts['outtmpl'] = '%(title)s_%(id)s.%(ext)s'
    # Actually yt-dlp might sanitize it differently. Let's use glob with ID.
    
    search_pattern = f"*_{video_id}.*.srt"
    if output_dir:
        search_pattern = os.path.join(output_dir, search_pattern)
    
    files = glob.glob(search_pattern)
    if not files:
        # Try without the title prefix just in case (e.g. if title processing was different)
        search_pattern = f"*{video_id}*.srt"
        if output_dir:
            search_pattern = os.path.join(output_dir, search_pattern)
        files = glob.glob(search_pattern)

    if not files:
        return None

    # Pick the first one (since we target 'orig' now, it should be the primary track)
    target_file = files[0]

    # print(f"Reading subtitle: {os.path.basename(target_file)}")
    
    try:
        with open(target_file, 'r', encoding='utf-8') as f:
            content = f.read()
            return clean_srt(content)
    except Exception as e:
        print(f"Error reading subtitle file {target_file}: {e}")
        return None

# ==========================================
# Helper Function: Save Metadata (Individual JSON)
# ==========================================
def save_metadata_to_json(info_dict, output_dir=None, force_condensed=False):
    """
    Saves the info_dict to a JSON file (Deep Mode).
    Supports forced condensed mode.
    """
    
    if not info_dict:
        return

    # Condense if requested
    if force_condensed:
        info_dict = condense_metadata(info_dict)

    video_id = info_dict.get('id', 'UnknownID')
    title = info_dict.get('title', 'UnknownTitle')
    
    # Sanitize title for filename
    safe_title = "".join([c for c in title if c.isalpha() or c.isdigit() or c in (' ', '-', '_')]).strip().replace(" ", "_")
    
    # Create filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_filename = f"{safe_title}_{video_id}_metadata_{timestamp}.json"
    
    if output_dir:
        output_path = os.path.join(output_dir, json_filename)
    else:
        output_path = os.path.join(os.getcwd(), json_filename)

    print(f"Saving metadata to: {json_filename}")
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(info_dict, f, indent=4, ensure_ascii=False)
        # print("Done.") # Reduce noise
    except IOError as e:
        print(f"Error saving file: {e}")

# ==========================================
# Helper Function: Save Heatmap (Individual JSON)
# ==========================================
def save_heatmap_to_json(info_dict, output_dir=None):
    """
    Extracts and saves heatmap data to a separate JSON.
    """
    heatmaps = info_dict.get('heatmaps')
    if not heatmaps:
        return

    video_id = info_dict.get('id', 'UnknownID')
    title = info_dict.get('title', 'UnknownTitle')
    safe_title = "".join([c for c in title if c.isalnum() or c in (' ', '-', '_')]).strip().replace(" ", "_")
    
    json_filename = f"{safe_title}_{video_id}_heatmap.json"
    
    if output_dir:
        output_path = os.path.join(output_dir, json_filename)
    else:
        output_path = os.path.join(os.getcwd(), json_filename)

    print(f"Saving heatmap to: {json_filename}")
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(heatmaps, f, indent=4, ensure_ascii=False)
    except IOError as e:
        print(f"Error saving heatmap: {e}")

# ==========================================
# Helper Function: Save CSV (List)
# ==========================================
def save_list_to_csv(video_entries, filename):
    """
    Saves a list of video entries to a CSV file.
    """
    if not video_entries:
        return

    # Define standard columns
    # Try to grab common fields. Flat extraction usually has: id, title, url, duration, uploader, view_count (maybe)
    columns = ['id', 'title', 'url', 'duration', 'view_count', 'upload_date', 'uploader']
    
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=columns, extrasaction='ignore')
            writer.writeheader()
            
            for entry in video_entries:
                # Ensure URL exists
                if 'url' not in entry and 'id' in entry:
                    entry['url'] = f"https://www.youtube.com/watch?v={entry['id']}"
                    
                writer.writerow(entry)
        print(f"Successfully exported {len(video_entries)} videos to CSV: {filename}")
    except IOError as e:
        print(f"Error writing CSV: {e}")

# ==========================================
# Helper Function: Save JSON (List)
# ==========================================
def save_list_to_json(video_entries, filename):
    """
    Saves a list of video entries to a single JSON file.
    """
    if not video_entries:
        return
        
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(video_entries, f, indent=4, ensure_ascii=False)
        print(f"Successfully exported {len(video_entries)} videos to JSON: {filename}")
    except IOError as e:
        print(f"Error writing JSON: {e}")

# ==========================================
# Core Processing Function
# ==========================================
def process_url(url, fetch_full_metadata=False, fetch_comments=False, fetch_sub=False, fetch_heatmap=False, output_format=None, condensed_mode=None):
    """
    Main logic to handle the URL.
    """
    
    # default options
    ydl_opts = {
        'quiet': True,           # Don't print standard logs
        'ignoreerrors': True,    # Skip errors
        'extract_flat': True,    # Default to FAST mode
        'dump_single_json': True,
    }

    # LOGIC: Adjust options based on flags
    
    # Heuristic: If explicitly a single video URL (and NOT a playlist), default to Deep Mode
    # This ensures we get descriptions/heatmaps for single videos without needing --full
    if not fetch_full_metadata:
        # Check for common single video patterns and absence of playlist indicators
        is_single_heuristic = ("watch?v=" in url or "youtu.be/" in url or "shorts/" in url) and ("list=" not in url)
        if is_single_heuristic:
            # Default to Deep Mode + Comments + Condensed
            fetch_full_metadata = True
            fetch_comments = True
            
            # Use Condensed Mode unless user explictly asked for full/raw data
            if condensed_mode is None: # None implies "Auto/Default"
                 condensed_mode = True
                 
            if condensed_mode:
                print("Single Video detected: Fetching rich metadata (Condensed Output).")
            else:
                print("Single Video detected: Fetching rich metadata (Raw Output).")

    # Comments = Deep Mode
    if fetch_comments:
        fetch_full_metadata = True 
        print("Enabling comment extraction...")
        ydl_opts['getcomments'] = True

    # Heatmaps = Deep Mode
    if fetch_heatmap:
        print("Enabling heatmap extraction...")
        fetch_full_metadata = True

    # Subtitles
    if fetch_sub:
        print("Enabling subtitle extraction...")
        ydl_opts['writesubtitles'] = True
        ydl_opts['writeautomaticsub'] = True
        ydl_opts['subtitleslangs'] = ['orig'] # Focus on the original source language
        ydl_opts['subtitlesformat'] = 'srt/best'
        ydl_opts['skip_download'] = True
        
        # Ensure subtitle filename matches our convention
        # yt-dlp uses outtmpl for subtitles too
        ydl_opts['outtmpl'] = '%(title)s_%(id)s.%(ext)s'
    
    # --full = Deep Mode
    if fetch_full_metadata:
        ydl_opts['extract_flat'] = False

    print(f"Processing URL: {url}")
    if fetch_comments:
        print("Note: Comment downloading is enabled. This may take a while.")
    
    # Mode Announcement
    if not is_single_heuristic:
        mode_str = "DEEP (Full Metadata)" if fetch_full_metadata else "FAST (List Only)"
        print(f"Channel/Playlist Mode: {mode_str}")

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # 1. Extract Info
            info_dict = ydl.extract_info(url, download=False)
            
            if info_dict is None:
                print("Error: Could not extract information.")
                return

            # 2. Identify Content Type
            is_single_video = 'entries' not in info_dict

            if is_single_video:
                # Resolve Auto-Condensed State if it was still None
                if condensed_mode is None:
                    condensed_mode = True # Default for single

                # If subtitles requested, we need to call download
                if fetch_sub:
                    ydl.extract_info(url, download=True)

                handle_single_video(info_dict, use_condensed=condensed_mode, fetch_sub=fetch_sub, fetch_heatmap=fetch_heatmap)
            else:
                handle_channel_or_playlist(info_dict, fetch_full_metadata, fetch_comments, fetch_sub, fetch_heatmap, output_format)

    except Exception as e:
        print(f"\nAn error occurred: {e}")

def handle_single_video(info_dict, use_condensed=False, fetch_sub=False, fetch_heatmap=False):
    title = info_dict.get('title', 'UnknownTitle')
    print(f"Detected Single Video: {title}")
    
    if fetch_sub:
        title = info_dict.get('title', 'UnknownTitle')
        video_id = info_dict.get('id', 'UnknownID')
        transcript = get_subtitle_content(video_id, title)
        if transcript:
             info_dict['transcript'] = transcript

    # Save Metadata JSON
    save_metadata_to_json(info_dict, force_condensed=use_condensed)
    
    # Save Heatmap if requested
    if fetch_heatmap:
        save_heatmap_to_json(info_dict)

    # Subtitles are handled by process_url if we use download=True there.
    # Refactoring: Let's move the final extract_info(download=True) call here if needed
    # OR just ensure process_url does it.
    # I will update process_url later slightly to ensure it.

# ==========================================
# Channel/Playlist Handler
# ==========================================
def handle_channel_or_playlist(info_dict, is_deep_mode, fetch_comments, fetch_sub, fetch_heatmap, output_format):
    """
    Handles processing for a channel or playlist.
    """
    channel_name = info_dict.get('uploader', info_dict.get('title', 'Unknown_Channel'))
    
    if 'entries' in info_dict:
        # Convert to list immediately
        video_entries = list(info_dict['entries'])
    else:
        print("No videos found.")
        return

    print(f"Found {len(video_entries)} videos.")

    # Sanitize channel name for filenames
    safe_title = "".join([c for c in channel_name if c.isalpha() or c.isdigit() or c in (' ', '-', '_')]).strip().replace(" ", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # ============================
    # FAST MODE (Flat Extraction)
    # ============================
    if not is_deep_mode:
        # Default to CSV if not meant to be JSON
        if output_format == 'json':
             filename = f"{safe_title}_videos_{timestamp}.json"
             save_list_to_json(video_entries, filename)
        else:
             # Default to CSV
             filename = f"{safe_title}_videos_{timestamp}.csv"
             save_list_to_csv(video_entries, filename)
        
        # If user also asked for subs/heatmaps in FAST mode, we need to iterate now
        if fetch_sub or fetch_heatmap:
            print(f"\nAdditive Resource Extraction (-s/-H) triggered for {len(video_entries)} videos...")
            extract_deep_resources(video_entries, fetch_sub, fetch_heatmap, fetch_comments, output_dir=None)
        
        return

    # ============================
    # DEEP MODE (Full Extraction)
    # ============================
    output_dir = f"{safe_title}_{timestamp}"
    os.makedirs(output_dir, exist_ok=True)
    print(f"Created output directory: {output_dir}")
    print("Starting deep metadata extraction...")

    extract_deep_resources(video_entries, fetch_sub, fetch_heatmap, fetch_comments, output_dir=output_dir)

# ==========================================
# Helper Function: Deep Resource Extraction
# ==========================================
def extract_deep_resources(video_entries, fetch_sub, fetch_heatmap, fetch_comments, output_dir=None):
    """
    Iterates through video entries to fetch subtitles, heatmaps, or full metadata.
    """
    
    video_ydl_opts = {
        'quiet': True,
        'ignoreerrors': True,
        'extract_flat': False, 
        'dump_single_json': True,
    }
    
    if fetch_comments:
        video_ydl_opts['getcomments'] = True
        
    if fetch_sub:
        video_ydl_opts['writesubtitles'] = True
        video_ydl_opts['writeautomaticsub'] = True
        video_ydl_opts['subtitleslangs'] = ['orig']
        video_ydl_opts['subtitlesformat'] = 'srt/best'
        video_ydl_opts['skip_download'] = True
        
    count = 0
    with yt_dlp.YoutubeDL(video_ydl_opts) as v_ydl:
        for index, entry in enumerate(video_entries, start=1):
            video_url = entry.get('url')
            video_title = entry.get('title', 'Unknown_Title')
            video_id = entry.get('id')
            
            # Progress update
            print(f"[{index}/{len(video_entries)}] Processing: {video_title}")
            
            if not video_url:
                if video_id:
                    video_url = f"https://www.youtube.com/watch?v={video_id}"
                else:
                    continue

            # Set output template for subtitles if in a directory
            if output_dir:
                # Sanitize title for filename
                s_title = "".join([c for c in video_title if c.isalnum() or c in (' ', '-', '_')]).strip().replace(" ", "_")
                v_ydl.params['outtmpl'] = os.path.join(output_dir, f"{s_title}_{video_id}.%(ext)s")
            else:
                v_ydl.params['outtmpl'] = '%(title)s_%(id)s.%(ext)s'

            try:
                # Re-extract full info (download=True if we want subs)
                full_info = v_ydl.extract_info(video_url, download=fetch_sub)
                
                if full_info:
                     # If subtitles requested, embed transcript
                     if fetch_sub:
                          transcript = get_subtitle_content(video_id, video_title, output_dir=output_dir)
                          if transcript:
                               full_info['transcript'] = transcript

                     # Only save metadata JSON if output_dir is provided (implies DEEP/Full mode)
                     if output_dir:
                         save_metadata_to_json(full_info, output_dir=output_dir)
                     
                     # Heatmap is always additive if requested
                     if fetch_heatmap:
                         save_heatmap_to_json(full_info, output_dir=output_dir)
                         
                     count += 1
                else:
                     print(f"  Failed for: {video_url}")

            except Exception as e:
                print(f"  Error processing {video_url}: {e}")
            except KeyboardInterrupt:
                print("\n\n[!] Interrupted by user. Saving progress and exiting...")
                print(f"Processed {count} videos before interruption.")
                sys.exit(0)

    print(f"\nCompleted. Processed {count} videos.")

# ==========================================
# Main Execution Block
# ==========================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export YouTube Channel video list or Single Video Metadata.")
    parser.add_argument("url", help="URL of channel/playlist/video.")
    parser.add_argument("-f", "--full", action="store_true", help="DEEP Mode: Fetch FULL metadata (Slower). Default for channels is FAST (List only).")
    parser.add_argument("-c", "--comment", action="store_true", help="Download comments (Implies --full).")
    parser.add_argument("-s", "--sub", action="store_true", help="Download subtitles as separate files and include in metadata.")
    parser.add_argument("-H", "--heatmap", action="store_true", help="Extract heatmap data to separate JSON and include in metadata.")
    
    # Condensed vs Raw Flags
    group_content = parser.add_mutually_exclusive_group()
    group_content.add_argument("-k", "--condensed", action="store_true", help="Clean & Condensed Output (Default for Single Videos).")
    group_content.add_argument("-r", "--raw", action="store_true", help="Full Raw Output (Disables Condensed Mode).")

    # Output Format Group
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-C", "--csv", action="store_true", help="Force CSV output (Default for FAST mode).")
    group.add_argument("-j", "--json", action="store_true", help="Force JSON output (Default for DEEP mode).")

    args = parser.parse_args()
    
    # Determine Output Format Preference
    out_fmt = 'csv' # Default fallback
    if args.json: out_fmt = 'json'
    if args.csv: out_fmt = 'csv'

    # Determine Condensed State
    # None = Auto/Default, True = Forced Condensed, False = Forced Raw
    is_condensed = None
    if args.condensed: is_condensed = True
    if args.raw: is_condensed = False

    try:
        # Handle Batch Mode (File input)
        if os.path.isfile(args.url):
            print(f"Batch Mode Detected: Reading from file '{args.url}'...")
            try:
                with open(args.url, 'r', encoding='utf-8') as f:
                    urls = [line.strip() for line in f if line.strip()]
                
                total_urls = len(urls)
                print(f"Found {total_urls} URLs to process.")
                
                for index, url in enumerate(urls, 1):
                    print(f"\n--- Processing URL {index}/{total_urls}: {url} ---")
                    try:
                        process_url(url, args.full, args.comment, args.sub, args.heatmap, out_fmt, is_condensed)
                    except Exception as e:
                        print(f"Error processing {url}: {e}")
                        # Continue to next URL in batch
            except Exception as e:
                print(f"Error reading batch file: {e}")
                sys.exit(1)
        else:
            # Standard Single URL Mode
            process_url(args.url, args.full, args.comment, args.sub, args.heatmap, out_fmt, is_condensed)

    except KeyboardInterrupt:
        print("\n\n[!] Script cancelled by user (Ctrl+C). Exiting gracefully.")
        sys.exit(0)

