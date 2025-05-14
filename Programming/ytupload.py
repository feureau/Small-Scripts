import os
import sys
import json
import signal
import atexit
import requests
import logging
from pathlib import Path
from datetime import datetime, timedelta
import glob
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# Constants
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CLIENT_SECRETS_FILE = None  # set via GUI file picker
TOKEN_FILE = 'token.json'
LOG_FILE = 'ytupload.log'

# Configure logging
logging.basicConfig(
    filename=LOG_FILE,
    filemode='a',
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Revocation logic

def revoke_token(token_path=TOKEN_FILE):
    if not os.path.exists(token_path):
        return
    logging.info(f"Revoking token file: {token_path}")
    try:
        data = json.load(open(token_path))
        refresh_token = data.get('refresh_token')
        if refresh_token:
            resp = requests.post(
                'https://oauth2.googleapis.com/revoke',
                params={'token': refresh_token},
                headers={'content-type': 'application/x-www-form-urlencoded'}
            )
            if resp.status_code == 200:
                logging.info('Refresh token successfully revoked.')
            else:
                logging.warning(f'Failed to revoke token: {resp.text}')
    except Exception as e:
        logging.error(f"Error revoking token: {e}")
    try:
        os.remove(token_path)
        logging.info(f"Deleted token file: {token_path}")
    except OSError as e:
        logging.warning(f"Could not delete token file: {e}")


def setup_revocation_on_exit():
    atexit.register(lambda: revoke_token())
    def handle_sigint(signum, frame):
        logging.info('Interrupted by user, revoking token')
        revoke_token()
        sys.exit(1)
    signal.signal(signal.SIGINT, handle_sigint)

# YouTube API client

def get_authenticated_service():
    if CLIENT_SECRETS_FILE is None:
        raise RuntimeError('Client secrets file not set')
    creds = None
    if Path(TOKEN_FILE).exists():
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        logging.info(f"Loaded existing token: {TOKEN_FILE}")
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logging.info('Access token expired, refreshing...')
            creds.refresh(Request())
            logging.info('Token refreshed successfully')
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRETS_FILE, SCOPES)
            # Use console flow for manual browser/account control
            if hasattr(flow, 'run_console'):
                creds = flow.run_console()
            else:
                print('Opening browser for authentication...')
                creds = flow.run_local_server()
            logging.info('Obtained new credentials via OAuth flow')
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
            logging.info(f"Saved token to {TOKEN_FILE}")
    youtube = build('youtube', 'v3', credentials=creds)
    try:
        response = youtube.channels().list(part='snippet', mine=True).execute()
        channel_title = response['items'][0]['snippet']['title']
        logging.info(f"Authenticated to channel: {channel_title}")
        print(f"✅ Authenticated to channel: {channel_title}")
    except Exception as e:
        logging.warning(f"Could not confirm channel: {e}")
    return youtube

# Data model for each video

class VideoRow:
    def __init__(self, filepath):
        self.filepath = filepath
        self.title = Path(filepath).stem
        self.publish_at = None

# GUI for batch upload

