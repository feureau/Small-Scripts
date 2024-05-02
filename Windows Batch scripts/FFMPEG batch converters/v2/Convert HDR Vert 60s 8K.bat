@echo off
COLOR 0C

FOR %%A IN (%*) DO (
    ECHO %%A


    ffmpeg -ss 00:00.00 -to 00:59.59 -accurate_seek -init_hw_device cuda=cuda -filter_hw_device cuda -hwaccel cuda -hwaccel_output_format cuda -i %%A -c:v hevc_nvenc -cq:v 16  -b_ref_mode 0 -c:a copy -map 0 -movflags use_metadata_tags -map_metadata 0 -preset fast -tune hq -lookahead_level auto -profile:v main10 -spatial-aq 1 -filter_complex "[0:v]hwdownload,format=p010le,crop=(3/4*ih):ih:(iw-(3/4*ih))/2:0,zscale=-2:7680:filter=lanczos,min=input:m=input:tin=input:t=input:pin=input:p=input,drawtext=fontfile=FuturaExtraBlack.TTF:text='Subscribe!':fontcolor=black:fontsize=(h/20):box=1:boxcolor=yellow@0.5:boxborderw=15:enable='between(t,55,60):x=(w-text_w)/2:y=((h/3*2)-th)',hwupload_cuda" -map_metadata 0 -movflags use_metadata_tags %%A.Vert.8K.HDR.mov 


    mkvmerge.exe -o %%A.Vert.8K.HDR.mov_cube_ACES.mp4 --colour-matrix 0:9 --colour-range 0:1 --colour-transfer-characteristics 0:16 --colour-primaries 0:9  --max-content-light 0:1000 --max-frame-light 0:300 --max-luminance 0:1000 --min-luminance 0:0.01 --chromaticity-coordinates 0:0.68,0.32,0.265,0.690,0.15,0.06 --white-colour-coordinates 0:0.3127,0.3290 %%A.Vert.8K.HDR.mov 

    mkvinfo.exe %%A.Vert.8K.HDR.mov_cube_ACES.mp4

)


::scale=iw*(7680/iw):ih*(4320/ih)
::libx265
::x=(w-text_w)/2:y=((h/3)-th)
COLOR 0A
::ECHO.
::ECHO Processing complete!  See file specs above.
::ECHO Press Any Key To Exit...
PAUSE >nul
EXIT