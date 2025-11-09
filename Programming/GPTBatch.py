"""
================================================================================
Multimodal AI Batch Processor (GPTBatcher) v19_mod_lmstudio (with Output Extension)
================================================================================
Purpose:
--------
This script provides a powerful tool for batch-processing local files (both
text and images) using generative AI models. It features a graphical user
interface (GUI) for easy operation and supports the Google Gemini API, a
local Ollama instance, and a local LM Studio instance. If run without any file
arguments, it will automatically scan the current directory for all supported
file types. For each file processed, it saves the raw AI response and a detailed
processing log.
Key Features:
-------------
- Triple AI Engine Support: Seamlessly switch between Google's cloud API, a
  local Ollama instance, or a local LM Studio instance.
- Automatic File Discovery: If launched without command-line file arguments,
  it automatically finds and loads all supported file types from the current
  directory.
- Resizable Two-Pane GUI: The interface is a modern, wide layout with a
  draggable sash, allowing dynamic resizing to fit any screen.
- Multimodal Input & Grouping: Natively handles text/image files and can
  process them in validated groups.
- Configurable Safety Settings (Google): A dedicated GUI section to control
  Google's safety filters, defaulting to OFF.
- User-Friendly Interface: An intuitive layout for adding files, editing the
  prompt, selecting models, and configuring outputs.
- Comprehensive Logging & Naming: Generates detailed logs with descriptive
  output filenames for groups.
- Interactive Quota Handling: Pauses on quota errors, allowing the user to
  switch models or quit.
- Robust Failure Handling: Copies original source files to a "failed"
  subfolder upon any failure.
- API Rate Limiting: Includes an automatic delay for the Google Gemini API.
- NEW: The final summary now includes the specific reason for each file's failure.
- NEW: Option to add the filename to the prompt before the file content.
- NEW: Added support for LM Studio as an AI provider.
- NEW: Added a sanitizer to remove Markdown code fences (```) from API output.
- NEW: Option to overwrite the original input file with the AI-generated output.
- ✅ UPDATED: Output filename extension matches input extension for single text files,
              with safe unique naming to prevent overwrites.
- ✅ NEW: User can specify custom output extension (e.g., md, srt). If empty, uses default logic.
Dependencies:
-------------
pip install google-generativeai requests
Setup & Usage:
--------------
1. Configure your Google API Key (preferably via the GOOGLE_API_KEY env var).
2. For local models, ensure Ollama or LM Studio's server is running.
3. Run from the command line in one of two ways:
   a) To process specific files (supports wildcards):
      `python <script_name>.py *.jpg *.txt`
   b) To automatically find and load all supported files in the folder:
      `python <script_name>.py`
4. The GUI will appear, pre-loaded with the files. You can drag the central
   divider to resize the input and settings columns.
--------------------------------------------------------------------------------
"""
import os
import sys
import json
import requests
import glob
import time
import datetime
import google.generativeai as genai
from google.api_core.exceptions import GoogleAPIError, ResourceExhausted, PermissionDenied
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import argparse
import tkinter as tk
from tkinter import ttk
from tkinter import scrolledtext
from tkinter import filedialog
import tkinter.messagebox
import tkinter.simpledialog
import base64
import mimetypes
import traceback
import re
import shutil

################################################################################
# --- Customizable Variables (Configuration) ---
################################################################################
API_KEY_ENV_VAR_NAME = "GOOGLE_API_KEY"
# Ollama Configuration
OLLAMA_API_URL = os.environ.get("OLLAMA_API_URL", "http://localhost:11434")
OLLAMA_TAGS_ENDPOINT = f"{OLLAMA_API_URL}/api/tags"
OLLAMA_GENERATE_ENDPOINT = f"{OLLAMA_API_URL}/api/generate"
# LM Studio Configuration
LMSTUDIO_API_URL = os.environ.get("LMSTUDIO_API_URL", "http://localhost:1234/v1")
LMSTUDIO_MODELS_ENDPOINT = f"{LMSTUDIO_API_URL}/models"
LMSTUDIO_CHAT_COMPLETIONS_ENDPOINT = f"{LMSTUDIO_API_URL}/chat/completions"

USER_PROMPT_TEMPLATE = """Analyze the provided content (text or image).
If text is provided below: Summarize the key points, identify main topics, and suggest relevant keywords.
If one or more images are provided: Describe the image(s) in detail. If multiple, note any relationships or differences. Suggest relevant keywords or tags.
Provide the output as plain text.
"""

SUPPORTED_TEXT_EXTENSIONS = ['.txt', '.srt', '.md', '.py', '.js', '.html', '.css']
SUPPORTED_IMAGE_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.webp', '.heic', '.heif']
ALL_SUPPORTED_EXTENSIONS = SUPPORTED_TEXT_EXTENSIONS + SUPPORTED_IMAGE_EXTENSIONS

DEFAULT_RAW_OUTPUT_SUFFIX = ""
RAW_OUTPUT_FILE_EXTENSION = ".txt"
LOG_FILE_EXTENSION = ".log"
DEFAULT_ENGINE = "google"
REQUESTS_PER_MINUTE = 15
REQUEST_INTERVAL_SECONDS = 60 / REQUESTS_PER_MINUTE
DEFAULT_OUTPUT_SUBFOLDER_NAME = ""
LOG_SUBFOLDER_NAME = "processing_logs"
FAILED_SUBFOLDER_NAME = "failed"
MAX_BATCH_SIZE_MB = 15
MAX_BATCH_SIZE_BYTES = MAX_BATCH_SIZE_MB * 1024 * 1024

################################################################################
# --- End of Customizable Variables ---
################################################################################

class QuotaExhaustedError(Exception): pass

last_request_time = None

