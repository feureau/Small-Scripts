

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
    "qvbr_value": "22", 
    "gop_value": "6",
    "fruc_setting": False,
    "denoise_setting": False, 
    "artifact_setting": False,
    "crop_w": None, "crop_h": None, "crop_x": None, "crop_y": None,
    "no_crop": False,
    "audio_tracks_config": [] 
}

ENGLISH_LANG_TAGS = ["eng", "en", "english"] 


# ---------------------------------------------------------------------
# Step 1: ffprobe-based metadata extraction (Functions unchanged)
# ---------------------------------------------------------------------
def get_video_color_info(video_file):
    cmd = ["ffprobe", "-v", "error", "-show_streams", "-of", "json", video_file]
    try:
        output = subprocess.check_output(
            cmd, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace'
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
            if side_type == "Mastering display metadata": mastering_display_metadata = side_data
            elif side_type == "Content light level metadata":
                max_content = side_data.get("max_content"); max_average = side_data.get("max_average")
                if max_content or max_average:
                    vals = [str(v) for v in [max_content, max_average] if v is not None]
                    max_cll = ",".join(vals)
    return {
        "color_range": video_stream.get("color_range"), "color_primaries": video_stream.get("color_primaries"),
        "color_transfer": video_stream.get("color_transfer"), "color_space": video_stream.get("color_space"),
        "mastering_display_metadata": mastering_display_metadata, "max_cll": max_cll
    }

def run_ffprobe_for_audio_streams(video_file):
    cmd = [ "ffprobe", "-v", "error", "-select_streams", "a",
        "-show_entries", "stream=index,codec_name,channels:stream_tags=language", "-of", "json", video_file ]
    try:
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
    except subprocess.CalledProcessError: return []
    data = json.loads(output)
    parsed_audio_info = []
    for i, s_data in enumerate(data.get("streams", []), start=1):
        parsed_audio_info.append({
            "ffprobe_stream_index": s_data.get("index"), "gui_track_number": i, 
            "codec": s_data.get("codec_name"),
            "language": (s_data.get("tags", {}).get("language") or "und").lower(),
            "channels": s_data.get("channels", 0)
        })
    return parsed_audio_info

def get_video_resolution(video_file): 
    cap = cv2.VideoCapture(video_file)
    if not cap.isOpened(): print(f"Unable to open video file: {video_file}"); return None, None
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)); height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release(); return height, width

def get_video_duration(video_file): 
    cap = cv2.VideoCapture(video_file)
    if not cap.isOpened(): print(f"Unable to open video file: {video_file}"); return None
    fps = cap.get(cv2.CAP_PROP_FPS); frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    cap.release(); return (frame_count / fps) if fps else None

