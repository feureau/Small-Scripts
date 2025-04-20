# --- START OF FILE GPTBatcher_Multimodal_Logged.py ---

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
RAW_OUTPUT_FILE_EXTENSION = "_raw_output.txt"
LOG_FILE_EXTENSION = "_processing.log" # New extension for log files
DEFAULT_RAW_OUTPUT_SUFFIX = "_raw" # Suffix for output and log filenames

# 5. Default Models and Engine - Placeholders, will be updated dynamically
DEFAULT_GEMINI_MODEL = ""
DEFAULT_OLLAMA_MODEL = ""
DEFAULT_ENGINE = "google"

# 6. Rate Limiting Configuration (Google Gemini)
REQUESTS_PER_MINUTE = 15
REQUEST_INTERVAL_SECONDS = 60 / REQUESTS_PER_MINUTE

# 7. Output Subfolder Name
RAW_OUTPUT_SUBFOLDER_NAME = "output_results"

################################################################################
# --- End of Customizable Variables ---
################################################################################

# Global variable for rate limiting
last_request_time = None

# --- Model Fetching Functions ---
# (fetch_google_models and fetch_ollama_models remain the same as before)
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
             model_names = sorted([
                 model.get("name") for model in data["models"]
                 if model.get("name") and ':' in model.get("name")
             ])
             model_names.extend(sorted([
                 model.get("name") for model in data["models"]
                 if model.get("name") and ':' not in model.get("name")
             ]))
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
# Note: These functions already return specific error messages prefixed with "Error:".
# We rely on these specific messages being returned on failure.
def call_generative_ai_api(engine, prompt_text, api_key, model_name,
                           image_bytes=None, mime_type=None, stream_output=False):
    """Calls the selected AI API (Google or Ollama) to get content, handling multimodal."""
    if engine == "google":
        return call_google_gemini_api(prompt_text, api_key, model_name, image_bytes, mime_type, stream_output)
    elif engine == "ollama":
        return call_ollama_api(prompt_text, model_name, image_bytes)
    else:
        print(f"Error: Unknown engine '{engine}'")
        # Return the error message directly
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
            # Ensure model is vision capable (basic check) - User needs to select correctly
            if "vision" not in model_name and "1.5" not in model_name:
                 print(f"Warning: Selected model '{model_name}' might not be optimized for vision tasks.")
            try:
                encoded_image = base64.b64encode(image_bytes).decode('utf-8')
                request_payload = [
                    prompt_text,
                    {"inline_data": {"mime_type": mime_type, "data": encoded_image}}
                ]
            except Exception as e:
                 print(f"Error encoding image for Google API: {e}")
                 return f"Error: Failed to encode image data - {e}"
        else:
            print("--- Preparing text-only request for Google Gemini (Model: {}): ---".format(model_name))
            print(prompt_text[:1000] + "..." if len(prompt_text) > 1000 else prompt_text)
            print("--- End of Prompt Snippet ---")
            request_payload = [prompt_text]

        print(f"--- Calling Google Gemini API with model '{model_name}'... {'Streaming enabled' if stream_output else '(Non-streaming)'} ---")
        generation_config = genai.types.GenerationConfig() # Add parameters if needed

        # API Call and Response Handling
        api_response_text = ""
        try:
            if stream_output:
                # Streaming logic remains complex, ensure robust error checking within the loop if used extensively
                response = model.generate_content(request_payload, generation_config=generation_config, stream=True)
                full_response_text = ""
                print("\n--- Streaming Response ---")
                for chunk in response:
                    # Simplified handling for brevity - needs more robust error checking in production
                    if chunk.text:
                        print(chunk.text, end="", flush=True)
                        full_response_text += chunk.text
                    # Add checks for prompt_feedback and finish_reason here if needed
                print("\n--- End of Stream ---")
                api_response_text = full_response_text.strip()
                # Add final safety checks based on potentially available response attributes after stream
                # ... (omitted for brevity, see previous version for examples)

            else: # Non-streaming (more reliable error info)
                response = model.generate_content(request_payload, generation_config=generation_config, stream=False)
                print("\n--- Google Gemini API call completed (non-streaming). ---")

                # Robust check for prompt feedback first
                if hasattr(response, 'prompt_feedback') and response.prompt_feedback and response.prompt_feedback.block_reason:
                     block_reason = response.prompt_feedback.block_reason
                     print(f"ERROR: Input prompt blocked due to: {block_reason}")
                     # Return specific error
                     return f"Error: Prompt blocked by safety filter ({block_reason})."

                # Then check candidates and finish reason
                if not hasattr(response, 'candidates') or not response.candidates:
                     # If no candidates, check prompt feedback again for detailed reason
                     block_reason = getattr(getattr(response, 'prompt_feedback', None), 'block_reason', 'Unknown')
                     print(f"ERROR: No candidates found in response (Reason: {block_reason}).")
                     return f"Error: No response generated (Reason: {block_reason})." # Specific error

                # We have candidates, check the first one
                candidate = response.candidates[0]
                finish_reason = getattr(candidate, 'finish_reason', 'UNKNOWN') # Default if missing
                safety_ratings = getattr(candidate, 'safety_ratings', None)

                if finish_reason != 'STOP':
                    print(f"WARNING: Generation finished unexpectedly: {finish_reason}")
                    if finish_reason == 'SAFETY':
                        print(f"Safety Ratings: {safety_ratings}")
                        return f"Error: Response generation stopped due to safety ({finish_reason})." # Specific error
                    # For other reasons like MAX_TOKENS, try getting text but return error if unavailable
                    try:
                        api_response_text = response.text # Attempt to get partial text
                        print(f"Warning: Generation stopped early ({finish_reason}), partial text retrieved.")
                        # Proceed with the partial text
                    except (ValueError, AttributeError) as e:
                         print(f"Error accessing partial text after non-STOP finish ({finish_reason}): {e}")
                         return f"Error: Generation stopped ({finish_reason}), couldn't retrieve text." # Specific error
                else: # Finish reason is STOP
                     try:
                        # This is the primary success path for getting text
                        api_response_text = response.text
                     except (ValueError, AttributeError) as e:
                          # This might happen if the response is empty even with STOP, or other issues
                          print(f"Error accessing response text despite STOP reason: {e}. Finish Reason: {finish_reason}")
                          # Check prompt feedback again just in case
                          block_reason = getattr(getattr(response, 'prompt_feedback', None), 'block_reason', None)
                          if block_reason:
                              return f"Error: No text content found (Prompt Block Reason: {block_reason})."
                          else:
                              # Return a specific error about text access
                              return f"Error: Could not retrieve text from response (Finish Reason: {finish_reason})."


        except Exception as e:
            # Catch potential errors during the generate_content call itself
            print(f"Error during Gemini content generation: {e}", file=sys.stderr)
            # Log the traceback for detailed debugging if needed
            # traceback.print_exc()
            # Return specific error
            return f"Error: Gemini generation failed - {str(e)[:150]}"

        # If we got here with non-empty text, return it
        # Handle the case where response is valid but .text is empty (though less common now with checks above)
        if api_response_text is None: api_response_text = "" # Ensure string type
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
    except Exception as e: # Catch-all for unexpected issues like configuration
        print(f"Unexpected error in Google API setup or call: {e}", file=sys.stderr)
        traceback.print_exc() # Print stack trace for unexpected errors
        return f"Error: Unexpected Google API issue - {str(e)[:100]}"

