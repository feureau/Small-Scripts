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
from tkinter import ttk, filedialog, messagebox
from collections import deque  # For storing previous lines - for SRT context
import datetime  # For timestamp in logs

# --- Configuration ---
DEFAULT_TARGET_LANGUAGE = "en"  # Two-letter code default
# We rely solely on dynamic model loading – start with empty lists.
DEFAULT_GEMINI_MODELS = []
DEFAULT_OLLAMA_MODELS = []
DEFAULT_ENGINE = "google"
DEFAULT_SUFFIX = "_processed"
OUTPUT_SUBFOLDER = "processed_output"
ORIGINAL_FILES_SUBFOLDER = "original_files"
CONTEXT_LINES = 5   # Number of previous lines for SRT context
MAX_RETRIES = 3     # Max retries for API calls
LOG_SUBFOLDER = "log" # Subfolder for log files

# --- Prompts ---
# These prompts are used for normal (non-SRT) translations with Markdown formatting.

# Base prompts without Chinese-specific instructions
BASE_TRANSLATION_PROMPT_REFINED_V7 = """**IMPORTANT: TRANSLATE ALL TEXT to natural and idiomatic {target_language}. DO NOT LEAVE ANY TEXT IN THE ORIGINAL LANGUAGE. TRANSLATE EVERYTHING.**

Translate the following text to natural and idiomatic {target_language}. The goal is to produce a translation that sounds fluent and natural to a native {target_language} speaker, as if written by one. Avoid literal, word-for-word translation. Instead, focus on conveying the meaning accurately using natural phrasing, sentence structure, and idiomatic expressions. Rephrase sentences as needed. This text is from OCR and is **VERY MESSY**. You **MUST** perform aggressive cleaning and correction during translation to produce a perfectly clean, readable, and well-formatted Markdown output.

**Specifically:**
* Correct all OCR errors, typos, and gibberish.
* Remove all page numbers.
* Ensure proper paragraphing and line breaks.
* Format structural elements using Markdown (e.g. `#`, `##`, `###`).
* Remove extraneous whitespace and artifacts.

**Constraint:** Provide ONLY the final cleaned, corrected, and translated text in {target_language} formatted in Markdown.
Text: {text}"""

BASE_TRANSLATION_PROMPT_REFINED_V7_COND_FORMAT = """**IMPORTANT: TRANSLATE ALL TEXT to natural and idiomatic {target_language}. DO NOT LEAVE ANY TEXT IN THE ORIGINAL LANGUAGE. TRANSLATE EVERYTHING.**

Translate the following text to natural and idiomatic {target_language}. The goal is to produce a translation that sounds fluent and natural to a native {target_language} speaker, as if written by one. Avoid literal, word-for-word translation. Instead, focus on conveying the meaning accurately using natural {target_language} phrasing, sentence structure, and idiomatic expressions. Rephrase sentences as needed to ensure a smooth and readable flow for a general {target_language} audience. Aim for a slightly informal and approachable tone. This text is from OCR and is **VERY MESSY**. It contains significant errors, typos, gibberish, and formatting problems, including leftover page numbers (like Roman numerals 'IV' or Arabic numerals '123').  You **MUST** perform aggressive cleaning and correction during translation to produce a perfectly clean, readable, and well-formatted translation **using Markdown formatting for structural elements**.

**Specifically, your cleaning, correction, and formatting MUST include:**

* **AGGRESSIVELY correct ALL OCR errors, typos, and gibberish.**  This is the most important step.  Ensure the translated text is free of any OCR artifacts and makes perfect sense.
* **REMOVE ALL page numbers**, whether they are Roman numerals (e.g., I, II, III, IV, V...) or Arabic numerals (e.g., 1, 2, 3...). Do not include any page numbers in the translated output.
* **Ensure proper paragraphing and line breaks for excellent readability.** Paragraphs should be clearly separated by blank lines in the Markdown output.
* **(NEW) Format structural elements using Markdown:** If the original text has structural elements like chapter headings, section headings, etc., please format them using Markdown.
    * Use `#` for chapter headings, `##` for main section headings, and `###` for subsections, etc.  Try to infer the hierarchy from the text if possible, or use `#` for the most prominent headings and `##` for subsequent ones if hierarchy is unclear.
    * Ensure paragraphs are separated by blank lines (standard Markdown).
* **Remove ALL extra whitespace, formatting inconsistencies, and extraneous characters that are artifacts of the OCR process.**

**ITALICS:** **DO NOT ITALICIZE CHINESE NAMES OR GENERAL CHINESE TERMS** in the output, even if they are italicized in the original text. However, if you identify POEMS or VERSES, **FIRST TRANSLATE THEM TO {target_language}**, and then format the **TRANSLATED POEMS/VERSES** in italics in the Markdown output using asterisks `*poem line*`. **ENSURE POEMS ARE TRANSLATED TO {target_language}.**

**Constraint:** You MUST TRANSLATE ALL TEXT TO {target_language}, including poems. You MUST NOT italicize Chinese characters or Pinyin. You MUST translate poems or verses and then italicize them if detected. Provide **ONLY** the final, cleaned, corrected, and translated text in {target_language}, **formatted in Markdown**.  Do **NOT** include the original French text. Do **NOT** include any page numbers. Do **NOT** include any introductory phrases, notes, quotation marks, or anything else.  Just the clean, translated text, perfectly formatted in Markdown and free of errors. Text: {text}"""


BASE_TRANSLATE_ONLY_PROMPT_REFINED_V7 = """**IMPORTANT: TRANSLATE ALL TEXT to natural and idiomatic {target_language}.**

Translate the following text to natural and idiomatic {target_language}. Produce a translation that sounds fluent and natural to a native speaker, formatted in Markdown.
Text: {text}"""

