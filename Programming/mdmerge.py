import argparse
import os
import shutil


def merge_markdown(files):
    if len(files) < 2:
        print("Error: At least two files are required (target and source).")
        return

    target_file = files[0]
    sources = files[1:]

    if not os.path.isfile(target_file):
        print(f"Error: Target file '{target_file}' not found.")
        return

    # Create a backup folder for the moved pieces
    backup_dir = "merged_source_files"
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)

    try:
        # Open the first file in append mode
        with open(target_file, "a", encoding="utf-8") as main_file:
            for source in sources:
                if not os.path.isfile(source):
                    print(f"Warning: Source file '{source}' not found. Skipping...")
                    continue

                if source == target_file:
                    continue

                # Read and append content
                with open(source, "r", encoding="utf-8") as s_file:
                    content = s_file.read()
                    # Ensure there is a newline between files
                    main_file.write("\n\n" + content.strip() + "\n")

                # Move the source file to the backup folder
                dest_path = os.path.join(backup_dir, os.path.basename(source))

                # Handle potential filename collisions in the backup folder
                if os.path.exists(dest_path):
                    base, ext = os.path.splitext(dest_path)
                    dest_path = f"{base}_old{ext}"

                shutil.move(source, dest_path)
                print(f"Merged and moved: {source}")

        print(f"Success: All content merged into '{target_file}'.")
        print(f"Original source files moved to '{backup_dir}/'.")

    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Merge multiple Markdown files into the first file provided."
    )
    # Accepts one or more files (e.g., target.md 01.md 02.md or *.md)
    parser.add_argument(
        "files",
        nargs="+",
        help="The first file is the target; others are appended to it.",
    )

    args = parser.parse_args()
    merge_markdown(args.files)