def call_ollama_api(prompt_text, model_name, image_bytes=None):
    """Calls the local Ollama API, supporting text and image input (e.g., for llava)."""
    payload = {
        "model": model_name,
        "prompt": prompt_text,
        "stream": False
    }
    encoded_image = None # Initialize

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
            return f"Error: Failed to encode image data - {e}" # Specific error
    else:
         print(f"--- Preparing text-only request for Ollama ({model_name}) ---")
         print(f"--- Prompt Snippet: {prompt_text[:500]}... ---")

    try:
        print(f"--- Calling Ollama API ({model_name}) at {OLLAMA_GENERATE_ENDPOINT} ---")
        response = requests.post(OLLAMA_GENERATE_ENDPOINT, json=payload, timeout=600)
        response.raise_for_status() # Raises HTTPError for 4xx/5xx responses
        data = response.json()
        print("--- Ollama API call completed. ---")

        if "response" in data:
            # Success case
            return data["response"].strip() if data["response"] else "" # Return empty string if response is null/empty
        elif "error" in data:
             # Ollama returned a structured error
             error_msg = data['error']
             print(f"ERROR from Ollama API: {error_msg}")
             return f"Error: Ollama API returned an error - {error_msg}" # Specific error
        else:
             # Unexpected response structure
             print(f"ERROR: Unexpected response structure from Ollama: {data}")
             return "Error: Unexpected response format from Ollama (missing 'response' or 'error')." # Specific error

    except requests.exceptions.ConnectionError as e:
        print(f"ERROR: Could not connect to Ollama API at {OLLAMA_GENERATE_ENDPOINT}. Is Ollama running?")
        return f"Error: Could not connect to Ollama API at {OLLAMA_API_URL} - {e}" # Specific error
    except requests.exceptions.Timeout as e:
         print(f"ERROR: Timeout during Ollama generation ({model_name}).")
         return f"Error: Ollama generation timed out ({model_name}) - {e}" # Specific error
    except requests.exceptions.HTTPError as e:
         # Handle 4xx/5xx errors specifically
         error_details = f"HTTP Error {e.response.status_code} calling Ollama generate API: {e}"
         try:
             # Try to get more specific error from response body
             error_body = e.response.json()
             error_details += f" - Ollama Error: {error_body.get('error', e.response.text[:200])}"
         except json.JSONDecodeError:
             error_details += f" - Response: {e.response.text[:200]}"
         print(error_details)
         return f"Error: Ollama Request Failed ({error_details})" # Specific error
    except requests.exceptions.RequestException as e:
        # Catch other request-related errors
        print(f"ERROR calling Ollama generate API: {e}")
        return f"Error: Ollama Request Failed - {e}" # Specific error
    except json.JSONDecodeError as e:
         # If server returns invalid JSON (less likely with raise_for_status, but possible)
         print(f"ERROR: Could not decode JSON response from Ollama generate API: {e}")
         return f"Error: Invalid JSON response from Ollama - {e}" # Specific error
    except Exception as e:
        # Catch-all for other unexpected errors
        print(f"Unexpected ERROR calling Ollama generate API: {e}")
        traceback.print_exc() # Print stack trace for unexpected errors
        return f"Error: Unexpected Ollama Call Failed - {e}" # Specific error


