@echo off

:: Check if at least one argument is given
if "%~1"=="" (
    echo Usage: %~nx0 file1.md [file2.md ...]
    exit /b 1
)

:: Loop through all provided .md files
for %%F in (%*) do (
    if exist "%%F" (
        echo Converting %%F to %%~nF.docx...
        pandoc "%%F" -t docx -o "%%~nF.docx"
    ) else (
        echo File not found: %%F
    )
)

echo Conversion complete!
