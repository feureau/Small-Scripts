import os
import json
import argparse

def merge_json_files():
    # Setup argument parser with mutually exclusive flags
    parser = argparse.ArgumentParser(
        description="Merge JSON files in the current working directory into a single 'main.json'."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        '-f', '--filename', 
        action='store_true', 
        help="Inject 'filename' field (without extension) into each merged object."
    )
    group.add_argument(
        '-fe', '--filename-ext', 
        action='store_true', 
        help="Inject 'filename' field (with extension) into each merged object."
    )
    args = parser.parse_args()

    # Get the current working directory
    cwd = os.getcwd()
    
    print(f"Scanning for JSON files in: {cwd}")
    if args.filename:
        print("Note: '-f' flag active. Filenames without extensions will be injected.")
    elif args.filename_ext:
        print("Note: '-fe' flag active. Filenames with extensions will be injected.")

    # Locate all .json files in the CWD, excluding 'main.json'
    json_files = [
        f for f in os.listdir(cwd) 
        if f.endswith('.json') and f.lower() != 'main.json'
    ]
    
    if not json_files:
        print("No JSON files found to merge.")
        return

    merged_data = []
    success_count = 0
    error_count = 0

    for filename in sorted(json_files):
        file_path = os.path.join(cwd, filename)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # Determine what value to inject if a flag is passed
                target_value = None
                if args.filename:
                    target_value = os.path.splitext(filename)[0]
                elif args.filename_ext:
                    target_value = filename

                # If a flag was specified, inject the "filename" field at the top
                if target_value is not None:
                    if isinstance(data, list):
                        for i, item in enumerate(data):
                            if isinstance(item, dict):
                                new_dict = {"filename": target_value}
                                new_dict.update(item)
                                data[i] = new_dict
                    elif isinstance(data, dict):
                        new_dict = {"filename": target_value}
                        new_dict.update(data)
                        data = new_dict

                # Merge data
                if isinstance(data, list):
                    merged_data.extend(data)
                else:
                    merged_data.append(data)
                    
                success_count += 1
        except json.JSONDecodeError:
            print(f"Error: '{filename}' is not a valid JSON file. Skipping.")
            error_count += 1
        except Exception as e:
            print(f"Error reading '{filename}': {e}. Skipping.")
            error_count += 1

    # Write the consolidated list to main.json in the current working directory
    output_path = os.path.join(cwd, 'main.json')
    try:
        with open(output_path, 'w', encoding='utf-8') as out_f:
            json.dump(merged_data, out_f, indent=2, ensure_ascii=False)
        
        print("\n--- Merge Complete ---")
        print(f"Successfully merged {success_count} file(s) into 'main.json'.")
        if error_count > 0:
            print(f"Skipped {error_count} file(s) due to errors.")
        print(f"Total merged entries: {len(merged_data)}")
        print(f"Output saved to: {output_path}")
    except Exception as e:
        print(f"Failed to write 'main.json': {e}")

if __name__ == "__main__":
    merge_json_files()