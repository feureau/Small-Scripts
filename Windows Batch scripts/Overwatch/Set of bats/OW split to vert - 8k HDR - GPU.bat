COLOR 0C

FOR %%A IN (*.mp4) DO (

    ffmpeg -ss 00:05.39 -to 00:18.51 -accurate_seek -y -init_hw_device cuda=cuda -filter_hw_device cuda -hwaccel cuda -hwaccel_output_format cuda -i "%%A" -c:v hevc_nvenc -cq:v 16  -b_ref_mode 0 -c:a copy -map 0 -movflags use_metadata_tags -map_metadata 0 -preset fast -tune hq -lookahead_level auto -profile:v main10 -spatial-aq 1 -filter_complex  "[0:v]hwdownload,format=nv12,crop=(3/4*ih):ih:(iw-(3/4*ih))/2:0,zscale=-2:7680:filter=lanczos:min=input:m=input:tin=input:t=input:pin=input:p=input,format=yuv420p10le,drawtext=fontfile=FuturaExtraBlack.TTF:text='Subscribe!':fontcolor=black:fontsize=(h/20):box=1:boxcolor=yellow@0.5:boxborderw=15:enable='between(t,10,15):x=(w-text_w)/2:y=((h/3*2)-th)',hwupload_cuda" "%%A_shorts-8k.mov"

    mkvmerge.exe -o %%A_shorts-8k_mov_HDR.mkv --colour-matrix 0:9 --colour-range 0:1 --colour-transfer-characteristics 0:16 --colour-primaries 0:9  --max-content-light 0:1000 --max-frame-light 0:300 --max-luminance 0:1000 --min-luminance 0:0.01 --chromaticity-coordinates 0:0.68,0.32,0.265,0.690,0.15,0.06 --white-colour-coordinates 0:0.3127,0.3290 %%A_shorts-8k.mov
     ECHO "%%A"
     del %%A_shorts-8k.mov
     move "%%A_shorts-8k_mov_HDR.mkv" "%cd%\vert split"
     popd
)