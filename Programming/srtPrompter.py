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

""" + "\n\n" + "Full SRT file content:\n{srt_content}"

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
RAW_OUTPUT_SUBFOLDER_NAME = "SEO_prompts" # Subfolder for raw API responses - RENAMED to ytSEO


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