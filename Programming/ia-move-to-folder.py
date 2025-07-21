#!/usr/bin/env python3
"""
ia-move-runner.py

== DESCRIPTION ==
A Python script to orchestrate a batch file move operation within a single
Internet Archive item. It is designed to move all files currently in the
root of an item into a specified subdirectory within that same item.

This script acts as a hybrid tool, leveraging the strengths of both the
`internetarchive` Python library and the `ia` command-line interface (CLI):
1.  **Discovery:** It uses the Python library to efficiently connect to the
    item and retrieve a list of all files that are in the root directory.
2.  **Execution:** It then iterates through this list and, for each file,
    it constructs and executes the `ia move` command using a Python
    subprocess. This provides a robust, reliable move operation with clear
    progress feedback, exactly as if you were running the commands manually.

== USAGE ==
The script is run from the command line and requires two arguments: the
item's identifier and the name of the destination folder.

Syntax:
  python ia-move-runner.py [options] <identifier> <destination_folder>

== ARGUMENTS ==
  <identifier>
    The unique identifier of the Internet Archive item you wish to modify.
    Example: eap-1268-babad-diponegoro-v-1-0001

  <destination_folder>
    The name of the folder within the item where the root files will be
    moved. If the folder does not exist, the `ia move` command will create
    it automatically.
    
    IMPORTANT: If the folder name contains spaces, you MUST enclose the
    entire name in double quotes ("").

== OPTIONS ==
  -l, --limit <seconds>
    Specify a delay (in seconds) between each `ia move` command to
    avoid rate-limiting errors from the server. The value can be a
    decimal (e.g., 1.5). Defaults to 2 seconds.

  -nl, --nolimit
    Disables the rate limit delay entirely. This will run commands as fast
    as possible and is VERY LIKELY to cause errors on items with many
    files. The presence of this flag overrides any value set by -l/--limit.

== EXAMPLES ==
  
  # Example 1: Move all root files into 'scans' with default 2-sec delay
  python ia-move-runner.py my-cool-item-01 scans
  
  # Example 2: Move files into a folder with spaces, using a 5-second delay
  python ia-move-runner.py -l 5 my-book-project "Chapter 1 Scans"

  # Example 3: Move files with no delay (fast, but risky)
  python ia-move-runner.py --nolimit my-item-with-few-files "quick-sort"

== REQUIREMENTS ==
  - Python 3.x
  
  - The `internetarchive` library must be installed.
    (Install with: pip install internetarchive)
    
  - The `ia` command-line tool must be installed AND configured. This means
    you must have run `ia configure` at least once and authenticated with
    your Internet Archive account.
    
  - The `ia` command must be in your system's PATH, so that the script can
    execute it from the command line.

== IMPORTANT NOTES ==
  - **Performance:** This script executes a separate `ia move` command for
    every single file. For items with hundreds or thousands of files, this
    will be a VERY SLOW process by design. It is built for reliability over
    speed. Please be patient and let it run to completion.
    
  - **Scope:** The script is specifically designed to move files from the
    ROOT of the item. It will automatically and deliberately skip any files
    that already appear to be in a folder (i.e., any filename containing a
    forward slash '/').
    
  - **Not Atomic:** The operation is not atomic. If the script is cancelled,
    some files will have been moved and others will not. It is safe to
    re-run the script on the same item; it will find the remaining files
    in the root and continue the process.
"""
import sys
import subprocess
import time
import internetarchive as ia

