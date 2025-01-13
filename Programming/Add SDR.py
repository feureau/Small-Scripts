import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

def process_file(file_path):
    # Get the input file's directory
    input_dir = os.path.dirname(file_path)
    output_dir = os.path.join(input_dir, "sdr")
    os.makedirs(output_dir, exist_ok=True)

    base_name = os.path.splitext(os.path.basename(file_path))[0]
    output_file = os.path.join(output_dir, f"{base_name}_SDR.mkv")

    print(f"Processing: {file_path}")

    # Run mkvmerge command with SDR tags
    mkvmerge_command = [
        "mkvmerge",
        "-o", output_file,
        "--colour-matrix", "0:1",
        "--colour-range", "0:1",
        "--colour-transfer-characteristics", "0:1",
        "--colour-primaries", "0:1",
        file_path
    ]
    subprocess.run(mkvmerge_command, check=True)

    # Run mkvinfo to display file info
    mkvinfo_command = ["mkvinfo", output_file]
    subprocess.run(mkvinfo_command, check=True)

    print(f"Moved processed file to: {output_dir}\n")


def process_files_parallel(file_list):
    # Determine max number of workers (based on CPU cores)
    max_workers = min(4, os.cpu_count() or 1)  # Use up to 4 or number of CPU cores

    print(f"Starting parallel processing with {max_workers} workers...\n")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(process_file, file_path) for file_path in file_list]

        # Wait for all tasks to complete
        for future in futures:
            future.result()  # This will re-raise any exceptions that occurred

    print("Processing complete!")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python script.py <file1> <file2> ...")
        sys.exit(1)

    # Get list of files from command-line arguments
    files = sys.argv[1:]
    process_files_parallel(files)
