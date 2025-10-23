"""
=================================================
Ultimate YouTube Batch Uploader & Manager
=================================================

Version: 1.1
Date: 2025-10-09
Author: [Your Name Here]

---
### DESCRIPTION ###
---
This script provides a comprehensive solution for batch uploading new videos and managing existing videos on a YouTube channel through a graphical user interface (GUI) built with Tkinter. It leverages the YouTube Data API v3 to interact with YouTube services.

The application operates in two primary modes:
1.  **Update Mode:** Fetches a list of existing videos from your channel, allowing you to batch-update their metadata (title, description, tags, category, schedule, visibility, etc.). It can automatically match local description (.txt) and subtitle (.srt) files to your existing videos based on the video's original title.
2.  **Upload Mode:** Scans the local directory for video files (.mp4, .mkv, etc.) and prepares them for batch uploading. It automatically finds matching description and subtitle files for each video, calculates a staggered upload schedule, and allows for bulk metadata assignment before starting the upload process.

---
### FEATURES ###
---
- **GUI-Based Operation:** Easy-to-use interface for all functions.
- **Dual Modes:** Seamlessly switch between managing existing videos and uploading new ones.
- **Google OAuth2 Authentication:** Securely authenticates with your YouTube account using the official Google Auth library. Tokens are stored locally and automatically revoked on exit for security.
- **Batch Metadata Updates:** Modify titles, descriptions, tags, categories, privacy status, and more for multiple videos at once.
- **Automated Scheduling:** Automatically calculate and assign staggered publishing times for a batch of videos based on a start time and interval.
- **Batch Uploading:** Upload multiple videos from your local machine in a single operation.
- **Automatic File Matching:**
    - Associates `.txt` files with videos for descriptions.
    - Associates `.srt` (and other subtitle formats) with videos for captions.
- **Advanced Description Parsing:** Can parse a JSON object within a `.txt` file to set title, description, tags, and hashtags, falling back to plain text if no JSON is found.
- **Dynamic Category Loading:** Fetches the available video categories directly from your YouTube channel.
- **Advanced Filtering:** In Update Mode, filter the video list by privacy status, scheduling, aspect ratio (horizontal/vertical), and whether they have matching local files.
- **Dry Run Mode:** Test your updates without making any actual changes to your YouTube videos.
- **Resumable Uploads:** Robustly handles video uploads, capable of resuming interrupted uploads.
- **Logging:** All operations are logged to the console and can be saved to a file (`yt_manager.log`) upon exit.
- **File Management:** Automatically moves successfully uploaded files to organized folders (enabled by default).

---
### PREREQUISITES & SETUP ###
---
1.  **Python 3.x:** Must be installed on your system.
2.  **Required Libraries:** Install using pip:
    ```
    pip install google-api-python-client google-auth-oauthlib google-auth-httplib2 requests
    ```
3.  **`client_secrets.json`:**
    - You MUST obtain your own `client_secrets.json` file from the Google Cloud Platform.
    - Create a new project in the Google Cloud Console.
    - Enable the "YouTube Data API v3".
    - Create OAuth 2.0 Client ID credentials for a "Desktop app".
    - Download the JSON file and place it in the same directory as this script, or be prepared to select it via the file dialog on first run.

---
### HOW TO USE (GUI WORKFLOW) ###
---
1.  **Authentication:**
    - Run the script (`python your_script_name.py`).
    - Click the "1. Select client_secrets.json & Authenticate" button.
    - Select your `client_secrets.json` file.
    - Your web browser will open, asking you to authorize the application. Grant the requested permissions.
    - After successful authentication, a `token.json` file will be created, and the app will load your channel's video categories.

2.  **Choose a Mode:**
    - **To Manage Existing Videos (Update Mode):**
        - Click the "2. Load Existing Videos" button.
        - The script will fetch videos from your channel and display them in the list. It will also try to find matching local files.
    - **To Upload New Videos (Upload Mode):**
        - Click the "OR: Load Files for Upload" button.
        - The script will scan the current directory for video files and display them.

3.  **Select Videos/Files:**
    - Click on items in the list to select them. Use Ctrl-Click or Shift-Click to select multiple items.
    - Use the "Select All Visible" and "Deselect All" buttons for convenience.

4.  **Configure Settings:**
    - **Scheduling & Visibility (Update & Upload):**
        - Set a start date and time for the first video.
        - Define the interval (in hours and minutes) between subsequent videos.
        - To apply the schedule, ensure the "Update Schedule" checkbox is checked. This automatically sets videos to "Private" until their scheduled time.
        - In Update Mode, you can also set a static visibility (Private, Unlisted, Public) if not scheduling.
    - **Metadata (Update & Upload):**
        - **Description/Tags:** You can enter a description or tags that will OVERRIDE the data from any matched `.txt` files for all selected videos. Leave blank to use the data from files or existing data.
        - **Category, Language, etc.:** Set other metadata fields as needed. "Don't Change" will preserve the existing value for that field (Update Mode only).
        - **Playlist ID:** Provide a playlist ID to add all processed videos to that playlist.
    - **Execution Options:**
        - **Dry Run:** Check this to simulate the process and see the log output without making any changes.
        - **Skip Subtitle Uploads:** Check this to prevent the script from uploading any found subtitle files.
        - **Move files after successful upload:** Enabled by default - moves uploaded files to organized folders.
        - **Save log on exit:** Check this to save the console output to `yt_manager.log` when you close the app.

5.  **Process:**
    - Click the "PROCESS SELECTED VIDEOS" or "UPLOAD SELECTED FILES" button to start the operation.
    - Monitor the console output for detailed progress and any errors. The GUI will remain responsive.

---
### FILE NAMING & DESCRIPTION FORMAT ###
---
- **Matching Logic:** The script matches files by comparing the video's title (or local video filename) with the filename of `.txt` or `.srt` files. It normalizes text by making it lowercase and removing special characters.
    - Example: A video titled "My Awesome Vacation!" will match a file named `my_awesome_vacation.txt`.

- **Description `.txt` File Format:**
    - **Plain Text:** If the file contains only plain text, the entire content will be used as the video description.
    - **JSON Format (for more control):** To set title, description, tags, and hashtags, format the `.txt` file with a JSON object. The script will automatically find and parse it.
    ```json
    {
      "title": "My New Video Title from File",
      "description": "This is the main description of the video.\nIt can span multiple lines.",
      "tags": ["tag1", "youtube api", "python", "automation"],
      "hashtags": ["#coding", "#tutorial"]
    }
    ```
    The script will append the hashtags to the end of the description.

---
### CODE BREAKDOWN ###
---

#### IMPORTS & CONSTANTS
- **Imports:** Includes standard libraries, Google API libraries, and Tkinter for the GUI.
- **SCOPES:** Defines the permissions the script requests from the user's Google account (upload, read, manage).
- **File/Folder Names:** Constants for token file, failed updates folder, uploaded files folder, and log file.
- **API Settings:** Default port for OAuth, API timeout.
- **File Patterns:** Glob patterns to find local video and subtitle files.
- **YouTube Limits:** Constants for max tag length, tag count, and title length.
- **Data Maps:** Dictionaries to map user-friendly language and category names to the IDs required by the YouTube API.

#### LOGGER SETUP
- Configures a global logger to print formatted messages to the console (stdout).
- A custom `ListHandler` stores all log records in memory so they can be written to a file on exit if the user chooses.

#### HELPER, AUTH & DATA MODELS
- **`revoke_token()` & `setup_revocation_on_exit()`:** Security functions. `revoke_token` invalidates the refresh token with Google's servers. `setup_revocation_on_exit` ensures this function is called automatically when the application is closed or terminated.
- **`get_authenticated_service()`:** Handles the entire OAuth2 authentication flow. It first tries to use a saved `token.json`, refreshes it if it's expired, and only if necessary, runs the new user authorization flow.
- **`normalize_for_matching()` & `sanitize_*()` functions:** A set of helper functions to clean and format text data to be compliant with the YouTube API (e.g., removing invalid characters, truncating to max length).
- **`VideoData` Class:** A data model to represent an **existing** video fetched from YouTube. It stores all relevant details like ID, title, snippet, status, and paths to any matched local description/subtitle files.
- **`VideoEntry` Class:** A data model to represent a **local video file** intended for upload. In its constructor, it automatically searches for and parses corresponding `.txt` and `.srt` files.
- **`calculate_default_start_time()`:** A utility to provide a sensible default start time for scheduling (the next available 2.4-hour interval, at least 1 hour in the future).
- **File Management Functions:** Functions to generate batch IDs, safely move files, and organize uploaded files into folders.

#### MainApp CLASS (The GUI)
- **`__init__()`:** The constructor initializes the main Tkinter window, sets up the token revocation, and calls `build_gui()`.
- **`build_gui()`:** Constructs the entire user interface by creating and arranging Tkinter widgets (buttons, labels, a Treeview for the list, etc.) into logical frames.
- **`_update_gui_for_mode()`:** Dynamically changes GUI elements (button text, list headers) when switching between "Update" and "Upload" modes.
- **`_update_ui_states()`:** Manages the enabled/disabled state of widgets based on user selections. For example, it disables the manual visibility radio buttons if "Update Schedule" is checked.
- **`_sort_column()`:** Implements clickable column headers in the Treeview to sort the video list.
- **`apply_filters()` & `clear_filters()`:** Implements the filtering logic in Update Mode. It rebuilds the list of displayed videos based on the active filter checkboxes.
- **`_populate_treeview()`:** Clears and repopulates the Treeview widget with the current list of videos to be displayed.
- **`on_video_select_display_info()`:** An event handler that runs when a user selects a video in the list. It populates the metadata entry fields with the data from the selected video, making it easy to see and edit.
- **`select_credentials_and_auth()`:** The callback for the authentication button.
- **`load_channel_categories()`:** Fetches and populates the category dropdown menu after successful authentication.
- **`gui_load_existing_videos()` & `gui_load_files_for_upload()`:** Callbacks for the "Load" buttons. They set the application mode and start the loading process in a separate thread.
- **Threading Functions (`run_video_load`, `start_processing_thread`, etc.):** These functions are designed to be run in background threads (`threading.Thread`). This is crucial for preventing the GUI from freezing during long-running tasks like API calls or file I/O. They perform the core work and then use `self.root.after()` to safely schedule a GUI update on the main thread once their work is done.
- **`fetch_all_videos_from_api()`:** The core function for "Update Mode". It retrieves the user's uploaded videos via the API, paginating through results. It then iterates through these videos and attempts to match them with local description/subtitle files. It uses a dictionary with the video ID as the key to prevent duplicate entries, which resolves potential Tkinter errors.
- **`on_exit()`:** The callback for closing the window. It handles saving the log file if requested and then destroys the Tkinter root window.

#### CORE LOGIC FUNCTIONS (Outside the MainApp Class)
- **`update_videos_on_youtube()`:** Contains the logic for processing videos in "Update Mode". It iterates through the selected `VideoData` objects, builds the API request body based on user settings and file data, and calls the `service.videos().update()` endpoint. It includes logic for dry runs and adding videos to a playlist.
- **`upload_new_videos()`:** Contains the logic for "Upload Mode". It iterates through the selected `VideoEntry` objects, constructs the metadata `snippet` and `status` parts of the request, and uses `MediaFileUpload` to handle the actual video upload. After a successful video upload, it proceeds to upload the subtitle file (if available) and add the new video to a playlist (if requested). It also handles moving files to organized folders after successful uploads.

#### SCRIPT ENTRY POINT
- **`if __name__ == '__main__':`:** This is standard Python practice. The code inside this block only runs when the script is executed directly. It creates an instance of the `MainApp` class, which starts the GUI and the application's event loop.
"""

