import os
import sys
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinterdnd2 import DND_FILES, TkinterDnD
import glob 

# --- CONFIGURATION ---
INITIAL_CWD = os.getcwd() 
OUTPUT_SUBFOLDER_NAME = "Processed_Overwatch_Videos_AV1"
VIDEO_EXTENSIONS = [
    '.mp4', '.mkv', '.mov', '.avi', '.flv', '.wmv', 
    '.webm', '.mpg', '.mpeg', '.ts', '.vob'
]
VIDEO_FILE_TYPES_DIALOG = [
    ("Video files", " ".join([f"*{ext}" for ext in VIDEO_EXTENSIONS])),
    ("All files", "*.*")
]

files = []
default_intro_trim = 293
default_outtro_trim = 1131
default_qvbr_str = "28"
default_qvbr_4k_str = "38"
# --- END CONFIGURATION ---

def gather_initial_files():
    """Gathers initial files based on CLI args or by scanning INITIAL_CWD."""
    global files
    files = []
    args = sys.argv[1:]

    if not args or (len(args) == 1 and args[0] == '*'):
        print(f"No specific files/folders given or '*' used. Scanning: {INITIAL_CWD}")
        found_in_cwd = []
        for ext in VIDEO_EXTENSIONS:
            found_in_cwd.extend(glob.glob(os.path.join(INITIAL_CWD, f"*{ext.lower()}")))
            found_in_cwd.extend(glob.glob(os.path.join(INITIAL_CWD, f"*{ext.upper()}")))
        
        for f_path in found_in_cwd:
            abs_path = os.path.abspath(f_path)
            if os.path.isfile(abs_path) and abs_path not in files:
                files.append(abs_path)
    else:
        print(f"Processing command-line arguments: {args}")
        for arg_item in args:
            expanded_by_glob = glob.glob(arg_item)
            paths_to_check = []
            if expanded_by_glob:
                paths_to_check.extend(expanded_by_glob)
            elif os.path.exists(arg_item):
                paths_to_check.append(arg_item)
            else:
                print(f"Warning: Argument '{arg_item}' not found or pattern matched no files.")
                continue

            for path_found in paths_to_check:
                abs_path_found = os.path.abspath(path_found)
                if os.path.isfile(abs_path_found):
                    _base, ext = os.path.splitext(abs_path_found)
                    if ext.lower() in VIDEO_EXTENSIONS and abs_path_found not in files:
                        files.append(abs_path_found)
                elif os.path.isdir(abs_path_found):
                    print(f"Scanning provided directory: {abs_path_found}")
                    for ext in VIDEO_EXTENSIONS:
                        files_in_subdir = glob.glob(os.path.join(abs_path_found, f"*{ext.lower()}"))
                        files_in_subdir.extend(glob.glob(os.path.join(abs_path_found, f"*{ext.upper()}")))
                        for f_path_in_dir in files_in_subdir:
                            abs_path_in_dir = os.path.abspath(f_path_in_dir)
                            if os.path.isfile(abs_path_in_dir) and abs_path_in_dir not in files:
                                files.append(abs_path_in_dir)
    
    files = sorted(list(set(files)))
    if files:
        print(f"Found {len(files)} video file(s) to load into GUI.")
    else:
        print("No video files initially identified. Please add files via GUI.")

