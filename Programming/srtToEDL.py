# -*- coding: utf-8 -*-
# --- IMPORTANT: This script requires the 'regex' module ---
# Install it using: pip install regex
# ---------------------------------------------------------

# Replace 'import re' with 'import regex as re'
# import re # Original line
import regex as re # Use the regex module for better Unicode support

from datetime import datetime, timedelta
import glob
import os
import sys

# --- Set DEBUG_MODE globally ---
DEBUG_MODE = False # Set to False once working, True for detailed logs

def parse_srt_block_debug(block_text, block_index):
    """Parses a single SRT block with debug output, allowing : as ms separator."""
    global DEBUG_MODE # Make sure it can access the global DEBUG_MODE
    if DEBUG_MODE: print(f"\n--- Attempting to parse block {block_index} ---")
    if DEBUG_MODE: print(f"Raw block content:\n'''\n{block_text}\n'''")

    # Regex allowing comma, period, OR colon [,.':'] as millisecond separator
    time_pattern_ms = r"((?:\d{2}:)?\d{2}:\d{2}[,.:']\d{3})" # Note [,.':'] here

    # Primary pattern using the corrected time sub-pattern
    block_pattern = re.compile(
        r"^\s*(\d+)\s*\n"                               # 1: Index
        r"\s*" + time_pattern_ms + r"\s*-->\s*"         # 2: Start Time
        r"\s*" + time_pattern_ms + r"\s*\r?\n"          # 3: End Time (added \r?)
        r"(.*)",                                        # 4: Text (greedy, remaining content)
        re.DOTALL | re.UNICODE # Added re.UNICODE flag
    )
    match = block_pattern.match(block_text)

    if match:
        if DEBUG_MODE: print(f"Block {block_index}: PARSED successfully.")
        # Prepare preview string safely for f-string
        text_preview = match.group(4)[:30].replace('\n', ' ')
        if DEBUG_MODE: print(f"  Index: {match.group(1)}, Start: {match.group(2)}, End: {match.group(3)}, Text Preview: {text_preview}...")
        return match.groups()
    else:
        if DEBUG_MODE: print(f"Block {block_index}: PARSE FAILED with primary pattern.")
        # Try alternative with more flexible spacing around '-->'
        block_pattern_alt = re.compile(
            r"^\s*(\d+)\s*\n"
            r"\s*" + time_pattern_ms + r"\s*-->\s*"         # Start Time
            r"\s*" + time_pattern_ms + r"\s*\s*\r?\n"       # End Time (more space before \n)
            r"(.*)",
            re.DOTALL | re.UNICODE # Added re.UNICODE flag
        )
        match = block_pattern_alt.match(block_text)
        if match:
             if DEBUG_MODE: print(f"Block {block_index}: PARSED successfully with ALT pattern.")
             # Prepare preview string safely for f-string
             text_preview = match.group(4)[:30].replace('\n', ' ')
             if DEBUG_MODE: print(f"  Index: {match.group(1)}, Start: {match.group(2)}, End: {match.group(3)}, Text Preview: {text_preview}...")
             return match.groups()
        else:
             if DEBUG_MODE: print(f"Block {block_index}: PARSE FAILED with ALT pattern.")
             return None


