import os
import sys
import json
import signal
import atexit
import re # Already present, needed for sanitization
import logging
from pathlib import Path
from datetime import datetime, timedelta, timezone
import requests # Keep for token revocation
import httplib2 # For API call timeouts, and used by google-api-client
import time # For timezone fallback

from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from oauthlib.oauth2.rfc6749.errors import MismatchingStateError

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

# --- Constants ---
SCOPES = [
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.force-ssl"
]
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

# --- Helper functions for sanitization (Integrated from ytupload.py logic) ---
def sanitize_description(desc: str) -> str:
    """
    Sanitizes the video description.
    - Removes most control characters.
    - Truncates to 5000 characters (YouTube limit).
    """
    if not desc:
        return ""
    # remove control chars (ASCII 0-8, 11-12, 14-31, and 127)
    # \x09 (tab), \x0A (LF), \x0D (CR) are generally okay in descriptions.
    sanitized_desc = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', desc)
    return sanitized_desc[:5000]

def sanitize_tags(raw_tags_list: list) -> list:
    """
    Sanitizes a list of video tags.
    - Strips whitespace from each tag.
    - Removes control characters.
    - Whitelists alphanumeric characters and spaces.
    - Limits individual tags to a reasonable length (e.g., 60 chars).
    - Ensures the total length of all tags (sum of individual tag lengths) does not exceed 500 characters.
    """
    clean_tags = []
    current_total_length = 0
    # YouTube recommends tags be under 30 chars, but no hard limit per tag, only total.
    # Using a practical per-tag cap for sanitization.
    PER_TAG_CHAR_LIMIT = 60
    TOTAL_TAGS_CHAR_LIMIT = 500

    for t in raw_tags_list:
        tag = t.strip()
        if not tag:
            continue

        # Remove control characters (ASCII 0-31 and 127)
        tag = re.sub(r'[\x00-\x1F\x7F]', '', tag)
        
        # Whitelist alphanumeric and space.
        tag = re.sub(r'[^A-Za-z0-9 ]+', '', tag).strip() # Strip again in case non-alnum chars were at ends

        # Apply a practical per-tag length limit
        tag = tag[:PER_TAG_CHAR_LIMIT]

        if not tag: # If tag became empty after sanitization
            continue

        # Check if adding this tag would exceed the total character limit
        if current_total_length + len(tag) <= TOTAL_TAGS_CHAR_LIMIT:
            clean_tags.append(tag)
            current_total_length += len(tag)
        else:
            # If adding this tag exceeds the limit, stop adding more tags.
            # Ensure logger is defined if this function is used elsewhere.
            # For this script, 'logger' will be defined in the global scope.
            if 'logger' in globals() and hasattr(logger, 'warning'):
                 logger.warning(f"Tag '{tag}' (and subsequent tags) omitted as total tag character limit ({TOTAL_TAGS_CHAR_LIMIT}) would be exceeded.")
            else: # Fallback if logger not available
                print(f"[WARNING] Tag '{tag}' (and subsequent tags) omitted as total tag character limit ({TOTAL_TAGS_CHAR_LIMIT}) would be exceeded.")
            break
            
    return clean_tags

# --- Logger ---
logger = logging.getLogger("ytscheduler")
logger.setLevel(logging.INFO) # Set to DEBUG to see detailed API responses

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO) # Match logger level or set explicitly
console_handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S"))
if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
    logger.addHandler(console_handler)

file_log_handler_global = None

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
                    headers={'content-type': 'application/x-www-form-urlencoded'},
                    timeout=10
                )
                if response.status_code == 200:
                    logger.info(f"Refresh token revoked successfully (token: ...{token_data['refresh_token'][-6:]}).")
                else:
                    logger.warning(f"Failed to revoke refresh token. Status: {response.status_code}, Response: {response.text}")
            else:
                logger.info("No refresh_token found to revoke from server.")
        except FileNotFoundError: logger.info("Token file not found for revocation.")
        except requests.exceptions.RequestException as e: logger.error(f"Network error during token revocation: {e}")
        except Exception as e: logger.error(f"Error during token data or server-side revocation: {e}", exc_info=True)
        finally:
            try:
                if os.path.exists(TOKEN_FILE):
                    os.remove(TOKEN_FILE)
                    logger.info(f"Local token file '{TOKEN_FILE}' deleted.")
            except OSError as e: logger.error(f"Error deleting local token file '{TOKEN_FILE}': {e}", exc_info=True)
    else: logger.info("No local token file to revoke or delete.")

def setup_revocation_on_exit():
    atexit.register(revoke_token)
    def on_sig(signum, frame):
        signal_name = signal.Signals(signum).name if hasattr(signal, 'Signals') and isinstance(signum, signal.Signals) else signum
        logger.info(f"Signal {signal_name} received, attempting token revocation before exit.")
        sys.exit(1)
    if hasattr(signal, 'SIGINT'): signal.signal(signal.SIGINT, on_sig)
    if hasattr(signal, 'SIGTERM'): signal.signal(signal.SIGTERM, on_sig)
    if os.name == 'nt' and hasattr(signal, 'SIGBREAK'): signal.signal(signal.SIGBREAK, on_sig)