def show_gui():
    """Initializes and displays the main GUI window."""
    try:
        root = TkinterDnD.Tk()
        root.title("Overwatch Video Processor")

        intro_trim_var = tk.StringVar(value=str(default_intro_trim))
        outtro_trim_var = tk.StringVar(value=str(default_outtro_trim))
        qvbr_var = tk.StringVar(value=default_qvbr_str)
        upscale_var = tk.BooleanVar(value=False)
        truehdr_var = tk.BooleanVar(value=True) # NGX TrueHDR filter, ON by default

        def refresh_listbox():
            listbox.delete(0, tk.END)
            for file_path in files: listbox.insert(tk.END, file_path)

        def add_files_from_dialog(dropped_files_list=None):
            global files
            if dropped_files_list is None:
                dropped_files_list = filedialog.askopenfilenames(
                    title="Select video files", filetypes=VIDEO_FILE_TYPES_DIALOG)
            added_count = 0
            for file_path in dropped_files_list:
                if os.path.isfile(file_path):
                    abs_file_path = os.path.abspath(file_path)
                    _base, ext = os.path.splitext(abs_file_path)
                    if ext.lower() in VIDEO_EXTENSIONS:
                        if abs_file_path not in files: files.append(abs_file_path); added_count += 1
                    else: messagebox.showwarning("File Type Skipped", f"Skipped: {os.path.basename(abs_file_path)}")
            if added_count > 0: refresh_listbox()

        def clear_all_files(): global files; files.clear(); refresh_listbox()
        def move_selected_file_up():
            global files; selected_indices = listbox.curselection()
            if not selected_indices or selected_indices[0] == 0: return
            idx = selected_indices[0]; files[idx - 1], files[idx] = files[idx], files[idx - 1]
            refresh_listbox(); listbox.selection_clear(0, tk.END); listbox.selection_set(idx - 1); listbox.activate(idx - 1)
        def move_selected_file_down():
            global files; selected_indices = listbox.curselection()
            if not selected_indices or selected_indices[0] == len(files) - 1: return
            idx = selected_indices[0]; files[idx + 1], files[idx] = files[idx], files[idx + 1]
            refresh_listbox(); listbox.selection_clear(0, tk.END); listbox.selection_set(idx + 1); listbox.activate(idx + 1)
        def remove_selected_files():
            global files; selected_indices = listbox.curselection()
            if not selected_indices: return
            for idx in sorted(selected_indices, reverse=True): del files[idx]
            refresh_listbox()
        def on_upscale_checkbox_toggle(): qvbr_var.set(default_qvbr_4k_str if upscale_var.get() else default_qvbr_str)

        def on_start_processing_button_click():
            try: intro_s = int(intro_trim_var.get()) if intro_trim_var.get() else 0
            except ValueError: messagebox.showerror("Invalid Input", f"Intro Trim: '{intro_trim_var.get()}' invalid."); return
            if intro_s < 0: messagebox.showerror("Invalid Input", "Intro trim cannot be negative."); return
            try: outtro_s = int(outtro_trim_var.get()) if outtro_trim_var.get() else 0
            except ValueError: messagebox.showerror("Invalid Input", f"Outtro Trim: '{outtro_trim_var.get()}' invalid."); return
            if outtro_s < 0: messagebox.showerror("Invalid Input", "Outtro trim cannot be negative."); return
            try:
                qvbr_val_int = int(qvbr_var.get())
                if not (1 <= qvbr_val_int <= 51): messagebox.showwarning("Input Warning", f"QVBR '{qvbr_val_int}' is outside typical 1-51 range.")
            except ValueError: messagebox.showerror("Invalid Input", f"QVBR: '{qvbr_var.get()}' invalid."); return
            
            if not files: messagebox.showerror("No Files", "No files selected."); return
            
            apply_truehdr = truehdr_var.get() # Get state of TrueHDR checkbox
            is_upscaling = upscale_var.get()
            
            root.destroy()
            execute_file_processing(intro_s, outtro_s, qvbr_val_int, is_upscaling, apply_truehdr)

        def on_file_drop(event): add_files_from_dialog(root.splitlist(event.data))

        main_app_frame = tk.Frame(root, padx=10, pady=10); main_app_frame.pack(fill=tk.BOTH, expand=True)
        left_controls_panel = tk.Frame(main_app_frame); left_controls_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        tk.Label(left_controls_panel, text="Files to Process:").pack(anchor="w")
        listbox_container_frame = tk.Frame(left_controls_panel); listbox_container_frame.pack(fill=tk.BOTH, expand=True)
        y_scrollbar = tk.Scrollbar(listbox_container_frame, orient=tk.VERTICAL)
        x_scrollbar = tk.Scrollbar(listbox_container_frame, orient=tk.HORIZONTAL)
        listbox = tk.Listbox(listbox_container_frame, width=70, height=15, selectmode=tk.EXTENDED, yscrollcommand=y_scrollbar.set, xscrollcommand=x_scrollbar.set)
        y_scrollbar.config(command=listbox.yview); x_scrollbar.config(command=listbox.xview)
        y_scrollbar.pack(side=tk.RIGHT, fill=tk.Y); x_scrollbar.pack(side=tk.BOTTOM, fill=tk.X); listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        listbox.drop_target_register(DND_FILES); listbox.dnd_bind("<<Drop>>", on_file_drop)
        file_management_buttons_frame = tk.Frame(left_controls_panel); file_management_buttons_frame.pack(fill=tk.X, pady=5)
        tk.Button(file_management_buttons_frame, text="Add Files", command=lambda: add_files_from_dialog(None)).pack(side=tk.LEFT, padx=2)
        tk.Button(file_management_buttons_frame, text="Remove Sel.", command=remove_selected_files).pack(side=tk.LEFT, padx=2)
        tk.Button(file_management_buttons_frame, text="Clear All", command=clear_all_files).pack(side=tk.LEFT, padx=2)
        tk.Button(file_management_buttons_frame, text="Move Up", command=move_selected_file_up).pack(side=tk.LEFT, padx=2)
        tk.Button(file_management_buttons_frame, text="Move Down", command=move_selected_file_down).pack(side=tk.LEFT, padx=2)
        
        processing_options_panel = tk.Frame(main_app_frame); processing_options_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(10, 0))
        tk.Label(processing_options_panel, text="Processing Options", font=('Helvetica', 10, 'bold')).pack(anchor="w", pady=(0,5))
        tk.Label(processing_options_panel, text="Intro Trim (seconds):").pack(anchor="w"); tk.Entry(processing_options_panel, textvariable=intro_trim_var, width=12).pack(anchor="w", pady=(0,5))
        tk.Label(processing_options_panel, text="Outtro Trim (seconds):").pack(anchor="w"); tk.Entry(processing_options_panel, textvariable=outtro_trim_var, width=12).pack(anchor="w", pady=(0,5))
        tk.Label(processing_options_panel, text="QVBR Value (e.g., 1-51):").pack(anchor="w"); tk.Entry(processing_options_panel, textvariable=qvbr_var, width=12).pack(anchor="w", pady=(0,5))
        tk.Checkbutton(processing_options_panel, text="Convert to 4K (2160x2160)", variable=upscale_var, command=on_upscale_checkbox_toggle).pack(anchor="w", pady=(0,5))
        tk.Checkbutton(processing_options_panel, text="Enable NGX TrueHDR & HDR Metadata", variable=truehdr_var).pack(anchor="w", pady=(0,10)) # New Checkbox
        tk.Button(processing_options_panel, text="Start Processing", command=on_start_processing_button_click, height=2, bg="#ADD8E6").pack(fill=tk.X, pady=10)

        refresh_listbox()
        root.mainloop()
    except Exception as e:
        messagebox.showerror("Critical GUI Error", f"Failed to initialize GUI: {e}\nApplication closing.")


