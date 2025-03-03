@echo off
setlocal

:: Check if .venv exists
if not exist ".venv\" (
    echo Virtual environment not found. First run:
    echo   uv venv .venv
    echo   uv sync
    exit /b 1
)

:: Activate environment
call .venv\Scripts\activate.bat

:: Run kokoro-tts with all arguments
python kokoro-tts %*

endlocal