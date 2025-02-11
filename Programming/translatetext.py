#!/usr/bin/env python3

import sys
import os
import glob
import argparse
import time
import requests
import json
import pycountry
import shutil
import re
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
import tkinter.messagebox

# --- Configuration ---
DEFAULT_TARGET_LANGUAGE = "en" # Changed to "en" for two-letter code default
DEFAULT_GEMINI_MODELS = ["gemini-2.0-pro-exp-02-05","gemini-2.0-flash-thinking-exp-01-21","gemini-2.0-flash-exp", "gemini-2.0-flash", "gemini-2.0-flash-lite-preview-02-05"]
DEFAULT_OLLAMA_MODELS = ["mistral-small:24b", "phi4", "qwen2.5:14b"]
DEFAULT_ENGINE = "google"
DEFAULT_SUFFIX = "_processed"
OUTPUT_SUBFOLDER = "processed_output"
ORIGINAL_FILES_SUBFOLDER = "original_files"

# --- Prompts ---
DEFAULT_TRANSLATION_PROMPT_REFINED_V7_COND_FORMAT = """**IMPORTANT: TRANSLATE ALL TEXT to natural and idiomatic {target_language}. DO NOT LEAVE ANY TEXT IN THE ORIGINAL LANGUAGE. TRANSLATE EVERYTHING.**

Translate the following text to natural and idiomatic {target_language}. The goal is to produce a translation that sounds fluent and natural to a native {target_language} speaker, as if written by one. Avoid literal, word-for-word translation. Instead, focus on conveying the meaning accurately using natural {target_language} phrasing, sentence structure, and idiomatic expressions. Rephrase sentences as needed to ensure a smooth and readable flow for a general {target_language} audience. Aim for a slightly informal and approachable tone. This text is from OCR and is **VERY MESSY**. It contains significant errors, typos, gibberish, and formatting problems, including leftover page numbers (like Roman numerals 'IV' or Arabic numerals '123').  You **MUST** perform aggressive cleaning and correction during translation to produce a perfectly clean, readable, and well-formatted translation **using Markdown formatting for structural elements**.

**Specifically, your cleaning, correction, and formatting MUST include:**

* **AGGRESSIVELY correct ALL OCR errors, typos, and gibberish.**  This is the most important step.  Ensure the translated text is free of any OCR artifacts and makes perfect sense.
* **REMOVE ALL page numbers**, whether they are Roman numerals (e.g., I, II, III, IV, V...) or Arabic numerals (e.g., 1, 2, 3...). Do not include any page numbers in the translated output.
* **Ensure proper paragraphing and line breaks for excellent readability.** Paragraphs should be clearly separated by blank lines in the Markdown output.
* **(NEW) Format structural elements using Markdown:** If the original text has structural elements like chapter headings, section headings, etc., please format them using Markdown.
    * Use `#` for chapter headings, `##` for main section headings, and `###` for subsections, etc.  Try to infer the hierarchy from the text if possible, or use `#` for the most prominent headings and `##` for subsequent ones if hierarchy is unclear.
    * Ensure paragraphs are separated by blank lines (standard Markdown).
* **Remove ALL extra whitespace, formatting inconsistencies, and extraneous characters that are artifacts of the OCR process.**

**IMPORTANT: MANDATORY PINYIN TRANSLITERATION WITH TONE MARKS AND CONDITIONAL FORMATTING FOR CHINESE NAMES AND GENERAL CHINESE TERMS.  CHINESE CHARACTERS MUST BE INCLUDED.  DO NOT ITALICIZE CHINESE NAMES OR TERMS.**

* **ITALICS:** **DO NOT ITALICIZE CHINESE NAMES OR GENERAL CHINESE TERMS** in the output, even if they are italicized in the original text. However, if you identify POEMS or VERSES, **FIRST TRANSLATE THEM TO {target_language}**, and then format the **TRANSLATED POEMS/VERSES** in italics in the Markdown output using asterisks `*poem line*`. **ENSURE POEMS ARE TRANSLATED TO {target_language}.**
* **CHINESE CHARACTERS:**  You **MUST INCLUDE** the original Chinese characters for all **CHINESE NAMES** in the translation. **FOR GENERAL CHINESE TERMS ORIGINALLY IN CHINESE, INCLUDE CHINESE CHARACTERS IN BRACKETS AFTER THE TRANSLATED TERM.**
* **PINYIN TRANSLITERATION (ALL CHINESE TERMS):** For **ALL CHINESE TERMS** (names and general terms originally in Chinese), you **ABSOLUTELY MUST** use **Hànyǔ Pīnyīn (汉语拼音)** - the standard and ONLY acceptable romanization system for Mandarin Chinese - for the transliterated term. **CRITICALLY IMPORTANT: Ensure Hanyu Pinyin is provided with CORRECT TONE MARKS for all Chinese terms.** **FOR BOTH NAMES AND GENERAL TERMS, INCLUDE HANYU PINYIN IN BRACKETS AFTER THE CHINESE CHARACTERS.** Example format for general terms:  `Translated Term (Chinese Characters Pinyin)`.
* **CONDITIONAL FORMATTING FOR NAMES - IMPORTANT:**
    * **CASE 1: TRANSLATED NAME IS DIFFERENT FROM PINYIN:** If the translated name is significantly different from the Pinyin (e.g., "Great Monkey King" vs. "Měi Hóuwáng"), use this format: **Translated Name (Chinese Characters Pinyin)**. Example: "Great Monkey King (美猴王 Měi Hóuwáng)".
    * **CASE 2: TRANSLATED NAME IS ESSENTIALLY THE SAME AS PINYIN:** If the translated name is essentially the same as the Pinyin (just anglicized Pinyin, e.g., "Sun Wukong" which is very close to "Sūn Wùkōng"), use this format: **Pinyin (Chinese Characters)**. Example: "Sūn Wùkōng (孫悟空)".  In this case, the Pinyin comes FIRST, followed by parentheses containing ONLY the Chinese characters.

**Constraint:** You MUST TRANSLATE ALL TEXT TO {target_language}, including poems. You MUST NOT italicize Chinese characters or Pinyin. You MUST translate poems or verses and then italicize them if detected. You MUST include Chinese characters for names and general Chinese terms, use Hanyu Pinyin with correct tone marks for names and general Chinese terms, and use the CONDITIONAL formatting for names as described in CASE 1 and CASE 2 above for names, and the general term format `Translated Term (Chinese Characters Pinyin)` for general terms. Do NOT use any other romanization method, do not omit tone marks or Chinese characters for Chinese terms, and adhere to the specified formatting. Provide **ONLY** the final, cleaned, corrected, and translated text in {target_language}, **formatted in Markdown**.  Do **NOT** include the original French text. Do **NOT** include any page numbers. Do **NOT** include any introductory phrases, notes, quotation marks, or anything else.  Just the clean, translated text, perfectly formatted in Markdown and free of errors. Text: {text}"""


