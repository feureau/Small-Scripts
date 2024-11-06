COLOR 0C

FOR %%A IN (*.mp4) DO (

    ffmpeg -ss 00:00.00 -to 00:18.51 -accurate_seek -y -init_hw_device cuda=cuda -filter_hw_device cuda -hwaccel cuda -hwaccel_output_format cuda -i "%%A" -c:v hevc_nvenc -cq:v 16  -b_ref_mode 0 -c:a copy -map 0 -movflags use_metadata_tags -map_metadata 0 -preset fast -tune hq -lookahead_level auto -profile:v main10 -spatial-aq 1 -filter_complex  "[0:v]hwdownload,format=nv12,crop=(3/4*ih):ih:(iw-(3/4*ih))/2:0,zscale=-2:1920:filter=lanczos,drawtext=fontfile=FuturaExtraBlack.TTF:text='Subscribe!':fontcolor=black:fontsize=(h/20):box=1:boxcolor=yellow@0.5:boxborderw=15:enable='between(t,10,15):x=(w-text_w)/2:y=((h/3*2)-th)',hwupload_cuda" "%%A_shorts-HD.mov"

     move "%%A_shorts-HD.mov" "%cd%\vert split\"
     popd

)

