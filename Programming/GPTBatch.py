import os
import sys
import json
import glob
import time
import datetime
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import google.oauth2.credentials
import google.oauth2.flow
from google.oauth2.flow import InstalledAppFlow
import argparse
import tkinter as tk
from tkinter import ttk
from tkinter import scrolledtext
from tkinter import filedialog
import tkinter.messagebox
import traceback

# --- Customizable Variables ---
CLIENT_SECRETS_FILE = "client_secret.json"  # Replace with your client secret file
SCOPES = ['https://www.googleapis.com/auth/youtube']
MAX_TAGS = 15  # Maximum number of tags allowed per video
RETRY_MAX_ATTEMPTS = 5
RETRY_INITIAL_DELAY = 5  # seconds
RETRY_MAX_DELAY = 60  # seconds
API_CALL_DELAY = 1  # Initial delay between API calls (seconds)

# --- Helper Functions ---

def get_youtube_service():
    """Builds and returns the YouTube Data API service object."""
    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
    credentials = flow.run_local_server(port=0)
    return build('youtube', 'v3', credentials=credentials)

def update_video_metadata(service, video_id, metadata):
    """Updates the metadata of a YouTube video with retry logic and exponential backoff."""
    max_retries = RETRY_MAX_ATTEMPTS
    retry_delay = RETRY_INITIAL_DELAY

    for attempt in range(max_retries):
        try:
            request = service.videos().update(
                part="snippet",
                body={
                    "id": video_id,
                    "snippet": metadata
                }
            ).execute()
            return request  # Success!
        except HttpError as e:
            if e.resp.status == 409:  # Conflict error
                print(f"Conflict error updating video {video_id}. Retrying in {retry_delay} seconds (attempt {attempt + 1}/{max_retries})...")
                time.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, RETRY_MAX_DELAY)  # Exponential backoff
            else:
                print(f"An unexpected error occurred: {e}")
                raise  # Re-raise other errors
    print(f"Failed to update video {video_id} after {max_retries} attempts.")
    return None  # Failed after all retries

def process_video(service, video_id, title, description, tags):
    """Processes a single video, updating its metadata."""
    metadata = {
        "title": title,
        "description": description,
        "tags": tags[:MAX_TAGS]  # Truncate tags to the maximum allowed
    }

    if len(tags) > MAX_TAGS:
        print(f"WARNING: Tag list for '{title}' truncated to {MAX_TAGS} tags.")

    try:
        response = update_video_metadata(service, video_id, metadata)
        if response:
            print(f"Metadata updated for '{title}' ({video_id})")
            return True
        else:
            return False
    except Exception as e:
        print(f"ERROR: Failed to update metadata for '{title}' ({video_id}): {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="YouTube Metadata Updater")
    parser.add_argument("files", nargs="*", help="Path(s) to JSON metadata files.")
    args = parser.parse_args()

    if not args.files:
        print("No JSON metadata files specified.")
        return

    service = get_youtube_service()

    video_files = []
    for file_path in args.files:
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                video_files.append(data)
        except FileNotFoundError:
            print(f"Error: File not found: {file_path}")
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON format in file: {file_path}")

    successful_updates = 0
    failed_updates = 0

    for video_data in video_files:
        video_id = video_data.get("id")
        title = video_data.get("title", "")
        description = video_data.get("description", "")
        tags = video_data.get("tags", [])

        if not video_id:
            print(f"Error: Video ID not found in file: {video_data}")
            failed_updates += 1
            continue

        if process_video(service, video_id, title, description, tags):
            successful_updates += 1
        else:
            failed_updates += 1

        time.sleep(API_CALL_DELAY)  # Delay between API calls

    print("\n--- Processing Summary ---")
    print(f"Successfully updated: {successful_updates}")
    print(f"Failed to update: {failed_updates}")

if __name__ == "__main__":
    main()