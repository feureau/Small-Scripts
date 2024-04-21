@echo off
COLOR 0C

FOR %%A IN (%*) DO (
    ECHO %%A

    ffmpeg -y -hwaccel cuda -hwaccel_output_format cuda -i %%A -vf "scale_cuda=-2:4320:format=p010le:interp_algo=lanczos" -c:v hevc_nvenc -c:a copy -map 0 -cq:v 16 -b_ref_mode 0 -preset fast -tune hq -lookahead_level auto -profile:v main10 -color_primaries bt2020 -colorspace bt2020nc -color_trc smpte2084 -spatial-aq 1 %%A.8K.HDR.mov

    mkvmerge.exe -o %%A.8K.HDR.mov_cube_ACES.mp4  --no-chapters --colour-matrix 0:9 --colour-range 0:1 --colour-transfer-characteristics 0:16 --colour-primaries 0:9 --max-content-light 0:1000 --max-frame-light 0:1000 --max-luminance 0:1000 --min-luminance 0:0.01 --chromaticity-coordinates 0:0.68,0.32,0.265,0.690,0.15,0.06 --white-colour-coordinates 0:0.3127,0.3290 --attachment-mime-type application/x-cube --attach-file C:\Users\Feureau\Videos\Wesley_Knapp_HDR_Tools\ACES_Rec2020-ST2084_to_Rec709.cube %%A.8K.HDR.mov

    mkvinfo.exe %%A.8K.HDR.mov_cube_ACES.mp4
)

:: other opt    -pix_fmt p010le yuv420p10le -pix_fmt p010le 
::-vf scale_cuda=720:404:format=p010le
::  -color_primaries 9 -color_trc 16 -colorspace 9 -color_range 1 -profile:v 2

:: working ffmpeg -y -vsync 0 -hwaccel nvdec -hwaccel_output_format cuda -i test.mp4 -vf "scale_cuda=-2:720" -c:a copy -c:v hevc_nvenc -b:v 5M output1.mp4
:: -threads 9 

::=w=-2:h=4320

::scale=iw*(7680/iw):ih*(4320/ih)
::libx265
::x=(w-text_w)/2:y=((h/3)-th)
COLOR 0A
::ECHO.
::ECHO Processing complete!  See file specs above.
::ECHO Press Any Key To Exit...
PAUSE >nul
EXIT