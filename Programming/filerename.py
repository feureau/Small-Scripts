#!/usr/bin/env python3

r"""
# 📂 FileRename.py
> **A powerful, safety-first bulk rename utility for power users.**

Recursively searches directories for files matching a pattern and replaces specific strings or regex patterns within their names. Designed to be fast, recursive by default, and interactive for safety.

---

## 🚀 Key Features
- 🔄 **Recursive by Default:** Automatically dives into subfolders.
- 🛡️ **Interactive Safety:** Preview all changes before committing.
- 🔍 **Flexible Matching:** Supports standard wildcards (*, ?) and Regular Expressions.
- 🔠 **Case Sensitivity Control:** Optionally ignore case matching with `-i`.
- 🛠️ **Multi-Action:** Prefix, suffix, extension changing, and sequencing support.
- 🐚 **Shell Friendly:** Handles both quoted patterns and shell-expanded file lists.

---

## 🛠 Usage
```bash
python filerename.py [file_pattern] [old_string] [new_string] [options]
```

### 📋 Arguments
1.  **`file_pattern`**: The pattern to match (e.g., `*.txt`). Supports shell wildcards.
2.  **`old_string`**: The substring or regex to find.
3.  **`new_string`**: The replacement string (use `""` for deletion).

### ⚙️ Options
| Flag | Name | Description |
| :--- | :--- | :--- |
| `-i` | `--ignore-case` | Perform case-insensitive matching/replacement. |
| `-r` | `--regex` | Treat `old_string` as a Regular Expression. |
| `-n` | `--non-recursive` | Look only in the current directory (disable recursion). |
| `-p` | `--prefix` | Prepends a string to the filename. |
| `-s` | `--suffix` | Appends a string before the file extension. |
| `-e` | `--extension` | Changes the file extension (e.g., `jpg`). |
| `-o` | `--order` | Reorders files (e.g., `reverse`). |
| `-h` | `--help` | Display this help documentation. |

---

## 💡 Examples

### 1. Basic Case-Insensitive Rename
Match `.LRF` files and replace `.lrf` (ignoring case) with `_lowres.mp4`.
```bash
python filerename.py *.LRF .lrf _lowres.mp4 -i
```

### 2. Recursive String Deletion
Remove "_draft" from all `.docx` files in all subfolders.
```bash
python filerename.py *.docx "_draft" ""
```

### 3. Regex Replacement
Remove date patterns (e.g., `2024-04-15_`) from filenames.
```bash
python filerename.py * "\d{4}-\d{2}-\d{2}_" "" -r
```

### 4. Changing Extensions
Convert all `.jpeg` files in the current folder to `.jpg`.
```bash
python filerename.py *.jpeg -e jpg -n
```

---

## ⚠️ Troubleshooting
- **No files found?** Ensure you are in the correct directory. If using wildcards on Linux/macOS, try quoting the pattern (e.g., `"*.txt"`).
- **Replacement didn't happen?** Check if you need the `-i` flag for case-insensitivity.
- **Unexpected renames?** Always review the preview list during the interactive prompt.

---
*Last updated: 2026-04-13*
"""

import os
import sys
import glob
import re

def display_help():
    """
    Prints a detailed usage guide to the console.
    
    WHAT: Displays arguments, options, and multiple real-world examples.
    WHY:  Manual print statements are used here instead of standard argparse help 
          to maintain a legacy, high-contrast visual layout that mimics classic 
          CLI tool documentation.
    """
    print("Usage: python FileRename.py [file_pattern] [old_string] [new_string] [options]")
    print("\nRecursively renames files by replacing a string in their names or reordering them.")
    print("The search is RECURSIVE BY DEFAULT.")
    print("\nArguments:")
    print("  file_pattern   The file pattern to match (e.g., *.txt, \"**/*.log\").")
    print("  old_string     The string (or regex pattern) to be replaced. (Optional if using flags)")
    print("  new_string     The string to replace with. (Optional if using flags)")
    print("\nOptions:")
    print("  -i, --ignore-case    Perform case-insensitive matching/replacement")
    print("  -n, --non-recursive  Disables recursion and searches ONLY the current directory.")
    print("  -s, --suffix         Appends a suffix before file extension.")
    print("  -r, --regex          Treats old_string as a Regular Expression.")
    print("  -p, --prefix         Prepends a string to the filenames.")
    print("  -o, --order          Apply a sequence/ordering (e.g., 'reverse' or 'r').")
    print("  -e, --extension      Changes file extension (e.g., 'jpg' or '.jpg').")
    print("  --replay-format      Converts Replay_YYYY-MM-DD_HH-MM-SS.ext to YYYY-MM-DD_HH-MM-SS_Rec-Replay.ext.")
    print("\nExamples:")
    print("  # Reverse the numbering of all .jpg files")
    print("  python FileRename.py *.jpg --order reverse")
    print("\nExamples:")
    print("  # Recursively rename all .txt files in current folder and all subfolders")
    print("  python FileRename.py *.txt draft final")
    print("\n  # Rename .jpg files ONLY in the current folder (shallow search)")
    print("  python FileRename.py *.jpg vacation holiday -n")
    print("\n  # Use Regex to remove a date pattern (e.g., 20240415) from filenames")
    print("  python FileRename.py * \" - \\d{8}\" \"\" -r")
    print("\n  # Add a prefix to all .jpg files")
    print("  python FileRename.py *.jpg --prefix \"Trip_2023_\"")
    print("\n  # Add a suffix before extension (e.g., image.jpg -> image_EDIT.jpg)")
    print("  python FileRename.py *.jpg --suffix \"_EDIT\"")
    print("\n  # Change extension of all .jpeg files to .jpg")
    print("  python FileRename.py *.jpeg --extension jpg")
    print("\n  # Convert Replay_2026-03-09_04-03-59.mp4 -> 2026-03-09_04-03-59_Rec-Replay.mp4")
    print("  python FileRename.py Replay_*.mp4 --replay-format")

