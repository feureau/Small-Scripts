#!/usr/bin/env python3
import sys
import os
import glob
import argparse
import re
import mimetypes
from google import genai
from google.genai import types

def natural_sort_key(s):
    """Return a list of strings and integers to use as sort key for natural ordering."""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]

def get_available_models(client):
    """Retrieve all available models from the API."""
    models = list(client.models.list())
    if not models:
        raise ValueError("No models available from the API.")
    return models

def choose_model(client):
    """Lists available models and prompts the user to select one."""
    models = get_available_models(client)
    print("Available models:")
    for idx, model in enumerate(models):
        print(f"{idx}: {model.name}")
    
    while True:
        selection = input("Enter the number for the model you want to use: ").strip()
        try:
            index = int(selection)
            if 0 <= index < len(models):
                chosen = models[index]
                break
            else:
                print(f"Please enter a number between 0 and {len(models)-1}.")
        except ValueError:
            print("Invalid input. Please enter a number.")
    print(f"Using model: {chosen.name}")
    return chosen.name

def get_mime_type(filepath):
    """Determine the MIME type of a file dynamically using the mimetypes module."""
    mime_type, _ = mimetypes.guess_type(filepath)
    if mime_type is None or not mime_type.startswith("image/"):
        return None
    return mime_type

def transcribe_and_cleanup_image(image_path, model_name, mime_type, client):
    # Read image bytes from the local file
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    
    # Create a Part object from the image bytes using from_bytes helper
    image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
    
    # Define a prompt that instructs the model to extract and clean up the text.
    prompt_text = (
        "Extract the text from the image exactly and then clean up the output. "
        "Remove any unnecessary line breaks and spaces, and format the text into well-structured paragraphs. "
        "Return only the cleaned text without any extra commentary."
    )
    
    # Build the contents list: first element is the prompt, second is the image part.
    contents = [prompt_text, image_part]
    
    # Call the API to generate content using the provided model and contents.
    response = client.models.generate_content(model=model_name, contents=contents)
    return response.text.strip()

def main():
    parser = argparse.ArgumentParser(
        description="Transcribe and clean up text from image files using Google Gen AI."
    )
    parser.add_argument("files", nargs="+", help="File patterns to process (e.g., *.webp, *.jpg, *.png)")
    args = parser.parse_args()
    
    # Expand wildcard file patterns using glob and apply natural sort
    file_list = []
    for pattern in args.files:
        matched = glob.glob(pattern)
        if not matched:
            print(f"Warning: No files found for pattern '{pattern}'.", file=sys.stderr)
        file_list.extend(matched)
    
    if not file_list:
        print("Error: No files found matching the provided pattern(s).", file=sys.stderr)
        sys.exit(1)
    
    file_list = sorted(file_list, key=natural_sort_key)
    
    # Load API key from environment
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("Error: GOOGLE_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)
    
    # Create the Gen AI client
    client = genai.Client(api_key=api_key)
    
    # Always prompt the user to choose a model.
    model_name = choose_model(client)
    
    # Process each file matching the provided patterns.
    for image_path in file_list:
        mime_type = get_mime_type(image_path)
        if not mime_type:
            print(f"Skipping '{image_path}': not a recognized image file.", file=sys.stderr)
            continue
        try:
            print(f"\nProcessing: {image_path}")
            transcription = transcribe_and_cleanup_image(image_path, model_name, mime_type, client)
            print("Cleaned Transcription:")
            print(transcription)
            
            # Save the transcription to a text file (without model metadata)
            output_file = os.path.splitext(image_path)[0] + "_transcription.txt"
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(transcription)
            print(f"Transcription saved to: {output_file}")
            
        except Exception as e:
            print(f"Error processing '{image_path}': {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
