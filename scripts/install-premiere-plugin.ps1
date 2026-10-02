# Xdrop - Adobe Premiere Pro & After Effects Plugin Installer
$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Installing Xdrop Plugin for Premiere Pro & After Effects" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$sourceDir = Join-Path $PSScriptRoot "..\apps\premiere-plugin"
$cepDir = Join-Path $env:APPDATA "Adobe\CEP\extensions"
$targetDir = Join-Path $cepDir "com.xdrop.panel"
$legacyDir = Join-Path $cepDir "com.resolvefetch.premiere"

# 1. Create target extensions directory
if (-not (Test-Path $cepDir)) {
    New-Item -ItemType Directory -Path $cepDir -Force | Out-Null
}

# 2. Copy extension files
Write-Host "Copying plugin files to: $targetDir" -ForegroundColor Yellow
if (Test-Path $targetDir) {
    Remove-Item -Path $targetDir -Recurse -Force
}
Copy-Item -Path $sourceDir -Destination $targetDir -Recurse -Force

# Also sync legacy folder for backwards compatibility
if (Test-Path $legacyDir) {
    Remove-Item -Path $legacyDir -Recurse -Force
}
Copy-Item -Path $sourceDir -Destination $legacyDir -Recurse -Force

# 3. Enable Adobe CEP PlayerDebugMode in Windows Registry for CC 2019-2026+
Write-Host "Enabling Adobe CEP Developer Mode in Registry..." -ForegroundColor Yellow
$csxsVersions = @("9", "10", "11", "12", "13", "14", "15", "16")

foreach ($ver in $csxsVersions) {
    $regPath = "HKCU:\Software\Adobe\CSXS.$ver"
    if (-not (Test-Path $regPath)) {
        New-Item -Path $regPath -Force | Out-Null
    }
    Set-ItemProperty -Path $regPath -Name "PlayerDebugMode" -Value "1" -Type String -Force
}

Write-Host ""
Write-Host "[SUCCESS] Xdrop installed for Adobe Premiere Pro & After Effects!" -ForegroundColor Green
Write-Host "Location: $targetDir" -ForegroundColor DarkGray
Write-Host ""
Write-Host "To use in Premiere Pro or After Effects:" -ForegroundColor Cyan
Write-Host "1. Start Xdrop engine: npm run start:service (or Xdrop.exe)"
Write-Host "2. Open Adobe Premiere Pro or Adobe After Effects"
Write-Host "3. Go to menu: Window -> Extensions -> Xdrop"
Write-Host "4. Download any media URL and it will automatically import into your project!"
Write-Host "==========================================================" -ForegroundColor Cyan
