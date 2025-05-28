import os
import subprocess
import shutil
import json
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinterdnd2 import TkinterDnD, DND_FILES
import codecs
import unicodedata
from ftfy import fix_text  # Import ftfy's fix_text function
import threading
import sys

# Set UTF-8 encoding for subprocesses
env = os.environ.copy()
env["PYTHONIOENCODING"] = "utf-8"

def get_video_bit_depth(file_path):
    cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0",
           "-show_entries", "stream=bits_per_raw_sample", "-of", "json", file_path]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, env=env)
        data = json.loads(result.stdout)
        bit_depth = data.get("streams", [{}])[0].get("bits_per_raw_sample", None)
        if bit_depth is None:
            return 8
        return int(bit_depth)
    except Exception as e:
        print(f"[WARN] Could not detect bit depth for {file_path}: {e}")
        return 8

def is_hdr(file_path):
    cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0",
           "-show_entries", "stream=color_transfer,color_primaries", "-of", "json", file_path]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, env=env)
        data = json.loads(result.stdout)
        if "streams" in data and len(data["streams"]) > 0:
            stream = data["streams"][0]
            color_transfer = stream.get("color_transfer", "").lower()
            color_primaries = stream.get("color_primaries", "").lower()
            if color_transfer in ["smpte2084", "arib-std-b67", "pq"]:
                return True
            if color_primaries == "bt2020":
                return True
        return False
    except Exception as e:
        print(f"[WARN] Could not detect HDR vs SDR for {file_path}: {e}")
        return False

def get_input_width(file_path):
    cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0",
           "-show_entries", "stream=width", "-of", "csv=p=0", file_path]
    try:
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT,
                                         universal_newlines=True, env=env)
        try:
            return int(output.strip().replace(',', ''))
        except ValueError:
            print(f"[ERROR] ffprobe output for width is not an integer: {output.strip()}")
            return 0
    except Exception as e:
        print(f"[ERROR] Error getting width from ffprobe: {e}")
        return 0

def get_input_height(file_path):
    cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0",
           "-show_entries", "stream=height", "-of", "csv=p=0", file_path]
    try:
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT,
                                         universal_newlines=True, env=env)
        try:
            return int(output.strip().replace(',', ''))
        except ValueError:
            print(f"[ERROR] ffprobe output for height is not an integer: {output.strip()}")
            return 0
    except Exception as e:
        print(f"[ERROR] Error getting height from ffprobe: {e}")
        return 0

def normalize_text(text):
    """Normalize text using ftfy for robust cleanup."""
    normalized_text = fix_text(text)
    normalized_text = normalized_text.replace("’", "'")
    return normalized_text

def cleanup_ass_content(ass_file):
    r"""Remove \\N line breaks from ASS file content."""
    try:
        with open(ass_file, 'r', encoding='utf-8') as f:
            content = f.readlines()
        cleaned_lines = []
        for line in content:
            cleaned_line = line.replace(r'\N', ' ', 1)
            cleaned_lines.append(cleaned_line)
        with open(ass_file, 'w', encoding='utf-8', newline='\n') as f:
            f.writelines(cleaned_lines)
        print(f"[DEBUG] Removed \\N line breaks from ASS file: {ass_file}")
    except Exception as e:
        print(f"[ERROR] Error cleaning up ASS content (removing \\N): {ass_file}: {e}")

