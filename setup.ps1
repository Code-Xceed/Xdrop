# Xdrop - PowerShell Automated Setup
[CmdletBinding()]
param()

$ErrorActionPreference = "Continue"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "  Xdrop - PowerShell Automated Setup & Configuration" -ForegroundColor Cyan
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Search for available Python installation
$pythonExe = $null

$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if ($pythonCmd) {
    try {
        & python -c "import sys" 2>$null
        if ($LASTEXITCODE -eq 0) {
            $pythonExe = "python"
        }
    } catch {}
}

if (-not $pythonExe) {
    $pyCmd = Get-Command py -ErrorAction SilentlyContinue
    if ($pyCmd) {
        try {
            & py -c "import sys" 2>$null
            if ($LASTEXITCODE -eq 0) {
                $pythonExe = "py"
            }
        } catch {}
    }
}

if (-not $pythonExe) {
    Write-Host "Probing system for installed Python runtimes..." -ForegroundColor Gray
    $candidates = @(
        "$env:LOCALAPPDATA\Programs\Python\Python314\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python39\python.exe",
        "C:\Program Files\Python314\python.exe",
        "C:\Program Files\Python313\python.exe",
        "C:\Program Files\Python312\python.exe",
        "C:\Program Files\Python311\python.exe",
        "C:\Program Files\Python310\python.exe",
        "C:\Program Files\Python39\python.exe",
        "C:\Python312\python.exe",
        "C:\Python311\python.exe",
        "C:\Python310\python.exe"
    )
    foreach ($cand in $candidates) {
        if (Test-Path $cand) {
            $pythonExe = $cand
            $pDir = Split-Path -Parent $cand
            $env:PATH = "$pDir;$pDir\Scripts;$env:PATH"
            break
        }
    }
}

# 2. Auto-install Python if not found
if (-not $pythonExe) {
    Write-Host "`n[!] Python was not found on your system." -ForegroundColor Yellow
    Write-Host "[*] Automatically installing Python 3.11..." -ForegroundColor Cyan

    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if ($winget) {
        Write-Host "[*] Installing official Python via Windows Package Manager (winget)..." -ForegroundColor Gray
        Start-Process winget -ArgumentList "install", "--id", "Python.Python.3.11", "--silent", "--accept-source-agreements", "--accept-package-agreements" -Wait
    } else {
        Write-Host "[*] Downloading official Python 3.11 from python.org..." -ForegroundColor Gray
        $tempInstaller = Join-Path $env:TEMP "xdrop_python_setup.exe"
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        (New-Object System.Net.WebClient).DownloadFile("https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe", $tempInstaller)
        if (Test-Path $tempInstaller) {
            Write-Host "[*] Running silent installation (adding Python to PATH)..." -ForegroundColor Gray
            Start-Process $tempInstaller -ArgumentList "/quiet", "InstallAllUsers=0", "PrependPath=1", "Include_test=0" -Wait
            Remove-Item $tempInstaller -Force -ErrorAction SilentlyContinue
        }
    }

    # Re-scan for installed Python
    $checkPaths = @(
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "C:\Program Files\Python311\python.exe",
        "C:\Program Files\Python312\python.exe"
    )
    foreach ($cp in $checkPaths) {
        if (Test-Path $cp) {
            $pythonExe = $cp
            $pDir = Split-Path -Parent $cp
            $env:PATH = "$pDir;$pDir\Scripts;$env:PATH"
            Write-Host "[+] Python successfully installed: $pythonExe" -ForegroundColor Green
            break
        }
    }
}

if (-not $pythonExe) {
    Write-Host "`n[ERROR] Automated Python installation could not complete." -ForegroundColor Red
    Write-Host "Please install Python 3.9+ from https://www.python.org/downloads/ (Check 'Add Python to PATH')" -ForegroundColor Yellow
    exit 1
}

Write-Host "[OK] Using Python: $pythonExe`n" -ForegroundColor Green

# 3. Run Python setup orchestrator
& $pythonExe "$ScriptDir\scripts\setup.py"
if ($LASTEXITCODE -ne 0) {
    Write-Host "`n[ERROR] Setup failed with exit code $LASTEXITCODE" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "[SUCCESS] Setup complete! You can start Xdrop anytime by running ./run.bat" -ForegroundColor Green
