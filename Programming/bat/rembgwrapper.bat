@echo off
REM ================================
REM rembgwrapper.bat
REM Processes image files using rembg inside a virtual environment.
REM Usage example:
REM   rembgwrapper.bat *.jpg --model birefnet-massive
REM ================================

REM --- Configuration ---
set "VENV_PATH=F:\AI\rembg\venv"
set "WORK_DIR=F:\AI\rembg"

REM --- Change to working directory ---
cd /d "%WORK_DIR%"

REM --- Activate the virtual environment ---
call "%VENV_PATH%\Scripts\activate"

REM --- Parse arguments ---
REM The first argument is the file mask (or single file).
set "FILEMASK=%1"
shift

REM Build options variable from the remaining arguments.
set "OPTS="
:buildOptions
if "%~1"=="" goto optionsDone
   set "OPTS=%OPTS% %1"
   shift
goto buildOptions
:optionsDone

echo.
echo File mask: %FILEMASK%
echo Options: %OPTS%
echo.

REM --- Enable delayed expansion for the loop ---
setlocal enabledelayedexpansion

REM --- Loop over each matching file ---
for %%F in (%FILEMASK%) do (
    set "INPUT=%%F"
    set "OUTPUT=%%~nF_T.png"
    echo Processing file: !INPUT!
    echo Running: rembg i !OPTS! "!INPUT!" "!OUTPUT!"
    rembg i !OPTS! "!INPUT!" "!OUTPUT!"
)

endlocal

REM --- Deactivate the virtual environment ---
call deactivate
