#!/usr/bin/env python3

import sys
import glob
import os
import argparse
import google.generativeai as genai
import time

# --- Rate Limiting Configuration ---
REQUESTS_PER_MINUTE = 10  # Maximum requests per minute
REQUEST_INTERVAL_SECONDS = 60 / REQUESTS_PER_MINUTE # Minimum interval between requests
last_request_time = None # Initialize last request time

# --- Default Configuration (Easily Editable Here) ---
DEFAULT_MODEL = "gemini-2.0-flash"  # Changed default model to gemini-2.0-flash
DEFAULT_PROMPT = "Clean and correct the following text for grammar, spelling, and clarity. Return only the cleaned text, do not include notes or anything else." # Default prompt
DEFAULT_OUTPUT_SUBFOLDER = "cleaned_output_gemini" # Default subfolder for cleaned files
#GEMINI_API_TIMEOUT_SECONDS = 60  # Timeout in seconds - REMOVED timeout as it's causing errors
API_KEY_ENV_VAR = "GOOGLE_API_KEY" # Environment variable for API key
# --- End Default Configuration ---


def cleanup_text_with_gemini(text_content, prompt, model_name=DEFAULT_MODEL): # Removed timeout_seconds parameter
    """
    Sends text content to Google Gemini API for cleanup (TIMEOUT REMOVED), with rate limiting.

    Args:
        text_content (str): The text content to be cleaned.
        prompt (str): The prompt for Gemini.
        model_name (str): The Gemini model to use.

    Returns:
        str: The cleaned text content from Gemini, or an error string on error.
    """
    global last_request_time

    try:
        genai.configure(api_key=os.environ.get(API_KEY_ENV_VAR)) # API key from env
        if not os.environ.get(API_KEY_ENV_VAR):
            error_message = f"Error: API key environment variable '{API_KEY_ENV_VAR}' not found."
            print(error_message)
            return error_message

        # --- Rate Limiting Implementation ---
        current_time = time.time()
        if last_request_time is not None:
            time_since_last_request = current_time - last_request_time
            if time_since_last_request < REQUEST_INTERVAL_SECONDS:
                sleep_duration = REQUEST_INTERVAL_SECONDS - time_since_last_request
                print(f"Rate limit active. Sleeping for {sleep_duration:.2f} seconds...")
                time.sleep(sleep_duration)
        # Update last request time before making the API call
        last_request_time = time.time()
        # --- End Rate Limiting ---


        model = genai.GenerativeModel(model_name)

        response = model.generate_content(
            [prompt, text_content] # Removed timeout argument
        )

        if response.text:
            cleaned_text = response.text.strip()
            return cleaned_text
        else:
            error_message = "Error from Gemini API: No text response received."
            if response.prompt_feedback:
                error_message += f"\nPrompt Feedback: {response.prompt_feedback}"
            if response.candidates:
                for candidate in response.candidates:
                    if candidate.finish_reason:
                        finish_reason_code = candidate.finish_reason.value
                        finish_reason_str = candidate.finish_reason.name
                        error_message += f"\nCandidate Finish Reason: {finish_reason_str} (Code: {finish_reason_code})"
                        if finish_reason_code == 4: # Specific check for finish_reason 4 (RECITATION)
                            error_message += "\nPossible copyright recitation issue detected."

            print(error_message) # Print error message to console as well
            return error_message # Return the error message string

    except Exception as e:
        error_message = f"An unexpected error occurred with Gemini API: {e}"
        print(error_message)
        return error_message # Return the error message string


def process_file(filepath, prompt, model, output_suffix="_cleaned_gemini", output_subfolder=DEFAULT_OUTPUT_SUBFOLDER): # Removed timeout parameter from process_file
    """
    Processes a text file, cleans it with Gemini API (TIMEOUT REMOVED), saves output, with rate limiting.

    Args:
        filepath (str): Path to the text file.
        prompt (str): Prompt for Gemini API cleanup.
        model (str): Gemini API model.
        output_suffix (str): Suffix for output filename.
        output_subfolder (str): Subfolder for cleaned files.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as infile:
            text_content = infile.read()

        print(f"Processing file: {filepath}")
        result_text = cleanup_text_with_gemini(text_content, prompt, model) # Get result, which can be cleaned text or error

        base, ext = os.path.splitext(filepath)
        original_dir = os.path.dirname(filepath)
        output_dir = os.path.join(original_dir, output_subfolder)
        os.makedirs(output_dir, exist_ok=True)

        if isinstance(result_text, str) and "Error from Gemini API" in result_text or "unexpected error occurred with Gemini API" in result_text or "API key environment variable" in result_text:
            # Save error message to file with _error suffix
            output_filename = f"{base}_error{ext}"
            output_filepath = os.path.join(output_dir, output_filename)
            with open(output_filepath, 'w', encoding='utf-8') as outfile:
                outfile.write(result_text)
            print(f"Error output saved to: {output_filepath}")

        elif isinstance(result_text, str): # Assume it's cleaned text if it's a string and not an error
            # Save cleaned text with _cleaned_gemini suffix
            output_filename = f"{base}{output_suffix}{ext}"
            output_filepath = os.path.join(output_dir, output_filename)
            with open(output_filepath, 'w', encoding='utf-8') as outfile:
                outfile.write(result_text)
            print(f"Cleaned output saved to: {output_filepath}")
        else:
            print(f"Cleanup failed for file: {filepath} - Unknown error.")


    except FileNotFoundError:
        print(f"Error: File not found: {filepath}")
    except Exception as e:
        print(f"Error processing file {filepath}: {e}")


def main():
    global last_request_time # Access the global variable
    last_request_time = None # Reset last_request_time at the start of main if needed, or keep it at the top level

    parser = argparse.ArgumentParser(description="Clean text files using Google Gemini API (TIMEOUT REMOVED), with rate limiting.") # Updated description
    parser.add_argument("file_pattern", help="File pattern (e.g., '*.txt') for text files.")
    parser.add_argument("--prompt", type=str, default=DEFAULT_PROMPT,
                        help=f"Custom prompt for Gemini API (default: '{DEFAULT_PROMPT}')")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL, help=f"Gemini API model (default: '{DEFAULT_MODEL}')")
    parser.add_argument("--output_suffix", type=str, default="_cleaned_gemini", help="Suffix for output filenames (default: '_cleaned_gemini')")
    parser.add_argument("--output_subfolder", type=str, default=DEFAULT_OUTPUT_SUBFOLDER, help=f"Subfolder for cleaned files (default: '{DEFAULT_OUTPUT_SUBFOLDER}')")
    #parser.add_argument("--timeout", type=int, default=GEMINI_API_TIMEOUT_SECONDS, help=f"Timeout in seconds (default: {GEMINI_API_TIMEOUT_SECONDS} seconds) - REMOVED timeout argument") # Removed timeout argument


    args = parser.parse_args()

    file_pattern = args.file_pattern
    prompt = args.prompt
    model = args.model
    output_suffix = args.output_suffix
    output_subfolder = args.output_subfolder
    #timeout = args.timeout # Removed timeout

    # --- No model availability check needed for cloud API ---

    files_to_process = glob.glob(file_pattern)

    if not files_to_process:
        print(f"No files found matching pattern: {file_pattern}")
        return

    for filepath in files_to_process:
        process_file(filepath, prompt, model, output_suffix, output_subfolder) # Removed timeout argument

if __name__ == "__main__":
    main()