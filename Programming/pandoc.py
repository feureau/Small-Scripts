#!/usr/bin/env python3
"""
=================================================
Pandoc Batch Converter Script: Detailed Rationale
=================================================

Version: 2.0

### 1. High-Level Purpose

This script serves as a user-friendly command-line wrapper for Pandoc, a powerful universal document converter. Its primary goal is to simplify the process of converting multiple files (batch conversion) from one format to another without needing to remember complex Pandoc commands. It is designed for common, everyday conversion tasks while providing flexibility for more advanced uses.

### 2. Key Features

-   **Batch Conversion:** Uses glob patterns (e.g., "*.md") to convert many files at once.
-   **User-Friendly:** Simplifies command-line usage compared to raw Pandoc.
-   **Automatic Setup:** Checks for Pandoc and attempts to automatically download and install it if missing, reducing setup friction.
-   **Flexible Input:** Can handle a wide range of common formats and includes an explicit '--from' flag to support any input format Pandoc can read.
-   **Robustness:** Includes progress reporting and error handling, so one failed file won't stop the entire batch process.
-   **Cross-Platform:** Built with standard Python libraries to work on Windows, macOS, and Linux.

### 3. System Requirements

-   **Python 3.x:** The script uses modern Python syntax and the `pathlib` library.
-   **pypandoc:** A Python library that acts as a wrapper for the Pandoc executable. It can be installed with `pip install pypandoc`.
-   **pandoc executable:** The core conversion engine. The `pypandoc` library will attempt to download this automatically if it's not found in the system's PATH.

### 4. Usage Instructions

The script is run from the command line with the following structure:
`python pandoc_converter_v2.py [input_pattern] [output_format] [options]`

**Examples:**
-   `python pandoc_converter_v2.py "*.md" docx`
    (Converts all Markdown files in the current directory to DOCX)
-   `python pandoc_converter_v2.py "report.txt" pdf`
    (Converts a single plaintext file to PDF, automatically treating it as Markdown)
-   `python pandoc_converter_v2.py "book.epub" odt -f epub`
    (Explicitly tells Pandoc that the input format is EPUB, converting it to ODT)
-   `python pandoc_converter_v2.py "chapter-*.rst" html`
    (Converts all ReStructuredText files starting with 'chapter-' to HTML)

**Important Note:** Use quotes around patterns with wildcards (like "*.md") to prevent your command-line shell from expanding the pattern before the script can process it.

-------------------------------------------------
### 5. Core Logic and Design Rationale
-------------------------------------------------

This section explains *why* the script is built the way it is.

**a. Dependency Management (`ensure_pandoc` function):**
-   **Why:** The script's core functionality depends entirely on the Pandoc executable. A common point of failure for users is not having dependencies installed correctly.
-   **Rationale:** This function was created to make the script as "plug-and-play" as possible. It leverages `pypandoc.ensure_pandoc_installed()` to first check for an existing installation. If that fails, it proactively tries to download it. This design choice significantly improves the user experience by automating the most critical setup step. If the automatic download also fails, it provides clear, actionable instructions for manual installation.

**b. Command-Line Argument Parsing (`main` function):**
-   **Why:** The script needs to accept user input (files, formats) from the command line.
-   **Rationale:** The script uses Python's built-in `sys.argv` for parsing. For the simple needs of this script (input pattern, output format, and one optional flag), this approach is lightweight and avoids adding extra dependencies like `argparse`. A more complex script with many flags would benefit from `argparse`, but for this use case, manual parsing of the list is sufficient and keeps the code simple and readable.

**c. File Discovery (`glob.glob` and `pathlib`):**
-   **Why:** The script needs to find all the files that match the user's input pattern.
-   **Rationale:**
    -   `glob.glob` is the standard Python library for handling Unix-style wildcard patterns (`*`, `?`, `[]`). This is the most intuitive way for a user to specify multiple files and is a core feature of the script's "batch" capability.
    -   `pathlib` is used for all file path manipulations. This is a deliberate choice over older `os.path` methods because `pathlib` provides an object-oriented, modern, and cross-platform-safe way to handle paths. For example, `file_path.with_suffix(f'.{output_format}')` is a much cleaner and more reliable way to change a file's extension than manual string splitting and joining.

**d. Input Format Handling (The '--from' flag and `format_map`):**
-   **Why:** Pandoc can read dozens of formats, but it can't always guess the correct format from a file's extension, especially for generic ones like `.txt`.
-   **Rationale:** A multi-layered approach was chosen for maximum flexibility and ease of use:
    1.  **User Override (`--from` flag):** This is the most powerful option. It gives the user complete control, allowing them to tell Pandoc exactly how to interpret a file. This design makes the script capable of handling *any* input format Pandoc supports, even if the file has a non-standard extension (e.g., converting a `.log` file as if it were markdown).
    2.  **Ambiguous Extension Mapping (`format_map`):** For the most common ambiguity (`.txt`), a simple dictionary maps the extension to a default Pandoc format (`markdown`). This solves 90% of the common issues for casual users without forcing them to use the `--from` flag. This map can be easily extended if other common ambiguities are found.
    3.  **Default Inference:** If neither of the above conditions is met, the script lets `pypandoc` do what it does best: infer the input format from the file extension (e.g., `.md` -> markdown, `.docx` -> docx).

**e. Conversion Loop and Error Handling:**
-   **Why:** When converting a large number of files, it's likely that one or more might be corrupted or in an unexpected format.
-   **Rationale:** The main conversion logic is wrapped in a `try...except Exception as e:` block. This is a crucial design choice for a batch processing tool. It ensures that if a single file fails to convert, the script prints a helpful error message for that specific file and then *continues* to the next one, rather than crashing the entire process. This makes the script robust and reliable for large jobs.

**f. Modular Functions (`ensure_pandoc`, `convert_files`, `show_help`, `main`):**
-   **Why:** The code is organized into separate functions, each with a clear purpose.
-   **Rationale:** This follows standard software design principles. It makes the code easier to read, test, and maintain. For example, if the argument parsing logic needed to be changed, only the `main` function would need to be edited. If the core conversion logic needed updating, only `convert_files` would be affected.

**g. Entry Point (`if __name__ == "__main__":`)**
-   **Why:** This is a standard Python convention.
-   **Rationale:** It ensures that the `main()` function is only called when the script is executed directly from the command line. This allows the script's functions (like `convert_files`) to be potentially imported and used in other Python programs without automatically running the command-line interface.
"""

