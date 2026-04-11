#!/usr/bin/env python3
"""
xmlmerge.py – Recursively merge all XML files in the current working directory.

Usage:
    python xmlmerge.py [--output OUTPUT] [--wrapper WRAPPER] [--pattern PATTERN]

Default behaviour:
    - Searches for *.xml files in current directory and subdirectories.
    - Combines their root elements under a <merged_files> root.
    - Saves the result as merged_output.xml.

Requirements:
    Python 3.x (standard library only)
"""

import os
import sys
import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

def find_xml_files(base_dir, pattern="*.xml"):
    """Yield all files matching the given pattern recursively from base_dir."""
    base = Path(base_dir).resolve()
    for file_path in base.rglob(pattern):
        if file_path.is_file():
            yield file_path

def merge_xml_files(file_paths, wrapper_tag="merged_files"):
    """
    Parse each XML file and append its root element as a child of a new wrapper root.

    Args:
        file_paths: iterable of Path objects pointing to XML files.
        wrapper_tag: name of the wrapper root element.

    Returns:
        ElementTree object of the merged content.
    """
    root = ET.Element(wrapper_tag)

    for xml_file in file_paths:
        try:
            tree = ET.parse(xml_file)
            file_root = tree.getroot()
            # Optionally add an attribute to remember the source file
            file_root.set("source", str(xml_file))
            root.append(file_root)
            print(f"[+] Merged: {xml_file}")
        except ET.ParseError as e:
            print(f"[!] Skipping {xml_file} – Parse error: {e}", file=sys.stderr)
        except Exception as e:
            print(f"[!] Skipping {xml_file} – Error: {e}", file=sys.stderr)

    return ET.ElementTree(root)

def main():
    parser = argparse.ArgumentParser(
        description="Recursively merge XML files from the current working directory."
    )
    parser.add_argument(
        "--output", "-o",
        default="merged_output.xml",
        help="Output filename (default: merged_output.xml)"
    )
    parser.add_argument(
        "--wrapper", "-w",
        default="merged_files",
        help="Wrapper root element name (default: merged_files)"
    )
    parser.add_argument(
        "--pattern", "-p",
        default="*.xml",
        help="File pattern to match (default: *.xml)"
    )
    args = parser.parse_args()

    # Current working directory is where the script was called from
    base_dir = Path.cwd()
    print(f"Searching for '{args.pattern}' in {base_dir} ...")

    xml_files = list(find_xml_files(base_dir, args.pattern))
    if not xml_files:
        print("No XML files found. Exiting.")
        sys.exit(1)

    print(f"Found {len(xml_files)} file(s). Merging...")

    merged_tree = merge_xml_files(xml_files, args.wrapper)

    output_path = base_dir / args.output
    merged_tree.write(output_path, encoding="utf-8", xml_declaration=True)
    print(f"✅ Merged XML written to: {output_path}")

if __name__ == "__main__":
    main()