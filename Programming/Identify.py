import sys
import re
import os
import tkinter as tk
from tkinter import scrolledtext, messagebox

def identify_speakers_srt(srt_filepath, custom_speaker_map):
    """
    Replaces speaker labels in an SRT file with identified names and occupations
    using a provided custom speaker map.
    Saves the modified content to a new SRT file.

    Args:
        srt_filepath (str): The path to the input SRT file.
        custom_speaker_map (dict): A dictionary containing speaker label mappings.
    """

    try:
        with open(srt_filepath, 'r', encoding='utf-8') as srt_file:
            srt_content = srt_file.readlines()
    except FileNotFoundError:
        messagebox.showerror("Error", f"SRT file not found at '{srt_filepath}'")
        return

    modified_lines = []
    for line in srt_content:
        speaker_match = re.match(r'\[(SPEAKER_\d+)\]: (.*)', line)
        if speaker_match:
            speaker_label = speaker_match.group(1)
            dialogue = speaker_match.group(2)
            if speaker_label in custom_speaker_map:
                modified_speaker = custom_speaker_map[speaker_label]
                modified_line = f"[{modified_speaker}]: {dialogue}"
                modified_lines.append(modified_line + '\n')
            else:
                modified_lines.append(line) # Keep original if speaker not in map
        else:
            modified_lines.append(line)

    # Create output file path
    base, ext = os.path.splitext(srt_filepath)
    output_filepath = f"{base}.speaker_identified{ext}"

    try:
        with open(output_filepath, 'w', encoding='utf-8') as output_file:
            output_file.writelines(modified_lines)
        messagebox.showinfo("Success", f"Modified SRT saved to: '{output_filepath}'")
    except Exception as e:
        messagebox.showerror("Error", f"Error writing to output file '{output_filepath}': {e}")

def parse_speaker_map_text(map_text):
    """
    Parses the pasted speaker map text into a dictionary.

    Args:
        map_text (str): The text from the GUI text area.

    Returns:
        dict: A dictionary with speaker labels as keys and names as values, or None if parsing fails.
    """
    speaker_map = {}
    lines = map_text.strip().split('\n')
    for line in lines:
        line = line.strip()
        if not line or line.startswith('*'): # Skip empty lines and list bullets
            continue
        match = re.match(r'\*\*?(SPEAKER_\d+)\*\*?:\s*(.*)', line) #Handles bolding variations
        if match:
            speaker_label = match.group(1)
            speaker_name = match.group(2).strip()
            speaker_map[speaker_label] = speaker_name
        elif line.startswith('**'): # error handling if bold format is wrong
            messagebox.showerror("Error", f"Invalid speaker mapping format in line:\n'{line}'.\nUse format like: **SPEAKER_00**: Speaker Name")
            return None
        elif ':' in line: # basic fallback if no bolding intended but colon exists
            parts = line.split(':', 1)
            speaker_label = parts<source_id data="0" title="FULL VIDEO： President Donald Trump's meeting with Ukraine President Zelenskyy turns tense [um19Mf4dYes].830cb1e7-78a8-48f8-882c-199035df5869.srt" />.strip()
            speaker_name = parts[1].strip()
            if re.match(r'SPEAKER_\d+', speaker_label):
                speaker_map[speaker_label] = speaker_name
            else:
                messagebox.showerror("Error", f"Invalid speaker label format in line: '{line}'. Expected 'SPEAKER_XX:'")
                return None


    return speaker_map

def process_srt_gui():
    srt_file_path = srt_file_entry.get()
    map_text = speaker_map_text_area.get("1.0", tk.END) # Get text from Text area

    if not os.path.exists(srt_file_path):
        messagebox.showerror("Error", f"SRT file not found: '{srt_file_path}'")
        return

    custom_map = parse_speaker_map_text(map_text)
    if custom_map:
        identify_speakers_srt(srt_file_path, custom_map)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: Identify.py Full_video.srt")
        print("       A GUI will open to paste speaker mappings.")
        sys.exit(1)

    srt_file = sys.argv[1]

    window = tk.Tk()
    window.title("SRT Speaker Identifier")

    tk.Label(window, text="SRT File Path:").pack(pady=5)
    srt_file_entry = tk.Entry(window, width=50)
    srt_file_entry.insert(0, srt_file) # Pre-fill with command line argument
    srt_file_entry.pack(pady=5)


    tk.Label(window, text="Paste Speaker Mappings (Format: **SPEAKER_XX**: Speaker Name):").pack(pady=5)
    speaker_map_text_area = scrolledtext.ScrolledText(window, height=10, width=60)
    speaker_map_text_area.pack(pady=10)

    process_button = tk.Button(window, text="Process SRT", command=process_srt_gui)
    process_button.pack(pady=10)

    window.mainloop()