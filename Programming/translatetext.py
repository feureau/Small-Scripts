#!/usr/bin/env python3

import sys
import os
import glob
import argparse
import time
import requests
import json
import pycountry  # For language code mapping
import shutil     # For moving files

# --- Configuration ---
DEFAULT_TARGET_LANGUAGE = "English"
DEFAULT_GEMINI_MODEL = "gemini-2.0-flash-exp"  # "gemini-2.0-flash" # "gemini-2.0-flash-lite-preview-02-05" # # # 
DEFAULT_OLLAMA_MODEL = "mistral-small:24b" #"phi4" # "qwen2.5:14b" # Default Ollama model
DEFAULT_ENGINE = "google"
DEFAULT_SUFFIX = "_translated"
OUTPUT_SUBFOLDER = "translated_output"
ORIGINAL_FILES_SUBFOLDER = "original_files" # Subfolder for moved original files
DEFAULT_TRANSLATION_PROMPT = """Translate the following text to natural and idiomatic {target_language}. The goal is to produce a translation that sounds fluent and natural to a native {target_language} speaker, as if written by one. Avoid literal, word-for-word translation. Instead, focus on conveying the meaning accurately using natural {target_language} phrasing, sentence structure, and idiomatic expressions. Rephrase sentences as needed to ensure a smooth and readable flow for a general {target_language} audience. Aim for a slightly informal and approachable tone. This text is from OCR and is **VERY MESSY**. It contains significant errors, typos, gibberish, and formatting problems, including leftover page numbers (like Roman numerals 'IV' or Arabic numerals '123').  You **MUST** perform aggressive cleaning and correction during translation to produce a perfectly clean, readable, and well-formatted translation **using Markdown formatting for structural elements**.

**Specifically, your cleaning, correction, and formatting MUST include:**

* **AGGRESSIVELY correct ALL OCR errors, typos, and gibberish.**  This is the most important step.  Ensure the translated text is free of any OCR artifacts and makes perfect sense.
* **REMOVE ALL page numbers**, whether they are Roman numerals (e.g., I, II, III, IV, V...) or Arabic numerals (e.g., 1, 2, 3...). Do not include any page numbers in the translated output.
* **Ensure proper paragraphing and line breaks for excellent readability.** Paragraphs should be clearly separated by blank lines in the Markdown output.
* **(NEW) Format structural elements using Markdown:** If the original text has structural elements like chapter headings, section headings, etc., please format them using Markdown.
    * Use `#` for chapter headings, `##` for main section headings, and `###` for subsections, etc.  Try to infer the hierarchy from the text if possible, or use `#` for the most prominent headings and `##` for subsequent ones if hierarchy is unclear.
    * Ensure paragraphs are separated by blank lines (standard Markdown).
* **Remove ALL extra whitespace, formatting inconsistencies, and extraneous characters that are artifacts of the OCR process.**

**IMPORTANT:** Provide **ONLY** the final, cleaned, corrected, and translated text in {target_language}, **formatted in Markdown**.  Do **NOT** include the original French text. Do **NOT** include any page numbers. Do **NOT** include any introductory phrases, notes, quotation marks, or anything else.  Just the clean, translated text, perfectly formatted in Markdown and free of errors. Text: {text}"""


# Google Gemini API Key
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    GOOGLE_API_KEY = "YOUR_GOOGLE_API_KEY_HERE"
    print("Warning: GOOGLE_API_KEY environment variable not set...")

# Rate Limiting for Google Gemini
REQUESTS_PER_MINUTE = 15
REQUEST_INTERVAL_SECONDS = 60 / REQUESTS_PER_MINUTE
last_request_time = None

# Ollama API Configuration
OLLAMA_API_URL = "http://localhost:11434/api/chat"
# --- End Configuration ---


