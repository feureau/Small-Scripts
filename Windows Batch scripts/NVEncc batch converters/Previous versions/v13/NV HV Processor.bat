@echo off
setlocal EnableDelayedExpansion
COLOR 0C

:: Prompt user for upscale resolution (4K or 8K), allowing 1 for 8K and 2 for 4K
set /p upscale_res="Select upscale resolution (1 for 8K, 2 for 4K) [default: 8K]: "
if "%upscale_res%"=="" set "upscale_res=8K"
set "upscale_res=!upscale_res:1=8K!"
set "upscale_res=!upscale_res:2=4K!"

:: Set resolution variables based on user choice
if /I "%upscale_res%"=="4K" (
    set "output_res=2160x2160"
    set "output_folder=4k"
) else (
    set "output_res=4320x4320"
    set "output_folder=8k"
)

:: Prompt user for custom qvbr value, default to 18 if no input is provided
set /p qvbr_value="Enter qvbr value (default is 18): "
if "%qvbr_value%"=="" set "qvbr_value=18"

:: Define individual variables for different parameters
set "FRUC_VAR=--vpp-fruc fps=60"

:: Prompt user for FRUC (fps=60), default to n, and accept 1 as yes, 0 as no
set /p fruc_enable="Enable FRUC (fps=60)? (y/n/1/0) [Default: n]: "
if "%fruc_enable%"=="" set "fruc_enable=n"
set "fruc_enable=!fruc_enable:1=Y!"
set "fruc_enable=!fruc_enable:0=N!"
set "fruc_enable=!fruc_enable:y=Y!"
set "fruc_enable=!fruc_enable:n=N!"
if /i "!fruc_enable!"=="Y" (set "FRUC_OPTION=!FRUC_VAR!") else (set "FRUC_OPTION=")

:: Prompt user for HDR 4K AV1 encoding if 4K resolution is selected
if /I "%upscale_res%"=="4K" (
    set "encode_hdr_8k_horz=N"
    set "encode_hdr_8k_vert=N"
    set /p encode_hdr_4k="Do you want to Encode to HDR 4K AV1? (y/n) [Default: y]: "
    if "%encode_hdr_4k%"=="" set "encode_hdr_4k=y"
    set "encode_hdr_4k=!encode_hdr_4k:1=Y!"
    set "encode_hdr_4k=!encode_hdr_4k:0=N!"
    set "encode_hdr_4k=!encode_hdr_4k:y=Y!"
    set "encode_hdr_4k=!encode_hdr_4k:n=N!"
) else (
    :: Prompt user for HDR 4K AV1 encoding, automatically set if any 8K encoding is requested
    set /p encode_hdr_4k="Do you want to Encode to HDR 4K AV1 as a prerequisite for 8K encoding? (y/n) [Default: y]: "
    if "%encode_hdr_4k%"=="" set "encode_hdr_4k=y"
    set "encode_hdr_4k=!encode_hdr_4k:1=Y!"
    set "encode_hdr_4k=!encode_hdr_4k:0=N!"
    set "encode_hdr_4k=!encode_hdr_4k:y=Y!"
    set "encode_hdr_4k=!encode_hdr_4k:n=N!"

    :: Prompt user for HDR 8K horizontal AV1 encoding if 8K resolution is selected
    set /p encode_hdr_8k_horz="Do you want to Encode to HDR 8K Horizontal AV1 (y/n) [Default: y]: "
    if "%encode_hdr_8k_horz%"=="" set "encode_hdr_8k_horz=y"
    set "encode_hdr_8k_horz=!encode_hdr_8k_horz:1=Y!"
    set "encode_hdr_8k_horz=!encode_hdr_8k_horz:0=N!"
    set "encode_hdr_8k_horz=!encode_hdr_8k_horz:y=Y!"
    set "encode_hdr_8k_horz=!encode_hdr_8k_horz:n=N!"

    :: Prompt user for HDR 8K vertical HEVC encoding
    set /p encode_hdr_8k_vert="Do you want to Encode to HDR 8K Vertical HEVC (y/n) [Default: y]: "
    if "%encode_hdr_8k_vert%"=="" set "encode_hdr_8k_vert=y"
    set "encode_hdr_8k_vert=!encode_hdr_8k_vert:1=Y!"
    set "encode_hdr_8k_vert=!encode_hdr_8k_vert:0=N!"
    set "encode_hdr_8k_vert=!encode_hdr_8k_vert:y=Y!"
    set "encode_hdr_8k_vert=!encode_hdr_8k_vert:n=N!"

    :: Automatically enable HDR 4K AV1 encoding if any 8K encoding is requested
    if /I "!encode_hdr_8k_horz!"=="Y" set "encode_hdr_4k=Y"
    if /I "!encode_hdr_8k_vert!"=="Y" set "encode_hdr_4k=Y"
)

:: Prompt user for crop type for 8K vertical HEVC encoding (wide or academic), default to wide
set /p crop_type="Select crop type for 8K vertical HEVC (w for wide, a for academic) [Default: w]: "
if "%crop_type%"=="" set "crop_type=w"
set "crop_type=!crop_type:w=W!"
set "crop_type=!crop_type:a=A!"

:: Set crop value based on user input (1056 for wide, 618 for academic).
if /I "!crop_type!"=="W" (
    set "crop_value=1056"
) else (
    set "crop_value=618"
)

