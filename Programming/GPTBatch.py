# --- START OF FILE GPTBatcher_Multimodal_Logged_v12.py ---

"""
================================================================================
Multimodal AI Batch Processor (GPTBatcher) v12
================================================================================

Purpose:
--------
This script provides a powerful tool for batch-processing local files (both
text and images) using generative AI models. It features a graphical user
interface (GUI) for easy operation and supports both the Google Gemini API and
a local Ollama instance. For each file processed, it saves the raw AI response
and a detailed processing log.

Key Features:
-------------
- Dual AI Engine Support: Seamlessly switch between Google's cloud API and a
  local Ollama instance.
- Multimodal Input: Natively handles text files (.txt, .py, .md, etc.) and
  image files (.png, .jpg, .webp, etc.).
- User-Friendly GUI: An intuitive interface for adding files, editing the
  prompt, selecting models, and configuring outputs.
- Comprehensive Logging: Generates a detailed .log file for every operation,
  capturing settings, timings, status, and any errors.
- Interactive Quota Handling: If a Google API quota is hit, it pauses and
  prompts the user to switch to an alternative model or quit. The prompt now
  marks any models that have previously hit their quota during the session.
- Graceful Cancellation: Handles Ctrl+C (KeyboardInterrupt) to stop the batch
  cleanly without crashing and provides a final summary.
- Natural File Sorting: Correctly sorts file lists with numbers (e.g.,
  'file-2.txt' before 'file-10.txt').
- API Rate Limiting: Includes an automatic delay for the Google Gemini API to
  prevent exceeding request quotas.

Dependencies:
-------------
You must install the required Python libraries before running:
pip install google-generativeai requests

Setup:
------
1. Google API Key:
   - The script requires a Google API Key for the 'google' engine.
   - **Recommended:** Set it as an environment variable named "GOOGLE_API_KEY".
   - Alternatively, you can enter the key via the secure prompt in the GUI.

2. Ollama (Optional):
   - If you want to use local models, ensure Ollama is installed and running.
   - The script will attempt to connect to the default URL (http://localhost:11434).
   - You can change this URL in the "Customizable Variables" section below.

Usage:
------
1. Run from the command line: `python GPTBatcher_Multimodal_Logged_v12.py`
2. Command-line arguments can be used to pre-populate the GUI.
3. The GUI will launch for configuration. Click "Process" to begin.
4. If a quota limit is reached, follow the instructions in the console.

Output Structure:
-----------------
- By default, output files are saved next to the input files.
- A "processing_logs" subfolder will be created in the same location to store
  the detailed .log files.
- If an "Output Dir" is specified, all raw outputs will be saved there, and a
  "processing_logs" subfolder will be created inside it.

--------------------------------------------------------------------------------
"""

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
import re # For natural sorting

################################################################################
# --- Customizable Variables (Configuration) ---
################################################################################

# 1. Google API Key Environment Variable Name
API_KEY_ENV_VAR_NAME = "GOOGLE_API_KEY"

# 2. Ollama API Endpoint Configuration
OLLAMA_API_URL = os.environ.get("OLLAMA_API_URL", "http://localhost:11434")
OLLAMA_TAGS_ENDPOINT = f"{OLLAMA_API_URL}/api/tags"
OLLAMA_GENERATE_ENDPOINT = f"{OLLAMA_API_URL}/api/generate"

# 3. Default User Prompt Template
USER_PROMPT_TEMPLATE = """Analyze the provided content (text or image).

If text is provided below: Summarize the key points, identify main topics, and suggest relevant keywords.
If an image is provided: Describe the image in detail, including objects, scene, actions, and overall mood. Suggest relevant keywords or tags for the image.

Provide the output as plain text.
"""

# 4. Supported File Types
SUPPORTED_TEXT_EXTENSIONS = ['.txt', '.srt', '.md', '.py', '.js', '.html', '.css']
SUPPORTED_IMAGE_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.webp', '.heic', '.heif']
ALL_SUPPORTED_EXTENSIONS = SUPPORTED_TEXT_EXTENSIONS + SUPPORTED_IMAGE_EXTENSIONS

# 5. Output File Naming
DEFAULT_RAW_OUTPUT_SUFFIX = ""
RAW_OUTPUT_FILE_EXTENSION = ".txt"
LOG_FILE_EXTENSION = ".log"

# 6. Default AI Engine
DEFAULT_ENGINE = "google"

