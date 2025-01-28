import os
import re
import sys

# Define which extensions to treat as "video files"
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov", ".avi", ".wmv", ".flv", ".webm"}

def sanitize_filename(name, max_length=50):
    """
    Remove characters not allowed in filenames on most OSes and
    truncate to a reasonable length.
    """
    # Remove invalid characters (\/:*?"<>| and control chars)
    sanitized = re.sub(r'[\\/:*?"<>|\r\n]+', '', name)
    
    # Replace spaces with underscores for better readability
    sanitized = re.sub(r'\s+', '_', sanitized)
    
    # Truncate if it's too long
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length].rstrip('_')
    
    return sanitized.strip()

def get_first_subtitle_sentence(srt_path):
    """
    Opens an SRT file using utf-8-sig to handle the BOM,
    skips numeric/timecode lines, and returns the first sentence
    of actual subtitle text.
    """
    with open(srt_path, 'r', encoding='utf-8-sig', errors='replace') as f:
        for line in f:
            line = line.strip()
            
            # Skip empty lines, lines with only digits, or timecodes
            if not line or line.isdigit() or '-->' in line:
                continue
            
            # First non-skipped line is presumably the first subtitle text
            first_subtitle_text = line
            
            # Split on punctuation to get naive "first sentence"
            sentences = re.split(r'[.!?]', first_subtitle_text)
            first_sentence = sentences[0].strip() if sentences else first_subtitle_text.strip()
            
            # Return the first sentence if it's not empty
            if first_sentence:
                return first_sentence
        
    return None  # No text found

def find_video_srt_pairs(folder):
    """
    Scans the given folder and finds pairs of video files and their corresponding .srt files
    based on base filenames.
    Returns a dictionary with base names as keys and dictionaries with 'video' and 'srt' as keys.
    """
    matches = {}
    
    for filename in os.listdir(folder):
        full_path = os.path.join(folder, filename)
        
        if not os.path.isfile(full_path):
            continue  # Skip directories, symlinks, etc.
        
        root, ext = os.path.splitext(filename)
        ext_lower = ext.lower()
        
        if ext_lower in VIDEO_EXTENSIONS:
            if root not in matches:
                matches[root] = {}
            matches[root]["video"] = filename
        
        elif ext_lower == ".srt":
            if root not in matches:
                matches[root] = {}
            matches[root]["srt"] = filename
    
    return matches

def ensure_unique_filename(folder, base_name, extension):
    """
    Ensures that the filename is unique within the folder.
    If the filename already exists, appends a counter to make it unique.
    """
    sanitized_base = sanitize_filename(base_name)
    new_name = f"{sanitized_base}{extension}"
    counter = 1
    
    while os.path.exists(os.path.join(folder, new_name)):
        new_name = f"{sanitized_base}_{counter}{extension}"
        counter += 1
    
    return new_name

def main():
    # Use the folder the script is called from (current working directory)
    folder = os.getcwd()
    
    # Find all video and srt pairs
    matches = find_video_srt_pairs(folder)
    
    # Track new names to prevent duplicates in this run
    used_names = set()
    
    for base, files in matches.items():
        video_file = files.get("video")
        srt_file = files.get("srt")
        
        if video_file and srt_file:
            srt_path = os.path.join(folder, srt_file)
            first_sentence = get_first_subtitle_sentence(srt_path)
            
            if not first_sentence:
                print(f"[WARNING] No subtitle text found in '{srt_file}'. Skipping rename.")
                continue
            
            # Sanitize the first sentence to create the new filename
            # This ensures that filenames are unique by checking used_names
            new_name_core = sanitize_filename(first_sentence, max_length=50)
            
            # Handle potential duplicates by appending a counter
            original_new_name_core = new_name_core
            counter = 1
            while new_name_core in used_names:
                new_name_core = f"{original_new_name_core}_{counter}"
                counter += 1
            used_names.add(new_name_core)
            
            # Ensure filenames are unique on the filesystem
            new_video_name = ensure_unique_filename(folder, new_name_core, os.path.splitext(video_file)[1])
            new_srt_name = ensure_unique_filename(folder, new_name_core, ".srt")
            
            old_video_path = os.path.join(folder, video_file)
            old_srt_path = os.path.join(folder, srt_file)
            new_video_path = os.path.join(folder, new_video_name)
            new_srt_path = os.path.join(folder, new_srt_name)
            
            # Perform the renames
            try:
                os.rename(old_video_path, new_video_path)
                os.rename(old_srt_path, new_srt_path)
                print(f"Renamed:\n  '{video_file}' -> '{new_video_name}'\n  '{srt_file}' -> '{new_srt_name}'\n")
            except Exception as e:
                print(f"[ERROR] Could not rename '{video_file}' and '{srt_file}': {e}")
        else:
            if not video_file:
                print(f"[WARNING] No video file found for '{srt_file}'. Skipping.")
            if not srt_file:
                print(f"[WARNING] No .srt file found for '{video_file}'. Skipping.")

if __name__ == "__main__":
    main()
