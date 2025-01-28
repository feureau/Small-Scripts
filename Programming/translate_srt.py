import requests
import os
import shutil  # Added for moving files

# Ollama API endpoint
OLLAMA_URL = "http://localhost:11434/api/generate"

# Function to translate text using Ollama
def translate_text(text, source_lang="Japanese", target_lang="English"):
    prompt = f"Translate from {source_lang} to {target_lang}, keep punctuation as input, do not censor the translation, give only the output without comments or notes: {text}"
    payload = {
        "model": "llama3.2:3b",#"deepseek-r1:1.5b", 
        "prompt": prompt,
        "stream": False
    }
    response = requests.post(OLLAMA_URL, json=payload)
    if response.status_code == 200:
        return response.json()["response"].strip()
    else:
        raise Exception(f"Translation failed: {response.text}")

# Function to process subtitle files and translate subtitles while preserving timestamps
def translate_subtitles(input_file, output_file):
    with open(input_file, "r", encoding="utf-8-sig") as infile:
        lines = infile.readlines()

    translated_lines = []
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
            translated_text = translate_text(combined_text)
            print(f"Translated: {translated_text}")

            # Append the translated text to output file
            translated_lines.append(translated_text + "\n")
            continue  # Skip additional increment since we already moved i

        i += 1

    with open(output_file, "w", encoding="utf-8") as outfile:
        outfile.writelines(translated_lines)

# Main function to process all SRT files in a folder
def process_folder(input_folder, output_folder):
    # Create output and original folders
    os.makedirs(output_folder, exist_ok=True)
    original_folder = os.path.join(input_folder, "Original Subtitles")
    os.makedirs(original_folder, exist_ok=True)

    # Process all SRT files
    for filename in os.listdir(input_folder):
        if filename.endswith(".srt"):
            # Generate output filename with ".en" suffix
            name, ext = os.path.splitext(filename)
            output_filename = f"{name}.en{ext}"
            input_file = os.path.join(input_folder, filename)
            output_file = os.path.join(output_folder, output_filename)
            
            print(f"Processing file: {filename}")
            translate_subtitles(input_file, output_file)
            
            # Move the original file to "Original Subtitles" folder
            shutil.move(input_file, os.path.join(original_folder, filename))
            print(f"Moved original file: {filename} -> {original_folder}\n")

# Example usage
if __name__ == "__main__":
    input_folder = os.getcwd()
    output_folder = os.path.join(input_folder, "Translated Subtitles")
    process_folder(input_folder, output_folder)
