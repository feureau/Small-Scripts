import sys
import glob
import argparse
import io
import os
import tempfile
from PIL import Image, ImageOps
from PyPDF2 import PdfMerger
import pypandoc

# --- Try to determine the correct resampling filter ---
# Pillow >= 9.1.0 uses Resampling enum
# Older versions use integer constants like Image.ANTIALIAS
try:
    RESAMPLE_FILTER = Image.Resampling.LANCZOS
except AttributeError:
    RESAMPLE_FILTER = Image.ANTIALIAS # Fallback for older Pillow versions

# Optional pure-Python dependencies
try:
    import markdown
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from docx import Document as DocxDocument
    PURE_PYTHON_AVAILABLE = True
except ImportError:
    PURE_PYTHON_AVAILABLE = False


def escape_text(text):
    """
    Escape &, <, and > for ReportLab's Paragraph parser.
    """
    return text.replace('&', '&').replace('<', '<').replace('>', '>')


def convert_doc_with_reportlab(input_file, verbose=False):
    """
    Pure-Python conversion of DOCX, Markdown, or text to PDF using ReportLab.
    Requires: reportlab, markdown, python-docx.
    """
    if not PURE_PYTHON_AVAILABLE:
        raise RuntimeError(
            "Pure-Python PDF conversion dependencies missing: install reportlab, markdown, python-docx.")
    if verbose:
        print(f"[Pure-Python] Converting {input_file}")
    tmp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    doc = SimpleDocTemplate(tmp_pdf.name)
    styles = getSampleStyleSheet()
    story = []
    ext = os.path.splitext(input_file)[1].lower()

    try:
        if ext == '.md':
            text = open(input_file, encoding='utf-8').read()
            html = markdown.markdown(text) # Basic markdown to HTML
            # TODO: Improve HTML to ReportLab conversion if needed (beyond simple paras)
            for line in text.splitlines(): # Sticking to simple line-by-line for now
                story.append(Paragraph(escape_text(line), styles['Normal']))
                story.append(Spacer(1, 4))
        elif ext == '.txt':
            with open(input_file, encoding='utf-8') as f:
                for line in f:
                    story.append(Paragraph(escape_text(line.rstrip()), styles['Normal']))
                    story.append(Spacer(1, 4))
        elif ext == '.docx':
            docx = DocxDocument(input_file)
            for para in docx.paragraphs:
                story.append(Paragraph(escape_text(para.text), styles['Normal']))
                story.append(Spacer(1, 4))
        else:
            # This path should not be reached if called from merge_to_pdf logic
            raise ValueError(f"Unsupported extension for pure-Python: {ext}")

        doc.build(story)
        return tmp_pdf.name
    except Exception as e:
        os.remove(tmp_pdf.name) # Clean up temp file on error
        raise e # Re-raise the exception


def convert_doc_to_pdf(input_file, pdf_engine=None, use_pandoc=False, verbose=False):
    """
    Converts DOCX, Markdown, or text file to a PDF.
    - Default: pure-Python ReportLab fallback.
    - If use_pandoc=True: uses Pandoc (with optional --pdf-engine).
    """
    if not use_pandoc:
        # Attempt pure-Python conversion
        try:
            return convert_doc_with_reportlab(input_file, verbose)
        except (RuntimeError, ValueError, ImportError) as e:
            print(f"Pure Python conversion failed for {input_file}: {e}", file=sys.stderr)
            print("Install optional dependencies (reportlab, python-docx, markdown) or use --pandoc.", file=sys.stderr)
            # Raise the error to stop processing this file
            raise e
        except Exception as e: # Catch other potential errors during conversion
            print(f"Error during pure Python conversion of {input_file}: {e}", file=sys.stderr)
            raise e

    # --- Use Pandoc ---
    if verbose:
        print(f"[Pandoc] Converting {input_file} with engine={pdf_engine or 'default'}")
    tmp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    try:
        extra_args = ['--pdf-engine', pdf_engine] if pdf_engine else []
        pypandoc.convert_file(input_file, 'pdf', outputfile=tmp_pdf.name, extra_args=extra_args)
        return tmp_pdf.name
    except Exception as e:
        os.remove(tmp_pdf.name) # Clean up temp file on error
        raise e # Re-raise the exception


