
import os
import sys
import subprocess
import cv2
import platform
import json
import tkinter as tk
from tkinter import ttk # Import ttk
from tkinter import filedialog, messagebox
from collections import Counter
from multiprocessing import Pool
import glob

# --- Constants for per-file settings ---
DEFAULT_SETTINGS_PER_FILE = {
    "output_resolution_choice": "No Resize",
    "qvbr_value": "22", # Default, will be overridden by global logic if not set
    "gop_value": "6",
    "fruc_setting": False,
    "denoise_setting": False, # The user's explicit choice for this file
    "artifact_setting": False,
    "crop_w": None, "crop_h": None, "crop_x": None, "crop_y": None,
    "no_crop": False
}


# ---------------------------------------------------------------------
# Step 1: ffprobe-based metadata extraction (Functions unchanged)
# ---------------------------------------------------------------------
def get_video_color_info(video_file):
    cmd = ["ffprobe", "-v", "error", "-show_streams", "-of", "json", video_file]
    try:
        output = subprocess.check_output(
            cmd,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
    except subprocess.CalledProcessError:
        return {
            "color_range": None, "color_primaries": None, "color_transfer": None,
            "color_space": None, "mastering_display_metadata": None, "max_cll": None
        }
    data = json.loads(output)
    streams = data.get("streams", [])
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    if not video_stream:
        return {
            "color_range": None, "color_primaries": None, "color_transfer": None,
            "color_space": None, "mastering_display_metadata": None, "max_cll": None
        }
    
    mastering_display_metadata, max_cll = None, None
    if "side_data_list" in video_stream:
        for side_data in video_stream["side_data_list"]:
            side_type = side_data.get("side_data_type", "")
            if side_type == "Mastering display metadata":
                mastering_display_metadata = side_data
            elif side_type == "Content light level metadata":
                max_content = side_data.get("max_content")
                max_average = side_data.get("max_average")
                if max_content or max_average:
                    vals = [str(v) for v in [max_content, max_average] if v is not None]
                    max_cll = ",".join(vals)
    return {
        "color_range": video_stream.get("color_range"),
        "color_primaries": video_stream.get("color_primaries"),
        "color_transfer": video_stream.get("color_transfer"),
        "color_space": video_stream.get("color_space"),
        "mastering_display_metadata": mastering_display_metadata,
        "max_cll": max_cll
    }

def run_ffprobe_for_audio_streams(video_file):
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "a",
        "-show_entries", "stream=index,codec_name,channels:stream_tags=language",
        "-of", "json", video_file
    ]
    try:
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
    except subprocess.CalledProcessError: return []
    data = json.loads(output)
    audio_info = []
    for i, s in enumerate(data.get("streams", []), start=1):
        audio_info.append({
            "stream_index": s.get("index"), "codec": s.get("codec_name"),
            "language": s.get("tags", {}).get("language"), "channels": s.get("channels", 0),
            "track_number": i # GUI Track number
        })
    return audio_info

def get_video_resolution(video_file):
    cap = cv2.VideoCapture(video_file)
    if not cap.isOpened(): print(f"Unable to open video file: {video_file}"); return None, None
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    return height, width

def get_video_duration(video_file):
    cap = cv2.VideoCapture(video_file)
    if not cap.isOpened(): print(f"Unable to open video file: {video_file}"); return None
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    cap.release()
    return (frame_count / fps) if fps else None

