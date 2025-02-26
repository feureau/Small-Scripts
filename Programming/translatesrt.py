import requests
import os
import shutil  # For moving files
from collections import deque  # For storing previous lines
import sys  # For handling PowerShell exit issue
import time  # For retrying API calls

# ==========================
# CONFIGURABLE PARAMETERS
# ==========================
SOURCE_LANG = "English"         # Source language
TARGET_LANG = "Indonesian"      # Target language
MODEL_NAME = "llama3.1:8b"      # Ollama model to use codellama:13b deepseek-coder-v2:latest deepseek-r1:14b deepseek-r1:7b gemma2:latest llama3.1:8b llama3.2:3b phi4:latest llama3.2-vision:latest mistral-nemo:latest qwen2.5:14b qwen2.5:latest qwen2.5-coder:latest
OLLAMA_URL = "http://localhost:11434/api/generate"  # Ollama API endpoint
CONTEXT_LINES = 5               # Number of previous lines for context
MAX_RETRIES = 3                 # Max retries for API calls
# ==========================

# Function to translate text using Ollama
def translate_text(text, prev_context):
    """Sends text to Ollama for translation, ensuring everything is in the target language"""
    context = "\n".join(prev_context) if prev_context else ""

    prompt = (
        f"Translate the following text from {SOURCE_LANG} to {TARGET_LANG}. "
        f"Ensure that the output is strictly in {TARGET_LANG} and does not contain any words from other languages, except proper nouns. Provide only the translated text without explanations, do not include translation notes, do not include alternative translations, and do not include any context. "
        f"Proper nouns (names, titles) should remain unchanged. "
        f"Keep punctuation as in the original. Do not censor or modify the text. "
        f"\n\n"
    )

    if context:
        prompt += f"Previous context (for reference only, do not translate):\n{context}\n---\n"

    prompt += f"Text to translate:\n{text}\n\n" \
              f"Output only the translated text in {TARGET_LANG}. Do not provide explanations, notes, or alternatives."

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False
    }

    # Retry logic for API failures
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(OLLAMA_URL, json=payload, timeout=30)
            response.raise_for_status()  # Raise exception if status code is not 200
            data = response.json()

            if "response" in data and data["response"].strip():
                return data["response"].strip()
        except requests.exceptions.RequestException:
            if attempt < MAX_RETRIES - 1:
                time.sleep(2)  # Wait before retrying
            else:
                return text  # Return original text if all retries fail

    return text  # Fallback to original text if API fails completely

# Function to process subtitle files and translate subtitles while preserving timestamps
def translate_subtitles(input_file, output_file):
    """Reads an SRT file, translates subtitles while preserving timestamps, and saves the result"""
    try:
        with open(input_file, "r", encoding="utf-8-sig") as infile:
            lines = infile.readlines()
    except Exception:
        return  # Skip this file if reading fails

    translated_lines = []
    previous_lines = deque(maxlen=CONTEXT_LINES)  # Stores up to N previous subtitle lines for context
    i = 0

    while i < len(lines):
        line = lines[i]

        # Preserve subtitle number and timestamps
        if line.strip().isdigit() or "-->" in line:
            translated_lines.append(line)
        elif not line.strip():
            translated_lines.append(line)
        else:
            # Collect all subtitle lines under the same timestamp
            subtitle_text = []
            while i < len(lines) and lines[i].strip() and "-->" not in lines[i] and not lines[i].strip().isdigit():
                subtitle_text.append(lines[i].strip())
                i += 1

            # Join multiple lines into a single translation request
            combined_text = " ".join(subtitle_text)
            print(f"Original: {combined_text}")

            # Translate the text
            translated_text = translate_text(combined_text, list(previous_lines))
            print(f"Translated: {translated_text}")

            # Store the original line (not the translated one) in context history
            previous_lines.append(combined_text)

            # Append the translated text to output file
            translated_lines.append(translated_text + "\n")
            continue  # Skip additional increment since we already moved i

        i += 1

    try:
        with open(output_file, "w", encoding="utf-8") as outfile:
            outfile.writelines(translated_lines)
    except Exception:
        return  # Skip writing if it fails

# Main function to process all SRT files in a folder
def process_folder(input_folder, output_folder):
    """Processes all SRT files in the folder, translates them, and moves originals to a backup folder"""
    os.makedirs(output_folder, exist_ok=True)
    original_folder = os.path.join(input_folder, "Original Subtitles")
    os.makedirs(original_folder, exist_ok=True)

    srt_files = [f for f in os.listdir(input_folder) if f.endswith(".srt")]

    if not srt_files:
        print("No SRT files found in the directory.")
        return

    for filename in srt_files:
        name, ext = os.path.splitext(filename)
        output_filename = f"{name}.en{ext}"
        input_file = os.path.join(input_folder, filename)
        output_file = os.path.join(output_folder, output_filename)

        print(f"Processing file: {filename}")
        translate_subtitles(input_file, output_file)

        # Move the original file to "Original Subtitles" folder
        try:
            shutil.move(input_file, os.path.join(original_folder, filename))
            print(f"Moved original file: {filename} -> {original_folder}\n")
        except Exception:
            pass  # Skip moving if it fails

# Example usage
if __name__ == "__main__":
    input_folder = os.getcwd()
    output_folder = os.path.join(input_folder, "Translated Subtitles")
    process_folder(input_folder, output_folder)

    # Prevent PowerShell from closing immediately
    input("Press Enter to exit...")
