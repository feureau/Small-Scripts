@echo off
COLOR 0C
ECHO Resolution size must be one step below. HD to 4K, 4k to 8K. If you want to convert HD to 8k, first convert to 4k then 4k to 8k
:: Prompt for resolution option (4K or 8K), default to 8K
set /p resolution="Enter resolution (4k, 8k, 1 for 4k, 2 for 8k) [Default: 8k]: "
if "%resolution%"=="" set "resolution=8k"
set "resolution=%resolution:1=4k%"
set "resolution=%resolution:2=8k%"
set "resolution=%resolution:4k=4k%"
set "resolution=%resolution:8k=8k%"
if /i not "%resolution%"=="4k" if /i not "%resolution%"=="8k" set "resolution=8k"

:: Prompt for horizontal conversion (yes or no), default to yes
set /p horizontal="Do you want to convert to Horizontal? (y/n/1/0) [Default: y]: "
if "%horizontal%"=="" set "horizontal=y"
set "horizontal=%horizontal:1=Y%"
set "horizontal=%horizontal:0=N%"
set "horizontal=%horizontal:y=Y%"
set "horizontal=%horizontal:n=N%"
if /i not "%horizontal%"=="Y" if /i not "%horizontal%"=="N" set "horizontal=Y"

:: Prompt for vertical conversion (yes or no), default to yes
set /p vertical="Do you want to convert to Vertical? (y/n/1/0) [Default: y]: "
if "%vertical%"=="" set "vertical=y"
set "vertical=%vertical:1=Y%"
set "vertical=%vertical:0=N%"
set "vertical=%vertical:y=Y%"
set "vertical=%vertical:n=N%"
if /i not "%vertical%"=="Y" if /i not "%vertical%"=="N" set "vertical=Y"

:: Prompt for custom qvbr value, default to 18 if no input is provided
set /p qvbr_value="Enter qvbr value (default is 18): "
if "%qvbr_value%"=="" set "qvbr_value=18"

:: Prompt for FRUC option (fps=60), default to no
set /p fruc_enable="Enable FRUC (fps=60)? (y/n/1/0) [Default: n]: "
if "%fruc_enable%"=="" set "fruc_enable=n"
set "fruc_enable=%fruc_enable:1=Y%"
set "fruc_enable=%fruc_enable:0=N%"
set "fruc_enable=%fruc_enable:y=Y%"
set "fruc_enable=%fruc_enable:n=N%"
if /i "%fruc_enable%"=="Y" (set "FRUC_OPTION=--vpp-fruc fps=60") else (set "FRUC_OPTION=")

:: Create output folder based on resolution
if not exist "%resolution%" mkdir "%resolution%"

:: Handle resolution-specific settings
if /i "%resolution%"=="4k" (
    set "output_res=2160x2160"
) else if /i "%resolution%"=="8k" (
    set "output_res=4320x4320"
) else (
    ECHO Invalid resolution specified! Defaulting to 8K.
    set "output_res=4320x4320"
    set "resolution=8k"
)

:: Define crop values based on resolution
if /i "%resolution%"=="4k" (
    set "crop_value=528,0,528,0"  :: For 4K, crop is set to 528,0,528,0
) else if /i "%resolution%"=="8k" (
    set "crop_value=1056,0,1056,0" :: For 8K, crop is set to 1056,0,1056,0
) else (
    ECHO Invalid resolution specified! Defaulting to 8K.
    set "crop_value=1056,0,1056,0" :: Default crop value for 8K
    set "resolution=8k"
)

:: Define resize algorithm based on resolution
if /i "%resolution%"=="4k" (
    set "resize_algorithm=algo=nvvfx-superres,superres-mode=0"
) else if /i "%resolution%"=="8k" (
    set "resize_algorithm=algo=ngx-vsr,vsr-quality=1"
) else (
    set "resize_algorithm=algo=nvvfx-superres,superres-mode=0"  :: Default to 4K resize algorithm
)

:: Display settings for confirmation
echo.
echo ===========================
echo Review Custom Settings
echo ===========================
echo Resolution: %resolution%
echo Crop Value: %crop_value%
echo ===========================
echo.

:: Process files
FOR %%A IN (%*) DO (
    ECHO Processing file: %%~fA

    :: Horizontal conversion
    IF /I "%horizontal%"=="Y" (
        NVEncC64 --avhw --codec av1 --tier 1 --profile high --qvbr %qvbr_value% --preset p1 --output-depth 10 --multipass 2pass-full --aq --aq-temporal --aq-strength 0 --lookahead 32 --lookahead-level auto --transfer auto --audio-copy --chapter-copy --key-on-chapter --sub-copy --metadata copy %FRUC_OPTION% --vpp-resize %resize_algorithm% --output-res %output_res%,preserve_aspect_ratio=increase -i "%%~fA" -o "%resolution%\%%~nA_Horizontal_%resolution%.mkv"
        ECHO Horizontal conversion completed for %%~fA.
    ) ELSE (
        ECHO Skipping horizontal conversion for %%~fA.
    )

    :: Vertical conversion
    IF /I "%vertical%"=="Y" (


        NVEncC64 --avhw --codec hevc --tier high --profile main10 --qvbr %qvbr_value% --preset p1 --output-depth 10 --multipass 2pass-full --aq --aq-temporal --aq-strength 0 --lookahead 32 --lookahead-level auto --transfer auto --audio-copy --chapter-copy --key-on-chapter --sub-copy --metadata copy --crop %crop_value% --vpp-resize algo=ngx-vsr,vsr-quality=1 --output-res %output_res%,preserve_aspect_ratio=increase -i "%%~fA" -o "%resolution%\%%~nA_Vertical_%resolution%.mkv"

        mkvmerge.exe -o "%resolution%\%%c.mkv" --split chapters:all "%resolution%\%%~nA_Vertical_%resolution%.mkv"

        ECHO Vertical conversion completed for %%~fA.
    ) ELSE (
        ECHO Skipping vertical conversion for %%~fA.
    )
)


:: Save encoding log to the resolution folder
echo Encoding Log > "%resolution%\encoding_log.txt"
echo Resolution: %resolution% >> "%resolution%\encoding_log.txt"
echo Convert to Horizontal: %horizontal% >> "%resolution%\encoding_log.txt"
echo Convert to Vertical: %vertical% >> "%resolution%\encoding_log.txt"
echo QVBR Value: %qvbr_value% >> "%resolution%\encoding_log.txt"
echo Enable FRUC: %fruc_enable% >> "%resolution%\encoding_log.txt"

:: Completion message
COLOR 0A
ECHO.
ECHO Processing complete! All resulting videos have been moved to the '%resolution%' folder.
ECHO A log of settings used has been saved to "%resolution%\encoding_log.txt".
ECHO Press Any Key To Exit...
PAUSE >nul
EXIT