BASE_TRANSLATE_ONLY_PROMPT_REFINED_V7_COND_FORMAT = """**IMPORTANT: TRANSLATE ALL TEXT to natural and idiomatic {target_language}. DO NOT LEAVE ANY TEXT IN THE ORIGINAL LANGUAGE. TRANSLATE EVERYTHING.**

Translate the following text to natural and idiomatic {target_language} and output only the final translation. For Chinese names and terms use Hànyǔ Pīnyīn for the term in the translation. Include Chinese character names and general Chinese terms in Chinese in the translation. The goal is to produce a translation that sounds fluent and natural to a native {target_language} speaker, as if written by one. Avoid literal, word-for-word translation. Instead, focus on conveying the meaning accurately using natural {target_language} phrasing, sentence structure, and idiomatic expressions. Rephrase sentences as needed to ensure a smooth and readable flow for a general {target_language} audience. Aim for a slightly informal and approachable tone.  Produce a translation that sounds fluent and natural to a native {target_language} speaker, as if written by one.  Format structural elements using Markdown where appropriate and ensure paragraphs are separated by blank lines.

**ITALICS:** **DO NOT ITALICIZE CHINESE NAMES OR GENERAL CHINESE TERMS** in the output, even if they are italicized in the original text. However, if you identify POEMS or VERSES, **FIRST TRANSLATE THEM TO {target_language}**, and then format the **TRANSLATED POEMS/VERSES** in italics in the Markdown output using asterisks `*poem line*`. **ENSURE POEMS ARE TRANSLATED TO {target_language}.**

**Constraint:** You MUST TRANSLATE ALL TEXT TO {target_language}, including poems. You MUST NOT italicize Chinese characters or Pinyin. You MUST translate poems or verses and then italicize them if detected. Provide **ONLY** the final translated text in {target_language}, **formatted in Markdown**.  Do **NOT** include any introductory phrases, notes, quotation marks, or anything else.  Just the translated text, perfectly formatted in Markdown and free of errors. Text: {text}"""

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

SRT_WHOLE_FILE_PROMPT = """TRANSLATE THE ENTIRE FOLLOWING SRT SUBTITLE FILE to {target_language}.
**IMPORTANT: PRESERVE THE EXACT SRT FORMAT WITHOUT ADDING CODE FENCES.**
1. Keep all subtitle numbers exactly as they are.
2. Keep all timestamps intact.
3. Translate only the subtitle text between the timestamps.
4. Do not add any markdown code fences (e.g., no ```).
Output the translation as plain text.
Text: {text}"""

PROMPTS = {
    "translate": BASE_TRANSLATION_PROMPT_REFINED_V7,
    "translate_pinyin": BASE_TRANSLATION_PROMPT_REFINED_V7_COND_FORMAT, # Now base, will be dynamically modified
    "cleanup": CLEANUP_PROMPT,
    "translate_only": BASE_TRANSLATE_ONLY_PROMPT_REFINED_V7,
    "translate_only_pinyin": BASE_TRANSLATE_ONLY_PROMPT_REFINED_V7_COND_FORMAT, # Now base, will be dynamically modified
    "srt_translate_whole_file": SRT_WHOLE_FILE_PROMPT
}
DEFAULT_PROMPT_KEY = "translate_only"

PROMPT_SUFFIX_MAP = {
    "translate": "_translated",
    "translate_pinyin": "_translated_pinyin",
    "cleanup": "_cleaned",
    "translate_only": "_only_translated",
    "translate_only_pinyin": "_only_translated_pinyin",
    "srt_translate_whole_file": "_translated_whole_file"
}

CHINESE_INSTRUCTIONS_CHARACTERS = """
**CHINESE CHARACTERS:**  You **MUST INCLUDE** the original Chinese characters for all **CHINESE NAMES** in the translation. **FOR GENERAL CHINESE TERMS ORIGINALLY IN CHINESE, INCLUDE CHINESE CHARACTERS IN BRACKETS AFTER THE TRANSLATED TERM.**
"""

CHINESE_INSTRUCTIONS_PINYIN = """
**PINYIN TRANSLITERATION (ALL CHINESE TERMS):** For **ALL CHINESE TERMS** (names and general terms originally in Chinese), you **ABSOLUTELY MUST** use **Hànyǔ Pīnyīn (汉语拼音)** - the standard and ONLY acceptable romanization system for Mandarin Chinese - for the transliterated term. **CRITICALLY IMPORTANT: Ensure Hanyu Pinyin is provided with CORRECT TONE MARKS for all Chinese terms.** **FOR BOTH NAMES AND GENERAL TERMS, INCLUDE HANYU PINYIN IN BRACKETS AFTER THE CHINESE CHARACTERS.** Example format for general terms:  `Translated Term (Chinese Characters Pinyin)`.
"""

CHINESE_INSTRUCTIONS_CONDITIONAL_FORMATTING = """
**CONDITIONAL FORMATTING FOR NAMES - IMPORTANT:**
    * **CASE 1: TRANSLATED NAME IS DIFFERENT FROM PINYIN:** If the translated name is significantly different from the Pinyin (e.g., "Great Monkey King" vs. "Měi Hóuwáng"), use this format: **Translated Name (Chinese Characters Pinyin)**. Example: "Great Monkey King (美猴王 Měi Hóuwáng)".
    * **CASE 2: TRANSLATED NAME IS ESSENTIALLY THE SAME AS PINYIN:** If the translated name is essentially the same as the Pinyin (just anglicized Pinyin, e.g., "Sun Wukong" which is very close to "Sūn Wùkōng"), use this format: **Pinyin (Chinese Characters)**. Example: "Sūn Wùkōng (孫悟空)".  In this case, the Pinyin comes FIRST, followed by parentheses containing ONLY the Chinese characters.
"""

