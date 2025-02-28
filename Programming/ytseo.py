# script_folder/ytseo.py
import os
import sys
import json
import requests  # Make sure to install: pip install requests
import glob # For handling wildcard file paths
import time # For rate limiting
import google.generativeai as genai # For Google Gemini API
from google.generativeai.types import GenerateContentResponse # For Google Gemini API response type
from google.api_core.exceptions import ResourceExhausted # For handling Google API quota exceptions
import argparse # For command-line argument parsing
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
import tkinter.messagebox
import pycountry # For language codes


################################################################################
# --- Customizable Variables (Configuration) ---
################################################################################

# 1. Google API Key Environment Variable Name
API_KEY_ENV_VAR_NAME = "GOOGLE_API_KEY"

# 2. User Prompt Template - **REVISED TO INCLUDE FULL LANGUAGE NAME**
USER_PROMPT_TEMPLATE = """_You are a YouTube SEO expert. Your task is to generate SEO-optimized content in **{target_language_name}** for a YouTube video based on a provided input, which may be a topic or a subtitle (.srt) file. The final output must include the following elements in **{target_language_name}**: Title, Description, Hashtags, and Tags. If the input is an SRT file, use it to create a separate chapter timestamp section—do not scatter SRT timestamps within the narrative description. Follow these instructions precisely:_

**1. Content Extraction and Analysis:**
*   **For Subtitle Files (.srt):**
    *   Extract both the dialogue text and the original timestamps from the SRT file.
    *   Do not integrate these timestamps directly into the narrative description. Instead, analyze the SRT to identify key moments that serve as chapter markers.
    *   Identify the central themes, key phrases, and recurring keywords that accurately reflect the subject matter.
*   **For Topics:**
    *   Research to pinpoint the primary subject, emerging trends, and popular search queries in **{target_language_name}**.
    *   Choose keywords that are highly relevant and truly reflective of the input in **{target_language_name}**.

**2. Title Creation:**
*   Generate a concise, engaging title in **{target_language_name}** that accurately reflects the video's content as derived from the input.
    *   The title must be between 60 and 70 characters and incorporate high-value keywords in **{target_language_name}**.
    *   Avoid adding extraneous humor or creative embellishments that are not present in the input; the title should remain faithful to the source material.

**3. Description Writing:**
*   Write a continuous, flowing narrative description in **{target_language_name}** that is **about 4000 characters long**.
    *   This narrative must be a single uninterrupted block of text with no bullet points, numbered lists, or any list formatting.
    *   The narrative may draw upon relevant material, insights, or commentary in addition to the SRT content, so long as it accurately reflects the video's subject matter and tone in **{target_language_name}**.
    *   Do not intersperse the original SRT timestamps within this narrative. Instead, use the narrative to provide an in-depth, detailed summary of the video’s content—including key themes, context, and analysis—and conclude with a strong call-to-action encouraging viewers to like, comment, subscribe, or explore related content in **{target_language_name}**.
    *   **Chapter Timestamps Section:**
        *   After the 4000-character narrative, append a separate section titled **"📌 Timestamps:"**.
        *   In this section, list the key chapter timestamps extracted from the SRT file (e.g., “00:00 - [Chapter Title]”) in **{target_language_name}**.  **(Note: Timestamps themselves remain in original format)**
        *   Format each timestamp on its own line so that it serves as a clear chapter marker, and ensure that this section is clearly separate from the main narrative.
        *   This chapter timestamp section is supplementary and does not count towards the 4000-character narrative.

**4. Hashtag Generation:**
*   Generate 10–15 relevant and trending hashtags in **{target_language_name}** that directly correspond to the themes and topics in the input.
    *   Ensure the hashtags include a mix of broad and niche terms to maximize reach in **{target_language_name}** contexts.
    *   Present the hashtags in a clearly defined section after the description (outside of the 4000-character narrative).

**5. Tag List Creation:**
*   Produce an SEO-optimized, comma-separated list of tags in **{target_language_name}** that incorporates variations of the primary keywords, related phrases, and common search queries in **{target_language_name}**.
    *   **Important:** In addition to the primary keywords and phrases, include common misspellings of those terms in **{target_language_name}** to capture a broader search audience.
    *   The entire tag list must not exceed 500 characters in total.

**6. Output Format:**
*   Present your final output with clearly labeled sections as follows in **{target_language_name}**:
    *   **Title:**
    *   **Description:**
        *   First, the 4000-character continuous narrative in **{target_language_name}**; then, on a new line, the separate **"📌 Timestamps:"** section listing chapter markers in **{target_language_name}**.
    *   **Hashtags:**
    *   **Tags:**
*   Each section must be formatted exactly as instructed.

_Every element of your output must strictly adhere to these instructions. The final result must faithfully reflect the input by preserving its key elements and themes while generating a description of about 4000 characters (using drawn relevant material as needed) and a separate chapter timestamp section. The tags must include common misspellings to help capture additional search traffic. This output should be fully optimized for YouTube SEO in **{target_language_name}**, ensuring maximum visibility and engagement.”""" + "\n\n" + "Full SRT file content:\n{srt_content}"

