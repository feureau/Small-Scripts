
#!/usr/bin/env python3

r"""
================================================================================
 SCRIPT NAME: Advanced Text File Merger
 VERSION: 4.2 (Natural Sorting Fix)
 AUTHOR: Contributor (Patched by ChatGPT, Refactored by Gemini)
 DATE: December 13, 2025
================================================================================

PURPOSE & DESCRIPTION:
----------------------
This script merges multiple text-based files (e.g., .txt, .srt, .md, .log)
into a single, consolidated output file.

NEW IN V4.2:
- Fixed sorting logic. Now uses "Natural Sorting" (alphanumeric split) instead
  of just looking at the last number. This fixes issues where files ending in
  "(1).txt" were incorrectly sorted to the top.
- Fixed SyntaxWarning regarding escape sequences in documentation.

--------------------------------------------------------------------------------
CORE FEATURES:
--------------------------------------------------------------------------------
-   Natural Sorting: Sorts filenames like a human would (e.g., "File 9" comes
    before "File 10", and "Chapter 109 (1)" follows "Chapter 109").
-   Content Sanitization: Automatically removes Markdown code fences
    (e.g., ```text ... ```) that often wrap LLM-generated text.
-   Linebreak & Hyphenation Stripping: Can reflow paragraphs by removing
    mid-sentence line breaks and automatically joining hyphenated words.
-   Customizable Markers: Can insert distinct markers around content.

--------------------------------------------------------------------------------
COMMAND-LINE ARGUMENTS:
--------------------------------------------------------------------------------
-   `file_patterns` (Required): One or more glob patterns.
    Example: `"*.txt" "chapter-*.md"`

-   `-o, --output` (Optional): Output filename.
    Example: `-o "final_document.md"`

-   `-lb, --linebreak` (Optional): Inserts an extra blank line between files.

-   `-r, --recursive` (Optional): Scans subdirectories for matching files.

-   `-strip, --strip` (Optional): Removes single line breaks within paragraphs
    and de-hyphenates words.

-   `-m, --markers` (Optional): Inserts headers/footers around file content.

-   `--no-remove-strings` (Optional): Disables markdown code fence removal.

--------------------------------------------------------------------------------
CONFIGURATION VARIABLES:
--------------------------------------------------------------------------------
-   `MARKER_CHAR`: Character for marker lines (default "=").
-   `MARKER_LENGTH`: Length of marker lines.
-   `START_MARKER_FORMAT`: Template for start marker.
-   `END_MARKER_FORMAT`: Template for end marker.

--------------------------------------------------------------------------------
FUNCTION REFERENCE:
--------------------------------------------------------------------------------
-   `get_numerical_sort_key(filename)`:
    Splits a filename into text and numeric chunks to perform natural sorting.

-   `sanitize_api_response(text)`:
    Cleans text by removing Markdown fences.

-   `merge_text_files(...)`:
    Main orchestration function.
================================================================================
"""

import sys
import glob
import os
import argparse
import re

#================================================================================
# SCRIPT CONFIGURATION
#================================================================================
# --- Section Marker Settings (for -m/--markers flag) ---
MARKER_CHAR = "="
MARKER_LENGTH = 50
START_MARKER_FORMAT = f"\n{MARKER_CHAR * MARKER_LENGTH}\n>> START: {{filename}}\n{MARKER_CHAR * MARKER_LENGTH}\n"
END_MARKER_FORMAT = f"\n{MARKER_CHAR * MARKER_LENGTH}\n>> END OF LINE: {{filename}}\n{MARKER_CHAR * MARKER_LENGTH}\n"

# --- Default Output Settings ---
DEFAULT_OUTPUT_BASENAME = "merged_output"
DEFAULT_OUTPUT_EXTENSION = "txt"

# --- Default Plaintext Extensions (used when no file patterns provided) ---
DEFAULT_PLAINTEXT_EXTENSIONS = [
    "txt", "json", "md", "srt", "log", "csv", "xml", "yaml", "yml",
    "ini", "cfg", "conf", "html", "htm", "css", "js", "py", "sh", "bat"
]
#================================================================================


def get_numerical_sort_key(filename):
    """
    Generates a key for 'Natural Sorting'.
    Splits the filename into a list of integers and lowercase strings.
    This ensures that 'file2.txt' comes before 'file10.txt', and
    'Vol 1 (1).txt' comes after 'Vol 1.txt' if logically appropriate.
    """
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split(r'(\d+)', filename)]


