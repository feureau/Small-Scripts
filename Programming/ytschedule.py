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
# MediaFileUpload is no longer needed as we are not uploading new files
# from googleapiclient.http import MediaFileUpload

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# --- Constants ---
SCOPES = [
    "https://www.googleapis.com/auth/youtube", # Comprehensive scope
    # "https://www.googleapis.com/auth/youtube.readonly", # Included in the above
    # "https://www.googleapis.com/auth/youtube.upload", # Kept if future might need it, but not for scheduling drafts
    "https://www.googleapis.com/auth/youtube.force-ssl" # Recommended for all YouTube API calls
]
TOKEN_FILE = "token.json"
LOG_FILE = "ytscheduler.log" # Renamed log file
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

# --- Token revocation (Kept as is - this is the correct server-side revocation) ---
def revoke_token():
    if os.path.exists(TOKEN_FILE):
        logger.info("Attempting to revoke token...")
        try:
            with open(TOKEN_FILE, 'r') as f:
                token_data = json.load(f)
            
            # Attempt to revoke the refresh token if present
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
            
            # Also attempt to revoke the access token if present and different
            # This is often not necessary if the refresh token is revoked, but can be an additional step.
            # For simplicity and standard practice, revoking the refresh token is the primary goal.
            # If 'token' field (access token) exists and is what google-auth might use for creds.revoke()
            # However, InstalledAppFlow primarily works with refresh tokens for long-term access.

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
        sys.exit(1) # Ensure exit after handling signal
    # Register for common termination signals
    if hasattr(signal, 'SIGINT'):
        signal.signal(signal.SIGINT, on_sig)
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, on_sig)
    # For Windows, SIGBREAK might be relevant if console is closed
    if hasattr(signal, 'SIGBREAK'): # Windows specific
        signal.signal(signal.SIGBREAK, on_sig)


# --- OAuth Authentication with retry and fallback (Kept as is) ---
def get_authenticated_service(secrets_path):
    from oauthlib.oauth2.rfc6749.errors import MismatchingStateError # Ensure this import is present
    creds = None
    if Path(TOKEN_FILE).exists():
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        except Exception as e:
            logger.warning(f"Failed to load token from file: {e}. Will attempt re-authentication.")
            creds = None # Ensure creds is None if loading fails

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("Refreshing expired credentials...")
            try:
                creds.refresh(Request())
            except Exception as e:
                logger.error(f"Failed to refresh credentials: {e}. Proceeding to full auth.")
                creds = None # Force re-authentication
        
        if not creds: # If still no valid creds, start new flow
            logger.info("No valid credentials found. Starting new OAuth flow.")
            if not secrets_path or not Path(secrets_path).exists():
                logger.error("Client secrets file path not provided or file does not exist.")
                raise FileNotFoundError("Client secrets file is required for new authentication.")
            
            flow = InstalledAppFlow.from_client_secrets_file(secrets_path, SCOPES)
            try:
                # Try local server first
                creds = flow.run_local_server(
                    port=OAUTH_PORT,
                    open_browser=True,
                    authorization_prompt_message="Please visit this URL:\n{url}",
                    success_message="Authentication successful! You can close this tab.",
                    timeout_seconds=300 
                )
            except MismatchingStateError as mse: 
                logger.warning(f"Mismatching state error during local server auth: {mse}. Falling back to console.")
                creds = flow.run_console()
            except Exception as e: 
                logger.warning(f"Local server auth failed (e.g. browser issue, timeout): {e}. Falling back to console.")
                creds = flow.run_console()
        
        with open(TOKEN_FILE, 'w') as f:
            f.write(creds.to_json())
        logger.info("Credentials saved to token.json")
    return build('youtube', 'v3', credentials=creds, cache_discovery=False) # cache_discovery=False can help with stale cache issues

