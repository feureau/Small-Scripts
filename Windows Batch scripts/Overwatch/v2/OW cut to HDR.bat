@echo off
COLOR 0C

FOR %%A IN (%*) DO (
    ECHO %%A


NVEncC64 --avhw --trim 293:1131 --codec av1 --tier 1 --profile high --cqp 43 --preset p7 --output-depth 10 --multipass 2pass-full --lookahead 32 --gop-len 4 --nonrefp --aq --aq-temporal --aq-strength 0 --transfer auto --audio-codec ac3 --audio-bitrate 640 --chapter-copy --key-on-chapter --metadata copy --vpp-ngx-truehdr maxluminance=1000,middlegray=18,saturation=200,contrast=200 --colormatrix bt2020nc --colorprim bt2020 --transfer smpte2084 -i %%A -o %%A_HDR.mkv 

    mkdir HDR
    move %%A_HDR.mkv  HDR\
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