import os
import shutil
import json
import sys
import re
from collections import defaultdict

try:
    import requests
except ImportError:
    print("Error: The 'requests' library is missing. Run: pip install requests")
    sys.exit(1)

# --- CONFIGURATION ---
OLLAMA_API_TAGS = "http://localhost:11434/api/tags"
OLLAMA_API_CHAT = "http://localhost:11434/api/chat"
CHUNK_SIZE = 250  # Batches of 250 files to balance context and speed
MISC_FOLDER = "misc"

def get_available_models():
    try:
        response = requests.get(OLLAMA_API_TAGS)
        response.raise_for_status()
        return [m['name'] for m in response.json()['models']]
    except:
        print("\n[ERROR] Could not connect to Ollama. Ensure 'ollama serve' is running.")
        sys.exit(1)

def get_ai_grouping_for_chunk(model, filenames):
    """Sends a specific batch of filenames to the AI."""
    prompt = f"""
    You are a professional File Librarian. Analyze these raw filenames and create a grouping map.
    
    FILENAMES:
    {json.dumps(filenames)}

    INSTRUCTIONS:
    1. Identify 'Series' or 'Project' titles. 
    2. Group abbreviations with their clear full-name counterparts (e.g., 'TT' with 'The Training', 'AH' with 'Anibody Home').
    3. If multiple files share a distinct name (like 'Upcoming-Descent'), create a folder for them.
    4. Ignore leading numbers, 'unused', 'misc_', or duplicate names like 'Found_Found'.
    5. VERY IMPORTANT: If a file is an individual/singular item and does not belong to a series of 2 or more files, map it to the folder "misc".
    
    OUTPUT:
    Return ONLY a valid JSON object. 
    Key = Folder Name
    Value = List of strings/keywords found in the filenames that belong in that folder.
    """

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "format": "json",
        "stream": False,
        "options": {"temperature": 0.1}
    }

    try:
        response = requests.post(OLLAMA_API_CHAT, json=payload)
        content = response.json()['message']['content']
        content = re.sub(r'```json\s*|\s*```', '', content).strip()
        return json.loads(content)
    except Exception as e:
        print(f"Batch Analysis Failed: {e}")
        return {}

def main():
    cur_dir = os.getcwd()
    script_name = os.path.basename(__file__)
    
    models = get_available_models()
    print("\n--- Available Ollama Models ---")
    for i, m in enumerate(models): print(f"{i + 1}. {m}")
    model = models[int(input("\nSelect model number: ")) - 1]

    # Get and SORT all files to keep series together
    all_files = [f for f in os.listdir(cur_dir) if os.path.isfile(os.path.join(cur_dir, f))]
    all_files = sorted([f for f in all_files if f != script_name and not f.lower().startswith('flatten')])
    
    if not all_files:
        print("No files found to organize.")
        return

    # 1. AI Analysis Phase
    master_mapping = defaultdict(set)
    chunks = [all_files[i:i + CHUNK_SIZE] for i in range(0, len(all_files), CHUNK_SIZE)]
    
    print(f"\n[AI] Analyzing {len(all_files)} files in {len(chunks)} batches...")
    for idx, chunk in enumerate(chunks):
        print(f" > Analyzing Batch {idx + 1}/{len(chunks)}...")
        chunk_map = get_ai_grouping_for_chunk(model, chunk)
        
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

    for f in all_files:
        assigned = False
        for folder in sorted_folder_names:
            if folder.lower() == MISC_FOLDER: continue
            
            keywords = master_mapping[folder]
            if any(k.lower() in f.lower() for k in keywords if len(k) > 1):
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
    main()