@echo off
cd /d "%~dp0"
py -m pip install --upgrade pip
py -m pip install -r requirements.txt
echo.
echo Installation finished. Start the bridge with start.bat
pause
