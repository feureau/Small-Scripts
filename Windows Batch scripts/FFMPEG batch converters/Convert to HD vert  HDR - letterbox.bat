@echo off
COLOR 0C

FOR %%A IN (%*) DO (
    ECHO %%A
    ffmpeg -hwaccel cuda -i %%A -c:v hevc_nvenc -cq:v 16  -b_ref_mode 0 -c:a copy -map 0 -preset fast -tune hq -lookahead_level auto -profile:v main10 -pix_fmt p010le -color_primaries bt2020 -colorspace bt2020nc -color_trc smpte2084 -spatial-aq 1 -vf "drawtext=fontfile=C\\:/Users/Feureau/Videos/Wesley_Knapp_HDR_Tools/FuturaExtraBlack.TTF:text='Subscribe!':fontcolor=black:fontsize=(h/20):box=1:boxcolor=yellow@0.5:boxborderw=15:enable='between(t,0,-5):x=(w-text_w)/2:y=((h/3*2)-th)',scale=-2:1920:force_original_aspect_ratio=1:flags=lanczos,pad=4320:5760:(ow-iw)/2:(oh-ih)/2" %%A_shorts.letterbox.HD.HDR.mov 

    mkvmerge.exe -o %%A_shorts.letterbox.HD.HDR.mov _cube_ACES.mp4  --no-chapters --colour-matrix 0:9 --colour-range 0:1 --colour-transfer-characteristics 0:16 --colour-primaries 0:9 --max-content-light 0:1000 --max-frame-light 0:1000 --max-luminance 0:1000 --min-luminance 0:0.01 --chromaticity-coordinates 0:0.68,0.32,0.265,0.690,0.15,0.06 --white-colour-coordinates 0:0.3127,0.3290 --attachment-mime-type application/x-cube --attach-file C:\Users\Feureau\Videos\Wesley_Knapp_HDR_Tools\ACES_Rec2020-ST2084_to_Rec709.cube  %%A_shorts.letterbox.HD.HDR.mov 

    mkvinfo.exe %%A_shorts.letterbox.HD.HDR.mov _cube_ACES.mp4
)


::ffmpeg -i input -vf "scale=w=5760:h=7680:force_original_aspect_ratio=1,pad=5760:7680:(ow-iw)/2:(oh-ih)/2" output
::libx265
::x=(w-text_w)/2:y=((h/3)-th)
COLOR 0A
::ECHO.
::ECHO Processing complete!  See file specs above.
::ECHO Press Any Key To Exit...
PAUSE >nul
EXIT