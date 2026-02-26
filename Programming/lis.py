import sys
import cv2
import torch
import numpy as np
import math
from PIL import Image

from groundingdino.util.inference import load_model, load_image, predict
from segment_anything import sam_model_registry, SamPredictor


# -----------------------------
# Smooth deterministic jitter
# -----------------------------
def smooth_jitter(x, y, t, amp=2.5):
    dx = math.sin(x * 0.012 + t * 0.9) * amp
    dy = math.cos(y * 0.015 + t * 1.1) * amp
    return dx, dy


# -----------------------------
# Bloom
# -----------------------------
def apply_bloom(frame):
    blur = cv2.GaussianBlur(frame, (0, 0), 8)
    return cv2.addWeighted(frame, 1.0, blur, 0.35, 0)


# -----------------------------
# Film grain
# -----------------------------
def apply_paper_grain(frame):
    noise = np.random.normal(0, 6, frame.shape).astype(np.uint8)
    return cv2.add(frame, noise)


# -----------------------------
# Render outlines
# -----------------------------
def render_scene_with_contours(base_img, contours):
    img = base_img.copy()
    cv2.drawContours(img, contours, -1, (255, 255, 255), 2)
    return img


# -----------------------------
# Animate outlines
# -----------------------------
def animate_outline(base_image, contours, frames=48):
    h, w = base_image.shape[:2]
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter("lis_output.mp4", fourcc, 24, (w, h))

    for frame_idx in range(frames):
        t = frame_idx * 0.05
        img = base_image.copy()

        animated_contours = []

        for contour in contours:
            animated = []
            for pt in contour:
                dx, dy = smooth_jitter(pt[0][0], pt[0][1], t)
                animated.append([[int(pt[0][0] + dx), int(pt[0][1] + dy)]])
            animated_contours.append(np.array(animated, dtype=np.int32))

        frame = render_scene_with_contours(img, animated_contours)
        frame = apply_bloom(frame)
        frame = apply_paper_grain(frame)

        out.write(frame)

    out.release()


# -----------------------------
# Main
# -----------------------------
def main(image_path, prompt):

    device = "cuda" if torch.cuda.is_available() else "cpu"

    # Load GroundingDINO
    model = load_model(
        "GroundingDINO_SwinT_OGC.py",
        "groundingdino_swint_ogc.pth"
    )

    image_source, image = load_image(image_path)

    boxes, logits, phrases = predict(
        model=model,
        image=image,
        caption=prompt,
        box_threshold=0.3,
        text_threshold=0.25
    )

    if len(boxes) == 0:
        print("No objects detected.")
        return

    # Load SAM
    sam = sam_model_registry["vit_h"](
        checkpoint="sam_vit_h_4b8939.pth"
    )
    sam.to(device)
    predictor = SamPredictor(sam)

    img_bgr = cv2.imread(image_path)
    predictor.set_image(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB))

    masks = []

    for box in boxes:
        box = box.cpu().numpy()
        box = box * np.array([img_bgr.shape[1], img_bgr.shape[0],
                              img_bgr.shape[1], img_bgr.shape[0]])
        masks_, _, _ = predictor.predict(
            box=box,
            multimask_output=False
        )
        masks.append(masks_[0])

    contours_all = []

    for mask in masks:
        mask_uint8 = (mask * 255).astype(np.uint8)
        contours, _ = cv2.findContours(
            mask_uint8,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )
        contours_all.extend(contours)

    animate_outline(img_bgr, contours_all)
    print("Saved: lis_output.mp4")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python lis.py <image_path> <prompt>")
        sys.exit(1)

    main(sys.argv[1], sys.argv[2])
