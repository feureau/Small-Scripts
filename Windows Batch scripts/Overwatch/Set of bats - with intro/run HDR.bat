::set "your_dir=%cd%"     
::cd %your_dir%
::ECHO "cd %your_dir%"

ECHO "call OW split Horz - 4K HDR - GPU.bat"
call "OW split Horz - 4K HDR - GPU.bat"

ECHO "Call OW split to vert - 4K HDR - GPU.bat"
call "OW split to vert - 4K HDR - GPU.bat"

ECHO "Call move to processed"
call "Move to Processed.bat"

ECHO "call %cd%\vert split\folder_splitter.bat"
call "%cd%\vert split\folder_splitter.bat"
::cd %your_dir%
::ECHO "cd %your_dir%"

::ECHO "call %cd%\horz split\folder_splitter.bat"
::call "%cd%\horz split\folder_splitter.bat"
::cd %your_dir%
::ECHO "cd %your_dir%"

ECHO "call %cd%\horz split\_directory lister.bat"
call "%cd%\horz split\_directory lister.bat"
cd %your_dir%
ECHO "cd %your_dir%"


COLOR 0A
::ECHO.
ECHO Processing complete!
::ECHO Press Any Key To Exit...
PAUSE >nul
EXIT

::set "your_dir=path_to_your_directory"     
::pushd %cd%
::cd %your_dir%
::run_your_command
::popd

PAUSE >nul
EXIT