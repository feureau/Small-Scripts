#!/usr/bin/env python
import os
import sys
import signal
import threading

# --- Auto-activate the virtual environment ---
VENV_PATH = r"F:\AI\rembg\venv"
venv_python = os.path.join(VENV_PATH, "Scripts", "python.exe")
if not os.path.exists(venv_python):
    print(f"Error: The specified venv interpreter was not found: {venv_python}")
    sys.exit(1)
if os.path.normcase(sys.executable) != os.path.normcase(venv_python):
    print("Re-launching script using virtual environment interpreter:", venv_python)
    os.execv(venv_python, [venv_python] + sys.argv)

# --- Ensure CUDA bin is in PATH if CUDA_PATH is defined ---
if "CUDA_PATH" in os.environ:
    cuda_path = os.environ["CUDA_PATH"]
    cuda_bin = os.path.join(cuda_path, "bin")
    if not os.path.exists(cuda_bin):
        print(f"Error: CUDA bin directory not found: {cuda_bin}. Please ensure CUDA Toolkit is correctly installed.")
        sys.exit(1)
    if cuda_bin not in os.environ["PATH"]:
        os.environ["PATH"] = cuda_bin + os.pathsep + os.environ["PATH"]

# --- Automatically ensure required packages are installed ---
def ensure_packages_installed():
    import pkg_resources
    import subprocess

    required = [
        ("numpy", "==1.24.2"),
        ("onnxruntime-gpu", "==1.15.1"),
        ("rembg[gpu,cli]", "")
    ]
    for pkg, ver in required:
        spec = pkg + ver
        try:
            pkg_resources.require(spec)
        except Exception as e:
            print(f"Package {spec} not installed or incompatible: {e}")
            print(f"Attempting to install {spec} ...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", spec])
            except Exception as install_error:
                print(f"Failed to install {spec}. Please install it manually. Error: {install_error}")
                sys.exit(1)
ensure_packages_installed()

# --- Check NumPy version ---
try:
    import numpy as np
    from packaging.version import parse as parse_version
except ImportError:
    print("Error: packaging module or numpy not found.")
    sys.exit(1)
np_version = np.__version__
if parse_version(np_version) < parse_version("1.24.2") or parse_version(np_version) >= parse_version("2.0.0"):
    print("Error: Installed numpy version", np_version, "is not supported.")
    print("Please install numpy==1.24.2 (e.g., pip install numpy==1.24.2)")
    sys.exit(1)

# --- Disable Numba JIT to avoid issues with pymatting ---
os.environ["NUMBA_DISABLE_JIT"] = "1"

# --- Patch onnxruntime if necessary ---
try:
    import onnxruntime as ort
    if not hasattr(ort, "SessionOptions"):
        class DummySessionOptions:
            def __init__(self):
                pass
        ort.SessionOptions = DummySessionOptions
    if not hasattr(ort, "set_default_logger_severity"):
        def dummy_set_default_logger_severity(severity):
            pass
        ort.set_default_logger_severity = dummy_set_default_logger_severity
    if not hasattr(ort, "InferenceSession"):
        print("Error: onnxruntime does not implement InferenceSession.")
        print("Please ensure onnxruntime-gpu==1.15.1 is installed.")
        sys.exit(1)
    else:
        _orig_inference_session = ort.InferenceSession
        def my_inference_session(*args, **kwargs):
            if "providers" not in kwargs or not kwargs["providers"]:
                kwargs["providers"] = ["TensorrtExecutionProvider", "CUDAExecutionProvider", "CPUExecutionProvider"]
            return _orig_inference_session(*args, **kwargs)
        ort.InferenceSession = my_inference_session
except Exception as e:
    print("Error importing or patching onnxruntime:", e)
    sys.exit(1)

# --- Import rembg ---
try:
    from rembg import remove, new_session
except Exception as e:
    print("Error importing rembg module:", e)
    sys.exit(1)

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

