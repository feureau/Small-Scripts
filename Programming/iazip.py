
#!/usr/bin/env python3

r"""
# IA Archive Utility (iazip)

> [!IMPORTANT]
> **Maintenance Requirement**: This documentation block must be updated and included in full after every functional or logic change to the script to ensure the internal README remains synchronized with the implementation.

A specialized archiving tool designed to package image sets, media, text, and other data for the **Internet Archive (IA)**.
It automates the grouping and compression of files into specific archive formats compatible with IA's automated derivation engine.

## 🚀 Features

-   **Automatic Grouping**: Detects file sequences (e.g., `Scan_001.jpg`, `Scan_002.jpg`) and groups them by prefix.
-   **IA Compatibility**: Creates `_images.zip` for pictures, `_{ext}_media.zip` for media, `_{ext}_text.zip` for documents, and `_{ext}_data.zip` for all other formats to trigger IA's automated processing correctly.
-   **Media Support**: Automatically identifies audio and video files.
-   **Comprehensive Processing**: Includes a catch-all mode to package unknown extensions, binaries, and archives.
-   **Selective Processing**: Process only specific file types using flags (text, media, images, other).
-   **Flexible Post-Archival Handling**:
    -   **Delete (Default)**: Reclaims storage by removing originals after zipping.
    -   **Move (`-m`)**: Relocates originals to a safe `_original` sibling folder.
    -   **Keep (`-k`)**: Leaves files exactly where they are.
-   **Safe Execution**: Only modifies/removes files *after* verifying the archive has been successfully written to disk. Ignores previously generated `.zip` files.

## 🛠 Usage

Run the script within the directory you wish to process:

```powershell
python iazip.py [OPTIONS]
```

### Options

| Flag | Long Flag | Description |
| :--- | :--- | :--- |
| `-m` | `--move` | Move originals to an external sibling folder suffixed with `_original`. |
| `-k` | `--keep` | Keep original files in their current location. |
| `-t` | `--text` | Process only text files. |
| `-M` | `--media` | Process only media files. |
| `-i` | `--images` | Process only image files. |
| `-o` | `--other` | Process other/unclassified files (e.g., binaries, archives). |
| `-h` | `--help` | Show the help message and exit. |

> Note: If no type flags (-t, -M, -i, -o) are specified, all file types will be processed by default.

## 📖 Examples

**1. Standard Archive (Delete Originals)**
Archives all file types and deletes the source files.
```powershell
python iazip.py
```

**2. Preservation Mode (Move Originals)**
Archives files and moves the sources into a folder named `current_folder_original`.
```powershell
python iazip.py -m
```

**3. Preview/Safety Mode (Keep Originals)**
Creates archives but leaves all source files untouched.
```powershell
python iazip.py -k
```

**4. Process Only Specific Classifications**
Creates only `_text.zip` and `_images.zip` archives, leaving media and other files alone.
```powershell
python iazip.py -t -i
```

**5. Process Only Unclassified / Data Files**
Creates only `_data.zip` archives.
```powershell
python iazip.py -o
```

## 🧠 How it Works

1.  **Prefix Derivation**: The tool analyzes filenames to find a shared "prefix" (e.g., `page_001` -> `page`).
2.  **File Classification**:
    -   **Images**: `.jpg`, `.png`, `.tif`, etc. -> `_images.zip`
    -   **Media**: `.mp4`, `.mp3`, `.wav`, etc. -> `_{ext}_media.zip`
    -   **Text**: Plaintext files with numeric naming -> `_{ext}_text.zip`
    -   **Data/Other**: Everything else (binaries, unknown extensions) -> `_{ext}_data.zip`
3.  **Compression**: Uses ZIP stored mode by default for faster archiving with no recompression.
"""

import os
import shutil
import zipfile
import re
import sys
import argparse


def _is_likely_plaintext_file(filepath):
    """
    HEURISTIC PLAINTEXT DETECTOR

    WHAT: Determines if a file is a human-readable text file versus a binary format.

    WHY: The script needs to separate metadata/OCR files from images and media.
    However, many non-text files (like small binary icons) might not have extensions.
    This function uses a two-stage check:
    1. EXTENSION FILTER: Skips known high-entropy/binary formats to save I/O.
    2. NULL-BYTE CHECK: Reads a sample chunk. If a NUL character (\x00) is found,
       it is almost certainly binary (non-UTF8/ASCII).

    BACKGROUND: Internet Archive derivation often ignores non-image files in
    _images.zip. Moving plaintext to a separate _text.zip ensures metadata is
    preserved without interfering with the image-to-JP2 conversion engine.
    """
    binary_exts = {
        ".jpg",
        ".jpeg",
        ".jp2",
        ".png",
        ".bmp",
        ".gif",
        ".webp",
        ".tif",
        ".tiff",
        ".pdf",
        ".doc",
        ".docx",
        ".ppt",
        ".pptx",
        ".xls",
        ".xlsx",
        ".zip",
        ".rar",
        ".7z",
        ".tar",
        ".gz",
        ".bz2",
        ".xz",
        ".mp3",
        ".wav",
        ".flac",
        ".aac",
        ".m4a",
        ".mp4",
        ".mkv",
        ".mov",
        ".avi",
        ".wmv",
        ".webm",
        ".exe",
        ".dll",
        ".so",
        ".bin",
        ".iso",
        ".dmg",
    }
    ext = os.path.splitext(filepath)[1].lower()
    if ext in binary_exts:
        return False

    try:
        # We only read the first 8KB. This is usually enough to detect
        # binary signatures or random distribution of NUL bytes.
        with open(filepath, "rb") as fh:
            chunk = fh.read(8192)
    except OSError:
        return False

    if not chunk:
        return True
    if b"\x00" in chunk:
        return False
    return True


