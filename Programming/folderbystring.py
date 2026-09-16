"""
# FolderByString.py - Smart Media Organizer v4

Organizes media files (.mp4/.mkv/.flac) into folders based on title prefix.
Groups all episodes of same series into single flat folder (e.g., Lanterns/ contains all S01E#, S02E#).
Also moves subtitle files (.srt) with their corresponding media.

Usage:
    python FolderByString.py <target_directory> [--preview|-p]
"""

import sys
import os
import shutil


def get_folder_name(filename):
    """Extract base title, grouping episodes under single series name."""
    basename = filename.lower()
    
    # Remove extension first
    for ext in ['.mp4', '.mkv', '.flac']:
        if basename.endswith(ext):
            basename = os.path.splitext(basename)[0]
            break
    
    # Detect episode pattern (S01E02, S2E5, etc.)
    import re
    match = re.search(r'S\d+[a-z]*e\d+', basename, re.IGNORECASE)
    
    if match:
        # Episode found - extract series name before episode marker
        prefix = basename[:match.start()]
        
        # Clean up trailing spaces and hyphens
        prefix = prefix.strip()
        
        # For "Lanterns - S01E02", return just "Lanterns"
        if prefix.endswith('-'):
            words = prefix.rsplit(' ', 1)
            if len(words) == 2:
                prefix = words[0].strip()
        
        # Remove trailing hyphens/periods for clean series name
        prefix = prefix.rstrip('-.')
        
        return prefix.strip()
    
    # No episode pattern - use full base name as folder
    basename_no_ext = os.path.splitext(basename)[0]
    return basename_no_ext


def is_media_file(filepath):
    """Check if file is a media file (.mp4, .mkv, .flac)."""
    filename = os.path.basename(filepath).lower()
    return any(filename.endswith(ext) for ext in ['.mp4', '.mkv', '.flac'])


def main():
    target_path = None
    has_preview = False
    
    # Parse arguments
    if len(sys.argv) > 1:
        first_arg = sys.argv[1]
        
        # Handle wildcard - means current directory
        if first_arg == '*':
            target_path = os.getcwd()
            # Check for preview flag in remaining args
            has_preview = '-p' in sys.argv or '--preview' in sys.argv
        
        elif not first_arg.startswith('-') and '/' not in first_arg:
            target_path = first_arg
        
        # Check for preview flag anywhere
        if '-p' in sys.argv or '--preview' in sys.argv:
            has_preview = True
    
    # Default to current directory if no valid path given
    if not target_path or not os.path.exists(target_path):
        target_path = os.getcwd()
    
    print("[Initialization] Scanning: {}".format(target_path))
    
    try:
        all_items = os.listdir(target_path)
    except PermissionError as e:
        print("[Error] Cannot access directory.")
        sys.exit(1)
    
    # Collect media files and their target folders (only first occurrence sets the folder name)
    unique_folders = set()
    media_to_move = []
    srt_files = []  # Keep list of all .srt files for later matching
    
    for item in all_items:
        filepath = os.path.join(target_path, item)
        
        if not os.path.isfile(filepath):
            continue
        
        filename_lower = item.lower()
        
        # Check media files first (these determine folder names)
        is_media = any(filename_lower.endswith(ext) for ext in ['.mp4', '.mkv', '.flac'])
        
        if is_media:
            # Skip hidden files and script itself
            if item.startswith('.') or 'folderbystring' in filename_lower:
                continue
            
            folder_name = get_folder_name(item)
            
            # Only add unique folder names (first file of each series determines the name)
            if folder_name not in unique_folders:
                unique_folders.add(folder_name)
            
            media_to_move.append((filepath, item))
        
        # Collect all .srt files separately for matching later
        elif filename_lower.endswith('.srt'):
            # Skip hidden files and script
            if item.startswith('.') or 'folderbystring' in filename_lower:
                continue
            
            srt_files.append((os.path.join(target_path, item), item))
    
    # Nothing to organize
    if not media_to_move:
        print("[Error] No media files (.mp4/.mkv/.flac) found.")
        sys.exit(1)
    
    # Preview mode
    if has_preview:
        print()
        print("[PREVIEW MODE]")
        print("=" * 60)
        
        for folder in sorted(unique_folders):
            try:
                safe = str(folder).encode('utf-8', errors='strict').decode('cp1252')[:64]
                print("  - {}".format(safe.ljust(64)))
            except (UnicodeEncodeError, UnicodeDecodeError):
                # Show as-is for UTF-8 characters
                print("  - {}".format(folder))
        
        print()
        print("Total folders to create: {}\n".format(len(unique_folders)))
        
        response = input("Execute? (y/n): ").strip().lower()
        
        if response in ['y', 'yes']:
            has_preview = False
    
    # Create destination folders for media files
    folder_set = set()
    for filepath, filename in media_to_move:
        folder_name = get_folder_name(filename)
        folder_set.add(folder_name)
    
    for folder_name in sorted(folder_set):
        dest_folder = os.path.join(target_path, folder_name)
        
        if not os.path.exists(dest_folder):
            print("[Operation] Creating: {}".format(folder_name))
            os.makedirs(dest_folder)
        else:
            print("[Status] Exists: {}".format(folder_name))
    
    # Move media files to their folders (duplicates are skipped by set logic)
    moved_count = 0
    
    for filepath, filename in media_to_move:
        folder_name = get_folder_name(filename)
        dest_path = os.path.join(target_path, folder_name, filename)
        
        try:
            shutil.move(filepath, dest_path)
            print("[Transfer] {} -> {}/".format(filename, folder_name))
            moved_count += 1
            
        except Exception as e:
            print("[Error] Failed {}: {}".format(filename, str(e)))
    
    # Move subtitle files to match with their media by checking prefix similarity
    for srt_path, srt_filename in srt_files:
        try:
            srt_basename = os.path.basename(srt_filename).lower()
            
            # Find matching folder based on series name pattern
            matched_folder_name = None
            
            # Try exact match first (e.g., "Lanterns - S01E01" matches subtitle)
            for folder in sorted(folder_set):
                if srt_basename.startswith(folder.lower()) or folder.lower() == 'lanterns':
                    matched_folder_name = folder
                    break
            
            # If no exact match, try partial matching (e.g., "Lanterns.srt" matches Lanterns/*)
            if not matched_folder_name and folder_set:
                for folder in sorted(folder_set):
                    if folder.lower() == 'lanterns' or srt_basename.startswith('lanterns'):
                        matched_folder_name = folder
                        break
            
            # For single non-episode titles (e.g., "Disclosure.Day.2026...")
            if not matched_folder_name:
                for folder in sorted(folder_set):
                    if srt_basename.lower().startswith(folder.lower()) or \
                       folder.lower() in srt_basename[:50]:  # Match first ~50 chars
                        matched_folder_name = folder
                        break
            
            if matched_folder_name:
                dest_path = os.path.join(target_path, matched_folder_name, srt_filename)
                
                try:
                    shutil.move(srt_path, dest_path)
                    print("[Transfer] {} -> {}/".format(srt_filename, matched_folder_name))
                    moved_count += 1
                    
                except Exception as e:
                    pass  # Skip on error for subtitles
            
        except Exception:
            pass
    
    print()
    print("[Termination] Done. Files organized: {}\n".format(moved_count))


if __name__ == "__main__":
    main()
