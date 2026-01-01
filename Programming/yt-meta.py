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
import csv
import sys
import os
import json
import argparse
from datetime import datetime

# ==========================================
# Core Processing Function
# ==========================================
def process_url(url, fetch_full_metadata=False, fetch_comments=False):
    """
    Main logic to handle the URL. Detects if it's a single video or a channel/list
    and processes accordingly.
    """
    
    # default options
    ydl_opts = {
        'quiet': True,           # Don't print standard logs to keep console clean
        'ignoreerrors': True,    # Skip errors (e.g. private videos)
        'extract_flat': True,    # Default to FAST mode (just IDs/titles)
        'dump_single_json': True, # We handle JSON dumping manually for control, but this helps logic
    }

    # LOGIC: Adjust options based on flags and expected behavior 
    
    # If comments are requested, we MUST fetch full metadata and specifically enable comments
    if fetch_comments:
        fetch_full_metadata = True # Comments require visiting the page, implying full metadata
        ydl_opts['getcomments'] = True
    
    # If full metadata is requested (or implied by comments), turn off 'extract_flat'
    if fetch_full_metadata:
        ydl_opts['extract_flat'] = False

    print(f"Processing URL: {url}")
    if fetch_comments:
        print("Note: Comment downloading is enabled. This may take a while.")

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # 1. Extract Info
            # ----------------
            # We first extract info. If 'extract_flat' is True, this is fast for channels.
            # If the URL is a single video, yt-dlp usually ignores 'extract_flat' or returns full info anyway.
            info_dict = ydl.extract_info(url, download=False)
            
            if info_dict is None:
                print("Error: Could not extract information. The video might be unavailable.")
                return

            # 2. Identify Content Type
            # ------------------------
            # 'entries' key exists for playlists/channels. It is missing for single videos.
            is_single_video = 'entries' not in info_dict

            if is_single_video:
                handle_single_video(info_dict, ydl, fetch_comments)
            else:
                handle_channel_or_playlist(info_dict, fetch_comments)

    except Exception as e:
        print(f"\nAn error occurred: {e}")

# ==========================================
# Single Video Handler
# ==========================================
def handle_single_video(info_dict, ydl, fetch_comments):
    """
    Handles processing for a single video URL.
    Always saves a rich JSON metadata file.
    """
    video_id = info_dict.get('id', 'UnknownID')
    title = info_dict.get('title', 'UnknownTitle')
    safe_title = "".join([c for c in title if c.isalpha() or c.isdigit() or c==' ']).strip().replace(" ", "_")
    
    print(f"Detected Single Video: {title}")

    # If extracting flat was on but we ended up with a single video, we might want to ensure 
    # we have EVERYTHING if the user didn't explicitly ask for full but we want to be "curated".
    # However, 'extract_info' usually gets everything for a single video unless it was a playlist entry.
    # Checks: If comments were requested but not present (rare if options set), we might need to re-fetch?
    # Usually ydl_opts passed to constructor covers it.

    # Sanitize data for JSON dump (handle non-serializable objects if any, though info_dict is usually pure data)
    # create filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_filename = f"{safe_title}_{video_id}_metadata_{timestamp}.json"
    output_path = os.path.join(os.getcwd(), json_filename)

    print(f"Saving full metadata to: {json_filename}")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(info_dict, f, indent=4, ensure_ascii=False)
    
    print("Done.")

# ==========================================
# Channel/Playlist Handler
# ==========================================
def handle_channel_or_playlist(info_dict, fetch_comments):
    """
    Handles processing for a channel or playlist.
    Exports the list of videos to a CSV file.
    """
    channel_name = info_dict.get('uploader', info_dict.get('title', 'Unknown_Channel'))
    
    if 'entries' in info_dict:
        # Convert to list immediately to safely handle generators (lazy loading)
        video_entries = list(info_dict['entries'])
    else:
        print("No videos found.")
        return

    # Prepare CSV Filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_channel_name = "".join([c for c in channel_name if c.isalpha() or c.isdigit() or c==' ']).strip().replace(" ", "_")
    csv_filename = f"{safe_channel_name}_videos_{timestamp}.csv"
    output_path = os.path.join(os.getcwd(), csv_filename)

    # Define CSV Columns
    columns = ['id', 'title', 'url', 'duration', 'view_count', 'upload_date', 'comment_count']

    print(f"Found {len(video_entries)} videos (approx). Writing to CSV...")
    
    count = 0
    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=columns, extrasaction='ignore')
        writer.writeheader()

        for video in video_entries:
            if not video:
                continue

            # Construct URL
            if 'url' not in video and 'id' in video:
                video['url'] = f"https://www.youtube.com/watch?v={video['id']}"
            
            # Row Data preparation
            row_data = {
                'id': video.get('id'),
                'title': video.get('title'),
                'url': video.get('url'),
                'duration': video.get('duration'),
                'view_count': video.get('view_count', 'N/A'),
                'upload_date': video.get('upload_date', 'N/A'),
                'comment_count': video.get('comment_count', 'N/A')
            }
            writer.writerow(row_data)
            count += 1
            
            # If fetching comments for a CHANNEL, we might also want to save individual JSONs per video
            # because comments won't fit in a CSV line efficiently.
            # For now, script only requested to "export channel to csv" as base function, 
            # but if -c is added, logic dictates we probably want those comments somewhere.
            # Current implementation: -c on channel enables get_comments, so comment data exists in 'video' dict.
            # We are not currently saving the raw comment JSONs for channels to avoid File Explosion (1000s of files).
            # The CSV will just contain 'comment_count' if available. 
            pass

    print(f"\nSuccess! Exported {count} videos.")
    print(f"File saved to: {output_path}")

# ==========================================
# Main Execution Block
# ==========================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export YouTube Channel video list to CSV or get Single Video Metadata.")
    parser.add_argument("url", help="The URL of the YouTube channel, playlist, or single video.")
    parser.add_argument("--full", action="store_true", help="Fetch FULL metadata (Slower: visits every video link).")
    parser.add_argument("-c", "--comment", action="store_true", help="Download all comments (Saved in JSON for single videos).")

    args = parser.parse_args()
    
    process_url(args.url, fetch_full_metadata=args.full, fetch_comments=args.comment)