def _derive_prefix(filename, fallback_prefix):
    """
    STABLE ARCHIVE PREFIX GENERATOR

    WHAT: Extracts the "stem" of a filename to group related files into a single ZIP.

    WHY: Files in a series (e.g., Scan_001.jpg, Scan_002.jpg) should be zipped
    into 'Scan_images.zip'. This function strips numeric counters, underscores,
    and dashes to find the common root string.

    LOGIC:
    1. STRIP TRAILING NUMBERS: Removes standard counters like _001 or -02.
    2. NORMALIZE: Converts all numeric runs to empty strings so 'vol1_page001'
       and 'vol1_page002' both resolve to 'vol_page'.
    3. FALLBACK: If a filename is just a number (e.g. 001.jpg), it uses the
       containing folder name as the prefix.
    """
    # Pattern: Captures everything before the final counter sequence.
    match = re.search(r"^(.*?)(?:_|-)?\d+\.[a-zA-Z0-9]+$", filename)
    if match and match.group(1):
        prefix = match.group(1).strip("_-")
    else:
        prefix = fallback_prefix

    # Normalize: remove internal digits and collapse consecutive separators.
    if prefix:
        prefix = re.sub(r"\d+", "", prefix)
        prefix = re.sub(r"[_-]{2,}", "_", prefix).strip("_-")

    if not prefix:
        prefix = "ia_archive_set"
    return prefix


