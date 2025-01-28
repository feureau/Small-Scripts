import os
import shutil

def main():
    # The folder from which the script is called (current working directory)
    cwd = os.getcwd()
    
    # Gather all .mov, .mp4, .mkv files
    # (case-insensitive check for extensions)
    exts = (".mov", ".mp4", ".mkv")
    all_files = os.listdir(cwd)
    video_files = [
        f for f in all_files
        if os.path.isfile(os.path.join(cwd, f)) 
        and f.lower().endswith(exts)
    ]
    
    # Sort them if you want consistent ordering (optional)
    video_files.sort()
    
    # Start the folder index at -1 so the first check moves it to 0
    dirN = -1
    
    # We'll move through the list of video_files in chunks of 15
    idx = 0
    limit = 15  # number of files per folder

    # While we still have videos to move
    while idx < len(video_files):
        # Find the next numeric directory name that does not exist
        dirN += 1
        while os.path.exists(str(dirN)):
            dirN += 1
        
        # Create the new folder
        os.mkdir(str(dirN))
        
        # Slice the next `limit` files
        chunk = video_files[idx : idx + limit]
        idx += limit
        
        # Move those files into the newly created folder
        for filename in chunk:
            src_path = os.path.join(cwd, filename)
            dst_path = os.path.join(cwd, str(dirN), filename)
            shutil.move(src_path, dst_path)
    
    print("Task Done!")

if __name__ == "__main__":
    main()
