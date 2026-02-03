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

        def collect_from_folders(prefix, video_list, processed_files):
            # Find all folders starting with the prefix
            folders = [d for d in os.listdir(current_directory) 
                      if os.path.isdir(os.path.join(current_directory, d)) and d.startswith(prefix)]
            
            # Sort folders numerically by index
            folders.sort(key=get_folder_index)
            
            for folder_name in folders:
                folder_path = os.path.join(current_directory, folder_name)
                try:
                    folder_content = os.listdir(folder_path)
                except OSError:
                    continue

                for item in folder_content:
                    full_path = os.path.join(folder_path, item)
                    if os.path.isfile(full_path):
                        _, ext = os.path.splitext(item)
                        dest_path = os.path.join(current_directory, item)
                        
                        # Process video files
                        if ext.lower() in video_extensions:
                            if not os.path.exists(dest_path):
                                try:
                                    shutil.move(full_path, dest_path)
                                except OSError:
                                    continue
                            video_list.append(item)
                            processed_files.add(item)
                            
                            # Move corresponding .srt if exists (exact match)
                            base, _ = os.path.splitext(item)
                            srt_name = base + ".srt"
                            srt_full_path = os.path.join(folder_path, srt_name)
                            if os.path.exists(srt_full_path):
                                srt_dest = os.path.join(current_directory, srt_name)
                                if not os.path.exists(srt_dest):
                                    try:
                                        shutil.move(srt_full_path, srt_dest)
                                    except OSError:
                                        pass
                                processed_files.add(srt_name)
                        
                        # Move any other .srt files that might be orphaned
                        elif ext.lower() == ".srt":
                            if not os.path.exists(dest_path):
                                try:
                                    shutil.move(full_path, dest_path)
                                except OSError:
                                    pass
                            processed_files.add(item)

                # Attempt to remove the old folder
                try:
                    # Only remove if it's empty now
                    if not os.listdir(folder_path):
                        os.rmdir(folder_path)
                    else:
                        # If still contains stuff (maybe non-video/srt), try rmtree
                        # but be cautious. For now, let's just use rmtree if it's our own folder structure.
                        shutil.rmtree(folder_path)
                except OSError:
                    # Folder might be locked, skip it for now
                    pass

        existing_replay_videos = []
        existing_horz_videos = []
        processed_files = set()
        
        collect_from_folders(base_replay_name, existing_replay_videos, processed_files)
        collect_from_folders(base_horz_name, existing_horz_videos, processed_files)
        
        # --- STEP 2: GATHER NEW FILES ---
        
        root_files = os.listdir(current_directory)
        new_replay_videos = []
        new_horz_videos = []
        
        # Sort root files to ensure consistent order
        for f in sorted(root_files):
            if f in processed_files:
                continue
            full_path = os.path.join(current_directory, f)
            if not os.path.isfile(full_path):
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

        # Deduplicate while preserving order
        def uniq(seq):
            seen = set()
            return [x for x in seq if not (x in seen or seen.add(x))]

        replay_videos = uniq(replay_videos)
        horz_videos = uniq(horz_videos)

        def distribute_files(file_list, base_folder_name):
            chunks = [file_list[i:i + file_limit] for i in range(0, len(file_list), file_limit)]
            created_folders = []
            
            for i, chunk in enumerate(chunks):
                folder_name = f"tmp_{base_folder_name}_{i}" # Use temporary names to avoid collisions during distribution
                folder_path = os.path.join(current_directory, folder_name)
                os.makedirs(folder_path, exist_ok=True)
                created_folders.append((folder_path, base_folder_name, i))
                
                for file_name in chunk:
                    source = os.path.join(current_directory, file_name)
                    dest = os.path.join(folder_path, file_name)
                    if os.path.exists(source) and not os.path.exists(dest):
                        try:
                            shutil.move(source, dest)
                        except OSError:
                            continue
                    
                    # Move corresponding .srt if exists
                    base, _ = os.path.splitext(file_name)
                    srt_name = base + ".srt"
                    srt_source = os.path.join(current_directory, srt_name)
                    srt_dest = os.path.join(folder_path, srt_name)
                    if os.path.exists(srt_source) and not os.path.exists(srt_dest):
                        try:
                            shutil.move(srt_source, srt_dest)
                        except OSError:
                            pass
            return created_folders

        final_replay_data = distribute_files(replay_videos, base_replay_name)
        final_horz_data = distribute_files(horz_videos, base_horz_name)

        # --- STEP 3: RENAME FOLDERS TO FINAL NAMES ---
        
        def finalize_folders(folder_data):
            total_count = 0
            for temp_path, base_name, index in folder_data:
                if not os.path.exists(temp_path):
                    continue
                
                # Count videos in the temp folder
                items = os.listdir(temp_path)
                count = sum(1 for item in items if os.path.isfile(os.path.join(temp_path, item)) 
                           and os.path.splitext(item)[1].lower() in video_extensions)
                
                total_count += count
                new_name = f"{base_name} {index}-{count}"
                new_path = os.path.join(current_directory, new_name)
                
                # Handle collision
                if os.path.exists(new_path):
                    if os.path.isdir(new_path):
                        # If it's a directory, move files from temp to it
                        for item in os.listdir(temp_path):
                            s = os.path.join(temp_path, item)
                            d = os.path.join(new_path, item)
                            if not os.path.exists(d):
                                shutil.move(s, d)
                        shutil.rmtree(temp_path)
                    else:
                        # If it's a file (unlikely), remove it and rename
                        os.remove(new_path)
                        os.rename(temp_path, new_path)
                else:
                    os.rename(temp_path, new_path)
            return total_count

        replay_total = finalize_folders(final_replay_data)
        horz_total = finalize_folders(final_horz_data)

        # --- STEP 4: CREATE TOTAL FILE ---
        
        old_totals = glob.glob(os.path.join(current_directory, "total *"))
        for old_file in old_totals:
            try:
                os.remove(old_file)
            except OSError:
                pass

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