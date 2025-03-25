@echo off
echo =====================================
echo Creating local Conda environment...
echo =====================================

REM Create the environment in the "env" folder with Python 3.11
conda create --prefix .\env python=3.11 -y

IF %ERRORLEVEL% NEQ 0 (
    echo Error: Failed to create the Conda environment.
    pause
    exit /B %ERRORLEVEL%
)

echo.
echo =====================================
echo Installing Open-WebUI using pip...
echo =====================================

REM Use conda run with live stream output to install Open-WebUI
conda run --live-stream --prefix .\env pip install open-webui

IF %ERRORLEVEL% NEQ 0 (
    echo Error: Failed to install Open-WebUI.
    pause
    exit /B %ERRORLEVEL%
)

echo.
echo =====================================
echo Setup complete.
echo You can now run Open-WebUI with:
echo   conda run --live-stream --prefix .\env open-webui serve
echo =====================================
pause
