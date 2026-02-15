import argparse
import os
import re


def split_markdown(file_path):
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found.")
        return

    # Extract the filename without the extension to use as a prefix
    # Example: "Knoerle's_Journal_NL.md" -> "Knoerle's_Journal_NL"
    file_prefix = os.path.splitext(os.path.basename(file_path))[0]

    print(f"Processing: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Split by Markdown headers (e.g., # Header)
    parts = re.split(r"^(#+ .*)$", content, flags=re.MULTILINE)

    initial_index = 0
    # Handle text appearing before the first header
    if parts and not parts[0].strip().startswith("#"):
        preamble = parts[0].strip()
        if preamble:
            preamble_name = f"{file_prefix}_00_preamble.md"
            with open(preamble_name, "w", encoding="utf-8") as f:
                f.write(preamble)
            print(f"Created: {preamble_name}")
        initial_index = 1

    # Iterate through headers and content
    for i in range(initial_index, len(parts), 2):
        header = parts[i].strip()
        body = parts[i + 1] if i + 1 < len(parts) else ""

        if not header:
            continue

        # Sanitize the header for a safe filename
        clean_header = re.sub(r"[^\w\s-]", "", header).strip().replace(" ", "_").lower()

        # Combine prefix and sanitized header
        filename = f"{file_prefix}_{clean_header[:50]}.md"

        with open(filename, "w", encoding="utf-8") as f:
            # We add a newline after the header to keep the structure clean
            f.write(header + "\n" + body)
        print(f"Created: {filename}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Split Markdown files by chapter headings with filename prefix."
    )
    parser.add_argument("files", nargs="+", help="Markdown files to process")

    args = parser.parse_args()

    for file in args.files:
        split_markdown(file)
