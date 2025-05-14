import os
import subprocess
import shutil
import json
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from tkinterdnd2 import TkinterDnD, DND_FILES
from ftfy import fix_text
import sys
import logging

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

# Set UTF-8 encoding for subprocesses
env = os.environ.copy()
env["PYTHONIOENCODING"] = "utf-8"

# --- Utility Functions (ffprobe, etc.) ---
def get_video_metadata_value(file_path, show_entries_options, stream_key, value_key, default_value, is_int=False):
    """Helper function to get specific metadata using ffprobe."""
    cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0"]
    cmd.extend(show_entries_options)
    cmd.extend(["-of", "json", file_path])
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, env=env, encoding='utf-8')
        data = json.loads(result.stdout)
        value = data.get("streams", [{}])[0].get(value_key, default_value)
        if value == default_value and value_key not in data.get("streams", [{}])[0]:
             if value_key == "bits_per_raw_sample" and default_value == 8:
                 return 8
             return default_value

        if is_int:
            if isinstance(value, str) and value.isdigit():
                return int(value)
            elif isinstance(value, int):
                return value
            return default_value
        return value
    except subprocess.CalledProcessError as e:
        logging.warning(f"ffprobe command failed for {file_path} ({' '.join(show_entries_options)}): {e.stderr}")
        return default_value
    except Exception as e:
        logging.warning(f"Could not parse metadata for {file_path} ({' '.join(show_entries_options)}): {e}")
        return default_value

def get_video_bit_depth(file_path):
    return get_video_metadata_value(file_path, ["-show_entries", "stream=bits_per_raw_sample"],
                                    "streams", "bits_per_raw_sample", 8, is_int=True)

def is_hdr(file_path):
    color_transfer = get_video_metadata_value(file_path, ["-show_entries", "stream=color_transfer"],
                                             "streams", "color_transfer", "", is_int=False)
    color_primaries = get_video_metadata_value(file_path, ["-show_entries", "stream=color_primaries"],
                                               "streams", "color_primaries", "", is_int=False)
    if isinstance(color_transfer, str) and color_transfer.lower() in ["smpte2084", "arib-std-b67", "pq", "smpte428"]:
        return True
    if isinstance(color_primaries, str) and color_primaries.lower() == "bt2020":
        return True
    return False

def get_input_width(file_path):
    width_str = get_video_metadata_value(file_path, ["-show_entries", "stream=width"],
                                        "streams", "width", "0", is_int=False)
    try:
        return int(width_str)
    except ValueError:
        logging.error(f"ffprobe output for width is not an integer: {width_str} for {file_path}")
        return None

def get_input_height(file_path):
    height_str = get_video_metadata_value(file_path, ["-show_entries", "stream=height"],
                                          "streams", "height", "0", is_int=False)
    try:
        return int(height_str)
    except ValueError:
        logging.error(f"ffprobe output for height is not an integer: {height_str} for {file_path}")
        return None

def normalize_text(text):
    normalized_text = fix_text(text)
    normalized_text = normalized_text.replace("’", "'")
    return normalized_text

def cleanup_ass_content(ass_file):
    r"""Remove \\N line breaks from ASS file content.
    This is a specific behavior and might not be universally desired,
    as \N is the standard line break in ASS.
    """
    try:
        with open(ass_file, 'r', encoding='utf-8') as f:
            content = f.readlines()
        cleaned_lines = []
        for line in content:
            cleaned_line = line.replace(r'\N', ' ', 1)
            cleaned_lines.append(cleaned_line)
        with open(ass_file, 'w', encoding='utf-8', newline='') as f:
            f.writelines(cleaned_lines)
        logging.debug(f"Performed line break cleanup on ASS file: {ass_file}")
    except Exception as e:
        logging.error(f"Error cleaning up ASS content (removing \\N) for {ass_file}: {e}")

