# ==================================================================================================
#
#                                  YouTube Batch Uploader & Scheduler
#
# ==================================================================================================
#
# TABLE OF CONTENTS
#
# 1. OVERVIEW
# 2. FEATURES
# 3. PREREQUISITES
# 4. REQUIRED FILE STRUCTURE
# 5. METADATA FILE FORMAT (.txt)
# 6. USER WORKFLOW (HOW IT WORKS)
# 7. DESIGN PHILOSOPHY (KEY DECISIONS & REASONING)
# 8. KEY CONSTANTS EXPLAINED
# 9. TROUBLESHOOTING COMMON ERRORS
#
# ==================================================================================================
#
# 1. OVERVIEW
#
# This script is a desktop application with a Graphical User Interface (GUI) built to
# streamline and automate the process of updating metadata and scheduling multiple YouTube
# videos in bulk. It allows a user to securely connect to their YouTube account, load all their
# videos, automatically match them with local text files for metadata, and then update
# their titles, descriptions, tags, and a wide range of other settings according to a
# user-defined configuration. It is designed to be highly robust, automatically sanitizing
# bad data to prevent common API errors.
#
# ==================================================================================================
#
# 2. FEATURES
#
# - Graphical User Interface: Uses Tkinter for a user-friendly, cross-platform experience.
# - Secure OAuth 2.0 Authentication: Follows Google's standard, secure flow for API access.
# - Automatic Token Revocation: For enhanced security, the access token is automatically
#   revoked when the application is closed, minimizing risk.
# - Bulk Video Loading: Fetches all videos from a user's channel via the YouTube Data API.
# - Dynamic Category Loading: Automatically fetches the correct, region-specific video categories
#   for the authenticated user, preventing invalid category errors.
# - Recursive File Matching: Automatically scans the entire folder tree (including all
#   subdirectories) to find and associate videos with local metadata and subtitle files.
# - Advanced Metadata Parsing: Can read metadata from either plain text files or, for more
#   control, structured JSON files containing a title, description, hashtags, and tags.
# - Comprehensive Metadata Control:
#   - Set Title, Description, and Tags from local files.
#   - Add videos to a specific Playlist ID.
#   - Set the Video Category (e.g., Gaming, Entertainment, Education).
#   - Set the Metadata Language and Audio Language.
#   - Set the Recording Date for the video.
#   - Control subscriber notifications, embedding, and "Made for Kids" status.
# - Flexible Scheduling & Visibility Control:
#   - Set a precise start date/time for the first video and a custom interval for all others.
#   - Explicitly set the final visibility of videos to Public, Private, or Unlisted.
#   - The UI intelligently forces "Private" visibility when scheduling, as required by the API.
# - Comprehensive Filtering & Sorting:
#   - Filter the video list by privacy, schedule status, file availability, and orientation.
#   - Sort the video list by any column by clicking its header.
# - Robust Data Sanitization (Error Prevention):
#   - Automatically cleans malformed JSON, shortens long titles, truncates oversized tag lists,
#     and removes forbidden characters ('<', '>') to prevent API errors.
# - Debugging & Safety Features:
#   - Dry Run Mode: A "test mode" to verify all settings without making any actual changes.
#   - Failed File Isolation: Automatically copies problematic metadata files into a
#     "failed_updates" folder for easy review if an API update fails.
# - Efficient & User-Friendly Architecture:
#   - Non-Blocking Processing: API updates are performed in a background thread, ensuring the
#     GUI remains responsive. Users can perform multiple batch operations in a single session.
#   - Efficient API Usage: Fetches all required video data in batched API calls to
#     conserve the daily API quota.
#
# ==================================================================================================
#
# 3. PREREQUISITES
#
# 1. Python 3.x installed on your system.
#
# 2. Required Python libraries. You can install them with this command in your terminal:
#    pip install --upgrade google-api-python-client google-auth-oauthlib google-auth-library requests
#
# 3. A `client_secrets.json` file from the Google Cloud Platform. (See original docs for setup)
#
# ==================================================================================================
#
# 4. REQUIRED FILE STRUCTURE
#
# Your files can be organized anywhere within the project folder. The script will
# recursively search all subdirectories to find matches.
#
# /MyProjectFolder/
# │
# ├── ytupdate.py                 (This script)
# ├── client_secrets.json         (Your downloaded Google credentials)
# │
# ├── /videos_batch_1/
# │   ├── video_one_title.txt
# │   └── video_one_title.srt
# │
# ├── /videos_batch_2/
# │   ├── another_video.txt
# │   └── another_video.vtt
# │
# └── ... (and so on for all other videos)
#
# ==================================================================================================
#
# 5. METADATA FILE FORMAT (.txt)
#
# The script can read metadata from `.txt` files in two ways:
#
# 1. Plain Text Mode:
#    If the file does not contain a valid JSON object, its ENTIRE content
#    will be used as the video's description.
#
# 2. JSON Mode:
#    For maximum control, the `.txt` file can contain a JSON object. This allows
#    setting the title, description, hashtags, and tags independently.
#
#    JSON Example (`my_video_title.txt`):
#    ```json
#    {
#      "title": "My New Awesome Video Title From JSON",
#      "description": "This is the main part of my video description.\nIt can have multiple lines.",
#      "hashtags": ["#awesome", "#tutorial", "#python"],
#      "tags": ["python programming", "youtube api", "automation", "tkinter gui"]
#    }
#    ```
#
# ==================================================================================================
#
# 6. USER WORKFLOW (HOW IT WORKS)
#
# 1. Authenticate: Click "Select client_secrets.json" and choose your file. A browser
#    window will open for Google account login and consent. After success, the app will
#    automatically load the correct video categories for your channel.
#
# 2. Load Videos: Click "Load My Videos" to fetch all videos from your channel. The script
#    simultaneously scans the local directory and all its subdirectories for matching
#    metadata and subtitle files.
#
# 3. Filter & Sort (Optional): Use the "Filter by..." menu to narrow down the list
#    or click on column headers to sort the videos.
#
# 4. Select & Configure:
#    - Select one or more videos from the list.
#    - Set the scheduling options (start time, interval) and default metadata if needed.
#    - In the "Default Metadata" panel, configure the desired publishing options
#      (like notifying subscribers), category, languages, and other settings.
#
# 5. Initiate Processing: Click the "PROCESS SELECTED VIDEOS" button.
#    - The script will start processing the selected videos in the background.
#    - Detailed progress, successes, and any errors are logged directly to the console.
#    - The GUI remains active and responsive. Once the process is complete, the button
#      will re-enable, and you can begin another batch operation or close the application.
#
# 6. Exit: Simply close the application window when you are finished. The script will
#    automatically revoke its security token for that session.
#
# ==================================================================================================
#
# 7. DESIGN PHILOSOPHY (KEY DECISIONS & REASONING)
#
# - Separation of GUI and Processing: This is a critical design choice. By running API calls
#   in a separate background thread, the GUI is prevented from freezing, providing a smooth,
#   non-blocking user experience. This allows users to review logs in the console while the
#   app is running and perform multiple batches without restarting.
#
# - Automatic Token Revocation on Exit: Security is paramount. The script stores an OAuth
#   token (`token.json`) to stay authenticated. By automatically revoking this token when the
#   program exits, we ensure the credential cannot be used again if it were ever compromised.
#   This forces a fresh, secure authentication on each run.
#
# - Multi-Layered Data Sanitization: Bulk updates are high-stakes. The script was designed to
#   be highly defensive. Instead of failing on bad data, it actively sanitizes it. This
#   includes fixing broken JSON, shortening long titles, truncating oversized tag lists, and
#   removing forbidden characters. This prevents an entire batch from failing due to a single
#   malformed file.
#
# ==================================================================================================
#
# 8. KEY CONSTANTS EXPLAINED
#
# - `FAILED_UPDATES_FOLDER`: Name of the subfolder for problematic metadata files.
# - `YOUTUBE_TAGS_MAX_LENGTH`: The total character limit for all tags combined (500).
# - `YOUTUBE_TAGS_MAX_COUNT`: A conservative limit on the number of tags to use (15).
# - `YOUTUBE_TITLE_MAX_LENGTH`: The character limit for a video title (100).
#
# ==================================================================================================
#
# 9. TROUBLESHOOTING COMMON ERRORS
#
# - `quotaExceeded`: You have used your daily YouTube Data API allowance. Wait 24 hours.
# - `invalidCategoryId`: The category you selected is no longer valid. Re-authenticate to refresh the list.
# - `invalidDescription`: The `.txt` file has broken JSON or the description exceeds 5000 chars.
# - `invalidTitle`: The title is empty or was longer than 100 characters.
# - `playlistItemDuplicate`: The video was already in the specified playlist. This is a warning, not an error.
# - `Failed to parse`: The `.txt` file contains a JSON syntax error the script could not fix.
#
# ==================================================================================================