TRANSLATE_ONLY_PROMPT_REFINED_V7_COND_FORMAT = """**IMPORTANT: TRANSLATE ALL TEXT to natural and idiomatic {target_language}. DO NOT LEAVE ANY TEXT IN THE ORIGINAL LANGUAGE. TRANSLATE EVERYTHING.**

Translate the following text to natural and idiomatic {target_language}. For Chinese names and general Chinese terms use Hànyǔ Pīnyīn for the term in the translation. Include Chinese character names and general Chinese terms in Chinese in the translation. The goal is to produce a translation that sounds fluent and natural to a native {target_language} speaker, as if written by one. Avoid literal, word-for-word translation. Instead, focus on conveying the meaning accurately using natural {target_language} phrasing, sentence structure, and idiomatic expressions. Rephrase sentences as needed to ensure a smooth and readable flow for a general {target_language} audience. Aim for a slightly informal and approachable tone.  Produce a translation that sounds fluent and natural to a native {target_language} speaker, as if written by one.  Format structural elements using Markdown where appropriate and ensure paragraphs are separated by blank lines.

**IMPORTANT: MANDATORY PINYIN TRANSLITERATION WITH TONE MARKS AND CONDITIONAL FORMATTING FOR CHINESE NAMES AND GENERAL CHINESE TERMS.  CHINESE CHARACTERS MUST BE INCLUDED. DO NOT ITALICIZE CHINESE NAMES OR TERMS.**

* **ITALICS:** **DO NOT ITALICIZE CHINESE NAMES OR GENERAL CHINESE TERMS** in the output, even if they are italicized in the original text. However, if you identify POEMS or VERSES, **FIRST TRANSLATE THEM TO {target_language}**, and then format the **TRANSLATED POEMS/VERSES** in italics in the Markdown output using asterisks `*poem line*`. **ENSURE POEMS ARE TRANSLATED TO {target_language}.**
* **CHINESE CHARACTERS:** You **MUST INCLUDE** the original Chinese characters for all **CHINESE NAMES** in the translation. **FOR GENERAL CHINESE TERMS ORIGINALLY IN CHINESE, INCLUDE CHINESE CHARACTERS IN BRACKETS AFTER THE TRANSLATED TERM.**
* **PINYIN TRANSLITERATION (ALL CHINESE TERMS):** For **ALL CHINESE TERMS** (names and general terms originally in Chinese), you **ABSOLUTELY MUST** use **Hànyǔ Pīnyīn (汉语拼音)** - the standard and ONLY acceptable romanization system for Mandarin Chinese - for the transliterated term. **CRITICALLY IMPORTANT: Ensure Hanyu Pinyin is provided with CORRECT TONE MARKS for all Chinese terms.** **FOR BOTH NAMES AND GENERAL TERMS, INCLUDE HANYU PINYIN IN BRACKETS AFTER THE CHINESE CHARACTERS.** Example format for general terms:  `Translated Term (Chinese Characters Pinyin)`.
* **CONDITIONAL FORMATTING FOR NAMES - IMPORTANT:**
    * **CASE 1: TRANSLATED NAME IS DIFFERENT FROM PINYIN:** If the translated name is significantly different from the Pinyin (e.g., "Great Monkey King" vs. "Měi Hóuwáng"), use this format: **Translated Name (Chinese Characters Pinyin)**. Example: "Great Monkey King (美猴王 Měi Hóuwáng)".
    * **CASE 2: TRANSLATED NAME IS ESSENTIALLY THE SAME AS PINYIN:** If the translated name is essentially the same as the Pinyin (just anglicized Pinyin, e.g., "Sun Wukong" which is very close to "Sūn Wùkōng"), use this format: **Pinyin (Chinese Characters)**. Example: "Sūn Wùkōng (孫悟空)". In this case, the Pinyin comes FIRST, followed by parentheses containing ONLY the Chinese characters.

**Constraint:** You MUST TRANSLATE ALL TEXT TO {target_language}, including poems. You MUST NOT italicize Chinese characters or Pinyin. You MUST translate poems or verses and then italicize them if detected. You MUST include Chinese characters for names and general Chinese terms, use Hanyu Pinyin with correct tone marks for names and general Chinese terms, and use the CONDITIONAL formatting for names as described in CASE 1 and CASE 2 above for names, and the general term format `Translated Term (Chinese Characters Pinyin)` for general terms. Do NOT use any other romanization method, do not omit tone marks or Chinese characters for Chinese terms, and adhere to the specified formatting. Provide **ONLY** the final, translated text in {target_language}, **formatted in Markdown**. Do **NOT** include any introductory phrases, notes, quotation marks, or anything else.  Just the translated text, perfectly formatted in Markdown and free of errors. Text: {text}"""


