## Welcome to Feureau's Small-Scripts

Here's a comprehensive README.md for your GitHub repository:


# addhdr.py - HDR Metadata Injector

A Python script for batch processing video files with HDR metadata injection and LUT embedding for professional video workflows.

## Features

- 🎥 Recursive directory scanning for video files
- 🔮 Automatic HDR metadata injection (SMPTE ST 2086)
- 🎨 Optional LUT embedding for HDR→SDR conversion
- 🚀 Bulk processing with preserved directory structure
- 🛠️ Cross-platform support (Windows/Linux/macOS)
- 📊 Detailed error reporting and progress tracking
- ⚙️ Customizable output directory and LUT path

## Installation

### Prerequisites
- Python 3.7+
- [MKVToolNix](https://mkvtoolnix.download/) (v68+ recommended)

```bash
# Clone repository
git clone https://github.com/yourusername/hdr-injector.git
cd hdr-injector

# Install requirements (no external dependencies needed)
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate  # Windows
```

## Usage

```bash
# Automatic mode: Process all videos in current directory and subdirectories
python addhdr.py

# Process single file with LUT embedding
python addhdr.py input.mkv

# Process directory and subdirectories
python addhdr.py /path/to/videos/

# Wildcard pattern matching
python addhdr.py *.mkv

# Without LUT embedding
python addhdr.py --no-lut input.mkv

# Custom output directory
python addhdr.py -o /custom/output/path input.mkv

# Custom mkvmerge path
python addhdr.py --mkvmerge-path "/usr/local/bin/mkvmerge" input.mkv
```

> ⚠️ **Note:** Always back up original files before processing

## Technical Specifications

### HDR Metadata Parameters
- Color Primaries: BT.2020
- Transfer Characteristics: ST.2084 (PQ)
- Maximum Luminance: 1000 nits
- Chromaticity Coordinates: SMPTE ST 2036-1
- White Point: D65

### Supported Formats
- Containers: MKV, MP4, AVI, MOV, WMV, TS, M2TS
- LUT Format: .cube files

### Default LUT
NBCU Technical LUT for PQ→SDR conversion (included in Resolve installations)

## Troubleshooting

**Q:** `mkvmerge not found`  
**A:** Install [MKVToolNix](https://mkvtoolnix.download/) and verify it's in your system PATH

**Q:** LUT file not found  
**A:** Use `--lut /custom/path/to/lut.cube` or disable with `--no-lut`

**Q:** Permission denied errors  
**A:** Run with elevated privileges or check file/directory permissions

**Q:** Output directory not created  
**A:** Verify valid path and write permissions on target drive


# transcribeimage.py - Transcribe Image with Google Gen AI

This Python script uses the [Google Gen AI Python SDK](https://googleapis.github.io/python-genai/) to extract and clean up text from image files. It dynamically determines the MIME type of each input file, allowing you to process any image file type (e.g., JPEG, PNG, WebP). The script also retrieves a list of available models from the API, prompts you to select one interactively, and processes the images in natural numerical order.

## Features

- **Dynamic Image Support:**  
  Automatically detects the MIME type for any image file based on its extension.

- **Interactive Model Selection:**  
  Lists available models from the API and prompts you to choose one by entering its corresponding number.

- **Natural File Sorting:**  
  Uses natural sorting to process files in human-friendly numerical order (e.g., `2.webp` comes before `10.webp`).

- **Transcription & Cleanup:**  
  Extracts text from images using OCR-like functionality, cleans up formatting (removes extra line breaks and spaces), and outputs well-structured text.

- **Output File Saving:**  
  Saves the cleaned transcription to a text file (with a `_transcription.txt` suffix) for each processed image.

## Usage

Run the script with one or more file patterns as arguments. For example:

```bash
python transcribeimage.py *.webp *.jpg *.png
```

When you run the script, it will:

1. **List Available Models:**  
   Display all models returned by the API (without extra metadata) with their index numbers.

2. **Prompt for Model Selection:**  
   Ask you to enter a number corresponding to the model you want to use.

3. **Process Files:**  
   Expand the provided file patterns using wildcards, sort the files naturally, and then process each image:
   - The script reads the image and automatically determines its MIME type.
   - It sends the image along with a prompt instructing the model to extract and clean up the text.
   - The cleaned transcription is printed to the console and saved to a file with the same base name as the image and a `_transcription.txt` suffix.

## How It Works

- **Dynamic MIME Type Detection:**  
  The script uses Python’s `mimetypes` module to guess the MIME type of each file. Only files with a MIME type that starts with `"image/"` are processed.

- **Interactive Model Selection:**  
  All available models from the API are listed. You choose the model to use by entering its index number.

- **Natural Sorting of Files:**  
  File names are sorted in natural (human-friendly) order, ensuring that files like `2.webp` are processed before `10.webp`.

- **Transcription & Cleanup:**  
  The selected model extracts the text from each image and cleans up the output, removing unnecessary line breaks and spaces.


---
# imagesort.py - Image Sorter

A simple Python GUI application for sorting images using Tkinter and Pillow. This tool allows you to preview images in a filmstrip, select images for processing, zoom and pan within the preview, and automatically organize selected files into folders based on their file extensions.

---

## Features

- **Graphical Interface:** Built with Tkinter for a responsive and intuitive user experience.
- **Image Preview:** Display images in a main preview area with support for zooming and panning.
- **Thumbnail Filmstrip:** Easily navigate through images using a horizontal filmstrip with thumbnails.
- **Selection & Processing:** Mark images for processing (selection via checkboxes) and move them into directories categorized by file extension.
- **Keyboard Shortcuts:** Quickly navigate images and control features using key bindings:
  - **Left Arrow / 's' key:** Previous image.
  - **Right Arrow / 'f' key:** Next image.
  - **'d' key:** Toggle image selection.
  - **'z' key:** Reset zoom.

---

## Prerequisites

- **Python 3.x**
- **Pillow:** Python Imaging Library fork  
  Install via pip:
  ```bash
  pip install Pillow
  ```

*Note: Tkinter is included with most standard Python distributions.*

---

## Installation

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/yourusername/imagesorter.git
   cd imagesorter
   ```

2. **Install Dependencies:**
   ```bash
   pip install Pillow
   ```

---

## Usage

1. **Prepare Your Images:**  
   Place the image files you want to sort in the same folder as the `imagesort.py` script.

2. **Run the Script:**
   ```bash
   python imagesort.py
   ```

3. **Navigate & Process:**
   - **Preview & Navigate:**  
     - Use the filmstrip to click on any thumbnail and see a larger preview.
     - Use the left/right arrow keys (or 's' and 'f') to move between images.
   - **Zoom & Pan:**  
     - Scroll the mouse wheel over the preview to zoom in or out.
     - Right-click and drag within the preview area to pan.
   - **Select & Process:**  
     - Press the 'd' key to toggle selection for the current image.
     - Click on the "Process Selected" button to move all selected images into new subdirectories (folders named after their file extension).

---

## Troubleshooting

- **Image Loading Errors:**  
  If an image fails to load (e.g., "cannot identify image file"), it will be skipped from the interface. An error message will be printed to the console.

- **Navigation Bounds:**  
  The script prevents navigation beyond the available images. If you reach the last image, the next image navigation will be disabled.

- **File Processing Issues:**  
  Ensure that the image files are not open in another application during processing. If errors occur, check the console for specific messages.

---

## Acknowledgements

- Built with [Tkinter](https://docs.python.org/3/library/tkinter.html) and [Pillow](https://python-pillow.org/).
- Inspired by the need for a simple yet effective tool for managing and organizing image files.

Enjoy sorting your images with ease!

---

# CropTransp

CropTransp is a Python script that automatically trims transparent borders from image files (such as PNGs) using ImageMagick. It supports wildcard file patterns, customizable transparency thresholds with a default of 30%, and an option to specify a custom output directory. If installed, it also displays a progress bar via `tqdm`.

---

## Features

- **Trim Transparent Borders:** Automatically crop images to remove transparent edges.
- **Customizable Transparency Threshold:** Use the `-f/--fuzz` flag to set a tolerance level (default is 30%).
- **Wildcard Support:** Accepts wildcard patterns (e.g., `*.png`) to process multiple images at once.
- **Custom Output Directory:** Specify an output folder for the processed images.
- **Progress Bar:** Displays progress if `tqdm` is installed.

---

## Prerequisites

- **Python 3:** Ensure you have Python 3 installed.
- **ImageMagick 7+:** The script requires ImageMagick v7 or later with the `magick` command available.  
  [Installation instructions](https://imagemagick.org/script/download.php)
- **tqdm (Optional):** For a progress bar, install using:
  ```bash
  pip install tqdm
  ```

---

## Installation

Clone the repository or download the script directly:

```bash
git clone https://github.com/yourusername/CropTransp.git
cd CropTransp
```

Make the script executable:

```bash
chmod +x croptransp.py
```

---

## Usage

### Basic Command

Trim transparent borders from one or more images:

```bash
./croptransp.py image1.png image2.png
```

### Options

- **`-f, --fuzz`**:  
  Set the transparency threshold as a percentage (default is `30%`).  
  Example (using a 10% threshold):
  ```bash
  ./croptransp.py -f 10 image1.png
  ```

- **`-o, --output`**:  
  Specify the output directory. Default is `TranspCrop`.
  ```bash
  ./croptransp.py -o OutputFolder *.png
  ```

- **Help:**
  ```bash
  ./croptransp.py -h
  ```

---

## How It Works

1. **File Expansion:**  
   The script expands wildcard patterns to create a list of input files.
2. **Output Directory Creation:**  
   It creates an output directory (default `TranspCrop`) in the current working directory.
3. **Image Processing:**  
   Uses ImageMagick’s `magick` command to apply the `-trim` operation along with `-fuzz` (default 30%) and `+repage` to crop transparent borders.
4. **Progress Indication:**  
   If `tqdm` is available, a progress bar is displayed during processing.

---

## Example

Process all PNG images in the current directory with a fuzz threshold of 20% and output them to a folder named `CroppedImages`:

```bash
./croptransp.py -f 20 -o CroppedImages *.png
```

---

## Troubleshooting

- **ImageMagick Warnings/Errors:**  
  Ensure you are using ImageMagick v7+ and that the `magick` command is correctly installed and in your system's PATH.
- **No Files Processed:**  
  Verify that your input file patterns correctly match your images.
- **Permission Issues:**  
  Ensure the script is executable and you have write permissions for the output directory.

---

## Acknowledgments

- [ImageMagick](https://imagemagick.org/) for their robust image processing capabilities.
- [tqdm](https://github.com/tqdm/tqdm) for the progress bar functionality.

Happy cropping!

---
# OSPL - One Sentence Per Line

## Overview
OSPL (`ospl.py`) is a Python script that processes text files to ensure that each sentence appears on a separate line. It also maintains paragraph separation and correctly handles decorative or extra text before sentences by placing them on separate lines.

## Features
- Converts input text files so that each sentence is on its own line.
- Maintains paragraph separation (double line breaks).
- Preserves extra text (such as decorative asterisks) by placing it on a separate line before the next sentence.
- Handles broken-up text lines by joining them properly before tokenization.
- Automatically downloads missing NLTK resources (`punkt_tab`) if required.
- Supports batch processing of multiple text files using wildcard patterns.
- Outputs the processed text files into an `output/` subfolder in the working directory.

## Prerequisites
- Python 3.6+
- NLTK library

### Installation
Ensure you have Python installed, then install NLTK if you haven't already:

```sh
pip install nltk
```

## Usage
Run the script from the command line, specifying one or more text files:

```sh
python ospl.py *.txt
```

### Example
#### Input (`chapter_003.txt`)
```
CHAPTER I.
Down the Rabbit-Hole
Alice was beginning to get very tired of sitting by her sister on the bank, and
of having nothing to do: once or twice she had peeped into the book her sister
was reading, but it had no pictures or conversations in it, “and what is
the use of a book,” thought Alice “without pictures or
conversations?”
```
#### Output (`output/chapter_003.txt`)
```
CHAPTER I.

Down the Rabbit-Hole

Alice was beginning to get very tired of sitting by her sister on the bank, and of having nothing to do.
Once or twice she had peeped into the book her sister was reading, but it had no pictures or conversations in it.
“And what is the use of a book,” thought Alice, “without pictures or conversations?”
```

## How It Works
1. Reads the input text file using UTF-8 encoding.
2. Splits the text into paragraphs based on blank lines.
3. Joins broken lines within paragraphs to form proper sentences.
4. Tokenizes the text into sentences using NLTK.
5. Ensures that extra text (such as decorative separators) is placed on its own line.
6. Writes the processed text into the `output/` folder.

## Handling Missing NLTK Data
If the required NLTK tokenizer is missing, the script will automatically download it and retry processing.

---

# rembg Wrapper Script (rembgwrapper.bat)

## Overview

The **rembgwrapper.bat** script is designed to wrap calls to the `rembg` tool from a virtual environment. It automatically activates the Python virtual environment, loops over image files (based on a file mask or list), calls `rembg` with the specified model option, and then deactivates the virtual environment.

It is intended to be hard‐coded with paths for your working directory and virtual environment, so you only need to modify the customizable variables at the top of the script.

## Features

- **Hardcoded Paths:**  
  Customize the virtual environment location and working directory in the script’s header.
  
- **File Mask Processing:**  
  Accepts a file mask (e.g. `*.jpg` or a single file) as the first command-line argument and applies the processing command to each file.
  
- **Model Option:**  
  The model option is provided via command-line parameters (after the file mask) and passed to `rembg`.
  
- **Virtual Environment Management:**  
  Automatically activates and then deactivates the virtual environment.

## Customizable Variables

At the top of the script, you will find variables that you can modify:

- `VENV_PATH`:  
  The absolute path to your virtual environment (e.g. `F:\AI\rembg\venv`).

- `WORK_DIR`:  
  The working directory where your source files and rembg script are located (e.g. `F:\AI\rembg`).

## Usage

1. **Place the Script:**  
   Save the batch file as `rembgwrapper.bat` in your project folder (for example, `F:\AI\rembg`).

2. **Call the Script:**  
   Open a command prompt in the working folder and run:
   ```
   rembgwrapper.bat *.jpg --model birefnet-massive
   ```
   This command will process every `.jpg` file in the directory using the `birefnet-massive` model.

3. **Processing Workflow:**
   - **Activation:**  
     The script changes to the working directory and calls the virtual environment’s `activate` script.
   - **Loop:**  
     It loops over each file matching the file mask, calls `rembg i` with the specified model, input, and output file names.
   - **Deactivation:**  
     Once processing is complete, the script calls `deactivate` to exit the virtual environment.

## Script Structure

```bat
@echo off
REM ============================
REM rembgwrapper.bat - Batch file wrapper for rembg command
REM Processes image files using rembg inside a virtual environment.
REM Usage example:
REM   rembgwrapper.bat *.jpg --model birefnet-massive
REM ============================

REM --- Configuration ---
set "VENV_PATH=F:\AI\rembg\venv"
set "WORK_DIR=F:\AI\rembg"

REM --- Change to working directory ---
cd /d "%WORK_DIR%"

REM --- Activate the virtual environment ---
call "%VENV_PATH%\Scripts\activate"

REM --- Parse arguments ---
REM The first argument is the file mask (or single file).
set "FILEMASK=%1"
shift

REM Build options variable from the remaining arguments.
set "OPTS="
:buildOptions
if "%~1"=="" goto optionsDone
   set "OPTS=%OPTS% %1"
   shift
goto buildOptions
:optionsDone

echo FILEMASK: %FILEMASK%
echo OPTS: %OPTS%
echo.

REM --- Enable delayed expansion ---
setlocal enabledelayedexpansion

REM --- Loop over each matching file ---
for %%F in (%FILEMASK%) do (
    set "INPUT=%%F"
    set "OUTPUT=%%~nF_T.png"
    echo Processing file: !INPUT!
    echo Running: rembg i !OPTS! "!INPUT!" "!OUTPUT!"
    rembg i !OPTS! "!INPUT!" "!OUTPUT!"
)

endlocal

REM --- Deactivate the virtual environment ---
call deactivate
```

## Troubleshooting

- **Unexpected Arguments:**  
  If you see errors about extra arguments, ensure that your options are placed after the file mask on the command line.

- **Virtual Environment Issues:**  
  Verify that the `VENV_PATH` is correct and that the virtual environment is set up with `rembg` installed.

- **Executable Not Found:**  
  Confirm that `rembg.exe` is available and in the expected location within your virtual environment’s Scripts folder.

---

# rembg Python GUI Script (rembatcher.py)

## Overview

The **rembatcher.py** script provides a graphical user interface (GUI) to select image files and one or more rembg models. It is intended to be run from a working folder containing your source images, and it outputs processed files into a subdirectory (customizable) within the working folder. When you press the **Process** button, the GUI closes immediately and processing begins with progress updates printed to the console.

## Features

- **GUI for File & Model Selection:**  
  A vertically arranged interface displays a list of files (populated from command-line arguments) and a list of rembg models as checkboxes.

- **Customizable Models List:**  
  The list of models is hardcoded (sorted alphabetically) at the top. You can add or remove models as needed.

- **Dynamic Window Sizing:**  
  The GUI window dynamically sizes itself to fit all widgets, including all model checkboxes (no scrollbar).

- **Output Directory:**  
  Processed images are output to a subdirectory (e.g., named `transp` by default) in the working folder.

- **Dynamic Console Updates:**  
  All processing commands and progress are printed to the console as each file is processed.

## Customizable Variables

At the very top of the script, you can modify:

- **REMBG_CMD:**  
  The full path to the `rembg` executable.  
  Example:  
  ```python
  REMBG_CMD = r"F:\AI\rembg\venv\Scripts\rembg.exe"
  ```

- **MODELS:**  
  A list of rembg models. This list is sorted automatically.  
  You can add or remove models as required.

- **OUTPUT_DIR_NAME:**  
  The name of the subdirectory where processed files are saved.  
  Example:  
  ```python
  OUTPUT_DIR_NAME = "transp"
  ```

## Usage

1. **Place the Script:**  
   Save the script as `rembatcher.py` in a central folder (for example, `F:\AI\rembg`).

2. **Run the Script:**  
   From a working folder (where your image files reside), run the script with:
   ```
   python F:\AI\rembg\rembatcher.py *.jpg
   ```
   The script uses the current working folder (from where it is run) as the location for input files and will create (or use) a subdirectory (e.g., `transp`) for the output files.

3. **Using the GUI:**  
   - **File List:**  
     The file list is pre-populated from the command-line arguments. You can also add or remove files using the buttons.
   - **Model Selection:**  
     All available models are displayed as checkboxes. Use the "Select All Models" or "Deselect All Models" buttons to toggle selection.
   - **Process:**  
     Clicking the **Process** button immediately closes the GUI and starts processing files, with progress messages printed to the console.

## Script Structure

```python
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import sys
import os
import subprocess

# -------------------------------
# Configuration - Customize these:
# -------------------------------
# Hardcoded location for the rembg executable.
REMBG_CMD = r"F:\AI\rembg\venv\Scripts\rembg.exe"

# List of rembg models (sorted alphabetically)
MODELS = [
    'birefnet-general',
    'birefnet-general-lite',
    'birefnet-portrait',
    'birefnet-dis',
    'birefnet-hrsod',
    'birefnet-cod',
    'birefnet-massive',
    'isnet-anime',
    'isnet-general-use',
    'sam',
    'silueta',
    'u2net_cloth_seg',
    'u2net_custom',
    'u2net_human_seg',
    'u2net',
    'u2netp',
    'bria-rmbg'
]
MODELS.sort()

# Name of the output subdirectory (within the working folder)
OUTPUT_DIR_NAME = "transp"

# -------------------------------
# End Configuration
# -------------------------------

def run_gui():
    # The working folder is the directory from which the script is called.
    working_dir = os.getcwd()
    selections = {"files": [], "models": []}
    
    root = tk.Tk()
    root.title("Rembatcher")
    
    # Main frame with vertical layout
    main_frame = ttk.Frame(root, padding=10)
    main_frame.pack(fill="both", expand=True)
    
    # ----- File Frame (top) -----
    file_frame = ttk.LabelFrame(main_frame, text="Files in " + working_dir)
    file_frame.pack(fill="both", expand=True, padx=5, pady=5)
    
    file_listbox = tk.Listbox(file_frame, selectmode=tk.MULTIPLE, width=60, height=10)
    file_listbox.pack(side="top", fill="both", expand=True, padx=5, pady=5)
    
    file_scrollbar = ttk.Scrollbar(file_frame, orient="vertical", command=file_listbox.yview)
    file_scrollbar.pack(side="right", fill="y")
    file_listbox.config(yscrollcommand=file_scrollbar.set)
    
    # Populate file listbox from command-line arguments
    for f in sys.argv[1:]:
        file_listbox.insert(tk.END, f)
    
    # File management buttons
    file_button_frame = ttk.Frame(file_frame)
    file_button_frame.pack(fill="x", padx=5, pady=5)
    
    def add_files():
        files = filedialog.askopenfilenames(title="Select Files", initialdir=working_dir)
        for f in files:
            file_listbox.insert(tk.END, os.path.basename(f))
    
    def remove_selected_files():
        for index in reversed(file_listbox.curselection()):
            file_listbox.delete(index)
    
    def select_all_files():
        file_listbox.select_set(0, tk.END)
    
    def deselect_all_files():
        file_listbox.select_clear(0, tk.END)
    
    def clear_files():
        file_listbox.delete(0, tk.END)
    
    ttk.Button(file_button_frame, text="Add", command=add_files).pack(side="left", padx=2)
    ttk.Button(file_button_frame, text="Remove", command=remove_selected_files).pack(side="left", padx=2)
    ttk.Button(file_button_frame, text="Select All", command=select_all_files).pack(side="left", padx=2)
    ttk.Button(file_button_frame, text="Deselect All", command=deselect_all_files).pack(side="left", padx=2)
    ttk.Button(file_button_frame, text="Clear All", command=clear_files).pack(side="left", padx=2)
    
    # ----- Model Frame (middle) -----
    model_frame = ttk.LabelFrame(main_frame, text="Models")
    model_frame.pack(fill="both", expand=True, padx=5, pady=5)
    
    # Instead of a canvas, use a frame directly for the checkbuttons.
    model_check_frame = ttk.Frame(model_frame)
    model_check_frame.pack(fill="both", expand=True, padx=5, pady=5)
    
    model_vars = {}
    for m in MODELS:
        var = tk.BooleanVar(value=False)
        chk = ttk.Checkbutton(model_check_frame, text=m, variable=var)
        chk.pack(anchor="w")
        model_vars[m] = var
    
    # Model selection buttons (below the checkbuttons)
    model_button_frame = ttk.Frame(model_frame)
    model_button_frame.pack(fill="x", padx=5, pady=5)
    
    def select_all_models():
        for var in model_vars.values():
            var.set(True)
    
    def deselect_all_models():
        for var in model_vars.values():
            var.set(False)
    
    ttk.Button(model_button_frame, text="Select All Models", command=select_all_models).pack(side="left", padx=5)
    ttk.Button(model_button_frame, text="Deselect All Models", command=deselect_all_models).pack(side="left", padx=5)
    
    # ----- Process Button (bottom) -----
    def on_process():
        selections["files"] = file_listbox.get(0, tk.END)
        selections["models"] = [model for model, var in model_vars.items() if var.get()]
        # Immediately close the GUI.
        root.destroy()
    
    process_button = ttk.Button(root, text="Process", command=on_process)
    process_button.pack(pady=10)
    
    # Dynamically size the window based on its contents.
    root.update_idletasks()
    req_width = root.winfo_reqwidth()
    req_height = root.winfo_reqheight()
    root.geometry(f"{req_width}x{req_height}")
    
    root.mainloop()
    return selections, working_dir

def main():
    selections, working_dir = run_gui()
    if not selections["files"]:
        print("No files selected for processing.")
        return
    if not selections["models"]:
        print("No models selected. Exiting.")
        return
    
    # Create output subdirectory in the working folder.
    output_dir = os.path.join(working_dir, OUTPUT_DIR_NAME)
    os.makedirs(output_dir, exist_ok=True)
    
    # Process each file with each selected model.
    for f in selections["files"]:
        input_file = os.path.join(working_dir, f)
        base, _ = os.path.splitext(os.path.basename(f))
        for model in selections["models"]:
            output_file = os.path.join(output_dir, f"{base}_{model}_T.png")
            cmd = [REMBG_CMD, "i", "--model", model, input_file, output_file]
            print(f"\nProcessing {f} with model {model}...", flush=True)
            print("Running command:", " ".join(cmd), flush=True)
            try:
                subprocess.run(cmd, check=True)
                print(f"Finished processing {f} with model {model}.", flush=True)
            except subprocess.CalledProcessError as e:
                print(f"Error processing {f} with model {model}:\n{e}", flush=True)
            except FileNotFoundError as e:
                print(f"Executable not found: {e}", flush=True)
                return
    
    print("\nAll processing complete. Processed files are in:", output_dir)

if __name__ == '__main__':
    main()
```

## Troubleshooting & Notes

- **GUI Not Fitting:**  
  The script uses `winfo_reqwidth()` and `winfo_reqheight()` to dynamically size the window. If you add many files or models, consider adjusting the design (e.g., adding scrollbars) for very large lists.

- **Processing Errors:**  
  Console messages provide feedback for each file/model combination. Check the console for error messages if a particular file fails to process.

- **Virtual Environment:**  
  Ensure the path in **REMBG_CMD** points to the correct executable (and that `rembg` is installed in that environment).

---

# ytvid.py - NVEncC Video Processing GUI Tool

[![Python](https://img.shields.io/badge/Python-3.x-blue.svg)](https://www.python.org) [![tkinter](https://img.shields.io/badge/GUI-tkinter-brightgreen.svg)](https://docs.python.org/3/library/tkinter.html) [![TkinterDnD2](https://img.shields.io/badge/Drag%20and%20Drop-TkinterDnD2-orange.svg)](https://github.com/ragardner/tkdnd)

## Description

This Python script provides a graphical user interface (GUI) for video processing, leveraging the power of [NVEncC](https://github.com/rigaya/NVEnc) (NVIDIA Encoder) for fast and efficient video encoding. The tool simplifies common video processing tasks such as:

*   **Resolution Upscaling/Downscaling:** Convert videos to Original resolution, 4K, or 8K.
*   **Upscale Algorithm Selection:** Choose between `nvvfx-superres` and `ngx-vsr` for upscaling quality.
*   **Bit Depth Conversion:** Convert videos to 8-bit color depth.
*   **HDR to SDR Conversion:**  Convert HDR (High Dynamic Range) videos to SDR (Standard Dynamic Range) for 8-bit output using a LUT (Look-Up Table).
*   **Vertical Cropping:** Apply vertical cropping for specific resolutions.
*   **QVBR Encoding:** Encode videos using QVBR (Quality Variable Bitrate) for consistent quality.
*   **FRUC (Frame Rate Up Conversion):**  Increase the frame rate of videos using NVIDIA Optical Flow FRUC.
*   **Subtitle Handling:** Burn-in subtitles into the video from embedded tracks or external SRT files.
*   **Audio and Subtitle Passthrough:** Copy audio and subtitle tracks from the input video.
*   **Logging:** Generate a log file of the encoding process for debugging and information.

This tool is designed to be user-friendly, allowing for drag-and-drop file input, intuitive option selection, and batch processing capabilities.

## Features

*   **Graphical User Interface (GUI):** Easy-to-use interface built with Tkinter.
*   **Drag and Drop Support:** Drag and drop video files directly into the application.
*   **File List Management:** Add, remove, clear, select, and reorder video files in a processing queue.
*   **Resolution Options:** Choose between Original, 4K, and 8K output resolutions.
*   **Upscale Algorithm Choice:** Select `nvvfx-superres` or `ngx-vsr (Quality 4)` for upscaling.
*   **8-bit Conversion:** Option to convert video to 8-bit color depth.
*   **HDR to SDR Conversion:**  Automatic HDR detection and optional SDR conversion with LUT application.
*   **Vertical Cropping:** Apply vertical cropping for 4K and 8K resolutions.
*   **QVBR Control:** Set the QVBR value for quality-based encoding.
*   **FRUC (Frame Rate Up Conversion):** Enable FRUC and set target FPS.
*   **Subtitle Burning:** Burn-in embedded subtitle tracks or external SRT files.
*   **Subtitle Styling:** Control subtitle alignment (Top, Middle, Bottom) and font size.
*   **Embedded Subtitle Extraction:** Detect and load embedded subtitle tracks from video files.
*   **External SRT Subtitle Support:** Add and burn-in external SRT subtitle files.
*   **Audio and Subtitle Copying:** Automatically copies audio and subtitle tracks from the input.
*   **Logging:** Option to generate a detailed log file of the encoding process.
*   **Batch Processing:** Process multiple video files in a queue.
*   **Cross-Platform Compatibility (with Dependencies):**  While NVEncC is Windows-specific, the Python script itself can potentially run on other platforms if NVEncC and required dependencies are available (primarily designed for Windows).

## Dependencies

This script relies on the following software and Python libraries:

### External Tools (Must be in your system's PATH environment variable):

*   **[NVEncC64](https://github.com/rigaya/NVEnc):**  The core NVIDIA encoder. You need to download and install NVEncC64. Make sure the directory containing `NVEncC64.exe` is added to your system's `PATH` environment variable.
*   **[ffmpeg](https://ffmpeg.org/):**  Used for video and subtitle processing (probing, extraction, format conversion). Ensure `ffmpeg.exe` and `ffprobe.exe` are in your `PATH`.
*   **[mkvmerge](https://mkvtoolnix.download/):** (Optional, but recommended for HDR tagging) Used for applying HDR metadata to MKV output files. Ensure `mkvmerge.exe` is in your `PATH`.
*   **[NVIDIA Maxine Video Effects SDK and Models](https://developer.nvidia.com/maxine-vfx-sdk):** (Optional, required for `nvvfx-superres` and `ngx-vsr` upscale algorithms) Download and install the SDK and models. You may need to set the model directory using the `--vpp-nvvfx-model-dir` NVEncC option if it's not automatically detected (this script currently doesn't expose this option in the GUI, but it's good to be aware of if you encounter issues).

### Python Libraries (Install using `pip install`):

*   **tkinter:** (Standard Python library) For the GUI. Usually comes pre-installed with Python.
*   **tkinterdnd2:** For drag and drop functionality. Install using: `pip install tkinterdnd2`
*   **ftfy:** For fixing text encoding issues, especially in subtitles. Install using: `pip install ftfy`

You can install the Python libraries using pip:

```bash
pip install tkinterdnd2 ftfy
```

### Optional NPP Libraries (for `--vpp-gauss` and `npp` based resize algorithms in NVEncC - not directly used in the current script's GUI options but mentioned in the NVEncC documentation):

*   **NPP (NVIDIA Performance Primitives) DLLs:**  `nppc64_10.dll`, `nppif64_10.dll`, `nppig64_10.dll`. These are required if you intend to use the `--vpp-gauss` filter or NPP-based resize algorithms directly with NVEncC command line (not exposed in the current GUI). You can download these DLLs from [NVEnc Releases](https://github.com/rigaya/NVEnc/releases) (look for `npp64_10_dll_7zip.7z`). Place these DLLs in the same directory as `NVEncC64.exe`.

## Installation

1.  **Install Python:** Ensure you have Python 3.x installed on your system. You can download it from [python.org](https://www.python.org).
2.  **Install Dependencies:** Install the required Python libraries using `pip install tkinterdnd2 ftfy`.
3.  **Install External Tools:** Download and install NVEncC64, ffmpeg, and mkvmerge (if desired for HDR tagging) and ensure their executable directories are added to your system's `PATH` environment variable.
4.  **Download the Script:** Download the Python script (`your_script_name.py`) from this repository.
5.  **(Optional) Install NVIDIA Maxine Video Effects SDK and Models:** If you plan to use the `nvvfx-superres` or `ngx-vsr` upscale algorithms, install the NVIDIA Maxine Video Effects SDK and Models.

## Usage

1.  **Run the Script:** Execute the Python script (`your_script_name.py`). This will open the Video Processing Tool GUI.

2.  **Add Video Files:**
    *   **Drag and Drop:** Drag and drop video files directly into the file listbox area in the GUI.
    *   **Add Files Button:** Click the "Add Files" button to open a file dialog and select video files to add to the list.

3.  **File List Management:**
    *   **Select Files:** Select one or more files in the listbox to apply options to them. Use `Ctrl+Click` or `Shift+Click` for multiple selections.
    *   **Select All:** Click "Select All" to select all files in the list.
    *   **Remove Selected:** Click "Remove Selected" to remove the highlighted files from the list.
    *   **Clear All:** Click "Clear All" to remove all files from the list.
    *   **Move Up/Down:** Select files and use "Move Up" or "Move Down" to reorder the processing queue.

4.  **Configure Encoding Options:**
    *   **Resolution and Upscale Algorithm (LabelFrame "Resolution and Upscale Algorithm"):**
        *   **Resolution:** Choose the output resolution:
            *   **Original:**  Keeps the input resolution.
            *   **4k:** Upscales or downscales to 4K resolution (2160x2160, maintaining aspect ratio).
            *   **8k:** Upscales or downscales to 8K resolution (4320x4320, maintaining aspect ratio).
        *   **Upscale Algorithm:** (Available when 4K or 8K resolution is selected) Choose the upscaling algorithm:
            *   **nvvfx-superres:** Uses NVIDIA's `nvvfx-superres` for AI-powered super-resolution upscaling (requires NVIDIA Maxine SDK). Generally offers good quality and detail preservation.
            *   **ngx-vsr (Quality 4):** Uses NVIDIA's VSR (Video Super Resolution) with quality level 4 (highest quality). Requires Turing GPUs or later and recent drivers. May be slower but can provide excellent results.

    *   **Convert to 8 bit:** Check this box to convert the output video to 8-bit color depth. If unchecked, the output will be 10-bit (if supported by the input and encoder).

    *   **Convert to HDR:** Check this box to tag the output video as HDR (High Dynamic Range). **Note:** For 8-bit output, this option will trigger HDR to SDR conversion using a LUT. For 10-bit output, it will apply HDR metadata tagging using `mkvmerge` (if installed).

    *   **Vertical Crop:** Check this box to apply vertical cropping. This is automatically applied for 4K and 8K resolutions if the input video width is large enough (>= 3840 for 4K, >= 7680 for 8K) to remove black bars.

    *   **QVBR Value:** Enter the desired QVBR (Quality Variable Bitrate) value (0-51, 0 for automatic). Lower values generally mean higher quality and larger file sizes.

    *   **Enable FRUC:** Check this box to enable Frame Rate Up Conversion (FRUC).

    *   **FRUC FPS Target:** (Enabled when "Enable FRUC" is checked) Enter the target FPS for FRUC. Common values are 60 or higher for smoother motion.

    *   **Subtitle Alignment:** Choose the alignment for burned-in subtitles: Top, Middle, or Bottom.

    *   **Subtitle Font Size:** Enter the desired font size for burned-in subtitles.

    *   **Generate Log File:** Check this box to create a `log.log` file in the same directory as the script, containing detailed encoding information.

5.  **Burn Subtitle Tracks (LabelFrame "Burn Subtitle Tracks"):**
    *   **Load Embedded SRT (All Files):** Click this button to detect and load embedded subtitle tracks from all video files in the list.
    *   **Add External SRT (Current File):** Select a file in the listbox and click this button to add external SRT subtitle files to the selected video.
    *   **Remove Selected SRT (Current File):** Select a file and then select subtitle tracks in the subtitle list below. Click this button to remove the selected external SRT subtitles from the current file.
    *   **Subtitle Track List:** Check the checkboxes next to subtitle tracks to select them for burning into the output video. Only one embedded subtitle track can be selected per file at a time.

6.  **Start Processing:** Once you have configured all options, click the "Start Processing" button in the bottom frame. The script will begin processing the files in the list according to your settings.

7.  **Output Files:** Output files will be created in subdirectories named "original", "4k", or "8k" within the same directory as the input video files, based on the selected resolution. File names will include suffixes indicating resolution, bit depth (e.g., `_8bit`), and subtitle track information if subtitles are burned in.

## NVEncC Options

This GUI tool utilizes [NVEncC](https://github.com/rigaya/NVEnc) for encoding and exposes a subset of its options through the interface. For advanced users who want to explore the full range of NVEncC's capabilities and command-line options, please refer to the [NVEncC Option List Documentation](link-to-NVEncC-documentation-if-available, or mention searching for "NVEncC Options" online).

## Limitations and Known Issues

*   **Windows-Centric:** While the Python script itself might be cross-platform, NVEncC and some of its features (like `ngx-vsr`, NVIDIA Maxine SDK integration) are primarily designed for and tested on Windows.
*   **NVIDIA GPU Required:** Hardware encoding and the upscale algorithms (`nvvfx-superres`, `ngx-vsr`) rely on NVIDIA GPUs. The script will not function as intended without a compatible NVIDIA graphics card.
*   **Dependency on External Tools:**  The script depends on correctly installed and configured external tools (NVEncC, ffmpeg, mkvmerge) being in the system `PATH`.
*   **Basic Error Handling:** While some error handling is implemented, more robust error reporting and user feedback could be added in future versions.
*   **Limited Option Exposure:** The GUI does not expose all NVEncC options. Advanced users may need to use NVEncC directly via the command line for more fine-grained control.

# magickjpg.py - PNG to JPG Converter Script with ImageMagick

This Python script converts PNG images to JPG format in the current working directory using ImageMagick. It's designed to be run from the command line and offers various options to control the JPG conversion process, such as quality, sampling factor, and more.  Newly generated JPG files are automatically moved into a `jpg` subfolder.

## Features

*   **PNG to JPG Conversion:** Converts all PNG images (or images matching a specified pattern) in the current directory to JPG format.
*   **ImageMagick Powered:** Leverages the powerful ImageMagick command-line tools for image processing.
*   **JPG Conversion Options:** Provides command-line arguments to control:
    *   **Quality (`-q` or `--quality`):**  Adjust JPG quality for file size vs. image quality trade-off.
    *   **Sampling Factor (`--sampling-factor`):**  Control chroma subsampling for color detail vs. file size.
    *   **Density (`--density`):** Set DPI resolution for the output JPG images.
    *   **Interlace Mode (`--interlace`):** Create progressive (interlaced) or baseline JPGs.
    *   **Metadata Stripping (`--strip`):** Remove metadata to reduce file size.
    *   **ICC Profile Embedding (`--profile`):** Embed a specific ICC color profile.
    *   **Resizing (`--resize`):** Resize images before conversion using ImageMagick geometry strings.
*   **Output to `jpg` Folder:**  Automatically creates a `jpg` subfolder and moves the newly created JPG files into it, keeping your original directory organized.
*   **Help Text:** Includes `-h` or `--help` flag to display usage instructions and available options.
*   **Cross-Platform (Windows Compatible):** Designed to run correctly on Windows command prompt.

## Prerequisites

Before running this script, you need to have the following software installed and properly configured:

1.  **Python:** Python 3.x must be installed on your system. You can download it from [https://www.python.org/](https://www.python.org/).
2.  **ImageMagick:** ImageMagick must be installed and the `magick` command-line tool must be accessible in your system's PATH environment variable. You can download ImageMagick from [https://imagemagick.org/](https://imagemagick.org/).  Make sure to install a version that includes the `magick` command (the newer unified command-line interface).

## Installation

1.  **Download the Script:** Download the Python script (`process_images.py` or `magickjpg.py`) to your desired location.
2.  **Make it Executable (Optional on some systems):** On some systems, you might need to make the script executable using `chmod +x process_images.py` (on Linux/macOS). On Windows, this is generally not necessary.

## Usage

1.  **Open Command Prompt/Terminal:** Open your command prompt (on Windows) or terminal (on macOS/Linux).
2.  **Navigate to the Directory with PNGs:** Use the `cd` command to navigate to the directory where your PNG images are located. This directory will be the **current working directory** for the script.
3.  **Run the Script:** Execute the script using the `python` interpreter, providing the input file pattern as the first argument, followed by any desired options.

    ```bash
    python path/to/magickjpg.py <input_pattern> [options]
    ```

    *   `path/to/magickjpg.py`:  Replace this with the actual path to where you saved the script if you are not running it from the same directory. If the script is in your current directory, you can just use `magickjpg.py` (or `python magickjpg.py` on Windows).
    *   `<input_pattern>`:  This is **required** and specifies the file pattern to match for conversion. Common patterns are:
        *   `*.png`: To convert all PNG files.
        *   `*.tif`: To convert all TIFF files.
        *   `image*.png`: To convert PNG files starting with "image".
        *   `single_image.bmp`: To convert a specific file named "single_image.bmp".
    *   `[options]`:  These are optional flags to control the JPG conversion process. See the "Command-Line Arguments" section below for available options.

## Command-Line Arguments

| Argument/Option          | Short Flag | Type    | Description                                                                                                                                                              |
| ------------------------ | ---------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `<input_pattern>`       | (positional) | String  | **Required.** Specifies the file pattern to match for image conversion (e.g., `*.png`, `image*.tif`).                                                                 |
| `-q` / `--quality`       | `-q`       | Integer | JPEG quality level (0-100, higher is better quality, larger file size). Default is ImageMagick's default quality.                                                     |
| `--sampling-factor`      |            | String  | JPEG chroma sampling factor (e.g., `'4:2:0'`, `'4:4:4'`). Controls color detail vs. file size.                                                                        |
| `--density`            |            | Integer | DPI density for the output JPEG images.                                                                                                                                  |
| `--interlace`          |            | String  | JPEG interlace mode. Choices: `'None'`, `'Plane'`, `'Line'`, `'Partition'`. Use `'Plane'` for progressive JPEGs (recommended for web).                               |
| `--strip`              |            | Flag    | Strip metadata (EXIF, IPTC, etc.) from JPEG images to reduce file size.                                                                                                  |
| `--profile`            |            | String  | Path to an ICC profile file to embed in the JPEG images.  Example: `"path/to/sRGB.icc"`.                                                                                   |
| `--resize`             |            | String  | ImageMagick geometry string for resizing images before conversion. Examples: `'50%'`, `'800x600'`, `'800x>'`. Refer to ImageMagick documentation for geometry syntax. |
| `-h` / `--help`          | `-h`       | Flag    | Display help message and exit.                                                                                                                                           |

## Output

The script will create a subfolder named `jpg` in the current working directory (if it doesn't already exist). All newly generated JPG files will be moved into this `jpg` folder.

## Example Usage

1.  **Convert all PNG files in the current directory to JPG with default settings:**

    ```bash
    python magickjpg.py *.png
    ```

2.  **Convert all PNG files to JPG with a quality level of 85:**

    ```bash
    python magickjpg.py *.png -q 85
    ```

3.  **Convert all PNG files, set quality to 90, use 4:2:0 sampling factor, and create progressive JPGs:**

    ```bash
    python magickjpg.py *.png -q 90 --sampling-factor 4:2:0 --interlace Plane
    ```

4.  **Convert all PNG files, resize them to 50% of their original size, and strip metadata:**

    ```bash
    python magickjpg.py *.png --resize 50% --strip
    ```

5.  **Get help information to see all available options:**

    ```bash
    python magickjpg.py -h
    ```
    or
    ```bash
    python magickjpg.py --help
    ```



---

## Contributing

Contributions to this project are welcome! If you find bugs, have feature requests, or want to contribute code improvements, please feel free to:

*   **Report Issues:**  Open issues on the GitHub repository to report bugs or suggest enhancements.
*   **Submit Pull Requests:**  Fork the repository, make your changes, and submit pull requests with your contributions.

# Contact/Support

For questions or support, pray to the AI god. Good luck.

**Disclaimer:** This tool is provided as-is, without warranty. Please use it responsibly and at your own risk. Always verify your output files.

# License

This project is open-source and available under the GNU General Public License version 3 (GPLv3) license.
