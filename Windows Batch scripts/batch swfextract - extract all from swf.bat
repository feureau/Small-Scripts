@echo off
setlocal enabledelayedexpansion
 
set /A Counter=1
 
echo Initial value of Counter: %Counter%
echo.
 
for %%f in (*.swf) do (
        echo File found: %%f
	swfextract --outputformat "extract_!Counter!_%%06d.%%s" -a 1- "%%f"
        echo Counter Before increment: !Counter!
        set /A Counter+=1
        echo Counter After Increment: !Counter!
        echo.
)
 
echo Counter after for loop: %Counter%
pause