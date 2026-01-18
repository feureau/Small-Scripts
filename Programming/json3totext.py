#!/usr/bin/env python3
import json
import os
import sys
import glob

def ms_to_srt_time(ms):
    """Converts milliseconds to SRT timestamp format (HH:MM:SS,mmm)."""
    seconds, milliseconds = divmod(ms, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d},{int(milliseconds):03d}"

def process_json3_subtitle(json3_path):
    """Parses a JSON3 subtitle file and extracts plaintext and word-level SRT."""
    try:
        if not os.path.exists(json3_path):
            return f"❌ File not found: {json3_path}"

        with open(json3_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        events = data.get('events', [])
        if not events:
            return f"⚠️  No events found in {os.path.basename(json3_path)}"

        base_name = os.path.splitext(json3_path)[0]
        txt_path = f"{base_name}.txt"
        srt_path = f"{base_name}.srt"
        
        full_text_parts = []
        srt_entries = []
        srt_index = 1
        last_event_end_ms = -1

        for event in events:
            start_ms = event.get('tStartMs', 0)
            duration = event.get('dDurationMs', 0)
            segments = event.get('segs', [])
            
            if not segments:
                continue

            # --- Plaintext Extraction (Readability Focus) ---
            event_text = "".join([s.get('utf8', '') for s in segments]).replace('\n', ' ').strip()
            if event_text:
                # Use a threshold (1.5s) to detect a natural break or paragraph
                if last_event_end_ms != -1 and (start_ms - last_event_end_ms) > 1500:
                    full_text_parts.append("\n\n")
                elif full_text_parts and not full_text_parts[-1].endswith("\n\n"):
                    full_text_parts.append(" ")
                
                full_text_parts.append(event_text)
                last_event_end_ms = start_ms + duration

            # --- SRT Extraction (Word/Segment Level) ---
            for i, seg in enumerate(segments):
                text = seg.get('utf8', '').strip()
                if not text:
                    continue
                
                offset = seg.get('tOffsetMs', 0)
                seg_start_ms = start_ms + offset
                
                if i < len(segments) - 1:
                    next_offset = segments[i+1].get('tOffsetMs', 0)
                    if next_offset > offset:
                         seg_end_ms = start_ms + next_offset
                    else:
                         seg_end_ms = seg_start_ms + 100
                else:
                    seg_end_ms = start_ms + duration
                
                if seg_end_ms <= seg_start_ms:
                     seg_end_ms = seg_start_ms + 100

                srt_entries.append(f"{srt_index}\n{ms_to_srt_time(seg_start_ms)} --> {ms_to_srt_time(seg_end_ms)}\n{text}\n")
                srt_index += 1

        # Write Plaintext (Joined parts)
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write("".join(full_text_parts).strip())

        # Write SRT
        with open(srt_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(srt_entries))
            
        return f"✅ Processed: {os.path.basename(json3_path)} -> .srt & .txt"

    except Exception as e:
        return f"❌ Error processing {os.path.basename(json3_path)}: {e}"

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 json3totext.py <path_to_file.json3> [more_files...]")
        sys.exit(1)

    # Gather inputs (handling wildcards manually for Windows CMD support, 
    # though Bash handles this automatically)
    files_to_process = []
    for arg in sys.argv[1:]:
        expanded = glob.glob(arg)
        if expanded:
            files_to_process.extend(expanded)
        else:
            # If glob doesn't find anything (e.g., exact filename), add arg as is
            files_to_process.append(arg)

    if not files_to_process:
        print("No files matches found.")
        sys.exit(1)

    print(f"Processing {len(files_to_process)} file(s)...")
    for file_path in files_to_process:
        result = process_json3_subtitle(file_path)
        print(result)

if __name__ == "__main__":
    main()