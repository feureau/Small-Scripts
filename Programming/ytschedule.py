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
    "https://www.googleapis.com/auth/youtube",       # Corrected
    "https://www.googleapis.com/auth/youtube.force-ssl" # Corrected
]
TOKEN_FILE = "token.json"
LOG_FILE = "ytscheduler.log"
OAUTH_PORT = 0 # Port for the local OAuth server. 0 means pick an available ephemeral port.
API_TIMEOUT_SECONDS = 60 # Timeout in seconds for YouTube API calls (currently used for token refresh)

CATEGORY_MAP = {
    "Film & Animation": "1", "Autos & Vehicles": "2", "Music": "10",
    "Pets & Animals": "15", "Sports": "17", "Travel & Events": "19",
    "Gaming": "20", "People & Blogs": "22", "Comedy": "23",
    "Entertainment": "24", "News & Politics": "25", "Howto & Style": "26",
    "Education": "27", "Science & Technology": "28", "Nonprofits & Activism": "29"
}
LANGUAGES = {"English": "en", "Spanish": "es", "French": "fr", "German": "de", "Japanese": "ja", "Chinese": "zh"}

# --- Logger ---
logger = logging.getLogger("ytscheduler")
logger.setLevel(logging.DEBUG) # Process DEBUG messages and above (for publishAt debugging)

# Console Handler for immediate feedback
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG) # For publishAt debugging
console_handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S"))
if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
    logger.addHandler(console_handler)

# Global reference to file handler for easier management in on_exit
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
                    timeout=10 # Timeout for the revoke request
                )
                if response.status_code == 200:
                    logger.info(f"Refresh token revoked successfully from server (token: ...{token_data['refresh_token'][-6:]}).")
                else:
                    logger.warning(f"Failed to revoke refresh token from server. Status: {response.status_code}, Response: {response.text}")
            else:
                logger.info("No refresh_token found in token.json to revoke from server.")
        except FileNotFoundError:
            logger.info("Token file not found for revocation (already deleted or never existed).")
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error during token revocation: {e}")
        except Exception as e:
            logger.error(f"Error during token data loading or server-side revocation: {e}", exc_info=True)
        finally:
            try:
                if os.path.exists(TOKEN_FILE):
                    os.remove(TOKEN_FILE)
                    logger.info(f"Local token file '{TOKEN_FILE}' deleted.")
            except OSError as e:
                logger.error(f"Error deleting local token file '{TOKEN_FILE}': {e}", exc_info=True)
    else:
        logger.info("No local token file to revoke or delete.")

