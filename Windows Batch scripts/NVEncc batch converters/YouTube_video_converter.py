import os
import sys
import shutil
import subprocess
import logging
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk  # for Combobox
from tkinterdnd2 import TkinterDnD, DND_FILES

import concurrent.futures
import multiprocessing

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


class SubtitleTrack:
    def __init__(
        self,
        track_id: str,
        track_type: str,
        file_path: str,
        external_path: str,
        description: str,
        widget,
        check_var
    ):
        self.track_id = track_id
        self.track_type = track_type  # 'embedded' or 'external'
        self.file_path = file_path
        self.external_path = external_path
        self.description = description
        self.widget = widget
        self.check_var = check_var

    def is_selected(self) -> bool:
        return self.check_var.get()

    def destroy_widget(self):
        self.widget.destroy()


class VideoProcessor:
    def __init__(self, lut_file: str):
        self.lut_file = lut_file

    def get_input_width(self, file_path: str) -> int:
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
            logger.error(f"Error getting width from ffprobe: {e}")
            return 0

    def compute_crop_value(self, file_path: str, resolution: str, crop_enabled: bool) -> str:
        if not crop_enabled:
            return "0,0,0,0"

        input_width = self.get_input_width(file_path)
        if resolution == "4k":
            if input_width >= 3840:
                return "528,0,528,0"
        elif resolution == "8k":
            if input_width >= 7680:
                return "1056,0,1056,0"
        return "0,0,0,0"

    def detect_embedded_subtitle_tracks(self, file_path: str):
        cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "s",
            "-show_entries", "stream=index:stream_tags=language:stream_tags=title",
            "-of", "default=noprint_wrappers=1",
            file_path
        ]
        logger.info(f"Detecting subtitles with: {' '.join(cmd)}")

        try:
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, universal_newlines=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"Error detecting subtitle tracks for {file_path}: {e}")
            return []

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

        return all_tracks

    def fix_ass_style(self, ass_file: str, alignment: str, resolution: str):
        alignment_map = {"top": 8, "middle": 5, "bottom": 2}
        alignment_code = alignment_map.get(alignment, 2)

        if resolution == "4k":
            screen_height = 2160
        elif resolution == "8k":
            screen_height = 4320
        else:
            screen_height = 1080

        margin_l = margin_r = int(screen_height * 0.01875)
        margin_v = 50 if alignment_code != 5 else 0

        logger.info(
            f"Fixing ASS style: alignment={alignment_code}, margin_l={margin_l}, "
            f"margin_r={margin_r}, margin_v={margin_v}"
        )

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
                            f"Style: Default,Futura,16,&H00FFFFFF,&H000000FF,&H00000000,"
                            f"&H64000000,-1,0,0,0,100,100,0,0,1,1,1,{alignment_code},"
                            f"{margin_l},{margin_r},{margin_v},1\n"
                        )
                        f.write(style_line)
                    elif in_styles and line.strip().startswith("Style:"):
                        continue
                    else:
                        f.write(line)
        except Exception as e:
            logger.error(f"Error fixing style in {ass_file}: {e}")

    def extract_embedded_subtitle_to_ass(self, input_file: str, output_ass: str, sub_track_id: str):
        cmd = [
            "ffmpeg",
            "-sub_charenc", "UTF-8",
            "-i", input_file,
            "-map", f"0:{sub_track_id}",
            "-c:s", "ass",
            output_ass
        ]
        logger.info(f"Extracting embedded subtitle track {sub_track_id} => {output_ass}")

        try:
            subprocess.run(cmd, check=True)
            logger.info(f"Embedded track {sub_track_id} extracted as ASS => {output_ass}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Error extracting embedded subtitle track {sub_track_id}: {e}")

    def extract_external_srt_to_ass(self, srt_file: str, output_ass: str):
        cmd = [
            "ffmpeg",
            "-sub_charenc", "UTF-8",
            "-i", srt_file,
            "-c:s", "ass",
            output_ass,
        ]
        logger.info(f"Converting external SRT => ASS: {' '.join(cmd)}")

        try:
            subprocess.run(cmd, check=True)
            logger.info(f"SRT converted => {output_ass}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Error converting external SRT {srt_file}: {e}")

    def extract_subtitle_to_srt(self, input_file: str, output_srt: str, sub_track_id: str = None):
        if sub_track_id is not None:
            cmd = [
                "ffmpeg",
                "-sub_charenc", "UTF-8",
                "-i", input_file,
                "-map", f"0:{sub_track_id}",
                "-c:s", "srt",
                output_srt,
            ]
            logger.info(f"Extracting embedded track => SRT: {' '.join(cmd)}")
            try:
                subprocess.run(cmd, check=True)
                logger.info(f"Extracted to {output_srt}")
            except subprocess.CalledProcessError as e:
                logger.error(f"Error extracting SRT from track {sub_track_id}: {e}")
        else:
            logger.info(f"Copying external SRT => {output_srt}")
            try:
                shutil.copyfile(input_file, output_srt)
            except Exception as e:
                logger.error(f"Error copying external SRT {input_file}: {e}")

    def build_nvenc_command(
        self,
        file_path: str,
        output_file: str,
        qvbr_value: int,
        resolution: str,
        fruc_enable: bool,
        fruc_fps_target: int,
        generate_log: bool,
        eight_bit: bool,
        crop_str: str
    ):
        input_width = self.get_input_width(file_path)
        do_resize = False
        resize_algo = "nvvfx-superres"
        target_res = "2160x2160"  # 4k

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
            "--audio-copy",
            "--sub-copy",
            "--chapter-copy",
            "--key-on-chapter",
            "--lookahead", "32",
            "--aq-temporal",
            "--multipass", "2pass-full",
            "--log-level", "info",
            "--output", output_file,
            "-i", file_path,
        ]

        depth_str = "8" if eight_bit else "10"
        color_str = "bt709" if eight_bit else "auto"
        cmd.extend(["--output-depth", depth_str])
        cmd.extend(["--transfer", color_str, "--colorprim", color_str, "--colormatrix", color_str])

        if eight_bit and self.lut_file and os.path.exists(self.lut_file):
            logger.info(f"Applying LUT: {self.lut_file}")
            cmd.extend([
                "--vpp-colorspace", f"lut3d={self.lut_file},lut3d_interp=trilinear"
            ])

        if do_resize:
            cmd.extend([
                "--vpp-resize", f"algo={resize_algo}",
                "--output-res", f"{target_res},preserve_aspect_ratio=increase"
            ])

        if crop_str != "0,0,0,0":
            cmd.extend(["--crop", crop_str])

        if fruc_enable:
            cmd.extend(["--vpp-fruc", f"fps={fruc_fps_target}"])

        if generate_log:
            cmd.extend(["--log", "log.log", "--log-level", "debug"])

        return cmd

    def apply_hdr_settings(self, output_file: str, eight_bit: bool) -> str:
        if eight_bit:
            logger.info("8-bit selected: Skipping mkvmerge HDR tagging.")
            return output_file

        base, ext = os.path.splitext(output_file)
        merged_output = f"{base}_HDR_CUBE{ext}"

        cube_file = self.lut_file
        if not cube_file or not os.path.exists(cube_file):
            logger.warning(f"LUT file not found: {cube_file}. Skipping HDR attachment.")
            return output_file

        cmd = [
            "mkvmerge.exe",
            "-o", merged_output,
            "--colour-matrix", "0:9",  # BT.2020
            "--colour-range", "0:1",   # Limited
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
        logger.info(f"Attaching LUT and setting HDR flags with mkvmerge:\n{' '.join(cmd)}")

        try:
            subprocess.run(cmd, check=True)
            logger.info(f"mkvmerge complete => {merged_output}")
            try:
                os.remove(output_file)
                logger.info(f"Deleted original file: {output_file}")
            except Exception as e_del:
                logger.error(f"Error deleting {output_file}: {e_del}")

            return merged_output
        except subprocess.CalledProcessError as e:
            logger.error(f"Error running mkvmerge: {e}")
            return output_file

    # Single pass / embedded / external encoding methods omitted for brevity...


class VideoProcessorApp:
    def __init__(self, root, initial_files):
        self.root = root
        self.root.title("Video Processing Tool")

        # Let Tkinter compute minimal geometry
        self.root.geometry("")

        self.processor = VideoProcessor(
            lut_file=r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\LUT\Colorspace LUTS\5-NBCU_PQ2SDR_DL_RESOLVE17-VRT_v1.2.cube"
        )

        self.file_list = []
        self.all_subs = []
        self.subtitle_id_counter = 0

        self.burn_subtitles_var = tk.BooleanVar(value=False)
        self.resolution_var = tk.StringVar(value="4k")
        self.eight_bit_var = tk.BooleanVar(value=False)
        self.crop_var = tk.BooleanVar(value=False)
        self.qvbr_var = tk.StringVar(value="18")
        self.fruc_var = tk.BooleanVar(value=False)
        self.fruc_fps_var = tk.StringVar(value="60")
        self.generate_log_var = tk.BooleanVar(value=False)
        self.alignment_var = tk.StringVar(value="middle")

        self.parallel_count_var = tk.StringVar(value="1")
        self.max_parallel = multiprocessing.cpu_count()

        self.fruc_fps_entry = None

        self._build_main_container()
        self._build_file_list_frame()
        self._build_options_frame()
        self._build_subtitle_tracks_frame()
        self._build_parallel_frame()
        self._build_bottom_frame()

        # Enable drag-and-drop
        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind("<<Drop>>", self._handle_file_drop)

        # Insert initial files
        self._update_file_list(initial_files)
        for f in initial_files:
            self._detect_subtitle_tracks_for_file(f)

        # -- NEW: Final step: measure actual needed size of inner_frame --
        # so the window can be tall enough for all content, up to 70% screen.
        self._finalize_geometry()

    def _finalize_geometry(self):
        """
        Force layout, measure the inner_frame, then clamp height to 70% of screen
        so the entire GUI is visible (if it fits).
        """
        # Let idle tasks run so geometry is computed
        self.inner_frame.update_idletasks()

        req_width = self.inner_frame.winfo_reqwidth()
        req_height = self.inner_frame.winfo_reqheight()

        screen_height = self.root.winfo_screenheight()
        max_height = int(screen_height * 0.7)

        final_height = min(req_height, max_height)

        # Optionally clamp width to screen as well if desired
        # screen_width = self.root.winfo_screenwidth()
        # final_width = min(req_width, screen_width)
        # For now, we trust the needed width
        final_width = req_width

        self.root.geometry(f"{final_width}x{final_height}")

    def _build_main_container(self):
        """
        Builds the scrollable Canvas + inner_frame.
        """
        main_container = tk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(main_container, highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(main_container, orient="vertical", command=self.canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.inner_frame = tk.Frame(self.canvas)
        self.inner_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas.create_window((0, 0), window=self.inner_frame, anchor="nw")

        # Mouse wheel scrolling
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)

    def _on_mousewheel(self, event):
        if event.num == 4 or event.delta > 0:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5 or event.delta < 0:
            self.canvas.yview_scroll(1, "units")

    def _build_file_list_frame(self):
        self.file_frame = tk.Frame(self.inner_frame)
        self.file_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.file_listbox = tk.Listbox(self.file_frame, selectmode=tk.EXTENDED, height=10)
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        file_scrollbar = tk.Scrollbar(self.file_frame, orient=tk.VERTICAL, command=self.file_listbox.yview)
        file_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_listbox.config(yscrollcommand=file_scrollbar.set)

        file_buttons_frame = tk.Frame(self.inner_frame)
        file_buttons_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Button(file_buttons_frame, text="Add Files", command=self._add_files).pack(side=tk.LEFT, padx=5)
        tk.Button(file_buttons_frame, text="Remove Selected", command=self._remove_selected).pack(side=tk.LEFT, padx=5)
        tk.Button(file_buttons_frame, text="Clear All", command=self._clear_all).pack(side=tk.LEFT, padx=5)
        tk.Button(file_buttons_frame, text="Move Up", command=self._move_up).pack(side=tk.LEFT, padx=5)
        tk.Button(file_buttons_frame, text="Move Down", command=self._move_down).pack(side=tk.LEFT, padx=5)

    def _build_options_frame(self):
        frame = tk.Frame(self.inner_frame)
        frame.pack(fill=tk.X, padx=10, pady=10)

        tk.Label(frame, text="Resolution:").grid(row=0, column=0, sticky=tk.W)
        tk.Radiobutton(frame, text="Original", variable=self.resolution_var, value="original").grid(row=0, column=1, sticky=tk.W)
        tk.Radiobutton(frame, text="4k", variable=self.resolution_var, value="4k").grid(row=0, column=2, sticky=tk.W)
        tk.Radiobutton(frame, text="8k", variable=self.resolution_var, value="8k").grid(row=0, column=3, sticky=tk.W)

        tk.Label(frame, text="Convert to 8 bit:").grid(row=1, column=0, sticky=tk.W)
        tk.Checkbutton(frame, variable=self.eight_bit_var).grid(row=1, column=1, sticky=tk.W)

        tk.Label(frame, text="Vertical Crop:").grid(row=2, column=0, sticky=tk.W)
        tk.Checkbutton(frame, variable=self.crop_var).grid(row=2, column=1, sticky=tk.W)

        tk.Label(frame, text="QVBR Value:").grid(row=3, column=0, sticky=tk.W)
        tk.Entry(frame, textvariable=self.qvbr_var, width=10).grid(row=3, column=1, sticky=tk.W)

        tk.Label(frame, text="Enable FRUC:").grid(row=4, column=0, sticky=tk.W)
        tk.Checkbutton(frame, variable=self.fruc_var, command=self._toggle_fruc_fps).grid(row=4, column=1, sticky=tk.W)

        tk.Label(frame, text="FRUC FPS Target:").grid(row=5, column=0, sticky=tk.W)
        self.fruc_fps_entry = tk.Entry(frame, textvariable=self.fruc_fps_var, width=10)
        self.fruc_fps_entry.grid(row=5, column=1, sticky=tk.W)
        self.fruc_fps_entry.configure(state="disabled")

        tk.Label(frame, text="Subtitle Alignment:").grid(row=6, column=0, sticky=tk.W)
        align_frame = tk.Frame(frame)
        align_frame.grid(row=6, column=1, columnspan=3, sticky=tk.W)
        tk.Radiobutton(align_frame, text="Top", variable=self.alignment_var, value="top").pack(anchor="w")
        tk.Radiobutton(align_frame, text="Middle", variable=self.alignment_var, value="middle").pack(anchor="w")
        tk.Radiobutton(align_frame, text="Bottom", variable=self.alignment_var, value="bottom").pack(anchor="w")

    def _build_subtitle_tracks_frame(self):
        frame = tk.LabelFrame(self.inner_frame, text="Burn Subtitle Tracks", padx=10, pady=10)
        frame.pack(fill=tk.X, padx=10, pady=5)

        buttons_frame = tk.Frame(frame)
        buttons_frame.pack(fill=tk.X, padx=5, pady=5)
        tk.Button(buttons_frame, text="Load Embedded SRT", command=self._load_embedded_srt).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(buttons_frame, text="Add External SRT", command=self._add_external_srt).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(buttons_frame, text="Remove Selected SRT", command=self._remove_selected_srt).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(buttons_frame, text="Select All", command=self._select_all_subtitles).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(buttons_frame, text="Deselect All", command=self._deselect_all_subtitles).pack(side=tk.LEFT, padx=(0, 5))

        self.subtitle_tracks_list_frame = tk.Frame(frame)
        self.subtitle_tracks_list_frame.pack(fill=tk.X)

    def _build_parallel_frame(self):
        frame = tk.LabelFrame(self.inner_frame, text="Parallel Processing", padx=10, pady=10)
        frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(frame, text="Number of Workers:").pack(side=tk.LEFT, padx=(0, 10))

        values = [str(i) for i in range(1, self.max_parallel + 1)]
        self.worker_combobox = ttk.Combobox(
            frame, textvariable=self.parallel_count_var,
            values=values, width=5
        )
        self.worker_combobox.pack(side=tk.LEFT)
        self.worker_combobox.current(0)  # default "1"

    def _build_bottom_frame(self):
        bottom_frame = tk.Frame(self.inner_frame)
        bottom_frame.pack(pady=10, padx=10, fill=tk.X)

        tk.Button(bottom_frame, text="Start Processing", command=self._start_processing).pack(side=tk.LEFT, padx=5)
        tk.Checkbutton(bottom_frame, text="Generate Log File", variable=self.generate_log_var).pack(side=tk.LEFT, padx=(10, 0))

    # -------------------------------------------------------------------------
    # DRAG-AND-DROP
    # -------------------------------------------------------------------------
    def _handle_file_drop(self, event):
        files = self.root.tk.splitlist(event.data)
        self._update_file_list(files)
        for f in files:
            self._detect_subtitle_tracks_for_file(f)

    def _update_file_list(self, files):
        for file in files:
            if file not in self.file_list:
                self.file_list.append(file)
                self.file_listbox.insert(tk.END, file)

    def _add_files(self):
        files = filedialog.askopenfilenames(
            filetypes=[("Video Files", "*.mp4;*.mkv;*.avi"), ("All Files", "*.*")]
        )
        self._update_file_list(files)
        for f in files:
            self._detect_subtitle_tracks_for_file(f)

    # -------------------------------------------------------------------------
    # FILE LIST & SUBTITLES
    # -------------------------------------------------------------------------
    def _remove_selected(self):
        selected_indices = list(self.file_listbox.curselection())
        for index in reversed(selected_indices):
            file_to_remove = self.file_list[index]
            subs_to_delete = [s for s in self.all_subs if s.file_path == file_to_remove]
            for s in subs_to_delete:
                s.destroy_widget()
                self.all_subs.remove(s)

            del self.file_list[index]
            self.file_listbox.delete(index)

        if not any(s.is_selected() for s in self.all_subs):
            self.burn_subtitles_var.set(False)

    def _clear_all(self):
        self.file_list.clear()
        self.file_listbox.delete(0, tk.END)
        for sub in self.all_subs:
            sub.destroy_widget()
        self.all_subs.clear()
        self.burn_subtitles_var.set(False)

    def _move_up(self):
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

    def _move_down(self):
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

    def _detect_subtitle_tracks_for_file(self, file_path):
        all_tracks = self.processor.detect_embedded_subtitle_tracks(file_path)
        if not all_tracks:
            logger.info(f"No embedded subtitle tracks found in {file_path}.")
            return

        first_selected = False
        for t in all_tracks:
            desc = f"Embedded: #{t['track_id']} - {t['lang']}"
            if t["title"]:
                desc += f" ({t['title']})"

            sub_id = f"embed_{os.path.basename(file_path)}_{t['track_id']}_{self.subtitle_id_counter}"
            self.subtitle_id_counter += 1

            cvar = tk.BooleanVar(value=False)
            cb = tk.Checkbutton(
                self.subtitle_tracks_list_frame,
                text=desc,
                variable=cvar,
                command=self._on_subtitle_check,
                anchor="w"
            )
            cb.pack(fill="x", padx=20, anchor="w")

            track_obj = SubtitleTrack(
                track_id=sub_id,
                track_type="embedded",
                file_path=file_path,
                external_path=None,
                description=desc,
                widget=cb,
                check_var=cvar
            )
            self.all_subs.append(track_obj)

            if not first_selected:
                cvar.set(True)
                self._on_subtitle_check()
                first_selected = True

    def _load_embedded_srt(self):
        for f in self.file_list:
            self._detect_subtitle_tracks_for_file(f)

    def _add_external_srt(self):
        srt_files = filedialog.askopenfilenames(
            filetypes=[("Subtitle Files", "*.srt"), ("All Files", "*.*")]
        )
        for s in srt_files:
            if any(x.track_type == "external" and x.external_path == s for x in self.all_subs):
                continue

            desc = f"External: {os.path.basename(s)}"
            sub_id = f"ext_{os.path.basename(s)}_{self.subtitle_id_counter}"
            self.subtitle_id_counter += 1

            cvar = tk.BooleanVar(value=False)
            cb = tk.Checkbutton(
                self.subtitle_tracks_list_frame,
                text=desc,
                variable=cvar,
                command=self._on_subtitle_check,
                anchor="w"
            )
            cb.pack(fill="x", padx=20, anchor="w")

            track_obj = SubtitleTrack(
                track_id=sub_id,
                track_type="external",
                file_path=None,
                external_path=s,
                description=desc,
                widget=cb,
                check_var=cvar
            )
            self.all_subs.append(track_obj)

            cvar.set(True)
            self._on_subtitle_check()

    def _remove_selected_srt(self):
        for sub in list(self.all_subs):
            if sub.track_type == "external" and sub.is_selected():
                sub.destroy_widget()
                self.all_subs.remove(sub)
                break

        if not any(s.is_selected() for s in self.all_subs):
            self.burn_subtitles_var.set(False)

    def _on_subtitle_check(self):
        self.burn_subtitles_var.set(any(s.is_selected() for s in self.all_subs))

    def _select_all_subtitles(self):
        for s in self.all_subs:
            s.check_var.set(True)
        self.burn_subtitles_var.set(True)

    def _deselect_all_subtitles(self):
        for s in self.all_subs:
            s.check_var.set(False)
        self.burn_subtitles_var.set(False)

    # -------------------------------------------------------------------------
    # FRUC Toggle
    # -------------------------------------------------------------------------
    def _toggle_fruc_fps(self):
        if self.fruc_var.get():
            self.fruc_fps_entry.configure(state="normal")
        else:
            self.fruc_fps_entry.configure(state="disabled")

    # -------------------------------------------------------------------------
    # ENCODING LOGIC
    # -------------------------------------------------------------------------
    def _start_processing(self):
        if not self.file_list:
            messagebox.showwarning("No Files", "Please add at least one file to process.")
            return

        self.root.destroy()

        num_workers = int(self.parallel_count_var.get())
        if num_workers == 1:
            # sequential
            for file_path in self.file_list:
                self._process_one_file(file_path)
        else:
            # parallel
            logger.info(f"Starting parallel processing with {num_workers} workers.")
            with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
                futures = [executor.submit(self._process_one_file, f) for f in self.file_list]
                for fut in concurrent.futures.as_completed(futures):
                    exc = fut.exception()
                    if exc:
                        logger.error(f"Error in parallel job: {exc}")

        logger.info("Processing Complete. Press Enter to exit.")
        input("Press Enter to continue...")

    def _get_selected_subtitle_for_file(self, file_path):
        for s in self.all_subs:
            if s.is_selected():
                if s.track_type == "embedded" and s.file_path == file_path:
                    return s
                elif s.track_type == "external":
                    return s
        return None

    def _process_one_file(self, file_path):
        """
        Encodes a single file (with or without subtitles).
        """
        try:
            qvbr_value = int(self.qvbr_var.get())
            fruc_fps_target = int(self.fruc_fps_var.get())
        except ValueError:
            logger.error("QVBR and FRUC FPS Target must be integers.")
            return

        resolution = self.resolution_var.get()
        eight_bit = self.eight_bit_var.get()
        crop_enabled = self.crop_var.get()
        fruc_enable = self.fruc_var.get()
        generate_log = self.generate_log_var.get()
        alignment = self.alignment_var.get()

        # If no subtitles => single pass
        if not self.burn_subtitles_var.get():
            self.processor.encode_single_pass(
                file_path=file_path,
                resolution=resolution,
                qvbr_value=qvbr_value,
                fruc_enable=fruc_enable,
                fruc_fps_target=fruc_fps_target,
                generate_log=generate_log,
                eight_bit=eight_bit,
                crop_enabled=crop_enabled,
                alignment=alignment
            )
            return

        # Otherwise, see if we have an embedded or external sub
        sub_found = self._get_selected_subtitle_for_file(file_path)
        if not sub_found:
            self.processor.encode_single_pass(
                file_path=file_path,
                resolution=resolution,
                qvbr_value=qvbr_value,
                fruc_enable=fruc_enable,
                fruc_fps_target=fruc_fps_target,
                generate_log=generate_log,
                eight_bit=eight_bit,
                crop_enabled=crop_enabled,
                alignment=alignment
            )
            return

        # If sub is external
        if sub_found.track_type == "external":
            self.processor.encode_with_external_srt(
                file_path=file_path,
                srt_file=sub_found.external_path,
                resolution=resolution,
                qvbr_value=qvbr_value,
                fruc_enable=fruc_enable,
                fruc_fps_target=fruc_fps_target,
                generate_log=generate_log,
                eight_bit=eight_bit,
                crop_enabled=crop_enabled,
                alignment=alignment
            )
        else:
            # embedded
            tokens = sub_found.track_id.split("_")
            real_track_idx = tokens[2] if len(tokens) > 2 else "0"

            self.processor.encode_with_embedded_sub(
                file_path=file_path,
                track_id=real_track_idx,
                resolution=resolution,
                qvbr_value=qvbr_value,
                fruc_enable=fruc_enable,
                fruc_fps_target=fruc_fps_target,
                generate_log=generate_log,
                eight_bit=eight_bit,
                crop_enabled=crop_enabled,
                alignment=alignment
            )


# ----------------------------------------------------------------------
if __name__ == "__main__":
    initial_files = sys.argv[1:] if len(sys.argv) > 1 else []
    root = TkinterDnD.Tk()
    app = VideoProcessorApp(root, initial_files)
    root.mainloop()
