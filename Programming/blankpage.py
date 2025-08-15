# ==============================================================================
#
#                                Blank Page Detector
#
# ==============================================================================
#
# Author: Gemini
# Version: 2.0 (OpenCV-only)
#
# ------------------------------------------------------------------------------
#
# --- PURPOSE ---
#
# This script is designed to automatically find and sort blank or nearly blank
# image files within a specified folder and all its subfolders. When it
# identifies a blank page, it moves that file into a new subfolder named "blank"
# created within the image's original directory.
#
# This is particularly useful for cleaning up large batches of scanned documents
# where some pages may have been scanned blank.
#
#
# --- METHODOLOGY ---
#
# The script uses a fast and efficient image processing technique with the
# OpenCV library, avoiding the need for slower Optical Character Recognition (OCR).
#
# 1.  Load Image: The script loads an image file. It is designed to handle file
#     paths that contain special characters (e.g., accents, non-Latin letters)
#     by reading the file in binary mode first.
#
# 2.  Convert to Grayscale: The image is converted from color to grayscale. This
#     simplifies the analysis by reducing the image to a single channel of pixel
#     intensities (from 0 for black to 255 for white).
#
# 3.  Calculate Standard Deviation: The script calculates the standard deviation
#     of all pixel intensity values in the grayscale image.
#       - A truly blank white page would have almost all pixels at a value of 255.
#         The standard deviation would be very close to 0.
#       - A page with text, lines, or any graphics will have a mix of dark and
#         light pixels, resulting in a much higher standard deviation.
#
# 4.  Compare to Threshold: This calculated standard deviation is compared
#     against a configurable `blank_threshold`. If the value is below the
#     threshold, the page is classified as "Blank".
#
#
# --- DEPENDENCIES & INSTALLATION ---
#
# This script requires Python 3 and the following Python libraries:
#   - opencv-python-headless: For all image processing tasks.
#   - numpy: For numerical operations, used by OpenCV.
#
# To install these libraries, open your terminal or command prompt and run:
#   pip install opencv-python-headless numpy
#
# Note: No Tesseract OCR installation is required for this version of the script.
#
#
# --- HOW TO USE ---
#
# 1.  Save the Code: Save this entire script into a file named `blankpage.py`
#     in a convenient location (e.g., C:\MyScripts\ or ~/Documents/scripts/).
#
# 2.  Open a Terminal:
#     - Windows: Open Command Prompt, PowerShell, or Windows Terminal.
#     - macOS/Linux: Open the Terminal application.
#
# 3.  Navigate to Your Images Folder (Recommended Method):
#     Use the 'cd' command to move into the directory containing the images you
#     want to process.
#     Example:
#       cd "C:\Users\YourName\Documents\Scans To Process"
#
# 4.  Run the Script:
#     Execute the script by calling it with 'python' and providing the full path
#     to where you saved `blankpage.py`. It will automatically process the
#     current folder.
#     Example:
#       python C:\MyScripts\blankpage.py
#
#     Alternatively, you can pass the target folder path as an argument without
#     navigating to it first:
#     Example:
#       python C:\MyScripts\blankpage.py "D:\Photos\Project X"
#
#
# --- CONFIGURATION ---
#
# You can fine-tune the script's sensitivity by changing the `blank_threshold`
# value inside the `is_page_blank_opencv` function.
#
#   blank_threshold = 10.0
#
#   - Increasing this value (e.g., to 15.0) will make the script more aggressive.
#     It will be more likely to classify pages with very faint marks or heavy
#     paper noise as "Blank".
#   - Decreasing this value (e.g., to 5.0) will make the script more conservative.
#     It will only classify extremely clean pages as "Blank".
#
# The script prints the standard deviation ("Std Dev") for every file, which you
# can use as a guide to find the perfect threshold for your specific images.
#
#
# --- OUTPUT ---
#
# As the script runs, it will print the following for each file:
#   - The full path of the image being processed.
#   - The calculated standard deviation ("Std Dev").
#   - The resulting "Status" (Blank or Not Blank).
#   - The "Action" taken (Moved or No action taken).
#
# After completion, any files identified as blank will be in a subfolder named
# "blank" in their original location.
#
# ==============================================================================

