import os
import shutil
import json
import sys
import re
import subprocess
from collections import defaultdict

try:
    import requests
except ImportError:
    print("Error: The 'requests' library is missing. Run: pip install requests")
    sys.exit(1)

# --- CONFIGURATION ---
OLLAMA_API_BASE = "http://localhost:11434"
LM_STUDIO_API_BASE = "http://localhost:1234/v1"
CHUNK_SIZE = 100  # Reduced to fit within standard model context limits (e.g. 8k tokens)
MISC_FOLDER = "misc"
MAX_METADATA_CHARS = 800  # Per-file metadata summary cap to keep prompts compact

import argparse

def repair_json(s):
    """Attempts to fix truncated/malformed JSON from AI output."""
    s = s.strip()
    # Remove markdown code blocks if present
    s = re.sub(r'```json\s*|\s*```', '', s).strip()
    
    # Simple fix for unterminated strings if they end with a backslash or just cut off
    if s.count('"') % 2 != 0: s += '"'
    
    # Try to close open braces/brackets
    depth_braces = s.count('{') - s.count('}')
    if depth_braces > 0: s += '}' * depth_braces
    
    depth_brackets = s.count('[') - s.count(']')
    if depth_brackets > 0: s += ']' * depth_brackets
    
    return s

def get_model_context_window(model_name, provider):
    """Estimates or fetches the context window size for a model."""
    default_ctx = 4096 # Safe default
    
    if provider == "Ollama":
        try:
            resp = requests.post(f"{OLLAMA_API_BASE}/api/show", json={"name": model_name}, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                # 1. Check explicit parameters
                params = data.get('parameters', '')
                if 'num_ctx' in params:
                    match = re.search(r'num_ctx\s+(\d+)', params)
                    if match: return int(match.group(1))
                
                # 3. Heuristics for "Cloud" / Large models that might default to 2048 in API but are actually larger
                # If we got 2048 (default) or nothing, let's look at the name.
                found_ctx = 2048
                if 'num_ctx' in params:
                    match = re.search(r'num_ctx\s+(\d+)', params)
                    if match: found_ctx = int(match.group(1))

                # If it's the default 2048, checking if it's a known large model to boost it
                if found_ctx == 2048:
                    lower_name = model_name.lower()
                    if ':cloud' in lower_name: return 128000 # Assume cloud tags are massive
                    if 'deepseek' in lower_name: return 32768
                    if 'qwen' in lower_name: return 32768
                    if 'glm-4' in lower_name: return 32768
                    if 'mistral-large' in lower_name: return 32768
                
                return found_ctx
        except: pass
        
    elif provider == "LM_Studio":
        # Heuristics based on name
        lower_name = model_name.lower()
        if '128k' in lower_name: return 128000
        if '32k' in lower_name: return 32000
        if '16k' in lower_name: return 16000
        if '8k' in lower_name: return 8192
        if '4k' in lower_name: return 4096
        
    return default_ctx

def calculate_safe_chunk_size(context_window):
    """Calculates a safe file batch size based on context window."""
    # Reserve for system prompt (approx 500) + JSON structure overhead + Output buffer (approx 1000)
    reserved = 2000
    available = context_window - reserved
    if available < 500: available = 500 # Floor
    
    # Approx tokens per filename (conservatively 15-20 tokens for long timestamps/paths)
    # With metadata, we assume ~60 tokens per file
    tokens_per_file = 60
    
    return max(10, int(available / tokens_per_file))

def tool_exists(name):
    return shutil.which(name) is not None

def run_json_command(cmd):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout.strip()) if result.stdout else None
    except Exception:
        return None

