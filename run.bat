@echo off
title Xdrop Desktop Service
cd /d "%~dp0"
echo Starting Xdrop Engine...
python apps\desktop-service\xdrop\main.py --gui
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Service stopped or encountered an error.
    pause
)
