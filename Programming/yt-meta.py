"""
SCRIPT DOCUMENTATION AND USAGE GUIDE
====================================

Overview
--------
This script (`yt-meta.py`) is a utility for extracting metadata from YouTube channels, playlists, 
or individual videos using the `yt-dlp` library. It exports video lists to CSV files and supports 
extracting detailed metadata (including comments) for individual videos into JSON files.

Features
--------
1. Channel/Playlist Export:
   - FAST mode (Default): Rapidly scrapes video lists without visiting every video page. 
     Extracts ID, Title, URL, Duration.
   - FULL mode (`--full`): Visits every video page to extract enriched metadata like view counts, 
     upload dates, and descriptions (slower).
   
2. Single Video Export:
   - Automatically detects if the input URL is a single video.
   - Always fetches full metadata for the single video.
   - Exports a detailed JSON file containing all available metadata (tags, description, heatmaps, etc.).
   
3. Comment Extraction (`-c/--comment`):
   - Downloads all available comments for the video(s).
   - For single videos: Comments are saved in the metadata JSON.
   - For channels: WARNING - This is extremely slow as it downloads comments for EVERY video.

Usage
-----
Run the script from the command line:

    python yt-meta.py [URL] [OPTIONS]

Arguments:
    URL             The URL of the YouTube channel, playlist, or single video.
    --full          (Channel/Playlist only) Fetch FULL metadata. Slower, but provides more details.
    -c, --comment   Download ALL comments.
                    - For single videos: Adds comments to the JSON output.
                    - For channels: Enables full metadata and downloads comments for every video.

Output
------
- CSV Files: Generated for channels/playlists (summary of videos).
- JSON Files: Generated for single videos (comprehensive metadata).

Dependencies
------------
- python 3.x
- yt_dlp (`pip install yt-dlp`)

Version History & Notes
-----------------------
- Revision: 2.0 (Enhanced Metadata & Comments)
- documentation must be included and updated with every revision.
"""

import yt_dlp
import sys
import os
import json
import csv
import argparse
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
        'categories', 'tags', 'heatmaps', 'webpage_url'
    ]
    
    condensed = {k: info.get(k) for k in keys_to_keep if info.get(k) is not None}
    
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
def process_url(url, fetch_full_metadata=False, fetch_comments=False, output_format=None, condensed_mode=None):
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
            # logic: if user passed --full check if they also passed --raw or something?
            # Actually, we will add a valid check for --raw in main.
            # If condensed_mode is NOT explicitly False (which it isn't by default), we set it True.
            # However process_url arg default is False.
            
            # If the user did NOT explicitly turn OFF condensed mode (via --raw logic which we will implement), we default to True.
            # We'll rely on the passed-in argument 'condensed_mode' which comes from main args.
            if condensed_mode is None: # None implies "Auto/Default"
                 condensed_mode = True
                 
            # Default to Condensed Mode if not explicitly disabled via --raw (condensed_mode=False)
            if condensed_mode is None: 
                 condensed_mode = True
                 
            if condensed_mode:
                print("Single Video detected: Fetching rich metadata (Condensed Output).")
            else:
                print("Single Video detected: Fetching rich metadata (Raw Output).")

    # Comments = Deep Mode
    if fetch_comments:
        fetch_full_metadata = True 
        ydl_opts['getcomments'] = True
    
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

                handle_single_video(info_dict, use_condensed=condensed_mode)
            else:
                handle_channel_or_playlist(info_dict, fetch_full_metadata, fetch_comments, output_format)

    except Exception as e:
        print(f"\nAn error occurred: {e}")

# ==========================================
# Single Video Handler
# ==========================================
def handle_single_video(info_dict):
    """
    Handles processing for a single video URL.
    Always saves a rich JSON metadata file.
    """
    # Check if condensed mode was active during process_url call?
    # Actually, handle_single_video is called FROM process_url, but we need to pass the state.
    # We missed passing 'condensed_mode' to handle_single_video in the main logic block.
    # Refactoring slightly below to fix that.
    pass 

    # NOTE: The caller (process_url) needs to be updated to pass use_condensed arg.
    # For now, let's just make handle_single_video accept the arg.
    
