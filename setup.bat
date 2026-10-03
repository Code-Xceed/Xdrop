@echo off
setlocal enabledelayedexpansion
title Xdrop One-Click Setup
cd /d "%~dp0"

echo ========================================================================
echo   Xdrop - Universal Media Importer Automated Setup
echo ========================================================================
echo.

:: 1. Search for available Python installation
set "PYTHON_EXE="

:: Check standard 'python' command
python -c "import sys" >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    set "PYTHON_EXE=python"
    goto :PythonFound
)

:: Check Windows 'py' launcher
py -c "import sys" >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    set "PYTHON_EXE=py"
    goto :PythonFound
)

:: Probe standard Python install directories (in case Python was installed without PATH)
echo Probing system for Python installations...
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
    "C:\Python312\python.exe"
    "C:\Python311\python.exe"
    "C:\Python310\python.exe"
) do (
    if exist %%P (
        set "PYTHON_EXE=%%~P"
        for %%D in ("%%~dpP.") do set "PATH=%%~fD;%%~fD\Scripts;!PATH!"
        goto :PythonFound
    )
)

:: 2. If Python is not installed, automatically install it
echo.
echo [!] Python is not installed on this machine.
echo [*] Initiating automatic silent Python installation...
echo.

:: Try Windows Package Manager (winget) first
where winget >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo [*] Installing official Python 3.11 via Windows Package Manager (winget)...
    winget install --id Python.Python.3.11 --silent --accept-source-agreements --accept-package-agreements
    if %ERRORLEVEL% EQU 0 (
        goto :ScanNewPython
    )
)

:: Direct download via PowerShell fallback
echo [*] Downloading official Python 3.11 installer from python.org...
set "TEMP_PY_INSTALLER=%TEMP%\xdrop_python_setup.exe"
powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object System.Net.WebClient).DownloadFile('https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe', '%TEMP_PY_INSTALLER%')"
if exist "%TEMP_PY_INSTALLER%" (
    echo [*] Installing Python silently (configured with PATH)...
    "%TEMP_PY_INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0
    del "%TEMP_PY_INSTALLER%" 2>nul
)

:ScanNewPython
for %%P in (
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "C:\Program Files\Python311\python.exe"
    "C:\Program Files\Python312\python.exe"
) do (
    if exist %%P (
        set "PYTHON_EXE=%%~P"
        for %%D in ("%%~dpP.") do set "PATH=%%~fD;%%~fD\Scripts;!PATH!"
        echo [+] Python was successfully installed: !PYTHON_EXE!
        goto :PythonFound
    )
)

:: Fallback warning if auto-installation couldn't complete
echo.
echo [ERROR] Automatic Python installation could not complete.
echo Please download and install Python 3.9+ from:
echo   https://www.python.org/downloads/
echo (Ensure you check "Add Python to PATH" during installation)
echo.
pause
exit /b 1

:PythonFound
echo [OK] Using Python: !PYTHON_EXE!
echo.

:: 3. Execute setup orchestrator
"!PYTHON_EXE!" scripts\setup.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Setup encountered an issue. See above for details.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo ========================================================================
echo   Setup Complete! Starting Xdrop now...
echo   (You can also launch anytime by double-clicking "run.bat")
echo ========================================================================
echo.
start "" run.bat
exit /b 0
