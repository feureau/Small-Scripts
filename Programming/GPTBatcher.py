# script_folder/ytseo.py
import os
import sys
import json
import requests  # Make sure to install: pip install requests
import glob # For handling wildcard file paths
import time # For rate limiting
import google.generativeai as genai # For Google Gemini API
from google.generativeai.types import GenerateContentResponse # For Google Gemini API response type
from google.api_core.exceptions import GoogleAPIError, ResourceExhausted, PermissionDenied # For handling Google API exceptions
import argparse # For command-line argument parsing
import tkinter as tk
from tkinter import ttk
from tkinter import scrolledtext # Import scrolledtext for the prompt box
from tkinter import filedialog
import tkinter.messagebox
import tkinter.simpledialog # For API key input fallback
# Removed: import pycountry


################################################################################
# --- Customizable Variables (Configuration) ---
################################################################################

# 1. Google API Key Environment Variable Name
API_KEY_ENV_VAR_NAME = "GOOGLE_API_KEY"

# 1b. Ollama API Endpoint
OLLAMA_API_URL = "http://localhost:11434/api/tags" # Default Ollama API endpoint

# 2. Default User Prompt Template - **This will pre-fill the GUI text box**
#    The {srt_content} placeholder is crucial for the script's operation.
#    If missing from user input, it will be appended automatically.
USER_PROMPT_TEMPLATE = """**Primary Goal:** The objective is to generate YouTube metadata optimized for **maximum virality and discoverability**. All generated elements (Title, Description, Hashtags, Tags) must adhere to **YouTube SEO best practices** and be designed to **maximize engagement, watch time, and reach**, contributing to the video's potential to go viral.

**IMPORTANT:** You will be provided with SRT content **alongside this prompt** (e.g., as an attachment or separate data input). This SRT data is the **foundation** for your analysis and content generation. You **must** locate and process this accompanying SRT data to fulfill the request. Use the content within this SRT data as the primary source for generating all requested metadata elements.

While the _core content_ should be derived from this provided SRT data, you are **required** to **substantially supplement** this with relevant external knowledge to **achieve significant length and enhance SEO/discoverability crucial for virality**. Focus on understanding the _topic_ deeply and incorporating a wide range of relevant keywords and context found within or related to the SRT content.

1.  **YouTube Title:**
    * **Create a highly click-worthy and attention-grabbing title engineered for virality.** Maximize clicks while accurately representing the core hook from the SRT.
    * **Deduce the most effective viral title style** based on the *topic, tone, and content* of the provided SRT data.
    * **Incorporate relevant emojis** strategically to boost visual appeal and CTR.
    * Keep title concise for display (ideally 60-70 characters, flexible for impact).
    * Incorporate primary keywords naturally for searchability, including terms viewers are likely searching for based on the SRT topic.
    * Focus on titles that **spark intense curiosity, evoke strong emotions, promise significant value, or hint at controversy/debate** relevant to the SRT content.

2.  **YouTube Description:**
    * **Goal:** Write an **exceptionally detailed, comprehensive, and SEO-saturated description based on the provided SRT.** Generate a **comprehensive and highly detailed description**, utilizing the available space effectively. Your primary objective remains substantial length and thoroughness for SEO, but the **total combined character count for Title, Description (including Timestamps), and Hashtags MUST strictly remain under 5000 characters.** Enrich the SRT basis extensively with contextual information and a high volume of relevant keywords derived from or related to the SRT.
    * **Understanding the Topic:** Infer the main subject/theme deeply *from the SRT*. Identify specific entities accurately *mentioned in the SRT*. Use this understanding to **target a broad range of relevant search queries**.
    * **Formatting:** Use **reader-friendly paragraphs**. Avoid numbered lists for main content. Structure for readability despite the length.
    * **Opening:** Start with 2-4 compelling sentences summarizing the core value/hook *from the SRT*, **front-loading crucial keywords**.
    * **Detailed Elaboration / Main Body:**
        * **Expand significantly** on the topics *found in the SRT* using multiple, well-structured paragraphs per theme. **Your main task here is extensive elaboration based on the SRT's core points.**
        * **Proactively research and incorporate significant external information** to add depth, context, and length *related to the topics identified in the SRT*. This MUST include: relevant historical background, definitions of key terms/concepts *from the SRT*, related contemporary discussions or controversies, information about key people/organizations/media involved (*even if not named directly in SRT but clearly relevant*), common audience questions *about the SRT topic*, differing perspectives, and potential implications/future developments related to the topic *discussed in the SRT*.
        * Break down content into logical themes *present in the SRT*. Discuss each theme **at length**, significantly enriching the explanation **far beyond** the raw SRT content using your knowledge base for maximum SEO and informational value, *while ensuring relevance to the source SRT*.
        * For each theme, extract core points *from the SRT*, then **extensively add related details, context, examples, analyses, and elaborations based on external knowledge.**
        * Quote impactful statements *from the SRT transcript* when appropriate, but focus primarily on original elaboration.
        * If discussing specific media *mentioned or clearly implied in the SRT*, use official titles and **incorporate a wide array of related SEO keywords** (actors, directors, studios, genre specifics, plot points, fan theories, critical reception, related works).
        * Weave a **very rich, dense, and diverse array of relevant keywords** naturally throughout – include **long-tail keywords, semantic variations, question-based keywords, and terms reflecting various facets of viewer search intent related to the SRT topic.** Aim for **maximum appropriate keyword density and variation**. **Revisit key concepts using different phrasing and related keywords multiple times** throughout the description to reinforce SEO signals and build length. Do not shy away from this strategic repetition.
        * **IMPORTANT: The YouTube Description MUST ABSOLUTELY NOT CONTAIN ANY FILE REFERENCES, MARKERS, OR TEXT THAT LOOKS LIKE FILE PATHS OR FILE IDENTIFIERS. OMIT COMPLETELY.**
    * **Timestamps Section:** Identify key segments *within the SRT data* to improve navigation. Use `MM:SS – Detailed, Keyword-Rich Topic Description`. Use approximate start times *from the SRT*. **Output only the list of timestamps without any introductory title. Max 2-3 words.**
    * **Closing:** Conclude with a clear CTA encouraging **likes, subscriptions, shares, comments, and notification bell clicks**. Reinforce the video's value using keywords *related to the SRT topic*.
    * **IMPORTANT:** Do not include section title in the description. Also, do not use any list in the description section. All list must be converted into proper text.

**Hashtags:**
* Generate **exactly 3** strategically chosen hashtags *relevant to the SRT content*. Mix broad, specific, and potentially trending terms. Use popular, relevant terms even if not explicitly in SRT but strongly related to the topic. **Output only the list of hashtags without any introductory title.**

**Overall Character Limit (Title + Description + Hashtags):**
* **Strict Overall Character Limit:** The total combined character count for the generated **Title + Description (including Timestamps section) + Hashtags** absolutely **must not exceed 5000 characters**. Verify this limit before finalizing the output.

**Tags (Keywords):**
* Generate a comprehensive list of keywords/phrases optimized for Youtube *based on the SRT content and related external knowledge*, **maximizing relevance within the strict character limit.**
* Include main topics, specifics, synonyms, common misspellings, long-tail variations, question queries, broader concepts *from the SRT and related external knowledge*. Focus intensely on search terms *relevant to the SRT's subject matter*.
* **Strict Character Limit (Tags):** The total character count for all tags combined **absolutely must not exceed 500 characters**.
* **Action Required:** If your initial list of generated tags exceeds 500 characters, you **MUST** shorten the list by removing less relevant or redundant tags until the total character count is **strictly below 500 characters**. Prioritize the most impactful and diverse tags.
* **Final Check:** Ensure the total character count of the final tag list is under 500 characters.
* **Output only the list of tags/keywords without any introductory title.**

**General Instructions:**

* **ABSOLUTELY NO FILE REFERENCES IN OUTPUT:** Non-negotiable. Must be completely absent from the final output (this refers to file paths/names, not citation markers which are handled below).
* **Virality & SEO First:** Prioritize maximizing viral potential via strong SEO, engagement hooks, and clickability, all derived from and expanding upon the provided SRT data. **Length and detail in the description remain key, within the overall limits.**
* **Extensive External Knowledge REQUIRED:** You MUST use your knowledge base extensively to elaborate, add context, and integrate keywords far beyond the raw SRT, *always staying relevant to the core topics identified within the SRT.*
* **SRT as Foundation Only:** The SRT provides the core topic/quotes, but the bulk of the description's text must be expanded information *related to that core*.
* **Paragraph Format (Description):** Maintain paragraph structure.
* **YouTube Best Practices:** Adhere strictly to best practices.
* **Tone:** Engaging/informative for description; highly attention-grabbing/viral for title.
* **No Section Titles in Output:** Ensure final output has no headers (Timestamps:, Hashtags:, Tags:).
* **Final Output Cleaning:** Before presenting the final result, review all generated text (Title, Description, Hashtags, Tags) and **remove any citation markers, source indicators, or similar notations** (e.g., `[1]`, `[citation needed]`, `Source: X`, `(Source: SRT)`). The final output delivered to the user must be completely free of such markers.

""" + "\n\n" + "Full SRT file content:\n{srt_content}" # {srt_content} placeholder remains crucial

