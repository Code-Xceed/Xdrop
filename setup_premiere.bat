@echo off
setlocal enabledelayedexpansion
title Xdrop Adobe Premiere Pro Setup & Installation
cd /d "%~dp0"

echo ========================================================================
echo    Xdrop — Adobe Premiere Pro ^& Creative Cloud Dedicated Setup
echo ========================================================================
echo.

set "PYTHON_BIN="

if exist "%~dp0.venv\Scripts\python.exe" (
    set "PYTHON_BIN=%~dp0.venv\Scripts\python.exe"
    goto :FoundPython
)

if exist "C:\Program Files\Python314\python.exe" (
    set "PYTHON_BIN=C:\Program Files\Python314\python.exe"
    goto :FoundPython
)

for %%P in (
    "%LOCALAPPDATA%\Programs\Python\Python314\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python39\python.exe"
    "C:\Program Files\Python314\python.exe"
    "C:\Program Files\Python313\python.exe"
    "C:\Program Files\Python312\python.exe"
    "C:\Program Files\Python311\python.exe"
    "C:\Program Files\Python310\python.exe"
    "C:\Program Files\Python39\python.exe"
) do (
    if exist %%P (
        set "PYTHON_BIN=%%~P"
        goto :FoundPython
    )
)

python -c "import sys" >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    set "PYTHON_BIN=python"
    goto :FoundPython
)

py -c "import sys" >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    set "PYTHON_BIN=py"
    goto :FoundPython
)

if exist "%~dp0XdropInstaller-Premiere.exe" (
    echo [*] Launching standalone Adobe Premiere installer binary...
    start "" "%~dp0XdropInstaller-Premiere.exe"
    exit /b 0
)

echo [!] Python 3 was not detected on this system.
echo [*] Attempting to install Python via Windows Package Manager (winget)...
winget install Python.Python.3.11 --accept-source-agreements --accept-package-agreements
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [X] Could not install Python automatically.
    echo [*] Please install Python 3.9+ from https://www.python.org/downloads/
    pause
    exit /b 1
)
set "PYTHON_BIN=python"

:FoundPython
echo [+] Using Python: %PYTHON_BIN%
echo.

echo [*] Validating dependencies...
"%PYTHON_BIN%" -m pip install --quiet --upgrade pip >nul 2>nul
"%PYTHON_BIN%" -m pip install -r requirements.txt >nul 2>nul

echo.
echo [*] Launching Adobe Premiere Pro ^& Creative Cloud Setup...
set "PYTHONPATH=%~dp0src;%~dp0src\desktop-service;%PYTHONPATH%"
"%PYTHON_BIN%" src\tools\installer_premiere.py %*

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================================================
    echo   [+] Adobe Premiere Pro setup completed successfully!
    echo ========================================================================
)

pause
