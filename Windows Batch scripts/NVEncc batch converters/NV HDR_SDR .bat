@echo off
COLOR 0C

FOR %%A IN (%*) DO (
    ECHO %%A

NVEncC64 --avhw --codec av1 --tier 1 --profile main --cqp 16:20:25 --preset p1 --output-depth 10 --multipass 2pass-full  --nonrefp --aq --aq-temporal --aq-strength 8 --lookahead 32  --lookahead-level auto --transfer auto --audio-copy --chapter-copy --key-on-chapter --metadata copy --vpp-colorspace lut3d="C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\LUT\NBCUniversal\LUTS_for_Software_DaVinci_Premiere_Avid_FinalCutPro\DaVinci-Resolve-with-Video-Range-Tag\5-NBCU_PQ2SDR_DL_RESOLVE17-VRT_v1.2.cube" -i %%A -o %%A_SDR.mkv 



    mkdir SDR
    move %%A_SDR.mkv SDR\
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