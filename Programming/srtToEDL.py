import re
from datetime import datetime, timedelta
import glob
import os
import sys

def generate_timeline_data(srt_file_path, output_file_path):
    """
    Generates timeline data in EDL format from an SRT file.

    Args:
        srt_file_path (str): Path to the SRT file.
        output_file_path (str): Path to the output EDL file.

    Returns:
        bool: True if successful, False otherwise.
    """

    try:
        # Try reading with UTF-8 first, fallback to latin-1 if needed
        try:
            with open(srt_file_path, 'r', encoding='utf-8') as srt_file:
                srt_content = srt_file.read()
        except UnicodeDecodeError:
            print(f"Warning: UTF-8 decoding failed for '{srt_file_path}'. Trying latin-1 encoding.")
            try:
                with open(srt_file_path, 'r', encoding='latin-1') as srt_file:
                    srt_content = srt_file.read()
            except Exception as enc_e:
                print(f"Error: Could not read file '{srt_file_path}' with tested encodings: {enc_e}")
                return False  # Indicate failure
    except FileNotFoundError:
        print(f"Error: SRT file not found at {srt_file_path}")
        return False  # Indicate failure
    except Exception as e:
        print(f"Error reading SRT file '{srt_file_path}': {e}")
        return False  # Indicate failure

    # --- Standard EDL Header ---
    title = os.path.splitext(os.path.basename(srt_file_path))[0]  # Use filename as title
    # Clean up title slightly for EDL if needed (optional)
    title = re.sub(r'[^\w\s-]', '', title).strip()  # Remove non-alphanumeric/space/hyphen
    edl_header = f"TITLE: {title}\nFCM: NON-DROP FRAME\n\n"

    # --- Parse SRT Entries ---
    # Regex captures: 1:Index, 2:Start Time, 3:End Time, 4:Text Block, 5: (Optional) Lookahead index
    # Handles variations in line endings and spacing, looks for blank line or EOF or next index as separator
    srt_entries = re.findall(
        r"(\d+)\s*(\d{2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,.]\d{3})\s*(.*?)(?=\n\n+|\n*\Z|\n*(\d+)\s*\d{2}:\d{2}:\d{2}[,.]\d{3})",
        srt_content,
        re.DOTALL | re.MULTILINE
    )
    # Corrected regex to handle both comma and dot as millisecond separators

    if not srt_entries:
        print(f"Warning: Could not parse any valid entries from '{srt_file_path}'. Is it a valid SRT file?")
        # Write empty EDL if requested or handle as error
        try:
            with open(output_file_path, 'w', encoding='utf-8') as output_file:
                output_file.write(edl_header)
                output_file.write("# No valid timestamp entries found in source SRT.\n")
            print(f"Empty EDL file created: '{output_file_path}'")
            return True  # Considered success (empty file created)
        except Exception as e:
            print(f"Error writing empty EDL file '{output_file_path}': {e}")
            return False  # Indicate failure

    # --- Process Entries and Build EDL Body ---
    edl_body = ""
    processed_count = 0  # Use this for the sequential EDL event number
    for i, entry in enumerate(srt_entries):
        seq_num_str, start_time_str, end_time_str, text, next_seq_num_str = entry
        original_srt_index = seq_num_str  # Keep track of original index if needed

        try:
            # Standardize separator to dot before parsing
            start_time_str_std = start_time_str.replace(',', '.')
            end_time_str_std = end_time_str.replace(',', '.')

            # Convert SRT timestamps (HH:MM:SS.ms) to datetime objects
            # Need a dummy date part for strptime
            dummy_date = "1900-01-01"
            start_time_dt = datetime.strptime(f"{dummy_date} {start_time_str_std}", "%Y-%m-%d %H:%M:%S.%f")
            # End time is not used directly for marker calculation in this EDL style, but parse it for validation
            end_time_dt_validation = datetime.strptime(f"{dummy_date} {end_time_str_std}", "%Y-%m-%d %H:%M:%S.%f")

            # --- Format Timestamps for EDL (HH:MM:SS:FF - Non-Drop Frame) ---
            # Assuming the EDL format uses frames, calculate from milliseconds.
            # Using hundredths derived from milliseconds as it matches the example's precision appearance.
            start_frames_or_hundredths = f"{start_time_dt.microsecond // 10000:02d}"

            # EDL timecodes often represent the *start* of the frame.
            # The example shows end time = start time + 1 frame/hundredth. Replicate that.
            end_time_plus_one_dt = start_time_dt + timedelta(microseconds=10000)  # Add 1/100th sec
            end_plus_one_frames_or_hundredths = f"{end_time_plus_one_dt.microsecond // 10000:02d}"

            start_tc = start_time_dt.strftime(f"%H:%M:%S:{start_frames_or_hundredths}")
            # Use the calculated "plus one" time for the end timecodes based on the example format
            end_tc = end_time_plus_one_dt.strftime(f"%H:%M:%S:{end_plus_one_frames_or_hundredths}")

            # --- Get Marker Label from Subtitle Text ---
            # Clean up subtitle text (remove leading/trailing whitespace, join lines with space)
            cleaned_text = ' '.join(line.strip() for line in text.strip().splitlines())
            # Remove potential HTML tags common in SRT
            cleaned_text = re.sub(r'<[^>]+>', '', cleaned_text)
            # Replace characters problematic for EDL M comments (like '|', newlines, etc.)
            marker_label = cleaned_text.replace('|', '_').replace('\n', ' ').replace('\r', '').strip()

            # Filter the marker label to include only letters and numbers
            marker_label = re.sub(r'[^A-Za-z0-9 ]', '', marker_label)

            if not marker_label:  # If the marker label becomes empty after filtering, use a fallback.
                marker_label = f"Marker_{original_srt_index}"

            # Limit marker label length if necessary (EDL comments can have limits)
            max_marker_len = 60  # Adjust as needed
            if len(marker_label) > max_marker_len:
                marker_label = marker_label[:max_marker_len-3] + "..."

            # --- Assemble EDL Event ---
            processed_count += 1  # Increment the EDL event number
            event_number_str = f"{processed_count:03}"

            # Line 1: Event#, Reel(use 001?), Track, Type, Transition, Start, End, RecStart, RecEnd
            # Using '001' for Reel for simplicity, V for Video, C for Cut.
            # Source TC Start = start_tc, Source TC End = end_tc
            # Record TC Start = start_tc, Record TC End = end_tc (since it's marking points on one timeline)
            edl_line1 = f"{event_number_str}  001      V     C        {start_tc} {end_tc} {start_tc} {end_tc}\n"

            # Line 2: Comments/Metadata
            # Using the format from the example: |C:Color |M:Marker Name |D:Duration(1 frame)
            edl_line2 = f"* FROM CLIP NAME: {os.path.basename(srt_file_path)}\n"  # Optional but good practice
            edl_line2 += f" |C:ResolveColorBlue |M:{marker_label} |D:1\n\n"  # Mimic example closely

            edl_body += edl_line1 + edl_line2

        except ValueError as time_e:
            print(f"Warning: Skipping entry index {original_srt_index} in '{srt_file_path}' due to time format/parsing error: {time_e} (Input: {start_time_str} / {end_time_str})")
        except Exception as parse_e:
            print(f"Warning: Skipping entry index {original_srt_index} in '{srt_file_path}' due to processing error: {parse_e}")

    # --- Write the Complete EDL File ---
    try:
        with open(output_file_path, 'w', encoding='utf-8') as output_file:
            output_file.write(edl_header)
            output_file.write(edl_body)

        if processed_count > 0:
            print(f"EDL file generated successfully ({processed_count} markers) for '{srt_file_path}' and saved to '{output_file_path}'")
        else:
            print(f"EDL file generated, but contained no valid markers, for '{srt_file_path}'. Saved to '{output_file_path}'")
        return True  # Indicate success

    except Exception as e:
        print(f"Error writing EDL file '{output_file_path}': {e}")
        return False  # Indicate failure

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("\nUsage: python srt_to_timeline.py <srt_file_pattern>")
        print("  Processes SRT files matching the pattern and creates corresponding .edl files.")
        print("\nExamples:")
        print("  Process a specific file (use quotes if name has spaces/special chars):")
        print("    python srt_to_timeline.py \"My Subtitles [ENG].srt\"")
        print("\n  Process all SRT files in the current directory:")
        print("    python srt_to_timeline.py *.srt")
        print("\n  Process files matching a partial name:")
        print("    python srt_to_timeline.py episode*.srt")
        sys.exit(1)

    pattern = sys.argv[1]
    current_dir = os.getcwd()
    srt_files_to_process = []

    # --- CORRECTED FILE FINDING LOGIC ---
    # Check if the pattern contains explicit glob wildcards * or ?
    if '*' in pattern or '?' in pattern:
        # Use glob only for explicit wildcards * or ?
        # Ensure glob pattern is joined with current dir if script is called from elsewhere
        # but pattern refers to current dir implicitly (e.g., *.srt)
        search_pattern = os.path.join(current_dir, pattern)
        potential_matches = glob.glob(search_pattern)
        # Filter to ensure only .srt files are included
        srt_files_to_process = [f for f in potential_matches if f.lower().endswith('.srt')]
    else:
        # Treat as a literal filename (even if it contains special chars like [])
        # Construct full path for checking
        literal_path = os.path.join(current_dir, pattern)
        if os.path.isfile(literal_path) and pattern.lower().endswith('.srt'):
            # Found the literal file (and it's a file, not a directory)
            srt_files_to_process = [literal_path]  # Use the full path
        # Optional: Add a check here if the file exists but doesn't end with .srt
        elif os.path.isfile(literal_path) and not pattern.lower().endswith('.srt'):
            print(f"Warning: File '{pattern}' exists but does not have a .srt extension. Skipping.")
        # If the literal file doesn't exist or isn't a file, srt_files_to_process remains empty.

    # --- END OF CORRECTION ---

    if not srt_files_to_process:
        # Use repr(pattern) to show potential non-printable characters if any
        print(f"\nError: No SRT files found matching the pattern {repr(pattern)} in the directory: {current_dir}")
        sys.exit(1)

    processed_count_total = 0
    error_count = 0
    print(f"\nFound {len(srt_files_to_process)} SRT file(s) to process.")

    for srt_file_path_full in srt_files_to_process:
        # srt_file_path_full should now always be an absolute path from the logic above
        print(f"\nProcessing: {srt_file_path_full}")

        # --- Create the output file path with .edl extension ---
        base_name = os.path.splitext(os.path.basename(srt_file_path_full))[0]
        output_dir = os.path.dirname(srt_file_path_full)  # Output in same dir as input
        output_file_path = os.path.join(output_dir, f"{base_name}.edl")

        if generate_timeline_data(srt_file_path_full, output_file_path):
            processed_count_total += 1
        else:
            error_count += 1

    print(f"\n--- Processing Complete ---")
    print(f"Successfully generated EDL for: {processed_count_total} file(s).")
    if error_count > 0:
        print(f"Encountered errors processing: {error_count} file(s). Check warnings above.")
