for %%a in ("*.mkv") do ffmpeg -i "%%a" -c copy "%%~na.mp4"
pause