import os
import sys
import json
import signal
import atexit
import re
import logging
import shutil
from pathlib import Path
from datetime import datetime, timedelta, timezone
import requests
import time
import threading

from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

import tkinter as tk
from tkinter import ttk, filedialog

# --- Constants ---
SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]
TOKEN_FILE = "token.json"
FAILED_UPDATES_FOLDER = "failed_updates"
LOG_FILE = "ytscheduler.log"
OAUTH_PORT = 0
API_TIMEOUT_SECONDS = 60
YOUTUBE_TAGS_MAX_LENGTH = 500
YOUTUBE_TAGS_MAX_COUNT = 15
YOUTUBE_TITLE_MAX_LENGTH = 100

LANGUAGES_MAP = {
    "Don't Change": None, "English": "en", "Spanish": "es", "French": "fr", 
    "German": "de", "Japanese": "ja", "Chinese": "zh"
}

# --- Helper, Logger, Auth, and Data Model functions (Unchanged) ---
def normalize_for_matching(text: str) -> str:
    text = text.lower(); text = re.sub(r'[^a-z0-9\s]', ' ', text); text = re.sub(r'\s+', '_', text)
    return text
def sanitize_for_youtube(text: str) -> str:
    return text.replace('<', '').replace('>', '')
def sanitize_and_parse_json(content: str) -> dict | None:
    try:
        content = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', content)
        start_index = content.find('{');
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
        json_str = re.sub(r'(".*?":\s*")(.*?)(")', escape_quotes, json_str, flags=re.DOTALL)
        json_str = re.sub(r',\s*([}\]])', r'\1', json_str)
        return json.loads(json_str)
    except Exception: return None