CLEANUP_PROMPT = """Please clean up the following text which is the result of Optical Character Recognition (OCR).  The text is very messy and contains significant errors, typos, gibberish, and formatting problems typical of OCR output, including **pagination numbers and inconsistent line breaks within paragraphs**.

**Your task is to perform aggressive cleaning and correction to produce a perfectly clean, readable, and well-formatted text using Markdown formatting for structural elements.**

**Specifically, your cleaning, correction, and formatting MUST include:**

* **AGGRESSIVELY correct ALL OCR errors, typos, and gibberish.** This is the most important step. Ensure the text is perfectly readable and grammatically correct in English.
* **REMOVE ALL pagination numbers.**  This includes both Arabic numerals (e.g., 1, 2, 3...) and Roman numerals (e.g., I, II, III, IV, V...). Do not include any page numbers in the cleaned output.
* **AGGRESSIVELY REMOVE **unnecessary line breaks WITHIN paragraphs** to create flowing paragraphs.**  Text within a paragraph should be on a single line unless it's a deliberate line break for formatting within that paragraph (which is unlikely in OCR cleanup).
* **JOIN hyphenated words that are split across lines.** For example, if "state- \n ment" appears, it should be corrected to "statement".
* **COLLAPSE multiple spaces and tabs into single spaces.** Remove leading and trailing whitespace from lines. Ensure consistent spacing throughout the text.
* **Ensure proper paragraphing and line breaks for excellent readability.** Paragraphs should be clearly separated by blank lines in the Markdown output.  **Preserve these paragraph breaks.**
* **Format structural elements using Markdown:** If the original text has structural elements like headings, please format them using Markdown.
    * Use `#` for main headings, `##` for main section headings, and `###` for subsections, etc. Try to infer the hierarchy from the text if possible.
    * Ensure paragraphs are separated by blank lines (standard Markdown).
* **Remove ALL extra whitespace, formatting inconsistencies, and extraneous characters that are artifacts of the OCR process.**

**IMPORTANT:** Provide **ONLY** the final, cleaned and corrected text, **formatted in Markdown**.  Do **NOT** include the original OCR text. Do **NOT** include any page numbers.  Do **NOT** include any introductory phrases, notes, quotation marks, or anything else. Just the clean, corrected text, perfectly formatted in Markdown and free of errors.

**Text to clean:** {text}"""