# 3. Default target language REMOVED
# DEFAULT_TARGET_LANGUAGE = "en"

# 4. Output file extension
RAW_OUTPUT_FILE_EXTENSION = "_raw.txt" # Default extension for raw API response files
DEFAULT_RAW_OUTPUT_SUFFIX = "_raw" # CHANGED Default suffix for raw API response files

# 5. Default Models and Engine - Placeholders, will be updated dynamically
DEFAULT_GEMINI_MODEL = "" # Will be populated dynamically
DEFAULT_OLLAMA_MODEL = "" # Will be populated dynamically
DEFAULT_ENGINE = "google" # Default engine selection

# 6. Rate Limiting Configuration
REQUESTS_PER_MINUTE = 15
REQUEST_INTERVAL_SECONDS = 60 / REQUESTS_PER_MINUTE

# 7. Output Subfolder Name
RAW_OUTPUT_SUBFOLDER_NAME = "output" # Subfolder for raw API responses


################################################################################
# --- End of Customizable Variables ---
################################################################################


# Global variable for rate limiting
last_request_time = None

# --- Model Fetching Functions ---

def fetch_google_models(api_key):
    """Fetches available 'generateContent' models from Google Generative AI."""
    if not api_key:
        return [], "API key not available."
    try:
        print("Fetching Google AI models...")
        genai.configure(api_key=api_key)
        models = [
            m.name
            for m in genai.list_models()
            if "generateContent" in m.supported_generation_methods
        ]
        print(f"Found Google models (raw): {models}")
        # Filter out vision models if they are not desired for text generation
        models = [m for m in models if 'vision' not in m]
        # Optional sort: prioritize flash/pro models
        models.sort(key=lambda x: (not ('flash' in x or 'pro' in x), x))
        print(f"Filtered/Sorted Google models: {models}")
        return models, None # Return models list and no error message
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
        print(f"Fetching Ollama models from {OLLAMA_API_URL}...")
        response = requests.get(OLLAMA_API_URL, timeout=5) # Add a timeout
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        data = response.json()
        if "models" in data and isinstance(data["models"], list):
             model_names = sorted([model.get("name") for model in data["models"] if model.get("name")]) # Sort alphabetically
             print(f"Found Ollama models: {model_names}")
             return model_names, None
        else:
             print("ERROR: Unexpected response format from Ollama API.")
             return [], "Unexpected response format from Ollama."
    except requests.exceptions.ConnectionError:
        print(f"ERROR: Could not connect to Ollama API at {OLLAMA_API_URL}. Is Ollama running?")
        return [], "Connection Error: Is Ollama running?"
    except requests.exceptions.Timeout:
         print(f"ERROR: Timeout connecting to Ollama API at {OLLAMA_API_URL}.")
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

