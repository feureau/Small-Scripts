import os

def purge_empty_files():
    """
    Traverses the current working directory and subdirectories
    to delete files with a size of 0 bytes.
    """
    # Define the root of the search as the current working directory
    root_dir = os.getcwd()
    
    files_deleted = 0

    for root, dirs, files in os.walk(root_dir):
        for name in files:
            file_path = os.path.join(root, name)
            
            try:
                # Check if file size is 0 bytes
                if os.path.getsize(file_path) == 0:
                    os.remove(file_path)
                    print(f"Deleted: {file_path}")
                    files_deleted += 1
            except OSError as e:
                print(f"Error accessing {file_path}: {e}")

    print(f"\nTask complete. Total empty files removed: {files_deleted}")

if __name__ == "__main__":
    purge_empty_files()