def normalize_metadata_dict(d):
    """Flattens common metadata fields into a compact dict with consistent keys."""
    if not d: return {}

    def pick(src, keys):
        for k in keys:
            for kk in src.keys():
                if kk.lower() == k.lower():
                    v = src.get(kk)
                    if v not in (None, "", []): return v
        return None

    out = {}
    out["title"] = pick(d, ["TrackName", "Track name", "Title"])
    out["album"] = pick(d, ["Album"])
    out["track"] = pick(d, ["Track", "TrackPosition", "TrackNumber", "Track name/Position"])
    out["artist"] = pick(d, ["Performer", "Artist", "AlbumArtist", "Author"])
    out["genre"] = pick(d, ["Genre"])
    out["year"] = pick(d, ["RecordedDate", "Year", "Date", "DateCreated", "OriginalReleaseDate"])
    out["comment"] = pick(d, ["Comment"])
    out["format"] = pick(d, ["Format", "FormatName", "FileType"])
    out["duration"] = pick(d, ["Duration", "DurationString"])
    out["bitrate"] = pick(d, ["OverallBitRate", "BitRate"])
    out["cover"] = pick(d, ["Cover", "CoverType", "CoverMime", "Picture", "PictureMimeType"])
    out["source_tool"] = pick(d, ["_source_tool"])

    # Remove empties
    return {k: v for k, v in out.items() if v not in (None, "", [], {})}

def summarize_metadata(meta):
    if not meta: return ""
    # Keep it compact and stable for the AI prompt
    parts = []
    for k in ["title", "album", "track", "artist", "genre", "year", "format", "duration", "bitrate", "cover", "comment", "source_tool"]:
        if k in meta:
            parts.append(f"{k}={meta[k]}")
    s = "; ".join(parts)
    if len(s) > MAX_METADATA_CHARS:
        s = s[:MAX_METADATA_CHARS] + "..."
    return s

def get_metadata_for_file(path):
    """Try mediainfo, exiftool, then ffprobe. Returns compact metadata dict."""
    # 1) mediainfo (best match to sample output)
    if tool_exists("mediainfo"):
        data = run_json_command(["mediainfo", "--Output=JSON", path])
        try:
            tracks = data.get("media", {}).get("track", [])
            general = next((t for t in tracks if t.get("@type") == "General"), None)
            if general:
                general["_source_tool"] = "mediainfo"
                return normalize_metadata_dict(general)
        except Exception:
            pass

    # 2) exiftool
    if tool_exists("exiftool"):
        data = run_json_command(["exiftool", "-json", path])
        try:
            if isinstance(data, list) and data:
                d0 = data[0]
                d0["_source_tool"] = "exiftool"
                return normalize_metadata_dict(d0)
        except Exception:
            pass

    # 3) ffprobe
    if tool_exists("ffprobe"):
        data = run_json_command([
            "ffprobe", "-v", "error", "-print_format", "json",
            "-show_format", "-show_streams", path
        ])
        try:
            tags = data.get("format", {}).get("tags", {})
            tags["_source_tool"] = "ffprobe"
            # add a few top-level format fields for extra context
            tags["Format"] = data.get("format", {}).get("format_name")
            tags["Duration"] = data.get("format", {}).get("duration")
            tags["OverallBitRate"] = data.get("format", {}).get("bit_rate")
            return normalize_metadata_dict(tags)
        except Exception:
            pass

    return {}

def get_available_models():
    models = []
    # Try Ollama
    try:
        resp = requests.get(f"{OLLAMA_API_BASE}/api/tags", timeout=2)
        if resp.status_code == 200:
            for m in resp.json().get('models', []):
                models.append({'name': m['name'], 'provider': 'Ollama'})
    except: pass

    # Try LM Studio (OpenAI-compatible)
    try:
        resp = requests.get(f"{LM_STUDIO_API_BASE}/models", timeout=2)
        if resp.status_code == 200:
            for m in resp.json().get('data', []):
                models.append({'name': m['id'], 'provider': 'LM_Studio'})
    except: pass

    if not models:
        print("\n[ERROR] No models found. Ensure Ollama (11434) or LM Studio (1234) is running.")
        sys.exit(1)
    return models

