
"""
# 🚀 Multimodal AI Batch Processor (GPTBatcher) v25.7

A powerful, GUI-driven batch processing tool for Multimodal Large Language Models. Streamline your workflow by processing hundreds of files (images, text, code) through **Google Gemini**, **Ollama**, or **LM Studio** simultaneously.

---

## ✨ Key Features

- **🌐 Multi-Engine Support**: Native integration with Google Gemini (via Files API), Ollama, and LM Studio.
- **🖼️ Multimodal Power**: Batch upload images and documents for analysis, OCR, or creative tasks.
- **📦 Intelligent Grouping**: Process files individually or group them (e.g., 3 images per prompt) to save tokens and context.
- **🔄 Upload Modes**: 
  - **Parallel**: High-speed multi-threaded uploads (internal ordering preserved).
  - **Sequential**: Strict one-by-one uploading for reliable logging and order.
- **🎯 Precision Control**: 
  - **JSON Validation**: Enforce valid JSON output with optional schema checks.
  - **Markdown Cleanup**: Automatically strip ```json wrappers for clean raw data.
  - **Prompt Templates**: Save and switch between custom processing presets.
- **🌊 Real-time Feedback**: Live console streaming and detailed processing logs.
- **🛡️ Safety & Reliability**: Integrated safety filters, custom job delays, and automatic retries for failed jobs.

---

## 🛠️ Configuration & Setup

1. **Google API Key**: Set your `GOOGLE_API_KEY` environment variable or enter it directly via the GUI.
2. **Local Engines**: Ensure Ollama or LM Studio are running locally (defaults to standard ports).
3. **Output Structure**:
   - `processing_logs/`: Detailed metadata, prompts, and timestamps for every job.
   - `failed/`: Automatic backups of files that failed to process.

---

## 📜 Recent Changelog

### v25.7
- ✅ **FEATURE**: Added "Upload Mode" (Parallel/Sequential) radio buttons.
- ✅ **IMPROVEMENT**: Human-readable error messages for Google Finish Reasons (e.g., "Max Tokens", "Safety").
- ✅ **BUGFIX**: Fixed status stuck on "Waiting for User" after quota recovery.
- ✅ **IMPROVEMENT**: Enhanced documentation header with GitHub-style formatting.

### v25.6
- ✅ **FEATURE**: Added "Enforce Schema" sub-option for JSON validation (title, description, hashtags, tags).

---

## ⚖️ License & Credits
Developed by Feureau. Designed for efficiency, reliability, and precision in AI-assisted workflows.

> [!IMPORTANT]
> This documentation block is a core part of the script and **must** be updated with every feature addition, bug fix, or logic change.
"""


################################################################################
# --- Configuration & Imports ---
################################################################################
import os
# --- SUPPRESS GOOGLE/GRPC LOGGING NOISE ---
os.environ['GRPC_VERBOSITY'] = 'ERROR'
os.environ['GLOG_minloglevel'] = '2'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

import sys
import json
import requests
import glob
import time
import datetime
import hashlib 
import threading
import queue
import signal
import base64
import mimetypes
import traceback
import re
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed


from google import genai
from google.genai import types
from google.api_core.exceptions import GoogleAPIError, ResourceExhausted, PermissionDenied

import argparse
import tkinter as tk
from tkinter import ttk
from tkinter import scrolledtext
from tkinter import filedialog
import tkinter.messagebox
import tkinter.simpledialog

import ollama 

# --- OPTIONAL: JSON REPAIR ---
try:
    import json_repair
except ImportError:
    json_repair = None

# --- GLOBAL CACHE FOR UPLOADED FILES (Deduplication) ---
# Stores { "sha256_hash": types.File }
UPLOADED_FILE_CACHE = {}
UPLOAD_LOCK = threading.Lock()

API_KEY_ENV_VAR_NAME = "GOOGLE_API_KEY"
DEFAULT_GOOGLE_MODEL = "models/gemini-1.5-flash"

OLLAMA_API_URL = os.environ.get("OLLAMA_API_URL", "http://localhost:11434")
OLLAMA_TAGS_ENDPOINT = f"{OLLAMA_API_URL}/api/tags"

LMSTUDIO_API_URL = os.environ.get("LMSTUDIO_API_URL", "http://localhost:1234/v1")
LMSTUDIO_MODELS_ENDPOINT = f"{LMSTUDIO_API_URL}/models"
LMSTUDIO_CHAT_COMPLETIONS_ENDPOINT = f"{LMSTUDIO_API_URL}/chat/completions"

USER_PROMPT_TEMPLATE = """Analyze the provided content."""

# --- AUTO-LOAD SETTINGS ---
AUTO_LOAD_EXTENSIONS = [
    # Text / Code / Data
    '.txt', '.md', '.srt', '.vtt', '.py', '.js', '.html', '.css', '.json', '.csv', 
    '.xml', '.yaml', '.yml', '.ini', '.log', '.bat', '.sh', '.r', '.c', '.cpp', '.h', 
    '.java', '.php', '.sql', '.rb', '.go', '.rs', '.swift', '.kt', '.ts', '.tsx', '.jsx',
    # Images
    '.png', '.jpg', '.jpeg', '.webp', '.heic', '.heif', '.bmp', '.tiff'
]

SUPPORTED_IMAGE_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.webp', '.heic', '.heif', '.bmp', '.tiff']

DEFAULT_RAW_OUTPUT_SUFFIX = ""
RAW_OUTPUT_FILE_EXTENSION = ".txt"
LOG_FILE_EXTENSION = ".log"
DEFAULT_ENGINE = "google"
REQUESTS_PER_MINUTE = 15
REQUEST_INTERVAL_SECONDS = 60 / REQUESTS_PER_MINUTE

PRESET_JSON_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "GPTBatch.py.preset.json")
DEFAULT_OUTPUT_SUBFOLDER_NAME = ""
LOG_SUBFOLDER_NAME = "processing_logs"
FAILED_SUBFOLDER_NAME = "failed"
MAX_BATCH_SIZE_MB = 15
MAX_RETRIES = 3

def sanitize_filename(name):
    # Strip illegal chars and typical markdown noise
    keep = (" ", ".", "_", "-")
    clean = "".join(c for c in name if c.isalnum() or c in keep).strip()
    return clean[:250] # Truncate to safe length



################################################################################
# --- Core Logic & Helpers ---
################################################################################

class QuotaExhaustedError(Exception): pass
class FatalProcessingError(Exception): pass
last_request_time = None

def console_log(msg, type="INFO"):
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    icon = "ℹ️"
    if type == "ERROR": icon = "❌"
    elif type == "SUCCESS": icon = "✅"
    elif type == "WARN": icon = "⚠️"
    elif type == "ACTION": icon = "👉"
    elif type == "UPLOAD": icon = "☁️"
    elif type == "STREAM": icon = "🌊"
    print(f"[{timestamp}] {icon} {msg}")

def load_presets():
    """Loads presets from PRESET_JSON_FILE."""
    if not os.path.exists(PRESET_JSON_FILE):
        console_log(f"Preset file not found: {PRESET_JSON_FILE}", "WARN")
        return {}
    try:
        with open(PRESET_JSON_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        console_log(f"Error loading presets from JSON: {e}", "ERROR")
        return {"Error - Backup": {"prompt": "Data Corrupt", "engine": "google", "model": "", "output_suffix": ""}}

def save_presets(new_presets_dict):
    """Saves presets to PRESET_JSON_FILE."""
    try:
        with open(PRESET_JSON_FILE, 'w', encoding='utf-8') as f:
            json.dump(new_presets_dict, f, indent=4)
        console_log(f"Presets saved to {PRESET_JSON_FILE}.", "SUCCESS")
    except Exception as e:
        console_log(f"Failed to save presets to JSON: {e}", "ERROR")

def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]

def generate_group_base_name(filepaths_group):
    if not filepaths_group: return "empty_group"
    base_names = [os.path.splitext(os.path.basename(fp)) for fp in filepaths_group]
    if len(base_names) == 1: return base_names[0][0]
    else: return f"{base_names[0][0]}_to_{base_names[-1][0]}"

# --- FILE HASHING FOR DEDUPLICATION ---
def hash_file(path, chunk_size=1024 * 1024):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()

# --- GEMINI FILES API UPLOADER (Cached & Robust) ---
def upload_image_file(path, client, retries=3):
    try:
        file_hash = hash_file(path)
        with UPLOAD_LOCK:
            if file_hash in UPLOADED_FILE_CACHE:
                return UPLOADED_FILE_CACHE[file_hash], True
    except Exception as e:
        console_log(f"[HASH FAILED] {path}: {e}", "ERROR")
        return None, False

    last_error = None
    for attempt in range(1, retries + 2):
        try:
            mime_type = mimetypes.guess_type(path)[0] or "image/png"
            uploaded_file = client.files.upload(file=path, config={'mime_type': mime_type})
            
            while uploaded_file.state == "PROCESSING":
                time.sleep(1)
                uploaded_file = client.files.get(name=uploaded_file.name)
                
            if uploaded_file.state == "FAILED":
                raise ValueError("Google says file processing failed.")

            with UPLOAD_LOCK:
                UPLOADED_FILE_CACHE[file_hash] = uploaded_file
                
            console_log(f"Uploaded: {os.path.basename(path)}", "UPLOAD")
            return uploaded_file, False 

        except Exception as e:
            last_error = e
            if attempt <= retries:
                wait_time = 2 * attempt 
                console_log(f"Retry {attempt}/{retries} for {os.path.basename(path)}: {e}", "WARN")
                time.sleep(wait_time)
            else:
                pass

    console_log(f"❌ [UPLOAD FAILED] {path}: {last_error}", "ERROR")
    return None, False