def process_directory(
    base_dir,
    move_mode,
    keep_mode=False,
    process_text=True,
    process_media=True,
    process_images=True,
    process_other=True,
):
    """
    DIRECTORY ARCHIVE ORCHESTRATOR

    WHAT: Scans a directory tree, groups files, creates ZIPs, and handles cleanup.

    WHY: This is the main entry point for the tool's logic. It bridges the
    user requirements (delete/move/keep) with the technical requirements of
    Internet Archive zip naming conventions.

    POST-ARCHIVAL MODES:
    - KEEP: The safest mode, leaves originals in place (Copy-to-Zip).
    - MOVE: Moves originals to a sibling folder '{base}_original', preserving
      folder structure. Use this if you want to verify the archives before deleting.
    - DELETE (Default): Removes originals immediately to save space.

    SAFETY:
    The function uses a 'with' context manager for zipfile. Cleanup ONLY runs
    after the ZIP has been successfully closed and flushed to the filesystem.
    """
    base_dir = os.path.abspath(base_dir)
    image_exts = (".jpg", ".jpeg", ".jp2", ".tif", ".tiff", ".bmp", ".png")
    media_exts = (
        ".mp3",
        ".wav",
        ".flac",
        ".aac",
        ".m4a",
        ".mp4",
        ".mkv",
        ".mov",
        ".avi",
        ".wmv",
        ".webm",
    )
    
    # Suffixes used by our own script; ensures we don't accidentally zip a generated zip
    archive_suffixes = ("_images.zip", "_media.zip", "_text.zip", "_data.zip")

    # Setup pool directory only if move_mode is enabled
    pool_dir = None
    if move_mode and not keep_mode:
        parent_dir = os.path.dirname(base_dir)
        folder_name = os.path.basename(base_dir)
        pool_dir = os.path.join(parent_dir, f"{folder_name}_original")

    # Walk recursively through the base directory
    for root, dirs, files in os.walk(base_dir):
        file_groups = {}
        leftovers = {}

        for f in files:
            lower_name = f.lower()
            ext = os.path.splitext(lower_name)[1]
            filepath = os.path.join(root, f)

            # Skip files that look like our own generated zip archives
            if lower_name.endswith(archive_suffixes):
                continue

            # Step 1: Determine file classification
            if lower_name.endswith(image_exts):
                file_class = "image"
            elif lower_name.endswith(media_exts):
                file_class = "media"
            elif _is_likely_plaintext_file(filepath):
                file_class = "text"
            else:
                file_class = "data"

            # Step 2: Check if this classification should be processed based on user flags
            if file_class == "image" and not process_images:
                continue
            if file_class == "media" and not process_media:
                continue
            if file_class == "text" and not process_text:
                continue
            if file_class == "data" and not process_other:
                continue

            # Step 3: Process and group according to classification
            if file_class == "image":
                prefix = _derive_prefix(f, os.path.basename(root))
                file_groups.setdefault(("image", prefix, ""), []).append(f)

            elif file_class == "media":
                prefix = _derive_prefix(f, os.path.basename(root))
                file_groups.setdefault(("media", prefix, ext), []).append(f)

            elif file_class == "text":
                stem = os.path.splitext(f)[0]
                # Only consider numbered plaintext files as part of a series.
                if not re.search(r"\d", stem):
                    leftovers.setdefault(("text", ext), []).append(f)
                else:
                    prefix = _derive_prefix(f, os.path.basename(root))
                    file_groups.setdefault(("text", prefix, ext), []).append(f)

            elif file_class == "data":
                prefix = _derive_prefix(f, os.path.basename(root))
                file_groups.setdefault(("data", prefix, ext), []).append(f)


        final_groups = {}
        # Process the detected groups
        for (group_kind, prefix, ext), group_files in file_groups.items():
            if not group_files:
                continue

            # Move solitary files to leftovers instead of skipping
            if len(group_files) < 2:
                leftovers.setdefault((group_kind, ext), []).extend(group_files)
                continue
                
            final_groups[(group_kind, prefix, ext)] = group_files

        # Add leftovers to final groups
        folder_prefix = os.path.basename(root)
        misc_prefix = f"{folder_prefix}_misc" if folder_prefix else "misc"
        
        for (group_kind, ext), group_files in leftovers.items():
            if group_files:
                final_groups[(group_kind, misc_prefix, ext)] = group_files

        # Process the final groups
        for (group_kind, prefix, ext), group_files in final_groups.items():
            group_files.sort()

            # Determine zip filename based on IA naming conventions
            if group_kind == "image":
                zip_name = f"{prefix}_images.zip"
            elif group_kind == "media":
                ext_label = ext.lstrip(".") or "media"
                zip_name = f"{prefix}_{ext_label}_media.zip"
            elif group_kind == "text":
                ext_label = ext.lstrip(".") or "txt"
                zip_name = f"{prefix}_{ext_label}_text.zip"
            else:
                ext_label = ext.lstrip(".") or "data"
                zip_name = f"{prefix}_{ext_label}_data.zip"
                
            zip_path = os.path.join(root, zip_name)

            print(f"Archiving {len(group_files)} files to {zip_name}...")

            # CREATE: Zip archive using stored mode for fastest packaging
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_STORED) as zf:
                for gf in group_files:
                    zf.write(os.path.join(root, gf), arcname=gf)

            # CLEANUP: Runs only after the 'with' block successfully closes (zip is confirmed on disk)
            if keep_mode:
                print(f"Done. Originals kept in place.")
            elif move_mode:
                rel_path = os.path.relpath(root, base_dir)
                target_dir = os.path.normpath(os.path.join(pool_dir, rel_path))
                os.makedirs(target_dir, exist_ok=True)

                for gf in group_files:
                    source_file = os.path.join(root, gf)
                    destination_file = os.path.join(target_dir, gf)
                    shutil.move(source_file, destination_file)
                print(f"Done. Originals moved to: {target_dir}")
            else:
                for gf in group_files:
                    source_file = os.path.join(root, gf)
                    os.remove(source_file)
                print(f"Done. Originals deleted.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="IA Image Zipper: Archive image sets for Internet Archive unpacking."
    )
    parser.add_argument(
        "-m",
        "--move",
        action="store_true",
        help="Move original files to an external '_original' folder instead of deleting them.",
    )
    parser.add_argument(
        "-k",
        "--keep",
        action="store_true",
        help="Keep original files in place after zipping.",
    )
    parser.add_argument(
        "-t", "--text", action="store_true", help="Process only text files."
    )
    parser.add_argument(
        "-M", "--media", action="store_true", help="Process only media files."
    )
    parser.add_argument(
        "-i", "--images", action="store_true", help="Process only image files."
    )
    parser.add_argument(
        "-o", "--other", action="store_true", help="Process other/unclassified files (e.g., binaries, unknown extensions)."
    )

    args = parser.parse_args()

    # If no specific type flags are provided, default to processing all types
    if not any([args.text, args.media, args.images, args.other]):
        args.text = args.media = args.images = args.other = True

    current_working_directory = os.getcwd()
    try:
        process_directory(
            current_working_directory,
            args.move,
            args.keep,
            args.text,
            args.media,
            args.images,
            args.other,
        )
    except KeyboardInterrupt:
        print("\n\nUser interrupted (Ctrl+C). Exiting gracefully...")
        sys.exit(130)
