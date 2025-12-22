import os
import shutil
import re

def sort_files():
    # Get the current working directory
    source_dir = os.getcwd()
    
    print(f"Sorting files in: {source_dir}")
    print("-" * 60)
    print(f"{'FILENAME':<50} | {'ACTION':<15} | {'DESTINATION'}")
    print("-" * 60)

    # Define the categorization rules
    # ORDER MATTERS: The script checks these top-to-bottom.
    # "Downloads_Generic" is last to catch everything else.
    rules = {
        # --- NEW RULES ---
        "Blackmagic_Camera": [
            r"^A001_",            # A001_12211040_C011.mp4
        ],
        "Xiaohongshu": [
            r"^Camera_",          # Camera_1040g...
        ],
        "Ezviz_Security": [
            r"^\d{13,}",          # 13+ digit timestamp: 1763021070987.jpg
        ],

        # --- PREVIOUS RULES ---
        "Google_Pixel": [
            r"^PXL_\d+",          # PXL_2025... 
            r"^PXL_.*\.RAW",      
        ],
        "DJI_Drone": [
            r"^DJI_\d+",          
        ],
        "WhatsApp": [
            r"^IMG-\d{8}-WA",     
            r"^VID-\d{8}-WA",     
            r".*WA\d+.*",         
        ],
        "Screenshots": [
            r"^Screenshot_.*",    
        ],
        "TikTok": [
            r"^snaptik",          
            r".*tiktok.*",        
        ],
        "Snapchat": [
            r"^Snapchat-",        
        ],
        "Instagram": [
            r"^SnapInsta",        
            r"^IG_.*",
            r"^Instagram.*",
        ],
        "Facebook_Messenger": [
            r"^FB_IMG_",          
            r"^\d{10,}_edited",   
            r"^received_",        
        ],
        "Generic_Camera_Date": [
            # Standard generic date formats: 2025-11-12...
            r"^20\d{2}-\d{2}-\d{2}", 
            r"^Img_20\d{2}",
            r"^Image_20\d{2}",
            r"^VID_20\d{2}",
        ],
        "Hashed_Filenames": [
            # 32-character hex strings (MD5)
            r"^[a-fA-F0-9]{32}(_\d+)?",
        ],

        # --- CATCH-ALL ---
        "Downloads_Generic": [
            # Specific download patterns
            r"^downloadfile",     
            r"^images", 
            r"^maxresdefault",
            r"^mqdefault",
            # THE CATCH-ALL: Matches literally anything else not moved yet
            r".*", 
        ],
    }

    # Files to ignore (the script itself and system files)
    ignore_files = ["sortphonefiles.py", ".DS_Store", "Thumbs.db"]

    moved_count = 0
    folders_created = set()

    for filename in os.listdir(source_dir):
        # Skip directories and ignored files
        if os.path.isdir(filename) or filename in ignore_files:
            continue

        moved = False

        # Check the file against our rules
        for folder_name, patterns in rules.items():
            for pattern in patterns:
                if re.search(pattern, filename, re.IGNORECASE):
                    
                    # Create the target folder if it doesn't exist
                    target_folder = os.path.join(source_dir, folder_name)
                    if not os.path.exists(target_folder):
                        os.makedirs(target_folder)
                        if folder_name not in folders_created:
                            print(f"[*] Created Folder: {folder_name}")
                            folders_created.add(folder_name)

                    # Source and Destination paths
                    src_path = os.path.join(source_dir, filename)
                    dst_path = os.path.join(target_folder, filename)

                    # Handle duplicates in destination
                    if os.path.exists(dst_path):
                        base, extension = os.path.splitext(filename)
                        counter = 1
                        while os.path.exists(os.path.join(target_folder, f"{base}_copy{counter}{extension}")):
                            counter += 1
                        new_filename = f"{base}_copy{counter}{extension}"
                        dst_path = os.path.join(target_folder, new_filename)
                        print(f"{filename:<50} | RENAMED ->      | {folder_name}/{new_filename}")
                    else:
                        print(f"{filename:<50} | MOVED ->        | {folder_name}")

                    try:
                        shutil.move(src_path, dst_path)
                        moved_count += 1
                        moved = True
                    except Exception as e:
                        print(f"[!] Error moving {filename}: {e}")
                    
                    break # Stop checking patterns for this folder
            
            if moved:
                break # Stop checking other folders (File is done)

    print("-" * 60)
    print(f"Done! Sorted {moved_count} files.")
    print("Files left in root: 0 (Everything else moved to Downloads_Generic)")

if __name__ == "__main__":
    sort_files()