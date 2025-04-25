import re
from datetime import datetime, timedelta
import glob
import os
import sys

# Set to False once working, True for detailed logs
DEBUG_MODE = False

def parse_srt_block_debug(block_text, block_index):
    """Parses a single SRT block with debug output, allowing : as ms separator."""
    if DEBUG_MODE: print(f"\n--- Attempting to parse block {block_index} ---")
    if DEBUG_MODE: print(f"Raw block content:\n'''\n{block_text}\n'''")

    # Regex allowing comma, period, OR colon [,.':'] as millisecond separator
    time_pattern_ms = r"((?:\d{2}:)?\d{2}:\d{2}[,.:]\d{3})" # Note [,.':'] here

    # Primary pattern using the corrected time sub-pattern
    block_pattern = re.compile(
        r"^\s*(\d+)\s*\n"                               # 1: Index
        r"\s*" + time_pattern_ms + r"\s*-->\s*"         # 2: Start Time
        r"\s*" + time_pattern_ms + r"\s*\r?\n"          # 3: End Time (added \r?)
        r"(.*)",                                        # 4: Text (greedy, remaining content)
        re.DOTALL
    )
    match = block_pattern.match(block_text)

    if match:
        if DEBUG_MODE: print(f"Block {block_index}: PARSED successfully.")
        if DEBUG_MODE: print(f"  Index: {match.group(1)}, Start: {match.group(2)}, End: {match.group(3)}, Text Preview: {match.group(4)[:30].replace('\n',' ')}...")
        return match.groups()
    else:
        if DEBUG_MODE: print(f"Block {block_index}: PARSE FAILED with primary pattern.")
        # Try alternative with more flexible spacing around '-->'
        block_pattern_alt = re.compile(
            r"^\s*(\d+)\s*\n"
            r"\s*" + time_pattern_ms + r"\s*-->\s*"         # Start Time
            r"\s*" + time_pattern_ms + r"\s*\s*\r?\n"       # End Time (more space before \n)
            r"(.*)",
            re.DOTALL
        )
        match = block_pattern_alt.match(block_text)
        if match:
             if DEBUG_MODE: print(f"Block {block_index}: PARSED successfully with ALT pattern.")
             if DEBUG_MODE: print(f"  Index: {match.group(1)}, Start: {match.group(2)}, End: {match.group(3)}, Text Preview: {match.group(4)[:30].replace('\n',' ')}...")
             return match.groups()
        else:
             if DEBUG_MODE: print(f"Block {block_index}: PARSE FAILED with ALT pattern.")
             return None


def generate_timeline_data(srt_file_path, output_file_path):
    """
    Generates timeline data using split-and-parse with corrected time normalization.
    """
    try:
        try:
            with open(srt_file_path, 'rb') as f_byte:
                raw_bytes = f_byte.read()
            try:
                srt_content = raw_bytes.decode('utf-8')
                encoding_used = 'utf-8'
            except UnicodeDecodeError:
                print(f"Warning: UTF-8 decoding failed for '{srt_file_path}'. Trying latin-1 encoding.")
                srt_content = raw_bytes.decode('latin-1')
                encoding_used = 'latin-1'
        except Exception as enc_e:
            print(f"Error: Could not read/decode file '{srt_file_path}': {enc_e}")
            return False
    except FileNotFoundError:
        print(f"Error: SRT file not found at {srt_file_path}")
        return False
    except Exception as e:
        print(f"Error reading SRT file '{srt_file_path}': {e}")
        return False

    if DEBUG_MODE: print(f"File '{srt_file_path}' read using {encoding_used} encoding.")

    # --- Standard EDL Header ---
    title = os.path.splitext(os.path.basename(srt_file_path))[0]
    title = re.sub(r'[<>:"/\\|?*\n\r]', '', title).strip()
    if not title: title = "Untitled"
    edl_header = f"TITLE: {title}\nFCM: NON-DROP FRAME\n\n"

    # --- Split content into blocks ---
    normalized_content = srt_content.replace('\r\n', '\n').replace('\r', '\n')
    srt_blocks = re.split(r'\n\s*\n+', normalized_content.strip())

    if DEBUG_MODE: print(f"Split into {len(srt_blocks)} potential blocks.")

    if not srt_blocks or (len(srt_blocks) == 1 and not srt_blocks[0].strip()):
         print(f"Warning: Could not split SRT file '{srt_file_path}' into meaningful blocks.")
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

        parsed_data = parse_srt_block_debug(block, i + 1)

        if not parsed_data:
            if not DEBUG_MODE:
                 print(f"Warning: Skipping malformed block near original index {i+1} in '{srt_file_path}'.")
            skipped_block_count += 1
            continue

        # --- Try processing the successfully parsed block ---
        try:
            seq_num_str, start_time_str, end_time_str, text = parsed_data
            original_srt_index = seq_num_str

            # --- Time/Text Processing Logic ---
            try:
                # CORRECTED Normalization: Only replace the ms separator
                def normalize_ms_separator(time_str):
                    if len(time_str) > 4 and time_str[-4] in [',', '.', ':']:
                        return time_str[:-4] + '.' + time_str[-3:]
                    else:
                        # Don't modify if format is unexpected
                        if DEBUG_MODE: print(f"DEBUG: Time string '{time_str}' did not match expected separator pattern for normalization.")
                        return time_str

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
                end_time_dt_validation = datetime.strptime(f"{dummy_date} {end_time_str_pad}", "%Y-%m-%d %H:%M:%S.%f")
                if DEBUG_MODE: print(f"DEBUG: strptime successful.")

                # -- EDL Formatting (remains the same) --
                start_frames_or_hundredths = f"{start_time_dt.microsecond // 10000:02d}"
                end_time_plus_one_dt = start_time_dt + timedelta(microseconds=10000)
                end_plus_one_frames_or_hundredths = f"{end_time_plus_one_dt.microsecond // 10000:02d}"
                start_tc = start_time_dt.strftime(f"%H:%M:%S:{start_frames_or_hundredths}")
                end_tc = end_time_plus_one_dt.strftime(f"%H:%M:%S:{end_plus_one_frames_or_hundredths}")

                # -- Text Cleaning (remains the same) --
                cleaned_text = ' '.join(line.strip() for line in text.strip().splitlines())
                cleaned_text = re.sub(r'<[^>]+>', '', cleaned_text)
                marker_label = cleaned_text.replace('|', '_').strip()
                marker_label = re.sub(r'\s+', ' ', marker_label).strip()

                if not marker_label: marker_label = f"Marker_{original_srt_index}"

                max_marker_len = 80
                if len(marker_label) > max_marker_len: marker_label = marker_label[:max_marker_len-3] + "..."

                # Assemble EDL Event
                processed_count += 1
                event_number_str = f"{processed_count:03}"
                edl_line1 = f"{event_number_str}  001      V     C        {start_tc} {end_tc} {start_tc} {end_tc}\n"
                edl_line2 = f"* FROM CLIP NAME: {os.path.basename(srt_file_path)}\n"
                edl_line2 += f" |C:ResolveColorBlue |M:{marker_label} |D:1\n\n"

                edl_body += edl_line1 + edl_line2

            except ValueError as time_e:
                print(f"Warning: Skipping entry index {original_srt_index} (from block {i+1}) due to time format/parsing error: {time_e} (Input: '{start_time_str}' / '{end_time_str}'; Processed as: '{start_time_str_pad}' / '{end_time_str_pad}')")
                skipped_block_count += 1
            except Exception as parse_e:
                print(f"Warning: Skipping entry index {original_srt_index} (from block {i+1}) due to processing error: {parse_e} on text: '{text[:50].replace('\n', ' ')}...'")
                skipped_block_count += 1

        except Exception as block_proc_e:
             print(f"Error processing parsed block {i+1}: {block_proc_e}")
             skipped_block_count += 1

    # --- Write the Complete EDL File ---
    try:
        with open(output_file_path, 'w', encoding='utf-8') as output_file:
            output_file.write(edl_header)
            output_file.write(edl_body)

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
                  print(f"EDL file generated empty for '{srt_file_path}' as the source file was empty or could not be split. Saved to '{output_file_path}'")
             else: # Blocks existed but none parsed/processed
                  print(f"EDL file generated empty for '{srt_file_path}' as no valid SRT entries were found or could be processed from the blocks. Saved to '{output_file_path}'")
        return True # Indicate success if file writing occurred

    except Exception as e:
        print(f"Error writing EDL file '{output_file_path}': {e}")
        return False # Indicate failure on write error


