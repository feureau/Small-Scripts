import cv2
import numpy as np
from PIL import Image, UnidentifiedImageError
import os
import glob
import argparse
import sys

# --- Configuration for Object Detection (Defaults for YOLOv4-tiny) ---
# IMPORTANT: You MUST download these files and update the paths if they are different,
# or provide them via command-line arguments.
DEFAULT_MODEL_WEIGHTS = "yolov4-tiny.weights"
DEFAULT_MODEL_CONFIG = "yolov4-tiny.cfg"
DEFAULT_CLASS_NAMES = "coco.names"
DEFAULT_CONFIDENCE_THRESHOLD = 0.5
DEFAULT_NMS_THRESHOLD = 0.4 # Non-Maximum Suppression threshold
DEFAULT_INPUT_SIZE = 416 # YOLO input size (can be 320, 416, 608, etc.)

def load_object_detection_model(weights_path, config_path):
    """Loads the object detection model from disk."""
    print(f"[INFO] Loading model from {weights_path} and {config_path}...")
    try:
        net = cv2.dnn.readNetFromDarknet(config_path, weights_path)
        # Optional: Set preferable backend and target (e.g., for GPU usage if OpenCV is compiled with CUDA support)
        # net.setPreferableBackend(cv2.dnn.DNN_BACKEND_CUDA)
        # net.setPreferableTarget(cv2.dnn.DNN_TARGET_CUDA)
        print("[INFO] Model loaded successfully.")
        return net
    except cv2.error as e:
        print(f"[ERROR] Could not load the model. OpenCV error: {e}")
        print(f"[ERROR] Please ensure '{weights_path}' and '{config_path}' are correct and accessible.")
        return None

def load_class_names(names_path):
    """Loads class names from a file."""
    try:
        with open(names_path, "r") as f:
            class_names = [line.strip() for line in f.readlines()]
        print(f"[INFO] Loaded {len(class_names)} class names.")
        return class_names
    except FileNotFoundError:
        print(f"[ERROR] Class names file not found: {names_path}")
        return None

def perform_object_detection(image_cv, net, class_names_all, args):
    """
    Performs object detection on the image.
    Returns the crop box (x, y, w, h) for the best target object, or None.
    """
    if net is None or class_names_all is None:
        return None

    H, W = image_cv.shape[:2]
    blob = cv2.dnn.blobFromImage(image_cv, 1 / 255.0, (DEFAULT_INPUT_SIZE, DEFAULT_INPUT_SIZE),
                                 swapRB=True, crop=False)
    net.setInput(blob)

    layer_names = net.getLayerNames()
    # Correctly get output layer names for different OpenCV versions
    try:
        output_layer_names = [layer_names[i - 1] for i in net.getUnconnectedOutLayers().flatten()]
    except AttributeError: # For older OpenCV versions where getUnconnectedOutLayers() returns indices directly
        output_layer_names = [layer_names[i[0] - 1] for i in net.getUnconnectedOutLayers()]


    layer_outputs = net.forward(output_layer_names)

    boxes = []
    confidences = []
    class_ids = []

    for output in layer_outputs:
        for detection in output:
            scores = detection[5:]
            class_id = np.argmax(scores)
            confidence = scores[class_id]

            if confidence > args.confidence_threshold:
                box_cv = detection[0:4] * np.array([W, H, W, H])
                (centerX, centerY, width, height) = box_cv.astype("int")
                x = int(centerX - (width / 2))
                y = int(centerY - (height / 2))

                boxes.append([x, y, int(width), int(height)])
                confidences.append(float(confidence))
                class_ids.append(class_id)

    # Apply Non-Maximum Suppression
    indices = cv2.dnn.NMSBoxes(boxes, confidences, args.confidence_threshold, DEFAULT_NMS_THRESHOLD)

    if len(indices) == 0:
        print("[INFO] No objects detected meeting the confidence threshold after NMS.")
        return None

    target_objects_found = [] # List of (box, confidence, class_name, area)

    for i in indices.flatten():
        box = boxes[i]
        confidence = confidences[i]
        class_id = class_ids[i]
        class_name = class_names_all[class_id]
        area = box[2] * box[3] # width * height

        if args.target_object_class:
            if class_name.lower() == args.target_object_class.lower():
                target_objects_found.append(((box[0], box[1], box[2], box[3]), confidence, class_name, area))
        else: # No specific target, consider all detected objects
            target_objects_found.append(((box[0], box[1], box[2], box[3]), confidence, class_name, area))

    if not target_objects_found:
        if args.target_object_class:
            print(f"[INFO] Target object '{args.target_object_class}' not found.")
        else:
            print("[INFO] No suitable objects found after filtering.")
        return None

    # Select the best object (e.g., largest area if no specific class, or largest of the target class)
    # If target_object_class is specified, all items in target_objects_found are of that class.
    # If not, we pick the largest of any detected object.
    best_object = max(target_objects_found, key=lambda item: item[3]) # Sort by area
    
    final_box_coords = best_object[0] # (x, y, w, h)
    print(f"[INFO] Selected object: {best_object[2]} with confidence {best_object[1]:.2f} and area {best_object[3]}")
    
    # Apply padding
    x, y, w, h = final_box_coords
    padding_w = int(w * (args.crop_padding_percent / 100.0))
    padding_h = int(h * (args.crop_padding_percent / 100.0))

    crop_x1 = max(0, x - padding_w)
    crop_y1 = max(0, y - padding_h)
    crop_x2 = min(W, x + w + padding_w)
    crop_y2 = min(H, y + h + padding_h)
    
    # Return as (x_start, y_start, x_end, y_end) for Pillow's crop
    return (crop_x1, crop_y1, crop_x2, crop_y2)


