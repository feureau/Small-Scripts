import os
import shutil
import traceback

def organize_replay_files():
    """
    Moves files containing 'Replay' into a 'Replay' folder.
    Moves files containing '-Rec' (and not Replay) into a 'Horz' folder.
    Works with both 'Prefix' style and 'Timestamp' style names.
    """
    try:
        current_directory = os.getcwd()
        
        # --- CONFIGURATION ---
        replay_folder_name = "Replay"
        horz_folder_name = "Horz"

        replay_folder_path = os.path.join(current_directory, replay_folder_name)
        horz_folder_path = os.path.join(current_directory, horz_folder_name)

        os.makedirs(replay_folder_path, exist_ok=True)
        os.makedirs(horz_folder_path, exist_ok=True)

        files = os.listdir(current_directory)

        for file_name in files:
            source_path = os.path.join(current_directory, file_name)

            # Ensure we are only moving files, not folders
            if os.path.isfile(source_path):
                
                # Condition A: Files containing "Replay" 
                # This catches "Replay 01.mp4" AND "2025...-Rec Replay.mp4"
                if "Replay" in file_name:
                    destination_path = os.path.join(replay_folder_path, file_name)
                    shutil.move(source_path, destination_path)

                # Condition B: Files containing "Rec" (that didn't match the Replay check)
                # This catches "Rec-01.mp4" AND "2025...-Rec.mp4"
                elif "Rec" in file_name:
                    destination_path = os.path.join(horz_folder_path, file_name)
                    shutil.move(source_path, destination_path)

    except Exception:
        # Log errors to a file
        with open("error_log.txt", "w") as f:
            traceback.print_exc(file=f)


if __name__ == "__main__":
    organize_replay_files()