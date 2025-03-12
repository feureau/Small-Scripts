#!/usr/bin/env python3
"""
Automatically detect and crop color swatches from images of color cards,
with debug outputs to help diagnose detection issues.

By default, this script:
  - Uses Otsu's thresholding.
  - Does NOT do morphological closing (to avoid merging small shapes).
  - Filters out very large contours (> 300000 area) and very small (< 3000).
  - Discards any contour covering more than 80% of the image area.
  - Accepts aspect ratios from 1.0 to 4.0.

Generates debug images for each input:
  - <filename>_debug_thresh.jpg   (thresholded image)
  - <filename>_debug_contours.jpg (original image with bounding boxes)

Usage example:
  python cropcolorswatch.py *.jpg

To further tweak detection, adjust or override parameters:
  --min_area, --max_area, --invert, --morph_close, --kernel_size,
  --aspect_min, --aspect_max, --full_contour_ratio.
"""

import cv2
import numpy as np
import os
import sys
import glob
import argparse

def process_file(filepath,
                 out_dir="cropped",
                 min_area=3000,
                 max_area=300000,
                 invert=False,
                 kernel_size=5,
                 morph_close=False,
                 aspect_min=1.0,
                 aspect_max=4.0,
                 full_contour_ratio=0.8):
    """
    Process a single image file:
      - Reads the image.
      - Converts to grayscale and blurs it.
      - Thresholds (Otsu's method).
      - Optionally inverts and applies morphological closing.
      - Filters out contours that are too large, too small, or cover most of the image.
      - Saves a debug threshold image.
      - Finds contours, checks aspect ratio, etc.
      - Saves a debug image with bounding boxes.
      - Crops and saves each detected swatch into the out_dir.
    """

    # Read the image
    img = cv2.imread(filepath)
    if img is None:
        print(f"Could not open {filepath}")
        return

    # Compute the full image area for filtering out giant contours
    img_area = img.shape[0] * img.shape[1]

    # Convert to grayscale and blur to reduce noise
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)

    # Threshold using Otsu's method
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # Optionally invert the threshold
    if invert:
        thresh = cv2.bitwise_not(thresh)

    # Optionally apply morphological closing
    if morph_close:
        kernel = np.ones((kernel_size, kernel_size), np.uint8)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

    # Save debug threshold image
    base_path = os.path.splitext(filepath)[0]
    debug_thresh_path = f"{base_path}_debug_thresh.jpg"
    cv2.imwrite(debug_thresh_path, thresh)

    # Find external contours
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    swatch_boxes = []

    for cnt in contours:
        area = cv2.contourArea(cnt)

        # Skip contours covering more than full_contour_ratio of the image
        if area > full_contour_ratio * img_area:
            continue

        # Skip if below min_area or above max_area
        if area < min_area or area > max_area:
            continue

        # Approximate the contour to a polygon
        epsilon = 0.02 * cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, epsilon, True)

        # Consider only quadrilaterals (roughly rectangular)
        if len(approx) == 4:
            x, y, w, h = cv2.boundingRect(approx)
            if h == 0:
                continue

            ratio = w / float(h)
            if ratio < aspect_min or ratio > aspect_max:
                continue

            swatch_boxes.append((x, y, w, h))

    # Sort bounding boxes top-to-bottom, then left-to-right
    swatch_boxes.sort(key=lambda b: (b[1], b[0]))

    # Create debug image with bounding boxes
    debug_img = img.copy()
    for (x, y, w, h) in swatch_boxes:
        cv2.rectangle(debug_img, (x, y), (x + w, y + h), (0, 255, 0), 2)

    debug_contours_path = f"{base_path}_debug_contours.jpg"
    cv2.imwrite(debug_contours_path, debug_img)
    print(f"DEBUG images saved: {debug_thresh_path}, {debug_contours_path}")

    # Create output directory if needed
    os.makedirs(out_dir, exist_ok=True)

    # Crop and save each detected swatch
    base_name = os.path.splitext(os.path.basename(filepath))[0]
    swatch_num = 1
    for (x, y, w, h) in swatch_boxes:
        cropped = img[y:y+h, x:x+w]
        out_filename = f"{base_name}_swatch_{swatch_num}.jpg"
        out_path = os.path.join(out_dir, out_filename)
        cv2.imwrite(out_path, cropped)
        print(f"Saved: {out_path}")
        swatch_num += 1

def main():
    parser = argparse.ArgumentParser(
        description="Automatically detect and crop color swatches from images of color cards, with debug outputs."
    )
    parser.add_argument(
        "files",
        nargs="+",
        help="Input image files (use wildcards like *.jpg or *.png)."
    )
    parser.add_argument(
        "--outdir",
        default="cropped",
        help="Output directory for cropped swatches (default: 'cropped')."
    )
    parser.add_argument(
        "--min_area",
        type=float,
        default=3000,
        help="Minimum contour area to consider as a swatch (default: 3000)."
    )
    parser.add_argument(
        "--max_area",
        type=float,
        default=300000,
        help="Maximum contour area to consider as a swatch (default: 300000)."
    )
    parser.add_argument(
        "--invert",
        action="store_true",
        help="Invert the thresholded image (useful if swatches are lighter than background)."
    )
    parser.add_argument(
        "--morph_close",
        action="store_true",
        default=False,
        help="Apply morphological closing to connect edges (default: False)."
    )
    parser.add_argument(
        "--kernel_size",
        type=int,
        default=5,
        help="Kernel size for morphological operations (default: 5)."
    )
    parser.add_argument(
        "--aspect_min",
        type=float,
        default=1.0,
        help="Minimum aspect ratio (width/height) for a swatch (default: 1.0)."
    )
    parser.add_argument(
        "--aspect_max",
        type=float,
        default=4.0,
        help="Maximum aspect ratio (width/height) for a swatch (default: 4.0)."
    )
    parser.add_argument(
        "--full_contour_ratio",
        type=float,
        default=0.8,
        help="Ignore contours covering more than this fraction of the image area (default: 0.8)."
    )

    args = parser.parse_args()

    # Expand wildcards
    all_files = []
    for pattern in args.files:
        matched = glob.glob(pattern)
        all_files.extend(matched)
    all_files = sorted(set(all_files))

    if not all_files:
        print("No files found matching the given patterns.")
        sys.exit(1)

    for filepath in all_files:
        process_file(
            filepath,
            out_dir=args.outdir,
            min_area=args.min_area,
            max_area=args.max_area,
            invert=args.invert,
            kernel_size=args.kernel_size,
            morph_close=args.morph_close,
            aspect_min=args.aspect_min,
            aspect_max=args.aspect_max,
            full_contour_ratio=args.full_contour_ratio
        )

if __name__ == "__main__":
    main()