# --- Helpers ---
def sanitize_filename(name): # May not be needed directly, but good to have
    stem = Path(name).stem
    s = re.sub(r"[^A-Za-z0-9 _-]+", "", stem) # Allow underscore and hyphen
    return re.sub(r"\s+", " ", s).strip()

def sanitize_description(desc: str) -> str:
    desc = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F]', '', desc) # remove control chars
    return desc[:4999] # YouTube description limit 5000

def sanitize_tags(raw_tags):
    clean = []
    current_length = 0
    for t in raw_tags:
        tag = str(t).strip() # Ensure it's a string
        if not tag:
            continue
        # Remove control characters and quotes that might break API
        tag = re.sub(r'[\x00-\x1F\x7F\"]', '', tag)
        # YouTube tags can contain spaces. Let's be a bit more permissive.
        # No need to aggressively remove all special chars, but let's limit length.
        tag = tag[:75] # Individual tag length limit is quite high, but total is 500.
        
        # Check total length (including commas for joining)
        if current_length + len(tag) + (1 if clean else 0) > 480: # Leave some buffer
            logger.warning(f"Tag '{tag}' truncated or skipped as total tag length exceeds limit.")
            break
        if tag: # Ensure tag is not empty after sanitization
            clean.append(tag)
            current_length += len(tag) + (1 if len(clean) > 1 else 0)
    return clean

# --- DraftVideo model ---
class DraftVideo:
    def __init__(self, video_id, title, current_snippet, current_status):
        self.video_id = video_id
        self.original_title = title
        self.current_snippet = current_snippet
        self.current_status = current_status

        # These will be populated by GUI defaults or current values
        self.title_to_set = title
        self.description_to_set = current_snippet.get('description', '')
        self.tags_to_set = current_snippet.get('tags', [])
        self.categoryId_to_set = current_snippet.get('categoryId', CATEGORY_MAP['Entertainment'])
        self.videoLanguage_to_set = current_snippet.get('defaultAudioLanguage') # Keep None if not set
        self.defaultLanguage_to_set = current_snippet.get('defaultLanguage')   # Keep None if not set
        self.recordingDate_to_set = (current_snippet.get('recordingDetails') or {}).get('recordingDate')
        
        self.notifySubscribers_to_set = True 
        self.madeForKids_to_set = current_status.get('selfDeclaredMadeForKids', False)
        self.embeddable_to_set = current_status.get('embeddable', True)
        self.publicStatsViewable_to_set = current_status.get('publicStatsViewable', True)
        
        self.playlistId_to_set = '' 
        self.publishAt_to_set = None 
        self.privacyStatus_to_set = 'private' 

    def __str__(self):
        return f"ID: {self.video_id}, Title: {self.original_title}, PublishAt: {self.publishAt_to_set}"