def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]

def generate_group_base_name(filepaths_group):
    if not filepaths_group:
        return "empty_group"
    base_names = [os.path.splitext(os.path.basename(fp)) for fp in filepaths_group]
    if len(base_names) == 1:
        return base_names[0][0]  # Return filename without extension
    else:
        return f"{base_names[0][0]}_to_{base_names[-1][0]}"  # First and last filenames

def fetch_google_models(api_key):
    if not api_key:
        return [], "API key not available."
    try:
        print("Fetching Google AI models...")
        genai.configure(api_key=api_key)
        models = [m.name for m in genai.list_models() if "generateContent" in m.supported_generation_methods]
        models.sort(key=lambda x: (not ('1.5' in x or 'pro' in x or 'flash' in x), x))
        print(f"Found and sorted Google models: {models}")
        return models, None
    except PermissionDenied:
        return [], "Google API Permission Denied. Check API key permissions."
    except GoogleAPIError as e:
        return [], f"Google API Error: {e}"
    except Exception as e:
        return [], f"An unexpected error occurred: {e}"

def fetch_ollama_models():
    try:
        print(f"Fetching Ollama models from {OLLAMA_TAGS_ENDPOINT}...")
        response = requests.get(OLLAMA_TAGS_ENDPOINT, timeout=10)
        response.raise_for_status()
        models = sorted([m.get("name") for m in response.json().get("models", []) if m.get("name")])
        print(f"Found Ollama models: {models}")
        return models, None
    except requests.exceptions.ConnectionError:
        return [], f"Connection Error: Is Ollama running at {OLLAMA_API_URL}?"
    except requests.exceptions.RequestException as e:
        return [], f"Ollama Request Error: {e}"
    except Exception as e:
        return [], f"An unexpected error occurred: {e}"

def fetch_lmstudio_models():
    try:
        print(f"Fetching LM Studio models from {LMSTUDIO_MODELS_ENDPOINT}...")
        response = requests.get(LMSTUDIO_MODELS_ENDPOINT, timeout=10)
        response.raise_for_status()
        models = sorted([m.get("id") for m in response.json().get("data", []) if m.get("id")])
        print(f"Found LM Studio models: {models}")
        return models, None
    except requests.exceptions.ConnectionError:
        return [], f"Connection Error: Is LM Studio server running at {os.path.dirname(LMSTUDIO_API_URL)}?"
    except requests.exceptions.RequestException as e:
        return [], f"LM Studio Request Error: {e}"
    except Exception as e:
        return [], f"An unexpected error occurred while fetching LM Studio models: {e}"

def read_file_content(filepath):
    _, extension = os.path.splitext(filepath)
    ext = extension.lower()
    try:
        if ext in SUPPORTED_TEXT_EXTENSIONS:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read(), 'text/plain', False, None
        elif ext in SUPPORTED_IMAGE_EXTENSIONS:
            mime_type, _ = mimetypes.guess_type(filepath)
            with open(filepath, 'rb') as f:
                return f.read(), mime_type or 'application/octet-stream', True, None
        else:
            return None, None, False, f"Unsupported file extension '{ext}'"
    except Exception as e:
        return None, None, False, f"Error reading file {filepath}: {e}"

def sanitize_api_response(text):
    if not text:
        return ""
    pattern = re.compile(r"^\s*```[a-z]*\s*\n?(.*?)\n?\s*```\s*$", re.DOTALL)
    match = pattern.match(text.strip())
    if match:
        return match.group(1).strip()
    return text.strip()

def call_generative_ai_api(engine, prompt_text, api_key, model_name, **kwargs):
    if engine == "google":
        return call_google_gemini_api(prompt_text, api_key, model_name, **kwargs)
    elif engine == "ollama":
        return call_ollama_api(prompt_text, model_name, **kwargs)
    elif engine == "lmstudio":
        return call_lmstudio_api(prompt_text, model_name, **kwargs)
    else:
        return f"Error: Unknown engine '{engine}'"

def call_google_gemini_api(prompt_text, api_key, model_name, images_data_list=None, stream_output=False, safety_settings=None):
    global last_request_time
    if not api_key:
        return "Error: Google API Key not configured."
    if not model_name:
        return "Error: No Google model selected."
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name, safety_settings=safety_settings)
        if last_request_time and (time.time() - last_request_time < REQUEST_INTERVAL_SECONDS):
            sleep_duration = REQUEST_INTERVAL_SECONDS - (time.time() - last_request_time)
            print(f"Rate limit active. Sleeping for {sleep_duration:.2f} seconds...")
            time.sleep(sleep_duration)
        last_request_time = time.time()
        payload = [prompt_text]
        if images_data_list:
            for img_data in images_data_list:
                payload.append({"inline_data": {"mime_type": img_data['mime_type'], "data": img_data['bytes']}})
        print(f"Sending request to Google Gemini (Model: {model_name}) with {len(images_data_list or [])} image(s)...")
        response = model.generate_content(payload, stream=stream_output)
        if stream_output:
            return sanitize_api_response("".join(chunk.text for chunk in response))
        else:
            try:
                return sanitize_api_response(response.text)
            except ValueError:
                if response.prompt_feedback and response.prompt_feedback.block_reason:
                    return f"Error: Request blocked by safety filter. Reason: {response.prompt_feedback.block_reason.name}"
                if response.candidates and response.candidates.finish_reason.name != "STOP":
                    return f"Error: No content generated. Finish Reason: {response.candidates.finish_reason.name}"
                return "Error: No content generated (Reason unknown, response was empty)."
    except ResourceExhausted:
        print(f"QUOTA ERROR: Google Gemini API Quota Exhausted for model {model_name}.", file=sys.stderr)
        raise QuotaExhaustedError(f"Quota exhausted for model {model_name}")
    except PermissionDenied:
        return "Error: Google API Permission Denied (Check Key)."
    except GoogleAPIError as e:
        return f"Error: Google API Call Failed - {e}"
    except Exception as e:
        traceback.print_exc()
        return f"Error: Unexpected Google API issue - {e}"

