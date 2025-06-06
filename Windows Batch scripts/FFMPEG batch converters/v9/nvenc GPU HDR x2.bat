@echo off
COLOR 0C

FOR %%A IN (%*) DO (
    ECHO %%A


    ffmpeg -y -init_hw_device cuda=gpu:0 -filter_hw_device gpu -hwaccel cuvid -hwaccel_output_format cuda -i %%A -c:v av1_nvenc -cq:v 16 -c:a copy -map 0 -preset p4 -tune hq -lookahead_level auto -rc-lookahead 53 -profile:v main10 -b_ref_mode:v middle -spatial-aq 1 -temporal-aq 1 -vf "scale_cuda='iw*2:ih*2:force_original_aspect_ratio=decrease:force_divisible_by=4:interp_algo=lanczos'" %%A_temp_HDR_x2.mkv 

mkvmerge.exe -o %%A_HDR_Horz_x2_CUBE.mkv --colour-matrix 0:9 --colour-range 0:1 --colour-transfer-characteristics 0:16 --colour-primaries 0:9 --max-content-light 0:1000 --max-frame-light 0:300 --max-luminance 0:1000 --min-luminance 0:0.01 --chromaticity-coordinates 0:0.68,0.32,0.265,0.690,0.15,0.06 --white-colour-coordinates 0:0.3127,0.3290 --attachment-mime-type application/x-cube --attach-file "C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\LUT\Colorspace LUTS\5-NBCU_PQ2SDR_DL_RESOLVE17-VRT_v1.2.cube" %%A_temp_HDR_x2.mkv 

    del %%A_temp_HDR_x2.mkv 

    mkvinfo.exe %%A_HDR_Horz_x2_CUBE.mkv

    mkdir x2
    move %%A_HDR_Horz_x2_CUBE.mkv x2\

)

REM format=p010le,zscale=-2:7680:filter=lanczos:min=input:m=input:tin=input:t=input:pin=input:p=input,format=yuv420p10le,
:: scale cuda: 
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