# --- Main GUI app ---
class SchedulerApp:
    def __init__(self):
        self.client_secrets_path = None
        self.service = None
        self.draft_videos = [] 

        try:
            if os.path.exists(LOG_FILE): os.remove(LOG_FILE)
        except Exception as e:
            logger.warning(f"Could not remove old log file: {e}")
        
        self.root = tk.Tk()
        # Call setup_revocation_on_exit after root is initialized, if it depends on root
        # However, it's better if setup_revocation_on_exit is independent of GUI elements
        setup_revocation_on_exit() # Call it here

        self.save_log_var = tk.BooleanVar(master=self.root, value=True)
        self.root.title('YouTube Draft Scheduler')
        self.build_gui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_exit)
        self.root.mainloop()

    def build_gui(self):
        frm = ttk.Frame(self.root, padding=10)
        frm.pack(fill=tk.BOTH, expand=True)

        top_frm = ttk.Frame(frm)
        top_frm.pack(fill=tk.X, pady=(0,10))
        ttk.Button(top_frm, text='Select Credentials JSON', command=self.select_credentials)\
            .pack(side=tk.LEFT, padx=(0,10))
        ttk.Button(top_frm, text='Load Draft Videos', command=self.load_draft_videos_gui)\
            .pack(side=tk.LEFT)

        self.tree = ttk.Treeview(frm, columns=('id', 'title', 'status'), show='headings', selectmode="extended")
        self.tree.heading('id', text='Video ID')
        self.tree.heading('title', text='Current Title')
        self.tree.heading('status', text='Current Privacy')
        self.tree.column('id', width=120, stretch=tk.NO, anchor='w')
        self.tree.column('title', width=300, anchor='w')
        self.tree.column('status', width=100, stretch=tk.NO, anchor='w')
        
        vsb = ttk.Scrollbar(frm, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(frm, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=5)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)


        sched = ttk.LabelFrame(frm, text='Schedule & Interval', padding=10)
        sched.pack(fill=tk.X, pady=5, after=self.tree) # Ensure it's packed after tree and scrollbars
        
        ttk.Label(sched, text='First Publish (YYYY-MM-DD HH:MM Local)').grid(row=0, column=0, sticky='w', pady=2)
        self.start_ent = ttk.Entry(sched, width=20)
        self.start_ent.insert(0, (datetime.now() + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M'))
        self.start_ent.grid(row=0, column=1, sticky='w', padx=5, pady=2)
        
        ttk.Label(sched, text='Interval Hours:').grid(row=1, column=0, sticky='w', pady=2)
        self.interval_hour_var = tk.StringVar(value='24') 
        self.interval_hour_spin = ttk.Spinbox(sched, from_=0, to=1000, width=5, textvariable=self.interval_hour_var)
        self.interval_hour_spin.grid(row=1, column=1, sticky='w', padx=5, pady=2)
        
        ttk.Label(sched, text='Interval Minutes:').grid(row=2, column=0, sticky='w', pady=2)
        self.interval_minute_var = tk.StringVar(value='0')
        self.interval_minute_spin = ttk.Spinbox(sched, from_=0, to=59, width=5, textvariable=self.interval_minute_var)
        self.interval_minute_spin.grid(row=2, column=1, sticky='w', padx=5, pady=(2,5))

        meta = ttk.LabelFrame(frm, text='Metadata Defaults (Applied to ALL selected drafts)', padding=10)
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
        self.cat_cb = ttk.Combobox(meta, values=['(Keep Original)'] + list(CATEGORY_MAP.keys()), width=37)
        self.cat_cb.set('(Keep Original)')
        self.cat_cb.grid(row=3, column=1, sticky='ew', pady=2)

        self.notify_var = tk.BooleanVar(value=True) # This is for videos.insert, publishAt handles it for updates
        # ttk.Checkbutton(meta, text='Notify Subscribers (when video goes live)', variable=self.notify_var).grid(row=4, column=0, columnspan=2, sticky='w', pady=2)
        
        self.made_for_kids_var_options = ['(Keep Original)', 'Yes', 'No']
        ttk.Label(meta, text='Made for Kids:').grid(row=5, column=0, sticky='w', pady=2)
        self.made_for_kids_cb = ttk.Combobox(meta, values=self.made_for_kids_var_options, width=37)
        self.made_for_kids_cb.set('(Keep Original)')
        self.made_for_kids_cb.grid(row=5, column=1, sticky='ew', pady=2)

        ttk.Checkbutton(frm, text='Save Log File on Exit', variable=self.save_log_var).pack(anchor='w', pady=5)
        ttk.Button(frm, text='SCHEDULE SELECTED DRAFTS', command=self.process_scheduling_gui, style="Accent.TButton")\
            .pack(pady=10, fill=tk.X, ipady=5)
        
        s = ttk.Style()
        s.configure("Accent.TButton", font=("Helvetica", 10, "bold")) # Removed background for better cross-platform look


    def refresh_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for dv in self.draft_videos:
            self.tree.insert('', tk.END, values=(dv.video_id, dv.original_title, dv.current_status.get('privacyStatus', 'N/A')))

    def select_credentials(self):
        path = filedialog.askopenfilename(title='Select client_secrets.json', filetypes=[('JSON files', '*.json')])
        if path:
            self.client_secrets_path = path
            logger.info(f'Selected credentials: {path}')
            messagebox.showinfo("Credentials Set", f"Client secrets file set to:\n{path}", parent=self.root)
            try:
                self.service = get_authenticated_service(self.client_secrets_path)
                logger.info("Successfully authenticated with YouTube API after selecting credentials.")
                messagebox.showinfo("Authentication Success", "Successfully authenticated with YouTube.", parent=self.root)
            except Exception as e:
                logger.error(f"Failed to authenticate after selecting credentials: {e}")
                messagebox.showerror("Authentication Failed", f"Could not authenticate with YouTube: {e}", parent=self.root)
                self.service = None


    def fetch_draft_videos_from_api(self):
        if not self.service:
            logger.error("YouTube service not initialized. Authenticate first.")
            messagebox.showerror("Error", "Not authenticated. Select credentials and ensure authentication is successful.", parent=self.root)
            return []

        logger.info("Fetching draft videos from channel...")
        found_drafts = []
        try:
            channel_response = self.service.channels().list(part="id", mine=True).execute()
            if not channel_response.get("items"):
                logger.error("Could not determine channel ID.")
                messagebox.showerror("Error", "Could not determine your channel ID.", parent=self.root)
                return []
            channel_id = channel_response["items"][0]["id"]
            logger.info(f"Operating on channel ID: {channel_id}")

            video_ids = []
            next_page_token = None
            page_count = 0
            max_pages = 10 # Safety break: max 10 pages * 50 results = 500 videos
            while page_count < max_pages:
                page_count += 1
                search_request = self.service.search().list(
                    part="id", channelId=channel_id, type="video",
                    order="date", maxResults=50, pageToken=next_page_token
                )
                search_response = search_request.execute()
                
                for item in search_response.get("items", []):
                    video_ids.append(item["id"]["videoId"])
                
                next_page_token = search_response.get("nextPageToken")
                if not next_page_token: break
            logger.info(f"Found {len(video_ids)} video IDs in channel (scanned up to {max_pages*50} videos). Fetching details...")

            for i in range(0, len(video_ids), 50):
                chunk_ids = video_ids[i:i+50]
                if not chunk_ids: continue

                videos_request = self.service.videos().list(part="snippet,status", id=",".join(chunk_ids))
                videos_response = videos_request.execute()

                for video_item in videos_response.get("items", []):
                    status = video_item.get("status", {})
                    snippet = video_item.get("snippet", {})
                    
                    is_private = status.get("privacyStatus") == "private"
                    has_publish_at = status.get("publishAt") is not None # Any publishAt means it's scheduled or past
                    upload_status_ok = status.get("uploadStatus") in ["processed", "uploaded", "succeeded"]
                    
                    if is_private and not has_publish_at and upload_status_ok:
                        draft = DraftVideo(video_item["id"], snippet.get("title", "No Title"), snippet, status)
                        found_drafts.append(draft)
                        logger.info(f"Found draft: ID={draft.video_id}, Title='{draft.original_title}'")
            
            logger.info(f"Total drafts matching criteria: {len(found_drafts)}")
            if not found_drafts:
                messagebox.showinfo("No Drafts", "No videos matching draft criteria (private, processed/uploaded, not scheduled) were found.", parent=self.root)

        except Exception as e:
            logger.error(f"Error fetching draft videos: {e}")
            messagebox.showerror("API Error", f"Failed to fetch draft videos: {e}", parent=self.root)
            return []
        return found_drafts

    def load_draft_videos_gui(self):
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
                return
        
        self.draft_videos = self.fetch_draft_videos_from_api()
        self.refresh_tree()
        if self.draft_videos:
            messagebox.showinfo("Drafts Loaded", f"Loaded {len(self.draft_videos)} videos matching draft criteria from your channel.", parent=self.root)

    def process_scheduling_gui(self):
        selected_items_indices = self.tree.selection()
        if not selected_items_indices:
            messagebox.showwarning("No Selection", "No videos selected from the list to schedule.", parent=self.root)
            return

        videos_to_schedule = []
        for item_widget_id in selected_items_indices:
            video_id_in_tree = self.tree.item(item_widget_id)['values'][0]
            for dv in self.draft_videos:
                if dv.video_id == video_id_in_tree:
                    videos_to_schedule.append(dv)
                    break
        
        if not videos_to_schedule:
            messagebox.showerror("Error", "Selected videos not found in the internal list. Try reloading drafts.", parent=self.root)
            return

        logger.info(f"Processing {len(videos_to_schedule)} selected draft videos for scheduling.")

        if not self.service:
             try: self.service = get_authenticated_service(self.client_secrets_path)
             except Exception as e:
                logger.error(f"Authentication error during scheduling: {e}")
                messagebox.showerror("Auth Error", f"Authentication failed: {e}", parent=self.root)
                return

        # GUI values for metadata
        new_title_base = self.title_ent.get().strip()
        new_desc_base = self.desc_txt.get('1.0','end-1c').strip()
        new_tags_list_base = sanitize_tags([t.strip() for t in self.tags_ent.get().split(',') if t.strip()])
        new_cat_choice = self.cat_cb.get()
        new_mfd_choice = self.made_for_kids_cb.get()

        try:
            start_time_str = self.start_ent.get()
            local_dt = datetime.strptime(start_time_str, '%Y-%m-%d %H:%M')
            local_tz = datetime.now().astimezone().tzinfo
            start_utc_dt = local_dt.replace(tzinfo=local_tz).astimezone(timezone.utc)
            logger.info(f"Scheduling first video at (UTC): {start_utc_dt.isoformat()}")
        except ValueError:
            logger.error(f"Invalid start date format: {start_time_str}")
            messagebox.showerror("Error", "Invalid 'First Publish' date/time. Use YYYY-MM-DD HH:MM.", parent=self.root)
            return

        try:
            interval_h = int(self.interval_hour_var.get())
            interval_m = int(self.interval_minute_var.get())
            interval_delta = timedelta(hours=interval_h, minutes=interval_m)
            if interval_delta <= timedelta(seconds=59*60): # YouTube minimum is 1 hour between scheduled uploads if many
                 if not messagebox.askyesno("Warning: Short Interval", 
                                       f"The interval ({interval_h}h {interval_m}m) is less than 1 hour. "
                                       "YouTube might have limitations on very frequent scheduling. Continue?", parent=self.root):
                    return
            if interval_delta <= timedelta(0): interval_delta = timedelta(hours=1) # Default to 1 hour if non-positive
        except ValueError:
            logger.error("Invalid interval format.")
            messagebox.showerror("Error", "Interval hours/minutes must be numbers.", parent=self.root)
            return

        current_publish_time = start_utc_dt
        for i, dv_obj in enumerate(videos_to_schedule):
            if new_title_base: dv_obj.title_to_set = new_title_base
            if new_desc_base: dv_obj.description_to_set = new_desc_base
            if new_tags_list_base: dv_obj.tags_to_set = new_tags_list_base # Replaces existing tags

            if new_cat_choice != '(Keep Original)':
                dv_obj.categoryId_to_set = CATEGORY_MAP.get(new_cat_choice, dv_obj.categoryId_to_set)
            
            if new_mfd_choice != '(Keep Original)':
                dv_obj.madeForKids_to_set = True if new_mfd_choice == 'Yes' else False
            
            dv_obj.publishAt_to_set = current_publish_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            logger.info(f"Video '{dv_obj.original_title}' (ID: {dv_obj.video_id}) set to schedule for: {dv_obj.publishAt_to_set}")
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
        ttk.Label(progress_win, text="Scheduling videos...").pack(pady=5)
        progress_bar = ttk.Progressbar(progress_win, orient="horizontal", length=350, mode="determinate", maximum=total_videos)
        progress_bar.pack(pady=5)
        progress_label = ttk.Label(progress_win, text=f"0 of {total_videos} scheduled", wraplength=400)
        progress_label.pack(pady=5)
        progress_win.grab_set()

        for i, dv in enumerate(videos_to_update):
            current_video_log = f"Updating ID: {dv.video_id}, Title: {dv.original_title}, New PublishAt: {dv.publishAt_to_set}"
            logger.info(current_video_log)
            progress_label.config(text=f"Processing {i+1}/{total_videos}: {dv.original_title[:50]}...")
            progress_win.update_idletasks()
            
            snippet_body = {'title': dv.title_to_set, 'description': dv.description_to_set,
                            'tags': dv.tags_to_set, 'categoryId': dv.categoryId_to_set}
            # Remove None values to avoid issues if a language was not set
            if dv.defaultLanguage_to_set: snippet_body['defaultLanguage'] = dv.defaultLanguage_to_set
            if dv.videoLanguage_to_set: snippet_body['defaultAudioLanguage'] = dv.videoLanguage_to_set
            if dv.recordingDate_to_set: snippet_body['recordingDetails'] = {'recordingDate': dv.recordingDate_to_set}


            status_body = {'privacyStatus': 'private', 'publishAt': dv.publishAt_to_set,
                           'selfDeclaredMadeForKids': dv.madeForKids_to_set,
                           'embeddable': dv.embeddable_to_set}

            video_update_body = {'id': dv.video_id, 'snippet': snippet_body, 'status': status_body}

            try:
                request = self.service.videos().update(part='snippet,status', body=video_update_body)
                response = request.execute()
                logger.info(f"Successfully updated ID: {response['id']}. Publish: {response['status'].get('publishAt', 'N/A')}")
                success_count +=1
            except Exception as e:
                logger.error(f"Failed to update video ID {dv.video_id}: {e}")
                failure_count +=1
            
            progress_bar['value'] = i + 1
            # progress_label.config(text=f"{i+1} of {total_videos} processed. Success: {success_count}, Failed: {failure_count}")
            # progress_win.update_idletasks()

        progress_win.destroy()
        
        summary_message = f"Scheduling complete.\nSuccessfully scheduled: {success_count}\nFailed to schedule: {failure_count}"
        logger.info(summary_message)
        messagebox.showinfo("Scheduling Complete", summary_message, parent=self.root)

        if success_count > 0 or failure_count > 0 : # Reload drafts if any change was attempted
             self.load_draft_videos_gui()


    def on_exit(self):
        logger.info("Application exiting procedure started.")
        # Token revocation is handled by atexit hook `setup_revocation_on_exit`
        # which was registered in __init__

        if self.save_log_var.get():
            try:
                with open(LOG_FILE, 'w', encoding='utf-8') as f:
                    f.write("\n".join(log_records))
                logger.info(f"Log saved to {LOG_FILE}")
            except Exception as e:
                logger.error(f"Failed to save log file: {e}")
        
        # Ensure atexit functions are called before tk is fully gone
        # No explicit call to revoke_token() here as atexit handles it.
        if self.root:
            try:
                self.root.destroy()
                logger.info("Tkinter root window destroyed.")
            except tk.TclError as e:
                logger.warning(f"Error destroying Tkinter root (possibly already destroyed): {e}")
        
        logger.info("Application exit procedure finished.")
        # sys.exit(0) # atexit handles cleanup, explicit sys.exit might be redundant or interfere


if __name__ == '__main__':
    # Ensure any previous atexit handlers are cleared if script is re-run in some environments
    # For simple script run, this is not strictly necessary.
    # atexit._clear() # Use with caution, might affect other parts of an embedded system.

    app = SchedulerApp()
    # The mainloop is started in SchedulerApp __init__
    # The on_exit method is bound to WM_DELETE_WINDOW