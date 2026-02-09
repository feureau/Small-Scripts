import cv2
import numpy as np
import os
import argparse
import glob

def get_background_color(image):
    """ Samples corners to find a background color to fill gaps during rotation. """
    corners = [image[0, 0], image[0, -1], image[-1, 0], image[-1, -1]]
    return tuple(map(int, np.median(corners, axis=0)))

def deskew_image(image):
    """ Straightens scanned pages. Crucial so the gutter is a straight vertical line. """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.bitwise_not(gray)
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
    coords = np.column_stack(np.where(thresh > 0))
    if len(coords) == 0: return image
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45: angle = -(90 + angle)
    else: angle = -angle
    if abs(angle) > 10 or abs(angle) < 0.1: return image
    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    bg_color = get_background_color(image)
    return cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, 
                         borderMode=cv2.BORDER_CONSTANT, borderValue=bg_color)

def find_smart_gutter(image):
    """
    Finds the spine by looking for the darkest vertical strip.
    Uses center-bias to ignore dark photos near the page edges.
    """
    h, w, _ = image.shape
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Adaptive blur relative to image width
    blur_k = int(w * 0.06) | 1 
    blurred = cv2.GaussianBlur(gray, (blur_k, blur_k), 0)
    
    # Search in the middle 30% of the image
    search_start = int(w * 0.35)
    search_end = int(w * 0.65)
    roi = blurred[:, search_start:search_end]
    
    # Darkness score
    darkness_projection = 255 - np.mean(roi, axis=0)
    
    # Center Bias: Strongly rewards the mathematical center
    x_indices = np.linspace(-1, 1, roi.shape[1])
    center_bias = np.exp(-0.5 * (x_indices / 0.40)**2) 
    
    weighted_score = darkness_projection * center_bias
    return search_start + np.argmax(weighted_score)

def process_files(file_patterns, output_dir, rtl_mode=False, force_split=False, overlap_pct=0.03):
    files_to_process = []
    for pattern in file_patterns:
        files_to_process.extend(glob.glob(pattern))
    files_to_process = sorted(list(set(files_to_process)))

    if not files_to_process:
        print("No files found.")
        return

    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(os.path.abspath(files_to_process[0])), "split_output")
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    page_counter = 1
    for filepath in files_to_process:
        img = cv2.imread(filepath)
        if img is None: continue
        
        filename = os.path.basename(filepath)
        base_name = os.path.splitext(filename)[0]

        try: img = deskew_image(img)
        except: pass

        h, w, _ = img.shape
        
        # Check Aspect Ratio (Landscape = Spread)
        if w < h and not force_split:
            out_name = f"{page_counter:04d}_{base_name}.jpg"
            cv2.imwrite(os.path.join(output_dir, out_name), img)
            print(f"Portrait -> {out_name}")
            page_counter += 1
            continue

        # 1. Find the gutter center
        split_x = find_smart_gutter(img)
        
        # 2. Calculate Adaptive Overlap
        # This creates a 'Shared Zone' centered on split_x
        overlap_px = int(w * overlap_pct)
        
        # 3. Create the pages
        # VERSO (Left): Starts at 0, ends slightly AFTER the gutter
        verso_end = min(w, split_x + overlap_px)
        verso_page = img[:, :verso_end]
        
        # RECTO (Right): Starts slightly BEFORE the gutter, ends at width
        recto_start = max(0, split_x - overlap_px)
        recto_page = img[:, recto_start:]

        # Ordering (Standard vs RTL)
        if rtl_mode:
            pages = [recto_page, verso_page]
            labels = ["Recto", "Verso"]
        else:
            pages = [verso_page, recto_page]
            labels = ["Verso", "Recto"]

        # 4. Save
        for i, p in enumerate(pages):
            out_name = f"{page_counter:04d}_{base_name}_{i+1}.jpg"
            cv2.imwrite(os.path.join(output_dir, out_name), p)
            page_counter += 1
            
        print(f"Split {filename} (Gutter: {split_x}, Overlap: {overlap_px}px included on both sides)")

    print(f"\nDone. Files saved to: {output_dir}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs='+')
    parser.add_argument("--output", "-o", default=None)
    parser.add_argument("--rtl", action="store_true", help="Right-to-Left mode")
    parser.add_argument("--force", action="store_true", help="Force split portrait images")
    parser.add_argument("--overlap", type=float, default=0.03, help="Overlap percent (0.03 = 3%% of width)")
    
    args = parser.parse_args()
    process_files(args.files, args.output, args.rtl, args.force, args.overlap)