@echo off
COLOR 0C

:: Prompt user for HDR 4K AV1 encoding and convert to lowercase.
set /p encode_hdr_4k="Do you want to Encode to HDR 4K AV1 (y/n)? [Default: y]: "
if "%encode_hdr_4k%"=="" set "encode_hdr_4k=y"
set "encode_hdr_4k=%encode_hdr_4k:y=Y%"
set "encode_hdr_4k=%encode_hdr_4k:n=N%"

:: Prompt user for HDR 8K horizontal AV1 encoding and convert to lowercase.
set /p encode_hdr_8k_horz="Do you want to Encode to HDR 8K Horizontal AV1 (y/n)? [Default: y]: "
if "%encode_hdr_8k_horz%"=="" set "encode_hdr_8k_horz=y"
set "encode_hdr_8k_horz=%encode_hdr_8k_horz:y=Y%"
set "encode_hdr_8k_horz=%encode_hdr_8k_horz:n=N%"

:: Prompt user for HDR 8K vertical HEVC encoding and convert to lowercase.
set /p encode_hdr_8k_vert="Do you want to Encode to HDR 8K Vertical HEVC (y/n)? [Default: y]: "
if "%encode_hdr_8k_vert%"=="" set "encode_hdr_8k_vert=y"
set "encode_hdr_8k_vert=%encode_hdr_8k_vert:y=Y%"
set "encode_hdr_8k_vert=%encode_hdr_8k_vert:n=N%"

:: Prompt user for crop type for 8K vertical HEVC encoding (wide or academic).
set /p crop_type="Select crop type for 8K vertical HEVC (w for wide, a for academic) [Default: w]: "
if "%crop_type%"=="" set "crop_type=w"
set "crop_type=%crop_type:w=W%"
set "crop_type=%crop_type:a=A%"

:: Set crop value based on user input (1056 for wide, 618 for academic).
if /I "%crop_type%"=="W" (
    set "crop_value=1056"
) else (
    set "crop_value=618"
)

:: Determine input file based on encoding selections.
set "input_file=%%A_temp_HDR_4K.mkv"
if /I "%encode_hdr_4k%"=="N" set "input_file=%%A"

