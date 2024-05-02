COLOR 0C

::set "your_dir=%cd%"     
::pushd %cd%
::cd %your_dir%

FOR %%A IN (*.mp4) DO (
    ::REM Now your batch file handles %%A instead of %1
    ::REM No need to use SHIFT anymore.
    ECHO "%%A"

    ffmpeg -y -ss 00:05.39 -to 00:18.51 -accurate_seek -hwaccel cuda -i "%%A" -c:v hevc_nvenc -cq:v 16  -b_ref_mode 0 -c:a copy -map 0 -preset fast -tune hq -lookahead_level auto -vf "crop=(3/4*ih):ih:(iw-(3/4*ih))/2:0,drawtext=fontfile=C\\:/Users/Feureau/Videos/Wesley_Knapp_HDR_Tools/FuturaExtraBlack.TTF:text='Subscribe!':fontcolor=black:fontsize=(h/20):box=1:boxcolor=yellow@0.5:boxborderw=15:enable='between(t,10,15):x=(w-text_w)/2:y=((h/3*2)-th)',scale=-2:7680:flags=lanczos" "%%A.shorts-8k.mov"

move "%%A.shorts-8k.mov" "%cd%\vert split"

popd
)


:: horz scale: iw*(7680/iw):ih*(4320/ih)
:: vert scale: iw*(4320/iw):ih*(5760/ih)
::libx265
::x=(w-text_w)/2:y=((h/3)-th)
::COLOR 0A
::ECHO.
::ECHO Processing complete!  See file specs above.
::ECHO Press Any Key To Exit...
::PAUSE >nul
::EXIT