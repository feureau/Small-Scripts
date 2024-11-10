@echo off
COLOR 0C

:: Check if a file is dragged onto the script
IF "%~1"=="" (
    ECHO No video file specified. Please drag and drop a video file onto the script.
    PAUSE
    EXIT /B
)

:: Ask user to select input resolution
ECHO Select input resolution:
ECHO [1] 1080p
ECHO [2] 2160p (default)
SET /P res_choice=Enter choice (1 or 2) [2]: 
IF "%res_choice%"=="" SET res_choice=2

:: Set resolution height and width based on user’s choice
IF "%res_choice%"=="1" (
    SET input_height=1080
    SET input_width=1920
) ELSE (
    SET input_height=2160
    SET input_width=3840
)

:: Define encoding variables for different processing options
set "FRUC_VAR=--vpp-fruc fps=60"
set "RESIZE_VAR=--vpp-resize algo=nvvfx-superres,superres-mode=0 --output-res 2160x2160,preserve_aspect_ratio=increase"
set "ARTIFACT_REDUCTION_VAR=--vpp-nvvfx-artifact-reduction mode=0"
set "DENOISE_VAR=--vpp-nvvfx-denoise strength=0"
set "HDR_VAR=--vpp-ngx-truehdr maxluminance=1000,middlegray=18,saturation=200,contrast=200 --colormatrix bt2020nc --colorprim bt2020 --transfer smpte2084"

:: Initialize option variables to empty strings (default: disabled)
set FRUC_OPTION=
set RESIZE_OPTION=
set ARTIFACT_REDUCTION_OPTION=
set DENOISE_OPTION=
set HDR_OPTION=

:: Prompt user for Resize to 4K (default: disabled)
echo Enable Resize to 4K? [Y/N] (default is N)
set /p resize_enable=""
if /i "%resize_enable%"=="y" set "RESIZE_OPTION=%RESIZE_VAR%"
if /i "%resize_enable%"=="n" set "RESIZE_OPTION="

:: Prompt user for FRUC (fps=60) (default: disabled)
echo Enable FRUC (fps=60)? [Y/N] (default is N)
set /p fruc_enable=""
if /i "%fruc_enable%"=="y" set "FRUC_OPTION=%FRUC_VAR%"
if /i "%fruc_enable%"=="n" set "FRUC_OPTION="

:: Prompt user for Artifact Reduction (default: disabled)
echo Enable Artifact Reduction? [Y/N] (default is N)
set /p artifact_enable=""
if /i "%artifact_enable%"=="y" set "ARTIFACT_REDUCTION_OPTION=%ARTIFACT_REDUCTION_VAR%"
if /i "%artifact_enable%"=="n" set "ARTIFACT_REDUCTION_OPTION="

:: Prompt user for Denoise (default: disabled)
echo Enable Denoise? [Y/N] (default is N)
set /p denoise_enable=""
if /i "%denoise_enable%"=="y" set "DENOISE_OPTION=%DENOISE_VAR%"
if /i "%denoise_enable%"=="n" set "DENOISE_OPTION="

:: Prompt user for HDR conversion (default: disabled)
echo Enable HDR Conversion? [Y/N] (default is N)
set /p hdr_enable=""
if /i "%hdr_enable%"=="y" set "HDR_OPTION=%HDR_VAR%"
if /i "%hdr_enable%"=="n" set "HDR_OPTION="

:: Ask the user for custom crop parameters with default values
ECHO Enter the crop values for the video.
SET /P target=Enter target vertical height (in pixels) [%input_height%]: 
IF "%target%"=="" SET target=%input_height%

SET /A top=(%input_height%-%target%)/2
SET /A topMod=top%%4
IF "%topMod%" NEQ "0" SET /A top-=topMod

SET /A bottom=(%input_height%-%target%)/2
SET /A bottomMod=bottom%%4
IF "%bottomMod%" NEQ "0" SET /A bottom-=bottomMod

SET /P width=Enter target horizontal width (in pixels) [%input_width%]: 
IF "%width%"=="" SET width=%input_width%

SET /A left=(%input_width%-%width%)/2
SET /A leftMod=left%%4
IF "%leftMod%" NEQ "0" SET /A left-=leftMod

SET /A right=(%input_width%-%width%)/2
SET /A rightMod=right%%4
IF "%rightMod%" NEQ "0" SET /A right-=rightMod

:: Ask for QVBR target value
SET /P qvbr=Enter target QVBR [33]: 
IF "%qvbr%"=="" SET qvbr=33

:: Display selected encoding options
echo Enabled Options:
if defined FRUC_OPTION echo - FRUC: %FRUC_VAR%
if defined RESIZE_OPTION echo - Resize to 4K: %RESIZE_VAR%
if defined ARTIFACT_REDUCTION_OPTION echo - Artifact Reduction: %ARTIFACT_REDUCTION_VAR%
if defined DENOISE_OPTION echo - Denoise: %DENOISE_VAR%
if defined HDR_OPTION echo - HDR Conversion: %HDR_VAR%

:: Loop through the dragged video files and process each
FOR %%A IN (%*) DO (
    ECHO Processing %%A
    NVEncC64 --avhw --codec av1 --tier 1 --profile high --crop %left%,%top%,%right%,%bottom% --qvbr %qvbr% --preset p7 --output-depth 10 --multipass 2pass-full --nonrefp --aq --aq-temporal --aq-strength 0 --lookahead 32 --gop-len 6 --lookahead-level auto --transfer auto --audio-copy --chapter-copy --key-on-chapter --metadata copy %FRUC_OPTION% %RESIZE_OPTION% %ARTIFACT_REDUCTION_OPTION% %DENOISE_OPTION% %HDR_OPTION% -i %%A -o "%%~nA_HDR.mkv"
    mkdir HDR 2>nul
    move "%%~nA_HDR.mkv" HDR\  
)

:: Write settings to a log file in the HDR folder
(
    ECHO Crop Settings:
    ECHO Input Resolution Height: %input_height%
    ECHO Input Resolution Width: %input_width%
    ECHO Target Height: %target%
    ECHO Target Width: %width%
    ECHO Top Crop: %top%
    ECHO Bottom Crop: %bottom%
    ECHO Left Crop: %left%
    ECHO Right Crop: %right%
    ECHO QVBR Quality Setting: %qvbr%
    ECHO FRUC 60p: %FRUC_OPTION%
    ECHO Resize to 4K: %RESIZE_OPTION%
    ECHO Artifact Reduction: %ARTIFACT_REDUCTION_OPTION%
    ECHO Denoise: %DENOISE_OPTION%
    ECHO HDR Conversion: %HDR_OPTION%
) > HDR\encoding_log.txt

:: Notify user of log file and end program
ECHO Encoding settings have been saved to HDR\encoding_log.txt
ECHO Press any key to exit...
COLOR 0A
PAUSE >NUL
EXIT