:: Process each file provided as an argument to the script.
FOR %%A IN (%*) DO (
    ECHO Processing file: %%A

    :: Encode to HDR 4K AV1 if requested.
    IF /I "%encode_hdr_4k%"=="y" (
        NVEncC64 --avhw --codec av1 --tier 1 --profile high --qvbr 1 --preset p1 --output-depth 10 --multipass 2pass-full --nonrefp --aq --aq-temporal --aq-strength 0 --lookahead 32 --lookahead-level auto --transfer auto --audio-copy --chapter-copy --key-on-chapter --sub-copy --metadata copy --vpp-resize algo=nvvfx-superres,superres-mode=0 --output-res 2160x2160,preserve_aspect_ratio=increase -i "%%A" -o "%%A_temp_HDR_4K.mkv"
    ) ELSE (
        ECHO Skipping HDR 4K AV1 encoding.
    )

    :: Encode to HDR 8K horizontal AV1 if requested.
    IF /I "%encode_hdr_8k_horz%"=="y" (
        NVEncC64 --avhw --codec av1 --tier 1 --profile high --qvbr 1 --preset p1 --output-depth 10 --multipass 2pass-full --aq --aq-temporal --aq-strength 0 --lookahead 32 --lookahead-level auto --transfer auto --audio-copy --chapter-copy --key-on-chapter --sub-copy --metadata copy --vpp-resize algo=nvvfx-superres,superres-mode=0 --output-res 4320x4320,preserve_aspect_ratio=increase -i "%input_file%" -o "%%A_HDR_8K_Horz.mkv"
    ) ELSE (
        ECHO Skipping HDR 8K Horizontal AV1 encoding.
    )

    :: Apply color correction to the horizontal version using a specific LUT file if requested.
    IF /I "%encode_hdr_8k_horz%"=="y" (
        mkvmerge.exe -o "%%A_HDR_8K_Horz_CUBE.mkv" --colour-matrix 0:9 --colour-range 0:1 --colour-transfer-characteristics 0:16 --colour-primaries 0:9 --max-content-light 0:1000 --max-frame-light 0:300 --max-luminance 0:1000 --min-luminance 0:0.01 --chromaticity-coordinates 0:0.68,0.32,0.265,0.690,0.15,0.06 --white-colour-coordinates 0:0.3127,0.3290 --attachment-mime-type application/x-cube --attach-file "C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\LUT\Colorspace LUTS\5-NBCU_PQ2SDR_DL_RESOLVE17-VRT_v1.2.cube" "%%A_HDR_8K_Horz.mkv"
        DEL /Q "%%A_HDR_8K_Horz.mkv"
    )

    :: Encode to HDR 8K vertical HEVC using the selected crop value, depending on whether 4K was encoded.
    IF /I "%encode_hdr_8k_vert%"=="y" (
        IF /I "%encode_hdr_4k%"=="y" (
            NVEncC64 --avhw --codec hevc --tier high --profile main10 --qvbr 1 --preset p1 --output-depth 10 --multipass 2pass-full --aq --aq-temporal --aq-strength 0 --lookahead 32 --lookahead-level auto --transfer auto --audio-copy --chapter-copy --key-on-chapter --sub-copy --metadata copy --crop %crop_value%,0,%crop_value%,0 --vpp-resize algo=ngx-vsr,vsr-quality=1 --output-res 4320x4320,preserve_aspect_ratio=increase -i "%input_file%" -o "%%A_HDR_8K_Vert.mkv"
        ) ELSE (
            NVEncC64 --avhw --codec hevc --tier high --profile main10 --qvbr 1 --preset p1 --output-depth 10 --multipass 2pass-full --aq --aq-temporal --aq-strength 0 --lookahead 32 --lookahead-level auto --transfer auto --audio-copy --chapter-copy --key-on-chapter --sub-copy --metadata copy --crop %crop_value%,0,%crop_value%,0 --vpp-resize algo=ngx-vsr,vsr-quality=1 --output-res 4320x4320,preserve_aspect_ratio=increase -i "%%A" -o "%%A_HDR_8K_Vert.mkv"
        )
    )

    :: Apply color correction to the vertical version using a specific LUT file.
    IF /I "%encode_hdr_8k_vert%"=="y" (
        mkvmerge.exe -o "%%A_HDR_8K_Vert_CUBE.mkv" --colour-matrix 0:9 --colour-range 0:1 --colour-transfer-characteristics 0:16 --colour-primaries 0:9 --max-content-light 0:1000 --max-frame-light 0:300 --max-luminance 0:1000 --min-luminance 0:0.01 --chromaticity-coordinates 0:0.68,0.32,0.265,0.690,0.15,0.06 --white-colour-coordinates 0:0.3127,0.3290 --attachment-mime-type application/x-cube --attach-file "C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\LUT\Colorspace LUTS\5-NBCU_PQ2SDR_DL_RESOLVE17-VRT_v1.2.cube" "%%A_HDR_8K_Vert.mkv"
        DEL /Q "%%A_HDR_8K_Vert.mkv"
    )

    :: Split and organize the vertical version into chapters, output to a directory named "8k".
    IF /I "%encode_hdr_8k_vert%"=="y" (
        mkvmerge.exe -o "8k\%%~nxA_HDR_8K_Vert_CUBE.mkv" --split chapters:all "%%A_HDR_8K_Vert_CUBE.mkv"
        DEL /Q "%%A_HDR_8K_Vert_CUBE.mkv"
    )

    :: Gather information about the processed files.
    IF /I "%encode_hdr_8k_horz%"=="y" (
        mkvinfo.exe "%%A_HDR_8K_Horz_CUBE.mkv"
    )

    IF /I "%encode_hdr_8k_vert%"=="y" (
        mkvinfo.exe "8k\%%~nxA_HDR_8K_Vert_CUBE.mkv"
    )
)

:: Create '8k' directory if it doesn't exist.
IF NOT EXIST "8k" MD "8k"

:: Delete any temporary files with "temp" in the filename, case-insensitively.
DEL /Q "*temp*.mkv"

:: Move all resulting .mkv files to the '8k' directory.
MOVE /Y "*CUBE.mkv" "8k\

:: Change console color to green.
COLOR 0A

:: Prompt the user to press a key before exiting the script.
ECHO.
ECHO Processing complete! All resulting videos have been moved to the '8k' folder.
ECHO Press Any Key To Exit...
PAUSE >nul

EXIT