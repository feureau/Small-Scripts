#!/usr/bin/env python3
"""
sanitize_filenames.py

Place this script in a folder (e.g. "scripts/") and invoke it from any directory.
It will expand glob patterns you pass, sanitize filenames to include only letters, numbers, and spaces,
and then either rename files in-place or copy them into a specified output directory.

Usage:
  # Rename files in-place (default):
  python sanitize_filenames.py "*.txt" "data/*.csv"

  # Dry-run to see changes without modifying files:
  python sanitize_filenames.py -d "*.txt" "data/*.csv"

  # Copy sanitized files into a folder:
  python sanitize_filenames.py -o clean_files "*.txt" "data/*.csv"

  # Dry-run copy:
  python sanitize_filenames.py -d -o clean_files "*.txt" "data/*.csv"

  # Process files recursively:
  python sanitize_filenames.py "photos/**/*.jpg"

  # Help:
  python sanitize_filenames.py -h
"""

import os
import re
import glob
import shutil
import argparse
import unicodedata
import sys

# Ensure stdout can handle unicode or fallback gracefully
def safe_print(msg: str):
    try:
        print(msg)
    except UnicodeEncodeError:
        # Fallback for environments (like some Windows CMD) that might crash on unicode
        print(msg.encode(sys.stdout.encoding, errors='replace').decode(sys.stdout.encoding))

# Regex for non-alphanumeric characters
NON_ALPHANUMERIC = re.compile(r"[^A-Za-z0-9]+")

def sanitize_name(name: str) -> str:
    """
    Sanitize filename part:
    1. Normalize Unicode (decomposes accented chars/fancy fonts).
    2. Filter out marks (accents).
    3. Replace non-alphanumeric with spaces.
    4. PascalCase words.
    """
    # Normalize NFKD to decompose characters (e.g., 'í' -> 'i' + accent tag)
    normalized = unicodedata.normalize('NFKD', name)
    # Filter out marks (accents) but keep base characters
    no_marks = "".join(c for c in normalized if not unicodedata.combining(c))
    # Filter out everything except A-Z, a-z, 0-9 by replacing with spaces
    spaced = NON_ALPHANUMERIC.sub(" ", no_marks)
    # Split, capitalize each word, and join
    tokens = spaced.strip().split()
    return "".join(token.capitalize() for token in tokens)