def call_ollama_api(prompt_text, model_name, images_data_list=None, **kwargs):
    payload = {"model": model_name, "prompt": prompt_text, "stream": False}
    if images_data_list:
        payload["images"] = [base64.b64encode(img_data['bytes']).decode('utf-8') for img_data in images_data_list]
    try:
        print(f"Calling Ollama API ({model_name}) with {len(images_data_list or [])} image(s) at {OLLAMA_GENERATE_ENDPOINT}")
        response = requests.post(OLLAMA_GENERATE_ENDPOINT, json=payload, timeout=600)
        response.raise_for_status()
        data = response.json()
        if "response" in data:
            return sanitize_api_response(data["response"])
        if "error" in data:
            return f"Error: Ollama API returned an error - {data['error']}"
        return "Error: Unexpected response format from Ollama."
    except requests.exceptions.RequestException as e:
        return f"Error: Could not connect to Ollama API - {e}"
    except Exception as e:
        traceback.print_exc()
        return f"Error: Unexpected Ollama Call Failed - {e}"

def call_lmstudio_api(prompt_text, model_name, images_data_list=None, **kwargs):
    headers = {"Content-Type": "application/json"}
    message_content = [{"type": "text", "text": prompt_text}]
    if images_data_list:
        for img_data in images_data_list:
            base64_image = base64.b64encode(img_data['bytes']).decode('utf-8')
            message_content.append({"type": "image_url", "image_url": {"url": f"data:{img_data['mime_type']};base64,{base64_image}"}})
    payload = {"model": model_name, "messages": [{"role": "user", "content": message_content}], "stream": False}
    try:
        print(f"Calling LM Studio API ({model_name}) with {len(images_data_list or [])} image(s) at {LMSTUDIO_CHAT_COMPLETIONS_ENDPOINT}")
        response = requests.post(LMSTUDIO_CHAT_COMPLETIONS_ENDPOINT, headers=headers, json=payload, timeout=600)
        response.raise_for_status()
        data = response.json()
        if data.get("choices") and len(data["choices"]) > 0:
            return sanitize_api_response(data["choices"][0]["message"]["content"])
        if "error" in data:
            return f"Error: LM Studio API returned an error - {data['error']}"
        return "Error: Unexpected response format from LM Studio."
    except requests.exceptions.RequestException as e:
        return f"Error: Could not connect to LM Studio API - {e}"
    except Exception as e:
        traceback.print_exc()
        return f"Error: Unexpected LM Studio Call Failed - {e}"

def determine_unique_output_paths(base_name, suffix, out_folder, log_folder, output_extension=RAW_OUTPUT_FILE_EXTENSION):
    out_base = f"{base_name}{suffix}"
    def find_unique(folder, base, ext):
        path = os.path.join(folder, f"{base}{ext}")
        if not os.path.exists(path):
            return path
        i = 1
        while True:
            path = os.path.join(folder, f"{base} ({i}){ext}")
            if not os.path.exists(path):
                return path
            i += 1
    raw_path = find_unique(out_folder, out_base, output_extension)
    log_path = find_unique(log_folder, out_base, LOG_FILE_EXTENSION)
    return raw_path, log_path

def save_raw_api_response(text, filepath):
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(text or "[Info: API response was empty]")
    except Exception as e:
        print(f"**ERROR: Could not save raw API response to {filepath}: {e}**")

def save_processing_log(log_data, log_filepath):
    try:
        with open(log_filepath, 'w', encoding='utf-8') as f:
            f.write("="*20 + " Processing Log " + "="*20 + "\n")
            for k, v in log_data.items():
                if isinstance(v, datetime.datetime):
                    v = v.strftime("%Y-%m-%d %H:%M:%S")
                elif isinstance(v, float):
                    v = f"{v:.2f} seconds"
                f.write(f"{k.replace('_', ' ').title()}: {v}\n")
            f.write("="*56 + "\n")
        print(f"Processing log saved to: {log_filepath}")
    except Exception as e:
        print(f"**ERROR: Could not save processing log to {log_filepath}: {e}**")

def copy_failed_file(filepath):
    try:
        source_dir = os.path.dirname(os.path.abspath(filepath))
        failed_dir = os.path.join(source_dir, FAILED_SUBFOLDER_NAME)
        os.makedirs(failed_dir, exist_ok=True)
        dest_path = os.path.join(failed_dir, os.path.basename(filepath))
        shutil.copy2(filepath, dest_path)
        print(f"Copied failed source file to: {dest_path}")
    except Exception as e:
        print(f"**ERROR: Could not copy failed file {filepath}: {e}**", file=sys.stderr)