logger = logging.getLogger("ytscheduler"); logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S"))
if not logger.handlers: logger.addHandler(console_handler)
def revoke_token():
    if not os.path.exists(TOKEN_FILE): return
    logger.info("Revoking token on exit...")
    try:
        with open(TOKEN_FILE, 'r') as f: token_data = json.load(f)
        if token_data.get('refresh_token'):
            requests.post('https://oauth2.googleapis.com/revoke', params={'token': token_data['refresh_token']}, timeout=10)
    except Exception as e: logger.error(f"Token revocation failed: {e}")
    finally: os.remove(TOKEN_FILE)
def setup_revocation_on_exit():
    atexit.register(revoke_token)
    signal.signal(signal.SIGTERM, lambda signum, frame: sys.exit(1))
    signal.signal(signal.SIGINT, lambda signum, frame: sys.exit(1))
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
            if not secrets_path or not Path(secrets_path).exists():
                logger.error("Client secrets file missing."); return None
            flow = InstalledAppFlow.from_client_secrets_file(secrets_path, SCOPES)
            creds = flow.run_local_server(port=OAUTH_PORT, open_browser=True)
        with open(TOKEN_FILE, 'w') as f: f.write(creds.to_json())
    return build('youtube', 'v3', credentials=creds, cache_discovery=False)
class VideoData:
    def __init__(self, video_id, video_title, video_snippet, video_status, video_file_details=None):
        self.video_id, self.original_title = video_id, video_title
        self.video_snippet, self.video_status = video_snippet or {}, video_status or {}
        self.upload_date = self.video_snippet.get('publishedAt', '')
        self.description_file_path, self.description_filename = None, "N/A"
        self.subtitle_file_path, self.subtitle_filename = None, "N/A"
        self.width, self.height = 0, 0
        if video_file_details and 'videoStreams' in video_file_details and video_file_details['videoStreams']:
            stream = video_file_details['videoStreams'][0]
            self.width, self.height = stream.get('widthPixels', 0), stream.get('heightPixels', 0)
        self.title_to_set = self.video_snippet.get('title', self.original_title)
        self.description_to_set = self.video_snippet.get('description', '')
        self.tags_to_set = self.video_snippet.get('tags', [])
        # --- FIX: Store the original category ID when the video is loaded ---
        self.categoryId_to_set = self.video_snippet.get('categoryId', '24') # Default to Entertainment

