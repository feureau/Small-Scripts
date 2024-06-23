COLOR 0C

FOR %%A IN (%*) DO (
    REM Now your batch file handles %%A instead of %1
    REM No need to use SHIFT anymore.
    ECHO %%A
    mkvmerge.exe -o %1_HDR_cube.mkv --attachment-mime-type application/x-cube --attach-file "C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\LUT\Colorspace LUTS\5-NBCU_PQ2SDR_DL_RESOLVE17-VRT_v1.2.cube" %1

    mkvinfo.exe %1_cube.mkv
)

REM mkvmerge.exe -o %1_cube_ACES.mp4  --no-chapters --colour-matrix 0:9 --colour-range 0:1 --colour-transfer-characteristics 0:16 --colour-primaries 0:9 --max-content-light 0:1000 --max-frame-light 0:1000 --max-luminance 0:1000 --min-luminance 0:0.01 --chromaticity-coordinates 0:0.68,0.32,0.265,0.690,0.15,0.06 --white-colour-coordinates 0:0.3127,0.3290 --attachment-mime-type application/x-cube --attach-file C:\Users\Feureau\Videos\Wesley_Knapp_HDR_Tools\ACES_Rec2020-ST2084_to_Rec709.cube %1


COLOR 0A
ECHO.
ECHO Processing complete!  See file specs above.
ECHO Press Any Key To Exit...
::PAUSE >nul
EXIT