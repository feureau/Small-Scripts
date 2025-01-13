import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import subprocess
import threading
from collections import Counter

class VideoProcessorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("NVEncC64 Video Processor")
        self.files = []
        self.crop_data = {}
        self.log_file = "processing_log.txt"

        # File list display with Treeview
        self.file_frame = tk.Frame(self.root)
        self.file_frame.pack(pady=10)

        columns = ("file_name", "width_crop", "height_crop")
        self.file_tree = ttk.Treeview(self.file_frame, columns=columns, show="headings", height=10)
        self.file_tree.heading("file_name", text="File Name")
        self.file_tree.heading("width_crop", text="Width Crop")
        self.file_tree.heading("height_crop", text="Height Crop")

        self.file_tree.column("file_name", width=300)
        self.file_tree.column("width_crop", width=100, anchor="center")
        self.file_tree.column("height_crop", width=100, anchor="center")
        self.file_tree.pack(side=tk.LEFT, fill=tk.BOTH)

        self.scrollbar = ttk.Scrollbar(self.file_frame, orient=tk.VERTICAL, command=self.file_tree.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_tree.configure(yscrollcommand=self.scrollbar.set)

        # Buttons for file selection
        self.add_files_button = tk.Button(self.root, text="Add Files", command=self.add_files)
        self.add_files_button.pack(pady=5)

        self.remove_files_button = tk.Button(self.root, text="Remove Selected", command=self.remove_selected_files)
        self.remove_files_button.pack(pady=5)

        # Cropdetect button
        self.crop_detect_button = tk.Button(self.root, text="Run Crop Detect", command=self.run_crop_detect)
        self.crop_detect_button.pack(pady=5)

        # Options section
        self.options_frame = tk.Frame(self.root)
        self.options_frame.pack(pady=10)

        tk.Label(self.options_frame, text="Decoding Mode:").grid(row=0, column=0, padx=5, sticky=tk.W)
        self.decode_mode = tk.StringVar(value="--avhw")
        tk.Radiobutton(self.options_frame, text="Hardware Decoding", variable=self.decode_mode, value="--avhw").grid(row=0, column=1, padx=5)
        tk.Radiobutton(self.options_frame, text="Software Decoding", variable=self.decode_mode, value="--avsw").grid(row=0, column=2, padx=5)

        self.hdr_enable = tk.BooleanVar(value=False)
        tk.Checkbutton(self.options_frame, text="Enable HDR Conversion", variable=self.hdr_enable).grid(row=1, column=0, columnspan=3, sticky=tk.W, padx=5)

        tk.Label(self.options_frame, text="Target Width:").grid(row=2, column=0, padx=5, sticky=tk.W)
        self.target_width = tk.Entry(self.options_frame, width=10)
        self.target_width.insert(0, "1080")
        self.target_width.grid(row=2, column=1, padx=5)

        tk.Label(self.options_frame, text="Target Height:").grid(row=2, column=2, padx=5, sticky=tk.W)
        self.target_height = tk.Entry(self.options_frame, width=10)
        self.target_height.insert(0, "1920")
        self.target_height.grid(row=2, column=3, padx=5)

        tk.Label(self.options_frame, text="GOP Length:").grid(row=3, column=0, padx=5, sticky=tk.W)
        self.gop_length = tk.Entry(self.options_frame, width=10)
        self.gop_length.insert(0, "6")
        self.gop_length.grid(row=3, column=1, padx=5)

        # Audio Options
        tk.Label(self.options_frame, text="Audio Handling:").grid(row=4, column=0, padx=5, sticky=tk.W)
        self.audio_option = tk.StringVar(value="copy")
        self.audio_convert_radio = tk.Radiobutton(self.options_frame, text="Convert to AC3", variable=self.audio_option, value="convert")
        self.audio_convert_radio.grid(row=4, column=1, padx=5)
        self.audio_copy_radio = tk.Radiobutton(self.options_frame, text="Copy Audio", variable=self.audio_option, value="copy")
        self.audio_copy_radio.grid(row=4, column=2, padx=5)

        # Start processing button
        self.start_button = tk.Button(self.root, text="Start Processing", command=self.start_processing)
        self.start_button.pack(pady=10)

        # Progress bar
        self.progress = ttk.Progressbar(self.root, orient="horizontal", length=300, mode="determinate")
        self.progress.pack(pady=10)
        self.status_label = tk.Label(self.root, text="Status: Idle")
        self.status_label.pack()

    def add_files(self):
        files = filedialog.askopenfilenames(filetypes=[("Video Files", "*.mp4 *.mkv *.avi *.mov")])
        for file in files:
            if file not in self.files:
                self.files.append(file)
                self.crop_data[file] = {"width_crop": "Full", "height_crop": "Full"}
                self.file_tree.insert("", "end", values=(os.path.basename(file), "Full", "Full"))

        self.check_audio_formats()

    def remove_selected_files(self):
        selected_items = self.file_tree.selection()
        for item in selected_items:
            values = self.file_tree.item(item, "values")
            file_name = values[0]
            for file in self.files:
                if os.path.basename(file) == file_name:
                    self.files.remove(file)
                    self.crop_data.pop(file, None)
                    break
            self.file_tree.delete(item)

        self.check_audio_formats()

    def run_crop_detect(self):
        selected_items = self.file_tree.selection()
        if not selected_items:
            messagebox.showerror("Error", "No files selected for crop detection.")
            return

        threading.Thread(
            target=self.perform_crop_detect,
            args=([self.files[int(self.file_tree.index(item))] for item in selected_items],),
            daemon=True
        ).start()

    def perform_crop_detect(self, files):
        for file in files:
            crop_params = self.get_crop_parameters(file)
            if crop_params:
                self.crop_data[file] = {
                    "width_crop": crop_params["width"],
                    "height_crop": crop_params["height"]
                }
                for item in self.file_tree.get_children():
                    if os.path.basename(file) == self.file_tree.item(item, "values")[0]:
                        self.file_tree.item(item, values=(
                            os.path.basename(file),
                            crop_params["width"],
                            crop_params["height"]
                        ))

    def get_crop_parameters(self, video_file):
        """Run FFmpeg cropdetect to determine optimal cropping parameters."""
        command = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", video_file]
        try:
            duration = float(subprocess.check_output(command, stderr=subprocess.STDOUT, text=True).strip())
        except Exception as e:
            self.log_error(f"Error retrieving video duration for {video_file}: {e}")
            return None

        sample_interval = max(10, duration // 12)  # Analyze at least 12 samples or one every 10 seconds
        crop_values = []

        for i in range(0, int(duration), int(sample_interval)):
            command = [
                "ffmpeg", "-ss", str(i), "-i", video_file, "-vframes", "1", "-vf",
                "cropdetect=64:4:0", "-f", "null", "-"
            ]
            try:
                process = subprocess.run(command, stderr=subprocess.PIPE, text=True, encoding="utf-8")
                stderr_output = process.stderr

                for line in stderr_output.splitlines():
                    if "crop=" in line:
                        crop_params = line.split("crop=")[-1].strip()
                        width, height, *_ = map(int, crop_params.split(":"))
                        crop_values.append({"width": width, "height": height})
                        break
            except Exception as e:
                self.log_error(f"Error during cropdetect at {i}s for {video_file}: {e}")

        if not crop_values:
            self.log_error(f"No crop parameters detected for {video_file}.")
            return None

        # Use the most common crop dimensions
        most_common_crop = Counter([(c["width"], c["height"]) for c in crop_values]).most_common(1)[0][0]
        return {"width": most_common_crop[0], "height": most_common_crop[1]}

    def check_audio_formats(self):
        """Check audio formats of all files and adjust the default audio option."""
        for file in self.files:
            command = ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=codec_name", "-of", "csv=p=0", file]
            try:
                output = subprocess.check_output(command, stderr=subprocess.STDOUT, text=True).strip()
                if any(codec.strip().lower() != "ac3" for codec in output.splitlines()):
                    self.audio_option.set("convert")
                    self.audio_convert_radio.select()
                    return
            except Exception as e:
                self.log_error(f"Error checking audio format for {file}: {e}")

        self.audio_option.set("copy")
        self.audio_copy_radio.select()

    def start_processing(self):
        if not self.files:
            messagebox.showerror("Error", "No files selected.")
            return

        # Retrieve options
        decode_flag = self.decode_mode.get()
        hdr_enabled = self.hdr_enable.get()
        target_width = self.target_width.get()
        target_height = self.target_height.get()
        gop_length = self.gop_length.get()

        # Validate options
        try:
            target_width = int(target_width)
            target_height = int(target_height)
            gop_length = int(gop_length)
        except ValueError:
            messagebox.showerror("Error", "Invalid input for width, height, or GOP length.")
            return

        self.progress["maximum"] = len(self.files)
        self.progress["value"] = 0
        self.status_label.config(text="Status: Processing...")

        # Start processing in a separate thread
        threading.Thread(
            target=self.process_videos,
            args=(self.files, decode_flag, hdr_enabled, target_width, target_height, gop_length),
            daemon=True
        ).start()

    def process_videos(self, files, decode_flag, hdr_enabled, target_width, target_height, gop_length):
        for index, file in enumerate(files):
            output_file = f"{os.path.splitext(file)[0]}_encoded.mkv"
            hdr_options = [
                "--vpp-ngx-truehdr", "--colormatrix", "bt2020nc", "--colorprim", "bt2020", "--transfer", "smpte2084"
            ] if hdr_enabled else []

            crop_option = self.crop_data.get(file, {"width_crop": "Full", "height_crop": "Full"})
            if crop_option["width_crop"] == "Full" and crop_option["height_crop"] == "Full":
                crop_args = []
            else:
                crop_args = ["--crop", f"{crop_option['width_crop']},{crop_option['height_crop']}"]

            audio_mode = self.audio_option.get()

            command = [
                "NVEncC64",
                decode_flag,
                "--codec", "av1",
                "--qvbr", "20",
                "--output-depth", "10",
                "--gop-len", str(gop_length),
                "--multipass", "2pass-full",
                "--preset", "p7",
                "--output-res", f"{target_width}x{target_height},preserve_aspect_ratio=increase",
                "-i", file,
                "-o", output_file
            ] + hdr_options + crop_args

            if audio_mode == "convert":
                command += ["--audio-codec", "ac3", "--audio-bitrate", "640", "--audio-stream", "0:5.1"]
            elif audio_mode == "copy":
                command += ["--audio-copy"]

            try:
                subprocess.run(command, check=True)
                self.log_message(f"Processing complete for: {file}")
            except subprocess.CalledProcessError as e:
                self.log_error(f"Failed to process {file}: {e}")

            self.progress["value"] = index + 1

        self.status_label.config(text="Status: Complete")
        messagebox.showinfo("Info", "All files processed.")

    def log_message(self, message):
        with open(self.log_file, "a") as log:
            log.write(f"INFO: {message}\n")

    def log_error(self, error):
        with open(self.log_file, "a") as log:
            log.write(f"ERROR: {error}\n")

if __name__ == "__main__":
    root = tk.Tk()
    app = VideoProcessorApp(root)
    root.mainloop()
