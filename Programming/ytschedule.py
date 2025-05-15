import os
import sys
import json
import signal
import atexit
import re
import logging
from pathlib import Path
from datetime import datetime, timedelta, timezone
import requests # Keep for token revocation

from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# --- Constants ---
SCOPES = [
    "https://www.googleapis.com/auth/youtube", # Comprehensive scope
    "https://www.googleapis.com/auth/youtube.force-ssl" # Recommended
]
TOKEN_FILE = "token.json"
LOG_FILE = "ytscheduler.log"
OAUTH_PORT = 8080

CATEGORY_MAP = {
    "Film & Animation": "1", "Autos & Vehicles": "2", "Music": "10",
    "Pets & Animals": "15", "Sports": "17", "Travel & Events": "19",
    "Gaming": "20", "People & Blogs": "22", "Comedy": "23",
    "Entertainment": "24", "News & Politics": "25", "Howto & Style": "26",
    "Education": "27", "Science & Technology": "28", "Nonprofits & Activism": "29"
}
LANGUAGES = {"English": "en", "Spanish": "es", "French": "fr", "German": "de", "Japanese": "ja", "Chinese": "zh"}

# --- Logger (in-memory) ---
logger = logging.getLogger("ytscheduler")
logger.setLevel(logging.INFO)
log_records = []
class ListHandler(logging.Handler):
    def emit(self, record):
        log_records.append(self.format(record))
handler = ListHandler()
handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S"))
logger.addHandler(handler)

# --- Token revocation ---
def revoke_token():
    if os.path.exists(TOKEN_FILE):
        logger.info("Attempting to revoke token...")
        try:
            with open(TOKEN_FILE, 'r') as f:
                token_data = json.load(f)
            
            if 'refresh_token' in token_data and token_data['refresh_token']:
                revoke_params = {'token': token_data['refresh_token']}
                response = requests.post(
                    'https://oauth2.googleapis.com/revoke',
                    params=revoke_params,
                    headers={'content-type': 'application/x-www-form-urlencoded'}
                )
                if response.status_code == 200:
                    logger.info(f"Refresh token revoked successfully from server (token: ...{token_data['refresh_token'][-6:]}).")
                else:
                    logger.warning(f"Failed to revoke refresh token from server. Status: {response.status_code}, Response: {response.text}")
        except FileNotFoundError:
            logger.info("Token file not found for revocation.")
        except Exception as e:
            logger.error(f"Error during token data loading or server-side revocation: {e}")
        finally:
            try:
                os.remove(TOKEN_FILE)
                logger.info(f"Local token file '{TOKEN_FILE}' deleted.")
            except OSError as e:
                logger.error(f"Error deleting local token file '{TOKEN_FILE}': {e}")
    else:
        logger.info("No token file to revoke or delete.")

def setup_revocation_on_exit():
    atexit.register(revoke_token)
    def on_sig(signum, frame):
        logger.info(f"Signal {signum} received, attempting token revocation before exit.")
        revoke_token()
        sys.exit(1)
    if hasattr(signal, 'SIGINT'): signal.signal(signal.SIGINT, on_sig)
    if hasattr(signal, 'SIGTERM'): signal.signal(signal.SIGTERM, on_sig)
    if hasattr(signal, 'SIGBREAK'): signal.signal(signal.SIGBREAK, on_sig)