def translate_text(text, target_language, engine, gemini_model_name, ollama_model_name, google_api_key, translation_prompt):
    """Translates text using Google Gemini API or Ollama, with rate limiting for Gemini."""
    global last_request_time

    if engine == "google":
        import google.generativeai as genai
        from google.generativeai.types import GenerateContentResponse
        from google.api_core.exceptions import ResourceExhausted

        genai.configure(api_key=google_api_key)
        model = genai.GenerativeModel(gemini_model_name)

        try:
            # --- Rate Limiting for Google Gemini ---
            current_time = time.time()
            if last_request_time is not None:
                time_since_last_request = current_time - last_request_time
                if time_since_last_request < REQUEST_INTERVAL_SECONDS:
                    sleep_duration = REQUEST_INTERVAL_SECONDS - time_since_last_request
                    print(f"Rate limit active (Google Gemini). Sleeping for {sleep_duration:.2f} seconds...")
                    time.sleep(sleep_duration)
            last_request_time = time.time()
            # --- End Rate Limiting ---

            prompt_content = translation_prompt.format(target_language=target_language, text=text)

            print(f"--- Calling Google Gemini API for translation... ---")
            response: GenerateContentResponse = model.generate_content(prompt_content)
            response.resolve()
            print(f"--- Google Gemini API call completed. ---")

            if response.text:
                translated_text = response.text.strip()
                return translated_text
            else:
                print("Warning: No translated text in Google Gemini API response.", file=sys.stderr)
                print(f"Gemini API response details: {response.raw_response}", file=sys.stderr)
                return None

        except ResourceExhausted as e: # Handle Google Gemini Quota Exhaustion (HTTP 429)
            if e.status_code == 429:
                print(f"Error: Google Gemini API Quota Exhausted (HTTP 429).", file=sys.stderr)
                print(f"Quota Exhaustion details: {e}", file=sys.stderr)
                return None
            else:
                print(f"Error calling Google Gemini API (ResourceExhausted, not quota related): {e}", file=sys.stderr)
                return None

        except Exception as e: # Handle other Google Gemini API errors
            print(f"Error calling Google Gemini API: {e}", file=sys.stderr)
            return None

    elif engine == "ollama":
        try:
            prompt_content = translation_prompt.format(target_language=target_language, text=text)

            payload = {
                "model": ollama_model_name,
                "messages": [{"role": "user", "content": prompt_content}],
                "stream": True
            }
            headers = {'Content-Type': 'application/json'}

            try: # Handle connection errors to Ollama API
                print(f"--- Calling Ollama API for translation... Streaming output below: ---")
                response = requests.post(OLLAMA_API_URL, headers=headers, data=json.dumps(payload), stream=True)
                response.raise_for_status()
            except requests.exceptions.ConnectionError as e:
                print(f"Error: Could not connect to Ollama API at {OLLAMA_API_URL}. Is Ollama server running?", file=sys.stderr)
                print(f"Connection error details: {e}", file=sys.stderr)
                return None
            except requests.exceptions.Timeout as e:
                print(f"Error: Timeout connecting to Ollama API at {OLLAMA_API_URL}.", file=sys.stderr)
                print(f"Timeout error details: {e}", file=sys.stderr)
                return None
            except requests.exceptions.RequestException as e: # Handle other request exceptions
                print(f"Error calling Ollama API: {e}", file=sys.stderr)
                if 'response' in locals() and response is not None:
                    print(f"HTTP Status Code: {response.status_code}", file=sys.stderr)
                    print(f"Response Text: {response.text}", file=sys.stderr)
                return None


            try: # Process Ollama streaming response
                translated_text_chunks = []
                for line in response.iter_lines():
                    if line:
                        try:
                            json_line = json.loads(line)
                            if 'message' in json_line and 'content' in json_line['message']:
                                content_chunk = json_line['message']['content']
                                print(content_chunk, end="", flush=True) # Stream output to console
                                translated_text_chunks.append(content_chunk)
                        except json.JSONDecodeError:
                            print(f"Warning: Could not decode JSON line from Ollama stream: {line.decode() if isinstance(line, bytes) else line}", file=sys.stderr)
                            continue
                print("\n--- Ollama API call completed and output streamed. ---")
                translated_text = "".join(translated_text_chunks).strip()
                return translated_text

            except Exception as e: # Handle errors during Ollama stream processing
                print(f"Error processing Ollama API streaming response: {e}", file=sys.stderr)
                return None

        except Exception as e: # Handle unexpected Ollama errors
            print(f"Unexpected error during Ollama translation: {e}", file=sys.stderr)
            return None

    else:
        print(f"Error: Invalid engine '{engine}'. Choose 'google' or 'ollama'.", file=sys.stderr)
        return None


def get_language_name_from_code(language_code):
    """Gets the full language name from a two-digit language code using pycountry."""
    try:
        lang = pycountry.languages.get(alpha_2=language_code)
        if lang:
            return lang.name
        else:
            return None  # Language code not found
    except KeyError:
        return None # Language code not found


