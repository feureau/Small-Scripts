import os
import sys
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinterdnd2 import DND_FILES, TkinterDnD
import concurrent.futures

# Default configuration values
files = []
default_intro_trim = 293
default_outtro_trim = 1131
default_qvbr_1080 = "22"  # Default QVBR value for 1080p
default_qvbr_4k = "33"    # Default QVBR value for 4K
default_concurrency = 1   # Default number of parallel processes

def process_cli_arguments():
    """
    Processes any file paths passed in via command line.
    Example: python script.py file1.mp4 file2.mp4
    """
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            if os.path.isfile(arg):
                files.append(os.path.abspath(arg))

def show_gui():
    """
    Creates and displays the Tkinter GUI, including:
      - File list management (add, remove, move up/down).
      - Intro/Outtro Trim settings.
      - QVBR value.
      - Resolution selection (1080p or 4K).
      - Number of parallel processes (concurrency).
      - Drag-and-drop support.
    """
    try:
        def refresh_listbox():
            listbox.delete(0, tk.END)
            for f in files:
                listbox.insert(tk.END, f)

        def add_files(new_files=None):
            if new_files is None:
                new_files = filedialog.askopenfilenames(title="Select files to process")
            for f in new_files:
                if os.path.isfile(f) and f not in files:
                    files.append(f)
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

        def update_qvbr(*args):
            """
            Automatically updates the QVBR field based on chosen resolution (1080 or 2160).
            """
            resolution = resolution_var.get()
            if resolution == "1080":
                qvbr_var.set(default_qvbr_1080)
            else:
                qvbr_var.set(default_qvbr_4k)

        def start_processing():
            """
            Gathers user inputs from the GUI and passes them to the processing function.
            """
            try:
                intro_trim = int(intro_trim_var.get()) if intro_trim_var.get() else default_intro_trim
                outtro_trim = int(outtro_trim_var.get()) if outtro_trim_var.get() else default_outtro_trim
                qvbr = int(qvbr_var.get()) if qvbr_var.get() else int(default_qvbr_1080)
                concurrency = int(concurrency_var.get()) if concurrency_var.get() else default_concurrency
            except ValueError:
                messagebox.showerror("Error", "Please enter valid integers for trim, QVBR, and concurrency.")
                return

            chosen_resolution = resolution_var.get()

            if not files:
                messagebox.showerror("Error", "No files selected.")
                return

            # Close the GUI
            root.destroy()
            # Start processing in console mode
            process_files(intro_trim, outtro_trim, qvbr, chosen_resolution, concurrency)

        def on_drop(event):
            # Convert dropped data to a list of file paths and add them
            dropped_files = root.splitlist(event.data)
            add_files(dropped_files)

        # Set up main window
        root = TkinterDnD.Tk()
        root.title("Video Processing Options")

        # File List Frame
        file_frame = tk.Frame(root)
        file_frame.pack(side="left", padx=10, pady=10)

        tk.Label(file_frame, text="Files to Process:").pack(anchor="w")
        listbox = tk.Listbox(file_frame, width=60, height=10)
        listbox.pack()

        # Enable drag-and-drop
        root.drop_target_register(DND_FILES)
        root.dnd_bind("<<Drop>>", on_drop)

        # Buttons to manage files
        button_frame = tk.Frame(root)
        button_frame.pack(side="left", padx=10, pady=10, fill="y")

        tk.Button(button_frame, text="Add Files", command=add_files).pack(fill="x", pady=5)
        tk.Button(button_frame, text="Clear Files", command=clear_files).pack(fill="x", pady=5)
        tk.Button(button_frame, text="Move Up", command=move_up).pack(fill="x", pady=5)
        tk.Button(button_frame, text="Move Down", command=move_down).pack(fill="x", pady=5)
        tk.Button(button_frame, text="Remove File", command=remove_file).pack(fill="x", pady=5)

        # Options Frame (right side)
        options_frame = tk.Frame(root)
        options_frame.pack(side="left", padx=10, pady=10, fill="y")

        # Intro Trim
        tk.Label(options_frame, text="Intro Trim (seconds):").pack(anchor="w")
        intro_trim_var = tk.StringVar(value=str(default_intro_trim))
        tk.Entry(options_frame, textvariable=intro_trim_var).pack(anchor="w")

        # Outtro Trim
        tk.Label(options_frame, text="Outtro Trim (seconds):").pack(anchor="w")
        outtro_trim_var = tk.StringVar(value=str(default_outtro_trim))
        tk.Entry(options_frame, textvariable=outtro_trim_var).pack(anchor="w")

        # QVBR Value
        tk.Label(options_frame, text="QVBR Value (1-51):").pack(anchor="w")
        qvbr_var = tk.StringVar(value=str(default_qvbr_1080))
        tk.Entry(options_frame, textvariable=qvbr_var).pack(anchor="w")

        # Resolution Radio Buttons
        tk.Label(options_frame, text="Output Resolution:").pack(anchor="w")
        resolution_var = tk.StringVar(value="1080")  # Default to 1080p
        resolution_var.trace_add("write", update_qvbr)  # Update QVBR if resolution changes

        res_1080 = tk.Radiobutton(options_frame, text="1080p (Full HD)", variable=resolution_var, value="1080")
        res_2160 = tk.Radiobutton(options_frame, text="4K (2160p)",      variable=resolution_var, value="2160")
        res_1080.pack(anchor="w")
        res_2160.pack(anchor="w")

        # Concurrency (Spinbox or Entry)
        tk.Label(options_frame, text="Parallel Processes:").pack(anchor="w")
        concurrency_var = tk.StringVar(value=str(default_concurrency))
        tk.Spinbox(options_frame, from_=1, to=16, textvariable=concurrency_var).pack(anchor="w")
        # or use tk.Entry if you prefer free-form input

        # Start Processing Button
        tk.Button(options_frame, text="Start Processing", command=start_processing).pack(pady=10)

        # Progress bar (optionally update it during processing)
        progress_label = tk.Label(options_frame, text="Progress:")
        progress_label.pack(anchor="w")
        progress_bar = ttk.Progressbar(options_frame, orient="horizontal", length=400, mode="determinate")
        progress_bar.pack(anchor="w", pady=5)

        # Populate listbox with any files we have so far
        refresh_listbox()

        root.mainloop()
    except Exception as e:
        print(f"An error occurred in the GUI: {e}")
        exit()