# --- CORRECTED & MODIFIED FUNCTION ---
def generate_timeline_data(srt_file_path, output_file_path):
    """
    Generates timeline data using split-and-parse with corrected time normalization,
    ensuring UTF-8 input/output and preserving specific text characters (alphanumeric,
    whitespace, underscore) while removing emojis and other symbols.
    Handles potential leading '```srt' and trailing '```' lines.
    """
    global DEBUG_MODE # Make sure it can access the global DEBUG_MODE

    try:
        with open(srt_file_path, 'rb') as f_byte:
            raw_bytes = f_byte.read()
        # Try decoding as UTF-8. If it fails, raise UnicodeDecodeError.
        srt_content = raw_bytes.decode('utf-8')
        encoding_used = 'utf-8'
        if DEBUG_MODE: print(f"File '{srt_file_path}' read successfully using {encoding_used} encoding.")

    except FileNotFoundError:
        print(f"Error: SRT file not found at {srt_file_path}")
        return False
    except UnicodeDecodeError:
        print(f"Error: Could not decode file '{srt_file_path}' as UTF-8. Please ensure the input file is saved in UTF-8 format.")
        return False
    except Exception as e:
        print(f"Error reading SRT file '{srt_file_path}': {e}")
        return False


    # --- Standard EDL Header ---
    title = os.path.splitext(os.path.basename(srt_file_path))[0]
    title = re.sub(r'[<>:"/\\|?*\n\r]', '', title).strip()
    if not title: title = "Untitled"
    edl_header = f"TITLE: {title}\nFCM: NON-DROP FRAME\n\n"

    # --- Normalize line endings FIRST ---
    normalized_content = srt_content.replace('\r\n', '\n').replace('\r', '\n')

    # --- *** NEW: Clean leading/trailing ``` markers *** ---
    original_length = len(normalized_content)
    # Remove leading ```srt (case-insensitive) possibly followed by newline, surrounded by optional whitespace
    cleaned_content = re.sub(r'^\s*```srt\s*\n', '', normalized_content, flags=re.IGNORECASE | re.UNICODE)
    # Remove trailing ``` possibly preceded by newline, surrounded by optional whitespace
    cleaned_content = re.sub(r'\n\s*```\s*$', '', cleaned_content, flags=re.UNICODE)
    # Strip leading/trailing whitespace that might remain after removal or be original
    cleaned_content = cleaned_content.strip()

    if DEBUG_MODE and len(cleaned_content) != original_length:
        print(f"DEBUG: Removed potential ```srt / ``` markers. Original length: {original_length}, New length: {len(cleaned_content)}")
    # --- *** End of NEW section *** ---


    # --- Split content into blocks (using the cleaned content) ---
    # Split using regex with UNICODE flag just in case \s needs it for various newlines
    srt_blocks = re.split(r'\n\s*\n+', cleaned_content, flags=re.UNICODE) # Use cleaned_content

    if DEBUG_MODE: print(f"Split into {len(srt_blocks)} potential blocks.")

    if not srt_blocks or (len(srt_blocks) == 1 and not srt_blocks[0].strip()):
         print(f"Warning: Could not split SRT file '{srt_file_path}' into meaningful blocks (after potential cleaning).")
         try: # Write empty EDL
            with open(output_file_path, 'w', encoding='utf-8') as output_file:
                output_file.write(edl_header)
                output_file.write("# Source file empty or could not be split into blocks.\n")
            print(f"Empty EDL file created: '{output_file_path}'")
         except Exception as e:
            print(f"Error writing empty EDL file '{output_file_path}': {e}")
         return False # Treat as failure if split fails badly

    # --- Process Blocks ---
    edl_body = ""
    processed_count = 0
    skipped_block_count = 0

    for i, block in enumerate(srt_blocks):
        block = block.strip()
        if not block:
            if DEBUG_MODE: print(f"Skipping empty block at index {i}.")
            continue

        parsed_data = parse_srt_block_debug(block, i + 1) # Using the helper function

        if not parsed_data:
            # Check if the block *looks* like the removed markers, to avoid noisy warnings
            is_likely_marker = re.match(r'^```(srt)?$', block, re.IGNORECASE) is not None
            if not DEBUG_MODE and not is_likely_marker:
                 # Prepare the preview string *before* the f-string:
                 block_preview = block[:50].replace('\n',' ') # Replace newline with space for preview
                 print(f"Warning: Skipping malformed block near original index {i+1} in '{srt_file_path}'. Content starts with: '{block_preview}...'")
            elif DEBUG_MODE and not is_likely_marker:
                 # Already printed detailed failure in parse_srt_block_debug
                 pass
            skipped_block_count += 1
            continue

        # --- Try processing the successfully parsed block ---
        try:
            seq_num_str, start_time_str, end_time_str, text = parsed_data
            # Use parsed index if available, fallback for safety but should always be there if parsed_data is not None
            original_srt_index = seq_num_str if seq_num_str else f"Block_{i+1}"

            # --- Time/Text Processing Logic ---
            try:
                # Helper function to normalize time string for strptime
                def normalize_ms_separator(time_str):
                    if len(time_str) > 4 and time_str[-4] in [',', '.', ':']:
                        return time_str[:-4] + '.' + time_str[-3:]
                    else:
                        if DEBUG_MODE: print(f"DEBUG: Time string '{time_str}' did not match expected separator pattern for normalization.")
                        return time_str # Don't modify if format is unexpected

                start_time_str_norm = normalize_ms_separator(start_time_str)
                end_time_str_norm = normalize_ms_separator(end_time_str)

                # Handle optional HH: part before strptime (Padding)
                if start_time_str_norm.count(':') == 1: # Check HH:MM count based on ':'
                    start_time_str_pad = "00:" + start_time_str_norm
                else:
                    start_time_str_pad = start_time_str_norm

                if end_time_str_norm.count(':') == 1:
                    end_time_str_pad = "00:" + end_time_str_norm
                else:
                    end_time_str_pad = end_time_str_norm

                # Now parse using the padded and CORRECTLY normalized string
                dummy_date = "1900-01-01"
                if DEBUG_MODE: print(f"DEBUG: Attempting strptime with: '{start_time_str_pad}' and '{end_time_str_pad}'")
                start_time_dt = datetime.strptime(f"{dummy_date} {start_time_str_pad}", "%Y-%m-%d %H:%M:%S.%f")
                # end_time_dt_validation = datetime.strptime(f"{dummy_date} {end_time_str_pad}", "%Y-%m-%d %H:%M:%S.%f") # Validation not strictly needed for EDL output
                if DEBUG_MODE: print(f"DEBUG: strptime successful.")

                # -- EDL Formatting --
                start_frames_or_hundredths = f"{start_time_dt.microsecond // 10000:02d}"
                # EDL has short duration based on original script logic
                end_time_plus_one_dt = start_time_dt + timedelta(microseconds=10000) # Add 1/100th sec
                end_plus_one_frames_or_hundredths = f"{end_time_plus_one_dt.microsecond // 10000:02d}"

                start_tc = start_time_dt.strftime(f"%H:%M:%S:{start_frames_or_hundredths}")
                end_tc = end_time_plus_one_dt.strftime(f"%H:%M:%S:{end_plus_one_frames_or_hundredths}")


                # -- Text Cleaning --
                cleaned_text = ' '.join(line.strip() for line in text.strip().splitlines())
                cleaned_text = re.sub(r'<[^>]+>', '', cleaned_text) # Remove HTML tags

                # Filter: Keep \w (alphanumeric + underscore, UNICODE) and \s (whitespace, UNICODE)
                marker_label = re.sub(r'[^\w\s\'\,\(\)]+', '', cleaned_text, re.UNICODE) #regex strip. add more stuff to inside the angle brackets to add more allowed characters.
                marker_label = re.sub(r'\s+', ' ', marker_label).strip() # Normalize whitespace
                marker_label = marker_label.replace('|', '_') # Replace pipe AFTER filtering

                if not marker_label: marker_label = f"Marker_{original_srt_index}"

                # Ensure marker label doesn't exceed a reasonable length (Resolve limit ~80)
                max_marker_len = 80
                if len(marker_label) > max_marker_len: marker_label = marker_label[:max_marker_len-3] + "..."


                # Assemble EDL Event
                processed_count += 1
                event_number_str = f"{processed_count:03}"
                edl_line1 = f"{event_number_str}  001      V     C        {start_tc} {end_tc} {start_tc} {end_tc}\n"
                edl_line2 = f"* FROM CLIP NAME: {os.path.basename(srt_file_path)}\n"
                edl_line2 += f" |C:ResolveColorBlue |M:{marker_label} |D:1\n\n" # Resolve marker format

                edl_body += edl_line1 + edl_line2

            except ValueError as time_e:
                print(f"Warning: Skipping entry index {original_srt_index} (from block {i+1}) due to time format/parsing error: {time_e} (Input: '{start_time_str}' / '{end_time_str}'; Processed as: '{start_time_str_pad}' / '{end_time_str_pad}')")
                skipped_block_count += 1
            except Exception as parse_e:
                 # Prepare the error text preview *before* the f-string:
                text_preview = text[:50].replace('\n', ' ') # Replace newline with space for preview
                print(f"Warning: Skipping entry index {original_srt_index} (from block {i+1}) due to processing error: {parse_e} on text: '{text_preview}...'")
                skipped_block_count += 1

        except Exception as block_proc_e:
             print(f"Error processing parsed block {i+1}: {block_proc_e}")
             skipped_block_count += 1


    # --- Write the Complete EDL File (Ensured UTF-8 Output) ---
    try:
        with open(output_file_path, 'w', encoding='utf-8') as output_file:
            output_file.write(edl_header)
            output_file.write(edl_body)

        # --- Reporting Logic ---
        if processed_count > 0:
            success_msg = f"EDL file generated successfully ({processed_count} markers) for '{srt_file_path}' and saved to '{output_file_path}'"
            if skipped_block_count > 0:
                 success_msg += f" ({skipped_block_count} potential blocks skipped due to parsing/processing errors)."
            print(success_msg)
        else:
             # Handle cases where no markers were processed
             if skipped_block_count > 0:
                  print(f"EDL file generated for '{srt_file_path}', but NO entries could be processed. {skipped_block_count} blocks were skipped (check warnings). Saved to '{output_file_path}'")
             elif not srt_blocks or (len(srt_blocks) == 1 and not srt_blocks[0].strip()):
                  # This condition should ideally be met if the file was only ```srt``` ``` after cleaning
                  print(f"EDL file generated empty for '{srt_file_path}' as the source file was empty or contained only markers after cleaning. Saved to '{output_file_path}'")
             else: # Blocks existed but none parsed/processed
                  print(f"EDL file generated empty for '{srt_file_path}' as no valid SRT entries were found or could be processed from the blocks. Saved to '{output_file_path}'")
        return True # Indicate success if file writing occurred

    except Exception as e:
        print(f"Error writing EDL file '{output_file_path}': {e}")
        return False # Indicate failure on write error


