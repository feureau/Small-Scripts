#!/usr/bin/env python3
import cv2
import pytesseract
from pytesseract import Output
import pandas as pd
import argparse
import os
import glob
import easyocr

# ==========================================
# CONFIGURATION
# ==========================================
print("Initializing EasyOCR (GPU)...")
reader = easyocr.Reader(['en'], gpu=True) 

def calculate_pixel_density(img_crop):
    """ Returns the percentage of 'ink' (dark pixels) in the image. """
    gray = cv2.cvtColor(img_crop, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    total_pixels = img_crop.shape[0] * img_crop.shape[1]
    ink_pixels = cv2.countNonZero(thresh)
    return ink_pixels / total_pixels

def get_ocr_text(img_crop):
    """ Uses EasyOCR to extract text. """
    try:
        results = reader.readtext(img_crop, detail=0, paragraph=True)
        full_text = " ".join(results).strip()
        if len(full_text) < 10: return False, ""
        return True, full_text
    except Exception as e:
        print(f"   [Error] OCR Failed: {e}")
        return False, ""

def process_single_image(image_path, output_dir):
    if not os.path.exists(image_path): return

    file_prefix = os.path.splitext(os.path.basename(image_path))[0]
    print(f"Scanning: {os.path.basename(image_path)}...")

    img = cv2.imread(image_path)
    if img is None: return
    
    h_img, w_img, _ = img.shape
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    # 1. Tesseract Layout Analysis
    custom_config = r'--oem 3 --psm 3'
    data = pytesseract.image_to_data(rgb, output_type=Output.DICT, config=custom_config)
    df = pd.DataFrame(data)
    
    # Filter valid blocks
    df = df[(df['width'] > 0) & (df['height'] > 0)]
    groups = df.groupby(['block_num', 'par_num'])

    candidates = []

    # 2. Extract Candidates
    for (block, par), group in groups:
        x_min = group['left'].min()
        y_min = group['top'].min()
        x_max = (group['left'] + group['width']).max()
        y_max = (group['top'] + group['height']).max()
        
        w_box = x_max - x_min
        h_box = y_max - y_min
        
        # --- NEW FILTER: Ignore "Full Page" Blocks ---
        # If the detected block is > 85% of the image width AND height, 
        # it is the page container, not a paragraph. Skip it.
        if w_box > (w_img * 0.85) and h_box > (h_img * 0.85):
            continue

        # Filter: Ignore tiny specks
        if (w_box * h_box) < 1000: continue
        
        # Create Crop with padding
        pad = 10
        x1 = max(0, x_min - pad)
        y1 = max(0, y_min - pad)
        x2 = min(w_img, x_max + pad)
        y2 = min(h_img, y_max + pad)
        
        crop = img[y1:y2, x1:x2]
        
        candidates.append({
            'x': x_min,
            'y': y_min,
            'crop': crop
        })

    if not candidates:
        print("   -> No layout blocks found.")
        return

    # 3. Dynamic Sorting (Left Page vs Right Page)
    # Average X position determines the split line
    all_x = [c['x'] for c in candidates]
    avg_x = sum(all_x) / len(all_x)
    
    left_page = [c for c in candidates if c['x'] < avg_x]
    right_page = [c for c in candidates if c['x'] >= avg_x]

    # Sort each page Top -> Down
    left_page.sort(key=lambda k: k['y'])
    right_page.sort(key=lambda k: k['y'])
    
    sorted_candidates = left_page + right_page

    # 4. Validation and Saving
    saved_count = 0
    
    for i, item in enumerate(sorted_candidates):
        crop = item['crop']
        
        # Filter A: Pixel Density (Visual Check)
        density = calculate_pixel_density(crop)
        if density < 0.02 or density > 0.60:
            continue

        # Filter B: EasyOCR (Content Check)
        is_text, extracted_text = get_ocr_text(crop)
        if not is_text:
            continue
        
        saved_count += 1
        base_filename = f"{file_prefix}_{saved_count:03d}"
        
        # Save Image
        img_out_path = os.path.join(output_dir, base_filename + ".png")
        cv2.imwrite(img_out_path, crop)
        
        # Save Text
        txt_out_path = os.path.join(output_dir, base_filename + ".txt")
        with open(txt_out_path, "w", encoding="utf-8") as f:
            f.write(extracted_text)

        print(f"   [Saved] {base_filename} | Text: {extracted_text[:30]}...")

    print(f"   -> Extracted {saved_count} paragraphs.")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs='+', help="Input images (e.g. *.jpg)")
    parser.add_argument("--out", default="combined_output", help="Output folder name")
    args = parser.parse_args()

    output_dir = os.path.abspath(args.out)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    print(f"Output Directory: {output_dir}")

    files_to_process = []
    for f in args.files:
        if '*' in f or '?' in f:
            files_to_process.extend(glob.glob(f))
        else:
            files_to_process.append(f)
    
    files_to_process = sorted(list(set(files_to_process)))

    if not files_to_process:
        print("No files found.")
        return

    for file_path in files_to_process:
        process_single_image(os.path.abspath(file_path), output_dir)

if __name__ == "__main__":
    main()