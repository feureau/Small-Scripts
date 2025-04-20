 
@echo off
SETLOCAL

REM Get the directory of this script
SET "PROJECT_DIR=%~dp0"

REM Define the environment path inside the project folder
SET "ENV_PATH=%PROJECT_DIR%env"

echo Activating Conda environment...
call conda activate "%ENV_PATH%"

echo Pulling the latest updates from GitHub...
git pull origin main

echo Installing any new dependencies...
pip install -r "%PROJECT_DIR%requirements.txt"

echo Update complete!
pause