def main():
    # --- 1. Argument Parsing ---
    args = sys.argv[1:]
    
    # Defaults
    delay_seconds = 1.0
    no_limit_flag = False
    
    positional_args = []
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ("-l", "--limit"):
            i += 1 # Move to the value
            if i < len(args):
                try:
                    delay_seconds = float(args[i])
                except ValueError:
                    print(f"FATAL ERROR: Invalid numeric value for limit: '{args[i]}'")
                    print(__doc__)
                    sys.exit(1)
            else:
                print(f"FATAL ERROR: The '{arg}' flag requires a numeric value after it.")
                print(__doc__)
                sys.exit(1)
        elif arg in ("-nl", "--nolimit"):
            no_limit_flag = True
        else:
            positional_args.append(arg)
        i += 1

    # --nolimit flag overrides any custom limit
    if no_limit_flag:
        delay_seconds = 0.0

    if len(positional_args) != 2:
        print("FATAL ERROR: Incorrect number of arguments.")
        print("\nUsage: python ia-move-runner.py [options] <identifier> <destination_folder>")
        print(__doc__)
        sys.exit(1)

    IDENTIFIER = positional_args[0]
    DEST_FOLDER = positional_args[1]

    # --- 2. Discovery Phase (using Python library) ---
    if delay_seconds > 0:
        print(f"Rate limiting is ON. Pausing {delay_seconds} seconds between each request.")
    else:
        print("Rate limiting is OFF. Running at maximum speed (higher risk of errors).")
    
    print(f"\nConnecting to item '{IDENTIFIER}' to get file list...")
    try:
        item = ia.get_item(IDENTIFIER)
        if not item.metadata:
            raise ia.exceptions.NotFound(f"Item '{IDENTIFIER}' not found.")
        
        # Filter for files in the root directory only
        root_files = [f['name'] for f in item.files if '/' not in f['name']]
        
    except FileNotFoundError:
        print(f"FATAL ERROR: The 'ia' command-line tool is not installed or not in your system's PATH.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: Could not retrieve item file list. Reason: {e}")
        sys.exit(1)

    if not root_files:
        print("No files found in the root of the item to move.")
        sys.exit(0)

    total_files = len(root_files)
    print(f"Found {total_files} file(s) to move into folder: '{DEST_FOLDER}'")
    print("Starting command-line execution now...")
    print("-" * 20)

    # --- 3. Execution Phase (calling ia command line) ---
    success_count = 0
    failure_count = 0
    for index, filename in enumerate(root_files):
        
        # Add the rate-limiting delay before executing the command.
        # We don't need to sleep on the very first item.
        if index > 0 and delay_seconds > 0:
            time.sleep(delay_seconds)

        source_path = f"{IDENTIFIER}/{filename}"
        dest_path = f"{IDENTIFIER}/{DEST_FOLDER}/{filename}"
        
        # The command is built as a list of arguments for robustness,
        # which correctly handles spaces in filenames or folders.
        command_to_run = ["ia", "move", source_path, dest_path]
        
        print(f"[{index + 1}/{total_files}] Executing: ia move \"{source_path}\" \"{dest_path}\"")
        
        try:
            # subprocess.run() executes the command.
            # check=True will raise an error if the command fails (returns a non-zero exit code).
            # capture_output=True and text=True capture the command's stdout and stderr.
            result = subprocess.run(
                command_to_run,
                capture_output=True,
                text=True,
                check=True
            )
            
            # Print the success message from the 'ia move' command
            print(f"  > SUCCESS: {result.stdout.strip()}")
            success_count += 1
            
        except subprocess.CalledProcessError as e:
            # This error is triggered by check=True if 'ia move' fails.
            # We print the error message that 'ia' itself provided.
            print(f"  > ERROR: The 'ia move' command failed.")
            print(f"    Details: {e.stderr.strip()}")
            failure_count += 1
        except FileNotFoundError:
            # This error happens if the 'ia' command itself cannot be found.
            print("FATAL ERROR: The 'ia' command could not be found.")
            print("Please ensure the internetarchive library is installed and 'ia' is in your system's PATH.")
            sys.exit(1)
        except Exception as e:
            # Catch any other unexpected errors during the process.
            print(f"  > An unexpected Python error occurred: {e}")
            failure_count += 1

    print("-" * 20)
    print("Operation Complete.")
    print(f"Successfully moved: {success_count} file(s)")
    print(f"Failed to move:     {failure_count} file(s)")
    print("-" * 20)

if __name__ == '__main__':
    main()