def setup_revocation_on_exit():
    atexit.register(revoke_token)
    def on_sig(signum, frame):
        signal_name = signal.Signals(signum).name if hasattr(signal, 'Signals') and isinstance(signum, signal.Signals) else signum
        logger.info(f"Signal {signal_name} received, attempting token revocation before exit.")
        sys.exit(1) # Ensure sys.exit is called to trigger atexit handlers
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
            logger.warning(f"Failed to load token from file: {e}. Will attempt re-authentication.", exc_info=True)
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("Refreshing expired credentials...")
            try:
                request_session_with_timeout = Request(timeout=API_TIMEOUT_SECONDS)
                creds.refresh(request_session_with_timeout)
                logger.info("Credentials refreshed successfully.")
            except Exception as e:
                logger.error(f"Failed to refresh credentials: {e}. Proceeding to full auth.", exc_info=True)
                creds = None

        if not creds:
            logger.info("No valid credentials found or refresh failed. Starting new OAuth flow.")
            if not secrets_path or not Path(secrets_path).exists():
                logger.error("Client secrets file path not provided or file does not exist.")
                parent_win = app_root_window if app_root_window and app_root_window.winfo_exists() else None
                if parent_win:
                    messagebox.showerror("Authentication Error", "Client secrets file path not provided or file does not exist. Please select it first.", parent=parent_win)
                else:
                    print("ERROR: Client secrets file path not provided or file does not exist.")
                raise FileNotFoundError("Client secrets file is required for new authentication.")

            flow_attempt1 = InstalledAppFlow.from_client_secrets_file(secrets_path, SCOPES)
            try:
                logger.info(f"Attempt 1: Authentication via local server (port={OAUTH_PORT}, auto browser open)...")
                creds = flow_attempt1.run_local_server(
                    port=OAUTH_PORT, open_browser=True,
                    authorization_prompt_message="Awaiting authorization in your browser...\nYour browser should open to Google's sign-in page.\nIf it doesn't, please copy the URL printed in the console/terminal and open it manually.\n{url}",
                    success_message="Authentication successful! You can close this browser tab and return to the application.",
                    timeout_seconds=900
                )
                logger.info("Attempt 1: Local server auth (auto browser) successful, credentials obtained.")
            except (MismatchingStateError, TimeoutError) as e_specific_attempt1:
                 logger.error(f"Attempt 1: Local server auth (auto browser) failed with {type(e_specific_attempt1).__name__}: {e_specific_attempt1}.", exc_info=True)
            except Exception as e_local_server_auto:
                logger.error(f"Attempt 1: Local server auth (auto browser) failed. Type: {type(e_local_server_auto).__name__}, Error: {e_local_server_auto}.", exc_info=True)

            if not (creds and creds.valid):
                logger.info("Attempt 1 failed or produced invalid credentials.")
                flow_attempt2 = InstalledAppFlow.from_client_secrets_file(secrets_path, SCOPES)
                try:
                    logger.info(f"Attempt 2: Authentication via local server (port={OAUTH_PORT}, manual browser open)...")
                    auth_url_manual_server, _ = flow_attempt2.authorization_url()
                    instructions_manual_server = (
                        "AUTHENTICATION REQUIRED (Attempt 2 of 3):\n\n"
                        "The application will now start a local server and wait for you to authorize.\n\n"
                        f"1. Please copy the URL below and paste it into your web browser:\n\n{auth_url_manual_server}\n\n"
                        "2. Authorize the application in your browser.\n\n"
                        "3. After authorization, your browser will attempt to redirect to the local server. "
                        "The application should then complete the process automatically.\n\n"
                        "Click 'OK' to start the local server and proceed with the steps above."
                    )
                    parent_win = app_root_window if app_root_window and app_root_window.winfo_exists() else None
                    if parent_win:
                         messagebox.showinfo("Manual Authentication - Local Server Method", instructions_manual_server, parent=parent_win)
                    else:
                        print(instructions_manual_server.replace("\n\n", "\n"))

                    creds = flow_attempt2.run_local_server(
                        port=OAUTH_PORT, open_browser=False,
                        timeout_seconds=900,
                        success_message="Authentication successful! You can close this browser tab and return to the application."
                    )
                    logger.info("Attempt 2: Local server auth (manual browser) successful, credentials obtained.")
                except (MismatchingStateError, TimeoutError) as e_specific_attempt2:
                    logger.error(f"Attempt 2: Local server auth (manual browser) failed with {type(e_specific_attempt2).__name__}: {e_specific_attempt2}.", exc_info=True)
                except Exception as e_local_server_manual:
                    logger.error(f"Attempt 2: Local server auth (manual browser) failed. Type: {type(e_local_server_manual).__name__}, Error: {e_local_server_manual}.", exc_info=True)

            if not (creds and creds.valid):
                logger.info("Attempts 1 and 2 failed or produced invalid credentials.")
                flow_attempt3 = InstalledAppFlow.from_client_secrets_file(secrets_path, SCOPES)
                try:
                    logger.info("Attempt 3: Fully manual code exchange flow...")
                    auth_url_fully_manual, _ = flow_attempt3.authorization_url()
                    instructions_part1 = (
                        "AUTHENTICATION REQUIRED (Attempt 3 of 3 - Fully Manual):\n\n"
                        "STEP 1 of 2: Authorize in Browser\n\n"
                        f"1. Please open this URL in your browser:\n\n{auth_url_fully_manual}\n\n"
                        "2. Authorize the application.\n\n"
                        "3. Your browser will be redirected to a URL. The address bar will show something like:\n"
                        f"   'http://localhost:{'A_DYNAMIC_PORT' if OAUTH_PORT == 0 else OAUTH_PORT}/?code=AUTH_CODE_HERE&state=...'\n"
                        f"   (The port will be dynamically assigned if OAUTH_PORT is 0, otherwise it's {OAUTH_PORT})\n\n"
                        "4. From that redirected URL in your browser's address bar, carefully copy THE ENTIRE 'code' VALUE.\n"
                        "   (It's the string of characters immediately after 'code=' and usually before the next '&' symbol, if any).\n\n"
                        "Click 'OK' here ONLY AFTER you have COPIED the authorization code."
                    )
                    auth_dialog_parent = app_root_window if app_root_window and app_root_window.winfo_exists() else None
                    if auth_dialog_parent:
                        messagebox.showinfo("Manual Authentication - Step 1: Get Code", instructions_part1, parent=auth_dialog_parent)
                    else:
                        print("--------------------------------------------------------------------")
                        print(instructions_part1.replace("\n\n", "\n"))
                        input("Press Enter after you have copied the code and are ready to paste it...")

                    auth_code = simpledialog.askstring(
                        "Manual Authentication - Step 2: Paste Code",
                        "Please paste the 'code' you copied from your browser's address bar in the previous step:",
                        parent=auth_dialog_parent
                    )

                    if auth_code:
                        auth_code = auth_code.strip()
                        if not auth_code:
                            logger.warning("Attempt 3: Manual authentication cancelled (empty code entered).")
                            raise Exception("Manual authentication failed: Empty code entered.")
                        flow_attempt3.fetch_token(code=auth_code)
                        creds = flow_attempt3.credentials
                        logger.info("Attempt 3: Successfully authenticated using manual code exchange.")
                    else:
                        logger.warning("Attempt 3: Manual authentication cancelled by user (dialog closed or cancel pressed).")
                        raise Exception("Manual authentication cancelled by user.")
                except Exception as e_fetch_token:
                    final_error_msg_manual = f"Attempt 3: Manual code exchange failed: {e_fetch_token}"
                    logger.error(final_error_msg_manual, exc_info=True)
                    parent_for_final_error = app_root_window if app_root_window and app_root_window.winfo_exists() else None
                    if "cancelled by user" not in str(e_fetch_token).lower() and "empty code entered" not in str(e_fetch_token).lower():
                        if parent_for_final_error:
                            messagebox.showerror("Authentication Failed", final_error_msg_manual, parent=parent_for_final_error)
                        else:
                            print(f"ERROR: {final_error_msg_manual}")
                    raise Exception(f"All authentication methods failed. Last error: {e_fetch_token}") from e_fetch_token

            if creds and creds.valid:
                with open(TOKEN_FILE, 'w') as f: f.write(creds.to_json())
                logger.info(f"Credentials obtained and saved to {TOKEN_FILE}")
            else:
                logger.error("All authentication attempts failed or resulted in invalid credentials.")
                raise Exception("Failed to obtain valid credentials after all authentication attempts.")

    if creds and creds.valid:
        return build('youtube', 'v3', credentials=creds, cache_discovery=False)
    else:
        logger.error("CRITICAL: Attempting to build service without valid credentials.")
        raise Exception("Failed to build YouTube service due to missing or invalid credentials after authentication process.")


