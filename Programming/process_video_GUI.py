import os
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox


def browse_files():
    """Opens a file dialog to select multiple video files and updates the input file field."""
    file_paths = filedialog.askopenfilenames(title="Select Video Files")
    if file_paths:
        input_file_entry.delete(0, tk.END)
        input_file_entry.insert(0, ";".join(file_paths))  # Use semicolon as a delimiter
        detect_metadata(file_paths[0])  # Detect resolution and audio tracks for the first selected file


def detect_metadata(file_path):
    """Uses FFprobe to detect resolution and audio track information of the given video file."""
    clear_audio_options()  # Clear any existing audio track options

    try:
        # Detect resolution
        resolution_result = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0", file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if resolution_result.returncode == 0:
            global detected_width, detected_height
            detected_width, detected_height = map(int, resolution_result.stdout.strip().split(","))
            detected_resolution_label.config(text=f"Detected Resolution: {detected_width}x{detected_height}")

            # Set default final resolutions to the detected resolution
            vertical_resolution_var.set(str(detected_height))
            horizontal_resolution_var.set(str(detected_width))

            # Apply crop presets based on resolution
            if detected_height == 1080:
                resize_to_4k_checkbox.config(state="disabled")  # Disable Resize to 4K
                artifact_reduction_checkbox.config(state="normal")  # Enable Artifact Reduction
                denoise_checkbox.config(state="normal")  # Enable Denoise
            elif detected_height == 2160:
                resize_to_4k_checkbox.config(state="normal")  # Enable Resize to 4K
                artifact_reduction_checkbox.config(state="disabled")  # Disable Artifact Reduction
                denoise_checkbox.config(state="disabled")  # Disable Denoise
            else:
                messagebox.showinfo("Warning", "Resolution not 1080p or 2160p. No special presets applied.")
        else:
            raise Exception(resolution_result.stderr.strip())

        # Detect audio tracks
        audio_result = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index,codec_name,channels,channel_layout,tags=language", "-of", "csv=p=0", file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if audio_result.returncode == 0:
            audio_tracks = audio_result.stdout.strip().split("\n")
            if audio_tracks:
                audio_tracks_label.config(text="Audio Tracks Detected:")
                for i, track_info in enumerate(audio_tracks):
                    parts = track_info.split(",")
                    track_index = parts[0] if len(parts) > 0 else "Unknown"
                    codec = parts[1] if len(parts) > 1 else "Unknown"
                    channels = parts[2] if len(parts) > 2 else "Unknown"
                    channel_layout = parts[3] if len(parts) > 3 else "Unknown"
                    language = parts[4] if len(parts) > 4 else "Unknown"

                    # Display options for each track
                    track_label = tk.Label(
                        audio_options_frame,
                        text=f"Track {track_index} ({codec}, Language: {language}, Channels: {channels}, Layout: {channel_layout})",
                    )
                    track_label.grid(row=i, column=0, sticky="w")

                    # Create radio buttons for options
                    option_var = tk.StringVar(value="copy" if i == 0 else "none")  # Default: Copy for first, None for others
                    tk.Radiobutton(audio_options_frame, text="Copy Audio", variable=option_var, value="copy").grid(row=i, column=1, sticky="w")
                    tk.Radiobutton(audio_options_frame, text="Convert to AC3", variable=option_var, value="ac3").grid(row=i, column=2, sticky="w")
                    tk.Radiobutton(audio_options_frame, text="Do Nothing", variable=option_var, value="none").grid(row=i, column=3, sticky="w")

                    # Save track metadata and option variable for processing later
                    audio_option_vars.append({"option_var": option_var, "channels": int(channels) if channels.isdigit() else 0})
            else:
                audio_tracks_label.config(text="Audio Tracks: None")
        else:
            raise Exception(audio_result.stderr.strip())

    except Exception as e:
        detected_resolution_label.config(text="Resolution Detection Failed")
        audio_tracks_label.config(text="Audio Detection Failed")
        messagebox.showerror("Error", f"Failed to detect metadata: {e}")