# --- OAuth Authentication ---
def get_authenticated_service(secrets_path, app_root_window=None):
    creds = None
    if Path(TOKEN_FILE).exists():
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
            logger.info("Loaded credentials from token.json")
        except Exception as e:
            logger.warning(f"Failed to load token: {e}. Re-authenticating.", exc_info=True)
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("Refreshing expired credentials...")
            try:
                creds.refresh(Request(timeout=API_TIMEOUT_SECONDS))
                logger.info("Credentials refreshed.")
            except Exception as e:
                logger.error(f"Failed to refresh: {e}. Full auth.", exc_info=True)
                creds = None
        if not creds:
            logger.info("No valid creds. Starting OAuth flow.")
            if not secrets_path or not Path(secrets_path).exists():
                err_msg = "Client secrets file missing."
                logger.error(err_msg)
                if app_root_window and app_root_window.winfo_exists():
                    messagebox.showerror("Auth Error", err_msg, parent=app_root_window)
                raise FileNotFoundError(err_msg)

            # Attempt 1: Local server with automatic browser opening
            flow_attempt1 = InstalledAppFlow.from_client_secrets_file(secrets_path, SCOPES)
            try:
                logger.info(f"Attempt 1: Auth via local server (port={OAUTH_PORT}, auto browser)...")
                creds = flow_attempt1.run_local_server(
                    port=OAUTH_PORT, open_browser=True,
                    authorization_prompt_message="Awaiting auth in browser...\nIf it doesn't open, copy URL from console: {url}",
                    success_message="Auth successful! You can close this tab.",
                    timeout_seconds=900
                )
                logger.info("Attempt 1: Auth successful.")
            except (MismatchingStateError, TimeoutError, ConnectionRefusedError) as e_specific_attempt1:
                 logger.error(f"Attempt 1: Local server auth (auto browser) failed with {type(e_specific_attempt1).__name__}: {e_specific_attempt1}.", exc_info=True)
            except Exception as e_local_server_auto: # Catch other unexpected errors
                logger.error(f"Attempt 1: Local server auth (auto browser) failed. Type: {type(e_local_server_auto).__name__}, Error: {e_local_server_auto}.", exc_info=True)

            if not (creds and creds.valid):
                logger.info("Attempt 1 failed. Trying Attempt 2 (manual browser, local server)...")
                flow_attempt2 = InstalledAppFlow.from_client_secrets_file(secrets_path, SCOPES)
                try:
                    auth_url_manual_server, _ = flow_attempt2.authorization_url()
                    instructions = (
                        "AUTHENTICATION REQUIRED (Attempt 2 of 3):\n\n"
                        "The application will now start a local server and wait for you to authorize.\n\n"
                        f"1. Please copy the URL below and paste it into your web browser:\n\n{auth_url_manual_server}\n\n"
                        "2. Authorize the application in your browser.\n\n"
                        "3. After authorization, your browser will attempt to redirect to the local server. "
                        "The application should then complete the process automatically.\n\n"
                        "Click 'OK' to start the local server and proceed with the steps above."
                    )
                    parent_win = app_root_window if app_root_window and app_root_window.winfo_exists() else None
                    if parent_win: messagebox.showinfo("Manual Auth - Local Server", instructions, parent=parent_win)
                    else: print(instructions.replace("\n\n", "\n"))
                    
                    creds = flow_attempt2.run_local_server(port=OAUTH_PORT, open_browser=False, timeout_seconds=900, success_message="Auth successful! You can close this tab.")
                    logger.info("Attempt 2: Auth successful.")
                except (MismatchingStateError, TimeoutError, ConnectionRefusedError) as e_specific_attempt2:
                    logger.error(f"Attempt 2: Local server auth (manual browser) failed with {type(e_specific_attempt2).__name__}: {e_specific_attempt2}.", exc_info=True)
                except Exception as e_local_server_manual:
                    logger.error(f"Attempt 2: Local server auth (manual browser) failed. Type: {type(e_local_server_manual).__name__}, Error: {e_local_server_manual}.", exc_info=True)

            if not (creds and creds.valid):
                logger.info("Attempts 1 & 2 failed. Trying Attempt 3 (fully manual code)...")
                flow_attempt3 = InstalledAppFlow.from_client_secrets_file(secrets_path, SCOPES)
                try:
                    auth_url_fully_manual, _ = flow_attempt3.authorization_url()
                    port_msg = 'A_DYNAMIC_PORT' if OAUTH_PORT == 0 else OAUTH_PORT
                    instructions_part1 = (
                        "AUTHENTICATION REQUIRED (Attempt 3 of 3 - Fully Manual):\n\n"
                        "STEP 1: Authorize in Browser\n"
                        f"1. Please open this URL in your browser:\n\n{auth_url_fully_manual}\n\n"
                        "2. Authorize the application.\n\n"
                        "3. Your browser will be redirected to a URL. The address bar will show something like:\n"
                        f"   'http://localhost:{port_msg}/?code=AUTH_CODE_HERE&state=...'\n"
                        f"   (The port will be dynamically assigned if OAUTH_PORT is 0, otherwise it's {OAUTH_PORT})\n\n"
                        "4. From that redirected URL, carefully copy THE ENTIRE 'code' VALUE.\n\n"
                        "Click 'OK' here ONLY AFTER you have COPIED the authorization code."
                    )
                    auth_dialog_parent = app_root_window if app_root_window and app_root_window.winfo_exists() else None
                    if auth_dialog_parent: messagebox.showinfo("Manual Auth - Step 1", instructions_part1, parent=auth_dialog_parent)
                    else:
                        print(instructions_part1.replace("\n\n", "\n"))
                        input("Press Enter after copying the code...")
                    
                    auth_code = simpledialog.askstring("Manual Auth - Step 2", "Paste the 'code' copied from browser:", parent=auth_dialog_parent)

                    if auth_code and auth_code.strip():
                        flow_attempt3.fetch_token(code=auth_code.strip())
                        creds = flow_attempt3.credentials
                        logger.info("Attempt 3: Auth successful.")
                    else:
                        raise Exception("Manual auth failed: Empty or no code entered.")
                except Exception as e_fetch_token:
                    final_error_msg = f"Attempt 3: Manual code exchange failed: {e_fetch_token}"
                    logger.error(final_error_msg, exc_info=True)
                    parent_for_err = app_root_window if app_root_window and app_root_window.winfo_exists() else None
                    if "cancelled" not in str(e_fetch_token).lower() and "empty code" not in str(e_fetch_token).lower():
                        if parent_for_err: messagebox.showerror("Auth Failed", final_error_msg, parent=parent_for_err)
                        else: print(f"ERROR: {final_error_msg}")
                    raise Exception(f"All auth methods failed. Last error: {e_fetch_token}") from e_fetch_token
            
            if creds and creds.valid:
                with open(TOKEN_FILE, 'w') as f: f.write(creds.to_json())
                logger.info(f"Credentials obtained and saved to {TOKEN_FILE}")
            else:
                raise Exception("Failed to obtain valid credentials after all attempts.")
                
    if creds and creds.valid:
        return build('youtube', 'v3', credentials=creds, cache_discovery=False)
    else:
        raise Exception("Failed to build YouTube service: No valid credentials.")

