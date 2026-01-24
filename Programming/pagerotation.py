"""
================================================================================
SCRIPT: rotatetext.py (v7 - Path Fix & Graceful Exit)
================================================================================

DESCRIPTION: 
    Auto-rotates book scans using Tesseract OCR.
    
    UPDATES v7:
    1. PATH DETECTION: Now correctly finds 'jpegtran' if it is in your Windows 
       System PATH (Environment Variables).
    2. GRACEFUL EXIT: Uses a signal handler to catch Ctrl+C immediately, 
       preventing messy 'PermissionError' tracebacks from Tesseract temp files.

USAGE:
    python rotatetext.py "folder_path"

================================================================================
"""

import pytesseract
import cv2
import os
import argparse
import sys
import imutils
import glob
import subprocess
import shutil
import signal
from pytesseract import Output

# ================= CONFIGURATION =================
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
# =================================================

# Confidence Settings
MIN_CONF_THRESH = 2.0    
HIGH_CONF_THRESH = 15.0  

# --- SIGNAL HANDLER FOR CTRL+C ---
def signal_handler(sig, frame):
    print("\n\n[STOP] Process aborted by user. Exiting immediately...")
    sys.exit(0)

# Register the signal (This prevents the ugly PermissionError traceback)
signal.signal(signal.SIGINT, signal_handler)

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def log(tag, filename, message, conf=None):
    """Uniform logger helper"""
    conf_str = f"(Conf: {conf:.2f})" if conf is not None else "(Conf: N/A)"
    print(f"[{tag}] {filename:<30} | {message} {conf_str}")