def handle_single_video(info_dict, use_condensed=False):
    title = info_dict.get('title', 'UnknownTitle')
    print(f"Detected Single Video: {title}")
    
    # Save directly calling helper
    save_metadata_to_json(info_dict, force_condensed=use_condensed)

# ==========================================
# Channel/Playlist Handler
# ==========================================
def handle_channel_or_playlist(info_dict, is_deep_mode, fetch_comments, output_format):
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
        return

    # ============================
    # DEEP MODE (Full Extraction)
    # ============================
    # Creating individual files in a directory
    
    output_dir = f"{safe_title}_{timestamp}"
    os.makedirs(output_dir, exist_ok=True)
    print(f"Created output directory: {output_dir}")
    print("Starting deep metadata extraction...")

    # Configure options for individual extraction
    video_ydl_opts = {
        'quiet': True,
        'ignoreerrors': True,
        'extract_flat': False, 
        'dump_single_json': True,
    }
    if fetch_comments:
        video_ydl_opts['getcomments'] = True

    count = 0
    with yt_dlp.YoutubeDL(video_ydl_opts) as v_ydl:
        for index, entry in enumerate(video_entries, start=1):
            video_url = entry.get('url')
            video_title = entry.get('title', 'Unknown_Title')
            
            # Progress update
            print(f"[{index}/{len(video_entries)}] Processing: {video_title}")
            
            if not video_url:
                if entry.get('id'):
                    video_url = f"https://www.youtube.com/watch?v={entry.get('id')}"
                else:
                    continue

            try:
                # Re-extract full info
                full_info = v_ydl.extract_info(video_url, download=False)
                
                if full_info:
                     save_metadata_to_json(full_info, output_dir=output_dir)
                     count += 1
                else:
                     print(f"  Failed for: {video_url}")

            except Exception as e:
                print(f"  Error processing {video_url}: {e}")
            except KeyboardInterrupt:
                print("\n\n[!] Interrupted by user. Saving progress and exiting...")
                print(f"Exported {count} videos before interruption.")
                sys.exit(0)

    print(f"\nCompleted. Exported {count} videos to '{output_dir}/'.")

# ==========================================
# Main Execution Block
# ==========================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export YouTube Channel video list or Single Video Metadata.")
    parser.add_argument("url", help="URL of channel/playlist/video.")
    parser.add_argument("--full", action="store_true", help="DEEP Mode: Fetch FULL metadata (Slower). Default for channels is FAST (List only).")
    parser.add_argument("-c", "--comment", action="store_true", help="Download comments (Implies --full).")
    
    # Condensed vs Raw Flags
    group_content = parser.add_mutually_exclusive_group()
    group_content.add_argument("--condensed", action="store_true", help="Clean & Condensed Output (Default for Single Videos).")
    group_content.add_argument("--raw", action="store_true", help="Full Raw Output (Disables Condensed Mode).")

    # Output Format Group
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--csv", action="store_true", help="Force CSV output (Default for FAST mode).")
    group.add_argument("--json", action="store_true", help="Force JSON output (Default for DEEP mode).")

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
                        process_url(url, args.full, args.comment, out_fmt, is_condensed)
                    except Exception as e:
                        print(f"Error processing {url}: {e}")
                        # Continue to next URL in batch
            except Exception as e:
                print(f"Error reading batch file: {e}")
                sys.exit(1)
        else:
            # Standard Single URL Mode
            process_url(args.url, args.full, args.comment, out_fmt, is_condensed)

    except KeyboardInterrupt:
        print("\n\n[!] Script cancelled by user (Ctrl+C). Exiting gracefully.")
        sys.exit(0)

