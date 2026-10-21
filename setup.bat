@echo off
setlocal enabledelayedexpansion
title Xdrop Dedicated Setup ^& Installation
cd /d "%~dp0"

echo ========================================================================
echo    Xdrop — Dedicated Editor Setup ^& Installation
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
echo ========================================================================
echo   Select your target video editor to configure:
echo ========================================================================
echo   [1] DaVinci Resolve Setup (Free ^& Studio)
echo   [2] Adobe Premiere Pro Setup (Creative Cloud)
echo   [3] Exit
echo ========================================================================
echo.

set /p "CHOICE=Enter choice [1, 2, or 3]: "
if "%CHOICE%"=="1" goto :RunResolve
if "%CHOICE%"=="2" goto :RunPremiere
if "%CHOICE%"=="3" exit /b 0

echo [!] Invalid selection. Defaulting to DaVinci Resolve.
:RunResolve
echo.
echo [*] Launching DaVinci Resolve Setup...
set "PYTHONPATH=%~dp0src;%~dp0src\desktop-service;%PYTHONPATH%"
"%PYTHON_BIN%" src\tools\installer_resolve.py %*
goto :Done

:RunPremiere
echo.
echo [*] Launching Adobe Premiere Pro Setup...
set "PYTHONPATH=%~dp0src;%~dp0src\desktop-service;%PYTHONPATH%"
"%PYTHON_BIN%" src\tools\installer_premiere.py %*
goto :Done

:Done
if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================================================
    echo   [+] Setup completed successfully! You can now launch your editor.
    echo ========================================================================
)
pause
