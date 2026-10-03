@echo off
setlocal enabledelayedexpansion
title Xdrop Desktop Service
cd /d "%~dp0"
echo Starting Xdrop Engine...

set "PYTHON_EXE="

if exist "%~dp0.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
    goto :RunService
)

if exist "C:\Program Files\Python314\python.exe" (
    set "PYTHON_EXE=C:\Program Files\Python314\python.exe"
    goto :RunService
)

python -c "import sys" >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    set "PYTHON_EXE=python"
    goto :RunService
)

py -c "import sys" >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    set "PYTHON_EXE=py"
    goto :RunService
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
        set "PYTHON_EXE=%%~P"
        goto :RunService
    )
)

echo.
echo [!] Python not found on this computer.
echo [*] Please run setup.bat first to configure Python.
pause
exit /b 1

:RunService
"%PYTHON_EXE%" apps\desktop-service\xdrop\main.py --gui
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Service stopped or encountered an error.
    pause
)
