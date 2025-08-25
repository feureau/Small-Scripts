# ==================================================================================================
#
# YouTube Batch Scheduler & Uploader
#
# --------------------------------------------------------------------------------------------------
#
# SCRIPT DOCUMENTATION
#
# --------------------------------------------------------------------------------------------------
#
# OVERVIEW
#
# This script is a desktop application with a Graphical User Interface (GUI) built to
# streamline and automate the process of updating metadata and scheduling multiple YouTube
# videos in bulk. It allows a user to connect to their YouTube account, load all their
# videos, automatically match them with local text files for metadata, and then update
# them according to a user-defined schedule.
#
# --------------------------------------------------------------------------------------------------
#
# FEATURES
#
# - Graphical User Interface: Uses Tkinter for a user-friendly, cross-platform experience.
# - Secure OAuth 2.0 Authentication: Follows Google's standard, secure flow for API access.
# - Automatic Token Revocation: For enhanced security, the access token is automatically
#   revoked when the application is closed, minimizing risk.
# - Bulk Video Loading: Fetches all videos from a user's channel via the YouTube Data API.
# - Smart Metadata Matching: Automatically associates videos with local metadata files
#   (.txt for description/tags, .srt/.vtt for subtitles) based on video titles.
# - Advanced Metadata Parsing: Can read metadata from either plain text files or, for more
#   control, structured JSON files containing a title, description, hashtags, and tags.
# - Flexible Scheduling: Allows setting a precise start date/time for the first video and a
#   custom interval (hours/minutes) for all subsequent videos.
# - Optional Updates: The user can choose to update only metadata (title, description, etc.)
#   without changing the video schedule.
# - Subtitle Uploads: Can upload subtitle files (.srt, .vtt) and associate them with the
#   correct video and language.
# - Tag Validation & Sanitization: Automatically cleans and truncates video tags to comply with
#   YouTube's 500-character limit and other API rules, preventing errors.
# - Dry Run Mode: Provides a "test mode" to verify all settings and file matches without
#   making any actual changes to the YouTube channel. The console will log what it *would* do.
# - Two-Stage Architecture: The GUI is used for configuration only. The actual API updates
#   are performed in the console after the GUI is closed, ensuring a non-blocking user
#   experience and clear, sequential logging.
# - Robust Error Handling: Includes specific checks for common API issues like quota
#   exhaustion and will gracefully abort operations if necessary.
#
# --------------------------------------------------------------------------------------------------
#
# HOW IT WORKS (USER WORKFLOW)
#
# The application operates in two distinct stages:
#
# 1. Stage 1: GUI Configuration
#    - Authenticate: The user clicks the first button to select their `client_secrets.json`
#      file, which opens a browser for Google account login and consent.
#    - Load Videos: The user clicks the second button to fetch all videos from their
#      channel. The script simultaneously scans the local directory for matching metadata files.
#    - Select & Configure: The user selects one or more videos from the list. They can then
#      set the scheduling options (start time, interval) and choose whether to update the
#      schedule, upload subtitles, or run in "Dry Run" mode.
#    - Initiate Update: The user clicks the final "UPDATE SELECTED VIDEOS & EXIT" button.
#      This action saves all the selected videos and settings into memory and closes the GUI.
#
# 2. Stage 2: Console Processing
#    - After the GUI closes, the script continues running in the command line/terminal.
#    - It iterates through the list of videos prepared in the first stage.
#    - For each video, it makes the necessary API calls to YouTube to update its metadata
#      and, if enabled, set its publication schedule.
#    - Detailed progress, successes, and any errors are logged directly to the console.
#
# --------------------------------------------------------------------------------------------------
#
# DESIGN PHILOSOPHY (REASONS FOR KEY DECISIONS)
#
# - Separation of GUI and Processing: The decision to close the GUI before processing begins
#   is intentional. API calls, especially for uploads, can be slow and are subject to network
#   latency. Performing these tasks in a separate console stage prevents the GUI from
#   freezing or becoming unresponsive, which provides a much smoother user experience. It
#   also allows for clean, uninterrupted logging of the batch process.
#
# - Automatic Token Revocation on Exit: Security is paramount. The script stores an OAuth
#   token (`token.json`) to stay authenticated. By automatically revoking this token when the
#   program exits, we ensure that the credential cannot be used again if it were ever
#   compromised. It forces a fresh authentication on each run, which is a safer default.
#
# - Batch API Calls: When fetching video details, the script first gets a list of all video
#   IDs and then requests full details in batches of 50. This is vastly more efficient and
#   consumes significantly less API quota compared to making one API call per video.
#
# - Resilient JSON Parsing: The `sanitize_and_parse_json` function is designed to be forgiving.
#   Users often copy-paste text which can lead to simple syntax errors (like unescaped quotes).
#   This function attempts to fix these common issues programmatically, making the script
#   more robust and user-friendly by avoiding failures on minor formatting mistakes.
#
# - "Dry Run" Mode as a Core Feature: Making bulk changes to a YouTube channel is a high-stakes
#   operation. The Dry Run mode acts as a critical safety net, allowing users to perform a
#   complete test run to verify that file matching, metadata parsing, and scheduling
#   calculations are all correct *before* any permanent changes are made.
#
# --------------------------------------------------------------------------------------------------
#
# PREREQUISITES
#
# 1. Python 3.x.
# 2. Required libraries: `google-api-python-client`, `google-auth-oauthlib`, `requests`.
#    You can install them with: `pip install --upgrade google-api-python-client google-auth-oauthlib google-auth-library requests`
# 3. `client_secrets.json` file: You must have a project in the Google Cloud Platform,
#    enable the "YouTube Data API v3", and create OAuth 2.0 Client ID credentials for a
#    "Desktop app". Download the resulting JSON file and save it as `client_secrets.json`.
#
# --------------------------------------------------------------------------------------------------
#
# METADATA FILE FORMAT (.txt)
#
# The script can read metadata from `.txt` files in two ways:
#
# 1. Plain Text Mode: If the file does not contain a valid JSON object, its entire content
#    will be used as the video's description.
#
# 2. JSON Mode: For maximum control, the `.txt` file can contain a JSON object. This allows
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

