import os
import shutil
import traceback
import glob
import argparse
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
            debug(f"collect_from_folders prefix={prefix} base_dirs={base_dirs}")
            for base_dir in base_dirs:
                try:
                    entries = os.listdir(base_dir)
                except OSError as exc:
                    log_exception(f"collect_from_folders listdir base_dir={base_dir}", exc)
                    continue

                folders = [d for d in entries
                           if os.path.isdir(os.path.join(base_dir, d)) and d.startswith(prefix)]

                # Sort folders numerically by index
                folders.sort(key=get_folder_index)
                debug(f"collect_from_folders base_dir={base_dir} folders={folders}")

                for folder_name in folders:
                    folder_path = os.path.join(base_dir, folder_name)
                    try:
                        folder_content = os.listdir(folder_path)
                    except OSError as exc:
                        log_exception(f"collect_from_folders listdir folder_path={folder_path}", exc)
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
                                    except OSError as exc:
                                        log_exception(f"collect_from_folders move video {full_path} -> {dest_path}", exc)
                                        continue
                                video_list.append(item)
                                processed_files.add(item)
                                debug(f"TRACK video={item} from {folder_path}")
                                
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
                                        except OSError as exc:
                                            log_exception(f"collect_from_folders move srt {srt_full_path} -> {srt_dest}", exc)
                                    processed_files.add(srt_name)
                                    debug(f"TRACK srt={srt_name}")

                                # Move associated sidecars with the video.
                                move_associated_sidecars(folder_path, current_directory, item, processed_files)
                            
                            # Move any other .srt files that might be orphaned
                            elif ext.lower() == ".srt":
                                if not os.path.exists(dest_path):
                                    try:
                                        if dry_run:
                                            log_action("MOVE", full_path, dest_path)
                                        else:
                                            shutil.move(full_path, dest_path)
                                    except OSError as exc:
                                        log_exception(f"collect_from_folders move orphan srt {full_path} -> {dest_path}", exc)
                                processed_files.add(item)
                                debug(f"TRACK orphan-srt={item}")

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
                    except OSError as exc:
                        # Folder might be locked, skip it for now
                        log_exception(f"collect_from_folders rmdir folder_path={folder_path}", exc)

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
                except OSError as exc:
                    log_exception(f"collect_from_folders rmdir base_dir={base_dir}", exc)

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
        debug(f"container_dirs={container_dirs}")
        debug(f"base_dirs={base_dirs}")

        collect_from_folders(base_replay_name, base_dirs, existing_replay_videos, processed_files)
        collect_from_folders(base_horz_name, base_dirs, existing_horz_videos, processed_files)
        debug(f"existing_replay_videos={len(existing_replay_videos)} existing_horz_videos={len(existing_horz_videos)} processed_files={len(processed_files)}")
        
        # --- STEP 2: GATHER NEW FILES ---
        debug("STEP 2 START gather new files")
        
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
        debug(f"new_replay_videos={len(new_replay_videos)} new_horz_videos={len(new_horz_videos)}")
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
                    except OSError as exc:
                        log_exception(f"group_into_container cleanup old container {path}", exc)

            if dry_run and planned_child_folders is not None:
                child_folders = planned_child_folders
            else:
                child_folders = [d for d in os.listdir(current_directory)
                                 if os.path.isdir(os.path.join(current_directory, d)) and d.startswith(child_prefix)]

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
