COLOR 0C

FOR %%A IN (%*) DO (
    ::REM Now your batch file handles %%A instead of %1
    ::REM No need to use SHIFT anymore.
    ECHO %%A
    magick %%A %%A.tif
    magick %%A %%A.jpg
)

COLOR 0A
::ECHO.
::ECHO Processing complete!  See file specs above.
::ECHO Press Any Key To Exit...
PAUSE >nul
EXIT