PROMPTS = {
    "translate": DEFAULT_TRANSLATION_PROMPT_REFINED_V7_COND_FORMAT, # Using V7_COND_FORMAT for translate
    "cleanup": CLEANUP_PROMPT,
    "translate_only": TRANSLATE_ONLY_PROMPT_REFINED_V7_COND_FORMAT, # Using V7_COND_FORMAT for translate_only
}
DEFAULT_PROMPT_KEY = "translate_only" # Changed default prompt to translate_only

PROMPT_SUFFIX_MAP = {
    "translate": "_translated", # Suffix for cleanup+translate remains "_translated" for backward compatibility
    "cleanup": "_cleaned",
    "translate_only": "_only_translated", # Suffix for translate_only is "_only_translated"
}


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
OLLAMA_API_URL = os.environ.get("OLLAMA_API_URL", "http://localhost:11434/api/chat") # Allow Ollama URL to be set via env var
# --- End Configuration ---


def translate_text(text, target_language, engine, model_name, google_api_key, processing_prompt):
    """Translates text using Google Gemini API or Ollama, with rate limiting for Gemini."""
    global last_request_time

    if engine == "google":
        import google.generativeai as genai
        from google.generativeai.types import GenerateContentResponse
        from google.api_core.exceptions import ResourceExhausted

        genai.configure(api_key=google_api_key)
        model = genai.GenerativeModel(model_name)

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

            prompt_content = processing_prompt.format(target_language=target_language, text=text)

            print(f"--- Calling Google Gemini API with model '{model_name}' for processing... Streaming output below: ---")
            response = model.generate_content(prompt_content, stream=True) # Important: stream=True

            processed_text_chunks = []
            for chunk in response: # Iterate through response chunks (parts)
                if chunk.text: # Check if the chunk has text content
                    content_chunk = chunk.text
                    print(content_chunk, end="", flush=True)
                    processed_text_chunks.append(content_chunk)

            print("\n--- Google Gemini API call completed and output streamed. ---")
            processed_text = "".join(processed_text_chunks).strip()
            return processed_text


        except ResourceExhausted as e:
            if e.status_code == 429:
                print(f"Error: Google Gemini API Quota Exhausted (HTTP 429).", file=sys.stderr)
                print(f"Quota Exhaustion details: {e}", file=sys.stderr)
                return None
            else:
                print(f"Error calling Google Gemini API (ResourceExhausted, not quota related): {e}", file=sys.stderr)
                return None

        except Exception as e:
            print(f"Error calling Google Gemini API: {e}", file=sys.stderr)
            return None

    elif engine == "ollama":
        try:
            prompt_content = processing_prompt.format(target_language=target_language, text=text)

            payload = {
                "model": model_name,
                "messages": [{"role": "user", "content": prompt_content}],
                "stream": True
            }
            headers = {'Content-Type': 'application/json'}

            try:
                print(f"--- Calling Ollama API with model '{model_name}' for processing... Streaming output below: ---")
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
            except requests.exceptions.RequestException as e:
                print(f"Error calling Ollama API: {e}", file=sys.stderr)
                if 'response' in locals() and response is not None:
                    print(f"HTTP Status Code: {response.status_code}", file=sys.stderr)
                    print(f"Response Text: {response.text}", file=sys.stderr)
                return None

            try:
                processed_text_chunks = []
                for line in response.iter_lines():
                    if line:
                        try:
                            json_line = json.loads(line)
                            if 'message' in json_line and 'content' in json_line['message']:
                                content_chunk = json_line['message']['content']
                                print(content_chunk, end="", flush=True)
                                processed_text_chunks.append(content_chunk)
                        except json.JSONDecodeError:
                            print(f"Warning: Could not decode JSON line from Ollama stream: {line.decode() if isinstance(line, bytes) else line}", file=sys.stderr)
                            continue
                print("\n--- Ollama API call completed and output streamed. ---")
                processed_text = "".join(processed_text_chunks).strip()
                return processed_text

            except Exception as e:
                print(f"Error processing Ollama API streaming response: {e}", file=sys.stderr)
                return None

        except Exception as e:
            print(f"Unexpected error during Ollama processing: {e}", file=sys.stderr)
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
            return None
    except KeyError:
        return None

def natural_sort_key(s):
    """Generates keys for natural sorting."""
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split(re.compile('([0-9]+)'), s)]

