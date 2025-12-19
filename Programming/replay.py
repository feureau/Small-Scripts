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
        
        # Define what counts as a video file (must be lowercase)
        video_extensions = {".mp4", ".mov", ".avi", ".mkv", ".flv", ".wmv", ".webm", ".m4v", ".ts", ".3gp"}

        # --- STEP 0: RESET FOLDERS ---
        all_items = os.listdir(current_directory)
        
        for item in all_items:
            full_path = os.path.join(current_directory, item)
            if os.path.isdir(full_path):
                # Check if folder starts with "Replay" (e.g. "Replay-5")
                if item.startswith(base_replay_name) and item != base_replay_name:
                    os.rename(full_path, os.path.join(current_directory, base_replay_name))
                # Check if folder starts with "Horz" (e.g. "Horz-8")
                elif item.startswith(base_horz_name) and item != base_horz_name:
                    os.rename(full_path, os.path.join(current_directory, base_horz_name))

        # Define standard paths
        replay_folder_path = os.path.join(current_directory, base_replay_name)
        horz_folder_path = os.path.join(current_directory, base_horz_name)

        os.makedirs(replay_folder_path, exist_ok=True)
        os.makedirs(horz_folder_path, exist_ok=True)

        # --- STEP 1: MOVE FILES ---
        files = os.listdir(current_directory)
        script_filename = os.path.basename(__file__) 

        for file_name in files:
            source_path = os.path.join(current_directory, file_name)

            if os.path.isfile(source_path) and file_name != script_filename:
                
                # Check extension
                _, ext = os.path.splitext(file_name)
                is_video = ext.lower() in video_extensions

                # Skip "total" files
                if file_name.startswith("total "):
                    continue

                # ONLY move if it contains the keyword AND is a video file
                if is_video:
                    if "Replay" in file_name:
                        destination_path = os.path.join(replay_folder_path, file_name)
                        if not os.path.exists(destination_path):
                            shutil.move(source_path, destination_path)
                    
                    elif "Rec" in file_name:
                        destination_path = os.path.join(horz_folder_path, file_name)
                        if not os.path.exists(destination_path):
                            shutil.move(source_path, destination_path)

        # --- STEP 2: COUNT AND RENAME FOLDERS ---
        
        # Helper function to count only videos in a specific folder
        def count_videos_in_folder(folder_path):
            if not os.path.exists(folder_path):
                return 0
            
            items = os.listdir(folder_path)
            video_count = 0
            for f in items:
                full_p = os.path.join(folder_path, f)
                if os.path.isfile(full_p):
                    _, ext = os.path.splitext(f)
                    if ext.lower() in video_extensions:
                        video_count += 1
            return video_count

        replay_count = count_videos_in_folder(replay_folder_path)
        horz_count = count_videos_in_folder(horz_folder_path)

        # Rename Replay Folder -> "Replay-X"
        new_replay_name = f"{base_replay_name}-{replay_count}"
        if os.path.exists(replay_folder_path): 
            os.rename(replay_folder_path, os.path.join(current_directory, new_replay_name))

        # Rename Horz Folder -> "Horz-X"
        new_horz_name = f"{base_horz_name}-{horz_count}"
        if os.path.exists(horz_folder_path):
            os.rename(horz_folder_path, os.path.join(current_directory, new_horz_name))

        # --- STEP 3: CREATE TOTAL FILE (NO EXTENSION) ---
        
        # Remove OLD "total" files
        old_totals = glob.glob(os.path.join(current_directory, "total *"))
        for old_file in old_totals:
            if os.path.isfile(old_file):
                try:
                    os.remove(old_file)
                except OSError:
                    pass

        # Create NEW total file WITHOUT extension
        grand_total = replay_count + horz_count
        total_file_name = f"total {grand_total}"
        
        with open(os.path.join(current_directory, total_file_name), "w") as f:
            f.write(f"Replay: {replay_count}\nHorz: {horz_count}\nTotal: {grand_total}")

        print(f"Done. Replay: {replay_count}, Horz: {horz_count}, Total: {grand_total}")

    except Exception:
        with open("error_log.txt", "w") as f:
            traceback.print_exc(file=f)

if __name__ == "__main__":
    organize_and_count_files()