# --- Main execution block (remains the same) ---
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("\nUsage: python srt_to_timeline.py <srt_file_pattern>")
        print("  Processes SRT files matching the pattern and creates corresponding .edl files.")
        print("\nExamples:")
        print("  Process a specific file (use quotes if name has spaces/special chars):")
        print("    python srt_to_timeline.py \"My Subtitles 😊 [ENG].srt\"")
        print("\n  Process all SRT files in the current directory:")
        print("    python srt_to_timeline.py *.srt")
        print("\n  Process files matching a partial name:")
        print("    python srt_to_timeline.py episode*.srt")
        print("\n  Set DEBUG_MODE = True inside the script for detailed parsing logs.")
        sys.exit(1)

    pattern = sys.argv[1]
    current_dir = os.getcwd()
    srt_files_to_process = []

    # File finding logic
    if '*' in pattern or '?' in pattern:
        search_pattern = os.path.join(current_dir, pattern)
        potential_matches = glob.glob(search_pattern)
        srt_files_to_process = [f for f in potential_matches if f.lower().endswith('.srt')]
    else:
        literal_path = os.path.join(current_dir, pattern)
        if os.path.isfile(literal_path) and pattern.lower().endswith('.srt'):
            srt_files_to_process = [literal_path]
        elif os.path.isfile(literal_path) and not pattern.lower().endswith('.srt'):
            print(f"Warning: File '{pattern}' exists but does not have a .srt extension. Skipping.")

    if not srt_files_to_process:
        print(f"\nError: No SRT files found matching the pattern {repr(pattern)} in the directory: {current_dir}")
        sys.exit(1)

    processed_count_total = 0
    error_count = 0
    print(f"\nFound {len(srt_files_to_process)} SRT file(s) to process.")

    for srt_file_path_full in srt_files_to_process:
        print(f"\nProcessing: {srt_file_path_full}")
        base_name = os.path.splitext(os.path.basename(srt_file_path_full))[0]
        output_dir = os.path.dirname(srt_file_path_full)
        output_file_path = os.path.join(output_dir, f"{base_name}.edl")

        # Set DEBUG_MODE at the top of the script if needed
        if generate_timeline_data(srt_file_path_full, output_file_path):
            processed_count_total += 1
        else:
            error_count += 1
            print(f"^^^ Errors occurred during processing of {os.path.basename(srt_file_path_full)}")

    print(f"\n--- Processing Complete ---")
    print(f"Attempted processing for: {processed_count_total} file(s).")
    if error_count > 0:
        print(f"Encountered errors processing: {error_count} file(s). Check warnings and debug logs above.")
    elif processed_count_total > 0 :
         print("Processing attempt complete.") # Simplified final message