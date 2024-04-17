COLOR 0C

FOR %%A IN (%*) DO (
    ::REM Now your batch file handles %%A instead of %1
    ::REM No need to use SHIFT anymore.
    ECHO %%A
    pandoc -i %%A -t docx -o %%A.docx
)

COLOR 0A
::ECHO.
::ECHO Processing complete!  See file specs above.
::ECHO Press Any Key To Exit...
PAUSE >nul
EXIT








::@echo off
::setlocal enabledelayedexpansion
::for /f "tokens=2,5,7,8 delims=," %%G in ('c:\ffmpeg\bin\ffprobe -i %1 -print_format csv -show_chapters -loglevel error  2^> nul') do (
::   set padded=00%%G
::   "c:\ffmpeg\bin\ffmpeg" -ss %%H -to %%I -i %1 -c:v copy -c:a copy -metadata title="%%J" -y "%~dpnx1-!padded:~-3!.mkv"
::)

::https://stackoverflow.com/questions/30305953/is-there-an-elegant-way-to-split-a-file-by-chapter-using-ffmpeg