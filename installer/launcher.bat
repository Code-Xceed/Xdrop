@echo off
setlocal
cd /d "%~dp0\.."
set PYTHONPATH=%CD%\apps\desktop-service;%PYTHONPATH%
start "" python apps\desktop-service\xdrop\main.py --gui
