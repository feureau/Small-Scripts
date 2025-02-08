import requests
import os
import shutil
from collections import deque
import sys
import time
import langcodes

# ==========================
# CONFIGURABLE PARAMETERS
# ==========================
SOURCE_LANG = "English"
TARGET_LANG = "Indonesian"
MODEL_NAME = "qwen2.5:14b"
OLLAMA_URL = "http://localhost:11434/api/generate"
CONTEXT_LINES = 3
MAX_RETRIES = 3
# ==========================

try:
    TARGET_LANG_CODE = langcodes.find(TARGET_LANG).language
except LookupError:
    print(f"Warning: Could not determine language code for '{TARGET_LANG}', using 'id' as fallback.")
    TARGET_LANG_CODE = "id"  # Fallback to Indonesian

def translate_text(text, prev_context):
    """Sends text to Ollama for translation with context"""
    context = "\n".join(prev_context) if prev_context else ""

    prompt = (
        f"Translate the following text from {SOURCE_LANG} to {TARGET_LANG}. "
        f"Maintain the original formatting and paragraph structure. "
        f"Preserve proper nouns (names, places, titles) and punctuation. "
        f"Ensure natural {TARGET_LANG} grammar and flow. "
        f"Respond only with the translation.\n\n"
    )

    if context:
        prompt += f"Previous Context (for reference):\n{context}\n\n"

    prompt += f"Text to translate:\n{text}"

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False
    }

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(OLLAMA_URL, json=payload, timeout=120)
            response.raise_for_status()
            data = response.json()
            return data["response"].strip()
        except Exception as e:
            print(f"API error (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
            time.sleep(2)

    return text  # Fallback

def translate_text_file(input_file, output_file):
    """Processes a text file paragraph by paragraph"""
    try:
        with open(input_file, "r", encoding="utf-8-sig") as infile:
            lines = [line.rstrip('\n') for line in infile.readlines()]
    except Exception as e:
        print(f"Error reading {input_file}: {e}")
        return

    translated_content = []
    previous_paragraphs = deque(maxlen=CONTEXT_LINES)
    current_paragraph = []

    for line in lines:
        if line.strip():
            current_paragraph.append(line.strip())
        else:
            if current_paragraph:
                combined_text = " ".join(current_paragraph)
                translated = translate_text(combined_text, list(previous_paragraphs))
                translated_content.append(translated + "\n\n")
                previous_paragraphs.append(combined_text)
                current_paragraph = []
    
    if current_paragraph:
        combined_text = " ".join(current_paragraph)
        translated = translate_text(combined_text, list(previous_paragraphs))
        translated_content.append(translated + "\n\n")

    try:
        with open(output_file, "w", encoding="utf-8") as outfile:
            outfile.write("".join(translated_content).rstrip() + "\n")
    except Exception as e:
        print(f"Error writing {output_file}: {e}")

def process_folder(input_folder, output_folder):
    """Processes all text files in the directory"""
    os.makedirs(output_folder, exist_ok=True)
    original_folder = os.path.join(input_folder, "Original Texts")
    os.makedirs(original_folder, exist_ok=True)

    txt_files = [f for f in os.listdir(input_folder) if f.endswith(".txt")]

    if not txt_files:
        print("No text files found")
        return

    for filename in txt_files:
        name, ext = os.path.splitext(filename)
        output_filename = f"{name}.{TARGET_LANG_CODE}{ext}"
        input_path = os.path.join(input_folder, filename)
        output_path = os.path.join(output_folder, output_filename)

        print(f"Processing: {filename}")
        translate_text_file(input_path, output_path)

        try:
            shutil.move(input_path, os.path.join(original_folder, filename))
            print(f"Archived original: {filename}")
        except Exception as e:
            print(f"Failed to move {filename}: {e}")

if __name__ == "__main__":
    input_dir = os.getcwd()
    output_dir = os.path.join(input_dir, "Translated Texts")
    process_folder(input_dir, output_dir)
    input("Press Enter to exit...")