# Google GenAI API Key
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    GOOGLE_API_KEY = "YOUR_GOOGLE_API_KEY_HERE"
    print("Warning: GOOGLE_API_KEY environment variable not set...")

# Rate Limiting for Google GenAI
REQUESTS_PER_MINUTE = 15
REQUEST_INTERVAL_SECONDS = 60 / REQUESTS_PER_MINUTE
last_request_time = None

# Ollama API Configuration
# For chat functions we use /api/chat; for model listing we now use the local endpoint /api/tags.
OLLAMA_API_URL = os.environ.get("OLLAMA_API_URL", "http://localhost:11434/api/chat")
def get_ollama_tags_url():
    if "/api/chat" in OLLAMA_API_URL:
        return OLLAMA_API_URL.replace("/api/chat", "/api/tags")
    else:
        return OLLAMA_API_URL.rstrip("/") + "/api/tags"

# --- Dynamic Model Listing Functions ---
def get_google_models(api_key):
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        models_iterable = client.models.list()  # List available models using the new SDK
        models = [model.name for model in models_iterable]
        return models
    except Exception as e:
        print(f"Error retrieving Google models: {e}", file=sys.stderr)
        return []

def get_ollama_models():
    try:
        url = get_ollama_tags_url()
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        # Expecting a JSON object with a "models" key containing model objects.
        models = [model["name"] for model in data.get("models", [])]
        return models
    except Exception as e:
        print(f"Error retrieving Ollama models: {e}", file=sys.stderr)
        return []
# --- End Dynamic Model Listing ---

def insert_custom_prompt(original_prompt, custom_prompt):
    """Inserts the custom prompt after the first line of the original prompt."""
    lines = original_prompt.splitlines(keepends=True)
    if len(lines) > 1:
        lines.insert(1, custom_prompt.strip() + "\n\n")
    elif lines:
        lines.append("\n\n" + custom_prompt.strip() + "\n")
    else:
        lines.insert(0, custom_prompt.strip() + "\n\n")
    return "".join(lines)

def remove_markdown_code_fences(text):
    """Removes markdown code fences (triple backticks) from the text."""
    return re.sub(r"```", "", text)

def translate_srt_whole_file(input_file, output_file, target_language, engine, model_name, google_api_key, processing_prompt, stream_output=False):
    """Translates an SRT file by sending its entire content in one call."""
    try:
        with open(input_file, "r", encoding="utf-8-sig") as infile:
            srt_content = infile.read()
        translated_content = translate_text(
            text=srt_content,
            target_language=target_language,
            engine=engine,
            model_name=model_name,
            google_api_key=google_api_key,
            processing_prompt=processing_prompt,
            stream_output=stream_output
        )
        if translated_content:
            try:
                with open(output_file, "w", encoding="utf-8") as outfile:
                    outfile.write(translated_content)
                return True
            except Exception as e:
                print(f"Error writing translated SRT: {e}", file=sys.stderr)
                return False
        else:
            return False
    except Exception as e:
        print(f"Error reading SRT file: {e}", file=sys.stderr)
        return False

def translate_text(text, target_language, engine, model_name, google_api_key, processing_prompt, stream_output=False, prev_context=None):
    """Translates text using Google GenAI or Ollama, with rate limiting for Google."""
    global last_request_time
    if engine == "google":
        from google import genai
        client = genai.Client(api_key=google_api_key)
        try:
            current_time = time.time()
            if last_request_time is not None:
                time_since_last_request = current_time - last_request_time
                if time_since_last_request < REQUEST_INTERVAL_SECONDS:
                    sleep_duration = REQUEST_INTERVAL_SECONDS - time_since_last_request
                    print(f"Rate limit active (Google GenAI). Sleeping for {sleep_duration:.2f} seconds...")
                    time.sleep(sleep_duration)
            last_request_time = time.time()
            prompt_content = processing_prompt.format(target_language=target_language, text=text)
            if stream_output:
                print(f"--- Calling Google GenAI API with model '{model_name}' for processing (streaming) ---")
                response = client.models.generate_content_stream(model=model_name, contents=prompt_content)
                processed_text_chunks = []
                for chunk in response:
                    if chunk.text:
                        print(chunk.text, end="", flush=True)
                        processed_text_chunks.append(chunk.text)
                print("\n--- Google GenAI API streaming completed. ---")
                return "".join(processed_text_chunks).strip()
            else:
                print(f"--- Calling Google GenAI API with model '{model_name}' for processing (non-streaming) ---")
                response = client.models.generate_content(model=model_name, contents=prompt_content)
                print("\n--- Google GenAI API call completed. ---")
                return response.text
        except Exception as e:
            if "quota" in str(e).lower():
                print(f"Error: Google GenAI API Quota Exhausted. {e}", file=sys.stderr)
                return None
            else:
                print(f"Error calling Google GenAI API: {e}", file=sys.stderr)
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
                print(f"--- Calling Ollama API with model '{model_name}' for processing (streaming) ---")
                response = requests.post(OLLAMA_API_URL, headers=headers, data=json.dumps(payload), stream=True)
                response.raise_for_status()
            except requests.exceptions.ConnectionError as e:
                print(f"Error: Could not connect to Ollama API at {OLLAMA_API_URL}. {e}", file=sys.stderr)
                return None
            except requests.exceptions.Timeout as e:
                print(f"Error: Timeout connecting to Ollama API at {OLLAMA_API_URL}. {e}", file=sys.stderr)
                return None
            except requests.exceptions.RequestException as e:
                print(f"Error calling Ollama API: {e}", file=sys.stderr)
                return None
            processed_text_chunks = []
            for line in response.iter_lines():
                if line:
                    try:
                        json_line = json.loads(line)
                        if 'message' in json_line and 'content' in json_line['message']:
                            processed_text_chunks.append(json_line['message']['content'])
                            print(json_line['message']['content'], end="", flush=True)
                    except json.JSONDecodeError:
                        print(f"Warning: Could not decode JSON line.", file=sys.stderr)
                        continue
            print("\n--- Ollama API streaming completed. ---")
            return "".join(processed_text_chunks).strip()
        except Exception as e:
            print(f"Unexpected error during Ollama processing: {e}", file=sys.stderr)
            return None
    else:
        print(f"Error: Invalid engine '{engine}'. Choose 'google' or 'ollama'.", file=sys.stderr)
        return None

