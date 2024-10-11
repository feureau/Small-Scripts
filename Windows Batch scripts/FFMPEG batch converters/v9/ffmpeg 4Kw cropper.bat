@echo off
COLOR 0C

FOR %%A IN (%*) DO (
    ECHO %%A

start /b /low /wait ffmpeg -y -init_hw_device cuda=gpu:0 -filter_hw_device gpu -hwaccel cuvid -hwaccel_output_format cuda -c:v av1_cuvid -crop 0x0x1056x1056 -resize 2160x2700 -i %%A -aspect 2160/2700 -c:v av1_nvenc -cq:v 16 -c:a copy -c:s copy -map 0 -map_metadata 0 -preset p4 -tune hq -lookahead_level auto -rc-lookahead 53 -profile:v main10 -b_ref_mode:v middle -spatial-aq 1 -temporal-aq 1 -force_key_frames chapters+0 -g 0 -vf "scale_cuda='2160:2700:force_original_aspect_ratio=decrease:force_divisible_by=4:interp_algo=lanczos'" %%A_crop.mkv


)

REM -lookahead_level auto -rc-lookahead 53 -b_ref_mode:v middle

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