def lossless_rotate(src, dst, angle, jpegtran_path):
    """
    Calls jpegtran.exe to perform lossless rotation.
    Returns True if successful, False if failed.
    """
    if angle == 0:
        if src != dst:
            shutil.copy2(src, dst)
        return True

    cmd_angle = {90: "90", 180: "180", 270: "270"}.get(angle)
    if not cmd_angle:
        return False 

    try:
        # Build command: jpegtran -rotate 90 -copy all -outfile "out" "in"
        subprocess.check_call([
            jpegtran_path, 
            '-rotate', cmd_angle, 
            '-copy', 'all', 
            '-outfile', dst, 
            src
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return False

def get_osd(image):
    """Returns Tesseract dictionary or None"""
    try:
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        return pytesseract.image_to_osd(rgb, output_type=Output.DICT)
    except pytesseract.TesseractError:
        return None
    except Exception:
        # Catch unexpected errors to prevent crash, return None
        return None

def process_image(src_path, dirs, args, jpegtran_exe):
    filename = os.path.basename(src_path)
    processed_path = os.path.join(dirs['processed'], filename)
    
    # 1. Read Image
    image = cv2.imread(src_path)
    if image is None:
        log("ERR", filename, "Could not read file")
        return

    # 2. Initial Detect
    res = get_osd(image)
    if res is None:
        log("SKIP", filename, "OSD failed (No text?) -> Moving to 'no_text'")
        if not args.overwrite:
            cv2.imwrite(os.path.join(dirs['no_text'], filename), image)
            shutil.move(src_path, processed_path)
        return

    angle = res["rotate"]
    conf = res["orientation_conf"]
    if conf is None: conf = 0.0

    # 3. Decision Logic
    final_angle = 0
    action = "save" # save, low_conf
    
    # --- CASE A: No Rotation Needed ---
    if angle == 0:
        log("OK", filename, "No rotation needed", conf)
        final_angle = 0

    # --- CASE B: High Confidence Rotation ---
    elif conf >= HIGH_CONF_THRESH:
        log("FIX", filename, f"Rotating {angle}°", conf)
        final_angle = angle

    # --- CASE C: Mediocre/Low Confidence (Verify) ---
    else:
        log("VERIFY", filename, f"detected {angle}° but low conf. Checking...", conf)
        
        # Test the rotation in memory
        test_img = imutils.rotate_bound(image, angle)
        res_verify = get_osd(test_img)
        
        if res_verify:
            v_angle = res_verify["rotate"]
            v_conf = res_verify["orientation_conf"] or 0.0
            
            if v_angle == 0 and v_conf > args.conf:
                log("FIX", filename, f"Verified! Rotation confirmed.", v_conf)
                final_angle = angle
            
            elif v_angle == 0:
                 log("WARN", filename, f"Verified orientation but conf still low ({v_conf} < {args.conf})", v_conf)
                 action = "low_conf"

            elif v_angle == 180:
                log("FIX", filename, f"Initial guess was Upside Down. Flipping 180° more.", v_conf)
                final_angle = (angle + 180) % 360
            else:
                log("WARN", filename, f"Verification failed (Result still asks for {v_angle}°)", v_conf)
                action = "low_conf"
        else:
            log("WARN", filename, "Verification OSD crashed.", 0)
            action = "low_conf"

    # 4. Perform Action
    dest_path = src_path if args.overwrite else os.path.join(dirs['out'], filename)
    
    if action == "low_conf":
        dest_path = os.path.join(dirs['low_conf'], filename)
        if not args.overwrite:
            cv2.imwrite(dest_path, image)
            shutil.move(src_path, processed_path)
        return

    # 5. Execute Rotation
    if final_angle == 0:
        if not args.overwrite and src_path != dest_path:
            shutil.copy2(src_path, dest_path)
            shutil.move(src_path, processed_path)
    else:
        # Try Lossless first
        success = False
        # Only try jpegtran if it exists AND the file is a jpg
        if jpegtran_exe and filename.lower().endswith(('.jpg', '.jpeg')):
            success = lossless_rotate(src_path, dest_path, final_angle, jpegtran_exe)
            if success:
                # log("INFO", filename, "Saved using Lossless jpegtran")
                pass

        # Fallback to OpenCV
        if not success:
            if jpegtran_exe and filename.lower().endswith(('.jpg', '.jpeg')):
                log("WARN", filename, "Lossless failed. Falling back to OpenCV re-encode.")
            
            rotated = imutils.rotate_bound(image, final_angle)
            cv2.imwrite(dest_path, rotated)
    
    # Move original to processed folder
    if not args.overwrite and os.path.exists(src_path):
        shutil.move(src_path, processed_path)

def find_jpegtran():
    """Finds jpegtran in PATH or local directory"""
    # 1. Check System PATH
    path_exe = shutil.which("jpegtran")
    if path_exe: 
        return path_exe
    
    # 2. Check Local Directory
    local_exe = os.path.join(os.getcwd(), "jpegtran.exe")
    if os.path.exists(local_exe):
        return local_exe
        
    return None

def main():
    print("--- Smart Rotate Script v7 (Lossless & Clean Logs) ---")
    
    # Locate jpegtran
    jpegtran_exe = find_jpegtran()
    
    if jpegtran_exe:
        print(f"[INIT] jpegtran found at: {jpegtran_exe}")
        print(f"[INIT] Lossless rotation enabled for JPEGs.")
    else:
        print(f"[INIT] jpegtran NOT found in PATH or local folder.")
        print(f"[INIT] Using standard OpenCV rotation (Re-encoding).")

    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("-o", "--output")
    parser.add_argument("--conf", type=float, default=MIN_CONF_THRESH)
    args = parser.parse_args()
    
    # 1. Gather Files
    raw_input = args.input.strip('"').strip("'")
    if "*" in raw_input or "?" in raw_input:
        if not os.path.isabs(raw_input): raw_input = os.path.join(os.getcwd(), raw_input)
        files = glob.glob(raw_input)
    elif os.path.isfile(raw_input):
        files = [os.path.abspath(raw_input)]
    elif os.path.isdir(raw_input):
        valid = ('.jpg', '.jpeg', '.png', '.tif', '.bmp')
        files = [os.path.join(raw_input, f) for f in os.listdir(raw_input) if f.lower().endswith(valid)]
    else:
        print("[ERROR] No files found.")
        return

    if not files:
        print("[ERROR] No files match.")
        return

    # 2. Setup Folders
    base_dir = os.path.dirname(files[0])
    out_root = args.output if args.output else os.path.join(base_dir, "rotated_out")
    
    dirs = {
        'out': out_root,
        'no_text': os.path.join(out_root, "no_text"),
        'low_conf': os.path.join(out_root, "confidence_low"),
        'processed': os.path.join(base_dir, "processed")
    }

    if not args.overwrite:
        ensure_dir(dirs['out'])
        ensure_dir(dirs['no_text'])
        ensure_dir(dirs['low_conf'])
        ensure_dir(dirs['processed'])
        print(f"Output: {dirs['out']}")
        print(f"Processed originals: {dirs['processed']}")

    # 3. Run
    # (Note: KeyboardInterrupt is now handled by the signal_handler above)
    for i, fpath in enumerate(files):
        process_image(fpath, dirs, args, jpegtran_exe)

if __name__ == "__main__":
    main()