def process_footnotes(content, global_state):
    """
    Detects, re-indexes, and collects Markdown-style footnotes.
    global_state: dict with 'footnotes' (list) and 'next_id' (int)
    """
    local_mapping = {}
    
    # Pattern for footnote definitions: [^id]: content
    # Supports multi-line definitions if subsequent lines are indented.
    def_pattern = re.compile(r'^\[\^([^\]]+)\]:\s*(.*(?:\n {1,4}.*)*)', re.MULTILINE)
    
    # Collect definitions and map to new global IDs
    def collect_def(match):
        orig_id = match.group(1)
        orig_content = match.group(2).strip()
        if orig_id not in local_mapping:
            new_id = str(global_state['next_id'])
            global_state['next_id'] += 1
            local_mapping[orig_id] = new_id
            global_state['footnotes'].append(f"[^{new_id}]: {orig_content}")
        return ""

    # 1. Remove definitions from text and collect them
    processed_content = def_pattern.sub(collect_def, content)
    
    # 2. If no footnotes found, return original content
    if not local_mapping:
        return content, False

    # Remove now-redundant footnote section headings left behind after
    # extracting footnote definitions.
    processed_content = re.sub(
        r'(?im)^[ \t]*#{1,6}[ \t]*footnotes?[ \t]*$',
        '',
        processed_content
    )

    # 3. Replace references in text using the local mapping
    ref_pattern = re.compile(r'\[\^([^\]]+)\](?!=:)')
    
    def replace_ref(match):
        orig_id = match.group(1)
        if orig_id in local_mapping:
            return f"[^{local_mapping[orig_id]}]"
        return match.group(0)

    processed_content = ref_pattern.sub(replace_ref, processed_content)
    
    # Cleanup whitespace left by removed definitions/headings
    processed_content = re.sub(r'\n{3,}', '\n\n', processed_content).rstrip()
    
    return processed_content, True


def sanitize_api_response(text):
    """Removes Markdown code fences from the start and end of a string."""
    if not text:
        return ""
    pattern = re.compile(r"^\s*```[a-z]*\s*\n?(.*?)\n?\s*```\s*$", re.DOTALL)
    match = pattern.match(text.strip())
    if match:
        return match.group(1).strip()
    return text.strip()


def derive_output_basename(files_to_merge):
    """
    Derives a readable output base name from input filenames.
    Example:
      INDO_..._page-01.txt + INDO_..._page-02.txt -> INDO_...
    """
    stems = []
    for path in files_to_merge:
        name = os.path.basename(path)
        stem, _ = os.path.splitext(name)
        if stem:
            stems.append(stem)

    if not stems:
        return DEFAULT_OUTPUT_BASENAME

    # Character-level common prefix across all stems.
    common = os.path.commonprefix(stems).rstrip(" _-.()[]{}")
    if not common:
        return DEFAULT_OUTPUT_BASENAME

    # Remove trailing page/index token patterns if present.
    common = re.sub(
        r'([ _\-.]*(?:page|pg|p)\s*[-_\.]?\s*\d+)$',
        '',
        common,
        flags=re.IGNORECASE
    ).rstrip(" _-.()[]{}")
    common = re.sub(
        r'([ _\-.]*(?:page|pg|p))$',
        '',
        common,
        flags=re.IGNORECASE
    ).rstrip(" _-.()[]{}")

    return common or DEFAULT_OUTPUT_BASENAME


def derive_output_extension(files_to_merge, file_patterns):
    """
    Derives output extension from matched files, preferring the dominant type.
    Falls back to first pattern extension, then default extension.
    """
    ext_counts = {}
    for path in files_to_merge:
        _, ext = os.path.splitext(path)
        if ext:
            clean_ext = ext.lstrip(".").lower()
            ext_counts[clean_ext] = ext_counts.get(clean_ext, 0) + 1

    if ext_counts:
        # Pick the most frequent extension; ties are resolved alphabetically
        # for deterministic behavior.
        return sorted(ext_counts.items(), key=lambda item: (-item[1], item[0]))[0][0]

    if file_patterns:
        first_pattern = file_patterns[0]
        pattern_parts = first_pattern.split('.')
        if len(pattern_parts) > 1 and pattern_parts[-1] != '*':
            return pattern_parts[-1].lower()

    return DEFAULT_OUTPUT_EXTENSION


