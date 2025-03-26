#!/usr/bin/env python
import subprocess
import sys
import os
import platform
import argparse

def get_gs_executable(custom_gs=None):
    """
    Determine the correct Ghostscript executable based on the OS.
    If a custom path is provided via command line, use that.
    """
    if custom_gs:
        return custom_gs
    if sys.platform.startswith("win"):
        return "gswin64c"
    else:
        return "gs"

def compress_pdf(input_pdf, output_pdf, quality, resolution, compatibility,
                 no_downsample, jpeg_quality, gs_executable):
    """
    Compress a PDF file using Ghostscript.
    
    Parameters:
      input_pdf (str): Path to the input PDF file.
      output_pdf (str): Path to save the compressed PDF file.
      quality (str): Ghostscript PDFSETTINGS option.
      resolution (int): DPI resolution for image downsampling.
      compatibility (str): PDF compatibility level.
      no_downsample (bool): Flag to disable image downsampling options.
      jpeg_quality (int): JPEG compression quality (0-100) for rasterized images.
      gs_executable (str): Path or name of the Ghostscript executable.
    """
    gs_command = [
        gs_executable,
        "-sDEVICE=pdfwrite",
        f"-dCompatibilityLevel={compatibility}",
        f"-dPDFSETTINGS={quality}",
        "-dNOPAUSE",
        "-dQUIET",
        "-dBATCH",
    ]
    
    # Add image downsampling options if not disabled.
    if not no_downsample:
        gs_command += [
            "-dDownsampleColorImages=true",
            "-dDownsampleGrayImages=true",
            "-dDownsampleMonoImages=true",
            "-dColorImageDownsampleType=/Bicubic",
            f"-dColorImageResolution={resolution}",
            "-dGrayImageDownsampleType=/Bicubic",
            f"-dGrayImageResolution={resolution}",
            "-dMonoImageDownsampleType=/Subsample",
            f"-dMonoImageResolution={resolution}",
            "-dColorImageDownsampleThreshold=1",
            "-dGrayImageDownsampleThreshold=1",
            "-dMonoImageDownsampleThreshold=1",
            "-dAutoFilterColorImages=true",
            "-dAutoFilterGrayImages=true",
            "-dColorImageFilter=/DCTEncode",
            "-dGrayImageFilter=/DCTEncode",
            f"-dJPEGQ={jpeg_quality}",
        ]
        
    gs_command += [
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
    parser = argparse.ArgumentParser(
        description="Compress PDF files using Ghostscript with various options."
    )
    parser.add_argument("pdf_files", nargs="+", help="PDF files to compress")
    parser.add_argument("-q", "--quality", default="/screen", choices=["/screen", "/ebook", "/printer", "/prepress", "/default"],
                        help="Ghostscript PDF settings for quality (default: /screen)")
    parser.add_argument("-r", "--resolution", type=int, default=72, 
                        help="Image resolution (in DPI) for downsampling (default: 72)")
    parser.add_argument("-n", "--no-downsample", action="store_true", 
                        help="Disable image downsampling options")
    parser.add_argument("-c", "--compatibility", default="1.4", 
                        help="PDF compatibility level (default: 1.4)")
    parser.add_argument("-j", "--jpeg-quality", type=int, default=50, 
                        help="JPEG quality (0-100) for rasterized images (default: 50, lower means higher compression)")
    parser.add_argument("-g", "--gs", default=None, 
                        help="Path to Ghostscript executable. If not provided, the default for the OS is used")
    parser.add_argument("-s", "--suffix", default="_compressed", 
                        help="Suffix to add to the output file name (default: _compressed)")
    
    args = parser.parse_args()
    
    gs_executable = get_gs_executable(args.gs)
    
    for input_pdf in args.pdf_files:
        if not os.path.isfile(input_pdf):
            print(f"File not found: {input_pdf}")
            continue
        
        base, ext = os.path.splitext(input_pdf)
        output_pdf = f"{base}{args.suffix}{ext}"
        
        compress_pdf(input_pdf, output_pdf, args.quality, args.resolution, args.compatibility,
                     args.no_downsample, args.jpeg_quality, gs_executable)

if __name__ == "__main__":
    main()