# --- VideoData model ---
class VideoData:
    def __init__(self, video_id, video_title, video_snippet, video_status, video_content_details=None, video_recording_details=None):
        self.video_id = video_id
        self.original_title = video_title # This is the title from video.snippet.title
        
        # Data from videos().list response
        self.video_snippet = video_snippet if video_snippet else {}
        self.video_status = video_status if video_status else {}
        self.video_content_details = video_content_details if video_content_details else {}
        self.video_recording_details = video_recording_details if video_recording_details else {}

        # --- MODIFICATION: Add attribute to track the source of the description ---
        self.description_source_file = "None" # Default if no .txt file is found

        # Fields to be set for update, initialized from the comprehensive video details
        self.title_to_set = self.video_snippet.get('title', self.original_title)
        self.description_to_set = self.video_snippet.get('description', '')
        self.tags_to_set = self.video_snippet.get('tags', [])
        self.categoryId_to_set = self.video_snippet.get('categoryId', CATEGORY_MAP['Entertainment'])
        self.videoLanguage_to_set = self.video_snippet.get('defaultAudioLanguage')
        self.defaultLanguage_to_set = self.video_snippet.get('defaultLanguage')
        self.recordingDate_to_set = self.video_recording_details.get('recordingDate')
        
        self.madeForKids_to_set = self.video_status.get('selfDeclaredMadeForKids', False)
        self.embeddable_to_set = self.video_status.get('embeddable', True)
        self.publicStatsViewable_to_set = self.video_status.get('publicStatsViewable', True)
        
        # For new scheduling action
        self.publishAt_to_set_new = None 
        self.privacyStatus_to_set = self.video_status.get('privacyStatus', 'private')

    def __str__(self):
        current_pub_at = self.video_status.get('publishAt', 'Not Set')
        return f"ID: {self.video_id}, Title: {self.title_to_set}, ActualPublishAt: {current_pub_at}, ActualPrivacy: {self.video_status.get('privacyStatus')}"

