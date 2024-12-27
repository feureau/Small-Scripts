import os
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinterdnd2 import TkinterDnD, DND_FILES

class VideoProcessorApp:
    def __init__(self, root, initial_files):
        self.root = root
        self.root.title("Video Processing Tool")
        self.file_list = []

        # Enable Drag-and-Drop Support
        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind("<<Drop>>", self.handle_file_drop)

        # File Listbox
        self.file_frame = tk.Frame(root)
        self.file_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.file_listbox = tk.Listbox(self.file_frame, selectmode=tk.EXTENDED, height=15)
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.file_scrollbar = tk.Scrollbar(self.file_frame, orient=tk.VERTICAL, command=self.file_listbox.yview)
        self.file_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_listbox.config(yscrollcommand=self.file_scrollbar.set)

        # Populate initial files
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
        # Options Section
        self.options_frame = tk.Frame(root)
        self.options_frame.pack(fill=tk.X, padx=10, pady=10)

        tk.Label(self.options_frame, text="Resolution:").grid(row=0, column=0, sticky=tk.W)
        self.resolution_var = tk.StringVar(value="4k")
        self.res_4k_button = tk.Radiobutton(self.options_frame, text="4k", variable=self.resolution_var, value="4k", command=self.update_qvbr)
        self.res_4k_button.grid(row=0, column=1, sticky=tk.W)
        self.res_8k_button = tk.Radiobutton(self.options_frame, text="8k", variable=self.resolution_var, value="8k", command=self.update_qvbr)
        self.res_8k_button.grid(row=0, column=2, sticky=tk.W)

        tk.Label(self.options_frame, text="Upscale:").grid(row=1, column=0, sticky=tk.W)
        self.upscale_var = tk.BooleanVar(value=True)
        self.upscale_checkbox = tk.Checkbutton(self.options_frame, variable=self.upscale_var)
        self.upscale_checkbox.grid(row=1, column=1, sticky=tk.W)

        tk.Label(self.options_frame, text="Vertical Crop:").grid(row=2, column=0, sticky=tk.W)
        self.crop_var = tk.BooleanVar(value=False)
        self.crop_checkbox = tk.Checkbutton(self.options_frame, variable=self.crop_var)
        self.crop_checkbox.grid(row=2, column=1, sticky=tk.W)

        tk.Label(self.options_frame, text="QVBR Value:").grid(row=3, column=0, sticky=tk.W)
        self.qvbr_var = tk.StringVar(value="18")
        self.qvbr_entry = tk.Entry(self.options_frame, textvariable=self.qvbr_var, width=10)
        self.qvbr_entry.grid(row=3, column=1, sticky=tk.W)

        tk.Label(self.options_frame, text="Enable FRUC:").grid(row=4, column=0, sticky=tk.W)
        self.fruc_var = tk.BooleanVar(value=False)
        self.fruc_checkbox = tk.Checkbutton(self.options_frame, variable=self.fruc_var, command=self.toggle_fruc_fps)
        self.fruc_checkbox.grid(row=4, column=1, sticky=tk.W)

        tk.Label(self.options_frame, text="FRUC FPS Target:").grid(row=5, column=0, sticky=tk.W)
        self.fruc_fps_var = tk.StringVar(value="60")
        self.fruc_fps_entry = tk.Entry(self.options_frame, textvariable=self.fruc_fps_var, width=10)
        self.fruc_fps_entry.grid(row=5, column=1, sticky=tk.W)
        self.fruc_fps_entry.configure(state="disabled")

        # Start Processing Button
        self.start_button = tk.Button(root, text="Start Processing", command=self.start_processing)
        self.start_button.pack(pady=10)
    def add_files(self):
        files = filedialog.askopenfilenames(filetypes=[("Video Files", "*.mp4;*.mkv;*.avi"), ("All Files", "*.*")])
        self.update_file_list(files)

    def handle_file_drop(self, event):
        files = self.root.tk.splitlist(event.data)  # Split dropped files
        self.update_file_list(files)

    def update_file_list(self, files):
        for file in files:
            if file not in self.file_list:
                self.file_list.append(file)
                self.file_listbox.insert(tk.END, file)

    def remove_selected(self):
        selected_indices = list(self.file_listbox.curselection())
        for index in reversed(selected_indices):
            del self.file_list[index]
            self.file_listbox.delete(index)

    def clear_all(self):
        self.file_list.clear()
        self.file_listbox.delete(0, tk.END)

    def move_up(self):
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

    def move_down(self):
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
    def update_qvbr(self):
        if self.resolution_var.get() == "4k":
            self.qvbr_var.set("18")
        else:
            self.qvbr_var.set("28")

    def toggle_fruc_fps(self):
        if self.fruc_var.get():
            self.fruc_fps_entry.configure(state="normal")
        else:
            self.fruc_fps_entry.configure(state="disabled")

    def apply_hdr_settings(self, file_path):
        """Apply HDR settings using mkvmerge and delete the input file."""
        hdr_file = os.path.splitext(file_path)[0] + "_HDR.mkv"
        lut_path = r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\LUT\Colorspace LUTS\5-NBCU_PQ2SDR_DL_RESOLVE17-VRT_v1.2.cube"

        try:
            if not os.path.exists(lut_path):
                raise FileNotFoundError(f"LUT file not found: {lut_path}")

            cmd = [
                "mkvmerge", "-o", hdr_file,
                "--colour-matrix", "0:9", "--colour-range", "0:1",
                "--colour-transfer-characteristics", "0:16", "--colour-primaries", "0:9",
                "--max-content-light", "0:1000", "--max-frame-light", "0:300",
                "--max-luminance", "0:1000", "--min-luminance", "0:0.01",
                "--attachment-mime-type", "application/x-cube",
                "--attach-file", lut_path,
                file_path
            ]

            print(f"Applying HDR settings with command: {' '.join(cmd)}")
            subprocess.run(cmd, check=True)
            print(f"HDR settings applied to: {hdr_file}")

            # Delete the input file after HDR settings are applied
            if os.path.exists(hdr_file):
                os.remove(file_path)
                print(f"Deleted original file: {file_path}")
            else:
                print(f"HDR file not created, original file retained: {file_path}")

            return hdr_file
        except subprocess.CalledProcessError as e:
            print(f"Error applying HDR settings: {e}")
            return file_path
        except Exception as ex:
            print(f"Unexpected error: {ex}")
            return file_path
    def start_processing(self):
        if not self.file_list:
            messagebox.showwarning("No Files", "Please add at least one file to process.")
            return

        resolution = self.resolution_var.get()
        upscale_only = "y" if self.upscale_var.get() else "n"
        vertical_crop = "y" if self.crop_var.get() else "n"
        qvbr_value = self.qvbr_var.get()
        fruc_enable = "y" if self.fruc_var.get() else "n"
        fruc_fps_target = self.fruc_fps_var.get()

        try:
            qvbr_value = int(qvbr_value)
            fruc_fps_target = int(fruc_fps_target)
        except ValueError:
            messagebox.showerror("Invalid Input", "QVBR and FRUC FPS Target must be integers.")
            return

        self.root.destroy()  # Close the GUI

        for file_path in self.file_list:
            output_dir = os.path.join(os.path.dirname(file_path), resolution)
            os.makedirs(output_dir, exist_ok=True)

            output_file = os.path.join(output_dir, os.path.basename(file_path))
            cmd = [
                "NVEncC64", "--avhw", "--codec", "av1", "--qvbr", str(qvbr_value),
                "--preset", "p1", "--output-depth", "10", "--audio-copy", "--sub-copy",
                "--chapter-copy", "--key-on-chapter", "--transfer", "auto", "--colorprim", "auto",
                "--colormatrix", "auto", "--lookahead", "32", "--aq-temporal",
                "--multipass", "2pass-full", "--log-level", "info",
                "--output", output_file, "-i", file_path
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

            try:
                print(f"Processing started for: {file_path}")
                subprocess.run(cmd, check=True)  # Allow output to show in the console
                print(f"Processing complete for: {file_path}")

                # Apply HDR settings with mkvmerge
                hdr_output = self.apply_hdr_settings(output_file)
                print(f"HDR applied to: {hdr_output}")
            except subprocess.CalledProcessError as e:
                print(f"Error processing {file_path}: {e}")

        print("Processing Complete.")
        os.system("pause")  # Wait for any key press before exiting

if __name__ == "__main__":
    import sys
    initial_files = sys.argv[1:] if len(sys.argv) > 1 else []
    root = TkinterDnD.Tk()  # Use TkinterDnD for drag-and-drop
    app = VideoProcessorApp(root, initial_files)
    root.mainloop()
