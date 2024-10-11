@echo off
COLOR 0C

FOR %%A IN (%*) DO (
    ECHO %%A

start /b /belownormal /wait ffmpeg -ss 00:00.00 -to 00:18.51 -accurate_seek -y -init_hw_device cuda=gpu:0 -filter_hw_device gpu -hwaccel cuvid -hwaccel_output_format cuda -i %%A -c:v hevc_nvenc -cq:v 8 -c:a copy -c:s copy -map 0 -map_metadata 0 -preset p4 -tune hq -profile:v main10 -spatial-aq 1 -temporal-aq 1 %%A_split.mkv

    mkdir split
    move %%A_split.mkv split\
)

REM -y -init_hw_device cuda=gpu:0 -filter_hw_device gpu -hwaccel cuvid -hwaccel_output_format cuda
REM format=p010le,zscale=-2:7680:filter=lanczos:min=input:m=input:tin=input:t=input:pin=input:p=input,format=yuv420p10le,

::thumbnail,scale='if(gt(iw,ih),7680,trunc(oh*a/2)*2)':'if(gt(iw,ih),trunc(ow/a/2)*2,7680)'
::scale=w=7680:h=7680:force_original_aspect_ratio=1:flags=lanczos
::scale=iw*(7680/iw):ih*(4320/ih)
::libx265
::x=(w-text_w)/2:y=((h/3)-th)
COLOR 0A
::ECHO.
::ECHO Processing complete!  See file specs above.
::ECHO Press Any Key To Exit...
PAUSE >nul
EXIT