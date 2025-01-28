@echo off
COLOR 0C
:: Check if a file is dragged onto the script
IF "%~1"=="" (
    ECHO No video file specified. Please drag and drop a video file onto the script.
    PAUSE
    EXIT /B
)

:: Ask the user for custom crop parameters with default values
ECHO Enter the crop values for the video.
SET /P target=Enter target vertical height (in pixels) [2160]: 
IF "%target%"=="" SET target=2160

SET /A top=(2160-%target%)/2
:: Check if top is divisible by 4, if not adjust it
SET /A topMod=top%%4
IF "%topMod%" NEQ "0" (
    SET /A top-=topMod
)
SET /A bottom=(2160-%target%)/2
:: Check if bottom is divisible by 4, if not adjust it
SET /A bottomMod=bottom%%4
IF "%bottomMod%" NEQ "0" (
    SET /A bottom-=bottomMod
)

SET /P width=Enter target horizontal width (in pixels) [3840]: 
IF "%width%"=="" SET width=3840

SET /A left=(3840-%width%)/2
:: Check if left is divisible by 4, if not adjust it
SET /A leftMod=left%%4
IF "%leftMod%" NEQ "0" (
    SET /A left-=leftMod
)
SET /A right=(3840-%width%)/2
:: Check if right is divisible by 4, if not adjust it
SET /A rightMod=right%%4
IF "%rightMod%" NEQ "0" (
    SET /A right-=rightMod
)

ECHO Enter the Quality-VBR (QVBR) setting.
SET /P qvbr=Enter target QVBR [33]: 
IF "%qvbr%"=="" SET qvbr=33

:: Loop through the dropped video file(s)
FOR %%A IN (%*) DO (
    ECHO Processing: %%A

    NVEncC64 --avhw --codec av1 --tier 1 --profile high --crop %left%,%top%,%right%,%bottom% --qvbr %qvbr% --preset p7 --output-depth 10 --multipass 2pass-full --nonrefp --aq --aq-temporal --aq-strength 0 --lookahead 32 --gop-len 6 --lookahead-level auto --transfer auto --audio-copy --chapter-copy --key-on-chapter --metadata copy -i %%A -o %%A_av1.mkv

    :: Create the AV1 directory and move the output file
    mkdir AV1 2>nul
    move "%%A_av1.mkv" "AV1\"
)
COLOR 0A
PAUSE >NUL
EXIT