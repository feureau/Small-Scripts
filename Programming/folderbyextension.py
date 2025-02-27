import os
import shutil

def sort_files_by_extension():
    """
    Sorts files in the current working directory into subfolders based on their file extensions.
    Folders are created if they don't exist.
    Files without extensions are placed in a folder named 'no_extension'.
    """
    current_dir = os.getcwd()  # Get the current working directory
    print(f"Sorting files in directory: {current_dir}")

    for filename in os.listdir(current_dir):
        filepath = os.path.join(current_dir, filename)

        if os.path.isfile(filepath):  # Process only files, not directories
            name, extension = os.path.splitext(filename)
            extension = extension.lstrip('.').lower()  # Remove leading dot and lowercase

            if not extension:
                extension_folder = os.path.join(current_dir, 'no_extension')
            else:
                extension_folder = os.path.join(current_dir, extension)

            if not os.path.exists(extension_folder):
                os.makedirs(extension_folder)  # Create folder if it doesn't exist

            destination_path = os.path.join(extension_folder, filename)

            try:
                shutil.move(filepath, destination_path)
                print(f"Moved '{filename}' to '{extension_folder}'")
            except Exception as e:
                print(f"Error moving '{filename}': {e}")

    print("File sorting complete.")

if __name__ == "__main__":
    sort_files_by_extension()
