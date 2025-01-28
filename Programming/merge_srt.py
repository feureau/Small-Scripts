import os
import codecs

def read_srt(file_path):
    """Read an SRT file and handle BOM/multi-line text."""
    subtitles = []
    current_sub = {}
    
    with codecs.open(file_path, 'r', encoding='utf-8-sig') as file:  # Handles BOM
        lines = file.readlines()
    
    line_buffer = []
    for line in lines:
        stripped = line.strip()
        
        # Detect subtitle number
        if stripped.isdigit() and not current_sub:
            if line_buffer:  # Save previous subtitle
                subtitles.append(current_sub)
                current_sub = {}
            current_sub['index'] = int(stripped)
            line_buffer = []
            continue
            
        # Detect timestamp
        if '-->' in stripped and 'index' in current_sub:
            if not current_sub.get('start'):
                start_end = stripped.split('-->')
                current_sub['start'] = start_end[0].strip()
                current_sub['end'] = start_end[1].strip()
            continue
            
        # Handle text lines
        if stripped and 'start' in current_sub:
            line_buffer.append(stripped)
            
        # End of subtitle block
        if not stripped and line_buffer:
            current_sub['text'] = '\n'.join(line_buffer)
            subtitles.append(current_sub)
            current_sub = {}
            line_buffer = []
    
    # Add last subtitle
    if line_buffer:
        current_sub['text'] = '\n'.join(line_buffer)
        subtitles.append(current_sub)
    
    return subtitles

def write_srt(subtitles, file_path):
    """Write subtitles with proper SRT formatting."""
    with open(file_path, 'w', encoding='utf-8') as f:
        for idx, sub in enumerate(subtitles, 1):
            f.write(f"{idx}\n")
            f.write(f"{sub['start']} --> {sub['end']}\n")
            f.write(f"{sub['text']}\n\n")

def merge_subtitles(japanese_subs, english_subs):
    """Merge subtitles with Japanese above English."""
    merged = []
    for jp, en in zip(japanese_subs, english_subs):
        merged.append({
            'start': jp['start'],
            'end': jp['end'],
            'text': f"{jp['text']}\n{en['text']}"
        })
    return merged

def find_matching_files(folder):
    """Find matching Japanese/English subtitle pairs."""
    files = os.listdir(folder)
    base_files = {}
    
    # First pass: Identify base files
    for f in files:
        if f.endswith('.srt') and not f.endswith('.en.srt'):
            base_name = os.path.splitext(f)[0]
            base_files[base_name] = os.path.join(folder, f)
    
    # Second pass: Find matches
    matches = []
    for f in files:
        if f.endswith('.en.srt'):
            base_name = os.path.splitext(f)[0].replace('.en', '')
            if base_name in base_files:
                matches.append((
                    base_files[base_name],
                    os.path.join(folder, f)
                ))
    
    return matches

def main():
    current_dir = os.getcwd()
    output_dir = os.path.join(current_dir, "Merged_Subtitles")
    os.makedirs(output_dir, exist_ok=True)
    
    matches = find_matching_files(current_dir)
    
    for jp_path, en_path in matches:
        print(f"Processing: {os.path.basename(jp_path)}")
        
        jp_subs = read_srt(jp_path)
        en_subs = read_srt(en_path)
        
        if len(jp_subs) != len(en_subs):
            print(f"  Warning: Subtitle count mismatch! ({len(jp_subs)} vs {len(en_subs)})")
            print(f"  Skipping {os.path.basename(jp_path)}")
            continue
        
        merged = merge_subtitles(jp_subs, en_subs)
        output_path = os.path.join(output_dir, os.path.basename(jp_path))
        write_srt(merged, output_path)
    
    print("Processing complete!")

if __name__ == "__main__":
    main()