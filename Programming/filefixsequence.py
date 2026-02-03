import os
import re

def fix_sequences():
    target_dir = os.getcwd()
    print(f"Targeting: {target_dir}")

    # Regex to capture the number at the start and the rest of the name
    # Group 1: Leading digits, Group 2: The rest of the filename
    pattern = re.compile(r'^(\d+)(.*)')

    files_to_fix = []
    max_val = 0

    # First pass: Identify files and find the maximum number for padding depth
    for filename in os.listdir(target_dir):
        if os.path.isfile(os.path.join(target_dir, filename)):
            match = pattern.match(filename)
            if match:
                num_str = match.group(1)
                num_val = int(num_str)
                files_to_fix.append((filename, num_str, match.group(2)))
                if num_val > max_val:
                    max_val = num_val

    if not files_to_fix:
        print("No files found starting with a sequence number.")
        return

    # Determine padding length based on the largest number found
    padding_length = len(str(max_val))
    print(f"Padding numbers to {padding_length} digits.")

    # Second pass: Rename
    count = 0
    for original_name, num_str, rest_of_name in files_to_fix:
        padded_num = num_str.zfill(padding_length)
        new_filename = f"{padded_num}{rest_of_name}"

        if original_name != new_filename:
            try:
                os.rename(
                    os.path.join(target_dir, original_name),
                    os.path.join(target_dir, new_filename)
                )
                print(f"Fixed: {original_name} -> {new_filename}")
                count += 1
            except OSError as e:
                print(f"Error renaming {original_name}: {e}")

    print(f"Done. {count} files corrected.")

if __name__ == "__main__":
    fix_sequences()