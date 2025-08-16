# --- START OF FILE GPTBatcher_Multimodal_Logged_v6.py ---

import os
import sys
import json
import requests # Make sure to install: pip install requests
import glob # For handling wildcard file paths
import time # For rate limiting, timestamps
import datetime # For timestamp formatting
import google.generativeai as genai # For Google Gemini API
from google.api_core.exceptions import GoogleAPIError, ResourceExhausted, PermissionDenied # For handling Google API exceptions
import argparse # For command-line argument parsing
import tkinter as tk
from tkinter import ttk
from tkinter import scrolledtext # Import scrolledtext for the prompt box
from tkinter import filedialog
import tkinter.messagebox
import tkinter.simpledialog # For API key input fallback
import base64 # For encoding images
import mimetypes # For guessing image MIME types
import traceback # For logging detailed exception info

################################################################################
# --- Customizable Variables (Configuration) ---
################################################################################

# 1. Google API Key Environment Variable Name
API_KEY_ENV_VAR_NAME = "GOOGLE_API_KEY"

# 1b. Ollama API Endpoint Configuration
OLLAMA_API_URL = os.environ.get("OLLAMA_API_URL", "http://localhost:11434") # Base URL
OLLAMA_TAGS_ENDPOINT = f"{OLLAMA_API_URL}/api/tags" # For fetching models
OLLAMA_GENERATE_ENDPOINT = f"{OLLAMA_API_URL}/api/generate" # For generation

# 2. Default User Prompt Template - **Generic for Text or Image**
USER_PROMPT_TEMPLATE = """Analyze the provided content (text or image).

If text is provided below: Summarize the key points, identify main topics, and suggest relevant keywords.
If an image is provided: Describe the image in detail, including objects, scene, actions, and overall mood. Suggest relevant keywords or tags for the image.

Provide the output as plain text.
"""

# 3. Supported File Types
SUPPORTED_TEXT_EXTENSIONS = ['.txt', '.srt', '.md', '.py', '.js', '.html', '.css']
SUPPORTED_IMAGE_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.webp', '.heic', '.heif']
ALL_SUPPORTED_EXTENSIONS = SUPPORTED_TEXT_EXTENSIONS + SUPPORTED_IMAGE_EXTENSIONS

# 4. Output file extensions
RAW_OUTPUT_FILE_EXTENSION = ".txt"
LOG_FILE_EXTENSION = ".log"
DEFAULT_RAW_OUTPUT_SUFFIX = "" # Suffix is blank for cleaner filenames

# 5. Default Models and Engine - Placeholders, will be updated dynamically
DEFAULT_GEMINI_MODEL = ""
DEFAULT_OLLAMA_MODEL = ""
DEFAULT_ENGINE = "google"

# 6. Rate Limiting Configuration (Google Gemini)
REQUESTS_PER_MINUTE = 15
REQUEST_INTERVAL_SECONDS = 60 / REQUESTS_PER_MINUTE

# 7. Output Subfolder Names
DEFAULT_OUTPUT_SUBFOLDER_NAME = "" # Default is blank to save next to input file
LOG_SUBFOLDER_NAME = "processing_logs" # Name of the dedicated log subfolder

################################################################################
# --- End of Customizable Variables ---
################################################################################

# Global variable for rate limiting
last_request_time = None

# --- Model Fetching Functions ---
# (fetch_google_models and fetch_ollama_models remain the same)
def fetch_google_models(api_key):
    """Fetches available 'generateContent' models from Google Generative AI."""
    if not api_key:
        return [], "API key not available."
    try:
        print("Fetching Google AI models...")
        genai.configure(api_key=api_key)
        models = []
        for m in genai.list_models():
             if "generateContent" in m.supported_generation_methods:
                 models.append(m.name)
        print(f"Found Google models (raw): {models}")
        # Prioritize pro/flash models in sorting
        models.sort(key=lambda x: (not ('pro' in x or 'flash' in x), x))
        print(f"Sorted Google models: {models}")
        return models, None
    except PermissionDenied:
         print("ERROR: Google API Permission Denied. Check your API key permissions.")
         return [], "Google API Permission Denied. Check API key permissions."
    except GoogleAPIError as e:
        print(f"ERROR fetching Google models: {e}")
        return [], f"Google API Error: {e}"
    except Exception as e:
        print(f"ERROR fetching Google models: {e}")
        return [], f"An unexpected error occurred: {e}"

def fetch_ollama_models():
    """Fetches available models from the Ollama API."""
    try:
        print(f"Fetching Ollama models from {OLLAMA_TAGS_ENDPOINT}...")
        response = requests.get(OLLAMA_TAGS_ENDPOINT, timeout=10)
        response.raise_for_status()
        data = response.json()
        if "models" in data and isinstance(data["models"], list):
             # Separate models with and without tags for better sorting
             models_with_tags = sorted([
                 model.get("name") for model in data["models"]
                 if model.get("name") and ':' in model.get("name")
             ])
             models_without_tags = sorted([
                 model.get("name") for model in data["models"]
                 if model.get("name") and ':' not in model.get("name")
             ])
             model_names = models_with_tags + models_without_tags # List base models last
             print(f"Found Ollama models: {model_names}")
             return model_names, None
        else:
             print("ERROR: Unexpected response format from Ollama API.")
             return [], "Unexpected response format from Ollama."
    except requests.exceptions.ConnectionError:
        print(f"ERROR: Could not connect to Ollama API at {OLLAMA_API_URL}. Is Ollama running?")
        return [], f"Connection Error: Is Ollama running at {OLLAMA_API_URL}?"
    except requests.exceptions.Timeout:
         print(f"ERROR: Timeout connecting to Ollama API at {OLLAMA_TAGS_ENDPOINT}.")
         return [], "Timeout connecting to Ollama."
    except requests.exceptions.RequestException as e:
        print(f"ERROR fetching Ollama models: {e}")
        return [], f"Ollama Request Error: {e}"
    except json.JSONDecodeError:
         print("ERROR: Could not decode JSON response from Ollama API.")
         return [], "Invalid JSON response from Ollama."
    except Exception as e:
        print(f"ERROR fetching Ollama models: {e}")
        return [], f"An unexpected error occurred: {e}"