:: Display all custom settings for confirmation
echo.
echo ===========================
echo Review Custom Settings
echo ===========================
echo QVBR Value: %qvbr_value%
echo Encode HDR 4K AV1: %encode_hdr_4k%
echo Enable FRUC: %fruc_enable%
echo Encode HDR 8K Horizontal AV1: %encode_hdr_8k_horz%
echo Encode HDR 8K Vertical HEVC: %encode_hdr_8k_vert%
echo Crop Type for 8K Vertical HEVC: %crop_type%
echo Crop Value: %crop_value%
echo Upscale Resolution: %upscale_res%
echo ===========================
echo.

:: Process each file provided as an argument to the script.
FOR %%A IN (%*) DO (
    ECHO Processing file: %%~fA

    :: Encode to HDR 4K AV1 if requested or as prerequisite for 8K encoding.
    IF /I "!encode_hdr_4k!"=="Y" (
        NVEncC64 --avhw --codec av1 --tier 1 --profile high --qvbr %qvbr_value% --preset p1 --output-depth 10 --multipass 2pass-full --nonrefp --aq --aq-temporal --aq-strength 0 --lookahead 32 --lookahead-level auto --transfer auto --audio-copy --chapter-copy --key-on-chapter --sub-copy --metadata copy !FRUC_OPTION! -i "%%~fA" -o "%%~fA_temp_HDR_4K.mkv"

        mkvmerge.exe -o "%%~fA_HDR_4K_CUBE.mkv" --colour-matrix 0:9 --colour-range 0:1 --colour-transfer-characteristics 0:16 --colour-primaries 0:9 --max-content-light 0:1000 --max-frame-light 0:300 --max-luminance 0:1000 --min-luminance 0:0.01 --attachment-mime-type application/x-cube --attach-file "%ProgramData%\Blackmagic Design\DaVinci Resolve\Support\LUT\Colorspace LUTS\5-NBCU_PQ2SDR_DL_RESOLVE17-VRT_v1.2.cube" "%%~fA_temp_HDR_4K.mkv"
    ) ELSE (
        ECHO Skipping HDR 4K AV1 encoding.
    )

    :: Encode to HDR 8K Horizontal AV1 if requested.
    IF /I "!encode_hdr_8k_horz!"=="Y" (
        NVEncC64 --avhw --codec av1 --tier 1 --profile high --qvbr %qvbr_value% --preset p1 --output-depth 10 --multipass 2pass-full --nonrefp --aq --aq-temporal --aq-strength 0 --lookahead 32 --lookahead-level auto --transfer auto --audio-copy --chapter-copy --key-on-chapter --sub-copy --metadata copy !FRUC_OPTION! -i "%%~fA_temp_HDR_4K.mkv" -o "%%~fA_HDR_8K_Horz.mkv"

        mkvmerge.exe -o "%%~fA_HDR_8K_Horz_CUBE.mkv" --colour-matrix 0:9 --colour-range 0:1 --colour-transfer-characteristics 0:16 --colour-primaries 0:9 --max-content-light 0:1000 --max-frame-light 0:300 --max-luminance 0:1000 --min-luminance 0:0.01 --attachment-mime-type application/x-cube --attach-file "%ProgramData%\Blackmagic Design\DaVinci Resolve\Support\LUT\Colorspace LUTS\5-NBCU_PQ2SDR_DL_RESOLVE17-VRT_v1.2.cube" "%%~fA_HDR_8K_Horz.mkv"
    ) ELSE (
        ECHO Skipping HDR 8K Horizontal AV1 encoding.
    )

    :: Encode to HDR 8K vertical HEVC if requested.
    IF /I "!encode_hdr_8k_vert!"=="Y" (
        NVEncC64 --avhw --codec hevc --preset p1 --output-depth 10 --multipass 2pass-full --qvbr %qvbr_value% --lookahead 32 --lookahead-level auto --nonrefp --aq --aq-temporal --aq-strength 0 --vpp-pad right=%crop_value% !FRUC_OPTION! -i "%%~fA_temp_HDR_4K.mkv" -o "%%~fA_HDR_8K_Vert.mkv"

        mkvmerge.exe -o "%%~fA_HDR_8K_Vert_CUBE.mkv" --colour-matrix 0:9 --colour-range 0:1 --colour-transfer-characteristics 0:16 --colour-primaries 0:9 --max-content-light 0:1000 --max-frame-light 0:300 --max-luminance 0:1000 --min-luminance 0:0.01 --attachment-mime-type application/x-cube --attach-file "%ProgramData%\Blackmagic Design\DaVinci Resolve\Support\LUT\Colorspace LUTS\5-NBCU_PQ2SDR_DL_RESOLVE17-VRT_v1.2.cube" "%%~fA_HDR_8K_Vert.mkv"

        :: Ensure split folder exists, then split and extract SRT
        mkdir split
        mkvmerge.exe -o "split\%%~nA_%%c.mkv" --split chapters:all "%%~fA_HDR_8K_Vert_CUBE.mkv"

        :: Extract the SRT subtitles for each split video
        for %%c in (split\*.mkv) do (
            ffmpeg -i "%%c" -map 0:s:? "%%c.srt"
        )
    ) ELSE (
        ECHO Skipping HDR 8K Vertical HEVC encoding.
    )
)

:: Completion message and log output
ECHO Processing complete!
PAUSE >nul
EXIT
