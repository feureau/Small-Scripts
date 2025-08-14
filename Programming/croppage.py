#!/usr/bin/env python

"""
================================================================================
croppage.py - A Document and Page Scanner Script
================================================================================

Purpose:
--------
This script automatically detects the main page or document within an image,
corrects its perspective, crops it from the background, and saves it as a new,
cleaned-up image file. It is designed to handle photos of book pages, receipts,
or any rectangular document taken at an angle.

Functionality:
--------------
- Processes a single specified image file or all supported images in a folder.
- Automatically creates a subfolder for successfully cropped images.
- Automatically copies any images that fail processing into a "Failed" subfolder
  for easy manual review.
- Corrects perspective distortion to provide a flat, "top-down" view.
- Default output is the cropped page in its original color.
- An optional flag allows for conversion to a clean, black-and-white "scanned"
  look using adaptive thresholding.
- Provides a summary of successful and failed files at the end of the process.

New in this version:
--------------------
- Robust page detection: Instead of requiring a perfect 4-corner polygon, the
  script now calculates the minimum bounding rectangle around the largest
  object. This is much better at handling curled corners, minor obstructions
  (like thumbs), and page imperfections. This is the default behavior.
- A configuration option (`USE_STRICT_4_CORNER_DETECTION`) is available to
  revert to the older, stricter method if desired.

"""

# ==============================================================================
# CONFIGURATION VARIABLES
# ==============================================================================
# Change these values to easily customize the script's behavior.

# The name of the subfolder where successfully cropped images will be saved.
OUTPUT_SUBFOLDER = "cropped_images"

# The name of the subfolder where failed original images will be copied.
FAILED_SUBFOLDER = "Failed"

# The text suffix to add to the end of each processed filename (before extension).
FILE_SUFFIX = "_cropped"

# Set to True to use the old method that requires a perfect 4-sided polygon.
# Set to False (default) to use the more robust "minimum area rectangle" method,
# which better handles imperfect page shapes, curled corners, etc.
USE_STRICT_4_CORNER_DETECTION = False

# ==============================================================================

import cv2
import numpy as np
import imutils
import argparse
import glob
import os
import shutil

