:@ECHO OFF
:COLOR 0B
:TITLE HDR MetaJECTOR 2.8 - HDR Metadata Injector
:ECHO                                "HDR MetaJECTOR"
:ECHO  HDR Metadata Injection Tool for YouTube Videos - (UI for mkvmerge and mkvinfo)
:ECHO                                  Version 2.8
:ECHO.
:ECHO    Created by Wesley Knapp    wesleyknapp.com    wesleyknappfilm@gmail.com
:ECHO.
:ECHO ______________________________________________________________________________
:ECHO.
:ECHO - Don't forget to include file extension (.mkv) when entering Output File name
:ECHO - Make sure this tool, mkvmerge, and mkvinfo are all in the same directory
:ECHO - Output File will be created in the same directory as this tool
:ECHO.
:ECHO.
SET /P IN="Drag and Drop Input File Here: "
:SET /P OUT="Output File Name: "

:lutquestion
:SET /P LUTYN="Have Ye An SDR Conversion LUT? (Y/N): "
:IF /I "%LUTYN%" EQU "Y" goto :lutyes
:IF /I "%LUTYN%" EQU "N" goto :lutno
:GOTO :lutquestion

:lutyes
:SET /P LUT="Drag and Drop LUT Here: "
:ECHO.
:ECHO. 
:ECHO Input Filepath: %IN%
:ECHO Output Filepath: %~dp0%OUT%
:ECHO LUT Filepath: %LUT%
:ECHO.
:ECHO.
:ECHO Shake 'N' Bake!
:ECHO.
:PAUSE



COLOR 0C
mkvmerge.exe -o %IN%_cube.mp4 --colour-matrix 0:9 --colour-range 0:1 --colour-transfer-characteristics 0:16 --colour-primaries 0:9 --max-content-light 0:1000 --max-frame-light 0:1000 --max-luminance 0:1000 --min-luminance 0:0.01 --chromaticity-coordinates 0:0.68,0.32,0.265,0.690,0.15,0.06 --white-colour-coordinates 0:0.3127,0.3290 --attachment-mime-type application/x-cube --attach-file HDR-Monitor_v2-3_WesleyKnapp.cube %IN%

mkvinfo.exe %IN%_cube.mp4
COLOR 0A
ECHO.
ECHO Processing complete!  See file specs above.
ECHO Press Any Key To Exit...
PAUSE >nul
EXIT

:lutno
ECHO.
ECHO. 
ECHO Input Filepath: %IN%
ECHO Output Filepath: %~dp0%OUT%
ECHO.
ECHO.
ECHO Shake 'N' Bake!
ECHO.
PAUSE

COLOR 0C
mkvmerge.exe -o %IN%_cube.mp4 --colour-matrix 0:9 --colour-range 0:1 --colour-transfer-characteristics 0:16 --colour-primaries 0:9 --max-content-light 0:1000 --max-frame-light 0:300 --max-luminance 0:1000 --min-luminance 0:0.01 --chromaticity-coordinates 0:0.68,0.32,0.265,0.690,0.15,0.06 --white-colour-coordinates 0:0.3127,0.3290 %IN%

mkvinfo.exe %IN%_cube.mp4
COLOR 0A
ECHO.
ECHO Processing complete!  See Output File specs above.
ECHO Press Any Key To Exit...
PAUSE >nul
EXIT