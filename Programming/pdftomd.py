import sys
import glob
import pathlib
import warnings

# Suppress harmless numpy/OCR warnings on blank page slices
warnings.filterwarnings("ignore", category=RuntimeWarning)
warnings.filterwarnings("ignore", category=UserWarning)

try:
    import pymupdf4llm
except ImportError:
    print("Error: The 'pymupdf4llm' library is not installed.")
    print("Please install it by running: pip install pymupdf4llm")
    sys.exit(1)

# Fix upstream pymupdf4llm bug where sanitized image path directories are not created
try:
    import pymupdf4llm.helpers.document_layout as dl
    _orig_md_path = dl.utils.md_path
    def _safe_md_path(folder: str, filename: str):
        md_ref, save_path = _orig_md_path(folder, filename)
        pathlib.Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        return md_ref, save_path
    dl.utils.md_path = _safe_md_path
except Exception:
    pass

def process_pdf(pdf_path, overwrite=False, use_ocr=True):
    pdf_file = pathlib.Path(pdf_path)
    
    # Ensure the file actually exists and is a valid file
    if not pdf_file.is_file():
        print(f"[!] File not found or not a valid file: {pdf_path}")
        return
        
    md_filename = pdf_file.with_suffix(".md")
    
    # Skip if markdown already exists (unless overwrite/force is specified)
    if md_filename.exists() and not overwrite:
        print(f"[-] Skipping (already exists): {pdf_file.name}")
        return
        
    print(f"-> Processing: {pdf_file.name} ...")
    
    # Define a folder to hold the extracted images (e.g., input_images)
    image_folder = pdf_file.parent / f"{pdf_file.stem}_images"
    
    # Create the image folder if it doesn't exist
    image_folder.mkdir(parents=True, exist_ok=True)
    
    try:
        # Convert the PDF to Markdown
        # write_images=True tells it to pull out images
        # image_path tells it where to save those images
        md_text = pymupdf4llm.to_markdown(
            doc=str(pdf_file),
            write_images=True, 
            image_path=str(image_folder),
            image_format="png",     # Saves images as high-quality PNGs
            dpi=200,                 # 200 DPI ensures crisp images
            show_progress=True,      # Displays progress bar for multi-page documents
            use_ocr=use_ocr          # OCR toggle
        )
        
        # Save the Markdown text
        # We use .encode("utf-8") which prevents Windows Unicode errors with special characters
        md_filename.write_bytes(md_text.encode("utf-8"))
        
        print(f"   [+] Success! Markdown saved to: {md_filename.name}")
        print(f"   [+] Images saved in folder:     {image_folder.name}\n")
        
    except KeyboardInterrupt:
        raise
    except Exception as e:
        print(f"   [X] Failed to process {pdf_file.name}. Error: {e}\n")

def main():
    args = sys.argv[1:]
    overwrite = False
    use_ocr = True
    
    if "--force" in args or "-f" in args:
        overwrite = True
        args = [a for a in args if a not in ("--force", "-f")]
        
    if "--no-ocr" in args:
        use_ocr = False
        args = [a for a in args if a != "--no-ocr"]
    
    try:
        if len(args) == 0:
            # If no arguments passed, process ALL pdf files in the current folder and subfolders
            pdf_files = [p for p in pathlib.Path(".").rglob("*.[pP][dD][fF]") if p.is_file()]
            
            if not pdf_files:
                print("No PDF files found in the current directory or subdirectories.")
                print("Usage: python pdftomd.py [--force] [--no-ocr] [optional_specific_file.pdf ...]")
                sys.exit(0)
                
            print(f"Found {len(pdf_files)} PDF(s) in this directory and subdirectories. Starting batch conversion...\n")
            print("-" * 50)
            
            for pdf in pdf_files:
                process_pdf(pdf, overwrite=overwrite, use_ocr=use_ocr)
                
        else:
            # If specific files are provided, process them
            for pdf_arg in args:
                process_pdf(pdf_arg, overwrite=True, use_ocr=use_ocr)
                
    except KeyboardInterrupt:
        print("\n[!] Batch processing stopped by user.")
        sys.exit(130)

if __name__ == "__main__":
    main()