import os
import shutil
import traceback
import glob
import argparse
import re
from datetime import datetime

def organize_and_count_files(dry_run=False):
    current_directory = os.getcwd()
    debug_log_path = os.path.join(current_directory, "replay_debug.log")

    def debug(message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            with open(debug_log_path, "a", encoding="utf-8") as logf:
                logf.write(f"{timestamp} | {message}\n")
        except OSError:
            pass

    def log_exception(context, exc):
        debug(f"ERROR {context}: {type(exc).__name__}: {exc}")

    def safe_rename(src, dst, attempts=5, delay_seconds=0.4):
        for attempt in range(1, attempts + 1):
            try:
                os.rename(src, dst)
                debug(f"RENAME-OK attempt={attempt}: {src} -> {dst}")
                return True
            except OSError as exc:
                log_exception(f"rename attempt={attempt} {src} -> {dst}", exc)
                if attempt == attempts:
                    raise
                try:
                    import time
                    time.sleep(delay_seconds)
                except Exception:
                    pass
        return False

    debug("=" * 80)
    debug(f"START organize_and_count_files dry_run={dry_run} cwd={current_directory}")

    try:
        def log_action(action, src=None, dst=None):
            if src is not None and dst is not None:
                debug(f"ACTION {action}: {src} -> {dst}")
            elif src is not None:
                debug(f"ACTION {action}: {src}")
            else:
                debug(f"ACTION {action}")

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
        debug(
            f"CONFIG base_replay_name={base_replay_name} base_horz_name={base_horz_name} "
            f"container_full_label={container_full_label} container_replay_label={container_replay_label} "
            f"file_limit={file_limit}"
        )
        
        # Define what counts as a video file (must be lowercase)
        video_extensions = {".mp4", ".mov", ".avi", ".mkv", ".flv", ".wmv", ".webm", ".m4v", ".ts", ".3gp"}

        def move_associated_sidecars(source_dir, dest_dir, video_name, processed_files=None):
            """
            Move sidecar files that belong to a video.
            Matches any non-video file whose filename starts with the video's stem,
            and also matching files under a processing_logs subfolder.
            """
            base, _ = os.path.splitext(video_name)

            def move_matching_files(src_dir, dst_dir, include_name_in_processed=True):
                try:
                    entries = os.listdir(src_dir)
                except OSError as exc:
                    log_exception(f"move_associated_sidecars listdir {src_dir}", exc)
                    return

                for name in entries:
                    src_path = os.path.join(src_dir, name)
                    if not os.path.isfile(src_path):
                        continue

                    if name == video_name:
                        continue

                    if not name.startswith(base):
                        continue

                    _, ext = os.path.splitext(name)
                    if ext.lower() in video_extensions:
                        continue

                    dst_path = os.path.join(dst_dir, name)
                    if not os.path.exists(dst_path):
                        try:
                            if dry_run:
                                log_action("MOVE", src_path, dst_path)
                            else:
                                shutil.move(src_path, dst_path)
                        except OSError as exc:
                            log_exception(f"move_associated_sidecars {src_path} -> {dst_path}", exc)
                            continue

                    if processed_files is not None and include_name_in_processed:
                        processed_files.add(name)
                        debug(f"TRACK processed sidecar={name}")

            # Sidecars in the same folder as the video
            move_matching_files(source_dir, dest_dir)

            # Sidecars under processing_logs/
            src_logs_dir = os.path.join(source_dir, "processing_logs")
            if os.path.isdir(src_logs_dir):
                dst_logs_dir = os.path.join(dest_dir, "processing_logs")
                if not os.path.exists(dst_logs_dir):
                    try:
                        if dry_run:
                            log_action("MKDIR", dst_logs_dir)
                        else:
                            os.makedirs(dst_logs_dir, exist_ok=True)
                    except OSError as exc:
                        log_exception(f"move_associated_sidecars mkdir {dst_logs_dir}", exc)
                        return

                move_matching_files(src_logs_dir, dst_logs_dir, include_name_in_processed=False)

        # --- STEP 1: CONSOLIDATE FILES FROM EXISTING FOLDERS ---
        debug("STEP 1 START consolidate existing folders")

        def remove_total_markers(folder_path):
            """Remove bookkeeping files like 'total 47' from a folder."""
            try:
                entries = os.listdir(folder_path)
            except OSError as exc:
                log_exception(f"remove_total_markers listdir {folder_path}", exc)
                return

            for name in entries:
                full_path = os.path.join(folder_path, name)
                if os.path.isfile(full_path) and name.startswith("total "):
                    try:
                        if dry_run:
                            log_action("REMOVE", full_path)
                        else:
                            os.remove(full_path)
                    except OSError as exc:
                        log_exception(f"remove_total_markers remove {full_path}", exc)
        
        def get_folder_index(folder_name):
            # Extract number from "Horz 2-14" or "Horz 2" or "Replay 59"
            parts = folder_name.split()
            if len(parts) > 1:
                # Try to get the first number in the second part
                match = re.search(r'(\d+)', parts[1])
                if match:
                    try:
                        return int(match.group(1))
                    except ValueError:
                        return 0
            return 0

        def consolidate_all_organized_folders():
            """
            Find all folders that match our naming conventions (Container or Chunk)
            and move their video/sidecar contents to the root directory for re-sorting.
            """
            debug("consolidate_all_organized_folders START")
            
            # Patterns for folders we recognize
            # Containers: "Replay 59", "Full 9"
            container_pattern = re.compile(rf"^({container_replay_label}|{container_full_label}) \d+$")
            # Chunks: "Replay 0-15", "Horz 0-9"
            chunk_pattern = re.compile(rf"^({base_replay_name}|{base_horz_name}) \d+-\d+$")

            def is_organized_folder(name):
                return container_pattern.match(name) or chunk_pattern.match(name)

            # We'll collect all matching folders first to avoid issues with directory walking while moving files
            folders_to_process = []
            for root, dirs, _ in os.walk(current_directory):
                for d in dirs:
                    if is_organized_folder(d):
                        folders_to_process.append(os.path.join(root, d))
            
            # Process longest paths first (deepest folders) to flatten correctly
            folders_to_process.sort(key=len, reverse=True)
            
            for folder_path in folders_to_process:
                debug(f"Consolidating folder: {folder_path}")
                try:
                    entries = os.listdir(folder_path)
                except OSError as exc:
                    log_exception(f"consolidate_all_organized_folders listdir {folder_path}", exc)
                    continue

                for item in entries:
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
                                except OSError as exc:
                                    log_exception(f"consolidate_all_organized_folders move video {full_path} -> {dest_path}", exc)
                                    continue
                            debug(f"TRACK consolidated video={item} from {folder_path}")
                            
                            # Move associated sidecars
                            move_associated_sidecars(folder_path, current_directory, item, processed_files)
                        
                        # Move orphaned .srt files
                        elif ext.lower() == ".srt":
                            if not os.path.exists(dest_path):
                                try:
                                    if dry_run:
                                        log_action("MOVE", full_path, dest_path)
                                    else:
                                        shutil.move(full_path, dest_path)
                                except OSError as exc:
                                    log_exception(f"consolidate_all_organized_folders move orphan srt {full_path} -> {dest_path}", exc)
                            processed_files.add(item)
                            debug(f"TRACK consolidated orphan-srt={item}")
                
                # Clean up bookkeeping files
                remove_total_markers(folder_path)
                
                # Remove the folder if it's now empty
                try:
                    if not os.listdir(folder_path):
                        if dry_run:
                            log_action("RMDIR", folder_path)
                        else:
                            os.rmdir(folder_path)
                            debug(f"Removed consolidated folder: {folder_path}")
                except OSError as exc:
                    log_exception(f"consolidate_all_organized_folders rmdir {folder_path}", exc)

            # Also clean up any lingering container-looking folders in the root that might be empty
            for d in os.listdir(current_directory):
                path = os.path.join(current_directory, d)
                if os.path.isdir(path) and is_organized_folder(d):
                    remove_total_markers(path)
                    try:
                        if not os.listdir(path):
                            if dry_run:
                                log_action("RMDIR", path)
                            else:
                                os.rmdir(path)
                    except OSError:
                        pass

        processed_files = set()
        consolidate_all_organized_folders()
        
        # After consolidation, all videos are in the root (current_directory)
        # We need to gather and sort them for distributing into chunks
        existing_replay_videos = []
        existing_horz_videos = []
        
        for f in sorted(os.listdir(current_directory)):
            if not os.path.isfile(os.path.join(current_directory, f)):
                continue
            if f == "folderbyrec.py" or f == "replay_debug.log":
                continue
                
            _, ext = os.path.splitext(f)
            if ext.lower() in video_extensions:
                if "Replay" in f:
                    existing_replay_videos.append(f)
                elif "Rec" in f:
                    existing_horz_videos.append(f)
        
        # Combine and Sort (alphabetical ensure consistent order)
        replay_videos = sorted(existing_replay_videos)
        horz_videos = sorted(existing_horz_videos)
        debug(f"replay_videos_final={len(replay_videos)} horz_videos_final={len(horz_videos)}")

        def distribute_files(file_list, base_folder_name):
            debug(f"distribute_files base_folder_name={base_folder_name} input_count={len(file_list)}")
            chunks = [file_list[i:i + file_limit] for i in range(0, len(file_list), file_limit)]
            created_folders = []
            debug(f"distribute_files base_folder_name={base_folder_name} chunk_count={len(chunks)}")
            
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
                        except OSError as exc:
                            log_exception(f"distribute_files move video {source} -> {dest}", exc)
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
                        except OSError as exc:
                            log_exception(f"distribute_files move srt {srt_source} -> {srt_dest}", exc)

                    # Move associated sidecars with the video.
                    move_associated_sidecars(current_directory, folder_path, file_name)
            return created_folders

        final_replay_data = distribute_files(replay_videos, base_replay_name)
        final_horz_data = distribute_files(horz_videos, base_horz_name)
        debug(f"final_replay_data_count={len(final_replay_data)} final_horz_data_count={len(final_horz_data)}")

        # --- STEP 3: RENAME FOLDERS TO FINAL NAMES ---
        debug("STEP 3 START finalize temp folders")
        
        def finalize_folders(folder_data):
            total_count = 0
            final_names = []
            for temp_path, base_name, index, planned_chunk in folder_data:
                debug(f"finalize_folders entry temp_path={temp_path} base_name={base_name} index={index}")
                if dry_run:
                    count = sum(1 for item in planned_chunk if os.path.splitext(item)[1].lower() in video_extensions)
                else:
                    if not os.path.exists(temp_path):
                        debug(f"finalize_folders missing temp_path={temp_path}; skipping")
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
                            except OSError as exc:
                                log_exception(f"finalize_folders merge move {s} -> {d}", exc)
                                move_failed = True
                        if not move_failed and not os.listdir(temp_path):
                            try:
                                os.rmdir(temp_path)
                            except OSError as exc:
                                log_exception(f"finalize_folders rmdir merged temp_path={temp_path}", exc)
                    else:
                        # If it's a file (unlikely), remove it and rename
                        if dry_run:
                            log_action("REMOVE", new_path)
                            log_action("RENAME", temp_path, new_path)
                        else:
                            os.remove(new_path)
                            safe_rename(temp_path, new_path)
                else:
                    if dry_run:
                        log_action("RENAME", temp_path, new_path)
                    else:
                        safe_rename(temp_path, new_path)
                debug(f"finalize_folders finalized {temp_path} -> {new_path} count={count}")
            debug(f"finalize_folders result total_count={total_count} final_names={final_names}")
            return total_count, final_names

        replay_total, replay_final_names = finalize_folders(final_replay_data)
        horz_total, horz_final_names = finalize_folders(final_horz_data)
        debug(f"totals replay_total={replay_total} horz_total={horz_total}")

        # --- STEP 4: GROUP INTO FULL/REPLAY CONTAINERS ---
        debug("STEP 4 START group into containers")

        def group_into_container(label, total_count, child_prefix, planned_child_folders=None):
            # Pattern for child folders: "Replay 0-15"
            child_pattern = re.compile(rf"^{child_prefix} \d+-\d+$")

            if dry_run and planned_child_folders is not None:
                child_folders = planned_child_folders
            else:
                child_folders = [d for d in os.listdir(current_directory)
                                 if os.path.isdir(os.path.join(current_directory, d)) and child_pattern.match(d)]

            if total_count == 0 and not child_folders:
                debug(f"group_into_container skipping empty container label={label} total_count=0 child_prefix={child_prefix}")
                return

            container_name = f"{label} {total_count}"
            container_path = os.path.join(current_directory, container_name)
            if dry_run:
                log_action("MKDIR", container_path)
            else:
                os.makedirs(container_path, exist_ok=True)
            debug(f"group_into_container label={label} container_path={container_path} child_folders={child_folders}")

            for folder_name in child_folders:
                src = os.path.join(current_directory, folder_name)
                dest = os.path.join(container_path, folder_name)
                if not os.path.exists(src):
                    debug(f"group_into_container missing src={src}; skipping")
                    continue
                
                # Check if src is actually the container itself (should not happen with regex but safe-guard)
                if src == container_path:
                    continue

                if not os.path.exists(dest):
                    try:
                        if dry_run:
                            log_action("MOVE", src, dest)
                        else:
                            shutil.move(src, dest)
                    except OSError as exc:
                        log_exception(f"group_into_container move {src} -> {dest}", exc)
                elif os.path.isdir(dest) and os.path.isdir(src):
                    debug(f"group_into_container merge existing dest={dest} from src={src}")
                    move_failed = False
                    for item in os.listdir(src):
                        s = os.path.join(src, item)
                        d = os.path.join(dest, item)
                        try:
                            if os.path.exists(d):
                                base, ext = os.path.splitext(item)
                                n = 1
                                while True:
                                    alt_name = f"{base}__dup{n}{ext}"
                                    alt_path = os.path.join(dest, alt_name)
                                    if not os.path.exists(alt_path):
                                        d = alt_path
                                        break
                                    n += 1
                            if dry_run:
                                log_action("MOVE", s, d)
                            else:
                                shutil.move(s, d)
                        except OSError as exc:
                            log_exception(f"group_into_container merge move {s} -> {d}", exc)
                            move_failed = True
                    if not dry_run and not move_failed:
                        try:
                            if not os.listdir(src):
                                os.rmdir(src)
                        except OSError as exc:
                            log_exception(f"group_into_container rmdir merged src={src}", exc)
                else:
                    debug(f"group_into_container destination exists and not mergeable src={src} dest={dest}")

            total_file_name = f"total {total_count}"
            try:
                total_file_path = os.path.join(container_path, total_file_name)
                if dry_run:
                    log_action("WRITE", total_file_path)
                else:
                    with open(total_file_path, "w") as f:
                        f.write(f"Total: {total_count}\n")
            except OSError as exc:
                log_exception(f"group_into_container write total file {container_path}", exc)

        group_into_container(container_full_label, horz_total, base_horz_name, planned_child_folders=horz_final_names if dry_run else None)
        group_into_container(container_replay_label, replay_total, base_replay_name, planned_child_folders=replay_final_names if dry_run else None)
        debug("STEP 4 COMPLETE")

        # --- STEP 5: CREATE TOTAL FILE ---
        debug("STEP 5 START write root total")
        
        old_totals = glob.glob(os.path.join(current_directory, "total *"))
        for old_file in old_totals:
            try:
                if dry_run:
                    log_action("REMOVE", old_file)
                else:
                    os.remove(old_file)
            except OSError as exc:
                log_exception(f"remove old total file {old_file}", exc)

        grand_total = replay_total + horz_total
        total_file_name = f"total {grand_total}"
        
        total_file_path = os.path.join(current_directory, total_file_name)
        if dry_run:
            log_action("WRITE", total_file_path)
        else:
            with open(total_file_path, "w") as f:
                f.write(f"Replay Total: {replay_total}\nHorz Total: {horz_total}\nGrand Total: {grand_total}")
        debug(f"STEP 5 COMPLETE replay_total={replay_total} horz_total={horz_total} grand_total={grand_total}")

        if dry_run:
            print(f"Dry-run complete. Replay: {replay_total}, Horz: {horz_total}, Total: {grand_total}")
        else:
            print(f"Done. Replay: {replay_total}, Horz: {horz_total}, Total: {grand_total}")
        debug("DONE organize_and_count_files success")

    except Exception as exc:
        log_exception("organize_and_count_files fatal", exc)
        with open("error_log.txt", "w") as f:
            traceback.print_exc(file=f)
        debug("Traceback written to error_log.txt")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sort Replay/Rec videos into grouped folders and container folders.")
    parser.add_argument("--dry-run", action="store_true", help="Preview planned file operations without changing files.")
    args = parser.parse_args()
    organize_and_count_files(dry_run=args.dry_run)