# --- Helpers ---
def sanitize_description(desc: str) -> str:
    desc = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F]', '', desc)
    return desc[:4999]

def sanitize_tags(raw_tags):
    clean = []; current_length = 0
    for t in raw_tags:
        tag = str(t).strip()
        if not tag: continue
        tag = re.sub(r'[\x00-\x1F\x7F\"]', '', tag); tag = tag[:75]
        if current_length + len(tag) + (1 if clean else 0) > 480:
            logger.warning(f"Tag '{tag}' truncated or skipped as total tag length exceeds limit."); break
        if tag: clean.append(tag); current_length += len(tag) + (1 if len(clean) > 1 else 0)
    return clean

# --- VideoData model ---
class VideoData:
    def __init__(self, video_id, title, current_snippet, current_status):
        self.video_id = video_id; self.original_title = title
        self.current_snippet = current_snippet if current_snippet else {} # From playlistItem.snippet
        self.current_status = current_status if current_status else {} # From playlistItem.status

        # Initialize with data primarily from playlistItem
        self.title_to_set = title # From playlistItem.snippet.title
        self.description_to_set = self.current_snippet.get('description', '') # From playlistItem.snippet.description

        # These are NOT in playlistItem.snippet or playlistItem.status. They are video-specific.
        # They will be default/empty unless populated by a videos().list call (not done by default for performance).
        self.tags_to_set = [] # Tags for a video
        self.categoryId_to_set = CATEGORY_MAP['Entertainment'] # Default category
        self.videoLanguage_to_set = None # e.g., 'en'
        self.defaultLanguage_to_set = None # e.g., 'en' for title/desc
        self.recordingDate_to_set = None # ISO 8601 string

        # These are NOT in playlistItem.status. They are video-specific status/details.
        self.madeForKids_to_set = False # Default
        self.embeddable_to_set = True # Default
        self.publicStatsViewable_to_set = True # Default

        # This is for the *new* schedule being applied by this script
        self.publishAt_to_set = None
        # This is the current privacy from playlistItem.status
        self.privacyStatus_to_set = self.current_status.get('privacyStatus', 'private')


    def __str__(self):
        # Display current actual publishAt from playlistItem.status if available
        current_pub_at = self.current_status.get('publishAt', 'Not Set')
        return f"ID: {self.video_id}, Title: {self.original_title}, CurrentPublishAt: {current_pub_at}, Privacy: {self.current_status.get('privacyStatus')}"

