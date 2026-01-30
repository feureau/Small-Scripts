import cv2
import numpy as np
import os
import argparse
import glob
import sys

def deskew_image(image):
    """ Detects angle and straightens the image. """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.bitwise_not(gray)
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
    coords = np.column_stack(np.where(thresh > 0))
    angle = cv2.minAreaRect(coords)[-1]
    
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
        
    if abs(angle) > 10: # Ignore extreme angles
        return image

    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))

def find_smart_gutter(image):
    """ Finds the visual center of the book. """
    height, width, _ = image.shape
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    
    search_start = int(width * 0.30)
    search_end = int(width * 0.70)
    roi = edges[:, search_start:search_end]
    
    vertical_projection = np.sum(roi, axis=0)
    kernel_size = 5
    smoothed = np.convolve(vertical_projection, np.ones(kernel_size)/kernel_size, mode='same')
    
    return np.argmin(smoothed) + search_start

def process_files(file_patterns, output_dir, rtl_mode=False):
    # 1. Expand Wildcards (Crucial for Windows)
    files_to_process = []
    for pattern in file_patterns:
        # glob.glob handles the "*" expansion
        matches = glob.glob(pattern)
        files_to_process.extend(matches)

    # Sort files to maintain book order (001.jpg, 002.jpg...)
    files_to_process = sorted(list(set(files_to_process)))

    if not files_to_process:
        print("No files found matching your pattern.")
        return

    # 2. Determine Output Directory
    # If user didn't specify output, create a "split" folder in the source directory
    if output_dir is None:
        first_file_dir = os.path.dirname(os.path.abspath(files_to_process[0]))
        output_dir = os.path.join(first_file_dir, "split_output")
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created output folder: {output_dir}")

    page_counter = 1
    print(f"Processing {len(files_to_process)} files...")

    for filepath in files_to_process:
        filename = os.path.basename(filepath)
        print(f"Reading: {filename}...", end=" ", flush=True)
        
        img = cv2.imread(filepath)
        if img is None:
            print("FAILED (Not an image?)")
            continue

        # Deskew
        try:
            img = deskew_image(img)
        except:
            pass

        # Gutter Detect
        h, w, _ = img.shape
        try:
            split_x = find_smart_gutter(img)
        except:
            split_x = w // 2
        
        # Safety Check
        if split_x < w * 0.25 or split_x > w * 0.75:
            split_x = w // 2

        # Cut
        left_page = img[:, :split_x]
        right_page = img[:, split_x:]

        # Order
        if rtl_mode:
            p1, p2 = right_page, left_page
        else:
            p1, p2 = left_page, right_page

        # Save using global counter to keep sequence perfect
        out_name_1 = f"page_{page_counter:04d}.jpg"
        out_name_2 = f"page_{page_counter + 1:04d}.jpg"
        
        cv2.imwrite(os.path.join(output_dir, out_name_1), p1)
        cv2.imwrite(os.path.join(output_dir, out_name_2), p2)

        print(f"Split at {split_x} -> Saved {out_name_1}, {out_name_2}")
        page_counter += 2

    print("Done.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Split scanned book pages.")
    
    # "nargs='+'" means "Take one or more arguments into a list"
    parser.add_argument("files", nargs='+', help="Input files (e.g. *.jpeg)")
    
    # Output is now optional
    parser.add_argument("--output", "-o", default=None, help="Output folder (Optional)")
    parser.add_argument("--rtl", action="store_true", help="Right-to-Left mode")
    
    args = parser.parse_args()
    
    process_files(args.files, args.output, args.rtl)