import os
import sys
import json
import signal
import atexit
import re
import logging
import shutil
import glob
import math
import random
from pathlib import Path
from datetime import datetime, timedelta, time, timezone
import requests
import threading

from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# --- Constants ---
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube", "https://www.googleapis.com/auth/youtube.force-ssl"
]
TOKEN_FILE = "token.json"; FAILED_UPDATES_FOLDER = "failed_updates"; UPLOADED_FOLDER = "uploaded"
UPLOADED_VIDEOS_SUBFOLDER = "videos"; UPLOADED_DESCRIPTIONS_SUBFOLDER = "descriptions"
UPLOADED_SUBTITLES_SUBFOLDER = "subtitles"; UPLOADED_LOGS_SUBFOLDER = "logs"
LOG_FILE = "yt_manager.log"
OAUTH_PORT = 0; API_TIMEOUT_SECONDS = 60
VIDEO_PATTERNS = ["*.mp4", "*.mkv", "*.avi", "*.mov", "*.wmv"]
SUBTITLE_PATTERNS = ["*.srt", "*.sbv", "*.vtt", "*.scc", "*.ttml"]
YOUTUBE_TAGS_MAX_LENGTH = 500; YOUTUBE_TAGS_MAX_COUNT = 15; YOUTUBE_TITLE_MAX_LENGTH = 100
LANGUAGES_MAP = {"Don't Change": None, "English": "en", "Spanish": "es", "French": "fr", "German": "de", "Japanese": "ja", "Chinese": "zh"}
STATIC_CATEGORY_MAP = {"Film & Animation": "1", "Autos & Vehicles": "2", "Music": "10", "Pets & Animals": "15", "Sports": "17", "Travel & Events": "19", "Gaming": "20", "People & Blogs": "22", "Comedy": "23", "Entertainment": "24", "News & Politics": "25", "Howto & Style": "26", "Education": "27", "Science & Technology": "28", "Nonprofits & Activism": "29"}

# --- Logger Setup ---
log_records = []
class ListHandler(logging.Handler):
    def emit(self, record): log_records.append(self.format(record))
logger = logging.getLogger("yt_manager"); logger.setLevel(logging.INFO)
formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S")
if not logger.handlers:
    console_handler = logging.StreamHandler(sys.stdout); console_handler.setFormatter(formatter)
    list_handler = ListHandler(); list_handler.setFormatter(formatter)
    logger.addHandler(console_handler); logger.addHandler(list_handler)


# --- Helper, Auth & Data Models ---
def revoke_token():
    if not os.path.exists(TOKEN_FILE): return
    logger.info("Revoking token on exit...")
    try:
        with open(TOKEN_FILE, 'r') as f: token_data = json.load(f)
        if token_data.get('refresh_token'):
            requests.post('https://oauth2.googleapis.com/revoke', params={'token': token_data['refresh_token']}, timeout=10)
    except Exception as e: logger.error(f"Token revocation failed: {e}")
    finally:
        try: os.remove(TOKEN_FILE)
        except OSError: pass
def setup_revocation_on_exit():
    atexit.register(revoke_token)
    signal.signal(signal.SIGTERM, lambda signum, frame: sys.exit(1)); signal.signal(signal.SIGINT, lambda signum, frame: sys.exit(1))
def get_authenticated_service(secrets_path):
    creds = None
    if Path(TOKEN_FILE).exists():
        try: creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        except Exception: creds = None
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try: creds.refresh(Request(timeout=API_TIMEOUT_SECONDS))
            except Exception as e: logger.error(f"Token refresh failed: {e}"); creds = None
        if not creds:
            if not secrets_path or not Path(secrets_path).exists(): logger.error("Client secrets file missing."); return None
            try:
                flow = InstalledAppFlow.from_client_secrets_file(secrets_path, SCOPES)
                creds = flow.run_local_server(port=OAUTH_PORT, open_browser=True, timeout=900)
            except Exception as e:
                logger.error(f"OAuth local server flow failed: {e}. Falling back to console.")
                flow = InstalledAppFlow.from_client_secrets_file(secrets_path, SCOPES); creds = flow.run_console()
        with open(TOKEN_FILE, 'w') as f: f.write(creds.to_json())
    return build('youtube', 'v3', credentials=creds, cache_discovery=False)
def normalize_for_matching(text: str) -> str:
    text = text.lower(); text = re.sub(r'[^a-z0-9\s]', ' ', text); text = re.sub(r'\s+', '_', text); return text
def sanitize_for_youtube(text: str, max_len=None) -> str:
    sanitized = text.replace('<', '').replace('>', ''); return sanitized[:max_len] if max_len else sanitized
def sanitize_description(desc: str) -> str:
    desc = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F]', '', desc); return desc[:5000]
