import os
import sys
import glob
from scenedetect import open_video, SceneManager
from scenedetect.detectors import ContentDetector
from scenedetect.output import write_scene_list_edl
from scenedetect.video_splitter import split_video_ffmpeg

def process_video(video_path: str):
    """
    Executes frame-accurate scene detection on the target video path,
    generating a corresponding CMX 3600 EDL file and isolated clip segments
    within the current active working directory.
    """
    # Resolve absolute path to guarantee stability across directory contexts
    abs_video_path = os.path.abspath(video_path)
    if not os.path.exists(abs_video_path):
        print(f"[-] Execution Error: File context not found at -> {abs_video_path}")
        return

    filename = os.path.basename(abs_video_path)
    base_name, _ = os.path.splitext(filename)
    
    # Establish target outputs relative to the current active shell directory
    current_working_dir = os.getcwd()
    edl_path = os.path.join(current_working_dir, f"{base_name}.edl")
    output_template = os.path.join(current_working_dir, f"{base_name}-Scene-$SCENE_NUMBER.mp4")
    
    print(f"\n[+] Ingesting: {filename}")
    print(f"    Source Path: {abs_video_path}")
    print(f"    Destination: {current_working_dir}")
    
    try:
        # Instantiate operational pipeline elements
        video = open_video(abs_video_path)
        scene_manager = SceneManager()
        
        # ContentDetector tracks structural frame shifts across HSL space
        scene_manager.add_detector(ContentDetector(threshold=27.0))
        
        print("    Analyzing structural transitions...")
        scene_manager.detect_scenes(video, show_progress=True)
        scene_list = scene_manager.get_scene_list()
        
        if not scene_list:
            print("    [-] No shot transitions detected matching threshold parameters.")
            return
            
        print(f"    [+] Exporting Edit Decision List -> {edl_path}")
        write_scene_list_edl(output_path=edl_path, scene_list=scene_list)
        
        print("    [+] Extracting individual scene sub-clips via FFmpeg...")
        split_video_ffmpeg(
            input_video_path=abs_video_path,
            scene_list=scene_list,
            output_file_template=output_template,
            show_progress=True
        )
        print(f"[+] Operational sequence successful for: {filename}\n")
        
    except Exception as error:
        print(f"    [-] Execution failure processing {filename}: {error}")

def main():
    # If no explicitly targeted strings are passed, evaluate current directory for MP4 assets
    if len(sys.argv) < 2:
        targets = glob.glob("*.mp4")
    else:
        targets = []
        for argument in sys.argv[1:]:
            # Explicit expansion ensures wildcard support on systems lacking shell expansion (e.g. Windows CMD)
            matched_files = glob.glob(argument)
            if matched_files:
                targets.extend(matched_files)
            else:
                targets.append(argument)
                
    if not targets:
        print("[-] Target Resolution Failure: No media elements matched the input criteria.")
        sys.exit(1)
        
    for target in targets:
        process_video(target)

if __name__ == '__main__':
    main()