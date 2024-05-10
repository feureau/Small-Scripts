@echo off
COLOR 0C

FOR %%A IN (%*) DO (
    ECHO %%A


    ffmpeg -y -init_hw_device cuda=cuda -filter_hw_device cuda -hwaccel cuda -hwaccel_output_format cuda -i %%A -c:v hevc_nvenc -cq:v 16  -b_ref_mode 0 -c:a copy -map 0 -preset fast -tune hq -lookahead_level auto -profile:v main10 -spatial-aq 1 -pix_fmt yuv420p10le -color_primaries 9 -color_trc 16 -colorspace 9 -color_range 1 -vf "drawtext=fontfile=E\\:Small-Scripts/Windows Batch scripts/FFMPEG batch converters/FuturaExtraBlack.TTF:text='Subscribe!':fontcolor=black:fontsize=(h/20):box=1:boxcolor=yellow@0.5:boxborderw=15:enable='between(t,0,-5):x=(w-text_w)/2:y=((h/3*2)-th)',scale=-2:4320:flags=lanczos" %%A.8K.HDR.mov 


    mkvmerge.exe -o %%A.8K.HDR.mkv --colour-matrix 0:9 --colour-range 0:1 --colour-transfer-characteristics 0:16 --colour-primaries 0:9  --max-content-light 0:1000 --max-frame-light 0:300 --max-luminance 0:1000 --min-luminance 0:0.01 --chromaticity-coordinates 0:0.68,0.32,0.265,0.690,0.15,0.06 --white-colour-coordinates 0:0.3127,0.3290 --attachment-mime-type application/x-cube --attach-file "E:\Small-Scripts\DaVinci Resolve\Wesley_Knapp_HDR_Tools\ACES_Rec2020-ST2084_to_Rec709.cube" %%A.8K.HDR.mov 


    del %%A.8K.HDR.mov 
    mkvinfo.exe %%A.8K.HDR.mkv

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