def process_file_group(filepaths_group, api_key, engine, user_prompt, model_name, add_filename_to_prompt=False, overwrite_original=False, **kwargs):
    start_time = datetime.datetime.now()
    base_name = generate_group_base_name(filepaths_group)
    log_data = {'input_filepaths': filepaths_group, 'start_time': start_time, 'engine': engine, 'model_name': model_name, 'status': 'Failure'}
    api_response = None
    # Determine output paths
    if overwrite_original and len(filepaths_group) == 1:
        raw_path = filepaths_group[0]
        log_folder_for_overwrite = os.path.join(os.path.dirname(raw_path), LOG_SUBFOLDER_NAME)
        os.makedirs(log_folder_for_overwrite, exist_ok=True)
        _, log_path = determine_unique_output_paths(base_name, kwargs['output_suffix'], log_folder_for_overwrite, log_folder_for_overwrite)
    else:
        # Determine output extension
        user_output_ext = kwargs.get('output_extension', '').strip()
        if user_output_ext:
            output_ext = '.' + user_output_ext.lstrip('.')
        else:
            if len(filepaths_group) == 1:
                filepath = filepaths_group[0]
                _, orig_ext = os.path.splitext(filepath)
                orig_ext = orig_ext.lower()
                if orig_ext in SUPPORTED_TEXT_EXTENSIONS:
                    output_ext = orig_ext
                else:
                    output_ext = RAW_OUTPUT_FILE_EXTENSION
            else:
                output_ext = RAW_OUTPUT_FILE_EXTENSION  # groups always use .txt

        raw_path, log_path = determine_unique_output_paths(
            base_name, kwargs['output_suffix'], kwargs['output_folder'], kwargs['log_folder'], output_ext
        )
    try:
        images_data, text_content_parts, prompt = [], [], user_prompt
        print(f"--- Reading {len(filepaths_group)} file(s) for this group ---")
        for filepath in filepaths_group:
            content, mime, is_image, err = read_file_content(filepath)
            if err:
                raise ValueError(f"Error reading {filepath}: {err}")
            if is_image:
                images_data.append({"bytes": content, "mime_type": mime})
            else:
                if add_filename_to_prompt:
                    filename_no_ext = os.path.splitext(os.path.basename(filepath))[0]
                    text_content_parts.append(f"\n--- Filename: {filename_no_ext} ---")
                text_content_parts.append(f"\n--- File Content Start: {os.path.basename(filepath)} ---\n{content}\n--- File Content End ---")
        if text_content_parts:
            prompt += "".join(text_content_parts)
        log_data['prompt_sent'] = prompt
        api_response = call_generative_ai_api(engine, prompt, api_key, model_name, images_data_list=images_data, stream_output=kwargs['stream_output'], safety_settings=kwargs.get('safety_settings'))
        if api_response and api_response.startswith("Error:"):
            raise Exception(api_response)
        log_data['status'] = 'Success'
        return api_response, None
    except Exception as e:
        print(f"**ERROR during processing group starting with {os.path.basename(filepaths_group[0])}: {e}**")
        log_data.update({'error_message': str(e), 'traceback_info': traceback.format_exc() if not isinstance(e, (QuotaExhaustedError, KeyboardInterrupt)) else "N/A"})
        if isinstance(e, (QuotaExhaustedError, KeyboardInterrupt)):
            raise
        return None, str(e)
    finally:
        if log_data['status'] == 'Success':
            save_raw_api_response(api_response, raw_path)
        log_data.update({'end_time': datetime.datetime.now(), 'duration': (datetime.datetime.now() - start_time).total_seconds()})
        save_processing_log(log_data, log_path)

def get_api_key(force_gui=False):
    api_key = os.environ.get(API_KEY_ENV_VAR_NAME)
    if not api_key or force_gui:
        if not force_gui:
            print(f"INFO: {API_KEY_ENV_VAR_NAME} environment variable not set.")
        root = tk.Tk()
        root.withdraw()
        try:
            api_key = tk.simpledialog.askstring("API Key Required", "Please enter your Google API Key:", show='*')
        finally:
            root.destroy()
        if api_key:
            print("INFO: API Key obtained via GUI prompt.")
        else:
            print("ERROR: Google API Key not provided.")
            return None
    return api_key

