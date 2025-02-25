import subprocess
import time
from pathlib import Path

def get_process_status(process_name):
    try:
        # Check if any process with the given name is running
        result = subprocess.run(["pgrep", "-f", process_name], capture_output=True, text=True)
        return len(result.stdout.strip().split("\n")) > 0
    except subprocess.CalledProcessError:
        return False

def start_service(command):
    try:
        print(f"Starting {command[0]}...")
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            universal_newlines=True
        )
        time.sleep(2)  # Give the service time to start
        return process
    except Exception as e:
        print(f"Error starting {command[0]}: {e}")
        return None

def stop_service(process):
    try:
        print(f"Stopping {process.args[0]}...")
        process.terminate()
        # Wait for the process to terminate
        process.wait(timeout=5)
        if process.returncode == 0:
            print(f"{process.args[0]} stopped successfully.")
        else:
            print(f"{process.args[0]} did not stop gracefully.")
    except Exception as e:
        print(f"Error stopping {process.args[0]}: {e}")

def main():
    # Initialize processes
    ollama_process = None
    openwebui_process = None

    try:
        # Start Ollama if not running
        if not get_process_status("ollama"):
            ollama_process = start_service(["ollama", "serve"])
            if ollama_process is None:
                return

        # Start OpenWebUI if not running
        if not get_process_status("openwebui"):
            openwebui_process = start_service(["openwebui", "start"])
            if openwebui_process is None:
                return

        print("\nServices are running.")
        print(f"Ollama status: {'running' if ollama_process else 'stopped'}")
        print(f"OpenWebUI status: {'running' if openwebui_process else 'stopped'}")

        # Wait for user input to stop
        input("\nPress Enter to stop the services...")

        # Stop services gracefully
        if ollama_process:
            stop_service(ollama_process)
        if openwebui_process:
            stop_service(openwebui_process)

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()