# 3. Default target language - NEW
DEFAULT_TARGET_LANGUAGE = "en" # Default target language

# 4. Output file extension for SEO results - NOT USED ANYMORE
# OUTPUT_FILE_EXTENSION = ".txt"
RAW_OUTPUT_FILE_EXTENSION = "_raw_response.txt" # Default extension for raw API response files
DEFAULT_RAW_OUTPUT_SUFFIX = "_raw_response" # Default suffix for raw API response files - NEW

# 5. Default Google Gemini Models - Customizable list
DEFAULT_GEMINI_MODELS = ["gemini-2.0-pro-exp-02-05","gemini-2.0-flash-thinking-exp-01-21","gemini-2.0-flash-exp", "gemini-2.0-flash", "gemini-2.0-flash-lite-preview-02-05"]
DEFAULT_GEMINI_MODEL = DEFAULT_GEMINI_MODELS[0] # Use the first model as default if none specified
DEFAULT_OLLAMA_MODELS = ["mistral-small:24b", "phi4", "qwen2.5:14b"] # Example Ollama models
DEFAULT_ENGINE = "google" # Default engine

# 6. Rate Limiting Configuration
REQUESTS_PER_MINUTE = 15
REQUEST_INTERVAL_SECONDS = 60 / REQUESTS_PER_MINUTE

# 7. Output Subfolder Name
# OUTPUT_SUBFOLDER_NAME = "seo_outputs" # NOT USED ANYMORE
RAW_OUTPUT_SUBFOLDER_NAME = "ytSEO" # Subfolder for raw API responses - RENAMED to ytSEO


# --- Prompts and Suffixes ---
PROMPTS = {"seo_prompt": USER_PROMPT_TEMPLATE} # Simplified prompts for SEO script
DEFAULT_PROMPT_KEY = "seo_prompt"
PROMPT_SUFFIX_MAP = {} # Empty map as suffixes are not needed if SEO output is not saved to file


################################################################################
# --- End of Customizable Variables ---
################################################################################


# Global variable for rate limiting
last_request_time = None


# --- Helper Functions (Modified construct_prompt) ---

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


