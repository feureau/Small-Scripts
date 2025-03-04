## Welcome to GitHub Pages

You can use the [editor on GitHub](https://github.com/feureau/Small-Scripts/edit/master/README.md) to maintain and preview the content for your website in Markdown files.

Whenever you commit to this repository, GitHub Pages will run [Jekyll](https://jekyllrb.com/) to rebuild the pages in your site, from the content in your Markdown files.

### Markdown

Markdown is a lightweight and easy-to-use syntax for styling your writing. It includes conventions for

```markdown
Syntax highlighted code block

# Header 1
## Header 2
### Header 3

- Bulleted
- List

1. Numbered
2. List

**Bold** and _Italic_ and `Code` text

[Link](url) and ![Image](src)
```

For more details see [GitHub Flavored Markdown](https://guides.github.com/features/mastering-markdown/).

### Jekyll Themes

Your Pages site will use the layout and styles from the Jekyll theme you have selected in your [repository settings](https://github.com/feureau/Small-Scripts/settings). The name of this theme is saved in the Jekyll `_config.yml` configuration file.

### Support or Contact

Having trouble with Pages? Check out our [documentation](https://help.github.com/categories/github-pages-basics/) or [contact support](https://github.com/contact) and we’ll help you sort it out.

# rembg_gui

**rembg_gui** is a Python-based GUI batch processing tool for [rembg](https://github.com/danielgatis/rembg), which removes image backgrounds using deep learning. It features automatic virtual environment activation, dynamic dependency installation, and a user-friendly interface that allows you to switch between GPU and CPU processing modes.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Requirements](#requirements)
- [Installation and Setup](#installation-and-setup)
  - [Folder Structure](#folder-structure)
  - [Creating and Configuring the Virtual Environment](#creating-and-configuring-the-virtual-environment)
  - [Installing CUDA (for GPU processing)](#installing-cuda-for-gpu-processing)
- [Usage](#usage)
  - [Running the Script](#running-the-script)
  - [Using the GUI](#using-the-gui)
- [Processing Modes](#processing-modes)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

**rembg_gui** provides an easy-to-use graphical user interface built with Tkinter that allows you to:

- **Batch Process Images:** Easily add, remove, and reorder image files for processing.
- **Select Processing Model:** Choose from various pre-trained rembg models (e.g., `u2net`, `u2netp`, `isnet-general-use`, etc.).
- **Switch Between GPU and CPU:** Select the desired processing mode via mutually exclusive options.
- **Automatic Dependency Management:** The script automatically checks for and installs required Python packages.
- **Automatic Virtual Environment Activation:** The script re‑launches itself using a dedicated virtual environment for consistency.
- **Graceful Exit:** The tool attempts to force termination when processing is complete so that no lingering threads remain.

---

## Features

- **GUI Interface:** Manage image files with options to add, remove, reorder, select, and deselect.
- **Model Selection:** Choose the appropriate rembg model for your use case.
- **Processing Mode Switch:** Use Radiobuttons to select GPU processing (default) or CPU processing.
- **Auto Dependency Installation:** Checks and installs `numpy==1.24.2`, `onnxruntime-gpu==1.15.1`, and `rembg[gpu,cli]` automatically.
- **Automatic venv Activation:** Re‑launches using a dedicated virtual environment.
- **CUDA Integration:** Supports GPU acceleration if your system meets the CUDA requirements.
- **Fallback to CPU:** If GPU initialization fails or if CPU-only processing is forced, the script automatically falls back to CPU mode.
- **Forced Exit:** Attempts to terminate any lingering threads after processing completes.

---

## Requirements

- **Operating System:** Windows (other OS support may require adjustments)
- **Python Version:** Python 3.10 or higher (tested with Python 3.11)
- **Virtual Environment:** The script assumes a dedicated venv is set up in the project folder.
- **Dependencies:**
  - `numpy==1.24.2`
  - `onnxruntime-gpu==1.15.1`
  - `rembg[gpu,cli]`
- **For GPU Processing:**
  - **CUDA Toolkit 11.8:** Must be installed.
  - **cuDNN:** Matching version for CUDA 11.8.
  - **Environment Variable:** `CUDA_PATH` should point to your CUDA installation root (e.g. `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8`).

---

## Installation and Setup

### Folder Structure

Your project folder should be organized as follows:

```
F:\AI\rembg\
  ├── rembg_gui.py
  └── venv\         # Your dedicated virtual environment
```

### Creating and Configuring the Virtual Environment

1. **Navigate to your project folder:**

   ```batch
   cd /d F:\AI\rembg
   ```

2. **Create the Virtual Environment:**

   ```batch
   python -m venv venv
   ```

3. **Activate the Virtual Environment:**

   - **Command Prompt:**

     ```batch
     venv\Scripts\activate
     ```

   - **PowerShell:**

     ```powershell
     .\venv\Scripts\Activate.ps1
     ```

4. **Install Required Packages:**

   The script will automatically check and install:
   
   ```batch
   pip install numpy==1.24.2 onnxruntime-gpu==1.15.1 "rembg[gpu,cli]"
   ```

   However, you can also run the above command manually to ensure dependencies are met.

### Installing CUDA (for GPU processing)

For GPU acceleration, ensure you have:

1. **CUDA Toolkit 11.8:**  
   Download from [NVIDIA CUDA Toolkit 11.8 Archive](https://developer.nvidia.com/cuda-11-8-0-download-archive).

2. **cuDNN for CUDA 11.8:**  
   Download the matching version from [NVIDIA cuDNN](https://developer.nvidia.com/cudnn).

3. **Environment Variable:**  
   Set `CUDA_PATH` to your CUDA 11.8 installation directory, e.g.:

   ```batch
   setx CUDA_PATH "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8"
   ```

   Also, ensure that the CUDA bin folder (e.g., `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8\bin`) is added to your system PATH.

---

## Usage

### Running the Script

Once your virtual environment is set up and dependencies are installed, you can run the script without manually activating the venv:

```batch
F:\AI\rembg\rembg_gui.py image1.jpg image2.png
```

The script will automatically re-launch itself using the venv interpreter.

### Using the GUI

- **File List:**  
  The main window displays the list of image files passed as command-line arguments. You can add more images using the **Add** button.

- **File Management:**  
  Options to **Remove**, **Move Up**, **Move Down**, **Remove All**, **Select All**, and **Deselect All** help you manage the list order.

- **Model Selection:**  
  Use the dropdown menu to select one of the available rembg models.

- **Processing Mode:**  
  Two Radiobuttons let you choose:
  - **GPU Processing** (default)
  - **CPU Processing**

  The selected mode determines whether the script attempts to use GPU acceleration or forces CPU-only processing.

- **Processing:**  
  Click the **Processing** button to start. The script will process the images and save the output to an `output` folder (created in the current directory).

- **Termination:**  
  After processing completes, the script is designed to automatically terminate.

---

## Processing Modes

- **GPU Processing:**  
  The script attempts to create an onnxruntime session with GPU providers (including TensorRT, CUDA, and CPU).  
  **Note:** If CUDA or cuDNN is not correctly installed, the session creation will fail, and the script will fall back to CPU processing.

- **CPU Processing:**  
  When selected, the script forces CPU-only processing by temporarily removing the `CUDA_PATH` variable to avoid attempting to load GPU libraries.

---

## Troubleshooting

- **CUDA Errors:**  
  If you see errors related to `CUDA_PATH` or DLL loading failures, ensure:
  - CUDA Toolkit 11.8 and the matching cuDNN are installed.
  - `CUDA_PATH` is correctly set to your CUDA 11.8 installation.
  - The CUDA bin directory is in your system PATH.

- **Dependency Issues:**  
  The script automatically checks for and installs required packages. If automatic installation fails, manually install the required packages using pip.

- **Virtual Environment:**  
  The script auto‑activates the venv located at `F:\AI\rembg\venv`. Ensure the venv exists and contains the correct packages.

- **Script Not Exiting:**  
  If the script does not exit automatically after processing, it uses a timer and forced exit (using `os._exit(0)`). If you still need to press Ctrl‑C, check for any lingering processes or threads that might be preventing termination.

---

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any improvements or bug fixes. When contributing, please follow the standard guidelines for Python code and include tests if applicable.

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- [rembg](https://github.com/danielgatis/rembg) – The background removal tool this script is based on.
- [onnxruntime](https://github.com/microsoft/onnxruntime) – For GPU and CPU acceleration.
- Thanks to all contributors who have helped improve the rembg ecosystem.

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

## Contributing

Contributions to this project are welcome! If you find bugs, have feature requests, or want to contribute code improvements, please feel free to:

*   **Report Issues:**  Open issues on the GitHub repository to report bugs or suggest enhancements.
*   **Submit Pull Requests:**  Fork the repository, make your changes, and submit pull requests with your contributions.

## License

This project is open-source and available under the GNU General Public License version 3 (GPLv3) license.

## Contact/Support

For questions or support, pray to the AI god. Good luck.

---

**Disclaimer:** This tool is provided as-is, without warranty. Please use it responsibly and at your own risk. Always verify your output files.

```


