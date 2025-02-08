#!/usr/bin/env python3

import sys
import os
import glob
import argparse
import google.generativeai as genai  # Import Google Gemini API library
import time

# --- Rate Limiting Configuration ---
REQUESTS_PER_MINUTE = 15  # Maximum requests per minute - DEFAULT IS NOW 15
REQUEST_INTERVAL_SECONDS = 60 / REQUESTS_PER_MINUTE # Minimum interval between requests
last_request_time = None # Initialize last request time

# --- Configuration ---
DEFAULT_TARGET_LANGUAGE = "English" # Default target language if no flag is provided - now English
DEFAULT_GEMINI_MODEL = "gemini-2.0-flash" # Default Gemini model
DEFAULT_SUFFIX = "_translated"
OUTPUT_SUBFOLDER = "translated_output"
DEFAULT_TRANSLATION_PROMPT = """Translate the following French text to {target_language}.  This text is from OCR and is **VERY MESSY**. It contains significant errors, typos, gibberish, and formatting problems, including leftover page numbers (like Roman numerals 'IV' or Arabic numerals '123').  You **MUST** perform aggressive cleaning and correction during translation to produce a perfectly clean, readable, and well-formatted translation.

**Specifically, your cleaning and correction MUST include:**

* **AGGRESSIVELY correct ALL OCR errors, typos, and gibberish.**  This is the most important step.  Ensure the translated text is free of any OCR artifacts and makes perfect sense.
* **REMOVE ALL page numbers**, whether they are Roman numerals (e.g., I, II, III, IV, V...) or Arabic numerals (e.g., 1, 2, 3...). Do not include any page numbers in the translated output.
* **Ensure proper paragraphing and line breaks for excellent readability.**
* **Remove ALL extra whitespace, formatting inconsistencies, and extraneous characters that are artifacts of the OCR process.**

**IMPORTANT:** Provide **ONLY** the final, cleaned, corrected, and translated text in {target_language}.  Do **NOT** include the original French text. Do **NOT** include any page numbers. Do **NOT** include any introductory phrases, notes, quotation marks, or anything else.  Just the clean, translated text, perfectly formatted and free of errors. Text: {text}"""

LANGUAGE_CODE_MAP = { # Mapping of two-digit language codes to full language names
    "en": "English",
    "id": "Bahasa Indonesia",
    "fr": "French",
    "es": "Spanish",
    # Add more languages as needed
}

# Google Gemini API Key -  Try to get from environment variable, otherwise use placeholder
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY") # Get API key from environment variable
if not GOOGLE_API_KEY:
    GOOGLE_API_KEY = "YOUR_GOOGLE_API_KEY_HERE"  # <---  **REPLACE WITH YOUR ACTUAL API KEY IF ENV VAR IS NOT SET**
    print("Warning: GOOGLE_API_KEY environment variable not set. Using placeholder API key from script.")
    print("         Please set the GOOGLE_API_KEY environment variable for security and proper functionality.")

# --- End Configuration ---


def translate_text(text, target_language, gemini_model_name, google_api_key, translation_prompt): # Added translation_prompt parameter
    """Translates text using Google Gemini API with rate limiting.

    Args:
        text: The text to translate.
        target_language: The target language name (full language name).
        gemini_model_name: The Gemini model to use.
        google_api_key: Your Google Gemini API key.
        translation_prompt: The prompt to use for translation. # Added documentation for new parameter

    Returns:
        The translated text, or None if an error occurred.
    """
    global last_request_time

    genai.configure(api_key=google_api_key)
    model = genai.GenerativeModel(gemini_model_name) # Use configured Gemini model

    try:
        # --- Rate Limiting Implementation ---
        current_time = time.time()
        if last_request_time is not None:
            time_since_last_request = current_time - last_request_time
            if time_since_last_request < REQUEST_INTERVAL_SECONDS:
                sleep_duration = REQUEST_INTERVAL_SECONDS - time_since_last_request
                print(f"Rate limit active. Sleeping for {sleep_duration:.2f} seconds...")
                time.sleep(sleep_duration)
        # Update last request time before making the API call
        last_request_time = time.time()
        # --- End Rate Limiting ---

        # Prompt for Gemini API - **Using configurable prompt variable**
        prompt_content = translation_prompt.format(target_language=target_language, text=text) # Use .format to insert variables

        response = model.generate_content(prompt_content)
        response.resolve() # Ensure the response is fully resolved

        if response.text:
            translated_text = response.text.strip()
            return translated_text
        else:
            print("Warning: No translated text in Gemini API response.", file=sys.stderr)
            print(f"Gemini API response details: {response.raw_response}", file=sys.stderr)
            return None


    except Exception as e:
        print(f"Error calling Google Gemini API: {e}", file=sys.stderr)
        return None


