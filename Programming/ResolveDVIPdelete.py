import os
import shutil
import platform

def delete_dvip_folder():
    user_home = os.path.expanduser('~')
    system = platform.system()

    if system == 'Windows':
        dvip_path = os.path.join(user_home, 'AppData', 'Roaming', 'Blackmagic Design', 'DaVinci Resolve', 'Support', 'DVIP')
    elif system == 'Darwin':  # macOS
        dvip_path = os.path.join(user_home, 'Library', 'Application Support', 'Blackmagic Design', 'DaVinci Resolve', 'Support', 'DVIP')
    elif system == 'Linux':
        dvip_path = os.path.join(user_home, '.local', 'share', 'DaVinciResolve', 'Support', 'DVIP')
    else:
        print(f'Unsupported operating system: {system}')
        return

    if os.path.exists(dvip_path):
        try:
            shutil.rmtree(dvip_path)
            print(f'Successfully deleted: {dvip_path}')
        except Exception as e:
            print(f'Error deleting {dvip_path}: {e}')
    else:
        print(f'DVIP folder does not exist at: {dvip_path}')

if __name__ == '__main__':
    delete_dvip_folder()
