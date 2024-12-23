@echo off
COLOR 0C

FOR %%A IN (%*) DO (
    ECHO %%A
    ffmpeg -init_hw_device cuda=cuda -filter_hw_device cuda -hwaccel cuda -hwaccel_output_format cuda -i %%A -c:v hevc_nvenc -cq:v 16  -b_ref_mode 0 -c:a copy -map 0 -preset fast -tune hq -lookahead_level auto -profile:v main10 -pix_fmt yuv420p10le -color_primaries bt2020 -colorspace bt2020nc -color_trc smpte2084 -spatial-aq 1 -filter_complex "[0:v]hwdownload,format=p010le,crop=(3/4*ih):ih:(iw-(3/4*ih))/2:0,drawtext=fontfile=FuturaExtraBlack.TTF:text='Subscribe!':fontcolor=black:fontsize=(h/20):box=1:boxcolor=yellow@0.5:boxborderw=15:enable='between(t,55,999):x=(w-text_w)/2:y=((h*(4/5))-th)',hwupload_cuda" -map_metadata 0 -movflags use_metadata_tags %%A_shorts.sub.HD.HDR.mov 

    mkvmerge.exe -o %%A_shorts.sub.HD.HDR.mov _cube_ACES.mp4  --no-chapters --colour-matrix 0:9 --colour-range 0:1 --colour-transfer-characteristics 0:16 --colour-primaries 0:9 --max-content-light 0:1000 --max-frame-light 0:1000 --max-luminance 0:1000 --min-luminance 0:0.01 --chromaticity-coordinates 0:0.68,0.32,0.265,0.690,0.15,0.06 --white-colour-coordinates 0:0.3127,0.3290 --attachment-mime-type application/x-cube --attach-file C:\Users\Feureau\Videos\Wesley_Knapp_HDR_Tools\ACES_Rec2020-ST2084_to_Rec709.cube %%A_shorts.sub.HD.HDR.mov 

    mkvinfo.exe %%A_shorts.sub.HD.HDR.mov _cube_ACES.mp4
)

::iw*(4320/iw):ih*(5760/ih)
::libx265
::x=(w-text_w)/2:y=((h/3)-th)
COLOR 0A
::ECHO.
::ECHO Processing complete!  See file specs above.
::ECHO Press Any Key To Exit...
PAUSE >nul
EXIT