# --- Helper Functions ---
# (read_file_content remains the same)
def read_file_content(filepath):
    """
    Reads file content based on extension.
    Returns (content, mime_type, is_image, error_message)
    """
    _, extension = os.path.splitext(filepath)
    extension = extension.lower()

    if extension in SUPPORTED_TEXT_EXTENSIONS:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read(), 'text/plain', False, None
        except FileNotFoundError:
            return None, None, False, f"Error: File not found at {filepath}"
        except Exception as e:
            return None, None, False, f"Error reading text file {filepath}: {e}"
    elif extension in SUPPORTED_IMAGE_EXTENSIONS:
        mime_type, _ = mimetypes.guess_type(filepath)
        if not mime_type:
            print(f"Warning: Could not determine MIME type for {filepath}. Assuming 'application/octet-stream'.")
            mime_type = 'application/octet-stream'

        try:
            with open(filepath, 'rb') as f:
                return f.read(), mime_type, True, None
        except FileNotFoundError:
            return None, None, False, f"Error: File not found at {filepath}"
        except Exception as e:
            return None, None, False, f"Error reading image file {filepath}: {e}"
    else:
        return None, None, False, f"Error: Unsupported file extension '{extension}' for {filepath}"

# --- API Call Functions ---
# (call_generative_ai_api, call_google_gemini_api, call_ollama_api remain the same)
def call_generative_ai_api(engine, prompt_text, api_key, model_name,
                           image_bytes=None, mime_type=None, stream_output=False):
    """Calls the selected AI API (Google or Ollama) to get content, handling multimodal."""
    if engine == "google":
        return call_google_gemini_api(prompt_text, api_key, model_name, image_bytes, mime_type, stream_output)
    elif engine == "ollama":
        return call_ollama_api(prompt_text, model_name, image_bytes)
    else:
        print(f"Error: Unknown engine '{engine}'")
        return f"Error: Unknown engine '{engine}'"

def call_google_gemini_api(prompt_text, api_key, model_name,
                            image_bytes=None, mime_type=None, stream_output=False):
    """Calls the Google Generative AI API, supporting text and image input."""
    global last_request_time
    if not api_key:
        return "Error: Google API Key not configured."
    if not model_name:
        return "Error: No Google model selected or available."

    try:
        genai.configure(api_key=api_key)
        safety_settings=[
            {"category": "HARM_CATEGORY_HARASSMENT","threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH","threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT","threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT","threshold": "BLOCK_MEDIUM_AND_ABOVE"}
        ]
        model = genai.GenerativeModel(model_name, safety_settings=safety_settings)

        # Rate Limiting
        current_time = time.time()
        if last_request_time is not None:
            time_since_last_request = current_time - last_request_time
            if time_since_last_request < REQUEST_INTERVAL_SECONDS:
                sleep_duration = REQUEST_INTERVAL_SECONDS - time_since_last_request
                print(f"Rate limit active (Google Gemini). Sleeping for {sleep_duration:.2f} seconds...")
                time.sleep(sleep_duration)
        last_request_time = time.time()

        # Construct Request Payload
        request_payload = []
        if image_bytes and mime_type:
            print(f"--- Preparing multimodal request for Google Gemini (Model: {model_name}) ---")
            print(f"Prompt Text: {prompt_text[:200]}...")
            print(f"Image MIME Type: {mime_type}, Size: {len(image_bytes)} bytes")
            if "vision" not in model_name and "1.5" not in model_name:
                 print(f"Warning: Selected model '{model_name}' might not be optimized for vision tasks.")
            try:
                request_payload = [
                    prompt_text,
                    {"inline_data": {"mime_type": mime_type, "data": image_bytes}}
                ]
            except Exception as e:
                 print(f"Error preparing image for Google API: {e}")
                 return f"Error: Failed to prepare image data - {e}"
        else:
            print("--- Preparing text-only request for Google Gemini (Model: {}): ---".format(model_name))
            print(prompt_text[:1000] + "..." if len(prompt_text) > 1000 else prompt_text)
            print("--- End of Prompt Snippet ---")
            request_payload = [prompt_text]

        print(f"--- Calling Google Gemini API with model '{model_name}'... {'Streaming enabled' if stream_output else '(Non-streaming)'} ---")
        generation_config = genai.types.GenerationConfig()

        # API Call and Response Handling
        api_response_text = ""
        try:
            if stream_output:
                response = model.generate_content(request_payload, generation_config=generation_config, stream=True)
                full_response_text = ""
                print("\n--- Streaming Response ---")
                for chunk in response:
                    if chunk.parts:
                        print(chunk.text, end="", flush=True)
                        full_response_text += chunk.text
                    if hasattr(chunk, 'prompt_feedback') and chunk.prompt_feedback and chunk.prompt_feedback.block_reason:
                        block_reason = chunk.prompt_feedback.block_reason
                        print(f"\nERROR: Stream interrupted by safety filter ({block_reason}).")
                        return f"Error: Stream blocked by safety filter ({block_reason})."
                print("\n--- End of Stream ---")
                api_response_text = full_response_text.strip()
            else: # Non-streaming
                response = model.generate_content(request_payload, generation_config=generation_config, stream=False)
                print("\n--- Google Gemini API call completed (non-streaming). ---")

                if hasattr(response, 'prompt_feedback') and response.prompt_feedback and response.prompt_feedback.block_reason:
                     block_reason = response.prompt_feedback.block_reason
                     print(f"ERROR: Input prompt blocked due to: {block_reason}")
                     return f"Error: Prompt blocked by safety filter ({block_reason})."

                if not hasattr(response, 'candidates') or not response.candidates:
                     block_reason = getattr(getattr(response, 'prompt_feedback', None), 'block_reason', 'Unknown')
                     print(f"ERROR: No candidates found in response (Reason: {block_reason}).")
                     return f"Error: No response generated (Reason: {block_reason})."

                candidate = response.candidates[0]
                finish_reason = getattr(candidate, 'finish_reason', 'UNKNOWN')
                safety_ratings = getattr(candidate, 'safety_ratings', None)

                if finish_reason != 'STOP':
                    print(f"WARNING: Generation finished unexpectedly: {finish_reason}")
                    if finish_reason == 'SAFETY':
                        print(f"Safety Ratings: {safety_ratings}")
                        return f"Error: Response generation stopped due to safety ({finish_reason})."
                    try:
                        api_response_text = response.text
                        print(f"Warning: Generation stopped early ({finish_reason}), partial text retrieved.")
                    except (ValueError, AttributeError) as e:
                         print(f"Error accessing partial text after non-STOP finish ({finish_reason}): {e}")
                         return f"Error: Generation stopped ({finish_reason}), couldn't retrieve text."
                else: # Finish reason is STOP
                     try:
                        api_response_text = response.text
                     except (ValueError, AttributeError) as e:
                          block_reason = getattr(getattr(response, 'prompt_feedback', None), 'block_reason', None)
                          if block_reason:
                              print(f"Error accessing text despite STOP (Prompt Block Reason: {block_reason}): {e}")
                              return f"Error: No text content found (Prompt Block Reason: {block_reason})."
                          else:
                              print(f"Error accessing response text despite STOP reason: {e}. Finish Reason: {finish_reason}")
                              return f"Error: Could not retrieve text from response (Finish Reason: {finish_reason})."
        except Exception as e:
            print(f"Error during Gemini content generation: {e}", file=sys.stderr)
            return f"Error: Gemini generation failed - {str(e)[:150]}"

        if api_response_text is None: api_response_text = ""
        return api_response_text.strip()
    except ResourceExhausted as e:
        print(f"Error: Google Gemini API Quota Exhausted.", file=sys.stderr)
        return "Error: Google API Quota Exhausted."
    except PermissionDenied as e:
        print(f"Error: Google API Permission Denied. Check API Key.", file=sys.stderr)
        return "Error: Google API Permission Denied (Check Key)."
    except GoogleAPIError as e:
         print(f"Error configuring or calling Google Gemini API: {e}", file=sys.stderr)
         return f"Error: Google API Call Failed - {str(e)[:100]}"
    except Exception as e:
        print(f"Unexpected error in Google API setup or call: {e}", file=sys.stderr)
        traceback.print_exc()
        return f"Error: Unexpected Google API issue - {str(e)[:100]}"

