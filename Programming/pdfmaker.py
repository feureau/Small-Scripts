import sys
import glob
import argparse
import io
import os
import tempfile
from PIL import Image, ImageOps
from PyPDF2 import PdfMerger
import pypandoc

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
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


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

    if ext == '.md':
        text = open(input_file, encoding='utf-8').read()
        for line in text.splitlines():
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
        raise ValueError(f"Unsupported extension for pure-Python: {ext}")

    doc.build(story)
    return tmp_pdf.name


def convert_doc_to_pdf(input_file, pdf_engine=None, use_pandoc=False, verbose=False):
    """
    Converts DOCX, Markdown, or text file to a PDF.
    - Default: pure-Python ReportLab fallback.
    - If use_pandoc=True: uses Pandoc (with optional --pdf-engine).
    """
    if not use_pandoc:
        return convert_doc_with_reportlab(input_file, verbose)

    if verbose:
        print(f"[Pandoc] Converting {input_file} with engine={pdf_engine or 'default'}")
    tmp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    extra_args = ['--pdf-engine', pdf_engine] if pdf_engine else []
    pypandoc.convert_file(input_file, 'pdf', outputfile=tmp_pdf.name, extra_args=extra_args)
    return tmp_pdf.name


def convert_image_to_pdf(img_path, dpi, compression, rotate, resize, grayscale, verbose=False):
    """Processes an image and saves it as a one-page PDF."""
    if verbose:
        print(f"Processing image: {img_path}")
    im = Image.open(img_path)
    if rotate:
        im = im.rotate(rotate, expand=True)
    if resize:
        w, h = map(int, resize.split('x'))
        im = im.resize((w, h), Image.ANTIALIAS)
    if grayscale:
        im = ImageOps.grayscale(im)
    if im.mode in ('RGBA','P'):
        im = im.convert('RGB')
    if compression:
        buf = io.BytesIO()
        im.save(buf, format='JPEG', quality=compression)
        buf.seek(0)
        im = Image.open(buf).convert('RGB')
    tmp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    im.save(tmp_pdf.name, 'PDF', resolution=dpi)
    return tmp_pdf.name


def merge_to_pdf(files, output_pdf, dpi, compression, rotate, resize, grayscale,
                 order, pdf_engine, use_pandoc, verbose):
    """Convert each file to PDF then merge into one PDF."""
    files = sorted(files, key=os.path.getmtime) if order=='date' else sorted(files)
    temp_pdfs = []
    for f in files:
        ext = os.path.splitext(f)[1].lower()
        try:
            if ext in ['.jpg','.jpeg','.png','.gif','.bmp','.tiff']:
                temp_pdfs.append(convert_image_to_pdf(f, dpi, compression, rotate, resize, grayscale, verbose))
            elif ext in ['.docx','.md','.txt']:
                temp_pdfs.append(convert_doc_to_pdf(f, pdf_engine, use_pandoc, verbose))
            else:
                if verbose:
                    print(f"Skipping unsupported: {f}")
        except Exception as e:
            print(f"Error converting {f}: {e}")
    if not temp_pdfs:
        print("No valid files to merge.")
        sys.exit(1)
    merger = PdfMerger()
    for pdf in temp_pdfs:
        merger.append(pdf)
    merger.write(output_pdf)
    merger.close()
    print(f"Merged PDF saved as {output_pdf}")


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Merge images & docs into a single PDF (pure-Python default).")
    parser.add_argument("pattern", help="Glob/window pattern (e.g., '*.md').")
    parser.add_argument("-o","--output", default=None,
                        help="Output PDF filename; defaults to input basename + .pdf when single file.")
    parser.add_argument("-q","--compression", type=int, default=75,
                        help="JPEG compression quality 1-100 (default 75)")
    parser.add_argument("-d","--dpi", type=int, default=100,
                        help="Image DPI for PDF (default 100)")
    parser.add_argument("-r","--rotate", type=int, default=0,
                        help="Rotate images by degrees (default 0)")
    parser.add_argument("-s","--resize",
                        help="Resize images to WIDTHxHEIGHT (e.g., 1024x768)")
    parser.add_argument("-g","--grayscale", action="store_true",
                        help="Convert images to grayscale")
    parser.add_argument("--order", choices=['name','date'], default='name',
                        help="Sort files by name or date (default name)")
    parser.add_argument("-P","--pandoc", action="store_true",
                        help="Use Pandoc for doc conversion (requires pandoc installed)")
    parser.add_argument("-e","--pdf-engine", metavar='ENGINE', default=None,
                        help="Pandoc PDF engine (e.g., weasyprint), only with -P")
    parser.add_argument("-v","--verbose", action="store_true",
                        help="Verbose output")
    return parser.parse_args()


def main():
    args = parse_arguments()
    files = glob.glob(args.pattern)
    if not files:
        print(f"No files found matching: {args.pattern}")
        sys.exit(1)
    # Determine default output filename
    if not args.output:
        if len(files) == 1:
            base = os.path.splitext(os.path.basename(files[0]))[0]
            args.output = f"{base}.pdf"
        else:
            args.output = 'output.pdf'
    if args.verbose:
        print(f"Output PDF: {args.output}")
    merge_to_pdf(
        files, args.output, args.dpi, args.compression,
        args.rotate, args.resize, args.grayscale,
        args.order, args.pdf_engine, args.pandoc, args.verbose
    )

if __name__ == "__main__":
    main()
