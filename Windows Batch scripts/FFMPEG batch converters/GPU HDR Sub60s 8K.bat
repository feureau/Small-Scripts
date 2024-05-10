@echo off
COLOR 0C

FOR %%A IN (%*) DO (
    ECHO %%A
    ffmpeg -ss 00:00.00 -to 00:59.59 -accurate_seek -y -hwaccel cuda -i %%A -c:v hevc_nvenc -cq:v 16 -b_ref_mode 0 -c:a copy -map 0 -movflags use_metadata_tags -map_metadata 0 -preset fast -tune hq -lookahead_level auto -profile:v main10 -spatial-aq 1 -vf "drawtext=fontfile=E\\:Small-Scripts/Windows Batch scripts/FFMPEG batch converters/FuturaExtraBlack.TTF:text='Subscribe!':fontcolor=black:fontsize=(h/20):box=1:boxcolor=yellow@0.5:boxborderw=15:enable='between(t,1,6):x=(w-text_w)/2:y=((h/3*2)-th)',scale=7680:7680:force_original_aspect_ratio=decrease:flags=lanczos" -pix_fmt yuv420p10le -color_primaries 9 -color_trc 16 -colorspace 9 -color_range 1 %%A.Vert.8K.HDR.mov 

REM    mkvmerge.exe -o %%A.Vert.8K.HDR.mkv --colour-matrix 0:9 --colour-range 0:1 --colour-transfer-characteristics 0:16 --colour-primaries 0:9  --max-content-light 0:1000 --max-frame-light 0:300 --max-luminance 0:1000 --min-luminance 0:0.01 --chromaticity-coordinates 0:0.68,0.32,0.265,0.690,0.15,0.06 --white-colour-coordinates 0:0.3127,0.3290 %%A.Vert.8K.HDR.mov 

REM    del %%A.Vert.8K.HDR.mov 
REM    mkvinfo.exe %%A.Vert.8K.HDR.mkv
)
ECHO Render completed
PAUSE >nul
EXIT