import os
import sys
import json
import signal
import atexit
import re
import logging
from pathlib import Path
from datetime import datetime, timedelta, timezone
import requests
import time

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
LOG_FILE = "ytscheduler.log"
OAUTH_PORT = 0
API_TIMEOUT_SECONDS = 60
YOUTUBE_TAGS_MAX_LENGTH = 500 # The official limit for total tag length
YOUTUBE_TAGS_MAX_COUNT = 15   # A safe, conservative limit to avoid API rejection

CATEGORY_MAP = {
    "Film & Animation": "1", "Autos & Vehicles": "2", "Music": "10",
    "Pets & Animals": "15", "Sports": "17", "Travel & Events": "19",
    "Gaming": "20", "People & Blogs": "22", "Comedy": "23",
    "Entertainment": "24", "News & Politics": "25", "Howto & Style": "26",
    "Education": "27", "Science & Technology": "28", "Nonprofits & Activism": "29"
}
LANGUAGES = {"English": "en", "Spanish": "es", "French": "fr", "German": "de", "Japanese": "ja", "Chinese": "zh"}

# --- Helper functions ---
def normalize_for_matching(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[\\/*?:"<>|]', "", text)
    text = re.sub(r'\s+', '_', text)
    return text

def sanitize_and_parse_json(content: str) -> dict | None:
    try:
        start_index = content.find('{')
        end_index = content.rfind('}')
        if start_index == -1 or end_index == -1 or end_index < start_index:
            return None
        json_str = content[start_index : end_index + 1]

        def escape_quotes_in_value(match):
            key_part = match.group(1)
            value_part = match.group(2)
            closing_quote = match.group(3)
            return key_part + value_part.replace('"', '\\"') + closing_quote

        json_str = re.sub(
            r'(".*?":\s*")(.*?)(")',
            escape_quotes_in_value,
            json_str,
            flags=re.DOTALL
        )
        json_str = re.sub(r',\s*([}\]])', r'\1', json_str)
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        # Re-raise the error so the calling function can catch it and log details.
        raise e
    except Exception:
        return None

# --- Logger Setup ---
logger = logging.getLogger("ytscheduler")
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S"))
if not logger.handlers:
    logger.addHandler(console_handler)

# --- Token Revocation ---
def revoke_token():
    if os.path.exists(TOKEN_FILE):
        logger.info("Attempting to revoke token...")
        try:
            with open(TOKEN_FILE, 'r') as f: token_data = json.load(f)
            if 'refresh_token' in token_data and token_data['refresh_token']:
                requests.post('https://oauth2.googleapis.com/revoke', params={'token': token_data['refresh_token']}, timeout=10)
                logger.info("Refresh token revoked.")
        except Exception as e:
            logger.error(f"Error during token revocation: {e}")
        finally:
            if os.path.exists(TOKEN_FILE):
                os.remove(TOKEN_FILE)
                logger.info(f"Local token file '{TOKEN_FILE}' deleted.")

def setup_revocation_on_exit():
    atexit.register(revoke_token)
    signal.signal(signal.SIGTERM, lambda signum, frame: sys.exit(1))
    signal.signal(signal.SIGINT, lambda signum, frame: sys.exit(1))

# --- OAuth Authentication ---
def get_authenticated_service(secrets_path):
    creds = None
    if Path(TOKEN_FILE).exists():
        try: creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        except Exception: creds = None
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try: creds.refresh(Request(timeout=API_TIMEOUT_SECONDS))
            except Exception as e:
                logger.error(f"Failed to refresh token: {e}")
                creds = None
        if not creds:
            if not secrets_path or not Path(secrets_path).exists():
                logger.error("Client secrets file missing.")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(secrets_path, SCOPES)
            creds = flow.run_local_server(port=OAUTH_PORT, open_browser=True)
        with open(TOKEN_FILE, 'w') as f:
            f.write(creds.to_json())
    return build('youtube', 'v3', credentials=creds, cache_discovery=False)

# --- Data Model ---
class VideoData:
    def __init__(self, video_id, video_title, video_snippet, video_status):
        self.video_id, self.original_title = video_id, video_title
        self.video_snippet, self.video_status = video_snippet or {}, video_status or {}
        self.description_file_path, self.description_filename = None, "N/A"
        self.subtitle_file_path, self.subtitle_filename = None, "N/A"
        self.title_to_set = self.video_snippet.get('title', self.original_title)
        self.description_to_set = self.video_snippet.get('description', '')
        self.tags_to_set = self.video_snippet.get('tags', [])
        self.categoryId_to_set = self.video_snippet.get('categoryId', CATEGORY_MAP['Entertainment'])
        self.publishAt_to_set_new = None

# --- Main Application Class ---
class SchedulerApp:
    def __init__(self, log_dir=None):
        self.service = None
        self.all_channel_videos = []
        self.videos_to_process_on_exit = []
        self.root = tk.Tk()
        setup_revocation_on_exit()
        self.root.title('YouTube Video Scheduler')
        self.build_gui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_exit)
        self.root.mainloop()

    def build_gui(self):
        frm = ttk.Frame(self.root, padding=10); frm.pack(fill=tk.BOTH, expand=True)

        top_frame = ttk.Frame(frm); top_frame.pack(fill=tk.X, pady=5)
        self.select_cred_button = ttk.Button(top_frame, text='1. Select client_secrets.json & Authenticate', command=self.select_credentials_and_auth)
        self.select_cred_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,5))
        self.load_all_button = ttk.Button(top_frame, text='2. Load My Videos', command=self.gui_load_all_videos, state=tk.DISABLED)
        self.load_all_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        list_lf = ttk.LabelFrame(frm, text="Video List", padding=5); list_lf.pack(fill=tk.BOTH, expand=True, pady=5)
        tree_frame = ttk.Frame(list_lf); tree_frame.pack(fill=tk.BOTH, expand=True)
        self.tree = ttk.Treeview(tree_frame, columns=('id', 'title', 'desc_file', 'sub_file', 'status', 'publish_at'), show='headings', selectmode="extended")
        self.tree.heading('id', text='Video ID'); self.tree.column('id', width=120, stretch=tk.NO)
        self.tree.heading('title', text='Title (New title if from JSON)'); self.tree.column('title', width=300)
        self.tree.heading('desc_file', text='Desc. File'); self.tree.column('desc_file', width=150)
        self.tree.heading('sub_file', text='Subtitle File'); self.tree.column('sub_file', width=150)
        self.tree.heading('status', text='Privacy'); self.tree.column('status', width=80, stretch=tk.NO)
        self.tree.heading('publish_at', text='Scheduled At (UTC)'); self.tree.column('publish_at', width=150)
        
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind('<<TreeviewSelect>>', self.on_video_select_display_only)
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Manually set Description...", command=lambda: self.manually_set_file('description'))
        self.context_menu.add_command(label="Manually set Subtitle...", command=lambda: self.manually_set_file('subtitle'))
        self.tree.bind("<Button-3>", self.show_context_menu)
        
        list_controls = ttk.Frame(list_lf); list_controls.pack(fill=tk.X, pady=(5,0))
        self.filter_menubutton = ttk.Menubutton(list_controls, text="Filter by Status...", state=tk.DISABLED)
        self.filter_menubutton.pack(side=tk.LEFT, padx=(0,10))
        self.filter_menu = tk.Menu(self.filter_menubutton, tearoff=0)
        self.filter_menubutton["menu"] = self.filter_menu
        
        self.filter_vars = {
            "public": tk.BooleanVar(), "not_public": tk.BooleanVar(),
            "private": tk.BooleanVar(), "not_private": tk.BooleanVar(),
            "unlisted": tk.BooleanVar(), "not_unlisted": tk.BooleanVar(),
            "has_schedule": tk.BooleanVar(),
            "no_schedule": tk.BooleanVar()
        }

        self.filter_menu.add_checkbutton(label="Public", variable=self.filter_vars["public"], command=self.apply_filters)
        self.filter_menu.add_checkbutton(label="Not Public", variable=self.filter_vars["not_public"], command=self.apply_filters)
        self.filter_menu.add_separator()
        self.filter_menu.add_checkbutton(label="Private", variable=self.filter_vars["private"], command=self.apply_filters)
        self.filter_menu.add_checkbutton(label="Not Private", variable=self.filter_vars["not_private"], command=self.apply_filters)
        self.filter_menu.add_separator()
        self.filter_menu.add_checkbutton(label="Unlisted", variable=self.filter_vars["unlisted"], command=self.apply_filters)
        self.filter_menu.add_checkbutton(label="Not Unlisted", variable=self.filter_vars["not_unlisted"], command=self.apply_filters)
        self.filter_menu.add_separator()
        self.filter_menu.add_checkbutton(label="Has Schedule", variable=self.filter_vars["has_schedule"], command=self.apply_filters)
        self.filter_menu.add_checkbutton(label="Not Scheduled", variable=self.filter_vars["no_schedule"], command=self.apply_filters)
        self.filter_menu.add_separator()
        self.filter_menu.add_command(label="Clear Filters", command=self.clear_filters)

        ttk.Button(list_controls, text='Select All Visible', command=self.select_all_visible_videos).pack(side=tk.LEFT, padx=2)
        ttk.Button(list_controls, text='Deselect All', command=self.deselect_all_videos).pack(side=tk.LEFT, padx=2)

        bottom_frame = ttk.Frame(frm); bottom_frame.pack(fill=tk.X, pady=5)
        sched = ttk.LabelFrame(bottom_frame, text='Scheduling', padding=10); sched.pack(side=tk.LEFT, fill=tk.Y, padx=(0,5))
        meta = ttk.LabelFrame(bottom_frame, text='Default Metadata (for selected)', padding=10); meta.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        ttk.Label(sched, text='First Publish (YYYY-MM-DD HH:MM):').grid(row=0, column=0, sticky='w'); self.start_ent = ttk.Entry(sched, width=20); self.start_ent.insert(0, (datetime.now() + timedelta(hours=2)).strftime('%Y-%m-%d %H:%M')); self.start_ent.grid(row=0, column=1, sticky='ew', padx=5, pady=2)
        ttk.Label(sched, text='Interval Hours:').grid(row=1, column=0, sticky='w'); self.interval_hour_var = tk.StringVar(value='2'); ttk.Spinbox(sched, from_=0, to=1000, width=5, textvariable=self.interval_hour_var).grid(row=1, column=1, sticky='w', padx=5, pady=2)
        ttk.Label(sched, text='Interval Mins:').grid(row=2, column=0, sticky='w'); self.interval_minute_var = tk.StringVar(value='24'); ttk.Spinbox(sched, from_=0, to=1000, width=5, textvariable=self.interval_minute_var).grid(row=2, column=1, sticky='w', padx=5, pady=2)

        ttk.Label(meta, text='Description:').grid(row=0, column=0, sticky='nw'); self.desc_txt = tk.Text(meta, height=5, width=40, wrap=tk.WORD); self.desc_txt.grid(row=0, column=1, sticky='ew', columnspan=2)
        ttk.Label(meta, text='Subtitle Lang:').grid(row=1, column=0, sticky='w'); self.subtitle_lang_cb = ttk.Combobox(meta, values=list(LANGUAGES.keys()), state="readonly"); self.subtitle_lang_cb.set('English'); self.subtitle_lang_cb.grid(row=1, column=1, sticky='ew', pady=(5,0))
        meta.grid_columnconfigure(1, weight=1)

        action_frame = ttk.LabelFrame(frm, text="Actions", padding=10); action_frame.pack(fill=tk.X, pady=5)
        self.dry_run_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(action_frame, text="Dry Run (Verify only, no uploads)", variable=self.dry_run_var).pack(anchor='w')
        
        self.update_schedule_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(action_frame, text="Update Schedule (Set publish time for selected videos)", variable=self.update_schedule_var).pack(anchor='w')
        
        self.skip_subs_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(action_frame, text="Skip Subtitle Uploads (Saves quota)", variable=self.skip_subs_var).pack(anchor='w')
        
        self.schedule_button = ttk.Button(action_frame, text='3. UPDATE SELECTED VIDEOS & EXIT', command=self.prepare_for_exit, state=tk.DISABLED)
        self.schedule_button.pack(fill=tk.X, ipady=8, pady=5)
        self.status_bar = ttk.Label(frm, text="Welcome! Please authenticate.", relief=tk.SUNKEN, anchor='w'); self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)

    def update_status(self, message):
        self.status_bar.config(text=message)
        self.root.update_idletasks()

    def apply_filters(self):
        if not self.all_channel_videos: return
        active_filters = {key for key, var in self.filter_vars.items() if var.get()}
        if not active_filters:
            return self._populate_treeview(self.all_channel_videos)
            
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
            
            if is_match: filtered_list.append(vd)
        
        self._populate_treeview(filtered_list)

    def clear_filters(self):
        for var in self.filter_vars.values(): var.set(False)
        self.apply_filters()

    def select_all_visible_videos(self): self.tree.selection_set(self.tree.get_children())
    def deselect_all_videos(self): self.tree.selection_remove(self.tree.selection())

    def show_context_menu(self, event):
        if len(self.tree.selection()) == 1:
            self.tree.focus(self.tree.identify_row(event.y))
            self.context_menu.post(event.x_root, event.y_root)

    def manually_set_file(self, file_type):
        selection = self.tree.selection()
        if not selection: return
        item_id = selection[0]
        video_id = self.tree.item(item_id, 'values')[0]
        
        vd_obj = next((vd for vd in self.all_channel_videos if vd.video_id == video_id), None)
        if not vd_obj: return
        
        ftypes = [('Text files', '*.txt'), ('All files', '*.*')] if file_type == 'description' else [('Subtitle Files', '*.srt *.vtt'), ('All files', '*.*')]
        path = filedialog.askopenfilename(title=f'Select {file_type.capitalize()} File', filetypes=ftypes)
        if path:
            file_path = Path(path)
            if file_type == 'description':
                vd_obj.description_to_set = file_path.read_text(encoding='utf-8', errors='ignore')
                vd_obj.description_file_path, vd_obj.description_filename = str(file_path), file_path.name
            else:
                vd_obj.subtitle_file_path, vd_obj.subtitle_filename = str(file_path), file_path.name
            self.refresh_treeview_row(item_id, vd_obj)

    def refresh_treeview_row(self, item_id, vd_obj):
        publish_at = self.format_publish_time(vd_obj.video_status.get('publishAt'))
        values = (vd_obj.video_id, vd_obj.title_to_set, vd_obj.description_filename, vd_obj.subtitle_filename, vd_obj.video_status.get('privacyStatus', 'N/A'), publish_at)
        self.tree.item(item_id, values=values)

    def _populate_treeview(self, videos_to_display):
        self.tree.delete(*self.tree.get_children())
        for vd in videos_to_display:
            publish_at = self.format_publish_time(vd.video_status.get('publishAt'))
            self.tree.insert('', tk.END, values=(vd.video_id, vd.title_to_set, vd.description_filename, vd.subtitle_filename, vd.video_status.get('privacyStatus', 'N/A'), publish_at))
        self.update_status(f"Displaying {len(videos_to_display)} of {len(self.all_channel_videos)} videos.")

    def format_publish_time(self, time_str):
        if not time_str: return "Not Scheduled"
        try: return datetime.fromisoformat(time_str.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S UTC')
        except: return time_str

    def on_video_select_display_only(self, event):
        selection = self.tree.selection()
        if len(selection) == 1:
            item_id = selection[0]
            video_id = self.tree.item(item_id, 'values')[0]
            vd_obj = next((vd for vd in self.all_channel_videos if vd.video_id == video_id), None)
            if vd_obj:
                self.desc_txt.delete('1.0', tk.END)
                self.desc_txt.insert('1.0', vd_obj.description_to_set)

    def select_credentials_and_auth(self):
        path = filedialog.askopenfilename(title='Select client_secrets.json', filetypes=[('JSON files', '*.json')])
        if path:
            self.update_status("Authenticating...")
            self.service = get_authenticated_service(path)
            if self.service:
                self.update_status("Authentication successful. Ready to load videos.")
                self.load_all_button.config(state=tk.NORMAL)
            else:
                self.update_status("Authentication failed. Check console.")

    def gui_load_all_videos(self):
        self.update_status("Loading videos from YouTube...")
        self.all_channel_videos = self.fetch_all_videos_from_api()
        self.clear_filters()
        self.filter_menubutton.config(state=tk.NORMAL)
        self.schedule_button.config(state=tk.NORMAL)
        self.update_status(f"Loaded {len(self.all_channel_videos)} videos. Ready for scheduling.")

    def fetch_all_videos_from_api(self):
        all_video_data, video_ids = [], []
        try:
            uploads_id = self.service.channels().list(part="contentDetails", mine=True).execute()["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
            
            next_page_token = None
            while True:
                pl_resp = self.service.playlistItems().list(playlistId=uploads_id, part="contentDetails", maxResults=50, pageToken=next_page_token).execute()
                video_ids.extend([item["contentDetails"]["videoId"] for item in pl_resp["items"]])
                next_page_token = pl_resp.get("nextPageToken")
                if not next_page_token: break
            
            local_files = [f for f in Path.cwd().iterdir() if f.is_file()]
            
            for i in range(0, len(video_ids), 50):
                batch_ids = video_ids[i:i+50]
                videos_resp = self.service.videos().list(id=",".join(batch_ids), part="snippet,status").execute()
                for item in videos_resp.get("items", []):
                    vd_obj = VideoData(item["id"], item["snippet"]["title"], item["snippet"], item["status"])
                    normalized_title = normalize_for_matching(vd_obj.original_title)
                    
                    for file_path in local_files:
                        file_stem_normalized = normalize_for_matching(file_path.stem)
                        if file_stem_normalized.startswith(normalized_title):
                            ext = file_path.suffix.lower()
                            
                            if ext == '.txt' and not vd_obj.description_file_path:
                                content = ""
                                try:
                                    content = file_path.read_text(encoding='utf-8', errors='ignore')
                                    try:
                                        data = sanitize_and_parse_json(content)
                                        if data and all(k in data for k in ["title", "description", "hashtags", "tags"]):
                                            logger.info(f"Matched and parsed '{file_path.name}' as JSON for '{vd_obj.original_title}'.")
                                            vd_obj.title_to_set = data["title"]
                                            hashtags_str = " ".join(data.get("hashtags", []))
                                            vd_obj.description_to_set = f"{data['description']}\n\n{hashtags_str}".strip()
                                            vd_obj.tags_to_set = data["tags"]
                                        else:
                                            vd_obj.description_to_set = content
                                    except json.JSONDecodeError as e:
                                        logger.error(f"Failed to parse '{file_path.name}'. Reason: {e.msg} (line {e.lineno}, col {e.colno}). Treating as plain text.")
                                        vd_obj.description_to_set = content
                                
                                except Exception as e:
                                    logger.error(f"Error reading file {file_path.name}: {e}")
                                    vd_obj.description_to_set = content

                                vd_obj.description_file_path, vd_obj.description_filename = str(file_path), file_path.name

                            elif ext in ['.srt', '.vtt', '.scc'] and not vd_obj.subtitle_file_path:
                                vd_obj.subtitle_file_path, vd_obj.subtitle_filename = str(file_path), file_path.name
                    
                    all_video_data.append(vd_obj)
        except Exception as e:
            logger.error(f"Error fetching videos: {e}", exc_info=True)
            self.update_status(f"Error fetching videos: {e}")
        return all_video_data

    def prepare_for_exit(self):
        selected_items = self.tree.selection()
        if not selected_items:
            return self.update_status("Error: No videos selected to schedule.")
        
        self.videos_to_process_on_exit = {
            "videos": [vd for vd in self.all_channel_videos if vd.video_id in [self.tree.item(i, 'values')[0] for i in selected_items]],
            "start_time_str": self.start_ent.get(),
            "interval_hours": int(self.interval_hour_var.get()),
            "interval_mins": int(self.interval_minute_var.get()),
            "subtitle_lang": self.subtitle_lang_cb.get(),
            "is_dry_run": self.dry_run_var.get(),
            "skip_subtitles": self.skip_subs_var.get(),
            "update_schedule": self.update_schedule_var.get()
        }
        
        logger.info("Configuration complete. Closing GUI and starting console processing.")
        self.root.destroy()

    def on_exit(self):
        logger.info("GUI closed.")
        self.root.destroy()

# --- Console Processing Functions ---
def update_videos_on_youtube(service, processing_data):
    if not service or not processing_data or not processing_data.get("videos"):
        logger.error("Could not start console processing: Missing service or video data.")
        return

    videos_to_update = processing_data["videos"]
    subtitle_lang_name = processing_data["subtitle_lang"]
    is_dry_run = processing_data["is_dry_run"]
    skip_subtitles = processing_data["skip_subtitles"]
    update_schedule = processing_data["update_schedule"]
    
    try:
        start_dt_local = datetime.strptime(processing_data["start_time_str"], '%Y-%m-%d %H:%M')
        start_dt_utc = start_dt_local.astimezone().astimezone(timezone.utc)
        delta = timedelta(hours=processing_data["interval_hours"], minutes=processing_data["interval_mins"])
    except (ValueError, TypeError) as e:
        logger.error(f"Invalid date or interval data passed from GUI: {e}")
        return
    
    logger.info("-------------------------------------------------")
    if is_dry_run:
        logger.info("DRY RUN MODE: No changes will be made to YouTube.")
    logger.info(f"Starting to process {len(videos_to_update)} videos in console.")
    
    succ, fail = 0, 0
    curr_pub_utc = start_dt_utc

    for i, vd_obj in enumerate(videos_to_update):
        if update_schedule:
            vd_obj.publishAt_to_set_new = curr_pub_utc.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        else:
            vd_obj.publishAt_to_set_new = None # Explicitly set to None if not scheduling
            
        final_tags = []
        current_length = 0
        original_tags = vd_obj.tags_to_set if isinstance(vd_obj.tags_to_set, list) else []

        for tag in original_tags:
            if not isinstance(tag, str): continue
            
            sanitized_tag = tag.replace('#', '').replace('<', '').replace('>', '').replace(',', '').strip()
            if not sanitized_tag: continue

            if len(final_tags) >= YOUTUBE_TAGS_MAX_COUNT:
                logger.warning(f"  -> WARNING: Tag list for '{vd_obj.original_title}' truncated due to tag count limit ({YOUTUBE_TAGS_MAX_COUNT}).")
                break

            if current_length + len(sanitized_tag) + 1 > YOUTUBE_TAGS_MAX_LENGTH:
                logger.warning(f"  -> WARNING: Tag list for '{vd_obj.original_title}' truncated due to 500-character limit.")
                break
            
            final_tags.append(sanitized_tag)
            current_length += len(sanitized_tag) + 1

        if is_dry_run:
            logger.info(f"DRY RUN ({i+1}/{len(videos_to_update)}): Video '{vd_obj.original_title}'")
            logger.info(f"  - Would set title to: '{vd_obj.title_to_set}'")
            logger.info(f"  - Would set tags to (validated): {final_tags}")
            if vd_obj.publishAt_to_set_new:
                logger.info(f"  - Would be scheduled for: {vd_obj.publishAt_to_set_new}")
            else:
                logger.info("  - Schedule update is disabled by user setting.")
            if vd_obj.subtitle_file_path and not skip_subtitles:
                logger.info(f"  - Would upload subtitle: '{vd_obj.subtitle_filename}'")
            elif skip_subtitles:
                logger.info("  - Subtitle upload skipped by user setting.")
            else:
                 logger.info("  - No subtitle file matched.")
            succ += 1
            if update_schedule:
                curr_pub_utc += delta
            continue

        try:
            # Build the request body dynamically based on whether we are scheduling
            request_body_status = {'privacyStatus': 'private'}
            if vd_obj.publishAt_to_set_new:
                request_body_status['publishAt'] = vd_obj.publishAt_to_set_new
            
            service.videos().update(part="snippet,status", body={
                'id': vd_obj.video_id,
                'snippet': {
                    'title': vd_obj.title_to_set, 
                    'description': vd_obj.description_to_set, 
                    'tags': final_tags, 
                    'categoryId': vd_obj.categoryId_to_set
                },
                'status': request_body_status
            }).execute()
            logger.info(f"({i+1}/{len(videos_to_update)}) Metadata updated for '{vd_obj.title_to_set}' ({vd_obj.video_id})")

            if vd_obj.subtitle_file_path and not skip_subtitles:
                lang_code = LANGUAGES.get(subtitle_lang_name, 'en')
                media_body = MediaFileUpload(vd_obj.subtitle_file_path, chunksize=-1, resumable=False)
                service.captions().insert(
                    part='snippet',
                    body={'snippet': {'videoId': vd_obj.video_id, 'language': lang_code, 'name': subtitle_lang_name}},
                    media_body=media_body
                ).execute()
                logger.info(f"    -> Subtitle '{vd_obj.subtitle_filename}' uploaded.")
            
            succ += 1
            if update_schedule:
                curr_pub_utc += delta

        except HttpError as e:
            fail += 1
            if e.resp.status == 403 and 'quotaExceeded' in str(e.content):
                logger.error(f"Failed to process video '{vd_obj.original_title}' due to exhausted quota.")
                logger.warning("!!! YouTube API Quota Exceeded. ABORTING all remaining operations. !!!")
                break
            else:
                logger.error(f"Failed to process video {vd_obj.video_id} ('{vd_obj.original_title}'):", exc_info=True)

        except Exception as e:
            fail += 1
            logger.error(f"An unexpected error occurred for video {vd_obj.video_id} ('{vd_obj.original_title}'):", exc_info=True)

    total_videos = len(videos_to_update)
    unprocessed = total_videos - (succ + fail)

    logger.info("-------------------------------------------------")
    logger.info("Processing complete.")
    logger.info(f"  Successfully processed: {succ}")
    logger.info(f"  Failed: {fail}")
    if unprocessed > 0:
        logger.warning(f"  Unprocessed (due to early exit): {unprocessed}")
    logger.info("-------------------------------------------------")


if __name__ == '__main__':
    app = SchedulerApp()
    
    if app.videos_to_process_on_exit and app.service:
        update_videos_on_youtube(app.service, app.videos_to_process_on_exit)
    else:
        logger.info("No scheduling data was prepared. Exiting.")