def get_language_name_from_code(language_code):
    """Gets the full language name from a two-letter language code using pycountry."""
    try:
        lang = pycountry.languages.get(alpha_2=language_code)
        return lang.name if lang else None
    except KeyError:
        return None

def natural_sort_key(s):
    """Generates keys for natural sorting."""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(re.compile('([0-9]+)'), s)]

def log_processing(log_dir, file_path, timestamp, settings, full_prompt):
    """Generates a log file with processing details."""
    os.makedirs(log_dir, exist_ok=True)
    log_file_path = os.path.join(log_dir, f"{os.path.basename(file_path)}_{timestamp.strftime('%Y%m%d_%H%M%S')}.log")
    with open(log_file_path, "w", encoding="utf-8") as logfile:
        logfile.write(f"Timestamp: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n")
        logfile.write("\n--- Processing Settings ---\n")
        for key, value in settings.items():
            logfile.write(f"{key}: {value}\n")
        logfile.write("\n--- Full Prompt (Expanded) ---\n")
        logfile.write(full_prompt)
    print(f"Log file saved to: {log_file_path}")

def process_files(args, stream_output, custom_prompt_text="", enable_chinese_chars=False, enable_pinyin=False):
    """Processes files for translation or cleanup based on arguments."""
    global last_request_time
    last_request_time = None
    quota_exhausted = False
    exit_code = 0

    if not args.files:
        print("Error: No files specified.", file=sys.stderr)
        return 1

    all_files = []
    for file_pattern in args.files:
        files_found = glob.glob(file_pattern)
        if not files_found:
            print(f"Warning: No files found matching pattern: '{file_pattern}'", file=sys.stderr)
        all_files.extend(files_found)

    if not all_files:
        print("Error: No files found matching any specified pattern(s).", file=sys.stderr)
        return 1

    if args.language and args.prompt_key in ["translate", "translate_only", "srt_translate_whole_file"]:
        target_language_code = args.language.lower()
        target_language = get_language_name_from_code(target_language_code)
        if not target_language:
            print(f"Error: Invalid language code '{args.language}'.", file=sys.stderr)
            return 1
    elif args.prompt_key == "cleanup":
        target_language = None
        target_language_code = None
    else:
        target_language = DEFAULT_TARGET_LANGUAGE
        target_language_code = DEFAULT_TARGET_LANGUAGE

    output_dir_base = args.output if args.output else OUTPUT_SUBFOLDER
    original_files_dir = os.path.join(os.getcwd(), ORIGINAL_FILES_SUBFOLDER)
    log_dir = os.path.join(os.getcwd(), LOG_SUBFOLDER) # Log directory
    if target_language_code and args.prompt_key in ["translate", "translate_only", "srt_translate_whole_file"]:
        output_dir = os.path.join(os.getcwd(), f"{output_dir_base}_{target_language_code}")
    else:
        output_dir = os.path.join(os.getcwd(), output_dir_base)

    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(original_files_dir, exist_ok=True)
    os.makedirs(log_dir, exist_ok=True) # Ensure log directory exists

    # Capture engine and model settings before loop
    engine_type = args.engine
    if engine_type == "google":
        updated_models = get_google_models(GOOGLE_API_KEY)
        global DEFAULT_GEMINI_MODELS
        DEFAULT_GEMINI_MODELS = updated_models
        model_name = args.model if args.model else (DEFAULT_GEMINI_MODELS[0] if DEFAULT_GEMINI_MODELS else "")
    elif engine_type == "ollama":
        updated_models = get_ollama_models()
        global DEFAULT_OLLAMA_MODELS
        DEFAULT_OLLAMA_MODELS = updated_models
        model_name = args.model if args.model else (DEFAULT_OLLAMA_MODELS[0] if DEFAULT_OLLAMA_MODELS else "")
    else:
        model_name = ""

    try: # Wrap file processing in try/except for KeyboardInterrupt
        for file_path in all_files:
            print(f"--- Processing file: '{file_path}' ---")
            timestamp = datetime.datetime.now() # Timestamp for log

            processing_prompt_base = PROMPTS.get(args.prompt_key) or PROMPTS[DEFAULT_PROMPT_KEY]
            if args.prompt_key in ["translate_pinyin", "translate_only_pinyin"]:
                processing_prompt_base = PROMPTS.get(args.prompt_key) # Use base prompt, then add instructions

            # Dynamically add Chinese instructions
            processing_prompt = processing_prompt_base
            if args.prompt_key in ["translate_pinyin", "translate_only_pinyin"]:
                if enable_chinese_chars:
                    processing_prompt = insert_custom_prompt(processing_prompt, CHINESE_INSTRUCTIONS_CHARACTERS)
                if enable_pinyin:
                    processing_prompt = insert_custom_prompt(processing_prompt, CHINESE_INSTRUCTIONS_PINYIN)
                    processing_prompt = insert_custom_prompt(processing_prompt, CHINESE_INSTRUCTIONS_CONDITIONAL_FORMATTING)

            processing_prompt = insert_custom_prompt(processing_prompt, custom_prompt_text) if custom_prompt_text else processing_prompt # Custom prompt last

            processing_settings = {
                "Engine": engine_type, # Use captured engine_type
                "Model": model_name, # Use captured model_name
                "Prompt": args.prompt_key,
                "Output Directory": output_dir,
                "Output File Suffix": args.suffix,
                "Files": args.files,
                "Stream Output": stream_output,
                "Custom Prompt": custom_prompt_text if custom_prompt_text else "None",
                "Include Chinese Characters": enable_chinese_chars,
                "Enable Chinese Pinyin": enable_pinyin
            }
            if args.prompt_key in ["translate", "translate_only", "srt_translate_whole_file"]:
                processing_settings["Target Language"] = target_language

            # Expand prompt placeholders for logging
            expanded_prompt = processing_prompt.format(target_language=target_language, text="{text}") # Text placeholder for log
            log_processing(log_dir, file_path, timestamp, processing_settings, expanded_prompt) # Log before API call

            try:
                if file_path.lower().endswith('.srt'):
                    base_name = os.path.basename(file_path)
                    name, ext = os.path.splitext(base_name)
                    output_file_path = os.path.join(output_dir, f"{name}_{target_language_code}{args.suffix}{ext}")
                    success = translate_srt_whole_file(
                        input_file=file_path,
                        output_file=output_file_path,
                        target_language=target_language,
                        engine=engine_type, # Use captured engine_type
                        model_name=model_name, # Use captured model_name
                        google_api_key=GOOGLE_API_KEY,
                        processing_prompt=processing_prompt.format(target_language=target_language, text="{text}"), # Full prompt for processing
                        stream_output=stream_output
                    )
                    if success:
                        print(f"Translated SRT '{file_path}' -> '{output_file_path}' using prompt '{args.prompt_key}' (whole-file)")
                        try:
                            shutil.move(file_path, os.path.join(original_files_dir, base_name))
                        except Exception as e:
                            print(f"Error moving original SRT: {e}", file=sys.stderr)
                    else:
                        print(f"Failed to translate SRT file: {file_path}", file=sys.stderr)
                    continue

                with open(file_path, "r", encoding="utf-8") as f:
                    text = f.read()

                processing_text = translate_text(
                    text,
                    target_language,
                    engine_type, # Use captured engine_type
                    model_name, # Use captured model_name
                    GOOGLE_API_KEY,
                    processing_prompt.format(target_language=target_language, text="{text}"), # Full prompt for processing
                    stream_output
                )

                if processing_text:
                    processing_text_no_fence = remove_markdown_code_fences(processing_text) # Remove code fences
                    base_name = os.path.basename(file_path)
                    name, ext = os.path.splitext(base_name)
                    output_file_path = os.path.join(output_dir, f"{name}_{target_language_code}{args.suffix}{ext}") if target_language_code and args.prompt_key in ["translate", "translate_only", "srt_translate_whole_file"] else os.path.join(output_dir, f"{name}{args.suffix}{ext}")
                    with open(output_file_path, "w", encoding="utf-8") as outfile:
                        outfile.write(processing_text_no_fence) # Write fence-less text
                    print(f"\nProcessed '{file_path}' using {engine_type} engine, model '{model_name}', prompt '{args.prompt_key}' and Pinyin {'enabled' if enable_pinyin else 'disabled'} -> '{output_file_path}'")
                    try:
                        destination_original_file_path = os.path.join(original_files_dir, os.path.basename(file_path))
                        os.rename(file_path, destination_original_file_path)
                        print(f"Moved original file '{file_path}' to '{destination_original_file_path}'")
                    except Exception as move_error:
                        print(f"Error moving original file '{file_path}': {move_error}", file=sys.stderr)
                elif processing_text is None and args.engine == "google":
                    print(f"Processing failed for '{file_path}' due to Google GenAI Quota Exhaustion. Script will terminate.", file=sys.stderr)
                    quota_exhausted = True
                    exit_code = 1
                    break
                else:
                    print(f"Processing failed for '{file_path}'. See error messages above.", file=sys.stderr)
            except FileNotFoundError:
                print(f"Error: File not found: {file_path}", file=sys.stderr)
            except Exception as e:
                print(f"Error processing {file_path}: {type(e)} - {e}", file=sys.stderr)
            finally:
                print(f"--- Finished processing file: '{file_path}' ---")

    except KeyboardInterrupt:
        print("\n--- Processing interrupted by user (Ctrl+C). Exiting gracefully. ---")
        return 0 # Graceful exit

    if quota_exhausted:
        print("\n--- Script terminated early due to Google GenAI Quota Exhaustion. ---", file=sys.stderr)
        return exit_code

    print("\n--- Processing Settings Used ---")
    for key, value in processing_settings.items():
        print(f"{key}: {value}")
    print("--- End Processing Settings ---")
    return exit_code

