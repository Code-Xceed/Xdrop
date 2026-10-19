@echo off
setlocal
cd /d "%~dp0"
set "PYTHONPATH=%~dp0src\desktop-service;%PYTHONPATH%"
python -m xdrop.main %*
