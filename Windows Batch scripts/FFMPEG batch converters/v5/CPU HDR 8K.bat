@echo off
COLOR 0C

FOR %%A IN (%*) DO (
    ECHO %%A


    ffmpeg -y -init_hw_device cuda=cuda -filter_hw_device cuda -hwaccel cuda -i %%A -c:v av1_nvenc -cq:v 16  -b_ref_mode 0 -c:a copy -map 0  -preset fast -tune ull -lookahead_level auto -profile:v main10 -spatial-aq 1 -vf "scale=7680:7680:force_original_aspect_ratio=decrease:flags=lanczos" -movflags use_metadata_tags -map_metadata 0 -pix_fmt p010le %%A.Horz.8K.HDR.mov


    mkvmerge.exe -o %%A.Horz.8K.HDR.ACES.mov --no-chapters --colour-matrix 0:9 --colour-range 0:1 --colour-transfer-characteristics 0:16 --colour-primaries 0:9  --max-content-light 0:1000 --max-frame-light 0:300 --max-luminance 0:1000 --min-luminance 0:0.0001 --chromaticity-coordinates 0:0.7080,0.2920,0.1700,0.7970,0.1310,0.0460 --white-colour-coordinates 0:0.3127,0.3290 %%A.Horz.8K.HDR.mov
    del %%A.Horz.8K.HDR.mov
    mkvinfo.exe %%A.Horz.8K.HDR.ACES.mov
)

REM    -color_primaries 9 -color_trc 16 -colorspace 9 -color_range 1
::scale=iw*(7680/iw):ih*(4320/ih)
::libx265
::x=(w-text_w)/2:y=((h/3)-th)
COLOR 0A
::ECHO.
::ECHO Processing complete!  See file specs above.
::ECHO Press Any Key To Exit...
PAUSE >nul
EXIT