# compress_pdf.py
import subprocess
import sys
import os
import platform

def get_gs_executable():
    """
    Determine the correct Ghostscript executable based on the OS.
    On Windows, use gswin64c; on Unix-like systems, use gs.
    If you have a custom installation, you might need to provide the full path.
    """
    if sys.platform.startswith("win"):
        # You can also provide the full path if Ghostscript is not in the PATH.
        # For example: r"C:\Program Files\gs\gs10.04.0\bin\gswin64c.exe"
        return "gswin64c"
    else:
        return "gs"

def compress_pdf(input_pdf, output_pdf, quality="/ebook"):
    """
    Compress a PDF file using Ghostscript.
    
    Parameters:
      input_pdf (str): Path to the input PDF file.
      output_pdf (str): Path to save the compressed PDF file.
      quality (str): Ghostscript PDFSETTINGS option. Options include:
                     /screen (low quality), /ebook, /printer, /prepress (high quality)
    """
    gs_executable = get_gs_executable()
    gs_command = [
        gs_executable,
        "-sDEVICE=pdfwrite",
        "-dCompatibilityLevel=1.4",
        f"-dPDFSETTINGS={quality}",
        "-dNOPAUSE",
        "-dQUIET",
        "-dBATCH",
        f"-sOutputFile={output_pdf}",
        input_pdf
    ]
    
    try:
        subprocess.check_call(gs_command)
        print(f"Compressed '{input_pdf}' to '{output_pdf}' successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error compressing {input_pdf}: {e}")
    except FileNotFoundError as fnf_error:
        print(f"Ghostscript executable not found. Please ensure it is installed and in your PATH. Error: {fnf_error}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python compress_pdf.py file1.pdf file2.pdf ...")
        sys.exit(1)
    
    for input_pdf in sys.argv[1:]:
        if not os.path.isfile(input_pdf):
            print(f"File not found: {input_pdf}")
            continue
        
        # Define output file name by adding a suffix before the file extension
        base, ext = os.path.splitext(input_pdf)
        output_pdf = f"{base}_compressed{ext}"
        
        compress_pdf(input_pdf, output_pdf)

if __name__ == "__main__":
    main()
