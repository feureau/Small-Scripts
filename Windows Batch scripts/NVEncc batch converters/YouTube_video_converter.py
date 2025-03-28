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
    Detects if the video is HDR by checking its color_transfer or color_primaries via ffprobe.
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
            color_transfer = stream.get("color_transfer", "").lower()  # e.g. "smpte2084"
            color_primaries = stream.get("color_primaries", "").lower()  # e.g. "bt2020"

            # Typical HDR color transfer markers
            if color_transfer in ["smpte2084", "arib-std-b67", "pq"]:
                return True
            # Another quick check: if color primaries is bt2020 => likely HDR
            if color_primaries == "bt2020":
                return True
        return False
    except Exception as e:
        print(f"[WARN] Could not detect HDR vs SDR for {file_path}: {e}")
        # default to False => treat as SDR
        return False


class VideoProcessorApp:
    def __init__(self, root, initial_files):
        self.root = root
        self.root.title("Video Processing Tool")

        # Path to the 3D LUT file for 8-bit conversion (if needed)
        self.lut_file = (
            r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\LUT\Colorspace LUTS\5-NBCU_PQ2SDR_DL_RESOLVE17-VRT_v1.2.cube"
        )

        # Subtitle management
        self.all_subs = []
        self.subtitle_id_counter = 0

        # File list
        self.file_list = []

        # We'll manage subtitles burn internally
        self.burn_subtitles_var = tk.BooleanVar(value=False)

        # Enable Drag-and-Drop
        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind("<<Drop>>", self.handle_file_drop)

        # ===============================
        # 1) FILE LIST + BUTTONS
        # ===============================
        self.file_frame = tk.Frame(root)
        self.file_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.file_listbox = tk.Listbox(self.file_frame, selectmode=tk.EXTENDED, height=15)
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.file_scrollbar = tk.Scrollbar(self.file_frame, orient=tk.VERTICAL, command=self.file_listbox.yview)
        self.file_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_listbox.config(yscrollcommand=self.file_scrollbar.set)

        self.file_buttons_frame = tk.Frame(root)
        self.file_buttons_frame.pack(fill=tk.X, padx=10, pady=5)

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

        # Resolution radio group: original, 4k, 8k
        tk.Label(self.options_frame, text="Resolution:").grid(row=0, column=0, sticky=tk.W)

        # Default to 4k
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

        # Convert to 8 bit
        tk.Label(self.options_frame, text="Convert to 8 bit:").grid(row=1, column=0, sticky=tk.W)
        self.eight_bit_var = tk.BooleanVar(value=False)
        self.eight_bit_checkbox = tk.Checkbutton(self.options_frame, variable=self.eight_bit_var)
        self.eight_bit_checkbox.grid(row=1, column=1, sticky=tk.W)

        # ** New: Convert to HDR
        tk.Label(self.options_frame, text="Convert to HDR:").grid(row=1, column=2, sticky=tk.W)
        self.hdr_var = tk.BooleanVar(value=False)
        self.hdr_checkbox = tk.Checkbutton(self.options_frame, variable=self.hdr_var)
        self.hdr_checkbox.grid(row=1, column=3, sticky=tk.W)

        # Vertical Crop
        tk.Label(self.options_frame, text="Vertical Crop:").grid(row=2, column=0, sticky=tk.W)
        self.crop_var = tk.BooleanVar(value=False)
        self.crop_checkbox = tk.Checkbutton(self.options_frame, variable=self.crop_var)
        self.crop_checkbox.grid(row=2, column=1, sticky=tk.W)

        # QVBR
        tk.Label(self.options_frame, text="QVBR Value:").grid(row=3, column=0, sticky=tk.W)
        self.qvbr_var = tk.StringVar(value="18")
        self.qvbr_entry = tk.Entry(self.options_frame, textvariable=self.qvbr_var, width=10)
        self.qvbr_entry.grid(row=3, column=1, sticky=tk.W)

        # FRUC
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

        # ===============================
        # SUBTITLE ALIGNMENT (Vertical)
        # ===============================
        tk.Label(self.options_frame, text="Subtitle Alignment:").grid(row=6, column=0, sticky=tk.W)
        self.alignment_var = tk.StringVar(value="middle")
        self.align_frame = tk.Frame(self.options_frame)
        self.align_frame.grid(row=6, column=1, columnspan=3, sticky=tk.W)

        self.align_top_rb = tk.Radiobutton(
            self.align_frame, text="Top", variable=self.alignment_var, value="top"
        )
        self.align_top_rb.pack(anchor="w")

        self.align_middle_rb = tk.Radiobutton(
            self.align_frame, text="Middle", variable=self.alignment_var, value="middle"
        )
        self.align_middle_rb.pack(anchor="w")

        self.align_bottom_rb = tk.Radiobutton(
            self.align_frame, text="Bottom", variable=self.alignment_var, value="bottom"
        )
        self.align_bottom_rb.pack(anchor="w")

        # ===============================
        # SUBTITLE TRACKS FRAME
        # ===============================
        self.subtitle_tracks_frame = tk.LabelFrame(root, text="Burn Subtitle Tracks", padx=10, pady=10)
        self.subtitle_tracks_frame.pack(fill=tk.X, padx=10, pady=5)

        self.subtitle_tracks_buttons_frame = tk.Frame(self.subtitle_tracks_frame)
        self.subtitle_tracks_buttons_frame.pack(fill=tk.X, padx=5, pady=5)

        self.load_embedded_srt_button = tk.Button(
            self.subtitle_tracks_buttons_frame,
            text="Load Embedded SRT",
            command=self.load_embedded_srt
        )
        self.load_embedded_srt_button.pack(side=tk.LEFT, padx=(0, 5))

        self.add_external_srt_button = tk.Button(
            self.subtitle_tracks_buttons_frame,
            text="Add External SRT",
            command=self.add_external_srt
        )
        self.add_external_srt_button.pack(side=tk.LEFT, padx=(0, 5))

        self.remove_srt_button = tk.Button(
            self.subtitle_tracks_buttons_frame,
            text="Remove Selected SRT",
            command=self.remove_selected_srt
        )
        self.remove_srt_button.pack(side=tk.LEFT, padx=(0, 5))

        self.subtitle_tracks_list_frame = tk.Frame(self.subtitle_tracks_frame)
        self.subtitle_tracks_list_frame.pack(fill=tk.X)

        # ===============================
        # BOTTOM FRAME: START + LOG
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

        # Add initial files if any passed from command line
        self.update_file_list(initial_files)
        for f in initial_files:
            self.detect_subtitle_tracks(f)
            self.auto_set_hdr(f)  # set HDR checkbox if needed

    # ===================================
    # Auto-set HDR if input is SDR
    # ===================================
    def auto_set_hdr(self, file_path):
        """
        If a file is detected as SDR, automatically check 'Convert to HDR'.
        If HDR, uncheck it.
        """
        hdr_detected = is_hdr(file_path)
        if hdr_detected:
            print(f"[Info] {file_path} is HDR. Unchecking Convert to HDR.")
            self.hdr_var.set(False)
        else:
            print(f"[Info] {file_path} is SDR. Checking Convert to HDR.")
            self.hdr_var.set(True)

    # ===================================
    # GET INPUT WIDTH
    # ===================================
    def get_input_width(self, file_path):
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
            return int(output.strip())
        except Exception as e:
            print(f"Error getting width from ffprobe: {e}")
            return 0

    def compute_crop_value(self, file_path):
        """
        Compute crop based on user selection of vertical_crop
        & the input size (4k vs. 8k).
        """
        if not self.crop_var.get():
            return "0,0,0,0"

        input_width = self.get_input_width(file_path)
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

    # ===================================
    # FILE & SUBTITLE DETECTION
    # ===================================
    def add_files(self):
        files = filedialog.askopenfilenames(
            filetypes=[("Video Files", "*.mp4;*.mkv;*.avi"), ("All Files", "*.*")]
        )
        self.update_file_list(files)
        for f in files:
            self.detect_subtitle_tracks(f)
            self.auto_set_hdr(f)

    def handle_file_drop(self, event):
        files = self.root.tk.splitlist(event.data)
        self.update_file_list(files)
        for f in files:
            self.detect_subtitle_tracks(f)
            self.auto_set_hdr(f)

    def update_file_list(self, files):
        for file in files:
            if file not in self.file_list:
                self.file_list.append(file)
                self.file_listbox.insert(tk.END, file)

    def detect_subtitle_tracks(self, file_path):
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

        if not all_tracks:
            print(f"No embedded subtitle tracks found in {file_path}.")
            return

        for track in all_tracks:
            desc = f"Embedded: #{track['track_id']} - {track['lang']}"
            if track["title"]:
                desc += f" ({track['title']})"

            sub_id = f"embed_{os.path.basename(file_path)}_{track['track_id']}_{self.subtitle_id_counter}"
            self.subtitle_id_counter += 1

            cvar = tk.BooleanVar(value=False)
            cb = tk.Checkbutton(
                self.subtitle_tracks_list_frame,
                text=desc,
                variable=cvar,
                command=lambda s_id=sub_id: self.on_subtitle_check(s_id),
                anchor="w"
            )
            cb.pack(fill="x", padx=20, anchor="w")

            self.all_subs.append({
                "id": sub_id,
                "type": "embedded",
                "file_path": file_path,
                "track_id": track["track_id"],
                "path": None,
                "description": desc,
                "widget": cb,
                "var": cvar,
            })

    # ===============================
    # CHECKBUTTON CALLBACK
    # ===============================
    def on_subtitle_check(self, sub_id):
        current_sub = next((s for s in self.all_subs if s["id"] == sub_id), None)
        if not current_sub:
            return

        if current_sub["var"].get() is True:
            # Uncheck all others
            for s in self.all_subs:
                if s["id"] != sub_id:
                    s["var"].set(False)
            self.burn_subtitles_var.set(True)
        else:
            any_checked = any(s["var"].get() for s in self.all_subs)
            if not any_checked:
                self.burn_subtitles_var.set(False)

    def get_selected_subtitle(self, file_path):
        sub_checked = next((s for s in self.all_subs if s["var"].get() is True), None)
        if not sub_checked:
            return None
        if sub_checked["type"] == "embedded" and sub_checked["file_path"] != file_path:
            return None
        return sub_checked

    # ===============================
    # MANAGING SUBTITLE & FILE LIST
    # ===============================
    def remove_selected(self):
        selected_indices = list(self.file_listbox.curselection())
        for index in reversed(selected_indices):
            file_to_remove = self.file_list[index]

            to_remove = []
            for s in self.all_subs:
                if (s["type"] == "embedded" and s["file_path"] == file_to_remove) or \
                   (s["type"] == "external" and s["path"] == file_to_remove):
                    to_remove.append(s)

            for sub in to_remove:
                sub["widget"].destroy()
                self.all_subs.remove(sub)

            del self.file_list[index]
            self.file_listbox.delete(index)

        if not any(s["var"].get() for s in self.all_subs):
            self.burn_subtitles_var.set(False)

    def clear_all(self):
        self.file_list.clear()
        self.file_listbox.delete(0, tk.END)
        for sub in self.all_subs:
            sub["widget"].destroy()
        self.all_subs.clear()
        self.burn_subtitles_var.set(False)

    def remove_selected_srt(self):
        for sub in self.all_subs[:]:
            if sub["type"] == "external" and sub["var"].get() is True:
                sub["widget"].destroy()
                self.all_subs.remove(sub)
                break

        if not any(s["var"].get() for s in self.all_subs):
            self.burn_subtitles_var.set(False)

    def load_embedded_srt(self):
        for file_path in self.file_list:
            self.detect_subtitle_tracks(file_path)

    def add_external_srt(self):
        # Use the directory of the first file in the list, if available
        initial_dir = None
        if self.file_list:
            initial_dir = os.path.dirname(self.file_list[0])

        srt_files = filedialog.askopenfilenames(
            filetypes=[("Subtitle Files", "*.srt"), ("All Files", "*.*")],
            initialdir=initial_dir
        )
        for s in srt_files:
            if not any(x["type"] == "external" and x["path"] == s for x in self.all_subs):
                desc = f"External: {os.path.basename(s)}"
                sub_id = f"ext_{os.path.basename(s)}_{self.subtitle_id_counter}"
                self.subtitle_id_counter += 1

                cvar = tk.BooleanVar(value=False)
                cb = tk.Checkbutton(
                    self.subtitle_tracks_list_frame,
                    text=desc,
                    variable=cvar,
                    command=lambda si=sub_id: self.on_subtitle_check(si),
                    anchor="w"
                )
                cb.pack(fill="x", padx=20, anchor="w")

                self.all_subs.append({
                    "id": sub_id,
                    "type": "external",
                    "file_path": None,
                    "track_id": None,
                    "path": s,
                    "description": desc,
                    "widget": cb,
                    "var": cvar,
                })

                # Automatically check this new external SRT
                cvar.set(True)
                self.on_subtitle_check(sub_id)

    # ===============================
    # MOVE UP / MOVE DOWN
    # ===============================
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
    # FRUC
    # ===============================
    def toggle_fruc_fps(self):
        if self.fruc_var.get():
            self.fruc_fps_entry.configure(state="normal")
        else:
            self.fruc_fps_entry.configure(state="disabled")

    # ===============================
    # SUBTITLE STYLE FIX
    # ===============================
    def fix_ass_style(self, ass_file):
        margin_v = 50
        alignment_map = {"top": 8, "middle": 5, "bottom": 2}
        alignment_code = alignment_map.get(self.alignment_var.get(), 2)

        if self.resolution_var.get() == "4k":
            screen_width = 2160
        elif self.resolution_var.get() == "8k":
            screen_width = 4320
        else:
            screen_width = 1080

        margin_l = margin_r = int(screen_width * 0.01875)
        if alignment_code == 5:  # middle
            margin_v = 0

        try:
            with open(ass_file, "r", encoding="utf-8") as f:
                lines = f.readlines()

            with open(ass_file, "w", encoding="utf-8") as f:
                in_styles = False
                for line in lines:
                    if line.strip().startswith("[V4+ Styles]"):
                        in_styles = True
                        f.write(line)
                        f.write(
                            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
                            "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
                            "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
                            "Alignment, MarginL, MarginR, MarginV, Encoding\n"
                        )
                        style_line = (
                            f"Style: Default,Futura,16,&H00FFFFFF,&H000000FF,&H00000000,&H64000000,"
                            f"-1,0,0,0,100,100,0,0,1,1,1,{alignment_code},{margin_l},{margin_r},{margin_v},1\n"
                        )
                        f.write(style_line)
                    elif in_styles and line.strip().startswith("Style:"):
                        continue
                    else:
                        f.write(line)
        except Exception as e:
            print(f"Error fixing style in {ass_file}: {e}")

    def extract_embedded_subtitle_to_ass(self, input_file, output_ass, sub_track_id):
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
            self.fix_ass_style(output_ass)
            print(f"Embedded track {sub_track_id} extracted as ASS => {output_ass}")
        except subprocess.CalledProcessError as e:
            print(f"Error extracting embedded subtitle track {sub_track_id}: {e}")

    def extract_external_srt_to_ass(self, srt_file, output_ass):
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
            self.fix_ass_style(output_ass)
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

        # close the GUI
        self.root.destroy()

        for file_path in self.file_list:
            sub_to_burn = None
            if self.burn_subtitles_var.get():
                sub_to_burn = self.get_selected_subtitle(file_path)

            if not sub_to_burn:
                self.encode_single_pass(
                    file_path, qvbr_value,
                    fruc_enable, fruc_fps_target,
                    generate_log, eight_bit, convert_to_hdr
                )
                continue

            if sub_to_burn["type"] == "external":
                self.encode_with_external_srt(
                    file_path, sub_to_burn["path"], qvbr_value,
                    fruc_enable, fruc_fps_target,
                    generate_log, eight_bit, convert_to_hdr
                )
            else:
                self.encode_with_embedded_sub(
                    file_path, sub_to_burn["track_id"], qvbr_value,
                    fruc_enable, fruc_fps_target,
                    generate_log, eight_bit, convert_to_hdr
                )

        print("Processing Complete.")
        os.system("pause")

    def encode_single_pass(
        self, file_path, qvbr_value,
        fruc_enable, fruc_fps_target,
        generate_log, eight_bit, convert_to_hdr
    ):
        resolution = self.resolution_var.get()
        output_dir = os.path.join(os.path.dirname(file_path), resolution)
        os.makedirs(output_dir, exist_ok=True)

        base_name, ext = os.path.splitext(os.path.basename(file_path))
        if eight_bit:
            output_file = os.path.join(output_dir, f"{base_name}_8bit{ext}")
        else:
            output_file = os.path.join(output_dir, f"{base_name}{ext}")

        cmd = self.build_nvenc_command(
            file_path, output_file, qvbr_value,
            fruc_enable, fruc_fps_target,
            generate_log, eight_bit
        )
        print("Running command:", " ".join(cmd))
        try:
            subprocess.run(cmd, check=True)
            print(f"Done: {file_path}")

            # If "Convert to HDR" is checked, apply HDR
            if convert_to_hdr:
                hdr_output = self.apply_hdr_settings(output_file, eight_bit)
                print(f"HDR => {hdr_output}")
        except subprocess.CalledProcessError as e:
            print(f"Error: {file_path}: {e}")

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

        # Extract => .ass & .srt
        ass_path = os.path.join(output_dir, f"{base_name}_track{sub_track_id}.ass")
        self.extract_embedded_subtitle_to_ass(file_path, ass_path, sub_track_id)

        srt_path = os.path.join(output_dir, f"{base_name}_track{sub_track_id}.srt")
        self.extract_subtitle_to_srt(file_path, srt_path, sub_track_id=sub_track_id)

        cmd = self.build_nvenc_command(
            file_path, output_file, qvbr_value,
            fruc_enable, fruc_fps_target,
            generate_log, eight_bit
        )
        cmd.extend(["--vpp-subburn", f"filename={ass_path}"])
        print("Running with embedded subtitles:", " ".join(cmd))
        try:
            subprocess.run(cmd, check=True)
            print(f"Done: {file_path} track {sub_track_id}")

            if convert_to_hdr:
                hdr_output = self.apply_hdr_settings(output_file, eight_bit)
                print(f"HDR => {hdr_output}")
        except subprocess.CalledProcessError as e:
            print(f"Error: {file_path} track {sub_track_id}: {e}")

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

        ass_path = os.path.join(output_dir, f"{base_name}_ext_{srt_base}.ass")
        self.extract_external_srt_to_ass(srt_file, ass_path)

        srt_path = os.path.join(output_dir, f"{base_name}_ext_{srt_base}.srt")
        self.extract_subtitle_to_srt(srt_file, srt_path, sub_track_id=None)

        cmd = self.build_nvenc_command(
            file_path, output_file, qvbr_value,
            fruc_enable, fruc_fps_target,
            generate_log, eight_bit
        )
        cmd.extend(["--vpp-subburn", f"filename={ass_path}"])
        print("Running with external SRT:", " ".join(cmd))
        try:
            subprocess.run(cmd, check=True)
            print(f"Done: {file_path} with {srt_file}")

            if convert_to_hdr:
                hdr_output = self.apply_hdr_settings(output_file, eight_bit)
                print(f"HDR => {hdr_output}")
        except subprocess.CalledProcessError as e:
            print(f"Error burning external SRT {srt_file} for {file_path}: {e}")

    # ===============================
    # NVEnc COMMAND
    # ===============================
    def build_nvenc_command(
        self, file_path, output_file,
        qvbr_value, fruc_enable, fruc_fps_target,
        generate_log, eight_bit
    ):
        resolution = self.resolution_var.get()
        input_width = self.get_input_width(file_path)
        do_resize = False
        resize_algo = "nvvfx-superres"
        target_res = "2160x2160"

        if resolution == "4k":
            if input_width < 3840:
                do_resize = True
                resize_algo = "nvvfx-superres"
                target_res = "2160x2160"
        elif resolution == "8k":
            if input_width < 7680:
                do_resize = True
                resize_algo = "ngx-vsr"
                target_res = "4320x4320"

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

        return cmd

    # ===============================
    # HDR SETTINGS
    # ===============================
    def apply_hdr_settings(self, output_file, eight_bit):
        """
        Applies HDR flags or merges LUT attachments for HDR, etc.
        If you want to force-skip HDR for 8-bit inputs, you can do so here as well.
        """
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


# ------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    from tkinterdnd2 import TkinterDnD
    initial_files = sys.argv[1:] if len(sys.argv) > 1 else []
    root = TkinterDnD.Tk()
    app = VideoProcessorApp(root, initial_files)
    root.mainloop()
