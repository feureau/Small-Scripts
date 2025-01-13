@echo off
:: Prompt the user for the number of minutes to wait
set /p minutes=Enter the time in minutes before putting the computer to sleep: 

:: Validate that the input is a number
for /f "delims=0123456789" %%a in ("%minutes%") do (
    echo Invalid input. Please enter a valid number of minutes.
    pause
    exit /b
)

:: Convert minutes to seconds
set /a seconds=%minutes%*60

:: Inform the user
echo The computer will go to sleep in %minutes% minute(s).
echo Countdown starting...

:: Countdown loop
:countdown
if %seconds% leq 0 goto sleep
echo %seconds% seconds remaining...
timeout /t 1 >nul
set /a seconds=%seconds%-1
goto countdown

:: Put the computer to sleep
:sleep
echo Time's up! Putting the computer to sleep now...
rundll32.exe powrprof.dll,SetSuspendState 0,1,0
