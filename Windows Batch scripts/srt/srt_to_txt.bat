@echo off
:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not added to PATH.
    pause
    exit /b
)

:: Check if the input file (dragged file) is provided
if "%~1"=="" (
    echo Error: No input file provided. Drag and drop an SRT file onto this script.
    pause
    exit /b
)

:: Run the Python script with the provided input file
python srt_to_transcript.py "%~1"

pause