def execute_file_processing(intro_trim_seconds, outtro_trim_seconds, qvbr_value_int, perform_upscale, apply_truehdr_and_hdr_metadata):
    """Processes files using NVEncC64 with conditionally applied TrueHDR and HDR metadata."""
    num_total_files = len(files)
    if num_total_files == 0: print("No files to process."); return

    output_main_directory = os.path.join(INITIAL_CWD, OUTPUT_SUBFOLDER_NAME)
    try:
        os.makedirs(output_main_directory, exist_ok=True)
        print(f"Output will be saved to: {output_main_directory}")
    except OSError as e_mkdir:
        print(f"Error creating output directory '{output_main_directory}': {e_mkdir}. Aborting."); return
        
    print(f"Commencing processing for {num_total_files} file(s)...")
    num_processed_successfully, num_errors = 0, 0

    for index, current_file_path in enumerate(files):
        clean_file_path = current_file_path.strip("\"'") 
        original_filename = os.path.basename(clean_file_path)
        print(f"\n[{index + 1}/{num_total_files}] Processing: {original_filename}")

        trim_options_str = f"--trim {intro_trim_seconds}:{outtro_trim_seconds}" if intro_trim_seconds > 0 or outtro_trim_seconds > 0 else ""
        upscale_options_str = "--vpp-resize algo=nvvfx-superres,superres-mode=0 --output-res 2160x2160,preserve_aspect_ratio=increase" if perform_upscale else ""
        
        # Determine suffix based on upscale and TrueHDR (which implies HDR output)
        if perform_upscale:
            output_suffix = "_4K_HDR_AV1" if apply_truehdr_and_hdr_metadata else "_4K_AV1"
        else:
            output_suffix = "_HDR_AV1" if apply_truehdr_and_hdr_metadata else "_AV1"
            
        processed_filename = f"{os.path.splitext(original_filename)[0]}{output_suffix}.mkv"
        final_output_full_path = os.path.join(output_main_directory, processed_filename)

        if os.path.exists(final_output_full_path):
            print(f"Output file '{final_output_full_path}' already exists. Skipping."); continue

        truehdr_filter_str = ""
        hdr_metadata_list = []

        if apply_truehdr_and_hdr_metadata:
            truehdr_filter_str = "--vpp-ngx-truehdr maxluminance=1000,middlegray=18,saturation=200,contrast=200"
            hdr_metadata_list = ["--colormatrix", "bt2020nc", "--colorprim", "bt2020", "--transfer", "smpte2084"]
            print("  NGX TrueHDR and HDR Metadata ENABLED for this file.")
        else:
            print("  NGX TrueHDR and HDR Metadata DISABLED for this file.")

        command_parts_list = [
            "NVEncC64", "--avhw",
            trim_options_str,
            upscale_options_str, 
            truehdr_filter_str, # Will be empty if not applied
            "--codec", "av1", 
            "--profile", "main", 
            "--qvbr", str(qvbr_value_int), 
            "--preset", "p7", "--output-depth", "10",
            "--multipass", "2pass-full",
            "--gop-len", "auto", 
            "--aq", "--aq-temporal", "--aq-strength", "0",
        ]
        command_parts_list.extend(hdr_metadata_list) # Add these only if TrueHDR is on

        command_parts_list.extend([
            "--audio-codec", "ac3", "--audio-bitrate", "640",
            "--chapter-copy", "--key-on-chapter", "--metadata", "copy",
            "-i", f'"{clean_file_path}"', 
            "-o", f'"{final_output_full_path}"'
        ])
        
        final_command_elements = [part for part in command_parts_list if part and part.strip()] # Filter out empty or whitespace-only strings
        command_to_run_str = " ".join(final_command_elements)
        
        print(f"Executing: {command_to_run_str}")
        try:
            subprocess.run(command_to_run_str, shell=True, check=True, encoding='utf-8', errors='ignore')
            if os.path.exists(final_output_full_path) and os.path.getsize(final_output_full_path) > 0:
                print(f"Successfully processed: {final_output_full_path}")
                num_processed_successfully += 1
            else:
                print(f"Error: Output file not created or empty for '{original_filename}'.")
                num_errors += 1
        except subprocess.CalledProcessError as e_proc:
            print(f"Error processing '{original_filename}': NVEncC64 failed (code {e_proc.returncode}).")
            if e_proc.stderr: print(f"NVEncC64 STDERR: {e_proc.stderr}")
            num_errors += 1
        except Exception as e_unexpected:
            print(f"Unexpected error processing '{original_filename}': {e_unexpected}")
            num_errors += 1
        
        print(f"Overall progress: {int(((index + 1) / num_total_files) * 100)}%")

    print(f"\n--- Processing Summary ---\nTotal: {num_total_files}, Success: {num_processed_successfully}, Errors: {num_errors}\nProcessing complete.")

if __name__ == "__main__":
    print(f"Script initiated. Files will be scanned from/output relative to: {INITIAL_CWD}")
    try:
        gather_initial_files()
        show_gui()
    except Exception as e_main:
        print(f"Critical error in application: {e_main}")
        import traceback; traceback.print_exc()
    finally:
        if sys.platform == "win32":
            print("\nScript finished. Press Enter to exit.")
            input() # Keeps window open until Enter is pressed