def main():
    global last_request_time # Access the global variable
    last_request_time = None # Reset last_request_time at the start of main if needed

    parser = argparse.ArgumentParser(description="Translate text files using Google Gemini API with rate limiting and OCR cleanup.") # Updated description
    parser.add_argument("files", nargs="+", help="Path(s) to the text file(s) to translate.")
    #parser.add_argument("-t", "--target", default=DEFAULT_TARGET_LANGUAGE, help=f"Target language code (e.g., en, es, fr, Bahasa Indonesia). Default: '{DEFAULT_TARGET_LANGUAGE}'") # Updated help text - REMOVED
    parser.add_argument("-l", "--language", default=None, help="Target language for translation using two-digit language code (e.g., en for English, id for Bahasa Indonesia). Overrides default language.") # NEW language flag
    parser.add_argument("-m", "--model", default=DEFAULT_GEMINI_MODEL, help=f"Gemini model to use. Default: {DEFAULT_GEMINI_MODEL}") # Now for Gemini model
    parser.add_argument("-o", "--output", default=None, help="Output directory (overrides subfolder). If not specified, translated files are placed in '{OUTPUT_SUBFOLDER}' subfolder.")
    parser.add_argument("-s", "--suffix", default=DEFAULT_SUFFIX, help=f"Suffix to add to the translated file name. Default: {DEFAULT_SUFFIX}")
    # No need to add argument for prompt as it's a configuration variable

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

    # Determine target language
    if args.language:
        target_language_code = args.language.lower() # Ensure lowercase for lookup
        if target_language_code in LANGUAGE_CODE_MAP:
            target_language = LANGUAGE_CODE_MAP[target_language_code]
        else:
            print(f"Error: Invalid language code '{args.language}'. Please use a valid two-digit language code (e.g., en, id, fr).", file=sys.stderr)
            sys.exit(1)
    else:
        target_language = DEFAULT_TARGET_LANGUAGE # Use default if no language flag

    # Determine output directory
    if args.output:
        output_dir = args.output
    else:
        output_dir = OUTPUT_SUBFOLDER

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    for file_path in all_files:
        if not file_path.lower().endswith(".txt"):
            print(f"Skipping non-txt file: {file_path}", file=sys.stderr)
            continue

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()

            # Pass target_language (full name), args.model, API key and DEFAULT_TRANSLATION_PROMPT to translate_text function
            translated_text = translate_text(text, target_language, args.model, GOOGLE_API_KEY, DEFAULT_TRANSLATION_PROMPT) # Pass the prompt variable

            if translated_text:
                base_name = os.path.basename(file_path)
                name, ext = os.path.splitext(base_name)
                output_file_path = os.path.join(output_dir, f"{name}{args.suffix}{ext}")

                with open(output_file_path, "w", encoding="utf-8") as outfile:
                    outfile.write(translated_text)
                print(f"Translated '{file_path}' to {target_language} -> '{output_file_path}'") # Updated print message

        except FileNotFoundError:
            print(f"Error: File not found: {file_path}", file=sys.stderr)
        except Exception as e:
            print(f"Error processing {file_path}: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()