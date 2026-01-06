import os
import sys
import json
from internetarchive import get_item, get_session

def sync_metadata(folder_path):
    # Assume folder name is the identifier
    identifier = os.path.basename(os.path.abspath(folder_path))
    metadata_file = os.path.join(folder_path, "metadata.json")

    # Check if metadata.json exists
    if not os.path.exists(metadata_file):
        # Silently skip folders that don't have the file
        # or print a message if you prefer:
        # print(f"[{identifier}] No metadata.json found. Skipping.")
        return

    print(f"\n[{identifier}] Found metadata.json. Processing...")

    # 1. Load the local JSON data
    try:
        with open(metadata_file, 'r', encoding='utf-8') as f:
            local_metadata = json.load(f)
    except json.JSONDecodeError as e:
        print(f"  Error: Invalid JSON format in {metadata_file}.")
        print(f"  Details: {e}")
        return

    # 2. Connect to Archive.org Item
    try:
        item = get_item(identifier)
        if not item.exists:
            print(f"  Error: Item '{identifier}' does not exist on server.")
            return
    except Exception as e:
        print(f"  Connection Error: {e}")
        return

    # 3. Compare and Update
    # We simply push the local_metadata dictionary. 
    # Archive.org's library handles the comparison and only updates what is necessary 
    # or overwrites existing fields with the new values.
    
    print("  Sending updates to Archive.org...")
    
    try:
        # modify_metadata takes a dictionary of changes
        item.modify_metadata(local_metadata)
        print("  Success: Metadata updated.")
        
        # Optional: Print what was sent
        for key, value in local_metadata.items():
            print(f"    - Updated '{key}'")
            
    except Exception as e:
        print(f"  Update Failed: {e}")

def main():
    working_dir = os.getcwd()
    
    # Get all subfolders
    subfolders = [f.path for f in os.scandir(working_dir) if f.is_dir()]

    if not subfolders:
        print("No subfolders found.")
        sys.exit()

    print(f"Scanning {len(subfolders)} folders for 'metadata.json'...")

    for folder in subfolders:
        sync_metadata(folder)

if __name__ == "__main__":
    # Check Auth
    try:
        if not get_session().access_key:
            print("Error: Please run 'ia configure' to log in first.")
            sys.exit(1)
    except:
        pass

    main()