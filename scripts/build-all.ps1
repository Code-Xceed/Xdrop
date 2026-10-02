# Xdrop Full Build Script
$ErrorActionPreference = "Stop"

Write-Host "=== Building Xdrop ===" -ForegroundColor Cyan

# 1. Install frontend packages if needed & build frontend
Write-Host "1. Building React + TypeScript Frontend..." -ForegroundColor Yellow
npm run build:ui

# 2. Run backend test suite
Write-Host "2. Running Backend Pytest Suite..." -ForegroundColor Yellow
python -m pytest tests -v

Write-Host "=== Build Completed Successfully! ===" -ForegroundColor Green