def get_percentage_crop_box(img_width, img_height, percentage):
    """Calculates the crop box for a percentage-based center crop."""
    crop_w = int(img_width * (percentage / 100.0))
    crop_h = int(img_height * (percentage / 100.0))

    x_offset = (img_width - crop_w) // 2
    y_offset = (img_height - crop_h) // 2

    # Pillow crop box is (left, upper, right, lower)
    return (x_offset, y_offset, x_offset + crop_w, y_offset + crop_h)

def process_image(image_path, output_path, args, net=None, class_names_all=None):
    """Processes a single image: crops and saves it."""
    try:
        print(f"[INFO] Processing image: {image_path}")
        img_pil = Image.open(image_path)
        img_pil = img_pil.convert("RGB") # Ensure 3 channels for consistency
        img_width, img_height = img_pil.size

        crop_box = None

        if not args.disable_od and net:
            # Convert PIL image to OpenCV format for detection
            img_cv = np.array(img_pil)
            img_cv = cv2.cvtColor(img_cv, cv2.COLOR_RGB2BGR) # OpenCV uses BGR
            
            crop_box_od = perform_object_detection(img_cv, net, class_names_all, args)
            if crop_box_od:
                crop_box = crop_box_od # (x1, y1, x2, y2)
                print(f"[INFO] Using object detection crop box: {crop_box}")
            else:
                print("[INFO] Object detection did not yield a crop box. Falling back to percentage crop.")
        
        if crop_box is None: # Fallback or OD disabled
            if args.disable_od:
                print("[INFO] Object detection disabled. Using percentage crop.")
            crop_box = get_percentage_crop_box(img_width, img_height, args.fallback_crop_percentage)
            print(f"[INFO] Using percentage crop box: {crop_box}")

        # Validate crop box (ensure it's within image bounds and valid)
        if not (0 <= crop_box[0] < crop_box[2] <= img_width and \
                0 <= crop_box[1] < crop_box[3] <= img_height):
            print(f"[WARNING] Invalid crop box {crop_box} for image size {(img_width, img_height)}. Skipping crop for {image_path}.")
            # Fallback to full image or a default safe crop if necessary, or just skip
            # For now, let's save the original if the crop box is bad after trying.
            # A better fallback might be a 100% crop (i.e., no crop) or a very safe small center crop.
            # Or simply skip saving this image if cropping is essential.
            # Let's try to make a safe full crop if the box is invalid.
            crop_box = (0, 0, img_width, img_height)
            print(f"[INFO] Fallback to full image crop due to invalid calculated box for {image_path}")


        cropped_img_pil = img_pil.crop(crop_box)

        # Save the cropped image
        save_format = args.output_format.upper()
        if save_format == "JPEG": save_format = "JPG" # Pillow uses JPG

        if args.output_format.lower() == 'jpg':
            cropped_img_pil.save(output_path, format='JPEG', quality=args.quality)
        elif args.output_format.lower() == 'png':
            cropped_img_pil.save(output_path, format='PNG')
        else:
            print(f"[WARNING] Unsupported output format: {args.output_format}. Defaulting to JPG.")
            cropped_img_pil.save(output_path, format='JPEG', quality=args.quality)
        
        print(f"[INFO] Saved cropped image to: {output_path}")
        return True

    except FileNotFoundError:
        print(f"[ERROR] Image file not found: {image_path}")
        return False
    except UnidentifiedImageError:
        print(f"[ERROR] Cannot identify image file (it may be corrupt or not a supported format): {image_path}")
        return False
    except Exception as e:
        print(f"[ERROR] An unexpected error occurred while processing {image_path}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Batch crop images using object detection or percentage crop.")
    
    # Input/Output Arguments
    parser.add_argument("-i", "--input_folder", type=str, default=".",
                        help="Path to the folder containing images. Default: current directory.")
    parser.add_argument("-o", "--output_folder_name", type=str, default="cropped_output",
                        help="Name for the output subfolder. Default: 'cropped_output'.")
    parser.add_argument("-f", "--output_format", type=str, default="jpg", choices=["jpg", "png"],
                        help="Output image format ('jpg' or 'png'). Default: 'jpg'.")
    parser.add_argument("-q", "--quality", type=int, default=95,
                        help="Quality for JPG output (1-100). Default: 95.")

    # Object Detection Control Arguments
    parser.add_argument("--disable_od", action="store_true",
                        help="Disable object detection and force percentage crop.")
    parser.add_argument("--target_object_class", type=str, default=None,
                        help="Specific object class to target for cropping (e.g., 'person', 'car'). Default: None (detects largest/most confident object).")
    parser.add_argument("--confidence_threshold", type=float, default=DEFAULT_CONFIDENCE_THRESHOLD,
                        help=f"Minimum probability to filter weak detections. Default: {DEFAULT_CONFIDENCE_THRESHOLD}.")
    parser.add_argument("--crop_padding_percent", type=int, default=10,
                        help="Percentage to expand the detected bounding box for the final crop. Default: 10.")

    # Fallback Percentage Crop Arguments
    parser.add_argument("--fallback_crop_percentage", type=float, default=80.0,
                        help="Percentage for center crop if OD is disabled or fails (1-100). Default: 80.0.")

    # Model Configuration Arguments
    parser.add_argument("--model_weights", type=str, default=DEFAULT_MODEL_WEIGHTS,
                        help=f"Path to object detection model weights file. Default: '{DEFAULT_MODEL_WEIGHTS}'.")
    parser.add_argument("--model_config", type=str, default=DEFAULT_MODEL_CONFIG,
                        help=f"Path to object detection model configuration file. Default: '{DEFAULT_MODEL_CONFIG}'.")
    parser.add_argument("--class_names", type=str, default=DEFAULT_CLASS_NAMES,
                        help=f"Path to file containing class names for the model. Default: '{DEFAULT_CLASS_NAMES}'.")

    args = parser.parse_args()

    # Validate fallback crop percentage
    if not (0 < args.fallback_crop_percentage <= 100):
        print("[ERROR] Fallback crop percentage must be between 0 (exclusive) and 100 (inclusive).")
        sys.exit(1)
    if not (0 <= args.crop_padding_percent <= 100): # Padding can be 0
        print("[ERROR] Crop padding percentage must be between 0 and 100.")
        sys.exit(1)


    # --- Setup ---
    # Determine input directory (current working directory if not specified)
    # The script is typically run *from* the directory containing images,
    # or an input_folder is specified relative to where the script is run.
    input_dir = os.path.abspath(args.input_folder) # Get absolute path
    if not os.path.isdir(input_dir):
        print(f"[ERROR] Input folder not found: {input_dir}")
        sys.exit(1)

    # Create output directory (as a subfolder of the input_dir or current working dir if input_folder is '.')
    # If input_folder is '.', output is './cropped_output'. If input_folder is 'some/path', output is 'some/path/cropped_output'
    base_output_dir = input_dir if args.input_folder != "." else os.getcwd()
    output_dir = os.path.join(base_output_dir, args.output_folder_name)
    
    try:
        os.makedirs(output_dir, exist_ok=True)
        print(f"[INFO] Output will be saved to: {output_dir}")
    except OSError as e:
        print(f"[ERROR] Could not create output directory {output_dir}: {e}")
        sys.exit(1)


    # Load OD model and class names if OD is not disabled
    net = None
    class_names_all = None
    if not args.disable_od:
        # Check if model files exist before trying to load
        if not os.path.exists(args.model_weights):
            print(f"[WARNING] Model weights file not found: {args.model_weights}. Object detection will be skipped.")
            args.disable_od = True # Effectively disable OD if files are missing
        elif not os.path.exists(args.model_config):
            print(f"[WARNING] Model config file not found: {args.model_config}. Object detection will be skipped.")
            args.disable_od = True
        elif not os.path.exists(args.class_names):
            print(f"[WARNING] Class names file not found: {args.class_names}. Object detection will be skipped.")
            args.disable_od = True
        
        if not args.disable_od: # Re-check if it wasn't disabled by missing files
            net = load_object_detection_model(args.model_weights, args.model_config)
            class_names_all = load_class_names(args.class_names)
            if net is None or class_names_all is None:
                print("[WARNING] Failed to load model or class names. Falling back to percentage crop for all images.")
                args.disable_od = True # Force disable if loading failed

    # Find images
    supported_extensions = ["*.jpg", "*.jpeg", "*.png", "*.bmp", "*.tiff", "*.gif",
                              "*.JPG", "*.JPEG", "*.PNG", "*.BMP", "*.TIFF", "*.GIF"]
    image_paths = []
    for ext in supported_extensions:
        image_paths.extend(glob.glob(os.path.join(input_dir, ext)))

    if not image_paths:
        print(f"[INFO] No images found in {input_dir} with supported extensions.")
        sys.exit(0)

    print(f"[INFO] Found {len(image_paths)} images to process.")

    # Process images
    success_count = 0
    failure_count = 0
    for image_path in image_paths:
        base_name = os.path.basename(image_path)
        name_part, ext_part = os.path.splitext(base_name)
        
        # Construct output path with potentially new extension
        output_filename = f"{name_part}_cropped.{args.output_format.lower()}"
        output_file_path = os.path.join(output_dir, output_filename)

        if process_image(image_path, output_file_path, args, net, class_names_all):
            success_count += 1
        else:
            failure_count += 1
            
    print(f"\n[INFO] --- Processing Complete ---")
    print(f"[INFO] Successfully processed: {success_count} images.")
    print(f"[INFO] Failed to process: {failure_count} images.")

if __name__ == "__main__":
    main()
