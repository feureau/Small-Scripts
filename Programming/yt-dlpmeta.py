#!/usr/bin/env python
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

Arguments Reference
-------------------
- `-D, --deep`      (Default) Deep Mode: Full metadata & comments for every video.
- `-q, --quick`     Quick Mode: Quick scrape of video list to CSV.
- `-S, --single`    Force Single-Video treatment for any URL.
- `-s, --sub`       Download subtitle files (.srt/.vtt).
- `-H, --heatmap`   Download heatmap data.
- `-k, --condensed` (Default) Clean & Condensed JSON output.
- `-r, --raw`       Full Raw Output (Disables Condensed Mode).
- `-b, --batch`     Batch Mode: treat input as a list of URLs.
- `-C, --csv`       Force CSV output.
- `-j, --json`      Force JSON output.

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
import time
import random
import shutil
import subprocess
from datetime import datetime

# ==========================================
# DEFAULT SETTINGS (User Configurable)
# ==========================================
DEFAULT_SLEEP = 3       # Seconds to wait between videos in a batch (prevents 429 errors)
DEFAULT_DEEP_MODE = True  # Default to fetching rich metadata & comments
DEFAULT_COMMENTS = True   # Default to downloading comments
DEFAULT_CONDENSED = True  # Default to cleaned metadata output
DEFAULT_SUB_FETCH = False # Default to NOT downloading .srt files unless -s is used