def sanitize_tags(raw_tags):
    clean = []; total_len = 0
    for t in raw_tags:
        tag = re.sub(r'[\x00-\x1F\x7F]', '', t.strip()); tag = re.sub(r'[^A-Za-z0-9 ]+', '', tag)[:30]
        if not tag: continue
        if total_len + len(tag) > YOUTUBE_TAGS_MAX_LENGTH or len(clean) >= YOUTUBE_TAGS_MAX_COUNT: break
        clean.append(tag); total_len += len(tag)
    return clean
def sanitize_and_parse_json(content: str) -> dict | None:
    try:
        content = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', content); start_index = content.find('{')
        if start_index == -1: return None
        brace_level, in_string, end_index = 1, False, -1
        for i in range(start_index + 1, len(content)):
            char = content[i]
            if char == '"' and content[i-1] != '\\': in_string = not in_string
            if in_string: continue
            if char == '{': brace_level += 1
            elif char == '}': brace_level -= 1
            if brace_level == 0: end_index = i + 1; break
        if end_index == -1: return None
        json_str = content[start_index:end_index]
        def escape_quotes(match): return match.group(1) + match.group(2).replace('"', '\\"') + match.group(3)
        json_str = re.sub(r'(".*?":\s*")(.*?)(")', escape_quotes, json_str, flags=re.DOTALL); json_str = re.sub(r',\s*([}\]])', r'\1', json_str)
        return json.loads(json_str)
    except Exception: return None

# File Management Functions
def generate_batch_id():
    """Generate a unique batch ID for this upload session"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    random_str = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=6))
    return f"batch_{timestamp}_{random_str}"

def safe_move_file(source_path, destination_path):
    """
    Safely move file with conflict resolution
    """
    source = Path(source_path)
    destination = Path(destination_path)
    
    if not source.exists():
        logger.warning(f"Source file doesn't exist: {source}")
        return False
        
    # Handle filename conflicts
    counter = 1
    original_dest = destination
    while destination.exists():
        stem = original_dest.stem
        suffix = original_dest.suffix
        destination = original_dest.parent / f"{stem}_{counter}{suffix}"
        counter += 1
    
    try:
        # Ensure destination directory exists
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(destination))
        logger.info(f"Moved: {source.name} → {destination}")
        return True
    except Exception as e:
        logger.error(f"Failed to move {source.name}: {e}")
        return False

def move_uploaded_files(video_entry, batch_id, upload_success=True):
    """
    Move files to appropriate folders after upload
    Returns: dict of original_path -> new_path mappings
    """
    moved_files = {}
    
    if upload_success:
        base_folder = UPLOADED_FOLDER
        # Create batch-specific subfolder: uploaded/2024-01-15_143022_batch123/
        batch_folder = f"{datetime.now().strftime('%Y-%m-%d_%H%M%S')}_{batch_id}"
        target_dir = Path(base_folder) / batch_folder
    else:
        target_dir = Path(FAILED_UPDATES_FOLDER) / batch_id
    
    # Create directory structure
    (target_dir / UPLOADED_VIDEOS_SUBFOLDER).mkdir(parents=True, exist_ok=True)
    (target_dir / UPLOADED_DESCRIPTIONS_SUBFOLDER).mkdir(parents=True, exist_ok=True)
    (target_dir / UPLOADED_SUBTITLES_SUBFOLDER).mkdir(parents=True, exist_ok=True)
    
    # Move video file
    video_src = Path(video_entry.filepath)
    video_dst = target_dir / UPLOADED_VIDEOS_SUBFOLDER / video_src.name
    if safe_move_file(video_src, video_dst):
        moved_files['video'] = (str(video_src), str(video_dst))
    
    # Move description file if exists and was used
    if hasattr(video_entry, 'description_file_path') and video_entry.description_file_path:
        desc_src = Path(video_entry.description_file_path)
        desc_dst = target_dir / UPLOADED_DESCRIPTIONS_SUBFOLDER / desc_src.name
        if safe_move_file(desc_src, desc_dst):
            moved_files['description'] = (str(desc_src), str(desc_dst))
    
    # Move subtitle file if exists and was used  
    if hasattr(video_entry, 'subtitle_path') and video_entry.subtitle_path:
        sub_src = Path(video_entry.subtitle_path)
        sub_dst = target_dir / UPLOADED_SUBTITLES_SUBFOLDER / sub_src.name
        if safe_move_file(sub_src, sub_dst):
            moved_files['subtitle'] = (str(sub_src), str(sub_dst))
    
    return moved_files

def save_upload_log(batch_id, upload_data):
    """Save JSON log of uploaded files for reference"""
    log_file = Path(UPLOADED_FOLDER) / UPLOADED_LOGS_SUBFOLDER / f"{batch_id}.json"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    log_data = {
        'batch_id': batch_id,
        'upload_time': datetime.now().isoformat(),
        'total_videos': len(upload_data),
        'uploads': upload_data
    }
    
    try:
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=2)
        logger.info(f"Upload log saved: {log_file}")
    except Exception as e:
        logger.error(f"Failed to save upload log: {e}")

class VideoData:
    def __init__(self, video_id, video_title, video_snippet, video_status, video_file_details=None):
        self.video_id, self.original_title = video_id, video_title; self.video_snippet, self.video_status = video_snippet or {}, video_status or {}
        self.upload_date = self.video_snippet.get('publishedAt', ''); self.description_file_path, self.description_filename = None, "N/A"; self.subtitle_file_path, self.subtitle_filename = None, "N/A"; self.width, self.height = 0, 0
        if video_file_details and 'videoStreams' in video_file_details and video_file_details['videoStreams']: stream = video_file_details['videoStreams'][0]; self.width, self.height = stream.get('widthPixels', 0), stream.get('heightPixels', 0)
        self.current_title = self.video_snippet.get('title', self.original_title); self.current_description = self.video_snippet.get('description', ''); self.current_tags = self.video_snippet.get('tags', []); self.current_category_id = self.video_snippet.get('categoryId', '24'); self.current_video_language = self.video_snippet.get('defaultAudioLanguage', 'en'); self.current_default_language = self.video_snippet.get('defaultLanguage', 'en'); self.current_recording_date = (self.video_snippet.get('recordingDetails') or {}).get('recordingDate', ''); self.current_made_for_kids = self.video_status.get('selfDeclaredMadeForKids'); self.current_embeddable = self.video_status.get('embeddable', True); self.current_public_stats_viewable = self.video_status.get('publicStatsViewable', False)

class VideoEntry:
    def __init__(self, filepath):
        p = Path(filepath); self.filepath = str(p); self.title = sanitize_for_youtube(p.stem, YOUTUBE_TITLE_MAX_LENGTH); self.description, self.description_source = "", "None"; self.subtitle_path, self.subtitle_source = None, "None"; self.tags = []; self.description_file_path = None
        try:
            matching_txt_files = list(p.parent.glob(f"{p.stem}*.txt"))
            if matching_txt_files:
                txt_file = matching_txt_files[0]; logger.info(f"Found matching description file '{txt_file.name}' for video '{p.name}'."); content = txt_file.read_text(encoding='utf-8'); data = sanitize_and_parse_json(content)
                if data: self.title = sanitize_for_youtube(data.get("title", self.title), YOUTUBE_TITLE_MAX_LENGTH); hashtags = " ".join(data.get("hashtags", [])); self.description = f"{data.get('description', '')}\n\n{hashtags}".strip(); self.tags = data.get("tags", [])[:YOUTUBE_TAGS_MAX_COUNT]
                else: self.description = content
                self.description_source = txt_file.name; self.description_file_path = str(txt_file)
        except Exception as e: logger.error(f"Error reading description file for '{p.name}': {e}")
        try:
            for pattern in SUBTITLE_PATTERNS:
                found_subs = list(p.parent.glob(f"{p.stem}*.srt"))
                if found_subs: sub_file = found_subs[0]; logger.info(f"Found matching subtitle file '{sub_file.name}' for video '{p.name}'."); self.subtitle_path = str(sub_file); self.subtitle_source = sub_file.name; break
        except Exception as e: logger.error(f"Error searching for subtitle file for '{p.name}': {e}")
        self.categoryId = '24'; self.videoLanguage = 'en'; self.defaultLanguage = 'en'; self.recordingDate = None; self.notifySubscribers = False; self.madeForKids = False; self.embeddable = True; self.publicStatsViewable = False; self.playlistId = ''; self.publishAt = None

def calculate_default_start_time():
    now = datetime.now(); minimum_time = now + timedelta(hours=1); midnight_today = datetime.combine(now.date(), time()); minutes_from_midnight_to_minimum = (minimum_time - midnight_today).total_seconds() / 60; interval_minutes = 144; num_intervals = math.ceil(minutes_from_midnight_to_minimum / interval_minutes); scheduled_time = midnight_today + timedelta(minutes=num_intervals * interval_minutes)
    return scheduled_time.strftime('%Y-%m-%d %H:%M')

# --- Main Application Class ---
class MainApp:
    def __init__(self):
        self.service = None; self.videos_to_process = []; self.dynamic_category_map = {}; self.app_mode = "update"
        self.root = tk.Tk(); setup_revocation_on_exit(); self.root.title('Ultimate YouTube Batch Uploader & Manager')
        self.build_gui(); self.root.protocol("WM_DELETE_WINDOW", self.on_exit); self._update_gui_for_mode(); self.root.mainloop()
    
    def build_gui(self):
        frm = ttk.Frame(self.root, padding=10); frm.pack(fill=tk.BOTH, expand=True)

        # --- Top Frame ---
        top_frame = ttk.Frame(frm); top_frame.pack(fill=tk.X, pady=5)
        self.select_cred_button = ttk.Button(top_frame, text='1. Select client_secrets.json & Authenticate', command=self.select_credentials_and_auth)
        self.select_cred_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        # --- Load Frame ---
        load_frame = ttk.Frame(frm); load_frame.pack(fill=tk.X, pady=5)
        self.load_existing_button = ttk.Button(load_frame, text='2. Load Existing Videos', command=self.gui_load_existing_videos, state=tk.DISABLED)
        self.load_existing_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.load_for_upload_button = ttk.Button(load_frame, text='OR: Load Files for Upload', command=self.gui_load_files_for_upload, state=tk.NORMAL)
        self.load_for_upload_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Label(load_frame, text='Max to Load:').pack(side=tk.LEFT, padx=(10, 2))
        self.max_videos_var = tk.StringVar(value='50')
        ttk.Spinbox(load_frame, from_=0, to=10000, width=5, textvariable=self.max_videos_var).pack(side=tk.LEFT, padx=(0, 5))

        # --- Treeview Frame ---
        list_lf = ttk.LabelFrame(frm, text="Video List", padding=5); list_lf.pack(fill=tk.BOTH, expand=True, pady=5)
        tree_frame = ttk.Frame(list_lf); tree_frame.pack(fill=tk.BOTH, expand=True)
        self.tree = ttk.Treeview(tree_frame, columns=('id_or_path', 'title', 'desc_file', 'sub_file', 'status', 'publish_at', 'upload_date'), show='headings', selectmode="extended")
        for col in self.tree['columns']: self.tree.heading(col, command=lambda c=col: self._sort_column(c, False))
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview); self.tree.configure(yscrollcommand=vsb.set); self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True); vsb.pack(side=tk.RIGHT, fill=tk.Y); self.tree.bind('<<TreeviewSelect>>', self.on_video_select_display_info)

        # --- Treeview Controls ---
        list_controls = ttk.Frame(list_lf); list_controls.pack(fill=tk.X, pady=(5, 0))
        self.filter_menubutton = ttk.Menubutton(list_controls, text="Filter by...", state=tk.DISABLED); self.filter_menubutton.pack(side=tk.LEFT, padx=(0, 10)); self.filter_menu = tk.Menu(self.filter_menubutton, tearoff=0); self.filter_menubutton["menu"] = self.filter_menu; self.filter_vars = {k: tk.BooleanVar() for k in ["public", "not_public", "private", "not_private", "unlisted", "not_unlisted", "has_schedule", "no_schedule", "has_desc_file", "no_desc_file", "has_sub_file", "no_sub_file", "is_horizontal", "is_vertical"]}; self.filter_menu.add_checkbutton(label="Public", variable=self.filter_vars["public"], command=self.apply_filters); self.filter_menu.add_checkbutton(label="Not Public", variable=self.filter_vars["not_public"], command=self.apply_filters); self.filter_menu.add_separator(); self.filter_menu.add_checkbutton(label="Private", variable=self.filter_vars["private"], command=self.apply_filters); self.filter_menu.add_checkbutton(label="Not Private", variable=self.filter_vars["not_private"], command=self.apply_filters); self.filter_menu.add_separator(); self.filter_menu.add_checkbutton(label="Unlisted", variable=self.filter_vars["unlisted"], command=self.apply_filters); self.filter_menu.add_checkbutton(label="Not Unlisted", variable=self.filter_vars["not_unlisted"], command=self.apply_filters); self.filter_menu.add_separator(); self.filter_menu.add_checkbutton(label="Has Schedule", variable=self.filter_vars["has_schedule"], command=self.apply_filters); self.filter_menu.add_checkbutton(label="Not Scheduled", variable=self.filter_vars["no_schedule"], command=self.apply_filters); self.filter_menu.add_separator(); self.filter_menu.add_checkbutton(label="Has Description File", variable=self.filter_vars["has_desc_file"], command=self.apply_filters); self.filter_menu.add_checkbutton(label="No Description File", variable=self.filter_vars["no_desc_file"], command=self.apply_filters); self.filter_menu.add_separator(); self.filter_menu.add_checkbutton(label="Has Subtitle File", variable=self.filter_vars["has_sub_file"], command=self.apply_filters); self.filter_menu.add_checkbutton(label="No Subtitle File", variable=self.filter_vars["no_sub_file"], command=self.apply_filters); self.filter_menu.add_separator(); self.filter_menu.add_checkbutton(label="Horizontal Video", variable=self.filter_vars["is_horizontal"], command=self.apply_filters); self.filter_menu.add_checkbutton(label="Vertical Video", variable=self.filter_vars["is_vertical"], command=self.apply_filters); self.filter_menu.add_separator(); self.filter_menu.add_command(label="Clear All Filters", command=self.clear_filters)
        ttk.Button(list_controls, text='Select All Visible', command=lambda: self.tree.selection_set(self.tree.get_children())).pack(side=tk.LEFT, padx=2); ttk.Button(list_controls, text='Deselect All', command=lambda: self.tree.selection_remove(self.tree.selection())).pack(side=tk.LEFT, padx=2)

        # --- Bottom Frames ---
        bottom_frame = ttk.Frame(frm); bottom_frame.pack(fill=tk.X, pady=5)
        sched = ttk.LabelFrame(bottom_frame, text='Scheduling & Visibility', padding=10); sched.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        meta = ttk.LabelFrame(bottom_frame, text='Metadata', padding=10); meta.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # --- Scheduling Widgets ---
        ttk.Label(sched, text='First Publish:').grid(row=0, column=0, sticky='w'); self.start_ent = ttk.Entry(sched, width=20); self.start_ent.insert(0, calculate_default_start_time()); self.start_ent.grid(row=0, column=1, sticky='ew', padx=5, pady=2)
        ttk.Label(sched, text='Interval Hours:').grid(row=1, column=0, sticky='w'); self.interval_hour_var = tk.StringVar(value='2'); ttk.Spinbox(sched, from_=0, to=1000, width=5, textvariable=self.interval_hour_var).grid(row=1, column=1, sticky='w', padx=5, pady=2)
        ttk.Label(sched, text='Interval Mins:').grid(row=2, column=0, sticky='w'); self.interval_minute_var = tk.StringVar(value='24'); ttk.Spinbox(sched, from_=0, to=59, width=5, textvariable=self.interval_minute_var).grid(row=2, column=1, sticky='w', padx=5, pady=2)
        ttk.Separator(sched, orient='horizontal').grid(row=3, column=0, columnspan=2, sticky='ew', pady=10)
        self.update_schedule_var = tk.BooleanVar(value=True); ttk.Checkbutton(sched, text="Update Schedule", variable=self.update_schedule_var, command=self._update_ui_states).grid(row=4, column=0, columnspan=2, sticky='w')
        self.update_visibility_var = tk.BooleanVar(value=False); self.vis_cb = ttk.Checkbutton(sched, text="Update Visibility Status", variable=self.update_visibility_var, command=self._update_ui_states); self.vis_cb.grid(row=5, column=0, columnspan=2, sticky='w')
        self.visibility_choice_var = tk.StringVar(value='private'); self.rad_private = ttk.Radiobutton(sched, text="Private", variable=self.visibility_choice_var, value='private'); self.rad_private.grid(row=6, column=0, columnspan=2, sticky='w', padx=10); self.rad_unlisted = ttk.Radiobutton(sched, text="Unlisted", variable=self.visibility_choice_var, value='unlisted'); self.rad_unlisted.grid(row=7, column=0, columnspan=2, sticky='w', padx=10); self.rad_public = ttk.Radiobutton(sched, text="Public", variable=self.visibility_choice_var, value='public'); self.rad_public.grid(row=8, column=0, columnspan=2, sticky='w', padx=10)

        # --- Metadata Widgets ---
        ttk.Label(meta, text='Description:').grid(row=0, column=0, sticky='nw'); self.desc_txt = tk.Text(meta, height=3, width=40, wrap=tk.WORD); self.desc_txt.grid(row=0, column=1, sticky='ew', columnspan=3)
        ttk.Label(meta, text='Tags (comma-sep):').grid(row=1, column=0, sticky='w', pady=(5,0)); self.tags_ent = ttk.Entry(meta); self.tags_ent.grid(row=1, column=1, sticky='ew', pady=(5,0), columnspan=3)
        ttk.Label(meta, text='Video Category:').grid(row=2, column=0, sticky='w', pady=(5,0)); self.category_var = tk.StringVar(); self.category_cb = ttk.Combobox(meta, textvariable=self.category_var, values=["Don't Change"], state="readonly"); self.category_cb.set("Don't Change"); self.category_cb.grid(row=2, column=1, sticky='ew', pady=(5,0), columnspan=3)
        ttk.Label(meta, text='Metadata Lang:').grid(row=3, column=0, sticky='w', pady=(5,0)); self.metadata_lang_var = tk.StringVar(); self.metadata_lang_cb = ttk.Combobox(meta, textvariable=self.metadata_lang_var, values=list(LANGUAGES_MAP.keys()), state="readonly"); self.metadata_lang_cb.set('English'); self.metadata_lang_cb.grid(row=3, column=1, sticky='ew', pady=(5,0), columnspan=3)
        ttk.Label(meta, text='Audio Language:').grid(row=4, column=0, sticky='w', pady=(5,0)); self.audio_lang_var = tk.StringVar(); self.audio_lang_cb = ttk.Combobox(meta, textvariable=self.audio_lang_var, values=list(LANGUAGES_MAP.keys()), state="readonly"); self.audio_lang_cb.set('English'); self.audio_lang_cb.grid(row=4, column=1, sticky='ew', pady=(5,0), columnspan=3)
        ttk.Label(meta, text='Recording Date (YYYY-MM-DD):').grid(row=5, column=0, sticky='w', pady=(5,0)); self.recording_date_var = tk.StringVar(value=datetime.now().strftime('%Y-%m-%d')); ttk.Entry(meta, textvariable=self.recording_date_var).grid(row=5, column=1, sticky='ew', pady=(5,0), columnspan=3)
        ttk.Label(meta, text='Playlist ID:').grid(row=6, column=0, sticky='w', pady=(5,0)); self.playlist_id_var = tk.StringVar(); ttk.Entry(meta, textvariable=self.playlist_id_var).grid(row=6, column=1, sticky='ew', pady=(5,0), columnspan=3)
        option_frame = ttk.Frame(meta); option_frame.grid(row=7, column=0, columnspan=4, sticky='w', pady=(5,0)); self.allow_embedding_var = tk.BooleanVar(value=True); ttk.Checkbutton(option_frame, text="Allow Embedding", variable=self.allow_embedding_var).pack(side=tk.LEFT, padx=(0,10)); self.notify_subscribers_var = tk.BooleanVar(value=False); ttk.Checkbutton(option_frame, text="Notify Subscribers (on public)", variable=self.notify_subscribers_var).pack(side=tk.LEFT, padx=(0,10)); self.public_stats_var = tk.BooleanVar(value=False); ttk.Checkbutton(option_frame, text="Public Stats Visible", variable=self.public_stats_var).pack(side=tk.LEFT)
        ttk.Label(meta, text='Made for Kids:').grid(row=9, column=0, sticky='w', pady=(5,0)); self.made_for_kids_var = tk.StringVar(value='no'); mfk_frame = ttk.Frame(meta); mfk_frame.grid(row=9, column=1, sticky='ew', pady=(5,0), columnspan=3); ttk.Radiobutton(mfk_frame, text="No", variable=self.made_for_kids_var, value='no').pack(side=tk.LEFT, padx=(0, 10)); ttk.Radiobutton(mfk_frame, text="Yes", variable=self.made_for_kids_var, value='yes').pack(side=tk.LEFT, padx=(0, 10)); ttk.Radiobutton(mfk_frame, text="Don't Change", variable=self.made_for_kids_var, value='dont_change').pack(side=tk.LEFT); meta.grid_columnconfigure(1, weight=1)

        # --- Execution Frame ---
        action_frame = ttk.LabelFrame(frm, text="Execution", padding=10)
        action_frame.pack(fill=tk.X, pady=5)

        # 1. Dry Run Checkbox: For testing without making actual changes.
        self.dry_run_var = tk.BooleanVar(value=False)
        dry_run_cb = ttk.Checkbutton(action_frame, text="Dry Run (Test Mode)", variable=self.dry_run_var)
        dry_run_cb.pack(side=tk.LEFT, padx=(0, 15))

        # 2. Skip Subtitles Checkbox: Prevents uploading found .srt files.
        self.skip_subs_var = tk.BooleanVar(value=True)
        skip_subs_cb = ttk.Checkbutton(action_frame, text="Skip Subtitle Uploads", variable=self.skip_subs_var)
        skip_subs_cb.pack(side=tk.LEFT, padx=(0, 15))
        
        # 3. Move Files Checkbox: Moves uploaded files to organized folders (enabled by default)
        self.move_files_var = tk.BooleanVar(value=True)
        move_files_cb = ttk.Checkbutton(action_frame, text="Move files to 'uploaded' folder after success", variable=self.move_files_var)
        move_files_cb.pack(side=tk.LEFT, padx=(0, 15))
        
        # 4. Save Log Checkbox: Saves console output to a file on exit.
        self.save_log_var = tk.BooleanVar(value=False)
        save_log_cb = ttk.Checkbutton(action_frame, text="Save log on exit", variable=self.save_log_var)
        save_log_cb.pack(side=tk.LEFT)
        
        # --- Process Button and Status Bar ---
        self.process_button = ttk.Button(frm, text='PROCESS', command=self.start_processing_thread, state=tk.DISABLED); self.process_button.pack(fill=tk.X, ipady=8, pady=(5, 0)); self.status_bar = ttk.Label(frm, text="Welcome! Authenticate to load existing videos, or load local files now.", relief=tk.SUNKEN, anchor='w'); self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)
    
    def _update_gui_for_mode(self):
        self.tree.delete(*self.tree.get_children())
        if self.app_mode == "update":
            self.filter_menubutton.config(state=tk.NORMAL); self.process_button.config(text="PROCESS SELECTED VIDEOS"); self.tree.heading('id_or_path', text='Video ID'); self.tree.heading('status', text='Privacy'); self.tree.heading('upload_date', text='Upload Date (UTC)'); self.tree.column('upload_date', width=150); self.vis_cb.config(state=tk.NORMAL); self.rad_private.config(state=tk.NORMAL); self.rad_unlisted.config(state=tk.NORMAL); self.rad_public.config(state=tk.NORMAL)
            self.update_status("UPDATE MODE: Load existing videos or select from list.")
        elif self.app_mode == "upload":
            self.clear_filters(); self.filter_menubutton.config(state=tk.DISABLED); self.process_button.config(text="UPLOAD SELECTED FILES"); self.tree.heading('id_or_path', text='File Path'); self.tree.heading('status', text='Desc Source'); self.tree.heading('upload_date', text='Sub Source'); self.tree.column('upload_date', width=120)
            self.vis_cb.config(state=tk.DISABLED); self.rad_private.config(state=tk.DISABLED); self.rad_unlisted.config(state=tk.DISABLED); self.rad_public.config(state=tk.DISABLED)
            self.update_status("UPLOAD MODE: Load local files or select from list to upload.")
        self._update_ui_states()
    def _update_ui_states(self):
        is_scheduling = self.update_schedule_var.get()
        if self.app_mode == "update":
            state = tk.DISABLED if is_scheduling else tk.NORMAL
            if is_scheduling: self.update_visibility_var.set(True); self.visibility_choice_var.set('private')
            self.vis_cb.config(state=state); self.rad_private.config(state=state); self.rad_unlisted.config(state=state); self.rad_public.config(state=state)
    def _sort_column(self, col, reverse):
        def get_sort_key(item_id):
            value = self.tree.set(item_id, col)
            if col in ['publish_at', 'upload_date'] and self.app_mode == 'update' and value != "Not Scheduled":
                try: return datetime.strptime(value.replace(' UTC', ''), '%Y-%m-%d %H:%M')
                except ValueError: pass
            return value.lower()
        data = [(get_sort_key(k), k) for k in self.tree.get_children('')]; data.sort(reverse=reverse)
        for i, item in enumerate(data): self.tree.move(item[1], '', i)
        self.tree.heading(col, command=lambda c=col: self._sort_column(col, not reverse))
    def update_status(self, message): self.status_bar.config(text=message); self.root.update_idletasks()
    def apply_filters(self):
        if self.app_mode != "update": return
        active_filters = {key for key, var in self.filter_vars.items() if var.get()}
        if not active_filters: return self._populate_treeview(self.videos_to_process)
        filtered_list = []
        for vd in self.videos_to_process:
            if not isinstance(vd, VideoData): continue
            status = vd.video_status.get('privacyStatus'); has_schedule = bool(vd.video_status.get('publishAt'))
            conditions = {"public": status == 'public', "not_public": status != 'public', "private": status == 'private', "not_private": status != 'private', "unlisted": status == 'unlisted', "not_unlisted": status != 'unlisted', "has_schedule": has_schedule, "no_schedule": not has_schedule, "has_desc_file": bool(vd.description_file_path), "no_desc_file": not vd.description_file_path, "has_sub_file": bool(vd.subtitle_file_path), "no_sub_file": not vd.subtitle_file_path}
            if vd.width > 0 and vd.height > 0: conditions.update({"is_horizontal": vd.width > vd.height, "is_vertical": vd.height >= vd.width})
            if all(conditions.get(key, True) for key in active_filters): filtered_list.append(vd)
        self._populate_treeview(filtered_list)
    def clear_filters(self):
        for var in self.filter_vars.values(): var.set(False); self.apply_filters()
    def _populate_treeview(self, videos_to_display):
        self.tree.delete(*self.tree.get_children())
        if not videos_to_display: return
        if self.app_mode == "update":
            for vd in videos_to_display:
                publish_at, upload_date = vd.video_status.get('publishAt'), vd.upload_date
                if publish_at:
                    try: publish_at = datetime.fromisoformat(publish_at.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M UTC')
                    except (ValueError, TypeError): pass
                else: publish_at = "Not Scheduled"
                if upload_date:
                    try: upload_date = datetime.fromisoformat(upload_date.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M UTC')
                    except (ValueError, TypeError): pass
                self.tree.insert('', tk.END, values=(vd.video_id, vd.current_title, vd.description_filename, vd.subtitle_filename, vd.video_status.get('privacyStatus', 'N/A'), publish_at, upload_date), iid=vd.video_id)
        elif self.app_mode == "upload":
            for ve in videos_to_display: self.tree.insert('', tk.END, values=(ve.filepath, ve.title, ve.description_source, '', '', '', ve.subtitle_source), iid=ve.filepath)
        self.update_status(f"Displaying {len(videos_to_display)} videos in {self.app_mode.upper()} mode.")
    def on_video_select_display_info(self, event):
        selected_items = self.tree.selection()
        if len(selected_items) == 1:
            item_iid = selected_items[0]
            if self.app_mode == "update":
                vd_obj = next((vd for vd in self.videos_to_process if isinstance(vd, VideoData) and vd.video_id == item_iid), None)
                if vd_obj:
                    self.desc_txt.delete('1.0', tk.END); self.desc_txt.insert('1.0', vd_obj.current_description); self.tags_ent.delete(0, tk.END); self.tags_ent.insert(0, ", ".join(vd_obj.current_tags)); cat_name = next((k for k, v in self.dynamic_category_map.items() if v == vd_obj.current_category_id), "Don't Change"); self.category_cb.set(cat_name); meta_lang_name = next((k for k, v in LANGUAGES_MAP.items() if v == vd_obj.current_default_language), "Don't Change"); self.metadata_lang_cb.set(meta_lang_name); audio_lang_name = next((k for k, v in LANGUAGES_MAP.items() if v == vd_obj.current_video_language), "Don't Change"); self.audio_lang_cb.set(audio_lang_name); self.recording_date_var.set(vd_obj.current_recording_date.split('T')[0] if vd_obj.current_recording_date else ''); self.allow_embedding_var.set(vd_obj.current_embeddable); self.public_stats_var.set(vd_obj.current_public_stats_viewable)
                    if vd_obj.current_made_for_kids is True: self.made_for_kids_var.set('yes')
                    elif vd_obj.current_made_for_kids is False: self.made_for_kids_var.set('no')
                    else: self.made_for_kids_var.set('dont_change')
            elif self.app_mode == "upload":
                ve_obj = next((ve for ve in self.videos_to_process if isinstance(ve, VideoEntry) and ve.filepath == item_iid), None)
                if ve_obj: self.desc_txt.delete('1.0', tk.END); self.desc_txt.insert('1.0', ve_obj.description); self.tags_ent.delete(0, tk.END); self.tags_ent.insert(0, ", ".join(ve_obj.tags))
        elif len(selected_items) != 1: self.desc_txt.delete('1.0', tk.END); self.tags_ent.delete(0, tk.END); self.category_cb.set("Don't Change"); self.metadata_lang_cb.set("English"); self.audio_lang_cb.set("English"); self.recording_date_var.set(datetime.now().strftime('%Y-%m-%d')); self.allow_embedding_var.set(True); self.public_stats_var.set(False); self.made_for_kids_var.set('no')
    def select_credentials_and_auth(self):
        path = filedialog.askopenfilename(title='Select client_secrets.json', filetypes=[('JSON files', '*.json')])
        if path: self.update_status("Authenticating..."); self.service = get_authenticated_service(path)
        if self.service: self.load_channel_categories(); self.load_existing_button.config(state=tk.NORMAL)
        else: self.update_status("Authentication failed.")
    def load_channel_categories(self):
        self.update_status("Loading channel categories...");
        try:
            channels_resp = self.service.channels().list(part="snippet", mine=True).execute(); categories_resp = self.service.videoCategories().list(part="snippet", regionCode=channels_resp["items"][0]["snippet"].get("country", "US")).execute(); self.dynamic_category_map = {item['snippet']['title']: item['id'] for item in categories_resp.get("items", []) if item.get('snippet', {}).get('assignable', False)}; sorted_categories = sorted(self.dynamic_category_map.keys()); self.category_cb['values'] = ["Don't Change"] + sorted_categories; self.update_status("Authentication successful. Categories loaded.")
        except Exception as e: logger.error(f"Failed to load video categories: {e}"); self.update_status("Error: Could not load categories.")
    def gui_load_existing_videos(self):
        self.app_mode = "update"; self._update_gui_for_mode()
        try: max_to_load = int(self.max_videos_var.get())
        except ValueError: max_to_load = 50
        self.update_status(f"Loading up to {max_to_load or 'ALL'} videos..."); self.load_existing_button.config(state=tk.DISABLED); threading.Thread(target=self.run_video_load, args=(max_to_load,), daemon=True).start()
    def run_video_load(self, max_to_load): self.videos_to_process = self.fetch_all_videos_from_api(max_videos_to_fetch=max_to_load); self.root.after(100, self.finish_video_load)
    def finish_video_load(self): self.apply_filters(); self.process_button.config(state=tk.NORMAL); self.filter_menubutton.config(state=tk.NORMAL); self.load_existing_button.config(state=tk.NORMAL); self.update_status(f"Loaded {len(self.videos_to_process)} videos.")
    def gui_load_files_for_upload(self):
        self.app_mode = "upload"; self._update_gui_for_mode(); self.videos_to_process = []; logger.info("Scanning for video files to upload...")
        for pat in VIDEO_PATTERNS:
            for f in glob.glob(pat):
                if f not in [v.filepath for v in self.videos_to_process]: self.videos_to_process.append(VideoEntry(f))
        logger.info(f"Found {len(self.videos_to_process)} videos to upload."); self._populate_treeview(self.videos_to_process); self.process_button.config(state=tk.NORMAL if self.videos_to_process else tk.DISABLED)
    def fetch_all_videos_from_api(self, max_videos_to_fetch=0):
        all_video_data_map, video_ids = {}, []; next_page_token = None # <-- FIX: Use a dictionary to prevent duplicates
        try:
            uploads_id = self.service.channels().list(part="contentDetails", mine=True).execute()["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
            while True:
                pl_resp = self.service.playlistItems().list(playlistId=uploads_id, part="contentDetails", maxResults=50, pageToken=next_page_token).execute(); video_ids.extend([item["contentDetails"]["videoId"] for item in pl_resp["items"]])
                if max_videos_to_fetch and len(video_ids) >= max_videos_to_fetch: break
                next_page_token = pl_resp.get("nextPageToken");
                if not next_page_token: break
            if max_videos_to_fetch: video_ids = video_ids[:max_videos_to_fetch]
            logger.info("Scanning for local files to match..."); local_files = [f for f in Path.cwd().rglob('*') if f.is_file()]
            for i in range(0, len(video_ids), 50):
                self.update_status(f"Fetching details... ({min(i+50, len(video_ids))}/{len(video_ids)})"); videos_resp = self.service.videos().list(id=",".join(video_ids[i:i+50]), part="snippet,status,fileDetails").execute()
                for item in videos_resp.get("items", []):
                    video_id = item["id"]
                    if video_id in all_video_data_map: continue # <-- FIX: Skip if already processed
                    
                    vd_obj = VideoData(video_id, item["snippet"]["title"], item["snippet"], item["status"], item.get("fileDetails")); normalized_title = normalize_for_matching(vd_obj.original_title)
                    for file_path in local_files:
                        if normalize_for_matching(file_path.stem).startswith(normalized_title):
                            ext = file_path.suffix.lower()
                            if ext == '.txt' and not vd_obj.description_file_path: vd_obj.description_file_path, vd_obj.description_filename = str(file_path), file_path.name
                            elif ext in SUBTITLE_PATTERNS and not vd_obj.subtitle_file_path: vd_obj.subtitle_file_path, vd_obj.subtitle_filename = str(file_path), file_path.name
                    all_video_data_map[video_id] = vd_obj # <-- FIX: Add to dictionary
        except Exception as e: logger.error(f"Error fetching videos: {e}", exc_info=True)
        return list(all_video_data_map.values()) # <-- FIX: Return a list of unique values
    def start_processing_thread(self):
        selected_iids = self.tree.selection()
        if not selected_iids: return self.update_status("Error: No items selected.")
        self.process_button.config(state=tk.DISABLED)
        if self.app_mode == "update":
            selected_videos = [vd for vd in self.videos_to_process if isinstance(vd, VideoData) and vd.video_id in selected_iids]
            processing_data = {"videos": selected_videos, "start_time_str": self.start_ent.get(), "interval_hours": int(self.interval_hour_var.get()), "interval_mins": int(self.interval_minute_var.get()), "playlist_id": self.playlist_id_var.get().strip(), "is_dry_run": self.dry_run_var.get(), "update_schedule": self.update_schedule_var.get(), "update_visibility": self.update_visibility_var.get(), "visibility_to_set": self.visibility_choice_var.get(), "notify_subscribers": self.notify_subscribers_var.get(), "category_id": self.dynamic_category_map.get(self.category_var.get()) if self.category_var.get() != "Don't Change" else None, "description_override": self.desc_txt.get('1.0', 'end-1c'), "tags_override": self.tags_ent.get(), "metadata_lang_name": self.metadata_lang_var.get(), "audio_lang_name": self.audio_lang_var.get(), "recording_date": self.recording_date_var.get().strip(), "allow_embedding": self.allow_embedding_var.get(), "public_stats_viewable": self.public_stats_var.get(), "made_for_kids": self.made_for_kids_var.get()}
            self.update_status("Updating... Check console for details."); threading.Thread(target=self.run_update_processing, args=(processing_data,), daemon=True).start()
        elif self.app_mode == "upload":
            selected_videos = [ve for ve in self.videos_to_process if isinstance(ve, VideoEntry) and ve.filepath in selected_iids]
            self.update_status("Uploading... Check console for details."); threading.Thread(target=self.run_upload_processing, args=(selected_videos,), daemon=True).start()
    def run_update_processing(self, processing_data):
        try:
            if self.service: update_videos_on_youtube(self.service, processing_data)
            else: messagebox.showerror("Error", "Authentication is required to update videos."); self.update_status("Error: Not authenticated.")
        except Exception as e: logger.error(f"Overall update process failed: {e}", exc_info=True); self.update_status("Update process failed.")
        finally: self.root.after(100, lambda: self.process_button.config(state=tk.NORMAL)); self.root.after(100, lambda: self.update_status("Update process complete."))
    def run_upload_processing(self, selected_videos):
        try:
            if not self.service: messagebox.showerror("Error", "Authentication is required to upload videos."); self.update_status("Error: Not authenticated."); return
            desc_override = self.desc_txt.get('1.0', 'end-1c').strip(); tags_from_gui = sanitize_tags([t.strip() for t in self.tags_ent.get().split(',')]); cat_name = self.category_var.get(); cat_id = self.dynamic_category_map.get(cat_name, STATIC_CATEGORY_MAP.get(cat_name, '24')); vlang = LANGUAGES_MAP.get(self.metadata_lang_var.get(), 'en'); dlang = LANGUAGES_MAP.get(self.metadata_lang_var.get(), 'en'); rec = self.recording_date_var.get().strip(); notify = self.notify_subscribers_var.get(); kids = self.made_for_kids_var.get() == 'yes'; embed = self.allow_embedding_var.get(); stats = self.public_stats_var.get(); playlist_id = self.playlist_id_var.get().strip(); base_time = self.start_ent.get(); hrs = int(self.interval_hour_var.get()); mins = int(self.interval_minute_var.get()); move_files = self.move_files_var.get()  # Get the move files setting
            
            utc_dt = datetime.strptime(base_time, '%Y-%m-%d %H:%M').astimezone(timezone.utc)
            
            for i, e in enumerate(selected_videos):
                if desc_override: e.description = desc_override
                if tags_from_gui: e.tags = tags_from_gui
                e.categoryId = cat_id; e.videoLanguage = vlang; e.defaultLanguage = dlang; e.recordingDate = rec; e.notifySubscribers = notify; e.madeForKids = kids; e.embeddable = embed; e.publicStatsViewable = stats; e.playlistId = playlist_id; e.publishAt = (utc_dt + timedelta(hours=hrs, minutes=mins) * i).strftime('%Y-%m-%dT%H:%M:%SZ')
            
            # Pass move_files flag to upload function
            upload_new_videos(self.service, selected_videos, self.skip_subs_var.get(), move_files)
            
        except Exception as e: logger.error(f"Overall upload process failed: {e}", exc_info=True); self.update_status("Upload process failed.")
        finally: self.root.after(100, lambda: self.process_button.config(state=tk.NORMAL)); self.root.after(100, lambda: self.update_status("Upload process complete."))
    def on_exit(self):
        logger.info("GUI closed.")
        if self.save_log_var.get():
            with open(LOG_FILE, 'w', encoding='utf-8') as f: f.write("\n".join(log_records))
            print(f"Log file saved to {LOG_FILE}", flush=True)
        self.root.destroy()

def update_videos_on_youtube(service, processing_data):
    videos = processing_data["videos"]; is_dry_run = processing_data["is_dry_run"]; logger.info(f"--- Starting to UPDATE {len(videos)} videos {'(DRY RUN)' if is_dry_run else ''} ---")
    try: start_dt = datetime.strptime(processing_data["start_time_str"], '%Y-%m-%d %H:%M').astimezone(timezone.utc); delta = timedelta(hours=processing_data["interval_hours"], minutes=processing_data["interval_mins"])
    except ValueError: logger.error("Invalid date format in GUI."); return
    for i, vd in enumerate(videos):
        parts, body = [], {'id': vd.video_id}; description_content = vd.current_description; tags_content = vd.current_tags; title_content = vd.current_title
        if processing_data["description_override"].strip(): description_content = processing_data["description_override"]
        elif vd.description_file_path:
            try:
                file_content = Path(vd.description_file_path).read_text(encoding='utf-8'); data = sanitize_and_parse_json(file_content)
                if data: title_content = data.get("title", title_content); hashtags = " ".join(data.get("hashtags", [])); description_content = f"{data.get('description', '')}\n\n{hashtags}".strip(); tags_content = data.get("tags", [])
                else: description_content = file_content
            except Exception as e: logger.error(f"Could not read/parse {vd.description_filename} for {vd.original_title}: {e}")
        if processing_data["tags_override"].strip(): tags_content = [t.strip() for t in processing_data["tags_override"].split(',')]
        snippet = {'title': sanitize_for_youtube(title_content, YOUTUBE_TITLE_MAX_LENGTH), 'description': sanitize_description(description_content), 'tags': sanitize_tags(tags_content)}
        if processing_data["category_id"]: snippet['categoryId'] = processing_data["category_id"]
        else: snippet['categoryId'] = vd.current_category_id
        if processing_data["metadata_lang_name"] != "Don't Change": snippet['defaultLanguage'] = LANGUAGES_MAP[processing_data["metadata_lang_name"]]
        if processing_data["audio_lang_name"] != "Don't Change": snippet['defaultAudioLanguage'] = LANGUAGES_MAP[processing_data["audio_lang_name"]]
        body['snippet'] = snippet; parts.append('snippet')
        status = {'publicStatsViewable': processing_data["public_stats_viewable"], 'embeddable': processing_data["allow_embedding"]}
        if processing_data["update_schedule"]: status['publishAt'] = (start_dt + i * delta).isoformat(timespec='milliseconds').replace('+00:00', 'Z'); status['privacyStatus'] = 'private'
        elif processing_data["update_visibility"]: status['privacyStatus'] = processing_data["visibility_to_set"]
        if processing_data["made_for_kids"] != 'dont_change': status['selfDeclaredMadeForKids'] = (processing_data["made_for_kids"] == 'yes')
        body['status'] = status; parts.append('status')
        if processing_data["recording_date"]:
            try: rec_dt = datetime.strptime(processing_data["recording_date"], '%Y-%m-%d'); body['recordingDetails'] = {'recordingDate': rec_dt.isoformat("T") + "Z"}; parts.append('recordingDetails')
            except ValueError: logger.warning(f"-> Invalid recording date for '{vd.original_title}'. Skipping.")
        if is_dry_run: logger.info(f"DRY RUN ({i+1}/{len(videos)}): '{vd.original_title}' -> '{snippet['title']}'"); continue
        try:
            kwargs = {'part': ",".join(parts), 'body': body}
            if status.get('privacyStatus') == 'public' and vd.video_status.get('privacyStatus') != 'public' and processing_data["notify_subscribers"]: kwargs['notifySubscribers'] = True
            service.videos().update(**kwargs).execute(); logger.info(f"({i+1}/{len(videos)}) Successfully updated '{snippet['title']}'.")
            if processing_data["playlist_id"]:
                try:
                    service.playlistItems().insert(part="snippet", body={'snippet': {'playlistId': processing_data["playlist_id"], 'resourceId': {'kind': 'youtube#video', 'videoId': vd.video_id}}}).execute()
                    logger.info(f"    -> Added to playlist '{processing_data['playlist_id']}'.")
                except HttpError as pl_e:
                    if 'playlistItemDuplicate' in str(pl_e.content): logger.warning(f"    -> NOTE: Video already in playlist.")
                    else: logger.error(f"    -> FAILED to add to playlist: {pl_e.reason}")
        except HttpError as e: logger.error(f"FAILED to update '{vd.original_title}': {e.reason}"); os.makedirs(FAILED_UPDATES_FOLDER, exist_ok=True); shutil.copy(vd.description_file_path, FAILED_UPDATES_FOLDER)
        except Exception as e: logger.error(f"An unexpected error occurred for '{vd.original_title}': {e}", exc_info=True)
    logger.info("--- Update processing complete. ---")

def upload_new_videos(service, video_entries, skip_subtitles, move_files=True):
    logger.info(f"--- Starting to UPLOAD {len(video_entries)} videos ---")
    
    # Generate batch ID for this upload session
    batch_id = generate_batch_id()
    uploaded_log = []
    
    for e in video_entries:
        video_success = False
        try:
            media = MediaFileUpload(e.filepath, chunksize=-1, resumable=True)
        except FileNotFoundError:
            logger.error(f"File not found, skipping: {e.filepath}")
            continue
            
        snippet = {'title': e.title, 'categoryId': e.categoryId, 'defaultLanguage': e.defaultLanguage, 'defaultAudioLanguage': e.videoLanguage}
        if e.description: snippet['description'] = sanitize_description(e.description)
        if e.tags: snippet['tags'] = sanitize_tags(e.tags)
        if e.recordingDate:
            try: 
                rec_dt = datetime.strptime(e.recordingDate, '%Y-%m-%d')
                snippet['recordingDetails'] = {'recordingDate': rec_dt.isoformat("T") + "Z"}
            except (ValueError, TypeError): 
                logger.warning(f"-> Invalid recording date for '{e.title}'. Skipping.")
                
        status = {'privacyStatus': 'private', 'publishAt': e.publishAt, 'selfDeclaredMadeForKids': e.madeForKids, 'license': 'youtube', 'embeddable': e.embeddable, 'publicStatsViewable': e.publicStatsViewable}
        body = {'snippet': snippet, 'status': status}
        
        logger.info(f"Uploading {e.filepath} with title '{e.title}'")
        req = service.videos().insert(part='snippet,status', body=body, media_body=media, notifySubscribers=e.notifySubscribers)
        resp = None
        
        try:
            while resp is None:
                progress, resp = req.next_chunk()
            video_success = True
        except HttpError as upload_ex:
            logger.error(f"Upload failed for {e.filepath}: {upload_ex.reason}")
            # Move to failed folder if upload fails and moving is enabled
            if move_files:
                move_uploaded_files(e, batch_id, False)
            continue
            
        if not resp:
            logger.error(f"Upload of {e.filepath} failed and was skipped.")
            if move_files:
                move_uploaded_files(e, batch_id, False)
            continue
            
        vid = resp['id']
        logger.info(f"Successfully uploaded {e.filepath} -> https://youtu.be/{vid}")
        
        subtitle_success = True
        # Handle subtitle upload
        if e.subtitle_path and not skip_subtitles:
            logger.info(f"  -> Uploading subtitle file: {e.subtitle_source}")
            try:
                media_subtitle = MediaFileUpload(e.subtitle_path)
                request_body = {'snippet': {'videoId': vid, 'language': e.videoLanguage, 'name': Path(e.subtitle_path).stem, 'isDraft': False}}
                service.captions().insert(part='snippet', body=request_body, media_body=media_subtitle).execute()
                logger.info(f"  -> Subtitle upload successful for video {vid}")
            except Exception as sub_ex:
                logger.error(f"  -> Subtitle upload FAILED for video {vid}: {sub_ex}")
                subtitle_success = False
        elif e.subtitle_path and skip_subtitles:
            logger.info(f"  -> Skipping subtitle upload for: {e.subtitle_source}")
        
        # Handle playlist addition
        playlist_success = True
        if e.playlistId:
            logger.info(f"  -> Adding to playlist {e.playlistId}")
            try:
                service.playlistItems().insert(part='snippet', body={'snippet': {'playlistId': e.playlistId, 'resourceId': {'kind': 'youtube#video', 'videoId': vid}}}).execute()
                logger.info(f"  -> Successfully added to playlist.")
            except HttpError as ex:
                logger.error(f"  -> Playlist add FAILED: {ex.reason}")
                playlist_success = False
        
        # Move files if upload was successful and moving is enabled
        overall_success = video_success and subtitle_success and playlist_success
        moved_files = {}
        if move_files and overall_success:
            moved_files = move_uploaded_files(e, batch_id, True)
        
        # Log this upload
        uploaded_log.append({
            'video_id': vid,
            'original_title': e.title,
            'file_path': e.filepath,
            'success': overall_success,
            'moved_files': moved_files,
            'timestamp': datetime.now().isoformat()
        })
    
    # Save batch log if we have any uploads and moving is enabled
    if move_files and uploaded_log:
        save_upload_log(batch_id, uploaded_log)
    
    logger.info("--- Batch upload process complete. ---")

if __name__ == '__main__':
    MainApp()
    logger.info("Application has been closed.")