def encode_single_file(
    filepath,
    intro_trim,
    outtro_trim,
    qvbr,
    chosen_resolution
):
    """
    Encodes a single file using NVEncC64 command.
    Returns True if successful, or False otherwise.
    """
    # Trim flags
    trim_flags = f"--trim {intro_trim}:{outtro_trim}" if (intro_trim != 0 or outtro_trim != 0) else ""

    # Determine output resolution flags
    if chosen_resolution == "2160":
        # 4K
        suffix = "4K_HDR"
        upscale_flag = "--vpp-resize algo=nvvfx-superres,superres-mode=0 --output-res 2160x2160,preserve_aspect_ratio=increase"
    else:
        # 1080p
        suffix = "1080_HDR"
        upscale_flag = "--vpp-resize algo=nvvfx-superres,superres-mode=0 --output-res 1080x1080,preserve_aspect_ratio=increase"

    # Construct output filename
    output_file = f"{os.path.splitext(filepath)[0]}_{suffix}.mkv"

    # Build NVEncC64 command
    command = (
        f"NVEncC64 --avhw {trim_flags} --codec av1 --tier 1 --profile high --qvbr {qvbr} "
        f"--preset p7 --output-depth 10 --multipass 2pass-full --lookahead 32 --gop-len 4 --nonrefp "
        f"--aq --aq-temporal --aq-strength 0 --transfer auto --audio-codec ac3 --audio-bitrate 640 "
        f"--chapter-copy --key-on-chapter --metadata copy "
        f"--vpp-ngx-truehdr maxluminance=1000,middlegray=18,saturation=200,contrast=200 "
        f"--colormatrix bt2020nc --colorprim bt2020 --transfer smpte2084 {upscale_flag} "
        f"-i \"{filepath}\" -o \"{output_file}\""
    )

    try:
        subprocess.run(command, shell=True, check=True)
        if os.path.exists(output_file):
            # Create HDR folder next to the original file
            hdr_folder = os.path.join(os.path.dirname(filepath), "HDR")
            os.makedirs(hdr_folder, exist_ok=True)
            destination = os.path.join(hdr_folder, os.path.basename(output_file))
            os.rename(output_file, destination)
            print(f"Processed successfully: {destination}")
            return True
        else:
            print(f"Failed to process {filepath}")
            return False
    except subprocess.CalledProcessError as e:
        print(f"Error processing {filepath}: {e}")
        return False

def process_files(intro_trim, outtro_trim, qvbr, chosen_resolution, concurrency):
    """
    Uses ThreadPoolExecutor to run multiple NVEncC64 encodes in parallel (up to 'concurrency').
    """
    total_files = len(files)
    if total_files == 0:
        print("No files to process.")
        return

    print(f"Starting encoding of {total_files} files with concurrency={concurrency}...")

    completed = 0

    # We'll submit each file to the pool
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        # Map each file to a Future
        future_to_file = {
            executor.submit(
                encode_single_file,
                f.strip("\"'"),  # remove quotes if present
                intro_trim,
                outtro_trim,
                qvbr,
                chosen_resolution
            ): f for f in files
        }

        for future in concurrent.futures.as_completed(future_to_file):
            f = future_to_file[future]
            try:
                success = future.result()  # True/False from encode_single_file
            except Exception as e:
                print(f"Error processing {f}: {e}")
            finally:
                completed += 1
                progress_percent = int((completed / total_files) * 100)
                print(f"Completed {completed}/{total_files} ({progress_percent}%).")

    print("All files processed.")

def main():
    # 1. Attempt to get files from command-line
    process_cli_arguments()

    # 2. If no CLI arguments found, automatically gather *.mp4 from the current working directory
    if not files:
        current_folder = os.getcwd()
        mp4_in_folder = [
            os.path.join(current_folder, f) for f in os.listdir(current_folder)
            if f.lower().endswith(".mp4") and os.path.isfile(os.path.join(current_folder, f))
        ]
        if mp4_in_folder:
            files.extend(mp4_in_folder)

    # 3. If we still have no files, launch GUI so the user can pick them
    if not files:
        print("No files detected via command line or in the current folder. Launching GUI...")
        show_gui()

    # 4. If after GUI, still no files, exit
    if not files:
        print("No valid files were provided or selected. Exiting.")
        return

    # 5. Otherwise, we show the GUI for user to confirm settings (including concurrency).
    show_gui()

if __name__ == "__main__":
    main()
    # Prevent the script window from closing immediately after double-click
    os.system("pause")
