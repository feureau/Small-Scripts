#!/usr/bin/env python

"""
# =================================================================================== #
#                                                                                     #
#                                  FileRename.py                                      #
#                                                                                     #
# =================================================================================== #

A powerful and user-friendly command-line utility for bulk renaming files within
a directory tree. This script searches for files based on a pattern and replaces
a specified part of their names with a new string.

It is designed to be safe and intuitive, featuring a recursive-by-default search
and an interactive confirmation step to prevent accidental changes.

-------------------------------------------------------------------------------------
Version: 1.2
Author: [Your Name Here]
Date: 2025-08-15
-------------------------------------------------------------------------------------

---------------------------------
--         FEATURES          --
---------------------------------

*   RECURSIVE BY DEFAULT: Automatically searches the current directory and all of
    its subdirectories for matching files. No special flags are needed for this,
    making it fast and easy to use.

*   INTERACTIVE CONFIRMATION: Displays a full list of all proposed changes and
    waits for the user's explicit 'y' confirmation before renaming any files.
    This is a critical safety feature to prevent mistakes.

*   FLEXIBLE PATTERN MATCHING: Intelligently handles command-line arguments,
    allowing the use of unquoted wildcards (like *.txt) in most shells.

*   STRING REMOVAL: To remove a piece of a filename, simply provide an empty
    string ("") as the replacement string.

*   SHALLOW SEARCH OPTION: For cases where you only want to search the current
    directory (and not subdirectories), a special flag (`-s`) is available.

*   CROSS-PLATFORM: Works on Windows, macOS, and Linux.

---------------------------------
--           USAGE           --
---------------------------------

The script is called from the command line with the following structure:

python filerename.py [file_pattern] [old_string] [new_string] [options]

--- ARGUMENTS ---

1.  [file_pattern]:
    The pattern to match files against. The shell's wildcard expansion is
    supported. For simple cases, quotes are not needed.
    Examples: *.txt, request-*.log, image_?.jpg

2.  [old_string]:
    The exact string within the filenames that you want to replace. If the
    string contains spaces, enclose it in quotes.

3.  [new_string]:
    The string that will replace [old_string]. To delete [old_string]
    entirely, use a pair of empty quotes (""). If the string contains spaces,
    enclose it in quotes.

--- OPTIONS ---

  -s, --shallow
    Disables the default recursive behavior and performs a "shallow" search,
    meaning it will ONLY look for files in the current working directory.

  -h, --help
    Displays this help message and exits.

---------------------------------
--          EXAMPLES         --
---------------------------------

(Assume you have opened a terminal in your project's root folder)

1. BASIC RECURSIVE RENAME:
   Rename all '.log' files in the current folder AND all subfolders by changing
   "backup" to "archived".

   > python filerename.py *.log "backup" "archived"

2. REMOVING A STRING (DELETION):
   Recursively find all '.txt' files and remove the suffix "_draft" from their
   names. This is the most common use case for the empty "" string.

   > python filerename.py *.txt "_draft" ""

3. SHALLOW SEARCH (NON-RECURSIVE):
   Rename files ONLY in the current directory. Do not touch any subfolders.
   Here, we change "temp_" to "final_" in all 'data-*.csv' files.

   > python filerename.py data-*.csv "temp_" "final_" -s

4. FILENAMES WITH SPACES:
   Recursively rename files, replacing "Final Report" with "Official Document".
   Quotes are necessary because of the spaces.

   > python filerename.py *.docx "Final Report" "Official Document"

---------------------------------
--     INSTALLATION & SETUP    --
---------------------------------

1.  Requires Python 3.
2.  Save this script as `filerename.py`.
3.  To run it from any directory, you can either:
    a) Call it with its full path: `python C:\\path\\to\\scripts\\filerename.py ...`
    b) [RECOMMENDED] Add the folder containing `filerename.py` to your system's
       PATH environment variable. After doing this, you can simply type
       `filerename.py ...` from any folder.

"""

import os
import sys
import glob
import re

def display_help():
    """Prints the help message."""
    print("Usage: python FileRename.py [file_pattern] old_string new_string [-s] [-r]")
    print("\nRecursively renames files by replacing a string in their names.")
    print("The search is RECURSIVE BY DEFAULT.")
    print("\nArguments:")
    print("  file_pattern   The file pattern to match (e.g., *.txt, \"**/*.log\").")
    print("  old_string     The string (or regex pattern) to be replaced in the filenames.")
    print("  new_string     The string to replace with. Use \"\" for an empty string.")
    print("\nOptions:")
    print("  -s, --shallow    Disables recursion and searches ONLY the current directory.")
    print("  -r, --regex      Treats old_string as a Regular Expression.")
    print("  -p, --prefix     Prepends a string to the filenames.")
    print("\nExamples:")
    print("  # Recursively rename all .txt files in current folder and all subfolders")
    print("  python FileRename.py *.txt draft final")
    print("\n  # Rename .jpg files ONLY in the current folder (shallow search)")
    print("  python FileRename.py *.jpg vacation holiday -s")
    print("\n  # Use Regex to remove a date pattern (e.g., 20240415) from filenames")
    print("  python FileRename.py * \" - \\d{8}\" \"\" -r")
    print("\n  # Add a prefix to all .jpg files")
    print("  python FileRename.py *.jpg --prefix \"Trip_2023_\"")

