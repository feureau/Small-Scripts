@echo off
COLOR 0C

FOR %%A IN (%*) DO (
    ECHO %%A

    ffmpeg -y -hwaccel cuda -hwaccel_output_format cuda -i %%A -vf "scale_cuda=-2:1080:format=p010le:interp_algo=lanczos" -c:v hevc_nvenc -c:a copy -map 0 -cq:v 16 -b_ref_mode 0 -preset fast -tune hq -lookahead_level auto -profile:v main10 -spatial-aq 1 %%A.HD.SDR.mov
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