class UploadGUI:
    def __init__(self, video_paths):
        self.videos = [VideoRow(p) for p in video_paths]
        self.start_time = datetime.now()
        self.interval_hours = 1
        logging.info(f"Starting GUI with {len(self.videos)} videos")
        self.root = tk.Tk()
        self.root.title('YouTube Batch Uploader')
        self.build_ui()

    def build_ui(self):
        frm = ttk.Frame(self.root, padding=10)
        frm.pack(fill=tk.BOTH, expand=True)

        cred_btn = ttk.Button(frm, text='Select client_secrets.json', command=self.pick_credentials)
        cred_btn.pack(fill=tk.X, pady=(0,10))

        cols = ('title', 'publish_at')
        self.tree = ttk.Treeview(frm, columns=cols, show='headings')
        self.tree.heading('title', text='Title')
        self.tree.heading('publish_at', text='Publish At')
        for v in self.videos:
            self.tree.insert('', tk.END, values=(v.title, ''))
        self.tree.pack(fill=tk.BOTH, expand=True, pady=10)

        settings = ttk.LabelFrame(frm, text='Global Settings', padding=10)
        settings.pack(fill=tk.X, pady=5)

        ttk.Label(settings, text='First Publish (YYYY-MM-DD HH:MM)').grid(row=0, column=0)
        self.start_entry = ttk.Entry(settings)
        self.start_entry.insert(0, self.start_time.strftime('%Y-%m-%d %H:%M'))
        self.start_entry.grid(row=0, column=1, padx=5)

        ttk.Label(settings, text='Interval (hours)').grid(row=1, column=0)
        self.interval_entry = ttk.Spinbox(settings, from_=1, to=168, width=5)
        self.interval_entry.set(self.interval_hours)
        self.interval_entry.grid(row=1, column=1, sticky=tk.W)

        apply_btn = ttk.Button(settings, text='Apply Schedule to All', command=self.apply_schedule)
        apply_btn.grid(row=2, column=0, columnspan=2, pady=5)

        upload_btn = ttk.Button(frm, text='Start Upload', command=self.on_start)
        upload_btn.pack(pady=10)

    def pick_credentials(self):
        global CLIENT_SECRETS_FILE
        path = filedialog.askopenfilename(
            title='Select client_secrets.json',
            filetypes=[('JSON files', '*.json')]
        )
        if path:
            CLIENT_SECRETS_FILE = path
            logging.info(f"Selected credentials file: {path}")
            messagebox.showinfo('Credentials Selected', f'Selected: {path}')

    def apply_schedule(self):
        try:
            dt = datetime.strptime(self.start_entry.get(), '%Y-%m-%d %H:%M')
            interval = int(self.interval_entry.get())
        except Exception as e:
            messagebox.showerror('Invalid input', f'Error parsing date/time or interval: {e}')
            return
        for idx, v in enumerate(self.videos):
            v.publish_at = dt + timedelta(hours=interval * idx)
            self.tree.set(self.tree.get_children()[idx], 'publish_at', v.publish_at.strftime('%Y-%m-%dT%H:%M:%SZ'))
        logging.info('Applied schedule to all videos')

    def on_start(self):
        if CLIENT_SECRETS_FILE is None:
            messagebox.showerror('Missing Credentials', 'Please select client_secrets.json before uploading.')
            return
        self.root.destroy()
        self.upload_all()

    def upload_all(self):
        youtube = get_authenticated_service()
        for v in self.videos:
            logging.info(f"Uploading {v.filepath} scheduled at {v.publish_at}")
            body = {
                'snippet': {'title': v.title},
                'status': {'privacyStatus': 'private', 'publishAt': v.publish_at.strftime('%Y-%m-%dT%H:%M:%SZ')}
            }
            request = youtube.videos().insert(
                part=','.join(body.keys()),
                body=body,
                media_body=v.filepath,
                notifySubscribers=False
            )
            try:
                response = request.execute()
                logging.info(f"Success: {v.filepath} -> https://youtu.be/{response['id']}")
            except Exception as e:
                logging.error(f"Failed upload {v.filepath}: {e}")
        logging.info('All uploads complete')
        revoke_token()
        logging.info('Session complete, exiting')


def main():
    if len(sys.argv) < 2:
        print('Usage: python ytupload.py <video_pattern1> [pattern2 ...]')
        sys.exit(1)
    patterns = sys.argv[1:]
    video_paths = []
    for pat in patterns:
        video_paths.extend(glob.glob(pat, recursive=True))
    video_paths = list(dict.fromkeys(video_paths))
    if not video_paths:
        print('No video files found for given patterns.')
        sys.exit(1)
    setup_revocation_on_exit()
    UploadGUI(video_paths).root.mainloop()

if __name__ == '__main__':
    main()