class RembgGUI(tk.Tk):
    def __init__(self, files):
        super().__init__()
        self.title("Rembg Batch Processor")
        self.geometry("600x400")
        self.files = list(files)
        self.selected_model = None
        # Use a StringVar for processing mode: "GPU" or "CPU"
        self.processing_mode = tk.StringVar(value="GPU")
        self.create_widgets()

    def create_widgets(self):
        # Frame for file list
        frame = ttk.Frame(self)
        frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.listbox = tk.Listbox(frame, selectmode=tk.EXTENDED)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.config(yscrollcommand=scrollbar.set)
        for file in self.files:
            self.listbox.insert(tk.END, file)
        # File management buttons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(btn_frame, text="Add", command=self.add_files).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Remove", command=self.remove_selected).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Move Up", command=self.move_up).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Move Down", command=self.move_down).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Remove All", command=self.remove_all).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Select All", command=self.select_all).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Deselect All", command=self.deselect_all).pack(side=tk.LEFT, padx=2)
        # Model selection dropdown
        model_frame = ttk.Frame(self)
        model_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(model_frame, text="Select Model:").pack(side=tk.LEFT, padx=5)
        self.model_var = tk.StringVar()
        model_options = [
            "u2net", "u2netp", "u2net_human_seg", "u2net_cloth_seg",
            "silueta", "isnet-general-use", "isnet-anime", "sam",
            "birefnet-general", "birefnet-general-lite", "birefnet-portrait",
            "birefnet-dis", "birefnet-hrsod", "birefnet-cod", "birefnet-massive"
        ]
        self.model_var.set(model_options[0])
        self.dropdown = ttk.Combobox(model_frame, textvariable=self.model_var, values=model_options, state="readonly")
        self.dropdown.pack(side=tk.LEFT, padx=5)
        # Processing mode selection using Radiobuttons
        mode_frame = ttk.Frame(self)
        mode_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(mode_frame, text="Processing Mode:").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(mode_frame, text="GPU Processing", variable=self.processing_mode, value="GPU").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(mode_frame, text="CPU Processing", variable=self.processing_mode, value="CPU").pack(side=tk.LEFT, padx=5)
        # Processing button
        ttk.Button(self, text="Processing", command=self.on_processing).pack(pady=10)

    def add_files(self):
        new_files = filedialog.askopenfilenames(filetypes=[("Image Files", "*.jpg *.jpeg *.png")])
        for file in new_files:
            if file not in self.files:
                self.files.append(file)
                self.listbox.insert(tk.END, file)

    def remove_selected(self):
        selected = list(self.listbox.curselection())
        for index in reversed(selected):
            self.listbox.delete(index)
            del self.files[index]

    def move_up(self):
        selected = list(self.listbox.curselection())
        for i in selected:
            if i > 0:
                self.files[i-1], self.files[i] = self.files[i], self.files[i-1]
        self.refresh_listbox()
        for i in [x-1 for x in selected if x > 0]:
            self.listbox.selection_set(i)

    def move_down(self):
        selected = list(self.listbox.curselection())
        for i in reversed(selected):
            if i < len(self.files) - 1:
                self.files[i], self.files[i+1] = self.files[i+1], self.files[i]
        self.refresh_listbox()
        for i in [x+1 for x in selected if x < len(self.files) - 1]:
            self.listbox.selection_set(i)

    def remove_all(self):
        self.files = []
        self.listbox.delete(0, tk.END)

    def select_all(self):
        self.listbox.select_set(0, tk.END)

    def deselect_all(self):
        self.listbox.selection_clear(0, tk.END)

    def refresh_listbox(self):
        self.listbox.delete(0, tk.END)
        for file in self.files:
            self.listbox.insert(tk.END, file)

    def on_processing(self):
        if not self.files:
            messagebox.showwarning("No Files", "No files to process.")
            return
        self.selected_model = self.model_var.get()
        self.destroy()

def process_files(files, model, processing_mode):
    output_dir = os.path.join(os.getcwd(), "output")
    os.makedirs(output_dir, exist_ok=True)
    if processing_mode == "CPU":
        print("CPU Processing selected.")
        providers = ["CPUExecutionProvider"]
        # Remove CUDA_PATH temporarily to avoid loading CUDA libraries.
        old_cuda_path = os.environ.pop("CUDA_PATH", None)
        try:
            session = new_session(model=model, providers=providers)
        except Exception as cpu_error:
            print(f"Error creating CPU session: {cpu_error}")
            session = None
        finally:
            if old_cuda_path is not None:
                os.environ["CUDA_PATH"] = old_cuda_path
    else:
        providers = ["TensorrtExecutionProvider", "CUDAExecutionProvider", "CPUExecutionProvider"]
        try:
            session = new_session(model=model, providers=providers)
        except Exception as gpu_error:
            print(f"Error creating session with model '{model}' on GPU: {gpu_error}")
            print("Falling back to CPU-only processing.")
            old_cuda_path = os.environ.pop("CUDA_PATH", None)
            try:
                session = new_session(model=model, providers=["CPUExecutionProvider"])
            except Exception as e_cpu:
                print(f"Error creating CPU session: {e_cpu}")
                session = None
            finally:
                if old_cuda_path is not None:
                    os.environ["CUDA_PATH"] = old_cuda_path
    if session is None:
        print("No session available. Proceeding with default processing (CPU).")
    for file in files:
        try:
            with open(file, "rb") as f:
                input_data = f.read()
            if session:
                output_data = remove(input_data, session=session)
            else:
                output_data = remove(input_data)
            base_name = os.path.basename(file)
            name, _ = os.path.splitext(base_name)
            output_path = os.path.join(output_dir, f"{name}_processed.png")
            with open(output_path, "wb") as out_f:
                out_f.write(output_data)
            print(f"Processed: {file} -> {output_path}")
        except Exception as e:
            print(f"Error processing {file}: {e}")

def main():
    if len(sys.argv) < 2:
        print("Usage: rembg_gui.py <image1> <image2> ...")
        sys.exit(1)
    initial_files = sys.argv[1:]
    app = RembgGUI(initial_files)
    app.mainloop()
    if app.selected_model is None:
        print("Processing cancelled.")
        sys.exit(0)
    mode = app.processing_mode.get()
    print("Starting processing using", mode, "mode...")
    process_files(app.files, app.selected_model, mode)
    print("Processing completed.")
    sys.stdout.flush()
    sys.stderr.flush()
    # Schedule a forced exit in 1 second to kill any lingering threads.
    threading.Timer(1.0, lambda: os._exit(0)).start()
    sys.exit(0)

if __name__ == "__main__":
    main()
