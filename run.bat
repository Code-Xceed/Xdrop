@echo off
title Xdrop Desktop Service
cd /d "%~dp0"
echo Starting Xdrop Engine...
if exist "C:\Program Files\Python314\python.exe" (
    "C:\Program Files\Python314\python.exe" apps\desktop-service\xdrop\main.py --gui
) else (
    python apps\desktop-service\xdrop\main.py --gui
)
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Service stopped or encountered an error.
    pause
)