# --- Output & Logging Functions ---

def generate_output_filenames(input_filepath, output_suffix):
    """Generates base filename, raw output filename, and log filename."""
    base_name = os.path.splitext(os.path.basename(input_filepath))[0]
    # Sanitize base name
    sanitized_base_name = "".join(c if c.isalnum() or c in ('_', '-') else '_' for c in base_name)
    output_filename_base = f"{sanitized_base_name}{output_suffix}"
    raw_output_filename = f"{output_filename_base}{RAW_OUTPUT_FILE_EXTENSION}"
    log_filename = f"{output_filename_base}{LOG_FILE_EXTENSION}"
    return output_filename_base, raw_output_filename, log_filename

def save_raw_api_response(api_response_text, output_folder, raw_output_filename):
    """Saves the raw API response text to the specified file."""
    # Note: api_response_text can contain error messages if API call failed
    if api_response_text is None: # Explicitly check for None
         api_response_text = "[Error: API response was None]"
         print("Debug: save_raw_api_response - API response was None, saving placeholder.")
    elif not api_response_text:
         api_response_text = "[Info: API response was empty]"
         print("Debug: save_raw_api_response - API response was empty, saving placeholder.")

    output_filepath = os.path.join(output_folder, raw_output_filename)

    try:
        with open(output_filepath, 'w', encoding='utf-8') as outfile:
            outfile.write(api_response_text)
        # Don't print success here, log function will confirm log+raw save
    except Exception as e:
        print(f"**ERROR: Could not save raw API response to file: {output_filepath}**\nError details: {e}")
        # We should still attempt to save the log file even if this fails