def call_ollama_api(prompt_text, model_name, image_bytes=None):
    """Calls the local Ollama API, supporting text and image input (e.g., for llava)."""
    payload = {
        "model": model_name,
        "prompt": prompt_text,
        "stream": False
    }
    if image_bytes:
        print(f"--- Preparing multimodal request for Ollama (Model: {model_name}) ---")
        print(f"Prompt Text: {prompt_text[:200]}...")
        print(f"Image Size: {len(image_bytes)} bytes")
        if "llava" not in model_name:
            print(f"Warning: Selected Ollama model '{model_name}' might not support images.")
        try:
            encoded_image = base64.b64encode(image_bytes).decode('utf-8')
            payload["images"] = [encoded_image]
        except Exception as e:
            print(f"Error encoding image for Ollama API: {e}")
            return f"Error: Failed to encode image data - {e}"
    else:
         print(f"--- Preparing text-only request for Ollama ({model_name}) ---")
         print(f"--- Prompt Snippet: {prompt_text[:500]}... ---")
    try:
        print(f"--- Calling Ollama API ({model_name}) at {OLLAMA_GENERATE_ENDPOINT} ---")
        response = requests.post(OLLAMA_GENERATE_ENDPOINT, json=payload, timeout=600)
        response.raise_for_status()
        data = response.json()
        print("--- Ollama API call completed. ---")
        if "response" in data:
            return data["response"].strip() if data["response"] else ""
        elif "error" in data:
             error_msg = data['error']
             print(f"ERROR from Ollama API: {error_msg}")
             return f"Error: Ollama API returned an error - {error_msg}"
        else:
             print(f"ERROR: Unexpected response structure from Ollama: {data}")
             return "Error: Unexpected response format from Ollama (missing 'response' or 'error')."
    except requests.exceptions.ConnectionError as e:
        print(f"ERROR: Could not connect to Ollama API at {OLLAMA_GENERATE_ENDPOINT}. Is Ollama running?")
        return f"Error: Could not connect to Ollama API at {OLLAMA_API_URL} - {e}"
    except requests.exceptions.Timeout as e:
         print(f"ERROR: Timeout during Ollama generation ({model_name}).")
         return f"Error: Ollama generation timed out ({model_name}) - {e}"
    except requests.exceptions.HTTPError as e:
         error_details = f"HTTP Error {e.response.status_code} calling Ollama generate API: {e}"
         try:
             error_body = e.response.json()
             error_details += f" - Ollama Error: {error_body.get('error', e.response.text[:200])}"
         except json.JSONDecodeError:
             error_details += f" - Response: {e.response.text[:200]}"
         print(error_details)
         return f"Error: Ollama Request Failed ({error_details})"
    except requests.exceptions.RequestException as e:
        print(f"ERROR calling Ollama generate API: {e}")
        return f"Error: Ollama Request Failed - {e}"
    except json.JSONDecodeError as e:
         print(f"ERROR: Could not decode JSON response from Ollama generate API: {e}")
         return f"Error: Invalid JSON response from Ollama - {e}"
    except Exception as e:
        print(f"Unexpected ERROR calling Ollama generate API: {e}")
        traceback.print_exc()
        return f"Error: Unexpected Ollama Call Failed - {e}"


