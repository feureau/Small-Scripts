# ==============================================================================
#
#                                Page Content Sorter
#
# ==============================================================================
#
# Author: Gemini
# Version: 3.4 (Fully Exposed Configuration)
#
# ------------------------------------------------------------------------------
#
# --- PURPOSE ---
#
# This script automatically identifies the content of scanned pages and sorts
# them into three categories:
#
#   1. Pages  : Contain text (main book content).
#   2. Images : Contain illustrations, photos, or diagrams (no body text).
#   3. Blanks : Contain neither (just noise, paper texture, or dust).
#
# Files are moved into a `sorted/` subdirectory with `pages`, `images`, and `blank` folders.
#
# ==============================================================================
# --- CONFIGURATION / PARAMETERS ---
# ==============================================================================

# --- 1. PREPROCESSING ---
# Kernel size for denoising (removing salt-and-pepper noise).
# Larger = more denoising but might lose fine detail.
MORPH_KERNEL_NOISE = (3, 3)

# --- 2. TEXT DETECTION ---
# Kernel to smear letters into words/lines.
# (Width, Height). Increase Width to connect letters further apart.
MORPH_KERNEL_TEXT_CONNECT = (25, 5)

# Filters for valid text "lines".
# A contour must meet ALL these criteria to be counted as a text line.
TEXT_MIN_WIDTH = 30          # Minimum width in pixels
TEXT_MIN_HEIGHT = 8          # Minimum height in pixels
TEXT_MIN_ASPECT_RATIO = 2.5  # Width / Height (Lines must be wide)
TEXT_MIN_AREA = 150          # Minimum blob area

# --- 3. IMAGE DETECTION ---
# Canny Edge Detection thresholds.
CANNY_LOW = 30
CANNY_HIGH = 150

# Minimum area for a contour to count towards "Image Content".
# Ignores small dust specks.
IMAGE_CONTOUR_MIN_AREA = 100

# --- 4. CLASSIFICATION THRESHOLDS ---

# BLANK Check
# Page is BLANK if Text Lines < X  AND  Image Content < Y
TH_BLANK_TEXT_MAX = 3
TH_BLANK_IMAGE_MAX = 5000

# STRONG PAGE Check
# Page is TEXT if Text Lines > X (Overrides image check)
TH_PAGE_TEXT_MIN = 20

# AMBIGUOUS RESOLUTION (Text is between 3 and 20 lines)
# If Image Content > X -> IMAGE. Otherwise -> PAGE.
TH_IMAGE_AREA_HIGH = 120000

# ==============================================================================

import os
import glob
import shutil
import argparse
import cv2
import numpy as np

