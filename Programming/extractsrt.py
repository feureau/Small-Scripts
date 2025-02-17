# extractsrt.py
import sys
import os
import subprocess
import glob
from colorama import init, Fore

# Initialize colorama for Windows console colors
init()

def find_mkvextract():
    """Check if mkvextract is available in the system PATH"""
    try:
        subprocess.run(["mkvextract", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return "mkvextract"
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None

def get_subtitle_tracks(file_path):
    """Get list of subtitle tracks with SRT codec using mkvinfo"""
    try:
        result = subprocess.run(["mkvinfo", file_path], capture_output=True, text=True, check=True)
        tracks = []
        current_track = {}
        
        for line in result.stdout.split('\n'):
            if "Track number:" in line:
                if current_track:
                    tracks.append(current_track)
                current_track = {}
            elif "Codec ID:" in line:
                current_track['codec'] = line.split(":")[1].strip()
            elif "Track type:" in line:
                current_track['type'] = line.split(":")[1].strip().lower()
            elif "Track ID:" in line:
                current_track['id'] = line.split(":")[1].strip()
        
        if current_track:
            tracks.append(current_track)
            
        return [t for t in tracks if t.get('type') == 'subtitles' and t.get('codec') == 's_text/utf8']
    
    except subprocess.CalledProcessError as e:
        return None

def extract_srt(file_path, mkvextract_path):
    """Extract SRT subtitles from a file using mkvextract"""
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    output_dir = os.path.dirname(file_path)
    extracted = []
    
    tracks = get_subtitle_tracks(file_path)
    if not tracks:
        return False, "No SRT subtitle tracks found"
    
    for track in tracks:
        output_file = os.path.join(output_dir, f"{base_name}.{track['id']}.srt")
        command = [
            mkvextract_path,
            "tracks",
            file_path,
            f"{track['id']}:{output_file}"
        ]
        
        try:
            subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            extracted.append(output_file)
        except subprocess.CalledProcessError as e:
            return False, f"Error extracting track {track['id']}: {e.stderr.decode()}"
    
    return True, extracted

def main():
    if len(sys.argv) < 2:
        print(Fore.RED + "Usage: extractsrt.py <file_pattern> (e.g., extractsrt.py *.mkv)")
        sys.exit(1)

    mkvextract_path = find_mkvextract()
    if not mkvextract_path:
        print(Fore.RED + "Error: mkvextract not found. Please install MKVToolNix and add it to PATH")
        print(Fore.RED + "Download from https://mkvtoolnix.download/")
        sys.exit(1)

    file_pattern = sys.argv[1]
    video_files = glob.glob(file_pattern)
    total_files = len(video_files)
    processed = []
    failed = []

    print(Fore.CYAN + f"\nProcessing {total_files} files...\n")

    for idx, file_path in enumerate(video_files, 1):
        if not os.path.isfile(file_path):
            continue
            
        print(Fore.WHITE + f"[{idx}/{total_files}] Processing: {os.path.basename(file_path)}")
        success, result = extract_srt(file_path, mkvextract_path)
        
        if success:
            processed.append((file_path, result))
            print(Fore.GREEN + f"  ✓ Extracted {len(result)} subtitle(s)")
        else:
            failed.append((file_path, result))
            print(Fore.RED + f"  ✗ {result}")

    # Print summary
    print(Fore.CYAN + "\nProcessing complete!\n")
    print(Fore.WHITE + "="*50)
    print(Fore.GREEN + f"Successfully processed: {len(processed)} files")
    for file_path, tracks in processed:
        print(Fore.WHITE + f"\n• {os.path.basename(file_path)}")
        for track in tracks:
            print(Fore.GREEN + f"  → {os.path.basename(track)}")
    
    if failed:
        print(Fore.RED + f"\nFailed to process: {len(failed)} files")
        for file_path, error in failed:
            print(Fore.WHITE + f"\n• {os.path.basename(file_path)}")
            print(Fore.RED + f"  → {error}")
    
    print(Fore.WHITE + "="*50 + "\n")

if __name__ == "__main__":
    main()