# --- Main GUI app ---
class SchedulerApp:
    def __init__(self):
        self.client_secrets_path = None; self.service = None
        self.all_channel_videos = []; self.current_filter_applied = "all"

        global file_log_handler_global
        try:
            if os.path.exists(LOG_FILE):
                os.remove(LOG_FILE)
            file_log_handler_global = logging.FileHandler(LOG_FILE, encoding='utf-8')
            file_log_handler_global.setLevel(logging.DEBUG) # For publishAt debugging
            file_log_handler_global.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S"))
            logger.addHandler(file_log_handler_global)
            logger.info("Application started and file logger initialized.")
        except Exception as e:
            logger.warning(f"Could not set up log file '{LOG_FILE}': {e}", exc_info=True)
            file_log_handler_global = None

        self.root = tk.Tk(); setup_revocation_on_exit()
        self.save_log_var = tk.BooleanVar(master=self.root, value=False) # Default to NOT saving log
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

        select_buttons_frame = ttk.Frame(frm); select_buttons_frame.pack(fill=tk.X, pady=(2,5))
        self.select_all_button = ttk.Button(select_buttons_frame, text='Select All Visible', command=self.select_all_visible_videos, state=tk.DISABLED); self.select_all_button.pack(side=tk.LEFT, padx=2)
        self.deselect_all_button = ttk.Button(select_buttons_frame, text='Deselect All', command=self.deselect_all_videos, state=tk.DISABLED); self.deselect_all_button.pack(side=tk.LEFT, padx=2)

        sched = ttk.LabelFrame(frm, text='Schedule & Interval', padding=10); sched.pack(fill=tk.X, pady=5)
        ttk.Label(sched, text='First Publish (YYYY-MM-DD HH:MM Local Time):').grid(row=0, column=0, sticky='w', pady=2)
        self.start_ent = ttk.Entry(sched, width=20); self.start_ent.insert(0, (datetime.now() + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M')); self.start_ent.grid(row=0, column=1, sticky='ew', padx=5, pady=2)
        ttk.Label(sched, text='Interval Hours:').grid(row=1, column=0, sticky='w', pady=2)
        self.interval_hour_var = tk.StringVar(value='1'); self.interval_hour_spin = ttk.Spinbox(sched, from_=0, to=1000, width=5, textvariable=self.interval_hour_var); self.interval_hour_spin.grid(row=1, column=1, sticky='w', padx=5, pady=2)
        ttk.Label(sched, text='Interval Minutes:').grid(row=2, column=0, sticky='w', pady=2)
        self.interval_minute_var = tk.StringVar(value='0'); self.interval_minute_spin = ttk.Spinbox(sched, from_=0, to=59, width=5, textvariable=self.interval_minute_var); self.interval_minute_spin.grid(row=2, column=1, sticky='w', padx=5, pady=(2,5))
        sched.grid_columnconfigure(1, weight=1)

        meta = ttk.LabelFrame(frm, text='Metadata Defaults (Applied to ALL selected videos for scheduling)', padding=10); meta.pack(fill=tk.X, pady=5)
        ttk.Label(meta, text='Title (leave empty for original):').grid(row=0, column=0, sticky='w', pady=2)
        self.title_ent = ttk.Entry(meta, width=40); self.title_ent.grid(row=0, column=1, sticky='ew', pady=2)
        ttk.Label(meta, text='Description (leave empty for original):').grid(row=1, column=0, sticky='nw', pady=2)
        self.desc_txt_frame = ttk.Frame(meta); self.desc_txt_frame.grid(row=1, column=1, sticky='ew', pady=2)
        self.desc_txt = tk.Text(self.desc_txt_frame, height=3, width=38, wrap=tk.WORD); self.desc_scroll = ttk.Scrollbar(self.desc_txt_frame, orient=tk.VERTICAL, command=self.desc_txt.yview)
        self.desc_txt.configure(yscrollcommand=self.desc_scroll.set); self.desc_txt.pack(side=tk.LEFT, fill=tk.BOTH, expand=True); self.desc_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        ttk.Label(meta, text='Tags (comma-sep, replaces existing):').grid(row=2, column=0, sticky='w', pady=2)
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
            # vd.current_status is from playlistItem.status
            if vd.current_status.get('publishAt') and vd.current_status['publishAt'] is not None:
                try:
                    pub_at_disp = datetime.fromisoformat(vd.current_status['publishAt'].replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S UTC')
                except ValueError:
                    pub_at_disp = vd.current_status['publishAt'] 
            self.tree.insert('', tk.END, values=(vd.video_id, vd.original_title, vd.current_status.get('privacyStatus', 'N/A'), pub_at_disp))
        self.enable_video_management_buttons(self.service is not None)


    def apply_filter_to_treeview(self, privacy_filter="all"):
        if not self.service: messagebox.showwarning("Not Authenticated", "Please authenticate first.", parent=self.root); return
        if not self.all_channel_videos: messagebox.showinfo("No Videos Loaded", "Please load videos first.", parent=self.root); return
        logger.info(f"Applying filter: {privacy_filter}")
        self.current_filter_applied = privacy_filter
        filtered_list = [vd for vd in self.all_channel_videos if privacy_filter == "all" or vd.current_status.get('privacyStatus') == privacy_filter]
        self._populate_treeview(filtered_list)
        if not filtered_list and privacy_filter != "all": messagebox.showinfo("Filter Result", f"No videos found for filter: '{privacy_filter}'.", parent=self.root)

    def select_all_visible_videos(self):
        if not self.tree.get_children(): messagebox.showinfo("No Videos", "No videos in list to select.", parent=self.root); return
        self.tree.selection_set(self.tree.get_children()); logger.info(f"Selected all {len(self.tree.get_children())} visible videos.")

    def deselect_all_videos(self):
        if self.tree.selection(): logger.info(f"Deselected {len(self.tree.selection())} videos."); self.tree.selection_remove(self.tree.selection())

    def select_credentials_and_auth(self):
        path = filedialog.askopenfilename(title='Select client_secrets.json', filetypes=[('JSON files', '*.json')], parent=self.root)
        if path:
            self.client_secrets_path = path; logger.info(f'Selected credentials file: {path}')
            try:
                self.service = get_authenticated_service(self.client_secrets_path, app_root_window=self.root)
                self.update_auth_status(True)
                logger.info("Authentication successful. User needs to manually load videos.")
                messagebox.showinfo("Authentication Successful",
                                    "Authentication successful.\nPlease click 'Load/Refresh My Videos' to fetch your video list.",
                                    parent=self.root)
            except FileNotFoundError: self.update_auth_status(False, "Client secrets file not found.")
            except Exception as e:
                logger.error(f"Authentication failed after selecting credentials: {e}", exc_info=True)
                err_msg_lower = str(e).lower()
                if "invalid_scope" in err_msg_lower: # Specific check for scope error
                     messagebox.showerror("Authentication Failed", f"OAuth Scope Error: {e}\nPlease ensure your client_secrets.json is configured correctly and the API has necessary permissions.", parent=self.root)
                elif "cancelled" not in err_msg_lower and \
                   "empty code" not in err_msg_lower and \
                   "all authentication methods failed" not in err_msg_lower and \
                   "failed to obtain valid credentials" not in err_msg_lower:
                    messagebox.showerror("Authentication Failed", f"Could not authenticate: {e}", parent=self.root)
                self.service = None; self.update_auth_status(False, "Authentication failed.")

    def fetch_all_videos_from_api(self):
        if not self.service: logger.error("Service not initialized."); messagebox.showerror("Error", "Not authenticated.", parent=self.root); return []
        logger.info("Fetching videos from playlistItems endpoint..."); all_videos_data = []
        load_progress_win = tk.Toplevel(self.root)
        try:
            ch_resp = self.service.channels().list(part="contentDetails", mine=True).execute()
            if not ch_resp.get("items"): raise Exception("Could not determine channel ID.")
            uploads_id = ch_resp["items"][0]["contentDetails"]["relatedPlaylists"].get("uploads")
            if not uploads_id: raise Exception("Could not find uploads playlist ID.")
            logger.info(f"Uploads playlist ID: {uploads_id}")
            next_page_token = None; vid_count = 0; max_vids = 500
            load_progress_win.title("Loading Videos"); load_progress_win.geometry("350x100"); load_progress_win.resizable(False, False); load_progress_win.grab_set(); load_progress_win.transient(self.root)
            ttk.Label(load_progress_win, text="Fetching video list...").pack(pady=5)
            prog_bar = ttk.Progressbar(load_progress_win, orient="horizontal", length=300, mode="indeterminate"); prog_bar.pack(pady=5); prog_bar.start(10)
            self.root.update_idletasks()
            while True:
                # Using playlistItems.list to get videos from the uploads playlist
                req = self.service.playlistItems().list(
                    playlistId=uploads_id,
                    part="snippet,status,contentDetails", # contentDetails for videoId, snippet for title/desc, status for privacy/publishAt
                    maxResults=50,
                    pageToken=next_page_token
                )
                resp = req.execute()
                logger.debug(f"API Response for playlistItems page: {json.dumps(resp, indent=2)}")

                for item in resp.get("items", []):
                    vid_count += 1
                    if item.get("snippet", {}).get("resourceId", {}).get("kind") == "youtube#video":
                        vid_id = item["snippet"]["resourceId"]["videoId"]
                        playlist_item_snippet = item["snippet"] # Snippet of the playlistItem (title, description, thumbnails, videoId)
                        playlist_item_status = item.get("status", {}) # Status of the playlistItem (privacyStatus, publishAt)

                        logger.debug(f"Processing Video ID: {vid_id}, Title from playlistItem: '{playlist_item_snippet.get('title', 'N/A')}'")
                        logger.debug(f"Full playlistItem for {vid_id}: {json.dumps(item, indent=2)}")
                        logger.debug(f"Status object for {vid_id} (from playlistItem.status): {json.dumps(playlist_item_status, indent=2)}")
                        
                        if 'publishAt' in playlist_item_status and playlist_item_status['publishAt']:
                            logger.debug(f"Found 'publishAt' in playlistItem.status for {vid_id}: {playlist_item_status['publishAt']}")
                        else:
                            logger.debug(f"No 'publishAt' or 'publishAt' is empty/None in playlistItem.status for {vid_id}. Keys: {list(playlist_item_status.keys())}")
                        
                        if not playlist_item_status.get("privacyStatus"):
                            logger.warning(f"Video {vid_id} ('{playlist_item_snippet.get('title','NT')}') from playlistItem has no privacyStatus, skipping.")
                            continue
                        
                        # VideoData is initialized with playlistItem's snippet and status
                        all_videos_data.append(VideoData(vid_id, playlist_item_snippet.get("title", "No Title"), playlist_item_snippet, playlist_item_status))
                next_page_token = resp.get("nextPageToken")
                if not next_page_token or (max_vids > 0 and vid_count >= max_vids): break
                load_progress_win.update_idletasks()
            if load_progress_win.winfo_exists(): prog_bar.stop(); load_progress_win.destroy()
            logger.info(f"Fetched {len(all_videos_data)} video items from playlistItems.")
            if not all_videos_data and vid_count == 0: messagebox.showinfo("No Videos", "No videos found in your uploads playlist.", parent=self.root)
            if max_vids > 0 and vid_count >= max_vids and next_page_token: messagebox.showwarning("Scan Limit", f"Loaded the first {max_vids} videos from your channel.", parent=self.root)
        except Exception as e:
            if 'load_progress_win' in locals() and load_progress_win.winfo_exists():
                if 'prog_bar' in locals(): prog_bar.stop()
                load_progress_win.destroy()
            logger.error(f"Error fetching videos: {e}", exc_info=True)
            err_msg = f"Failed to fetch videos: {e}"; specific_handled = False
            if "quotaExceeded" in str(e).lower(): err_msg = f"API Quota Error: {e}"; specific_handled=True
            elif isinstance(e, httplib2.HttpLib2Error) or "timeout" in str(e).lower(): err_msg = f"Network/API Error: {e}. Check internet or API timeout ({API_TIMEOUT_SECONDS}s)."; specific_handled=True
            if not specific_handled and hasattr(e, 'resp') and hasattr(e.resp, 'status') and e.resp.status == 403:
                 try:
                     content = json.loads(e.content.decode())
                     if any("domain Policy" in err.get("reason","") for err in content.get("error",{}).get("errors",[])):
                         err_msg = "API Error: Forbidden by domain policy. This action may be restricted by your Google Workspace administrator."
                 except: pass
            messagebox.showerror("API Error", err_msg, parent=self.root)
            return []
        return all_videos_data

    def gui_load_all_videos(self):
        if not self.service: messagebox.showerror('Error', 'Not authenticated. Please select credentials and authenticate first.', parent=self.root); self.update_auth_status(False, "Auth required."); return
        self.all_channel_videos = self.fetch_all_videos_from_api()
        self.current_filter_applied = "all"; self._populate_treeview(self.all_channel_videos)
        if self.all_channel_videos: messagebox.showinfo("Videos Loaded", f"Loaded {len(self.all_channel_videos)} videos.", parent=self.root)

    def process_scheduling_gui(self):
        sel_items = self.tree.selection()
        if not sel_items: messagebox.showwarning("No Selection", "No videos selected from the list.", parent=self.root); return
        
        vids_to_sched = []
        for item_id_in_tree in sel_items:
            video_id_from_tree = self.tree.item(item_id_in_tree)['values'][0]
            found_vd = next((vd for vd in self.all_channel_videos if vd.video_id == video_id_from_tree), None)
            if found_vd:
                vids_to_sched.append(found_vd)
            else:
                logger.warning(f"Video ID {video_id_from_tree} from tree selection not found in all_channel_videos list. Skipping.")

        if not vids_to_sched: messagebox.showerror("Error", "Selected videos not found in internal list. Please reload the video list.", parent=self.root); return
        
        logger.info(f"Processing {len(vids_to_sched)} videos for scheduling.")
        if not self.service: messagebox.showerror("Auth Error", "Authentication lost or service unavailable. Please re-authenticate.", parent=self.root); self.update_auth_status(False, "Auth required."); return

        title_base = self.title_ent.get().strip()
        desc_base = sanitize_description(self.desc_txt.get('1.0','end-1c').strip())
        tags_str = self.tags_ent.get()
        tags_list_new = []
        if tags_str.strip(): tags_list_new = sanitize_tags([t.strip() for t in tags_str.split(',') if t.strip()])
        
        cat_choice = self.cat_cb.get()
        mfd_choice = self.made_for_kids_cb.get()

        try:
            start_str = self.start_ent.get(); local_dt = datetime.strptime(start_str, '%Y-%m-%d %H:%M')
            try: local_tz = datetime.now().astimezone().tzinfo
            except Exception: local_tz = timezone(timedelta(seconds=-time.timezone if (hasattr(time, "daylight") and time.daylight == 0) else -time.altzone))
            if local_tz is None:
                logger.warning("Could not determine local timezone automatically, using system UTC offset.")
                offset_seconds_obj = datetime.now(timezone.utc).astimezone().utcoffset()
                if offset_seconds_obj: local_tz = timezone(offset_seconds_obj)
                else: local_tz = timezone.utc

            start_utc = local_dt.replace(tzinfo=local_tz).astimezone(timezone.utc)
            if start_utc < datetime.now(timezone.utc) + timedelta(minutes=15): messagebox.showerror("Error", "First publish time must be at least 15 minutes in the future.", parent=self.root); return
            logger.info(f"First video scheduled for (UTC): {start_utc.isoformat()}")
        except ValueError: messagebox.showerror("Error", "Invalid start date/time format. Please use YYYY-MM-DD HH:MM.", parent=self.root); return
        try:
            h = int(self.interval_hour_var.get()); m = int(self.interval_minute_var.get())
            if h < 0 or m < 0: raise ValueError("Interval components cannot be negative.")
            delta = timedelta(hours=h, minutes=m)
            if delta < timedelta(minutes=15) and len(vids_to_sched) > 1:
                 if not messagebox.askyesno("Warning", f"The scheduling interval ({h}h {m}m) is less than 15 minutes. YouTube may enforce a minimum interval. Continue?", parent=self.root): return
            if delta <= timedelta(0) and len(vids_to_sched) > 1:
                logger.warning("Interval was zero or negative for multiple videos. Defaulting to 15 minutes.")
                delta = timedelta(minutes=15)
        except ValueError as e: messagebox.showerror("Error", f"Invalid interval specified: {e}", parent=self.root); return

        curr_pub_utc = start_utc
        for i, vd_obj in enumerate(vids_to_sched):
            # Apply new metadata or keep original from VideoData object's initial state
            vd_obj.title_to_set = title_base if title_base else vd_obj.original_title
            vd_obj.description_to_set = desc_base if desc_base else vd_obj.current_snippet.get('description', '')
            
            if tags_str.strip(): vd_obj.tags_to_set = tags_list_new
            # else: vd_obj.tags_to_set remains as initialized (empty list by default in VideoData)

            if cat_choice != '(Keep Original)': vd_obj.categoryId_to_set = CATEGORY_MAP.get(cat_choice, vd_obj.categoryId_to_set)
            # else: vd_obj.categoryId_to_set remains as initialized

            if mfd_choice != '(Keep Original)': vd_obj.madeForKids_to_set = (mfd_choice == 'Yes')
            # else: vd_obj.madeForKids_to_set remains as initialized (default False in VideoData)

            # Forcing privacy to private for scheduling, then YouTube makes it public at publishAt
            vd_obj.privacyStatus_to_set = 'private'
            vd_obj.publishAt_to_set = curr_pub_utc.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            
            logger.info(f"Video '{vd_obj.original_title}' ({vd_obj.video_id}) will be scheduled for: {vd_obj.publishAt_to_set} with title '{vd_obj.title_to_set}'")
            if i < len(vids_to_sched) - 1:
                curr_pub_utc += delta
                if curr_pub_utc < datetime.now(timezone.utc) + timedelta(minutes=2):
                    logger.warning(f"Calculated next publish time for video {i+2} was too soon. Adjusting.")
                    curr_pub_utc = datetime.now(timezone.utc) + timedelta(minutes=2)
        self.update_videos_on_youtube(vids_to_sched)

    def update_videos_on_youtube(self, videos_to_update):
        if not self.service: messagebox.showerror("Error", "YouTube service unavailable. Please re-authenticate.", parent=self.root); self.update_auth_status(False, "Auth required."); return
        total_processed_or_attempted = len(videos_to_update); succ = 0; fail = 0
        prog_win = tk.Toplevel(self.root); prog_win.title("Scheduling Progress"); prog_win.geometry("450x130"); prog_win.resizable(False, False); prog_win.grab_set(); prog_win.transient(self.root)
        ttk.Label(prog_win, text="Updating videos on YouTube...").pack(pady=5)
        prog_bar = ttk.Progressbar(prog_win, orient="horizontal", length=350, mode="determinate", maximum=total_processed_or_attempted); prog_bar.pack(pady=5)
        prog_label = ttk.Label(prog_win, text="Preparing...", wraplength=400, justify=tk.LEFT); prog_label.pack(pady=5, fill=tk.X, padx=10)

        for i, vd_obj in enumerate(videos_to_update):
            prog_label.config(text=f"({i+1}/{total_processed_or_attempted}) Processing: {vd_obj.title_to_set[:50]}...")
            prog_bar['value'] = i; prog_win.update_idletasks()
            
            # Construct snippet part for video update
            # Note: playlistItem.snippet is NOT the same as video.snippet
            # We are using values prepared in vd_obj (title_to_set, description_to_set, etc.)
            snip_body = {
                'title': vd_obj.title_to_set,
                'description': vd_obj.description_to_set,
                'tags': vd_obj.tags_to_set, # Will be empty list if not set by user
                'categoryId': vd_obj.categoryId_to_set # Will be default if not set by user
            }
            # Optional: Language settings if they were ever populated/set
            if vd_obj.defaultLanguage_to_set: snip_body['defaultLanguage'] = vd_obj.defaultLanguage_to_set
            if vd_obj.videoLanguage_to_set: snip_body['defaultAudioLanguage'] = vd_obj.videoLanguage_to_set
            # Optional: Recording date if ever populated/set
            if vd_obj.recordingDate_to_set:
                snip_body['recordingDetails'] = {'recordingDate': vd_obj.recordingDate_to_set}

            # Construct status part for video update
            stat_body = {
                'privacyStatus': vd_obj.privacyStatus_to_set, # Should be 'private' for scheduling
                'publishAt': vd_obj.publishAt_to_set,
                'selfDeclaredMadeForKids': vd_obj.madeForKids_to_set, # From user choice or VideoData default
                'embeddable': vd_obj.embeddable_to_set, # From VideoData default (True)
                'publicStatsViewable': vd_obj.publicStatsViewable_to_set # From VideoData default (True)
            }
            update_body = {'id': vd_obj.video_id, 'snippet': snip_body, 'status': stat_body}
            logger.info(f"Updating video {vd_obj.video_id}: {json.dumps(update_body, indent=2)}")

            vid_succ = False
            for attempt in range(1, 3):
                try:
                    req = self.service.videos().update(part='snippet,status', body=update_body); resp = req.execute()
                    logger.info(f"Attempt {attempt}: Successfully updated video {resp['id']}.")
                    logger.debug(f"API response from videos().update: {json.dumps(resp, indent=2)}")
                    
                    # Update local VideoData object with the response from the update
                    # The response from videos().update contains the full video snippet and status
                    vd_obj.current_snippet = resp.get('snippet', vd_obj.current_snippet) # Now holds actual video snippet
                    vd_obj.current_status = resp.get('status', vd_obj.current_status) # Now holds actual video status
                    vd_obj.original_title = vd_obj.title_to_set # Reflects the title that was set
                    vid_succ = True; break
                except Exception as e:
                    logger.error(f"Attempt {attempt} failed for video {vd_obj.video_id} ('{vd_obj.title_to_set}'): {e}", exc_info=True)
                    err_details = str(e)
                    if hasattr(e, 'content'):
                        try: err_details = json.loads(e.content.decode()).get("error", {}).get("message", str(e))
                        except: pass
                    prog_label.config(text=f"({i+1}/{total_processed_or_attempted}) Error (Attempt {attempt}): {vd_obj.title_to_set[:30]}... {err_details[:60]}")
                    prog_win.update_idletasks()
                    if attempt < 2:
                        if not messagebox.askretrycancel("Update Error", f"Failed to update: {vd_obj.title_to_set}\nError: {err_details}\n\nDo you want to retry this video?", parent=prog_win):
                            if not messagebox.askyesno("Skip Video", "Retry was cancelled for this video.\nSkip this video and continue with the rest?", parent=prog_win):
                                logger.info("User cancelled remaining updates."); fail += (total_processed_or_attempted - i)
                                if prog_win.winfo_exists(): prog_win.destroy()
                                messagebox.showinfo("Updates Cancelled", f"Video updates cancelled by user.\nSucceeded: {succ}, Failed/Skipped: {fail}", parent=self.root)
                                if succ > 0:
                                    logger.info("Refreshing treeview from local data after cancellation with some successes.")
                                    self.apply_filter_to_treeview(self.current_filter_applied)
                                return
                            else:
                                logger.info(f"User skipped video {vd_obj.video_id} after failed attempt.")
                                break
                    else:
                        messagebox.showerror("Retry Failed", f"Retry also failed for: {vd_obj.title_to_set}\nError: {err_details}\nSkipping this video.", parent=prog_win)
            if vid_succ: succ += 1
            else: fail += 1
            prog_bar['value'] = i + 1; prog_win.update_idletasks()

        if prog_win.winfo_exists(): prog_win.destroy()

        base_summary = f"Scheduling process complete.\nSuccessfully updated: {succ}\nFailed/Skipped: {fail}"
        logger.info(base_summary.replace("\n", " "))

        if total_processed_or_attempted > 0:
            full_summary = f"{base_summary}\n\nThe list below has been updated based on these actions." \
                           "\nTo perform a full refresh from YouTube, please use the 'Load/Refresh My Videos' button."
            messagebox.showinfo("Process Complete", full_summary, parent=self.root)
            logger.info("Refreshing treeview from (potentially updated) local data. Not fetching from API.")
            self.apply_filter_to_treeview(self.current_filter_applied) # This will use updated vd_obj.current_status
        else:
            messagebox.showinfo("Process Complete", base_summary, parent=self.root)


    def on_exit(self):
        logger.info("Application exiting...")
        global file_log_handler_global, console_handler

        if not self.save_log_var.get() and file_log_handler_global:
            logger.info(f"Log saving to '{LOG_FILE}' is disabled. Removing log file.")
            logger.removeHandler(file_log_handler_global)
            file_log_handler_global.close()
            file_log_handler_global = None
            try:
                if os.path.exists(LOG_FILE):
                    os.remove(LOG_FILE)
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] Log file '{LOG_FILE}' deleted.")
            except OSError as e:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [WARNING] Could not delete log file '{LOG_FILE}': {e}")
        elif file_log_handler_global:
            logger.info(f"Log data will be saved to {LOG_FILE}.")
            file_log_handler_global.flush()
            file_log_handler_global.close()
            logger.removeHandler(file_log_handler_global)
            file_log_handler_global = None

        if self.root and self.root.winfo_exists():
            try:
                self.root.destroy()
                logger.info("Tkinter root destroyed.")
            except tk.TclError as e:
                logger.warning(f"Error destroying Tkinter root (may already be gone): {e}", exc_info=True)
            except Exception as e:
                logger.error(f"Unexpected error destroying Tkinter root: {e}", exc_info=True)

        for handler in list(logger.handlers):
            try:
                handler.close()
                logger.removeHandler(handler)
            except Exception as e:
                print(f"Error closing/removing handler during final exit: {e}")

        logger.info("Exit procedure finished.")
        if console_handler:
             # Check if console_handler is still in logger.handlers before trying to flush/close again
            if not any(h is console_handler for h in logger.handlers): # Check if it was removed
                 pass # Already removed and closed
            else:
                try:
                    console_handler.flush()
                    # console_handler.close() # Typically not closed for sys.stdout
                    # logger.removeHandler(console_handler) # Optional, as app is exiting
                except Exception as e:
                    print(f"Error flushing console_handler: {e}")


if __name__ == '__main__':
    try:
        app = SchedulerApp()
    except Exception as e:
        print(f"FATAL ERROR during application startup: {e}", file=sys.stderr)
        # BasicConfig for last-ditch logging if primary logger setup failed
        logging.basicConfig(filename=LOG_FILE, level=logging.DEBUG, filemode='a',
                            format="[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        logging.critical(f"Fatal error during application startup: {e}", exc_info=True)
        try:
            root_for_error = tk.Tk()
            root_for_error.withdraw()
            messagebox.showerror("Fatal Error", f"Application failed to start: {e}\nCheck {LOG_FILE} for details if created.", parent=root_for_error)
            root_for_error.destroy()
        except tk.TclError:
            print(f"FATAL ERROR (GUI could not display): Application failed to start: {e}\nCheck {LOG_FILE} for details.", file=sys.stderr)
        sys.exit(1)