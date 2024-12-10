@echo off
COLOR 0C

:: Check if a file is dragged onto the script
IF "%~1"=="" (
    ECHO No video file specified. Please drag and drop a video file onto the script.
    PAUSE
    EXIT /B
)

:: Call the Python script with the given arguments
python "%~dp0process_video.py" %*

:: End the script
COLOR 0A
PAUSE >NUL
EXIT
