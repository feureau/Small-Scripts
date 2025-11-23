
"""
================================================================================
Multimodal AI Batch Processor (GPTBatcher) v23.1_Final
================================================================================
Updates in v23.1:
- ✅ NEW: "Ext" (Extension) input box in Output Frame to define custom file extensions.
Updates in v23.0:
- ✅ NEW: "Add Selected to Queue" button allows processing specific files.
- ✅ NEW: "Requeue Failed" button allows retrying only failed jobs.
- ✅ NEW: Automatic Retry Logic. Retries 3 times on failure with smart delays.
- ✅ NEW: Graceful Ctrl+C handling. Exits clean from terminal immediately.
- ✅ NEW: Job Registry system to persist job data for requeuing.
================================================================================
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
import threading
import queue
import signal

################################################################################
# --- Customizable Variables (Configuration) ---
################################################################################
API_KEY_ENV_VAR_NAME = "GOOGLE_API_KEY"
DEFAULT_GOOGLE_MODEL = "models/gemini-flash-latest"

OLLAMA_API_URL = os.environ.get("OLLAMA_API_URL", "http://localhost:11434")
OLLAMA_TAGS_ENDPOINT = f"{OLLAMA_API_URL}/api/tags"
OLLAMA_GENERATE_ENDPOINT = f"{OLLAMA_API_URL}/api/generate"

LMSTUDIO_API_URL = os.environ.get("LMSTUDIO_API_URL", "http://localhost:1234/v1")
LMSTUDIO_MODELS_ENDPOINT = f"{LMSTUDIO_API_URL}/models"
LMSTUDIO_CHAT_COMPLETIONS_ENDPOINT = f"{LMSTUDIO_API_URL}/chat/completions"

USER_PROMPT_TEMPLATE = """Analyze the provided content (text or image).
If text is provided below: Summarize the key points, identify main topics, and suggest relevant keywords.
If one or more images are provided: Describe the image(s) in detail. If multiple, note any relationships or differences. Suggest relevant keywords or tags.
Provide the output as plain text.
"""

SUPPORTED_TEXT_EXTENSIONS = ['.txt', '.srt', '.md', '.py', '.js', '.html', '.css', '.json', '.csv']
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
MAX_RETRIES = 3

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
        return base_names[0][0]
    else:
        return f"{base_names[0][0]}_to_{base_names[-1][0]}"

def fetch_google_models(api_key):
    if not api_key:
        return [], "API key not available."
    try:
        print("Fetching Google AI models...")
        genai.configure(api_key=api_key)
        models = [m.name for m in genai.list_models() if "generateContent" in m.supported_generation_methods]
        models.sort(key=lambda x: (0 if 'latest' in x else 1 if '2.5' in x else 2 if '2.0' in x else 3, 0 if 'pro' in x else 1 if 'flash' in x else 2, x))
        return models, None
    except PermissionDenied:
        return [], "Google API Permission Denied. Check API key permissions."
    except GoogleAPIError as e:
        return [], f"Google API Error: {e}"
    except Exception as e:
        return [], f"An unexpected error occurred: {e}"

def fetch_ollama_models():
    try:
        response = requests.get(OLLAMA_TAGS_ENDPOINT, timeout=10)
        response.raise_for_status()
        models = sorted([m.get("name") for m in response.json().get("models", []) if m.get("name")])
        return models, None
    except requests.exceptions.ConnectionError:
        return [], f"Connection Error: Is Ollama running at {OLLAMA_API_URL}?"
    except Exception as e:
        return [], f"Ollama Error: {e}"

def fetch_lmstudio_models():
    try:
        response = requests.get(LMSTUDIO_MODELS_ENDPOINT, timeout=10)
        response.raise_for_status()
        models = sorted([m.get("id") for m in response.json().get("data", []) if m.get("id")])
        return models, None
    except requests.exceptions.ConnectionError:
        return [], f"Connection Error: Is LM Studio running at {os.path.dirname(LMSTUDIO_API_URL)}?"
    except Exception as e:
        return [], f"LM Studio Error: {e}"

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
    if not text: return ""
    pattern = re.compile(r"^\s*```[a-z]*\s*\n?(.*?)\n?\s*```\s*$", re.DOTALL)
    match = pattern.match(text.strip())
    if match: return match.group(1).strip()
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
    if not api_key: return "Error: Google API Key not configured."
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name, safety_settings=safety_settings)
        if last_request_time and (time.time() - last_request_time < REQUEST_INTERVAL_SECONDS):
            sleep_duration = REQUEST_INTERVAL_SECONDS - (time.time() - last_request_time)
            time.sleep(sleep_duration)
        last_request_time = time.time()
        payload = [prompt_text]
        if images_data_list:
            for img_data in images_data_list:
                payload.append({"inline_data": {"mime_type": img_data['mime_type'], "data": img_data['bytes']}})
        
        response = model.generate_content(payload, stream=stream_output)
        if stream_output:
            return sanitize_api_response("".join(chunk.text for chunk in response))
        else:
            if not response.parts and response.prompt_feedback:
                 return f"Error: Blocked. Reason: {response.prompt_feedback.block_reason.name}"
            return sanitize_api_response(response.text)
    except ResourceExhausted:
        raise QuotaExhaustedError(f"Quota exhausted for model {model_name}")
    except Exception as e:
        raise e

def call_ollama_api(prompt_text, model_name, images_data_list=None, **kwargs):
    payload = {"model": model_name, "prompt": prompt_text, "stream": False}
    if images_data_list:
        payload["images"] = [base64.b64encode(img_data['bytes']).decode('utf-8') for img_data in images_data_list]
    response = requests.post(OLLAMA_GENERATE_ENDPOINT, json=payload, timeout=600)
    response.raise_for_status()
    data = response.json()
    if "response" in data: return sanitize_api_response(data["response"])
    return f"Error: {data.get('error', 'Unknown Ollama error')}"

def call_lmstudio_api(prompt_text, model_name, images_data_list=None, **kwargs):
    headers = {"Content-Type": "application/json"}
    message_content = [{"type": "text", "text": prompt_text}]
    if images_data_list:
        for img_data in images_data_list:
            b64 = base64.b64encode(img_data['bytes']).decode('utf-8')
            message_content.append({"type": "image_url", "image_url": {"url": f"data:{img_data['mime_type']};base64,{b64}"}})
    payload = {"model": model_name, "messages": [{"role": "user", "content": message_content}], "stream": False}
    response = requests.post(LMSTUDIO_CHAT_COMPLETIONS_ENDPOINT, headers=headers, json=payload, timeout=600)
    response.raise_for_status()
    data = response.json()
    if data.get("choices"): return sanitize_api_response(data["choices"][0]["message"]["content"])
    return f"Error: {data.get('error', 'Unknown LM Studio error')}"

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
        with open(raw_path, 'w', encoding='utf-8') as f:
            f.write(api_response or "[Empty Response]")
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write("="*20 + " Processing Log " + "="*20 + "\n")
            for k, v in log_data.items():
                if isinstance(v, datetime.datetime): v = v.strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"{k}: {v}\n")
            f.write("="*50 + "\n")
    except Exception as e:
        print(f"Error saving files: {e}")

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
    
    # Determine paths
    if overwrite_original and len(filepaths_group) == 1:
        raw_path = filepaths_group[0]
        log_dir = os.path.join(os.path.dirname(raw_path), LOG_SUBFOLDER_NAME)
        os.makedirs(log_dir, exist_ok=True)
        _, log_path = determine_unique_output_paths(base_name, kwargs['output_suffix'], log_dir, log_dir)
    else:
        out_folder = kwargs.get('output_folder') or os.path.dirname(filepaths_group[0])
        log_folder = os.path.join(out_folder, LOG_SUBFOLDER_NAME)
        os.makedirs(out_folder, exist_ok=True); os.makedirs(log_folder, exist_ok=True)
        
        # Handle output extension
        requested_ext = kwargs.get('output_extension', '').strip()
        if not requested_ext:
            ext = RAW_OUTPUT_FILE_EXTENSION
        else:
            ext = '.' + requested_ext.lstrip('.')
            
        raw_path, log_path = determine_unique_output_paths(base_name, kwargs['output_suffix'], out_folder, log_folder, ext)

    try:
        images_data, text_parts, prompt = [], [], user_prompt
        for filepath in filepaths_group:
            content, mime, is_img, err = read_file_content(filepath)
            if err: raise ValueError(err)
            if is_img: images_data.append({"bytes": content, "mime_type": mime})
            else:
                if add_filename_to_prompt: text_parts.append(f"\n--- File: {os.path.basename(filepath)} ---")
                text_parts.append(f"\n{content}\n")
        
        prompt += "".join(text_parts)
        log_data['prompt_sent'] = prompt
        
        response = call_generative_ai_api(engine, prompt, api_key, model_name, images_data_list=images_data, stream_output=kwargs['stream_output'], safety_settings=kwargs.get('safety_settings'))
        
        if response and response.startswith("Error:"): raise Exception(response)
        
        log_data.update({'status': 'Success', 'end_time': datetime.datetime.now()})
        save_output_files(response, log_data, raw_path, log_path)
        return None
    except Exception as e:
        log_data.update({'status': 'Failure', 'error': str(e), 'traceback': traceback.format_exc()})
        save_output_files(f"Error: {e}", log_data, raw_path, log_path)
        if isinstance(e, QuotaExhaustedError): raise
        return str(e)

def get_api_key(force_gui=False):
    api_key = os.environ.get(API_KEY_ENV_VAR_NAME)
    if not api_key or force_gui:
        if not force_gui: print(f"INFO: {API_KEY_ENV_VAR_NAME} not set.")
        root = tk.Tk(); root.withdraw()
        api_key = tk.simpledialog.askstring("API Key", "Enter Google API Key:", show='*')
        root.destroy()
    return api_key

class AppGUI(tk.Tk):
    def __init__(self, initial_api_key, command_line_files, args):
        super().__init__()
        self.title("Multimodal AI Batch Processor v23.1")
        self.geometry("1400x850")
        self.minsize(1000, 600)
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # Ctrl+C Handling
        signal.signal(signal.SIGINT, self._handle_sigint)
        self._check_signal() # Start heartbeat

        self.api_key = initial_api_key
        self.args = args
        self.job_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.job_registry = {} # Stores job data for requeuing
        
        self.processing_paused = threading.Event()
        self.processing_cancelled = threading.Event()
        self.worker_thread = None
        self.job_id_counter = 0

        # UI Variables
        self.files_var = tk.Variable(value=list(command_line_files or []))
        self.engine_var = tk.StringVar(value=getattr(self.args, 'engine', DEFAULT_ENGINE))
        self.model_var = tk.StringVar()
        self.output_dir_var = tk.StringVar(value=getattr(self.args, 'output', DEFAULT_OUTPUT_SUBFOLDER_NAME))
        self.suffix_var = tk.StringVar(value=getattr(self.args, 'suffix', DEFAULT_RAW_OUTPUT_SUFFIX))
        self.output_ext_var = tk.StringVar(value=getattr(self.args, 'output_ext', ''))
        self.stream_var = tk.BooleanVar(value=getattr(self.args, 'stream', False))
        self.add_filename_var = tk.BooleanVar(value=getattr(self.args, 'add_filename_to_prompt', False))
        self.group_files_var = tk.BooleanVar(value=False)
        self.group_size_var = tk.IntVar(value=3)
        self.overwrite_var = tk.BooleanVar(value=False)
        self.enable_safety_var = tk.BooleanVar(value=False)
        self.safety_map = {'Off': HarmBlockThreshold.BLOCK_NONE, 'High Only': HarmBlockThreshold.BLOCK_ONLY_HIGH, 'Med+': HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE}
        self.harassment_var = tk.StringVar(value='Off')
        self.hate_speech_var = tk.StringVar(value='Off')
        self.sexually_explicit_var = tk.StringVar(value='Off')
        self.dangerous_content_var = tk.StringVar(value='Off')

        self.create_widgets()
        self.engine_var.trace_add("write", self.update_models)
        self.after(200, self.update_models)
        self.after(100, self._check_result_queue)

    def _check_signal(self):
        # Dummy loop to allow Python to catch signals like SIGINT
        self.after(500, self._check_signal)

    def _handle_sigint(self, signum, frame):
        print("\nReceived Ctrl+C. Exiting gracefully...")
        self._on_closing()

    def create_widgets(self):
        self.columnconfigure(0, weight=1); self.rowconfigure(1, weight=1)
        
        # API Frame
        api_frame = ttk.Frame(self, padding=(10, 10, 10, 5)); api_frame.grid(row=0, column=0, sticky="ew")
        self.api_status_label = ttk.Label(api_frame, text=f"API Key: {'Set' if self.api_key else 'Not Set'}")
        self.api_status_label.pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(api_frame, text="Update Key", command=self.prompt_for_api_key).pack(side=tk.LEFT)

        # Main Panes
        outer_pane = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        outer_pane.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        inner_pane = ttk.PanedWindow(outer_pane, orient=tk.HORIZONTAL)
        outer_pane.add(inner_pane, weight=3)

        # --- Col 1: Inputs ---
        col1 = ttk.Frame(inner_pane, padding=5); inner_pane.add(col1, weight=1)
        col1.columnconfigure(0, weight=1); col1.rowconfigure(1, weight=1)
        
        f_frame = ttk.LabelFrame(col1, text="Input Files", padding=10)
        f_frame.grid(row=0, column=0, sticky="nsew", pady=(0,5))
        f_frame.columnconfigure(0, weight=1); f_frame.rowconfigure(0, weight=1)
        self.file_listbox = tk.Listbox(f_frame, listvariable=self.files_var, selectmode=tk.EXTENDED)
        self.file_listbox.grid(row=0, column=0, sticky="nsew")
        sb = ttk.Scrollbar(f_frame, orient=tk.VERTICAL, command=self.file_listbox.yview)
        sb.grid(row=0, column=1, sticky="ns"); self.file_listbox.config(yscrollcommand=sb.set)
        
        btn_f = ttk.Frame(f_frame); btn_f.grid(row=0, column=2, sticky="ns", padx=(5,0))
        ttk.Button(btn_f, text="Add...", command=self.add_files).pack(fill=tk.X)
        ttk.Button(btn_f, text="Remove", command=self.remove_files).pack(fill=tk.X, pady=2)
        ttk.Button(btn_f, text="Clear", command=self.clear_files).pack(fill=tk.X)

        p_frame = ttk.LabelFrame(col1, text="Prompt", padding=10)
        p_frame.grid(row=1, column=0, sticky="nsew")
        p_frame.columnconfigure(0, weight=1); p_frame.rowconfigure(0, weight=1)
        self.prompt_text = scrolledtext.ScrolledText(p_frame, height=8); self.prompt_text.grid(row=0,column=0,sticky="nsew")
        self.prompt_text.insert(tk.INSERT, USER_PROMPT_TEMPLATE)

        # --- Col 2: Settings ---
        col2 = ttk.Frame(inner_pane, padding=5); inner_pane.add(col2, weight=1)
        canvas = tk.Canvas(col2, highlightthickness=0); scroll = ttk.Scrollbar(col2, orient="vertical", command=canvas.yview)
        s_frame = ttk.Frame(canvas, padding=5); s_frame.columnconfigure(1, weight=1)
        s_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0,0), window=s_frame, anchor="nw"); canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True); scroll.pack(side="right", fill="y")

        # Options
        opt_f = ttk.LabelFrame(s_frame, text="AI Options", padding=10); opt_f.grid(row=0, column=0, sticky="ew", pady=(0,5))
        ttk.Label(opt_f, text="Engine:").grid(row=0, column=0, sticky=tk.W)
        ttk.Combobox(opt_f, textvariable=self.engine_var, values=['google', 'ollama', 'lmstudio'], state="readonly").grid(row=0, column=1, sticky="ew")
        ttk.Label(opt_f, text="Model:").grid(row=1, column=0, sticky=tk.W, pady=(5,0))
        self.model_combo = ttk.Combobox(opt_f, textvariable=self.model_var, state="disabled"); self.model_combo.grid(row=1, column=1, sticky="ew", pady=(5,0))
        ttk.Checkbutton(opt_f, text="Add filename to prompt", variable=self.add_filename_var).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(5,0))

        grp_f = ttk.LabelFrame(s_frame, text="Batching", padding=10); grp_f.grid(row=1, column=0, sticky="ew", pady=5)
        self.group_check = ttk.Checkbutton(grp_f, text="Group Files", variable=self.group_files_var, command=self.toggle_grouping)
        self.group_check.grid(row=0, column=0, columnspan=2, sticky=tk.W)
        ttk.Label(grp_f, text="Group Size:").grid(row=1, column=0, sticky=tk.W)
        self.group_spin = ttk.Spinbox(grp_f, from_=2, to=100, textvariable=self.group_size_var, width=5, state="disabled")
        self.group_spin.grid(row=1, column=1, sticky=tk.W)

        safe_f = ttk.LabelFrame(s_frame, text="Google Safety", padding=10); safe_f.grid(row=2, column=0, sticky="ew", pady=5)
        ttk.Checkbutton(safe_f, text="Enable Filters", variable=self.enable_safety_var, command=self.toggle_safety).grid(row=0, column=0, columnspan=2, sticky=tk.W)
        self.safety_widgets = []
        for i, (txt, var) in enumerate([("Harassment", self.harassment_var), ("Hate Speech", self.hate_speech_var), ("Sexual", self.sexually_explicit_var), ("Dangerous", self.dangerous_content_var)]):
            l = ttk.Label(safe_f, text=txt); l.grid(row=i+1, column=0, sticky=tk.W)
            c = ttk.Combobox(safe_f, textvariable=var, values=list(self.safety_map.keys()), state="disabled", width=15); c.grid(row=i+1, column=1, sticky="ew")
            self.safety_widgets.extend([l, c])

        out_f = ttk.LabelFrame(s_frame, text="Output", padding=10); out_f.grid(row=3, column=0, sticky="ew", pady=5)
        ttk.Label(out_f, text="Folder:").grid(row=0, column=0, sticky=tk.W)
        self.out_ent = ttk.Entry(out_f, textvariable=self.output_dir_var); self.out_ent.grid(row=0, column=1, sticky="ew")
        ttk.Button(out_f, text="...", width=3, command=self.browse_out).grid(row=0, column=2)
        
        ttk.Label(out_f, text="Suffix:").grid(row=1, column=0, sticky=tk.W)
        self.suf_ent = ttk.Entry(out_f, textvariable=self.suffix_var); self.suf_ent.grid(row=1, column=1, sticky="ew")
        
        ttk.Label(out_f, text="Ext:").grid(row=2, column=0, sticky=tk.W)
        self.ext_ent = ttk.Entry(out_f, textvariable=self.output_ext_var); self.ext_ent.grid(row=2, column=1, sticky="ew")

        self.over_check = ttk.Checkbutton(out_f, text="Overwrite Original", variable=self.overwrite_var, command=self.toggle_overwrite)
        self.over_check.grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=(5,0))

        # --- Col 3: Queue ---
        col3 = ttk.Frame(outer_pane, padding=5); outer_pane.add(col3, weight=2)
        col3.columnconfigure(0, weight=1); col3.rowconfigure(0, weight=1)
        
        q_frame = ttk.LabelFrame(col3, text="Job Queue", padding=10)
        q_frame.grid(row=0, column=0, sticky="nsew"); q_frame.columnconfigure(0, weight=1); q_frame.rowconfigure(0, weight=1)
        self.tree = ttk.Treeview(q_frame, columns=('id', 'name', 'status', 'model'), show='headings')
        self.tree.heading('id', text='ID'); self.tree.column('id', width=40)
        self.tree.heading('name', text='Name'); self.tree.column('name', width=200)
        self.tree.heading('status', text='Status'); self.tree.column('status', width=120)
        self.tree.heading('model', text='Model'); self.tree.column('model', width=120)
        self.tree.grid(row=0, column=0, sticky='nsew')
        sc = ttk.Scrollbar(q_frame, orient=tk.VERTICAL, command=self.tree.yview); sc.grid(row=0, column=1, sticky="ns"); self.tree.config(yscrollcommand=sc.set)

        # Buttons
        b_frame = ttk.Frame(col3, padding=(0, 10)); b_frame.grid(row=1, column=0, sticky="ew")
        b_frame.columnconfigure(0, weight=1)
        c_b_frame = ttk.Frame(b_frame); c_b_frame.grid(row=0, column=0)
        
        self.btn_add_sel = ttk.Button(c_b_frame, text="Add Selected", command=lambda: self.add_to_queue(only_selected=True))
        self.btn_add_sel.pack(side=tk.LEFT, padx=2)
        self.btn_add_all = ttk.Button(c_b_frame, text="Add All Files", command=lambda: self.add_to_queue(only_selected=False))
        self.btn_add_all.pack(side=tk.LEFT, padx=2)
        ttk.Separator(c_b_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10, fill=tk.Y)
        
        self.start_btn = ttk.Button(c_b_frame, text="START", command=self.start_processing, style="Accent.TButton")
        self.start_btn.pack(side=tk.LEFT, padx=5)
        self.pause_btn = ttk.Button(c_b_frame, text="Pause", command=self.toggle_pause, state="disabled")
        self.pause_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Separator(c_b_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10, fill=tk.Y)
        self.btn_requeue = ttk.Button(c_b_frame, text="Requeue Failed", command=self.requeue_failed)
        self.btn_requeue.pack(side=tk.LEFT, padx=2)
        self.clear_btn = ttk.Button(c_b_frame, text="Clear Queue", command=self.clear_queue)
        self.clear_btn.pack(side=tk.LEFT, padx=2)
        
        ttk.Style().configure("Accent.TButton", font=('Helvetica', 10, 'bold'))

    def _on_closing(self):
        if self.worker_thread and self.worker_thread.is_alive():
            if not self.processing_cancelled.is_set():
                 self.processing_cancelled.set()
                 # Wait briefly for thread to tidy up, but don't hang if UI is killed via Ctrl+C
                 self.worker_thread.join(timeout=1.0) 
        self.destroy()
        sys.exit(0)

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

    def prompt_for_api_key(self):
        k = get_api_key(True)
        if k: self.api_key = k; self.api_status_label.config(text="API Key: Set"); self.update_models()

    def update_models(self, *args):
        e = self.engine_var.get(); self.model_combo.set('Loading...'); self.model_combo.config(state="disabled"); self.update_idletasks()
        if e == "google": m, err = fetch_google_models(self.api_key)
        elif e == "ollama": m, err = fetch_ollama_models()
        elif e == "lmstudio": m, err = fetch_lmstudio_models()
        else: m, err = [], "Unknown"
        
        if err: self.model_combo.set(err)
        elif m:
            self.model_combo['values'] = m; self.model_combo.config(state="readonly")
            self.model_combo.set(DEFAULT_GOOGLE_MODEL if e=="google" and DEFAULT_GOOGLE_MODEL in m else m[0])
        else: self.model_combo.set("No models found")

    def add_files(self):
        f = filedialog.askopenfilenames(parent=self, filetypes=[("Supported", " ".join(f"*{e}" for e in ALL_SUPPORTED_EXTENSIONS))])
        if f:
            cur = list(self.files_var.get())
            new = [os.path.normpath(x) for x in f if os.path.normpath(x) not in cur]
            self.files_var.set(tuple(sorted(cur + new, key=natural_sort_key)))

    def remove_files(self):
        sel = self.file_listbox.curselection()
        if sel:
            l = list(self.files_var.get())
            for i in sorted(sel, reverse=True): l.pop(i)
            self.files_var.set(tuple(l))

    def clear_files(self): self.files_var.set([])
    def browse_out(self):
        d = filedialog.askdirectory(parent=self)
        if d: self.output_dir_var.set(d)

    def add_to_queue(self, only_selected=False):
        if only_selected:
            indices = self.file_listbox.curselection()
            all_files = self.files_var.get()
            files = [all_files[i] for i in indices]
            if not files: tkinter.messagebox.showwarning("Selection", "No files selected."); return
        else:
            files = list(self.files_var.get())
            if not files: tkinter.messagebox.showwarning("Input", "No files in list."); return

        mod = self.model_var.get()
        if not mod or "Error" in mod: tkinter.messagebox.showwarning("Error", "Invalid Model."); return
        if self.engine_var.get() == 'google' and not self.api_key: tkinter.messagebox.showwarning("Error", "No API Key."); return

        g_size = self.group_size_var.get() if (self.group_files_var.get() and not self.overwrite_var.get()) else 1
        safe = {}
        if self.engine_var.get() == 'google':
             if self.enable_safety_var.get():
                 safe = {HarmCategory.HARM_CATEGORY_HARASSMENT: self.safety_map[self.harassment_var.get()],
                         HarmCategory.HARM_CATEGORY_HATE_SPEECH: self.safety_map[self.hate_speech_var.get()],
                         HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: self.safety_map[self.sexually_explicit_var.get()],
                         HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: self.safety_map[self.dangerous_content_var.get()]}
             else:
                 safe = {cat: HarmBlockThreshold.BLOCK_NONE for cat in HarmCategory if cat != HarmCategory.HARM_CATEGORY_UNSPECIFIED}

        batches = [files[i:i + g_size] for i in range(0, len(files), g_size)]
        
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
                'overwrite_original': self.overwrite_var.get()
            }
            self.job_registry[jid] = job_data # Persist for requeuing
            self.job_queue.put(job_data)
            self.tree.insert('', tk.END, iid=jid, values=(jid, generate_group_base_name(batch), 'Pending', mod))

    def requeue_failed(self):
        failed_ids = []
        for item in self.tree.get_children():
            vals = self.tree.item(item)['values']
            if vals[2] == 'Failed': failed_ids.append(vals[0])
        
        if not failed_ids: tkinter.messagebox.showinfo("Info", "No failed jobs found in list."); return
        
        count = 0
        for old_id in failed_ids:
            if old_id in self.job_registry:
                # Create new job based on old data
                new_data = self.job_registry[old_id].copy()
                self.job_id_counter += 1
                new_id = self.job_id_counter
                new_data['job_id'] = new_id
                
                self.job_registry[new_id] = new_data
                self.job_queue.put(new_data)
                self.tree.insert('', tk.END, iid=new_id, values=(new_id, generate_group_base_name(new_data['filepaths_group']), 'Pending', new_data['model_name']))
                count += 1
        print(f"Requeued {count} jobs.")

    def start_processing(self):
        if not self.job_queue.empty() and (not self.worker_thread or not self.worker_thread.is_alive()):
            self.processing_cancelled.clear(); self.processing_paused.clear()
            self.worker_thread = threading.Thread(target=self._worker, daemon=True)
            self.worker_thread.start()
            self.start_btn.config(state="disabled"); self.pause_btn.config(state="normal", text="Pause")
            self.clear_btn.config(text="Stop")
            self.btn_add_sel.config(state="disabled"); self.btn_add_all.config(state="disabled")

    def toggle_pause(self):
        if self.processing_paused.is_set(): self.processing_paused.clear(); self.pause_btn.config(text="Pause")
        else: self.processing_paused.set(); self.pause_btn.config(text="Resume")

    def clear_queue(self):
        if self.worker_thread and self.worker_thread.is_alive():
            if tkinter.messagebox.askokcancel("Stop", "Cancel current processing?"):
                self.processing_cancelled.set()
        else:
            self.tree.delete(*self.tree.get_children())
            with self.job_queue.mutex: self.job_queue.queue.clear()
            self.job_registry.clear() # Clear history too? Maybe, or keep it. Clearing for now.
            print("Queue cleared.")

    def _reset_gui(self):
        self.start_btn.config(state="normal"); self.pause_btn.config(state="disabled")
        self.clear_btn.config(text="Clear Queue")
        self.btn_add_sel.config(state="normal"); self.btn_add_all.config(state="normal")

    def _check_result_queue(self):
        try:
            while not self.result_queue.empty():
                res = self.result_queue.get_nowait()
                jid, status = res['job_id'], res['status']
                if self.tree.exists(jid):
                    self.tree.set(jid, 'status', status)
                    tag = 'success' if status=='Completed' else 'fail' if status=='Failed' else 'retry' if 'Retrying' in status else ''
                    if tag: self.tree.tag_configure('success', background='#ccffcc'); self.tree.tag_configure('fail', background='#ffcccc'); self.tree.tag_configure('retry', background='#fff5cc')
                    if tag: self.tree.item(jid, tags=(tag,))
        except queue.Empty: pass
        finally: self.after(100, self._check_result_queue)

    def _worker(self):
        while not self.job_queue.empty():
            if self.processing_cancelled.is_set(): break
            if self.processing_paused.is_set(): time.sleep(0.5); continue
            
            try: job = self.job_queue.get_nowait()
            except queue.Empty: break
            
            jid = job['job_id']
            self.result_queue.put({'job_id': jid, 'status': 'Running'})
            
            params = job.copy(); params.pop('job_id')
            success = False
            
            # --- RETRY LOOP ---
            for attempt in range(1, MAX_RETRIES + 1):
                if self.processing_cancelled.is_set(): break
                try:
                    err = process_file_group(**params)
                    if not err:
                        self.result_queue.put({'job_id': jid, 'status': 'Completed'})
                        success = True
                        break
                    else:
                        raise Exception(err) # Trigger catch block
                except Exception as e:
                    is_quota = isinstance(e, QuotaExhaustedError)
                    if attempt < MAX_RETRIES:
                        wait_time = 60 if is_quota else 5
                        msg = f"Retrying ({attempt}/{MAX_RETRIES})..."
                        self.result_queue.put({'job_id': jid, 'status': msg})
                        print(f"Job {jid} failed (Attempt {attempt}). Waiting {wait_time}s. Error: {e}")
                        time.sleep(wait_time)
                    else:
                        # Final Failure
                        [copy_failed_file(fp) for fp in job['filepaths_group']]
                        self.result_queue.put({'job_id': jid, 'status': 'Failed'})
                        print(f"Job {jid} PERMANENT FAILURE: {e}")

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
        for ext in ALL_SUPPORTED_EXTENSIONS: fps.extend(glob.glob(os.path.join(os.getcwd(), f"**/*{ext}"), recursive=True))
    
    fps = sorted(list(set(f for f in fps if os.path.isfile(f) and os.path.splitext(f)[1].lower() in ALL_SUPPORTED_EXTENSIONS)), key=natural_sort_key)
    
    app = AppGUI(get_api_key(), fps, args)
    app.mainloop()

if __name__ == "__main__":
    main()
