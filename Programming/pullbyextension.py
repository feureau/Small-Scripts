import os
import glob
import shutil
import argparse

def move_files_by_extension(extension):
    """
    Finds all files with the given extension in the current working
    directory and its subdirectories and moves them to the current
    working directory.

    Args:
        extension (str): The file extension to search for (without the dot).
    """
    # Get the current working directory
    working_dir = os.getcwd()
    print(f"Working directory: {working_dir}")

    # Construct the search pattern for the given extension in all subdirectories
    # The '**' pattern with recursive=True will search all directories and subdirectories.
    pattern = os.path.join(working_dir, '**', f'*.{extension}')

    # Use glob to find all files matching the pattern
    found_files = glob.glob(pattern, recursive=True)

    if not found_files:
        print(f"No files with the extension '.{extension}' found.")
        return

    print(f"Found {len(found_files)} file(s) with the extension '.{extension}'.")

    for file_path in found_files:
        # Get the directory where the file is currently located
        file_dir = os.path.dirname(file_path)

        # Skip files that are already in the target working directory
        if file_dir == working_dir:
            # This print statement is optional but helpful for debugging
            # print(f"Skipping '{os.path.basename(file_path)}' as it is already in the working directory.")
            continue

        file_name = os.path.basename(file_path)
        destination_path = os.path.join(working_dir, file_name)

        # Handle potential file name conflicts
        if os.path.exists(destination_path):
            print(f"Skipping '{file_name}' because a file with that name already exists in the destination.")
            continue

        # Move the file to the working directory
        try:
            shutil.move(file_path, destination_path)
            print(f"Moved '{file_name}' to the working directory.")
        except shutil.Error as e:
            print(f"Could not move '{file_name}': {e}")

if __name__ == "__main__":
    # Set up argument parser to accept the extension from the command line
    parser = argparse.ArgumentParser(description="Move files with a specific extension to the current working directory.")
    parser.add_argument("extension", help="The file extension of the files to move (e.g., 'txt', 'pdf').")

    # Parse the command-line arguments
    args = parser.parse_args()

    # Call the main function with the provided extension
    move_files_by_extension(args.extension)