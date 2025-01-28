import os
import shutil

def flatten_directory_tree(root_dir):
    """
    Moves all files from subdirectories into the root directory.
    Deletes empty subdirectories after moving files.
    """
    for dirpath, _, filenames in os.walk(root_dir, topdown=False):
        for filename in filenames:
            src_path = os.path.join(dirpath, filename)
            dest_path = os.path.join(root_dir, filename)

            # Ensure we don't overwrite files with the same name
            if os.path.exists(dest_path):
                base, ext = os.path.splitext(filename)
                counter = 1
                while os.path.exists(dest_path):
                    dest_path = os.path.join(root_dir, f"{base}_{counter}{ext}")
                    counter += 1

            shutil.move(src_path, dest_path)

        # Remove empty directories after moving files
        if dirpath != root_dir:
            try:
                os.rmdir(dirpath)
            except OSError:
                pass  # Ignore errors if the directory isn't empty

if __name__ == "__main__":
    current_dir = os.getcwd()  # The directory where the script is called
    flatten_directory_tree(current_dir)
