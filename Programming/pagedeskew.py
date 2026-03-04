#!/usr/bin/env python3

import cv2
import numpy as np
import pytesseract
import argparse
import shutil
import glob
import signal
import sys
from pathlib import Path


# ============================================================
# GLOBAL CANCEL STATE
# ============================================================
class Cancelled(Exception):
    pass


CANCELLED = False


def handle_sigint(sig, frame):
    global CANCELLED
    CANCELLED = True
    print("\n[interrupt] cancellation requested...")


signal.signal(signal.SIGINT, handle_sigint)


def check_cancel():
    if CANCELLED:
        raise Cancelled()


# ============================================================
# SAFE ROTATION
# ============================================================
def rotate_image(image, angle):

    check_cancel()

    h, w = image.shape[:2]
    center = (w / 2, h / 2)

    M = cv2.getRotationMatrix2D(center, angle, 1.0)

    cos = abs(M[0, 0])
    sin = abs(M[0, 1])

    new_w = int((h * sin) + (w * cos))
    new_h = int((h * cos) + (w * sin))

    M[0, 2] += (new_w / 2) - center[0]
    M[1, 2] += (new_h / 2) - center[1]

    return cv2.warpAffine(
        image,
        M,
        (new_w, new_h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE
    )


# ============================================================
# SAFE TESSERACT CALL
# ============================================================
def safe_tesseract(func, *args, **kwargs):

    check_cancel()

    try:
        return func(*args, **kwargs)
    except pytesseract.TesseractError as e:
        print(f"  [tesseract] warning: {e}")
        return None


# ============================================================
# ORIENTATION
# ============================================================
def detect_orientation(image):

    print("  [osd] detecting orientation")

    osd = safe_tesseract(
        pytesseract.image_to_osd,
        image
    )

    if not osd:
        return 0

    for line in osd.split("\n"):
        if "Rotate:" in line:
            angle = int(line.split(":")[1])
            print(f"  [osd] rotate={angle}")
            return angle

    return 0


# ============================================================
# TEXT SCORE
# ============================================================
def text_score(image):

    data = safe_tesseract(
        pytesseract.image_to_data,
        image,
        output_type=pytesseract.Output.DICT
    )

    if not data:
        return 0

    confs = [
        int(c)
        for c in data["conf"]
        if c != "-1"
    ]

    return np.mean(confs) if confs else 0


def ensure_upright(image):

    print("  [upright] checking inversion")

    s1 = text_score(image)
    flipped = rotate_image(image, 180)
    s2 = text_score(flipped)

    print(f"  scores normal={s1:.2f} flipped={s2:.2f}")

    if s2 > s1:
        print("  flipping 180°")
        return flipped, 180

    return image, 0


# ============================================================
# PROJECTION SCORE
# ============================================================
def projection_score(binary, angle):

    rotated = rotate_image(binary, angle)
    proj = np.sum(rotated, axis=1)
    return np.var(proj)


def search_angle(binary, center, limit, step):

    angles = np.arange(
        center - limit,
        center + limit + step,
        step
    )

    best_angle = center
    best_score = -1
    scores = []

    for a in angles:

        check_cancel()

        score = projection_score(binary, a)
        scores.append((a, score))

        print(f"    angle={a:+.3f} score={score:.2e}")

        if score > best_score:
            best_score = score
            best_angle = a

    return best_angle, best_score, scores


# ============================================================
# MULTI-STAGE DESKEW
# ============================================================
def detect_skew_angle(image):

    print("  [deskew] building text mask")

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (9, 9), 0)

    text_mask = cv2.adaptiveThreshold(
        blur,
        255,
        cv2.ADAPTIVE_THRESH_MEAN_C,
        cv2.THRESH_BINARY_INV,
        35,
        15,
    )

    # Connect nearby characters so scoring follows line structure.
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 3))
    text_mask = cv2.morphologyEx(text_mask, cv2.MORPH_CLOSE, kernel)
    text_mask = cv2.medianBlur(text_mask, 5)

    # Remove outer margins where borders/gutter noise often dominates.
    h, w = text_mask.shape[:2]
    mx = int(w * 0.08)
    my = int(h * 0.08)
    inner = np.zeros_like(text_mask)
    inner[my:h - my, mx:w - mx] = 255
    text_mask = cv2.bitwise_and(text_mask, inner)

    # Reliability checks: skip deskew when there is too little text evidence.
    nonzero = int(cv2.countNonZero(text_mask))
    inner_area = max((h - 2 * my) * (w - 2 * mx), 1)
    text_ratio = nonzero / inner_area

    num_labels, _, stats, _ = cv2.connectedComponentsWithStats(text_mask, connectivity=8)
    # Label 0 is background.
    comp_areas = stats[1:, cv2.CC_STAT_AREA] if num_labels > 1 else np.array([])
    text_like_components = int(np.sum(comp_areas >= 50))

    print(
        f"  [deskew] mask coverage={text_ratio:.4f} "
        f"components={text_like_components}"
    )

    # Hard fail: essentially no usable text evidence.
    if text_ratio < 0.002 or text_like_components < 12:
        print("  [deskew] weak text signal - skipping skew correction")
        return 0.0, True, "weak_text_signal"

    # Soft fail: likely non-text/noisy page; keep output but mark for review.
    review_flag = False
    review_reason = ""
    if text_ratio < 0.03 or text_like_components < 25:
        review_flag = True
        review_reason = "sparse_text_regions"
    elif text_ratio < 0.06 and text_like_components > 400:
        review_flag = True
        review_reason = "fragmented_noise_regions"

    if review_flag:
        print(f"  [deskew] low-confidence page - mark for review ({review_reason})")

    print("  [deskew] searching skew using text regions")
    angle, _, _ = search_angle(text_mask, 0, 5, 0.25)

    # If best angle lands near the boundary, widen the search range.
    if abs(angle) >= 4.75:
        print("  [deskew] boundary hit at ±5°, expanding search to ±10°")
        angle, _, _ = search_angle(text_mask, 0, 10, 0.25)

    print(f"  [deskew] final={angle:.3f}")
    return angle, review_flag, review_reason


