@echo off
COLOR 0C

FOR %%A IN (%*) DO (
    ECHO %%A

    ffmpeg -hwaccel cuda -i %%A -c:v hevc_nvenc -cq:v 16 -b_ref_mode 0 -c:a copy -map 0 -preset fast -tune hq -lookahead_level auto -pix_fmt p010le -profile:v main10 -spatial-aq 1 -vf "drawtext=fontfile=C\\:/Users/Feureau/Videos/Wesley_Knapp_HDR_Tools/FuturaExtraBlack.TTF:text='Subscribe!':fontcolor=black:fontsize=(h/20):box=1:boxcolor=yellow@0.5:boxborderw=15:enable='between(t,0,-5):x=(w-text_w)/2:y=((h/3*2)-th)',scale=-2:4320:flags=lanczos" %%A.8K.SDR.mov
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