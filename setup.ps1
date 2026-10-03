# Xdrop - PowerShell Automated Setup
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "  Xdrop - PowerShell Automated Setup & Configuration" -ForegroundColor Cyan
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Check Python
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "[ERROR] Python was not found on your system!" -ForegroundColor Red
    Write-Host "Please install Python 3.9+ from https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}

# 2. Run Python setup orchestrator
python "$ScriptDir\scripts\setup.py"
if ($LASTEXITCODE -ne 0) {
    Write-Host "`n[ERROR] Setup failed with exit code $LASTEXITCODE" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "[SUCCESS] Setup complete! You can start Xdrop by running ./run.bat or npm run start:service" -ForegroundColor Green