# ---------------------------------------------------------------------
# Step 2: Automatic Crop Detection (Function unchanged)
# ---------------------------------------------------------------------
def get_crop_parameters(video_file, input_width, input_height, limit_value): 
    print(f"Detecting optimal crop parameters for {os.path.basename(video_file)}...")
    duration = get_video_duration(video_file)
    if duration is None or duration < 1: print("Video too short or duration error."); return input_width, input_height, 0, 0 
    round_value = "2"; sample_interval = 300
    num_samples = max(12, min(72, int(duration // sample_interval)))
    if num_samples < 12: num_samples = 12
    start_offset = min(300, duration * 0.05)
    interval = (duration - start_offset) / num_samples if duration > start_offset else duration / num_samples
    crop_values = []
    for i in range(num_samples):
        start_time = start_offset + i * interval if duration > start_offset else i * interval
        if start_time >= duration: start_time = duration - 1
        if num_samples > 1 : print(f"  Analyzing {os.path.basename(video_file)} @{int(start_time)}s ({i+1}/{num_samples})...")
        else: print(f"  Analyzing {os.path.basename(video_file)} @{int(start_time)}s...")
        command = ["ffmpeg", "-ss", str(int(start_time)), "-i", video_file, "-vframes", "3", 
                   "-vf", f"cropdetect={limit_value}:{round_value}:0", "-f", "null", "-", 
                   "-hide_banner", "-loglevel", "verbose"]
        try:
            process = subprocess.Popen(command, stderr=subprocess.PIPE, stdout=subprocess.PIPE, 
                                     text=True, encoding='utf-8', errors='replace')
            stdout, stderr = process.communicate()
            ffmpeg_output = (stdout or '') + (stderr or '')
            for line in ffmpeg_output.split('\n'):
                if 'crop=' in line: crop_values.append(line[line.index('crop=')+5:].strip())
        except Exception as e: print(f"Error during cropdetect @{int(start_time)}s: {e}")
    if crop_values:
        try:
            w, h, x, y = [int(v) for v in Counter(crop_values).most_common(1)[0][0].split(':')]
            print(f"  Optimal crop for {os.path.basename(video_file)}: W={w}, H={h}, X={x}, Y={y}")
        except: w, h, x, y = input_width, input_height, 0, 0; print(f"  Invalid crop. Full frame.")
    else: w, h, x, y = input_width, input_height, 0, 0; print(f"  No crop found. Full frame.")
    return w, h, x, y

# ---------------------------------------------------------------------
# Step 3: Basic Tkinter GUI for user settings
# ---------------------------------------------------------------------
def launch_gui(initial_file_list, initial_file_settings_map, default_qvbr_global, default_hdr_global):
    root = tk.Tk()
    root.title("Video Processing Settings")
    file_settings_map = initial_file_settings_map 
    
    gui_vars = { "no_crop": tk.BooleanVar(), "output_resolution_choice": tk.StringVar(),
        "qvbr_value": tk.StringVar(), "gop_value": tk.StringVar(), "fruc_setting": tk.BooleanVar(),
        "denoise_setting": tk.BooleanVar(), "artifact_setting": tk.BooleanVar() }
    decoding_mode_global = tk.StringVar(value="Hardware")
    hdr_enable_global_var = tk.BooleanVar(value=default_hdr_global)
    sleep_enable_global = tk.BooleanVar(value=False)
    max_processes_global_str_var = tk.StringVar(value="1")
    crop_w_display_var, crop_h_display_var = tk.StringVar(value="0"), tk.StringVar(value="0")
    crop_x_display_var, crop_y_display_var = tk.StringVar(value="0"), tk.StringVar(value="0")
    current_primary_selected_file_path, current_input_width_primary, current_input_height_primary = None, 0, 0

    screen_width, screen_height = root.winfo_screenwidth(), root.winfo_screenheight()
    main_frame = tk.Frame(root); main_frame.pack(fill='both', expand=True)
    
    main_canvas = tk.Canvas(main_frame); main_canvas.pack(side='left', fill='both', expand=True) 
    main_scrollbar_y = tk.Scrollbar(main_frame, orient='vertical', command=main_canvas.yview); main_scrollbar_y.pack(side='right', fill='y') 
    main_canvas.configure(yscrollcommand=main_scrollbar_y.set)
    
    inner_frame = tk.Frame(main_canvas) 
    main_canvas.create_window((0, 0), window=inner_frame, anchor='nw')

    resolution_map_config={"No Resize":(None,None,None),"HD 1080p":(1920,1080,"20"),
                           "4K 2160p":(3840,2160,"30"),"8K 4320p":(7680,4320,"40")}

    # Initialize widget references that are used in helper functions before widget creation
    metadata_text_widget, file_treeview, nvvfx_denoise_checkbox_widget, audio_tracks_dynamic_frame = None, None, None, None
    audio_utility_buttons_frame = None 
    width_entry_widget, height_entry_widget, x_offset_entry_widget, y_offset_entry_widget = None,None,None,None 
    audio_canvas = None 

    MIXED_VALUE_DISPLAY = "---" 
    TREE_COLUMNS = { "filename": {"text":"File","width":220,"stretch":tk.YES}, "audio_summary":{"text":"Audio","width":120,"stretch":tk.NO,"anchor":"w"},
        "output_resolution_choice":{"text":"OutRes","width":80,"stretch":tk.NO,"anchor":"c"}, "no_crop":{"text":"NoCr","width":50,"stretch":tk.NO,"anchor":"c"},
        "crop_w":{"text":"CrW","width":45,"stretch":tk.NO,"anchor":"c"}, "crop_h":{"text":"CrH","width":45,"stretch":tk.NO,"anchor":"c"},
        "crop_x":{"text":"CrX","width":45,"stretch":tk.NO,"anchor":"c"}, "crop_y":{"text":"CrY","width":45,"stretch":tk.NO,"anchor":"c"},
        "qvbr_value":{"text":"QVBR","width":50,"stretch":tk.NO,"anchor":"c"}, "gop_value":{"text":"GOP","width":40,"stretch":tk.NO,"anchor":"c"},
        "fruc_setting":{"text":"FRUC","width":50,"stretch":tk.NO,"anchor":"c"}, "denoise_setting":{"text":"Den","width":50,"stretch":tk.NO,"anchor":"c"},
        "artifact_setting":{"text":"ArtR","width":60,"stretch":tk.NO,"anchor":"c"} }

    # --- Helper function definitions (order matters for visibility) ---
    def _on_mousewheel(event): 
        target_widget = event.widget
        while target_widget and not hasattr(target_widget, 'yview_scroll'):
            target_widget = target_widget.master
        if not target_widget: 
            target_widget = main_canvas
        delta = -1 * (event.delta // 120) if platform.system() == 'Windows' else -1 * event.delta
        if hasattr(target_widget, 'yview_scroll'):
            target_widget.yview_scroll(delta, "units")
    root.bind_all("<MouseWheel>", _on_mousewheel)

    def _configure_inner_frame(event): 
        main_canvas.configure(scrollregion=main_canvas.bbox("all"))
    inner_frame.bind("<Configure>", _configure_inner_frame)

    def _get_audio_summary_for_file(file_path): 
        if file_path not in file_settings_map or 'audio_tracks_config' not in file_settings_map[file_path]: return "N/A"
        audio_config = file_settings_map[file_path]['audio_tracks_config']
        if not audio_config: return "None"
        selected_count = sum(1 for t in audio_config if t.get('is_selected_for_processing'))
        total_count = len(audio_config)
        if selected_count == 0: return f"0/{total_count} sel."
        first_sel_summary = ""
        for t in audio_config:
            if t.get('is_selected_for_processing'):
                lang = t.get('language','und'); codec = t.get('codec','?'); to_ac3 = "->AC3" if t.get('convert_to_ac3') and codec!='ac3' else ""
                first_sel_summary = f"{lang.upper()}:{codec}{to_ac3}"; break
        return f"{selected_count}/{total_count} ({first_sel_summary})"

    def _get_treeview_values_for_file(file_path): 
        config = file_settings_map.get(file_path, {}); values = []
        for col_id in TREE_COLUMNS.keys():
            if col_id == "filename": values.append(os.path.basename(file_path))
            elif col_id == "audio_summary": values.append(_get_audio_summary_for_file(file_path))
            elif col_id in ["no_crop","fruc_setting","denoise_setting","artifact_setting"]: values.append("Y" if config.get(col_id) else "N")
            elif col_id.startswith("crop_"): values.append(str(config.get(col_id)) if config.get(col_id) is not None else "N/A")
            else: values.append(str(config.get(col_id, DEFAULT_SETTINGS_PER_FILE.get(col_id, "N/A"))))
        return tuple(values)

    def _update_treeview_row(file_path_to_update): 
        if file_treeview and file_path_to_update in file_settings_map:
            try:
                if file_treeview.exists(file_path_to_update):
                    file_treeview.item(file_path_to_update, values=_get_treeview_values_for_file(file_path_to_update))
            except tk.TclError: pass 

    def _apply_gui_var_to_selected_files(var_key_name, new_value): 
        selected_iids = file_treeview.selection();
        if not selected_iids: return
        for iid in selected_iids:
            if iid in file_settings_map:
                file_settings_map[iid][var_key_name] = new_value; _update_treeview_row(iid)
        if len(selected_iids) > 1: _update_gui_controls_for_selection(selected_iids) # Refresh mixed states if needed
    
    def update_metadata_display(selected_file_path_to_display): # Moved definition up
        nonlocal metadata_text_widget
        if not metadata_text_widget: return 
        if not selected_file_path_to_display:
            metadata_text_widget.config(state='normal')
            metadata_text_widget.delete("1.0", "end")
            metadata_text_widget.insert("1.0", "No file selected or metadata available.")
            metadata_text_widget.config(state='disabled')
            return
        color_data = get_video_color_info(selected_file_path_to_display)
        meta_txt = (f"File: {os.path.basename(selected_file_path_to_display)}\n" + "".join([f"{k.replace('_', ' ').title()}: {v or 'N/A'}\n" for k, v in color_data.items()]))
        metadata_text_widget.config(state='normal')
        metadata_text_widget.delete("1.0", "end")
        metadata_text_widget.insert("1.0", meta_txt)
        metadata_text_widget.config(state='disabled')

    def _update_crop_fields_for_primary_selection(): 
        nonlocal width_entry_widget, height_entry_widget, x_offset_entry_widget, y_offset_entry_widget, \
                 current_input_width_primary, current_input_height_primary

        if not current_primary_selected_file_path or current_primary_selected_file_path not in file_settings_map:
            crop_w_display_var.set("0"); crop_h_display_var.set("0"); crop_x_display_var.set("0"); crop_y_display_var.set("0")
            for entry in [width_entry_widget,height_entry_widget,x_offset_entry_widget,y_offset_entry_widget]:
                if entry: entry.config(state='disabled')
            return
        config = file_settings_map[current_primary_selected_file_path]
        current_input_width_primary, current_input_height_primary = config['resolution_w'], config['resolution_h']
        is_no_crop = config.get("no_crop",False)
        entry_state = 'disabled' if is_no_crop else 'normal'
        if is_no_crop:
            crop_w_display_var.set(str(current_input_width_primary)); crop_h_display_var.set(str(current_input_height_primary))
            crop_x_display_var.set("0"); crop_y_display_var.set("0")
        else:
            crop_w_display_var.set(str(config['crop_w']) if config['crop_w'] is not None else str(current_input_width_primary))
            crop_h_display_var.set(str(config['crop_h']) if config['crop_h'] is not None else str(current_input_height_primary))
            crop_x_display_var.set(str(config['crop_x']) if config['crop_x'] is not None else "0")
            crop_y_display_var.set(str(config['crop_y']) if config['crop_y'] is not None else "0")
        for entry in [width_entry_widget,height_entry_widget,x_offset_entry_widget,y_offset_entry_widget]:
            if entry: entry.config(state=entry_state)
            
    def _update_denoise_checkbox_state(primary_file_config): 
        nonlocal nvvfx_denoise_checkbox_widget
        if not nvvfx_denoise_checkbox_widget or not primary_file_config: return
        applicable = not (primary_file_config.get('resolution_h',0)>=1080 and primary_file_config.get('resolution_w',0)>=1920)
        nvvfx_denoise_checkbox_widget.config(state='normal' if applicable else 'disabled')
        if not applicable: gui_vars["denoise_setting"].set(False) 

    def _update_dynamic_audio_track_display(file_path_for_audio): 
        nonlocal audio_tracks_dynamic_frame, audio_utility_buttons_frame, audio_canvas 
        for widget in audio_tracks_dynamic_frame.winfo_children(): widget.destroy()
        is_single_file_selected = file_path_for_audio and file_path_for_audio in file_settings_map
        new_state = 'normal' if is_single_file_selected else 'disabled'
        if audio_utility_buttons_frame: 
            for child in audio_utility_buttons_frame.winfo_children():
                if isinstance(child, tk.Button): child.config(state=new_state)

        bg_color = audio_tracks_dynamic_frame.cget('bg') 
        if not is_single_file_selected:
            tk.Label(audio_tracks_dynamic_frame, text="Select a single file to manage its audio tracks.", bg=bg_color).pack(padx=5,pady=5)
            return
        tracks_config_list = file_settings_map[file_path_for_audio].get('audio_tracks_config', [])
        if not tracks_config_list:
            tk.Label(audio_tracks_dynamic_frame, text="No audio tracks found or scanned for this file.", bg=bg_color).pack(padx=5,pady=5)
            return

        for track_idx, track_data in enumerate(tracks_config_list):
            track_ui_frame = tk.Frame(audio_tracks_dynamic_frame, bg=bg_color)
            track_ui_frame.pack(fill='x', padx=2, pady=1)
            def create_handler(f_path, t_idx, key_in_map, tk_var_instance):
                def handler_func(*args): 
                    if f_path in file_settings_map and \
                       0 <= t_idx < len(file_settings_map[f_path]['audio_tracks_config']):
                        file_settings_map[f_path]['audio_tracks_config'][t_idx][key_in_map] = tk_var_instance.get()
                        _update_treeview_row(f_path) 
                return handler_func
            track_select_var = tk.BooleanVar(value=track_data.get('is_selected_for_processing', False))
            track_data['_gui_select_var'] = track_select_var 
            track_select_var.trace_add("write", create_handler(file_path_for_audio, track_idx, 'is_selected_for_processing', track_select_var))
            tk.Checkbutton(track_ui_frame, variable=track_select_var, bg=bg_color).pack(side='left')
            info = f"Trk {track_data['gui_track_number']} (idx {track_data['ffprobe_stream_index']}): {track_data['codec']} " \
                   f"({track_data['language']}, {track_data['channels']}ch)"
            tk.Label(track_ui_frame, text=info, bg=bg_color, anchor='w').pack(side='left', padx=5, fill='x', expand=True)
            convert_ac3_var = tk.BooleanVar(value=track_data.get('convert_to_ac3', False))
            track_data['_gui_convert_var'] = convert_ac3_var 
            convert_ac3_var.trace_add("write", create_handler(file_path_for_audio, track_idx, 'convert_to_ac3', convert_ac3_var))
            tk.Checkbutton(track_ui_frame, text="To AC3", variable=convert_ac3_var, bg=bg_color).pack(side='left', padx=5)
        if audio_canvas: audio_canvas.yview_moveto(0) 

    def _update_gui_controls_for_selection(selected_iids): 
        nonlocal current_primary_selected_file_path
        if not selected_iids: 
            current_primary_selected_file_path = None
            for var in gui_vars.values(): var.set(False) if isinstance(var,tk.BooleanVar) else var.set("")
            update_metadata_display(None); _update_crop_fields_for_primary_selection()
            if nvvfx_denoise_checkbox_widget: nvvfx_denoise_checkbox_widget.config(state='disabled')
            _update_dynamic_audio_track_display(None) 
            return
        is_single = len(selected_iids) == 1; new_primary = selected_iids[0]
        if current_primary_selected_file_path != new_primary or is_single: 
            current_primary_selected_file_path = new_primary
            primary_cfg = file_settings_map.get(current_primary_selected_file_path,{})
            update_metadata_display(current_primary_selected_file_path) # Now defined
            _update_crop_fields_for_primary_selection()
            if primary_cfg and nvvfx_denoise_checkbox_widget: 
                 _update_denoise_checkbox_state(primary_cfg) 
        
        _update_dynamic_audio_track_display(current_primary_selected_file_path if is_single else None)

        for key, var_ctrl in gui_vars.items():
            if selected_iids[0] not in file_settings_map: continue 
            first_val = file_settings_map[selected_iids[0]].get(key)
            if is_single: var_ctrl.set(first_val if first_val is not None else DEFAULT_SETTINGS_PER_FILE.get(key))
            else:
                all_same = all( (iid in file_settings_map and file_settings_map[iid].get(key) == first_val) for iid in selected_iids[1:])
                if all_same: var_ctrl.set(first_val if first_val is not None else DEFAULT_SETTINGS_PER_FILE.get(key))
                else: (var_ctrl.set(False) if isinstance(var_ctrl,tk.BooleanVar) else var_ctrl.set(MIXED_VALUE_DISPLAY))

    # Traced variable handlers (defined after helpers they use)
    def _on_no_crop_var_changed(*args):
        _apply_gui_var_to_selected_files("no_crop", gui_vars["no_crop"].get())
        if current_primary_selected_file_path and current_primary_selected_file_path in file_treeview.selection(): 
            _update_crop_fields_for_primary_selection()
    def _on_resolution_var_changed(*args):
        new_res_val = gui_vars["output_resolution_choice"].get()
        if new_res_val != MIXED_VALUE_DISPLAY: _apply_gui_var_to_selected_files("output_resolution_choice", new_res_val)
        selected_iids = file_treeview.selection()
        if len(selected_iids) == 1 and new_res_val != MIXED_VALUE_DISPLAY: 
             if new_res_val in resolution_map_config:  # resolution_map_config is now defined earlier
                 recommended_qvbr = resolution_map_config[new_res_val][2]
                 if recommended_qvbr is not None:
                     gui_vars["qvbr_value"].set(recommended_qvbr) 
                     if current_primary_selected_file_path in file_settings_map:
                          file_settings_map[current_primary_selected_file_path]["qvbr_value"] = recommended_qvbr
                          _update_treeview_row(current_primary_selected_file_path)
    def _on_qvbr_var_changed(*args): 
        val=gui_vars["qvbr_value"].get()
        if val!=MIXED_VALUE_DISPLAY: 
            _apply_gui_var_to_selected_files("qvbr_value",val)
    def _on_gop_var_changed(*args): 
        val=gui_vars["gop_value"].get()
        if val!=MIXED_VALUE_DISPLAY: 
            _apply_gui_var_to_selected_files("gop_value",val)
    def _on_fruc_var_changed(*args): _apply_gui_var_to_selected_files("fruc_setting", gui_vars["fruc_setting"].get())
    def _on_denoise_var_changed(*args): 
        _apply_gui_var_to_selected_files("denoise_setting", gui_vars["denoise_setting"].get()) 
        if current_primary_selected_file_path and current_primary_selected_file_path in file_treeview.selection() and current_primary_selected_file_path in file_settings_map: 
            _update_denoise_checkbox_state(file_settings_map[current_primary_selected_file_path])
    def _on_artifact_var_changed(*args): _apply_gui_var_to_selected_files("artifact_setting", gui_vars["artifact_setting"].get())

    gui_vars["no_crop"].trace_add("write",_on_no_crop_var_changed)
    gui_vars["output_resolution_choice"].trace_add("write",_on_resolution_var_changed)
    gui_vars["qvbr_value"].trace_add("write",_on_qvbr_var_changed)
    gui_vars["gop_value"].trace_add("write",_on_gop_var_changed)
    gui_vars["fruc_setting"].trace_add("write",_on_fruc_var_changed)
    gui_vars["denoise_setting"].trace_add("write",_on_denoise_var_changed)
    gui_vars["artifact_setting"].trace_add("write",_on_artifact_var_changed)
    
    def on_treeview_select(event): _update_gui_controls_for_selection(file_treeview.selection()) # Defined before use

    # --- GUI Layout Start ---
    file_list_outer_frame = tk.Frame(inner_frame)
    file_list_outer_frame.grid(row=0, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
    file_list_outer_frame.columnconfigure(0, weight=1); file_list_outer_frame.rowconfigure(0, weight=1)
    file_treeview = ttk.Treeview(file_list_outer_frame,columns=list(TREE_COLUMNS.keys()),show="headings",selectmode="extended",height=8)
    for col_id,col_props in TREE_COLUMNS.items():
        file_treeview.heading(col_id,text=col_props["text"])
        file_treeview.column(col_id,width=col_props["width"],minwidth=col_props.get("minwidth",40),stretch=col_props["stretch"],anchor=col_props.get("anchor","w"))
    for f_path in initial_file_list: 
        if f_path in initial_file_settings_map: file_treeview.insert("","end",iid=f_path,values=_get_treeview_values_for_file(f_path))
    tree_scroll_y = ttk.Scrollbar(file_list_outer_frame,orient="vertical",command=file_treeview.yview)
    tree_scroll_x = ttk.Scrollbar(file_list_outer_frame,orient="horizontal",command=file_treeview.xview)
    file_treeview.configure(yscrollcommand=tree_scroll_y.set,xscrollcommand=tree_scroll_x.set)
    file_treeview.grid(row=0,column=0,sticky="nsew"); tree_scroll_y.grid(row=0,column=1,sticky="ns"); tree_scroll_x.grid(row=1,column=0,sticky="ew")
    file_treeview.bind("<<TreeviewSelect>>",on_treeview_select)
    def _on_crop_display_var_changed(var_name_str,*args): 
        if current_primary_selected_file_path and current_primary_selected_file_path in file_settings_map:
            if not file_settings_map[current_primary_selected_file_path].get("no_crop"):
                try:
                    tk_var_map = {"crop_w_display_var":crop_w_display_var,"crop_h_display_var":crop_h_display_var,
                                  "crop_x_display_var":crop_x_display_var,"crop_y_display_var":crop_y_display_var}
                    tk_var = tk_var_map[var_name_str]
                    val = int(tk_var.get()); map_key = var_name_str.replace('_display_var','')
                    file_settings_map[current_primary_selected_file_path][map_key] = val-(val%2)
                    tk_var.set(str(file_settings_map[current_primary_selected_file_path][map_key]))
                    _update_treeview_row(current_primary_selected_file_path)
                except (ValueError, KeyError): pass
    crop_w_display_var.trace_add("write",lambda n,i,m,v="crop_w_display_var":_on_crop_display_var_changed(v))
    crop_h_display_var.trace_add("write",lambda n,i,m,v="crop_h_display_var":_on_crop_display_var_changed(v))
    crop_x_display_var.trace_add("write",lambda n,i,m,v="crop_x_display_var":_on_crop_display_var_changed(v))
    crop_y_display_var.trace_add("write",lambda n,i,m,v="crop_y_display_var":_on_crop_display_var_changed(v))
    file_controls_frame = tk.Frame(file_list_outer_frame); file_controls_frame.grid(row=0,column=2,rowspan=2,padx=5,sticky="ns")
    def add_files_gui_handler(): 
        files_to_add = filedialog.askopenfilenames(filetypes=[("Video Files","*.mp4 *.mkv *.avi *.mov")]); newly_added_iids = []
        for fp in files_to_add:
            abs_fp = os.path.abspath(fp)
            if not file_treeview.exists(abs_fp):
                h_res,w_res=get_video_resolution(abs_fp);
                if h_res is None: continue
                cd=get_video_color_info(abs_fp); cp=(cd["color_primaries"]or"").lower(); cs=(cd["color_space"]or"").lower()
                is_hdr=cp in ["bt2020","2020"] or cs in ["bt2020nc","2020nc"]; limit_val="128" if is_hdr else "24"
                fqvbr=("44" if w_res>=7680 or h_res>=4320 else "33" if w_res>=3840 or h_res>=2160 else DEFAULT_SETTINGS_PER_FILE["qvbr_value"])
                s_aud=run_ffprobe_for_audio_streams(abs_fp); aud_cfg=[]; n_aud=len(s_aud)
                for ti in s_aud:
                    is_sel=(n_aud==1) or (ti['language'] not in [None,"und",""] and ti['language'] in ENGLISH_LANG_TAGS)
                    aud_cfg.append({**ti,'is_selected_for_processing':is_sel,'convert_to_ac3':(ti['codec']!='ac3' and is_sel)})
                file_settings_map[abs_fp]={**DEFAULT_SETTINGS_PER_FILE,"resolution_w":w_res,"resolution_h":h_res,
                    "is_hdr_content":is_hdr,"limit_value_for_cropdetect":limit_val,"qvbr_value":fqvbr,"audio_tracks_config":aud_cfg}
                file_treeview.insert("","end",iid=abs_fp,values=_get_treeview_values_for_file(abs_fp)); newly_added_iids.append(abs_fp)
        if newly_added_iids: file_treeview.selection_set(newly_added_iids[0]); file_treeview.focus(newly_added_iids[0])
    tk.Button(file_controls_frame,text="Add Files",command=add_files_gui_handler).pack(fill='x',pady=(0,5))
    tk.Button(file_controls_frame,text="Clear List",command=lambda:([file_treeview.delete(i) for i in file_treeview.get_children()],
        file_settings_map.clear(),_update_gui_controls_for_selection([]))).pack(fill='x',pady=(0,5))
    def move_item_handler(d): 
        sel=file_treeview.selection();
        if not sel: return
        for iid in (sel if d=="up" else reversed(sel)): 
            idx=file_treeview.index(iid); tgt=idx-1 if d=="up" else idx+1
            if 0<=tgt<len(file_treeview.get_children()): file_treeview.move(iid,file_treeview.parent(iid),tgt)
        file_treeview.selection_set(sel);
        if sel: file_treeview.focus(sel[0])
    tk.Button(file_controls_frame,text="Move Up",command=lambda:move_item_handler("up")).pack(fill='x',pady=(0,5))
    tk.Button(file_controls_frame,text="Move Down",command=lambda:move_item_handler("down")).pack(fill='x',pady=(0,5))
    def delete_selected_gui_handler(): 
        sel=file_treeview.selection();
        if not sel: return
        for iid in sel:
            if file_treeview.exists(iid): file_treeview.delete(iid)
            if iid in file_settings_map: del file_settings_map[iid]
        _update_gui_controls_for_selection(file_treeview.selection())
    tk.Button(file_controls_frame,text="Delete Selected",command=delete_selected_gui_handler).pack(fill='x',pady=(0,5))
    def calculate_crop_for_all_handler(): 
        all_ids=file_treeview.get_children("");
        if not all_ids: messagebox.showinfo("Info","No files."); return
        print("\nBatch crop calc..."); root.update_idletasks()
        for i,fp in enumerate(all_ids):
            if fp not in file_settings_map: continue
            cfg=file_settings_map[fp]; print(f"Processing ({i+1}/{len(all_ids)}): {os.path.basename(fp)}"); root.update_idletasks()
            w,h,x,y=get_crop_parameters(fp,cfg['resolution_w'],cfg['resolution_h'],cfg['limit_value_for_cropdetect'])
            cfg.update({'crop_w':w,'crop_h':h,'crop_x':x,'crop_y':y,'no_crop':False}); _update_treeview_row(fp)
            if fp==current_primary_selected_file_path: gui_vars["no_crop"].set(False); _update_crop_fields_for_primary_selection()
        messagebox.showinfo("Batch Crop","Done."); print("Batch crop done.\n")
    tk.Button(file_controls_frame,text="Calc Crop All",command=calculate_crop_for_all_handler).pack(fill='x',pady=(10,5))

    left_column_frame = tk.Frame(inner_frame)
    left_column_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
    right_column_frame = tk.Frame(inner_frame)
    right_column_frame.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)
    inner_frame.columnconfigure(0, weight=1); inner_frame.columnconfigure(1, weight=1) 
    
    current_row_left = 0
    metadata_frame=tk.LabelFrame(left_column_frame,text="Color Metadata (Primary Selected)"); 
    metadata_frame.grid(row=current_row_left,column=0,padx=0,pady=5,sticky="new"); current_row_left += 1
    metadata_frame.columnconfigure(0,weight=1); metadata_frame.rowconfigure(0,weight=1)
    metadata_text_widget=tk.Text(metadata_frame,height=5,wrap="word",state='disabled',bg="#f0f0f0"); metadata_text_widget.grid(row=0,column=0,sticky="nsew")

    options_frame=tk.LabelFrame(left_column_frame,text="Video Settings (Applied to Selected)"); 
    options_frame.grid(row=current_row_left,column=0,padx=0,pady=5,sticky="new"); current_row_left += 1
    options_frame.columnconfigure(1,weight=1) 
    decode_mode_lf=tk.LabelFrame(options_frame,text="Global: Decoding"); decode_mode_lf.grid(row=0,column=0,padx=5,pady=2,sticky="ew",columnspan=2)
    tk.Radiobutton(decode_mode_lf,text="HW",variable=decoding_mode_global,value="Hardware").pack(side="left",padx=5)
    tk.Radiobutton(decode_mode_lf,text="SW",variable=decoding_mode_global,value="Software").pack(side="left",padx=5)
    tk.Checkbutton(options_frame,text="Global: HDR Convert",variable=hdr_enable_global_var).grid(row=1,column=0,sticky="w",padx=5,pady=2)
    mp_f=tk.Frame(options_frame); mp_f.grid(row=1,column=1,sticky="e",padx=5,pady=2)
    tk.Label(mp_f,text="Global: MaxProc:").pack(side="left"); tk.Entry(mp_f,textvariable=max_processes_global_str_var,width=3).pack(side="left")
    tk.Label(options_frame,text="Out Res:").grid(row=2,column=0,sticky="w",padx=5,pady=2)
    opt_choices=[MIXED_VALUE_DISPLAY]+list(resolution_map_config.keys())
    tk.OptionMenu(options_frame,gui_vars["output_resolution_choice"],*opt_choices).grid(row=2,column=1,sticky="ew",padx=5,pady=2)
    tk.Label(options_frame,text="QVBR:").grid(row=3,column=0,sticky="w",padx=5,pady=2); tk.Entry(options_frame,textvariable=gui_vars["qvbr_value"],width=7).grid(row=3,column=1,sticky="ew",padx=5,pady=2)
    tk.Label(options_frame,text="GOP Len:").grid(row=4,column=0,sticky="w",padx=5,pady=2); tk.Entry(options_frame,textvariable=gui_vars["gop_value"],width=7).grid(row=4,column=1,sticky="ew",padx=5,pady=2)
    tk.Checkbutton(options_frame,text="FRUC",variable=gui_vars["fruc_setting"]).grid(row=5,column=0,sticky="w",padx=5,pady=2)
    nvvfx_denoise_checkbox_widget=tk.Checkbutton(options_frame,text="Denoise",variable=gui_vars["denoise_setting"]); nvvfx_denoise_checkbox_widget.grid(row=5,column=1,sticky="w",padx=5,pady=2)
    tk.Checkbutton(options_frame,text="Artifact Red.",variable=gui_vars["artifact_setting"]).grid(row=6,column=0,sticky="w",padx=5,pady=2)

    crop_frame=tk.LabelFrame(left_column_frame,text="Crop (Primary Selected)"); 
    crop_frame.grid(row=current_row_left,column=0,padx=0,pady=5,sticky="new"); current_row_left += 1
    crop_frame.columnconfigure(1,weight=1)
    tk.Label(crop_frame,text="W:").grid(row=0,column=0,sticky="w",padx=5,pady=2); width_entry_widget=tk.Entry(crop_frame,textvariable=crop_w_display_var); width_entry_widget.grid(row=0,column=1,sticky="ew",padx=5,pady=2)
    tk.Label(crop_frame,text="H:").grid(row=1,column=0,sticky="w",padx=5,pady=2); height_entry_widget=tk.Entry(crop_frame,textvariable=crop_h_display_var); height_entry_widget.grid(row=1,column=1,sticky="ew",padx=5,pady=2)
    tk.Label(crop_frame,text="X:").grid(row=2,column=0,sticky="w",padx=5,pady=2); x_offset_entry_widget=tk.Entry(crop_frame,textvariable=crop_x_display_var); x_offset_entry_widget.grid(row=2,column=1,sticky="ew",padx=5,pady=2)
    tk.Label(crop_frame,text="Y:").grid(row=3,column=0,sticky="w",padx=5,pady=2); y_offset_entry_widget=tk.Entry(crop_frame,textvariable=crop_y_display_var); y_offset_entry_widget.grid(row=3,column=1,sticky="ew",padx=5,pady=2)
    def calculate_crop_for_selected_handler(): 
        sel_ids=file_treeview.selection();
        if not sel_ids: messagebox.showinfo("Info","Select file(s)."); return
        print(f"\nCrop calc for {len(sel_ids)} file(s)..."); root.update_idletasks()
        for i,fp in enumerate(sel_ids):
            if fp not in file_settings_map: continue
            cfg=file_settings_map[fp]; print(f"  Processing ({i+1}/{len(sel_ids)}): {os.path.basename(fp)}"); root.update_idletasks()
            w,h,x,y=get_crop_parameters(fp,cfg['resolution_w'],cfg['resolution_h'],cfg['limit_value_for_cropdetect'])
            cfg.update({'crop_w':w,'crop_h':h,'crop_x':x,'crop_y':y,'no_crop':False}); _update_treeview_row(fp)
            if fp==current_primary_selected_file_path: gui_vars["no_crop"].set(False); _update_crop_fields_for_primary_selection()
        messagebox.showinfo("Crop Calc",f"Done for {len(sel_ids)} file(s)."); print("Selected crop calc done.\n")
    tk.Button(crop_frame,text="Calc Crop Selected",command=calculate_crop_for_selected_handler).grid(row=4,column=0,columnspan=2,pady=(10,0),sticky="ew",padx=5)
    tk.Checkbutton(crop_frame,text="No Crop (for selected)",variable=gui_vars["no_crop"]).grid(row=5,column=0,columnspan=2,pady=(5,0),sticky="w",padx=5)
    
    audio_section_frame=tk.LabelFrame(right_column_frame,text="Audio Tracks (Primary Selected File)"); 
    audio_section_frame.grid(row=0,column=0,padx=0,pady=5,sticky="nsew") 
    right_column_frame.rowconfigure(0, weight=1) 
    right_column_frame.columnconfigure(0, weight=1) 
    audio_section_frame.columnconfigure(0,weight=1) 
    audio_section_frame.rowconfigure(1, weight=1) 
    audio_utility_buttons_frame=tk.Frame(audio_section_frame); audio_utility_buttons_frame.grid(row=0, column=0, sticky="new", padx=5, pady=5)
    def _apply_to_displayed_audio_tracks(setting_key,value): 
        if current_primary_selected_file_path and current_primary_selected_file_path in file_settings_map:
            tracks_cfg=file_settings_map[current_primary_selected_file_path].get('audio_tracks_config',[])
            for t_data in tracks_cfg:
                if setting_key=='is_selected_for_processing' and '_gui_select_var' in t_data: t_data['_gui_select_var'].set(value)
                elif setting_key=='convert_to_ac3' and '_gui_convert_var' in t_data: t_data['_gui_convert_var'].set(value)
            _update_treeview_row(current_primary_selected_file_path)
    tk.Button(audio_utility_buttons_frame,text="Sel.All",command=lambda:_apply_to_displayed_audio_tracks('is_selected_for_processing',True)).pack(side='left',padx=2)
    tk.Button(audio_utility_buttons_frame,text="Clr.All",command=lambda:_apply_to_displayed_audio_tracks('is_selected_for_processing',False)).pack(side='left',padx=2)
    tk.Button(audio_utility_buttons_frame,text="CopyAll",command=lambda:_apply_to_displayed_audio_tracks('convert_to_ac3',False)).pack(side='left',padx=2)
    tk.Button(audio_utility_buttons_frame,text="ConvAll",command=lambda:_apply_to_displayed_audio_tracks('convert_to_ac3',True)).pack(side='left',padx=2)
    audio_canvas_outer_frame = tk.Frame(audio_section_frame) 
    audio_canvas_outer_frame.grid(row=1, column=0, sticky="nsew")
    audio_canvas_outer_frame.rowconfigure(0, weight=1); audio_canvas_outer_frame.columnconfigure(0, weight=1)
    audio_canvas=tk.Canvas(audio_canvas_outer_frame,borderwidth=0, highlightthickness=0) 
    audio_tracks_dynamic_frame=tk.Frame(audio_canvas) 
    audio_scrollbar=ttk.Scrollbar(audio_canvas_outer_frame,orient="vertical",command=audio_canvas.yview)
    audio_canvas.configure(yscrollcommand=audio_scrollbar.set)
    audio_canvas.grid(row=0, column=0, sticky="nsew"); audio_scrollbar.grid(row=0, column=1, sticky="ns")
    audio_canvas.create_window((0,0),window=audio_tracks_dynamic_frame,anchor="nw", tags="audio_dynamic_frame_tag")
    def _configure_audio_canvas_window(event): 
        audio_canvas.configure(scrollregion=audio_canvas.bbox("all"))
        audio_canvas.itemconfig("audio_dynamic_frame_tag", width=event.width) 
    audio_tracks_dynamic_frame.bind("<Configure>",_configure_audio_canvas_window)
    audio_canvas_outer_frame.config(height=150) 

    tk.Checkbutton(inner_frame,text="Global: Sleep After Processing",variable=sleep_enable_global).grid(row=2,column=0,columnspan=2,padx=10,pady=(10,0),sticky="w")
    def start_processing_handler(): 
        ordered_files=file_treeview.get_children("");
        if not ordered_files: messagebox.showerror("Error","No files."); return
        if current_primary_selected_file_path: 
            try:
                if not file_settings_map[current_primary_selected_file_path].get("no_crop"): 
                    int(crop_w_display_var.get());int(crop_h_display_var.get());int(crop_x_display_var.get());int(crop_y_display_var.get())
            except ValueError: messagebox.showerror("Error",f"Invalid crop for {os.path.basename(current_primary_selected_file_path)}."); return
        for fp in ordered_files: 
            cfg=file_settings_map[fp]
            if not cfg['no_crop'] and cfg.get('crop_w') is not None:
                if not all(isinstance(cfg.get(k),int) for k in ['crop_w','crop_h','crop_x','crop_y']):
                    messagebox.showerror("Error",f"Corrupt crop for {os.path.basename(fp)}."); return
            if cfg.get("output_resolution_choice")==MIXED_VALUE_DISPLAY: messagebox.showerror("Error",f"Res not set for {os.path.basename(fp)}."); return
            if cfg.get("qvbr_value")==MIXED_VALUE_DISPLAY or not cfg.get("qvbr_value","").isdigit(): messagebox.showerror("Error",f"QVBR invalid for {os.path.basename(fp)}."); return
            if cfg.get("gop_value")==MIXED_VALUE_DISPLAY or not cfg.get("gop_value","").isdigit(): messagebox.showerror("Error",f"GOP invalid for {os.path.basename(fp)}."); return
        proc_bundle={"files":list(ordered_files),"decode_mode_global":decoding_mode_global.get(),"hdr_enable_global":hdr_enable_global_var.get(),
            "max_processes_global":max_processes_global_str_var.get(),"file_settings_map":file_settings_map,
            "sleep_after_processing_global":sleep_enable_global.get()}
        root.destroy(); print("\nSettings collected. Starting...\n"); print(json.dumps({k:v for k,v in proc_bundle.items() if k!="file_settings_map"},indent=2))
        process_batch(proc_bundle["files"],proc_bundle)
        if proc_bundle.get("sleep_after_processing_global"):
            print("Sleeping..."); plat=platform.system()
            if plat=="Windows": os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
            elif plat=="Linux": os.system("systemctl suspend")
            elif plat=="Darwin": os.system("pmset sleepnow")
            else: print("Sleep unsupported.")
    tk.Button(inner_frame,text="Start Processing",command=start_processing_handler).grid(row=3,column=0,columnspan=2,padx=10,pady=10,sticky="ew")
    
    inner_frame.rowconfigure(1, weight=1) 

    if file_treeview.get_children(""): 
        first_id=file_treeview.get_children("")[0]; file_treeview.selection_set(first_id); file_treeview.focus(first_id) 
    else: _update_gui_controls_for_selection([]) 
    root.update_idletasks()
    req_w=inner_frame.winfo_reqwidth(); win_w=min(max(req_w+80, 850),screen_width); win_h=int(screen_height*0.90) # Increased min width
    root.geometry(f"{win_w}x{win_h}")
    root.mainloop()

# ---------------------------------------------------------------------
# Step 4: The main encode function (Unchanged from previous full script)
# ---------------------------------------------------------------------
def process_video(file_path, settings_bundle): 
    input_dir = os.path.dirname(file_path); file_name = os.path.basename(file_path)
    output_subdir = os.path.join(input_dir, "processed_videos"); os.makedirs(output_subdir, exist_ok=True)
    output_file = os.path.join(output_subdir, os.path.splitext(file_name)[0] + ".mp4")
    log_file = os.path.join(output_subdir, os.path.splitext(file_name)[0] + "_encoding.log")

    current_file_config = settings_bundle["file_settings_map"].get(file_path)
    if not current_file_config: print(f"Error: No settings for {file_path}. Skipping."); return

    input_height = current_file_config['resolution_h']; input_width = current_file_config['resolution_w']
    qvbr_to_use = current_file_config.get("qvbr_value", "25") 
    gop_to_use = current_file_config.get("gop_value", "6")
    fruc_to_use = current_file_config.get("fruc_setting", False)
    denoise_user_choice = current_file_config.get("denoise_setting", False)
    artifact_to_use = current_file_config.get("artifact_setting", False)
    output_res_choice_this_file = current_file_config.get("output_resolution_choice", "No Resize")

    command = [ "NVEncC64", "--codec", "av1", "--qvbr", qvbr_to_use, "--preset", "p7", "--output-depth", "10", 
        "--gop-len", gop_to_use, "--metadata", "copy", "--chapter-copy", "--key-on-chapter", "--bframes","4", 
        "--tf-level","4", "--split-enc","auto", "--parallel", "auto", "--profile", "high", "--multipass", "2pass-full",
        "--aq", "--aq-temporal", "--aq-strength", "5", "--lookahead", "32", "-i", file_path, "-o", output_file ]
    if settings_bundle["decode_mode_global"] == "Hardware": command.append("--avhw")
    else: command.append("--avsw")
    command.extend(["--colormatrix", "bt2020nc", "--colorprim", "bt2020", "--transfer", "smpte2084"])
    if settings_bundle["hdr_enable_global"]: command.append("--vpp-ngx-truehdr")
    else: command.extend(["--dhdr10-info", "copy", "--dolby-vision-profile", "copy", "--dolby-vision-rpu", "copy"])

    crop_params_to_use = {} 
    if current_file_config.get('no_crop', False): crop_params_to_use = {'crop_w': input_width, 'crop_h': input_height, 'crop_x': 0, 'crop_y': 0}
    elif current_file_config.get('crop_w') is not None: crop_params_to_use = {k: current_file_config[k] for k in ['crop_w','crop_h','crop_x','crop_y']}
    else: 
        w_c, h_c, x_c, y_c = get_crop_parameters(file_path, input_width, input_height, current_file_config['limit_value_for_cropdetect'])
        crop_params_to_use = {'crop_w': w_c, 'crop_h': h_c, 'crop_x': x_c, 'crop_y': y_c}
    for k in ['crop_w','crop_h','crop_x','crop_y']: crop_params_to_use[k] -= crop_params_to_use[k]%2
    left=crop_params_to_use["crop_x"]; top=crop_params_to_use["crop_y"]; crop_w_val=crop_params_to_use["crop_w"]; crop_h_val=crop_params_to_use["crop_h"]
    if left+crop_w_val > input_width: crop_w_val=input_width-left
    if top+crop_h_val > input_height: crop_h_val=input_height-top
    crop_w_val=max(crop_w_val,0); crop_h_val=max(crop_h_val,0)
    right=input_width-(left+crop_w_val); bottom=input_height-(top+crop_h_val); right=max(right,0); bottom=max(bottom,0)
    if crop_w_val>0 and crop_h_val>0 : command.extend(["--crop", f"{left},{top},{right},{bottom}"])
    else: crop_w_val=input_width; crop_h_val=input_height 

    if fruc_to_use: command.extend(["--vpp-fruc", "fps=60"])
    if denoise_user_choice and not (input_height>=1080 and input_width>=1920): command.append("--vpp-nvvfx-denoise")
    elif denoise_user_choice: print(f"Denoise chosen but skipped for {file_name} (res >= 1080p).")
    if artifact_to_use: command.append("--vpp-nvvfx-artifact-reduction")

    local_res_map = { "No Resize":(None,None,None),"HD 1080p":(1920,1080,"20"),"4K 2160p":(3840,2160,"30"),"8K 4320p":(7680,4320,"40") }
    if output_res_choice_this_file in local_res_map: 
        target_w_map_val, target_h_map_val, _ = local_res_map[output_res_choice_this_file] # Renamed to avoid conflict
        curr_w,curr_h = crop_w_val,crop_h_val
        if target_h_map_val is not None and curr_h>0: # Use target_h_map_val
            out_h=target_h_map_val; out_w=int(curr_w*(out_h/curr_h)); out_w-=out_w%2
            if out_w>0 and out_h>0 and (out_w!=curr_w or out_h!=curr_h):
                algo="nvvfx-superres,superres-mode=0" if out_w>curr_w or out_h>curr_h else "bilinear"
                command.extend(["--vpp-resize",f"algo={algo}","--output-res",f"{out_w}x{out_h}"])

    file_specific_audio_config = current_file_config.get('audio_tracks_config', [])
    audio_copy_indices_cmd = [] 
    for track_cfg in file_specific_audio_config:
        if track_cfg.get('is_selected_for_processing'):
            stream_specifier = str(track_cfg['ffprobe_stream_index'])
            if track_cfg.get('convert_to_ac3'):
                command.extend([f"--audio-codec", f"{stream_specifier}?ac3", f"--audio-bitrate", f"{stream_specifier}?640",
                                f"--audio-stream", f"{stream_specifier}?5.1", f"--audio-samplerate", f"{stream_specifier}?48000"])
            else: audio_copy_indices_cmd.append(stream_specifier)
    if audio_copy_indices_cmd: command.extend(["--audio-copy", ",".join(audio_copy_indices_cmd)])

    quoted_command = ' '.join(f'"{arg}"' if ' ' in arg else arg for arg in command)
    print(f"\nProcessing: {file_path}\nNVEncC command:\n{quoted_command}")
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
    vf, settings_bundle = args; process_video(vf, settings_bundle)
def process_batch(video_files_to_process, settings_bundle): 
    try: mp = int(settings_bundle.get("max_processes_global", "1")) 
    except ValueError: mp = 1
    valid_tasks = [(vf, settings_bundle) for vf in video_files_to_process if vf in settings_bundle["file_settings_map"]]
    if not valid_tasks: print("No valid tasks for processing."); return
    if mp <= 1:
        for vf, s_dict in valid_tasks: process_video(vf, s_dict) 
    else: print(f"Using multiprocessing with {mp} processes..."); Pool(mp).map(process_wrapper, valid_tasks)

# ---------------------------------------------------------------------
# Main Script Logic (Batch + GUI) 
# ---------------------------------------------------------------------
if __name__ == "__main__": 
    cli_input_files = []
    if len(sys.argv) > 1:
        for arg_pattern in sys.argv[1:]:
            expanded_cli_files = glob.glob(arg_pattern)
            if not expanded_cli_files: print(f"Warning: CLI pattern '{arg_pattern}' matched no files.")
            cli_input_files.extend(expanded_cli_files)
    cwd = os.getcwd(); print(f"Scanning CWD for videos: {cwd}")
    cwd_found_files = []
    vid_exts = ["*.mp4","*.mkv","*.avi","*.mov","*.webm","*.flv","*.ts","*.mpg","*.mpeg"] 
    for ext_pattern in vid_exts: cwd_found_files.extend(glob.glob(os.path.join(cwd, ext_pattern)))
    unique_abs_paths = {os.path.abspath(f) for f in cli_input_files + cwd_found_files}
    input_video_files = sorted(list(unique_abs_paths))
    master_file_settings_map = {}
    global_default_hdr_setting, global_default_qvbr_setting = False, "22" 
    if input_video_files:
        print("\nInitial files to load:")
        for f_path in input_video_files:
            print(f"  - {os.path.basename(f_path)} (from: {os.path.dirname(f_path)})")
            h, w = get_video_resolution(f_path)
            if h is None or w is None: print(f"Error: No resolution for {f_path}. Skipped."); continue 
            color_data = get_video_color_info(f_path)
            cp = (color_data["color_primaries"] or "").lower(); cs = (color_data["color_space"] or "").lower()
            is_hdr = cp in ["bt2020", "2020"] or cs in ["bt2020nc", "2020nc"]
            limit_crop_val = "128" if is_hdr else "24" 
            file_specific_qvbr = ("44" if w>=7680 or h>=4320 else "33" if w>=3840 or h>=2160 else DEFAULT_SETTINGS_PER_FILE["qvbr_value"])
            scanned_audio_tracks = run_ffprobe_for_audio_streams(f_path)
            current_file_audio_config = []
            num_audio_tracks = len(scanned_audio_tracks)
            for track_info in scanned_audio_tracks:
                is_selected = (num_audio_tracks==1) or (track_info['language'] not in [None,"und",""] and track_info['language'] in ENGLISH_LANG_TAGS)
                current_file_audio_config.append({**track_info, 'is_selected_for_processing':is_selected,
                    'convert_to_ac3':(track_info['codec']!='ac3' and is_selected)})
            master_file_settings_map[f_path] = {**DEFAULT_SETTINGS_PER_FILE, "resolution_w":w,"resolution_h":h, 
                "is_hdr_content":is_hdr, "limit_value_for_cropdetect":limit_crop_val, "qvbr_value":file_specific_qvbr,
                "audio_tracks_config":current_file_audio_config }
        if master_file_settings_map: 
            first_valid_path = next(iter(master_file_settings_map))
            first_cfg_data = master_file_settings_map[first_valid_path] 
            global_default_hdr_setting = not first_cfg_data['is_hdr_content'] 
            global_default_qvbr_setting = first_cfg_data['qvbr_value'] 
    if not input_video_files: print("No video files found by CLI or in CWD.")
    print("\nLaunching GUI...\n")
    launch_gui(list(master_file_settings_map.keys()), master_file_settings_map, global_default_qvbr_setting, global_default_hdr_setting)
    print("Processing Complete or GUI closed.")
    if platform.system() == "Windows": os.system("pause")