def read_srt_file(srt_filepath):
    """Reads an SRT file and extracts dialogue text and timestamps."""
    dialogue_text = []
    timestamps = []
    try:
        with open(srt_filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            i = 0
            while i < len(lines):
                try:
                    int(lines[i].strip())
                    i += 1
                    timestamp_line = lines[i].strip()
                    timestamps.append(timestamp_line)
                    i += 1
                    text_line = ""
                    while i < len(lines) and lines[i].strip() != '':
                        text_line += lines[i].strip() + " "
                        i += 1
                    dialogue_text.append(text_line.strip())
                    i += 1
                except ValueError:
                    i += 1
    except FileNotFoundError:
        print(f"Error: SRT file not found at {srt_filepath}")
        return None, None
    except Exception as e:
        print(f"Error occurred while reading SRT file: {e}")
        return None, None

    return dialogue_text, timestamps

def read_raw_srt_content(srt_filepath):
    """Reads the entire SRT file content as a single string."""
    try:
        with open(srt_filepath, 'r', encoding='utf-8') as f:
            raw_srt_content = f.read()
        return raw_srt_content
    except FileNotFoundError:
        print(f"Error: SRT file not found at {srt_filepath}")
        return None
    except Exception as e:
        print(f"Error reading SRT file: {e}")
        return None


def construct_prompt(srt_content, timestamps, user_prompt_template, language_code=DEFAULT_TARGET_LANGUAGE): # Added language_code
    """Constructs the full prompt for the LLM API, incorporating target language NAME."""
    srt_text_for_prompt = srt_content if srt_content else "No subtitle content found."
    full_prompt = user_prompt_template.replace("{srt_content}", srt_text_for_prompt)
    language_name = get_language_name_from_code(language_code) # Get full language name
    if language_name:
        full_prompt = full_prompt.replace("{target_language_name}", language_name) # Replace with language name
    else: # Fallback to code if name not found (shouldn't happen with valid codes)
        full_prompt = full_prompt.replace("{target_language_name}", language_code) # Fallback to language code
    return full_prompt

def call_generative_ai_api(prompt, api_key, model_name=DEFAULT_GEMINI_MODEL, stream_output=False):
    """Calls the Google Generative AI API to get SEO content, optionally streaming output."""
    global last_request_time

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)

    try:
        current_time = time.time()
        if last_request_time is not None:
            time_since_last_request = current_time - last_request_time
            if time_since_last_request < REQUEST_INTERVAL_SECONDS:
                sleep_duration = REQUEST_INTERVAL_SECONDS - time_since_last_request
                print(f"Rate limit active (Google Gemini). Sleeping for {sleep_duration:.2f} seconds...")
                time.sleep(sleep_duration)
        last_request_time = time.time()

        prompt_content = prompt

        print("--- Full Prompt being sent to Google Gemini API (Model: {}): ---".format(model_name))
        print(prompt_content)
        print("--- End of Prompt ---")
        print(f"--- Calling Google Gemini API with model '{model_name}' for processing... {'Streaming output enabled' if stream_output else '(Non-streaming)'} ---")
        if stream_output:
            response = model.generate_content(prompt_content, stream=True)
            processed_text_chunks = []
            full_response_text = "" # Capture full response text
            for chunk in response:
                if chunk.text:
                    content_chunk = chunk.text
                    print("\n" + content_chunk, end="", flush=True) # Added newline for better readability
                    processed_text_chunks.append(content_chunk)
                    full_response_text += content_chunk # Append to full response
            print("\n--- Google Gemini API call completed (streaming). ---")
            processed_text = "".join(processed_text_chunks).strip()
            api_response_text = full_response_text # Use full response text for parsing
        else:
            response = model.generate_content(prompt_content, stream=False)
            print("\n--- Google Gemini API call completed (non-streaming). ---")
            processed_text = response.text
            api_response_text = response.text # Capture response text for parsing

        return api_response_text

    except ResourceExhausted as e:
        print(f"Error: Google Gemini API Quota Exhausted.", file=sys.stderr)
        print(f"  Detailed Quota Exhaustion Information:")
        if hasattr(e, 'status_code'):
            print(f"    HTTP Status Code: {e.status_code}")
        if hasattr(e, 'message'):
            print(f"    Error Message: {e.message}")
        return None
    except Exception as e:
        print(f"Error calling Google Gemini API: {e}", file=sys.stderr)
        return None


