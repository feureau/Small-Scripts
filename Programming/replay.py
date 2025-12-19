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

        # --- STEP 0: RESET FOLDERS ---
        # If folders like "Replay-10" exist from a previous run, 
        # rename them back to "Replay" so we can move new files into them easily.
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
        
        # Get the script's own name to prevent moving itself
        script_filename = os.path.basename(__file__) 

        for file_name in files:
            source_path = os.path.join(current_directory, file_name)

            if os.path.isfile(source_path) and file_name != script_filename:
                # Skip the "total X.txt" files if they exist, we will clean them later
                if file_name.startswith("total ") and file_name.endswith(".txt"):
                    continue

                if "Replay" in file_name:
                    destination_path = os.path.join(replay_folder_path, file_name)
                    # Handle overwrite protection
                    if not os.path.exists(destination_path):
                        shutil.move(source_path, destination_path)
                
                elif "Rec" in file_name:
                    destination_path = os.path.join(horz_folder_path, file_name)
                    if not os.path.exists(destination_path):
                        shutil.move(source_path, destination_path)

        # --- STEP 2: COUNT AND RENAME FOLDERS ---
        
        # Count files in Replay
        replay_files = [f for f in os.listdir(replay_folder_path) if os.path.isfile(os.path.join(replay_folder_path, f))]
        replay_count = len(replay_files)
        
        # Count files in Horz
        horz_files = [f for f in os.listdir(horz_folder_path) if os.path.isfile(os.path.join(horz_folder_path, f))]
        horz_count = len(horz_files)

        # Rename Replay Folder -> "Replay-X"
        new_replay_name = f"{base_replay_name}-{replay_count}"
        if os.path.exists(replay_folder_path): # Check exists to prevent crash if folder was deleted
            os.rename(replay_folder_path, os.path.join(current_directory, new_replay_name))

        # Rename Horz Folder -> "Horz-X"
        new_horz_name = f"{base_horz_name}-{horz_count}"
        if os.path.exists(horz_folder_path):
            os.rename(horz_folder_path, os.path.join(current_directory, new_horz_name))

        # --- STEP 3: CREATE TOTAL TXT FILE ---
        
        # Remove OLD "total X.txt" files to avoid clutter
        old_totals = glob.glob(os.path.join(current_directory, "total *.txt"))
        for old_file in old_totals:
            try:
                os.remove(old_file)
            except OSError:
                pass

        # Create NEW total file
        grand_total = replay_count + horz_count
        total_file_name = f"total {grand_total}.txt"
        with open(os.path.join(current_directory, total_file_name), "w") as f:
            f.write(f"Replay: {replay_count}\nHorz: {horz_count}\nTotal: {grand_total}")

        print(f"Done. Replay: {replay_count}, Horz: {horz_count}, Total: {grand_total}")

    except Exception:
        with open("error_log.txt", "w") as f:
            traceback.print_exc(file=f)

if __name__ == "__main__":
    organize_and_count_files()