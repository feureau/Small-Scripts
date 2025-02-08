#!/usr/bin/env python3

import subprocess
import sys
import glob
import os
import argparse

# --- Default Configuration (Easily Editable Here) ---
DEFAULT_MODEL = "llama3.2:3b"  # Change this to your desired default Ollama model
DEFAULT_PROMPT = "Clean and correct the following text for grammar, spelling, and clarity. Return only the cleaned text, do not include notes or anything else." # Change this to your desired default prompt
DEFAULT_OUTPUT_SUBFOLDER = "cleaned_output" # Default subfolder name for cleaned files
OLLAMA_TIMEOUT_SECONDS = 60  # Timeout in seconds for Ollama command (adjust as needed)
# --- End Default Configuration ---


def is_ollama_model_available(model_name):
    """
    Checks if the specified Ollama model is available locally using 'ollama list'.

    Args:
        model_name (str): The name of the Ollama model to check.

    Returns:
        bool: True if the model is available, False otherwise.
    """
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            check=True # Raise an exception if ollama list command fails
        )
        models_output = result.stdout
        return model_name in models_output.lower() # Case-insensitive check

    except subprocess.CalledProcessError as e:
        print(f"Error checking Ollama models: {e}")
        print(f"Ollama 'list' command stderr: {e.stderr}")
        return False # Assume model is not available if there's an error
    except FileNotFoundError:
        print("Error: Ollama command not found. Make sure Ollama is installed and in your PATH.")
        return False
    except Exception as e:
        print(f"An unexpected error occurred while checking Ollama models: {e}")
        return False


def cleanup_text_with_ollama(text_content, prompt, model=DEFAULT_MODEL):
    """
    Sends text content to Ollama with a custom prompt and model for cleanup.

    Args:
        text_content (str): The text content to be cleaned up.
        prompt (str): The prompt to guide Ollama for cleanup.
        model (str): The Ollama model to use (default: DEFAULT_MODEL - defined at the top).

    Returns:
        str: The cleaned text content from Ollama, or None if there was an error.
    """
    try:
        ollama_command = [
            "ollama", "run", model,
            prompt
        ]

        process = subprocess.Popen(
            ollama_command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding='utf-8'  # Explicitly set encoding to UTF-8 for subprocess
        )

        try:
            stdout, stderr = process.communicate(input=text_content, timeout=OLLAMA_TIMEOUT_SECONDS) # Added timeout
        except subprocess.TimeoutExpired:
            process.kill() # Terminate Ollama process if timeout occurs
            print(f"Error: Ollama command timed out after {OLLAMA_TIMEOUT_SECONDS} seconds.")
            return None


        if process.returncode == 0:
            # Ollama might add extra newlines or formatting, you might want to trim it
            cleaned_text = stdout.strip()
            return cleaned_text
        else:
            print(f"Error running Ollama: (Return Code: {process.returncode})")
            print(f"Ollama stderr: {stderr}") # Print stderr for more detailed Ollama errors
            return None  # Indicate an error occurred

    except FileNotFoundError:
        print("Error: Ollama command not found. Make sure Ollama is installed and in your PATH.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

def process_file(filepath, prompt, model, output_suffix="_cleaned", output_subfolder=DEFAULT_OUTPUT_SUBFOLDER):
    """
    Processes a single text file, cleans it with Ollama, and saves the cleaned output
    in a subfolder.

    Args:
        filepath (str): The path to the text file.
        prompt (str): The prompt to use for Ollama cleanup.
        model (str): The Ollama model to use.
        output_suffix (str): Suffix to add to the output filename (default: "_cleaned").
        output_subfolder (str): Name of the subfolder to save cleaned files (default: DEFAULT_OUTPUT_SUBFOLDER).
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as infile: # Ensure input file is read with UTF-8
            text_content = infile.read()

        print(f"Processing file: {filepath}")
        cleaned_text = cleanup_text_with_ollama(text_content, prompt, model)

        if cleaned_text is not None:
            base, ext = os.path.splitext(filepath)
            original_dir = os.path.dirname(filepath) # Get the directory of the original file
            output_dir = os.path.join(original_dir, output_subfolder) # Create path for the subfolder
            os.makedirs(output_dir, exist_ok=True) # Create the subfolder if it doesn't exist
            output_filename = f"{base}{output_suffix}{ext}" # Filename inside the subfolder
            output_filepath = os.path.join(output_dir, output_filename) # Full path to the output file

            with open(output_filepath, 'w', encoding='utf-8') as outfile: # Ensure output file is written with UTF-8
                outfile.write(cleaned_text)
            print(f"Cleaned output saved to: {output_filepath}")
        else:
            print(f"Cleanup failed for file: {filepath}")

    except FileNotFoundError:
        print(f"Error: File not found: {filepath}")
    except Exception as e:
        print(f"Error processing file {filepath}: {e}")


def main():
    parser = argparse.ArgumentParser(description="Clean up text files using Ollama.")
    parser.add_argument("file_pattern", help="File pattern (e.g., '*.txt') to specify text files.")
    parser.add_argument("--prompt", type=str, default=DEFAULT_PROMPT,
                        help=f"Custom prompt for Ollama (default: '{DEFAULT_PROMPT}')")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL, help=f"Ollama model to use (default: '{DEFAULT_MODEL}')")
    parser.add_argument("--output_suffix", type=str, default="_cleaned", help="Suffix to add to cleaned output filenames (default: '_cleaned')")
    parser.add_argument("--output_subfolder", type=str, default=DEFAULT_OUTPUT_SUBFOLDER, help=f"Subfolder to save cleaned files (default: '{DEFAULT_OUTPUT_SUBFOLDER}')")
    parser.add_argument("--timeout", type=int, default=OLLAMA_TIMEOUT_SECONDS, help=f"Timeout in seconds for Ollama command (default: {OLLAMA_TIMEOUT_SECONDS} seconds)")


    args = parser.parse_args()

    file_pattern = args.file_pattern
    prompt = args.prompt
    model = args.model
    output_suffix = args.output_suffix
    output_subfolder = args.output_subfolder
    timeout = args.timeout # Get timeout from arguments

    # --- Check if the specified Ollama model is available BEFORE processing ---
    if not is_ollama_model_available(model):
        print(f"Error: Ollama model '{model}' is not available locally.")
        print(f"Please run 'ollama pull {model}' in your terminal to download the model first.")
        sys.exit(1) # Exit with an error code

    # Expand the file pattern using glob relative to the current directory
    files_to_process = glob.glob(file_pattern)

    if not files_to_process:
        print(f"No files found matching pattern: {file_pattern}")
        return

    for filepath in files_to_process:
        process_file(filepath, prompt, model, output_suffix, output_subfolder)

if __name__ == "__main__":
    main()