import os
import sys
import json
import signal
import atexit
import re
import logging
from pathlib import Path
from datetime import datetime, timedelta, timezone
import glob
import requests

from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# --- Constants ---
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube"
]
TOKEN_FILE = "token.json"
LOG_FILE = "ytupload.log"
OAUTH_PORT = 8080
VIDEO_PATTERNS = ["*.mp4", "*.mkv", "*.avi"]

CATEGORY_MAP = {
    "Film & Animation": "1", "Autos & Vehicles": "2", "Music": "10",
    "Pets & Animals": "15", "Sports": "17", "Travel & Events": "19",
    "Gaming": "20", "People & Blogs": "22", "Comedy": "23",
    "Entertainment": "24", "News & Politics": "25", "Howto & Style": "26",
    "Education": "27", "Science & Technology": "28", "Nonprofits & Activism": "29"
}
LANGUAGES = {"English": "en", "Spanish": "es", "French": "fr", "German": "de", "Japanese": "ja", "Chinese": "zh"}

# --- Logger (in-memory) ---
logger = logging.getLogger("ytupload")
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
        try:
            data = json.load(open(TOKEN_FILE))
            if 'refresh_token' in data:
                requests.post(
                    'https://oauth2.googleapis.com/revoke',
                    params={'token': data['refresh_token']},
                    headers={'content-type': 'application/x-www-form-urlencoded'}
                )
        except: pass
        try: os.remove(TOKEN_FILE)
        except: pass

def setup_revocation_on_exit():
    atexit.register(revoke_token)
    def on_sig(signum, frame):
        revoke_token()
        sys.exit(1)
    signal.signal(signal.SIGINT, on_sig)

# --- OAuth Authentication ---
def get_authenticated_service(secrets_path):
    from oauthlib.oauth2.rfc6749.errors import MismatchingStateError
    creds = None
    if Path(TOKEN_FILE).exists():
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(secrets_path, SCOPES)
            try:
                creds = flow.run_local_server(port=OAUTH_PORT, open_browser=True)
            except MismatchingStateError:
                creds = flow.run_local_server(port=OAUTH_PORT, open_browser=True)
            except Exception:
                creds = flow.run_console()
        with open(TOKEN_FILE, 'w') as f:
            f.write(creds.to_json())
    return build('youtube', 'v3', credentials=creds)

# --- Helpers ---
def sanitize_filename(name):
    stem = Path(name).stem
    s = re.sub(r"[^A-Za-z0-9 ]+", "", stem)
    return re.sub(r"\s+", " ", s).strip()

# --- Video Data Model ---
class VideoEntry:
    def __init__(self, filepath):
        p = Path(filepath)
        clean = sanitize_filename(p.name)
        new_path = p.with_name(f"{clean}{p.suffix}")
        if p.name != new_path.name:
            os.rename(p, new_path)
        self.filepath = str(new_path)
        self.title = sanitize_filename(new_path.stem)
        self.description = ''
        self.tags = []
        self.categoryId = CATEGORY_MAP['Entertainment']
        self.videoLanguage = 'en'
        self.defaultLanguage = 'en'
        self.recordingDate = None
        self.notifySubscribers = False
        self.madeForKids = False
        self.embeddable = True
        self.publicStatsViewable = False
        self.playlistId = ''
        self.publishAt = None