def upload_images_parallel(image_paths, client, max_workers=4, sequential=False):
    uploaded_files = [None] * len(image_paths)
    if not image_paths: return []
        
    console_log(f"Preparing {len(image_paths)} images...", "INFO")
    cached_count = 0
    new_upload_count = 0

    if sequential:
        files_list = []
        for i, p in enumerate(image_paths):
             file_obj, was_cached = upload_image_file(p, client)
             if file_obj:
                 files_list.append(file_obj)
                 if was_cached: cached_count += 1
                 else: new_upload_count += 1
        uploaded_files = files_list
    else:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_index = {executor.submit(upload_image_file, p, client): i for i, p in enumerate(image_paths)}
            for future in as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    file_obj, was_cached = future.result()
                    if file_obj:
                        uploaded_files[index] = file_obj
                        if was_cached: cached_count += 1
                        else: new_upload_count += 1
                except Exception as e:
                    console_log(f"Error uploading image at index {index}: {e}", "ERROR")
        
        # Filter out Nones (failed uploads)
        uploaded_files = [f for f in uploaded_files if f is not None]
    
    msg = f"Ready: {len(uploaded_files)} images."
    details = []
    if new_upload_count > 0: details.append(f"{new_upload_count} uploaded")
    if cached_count > 0: details.append(f"{cached_count} from cache")
    if details: console_log(f"{msg} ({', '.join(details)})", "SUCCESS")
    elif len(uploaded_files) > 0: console_log(msg, "SUCCESS")
    return uploaded_files

def fetch_google_models(api_key):
    if not api_key: return [], "API key not available."
    try:
        console_log("Fetching Google models...", "INFO")
        client = genai.Client(api_key=api_key)
        # client.models.list() returns internal model objects, we need the name
        models = [m.name for m in client.models.list()]
        # Filter for models that likely support generation (not strictly necessary but good)
        models = [m for m in models if "gemini" in m]
        models.sort(key=lambda x: (0 if 'latest' in x else 1 if '2.5' in x else 2 if '2.0' in x else 3, 0 if 'pro' in x else 1 if 'flash' in x else 2, x))
        return models, None
    except Exception as e: return [], str(e)

def fetch_ollama_models():
    try:
        console_log("Fetching Ollama models...", "INFO")
        response = requests.get(OLLAMA_TAGS_ENDPOINT, timeout=5)
        response.raise_for_status()
        models = sorted([m.get("name") for m in response.json().get("models", []) if m.get("name")])
        return models, None
    except Exception as e: return [], str(e)

def fetch_lmstudio_models():
    try:
        console_log("Fetching LM Studio models...", "INFO")
        response = requests.get(LMSTUDIO_MODELS_ENDPOINT, timeout=5)
        response.raise_for_status()
        models = sorted([m.get("id") for m in response.json().get("data", []) if m.get("id")])
        return models, None
    except Exception as e: return [], str(e)

def read_file_content(filepath):
    _, extension = os.path.splitext(filepath)
    ext = extension.lower()
    try:
        if ext in SUPPORTED_IMAGE_EXTENSIONS:
            mime_type, _ = mimetypes.guess_type(filepath)
            with open(filepath, 'rb') as f:
                return f.read(), mime_type or 'application/octet-stream', True, None
        else:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    return f.read(), 'text/plain', False, None
            except UnicodeDecodeError:
                return None, None, False, f"File binary/unsupported: {filepath}"
    except Exception as e:
        return None, None, False, f"Error reading file {filepath}: {e}"

def sanitize_api_response(text):
    """
    Cleans markdown code fences from the start and end of the string.
    Works for ```json, ```xml, ```markdown, or just ```.
    """
    if not text: return ""
    text = text.strip()
    # Matches starting ``` (optional language) ... content ... ending ```
    # re.DOTALL allows matching across newlines
    pattern = re.compile(r"^```(?:\w+)?\s*(.*?)\s*```$", re.DOTALL)
    match = pattern.search(text)
    if match:
        return match.group(1).strip()
    return text

def call_generative_ai_api(engine, prompt_text, api_key, model_name, **kwargs):
    clean_output = kwargs.get('clean_markdown', True)
    
    response_text = ""
    error_msg = None

    if engine == "google": 
        response_text = call_google_gemini_api(prompt_text, api_key, model_name, **kwargs)
    elif engine == "ollama": 
        response_text = call_ollama_api(prompt_text, model_name, **kwargs)
    elif engine == "lmstudio": 
        response_text = call_lmstudio_api(prompt_text, model_name, **kwargs)
    else: 
        return f"Error: Unknown engine '{engine}'"
    
    # Check for error strings returned by wrappers
    if response_text and str(response_text).startswith("Error:"):
        return response_text

    if clean_output:
        return sanitize_api_response(response_text)
    return response_text

def call_google_gemini_api(prompt_text, api_key, model_name, client=None, google_file_objects=None, stream_output=False, safety_settings=None, **kwargs):
    global last_request_time
    if not api_key: return "Error: Google API Key not configured."
    try:
        if not client:
             client = genai.Client(api_key=api_key)
             
        if last_request_time and (time.time() - last_request_time < REQUEST_INTERVAL_SECONDS):
            time.sleep(REQUEST_INTERVAL_SECONDS - (time.time() - last_request_time))
        last_request_time = time.time()
        
        # Prepare contents
        contents = []
        if google_file_objects:
            # New SDK can take types.File directly or 'file' objects
            for f in google_file_objects:
                 contents.append(f)
        contents.append(prompt_text)
        
        # Configuration
        config = types.GenerateContentConfig(
             safety_settings=safety_settings
        )

        if stream_output:
            response = client.models.generate_content_stream(model=model_name, contents=contents, config=config)
        else:
            response = client.models.generate_content(model=model_name, contents=contents, config=config)
        
        if stream_output:
            full_text = ""
            print(f"\n--- [STREAM] Google Gemini ({model_name}) ---\n", end="", flush=True)
            for chunk in response:
                text_part = chunk.text
                if text_part:
                    print(text_part, end="", flush=True)
                    full_text += text_part
            print("\n----------------------------------------------\n", flush=True)
            return full_text
        else:
            # Check finish reason
            # response.candidates[0].finish_reason is now a string or enum in types
            # Accessing via attributes
            candidate = response.candidates[0] if response.candidates else None
            if not candidate:
                if response.prompt_feedback:
                    raise FatalProcessingError(f"Fatal: Blocked by Prompt Filter. Reason: {response.prompt_feedback.block_reason}")
                raise FatalProcessingError("Fatal: No candidates returned.")

            # Assuming finish_reason is convertible to str or comparable
            # New SDK finish reasons are strings like "STOP", "MAX_TOKENS", "SAFETY"
            reason = str(candidate.finish_reason)
            
            if reason != "STOP":
                 # Map new string reasons to our readable dict if possible, or just use raw
                 # Our old dict was integer based.
                 msg = f"Fatal: Blocked by Google. Reason: {reason}"
                 raise FatalProcessingError(msg)
                 
            return response.text
            
    except ResourceExhausted: raise QuotaExhaustedError(f"Quota exhausted for model {model_name}")
    except FatalProcessingError: raise 
    except Exception as e: raise e

def call_ollama_api(prompt_text, model_name, images_data_list=None, enable_web_search=False, stream_output=False, **kwargs):
    try:
        message = {'role': 'user', 'content': prompt_text}
        if images_data_list:
            message['images'] = [img['bytes'] for img in images_data_list]

        tools_list = [ollama.web_search] if enable_web_search else []

        if stream_output:
            print(f"\n--- [STREAM] Ollama ({model_name}) ---\n", end="", flush=True)
            stream = ollama.chat(
                model=model_name,
                messages=[message],
                tools=tools_list,
                stream=True
            )
            full_text = ""
            for chunk in stream:
                part = chunk['message']['content']
                print(part, end="", flush=True)
                full_text += part
            print("\n---------------------------------------\n", flush=True)
            return full_text
        else:
            response = ollama.chat(
                model=model_name,
                messages=[message],
                tools=tools_list, 
            )
            return response['message']['content']
    except Exception as e:
        return f"Error: Ollama API: {str(e)}"