class AppGUI(tk.Tk):
    def __init__(self, initial_api_key, command_line_files, args):
        super().__init__()
        self.title("Multimodal AI Batch Processor")
        self.geometry("900x700")
        self.settings = None
        self.api_key = initial_api_key
        self.args = args or argparse.Namespace()
        self.files_var = tk.Variable(value=list(command_line_files or []))
        self.engine_var = tk.StringVar(value=getattr(self.args, 'engine', DEFAULT_ENGINE))
        self.model_var = tk.StringVar()
        self.output_dir_var = tk.StringVar(value=getattr(self.args, 'output', DEFAULT_OUTPUT_SUBFOLDER_NAME))
        self.suffix_var = tk.StringVar(value=getattr(self.args, 'suffix', DEFAULT_RAW_OUTPUT_SUFFIX))
        self.output_ext_var = tk.StringVar(value=getattr(self.args, 'output_ext', ''))  # <-- NEW
        self.stream_var = tk.BooleanVar(value=getattr(self.args, 'stream', False))
        self.add_filename_var = tk.BooleanVar(value=getattr(self.args, 'add_filename_to_prompt', False))
        self.group_files_var = tk.BooleanVar(value=False)
        self.group_size_var = tk.IntVar(value=3)
        self.batch_size_warning = tk.BooleanVar(value=False)
        self.overwrite_var = tk.BooleanVar(value=False)
        self.safety_map = {
            'Off (Block None)': HarmBlockThreshold.BLOCK_NONE,
            'Block High Severity Only': HarmBlockThreshold.BLOCK_ONLY_HIGH,
            'Block Medium & Above': HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            'Block Low & Above': HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
        }
        self.enable_safety_var = tk.BooleanVar(value=False)
        default_safety_level = 'Off (Block None)'
        self.harassment_var = tk.StringVar(value=default_safety_level)
        self.hate_speech_var = tk.StringVar(value=default_safety_level)
        self.sexually_explicit_var = tk.StringVar(value=default_safety_level)
        self.dangerous_content_var = tk.StringVar(value=default_safety_level)
        self.create_widgets()
        self.engine_var.trace_add("write", self.update_models)
        self.after(150, self.update_models)
        self.after(200, self.validate_batch_sizes)

    def create_widgets(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        api_frame = ttk.Frame(self, padding=(10, 10, 10, 5))
        api_frame.grid(row=0, column=0, sticky="ew")
        self.api_status_label = ttk.Label(api_frame, text=f"API Key Status: {'Set' if self.api_key else 'Not Set'}")
        self.api_status_label.pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(api_frame, text="Enter/Update Google API Key", command=self.prompt_for_api_key).pack(side=tk.LEFT)

        paned_window = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned_window.grid(row=1, column=0, sticky="nsew", padx=10)

        left_pane = ttk.Frame(paned_window, padding=5)
        left_pane.columnconfigure(0, weight=1)
        left_pane.rowconfigure(1, weight=1)
        paned_window.add(left_pane, weight=1)

        files_frame = ttk.LabelFrame(left_pane, text="Input Files", padding=10)
        files_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 5))
        files_frame.columnconfigure(0, weight=1)
        files_frame.rowconfigure(0, weight=1)

        self.file_listbox = tk.Listbox(files_frame, listvariable=self.files_var, selectmode=tk.EXTENDED)
        self.file_listbox.grid(row=0, column=0, sticky="nsew")
        files_scrollbar = ttk.Scrollbar(files_frame, orient=tk.VERTICAL, command=self.file_listbox.yview)
        files_scrollbar.grid(row=0, column=1, sticky="ns")
        self.file_listbox.config(yscrollcommand=files_scrollbar.set)

        btn_frame = ttk.Frame(files_frame)
        btn_frame.grid(row=0, column=2, sticky="ns", padx=(5,0))
        ttk.Button(btn_frame, text="Add Files...", command=self.add_files).pack(fill=tk.X)
        ttk.Button(btn_frame, text="Remove Sel.", command=self.remove_files).pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="Clear All", command=self.clear_files).pack(fill=tk.X)

        prompt_frame = ttk.LabelFrame(left_pane, text="User Prompt", padding=10)
        prompt_frame.grid(row=1, column=0, sticky="nsew")
        prompt_frame.columnconfigure(0, weight=1)
        prompt_frame.rowconfigure(0, weight=1)

        self.prompt_text = scrolledtext.ScrolledText(prompt_frame, wrap=tk.WORD, height=8)
        self.prompt_text.grid(row=0, column=0, sticky="nsew")
        self.prompt_text.insert(tk.INSERT, USER_PROMPT_TEMPLATE)

        right_pane = ttk.Frame(paned_window, padding=5)
        paned_window.add(right_pane, weight=1)
        right_pane.columnconfigure(0, weight=1)

        options_frame = ttk.LabelFrame(right_pane, text="AI Options", padding=10)
        options_frame.pack(fill=tk.X, pady=(0, 5))
        options_frame.columnconfigure(1, weight=1)
        ttk.Label(options_frame, text="AI Engine:").grid(row=0, column=0, sticky=tk.W)
        ttk.Combobox(options_frame, textvariable=self.engine_var, values=['google', 'ollama', 'lmstudio'], state="readonly").grid(row=0, column=1, sticky=tk.EW)
        ttk.Label(options_frame, text="Model:").grid(row=1, column=0, sticky=tk.W, pady=(5,0))
        self.model_combo = ttk.Combobox(options_frame, textvariable=self.model_var, state="disabled")
        self.model_combo.grid(row=1, column=1, sticky=tk.EW, pady=(5,0))
        ttk.Checkbutton(options_frame, text="Append filename to prompt before content", variable=self.add_filename_var).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(5,0))

        grouping_frame = ttk.LabelFrame(right_pane, text="Batch Grouping", padding=10)
        grouping_frame.pack(fill=tk.X, pady=5)
        self.group_check = ttk.Checkbutton(grouping_frame, text="Process multiple files in one API call", variable=self.group_files_var, command=self.toggle_grouping_options)
        self.group_check.grid(row=0, column=0, columnspan=2, sticky=tk.W)
        ttk.Label(grouping_frame, text="Files per call:").grid(row=1, column=0, sticky=tk.W, padx=(5,0))
        self.group_size_spinbox = ttk.Spinbox(grouping_frame, from_=2, to=100, textvariable=self.group_size_var, width=5, state="disabled", command=self.validate_batch_sizes)
        self.group_size_spinbox.grid(row=1, column=1, sticky=tk.W)
        self.group_status_label = ttk.Label(grouping_frame, text="")
        self.group_status_label.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(5,0))

        safety_frame = ttk.LabelFrame(right_pane, text="Google Safety Settings", padding=10)
        safety_frame.pack(fill=tk.X, pady=5)
        safety_frame.columnconfigure(1, weight=1)
        self.safety_check = ttk.Checkbutton(safety_frame, text="Enable Safety Filters (Defaults to Off)", variable=self.enable_safety_var, command=self.toggle_safety_widgets)
        self.safety_check.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 5))
        self.safety_widgets = []
        categories = [("Harassment:", self.harassment_var), ("Hate Speech:", self.hate_speech_var), ("Sexually Explicit:", self.sexually_explicit_var), ("Dangerous Content:", self.dangerous_content_var)]
        for i, (label_text, var) in enumerate(categories):
            label = ttk.Label(safety_frame, text=label_text)
            label.grid(row=i+1, column=0, sticky=tk.W, padx=5, pady=1)
            combo = ttk.Combobox(safety_frame, textvariable=var, values=list(self.safety_map.keys()), state="disabled", width=25)
            combo.grid(row=i+1, column=1, sticky=tk.EW, pady=1)
            self.safety_widgets.extend([label, combo])

        settings_frame = ttk.LabelFrame(right_pane, text="Output Settings", padding=10)
        settings_frame.pack(fill=tk.X, pady=5)
        settings_frame.columnconfigure(1, weight=1)

        ttk.Label(settings_frame, text="Output Dir:").grid(row=0, column=0, sticky=tk.W)
        self.output_dir_entry = ttk.Entry(settings_frame, textvariable=self.output_dir_var)
        self.output_dir_entry.grid(row=0, column=1, sticky=tk.EW)
        self.browse_button = ttk.Button(settings_frame, text="Browse...", command=self.browse_output_dir)
        self.browse_button.grid(row=0, column=2, padx=(5,0))

        ttk.Label(settings_frame, text="Output Suffix:").grid(row=1, column=0, sticky=tk.W, pady=(5,0))
        self.suffix_entry = ttk.Entry(settings_frame, textvariable=self.suffix_var)
        self.suffix_entry.grid(row=1, column=1, sticky=tk.W, pady=(5,0))

        # --- NEW: Output Extension Field ---
        ttk.Label(settings_frame, text="Output Extension:").grid(row=2, column=0, sticky=tk.W, pady=(5,0))
        self.output_ext_entry = ttk.Entry(settings_frame, textvariable=self.output_ext_var)
        self.output_ext_entry.grid(row=2, column=1, sticky=tk.W, pady=(5,0))

        ttk.Checkbutton(settings_frame, text="Stream Output (Google Only)", variable=self.stream_var).grid(row=3, column=0, columnspan=2, sticky=tk.W)

        self.overwrite_check = ttk.Checkbutton(settings_frame, text="Overwrite original input file", variable=self.overwrite_var, command=self.toggle_overwrite_options)
        self.overwrite_check.grid(row=4, column=0, columnspan=2, sticky=tk.W)

        ttk.Button(self, text="Process Files", command=self.process).grid(row=2, column=0, pady=(5, 10))

    def toggle_overwrite_options(self):
        if self.overwrite_var.get():
            self.group_files_var.set(False)
            self.group_check.config(state="disabled")
            self.group_size_spinbox.config(state="disabled")
            self.output_dir_entry.config(state="disabled")
            self.browse_button.config(state="disabled")
            self.suffix_entry.config(state="disabled")
            self.output_ext_entry.config(state="disabled")  # <-- NEW
        else:
            self.group_check.config(state="normal")
            self.group_size_spinbox.config(state="normal" if self.group_files_var.get() else "disabled")
            self.output_dir_entry.config(state="normal")
            self.browse_button.config(state="normal")
            self.suffix_entry.config(state="normal")
            self.output_ext_entry.config(state="normal")  # <-- NEW
            self.toggle_grouping_options()

    def toggle_grouping_options(self):
        if self.group_files_var.get():
            self.overwrite_var.set(False)
            self.overwrite_check.config(state="disabled")
            self.group_size_spinbox.config(state="normal")
        else:
            self.overwrite_check.config(state="normal")
            self.group_size_spinbox.config(state="disabled")
        self.validate_batch_sizes()

    def toggle_safety_widgets(self):
        state = "readonly" if self.enable_safety_var.get() else "disabled"
        for widget in self.safety_widgets:
            widget.config(state=state)

    def validate_batch_sizes(self, *args):
        if not self.group_files_var.get() or not self.files_var.get():
            self.group_status_label.config(text="")
            self.batch_size_warning.set(False)
            return
        try:
            group_size = self.group_size_var.get()
        except tk.TclError:
            return
        if group_size < 1:
            return
        try:
            file_sizes = [os.path.getsize(f) for f in self.files_var.get()]
        except FileNotFoundError:
            self.group_status_label.config(text="⚠️ Error: One or more files not found.", foreground="red")
            self.batch_size_warning.set(True)
            return
        limit_exceeded = any(sum(file_sizes[i:i + group_size]) > MAX_BATCH_SIZE_BYTES for i in range(0, len(file_sizes), group_size))
        if limit_exceeded:
            msg, fg, warn = f"⚠️ Warning: At least one batch exceeds {MAX_BATCH_SIZE_MB} MB!", "red", True
        else:
            msg, fg, warn = f"✓ All {len(file_sizes)//group_size + (1 if len(file_sizes)%group_size else 0)} batches are under {MAX_BATCH_SIZE_MB} MB.", "green", False
        self.group_status_label.config(text=msg, foreground=fg)
        self.batch_size_warning.set(warn)

    def prompt_for_api_key(self):
        new_key = get_api_key(force_gui=True)
        if new_key:
            self.api_key = new_key
            self.api_status_label.config(text="API Key Status: Set (via prompt)")
            self.update_models()
        else:
            self.api_status_label.config(text="API Key Status: NOT Set")

    def update_models(self, *args):
        engine = self.engine_var.get()
        self.model_combo.set('Fetching...')
        self.model_combo.configure(state="disabled")
        self.update_idletasks()
        if engine == "google":
            models, error_msg = fetch_google_models(self.api_key)
        elif engine == "ollama":
            models, error_msg = fetch_ollama_models()
        elif engine == "lmstudio":
            models, error_msg = fetch_lmstudio_models()
        else:
            models, error_msg = [], "Unknown engine selected"
        if error_msg:
            self.model_combo.set(f"Error: {error_msg}")
            self.model_var.set("")
        elif models:
            self.model_combo['values'] = models
            self.model_combo.configure(state="readonly")
            cmd_model = getattr(self.args, 'model', None)
            self.model_var.set(cmd_model if cmd_model in models else (models[0] if models else ""))
        else:
            self.model_combo.set("No models found")
            self.model_var.set("")

    def add_files(self):
        selected = filedialog.askopenfilenames(parent=self, title="Select Input Files", filetypes=[("Supported Files", " ".join(f"*{ext}" for ext in ALL_SUPPORTED_EXTENSIONS)), ("All Files", "*.*")])
        if selected:
            current = list(self.files_var.get())
            new_files = [os.path.normpath(f) for f in selected if os.path.normpath(f) not in current]
            if new_files:
                self.files_var.set(tuple(sorted(current + new_files, key=natural_sort_key)))
                self.validate_batch_sizes()

    def remove_files(self):
        selected = self.file_listbox.curselection()
        if selected:
            current = list(self.files_var.get())
            for i in sorted(selected, reverse=True):
                current.pop(i)
            self.files_var.set(tuple(current))
            self.validate_batch_sizes()

    def clear_files(self):
        self.files_var.set([])
        self.validate_batch_sizes()

    def browse_output_dir(self):
        directory = filedialog.askdirectory(initialdir=os.getcwd(), parent=self)
        if directory:
            self.output_dir_var.set(directory)

    def process(self):
        if self.batch_size_warning.get():
            if not tkinter.messagebox.askokcancel("Batch Size Warning", f"One or more batches exceeds the {MAX_BATCH_SIZE_MB} MB limit.\nThis may cause API errors.\nProceed anyway?", icon='warning', parent=self):
                return
        if self.overwrite_var.get():
            if not tkinter.messagebox.askokcancel("Overwrite Warning", "You have selected to overwrite the original input files with the AI output.\nThis action cannot be undone.\nAre you sure you want to proceed?", icon='warning', parent=self):
                return
        group_size = self.group_size_var.get() if self.group_files_var.get() else 1
        if self.group_files_var.get() and group_size < 2:
            tkinter.messagebox.showwarning("Input Error", "Files per call must be 2 or greater.", parent=self)
            return
        final_safety_settings = {}
        if self.engine_var.get() == 'google':
            if not self.enable_safety_var.get():
                final_safety_settings = {cat: HarmBlockThreshold.BLOCK_NONE for cat in HarmCategory if cat != HarmCategory.HARM_CATEGORY_UNSPECIFIED}
            else:
                final_safety_settings = {
                    HarmCategory.HARM_CATEGORY_HARASSMENT: self.safety_map[self.harassment_var.get()],
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: self.safety_map[self.hate_speech_var.get()],
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: self.safety_map[self.sexually_explicit_var.get()],
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: self.safety_map[self.dangerous_content_var.get()],
                }
        self.settings = {
            'files': list(self.files_var.get()),
            'custom_prompt': self.prompt_text.get("1.0", tk.END).strip(),
            'engine': self.engine_var.get(),
            'model': self.model_var.get(),
            'output_dir': self.output_dir_var.get(),
            'suffix': self.suffix_var.get(),
            'output_extension': self.output_ext_var.get().lstrip('.'),  # <-- NEW
            'stream_output': self.stream_var.get(),
            'api_key': self.api_key,
            'group_size': group_size,
            'safety_settings': final_safety_settings,
            'add_filename_to_prompt': self.add_filename_var.get(),
            'overwrite_original': self.overwrite_var.get()
        }
        if not self.settings['files']:
            tkinter.messagebox.showwarning("Input Error", "Please add at least one file.", parent=self)
            return
        if not self.settings['model'] or self.settings['model'].startswith("Error:"):
            tkinter.messagebox.showwarning("Input Error", "Please select a valid model.", parent=self)
            return
        if self.settings['engine'] == 'google' and not self.settings['api_key']:
            tkinter.messagebox.showwarning("Input Error", "Google engine requires an API Key.", parent=self)
            return
        self.destroy()

