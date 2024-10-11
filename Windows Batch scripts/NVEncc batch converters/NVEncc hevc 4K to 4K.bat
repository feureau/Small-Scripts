@echo off
COLOR 0C

FOR %%A IN (%*) DO (
    ECHO %%A

start /b /low /wait NVEncC64 --avhw --codec hevc --profile high --qvbr 0 --preset p4 --output-depth 10 --multipass 2pass-full --lookahead 32 --nonrefp --aq --aq-temporal --aq-strength 0 --transfer auto --audio-copy --chapter-copy --key-on-chapter --sub-copy --metadata copy --output-csp yuv444 --vpp-resize algo=nvvfx-superres,superres-mode=0,superres-strength=1.0 --output-res 2160x2160,preserve_aspect_ratio=increase --output-csp yuv444 -i %%A -o %%A_4K_.mkv 

    mkdir 4K
    move %%A_4K_.mkv  4K\
)

REM --colormatrix bt2020nc --colorprim bt2020 --transfer smpte2084
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