def main():
    parser = argparse.ArgumentParser(description="Translate or cleanup text files using Google GenAI or Ollama.")
    parser.add_argument("files", nargs="*", help="Path(s) to the text file(s) to process. Will be pre-filled in GUI.")
    parser.add_argument("-l", "--language", default=None, help="Target language (e.g., en, id, fr).")
    parser.add_argument("-e", "--engine", default=DEFAULT_ENGINE, choices=['google', 'ollama'], help="AI engine to use: google or ollama.")
    parser.add_argument("-m", "--model", dest="model", default=None, help="Model to use (engine specific).")
    parser.add_argument("-p", "--prompt", dest="prompt_key", default=DEFAULT_PROMPT_KEY, choices=PROMPTS.keys(), help=f"Prompt to use. Options: {', '.join(PROMPTS.keys())}")
    parser.add_argument("-o", "--output", default=None, help="Output directory (overrides default).")
    parser.add_argument("-s", "--suffix", dest="suffix", default=DEFAULT_SUFFIX, help="Suffix for processed file names.")
    parser.add_argument("--no-stream", dest="stream_output_cli", action='store_false', default=False, help="Disable streaming output for Google GenAI (CLI only).")
    parser.add_argument("--pinyin", dest="enable_pinyin_cli", action='store_true', default=False, help="Enable Chinese Pinyin transliteration (CLI only, for translate prompts).")
    parser.add_argument("--chinese-chars", dest="enable_chinese_chars_cli", action='store_true', default=False, help="Include Chinese characters in output (CLI only, for translate prompts).")
    parser.set_defaults(stream_output_cli=False)
    parser.set_defaults(enable_pinyin_cli=False)
    parser.set_defaults(enable_chinese_chars_cli=False)
    args = parser.parse_args()

    # Dynamically update model lists for both engines at launch
    global DEFAULT_GEMINI_MODELS, DEFAULT_OLLAMA_MODELS
    DEFAULT_GEMINI_MODELS = get_google_models(GOOGLE_API_KEY)
    DEFAULT_OLLAMA_MODELS = get_ollama_models()

    resolved_files = []
    for file_pattern in args.files:
        resolved_files.extend(glob.glob(file_pattern))
    resolved_files.sort(key=natural_sort_key)

    gui_exit_code = use_gui(resolved_files, args)
    if gui_exit_code is not None:
        sys.exit(gui_exit_code)
    else:
        sys.exit(process_files(args, args.stream_output_cli, enable_chinese_chars=args.enable_chinese_chars_cli, enable_pinyin=args.enable_pinyin_cli))

