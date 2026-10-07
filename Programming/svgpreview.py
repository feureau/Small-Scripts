import os
import sys
import subprocess
import platform
import glob
from pathlib import Path

def generate_preview(svg_path):
    """
    Generates a high-resolution PNG preview of an SVG file using ImageMagick.
    """
    # Configuration
    # Try 'magick' from system PATH first, then fallback to a known hardcoded path
    MAGICK_COMMAND = "magick"
    FALLBACK_MAGICK_PATH = r"C:\Users\Feureau\AppData\Roaming\Tools\magick.exe"
    PREVIEWS_DIR = "_previews"
    DENSITY = "300"  # High resolution for mockup quality
    
    # Windows sometimes requires shell=True to resolve .cmd or .bat files (like magick)
    use_shell = platform.system() == "Windows"
    
    # Setup paths - resolve the input path relative to current working directory
    svg_file = Path(svg_path).resolve()
    if not svg_file.exists():
        print(f"Error: File {svg_file} not found.")
        return

    # Ensure _previews directory exists relative to the SVG file's parent
    # This means if the SVG is in the CWD, the folder is created in the CWD.
    output_dir = svg_file.parent / PREVIEWS_DIR
    output_dir.mkdir(exist_ok=True)
    
    # Define output filename (change .svg to .png)
    output_file = output_dir / f"{svg_file.stem}.png"
    
    print(f"Generating preview for: {svg_file.name}...")
    
    # Determine which magick executable to use
    magick_exe = MAGICK_COMMAND
    
    try:
        # Command: magick -density 300 -background none "input.svg" "output.png"
        cmd = [
            magick_exe,
            "-density", DENSITY,
            "-background", "none",
            str(svg_file),
            str(output_file)
        ]
        
        # Run ImageMagick
        subprocess.run(cmd, capture_output=True, text=True, check=True, shell=use_shell)
        print(f"Successfully saved to: {output_file}")
        
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        # If first attempt fails because 'magick' isn't in PATH, try fallback
        if magick_exe == MAGICK_COMMAND:
            print(f"System 'magick' not found or failed. Trying fallback path...")
            magick_exe = FALLBACK_MAGICK_PATH
            try:
                cmd = [
                    magick_exe,
                    "-density", DENSITY,
                    "-background", "none",
                    str(svg_file),
                    str(output_file)
                ]
                subprocess.run(cmd, capture_output=True, text=True, check=True, shell=use_shell)
                print(f"Successfully saved to: {output_file}")
                return # Success with fallback
            except Exception as fallback_e:
                print(f"Fallback also failed: {fallback_e}")
        else:
            print(f"Error during rendering: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python svgpreview.py \"YourFile.svg\" or \"*.svg\"")
        print("  - Single file: svgpreview.py filename.svg")
        print("  - Wildcard:   svgpreview.py *.svg (scans current directory)")
        sys.exit(1)
    
    target = sys.argv[1]
    
    # Check if it's a glob pattern with wildcards
    if '*' in target or '?' in target:
        print(f"Expanding pattern: {target}")
        matches = glob.glob(target)
        if not matches:
            print(f"No files matched the pattern: {target}")
            sys.exit(1)
        
        # Process all matching files
        for svg_path in matches:
            generate_preview(svg_path)
    else:
        # Single file mode (original behavior)
        generate_preview(target)