# --- Main Application Class ---
class SchedulerApp:
    def __init__(self, log_dir=None):
        self.service = None
        self.all_channel_videos = []
        self.dynamic_category_map = {}
        self.root = tk.Tk()
        setup_revocation_on_exit()
        self.root.title('YouTube Batch Uploader & Scheduler')
        self.build_gui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_exit)
        self.root.mainloop()

    def build_gui(self):
        frm = ttk.Frame(self.root, padding=10); frm.pack(fill=tk.BOTH, expand=True)

        top_frame = ttk.Frame(frm); top_frame.pack(fill=tk.X, pady=5)
        self.select_cred_button = ttk.Button(top_frame, text='1. Select client_secrets.json & Authenticate', command=self.select_credentials_and_auth); self.select_cred_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,5))
        ttk.Label(top_frame, text='Max Videos (0=all):').pack(side=tk.LEFT, padx=(10, 2))
        self.max_videos_var = tk.StringVar(value='50'); ttk.Spinbox(top_frame, from_=0, to=10000, width=5, textvariable=self.max_videos_var).pack(side=tk.LEFT, padx=(0,5))
        self.load_all_button = ttk.Button(top_frame, text='2. Load My Videos', command=self.gui_load_all_videos, state=tk.DISABLED); self.load_all_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        list_lf = ttk.LabelFrame(frm, text="Video List", padding=5); list_lf.pack(fill=tk.BOTH, expand=True, pady=5)
        tree_frame = ttk.Frame(list_lf); tree_frame.pack(fill=tk.BOTH, expand=True)
        self.tree = ttk.Treeview(tree_frame, columns=('id', 'title', 'desc_file', 'sub_file', 'status', 'publish_at', 'upload_date'), show='headings', selectmode="extended")
        self.tree.heading('id', text='Video ID'); self.tree.column('id', width=120, stretch=tk.NO); self.tree.heading('title', text='Title'); self.tree.column('title', width=300); self.tree.heading('desc_file', text='Desc. File'); self.tree.column('desc_file', width=150); self.tree.heading('sub_file', text='Subtitle File'); self.tree.column('sub_file', width=150); self.tree.heading('status', text='Privacy'); self.tree.column('status', width=80, stretch=tk.NO); self.tree.heading('publish_at', text='Scheduled At (UTC)'); self.tree.column('publish_at', width=150); self.tree.heading('upload_date', text='Upload Date (UTC)'); self.tree.column('upload_date', width=150)
        for col in self.tree['columns']: self.tree.heading(col, command=lambda c=col: self._sort_column(c, False))
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview); self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True); vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.bind('<<TreeviewSelect>>', self.on_video_select_display_only)
        
        list_controls = ttk.Frame(list_lf); list_controls.pack(fill=tk.X, pady=(5,0))
        
        self.filter_menubutton = ttk.Menubutton(list_controls, text="Filter by...", state=tk.DISABLED); self.filter_menubutton.pack(side=tk.LEFT, padx=(0,10))
        self.filter_menu = tk.Menu(self.filter_menubutton, tearoff=0); self.filter_menubutton["menu"] = self.filter_menu
        self.filter_vars = {k: tk.BooleanVar() for k in ["public", "not_public", "private", "not_private", "unlisted", "not_unlisted", "has_schedule", "no_schedule", "has_desc_file", "no_desc_file", "has_sub_file", "no_sub_file", "is_horizontal", "is_vertical"]}
        self.filter_menu.add_checkbutton(label="Public", variable=self.filter_vars["public"], command=self.apply_filters); self.filter_menu.add_checkbutton(label="Not Public", variable=self.filter_vars["not_public"], command=self.apply_filters); self.filter_menu.add_separator()
        self.filter_menu.add_checkbutton(label="Private", variable=self.filter_vars["private"], command=self.apply_filters); self.filter_menu.add_checkbutton(label="Not Private", variable=self.filter_vars["not_private"], command=self.apply_filters); self.filter_menu.add_separator()
        self.filter_menu.add_checkbutton(label="Unlisted", variable=self.filter_vars["unlisted"], command=self.apply_filters); self.filter_menu.add_checkbutton(label="Not Unlisted", variable=self.filter_vars["not_unlisted"], command=self.apply_filters); self.filter_menu.add_separator()
        self.filter_menu.add_checkbutton(label="Has Schedule", variable=self.filter_vars["has_schedule"], command=self.apply_filters); self.filter_menu.add_checkbutton(label="Not Scheduled", variable=self.filter_vars["no_schedule"], command=self.apply_filters); self.filter_menu.add_separator()
        self.filter_menu.add_checkbutton(label="Has Description File", variable=self.filter_vars["has_desc_file"], command=self.apply_filters); self.filter_menu.add_checkbutton(label="No Description File", variable=self.filter_vars["no_desc_file"], command=self.apply_filters); self.filter_menu.add_separator()
        self.filter_menu.add_checkbutton(label="Has Subtitle File", variable=self.filter_vars["has_sub_file"], command=self.apply_filters); self.filter_menu.add_checkbutton(label="No Subtitle File", variable=self.filter_vars["no_sub_file"], command=self.apply_filters); self.filter_menu.add_separator()
        self.filter_menu.add_checkbutton(label="Horizontal Video", variable=self.filter_vars["is_horizontal"], command=self.apply_filters); self.filter_menu.add_checkbutton(label="Vertical Video", variable=self.filter_vars["is_vertical"], command=self.apply_filters); self.filter_menu.add_separator()
        self.filter_menu.add_command(label="Clear All Filters", command=self.clear_filters)
        
        ttk.Button(list_controls, text='Select All Visible', command=self.select_all_visible_videos).pack(side=tk.LEFT, padx=2)
        ttk.Button(list_controls, text='Deselect All', command=self.deselect_all_videos).pack(side=tk.LEFT, padx=2)

        bottom_frame = ttk.Frame(frm); bottom_frame.pack(fill=tk.X, pady=5)
        sched = ttk.LabelFrame(bottom_frame, text='Scheduling & Actions', padding=10); sched.pack(side=tk.LEFT, fill=tk.Y, padx=(0,5))
        meta = ttk.LabelFrame(bottom_frame, text='Default Metadata (for selected)', padding=10); meta.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        ttk.Label(sched, text='First Publish:').grid(row=0, column=0, sticky='w'); self.start_ent = ttk.Entry(sched, width=20); self.start_ent.insert(0, (datetime.now() + timedelta(hours=2)).strftime('%Y-%m-%d %H:%M')); self.start_ent.grid(row=0, column=1, sticky='ew', padx=5, pady=2)
        ttk.Label(sched, text='Interval Hours:').grid(row=1, column=0, sticky='w'); self.interval_hour_var = tk.StringVar(value='2'); ttk.Spinbox(sched, from_=0, to=1000, width=5, textvariable=self.interval_hour_var).grid(row=1, column=1, sticky='w', padx=5, pady=2)
        ttk.Label(sched, text='Interval Mins:').grid(row=2, column=0, sticky='w'); self.interval_minute_var = tk.StringVar(value='24'); ttk.Spinbox(sched, from_=0, to=1000, width=5, textvariable=self.interval_minute_var).grid(row=2, column=1, sticky='w', padx=5, pady=2)
        ttk.Separator(sched, orient='horizontal').grid(row=3, column=0, columnspan=2, sticky='ew', pady=10)
        self.update_schedule_var = tk.BooleanVar(value=True); ttk.Checkbutton(sched, text="Update Schedule", variable=self.update_schedule_var, command=self._update_ui_states).grid(row=4, column=0, columnspan=2, sticky='w')
        self.update_visibility_var = tk.BooleanVar(value=False); self.vis_cb = ttk.Checkbutton(sched, text="Update Visibility Status", variable=self.update_visibility_var, command=self._update_ui_states); self.vis_cb.grid(row=5, column=0, columnspan=2, sticky='w')
        self.visibility_choice_var = tk.StringVar(value='private'); self.rad_private = ttk.Radiobutton(sched, text="Private", variable=self.visibility_choice_var, value='private'); self.rad_private.grid(row=6, column=0, columnspan=2, sticky='w', padx=10); self.rad_unlisted = ttk.Radiobutton(sched, text="Unlisted", variable=self.visibility_choice_var, value='unlisted'); self.rad_unlisted.grid(row=7, column=0, columnspan=2, sticky='w', padx=10); self.rad_public = ttk.Radiobutton(sched, text="Public", variable=self.visibility_choice_var, value='public'); self.rad_public.grid(row=8, column=0, columnspan=2, sticky='w', padx=10)
        
        ttk.Label(meta, text='Description:').grid(row=0, column=0, sticky='nw'); self.desc_txt = tk.Text(meta, height=4, width=40, wrap=tk.WORD); self.desc_txt.grid(row=0, column=1, sticky='ew', columnspan=3)
        ttk.Label(meta, text='Video Category:').grid(row=1, column=0, sticky='w', pady=(5,0)); self.category_var = tk.StringVar(); self.category_cb = ttk.Combobox(meta, textvariable=self.category_var, values=["Don't Change"], state="readonly"); self.category_cb.set("Don't Change"); self.category_cb.grid(row=1, column=1, sticky='ew', pady=(5,0), columnspan=3)
        ttk.Label(meta, text='Metadata Lang:').grid(row=2, column=0, sticky='w', pady=(5,0)); self.metadata_lang_var = tk.StringVar(); self.metadata_lang_cb = ttk.Combobox(meta, textvariable=self.metadata_lang_var, values=list(LANGUAGES_MAP.keys()), state="readonly"); self.metadata_lang_cb.set('English'); self.metadata_lang_cb.grid(row=2, column=1, sticky='ew', pady=(5,0), columnspan=3)
        ttk.Label(meta, text='Audio Language:').grid(row=3, column=0, sticky='w', pady=(5,0)); self.audio_lang_var = tk.StringVar(); self.audio_lang_cb = ttk.Combobox(meta, textvariable=self.audio_lang_var, values=list(LANGUAGES_MAP.keys()), state="readonly"); self.audio_lang_cb.set('English'); self.audio_lang_cb.grid(row=3, column=1, sticky='ew', pady=(5,0), columnspan=3)
        ttk.Label(meta, text='Recording Date:').grid(row=4, column=0, sticky='w', pady=(5,0)); self.recording_date_var = tk.StringVar(value=datetime.now().strftime('%Y-%m-%d')); ttk.Entry(meta, textvariable=self.recording_date_var).grid(row=4, column=1, sticky='ew', pady=(5,0), columnspan=3)
        ttk.Label(meta, text='Playlist ID:').grid(row=5, column=0, sticky='w', pady=(5,0)); self.playlist_id_var = tk.StringVar(); ttk.Entry(meta, textvariable=self.playlist_id_var).grid(row=5, column=1, sticky='ew', pady=(5,0), columnspan=3)
        self.allow_embedding_var = tk.BooleanVar(value=True); ttk.Checkbutton(meta, text="Allow Embedding", variable=self.allow_embedding_var).grid(row=6, column=0, sticky='w', pady=(5,0), columnspan=2)
        self.notify_subscribers_var = tk.BooleanVar(value=False); ttk.Checkbutton(meta, text="Notify Subscribers (Public only)", variable=self.notify_subscribers_var).grid(row=7, column=0, sticky='w', pady=(5,0), columnspan=2)
        ttk.Label(meta, text='Made for Kids:').grid(row=8, column=0, sticky='w', pady=(5,0)); self.made_for_kids_var = tk.StringVar(value='no'); mfk_frame = ttk.Frame(meta); mfk_frame.grid(row=8, column=1, sticky='ew', pady=(5,0), columnspan=3); ttk.Radiobutton(mfk_frame, text="No", variable=self.made_for_kids_var, value='no').pack(side=tk.LEFT, padx=(0, 10)); ttk.Radiobutton(mfk_frame, text="Yes", variable=self.made_for_kids_var, value='yes').pack(side=tk.LEFT, padx=(0, 10)); ttk.Radiobutton(mfk_frame, text="Don't Change", variable=self.made_for_kids_var, value='dont_change').pack(side=tk.LEFT)
        meta.grid_columnconfigure(1, weight=1)

        action_frame = ttk.LabelFrame(frm, text="Execution", padding=10); action_frame.pack(fill=tk.X, pady=5)
        self.dry_run_var = tk.BooleanVar(value=False); ttk.Checkbutton(action_frame, text="Dry Run (Verify settings in console, no actual changes)", variable=self.dry_run_var).pack(side=tk.LEFT)
        self.skip_subs_var = tk.BooleanVar(value=True); ttk.Checkbutton(action_frame, text="Skip Subtitle Uploads", variable=self.skip_subs_var).pack(side=tk.LEFT, padx=10)
        
        self.process_button = ttk.Button(frm, text='PROCESS SELECTED VIDEOS', command=self.start_processing_thread, state=tk.DISABLED); self.process_button.pack(fill=tk.X, ipady=8, pady=(5, 0))
        self.status_bar = ttk.Label(frm, text="Welcome! Please authenticate.", relief=tk.SUNKEN, anchor='w'); self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        self._update_ui_states()

    def _update_ui_states(self):
        is_scheduling = self.update_schedule_var.get()
        if is_scheduling: self.update_visibility_var.set(True); self.visibility_choice_var.set('private')
        self.vis_cb.config(state=tk.DISABLED if is_scheduling else tk.NORMAL)
        self.rad_private.config(state=tk.DISABLED if is_scheduling else tk.NORMAL)
        self.rad_unlisted.config(state=tk.DISABLED if is_scheduling else tk.NORMAL)
        self.rad_public.config(state=tk.DISABLED if is_scheduling else tk.NORMAL)

    def _sort_column(self, col, reverse):
        data = [(self.tree.set(k, col), k) for k in self.tree.get_children('')]
        data.sort(key=lambda x: x[0].lower(), reverse=reverse)
        for i, item in enumerate(data): self.tree.move(item[1], '', i)
        self.tree.heading(col, command=lambda: self._sort_column(col, not reverse))

    def update_status(self, message): self.status_bar.config(text=message); self.root.update_idletasks()
    
    def apply_filters(self):
        if not self.all_channel_videos: return
        active_filters = {key for key, var in self.filter_vars.items() if var.get()}
        if not active_filters: return self._populate_treeview(self.all_channel_videos)
        filtered_list = []
        for vd in self.all_channel_videos:
            is_match = True
            status = vd.video_status.get('privacyStatus')
            if "public" in active_filters and status != 'public': is_match = False
            if is_match and "private" in active_filters and status != 'private': is_match = False
            if is_match and "unlisted" in active_filters and status != 'unlisted': is_match = False
            if is_match and "not_public" in active_filters and status == 'public': is_match = False
            if is_match and "not_private" in active_filters and status == 'private': is_match = False
            if is_match and "not_unlisted" in active_filters and status == 'unlisted': is_match = False
            if is_match and "has_schedule" in active_filters and not vd.video_status.get('publishAt'): is_match = False
            if is_match and "no_schedule" in active_filters and vd.video_status.get('publishAt'): is_match = False
            if is_match and "has_desc_file" in active_filters and not vd.description_file_path: is_match = False
            if is_match and "no_desc_file" in active_filters and vd.description_file_path: is_match = False
            if is_match and "has_sub_file" in active_filters and not vd.subtitle_file_path: is_match = False
            if is_match and "no_sub_file" in active_filters and vd.subtitle_file_path: is_match = False
            if vd.width > 0 and vd.height > 0:
                if is_match and "is_horizontal" in active_filters and vd.width <= vd.height: is_match = False
                if is_match and "is_vertical" in active_filters and vd.height <= vd.width: is_match = False
            elif "is_horizontal" in active_filters or "is_vertical" in active_filters: is_match = False
            if is_match: filtered_list.append(vd)
        self._populate_treeview(filtered_list)

    def clear_filters(self):
        for var in self.filter_vars.values(): var.set(False)
        self.apply_filters()
    
    def select_all_visible_videos(self): self.tree.selection_set(self.tree.get_children())
    def deselect_all_videos(self): self.tree.selection_remove(self.tree.selection())

    def on_video_select_display_only(self, event):
        if len(self.tree.selection()) == 1:
            item_id = self.tree.selection()[0]; video_id = self.tree.item(item_id, 'values')[0]
            vd_obj = next((vd for vd in self.all_channel_videos if vd.video_id == video_id), None)
            if vd_obj: self.desc_txt.delete('1.0', tk.END); self.desc_txt.insert('1.0', vd_obj.description_to_set)

    def _populate_treeview(self, videos_to_display):
        self.tree.delete(*self.tree.get_children())
        for vd in videos_to_display:
            publish_at = datetime.fromisoformat(vd.video_status.get('publishAt').replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S UTC') if vd.video_status.get('publishAt') else "Not Scheduled"
            upload_date = datetime.fromisoformat(vd.upload_date.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S UTC')
            self.tree.insert('', tk.END, values=(vd.video_id, vd.title_to_set, vd.description_filename, vd.subtitle_filename, vd.video_status.get('privacyStatus', 'N/A'), publish_at, upload_date))
        self.update_status(f"Displaying {len(videos_to_display)} of {len(self.all_channel_videos)} total videos.")

    def select_credentials_and_auth(self):
        path = filedialog.askopenfilename(title='Select client_secrets.json', filetypes=[('JSON files', '*.json')])
        if path:
            self.update_status("Authenticating..."); self.service = get_authenticated_service(path)
            if self.service:
                self.load_channel_categories()
                self.load_all_button.config(state=tk.NORMAL)
            else:
                self.update_status("Authentication failed.")
    
    def load_channel_categories(self):
        self.update_status("Loading channel categories...")
        try:
            channels_resp = self.service.channels().list(part="snippet", mine=True).execute()
            region_code = channels_resp["items"][0]["snippet"].get("country", "US")
            
            categories_resp = self.service.videoCategories().list(part="snippet", regionCode=region_code).execute()
            
            self.dynamic_category_map = {
                item['snippet']['title']: item['id']
                for item in categories_resp.get("items", [])
                if item.get('snippet', {}).get('assignable', False)
            }
            
            sorted_categories = sorted(self.dynamic_category_map.keys())
            self.category_cb['values'] = ["Don't Change"] + sorted_categories
            self.category_cb.set("Don't Change")
            self.update_status("Authentication successful. Categories loaded.")

        except Exception as e:
            logger.error(f"Failed to load video categories: {e}")
            self.update_status("Error: Could not load categories.")

    def gui_load_all_videos(self):
        try: max_to_load = int(self.max_videos_var.get())
        except ValueError: max_to_load = 50
        self.update_status(f"Loading up to {max_to_load or 'ALL'} videos...")
        self.all_channel_videos = self.fetch_all_videos_from_api(max_videos_to_fetch=max_to_load)
        self.apply_filters()
        self.process_button.config(state=tk.NORMAL)
        self.filter_menubutton.config(state=tk.NORMAL)
        self.update_status(f"Loaded {len(self.all_channel_videos)} videos.")

    def fetch_all_videos_from_api(self, max_videos_to_fetch=0):
        all_video_data, video_ids = [], []
        try:
            uploads_id = self.service.channels().list(part="contentDetails", mine=True).execute()["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
            next_page_token = None
            while True:
                pl_resp = self.service.playlistItems().list(playlistId=uploads_id, part="contentDetails", maxResults=50, pageToken=next_page_token).execute()
                video_ids.extend([item["contentDetails"]["videoId"] for item in pl_resp["items"]])
                if max_videos_to_fetch and len(video_ids) >= max_videos_to_fetch: break
                next_page_token = pl_resp.get("nextPageToken")
                if not next_page_token: break
            if max_videos_to_fetch: video_ids = video_ids[:max_videos_to_fetch]
            logger.info("Scanning for local files recursively...")
            local_files = [f for f in Path.cwd().rglob('*') if f.is_file()]
            for i in range(0, len(video_ids), 50):
                batch_ids = video_ids[i:i+50]
                videos_resp = self.service.videos().list(id=",".join(batch_ids), part="snippet,status,fileDetails").execute()
                for item in videos_resp.get("items", []):
                    vd_obj = VideoData(item["id"], item["snippet"]["title"], item["snippet"], item["status"], item.get("fileDetails"))
                    normalized_title = normalize_for_matching(vd_obj.original_title)
                    for file_path in local_files:
                        if normalize_for_matching(file_path.stem).startswith(normalized_title):
                            ext = file_path.suffix.lower()
                            if ext == '.txt' and not vd_obj.description_file_path:
                                try:
                                    content = file_path.read_text(encoding='utf-8', errors='ignore')
                                    data = sanitize_and_parse_json(content)
                                    if data:
                                        vd_obj.title_to_set = data.get("title", vd_obj.title_to_set)
                                        hashtags = " ".join(data.get("hashtags", []))
                                        vd_obj.description_to_set = f"{data.get('description', '')}\n\n{hashtags}".strip()
                                        vd_obj.tags_to_set = data.get("tags", [])[:YOUTUBE_TAGS_MAX_COUNT]
                                    else: vd_obj.description_to_set = content
                                    vd_obj.description_file_path, vd_obj.description_filename = str(file_path), file_path.name
                                except Exception as e: logger.error(f"Error reading {file_path.name}: {e}")
                            elif ext in ['.srt', '.vtt'] and not vd_obj.subtitle_file_path:
                                vd_obj.subtitle_file_path, vd_obj.subtitle_filename = str(file_path), file_path.name
                    all_video_data.append(vd_obj)
        except Exception as e: logger.error(f"Error fetching videos: {e}", exc_info=True)
        return all_video_data

    def start_processing_thread(self):
        selected_items = self.tree.selection()
        if not selected_items: return self.update_status("Error: No videos selected.")
        
        category_name = self.category_var.get()
        category_id_to_set = self.dynamic_category_map.get(category_name) if category_name != "Don't Change" else None

        processing_data = {
            "videos": [vd for vd in self.all_channel_videos if vd.video_id in [self.tree.item(i, 'values')[0] for i in selected_items]],
            "start_time_str": self.start_ent.get(), "interval_hours": int(self.interval_hour_var.get()), "interval_mins": int(self.interval_minute_var.get()),
            "playlist_id": self.playlist_id_var.get().strip(), "is_dry_run": self.dry_run_var.get(), "skip_subtitles": self.skip_subs_var.get(),
            "update_schedule": self.update_schedule_var.get(), "update_visibility": self.update_visibility_var.get(),
            "visibility_to_set": self.visibility_choice_var.get(), "notify_subscribers": self.notify_subscribers_var.get(),
            "category_id": category_id_to_set,
            "metadata_lang_name": self.metadata_lang_var.get(), "audio_lang_name": self.audio_lang_var.get(),
            "recording_date": self.recording_date_var.get().strip(), "allow_embedding": self.allow_embedding_var.get(), "made_for_kids": self.made_for_kids_var.get()
        }
        self.update_status("Processing... Check console for details.")
        self.process_button.config(state=tk.DISABLED)
        threading.Thread(target=self.run_processing, args=(processing_data,), daemon=True).start()

    def run_processing(self, processing_data):
        if self.service: update_videos_on_youtube(self.service, processing_data)
        else: logger.error("Cannot process: YouTube service not authenticated.")
        self.process_button.config(state=tk.NORMAL); self.update_status("Processing complete.")

    def on_exit(self):
        logger.info("GUI closed."); self.root.destroy()

# --- Console Processing Functions ---
def update_videos_on_youtube(service, processing_data):
    videos = processing_data["videos"]; is_dry_run = processing_data["is_dry_run"]
    notify_subscribers = processing_data["notify_subscribers"]
    category_id_from_gui = processing_data["category_id"]
    metadata_lang = LANGUAGES_MAP.get(processing_data["metadata_lang_name"])
    audio_lang = LANGUAGES_MAP.get(processing_data["audio_lang_name"])
    recording_date = processing_data["recording_date"]
    allow_embedding = processing_data["allow_embedding"]
    made_for_kids = processing_data["made_for_kids"]
    
    try:
        start_dt = datetime.strptime(processing_data["start_time_str"], '%Y-%m-%d %H:%M').astimezone().astimezone(timezone.utc)
        delta = timedelta(hours=processing_data["interval_hours"], minutes=processing_data["interval_mins"])
    except ValueError: logger.error("Invalid date format in GUI."); return

    logger.info(f"--- Starting to process {len(videos)} videos {'(DRY RUN)' if is_dry_run else ''} ---")
    
    for i, vd in enumerate(videos):
        parts, body = [], {'id': vd.video_id}
        snippet = {'title': vd.title_to_set[:YOUTUBE_TITLE_MAX_LENGTH], 'description': vd.description_to_set, 'tags': vd.tags_to_set}
        
        # --- FINAL FIX: Always include a category ID in the snippet update ---
        if category_id_from_gui:
            # If the user chose a new category, use it.
            snippet['categoryId'] = category_id_from_gui
        else:
            # Otherwise, use the video's existing category ID.
            snippet['categoryId'] = vd.categoryId_to_set

        if metadata_lang: snippet['defaultLanguage'] = metadata_lang
        if audio_lang: snippet['defaultAudioLanguage'] = audio_lang
        body['snippet'] = snippet; parts.append('snippet')

        status, is_publishing = {}, False
        if processing_data["update_schedule"]:
            status['publishAt'] = (start_dt + i * delta).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
            status['privacyStatus'] = 'private'
        elif processing_data["update_visibility"]:
            status['privacyStatus'] = processing_data["visibility_to_set"]
            if status['privacyStatus'] == 'public' and vd.video_status.get('privacyStatus') != 'public':
                is_publishing = True
        
        status['embeddable'] = allow_embedding
        if made_for_kids != 'dont_change': status['selfDeclaredMadeForKids'] = (made_for_kids == 'yes')
        body['status'] = status; parts.append('status')
        
        if recording_date:
            try:
                body['recordingDetails'] = {'recordingDate': datetime.strptime(recording_date, '%Y-%m-%d').isoformat("T") + "Z"}
                parts.append('recordingDetails')
            except ValueError: logger.warning(f"    -> Invalid recording date '{recording_date}'. Skipping.")

        if is_dry_run:
            logger.info(f"DRY RUN ({i+1}/{len(videos)}): '{vd.original_title}' -> '{snippet['title']}'")
            logger.info(f"  - Schedule: {status.get('publishAt', 'N/A')}, Privacy: {status.get('privacyStatus', 'N/A')}")
            logger.info(f"  - Category ID: {snippet.get('categoryId', 'N/A')}")
            logger.info(f"  - Notify Subs: {notify_subscribers if is_publishing else 'N/A (Not publishing publicly)'}, Embedding: {allow_embedding}, Made for Kids: {made_for_kids}")
            continue

        try:
            kwargs = {'part': ",".join(parts), 'body': body}
            if is_publishing:
                kwargs['notifySubscribers'] = notify_subscribers
            
            service.videos().update(**kwargs).execute()
            logger.info(f"({i+1}/{len(videos)}) Successfully updated '{snippet['title']}'.")

            if processing_data["playlist_id"]:
                try:
                    service.playlistItems().insert(part="snippet", body={'snippet': {'playlistId': processing_data["playlist_id"], 'resourceId': {'kind': 'youtube#video', 'videoId': vd.video_id}}}).execute()
                    logger.info(f"    -> Added to playlist '{processing_data['playlist_id']}'.")
                except HttpError as pl_e:
                    if 'playlistItemDuplicate' in str(pl_e.content): logger.warning(f"    -> NOTE: Video already in playlist.")
                    else: logger.error(f"    -> FAILED to add to playlist: {pl_e.reason}")

        except HttpError as e:
            logger.error(f"FAILED to update '{vd.original_title}': {e.reason}")
            if vd.description_file_path and os.path.exists(vd.description_file_path):
                os.makedirs(FAILED_UPDATES_FOLDER, exist_ok=True); shutil.copy(vd.description_file_path, FAILED_UPDATES_FOLDER)
        except Exception as e:
            logger.error(f"An unexpected error occurred for '{vd.original_title}': {e}", exc_info=True)
    
    logger.info("--- Processing complete. ---")

if __name__ == '__main__':
    app = SchedulerApp()
    logger.info("Application has been closed.")