#!/usr/bin/env python3
"""
iadownload.py

Utility script to download all original files from an Internet Archive item.

Usage:
  python iadownload.py <identifier> [<destination_folder>]

Arguments:
  identifier           (required) Archive.org item identifier to download.
  destination_folder   (optional) Local folder to save files; defaults to the identifier.

Requirements:
  - Python 3.x
  - internetarchive module (pip install internetarchive)
  - Internet connectivity and valid IA credentials (ia.configure)

Example:
  python iadownload.py eap-1268-babad-diponegoro-v-1-0001
  python iadownload.py eap-1268-babad-diponegoro-v-1-0001 my_downloads

Behaviour:
  - Downloads all files in the item to the specified local directory.
  - Prints progress for each file downloaded.

"""
import sys
from pathlib import Path
import internetarchive as ia


def main():
    if len(sys.argv) < 2:
        print("Usage: python iadownload.py <identifier> [<destination_folder>]")
        sys.exit(1)

    IDENT = sys.argv[1]
    # Determine destination directory
    dest = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(IDENT)
    dest.mkdir(parents=True, exist_ok=True)

    print(f"Downloading all files from '{IDENT}' into '{dest}/'...")
    # Download all files, saving into dest directory
    ia.download(IDENT, destdir=str(dest), verbose=True)

    print("Download complete.")


if __name__ == '__main__':
    main()