# ---------------------------------------------------------------------
# Step 2: Automatic Crop Detection (Function unchanged)
# ---------------------------------------------------------------------
def get_crop_parameters(video_file, input_width, input_height, limit_value):
    print(f"Detecting optimal crop parameters for {os.path.basename(video_file)}...")
    duration = get_video_duration(video_file)
    if duration is None or duration < 1:
        print("Unable to determine video duration or video is too short.")
        return input_width, input_height, 0, 0 
    round_value = "2"; sample_interval = 300
    num_samples = max(12, min(72, int(duration // sample_interval)))
    if num_samples < 12: num_samples = 12
    start_offset = min(300, duration * 0.05)
    interval = (duration - start_offset) / num_samples if duration > start_offset else duration / num_samples
    crop_values = []
    for i in range(num_samples):
        start_time = start_offset + i * interval if duration > start_offset else i * interval
        if start_time >= duration: start_time = duration - 1
        if num_samples > 1 : print(f"  Analyzing {os.path.basename(video_file)} frame at {int(start_time)}s ({i+1}/{num_samples})...")
        else: print(f"  Analyzing {os.path.basename(video_file)} frame at {int(start_time)}s...")
        command = ["ffmpeg", "-ss", str(int(start_time)), "-i", video_file, "-vframes", "3", 
                   "-vf", f"cropdetect={limit_value}:{round_value}:0", "-f", "null", "-", 
                   "-hide_banner", "-loglevel", "verbose"]
        try:
            process = subprocess.Popen(command, stderr=subprocess.PIPE, stdout=subprocess.PIPE, 
                                     text=True, encoding='utf-8', errors='replace')
            stdout, stderr = process.communicate()
            ffmpeg_output = (stdout or '') + (stderr or '')
            for line in ffmpeg_output.split('\n'):
                if 'crop=' in line:
                    crop_str = line[line.index('crop=')+5:].strip()
                    crop_values.append(crop_str)
        except Exception as e: print(f"Error while running cropdetect at {int(start_time)}s: {e}")
    if crop_values:
        try:
            w, h, x, y = [int(v) for v in Counter(crop_values).most_common(1)[0][0].split(':')]
            print(f"  Optimal crop for {os.path.basename(video_file)}: W={w}, H={h}, X={x}, Y={y}")
        except: w, h, x, y = input_width, input_height, 0, 0; print(f"  Invalid crop. Using full frame.")
    else: w, h, x, y = input_width, input_height, 0, 0; print(f"  No crop found. Using full frame.")
    return w, h, x, y


# ---------------------------------------------------------------------
# Step 3: Basic Tkinter GUI for user settings
# ---------------------------------------------------------------------
def launch_gui(initial_file_list, initial_file_settings_map, audio_streams_first_file, default_qvbr_global, default_hdr_global): # Renamed global defaults
    root = tk.Tk()
    root.title("Video Processing Settings")
    file_settings_map = initial_file_settings_map # This is the live map
    
    # --- Store references to GUI control variables ---
    # These will be updated based on single or multi-selection
    gui_vars = { 
        "no_crop": tk.BooleanVar(),
        "output_resolution_choice": tk.StringVar(),
        "qvbr_value": tk.StringVar(),
        "gop_value": tk.StringVar(),
        "fruc_setting": tk.BooleanVar(),
        "denoise_setting": tk.BooleanVar(), # Tracks user's *choice* for denoise
        "artifact_setting": tk.BooleanVar()
    }
    # Global (not per-file) settings
    decoding_mode_global = tk.StringVar(value="Hardware")
    hdr_enable_global_var = tk.BooleanVar(value=default_hdr_global) # Global HDR conversion toggle
    sleep_enable_global = tk.BooleanVar(value=False)
    max_processes_global_str_var = tk.StringVar(value="1")

    # Variables for crop entries (always reflect primary selected file, or blank if multi-select and different)
    crop_w_display_var = tk.StringVar(value="0") 
    crop_h_display_var = tk.StringVar(value="0") 
    crop_x_display_var = tk.StringVar(value="0") 
    crop_y_display_var = tk.StringVar(value="0") 
    
    current_primary_selected_file_path = None # The file whose details populate non-batch edit fields
    current_input_width_primary = 0 # For the primary selected file
    current_input_height_primary = 0

    screen_width = root.winfo_screenwidth(); screen_height = root.winfo_screenheight()
    main_frame = tk.Frame(root); main_frame.pack(fill='both', expand=True)
    canvas = tk.Canvas(main_frame); canvas.pack(side='left', fill='both', expand=True)
    scrollbar_y_main = tk.Scrollbar(main_frame, orient='vertical', command=canvas.yview); scrollbar_y_main.pack(side='right', fill='y')
    canvas.configure(yscrollcommand=scrollbar_y_main.set)
    inner_frame = tk.Frame(canvas)
    canvas.create_window((0, 0), window=inner_frame, anchor='nw')

    def _on_mousewheel(event):
        delta_scroll = -1 * (event.delta // 120) if platform.system() in ['Windows', 'Linux'] else -1 * event.delta
        canvas.yview_scroll(delta_scroll, "units")
    canvas.bind("<MouseWheel>", _on_mousewheel)
    inner_frame.bind("<MouseWheel>", _on_mousewheel)
    def _configure_event(event): canvas.configure(scrollregion=canvas.bbox("all"))
    inner_frame.bind("<Configure>", _configure_event)

    metadata_text_widget = None 
    audio_vars, convert_vars = [], []
    file_treeview = None 
    nvvfx_denoise_checkbox_widget = None # Store ref to enable/disable

    MIXED_VALUE_DISPLAY = "---" # For Entry fields and OptionMenu if values are mixed

    # --- Treeview Column Definitions ---
    # New columns for per-file settings will be added here
    TREE_COLUMNS = {
        "filename": {"text": "File Name", "width": 220, "stretch": tk.YES},
        "output_resolution_choice": {"text": "Out Res", "width": 80, "stretch": tk.NO, "anchor": "center"},
        "no_crop": {"text": "NoCrop", "width": 60, "stretch": tk.NO, "anchor": "center"},
        "crop_w": {"text": "Cr W", "width": 50, "stretch": tk.NO, "anchor": "center"},
        "crop_h": {"text": "Cr H", "width": 50, "stretch": tk.NO, "anchor": "center"},
        "crop_x": {"text": "Cr X", "width": 50, "stretch": tk.NO, "anchor": "center"},
        "crop_y": {"text": "Cr Y", "width": 50, "stretch": tk.NO, "anchor": "center"},
        "qvbr_value": {"text": "QVBR", "width": 50, "stretch": tk.NO, "anchor": "center"},
        "gop_value": {"text": "GOP", "width": 40, "stretch": tk.NO, "anchor": "center"},
        "fruc_setting": {"text": "FRUC", "width": 50, "stretch": tk.NO, "anchor": "center"},
        "denoise_setting": {"text": "Denoise", "width": 60, "stretch": tk.NO, "anchor": "center"},
        "artifact_setting": {"text": "ArtifactR", "width": 70, "stretch": tk.NO, "anchor": "center"},
    }


    def _get_treeview_values_for_file(file_path):
        """Helper to get all display values for a treeview row for a given file."""
        config = file_settings_map.get(file_path, {})
        values = []
        for col_id in TREE_COLUMNS.keys():
            if col_id == "filename":
                values.append(os.path.basename(file_path))
            elif col_id in ["no_crop", "fruc_setting", "denoise_setting", "artifact_setting"]:
                values.append("Yes" if config.get(col_id) else "No")
            elif col_id.startswith("crop_"):
                values.append(str(config.get(col_id)) if config.get(col_id) is not None else "N/A")
            else: # For other settings like qvbr_value, gop_value, output_resolution_choice
                values.append(str(config.get(col_id, DEFAULT_SETTINGS_PER_FILE.get(col_id, "N/A"))))
        return tuple(values)

    def _update_treeview_row(file_path_to_update):
        if file_treeview and file_path_to_update in file_settings_map:
            try:
                if file_treeview.exists(file_path_to_update):
                    file_treeview.item(file_path_to_update, values=_get_treeview_values_for_file(file_path_to_update))
            except tk.TclError: pass # Item might have been deleted

    def _apply_gui_var_to_selected_files(var_key_name, new_value):
        """Applies a new value from a GUI control to all selected files for the given setting key."""
        selected_iids = file_treeview.selection()
        if not selected_iids: return
        
        for iid in selected_iids:
            if iid in file_settings_map:
                file_settings_map[iid][var_key_name] = new_value
                _update_treeview_row(iid)
        # If only one item was selected, it's the primary, so its detail view is already correct.
        # If multiple were selected, and this action makes them uniform, on_file_select will handle
        # the GUI var update next time selection changes or if we explicitly call it.
        # For immediate reflection if >1 selected, we might need to re-evaluate mixed states.
        if len(selected_iids) > 1:
            _update_gui_controls_for_selection(selected_iids)


    # --- Traced GUI variable handlers ---
    def _on_no_crop_var_changed(*args):
        _apply_gui_var_to_selected_files("no_crop", gui_vars["no_crop"].get())
        # Special handling for crop fields if primary selection is affected
        if current_primary_selected_file_path and current_primary_selected_file_path in file_treeview.selection():
            _update_crop_fields_for_primary_selection()

    def _on_resolution_var_changed(*args):
        # Update QVBR recommendation only if a single file is selected, and its the primary one
        # Or, if the change is not to "--- Mixed ---"
        selected_iids = file_treeview.selection()
        new_res_val = gui_vars["output_resolution_choice"].get()

        if new_res_val != MIXED_VALUE_DISPLAY:
            _apply_gui_var_to_selected_files("output_resolution_choice", new_res_val)
            
            # QVBR recommendation logic (applies to the QVBR entry field)
            if len(selected_iids) == 1 and selected_iids[0] == current_primary_selected_file_path:
                if new_res_val in resolution_map_config: # resolution_map_config is the global one
                    recommended_qvbr = resolution_map_config[new_res_val][2]
                    if recommended_qvbr is not None:
                        # This updates the GUI qvbr field. If user wants this new QVBR for selected files,
                        # they'd confirm by editing/focus-out on qvbr field.
                        gui_vars["qvbr_value"].set(recommended_qvbr) 
                        # And apply it to the primary selected file's map entry immediately
                        if current_primary_selected_file_path in file_settings_map:
                             file_settings_map[current_primary_selected_file_path]["qvbr_value"] = recommended_qvbr
                             _update_treeview_row(current_primary_selected_file_path)


    def _on_qvbr_var_changed(*args):
        val = gui_vars["qvbr_value"].get()
        if val != MIXED_VALUE_DISPLAY: _apply_gui_var_to_selected_files("qvbr_value", val)

    def _on_gop_var_changed(*args):
        val = gui_vars["gop_value"].get()
        if val != MIXED_VALUE_DISPLAY: _apply_gui_var_to_selected_files("gop_value", val)

    def _on_fruc_var_changed(*args):
        _apply_gui_var_to_selected_files("fruc_setting", gui_vars["fruc_setting"].get())

    def _on_denoise_var_changed(*args):
        _apply_gui_var_to_selected_files("denoise_setting", gui_vars["denoise_setting"].get())
        # Update denoise checkbox enabled state if primary is selected
        if current_primary_selected_file_path and current_primary_selected_file_path in file_treeview.selection():
             _update_denoise_checkbox_state(file_settings_map[current_primary_selected_file_path])


    def _on_artifact_var_changed(*args):
        _apply_gui_var_to_selected_files("artifact_setting", gui_vars["artifact_setting"].get())

    # Attach traces
    gui_vars["no_crop"].trace_add("write", _on_no_crop_var_changed)
    gui_vars["output_resolution_choice"].trace_add("write", _on_resolution_var_changed)
    gui_vars["qvbr_value"].trace_add("write", _on_qvbr_var_changed) # Consider on focus-out for Entries
    gui_vars["gop_value"].trace_add("write", _on_gop_var_changed)   # Consider on focus-out
    gui_vars["fruc_setting"].trace_add("write", _on_fruc_var_changed)
    gui_vars["denoise_setting"].trace_add("write", _on_denoise_var_changed)
    gui_vars["artifact_setting"].trace_add("write", _on_artifact_var_changed)


    def _update_crop_fields_for_primary_selection():
        """Updates the W/H/X/Y crop_display_vars based on current_primary_selected_file_path."""
        nonlocal crop_w_display_var, crop_h_display_var, crop_x_display_var, crop_y_display_var, \
                 current_input_width_primary, current_input_height_primary, \
                 width_entry_widget, height_entry_widget, x_offset_entry_widget, y_offset_entry_widget # Entry widgets

        if not current_primary_selected_file_path or current_primary_selected_file_path not in file_settings_map:
            # No primary selection or data missing, clear and disable crop entries
            crop_w_display_var.set("0"); crop_h_display_var.set("0")
            crop_x_display_var.set("0"); crop_y_display_var.set("0")
            for entry in [width_entry_widget, height_entry_widget, x_offset_entry_widget, y_offset_entry_widget]:
                entry.config(state='disabled')
            return

        config = file_settings_map[current_primary_selected_file_path]
        current_input_width_primary = config['resolution_w'] # Update these for primary
        current_input_height_primary = config['resolution_h']

        is_no_crop_for_primary = config.get("no_crop", False)
        
        if is_no_crop_for_primary:
            crop_w_display_var.set(str(current_input_width_primary))
            crop_h_display_var.set(str(current_input_height_primary))
            crop_x_display_var.set("0")
            crop_y_display_var.set("0")
            for entry in [width_entry_widget, height_entry_widget, x_offset_entry_widget, y_offset_entry_widget]:
                entry.config(state='disabled')
        else:
            crop_w_display_var.set(str(config['crop_w']) if config['crop_w'] is not None else str(current_input_width_primary))
            crop_h_display_var.set(str(config['crop_h']) if config['crop_h'] is not None else str(current_input_height_primary))
            crop_x_display_var.set(str(config['crop_x']) if config['crop_x'] is not None else "0")
            crop_y_display_var.set(str(config['crop_y']) if config['crop_y'] is not None else "0")
            for entry in [width_entry_widget, height_entry_widget, x_offset_entry_widget, y_offset_entry_widget]:
                entry.config(state='normal')
    
    def _update_denoise_checkbox_state(primary_file_config):
        """Updates the enabled state of the nvvfx_denoise_checkbox_widget based on primary file's resolution."""
        nonlocal nvvfx_denoise_checkbox_widget
        if not nvvfx_denoise_checkbox_widget: return

        # Denoise is only applicable if resolution is < 1080p
        applicable = not (primary_file_config['resolution_h'] >= 1080 and primary_file_config['resolution_w'] >= 1920)
        nvvfx_denoise_checkbox_widget.config(state='normal' if applicable else 'disabled')
        if not applicable: # If not applicable, ensure the user's choice (denoise_setting) for this file is off
            gui_vars["denoise_setting"].set(False) 
            # Note: This will trigger its trace, which will update file_settings_map.

    def _update_gui_controls_for_selection(selected_iids):
        """Updates all GUI controls based on the current selection (single or multiple)."""
        nonlocal current_primary_selected_file_path, current_input_width_primary, current_input_height_primary
        
        if not selected_iids: # No selection
            current_primary_selected_file_path = None
            for key, var in gui_vars.items():
                if isinstance(var, tk.BooleanVar): var.set(False)
                else: var.set("") # Clear StringVars
            update_metadata_display(None)
            _update_crop_fields_for_primary_selection() # Will clear and disable
            if nvvfx_denoise_checkbox_widget: nvvfx_denoise_checkbox_widget.config(state='disabled')
            return

        is_single_selection = len(selected_iids) == 1
        
        # Set primary selected file for detailed views (metadata, crop entries)
        current_primary_selected_file_path = selected_iids[0]
        primary_config = file_settings_map.get(current_primary_selected_file_path, {})
        update_metadata_display(current_primary_selected_file_path)
        _update_crop_fields_for_primary_selection() # Updates crop display vars and entry states
        if primary_config: _update_denoise_checkbox_state(primary_config)


        # Update per-file GUI controls (Checkboxes, OptionMenu, Entries for QVBR/GOP)
        for key, var_control in gui_vars.items():
            is_boolean_var = isinstance(var_control, tk.BooleanVar)
            first_val = file_settings_map[selected_iids[0]].get(key)
            
            if is_single_selection:
                var_control.set(first_val if first_val is not None else DEFAULT_SETTINGS_PER_FILE.get(key))
            else: # Multiple items selected
                all_same = True
                for iid in selected_iids[1:]:
                    if file_settings_map[iid].get(key) != first_val:
                        all_same = False
                        break
                
                if all_same:
                    var_control.set(first_val if first_val is not None else DEFAULT_SETTINGS_PER_FILE.get(key))
                else: # Mixed values
                    if is_boolean_var: var_control.set(False) # Or use tristate if available/desired
                    else: var_control.set(MIXED_VALUE_DISPLAY)
    
    def on_treeview_select(event):
        selected_iids = file_treeview.selection()
        _update_gui_controls_for_selection(selected_iids)

    # File Frame and Treeview
    file_frame = tk.Frame(inner_frame)
    file_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
    file_frame.columnconfigure(0, weight=1); file_frame.rowconfigure(0, weight=1)

    file_treeview = ttk.Treeview(file_frame, columns=list(TREE_COLUMNS.keys()), show="headings", selectmode="extended", height=10)
    for col_id, col_props in TREE_COLUMNS.items():
        file_treeview.heading(col_id, text=col_props["text"])
        file_treeview.column(col_id, width=col_props["width"], minwidth=col_props.get("minwidth", 40), 
                              stretch=col_props["stretch"], anchor=col_props.get("anchor", "w"))

    for f_path in initial_file_list: # Populate treeview
        if f_path in initial_file_settings_map:
            file_treeview.insert("", "end", iid=f_path, values=_get_treeview_values_for_file(f_path))

    tree_scrollbar_y = ttk.Scrollbar(file_frame, orient="vertical", command=file_treeview.yview)
    tree_scrollbar_x = ttk.Scrollbar(file_frame, orient="horizontal", command=file_treeview.xview)
    file_treeview.configure(yscrollcommand=tree_scrollbar_y.set, xscrollcommand=tree_scrollbar_x.set)
    file_treeview.grid(row=0, column=0, sticky="nsew")
    tree_scrollbar_y.grid(row=0, column=1, sticky="ns")
    tree_scrollbar_x.grid(row=1, column=0, sticky="ew")
    file_treeview.bind("<<TreeviewSelect>>", on_treeview_select)
    
    # --- Crop display/edit field traces (for primary selection) ---
    def _on_crop_display_var_changed(var_name, *args):
        # This is called when user types into crop_w/h/x/y fields
        if current_primary_selected_file_path and current_primary_selected_file_path in file_settings_map:
            # Only apply if not "No Crop" for the primary file
            if not file_settings_map[current_primary_selected_file_path].get("no_crop"):
                try:
                    val = int(globals()[var_name].get()) # e.g. crop_w_display_var.get()
                    # Determine which crop setting this corresponds to ('crop_w', 'crop_h', etc.)
                    map_key = var_name.replace('_display_var', '') # e.g. "crop_w"
                    
                    # Update map for primary file
                    file_settings_map[current_primary_selected_file_path][map_key] = val - (val % 2) # ensure even
                    # Refresh the display var in case mod2 changed it
                    globals()[var_name].set(str(file_settings_map[current_primary_selected_file_path][map_key]))
                    
                    _update_treeview_row(current_primary_selected_file_path)
                except ValueError:
                    pass # Ignore non-integer input for now, or show error
    
    crop_w_display_var.trace_add("write", lambda n,i,m,v="crop_w_display_var": _on_crop_display_var_changed(v))
    crop_h_display_var.trace_add("write", lambda n,i,m,v="crop_h_display_var": _on_crop_display_var_changed(v))
    crop_x_display_var.trace_add("write", lambda n,i,m,v="crop_x_display_var": _on_crop_display_var_changed(v))
    crop_y_display_var.trace_add("write", lambda n,i,m,v="crop_y_display_var": _on_crop_display_var_changed(v))


    # File Control Buttons
    file_controls_frame = tk.Frame(file_frame) 
    file_controls_frame.grid(row=0, column=2, rowspan=2, padx=5, sticky="ns") 

    def add_files_gui_handler():
        files_to_add = filedialog.askopenfilenames(filetypes=[("Video Files", "*.mp4 *.mkv *.avi *.mov")])
        newly_added_iids = []
        for file_path in files_to_add:
            abs_file_path = os.path.abspath(file_path)
            if not file_treeview.exists(abs_file_path):
                h_res, w_res = get_video_resolution(abs_file_path)
                if h_res is None or w_res is None: continue # Error already printed
                
                color_data = get_video_color_info(abs_file_path)
                cp = (color_data["color_primaries"] or "").lower(); cs = (color_data["color_space"] or "").lower()
                is_hdr = cp in ["bt2020", "2020"] or cs in ["bt2020nc", "2020nc"]
                limit_val = "128" if is_hdr else "24"

                # Initialize with global defaults and per-file fixed info
                file_settings_map[abs_file_path] = {
                    **DEFAULT_SETTINGS_PER_FILE, # Start with defaults
                    "resolution_w": w_res, "resolution_h": h_res,
                    "is_hdr_content": is_hdr,
                    "limit_value_for_cropdetect": limit_val,
                    # Override QVBR with smart default based on this file's resolution
                    "qvbr_value": ("44" if w_res >= 7680 or h_res >= 4320 else \
                                   "33" if w_res >= 3840 or h_res >= 2160 else \
                                   DEFAULT_SETTINGS_PER_FILE["qvbr_value"])
                }
                file_treeview.insert("", "end", iid=abs_file_path, values=_get_treeview_values_for_file(abs_file_path))
                newly_added_iids.append(abs_file_path)
        
        if newly_added_iids: # Select the first newly added file
            file_treeview.selection_set(newly_added_iids[0])
            file_treeview.focus(newly_added_iids[0])


    tk.Button(file_controls_frame, text="Add Files", command=add_files_gui_handler).pack(fill='x', pady=(0,5))
    tk.Button(file_controls_frame, text="Clear List", command=lambda: (
        [file_treeview.delete(iid) for iid in file_treeview.get_children()],
        file_settings_map.clear(), _update_gui_controls_for_selection([]))).pack(fill='x', pady=(0,5)) # Pass empty list to clear
    
    def move_item_handler(direction):
        selected_iids = file_treeview.selection()
        if not selected_iids: return
        for iid_to_move in selected_iids: # Move all selected, one by one
            current_index = file_treeview.index(iid_to_move)
            target_index = current_index - 1 if direction == "up" else current_index + 1
            file_treeview.move(iid_to_move, file_treeview.parent(iid_to_move), target_index)
        file_treeview.selection_set(selected_iids) # Re-select them
        if selected_iids: file_treeview.focus(selected_iids[0]) # Focus on the first one

    tk.Button(file_controls_frame, text="Move Up", command=lambda: move_item_handler("up")).pack(fill='x', pady=(0,5))
    tk.Button(file_controls_frame, text="Move Down", command=lambda: move_item_handler("down")).pack(fill='x', pady=(0,5))
    
    def delete_selected_gui_handler():
        selected_iids = file_treeview.selection()
        if not selected_iids: return
        for iid in selected_iids:
            if file_treeview.exists(iid): file_treeview.delete(iid)
            if iid in file_settings_map: del file_settings_map[iid]
        _update_gui_controls_for_selection(file_treeview.selection()) # Update based on new (or no) selection

    tk.Button(file_controls_frame, text="Delete Selected", command=delete_selected_gui_handler).pack(fill='x', pady=(0,5))

    def calculate_crop_for_all_handler():
        all_file_iids = file_treeview.get_children("")
        if not all_file_iids: messagebox.showinfo("Info", "No files."); return
        print("\nStarting batch crop calculation..."); root.update_idletasks()
        for i, file_path in enumerate(all_file_iids):
            if file_path not in file_settings_map: continue
            config = file_settings_map[file_path]
            print(f"Processing ({i+1}/{len(all_file_iids)}): {os.path.basename(file_path)}"); root.update_idletasks()
            w_c, h_c, x_c, y_c = get_crop_parameters(file_path, config['resolution_w'], config['resolution_h'], config['limit_value_for_cropdetect'])
            config.update({'crop_w': w_c, 'crop_h': h_c, 'crop_x': x_c, 'crop_y': y_c, 'no_crop': False})
            _update_treeview_row(file_path)
            if file_path == current_primary_selected_file_path: # Update detailed view if primary
                gui_vars["no_crop"].set(False) 
                _update_crop_fields_for_primary_selection()
        messagebox.showinfo("Batch Crop", "Finished for all files."); print("Batch crop calculation finished.\n")

    tk.Button(file_controls_frame, text="Calc Crop All", command=calculate_crop_for_all_handler).pack(fill='x', pady=(10,5))

    # Metadata display
    metadata_frame = tk.LabelFrame(inner_frame, text="Color Metadata (Primary Selected File)")
    metadata_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
    metadata_frame.columnconfigure(0, weight=1); metadata_frame.rowconfigure(0, weight=1)
    metadata_text_widget = tk.Text(metadata_frame, height=5, wrap="word", state='disabled', bg="#f0f0f0") # Reduced height
    metadata_text_widget.grid(row=0, column=0, sticky="nsew")

    # --- Options Section (Global and Per-File when single selected) ---
    options_frame = tk.LabelFrame(inner_frame, text="Settings (Applied to Selected Files)")
    options_frame.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")
    options_frame.columnconfigure(1, weight=1) # Allow entries to expand

    # Global settings (placed separately or clearly marked if within this frame)
    decode_mode_frame = tk.LabelFrame(options_frame, text="Global: Decoding Mode")
    decode_mode_frame.grid(row=0, column=0, padx=5, pady=2, sticky="ew", columnspan=2)
    tk.Radiobutton(decode_mode_frame, text="Hardware", variable=decoding_mode_global, value="Hardware").pack(side="left", padx=5)
    tk.Radiobutton(decode_mode_frame, text="Software", variable=decoding_mode_global, value="Software").pack(side="left", padx=5)

    tk.Checkbutton(options_frame, text="Global: Enable HDR Conversion", variable=hdr_enable_global_var).grid(row=1, column=0, sticky="w", padx=5, pady=2)
    
    mp_frame = tk.Frame(options_frame)
    mp_frame.grid(row=1, column=1, sticky="e", padx=5, pady=2)
    tk.Label(mp_frame, text="Global: Max Proc:").pack(side="left")
    tk.Entry(mp_frame, textvariable=max_processes_global_str_var, width=3).pack(side="left")

    # Per-file settings controls
    tk.Label(options_frame, text="Output Resolution:").grid(row=2, column=0, sticky="w", padx=5, pady=2)
    # Add MIXED_VALUE_DISPLAY to the resolution choices for the OptionMenu
    resolution_map_config = { # This is the original map used for configuring the OptionMenu
        "No Resize": (None, None, None), "HD 1080p":  (1920, 1080, "20"),
        "4K 2160p":  (3840, 2160, "30"), "8K 4320p":  (7680, 4320, "40")
    }
    option_menu_choices = [MIXED_VALUE_DISPLAY] + list(resolution_map_config.keys())
    tk.OptionMenu(options_frame, gui_vars["output_resolution_choice"], *option_menu_choices).grid(row=2, column=1, sticky="ew", padx=5, pady=2)

    tk.Label(options_frame, text="Target QVBR:").grid(row=3, column=0, sticky="w", padx=5, pady=2)
    tk.Entry(options_frame, textvariable=gui_vars["qvbr_value"], width=7).grid(row=3, column=1, sticky="ew", padx=5, pady=2)
    
    tk.Label(options_frame, text="GOP Length:").grid(row=4, column=0, sticky="w", padx=5, pady=2)
    tk.Entry(options_frame, textvariable=gui_vars["gop_value"], width=7).grid(row=4, column=1, sticky="ew", padx=5, pady=2)

    tk.Checkbutton(options_frame, text="Enable FRUC (fps=60)", variable=gui_vars["fruc_setting"]).grid(row=5, column=0, sticky="w", padx=5, pady=2)
    
    # Store ref to denoise checkbox to enable/disable it
    nvvfx_denoise_checkbox_widget = tk.Checkbutton(options_frame, text="Enable Denoising (NVVFX)", variable=gui_vars["denoise_setting"])
    nvvfx_denoise_checkbox_widget.grid(row=5, column=1, sticky="w", padx=5, pady=2)
    
    tk.Checkbutton(options_frame, text="Enable Artifact Reduction (NVVFX)", variable=gui_vars["artifact_setting"]).grid(row=6, column=0, sticky="w", padx=5, pady=2)


    # Crop Parameters (for primary selected file only)
    crop_frame = tk.LabelFrame(inner_frame, text="Crop Parameters (Primary Selected File)")
    crop_frame.grid(row=3, column=0, padx=10, pady=10, sticky="nsew")
    crop_frame.columnconfigure(1, weight=1)
    tk.Label(crop_frame, text="Width:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
    width_entry_widget = tk.Entry(crop_frame, textvariable=crop_w_display_var) # Store ref
    width_entry_widget.grid(row=0, column=1, sticky="ew", padx=5, pady=2)
    tk.Label(crop_frame, text="Height:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
    height_entry_widget = tk.Entry(crop_frame, textvariable=crop_h_display_var) # Store ref
    height_entry_widget.grid(row=1, column=1, sticky="ew", padx=5, pady=2)
    tk.Label(crop_frame, text="X Offset:").grid(row=2, column=0, sticky="w", padx=5, pady=2)
    x_offset_entry_widget = tk.Entry(crop_frame, textvariable=crop_x_display_var) # Store ref
    x_offset_entry_widget.grid(row=2, column=1, sticky="ew", padx=5, pady=2)
    tk.Label(crop_frame, text="Y Offset:").grid(row=3, column=0, sticky="w", padx=5, pady=2)
    y_offset_entry_widget = tk.Entry(crop_frame, textvariable=crop_y_display_var) # Store ref
    y_offset_entry_widget.grid(row=3, column=1, sticky="ew", padx=5, pady=2)

    def calculate_crop_for_selected_handler(): # Renamed
        selected_iids = file_treeview.selection()
        if not selected_iids: messagebox.showinfo("Info", "Select file(s) first."); return
        
        print(f"\nCalculating crop for {len(selected_iids)} selected file(s)..."); root.update_idletasks()
        for i, file_path in enumerate(selected_iids):
            if file_path not in file_settings_map: continue
            config = file_settings_map[file_path]
            print(f"  Processing ({i+1}/{len(selected_iids)}): {os.path.basename(file_path)}"); root.update_idletasks()
            w_c, h_c, x_c, y_c = get_crop_parameters(file_path, config['resolution_w'], config['resolution_h'], config['limit_value_for_cropdetect'])
            config.update({'crop_w': w_c, 'crop_h': h_c, 'crop_x': x_c, 'crop_y': y_c, 'no_crop': False})
            _update_treeview_row(file_path)
            if file_path == current_primary_selected_file_path: # Update detail view if primary
                gui_vars["no_crop"].set(False)
                _update_crop_fields_for_primary_selection()
        messagebox.showinfo("Crop Calc", f"Finished for {len(selected_iids)} file(s)."); print("Selected crop calculation finished.\n")

    tk.Button(crop_frame, text="Calculate Crop for Selected", command=calculate_crop_for_selected_handler).grid(row=4, column=0, columnspan=2, pady=(10,0), sticky="ew", padx=5)
    
    # "No Crop" checkbox - now uses gui_vars["no_crop"] which is multi-select aware
    tk.Checkbutton(crop_frame, text="No Crop (for selected files)", variable=gui_vars["no_crop"]).grid(row=5, column=0, columnspan=2, pady=(5, 0), sticky="w", padx=5)


    # Audio Tracks (Global based on first file)
    audio_tracks_frame = tk.LabelFrame(inner_frame, text="Audio Tracks (From First File, Global Setting)")
    audio_tracks_frame.grid(row=4, column=0, padx=10, pady=10, sticky="nsew")
    # ... (Audio track setup unchanged) ...
    audio_tracks_frame.columnconfigure(0, weight=1); audio_tracks_frame.columnconfigure(1, weight=1)
    button_frame = tk.Frame(audio_tracks_frame); button_frame.grid(row=0, column=0, columnspan=2, sticky="n", padx=5, pady=5)
    tk.Button(button_frame, text="Select All", command=lambda: [v.set(True) for v in audio_vars]).pack(side='left', padx=2)
    tk.Button(button_frame, text="Clear All", command=lambda: [v.set(False) for v in audio_vars]).pack(side='left', padx=2)
    tk.Button(button_frame, text="Copy All", command=lambda: [v.set(False) for v in convert_vars]).pack(side='left', padx=2)
    tk.Button(button_frame, text="Convert All", command=lambda: [v.set(True) for v in convert_vars]).pack(side='left', padx=2)
    if audio_streams_first_file:
        for idx, stream in enumerate(audio_streams_first_file, start=1):
            track_frame = tk.Frame(audio_tracks_frame); track_frame.grid(row=idx, column=0, padx=5, pady=2, sticky='e')
            lbl_text = f"Trk {stream['track_number']}: {stream['codec']} ({stream['language'] or 'N/A'}, {stream.get('channels',0)}-ch)"
            tk.Label(track_frame, text=lbl_text, anchor='e').pack(side='left')
            track_var = tk.BooleanVar(value=(stream['language'] == 'eng'))
            tk.Checkbutton(track_frame, variable=track_var).pack(side='right', padx=(5,0))
            audio_vars.append(track_var)
            convert_var = tk.BooleanVar(value=(stream['codec'] != 'ac3'))
            tk.Checkbutton(audio_tracks_frame, text="Convert to AC3", variable=convert_var, anchor='w').grid(row=idx, column=1, padx=5, pady=2, sticky='w')
            convert_vars.append(convert_var)
    else: tk.Label(audio_tracks_frame, text="No audio tracks found in first loaded file.").grid(row=1,column=0,padx=5,pady=5,sticky='w')

    tk.Checkbutton(inner_frame, text="Global: Put Computer to Sleep", variable=sleep_enable_global).grid(row=5, column=0, padx=10, pady=5, sticky="w")

    def start_processing_handler(): # Renamed
        files_to_process_ordered = file_treeview.get_children("")
        if not files_to_process_ordered: messagebox.showerror("Error", "No files."); return

        # Final validation of primary selected file's crop entries if it exists
        if current_primary_selected_file_path:
            try:
                if not file_settings_map[current_primary_selected_file_path].get("no_crop"): # Only validate if not 'no crop'
                    int(crop_w_display_var.get()); int(crop_h_display_var.get());
                    int(crop_x_display_var.get()); int(crop_y_display_var.get())
            except ValueError: messagebox.showerror("Error", f"Invalid crop for {os.path.basename(current_primary_selected_file_path)}."); return

        # Validate all files in the map that are in the processing list
        for f_path in files_to_process_ordered:
            f_config = file_settings_map[f_path]
            if not f_config['no_crop'] and f_config.get('crop_w') is not None:
                # Simplified validation, detailed checks should be where data is set
                if not all(isinstance(f_config.get(k), int) for k in ['crop_w','crop_h','crop_x','crop_y']):
                    messagebox.showerror("Error", f"Corrupt crop data for {os.path.basename(f_path)}."); return
                # Add other critical validations for resolution choice, qvbr, gop, etc. from f_config if needed
                if f_config.get("output_resolution_choice") == MIXED_VALUE_DISPLAY:
                    messagebox.showerror("Error", f"Resolution not set for {os.path.basename(f_path)} (mixed). Please select a resolution."); return
                if f_config.get("qvbr_value") == MIXED_VALUE_DISPLAY or not f_config.get("qvbr_value", "").isdigit():
                    messagebox.showerror("Error", f"QVBR not set or invalid for {os.path.basename(f_path)}."); return
                if f_config.get("gop_value") == MIXED_VALUE_DISPLAY or not f_config.get("gop_value", "").isdigit():
                    messagebox.showerror("Error", f"GOP not set or invalid for {os.path.basename(f_path)}."); return


        selected_audio_tracks_data = [] # Renamed
        if audio_streams_first_file:
            for i, s_audio in enumerate(audio_streams_first_file):
                if audio_vars[i].get():
                    s_copy = s_audio.copy(); s_copy['convert_to_ac3'] = convert_vars[i].get()
                    selected_audio_tracks_data.append(s_copy)
        
        processing_settings_bundle = { # Renamed
            "files": list(files_to_process_ordered), 
            "decode_mode_global": decoding_mode_global.get(), # Pass global
            "hdr_enable_global": hdr_enable_global_var.get(), # Pass global
            "max_processes_global": max_processes_global_str_var.get(), # Pass global
            "file_settings_map": file_settings_map, # This contains all per-file settings
            "audio_tracks_global": selected_audio_tracks_data, # Pass global audio
            "sleep_after_processing_global": sleep_enable_global.get() # Pass global
        }
        root.destroy()
        print("\nSettings collected. Starting processing...\n")
        print(json.dumps({k: v for k, v in processing_settings_bundle.items() if k != "file_settings_map"}, indent=2))
        
        process_batch(processing_settings_bundle["files"], processing_settings_bundle)
        
        if processing_settings_bundle.get("sleep_after_processing_global"):
            print("Putting the computer to sleep...")
            # ... (sleep commands unchanged) ...
            if platform.system() == "Windows": os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
            elif platform.system() == "Linux": os.system("systemctl suspend")
            elif platform.system() == "Darwin": os.system("pmset sleepnow")
            else: print("Sleep command not supported.")

    tk.Button(inner_frame, text="Start Processing", command=start_processing_handler).grid(row=6, column=0, padx=10, pady=10, sticky="ew")
    
    # Initial selection and GUI state update
    if file_treeview.get_children(""): 
        first_iid = file_treeview.get_children("")[0]
        file_treeview.selection_set(first_iid)
        file_treeview.focus(first_iid) 
    else: _update_gui_controls_for_selection([]) # No files, clear/disable GUI

    root.update_idletasks()
    required_width = inner_frame.winfo_reqwidth()
    window_width = min(required_width + 80, screen_width) # Increased padding
    window_height = int(screen_height * 0.85) # Increased height
    root.geometry(f"{window_width}x{window_height}")
    root.mainloop()

# ---------------------------------------------------------------------
# Step 4: The main encode function 
# ---------------------------------------------------------------------
def process_video(file_path, settings_bundle): # Renamed for clarity
    # ... (Output path setup unchanged) ...
    input_dir = os.path.dirname(file_path); file_name = os.path.basename(file_path)
    output_subdir = os.path.join(input_dir, "processed_videos"); os.makedirs(output_subdir, exist_ok=True)
    output_file = os.path.join(output_subdir, os.path.splitext(file_name)[0] + ".mp4")
    log_file = os.path.join(output_subdir, os.path.splitext(file_name)[0] + "_encoding.log")

    # Get settings for THIS file from the map
    current_file_config = settings_bundle["file_settings_map"].get(file_path)
    if not current_file_config: print(f"Error: No settings for {file_path}. Skipping."); return

    input_height = current_file_config['resolution_h']; input_width = current_file_config['resolution_w']
    
    # Use per-file settings from current_file_config where available, else global from settings_bundle
    qvbr_to_use = current_file_config.get("qvbr_value", "25") # Fallback if somehow missing
    gop_to_use = current_file_config.get("gop_value", "6")
    fruc_to_use = current_file_config.get("fruc_setting", False)
    denoise_user_choice = current_file_config.get("denoise_setting", False)
    artifact_to_use = current_file_config.get("artifact_setting", False)
    output_res_choice_this_file = current_file_config.get("output_resolution_choice", "No Resize")

    command = [
        "NVEncC64", "--codec", "av1", "--qvbr", qvbr_to_use, "--preset", "p7",
        "--output-depth", "10", "--gop-len", gop_to_use, "--metadata", "copy",
        # ... (other relatively fixed NVEncC params) ...
        "--chapter-copy", "--key-on-chapter", "--bframes","4", "--tf-level","4", 
        "--split-enc","auto", "--parallel", "auto", "--profile", "high", 
        "--multipass", "2pass-full", "--aq", "--aq-temporal", "--aq-strength", "5", 
        "--lookahead", "32", "-i", file_path, "-o", output_file
    ]
    if settings_bundle["decode_mode_global"] == "Hardware": command.append("--avhw")
    else: command.append("--avsw")

    command.extend(["--colormatrix", "bt2020nc", "--colorprim", "bt2020", "--transfer", "smpte2084"])
    if settings_bundle["hdr_enable_global"]: command.append("--vpp-ngx-truehdr")
    else: command.extend(["--dhdr10-info", "copy", "--dolby-vision-profile", "copy", "--dolby-vision-rpu", "copy"])

    # Crop logic (uses current_file_config directly)
    crop_params_to_use = {}
    if current_file_config.get('no_crop', False):
        crop_params_to_use = {'crop_w': input_width, 'crop_h': input_height, 'crop_x': 0, 'crop_y': 0}
    elif current_file_config.get('crop_w') is not None: 
        crop_params_to_use = {k: current_file_config[k] for k in ['crop_w','crop_h','crop_x','crop_y']}
    else: # Auto-calculate if not set and not 'no_crop'
        w_c, h_c, x_c, y_c = get_crop_parameters(file_path, input_width, input_height, current_file_config['limit_value_for_cropdetect'])
        crop_params_to_use = {'crop_w': w_c, 'crop_h': h_c, 'crop_x': x_c, 'crop_y': y_c}
    
    for k in ['crop_w', 'crop_h', 'crop_x', 'crop_y']: crop_params_to_use[k] -= crop_params_to_use[k] % 2
    left = crop_params_to_use["crop_x"]; top = crop_params_to_use["crop_y"]
    crop_w_val = crop_params_to_use["crop_w"]; crop_h_val = crop_params_to_use["crop_h"]
    if left + crop_w_val > input_width: crop_w_val = input_width - left
    if top + crop_h_val > input_height: crop_h_val = input_height - top
    crop_w_val = max(crop_w_val, 0); crop_h_val = max(crop_h_val, 0)
    right = input_width - (left + crop_w_val); bottom = input_height - (top + crop_h_val)
    right = max(right, 0); bottom = max(bottom, 0)
    if crop_w_val > 0 and crop_h_val > 0 : command.extend(["--crop", f"{left},{top},{right},{bottom}"])
    else: crop_w_val = input_width; crop_h_val = input_height # Reset for scaling if crop invalid

    if fruc_to_use: command.extend(["--vpp-fruc", "fps=60"])
    
    # Denoise: check user's choice for *this file* AND original resolution applicability
    if denoise_user_choice and not (input_height >= 1080 and input_width >= 1920):
        command.append("--vpp-nvvfx-denoise")
    elif denoise_user_choice: print(f"Denoise chosen but skipped for {file_name} (res >= 1080p).")
    
    if artifact_to_use: command.append("--vpp-nvvfx-artifact-reduction")

    # Resolution scaling based on this file's choice
    # resolution_map_config from global scope (defined in launch_gui or could be redefined here)
    # For simplicity, assuming resolution_map_config is accessible or use a local copy.
    # Using the one from launch_gui context as it's more likely to be the source of truth for "No Resize" etc.
    # This part might need `resolution_map_config` to be passed or be global if process_video is truly isolated.
    # For now, assume it's available via settings_bundle or implicitly. Let's use a local copy for robustness.
    local_resolution_map_config = { 
        "No Resize": (None, None, None), "HD 1080p":  (1920, 1080, "20"),
        "4K 2160p":  (3840, 2160, "30"), "8K 4320p":  (7680, 4320, "40")
    }
    if output_res_choice_this_file in local_resolution_map_config:
        target_w_map, target_h_map, _ = local_resolution_map_config[output_res_choice_this_file] # Target H from map
        
        curr_w_after_crop = crop_w_val; curr_h_after_crop = crop_h_val
        if target_h_map is not None and curr_h_after_crop > 0: # If not "No Resize" and valid height
            out_h = target_h_map
            out_w = int(curr_w_after_crop * (out_h / curr_h_after_crop)); out_w -= out_w % 2
            if out_w > 0 and out_h > 0:
                # Only resize if dimensions actually change
                if out_w != curr_w_after_crop or out_h != curr_h_after_crop:
                    algo = "nvvfx-superres,superres-mode=0" if out_w > curr_w_after_crop or out_h > curr_h_after_crop else "bilinear"
                    command.extend(["--vpp-resize", f"algo={algo}", "--output-res", f"{out_w}x{out_h}"])

    # Audio (uses global settings_bundle["audio_tracks_global"])
    audio_tracks_data = settings_bundle["audio_tracks_global"]; copy_tr, conv_tr = [], []
    # ... (Audio command building unchanged) ...
    for s_audio in audio_tracks_data:
        num_str = str(s_audio["stream_index"]) # Use actual stream index from ffprobe
        (conv_tr if s_audio.get("convert_to_ac3") else copy_tr).append(num_str)
    if copy_tr: command.extend(["--audio-copy", ",".join(copy_tr)])
    for num_str in conv_tr:
        command.extend([f"--audio-codec", f"{num_str}?ac3", f"--audio-bitrate", f"{num_str}?640",
                        f"--audio-stream", f"{num_str}?5.1", f"--audio-samplerate", f"{num_str}?48000"]) 

    quoted_command = ' '.join(f'"{arg}"' if ' ' in arg else arg for arg in command)
    print(f"\nProcessing: {file_path}\nNVEncC command:\n{quoted_command}")
    
    # ... (subprocess execution and logging unchanged) ...
    status = "Starting..."; process = None; stdout, stderr = "", ""
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace') 
        stdout, stderr = process.communicate()
        if process.returncode == 0: status = "Success"; print(f"Success: Processed {file_path} -> {output_file}")
        else:
            status = f"Error (code {process.returncode}):\nStdout:\n{stdout}\nStderr:\n{stderr}"
            print(f"Error: Failed {file_path}. Code: {process.returncode}\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}")
    except FileNotFoundError: status = "Error: NVEncC64 not found."; print(status)
    except Exception as e: status = f"Unexpected Error: {e}"; print(f"Unexpected error processing {file_path}: {e}")

    with open(log_file, "w", encoding='utf-8') as log:
        log.write(f"Command:\n{quoted_command}\n\nFile: {file_path}\nOutput: {output_file}\nStatus: {status}\n")
        if "Stdout:" not in status and (stdout or stderr):
             log.write(f"\n--- NVEncC Output ---\nStdout:\n{stdout}\nStderr:\n{stderr}\n")


def process_wrapper(args):
    vf, settings_bundle = args 
    process_video(vf, settings_bundle)

def process_batch(video_files_to_process, settings_bundle): # Renamed
    try: mp = int(settings_bundle.get("max_processes_global", "1")) # Use global
    except ValueError: mp = 1

    valid_tasks = [(vf, settings_bundle) for vf in video_files_to_process if vf in settings_bundle["file_settings_map"]]
    if not valid_tasks: print("No valid tasks for processing."); return

    if mp <= 1:
        for vf, s_dict in valid_tasks: process_video(vf, s_dict) # Pass full bundle
    else: 
        print(f"Using multiprocessing with {mp} processes...")
        with Pool(mp) as p: p.map(process_wrapper, valid_tasks)

# ---------------------------------------------------------------------
# Main Script Logic (Batch + GUI) 
# ---------------------------------------------------------------------
if __name__ == "__main__":
    # ... (File gathering unchanged from previous version) ...
    cli_input_files = []
    if len(sys.argv) > 1:
        for arg_pattern in sys.argv[1:]:
            expanded_cli_files = glob.glob(arg_pattern)
            if not expanded_cli_files: print(f"Warning: CLI pattern '{arg_pattern}' matched no files.")
            cli_input_files.extend(expanded_cli_files)
    cwd = os.getcwd(); print(f"Scanning CWD for videos: {cwd}")
    cwd_found_files = []
    vid_exts = ["*.mp4", "*.mkv", "*.avi", "*.mov", "*.webm", "*.flv", "*.ts", "*.mpg", "*.mpeg"]
    for ext_pattern in vid_exts: cwd_found_files.extend(glob.glob(os.path.join(cwd, ext_pattern)))
    unique_abs_paths = {os.path.abspath(f) for f in cli_input_files + cwd_found_files}
    input_video_files = sorted(list(unique_abs_paths))
    
    master_file_settings_map = {}
    # Global defaults (not per-file initially, but used to seed per-file if needed)
    global_default_hdr_setting, global_default_qvbr_setting = False, "22" # QVBR default for GUI if no files
    first_file_audio_streams_data = [] # Renamed

    if input_video_files:
        print("\nInitial files to load:")
        for f_path in input_video_files:
            print(f"  - {os.path.basename(f_path)} (from: {os.path.dirname(f_path)})")
            h, w = get_video_resolution(f_path)
            if h is None or w is None: print(f"Error: No resolution for {f_path}. Skipped."); continue 

            color_data = get_video_color_info(f_path)
            cp = (color_data["color_primaries"] or "").lower(); cs = (color_data["color_space"] or "").lower()
            is_hdr = cp in ["bt2020", "2020"] or cs in ["bt2020nc", "2020nc"]
            limit_crop_val = "128" if is_hdr else "24" # Renamed

            # Determine smart QVBR default for this specific file
            file_specific_qvbr = "22" # Base default
            if h >= 4320 or w >= 7680: file_specific_qvbr = "44"
            elif h >= 2160 or w >= 3840: file_specific_qvbr = "33"

            master_file_settings_map[f_path] = {
                **DEFAULT_SETTINGS_PER_FILE, # Start with defined defaults
                "resolution_w": w, "resolution_h": h, 
                "is_hdr_content": is_hdr,
                "limit_value_for_cropdetect": limit_crop_val,
                "qvbr_value": file_specific_qvbr # Override QVBR with smart default
            }
        
        if master_file_settings_map: # If any files were successfully processed
            first_valid_path = next(iter(master_file_settings_map))
            first_cfg_data = master_file_settings_map[first_valid_path] # Renamed
            # Set global GUI defaults based on the first successfully loaded file
            global_default_hdr_setting = not first_cfg_data['is_hdr_content'] # Suggest HDR conversion if SDR
            global_default_qvbr_setting = first_cfg_data['qvbr_value'] # Use its smart QVBR
            first_file_audio_streams_data = run_ffprobe_for_audio_streams(first_valid_path)
    
    if not input_video_files: print("No video files found by CLI or in CWD.")

    print("\nLaunching GUI...\n")
    launch_gui(
        list(master_file_settings_map.keys()), master_file_settings_map,          
        first_file_audio_streams_data, global_default_qvbr_setting, global_default_hdr_setting
    )
    print("Processing Complete or GUI closed.")
    if platform.system() == "Windows": os.system("pause")

