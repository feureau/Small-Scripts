#!/usr/bin/env python3
import sys
import os
import glob
import argparse
from pathlib import Path
import tempfile
import textwrap
import traceback
try:
    from weasyprint import HTML
except Exception:  # handled at runtime
    HTML = None

DEFAULT_FONT_FALLBACKS = [
    "MS Mincho",
    "Hiragino Mincho ProN",
    "Yu Gothic",
    "YuGothic",
    "Meiryo",
    "MS Gothic",
    "MS PGothic",
    "Noto Sans CJK JP",
    "Noto Sans JP",
    "sans-serif",
]

DEFAULT_WINDOWS_FONT_CANDIDATES = [
    r"C:\Windows\Fonts\ Pro L.otf",
    r"C:\Windows\Fonts\EVA-Matisse_Standard.ttf",
    r"C:\Windows\Fonts\EVA-Matisse_Classic.ttf",
    r"C:\Windows\Fonts\meiryo.ttf",
    r"C:\Windows\Fonts\msgothic.ttf",
    r"C:\Windows\Fonts\YuGothM.ttf",
    r"C:\Windows\Fonts\YuGothR.ttf",
    r"C:\Windows\Fonts\yugothic.ttf",
    r"C:\Windows\Fonts\NotoSansCJKjp-Regular.otf",
    r"C:\Windows\Fonts\NotoSansJP-Regular.ttf",
]

DEFAULT_WINDOWS_FONT_BOLD_CANDIDATES = [
    r"C:\Windows\Fonts\ Pro B.otf",
    r"C:\Windows\Fonts\Pro B.otf",
]

def find_default_font_file():
    pro = [
        r"C:\Windows\Fonts\ Pro L.otf",
        r"C:\Windows\Fonts\Pro L.otf",
    ]
    pro += glob.glob(r"C:\Windows\Fonts\*Pro L.otf")
    for p in pro:
        if os.path.isfile(p):
            return p
    matisse = [
        r"C:\Windows\Fonts\EVA-Matisse_Standard.ttf",
        r"C:\Windows\Fonts\EVA-Matisse_Classic.ttf",
    ]
    matisse += glob.glob(r"C:\Windows\Fonts\*Matisse*.ttf")
    matisse += glob.glob(r"C:\Windows\Fonts\*Matisse*.otf")
    for p in matisse:
        if os.path.isfile(p):
            return p
    for p in DEFAULT_WINDOWS_FONT_CANDIDATES:
        if os.path.isfile(p):
            return p
    return None

def find_default_bold_font_file():
    for p in DEFAULT_WINDOWS_FONT_BOLD_CANDIDATES:
        if os.path.isfile(p):
            return p
    for p in glob.glob(r"C:\Windows\Fonts\*Pro B.otf"):
        if os.path.isfile(p):
            return p
    return None

def build_style_block(font_path, font_name, bold_font_path, extra_css, force_font=False):
    parts = []

    family = [f"'{f}'" for f in DEFAULT_FONT_FALLBACKS]
    if font_path:
        font_uri = Path(font_path).resolve().as_uri()
        parts.append(
            "@font-face {"
            f" font-family: '{font_name}';"
            f" src: url('{font_uri}');"
            " font-weight: normal;"
            "}"
        )
        if bold_font_path:
            bold_uri = Path(bold_font_path).resolve().as_uri()
            parts.append(
                "@font-face {"
                f" font-family: '{font_name}';"
                f" src: url('{bold_uri}');"
                " font-weight: bold;"
                "}"
            )
        family = [f"'{font_name}'"] + family
    if force_font and font_path:
        parts.append(f"* {{ font-family: '{font_name}' !important; }}")
    else:
        parts.append(f"body {{ font-family: {', '.join(family)}; }}")

    if extra_css:
        parts.append(extra_css)

    return "<style>\n" + "\n".join(parts) + "\n</style>\n"

def inject_style(html_text, style_block):
    lower = html_text.lower()
    idx = lower.find("<head>")
    if idx != -1:
        insert_at = idx + len("<head>")
        return html_text[:insert_at] + "\n" + style_block + html_text[insert_at:]
    return style_block + html_text