def process_files(args):
    """Processes files for translation or cleanup based on arguments.
       Now processes files regardless of extension."""
    global last_request_time
    last_request_time = None
    quota_exhausted = False

    if not args.files:
        print("Error: No files specified.", file=sys.stderr)
        return 1

    all_files = [] # Initialize as empty list to handle glob correctly
    for file_pattern in args.files: # Iterate through file patterns from args
        resolved_files_for_pattern = glob.glob(file_pattern) # Expand each pattern
        if not resolved_files_for_pattern: # Check if any files found for this pattern
            print(f"Warning: No files found matching pattern: '{file_pattern}'", file=sys.stderr)
        all_files.extend(resolved_files_for_pattern) # Add found files to the list

    if not all_files: # Check if the final list of files is empty after processing all patterns
        print(f"Error: No files found matching any specified pattern(s).", file=sys.stderr)
        return 1


    if args.language and (args.prompt_key == "translate" or args.prompt_key == "translate_only"): # Language is relevant for translation prompts
        target_language_code = args.language.lower()
        target_language = get_language_name_from_code(target_language_code)
        if not target_language:
            print(f"Error: Invalid language code '{args.language}'. Use valid two-digit language code (e.g., en, fr, id).", file=sys.stderr)
            print("       Refer to pycountry documentation for valid language codes.")
            return 1
    elif args.prompt_key == "cleanup": # target_language not needed for cleanup
        target_language = None
        target_language_code = None # Set to None for cleanup
    else:
        target_language = DEFAULT_TARGET_LANGUAGE
        target_language_code = DEFAULT_TARGET_LANGUAGE # Use default lang code if not specified for default translate


    output_dir_base = args.output if args.output else OUTPUT_SUBFOLDER # Base output dir, before language code
    original_files_dir = os.path.join(os.getcwd(), ORIGINAL_FILES_SUBFOLDER)

    # --- Construct output directory name ---
    if target_language_code and (args.prompt_key == "translate" or args.prompt_key == "translate_only"):
        output_dir = os.path.join(os.getcwd(), f"{output_dir_base}_{target_language_code}") # Append language code to output folder
    else:
        output_dir = os.path.join(os.getcwd(), output_dir_base) # Use base output dir for cleanup or no language specified

    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(original_files_dir, exist_ok=True)

    if args.engine == "google":
        default_model = DEFAULT_GEMINI_MODELS[0]
        model_name = args.model if args.model else default_model
    elif args.engine == "ollama":
        default_model = DEFAULT_OLLAMA_MODELS[0]
        model_name = args.model if args.model else default_model
    else:
        model_name = None

    processing_prompt = PROMPTS.get(args.prompt_key)
    if not processing_prompt:
        processing_prompt = PROMPTS[DEFAULT_PROMPT_KEY]

    processing_settings = {
        "Engine": args.engine,
        "Model": model_name,
        "Prompt": args.prompt_key,
        "Output Directory": output_dir,
        "Output File Suffix": args.suffix,
        "Files": args.files
    }
    if args.prompt_key == "translate" or args.prompt_key == "translate_only": # Add target language for translation prompts
        processing_settings["Target Language"] = target_language


    for file_path in all_files:
        print(f"--- Processing file: '{file_path}' ---")
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()

            processed_text = translate_text(
                text,
                target_language,
                args.engine,
                model_name,
                GOOGLE_API_KEY,
                processing_prompt
            )

            if processed_text:
                base_name = os.path.basename(file_path)
                name, ext = os.path.splitext(base_name)

                # --- Construct output filename ---
                if target_language_code and (args.prompt_key == "translate" or args.prompt_key == "translate_only"):
                    output_file_path = os.path.join(output_dir, f"{name}_{target_language_code}{args.suffix}{ext}") # Append lang code to filename
                else:
                    output_file_path = os.path.join(output_dir, f"{name}{args.suffix}{ext}") # No lang code in filename for cleanup

                with open(output_file_path, "w", encoding="utf-8") as outfile:
                    outfile.write(processed_text)
                print(f"\nProcessed '{file_path}' using {args.engine} engine, model '{model_name}', and prompt '{args.prompt_key}' -> '{output_file_path}'")

                try:
                    original_file_name = os.path.basename(file_path)
                    destination_original_file_path = os.path.join(original_files_dir, original_file_name)
                    os.rename(file_path, destination_original_file_path)
                    print(f"Moved original file '{file_path}' to '{destination_original_file_path}'")
                except Exception as move_error:
                    print(f"Error moving original file '{file_path}' to '{original_files_dir}': {move_error}", file=sys.stderr)


            elif processed_text is None and args.engine == "google":
                print(f"Processing failed for '{file_path}' due to Google Gemini Quota Exhaustion. Script will terminate.", file=sys.stderr)
                quota_exhausted = True
                break
            else:
                print(f"Processing failed for '{file_path}'. See error messages above.", file=sys.stderr)

        except FileNotFoundError:
            print(f"Error: File not found: {file_path}", file=sys.stderr)
        except Exception as e:
            print(f"Error processing {file_path}: {e}", file=sys.stderr)
        finally:
            print(f"--- Finished processing file: '{file_path}' ---")

    if quota_exhausted:
        print("\n--- Script terminated early due to Google Gemini Quota Exhaustion. ---", file=sys.stderr)
        return 1

    print("\n--- Processing Settings Used ---")
    for key, value in processing_settings.items():
        print(f"{key}: {value}")
    print("--- End Processing Settings ---")
    return 0


