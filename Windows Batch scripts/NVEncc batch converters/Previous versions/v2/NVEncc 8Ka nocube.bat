@echo off
COLOR 0C

FOR %%A IN (%*) DO (
    ECHO %%A

NVEncC64 --avhw --codec av1 --profile high --qvbr 0 --preset p4 --output-depth 10 --multipass 2pass-full --lookahead 32 --nonrefp --aq --aq-temporal --aq-strength 0 --transfer auto --audio-copy --chapter-copy --key-on-chapter --sub-copy --metadata copy --vpp-resize algo=nvvfx-superres,superres-mode=1,superres-strength=1.0 --output-res 2160x2160,preserve_aspect_ratio=increase -i %%A -o %%A_temp_HDR_4K.mkv 

ffmpeg -y -init_hw_device cuda=gpu:0 -filter_hw_device gpu -hwaccel cuvid -hwaccel_output_format cuda -i %%A_temp_HDR_4K.mkv -c:v av1_nvenc -cq:v 16 -c:a copy -c:s copy -map 0 -map_metadata 0 -preset p4 -tune hq -lookahead_level auto -rc-lookahead 53 -profile:v main10 -b_ref_mode:v middle -spatial-aq 1 -temporal-aq 1 -g 0 -vf "scale_cuda='iw*2:ih*2:force_original_aspect_ratio=decrease:force_divisible_by=4:interp_algo=lanczos'" %%A_HDR_8K_Horz.mkv

ffmpeg -y -init_hw_device cuda=gpu:0 -filter_hw_device gpu -hwaccel cuvid -hwaccel_output_format cuda -c:v av1_cuvid -crop 0x0x618x618 -resize 2160x2700 -i %%A_temp_HDR_4K.mkv -aspect 2160/2700 -c:v av1_nvenc -cq:v 16 -c:a copy -c:s copy -map 0 -map_metadata 0 -preset p4 -tune hq -lookahead_level auto -rc-lookahead 53 -profile:v main10 -b_ref_mode:v middle -spatial-aq 1 -temporal-aq 1 -force_key_frames chapters+0 -g 0 -vf "scale_cuda='2160:2700:force_original_aspect_ratio=decrease:force_divisible_by=4:interp_algo=lanczos'" %%A_temp_HDR_4K_vert_crop.mkv

ffmpeg -y -init_hw_device cuda=gpu:0 -filter_hw_device gpu -hwaccel cuvid -hwaccel_output_format cuda -i %%A_temp_HDR_4K_vert_crop.mkv -c:v hevc_nvenc -cq:v 16 -c:a copy -c:s copy -map 0 -map_metadata 0 -preset p4 -tune hq -profile:v main10 -spatial-aq 1 -temporal-aq 1 -g 0 -vf "scale_cuda='iw*2:ih*2:force_original_aspect_ratio=decrease:force_divisible_by=4:interp_algo=lanczos'" %%A_HDR_8K_vert_crop.mkv

mkvmerge.exe -o %%A_HDR_8K_vert_crop-%%c.mkv --split chapters:all %%A_HDR_8K_vert_crop.mkv

    mkdir 8k
    move %%A_HDR_8K_Horz.mkv 8k\
    move %%A_HDR_8K_vert_crop-*.mkv 8k\

     del %%A_temp_HDR_4K.mkv
     del %%A_temp_HDR_4K_vert_crop.mkv
     del %%A_HDR_8K_vert_crop.mkv


)

REM -lookahead_level auto -rc-lookahead 53 -b_ref_mode:v middle

REM format=p010le,zscale=-2:7680:filter=lanczos:min=input:m=input:tin=input:t=input:pin=input:p=input,format=yuv420p10le,

::thumbnail,scale='if(gt(iw,ih),7680,trunc(oh*a/2)*2)':'if(gt(iw,ih),trunc(ow/a/2)*2,7680)'
::scale=w=7680:h=7680:force_original_aspect_ratio=1:flags=lanczos
::scale=iw*(7680/iw):ih*(4320/ih)
::libx265
::x=(w-text_w)/2:y=((h/3)-th)
COLOR 0A
::ECHO.
::ECHO Processing complete!  See file specs above.
::ECHO Press Any Key To Exit...
PAUSE >nul
EXIT