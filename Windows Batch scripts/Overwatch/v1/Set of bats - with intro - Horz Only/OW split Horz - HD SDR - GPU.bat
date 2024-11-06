COLOR 0C

::set "your_dir=%cd%"     
::pushd %cd%
::cd %your_dir%

FOR %%A IN (*.mp4) DO (
    ::REM Now your batch file handles %%A instead of %1
    ::REM No need to use SHIFT anymore.
    ECHO "%%A"

ffmpeg -ss 00:00.00 -to 00:18.51 -accurate_seek -y -init_hw_device cuda=cuda -filter_hw_device cuda -hwaccel cuda -hwaccel_output_format cuda -i "%%A" -c:v hevc_nvenc -cq:v 16  -b_ref_mode 0 -c:a copy -map 0 -movflags use_metadata_tags -map_metadata 0 -preset fast -tune hq -lookahead_level auto -profile:v main10 -spatial-aq 1 -filter_complex  "[0:v]hwdownload,format=nv12,zscale=-2:1080:filter=lanczos,drawtext=fontfile=FuturaExtraBlack.TTF:text='Subscribe!':fontcolor=black:fontsize=(h/20):box=1:boxcolor=yellow@0.5:boxborderw=15:enable='between(t,10,15):x=(w-text_w)/2:y=((h/3*2)-th)',hwupload_cuda" "%%A_horz-HD.mov"
move "%%A_horz-HD.mov" "%cd%\horz split"
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