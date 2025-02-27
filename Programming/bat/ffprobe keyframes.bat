@echo off
COLOR 0C

FOR %%A IN (%*) DO (
    ECHO %%A

ffprobe -loglevel error -skip_frame nokey -select_streams v:0 -show_entries frame=pts_time -of csv=print_section=0 %%A

)


COLOR 0A

PAUSE >nul
EXIT