# --- Main Application ---
class UploaderApp:
    def __init__(self):
        setup_revocation_on_exit()
        self.client_secrets = None
        try: os.remove(LOG_FILE)
        except: pass
        # Auto-scan videos
        self.video_entries = []
        for pat in VIDEO_PATTERNS:
            for f in glob.glob(pat):
                if f not in [v.filepath for v in self.video_entries]:
                    self.video_entries.append(VideoEntry(f))
        self.root = tk.Tk()
        self.save_log_var = tk.BooleanVar(master=self.root, value=False)
        self.root.title('YouTube Batch Uploader')
        self.build_gui()
        self.root.mainloop()

    def build_gui(self):
        frm = ttk.Frame(self.root, padding=10)
        frm.pack(fill=tk.BOTH, expand=True)
        ttk.Button(frm, text='Select Credentials JSON', command=self.select_credentials).pack(fill=tk.X, pady=(0,5))
        self.tree = ttk.Treeview(frm, columns=('file','title'), show='headings')
        self.tree.heading('file', text='File'); self.tree.heading('title', text='Title')
        self.tree.pack(fill=tk.BOTH, expand=True, pady=5)
        self.refresh_tree()
        sched = ttk.LabelFrame(frm, text='Schedule & Interval', padding=10)
        sched.pack(fill=tk.X, pady=5)
        ttk.Label(sched, text='First Publish (YYYY-MM-DD HH:MM)').grid(row=0, column=0)
        self.start_ent = ttk.Entry(sched); self.start_ent.insert(0, datetime.now().astimezone().strftime('%Y-%m-%d %H:%M')); self.start_ent.grid(row=0, column=1)
        ttk.Label(sched, text='Interval Hours').grid(row=1, column=0) ; self.interval_hour = ttk.Spinbox(sched, from_=0, to=168, width=5); self.interval_hour.set(1); self.interval_hour.grid(row=1, column=1)
        ttk.Label(sched, text='Interval Minutes').grid(row=2, column=0); self.interval_minute = ttk.Spinbox(sched, from_=0, to=59, width=5); self.interval_minute.set(0); self.interval_minute.grid(row=2, column=1)
        meta = ttk.LabelFrame(frm, text='Metadata Defaults', padding=10)
        meta.pack(fill=tk.X, pady=5)
        ttk.Label(meta, text='Description').grid(row=0, column=0); self.desc_txt = tk.Text(meta, height=3); self.desc_txt.grid(row=0, column=1, sticky='ew')
        ttk.Label(meta, text='Tags').grid(row=1, column=0); self.tags_ent = ttk.Entry(meta); self.tags_ent.grid(row=1, column=1, sticky='ew')
        ttk.Label(meta, text='Category').grid(row=2, column=0); self.cat_cb = ttk.Combobox(meta, values=list(CATEGORY_MAP.keys())); self.cat_cb.set('Entertainment'); self.cat_cb.grid(row=2, column=1, sticky='ew')
        ttk.Label(meta, text='Video Lang').grid(row=3, column=0); self.vlang_cb = ttk.Combobox(meta, values=list(LANGUAGES.keys())); self.vlang_cb.set('English'); self.vlang_cb.grid(row=3, column=1, sticky='ew')
        ttk.Label(meta, text='Default Lang').grid(row=4, column=0); self.dlang_cb = ttk.Combobox(meta, values=list(LANGUAGES.keys())); self.dlang_cb.set('English'); self.dlang_cb.grid(row=4, column=1, sticky='ew')
        ttk.Label(meta, text='Recording Date (UTC)').grid(row=5, column=0); self.rec_ent = ttk.Entry(meta); self.rec_ent.insert(0, datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')); self.rec_ent.grid(row=5, column=1, sticky='ew')
        self.notify_var = tk.BooleanVar(value=False); ttk.Checkbutton(meta, text='Notify Subscribers', variable=self.notify_var).grid(row=6, column=0, sticky='w')
        self.kids_var = tk.BooleanVar(value=False); ttk.Checkbutton(meta, text='Made for Kids', variable=self.kids_var).grid(row=7, column=0, sticky='w')
        self.embed_var = tk.BooleanVar(value=True); ttk.Checkbutton(meta, text='Embeddable', variable=self.embed_var).grid(row=8, column=0, sticky='w')
        self.stats_var = tk.BooleanVar(value=False); ttk.Checkbutton(meta, text='Public Stats Visible', variable=self.stats_var).grid(row=9, column=0, sticky='w')
        ttk.Label(meta, text='Playlist ID').grid(row=10, column=0); self.playlist_ent = ttk.Entry(meta); self.playlist_ent.grid(row=10, column=1, sticky='ew')
        btn_frm = ttk.Frame(frm); btn_frm.pack(fill=tk.X, pady=5)
        ttk.Button(btn_frm, text='Save Settings', command=self.save_settings).pack(side=tk.LEFT)
        ttk.Button(btn_frm, text='Load Settings', command=self.load_settings).pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(frm, text='Save Log File', variable=self.save_log_var).pack(anchor='w', pady=5)
        ttk.Button(frm, text='Process & Upload', command=self.process_upload).pack(pady=10)

    def refresh_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for e in self.video_entries:
            self.tree.insert('', tk.END, values=(Path(e.filepath).name, e.title))

    def select_credentials(self):
        path = filedialog.askopenfilename(title='Select credentials JSON', filetypes=[('JSON','*.json')])
        if path:
            self.client_secrets = path
            logger.info(f'Selected credentials: {path}')

    def save_settings(self):
        cfg = {
            'description': self.desc_txt.get('1.0','end'),
            'tags': self.tags_ent.get(),
            'category': self.cat_cb.get(),
            'videoLang': self.vlang_cb.get(),
            'defaultLang': self.dlang_cb.get(),
            'recordingDate': self.rec_ent.get(),
            'notify': self.notify_var.get(),
            'madeForKids': self.kids_var.get(),
            'embeddable': self.embed_var.get(),
            'publicStatsVisible': self.stats_var.get(),
            'playlistId': self.playlist_ent.get(),
            'firstPublish': self.start_ent.get(),
            'intervalHours': self.interval_hour.get(),
            'intervalMinutes': self.interval_minute.get(),
            'saveLog': self.save_log_var.get()
        }
        f = filedialog.asksaveasfilename(defaultextension='.json', filetypes=[('JSON','*.json')])
        if f:
            with open(f,'w') as out: json.dump(cfg,out)
            messagebox.showinfo('Saved','Settings saved')

    def load_settings(self):
        f = filedialog.askopenfilename(filetypes=[('JSON','*.json')])
        if f:
            with open(f) as inp: cfg = json.load(inp)
            self.desc_txt.delete('1.0','end'); self.desc_txt.insert('1.0', cfg.get('description',''))
            self.tags_ent.delete(0, tk.END); self.tags_ent.insert(0, cfg.get('tags',''))
            self.cat_cb.set(cfg.get('category','Entertainment'))
            self.vlang_cb.set(cfg.get('videoLang','English'))
            self.dlang_cb.set(cfg.get('defaultLang','English'))
            self.rec_ent.delete(0, tk.END); self.rec_ent.insert(0, cfg.get('recordingDate',''))
            self.notify_var.set(cfg.get('notify',False))
            self.kids_var.set(cfg.get('madeForKids',False))
            self.embed_var.set(cfg.get('embeddable',True))
            self.stats_var.set(cfg.get('publicStatsVisible',False))
            self.playlist_ent.delete(0, tk.END); self.playlist_ent.insert(0, cfg.get('playlistId',''))
            self.start_ent.delete(0, tk.END); self.start_ent.insert(0, cfg.get('firstPublish',''))
            self.interval_hour.set(cfg.get('intervalHours',1))
            self.interval_minute.set(cfg.get('intervalMinutes',0))
            self.save_log_var.set(cfg.get('saveLog',False))
            messagebox.showinfo('Loaded','Settings loaded')

    def process_upload(self):
        if not self.client_secrets:
            messagebox.showerror('Error','No credentials selected'); return
        # read GUI values
        desc = self.desc_txt.get('1.0','end').strip()
        tags = [t.strip() for t in self.tags_ent.get().split(',') if t.strip()]
        cat = CATEGORY_MAP.get(self.cat_cb.get(), '24')
        vlang = LANGUAGES.get(self.vlang_cb.get(), 'en')
        dlang = LANGUAGES.get(self.dlang_cb.get(), 'en')
        rec = self.rec_ent.get().strip()
        notify = self.notify_var.get()
        kids = self.kids_var.get()
        embed = self.embed_var.get()
        stats = self.stats_var.get()
        playlist_id = self.playlist_ent.get().strip()
        base_time = self.start_ent.get()
        hrs = int(self.interval_hour.get()); mins = int(self.interval_minute.get())
        # authenticate
        try:
            service = get_authenticated_service(self.client_secrets)
        except Exception as auth_ex:
            messagebox.showerror('Auth Error', f'Authentication failed: {auth_ex}')
            return
        # close GUI
        self.root.destroy()
        # parse start time
        try:
            loc = datetime.strptime(base_time, '%Y-%m-%d %H:%M')
            loc_tz = datetime.now().astimezone().tzinfo
            utc_dt = loc.replace(tzinfo=loc_tz).astimezone(timezone.utc)
        except:
            utc_dt = datetime.now(timezone.utc)
        # assign metadata and publishAt
        for i, e in enumerate(self.video_entries):
            e.description, e.tags, e.categoryId = desc, tags, cat
            e.videoLanguage, e.defaultLanguage = vlang, dlang
            e.recordingDate = rec
            e.notifySubscribers, e.madeForKids = notify, kids
            e.embeddable, e.publicStatsViewable = embed, stats
            e.playlistId = playlist_id
            delta = timedelta(hours=hrs, minutes=mins) * i
            e.publishAt = (utc_dt + delta).strftime('%Y-%m-%dT%H:%M:%SZ')
        # upload
        self.upload_all(service)

    def upload_all(self, service):
        for e in self.video_entries:
            media = MediaFileUpload(e.filepath, chunksize=-1, resumable=True)
            body = {'snippet': {'title': e.title, 'description': e.description, 'tags': e.tags, 'categoryId': e.categoryId, 'defaultLanguage': e.defaultLanguage, 'defaultAudioLanguage': e.videoLanguage, 'recordingDetails': {'recordingDate': e.recordingDate}}, 'status': {'privacyStatus': 'private', 'publishAt': e.publishAt, 'selfDeclaredMadeForKids': e.madeForKids, 'license': 'youtube', 'embeddable': e.embeddable, 'publicStatsViewable': e.publicStatsViewable}}
            req = service.videos().insert(part='snippet,status', body=body, media_body=media, notifySubscribers=e.notifySubscribers)
            print(f"Uploading {Path(e.filepath).name}", flush=True)
            status = None; resp = None
            while resp is None:
                status, resp = req.next_chunk()
                if status:
                    print(f"  {int(status.progress()*100)}%", flush=True)
            vid = resp['id']; print(f"Done: https://youtu.be/{vid}", flush=True)
            logger.info(f"Uploaded {e.filepath} -> {vid}")
            if e.playlistId:
                try:
                    service.playlistItems().insert(part='snippet', body={'snippet': {'playlistId': e.playlistId, 'resourceId': {'kind': 'youtube#video', 'videoId': vid}}}).execute()
                    print(f"  Added to playlist {e.playlistId}", flush=True)
                    logger.info(f"Added {vid} to playlist {e.playlistId}")
                except Exception as ex:
                    print(f"  Playlist add failed: {ex}", flush=True)
                    logger.error(f"Playlist error for {vid}: {ex}")
        if self.save_log_var.get():
            with open(LOG_FILE, 'w') as f:
                f.write("\n".join(log_records))
        revoke_token()

if __name__ == '__main__':
    UploaderApp()