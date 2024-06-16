COLOR 0C
mkvmerge.exe -o %1_cube_Flanel.mp4 --colour-matrix 0:9 --colour-range 0:1 --colour-transfer-characteristics 0:16 --colour-primaries 0:9 --max-content-light 0:1000 --max-frame-light 0:1000 --max-luminance 0:1000 --min-luminance 0:0.01 --chromaticity-coordinates 0:0.68,0.32,0.265,0.690,0.15,0.06 --white-colour-coordinates 0:0.3127,0.3290 --attachment-mime-type application/x-cube --attach-file C:\Users\Feureau\Videos\Wesley_Knapp_HDR_Tools\flannel_ninja_hdr_to_sdr_custom_conversion_lut_v1.0.cube %1

mkvinfo.exe %1_cube_Flanel.mp4
COLOR 0A
ECHO.
ECHO Processing complete!  See file specs above.
ECHO Press Any Key To Exit...
::PAUSE >nul
EXIT