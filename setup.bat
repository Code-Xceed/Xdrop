@echo off
setlocal enabledelayedexpansion
title Xdrop One-Click Setup
cd /d "%~dp0"

echo ========================================================================
echo   Xdrop - Automated Setup for Windows
echo ========================================================================
echo.

:: 1. Check Python installation
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed or not in your system PATH!
    echo Please download and install Python 3.9+ from:
    echo   https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

:: 2. Execute automated setup script
python scripts\setup.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Setup encountered an issue. See above for details.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo ========================================================================
echo   Setup is complete! You can now launch Xdrop anytime by double-clicking
echo   "run.bat" in this directory.
echo ========================================================================
echo.

set /p LAUNCH="Would you like to start Xdrop right now? (Y/n): "
if /i "%LAUNCH%"=="n" (
    echo Goodbye!
) else (
    echo Starting Xdrop...
    start "" run.bat
)

exit /b 0
