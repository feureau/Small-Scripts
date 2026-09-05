"""
YouTube Analytics & Visibility Manager
-------------------------------------
Specialized tool for:
1. Fetching granular YouTube Analytics (Watch Time, Retention %, Net Subs, Shares).
2. Date-range performance slicing & CSV export.
3. Batch switching video privacy (Public, Unlisted, Private).
"""

import os
import sys
import json
import csv
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# --- Scopes ---
SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube.force-ssl",     # Required to update privacy
    "https://www.googleapis.com/auth/yt-analytics.readonly"  # Required for deep analytics
]
TOKEN_FILE = "analytics_token.json"


class VideoAnalyticsRecord:
    def __init__(self, video_id, title, published_at, privacy_status, duration_sec, is_short):
        self.video_id = video_id
        self.title = title
        self.published_at = published_at
        self.privacy_status = privacy_status
        self.duration_sec = duration_sec
        self.is_short = is_short
        
        # Analytics Metrics (Period-Specific)
        self.views = 0
        self.watch_time_min = 0.0
        self.avg_view_duration_sec = 0
        self.avg_view_percentage = 0.0
        self.subs_gained = 0
        self.subs_lost = 0
        self.net_subs = 0
        self.shares = 0

    def apply_analytics(self, views, watch_min, avg_dur, avg_pct, subs_g, subs_l, shares):
        self.views = int(views or 0)
        self.watch_time_min = round(float(watch_min or 0.0), 1)
        self.avg_view_duration_sec = int(avg_dur or 0)
        self.avg_view_percentage = round(float(avg_pct or 0.0), 2)
        self.subs_gained = int(subs_g or 0)
        self.subs_lost = int(subs_l or 0)
        self.net_subs = self.subs_gained - self.subs_lost
        self.shares = int(shares or 0)


class AnalyticsApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("YouTube Analytics & Visibility Hub")
        self.root.geometry("1200x750")
        
        self.youtube_service = None
        self.analytics_service = None
        self.video_records = []
        
        self._build_ui()
        self.root.mainloop()

    def _build_ui(self):
        frm = ttk.Frame(self.root, padding=10)
        frm.pack(fill=tk.BOTH, expand=True)

        # 1. Top Auth & Controls Bar
        top_bar = ttk.LabelFrame(frm, text="Authentication & Data Query", padding=10)
        top_bar.pack(fill=tk.X, pady=(0, 5))

        self.auth_btn = ttk.Button(top_bar, text="1. Authenticate (client_secrets.json)", command=self.authenticate)
        self.auth_btn.pack(side=tk.LEFT, padx=5)

        ttk.Label(top_bar, text="Date Range:").pack(side=tk.LEFT, padx=(15, 2))
        self.date_preset_var = tk.StringVar(value="Last 28 Days")
        preset_cb = ttk.Combobox(
            top_bar, textvariable=self.date_preset_var,
            values=["Last 7 Days", "Last 28 Days", "Last 90 Days", "Last 365 Days", "Lifetime (2020-Now)"],
            state="readonly", width=18
        )
        preset_cb.pack(side=tk.LEFT, padx=5)

        self.load_btn = ttk.Button(top_bar, text="2. Load Analytics", command=self.load_data, state=tk.DISABLED)
        self.load_btn.pack(side=tk.LEFT, padx=5)

        self.export_btn = ttk.Button(top_bar, text="Export to CSV", command=self.export_csv, state=tk.DISABLED)
        self.export_btn.pack(side=tk.RIGHT, padx=5)

        # 2. Filter & Search Controls
        filter_bar = ttk.Frame(frm, padding=5)
        filter_bar.pack(fill=tk.X, pady=2)

        ttk.Label(filter_bar, text="Search:").pack(side=tk.LEFT, padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.apply_filters())
        ttk.Entry(filter_bar, textvariable=self.search_var, width=25).pack(side=tk.LEFT, padx=5)

        ttk.Label(filter_bar, text="Type:").pack(side=tk.LEFT, padx=(15, 2))
        self.type_filter_var = tk.StringVar(value="All")
        ttk.Combobox(filter_bar, textvariable=self.type_filter_var, values=["All", "Long-form Only", "Shorts Only"], state="readonly", width=15).pack(side=tk.LEFT, padx=5)
        self.type_filter_var.trace_add("write", lambda *args: self.apply_filters())

        ttk.Label(filter_bar, text="Privacy:").pack(side=tk.LEFT, padx=(15, 2))
        self.privacy_filter_var = tk.StringVar(value="All")
        ttk.Combobox(filter_bar, textvariable=self.privacy_filter_var, values=["All", "Public", "Unlisted", "Private"], state="readonly", width=12).pack(side=tk.LEFT, padx=5)
        self.privacy_filter_var.trace_add("write", lambda *args: self.apply_filters())

        ttk.Button(filter_bar, text="Select All Visible", command=lambda: self.tree.selection_set(self.tree.get_children())).pack(side=tk.RIGHT, padx=2)
        ttk.Button(filter_bar, text="Deselect All", command=lambda: self.tree.selection_remove(self.tree.selection())).pack(side=tk.RIGHT, padx=2)

        # 3. Main Data Table (Treeview)
        table_frame = ttk.Frame(frm)
        table_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.columns = (
            "video_id", "title", "type", "privacy", "views", 
            "watch_time_min", "avg_duration", "retention_pct", "net_subs", "shares", "published"
        )
        self.tree = ttk.Treeview(table_frame, columns=self.columns, show="headings", selectmode="extended")

        col_configs = {
            "video_id": ("Video ID", 90),
            "title": ("Title", 250),
            "type": ("Format", 70),
            "privacy": ("Privacy", 70),
            "views": ("Views", 70),
            "watch_time_min": ("Watch (Min)", 85),
            "avg_duration": ("Avg Dur (s)", 80),
            "retention_pct": ("Retention %", 85),
            "net_subs": ("Net Subs", 70),
            "shares": ("Shares", 65),
            "published": ("Published Date", 100),
        }

        for col, (header, width) in col_configs.items():
            self.tree.heading(col, text=header, command=lambda c=col: self._sort_column(c, False))
            self.tree.column(col, width=width, anchor=tk.CENTER if col not in ["title", "video_id"] else tk.W)

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        # 4. Action Frame: Bulk Privacy Switcher
        action_bar = ttk.LabelFrame(frm, text="Bulk Visibility Actions (Selected Videos)", padding=10)
        action_bar.pack(fill=tk.X, pady=(5, 0))

        ttk.Button(action_bar, text="Set Selected to PUBLIC", command=lambda: self.bulk_update_privacy("public")).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_bar, text="Set Selected to UNLISTED", command=lambda: self.bulk_update_privacy("unlisted")).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_bar, text="Set Selected to PRIVATE", command=lambda: self.bulk_update_privacy("private")).pack(side=tk.LEFT, padx=5)

        self.status_var = tk.StringVar(value="Ready. Authenticate to start.")
        status_bar = ttk.Label(frm, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM, pady=(5, 0))

    # --- Authentication ---
    def authenticate(self):
        path = filedialog.askopenfilename(title="Select client_secrets.json", filetypes=[("JSON files", "*.json")])
        if not path:
            return
        
        self.status_var.set("Authenticating...")
        try:
            creds = None
            if Path(TOKEN_FILE).exists():
                creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(path, SCOPES)
                    creds = flow.run_local_server(port=0)
                with open(TOKEN_FILE, "w") as f:
                    f.write(creds.to_json())

            self.youtube_service = build("youtube", "v3", credentials=creds)
            self.analytics_service = build("youtubeAnalytics", "v2", credentials=creds)
            
            self.load_btn.config(state=tk.NORMAL)
            self.status_var.set("Authentication successful.")
        except Exception as e:
            messagebox.showerror("Auth Error", f"Failed to authenticate: {e}")
            self.status_var.set("Authentication failed.")

    # --- Data Fetching & Aggregation ---
    def load_data(self):
        self.load_btn.config(state=tk.DISABLED)
        self.status_var.set("Fetching videos and analytics...")
        threading.Thread(target=self._run_data_pipeline, daemon=True).start()

    def _run_data_pipeline(self):
        try:
            # 1. Fetch channel's uploads playlist ID
            channels_resp = self.youtube_service.channels().list(part="contentDetails", mine=True).execute()
            uploads_pid = channels_resp["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

            # 2. Get all video IDs
            video_ids = []
            next_token = None
            while True:
                pl_resp = self.youtube_service.playlistItems().list(
                    playlistId=uploads_pid, part="contentDetails", maxResults=50, pageToken=next_token
                ).execute()
                for item in pl_resp.get("items", []):
                    video_ids.append(item["contentDetails"]["videoId"])
                next_token = pl_resp.get("nextPageToken")
                if not next_token:
                    break

            # 3. Batch fetch metadata via Data API
            records_map = {}
            for i in range(0, len(video_ids), 50):
                batch_ids = video_ids[i:i + 50]
                resp = self.youtube_service.videos().list(
                    id=",".join(batch_ids), part="snippet,status,contentDetails"
                ).execute()

                for item in resp.get("items", []):
                    vid = item["id"]
                    title = item["snippet"]["title"]
                    pub_date = item["snippet"]["publishedAt"].split("T")[0]
                    privacy = item["status"]["privacyStatus"]
                    
                    # Estimate Duration & Shorts classification
                    duration_iso = item["contentDetails"].get("duration", "PT0S")
                    dur_sec = self._parse_iso_duration(duration_iso)
                    is_short = dur_sec <= 180  # Heuristic limit for shorts

                    records_map[vid] = VideoAnalyticsRecord(vid, title, pub_date, privacy, dur_sec, is_short)

            # 4. Fetch Bulk YouTube Analytics
            start_date, end_date = self._get_date_range()
            analytics_resp = self.analytics_service.reports().query(
                ids="channel==MINE",
                startDate=start_date,
                endDate=end_date,
                metrics="views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,subscribersGained,subscribersLost,shares",
                dimensions="video"
            ).execute()

            # Columns in response: [video, views, estMinWatched, avgDur, avgPct, subsGained, subsLost, shares]
            for row in analytics_resp.get("rows", []):
                v_id = row[0]
                if v_id in records_map:
                    records_map[v_id].apply_analytics(
                        views=row[1], watch_min=row[2], avg_dur=row[3],
                        avg_pct=row[4], subs_g=row[5], subs_l=row[6], shares=row[7]
                    )

            self.video_records = list(records_map.values())
            self.root.after(0, self._render_table)
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Query Failed", f"Error: {e}"))
            self.root.after(0, lambda: self.status_var.set("Error loading data."))
        finally:
            self.root.after(0, lambda: self.load_btn.config(state=tk.NORMAL))

    def _render_table(self):
        self.apply_filters()
        self.export_btn.config(state=tk.NORMAL)
        self.status_var.set(f"Loaded {len(self.video_records)} videos.")

    def apply_filters(self):
        query = self.search_var.get().lower()
        type_filter = self.type_filter_var.get()
        privacy_filter = self.privacy_filter_var.get().lower()

        self.tree.delete(*self.tree.get_children())
        for rec in self.video_records:
            if query and (query not in rec.title.lower() and query not in rec.video_id.lower()):
                continue
            if type_filter == "Shorts Only" and not rec.is_short:
                continue
            if type_filter == "Long-form Only" and rec.is_short:
                continue
            if privacy_filter != "all" and rec.privacy_status != privacy_filter:
                continue

            self.tree.insert("", tk.END, iid=rec.video_id, values=(
                rec.video_id,
                rec.title,
                "Short" if rec.is_short else "Video",
                rec.privacy_status.upper(),
                f"{rec.views:,}",
                f"{rec.watch_time_min:,.1f}",
                rec.avg_view_duration_sec,
                f"{rec.avg_view_percentage}%",
                rec.net_subs,
                rec.shares,
                rec.published_at
            ))

    # --- Bulk Privacy Actions ---
    def bulk_update_privacy(self, new_privacy):
        selected_ids = self.tree.selection()
        if not selected_ids:
            messagebox.showwarning("No Selection", "Please select one or more videos from the table.")
            return

        confirm = messagebox.askyesno(
            "Confirm Update",
            f"Are you sure you want to change {len(selected_ids)} video(s) to '{new_privacy.upper()}'?"
        )
        if not confirm:
            return

        self.status_var.set(f"Updating {len(selected_ids)} video(s) to {new_privacy}...")
        threading.Thread(target=self._run_privacy_update, args=(selected_ids, new_privacy), daemon=True).start()

    def _run_privacy_update(self, video_ids, new_privacy):
        success = 0
        for vid in video_ids:
            try:
                self.youtube_service.videos().update(
                    part="status",
                    body={"id": vid, "status": {"privacyStatus": new_privacy}}
                ).execute()
                
                # Update local record
                rec = next((r for r in self.video_records if r.video_id == vid), None)
                if rec:
                    rec.privacy_status = new_privacy
                success += 1
            except HttpError as e:
                print(f"Failed to update {vid}: {e}")

        self.root.after(0, self.apply_filters)
        self.root.after(0, lambda: messagebox.showinfo("Success", f"Updated {success}/{len(video_ids)} videos to {new_privacy.upper()}."))
        self.root.after(0, lambda: self.status_var.set(f"Finished privacy update ({success} succeeded)."))

    # --- CSV Export ---
    def export_csv(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv")],
            title="Export Analytics Data"
        )
        if not file_path:
            return

        try:
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                headers = [self.tree.heading(col)["text"] for col in self.columns]
                writer.writerow(headers)
                for item_id in self.tree.get_children():
                    writer.writerow(self.tree.item(item_id)["values"])
            messagebox.showinfo("Export Successful", f"Saved to {file_path}")
        except Exception as e:
            messagebox.showerror("Export Failed", f"Error: {e}")

    # --- Helpers ---
    def _get_date_range(self):
        today = datetime.now(timezone.utc).date()
        preset = self.date_preset_var.get()
        if preset == "Last 7 Days":
            start = today - timedelta(days=7)
        elif preset == "Last 28 Days":
            start = today - timedelta(days=28)
        elif preset == "Last 90 Days":
            start = today - timedelta(days=90)
        elif preset == "Last 365 Days":
            start = today - timedelta(days=365)
        else:
            start = datetime(2020, 1, 1).date()
        return start.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")

    def _parse_iso_duration(self, duration_str):
        import re
        match = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration_str)
        if not match:
            return 0
        h = int(match.group(1) or 0)
        m = int(match.group(2) or 0)
        s = int(match.group(3) or 0)
        return h * 3600 + m * 60 + s

    def _sort_column(self, col, reverse):
        def parse_val(v):
            cleaned = str(v).replace(",", "").replace("%", "").strip()
            try:
                return float(cleaned)
            except ValueError:
                return str(v).lower()

        data = [(parse_val(self.tree.set(k, col)), k) for k in self.tree.get_children("")]
        data.sort(reverse=reverse)
        for idx, (_, k) in enumerate(data):
            self.tree.move(k, "", idx)
        self.tree.heading(col, command=lambda: self._sort_column(col, not reverse))


if __name__ == "__main__":
    AnalyticsApp()