# --- OAuth Authentication ---
def get_authenticated_service(secrets_path):
    from oauthlib.oauth2.rfc6749.errors import MismatchingStateError
    creds = None
    if Path(TOKEN_FILE).exists():
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        except Exception as e:
            logger.warning(f"Failed to load token from file: {e}. Will attempt re-authentication.")
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("Refreshing expired credentials...")
            try:
                creds.refresh(Request())
            except Exception as e:
                logger.error(f"Failed to refresh credentials: {e}. Proceeding to full auth.")
                creds = None
        
        if not creds:
            logger.info("No valid credentials found. Starting new OAuth flow.")
            if not secrets_path or not Path(secrets_path).exists():
                logger.error("Client secrets file path not provided or file does not exist.")
                raise FileNotFoundError("Client secrets file is required for new authentication.")
            
            flow = InstalledAppFlow.from_client_secrets_file(secrets_path, SCOPES)
            try:
                creds = flow.run_local_server(
                    port=OAUTH_PORT, open_browser=True,
                    authorization_prompt_message="Please visit this URL:\n{url}",
                    success_message="Authentication successful! You can close this tab.",
                    timeout_seconds=300 
                )
            except MismatchingStateError as mse: 
                logger.warning(f"Mismatching state error during local server auth: {mse}. Falling back to console.")
                creds = flow.run_console()
            except Exception as e: 
                logger.warning(f"Local server auth failed: {e}. Falling back to console.")
                creds = flow.run_console()
        
        with open(TOKEN_FILE, 'w') as f: f.write(creds.to_json())
        logger.info("Credentials saved to token.json")
    return build('youtube', 'v3', credentials=creds, cache_discovery=False)

# --- Helpers ---
def sanitize_description(desc: str) -> str:
    desc = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F]', '', desc)
    return desc[:4999]

def sanitize_tags(raw_tags):
    clean = []
    current_length = 0
    for t in raw_tags:
        tag = str(t).strip()
        if not tag: continue
        tag = re.sub(r'[\x00-\x1F\x7F\"]', '', tag)
        tag = tag[:75]
        if current_length + len(tag) + (1 if clean else 0) > 480:
            logger.warning(f"Tag '{tag}' truncated or skipped as total tag length exceeds limit.")
            break
        if tag:
            clean.append(tag)
            current_length += len(tag) + (1 if len(clean) > 1 else 0)
    return clean

# --- VideoData model ---
class VideoData:
    def __init__(self, video_id, title, current_snippet, current_status):
        self.video_id = video_id
        self.original_title = title
        self.current_snippet = current_snippet
        self.current_status = current_status

        self.title_to_set = title
        self.description_to_set = current_snippet.get('description', '')
        self.tags_to_set = current_snippet.get('tags', [])
        self.categoryId_to_set = current_snippet.get('categoryId', CATEGORY_MAP['Entertainment'])
        self.videoLanguage_to_set = current_snippet.get('defaultAudioLanguage')
        self.defaultLanguage_to_set = current_snippet.get('defaultLanguage')
        self.recordingDate_to_set = (current_snippet.get('recordingDetails') or {}).get('recordingDate')
        
        self.madeForKids_to_set = current_status.get('selfDeclaredMadeForKids', False)
        self.embeddable_to_set = current_status.get('embeddable', True)
        self.publicStatsViewable_to_set = current_status.get('publicStatsViewable', True)
        
        self.publishAt_to_set = None
        self.privacyStatus_to_set = 'private'

    def __str__(self):
        return f"ID: {self.video_id}, Title: {self.original_title}, PublishAt: {self.publishAt_to_set or 'Not Set'}"


