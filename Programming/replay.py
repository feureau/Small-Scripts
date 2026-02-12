import os
import shutil
import traceback
import glob
import argparse

def organize_and_count_files(dry_run=False):
    try:
        current_directory = os.getcwd()

        def log_action(action, src=None, dst=None):
            if not dry_run:
                return
            if src is not None and dst is not None:
                print(f"[DRY-RUN] {action}: {src} -> {dst}")
            elif src is not None:
                print(f"[DRY-RUN] {action}: {src}")
            else:
                print(f"[DRY-RUN] {action}")
        
        # --- CONFIGURATION ---
        base_replay_name = "Replay"
        base_horz_name = "Horz"
        container_full_label = "Full"
        container_replay_label = "Replay"
        file_limit = 15
        
        # Define what counts as a video file (must be lowercase)
        video_extensions = {".mp4", ".mov", ".avi", ".mkv", ".flv", ".wmv", ".webm", ".m4v", ".ts", ".3gp"}

        # --- STEP 1: CONSOLIDATE FILES FROM EXISTING FOLDERS ---

        def remove_total_markers(folder_path):
            """Remove bookkeeping files like 'total 47' from a folder."""
            try:
                entries = os.listdir(folder_path)
            except OSError:
                return

            for name in entries:
                full_path = os.path.join(folder_path, name)
                if os.path.isfile(full_path) and name.startswith("total "):
                    try:
                        if dry_run:
                            log_action("REMOVE", full_path)
                        else:
                            os.remove(full_path)
                    except OSError:
                        pass
        
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

        def collect_from_folders(prefix, base_dirs, video_list, processed_files):
            # Find all folders starting with the prefix inside each base dir
            for base_dir in base_dirs:
                try:
                    entries = os.listdir(base_dir)
                except OSError:
                    continue

                folders = [d for d in entries
                           if os.path.isdir(os.path.join(base_dir, d)) and d.startswith(prefix)]

                # Sort folders numerically by index
                folders.sort(key=get_folder_index)

                for folder_name in folders:
                    folder_path = os.path.join(base_dir, folder_name)
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
                                        if dry_run:
                                            log_action("MOVE", full_path, dest_path)
                                        else:
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
                                            if dry_run:
                                                log_action("MOVE", srt_full_path, srt_dest)
                                            else:
                                                shutil.move(srt_full_path, srt_dest)
                                        except OSError:
                                            pass
                                    processed_files.add(srt_name)
                            
                            # Move any other .srt files that might be orphaned
                            elif ext.lower() == ".srt":
                                if not os.path.exists(dest_path):
                                    try:
                                        if dry_run:
                                            log_action("MOVE", full_path, dest_path)
                                        else:
                                            shutil.move(full_path, dest_path)
                                    except OSError:
                                        pass
                                processed_files.add(item)

                    # Old bookkeeping files prevent cleanup; remove them here.
                    remove_total_markers(folder_path)

                    # Attempt to remove the old folder only if it is truly empty.
                    # Never force-delete here; subfolders/non-video files may exist.
                    try:
                        if not os.listdir(folder_path):
                            if dry_run:
                                log_action("RMDIR", folder_path)
                            else:
                                os.rmdir(folder_path)
                    except OSError:
                        # Folder might be locked, skip it for now
                        pass

            # Clean up empty container folders
            for base_dir in base_dirs:
                if base_dir == current_directory:
                    continue
                remove_total_markers(base_dir)
                try:
                    if not os.listdir(base_dir):
                        if dry_run:
                            log_action("RMDIR", base_dir)
                        else:
                            os.rmdir(base_dir)
                except OSError:
                    pass

        existing_replay_videos = []
        existing_horz_videos = []
        processed_files = set()
        
        def find_container_dirs(label_prefix):
            dirs = []
            for d in os.listdir(current_directory):
                path = os.path.join(current_directory, d)
                if os.path.isdir(path) and d.startswith(label_prefix):
                    dirs.append(path)
            return dirs

        container_dirs = find_container_dirs(container_full_label) + find_container_dirs(container_replay_label)
        base_dirs = [current_directory] + container_dirs

        collect_from_folders(base_replay_name, base_dirs, existing_replay_videos, processed_files)
        collect_from_folders(base_horz_name, base_dirs, existing_horz_videos, processed_files)
        
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
                if dry_run:
                    log_action("MKDIR", folder_path)
                else:
                    os.makedirs(folder_path, exist_ok=True)
                created_folders.append((folder_path, base_folder_name, i, chunk))
                
                for file_name in chunk:
                    source = os.path.join(current_directory, file_name)
                    dest = os.path.join(folder_path, file_name)
                    if os.path.exists(source) and not os.path.exists(dest):
                        try:
                            if dry_run:
                                log_action("MOVE", source, dest)
                            else:
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
                            if dry_run:
                                log_action("MOVE", srt_source, srt_dest)
                            else:
                                shutil.move(srt_source, srt_dest)
                        except OSError:
                            pass
            return created_folders

        final_replay_data = distribute_files(replay_videos, base_replay_name)
        final_horz_data = distribute_files(horz_videos, base_horz_name)

        # --- STEP 3: RENAME FOLDERS TO FINAL NAMES ---
        
        def finalize_folders(folder_data):
            total_count = 0
            final_names = []
            for temp_path, base_name, index, planned_chunk in folder_data:
                if dry_run:
                    count = sum(1 for item in planned_chunk if os.path.splitext(item)[1].lower() in video_extensions)
                else:
                    if not os.path.exists(temp_path):
                        continue
                    # Count videos in the temp folder
                    items = os.listdir(temp_path)
                    count = sum(1 for item in items if os.path.isfile(os.path.join(temp_path, item)) 
                               and os.path.splitext(item)[1].lower() in video_extensions)
                
                total_count += count
                new_name = f"{base_name} {index}-{count}"
                new_path = os.path.join(current_directory, new_name)
                final_names.append(new_name)
                
                # Handle collision
                if os.path.exists(new_path):
                    if os.path.isdir(new_path):
                        # If it's a directory, move files from temp to it.
                        # Preserve duplicates by renaming the incoming file.
                        if dry_run:
                            log_action("MERGE-DIR", temp_path, new_path)
                            continue
                        move_failed = False
                        for item in os.listdir(temp_path):
                            s = os.path.join(temp_path, item)
                            d = os.path.join(new_path, item)
                            try:
                                if os.path.exists(d):
                                    base, ext = os.path.splitext(item)
                                    n = 1
                                    while True:
                                        alt_name = f"{base}__dup{n}{ext}"
                                        alt_path = os.path.join(new_path, alt_name)
                                        if not os.path.exists(alt_path):
                                            d = alt_path
                                            break
                                        n += 1
                                shutil.move(s, d)
                            except OSError:
                                move_failed = True
                        if not move_failed and not os.listdir(temp_path):
                            os.rmdir(temp_path)
                    else:
                        # If it's a file (unlikely), remove it and rename
                        if dry_run:
                            log_action("REMOVE", new_path)
                            log_action("RENAME", temp_path, new_path)
                        else:
                            os.remove(new_path)
                            os.rename(temp_path, new_path)
                else:
                    if dry_run:
                        log_action("RENAME", temp_path, new_path)
                    else:
                        os.rename(temp_path, new_path)
            return total_count, final_names

        replay_total, replay_final_names = finalize_folders(final_replay_data)
        horz_total, horz_final_names = finalize_folders(final_horz_data)

        # --- STEP 4: GROUP INTO FULL/REPLAY CONTAINERS ---

        def group_into_container(label, total_count, child_prefix, planned_child_folders=None):
            # Remove old containers with this label (should be empty after consolidation)
            for d in os.listdir(current_directory):
                path = os.path.join(current_directory, d)
                if os.path.isdir(path) and d.startswith(label):
                    try:
                        if not os.listdir(path):
                            if dry_run:
                                log_action("RMDIR", path)
                            else:
                                os.rmdir(path)
                    except OSError:
                        pass

            container_name = f"{label} {total_count}"
            container_path = os.path.join(current_directory, container_name)
            if dry_run:
                log_action("MKDIR", container_path)
            else:
                os.makedirs(container_path, exist_ok=True)

            if dry_run and planned_child_folders is not None:
                child_folders = planned_child_folders
            else:
                child_folders = [d for d in os.listdir(current_directory)
                                 if os.path.isdir(os.path.join(current_directory, d)) and d.startswith(child_prefix)]

            for folder_name in child_folders:
                src = os.path.join(current_directory, folder_name)
                dest = os.path.join(container_path, folder_name)
                if not os.path.exists(dest):
                    try:
                        if dry_run:
                            log_action("MOVE", src, dest)
                        else:
                            shutil.move(src, dest)
                    except OSError:
                        pass

            total_file_name = f"total {total_count}"
            try:
                total_file_path = os.path.join(container_path, total_file_name)
                if dry_run:
                    log_action("WRITE", total_file_path)
                else:
                    with open(total_file_path, "w") as f:
                        f.write(f"Total: {total_count}\n")
            except OSError:
                pass

        group_into_container(container_full_label, horz_total, base_horz_name, planned_child_folders=horz_final_names if dry_run else None)
        group_into_container(container_replay_label, replay_total, base_replay_name, planned_child_folders=replay_final_names if dry_run else None)

        # --- STEP 5: CREATE TOTAL FILE ---
        
        old_totals = glob.glob(os.path.join(current_directory, "total *"))
        for old_file in old_totals:
            try:
                if dry_run:
                    log_action("REMOVE", old_file)
                else:
                    os.remove(old_file)
            except OSError:
                pass

        grand_total = replay_total + horz_total
        total_file_name = f"total {grand_total}"
        
        total_file_path = os.path.join(current_directory, total_file_name)
        if dry_run:
            log_action("WRITE", total_file_path)
        else:
            with open(total_file_path, "w") as f:
                f.write(f"Replay Total: {replay_total}\nHorz Total: {horz_total}\nGrand Total: {grand_total}")

        if dry_run:
            print(f"Dry-run complete. Replay: {replay_total}, Horz: {horz_total}, Total: {grand_total}")
        else:
            print(f"Done. Replay: {replay_total}, Horz: {horz_total}, Total: {grand_total}")

    except Exception:
        with open("error_log.txt", "w") as f:
            traceback.print_exc(file=f)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sort Replay/Rec videos into grouped folders and container folders.")
    parser.add_argument("--dry-run", action="store_true", help="Preview planned file operations without changing files.")
    args = parser.parse_args()
    organize_and_count_files(dry_run=args.dry_run)