# --- Main execution block (ensure this is present in your final script) ---
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("\nUsage: python srt_to_timeline.py <srt_file_pattern>")
        print("  Processes SRT files matching the pattern and creates corresponding .edl files.")
        print("  Requires input SRT files to be encoded in UTF-8.")
        print("  Requires the 'regex' module: pip install regex") # Added reminder here too
        print("  Markers will contain only letters, numbers, whitespace, and underscores.")
        print("\nExamples:")
        print("  Process a specific file (use quotes if name has spaces/special chars):")
        print("    python srt_to_timeline.py \"My Subtitles.srt\"")
        print("\n  Process all SRT files in the current directory:")
        print("    python srt_to_timeline.py *.srt")
        print("\n  Process files matching a partial name:")
        print("    python srt_to_timeline.py episode*.srt")
        print("\n  Set DEBUG_MODE = True inside the script for detailed parsing logs.")
        sys.exit(1) # Exit if no args

    pattern = sys.argv[1]
    current_dir = os.getcwd()
    srt_files_to_process = []

    # File finding logic (improved slightly from original)
    if '*' in pattern or '?' in pattern:
        search_pattern = os.path.join(current_dir, pattern)
        potential_matches = glob.glob(search_pattern)
        # Filter ensuring it's a file and ends with .srt (case-insensitive)
        srt_files_to_process = [f for f in potential_matches if os.path.isfile(f) and f.lower().endswith('.srt')]
    else:
        # Handle literal filename potentially with relative path parts
        literal_path = os.path.join(current_dir, pattern)
        if os.path.isfile(literal_path) and literal_path.lower().endswith('.srt'):
             srt_files_to_process = [literal_path] # Use the constructed path
        elif os.path.isfile(literal_path) and not literal_path.lower().endswith('.srt'):
             print(f"Warning: File '{pattern}' exists but does not have a .srt extension. Skipping: {literal_path}")
        elif not os.path.exists(literal_path):
             print(f"Error: Specified file not found: {literal_path}")


    if not srt_files_to_process:
        # Refined error message based on whether it was a pattern or specific file
        if '*' in pattern or '?' in pattern:
            print(f"\nError: No SRT files found matching the pattern {repr(pattern)} in the directory: {current_dir}")
        elif not os.path.exists(os.path.join(current_dir, pattern)):
             # Already printed the specific 'not found' message above
             pass # Avoid duplicate message
        else: # File existed but wasn't .srt or other issue
            print(f"\nError: No valid SRT file specified or found for '{pattern}'.")

        sys.exit(1)

    processed_count_total = 0
    error_count = 0
    print(f"\nFound {len(srt_files_to_process)} SRT file(s) to process:")
    # List files being processed for clarity
    for fpath in srt_files_to_process:
        print(f"  - {os.path.basename(fpath)}")

    for srt_file_path_full in srt_files_to_process:
        # Ensure we use the absolute path found by glob or constructed
        print(f"\nProcessing: {os.path.basename(srt_file_path_full)}")
        base_name = os.path.splitext(os.path.basename(srt_file_path_full))[0]
        output_dir = os.path.dirname(srt_file_path_full)
        output_file_path = os.path.join(output_dir, f"{base_name}.edl")

        # DEBUG_MODE is set at the top of the script
        if generate_timeline_data(srt_file_path_full, output_file_path):
            processed_count_total += 1
        else:
            error_count += 1
            print(f"^^^ Failed to process {os.path.basename(srt_file_path_full)} due to errors (check warnings above).")

    print(f"\n--- Processing Complete ---")
    print(f"Successfully attempted processing for: {processed_count_total} file(s).")
    if error_count > 0:
        print(f"Failed or skipped processing for: {error_count} file(s). Check warnings and debug logs above.")
    elif processed_count_total > 0 :
         print("All attempted files processed successfully.")
    else: # No files were processed successfully, and no errors were flagged (e.g., only non-SRT files found)
         print("No files were successfully processed.")
# --- End of Script ---