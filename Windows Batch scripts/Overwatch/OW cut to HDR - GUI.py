import os
import sys
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinterdnd2 import DND_FILES, TkinterDnD

# Default configuration values
files = []
default_intro_trim = 293
default_outtro_trim = 1131
default_qvbr = "28"  # Default QVBR value for standard resolution
default_qvbr_4k = "38"  # Default QVBR value for 4K

# Function to process command-line arguments (drag-and-drop files)
def process_cli_arguments():
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            if os.path.isfile(arg):
                files.append(arg)

# GUI for file selection and options
def show_gui():
    try:
        def refresh_listbox():
            listbox.delete(0, tk.END)
            for file in files:
                listbox.insert(tk.END, file)

        def add_files(new_files=None):
            if new_files is None:
                new_files = filedialog.askopenfilenames(title="Select files to process")
            for file in new_files:  # Iterate over the list or tuple
                if os.path.isfile(file) and file not in files:
                    files.append(file)
            refresh_listbox()

        def clear_files():
            files.clear()
            refresh_listbox()

        def move_up():
            selected = listbox.curselection()
            if not selected or selected[0] == 0:
                return
            idx = selected[0]
            files[idx - 1], files[idx] = files[idx], files[idx - 1]
            refresh_listbox()
            listbox.selection_set(idx - 1)

        def move_down():
            selected = listbox.curselection()
            if not selected or selected[0] == len(files) - 1:
                return
            idx = selected[0]
            files[idx + 1], files[idx] = files[idx], files[idx + 1]
            refresh_listbox()
            listbox.selection_set(idx + 1)

        def remove_file():
            selected = listbox.curselection()
            if not selected:
                return
            idx = selected[0]
            del files[idx]
            refresh_listbox()

        def update_qvbr():
            if upscale_var.get():
                qvbr_var.set(default_qvbr_4k)  # Set QVBR value to 38 for 4K
            else:
                qvbr_var.set(default_qvbr)  # Reset QVBR value to standard resolution

        def start_processing():
            intro_trim = int(intro_trim_var.get()) if intro_trim_var.get() else default_intro_trim
            outtro_trim = int(outtro_trim_var.get()) if outtro_trim_var.get() else default_outtro_trim
            qvbr = int(qvbr_var.get()) if qvbr_var.get() else default_qvbr
            upscale = upscale_var.get()

            if not files:
                messagebox.showerror("Error", "No files selected.")
                return

            root.destroy()
            process_files(intro_trim, outtro_trim, qvbr, upscale)

        def on_drop(event):
            dropped_files = root.splitlist(event.data)  # Convert dropped data to a list of file paths
            add_files(dropped_files)

        root = TkinterDnD.Tk()
        root.title("Video Processing Options")

        # File list
        file_frame = tk.Frame(root)
        file_frame.pack(side="left", padx=10, pady=10)

        tk.Label(file_frame, text="Files to Process:").pack(anchor="w")
        listbox = tk.Listbox(file_frame, width=60, height=10)
        listbox.pack()

        # Enable drag-and-drop file addition
        root.drop_target_register(DND_FILES)
        root.dnd_bind("<<Drop>>", on_drop)

        # Buttons next to the file list
        button_frame = tk.Frame(root)
        button_frame.pack(side="left", padx=10, pady=10)

        tk.Button(button_frame, text="Add Files", command=add_files).pack(fill="x", pady=5)
        tk.Button(button_frame, text="Clear Files", command=clear_files).pack(fill="x", pady=5)
        tk.Button(button_frame, text="Move Up", command=move_up).pack(fill="x", pady=5)
        tk.Button(button_frame, text="Move Down", command=move_down).pack(fill="x", pady=5)
        tk.Button(button_frame, text="Remove File", command=remove_file).pack(fill="x", pady=5)

        # Options
        tk.Label(root, text="Intro Trim (seconds):").pack(anchor="w")
        intro_trim_var = tk.StringVar(value=str(default_intro_trim))
        tk.Entry(root, textvariable=intro_trim_var).pack(anchor="w")

        tk.Label(root, text="Outtro Trim (seconds):").pack(anchor="w")
        outtro_trim_var = tk.StringVar(value=str(default_outtro_trim))
        tk.Entry(root, textvariable=outtro_trim_var).pack(anchor="w")

        tk.Label(root, text="QVBR Value (1-51):").pack(anchor="w")
        qvbr_var = tk.StringVar(value=str(default_qvbr))
        tk.Entry(root, textvariable=qvbr_var).pack(anchor="w")

        upscale_var = tk.BooleanVar()
        tk.Checkbutton(root, text="Convert to 4K", variable=upscale_var, command=update_qvbr).pack(anchor="w")

        # Start button
        tk.Button(root, text="Start Processing", command=start_processing).pack(pady=10)

        # Progress bar
        progress_label = tk.Label(root, text="Progress:")
        progress_label.pack(anchor="w")
        progress_bar = ttk.Progressbar(root, orient="horizontal", length=400, mode="determinate")
        progress_bar.pack(anchor="w", pady=5)

        # Populate listbox with files dragged and dropped before GUI launch
        refresh_listbox()

        root.mainloop()
    except Exception as e:
        print(f"An error occurred in the GUI: {e}")
        exit()