def parse_api_response(api_response):
    """Parses the API response to extract Title, Description, Hashtags, Tags."""
    if not api_response:
        print("Debug: parse_api_response - API response is None/empty.")
        return None
    try:
        sections = {}
        current_section = None
        for line in api_response.strip().split('\n'):
            line = line.strip()
            if line.startswith("**") and line.endswith("**"):
                section_title = line.replace("**", "").strip()
                current_section = section_title
                sections[current_section] = []
            elif current_section:
                sections[current_section].append(line)

        title = "\n".join(sections.get("Title", [])).strip()
        description_lines = sections.get("Description", [])
        description = "\n".join(description_lines).strip()
        timestamps_section = "\n".join(sections.get("📌 Timestamps:", [])).strip()
        hashtags = "\n".join(sections.get("Hashtags", [])).strip()
        tags = "\n".join(sections.get("Tags", [])).strip()

        parsed_data = {
            "title": title,
            "description": description.strip(),
            "timestamps_section": timestamps_section.strip(),
            "hashtags": hashtags,
            "tags": tags,
        }
        return parsed_data

    except Exception as e:
        print(f"Error parsing API response: {e}")
        return None


def format_output(seo_data, timestamps):
    """Formats the SEO data into the desired output structure."""
    if not seo_data:
        print("Debug: format_output - seo_data is None/empty.")
        return "Error: No SEO data to format."

    formatted_output = f"""**Title:**
{seo_data.get('title', 'N/A')}

**Description:**
{seo_data.get('description', 'N/A')}

**📌 Timestamps:**
{seo_data.get('timestamps_section', 'N/A')}

**Hashtags:**
{seo_data.get('hashtags', 'N/A')}

**Tags:**
{seo_data.get('tags', 'N/A')}
"""
    return formatted_output

def save_raw_api_response(api_response_text, srt_filepath, output_folder, output_suffix=DEFAULT_RAW_OUTPUT_SUFFIX): # Added output_suffix
    """Saves the raw API response to a text file with customizable suffix."""
    if not api_response_text:
        print("Debug: save_raw_api_response - No API response text to save.")
        return

    raw_output_folder_path = os.path.join(os.getcwd(), output_folder)
    os.makedirs(raw_output_folder_path, exist_ok=True)

    output_filename_base = os.path.splitext(os.path.basename(srt_filepath))[0]
    output_filename = output_filename_base + output_suffix + RAW_OUTPUT_FILE_EXTENSION # Use output_suffix
    output_filepath = os.path.join(raw_output_folder_path, output_filename)

    try:
        with open(output_filepath, 'w', encoding='utf-8') as outfile:
            outfile.write(api_response_text)
        print(f"Raw API response saved to: {output_filepath}")
    except Exception as e:
        print(f"**ERROR: Could not save raw API response to file: {output_filepath}**")
        print(f"Error details: {e}")


def process_srt_and_get_seo(srt_filepath, api_key, user_prompt_template, model_name=DEFAULT_GEMINI_MODEL, stream_output=False, language_code=DEFAULT_TARGET_LANGUAGE, output_suffix=DEFAULT_RAW_OUTPUT_SUFFIX): # Added output_suffix
    """Processes a single SRT file and returns the formatted SEO output, now with language name in prompt and output suffix."""
    raw_srt_content = read_raw_srt_content(srt_filepath)
    if raw_srt_content is None:
        return None

    prompt = construct_prompt(raw_srt_content, None, user_prompt_template, language_code=language_code) # Pass language_code to construct_prompt
    api_response_text = call_generative_ai_api(prompt, api_key, model_name=model_name, stream_output=stream_output)

    save_raw_api_response(api_response_text, srt_filepath, RAW_OUTPUT_SUBFOLDER_NAME, output_suffix=output_suffix) # Save raw response here, pass output_suffix

    seo_data = parse_api_response(api_response_text)
    if seo_data:
        return format_output(seo_data, None)
    else:
        return "Error: Failed to generate SEO content from API."