def call_lmstudio_api(prompt_text, model_name, images_data_list=None, stream_output=False, **kwargs):
    headers = {"Content-Type": "application/json"}
    if images_data_list:
        message_content = [{"type": "text", "text": prompt_text}]
        for img_data in images_data_list:
            b64 = base64.b64encode(img_data['bytes']).decode('utf-8')
            message_content.append({
                "type": "image_url", 
                "image_url": {"url": f"data:{img_data['mime_type']};base64,{b64}"}
            })
        final_content = message_content
    else:
        final_content = prompt_text
    
    payload = {
        "model": model_name, 
        "messages": [{"role": "user", "content": final_content}], 
        "stream": stream_output
    }
    
    try:
        response = requests.post(LMSTUDIO_CHAT_COMPLETIONS_ENDPOINT, headers=headers, json=payload, stream=stream_output, timeout=600)
        response.raise_for_status()
        
        if stream_output:
            print(f"\n--- [STREAM] LM Studio ({model_name}) ---\n", end="", flush=True)
            full_text = ""
            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8').strip()
                    if decoded_line.startswith("data: "):
                        json_str = decoded_line[6:] # Skip "data: "
                        if json_str == "[DONE]": break
                        try:
                            chunk_json = json.loads(json_str)
                            content = chunk_json.get("choices", [{}])[0].get("delta", {}).get("content", "")
                            if content:
                                print(content, end="", flush=True)
                                full_text += content
                        except json.JSONDecodeError: pass
            print("\n-----------------------------------------\n", flush=True)
            return full_text
        else:
            return response.json().get("choices", [{}])[0].get("message", {}).get("content", "")

    except requests.exceptions.HTTPError as e:
        if 'response' in locals() and response is not None:
             print(f"LM Studio Error Details: {response.text}")
        raise e

def determine_unique_output_paths(base_name, suffix, out_folder, log_folder, output_extension=RAW_OUTPUT_FILE_EXTENSION):
    out_base = f"{base_name}{suffix}"
    def find_unique(folder, base, ext):
        path = os.path.join(folder, f"{base}{ext}")
        if not os.path.exists(path): return path
        i = 1
        while True:
            path = os.path.join(folder, f"{base} ({i}){ext}")
            if not os.path.exists(path): return path
            i += 1
    return find_unique(out_folder, out_base, output_extension), find_unique(log_folder, out_base, LOG_FILE_EXTENSION)

def save_output_files(api_response, log_data, raw_path, log_path):
    try:
        with open(raw_path, 'w', encoding='utf-8') as f: f.write(api_response or "[Empty Response]")
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write("="*20 + " Processing Log " + "="*20 + "\n")
            for k, v in log_data.items():
                if isinstance(v, datetime.datetime): v = v.strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"{k}: {v}\n")
            f.write("="*50 + "\n")
    except Exception as e: console_log(f"Error saving files: {e}", "ERROR")

def copy_failed_file(filepath):
    try:
        failed_dir = os.path.join(os.path.dirname(filepath), FAILED_SUBFOLDER_NAME)
        os.makedirs(failed_dir, exist_ok=True)
        shutil.copy2(filepath, os.path.join(failed_dir, os.path.basename(filepath)))
    except Exception: pass

def process_file_group(filepaths_group, api_key, engine, user_prompt, model_name, add_filename_to_prompt=False, overwrite_original=False, **kwargs):
    start_time = datetime.datetime.now()
    base_name = generate_group_base_name(filepaths_group)
    log_data = {'input_filepaths': filepaths_group, 'start_time': start_time, 'engine': engine, 'model_name': model_name}
    console_log(f"Processing group: {base_name} ({len(filepaths_group)} files)...")

    source_dir = os.path.dirname(filepaths_group[0])
    if not source_dir: source_dir = "."

    if overwrite_original and len(filepaths_group) == 1:
        raw_path = filepaths_group[0]
        log_dir = os.path.join(source_dir, LOG_SUBFOLDER_NAME)
        os.makedirs(log_dir, exist_ok=True)
        _, log_path = determine_unique_output_paths(base_name, kwargs['output_suffix'], log_dir, log_dir)
    else:
        out_folder = kwargs.get('output_folder') or source_dir
        log_folder = os.path.join(out_folder, LOG_SUBFOLDER_NAME)
        os.makedirs(out_folder, exist_ok=True); os.makedirs(log_folder, exist_ok=True)
        requested_ext = kwargs.get('output_extension', '').strip()
        ext = ('.' + requested_ext.lstrip('.')) if requested_ext else RAW_OUTPUT_FILE_EXTENSION
        raw_path, log_path = determine_unique_output_paths(base_name, kwargs['output_suffix'], out_folder, log_folder, ext)

    try:
        # --- SPLIT TEXT vs IMAGES ---
        image_files = [f for f in filepaths_group if os.path.splitext(f)[1].lower() in SUPPORTED_IMAGE_EXTENSIONS]
        text_files = [f for f in filepaths_group if f not in image_files]
        
        images_data_legacy = [] # For Ollama/LMStudio (Base64)
        google_file_objects = [] # For Gemini (Files API)
        prompt_parts = []
        client = None

        if engine == "google":
             client = genai.Client(api_key=api_key)

        # 1. Handle Images
        if image_files:
            if engine == "google":
                sequential_upload = kwargs.get('sequential_upload', False)
                google_file_objects = upload_images_parallel(image_files, client, sequential=sequential_upload)
            else:
                for img_path in image_files:
                    content, mime, _, err = read_file_content(img_path)
                    if not err:
                        images_data_legacy.append({"bytes": content, "mime_type": mime})

        # 2. Handle Text Files
        for filepath in text_files:
            content, _, _, err = read_file_content(filepath)
            if err: raise ValueError(err)
            if add_filename_to_prompt: prompt_parts.append(f"\n--- File: {os.path.basename(filepath)} ---")
            prompt_parts.append(f"\n{content}\n")
        
        
        full_prompt = user_prompt + "".join(prompt_parts)
        log_data['prompt_sent'] = full_prompt
        
        response = call_generative_ai_api(
            engine, 
            full_prompt, 
            api_key, 
            model_name,
            client=client,
            images_data_list=images_data_legacy, # For Ollama/LMStudio
            google_file_objects=google_file_objects, # For Gemini
            stream_output=kwargs['stream_output'], 
            safety_settings=kwargs.get('safety_settings'),
            enable_web_search=kwargs.get('enable_web_search', False),
            clean_markdown=kwargs.get('clean_markdown', True) # Pass clean setting
        )
        
        if response and str(response).strip().startswith("Error"): 
            raise Exception(response)

        # --- RENAME MODE LOGIC ---
        if kwargs.get('rename_mode', False):
            # 1. Sanitize
            new_stem = sanitize_filename(response)
            if not new_stem: raise ValueError("LLM returned empty or invalid filename.")
            
            # 2. Collision Handling
            if len(filepaths_group) > 1: raise ValueError("Rename Mode requires single file groups.")
            original_path = filepaths_group[0]
            
            directory = os.path.dirname(original_path)
            ext = os.path.splitext(original_path)[1]
            
            new_filename = f"{new_stem}{ext}"
            new_path = os.path.join(directory, new_filename)
            
            counter = 1
            while os.path.exists(new_path) and os.path.normpath(new_path) != os.path.normpath(original_path):
                 new_path = os.path.join(directory, f"{new_stem}_{counter}{ext}")
                 counter += 1
            
            # 3. Rename
            if os.path.normpath(new_path) != os.path.normpath(original_path):
                os.rename(original_path, new_path)
                console_log(f"Renamed: {os.path.basename(original_path)} -> {os.path.basename(new_path)}", "ACTION")
                
                if 'result_metadata' in kwargs:
                    kwargs['result_metadata']['rename_from'] = original_path
                    kwargs['result_metadata']['rename_to'] = new_path
                else: 
                     console_log("Warning: result_metadata missing, Undo unavailable.", "WARN")
            else:
                 console_log(f"Filename unchanged: {os.path.basename(original_path)}", "WARN")
            
            return None        

        # --- JSON VALIDITY CHECK ---
        if kwargs.get('validate_json', False):
            # Already mostly sanitized by clean_markdown if enabled, but good to ensure
            response = sanitize_api_response(response)
            parsed_json = None
            validation_error = None
            if json_repair:
                try: parsed_json = json_repair.loads(response)
                except Exception as e: validation_error = f"json_repair failed: {e}"
            if parsed_json is None:
                match = re.search(r'(\{.*\}|\[.*\])', response, re.DOTALL)
                if match:
                    try: parsed_json = json.loads(match.group(1))
                    except json.JSONDecodeError as e: 
                        if not validation_error: validation_error = f"JSON Validation Failed (Extracted): {e.msg} line {e.lineno}"
                else:
                    try: parsed_json = json.loads(response)
                    except json.JSONDecodeError as e:
                        if not validation_error: validation_error = f"JSON Validation Failed: {e.msg} line {e.lineno}"

            if parsed_json is not None:
                # --- NEW: SCHEMA VALIDATION (v25.6) ---
                if kwargs.get('validate_json_keys', False):
                    if not isinstance(parsed_json, dict):
                         raise ValueError("JSON Validation Failed: Output is not a JSON Object (Dictionary)")
                    
                    required_keys = ["title", "description", "hashtags", "tags"]
                    missing_keys = [k for k in required_keys if k not in parsed_json]
                    
                    if missing_keys:
                        # Construct a helpful error message so the LLM knows what it missed if retried
                        raise ValueError(f"JSON Validation Failed: Missing required keys: {missing_keys}")
                        
                response = json.dumps(parsed_json, indent=4)
            else:
                log_data['invalid_output_content'] = response 
                raise ValueError(validation_error or "Unknown JSON validation error")

        log_data.update({'status': 'Success', 'end_time': datetime.datetime.now()})
        save_output_files(response, log_data, raw_path, log_path)
        console_log(f"Saved: {os.path.basename(raw_path)}", "SUCCESS")
        return None

    except Exception as e:
        log_data.update({'status': 'Failure', 'error': str(e)})
        if isinstance(e, QuotaExhaustedError): raise
        if isinstance(e, FatalProcessingError): raise
        
        is_json_fail = "JSON Validation Failed" in str(e) or "json_repair failed" in str(e)
        if is_json_fail: console_log(f"Skipping save for {os.path.basename(raw_path)} ({e})", "WARN")
        else: save_output_files(f"Error: {e}", log_data, raw_path, log_path)
        return str(e)

