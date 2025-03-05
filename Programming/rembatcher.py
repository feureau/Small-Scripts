import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import sys
import os
import glob
import subprocess

# -------------------------------
# Configuration - Customize these:
# -------------------------------
# Hardcoded location for the rembg executable.
REMBG_CMD = r"F:\AI\rembg\venv\Scripts\rembg.exe"

# List of rembg models (sorted alphabetically)
MODELS = [
    'birefnet-general',
    'birefnet-general-lite',
    'birefnet-portrait',
    'birefnet-dis',
    'birefnet-hrsod',
    'birefnet-cod',
    'birefnet-massive',
    'isnet-anime',
    'isnet-general-use',
    'sam',
    'silueta',
    'u2net_cloth_seg',
    'u2net_custom',
    'u2net_human_seg',
    'u2net',
    'u2netp',
    'bria-rmbg'
]
MODELS.sort()

# Name of the output subdirectory (within the working folder)
OUTPUT_DIR_NAME = "transp"
# -------------------------------
# End Configuration
# -------------------------------

def run_gui():
    # The working folder is the directory from which the script is called.
    working_dir = os.getcwd()
    selections = {"files": [], "models": []}
    
    root = tk.Tk()
    root.title("Rembatcher")
    
    # Main frame with vertical layout
    main_frame = ttk.Frame(root, padding=10)
    main_frame.pack(fill="both", expand=True)
    
    # ----- File Frame (top) -----
    file_frame = ttk.LabelFrame(main_frame, text="Files in " + working_dir)
    file_frame.pack(fill="both", expand=True, padx=5, pady=5)
    
    file_listbox = tk.Listbox(file_frame, selectmode=tk.MULTIPLE, width=60, height=10)
    file_listbox.pack(side="top", fill="both", expand=True, padx=5, pady=5)
    
    file_scrollbar = ttk.Scrollbar(file_frame, orient="vertical", command=file_listbox.yview)
    file_scrollbar.pack(side="right", fill="y")
    file_listbox.config(yscrollcommand=file_scrollbar.set)
    
    # Expand wildcards in command-line arguments using glob.
    file_args = []
    for arg in sys.argv[1:]:
        if '*' in arg or '?' in arg:
            file_args.extend(glob.glob(arg))
        else:
            file_args.append(arg)
    
    # Populate file listbox from the expanded file arguments.
    for f in file_args:
        file_listbox.insert(tk.END, f)
    
    # File management buttons
    file_button_frame = ttk.Frame(file_frame)
    file_button_frame.pack(fill="x", padx=5, pady=5)
    
    def add_files():
        files = filedialog.askopenfilenames(title="Select Files", initialdir=working_dir)
        for f in files:
            file_listbox.insert(tk.END, os.path.basename(f))
    
    def remove_selected_files():
        for index in reversed(file_listbox.curselection()):
            file_listbox.delete(index)
    
    def select_all_files():
        file_listbox.select_set(0, tk.END)
    
    def deselect_all_files():
        file_listbox.select_clear(0, tk.END)
    
    def clear_files():
        file_listbox.delete(0, tk.END)
    
    ttk.Button(file_button_frame, text="Add", command=add_files).pack(side="left", padx=2)
    ttk.Button(file_button_frame, text="Remove", command=remove_selected_files).pack(side="left", padx=2)
    ttk.Button(file_button_frame, text="Select All", command=select_all_files).pack(side="left", padx=2)
    ttk.Button(file_button_frame, text="Deselect All", command=deselect_all_files).pack(side="left", padx=2)
    ttk.Button(file_button_frame, text="Clear All", command=clear_files).pack(side="left", padx=2)
    
    # ----- Model Frame (middle) -----
    model_frame = ttk.LabelFrame(main_frame, text="Models")
    model_frame.pack(fill="both", expand=True, padx=5, pady=5)
    
    # Use a frame directly for the checkbuttons.
    model_check_frame = ttk.Frame(model_frame)
    model_check_frame.pack(fill="both", expand=True, padx=5, pady=5)
    
    model_vars = {}
    for m in MODELS:
        # Set 'bria-rmbg' as selected by default.
        initial_value = True if m == "bria-rmbg" else False
        var = tk.BooleanVar(value=initial_value)
        chk = ttk.Checkbutton(model_check_frame, text=m, variable=var)
        chk.pack(anchor="w")
        model_vars[m] = var
    
    # Model selection buttons (below the checkbuttons)
    model_button_frame = ttk.Frame(model_frame)
    model_button_frame.pack(fill="x", padx=5, pady=5)
    
    def select_all_models():
        for var in model_vars.values():
            var.set(True)
    
    def deselect_all_models():
        for var in model_vars.values():
            var.set(False)
    
    ttk.Button(model_button_frame, text="Select All Models", command=select_all_models).pack(side="left", padx=5)
    ttk.Button(model_button_frame, text="Deselect All Models", command=deselect_all_models).pack(side="left", padx=5)
    
    # ----- Process Button (bottom) -----
    def on_process():
        selections["files"] = file_listbox.get(0, tk.END)
        selections["models"] = [model for model, var in model_vars.items() if var.get()]
        # Immediately close the GUI.
        root.destroy()
    
    process_button = ttk.Button(root, text="Process", command=on_process)
    process_button.pack(pady=10)
    
    # Dynamically size the window based on its contents.
    root.update_idletasks()
    req_width = root.winfo_reqwidth()
    req_height = root.winfo_reqheight()
    root.geometry(f"{req_width}x{req_height}")
    
    root.mainloop()
    return selections, working_dir

def main():
    selections, working_dir = run_gui()
    if not selections["files"]:
        print("No files selected for processing.")
        return
    if not selections["models"]:
        print("No models selected. Exiting.")
        return
    
    # Create output subdirectory in the working folder.
    output_dir = os.path.join(working_dir, OUTPUT_DIR_NAME)
    os.makedirs(output_dir, exist_ok=True)
    
    # Process each file with each selected model.
    for f in selections["files"]:
        input_file = os.path.join(working_dir, f)
        base, _ = os.path.splitext(os.path.basename(f))
        for model in selections["models"]:
            output_file = os.path.join(output_dir, f"{base}_{model}_T.png")
            cmd = [REMBG_CMD, "i", "--model", model, input_file, output_file]
            print(f"\nProcessing {f} with model {model}...", flush=True)
            print("Running command:", " ".join(cmd), flush=True)
            try:
                subprocess.run(cmd, check=True)
                print(f"Finished processing {f} with model {model}.", flush=True)
            except subprocess.CalledProcessError as e:
                print(f"Error processing {f} with model {model}:\n{e}", flush=True)
            except FileNotFoundError as e:
                print(f"Executable not found: {e}", flush=True)
                return
    
    print("\nAll processing complete. Processed files are in:", output_dir)

if __name__ == '__main__':
    main()