class VideoProcessorApp:
    def __init__(self, root, initial_files):
        self.root = root
        self.root.title("Video Processing Tool v2.2") # Version update
        self.lut_file = r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\LUT\NBCU\5-NBCU_PQ2SDR_DL_RESOLVE17-VRT_v1.2.cube"
        self.subtitles_by_file = {}
        self.file_list = []
        self.subtitle_id_counter = 0
        self.current_subtitle_checkbuttons = {}
        self.file_options = {}

        # --- Tkinter Variables ---
        self.resolution_var = tk.StringVar(value="4k")
        self.upscale_algo_var = tk.StringVar(value="nvvfx-superres")
        self.eight_bit_var = tk.BooleanVar(value=False)
        self.hdr_var = tk.BooleanVar(value=True)
        self.convert_hdr_var = tk.BooleanVar(value=False)
        self.crop_var = tk.BooleanVar(value=False)
        self.qvbr_var = tk.StringVar(value="12")
        self.fruc_var = tk.BooleanVar(value=False)
        self.fruc_fps_var = tk.StringVar(value="60")

        self.alignment_var = tk.StringVar(value="bottom")
        self.subtitle_font_name_var = tk.StringVar(value="Futura")
        self.subtitle_font_size_var = tk.StringVar(value="24")

        self.generate_log_var = tk.BooleanVar(value=False)
        self.widget_mixed_values = {}


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

        tk.Button(self.file_buttons_frame, text="Select All", command=self.select_all_files).pack(side=tk.LEFT, padx=5)
        tk.Button(self.file_buttons_frame, text="Add Files", command=self.add_files).pack(side=tk.LEFT, padx=5)
        tk.Button(self.file_buttons_frame, text="Remove Selected", command=self.remove_selected).pack(side=tk.LEFT, padx=5)
        tk.Button(self.file_buttons_frame, text="Clear All", command=self.clear_all).pack(side=tk.LEFT, padx=5)
        tk.Button(self.file_buttons_frame, text="Move Up", command=self.move_up).pack(side=tk.LEFT, padx=5)
        tk.Button(self.file_buttons_frame, text="Move Down", command=self.move_down).pack(side=tk.LEFT, padx=5)

        self.options_frame = tk.Frame(root)
        self.options_frame.pack(fill=tk.X, padx=10, pady=10)

        res_frame = tk.LabelFrame(self.options_frame, text="Resolution & Upscaling", padx=10, pady=5)
        res_frame.grid(row=0, column=0, columnspan=4, sticky="ew", pady=5)
        tk.Label(res_frame, text="Resolution:").grid(row=0, column=0, sticky=tk.W)
        for i, (text, val) in enumerate([("Original", "original"), ("4K", "4k"), ("8K", "8k")]):
            tk.Radiobutton(res_frame, text=text, variable=self.resolution_var, value=val,
                           command=lambda v=val: self.apply_specific_option_to_selected_files("resolution", v)
                           ).grid(row=0, column=i + 1, sticky=tk.W)
        tk.Label(res_frame, text="Upscale Algo:").grid(row=1, column=0, sticky=tk.W, padx=(10,0))
        for i, (text, val) in enumerate([("NVVFX SuperRes", "nvvfx-superres"), ("NGX VSR", "ngx-vsr")]):
            tk.Radiobutton(res_frame, text=text, variable=self.upscale_algo_var, value=val,
                           command=lambda v=val: self.apply_specific_option_to_selected_files("upscale_algo", v)
                           ).grid(row=1, column=i + 1, sticky=tk.W)

        row_idx = 1
        tk.Label(self.options_frame, text="Convert to 8-bit (SDR):").grid(row=row_idx, column=0, sticky=tk.W)
        tk.Checkbutton(self.options_frame, variable=self.eight_bit_var,
                         command=lambda: self.apply_specific_option_to_selected_files("eight_bit", self.eight_bit_var.get())
                         ).grid(row=row_idx, column=1, sticky=tk.W); row_idx+=1

        tk.Label(self.options_frame, text="Convert to HDR (TrueHDR VPP):").grid(row=row_idx, column=0, sticky=tk.W)
        tk.Checkbutton(self.options_frame, variable=self.convert_hdr_var,
                         command=lambda: self.apply_specific_option_to_selected_files("convert_hdr", self.convert_hdr_var.get())
                         ).grid(row=row_idx, column=1, sticky=tk.W); row_idx+=1

        tk.Label(self.options_frame, text="HDR Metadata (for mkvmerge):").grid(row=row_idx, column=0, sticky=tk.W)
        tk.Checkbutton(self.options_frame, variable=self.hdr_var,
                         command=lambda: self.apply_specific_option_to_selected_files("hdr", self.hdr_var.get())
                         ).grid(row=row_idx, column=1, sticky=tk.W); row_idx+=1
        
        tk.Label(self.options_frame, text="Vertical Crop:").grid(row=row_idx, column=0, sticky=tk.W)
        tk.Checkbutton(self.options_frame, variable=self.crop_var,
                         command=lambda: self.apply_specific_option_to_selected_files("crop", self.crop_var.get())
                         ).grid(row=row_idx, column=1, sticky=tk.W); row_idx+=1

        tk.Label(self.options_frame, text="QVBR Value:").grid(row=row_idx, column=0, sticky=tk.W)
        self.qvbr_entry = tk.Entry(self.options_frame, textvariable=self.qvbr_var, width=10)
        self.qvbr_entry.grid(row=row_idx, column=1, sticky=tk.W)
        self.qvbr_entry.bind("<FocusOut>", lambda e: self.apply_specific_option_to_selected_files("qvbr", self.qvbr_var.get()))
        row_idx+=1

        tk.Label(self.options_frame, text="Enable FRUC:").grid(row=row_idx, column=0, sticky=tk.W)
        self.fruc_checkbox = tk.Checkbutton(self.options_frame, variable=self.fruc_var,
                                            command=self.toggle_fruc_and_apply) # CHANGED
        self.fruc_checkbox.grid(row=row_idx, column=1, sticky=tk.W); row_idx+=1

        tk.Label(self.options_frame, text="FRUC FPS Target:").grid(row=row_idx, column=0, sticky=tk.W)
        self.fruc_fps_entry = tk.Entry(self.options_frame, textvariable=self.fruc_fps_var, width=10, state="disabled")
        self.fruc_fps_entry.grid(row=row_idx, column=1, sticky=tk.W)
        self.fruc_fps_entry.bind("<FocusOut>", lambda e: self.apply_specific_option_to_selected_files("fruc_fps", self.fruc_fps_var.get()))
        row_idx+=1

        sub_style_frame = tk.LabelFrame(self.options_frame, text="Subtitle Styling", padx=10, pady=5)
        sub_style_frame.grid(row=row_idx, column=0, columnspan=2, sticky="ew", pady=5); row_idx+=1
        
        tk.Label(sub_style_frame, text="Alignment:").grid(row=0, column=0, sticky=tk.W)
        align_options_frame = tk.Frame(sub_style_frame)
        align_options_frame.grid(row=0, column=1, sticky=tk.W)
        for i, (text, val) in enumerate([("Top", "top"), ("Middle", "middle"), ("Bottom", "bottom")]):
            tk.Radiobutton(align_options_frame, text=text, variable=self.alignment_var, value=val,
                           command=lambda v=val: self.apply_specific_option_to_selected_files("alignment", v)
                           ).pack(side=tk.LEFT)

        tk.Label(sub_style_frame, text="Font Name:").grid(row=1, column=0, sticky=tk.W)
        self.subtitle_font_name_entry = tk.Entry(sub_style_frame, textvariable=self.subtitle_font_name_var, width=15)
        self.subtitle_font_name_entry.grid(row=1, column=1, sticky=tk.W)
        self.subtitle_font_name_entry.bind("<FocusOut>", lambda e: self.apply_specific_option_to_selected_files("subtitle_font_name", self.subtitle_font_name_var.get()))

        tk.Label(sub_style_frame, text="Font Size:").grid(row=2, column=0, sticky=tk.W)
        self.subtitle_font_size_entry = tk.Entry(sub_style_frame, textvariable=self.subtitle_font_size_var, width=10)
        self.subtitle_font_size_entry.grid(row=2, column=1, sticky=tk.W)
        self.subtitle_font_size_entry.bind("<FocusOut>", lambda e: self.apply_specific_option_to_selected_files("subtitle_font_size", self.subtitle_font_size_var.get()))

        self.subtitle_tracks_frame = tk.LabelFrame(root, text="Subtitle Tracks (Select one to burn & create sidecars)", padx=10, pady=10)
        self.subtitle_tracks_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.subtitle_tracks_buttons_frame = tk.Frame(self.subtitle_tracks_frame)
        self.subtitle_tracks_buttons_frame.pack(fill=tk.X, padx=5, pady=5)

        tk.Button(self.subtitle_tracks_buttons_frame, text="Load Embedded SRT (All Files)", command=self.load_embedded_srt_all).pack(side=tk.LEFT, padx=(0,5))
        tk.Button(self.subtitle_tracks_buttons_frame, text="Add External SRT (Current File)", command=self.add_external_srt).pack(side=tk.LEFT, padx=(0,5))
        tk.Button(self.subtitle_tracks_buttons_frame, text="Remove Selected SRT (Current File)", command=self.remove_selected_srt_from_gui).pack(side=tk.LEFT, padx=(0,5))

        self.subtitle_tracks_list_frame = tk.Frame(self.subtitle_tracks_frame) 
        self.subtitle_tracks_list_frame.pack(fill=tk.X)

        self.bottom_frame = tk.Frame(root)
        self.bottom_frame.pack(pady=10, padx=10, fill=tk.X)
        tk.Button(self.bottom_frame, text="Start Processing", command=self.start_processing_and_close_gui).pack(side=tk.LEFT, padx=5)
        tk.Checkbutton(self.bottom_frame, text="Generate NVEncC Log File", variable=self.generate_log_var,
                         command=lambda: self.apply_specific_option_to_selected_files("generate_log", self.generate_log_var.get())
                         ).pack(side=tk.LEFT, padx=(10,0))

        self.update_file_list(initial_files)
        if self.file_listbox.size() > 0:
            self.file_listbox.select_set(0)
            self.on_file_select(None)

    def _get_default_file_options(self):
        return {
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
            "subtitle_font_name": self.subtitle_font_name_var.get(),
            "subtitle_font_size": self.subtitle_font_size_var.get(),
            "generate_log": self.generate_log_var.get(),
        }

    def apply_specific_option_to_selected_files(self, option_key, new_value):
        selected_indices = self.file_listbox.curselection()
        if not selected_indices:
            return

        for index in selected_indices:
            filepath = self.file_list[index]
            if filepath not in self.file_options:
                self.file_options[filepath] = self._get_default_file_options()
            
            self.file_options[filepath][option_key] = new_value
            logging.debug(f"Set option '{option_key}' to '{new_value}' for {os.path.basename(filepath)}")
        self.on_file_select(None) # Refresh GUI based on (potentially) changed options

    def toggle_fruc_and_apply(self): # REVISED FRUC LOGIC
        self.toggle_fruc_fps_entry_state() # Visually enable/disable FPS entry
        
        current_fruc_state = self.fruc_var.get() # Get the new state of the FRUC checkbox
        self.apply_specific_option_to_selected_files("fruc", current_fruc_state)

        # If FRUC is being enabled, ensure a valid FPS is set and saved.
        # If FRUC is being disabled, the current FPS value is less critical but saved anyway.
        current_fruc_fps_str = self.fruc_fps_var.get()
        if current_fruc_state: # If FRUC is now enabled
            try:
                fps_val = int(current_fruc_fps_str)
                if fps_val <= 0:
                    logging.warning(f"FRUC enabled with invalid FPS '{current_fruc_fps_str}', defaulting to 60 for GUI and options.")
                    self.fruc_fps_var.set("60")
                    current_fruc_fps_str = "60"
            except ValueError: # Non-integer in FPS field
                logging.warning(f"FRUC enabled with non-integer FPS '{current_fruc_fps_str}', defaulting to 60 for GUI and options.")
                self.fruc_fps_var.set("60")
                current_fruc_fps_str = "60"
        
        self.apply_specific_option_to_selected_files("fruc_fps", current_fruc_fps_str)


    def compute_final_resolution(self, file_path):
        options = self.file_options.get(file_path, self._get_default_file_options())
        resolution_setting = options.get("resolution", "original")

        in_w = get_input_width(file_path)
        in_h = get_input_height(file_path)

        if in_w is None or in_h is None:
            logging.error(f"Cannot determine input dimensions for {file_path}. Skipping resolution computation.")
            return None, None

        if resolution_setting == "original":
            return in_w, in_h
        elif resolution_setting == "4k":
            return 2160, 2160
        elif resolution_setting == "8k":
            return 4320, 4320
        else:
            return in_w, in_h

    def auto_set_hdr(self, file_path):
        is_hdr_video = is_hdr(file_path)
        return not is_hdr_video


    def add_files(self):
        files = filedialog.askopenfilenames(
            filetypes=[("Video Files", "*.mp4;*.mkv;*.avi;*.mov;*.webm"), ("All Files", "*.*")]
        )
        self.update_file_list(files)
        if self.file_listbox.size() > 0 and not self.file_listbox.curselection():
            self.file_listbox.select_set(0)
            self.on_file_select(None)

    def handle_file_drop(self, event):
        try:
            files_str = event.data
            if files_str.startswith('{') and files_str.endswith('}'):
                files_str = files_str[1:-1]
                files = [f.strip('{}') for f in files_str.split('} {')]
            else:
                files = self.root.tk.splitlist(files_str)
        except Exception as e:
            logging.error(f"Error processing dropped files: {e}")
            files = []

        valid_files = [f for f in files if os.path.exists(f) and not os.path.isdir(f)]
        self.update_file_list(valid_files)

        if self.file_listbox.size() > 0 and not self.file_listbox.curselection():
            self.file_listbox.select_set(0)
            self.on_file_select(None)


    def update_file_list(self, files_to_add):
        newly_added_files = []
        for file_path in files_to_add:
            if file_path not in self.file_list:
                self.file_list.append(file_path)
                self.file_listbox.insert(tk.END, os.path.basename(file_path))
                self.subtitles_by_file[file_path] = []
                
                default_opts = self._get_default_file_options()
                default_opts["hdr"] = self.auto_set_hdr(file_path)
                self.file_options[file_path] = default_opts
                
                self.detect_subtitle_tracks(file_path)
                newly_added_files.append(file_path)
        
        if newly_added_files and self.file_listbox.size() == len(newly_added_files):
            self.file_listbox.select_set(0)
            self.on_file_select(None)
        elif newly_added_files :
            try:
                first_new_idx = self.file_list.index(newly_added_files[0])
                self.file_listbox.select_clear(0,tk.END)
                self.file_listbox.select_set(first_new_idx)
                self.on_file_select(None)
            except ValueError:
                pass


    def select_all_files(self):
        self.file_listbox.select_set(0, tk.END)
        self.on_file_select(None)

    def remove_selected(self):
        selected_indices = list(self.file_listbox.curselection())
        selected_indices.sort(reverse=True)

        for index in selected_indices:
            file_to_remove = self.file_list.pop(index)
            self.file_listbox.delete(index)
            if file_to_remove in self.subtitles_by_file:
                del self.subtitles_by_file[file_to_remove]
            if file_to_remove in self.file_options:
                del self.file_options[file_to_remove]
        
        if self.file_list:
            new_selection_idx = min(selected_indices[-1] if selected_indices else 0, len(self.file_list) - 1)
            self.file_listbox.select_set(new_selection_idx)
        
        self.on_file_select(None)

    def clear_all(self):
        self.file_list.clear()
        self.file_listbox.delete(0, tk.END)
        self.subtitles_by_file.clear()
        self.file_options.clear()
        self.on_file_select(None)

    def _swap_files_in_list(self, idx1, idx2):
        self.file_list[idx1], self.file_list[idx2] = self.file_list[idx2], self.file_list[idx1]
        item1_text = self.file_listbox.get(idx1)
        item2_text = self.file_listbox.get(idx2)
        self.file_listbox.delete(idx1)
        self.file_listbox.insert(idx1, item2_text)
        self.file_listbox.delete(idx2)
        self.file_listbox.insert(idx2, item1_text)

    def move_up(self):
        selected_indices = list(self.file_listbox.curselection())
        if not selected_indices or selected_indices[0] == 0:
            return
        
        selected_indices.sort()
        new_selection_indices = []
        for index in selected_indices:
            if index > 0:
                self._swap_files_in_list(index, index - 1)
                new_selection_indices.append(index - 1)
            else:
                new_selection_indices.append(index)
        
        self.file_listbox.select_clear(0, tk.END)
        for idx in new_selection_indices:
            self.file_listbox.select_set(idx)
        self.on_file_select(None)


    def move_down(self):
        selected_indices = list(self.file_listbox.curselection())
        if not selected_indices or selected_indices[-1] == len(self.file_list) - 1:
            return

        selected_indices.sort(reverse=True)
        new_selection_indices = []
        for index in selected_indices:
            if index < len(self.file_list) - 1:
                self._swap_files_in_list(index, index + 1)
                new_selection_indices.append(index + 1)
            else:
                new_selection_indices.append(index)
        
        self.file_listbox.select_clear(0, tk.END)
        for idx in new_selection_indices:
            self.file_listbox.select_set(idx)
        self.on_file_select(None)


    def detect_subtitle_tracks(self, file_path):
        cmd = ["ffprobe", "-v", "error", "-select_streams", "s",
               "-show_entries", "stream=index:stream_tags=language:stream_tags=title",
               "-of", "json", file_path]
        logging.info(f"Detecting subtitle tracks for {file_path}")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, env=env, encoding='utf-8')
            data = json.loads(result.stdout)
            
            if file_path not in self.subtitles_by_file:
                self.subtitles_by_file[file_path] = []

            for stream_idx, stream in enumerate(data.get("streams", [])):
                track_id_for_map = str(stream_idx)
                lang = stream.get("tags", {}).get("language", "und")
                title = stream.get("tags", {}).get("title", "")
                desc = f"Embedded (s:{track_id_for_map}): {lang}"
                if title: desc += f" ({title})"
                sub_unique_id = f"embed_{os.path.basename(file_path)}_s{track_id_for_map}_{self.subtitle_id_counter}"
                self.subtitle_id_counter += 1
                
                if any(s["track_id_for_map"] == track_id_for_map and s["type"] == "embedded" for s in self.subtitles_by_file[file_path]):
                    continue

                self.subtitles_by_file[file_path].append({
                    "id": sub_unique_id, "type": "embedded", "file_path_source": file_path,
                    "track_id_for_map": track_id_for_map, 
                    "ffmpeg_stream_index": str(stream.get("index")),
                    "external_path": None, "description": desc, "selected_for_burn": False
                })
        except subprocess.CalledProcessError as e:
            logging.warning(f"ffprobe found no subtitle tracks or errored for {file_path}: {e.stderr if e.stderr else e.stdout}")
        except Exception as e:
            logging.error(f"Error detecting subtitle tracks for {file_path}: {e}")
        
        current_selection_indices = self.file_listbox.curselection()
        if current_selection_indices and self.file_list[current_selection_indices[0]] == file_path:
            self.refresh_subtitle_list_for_current_file()


    def load_embedded_srt_all(self):
        for file_path_in_queue in self.file_list:
            self.detect_subtitle_tracks(file_path_in_queue)
        self.refresh_subtitle_list_for_current_file()


    def add_external_srt(self):
        sel_indices = self.file_listbox.curselection()
        if not sel_indices:
            messagebox.showwarning("No File Selected", "Please select a video file from the list first.")
            return
        
        current_file_path = self.file_list[sel_indices[0]]
        initial_dir = os.path.dirname(current_file_path)

        srt_files_paths = filedialog.askopenfilenames(
            title=f"Add External Subtitles for {os.path.basename(current_file_path)}",
            filetypes=[("Subtitle Files", "*.srt;*.ass"), ("All Files", "*.*")],
            initialdir=initial_dir
        )
        if not srt_files_paths: return

        for srt_path in srt_files_paths:
            already_exists = any(
                s["type"] == "external" and s["external_path"] == srt_path 
                for s in self.subtitles_by_file.get(current_file_path, [])
            )
            if already_exists:
                logging.info(f"Subtitle {os.path.basename(srt_path)} already added for {os.path.basename(current_file_path)}.")
                continue

            srt_base = os.path.basename(srt_path)
            desc = f"External: {srt_base}"
            sub_unique_id = f"ext_{srt_base}_{self.subtitle_id_counter}"
            self.subtitle_id_counter += 1
            
            self.subtitles_by_file[current_file_path].append({
                "id": sub_unique_id, "type": "external", "file_path_source": current_file_path, 
                "track_id_for_map": None, "ffmpeg_stream_index": None,
                "external_path": srt_path, "description": desc, "selected_for_burn": False
            })
        self.refresh_subtitle_list_for_current_file()

    def remove_selected_srt_from_gui(self):
        sel_indices = self.file_listbox.curselection()
        if not sel_indices:
            messagebox.showwarning("No File Selected", "Please select a video file.")
            return
        current_file_path = self.file_list[sel_indices[0]]

        if current_file_path not in self.subtitles_by_file or not self.subtitles_by_file[current_file_path]:
            messagebox.showinfo("No Subtitles", "No subtitles to remove for the selected file.")
            return

        new_subs_list = [s for s in self.subtitles_by_file[current_file_path] if s["type"] != "external"]
        
        if len(new_subs_list) < len(self.subtitles_by_file[current_file_path]):
            self.subtitles_by_file[current_file_path] = new_subs_list
            logging.info(f"Removed all external subtitles for {os.path.basename(current_file_path)}.")
            self.refresh_subtitle_list_for_current_file()
        else:
            messagebox.showinfo("No External Subtitles", "No external subtitles found to remove for this file.")


    def on_file_select(self, event=None):
        selected_indices = self.file_listbox.curselection()

        if not selected_indices:
            for var_attr, default_val in [
                ('resolution_var', '4k'), ('upscale_algo_var', 'nvvfx-superres'),
                ('eight_bit_var', False), ('hdr_var', True), ('convert_hdr_var', False),
                ('crop_var', False), ('qvbr_var', "12"), ('fruc_var', False),
                ('fruc_fps_var', "60"), ('alignment_var', 'bottom'),
                ('subtitle_font_name_var', 'Futura'), ('subtitle_font_size_var', '24'),
                ('generate_log_var', False)
            ]:
                getattr(self, var_attr).set(default_val)
            self.toggle_fruc_fps_entry_state()
            self.refresh_subtitle_list_for_current_file()
            return

        first_selected_filepath = self.file_list[selected_indices[0]]
        
        options_to_check = [
            ("resolution", self.resolution_var), ("upscale_algo", self.upscale_algo_var),
            ("eight_bit", self.eight_bit_var), ("hdr", self.hdr_var),
            ("convert_hdr", self.convert_hdr_var), ("crop", self.crop_var),
            ("qvbr", self.qvbr_var), ("fruc", self.fruc_var),
            ("fruc_fps", self.fruc_fps_var), ("alignment", self.alignment_var),
            ("subtitle_font_name", self.subtitle_font_name_var),
            ("subtitle_font_size", self.subtitle_font_size_var),
            ("generate_log", self.generate_log_var)
        ]

        for key, tk_var in options_to_check:
            ref_value = self.file_options.get(first_selected_filepath, {}).get(key)
            if ref_value is None: ref_value = tk_var.get() 

            is_mixed = False
            if len(selected_indices) > 1:
                for idx in selected_indices[1:]:
                    fpath = self.file_list[idx]
                    if self.file_options.get(fpath, {}).get(key, tk_var.get()) != ref_value:
                        is_mixed = True; break
            
            if is_mixed:
                current_val = self.file_options.get(first_selected_filepath,{}).get(key, tk_var.get())
                tk_var.set(current_val)
                self.widget_mixed_values[key] = True
            else:
                tk_var.set(ref_value)
                self.widget_mixed_values[key] = False

        self.toggle_fruc_fps_entry_state()
        self.refresh_subtitle_list_for_current_file()

    def refresh_subtitle_list_for_current_file(self):
        for _id, cb_info in list(self.current_subtitle_checkbuttons.items()):
            cb_info["cb"].destroy()
            if cb_info["trace_id"]:
                try: cb_info["var"].trace_remove("write", cb_info["trace_id"])
                except tk.TclError: pass 
        self.current_subtitle_checkbuttons.clear()

        selected_indices = self.file_listbox.curselection()
        if not selected_indices: return

        current_file_path = self.file_list[selected_indices[0]]
        subs_for_this_file = self.subtitles_by_file.get(current_file_path, [])

        for sub_info in subs_for_this_file:
            var = tk.BooleanVar(value=sub_info.get("selected_for_burn", False))
            cb = tk.Checkbutton(self.subtitle_tracks_list_frame, text=sub_info["description"], variable=var, anchor="w")
            def _make_command(s_id, v_obj): return lambda name, index, mode: self.on_subtitle_burn_select(s_id, v_obj)
            trace_id = var.trace_add("write", _make_command(sub_info["id"], var))
            cb.pack(fill="x", padx=20, anchor="w")
            self.current_subtitle_checkbuttons[sub_info["id"]] = {"cb": cb, "var": var, "trace_id": trace_id}


    def on_subtitle_burn_select(self, selected_sub_id, var_of_selected_cb):
        selected_indices = self.file_listbox.curselection()
        if not selected_indices: return
        current_file_path = self.file_list[selected_indices[0]]
        is_now_selected = var_of_selected_cb.get()

        for sub_info in self.subtitles_by_file.get(current_file_path, []):
            current_sub_id = sub_info["id"]
            if current_sub_id == selected_sub_id:
                sub_info["selected_for_burn"] = is_now_selected
            elif is_now_selected:
                sub_info["selected_for_burn"] = False
                if current_sub_id in self.current_subtitle_checkbuttons:
                    other_cb_info = self.current_subtitle_checkbuttons[current_sub_id]
                    if other_cb_info["var"].get():
                        other_trace_id = other_cb_info["trace_id"]
                        other_cb_info["var"].trace_remove("write", other_trace_id)
                        other_cb_info["var"].set(False)
                        def _make_re_add_command(s_id, v_obj): return lambda name, index, mode: self.on_subtitle_burn_select(s_id, v_obj)
                        new_trace_id = other_cb_info["var"].trace_add("write", _make_re_add_command(current_sub_id, other_cb_info["var"]))
                        other_cb_info["trace_id"] = new_trace_id
        logging.debug(f"Subtitle {selected_sub_id} burn status for {os.path.basename(current_file_path)}: {is_now_selected}")


    def toggle_fruc_fps_entry_state(self):
        if self.fruc_var.get():
            self.fruc_fps_entry.config(state="normal")
        else:
            self.fruc_fps_entry.config(state="disabled")

    def fix_ass_style(self, ass_file, final_width, final_height, file_options):
        font_name = file_options.get("subtitle_font_name", self.subtitle_font_name_var.get())
        font_size_str = file_options.get("subtitle_font_size", self.subtitle_font_size_var.get())
        alignment_str = file_options.get("alignment", self.alignment_var.get())

        try: font_size = int(font_size_str)
        except ValueError:
            logging.warning(f"Invalid font size '{font_size_str}', using default 24 for {ass_file}"); font_size = 24
        alignment_map = {"top": 8, "middle": 5, "bottom": 2}; alignment_code = alignment_map.get(alignment_str, 2)
        margin_l = margin_r = int(final_width * 0.02)
        margin_v = int(final_height * 0.02) if alignment_code != 5 else int(final_height * 0.01)

        try:
            with open(ass_file, "r", encoding="utf-8") as f: lines = f.readlines()
            new_lines = []
            in_styles_section = False; style_format_line_found_or_added = False; default_style_found_and_replaced = False
            header_lines_buffer = [] 
            event_section_start_index = -1; v4_styles_section_start_index = -1

            for i, line in enumerate(lines):
                stripped_line = line.strip().lower()
                if stripped_line == "[v4+ styles]" or stripped_line == "[v4 styles]": v4_styles_section_start_index = i; break
                if stripped_line == "[events]": event_section_start_index = i
            
            current_lines_to_process = lines
            if v4_styles_section_start_index == -1: # No style section, will create one
                new_lines = list(lines) # Copy all lines
            else: # Style section exists
                new_lines.extend(lines[:v4_styles_section_start_index]) # Lines before V4 Styles
                current_lines_to_process = lines[v4_styles_section_start_index:]


            # Process or create V4+ Styles section
            if v4_styles_section_start_index != -1:
                for i, line_content in enumerate(current_lines_to_process):
                    stripped_line = line_content.strip()
                    if i == 0: # The [V4+ Styles] line itself
                        new_lines.append(line_content)
                        in_styles_section = True
                        new_lines.append("Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n")
                        style_format_line_found_or_added = True
                        continue
                    if in_styles_section:
                        if stripped_line.lower().startswith("format:"): continue
                        if stripped_line.lower().startswith("style: default"):
                            style_line = (f"Style: Default,{font_name},{font_size},"
                                          "&H00FFFFFF,&H000000FF,&H00000000,&H80000000,"
                                          "-1,0,0,0,100,100,0,0,1,2,1,"
                                          f"{alignment_code},{margin_l},{margin_r},{margin_v},1\n")
                            new_lines.append(style_line)
                            default_style_found_and_replaced = True
                            continue
                        if stripped_line.startswith("["):
                            if not default_style_found_and_replaced:
                                new_lines.append((f"Style: Default,{font_name},{font_size},"
                                                  "&H00FFFFFF,&H000000FF,&H00000000,&H80000000,"
                                                  "-1,0,0,0,100,100,0,0,1,2,1,"
                                                  f"{alignment_code},{margin_l},{margin_r},{margin_v},1\n"))
                            in_styles_section = False
                    new_lines.append(line_content)
                if in_styles_section and not default_style_found_and_replaced:
                     new_lines.append((f"Style: Default,{font_name},{font_size},"
                                      "&H00FFFFFF,&H000000FF,&H00000000,&H80000000,"
                                      "-1,0,0,0,100,100,0,0,1,2,1,"
                                      f"{alignment_code},{margin_l},{margin_r},{margin_v},1\n"))
            else: # No [V4+ Styles] section, create it
                style_section_content = [
                    "\n[V4+ Styles]\n",
                    "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n",
                    f"Style: Default,{font_name},{font_size},"
                    "&H00FFFFFF,&H000000FF,&H00000000,&H80000000,"
                    "-1,0,0,0,100,100,0,0,1,2,1,"
                    f"{alignment_code},{margin_l},{margin_r},{margin_v},1\n"
                ]
                if event_section_start_index != -1 and event_section_start_index < len(new_lines):
                    new_lines = new_lines[:event_section_start_index] + style_section_content + new_lines[event_section_start_index:]
                else: new_lines.extend(style_section_content)
            
            with open(ass_file, "w", encoding="utf-8", newline='') as f: f.writelines(new_lines)
            self.fix_overlapping_subtitle_lines(ass_file)

        except Exception as e: logging.error(f"Error fixing style in {ass_file}: {e}", exc_info=True)


    def fix_overlapping_subtitle_lines(self, ass_file):
        def ass_time_to_seconds(t_str):
            parts = t_str.split(':')
            try:
                h = int(parts[0]); m = int(parts[1]); s_ms_parts = parts[2].split('.')
                s = int(s_ms_parts[0]); cs = int(s_ms_parts[1])
                return h * 3600 + m * 60 + s + cs / 100.0
            except: return 0.0
        def seconds_to_ass_time(s_float):
            if s_float < 0: s_float = 0.0
            h = int(s_float // 3600); s_float %= 3600; m = int(s_float // 60); s_float %= 60
            s = int(s_float // 1); cs = int(round((s_float % 1) * 100))
            if cs >= 100: s += 1; cs = 0
            if s >= 60: m += s // 60; s %= 60
            if m >= 60: h += m // 60; m %= 60
            return f"{h:01}:{m:02}:{s:02}.{cs:02}"
        try:
            with open(ass_file, "r", encoding="utf-8") as f: lines = f.readlines()
            new_lines = []; in_events_section = False; last_end_time = 0.0
            dialogue_format_fields = []; text_field_index = -1; start_field_index = -1; end_field_index = -1
            for line_content in lines:
                stripped_line = line_content.strip()
                if stripped_line.lower() == "[events]":
                    in_events_section = True; new_lines.append(line_content); continue
                if in_events_section:
                    if stripped_line.lower().startswith("format:"):
                        dialogue_format_fields = [f.strip().lower() for f in stripped_line.split(":",1)[1].split(',')]
                        try:
                            text_field_index = dialogue_format_fields.index("text")
                            start_field_index = dialogue_format_fields.index("start")
                            end_field_index = dialogue_format_fields.index("end")
                        except ValueError: text_field_index = start_field_index = end_field_index = -1 
                        new_lines.append(line_content); continue
                    if stripped_line.lower().startswith("dialogue:") and all(i!=-1 for i in [text_field_index,start_field_index,end_field_index]):
                        parts = stripped_line.split(",", len(dialogue_format_fields) - 1)
                        if len(parts) == len(dialogue_format_fields):
                            parts[text_field_index] = normalize_text(parts[text_field_index])
                            current_start_sec = ass_time_to_seconds(parts[start_field_index])
                            current_end_sec = ass_time_to_seconds(parts[end_field_index])
                            if current_start_sec < last_end_time: current_start_sec = last_end_time + 0.01
                            if current_end_sec <= current_start_sec: current_end_sec = current_start_sec + 1.0
                            parts[start_field_index] = seconds_to_ass_time(current_start_sec)
                            parts[end_field_index] = seconds_to_ass_time(current_end_sec)
                            last_end_time = current_end_sec
                            new_lines.append(",".join(parts) + "\n")
                        else: new_lines.append(line_content)
                        continue
                    if stripped_line.startswith("["): in_events_section = False
                new_lines.append(line_content)
            with open(ass_file, "w", encoding="utf-8", newline='') as f: f.writelines(new_lines)
        except Exception as e: logging.error(f"Error fixing overlaps in {ass_file}: {e}", exc_info=True)


    def extract_embedded_subtitle_to_ass(self, input_file, output_ass, sub_track_id_for_map, final_width, final_height, file_options):
        os.makedirs(os.path.dirname(output_ass), exist_ok=True)
        cmd = ["ffmpeg", "-y", "-i", input_file, "-map", f"0:s:{sub_track_id_for_map}", "-c:s", "ass", output_ass]
        logging.info(f"Extracting embedded subtitle (map 0:s:{sub_track_id_for_map}) from {os.path.basename(input_file)} to {output_ass}")
        try:
            subprocess.run(cmd, check=True, env=env, capture_output=True, text=True, encoding='utf-8')
            self.fix_ass_style(output_ass, final_width, final_height, file_options)
            logging.info(f"Embedded track (map 0:s:{sub_track_id_for_map}) extracted and styled to ASS: {output_ass}")
        except subprocess.CalledProcessError as e: logging.error(f"Error extracting embedded subtitle (map 0:s:{sub_track_id_for_map}) from {input_file}: {e.stderr}")
        except Exception as e_gen: logging.error(f"General error during embedded subtitle extraction for {input_file}, map 0:s:{sub_track_id_for_map}: {e_gen}")


    def extract_external_srt_to_ass(self, srt_file_path, output_ass, final_width, final_height, file_options):
        os.makedirs(os.path.dirname(output_ass), exist_ok=True)
        self.cleanup_srt_encoding(srt_file_path)
        cmd = ["ffmpeg", "-y", "-sub_charenc", "UTF-8", "-i", srt_file_path, "-c:s", "ass", output_ass]
        logging.info(f"Converting external subtitle {srt_file_path} to ASS: {output_ass}")
        try:
            subprocess.run(cmd, check=True, env=env, capture_output=True, text=True, encoding='utf-8')
            self.fix_ass_style(output_ass, final_width, final_height, file_options)
        except subprocess.CalledProcessError as e: logging.error(f"Error converting external subtitle {srt_file_path} to ASS: {e.stderr}")
        except Exception as e_gen: logging.error(f"General error during external subtitle to ASS conversion for {srt_file_path}: {e_gen}")

    def extract_subtitle_to_srt(self, input_file_or_srt_path, output_srt, sub_track_id_for_map=None):
        os.makedirs(os.path.dirname(output_srt), exist_ok=True)
        if sub_track_id_for_map is not None:
            cmd = ["ffmpeg", "-y", "-i", input_file_or_srt_path, "-map", f"0:s:{sub_track_id_for_map}", "-c:s", "srt", output_srt]
            logging.info(f"Extracting embedded track (map 0:s:{sub_track_id_for_map}) from {os.path.basename(input_file_or_srt_path)} to SRT: {output_srt}")
            try:
                subprocess.run(cmd, check=True, env=env, capture_output=True, text=True, encoding='utf-8')
                self.cleanup_srt_encoding(output_srt)
            except subprocess.CalledProcessError as e: logging.error(f"Error extracting SRT (map 0:s:{sub_track_id_for_map}) from {input_file_or_srt_path}: {e.stderr}")
            except Exception as e_gen: logging.error(f"General error extracting SRT for {input_file_or_srt_path}, map 0:s:{sub_track_id_for_map}: {e_gen}")
        else:
            logging.info(f"Copying and cleaning external subtitle {input_file_or_srt_path} to {output_srt}")
            try:
                shutil.copyfile(input_file_or_srt_path, output_srt)
                self.cleanup_srt_encoding(output_srt)
            except Exception as e: logging.error(f"Error copying/cleaning external subtitle {input_file_or_srt_path}: {e}")

    def cleanup_srt_encoding(self, srt_file):
        try:
            with open(srt_file, 'rb') as f: raw_data = f.read()
            content = None; detected_encoding = None
            try: content = raw_data.decode('utf-8'); detected_encoding = 'utf-8'
            except UnicodeDecodeError:
                try: content = raw_data.decode('cp1252'); detected_encoding = 'cp1252'
                except UnicodeDecodeError:
                    try: content = raw_data.decode('latin-1'); detected_encoding = 'latin-1'
                    except Exception as e_enc: logging.warning(f"Could not decode SRT {srt_file}: {e_enc}. Skipping."); return
            if detected_encoding and detected_encoding != 'utf-8': logging.info(f"Converted SRT {srt_file} from {detected_encoding} to UTF-8.")
            if content:
                normalized_content = normalize_text(content)
                with open(srt_file, 'w', encoding='utf-8', newline='') as f: f.write(normalized_content)
        except FileNotFoundError: logging.error(f"SRT file not found for cleanup: {srt_file}")
        except Exception as e: logging.error(f"Error cleaning up SRT encoding for {srt_file}: {e}")

    def run_nvenc_command(self, cmd):
        # Quote arguments with spaces for logging, subprocess list doesn't need this if shell=False
        logging.info("Running NVEncC command:\n" + " ".join(f'"{c}"' if " " in c and not (c.startswith('"') and c.endswith('"')) else c for c in cmd))
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   env=env, text=True, encoding='utf-8', errors='replace', bufsize=1)
        if process.stdout:
            for line in iter(process.stdout.readline, ''):
                if "\r" in line:
                    progress_text = line.split("\r")[-1].strip()
                    sys.stdout.write(f"\r{progress_text}")
                    sys.stdout.flush()
                else: sys.stdout.write(line); sys.stdout.flush()
            process.stdout.close()
        ret_code = process.wait()
        sys.stdout.write("\n")
        if ret_code == 0: logging.info("NVEncC processing finished successfully.")
        else: logging.error(f"NVEncC processing failed with return code {ret_code}.")
        return ret_code

    def build_nvenc_command_and_run(self, file_path, output_file_path_override=None, ass_burn_path=None):
        file_options = self.file_options.get(file_path, self._get_default_file_options())
        qvbr_str = file_options.get("qvbr", "12")
        try:
            qvbr_val = int(qvbr_str)
            if not (0 < qvbr_val <= 51): logging.warning(f"QVBR {qvbr_val} out of range. Using 12."); qvbr_val = 12
        except ValueError: logging.warning(f"Invalid QVBR '{qvbr_str}'. Using 12."); qvbr_val = 12
        
        fruc_enable = file_options.get("fruc", False)
        fruc_fps_str = file_options.get("fruc_fps", "60")
        fruc_fps_target_for_cmd = 0
        if fruc_enable:
            try:
                fruc_fps_target_for_cmd = int(fruc_fps_str)
                if fruc_fps_target_for_cmd <=0: logging.warning(f"Invalid FRUC FPS. Disabling FRUC."); fruc_enable = False
            except ValueError: logging.warning(f"Invalid FRUC FPS string. Disabling FRUC."); fruc_enable = False

        final_width, final_height = self.compute_final_resolution(file_path)
        if final_width is None: logging.error(f"Skipping {os.path.basename(file_path)}: missing dimensions."); return None, None, None

        resolution_folder_name = file_options.get("resolution", "original")
        output_dir = os.path.join(os.path.dirname(file_path), resolution_folder_name); os.makedirs(output_dir, exist_ok=True)
        base_name, ext = os.path.splitext(os.path.basename(file_path)); ext = ext if ext else '.mkv' # Ensure extension
        eight_bit_suffix = "_8bit" if file_options.get("eight_bit") else ""
        sub_suffix = ""
        if ass_burn_path:
            bn_part = "".join(c for c in os.path.splitext(os.path.basename(ass_burn_path))[0] if c.isalnum() or c in ('_','-')).strip()[:30]
            if not base_name.endswith(bn_part): sub_suffix = f"_{bn_part}"

        temp_output_file = os.path.join(output_dir, f"{base_name}{sub_suffix}{eight_bit_suffix}_temp{ext}")
        final_output_file_after_mkvmerge = os.path.join(output_dir, f"{base_name}{sub_suffix}{eight_bit_suffix}{ext}")
        
        if output_file_path_override: temp_output_file = output_file_path_override

        cmd = self.construct_nvencc_command(
            file_path, temp_output_file, qvbr_val, file_options.get("eight_bit", False),
            fruc_enable, fruc_fps_target_for_cmd, file_options.get("generate_log", False),
            file_options.get("hdr", True), file_options.get("convert_hdr", False), ass_burn_path,
            file_options.get("upscale_algo", "nvvfx-superres"), f"{final_width}x{final_height}",
            resolution_folder_name not in ["original", ""]
        )
        if not cmd: return None, final_width, final_height

        ret_code = self.run_nvenc_command(cmd)
        
        if ret_code == 0:
            logging.info(f"Encoded: {file_path} -> {temp_output_file}")
            if not file_options.get("eight_bit") and file_options.get("hdr"):
                processed_output = self.apply_hdr_settings_mkvmerge(temp_output_file, final_output_file_after_mkvmerge)
                return processed_output, final_width, final_height
            else:
                try:
                    if os.path.exists(final_output_file_after_mkvmerge) and final_output_file_after_mkvmerge != temp_output_file:
                        os.remove(final_output_file_after_mkvmerge)
                    if temp_output_file != final_output_file_after_mkvmerge: shutil.move(temp_output_file, final_output_file_after_mkvmerge)
                    logging.info(f"Output file: {final_output_file_after_mkvmerge}")
                    return final_output_file_after_mkvmerge, final_width, final_height
                except Exception as e_move:
                    logging.error(f"Error moving/renaming {temp_output_file} to {final_output_file_after_mkvmerge}: {e_move}")
                    return temp_output_file, final_width, final_height
        else:
            logging.error(f"Error encoding {file_path}: NVEncC return code {ret_code}")
            if os.path.exists(temp_output_file):
                try: os.remove(temp_output_file); logging.info(f"Cleaned temp: {temp_output_file}")
                except Exception as e_del: logging.warning(f"Could not delete failed temp {temp_output_file}: {e_del}")
            return None, final_width, final_height


    def construct_nvencc_command(self, input_file, output_file, qvbr_value, eight_bit,
                                  fruc_enable, fruc_fps_target, generate_log,
                                  hdr_metadata_flag, convert_to_hdr_vpp, ass_burn_path,
                                  resize_algo, target_res_str, do_resize):
        cmd = ["NVEncC64", "--avhw", "--codec", "av1", "--qvbr", str(qvbr_value),
            "--preset", "p1", "--output-depth", "8" if eight_bit else "10",
            "--audio-copy", "--sub-copy", "--chapter-copy", "--key-on-chapter",
            "--transfer", "bt709" if eight_bit else "auto",
            "--colorprim", "bt709" if eight_bit else "auto",
            "--colormatrix", "bt709" if eight_bit else "auto",
            "--lookahead", "32", "--aq-temporal", "--multipass", "2pass-full",
            "--bframes", "4", "--log-level", "info", "--output", output_file, "-i", input_file]
        if eight_bit and os.path.exists(self.lut_file):
            cmd.extend(["--vpp-colorspace", f"lut3d=\"{self.lut_file}\",lut3d_interp=trilinear"])
            logging.info(f"Applying 3D LUT for HDR->SDR: {self.lut_file}")
        if do_resize:
            if 'x' not in target_res_str: logging.error(f"Invalid target res: {target_res_str}. Skipping resize.")
            else:
                algo_str = "ngx,vsr-quality=1" if resize_algo == "ngx-vsr" else resize_algo
                cmd.extend(["--vpp-resize", f"algo={algo_str}", "--output-res", f"{target_res_str},preserve_aspect_ratio=increase"])
        file_options_for_crop = self.file_options.get(input_file, {})
        if file_options_for_crop.get("crop", False):
            crop_str = self.compute_crop_value(input_file, file_options_for_crop)
            if crop_str and crop_str != "0,0,0,0": cmd.extend(["--crop", crop_str])
            elif crop_str is None: logging.error(f"Could not compute crop for {input_file}, skipping.")
        if fruc_enable and fruc_fps_target > 0: cmd.extend(["--vpp-fruc", f"fps={fruc_fps_target}"])
        if generate_log:
            log_path = os.path.join(os.path.dirname(output_file), f"{os.path.splitext(os.path.basename(output_file))[0]}_nvencc.log")
            cmd.extend(["--log", log_path, "--log-level", "debug"])
        if ass_burn_path and os.path.exists(ass_burn_path):
            cmd.extend(["--vpp-subburn", f"filename=\"{os.path.normpath(ass_burn_path)}\""])
            logging.info(f"Will burn subtitles from: {ass_burn_path}")
        if convert_to_hdr_vpp: cmd.extend(["--vpp-ngx-truehdr"]); logging.info("Applying --vpp-ngx-truehdr.")
        return cmd

    def encode_single_file_logic(self, file_path):
        logging.info(f"--- Processing: {os.path.basename(file_path)} ---")
        current_file_options = self.file_options.get(file_path, self._get_default_file_options())
        final_video_width, final_video_height = self.compute_final_resolution(file_path)
        if final_video_width is None: logging.error(f"No target dimensions for {file_path}. Skipping."); return

        output_base_name, _ = os.path.splitext(os.path.basename(file_path))
        res_folder = current_file_options.get("resolution", "original")
        output_dir = os.path.join(os.path.dirname(file_path), res_folder); os.makedirs(output_dir, exist_ok=True)

        selected_sub_to_burn = next((s for s in self.subtitles_by_file.get(file_path,[]) if s.get("selected_for_burn")), None)
        ass_burn_path_for_nvencc = None
        if selected_sub_to_burn:
            logging.info(f"Selected sub: {selected_sub_to_burn['description']}")
            sub_type = selected_sub_to_burn["type"]
            s_id = selected_sub_to_burn["track_id_for_map"] if sub_type=="embedded" else os.path.splitext(os.path.basename(selected_sub_to_burn["external_path"]))[0]
            s_id_part = "".join(c for c in s_id if c.isalnum() or c in ('_','-')).strip()[:20]
            sidecar_ass = os.path.join(output_dir, f"{output_base_name}_sub_{s_id_part}.ass")
            sidecar_srt = os.path.join(output_dir, f"{output_base_name}_sub_{s_id_part}.srt")
            if sub_type == "embedded":
                self.extract_embedded_subtitle_to_ass(file_path, sidecar_ass, selected_sub_to_burn['track_id_for_map'], final_video_width, final_video_height, current_file_options)
                self.extract_subtitle_to_srt(file_path, sidecar_srt, sub_track_id_for_map=selected_sub_to_burn['track_id_for_map'])
            else: # External
                self.extract_external_srt_to_ass(selected_sub_to_burn["external_path"], sidecar_ass, final_video_width, final_video_height, current_file_options)
                self.extract_subtitle_to_srt(selected_sub_to_burn["external_path"], sidecar_srt)
            if os.path.exists(sidecar_ass): ass_burn_path_for_nvencc = sidecar_ass
            else: logging.warning(f"Sidecar ASS ({sidecar_ass}) not created. Cannot burn.")
        else: logging.info(f"No subtitle selected for burning for {os.path.basename(file_path)}.")

        encoded_file, _, _ = self.build_nvenc_command_and_run(file_path, ass_burn_path=ass_burn_path_for_nvencc)
        if encoded_file: logging.info(f"Successfully processed {os.path.basename(file_path)} -> {encoded_file}")
        else: logging.error(f"Processing FAILED for {os.path.basename(file_path)}")
        logging.info(f"--- Finished: {os.path.basename(file_path)} ---")


    def apply_hdr_settings_mkvmerge(self, temp_output_file, final_target_output_file):
        if not os.path.exists(temp_output_file): logging.error(f"Temp file {temp_output_file} not found."); return temp_output_file
        os.makedirs(os.path.dirname(final_target_output_file), exist_ok=True)
        cmd = ["mkvmerge", "-o", final_target_output_file, "--colour-matrix", "0:9", "--colour-range", "0:1",
            "--colour-transfer-characteristics", "0:16", "--colour-primaries", "0:9",
            "--max-content-light", "0:1000", "--max-frame-light", "0:300", temp_output_file]
        logging.info(f"Applying HDR metadata with mkvmerge to: {final_target_output_file}")
        try:
            subprocess.run(cmd, check=True, env=env, capture_output=True, text=True, encoding='utf-8')
            logging.info(f"mkvmerge applied HDR metadata."); os.remove(temp_output_file); logging.debug(f"Deleted temp: {temp_output_file}")
            return final_target_output_file
        except subprocess.CalledProcessError as e:
            logging.error(f"Error running mkvmerge for HDR tagging: {e.stderr}")
            try:
                if os.path.exists(final_target_output_file) and final_target_output_file != temp_output_file: os.remove(final_target_output_file)
                if temp_output_file != final_target_output_file: shutil.move(temp_output_file, final_target_output_file)
                logging.warning(f"mkvmerge failed, moved {temp_output_file} to {final_target_output_file} (no HDR tags).")
                return final_target_output_file
            except Exception as e_move: logging.error(f"Could not move {temp_output_file} after mkvmerge fail: {e_move}"); return temp_output_file
        except Exception as e_gen: logging.error(f"General error mkvmerge HDR: {e_gen}"); return temp_output_file


    def compute_crop_value(self, file_path, file_options):
        if not file_options.get("crop", False): return "0,0,0,0"
        input_width = get_input_width(file_path)
        if input_width is None: logging.warning(f"No input width for {file_path}. No crop."); return "0,0,0,0"
        res_setting = file_options.get("resolution", "original")
        if res_setting == "4k": return "528,0,528,0" if input_width >= 3840 else "0,0,0,0"
        elif res_setting == "8k": return "1056,0,1056,0" if input_width >= 7680 else "0,0,0,0"
        return "0,0,0,0"

    def start_processing_and_close_gui(self): # CHANGED: No confirmation, immediate close
        if not self.file_list:
            messagebox.showwarning("No Files", "Please add at least one file to process.")
            return
        
        # REMOVED confirmation dialog
        # if not messagebox.askokcancel("Start Processing?", 
        #                               "The GUI will close and processing will start in the console. Continue?"):
        #     return

        self.root.destroy() 

        logging.info("=== Batch Video Processing Started (Console Mode) ===")
        for i, file_path in enumerate(self.file_list):
            logging.info(f"Processing file {i+1}/{len(self.file_list)}: {os.path.basename(file_path)}")
            try:
                self.encode_single_file_logic(file_path)
            except Exception as e:
                logging.error(f"CRITICAL ERROR processing {os.path.basename(file_path)}: {e}", exc_info=True)
        
        logging.info("=== Batch Video Processing Complete ===")
        print("\nProcessing finished. You can close this console window.")


if __name__ == "__main__":
    root = TkinterDnD.Tk() 
    expanded_files = []
    if len(sys.argv) > 1:
        args_to_expand = sys.argv[1:]
        for arg_pattern in args_to_expand:
            if '*' in arg_pattern or '?' in arg_pattern or '[' in arg_pattern:
                import glob 
                found_files = glob.glob(arg_pattern, recursive=False)
                expanded_files.extend(f for f in found_files if os.path.isfile(f))
            elif os.path.isfile(arg_pattern):
                expanded_files.append(os.path.abspath(arg_pattern))
            elif os.path.isdir(arg_pattern):
                logging.warning(f"Argument '{arg_pattern}' is a directory and will be ignored.")

    app = VideoProcessorApp(root, expanded_files)
    root.mainloop()