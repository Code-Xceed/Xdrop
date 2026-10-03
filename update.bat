@echo off
setlocal enabledelayedexpansion
title Xdrop One-Click Updater
cd /d "%~dp0"

echo ========================================================================
echo   Xdrop - Automated One-Click Updater
echo ========================================================================
echo.

:: 1. Search for available Python
set "PYTHON_EXE="
python -c "import sys" >nul 2>nul
if %ERRORLEVEL% EQU 0 set "PYTHON_EXE=python"
if not defined PYTHON_EXE (
    py -c "import sys" >nul 2>nul
    if %ERRORLEVEL% EQU 0 set "PYTHON_EXE=py"
)
if not defined PYTHON_EXE (
    for %%P in (
        "%LOCALAPPDATA%\Programs\Python\Python314\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
        "C:\Program Files\Python314\python.exe"
        "C:\Program Files\Python313\python.exe"
        "C:\Program Files\Python312\python.exe"
        "C:\Program Files\Python311\python.exe"
    ) do (
        if exist %%P (
            set "PYTHON_EXE=%%~P"
            goto :FoundPyUpdate
        )
    )
)
:FoundPyUpdate

if not defined PYTHON_EXE (
    echo [!] Python not found. Running setup.bat to install Python and dependencies...
    call setup.bat
    exit /b %ERRORLEVEL%
)

:: 2. Check for Git updates if in a git repo
where git >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    if exist ".git" (
        echo [1/4] Pulling latest updates from GitHub...
        git pull origin master
        if %ERRORLEVEL% NEQ 0 (
            echo [!] Git pull encountered a conflict or offline mode. Continuing with local update...
        )
    ) else (
        echo [1/4] Non-git installation detected. Skipping git pull.
    )
) else (
    echo [1/4] Git not found. Skipping repository sync.
)

:: 3. Update yt-dlp to latest upstream release
echo.
echo [2/4] Updating social media extractor engines (yt-dlp)...
"!PYTHON_EXE!" -m pip install --upgrade yt-dlp

:: 4. Update dependencies
echo.
echo [3/4] Updating core Python dependencies...
"!PYTHON_EXE!" -m pip install --upgrade -r requirements.txt

:: 5. Re-synchronize editor integrations and configurations
echo.
echo [4/4] Synchronizing editor scripts and configurations...
"!PYTHON_EXE!" scripts\setup.py

echo.
echo ========================================================================
echo   🎉 XDROP UPDATE COMPLETE! 🎉
echo ========================================================================
echo.

set /p LAUNCH="Start updated Xdrop right now? (Y/n): "
if /i "%LAUNCH%"=="n" (
    echo Done!
) else (
    echo Starting Xdrop...
    start "" run.bat
)

exit /b 0