def save_processing_log(log_data, output_folder, log_filename):
    """Saves the processing parameters and outcome to a log file."""
    log_filepath = os.path.join(output_folder, log_filename)
    timestamp_format = "%Y-%m-%d %H:%M:%S"

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
            logfile.write(f"  Output Directory: {log_data.get('output_folder', 'N/A')}\n")
            logfile.write(f"  Output Suffix: {log_data.get('output_suffix', 'N/A')}\n")
            logfile.write(f"  Raw Output File: {log_data.get('raw_output_filename', 'N/A')}\n")
            logfile.write(f"  Log File: {log_filename}\n") # Log its own name
            logfile.write("-"*50 + "\n")
            logfile.write("Prompt Sent to API:\n")
            # Log the full prompt for debugging - can be very long
            logfile.write(log_data.get('prompt_sent', '[Prompt not captured]'))
            logfile.write("\n" + "-"*50 + "\n")
            logfile.write("Outcome:\n")
            logfile.write(f"  Status: {log_data.get('status', 'Unknown')}\n")
            if log_data.get('status', 'Unknown') == 'Failure':
                logfile.write(f"  Error Message: {log_data.get('error_message', 'No specific error message.')}\n")
                if log_data.get('traceback_info'):
                    logfile.write(f"  Traceback:\n{log_data.get('traceback_info')}\n")
            logfile.write("="*56 + "\n")
        print(f"Processing log saved to: {log_filepath}")
        print(f"Raw API response saved to: {os.path.join(output_folder, log_data.get('raw_output_filename', 'N/A'))}")
    except Exception as e:
        print(f"**ERROR: Could not save processing log file: {log_filepath}**\nError details: {e}")


# --- Core Processing ---