def get_api_key(force_gui=False):
    api_key = os.environ.get(API_KEY_ENV_VAR_NAME)
    if not api_key or force_gui:
        if not force_gui: console_log(f"{API_KEY_ENV_VAR_NAME} not in environment. Prompting...", "WARN")
        root = tk.Tk(); root.withdraw()
        api_key = tk.simpledialog.askstring("API Key", "Enter Google API Key:", show='*')
        root.destroy()
    return api_key

################################################################################
# --- GUI Class ---
################################################################################

class ModelSelectionDialog(tk.Toplevel):
    def __init__(self, parent, current_engine, current_model, fetch_callback, exhausted_set):
        super().__init__(parent)
        self.title("Quota Exhausted")
        self.result = None
        self.fetch_callback = fetch_callback
        self.exhausted_set = exhausted_set
        self.quota_marker = " ⛔ (Quota Hit)"
        
        w, h = 450, 200
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (w // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.resizable(False, False)

        frame = ttk.Frame(self, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text=f"Quota exhausted for: {current_model}", foreground="red").pack(pady=(0, 5))
        ttk.Label(frame, text="Select a new Provider and Model:", font=('Helvetica', 9, 'bold')).pack(pady=(0, 10))

        grid_frame = ttk.Frame(frame)
        grid_frame.pack(fill=tk.X)

        ttk.Label(grid_frame, text="Provider:").grid(row=0, column=0, sticky="w", padx=5)
        self.provider_var = tk.StringVar(value=current_engine)
        self.provider_combo = ttk.Combobox(grid_frame, textvariable=self.provider_var, 
                                           values=['google', 'ollama', 'lmstudio'], state="readonly", width=15)
        self.provider_combo.grid(row=0, column=1, sticky="ew", padx=5)
        self.provider_combo.bind("<<ComboboxSelected>>", self.on_provider_change)

        ttk.Label(grid_frame, text="Model:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.model_combo_var = tk.StringVar()
        self.model_combo = ttk.Combobox(grid_frame, textvariable=self.model_combo_var, state="readonly", width=35)
        self.model_combo.grid(row=1, column=1, sticky="ew", padx=5, pady=5)

        self.on_provider_change(None, initial_model=current_model)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=15, fill=tk.X)
        ttk.Button(btn_frame, text="Cancel", command=self.on_cancel).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Apply to Remaining Jobs", command=self.on_ok).pack(side=tk.RIGHT, padx=5)

        self.protocol("WM_DELETE_WINDOW", self.on_cancel)
        self.transient(parent)
        self.wait_visibility()
        self.grab_set()
        self.wait_window(self)

    def on_provider_change(self, event, initial_model=None):
        engine = self.provider_var.get()
        self.model_combo.set("Loading...")
        self.model_combo['values'] = []
        self.update_idletasks()
        
        models = self.fetch_callback(engine)
        
        display_values = []
        for m in models:
            if m in self.exhausted_set:
                display_values.append(f"{m}{self.quota_marker}")
            else:
                display_values.append(m)
        
        self.model_combo['values'] = display_values
        
        if display_values:
            if initial_model and initial_model in models:
                if initial_model in self.exhausted_set: self.model_combo.set(f"{initial_model}{self.quota_marker}")
                else: self.model_combo.set(initial_model)
            else: self.model_combo.current(0)
        else:
            self.model_combo.set("No models found")

    def on_ok(self):
        raw_model = self.model_combo_var.get()
        clean_model = raw_model.split(self.quota_marker)[0]
        self.result = (self.provider_var.get(), clean_model)
        self.destroy()

    def on_cancel(self):
        self.result = None
        self.destroy()

class AppGUI(tk.Tk):
    def __init__(self, initial_api_key, command_line_files, args):
        super().__init__()
        self.title("Multimodal AI Batch Processor v25.6 (Gemini Files API Supported)")
        self.geometry("1400x800")
        self.minsize(1100, 700)
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        signal.signal(signal.SIGINT, self._handle_sigint)
        self._check_signal()

        self.api_key = initial_api_key
        self.args = args
        self.job_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.job_registry = {}
        self.current_presets = {}
        self.model_cache = {} 
        self.exhausted_models = set()
        self.global_runtime_overrides = None 
        
        self.processing_paused = threading.Event()
        self.processing_cancelled = threading.Event()
        self.worker_thread = None
        self.job_id_counter = 0

        self.files_var = tk.Variable(value=list(command_line_files or []))
        self.engine_var = tk.StringVar(value=getattr(self.args, 'engine', DEFAULT_ENGINE))
        self.model_var = tk.StringVar()
        self.output_dir_var = tk.StringVar(value=getattr(self.args, 'output', DEFAULT_OUTPUT_SUBFOLDER_NAME))
        self.suffix_var = tk.StringVar(value=getattr(self.args, 'suffix', DEFAULT_RAW_OUTPUT_SUFFIX))
        self.output_ext_var = tk.StringVar(value=getattr(self.args, 'output_ext', ''))
        # --- UPDATE: STREAM ENABLED BY DEFAULT ---
        self.stream_var = tk.BooleanVar(value=getattr(self.args, 'stream', True))
        self.add_filename_var = tk.BooleanVar(value=getattr(self.args, 'add_filename_to_prompt', False))
        self.group_files_var = tk.BooleanVar(value=False)
        self.group_size_var = tk.IntVar(value=3)
        self.overwrite_var = tk.BooleanVar(value=False)
        self.validate_json_var = tk.BooleanVar(value=False)
        self.validate_keys_var = tk.BooleanVar(value=False) # New schema validation var (v25.6)
        self.clean_markdown_var = tk.BooleanVar(value=True) # Default On
        self.enable_safety_var = tk.BooleanVar(value=False)
        self.safety_map = {'Off': 'BLOCK_NONE', 'High Only': 'BLOCK_ONLY_HIGH', 'Med+': 'BLOCK_MEDIUM_AND_ABOVE'}
        self.harassment_var = tk.StringVar(value='Off')
        self.hate_speech_var = tk.StringVar(value='Off')
        self.sexually_explicit_var = tk.StringVar(value='Off')
        self.dangerous_content_var = tk.StringVar(value='Off')
        
        # Job Delay Variables
        self.delay_min_var = tk.IntVar(value=0)
        self.delay_sec_var = tk.IntVar(value=0)

        # Upload Mode (Parallel vs Sequential)
        self.upload_mode_var = tk.StringVar(value=getattr(self.args, 'upload_mode', 'parallel'))
        
        # Rename Mode
        self.rename_mode_var = tk.BooleanVar(value=False)

        self.create_widgets()
        self.refresh_presets_combo()
        self.engine_var.trace_add("write", self.update_models)
        self.after(200, self.update_models)
        self.after(100, self._check_result_queue)

    def _check_signal(self):
        self.after(500, self._check_signal)

    def _handle_sigint(self, signum, frame):
        console_log("Received Ctrl+C. Exiting gracefully...", "WARN")
        self._on_closing()

    def create_widgets(self):
        toolbar = ttk.Frame(self, padding=(10, 5))
        toolbar.pack(side=tk.TOP, fill=tk.X)
        
        ttk.Label(toolbar, text="Preset:").pack(side=tk.LEFT, padx=(0, 5))
        self.preset_var = tk.StringVar()
        self.preset_combo = ttk.Combobox(toolbar, textvariable=self.preset_var, state="readonly", width=30)
        self.preset_combo.pack(side=tk.LEFT)
        self.preset_combo.bind("<<ComboboxSelected>>", self.load_preset)
        
        ttk.Button(toolbar, text="➕ New", width=6, command=self.create_new_preset).pack(side=tk.LEFT, padx=(5, 1))
        ttk.Button(toolbar, text="💾 Save", width=6, command=self.save_current_preset).pack(side=tk.LEFT, padx=1)
        ttk.Button(toolbar, text="✏️ Ren", width=6, command=self.rename_preset).pack(side=tk.LEFT, padx=1)
        ttk.Button(toolbar, text="🗑️ Del", width=6, command=self.delete_preset).pack(side=tk.LEFT, padx=1)
        
        self.api_status_label = ttk.Label(toolbar, text=f"API Key: {'Set' if self.api_key else 'Not Set'}", foreground="blue")
        self.api_status_label.pack(side=tk.RIGHT, padx=10)
        ttk.Button(toolbar, text="Update Key", command=self.prompt_for_api_key).pack(side=tk.RIGHT)

        main_pane = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        left_frame = ttk.Frame(main_pane)
        main_pane.add(left_frame, weight=1)
        
        file_frame = ttk.LabelFrame(left_frame, text="1. Input Files", padding=5)
        file_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=(0, 5))
        self.file_listbox = tk.Listbox(file_frame, listvariable=self.files_var, selectmode=tk.EXTENDED, height=6)
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb = ttk.Scrollbar(file_frame, orient=tk.VERTICAL, command=self.file_listbox.yview)
        sb.pack(side=tk.LEFT, fill=tk.Y); self.file_listbox.config(yscrollcommand=sb.set)
        
        btn_f = ttk.Frame(file_frame)
        btn_f.pack(side=tk.LEFT, fill=tk.Y, padx=5)
        ttk.Button(btn_f, text="Add", command=self.add_files).pack(fill=tk.X, pady=2)
        ttk.Button(btn_f, text="Remove", command=self.remove_files).pack(fill=tk.X, pady=2)
        ttk.Button(btn_f, text="Clear", command=self.clear_files).pack(fill=tk.X, pady=2)

        prompt_frame = ttk.LabelFrame(left_frame, text="2. System Prompt", padding=5)
        prompt_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=(0, 5))
        self.prompt_text = scrolledtext.ScrolledText(prompt_frame, height=10)
        self.prompt_text.pack(fill=tk.BOTH, expand=True)
        self.prompt_text.insert(tk.INSERT, USER_PROMPT_TEMPLATE)

        settings_frame = ttk.LabelFrame(left_frame, text="3. Configuration", padding=5)
        settings_frame.pack(side=tk.TOP, fill=tk.X, pady=(0, 5))
        self.notebook = ttk.Notebook(settings_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        tab_ai = ttk.Frame(self.notebook, padding=10); self.notebook.add(tab_ai, text="AI Engine")
        ttk.Label(tab_ai, text="Provider:").grid(row=0, column=0, sticky="w")
        ttk.Combobox(tab_ai, textvariable=self.engine_var, values=['google', 'ollama', 'lmstudio'], state="readonly").grid(row=0, column=1, sticky="ew", padx=5)
        ttk.Label(tab_ai, text="Model:").grid(row=1, column=0, sticky="w", pady=5)
        self.model_combo = ttk.Combobox(tab_ai, textvariable=self.model_var, state="disabled", width=50); self.model_combo.grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        ttk.Checkbutton(tab_ai, text="Append Filename to Prompt", variable=self.add_filename_var).grid(row=2, column=0, columnspan=2, sticky="w")
        
        self.ollama_search_var = tk.BooleanVar(value=False)
        self.ollama_search_check = ttk.Checkbutton(tab_ai, text="Enable Web Search (Ollama Only)", variable=self.ollama_search_var)
        self.ollama_search_check.grid(row=3, column=0, columnspan=2, sticky="w", pady=(5,0))

        tab_out = ttk.Frame(self.notebook, padding=10); self.notebook.add(tab_out, text="Output & Batch")
        ttk.Label(tab_out, text="Folder:").grid(row=0, column=0, sticky="w")
        self.out_ent = ttk.Entry(tab_out, textvariable=self.output_dir_var, width=15); self.out_ent.grid(row=0, column=1, sticky="ew")
        ttk.Button(tab_out, text="...", width=3, command=self.browse_out).grid(row=0, column=2)
        ttk.Label(tab_out, text="Suffix/Ext:").grid(row=1, column=0, sticky="w")
        f_ext = ttk.Frame(tab_out); f_ext.grid(row=1, column=1, columnspan=2, sticky="ew")
        self.suf_ent = ttk.Entry(f_ext, textvariable=self.suffix_var, width=10); self.suf_ent.pack(side=tk.LEFT)
        self.ext_ent = ttk.Entry(f_ext, textvariable=self.output_ext_var, width=6); self.ext_ent.pack(side=tk.LEFT, padx=5)
        self.group_check = ttk.Checkbutton(tab_out, text="Group Files:", variable=self.group_files_var, command=self.toggle_grouping)
        self.group_check.grid(row=2, column=0, sticky="w", pady=5)
        
        self.group_spin = ttk.Spinbox(tab_out, from_=2, to=5000, textvariable=self.group_size_var, width=5, state="disabled")
        self.group_spin.grid(row=2, column=1, sticky="w", pady=5)
        
        self.over_check = ttk.Checkbutton(tab_out, text="Overwrite Original", variable=self.overwrite_var, command=self.toggle_overwrite)
        self.over_check.grid(row=3, column=0, columnspan=2, sticky="w")
        
        # New Cleanup Option
        self.clean_md_check = ttk.Checkbutton(tab_out, text="Clean Markdown Fences (```)", variable=self.clean_markdown_var)
        self.clean_md_check.grid(row=4, column=0, columnspan=2, sticky="w", pady=(2, 0))

        self.json_check = ttk.Checkbutton(tab_out, text="Validate JSON Output", variable=self.validate_json_var)
        self.json_check.grid(row=5, column=0, columnspan=2, sticky="w", pady=(2, 0))
        
        # New Checkbox for Schema Validation (v25.6)
        self.json_keys_check = ttk.Checkbutton(tab_out, text="Enforce Schema (Title, Desc, Tags)", variable=self.validate_keys_var)
        self.json_keys_check.grid(row=6, column=0, columnspan=2, sticky="w", padx=(20, 0), pady=(0, 2))
        
        # Rename Mode
        self.rename_check = ttk.Checkbutton(tab_out, text="Rename Input Mode (File System Change)", variable=self.rename_mode_var, command=self.toggle_rename_mode)
        self.rename_check.grid(row=7, column=0, columnspan=2, sticky="w", pady=(5, 0))

        # Upload Mode Radio Buttons
        ttk.Label(tab_out, text="Upload Mode:").grid(row=8, column=0, sticky="w", pady=(5, 0))
        u_frame = ttk.Frame(tab_out)
        u_frame.grid(row=8, column=1, columnspan=2, sticky="ew", pady=(5, 0))
        ttk.Radiobutton(u_frame, text="Parallel", variable=self.upload_mode_var, value="parallel").pack(side=tk.LEFT)
        ttk.Radiobutton(u_frame, text="Sequential", variable=self.upload_mode_var, value="sequential").pack(side=tk.LEFT, padx=10)

        self.stream_check = ttk.Checkbutton(tab_out, text="Stream Output to Console", variable=self.stream_var)
        self.stream_check.grid(row=9, column=0, columnspan=2, sticky="w", pady=(5, 0))

        # --- Delay Controls ---
        delay_frame = ttk.Frame(tab_out)
        delay_frame.grid(row=10, column=0, columnspan=3, sticky="w", pady=(5, 0))
        ttk.Label(delay_frame, text="Delay between jobs:").pack(side=tk.LEFT)
        ttk.Spinbox(delay_frame, from_=0, to=60, textvariable=self.delay_min_var, width=3).pack(side=tk.LEFT, padx=2)
        ttk.Label(delay_frame, text="m").pack(side=tk.LEFT)
        ttk.Spinbox(delay_frame, from_=0, to=60, textvariable=self.delay_sec_var, width=3).pack(side=tk.LEFT, padx=2)
        ttk.Label(delay_frame, text="s").pack(side=tk.LEFT)

        tab_safe = ttk.Frame(self.notebook, padding=10); self.notebook.add(tab_safe, text="Safety")
        ttk.Checkbutton(tab_safe, text="Enable Filters", variable=self.enable_safety_var, command=self.toggle_safety).pack(anchor="w")
        self.safety_widgets = []
        safe_grid = ttk.Frame(tab_safe); safe_grid.pack(fill=tk.X, pady=5)
        for i, (txt, var) in enumerate([("Harassment", self.harassment_var), ("Hate Speech", self.hate_speech_var), 
                                        ("Sexual", self.sexually_explicit_var), ("Dangerous", self.dangerous_content_var)]):
            l = ttk.Label(safe_grid, text=txt); l.grid(row=i, column=0, sticky="w")
            c = ttk.Combobox(safe_grid, textvariable=var, values=list(self.safety_map.keys()), state="disabled", width=12)
            c.grid(row=i, column=1, sticky="ew", padx=5); self.safety_widgets.extend([l, c])

        right_frame = ttk.Frame(main_pane); main_pane.add(right_frame, weight=2)
        q_frame = ttk.LabelFrame(right_frame, text="Job Queue", padding=5); q_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.tree = ttk.Treeview(q_frame, columns=('id', 'name', 'status', 'model'), show='headings')
        self.tree.heading('id', text='ID'); self.tree.column('id', width=30)
        self.tree.heading('name', text='File/Group'); self.tree.column('name', width=250)
        self.tree.heading('status', text='Status'); self.tree.column('status', width=100)
        self.tree.heading('model', text='Model'); self.tree.column('model', width=120)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sc = ttk.Scrollbar(q_frame, orient=tk.VERTICAL, command=self.tree.yview); sc.pack(side=tk.RIGHT, fill=tk.Y); self.tree.config(yscrollcommand=sc.set)

        btn_area = ttk.Frame(right_frame, padding=10); btn_area.pack(side=tk.BOTTOM, fill=tk.X)
        self.btn_add_sel = ttk.Button(btn_area, text="Add Sel", width=8, command=lambda: self.add_to_queue(True)); self.btn_add_sel.pack(side=tk.LEFT, padx=2)
        self.btn_add_all = ttk.Button(btn_area, text="Add All", width=8, command=lambda: self.add_to_queue(False)); self.btn_add_all.pack(side=tk.LEFT, padx=2)
        self.start_btn = ttk.Button(btn_area, text="START PROCESSING", command=self.start_processing, style="Accent.TButton"); self.start_btn.pack(side=tk.RIGHT, padx=5, ipadx=10)
        self.pause_btn = ttk.Button(btn_area, text="Pause", command=self.toggle_pause, state="disabled"); self.pause_btn.pack(side=tk.RIGHT, padx=5)
        self.clear_btn = ttk.Button(btn_area, text="Clear", command=self.clear_queue); self.clear_btn.pack(side=tk.RIGHT, padx=5)
        self.btn_requeue = ttk.Button(btn_area, text="Retry Failed", command=self.requeue_failed); self.btn_requeue.pack(side=tk.RIGHT, padx=5)
        self.btn_undo = ttk.Button(btn_area, text="Undo Rename", command=self.undo_rename); self.btn_undo.pack(side=tk.RIGHT, padx=5)
        ttk.Style().configure("Accent.TButton", font=('Helvetica', 10, 'bold'), foreground="black")

        # --- Context Menu ---
        self.context_menu = tk.Menu(self.tree, tearoff=0)
        self.context_menu.add_command(label="Remove Selected", command=self.remove_selected_jobs)
        self.context_menu.add_command(label="Retry Selected", command=self.retry_selected_jobs)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Copy Filepath/Group", command=self.copy_job_name)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Clear Completed", command=self.clear_completed_jobs)
        
        self.tree.bind("<Button-3>", self.show_context_menu)

    def refresh_presets_combo(self):
        console_log("Loading presets from script file...", "INFO")
        self.current_presets = load_presets()
        self.preset_combo['values'] = sorted(list(self.current_presets.keys()))

    def load_preset(self, event=None):
        name = self.preset_var.get()
        console_log(f"User selected preset: {name}", "ACTION")
        if name in self.current_presets:
            data = self.current_presets[name]
            self.prompt_text.delete("1.0", tk.END); self.prompt_text.insert(tk.END, data.get('prompt', ''))
            
            def set_var(var, key, default=None):
                if key in data: var.set(data[key])
                elif default is not None: var.set(default)

            set_var(self.engine_var, 'engine')
            self.update_models()
            set_var(self.model_var, 'model')
            set_var(self.suffix_var, 'output_suffix')
            set_var(self.output_ext_var, 'output_extension', "")
            set_var(self.overwrite_var, 'overwrite_original', False)
            set_var(self.stream_var, 'stream_output', False)
            set_var(self.group_size_var, 'group_size', 3)
            set_var(self.group_files_var, 'group_files', False)
            set_var(self.validate_json_var, 'validate_json', False)
            set_var(self.validate_keys_var, 'validate_json_keys', False) # Load new setting
            set_var(self.clean_markdown_var, 'clean_markdown', True) 
            set_var(self.delay_min_var, 'delay_min', 0)
            set_var(self.delay_sec_var, 'delay_sec', 0)
            set_var(self.upload_mode_var, 'upload_mode', 'parallel')
            set_var(self.rename_mode_var, 'rename_mode', False)
            self.ollama_search_var.set(False)
            
            self.toggle_rename_mode()
            
            self.toggle_overwrite()
            self.toggle_grouping()

    def get_current_settings_dict(self):
        return {
            'prompt': self.prompt_text.get("1.0", tk.END).strip(),
            'engine': self.engine_var.get(),
            'model': self.model_var.get(),
            'output_suffix': self.suffix_var.get(),
            'output_extension': self.output_ext_var.get(),
            'overwrite_original': self.overwrite_var.get(),
            'stream_output': self.stream_var.get(),
            'group_size': self.group_size_var.get(),
            'group_files': self.group_files_var.get(),
            'validate_json': self.validate_json_var.get(),
            'validate_json_keys': self.validate_keys_var.get(), # Save new setting
            'clean_markdown': self.clean_markdown_var.get(),
            'delay_min': self.delay_min_var.get(),
            'delay_min': self.delay_min_var.get(),
            'delay_sec': self.delay_sec_var.get(),
            'upload_mode': self.upload_mode_var.get(),
            'rename_mode': self.rename_mode_var.get()
        }

    def save_current_preset(self):
        name = self.preset_var.get()
        if not name: tkinter.messagebox.showwarning("Save", "No preset selected."); return
        if name not in self.current_presets: tkinter.messagebox.showerror("Error", "Preset not found."); return
        self.current_presets[name] = self.get_current_settings_dict()
        save_presets(self.current_presets)
        tkinter.messagebox.showinfo("Saved", f"Preset '{name}' updated.")

    def create_new_preset(self):
        new_name = tkinter.simpledialog.askstring("New Preset", "Enter Name for New Preset:")
        if not new_name: return
        if new_name in self.current_presets:
            if not tkinter.messagebox.askyesno("Overwrite", f"Preset '{new_name}' exists. Overwrite?"): return
        self.current_presets[new_name] = self.get_current_settings_dict()
        save_presets(self.current_presets)
        self.refresh_presets_combo(); self.preset_var.set(new_name)

    def rename_preset(self):
        old_name = self.preset_var.get()
        if not old_name or old_name not in self.current_presets: return
        new_name = tkinter.simpledialog.askstring("Rename Preset", f"Rename '{old_name}' to:", initialvalue=old_name)
        if not new_name or new_name == old_name: return
        if new_name in self.current_presets:
            if not tkinter.messagebox.askyesno("Overwrite", f"'{new_name}' exists. Overwrite?"): return
        self.current_presets[new_name] = self.current_presets.pop(old_name)
        save_presets(self.current_presets)
        self.refresh_presets_combo(); self.preset_var.set(new_name)

    def delete_preset(self):
        name = self.preset_var.get()
        if name and name in self.current_presets:
            if tkinter.messagebox.askyesno("Confirm", f"Delete '{name}'?"):
                del self.current_presets[name]
                save_presets(self.current_presets)
                self.refresh_presets_combo(); self.preset_var.set('')

    def _on_closing(self):
        if self.worker_thread and self.worker_thread.is_alive():
            self.processing_cancelled.set()
            self.worker_thread.join(timeout=1.0) 
        self.destroy(); sys.exit(0)

    def toggle_overwrite(self):
        st = "disabled" if self.overwrite_var.get() else "normal"
        self.group_check.config(state=st); self.group_spin.config(state=st if self.group_files_var.get() else "disabled")
        self.out_ent.config(state=st); self.suf_ent.config(state=st); self.ext_ent.config(state=st)

    def toggle_grouping(self):
        st = "normal" if self.group_files_var.get() else "disabled"
        self.group_spin.config(state=st); self.over_check.config(state="disabled" if st=="normal" else "normal")

    def toggle_safety(self):
        st = "readonly" if self.enable_safety_var.get() else "disabled"
        for w in self.safety_widgets: w.config(state=st)

    def toggle_rename_mode(self):
        is_rename = self.rename_mode_var.get()
        state = "disabled" if is_rename else "normal"
        
        # Disable/Enable Output controls
        self.out_ent.config(state=state)
        self.suf_ent.config(state=state)
        self.ext_ent.config(state=state)
        self.over_check.config(state=state)
        self.group_check.config(state=state)
        
        # Force Grouping to False/1 if Rename Mode is ON
        if is_rename:
            self.group_files_var.set(False)
            self.group_spin.config(state="disabled")
        else:
            self.toggle_grouping() # Restore correct state based on checkbox

    def prompt_for_api_key(self):
        k = get_api_key(True)
        if k: self.api_key = k; self.api_status_label.config(text="API Key: Set"); self.update_models()

    def get_models_for_provider(self, provider):
        if provider in self.model_cache: return self.model_cache[provider]
        m, err = [], None
        if provider == "google": m, err = fetch_google_models(self.api_key)
        elif provider == "ollama": m, err = fetch_ollama_models()
        elif provider == "lmstudio": m, err = fetch_lmstudio_models()
        if m: self.model_cache[provider] = m
        return m or []

    def update_models(self, *args):
        e = self.engine_var.get()
        if e == 'ollama': self.ollama_search_check.grid()
        else: self.ollama_search_check.grid_remove(); self.ollama_search_var.set(False)

        self.model_combo.set('Loading...')
        self.model_combo.config(state="disabled")
        self.update_idletasks()
        
        m = self.get_models_for_provider(e)
        if m:
            self.model_combo['values'] = m
            self.model_combo.config(state="readonly")
            curr = self.model_var.get()
            if curr and curr in m: self.model_combo.set(curr)
            else: self.model_combo.set(DEFAULT_GOOGLE_MODEL if e=="google" and DEFAULT_GOOGLE_MODEL in m else m[0])
        else: self.model_combo.set("No models found")

    def add_files(self):
        f = filedialog.askopenfilenames(parent=self, filetypes=[("Supported", " ".join(f"*{e}" for e in SUPPORTED_IMAGE_EXTENSIONS + ['.*']))])
        if f:
            cur = list(self.files_var.get()); new = [os.path.normpath(x) for x in f if os.path.normpath(x) not in cur]
            self.files_var.set(tuple(sorted(cur + new, key=natural_sort_key)))

    def remove_files(self):
        sel = self.file_listbox.curselection()
        if sel:
            l = list(self.files_var.get()); 
            for i in sorted(sel, reverse=True): l.pop(i)
            self.files_var.set(tuple(l))

    def clear_files(self): self.files_var.set([])
    def browse_out(self):
        d = filedialog.askdirectory(parent=self)
        if d: self.output_dir_var.set(d)

    def add_to_queue(self, only_selected=False):
        if only_selected:
            indices = self.file_listbox.curselection(); all_files = self.files_var.get(); files = [all_files[i] for i in indices]
            if not files: tkinter.messagebox.showwarning("Selection", "No files selected."); return
        else:
            files = list(self.files_var.get())
            if not files: tkinter.messagebox.showwarning("Input", "No files in list."); return

        mod = self.model_var.get()
        if not mod or "Error" in mod: tkinter.messagebox.showwarning("Error", "Invalid Model."); return
        if self.engine_var.get() == 'google' and not self.api_key: tkinter.messagebox.showwarning("Error", "No API Key."); return

        base_group_size = self.group_size_var.get()
        if self.overwrite_var.get() or not self.group_files_var.get():
             final_batch_size = 1
        else:
             final_batch_size = base_group_size

        batches = [files[i:i + final_batch_size] for i in range(0, len(files), final_batch_size)]

        safe = {}
        if self.engine_var.get() == 'google':
             if self.enable_safety_var.get():
                 safe = [
                    types.SafetySetting(category='HARM_CATEGORY_HARASSMENT', threshold=self.safety_map[self.harassment_var.get()]),
                    types.SafetySetting(category='HARM_CATEGORY_HATE_SPEECH', threshold=self.safety_map[self.hate_speech_var.get()]),
                    types.SafetySetting(category='HARM_CATEGORY_SEXUALLY_EXPLICIT', threshold=self.safety_map[self.sexually_explicit_var.get()]),
                    types.SafetySetting(category='HARM_CATEGORY_DANGEROUS_CONTENT', threshold=self.safety_map[self.dangerous_content_var.get()])
                 ]
             else:
                 safe = [
                     types.SafetySetting(category='HARM_CATEGORY_HARASSMENT', threshold='BLOCK_NONE'),
                     types.SafetySetting(category='HARM_CATEGORY_HATE_SPEECH', threshold='BLOCK_NONE'),
                     types.SafetySetting(category='HARM_CATEGORY_SEXUALLY_EXPLICIT', threshold='BLOCK_NONE'),
                     types.SafetySetting(category='HARM_CATEGORY_DANGEROUS_CONTENT', threshold='BLOCK_NONE')
                 ]

        
        # Capture current delay settings when adding jobs
        d_min = self.delay_min_var.get()
        d_sec = self.delay_sec_var.get()
        total_delay = (d_min * 60) + d_sec

        for batch in batches:
            self.job_id_counter += 1
            jid = self.job_id_counter
            job_data = {
                'job_id': jid, 'filepaths_group': batch, 
                'user_prompt': self.prompt_text.get("1.0", tk.END).strip(),
                'engine': self.engine_var.get(), 'model_name': mod, 'api_key': self.api_key,
                'output_folder': self.output_dir_var.get(), 'output_suffix': self.suffix_var.get(),
                'output_extension': self.output_ext_var.get(), 'stream_output': self.stream_var.get(),
                'safety_settings': safe, 'add_filename_to_prompt': self.add_filename_var.get(),
                'overwrite_original': self.overwrite_var.get(),
                'enable_web_search': self.ollama_search_var.get(), 
                'validate_json': self.validate_json_var.get(),
                'validate_json_keys': self.validate_keys_var.get(), # Pass new setting
                'clean_markdown': self.clean_markdown_var.get(),
                'job_delay_seconds': total_delay,
                'sequential_upload': (self.upload_mode_var.get() == 'sequential'),
                'rename_mode': self.rename_mode_var.get(),
                'result_metadata': {} # Mutable container for returning data
            }
            self.job_registry[jid] = job_data
            self.job_queue.put(job_data)
            self.tree.insert('', tk.END, iid=jid, values=(jid, generate_group_base_name(batch), 'Pending', mod))

    def requeue_failed(self):
        failed_ids = []
        for item in self.tree.get_children():
            vals = self.tree.item(item)['values']
            if vals[2] == 'Failed': failed_ids.append(vals[0])
        
        if not failed_ids: tkinter.messagebox.showinfo("Info", "No failed jobs found."); return
        count = 0
        for old_id in failed_ids:
            if old_id in self.job_registry:
                new_data = self.job_registry[old_id].copy(); self.job_id_counter += 1; new_id = self.job_id_counter; new_data['job_id'] = new_id
                self.job_registry[new_id] = new_data; self.job_queue.put(new_data)
                self.tree.insert('', tk.END, iid=new_id, values=(new_id, generate_group_base_name(new_data['filepaths_group']), 'Pending', new_data['model_name']))
                count += 1
        console_log(f"Requeued {count} jobs.", "INFO")

    def undo_rename(self):
        sel_item = self.tree.focus()
        if not sel_item: return
        job_id = int(self.tree.item(sel_item)['values'][0])
        
        if job_id not in self.job_registry: return
        job = self.job_registry[job_id]
        
        # Check result_metadata first (new way), otherwise fallback or fail
        history = job.get('result_metadata', {})
        src = history.get('rename_from')
        dst = history.get('rename_to')
        
        # Fallback for older jobs or direct keys if any (not used currently)
        if not src or not dst:
             src = job.get('rename_from') # direct
             dst = job.get('rename_to')
             
        if not src or not dst:
            tkinter.messagebox.showinfo("Undo", "This job currently cannot be undone (No rename history).")
            return
        
        if os.path.exists(dst) and not os.path.exists(src):
            try:
                os.rename(dst, src)
                self.tree.set(sel_item, 'status', 'Undone')
                console_log(f"Undid rename: {os.path.basename(dst)} -> {os.path.basename(src)}", "ACTION")
            except Exception as e:
                console_log(f"Undo failed: {e}", "ERROR")
                tkinter.messagebox.showerror("Undo Failed", str(e))
        else:
             tkinter.messagebox.showwarning("Undo", "Cannot undo: Target file missing or Source file already exists.")

    def show_context_menu(self, event):
        item_id = self.tree.identify_row(event.y)
        if item_id:
            # If the item clicked is not already selected, select it (and deselect others)
            # If it IS selected, keep the current selection (so we can act on the group)
            if item_id not in self.tree.selection():
                self.tree.selection_set(item_id)
            self.context_menu.post(event.x_root, event.y_root)

    def remove_selected_jobs(self):
        selected_items = self.tree.selection()
        if not selected_items: return

        # Ask for confirmation if any selected job is running? 
        # For simplicity, we just delete. If running, the worker check will handle it (eventually) or it finishes.
        # Ideally we shouldn't delete 'Running' jobs effortlessly, but let's allow it with the registry check.

        count = 0
        for item in selected_items:
            # The item iid is the job_id (str)
            try:
                job_id = int(item)
                if job_id in self.job_registry:
                    del self.job_registry[job_id]
                    # We cannot remove from self.job_queue easily. 
                    # The worker will pop it, see it's missing from registry, and skip.
                self.tree.delete(item)
                count += 1
            except ValueError: pass # fast mode header or something? shouldn't happen with stored IDs
        
        console_log(f"Removed {count} jobs from queue.", "ACTION")

    def retry_selected_jobs(self):
        selected_items = self.tree.selection()
        if not selected_items: return
        
        count = 0
        for item in selected_items:
            try:
                old_id = int(item)
                if old_id in self.job_registry:
                    # Create a clone
                    new_data = self.job_registry[old_id].copy()
                    self.job_id_counter += 1
                    new_id = self.job_id_counter
                    new_data['job_id'] = new_id
                    
                    self.job_registry[new_id] = new_data
                    self.job_queue.put(new_data)
                    
                    self.tree.insert('', tk.END, iid=new_id, values=(new_id, generate_group_base_name(new_data['filepaths_group']), 'Pending', new_data['model_name']))
                    count += 1
            except Exception: pass
        if count > 0:
            console_log(f"Retrying {count} selected jobs...", "ACTION")

    def copy_job_name(self):
        selected = self.tree.selection()
        if not selected: return
        # Copy the first selected item's name/group
        # Or all of them newline separated? Let's do newline separated.
        texts = []
        for item in selected:
            vals = self.tree.item(item)['values']
            if vals and len(vals) > 1:
                texts.append(str(vals[1]))
        
        if texts:
            self.clipboard_clear()
            self.clipboard_append("\n".join(texts))
            console_log(f"Copied {len(texts)} item names to clipboard.", "INFO")

    def clear_completed_jobs(self):
        # Iterate all items
        children = self.tree.get_children()
        count = 0
        for item in children:
            vals = self.tree.item(item)['values']
            status = vals[2]
            if status == 'Completed':
                job_id = int(vals[0])
                if job_id in self.job_registry: del self.job_registry[job_id]
                self.tree.delete(item)
                count += 1
        if count > 0: console_log(f"Cleared {count} completed jobs.", "INFO")

    def start_processing(self):
        if not self.job_queue.empty() and (not self.worker_thread or not self.worker_thread.is_alive()):
            self.processing_cancelled.clear(); self.processing_paused.clear()
            self.worker_thread = threading.Thread(target=self._worker, daemon=True)
            self.worker_thread.start()
            self.start_btn.config(state="disabled"); self.pause_btn.config(state="normal", text="Pause")
            self.clear_btn.config(text="Stop"); self.btn_add_sel.config(state="disabled"); self.btn_add_all.config(state="disabled")

    def toggle_pause(self):
        if self.processing_paused.is_set(): self.processing_paused.clear(); self.pause_btn.config(text="Pause")
        else: self.processing_paused.set(); self.pause_btn.config(text="Resume")

    def clear_queue(self):
        if self.worker_thread and self.worker_thread.is_alive():
            if tkinter.messagebox.askokcancel("Stop", "Cancel current processing?"):
                self.processing_cancelled.set()
        else:
            self.tree.delete(*self.tree.get_children()); 
            with self.job_queue.mutex: self.job_queue.queue.clear()
            self.job_registry.clear(); console_log("Queue cleared.", "INFO")

    def _reset_gui(self):
        self.start_btn.config(state="normal"); self.pause_btn.config(state="disabled")
        self.clear_btn.config(text="Clear"); self.btn_add_sel.config(state="normal"); self.btn_add_all.config(state="normal")

    def _check_result_queue(self):
        try:
            while not self.result_queue.empty():
                res = self.result_queue.get_nowait()
                jid, status = res['job_id'], res['status']
                if self.tree.exists(jid):
                    self.tree.set(jid, 'status', status)
                    tag = 'success' if status=='Completed' else 'fail' if status=='Failed' else 'retry' if 'Retrying' in status else 'wait' if 'Waiting' in status else ''
                    if tag: 
                        self.tree.tag_configure('success', background='#ccffcc')
                        self.tree.tag_configure('fail', background='#ffcccc')
                        self.tree.tag_configure('retry', background='#fff5cc')
                        self.tree.tag_configure('wait', background='#ffe0b2')
                    if tag: self.tree.item(jid, tags=(tag,))
        except queue.Empty: pass
        finally: self.after(100, self._check_result_queue)

    def update_tree_models(self, new_model_name):
        for child in self.tree.get_children():
            status = self.tree.set(child, 'status')
            if status in ('Pending', 'Running', 'Waiting for User...', 'Retrying'):
                self.tree.set(child, 'model', new_model_name)

    def _ask_user_for_new_model(self, current_engine, current_model, event_container):
        dialog = ModelSelectionDialog(self, current_engine, current_model, self.get_models_for_provider, self.exhausted_models)
        event_container['result'] = dialog.result
        event_container['event'].set()

    def _worker(self):
        console_log("Worker thread started.", "INFO")
        first_job = True
        while not self.job_queue.empty():
            if self.processing_cancelled.is_set(): break
            if self.processing_paused.is_set(): time.sleep(0.5); continue
            
            try: job = self.job_queue.get_nowait()
            except queue.Empty: break
            
            # --- Delay Logic ---
            delay_sec = job.get('job_delay_seconds', 0)
            if not first_job and delay_sec > 0:
                console_log(f"Waiting {delay_sec}s before next job...", "INFO")
                # Sleep in small chunks to remain responsive to pause/cancel
                elapsed = 0
                step = 0.5
                while elapsed < delay_sec:
                    if self.processing_cancelled.is_set(): break
                    if self.processing_paused.is_set(): 
                        time.sleep(0.5)
                        continue 
                    time.sleep(step)
                    elapsed += step
                if self.processing_cancelled.is_set(): break
            
            first_job = False
            # -------------------

            jid = job['job_id']
            
            # --- CHECK IF JOB WAS REMOVED FROM REGISTRY (Cancelled by User) ---
            if jid not in self.job_registry:
                # Silently skip
                continue

            self.result_queue.put({'job_id': jid, 'status': 'Running'})
            params = job.copy(); params.pop('job_id')
            
            if self.global_runtime_overrides:
                params['engine'] = self.global_runtime_overrides['engine']
                params['model_name'] = self.global_runtime_overrides['model_name']
                if params['engine'] == 'google' and not params.get('api_key'):
                    params['api_key'] = self.api_key

            attempt = 0
            while attempt < MAX_RETRIES:
                attempt += 1
                if self.processing_cancelled.is_set(): break
                try:
                    err = process_file_group(**params)
                    if not err:
                        self.result_queue.put({'job_id': jid, 'status': 'Completed'})
                        break
                    else: raise Exception(err)
                except Exception as e:
                    if isinstance(e, FatalProcessingError) or "Fatal:" in str(e):
                        console_log(f"❌ Job {jid} Failed: {e}", "ERROR")
                        self.result_queue.put({'job_id': jid, 'status': 'Failed (Blocked)'})
                        break

                    is_quota = (isinstance(e, QuotaExhaustedError) or 
                                "Quota exhausted" in str(e) or 
                                "429" in str(e) or 
                                "Open WebUI: Server Connection Error" in str(e))
                    if is_quota:
                        console_log(f"Job {jid} Quota Hit. Asking user...", "WARN")
                        self.result_queue.put({'job_id': jid, 'status': 'Waiting for User...'})
                        self.exhausted_models.add(params['model_name'])
                        event_container = {'event': threading.Event(), 'result': None}
                        self.after(0, lambda: self._ask_user_for_new_model(params['engine'], params['model_name'], event_container))
                        event_container['event'].wait() 
                        user_result = event_container['result']
                        if user_result:
                            new_engine, new_model = user_result
                            console_log(f"Switching to: {new_engine} / {new_model} (Applied to ALL remaining jobs)", "ACTION")
                            self.global_runtime_overrides = {'engine': new_engine, 'model_name': new_model}
                            params['engine'] = new_engine
                            params['model_name'] = new_model
                            if new_engine == 'google': params['api_key'] = self.api_key
                            self.after(0, lambda: self.update_tree_models(new_model))
                            self.result_queue.put({'job_id': jid, 'status': 'Running'})
                            attempt -= 1 
                            continue 
                        else:
                            console_log("User cancelled model switch. Retrying normally...", "WARN")

                    console_log(f"Job {jid} Error: {e}", "ERROR")
                    if attempt < MAX_RETRIES:
                        wait_time = 60 if is_quota else 5
                        self.result_queue.put({'job_id': jid, 'status': f"Retrying ({attempt})"})
                        time.sleep(wait_time)
                    else:
                        traceback.print_exc()
                        [copy_failed_file(fp) for fp in job['filepaths_group']]
                        self.result_queue.put({'job_id': jid, 'status': 'Failed'})
                        break
        console_log("Worker thread finished.", "INFO")
        self.after(0, self._reset_gui)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="*")
    parser.add_argument("-o", "--output", default=DEFAULT_OUTPUT_SUBFOLDER_NAME)
    parser.add_argument("-s", "--suffix", default=DEFAULT_RAW_OUTPUT_SUFFIX)
    parser.add_argument("--output-ext", default="")
    parser.add_argument("--stream", action='store_true')
    parser.add_argument("-e", "--engine", default=DEFAULT_ENGINE, choices=['google', 'ollama', 'lmstudio'])
    parser.add_argument("-m", "--model")
    parser.add_argument("--add-filename-to-prompt", action='store_true')
    args = parser.parse_args()
    
    fps = []
    if args.files:
        for p in args.files: fps.extend(glob.glob(p, recursive=True))
    else:
        console_log("No files specified. Scanning current directory for supported formats...", "INFO")
        cwd = os.getcwd()
        for ext in AUTO_LOAD_EXTENSIONS:
            found = glob.glob(os.path.join(cwd, f"**/*{ext}"), recursive=True)
            for f in found:
                if LOG_SUBFOLDER_NAME in f or FAILED_SUBFOLDER_NAME in f or os.path.basename(f) == os.path.basename(__file__):
                    continue
                fps.append(f)
    
    fps = sorted(list(set(f for f in fps if os.path.isfile(f))), key=natural_sort_key)
    if fps: console_log(f"Found {len(fps)} files.", "INFO")
    else: console_log("No supported files found in this folder.", "WARN")
    
    app = AppGUI(get_api_key(), fps, args)
    app.mainloop()

if __name__ == "__main__":
    main()