for %%a in ("*.tif") do ffmpeg -i "%%a" -pix_fmt rgb24 "%%~na.jpg"
pause