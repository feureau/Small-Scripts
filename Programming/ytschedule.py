# ==================================================================================================
#
# YouTube Batch Scheduler & Uploader
#
# Overview:
# This script provides a graphical user interface (GUI) to facilitate the batch scheduling
# of YouTube videos. It automates the process of setting publication times, descriptions,
# and subtitles by matching local files to video titles on YouTube. After configuration,
# it performs all API operations in the console for clear, non-blocking progress logging.
#
# Features:
#   - Secure OAuth 2.0 authentication with Google.
#   - Automated matching of local .txt (description) and .srt/.vtt (subtitle) files to
#     YouTube videos based on title.
#   - Robust file matching that handles inconsistencies (e.g., spaces vs. underscores).
#   - A GUI for easy visual selection and configuration of videos.
#   - Multi-select (Ctrl/Shift+Click) and Select All/Deselect All capabilities.
#   - Precise 'AND' filtering to show videos by status (Public, Private, Unlisted) and
#     whether they have a schedule.
#   - Manual override via a right-click context menu to assign a specific description or
#     subtitle file to a single video.
#   - Batch scheduling with a configurable start time and interval.
#   - API Quota safety tools:
#       * A "Dry Run" mode to verify actions without making any actual changes.
#       * A "Skip Subtitle Uploads" option to save on expensive API quota costs.
#   - Hybrid GUI-to-Console workflow: Setup is visual, but processing is done in the
#     console to provide clear progress and prevent the GUI from freezing.
#   - Non-modal feedback: Uses a status bar instead of pop-ups for a smoother user experience.
#
# Workflow / How to Use:
#   1. Prerequisites:
#      - Place this script in a directory.
#      - Obtain your `client_secrets.json` file from the Google Cloud Console and place it
#        in a known location.
#
#   2. File Preparation (The Core Concept):
#      - In the same directory as the script, place your description and subtitle files.
#      - Name the files to match the title of the YouTube video they correspond to. The
#        matching is flexible (e.g., for a video titled "My Awesome Video", files like
#        `My_Awesome_Video.txt`, `my awesome video.srt`, or `My_Awesome_Video_final.vtt`
#        will all match).
#
#   3. Running the Script:
#      - Execute the script from your terminal (`python your_script_name.py`).
#
#   4. Using the GUI:
#      a. Step 1: Click "Select client_secrets.json & Authenticate". A browser window will
#         open for you to log in and grant permission.
#      b. Step 2: Click "Load My Videos". The script will fetch all videos from your channel
#         and automatically try to match local files. The results will appear in the list.
#      c. Step 3: Select the videos you want to schedule using Ctrl+Click, Shift+Click, or
#         the "Select All" button.
#      d. Step 4: Configure the scheduling start time and interval.
#      e. Step 5: (Optional) Set a default description or select the subtitle language.
#         Review the matched files in the list. Right-click a video for manual overrides.
#      f. Step 6: (Recommended) Check "Dry Run" first to verify your settings.
#      g. Step 7: When ready, uncheck "Dry Run" and click "SCHEDULE SELECTED VIDEOS & EXIT".
#
#   5. Console Processing:
#      - The GUI will close, and all upload/update progress will be printed to the console
#        where you ran the script.
#
# Design Decisions:
#   - Hybrid GUI/CLI Approach: The GUI is used for complex, interactive tasks like selection
#     and configuration. The actual, time-consuming API calls are then handed off to the
#     console. This prevents the GUI from freezing during network operations and provides a
#     clear, scrollable log of the results, which is superior for batch processing.
#
#   - File-Based Automation: The core design assumes that managing metadata as local text
#     files is more efficient for batch workflows than manually pasting into a GUI. This
#     allows users to prepare all their content in their preferred text editor beforehand.
#
#   - Robust File Matching: The initial matching was brittle. A `normalize_for_matching`
#     function was created to handle common variations in filenames (case, spaces,
#     underscores, special characters), making the automation far more reliable.
#
#   - API Quota Management Tools: The YouTube Data API v3 has a limited daily quota, and
#     subtitle uploads are extremely expensive (400 units). The "Dry Run" and "Skip Subtitles"
#     options were added to give the user complete control over their quota usage, preventing
#     accidental exhaustion. Raw error tracebacks for quota errors were restored at user
#     request for unfiltered debugging.
#
#   - Non-Modal UI Feedback: Annoying pop-ups were intentionally replaced with a persistent
#     status bar at the bottom of the GUI. This provides necessary feedback without
#     interrupting the user's workflow.
#
#   - Precise 'AND' Filtering: The filter logic was explicitly designed to be conjunctive
#     ('AND'). This allows for powerful, precise narrowing of video lists (e.g., find all
#     videos that are 'Private' AND 'Have a schedule'), which is more useful than a broad
#     'OR' filter for management tasks.
#
#   - Manual Overrides: While automation is the goal, it can fail. The right-click context
#     menu is a crucial escape hatch, ensuring the user is never stuck and always has
#     final control over the file associations for each video.
#
# Dependencies:
#   - requests
#   - google-api-python-client
#   - google-auth-oauthlib
#   - google-auth-httplib2
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