# --- Output & Logging Functions ---

def determine_unique_output_paths(input_filepath, output_suffix, output_folder, log_folder):
    """
    Generates unique, full file paths for the raw output and log file.
    If a file exists, it appends a counter like ' (1)', ' (2)', etc.
    Returns (unique_raw_output_path, unique_log_path)
    """
    base_name = os.path.splitext(os.path.basename(input_filepath))[0]

    # MODIFIED: Removed the sanitization line to preserve original filenames.
    # sanitized_base_name = "".join(c if c.isalnum() or c in ('_', '-') else '_' for c in base_name)

    # Use the original base_name directly
    output_filename_base = f"{base_name}{output_suffix}"

    ideal_raw_path = os.path.join(output_folder, f"{output_filename_base}{RAW_OUTPUT_FILE_EXTENSION}")
    ideal_log_path = os.path.join(log_folder, f"{output_filename_base}{LOG_FILE_EXTENSION}")

    if not os.path.exists(ideal_raw_path) and not os.path.exists(ideal_log_path):
        return ideal_raw_path, ideal_log_path

    counter = 1
    while True:
        new_base = f"{output_filename_base} ({counter})"
        new_raw_path = os.path.join(output_folder, f"{new_base}{RAW_OUTPUT_FILE_EXTENSION}")
        new_log_path = os.path.join(log_folder, f"{new_base}{LOG_FILE_EXTENSION}")
        if not os.path.exists(new_raw_path) and not os.path.exists(new_log_path):
            return new_raw_path, new_log_path
        counter += 1

def save_raw_api_response(api_response_text, output_filepath):
    """Saves the raw API response text to the specified file path."""
    if api_response_text is None:
         api_response_text = "[Error: API response was None]"
         print("Debug: save_raw_api_response - API response was None, saving placeholder.")
    elif not api_response_text:
         api_response_text = "[Info: API response was empty]"
         print("Debug: save_raw_api_response - API response was empty, saving placeholder.")
    try:
        with open(output_filepath, 'w', encoding='utf-8') as outfile:
            outfile.write(api_response_text)
    except Exception as e:
        print(f"**ERROR: Could not save raw API response to file: {output_filepath}**\nError details: {e}")

def save_processing_log(log_data, log_filepath):
    """Saves the processing parameters and outcome to the specified log file path."""
    timestamp_format = "%Y-%m-%d %H:%M:%S"
    log_folder = os.path.dirname(log_filepath)
    try:
        with open(log_filepath, 'w', encoding='utf-8') as logfile:
            logfile.write("="*20 + " Processing Log " + "="*20 + "\n")
            logfile.write(f"Input File: {log_data.get('input_filepath', 'N/A')}\n")
            logfile.write(f"Processing Start: {log_data.get('start_time').strftime(timestamp_format) if log_data.get('start_time') else 'N/A'}\n")
            logfile.write(f"Processing End:   {log_data.get('end_time').strftime(timestamp_format) if log_data.get('end_time') else 'N/A'}\n")
            logfile.write(f"Duration: {log_data.get('duration', -1):.2f} seconds\n")
            logfile.write("-"*50 + "\n")
            logfile.write("Parameters:\n")
            logfile.write(f"  Engine: {log_data.get('engine', 'N/A')}\n")
            logfile.write(f"  Model: {log_data.get('model_name', 'N/A')}\n")
            logfile.write(f"  Google API Key Status: {'Provided' if log_data.get('api_key_provided') else 'Not Provided'}\n")
            logfile.write(f"  Input Type: {'Image' if log_data.get('is_image') else 'Text'}\n")
            if log_data.get('is_image'):
                logfile.write(f"  Image MIME Type: {log_data.get('mime_type', 'N/A')}\n")
                logfile.write(f"  Image Size (bytes): {log_data.get('image_size', 'N/A')}\n")
            logfile.write(f"  Streaming Enabled: {log_data.get('stream_output', 'N/A')}\n")
            logfile.write(f"  Output Directory (Raw Files): {log_data.get('output_folder', 'N/A')}\n")
            logfile.write(f"  Log Directory: {log_folder}\n")
            logfile.write(f"  Output Suffix: '{log_data.get('output_suffix', 'N/A')}'\n")
            logfile.write(f"  Raw Output File: {log_data.get('raw_output_filename', 'N/A')}\n")
            logfile.write(f"  Log File: {os.path.basename(log_filepath)}\n")
            logfile.write("-"*50 + "\n")
            logfile.write("Prompt Sent to API:\n")
            logfile.write(log_data.get('prompt_sent', '[Prompt not captured]'))
            logfile.write("\n" + "-"*50 + "\n")
            logfile.write("Outcome:\n")
            logfile.write(f"  Status: {log_data.get('status', 'Unknown')}\n")
            if log_data.get('status', 'Unknown') == 'Failure':
                logfile.write(f"  Error Message: {log_data.get('error_message', 'No specific error message.')}\n")
                if log_data.get('traceback_info'):
                    logfile.write(f"  Traceback:\n{log_data.get('traceback_info')}\n")
            logfile.write("="*56 + "\n")
        raw_output_full_path = os.path.join(log_data.get('output_folder', 'N/A'), log_data.get('raw_output_filename', 'N/A'))
        print(f"Processing log saved to: {log_filepath}")
        print(f"Raw API response saved to: {raw_output_full_path}")
    except Exception as e:
        print(f"**ERROR: Could not save processing log file: {log_filepath}**\nError details: {e}")