import os
import glob
import shutil
import argparse
import cv2
import numpy as np

def is_page_blank_opencv(image_path, blank_threshold=10.0):
    """
    Checks if an image is likely blank using only OpenCV.
    Handles file paths with Unicode characters.

    Args:
        image_path (str): The path to the image file.
        blank_threshold (float): The standard deviation threshold. Anything below this
                                 is considered a blank page.

    Returns:
        bool: True if the page is considered blank, False otherwise.
    """
    try:
        # Read the image as a stream of bytes to handle special characters in the path
        with open(image_path, 'rb') as f:
            chunk = np.frombuffer(f.read(), dtype=np.uint8)
        
        # Decode the byte stream into an image using the IMREAD_COLOR flag
        img_cv = cv2.imdecode(chunk, cv2.IMREAD_COLOR)

        if img_cv is None:
            print(f"    - Warning: Could not decode image file, it might be corrupt. Skipping.")
            return False

        # Convert to grayscale and calculate the standard deviation of pixel intensities
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        std_dev = np.std(gray)
        
        # Print the calculated standard deviation for user feedback and tuning
        print(f"    - Std Dev: {std_dev:.2f}")

        # Return True if the standard deviation is below the threshold, otherwise False
        return std_dev < blank_threshold

    except FileNotFoundError:
        print(f"    - Warning: File not found. It may have been moved or deleted. Skipping: {image_path}")
        return False
    except Exception as e:
        print(f"    - Warning: An error occurred processing {os.path.basename(image_path)}: {e}")
        return False

def process_images(target_dir):
    """
    Finds all images in the target directory and its subdirectories,
    checks if they are blank, and moves them if they are.
    """
    # Define the image file extensions to search for
    image_extensions = ('*.png', '*.jpg', '*.jpeg', '*.tif', '*.tiff', '*.bmp')
    image_files = []

    print(f"Searching for images in: {os.path.abspath(target_dir)}\n")

    # Use glob to find all image files recursively
    for ext in image_extensions:
        search_path = os.path.join(target_dir, '**', ext)
        image_files.extend(glob.glob(search_path, recursive=True))

    if not image_files:
        print("No image files found in the specified directory.")
        return

    print(f"Found {len(image_files)} image(s) to process.\n")
    moved_count = 0

    for image_path in image_files:
        # To prevent reprocessing, skip any files already inside a "blank" folder
        if os.path.basename(os.path.dirname(image_path)).lower() == 'blank':
            continue

        print(f"Processing: {image_path}")
        
        # Call the simplified function to check if the page is blank
        if is_page_blank_opencv(image_path):
            print(f"    - Status: Blank")
            try:
                original_dir = os.path.dirname(image_path)
                blank_folder = os.path.join(original_dir, 'blank')
                
                # Create the "blank" subfolder if it doesn't exist
                os.makedirs(blank_folder, exist_ok=True)
                
                # Move the image file
                shutil.move(image_path, blank_folder)
                print(f"    - Action: Moved to {blank_folder}\n")
                moved_count += 1
            except Exception as e:
                print(f"    - Error: Could not move file. {e}\n")
        else:
            print("    - Status: Not Blank")
            print("    - Action: No action taken.\n")

    # Print a summary report
    print("="*30)
    print("Processing complete.")
    print(f"Total blank pages moved: {moved_count}")
    print("="*30)

def main():
    """
    Parses command-line arguments and initiates the image processing.
    """
    parser = argparse.ArgumentParser(
        description="Scans a directory for image files, detects blank pages using image analysis, and moves them to a 'blank' subfolder."
    )
    parser.add_argument(
        'target_directory',
        nargs='?', # Makes the argument optional
        default=os.getcwd(), # If no argument is given, use the current working directory
        help="The directory to process. Defaults to the current working directory."
    )
    args = parser.parse_args()

    # Verify that the provided directory path is valid
    if not os.path.isdir(args.target_directory):
        print(f"Error: The specified directory does not exist: {args.target_directory}")
        return

    process_images(args.target_directory)

if __name__ == "__main__":
    main()