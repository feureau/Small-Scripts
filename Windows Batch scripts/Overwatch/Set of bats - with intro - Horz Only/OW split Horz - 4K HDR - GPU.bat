COLOR 0C

::set "your_dir=%cd%"     
::pushd %cd%
::cd %your_dir%

FOR %%A IN (*.mp4) DO (
    ::REM Now your batch file handles %%A instead of %1
    ::REM No need to use SHIFT anymore.
    ECHO "%%A"

ffmpeg -ss 00:00.00 -to 00:18.51 -accurate_seek -y -init_hw_device cuda=cuda -filter_hw_device cuda -hwaccel cuda -hwaccel_output_format cuda -i "%%A" -c:v hevc_nvenc -cq:v 16  -b_ref_mode 0 -c:a copy -map 0:v:0 -map 0:a:0 -movflags use_metadata_tags -map_metadata 0 -preset fast -tune hq -lookahead_level auto -profile:v main10 -spatial-aq 1 -filter_complex  "[0:v]hwdownload,format=nv12,zscale=-2:2160:filter=lanczos:min=709:m=2020_ncl:tin=709:t=2020_10:pin=709:p=2020,format=yuv420p10le,drawtext=fontfile=FuturaExtraBlack.TTF:text='Subscribe!':fontcolor=black:fontsize=(h/20):box=1:boxcolor=yellow@0.5:boxborderw=15:enable='between(t,0,-5):x=(w-text_w)/2:y=((h/3*2)-th)',hwupload_cuda" -color_primaries 9 -color_trc 14 -colorspace 9 -color_range 1 "%%A_horz-4K.mov"

    mkvmerge.exe -o "%%A.Horz.4K.HDR.mkv" --colour-matrix 0:9 --colour-range 0:1 --colour-transfer-characteristics 0:16 --colour-primaries 0:9  --max-content-light 0:1000 --max-frame-light 0:300 --max-luminance 0:1000 --min-luminance 0:0.01 --chromaticity-coordinates 0:0.68,0.32,0.265,0.690,0.15,0.06 --white-colour-coordinates 0:0.3127,0.3290 --attachment-mime-type application/x-cube --attach-file "E:\Small-Scripts\DaVinci Resolve\Wesley_Knapp_HDR_Tools\ACES_Rec2020-ST2084_to_Rec709.cube" "%%A_horz-4K.mov"

    del "%%A_horz-4K.mov"

    mkvinfo.exe "%%A.Horz.4K.HDR.mkv"

move "%%A.Horz.4K.HDR.mkv" "%cd%\horz split"
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