def use_gui(command_line_files=None, args=None):
    """Launches a tkinter GUI for script options, pre-filled and synced with command-line args."""
    window = tk.Tk()
    window.title("YouTube SEO Script GUI")

    settings = {}

    files_list_var = tk.Variable(value=command_line_files if command_line_files else [])
    engine_var = tk.StringVar(value=args.engine if args and args.engine else DEFAULT_ENGINE)
    model_var = tk.StringVar(value=args.model if args and args.model else DEFAULT_GEMINI_MODEL)
    prompt_var = tk.StringVar(value=args.prompt_key if args and args.prompt_key else DEFAULT_PROMPT_KEY)
    output_dir_var = tk.StringVar(value=args.output if args and args.output else RAW_OUTPUT_SUBFOLDER_NAME) # Changed default to RAW_OUTPUT_SUBFOLDER_NAME
    suffix_var = tk.StringVar(value=args.suffix if args and args.suffix else DEFAULT_RAW_OUTPUT_SUFFIX) # Suffix now populated with default suffix
    stream_output_var = tk.BooleanVar(value=args.stream if args and args.stream else False)
    language_var = tk.StringVar(value=args.language if args and args.language else DEFAULT_TARGET_LANGUAGE) # NEW: Language var

    # --- GUI Layout (including Model and all options) ---
    files_frame = ttk.Frame(window, padding="10 10 10 10"); files_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    tk.Label(files_frame, text="SRT Files:").grid(row=0, column=0, sticky=tk.NW)
    file_listbox = tk.Listbox(files_frame, listvariable=files_list_var, height=5, width=60); file_listbox.grid(row=1, column=0, sticky=(tk.W, tk.E)) # Corrected to tk.Listbox
    file_buttons_frame = ttk.Frame(files_frame, padding="0 0 0 0"); file_buttons_frame.grid(row=1, column=1, sticky=(tk.N, tk.S))
    tk.Button(file_buttons_frame, text="Add Files", command=lambda: add_files_to_list(files_list_var, file_listbox, window)).grid(row=0, column=0, sticky=tk.W, pady=2)
    tk.Button(file_buttons_frame, text="Clear All", command=lambda: files_list_var.set([]), width=10).grid(row=1, column=0, sticky=tk.W, pady=2)

    lang_frame = ttk.Frame(window, padding="10 10 10 10") # NEW: Language Frame
    lang_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    tk.Label(lang_frame, text="Language Code:").grid(row=0, column=0, sticky=tk.W) # NEW: Language Label
    lang_entry = ttk.Entry(lang_frame, textvariable=language_var, width=30) # NEW: Language Entry
    lang_entry.grid(row=0, column=1, sticky=(tk.W, tk.E))
    tk.Label(lang_frame, text="(e.g., en, fr, id)").grid(row=0, column=2, sticky=tk.W) # NEW: Language Hint

    engine_frame = ttk.Frame(window, padding="10 10 10 10"); engine_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S)) # Shifted down
    tk.Label(engine_frame, text="Engine:").grid(row=0, column=0, sticky=tk.W)
    engine_options = ['google', 'ollama'] # Add 'ollama' if you intend to support it in GUI
    engine_combo = ttk.Combobox(engine_frame, textvariable=engine_var, values=engine_options, state="readonly"); engine_combo.grid(row=0, column=1, sticky=(tk.W, tk.E))

    model_frame = ttk.Frame(window, padding="10 10 10 10"); model_frame.grid(row=4, column=0, sticky=(tk.W, tk.E, tk.N, tk.S)) # Shifted down
    tk.Label(model_frame, text="Model:").grid(row=0, column=0, sticky=tk.W)
    model_combo = ttk.Combobox(model_frame, textvariable=model_var, values=DEFAULT_GEMINI_MODELS, state="readonly"); model_combo.grid(row=0, column=1, sticky=(tk.W, tk.E)) # Populate with Gemini models initially

    prompt_frame = ttk.Frame(window, padding="10 10 10 10"); prompt_frame.grid(row=5, column=0, sticky=(tk.W, tk.E, tk.N, tk.S)) # Shifted down
    tk.Label(prompt_frame, text="Prompt:").grid(row=0, column=0, sticky=tk.W)
    prompt_options = list(PROMPTS.keys())
    prompt_combo = ttk.Combobox(prompt_frame, textvariable=prompt_var, values=prompt_options, state="readonly"); prompt_combo.grid(row=0, column=1, sticky=(tk.W, tk.E))

    output_frame = ttk.Frame(window, padding="10 10 10 10"); output_frame.grid(row=6, column=0, sticky=(tk.W, tk.E, tk.N, tk.S)) # Shifted down
    tk.Label(output_frame, text="Output Dir (Raw Responses):").grid(row=0, column=0, sticky=tk.W) # Updated label
    output_entry = ttk.Entry(output_frame, textvariable=output_dir_var, width=50); output_entry.grid(row=0, column=1, sticky=(tk.W, tk.E))
    tk.Button(output_frame, text="Browse Dir", command=lambda: output_dir_var.set(filedialog.askdirectory())).grid(row=0, column=2, sticky=tk.W)

    suffix_frame = ttk.Frame(window, padding="10 10 10 10"); suffix_frame.grid(row=7, column=0, sticky=(tk.W, tk.E, tk.N, tk.S)) # Shifted down
    tk.Label(suffix_frame, text="Raw Response Suffix:").grid(row=0, column=0, sticky=tk.W) # Updated label for suffix
    suffix_entry = ttk.Entry(suffix_frame, textvariable=suffix_var, width=20, state='enabled'); suffix_entry.grid(row=0, column=1, sticky=(tk.W, tk.E)) # Enabled suffix entry

    stream_frame = ttk.Frame(window, padding="10 10 10 10"); stream_frame.grid(row=8, column=0, sticky=(tk.W, tk.E, tk.N, tk.S)) # Shifted down
    stream_check = ttk.Checkbutton(stream_frame, text="Stream Output", variable=stream_output_var); stream_check.grid(row=0, column=0, sticky=tk.W)


    def process_from_gui():
        settings['files'] = list(files_list_var.get())
        settings['engine'] = engine_var.get()
        settings['model'] = model_var.get()
        settings['prompt_key'] = prompt_var.get()
        settings['output_dir'] = output_dir_var.get()
        settings['suffix'] = suffix_var.get() # Get suffix from GUI
        settings['stream_output'] = stream_output_var.get()
        settings['language_code'] = language_var.get() # NEW: Get language code from GUI
        window.destroy()
        window.quit()
        return settings

    process_button = ttk.Button(window, text="Process", command=process_from_gui); process_button.grid(row=9, column=0, columnspan=3, pady=20) # Shifted down

    window.mainloop()
    return settings


