@echo off
COLOR 0C

:: Define individual variables for different parameters
set "FRUC_VAR=--vpp-fruc fps=60"
set "RESIZE_VAR=--vpp-resize algo=nvvfx-superres,superres-mode=0 --output-res 2160x2160,preserve_aspect_ratio=increase"
set "ARTIFACT_REDUCTION_VAR=--vpp-nvvfx-artifact-reduction mode=0"
set "DENOISE_VAR=--vpp-nvvfx-denoise strength=0"

:: Initialize option variables to empty strings
set FRUC_OPTION=
set RESIZE_OPTION=
set ARTIFACT_REDUCTION_OPTION=
set DENOISE_OPTION=

:: Prompt user for Resize to 4K first
echo Enable Resize to 4K? [Y/N]
set /p resize_enable=""
if /i "%resize_enable%"=="y" set "RESIZE_OPTION=%RESIZE_VAR%"
if /i "%resize_enable%"=="n" set "RESIZE_OPTION="

:: Prompt user for FRUC (fps=60)
echo Enable FRUC (fps=60)? [Y/N]
set /p fruc_enable=""
if /i "%fruc_enable%"=="y" set "FRUC_OPTION=%FRUC_VAR%"
if /i "%fruc_enable%"=="n" set "FRUC_OPTION="

:: Prompt user for Artifact Reduction
echo Enable Artifact Reduction? [Y/N]
set /p artifact_enable=""
if /i "%artifact_enable%"=="y" set "ARTIFACT_REDUCTION_OPTION=%ARTIFACT_REDUCTION_VAR%"
if /i "%artifact_enable%"=="n" set "ARTIFACT_REDUCTION_OPTION="

:: Prompt user for Denoise
echo Enable Denoise? [Y/N]
set /p denoise_enable=""
if /i "%denoise_enable%"=="y" set "DENOISE_OPTION=%DENOISE_VAR%"
if /i "%denoise_enable%"=="n" set "DENOISE_OPTION="

:: Print enabled options
echo Enabled Options:
if defined FRUC_OPTION echo - FRUC: %FRUC_VAR%
if defined RESIZE_OPTION echo - Resize to 4K: %RESIZE_VAR%
if defined ARTIFACT_REDUCTION_OPTION echo - Artifact Reduction: %ARTIFACT_REDUCTION_VAR%
if defined DENOISE_OPTION echo - Denoise: %DENOISE_VAR%

FOR %%A IN (%*) DO (
    ECHO Processing %%A
    NVEncC64 --avhw --codec av1 --tier 1 --profile high --qvbr 1 --preset p1 --output-depth 10 --multipass 2pass-full --nonrefp --aq --aq-temporal --aq-strength 0 --lookahead 32 --gop-len 4 --lookahead-level auto --transfer auto --audio-copy --chapter-copy --key-on-chapter --metadata copy %FRUC_OPTION% %RESIZE_OPTION% %ARTIFACT_REDUCTION_OPTION% %DENOISE_OPTION% --vpp-ngx-truehdr maxluminance=1000,middlegray=18,saturation=200,contrast=200 --colormatrix bt2020nc --colorprim bt2020 --transfer smpte2084 -i %%A -o "%%~nA_HDR.mkv"
    mkdir NR
    move "%%~nA_HDR.mkv" NR\
)

:: Print message to prompt user to press any key to end the program
echo Press any key to end the program...
pause > nul

EXIT