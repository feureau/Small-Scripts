import sys
import json
import os
import internetarchive
from urllib.parse import urlparse

def get_id_from_input(input_str):
    """
    Extracts the Item ID from a full URL or returns the input if it's already an ID.
    """
    input_str = input_str.strip()
    
    # Check if it looks like a URL
    if "archive.org" in input_str or "://" in input_str:
        try:
            parsed_url = urlparse(input_str)
            path_parts = parsed_url.path.split('/')
            
            # Standard IA URLs are like /details/identifier
            if 'details' in path_parts:
                index = path_parts.index('details')
                if index + 1 < len(path_parts):
                    return path_parts[index + 1]
            
            # Fallback for /metadata/identifier
            if 'metadata' in path_parts:
                index = path_parts.index('metadata')
                if index + 1 < len(path_parts):
                    return path_parts[index + 1]
        except Exception:
            return input_str
            
    return input_str

def process_item(raw_input):
    """
    Downloads metadata for a single item and saves as JSON.
    """
    # Clean the ID
    item_id = get_id_from_input(raw_input)
    
    if not item_id:
        # Skip empty lines
        return

    # Check if item exists
    item = internetarchive.get_item(item_id)
    if not item.exists:
        print(f"Skipping: Item '{item_id}' not found.")
        return

    print(f"Downloading: {item_id}...")
    
    # Get metadata
    metadata = item.metadata

    # Save as .json
    output_filename = f"{item_id}.json"

    try:
        with open(output_filename, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=4)
        print(f" -> Saved: {output_filename}")
    except IOError as e:
        print(f" -> Error writing file: {e}")
    except OSError as e:
        print(f" -> Error: Invalid filename generated. ({e})")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: iametadl.py <item_id_OR_url_OR_listfile.txt>")
        sys.exit()

    user_input = sys.argv[1]

    # CHECK: Is the input a file that exists on the disk?
    if os.path.isfile(user_input):
        print(f"--- Batch Mode: Reading from {user_input} ---")
        try:
            with open(user_input, "r", encoding="utf-8") as f:
                lines = f.readlines()
                
            total = len(lines)
            for i, line in enumerate(lines):
                # clean whitespace/newlines
                clean_line = line.strip()
                if clean_line:
                    process_item(clean_line)
                    
            print("--- Batch Complete ---")
            
        except Exception as e:
            print(f"Error reading list file: {e}")
            
    # ELSE: Treat it as a single ID/URL
    else:
        process_item(user_input)