def classify_page_content(image_path, verbose=True):
    """
    Analyzes an image to determine if it contains Text, Images, or is Blank.
    
    Returns:
        str: 'pages', 'images', or 'blank'
    """
    try:
        # Read image safely (handle unicode paths)
        with open(image_path, 'rb') as f:
            chunk = np.frombuffer(f.read(), dtype=np.uint8)
        img = cv2.imdecode(chunk, cv2.IMREAD_COLOR)

        if img is None:
            if verbose: print(f"    - Warning: Could not decode {os.path.basename(image_path)}")
            return 'error'

        # 1. Preprocessing
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Denoise
        kernel_noise = cv2.getStructuringElement(cv2.MORPH_RECT, MORPH_KERNEL_NOISE)
        denoised = cv2.morphologyEx(gray, cv2.MORPH_OPEN, kernel_noise)
        
        # ----------------------------------------------------------------------
        # DETECT TEXT LINES
        # ----------------------------------------------------------------------
        gradX = cv2.Sobel(denoised, ddepth=cv2.CV_32F, dx=1, dy=0, ksize=-1)
        gradX = np.absolute(gradX)
        (minVal, maxVal) = (np.min(gradX), np.max(gradX))
        
        if maxVal - minVal > 0:
            gradX = (255 * ((gradX - minVal) / (maxVal - minVal))).astype("uint8")
        else:
            gradX = np.zeros_like(gradX, dtype="uint8")

        _, thresh_text = cv2.threshold(gradX, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        
        kernel_text_connect = cv2.getStructuringElement(cv2.MORPH_RECT, MORPH_KERNEL_TEXT_CONNECT)
        connected_text = cv2.morphologyEx(thresh_text, cv2.MORPH_CLOSE, kernel_text_connect)
        
        cnts_text, _ = cv2.findContours(connected_text.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        text_lines_found = 0
        total_text_area = 0
        
        if verbose: print(f"    [Diagnostics] Analyzing: {os.path.basename(image_path)}")

        for c in cnts_text:
            (x, y, w, h) = cv2.boundingRect(c)
            if h > 0:
                aspect_ratio = w / float(h)
            else:
                aspect_ratio = 0
            area = cv2.contourArea(c)
            
            # Text Filter
            if (w > TEXT_MIN_WIDTH and 
                h > TEXT_MIN_HEIGHT and 
                aspect_ratio > TEXT_MIN_ASPECT_RATIO and 
                area > TEXT_MIN_AREA):
                text_lines_found += 1
                total_text_area += area
        
        if verbose: print(f"      -> METRIC: Text Lines Found: {text_lines_found}")

        # ----------------------------------------------------------------------
        # DETECT IMAGE CONTENT
        # ----------------------------------------------------------------------
        edges = cv2.Canny(denoised, CANNY_LOW, CANNY_HIGH)
        
        kernel_edge_connect = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        closed_edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel_edge_connect)
        
        cnts_img, _ = cv2.findContours(closed_edges.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        image_content_area = 0
        largest_contour_area = 0
        
        for c in cnts_img:
            area = cv2.contourArea(c)
            if area > IMAGE_CONTOUR_MIN_AREA: 
                image_content_area += area
                if area > largest_contour_area:
                    largest_contour_area = area

        if verbose: print(f"      -> METRIC: Image Content Area: {image_content_area} (Largest: {largest_contour_area})")

        # ----------------------------------------------------------------------
        # DECISION LOGIC
        # ----------------------------------------------------------------------
        
        # 1. BLANK CHECK
        if text_lines_found < TH_BLANK_TEXT_MAX and image_content_area < TH_BLANK_IMAGE_MAX:
            if verbose: print(f"      -> RESULT: Blank (Text < {TH_BLANK_TEXT_MAX} AND Image < {TH_BLANK_IMAGE_MAX})")
            return 'blank'

        # 2. STRONG TEXT CHECK
        if text_lines_found > TH_PAGE_TEXT_MIN:
             if verbose: print(f"      -> RESULT: Pages (Strong Text: {text_lines_found} > {TH_PAGE_TEXT_MIN})")
             return 'pages'

        # 3. AMBIGUOUS ZONE (Text is between thresholds)
        if image_content_area > TH_IMAGE_AREA_HIGH:
            if verbose: print(f"      -> RESULT: Images (Ambiguous Text, High Image Content: {image_content_area} > {TH_IMAGE_AREA_HIGH})")
            return 'images'
        
        if verbose: print(f"      -> RESULT: Pages (Ambiguous Text, Low Image Content: {image_content_area} <= {TH_IMAGE_AREA_HIGH})")
        return 'pages'

    except Exception as e:
        print(f"    - Error analyzing {os.path.basename(image_path)}: {e}")
        return 'error'

def process_images(target_dir, verbose=True):
    image_extensions = ('*.png', '*.jpg', '*.jpeg', '*.tif', '*.tiff', '*.bmp')
    image_files = []

    abs_target = os.path.abspath(target_dir)
    print(f"Searching in: {abs_target}\n")
    
    if verbose:
        print("--- CURRENT CONFIGURATION ---")
        print(f"  TH_BLANK_TEXT_MAX  = {TH_BLANK_TEXT_MAX}")
        print(f"  TH_BLANK_IMAGE_MAX = {TH_BLANK_IMAGE_MAX}")
        print(f"  TH_PAGE_TEXT_MIN   = {TH_PAGE_TEXT_MIN}")
        print(f"  TH_IMAGE_AREA_HIGH = {TH_IMAGE_AREA_HIGH}")
        print("-" * 30 + "\n")

    for ext in image_extensions:
        image_files.extend(glob.glob(os.path.join(abs_target, '**', ext), recursive=True))

    if not image_files:
        print("No images found.")
        return

    print(f"Found {len(image_files)} images.\n")

    # Stats
    stats = {'pages': 0, 'images': 0, 'blank': 0, 'error': 0, 'skipped': 0}

    # Setup Sorted Folders
    sorted_root = os.path.join(abs_target, 'sorted') 
    dirs = {
        'pages': os.path.join(sorted_root, 'pages'),
        'images': os.path.join(sorted_root, 'images'),
        'blank': os.path.join(sorted_root, 'blanks')
    }

    # Create them if they don't exist
    for d in dirs.values():
        os.makedirs(d, exist_ok=True)

    for image_path in image_files:
        # Skip files already in 'sorted' to avoid double-processing if re-run
        if 'sorted' in image_path.split(os.sep):
            continue

        if verbose:
            print("-" * 40)
        else:
            print(f"Processing: {os.path.basename(image_path)}")
        
        category = classify_page_content(image_path, verbose=verbose)
        
        if category in dirs:
            dest_dir = dirs[category]
            try:
                shutil.move(image_path, dest_dir)
                if not verbose:
                    print(f"    -> Moved to: sorted/{os.path.basename(dest_dir)}")
                else:
                    print(f"      -> Action: Moved to sorted/{os.path.basename(dest_dir)}")
                stats[category] += 1
            except Exception as e:
                print(f"    -> Error moving file: {e}")
                stats['error'] += 1
        else:
            if not verbose: print("    -> Skipped (Error or Unknown)")
            stats['skipped'] += 1
        
        if not verbose: print("")

    print("="*30)
    print("Sorting Complete Check 'sorted/' folder.")
    print(f"  Pages  : {stats['pages']}")
    print(f"  Images : {stats['images']}")
    print(f"  Blanks : {stats['blank']}")
    print("="*30)

def main():
    parser = argparse.ArgumentParser(description="Sorts scanned pages into Pages (Text), Images, and Blanks.")
    parser.add_argument('target_directory', nargs='?', default=os.getcwd(), help="Directory to process")
    parser.add_argument('-q', '--quiet', action='store_true', help="Disable verbose diagnostic output")
    args = parser.parse_args()

    if not os.path.isdir(args.target_directory):
        print("Invalid directory.")
        return

    process_images(args.target_directory, verbose=not args.quiet)

if __name__ == "__main__":
    main()