# Function to process files
def process_files(intro_trim, outtro_trim, qvbr, upscale):
    total_files = len(files)
    progress = 0

    for file in files:
        file = file.strip("\"'")  # Strip quotes if dragged-and-dropped
        print(f"Processing: {file}")

        trim_flags = f"--trim {intro_trim}:{outtro_trim}" if intro_trim != 0 or outtro_trim != 0 else ""
        upscale_flag = "--vpp-resize algo=nvvfx-superres,superres-mode=0 --output-res 2160x2160,preserve_aspect_ratio=increase" if upscale else ""

        suffix = "4K_HDR" if upscale else "HDR"
        output_file = f"{os.path.splitext(file)[0]}_{suffix}.mkv"

        command = (
            f"NVEncC64 --avhw {trim_flags} --codec av1 --tier 1 --profile high --qvbr {qvbr} --preset p7 --output-depth 10 "
            f"--multipass 2pass-full --lookahead 32 --gop-len 4 --nonrefp --aq --aq-temporal --aq-strength 0 "
            f"--transfer auto --audio-codec ac3 --audio-bitrate 640 --chapter-copy --key-on-chapter --metadata copy "
            f"--vpp-ngx-truehdr maxluminance=1000,middlegray=18,saturation=200,contrast=200 "
            f"--colormatrix bt2020nc --colorprim bt2020 --transfer smpte2084 {upscale_flag} -i \"{file}\" -o \"{output_file}\""
        )

        try:
            subprocess.run(command, shell=True, check=True)
            if os.path.exists(output_file):
                hdr_folder = os.path.join(os.path.dirname(file), "HDR")
                os.makedirs(hdr_folder, exist_ok=True)
                destination = os.path.join(hdr_folder, os.path.basename(output_file))
                os.rename(output_file, destination)
                print(f"Processed successfully: {destination}")
            else:
                print(f"Failed to process {file}")
        except subprocess.CalledProcessError as e:
            print(f"Error processing {file}: {e}")

        # Update progress
        progress += 1
        progress_percent = int((progress / total_files) * 100)
        print(f"Progress: {progress_percent}%")

    print("Processing complete.")

# Main function
try:
    # Handle drag-and-drop or manual GUI selection
    process_cli_arguments()
    if not files:
        print("No files detected via drag-and-drop. Launching GUI...")
    show_gui()

    if not files:
        print("No valid files provided. Exiting.")
        exit()
except Exception as e:
    print(f"An unexpected error occurred: {e}")
    exit()

# Prevent the script from closing immediately after double-click
os.system("pause")