def main():
    """Main function to translate text files."""
    global last_request_time
    last_request_time = None
    quota_exhausted = False # Flag for Google Gemini quota exhaustion

    parser = argparse.ArgumentParser(description="Translate text files using Google Gemini or Ollama with OCR cleanup.")
    parser.add_argument("files", nargs="+", help="Path(s) to the text file(s) to translate.")
    parser.add_argument("-l", "--language", default=None, help="Target language (e.g., en, id, fr).")
    parser.add_argument("-e", "--engine", default=DEFAULT_ENGINE, choices=['google', 'ollama'], help=f"AI engine to use: google or ollama.")
    parser.add_argument("-gm", "--gemini-model", default=DEFAULT_GEMINI_MODEL, help=f"Gemini model to use (if engine is google).")
    parser.add_argument("-om", "--ollama-model", default=DEFAULT_OLLAMA_MODEL, help=f"Ollama model to use (if engine is ollama).")
    parser.add_argument("-o", "--output", default=None, help="Output directory (overrides '{OUTPUT_SUBFOLDER}').")
    parser.add_argument("-s", "--suffix", default=DEFAULT_SUFFIX, help=f"Suffix for translated file names.")

    args = parser.parse_args()

    if not args.files:
        print("Error: No files specified.", file=sys.stderr)
        sys.exit(1)

    all_files = []
    for file_pattern in args.files:
       all_files.extend(glob.glob(file_pattern))

    if not all_files:
        print(f"Error: No files found matching the pattern(s).", file=sys.stderr)
        sys.exit(1)

    # Determine target language using pycountry
    if args.language:
        target_language_code = args.language.lower()
        target_language = get_language_name_from_code(target_language_code)
        if not target_language:
            print(f"Error: Invalid language code '{args.language}'. Use valid two-digit language code (e.g., en, fr, id).", file=sys.stderr)
            print("       Refer to pycountry documentation for valid language codes.")
            sys.exit(1)
    else:
        target_language = DEFAULT_TARGET_LANGUAGE

    # Determine output directories
    output_dir = args.output if args.output else OUTPUT_SUBFOLDER
    original_files_dir = os.path.join(os.getcwd(), ORIGINAL_FILES_SUBFOLDER)

    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(original_files_dir, exist_ok=True)

    # Collect translation settings
    translation_settings = {
        "Engine": args.engine,
        "Target Language": target_language,
        "Output Directory": output_dir,
        "Output File Suffix": args.suffix,
        "Translation Prompt": "DEFAULT_TRANSLATION_PROMPT" # Or DEFAULT_TRANSLATION_PROMPT if you want to print the whole prompt, but it's long.
    }
    if args.engine == "google":
        translation_settings["Gemini Model"] = args.gemini_model
    elif args.engine == "ollama":
        translation_settings["Ollama Model"] = args.ollama_model


    for file_path in all_files:
        if not file_path.lower().endswith(".txt"):
            print(f"Skipping non-txt file: {file_path}", file=sys.stderr)
            continue

        print(f"--- Processing file: '{file_path}' ---")
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()

            translated_text = translate_text(
                text,
                target_language,
                args.engine,
                args.gemini_model,
                args.ollama_model,
                GOOGLE_API_KEY,
                DEFAULT_TRANSLATION_PROMPT
            )

            if translated_text:
                base_name = os.path.basename(file_path)
                name, ext = os.path.splitext(base_name)
                output_file_path = os.path.join(output_dir, f"{name}{args.suffix}{ext}")

                with open(output_file_path, "w", encoding="utf-8") as outfile:
                    outfile.write(translated_text)
                print(f"\nTranslated '{file_path}' to {target_language} using {args.engine} engine -> '{output_file_path}'")

                # Move original file after successful translation
                try:
                    original_file_name = os.path.basename(file_path)
                    destination_original_file_path = os.path.join(original_files_dir, original_file_name)
                    os.rename(file_path, destination_original_file_path)
                    print(f"Moved original file '{file_path}' to '{destination_original_file_path}'")
                except Exception as move_error:
                    print(f"Error moving original file '{file_path}' to '{original_files_dir}': {move_error}", file=sys.stderr)


            elif translated_text is None and args.engine == "google": # Handle Google Gemini quota exhaustion
                print(f"Translation failed for '{file_path}' due to Google Gemini Quota Exhaustion. Script will terminate.", file=sys.stderr)
                quota_exhausted = True
                break # Stop processing further files due to quota
            else: # Handle other translation failures
                print(f"Translation failed for '{file_path}'. See error messages above.", file=sys.stderr)


        except FileNotFoundError:
            print(f"Error: File not found: {file_path}", file=sys.stderr)
        except Exception as e:
            print(f"Error processing {file_path}: {e}", file=sys.stderr)
        finally:
            print(f"--- Finished processing file: '{file_path}' ---")

    if quota_exhausted: # Terminate script if Google Gemini quota was exhausted
        print("\n--- Script terminated early due to Google Gemini Quota Exhaustion. ---", file=sys.stderr)
        sys.exit(1) # Exit with error code

    # Print translation settings at the end
    print("\n--- Translation Settings Used ---")
    for key, value in translation_settings.items():
        print(f"{key}: {value}")
    print("--- End Translation Settings ---")


if __name__ == "__main__":
    main()