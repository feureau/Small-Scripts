import os
import sys

def diagnose_cuda_setup():
    print("--- CUDA Setup Diagnostics ---")

    # 1. Check for CUDA_PATH environment variable
    cuda_path_env = os.environ.get("CUDA_PATH")
    if cuda_path_env:
        print(f"CUDA_PATH environment variable is set: {cuda_path_env}")
    else:
        print("CUDA_PATH environment variable is NOT set.")
        print("This variable is needed for onnxruntime-gpu to find CUDA.")
        print("Please set CUDA_PATH to your CUDA Toolkit installation directory (e.g., C:\\Program Files\\NVIDIA GPU Computing Toolkit\\CUDA\\vXXX).")
        return False  # Stop further checks if CUDA_PATH is missing

    # 2. Check if CUDA_PATH exists
    if os.path.exists(cuda_path_env):
        print(f"CUDA_PATH directory exists: {cuda_path_env}")
    else:
        print(f"ERROR: CUDA_PATH directory DOES NOT EXIST: {cuda_path_env}")
        print("Please ensure CUDA_PATH points to a valid CUDA Toolkit installation directory.")
        return False

    # 3. Check CUDA bin directory existence
    cuda_bin_dir = os.path.join(cuda_path_env, "bin")
    if os.path.exists(cuda_bin_dir):
        print(f"CUDA bin directory exists: {cuda_bin_dir}")
    else:
        print(f"ERROR: CUDA bin directory DOES NOT EXIST: {cuda_bin_dir}")
        print("The 'bin' subdirectory is expected within the CUDA Toolkit installation.")
        print("Please check your CUDA Toolkit installation structure.")
        return False

    # 4. Check if CUDA bin is in PATH
    path_env = os.environ.get("PATH")
    if path_env:
        if cuda_bin_dir in path_env: # Simple substring check - might need more robust check for complex PATHs
            print(f"CUDA bin directory IS in PATH environment variable.")
        else:
            print(f"ERROR: CUDA bin directory IS NOT in PATH environment variable.")
            print(f"CUDA bin directory: {cuda_bin_dir}")
            print(f"Current PATH: {path_env}")
            print("Please add the CUDA bin directory to your PATH environment variable.")
            print("This allows Windows to find CUDA DLLs.")
            return False
    else:
        print("WARNING: PATH environment variable is empty or not set.") # Should not normally happen, but just in case
        print("This is unusual. PATH is needed for finding DLLs.")
        return False # Technically, CUDA bin not being in empty PATH is still an error

    # 5. Attempt to import onnxruntime and check for CUDA provider
    try:
        import onnxruntime as ort
        providers = ort.get_available_providers()
        if 'CUDAExecutionProvider' in providers:
            print("onnxruntime-gpu imported SUCCESSFULLY.")
            print("CUDAExecutionProvider IS available in onnxruntime.")
            print(f"Available providers: {providers}")
            print("CUDA setup appears to be CORRECTLY configured for onnxruntime.")
            return True
        else:
            print("onnxruntime-gpu imported SUCCESSFULLY.")
            print("ERROR: CUDAExecutionProvider is NOT available in onnxruntime.")
            print(f"Available providers: {providers}")
            print("This indicates that onnxruntime-gpu was not able to load the CUDA provider.")
            print("Please double-check CUDA Toolkit and cuDNN installation and environment variables.")
            return False

    except ImportError as e:
        print("ERROR: Failed to import onnxruntime-gpu.")
        print(f"ImportError: {e}")
        print("Please ensure onnxruntime-gpu is correctly installed in your virtual environment.")
        return False
    except Exception as e:
        print("ERROR: An unexpected error occurred while checking onnxruntime-gpu.")
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    success = diagnose_cuda_setup()
    if success:
        print("\nCUDA setup diagnostics COMPLETED SUCCESSFULLY.")
    else:
        print("\nCUDA setup diagnostics FAILED. Please review the errors and warnings above.")
