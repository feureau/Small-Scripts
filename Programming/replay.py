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
        # Collect files from existing Replay/Horz folders in order, then remove folders
        
        def get_folder_index(folder_name):
            # Extract number from "Horz 2-14" or "Horz 2"
            parts = folder_name.split()
            if len(parts) > 1:
                idx_part = parts[1].split('-')[0]
                try:
                    return int(idx_part)
                except ValueError:
                    return 0
            return 0

        existing_replay_videos = []
        existing_horz_videos = []
        processed_files = set()
        
        all_items = sorted(os.listdir(current_directory))
        replay_folders = []
        horz_folders = []
        
        for item in all_items:
            full_path = os.path.join(current_directory, item)
            if os.path.isdir(full_path):
                if item.startswith(base_replay_name):
                    replay_folders.append(item)
                elif item.startswith(base_horz_name):
                    horz_folders.append(item)
        
        # Sort folders numerically by index
        replay_folders.sort(key=get_folder_index)
        horz_folders.sort(key=get_folder_index)
        
        def collect_from_folders(folders, video_list):
            for folder_name in folders:
                folder_path = os.path.join(current_directory, folder_name)
                # Sort files within the folder alphabetically
                folder_content = sorted(os.listdir(folder_path))
                for sub_item in folder_content:
                    sub_full_path = os.path.join(folder_path, sub_item)
                    if os.path.isfile(sub_full_path):
                        _, ext = os.path.splitext(sub_item)
                        if ext.lower() in video_extensions:
                            # Move to root Temporarily (or just track them)
                            dest_path = os.path.join(current_directory, sub_item)
                            if not os.path.exists(dest_path):
                                shutil.move(sub_full_path, dest_path)
                            video_list.append(sub_item)
                            processed_files.add(sub_item)
                
                # Remove the old folder
                try:
                    shutil.rmtree(folder_path)
                except OSError:
                    pass

        collect_from_folders(replay_folders, existing_replay_videos)
        collect_from_folders(horz_folders, existing_horz_videos)
        
        # --- STEP 2: GATHER AND DISTRIBUTE FILES ---
        
        # Get remaining (new) videos from root
        root_files = os.listdir(current_directory)
        new_replay_videos = []
        new_horz_videos = []
        
        for f in sorted(root_files):
            if f in processed_files:
                continue
            if not os.path.isfile(os.path.join(current_directory, f)):
                continue
                
            _, ext = os.path.splitext(f)
            if ext.lower() in video_extensions:
                if "Replay" in f:
                    new_replay_videos.append(f)
                elif "Rec" in f:
                    new_horz_videos.append(f)
        
        # Combine: Existing Groups first, then New Files alphabetically
        replay_videos = existing_replay_videos + new_replay_videos
        horz_videos = existing_horz_videos + new_horz_videos

        def distribute_files(file_list, base_folder_name):
            chunks = [file_list[i:i + file_limit] for i in range(0, len(file_list), file_limit)]
            created_folders = []
            
            for i, chunk in enumerate(chunks):
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

        final_replay_folders = distribute_files(replay_videos, base_replay_name)
        final_horz_folders = distribute_files(horz_videos, base_horz_name)

        # --- STEP 2: COUNT AND RENAME FOLDERS ---
        
        def process_folders(folders):
            total_count = 0
            for folder_path in folders:
                if not os.path.exists(folder_path):
                    continue
                
                items = os.listdir(folder_path)
                count = 0
                for item in items:
                    if os.path.isfile(os.path.join(folder_path, item)):
                         _, ext = os.path.splitext(item)
                         if ext.lower() in video_extensions:
                             count += 1
                
                total_count += count
                parent = os.path.dirname(folder_path)
                base = os.path.basename(folder_path)
                new_name = f"{base}-{count}"
                new_path = os.path.join(parent, new_name)
                
                os.rename(folder_path, new_path)
            return total_count

        replay_total = process_folders(final_replay_folders)
        horz_total = process_folders(final_horz_folders)

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