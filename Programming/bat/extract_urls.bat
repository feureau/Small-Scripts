@echo off
setlocal enabledelayedexpansion

:: Output file to store extracted URLs
set outputFile=extracted_urls.txt

:: Clear the output file if it already exists
if exist "%outputFile%" del "%outputFile%"

:: Loop through all .url files in the current directory
for %%f in ("*.url") do (
    :: Read each line in the file
    for /f "usebackq delims=" %%l in ("%%~f") do (
        :: Check if the line starts with "URL="
        if "%%l" neq "" (
            set line=%%l
            if "!line:~0,4!"=="URL=" (
                :: Extract the URL and append it to the output file
                echo !line:~4! >> "%outputFile%"
            )
        )
    )
)

echo URLs have been extracted to %outputFile%.
pause
