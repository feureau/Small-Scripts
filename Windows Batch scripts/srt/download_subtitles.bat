@echo off
:: Script to download YouTube subtitles using yt-dlp

:: Ask for the YouTube link
set /p yt_link=Enter the YouTube video link: 

:: Check if yt_link is empty
if "%yt_link%"=="" (
    echo You did not provide a link. Exiting...
    pause
    exit /b
)

:: Run yt-dlp to download subtitles in SRT format
yt-dlp --write-sub --sub-format "srt" --skip-download "%yt_link%"

:: Check if yt-dlp succeeded
if %errorlevel% equ 0 (
    echo Subtitles downloaded successfully!
) else (
    echo Failed to download subtitles. Please check the link and try again.
)

:: Pause to keep the console open
pause
