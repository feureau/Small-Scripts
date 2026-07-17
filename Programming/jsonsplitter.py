import json
import os
import argparse
import sys

def split_json(input_file, output_dir):
    # Try reading the input file
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: The file '{input_file}' was not found.")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: The file '{input_file}' is not a valid JSON.")
        sys.exit(1)

    # Make sure the root is a list
    if not isinstance(data, list):
        print("Error: The JSON file must contain a list of objects.")
        sys.exit(1)

    # Ensure output directory exists (if a specific one was provided)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    success_count = 0
    for item in data:
        # Get the filename from the JSON object
        filename = item.get("filename")
        if not filename:
            print("Warning: Found an object without a 'filename' key. Skipping...")
            continue
        
        # Ensure the filename ends with .json
        if not filename.endswith('.json'):
            filename += '.json'
            
        output_path = os.path.join(output_dir, filename)
        
        # Write the individual JSON file
        try:
            with open(output_path, 'w', encoding='utf-8') as out_f:
                # indent=2 keeps it pretty and readable
                json.dump(item, out_f, indent=2, ensure_ascii=False)
            success_count += 1
        except Exception as e:
            print(f"Error writing to '{output_path}': {e}")
            
    print(f"✅ Successfully created {success_count} JSON files in '{os.path.abspath(output_dir)}'.")

def main():
    parser = argparse.ArgumentParser(description="Split a JSON list into individual files based on their 'filename' key.")
    parser.add_argument("input_file", help="Path to the input JSON file (e.g., main.json)")
    parser.add_argument("-o", "--output", default=".", help="Output directory (defaults to current working directory)")
    
    args = parser.parse_args()
    split_json(args.input_file, args.output)

if __name__ == "__main__":
    main()