def main():
    """Main function to always launch GUI, optionally pre-filled with command-line files."""
    parser = argparse.ArgumentParser(description="Translate or cleanup text files using Google Gemini or Ollama.")
    parser.add_argument("files", nargs="*", help="Path(s) to the text file(s) to process. Will be pre-filled in GUI.")
    parser.add_argument("-l", "--language", default=None, help="Target language (e.g., en, id, fr). (For translation prompts only)")
    parser.add_argument("-e", "--engine", default=DEFAULT_ENGINE, choices=['google', 'ollama'], help=f"AI engine to use: google or ollama.")
    parser.add_argument("-m", "--model", "--model", dest="model", default=None, help=f"Model to use (engine specific).")
    parser.add_argument("-p", "--prompt", "--prompt", dest="prompt_key", default=DEFAULT_PROMPT_KEY, choices=PROMPTS.keys(), help=f"Prompt to use. Keywords: {', '.join(PROMPTS.keys())}")
    parser.add_argument("-o", "--output", default=None, help="Output directory (overrides '{OUTPUT_SUBFOLDER}').")
    parser.add_argument("-s", "--suffix", dest="suffix", default=DEFAULT_SUFFIX, help=f"Suffix for processed file names.")

    args = parser.parse_args()

    resolved_files = []
    for file_pattern in args.files:
        resolved_files.extend(glob.glob(file_pattern))

    resolved_files.sort(key=natural_sort_key)

    use_gui(resolved_files, args)


