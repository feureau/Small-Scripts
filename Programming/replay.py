import os
import shutil
import traceback
import glob

def organize_and_count_files():
    try:
        current_directory = os.getcwd()
        
        # --- CONFIGURATION ---
        base_replay_name = "Replay"
        base_horz_name = "Horz"
        file_limit = 15
        
        # Define what counts as a video file (must be lowercase)
        video_extensions = {".mp4", ".mov", ".avi", ".mkv", ".flv", ".wmv", ".webm", ".m4v", ".ts", ".3gp"}

        # --- STEP 1: CONSOLIDATE FILES FROM EXISTING FOLDERS ---
        # Move files out of existing Replay/Horz folders to root, then remove old folders
        
        all_items = os.listdir(current_directory)
        folders_to_remove = []
        
        for item in all_items:
            full_path = os.path.join(current_directory, item)
            if os.path.isdir(full_path):
                # Check if it's a Replay or Horz folder
                if item.startswith(base_replay_name) or item.startswith(base_horz_name):
                    folders_to_remove.append(full_path)
                    # Move all video files out to root
                    for sub_item in os.listdir(full_path):
                        sub_full_path = os.path.join(full_path, sub_item)
                        if os.path.isfile(sub_full_path):
                            _, ext = os.path.splitext(sub_item)
                            if ext.lower() in video_extensions:
                                dest_path = os.path.join(current_directory, sub_item)
                                if not os.path.exists(dest_path):
                                    shutil.move(sub_full_path, dest_path)
        
        # Remove old folders (they should be empty or have non-video files)
        for folder_path in folders_to_remove:
            try:
                shutil.rmtree(folder_path)
            except OSError:
                pass
        
        # --- STEP 2: GATHER AND DISTRIBUTE FILES ---
        
        def get_video_files():
            files = [f for f in os.listdir(current_directory) if os.path.isfile(os.path.join(current_directory, f))]
            videos = []
            for f in files:
                _, ext = os.path.splitext(f)
                if ext.lower() in video_extensions:
                    videos.append(f)
            return videos

        all_videos = get_video_files()
        
        replay_videos = sorted([f for f in all_videos if "Replay" in f])
        horz_videos = sorted([f for f in all_videos if "Rec" in f]) # "Rec" for Horz as per original script

        def distribute_files(file_list, base_folder_name):
            chunks = [file_list[i:i + file_limit] for i in range(0, len(file_list), file_limit)]
            created_folders = []
            
            for i, chunk in enumerate(chunks):
                # "Replay 0", "Replay 1", etc.
                folder_name = f"{base_folder_name} {i}"
                folder_path = os.path.join(current_directory, folder_name)
                os.makedirs(folder_path, exist_ok=True)
                created_folders.append(folder_path)
                
                for file_name in chunk:
                    source = os.path.join(current_directory, file_name)
                    dest = os.path.join(folder_path, file_name)
                    if os.path.exists(source) and not os.path.exists(dest):
                        shutil.move(source, dest)
            return created_folders

        replay_folders = distribute_files(replay_videos, base_replay_name)
        horz_folders = distribute_files(horz_videos, base_horz_name)

        # --- STEP 2: COUNT AND RENAME FOLDERS ---
        
        def process_folders(folders):
            total_count = 0
            for folder_path in folders:
                if not os.path.exists(folder_path):
                    continue
                
                # Count videos
                items = os.listdir(folder_path)
                count = 0
                for item in items:
                    if os.path.isfile(os.path.join(folder_path, item)):
                         _, ext = os.path.splitext(item)
                         if ext.lower() in video_extensions:
                             count += 1
                
                total_count += count
                
                # Rename: "Replay 0" -> "Replay 0-15"
                # If folder already ends with dash-number, we might need to be careful? 
                # But we just created them as "Replay X", so they are clean.
                
                parent = os.path.dirname(folder_path)
                base = os.path.basename(folder_path)
                new_name = f"{base}-{count}"
                new_path = os.path.join(parent, new_name)
                
                os.rename(folder_path, new_path)
            return total_count

        replay_total = process_folders(replay_folders)
        horz_total = process_folders(horz_folders)

        # --- STEP 3: CREATE TOTAL FILE ---
        
        # Remove OLD "total" files
        old_totals = glob.glob(os.path.join(current_directory, "total *"))
        for old_file in old_totals:
            if os.path.isfile(old_file):
                try:
                    os.remove(old_file)
                except OSError:
                    pass

        # Create NEW total file
        grand_total = replay_total + horz_total
        total_file_name = f"total {grand_total}"
        
        with open(os.path.join(current_directory, total_file_name), "w") as f:
            f.write(f"Replay Total: {replay_total}\nHorz Total: {horz_total}\nGrand Total: {grand_total}")

        print(f"Done. Replay: {replay_total}, Horz: {horz_total}, Total: {grand_total}")

    except Exception:
        with open("error_log.txt", "w") as f:
            traceback.print_exc(file=f)

if __name__ == "__main__":
    organize_and_count_files()