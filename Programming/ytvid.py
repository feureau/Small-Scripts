import os
import subprocess
import shutil
import json
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinterdnd2 import TkinterDnD, DND_FILES

def get_video_bit_depth(file_path):
    """
    Uses ffprobe to detect the bit depth of the input video file.
    Returns an integer (e.g., 8, 10, 12). Defaults to 8 on error or if not found.
    """
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=bits_per_raw_sample",
        "-of", "json",
        file_path
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        bit_depth = data.get("streams", [{}])[0].get("bits_per_raw_sample", None)
        if bit_depth is None:
            return 8
        return int(bit_depth)
    except Exception as e:
        print(f"[WARN] Could not detect bit depth for {file_path}: {e}")
        return 8

def is_hdr(file_path):
    """
    Detects if the video is HDR by checking color_transfer or color_primaries via ffprobe.
    If color_transfer is SMPTE2084 (PQ) or ARIB-STD-B67 (HLG), or color primaries are BT.2020,
    we consider it HDR. Otherwise, assume SDR.
    """
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=color_transfer,color_primaries",
        "-of", "json",
        file_path
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        if "streams" in data and len(data["streams"]) > 0:
            stream = data["streams"][0]
            color_transfer = stream.get("color_transfer", "").lower()
            color_primaries = stream.get("color_primaries", "").lower()
            # Typical HDR color_transfer markers
            if color_transfer in ["smpte2084", "arib-std-b67", "pq"]:
                return True
            if color_primaries == "bt2020":
                return True
        return False
    except Exception as e:
        print(f"[WARN] Could not detect HDR vs SDR for {file_path}: {e}")
        return False

def get_input_width(file_path):
    """
    Returns the input width in pixels using ffprobe.
    """
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width",
        "-of", "csv=p=0",
        file_path
    ]
    try:
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, universal_newlines=True)
        try:
            return int(output.strip())
        except ValueError:
            print(f"[ERROR] ffprobe output for width is not an integer: {output.strip()}")
            return 0 # Or consider returning None and handle it in the caller
    except Exception as e:
        print(f"[ERROR] Error getting width from ffprobe: {e}")
        return 0 # Or consider returning None and handle it in the caller

def get_input_height(file_path):
    """
    Returns the input height in pixels using ffprobe.
    """
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=height",
        "-of", "csv=p=0",
        file_path
    ]
    try:
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, universal_newlines=True)
        try:
            return int(output.strip())
        except ValueError:
            print(f"[ERROR] ffprobe output for height is not an integer: {output.strip()}")
            return 0 # Or consider returning None and handle it in the caller
    except Exception as e:
        print(f"[ERROR] Error getting height from ffprobe: {e}")
        return 0 # Or consider returning None and handle it in the caller