def add_files_to_list(files_list_var, file_listbox, window):
    selected_files = filedialog.askopenfilenames(filetypes=[("SRT files", "*.srt"), ("All files", "*.*")])
    if selected_files:
        current_files = list(files_list_var.get())
        updated_files = current_files + list(selected_files)
        files_list_var.set(tuple(updated_files))


def main():
    api_key = os.environ.get(API_KEY_ENV_VAR_NAME)
    if not api_key:
        print(f"Error: {API_KEY_ENV_VAR_NAME} environment variable not set.")
        return

    parser = argparse.ArgumentParser(description="YouTube SEO Script")
    parser.add_argument("files", nargs="*", help="Path(s) to SRT file(s)")
    parser.add_argument("-p", "--prompt", dest="prompt_key", default=DEFAULT_PROMPT_KEY, choices=list(PROMPTS.keys()), help=f"Prompt to use. Default: '{DEFAULT_PROMPT_KEY}'.")
    parser.add_argument("-o", "--output", dest="output", default=RAW_OUTPUT_SUBFOLDER_NAME, help=f"Output directory for raw responses. Default: '{RAW_OUTPUT_SUBFOLDER_NAME}'.") # Updated description
    parser.add_argument("-s", "--suffix", dest="suffix", default=DEFAULT_RAW_OUTPUT_SUFFIX, help=f"Suffix for raw output files. Default: '{DEFAULT_RAW_OUTPUT_SUFFIX}'.") # Updated description, default to DEFAULT_RAW_OUTPUT_SUFFIX
    parser.add_argument("--stream", action='store_true', default=False, help="Enable streaming output.")
    parser.add_argument("-e", "--engine", dest="engine", default=DEFAULT_ENGINE, choices=['google', 'ollama'], help=f"AI engine to use: google or ollama.") # Engine command line argument
    parser.add_argument("-m", "--model", "--model", dest="model", default=DEFAULT_GEMINI_MODEL, help=f"Model to use (engine specific). Default Google Gemini model: '{DEFAULT_GEMINI_MODEL}'.") # Model arg
    parser.add_argument("-l", "--language", dest="language", default=DEFAULT_TARGET_LANGUAGE, help=f"Target language code (e.g., en, fr, id). Default: '{DEFAULT_TARGET_LANGUAGE}'.") # NEW: Language argument

    args = parser.parse_args()

    # Expand file patterns using glob in main script before passing to GUI
    filepaths_from_cli = []
    if args.files:
        for pattern in args.files:
            filepaths_from_cli.extend(glob.glob(pattern))
    else:
        filepaths_from_cli = None # or [] if you prefer an empty list

    gui_settings = use_gui(command_line_files=filepaths_from_cli, args=args) # Call GUI always, pass command-line files and args to GUI
    if not gui_settings:
        return # GUI closed without processing

    srt_file_patterns = gui_settings.get('files', [])
    prompt_key = gui_settings.get('prompt_key', args.prompt_key) # GUI setting or CLI arg
    output_folder_base = gui_settings.get('output_dir', args.output) # GUI setting or CLI arg
    suffix = gui_settings.get('suffix', args.suffix) # Get suffix from GUI setting or CLI arg
    stream_output = gui_settings.get('stream_output', args.stream) # GUI setting or CLI arg
    engine = gui_settings.get('engine', args.engine) # Get engine from GUI or CLI
    model_name = gui_settings.get('model', args.model) # Get model from GUI or CLI
    language_code = gui_settings.get('language_code', args.language) # NEW: Get language code from GUI or CLI

    raw_output_folder_path = os.path.join(os.getcwd(), RAW_OUTPUT_SUBFOLDER_NAME) # Define raw output folder path - now ytSEO
    os.makedirs(raw_output_folder_path, exist_ok=True) # Create raw output folder if it doesn't exist


    # output_folder_path = os.path.join(os.getcwd(), output_folder_base) # No SEO output folder anymore
    # os.makedirs(output_folder_path, exist_ok=True) # No SEO output folder anymore

    processed_files = 0
    for pattern in srt_file_patterns:
        for srt_filepath in glob.glob(pattern):
            language_name = get_language_name_from_code(language_code) or language_code # Get name or fallback to code
            print(f"Processing SRT file: {srt_filepath}, Language: {language_name} ({language_code})") # NEW: Print language name
            seo_output = process_srt_and_get_seo(srt_filepath, api_key, PROMPTS.get(prompt_key, USER_PROMPT_TEMPLATE), model_name=model_name, stream_output=stream_output, language_code=language_code, output_suffix=suffix) # Pass suffix to process_srt_and_get_seo
            if seo_output:
                processed_files += 1 # Still count as processed (even if not saved)
            else:
                print(f"Failed to process SRT file: {srt_filepath}")
            print("-" * 50)

    if processed_files > 0:
        print(f"SRT processing complete. Raw API responses saved to '{RAW_OUTPUT_SUBFOLDER_NAME}' folder. SEO output printed to console but NOT saved to files.") # Updated summary message
    else:
        print("No SRT files processed.")


if __name__ == "__main__":
    main()