def rename_files(files_to_process, old_string=None, new_string=None, use_regex=False, prefix=None):
    """
    Proposes and executes file renames after user confirmation.
    """
    if not files_to_process:
        print("\nNo files matching the criteria were found.")
        return

    changes = []
    for original_path in files_to_process:
        if not os.path.isfile(original_path):
            continue

        original_filename = os.path.basename(original_path)
        new_filename = original_filename
        
        match_found = False

        if old_string is not None and new_string is not None:
            if use_regex:
                try:
                    if re.search(old_string, original_filename):
                        new_filename = re.sub(old_string, new_string, original_filename)
                        match_found = (new_filename != original_filename)
                except re.error as e:
                    print(f"Error in Regex pattern: {e}")
                    return
            else:
                if old_string in original_filename:
                    new_filename = original_filename.replace(old_string, new_string)
                    match_found = True

        if prefix:
            new_filename = prefix + new_filename
            match_found = True

        if match_found:
            directory = os.path.dirname(original_path)
            new_path = os.path.join(directory, new_filename)
            changes.append((original_path, new_path))

    if not changes:
        print(f"\nScan complete. Found {len(files_to_process)} file(s) matching the pattern, but none contained the string/pattern: '{old_string}'.")
        return

    print("\nThe following files will be renamed:")
    for original, new in changes:
        print(f'  "{original}"  ->  "{new}"')

    try:
        confirm = input("\nDo you want to proceed with these changes? (y/n): ")
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        return

    if confirm.lower() in ('y', 'yes'):
        print("\nRenaming files...")
        for original, new in changes:
            try:
                os.rename(original, new)
                print(f'  Renamed: "{original}"')
            except OSError as e:
                print(f"  Error renaming {original}: {e}")
        print("\nOperation complete.")
    else:
        print("\nOperation cancelled. No files were changed.")

def main():
    args = sys.argv[1:]
    if not args or "-h" in args or "--help" in args:
        display_help()
        sys.exit(0)
    
    print(f"--- File Rename Script ---")
    print(f"Working Directory: {os.getcwd()}")
    
    # --- LOGIC CHANGE HERE ---
    # Recursion is now ON by default. The '-s' flag turns it OFF.
    recursive = True
    if '-s' in args or '--shallow' in args:
        recursive = False
        if '-s' in args: args.remove('-s')
        if '--shallow' in args: args.remove('--shallow')
    
    # Regex support
    use_regex = False
    if '-r' in args or '--regex' in args:
        use_regex = True
        if '-r' in args: args.remove('-r')
        if '--regex' in args: args.remove('--regex')
    
    # Prefix support
    prefix = None
    if '-p' in args or '--prefix' in args:
        try:
            idx = args.index('-p') if '-p' in args else args.index('--prefix')
            prefix = args[idx + 1]
            # Remove flag and value
            args.pop(idx + 1)
            args.pop(idx)
        except (IndexError, ValueError):
            print("\nError: --prefix requires a value.")
            sys.exit(1)
    
    if len(args) < 1 or (not prefix and len(args) < 3):
        print("\nError: Invalid number of arguments.")
        display_help()
        sys.exit(1)

    new_string = None
    old_string = None
    
    if len(args) >= 3:
        new_string = args.pop()
        old_string = args.pop()
    
    file_inputs = args
    
    # If the user enters `*.txt`, the shell might expand it. We'll just use the first item as the pattern.
    pattern = file_inputs[0]
    
    print(f"Searching for files matching pattern: '{pattern}'")
    if old_string is not None:
        print(f"Replacing {'regex' if use_regex else 'string'}: '{old_string}' -> '{new_string}'")
    if prefix:
        print(f"Adding prefix: '{prefix}'")
    print(f"Recursive mode: {'On (Default)' if recursive else 'Off (-s flag used)'}")
    print("---------------------------------")
    
    # Use the pattern to search with glob.
    # The '**/' prefix is what enables glob to search subdirectories.
    pathname = os.path.join('**', pattern) if recursive else pattern
    files_to_process = glob.glob(pathname, recursive=recursive)
        
    rename_files(files_to_process, old_string, new_string, use_regex=use_regex, prefix=prefix)

if __name__ == "__main__":
    main()