def use_gui(command_line_files, args):
    window = tk.Tk()
    window.title("Text Processing Script GUI")
    exit_code_from_gui = None

    files_list_var = tk.Variable(value=command_line_files if command_line_files else [])
    language_var = tk.StringVar(value=args.language if args.language else DEFAULT_TARGET_LANGUAGE)
    engine_var = tk.StringVar(value=args.engine if args.engine else DEFAULT_ENGINE)
    model_var = tk.StringVar(value=args.model if args.model else "")

    prompt_options = [key for key in PROMPTS.keys() if key not in ["translate_pinyin", "translate_only_pinyin"]]
    prompt_display_options = [
        "Cleanup and Translate" if key == "translate" else
        "Cleanup" if key == "cleanup" else
        "Translate Only" if key == "translate_only" else
        "SRT Translate (Whole File)" if key == "srt_translate_whole_file" else
        key.replace("_", " ").title()
        for key in prompt_options
    ]
    prompt_value_map = dict(zip(prompt_display_options, prompt_options))

    initial_prompt_key = args.prompt_key if args.prompt_key else DEFAULT_PROMPT_KEY
    initial_prompt_display_value = None
    for disp, key in prompt_value_map.items():
        if key == initial_prompt_key:
            initial_prompt_display_value = disp
            break
    if not initial_prompt_display_value:
        initial_prompt_display_value = prompt_display_options[0] if prompt_display_options else ""

    prompt_var = tk.StringVar(value=initial_prompt_display_value)
    output_dir_var = tk.StringVar(value=args.output if args.output else "")
    suffix_var = tk.StringVar(value=args.suffix if args.suffix else DEFAULT_SUFFIX)
    stream_output_var = tk.BooleanVar(value=False)
    enable_pinyin_var = tk.BooleanVar(value=False)
    enable_chinese_chars_var = tk.BooleanVar(value=False) # New checkbox

    # --- GUI Layout and Grouping ---
    main_frame = ttk.Frame(window, padding="10 10 10 10")
    main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

    # File Management Group
    files_group_frame = ttk.LabelFrame(main_frame, text="File Management", padding="10 10 10 10")
    files_group_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

    files_frame = ttk.Frame(files_group_frame, padding="0 0 0 0") # No padding inside files_frame
    files_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    tk.Label(files_frame, text="Files:").grid(row=0, column=0, sticky=tk.NW)
    file_listbox = tk.Listbox(files_frame, listvariable=files_list_var, height=10, width=60, selectmode=tk.EXTENDED)
    file_listbox.grid(row=1, column=0, sticky=(tk.W, tk.E))

    file_buttons_frame = ttk.Frame(files_group_frame, padding="0 0 0 0") # No padding inside file_buttons_frame
    file_buttons_frame.grid(row=0, column=1, sticky=(tk.N, tk.S))

    def add_files_to_list():
        selected_files = filedialog.askopenfilenames(filetypes=[("Text files", "*.txt;*.md;*.text;*.rtf;*.srt"), ("All files", "*.*")])
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

    add_file_button = tk.Button(file_buttons_frame, text="Add File(s)", command=add_files_to_list, width=10)
    remove_file_button = tk.Button(file_buttons_frame, text="Remove File(s)", command=remove_selected_files, width=10)
    clear_all_button = tk.Button(file_buttons_frame, text="Clear All", command=clear_all_files, width=10)
    select_all_button = tk.Button(file_buttons_frame, text="Select All", command=select_all_files, width=10)
    deselect_all_button = tk.Button(file_buttons_frame, text="Deselect All", command=deselect_all_files, width=10)
    move_up_button = tk.Button(file_buttons_frame, text="Move Up", command=move_file_up, width=10)
    move_down_button = tk.Button(file_buttons_frame, text="Move Down", command=move_file_down, width=10)

    add_file_button.grid(row=0, column=0, sticky=tk.W, pady=2)
    remove_file_button.grid(row=1, column=0, sticky=tk.W, pady=2)
    clear_all_button.grid(row=2, column=0, sticky=tk.W, pady=2)
    select_all_button.grid(row=3, column=0, sticky=tk.W, pady=2)
    deselect_all_button.grid(row=4, column=0, sticky=tk.W, pady=2)
    move_up_button.grid(row=5, column=0, sticky=tk.W, pady=2)
    move_down_button.grid(row=6, column=0, sticky=tk.W, pady=2)


    # Language and Engine Settings Group
    lang_engine_group_frame = ttk.LabelFrame(main_frame, text="Language and Engine Settings", padding="10 10 10 10")
    lang_engine_group_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

    lang_frame = ttk.Frame(lang_engine_group_frame, padding="0 0 0 0") # No padding inside lang_frame
    lang_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    tk.Label(lang_frame, text="Language Code:").grid(row=0, column=0, sticky=tk.W)
    lang_entry = ttk.Entry(lang_frame, textvariable=language_var, width=30)
    lang_entry.grid(row=0, column=1, sticky=(tk.W, tk.E))
    tk.Label(lang_frame, text="(e.g., en, fr, id)").grid(row=0, column=2, sticky=tk.W)

    engine_frame = ttk.Frame(lang_engine_group_frame, padding="0 0 0 0") # No padding inside engine_frame
    engine_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    tk.Label(engine_frame, text="Engine:").grid(row=0, column=0, sticky=tk.W)
    engine_options = ['google', 'ollama']
    engine_combo = ttk.Combobox(engine_frame, textvariable=engine_var, values=engine_options, state="readonly", width=50)
    engine_combo.grid(row=0, column=1, sticky=(tk.W, tk.E))

    model_frame = ttk.Frame(lang_engine_group_frame, padding="0 0 0 0") # No padding inside model_frame
    model_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    tk.Label(model_frame, text="Model:").grid(row=0, column=0, sticky=tk.W)
    model_combo = ttk.Combobox(model_frame, textvariable=model_var, values=[], state="readonly", width=50)
    model_combo.grid(row=0, column=1, sticky=(tk.W, tk.E))
    refresh_button = ttk.Button(model_frame, text="Refresh Models", command=lambda: refresh_models(), width=15)
    refresh_button.grid(row=0, column=2, padx=5)

    def refresh_models():
        eng = engine_var.get()
        if eng == "google":
            new_models = get_google_models(GOOGLE_API_KEY)
            global DEFAULT_GEMINI_MODELS
            DEFAULT_GEMINI_MODELS = new_models
            model_combo['values'] = new_models
            model_var.set(new_models[0] if new_models else "")
        elif eng == "ollama":
            new_models = get_ollama_models()
            global DEFAULT_OLLAMA_MODELS
            DEFAULT_OLLAMA_MODELS = new_models
            model_combo['values'] = new_models
            model_var.set(new_models[0] if new_models else "")

    def update_model_options(*args):
        eng = engine_var.get()
        if eng == 'google':
            model_combo['values'] = DEFAULT_GEMINI_MODELS
            model_var.set(DEFAULT_GEMINI_MODELS[0] if DEFAULT_GEMINI_MODELS else "")
        elif eng == 'ollama':
            model_combo['values'] = DEFAULT_OLLAMA_MODELS
            model_var.set(DEFAULT_OLLAMA_MODELS[0] if DEFAULT_OLLAMA_MODELS else "")
        else:
            model_combo['values'] = []
            model_var.set("")
    engine_var.trace_add('write', update_model_options)
    update_model_options()

    # Prompt and Output Settings Group
    prompt_output_group_frame = ttk.LabelFrame(main_frame, text="Prompt and Output Settings", padding="10 10 10 10")
    prompt_output_group_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

    prompt_frame = ttk.Frame(prompt_output_group_frame, padding="0 0 0 0") # No padding inside prompt_frame
    prompt_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    tk.Label(prompt_frame, text="Prompt:").grid(row=0, column=0, sticky=tk.W)
    prompt_combo = ttk.Combobox(prompt_frame, textvariable=prompt_var, values=list(prompt_value_map.keys()), state="readonly", width=50)
    prompt_combo.grid(row=0, column=1, sticky=(tk.W, tk.E))
    def update_suffix_from_prompt(*args):
        selected_disp = prompt_combo.get()
        try:
            selected_key = prompt_value_map[selected_disp]
            suffix = PROMPT_SUFFIX_MAP.get(selected_key, DEFAULT_SUFFIX)
            suffix_var.set(suffix)
        except KeyError:
            suffix_var.set(DEFAULT_SUFFIX)
    update_suffix_from_prompt()
    prompt_var.trace_add('write', update_suffix_from_prompt)

    chinese_options_frame = ttk.Frame(prompt_output_group_frame, padding="5 0 0 0") # Padding for checkboxes
    chinese_options_frame.grid(row=1, column=0, columnspan=2, sticky=tk.W)
    chinese_chars_check = ttk.Checkbutton(chinese_options_frame, text="Include Chinese Characters", variable=enable_chinese_chars_var) # Added checkbox
    chinese_chars_check.grid(row=0, column=0, sticky=tk.W)
    pinyin_check = ttk.Checkbutton(chinese_options_frame, text="Enable Chinese Pinyin", variable=enable_pinyin_var)
    pinyin_check.grid(row=0, column=1, sticky=tk.W)

    output_frame = ttk.Frame(prompt_output_group_frame, padding="0 0 0 0") # No padding inside output_frame
    output_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    tk.Label(output_frame, text="Output Dir:").grid(row=0, column=0, sticky=tk.W)
    output_entry = ttk.Entry(output_frame, textvariable=output_dir_var, width=50)
    output_entry.grid(row=0, column=1, sticky=(tk.W, tk.E))
    tk.Button(output_frame, text="Browse Dir", command=lambda: output_dir_var.set(filedialog.askdirectory())).grid(row=0, column=2, sticky=tk.W)
    tk.Label(output_frame, text="(optional)").grid(row=0, column=3, sticky=tk.W)

    suffix_frame = ttk.Frame(prompt_output_group_frame, padding="0 0 0 0") # No padding inside suffix_frame
    suffix_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    tk.Label(suffix_frame, text="Suffix:").grid(row=0, column=0, sticky=tk.W)
    suffix_entry = ttk.Entry(suffix_frame, textvariable=suffix_var, state='readonly', width=20)
    suffix_entry.grid(row=0, column=1, sticky=(tk.W, tk.E))

    stream_frame = ttk.Frame(prompt_output_group_frame, padding="0 0 0 0") # No padding inside stream_frame
    stream_frame.grid(row=4, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    stream_check = ttk.Checkbutton(stream_frame, text="Stream Output (Google GenAI)", variable=stream_output_var)
    stream_check.grid(row=0, column=0, sticky=tk.W)

    # Processing Prompt Preview Frame (Outside of group frames for layout)
    prompt_preview_frame = ttk.LabelFrame(main_frame, text="Processing Prompt Preview", padding="10 10 10 10")
    prompt_preview_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    prompt_preview_text = tk.Text(prompt_preview_frame, height=10, width=60)
    prompt_preview_text.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E))

    custom_prompt_frame = ttk.LabelFrame(main_frame, text="Custom Prompt (optional)", padding="10 10 10 10")
    custom_prompt_frame.grid(row=4, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    custom_prompt_text = tk.Text(custom_prompt_frame, height=3, width=50)
    custom_prompt_text.grid(row=0, column=0, sticky=(tk.W, tk.E))

    window.protocol("WM_DELETE_WINDOW", lambda: window.destroy() or sys.exit(0))
    window.update_idletasks()

    file_listbox_height_pixels = file_buttons_frame.winfo_height()
    clear_all_button_height_pixels = clear_all_button.winfo_height() # Now defined before being used!
    max_listbox_height_pixels = clear_all_button_height_pixels
    file_listbox_height_pixels = min(file_listbox_height_pixels, max_listbox_height_pixels)
    char_height = file_listbox.winfo_height() / int(file_listbox.config()['height'][0]) if isinstance(file_listbox.config()['height'], tuple) and file_listbox.config()['height'] and file_listbox.config()['height'][0].isdigit() else (file_listbox.winfo_height() / int(file_listbox.config()['height']) if isinstance(file_listbox.config()['height'], str) and file_listbox.config()['height'].isdigit() else 1)
    file_listbox_height_lines = max(3, int((file_listbox_height_pixels / char_height) / 2))
    file_listbox.config(height=file_listbox_height_lines)


    # Function to update the processing prompt preview
    def update_prompt_preview(*args):
        selected_disp = prompt_combo.get()
        try:
            selected_key = prompt_value_map[selected_disp]
        except KeyError:
            selected_key = DEFAULT_PROMPT_KEY
        # Determine base prompt using pinyin if enabled
        if selected_key in ["translate", "translate_only"]:
            if enable_pinyin_var.get() or enable_chinese_chars_var.get():
                base_prompt = PROMPTS.get(selected_key + "_pinyin", PROMPTS.get(selected_key))
            else:
                base_prompt = PROMPTS.get(selected_key, PROMPTS.get(DEFAULT_PROMPT_KEY))
        else:
            base_prompt = PROMPTS.get(selected_key, PROMPTS.get(DEFAULT_PROMPT_KEY))

        final_prompt = base_prompt
        if selected_key in ["translate_pinyin", "translate_only_pinyin"]:
            if enable_chinese_chars_var.get():
                final_prompt = insert_custom_prompt(final_prompt, CHINESE_INSTRUCTIONS_CHARACTERS)
            if enable_pinyin_var.get():
                final_prompt = insert_custom_prompt(final_prompt, CHINESE_INSTRUCTIONS_PINYIN)
                final_prompt = insert_custom_prompt(final_prompt, CHINESE_INSTRUCTIONS_CONDITIONAL_FORMATTING)

        custom_prompt = custom_prompt_text.get("1.0", tk.END).strip()
        if custom_prompt:
            final_prompt = insert_custom_prompt(final_prompt, custom_prompt)

        prompt_preview_text.delete("1.0", tk.END)
        prompt_preview_text.insert(tk.END, final_prompt)

    # Bind update function to changes in prompt selection, custom prompt, and pinyin/chinese chars checkboxes
    prompt_var.trace_add("write", update_prompt_preview)
    custom_prompt_text.bind("<KeyRelease>", lambda event: update_prompt_preview())
    enable_pinyin_var.trace_add("write", update_prompt_preview)
    enable_chinese_chars_var.trace_add("write", update_prompt_preview)
    update_prompt_preview() # Initial preview update

    process_button = ttk.Button(main_frame, text="Process",
                                command=lambda: process_from_gui(window, files_list_var, language_var, engine_var, model_var, prompt_var, output_dir_var, suffix_var, prompt_value_map, stream_output_var.get(), custom_prompt_text.get("1.0", tk.END), enable_chinese_chars_var.get(), enable_pinyin_var.get()))
    process_button.grid(row=5, column=0, columnspan=3, pady=20)


    window.mainloop()
    return exit_code_from_gui

def process_from_gui(window, files_list_var, language_var, engine_var, model_var, prompt_var, output_dir_var, suffix_var, prompt_value_map, stream_output, custom_prompt_text, enable_chinese_chars, enable_pinyin):
    files_input = files_list_var.get()
    if not files_input:
        messagebox.showerror("Error", "Please select at least one file.")
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
    gui_args.stream_output_gui = stream_output
    gui_args.custom_prompt_text = custom_prompt_text.strip()
    gui_args.enable_chinese_chars_gui = enable_chinese_chars
    gui_args.enable_pinyin_gui = enable_pinyin
    window.destroy()
    gui_exit_code = process_files(gui_args, stream_output, gui_args.custom_prompt_text, enable_chinese_chars=gui_args.enable_chinese_chars_gui, enable_pinyin=gui_args.enable_pinyin_gui)
    sys.exit(gui_exit_code)

if __name__ == "__main__":
    main()