def get_ai_grouping_for_chunk(model_info, file_infos, verbose=False, raw=False):
    """Sends a specific batch of filenames to the AI and streams the response."""
    model = model_info['name']
    provider = model_info['provider']
    
    prompt = f"""
    You are a professional File Librarian. Analyze these filenames and create a grouping map.
    
    FILES (filename + metadata):
    {json.dumps(file_infos, indent=2)}

    INSTRUCTIONS:
    1. PRIMARY GOAL: Identify distinct categories based on semantic patterns, file prefixes, or sources (e.g., 'PXL' for Pixel Photos, 'Screenshot' for screenshots, 'Shopee' for shopping, 'TikTok' for videos).
    2. FALLBACK (TYPE-BASED): If filenames are vague strings or timestamps (e.g., '000ed587...', '17683547...'), group them by their file type/extension.
    3. USE METADATA: When available, use metadata fields like album, title, artist/performer, genre, year, and format to group files into meaningful folders (e.g., Album, Artist, Year).
    3. NAMING CONVENTIONS:
        - DO NOT use words like 'vague', 'random', 'misc', 'other', or 'generic' in folder names.
        - GOOD NAMES: 'Unlabeled_Photos', 'MP4_Videos', 'Timestamped_JPEG_Files', 'Camera_Roll_Archive'.
        - BAD NAMES: 'vague_files', 'miscellaneous_audio', 'random_mp4s'.
    4. Group 'Series' or 'Project' titles (e.g., matching common strings like 'Upcoming-Descent').
    5. Ignore leading numbers, 'unused', 'misc_', or duplicate names.
    6. VERY IMPORTANT: If a file is an individual/singular item and does not belong to a group of 2 or more files, map it to the folder "misc".
    
    OUTPUT:
    Return ONLY a valid JSON object. 
    Key = Professional, Descriptive Folder Name
    Value = List of strings/keywords/extensions found in the filenames that belong in that folder.
    """

    if provider == "Ollama":
        url = f"{OLLAMA_API_BASE}/api/chat"
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "format": "json", "stream": True, "options": {"temperature": 0.1}
        }
    else: # LM Studio / OpenAI
        url = f"{LM_STUDIO_API_BASE}/chat/completions"
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "stream": True # Streaming is key for LM Studio / OpenAI
        }

    if verbose:
        print("\n--- DEBUG: FILE INFOS SENT TO AI ---")
        print(json.dumps(file_infos, indent=2))
        print("\n--- DEBUG: FULL PROMPT ---")
        print(prompt)
        print("\n--- DEBUG: REQUEST PAYLOAD (METADATA) ---")
        print(json.dumps(payload, indent=2))

    full_content = ""
    thinking_content = ""
    printed_thinking_header = False
    try:
        response = requests.post(url, json=payload, stream=True)
        response.raise_for_status()
        
        print(f"\n--- AI RESPONSE ({model}) ---")
        for line in response.iter_lines():
            if not line: continue
            
            chunk_content = ""
            if provider == "Ollama":
                if raw:
                    try:
                        print(f"[DEBUG RAW LINE] {line.decode('utf-8', errors='ignore')}")
                    except Exception:
                        print(f"[DEBUG RAW LINE] {line}")
                data = json.loads(line)
                chunk_content = data.get('message', {}).get('content', '')
                chunk_thinking = data.get('message', {}).get('thinking', '')
                if chunk_thinking:
                    thinking_content += chunk_thinking
                    if verbose:
                        # GUI-like: print a single header, then stream thinking text on its own line(s)
                        if not printed_thinking_header:
                            print("\nTHINKING:\n", end='')
                            printed_thinking_header = True
                        print(chunk_thinking, end='', flush=True)
            else: # LM Studio / OpenAI
                decoded_line = line.decode('utf-8').strip()
                if not decoded_line: continue
                
                if decoded_line.startswith('data:'):
                    json_str = decoded_line[5:].strip()
                    if json_str == '[DONE]': break
                    try:
                        data = json.loads(json_str)
                        chunk_content = data.get('choices', [{}])[0].get('delta', {}).get('content', '')
                    except: pass
                else:
                    # Debug: Print lines that don't start with data: to see if we're missing something
                    if raw:
                        print(f"[DEBUG RAW]: {decoded_line}")
            
            if chunk_content:
                if verbose and printed_thinking_header:
                    # Ensure final content starts after thinking block
                    print("\n\nFINAL:\n", end='')
                print(chunk_content, end='', flush=True)
                full_content += chunk_content
        print("\n" + "-" * 40 + "\n")

        # Fallback: If streaming returned nothing (maybe model doesn't support it?), try non-streaming
        if not full_content and provider != "Ollama":
            print("Streaming yielded no content. Retrying with non-streaming request...")
            payload['stream'] = False
            try:
                response = requests.post(url, json=payload, timeout=300) 
                response.raise_for_status()
                data = response.json()
                full_content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
                print(f"{full_content}\n" + "-" * 40 + "\n")
            except requests.exceptions.HTTPError as http_err:
                print(f"Fallback Request Failed: {http_err}")
                if hasattr(response, 'text') and response.text:
                   error_text = response.text
                   print(f"Server Error Detail: {error_text}")
                   
                   # Friendly Error Explanations
                   if "n_ctx" in error_text or "context length" in error_text.lower():
                       print("\n" + "!" * 50)
                       print(" [TIP] CONTEXT LIMIT EXCEEDED")
                       print(" The batch of filenames is too large for this model's memory.")
                       print(f" -> ACTION: Edit the script and lower 'CHUNK_SIZE' (currently {CHUNK_SIZE}).")
                       print("!" * 50 + "\n")
                return {}
            except Exception as e:
                print(f"Fallback Exception: {e}")
                return {}

        if not full_content:
            print(f"Warning: Empty response from {provider}. The model might have output nothing or the stream format is unexpected.")
            if verbose and hasattr(response, "text") and response.text:
                print("\n--- DEBUG: EMPTY RESPONSE TEXT ---")
                print(response.text)
            if thinking_content:
                print("\n--- DEBUG: MODEL THINKING (OLLAMA) ---")
                print(thinking_content)
            return {}
            
        try:
            return json.loads(repair_json(full_content))
        except Exception as json_e:
            print(f"JSON Parse Failed: {json_e}")
            # Try a slightly more aggressive repair if the first one failed
            try:
                # If it's really messy, the AI might have started with some text. 
                # Find the first { and last }
                start = full_content.find('{')
                end = full_content.rfind('}')
                if start != -1 and end != -1:
                    return json.loads(repair_json(full_content[start:end+1]))
            except: pass
            return {}
    except Exception as e:
        print(f"Batch Analysis Failed ({provider}): {e}")
        # Note: 'response.text' would crash here because streaming consumed the context.
        # We use the full_content we already accumulated instead.
        if full_content:
            print(f"Content Received so far: {full_content[:300]}...")
        return {}

