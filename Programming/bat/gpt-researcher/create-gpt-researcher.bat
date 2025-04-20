 
@echo off
SETLOCAL

REM Get the directory of this script
SET "PROJECT_DIR=%~dp0"

REM Define the environment path inside the project folder
SET "ENV_PATH=%PROJECT_DIR%env"

echo Creating Conda environment at %ENV_PATH%...
conda create --prefix "%ENV_PATH%" python=3.11 -y

echo Activating environment...
call conda activate "%ENV_PATH%"

echo Installing dependencies...
if exist "%PROJECT_DIR%requirements.txt" (
    pip install -r "%PROJECT_DIR%requirements.txt"
) else (
    echo No requirements.txt found. Skipping package installation.
)

echo Starting GPT Researcher...
conda run --live-stream --prefix "%ENV_PATH%" python -m uvicorn main:app --reload

ENDLOCAL
pause
