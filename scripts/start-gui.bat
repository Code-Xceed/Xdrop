@echo off
setlocal
cd /d "%~dp0\.."
echo ========================================================
echo  Starting Xdrop Companion Window
echo  Endpoint: http://localhost:8484
echo ========================================================
set PYTHONPATH=%CD%\apps\desktop-service;%PYTHONPATH%
python apps\desktop-service\xdrop\main.py --gui %*
pause
