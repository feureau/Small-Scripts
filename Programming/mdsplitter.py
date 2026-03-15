import argparse
import os
import re


def split_markdown(input_path, level):
    if not os.path.isfile(input_path):
        print(f"Error: File '{input_path}' not found. Skipping...")
        return

    # Create a subfolder for each file to avoid filename collisions during batching
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    output_dir = f"split_{base_name}"
    os.makedirs(output_dir, exist_ok=True)

    with open(input_path, "r", encoding="utf-8") as file:
        content = file.read()

    # Regex matches exactly the specified number of '#' at the start of a line
    pattern = rf"^(#{{{level}}}\s+.*)$"
    parts = re.split(pattern, content, flags=re.MULTILINE)

    intro = parts[0].strip()
    if intro:
        with open(
            os.path.join(output_dir, "00_intro.md"), "w", encoding="utf-8"
        ) as out_file:
            out_file.write(intro + "\n")

    chapter_num = 1
    for i in range(1, len(parts), 2):
        heading_line = parts[i]
        body = parts[i + 1] if i + 1 < len(parts) else ""

        # Clean heading for filename
        heading_text = heading_line.lstrip("#").strip()
        safe_name = re.sub(r'[\\/*?:"<>|]', "", heading_text)
        safe_name = safe_name.replace(" ", "_").lower()
        filename = f"{chapter_num:02d}_{safe_name}.md"

        output_path = os.path.join(output_dir, filename)
        with open(output_path, "w", encoding="utf-8") as out_file:
            out_file.write(heading_line + "\n" + body.lstrip("\n"))

        chapter_num += 1

    print(f"Processed '{input_path}' -> Files saved in '{output_dir}/'")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Split one or more Markdown files by a specific heading level."
    )
    # 'nargs="+"' allows passing multiple files (e.g., *.md)
    parser.add_argument(
        "files", nargs="+", help="One or more Markdown files to process."
    )
    parser.add_argument(
        "-l",
        "--level",
        type=int,
        default=1,
        choices=range(1, 7),
        help="Heading level to split at (1-6). Default is 1.",
    )

    args = parser.parse_args()

    for file_path in args.files:
        split_markdown(file_path, args.level)
