import os
import sys
import re

def print_help():
    print("""
    Text Remove String - Bulk Delete Tool
    -------------------------------------
    Scans all text files in the CURRENT folder and removes text matching
    a specific Regular Expression pattern.

    USAGE:
      python txtremovestring.py "<pattern>" [run]
      python txtremovestring.py -h

    ARGUMENTS:
      <pattern>   The Regex pattern to find and remove.
                  IMPORTANT: Put quotes around the pattern!
      run         (Optional) If present, the script will actually MODIFY files.
                  If missing, the script runs in PREVIEW mode.

    EXAMPLES:
      1. Preview removing (h.238):
         python txtremovestring.py "\(h\.[^)]*\)"

      2. Actually remove (h.238):
         python txtremovestring.py "\(h\.[^)]*\)" run

    COMMON REGEX PATTERNS:
      "\(h\.[^)]*\)"  -> Matches (h.123), (h.abc), etc. (Safest)
      "\(h\.[0-9]*\)" -> Matches (h.123) only numbers.
      "\(.*?\)"       -> Matches ANY text inside parentheses.
    """)

def main():
    # 1. Check for Help Flag or Missing Arguments
    args = sys.argv[1:]
    
    if not args or "-h" in args or "--help" in args:
        print_help()
        sys.exit(0)

    # 2. Get the pattern
    raw_pattern = args[0]
    
    # 3. Check for "run" command
    is_live_run = False
    if len(args) > 1:
        if args[1].lower() == "run":
            is_live_run = True
        else:
            print(f"Error: Unknown argument '{args[1]}'. Did you mean 'run'?")
            print_help()
            sys.exit(1)

    # 4. Compile Regex
    try:
        regex = re.compile(raw_pattern)
    except re.error as e:
        print(f"\n[ERROR] Invalid Regex pattern: {e}")
        print("Tip: Don't forget to escape special characters like brackets: \( \)")
        sys.exit(1)

    # 5. Define extensions
    valid_extensions = ('.txt', '.md', '.csv', '.json', '.xml', '.log')
    cwd = os.getcwd()
    
    print("-" * 60)
    print(f"Scanning Folder: {cwd}")
    print(f"Target Pattern:  {raw_pattern}")
    print(f"Action Mode:     {'[REAL RUN - SAVING CHANGES]' if is_live_run else '[PREVIEW ONLY]'}")
    print("-" * 60)

    files_modified = 0
    files_found = 0

    # 6. Process Files
    for filename in os.listdir(cwd):
        if filename == os.path.basename(__file__): continue
        
        if filename.lower().endswith(valid_extensions):
            file_path = os.path.join(cwd, filename)

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Find matches
                matches = regex.findall(content)
                
                if matches:
                    files_found += 1
                    unique_matches = list(set(matches)) # Show unique instances found
                    display_matches = unique_matches[:3] # Only show first 3 examples
                    
                    print(f"[{'FIXED' if is_live_run else 'FOUND'}] {filename}")
                    print(f"        Found {len(matches)} instance(s). Examples: {display_matches}")

                    if is_live_run:
                        new_content = regex.sub('', content)
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        files_modified += 1
            
            except UnicodeDecodeError:
                # Silently skip non-text files or warn user
                pass
            except Exception as e:
                print(f"[ERROR] {filename}: {e}")

    print("-" * 60)
    if is_live_run:
        print(f"Done. Modified {files_modified} files.")
    else:
        print(f"Preview Done. Found matches in {files_found} files.")
        print("To apply changes, run the command again with 'run' at the end.")

if __name__ == "__main__":
    main()