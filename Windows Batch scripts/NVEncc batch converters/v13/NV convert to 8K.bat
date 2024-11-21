@echo off
COLOR 0C

:: Prompt user for custom qvbr value, default to 18 if no input is provided
set /p qvbr_value="Enter qvbr value (default is 18): "
if "%qvbr_value%"=="" set "qvbr_value=18"

:: Define individual variables for different parameters
set "FRUC_VAR=--vpp-fruc fps=60"

:: Prompt user for HDR 4K AV1 encoding and accept 1 as yes, 0 as no
set /p encode_hdr_4k="Do you want to Encode to HDR 4K AV1 (y/n/1/0)? [Default: y]: "
if "%encode_hdr_4k%"=="" set "encode_hdr_4k=y"
set "encode_hdr_4k=%encode_hdr_4k:1=Y%"
set "encode_hdr_4k=%encode_hdr_4k:0=N%"
set "encode_hdr_4k=%encode_hdr_4k:y=Y%"
set "encode_hdr_4k=%encode_hdr_4k:n=N%"

:: Prompt user for FRUC (fps=60), default to n, and accept 1 as yes, 0 as no
set /p fruc_enable="Enable FRUC (fps=60)? (y/n/1/0) [Default: n]: "
if "%fruc_enable%"=="" set "fruc_enable=n"
set "fruc_enable=%fruc_enable:1=Y%"
set "fruc_enable=%fruc_enable:0=N%"
set "fruc_enable=%fruc_enable:y=Y%"
set "fruc_enable=%fruc_enable:n=N%"
if /i "%fruc_enable%"=="Y" (set "FRUC_OPTION=%FRUC_VAR%") else (set "FRUC_OPTION=")

:: Prompt user for HDR 8K horizontal AV1 encoding, accept 1 as yes, 0 as no
set /p encode_hdr_8k_horz="Do you want to Encode to HDR 8K Horizontal AV1 (y/n/1/0)? [Default: y]: "
if "%encode_hdr_8k_horz%"=="" set "encode_hdr_8k_horz=y"
set "encode_hdr_8k_horz=%encode_hdr_8k_horz:1=Y%"
set "encode_hdr_8k_horz=%encode_hdr_8k_horz:0=N%"
set "encode_hdr_8k_horz=%encode_hdr_8k_horz:y=Y%"
set "encode_hdr_8k_horz=%encode_hdr_8k_horz:n=N%"

:: Prompt user for HDR 8K vertical HEVC encoding, accept 1 as yes, 0 as no
set /p encode_hdr_8k_vert="Do you want to Encode to HDR 8K Vertical HEVC (y/n/1/0)? [Default: y]: "
if "%encode_hdr_8k_vert%"=="" set "encode_hdr_8k_vert=y"
set "encode_hdr_8k_vert=%encode_hdr_8k_vert:1=Y%"
set "encode_hdr_8k_vert=%encode_hdr_8k_vert:0=N%"
set "encode_hdr_8k_vert=%encode_hdr_8k_vert:y=Y%"
set "encode_hdr_8k_vert=%encode_hdr_8k_vert:n=N%"

:: Prompt user for crop type for 8K vertical HEVC encoding (wide or academic), default to wide
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
echo ===========================
echo.

:: Determine input file based on encoding selections.
set "input_file=%%~fA_temp_HDR_4K.mkv"
if /I "%encode_hdr_4k%"=="N" set "input_file=%%~fA"

