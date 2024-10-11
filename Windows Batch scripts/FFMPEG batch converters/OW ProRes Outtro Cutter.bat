@echo off
COLOR 0C

FOR %%A IN (%*) DO (
    ECHO %%A

start /b /low /wait ffmpeg -ss 00:00.00 -to 00:18.51 -accurate_seek -i %%A -c:v prores_ks -profile:v 3 -vendor apl0 -pix_fmt yuv422p10le -c:a copy -c:s copy -map 0 -map_metadata 0 %%A_cut.mkv

    mkdir cut
    move %%A_cut.mkv cut\
)

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