def calculate_crop(event=None):
    """Automatically calculates crop values when the resolution inputs are updated."""
    try:
        final_vertical = int(vertical_resolution_var.get())
        final_horizontal = int(horizontal_resolution_var.get())

        if final_vertical > detected_height or final_horizontal > detected_width:
            status_box.insert(tk.END, "Error: Final resolution cannot be larger than the detected resolution.\n")
            return

        # Calculate the crop values
        top_crop = (detected_height - final_vertical) // 2
        bottom_crop = detected_height - final_vertical - top_crop
        left_crop = (detected_width - final_horizontal) // 2
        right_crop = detected_width - final_horizontal - left_crop

        # Log crop calculation
        status_box.insert(tk.END, f"Crop calculated: Top={top_crop}, Bottom={bottom_crop}, Left={left_crop}, Right={right_crop}\n")
    except ValueError:
        status_box.insert(tk.END, "Error: Please enter valid numeric values for the final resolution.\n")


def clear_audio_options():
    """Clears all dynamically created audio track options."""
    for widget in audio_options_frame.winfo_children():
        widget.destroy()
    audio_option_vars.clear()


def process_videos():
    """Placeholder for processing videos. Logs updates to the status box."""
    status_box.insert(tk.END, "Processing videos...\n")
    # Here you would implement the video processing logic and update the status box with progress.


# GUI Setup
root = tk.Tk()
root.title("Batch Video Processing GUI")

# Input Files Section
tk.Label(root, text="Input Files:").grid(row=0, column=0, sticky="w")
input_file_entry = tk.Entry(root, width=50)
input_file_entry.grid(row=0, column=1, sticky="w")
browse_button = tk.Button(root, text="Browse", command=browse_files)
browse_button.grid(row=0, column=2, sticky="w")

# Resolution Label
detected_resolution_label = tk.Label(root, text="Detected Resolution: Not Available")
detected_resolution_label.grid(row=1, column=0, columnspan=3, sticky="w")

# Final Resolution Input
tk.Label(root, text="Vertical Res:").grid(row=2, column=0, sticky="e")
vertical_resolution_var = tk.StringVar(value="0")
tk.Entry(root, textvariable=vertical_resolution_var).grid(row=2, column=1, sticky="w")
tk.Label(root, text="Horizontal Res:").grid(row=3, column=0, sticky="e")
horizontal_resolution_var = tk.StringVar(value="0")
tk.Entry(root, textvariable=horizontal_resolution_var).grid(row=3, column=1, sticky="w")

# Bind inputs to automatically calculate crop
vertical_resolution_var.trace_add("write", calculate_crop)
horizontal_resolution_var.trace_add("write", calculate_crop)

# Audio Tracks Section
audio_tracks_label = tk.Label(root, text="Audio Tracks: Not Available")
audio_tracks_label.grid(row=4, column=0, columnspan=3, sticky="w")

# Audio Options
audio_options_frame = tk.Frame(root)
audio_options_frame.grid(row=5, column=0, columnspan=3, sticky="w")
audio_option_vars = []  # Store variables for audio options

# Additional Processing Options
resize_option = tk.BooleanVar(value=False)
resize_to_4k_checkbox = tk.Checkbutton(root, text="Enable Resize to 4K", variable=resize_option, state="disabled")
resize_to_4k_checkbox.grid(row=6, column=0, columnspan=3, sticky="w")

artifact_reduction_option = tk.BooleanVar(value=False)
artifact_reduction_checkbox = tk.Checkbutton(root, text="Enable Artifact Reduction", variable=artifact_reduction_option)
artifact_reduction_checkbox.grid(row=7, column=0, columnspan=3, sticky="w")

denoise_option = tk.BooleanVar(value=False)
denoise_checkbox = tk.Checkbutton(root, text="Enable Denoise", variable=denoise_option)
denoise_checkbox.grid(row=8, column=0, columnspan=3, sticky="w")

# Process Button
process_button = tk.Button(root, text="Process Videos", command=process_videos)
process_button.grid(row=9, column=0, columnspan=3, pady=10)

# Status Box
status_box = tk.Text(root, height=10, width=70)
status_box.grid(row=10, column=0, columnspan=3, padx=10, pady=10)

# Run GUI
root.mainloop()
