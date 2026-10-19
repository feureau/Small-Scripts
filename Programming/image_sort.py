import os
import shutil
import argparse
import platform
from datetime import datetime
from PIL import Image

def get_image_date(file_path):
    """
    Try to extract the 'Date Taken' from the image's EXIF data.
    Falls back to the file's modification time if EXIF data is missing.
    """
    try:
        with Image.open(file_path) as img:
            # getexif() returns a dictionary of EXIF data
            exif = img.getexif()
            if exif is not None:
                # 36867 is DateTimeOriginal, 306 is DateTime
                for tag in [36867, 306]:
                    if tag in exif:
                        date_str = exif[tag]
                        try:
                            # EXIF date format is typically "YYYY:MM:DD HH:MM:SS"
                            return datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S')
                        except ValueError:
                            pass
    except Exception:
        # File might not be an image, or PIL couldn't read it
        pass

    # Fallback to the file's creation time
    if platform.system() == 'Windows':
        ctime = os.path.getctime(file_path)
    else:
        stat = os.stat(file_path)
        try:
            ctime = stat.st_birthtime
        except AttributeError:
            # Linux systems often don't store birth time, fallback to mtime
            ctime = stat.st_mtime

    return datetime.fromtimestamp(ctime)

def main():
    parser = argparse.ArgumentParser(description="Sort images into folders based on their creation/taken date.")
    # By default, it will operate on the current working directory (where you call the script from)
    parser.add_argument("directory", nargs="?", default=".", help="Target directory (default: current working directory)")
    parser.add_argument("-d", "--daily", action="store_true", help="Sort into YYYY-MM-DD folders instead of YYYY-MM")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without actually moving any files")

    args = parser.parse_args()

    # Get the absolute path of the target directory
    target_dir = os.path.abspath(args.directory)

    if not os.path.isdir(target_dir):
        print(f"Error: '{target_dir}' is not a valid directory.")
        return

    # Determine folder name format
    date_format = "%Y-%m-%d" if args.daily else "%Y-%m"

    # Supported image extensions
    image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif", ".webp", ".cr2", ".cr3", ".nef", ".arw", ".dng"}

    moved_count = 0

    for filename in os.listdir(target_dir):
        file_path = os.path.join(target_dir, filename)

        # Skip if it's not a file
        if not os.path.isfile(file_path):
            continue

        # Check if file has an image extension
        ext = os.path.splitext(filename)[1].lower()
        if ext not in image_extensions:
            continue

        # Get the date and determine the folder name
        date_taken = get_image_date(file_path)
        folder_name = date_taken.strftime(date_format)

        dest_folder = os.path.join(target_dir, folder_name)
        dest_path = os.path.join(dest_folder, filename)

        if args.dry_run:
            print(f"[Dry Run] Would move '{filename}' -> '{folder_name}/{filename}'")
        else:
            # Create the destination folder if it doesn't exist
            if not os.path.exists(dest_folder):
                os.makedirs(dest_folder)

            # Move the file if it doesn't already exist in the destination to prevent overwrites
            if not os.path.exists(dest_path):
                shutil.move(file_path, dest_path)
                print(f"Moved '{filename}' -> '{folder_name}/'")
                moved_count += 1
            else:
                print(f"Skipped '{filename}' (File already exists in '{folder_name}/')")

    if not args.dry_run:
        print(f"\nFinished sorting {moved_count} image(s).")

if __name__ == "__main__":
    main()