def process(patterns: list[str], execute: bool, output_dir_abs: str | None) -> None:
    """
    For each glob pattern, find matching files and either rename them in-place or
    copy sanitized files into an output directory.

    :param patterns: List of glob patterns (e.g. ['*.jpg', 'data/*.png'])
    :param execute: If True, perform file operations; if False, only print planned actions.
    :param output_dir_abs: Absolute path to the directory to copy sanitized files into.
                           If None, files are renamed in-place.
    """
    if output_dir_abs:
        try:
            os.makedirs(output_dir_abs, exist_ok=True)
        except OSError as e:
            print(f"Error: Could not create output directory '{output_dir_abs}': {e}")
            return 

    processed_sources = set() 

    for pattern in patterns:
        # Sorting makes behavior more predictable, especially with potential name conflicts.
        # Using recursive=True to support '**' in patterns.
        try:
            glob_results = glob.glob(pattern, recursive=True)
        except Exception as e:
            print(f"Error expanding glob pattern '{pattern}': {e}")
            continue
        
        sorted_glob_results = sorted(glob_results)

        for src_path_relative in sorted_glob_results:
            abs_src_path = os.path.abspath(src_path_relative)
            
            if abs_src_path in processed_sources:
                continue # Already processed this exact file path
            
            if not os.path.isfile(abs_src_path):
                continue

            # Add to processed_sources *before* any potential rename, using its original absolute path
            processed_sources.add(abs_src_path)

            dirpath, filename = os.path.split(abs_src_path)
            name_part, ext = os.path.splitext(filename)
            
            sanitized_name_part = sanitize_name(name_part)

            if sanitized_name_part == name_part:
                # Filename part is already sanitized according to the rule.
                safe_print(f"No change required for name of '{src_path_relative}' (already sanitized).")
                continue # Go to the next file
            
            # If we reach here, sanitized_name_part is different from name_part,
            # so an operation (rename or copy with new name) is intended.

            current_base_name_for_dest = sanitized_name_part
            
            if output_dir_abs:
                target_operation_dir = output_dir_abs
                action_verb = "Copying"
            else:
                target_operation_dir = dirpath 
                action_verb = "Renaming"

            # Determine initial proposed new filename and destination path
            new_filename_candidate = current_base_name_for_dest + ext
            dst_candidate_path = os.path.join(target_operation_dir, new_filename_candidate)
            
            final_dst_path = dst_candidate_path
            final_new_filename_for_print = new_filename_candidate # For print messages
            
            counter = 1
            # Loop to find a unique name if dst_candidate_path already exists
            while os.path.exists(final_dst_path):
                # Check if it's an in-place rename targeting the source file itself (e.g., case change on Windows)
                is_self_rename_case_change = (
                    not output_dir_abs and # Must be an in-place rename
                    os.path.normcase(abs_src_path) == os.path.normcase(final_dst_path) and # Paths are the same ignoring case
                    os.path.isfile(final_dst_path) and # Ensure final_dst_path is a file before samefile
                    os.path.samefile(abs_src_path, final_dst_path) # And they point to the same physical file
                )
                
                if is_self_rename_case_change:
                    # Destination is the source file itself (e.g. 'File.txt' -> 'file.txt' on Win).
                    # os.rename will handle this. No need to add "(1)".
                    break 
                else:
                    # Collision with a *different* file, or collision when copying.
                    # Append counter to find a unique name.
                    if counter == 1: # Only print notice on the first collision detection for this file
                         notice_prefix = "[DRY-RUN] " if not execute else ""
                         safe_print(f"{notice_prefix}Notice: Proposed name '{os.path.basename(final_dst_path)}' for '{src_path_relative}' (to be {action_verb.lower()}) already exists and is a different file. Attempting to find a unique name.")

                    unique_suffixed_name_part = f"{current_base_name_for_dest} ({counter})"
                    final_new_filename_for_print = unique_suffixed_name_part + ext # Update for print
                    final_dst_path = os.path.join(target_operation_dir, final_new_filename_for_print)
                    counter += 1
                    if counter > 100: # Safety break
                        safe_print(f"Error: Could not find a unique name for '{src_path_relative}' (sanitized base: '{current_base_name_for_dest}') after 100 attempts in directory '{target_operation_dir}'. Skipping this file.")
                        final_dst_path = None # Signal failure
                        break
            
            if final_dst_path is None: # Failed to find a unique name
                continue # Skip to the next source file

            prefix = "" if execute else "[DRY-RUN] "
            
            # This check is mostly a safeguard.
            # If src and final_dst_path are the same physical file AND it's a copy operation
            # AND output_dir is the same as src dir, this could happen if the original file
            # was clean and the name didn't change. However, the `sanitized_name_part == name_part`
            # check at the top should prevent operations on already-clean names.
            try:
                if output_dir_abs and os.path.exists(final_dst_path) and os.path.samefile(abs_src_path, final_dst_path):
                    safe_print(f"{prefix}Skipping {action_verb.lower()}: source '{src_path_relative}' and destination '{final_dst_path}' are the same file, and name did not require change for this target.")
                    continue
            except FileNotFoundError: 
                pass 


            safe_print(f"{prefix}{action_verb}: '{src_path_relative}' -> '{final_dst_path}'")

            if execute:
                try:
                    if output_dir_abs: # Copy
                        shutil.copy2(abs_src_path, final_dst_path)
                    else: # Rename
                        # If abs_src_path and final_dst_path are identical strings, os.rename might be a no-op or error.
                        # However, if they differ by case on a case-sensitive FS but represent the same intended file
                        # (e.g. "file.txt" to "File.TXT"), os.rename should work.
                        # The collision logic handles cases where final_dst_path is a *different* existing file.
                        # If it's a case-only rename of the *same* file, is_self_rename_case_change allowed it.
                        if abs_src_path == final_dst_path: # Truly identical string paths (e.g. no change after all logic)
                            safe_print(f"Note: Source and destination path for rename are identical ('{src_path_relative}'). No effective action taken.")
                        else:
                            os.rename(abs_src_path, final_dst_path)
                except FileExistsError as e:
                    # This should be rare given the collision handling loop, but can happen in race conditions
                    # or if os.path.exists behaves unexpectedly with os.rename.
                    safe_print(f"Error: File still existed at destination '{final_dst_path}' during {action_verb.lower()} operation for '{src_path_relative}'. Skipping. Original error: {e}")
                except Exception as e:
                    safe_print(f"Error performing {action_verb.lower()} on '{src_path_relative}' to '{final_dst_path}': {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Sanitize filenames to include only letters, numbers, and spaces."
    )
    parser.add_argument(
        "patterns",
        nargs='+',
        help="Glob patterns for files to process (e.g. '*.mp3', 'photos/*.PNG', 'docs/**')."
    )
    parser.add_argument(
        "-d", "--dry-run",
        action='store_true',
        help="Run in dry-run mode (no actual file modifications)."
    )
    parser.add_argument(
        "-o", "--output-dir",
        metavar="DIR",
        help="Copy sanitized files into specified directory instead of renaming in-place."
    )
    args = parser.parse_args()

    execute = not args.dry_run
    
    abs_output_dir = os.path.abspath(args.output_dir) if args.output_dir else None
    
    process(args.patterns, execute, abs_output_dir)


if __name__ == "__main__":
    main()