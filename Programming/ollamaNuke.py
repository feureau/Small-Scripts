"""
DOCUMENTATION: OLLAMA GUI HISTORY TERMINATOR (v4.0)
-----------------------------------------
FUNCTIONALITY:
This script performs a deep clean of the Ollama Windows GUI by:
1. Force-terminating 'ollama app.exe' and 'ollama.exe'.
2. Locating the Electron 'web-cache' and 'Local Storage' directories.
3. Recursively deleting the contents of the GUI data folder to clear chats.

NOTE: This documentation block must be updated and included with every 
subsequent iteration or modification of this script to maintain 
traceability and operational safety.
-----------------------------------------
"""

import os
import shutil
import platform
import subprocess
import time

def nuke_ollama_gui():
    if platform.system() != "Windows":
        print("Error: This script is optimized for the Windows Ollama GUI.")
        return

    # 1. Kill processes to unlock the cache files
    processes = ["ollama app.exe", "ollama.exe"]
    for proc in processes:
        print(f"Terminating {proc}...")
        subprocess.run(["taskkill", "/F", "/IM", proc, "/T"], capture_output=True)
    
    time.sleep(2) # Necessary for Electron to release file handles

    # 2. Define the GUI's local data path
    # On Windows, Electron apps store data in %APPDATA% (Roaming) or %LOCALAPPDATA%
    # For Ollama, the GUI data is typically in %LOCALAPPDATA%\ollama
    local_appdata = os.environ.get("LOCALAPPDATA", "")
    gui_data_path = os.path.join(local_appdata, "ollama")

    # Folders that store the actual "chats" and interface state
    cache_folders = ["IndexedDB", "Local Storage", "Session Storage", "Cache", "Network"]

    found_any = False
    if os.path.exists(gui_data_path):
        for folder in cache_folders:
            target_path = os.path.join(gui_data_path, folder)
            if os.path.exists(target_path):
                try:
                    shutil.rmtree(target_path)
                    print(f"CLEARED: {folder}")
                    found_any = True
                except Exception as e:
                    print(f"COULD NOT CLEAR {folder}: {e}")
    
    # Also check for the specific history file in the .ollama user folder
    user_ollama = os.path.join(os.path.expanduser("~"), ".ollama", "history")
    if os.path.exists(user_ollama):
        os.remove(user_ollama)
        print("CLEARED: Terminal History File")
        found_any = True

    if found_any:
        print("\nSUCCESS: All chat history and GUI cache have been nuked.")
    else:
        print("\nDIAGNOSIS: No history folders found. Ensure you are using the official Ollama tray app.")

if __name__ == "__main__":
    nuke_ollama_gui()