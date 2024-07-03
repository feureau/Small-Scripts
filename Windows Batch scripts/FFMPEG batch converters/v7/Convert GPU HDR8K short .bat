@echo off
COLOR 0C

FOR %%A IN (%*) DO (
    ECHO %%A


    ffmpeg -ss 00:00.00 -to 00:59.900 -accurate_seek -y -init_hw_device cuda=cuda -filter_hw_device cuda -hwaccel cuda -hwaccel_output_format cuda -i %%A -c:v hevc_nvenc -cq:v 16  -b_ref_mode 0 -c:a copy -map 0 -movflags use_metadata_tags -map_metadata 0 -preset fast -tune ull -lookahead_level auto -profile:v main10 -spatial-aq 1 -filter_complex  "[0:v]hwdownload,format=p010le,drawtext=fontfile=E\\:Small-Scripts/Windows Batch scripts/FFMPEG batch converters/FuturaExtraBlack.TTF:text='Subscribe!':fontcolor=black:fontsize=(h/20):box=1:boxcolor=yellow@0.5:boxborderw=15:enable='between(t,1,6):x=(w-text_w)/2:y=((h/3*2)-th)',zscale=-2:7680:filter=lanczos,hwupload_cuda" %%A.shorts.HDR_8K.mov 


    mkvmerge.exe -o %%A.shorts.HDR_8K.ACES.mov --no-chapters --colour-matrix 0:9 --colour-range 0:1 --colour-transfer-characteristics 0:16 --colour-primaries 0:9  --max-content-light 0:1000 --max-frame-light 0:300 --max-luminance 0:1000 --min-luminance 0:0.0001 --chromaticity-coordinates 0:0.7080,0.2920,0.1700,0.7970,0.1310,0.0460 --white-colour-coordinates 0:0.3127,0.3290 %%A.shorts.HDR_8K.mov

    del %%A.shorts.HDR_8K.mov 
    mkvinfo.exe %%A.shorts.HDR_8K.ACES.mov

)

REM format=p010le,zscale=-2:7680:filter=lanczos:min=input:m=input:tin=input:t=input:pin=input:p=input,format=yuv420p10le,
::scale=iw*(7680/iw):ih*(4320/ih)
::libx265
::x=(w-text_w)/2:y=((h/3)-th)
COLOR 0A
::ECHO.
::ECHO Processing complete!  See file specs above.
::ECHO Press Any Key To Exit...
PAUSE >nul
EXIT