import pypandoc
import sys
import glob
import subprocess
import shutil
from pathlib import Path

# Optional PDF conversion dependencies
try:
    import markdown
    from xhtml2pdf import pisa
    LIB_PDF_AVAILABLE = True
except ImportError:
    LIB_PDF_AVAILABLE = False

# Default font to use when converting Markdown inputs.
# Uses CMU Serif (cmunrm.ttf) from the Computer Modern Unicode family.
DEFAULT_MARKDOWN_FONT = "CMU Serif"

MARKDOWN_FORMAT_NAMES = {
    "markdown",
    "md",
    "gfm",
    "commonmark",
    "commonmark_x",
}


def is_markdown_format(fmt):
    if not fmt:
        return False
    return fmt.lower() in MARKDOWN_FORMAT_NAMES


def wrap_html_with_font(html_body, font_name):
    return f"""<html>
<head>
  <style>
    body {{ font-family: '{font_name}', serif; }}
  </style>
</head>
<body>
{html_body}
</body>
</html>"""


def update_reference_docx_font(docx_path, font_name):
    """
    Patch all font references inside a .docx to use font_name.
    Uses regex-based text substitution on the raw XML so namespace
    round-trip issues in ElementTree cannot corrupt the file.
    """
    import zipfile
    import shutil
    import re

    docx_path = Path(docx_path)
    tmp_path = docx_path.with_suffix('.tmp.docx')

    def patch_styles(text):
        # Replace every <w:rFonts .../> element wholesale so both explicit font
        # names (w:ascii="Calibri") and theme references (w:asciiTheme="minorHAnsi")
        # are overwritten with the desired font.
        repl = (
            f'<w:rFonts w:ascii="{font_name}" w:hAnsi="{font_name}" '
            f'w:cs="{font_name}" w:eastAsia="{font_name}"/>'
        )
        text = re.sub(r'<w:rFonts\b[^/]*/>', repl, text)
        text = re.sub(r'<w:rFonts\b[^>]*>.*?</w:rFonts>', repl, text, flags=re.DOTALL)
        return text

    def patch_theme(text):
        # Replace all typeface= values inside font-family elements.
        # Skip the "+mj-lt" / "+mn-lt" virtual-font tokens — those live inside
        # <a:font> fallback lists and should keep their original values.
        def _repl(m):
            val = m.group(1)
            if val.startswith('+') or val.startswith('&'):
                return m.group(0)
            return f'typeface="{font_name}"'
        return re.sub(r'typeface="([^"]*)"', _repl, text)

    PATCH_MAP = {
        'word/styles.xml':       patch_styles,
        'word/theme/theme1.xml': patch_theme,
    }

    with zipfile.ZipFile(docx_path, 'r') as zin, \
         zipfile.ZipFile(tmp_path, 'w', compression=zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            patcher = PATCH_MAP.get(item.filename)
            if patcher:
                try:
                    data = patcher(data.decode('utf-8')).encode('utf-8')
                except Exception:
                    pass  # leave unchanged if anything goes wrong
            zout.writestr(item, data)

    shutil.move(str(tmp_path), str(docx_path))


def ensure_reference_docx(reference_path, font_name):
    reference_path = Path(reference_path)

    # Always regenerate from Pandoc defaults so we never patch a stale/broken file.
    pandoc_path = pypandoc.get_pandoc_path()
    result = subprocess.run(
        [pandoc_path, '--print-default-data-file=reference.docx'],
        capture_output=True,
        check=False
    )
    if result.returncode != 0:
        stderr = result.stderr.decode('utf-8', errors='ignore').strip()
        raise RuntimeError(f"Pandoc failed to create reference.docx: {stderr}")

    reference_path.write_bytes(result.stdout)
    update_reference_docx_font(reference_path, font_name)
    return reference_path

def detect_pdf_engine():
    """
    Return the best available Pandoc PDF engine and whether it supports
    fontspec (i.e. can load system fonts by name via -V mainfont=...).

    Priority: xelatex > lualatex > pdflatex > wkhtmltopdf > weasyprint
    Returns (engine_name, supports_fontspec) or (None, False) if nothing found.
    """
    candidates = [
        ('xelatex',     True),
        ('lualatex',    True),
        ('pdflatex',    False),
        ('wkhtmltopdf', False),
        ('weasyprint',  False),
    ]
    for engine, fontspec in candidates:
        if shutil.which(engine):
            return engine, fontspec
    return None, False


def convert_to_pdf_lib(input_path, output_path, input_format=None, font_name=None):
    """
    Convert a file to PDF using xhtml2pdf (pisa).
    Supports MD, TXT, HTML directly. 
    Supports DOCX by converting to HTML via pypandoc first.
    """
    if not LIB_PDF_AVAILABLE:
        raise RuntimeError("Missing xhtml2pdf or markdown libraries for library-based PDF conversion.")
    
    file_path = Path(input_path)
    ext = file_path.suffix.lower()
    
    html_content = ""
    
    if input_format == 'markdown' or ext in ('.md', '.markdown'):
        text = file_path.read_text(encoding='utf-8')
        # Use simple markdown for robust conversion
        html_content = markdown.markdown(text, extensions=['extra', 'codehilite'])
        html_content = wrap_html_with_font(html_content, font_name or DEFAULT_MARKDOWN_FONT)
    elif ext == '.txt':
        text = file_path.read_text(encoding='utf-8')
        html_content = f"<pre>{text}</pre>"
        html_content = wrap_html_with_font(html_content, font_name or DEFAULT_MARKDOWN_FONT)
    elif input_format == 'docx' or ext == '.docx':
        # Convert DOCX to HTML via Pandoc first
        html_content = pypandoc.convert_file(str(file_path), 'html')
    elif input_format == 'html' or ext in ('.html', '.htm'):
        html_content = file_path.read_text(encoding='utf-8')
    else:
        # Fallback: try to let pandoc handle the HTML conversion if we can't guess
        try:
            html_content = pypandoc.convert_file(str(file_path), 'html')
        except:
            return False

    # Create the PDF
    with open(output_path, "wb") as pdf_file:
        pisa_status = pisa.CreatePDF(html_content, dest=pdf_file)
    
    return not pisa_status.err

def ensure_pandoc():
    """
    Ensure pandoc is available by either finding an existing installation
    or downloading it automatically.
    
    Returns:
        bool: True if pandoc is available, False otherwise
    """
    try:
        pypandoc.ensure_pandoc_installed()
        print("✓ Pandoc is ready!")
        return True
    except Exception as e:
        print(f"! Pandoc not found: {e}")
        print("Attempting to download pandoc automatically...")
        try:
            pypandoc.download_pandoc()
            print("✓ Pandoc downloaded successfully!")
            return True
        except Exception as e2:
            print(f"✗ Failed to download pandoc: {e2}")
            print("\nPlease install pandoc manually:")
            print("- Visit: https://pandoc.org/installing.html")
            print("- Or run: conda install -c conda-forge pandoc")
            return False

def convert_files(input_pattern, output_format='docx', input_format=None, force_pandoc=False, font_name=None, debug=False):
    """
    Convert files matching the input pattern to the specified format.
    
    Args:
        input_pattern (str): File pattern to match (e.g., "*.md", "file.txt")
        output_format (str): Target format for conversion (default: 'docx')
        input_format (str, optional): Explicit input format for pandoc.
        force_pandoc (bool): Skip xhtml2pdf and use raw pandoc for PDF.
    """
    if not ensure_pandoc():
        print("Cannot proceed without pandoc")
        return
    
    files = glob.glob(input_pattern) if any(c in input_pattern for c in "*?[") else [input_pattern]
    
    if not any(Path(f).is_file() for f in files):
        print(f"No files found matching pattern: {input_pattern}")
        return
    
    print(f"Found {len(files)} files to convert")
    if debug:
        print(f"  [debug] input_pattern={input_pattern}")
        print(f"  [debug] output_format={output_format}")
        print(f"  [debug] input_format={input_format}")
        print(f"  [debug] force_pandoc={force_pandoc}")
        print(f"  [debug] font_name={font_name}")
    
    # Expanded list of common extensions. The '--from' flag is the true catch-all.
    supported_extensions = {
        '.md', '.markdown', '.txt', '.html', '.htm', '.rst', '.tex', '.latex',
        '.doc', '.docx', '.odt', '.rtf', '.epub', '.opml', '.org', '.wiki', '.textile'
    }
    
    # Mapping for ambiguous extensions to default Pandoc formats
    format_map = {
        '.txt': 'markdown',
    }
    
    converted_count = 0
    failed_count = 0
    
    for file_path_str in files:
        _tmp_files_to_clean = []
        try:
            file_path = Path(file_path_str)
            
            if not file_path.exists() or not file_path.is_file():
                print(f"Skipping non-existent file or directory: {file_path}")
                continue

            # If an input format is NOT specified via command line, we check our default list.
            if not input_format and file_path.suffix.lower() not in supported_extensions:
                print(f"Skipping unsupported file type: {file_path}. Use '--from <format>' to force conversion.")
                continue
            
            output_filename = file_path.with_suffix(f'.{output_format}')

            # Determine format specifier and markdown status early so we can
            # route PDF correctly before deciding whether to use xhtml2pdf.
            format_specifier = input_format  # Prioritize user-provided format
            if not format_specifier:
                format_specifier = format_map.get(file_path.suffix.lower())
            if format_specifier:
                print(f"  → Explicitly using input format: '{format_specifier}'")

            is_markdown_input = (
                is_markdown_format(format_specifier)
                or (format_specifier is None and file_path.suffix.lower() in ('.md', '.markdown'))
            )

            # xhtml2pdf cannot load system fonts by name, so always use the
            # Pandoc/XeLaTeX path for markdown → PDF (font is applied via -V mainfont).
            # xhtml2pdf is only used for non-markdown sources (e.g. DOCX → PDF).
            use_xhtml2pdf = (
                output_format.lower() == 'pdf'
                and not force_pandoc
                and not is_markdown_input
            )

            if use_xhtml2pdf:
                print(f"Converting {file_path.name} to {output_filename.name} using xhtml2pdf...")
                try:
                    if convert_to_pdf_lib(file_path, output_filename, input_format, font_name=font_name):
                        print(f"  ✓ Success")
                        converted_count += 1
                        continue
                    else:
                        print(f"  ✗ xhtml2pdf failed, falling back to Pandoc...")
                except Exception as e:
                    print(f"  ! Library conversion skipped: {e}")
                    print(f"  → Falling back to Pandoc (requires system PDF engine)...")

            extra_args = []

            if is_markdown_input:
                _active_font = font_name or DEFAULT_MARKDOWN_FONT
                _fmt = output_format.lower()

                if _fmt == 'pdf':
                    _engine, _fontspec = detect_pdf_engine()
                    if _engine is None:
                        # No LaTeX/HTML-PDF engine found at all — fall back to
                        # xhtml2pdf with the font embedded so it actually renders.
                        print(f"  * No PDF engine found (xelatex/lualatex/pdflatex/wkhtmltopdf).")
                        print(f"  → Falling back to xhtml2pdf (install XeLaTeX for best font support).")
                        if convert_to_pdf_lib(file_path, output_filename, input_format, font_name=_active_font):
                            converted_count += 1
                            print(f"  ✓ Success")
                            continue
                        else:
                            raise RuntimeError("xhtml2pdf fallback also failed.")
                    extra_args.append(f'--pdf-engine={_engine}')
                    if _fontspec:
                        extra_args.extend([
                            '-V', f'mainfont={_active_font}',
                            '-V', f'sansfont={_active_font}',
                            '-V', f'monofont={_active_font}',
                        ])
                    else:
                        # pdflatex / wkhtmltopdf / weasyprint — fontspec unavailable.
                        # Use lmodern (best pdflatex match for CM fonts) and warn.
                        extra_args.extend(['-V', 'fontfamily=lmodern'])
                        print(f"  * {_engine} does not support system fonts.")
                        print(f"  → Using lmodern (Computer Modern) as a substitute.")
                        print(f"  → Install XeLaTeX or LuaLaTeX for exact CMU Serif output.")
                elif _fmt == 'docx':
                    reference_path = Path(__file__).with_name('pandoc_reference.docx')
                    reference_path = ensure_reference_docx(reference_path, _active_font)
                    extra_args.extend(['--reference-doc', str(reference_path)])
                elif _fmt in ('html', 'html5', 'html4', 'chunkedhtml'):
                    import tempfile
                    css = (
                        "body, p, li, td, th, blockquote, pre, code {\n"
                        f"  font-family: '{_active_font}', serif;\n"
                        "}\n"
                    )
                    tmp_css = tempfile.NamedTemporaryFile(
                        mode='w', suffix='.css', delete=False, encoding='utf-8'
                    )
                    tmp_css.write(css)
                    tmp_css.close()
                    _tmp_files_to_clean.append(tmp_css.name)
                    extra_args.extend(['--standalone', '--css', tmp_css.name])
                elif _fmt in ('epub', 'epub2', 'epub3'):
                    import tempfile
                    css = (
                        "body, p, li, td, th, blockquote {\n"
                        f"  font-family: '{_active_font}', serif;\n"
                        "}\n"
                    )
                    tmp_css = tempfile.NamedTemporaryFile(
                        mode='w', suffix='.css', delete=False, encoding='utf-8'
                    )
                    tmp_css.write(css)
                    tmp_css.close()
                    _tmp_files_to_clean.append(tmp_css.name)
                    extra_args.extend(['--css', tmp_css.name])
                elif _fmt == 'odt':
                    print(f"  * ODT: font embedding not supported via Pandoc -- set default font in LibreOffice.")

            if debug:
                print(f"  [debug] file={file_path}")
                print(f"  [debug] ext={file_path.suffix.lower()}")
                print(f"  [debug] format_specifier={format_specifier}")
                print(f"  [debug] is_markdown_input={is_markdown_input}")
                print(f"  [debug] output_filename={output_filename}")
                print(f"  [debug] extra_args={extra_args}")
                if output_format.lower() == 'docx' and is_markdown_input:
                    print(f"  [debug] reference_doc={reference_path}")

            print(f"Converting {file_path.name} to {output_filename.name}...")
            pypandoc.convert_file(
                str(file_path),
                output_format,
                format=format_specifier,
                outputfile=str(output_filename),
                extra_args=extra_args
            )
            
            converted_count += 1
            print(f"  ✓ Success")

        except Exception as e:
            print(f"  ✗ Failed to convert {file_path_str}: {str(e)}")
            failed_count += 1

        finally:
            for _tmp in _tmp_files_to_clean:
                try:
                    Path(_tmp).unlink(missing_ok=True)
                except Exception:
                    pass
    
    print(f"\nConversion complete!")
    print(f"Successfully converted: {converted_count}")
    print(f"Failed: {failed_count}")

def show_help():
    """Display help information."""
    help_text = """
Pandoc Batch Converter v2.0
===========================

Usage: python pandoc_converter.py [input_pattern] [output_format] [options]

Arguments:
  input_pattern    Pattern to match input files (use quotes for wildcards)
  output_format    Target format (docx, pdf, html, etc.) - default: docx

Options:
  -f, --from [format]    Explicitly specify the input format (e.g., markdown, latex, html, rtf)
  -p, --pandoc           Force use of Pandoc for PDF (requires system PDF engine)
  --font [name]          Set default font for Markdown conversions (PDF/DOCX)
  --debug                Verbose debug output for conversion decisions
  -h, --help             Show this help message

Examples:
  python pandoc_converter.py "*.md" docx               # Convert all .md files to .docx
  python pandoc_converter.py "report.md" pdf           # Convert MD to PDF using xhtml2pdf
  python pandoc_converter.py "book.docx" pdf           # Convert DOCX to PDF (hybrid pipeline)
  python pandoc_converter.py "paper.md" pdf --pandoc   # Force Pandoc (requires LaTeX/etc)
"""
    print(help_text)

def main():
    """Main function to handle command line arguments and start conversion."""
    args = sys.argv[1:]
    
    if not args or '-h' in args or '--help' in args:
        show_help()
        return

    input_pattern = args.pop(0)
    output_format = 'docx'
    input_format = None
    force_pandoc = False
    font_name = DEFAULT_MARKDOWN_FONT
    debug = False
    
    # Check if output_format is provided and it's not a flag
    if args and not args[0].startswith('-'):
        candidate = args.pop(0)
        # "pandoc" is not a format — treat it as shorthand for the --pandoc flag
        if candidate.lower() == 'pandoc':
            force_pandoc = True
        else:
            output_format = candidate
        
    # Manual flag parsing
    if '-f' in args:
        idx = args.index('-f')
        if len(args) > idx + 1: input_format = args[idx+1]
    elif '--from' in args:
        idx = args.index('--from')
        if len(args) > idx + 1: input_format = args[idx+1]
    
    if '--font' in args:
        idx = args.index('--font')
        if len(args) > idx + 1: font_name = args[idx+1]

    if '--debug' in args:
        debug = True

    if '-p' in args or '--pandoc' in args:
        force_pandoc = True

    convert_files(input_pattern, output_format, input_format, force_pandoc, font_name=font_name, debug=debug)

if __name__ == "__main__":
    main()