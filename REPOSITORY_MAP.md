# 🗺️ Master Repository Map: Feureau's Small-Scripts & Configs

This document serves as the definitive functional map of the entire repository. Rather than a simple file list, it organizes the 3,200+ files into logical "Workstations" based on their actual purpose in a professional production workflow.

---

## 🎥 Workstation 1: Video Engineering & Color Pipeline
*Focus: High-fidelity encoding, AI upscaling, and professional color grading.*

### 🚀 Hardware-Accelerated Encoding (NVEncC)
*   **AI Upscaling**: Tools to upscale footage to 4K/8K using `ngx-vsr` and `nvvfx-superres`.
*   **Noise Reduction**: Specialized "NR" batches (`NR-hi`, `NR-lo`) for cleaning grainy footage.
*   **AV1 Pipeline**: Latest versions of converters focusing on the high-efficiency AV1 codec.
*   **Vertical Automation**: "Vert Cropper" scripts for converting wide footage to vertical formats.

### 🎞️ FFmpeg Batch Processing
*   **Resolution Suite (v1-v9)**: A massive library of scripts for rapid HD/4K/8K conversion.
*   **Color Space Transitions**: Specialized batches for **HDR $\rightarrow$ SDR** and **SDR $\rightarrow$ HDR**.
*   **Technical Utilities**: `Extract audio.py`, `chapter splitter.bat`, and `ffmpeg crop detect`.

### 🔮 HDR & Color Grading
*   **Metadata Injection**: `addhdr.py` and the **HDR Metajector** for injecting SMPTE ST 2086 metadata.
*   **Lut Management**: A professional library of `.cube` files and the `lutconvert.py` utility.

### 🎬 DaVinci Resolve Ecosystem
*   **Project Presets**: Camera-specific configs (Canon 6D, EOS RP) and color spaces (ACES, HDR).
*   **Timeline Templates**: `.drt` files for Assembly (24p/60p) and Binaural audio.
*   **Automation**: LUA/Python scripts for rendering by markers and YouTube chapter generation.
*   **Delivery**: XML export presets for YouTube (4K/AV1), TikTok, and ProRes.

---

## 🤖 Workstation 2: AI Intelligence & Prompt Engineering
*Focus: Maximizing LLM output and Generative AI control.*

### 🧠 The "Cognitive OS" (GPT Prompts)
A structured, multi-pass generation system for content creation:
*   **The Pipeline**: `Source Analysis` $\rightarrow$ `Fact Verification` $\rightarrow$ `Angle Selection` $\rightarrow$ `Voice Synthesis`.
*   **Viral Frameworks**: `the_mrbeast_hook_principle.md` and `superstar_viral_video_creator`.
*   **Personas**: Specialized identities like the `Benevolent Chaos Agent`.
*   **Formatting**: Non-negotiable output rules for JSON and professional prose.

### 🛠️ AI Utility Scripts
*   **Batch Processing**: `GPTBatch.py` for bulk text processing.
*   **Speech & Vision**: `kokoro.py` (TTS) and `hunyuanOCR.py` (Advanced OCR).
*   **Cleaning**: `GPTSanitize.py` for removing AI-typical linguistic patterns.

### 🌌 Generative Art (Stable Diffusion)
*   **OpenPose Bones**: A massive library (V3-V96) of skeleton images for precise ControlNet posing.
*   **Helper Tools**: `LatentCoupleHelper` for multi-subject compositions.

---

## 🖼️ Workstation 3: Image Manipulation & AI Vision
*Focus: High-precision visual cleaning and organization.*

### 🎨 ImageMagick Automation
*   **Batch Tools**: `magick jpg.bat` and `magick square.bat` for standardizing assets.
*   **Precision Cropping**: `croptransp.py` for removing transparent borders using "fuzz" logic.
*   **Specialized Crops**: `crop_object detection.py` and `cropcolorswatch.py`.

### ✂️ AI-Powered Vision
*   **Rembatcher**: A GUI wrapper for `rembg` supporting multiple models (Birefnet, ISNet, U2Net).
*   **Image Sorting**: `imagesort.py` (GUI) and `sortbydimension.py`.

---

## 📝 Workstation 4: Text, Data & Subtitle Engineering
*Focus: Converting raw data into structured, AI-ready content.*

### ✍️ Prose Structuring
*   **OSPL (One Sentence Per Line)**: `ospl.py` uses NLTK to reformat prose for AI, while preserving Markdown tables and code blocks.

### 📜 Subtitle Pipeline
*   **Conversion**: `asstosrt.py`, `srtToEDL.py`, and `srt_to_transcript.py`.
*   **Manipulation**: `merge_srt.py`, `srtrename.py`, and `one_word_srt.py` (Karaoke style).
*   **Localization**: `translatesrt.py` and `srtmultilang.py`.

### 📂 Data Wranglers
*   **Text Extraction**: `pdftotext.py`, `docxtotext.py`, and `epubtotext.py`.
*   **Organization**: `folderbydate.py` and `combine_text_files.py`.

---

## 🧊 Workstation 5: 3D, Game Dev & Configs
*Focus: Software environment backups and 3D modeling utilities.*

### 🧊 Blender Power-User Setup
*   **Environment**: Full config backups for v2.90 (with Flared Compositor) and v2.91.
*   **Modular Addons**: 
  *   **Bricks**: `bricker` and `bricksculpt` for LEGO-style modeling.
  *   **Characters**: `XNALaraMesh`, `mecafig`, and `MecaFace`.
  *   **Imports**: `io_scene_importldraw` for LDraw file integration.

### 🎮 Gaming & Hardware Mods
*   **Overwatch**: `OW cut to HDR` and specialized vertical crop batches for Shorts.
*   **Magic Lantern**: Firmware (`.FIR`) and `.mo` modules for Canon 6D RAW video.
*   **Marvel Rivals**: Competitive meta-analysis (Pick/Win rates) via `graph.py`.
*   **Game Engines**: Unity and Unreal Engine projects for Spline Path following and camera logic.

### ⌨️ System Dotfiles
*   **Editor**: `DOTemacs` configuration.
*   **Media**: `mpv.conf` and `yt-dlp` config for high-quality archiving.

---

## ⚙️ Master Prerequisites Matrix

| Station | Required Software | Key Python Libraries |
| :--- | :--- | :--- |
| **Video** | NVEncC, FFmpeg, DaVinci Resolve, MKVToolNix | `tkinterdnd2`, `ftfy` |
| **AI/Vision** | ImageMagick, Stable Diffusion | `rembg`, `openai`, `Pillow` |
| **Text** | Python 3.x | `nltk`, `chardet`, `ftfy` |
| **3D** | Blender | (Addon specific) |
| **Gaming** | Magic Lantern (Hardware) | `pandas`, `matplotlib` |

---
*Last Updated: 2026-10-02*
*Owner: Feureau*
