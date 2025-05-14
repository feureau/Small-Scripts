import os
import sys
import json
import signal
import atexit
import re
import requests
import logging
from pathlib import Path
from datetime import datetime, timedelta, timezone
import glob
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# Constants
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly"
]
TOKEN_FILE = 'token.json'
LOG_FILE = 'ytupload.log'
OAUTH_PORT = 8080
VIDEO_PATTERNS = ['*.mp4', '*.mkv', '*.avi']

CATEGORY_MAP = {
    'Film & Animation': '1',
    'Autos & Vehicles': '2',
    'Music': '10',
    'Pets & Animals': '15',
    'Sports': '17',
    'Travel & Events': '19',
    'Gaming': '20',
    'People & Blogs': '22',
    'Comedy': '23',
    'Entertainment': '24',
    'News & Politics': '25',
    'Howto & Style': '26',
    'Education': '27',
    'Science & Technology': '28',
    'Nonprofits & Activism': '29'
}
LANGUAGES = {
    'English': 'en',
    'Spanish': 'es',
    'French': 'fr',
    'German': 'de',
    'Japanese': 'ja',
    'Chinese': 'zh'
}
LICENSE_OPTIONS = {'YouTube Standard': 'youtube', 'Creative Commons': 'creativeCommon'}

# Logging config
logging.basicConfig(
    filename=LOG_FILE,
    filemode='a',
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

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
        except Exception:
            pass
        try:
            os.remove(TOKEN_FILE)
        except Exception:
            pass


def setup_revocation_on_exit():
    atexit.register(revoke_token)
    def on_sigint(signum, frame):
        revoke_token()
        sys.exit(1)
    signal.signal(signal.SIGINT, on_sigint)

# OAuth

def get_authenticated_service(client_secrets_path):
    creds = None
    if Path(TOKEN_FILE).exists():
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(client_secrets_path, SCOPES)
            try:
                creds = flow.run_local_server(port=OAUTH_PORT, open_browser=True)
            except Exception:
                creds = flow.run_console()
        with open(TOKEN_FILE, 'w') as f:
            f.write(creds.to_json())
    return build('youtube', 'v3', credentials=creds)

# sanitize

def sanitize_filename(name):
    stem = Path(name).stem
    s = re.sub(r'[^A-Za-z0-9 ]+', '', stem)
    return re.sub(r'\s+', ' ', s).strip()

# video model
class VideoEntry:
    def __init__(self, filepath):
        p = Path(filepath)
        clean = sanitize_filename(p.name)
        new_name = f"{clean}{p.suffix}"
        new_path = p.with_name(new_name)
        if p.name != new_name:
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
        self.license = 'youtube'
        self.embeddable = True
        self.publicStatsViewable = False
        self.publishAt = None

class UploaderApp:
    def __init__(self):
        setup_revocation_on_exit()
        self.client_secrets = None
        # scan videos
        self.video_entries = []
        for pat in VIDEO_PATTERNS:
            for f in glob.glob(pat):
                if f not in [v.filepath for v in self.video_entries]:
                    self.video_entries.append(VideoEntry(f))
        self.root = tk.Tk()
        self.root.title('YouTube Batch Uploader')
        self.build_gui()
        self.root.mainloop()

    def build_gui(self):
        frm = ttk.Frame(self.root, padding=10)
        frm.pack(fill=tk.BOTH, expand=True)
        # creds
        ttk.Button(frm, text='Select Credentials JSON', command=self.select_credentials).pack(fill=tk.X)
        # list
        self.tree = ttk.Treeview(frm, columns=('file','title'), show='headings')
        self.tree.heading('file', text='File')
        self.tree.heading('title', text='Title')
        self.tree.pack(fill=tk.BOTH, expand=True, pady=5)
        self.refresh_tree()
        # metadata defaults
        meta = ttk.LabelFrame(frm, text='Metadata Defaults', padding=10)
        meta.pack(fill=tk.X)
        ttk.Label(meta, text='Description').grid(row=0,column=0)
        self.desc_txt = tk.Text(meta, height=3)
        self.desc_txt.grid(row=0,column=1,sticky='ew')
        ttk.Label(meta, text='Tags (comma)').grid(row=1,column=0)
        self.tags_ent = ttk.Entry(meta)
        self.tags_ent.grid(row=1,column=1,sticky='ew')
        ttk.Label(meta, text='Category').grid(row=2,column=0)
        self.cat_cb = ttk.Combobox(meta,values=list(CATEGORY_MAP.keys()))
        self.cat_cb.set('Entertainment')
        self.cat_cb.grid(row=2,column=1,sticky='ew')
        ttk.Label(meta, text='Video Lang').grid(row=3,column=0)
        self.vlang_cb = ttk.Combobox(meta,values=list(LANGUAGES.keys()))
        self.vlang_cb.set('English')
        self.vlang_cb.grid(row=3,column=1,sticky='ew')
        ttk.Label(meta, text='Default Lang').grid(row=4,column=0)
        self.dlang_cb = ttk.Combobox(meta,values=list(LANGUAGES.keys()))
        self.dlang_cb.set('English')
        self.dlang_cb.grid(row=4,column=1,sticky='ew')
        ttk.Label(meta, text='Recording Date').grid(row=5,column=0)
        self.rec_ent = ttk.Entry(meta)
        self.rec_ent.insert(0,datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))
        self.rec_ent.grid(row=5,column=1,sticky='ew')
        self.notify_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(meta,text='Notify Subscribers',variable=self.notify_var).grid(row=6,column=1,sticky='w')
        self.kids_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(meta,text='Made for Kids',variable=self.kids_var).grid(row=7,column=1,sticky='w')
        ttk.Label(meta,text='License').grid(row=8,column=0)
        self.lic_cb=ttk.Combobox(meta,values=list(LICENSE_OPTIONS.keys()))
        self.lic_cb.set('YouTube Standard')
        self.lic_cb.grid(row=8,column=1,sticky='ew')
        self.embed_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(meta,text='Embeddable',variable=self.embed_var).grid(row=9,column=1,sticky='w')
        self.stats_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(meta,text='Public Stats Visible',variable=self.stats_var).grid(row=10,column=1,sticky='w')
        # schedule
        sched=ttk.LabelFrame(frm,text='Schedule',padding=10)
        sched.pack(fill=tk.X,pady=5)
        ttk.Label(sched,text='First Publish (YYYY-MM-DD HH:MM)').grid(row=0,column=0)
        self.start_ent=ttk.Entry(sched)
        self.start_ent.insert(0,datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M'))
        self.start_ent.grid(row=0,column=1,sticky='w')
        # process
        ttk.Button(frm,text='Process & Upload',command=self.process_upload).pack(pady=10)

    def refresh_tree(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        for e in self.video_entries:
            self.tree.insert('',tk.END,values=(Path(e.filepath).name,e.title))

    def select_credentials(self):
        path=filedialog.askopenfilename(title='Select credentials JSON',filetypes=[('JSON','*.json')])
        if path:
            self.client_secrets=path
            logging.info(f"Selected credentials: {path}")

    def process_upload(self):
        if not getattr(self,'client_secrets',None):
            messagebox.showerror('Error','No credentials selected')
            return
        try:
            base_dt=datetime.strptime(self.start_ent.get(),'%Y-%m-%d %H:%M')
            base_dt=base_dt.replace(tzinfo=timezone.utc)
        except:
            base_dt=datetime.now(timezone.utc)
        # defaults
        desc=self.desc_txt.get('1.0','end').strip()
        tags=[t.strip() for t in self.tags_ent.get().split(',') if t.strip()]
        cat=CATEGORY_MAP.get(self.cat_cb.get(),'24')
        vlang=LANGUAGES.get(self.vlang_cb.get(),'en')
        dlang=LANGUAGES.get(self.dlang_cb.get(),'en')
        rec=self.rec_ent.get().strip()
        notify=self.notify_var.get()
        kids=self.kids_var.get()
        lic=LICENSE_OPTIONS.get(self.lic_cb.get(),'youtube')
        embed=self.embed_var.get()
        stats=self.stats_var.get()
        for i,e in enumerate(self.video_entries):
            e.description=desc
            e.tags=tags
            e.categoryId=cat
            e.videoLanguage=vlang
            e.defaultLanguage=dlang
            e.recordingDate=rec
            e.notifySubscribers=notify
            e.madeForKids=kids
            e.license=lic
            e.embeddable=embed
            e.publicStatsViewable=stats
            dt=base_dt+timedelta(hours=i+1)
            e.publishAt=dt.strftime('%Y-%m-%dT%H:%M:%SZ')
        self.root.destroy()
        self.upload_all()

    def upload_all(self):
        service=get_authenticated_service(self.client_secrets)
        for e in self.video_entries:
            media=MediaFileUpload(e.filepath,chunksize=-1,resumable=True)
            body={'snippet':{'title':e.title,'description':e.description,'tags':e.tags,'categoryId':e.categoryId,
                    'defaultLanguage':e.defaultLanguage,'defaultAudioLanguage':e.videoLanguage,
                    'recordingDetails':{'recordingDate':e.recordingDate}},
                  'status':{'privacyStatus':'private','publishAt':e.publishAt,
                    'selfDeclaredMadeForKids':e.madeForKids,'license':e.license,
                    'embeddable':e.embeddable,'publicStatsViewable':e.publicStatsViewable}}
            request=service.videos().insert(part=','.join(body.keys()),body=body,media_body=media,notifySubscribers=e.notifySubscribers)
            print(f"Uploading {Path(e.filepath).name}",flush=True)
            status=None;response=None
            while response is None:
                status,response=request.next_chunk()
                if status: print(f"  {int(status.progress()*100)}%",flush=True)
            print(f"Done: https://youtu.be/{response['id']}",flush=True)
            logging.info(f"Uploaded {e.filepath} -> {response['id']}")
        revoke_token()

if __name__=='__main__':
    UploaderApp()
