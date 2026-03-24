@echo off
setlocal enabledelayedexpansion

:: Validate that a file has been dropped onto the script
if "%~1"=="" (
    echo [Error] Please drag and drop a text file onto this batch script.
    pause
    exit /b
)

:: Define the absolute path to mpv.exe
set "MPV_PATH="C:\Users\Feureau\AppData\Roaming\mpv\mpv.exe""

:: Initialize the list variable
set "URL_LIST="

:: Iterate through the text file to collect URLs
for /f "usebackq tokens=*" %%A in ("%~1") do (
    set "URL_LIST=!URL_LIST! "%%A""
)

:: Execute mpv using the defined path and the concatenated list
start "" %MPV_PATH% %URL_LIST%

endlocal