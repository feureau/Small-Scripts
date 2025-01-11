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

        # Path to the 3D LUT file for 8-bit conversion
        self.lut_file = r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\LUT\Colorspace LUTS\5-NBCU_PQ2SDR_DL_RESOLVE17-VRT_v1.2.cube"

        # List to store both embedded & external subtitles
        self.all_subs = []

        # List to store video files
        self.file_list = []

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

        # -- NEW: Convert to 8 bit --
        tk.Label(self.options_frame, text="Convert to 8 bit:").grid(row=1, column=2, sticky=tk.W)
        self.eight_bit_var = tk.BooleanVar(value=False)  # Default = False
        self.eight_bit_checkbox = tk.Checkbutton(self.options_frame, variable=self.eight_bit_var)
        self.eight_bit_checkbox.grid(row=1, column=3, sticky=tk.W)

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
        self.marginv_label.grid(row=6, column=2, sticky=tk.W, padx=(10, 0))
        self.marginv_entry.grid(row=6, column=3, sticky=tk.W)
        self.marginv_label.grid_remove()
        self.marginv_entry.grid_remove()

        # ===============================
        # 3) SUBTITLE ALIGNMENT (Vertical)
        # ===============================
        tk.Label(self.options_frame, text="Subtitle Alignment:").grid(row=7, column=0, sticky=tk.W)
        # Default alignment => "middle"
        self.alignment_var = tk.StringVar(value="middle")
        self.align_frame = tk.Frame(self.options_frame)
        self.align_frame.grid(row=7, column=1, columnspan=3, sticky=tk.W)

        self.align_top_rb = tk.Radiobutton(self.align_frame, text="Top", variable=self.alignment_var, value="top")
        self.align_top_rb.pack(anchor="w")

        self.align_middle_rb = tk.Radiobutton(self.align_frame, text="Middle", variable=self.alignment_var, value="middle")
        self.align_middle_rb.pack(anchor="w")

        self.align_bottom_rb = tk.Radiobutton(self.align_frame, text="Bottom", variable=self.alignment_var, value="bottom")
        self.align_bottom_rb.pack(anchor="w")

        # ===============================
        # SUBTITLE TRACKS FRAME
        # ===============================
        self.subtitle_tracks_frame = tk.LabelFrame(root, text="Subtitle Tracks", padx=10, pady=10)
        self.subtitle_tracks_frame.pack(fill=tk.X, padx=10, pady=5)

        self.subtitle_tracks_buttons_frame = tk.Frame(self.subtitle_tracks_frame)
        self.subtitle_tracks_buttons_frame.pack(fill=tk.X, padx=5, pady=5)

        # "Load Embedded SRT" button
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

        # This frame will hold the checkboxes for both embedded and external subtitles
        self.subtitle_tracks_list_frame = tk.Frame(self.subtitle_tracks_frame)
        self.subtitle_tracks_list_frame.pack(fill=tk.X)

        # ===============================
        # BOTTOM FRAME: START PROCESSING + GENERATE LOG FILE
        # ===============================
        self.bottom_frame = tk.Frame(root)
        self.bottom_frame.pack(pady=10, padx=10, fill=tk.X)

        # Start Processing Button
        self.start_button = tk.Button(self.bottom_frame, text="Start Processing", command=self.start_processing)
        self.start_button.pack(side=tk.LEFT, padx=5)

        # Generate Log File Option
        self.generate_log_var = tk.BooleanVar(value=False)
        self.generate_log_checkbox = tk.Checkbutton(
            self.bottom_frame,
            text="Generate Log File",
            variable=self.generate_log_var
        )
        self.generate_log_checkbox.pack(side=tk.LEFT, padx=(10, 0))

        # ===============================
        # ADD INITIAL FILES AND DETECT SUBTITLES
        # ===============================
        self.update_file_list(initial_files)
        for f in initial_files:
            self.detect_subtitle_tracks(f)

    # ===================================
    # FILE & SUBTITLE TRACKS DETECTION
    # ===================================
    def add_files(self):
        """Add video files and automatically load any embedded subs."""
        files = filedialog.askopenfilenames(
            filetypes=[("Video Files", "*.mp4;*.mkv;*.avi"), ("All Files", "*.*")]
        )
        self.update_file_list(files)
        # Automatically detect & load embedded subs
        for f in files:
            self.detect_subtitle_tracks(f)

    def handle_file_drop(self, event):
        """Handle drag-and-drop for video files."""
        files = self.root.tk.splitlist(event.data)
        self.update_file_list(files)
        # Automatically detect & load embedded subs
        for f in files:
            self.detect_subtitle_tracks(f)

    def update_file_list(self, files):
        for file in files:
            if file not in self.file_list:
                self.file_list.append(file)
                self.file_listbox.insert(tk.END, file)

    def detect_subtitle_tracks(self, file_path):
        """
        Auto-detect embedded subtitles in the specified video file using ffprobe,
        then add them as 'embedded' subtitle entries in self.all_subs.
        """
        # ffprobe to detect subtitle streams
        cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "s",  # 's' means subtitle streams
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
                if track_info:  # if we had an un-pushed track_info, store it
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

        for idx, track in enumerate(all_tracks):
            desc = f"Embedded: #{track['track_id']} - {track['lang']}"
            if track["title"]:
                desc += f" ({track['title']})"
            cvar = tk.BooleanVar(value=True)
            cb = tk.Checkbutton(self.subtitle_tracks_list_frame, text=desc, variable=cvar)
            cb.pack(anchor="w", padx=20)

            self.all_subs.append({
                "type": "embedded",
                "file_path": file_path,
                "track_id": track["track_id"],
                "path": None,
                "description": desc,
                "selected": cvar,
                "widget": cb
            })

        # Automatically check "Burn Subtitles" if embedded subs found
        if all_tracks:
            self.burn_subtitles_var.set(True)

    # ===============================
    # MANAGING SUBTITLE LIST & FILE LIST
    # ===============================
    def remove_selected(self):
        """
        Removes the selected video files from file_list. Also removes
        any associated embedded subtitles (with type='embedded') and external subtitles.
        """
        selected_indices = list(self.file_listbox.curselection())
        for index in reversed(selected_indices):
            file_to_remove = self.file_list[index]
            # Remove associated subtitles
            to_remove = [s for s in self.all_subs
                         if (s["type"] == "embedded" and s.get("file_path") == file_to_remove) or
                            (s["type"] == "external" and s.get("path") == file_to_remove)]
            for sub in to_remove:
                sub["widget"].destroy()
                self.all_subs.remove(sub)

            del self.file_list[index]
            self.file_listbox.delete(index)

        # If no subtitles remain, uncheck "Burn Subtitles"
        if not self.all_subs:
            self.burn_subtitles_var.set(False)

    def clear_all(self):
        """Clears everything: video files, external subtitles, embedded subtitles."""
        self.file_list.clear()
        self.file_listbox.delete(0, tk.END)

        for sub in self.all_subs:
            sub["widget"].destroy()
        self.all_subs.clear()

        self.burn_subtitles_var.set(False)

    def remove_selected_srt(self):
        """
        Removes the selected external SRT from self.all_subs.
        If it's an embedded track, just deselect it (cannot truly remove).
        """
        to_remove = []
        for sub in self.all_subs:
            if sub["selected"].get():
                if sub["type"] == "external":
                    sub["widget"].destroy()
                    to_remove.append(sub)
                else:
                    # Embedded => just deselect
                    sub["selected"].set(False)

        for r in to_remove:
            self.all_subs.remove(r)

        if not self.all_subs:
            self.burn_subtitles_var.set(False)

    # ===============================
    # LOAD EMBEDDED SRT LOGIC
    # ===============================
    def load_embedded_srt(self):
        """Manually trigger detection of embedded subtitles for all loaded files."""
        for file_path in self.file_list:
            self.detect_subtitle_tracks(file_path)

    # ===============================
    # EXTERNAL SRT LOGIC
    # ===============================
    def add_external_srt(self):
        """Load external SRT files into the same list (type='external')."""
        srt_files = filedialog.askopenfilenames(
            filetypes=[("Subtitle Files", "*.srt"), ("All Files", "*.*")]
        )
        for s in srt_files:
            if not any(x["type"] == "external" and x["path"] == s for x in self.all_subs):
                desc = f"External: {os.path.basename(s)}"
                cvar = tk.BooleanVar(value=True)
                cb = tk.Checkbutton(self.subtitle_tracks_list_frame, text=desc, variable=cvar)
                cb.pack(anchor="w", padx=20)

                self.all_subs.append({
                    "type": "external",
                    "file_path": None,
                    "track_id": None,
                    "path": s,
                    "description": desc,
                    "selected": cvar,
                    "widget": cb
                })

        # Automatically check "Burn Subtitles" if any external subs added
        if srt_files:
            self.burn_subtitles_var.set(True)

    # ===============================
    # MOVE UP / MOVE DOWN
    # ===============================
    def move_up(self):
        """Moves the selected file(s) in the file list up."""
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
        """Moves the selected file(s) in the file list down."""
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
    # BURN SUBTITLES CHECKBOX & MARGIN
    # ===============================
    def toggle_burn_subtitles(self):
        """Show/hide MarginV fields when 'Burn Subtitles' is toggled."""
        if self.burn_subtitles_var.get():
            self.marginv_label.grid()
            self.marginv_entry.grid()
            self.update_marginv()
        else:
            self.marginv_label.grid_remove()
            self.marginv_entry.grid_remove()

    def update_qvbr(self):
        """Adjust the QVBR value based on resolution."""
        if self.resolution_var.get() == "4k":
            self.qvbr_var.set("18")
        else:
            self.qvbr_var.set("28")
        self.update_marginv()

    def update_marginv(self):
        """Set default MarginV if burn_subtitles is on."""
        if self.burn_subtitles_var.get():
            margin_v = 50 # if self.resolution_var.get() == "4k" else 100
            self.marginv_var.set(str(margin_v))

    def toggle_fruc_fps(self):
        """Enable/disable FRUC FPS Target entry."""
        if self.fruc_var.get():
            self.fruc_fps_entry.configure(state="normal")
        else:
            self.fruc_fps_entry.configure(state="disabled")

    # ===============================
    # EXTRACT & FIX STYLE
    # ===============================
    def fix_ass_style(self, ass_file, margin_v, resolution):
        """
        Update alignment based on self.alignment_var:
          top=8, middle=5, bottom=2
        Sets MarginL and MarginR.
        Sets MarginV based on alignment:
          - Top: e.g., 50
          - Middle: 0
          - Bottom: 50
        Reverts font back to "Futura".
        """
        alignment_map = {
            "top": 8,
            "middle": 5,
            "bottom": 2,
        }
        alignment_code = alignment_map.get(self.alignment_var.get(), 2)

        # Determine screen width
        if resolution == "4k":
            screen_width = 2160
        else:  # 8k
            screen_width = 4320

        # Set MarginL and MarginR to ~1.875% of screen width
        margin_l = margin_r = int(screen_width * 0.01875)

        # For middle alignment, margin_v = 0
        if alignment_code == 5:
            margin_v = 0
        else:
            margin_v = 50 # if resolution == "4k" else 100

        print(f"Alignment Code: {alignment_code}")
        print(f"Margins - Left: {margin_l}, Right: {margin_r}, Vertical: {margin_v}")

        try:
            with open(ass_file, "r", encoding="utf-8") as f:
                lines = f.readlines()

            with open(ass_file, "w", encoding="utf-8") as f:
                in_styles = False
                for line in lines:
                    if line.strip().startswith("[V4+ Styles]"):
                        in_styles = True
                        f.write(line)
                        # Overwrite the Style format line
                        f.write(
                            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
                            "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
                            "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
                        )
                        style_line = (
                            f"Style: Default,Futura,16,&H00FFFFFF,&H000000FF,&H00000000,&H64000000,"
                            f"-1,0,0,0,100,100,0,0,1,1,1,{alignment_code},{margin_l},{margin_r},{margin_v},1\n"
                        )
                        f.write(style_line)
                    elif in_styles and line.strip().startswith("Style:"):
                        # Skip old style lines
                        continue
                    else:
                        f.write(line)
        except Exception as e:
            print(f"Error fixing style in {ass_file}: {e}")

    def extract_embedded_subtitle_to_ass(self, input_file, output_ass, margin_v, sub_track_id):
        """Extract embedded subtitle track to ASS format."""
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
            self.fix_ass_style(output_ass, margin_v, self.resolution_var.get())
            print(f"Embedded track {sub_track_id} extracted as ASS => {output_ass}")
        except subprocess.CalledProcessError as e:
            print(f"Error extracting embedded subtitle track {sub_track_id}: {e}")

    def extract_external_srt_to_ass(self, srt_file, output_ass, margin_v):
        """Convert external SRT file to ASS format."""
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
            print(f"SRT converted => {output_ass}")
            self.fix_ass_style(output_ass, margin_v, self.resolution_var.get())
        except subprocess.CalledProcessError as e:
            print(f"Error converting external SRT {srt_file}: {e}")

    # ===============================
    # EXTRACT SRT (for final .srt output)
    # ===============================
    def extract_subtitle_to_srt(self, input_file, output_srt, sub_track_id=None):
        """
        If sub_track_id is not None, extract embedded track to SRT.
        Otherwise, copy external SRT.
        """
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
            # External SRT => just copy
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
        burn_subs = self.burn_subtitles_var.get()
        eight_bit = self.eight_bit_var.get()  # <-- New 8-bit setting

        try:
            qvbr_value = int(qvbr_value)
            fruc_fps_target = int(fruc_fps_target)
        except ValueError:
            messagebox.showerror("Invalid Input", "QVBR and FRUC FPS Target must be integers.")
            return

        # Close the GUI
        self.root.destroy()

        # Figure out margin_v
        try:
            margin_v = int(self.marginv_var.get()) if burn_subs else 0
        except ValueError:
            margin_v = 50 if resolution == "4k" else 100

        for file_path in self.file_list:
            if not burn_subs:
                # No subtitle burning => single pass encode
                self.encode_single_pass(
                    file_path, resolution, vertical_crop, qvbr_value,
                    fruc_enable, fruc_fps_target, generate_log, eight_bit
                )
            else:
                # Gather external & embedded subs
                external_selected = [
                    s for s in self.all_subs
                    if s["type"] == "external" and s["selected"].get()
                ]
                embedded_selected = [
                    s for s in self.all_subs
                    if s["type"] == "embedded" and s["file_path"] == file_path and s["selected"].get()
                ]

                # If no subtitles selected for this file, do normal encode
                if not external_selected and not embedded_selected:
                    self.encode_single_pass(
                        file_path, resolution, vertical_crop, qvbr_value,
                        fruc_enable, fruc_fps_target, generate_log, eight_bit
                    )
                    continue

                # Encode with each external SRT
                for ext_sub in external_selected:
                    self.encode_with_external_srt(
                        file_path, ext_sub["path"], margin_v, resolution,
                        vertical_crop, qvbr_value, fruc_enable, fruc_fps_target,
                        generate_log, eight_bit
                    )

                # Encode with each embedded SRT track
                for emb_sub in embedded_selected:
                    self.encode_with_embedded_sub(
                        file_path, emb_sub["track_id"], margin_v, resolution,
                        vertical_crop, qvbr_value, fruc_enable, fruc_fps_target,
                        generate_log, eight_bit
                    )

        print("Processing Complete.")
        os.system("pause")

    # -----------
    # ENCODERS
    # -----------
    def encode_single_pass(
        self, file_path, resolution, vertical_crop, qvbr_value,
        fruc_enable, fruc_fps_target, generate_log, eight_bit
    ):
        """Encode the video without burning any subtitles."""
        output_dir = os.path.join(os.path.dirname(file_path), resolution)
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, os.path.basename(file_path))

        cmd = self.build_nvenc_command(
            file_path, output_file, resolution, vertical_crop,
            qvbr_value, fruc_enable, fruc_fps_target, generate_log, eight_bit
        )
        print("Running command:", " ".join(cmd))
        try:
            subprocess.run(cmd, check=True)
            print(f"Done: {file_path}")
            hdr_output = self.apply_hdr_settings(output_file, eight_bit)
            print(f"HDR => {hdr_output}")
        except subprocess.CalledProcessError as e:
            print(f"Error: {file_path}: {e}")

    def encode_with_embedded_sub(
        self, file_path, sub_track_id, margin_v, resolution,
        vertical_crop, qvbr_value, fruc_enable, fruc_fps_target,
        generate_log, eight_bit
    ):
        """Burn a single embedded subtitle track."""
        base_name, ext = os.path.splitext(os.path.basename(file_path))
        output_dir = os.path.join(os.path.dirname(file_path), resolution)
        os.makedirs(output_dir, exist_ok=True)

        output_file = os.path.join(output_dir, f"{base_name}_track{sub_track_id}{ext}")
        # 1) Extract embedded track => .ass
        ass_path = os.path.join(output_dir, f"{base_name}_track{sub_track_id}.ass")
        self.extract_embedded_subtitle_to_ass(file_path, ass_path, margin_v, sub_track_id)

        # 2) Extract => .srt
        srt_path = os.path.join(output_dir, f"{base_name}_track{sub_track_id}.srt")
        self.extract_subtitle_to_srt(file_path, srt_path, sub_track_id=sub_track_id)

        # 3) NVEnc
        cmd = self.build_nvenc_command(
            file_path, output_file, resolution, vertical_crop,
            qvbr_value, fruc_enable, fruc_fps_target, generate_log, eight_bit
        )
        cmd.extend(["--vpp-subburn", f"filename={ass_path}"])
        print("Running with embedded subtitles:", " ".join(cmd))
        try:
            subprocess.run(cmd, check=True)
            print(f"Done: {file_path} track {sub_track_id}")
            hdr_output = self.apply_hdr_settings(output_file, eight_bit)
            print(f"HDR => {hdr_output}")
        except subprocess.CalledProcessError as e:
            print(f"Error: {file_path} track {sub_track_id}: {e}")

    def encode_with_external_srt(
        self, file_path, srt_file, margin_v, resolution,
        vertical_crop, qvbr_value, fruc_enable, fruc_fps_target,
        generate_log, eight_bit
    ):
        """Burn an external SRT into the output."""
        base_name, ext = os.path.splitext(os.path.basename(file_path))
        output_dir = os.path.join(os.path.dirname(file_path), resolution)
        os.makedirs(output_dir, exist_ok=True)

        srt_base = os.path.splitext(os.path.basename(srt_file))[0]
        output_file = os.path.join(output_dir, f"{base_name}_srt_{srt_base}{ext}")

        # 1) Convert external SRT => .ass
        ass_path = os.path.join(output_dir, f"{base_name}_ext_{srt_base}.ass")
        self.extract_external_srt_to_ass(srt_file, ass_path, margin_v)

        # 2) Also produce a .srt copy
        srt_path = os.path.join(output_dir, f"{base_name}_ext_{srt_base}.srt")
        self.extract_subtitle_to_srt(srt_file, srt_path, sub_track_id=None)

        # 3) NVEnc
        cmd = self.build_nvenc_command(
            file_path, output_file, resolution, vertical_crop,
            qvbr_value, fruc_enable, fruc_fps_target, generate_log, eight_bit
        )
        cmd.extend(["--vpp-subburn", f"filename={ass_path}"])
        print("Running with external SRT:", " ".join(cmd))
        try:
            subprocess.run(cmd, check=True)
            print(f"Done: {file_path} with {srt_file}")
            hdr_output = self.apply_hdr_settings(output_file, eight_bit)
            print(f"HDR => {hdr_output}")
        except subprocess.CalledProcessError as e:
            print(f"Error burning external SRT {srt_file} for {file_path}: {e}")

    # ===============================
    # NVEnc COMMAND
    # ===============================
    def build_nvenc_command(
        self, file_path, output_file, resolution, vertical_crop,
        qvbr_value, fruc_enable, fruc_fps_target, generate_log,
        eight_bit
    ):
        """
        Builds the NVEncC64 command line with the given parameters.
        """
        cmd = [
            "NVEncC64",
            "--avhw",
            "--codec", "av1",
            "--qvbr", str(qvbr_value),
            "--preset", "p1",
            # Switch output depth depending on the checkbox
            "--output-depth", "8" if eight_bit else "10",
            "--audio-copy",
            "--sub-copy",
            "--chapter-copy",
            "--key-on-chapter",
            # Force color metadata based on bit depth
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

        # Apply LUT for 8-bit conversion
        if eight_bit:
            if os.path.exists(self.lut_file):
                cmd.extend([
                    "--vpp-colorspace", f"lut3d={self.lut_file},lut3d_interp=trilinear"
                ])
                print(f"Applying LUT: {self.lut_file}")
            else:
                print(f"LUT file not found: {self.lut_file}. Skipping LUT application.")

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
            # Crop logic
            if resolution == "4k":
                crop_value = "528,0,528,0"
            else:
                crop_value = "1056,0,1056,0"
            cmd.extend(["--crop", crop_value])

        if generate_log:
            cmd.extend(["--log", "log.log", "--log-level", "debug"])

        return cmd

    # ===============================
    # HDR SETTINGS
    # ===============================
    def apply_hdr_settings(self, output_file, eight_bit):
        """
        After each encode, run mkvmerge to attach the LUT file and set color flags.
        If eight_bit is True, skip HDR tagging to ensure Rec.709 SDR.
        If eight_bit is False, apply HDR metadata.
        """
        if eight_bit:
            # For 8-bit SDR, skip HDR tagging
            print("8-bit selected: Skipping mkvmerge HDR tagging.")
            return output_file

        base, ext = os.path.splitext(output_file)
        merged_output = base + "_HDR_CUBE" + ext

        # Path to the .cube LUT file
        cube_file = r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\LUT\Colorspace LUTS\5-NBCU_PQ2SDR_DL_RESOLVE17-VRT_v1.2.cube"

        # Check if the cube file exists
        if not os.path.exists(cube_file):
            print(f"LUT file not found: {cube_file}. Skipping HDR attachment.")
            return output_file

        cmd = [
            "mkvmerge.exe",
            "-o", merged_output,
            "--colour-matrix", "0:9",  # BT.2020
            "--colour-range", "0:1",  # Limited
            "--colour-transfer-characteristics", "0:16",  # PQ
            "--colour-primaries", "0:9",  # BT.2020
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
            # Remove original
            try:
                os.remove(output_file)
                print(f"Deleted original file without LUT: {output_file}")
            except Exception as e_del:
                print(f"Error deleting original file {output_file}: {e_del}")
            return merged_output
        except subprocess.CalledProcessError as e:
            print(f"Error running mkvmerge: {e}")
            return output_file

# ------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    initial_files = sys.argv[1:] if len(sys.argv) > 1 else []
    root = TkinterDnD.Tk()
    app = VideoProcessorApp(root, initial_files)
    root.mainloop()
