@echo off
COLOR 0C

FOR %%A IN (%*) DO (
    ECHO %%A

NVEncC64 --avhw --codec av1 --tier 1 --profile high --qvbr 1 --preset p1 --output-depth 10 --multipass 2pass-full --nonrefp --aq --aq-temporal --aq-strength 0 --lookahead 32  --lookahead-level auto --transfer auto --audio-copy --chapter-copy --key-on-chapter --sub-copy --metadata copy --vpp-resize algo=nvvfx-superres,superres-mode=0 --output-res 4320x4320,preserve_aspect_ratio=increase -i %%A -o %%A_8K.mkv 

    mkdir 8K
    move %%A_8K.mkv 8K\
)

REM --output-csp yuv444 

REM 
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