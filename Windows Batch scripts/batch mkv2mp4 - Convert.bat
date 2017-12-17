for %%a in ("*.mkv") do ffmpeg -i "%%a" -c:v libx264 -c:a aac -b:a 128k "%%~na.mp4"
pause