:: Process each file provided as an argument to the script.
FOR %%A IN (%*) DO (
    ECHO Processing file: %%~fA

    :: Encode to HDR 4K AV1 if requested.
    IF /I "%encode_hdr_4k%"=="Y" (
        NVEncC64 --avhw --codec av1 --tier 1 --profile high --qvbr %qvbr_value% --preset p1 --output-depth 10 --multipass 2pass-full --nonrefp --aq --aq-temporal --aq-strength 0 --lookahead 32 --lookahead-level auto --transfer auto --audio-copy --chapter-copy --key-on-chapter --sub-copy --metadata copy %FRUC_OPTION% --vpp-resize algo=nvvfx-superres,superres-mode=0 --output-res 2160x2160,preserve_aspect_ratio=increase -i "%%~fA" -o "%%~fA_temp_HDR_4K.mkv"

        mkvmerge.exe -o "%%~fA_HDR_4K_CUBE.mkv" --colour-matrix 0:9 --colour-range 0:1 --colour-transfer-characteristics 0:16 --colour-primaries 0:9 --max-content-light 0:1000 --max-frame-light 0:300 --max-luminance 0:1000 --min-luminance 0:0.01 --chromaticity-coordinates 0:0.68,0.32,0.265,0.690,0.15,0.06 --white-colour-coordinates 0:0.3127,0.3290 --attachment-mime-type application/x-cube --attach-file "C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\LUT\Colorspace LUTS\5-NBCU_PQ2SDR_DL_RESOLVE17-VRT_v1.2.cube" "%%~fA_temp_HDR_4K.mkv"
    ) ELSE (
        ECHO Skipping HDR 4K AV1 encoding.
    )

    :: Encode to HDR 8K horizontal AV1 if requested.
    IF /I "%encode_hdr_8k_horz%"=="Y" (
        NVEncC64 --avhw --codec av1 --tier 1 --profile high --qvbr %qvbr_value% --preset p1 --output-depth 10 --multipass 2pass-full --aq --aq-temporal --aq-strength 0 --lookahead 32 --lookahead-level auto --transfer auto --audio-copy --chapter-copy --key-on-chapter --sub-copy --metadata copy --vpp-resize algo=ngx-vsr,vsr-quality=1 --output-res 4320x4320,preserve_aspect_ratio=increase -i "%input_file%" -o "%%~fA_HDR_8K_Horz.mkv"

        mkvmerge.exe -o "%%~fA_HDR_8K_Horz_CUBE.mkv" --colour-matrix 0:9 --colour-range 0:1 --colour-transfer-characteristics 0:16 --colour-primaries 0:9 --max-content-light 0:1000 --max-frame-light 0:300 --max-luminance 0:1000 --min-luminance 0:0.01 --chromaticity-coordinates 0:0.68,0.32,0.265,0.690,0.15,0.06 --white-colour-coordinates 0:0.3127,0.3290 --attachment-mime-type application/x-cube --attach-file "C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\LUT\Colorspace LUTS\5-NBCU_PQ2SDR_DL_RESOLVE17-VRT_v1.2.cube" "%%~fA_HDR_8K_Horz.mkv"

        DEL /Q "%%~fA_HDR_8K_Horz.mkv"

    ) ELSE (
        ECHO Skipping HDR 8K Horizontal AV1 encoding.
    )

    :: Encode to HDR 8K vertical HEVC using the selected crop value, depending on whether 4K was encoded.
    IF /I "%encode_hdr_8k_vert%"=="Y" (
        NVEncC64 --avhw --codec hevc --tier high --profile main10 --qvbr %qvbr_value% --preset p1 --output-depth 10 --multipass 2pass-full --aq --aq-temporal --aq-strength 0 --lookahead 32 --lookahead-level auto --transfer auto --audio-copy --chapter-copy --key-on-chapter --sub-copy --metadata copy --crop %crop_value%,0,%crop_value%,0 --vpp-resize algo=ngx-vsr,vsr-quality=1 --output-res 4320x4320,preserve_aspect_ratio=increase -i "%input_file%" -o "%%~fA_HDR_8K_Vert.mkv"

        mkvmerge.exe -o "%%~fA_HDR_8K_Vert_CUBE.mkv" --colour-matrix 0:9 --colour-range 0:1 --colour-transfer-characteristics 0:16 --colour-primaries 0:9 --max-content-light 0:1000 --max-frame-light 0:300 --max-luminance 0:1000 --min-luminance 0:0.01 --chromaticity-coordinates 0:0.68,0.32,0.265,0.690,0.15,0.06 --white-colour-coordinates 0:0.3127,0.3290 --attachment-mime-type application/x-cube --attach-file "C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\LUT\Colorspace LUTS\5-NBCU_PQ2SDR_DL_RESOLVE17-VRT_v1.2.cube" "%%~fA_HDR_8K_Vert.mkv"

        DEL /Q "%%~fA_HDR_8K_Vert.mkv"
    ) ELSE (
        ECHO Skipping HDR 8K vertical HEVC encoding.
    )

    :: Split and organize the vertical version into chapters, output to a directory named "8k".
    IF /I "%encode_hdr_8k_vert%"=="Y" (
        mkvmerge.exe -o "8k\%%c.mkv" --split chapters:all "%%~fA_HDR_8K_Vert_CUBE.mkv"
        DEL /Q "%%~fA_HDR_8K_Vert_CUBE.mkv"
    )

    :: Gather information about the processed files.
    IF /I "%encode_hdr_8k_horz%"=="Y" (
        mkvinfo.exe "%%~fA_HDR_8K_Horz_CUBE.mkv"
    )

    IF /I "%encode_hdr_8k_vert%"=="Y" (
        mkvinfo.exe "%%~nxA_HDR_8K_Vert_CUBE.mkv"
    )
)

:: Create '8k' directory if it doesn't exist.
IF NOT EXIST "8k" MD "8k"

:: Move all resulting .mkv files to the '8k' directory.
MOVE /Y "*CUBE.mkv" "8k\"

:: Delete any temporary files with "temp" in the filename, case-insensitively.
DEL /Q "*temp*.mkv"

:: Log all settings used to an encoding log file in the '8k' folder.
echo Encoding Log > "8k\encoding_log.txt"
echo QVBR Value: %qvbr_value% >> "8k\encoding_log.txt"
echo Encode HDR 4K AV1: %encode_hdr_4k% >> "8k\encoding_log.txt"
echo Enable FRUC: %fruc_enable% >> "8k\encoding_log.txt"
echo Encode HDR 8K Horizontal AV1: %encode_hdr_8k_horz% >> "8k\encoding_log.txt"
echo Encode HDR 8K Vertical HEVC: %encode_hdr_8k_vert% >> "8k\encoding_log.txt"
echo Crop Type for 8K Vertical HEVC: %crop_type% >> "8k\encoding_log.txt"
echo Crop Value: %crop_value% >> "8k\encoding_log.txt"

:: Change console color to green.
COLOR 0A

:: Prompt the user to press a key before exiting the script.
ECHO.
ECHO Processing complete! All resulting videos have been moved to the '8k' folder.
ECHO A log of settings used has been saved to "8k\encoding_log.txt".
ECHO Press Any Key To Exit...
PAUSE >nul

EXIT

::--vpp-subburn track=3,scale=3,brightness=1,transparency=0.9,shaping=complex,fontsdir="C:\Windows\Fonts\big_noodle_titling.ttf"