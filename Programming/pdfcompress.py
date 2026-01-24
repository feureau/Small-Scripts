#!/usr/bin/env python
import subprocess
import sys
import os
import platform
import argparse
import glob
import re

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

def get_pdf_size(pdf_path):
    """
    Try to get the dimensions (in points) of the first page of the PDF.
    Returns (width, height) or (None, None) if failed.
    """
    try:
        # Use pdfinfo which is usually available alongside Ghostscript/Poppler
        result = subprocess.check_output(["pdfinfo", pdf_path], stderr=subprocess.STDOUT, text=True)
        for line in result.splitlines():
            if line.startswith("Page size:"):
                # Example: Page size:      595.276 x 841.89 pts (A4)
                # or: Page size:      612 x 792 pts (letter)
                match = re.search(r"([\d\.]+)\s*x\s*([\d\.]+)", line)
                if match:
                    return float(match.group(1)), float(match.group(2))
    except Exception:
        pass
    return None, None

def compress_pdf(input_pdf, output_pdf, quality, resolution, compatibility,
                 no_downsample, jpeg_quality, gs_executable, target_size=None):
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
        
    # If target_size is provided, add scaling options.
    # target_size is (width, height) in points.
    if target_size:
        tw, th = target_size
        gs_command += [
            f"-dDEVICEWIDTHPOINTS={tw}",
            f"-dDEVICEHEIGHTPOINTS={th}",
            "-dFIXEDMEDIA",
            "-dPDFFitPage"
        ]

    # Ghostscript treats '%' in output filenames as page number placeholders.
    # We must escape it by doubling it.
    escaped_output_pdf = output_pdf.replace("%", "%%")
    
    gs_command += [
        f"-sOutputFile={escaped_output_pdf}",
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
    parser.add_argument("-S", "--suffix", default="_compressed", 
                        help="Suffix to add to the output file name (default: _compressed)")
    parser.add_argument("-s", "--scale", default=None,
                        help="Scale the image. Can be a percentage (e.g., 50%%), a factor (e.g., 0.5), or a bounding box (e.g., 1024x768)")
    
    args = parser.parse_args()
    
    gs_executable = get_gs_executable(args.gs)
    
    # Expand glob patterns (e.g., *.pdf) into actual file names
    expanded_files = []
    for pattern in args.pdf_files:
        matches = glob.glob(pattern)
        if matches:
            expanded_files.extend(matches)
        else:
            # If no matches, keep the original (might be a literal filename)
            expanded_files.append(pattern)
    
    for input_pdf in expanded_files:
        if not os.path.isfile(input_pdf):
            print(f"File not found: {input_pdf}")
            continue
        
        target_size = None
        if args.scale:
            orig_w, orig_h = get_pdf_size(input_pdf)
            if orig_w and orig_h:
                if "%" in args.scale:
                    factor = float(args.scale.strip("%")) / 100.0
                    target_size = (orig_w * factor, orig_h * factor)
                elif "x" in args.scale.lower():
                    # Bounding box scaling
                    match = re.search(r"(\d+)\s*[xX]\s*(\d+)", args.scale)
                    if match:
                        box_w, box_h = float(match.group(1)), float(match.group(2))
                        # Fit within box while maintaining aspect ratio
                        ratio = min(box_w / orig_w, box_h / orig_h)
                        target_size = (orig_w * ratio, orig_h * ratio)
                else:
                    try:
                        factor = float(args.scale)
                        target_size = (orig_w * factor, orig_h * factor)
                    except ValueError:
                        print(f"Invalid scale format: {args.scale}")
            else:
                if "x" in args.scale.lower():
                    # Absolute bounding box without knowing original size
                    match = re.search(r"(\d+)\s*[xX]\s*(\d+)", args.scale)
                    if match:
                        target_size = (float(match.group(1)), float(match.group(2)))
                else:
                    print(f"Could not determine original size for {input_pdf}. Scaling by factor/percentage requires pdfinfo.")

        base, ext = os.path.splitext(input_pdf)
        output_pdf = f"{base}{args.suffix}{ext}"
        
        compress_pdf(input_pdf, output_pdf, args.quality, args.resolution, args.compatibility,
                     args.no_downsample, args.jpeg_quality, gs_executable, target_size=target_size)

if __name__ == "__main__":
    main()
