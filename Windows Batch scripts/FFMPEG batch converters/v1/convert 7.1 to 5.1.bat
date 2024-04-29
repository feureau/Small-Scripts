COLOR 0C

FOR %%A IN (%*) DO (
    ::REM Now your batch file handles %%A instead of %1
    ::REM No need to use SHIFT anymore.
    ECHO %%A
    ffmpeg -i %%A -map 0:0 -map 0:1 -c:v copy -c:a:0 ac3 -ac:a:0 6 -c:a:1 aac %%A.mov
)

COLOR 0A
::ECHO.
::ECHO Processing complete!  See file specs above.
::ECHO Press Any Key To Exit...
PAUSE >nul
EXIT