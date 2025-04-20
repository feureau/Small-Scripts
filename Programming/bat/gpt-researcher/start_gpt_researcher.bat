@echo off
SETLOCAL

REM Get the directory of this script
SET "PROJECT_DIR=%~dp0"
SET "ENV_PATH=%PROJECT_DIR%env"

echo Loading environment variables...
if exist "%PROJECT_DIR%.env" (
    for /f "tokens=*" %%i in (%PROJECT_DIR%.env) do set %%i
)

echo Activating Conda environment...
conda run --live-stream --prefix "%ENV_PATH%" python -m uvicorn main:app --reload

ENDLOCAL