def detect_and_crop_page(image_path, output_path, apply_threshold):
    """
    Detects a document page in an image and saves the cropped result.
    Returns True on success, False on failure.
    """
    try:
        # --- 1. Load Image and Initial Pre-processing ---
        image = cv2.imread(image_path)
        if image is None:
            print(f"Error: Could not read image at {os.path.basename(image_path)}. It might be corrupted or an unsupported format.")
            return False

        original_image = image.copy()
        orig_h = original_image.shape[0]
        ratio = orig_h / 500.0
        
        image_resized = imutils.resize(original_image, height=500)

        # --- 2. Isolate the Page using Thresholding ---
        gray = cv2.cvtColor(image_resized, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # --- 3. Find the Contour of the Page ---
        contours = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours = imutils.grab_contours(contours)
        
        if len(contours) == 0:
            print(f"Error: No contours found in {os.path.basename(image_path)}. Cannot process.")
            return False

        contours = sorted(contours, key=cv2.contourArea, reverse=True)
        largest_contour = contours[0]

        if USE_STRICT_4_CORNER_DETECTION:
            perimeter = cv2.arcLength(largest_contour, True)
            approx = cv2.approxPolyDP(largest_contour, 0.02 * perimeter, True)
            if len(approx) == 4:
                screen_contour = approx
            else:
                print(f"Error: Strict mode failed. Largest contour in {os.path.basename(image_path)} does not have 4 corners.")
                return False
        else:
            rect = cv2.minAreaRect(largest_contour)
            box = cv2.boxPoints(rect)
            
            # *** MODIFICATION HERE: Use the modern .astype("int") instead of np.int0() ***
            screen_contour = box.astype("int")

        # --- 4. Perspective Transformation ---
        points = screen_contour.reshape(4, 2) * ratio
        rect = np.zeros((4, 2), dtype="float32")

        s = points.sum(axis=1)
        rect[0] = points[np.argmin(s)]
        rect[2] = points[np.argmax(s)]
        diff = np.diff(points, axis=1)
        rect[1] = points[np.argmin(diff)]
        rect[3] = points[np.argmax(diff)]

        (tl, tr, br, bl) = rect

        widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
        widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
        maxWidth = max(int(widthA), int(widthB))

        heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
        heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
        maxHeight = max(int(heightA), int(heightB))

        dst = np.array([
            [0, 0],
            [maxWidth - 1, 0],
            [maxWidth - 1, maxHeight - 1],
            [0, maxHeight - 1]], dtype="float32")

        transform_matrix = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(original_image, transform_matrix, (maxWidth, maxHeight))

        # --- 5. Final Image Processing ---
        if apply_threshold:
            warped_gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
            final_image = cv2.adaptiveThreshold(warped_gray, 255, 
                                                cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                                cv2.THRESH_BINARY, 51, 10)
        else:
            final_image = warped

        cv2.imwrite(output_path, final_image)
        print(f"Successfully processed {os.path.basename(image_path)} -> {output_path}")
        return True

    except Exception as e:
        print(f"An unexpected error occurred while processing {os.path.basename(image_path)}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Detect and crop a page from an image using thresholding.")
    parser.add_argument("filename", nargs='?', default=None, help="Optional: Path to a single image file to process.")
    parser.add_argument("--apply-threshold", action="store_true",
                        help="Optional: Apply a B&W threshold to the final cropped image.")
    args = parser.parse_args()
    
    os.makedirs(OUTPUT_SUBFOLDER, exist_ok=True)
    os.makedirs(FAILED_SUBFOLDER, exist_ok=True)
    
    if args.filename:
        if not os.path.exists(args.filename):
            print(f"Error: The file '{args.filename}' does not exist.")
            return
        files_to_process = [args.filename]
    else:
        supported_types = ("*.jpg", "*.jpeg", "*.png", "*.JPG", "*.JPEG", "*.PNG", "*.tif", "*.tiff")
        files_to_process = []
        for file_type in supported_types:
            files_to_process.extend(glob.glob(file_type))
        
        if not files_to_process:
            print("No supported image files found in the current directory.")
            return

    print(f"Successful output will be saved to the '{OUTPUT_SUBFOLDER}/' subfolder.")
    print(f"Failed files will be copied to the '{FAILED_SUBFOLDER}/' subfolder.")
    
    success_count = 0
    error_count = 0
    error_files = []

    for image_path in files_to_process:
        filename = os.path.basename(image_path)
        name, ext = os.path.splitext(filename)
        
        if args.apply_threshold:
            output_filename = f"{name}{FILE_SUFFIX}.png"
        else:
            output_filename = f"{name}{FILE_SUFFIX}.jpg"

        output_path = os.path.join(OUTPUT_SUBFOLDER, output_filename)
        
        if detect_and_crop_page(image_path, output_path, args.apply_threshold):
            success_count += 1
        else:
            error_count += 1
            error_files.append(filename)
            
            try:
                dest_path = os.path.join(FAILED_SUBFOLDER, filename)
                shutil.copy(image_path, dest_path)
                print(f"--> Copied original file to '{dest_path}' for manual review.")
            except Exception as e:
                print(f"--> Could not copy failed file {filename} to '{FAILED_SUBFOLDER}'. Reason: {e}")

    print("\n" + "="*50)
    print("--- PROCESSING SUMMARY ---")
    print(f"Total files found: {len(files_to_process)}")
    print(f"Successfully processed: {success_count}")
    print(f"Failed to process: {error_count}")
    print("="*50)

    if error_files:
        print("\nThe following files failed to process and were copied to the 'Failed' folder:")
        for fname in error_files:
            print(f"- {fname}")

if __name__ == "__main__":
    main()