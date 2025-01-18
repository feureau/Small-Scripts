#!/usr/bin/env python3

import os
import sys
import argparse

def is_non_fixed(filename):
    """
    Determine if the .srt file is 'non-fixed'.
    Non-fixed files end with '.en.srt' but do not end with '.en-fixed.srt'.
    """
    return filename.lower().endswith('.en.srt') and not filename.lower().endswith('.en-fixed.srt')

def find_non_fixed_srt_files(directory):
    """
    Find all .srt files in the directory that are not 'fixed'.
    """
    try:
        all_files = os.listdir(directory)
    except Exception as e:
        print(f"Error accessing directory '{directory}': {e}")
        sys.exit(1)

    non_fixed_files = [f for f in all_files if is_non_fixed(f)]
    return non_fixed_files

def delete_files(files, directory, dry_run=False):
    """
    Delete the specified files from the directory.
    If dry_run is True, just print the files that would be deleted.
    """
    if dry_run:
        print("\nDry Run: The following files would be deleted:")
        for f in files:
            print(f" - {f}")
        return

    for f in files:
        file_path = os.path.join(directory, f)
        try:
            os.remove(file_path)
            print(f"Deleted: {f}")
        except Exception as e:
            print(f"Error deleting '{f}': {e}")

def main():
    parser = argparse.ArgumentParser(
        description="Delete non-fixed .srt files in a directory.\n\n"
                    "Fixed files end with '.en-fixed.srt' and will be preserved.\n"
                    "Non-fixed files end with '.en.srt' and will be deleted.",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        'directory',
        nargs='?',
        default='.',
        help='Target directory (default: current directory)'
    )
    parser.add_argument(
        '--force',
        '-f',
        action='store_true',
        help='Force deletion without confirmation'
    )
    parser.add_argument(
        '--dry-run',
        '-d',
        action='store_true',
        help='Show files to be deleted without deleting them'
    )

    args = parser.parse_args()
    target_dir = os.path.abspath(args.directory)

    if not os.path.isdir(target_dir):
        print(f"Error: The directory '{target_dir}' does not exist or is not a directory.")
        sys.exit(1)

    non_fixed_files = find_non_fixed_srt_files(target_dir)

    if not non_fixed_files:
        print("No non-fixed .srt files found to delete.")
        sys.exit(0)

    print(f"\nFound {len(non_fixed_files)} non-fixed .srt file(s) to delete in '{target_dir}':")
    for f in non_fixed_files:
        print(f" - {f}")

    if args.dry_run:
        delete_files(non_fixed_files, target_dir, dry_run=True)
        sys.exit(0)

    if not args.force:
        confirm = input("\nAre you sure you want to delete these files? (y/N): ").strip().lower()
        if confirm != 'y':
            print("Deletion canceled.")
            sys.exit(0)

    delete_files(non_fixed_files, target_dir)

if __name__ == "__main__":
    main()
