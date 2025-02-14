import os
import sys
import glob
import re

# Define subfolder for processed text
OUTPUT_FOLDER = "striplinebreak_output"  # Updated output folder name
SUFFIX = "_processed"  # Suffix for output filenames

def process_text(text):
    """Processes text to remove unwanted line breaks while preserving structure."""

    # Normalize different hyphen types
    text = text.replace("–", "-").replace("—", "-")

    lines = text.split("\n")
    processed_lines = []
    buffer = []

    for line in lines:
        stripped = line.strip()

        # Preserve empty lines (paragraph breaks)
        if not stripped:
            if buffer:
                processed_lines.append(" ".join(buffer))  # Join buffered lines as a paragraph
                buffer = []
            processed_lines.append("")  # Preserve blank line for paragraph separation
            continue

        # Handle hyphenated words (merge them)
        if buffer and buffer[-1].endswith("-"):
            buffer[-1] = buffer[-1][:-1] + stripped  # Remove hyphen and merge words
        # Merge sentences correctly (avoid joining separate sentences)
        elif buffer and not buffer[-1].endswith((".", "!", "?", ":", ";")):
            buffer.append(stripped)  # Merge into sentence
        else:
            buffer.append(stripped)

    # Append remaining buffer
    if buffer:
        processed_lines.append(" ".join(buffer))

    # Preserve tables (lines that seem structured with spaces)
    final_text = []
    for i, line in enumerate(processed_lines):
        if i > 0 and re.match(r"^\s*\S+\s+\S+", line):  # Looks like a table row
            final_text.append(line)  # Keep line as is
        else:
            # Preserve multiple spaces within tables, but collapse excessive spaces elsewhere
            line = re.sub(r'(\S)  +(\S)', r'\1 \2', line)  # Preserve at least one space
            final_text.append(re.sub(r'\s+', ' ', line))  # Collapse excessive whitespace

    return "\n".join(line.rstrip() for line in final_text)  # Trim trailing spaces

def process_files(file_pattern):
    """Processes all matching text files and saves them in a subfolder."""

    # Get the working directory
    cwd = os.getcwd()

    # Create output directory
    output_dir = os.path.join(cwd, OUTPUT_FOLDER)
    os.makedirs(output_dir, exist_ok=True)

    # Find matching text files
    text_files = glob.glob(file_pattern)

    if not text_files:
        print("No text files found matching:", file_pattern)
        return

    print(f"Processing {len(text_files)} text files...")

    for txt_file in text_files:
        base_name, ext = os.path.splitext(os.path.basename(txt_file))
        output_file = os.path.join(output_dir, f"{base_name}{SUFFIX}{ext}")  # Add suffix to filename

        # Read and process text
        with open(txt_file, "r", encoding="utf-8") as f:
            text = f.read()

        cleaned_text = process_text(text)

        # Save the cleaned text
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(cleaned_text)

        print(f"Processed: {txt_file} -> {output_file}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python striplinebreaks.py <file_pattern>")
        sys.exit(1)

    file_pattern = sys.argv[1]
    process_files(file_pattern)
