import os
from argparse import ArgumentParser

def main():
    # Parse command-line arguments
    parser = ArgumentParser(description='Organizes media files into subdirectories with customizable limits.')
    parser.add_argument('-l', '--limit', type=int, default=15,
                        help='Number of files per directory (default: 15)')
    args = parser.parse_args()
    limit = args.limit

    # Ensure we are in the correct directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(current_dir)
    
    print(f"Starting with directory: {current_dir}")
    
    dir_number = -1
    while True:
        dir_number += 1
        dir_path = f"{dir_number}"
        if not os.path.exists(dir_path):
            break
    
    file_count = 0
    for filename in os.listdir('.'):
        # Check if the file is a media file
        file_extension = os.path.splitext(filename)[1].lower()
        if file_extension in ['.mov', '.mp4', '.mkv']:
            if file_count >= limit:
                dir_number += 1
                while True:
                    new_dir_path = f"{dir_number}"
                    if not os.path.exists(new_dir_path):
                        os.mkdir(new_dir_path)
                        break
                    else:
                        dir_number += 1
                
                # Move the file to the new directory
                try:
                    os.rename(filename, os.path.join(new_dir_path, filename))
                    print(f"Moved '{filename}' to '{new_dir_path}'")
                except Exception as e:
                    print(f"Error moving '{filename}': {str(e)}")
                
                file_count = 1  # Reset count after creating new directory
            else:
                try:
                    os.rename(filename, os.path.join(str(dir_number), filename))
                    print(f"Moved '{filename}' to '{dir_number}'")
                except Exception as e:
                    print(f"Error moving '{filename}': {str(e)}")
                
                file_count += 1

if __name__ == "__main__":
    main()