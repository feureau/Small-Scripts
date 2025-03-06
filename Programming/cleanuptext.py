#!/usr/bin/env python3
import os
os.environ["PYTHONIOENCODING"] = "utf-8" # Setting PYTHONIOENCODING to utf-8 at the start
import sys
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
from collections import deque  # For storing previous lines - for SRT context # Keep import, might be used in other parts
# --- Configuration ---
DEFAULT_TARGET_LANGUAGE = "en" # Changed to "en" for two-letter code default
DEFAULT_GEMINI_MODELS_BASE = [] # Now empty - we rely on API listing
DEFAULT_GEMINI_MODELS = [] # Initialize as empty, will be populated dynamically
DEFAULT_OLLAMA_MODELS = ["mistral-small:24b", "phi4", "qwen2.5:14b"]
DEFAULT_ENGINE = "google"
DEFAULT_SUFFIX = "_cleaned" # Changed default suffix to "_cleaned" for cleanup only
OUTPUT_SUBFOLDER = "processed_output"
ORIGINAL_FILES_SUBFOLDER = "original_files"
CONTEXT_LINES = 5               # Number of previous lines for SRT context # Keep import, might be used elsewhere
MAX_RETRIES = 3                 # Max retries for API calls - for SRT # Keep, might be used elsewhere
# --- Prompts ---
CLEANUP_PROMPT = """Please clean up the following text which is the result of Optical Character Recognition (OCR). The text is very messy and contains significant errors, typos, gibberish, and formatting problems typical of OCR output, including **pagination numbers and inconsistent line breaks within paragraphs**. Format the text properly with a structure that is fit for book publishing.
**Your task is to perform aggressive cleaning and correction to produce a perfectly clean, readable, and well-formatted plain text.**
**Specifically, your cleaning and correction MUST include:**
* **AGGRESSIVELY correct ALL OCR errors, typos, and gibberish.** This is the most important step. Ensure the text is perfectly readable and grammatically correct with proper terminal punctuation marks. Make sure all sentences ended with the proper terminal punctuation marks, even if it's a title  or ending with a linebreak.
* **REMOVE ALL pagination numbers.**  This includes both Arabic numerals (e.g., 1, 2, 3...) and Roman numerals (e.g., I, II, III, IV, V...). Do not include any page numbers in the cleaned output.
* **AGGRESSIVELY REMOVE** unnecessary line breaks WITHIN paragraphs** to create flowing paragraphs.**  Text within a paragraph should be on a single line unless it's a deliberate line break for formatting within that paragraph (which is unlikely in OCR cleanup).
* **JOIN hyphenated words that are split across lines.** For example, if "state- \n ment" appears, it should be corrected to "statement".
* **COLLAPSE multiple spaces and tabs into single spaces.** Remove leading and trailing whitespace from lines. Ensure consistent spacing throughout the text.
* **Ensure proper paragraphing and line breaks for excellent readability.** Paragraphs should be clearly separated by blank lines in the output.  **Preserve these paragraph breaks.**
* **Remove ALL extra whitespace, formatting inconsistencies, and extraneous characters that are artifacts of the OCR process.**  Ensure a clean and professional output.
* **CHAPTER TITLE that is in roman numeral must be converted into arabic numbering with proper terminal punctuation marks at the end, for example Chapter IV becomes Chapter 4. Also, the title of the chapter must be terminated with proper terminal punctuation marks, for example Down the Rabbit Hole becomes Down the Rabbit Hole. Note the period at the end.**
**IMPORTANT:** Provide **ONLY** the final, cleaned and corrected text, in **plain text format**.  Do **NOT** include the original OCR text. Do **NOT** include any page numbers.  Do **NOT** include any introductory phrases, notes, quotation marks, or anything else. Just the clean, corrected plain text, perfectly readable and free of errors.
**Text to clean:** {text}"""
PROMPTS = {
    "cleanup": CLEANUP_PROMPT, # Only keep the cleanup prompt
}
DEFAULT_PROMPT_KEY = "cleanup" # Default prompt is now always cleanup
PROMPT_SUFFIX_MAP = {
    "cleanup": "_cleaned", # Only keep the cleanup suffix
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
def insert_custom_prompt(original_prompt, custom_prompt):
    """Inserts the custom prompt after the first line of the original prompt."""
    lines = original_prompt.splitlines(keepends=True)
    if len(lines) > 1:
        lines.insert(1, custom_prompt.strip() + "\n\n") # Insert after the first line, add two newlines for separation
    elif lines: # if only one line or empty, append after the first line if exists, else just prepend.
        lines.append("\n\n" + custom_prompt.strip() + "\n")
    else:
        lines.insert(0, custom_prompt.strip() + "\n\n") # if prompt was empty, prepend.
    return "".join(lines)
def translate_srt_whole_file(input_file, output_file, target_language, engine, model_name, google_api_key, processing_prompt, stream_output=False):
    """Translates SRT file by sending the entire file content in one call."""
    # SRT translation is removed in this cleanup-only version
    pass # Functionality removed for cleanup-only script
def translate_text(text, target_language, engine, model_name, google_api_key, processing_prompt, stream_output=False, prev_context=None): # Changed default to False (non-streaming default)
    """Translates text using Google Gemini API or Ollama, with rate limiting for Gemini."""
    global last_request_time
    if engine == "google":
        from google import genai
        from google.api_core.exceptions import ResourceExhausted, NotFound, GoogleAPIError # Ensure GoogleAPIError is imported
        from google.genai import types # Import types

        client = genai.Client(api_key=google_api_key) # Initialize client here using new SDK

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
            prompt_content = processing_prompt.format(text=text) # target_language removed
            generate_content_config = types.GenerateContentConfig() # Create config object

            api_params = { # Prepare API call parameters
                "model": model_name if model_name else None, # Include model only if specified
                "contents": prompt_content,
                "config": generate_content_config
            }
            if model_name is None: # Remove 'model' key if model_name is None to use API default
                del api_params["model"]

            if stream_output: # Conditional streaming based on stream_output parameter
                print(f"--- Calling Google Gemini API with model '{api_params.get('model', 'default')}' for processing... Streaming output below: ---") # Use 'default' if model is not in params
                response_stream = client.models.generate_content_stream( # Use _stream method
                    **api_params # Pass parameters as kwargs
                )
                processed_text_chunks = []
                for chunk in response_stream: # Iterate through response chunks (parts)
                    if chunk.text: # Check if the chunk has text content
                        content_chunk = chunk.text
                        print(content_chunk, end="", flush=True)
                        processed_text_chunks.append(content_chunk)
                print("\n--- Google Gemini API call completed and output streamed. ---")
                processed_text = "".join(processed_text_chunks).strip()
                return processed_text
            else: # Non-streaming mode
                print(f"--- Calling Google Gemini API with model '{api_params.get('model', 'default')}' for processing... (Non-streaming) ---") # Use 'default' if model is not in params
                response = client.models.generate_content( # Use client.models.generate_content
                    **api_params # Pass parameters as kwargs
                )
                print("\n--- Google Gemini API call completed. ---")
                processed_text = response.text
                return processed_text
        except ResourceExhausted as e:
            print(f"Error: Google Gemini API Quota Exhausted.", file=sys.stderr)
            print(f"  Detailed Quota Exhaustion Information:")
            if hasattr(e, 'status_code'):
                print(f"    HTTP Status Code: {e.status_code}")
            if hasattr(e, 'message'):
                print(f"    Error Message: {e.message}')") # Corrected f-string formatting
            return None # Simplified error handling - return None directly
        except NotFound as e: # Catch NotFound error for invalid model name
            print(f"Warning: Gemini model '{model_name}' not found or unavailable. It will be excluded from the model list.", file=sys.stderr) # Still warn if *user-specified* model not found
            print(f"  Detailed Model Not Found Information:")
            if hasattr(e, 'status_code'):
                print(f"    HTTP Status Code: {e.status_code}")
            if hasattr(e, 'message'):
                print(f"    Error Message: {e.message}")
            return None # Return None to indicate processing failed for this model, but not a fatal error
        except GoogleAPIError as e: # Catch general API errors
            print(f"Error calling Google Gemini API: {e}", file=sys.stderr)
            if hasattr(e, 'status_code'):
                print(f"    HTTP Status Code: {e.status_code}")
            if hasattr(e, 'message'):
                print(f"    Error Message: {e.message}")
            return None
        except Exception as e:
            print(f"Error calling Google Gemini API: {e}", file=sys.stderr)
            return None
    elif engine == "ollama":
        try:
            prompt_content = processing_prompt.format(text=text) # Removed target_language from prompt formatting
            payload = {
                "model": model_name,
                "messages": [{"role": "user", "content": prompt_content}],
                "stream": True # Ollama is always streaming, keep it True
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
    # Language code functionality removed as it's cleanup-only
    return None
def natural_sort_key(s):
    """Generates keys for natural sorting."""
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split(re.compile('([0-9]+)'), s)]

def get_available_gemini_models_from_api(api_key, potential_models): # potential_models is now effectively ignored
    """
    Queries Google Gemini API using client.models.list() to get available models.
    Returns a list of valid/available Gemini model names directly from the API.
    """
    from google import genai
    from google.api_core.exceptions import GoogleAPIError # Keep GoogleAPIError import
    from google.genai import types # Keep types import

    available_models = []
    client = genai.Client(api_key=api_key) # Initialize client

    print("--- Checking Google Gemini model availability from API using client.models.list()... ---")
    try:
        response_model_list = client.models.list() # Call client.models.list() to get all models
        api_model_names = [model.name for model in response_model_list] # Extract all model names from API response into a list

        if not api_model_names: # Check if API returned any models at all
            print("Warning: Gemini API model list is empty. No models available from API.")
            return [] # Return empty list if no models from API
        else:
            print(f"  Found {len(api_model_names)} models available from Gemini API.")
            return api_model_names # Return the list of model names from the API

    except GoogleAPIError as e: # Catch general API errors during list call
        print(f"  Error listing Gemini models from API: {e}")
        print("  Warning: Could not retrieve Gemini model list from API. Please check your API key and network connection.")
        return [] # Return empty list on API error to indicate no models available
    except Exception as e: # Catch any other unexpected exceptions during API list call
        print(f"  Unexpected error during Gemini model list retrieval: {e}")
        print("  Warning: Could not retrieve Gemini model list due to unexpected error. ")
        return [] # Return empty list on unexpected error


def process_files(args, stream_output, custom_prompt_text="", enable_pinyin=False): # enable_pinyin is now irrelevant for cleanup-only
    """Processes files for translation or cleanup based on arguments.
       Now processes files regardless of extension."""

    global DEFAULT_GEMINI_MODELS # Ensure we are using the global list

    # DEFAULT_GEMINI_MODELS list is now populated in main() just once at startup
    # No need to repopulate it here anymore.

    global last_request_time
    last_request_time = None
    quota_exhausted = False
    exit_code = 0 # Initialize exit code to success
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
    target_language = None # Language is not relevant for cleanup
    target_language_code = None # Language code is not relevant for cleanup
    output_dir_base = args.output if args.output else OUTPUT_SUBFOLDER # Base output dir, before language code
    # --- Construct output directory name ---
    output_dir = os.path.join(os.getcwd(), output_dir_base) # Output dir for cleanup, no language code
    os.makedirs(output_dir, exist_ok=True)
    if args.engine == "google":
        # DEFAULT_GEMINI_MODELS is populated in main()
        # No need for fallback to DEFAULT_GEMINI_MODELS_BASE anymore

        model_name = args.model if args.model else None # Let API use default model if None is specified
        if args.model and not DEFAULT_GEMINI_MODELS and DEFAULT_GEMINI_MODELS != []: # If user specified a model but no models were loaded from API, and API model list is not explicitly empty (empty list means API call was attempted)
            print(f"Warning: You specified model '{args.model}', but no Gemini models were loaded from the API. Using API default model instead (if available).", file=sys.stderr)
        elif not DEFAULT_GEMINI_MODELS and DEFAULT_GEMINI_MODELS != []: # If no model specified by user and no models loaded from API
             print(f"Warning: No Gemini models available from API. Using API default model (if available).", file=sys.stderr)


    elif args.engine == "ollama":
        default_model = DEFAULT_OLLAMA_MODELS[0]
        model_name = args.model if args.model else default_model
    else:
        model_name = None
    processing_prompt_base = PROMPTS.get(args.prompt_key) # Should always be "cleanup" now
    if not processing_prompt_base:
        processing_prompt_base = PROMPTS[DEFAULT_PROMPT_KEY]
    processing_prompt = processing_prompt_base # No more conditional prompt selection

    # Insert custom prompt if provided
    if custom_prompt_text:
        processing_prompt = insert_custom_prompt(processing_prompt_base, custom_prompt_text)
    else:
        processing_prompt = processing_prompt_base
    processing_settings = {
        "Engine": args.engine,
        "Model": model_name if model_name else "API Default", # Indicate "API Default" if no model name is explicitly set
        "Prompt": args.prompt_key, # Will always be cleanup
        "Output Directory": output_dir,
        "Output File Suffix": args.suffix,
        "Files": args.files,
        "Stream Output": stream_output, # Added stream output setting
        "Custom Prompt": custom_prompt_text if custom_prompt_text else "None", # Include custom prompt in settings
    }
    for file_path in all_files:
        print(f"--- Processing file: '{file_path}' ---")
        try:
            # SRT file handling removed for cleanup-only script
            if file_path.lower().endswith('.srt'):
                print(f"Warning: SRT file '{file_path}' will be processed as a text file for cleanup. SRT-specific formatting will be ignored.")

            # Existing text file processing (and now SRT files too)
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
            processed_text = translate_text( # Using translate_text but for cleanup prompt
                text,
                target_language, # Will be None, not used in cleanup prompt
                args.engine,
                model_name,
                GOOGLE_API_KEY,
                processing_prompt,
                stream_output # Pass stream_output to translate_text
            )
            if processed_text:
                base_name = os.path.basename(file_path)
                name, ext = os.path.splitext(base_name)
                # --- Construct output filename ---
                output_file_path = os.path.join(output_dir, f"{name}{args.suffix}{ext}") # No language code in filename for cleanup
                print(f"  Saving processed output to: '{output_file_path}'") # Debug print before saving
                with open(output_file_path, "w", encoding="utf-8") as outfile:
                    outfile.write(processed_text)
                print(f"  Successfully saved to: '{output_file_path}'") # Debug print after saving
                print(f"\nProcessed '{file_path}' using {args.engine} engine, model '{model_name if model_name else 'API Default'}', prompt '{args.prompt_key}' -> '{output_file_path}'")
            elif processed_text is None and args.engine == "google":
                print(f"Processing failed for '{file_path}' due to Google Gemini Quota Exhaustion or Model issue (New SDK). Script will terminate file processing for Gemini errors.", file=sys.stderr)
                quota_exhausted = True
                exit_code = 1 # Set exit code to 1 for quota exhaustion or Gemini model issue
                break # Add break here to stop processing further files for Google Gemini errors
            else:
                print(f"Processing failed for '{file_path}'. See error messages above.", file=sys.stderr)
        except FileNotFoundError:
            print(f"Error: File not found: {file_path}", file=sys.stderr)
        except Exception as e:
            print(f"Error processing {file_path}: Exception Type: {type(e)}, Message: {e}", file=sys.stderr) # Simplified error print
        finally:
            print(f"--- Finished processing file: '{file_path}' ---")
    if quota_exhausted:
        print("\n--- Script terminated early due to Google Gemini Quota Exhaustion or Model issue (New SDK). ---", file=sys.stderr)
        return exit_code # Return non-zero exit code for quota exhaustion or Gemini errors
    print("\n--- Processing Settings Used ---")
    for key, value in processing_settings.items():
        print(f"{key}: {value}")
    print("--- End Processing Settings ---")
    return exit_code # Return 0 for successful processing (or 1 if error occurred but not quota exhaustion, though currently only quota exhaustion sets exit_code to 1)
def main():
    """Main function to always launch GUI, optionally pre-filled with command-line files."""

    global DEFAULT_GEMINI_MODELS # Ensure we are modifying the global list

    DEFAULT_GEMINI_MODELS = get_available_gemini_models_from_api(GOOGLE_API_KEY, DEFAULT_GEMINI_MODELS_BASE) # Populate Gemini models list ONCE at startup

    parser = argparse.ArgumentParser(description="Cleanup text files using Google Gemini or Ollama.") # Updated description
    parser.add_argument("files", nargs="*", help="Path(s) to the text file(s) to process. Will be pre-filled in GUI.")
    parser.add_argument("-e", "--engine", default=DEFAULT_ENGINE, choices=['google', 'ollama'], help=f"AI engine to use: google or ollama.")
    parser.add_argument("-m", "--model", "--model", dest="model", default=None, help=f"Model to use (engine specific). If not specified, API default model will be used for Google Gemini.") # Updated model help text
    parser.add_argument("-p", "--prompt", "--prompt", dest="prompt_key", default=DEFAULT_PROMPT_KEY, choices=PROMPTS.keys(), help=f"Prompt to use. Keywords: {', '.join(PROMPTS.keys())} (default: {DEFAULT_PROMPT_KEY})") # Keep prompt arg for CLI for potential advanced use, but default to cleanup
    parser.add_argument("-o", "--output", default=None, help="Output directory (overrides '{OUTPUT_SUBFOLDER}').")
    parser.add_argument("-s", "--suffix", dest="suffix", default=DEFAULT_SUFFIX, help=f"Suffix for processed file names.")
    parser.add_argument("--no-stream", dest="stream_output_cli", action='store_false', default=False, help="Disable streaming output for Google Gemini (CLI only).") # CLI option to disable stream, default False (non-streaming CLI default)
    parser.set_defaults(stream_output_cli=False) # Default stream is False for CLI
    args = parser.parse_args()
    resolved_files = []
    for file_pattern in args.files:
        resolved_files.extend(glob.glob(file_pattern))
    resolved_files.sort(key=natural_sort_key)
    gui_exit_code = use_gui(resolved_files, args)
    if gui_exit_code is not None: # GUI mode was used
        sys.exit(gui_exit_code) # Exit with code from GUI processing
    else: # CLI mode (GUI was bypassed or not used)
        sys.exit(process_files(args, args.stream_output_cli, enable_pinyin=False)) # enable_pinyin is now irrelevant
def use_gui(command_line_files, args):
    """Launches a tkinter GUI for script options, optionally pre-filled with files.
       Returns exit code from processing, or None if GUI is closed without processing."""

    global DEFAULT_GEMINI_MODELS # Use the global list

    window = tk.Tk()
    window.title("Text Cleanup Script GUI") # Updated title
    exit_code_from_gui = None # Initialize exit code for GUI
    files_list_var = tk.Variable(value=command_line_files if command_line_files else [])
    language_var = tk.StringVar(value="") # Language var is now irrelevant, keep empty
    engine_var = tk.StringVar(value=args.engine if args.engine else DEFAULT_ENGINE)
    model_var = tk.StringVar(value=args.model if args.model else "") # Keep model_var, but it can be empty for API default
    prompt_var = tk.StringVar(value="cleanup") # Always set prompt_var to "cleanup"
    output_dir_var = tk.StringVar(value=args.output if args.output else "")
    suffix_var = tk.StringVar(value=args.suffix if args.suffix else DEFAULT_SUFFIX)
    stream_output_var = tk.BooleanVar(value=False) # Default to non-streaming in GUI
    custom_prompt_var = tk.StringVar(value="") # Variable to store custom prompt text

    files_frame = ttk.Frame(window, padding="10 10 10 10")
    files_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    tk.Label(files_frame, text="Files:").grid(row=0, column=0, sticky=tk.NW)
    file_listbox = tk.Listbox(files_frame, listvariable=files_list_var, height=10, width=60, selectmode=tk.EXTENDED)
    file_listbox.grid(row=1, column=0, sticky=(tk.W, tk.E))
    file_buttons_frame = ttk.Frame(files_frame, padding="0 0 0 0")
    file_buttons_frame.grid(row=1, column=1, sticky=(tk.N, tk.S))
    def add_files_to_list():
        selected_files = filedialog.askopenfilenames(filetypes=[("Text files", "*.txt;*.md;*.text;*.rtf;*.srt"), ("All files", "*.*")]) # Added .srt to file dialog
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

    engine_frame = ttk.Frame(window, padding="10 10 10 10")
    engine_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    tk.Label(engine_frame, text="Engine:").grid(row=0, column=0, sticky=tk.W)
    engine_options = ['google', 'ollama']
    engine_combo = ttk.Combobox(engine_frame, textvariable=engine_var, values=engine_options, state="readonly")
    engine_combo.grid(row=0, column=1, sticky=(tk.W, tk.E))
    model_frame = ttk.Frame(window, padding="10 10 10 10")
    model_frame.grid(row=4, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    tk.Label(model_frame, text="Model (optional for Google):").grid(row=0, column=0, sticky=tk.W) # Updated label text
    model_combo = ttk.Combobox(model_frame, textvariable=model_var, values=[], state="readonly")
    model_combo.grid(row=0, column=1, sticky=(tk.W, tk.E))

    def update_model_options(*args):
        selected_engine = engine_var.get()
        if selected_engine == 'google':
            model_options = DEFAULT_GEMINI_MODELS # Use the API-loaded list
        elif selected_engine == 'ollama':
            model_options = DEFAULT_OLLAMA_MODELS
        else:
            model_options = []

        model_combo['values'] = model_options

        if selected_engine == 'google':
            if DEFAULT_GEMINI_MODELS:
                model_combo.set('') # Set to blank initially in GUI to indicate optional, API default will be used if blank
            else: # If no models loaded from API at all
                tk.messagebox.showwarning("Warning", "No Google Gemini models available from API. Using API default model if you proceed.") # Warn user, but allow to proceed with API default
                model_combo['values'] = [] # Clear model options
                model_combo.set('') # Ensure it's blank
        elif selected_engine == 'ollama':
            model_var.set(DEFAULT_OLLAMA_MODELS[0] if DEFAULT_OLLAMA_MODELS else "") # Set default Ollama model if available
        else:
            model_var.set("")

        # Calculate max width and set Combobox width
        max_model_name_length = 0
        for model_name in model_options:
            max_model_name_length = max(max_model_name_length, len(model_name))
        model_combo_width = max(max_model_name_length + 5, 20) # Add some padding, set minimum width
        model_combo.config(width=model_combo_width)


    engine_var.trace_add('write', update_model_options)

    # Model list is populated in main(), no need to call update_model_options() here at GUI startup anymore.
    model_combo['values'] = DEFAULT_GEMINI_MODELS # Set initial values (could be empty list)
    update_model_options() # Call it once at startup to set initial width

    custom_prompt_frame = ttk.Frame(window, padding="10 10 10 10")
    custom_prompt_frame.grid(row=5, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    tk.Label(custom_prompt_frame, text="Custom Prompt (optional):").grid(row=0, column=0, sticky=tk.NW)
    custom_prompt_text = tk.Text(custom_prompt_frame, height=3, width=50)
    custom_prompt_text.grid(row=1, column=0, sticky=(tk.W, tk.E))
    custom_prompt_var.set(custom_prompt_text.get("1.0", tk.END).strip()) # Initialize custom_prompt_var with empty text

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
    stream_frame = ttk.Frame(window, padding="10 10 10 10")
    stream_frame.grid(row=8, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    stream_check = ttk.Checkbutton(stream_frame, text="Stream Output (Google Gemini)", variable=stream_output_var) # Checkbox for stream output
    stream_check.grid(row=0, column=0, sticky=tk.W)
    process_button = ttk.Button(window, text="Process", command=lambda: process_from_gui(window, files_list_var, language_var, engine_var, model_var, prompt_var, output_dir_var, suffix_var, stream_output_var.get(), custom_prompt_text.get("1.0", tk.END))) # Removed prompt_value_map and enable_pinyin
    process_button.grid(row=9, column=0, columnspan=3, pady=20)

    window.protocol("WM_DELETE_WINDOW", lambda: window.destroy() or sys.exit(0) ) # Close and exit 0 if GUI closed
    window.mainloop()
    return exit_code_from_gui # Return exit code from GUI, will be None if GUI closed without processing
def process_from_gui(window, files_list_var, language_var, engine_var, model_var, prompt_var, output_dir_var, suffix_var, stream_output, custom_prompt_text): # Removed prompt_value_map and enable_pinyin parameters
    """Processes files based on GUI input and closes GUI."""
    files_input = files_list_var.get()
    if not files_input:
        tk.messagebox.showerror("Error", "Please select at least one file.")
        return
    class GUIArgs:
        pass
    gui_args = GUIArgs()
    gui_args.files = list(files_input)
    gui_args.language = "" # Language is not relevant anymore
    gui_args.engine = engine_var.get()
    gui_args.model = model_var.get() if model_var.get() else None # Get model from GUI, set to None if empty to use API default
    gui_args.prompt_key = "cleanup" # Always set prompt_key to "cleanup"
    gui_args.output = output_dir_var.get() if output_dir_var.get() else None
    gui_args.suffix = suffix_var.get()
    gui_args.stream_output_gui = stream_output # Pass stream_output from GUI
    gui_args.custom_prompt_text = custom_prompt_text.strip() # Get custom prompt text from GUI and strip whitespace
    gui_args.enable_pinyin_gui = False # enable_pinyin is now irrelevant, set to False

    window.destroy()
    gui_exit_code = process_files(gui_args, stream_output, gui_args.custom_prompt_text, enable_pinyin=False) # enable_pinyin is now irrelevant
    sys.exit(gui_exit_code) # Exit with code from file processing
if __name__ == "__main__":
    main()