# ==========================================
# Helper Function: Check for JS Runtime
# ==========================================
def check_js_runtime():
    """
    Checks if a supported JavaScript runtime (node, deno, bun, qjs) is available.
    Returns (runtime_name, runtime_path) if found, else None.
    Prints a warning if none are found.
    """
    runtimes = ['node', 'deno', 'bun', 'qjs']
    found_info = None
    
    for rt in runtimes:
        path = shutil.which(rt)
        if path:
            found_info = (rt, path)
            print(f"[INFO] Found JavaScript runtime: {rt}")
            break
    
    if not found_info:
        print("\n" + "="*80)
        print("WARNING: No JavaScript runtime found (Node.js, Deno, Bun, or QuickJS).")
        print("YouTube extraction may be limited and some formats may be missing.")
        print("Recommendation: Install Node.js (https://nodejs.org/) or Deno (https://deno.land/).")
        print("="*80 + "\n")
        
    return found_info

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
        'categories', 'tags', 'heatmaps', 'webpage_url', 'subtitle_text',
        'language'  # Include language to show video's original language
    ]
    
    condensed = {k: info.get(k) for k in keys_to_keep if info.get(k) is not None}
    
    # Note: We preserve subtitles/automatic_captions structure for now
    # The get_primary_subtitle_text function will handle extraction

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
# Helper Function: Get Primary Subtitle Text
# ==========================================
def get_primary_subtitle_text(info_dict):
    """
    Extracts subtitle text in the video's original language.
    Prioritizes manual subtitles, falls back to auto-generated.
    Returns cleaned subtitle text or None.
    """
    import urllib.request
    
    # Strategy: Detect the video's original language intelligently
    
    # Validation: Ensure info_dict is actually a dictionary
    if not isinstance(info_dict, dict):
        return None

    video_lang = None
    
    # First, check for 'orig' markers in subtitles/captions (highest priority)
    if info_dict.get('subtitles'):
        if 'orig' in info_dict['subtitles']:
            video_lang = 'orig'
        else:
            # Pick the first available manual subtitle language safely
            available_subs = list(info_dict['subtitles'].keys())
            if available_subs:
                video_lang = available_subs[0]
    
    if not video_lang and info_dict.get('automatic_captions'):
        # Check for original marker in auto-captions
        if 'en-orig' in info_dict['automatic_captions']:
            video_lang = 'en-orig'
        elif 'orig' in info_dict['automatic_captions']:
            video_lang = 'orig'
    
    # If still no language detected, try the metadata language field
    if not video_lang:
        video_lang = info_dict.get('language', None)
    
    # Final fallback: pick the first available auto-caption language
    # (YouTube always generates captions in the video's original language first)
    if not video_lang and info_dict.get('automatic_captions'):
        available_langs = list(info_dict['automatic_captions'].keys())
        if available_langs:
            video_lang = available_langs[0]
            print(f"  [INFO] Auto-detected subtitle language: {video_lang}")
    
    # If we still have nothing, we can't extract subtitles
    if not video_lang:
        return None
    
    subtitle_url = None
    subtitle_format = None
    
    # Try manual subtitles first (preferred)
    if info_dict.get('subtitles') and video_lang in info_dict['subtitles']:
        subtitle_tracks = info_dict['subtitles'][video_lang]
        # Validation: ensure subtitle_tracks is a list
        if isinstance(subtitle_tracks, list):
            # Find best format (prefer srt)
            for track in subtitle_tracks:
                if isinstance(track, dict) and track.get('ext') == 'srt':
                    subtitle_url = track.get('url')
                    subtitle_format = 'srt'
                    break
            # Fallback to any available format
            if not subtitle_url and subtitle_tracks:
                first_track = subtitle_tracks[0]
                if isinstance(first_track, dict):
                    subtitle_url = first_track.get('url')
                    subtitle_format = first_track.get('ext', 'unknown')
    
    # Fallback to auto-generated captions
    if not subtitle_url and info_dict.get('automatic_captions'):
        # Try the detected language
        if video_lang in info_dict['automatic_captions']:
            caption_tracks = info_dict['automatic_captions'][video_lang]
        # Try 'orig' marker
        elif 'orig' in info_dict['automatic_captions']:
            caption_tracks = info_dict['automatic_captions']['orig']
        elif 'en-orig' in info_dict['automatic_captions']:
            caption_tracks = info_dict['automatic_captions']['en-orig']
        # Try English as last resort
        elif 'en' in info_dict['automatic_captions']:
            caption_tracks = info_dict['automatic_captions']['en']
        else:
            caption_tracks = None
        
        if caption_tracks and isinstance(caption_tracks, list):
            # Find best format
            for track in caption_tracks:
                if isinstance(track, dict) and track.get('ext') == 'srt':
                    subtitle_url = track.get('url')
                    subtitle_format = 'srt'
                    break
            # Fallback to any format
            if not subtitle_url and caption_tracks:
                first_track = caption_tracks[0]
                if isinstance(first_track, dict):
                    subtitle_url = first_track.get('url')
                    subtitle_format = first_track.get('ext', 'unknown')
    
    # Download and clean subtitle content
    if subtitle_url:
        max_retries = 3
        retry_delay = 5 # Initial delay
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                     print(f"  [INFO] Retrying subtitle download (Attempt {attempt + 1}/{max_retries})...")
                     time.sleep(retry_delay)
                     retry_delay *= 2 # Exponential backoff
                
                print(f"  [INFO] Downloading subtitle track ({subtitle_format}: {video_lang})...")
                
                # Use headers to avoid 429
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                }
                req = urllib.request.Request(subtitle_url, headers=headers)
                
                with urllib.request.urlopen(req, timeout=10) as response:
                    content = response.read().decode('utf-8')
                    return clean_srt(content)
                    
            except Exception as e:
                if "429" in str(e):
                    print(f"  [WARN] Rate limited (429) during subtitle download.")
                    if attempt == max_retries - 1:
                        print("  [ERROR] Max retries reached for subtitles.")
                else:
                    print(f"  Warning: Could not download subtitle - {e}")
                    break # Not a rate limit issue, don't retry
    
    return None

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
    
    search_pattern = f"*[{video_id}]*.srt"
    if output_dir:
        search_pattern = os.path.join(output_dir, search_pattern)
    
    files = glob.glob(search_pattern)
    
    # Fallback to old patterns if not found
    if not files:
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
    # Create filename
    # Format: {channel} - {upload_date} - {title} [{id}] [{view_count}].json
    channel = info_dict.get('channel', info_dict.get('uploader', 'UnknownChannel'))
    upload_date = info_dict.get('upload_date', 'UnknownDate')
    view_count = info_dict.get('view_count', 'NA')
    
    # Sanitize components
    def sanitize(s):
        return "".join([c for c in str(s) if c.isalnum() or c in (' ', '-', '_', '.')]).strip()

    safe_channel = sanitize(channel)
    safe_title = sanitize(title)
        
    json_filename = f"{safe_channel} - {upload_date} - {safe_title} [{video_id}] [{view_count}].json"
    
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
    # Format: {channel} - {upload_date} - {title} [{id}] [{view_count}]_heatmap.json
    channel = info_dict.get('channel', info_dict.get('uploader', 'UnknownChannel'))
    upload_date = info_dict.get('upload_date', 'UnknownDate')
    view_count = info_dict.get('view_count', 'NA')
    
    # Sanitize components
    def sanitize(s):
        return "".join([c for c in str(s) if c.isalnum() or c in (' ', '-', '_', '.')]).strip()

    safe_channel = sanitize(channel)
    safe_title = sanitize(title)
    
    json_filename = f"{safe_channel} - {upload_date} - {safe_title} [{video_id}] [{view_count}]_heatmap.json"
    
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
def process_url(url, fetch_full_metadata=False, fetch_comments=False, fetch_sub=False, fetch_heatmap=False, output_format=None, condensed_mode=None, force_single=False, quick_mode=False, sleep_seconds=DEFAULT_SLEEP, js_runtime=None):
    """
    Main logic to handle the URL.
    """
    
    # URL Sanitization: Prepend https:// if missing or expand bare IDs
    if not url.startswith(('http://', 'https://', 'ftp://', 'file://')):
        # 1. Detect common bare YouTube patterns
        if url.startswith('PL') and len(url) >= 18:
            # Bare Playlist ID
            url = 'https://www.youtube.com/playlist?list=' + url
        elif url.startswith('UC') and len(url) == 24:
            # Bare Channel ID
            url = 'https://www.youtube.com/channel/' + url
        elif url.startswith('@'):
            # Bare Channel Handle
            url = 'https://www.youtube.com/' + url
        elif len(url) == 11 and all(c.isalnum() or c in '-_' for c in url):
            # Bare Video ID
            url = 'https://www.youtube.com/watch?v=' + url
        elif '.' in url.split('/')[0]:
            # Simple heuristic: if it contains a dot before the first slash, treat as domain
            url = 'https://' + url
        else:
            # Final fallback: just try prepending https:// and hope for the best
            url = 'https://' + url

    # default options
    ydl_opts = {
        'quiet': True,           # Don't print standard logs
        'ignoreerrors': True,    # Skip errors
        'extract_flat': True,    # Default to FAST mode
    }

    # LOGIC: Adjust options based on flags
    
    # Detect likely single video URLs (YouTube + TikTok + others)
    likely_single_url = ("watch?v=" in url or "youtu.be/" in url or "shorts/" in url or "tiktok.com" in url) and ("list=" not in url)
    
    # NEW DEFAULT: Every URL gets Deep Mode + Comments + Condensed unless --quick (-q) is used.
    if not quick_mode:
        # Respect defaults but leave True if user already passed True via flags
        if not fetch_full_metadata: 
             fetch_full_metadata = DEFAULT_DEEP_MODE
        if not fetch_comments:
             fetch_comments = DEFAULT_COMMENTS
        
        # Use Condensed Mode by default
        if condensed_mode is None: # None implies "Auto/Default"
             condensed_mode = DEFAULT_CONDENSED
             
        if force_single:
            print(f"Force Single Mode (-S) active for: {url}")
        elif likely_single_url:
            print("Single Video URL detected: Fetching rich metadata (Condensed Output).")
        else:
            print("Channel/Playlist detected: Fetching rich metadata for each video (Condensed Output).")
    else:
        # QUICK MODE requested (-q)
        # We ensure it stays quick by turning off the deep defaults
        fetch_full_metadata = False
        fetch_comments = False
        if condensed_mode is None:
             condensed_mode = False
        print("QUICK Mode Requested: Rapidly scraping video list.")
    
    if force_single:
         # If user explicitly forced single mode via -S
         pass

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
        ydl_opts['subtitleslangs'] = ['orig', 'en.*', '.*-orig'] # Broad filter for original/english
        ydl_opts['subtitlesformat'] = 'srt/best'
        ydl_opts['skip_download'] = True
        
        # Ensure subtitle filename matches our convention
        # yt-dlp uses outtmpl for subtitles too
        ydl_opts['outtmpl'] = '%(channel)s - %(upload_date)s - %(title)s [%(id)s] [%(view_count)s].%(ext)s'
    
    # extract_flat logic:
    # Only set extract_flat to False if we are SURE it's a single video URL.
    # If it's a channel, we want to extract the list FLAT first so we can iterate.
    if fetch_full_metadata:
        if likely_single_url:
            ydl_opts['extract_flat'] = False
        else:
            # For channels/playlists, we always extract flat first to get the list
            ydl_opts['extract_flat'] = True
    
    print(f"Processing URL: {url}")
    if fetch_comments:
        print("Note: Comment downloading is enabled. This may take a while.")
    
    # Mode Announcement logic
    # We'll announce based on what we find AFTER extraction for more accuracy.

    # Add JS Runtime if detected
    if js_runtime:
        # js_runtime is (name, path) tuple
        rt_name, rt_path = js_runtime
        ydl_opts['js_runtimes'] = {
            rt_name: {'executable': rt_path}
        }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # 1. Extract Info
            info_dict = ydl.extract_info(url, download=False)
            
            if info_dict is None:
                print("Error: Could not extract information.")
                return

            # Additional validation: Ensure we got a valid title or ID
            # Prevents saving "UnknownTitle" skeleton files from generic extractor failures
            if not info_dict.get('id') and not info_dict.get('title'):
                 print(f"Error: yt-dlp could not resolve metadata for: {url}")
                 print("Hint: Ensure the URL includes the protocol (e.g., https://) and is accessible.")
                 return

            # 2. Identify Content Type
            is_single_video = 'entries' not in info_dict

            if is_single_video:
                # Resolve Auto-Condensed State if it was still None
                if condensed_mode is None:
                    condensed_mode = True # Default for single

                # If subtitles requested, we need to call download
                if fetch_sub:
                    ydl_opts['extract_flat'] = False # For single, we need info + download
                    ydl.extract_info(url, download=True)

                handle_single_video(info_dict, use_condensed=condensed_mode, fetch_sub=fetch_sub, fetch_heatmap=fetch_heatmap)
            else:
                mode_str = "DEEP (Full Metadata)" if fetch_full_metadata else "FAST (List Only)"
                print(f"Channel/Playlist Detected. Processing in {mode_str} mode.")
                handle_channel_or_playlist(info_dict, fetch_full_metadata, fetch_comments, fetch_sub, fetch_heatmap, output_format, condensed_mode, sleep_seconds=sleep_seconds, js_runtime=js_runtime)

    except Exception as e:
        print(f"\nAn error occurred: {e}")