def rename_files(files_to_process, old_string=None, new_string=None, use_regex=False, prefix=None, suffix=None, order=None, extension=None, replay_format=False, ignore_case=False):
    """
    Proposes and executes file renames after user confirmation.
    
    WHAT: Orchestrates the renaming logic, from previewing changes to executing 
          the os.rename calls.
    WHY:  Renaming is separated into a dedicated function to keep the CLI parsing 
          (main) clean and allow for future programmatic use of this script.
          
    Args:
        files_to_process (list): List of file paths to evaluate.
        old_string (str): The search pattern (literal or regex).
        new_string (str): The replacement value.
        ignore_case (bool): Whether to ignore case during matching.
        ... (and other flags)
    """
    if not files_to_process:
        print("\nNo files matching the criteria were found.")
        return

    changes = []

    if order in ('reverse', 'r'):
        # Group files by directory
        dirs = {}
        for f in files_to_process:
            d = os.path.dirname(f)
            if d not in dirs:
                dirs[d] = []
            dirs[d].append(f)
        
        for d, dir_files in dirs.items():
            # Sort files in this directory lexicographically
            dir_files.sort()
            basenames = [os.path.basename(f) for f in dir_files]
            reversed_basenames = basenames[::-1]
            
            for i, original_path in enumerate(dir_files):
                new_filename = reversed_basenames[i]
                if new_filename != os.path.basename(original_path):
                    new_path = os.path.join(d, new_filename)
                    changes.append((original_path, new_path))
    else:
        for original_path in files_to_process:
            if not os.path.isfile(original_path):
                continue

            original_filename = os.path.basename(original_path)
            new_filename = original_filename
            
            match_found = False

            if replay_format:
                replay_match = re.match(r'^Replay_(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})(\..+)$', original_filename)
                if replay_match:
                    new_filename = f"{replay_match.group(1)}_Rec-Replay{replay_match.group(2)}"
                    match_found = (new_filename != original_filename)
            elif old_string is not None and new_string is not None:
                if use_regex:
                    try:
                        flags = re.IGNORECASE if ignore_case else 0
                        if re.search(old_string, original_filename, flags=flags):
                            new_filename = re.sub(old_string, new_string, original_filename, flags=flags)
                            match_found = (new_filename != original_filename)
                    except re.error as e:
                        print(f"Error in Regex pattern: {e}")
                        return
                else:
                    if ignore_case:
                        if old_string.lower() in original_filename.lower():
                            # Use regex for case-insensitive literal replacement to be safe
                            new_filename = re.sub(re.escape(old_string), new_string, original_filename, flags=re.IGNORECASE)
                            match_found = True
                    else:
                        if old_string in original_filename:
                            new_filename = original_filename.replace(old_string, new_string)
                            match_found = True

            if prefix:
                new_filename = prefix + new_filename
                match_found = True

            if suffix:
                base, ext = os.path.splitext(new_filename)
                new_filename = base + suffix + ext
                match_found = True
            
            if extension is not None:
                base, _ext = os.path.splitext(new_filename)
                if extension == "":
                    new_ext = ""
                elif extension.startswith("."):
                    new_ext = extension
                else:
                    new_ext = "." + extension
                new_filename = base + new_ext
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
        
        # To avoid collisions during order/sequence changes, we use a two-step rename.
        # WHY: If we try to rename '1.txt' to '2.txt' while '2.txt' still exists, 
        #      the OS will throw an error. By renaming to a .tmp suffix first, 
        #      we clear the names space before final assignment.
        if order:
            temp_changes = []
            for original, new in changes:
                temp_path = original + ".tmp_rename"
                try:
                    os.rename(original, temp_path)
                    temp_changes.append((temp_path, new))
                    print(f'  Pre-renamed: "{original}" -> "{temp_path}"')
                except OSError as e:
                    print(f"  Error pre-renaming {original}: {e}")
            
            for temp_path, new in temp_changes:
                try:
                    os.rename(temp_path, new)
                    print(f'  Final renamed: "{new}"')
                except OSError as e:
                    print(f"  Error final renaming {temp_path} to {new}: {e}")
        else:
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
    """
    Argparse-free CLI entry point.
    
    WHAT: Parses sys.argv, determines modes (regex, recursion, etc.), 
          collects matching files via glob, and triggers rename_files.
    WHY:  This script uses manual list-based parsing for flags because it handles 
          variable-length positional arguments (multiple patterns) in a way 
          that is more flexible than standard argparse for this specific 
          wildcard use case.
    """
    args = sys.argv[1:]
    if not args or "-h" in args or "--help" in args:
        display_help()
        sys.exit(0)
    
    print(f"--- File Rename Script ---")
    print(f"Working Directory: {os.getcwd()}")
    
    # --- LOGIC CHANGE HERE ---
    # Recursion is now ON by default. The '-n' flag turns it OFF.
    recursive = True
    if '-n' in args or '--non-recursive' in args:
        recursive = False
        if '-n' in args: args.remove('-n')
        if '--non-recursive' in args: args.remove('--non-recursive')
    
    # Regex support
    use_regex = False
    if '-r' in args or '--regex' in args:
        use_regex = True
        if '-r' in args: args.remove('-r')
        if '--regex' in args: args.remove('--regex')
    
    # Ignore Case support
    ignore_case = False
    if '-i' in args or '--ignore-case' in args:
        ignore_case = True
        if '-i' in args: args.remove('-i')
        if '--ignore-case' in args: args.remove('--ignore-case')

    # Order support
    order = None
    if '-o' in args or '--order' in args:
        try:
            idx = args.index('-o') if '-o' in args else args.index('--order')
            order = args[idx + 1]
            args.pop(idx + 1)
            args.pop(idx)
        except (IndexError, ValueError):
            print("\nError: --order requires a value (e.g., 'reverse').")
            sys.exit(1)
    
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

    # Suffix support
    suffix = None
    if '-s' in args or '--suffix' in args:
        try:
            idx = args.index('-s') if '-s' in args else args.index('--suffix')
            suffix = args[idx + 1]
            # Remove flag and value
            args.pop(idx + 1)
            args.pop(idx)
        except (IndexError, ValueError):
            print("\nError: --suffix requires a value.")
            sys.exit(1)

    # Extension support
    extension = None
    if '-e' in args or '--extension' in args:
        try:
            idx = args.index('-e') if '-e' in args else args.index('--extension')
            extension = args[idx + 1]
            # Remove flag and value
            args.pop(idx + 1)
            args.pop(idx)
        except (IndexError, ValueError):
            print("\nError: --extension requires a value.")
            sys.exit(1)
    
    # Replay format support
    replay_format = False
    if '--replay-format' in args:
        replay_format = True
        args.remove('--replay-format')
    
    if len(args) < 1 or (not prefix and not suffix and not order and extension is None and not replay_format and len(args) < 3):
        print("\nError: Invalid number of arguments.")
        display_help()
        sys.exit(1)

    new_string = None
    old_string = None
    
    if len(args) >= 3:
        new_string = args.pop()
        old_string = args.pop()
    
    file_inputs = args
    
    # Handle patterns and expanded file lists
    files_to_process = []
    seen_files = set()

    for pattern in file_inputs:
        # If the user enters `*.txt`, the shell might expand it.
        # The '**/' prefix is what enables glob to search subdirectories.
        pathname = os.path.join('**', pattern) if recursive else pattern
        matched = glob.glob(pathname, recursive=recursive)
        for f in matched:
            if os.path.isfile(f) and f not in seen_files:
                files_to_process.append(f)
                seen_files.add(f)
    
    if not files_to_process:
        print(f"\nNo files found matching patterns: {file_inputs}")
        return

    # Print summary of search
    print(f"Searching for files matching pattern(s): {', '.join(file_inputs)}")
    if old_string is not None:
        print(f"Replacing {'regex' if use_regex else 'string'}{' (Case-Insensitive)' if ignore_case else ''}: '{old_string}' -> '{new_string}'")
    if prefix:
        print(f"Adding prefix: '{prefix}'")
    if suffix:
        print(f"Adding suffix: '{suffix}'")
    if order:
        print(f"Applying order: '{order}'")
    if extension is not None:
        display_ext = extension if extension.startswith(".") or extension == "" else "." + extension
        print(f"Changing extension to: '{display_ext}'")
    if replay_format:
        print("Applying Replay format conversion: Replay_<timestamp>.<ext> -> <timestamp>_Rec-Replay.<ext>")
    print(f"Recursive mode: {'On (Default)' if recursive else 'Off (-n flag used)'}")
    print("---------------------------------")
    
    rename_files(files_to_process, old_string, new_string, use_regex=use_regex, prefix=prefix, suffix=suffix, order=order, extension=extension, replay_format=replay_format, ignore_case=ignore_case)

if __name__ == "__main__":
    main()