def merge_text_files(file_patterns, output_filename, add_linebreak=False, strip_linebreaks=False, remove_strings=True, add_markers=False, recursive=False, **kwargs):
    """Merges all text files matching the given patterns into a single output file."""
    try:
        all_files = set()
        for pattern in file_patterns:
            # If recursive is True and pattern doesn't already have recursive syntax, adapt it
            if recursive and '**' not in pattern:
                # Check if it's already a path-like pattern
                if os.path.sep in pattern or '/' in pattern:
                    # It's a path, but might need ** insertion
                    # This is a bit tricky, but simple strategy: replace last segment if it has wildcards
                    dirname, basename = os.path.split(pattern)
                    if '*' in basename:
                        pattern = os.path.join(dirname, '**', basename)
                else:
                    # It's just a glob like *.txt in current dir
                    pattern = os.path.join('**', pattern)

            matched_files = glob.glob(pattern, recursive=recursive)
            all_files.update(matched_files)

        files_to_merge = list(all_files)

        if not files_to_merge:
            print(f"No files found matching patterns: {file_patterns}")
            return

        default_output_file = f"{DEFAULT_OUTPUT_BASENAME}.{DEFAULT_OUTPUT_EXTENSION}"
        # Intelligent output naming if -o is not provided
        if output_filename == default_output_file:
            output_basename = derive_output_basename(files_to_merge)
            output_extension = derive_output_extension(files_to_merge, file_patterns)
            output_filename = f"{output_basename}.{output_extension}"

        # Apply Natural Sorting
        files_to_merge.sort(key=get_numerical_sort_key)

        # Ensure we don't try to merge the output file into itself
        if output_filename in files_to_merge:
            files_to_merge.remove(output_filename)

        print(f"Merging files in Natural Sort order:")
        for f in files_to_merge:
            print(f"  - {f}")
        print(f"Output file will be: {output_filename}\n")

        global_footnote_state = {'footnotes': [], 'next_id': 1}
        any_footnotes = False

        with open(output_filename, 'w', encoding='utf-8') as outfile:
            for filename in files_to_merge:
                try:
                    with open(filename, 'r', encoding='utf-8') as infile:
                        content = infile.read()

                        if remove_strings:
                            content = sanitize_api_response(content)

                        if strip_linebreaks:
                            # De-hyphenate words split across lines
                            while True:
                                original_content = content
                                # Use a more robust pattern for hyphenation at line breaks
                                content = re.sub(r'(\w)-\n(\w?)', r'\1\2', content, flags=re.MULTILINE)
                                if content == original_content:
                                    break
                            
                            # Reflow paragraphs
                            content = re.sub(r'\n{2,}', '\n\n', content)
                            content = re.sub(r'(?<!\n)\n(?!\n)', ' ', content)

                        # Handle footnotes if not explicitly disabled
                        if kwargs.get('merge_footnotes', True):
                            content, found = process_footnotes(content, global_footnote_state)
                            if found:
                                any_footnotes = True

                        if add_markers:
                            base_name = os.path.basename(filename)
                            outfile.write(START_MARKER_FORMAT.format(filename=base_name))

                        outfile.write(content)

                        if add_markers:
                            base_name = os.path.basename(filename)
                            outfile.write(END_MARKER_FORMAT.format(filename=base_name))

                        if add_linebreak:
                            outfile.write("\n\n")
                        else:
                            if not add_markers:
                                outfile.write("\n")

                    print(f"  ✓ Merged: {filename}")
                except Exception as e:
                    print(f"  ⚠ Error reading file: {filename} - {e}")

            # Append consolidated footnotes
            if any_footnotes:
                outfile.write("\n\n## Footnotes\n\n")
                outfile.write("\n".join(global_footnote_state['footnotes']))
                outfile.write("\n")

        print(f"\n✅ Successfully merged files into: {output_filename}")

    except Exception as e:
        print(f"❌ An error occurred: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Merge text files matching one or more patterns. "
                    "See the extensive documentation at the top of the script for full details.",
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument("file_patterns", nargs='*', help="One or more file patterns to match (e.g., '*.txt', 'chapter-*.md'). If not provided, processes all common plaintext files.")
    parser.add_argument("-o", "--output", default=f"{DEFAULT_OUTPUT_BASENAME}.{DEFAULT_OUTPUT_EXTENSION}", help="Name of the output file (default derives from first pattern).")
    parser.add_argument("-lb", "--linebreak", action="store_true", help="Add a blank line between merged files.")
    parser.add_argument("-r", "--recursive", action="store_true", help="Scan subdirectories for matching files.")
    parser.add_argument("-strip", "--strip", action="store_true", help="Strip linebreaks within paragraphs and join hyphenated words.")
    parser.add_argument("--no-remove-strings", action="store_false", dest="remove_strings", default=True, help="Disable markdown fence removal.")
    parser.add_argument("-m", "--markers", action="store_true", help="Add start and end markers for each merged file's content.")
    parser.add_argument("--no-merge-footnotes", action="store_false", dest="merge_footnotes", default=True, help="Disable automatic footnote re-indexing and consolidation.")

    args = parser.parse_args()

    # Use default plaintext extensions if no patterns provided
    if not args.file_patterns:
        args.file_patterns = [f"*.{ext}" for ext in DEFAULT_PLAINTEXT_EXTENSIONS]
        print(f"No file patterns specified. Using default plaintext extensions:")
        print(f"  {', '.join(DEFAULT_PLAINTEXT_EXTENSIONS)}\n")

    # Heuristic: If -o wasn't used, and we have multiple patterns, and the last pattern
    # doesn't look like a glob AND doesn't exist as a file, treat it as output.
    # This supports usage like: mergetext.py *.md output.md
    if args.output == f"{DEFAULT_OUTPUT_BASENAME}.{DEFAULT_OUTPUT_EXTENSION}" and len(args.file_patterns) >= 2:
        last_arg = args.file_patterns[-1]
        is_glob = any(char in last_arg for char in "*?[]")
        if not is_glob and not os.path.exists(last_arg):
            print(f"ℹ️  Implicit output detected: '{last_arg}' (treating as output file)")
            args.output = last_arg
            args.file_patterns.pop()

    merge_text_files(
        file_patterns=args.file_patterns,
        output_filename=args.output,
        add_linebreak=args.linebreak,
        strip_linebreaks=args.strip,
        remove_strings=args.remove_strings,
        add_markers=args.markers,
        recursive=args.recursive,
        merge_footnotes=args.merge_footnotes
    )
