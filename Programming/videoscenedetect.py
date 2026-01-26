import sys
import os
import glob
from scenedetect import open_video, SceneManager, ContentDetector

def frame_to_timecode(frame_num, fps):
    """
    Converts a frame number to SMPTE timecode (HH:MM:SS:FF).
    """
    # Ensure fps is a float to avoid division errors
    fps = float(fps)
    
    total_seconds = int(frame_num / fps)
    frames = int(frame_num % fps)
    
    hours = int(total_seconds / 3600)
    minutes = int((total_seconds % 3600) / 60)
    seconds = int(total_seconds % 60)
    
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frames:02d}"

def write_custom_edl(file_path, scene_list, fps, title="VIDEO"):
    """
    Writes a DaVinci Resolve compatible CMX 3600 EDL manually.
    """
    try:
        with open(file_path, 'w') as f:
            f.write(f"TITLE: {title}\n")
            f.write("FCM: NON-DROP FRAME\n\n")
            
            for i, (start, end) in enumerate(scene_list):
                # EDL events typically start at 1
                index = f"{i + 1:03d}"
                
                # Get frame numbers from FrameTimecode objects
                start_frame = start.get_frames()
                end_frame = end.get_frames()
                
                # Convert to HH:MM:SS:FF
                tc_start = frame_to_timecode(start_frame, fps)
                tc_end = frame_to_timecode(end_frame, fps)
                
                # CMX 3600 Format: 
                # ID  REEL  TYPE  TRANSITION  SRC_IN  SRC_OUT  DST_IN  DST_OUT
                # AX = Auxiliary Reel (Standard for file imports)
                line = f"{index}  AX       V     C        {tc_start} {tc_end} {tc_start} {tc_end}\n"
                f.write(line)
                
    except Exception as e:
        print(f"Error inside EDL writer: {e}")

def process_video(file_path):
    print(f"--------------------------------------------------")
    print(f"Processing: {file_path}")
    
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} not found.")
        return

    try:
        # 1. Open the video
        video = open_video(file_path)
        fps = video.frame_rate
        
        # 2. Configure Scene Manager
        scene_manager = SceneManager()
        # threshold=27.0 is standard. 
        # Increase to ~50 if you get too many false cuts.
        # Decrease to ~15 if it misses dark scenes.
        scene_manager.add_detector(ContentDetector(threshold=27.0))

        # 3. Detect Scenes
        print("Detecting scenes...")
        scene_manager.detect_scenes(video, show_progress=True)
        
        # 4. Get list of cuts
        scene_list = scene_manager.get_scene_list()
        print(f"Found {len(scene_list)} scenes.")

        # 5. Generate Output Filename
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        output_edl = f"{base_name}.edl"

        # 6. Write EDL using our custom function
        write_custom_edl(output_edl, scene_list, fps, title=base_name)
        
        print(f"Success: Saved EDL to {output_edl}")

    except Exception as e:
        print(f"Error processing {file_path}: {e}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python videoscenedetect.py <video_files>")
        sys.exit(1)

    files_to_process = []
    
    # Handle Glob expansion (Windows/CMD doesn't do this automatically)
    for arg in sys.argv[1:]:
        if '*' in arg or '?' in arg:
            expanded = glob.glob(arg)
            files_to_process.extend(expanded)
        else:
            files_to_process.append(arg)

    if not files_to_process:
        print("No files found matching the pattern.")
        sys.exit(1)

    for file_path in files_to_process:
        process_video(file_path)

if __name__ == "__main__":
    main()