# 7. Rate Limiting Configuration (for Google Gemini API)
REQUESTS_PER_MINUTE = 15
REQUEST_INTERVAL_SECONDS = 60 / REQUESTS_PER_MINUTE

# 8. Output Subfolder Names
DEFAULT_OUTPUT_SUBFOLDER_NAME = ""
LOG_SUBFOLDER_NAME = "processing_logs"

################################################################################
# --- End of Customizable Variables ---
################################################################################

# --- Custom Exception for Fatal Errors ---
class QuotaExhaustedError(Exception):
    """Custom exception raised when Google API quota is exhausted."""
    pass

# Global variable for rate limiting
last_request_time = None

# --- Helper Functions ---
def natural_sort_key(s):
    """Creates a key for natural sorting (e.g., '2' before '10')."""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]

# --- Model Fetching Functions ---
def fetch_google_models(api_key):
    """Fetches available 'generateContent' models from Google Generative AI."""
    if not api_key: return [], "API key not available."
    try:
        print("Fetching Google AI models...")
        genai.configure(api_key=api_key)
        models = [m.name for m in genai.list_models() if "generateContent" in m.supported_generation_methods]
        models.sort(key=lambda x: (not ('pro' in x or 'flash' in x), x))
        print(f"Found and sorted Google models: {models}")
        return models, None
    except PermissionDenied: return [], "Google API Permission Denied. Check API key permissions."
    except GoogleAPIError as e: return [], f"Google API Error: {e}"
    except Exception as e: return [], f"An unexpected error occurred: {e}"

def fetch_ollama_models():
    """Fetches available models from the Ollama API."""
    try:
        print(f"Fetching Ollama models from {OLLAMA_TAGS_ENDPOINT}...")
        response = requests.get(OLLAMA_TAGS_ENDPOINT, timeout=10)
        response.raise_for_status()
        models = sorted([m.get("name") for m in response.json().get("models", []) if m.get("name")])
        print(f"Found Ollama models: {models}")
        return models, None
    except requests.exceptions.ConnectionError: return [], f"Connection Error: Is Ollama running at {OLLAMA_API_URL}?"
    except requests.exceptions.RequestException as e: return [], f"Ollama Request Error: {e}"
    except Exception as e: return [], f"An unexpected error occurred: {e}"

def read_file_content(filepath):
    """Reads file content, returning content, mime type, and is_image flag."""
    _, extension = os.path.splitext(filepath)
    ext = extension.lower()
    try:
        if ext in SUPPORTED_TEXT_EXTENSIONS:
            with open(filepath, 'r', encoding='utf-8') as f: return f.read(), 'text/plain', False, None
        elif ext in SUPPORTED_IMAGE_EXTENSIONS:
            mime_type, _ = mimetypes.guess_type(filepath)
            with open(filepath, 'rb') as f: return f.read(), mime_type or 'application/octet-stream', True, None
        else: return None, None, False, f"Unsupported file extension '{ext}'"
    except Exception as e: return None, None, False, f"Error reading file {filepath}: {e}"

# --- API Call Functions ---
def call_generative_ai_api(engine, prompt_text, api_key, model_name, **kwargs):
    if engine == "google": return call_google_gemini_api(prompt_text, api_key, model_name, **kwargs)
    elif engine == "ollama": return call_ollama_api(prompt_text, model_name, **kwargs)
    else: return f"Error: Unknown engine '{engine}'"

def call_google_gemini_api(prompt_text, api_key, model_name, image_bytes=None, mime_type=None, stream_output=False):
    global last_request_time
    if not api_key: return "Error: Google API Key not configured."
    if not model_name: return "Error: No Google model selected."
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        if last_request_time and (time.time() - last_request_time < REQUEST_INTERVAL_SECONDS):
            sleep_duration = REQUEST_INTERVAL_SECONDS - (time.time() - last_request_time)
            print(f"Rate limit active. Sleeping for {sleep_duration:.2f} seconds...")
            time.sleep(sleep_duration)
        last_request_time = time.time()
        payload = [prompt_text]
        if image_bytes: payload.append({"inline_data": {"mime_type": mime_type, "data": image_bytes}})
        print(f"Sending request to Google Gemini (Model: {model_name})")
        response = model.generate_content(payload, stream=stream_output)
        if stream_output: return "".join(chunk.text for chunk in response).strip()
        else:
            if hasattr(response, 'text'): return response.text.strip()
            if response.prompt_feedback and response.prompt_feedback.block_reason:
                return f"Error: Prompt blocked by safety filter ({response.prompt_feedback.block_reason})."
            return "Error: No content generated (Reason unknown)."
    except ResourceExhausted:
        print(f"FATAL ERROR: Google Gemini API Quota Exhausted for model {model_name}.", file=sys.stderr)
        raise QuotaExhaustedError(f"Quota exhausted for model {model_name}")
    except PermissionDenied: return "Error: Google API Permission Denied (Check Key)."
    except GoogleAPIError as e: return f"Error: Google API Call Failed - {e}"
    except Exception as e: traceback.print_exc(); return f"Error: Unexpected Google API issue - {e}"

