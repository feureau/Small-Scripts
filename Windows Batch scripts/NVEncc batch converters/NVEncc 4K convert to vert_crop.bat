@echo off
COLOR 0C

FOR %%A IN (%*) DO (
    ECHO %%A

NVEncC64 --avhw --codec av1 --profile high --qvbr 0 --preset p4 --output-depth 10 --multipass 2pass-full --lookahead 32 --nonrefp --aq --aq-temporal --aq-strength 0 --transfer auto --audio-copy --chapter-copy --key-on-chapter --metadata copy --vpp-resize algo=nvvfx-superres,superres-mode=1,superres-strength=1.0 --output-res 2160x2160,preserve_aspect_ratio=increase -i %%A -o %%A_temp_HDR_4K.mkv 

mkvmerge.exe -o %%A_HDR_4K_Horz_CUBE.mkv --colour-matrix 0:9 --colour-range 0:1 --colour-transfer-characteristics 0:16 --colour-primaries 0:9 --max-content-light 0:1000 --max-frame-light 0:300 --max-luminance 0:1000 --min-luminance 0:0.01 --chromaticity-coordinates 0:0.68,0.32,0.265,0.690,0.15,0.06 --white-colour-coordinates 0:0.3127,0.3290 --attachment-mime-type application/x-cube --attach-file "C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\LUT\Colorspace LUTS\5-NBCU_PQ2SDR_DL_RESOLVE17-VRT_v1.2.cube" %%A_temp_HDR_4K.mkv


ffmpeg -hwaccel cuda -i %%A_temp_HDR_4K.mkv -c:v av1_nvenc -cq:v 16  -b_ref_mode:v middle -c:a copy -map 0 -preset p4 -tune hq -lookahead_level auto -profile:v main10 -pix_fmt p010le -color_primaries bt2020 -colorspace bt2020nc -color_trc smpte2084 -spatial-aq 1 -temporal-aq 1 -vf "scale=2160:2700:force_original_aspect_ratio=2:flags=lanczos,crop=2160:2700" %%A_temp_HDR_4K_vert_crop.mkv

mkvmerge.exe -o %%A_HDR_4K_Vert_crop_CUBE.mkv --colour-matrix 0:9 --colour-range 0:1 --colour-transfer-characteristics 0:16 --colour-primaries 0:9 --max-content-light 0:1000 --max-frame-light 0:300 --max-luminance 0:1000 --min-luminance 0:0.01 --chromaticity-coordinates 0:0.68,0.32,0.265,0.690,0.15,0.06 --white-colour-coordinates 0:0.3127,0.3290 --attachment-mime-type application/x-cube --attach-file "C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\LUT\Colorspace LUTS\5-NBCU_PQ2SDR_DL_RESOLVE17-VRT_v1.2.cube" %%A_temp_HDR_4K_vert_crop.mkv

    del %%A_temp_HDR_4K.mkv
    del %%A_temp_HDR_4K_vert_crop.mkv

    mkvinfo.exe %%A_HDR_4K_Horz_CUBE.mkv
    mkvinfo.exe %%A_HDR_4K_Vert_crop_CUBE.mkv
    mkdir 4k
    move %%A_HDR_4K_Horz_CUBE.mkv 4k\
    move %%A_HDR_4K_Vert_crop_CUBE.mkv 4k\
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