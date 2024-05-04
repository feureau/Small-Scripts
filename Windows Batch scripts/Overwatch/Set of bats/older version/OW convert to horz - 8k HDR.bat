COLOR 0C

::set "your_dir=%cd%"     
::pushd %cd%
::cd %your_dir%

FOR %%A IN (*.mp4) DO (
    ::REM Now your batch file handles %%A instead of %1
    ::REM No need to use SHIFT anymore.
    ECHO "%%A"

    ffmpeg -y -ss 00:05.39 -to 00:18.51 -accurate_seek -hwaccel cuda -i "%%A" -c:v hevc_nvenc -cq:v 16  -b_ref_mode 0 -c:a copy -map 0 -movflags use_metadata_tags -map_metadata 0 -preset fast -tune hq -lookahead_level auto -profile:v main10 -spatial-aq 1 -vf "drawtext=fontfile=C\\:/Users/Feureau/Videos/Wesley_Knapp_HDR_Tools/FuturaExtraBlack.TTF:text='Subscribe!':fontcolor=black:fontsize=(h/20):box=1:boxcolor=yellow@0.5:boxborderw=15:enable='between(t,19,27):x=(w-text_w)/2:y=((h*(4/5))-th)',zscale=min=709:m=2020_ncl:tin=709:t=2020_10:pin=709:p=2020,format=yuv420p10le,scale=-2:4320:flags=lanczos" "%%A_shorts-8k.mov"

    mkvmerge.exe -o %%A_shorts-8k_mov_HDR.mkv  --no-chapters --colour-matrix 0:9 --colour-range 0:1 --colour-transfer-characteristics 0:16 --colour-primaries 0:9 --max-content-light 0:1000 --max-frame-light 0:1000 --max-luminance 0:1000 --min-luminance 0:0.01 --chromaticity-coordinates 0:0.68,0.32,0.265,0.690,0.15,0.06 --white-colour-coordinates 0:0.3127,0.3290 --attachment-mime-type application/x-cube --attach-file C:\Users\Feureau\Videos\Wesley_Knapp_HDR_Tools\ACES_Rec2020-ST2084_to_Rec709.cube%%A_shorts-8k.mov

::    mkvinfo.exe %%A_shorts-8k_mov_HDR.mkv

     ECHO "%%A"

     move "%%A_shorts-8k_mov_HDR.mkv" "%cd%\horz split"
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