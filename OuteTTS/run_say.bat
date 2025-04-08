@echo off
CALL "%USERPROFILE%\anaconda3\Scripts\activate.bat"
conda activate F:\AI\OuteTTS\venv
python -u say.py %*
pause
