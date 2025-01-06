import os
import subprocess
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinterdnd2 import TkinterDnD, DND_FILES

class VideoProcessorApp:
    def __init__(self, root, initial_files):
        self.root = root
        self.root.title("Video Processing Tool")

        # Data structures
        self.file_list = []
        self.subtitle_tracks = {}  # { file_path: [ {track_id, lang, title, selected}, ... ] }
        self.external_srt = []     # [ {path: str, selected: tk.BooleanVar}, ... ]

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

        # Initialize file list from command-line arguments
        self.update_file_list(initial_files)

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

        # Resolution
        tk.Label(self.options_frame, text="Resolution:").grid(row=0, column=0, sticky=tk.W)
        self.resolution_var = tk.StringVar(value="4k")
        self.res_4k_button = tk.Radiobutton(
            self.options_frame, text="4k", variable=self.resolution_var, value="4k", command=self.update_qvbr
        )
        self.res_4k_button.grid(row=0, column=1, sticky=tk.W)
        self.res_8k_button = tk.Radiobutton(
            self.options_frame, text="8k", variable=self.resolution_var, value="8k", command=self.update_qvbr
        )
        self.res_8k_button.grid(row=0, column=2, sticky=tk.W)

        # Upscale
        tk.Label(self.options_frame, text="Upscale:").grid(row=1, column=0, sticky=tk.W)
        self.upscale_var = tk.BooleanVar(value=True)
        self.upscale_checkbox = tk.Checkbutton(self.options_frame, variable=self.upscale_var)
        self.upscale_checkbox.grid(row=1, column=1, sticky=tk.W)

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
            self.options_frame, variable=self.fruc_var, command=self.toggle_fruc_fps
        )
        self.fruc_checkbox.grid(row=4, column=1, sticky=tk.W)

        tk.Label(self.options_frame, text="FRUC FPS Target:").grid(row=5, column=0, sticky=tk.W)
        self.fruc_fps_var = tk.StringVar(value="60")
        self.fruc_fps_entry = tk.Entry(self.options_frame, textvariable=self.fruc_fps_var, width=10)
        self.fruc_fps_entry.grid(row=5, column=1, sticky=tk.W)
        self.fruc_fps_entry.configure(state="disabled")

        # Burn Subtitles
        tk.Label(self.options_frame, text="Burn Subtitles:").grid(row=6, column=0, sticky=tk.W)
        self.burn_subtitles_var = tk.BooleanVar(value=False)
        self.burn_subtitles_checkbox = tk.Checkbutton(
            self.options_frame, variable=self.burn_subtitles_var, command=self.toggle_burn_subtitles
        )
        self.burn_subtitles_checkbox.grid(row=6, column=1, sticky=tk.W)

        # MarginV
        self.marginv_var = tk.StringVar()
        self.marginv_label = tk.Label(self.options_frame, text="MarginV:")
        self.marginv_entry = tk.Entry(self.options_frame, textvariable=self.marginv_var, width=10)
        self.marginv_label.grid(row=6, column=2, sticky=tk.W, padx=(10,0))
        self.marginv_entry.grid(row=6, column=3, sticky=tk.W)
        self.marginv_label.grid_remove()
        self.marginv_entry.grid_remove()

        # ===============================
        # 3) SUBTITLE ALIGNMENT (Vertical)
        # ===============================
        tk.Label(self.options_frame, text="Subtitle Alignment:").grid(row=7, column=0, sticky=tk.W)
        self.alignment_var = tk.StringVar(value="bottom")  # Default = bottom
        self.align_frame = tk.Frame(self.options_frame)
        self.align_frame.grid(row=7, column=1, columnspan=3, sticky=tk.W)

        self.align_top_rb = tk.Radiobutton(self.align_frame, text="Top", variable=self.alignment_var, value="top")
        self.align_top_rb.pack(anchor="w")

        self.align_middle_rb = tk.Radiobutton(self.align_frame, text="Middle", variable=self.alignment_var, value="middle")
        self.align_middle_rb.pack(anchor="w")

        self.align_bottom_rb = tk.Radiobutton(self.align_frame, text="Bottom", variable=self.alignment_var, value="bottom")
        self.align_bottom_rb.pack(anchor="w")

        # ===============================
        # EMBEDDED SUBTITLE TRACKS FRAME
        # ===============================
        self.subtitle_tracks_frame = tk.LabelFrame(root, text="Embedded Subtitle Tracks", padx=10, pady=10)
        self.subtitle_tracks_frame.pack(fill=tk.X, padx=10, pady=5)

        # ===============================
        # EXTERNAL SRT FILES FRAME + BUTTON
        # ===============================
        self.external_srt_frame = tk.LabelFrame(root, text="External SRT Files", padx=10, pady=10)
        self.external_srt_frame.pack(fill=tk.X, padx=10, pady=5)

        self.add_external_srt_button = tk.Button(root, text="Add External SRT", command=self.add_external_srt)
        self.add_external_srt_button.pack()

        # ===============================
        # BOTTOM FRAME: START PROCESSING + GENERATE LOG FILE
        # ===============================
        self.bottom_frame = tk.Frame(root)
        self.bottom_frame.pack(pady=10, padx=10, fill=tk.X)

        # Start Processing Button (Left)
        self.start_button = tk.Button(self.bottom_frame, text="Start Processing", command=self.start_processing)
        self.start_button.pack(side=tk.LEFT, padx=5)

        # Generate Log File Option (Right of Start Processing)
        self.generate_log_var = tk.BooleanVar(value=False)
        self.generate_log_checkbox = tk.Checkbutton(
            self.bottom_frame,
            text="Generate Log File",
            variable=self.generate_log_var
        )
        self.generate_log_checkbox.pack(side=tk.LEFT, padx=(10, 0))

    # ===================================
    # FILE & SUBTITLE TRACKS DETECTION
    # ===================================
    def add_files(self):
        files = filedialog.askopenfilenames(
            filetypes=[("Video Files", "*.mp4;*.mkv;*.avi"), ("All Files", "*.*")]
        )
        self.update_file_list(files)
        for f in files:
            self.detect_subtitle_tracks(f)

    def detect_subtitle_tracks(self, file_path):
        if file_path in self.subtitle_tracks:
            return

        self.subtitle_tracks[file_path] = []
        cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "s",
            "-show_entries", "stream=index:stream_tags=language:stream_tags=title",
            "-of", "default=noprint_wrappers=1",
            file_path
        ]
        print(f"Detecting subtitles with: {' '.join(cmd)}")
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
                track_index = line.split("=")[1]
                track_info = {"track_id": track_index, "lang": "und", "title": ""}
            elif line.startswith("TAG:language="):
                track_info["lang"] = line.split("=")[1]
            elif line.startswith("TAG:title="):
                track_info["title"] = line.split("=")[1]
            elif line.startswith("[STREAM]"):
                if track_info:
                    all_tracks.append(track_info)
                track_info = {}
            elif line.startswith("[/STREAM]"):
                if track_info:
                    all_tracks.append(track_info)
                track_info = {}
        if track_info:
            all_tracks.append(track_info)

        # Show in the subtitle_tracks_frame
        file_label = tk.Label(self.subtitle_tracks_frame, text=os.path.basename(file_path))
        file_label.pack(anchor="w")

        for track in all_tracks:
            cvar = tk.BooleanVar(value=False)
            desc = f"Track #{track['track_id']} - {track['lang']}"
            if track["title"]:
                desc += f" ({track['title']})"
            cb = tk.Checkbutton(self.subtitle_tracks_frame, text=desc, variable=cvar)
            cb.pack(anchor="w", padx=20)
            self.subtitle_tracks[file_path].append({
                "track_id": track["track_id"],
                "lang": track["lang"],
                "title": track["title"],
                "selected": cvar
            })

    def handle_file_drop(self, event):
        files = self.root.tk.splitlist(event.data)
        self.update_file_list(files)
        for f in files:
            self.detect_subtitle_tracks(f)

    def update_file_list(self, files):
        for file in files:
            if file not in self.file_list:
                self.file_list.append(file)
                self.file_listbox.insert(tk.END, file)

    def remove_selected(self):
        selected_indices = list(self.file_listbox.curselection())
        for index in reversed(selected_indices):
            file_to_remove = self.file_list[index]
            if file_to_remove in self.subtitle_tracks:
                del self.subtitle_tracks[file_to_remove]
            del self.file_list[index]
            self.file_listbox.delete(index)

    def clear_all(self):
        self.file_list.clear()
        self.file_listbox.delete(0, tk.END)
        self.subtitle_tracks.clear()
        for widget in self.subtitle_tracks_frame.pack_slaves():
            widget.destroy()

        # Clear external SRT
        self.external_srt.clear()
        for widget in self.external_srt_frame.pack_slaves():
            widget.destroy()

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
    # EXTERNAL SRT LOGIC
    # ===============================
    def add_external_srt(self):
        srt_files = filedialog.askopenfilenames(
            filetypes=[("Subtitle Files", "*.srt"), ("All Files", "*.*")]
        )
        for s in srt_files:
            if not any(e["path"] == s for e in self.external_srt):
                cvar = tk.BooleanVar(value=True)
                cb = tk.Checkbutton(self.external_srt_frame, text=os.path.basename(s), variable=cvar)
                cb.pack(anchor="w")
                self.external_srt.append({"path": s, "selected": cvar})

    # ===============================
    # SUBTITLE BURNING & ALIGNMENT
    # ===============================
    def toggle_burn_subtitles(self):
        if self.burn_subtitles_var.get():
            self.marginv_label.grid()
            self.marginv_entry.grid()
            self.update_marginv()
        else:
            self.marginv_label.grid_remove()
            self.marginv_entry.grid_remove()

    def update_qvbr(self):
        if self.resolution_var.get() == "4k":
            self.qvbr_var.set("18")
        else:
            self.qvbr_var.set("28")
        self.update_marginv()

    def update_marginv(self):
        if self.burn_subtitles_var.get():
            margin_v = 50 if self.resolution_var.get() == "4k" else 100
            self.marginv_var.set(str(margin_v))

    def toggle_fruc_fps(self):
        if self.fruc_var.get():
            self.fruc_fps_entry.configure(state="normal")
        else:
            self.fruc_fps_entry.configure(state="disabled")

    # ===============================
    # EXTRACT & FIX STYLE
    # ===============================
    def fix_ass_style(self, ass_file, margin_v):
        """Update alignment based on self.alignment_var (top=8, middle=5, bottom=2)."""
        alignment_map = {
            "top": 8,
            "middle": 5,
            "bottom": 2,
        }
        alignment_code = alignment_map.get(self.alignment_var.get(), 2)

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
                            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
                            "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
                            "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
                        )
                        style_line = (
                            f"Style: Default,Futura,18,&H00FFFFFF,&H000000FF,&H00000000,&H64000000,"
                            f"-1,0,0,0,100,100,0,0,1,1,1,{alignment_code},10,10,{margin_v},1\n"
                        )
                        f.write(style_line)
                    elif in_styles and line.strip().startswith("Style:"):
                        continue  # Skip existing style lines
                    else:
                        f.write(line)
        except Exception as e:
            print(f"Error fixing style in {ass_file}: {e}")

    def extract_embedded_subtitle_to_ass(self, input_file, output_ass, margin_v, sub_track_id):
        cmd = [
            "ffmpeg",
            "-i", input_file,
            "-map", f"0:s:{sub_track_id}",
            "-c:s", "ass",
            output_ass,
        ]
        print(f"Running command: {' '.join(cmd)}")
        try:
            subprocess.run(cmd, check=True)
            print(f"ASS subtitle extracted to {output_ass}")
            self.fix_ass_style(output_ass, margin_v)
        except subprocess.CalledProcessError as e:
            print(f"Error extracting embedded subtitle track {sub_track_id}: {e}")

    def extract_external_srt_to_ass(self, srt_file, output_ass, margin_v):
        cmd = [
            "ffmpeg",
            "-i", srt_file,
            "-c:s", "ass",
            output_ass,
        ]
        print(f"Converting external SRT => ASS: {' '.join(cmd)}")
        try:
            subprocess.run(cmd, check=True)
            print(f"SRT converted => {output_ass}")
            self.fix_ass_style(output_ass, margin_v)
        except subprocess.CalledProcessError as e:
            print(f"Error converting external SRT {srt_file}: {e}")

    # ===============================
    # EXTRACT SRT (for final .srt output)
    # ===============================
    def extract_subtitle_to_srt(self, input_file, output_srt, sub_track_id=None):
        """
        If sub_track_id is not None, we assume an embedded track.
        Otherwise, for an external SRT, we can just copy it.
        """
        if sub_track_id is not None:
            # Embedded track => extract using ffmpeg
            cmd = [
                "ffmpeg",
                "-i", input_file,
                "-map", f"0:s:{sub_track_id}",
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
            # External SRT => copy the file
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

        resolution = self.resolution_var.get()
        vertical_crop = "y" if self.crop_var.get() else "n"
        qvbr_value = self.qvbr_var.get()
        fruc_enable = "y" if self.fruc_var.get() else "n"
        fruc_fps_target = self.fruc_fps_var.get()
        generate_log = self.generate_log_var.get()

        try:
            qvbr_value = int(qvbr_value)
            fruc_fps_target = int(fruc_fps_target)
        except ValueError:
            messagebox.showerror("Invalid Input", "QVBR and FRUC FPS Target must be integers.")
            return

        self.root.destroy()  # close GUI

        burn_subs = self.burn_subtitles_var.get()
        try:
            margin_v = int(self.marginv_var.get()) if burn_subs else 0
        except ValueError:
            margin_v = 50 if resolution == "4k" else 100

        for file_path in self.file_list:
            if not burn_subs:
                self.encode_single_pass(file_path, resolution, vertical_crop, qvbr_value, fruc_enable, fruc_fps_target, generate_log)
            else:
                embedded_tracks_selected = []
                if file_path in self.subtitle_tracks:
                    for track_info in self.subtitle_tracks[file_path]:
                        if track_info["selected"].get():
                            embedded_tracks_selected.append(track_info["track_id"])

                external_srt_selected = []
                for ext_srt in self.external_srt:
                    if ext_srt["selected"].get():
                        external_srt_selected.append(ext_srt["path"])

                if not embedded_tracks_selected and not external_srt_selected:
                    self.encode_single_pass(file_path, resolution, vertical_crop, qvbr_value, fruc_enable, fruc_fps_target, generate_log)
                    continue

                for sub_id in embedded_tracks_selected:
                    self.encode_with_embedded_sub(
                        file_path, sub_id, margin_v, resolution, vertical_crop, qvbr_value,
                        fruc_enable, fruc_fps_target, generate_log
                    )

                for srt_file in external_srt_selected:
                    self.encode_with_external_srt(
                        file_path, srt_file, margin_v, resolution, vertical_crop, qvbr_value,
                        fruc_enable, fruc_fps_target, generate_log
                    )

        print("Processing Complete.")
        os.system("pause")

    # -----------
    # ENCODERS
    # -----------
    def encode_single_pass(self, file_path, resolution, vertical_crop, qvbr_value, fruc_enable, fruc_fps_target, generate_log):
        """Encode without burning any subtitles."""
        output_dir = os.path.join(os.path.dirname(file_path), resolution)
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, os.path.basename(file_path))

        cmd = self.build_nvenc_command(file_path, output_file, resolution, vertical_crop, qvbr_value, fruc_enable, fruc_fps_target, generate_log)
        print(f"Running command: {' '.join(cmd)}")
        try:
            subprocess.run(cmd, check=True)
            print(f"Done: {file_path}")
            hdr_output = self.apply_hdr_settings(output_file)
            print(f"HDR => {hdr_output}")

        except subprocess.CalledProcessError as e:
            print(f"Error: {file_path}: {e}")

    def encode_with_embedded_sub(self, file_path, sub_track_id, margin_v, resolution, vertical_crop, qvbr_value, fruc_enable, fruc_fps_target, generate_log):
        """Burn a single embedded subtitle track into the output and generate corresponding .srt."""
        base_name, ext = os.path.splitext(os.path.basename(file_path))
        output_dir = os.path.join(os.path.dirname(file_path), resolution)
        os.makedirs(output_dir, exist_ok=True)

        output_file = os.path.join(output_dir, f"{base_name}_track{sub_track_id}{ext}")

        # 1) Produce .ass
        ass_path = os.path.join(output_dir, f"{base_name}_track{sub_track_id}.ass")
        self.extract_embedded_subtitle_to_ass(file_path, ass_path, margin_v, sub_track_id)

        # 2) Produce .srt
        srt_path = os.path.join(output_dir, f"{base_name}_track{sub_track_id}.srt")
        self.extract_subtitle_to_srt(file_path, srt_path, sub_track_id=sub_track_id)

        # 3) Build NVEnc command
        cmd = self.build_nvenc_command(file_path, output_file, resolution, vertical_crop, qvbr_value, fruc_enable, fruc_fps_target, generate_log)
        cmd.extend(["--vpp-subburn", f"filename={ass_path}"])
        print(f"Running with subs: {' '.join(cmd)}")
        try:
            subprocess.run(cmd, check=True)
            print(f"Done: {file_path} track {sub_track_id}")
            hdr_output = self.apply_hdr_settings(output_file)
            print(f"HDR => {hdr_output}")
        except subprocess.CalledProcessError as e:
            print(f"Error: {file_path} track {sub_track_id}: {e}")

    def encode_with_external_srt(self, file_path, srt_file, margin_v, resolution, vertical_crop, qvbr_value, fruc_enable, fruc_fps_target, generate_log):
        """Burn an external SRT into the output and generate corresponding .srt."""
        base_name, ext = os.path.splitext(os.path.basename(file_path))
        output_dir = os.path.join(os.path.dirname(file_path), resolution)
        os.makedirs(output_dir, exist_ok=True)

        srt_base = os.path.splitext(os.path.basename(srt_file))[0]
        output_file = os.path.join(output_dir, f"{base_name}_srt_{srt_base}{ext}")

        # 1) Convert external .srt => .ass
        ass_path = os.path.join(output_dir, f"{base_name}_ext_{srt_base}.ass")
        self.extract_external_srt_to_ass(srt_file, ass_path, margin_v)

        # 2) Also produce a .srt
        srt_path = os.path.join(output_dir, f"{base_name}_ext_{srt_base}.srt")
        self.extract_subtitle_to_srt(srt_file, srt_path, sub_track_id=None)

        # 3) NVEnc
        cmd = self.build_nvenc_command(file_path, output_file, resolution, vertical_crop, qvbr_value, fruc_enable, fruc_fps_target, generate_log)
        cmd.extend(["--vpp-subburn", f"filename={ass_path}"])
        print(f"Running with external SRT: {' '.join(cmd)}")
        try:
            subprocess.run(cmd, check=True)
            print(f"Done: {file_path} with {srt_file}")
            hdr_output = self.apply_hdr_settings(output_file)
            print(f"HDR => {hdr_output}")
        except subprocess.CalledProcessError as e:
            print(f"Error burning external SRT {srt_file} for {file_path}: {e}")

    def build_nvenc_command(self, file_path, output_file, resolution, vertical_crop, qvbr_value, fruc_enable, fruc_fps_target, generate_log):
        """Build the NVEncC64 command with provided parameters."""
        cmd = [
            "NVEncC64",
            "--avhw",
            "--codec", "av1",
            "--qvbr", str(qvbr_value),
            "--preset", "p1",
            "--output-depth", "10",
            "--audio-copy",
            "--sub-copy",
            "--chapter-copy",
            "--key-on-chapter",
            "--transfer", "auto",
            "--colorprim", "auto",
            "--colormatrix", "auto",
            "--lookahead", "32",
            "--aq-temporal",
            "--multipass", "2pass-full",
            "--log-level", "info",
            "--output", output_file,
            "-i", file_path,
        ]
        if resolution == "4k":
            cmd.extend([
                "--vpp-resize", "algo=nvvfx-superres",
                "--output-res", "2160x2160,preserve_aspect_ratio=increase"
            ])
        else:  # 8k
            cmd.extend([
                "--vpp-resize", "algo=ngx-vsr",
                "--output-res", "4320x4320,preserve_aspect_ratio=increase"
            ])

        if fruc_enable == "y":
            cmd.extend(["--vpp-fruc", f"fps={fruc_fps_target}"])

        if vertical_crop == "y":
            crop_value = "528,0,528,0" if resolution == "4k" else "1056,0,1056,0"
            cmd.extend(["--crop", crop_value])

        if generate_log:
            cmd.extend(["--log", "log.log", "--log-level", "debug"])

        return cmd

    def apply_hdr_settings(self, output_file):
        """
        After each encode, run mkvmerge to attach the cube file and set color flags.

        Example command:
          mkvmerge.exe -o output_HDR_CUBE.mkv --colour-matrix 0:9 --colour-range 0:1 ...
                       --attach-file "C:\\path\\to\\your.cube" output_file.mkv
        """
        # (1) Build the mkvmerge command with the new output filename
        base, ext = os.path.splitext(output_file)
        merged_output = base + "_HDR_CUBE" + ext

        # Update the path to your .cube file
        cube_file = r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\LUT\Colorspace LUTS\5-NBCU_PQ2SDR_DL_RESOLVE17-VRT_v1.2.cube"

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
            # Delete the original output file without LUT
            try:
                os.remove(output_file)
                print(f"Deleted original file without LUT: {output_file}")
            except Exception as e_del:
                print(f"Error deleting original file {output_file}: {e_del}")
            return merged_output
        except subprocess.CalledProcessError as e:
            print(f"Error running mkvmerge: {e}")
            # Return original output if mkvmerge fails
            return output_file

if __name__ == "__main__":
    import sys
    initial_files = sys.argv[1:] if len(sys.argv) > 1 else []
    root = TkinterDnD.Tk()
    app = VideoProcessorApp(root, initial_files)
    root.mainloop()