def call_ollama_api(prompt_text, model_name, image_bytes=None, **kwargs):
    payload = {"model": model_name, "prompt": prompt_text, "stream": False}
    if image_bytes: payload["images"] = [base64.b64encode(image_bytes).decode('utf-8')]
    try:
        print(f"Calling Ollama API ({model_name}) at {OLLAMA_GENERATE_ENDPOINT}")
        response = requests.post(OLLAMA_GENERATE_ENDPOINT, json=payload, timeout=600)
        response.raise_for_status()
        data = response.json()
        if "response" in data: return data["response"].strip()
        if "error" in data: return f"Error: Ollama API returned an error - {data['error']}"
        return "Error: Unexpected response format from Ollama."
    except requests.exceptions.RequestException as e: return f"Error: Could not connect to Ollama API - {e}"
    except Exception as e: traceback.print_exc(); return f"Error: Unexpected Ollama Call Failed - {e}"

# --- Output & Logging Functions ---
def determine_unique_output_paths(input_filepath, suffix, out_folder, log_folder):
    base_name = os.path.splitext(os.path.basename(input_filepath))[0]
    out_base = f"{base_name}{suffix}"
    def find_unique(folder, base, ext):
        path = os.path.join(folder, f"{base}{ext}")
        if not os.path.exists(path): return path
        i = 1
        while True:
            path = os.path.join(folder, f"{base} ({i}){ext}")
            if not os.path.exists(path): return path
            i += 1
    return find_unique(out_folder, out_base, RAW_OUTPUT_FILE_EXTENSION), find_unique(log_folder, out_base, LOG_FILE_EXTENSION)

def save_raw_api_response(text, filepath):
    try:
        with open(filepath, 'w', encoding='utf-8') as f: f.write(text or "[Info: API response was empty]")
    except Exception as e: print(f"**ERROR: Could not save raw API response to {filepath}: {e}**")

def save_processing_log(log_data, log_filepath):
    try:
        with open(log_filepath, 'w', encoding='utf-8') as f:
            f.write("="*20 + " Processing Log " + "="*20 + "\n")
            for k, v in log_data.items():
                if isinstance(v, datetime.datetime): v = v.strftime("%Y-%m-%d %H:%M:%S")
                elif isinstance(v, float): v = f"{v:.2f} seconds"
                f.write(f"{k.replace('_', ' ').title()}: {v}\n")
            f.write("="*56 + "\n")
        print(f"Processing log saved to: {log_filepath}")
    except Exception as e: print(f"**ERROR: Could not save processing log to {log_filepath}: {e}**")

# --- Core Processing ---
def process_single_file(input_filepath, api_key, engine, user_prompt, model_name, **kwargs):
    start_time = datetime.datetime.now()
    raw_path, log_path = determine_unique_output_paths(input_filepath, kwargs['output_suffix'], kwargs['output_folder'], kwargs['log_folder'])
    log_data = {'input_filepath': input_filepath, 'start_time': start_time, 'engine': engine, 'model_name': model_name, 'status': 'Failure'}
    api_response = None
    try:
        print(f"--- Reading file: {input_filepath} ---")
        content, mime, is_image, err = read_file_content(input_filepath)
        if err: raise ValueError(err)
        prompt = user_prompt if is_image else f"{user_prompt}\n\n--- File Content Start ---\n{content}\n--- File Content End ---"
        log_data['prompt_sent'] = prompt
        api_response = call_generative_ai_api(engine, prompt, api_key, model_name, image_bytes=content if is_image else None, mime_type=mime, stream_output=kwargs['stream_output'])
        if api_response and api_response.startswith("Error:"): raise Exception(api_response)
        log_data['status'] = 'Success'
        return api_response, None
    except Exception as e:
        print(f"**ERROR during processing {input_filepath}: {e}**")
        log_data.update({'error_message': str(e), 'traceback_info': traceback.format_exc() if not isinstance(e, (QuotaExhaustedError, KeyboardInterrupt)) else "N/A"})
        if isinstance(e, (QuotaExhaustedError, KeyboardInterrupt)): raise
        return None, str(e)
    finally:
        save_raw_api_response(api_response or f"[ERROR] {log_data.get('error_message')}", raw_path)
        log_data.update({'end_time': datetime.datetime.now(), 'duration': (datetime.datetime.now() - start_time).total_seconds()})
        save_processing_log(log_data, log_path)

