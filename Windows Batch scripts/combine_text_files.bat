@echo off
setlocal enabledelayedexpansion

:: Check if no files were dragged and dropped
if "%~1"=="" (
    echo No files were dragged and dropped!
    pause
    exit /b
)

:: Define the output file name
set output=combined_output.txt

:: Delete the output file if it already exists
if exist "%output%" del "%output%"

:: Loop through all the dragged files
for %%f in (%*) do (
    echo Adding: "%%~f"
    type "%%~f" >> "%output%"
    echo. >> "%output%"  :: Adds a blank line between files
)

echo Files combined successfully into "%output%"
pause
