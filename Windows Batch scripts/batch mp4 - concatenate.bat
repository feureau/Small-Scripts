set path2exe=E:\ffmpeg-20170723-dd4b7ba-win64-static\bin\ffmpeg.exe
(for %%i in (*.mp4) do @echo file '%%i') > list.txt
%path2exe% -f concat -i list.txt -c copy output.mp4
del list.txt
pause