# --- Core Processing ---
# (process_single_file is unchanged from v5)
def process_single_file(input_filepath, api_key, engine, user_prompt_template, model_name,
                        stream_output, output_suffix, output_folder, log_folder):
    """
    Processes a single input file, calls the API, saves raw output and a detailed log file.
    Returns (generated_content, error_message) where generated_content is None on failure.
    """
    start_time = datetime.datetime.now()
    raw_output_filepath, log_filepath = determine_unique_output_paths(
        input_filepath, output_suffix, output_folder, log_folder
    )
    log_data = {
        'input_filepath': input_filepath,
        'start_time': start_time,
        'engine': engine,
        'model_name': model_name,
        'api_key_provided': bool(api_key),
        'stream_output': stream_output,
        'output_suffix': output_suffix,
        'output_folder': output_folder,
        'status': 'Failure',
        'error_message': None,
        'traceback_info': None,
        'prompt_sent': None,
        'raw_output_filename': os.path.basename(raw_output_filepath),
        'end_time': None,
        'duration': -1,
    }
    api_response_text = None
    generated_content = None
    try:
        print(f"--- Reading file: {input_filepath} ---")
        content_data, mime_type, is_image, read_error_msg = read_file_content(input_filepath)
        if read_error_msg:
            print(read_error_msg)
            log_data['status'] = 'Failure'
            log_data['error_message'] = f"File Read Error: {read_error_msg}"
            save_raw_api_response(log_data['error_message'], raw_output_filepath)
            raise Exception(log_data['error_message'])
        log_data['is_image'] = is_image
        log_data['mime_type'] = mime_type
        prompt_for_api = user_prompt_template
        image_bytes_for_api = None
        if is_image:
            print(f"Type: Image ({mime_type})")
            image_bytes_for_api = content_data
            log_data['image_size'] = len(content_data) if content_data else 0
            log_data['prompt_sent'] = prompt_for_api
        else:
            print("Type: Text")
            file_content_str = content_data if content_data else " [File was empty or could not be read fully]"
            prompt_for_api += f"\n\n--- File Content Start ---\n{file_content_str}\n--- File Content End ---"
            log_data['prompt_sent'] = prompt_for_api
        api_response_text = call_generative_ai_api(
            engine=engine,
            prompt_text=prompt_for_api,
            api_key=api_key,
            model_name=model_name,
            image_bytes=image_bytes_for_api,
            mime_type=mime_type,
            stream_output=stream_output and engine == 'google'
        )
        save_raw_api_response(api_response_text, raw_output_filepath)
        if api_response_text is None or api_response_text.startswith("Error:"):
            error_detail = api_response_text if api_response_text else "API call returned None or Empty."
            print(f"API Call Failed: {error_detail}")
            log_data['status'] = 'Failure'
            log_data['error_message'] = error_detail
            generated_content = None
        else:
            log_data['status'] = 'Success'
            log_data['error_message'] = None
            generated_content = api_response_text
    except Exception as e:
        print(f"**ERROR during processing {input_filepath}: {e}**")
        log_data['status'] = 'Failure'
        if not log_data.get('error_message'):
             log_data['error_message'] = f"Processing Exception: {str(e)}"
        log_data['traceback_info'] = traceback.format_exc()
        if api_response_text is None:
             error_content = f"[ERROR] {log_data['error_message']}\n\n{log_data['traceback_info']}"
             save_raw_api_response(error_content, raw_output_filepath)
        generated_content = None
    finally:
        end_time = datetime.datetime.now()
        log_data['end_time'] = end_time
        log_data['duration'] = (end_time - start_time).total_seconds()
        save_processing_log(log_data, log_filepath)
        return generated_content, log_data.get('error_message')


# --- API Key Handling ---
# (get_api_key remains the same)
def get_api_key(force_gui=False):
    """Gets the Google API key from env var or prompts the user via GUI."""
    api_key = os.environ.get(API_KEY_ENV_VAR_NAME)
    if not api_key or force_gui:
        if not force_gui:
            print(f"INFO: {API_KEY_ENV_VAR_NAME} environment variable not set or empty.")
        else:
            print("INFO: Forcing GUI prompt for API Key.")
        temp_root = None
        if not tk._default_root:
             temp_root = tk.Tk()
             temp_root.withdraw()
        try:
             api_key = tk.simpledialog.askstring(
                 "API Key Required",
                 f"Please enter your Google API Key (required for 'google' engine):",
                 show='*'
             )
        finally:
             if temp_root:
                 temp_root.destroy()
        if not api_key:
            print("ERROR: Google API Key not provided via prompt.")
            return None
        else:
            print("INFO: API Key obtained via GUI prompt.")
    return api_key

# --- GUI Implementation ---
# (ArgsWrapper, use_gui, add_files_to_list, remove_selected_files are unchanged from v5)
class ArgsWrapper:
    def __init__(self):
        self.model = None
        self.engine = DEFAULT_ENGINE
        self.output = DEFAULT_OUTPUT_SUBFOLDER_NAME
        self.suffix = DEFAULT_RAW_OUTPUT_SUFFIX
        self.stream = False
        self.files = []