# --- API Key Handling ---
def get_api_key(force_gui=False):
    api_key = os.environ.get(API_KEY_ENV_VAR_NAME)
    if not api_key or force_gui:
        if not force_gui: print(f"INFO: {API_KEY_ENV_VAR_NAME} environment variable not set.")
        root = tk.Tk(); root.withdraw()
        try: api_key = tk.simpledialog.askstring("API Key Required", "Please enter your Google API Key:", show='*')
        finally: root.destroy()
        if api_key: print("INFO: API Key obtained via GUI prompt.")
        else: print("ERROR: Google API Key not provided."); return None
    return api_key

# --- GUI Implementation ---
class AppGUI(tk.Tk): # (GUI class remains the same)
    def __init__(self, initial_api_key, command_line_files, args):
        super().__init__()
        self.title("Multimodal AI Batch Processor")
        self.settings = None
        self.api_key = initial_api_key
        self.args = args or argparse.Namespace()
        self.files_var = tk.Variable(value=list(command_line_files or []))
        self.engine_var = tk.StringVar(value=getattr(self.args, 'engine', DEFAULT_ENGINE))
        self.model_var = tk.StringVar()
        self.output_dir_var = tk.StringVar(value=getattr(self.args, 'output', DEFAULT_OUTPUT_SUBFOLDER_NAME))
        self.suffix_var = tk.StringVar(value=getattr(self.args, 'suffix', DEFAULT_RAW_OUTPUT_SUFFIX))
        self.stream_var = tk.BooleanVar(value=getattr(self.args, 'stream', False))
        self.create_widgets()
        self.engine_var.trace_add("write", self.update_models)
        self.after(150, self.update_models)
    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="10"); main_frame.pack(fill=tk.BOTH, expand=True)
        api_frame = ttk.Frame(main_frame, padding="5"); api_frame.pack(fill=tk.X)
        self.api_status_label = ttk.Label(api_frame, text=f"API Key Status: {'Set' if self.api_key else 'Not Set'}"); self.api_status_label.pack(side=tk.LEFT, padx=5)
        ttk.Button(api_frame, text="Enter/Update Google API Key", command=self.prompt_for_api_key).pack(side=tk.LEFT)
        files_frame = ttk.LabelFrame(main_frame, text="Input Files", padding="10"); files_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.file_listbox = tk.Listbox(files_frame, listvariable=self.files_var, selectmode=tk.EXTENDED, height=8); self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        files_scrollbar = ttk.Scrollbar(files_frame, orient=tk.VERTICAL, command=self.file_listbox.yview); files_scrollbar.pack(side=tk.LEFT, fill=tk.Y); self.file_listbox.config(yscrollcommand=files_scrollbar.set)
        btn_frame = ttk.Frame(files_frame); btn_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5)
        ttk.Button(btn_frame, text="Add Files...", command=self.add_files).pack(fill=tk.X)
        ttk.Button(btn_frame, text="Remove Sel.", command=self.remove_files).pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="Clear All", command=lambda: self.files_var.set([])).pack(fill=tk.X)
        prompt_frame = ttk.LabelFrame(main_frame, text="User Prompt", padding="10"); prompt_frame.pack(fill=tk.X, pady=5)
        self.prompt_text = scrolledtext.ScrolledText(prompt_frame, wrap=tk.WORD, height=8); self.prompt_text.pack(fill=tk.X); self.prompt_text.insert(tk.INSERT, USER_PROMPT_TEMPLATE)
        options_frame = ttk.Frame(main_frame); options_frame.pack(fill=tk.X, pady=5)
        ttk.Label(options_frame, text="AI Engine:").grid(row=0, column=0, sticky=tk.W); ttk.Combobox(options_frame, textvariable=self.engine_var, values=['google', 'ollama'], state="readonly").grid(row=0, column=1, sticky=tk.EW)
        ttk.Label(options_frame, text="Model:").grid(row=1, column=0, sticky=tk.W); self.model_combo = ttk.Combobox(options_frame, textvariable=self.model_var, state="disabled"); self.model_combo.grid(row=1, column=1, sticky=tk.EW); options_frame.columnconfigure(1, weight=1)
        settings_frame = ttk.LabelFrame(main_frame, text="Output Settings", padding="10"); settings_frame.pack(fill=tk.X, pady=5)
        ttk.Label(settings_frame, text="Output Dir:").grid(row=0, column=0, sticky=tk.W); ttk.Entry(settings_frame, textvariable=self.output_dir_var).grid(row=0, column=1, sticky=tk.EW); ttk.Button(settings_frame, text="Browse...", command=self.browse_output_dir).grid(row=0, column=2)
        ttk.Label(settings_frame, text="Output Suffix:").grid(row=1, column=0, sticky=tk.W); ttk.Entry(settings_frame, textvariable=self.suffix_var).grid(row=1, column=1, sticky=tk.W)
        ttk.Checkbutton(settings_frame, text="Stream Output (Google Only)", variable=self.stream_var).grid(row=2, column=1, sticky=tk.W); settings_frame.columnconfigure(1, weight=1)
        ttk.Button(main_frame, text="Process Selected Files", command=self.process).pack(pady=10)
    def prompt_for_api_key(self):
        new_key = get_api_key(force_gui=True)
        if new_key: self.api_key = new_key; self.api_status_label.config(text="API Key Status: Set (via prompt)"); self.update_models()
        else: self.api_status_label.config(text="API Key Status: NOT Set")
    def update_models(self, *args):
        engine = self.engine_var.get(); self.model_combo.set('Fetching...'); self.model_combo.configure(state="disabled"); self.update_idletasks()
        models, error_msg = fetch_google_models(self.api_key) if engine == "google" else fetch_ollama_models()
        if error_msg: self.model_combo.set(f"Error: {error_msg}"); self.model_var.set("")
        elif models:
            self.model_combo['values'] = models; self.model_combo.configure(state="readonly")
            cmd_model = getattr(self.args, 'model', None)
            self.model_var.set(cmd_model if cmd_model in models else (models[0] if models else ""))
        else: self.model_combo.set("No models found"); self.model_var.set("")
    def add_files(self):
        selected = filedialog.askopenfilenames(parent=self, title="Select Input Files", filetypes=[("Supported Files", " ".join(f"*{ext}" for ext in ALL_SUPPORTED_EXTENSIONS)), ("All Files", "*.*")])
        if selected:
            current = list(self.files_var.get()); new_files = [os.path.normpath(f) for f in selected if os.path.normpath(f) not in current]
            if new_files: self.files_var.set(tuple(sorted(current + new_files, key=natural_sort_key)))
    def remove_files(self):
        selected = self.file_listbox.curselection()
        if selected:
            current = list(self.files_var.get())
            for i in sorted(selected, reverse=True): current.pop(i)
            self.files_var.set(tuple(current))
    def browse_output_dir(self):
        directory = filedialog.askdirectory(initialdir=os.getcwd(), parent=self)
        if directory: self.output_dir_var.set(directory)
    def process(self):
        self.settings = {
            'files': list(self.files_var.get()), 'custom_prompt': self.prompt_text.get("1.0", tk.END).strip(),
            'engine': self.engine_var.get(), 'model': self.model_var.get(), 'output_dir': self.output_dir_var.get(),
            'suffix': self.suffix_var.get(), 'stream_output': self.stream_var.get(), 'api_key': self.api_key
        }
        if not self.settings['files']: tkinter.messagebox.showwarning("Input Error", "Please add at least one file.", parent=self); return
        if not self.settings['model'] or self.settings['model'].startswith("Error:"): tkinter.messagebox.showwarning("Input Error", "Please select a valid model.", parent=self); return
        if self.settings['engine'] == 'google' and not self.settings['api_key']: tkinter.messagebox.showwarning("Input Error", "Google engine requires an API Key.", parent=self); return
        self.destroy()

