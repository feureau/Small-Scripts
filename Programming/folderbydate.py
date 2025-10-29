#!/usr/bin/env python3
import os
import shutil
from datetime import datetime
import sys

def sort_files_by_date():
    current_dir = os.getcwd()
    
    for filename in os.listdir(current_dir):
        filepath = os.path.join(current_dir, filename)
        
        if os.path.isfile(filepath):
            # Get creation time (or modification time as fallback on some systems)
            timestamp = os.path.getctime(filepath)
            date = datetime.fromtimestamp(timestamp)
            date_folder = date.strftime('%Y-%m-%d')
            
            # Create date folder if it doesn't exist
            date_path = os.path.join(current_dir, date_folder)
            os.makedirs(date_path, exist_ok=True)
            
            # Move file to date folder
            shutil.move(filepath, os.path.join(date_path, filename))

if __name__ == "__main__":
    sort_files_by_date()