# --- Logger Setup ---
logger = logging.getLogger("ytscheduler")
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S"))
if not logger.handlers:
    logger.addHandler(console_handler)
file_log_handler_global = None

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
    def __init__(self):
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
        self.tree.heading('title', text='Current Title'); self.tree.column('title', width=300)
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

        ttk.Label(sched, text='First Publish (YYYY-MM-DD HH:MM):').grid(row=0, column=0, sticky='w'); self.start_ent = ttk.Entry(sched, width=20); self.start_ent.insert(0, (datetime.now() + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M')); self.start_ent.grid(row=0, column=1, sticky='ew', padx=5, pady=2)
        ttk.Label(sched, text='Interval Hours:').grid(row=1, column=0, sticky='w'); self.interval_hour_var = tk.StringVar(value='0'); ttk.Spinbox(sched, from_=0, to=1000, width=5, textvariable=self.interval_hour_var).grid(row=1, column=1, sticky='w', padx=5, pady=2)
        ttk.Label(sched, text='Interval Mins:').grid(row=2, column=0, sticky='w'); self.interval_minute_var = tk.StringVar(value='0'); ttk.Spinbox(sched, from_=0, to=59, width=5, textvariable=self.interval_minute_var).grid(row=2, column=1, sticky='w', padx=5, pady=2)

        ttk.Label(meta, text='Description:').grid(row=0, column=0, sticky='nw'); self.desc_txt = tk.Text(meta, height=5, width=40, wrap=tk.WORD); self.desc_txt.grid(row=0, column=1, sticky='ew', columnspan=2)
        ttk.Label(meta, text='Subtitle Lang:').grid(row=1, column=0, sticky='w'); self.subtitle_lang_cb = ttk.Combobox(meta, values=list(LANGUAGES.keys()), state="readonly"); self.subtitle_lang_cb.set('English'); self.subtitle_lang_cb.grid(row=1, column=1, sticky='ew', pady=(5,0))
        meta.grid_columnconfigure(1, weight=1)

        action_frame = ttk.LabelFrame(frm, text="Actions", padding=10); action_frame.pack(fill=tk.X, pady=5)
        self.dry_run_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(action_frame, text="Dry Run (Verify only, no uploads)", variable=self.dry_run_var).pack(anchor='w')
        self.skip_subs_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(action_frame, text="Skip Subtitle Uploads (Saves quota)", variable=self.skip_subs_var).pack(anchor='w')
        
        self.schedule_button = ttk.Button(action_frame, text='3. SCHEDULE SELECTED VIDEOS & EXIT', command=self.prepare_for_exit, state=tk.DISABLED); self.schedule_button.pack(fill=tk.X, ipady=8, pady=5)
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

            # Inclusionary privacy filters
            if "public" in active_filters and status != 'public': is_match = False
            if is_match and "private" in active_filters and status != 'private': is_match = False
            if is_match and "unlisted" in active_filters and status != 'unlisted': is_match = False

            # Exclusionary privacy filters
            if is_match and "not_public" in active_filters and status == 'public': is_match = False
            if is_match and "not_private" in active_filters and status == 'private': is_match = False
            if is_match and "not_unlisted" in active_filters and status == 'unlisted': is_match = False

            # Schedule filters
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
        item_id = self.tree.selection()[0]
        video_id = self.tree.item(item_id, 'values')[0]
        vd_obj = next((vd for vd in self.all_channel_videos if vd.video_id == video_id), None)
        if not vd_obj: return
        ftypes = [('Text files', '*.txt'), ('All files', '*.*')] if file_type == 'description' else [('Subtitle Files', '*.srt *.vtt'), ('All files', '*.*')]
        path = filedialog.askopenfilename(title=f'Select {file_type.capitalize()} File', filetypes=ftypes)
        if path:
            filename = Path(path).name
            if file_type == 'description':
                vd_obj.description_to_set = Path(path).read_text(encoding='utf-8', errors='ignore')
                vd_obj.description_file_path, vd_obj.description_filename = path, filename
            else:
                vd_obj.subtitle_file_path, vd_obj.subtitle_filename = path, filename
            self.refresh_treeview_row(item_id, vd_obj)

    def refresh_treeview_row(self, item_id, vd_obj):
        publish_at = self.format_publish_time(vd_obj.video_status.get('publishAt'))
        values = (vd_obj.video_id, vd_obj.original_title, vd_obj.description_filename, vd_obj.subtitle_filename, vd_obj.video_status.get('privacyStatus', 'N/A'), publish_at)
        self.tree.item(item_id, values=values)

    def _populate_treeview(self, videos_to_display):
        self.tree.delete(*self.tree.get_children())
        for vd in videos_to_display:
            publish_at = self.format_publish_time(vd.video_status.get('publishAt'))
            self.tree.insert('', tk.END, values=(vd.video_id, vd.original_title, vd.description_filename, vd.subtitle_filename, vd.video_status.get('privacyStatus', 'N/A'), publish_at))
        self.update_status(f"Displaying {len(videos_to_display)} of {len(self.all_channel_videos)} videos.")

    def format_publish_time(self, time_str):
        if not time_str: return "Not Scheduled"
        try: return datetime.fromisoformat(time_str.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S UTC')
        except: return time_str

    def on_video_select_display_only(self, event):
        if len(self.tree.selection()) == 1:
            video_id = self.tree.item(self.tree.selection()[0], 'values')[0]
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
                                vd_obj.description_to_set = file_path.read_text(encoding='utf-8', errors='ignore')
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
            "skip_subtitles": self.skip_subs_var.get()
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
        vd_obj.publishAt_to_set_new = curr_pub_utc.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        
        if is_dry_run:
            logger.info(f"DRY RUN ({i+1}/{len(videos_to_update)}): Video '{vd_obj.original_title}'")
            logger.info(f"  - Would be scheduled for: {vd_obj.publishAt_to_set_new}")
            if vd_obj.subtitle_file_path and not skip_subtitles:
                logger.info(f"  - Would upload subtitle: '{vd_obj.subtitle_filename}'")
            elif skip_subtitles:
                logger.info("  - Subtitle upload skipped by user setting.")
            else:
                 logger.info("  - No subtitle file matched.")
            succ += 1
            curr_pub_utc += delta
            continue

        try:
            service.videos().update(part="snippet,status", body={
                'id': vd_obj.video_id,
                'snippet': {'title': vd_obj.title_to_set, 'description': vd_obj.description_to_set, 'tags': vd_obj.tags_to_set, 'categoryId': vd_obj.categoryId_to_set},
                'status': {'privacyStatus': 'private', 'publishAt': vd_obj.publishAt_to_set_new}
            }).execute()
            logger.info(f"({i+1}/{len(videos_to_update)}) Metadata updated for '{vd_obj.original_title}' ({vd_obj.video_id})")

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