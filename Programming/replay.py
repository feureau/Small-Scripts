import os
import shutil
import traceback

def organize_replay_files():
    """
    Moves files starting with 'Replay ' into a 'Replay' folder.
    Moves files starting with 'Rec-' into a 'Horz' folder.
    """
    try:
        current_directory = os.getcwd()
        
        # --- CONFIGURATION ---
        # 1. Define folder names
        replay_folder_name = "Replay"
        horz_folder_name = "Horz"

        # 2. Define full paths
        replay_folder_path = os.path.join(current_directory, replay_folder_name)
        horz_folder_path = os.path.join(current_directory, horz_folder_name)

        # 3. Create the subfolders if they don't exist
        os.makedirs(replay_folder_path, exist_ok=True)
        os.makedirs(horz_folder_path, exist_ok=True)

        # Get a list of all files in the current directory
        files = os.listdir(current_directory)

        # Iterate over all the files
        for file_name in files:
            source_path = os.path.join(current_directory, file_name)

            # Ensure we are only moving files, not folders
            if os.path.isfile(source_path):
                
                # Condition A: Files starting with "Replay "
                if file_name.startswith("Replay "):
                    destination_path = os.path.join(replay_folder_path, file_name)
                    shutil.move(source_path, destination_path)

                # Condition B: Files starting with "Rec-"
                # We use 'elif' so a file isn't processed twice
                elif file_name.startswith("Rec-"):
                    destination_path = os.path.join(horz_folder_path, file_name)
                    shutil.move(source_path, destination_path)

    except Exception:
        # Log errors to a file
        with open("error_log.txt", "w") as f:
            traceback.print_exc(file=f)


if __name__ == "__main__":
    organize_replay_files()