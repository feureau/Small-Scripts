@Echo Off
If /I Not "%__CD__%"=="%~dp0" PushD "%~dp0" 2>Nul||Exit/B
SetLocal EnableDelayedExpansion
Set "DirN=-1"

ECHO "Directory: Echo %0"

:Check_DirN
Set/A "DirN+=1"
If Exist "%DirN%" GoTo Check_DirN

ECHO "Splitting folder: %DirN%"

Set "limit=14"
For %%A In (*.mov *.mp4 *.mkv) Do (
    If Not Exist "%DirN%" MD "%DirN%"
    If /I Not "%%~nxA"=="%~nx0" RoboCopy . "%DirN%" "%%A" /MOV 1>NUL
    Set/A "limit-=1"
    If !limit! Lss 0 GoTo Check_DirN
)
Echo "Task Done!"
::Timeout -1 1>Nul