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

Feel free to customize this README further to suit your project needs!