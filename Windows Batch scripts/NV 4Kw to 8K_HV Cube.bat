@echo off
COLOR 0C

FOR %%A IN (%*) DO (
    ECHO %%A

NVEncC64 --avhw --codec av1 --tier 1 --profile high --cqp 30:38:46 --preset p1 --output-depth 10 --multipass 2pass-full --weightp --nonrefp --aq --aq-temporal --aq-strength 0 --lookahead 32  --lookahead-level auto --transfer auto --audio-copy --chapter-copy --key-on-chapter --sub-copy --metadata copy --vpp-resize algo=ngx-vsr,vsr-quality=1 --output-res 4320x4320,preserve_aspect_ratio=increase -i %%A -o %%A_HDR_8K_Horz.mkv 

NVEncC64 --avhw --codec hevc --tier high --profile main10 --cqp 12 --preset p1 --output-depth 10 --multipass 2pass-full  --aq --aq-temporal --aq-strength 0 --lookahead 32  --lookahead-level auto --transfer auto --audio-copy --chapter-copy --key-on-chapter --sub-copy --metadata copy --crop 1056,0,1056,0 --vpp-resize algo=ngx-vsr,vsr-quality=1 --output-res 4320x4320,preserve_aspect_ratio=increase -i %%A -o %%A_HDR_8K_Vert.mkv 

mkvmerge.exe -o %%A_HDR_8K_Horz_CUBE.mkv --colour-matrix 0:9 --colour-range 0:1 --colour-transfer-characteristics 0:16 --colour-primaries 0:9 --max-content-light 0:1000 --max-frame-light 0:300 --max-luminance 0:1000 --min-luminance 0:0.01 --chromaticity-coordinates 0:0.68,0.32,0.265,0.690,0.15,0.06 --white-colour-coordinates 0:0.3127,0.3290 --attachment-mime-type application/x-cube --attach-file "C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\LUT\Colorspace LUTS\5-NBCU_PQ2SDR_DL_RESOLVE17-VRT_v1.2.cube" %%A_HDR_8K_Horz.mkv 

mkvmerge.exe -o %%A_HDR_8K_Vert_CUBE.mkv --colour-matrix 0:9 --colour-range 0:1 --colour-transfer-characteristics 0:16 --colour-primaries 0:9 --max-content-light 0:1000 --max-frame-light 0:300 --max-luminance 0:1000 --min-luminance 0:0.01 --chromaticity-coordinates 0:0.68,0.32,0.265,0.690,0.15,0.06 --white-colour-coordinates 0:0.3127,0.3290 --attachment-mime-type application/x-cube --attach-file "C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\LUT\Colorspace LUTS\5-NBCU_PQ2SDR_DL_RESOLVE17-VRT_v1.2.cube" %%A_HDR_8K_Vert.mkv 

mkvinfo.exe %%A_HDR_8K_Horz_CUBE.mkv

mkvinfo.exe %%A_HDR_8K_Vert_CUBE.mkv

mkvmerge.exe -o 8k\%%c.mkv --split chapters:all %%~nxA_HDR_8K_Vert_CUBE.mkv


    mkdir 8k
    move %%A_HDR_8K_Horz_CUBE.mkv 8k\
    move %%A_HDR_8K_Vert_CUBE-*.mkv 8k\

REM     del %%A_temp_HDR_4K.mkv
REM     del %%A_temp_HDR_4K_vert_crop.mkv
REM     del %%A_HDR_8K_vert_crop.mkv
     del %%A_HDR_8K_Vert.mkv
     del %%A_HDR_8K_Horz.mkv
     del %%~nxA_HDR_8K_Vert_CUBE.mkv
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