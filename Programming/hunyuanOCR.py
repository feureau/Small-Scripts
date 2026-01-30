#!/usr/bin/env python3
import argparse
import glob
import os
import sys
import torch
from pathlib import Path
from PIL import Image
from transformers import AutoProcessor, HunYuanVLForConditionalGeneration

# --- CONFIGURATION ---
MODEL_ID = "tencent/HunyuanOCR"
# ---------------------

def setup_model():
    """Loads the model and processor once."""
    print(f"Loading {MODEL_ID} model... (Please wait)")
    try:
        processor = AutoProcessor.from_pretrained(MODEL_ID)
        # Load in float16 for speed and lower VRAM usage
        model = HunYuanVLForConditionalGeneration.from_pretrained(
            MODEL_ID,
            torch_dtype=torch.float16,
            device_map="auto",
            low_cpu_mem_usage=True
        )
        return model, processor
    except Exception as e:
        print(f"Error loading model: {e}")
        sys.exit(1)

def run_ocr(model, processor, image_path):
    """Runs inference on a single image and returns text."""
    try:
        image = Image.open(image_path).convert("RGB")
    except Exception as e:
        print(f"  [!] Could not open image {image_path}: {e}")
        return None

    # Prompt specifically for Markdown output
    prompt = "Transcribe this image to Markdown."
    
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": prompt},
            ],
        }
    ]

    # Prepare inputs
    inputs = processor(
        text=messages,
        images=image,
        return_tensors="pt"
    ).to(model.device)

    # Generate
    with torch.no_grad():
        generated_ids = model.generate(
            **inputs,
            max_new_tokens=2048,
            do_sample=False,    # Critical for OCR accuracy
            temperature=0.0,    # Critical for OCR accuracy
            repetition_penalty=1.05
        )

    output_text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
    return output_text

def main():
    parser = argparse.ArgumentParser(description="Batch convert images to Markdown using HunyuanOCR.")
    parser.add_argument("input_files", nargs='+', help="Images to process (e.g., *.jpg, doc.png)")
    args = parser.parse_args()

    # 1. Expand wildcards (Fix for Windows CMD which doesn't expand *.jpg automatically)
    files_to_process = []
    for pattern in args.input_files:
        # glob.glob handles wildcards; if it's a direct file, it just returns the file
        matches = glob.glob(pattern)
        if not matches:
            # If glob found nothing, maybe the user passed a direct filename that exists
            if os.path.exists(pattern):
                matches = [pattern]
            else:
                print(f"  [!] Warning: No files found matching '{pattern}'")
        files_to_process.extend(matches)

    # Remove duplicates and sort
    files_to_process = sorted(list(set(files_to_process)))

    if not files_to_process:
        print("No valid files found to process.")
        return

    # 2. Load Model (Only once!)
    model, processor = setup_model()
    print(f"Model loaded. Ready to process {len(files_to_process)} files.\n")

    # 3. Iterate and Process
    for file_path in files_to_process:
        path_obj = Path(file_path)
        output_filename = path_obj.with_suffix('.md')
        
        print(f"Processing: {path_obj.name} ...", end="", flush=True)
        
        ocr_result = run_ocr(model, processor, file_path)
        
        if ocr_result:
            with open(output_filename, "w", encoding="utf-8") as f:
                f.write(ocr_result)
            print(f" -> Saved to {output_filename.name}")
        else:
            print(" -> FAILED.")

    print("\nBatch processing complete.")

if __name__ == "__main__":
    main()