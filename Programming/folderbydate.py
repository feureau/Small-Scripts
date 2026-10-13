#!/usr/bin/env python3
import os
import shutil
from datetime import datetime
import sys
from PIL import Image
from PIL.ExifTags import TAGS

def get_date_taken(filepath):
    """
    Attempts to extract the 'Date Taken' from EXIF data for images.
    Returns a datetime object if found, otherwise None.
    """
    try:
        with Image.open(filepath) as img:
            exif_data = img._getexif()
            if not exif_data:
                return None
            
            for tag_id, value in exif_data.items():
                tag = TAGS.get(tag_id, img.getexif().get(tag_id))
                if tag == 'DateTimeOriginal' or tag == 'DateTime':
                    # EXIF dates are usually stored as 'YYYY:MM:DD HH:MM:SS'
                    return datetime.strptime(value, '%Y:%m:%d %H:%M:%S')
    except Exception:
        # If file is not an image or EXIF reading fails, return None
        return None
    return None

def sort_files_by_date():
    current_dir = os.getcwd()
    script_name = os.path.basename(__file__)
    
    print(f"Scanning directory: {current_dir}")
    
    files_processed = 0
    
    for filename in os.listdir(current_dir):
        # Skip the script itself to prevent it from moving itself
        if filename == script_name:
            continue
            
        filepath = os.path.join(current_dir, filename)
        
        if os.path.isfile(filepath):
            # 1. Try to get EXIF date (Embedded)
            date = get_date_taken(filepath)
            
            # 2. Fallback to Modification Time (Filesystem)
            if date is None:
                timestamp = os.path.getmtime(filepath)
                date = datetime.fromtimestamp(timestamp)
            
            date_folder = date.strftime('%Y-%m-%d')
            
            # Create date folder if it doesn't exist
            date_path = os.path.join(current_dir, date_folder)
            os.makedirs(date_path, exist_ok=True)
            
            # Move file to date folder
            try:
                shutil.move(filepath, os.path.join(date_path, filename))
                files_processed += 1
            except Exception as e:
                print(f"Error moving {filename}: {e}")
    
    print(f"Done! Processed {files_processed} files.")

if __name__ == "__main__":
    sort_files_by_date()
