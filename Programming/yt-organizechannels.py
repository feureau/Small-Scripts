import os
import shutil
import re
import sys

def clean_folder_name(name):
    """
    Removes characters that are illegal in Windows folder names 
    (though fullwidth characters like ｜ and ： are usually fine).
    Standard illegal: < > : " / \\ | ? *
    """
    # Replace standard illegal characters just in case
    forbidden = [('<', ''), ('>', ''), (':', ' -'), ('"', '\''), 
                 ('/', '-'), ('\\', '-'), ('|', '-'), ('?', ''), ('*', '')]
    
    cleaned = name
    for char, replacement in forbidden:
        cleaned = cleaned.replace(char, replacement)
    return cleaned.strip()

def organize_files():
    # Get the current working directory (where the script is executed from)
    current_dir = os.getcwd()
    
    print(f"Scanning directory: {current_dir}")
    print("-" * 50)

    # Regex to find: [Channel Name] - [Date 20xxxxxx] - 
    # Logic: Look for text at the start, followed by " - 20" then 6 digits then " - "
    # We use 20\d{6} to ensure we match the years 2025, 2026, etc.
    pattern = re.compile(r"^(.*?) - 20\d{6} - ")

    files_moved = 0
    files_skipped = 0

    for filename in os.listdir(current_dir):
        # Full path to the file
        src_path = os.path.join(current_dir, filename)

        # Skip if it's a directory or this script itself
        if os.path.isdir(src_path) or filename == os.path.basename(__file__):
            continue

        # Try to match the pattern
        match = pattern.search(filename)
        
        if match:
            # Extract the channel name (Group 1 from regex)
            raw_channel_name = match.group(1)
            
            # Clean the name to ensure valid folder creation
            channel_folder = clean_folder_name(raw_channel_name)
            
            # path to the new folder
            dest_folder = os.path.join(current_dir, channel_folder)
            
            # Create folder if it doesn't exist
            if not os.path.exists(dest_folder):
                try:
                    os.makedirs(dest_folder)
                    print(f"Created folder: {channel_folder}")
                except OSError as e:
                    print(f"Error creating folder {channel_folder}: {e}")
                    continue

            # Move the file
            dest_path = os.path.join(dest_folder, filename)
            try:
                shutil.move(src_path, dest_path)
                print(f"[MOVED] {filename} -> {channel_folder}")
                files_moved += 1
            except Exception as e:
                print(f"[ERROR] Could not move {filename}: {e}")
        else:
            # Files that don't match the pattern (like the JSON metadata or SnapVid files)
            # print(f"[SKIPPING] {filename} (No pattern match)") # Uncomment to see skipped files
            files_skipped += 1

    print("-" * 50)
    print(f"Done! Moved {files_moved} files. Skipped {files_skipped} items.")

if __name__ == "__main__":
    organize_files()