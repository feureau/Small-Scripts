import os
import sys
import zipfile
import glob

# Define common media extensions found in EPUBs
MEDIA_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.gif', '.svg',  # Images
    '.mp3', '.ogg', '.wav',                   # Audio
    '.mp4', '.webm'                           # Video
}

def extract_media(epub_path):
    if not os.path.isfile(epub_path):
        print(f"Skipping: {epub_path} (Not a file)")
        return

    # Create output folder name based on filename (e.g., "book.epub" -> "book_media")
    base_name = os.path.splitext(os.path.basename(epub_path))[0]
    output_folder = os.path.join(os.getcwd(), f"{base_name}_media")

    try:
        with zipfile.ZipFile(epub_path, 'r') as z:
            # Filter files inside the zip that have media extensions
            media_files = [f for f in z.namelist() if os.path.splitext(f.lower())[1] in MEDIA_EXTENSIONS]
            
            if not media_files:
                print(f"No media found in {epub_path}")
                return

            # Create output directory
            os.makedirs(output_folder, exist_ok=True)
            print(f"Extracting {len(media_files)} files to: {output_folder}")

            for file_info in media_files:
                # Get just the filename to avoid creating deep nested subfolders from the zip
                filename = os.path.basename(file_info)
                if not filename: continue # Skip if it's a directory
                
                target_path = os.path.join(output_folder, filename)
                
                # Extract the file data and write it
                with z.open(file_info) as source, open(target_path, "wb") as target:
                    target.write(source.read())

    except zipfile.BadZipFile:
        print(f"Error: {epub_path} is not a valid EPUB/ZIP file.")
    except Exception as e:
        print(f"An error occurred with {epub_path}: {e}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python epubextract.py <file_or_wildcard>")
        sys.exit(1)

    # The shell (Mac/Linux) or glob (Windows) handles the *
    input_patterns = sys.argv[1:]
    
    files_to_process = []
    for pattern in input_patterns:
        # Expand wildcards (crucial for Windows CMD)
        matched = glob.glob(pattern)
        files_to_process.extend(matched)

    if not files_to_process:
        print("No matching files found.")
        return

    for epub_file in files_to_process:
        if epub_file.lower().endswith(".epub"):
            extract_media(epub_file)

if __name__ == "__main__":
    main()