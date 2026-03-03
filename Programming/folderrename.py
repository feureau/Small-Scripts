#!/usr/bin/env python

"""
FolderRename.py

Bulk rename folders by replacing text (or regex) in directory names.
Recursive search is on by default.
"""

import glob
import os
import re
import sys


def display_help():
    print("Usage: python folderrename.py [folder_pattern] [old_string] [new_string] [options]")
    print("\nRecursively renames folders by replacing text in their names.")
    print("The search is RECURSIVE BY DEFAULT.")
    print("\nArguments:")
    print("  folder_pattern  Folder name pattern (e.g., project-*, *_backup).")
    print("  old_string      String (or regex pattern with -r) to replace.")
    print("  new_string      Replacement string. Use \"\" to remove old_string.")
    print("\nOptions:")
    print("  -s, --shallow   Search only current directory (disable recursion).")
    print("  -r, --regex     Treat old_string as a regular expression.")
    print("  -p, --prefix    Prepend text to matching folder names.")
    print("  -h, --help      Show this help and exit.")
    print("\nExamples:")
    print("  python folderrename.py \"*\" old new")
    print("  python folderrename.py \"project-*\" \"_draft\" \"\"")
    print("  python folderrename.py \"*\" \"^2024_\" \"2026_\" -r")
    print("  python folderrename.py \"*\" --prefix \"ARCHIVE_\" -s")


def rename_folders(folders_to_process, old_string=None, new_string=None, use_regex=False, prefix=None):
    if not folders_to_process:
        print("\nNo folders matching the criteria were found.")
        return

    changes = []

    # Rename deepest folders first so parent path changes do not invalidate children.
    folders_to_process = sorted(
        set(folders_to_process),
        key=lambda p: (p.count(os.sep), len(p)),
        reverse=True,
    )

    for original_path in folders_to_process:
        if not os.path.isdir(original_path):
            continue

        original_name = os.path.basename(original_path.rstrip(os.sep))
        parent_dir = os.path.dirname(original_path.rstrip(os.sep))
        new_name = original_name
        match_found = False

        if old_string is not None and new_string is not None:
            if use_regex:
                try:
                    if re.search(old_string, original_name):
                        new_name = re.sub(old_string, new_string, original_name)
                        match_found = new_name != original_name
                except re.error as exc:
                    print(f"Error in regex pattern: {exc}")
                    return
            else:
                if old_string in original_name:
                    new_name = original_name.replace(old_string, new_string)
                    match_found = True

        if prefix:
            new_name = prefix + new_name
            match_found = True

        if not match_found or new_name == original_name:
            continue

        new_path = os.path.join(parent_dir, new_name) if parent_dir else new_name
        changes.append((original_path, new_path))

    if not changes:
        print(
            f"\nScan complete. Found {len(folders_to_process)} folder(s), but no rename changes were produced."
        )
        return

    print("\nThe following folders will be renamed:")
    for original, new in changes:
        print(f'  "{original}"  ->  "{new}"')

    try:
        confirm = input("\nDo you want to proceed with these changes? (y/n): ")
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        return

    if confirm.lower() not in ("y", "yes"):
        print("\nOperation cancelled. No folders were changed.")
        return

    print("\nRenaming folders...")
    for original, new in changes:
        if os.path.exists(new):
            print(f'  Skipped (target exists): "{original}" -> "{new}"')
            continue
        try:
            os.rename(original, new)
            print(f'  Renamed: "{original}"')
        except OSError as exc:
            print(f'  Error renaming "{original}": {exc}')

    print("\nOperation complete.")


def parse_flag_with_value(args, short_flag, long_flag, error_message):
    if short_flag in args or long_flag in args:
        try:
            idx = args.index(short_flag) if short_flag in args else args.index(long_flag)
            value = args[idx + 1]
            args.pop(idx + 1)
            args.pop(idx)
            return value
        except (IndexError, ValueError):
            print(f"\nError: {error_message}")
            sys.exit(1)
    return None


def main():
    args = sys.argv[1:]
    if not args or "-h" in args or "--help" in args:
        display_help()
        sys.exit(0)

    print("--- Folder Rename Script ---")
    print(f"Working Directory: {os.getcwd()}")

    recursive = True
    if "-s" in args or "--shallow" in args:
        recursive = False
        if "-s" in args:
            args.remove("-s")
        if "--shallow" in args:
            args.remove("--shallow")

    use_regex = False
    if "-r" in args or "--regex" in args:
        use_regex = True
        if "-r" in args:
            args.remove("-r")
        if "--regex" in args:
            args.remove("--regex")

    prefix = parse_flag_with_value(args, "-p", "--prefix", "--prefix requires a value.")

    if len(args) < 1 or (not prefix and len(args) < 3):
        print("\nError: Invalid number of arguments.")
        display_help()
        sys.exit(1)

    old_string = None
    new_string = None
    if len(args) >= 3:
        new_string = args.pop()
        old_string = args.pop()

    pattern = args[0]

    print(f"Searching for folders matching pattern: '{pattern}'")
    if old_string is not None:
        mode = "regex" if use_regex else "string"
        print(f"Replacing {mode}: '{old_string}' -> '{new_string}'")
    if prefix:
        print(f"Adding prefix: '{prefix}'")
    print(f"Recursive mode: {'On (Default)' if recursive else 'Off (-s flag used)'}")
    print("---------------------------------")

    pathname = os.path.join("**", pattern) if recursive else pattern
    matches = glob.glob(pathname, recursive=recursive)
    folders_to_process = [p for p in matches if os.path.isdir(p)]

    rename_folders(
        folders_to_process,
        old_string=old_string,
        new_string=new_string,
        use_regex=use_regex,
        prefix=prefix,
    )


if __name__ == "__main__":
    main()
