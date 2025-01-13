@echo off
COLOR 0C
:: Set console text color to red

:: Initialize variables with default values for cutting intro and outro
SET intro_trim=293
SET outtro_trim=1131
SET upscale=
SET trim_flags=

:: Prompt user for "Cut Intro?" with default set to "yes"
SET /P cut_intro="Cut Intro? (y/n or 1/0, default is yes): "
IF /I "%cut_intro%"=="n" SET intro_trim=0
IF /I "%cut_intro%"=="0" SET intro_trim=0

:: Prompt user for "Cut Outtro?" with default set to "yes"
SET /P cut_outtro="Cut Outtro? (y/n or 1/0, default is yes): "
IF /I "%cut_outtro%"=="n" SET outtro_trim=0
IF /I "%cut_outtro%"=="0" SET outtro_trim=0

:: Prepare --trim flag only if needed
IF NOT "%intro_trim%"=="0" IF NOT "%outtro_trim%"=="0" SET trim_flags=--trim %intro_trim%:%outtro_trim%

:: Prompt user for "Convert to 4K?" with default set to "no"
SET /P convert_to_4k="Convert to 4K? (y/n or 1/0, default is no): "
IF /I "%convert_to_4k%"=="y" SET upscale=--vpp-resize algo=nvvfx-superres,superres-mode=0 --output-res 2160x2160,preserve_aspect_ratio=increase
IF /I "%convert_to_4k%"=="1" SET upscale=--vpp-resize algo=nvvfx-superres,superres-mode=0 --output-res 2160x2160,preserve_aspect_ratio=increase

:: Loop through all command-line arguments (file paths)
FOR %%A IN (%*) DO (
    :: Display the current file being processed
    ECHO Processing: %%A

    :: Encode video using NVEncC64 with specified settings
    NVEncC64 --avhw %trim_flags% --codec av1 --tier 1 --profile high --cqp 43 --preset p7 --output-depth 10 ^
    --multipass 2pass-full --lookahead 32 --gop-len 4 --nonrefp --aq --aq-temporal --aq-strength 0 ^
    --transfer auto --audio-codec ac3 --audio-bitrate 640 --chapter-copy --key-on-chapter --metadata copy ^
    --vpp-ngx-truehdr maxluminance=1000,middlegray=18,saturation=200,contrast=200 ^
    --colormatrix bt2020nc --colorprim bt2020 --transfer smpte2084 %upscale% -i %%A -o %%A_HDR.mkv 

    :: Verify if the output file exists, then move to HDR folder
    IF EXIST %%A_HDR.mkv (
        mkdir HDR
        move %%A_HDR.mkv HDR\
    ) ELSE (
        ECHO Failed to process %%A
    )
)

:: Set console text color to green
COLOR 0A

:: Pause and wait for user input before exiting
PAUSE >nul
EXIT