def main():
    parser = argparse.ArgumentParser(description="Multimodal AI Batch Processor")
    parser.add_argument("files", nargs="*", help="Path(s) to input file(s). Supports wildcards. If omitted, scans current directory.")
    parser.add_argument("-o", "--output", default=DEFAULT_OUTPUT_SUBFOLDER_NAME, help="Subfolder for output.")
    parser.add_argument("-s", "--suffix", default=DEFAULT_RAW_OUTPUT_SUFFIX, help="Suffix for output filenames.")
    parser.add_argument("--output-ext", default="", help="Override output file extension (e.g., md, srt, txt).")  # <-- NEW CLI
    parser.add_argument("--stream", action='store_true', help="Enable streaming output (Google Only).")
    parser.add_argument("-e", "--engine", default=DEFAULT_ENGINE, choices=['google', 'ollama', 'lmstudio'], help="AI engine.")
    parser.add_argument("-m", "--model", help="Suggest a model to select by default.")
    parser.add_argument("--add-filename-to-prompt", action='store_true', help="Append filename (no extension) to the prompt before the file content.")
    args = parser.parse_args()

    filepaths = []
    if args.files:
        print("Processing files specified on the command line...")
        for pattern in args.files:
            filepaths.extend(glob.glob(pattern, recursive=True))
    else:
        print("No input files specified. Searching current directory and all subdirectories for supported files...")
        current_directory = os.getcwd()
        for ext in ALL_SUPPORTED_EXTENSIONS:
            search_pattern = os.path.join(current_directory, f"**/*{ext}")
            filepaths.extend(glob.glob(search_pattern, recursive=True))
        if filepaths:
            print(f"Found {len(filepaths)} supported files to process.")
        else:
            print("No supported files found in the current directory.")
    filepaths = sorted(list(set(f for f in filepaths if os.path.isfile(f) and os.path.splitext(f)[1].lower() in ALL_SUPPORTED_EXTENSIONS)), key=natural_sort_key)

    initial_api_key = get_api_key()
    app = AppGUI(initial_api_key, filepaths, args)
    app.mainloop()

    gui_settings = app.settings
    if not gui_settings:
        print("Operation cancelled or GUI closed.")
        return

    all_files = sorted(list(set(gui_settings['files'])), key=natural_sort_key)
    if not all_files:
        print("Error: No valid input files specified.")
        return

    group_size = 1 if gui_settings.get('overwrite_original') else gui_settings.get('group_size', 1)
    if gui_settings.get('overwrite_original'):
        print("INFO: Overwrite mode enabled. Processing files individually.")
    file_groups = [all_files[i:i + group_size] for i in range(0, len(all_files), group_size)]
    total_groups = len(file_groups)
    central_out_folder = os.path.join(os.getcwd(), gui_settings['output_dir']) if gui_settings['output_dir'] and not gui_settings.get('overwrite_original') else None
    processed_files, quota_hits, failed_files = 0, 0, {}

    exhausted_models = set()
    print(f"\nStarting batch processing for {len(all_files)} file(s) in {total_groups} group(s)...")

    i = 0
    while i < total_groups:
        group_of_filepaths = file_groups[i]
        first_filepath = group_of_filepaths[0]
        print(f"\n--- Processing Group {i + 1}/{total_groups} ---")
        for fp in group_of_filepaths:
            print(f"  - {os.path.basename(fp)}")
        out_folder = central_out_folder or os.path.dirname(os.path.abspath(first_filepath))
        log_folder = os.path.join(out_folder, LOG_SUBFOLDER_NAME)
        os.makedirs(out_folder, exist_ok=True)
        os.makedirs(log_folder, exist_ok=True)

        try:
            _, error_msg = process_file_group(
                group_of_filepaths,
                gui_settings['api_key'],
                gui_settings['engine'],
                gui_settings['custom_prompt'],
                gui_settings['model'],
                output_suffix=gui_settings['suffix'],
                output_extension=gui_settings.get('output_extension', ''),  # <-- NEW
                stream_output=gui_settings['stream_output'],
                output_folder=out_folder,
                log_folder=log_folder,
                safety_settings=gui_settings['safety_settings'],
                add_filename_to_prompt=gui_settings['add_filename_to_prompt'],
                overwrite_original=gui_settings['overwrite_original']
            )
            if not error_msg:
                processed_files += len(group_of_filepaths)
                print(f"✓ SUCCESS: Group {i + 1}/{total_groups} processed successfully.")
            else:
                for fp in group_of_filepaths:
                    failed_files[fp] = error_msg
                [copy_failed_file(fp) for fp in group_of_filepaths]
                print(f"✗ FAILED: Group {i + 1}/{total_groups} failed. See log for details.")
            i += 1
        except QuotaExhaustedError:
            quota_hits += 1
            failed_model = gui_settings['model']
            exhausted_models.add(failed_model)
            print("\n" + "=" * 50)
            print(f"QUOTA LIMIT REACHED for model: {failed_model}")
            print("=" * 50)
            all_google_models, err = fetch_google_models(gui_settings['api_key'])
            if err or not all_google_models:
                print("Could not fetch alternative models. This group will be marked as failed.")
                reason = f"Quota limit reached for model {failed_model}; could not fetch alternatives"
                for fp in group_of_filepaths:
                    failed_files[fp] = reason
                [copy_failed_file(fp) for fp in group_of_filepaths]
                i += 1
                continue
            prompt_text = "Please choose an action:\n"
            for idx, model_name in enumerate(all_google_models):
                prompt_text += f"  [{idx + 1}] Switch to model: {model_name}{' (Quota Reached)' if model_name in exhausted_models else ''}\n"
            prompt_text += f"  [{len(all_google_models) + 1}] Quit the batch process\nYour choice: "
            while True:
                choice = input(prompt_text).strip()
                try:
                    choice_num = int(choice)
                    if 1 <= choice_num <= len(all_google_models):
                        gui_settings['model'] = all_google_models[choice_num - 1]
                        print(f"Switching to model: {gui_settings['model']}")
                        break
                    elif choice_num == len(all_google_models) + 1:
                        print("Quitting batch process. This group will be marked as failed.")
                        reason = f"Quota limit reached for model {failed_model}"
                        for fp in group_of_filepaths:
                            failed_files[fp] = reason
                        [copy_failed_file(fp) for fp in group_of_filepaths]
                        i = total_groups  # Exit outer loop
                        break
                    else:
                        print("Invalid number. Please try again.")
                except ValueError:
                    print("Invalid choice. Please enter a number from the list.")
        except KeyboardInterrupt:
            print("\n" + "=" * 50 + "\nCANCELLED: Batch processing was interrupted by the user.\n" + "=" * 50)
            reason = "Processing cancelled by user"
            for fp in group_of_filepaths:
                failed_files[fp] = reason
            [copy_failed_file(fp) for fp in group_of_filepaths]
            break

    failed_count = len(failed_files)
    attempted_count = processed_files + failed_count
    print("\n=========================================")
    print("          Batch Processing Summary")
    print("=========================================")
    print(f"Total files attempted: {attempted_count}{f' (in {total_groups} groups)' if group_size > 1 else ''}")
    print(f"Successfully processed: {processed_files}")
    if gui_settings.get('overwrite_original') and processed_files > 0:
        print("(Original input files were overwritten with AI output)")
    print(f"Failed (unrecoverable errors or cancelled): {failed_count}")
    print(f"Quota limits reached: {quota_hits} time(s)")
    if failed_files:
        print("\n--- List of Failed Files ---")
        for filepath, reason in failed_files.items():
            clean_reason = reason.replace('Error: ', '').strip()
            print(f"  - {os.path.basename(filepath)}: {clean_reason}")
        print("----------------------------")
        print("(Originals of failed files have been copied to a 'failed' subfolder)")
    print("=========================================")

if __name__ == "__main__":
    main()