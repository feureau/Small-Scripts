@echo off
COLOR 0C

:: Initialize a temporary file to store processed file names
set processed_files=%~dp0processed_files.txt
if exist "%processed_files%" del "%processed_files%"

:: Loop through all arguments (files provided as input)
FOR %%A IN (%*) DO (
    ECHO Processing file: %%~A

    :: Call the Python script (SRT_extractor.py) and pass the file as an argument
    python "%~dp0SRT_extractor.py" "%%~A" >> "%processed_files%" 2>&1
)

:: Output the summary from the Python script
COLOR 0A
ECHO.
ECHO Processing complete! See details below:
type "%processed_files%"
ECHO.

:: Cleanup temporary file
if exist "%processed_files%" del "%processed_files%"

PAUSE >nul
EXIT
