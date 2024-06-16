@echo off
COLOR 0C

FOR %%A IN (%*) DO (
    ECHO %%A
    ffmpeg -ss 00:00.00 -to 00:59.984 -accurate_seek -y -hwaccel cuda -i %%A -c:v hevc_nvenc -cq:v 16 -b_ref_mode 0 -c:a copy -map 0  -preset p1 -tune ull -lookahead_level auto -profile:v main10 -spatial-aq 1 -pix_fmt p010le -vf "drawtext=fontfile=E\\:Small-Scripts/Windows Batch scripts/FFMPEG batch converters/FuturaExtraBlack.TTF:text='Subscribe!':fontcolor=black:fontsize=(h/20):box=1:boxcolor=yellow@0.5:boxborderw=15:enable='between(t,1,6):x=(w-text_w)/2:y=((h/3*2)-th)'" %%A.Vert.HDR.mov 

    mkvmerge.exe -o %%A.Vert.HDR.ACES.mov --no-chapters --colour-matrix 0:9 --colour-range 0:1 --colour-transfer-characteristics 0:16 --colour-primaries 0:9  --max-content-light 0:1000 --max-frame-light 0:300 --max-luminance 0:1000 --min-luminance 0:0.0001 --chromaticity-coordinates 0:0.7080,0.2920,0.1700,0.7970,0.1310,0.0460 --white-colour-coordinates 0:0.3127,0.3290 %%A.Vert.HDR.mov 

    del %%A.Vert.HDR.mov 
    mkvinfo.exe %%A.Vert.HDR.ACES.mov
)

REM    -movflags use_metadata_tags -map_metadata 0 
REM    -color_primaries 9 -color_trc 16 -colorspace 9 -color_range 1
PAUSE >nul
EXIT