# Removed: get_language_name_from_code function

def read_raw_srt_content(filepath): # Renamed parameter
    """Reads the entire file content as a single string."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"Error: File not found at {filepath}")
        return None
    except Exception as e:
        print(f"Error reading file {filepath}: {e}")
        return None

def construct_prompt(file_content, user_prompt_template): # Removed language_code
    """Constructs the full prompt, ensuring {srt_content} placeholder exists."""
    content_for_prompt = file_content if file_content else "No file content found."
    full_prompt = user_prompt_template.strip() # Start with user's template

    # --- AUTOMATIC {srt_content} HANDLING ---
    placeholder = "{srt_content}"
    if placeholder not in full_prompt:
        print(f"Warning: Placeholder '{placeholder}' not found in the custom prompt.")
        print(f"Automatically appending '{placeholder}' to the end of the prompt.")
        # Add separator for clarity if appending
        full_prompt += f"\n\n--- Appended File Content Below ---\n{placeholder}"
        # Now replace the appended placeholder
        full_prompt = full_prompt.replace(placeholder, content_for_prompt)
    else:
        # Replace the existing placeholder
        full_prompt = full_prompt.replace(placeholder, content_for_prompt)

    # Removed language name replacement logic

    return full_prompt


def call_generative_ai_api(engine, prompt, api_key, model_name, stream_output=False):
    """Calls the selected AI API (Google or Ollama) to get content."""
    if engine == "google":
        return call_google_gemini_api(prompt, api_key, model_name, stream_output)
    elif engine == "ollama":
        return call_ollama_api(prompt, model_name)
    else:
        print(f"Error: Unknown engine '{engine}'")
        return f"Error: Unknown engine '{engine}'"


def call_google_gemini_api(prompt, api_key, model_name, stream_output=False):
    """Calls the Google Generative AI API."""
    global last_request_time
    if not api_key:
        return "Error: Google API Key not configured."
    if not model_name:
        return "Error: No Google model selected or available."

    try:
        genai.configure(api_key=api_key)
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        ]
        model = genai.GenerativeModel(model_name, safety_settings=safety_settings)

        current_time = time.time()
        if last_request_time is not None:
            time_since_last_request = current_time - last_request_time
            if time_since_last_request < REQUEST_INTERVAL_SECONDS:
                sleep_duration = REQUEST_INTERVAL_SECONDS - time_since_last_request
                print(f"Rate limit active (Google Gemini). Sleeping for {sleep_duration:.2f} seconds...")
                time.sleep(sleep_duration)
        last_request_time = time.time()

        prompt_content = prompt
        print("--- Custom Prompt being sent to Google Gemini API (Model: {}): ---".format(model_name))
        print(prompt_content[:1000] + "..." if len(prompt_content) > 1000 else prompt_content)
        print("--- End of Prompt Snippet ---")
        print(f"--- Calling Google Gemini API with model '{model_name}'... {'Streaming output enabled' if stream_output else '(Non-streaming)'} ---")

        generation_config = genai.types.GenerationConfig(
             # temperature=0.7,
             # max_output_tokens=8192,
         )

        if stream_output:
            response = model.generate_content(prompt_content, generation_config=generation_config, stream=True)
            full_response_text = ""
            print("\n--- Streaming Response ---")
            try:
                for chunk in response:
                    if chunk.text:
                        print(chunk.text, end="", flush=True)
                        full_response_text += chunk.text
                    if chunk.prompt_feedback and chunk.prompt_feedback.block_reason:
                         print(f"\n\nWARNING: Input prompt blocked due to: {chunk.prompt_feedback.block_reason}")
                    if chunk.candidates and chunk.candidates[0].finish_reason != 'STOP':
                        print(f"\n\nWARNING: Generation finished unexpectedly: {chunk.candidates[0].finish_reason}")
            except Exception as stream_error:
                 print(f"\nERROR during streaming: {stream_error}")
                 if not full_response_text:
                     return f"Error: Streaming failed early ({stream_error})"
            print("\n--- End of Stream ---")
            api_response_text = full_response_text.strip()

            # Post-stream safety checks (if response object is accessible after stream ends)
            try:
                if response.prompt_feedback and response.prompt_feedback.block_reason:
                     api_response_text = f"Error: Prompt blocked by safety filter ({response.prompt_feedback.block_reason}).\n{api_response_text}" # Prepend error
                if response.candidates and response.candidates[0].finish_reason == 'SAFETY':
                     api_response_text = f"Error: Response blocked by safety filter.\n{api_response_text}" # Prepend error
            except (AttributeError, IndexError):
                 # Response object might not have these attributes after streaming finishes
                 pass

        else: # Non-streaming
            response = model.generate_content(prompt_content, generation_config=generation_config, stream=False)
            print("\n--- Google Gemini API call completed (non-streaming). ---")

            # Safety/Error checks for non-streaming
            if response.prompt_feedback and response.prompt_feedback.block_reason:
                 print(f"ERROR: Input prompt blocked due to: {response.prompt_feedback.block_reason}")
                 return f"Error: Prompt blocked by safety filter ({response.prompt_feedback.block_reason})."
            if not response.candidates:
                 block_reason = (response.prompt_feedback.block_reason
                                 if response.prompt_feedback and response.prompt_feedback.block_reason
                                 else "Unknown")
                 print(f"ERROR: No candidates found in response (Reason: {block_reason}).")
                 return f"Error: No response generated (Reason: {block_reason})."
            if response.candidates[0].finish_reason != 'STOP':
                 print(f"WARNING: Generation finished unexpectedly: {response.candidates[0].finish_reason}")
                 if response.candidates[0].finish_reason == 'SAFETY':
                      safety_info = getattr(response.candidates[0], 'safety_ratings', 'N/A')
                      print(f"Safety Ratings: {safety_info}")
                      return f"Error: Response generation stopped due to safety ({response.candidates[0].finish_reason}). See console log."

            # Get text if successful
            try:
                api_response_text = response.text
            except ValueError as e:
                 finish_reason = getattr(response.candidates[0], 'finish_reason', 'N/A')
                 print(f"Error accessing response text: {e}. Finish Reason: {finish_reason}")
                 api_response_text = f"Error: Could not retrieve text from response (Finish Reason: {finish_reason})."
            except AttributeError:
                 finish_reason = getattr(response.candidates[0], 'finish_reason', 'N/A') if response.candidates else 'N/A'
                 print(f"Error: Unexpected response structure. Cannot access .text. Finish Reason: {finish_reason}")
                 api_response_text = f"Error: Could not retrieve text from response (Unexpected structure)."

        return api_response_text

    except ResourceExhausted as e:
        print(f"Error: Google Gemini API Quota Exhausted.", file=sys.stderr); return "Error: Google API Quota Exhausted."
    except PermissionDenied as e:
        print(f"Error: Google API Permission Denied. Check API Key.", file=sys.stderr); return "Error: Google API Permission Denied (Check Key)."
    except Exception as e:
        print(f"Error calling Google Gemini API: {e}", file=sys.stderr); return f"Error: Google API Call Failed ({str(e)[:100]})"


def call_ollama_api(prompt, model_name):
    """Calls the local Ollama API."""
    ollama_generate_url = os.environ.get("OLLAMA_API_URL", "http://localhost:11434/api/generate")
    payload = {
        "model": model_name,
        "prompt": prompt,
        "stream": False
    }
    try:
        print(f"--- Calling Ollama API ({model_name}) at {ollama_generate_url} ---")
        print(f"--- Prompt Snippet: {prompt[:500]}... ---")
        response = requests.post(ollama_generate_url, json=payload, timeout=300)
        response.raise_for_status()
        data = response.json()
        print("--- Ollama API call completed. ---")
        if "response" in data:
            return data["response"].strip()
        elif "error" in data:
             print(f"ERROR from Ollama API: {data['error']}")
             return f"Error: Ollama API returned an error - {data['error']}"
        else:
             print("ERROR: Unexpected response structure from Ollama.")
             return "Error: No 'response' field in Ollama output."
    except requests.exceptions.ConnectionError:
        print(f"ERROR: Could not connect to Ollama API at {ollama_generate_url}. Is Ollama running?"); return "Error: Could not connect to Ollama API."
    except requests.exceptions.Timeout:
         print(f"ERROR: Timeout during Ollama generation."); return "Error: Ollama generation timed out."
    except requests.exceptions.RequestException as e:
        error_details = str(e)
        if e.response is not None: error_details += f" - Response: {e.response.text[:200]}"
        print(f"ERROR calling Ollama generate API: {error_details}"); return f"Error: Ollama Request Failed ({error_details})"
    except json.JSONDecodeError:
         print("ERROR: Could not decode JSON response from Ollama generate API."); return "Error: Invalid JSON response from Ollama."
    except Exception as e:
        print(f"ERROR calling Ollama generate API: {e}"); return f"Error: Ollama Call Failed ({e})"


def parse_api_response(api_response):
    """Parses the API response to extract structured data if possible (flexible)."""
    # This parser is generic; effectiveness depends on the LLM following prompt instructions.
    if not api_response or api_response.startswith("Error:"):
        print(f"Debug: parse_api_response - Invalid API response received: {api_response}")
        # Return a structure indicating the error
        return { "title": f"N/A ({api_response or 'Empty Response'})", "description": "", "hashtags": "", "tags": "" } # Removed timestamp section

    try:
        # Simple approach: return the whole response as 'description' if no clear markers found
        # More complex parsing could be added here if needed, but relies on prompt adherence.
        # Example: Look for "Title:", "Description:", etc. but fall back gracefully.
        # For now, we treat the whole output as the primary content.
        parsed_data = {
            "title": "", # Placeholder, might not be extracted unless explicitly requested/formatted
            "description": api_response.strip(),
            "hashtags": "", # Placeholder
            "tags": ""      # Placeholder
        }
        # Optional: Add logic here to look for specific markers like **Title:**
        # if api_response.lstrip().startswith("**Title:"): ... etc.

        # If no specific sections are parsed, the full response is in 'description'.
        return parsed_data

    except Exception as e:
        print(f"Error parsing API response: {e}")
        # Fallback: return raw response in description field
        return { "title": "N/A (Parsing Error)", "description": api_response, "hashtags": "N/A", "tags": "N/A" }


def format_output(parsed_data): # Changed parameter name
    """Formats the parsed data into a user-friendly string."""
    if not parsed_data:
        return "Error: No data to format."

    # Prioritize description as it likely contains the main content
    output = parsed_data.get('description', 'N/A (No description found)')

    # Optionally prepend other extracted fields if they exist and are not N/A
    title = parsed_data.get('title', '')
    if title and not title.startswith("N/A"):
        output = f"**Title:**\n{title}\n\n**Description:**\n{output}" # Assume description follows title

    hashtags = parsed_data.get('hashtags', '')
    if hashtags and not hashtags.startswith("N/A"):
         output += f"\n\n**Hashtags:**\n{hashtags}"

    tags = parsed_data.get('tags', '')
    if tags and not tags.startswith("N/A"):
        output += f"\n\n**Tags:**\n{tags}"

    return output.strip()


def save_raw_api_response(api_response_text, input_filepath, output_folder, output_suffix=DEFAULT_RAW_OUTPUT_SUFFIX):
    """Saves the raw API response to a text file."""
    if not api_response_text:
        print("Debug: save_raw_api_response - No API response text to save.")
        return

    raw_output_folder_path = os.path.join(os.getcwd(), output_folder)
    os.makedirs(raw_output_folder_path, exist_ok=True)

    if not input_filepath or not isinstance(input_filepath, str):
         input_filepath = "unknown_file"
         print("Warning: Invalid input_filepath for save_raw_api_response. Using 'unknown_file'.")

    output_filename_base = os.path.splitext(os.path.basename(input_filepath))[0]
    output_filename = f"{output_filename_base}{output_suffix}{RAW_OUTPUT_FILE_EXTENSION}" # Use constant
    output_filepath = os.path.join(raw_output_folder_path, output_filename)

    try:
        with open(output_filepath, 'w', encoding='utf-8') as outfile:
            outfile.write(api_response_text)
        print(f"Raw API response saved to: {output_filepath}")
    except Exception as e:
        print(f"**ERROR: Could not save raw API response to file: {output_filepath}**\nError details: {e}")


def process_single_file(input_filepath, api_key, engine, user_prompt_template, model_name, stream_output=False, output_suffix=DEFAULT_RAW_OUTPUT_SUFFIX): # Renamed, removed language_code
    """Processes a single input file using the selected engine and custom prompt."""
    raw_file_content = read_raw_srt_content(input_filepath)
    if raw_file_content is None:
        error_msg = f"Error reading input file: {input_filepath}"
        save_raw_api_response(error_msg, input_filepath, RAW_OUTPUT_SUBFOLDER_NAME, output_suffix)
        return None, error_msg

    prompt = construct_prompt(raw_file_content, user_prompt_template) # Removed language_code

    api_response_text = call_generative_ai_api(engine, prompt, api_key, model_name, stream_output)

    save_raw_api_response(api_response_text or "API call failed or returned empty.", input_filepath, RAW_OUTPUT_SUBFOLDER_NAME, output_suffix)

    if not api_response_text or api_response_text.startswith("Error:"):
         return None, api_response_text # Return error from API call

    parsed_data = parse_api_response(api_response_text)

    # Check for parsing failure indicated by N/A title and empty description
    if parsed_data.get("title","").startswith("N/A") and not parsed_data.get("description"):
         return None, f"Error: Failed to parse API response. Raw response saved."

    return format_output(parsed_data), None # Return formatted output and no error


def get_api_key(force_gui=False):
    """Gets the Google API key from env var or prompts the user."""
    api_key = os.environ.get(API_KEY_ENV_VAR_NAME)
    if not api_key or force_gui:
        if not force_gui: print(f"INFO: {API_KEY_ENV_VAR_NAME} environment variable not set.")
        root = tk.Tk(); root.withdraw()
        api_key = tk.simpledialog.askstring("API Key Required", f"Please enter your Google API Key:", show='*')
        root.destroy()
        if not api_key: print("ERROR: Google API Key not provided."); return None
        print("INFO: API Key obtained via GUI prompt.")
    return api_key

# Simple class to mimic args structure if args is None
class ArgsWrapper:
    def __init__(self):
        self.model = None
        self.engine = DEFAULT_ENGINE
        self.output = RAW_OUTPUT_SUBFOLDER_NAME
        self.suffix = DEFAULT_RAW_OUTPUT_SUFFIX
        self.stream = False
        # self.language removed

def use_gui(initial_api_key, command_line_files=None, args=None):
    """Launches a tkinter GUI for script options, with dynamic model loading."""
    window = tk.Tk()
    window.title("GPT Batch Processor")

    api_key_for_fetch = initial_api_key # Use the initially fetched key

    settings = {}
    files_list_var = tk.Variable(value=command_line_files if command_line_files else [])
    engine_var = tk.StringVar(value=args.engine if args else DEFAULT_ENGINE)
    model_var = tk.StringVar()
    output_dir_var = tk.StringVar(value=args.output if args else RAW_OUTPUT_SUBFOLDER_NAME)
    suffix_var = tk.StringVar(value=args.suffix if args else DEFAULT_RAW_OUTPUT_SUFFIX) # Use new default
    stream_output_var = tk.BooleanVar(value=args.stream if args else False)
    # language_var removed

    # --- GUI Layout ---
    current_row = 0

    # Files Section
    files_frame = ttk.Frame(window, padding="10 10 10 10"); files_frame.grid(row=current_row, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))
    current_row += 1
    tk.Label(files_frame, text="Input Files:").grid(row=0, column=0, sticky=tk.NW)
    file_listbox = tk.Listbox(files_frame, listvariable=files_list_var, height=5, width=70, selectmode=tk.EXTENDED); file_listbox.grid(row=1, column=0, sticky=(tk.W, tk.E))
    files_scrollbar = ttk.Scrollbar(files_frame, orient=tk.VERTICAL, command=file_listbox.yview); files_scrollbar.grid(row=1, column=1, sticky=(tk.N, tk.S))
    file_listbox.config(yscrollcommand=files_scrollbar.set)
    file_buttons_frame = ttk.Frame(files_frame); file_buttons_frame.grid(row=1, column=2, sticky=(tk.N, tk.S), padx=(5,0))
    tk.Button(file_buttons_frame, text="Add Files", command=lambda: add_files_to_list(files_list_var, file_listbox, window)).grid(row=0, column=0, sticky=(tk.W, tk.EW), pady=2)
    tk.Button(file_buttons_frame, text="Clear All", command=lambda: files_list_var.set([]), width=10).grid(row=1, column=0, sticky=(tk.W, tk.EW), pady=2)
    tk.Button(file_buttons_frame, text="Remove Sel.", command=lambda: remove_selected_files(files_list_var, file_listbox), width=10).grid(row=2, column=0, sticky=(tk.W, tk.EW), pady=2)

    # Prompt Section
    prompt_frame = ttk.LabelFrame(window, text="Custom Prompt Template", padding="10 10 10 10"); prompt_frame.grid(row=current_row, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
    current_row += 1
    prompt_text_widget = scrolledtext.ScrolledText(prompt_frame, wrap=tk.WORD, width=80, height=15, relief=tk.SOLID, borderwidth=1)
    prompt_text_widget.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S)); prompt_text_widget.insert(tk.INSERT, USER_PROMPT_TEMPLATE)

    # Options Frame (Engine, Model) - Language Removed
    options_frame = ttk.Frame(window, padding="10 10 10 10"); options_frame.grid(row=current_row, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))
    options_frame.columnconfigure(1, weight=1); current_row += 1
    tk.Label(options_frame, text="Engine:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
    engine_options = ['google', 'ollama']; engine_combo = ttk.Combobox(options_frame, textvariable=engine_var, values=engine_options, state="readonly", width=30); engine_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=2)
    tk.Label(options_frame, text="Model:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
    model_combo = ttk.Combobox(options_frame, textvariable=model_var, state="disabled", width=30); model_combo.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5, pady=2)
    # Language row removed

    # Other Settings Frame (Output, Suffix, Stream)
    settings_frame = ttk.Frame(window, padding="10 10 10 10"); settings_frame.grid(row=current_row, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))
    settings_frame.columnconfigure(1, weight=1); current_row += 1
    tk.Label(settings_frame, text="Output Dir:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
    output_entry = ttk.Entry(settings_frame, textvariable=output_dir_var, width=40); output_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=2)
    tk.Button(settings_frame, text="Browse", command=lambda: output_dir_var.set(filedialog.askdirectory(initialdir=os.getcwd(), parent=window) or output_dir_var.get())).grid(row=0, column=2, sticky=tk.E, padx=5)
    tk.Label(settings_frame, text="Raw Suffix:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
    suffix_entry = ttk.Entry(settings_frame, textvariable=suffix_var, width=20); suffix_entry.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
    stream_check = ttk.Checkbutton(settings_frame, text="Stream Output (Google / Experimental)", variable=stream_output_var); stream_check.grid(row=2, column=1, columnspan=2, sticky=tk.W, padx=5, pady=5)

    # --- Dynamic Model Loading Logic (FIXED) ---
    def update_models(cmd_line_args, *trace_details):
        print(f"Updating models for engine: {engine_var.get()}")
        selected_engine = engine_var.get(); models = []; error_msg = None
        model_combo.set(''); model_combo['values'] = []; model_combo.configure(state="disabled")
        if selected_engine == "google":
            models, error_msg = fetch_google_models(api_key_for_fetch)
            if not api_key_for_fetch and not error_msg: error_msg = "Google API Key needed."
        elif selected_engine == "ollama": models, error_msg = fetch_ollama_models()
        if error_msg: model_combo.set(f"Error: {error_msg}"); model_var.set("")
        elif models:
            model_combo['values'] = models; model_combo.configure(state="readonly")
            default_to_set = ""
            if cmd_line_args and cmd_line_args.model and cmd_line_args.model in models:
                default_to_set = cmd_line_args.model; print(f"Using model from command line args: {default_to_set}")
            elif models: default_to_set = models[0]; print(f"Using first available model: {default_to_set}")
            model_var.set(default_to_set)
        else: model_combo.set("No models found"); model_var.set("")

    original_cmd_args = args if args is not None else ArgsWrapper()
    engine_var.trace_add("write", lambda *trace_details: update_models(original_cmd_args, *trace_details))
    window.after(100, lambda: update_models(original_cmd_args))

    # --- Process Button ---
    def process_from_gui():
        settings['files'] = list(files_list_var.get())
        settings['custom_prompt'] = prompt_text_widget.get("1.0", tk.END).strip()
        settings['engine'] = engine_var.get()
        settings['model'] = model_var.get()
        settings['output_dir'] = output_dir_var.get()
        settings['suffix'] = suffix_var.get()
        settings['stream_output'] = stream_output_var.get()
        # language_code removed
        settings['api_key'] = api_key_for_fetch

        # Validation
        if not settings['files']: tkinter.messagebox.showwarning("Input Error", "Please add at least one input file.", parent=window); return
        if not settings['custom_prompt']: # Check only for empty prompt now
             tkinter.messagebox.showwarning("Prompt Warning", "The custom prompt is empty. Proceed anyway?", parent=window); # Removed askyesno, just warn
             # Proceed even if empty, user might want this? Or add 'return' here if empty prompt is invalid.
        # Removed the check for {srt_content} here
        if not settings['model'] or settings['model'].startswith("Error:") or settings['model'] == "No models found": tkinter.messagebox.showwarning("Input Error", "Please select a valid model.", parent=window); return
        if settings['engine'] == 'google' and not settings['api_key']: tkinter.messagebox.showwarning("Input Error", "Google engine selected, but API Key is missing.", parent=window); return

        window.destroy(); window.quit(); return settings

    process_button = ttk.Button(window, text="Process Files", command=process_from_gui); process_button.grid(row=current_row, column=0, columnspan=3, pady=20); current_row += 1

    window.mainloop()
    return settings

# --- GUI Helper Functions ---
def add_files_to_list(files_list_var, file_listbox, window):
    selected_files = filedialog.askopenfilenames(parent=window, title="Select Input Files", filetypes=[("Text files", "*.srt *.txt *.md"), ("All files", "*.*")])
    if selected_files:
        current_files = list(files_list_var.get())
        added_count = 0
        for f_raw in selected_files:
            f = os.path.normpath(f_raw).replace("\\", "/")
            if f not in current_files: current_files.append(f); added_count += 1
        if added_count > 0: files_list_var.set(tuple(current_files)); file_listbox.see(tk.END)

def remove_selected_files(files_list_var, file_listbox):
     selected_indices = file_listbox.curselection()
     if not selected_indices: return
     current_files = list(files_list_var.get()); removed_count = 0
     for i in sorted(selected_indices, reverse=True):
         try: del current_files[i]; removed_count += 1
         except IndexError: print(f"Warning: Index {i} out of bounds during removal.")
     if removed_count > 0: files_list_var.set(tuple(current_files))


def main():
    initial_api_key = get_api_key()

    parser = argparse.ArgumentParser(description="GPT Batch Processor - Process text files using AI")
    parser.add_argument("files", nargs="*", help="Path(s) to input text file(s) (e.g., *.srt, *.txt, *.md). Supports patterns.")
    parser.add_argument("-o", "--output", default=RAW_OUTPUT_SUBFOLDER_NAME, help=f"Output directory for raw responses. Default: '{RAW_OUTPUT_SUBFOLDER_NAME}'.")
    parser.add_argument("-s", "--suffix", default=DEFAULT_RAW_OUTPUT_SUFFIX, help=f"Suffix for raw output filenames. Default: '{DEFAULT_RAW_OUTPUT_SUFFIX}'.") # Uses new default
    parser.add_argument("--stream", action='store_true', default=False, help="Enable streaming output (Google / Experimental).")
    parser.add_argument("-e", "--engine", default=DEFAULT_ENGINE, choices=['google', 'ollama'], help=f"AI engine to use. Default: '{DEFAULT_ENGINE}'.")
    parser.add_argument("-m", "--model", dest="model", default=None, help="Default model (GUI selection overrides).")
    # Removed language argument

    args = parser.parse_args()

    filepaths_from_cli = []
    if args.files:
        print("Expanding file patterns from command line...")
        for pattern in args.files:
            try:
                expanded_files = glob.glob(pattern, recursive=True)
                if not expanded_files: print(f"Warning: Pattern '{pattern}' did not match any files.")
                else:
                    print(f"  Pattern '{pattern}' matched: {len(expanded_files)} file(s)")
                    filepaths_from_cli.extend([os.path.normpath(f).replace("\\", "/") for f in expanded_files])
            except Exception as e: print(f"Error processing pattern '{pattern}': {e}")
        filepaths_from_cli = sorted(list(set(filepaths_from_cli)))
        print(f"Total unique files from command line: {len(filepaths_from_cli)}")

    gui_settings = use_gui(initial_api_key=initial_api_key, command_line_files=filepaths_from_cli, args=args)
    if not gui_settings: print("Operation cancelled via GUI."); return

    input_file_paths_gui = gui_settings.get('files', [])
    custom_prompt_template = gui_settings.get('custom_prompt', USER_PROMPT_TEMPLATE)
    output_folder_base = gui_settings.get('output_dir', RAW_OUTPUT_SUBFOLDER_NAME)
    suffix = gui_settings.get('suffix')
    stream_output = gui_settings.get('stream_output')
    engine = gui_settings.get('engine')
    model_name = gui_settings.get('model')
    final_api_key = gui_settings.get('api_key')
    # language_code removed

    if not input_file_paths_gui: print("Error: No input files selected for processing."); return
    if not custom_prompt_template: print("Warning: Custom prompt is empty. Processing will continue but may yield unexpected results."); # Warn if empty
    # Removed check for {srt_content} as it's handled automatically
    if not model_name: print("Error: No model selected in the GUI."); return
    if engine == 'google' and not final_api_key: print("Error: Google engine selected, but final API Key is missing."); return

    all_input_filepaths = sorted(list(set(input_file_paths_gui)))
    if not all_input_filepaths: print("Error: No valid input file paths specified."); return

    output_folder_path = os.path.join(os.getcwd(), output_folder_base)
    try: os.makedirs(output_folder_path, exist_ok=True); print(f"Ensured output directory exists: {output_folder_path}")
    except OSError as e: print(f"Error creating output directory '{output_folder_path}': {e}"); return

    processed_files = 0; failed_files = 0; total_files = len(all_input_filepaths)
    print(f"\nStarting batch processing for {total_files} file(s)...")
    print(f"Engine: {engine}, Model: {model_name}") # Removed language
    print(f"Output Directory: {output_folder_path}")
    print("-" * 50)

    for i, input_filepath in enumerate(all_input_filepaths):
        print(f"\n--- Processing file {i + 1}/{total_files} ---")
        print(f"File: {input_filepath}")
        # Removed language print

        formatted_output, error_message = process_single_file( # Renamed function call
            input_filepath=input_filepath,
            api_key=final_api_key,
            engine=engine,
            user_prompt_template=custom_prompt_template,
            model_name=model_name,
            stream_output=(stream_output and engine == 'google'),
            output_suffix=suffix
            # language_code removed
        )

        if formatted_output and not error_message:
            print("\n--- Generated Content (Console Output Only) ---")
            print(formatted_output)
            print("--- End of Generated Content ---")
            processed_files += 1
        else:
            print(f"\n--- FAILED to process file: {input_filepath} ---")
            print(f"Error: {error_message or 'Unknown processing error.'}")
            failed_files += 1
        print("-" * 30)

    print("\n=========================================")
    print("          Batch Processing Summary")
    print("=========================================")
    print(f"Total files attempted: {total_files}")
    print(f"Successfully processed: {processed_files}")
    print(f"Failed: {failed_files}")
    if processed_files > 0 or failed_files > 0: print(f"\nRaw API responses saved in: '{output_folder_path}'")
    if processed_files > 0: print("Formatted content was printed to the console above for successful files.")
    if failed_files > 0: print("\nCheck the console output and raw response files for details on failures.")
    print("=========================================")


if __name__ == "__main__":
    main()