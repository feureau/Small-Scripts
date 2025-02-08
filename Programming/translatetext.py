#!/usr/bin/env python3

import subprocess
import sys
import os
import glob
import argparse
import re
import json

# --- Configuration ---
DEFAULT_TARGET_LANGUAGE = "en"
DEFAULT_OLLAMA_MODEL = "llama3.2:3b"
DEFAULT_SUFFIX = "_translated"
OUTPUT_SUBFOLDER = "translated_output"
# --- End Configuration ---


def translate_text(text, target_language, ollama_model):
    """Translates text using Ollama with a simplified prompt.

    Args:
        text: The text to translate.
        target_language: The target language code.
        ollama_model: The Ollama model to use.

    Returns:
        The translated text, or None if an error occurred.
    """
    try:
        # Simplified Prompt:  Directly ask for translation.
        prompt = f"Translate this French text to {target_language}: {text}" # Assuming source is French

        # Construct the Ollama command.
        command = [
            "ollama",
            "run",
            ollama_model,
            json.dumps({"prompt": prompt, "format": "json"}),
        ]

        # Run Ollama and capture output.
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding='utf-8',
            check=True
        )

        raw_output = process.stdout.strip()
        translated_text = raw_output.strip('"') # Keep quote stripping for safety

        if not translated_text:
            print(f"Warning: No translated text from Ollama. Raw output: '{raw_output[:100]}...'", file=sys.stderr)
            return None

        return translated_text

    except subprocess.CalledProcessError as e:
        print(f"Error running Ollama: {e}", file=sys.stderr)
        print(f"Ollama output (stderr): {e.stderr.decode('utf-8', errors='ignore')}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        return None


def main():
    parser = argparse.ArgumentParser(description="Translate text files using Ollama.")
    parser.add_argument("files", nargs="+", help="Path(s) to the text file(s) to translate.")
    parser.add_argument("-t", "--target", default=DEFAULT_TARGET_LANGUAGE, help=f"Target language code (e.g., en, es, fr). Default: {DEFAULT_TARGET_LANGUAGE}")
    parser.add_argument("-m", "--model", default=DEFAULT_OLLAMA_MODEL, help=f"Ollama model to use. Default: {DEFAULT_OLLAMA_MODEL}")
    parser.add_argument("-o", "--output", default=None, help="Output directory (overrides subfolder). If not specified, translated files are placed in '{OUTPUT_SUBFOLDER}' subfolder.")
    parser.add_argument("-s", "--suffix", default=DEFAULT_SUFFIX, help=f"Suffix to add to the translated file name. Default: {DEFAULT_SUFFIX}")

    args = parser.parse_args()

    if not args.files:
        print("Error: No files specified.", file=sys.stderr)
        sys.exit(1)

    all_files = []
    for file_pattern in args.files:
       all_files.extend(glob.glob(file_pattern))

    if not all_files:
        print(f"Error: No files found matching the pattern(s).", file=sys.stderr)
        sys.exit(1)

    # Determine output directory
    if args.output:
        output_dir = args.output
    else:
        output_dir = OUTPUT_SUBFOLDER

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    for file_path in all_files:
        if not file_path.lower().endswith(".txt"):
            print(f"Skipping non-txt file: {file_path}", file=sys.stderr)
            continue

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()

            translated_text = translate_text(text, args.target, args.model)

            if translated_text:
                base_name = os.path.basename(file_path)
                name, ext = os.path.splitext(base_name)
                output_file_path = os.path.join(output_dir, f"{name}{args.suffix}{ext}")

                with open(output_file_path, "w", encoding="utf-8") as outfile:
                    outfile.write(translated_text)
                print(f"Translated '{file_path}' -> '{output_file_path}'")

        except FileNotFoundError:
            print(f"Error: File not found: {file_path}", file=sys.stderr)
        except Exception as e:
            print(f"Error processing {file_path}: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()