# --- Main Execution ---
def main():
    parser = argparse.ArgumentParser(description="Multimodal AI Batch Processor")
    parser.add_argument("files", nargs="*", help="Path(s) to input file(s). Supports wildcards.")
    parser.add_argument("-o", "--output", default=DEFAULT_OUTPUT_SUBFOLDER_NAME, help="Subfolder for output.")
    parser.add_argument("-s", "--suffix", default=DEFAULT_RAW_OUTPUT_SUFFIX, help="Suffix for output filenames.")
    parser.add_argument("--stream", action='store_true', help="Enable streaming output (Google Only).")
    parser.add_argument("-e", "--engine", default=DEFAULT_ENGINE, choices=['google', 'ollama'], help="AI engine.")
    parser.add_argument("-m", "--model", help="Suggest a model to select by default.")
    args = parser.parse_args()

    filepaths = []
    if args.files:
        for pattern in args.files: filepaths.extend(glob.glob(pattern, recursive=True))
    filepaths = sorted(list(set(f for f in filepaths if os.path.isfile(f) and os.path.splitext(f)[1].lower() in ALL_SUPPORTED_EXTENSIONS)), key=natural_sort_key)

    initial_api_key = get_api_key()
    app = AppGUI(initial_api_key, filepaths, args); app.mainloop()
    gui_settings = app.settings
    if not gui_settings: print("Operation cancelled or GUI closed."); return

    all_files = sorted(list(set(gui_settings['files'])), key=natural_sort_key)
    if not all_files: print("Error: No valid input files specified."); return

    central_out_folder = os.path.join(os.getcwd(), gui_settings['output_dir']) if gui_settings['output_dir'] else None
    processed_files, failed_files = 0, 0
    total_files = len(all_files)
    exhausted_models = set() # *** CHANGE 1: Initialize the tracker ***
    print(f"\nStarting batch processing for {total_files} file(s)...")

    i = 0
    while i < total_files:
        filepath = all_files[i]
        print(f"\n--- Processing file {i + 1}/{total_files} ({os.path.basename(filepath)}) ---")
        out_folder = central_out_folder or os.path.dirname(os.path.abspath(filepath))
        log_folder = os.path.join(out_folder, LOG_SUBFOLDER_NAME)
        os.makedirs(log_folder, exist_ok=True)

        try:
            _, error_msg = process_single_file(filepath, gui_settings['api_key'], gui_settings['engine'],
                gui_settings['custom_prompt'], gui_settings['model'], output_suffix=gui_settings['suffix'],
                stream_output=gui_settings['stream_output'], output_folder=out_folder, log_folder=log_folder)
            if not error_msg: processed_files += 1
            else: failed_files += 1
            i += 1 # Move to next file on success or normal failure

        except QuotaExhaustedError:
            failed_model = gui_settings['model']
            exhausted_models.add(failed_model) # *** CHANGE 2: Update the tracker ***
            print("\n" + "="*50); print(f"QUOTA LIMIT REACHED for model: {failed_model}"); print("="*50)
            
            all_google_models, err = fetch_google_models(gui_settings['api_key'])
            if err or not all_google_models:
                print("Could not fetch alternative models. Halting batch.")
                failed_files += 1; break

            # *** CHANGE 3: Rework the prompt generation to mark exhausted models ***
            prompt = "Please choose an action:\n"
            # Use the full list of models to build the selection menu
            for idx, model_name in enumerate(all_google_models):
                marker = " (Quota Reached)" if model_name in exhausted_models else ""
                prompt += f"  [{idx + 1}] Switch to model: {model_name}{marker}\n"
            prompt += f"  [{len(all_google_models) + 1}] Quit the batch process\nYour choice: "
            
            while True:
                choice = input(prompt).strip()
                try:
                    choice_num = int(choice)
                    if 1 <= choice_num <= len(all_google_models):
                        new_model = all_google_models[choice_num - 1]
                        print(f"Switching to model: {new_model}"); gui_settings['model'] = new_model
                        break # This will retry the same file (since 'i' is not incremented)
                    elif choice_num == len(all_google_models) + 1:
                        print("Quitting batch process.")
                        failed_files += 1; i = total_files; break # Set i to exit the main while loop
                    else:
                        print("Invalid number. Please try again.")
                except ValueError:
                    print("Invalid choice. Please enter a number from the list.")

        except KeyboardInterrupt:
            print("\n" + "="*50); print("CANCELLED: Batch processing was interrupted by the user."); print("="*50)
            failed_files += 1; break

    print("\n=========================================")
    print("          Batch Processing Summary")
    print("=========================================")
    print(f"Total files attempted: {processed_files + failed_files}")
    print(f"Successfully processed: {processed_files}")
    print(f"Failed: {failed_files}")
    print("=========================================")

if __name__ == "__main__":
    main()

# --- END OF FILE GPTBatcher_Multimodal_Logged_v12.py ---