def convert_image_to_pdf(img_path, dpi, compression, rotate, resize, grayscale, verbose=False):
    """
    Processes an image and saves it as a one-page PDF.
    Handles basic transformations.
    Note: Multi-page TIFFs will only have their first page converted.
    Note: The 'compression' argument is largely ignored by Pillow's direct PDF saving.
    """
    if verbose:
        print(f"Processing image: {img_path}")
    im = None # Initialize im to None
    tmp_pdf = None # Initialize tmp_pdf to None
    try:
        # Ensure Pillow can read the specific TIFF format (may need libtiff)
        im = Image.open(img_path)

        if rotate:
            im = im.rotate(rotate, expand=True)
        if resize:
            w, h = map(int, resize.split('x'))
            im = im.resize((w, h), RESAMPLE_FILTER)
        if grayscale:
            # Use ImageOps.grayscale for better handling than just convert('L')
            im = ImageOps.grayscale(im)

        # Convert modes suitable for PDF embedding (RGB is safest)
        # Handle common cases like RGBA (remove alpha), P (palette)
        # Grayscale ('L') images are usually handled correctly by PDF save
        if im.mode in ('RGBA', 'P'):
            if verbose:
                print(f"  Converting image mode from {im.mode} to RGB")
            im = im.convert('RGB')
        elif im.mode == 'LA': # Grayscale with Alpha
             if verbose:
                print(f"  Converting image mode from LA to L (Grayscale)")
             im = im.convert('L')
        # Note: CMYK might work directly, but converting to RGB is often more compatible
        # elif im.mode == 'CMYK':
        #     im = im.convert('RGB')

        # *** Removed the problematic intermediate JPEG conversion block ***
        # The --compression flag now has limited effect for direct image->PDF save

        tmp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        # Save directly to PDF format using Pillow's writer
        im.save(tmp_pdf.name, 'PDF', resolution=dpi)
        return tmp_pdf.name

    except Exception as e:
        # Clean up temp file if created before the error
        if tmp_pdf and os.path.exists(tmp_pdf.name):
            try:
                os.remove(tmp_pdf.name)
            except OSError:
                pass # Ignore error if removal fails
        # Re-raise the exception to be caught in the main loop
        raise e
    finally:
        # Ensure the image object is closed
        if im:
            im.close()


def merge_to_pdf(files, output_pdf, dpi, compression, rotate, resize, grayscale,
                 order, pdf_engine, use_pandoc, verbose):
    """Convert each file to PDF then merge into one PDF."""
    files = sorted(files, key=os.path.getmtime) if order=='date' else sorted(files)
    temp_pdfs = []
    success_count = 0
    error_count = 0

    for f in files:
        ext = os.path.splitext(f)[1].lower()
        try:
            # *** UPDATED THIS LINE TO INCLUDE .tif ***
            if ext in ['.jpg','.jpeg','.png','.gif','.bmp','.tiff', '.tif']:
                pdf_path = convert_image_to_pdf(f, dpi, compression, rotate, resize, grayscale, verbose)
                temp_pdfs.append(pdf_path)
                success_count += 1
            elif ext in ['.docx','.md','.txt']:
                pdf_path = convert_doc_to_pdf(f, pdf_engine, use_pandoc, verbose)
                temp_pdfs.append(pdf_path)
                success_count += 1
            else:
                if verbose:
                    print(f"Skipping unsupported file type: {f}")
        except (Image.UnidentifiedImageError, FileNotFoundError) as e:
             print(f"Error opening or identifying file {f}: {e}", file=sys.stderr)
             error_count += 1
        except pypandoc.PandocError as e:
            print(f"Pandoc conversion error for {f}: {e}", file=sys.stderr)
            error_count += 1
        except ImportError as e:
             print(f"Missing dependency for processing {f}: {e}", file=sys.stderr)
             error_count += 1
        except RuntimeError as e: # Catch missing dependency errors from pure python path
             print(f"Runtime error processing {f}: {e}", file=sys.stderr)
             error_count += 1
        except Exception as e:
            # Catch any other exceptions during conversion
            print(f"Failed to convert {f}: {type(e).__name__} - {e}", file=sys.stderr)
            error_count += 1
            if verbose: # Provide more detail if verbose is on
                import traceback
                traceback.print_exc()


    if not temp_pdfs:
        print("No files were successfully converted to PDF. Cannot merge.", file=sys.stderr)
        # Clean up any stray temp files just in case (though unlikely)
        for pdf in temp_pdfs:
            if os.path.exists(pdf):
                os.remove(pdf)
        sys.exit(1)

    merger = PdfMerger()
    merge_success = True
    try:
        if verbose:
            print(f"\nMerging {len(temp_pdfs)} PDF files...")
        for pdf in temp_pdfs:
            if verbose:
                print(f"  Appending {os.path.basename(pdf)}")
            try:
                merger.append(pdf)
            except Exception as merge_err:
                 print(f"Error appending {os.path.basename(pdf)} to merge list: {merge_err}", file=sys.stderr)
                 error_count += 1 # Count merge errors as errors

        merger.write(output_pdf)
    except Exception as e:
        print(f"\nError writing final PDF '{output_pdf}': {e}", file=sys.stderr)
        merge_success = False
    finally:
        merger.close()
        # Clean up temporary PDF files
        if verbose:
            print("Cleaning up temporary files...")
        for pdf in temp_pdfs:
             try:
                 if os.path.exists(pdf):
                    os.remove(pdf)
             except OSError as e:
                 print(f"Warning: Could not remove temporary file {pdf}: {e}", file=sys.stderr)


    print("-" * 20)
    if merge_success:
        print(f"Successfully merged {success_count} file(s) into {output_pdf}")
    else:
         print(f"Attempted merge, but failed to write final PDF.")

    if error_count > 0:
        print(f"Encountered errors with {error_count} file(s). Check messages above.", file=sys.stderr)
        # Optionally exit with error code if any file failed
        # sys.exit(1)
    elif not merge_success:
        sys.exit(1) # Exit with error if final merge failed


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Merge images & docs into a single PDF. Handles common image formats (JPG, PNG, GIF, BMP, TIF/TIFF) and documents (DOCX, MD, TXT). Uses pure-Python libraries by default, with Pandoc as an option.",
        formatter_class=argparse.RawTextHelpFormatter # Keep formatting in help
        )
    parser.add_argument("pattern", help="Glob/window pattern for input files (e.g., '*.tif', 'scans/*.jpg', 'report.*').\nUse quotes if pattern contains spaces or special characters.")
    parser.add_argument("-o","--output", default=None,
                        help="Output PDF filename.\nDefaults to 'output.pdf', or uses the input filename base if only one file matches.")
    parser.add_argument("-q","--compression", type=int, default=75,
                        help="Image compression quality (1-100).\nNOTE: This argument is currently IGNORED by the Pillow PDF writer when converting images directly.\nIt might affect Pandoc conversions if Pandoc uses it. (Default: 75)")
    parser.add_argument("-d","--dpi", type=int, default=100,
                        help="Image DPI (dots per inch) for PDF embedding (Default: 100)")
    parser.add_argument("-r","--rotate", type=int, default=0, choices=[0, 90, 180, 270],
                        help="Rotate images by degrees (0, 90, 180, 270). (Default: 0)")
    parser.add_argument("-s","--resize", metavar="WxH",
                        help="Resize images to WIDTHxHEIGHT (e.g., '1024x768'). Aspect ratio is not preserved.")
    parser.add_argument("-g","--grayscale", action="store_true",
                        help="Convert images to grayscale.")
    parser.add_argument("--order", choices=['name','date'], default='name',
                        help="Sort input files by name or modification date (Default: name)")
    parser.add_argument("-P","--pandoc", action="store_true",
                        help="Use Pandoc for DOCX/MD/TXT conversion (requires Pandoc installed).\nPure-Python libraries (ReportLab, python-docx, markdown) are used otherwise.")
    parser.add_argument("-e","--pdf-engine", metavar='ENGINE', default=None,
                        help="Pandoc PDF engine (e.g., 'xelatex', 'weasyprint', 'wkhtmltopdf'). Only used with --pandoc.")
    parser.add_argument("-v","--verbose", action="store_true",
                        help="Print detailed information during processing.")
    return parser.parse_args()


