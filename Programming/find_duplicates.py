import os
import sys
import hashlib
import shutil
import argparse
from collections import defaultdict

# --- (Core functions: calculate_file_hash, find_duplicate_files, etc. are unchanged) ---
# --- (Scroll to the bottom for the main changes in the `main` function) ---

def find_duplicate_files(start_directory):
    """
    Finds duplicate files based on content hash in a given directory.
    This function efficiently finds duplicates by first grouping files by size,
    then calculating and comparing hashes only for files of the same size.

    Args:
        start_directory (str): The path to the directory to scan.

    Returns:
        list: A list of lists, where each inner list contains paths to duplicate files.
    """
    abs_path = os.path.abspath(start_directory)
    print(f"[*] Scanning directory: {abs_path}")
    # 1st pass: Group files by size
    file_sizes = defaultdict(list)
    for root, _, files in os.walk(abs_path):
        for filename in files:
            filepath = os.path.join(root, filename)
            # Avoid scanning the script's own quarantine folder
            if "_quarantine" in filepath:
                continue
            if os.path.isfile(filepath) and not os.path.islink(filepath):
                try:
                    file_size = os.path.getsize(filepath)
                    file_sizes[file_size].append(filepath)
                except OSError:
                    continue
    
    # 2nd pass: For files of the same size, check hashes
    hashes = defaultdict(list)
    for size, paths in file_sizes.items():
        if len(paths) < 2:
            continue

        for path in paths:
            try:
                hasher = hashlib.md5()
                with open(path, 'rb') as f:
                    while chunk := f.read(8192):
                        hasher.update(chunk)
                file_hash = hasher.hexdigest()
                hashes[file_hash].append(path)
            except (IOError, OSError):
                print(f"[!] Warning: Could not read file: {path}", file=sys.stderr)
                continue

    duplicates = [group for group in hashes.values() if len(group) > 1]
    print(f"[*] Scan complete. Found {len(duplicates)} groups of duplicate files.")
    return duplicates

def list_duplicates(duplicate_groups):
    """Prints the found groups of duplicates."""
    if not duplicate_groups:
        return
    print("\n--- Duplicate Files Found ---")
    for i, group in enumerate(duplicate_groups, 1):
        print(f"\n[+] Group {i}:")
        for path in group:
            print(f"  - {path}")

def quarantine_duplicates(duplicate_groups, base_directory):
    """Moves all but one file from each duplicate group to a quarantine folder."""
    if not duplicate_groups:
        return
    quarantine_folder = os.path.join(base_directory, "_quarantine")
    if not os.path.exists(quarantine_folder):
        os.makedirs(quarantine_folder)
    print(f"\n[*] Moving duplicates to: {quarantine_folder}")
    
    for group in duplicate_groups:
        for filepath_to_move in group[1:]:
            try:
                filename = os.path.basename(filepath_to_move)
                destination = os.path.join(quarantine_folder, filename)
                counter = 1
                while os.path.exists(destination):
                    name, ext = os.path.splitext(filename)
                    destination = os.path.join(quarantine_folder, f"{name}_{counter}{ext}")
                    counter += 1
                shutil.move(filepath_to_move, destination)
                print(f"  -> Moved: {filepath_to_move}")
            except (IOError, OSError) as e:
                print(f"[!] Error moving {filepath_to_move}: {e}", file=sys.stderr)

def interactive_delete(duplicate_groups):
    """Asks the user which duplicate files to delete for each group."""
    if not duplicate_groups:
        return
    for group in duplicate_groups:
        print("\n--- Found Duplicate Group ---")
        for i, filepath in enumerate(group):
            print(f"  [{i}] {filepath}")
        
        try:
            choice_str = input("Enter the number of the file to KEEP (e.g., '0'). Type 's' to skip: ")
            if choice_str.lower() == 's':
                continue
            keep_index = int(choice_str)
            if not 0 <= keep_index < len(group):
                raise IndexError
            
            for i, filepath in enumerate(group):
                if i != keep_index:
                    os.remove(filepath)
                    print(f"  - Deleted: {filepath}")
        except (ValueError, IndexError):
            print("[!] Invalid selection. Skipping this group.")

def auto_delete(duplicate_groups):
    """Automatically keeps one file and deletes the rest. DANGEROUS."""
    if not duplicate_groups:
        return
    print("\n[!] WARNING: Automatic Deletion Mode")
    print("This will permanently delete duplicate files, keeping only one copy from each group.")
    confirm = input("Are you absolutely sure you want to proceed? (yes/no): ")
    
    if confirm.lower() != 'yes':
        print("[*] Aborted by user.")
        return

    print("[*] Proceeding with automatic deletion...")
    for group in duplicate_groups:
        for filepath in group[1:]:
            try:
                os.remove(filepath)
                print(f"  - Deleted: {filepath}")
            except OSError as e:
                print(f"[!] Error deleting {filepath}: {e}", file=sys.stderr)

def main():
    parser = argparse.ArgumentParser(
        description="Find and handle duplicate files in a directory.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    # --- HERE ARE THE CHANGES ---
    parser.add_argument(
        "directory", 
        nargs='?',                                                           # <-- CHANGED: Make the argument optional
        default=os.getcwd(),                                                 # <-- ADDED: Default to the current working directory
        help="The directory to scan. Defaults to the current directory if omitted." # <-- CHANGED: Updated help text
    )
    
    action_group = parser.add_mutually_exclusive_group()
    action_group.add_argument("-l", "--list", action="store_true",
                              help="List duplicate files. (Safe Mode)")
    action_group.add_argument("-q", "--quarantine", action="store_true",
                              help="Move duplicates to a '_quarantine' folder. (Default Action)")
    action_group.add_argument("-i", "--interactive", action="store_true",
                              help="Interactively decide which files to delete.")
    action_group.add_argument("-d", "--delete", action="store_true",
                              help="DANGEROUS: Automatically delete duplicates, keeping one copy.")

    args = parser.parse_args()
    
    if not os.path.isdir(args.directory):
        print(f"[!] Error: The specified directory does not exist: {args.directory}", file=sys.stderr)
        sys.exit(1)

    duplicates = find_duplicate_files(args.directory)
    
    if not duplicates:
        print("\n[*] No duplicate files were found.")
        sys.exit(0)

    # Determine action. Quarantine is the default if no other action is specified.
    if args.list:
        list_duplicates(duplicates)
    elif args.interactive:
        interactive_delete(duplicates)
    elif args.delete:
        auto_delete(duplicates)
    else: # Default action
        quarantine_duplicates(duplicates, args.directory)

if __name__ == "__main__":
    main()