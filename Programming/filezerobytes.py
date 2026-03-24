import os
import sys

def list_zero_byte_files(target_dir):
    try:
        # Verify the provided path is a valid directory
        if not os.path.isdir(target_dir):
            return f"Error: {target_dir} is not a valid directory."

        # Filter files in the directory that have a size of 0 bytes
        zero_byte_files = [
            f for f in os.listdir(target_dir)
            if os.path.isfile(os.path.join(target_dir, f)) 
            and os.path.getsize(os.path.join(target_dir, f)) == 0
        ]

        # Return the list joined by spaces
        return " ".join(zero_byte_files)

    except Exception as e:
        return f"An error occurred: {e}"

if __name__ == "__main__":
    # If a path is provided as an argument, use it; otherwise, use the current working directory
    path_to_scan = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    print(list_zero_byte_files(path_to_scan))