def handle_single_video(info_dict, use_condensed=False, fetch_sub=False, fetch_heatmap=False):
    title = info_dict.get('title', 'UnknownTitle')
    video_id = info_dict.get('id', 'UnknownID')
    print(f"Detected Single Video: {title}")
    
    # Optimized Subtitle Extraction logic:
    # 1. If -s was used, try reading from disk first
    transcript = None
    if fetch_sub:
        transcript = get_subtitle_content(video_id, title)
        if transcript:
             print(f"  [OK] Extracted subtitle text from local file.")
    
    # 2. Fallback to extracting from metadata/URL
    if not transcript:
        transcript = get_primary_subtitle_text(info_dict)
        if transcript:
            print(f"  [OK] Extracted subtitle text from metadata ({len(transcript)} characters)")
        else:
            print(f"  [INFO] No subtitles available for this video")
    
    if transcript:
        info_dict['subtitle_text'] = transcript

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
def handle_channel_or_playlist(info_dict, is_deep_mode, fetch_comments, fetch_sub, fetch_heatmap, output_format, condensed_mode=None, sleep_seconds=DEFAULT_SLEEP, js_runtime=None):
    """
    Handles processing for a channel or playlist.
    """
    channel_name = info_dict.get('uploader', info_dict.get('title', 'Unknown_Channel'))
    
    video_entries = []
    if 'entries' in info_dict:
        # YouTube channels often return "Tabs" (Videos, Live, Shorts) as top-level entries
        # when extract_flat is True. We need to flatten these.
        raw_entries = list(info_dict['entries'])
        seen_ids = set()
        
        for entry in raw_entries:
            # If the entry is a sub-playlist (like a channel tab), grab its contents
            if entry.get('_type') == 'playlist' and 'entries' in entry:
                for sub_entry in entry['entries']:
                    eid = sub_entry.get('id')
                    if eid and eid not in seen_ids:
                        video_entries.append(sub_entry)
                        seen_ids.add(eid)
            else:
                eid = entry.get('id')
                # Skip if it's already a channel ID or invalid
                if eid and eid not in seen_ids:
                    # Basic heuristic: video IDs are usually not the same as the parent ID
                    if eid != info_dict.get('id'):
                        video_entries.append(entry)
                        seen_ids.add(eid)
    else:
        print("No videos found.")
        return

    print(f"Found {len(video_entries)} unique videos.")

    # Sanitize channel name for folder (keep spaces, like yt-organizechannels.py)
    # Only remove characters illegal in Windows folder names: < > : " / \ | ? *
    forbidden_chars = '<>:"/\\|?*'
    folder_name = "".join([c for c in channel_name if c not in forbidden_chars]).strip()
    
    # Sanitize channel name for filenames (with underscores, for CSV/JSON list files)
    safe_title = "".join([c for c in channel_name if c.isalpha() or c.isdigit() or c in (' ', '-', '_')]).strip().replace(" ", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Determine if we need an output directory for individual files
    # We use a directory if FULL mode is on, OR if additive resources (subs/heatmaps) are requested
    output_dir = None
    if is_deep_mode or fetch_sub or fetch_heatmap:
        output_dir = folder_name  # Use clean folder name without timestamp
        os.makedirs(output_dir, exist_ok=True)
        print(f"Files will be saved in: {output_dir}")

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
            if output_dir:
                print(f"Individual files (subtitles/metadata) will be saved in: {output_dir}")
            extract_deep_resources(video_entries, fetch_sub, fetch_heatmap, fetch_comments, output_dir=output_dir, condensed_mode=condensed_mode, sleep_seconds=sleep_seconds, js_runtime=js_runtime)
        
        return

    # ============================
    # DEEP MODE (Full Extraction)
    # ============================
    # Files are saved inside the output_dir folder created above
    print("Starting metadata extraction for all videos...")
    extract_deep_resources(video_entries, fetch_sub, fetch_heatmap, fetch_comments, output_dir=output_dir, condensed_mode=condensed_mode, sleep_seconds=sleep_seconds, js_runtime=js_runtime)

# ==========================================
# Helper Function: Deep Resource Extraction
# ==========================================
def extract_deep_resources(video_entries, fetch_sub, fetch_heatmap, fetch_comments, output_dir=None, condensed_mode=None, sleep_seconds=DEFAULT_SLEEP, js_runtime=None):
    """
    Iterates through video entries to fetch subtitles, heatmaps, or full metadata.
    """
    
    video_ydl_opts = {
        'quiet': True,
        'ignoreerrors': True,
        'extract_flat': False, 
        'outtmpl': os.path.join(output_dir, '%(channel)s - %(upload_date)s - %(title)s [%(id)s] [%(view_count)s].%(ext)s') if output_dir else '%(channel)s - %(upload_date)s - %(title)s [%(id)s] [%(view_count)s].%(ext)s'
    }
    
    if fetch_comments:
        video_ydl_opts['getcomments'] = True
        
    if fetch_sub:
        video_ydl_opts['writesubtitles'] = True
        video_ydl_opts['writeautomaticsub'] = True
        video_ydl_opts['subtitleslangs'] = ['orig', 'en.*', '.*-orig']
        video_ydl_opts['subtitlesformat'] = 'srt/best'
        video_ydl_opts['skip_download'] = True
        
    count = 0
    if js_runtime:
        rt_name, rt_path = js_runtime
        video_ydl_opts['js_runtimes'] = {
            rt_name: {'executable': rt_path}
        }
        
    with yt_dlp.YoutubeDL(video_ydl_opts) as v_ydl:
        for index, entry in enumerate(video_entries, start=1):
            video_url = entry.get('url')
            video_title = entry.get('title', 'Unknown_Title')
            video_id = entry.get('id')
            
            try:
                # Filter: Skip entries that aren't videos (e.g. channel tabs that didn't flatten)
                if entry.get('_type') == 'playlist' and 'entries' not in entry:
                    print(f"\n[{index}/{len(video_entries)}] Skipping non-video entry: {video_title}")
                    continue

                if not video_url:
                    if video_id and len(video_id) == 11: # Standard YouTube Video ID length
                        video_url = f"https://www.youtube.com/watch?v={video_id}"
                    else:
                        print(f"\n[{index}/{len(video_entries)}] [SKIP] Invalid video ID/URL: {video_title}")
                        continue

                # Progress update: Match Single Video UI
                print(f"\n[{index}/{len(video_entries)}] Detected Single Video: {video_title}")

                # Verbosity: Indicate what's happening
                print(f"  [INFO] Extracting rich metadata...")
                if fetch_comments:
                    print(f"  [INFO] Gathering comments (this may take a while)...")
                
                # Re-extract full info (download=True if we want subs)
                full_info = v_ydl.extract_info(video_url, download=fetch_sub)
                
                if full_info and isinstance(full_info, dict):
                     # Optimized Subtitle Extraction logic:
                     # 1. If -s was used, try reading from disk first (avoids HTTP request)
                     transcript = None
                     if fetch_sub:
                          transcript = get_subtitle_content(video_id, video_title, output_dir=output_dir)
                          if transcript:
                               print(f"  [OK] Extracted subtitle text from local file.")
                     
                     # 2. Fallback to extracting from metadata/URL if not found on disk OR if -s was NOT used
                     if not transcript:
                          transcript = get_primary_subtitle_text(full_info)
                          if transcript:
                               print(f"  [OK] Extracted subtitle text from metadata ({len(transcript)} characters)")
                     
                     if transcript:
                          full_info['subtitle_text'] = transcript

                     # Save Metadata JSON
                     # For defaults, we save to root (output_dir=None)
                     save_metadata_to_json(full_info, output_dir=output_dir, force_condensed=condensed_mode)
                     
                     # Heatmap is always additive if requested
                     if fetch_heatmap:
                          print(f"  [INFO] Saving heatmap data...")
                          save_heatmap_to_json(full_info, output_dir=output_dir)
                          
                     count += 1
                else:
                     print(f"  [ERROR] Failed for: {video_url}")

                # Rate Limiting: Sleep between videos with Jitter
                if index < len(video_entries):
                    jitter = random.uniform(0, 2)
                    total_sleep = sleep_seconds + jitter
                    print(f"  [INFO] Sleeping for {total_sleep:.2f} seconds...")
                    time.sleep(total_sleep)

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
    parser.add_argument("-f", "--full", action="store_true", help="DEEP Mode: Fetch FULL metadata & comments (Now Default).")
    parser.add_argument("-q", "--quick", action="store_true", help="QUICK Mode: Quick scrape to CSV.")
    parser.add_argument("-S", "--single", action="store_true", help="Force SINGLE video treatment for any URL.")
    parser.add_argument("-c", "--comment", action="store_true", help="Download comments (Auto-enabled for single videos).")
    parser.add_argument("-s", "--sub", action="store_true", help="Download subtitles as separate files and include in metadata.")
    parser.add_argument("-H", "--heatmap", action="store_true", help="Extract heatmap data to separate JSON and include in metadata.")
    parser.add_argument("-b", "--batch", action="store_true", help="Force Batch Mode: URL is a local text file with video list.")

    # Condensed vs Raw Flags
    group_content = parser.add_mutually_exclusive_group()
    group_content.add_argument("-k", "--condensed", action="store_true", help="Clean & Condensed JSON output (Default).")
    group_content.add_argument("-r", "--raw", action="store_true", help="Full Raw Output (Disables Condensed Mode).")

    # Output Format Group
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-C", "--csv", action="store_true", help="Force CSV output (Default for FAST mode).")
    group.add_argument("-j", "--json", action="store_true", help="Force JSON output (Default for DEEP mode).")
    
    parser.add_argument("-z", "--sleep", type=int, default=DEFAULT_SLEEP, help=f"Seconds to sleep between video extractions (Default: {DEFAULT_SLEEP}).")

    args = parser.parse_args()
    
    # Check for JS Runtime (Required by yt-dlp for SABR)
    js_runtime = check_js_runtime()
    
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
        # Check if -b is used OR if it's a file on disk
        if args.batch or (os.path.isfile(args.url) and not args.url.startswith(('http://', 'https://'))):
            print(f"Batch Mode Detected: Reading from file '{args.url}'...")
            try:
                with open(args.url, 'r', encoding='utf-8') as f:
                    urls = [line.strip() for line in f if line.strip()]
                
                total_urls = len(urls)
                print(f"Found {total_urls} URLs to process.")
                
                for index, url in enumerate(urls, 1):
                    print(f"\n--- Processing URL {index}/{total_urls}: {url} ---")
                    try:
                        process_url(url, args.full, args.comment, args.sub, args.heatmap, out_fmt, is_condensed, args.single, args.quick, sleep_seconds=args.sleep)
                    except Exception as e:
                        print(f"Error processing {url}: {e}")
                        # Continue to next URL in batch
            except Exception as e:
                print(f"Error reading batch file: {e}")
                sys.exit(1)
        else:
            # Standard Single URL Mode
            process_url(args.url, args.full, args.comment, args.sub, args.heatmap, out_fmt, is_condensed, args.single, args.quick, sleep_seconds=args.sleep)

    except KeyboardInterrupt:
        print("\n\n[!] Script cancelled by user (Ctrl+C). Exiting gracefully.")
        sys.exit(0)

