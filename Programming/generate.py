import sys
import os
import glob
import random
import argparse
import torch
from diffusers import DiffusionPipeline, DPMSolverMultistepScheduler

# -------------------------------
# SDXL settings and model variables
# -------------------------------
# Path to your Juggernaut XL lightning variant model
MODEL_PATH = r"F:\AI\stable-diffusion-webui-forge\webui\models\stable-diffusion\juggernautXL_juggXILightningByRD.safetensors"
# Sampler type (we're using DPM++ SDE via the DPMSolverMultistepScheduler)
SAMPLER = "DPM++ SDE"
# Number of inference steps: random value between STEPS_MIN and STEPS_MAX
STEPS_MIN = 4
STEPS_MAX = 6
# Guidance scale (CFG): random value between CFG_MIN and CFG_MAX
CFG_MIN = 1.0
CFG_MAX = 2.0

# -------------------------------
# Parse command-line arguments
# -------------------------------
parser = argparse.ArgumentParser(description="Generate images from text files using SDXL (Juggernaut XL Lightning variant).")
parser.add_argument("file_pattern", help="File pattern for input text files (e.g., '*.txt').")
parser.add_argument("-c", "--count", type=int, default=1,
                    help="Number of images to generate per text file. Default is 1.")
args = parser.parse_args()

# -------------------------------
# Check for GPU availability; exit if not found.
# -------------------------------
if not torch.cuda.is_available():
    raise EnvironmentError("CUDA GPU not found. This script requires a GPU.")

# -------------------------------
# Load the diffusion pipeline using the model and set the scheduler.
# -------------------------------
# Load the pipeline from your specified model path.
pipe = DiffusionPipeline.from_pretrained(MODEL_PATH, torch_dtype=torch.float16, local_files_only=True)

# Replace the default scheduler with DPMSolverMultistepScheduler which uses DPM++ SDE sampling.
pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config)
pipe = pipe.to("cuda")

# -------------------------------
# Create an output directory for the generated images.
# -------------------------------
output_dir = "generated_images"
os.makedirs(output_dir, exist_ok=True)

# -------------------------------
# Get files matching the provided pattern.
# -------------------------------
files = glob.glob(args.file_pattern)
if not files:
    print(f"No files found matching pattern '{args.file_pattern}'")
    sys.exit(1)

# -------------------------------
# Process each file.
# -------------------------------
for file in files:
    with open(file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    if len(lines) < 2:
        print(f"File '{file}' must contain at least two lines: prompt and negative prompt.")
        continue

    # Read the prompt and negative prompt from the first two lines.
    prompt = lines[0].strip()
    negative_prompt = lines[1].strip()
    
    # Use the base name of the file for naming output images.
    base_name = os.path.splitext(os.path.basename(file))[0]

    for i in range(args.count):
        # Generate a random seed for each image.
        seed = random.randint(0, 2**32 - 1)
        generator = torch.manual_seed(seed)
        
        # Randomly choose the number of inference steps and guidance scale.
        num_inference_steps = random.randint(STEPS_MIN, STEPS_MAX)
        guidance_scale = random.uniform(CFG_MIN, CFG_MAX)
        
        print(f"Generating image {i + 1} for '{file}' with seed {seed}, steps {num_inference_steps}, CFG {guidance_scale:.2f}")

        # Generate the image at 1280x720 resolution with the negative prompt.
        result = pipe(
            prompt,
            negative_prompt=negative_prompt,
            generator=generator,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            height=720,
            width=1280
        )
        image = result.images[0]

        # Construct the output filename to reflect the input file name.
        image_filename = f"{base_name}_img{i+1}_seed_{seed}.png"
        image_path = os.path.join(output_dir, image_filename)
        image.save(image_path)
        print(f"Saved image to {image_path}")