def main():
    parser = argparse.ArgumentParser(description="Organize files using AI.")
    parser.add_argument("-c", "--chunk-size", type=int, help="Manually set the number of files per batch (overrides auto-detection).")
    parser.add_argument("--no-metadata", action="store_true", help="Disable metadata extraction for prompts.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Print verbose debug output (prompts, payloads, metadata).")
    parser.add_argument("--raw-stream", action="store_true", help="Print raw streaming lines from the model (very noisy).")
    args = parser.parse_args()

    cur_dir = os.getcwd()
    script_name = os.path.basename(__file__)
    
    models = get_available_models()
    print("\n--- Available AI Models ---")
    for i, m in enumerate(models): 
        print(f"{i + 1}. {m['name']} ({m['provider']})")
    
    # Simple input loop robust to non-integers
    while True:
        try:
            choice_str = input("\nSelect model number: ")
            choice = int(choice_str) - 1
            if 0 <= choice < len(models):
                selected_model = models[choice]
                break
        except ValueError: pass
        print("Invalid selection.")

    # Determine Chunk Size
    if args.chunk_size:
        chunk_size = args.chunk_size
        print(f"\n[Config] Manual Chunk Size: {chunk_size}")
    else:
        print("\n[Config] Detecting optimal batch size...")
        ctx = get_model_context_window(selected_model['name'], selected_model['provider'])
        chunk_size = calculate_safe_chunk_size(ctx)
        print(f" > Model Context: ~{ctx} tokens")
        print(f" > Auto-Calculated Batch Size: {chunk_size} files")

    # Get and SORT all files to keep series together
    all_files = [f for f in os.listdir(cur_dir) if os.path.isfile(os.path.join(cur_dir, f))]
    all_files = sorted([f for f in all_files if f != script_name and not f.lower().startswith('flatten')])
    
    if not all_files:
        print("No files found to organize.")
        return

    # 1. AI Analysis Phase
    master_mapping = defaultdict(set)
    chunks = [all_files[i:i + chunk_size] for i in range(0, len(all_files), chunk_size)]
    
    print(f"\n[AI] Analyzing {len(all_files)} files in {len(chunks)} batches using {selected_model['name']}...")
    for idx, chunk in enumerate(chunks):
        print(f" > Analyzing Batch {idx + 1}/{len(chunks)}...")
        file_infos = []
        for f in chunk:
            info = {"filename": f}
            if not args.no_metadata:
                meta = get_metadata_for_file(os.path.join(cur_dir, f))
                if meta:
                    info["metadata"] = summarize_metadata(meta)
            file_infos.append(info)

        chunk_map = get_ai_grouping_for_chunk(selected_model, file_infos, verbose=args.verbose, raw=args.raw_stream)
        
        for folder, keywords in chunk_map.items():
            # Standardize: Find existing key with different case to prevent "The Rescue" vs "the rescue"
            target_key = folder
            for master_key in master_mapping.keys():
                if master_key.lower() == folder.lower():
                    target_key = master_key
                    break
            master_mapping[target_key].update(keywords)

    # 2. Assignment Phase (Mapping filenames to final folders)
    # We do this in memory first to count how many files each folder actually gets
    folder_assignments = defaultdict(list)
    remaining_files = all_files.copy()

    # Sort folders by length (longest first) to ensure "The Training" matches before "Training"
    sorted_folder_names = sorted(master_mapping.keys(), key=len, reverse=True)

    # Build lookup of metadata summaries for assignment matching
    metadata_cache = {}
    if not args.no_metadata:
        for f in all_files:
            meta = get_metadata_for_file(os.path.join(cur_dir, f))
            if meta:
                metadata_cache[f] = summarize_metadata(meta)

    for f in all_files:
        assigned = False
        haystack = f.lower()
        if f in metadata_cache:
            haystack = f"{haystack} {metadata_cache[f].lower()}"
        for folder in sorted_folder_names:
            if folder.lower() == MISC_FOLDER: continue
            
            keywords = master_mapping[folder]
            if any(k.lower() in haystack for k in keywords if len(k) > 1):
                folder_assignments[folder].append(f)
                assigned = True
                break
        
        if not assigned:
            folder_assignments[MISC_FOLDER].append(f)

    # 3. Global Threshold Check
    # If a folder ended up with only 1 file total, move that file to misc instead.
    final_plan = defaultdict(list)
    for folder, files in folder_assignments.items():
        if folder == MISC_FOLDER:
            final_plan[MISC_FOLDER].extend(files)
        elif len(files) < 2:
            # Demote singular files to misc
            final_plan[MISC_FOLDER].extend(files)
        else:
            final_plan[folder] = files

    # 4. Review and Execute
    print("\n--- Proposed Organization ---")
    for folder in sorted(final_plan.keys()):
        print(f"  {folder}: {len(final_plan[folder])} files")

    if input("\nProceed? (y/n): ").lower() != 'y': return

    count = 0
    for folder, files in final_plan.items():
        dest_path = os.path.join(cur_dir, folder)
        if not os.path.exists(dest_path): os.makedirs(dest_path)
        
        for f in files:
            try:
                shutil.move(os.path.join(cur_dir, f), os.path.join(dest_path, f))
                count += 1
            except: pass

    print(f"\nDone! Organized {count} files.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[Exiting...] Operation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n[CRITICAL ERROR] {e}")
        sys.exit(1)