# ============================================================
# PROCESS
# ============================================================
def process_image(path, outdir, archivedir, reviewdir):

    print(f"\n[processing] {path.name}")

    image = cv2.imread(str(path))
    if image is None:
        print("  unreadable")
        return

    orientation = detect_orientation(image)
    rotated = rotate_image(image, -orientation)

    rotated, flip = ensure_upright(rotated)

    skew, review_flag, review_reason = detect_skew_angle(rotated)
    outpath = None
    if not review_flag:
        # detect_skew_angle() already returns the best correction rotation.
        corrected = rotate_image(rotated, skew)
        outpath = outdir / path.name
        cv2.imwrite(str(outpath), corrected)

    if review_flag:
        # Create only when needed.
        reviewdir.mkdir(exist_ok=True)
        archive_target = reviewdir
    else:
        archive_target = archivedir
    moved_to = archive_target / path.name
    shutil.move(str(path), str(moved_to))

    print(
        f"  DONE osd={orientation} "
        f"flip={flip} skew={skew:.3f} "
        f"output={outpath if outpath else 'skipped(review)'} "
        f"moved_to={moved_to}"
        f"{' reason=' + review_reason if review_flag else ''}"
    )


# ============================================================
# MAIN
# ============================================================
def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("images", nargs="+")
    args = parser.parse_args()

    cwd = Path.cwd()
    outdir = cwd / "output"
    archivedir = cwd / "input"
    reviewdir = cwd / "needs_review"

    outdir.mkdir(exist_ok=True)
    archivedir.mkdir(exist_ok=True)

    files = []
    for p in args.images:
        files.extend(glob.glob(p))

    print(f"[init] {len(files)} files")

    try:
        for i, f in enumerate(files, 1):

            check_cancel()

            print(f"\n==== ({i}/{len(files)}) ====")

            process_image(
                Path(f),
                outdir,
                archivedir,
                reviewdir
            )

    except Cancelled:
        print("\n[exit] cancelled cleanly.")

    print("[complete]")


if __name__ == "__main__":
    main()
