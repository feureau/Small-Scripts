#!/usr/bin/env python
import argparse
import subprocess
import sys

ENV_NAME = "myenv"
PYTHON_VERSION = "3.12"
# List of packages to install in the environment.
PACKAGES = ["audiblez", "pillow", "wxpython"]

def conda_env_exists(env_name):
    try:
        result = subprocess.check_output(["conda", "env", "list"], universal_newlines=True)
    except FileNotFoundError:
        sys.exit("Conda not found. Please ensure that Conda is installed and in your PATH.")
    return env_name in result

def create_conda_env(env_name):
    print(f"Creating conda environment '{env_name}' with Python {PYTHON_VERSION}...")
    try:
        subprocess.check_call(["conda", "create", "-n", env_name, f"python={PYTHON_VERSION}", "-y"])
    except subprocess.CalledProcessError:
        sys.exit("Error creating the conda environment.")
    print(f"Installing packages: {', '.join(PACKAGES)} ...")
    try:
        # Use 'conda run' to execute pip install within the new environment.
        subprocess.check_call(["conda", "run", "-n", env_name, "pip", "install"] + PACKAGES)
    except subprocess.CalledProcessError:
        sys.exit("Error installing packages in the conda environment.")

def run_audiblez_ui(env_name):
    print("Launching audiblez-ui...")
    try:
        # This will run the audiblez-ui command in the specified environment.
        subprocess.check_call(["conda", "run", "-n", env_name, "audiblez-ui"])
    except subprocess.CalledProcessError:
        sys.exit("Error launching audiblez-ui.")

def main():
    parser = argparse.ArgumentParser(
        description="Launch audiblez-ui inside a conda environment. "
                    "If the environment does not exist or if -iv/--install-venv is specified, "
                    "it will create it."
    )
    parser.add_argument(
        "-iv", "--install-venv", action="store_true",
        help="Force (re)installation of the conda environment and packages."
    )
    args = parser.parse_args()

    if args.install_venv or not conda_env_exists(ENV_NAME):
        create_conda_env(ENV_NAME)
    else:
        print(f"Conda environment '{ENV_NAME}' already exists. Skipping environment creation.")
    
    run_audiblez_ui(ENV_NAME)

if __name__ == "__main__":
    main()