def use_gui(command_line_files, args):
    """Launches a tkinter GUI for script options, optionally pre-filled with files.
       Language input now defaults to and expects two-letter language codes (e.g., en, fr)."""


    window = tk.Tk()
    window.title("Text Processing Script GUI")

    files_list_var = tk.Variable(value=command_line_files if command_line_files else [])
    language_var = tk.StringVar(value=args.language if args.language else DEFAULT_TARGET_LANGUAGE) # Default is now DEFAULT_TARGET_LANGUAGE which is "en"
    engine_var = tk.StringVar(value=args.engine if args.engine else DEFAULT_ENGINE)
    model_var = tk.StringVar(value=args.model if args.model else "")

    prompt_options = list(PROMPTS.keys())
    prompt_display_options = ["Cleanup and Translate" if key == "translate" else key.replace("_", " ").title() for key in prompt_options]
    prompt_value_map = {display_option: key for display_option, key in zip(prompt_display_options, prompt_options)}

    # Determine initial prompt display value based on args.prompt_key or DEFAULT_PROMPT_KEY
    initial_prompt_key = args.prompt_key if args.prompt_key else DEFAULT_PROMPT_KEY
    initial_prompt_display_value = ""
    for display_option, key in prompt_value_map.items():
        if key == initial_prompt_key:
            initial_prompt_display_value = display_option
            break
    if not initial_prompt_display_value: # Fallback in case of issue (shouldn't happen with defined PROMPTS)
        initial_prompt_display_value = prompt_display_options[0] if prompt_display_options else ""


    prompt_var = tk.StringVar(value=initial_prompt_display_value) # Set initial value to display name
    prompt_var.set("Translate Only") # Set "translate_only" as default in GUI

    output_dir_var = tk.StringVar(value=args.output if args.output else "")
    suffix_var = tk.StringVar(value=args.suffix if args.suffix else DEFAULT_SUFFIX)

    files_frame = ttk.Frame(window, padding="10 10 10 10")
    files_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    tk.Label(files_frame, text="Files:").grid(row=0, column=0, sticky=tk.NW)

    file_listbox = tk.Listbox(files_frame, listvariable=files_list_var, height=10, width=60, selectmode=tk.EXTENDED)
    file_listbox.grid(row=1, column=0, sticky=(tk.W, tk.E))

    file_buttons_frame = ttk.Frame(files_frame, padding="0 0 0 0")
    file_buttons_frame.grid(row=1, column=1, sticky=(tk.N, tk.S))

    def add_files_to_list():
        selected_files = filedialog.askopenfilenames(filetypes=[("Text files", "*.txt;*.md;*.text;*.rtf"), ("All files", "*.*")]) # Added .md and other plaintext extensions to file dialog
        if selected_files:
            current_files = list(files_list_var.get())
            updated_files = current_files + list(selected_files)
            updated_files.sort(key=natural_sort_key)
            files_list_var.set(tuple(updated_files))

    def remove_selected_files():
        selected_indices = file_listbox.curselection()
        if selected_indices:
            current_files = list(files_list_var.get())
            updated_files = [file for index, file in enumerate(current_files) if index not in selected_indices]
            files_list_var.set(tuple(updated_files))

    def clear_all_files():
        files_list_var.set(())

    def select_all_files():
        file_listbox.select_set(0, tk.END)

    def deselect_all_files():
        file_listbox.selection_clear(0, tk.END)

    def move_file_up():
        selected_indices = file_listbox.curselection()
        if selected_indices:
            current_files = list(files_list_var.get())
            updated_files = list(current_files)
            for index in sorted(selected_indices):
                if index > 0:
                    updated_files[index], updated_files[index-1] = updated_files[index-1], updated_files[index]
            files_list_var.set(tuple(updated_files))
            for index in selected_indices:
                if index > 0:
                    file_listbox.select_set(index - 1)

    def move_file_down():
        selected_indices = file_listbox.curselection()
        if selected_indices:
            current_files = list(files_list_var.get())
            updated_files = list(current_files)
            for index in sorted(selected_indices, reverse=True):
                if index < len(current_files) - 1:
                    updated_files[index], updated_files[index+1] = updated_files[index+1], updated_files[index]
            files_list_var.set(tuple(updated_files))
            for index in selected_indices:
                if index < len(current_files) - 1:
                    file_listbox.select_set(index + 1)

    clear_all_button = tk.Button(file_buttons_frame, text="Clear All", command=clear_all_files, width=10) # Separate button creation
    clear_all_button.grid(row=6, column=0, sticky=tk.W, pady=2) # Separate grid placement
    tk.Button(file_buttons_frame, text="Add File", command=add_files_to_list, width=10).grid(row=0, column=0, sticky=tk.W, pady=2)
    tk.Button(file_buttons_frame, text="Remove File", command=remove_selected_files, width=10).grid(row=1, column=0, sticky=tk.W, pady=2)
    tk.Button(file_buttons_frame, text="Select All", command=select_all_files, width=10).grid(row=2, column=0, sticky=tk.W, pady=2)
    tk.Button(file_buttons_frame, text="Deselect All", command=deselect_all_files, width=10).grid(row=3, column=0, sticky=tk.W, pady=2)
    tk.Button(file_buttons_frame, text="Move Up", command=move_file_up, width=10).grid(row=4, column=0, sticky=tk.W, pady=2)
    tk.Button(file_buttons_frame, text="Move Down", command=move_file_down, width=10).grid(row=5, column=0, sticky=tk.W, pady=2)


    lang_frame = ttk.Frame(window, padding="10 10 10 10")
    lang_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    tk.Label(lang_frame, text="Language Code:").grid(row=0, column=0, sticky=tk.W) # Changed label to "Language Code"
    lang_entry = ttk.Entry(lang_frame, textvariable=language_var, width=30)
    lang_entry.grid(row=0, column=1, sticky=(tk.W, tk.E))
    tk.Label(lang_frame, text="(e.g., en, fr, id, for translation)").grid(row=0, column=2, sticky=tk.W)

    engine_frame = ttk.Frame(window, padding="10 10 10 10")
    engine_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    tk.Label(engine_frame, text="Engine:").grid(row=0, column=0, sticky=tk.W)
    engine_options = ['google', 'ollama']
    engine_combo = ttk.Combobox(engine_frame, textvariable=engine_var, values=engine_options, state="readonly")
    engine_combo.grid(row=0, column=1, sticky=(tk.W, tk.E))

    model_frame = ttk.Frame(window, padding="10 10 10 10")
    model_frame.grid(row=4, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    tk.Label(model_frame, text="Model:").grid(row=0, column=0, sticky=tk.W)
    model_combo = ttk.Combobox(model_frame, textvariable=model_var, values=[], state="readonly")
    model_combo.grid(row=0, column=1, sticky=(tk.W, tk.E))

    def update_model_options(*args):
        selected_engine = engine_var.get()
        if selected_engine == 'google':
            model_combo['values'] = DEFAULT_GEMINI_MODELS
            model_var.set(DEFAULT_GEMINI_MODELS[0] if DEFAULT_GEMINI_MODELS else "")
        elif selected_engine == 'ollama':
            model_combo['values'] = DEFAULT_OLLAMA_MODELS
            model_var.set(DEFAULT_OLLAMA_MODELS[0] if DEFAULT_OLLAMA_MODELS else "")
        else:
            model_combo['values'] = []
            model_var.set("")

    engine_var.trace_add('write', update_model_options)
    update_model_options()

    prompt_frame = ttk.Frame(window, padding="10 10 10 10")
    prompt_frame.grid(row=5, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    tk.Label(prompt_frame, text="Prompt:").grid(row=0, column=0, sticky=tk.W)
    prompt_combo = ttk.Combobox(prompt_frame, textvariable=prompt_var, values=prompt_display_options, state="readonly")
    prompt_combo.grid(row=0, column=1, sticky=(tk.W, tk.E))
    # Need to map display options back to keys for prompt selection
    prompt_value_map = {display_option: key for display_option, key in zip(prompt_display_options, prompt_options)}

    # Initialize suffix AFTER prompt_value_map is created
    def update_suffix_from_prompt(*args):
        selected_prompt_display = prompt_combo.get() # Get display value
        selected_prompt_key = prompt_value_map[selected_prompt_display] # Map back to key
        suffix = PROMPT_SUFFIX_MAP.get(selected_prompt_key, DEFAULT_SUFFIX)
        suffix_var.set(suffix)

    update_suffix_from_prompt() # Initial suffix update - called AFTER prompt_value_map is ready
    prompt_var.trace_add('write', update_suffix_from_prompt)


    output_frame = ttk.Frame(window, padding="10 10 10 10")
    output_frame.grid(row=6, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    tk.Label(output_frame, text="Output Dir:").grid(row=0, column=0, sticky=tk.W)
    output_entry = ttk.Entry(output_frame, textvariable=output_dir_var, width=50)
    output_entry.grid(row=0, column=1, sticky=(tk.W, tk.E))
    tk.Button(output_frame, text="Browse Dir", command=lambda: output_dir_var.set(filedialog.askdirectory())).grid(row=0, column=2, sticky=tk.W)
    tk.Label(output_frame, text="(optional)").grid(row=0, column=3, sticky=tk.W)

    suffix_frame = ttk.Frame(window, padding="10 10 10 10")
    suffix_frame.grid(row=7, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    tk.Label(suffix_frame, text="Suffix:").grid(row=0, column=0, sticky=tk.W)
    suffix_entry = ttk.Entry(suffix_frame, textvariable=suffix_var, state='readonly', width=20)
    suffix_entry.grid(row=0, column=1, sticky=(tk.W, tk.E))

    process_button = ttk.Button(window, text="Process", command=lambda: process_from_gui(window, files_list_var, language_var, engine_var, model_var, prompt_var, output_dir_var, suffix_var, prompt_value_map)) # Pass prompt_value_map
    process_button.grid(row=8, column=0, columnspan=3, pady=20)

    window.update_idletasks()
    file_listbox_height_pixels = file_buttons_frame.winfo_height()
    clear_all_button_height_pixels = clear_all_button.winfo_height()
    max_listbox_height_pixels = clear_all_button_height_pixels
    file_listbox_height_pixels = min(file_listbox_height_pixels, max_listbox_height_pixels)
    char_height = file_listbox.winfo_height() / int(file_listbox.config()['height'][0]) if isinstance(file_listbox.config()['height'], tuple) and file_listbox.config()['height'] and file_listbox.config()['height'][0].isdigit() else (file_listbox.winfo_height() / int(file_listbox.config()['height']) if isinstance(file_listbox.config()['height'], str) and file_listbox.config()['height'].isdigit() else 1)
    file_listbox_height_lines = max(3, int((file_listbox_height_pixels / char_height) / 2 ))
    file_listbox.config(height=file_listbox_height_lines)

    window.mainloop()


def process_from_gui(window, files_list_var, language_var, engine_var, model_var, prompt_var, output_dir_var, suffix_var, prompt_value_map): # Accept prompt_value_map as argument
    """Processes files based on GUI input and closes GUI."""
    files_input = files_list_var.get()
    if not files_input:
        tk.messagebox.showerror("Error", "Please select at least one file.")
        return

    class GUIArgs:
        pass
    gui_args = GUIArgs()
    gui_args.files = list(files_input)
    gui_args.language = language_var.get()
    gui_args.engine = engine_var.get()
    gui_args.model = model_var.get()
    gui_args.prompt_key = prompt_value_map[prompt_var.get()]
    gui_args.output = output_dir_var.get() if output_dir_var.get() else None
    gui_args.suffix = suffix_var.get()

    window.destroy()
    sys.exit(process_files(gui_args))


if __name__ == "__main__":
    main()