def process_single_file(input_filepath, api_key, engine, user_prompt_template, model_name,
                        stream_output, output_suffix, output_folder):
    """
    Processes a single input file, calls the API, saves raw output and a detailed log file.
    Returns (generated_content, error_message) where generated_content is None on failure.
    """
    start_time = datetime.datetime.now()
    log_data = {
        'input_filepath': input_filepath,
        'start_time': start_time,
        'engine': engine,
        'model_name': model_name,
        'api_key_provided': bool(api_key),
        'stream_output': stream_output,
        'output_suffix': output_suffix,
        'output_folder': output_folder,
        'status': 'Failure', # Default status
        'error_message': None,
        'traceback_info': None,
        'prompt_sent': None,
        'raw_output_filename': None,
        'end_time': None,
        'duration': -1,
    }

    # Generate filenames early
    _, raw_output_filename, log_filename = generate_output_filenames(input_filepath, output_suffix)
    log_data['raw_output_filename'] = raw_output_filename
    log_data['log_filename'] = log_filename # Log its own name too

    api_response_text = None # Initialize
    generated_content = None # Final content if successful

    try:
        print(f"--- Reading file: {input_filepath} ---")
        content_data, mime_type, is_image, read_error_msg = read_file_content(input_filepath)

        if read_error_msg:
            print(read_error_msg)
            log_data['status'] = 'Failure'
            log_data['error_message'] = f"File Read Error: {read_error_msg}"
            # Save the read error into the 'raw output' file for consistency
            save_raw_api_response(log_data['error_message'], output_folder, raw_output_filename)
            # No API call made, return error
            raise Exception(log_data['error_message']) # Use exception flow to get to finally block for logging

        log_data['is_image'] = is_image
        log_data['mime_type'] = mime_type

        prompt_for_api = user_prompt_template
        image_bytes_for_api = None

        if is_image:
            print(f"Type: Image ({mime_type})")
            image_bytes_for_api = content_data
            log_data['image_size'] = len(content_data) if content_data else 0
            # For images, prompt is just the template
            log_data['prompt_sent'] = prompt_for_api
        else: # Is text file
            print("Type: Text")
            # Append text file content
            file_content_str = content_data if content_data else " [File was empty or could not be read fully]"
            prompt_for_api += f"\n\n--- File Content Start ---\n{file_content_str}\n--- File Content End ---"
            log_data['prompt_sent'] = prompt_for_api # Log the full combined prompt

        # --- Call the API ---
        api_response_text = call_generative_ai_api(
            engine=engine,
            prompt_text=prompt_for_api,
            api_key=api_key,
            model_name=model_name,
            image_bytes=image_bytes_for_api,
            mime_type=mime_type,
            stream_output=stream_output and engine == 'google'
        )

        # --- Process API Response ---
        # Save the raw response regardless of whether it's an error message or content
        save_raw_api_response(api_response_text, output_folder, raw_output_filename)

        # Check if the response indicates an error
        if api_response_text is None or api_response_text.startswith("Error:"):
            error_detail = api_response_text if api_response_text else "API call returned None or Empty."
            print(f"API Call Failed: {error_detail}")
            log_data['status'] = 'Failure'
            log_data['error_message'] = error_detail
            # No successful content generated
            generated_content = None
        else:
            # Success!
            log_data['status'] = 'Success'
            log_data['error_message'] = None
            generated_content = api_response_text # The response is the content

    except Exception as e:
        # Catch errors from file reading or other unexpected issues before/during API call
        print(f"**ERROR during processing {input_filepath}: {e}**")
        log_data['status'] = 'Failure'
        # Store specific error if not already set by API call failure
        if not log_data.get('error_message'):
             log_data['error_message'] = f"Processing Exception: {str(e)}"
        log_data['traceback_info'] = traceback.format_exc() # Capture stack trace

        # Ensure raw output file contains the error if API wasn't called or failed early
        if api_response_text is None:
             save_raw_api_response(f"[ERROR] {log_data['error_message']}\n\n{log_data['traceback_info']}", output_folder, raw_output_filename)

        generated_content = None # Ensure content is None on exception

    finally:
        # --- Finalize and Log ---
        end_time = datetime.datetime.now()
        log_data['end_time'] = end_time
        log_data['duration'] = (end_time - start_time).total_seconds()
        # Save the log file with all collected data
        save_processing_log(log_data, output_folder, log_filename)

        # Return the final content (None if failed) and error message
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
    # else: # Reduce console noise if key is found silently
    #      print(f"INFO: Using Google API Key from environment variable {API_KEY_ENV_VAR_NAME}.")
    return api_key

# --- GUI Implementation ---
# (ArgsWrapper, use_gui, add_files_to_list, remove_selected_files remain the same)
class ArgsWrapper:
    def __init__(self):
        self.model = None
        self.engine = DEFAULT_ENGINE
        self.output = RAW_OUTPUT_SUBFOLDER_NAME
        self.suffix = DEFAULT_RAW_OUTPUT_SUFFIX
        self.stream = False
        self.files = []

