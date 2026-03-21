"""
# FolderByString.py

## Overview
A Python utility designed to automate file organization by parsing a wildcard
pattern, generating a destination directory based on the pattern's prefix,
and migrating all matching files into that directory.

## Documentation
- **Functionality**: Extracts the string preceding the first asterisk (`*`)
  in the command-line argument to use as a folder name.
- **Directory Management**: Checks for the existence of the target folder;
  creates it if it is missing.
- **File Migration**: Utilizes `glob` for pattern matching and `shutil.move`
  for file relocation.
- **Verbosity**: Provides real-time console feedback for initialization,
  directory resolution, and individual file transfer paths.

## Installation & Usage
1. Place `folderbystring.py` in a directory included in your system's `PATH`.
2. Open a terminal in the directory containing the files to be organized.
3. Execute: `folderbystring.py [pattern]*.*`
   - *Example*: `folderbystring.py cd1*.*` moves files starting with 'cd1'
     into a folder named 'cd1'.

---
**Requirement**: This documentation block must be included and updated with
every subsequent revision of the script to maintain operational transparency.
---
"""

import glob
import os
import shutil
import sys


def main():
    if len(sys.argv) < 2:
        print(
            "[Error] Execution failed. Required parameter missing: <pattern> (e.g., cd1*.*)"
        )
        sys.exit(1)

    pattern = sys.argv[1]
    print(f"[Initialization] Search pattern acquired: '{pattern}'")

    # Isolate the target directory string by extracting the prefix preceding the primary wildcard.
    folder_name = pattern.split("*")[0]

    if not folder_name:
        print(
            "[Error] Malformed pattern. The pattern must initiate with an alphanumeric string prior to the wildcard."
        )
        sys.exit(1)

    print(f"[Resolution] Target directory string identified as: '{folder_name}'")

    # Evaluate the existence of the target directory and instantiate if absent.
    if not os.path.exists(folder_name):
        print(
            f"[Operation] Directory '{folder_name}' not detected. Creating directory..."
        )
        os.makedirs(folder_name)
    else:
        print(f"[Status] Directory '{folder_name}' verified as preexisting.")

    # Compile an array of files corresponding to the provided wildcard pattern.
    print(
        f"[Scanning] Analyzing current working directory for files matching '{pattern}'..."
    )
    files_to_move = glob.glob(pattern)

    total_files = len(files_to_move)
    print(f"[Status] Scan concluded. Total matching entities identified: {total_files}")

    # Execute and document the sequential file transfer protocol.
    transfer_count = 0
    for file_path in files_to_move:
        if os.path.isfile(file_path):
            file_name = os.path.basename(file_path)
            target_path = os.path.join(folder_name, file_name)

            # Prevent moving the script itself if it happens to match the pattern
            if file_name == os.path.basename(__file__):
                print(
                    f"[Skip] Identified script file '{file_name}'; bypassing to prevent recursion."
                )
                continue

            print(f"[Transfer] Moving: '{file_name}' -> '{folder_name}/'")
            shutil.move(file_path, target_path)
            transfer_count += 1

    print(
        f"[Termination] Execution complete. Total files successfully relocated: {transfer_count}"
    )


if __name__ == "__main__":
    main()
