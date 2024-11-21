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

:: Set the resolution height and width based on the user’s choice
IF "%res_choice%"=="1" (
    SET input_height=1080
    SET input_width=1920
) ELSE (
    SET input_height=2160
    SET input_width=3840
)

:: Define individual variables for different parameters
set "FRUC_VAR=--vpp-fruc fps=60"

:: Ask the user for custom crop parameters with default values
ECHO Enter the crop values for the video.
SET /P target=Enter target vertical height (in pixels) [%input_height%]: 
IF "%target%"=="" SET target=%input_height%

SET /A top=(%input_height%-%target%)/2
:: Check if top is divisible by 4, if not adjust it
SET /A topMod=top%%4
IF "%topMod%" NEQ "0" (
    SET /A top-=topMod
)
SET /A bottom=(%input_height%-%target%)/2
:: Check if bottom is divisible by 4, if not adjust it
SET /A bottomMod=bottom%%4
IF "%bottomMod%" NEQ "0" (
    SET /A bottom-=bottomMod
)

SET /P width=Enter target horizontal width (in pixels) [%input_width%]: 
IF "%width%"=="" SET width=%input_width%

SET /A left=(%input_width%-%width%)/2
:: Check if left is divisible by 4, if not adjust it
SET /A leftMod=left%%4
IF "%leftMod%" NEQ "0" (
    SET /A left-=leftMod
)
SET /A right=(%input_width%-%width%)/2
:: Check if right is divisible by 4, if not adjust it
SET /A rightMod=right%%4
IF "%rightMod%" NEQ "0" (
    SET /A right-=rightMod
)

SET /P qvbr=Enter target QVBR [33]: 
IF "%qvbr%"=="" SET qvbr=33

:: Prompt user for FRUC (fps=60)
echo Enable FRUC (fps=60)? [Y/N]
set /p fruc_enable=""
if /i "%fruc_enable%"=="y" set "FRUC_OPTION=%FRUC_VAR%"
if /i "%fruc_enable%"=="n" set "FRUC_OPTION="

:: Loop through the dropped video file(s)
FOR %%A IN (%*) DO (
    ECHO Processing: %%A

    NVEncC64 --avhw --codec av1 --tier 1 --profile high --crop %left%,%top%,%right%,%bottom% --qvbr %qvbr% --preset p7 --output-depth 10 --multipass 2pass-full --nonrefp --aq --aq-temporal --aq-strength 0 --lookahead 32 --gop-len 6 --lookahead-level auto --transfer auto --audio-copy --chapter-copy --key-on-chapter --metadata copy %FRUC_OPTION% -i %%A -o %%A_av1.mkv

    :: Create the AV1 directory and move the output file
    mkdir AV1 2>nul
    move "%%A_av1.mkv" "AV1\"  
)

:: Write settings to a log file in the AV1 folder
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
) > AV1\encoding_log.txt

:: Notify the user of the log file
ECHO Encoding settings have been saved to AV1\encoding_log.txt
ECHO Press any key to exit...
COLOR 0A
PAUSE >NUL
EXIT
