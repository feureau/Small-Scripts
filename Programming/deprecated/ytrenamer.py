
import os
import json
import sys
import glob
import re

def extract_title_from_text(text):
    """Extract title from JSON-like text using regex."""
    match = re.search(r'"title":\s*"([^"]+)"', text, re.IGNORECASE)
    if match:
        return match.group(1)
    return None

def batch_rename_files():
    if len(sys.argv) > 1:
        files = sys.argv[1:]
    else:
        files = glob.glob('*.mp4')

    for media_file in files:
        if not media_file.lower().endswith(('.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm')):
            continue

        base_name = os.path.splitext(media_file)[0]
        txt_file = base_name + '.txt'

        if not os.path.exists(txt_file):
            print(f"Missing txt: {txt_file}")
            continue

        # Try to read title from JSON
        new_title = None
        try:
            with open(txt_file, 'r', encoding='utf-8') as f:
                content = f.read()
            # Remove all control characters
            content = ''.join(char for char in content if ord(char) >= 32 or char in '\n\r\t')
            data = json.loads(content)
            new_title = data.get('title')
        except:
            # If JSON parsing fails, try regex extraction
            try:
                with open(txt_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                new_title = extract_title_from_text(content)
            except:
                pass

        if not new_title:
            print(f"No title in: {txt_file}")
            continue

        # Sanitize filename
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            new_title = new_title.replace(char, '_')

        # Rename files
        ext = os.path.splitext(media_file)[1]
        new_media = new_title + ext
        new_txt = new_title + '.txt'
        
        # Rename SRT if exists
        srt_file = base_name + '.srt'
        new_srt = new_title + '.srt' if os.path.exists(srt_file) else None

        os.rename(media_file, new_media)
        os.rename(txt_file, new_txt)
        if new_srt:
            os.rename(srt_file, new_srt)
        print(f"Renamed: {base_name} -> {new_title}")

if __name__ == '__main__':
    batch_rename_files()