# --- Main GUI app ---
class SchedulerApp:
    def __init__(self):
        self.client_secrets_path = None; self.service = None
        self.all_channel_videos = []; self.current_filter_applied = "all"

        global file_log_handler_global
        try:
            if os.path.exists(LOG_FILE): os.remove(LOG_FILE)
            file_log_handler_global = logging.FileHandler(LOG_FILE, encoding='utf-8')
            file_log_handler_global.setLevel(logger.level)
            file_log_handler_global.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S"))
            logger.addHandler(file_log_handler_global)
            logger.info("Application started and file logger initialized.")
        except Exception as e:
            logger.warning(f"Could not set up log file '{LOG_FILE}': {e}", exc_info=True)
            file_log_handler_global = None

        self.root = tk.Tk(); setup_revocation_on_exit()
        self.save_log_var = tk.BooleanVar(master=self.root, value=False)
        self.root.title('YouTube Video Scheduler'); self.build_gui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_exit); self.root.mainloop()

    def build_gui(self):
        frm = ttk.Frame(self.root, padding=10); frm.pack(fill=tk.BOTH, expand=True)
        cred_frm = ttk.LabelFrame(frm, text="Authentication", padding=5); cred_frm.pack(fill=tk.X, pady=(0,5))
        self.select_cred_button = ttk.Button(cred_frm, text='Select client_secrets.json & Authenticate', command=self.select_credentials_and_auth)
        self.select_cred_button.pack(side=tk.LEFT, padx=(0,10), fill=tk.X, expand=True)
        self.auth_status_label = ttk.Label(cred_frm, text="Status: Not Authenticated", foreground="red", width=35, anchor='w'); self.auth_status_label.pack(side=tk.LEFT, padx=(10,0))

        load_filter_lf = ttk.LabelFrame(frm, text="Video List Management", padding=5); load_filter_lf.pack(fill=tk.X, pady=5)
        self.load_all_button = ttk.Button(load_filter_lf, text='Load/Refresh My Videos', command=self.gui_load_all_videos, state=tk.DISABLED)
        self.load_all_button.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        filter_buttons_frame = ttk.Frame(load_filter_lf); filter_buttons_frame.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        self.filter_all_button = ttk.Button(filter_buttons_frame, text='Show All', command=lambda: self.apply_filter_to_treeview("all"), state=tk.DISABLED); self.filter_all_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1)
        self.filter_private_button = ttk.Button(filter_buttons_frame, text='Private', command=lambda: self.apply_filter_to_treeview("private"), state=tk.DISABLED); self.filter_private_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1)
        self.filter_unlisted_button = ttk.Button(filter_buttons_frame, text='Unlisted', command=lambda: self.apply_filter_to_treeview("unlisted"), state=tk.DISABLED); self.filter_unlisted_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1)
        self.filter_public_button = ttk.Button(filter_buttons_frame, text='Public', command=lambda: self.apply_filter_to_treeview("public"), state=tk.DISABLED); self.filter_public_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1)

        tree_frame = ttk.Frame(frm); tree_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.tree = ttk.Treeview(tree_frame, columns=('id', 'title', 'status', 'publish_at'), show='headings', selectmode="extended")
        self.tree.heading('id', text='Video ID'); self.tree.column('id', width=120, stretch=tk.NO, anchor='w')
        self.tree.heading('title', text='Current Title'); self.tree.column('title', width=300, anchor='w')
        self.tree.heading('status', text='Current Privacy'); self.tree.column('status', width=100, stretch=tk.NO, anchor='w')
        self.tree.heading('publish_at', text='Scheduled At (UTC)'); self.tree.column('publish_at', width=180, anchor='w')
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview); hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set); self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True); vsb.pack(side=tk.RIGHT, fill=tk.Y); hsb.pack(side=tk.BOTTOM, fill=tk.X)

        # --- MODIFICATION: Bind selection event to the new display logic ---
        self.tree.bind('<<TreeviewSelect>>', self.on_video_select_display_only)

        select_buttons_frame = ttk.Frame(frm); select_buttons_frame.pack(fill=tk.X, pady=(2,5))
        self.select_all_button = ttk.Button(select_buttons_frame, text='Select All Visible', command=self.select_all_visible_videos, state=tk.DISABLED); self.select_all_button.pack(side=tk.LEFT, padx=2)
        self.deselect_all_button = ttk.Button(select_buttons_frame, text='Deselect All', command=self.deselect_all_videos, state=tk.DISABLED); self.deselect_all_button.pack(side=tk.LEFT, padx=2)

        sched = ttk.LabelFrame(frm, text='Schedule & Interval', padding=10); sched.pack(fill=tk.X, pady=5)
        ttk.Label(sched, text='First Publish (YYYY-MM-DD HH:MM Local Time):').grid(row=0, column=0, sticky='w', pady=2)
        self.start_ent = ttk.Entry(sched, width=20); self.start_ent.insert(0, (datetime.now() + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M')); self.start_ent.grid(row=0, column=1, sticky='ew', padx=5, pady=2)
        ttk.Label(sched, text='Interval Hours:').grid(row=1, column=0, sticky='w', pady=2)
        self.interval_hour_var = tk.StringVar(value='0'); self.interval_hour_spin = ttk.Spinbox(sched, from_=0, to=1000, width=5, textvariable=self.interval_hour_var); self.interval_hour_spin.grid(row=1, column=1, sticky='w', padx=5, pady=2)
        ttk.Label(sched, text='Interval Minutes:').grid(row=2, column=0, sticky='w', pady=2)
        self.interval_minute_var = tk.StringVar(value='120'); self.interval_minute_spin = ttk.Spinbox(sched, from_=0, to=59, width=5, textvariable=self.interval_minute_var); self.interval_minute_spin.grid(row=2, column=1, sticky='w', padx=5, pady=(2,5))
        sched.grid_columnconfigure(1, weight=1)

        # --- MODIFICATION: Update label for clarity ---
        meta = ttk.LabelFrame(frm, text='Metadata Defaults', padding=10); meta.pack(fill=tk.X, pady=5)
        ttk.Label(meta, text='Title (override):').grid(row=0, column=0, sticky='w', pady=2)
        self.title_ent = ttk.Entry(meta, width=40); self.title_ent.grid(row=0, column=1, sticky='ew', pady=2)
        ttk.Label(meta, text='Description (override):').grid(row=1, column=0, sticky='nw', pady=2)
        self.desc_txt_frame = ttk.Frame(meta); self.desc_txt_frame.grid(row=1, column=1, sticky='ew', pady=2)
        self.desc_txt = tk.Text(self.desc_txt_frame, height=3, width=38, wrap=tk.WORD); self.desc_scroll = ttk.Scrollbar(self.desc_txt_frame, orient=tk.VERTICAL, command=self.desc_txt.yview)
        self.desc_txt.configure(yscrollcommand=self.desc_scroll.set); self.desc_txt.pack(side=tk.LEFT, fill=tk.BOTH, expand=True); self.desc_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        ttk.Label(meta, text='Tags (replaces existing):').grid(row=2, column=0, sticky='w', pady=2)
        self.tags_ent = ttk.Entry(meta, width=40); self.tags_ent.grid(row=2, column=1, sticky='ew', pady=2)
        ttk.Label(meta, text='Category:').grid(row=3, column=0, sticky='w', pady=2)
        self.cat_cb = ttk.Combobox(meta, values=['(Keep Original)'] + list(CATEGORY_MAP.keys()), width=37, state="readonly"); self.cat_cb.set('(Keep Original)'); self.cat_cb.grid(row=3, column=1, sticky='ew', pady=2)
        self.made_for_kids_var_options = ['(Keep Original)', 'Yes', 'No']
        ttk.Label(meta, text='Made for Kids:').grid(row=4, column=0, sticky='w', pady=2)
        self.made_for_kids_cb = ttk.Combobox(meta, values=self.made_for_kids_var_options, width=37, state="readonly"); self.made_for_kids_cb.set('(Keep Original)'); self.made_for_kids_cb.grid(row=4, column=1, sticky='ew', pady=2)
        meta.grid_columnconfigure(1, weight=1)

        action_frm = ttk.Frame(frm); action_frm.pack(fill=tk.X, pady=5)
        self.log_checkbutton = ttk.Checkbutton(action_frm, text='Save Log File on Exit (ytscheduler.log)', variable=self.save_log_var); self.log_checkbutton.pack(anchor='w', pady=(5,0))
        self.schedule_button = ttk.Button(action_frm, text='SCHEDULE SELECTED VIDEOS', command=self.process_scheduling_gui, style="Accent.TButton", state=tk.DISABLED); self.schedule_button.pack(pady=10, fill=tk.X, ipady=5)
        s = ttk.Style(); s.configure("Accent.TButton", font=("Helvetica", 10, "bold"))

    def update_auth_status(self, authenticated: bool, message: str = ""):
        if authenticated: self.auth_status_label.config(text="Status: Authenticated", foreground="green")
        else: self.auth_status_label.config(text=f"Status: Not Authenticated. {message}".strip(), foreground="red")
        self.enable_video_management_buttons(authenticated)

    def enable_video_management_buttons(self, authenticated: bool):
        auth_dep_state = tk.NORMAL if authenticated and self.service else tk.DISABLED
        self.load_all_button.config(state=auth_dep_state)
        self.schedule_button.config(state=auth_dep_state)
        list_dep_state = tk.NORMAL if authenticated and self.service and self.all_channel_videos else tk.DISABLED
        for btn in [self.filter_all_button, self.filter_private_button, self.filter_unlisted_button, self.filter_public_button, self.select_all_button, self.deselect_all_button]:
            btn.config(state=list_dep_state)

    def _populate_treeview(self, videos_to_display):
        for item in self.tree.get_children(): self.tree.delete(item)
        for vd in videos_to_display:
            pub_at_disp = "Not Scheduled"
            publish_at_val = vd.video_status.get('publishAt')
            if publish_at_val:
                try:
                    pub_at_disp = datetime.fromisoformat(publish_at_val.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S UTC')
                except ValueError:
                    pub_at_disp = publish_at_val
            
            privacy_status_val = vd.video_status.get('privacyStatus', 'N/A')
            
            self.tree.insert('', tk.END, values=(
                vd.video_id,
                vd.video_snippet.get('title', vd.original_title),
                privacy_status_val,
                pub_at_disp
            ))
        self.enable_video_management_buttons(self.service is not None)

    def apply_filter_to_treeview(self, privacy_filter="all"):
        if not self.service: messagebox.showwarning("Not Authenticated", "Please authenticate first.", parent=self.root); return
        if not self.all_channel_videos: messagebox.showinfo("No Videos Loaded", "Please load videos first.", parent=self.root); return
        logger.info(f"Applying filter: {privacy_filter}")
        self.current_filter_applied = privacy_filter
        filtered_list = [vd for vd in self.all_channel_videos if privacy_filter == "all" or vd.video_status.get('privacyStatus') == privacy_filter]
        self._populate_treeview(filtered_list)
        if not filtered_list and privacy_filter != "all": messagebox.showinfo("Filter Result", f"No videos found for filter: '{privacy_filter}'.", parent=self.root)

    def select_all_visible_videos(self):
        if not self.tree.get_children(): messagebox.showinfo("No Videos", "No videos in list to select.", parent=self.root); return
        self.tree.selection_set(self.tree.get_children()); logger.info(f"Selected all {len(self.tree.get_children())} visible videos.")

    def deselect_all_videos(self):
        if self.tree.selection(): logger.info(f"Deselected {len(self.tree.selection())} videos."); self.tree.selection_remove(self.tree.selection())

    # --- MODIFICATION: This method now only displays pre-loaded data ---
    def on_video_select_display_only(self, event):
        """
        Called when a video selection changes. If a single video is selected,
        it displays the pre-loaded description in the description box.
        """
        self.desc_txt.delete('1.0', tk.END) # Clear box first
        selected_items = self.tree.selection()

        if len(selected_items) != 1:
            return # Do nothing if zero or multiple videos are selected

        item_id = selected_items[0]
        try:
            video_id_from_tree = self.tree.item(item_id, 'values')[0]
        except IndexError:
            logger.warning("Could not retrieve video ID from selected tree item.")
            return

        # Find the corresponding VideoData object from our master list
        found_vd = next((vd for vd in self.all_channel_videos if vd.video_id == video_id_from_tree), None)

        if found_vd:
            # Populate the description box with the description from the object
            self.desc_txt.insert('1.0', found_vd.description_to_set)
        else:
            logger.warning(f"Could not find VideoData object for ID {video_id_from_tree}")

    def select_credentials_and_auth(self):
        path = filedialog.askopenfilename(title='Select client_secrets.json', filetypes=[('JSON files', '*.json')], parent=self.root)
        if path:
            self.client_secrets_path = path; logger.info(f'Selected credentials file: {path}')
            try:
                self.service = get_authenticated_service(self.client_secrets_path, app_root_window=self.root)
                self.update_auth_status(True)
                messagebox.showinfo("Authentication Successful",
                                    "Authentication successful.\nPlease click 'Load/Refresh My Videos' to fetch your video list.",
                                    parent=self.root)
            except FileNotFoundError: self.update_auth_status(False, "Client secrets file not found.")
            except Exception as e:
                logger.error(f"Authentication failed after selecting credentials: {e}", exc_info=True)
                err_msg_lower = str(e).lower()
                if "invalid_scope" in err_msg_lower:
                     messagebox.showerror("Authentication Failed", f"OAuth Scope Error: {e}\nPlease ensure client_secrets.json & API permissions are correct.", parent=self.root)
                elif "cancelled" not in err_msg_lower and "empty code" not in err_msg_lower:
                    messagebox.showerror("Authentication Failed", f"Could not authenticate: {e}", parent=self.root)
                self.service = None; self.update_auth_status(False, "Authentication failed.")

    # --- MODIFICATION: Core matching logic moved here ---
    def fetch_all_videos_from_api(self):
        if not self.service:
            logger.error("Service not initialized.")
            messagebox.showerror("Error", "Not authenticated.", parent=self.root)
            return []

        all_video_data_objects = []
        load_progress_win = tk.Toplevel(self.root)
        load_progress_win.title("Loading Videos"); load_progress_win.geometry("400x100"); load_progress_win.resizable(False, False); load_progress_win.grab_set(); load_progress_win.transient(self.root)
        prog_label_text = tk.StringVar(value="Initializing..."); ttk.Label(load_progress_win, textvariable=prog_label_text).pack(pady=5)
        prog_bar = ttk.Progressbar(load_progress_win, orient="horizontal", length=350, mode="indeterminate"); prog_bar.pack(pady=5); prog_bar.start(10)
        self.root.update_idletasks()
        
        # Log the directory where we will search for .txt files
        search_dir = Path.cwd()
        logger.info(f"Searching for .txt description files in: {search_dir}")

        try:
            # ... (Existing API call logic to get channel and playlist ID) ...
            prog_label_text.set("Fetching channel details...")
            load_progress_win.update_idletasks()
            ch_resp = self.service.channels().list(part="contentDetails", mine=True).execute()
            uploads_id = ch_resp["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
            logger.info(f"Uploads playlist ID: {uploads_id}")

            video_ids = []
            next_page_token = None
            while True:
                playlist_req = self.service.playlistItems().list(playlistId=uploads_id, part="contentDetails", maxResults=50, pageToken=next_page_token)
                playlist_resp = playlist_req.execute()
                video_ids.extend([item["contentDetails"]["videoId"] for item in playlist_resp.get("items", [])])
                next_page_token = playlist_resp.get("nextPageToken")
                if not next_page_token:
                    break
                prog_label_text.set(f"Fetched {len(video_ids)} video IDs so far...")
                load_progress_win.update_idletasks()
            
            logger.info(f"Found {len(video_ids)} total video IDs.")
            if not video_ids: return []

            prog_bar.config(mode="determinate", maximum=len(video_ids), value=0)
            prog_bar.stop()
            
            for i in range(0, len(video_ids), 50):
                batch_ids = video_ids[i:i+50]
                prog_label_text.set(f"Fetching details for videos {i+1}-{min(i+50, len(video_ids))} of {len(video_ids)}...")
                load_progress_win.update_idletasks()

                videos_req = self.service.videos().list(id=",".join(batch_ids), part="snippet,status,contentDetails,recordingDetails")
                videos_resp = videos_req.execute()

                for video_item in videos_resp.get("items", []):
                    vid_id = video_item["id"]
                    vid_snippet = video_item.get("snippet", {})
                    title = vid_snippet.get("title", "No Title")
                    
                    # Create the VideoData object first
                    vd_obj = VideoData(vid_id, title, vid_snippet, video_item.get("status", {}), video_item.get("contentDetails", {}), video_item.get("recordingDetails", {}))

                    # --- NEW MATCHING LOGIC ---
                    # Normalize the YouTube video title for file matching
                    normalized_title = title.replace(' ', '_')
                    
                    # Search for a matching .txt file in the script's working directory
                    try:
                        for txt_file in search_dir.glob(f"{normalized_title}*.txt"):
                            logger.info(f"Found match: File '{txt_file.name}' for Video Title '{title}'.")
                            vd_obj.description_to_set = txt_file.read_text(encoding='utf-8')
                            vd_obj.description_source_file = txt_file.name # Store for verification
                            break # Use the first match
                    except Exception as e:
                        logger.error(f"Error reading description file for '{title}': {e}")
                    # --- END OF NEW LOGIC ---
                    
                    all_video_data_objects.append(vd_obj)
                    prog_bar['value'] += 1
                    load_progress_win.update_idletasks()

            logger.info(f"Fetched full details for {len(all_video_data_objects)} videos.")

        except Exception as e:
            logger.error(f"Error fetching videos: {e}", exc_info=True)
            messagebox.showerror("API Error", f"Failed to fetch videos: {e}", parent=self.root)
            return []
        finally:
            if load_progress_win.winfo_exists():
                load_progress_win.destroy()
        
        return all_video_data_objects

    def gui_load_all_videos(self):
        if not self.service: messagebox.showerror('Error', 'Not authenticated.', parent=self.root); self.update_auth_status(False, "Auth required."); return
        self.all_channel_videos = self.fetch_all_videos_from_api()
        self.current_filter_applied = "all"; self._populate_treeview(self.all_channel_videos)
        if self.all_channel_videos: messagebox.showinfo("Videos Loaded", f"Loaded {len(self.all_channel_videos)} videos. Descriptions from matching .txt files have been pre-loaded.", parent=self.root)

    def process_scheduling_gui(self):
        sel_items = self.tree.selection()
        if not sel_items: messagebox.showwarning("No Selection", "No videos selected.", parent=self.root); return
        
        vids_to_sched = []
        for item_id_in_tree in sel_items:
            video_id_from_tree = self.tree.item(item_id_in_tree)['values'][0]
            found_vd = next((vd for vd in self.all_channel_videos if vd.video_id == video_id_from_tree), None)
            if found_vd: vids_to_sched.append(found_vd)
        
        if not vids_to_sched: messagebox.showerror("Error", "Selected videos not found. Reload list.", parent=self.root); return
        logger.info(f"Processing {len(vids_to_sched)} videos for scheduling.")
        if not self.service: messagebox.showerror("Auth Error", "Auth lost. Re-authenticate.", parent=self.root); return

        # --- MODIFICATION: Check for global overrides ---
        title_override = self.title_ent.get().strip()
        desc_override = self.desc_txt.get('1.0','end-1c').strip()
        tags_str_new = self.tags_ent.get()
        
        tags_list_new = []
        if tags_str_new.strip(): tags_list_new = sanitize_tags([t.strip() for t in tags_str_new.split(',') if t.strip()])
        
        cat_choice = self.cat_cb.get()
        mfd_choice = self.made_for_kids_cb.get()

        # ... (Date and interval parsing logic remains the same) ...
        try:
            start_str = self.start_ent.get(); local_dt = datetime.strptime(start_str, '%Y-%m-%d %H:%M')
            try: local_tz = datetime.now().astimezone().tzinfo
            except Exception: local_tz = timezone(timedelta(seconds=-time.timezone))
            start_utc = local_dt.replace(tzinfo=local_tz).astimezone(timezone.utc)
            if start_utc < datetime.now(timezone.utc) + timedelta(minutes=15): messagebox.showerror("Error", "First publish must be >= 15 mins in future.", parent=self.root); return
        except ValueError: messagebox.showerror("Error", "Invalid start date/time (YYYY-MM-DD HH:MM).", parent=self.root); return
        try:
            h = int(self.interval_hour_var.get()); m = int(self.interval_minute_var.get())
            delta = timedelta(hours=h, minutes=m)
            if delta <= timedelta(0) and len(vids_to_sched) > 1: delta = timedelta(minutes=15)
        except ValueError as e: messagebox.showerror("Error", f"Invalid interval: {e}", parent=self.root); return

        curr_pub_utc = start_utc
        for i, vd_obj in enumerate(vids_to_sched):
            # Apply overrides if they exist, otherwise use pre-loaded values
            if title_override:
                vd_obj.title_to_set = title_override
            if desc_override:
                vd_obj.description_to_set = desc_override
            
            if tags_str_new.strip():
                vd_obj.tags_to_set = tags_list_new
            
            if cat_choice != '(Keep Original)':
                vd_obj.categoryId_to_set = CATEGORY_MAP.get(cat_choice, vd_obj.categoryId_to_set)

            if mfd_choice != '(Keep Original)':
                vd_obj.madeForKids_to_set = (mfd_choice == 'Yes')
            
            vd_obj.privacyStatus_to_set = 'private' 
            vd_obj.publishAt_to_set_new = curr_pub_utc.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            
            logger.info(f"Video '{vd_obj.original_title}' ({vd_obj.video_id}) to schedule for: {vd_obj.publishAt_to_set_new} with title '{vd_obj.title_to_set}'")
            if i < len(vids_to_sched) - 1:
                curr_pub_utc += delta

        self.update_videos_on_youtube(vids_to_sched)

    def update_videos_on_youtube(self, videos_to_update):
        # ... (This method remains largely the same as it just uses the prepared data) ...
        if not self.service: messagebox.showerror("Error", "YouTube service unavailable.", parent=self.root); return
        total = len(videos_to_update); succ = 0; fail = 0
        prog_win = tk.Toplevel(self.root); prog_win.title("Scheduling Progress"); prog_win.geometry("450x130"); prog_win.resizable(False, False); prog_win.grab_set(); prog_win.transient(self.root)
        prog_bar = ttk.Progressbar(prog_win, orient="horizontal", length=350, mode="determinate", maximum=total); prog_bar.pack(pady=10)
        prog_label = ttk.Label(prog_win, text="Starting..."); prog_label.pack(pady=5)

        for i, vd_obj in enumerate(videos_to_update):
            prog_label.config(text=f"({i+1}/{total}) Processing: {vd_obj.title_to_set[:40]}...")
            prog_bar['value'] = i + 1; prog_win.update_idletasks()
            
            snip_body = {'title': vd_obj.title_to_set, 'description': vd_obj.description_to_set, 'tags': vd_obj.tags_to_set, 'categoryId': vd_obj.categoryId_to_set}
            stat_body = {'privacyStatus': vd_obj.privacyStatus_to_set, 'publishAt': vd_obj.publishAt_to_set_new, 'selfDeclaredMadeForKids': vd_obj.madeForKids_to_set}
            
            update_body = {'id': vd_obj.video_id, 'snippet': snip_body, 'status': stat_body}
            
            logger.info(f"Updating video {vd_obj.video_id}: {json.dumps(update_body, indent=2, ensure_ascii=False)}")
            try:
                req = self.service.videos().update(part="snippet,status", body=update_body)
                resp = req.execute()
                logger.info(f"Successfully updated video {resp['id']}.")
                vd_obj.video_snippet = resp.get('snippet', vd_obj.video_snippet)
                vd_obj.video_status = resp.get('status', vd_obj.video_status)
                vd_obj.original_title = vd_obj.title_to_set
                succ += 1
            except Exception as e:
                logger.error(f"Failed for video {vd_obj.video_id} ('{vd_obj.title_to_set}'): {e}", exc_info=True)
                fail += 1
        
        if prog_win.winfo_exists(): prog_win.destroy()
        summary = f"Process complete.\nSuccessfully updated: {succ}\nFailed/Skipped: {fail}"
        messagebox.showinfo("Process Complete", summary, parent=self.root)
        logger.info(summary.replace('\n', ' '))
        self.apply_filter_to_treeview(self.current_filter_applied)

    def on_exit(self):
        logger.info("Application exiting...")
        global file_log_handler_global
        if not self.save_log_var.get() and file_log_handler_global:
            logger.info(f"Log saving disabled. Removing log file.")
            if file_log_handler_global in logger.handlers: logger.removeHandler(file_log_handler_global)
            file_log_handler_global.close()
            file_log_handler_global = None
            try:
                if os.path.exists(LOG_FILE): os.remove(LOG_FILE)
            except OSError as e: logger.warning(f"Could not delete '{LOG_FILE}': {e}")
        
        if self.root and self.root.winfo_exists():
            self.root.destroy()
        
        logger.info("Exit procedure finished.")

if __name__ == '__main__':
    try:
        app = SchedulerApp()
    except Exception as e:
        logging.basicConfig(filename=LOG_FILE, level=logging.DEBUG, filemode='a', format="[%(asctime)s] [%(levelname)s] %(message)s")
        logging.critical(f"Fatal error during application startup: {e}", exc_info=True)
        try:
            root_error = tk.Tk(); root_error.withdraw()
            messagebox.showerror("Fatal Error", f"Application failed to start: {e}\nCheck {LOG_FILE}.", parent=root_error)
        except tk.TclError:
            print(f"FATAL ERROR (GUI FAILED): {e}\nCheck {LOG_FILE}.", file=sys.stderr)
        sys.exit(1)