# --- Main GUI app ---
class SchedulerApp:
    def __init__(self):
        self.client_secrets_path = None
        self.service = None
        self.all_channel_videos = [] # Stores all fetched VideoData objects
        self.current_filter_applied = "all" # To know which filter is active

        try:
            if os.path.exists(LOG_FILE): os.remove(LOG_FILE)
        except Exception as e:
            logger.warning(f"Could not remove old log file: {e}")
        
        self.root = tk.Tk()
        setup_revocation_on_exit() 

        self.save_log_var = tk.BooleanVar(master=self.root, value=False) # Default set to False
        self.root.title('YouTube Video Scheduler')
        self.build_gui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_exit)
        self.root.mainloop()

    def build_gui(self):
        frm = ttk.Frame(self.root, padding=10)
        frm.pack(fill=tk.BOTH, expand=True)

        # --- Credentials Frame ---
        cred_frm = ttk.Frame(frm)
        cred_frm.pack(fill=tk.X, pady=(0,5))
        self.select_cred_button = ttk.Button(cred_frm, text='Select Credentials JSON', command=self.select_credentials)
        self.select_cred_button.pack(side=tk.LEFT, padx=(0,10))

        # --- Load and Filter Videos Frame ---
        load_filter_lf = ttk.LabelFrame(frm, text="Video List Management", padding=5)
        load_filter_lf.pack(fill=tk.X, pady=5)

        self.load_all_button = ttk.Button(load_filter_lf, text='Load All My Videos (Refresh)', command=self.gui_load_all_videos, state=tk.DISABLED)
        self.load_all_button.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        
        self.filter_all_button = ttk.Button(load_filter_lf, text='Show All', command=lambda: self.apply_filter_to_treeview("all"), state=tk.DISABLED)
        self.filter_all_button.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        
        self.filter_private_button = ttk.Button(load_filter_lf, text='Filter: Private', command=lambda: self.apply_filter_to_treeview("private"), state=tk.DISABLED)
        self.filter_private_button.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)

        self.filter_unlisted_button = ttk.Button(load_filter_lf, text='Filter: Unlisted', command=lambda: self.apply_filter_to_treeview("unlisted"), state=tk.DISABLED)
        self.filter_unlisted_button.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)

        self.filter_public_button = ttk.Button(load_filter_lf, text='Filter: Public', command=lambda: self.apply_filter_to_treeview("public"), state=tk.DISABLED)
        self.filter_public_button.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)


        # --- Treeview for videos ---
        tree_frame = ttk.Frame(frm)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.tree = ttk.Treeview(tree_frame, columns=('id', 'title', 'status', 'publish_at'), show='headings', selectmode="extended")
        self.tree.heading('id', text='Video ID')
        self.tree.heading('title', text='Current Title')
        self.tree.heading('status', text='Current Privacy')
        self.tree.heading('publish_at', text='Currently Scheduled At (UTC)')

        self.tree.column('id', width=120, stretch=tk.NO, anchor='w')
        self.tree.column('title', width=300, anchor='w')
        self.tree.column('status', width=100, stretch=tk.NO, anchor='w')
        self.tree.column('publish_at', width=180, anchor='w')
        
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)

        # --- Schedule & Interval Frame ---
        sched = ttk.LabelFrame(frm, text='Schedule & Interval', padding=10)
        sched.pack(fill=tk.X, pady=5)
        
        ttk.Label(sched, text='First Publish (YYYY-MM-DD HH:MM Local)').grid(row=0, column=0, sticky='w', pady=2)
        self.start_ent = ttk.Entry(sched, width=20)
        self.start_ent.insert(0, (datetime.now() + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M'))
        self.start_ent.grid(row=0, column=1, sticky='ew', padx=5, pady=2)
        
        ttk.Label(sched, text='Interval Hours:').grid(row=1, column=0, sticky='w', pady=2)
        self.interval_hour_var = tk.StringVar(value='1') 
        self.interval_hour_spin = ttk.Spinbox(sched, from_=0, to=1000, width=5, textvariable=self.interval_hour_var)
        self.interval_hour_spin.grid(row=1, column=1, sticky='w', padx=5, pady=2)
        
        ttk.Label(sched, text='Interval Minutes:').grid(row=2, column=0, sticky='w', pady=2)
        self.interval_minute_var = tk.StringVar(value='0')
        self.interval_minute_spin = ttk.Spinbox(sched, from_=0, to=59, width=5, textvariable=self.interval_minute_var)
        self.interval_minute_spin.grid(row=2, column=1, sticky='w', padx=5, pady=(2,5))
        sched.grid_columnconfigure(1, weight=1)

        # --- Metadata Defaults Frame ---
        meta = ttk.LabelFrame(frm, text='Metadata Defaults (Applied to ALL selected videos)', padding=10)
        meta.pack(fill=tk.X, pady=5)
        
        ttk.Label(meta, text='Title (leave empty to keep original):').grid(row=0, column=0, sticky='w', pady=2)
        self.title_ent = ttk.Entry(meta, width=40)
        self.title_ent.grid(row=0, column=1, sticky='ew', pady=2)

        ttk.Label(meta, text='Description (leave empty to keep original):').grid(row=1, column=0, sticky='nw', pady=2)
        self.desc_txt = tk.Text(meta, height=3, width=40)
        self.desc_txt.grid(row=1, column=1, sticky='ew', pady=2)
        
        ttk.Label(meta, text='Tags (comma-sep, replaces existing):').grid(row=2, column=0, sticky='w', pady=2)
        self.tags_ent = ttk.Entry(meta, width=40)
        self.tags_ent.grid(row=2, column=1, sticky='ew', pady=2)
        
        ttk.Label(meta, text='Category:').grid(row=3, column=0, sticky='w', pady=2)
        self.cat_cb = ttk.Combobox(meta, values=['(Keep Original)'] + list(CATEGORY_MAP.keys()), width=37, state="readonly")
        self.cat_cb.set('(Keep Original)')
        self.cat_cb.grid(row=3, column=1, sticky='ew', pady=2)
        
        self.made_for_kids_var_options = ['(Keep Original)', 'Yes', 'No']
        ttk.Label(meta, text='Made for Kids:').grid(row=4, column=0, sticky='w', pady=2)
        self.made_for_kids_cb = ttk.Combobox(meta, values=self.made_for_kids_var_options, width=37, state="readonly")
        self.made_for_kids_cb.set('(Keep Original)')
        self.made_for_kids_cb.grid(row=4, column=1, sticky='ew', pady=2)
        meta.grid_columnconfigure(1, weight=1)

        # --- Action Buttons & Log Option ---
        ttk.Checkbutton(frm, text='Save Log File on Exit', variable=self.save_log_var).pack(anchor='w', pady=5)
        ttk.Button(frm, text='SCHEDULE SELECTED VIDEOS', command=self.process_scheduling_gui, style="Accent.TButton")\
            .pack(pady=10, fill=tk.X, ipady=5)
        
        s = ttk.Style()
        s.configure("Accent.TButton", font=("Helvetica", 10, "bold"))

    def enable_video_management_buttons(self, enabled=True):
        state = tk.NORMAL if enabled else tk.DISABLED
        self.load_all_button.config(state=state) # This is the main load/refresh button
        # Filter buttons depend on self.all_channel_videos having content
        filter_state = tk.NORMAL if enabled and self.all_channel_videos else tk.DISABLED
        self.filter_all_button.config(state=filter_state)
        self.filter_private_button.config(state=filter_state)
        self.filter_unlisted_button.config(state=filter_state)
        self.filter_public_button.config(state=filter_state)

    def _populate_treeview(self, videos_to_display):
        """Helper function to populate the treeview with a given list of videos."""
        for item in self.tree.get_children():
            self.tree.delete(item)
        for vd in videos_to_display:
            publish_at_display = "Not Scheduled"
            current_publish_at = vd.current_status.get('publishAt')
            if current_publish_at:
                try:
                    dt_utc = datetime.fromisoformat(current_publish_at.replace('Z', '+00:00'))
                    publish_at_display = dt_utc.strftime('%Y-%m-%d %H:%M:%S UTC')
                except ValueError:
                    publish_at_display = current_publish_at 
            
            self.tree.insert('', tk.END, values=(
                vd.video_id, 
                vd.original_title, 
                vd.current_status.get('privacyStatus', 'N/A'),
                publish_at_display 
            ))

    def apply_filter_to_treeview(self, privacy_filter="all"):
        if not self.all_channel_videos:
            messagebox.showinfo("No Videos Loaded", "Please load videos from your channel first using 'Load All My Videos'.", parent=self.root)
            return

        logger.info(f"Applying filter: {privacy_filter}")
        self.current_filter_applied = privacy_filter
        
        if privacy_filter == "all":
            self._populate_treeview(self.all_channel_videos)
            return

        filtered_list = []
        for vd in self.all_channel_videos:
            if vd.current_status.get('privacyStatus') == privacy_filter:
                filtered_list.append(vd)
        
        self._populate_treeview(filtered_list)
        if not filtered_list:
            messagebox.showinfo("Filter Result", f"No videos found matching filter: '{privacy_filter}'.", parent=self.root)


    def select_credentials(self):
        path = filedialog.askopenfilename(title='Select client_secrets.json', filetypes=[('JSON files', '*.json')], parent=self.root)
        if path:
            self.client_secrets_path = path
            logger.info(f'Selected credentials: {path}')
            messagebox.showinfo("Credentials Set", f"Client secrets file set to:\n{path}", parent=self.root)
            try:
                self.service = get_authenticated_service(self.client_secrets_path)
                logger.info("Successfully authenticated with YouTube API after selecting credentials.")
                messagebox.showinfo("Authentication Success", "Successfully authenticated with YouTube.", parent=self.root)
                self.enable_video_management_buttons(True) # Enable main load button
            except Exception as e:
                logger.error(f"Failed to authenticate after selecting credentials: {e}")
                messagebox.showerror("Authentication Failed", f"Could not authenticate with YouTube: {e}", parent=self.root)
                self.service = None
                self.enable_video_management_buttons(False) # Keep all disabled

    def fetch_all_videos_from_api(self):
        if not self.service:
            logger.error("YouTube service not initialized. Authenticate first.")
            messagebox.showerror("Error", "Not authenticated.", parent=self.root)
            return []

        logger.info(f"Fetching all videos from channel using uploads playlist...")
        all_videos_data = []
        try:
            # 1. Get uploads playlist ID
            channel_response = self.service.channels().list(part="contentDetails", mine=True).execute()
            if not channel_response.get("items"):
                logger.error("Could not determine channel ID for uploads playlist.")
                messagebox.showerror("Error", "Could not determine your channel ID.", parent=self.root)
                return []
            
            uploads_playlist_id = channel_response["items"][0]["contentDetails"]["relatedPlaylists"].get("uploads")
            if not uploads_playlist_id:
                logger.error("Could not find uploads playlist ID for the channel.")
                messagebox.showerror("Error", "Could not find uploads playlist for your channel.", parent=self.root)
                return []
            logger.info(f"Found uploads playlist ID: {uploads_playlist_id}")

            # 2. Paginate through playlistItems
            next_page_token = None
            video_count = 0
            max_videos_to_scan = 1000 # Safety limit for very large channels
            
            while video_count < max_videos_to_scan:
                playlist_items_request = self.service.playlistItems().list(
                    playlistId=uploads_playlist_id,
                    part="snippet,status,contentDetails", # status needed for privacyStatus
                    maxResults=50,
                    pageToken=next_page_token
                )
                playlist_items_response = playlist_items_request.execute()

                for item in playlist_items_response.get("items", []):
                    video_count +=1
                    # Ensure it's a video and has necessary details
                    if item.get("snippet", {}).get("resourceId", {}).get("kind") == "youtube#video":
                        video_id = item["snippet"]["resourceId"]["videoId"]
                        snippet = item["snippet"]
                        status = item.get("status", {}) # Status might not be present for very new/processing videos
                        
                        # We still need to check uploadStatus from a videos.list call if not in playlistItem status
                        # However, playlistItem status *should* have privacyStatus.
                        # For simplicity here, we'll rely on playlistItem's status if available.
                        # A more robust solution might do a videos.list for uploadStatus if critical.

                        upload_status_ok = status.get("uploadStatus") in ["processed", "uploaded", "succeeded"]
                        # If uploadStatus is not directly available here, assume OK if privacyStatus is set,
                        # or consider an additional videos.list call for a batch of IDs later if needed.
                        # For now, let's assume playlistItem status is sufficient for filtering.
                        if not status.get("privacyStatus"): # If no privacy status, video might be weird (e.g. deleted after being in playlist)
                            logger.warning(f"Video ID {video_id} from playlist has no privacyStatus, skipping.")
                            continue
                        
                        # We will perform uploadStatus check more reliably after getting all video details
                        # For now, just grab everything from the playlist.

                        video_data_obj = VideoData(
                            video_id,
                            snippet.get("title", "No Title"),
                            snippet, # This is playlistItem snippet
                            status   # This is playlistItem status
                        )
                        all_videos_data.append(video_data_obj)
                
                next_page_token = playlist_items_response.get("nextPageToken")
                if not next_page_token:
                    break
                if video_count >= max_videos_to_scan:
                    logger.warning(f"Reached max scan limit of {max_videos_to_scan} videos from playlist.")
                    messagebox.showwarning("Scan Limit", f"Scanned the {max_videos_to_scan} most recent videos. "
                                                       "If you have more, not all may be loaded.", parent=self.root)
                    break
            
            logger.info(f"Total videos fetched from uploads playlist: {len(all_videos_data)}")
            if not all_videos_data:
                 messagebox.showinfo("No Videos Found", "No videos found in your channel's uploads playlist.", parent=self.root)

        except Exception as e:
            logger.error(f"Error fetching all videos from API: {e}")
            if "quotaExceeded" in str(e).lower():
                 messagebox.showerror("API Quota Error", f"Failed to fetch videos due to YouTube API quota limitations. Please try again later.\nDetails: {e}", parent=self.root)
            else:
                messagebox.showerror("API Error", f"Failed to fetch videos: {e}", parent=self.root)
            return [] # Return empty list on error
        return all_videos_data


    def gui_load_all_videos(self):
        if not self.client_secrets_path:
            messagebox.showerror('Error', 'No credentials JSON selected.', parent=self.root)
            return
        if not self.service:
            try: 
                self.service = get_authenticated_service(self.client_secrets_path)
                logger.info("Successfully authenticated with YouTube API.")
            except Exception as auth_ex:
                logger.error(f"Authentication failed: {auth_ex}")
                messagebox.showerror('Auth Error', f'Authentication failed: {auth_ex}', parent=self.root)
                self.service = None
                self.enable_video_management_buttons(False)
                return
        
        self.all_channel_videos = self.fetch_all_videos_from_api() 
        self.current_filter_applied = "all" # Reset filter to "all"
        self._populate_treeview(self.all_channel_videos) # Display all fetched videos
        
        if self.all_channel_videos:
            messagebox.showinfo("Videos Loaded", f"Successfully loaded {len(self.all_channel_videos)} videos from your channel.", parent=self.root)
        
        # Enable filter buttons regardless of whether videos were found, so user can see "No videos found" message if they filter.
        self.enable_video_management_buttons(True)


    def process_scheduling_gui(self):
        selected_items_indices = self.tree.selection()
        if not selected_items_indices:
            messagebox.showwarning("No Selection", "No videos selected from the list to schedule.", parent=self.root)
            return

        videos_to_schedule = []
        # Important: Get VideoData objects from self.all_channel_videos based on selected IDs in tree
        # because the tree might be showing a filtered list.
        selected_video_ids_in_tree = {self.tree.item(item_widget_id)['values'][0] for item_widget_id in selected_items_indices}

        for vd_obj in self.all_channel_videos:
            if vd_obj.video_id in selected_video_ids_in_tree:
                videos_to_schedule.append(vd_obj)
        
        if not videos_to_schedule:
            messagebox.showerror("Error", "Selected videos could not be fully matched. Try reloading the video list.", parent=self.root)
            return

        logger.info(f"Processing {len(videos_to_schedule)} selected videos for scheduling.")

        if not self.service: # Should ideally be available if videos are loaded
             try: self.service = get_authenticated_service(self.client_secrets_path)
             except Exception as e:
                logger.error(f"Authentication error during scheduling: {e}")
                messagebox.showerror("Auth Error", f"Authentication failed: {e}", parent=self.root)
                return

        # --- Get scheduling parameters from GUI ---
        new_title_base = self.title_ent.get().strip()
        new_desc_base = self.desc_txt.get('1.0','end-1c').strip()
        new_tags_list_base = sanitize_tags([t.strip() for t in self.tags_ent.get().split(',') if t.strip()])
        new_cat_choice = self.cat_cb.get()
        new_mfd_choice = self.made_for_kids_cb.get()

        try:
            start_time_str = self.start_ent.get()
            local_dt = datetime.strptime(start_time_str, '%Y-%m-%d %H:%M')
            try: local_tz = datetime.now().astimezone().tzinfo
            except AttributeError: 
                offset_seconds = -timezone.utc.utcoffset(datetime.now()).total_seconds() if timezone.utc.utcoffset(datetime.now()) else 0
                local_tz = timezone(timedelta(seconds=offset_seconds))
            start_utc_dt = local_dt.replace(tzinfo=local_tz).astimezone(timezone.utc)
            
            if start_utc_dt < datetime.now(timezone.utc) + timedelta(minutes=10): # Future buffer
                messagebox.showerror("Error", "The first publish time must be at least 10 minutes in the future.", parent=self.root)
                return
            logger.info(f"Scheduling first video at (UTC): {start_utc_dt.isoformat()}")
        except ValueError:
            logger.error(f"Invalid start date format: {start_time_str}")
            messagebox.showerror("Error", "Invalid 'First Publish' date/time. Use YYYY-MM-DD HH:MM.", parent=self.root)
            return

        try:
            interval_h = int(self.interval_hour_var.get())
            interval_m = int(self.interval_minute_var.get())
            interval_delta = timedelta(hours=interval_h, minutes=interval_m)
            min_interval = timedelta(minutes=15)
            if interval_delta < min_interval and len(videos_to_schedule) > 1 :
                 if not messagebox.askyesno("Warning: Short Interval", 
                                       f"The interval ({interval_h}h {interval_m}m) is less than 15 minutes. "
                                       "YouTube might have limitations. Continue?", parent=self.root):
                    return
            if interval_delta <= timedelta(0) and len(videos_to_schedule) > 1 : 
                interval_delta = min_interval
        except ValueError:
            logger.error("Invalid interval format.")
            messagebox.showerror("Error", "Interval hours/minutes must be numbers.", parent=self.root)
            return

        # --- Apply settings to selected VideoData objects ---
        current_publish_time = start_utc_dt
        for i, vd_obj in enumerate(videos_to_schedule):
            # Metadata
            if new_title_base: vd_obj.title_to_set = new_title_base
            else: vd_obj.title_to_set = vd_obj.original_title # Ensure it defaults back if field cleared

            if new_desc_base: vd_obj.description_to_set = new_desc_base
            else: vd_obj.description_to_set = vd_obj.current_snippet.get('description', '')

            if self.tags_ent.get().strip(): vd_obj.tags_to_set = new_tags_list_base
            else: vd_obj.tags_to_set = vd_obj.current_snippet.get('tags', [])
            
            if new_cat_choice != '(Keep Original)':
                vd_obj.categoryId_to_set = CATEGORY_MAP.get(new_cat_choice, vd_obj.categoryId_to_set)
            # else it keeps its original or default from VideoData init
            
            if new_mfd_choice != '(Keep Original)':
                vd_obj.madeForKids_to_set = True if new_mfd_choice == 'Yes' else False
            # else it keeps its original

            # Scheduling
            vd_obj.publishAt_to_set = current_publish_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            vd_obj.privacyStatus_to_set = 'private' # Ensure it's set to private for scheduling
            logger.info(f"Video '{vd_obj.original_title}' (ID: {vd_obj.video_id}) set to schedule for: {vd_obj.publishAt_to_set}")
            
            if i < len(videos_to_schedule) - 1:
                current_publish_time += interval_delta

        self.update_videos_on_youtube(videos_to_schedule)


    def update_videos_on_youtube(self, videos_to_update):
        if not self.service:
            messagebox.showerror("Error", "YouTube service not available.", parent=self.root)
            return

        total_videos = len(videos_to_update)
        logger.info(f"Starting to update {total_videos} videos on YouTube...")
        success_count, failure_count = 0, 0

        progress_win = tk.Toplevel(self.root)
        progress_win.title("Scheduling Progress")
        progress_win.geometry("450x120")
        progress_win.resizable(False, False)
        ttk.Label(progress_win, text="Scheduling videos...").pack(pady=5)
        progress_bar = ttk.Progressbar(progress_win, orient="horizontal", length=350, mode="determinate", maximum=total_videos)
        progress_bar.pack(pady=5)
        progress_label = ttk.Label(progress_win, text=f"0 of {total_videos} processed", wraplength=400)
        progress_label.pack(pady=5)
        progress_win.grab_set()

        for i, vd in enumerate(videos_to_update):
            progress_label.config(text=f"Processing {i+1}/{total_videos}: {vd.original_title[:50]}...")
            progress_win.update_idletasks()
            
            # Prepare snippet for update. Only include fields that are being set.
            snippet_body = {
                'title': vd.title_to_set, 
                'description': vd.description_to_set,
                'tags': vd.tags_to_set, 
                'categoryId': vd.categoryId_to_set
            }
            # Optional fields:
            if vd.defaultLanguage_to_set is not None: snippet_body['defaultLanguage'] = vd.defaultLanguage_to_set
            if vd.videoLanguage_to_set is not None: snippet_body['defaultAudioLanguage'] = vd.videoLanguage_to_set
            # Recording date needs careful handling: API expects ISO 8601 or null to clear
            if vd.recordingDate_to_set:
                 snippet_body['recordingDetails'] = {'recordingDate': vd.recordingDate_to_set}
            elif 'recordingDetails' in vd.current_snippet: # If it had one and now it's cleared
                 snippet_body['recordingDetails'] = None


            status_body = {
                'privacyStatus': vd.privacyStatus_to_set, # Should be 'private' for scheduling
                'publishAt': vd.publishAt_to_set,
                'selfDeclaredMadeForKids': vd.madeForKids_to_set,
                'embeddable': vd.embeddable_to_set 
            }
            video_update_body = {'id': vd.video_id, 'snippet': snippet_body, 'status': status_body}

            try:
                request = self.service.videos().update(part='snippet,status', body=video_update_body)
                response = request.execute()
                logger.info(f"Successfully updated ID: {response['id']}. Publish: {response['status'].get('publishAt', 'N/A')}")
                # Update local VideoData object's status (important if not re-fetching immediately)
                vd.current_status = response.get('status', vd.current_status)
                vd.current_snippet = response.get('snippet', vd.current_snippet) # Update snippet too
                success_count +=1
            except Exception as e:
                logger.error(f"Failed to update video ID {vd.video_id}: {e}")
                failure_count +=1
            
            progress_bar['value'] = i + 1
        progress_win.destroy()
        
        summary_message = f"Scheduling complete.\nSuccessfully scheduled: {success_count}\nFailed to schedule: {failure_count}"
        logger.info(summary_message)
        messagebox.showinfo("Scheduling Complete", summary_message, parent=self.root)

        # After scheduling, refresh the tree view with the current filter
        # This will reflect changes like `publishAt` being set.
        if success_count > 0 or failure_count > 0 :
             self.apply_filter_to_treeview(self.current_filter_applied)


    def on_exit(self):
        logger.info("Application exiting procedure started.")
        if self.save_log_var.get():
            try:
                with open(LOG_FILE, 'w', encoding='utf-8') as f:
                    f.write("\n".join(log_records))
                logger.info(f"Log saved to {LOG_FILE}")
            except Exception as e:
                logger.error(f"Failed to save log file: {e}")
        if self.root:
            try:
                self.root.destroy()
                logger.info("Tkinter root window destroyed.")
            except tk.TclError as e:
                logger.warning(f"Error destroying Tkinter root (possibly already destroyed): {e}")
        logger.info("Application exit procedure finished.")

if __name__ == '__main__':
    app = SchedulerApp()