def use_gui(initial_api_key, command_line_files=None, args=None):
    """Launches a tkinter GUI for script options, with dynamic model loading."""
    window = tk.Tk()
    window.title("Multimodal AI Batch Processor")
    current_api_key = {'key': initial_api_key}
    settings = {}
    files_list_var = tk.Variable(value=command_line_files if command_line_files else [])
    engine_var = tk.StringVar(value=args.engine if args else DEFAULT_ENGINE)
    model_var = tk.StringVar()
    output_dir_var = tk.StringVar(value=args.output if args else RAW_OUTPUT_SUBFOLDER_NAME)
    suffix_var = tk.StringVar(value=args.suffix if args else DEFAULT_RAW_OUTPUT_SUFFIX)
    stream_output_var = tk.BooleanVar(value=args.stream if args else False)

    # --- GUI Layout --- (Mostly unchanged, ensure frames pack/grid correctly)
    current_row = 0
    # API Key Frame
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

    # Files Section
    files_frame = ttk.LabelFrame(window, text="Input Files (Text or Images)", padding="10 10 10 10"); files_frame.grid(row=current_row, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5); files_frame.columnconfigure(0, weight=1); current_row += 1
    file_listbox = tk.Listbox(files_frame, listvariable=files_list_var, height=6, width=70, selectmode=tk.EXTENDED); file_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    files_scrollbar = ttk.Scrollbar(files_frame, orient=tk.VERTICAL, command=file_listbox.yview); files_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S)); file_listbox.config(yscrollcommand=files_scrollbar.set)
    file_buttons_frame = ttk.Frame(files_frame); file_buttons_frame.grid(row=0, column=2, sticky=(tk.N, tk.S), padx=(5,0))
    tk.Button(file_buttons_frame, text="Add Files...", command=lambda: add_files_to_list(files_list_var, file_listbox, window)).pack(fill=tk.X, pady=2)
    tk.Button(file_buttons_frame, text="Clear All", command=lambda: files_list_var.set([]), width=10).pack(fill=tk.X, pady=2)
    tk.Button(file_buttons_frame, text="Remove Sel.", command=lambda: remove_selected_files(files_list_var, file_listbox), width=10).pack(fill=tk.X, pady=2)

    # Prompt Section
    prompt_frame = ttk.LabelFrame(window, text="User Prompt (Adapt for Text vs. Image Analysis)", padding="10 10 10 10"); prompt_frame.grid(row=current_row, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5); prompt_frame.columnconfigure(0, weight=1); current_row += 1
    prompt_text_widget = scrolledtext.ScrolledText(prompt_frame, wrap=tk.WORD, width=80, height=10, relief=tk.SOLID, borderwidth=1); prompt_text_widget.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S)); prompt_text_widget.insert(tk.INSERT, USER_PROMPT_TEMPLATE)

    # Options Frame
    options_frame = ttk.Frame(window, padding="10 10 10 10"); options_frame.grid(row=current_row, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S)); options_frame.columnconfigure(1, weight=1); current_row += 1
    tk.Label(options_frame, text="AI Engine:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
    engine_options = ['google', 'ollama']; engine_combo = ttk.Combobox(options_frame, textvariable=engine_var, values=engine_options, state="readonly", width=35); engine_combo.grid(row=0, column=1, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=2)
    tk.Label(options_frame, text="Model:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
    model_combo = ttk.Combobox(options_frame, textvariable=model_var, state="disabled", width=35); model_combo.grid(row=1, column=1, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=2)
    tk.Label(options_frame, text="(Select multimodal model like 'gemini-1.5-pro' or 'llava' for images)", font=('TkDefaultFont', 8)).grid(row=2, column=1, columnspan=2, sticky=tk.W, padx=5)

    # Settings Frame
    settings_frame = ttk.Frame(window, padding="10 10 10 10"); settings_frame.grid(row=current_row, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S)); settings_frame.columnconfigure(1, weight=1); current_row += 1
    tk.Label(settings_frame, text="Output Dir:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2); output_entry = ttk.Entry(settings_frame, textvariable=output_dir_var, width=40); output_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=2)
    tk.Button(settings_frame, text="Browse...", command=lambda: output_dir_var.set(filedialog.askdirectory(initialdir=os.getcwd(), parent=window) or output_dir_var.get())).grid(row=0, column=2, sticky=tk.E, padx=5)
    tk.Label(settings_frame, text="Output Suffix:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2); suffix_entry = ttk.Entry(settings_frame, textvariable=suffix_var, width=20); suffix_entry.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
    stream_check = ttk.Checkbutton(settings_frame, text="Stream Output (Google Engine Only / Experimental)", variable=stream_output_var); stream_check.grid(row=2, column=1, columnspan=2, sticky=tk.W, padx=5, pady=5)

    # Dynamic Model Loading Logic (Unchanged - relies on fetch functions)
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

    # Process Button Logic (Validation mostly unchanged)
    def process_from_gui():
        settings['files'] = list(files_list_var.get())
        settings['custom_prompt'] = prompt_text_widget.get("1.0", tk.END).strip()
        settings['engine'] = engine_var.get()
        settings['model'] = model_var.get()
        settings['output_dir'] = output_dir_var.get() or RAW_OUTPUT_SUBFOLDER_NAME
        settings['suffix'] = suffix_var.get() or DEFAULT_RAW_OUTPUT_SUFFIX
        settings['stream_output'] = stream_output_var.get()
        settings['api_key'] = current_api_key['key']

        # Validation (mostly unchanged)
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
    window.columnconfigure(0, weight=1); window.rowconfigure(1, weight=1); window.rowconfigure(2, weight=1) # Resize config
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
                 # else: print(f"Skipping duplicate file (basename match): {f_normalized}") # Less verbose
            # else: print(f"Skipping duplicate file (exact path match): {f_normalized}") # Less verbose
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
         try: removed_item = current_files.pop(i); removed_count += 1 # print(f"Removed: {removed_item}") # Less verbose
         except IndexError: print(f"Warning: Index {i} out of bounds during removal.")
     if removed_count > 0: files_list_var.set(tuple(current_files)); print(f"Removed {removed_count} file(s).")

# --- Main Execution ---

def main():
    initial_api_key = get_api_key(force_gui=False)

    parser = argparse.ArgumentParser(description="Multimodal AI Batch Processor - Process text/image files using AI")
    parser.add_argument("files", nargs="*", help=f"Path(s) to input file(s). Supports patterns and extensions like {', '.join(ALL_SUPPORTED_EXTENSIONS)}.")
    parser.add_argument("-o", "--output", default=RAW_OUTPUT_SUBFOLDER_NAME, help=f"Output directory for raw responses and logs. Default: '{RAW_OUTPUT_SUBFOLDER_NAME}'.")
    parser.add_argument("-s", "--suffix", default=DEFAULT_RAW_OUTPUT_SUFFIX, help=f"Suffix for output/log filenames. Default: '{DEFAULT_RAW_OUTPUT_SUFFIX}'.")
    parser.add_argument("--stream", action='store_true', default=False, help="Enable streaming output (Google Engine Only / Experimental).")
    parser.add_argument("-e", "--engine", default=DEFAULT_ENGINE, choices=['google', 'ollama'], help=f"AI engine to use. Default: '{DEFAULT_ENGINE}'.")
    parser.add_argument("-m", "--model", dest="model", default=None, help="Suggest a model to select by default in GUI.")

    args = parser.parse_args()

    # Expand File Patterns from Command Line (Unchanged)
    filepaths_from_cli = []
    if args.files:
        print("Expanding file patterns from command line...")
        for pattern in args.files:
            try:
                expanded_files = glob.glob(pattern, recursive=True)
                valid_files = []
                for f in expanded_files:
                    if os.path.isfile(f):
                         _, ext = os.path.splitext(f)
                         if ext.lower() in ALL_SUPPORTED_EXTENSIONS:
                             valid_files.append(os.path.normpath(f).replace("\\", "/"))
                         # else: print(f"Skipping unsupported file type from pattern '{pattern}': {f}") # Less verbose
                    # else: print(f"Skipping directory found by pattern '{pattern}': {f}") # Less verbose
                if valid_files:
                     # print(f"  Pattern '{pattern}' matched: {len(valid_files)} supported file(s)") # Less verbose
                     filepaths_from_cli.extend(valid_files)
                # else: print(f"Warning: Pattern '{pattern}' did not match any supported files.") # Less verbose
            except Exception as e: print(f"Error processing pattern '{pattern}': {e}")
        filepaths_from_cli = sorted(list(set(filepaths_from_cli)))
        print(f"Total unique supported files from command line: {len(filepaths_from_cli)}")
        args.files = filepaths_from_cli

    # Launch GUI (Unchanged)
    gui_settings = use_gui(initial_api_key=initial_api_key, command_line_files=filepaths_from_cli, args=args)
    if not gui_settings: print("Operation cancelled or GUI closed."); return

    # Extract Settings (Unchanged)
    input_file_paths_gui = gui_settings.get('files', [])
    custom_prompt_template = gui_settings.get('custom_prompt', USER_PROMPT_TEMPLATE)
    output_folder_base = gui_settings.get('output_dir', RAW_OUTPUT_SUBFOLDER_NAME)
    suffix = gui_settings.get('suffix', DEFAULT_RAW_OUTPUT_SUFFIX)
    stream_output = gui_settings.get('stream_output', False)
    engine = gui_settings.get('engine', DEFAULT_ENGINE)
    model_name = gui_settings.get('model')
    final_api_key = gui_settings.get('api_key')

    # Final Validation (Unchanged)
    if not input_file_paths_gui: print("Error: No input files selected for processing."); return
    if not model_name: print("Error: No model selected."); return
    if engine == 'google' and not final_api_key: print("Error: Google engine selected, but final API Key is missing."); return

    # Prepare for Processing (Create output dir logic unchanged)
    all_input_filepaths = sorted(list(set(input_file_paths_gui)))
    if not all_input_filepaths: print("Error: No valid input file paths specified."); return

    output_folder_path = os.path.join(os.getcwd(), output_folder_base)
    try:
        os.makedirs(output_folder_path, exist_ok=True)
        print(f"Ensured output directory exists: {output_folder_path}")
    except OSError as e:
        print(f"Error creating output directory '{output_folder_path}': {e}")
        # Use temporary Tk root for messagebox if main GUI is gone
        temp_root = tk.Tk(); temp_root.withdraw()
        try:
             if tkinter.messagebox.askyesno("Directory Error", f"Could not create output directory:\n{output_folder_path}\n\nSave output files to the current working directory instead? ({os.getcwd()})", parent=temp_root):
                  output_folder_path = os.getcwd()
                  print(f"Proceeding with output to current directory: {output_folder_path}")
             else: print("Exiting due to output directory error."); return
        finally: temp_root.destroy()


    # --- Batch Processing Loop ---
    processed_files = 0; failed_files = 0; total_files = len(all_input_filepaths)
    print(f"\nStarting batch processing for {total_files} file(s)...")
    print(f"Engine: {engine}, Model: {model_name}")
    print(f"Output Directory: {output_folder_path}")
    print("-" * 50)

    for i, input_filepath in enumerate(all_input_filepaths):
        print(f"\n--- Processing file {i + 1}/{total_files} ---")

        # Process the file - now includes logging internally
        generated_content, error_message = process_single_file(
            input_filepath=input_filepath,
            api_key=final_api_key,
            engine=engine,
            user_prompt_template=custom_prompt_template,
            model_name=model_name,
            stream_output=stream_output,
            output_suffix=suffix,
            output_folder=output_folder_path # Pass the final output folder path
        )

        # Report outcome based on return values
        if generated_content is not None and not error_message:
            print("\n--- Generated Content (Success) ---")
            max_console_print = 1000
            print(generated_content[:max_console_print] + ('...' if len(generated_content) > max_console_print else ''))
            # Confirmation of saves is now printed by logging function
            # print("--- (Full response and log saved to file) ---")
            processed_files += 1
        else:
            # Error message should contain specifics now
            print(f"\n--- FAILED to process file: {os.path.basename(input_filepath)} ---")
            print(f"Error logged: {error_message or 'Unknown processing error.'}")
            # Confirmation of saves is now printed by logging function
            # print("--- (Error details saved to raw output and log file) ---")
            failed_files += 1
        print("-" * 30) # Separator between files

    # Final Summary (Unchanged)
    print("\n=========================================")
    print("          Batch Processing Summary")
    print("=========================================")
    print(f"Total files attempted: {total_files}")
    print(f"Successfully processed: {processed_files}")
    print(f"Failed: {failed_files}")
    if processed_files > 0 or failed_files > 0:
        print(f"\nRaw API responses and processing logs saved in: '{output_folder_path}'")
    if failed_files > 0:
        print("\nCheck console output and *.log files for details on failures.")
    print("=========================================")


if __name__ == "__main__":
    main()

# --- END OF FILE GPTBatcher_Multimodal_Logged.py ---