class VideoProcessorApp:
    def __init__(self, root, initial_files):
        self.root = root
        self.root.title("Video Processing Tool")
        # Path to the 3D LUT file for 8-bit conversion (if needed)
        self.lut_file = (
            r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\LUT\Colorspace LUTS\5-NBCU_PQ2SDR_DL_RESOLVE17-VRT_v1.2.cube"
        )
        # For subtitles
        self.subtitles_by_file = {}
        self.file_list = []
        self.subtitle_id_counter = 0
        self.current_subtitle_checkbuttons = []
        # Enable Drag-and-Drop
        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind("<<Drop>>", self.handle_file_drop)
        # ===============================
        # 1) FILE LIST + BUTTONS
        # ===============================
        self.file_frame = tk.Frame(root)
        self.file_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.file_listbox = tk.Listbox(self.file_frame, selectmode=tk.SINGLE, height=15)
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
        # ===============================
        # 2) OPTIONS SECTION
        # ===============================
        self.options_frame = tk.Frame(root)
        self.options_frame.pack(fill=tk.X, padx=10, pady=10)
        tk.Label(self.options_frame, text="Resolution:").grid(row=0, column=0, sticky=tk.W)
        self.resolution_var = tk.StringVar(value="4k")
        self.res_original_button = tk.Radiobutton(
            self.options_frame, text="Original", variable=self.resolution_var, value="original"
        )
        self.res_original_button.grid(row=0, column=1, sticky=tk.W)
        self.res_4k_button = tk.Radiobutton(
            self.options_frame, text="4k", variable=self.resolution_var, value="4k"
        )
        self.res_4k_button.grid(row=0, column=2, sticky=tk.W)
        self.res_8k_button = tk.Radiobutton(
            self.options_frame, text="8k", variable=self.resolution_var, value="8k"
        )
        self.res_8k_button.grid(row=0, column=3, sticky=tk.W)
        tk.Label(self.options_frame, text="Convert to 8 bit:").grid(row=1, column=0, sticky=tk.W)
        self.eight_bit_var = tk.BooleanVar(value=False)
        self.eight_bit_checkbox = tk.Checkbutton(self.options_frame, variable=self.eight_bit_var)
        self.eight_bit_checkbox.grid(row=1, column=1, sticky=tk.W)
        tk.Label(self.options_frame, text="Convert to HDR:").grid(row=1, column=2, sticky=tk.W)
        self.hdr_var = tk.BooleanVar(value=False)
        self.hdr_checkbox = tk.Checkbutton(self.options_frame, variable=self.hdr_var)
        self.hdr_checkbox.grid(row=1, column=3, sticky=tk.W)
        tk.Label(self.options_frame, text="Vertical Crop:").grid(row=2, column=0, sticky=tk.W)
        self.crop_var = tk.BooleanVar(value=False)
        self.crop_checkbox = tk.Checkbutton(self.options_frame, variable=self.crop_var)
        self.crop_checkbox.grid(row=2, column=1, sticky=tk.W)
        tk.Label(self.options_frame, text="QVBR Value:").grid(row=3, column=0, sticky=tk.W)
        self.qvbr_var = tk.StringVar(value="6")
        self.qvbr_entry = tk.Entry(self.options_frame, textvariable=self.qvbr_var, width=10)
        self.qvbr_entry.grid(row=3, column=1, sticky=tk.W)
        tk.Label(self.options_frame, text="Enable FRUC:").grid(row=4, column=0, sticky=tk.W)
        self.fruc_var = tk.BooleanVar(value=False)
        self.fruc_checkbox = tk.Checkbutton(
            self.options_frame,
            variable=self.fruc_var,
            command=self.toggle_fruc_fps
        )
        self.fruc_checkbox.grid(row=4, column=1, sticky=tk.W)
        tk.Label(self.options_frame, text="FRUC FPS Target:").grid(row=5, column=0, sticky=tk.W)
        self.fruc_fps_var = tk.StringVar(value="60")
        self.fruc_fps_entry = tk.Entry(self.options_frame, textvariable=self.fruc_fps_var, width=10)
        self.fruc_fps_entry.grid(row=5, column=1, sticky=tk.W)
        self.fruc_fps_entry.configure(state="disabled")
        tk.Label(self.options_frame, text="Subtitle Alignment:").grid(row=6, column=0, sticky=tk.W)
        self.alignment_var = tk.StringVar(value="middle")
        self.align_frame = tk.Frame(self.options_frame)
        self.align_frame.grid(row=6, column=1, columnspan=3, sticky=tk.W)
        self.align_top_rb = tk.Radiobutton(self.align_frame, text="Top", variable=self.alignment_var, value="top")
        self.align_top_rb.pack(anchor="w")
        self.align_middle_rb = tk.Radiobutton(self.align_frame, text="Middle", variable=self.alignment_var, value="middle")
        self.align_middle_rb.pack(anchor="w")
        self.align_bottom_rb = tk.Radiobutton(self.align_frame, text="Bottom", variable=self.alignment_var, value="bottom")
        self.align_bottom_rb.pack(anchor="w")
        tk.Label(self.options_frame, text="Subtitle Font Size:").grid(row=7, column=0, sticky=tk.W)
        self.subtitle_font_size_var = tk.StringVar(value="12")
        self.subtitle_font_size_entry = tk.Entry(self.options_frame, textvariable=self.subtitle_font_size_var, width=10)
        self.subtitle_font_size_entry.grid(row=7, column=1, sticky=tk.W)
        # ===============================
        # SUBTITLE TRACKS FRAME
        # ===============================
        self.subtitle_tracks_frame = tk.LabelFrame(root, text="Burn Subtitle Tracks", padx=10, pady=10)
        self.subtitle_tracks_frame.pack(fill=tk.X, padx=10, pady=5)
        self.subtitle_tracks_buttons_frame = tk.Frame(self.subtitle_tracks_frame)
        self.subtitle_tracks_buttons_frame.pack(fill=tk.X, padx=5, pady=5)
        self.load_embedded_srt_button = tk.Button(
            self.subtitle_tracks_buttons_frame,
            text="Load Embedded SRT (All Files)",
            command=self.load_embedded_srt_all
        )
        self.load_embedded_srt_button.pack(side=tk.LEFT, padx=(0, 5))
        self.add_external_srt_button = tk.Button(
            self.subtitle_tracks_buttons_frame,
            text="Add External SRT (Current File)",
            command=self.add_external_srt
        )
        self.add_external_srt_button.pack(side=tk.LEFT, padx=(0, 5))
        self.remove_srt_button = tk.Button(
            self.subtitle_tracks_buttons_frame,
            text="Remove Selected SRT (Current File)",
            command=self.remove_selected_srt
        )
        self.remove_srt_button.pack(side=tk.LEFT, padx=(0, 5))
        self.subtitle_tracks_list_frame = tk.Frame(self.subtitle_tracks_frame)
        self.subtitle_tracks_list_frame.pack(fill=tk.X)
        # ===============================
        # BOTTOM FRAME
        # ===============================
        self.bottom_frame = tk.Frame(root)
        self.bottom_frame.pack(pady=10, padx=10, fill=tk.X)
        self.start_button = tk.Button(self.bottom_frame, text="Start Processing", command=self.start_processing)
        self.start_button.pack(side=tk.LEFT, padx=5)
        self.generate_log_var = tk.BooleanVar(value=False)
        self.generate_log_checkbox = tk.Checkbutton(
            self.bottom_frame,
            text="Generate Log File",
            variable=self.generate_log_var
        )
        self.generate_log_checkbox.pack(side=tk.LEFT, padx=(10, 0))
        # Add initial files
        self.update_file_list(initial_files)
        for f in initial_files:
            self.auto_set_hdr(f)
        # Select first item if available
        if self.file_listbox.size() > 0:
            self.file_listbox.select_set(0)
            self.on_file_select(None)
    # ===============================
    # NEW METHOD: load_embedded_srt_all
    # ===============================
    def load_embedded_srt_all(self):
        """
        Loads embedded subtitles for all files in the list.
        Then refresh the UI.
        """
        for file_path in self.file_list:
            self.detect_subtitle_tracks(file_path)
        self.refresh_subtitle_list()
    # ===============================
    # HDR / FILE HANDLING
    # ===============================
    def auto_set_hdr(self, file_path):
        hdr_detected = is_hdr(file_path)
        if hdr_detected:
            print(f"[Info] {file_path} is HDR. Unchecking Convert to HDR.")
            self.hdr_var.set(False)
        else:
            print(f"[Info] {file_path} is SDR. Checking Convert to HDR.")
            self.hdr_var.set(True)
    def add_files(self):
        files = filedialog.askopenfilenames(
            filetypes=[("Video Files", "*.mp4;*.mkv;*.avi"), ("All Files", "*.*")]
        )
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
        for file in files:
            if file not in self.file_list:
                self.file_list.append(file)
                self.file_listbox.insert(tk.END, file)
                self.subtitles_by_file[file] = []
                self.detect_subtitle_tracks(file)
    def select_all_files(self):
        self.file_listbox.select_set(0, tk.END)
    def remove_selected(self):
        selected_indices = list(self.file_listbox.curselection())
        for index in reversed(selected_indices):
            file_to_remove = self.file_list[index]
            if file_to_remove in self.subtitles_by_file:
                del self.subtitles_by_file[file_to_remove]
            del self.file_list[index]
            self.file_listbox.delete(index)
        self.refresh_subtitle_list()
    def clear_all(self):
        self.file_list.clear()
        self.file_listbox.delete(0, tk.END)
        self.subtitles_by_file.clear()
        self.refresh_subtitle_list()
    def move_up(self):
        selected_indices = list(self.file_listbox.curselection())
        if not selected_indices or selected_indices[0] == 0:
            return
        for index in selected_indices:
            if index > 0:
                self.file_list[index], self.file_list[index - 1] = (
                    self.file_list[index - 1],
                    self.file_list[index],
                )
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
                self.file_list[index], self.file_list[index + 1] = (
                    self.file_list[index + 1],
                    self.file_list[index],
                )
                self.file_listbox.delete(index)
                self.file_listbox.insert(index + 1, self.file_list[index + 1])
                self.file_listbox.select_set(index + 1)
                self.file_listbox.select_clear(index)
    # ===============================
    # SUBTITLE DETECTION
    # ===============================
    def detect_subtitle_tracks(self, file_path):
        """
        Probe for embedded subtitles, auto-select if vertical (height>width).
        Defensive check for 'track_id' to handle potential ffprobe output issues.
        """
        cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "s",
            "-show_entries", "stream=index:stream_tags=language:stream_tags=title",
            "-of", "default=noprint_wrappers=1",
            file_path
        ]
        print("Detecting subtitles with:", " ".join(cmd))
        try:
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, universal_newlines=True)
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

        # Decide if vertical by checking raw width vs. height
        w = get_input_width(file_path)
        h = get_input_height(file_path)
        is_vertical = (h > w)
        existing_embedded_ids = {
            s["track_id"] for s in self.subtitles_by_file[file_path] if s["type"] == "embedded"
        }
        for track in all_tracks:
            # Defensive check: Ensure 'track_id' key exists before accessing it
            if "track_id" not in track:
                print(f"[WARN] Subtitle track info is missing 'track_id', skipping track: {track}")
                continue  # Skip this track if track_id is missing

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
                "track_id": track["track_id"],
                "path": None,
                "description": desc,
                "selected": is_vertical,  # auto select if vertical
                "checkbutton": None,
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
        srt_files = filedialog.askopenfilenames(
            filetypes=[("Subtitle Files", "*.srt"), ("All Files", "*.*")],
            initialdir=initial_dir
        )
        for s in srt_files:
            already_exists = any(
                (x["type"] == "external" and x["path"] == s)
                for x in self.subtitles_by_file[current_file]
            )
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
                "checkbutton": None,
            })
        self.refresh_subtitle_list()

    def remove_selected_srt(self):
        sel = self.file_listbox.curselection()
        if not sel:
            return
        file_idx = sel[0]
        current_file = self.file_list[file_idx]
        for sub in self.subtitles_by_file[current_file]:
            if sub["selected"] and sub["type"] == "external":
                self.subtitles_by_file[current_file].remove(sub)
                break
        self.refresh_subtitle_list()

    def on_file_select(self, event):
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
            cb = tk.Checkbutton(
                self.subtitle_tracks_list_frame,
                text=sub["description"],
                variable=var,
                anchor="w",
                command=lambda s=sub, v=var: self.on_subtitle_check(s, v)
            )
            cb.pack(fill="x", padx=20, anchor="w")
            sub["checkbutton"] = cb
            self.current_subtitle_checkbuttons.append(cb)

    def on_subtitle_check(self, sub, var):
        sel = self.file_listbox.curselection()
        if not sel:
            return
        file_idx = sel[0]
        current_file = self.file_list[file_idx]
        if var.get():
            for s in self.subtitles_by_file[current_file]:
                if s["id"] != sub["id"]:
                    s["selected"] = False
                    if s["checkbutton"]:
                        s["checkbutton"].deselect()
            sub["selected"] = True
        else:
            sub["selected"] = False

    # ===============================
    # FRUC
    # ===============================
    def toggle_fruc_fps(self):
        if self.fruc_var.get():
            self.fruc_fps_entry.configure(state="normal")
        else:
            self.fruc_fps_entry.configure(state="disabled")

    # ===============================
    # STYLE FIX
    # ===============================
    def fix_ass_style(self, ass_file, final_width, final_height):
        """
        Skip existing Format/Style lines after we inject ours,
        so there's only one set of 'Format:' lines in [V4+ Styles].
        """
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
                        # Our single "Format" + "Style" lines
                        f.write(
                            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
                            "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
                            "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
                            "Alignment, MarginL, MarginR, MarginV, Encoding\n"
                        )
                        style_line = (
                            f"Style: Default,Futura,{font_size},&H00FFFFFF,&H000000FF,&H00000000,&H64000000,"
                            f"-1,0,0,0,100,100,0,0,1,1,1,{alignment_code},{margin_l},{margin_r},{margin_v},1\n"
                        )
                        f.write(style_line)
                        continue
                    if in_styles:
                        if line.strip().startswith("Format:") or line.strip().startswith("Style:"):
                            continue
                    f.write(line)
            # >>> CALL overlap fixer right here <<<
            self.fix_overlapping_subtitle_lines(ass_file)
        except Exception as e:
            print(f"Error fixing style in {ass_file}: {e}")

    # ===============================
    # NEW FUNCTION: DETECT & FIX OVERLAPPING TIMESTAMPS
    # ===============================
    def fix_overlapping_subtitle_lines(self, ass_file):
        """
        Scans the [Events] section of the given .ass file and fixes any
        overlapping subtitles by ensuring each start time >= previous end time.
        If an overlap is found, the start time is pushed slightly forward.
        """
        def ass_time_to_seconds(t):
            # Format is H:MM:SS.xx (or H:MM:SS.mmm)
            # e.g. "0:00:14.33"
            # We'll parse hour, minute, second.fraction
            parts = t.split(':')
            if len(parts) != 3:
                return 0.0
            hh = int(parts[0])
            mm = int(parts[1])
            ss = float(parts[2])
            return hh * 3600 + mm * 60 + ss

        def seconds_to_ass_time(s):
            # Convert float seconds back to H:MM:SS.xx
            hh = int(s // 3600)
            s_mod = s % 3600
            mm = int(s_mod // 60)
            ss = s_mod % 60
            return f"{hh}:{mm:02d}:{ss:05.2f}"

        try:
            with open(ass_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception as e:
            print(f"Error reading for overlap fixing: {e}")
            return

        in_events = False
        last_end = 0.0
        new_lines = []
        for line in lines:
            # Check if we've entered the [Events] section
            if line.strip().startswith("[Events]"):
                in_events = True
                new_lines.append(line)
                continue
            # If we hit another section after [Events], we exit that mode
            if in_events and line.strip().startswith("["):
                in_events = False
                new_lines.append(line)
                continue
            if in_events and line.strip().startswith("Dialogue:"):
                # Dialogue line format: Dialogue: 0,<start>,<end>,...
                parts = line.split(",")
                if len(parts) >= 3:
                    # parts[1] -> start, parts[2] -> end
                    start_ts = parts[1]
                    end_ts = parts[2]
                    start_sec = ass_time_to_seconds(start_ts)
                    end_sec = ass_time_to_seconds(end_ts)

                    # Fix overlap if start is < last_end
                    if start_sec < last_end:
                        # Bump the start time slightly forward
                        start_sec = last_end + 0.01
                        # If that ends up beyond end_sec, we might also shift end_sec
                        if start_sec > end_sec:
                            end_sec = start_sec + 1.0

                    # Re-assemble line
                    new_start_str = seconds_to_ass_time(start_sec)
                    new_end_str = seconds_to_ass_time(end_sec)
                    # Update last_end
                    last_end = end_sec
                    # Rebuild "Dialogue: 0,start,end,..." by replacing parts[1] and [2]
                    parts[1] = new_start_str
                    parts[2] = new_end_str
                    line = ",".join(parts)
            new_lines.append(line)

        # Write back
        try:
            with open(ass_file, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
        except Exception as e:
            print(f"Error writing fixed overlaps: {e}")

    # ===============================
    # EXTRACTING SUBTITLES
    # ===============================
    def extract_embedded_subtitle_to_ass(self, input_file, output_ass, sub_track_id, final_width, final_height):
        cmd = [
            "ffmpeg",
            "-sub_charenc", "UTF-8",
            "-i", input_file,
            "-map", f"0:{sub_track_id}",
            "-c:s", "ass",
            output_ass,
        ]
        print(f"Extracting embedded subtitle track {sub_track_id} => {output_ass}")
        try:
            subprocess.run(cmd, check=True)
            self.fix_ass_style(output_ass, final_width, final_height)
            print(f"Embedded track {sub_track_id} extracted as ASS => {output_ass}")
        except subprocess.CalledProcessError as e:
            print(f"Error extracting embedded subtitle track {sub_track_id}: {e}")

    def extract_external_srt_to_ass(self, srt_file, output_ass, final_width, final_height):
        cmd = [
            "ffmpeg",
            "-sub_charenc", "UTF-8",
            "-i", srt_file,
            "-c:s", "ass",
            output_ass,
        ]
        print(f"Converting external SRT => ASS: {' '.join(cmd)}")
        try:
            subprocess.run(cmd, check=True)
            self.fix_ass_style(output_ass, final_width, final_height)
        except subprocess.CalledProcessError as e:
            print(f"Error converting external SRT {srt_file}: {e}")

    def extract_subtitle_to_srt(self, input_file, output_srt, sub_track_id=None):
        if sub_track_id is not None:
            cmd = [
                "ffmpeg",
                "-sub_charenc", "UTF-8",
                "-i", input_file,
                "-map", f"0:{sub_track_id}",
                "-c:s", "srt",
                output_srt,
            ]
            print(f"Extracting embedded track => SRT: {' '.join(cmd)}")
            try:
                subprocess.run(cmd, check=True)
                print(f"Extracted to {output_srt}")
            except subprocess.CalledProcessError as e:
                print(f"Error extracting SRT from track {sub_track_id}: {e}")
        else:
            print(f"Copying external SRT => {output_srt}")
            try:
                shutil.copyfile(input_file, output_srt)
                print(f"Copied {input_file} => {output_srt}")
            except Exception as e:
                print(f"Error copying external SRT {input_file}: {e}")

    # ===============================
    # MAIN PROCESSING
    # ===============================
    def start_processing(self):
        if not self.file_list:
            messagebox.showwarning("No Files", "Please add at least one file to process.")
            return

        qvbr_value = self.qvbr_var.get()
        fruc_enable = self.fruc_var.get()
        fruc_fps_target = self.fruc_fps_var.get()
        generate_log = self.generate_log_var.get()
        eight_bit = self.eight_bit_var.get()
        convert_to_hdr = self.hdr_var.get()

        try:
            qvbr_value = int(qvbr_value)
            fruc_fps_target = int(fruc_fps_target)
        except ValueError:
            messagebox.showerror("Invalid Input", "QVBR and FRUC FPS Target must be integers.")
            return

        # close GUI
        self.root.destroy()

        for file_path in self.file_list:
            chosen_sub = None
            # find any sub selected for burning
            if file_path in self.subtitles_by_file:
                for sub in self.subtitles_by_file[file_path]:
                    if sub["selected"]:
                        chosen_sub = sub
                        break

            if not chosen_sub:
                # no sub => single pass
                self.encode_single_pass(
                    file_path, qvbr_value,
                    fruc_enable, fruc_fps_target,
                    generate_log, eight_bit, convert_to_hdr
                )
            else:
                # we have a chosen sub
                if chosen_sub["type"] == "embedded":
                    self.encode_with_embedded_sub(
                        file_path, chosen_sub["track_id"],
                        qvbr_value, fruc_enable, fruc_fps_target,
                        generate_log, eight_bit, convert_to_hdr
                    )
                else:
                    self.encode_with_external_srt(
                        file_path, chosen_sub["path"],
                        qvbr_value, fruc_enable, fruc_fps_target,
                        generate_log, eight_bit, convert_to_hdr
                    )

        print("Processing Complete.")
        # os.system("pause") # Removed Windows-specific pause, just let console exit

    def compute_final_resolution(self, file_path):
        resolution = self.resolution_var.get()
        in_w = get_input_width(file_path)
        in_h = get_input_height(file_path)
        if resolution == "original":
            return in_w, in_h
        elif resolution == "4k":
            # User wants 2160x2160, do not change
            return 2160, 2160
        elif resolution == "8k":
            # User wants 4320x4320, do not change
            return 4320, 4320
        else:
            return in_w, in_h

    def build_nvenc_command_and_run(
        self, file_path, output_file, qvbr_value,
        fruc_enable, fruc_fps_target, generate_log, eight_bit,
        ass_burn=None
    ):
        resolution = self.resolution_var.get()
        if output_file is None:
            output_dir = os.path.join(os.path.dirname(file_path), resolution)
            os.makedirs(output_dir, exist_ok=True)
            base_name, ext = os.path.splitext(os.path.basename(file_path))
            if eight_bit:
                output_file = os.path.join(output_dir, f"{base_name}_8bit{ext}")
            else:
                output_file = os.path.join(output_dir, f"{base_name}{ext}")

        final_width, final_height = self.compute_final_resolution(file_path)
        do_resize = resolution in ["4k", "8k"]
        resize_algo = "nvvfx-superres"
        target_res = f"{final_width}x{final_height}"

        cmd = [
            "NVEncC64",
            "--avhw",
            "--codec", "av1",
            "--qvbr", str(qvbr_value),
            "--preset", "p1",
            "--output-depth", "8" if eight_bit else "10",
            "--audio-copy",
            "--sub-copy",
            "--chapter-copy",
            "--key-on-chapter",
            "--transfer", "bt709" if eight_bit else "auto",
            "--colorprim", "bt709" if eight_bit else "auto",
            "--colormatrix", "bt709" if eight_bit else "auto",
            "--lookahead", "32",
            "--aq-temporal",
            "--multipass", "2pass-full",
            "--log-level", "info",
            "--output", output_file,
            "-i", file_path,
        ]

        if eight_bit and os.path.exists(self.lut_file):
            cmd.extend([
                "--vpp-colorspace", f"lut3d={self.lut_file},lut3d_interp=trilinear"
            ])
            print(f"Applying LUT: {self.lut_file}")

        if do_resize:
            cmd.extend([
                "--vpp-resize", f"algo={resize_algo}",
                "--output-res", f"{target_res},preserve_aspect_ratio=increase"
            ])

        crop_str = self.compute_crop_value(file_path)
        if crop_str != "0,0,0,0":
            cmd.extend(["--crop", crop_str])

        if fruc_enable:
            cmd.extend(["--vpp-fruc", f"fps={fruc_fps_target}"])

        if generate_log:
            cmd.extend(["--log", "log.log", "--log-level", "debug"])

        if ass_burn:
            cmd.extend(["--vpp-subburn", f"filename={ass_burn}"])

        print("Running command:", " ".join(cmd))
        try:
            subprocess.run(cmd, check=True)
            print(f"Done: {file_path}")
            return (output_file, final_width, final_height)
        except subprocess.CalledProcessError as e:
            print(f"Error encoding {file_path}: {e}")
            return (None, final_width, final_height)

    def encode_single_pass(
        self, file_path, qvbr_value,
        fruc_enable, fruc_fps_target,
        generate_log, eight_bit, convert_to_hdr
    ):
        out_file, _,_ = self.build_nvenc_command_and_run(
            file_path, None, qvbr_value,
            fruc_enable, fruc_fps_target,
            generate_log, eight_bit
        )
        if convert_to_hdr and out_file:
            hdr_output = self.apply_hdr_settings(out_file, eight_bit)
            print(f"HDR => {hdr_output}")

    def encode_with_embedded_sub(
        self, file_path, sub_track_id,
        qvbr_value, fruc_enable, fruc_fps_target,
        generate_log, eight_bit, convert_to_hdr
    ):
        resolution = self.resolution_var.get()
        base_name, ext = os.path.splitext(os.path.basename(file_path))
        output_dir = os.path.join(os.path.dirname(file_path), resolution)
        os.makedirs(output_dir, exist_ok=True)
        if eight_bit:
            output_file = os.path.join(output_dir, f"{base_name}_track{sub_track_id}_8bit{ext}")
        else:
            output_file = os.path.join(output_dir, f"{base_name}_track{sub_track_id}{ext}")
        final_width, final_height = self.compute_final_resolution(file_path)

        # Extract => .ass & .srt
        ass_path = os.path.join(output_dir, f"{base_name}_track{sub_track_id}.ass")
        self.extract_embedded_subtitle_to_ass(file_path, ass_path, sub_track_id, final_width, final_height)
        srt_path = os.path.join(output_dir, f"{base_name}_track{sub_track_id}.srt")
        self.extract_subtitle_to_srt(file_path, srt_path, sub_track_id=sub_track_id)

        self.build_nvenc_command_and_run(
            file_path, output_file, qvbr_value,
            fruc_enable, fruc_fps_target,
            generate_log, eight_bit, ass_burn=ass_path
        )

        if convert_to_hdr:
            hdr_output = self.apply_hdr_settings(output_file, eight_bit)
            print(f"HDR => {hdr_output}")

    def encode_with_external_srt(
        self, file_path, srt_file,
        qvbr_value, fruc_enable, fruc_fps_target,
        generate_log, eight_bit, convert_to_hdr
    ):
        resolution = self.resolution_var.get()
        base_name, ext = os.path.splitext(os.path.basename(file_path))
        output_dir = os.path.join(os.path.dirname(file_path), resolution)
        os.makedirs(output_dir, exist_ok=True)
        srt_base = os.path.splitext(os.path.basename(srt_file))[0]
        if eight_bit:
            output_file = os.path.join(output_dir, f"{base_name}_srt_{srt_base}_8bit{ext}")
        else:
            output_file = os.path.join(output_dir, f"{base_name}_srt_{srt_base}{ext}")
        final_width, final_height = self.compute_final_resolution(file_path)

        ass_path = os.path.join(output_dir, f"{base_name}_ext_{srt_base}.ass")
        self.extract_external_srt_to_ass(srt_file, ass_path, final_width, final_height)
        srt_path = os.path.join(output_dir, f"{base_name}_ext_{srt_base}.srt")
        self.extract_subtitle_to_srt(srt_file, srt_path)

        self.build_nvenc_command_and_run(
            file_path, output_file, qvbr_value,
            fruc_enable, fruc_fps_target,
            generate_log, eight_bit, ass_burn=ass_path
        )

        if convert_to_hdr:
            hdr_output = self.apply_hdr_settings(output_file, eight_bit)
            print(f"HDR => {hdr_output}")

    def apply_hdr_settings(self, output_file, eight_bit):
        if eight_bit:
            print("8-bit selected: Skipping mkvmerge HDR tagging.")
            return output_file

        base, ext = os.path.splitext(output_file)
        merged_output = base + "_HDR_CUBE" + ext
        cube_file = (
            r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\LUT\Colorspace LUTS\5-NBCU_PQ2SDR_DL_RESOLVE17-VRT_v1.2.cube"
        )
        if not os.path.exists(cube_file):
            print(f"LUT file not found: {cube_file}. Skipping HDR attachment.")
            return output_file

        cmd = [
            "mkvmerge.exe",
            "-o", merged_output,
            "--colour-matrix", "0:9",
            "--colour-range", "0:1",
            "--colour-transfer-characteristics", "0:16",
            "--colour-primaries", "0:9",
            "--max-content-light", "0:1000",
            "--max-frame-light", "0:300",
            "--max-luminance", "0:1000",
            "--min-luminance", "0:0.01",
            "--chromaticity-coordinates", "0:0.68,0.32,0.265,0.69,0.15,0.06",
            "--white-colour-coordinates", "0:0.3127,0.3290",
            "--attachment-mime-type", "application/x-cube",
            "--attach-file", cube_file,
            output_file
        ]
        print("Attaching LUT and setting HDR flags:")
        print(" ".join(cmd))
        try:
            subprocess.run(cmd, check=True)
            print(f"mkvmerge complete => {merged_output}")
            try:
                os.remove(output_file)
                print(f"Deleted original file: {output_file}")
            except Exception as e_del:
                print(f"Error deleting original file {output_file}: {e_del}")
            return merged_output
        except subprocess.CalledProcessError as e:
            print(f"Error running mkvmerge: {e}")
            return output_file

    def compute_crop_value(self, file_path):
        """
        If 'Vertical Crop' is checked, remove some pixels from left/right if big enough,
        else no crop.
        """
        if not self.crop_var.get():
            return "0,0,0,0"
        input_width = get_input_width(file_path)
        resolution = self.resolution_var.get()
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

# ------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    import glob
    from tkinterdnd2 import TkinterDnD

    # Expand wildcards in arguments (works on Windows/Linux)
    expanded_files = []
    for arg in sys.argv[1:]:
        if '*' in arg or '?' in arg:
            expanded_files.extend(glob.glob(arg, recursive=False))
        else:
            expanded_files.append(arg)

    root = TkinterDnD.Tk()
    app = VideoProcessorApp(root, expanded_files)
    root.mainloop()