def use_gui(initial_api_key, command_line_files=None, args=None):
    """Launches a tkinter GUI for script options, with dynamic model loading."""
    window = tk.Tk()
    window.title("Multimodal AI Batch Processor")
    current_api_key = {'key': initial_api_key}
    settings = {}
    files_list_var = tk.Variable(value=list(command_line_files) if command_line_files else [])
    engine_var = tk.StringVar(value=args.engine if args else DEFAULT_ENGINE)
    model_var = tk.StringVar()
    output_dir_var = tk.StringVar(value=args.output if args else DEFAULT_OUTPUT_SUBFOLDER_NAME)
    suffix_var = tk.StringVar(value=args.suffix if args else DEFAULT_RAW_OUTPUT_SUFFIX)
    stream_output_var = tk.BooleanVar(value=args.stream if args else False)
    current_row = 0
    def re_prompt_api_key():
         new_key = get_api_key(force_gui=True)
         if new_key:
             current_api_key['key'] = new_key
             api_key_status_label.config(text="API Key Status: Set (via prompt)")
             if engine_var.get() == 'google': update_models(args if args else ArgsWrapper())
         else:
             api_key_status_label.config(text="API Key Status: NOT Set")
    api_key_frame = ttk.Frame(window, padding="5 5 5 0"); api_key_frame.grid(row=current_row, column=0, columnspan=3, sticky=(tk.W, tk.E))
    api_key_status_label = tk.Label(api_key_frame, text=f"API Key Status: {'Set' if initial_api_key else 'Not Set'}")
    api_key_status_label.pack(side=tk.LEFT, padx=5)
    ttk.Button(api_key_frame, text="Enter/Update Google API Key", command=re_prompt_api_key).pack(side=tk.LEFT, padx=5)
    current_row += 1
    files_frame = ttk.LabelFrame(window, text="Input Files (Text or Images)", padding="10 10 10 10"); files_frame.grid(row=current_row, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5); files_frame.columnconfigure(0, weight=1); current_row += 1
    file_listbox = tk.Listbox(files_frame, listvariable=files_list_var, height=6, width=70, selectmode=tk.EXTENDED); file_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    files_scrollbar = ttk.Scrollbar(files_frame, orient=tk.VERTICAL, command=file_listbox.yview); files_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S)); file_listbox.config(yscrollcommand=files_scrollbar.set)
    file_buttons_frame = ttk.Frame(files_frame); file_buttons_frame.grid(row=0, column=2, sticky=(tk.N, tk.S), padx=(5,0))
    tk.Button(file_buttons_frame, text="Add Files...", command=lambda: add_files_to_list(files_list_var, file_listbox, window)).pack(fill=tk.X, pady=2)
    tk.Button(file_buttons_frame, text="Clear All", command=lambda: files_list_var.set([]), width=10).pack(fill=tk.X, pady=2)
    tk.Button(file_buttons_frame, text="Remove Sel.", command=lambda: remove_selected_files(files_list_var, file_listbox), width=10).pack(fill=tk.X, pady=2)
    prompt_frame = ttk.LabelFrame(window, text="User Prompt (Adapt for Text vs. Image Analysis)", padding="10 10 10 10"); prompt_frame.grid(row=current_row, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5); prompt_frame.columnconfigure(0, weight=1); current_row += 1
    prompt_text_widget = scrolledtext.ScrolledText(prompt_frame, wrap=tk.WORD, width=80, height=10, relief=tk.SOLID, borderwidth=1); prompt_text_widget.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S)); prompt_text_widget.insert(tk.INSERT, USER_PROMPT_TEMPLATE)
    options_frame = ttk.Frame(window, padding="10 10 10 10"); options_frame.grid(row=current_row, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S)); options_frame.columnconfigure(1, weight=1); current_row += 1
    tk.Label(options_frame, text="AI Engine:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
    engine_options = ['google', 'ollama']; engine_combo = ttk.Combobox(options_frame, textvariable=engine_var, values=engine_options, state="readonly", width=35); engine_combo.grid(row=0, column=1, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=2)
    tk.Label(options_frame, text="Model:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
    model_combo = ttk.Combobox(options_frame, textvariable=model_var, state="disabled", width=35); model_combo.grid(row=1, column=1, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=2)
    tk.Label(options_frame, text="(Select multimodal model like 'gemini-1.5-pro' or 'llava' for images)", font=('TkDefaultFont', 8)).grid(row=2, column=1, columnspan=2, sticky=tk.W, padx=5)
    settings_frame = ttk.Frame(window, padding="10 10 10 10"); settings_frame.grid(row=current_row, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S)); settings_frame.columnconfigure(1, weight=1); current_row += 1
    tk.Label(settings_frame, text="Output Dir:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2); output_entry = ttk.Entry(settings_frame, textvariable=output_dir_var, width=40); output_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=2)
    tk.Button(settings_frame, text="Browse...", command=lambda: output_dir_var.set(filedialog.askdirectory(initialdir=os.getcwd(), parent=window) or output_dir_var.get())).grid(row=0, column=2, sticky=tk.E, padx=5)
    tk.Label(settings_frame, text="Output Suffix:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2); suffix_entry = ttk.Entry(settings_frame, textvariable=suffix_var, width=20); suffix_entry.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
    stream_check = ttk.Checkbutton(settings_frame, text="Stream Output (Google Engine Only / Experimental)", variable=stream_output_var); stream_check.grid(row=2, column=1, columnspan=2, sticky=tk.W, padx=5, pady=5)
    def update_models(cmd_line_args, *trace_details):
        print(f"Updating models for engine: {engine_var.get()}...")
        selected_engine = engine_var.get(); models = []; error_msg = None
        model_combo.set('Fetching...'); model_combo.configure(state="disabled"); window.update_idletasks()
        if selected_engine == "google":
            if not current_api_key['key']: error_msg = "Google API Key needed."
            else: models, error_msg = fetch_google_models(current_api_key['key'])
        elif selected_engine == "ollama": models, error_msg = fetch_ollama_models()
        if error_msg: model_combo.set(f"Error: {error_msg}"); model_var.set(""); model_combo.configure(state="disabled")
        elif models:
            model_combo['values'] = models; model_combo.configure(state="readonly")
            default_to_set = ""; model_to_check = getattr(cmd_line_args, 'model', None)
            if model_to_check and model_to_check in models: default_to_set = model_to_check
            elif models: default_to_set = models[0]
            model_var.set(default_to_set)
            if not default_to_set: model_combo.set("Select a model")
        else: model_combo.set("No models found"); model_var.set(""); model_combo.configure(state="disabled")
        print("Model update complete.")
    effective_args = args if args is not None else ArgsWrapper()
    engine_var.trace_add("write", lambda *trace: update_models(effective_args, *trace))
    window.after(150, lambda: update_models(effective_args))
    def process_from_gui():
        settings['files'] = list(files_list_var.get())
        settings['custom_prompt'] = prompt_text_widget.get("1.0", tk.END).strip()
        settings['engine'] = engine_var.get()
        settings['model'] = model_var.get()
        settings['output_dir'] = output_dir_var.get()
        settings['suffix'] = suffix_var.get()
        settings['stream_output'] = stream_output_var.get()
        settings['api_key'] = current_api_key['key']
        if not settings['files']: tkinter.messagebox.showwarning("Input Error", "Please add at least one input file.", parent=window); return None
        if not settings['custom_prompt']:
             if not tkinter.messagebox.askyesno("Prompt Warning", "The custom prompt is empty. Proceed anyway?", parent=window): return None
        selected_model = settings['model']
        if not selected_model or selected_model.startswith("Error:") or selected_model in ["No models found", "Fetching...", "Select a model"]:
             tkinter.messagebox.showwarning("Input Error", "Please select a valid model.", parent=window); return None
        if settings['engine'] == 'google' and not settings['api_key']:
            tkinter.messagebox.showwarning("Input Error", "Google engine selected, but API Key is missing.", parent=window); return None
        window.destroy(); window.quit(); return settings
    process_button = ttk.Button(window, text="Process Selected Files", command=process_from_gui); process_button.grid(row=current_row, column=0, columnspan=3, pady=20); current_row += 1
    window.columnconfigure(0, weight=1); window.rowconfigure(1, weight=1); window.rowconfigure(2, weight=1)
    window.mainloop()
    return settings if 'files' in settings else None

def add_files_to_list(files_list_var, file_listbox, window):
    """Adds selected files (text and images) to the listbox."""
    file_types = [("Supported Files", " ".join("*" + ext for ext in ALL_SUPPORTED_EXTENSIONS)), ("Text Files", " ".join("*" + ext for ext in SUPPORTED_TEXT_EXTENSIONS)), ("Image Files", " ".join("*" + ext for ext in SUPPORTED_IMAGE_EXTENSIONS)), ("All Files", "*.*")]
    selected_files = filedialog.askopenfilenames(parent=window, title="Select Input Files (Text or Images)", filetypes=file_types)
    if selected_files:
        current_files = list(files_list_var.get()); added_count = 0; newly_added_paths = []
        for f_raw in selected_files:
            f_normalized = os.path.normpath(f_raw).replace("\\", "/")
            if f_normalized not in current_files:
                 base_f = os.path.basename(f_normalized)
                 already_exists = any(os.path.basename(existing) == base_f for existing in current_files)
                 if not already_exists:
                     current_files.append(f_normalized); newly_added_paths.append(f_normalized); added_count += 1
        if added_count > 0:
            current_files.sort(); files_list_var.set(tuple(current_files))
            try: file_listbox.see(current_files.index(newly_added_paths[-1]))
            except (ValueError, IndexError): file_listbox.see(tk.END)
            print(f"Added {added_count} new unique file(s).")
        else: print("No new unique files were added.")

def remove_selected_files(files_list_var, file_listbox):
     """Removes selected items from the listbox."""
     selected_indices = file_listbox.curselection()
     if not selected_indices: print("No files selected to remove."); return
     current_files = list(files_list_var.get()); removed_count = 0
     for i in sorted(selected_indices, reverse=True):
         try: removed_item = current_files.pop(i); removed_count += 1
         except IndexError: print(f"Warning: Index {i} out of bounds during removal.")
     if removed_count > 0: files_list_var.set(tuple(current_files)); print(f"Removed {removed_count} file(s).")

# --- Main Execution ---

def main():
    initial_api_key = get_api_key(force_gui=False)

    parser = argparse.ArgumentParser(description="Multimodal AI Batch Processor - Process text/image files using AI")
    parser.add_argument("files", nargs="*", help=f"Path(s) to input file(s). Supports patterns and extensions like {', '.join(ALL_SUPPORTED_EXTENSIONS)}. If none provided, scans current directory.")
    parser.add_argument("-o", "--output", default=DEFAULT_OUTPUT_SUBFOLDER_NAME, help=f"Subfolder for output. Default: (save next to input file). Logs go in a '{LOG_SUBFOLDER_NAME}' sub-subfolder.")
    parser.add_argument("-s", "--suffix", default=DEFAULT_RAW_OUTPUT_SUFFIX, help=f"Suffix for output filenames. Default: (none).")
    parser.add_argument("--stream", action='store_true', default=False, help="Enable streaming output (Google Engine Only / Experimental).")
    parser.add_argument("-e", "--engine", default=DEFAULT_ENGINE, choices=['google', 'ollama'], help=f"AI engine to use. Default: '{DEFAULT_ENGINE}'.")
    parser.add_argument("-m", "--model", dest="model", default=None, help="Suggest a model to select by default in GUI.")
    args = parser.parse_args()

    filepaths_from_cli = []
    if args.files:
        print("Expanding file patterns from command line...")
        for pattern in args.files:
            try:
                expanded_files = glob.glob(pattern, recursive=True)
                valid_files = [os.path.normpath(f).replace("\\", "/") for f in expanded_files if os.path.isfile(f) and os.path.splitext(f)[1].lower() in ALL_SUPPORTED_EXTENSIONS]
                if valid_files:
                     filepaths_from_cli.extend(valid_files)
            except Exception as e: print(f"Error processing pattern '{pattern}': {e}")
        filepaths_from_cli = sorted(list(set(filepaths_from_cli)))

    if not filepaths_from_cli and not args.files:
        print("\nINFO: No input files specified. Scanning current directory for supported files...")
        current_dir = os.getcwd()
        try:
            scanned_files = [os.path.normpath(os.path.join(current_dir, entry)).replace("\\", "/") for entry in os.listdir(current_dir) if os.path.isfile(os.path.join(current_dir, entry)) and os.path.splitext(entry)[1].lower() in ALL_SUPPORTED_EXTENSIONS]
            if scanned_files:
                scanned_files.sort()
                print(f"Found {len(scanned_files)} supported files in the current directory.")
                filepaths_from_cli = scanned_files
                args.files = filepaths_from_cli
            else:
                print("No supported files found in the current directory.")
        except OSError as e:
            print(f"Warning: Could not scan directory '{current_dir}': {e}")

    if filepaths_from_cli:
        print(f"Prepared {len(filepaths_from_cli)} file(s) for processing.")
        args.files = filepaths_from_cli

    gui_settings = use_gui(initial_api_key=initial_api_key, command_line_files=filepaths_from_cli, args=args)
    if not gui_settings: print("Operation cancelled or GUI closed."); return

    input_file_paths_gui = gui_settings.get('files', [])
    custom_prompt_template = gui_settings.get('custom_prompt', USER_PROMPT_TEMPLATE)
    output_folder_base = gui_settings.get('output_dir', DEFAULT_OUTPUT_SUBFOLDER_NAME)
    suffix = gui_settings.get('suffix', DEFAULT_RAW_OUTPUT_SUFFIX)
    stream_output = gui_settings.get('stream_output', False)
    engine = gui_settings.get('engine', DEFAULT_ENGINE)
    model_name = gui_settings.get('model')
    final_api_key = gui_settings.get('api_key')

    if not input_file_paths_gui: print("Error: No input files selected for processing."); return
    if not model_name: print("Error: No model selected."); return
    if engine == 'google' and not final_api_key: print("Error: Google engine selected, but final API Key is missing."); return

    all_input_filepaths = sorted(list(set(input_file_paths_gui)))
    if not all_input_filepaths: print("Error: No valid input file paths specified."); return

    central_output_folder = None
    if output_folder_base:
        central_output_folder = os.path.join(os.getcwd(), output_folder_base)
        # We don't need to create the log folder here, it will be done per-file if needed
    else:
        print("\nINFO: No output subfolder specified. Output will be saved next to input files.")

    processed_files = 0; failed_files = 0; total_files = len(all_input_filepaths)
    created_log_dirs = set() # Keep track of which log directories we've already created
    print(f"\nStarting batch processing for {total_files} file(s)...")
    print(f"Engine: {engine}, Model: {model_name}")
    print("-" * 50)

    for i, input_filepath in enumerate(all_input_filepaths):
        print(f"\n--- Processing file {i + 1}/{total_files} ---")

        output_folder_for_this_file = None
        log_folder_for_this_file = None

        if central_output_folder:
            output_folder_for_this_file = central_output_folder
            log_folder_for_this_file = os.path.join(central_output_folder, LOG_SUBFOLDER_NAME)
        else:
            input_dir = os.path.dirname(os.path.abspath(input_filepath))
            output_folder_for_this_file = input_dir
            log_folder_for_this_file = os.path.join(input_dir, LOG_SUBFOLDER_NAME)

        if log_folder_for_this_file not in created_log_dirs:
            try:
                os.makedirs(log_folder_for_this_file, exist_ok=True)
                print(f"Ensured log directory exists: {log_folder_for_this_file}")
                created_log_dirs.add(log_folder_for_this_file)
            except OSError as e:
                print(f"**ERROR: Could not create log directory '{log_folder_for_this_file}': {e}**")
                print(f"--- SKIPPING file due to directory error: {os.path.basename(input_filepath)} ---")
                failed_files += 1
                continue

        generated_content, error_message = process_single_file(
            input_filepath=input_filepath,
            api_key=final_api_key,
            engine=engine,
            user_prompt_template=custom_prompt_template,
            model_name=model_name,
            stream_output=stream_output,
            output_suffix=suffix,
            output_folder=output_folder_for_this_file,
            log_folder=log_folder_for_this_file
        )
        if generated_content is not None and not error_message:
            print("\n--- Generated Content (Success) ---")
            max_console_print = 1000
            print(generated_content[:max_console_print] + ('...' if len(generated_content) > max_console_print else ''))
            processed_files += 1
        else:
            print(f"\n--- FAILED to process file: {os.path.basename(input_filepath)} ---")
            print(f"Error logged: {error_message or 'Unknown processing error.'}")
            failed_files += 1
        print("-" * 30)

    print("\n=========================================")
    print("          Batch Processing Summary")
    print("=========================================")
    print(f"Total files attempted: {total_files}")
    print(f"Successfully processed: {processed_files}")
    print(f"Failed: {failed_files}")
    if processed_files > 0 or failed_files > 0:
        if central_output_folder:
            print(f"\nRaw API responses saved in: '{central_output_folder}'")
            print(f"Processing logs saved in: '{os.path.join(central_output_folder, LOG_SUBFOLDER_NAME)}'")
        else:
            print(f"\nOutput files saved next to their originals.")
            print(f"Processing logs saved in a '{LOG_SUBFOLDER_NAME}' subfolder within each location.")
    if failed_files > 0:
        print("\nCheck console output and log files for details on failures.")
    print("=========================================")

if __name__ == "__main__":
    main()

# --- END OF FILE GPTBatcher_Multimodal_Logged_v6.py ---