class VideoProcessorApp:
    def __init__(self, root, initial_files):
        self.root = root
        self.root.title("Video Processing Tool")
        # Updated LUT location
        self.lut_file = r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\LUT\NBCU\5-NBCU_PQ2SDR_DL_RESOLVE17-VRT_v1.2.cube"
        self.subtitles_by_file = {}
        self.file_list = []
        self.subtitle_id_counter = 0
        self.current_subtitle_checkbuttons = []
        self.file_options = {}
        self.resolution_var = tk.StringVar(value="4k")
        self.upscale_algo_var = tk.StringVar(value="nvvfx-superres")
        self.eight_bit_var = tk.BooleanVar(value=False)
        # HDR Metadata is on by default for SDR videos
        self.hdr_var = tk.BooleanVar(value=True)
        self.crop_var = tk.BooleanVar(value=False)
        self.qvbr_var = tk.StringVar(value="12")
        self.fruc_var = tk.BooleanVar(value=False)
        self.fruc_fps_var = tk.StringVar(value="60")
        self.alignment_var = tk.StringVar(value="middle")
        self.subtitle_font_size_var = tk.StringVar(value="12")
        self.generate_log_var = tk.BooleanVar(value=False)
        # Convert to HDR option (applies --vpp-ngx-truehdr flag)
        self.convert_hdr_var = tk.BooleanVar(value=False)

        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind("<<Drop>>", self.handle_file_drop)

        self.file_frame = tk.Frame(root)
        self.file_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.file_listbox = tk.Listbox(self.file_frame, selectmode=tk.EXTENDED, height=15)
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.file_scrollbar = tk.Scrollbar(self.file_frame, orient=tk.VERTICAL, command=self.file_listbox.yview)
        self.file_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_listbox.config(yscrollcommand=self.file_scrollbar.set)
        self.file_listbox.bind("<<ListboxSelect>>", self.on_file_select)

        self.file_buttons_frame = tk.Frame(root)
        self.file_buttons_frame.pack(fill=tk.X, padx=10, pady=5)

        self.select_all_button = tk.Button(self.file_buttons_frame, text="Select All", command=self.select_all_files)
        self.select_all_button.pack(side=tk.LEFT, padx=5)
        self.add_button = tk.Button(self.file_buttons_frame, text="Add Files", command=self.add_files)
        self.add_button.pack(side=tk.LEFT, padx=5)
        self.remove_button = tk.Button(self.file_buttons_frame, text="Remove Selected", command=self.remove_selected)
        self.remove_button.pack(side=tk.LEFT, padx=5)
        self.clear_button = tk.Button(self.file_buttons_frame, text="Clear All", command=self.clear_all)
        self.clear_button.pack(side=tk.LEFT, padx=5)
        self.move_up_button = tk.Button(self.file_buttons_frame, text="Move Up", command=self.move_up)
        self.move_up_button.pack(side=tk.LEFT, padx=5)
        self.move_down_button = tk.Button(self.file_buttons_frame, text="Move Down", command=self.move_down)
        self.move_down_button.pack(side=tk.LEFT, padx=5)

        self.options_frame = tk.Frame(root)
        self.options_frame.pack(fill=tk.X, padx=10, pady=10)

        # Resolution Options Frame
        self.resolution_options_frame = tk.LabelFrame(self.options_frame, text="Resolution and Upscale Algorithm", padx=10, pady=5)
        self.resolution_options_frame.grid(row=0, column=0, columnspan=4, sticky="ew", pady=5)

        tk.Label(self.resolution_options_frame, text="Resolution:").grid(row=0, column=0, sticky=tk.W)
        self.res_original_button = tk.Radiobutton(self.resolution_options_frame, text="Original",
                                                  variable=self.resolution_var, value="original", command=self.apply_gui_options_to_selected_files)
        self.res_original_button.grid(row=0, column=1, sticky=tk.W)
        self.res_4k_button = tk.Radiobutton(self.resolution_options_frame, text="4k",
                                            variable=self.resolution_var, value="4k", command=self.apply_gui_options_to_selected_files)
        self.res_4k_button.grid(row=0, column=2, sticky=tk.W)
        self.res_8k_button = tk.Radiobutton(self.resolution_options_frame, text="8k",
                                            variable=self.resolution_var, value="8k", command=self.apply_gui_options_to_selected_files)
        self.res_8k_button.grid(row=0, column=3, sticky=tk.W)

        tk.Label(self.resolution_options_frame, text="Upscale Algorithm:").grid(row=1, column=0, sticky=tk.W, padx=(20, 0))
        self.upscale_nvvfx_button = tk.Radiobutton(self.resolution_options_frame, text="nvvfx-superres",
                                                   variable=self.upscale_algo_var, value="nvvfx-superres", command=self.apply_gui_options_to_selected_files)
        self.upscale_nvvfx_button.grid(row=1, column=1, sticky=tk.W, padx=(20, 0))
        self.upscale_ngxvsr_button = tk.Radiobutton(self.resolution_options_frame, text="ngx-vsr",
                                                   variable=self.upscale_algo_var, value="ngx-vsr", command=self.apply_gui_options_to_selected_files)
        self.upscale_ngxvsr_button.grid(row=1, column=2, sticky=tk.W)

        # --- Options Panel Layout ---
        tk.Label(self.options_frame, text="Convert to 8 bit:").grid(row=1, column=0, sticky=tk.W)
        self.eight_bit_checkbox = tk.Checkbutton(self.options_frame, variable=self.eight_bit_var,
                                                 command=self.apply_gui_options_to_selected_files)
        self.eight_bit_checkbox.grid(row=1, column=1, sticky=tk.W)

        tk.Label(self.options_frame, text="Convert to HDR:").grid(row=2, column=0, sticky=tk.W)
        self.convert_hdr_checkbox = tk.Checkbutton(self.options_frame, variable=self.convert_hdr_var,
                                                   command=self.apply_gui_options_to_selected_files)
        self.convert_hdr_checkbox.grid(row=2, column=1, sticky=tk.W)

        tk.Label(self.options_frame, text="HDR Metadata:").grid(row=3, column=0, sticky=tk.W)
        self.hdr_checkbox = tk.Checkbutton(self.options_frame, variable=self.hdr_var,
                                           command=self.apply_gui_options_to_selected_files)
        self.hdr_checkbox.grid(row=3, column=1, sticky=tk.W)

        tk.Label(self.options_frame, text="Vertical Crop:").grid(row=4, column=0, sticky=tk.W)
        self.crop_checkbox = tk.Checkbutton(self.options_frame, variable=self.crop_var,
                                            command=self.apply_gui_options_to_selected_files)
        self.crop_checkbox.grid(row=4, column=1, sticky=tk.W)

        tk.Label(self.options_frame, text="QVBR Value:").grid(row=5, column=0, sticky=tk.W)
        self.qvbr_entry = tk.Entry(self.options_frame, textvariable=self.qvbr_var, width=10)
        self.qvbr_entry.grid(row=5, column=1, sticky=tk.W)
        self.qvbr_entry.bind("<FocusOut>", self.apply_gui_options_to_selected_files_event)

        tk.Label(self.options_frame, text="Enable FRUC:").grid(row=6, column=0, sticky=tk.W)
        self.fruc_checkbox = tk.Checkbutton(self.options_frame, variable=self.fruc_var,
                                            command=lambda: [self.toggle_fruc_fps(), self.apply_gui_options_to_selected_files()])
        self.fruc_checkbox.grid(row=6, column=1, sticky=tk.W)

        tk.Label(self.options_frame, text="FRUC FPS Target:").grid(row=7, column=0, sticky=tk.W)
        self.fruc_fps_entry = tk.Entry(self.options_frame, textvariable=self.fruc_fps_var, width=10)
        self.fruc_fps_entry.grid(row=7, column=1, sticky=tk.W)
        self.fruc_fps_entry.configure(state="disabled")
        self.fruc_fps_entry.bind("<FocusOut>", self.apply_gui_options_to_selected_files_event)

        tk.Label(self.options_frame, text="Subtitle Alignment:").grid(row=8, column=0, sticky=tk.W)
        self.align_frame = tk.Frame(self.options_frame)
        self.align_frame.grid(row=8, column=1, columnspan=3, sticky=tk.W)
        self.align_top_rb = tk.Radiobutton(self.align_frame, text="Top",
                                           variable=self.alignment_var, value="top",
                                           command=self.apply_gui_options_to_selected_files)
        self.align_top_rb.pack(anchor="w")
        self.align_middle_rb = tk.Radiobutton(self.align_frame, text="Middle",
                                              variable=self.alignment_var, value="middle",
                                              command=self.apply_gui_options_to_selected_files)
        self.align_middle_rb.pack(anchor="w")
        self.align_bottom_rb = tk.Radiobutton(self.align_frame, text="Bottom",
                                              variable=self.alignment_var, value="bottom",
                                              command=self.apply_gui_options_to_selected_files)
        self.align_bottom_rb.pack(anchor="w")

        tk.Label(self.options_frame, text="Subtitle Font Size:").grid(row=9, column=0, sticky=tk.W)
        self.subtitle_font_size_entry = tk.Entry(self.options_frame, textvariable=self.subtitle_font_size_var, width=10)
        self.subtitle_font_size_entry.grid(row=9, column=1, sticky=tk.W)
        self.subtitle_font_size_entry.bind("<FocusOut>", self.apply_gui_options_to_selected_files_event)

        # --- End Options Panel Layout ---
        self.subtitle_tracks_frame = tk.LabelFrame(root, text="Burn Subtitle Tracks", padx=10, pady=10)
        self.subtitle_tracks_frame.pack(fill=tk.X, padx=10, pady=5)

        self.subtitle_tracks_buttons_frame = tk.Frame(self.subtitle_tracks_frame)
        self.subtitle_tracks_buttons_frame.pack(fill=tk.X, padx=5, pady=5)

        self.load_embedded_srt_button = tk.Button(self.subtitle_tracks_buttons_frame, text="Load Embedded SRT (All Files)",
                                                  command=self.load_embedded_srt_all)
        self.load_embedded_srt_button.pack(side=tk.LEFT, padx=(0, 5))
        self.add_external_srt_button = tk.Button(self.subtitle_tracks_buttons_frame, text="Add External SRT (Current File)",
                                                 command=self.add_external_srt)
        self.add_external_srt_button.pack(side=tk.LEFT, padx=(0, 5))
        self.remove_srt_button = tk.Button(self.subtitle_tracks_buttons_frame, text="Remove Selected SRT (Current File)",
                                           command=self.remove_selected_srt)
        self.remove_srt_button.pack(side=tk.LEFT, padx=(0, 5))

        self.subtitle_tracks_list_frame = tk.Frame(self.subtitle_tracks_frame)
        self.subtitle_tracks_list_frame.pack(fill=tk.X)

        self.bottom_frame = tk.Frame(root)
        self.bottom_frame.pack(pady=10, padx=10, fill=tk.X)

        self.start_button = tk.Button(self.bottom_frame, text="Start Processing", command=self.start_processing)
        self.start_button.pack(side=tk.LEFT, padx=5)
        self.generate_log_checkbox = tk.Checkbutton(self.bottom_frame, text="Generate Log File",
                                                      variable=self.generate_log_var,
                                                      command=self.apply_gui_options_to_selected_files)
        self.generate_log_checkbox.pack(side=tk.LEFT, padx=(10, 0))

        self.update_file_list(initial_files)
        for f in initial_files:
            self.auto_set_hdr(f)

        if self.file_listbox.size() > 0:
            self.file_listbox.select_set(0)
            self.on_file_select(None)

    def compute_final_resolution(self, file_path):
        options = self.file_options.get(file_path, {})
        resolution = options.get("resolution", self.resolution_var.get())
        in_w = get_input_width(file_path)
        in_h = get_input_height(file_path)
        if resolution == "original":
            return in_w, in_h
        elif resolution == "4k":
            return 2160, 2160
        elif resolution == "8k":
            return 4320, 4320
        else:
            return in_w, in_h

    def apply_gui_options_to_selected_files(self, event=None):
        selected_indices = self.file_listbox.curselection()
        if not selected_indices:
            return
        options_state = {
            "resolution": self.resolution_var.get(),
            "upscale_algo": self.upscale_algo_var.get(),
            "eight_bit": self.eight_bit_var.get(),
            "hdr": self.hdr_var.get(),
            "convert_hdr": self.convert_hdr_var.get(),
            "crop": self.crop_var.get(),
            "qvbr": self.qvbr_var.get(),
            "fruc": self.fruc_var.get(),
            "fruc_fps": self.fruc_fps_var.get(),
            "alignment": self.alignment_var.get(),
            "subtitle_font_size": self.subtitle_font_size_var.get(),
            "generate_log": self.generate_log_var.get()
        }
        for index in selected_indices:
            filepath = self.file_list[index]
            self.file_options[filepath] = options_state

    def apply_gui_options_to_selected_files_event(self, event):
        self.apply_gui_options_to_selected_files()

    def load_embedded_srt_all(self):
        for file_path in self.file_list:
            self.detect_subtitle_tracks(file_path)
        self.refresh_subtitle_list()

    def auto_set_hdr(self, file_path):
        hdr_detected = is_hdr(file_path)
        if hdr_detected:
            self.hdr_var.set(False)
        else:
            self.hdr_var.set(True)

    def add_files(self):
        files = filedialog.askopenfilenames(filetypes=[("Video Files", "*.mp4;*.mkv;*.avi"), ("All Files", "*.*")])
        self.update_file_list(files)
        for f in files:
            self.auto_set_hdr(f)
        if self.file_listbox.size() > 0 and not self.file_listbox.curselection():
            self.file_listbox.select_set(0)
            self.on_file_select(None)

    def handle_file_drop(self, event):
        files = self.root.tk.splitlist(event.data)
        self.update_file_list(files)
        for f in files:
            self.auto_set_hdr(f)
        if self.file_listbox.size() > 0 and not self.file_listbox.curselection():
            self.file_listbox.select_set(0)
            self.on_file_select(None)

    def update_file_list(self, files):
        for file_path in files: # Renamed 'file' to 'file_path' for clarity with debug
            print(f"DEBUG: Received file_path by update_file_list: '{file_path}'") # <<< ADDED DEBUG
            if file_path not in self.file_list:
                self.file_list.append(file_path)
                self.file_listbox.insert(tk.END, file_path)
                self.subtitles_by_file[file_path] = []
                self.detect_subtitle_tracks(file_path)
                self.file_options[file_path] = {
                    "resolution": self.resolution_var.get(),
                    "upscale_algo": self.upscale_algo_var.get(),
                    "eight_bit": self.eight_bit_var.get(),
                    "hdr": self.hdr_var.get(),
                    "convert_hdr": self.convert_hdr_var.get(),
                    "crop": self.crop_var.get(),
                    "qvbr": self.qvbr_var.get(),
                    "fruc": self.fruc_var.get(),
                    "fruc_fps": self.fruc_fps_var.get(),
                    "alignment": self.alignment_var.get(),
                    "subtitle_font_size": self.subtitle_font_size_var.get(),
                    "generate_log": self.generate_log_var.get()
                }

    def select_all_files(self):
        self.file_listbox.select_set(0, tk.END)

    def remove_selected(self):
        selected_indices = list(self.file_listbox.curselection())
        for index in reversed(selected_indices):
            file_to_remove = self.file_list[index]
            if file_to_remove in self.subtitles_by_file:
                del self.subtitles_by_file[file_to_remove]
            if file_to_remove in self.file_options:
                del self.file_options[file_to_remove]
            del self.file_list[index]
            self.file_listbox.delete(index)
        self.refresh_subtitle_list()

    def clear_all(self):
        self.file_list.clear()
        self.file_listbox.delete(0, tk.END)
        self.subtitles_by_file.clear()
        self.file_options.clear()
        self.refresh_subtitle_list()

    def move_up(self):
        selected_indices = list(self.file_listbox.curselection())
        if not selected_indices or selected_indices[0] == 0:
            return
        for index in selected_indices:
            if index > 0:
                self.file_list[index], self.file_list[index - 1] = self.file_list[index - 1], self.file_list[index]
                self.file_listbox.delete(index)
                self.file_listbox.insert(index - 1, self.file_list[index - 1])
                self.file_listbox.select_set(index - 1)
                self.file_listbox.select_clear(index)

    def move_down(self):
        selected_indices = list(self.file_listbox.curselection())
        if not selected_indices or selected_indices[-1] == len(self.file_list) - 1:
            return
        for index in reversed(selected_indices):
            if index < len(self.file_list) - 1:
                self.file_list[index], self.file_list[index + 1] = self.file_list[index + 1], self.file_list[index]
                self.file_listbox.delete(index)
                self.file_listbox.insert(index + 1, self.file_list[index + 1])
                self.file_listbox.select_set(index + 1)
                self.file_listbox.select_clear(index)

    def detect_subtitle_tracks(self, file_path):
        cmd = ["ffprobe", "-v", "error", "-select_streams", "s",
               "-show_entries", "stream=index:stream_tags=language:stream_tags=title",
               "-of", "default=noprint_wrappers=1", file_path]
        print("Detecting subtitles with:", " ".join(cmd))
        try:
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT,
                                             universal_newlines=True, env=env)
        except subprocess.CalledProcessError as e:
            print(f"Error detecting subtitle tracks for {file_path}: {e}")
            return
        lines = output.splitlines()
        track_info = {}
        all_tracks = []
        for line in lines:
            line = line.strip()
            if line.startswith("index="):
                if track_info:
                    all_tracks.append(track_info)
                idx_val = line.split("=")[1]
                track_info = {"track_id": idx_val, "lang": "und", "title": ""}
            elif line.startswith("TAG:language="):
                track_info["lang"] = line.split("=")[1]
            elif line.startswith("TAG:title="):
                track_info["title"] = line.split("=")[1]
            elif line.startswith("[/STREAM]"):
                if track_info:
                    all_tracks.append(track_info)
                track_info = {}
        if track_info:
            all_tracks.append(track_info)
        existing_embedded_ids = {s["track_id"] for s in self.subtitles_by_file[file_path] if s["type"] == "embedded"}
        for track in all_tracks:
            if "track_id" not in track:
                print(f"[WARN] Subtitle track info is missing 'track_id', skipping track: {track}")
                continue
            if track["track_id"] in existing_embedded_ids:
                continue
            desc = f"Embedded: #{track['track_id']} - {track['lang']}"
            if track["title"]:
                desc += f" ({track['title']})"
            sub_id = f"embed_{os.path.basename(file_path)}_{track['track_id']}_{self.subtitle_id_counter}"
            self.subtitle_id_counter += 1
            self.subtitles_by_file[file_path].append({
                "id": sub_id,
                "type": "embedded",
                "file_path": file_path,
                "track_id": track['track_id'],
                "path": None,
                "description": desc,
                "selected": False,
                "checkbutton": None
            })
        self.refresh_subtitle_list()

    def add_external_srt(self):
        sel = self.file_listbox.curselection()
        if not sel:
            messagebox.showwarning("No file selected", "Please select a file to add external subtitles to.")
            return
        file_idx = sel[0]
        current_file = self.file_list[file_idx]
        initial_dir = os.path.dirname(current_file)
        srt_files = filedialog.askopenfilenames(filetypes=[("Subtitle Files", "*.srt"), ("All Files", "*.*")],
                                                initialdir=initial_dir)
        for s in srt_files:
            already_exists = any((x["type"] == "external" and x["path"] == s)
                                   for x in self.subtitles_by_file[current_file])
            if already_exists:
                continue
            srt_base = os.path.basename(s)
            desc = f"External: {srt_base}"
            sub_id = f"ext_{srt_base}_{self.subtitle_id_counter}"
            self.subtitle_id_counter += 1
            self.subtitles_by_file[current_file].append({
                "id": sub_id,
                "type": "external",
                "file_path": current_file,
                "track_id": None,
                "path": s,
                "description": desc,
                "selected": False,
                "checkbutton": None
            })
        self.refresh_subtitle_list()

    def remove_selected_srt(self):
        sel = self.file_listbox.curselection()
        if not sel:
            return
        file_idx = sel[0]
        current_file = self.file_list[file_idx]
        subs_to_remove = [sub for sub in self.subtitles_by_file[current_file]
                          if sub["selected"] and sub["type"] == "external"]
        for sub in subs_to_remove:
            self.subtitles_by_file[current_file].remove(sub)
        self.refresh_subtitle_list()

    def on_file_select(self, event):
        sel = self.file_listbox.curselection()
        if sel:
            selected_file = self.file_list[sel[0]]
            if selected_file in self.file_options:
                file_options = self.file_options[selected_file]
                self.resolution_var.set(file_options.get("resolution", "4k"))
                self.upscale_algo_var.set(file_options.get("upscale_algo", "nvvfx-superres"))
                self.eight_bit_var.set(file_options.get("eight_bit", False))
                self.hdr_var.set(file_options.get("hdr", False))
                self.convert_hdr_var.set(file_options.get("convert_hdr", False))
                self.crop_var.set(file_options.get("crop", False))
                self.qvbr_var.set(file_options.get("qvbr", "12"))
                self.fruc_var.set(file_options.get("fruc", False))
                self.fruc_fps_var.set(file_options.get("fruc_fps", "60"))
                self.alignment_var.set(file_options.get("alignment", "middle"))
                self.subtitle_font_size_var.set(file_options.get("subtitle_font_size", "12"))
                self.generate_log_var.set(file_options.get("generate_log", False))
                self.toggle_fruc_fps()
        self.refresh_subtitle_list()

    def refresh_subtitle_list(self):
        for cb in self.current_subtitle_checkbuttons:
            cb.destroy()
        self.current_subtitle_checkbuttons.clear()
        sel = self.file_listbox.curselection()
        if not sel:
            return
        file_idx = sel[0]
        current_file = self.file_list[file_idx]
        for sub in self.subtitles_by_file[current_file]:
            var = tk.BooleanVar(value=sub["selected"])
            cb = tk.Checkbutton(self.subtitle_tracks_list_frame, text=sub["description"],
                                variable=var, anchor="w",
                                command=lambda s=sub, v=var: self.on_subtitle_check(s, v))
            cb.pack(fill="x", padx=20, anchor="w")
            sub["checkbutton"] = cb
            self.current_subtitle_checkbuttons.append(cb)

    def on_subtitle_check(self, sub, var):
        selected_indices = self.file_listbox.curselection()
        if not selected_indices:
            return
        selected_track_id = None
        if var.get():
            selected_track_id = sub["track_id"]
        for file_index in selected_indices:
            file_path = self.file_list[file_index]
            if file_path in self.subtitles_by_file:
                for s in self.subtitles_by_file[file_path]:
                    if s["type"] == "embedded":
                        if selected_track_id is not None and s["track_id"] == selected_track_id:
                            s["selected"] = True
                        else:
                            s["selected"] = False
                            if s["checkbutton"]:
                                s["checkbutton"].deselect()
        self.apply_gui_options_to_selected_files()

    def toggle_fruc_fps(self):
        if self.fruc_var.get():
            self.fruc_fps_entry.configure(state="normal")
        else:
            self.fruc_fps_entry.configure(state="disabled")

    def fix_ass_style(self, ass_file, final_width, final_height):
        alignment_map = {"top": 8, "middle": 5, "bottom": 2}
        alignment_code = alignment_map.get(self.alignment_var.get(), 2)
        margin_l = margin_r = int(final_width * 0.01875)
        margin_v = 0 if alignment_code == 5 else 50
        try:
            font_size = int(self.subtitle_font_size_var.get())
        except ValueError:
            font_size = 12
        try:
            with open(ass_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
            with open(ass_file, "w", encoding="utf-8") as f:
                in_styles = False
                for line in lines:
                    if line.strip().startswith("[V4+ Styles]"):
                        in_styles = True
                        f.write(line)
                        f.write("Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n")
                        style_line = f"Style: Default,FreeSans,{font_size},&H00FFFFFF,&H000000FF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,1,1,{alignment_code},{margin_l},{margin_r},{margin_v},1\n"
                        f.write(style_line)
                        continue
                    if in_styles:
                        if line.strip().startswith("Format:") or line.strip().startswith("Style:"):
                            continue
                    f.write(line)
            self.fix_overlapping_subtitle_lines(ass_file)
        except Exception as e:
            print(f"[ERROR] Error fixing style in {ass_file}: {e}")

    def fix_overlapping_subtitle_lines(self, ass_file):
        def ass_time_to_seconds(t):
            parts = t.split(':')
            if len(parts) != 3:
                return 0.0
            hh = int(parts[0])
            mm = int(parts[1])
            ss = float(parts[2])
            return hh * 3600 + mm * 60 + ss
        def seconds_to_ass_time(s):
            hh = int(s // 3600)
            s_mod = s % 3600
            mm = int(s_mod // 60)
            ss = s_mod % 60
            return f"{hh}:{mm:02d}:{ss:05.2f}"
        try:
            with open(ass_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
            in_events = False
            last_end = 0.0
            new_lines = []
            for line in lines:
                if line.strip().startswith("[Events]"):
                    in_events = True
                    new_lines.append(line)
                    continue
                if in_events and line.strip().startswith("["):
                    in_events = False
                    new_lines.append(line)
                    continue
                if in_events and line.strip().startswith("Dialogue:"):
                    parts = line.split(",")
                    if len(parts) >= 10:
                        subtitle_text = parts[9]
                        normalized_text = normalize_text(subtitle_text)
                        parts[9] = normalized_text
                        line = ",".join(parts)
                        start_ts = parts[1]
                        end_ts = parts[2]
                        start_sec = ass_time_to_seconds(start_ts)
                        end_sec = ass_time_to_seconds(end_ts)
                        if start_sec < last_end:
                            start_sec = last_end + 0.01
                            if start_sec > end_sec:
                                end_sec = start_sec + 1.0
                        new_start_str = seconds_to_ass_time(start_sec)
                        new_end_str = seconds_to_ass_time(end_sec)
                        last_end = end_sec
                        parts[1] = new_start_str
                        parts[2] = new_end_str
                        line = ",".join(parts)
                new_lines.append(line)
            with open(ass_file, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
        except Exception as e:
            print(f"[ERROR] Error writing fixed overlaps: {e}")

    def extract_embedded_subtitle_to_ass(self, input_file, output_ass, sub_track_id, final_width, final_height):
        cmd = ["ffmpeg", "-sub_charenc", "UTF-8", "-i", input_file,
               "-map", f"0:{sub_track_id}", "-c:s", "ass", output_ass]
        print(f"Extracting embedded subtitle track {sub_track_id} => {output_ass}")
        try:
            subprocess.run(cmd, check=True, env=env)
            self.fix_ass_style(output_ass, final_width, final_height)
            cleanup_ass_content(output_ass)
            print(f"Embedded track {sub_track_id} extracted as ASS => {output_ass}")
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Error extracting embedded subtitle track {sub_track_id}: {e}")

    def extract_external_srt_to_ass(self, srt_file, output_ass, final_width, final_height):
        self.cleanup_srt_encoding(srt_file)
        cmd = ["ffmpeg", "-sub_charenc", "UTF-8", "-i", srt_file, "-c:s", "ass", output_ass]
        print(f"Converting external SRT => ASS: {' '.join(cmd)}")
        try:
            subprocess.run(cmd, check=True, env=env)
            self.fix_ass_style(output_ass, final_width, final_height)
            cleanup_ass_content(output_ass)
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Error converting external SRT {srt_file}: {e}")

    def extract_subtitle_to_srt(self, input_file, output_srt, sub_track_id=None):
        if sub_track_id is not None:
            cmd = ["ffmpeg", "-sub_charenc", "UTF-8", "-i", input_file,
                   "-map", f"0:{sub_track_id}", "-c:s", "srt", output_srt]
            print(f"Extracting embedded track => SRT: {' '.join(cmd)}")
            try:
                subprocess.run(cmd, check=True, env=env)
                print(f"Extracted to {output_srt}")
            except subprocess.CalledProcessError as e:
                print(f"[ERROR] Error extracting SRT from track {sub_track_id}: {e}")
        else:
            srt_file = input_file
            self.cleanup_srt_encoding(srt_file)
            print(f"Copying external SRT => {output_srt}")
            try:
                shutil.copyfile(input_file, output_srt)
                print(f"Copied {input_file} => {output_srt}")
            except Exception as e:
                print(f"[ERROR] Error copying external SRT {input_file}: {e}")

    def cleanup_srt_encoding(self, srt_file):
        try:
            with open(srt_file, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            try:
                with open(srt_file, 'r', encoding='cp1252') as f:
                    content = f.read()
                content = normalize_text(content)
                with open(srt_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"[WARN] Converted SRT {srt_file} from CP1252 to UTF-8 and normalized text. Ensure subtitles display correctly.")
            except Exception as e_conv:
                print(f"[ERROR] SRT Conversion failed for {srt_file}: {e_conv}")
                return
        except Exception as e_read:
            print(f"[ERROR] SRT Read error for {srt_file}: {e_read}")
            return
        try:
            with open(srt_file, 'r', encoding='utf-8') as f:
                content_utf8 = f.read()
        except Exception as e_read_utf8:
            print(f"[ERROR] Error re-reading SRT as UTF-8: {srt_file}: {e_read_utf8}")
            return
        normalized_content = normalize_text(content_utf8)
        with open(srt_file, 'w', encoding='utf-8') as f:
            f.write(normalized_content)

    # Run NVEnc command and update output dynamically on a single line
    def run_nvenc_command(self, cmd):
        print("Running NVEnc command:")
        print(" ".join(cmd))
        process = subprocess.Popen(cmd,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env, text=True,encoding='utf-8',errors='replace',bufsize=1)
        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            if line:
                if "\r" in line:
                    progress = line.split("\r")[-1].strip()
                    sys.stdout.write("\r" + progress)
                    sys.stdout.flush()
                else:
                    sys.stdout.write(line)
                    sys.stdout.flush()
        process.stdout.close()
        ret = process.wait()
        print("\nNVEnc conversion finished.")
        return ret

    def build_nvenc_command_and_run(self, file_path, output_file, ass_burn=None):
        print(f"DEBUG: file_path at start of build_nvenc_command_and_run: '{file_path}'") # <<< ADDED DEBUG
        file_options = self.file_options.get(file_path, {})
        resolution = file_options.get("resolution", self.resolution_var.get())
        upscale_algo = file_options.get("upscale_algo", self.upscale_algo_var.get())
        qvbr_value = file_options.get("qvbr", self.qvbr_var.get())
        eight_bit = file_options.get("eight_bit", self.eight_bit_var.get())
        fruc_enable = file_options.get("fruc", self.fruc_var.get())
        fruc_fps_target = file_options.get("fruc_fps")
        generate_log = file_options.get("generate_log", self.generate_log_var.get())
        convert_to_hdr = file_options.get("hdr", self.hdr_var.get())
        convert_hdr = file_options.get("convert_hdr", self.convert_hdr_var.get())

        if output_file is None:
            # OUTPUT FILE NAMED WITH _temp SUFFIX FOR mkvmerge
            output_dir = os.path.join(os.path.dirname(file_path), resolution)
            os.makedirs(output_dir, exist_ok=True)
            base_name, ext = os.path.splitext(os.path.basename(file_path))
            print(f"DEBUG: base_name: '{base_name}', ext: '{ext}'") # <<< ADDED DEBUG
            if eight_bit:
                temp_name = f"{base_name}_8bit_temp{ext}"
            else:
                temp_name = f"{base_name}_temp{ext}"
            output_file = os.path.join(output_dir, temp_name)

        final_width, final_height = self.compute_final_resolution(file_path)
        do_resize = resolution in ["4k", "8k"]
        resize_algo = upscale_algo
        target_res = f"{final_width}x{final_height}"

        cmd = self.construct_nvencc_command(
            file_path, output_file, qvbr_value, eight_bit,
            fruc_enable, fruc_fps_target, generate_log,
            convert_to_hdr, convert_hdr, ass_burn,
            resize_algo, target_res, do_resize
        )
        ret = self.run_nvenc_command(cmd)
        if ret == 0:
            print(f"\nDone processing: {file_path}")
            return (output_file, final_width, final_height)
        else:
            print(f"[ERROR] Error encoding {file_path}: return code {ret}")
            return (None, final_width, final_height)

    def construct_nvencc_command(self, file_path, output_file, qvbr_value, eight_bit,
                                  fruc_enable, fruc_fps_target, generate_log,
                                  convert_to_hdr, convert_hdr, ass_burn,
                                  resize_algo, target_res, do_resize):
        cmd = [
            "NVEncC64", "--avhw", "--codec", "av1", "--qvbr", str(qvbr_value), "--max-bitrate", "100000",
            "--preset", "p4", "--output-depth", "8" if eight_bit else "10",
            "--audio-copy", "--sub-copy", "--chapter-copy", #"--key-on-chapter",
            "--transfer", "bt709" if eight_bit else "auto",
            "--colorprim", "bt709" if eight_bit else "auto",
            "--colormatrix", "bt709" if eight_bit else "auto",
            "--lookahead", "32", "--aq-temporal", "--multipass", "2pass-full",
            "--bframes", "4", "--tf-level", "4", "--split-enc", "forced_4", "--parallel", "2",
            "--log-level", "info", "--output", output_file, "-i", file_path
        ]
        if eight_bit and os.path.exists(self.lut_file):
            cmd.extend(["--vpp-colorspace", f"lut3d={self.lut_file},lut3d_interp=trilinear"])
            print(f"Applying LUT: {self.lut_file}")
        if do_resize:
            if resize_algo == "ngx-vsr":
                cmd.extend(["--vpp-resize", f"algo={resize_algo},vsr-quality=1",
                            "--output-res", f"{target_res},preserve_aspect_ratio=increase"])
            else:
                cmd.extend(["--vpp-resize", f"algo={resize_algo}",
                            "--output-res", f"{target_res},preserve_aspect_ratio=increase"])
        crop_str = self.compute_crop_value(file_path)
        if crop_str != "0,0,0,0":
            cmd.extend(["--crop", crop_str])
        if fruc_enable:
            cmd.extend(["--vpp-fruc", f"fps={fruc_fps_target}"])
        if generate_log:
            cmd.extend(["--log", "log.log", "--log-level", "debug"])
        if ass_burn:
            cmd.extend(["--vpp-subburn", f"filename={ass_burn}"])
        if convert_hdr:
            cmd.extend(["--vpp-ngx-truehdr"])
        return cmd

    # Updated: Extract subtitles by default regardless of burning selection.
    def encode_single_pass(self, file_path, qvbr_value, fruc_enable, fruc_fps_target,
                           generate_log, eight_bit, convert_to_hdr, convert_hdr):
        out_file, width, height = self.build_nvenc_command_and_run(file_path, None)
        # Now, regardless of burning, extract all embedded subtitle tracks (if any)
        if file_path in self.subtitles_by_file:
            output_dir = os.path.join(os.path.dirname(file_path),
                                      self.file_options[file_path].get("resolution", "4k"))
            base_name, ext = os.path.splitext(os.path.basename(file_path))
            print(f"DEBUG (encode_single_pass for subtitles): base_name: '{base_name}', ext: '{ext}'") # <<< ADDED DEBUG for completeness
            for sub in self.subtitles_by_file[file_path]:
                if sub["type"] == "embedded":
                    ass_path = os.path.join(output_dir, f"{base_name}_track{sub['track_id']}.ass")
                    srt_path = os.path.join(output_dir, f"{base_name}_track{sub['track_id']}.srt")
                    print(f"Extracting subtitles for track {sub['track_id']}...")
                    self.extract_embedded_subtitle_to_ass(file_path, ass_path, sub["track_id"], width, height)
                    self.extract_subtitle_to_srt(file_path, srt_path, sub["track_id"])
        options = self.file_options.get(file_path, {})
        convert_to_hdr = options.get("hdr", self.hdr_var.get())
        eight_bit = options.get("eight_bit", self.eight_bit_var.get())
        if convert_to_hdr and out_file:
            hdr_output = self.apply_hdr_settings(out_file, eight_bit)
            print(f"HDR => {hdr_output}")

    def encode_with_embedded_sub(self, file_path, sub_track_id, qvbr_value, fruc_enable,
                                   fruc_fps_target, generate_log, eight_bit, convert_to_hdr, convert_hdr):
        resolution = self.file_options.get(file_path, {}).get("resolution", self.resolution_var.get())
        base_name, ext = os.path.splitext(os.path.basename(file_path))
        print(f"DEBUG (encode_with_embedded_sub): base_name: '{base_name}', ext: '{ext}'") # <<< ADDED DEBUG for completeness
        output_dir = os.path.join(os.path.dirname(file_path), resolution)
        os.makedirs(output_dir, exist_ok=True)
        eight_bit_option = self.file_options.get(file_path, {}).get("eight_bit", self.eight_bit_var.get())
        if eight_bit_option:
            output_file = os.path.join(output_dir, f"{base_name}_track{sub_track_id}_8bit{ext}")
        else:
            output_file = os.path.join(output_dir, f"{base_name}_track{sub_track_id}{ext}")
        final_width, final_height = self.compute_final_resolution(file_path)
        ass_path = os.path.join(output_dir, f"{base_name}_track{sub_track_id}.ass")
        self.extract_embedded_subtitle_to_ass(file_path, ass_path, sub_track_id, final_width, final_height)
        srt_path = os.path.join(output_dir, f"{base_name}_track{sub_track_id}.srt")
        self.extract_subtitle_to_srt(file_path, srt_path, sub_track_id=sub_track_id)
        output_file_with_subs, _, _ = self.build_nvenc_command_and_run(file_path, output_file, ass_burn=ass_path)
        options = self.file_options.get(file_path, {})
        convert_to_hdr = options.get("hdr", self.hdr_var.get())
        eight_bit_val = options.get("eight_bit", self.eight_bit_var.get())
        if convert_to_hdr and output_file_with_subs:
            hdr_output = self.apply_hdr_settings(output_file_with_subs, eight_bit_val)
            print(f"HDR => {hdr_output}")

    def encode_with_external_srt(self, file_path, srt_file, qvbr_value, fruc_enable,
                                 fruc_fps_target, generate_log, eight_bit, convert_to_hdr, convert_hdr):
        resolution = self.file_options.get(file_path, {}).get("resolution", self.resolution_var.get())
        base_name, ext = os.path.splitext(os.path.basename(file_path))
        print(f"DEBUG (encode_with_external_srt): base_name: '{base_name}', ext: '{ext}'") # <<< ADDED DEBUG for completeness
        output_dir = os.path.join(os.path.dirname(file_path), resolution)
        os.makedirs(output_dir, exist_ok=True)
        srt_base = os.path.splitext(os.path.basename(srt_file))[0]
        print(f"DEBUG (encode_with_external_srt): srt_base: '{srt_base}'") # <<< ADDED DEBUG for srt_base
        eight_bit_option = self.file_options.get(file_path, {}).get("eight_bit", self.eight_bit_var.get())
        if eight_bit_option:
            output_file = os.path.join(output_dir, f"{base_name}_srt_{srt_base}_8bit{ext}")
        else:
            output_file = os.path.join(output_dir, f"{base_name}_srt_{srt_base}{ext}")
        final_width, final_height = self.compute_final_resolution(file_path)
        ass_path = os.path.join(output_dir, f"{base_name}_ext_{srt_base}.ass")
        self.extract_external_srt_to_ass(srt_file, ass_path, final_width, final_height)
        srt_path = os.path.join(output_dir, f"{base_name}_ext_{srt_base}.srt")
        self.extract_subtitle_to_srt(srt_file, srt_path)
        output_file_with_subs, _, _ = self.build_nvenc_command_and_run(file_path, output_file, ass_burn=ass_path)
        options = self.file_options.get(file_path, {})
        convert_to_hdr = options.get("hdr", self.hdr_var.get())
        eight_bit_val = options.get("eight_bit", self.eight_bit_var.get())
        if convert_to_hdr and output_file_with_subs:
            hdr_output = self.apply_hdr_settings(output_file_with_subs, eight_bit_val)
            print(f"HDR => {hdr_output}")

    def apply_hdr_settings(self, output_file, eight_bit):
        if eight_bit:
            print("8-bit selected: Skipping mkvmerge HDR tagging.")
            return output_file

        # STRIP OFF '_temp' TO GET FINAL FILENAME
        base, ext = os.path.splitext(output_file)
        print(f"DEBUG (apply_hdr_settings): base before _temp strip: '{base}', ext: '{ext}'") # <<< ADDED DEBUG
        if base.endswith("_temp"):
            final_base = base[:-5]
        else:
            final_base = base
        print(f"DEBUG (apply_hdr_settings): final_base after _temp strip: '{final_base}'") # <<< ADDED DEBUG
        merged_output = final_base + ext

        cube_file = self.lut_file
        if not os.path.exists(cube_file):
            print(f"LUT file not found: {cube_file}. Skipping HDR attachment.")
            return output_file

        cmd = [
            "mkvmerge.exe", "-o", merged_output,
            "--colour-matrix", "0:9", "--colour-range", "0:1",
            "--colour-transfer-characteristics", "0:16", "--colour-primaries", "0:9",
            "--max-content-light", "0:1000", "--max-frame-light", "0:400",
            "--max-luminance", "0:1000", "--min-luminance", "0:0.0001",
            "--chromaticity-coordinates", "0:0.708,0.292,0.170,0.797,0.131,0.046",
            "--white-colour-coordinates", "0:0.3127,0.3290",
            "--attachment-mime-type", "application/x-cube",
            "--attach-file", cube_file,
            output_file
        ]
        try:
            subprocess.run(cmd, check=True, env=env)
            print(f"mkvmerge complete => {merged_output}")
            try:
                os.remove(output_file)
                print(f"Deleted temporary file: {output_file}")
            except Exception as e_del:
                print(f"[ERROR] Error deleting temporary file {output_file}: {e_del}")
            return merged_output
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Error running mkvmerge: {e}")
            return output_file

    def compute_crop_value(self, file_path):
        options = self.file_options.get(file_path, {})
        crop_var = options.get("crop", self.crop_var.get())
        if not crop_var:
            return "0,0,0,0"
        input_width = get_input_width(file_path)
        resolution = options.get("resolution", self.resolution_var.get())
        if resolution == "4k":
            if input_width >= 3840:
                return "528,0,528,0"
            else:
                return "0,0,0,0"
        elif resolution == "8k":
            if input_width >= 7680:
                return "1056,0,1056,0"
            else:
                return "0,0,0,0"
        return "0,0,0,0"

    def start_processing(self):
        if not self.file_list:
            messagebox.showwarning("No Files", "Please add at least one file to process.")
            return
        self.root.destroy()  # Close the GUI
        for file_path in self.file_list:
            options = self.file_options.get(file_path, {})
            try:
                qvbr_value = int(options.get("qvbr", self.qvbr_var.get()))
                fruc_fps_target = int(options.get("fruc_fps", self.fruc_fps_var.get()))
            except ValueError:
                print("[ERROR] QVBR and FRUC FPS Target must be integers.")
                return
            fruc_enable = options.get("fruc", self.fruc_var.get())
            generate_log = options.get("generate_log", self.generate_log_var.get())
            eight_bit = options.get("eight_bit", self.eight_bit_var.get())
            convert_to_hdr = options.get("hdr", self.hdr_var.get())
            convert_hdr = options.get("convert_hdr", self.convert_hdr_var.get())
            self.encode_single_pass(
                file_path, qvbr_value, fruc_enable, fruc_fps_target,
                generate_log, eight_bit, convert_to_hdr, convert_hdr
            )
        print("Processing Complete.")


if __name__ == "__main__":
    import glob
    from tkinterdnd2 import TkinterDnD

    # 'os' and 'sys' are already imported at the top of the file.

    expanded_files = []

    # Check if any command-line arguments were provided
    if len(sys.argv) > 1:
        # If arguments are provided, process them as before.
        # This part remains consistent with the original script's handling of CLI arguments.
        print("[INFO] Processing files from command-line arguments...")
        for arg in sys.argv[1:]:
            if '*' in arg or '?' in arg:
                # glob.glob can return relative paths if the pattern is relative.
                # These are added to expanded_files as they are.
                glob_matches = glob.glob(arg, recursive=False)
                if not glob_matches:
                    print(f"[WARN] No files matched by pattern: {arg}")
                expanded_files.extend(glob_matches)
            else:
                # Direct file paths from arguments are added as they are (can be relative or absolute).
                expanded_files.append(arg)

        if not expanded_files:
            # This message is shown if CLI arguments were given but resulted in no files.
            # Crucially, it does NOT fall back to scanning the current directory in this case.
            print("[INFO] No valid files found based on the provided command-line arguments.")

    else:
        # No command-line arguments were provided, so scan the current directory.
        current_dir = os.getcwd()  # Gets the current working directory.
        # Define a list of common video file extensions to look for.
        video_extensions = [
            '.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv', '.wmv',
            '.mpg', '.mpeg', '.vob', '.ts', '.m2ts', '.mts', '.asf',
            '.divx', '.f4v', '.m4v'
        ]
        print(
            f"[INFO] No files provided via command line. Scanning current directory: {current_dir} for video files...")

        files_from_cwd = []
        for filename in os.listdir(current_dir):
            # Construct the full path to the file.
            # os.path.join will correctly create the path.
            # Since os.getcwd() returns an absolute path, file_path will also be absolute.
            file_path = os.path.join(current_dir, filename)

            # Check if it's a file (not a directory) and if its extension is in our list.
            if os.path.isfile(file_path):
                _, ext = os.path.splitext(filename)  # Get the file extension.
                if ext.lower() in video_extensions:  # Case-insensitive check.
                    print(f"[INFO] Found video file in CWD: {filename}")
                    files_from_cwd.append(file_path)  # Add the full path.

        # Sort the list of files found in the CWD alphabetically for a consistent order.
        expanded_files.extend(sorted(files_from_cwd))

        if not expanded_files:  # If the scan of the current directory also found no video files.
            print("[INFO] No video files found in the current directory.")

    # Initialize and run the Tkinter application with the (potentially empty) list of files.
    root = TkinterDnD.Tk()
    app = VideoProcessorApp(root, expanded_files)
    root.mainloop()