def main():
    args = parse_arguments()
    try:
        files = glob.glob(args.pattern)
    except Exception as e:
         print(f"Error evaluating file pattern '{args.pattern}': {e}", file=sys.stderr)
         sys.exit(1)

    if not files:
        print(f"No files found matching pattern: {args.pattern}")
        sys.exit(1)

    # Determine default output filename
    if not args.output:
        # If only one file matched the pattern, use its name as the base
        if len(files) == 1:
            base = os.path.splitext(os.path.basename(files[0]))[0]
            args.output = f"{base}.pdf"
        else:
            # Otherwise, use a generic name
            args.output = 'output.pdf'
            print(f"Multiple input files found. Defaulting output to: {args.output}")


    if args.verbose:
        print(f"Input pattern: {args.pattern}")
        print(f"Found {len(files)} file(s):")
        for f in sorted(files): # Show sorted list for clarity
             print(f"  - {f}")
        print(f"Output PDF: {args.output}")
        print(f"Sorting by: {args.order}")
        print(f"Image DPI: {args.dpi}")
        print(f"Image Rotation: {args.rotate}")
        print(f"Image Resize: {args.resize or 'None'}")
        print(f"Image Grayscale: {args.grayscale}")
        print(f"Compression quality (Info): {args.compression} (Note: Pillow PDF writer ignores this)")
        print(f"Using Pandoc for docs: {args.pandoc}")
        if args.pandoc:
            print(f"Pandoc PDF Engine: {args.pdf_engine or 'default'}")
        print("-" * 20)


    # Check for potential conflicts or issues
    if args.pdf_engine and not args.pandoc:
        print("Warning: --pdf-engine is specified but --pandoc is not. The engine will be ignored.", file=sys.stderr)

    # Check pure python dependencies if not using pandoc
    if not args.pandoc:
        doc_files_present = any(os.path.splitext(f)[1].lower() in ['.docx', '.md', '.txt'] for f in files)
        if doc_files_present and not PURE_PYTHON_AVAILABLE:
             print("Warning: Document files found, but optional pure-Python dependencies (reportlab, python-docx, markdown) are missing.", file=sys.stderr)
             print("Document conversion will fail unless you install them or use the --pandoc flag.", file=sys.stderr)


    merge_to_pdf(
        files, args.output, args.dpi, args.compression,
        args.rotate, args.resize, args.grayscale,
        args.order, args.pdf_engine, args.pandoc, args.verbose
    )

if __name__ == "__main__":
    main()