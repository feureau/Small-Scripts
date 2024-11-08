@echo off
COLOR 0C

FOR %%A IN (%*) DO (
    ECHO %%A
ffmpeg -i %%A -ss 00:10:00 -vf "fps=1/60,cropdetect"  -f null -

)


COLOR 0A

PAUSE >nul
EXIT