def convert_html_to_pdf(file_patterns, font_path=None, font_bold_path=None, font_name="Matisse Pro", css_path=None, auto_font=True, force_font=False, auto_force_font=True, log_path=None):
    # 1. Collect all files based on patterns
    files_to_process = []
    for pattern in file_patterns:
        # glob expands the wildcard pattern for Windows terminals
        matches = glob.glob(pattern)
        if not matches:
            print(f"Warning: No files found matching pattern '{pattern}'")
        files_to_process.extend(matches)

    files_to_process = sorted(list(set(files_to_process)))

    if not files_to_process:
        print("No files to process.")
        return

    def log(msg):
        print(msg)
        if log_path:
            try:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(msg + "\n")
            except Exception:
                pass

    log(f"Found {len(files_to_process)} files. Starting conversion...\n")

    if HTML is not None and os.name == "nt":
        if not os.environ.get("FONTCONFIG_FILE"):
            temp_dir = Path(tempfile.gettempdir())
            fc_path = temp_dir / "fontconfig-weasyprint.xml"
            if not fc_path.exists():
                fc_xml = textwrap.dedent(
                    """\
                    <?xml version="1.0"?>
                    <!DOCTYPE fontconfig SYSTEM "fonts.dtd">
                    <fontconfig>
                      <dir>C:/Windows/Fonts</dir>
                      <cachedir>"""
                    + temp_dir.as_posix()
                    + """</cachedir>
                    </fontconfig>
                    """
                )
                try:
                    fc_path.write_text(fc_xml, encoding="utf-8")
                except Exception as e:
                    log(f" [WARN] Failed to write fontconfig file: {e}")
            os.environ["FONTCONFIG_FILE"] = str(fc_path)
            os.environ.setdefault("FONTCONFIG_PATH", str(temp_dir))

    chosen_font = None
    chosen_bold_font = None
    if font_path:
        chosen_font = font_path
    elif auto_font:
        chosen_font = find_default_font_file()

    if font_bold_path:
        chosen_bold_font = font_bold_path
    elif auto_font:
        chosen_bold_font = find_default_bold_font_file()

    if chosen_font:
        log(f"Using font: {chosen_font}")
    else:
        log("No font file selected. Using CSS fallbacks only.")
    if chosen_bold_font:
        log(f"Using bold font: {chosen_bold_font}")
    extra_css = None
    if css_path:
        with open(css_path, "r", encoding="utf-8") as f:
            extra_css = f.read()

    # 2. Process files
    for input_file in files_to_process:
        base_name = os.path.splitext(input_file)[0]
        output_file = f"{base_name}.pdf"

        log(f"Converting: {input_file} -> {output_file}")
        
        try:
            if HTML is None:
                raise RuntimeError("WeasyPrint is not installed. Run: pip install weasyprint")

            with open(input_file, "r", encoding="utf-8") as source_html:
                html_text = source_html.read()

            html_lower = html_text.lower()
            has_font_family = "font-family" in html_lower
            if extra_css and "font-family" in extra_css.lower():
                has_font_family = True

            effective_force_font = force_font or (auto_force_font and not has_font_family)
            if effective_force_font and not force_font:
                log(" [INFO] No font-family found in HTML/CSS; forcing selected font.")

            style_block = build_style_block(
                chosen_font,
                font_name,
                chosen_bold_font,
                extra_css,
                force_font=effective_force_font,
            )
            html_text = inject_style(html_text, style_block)

            HTML(string=html_text, base_url=str(Path(input_file).parent)).write_pdf(output_file)

            size_bytes = os.path.getsize(output_file) if os.path.exists(output_file) else 0
            if size_bytes == 0:
                log(f" [ERROR] Output PDF is 0 bytes: {output_file}")
            else:
                log(f" [OK] Saved {output_file}")

        except Exception as e:
            log(f" [EXCEPTION] Error converting {input_file}: {e}")
            tb = traceback.format_exc()
            log(tb)

    log("\nProcessing complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert HTML to PDF with better CJK font handling.")
    parser.add_argument("patterns", nargs="+", help="File pattern(s) for input HTML (e.g., *.html)")
    parser.add_argument("--font", dest="font_path", help="Path to a TTF/OTF font file for Japanese text")
    parser.add_argument("--font-name", default="Matisse Pro", help="Font name to reference in CSS")
    parser.add_argument("--font-bold", dest="font_bold_path", help="Path to a bold TTF/OTF font file")
    parser.add_argument("--css", dest="css_path", help="Optional CSS file to inject into HTML")
    parser.add_argument("-f", "--force-font", action="store_true", help="Force the selected font on all elements")
    parser.add_argument("--auto-font", dest="auto_font", action="store_true", help="Enable auto-pick of a Windows font file (default)")
    parser.add_argument("--no-auto-font", dest="auto_font", action="store_false", help="Disable auto font detection")
    parser.add_argument("--auto-force-font", dest="auto_force_font", action="store_true", help="Force selected font if HTML/CSS has no font-family (default)")
    parser.add_argument("--no-auto-force-font", dest="auto_force_font", action="store_false", help="Disable auto force-font behavior")
    parser.add_argument("--log", dest="log_path", help="Write verbose logs to this file")
    parser.set_defaults(auto_font=True, auto_force_font=True)
    args = parser.parse_args()

    convert_html_to_pdf(
        args.patterns,
        font_path=args.font_path,
        font_bold_path=args.font_bold_path,
        font_name=args.font_name,
        css_path=args.css_path,
        auto_font=args.auto_font,
        force_font=args.force_font,
        auto_force_font=args.auto_force_font,
        log_path=args.log_path,
    )
