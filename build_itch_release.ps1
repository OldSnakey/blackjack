<#
.SYNOPSIS
    Automated build pipeline for Blackjack standalone distribution on itch.io.
.DESCRIPTION
    Runs regression tests, packages the application via PyInstaller into an optimized
    standalone directory (--onedir), bundles player documentation, and produces a
    clean, ready-to-upload ZIP archive for itch.io.
#>

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "            BLACKJACK ITCH.IO RELEASE BUILD PIPELINE                  " -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

# 1. Verify dependencies
Write-Host "`n[1/5] Verifying Python and PyInstaller..." -ForegroundColor Yellow
python -c "import PyInstaller, pygame, tkinter; print('Dependencies verified successfully.')"
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Missing required packaging dependencies." -ForegroundColor Red
    exit 1
}

# 2. Run automated test suite
Write-Host "`n[2/5] Running automated test suite..." -ForegroundColor Yellow
python -m unittest discover tests
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Test suite failed! Aborting build to protect release quality." -ForegroundColor Red
    exit 1
}
Write-Host "Test suite passed cleanly." -ForegroundColor Green

# 3. Clean previous build artifacts
Write-Host "`n[3/5] Cleaning previous build artifacts..." -ForegroundColor Yellow
Get-Process -Name "Blackjack" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 300
if (Test-Path "build") { Remove-Item -Recurse -Force "build" -ErrorAction SilentlyContinue }
if (Test-Path "dist")  { Remove-Item -Recurse -Force "dist" -ErrorAction SilentlyContinue }

# 4. Compile standalone executable with PyInstaller
Write-Host "`n[4/5] Packaging standalone executable via PyInstaller..." -ForegroundColor Yellow
python -m PyInstaller --clean --noconfirm blackjack.spec
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: PyInstaller build failed." -ForegroundColor Red
    exit 1
}

# 5. Assemble distribution package and create ZIP
Write-Host "`n[5/5] Assembling release folder and creating itch.io ZIP archive..." -ForegroundColor Yellow
$releaseFolder = Join-Path $ScriptDir "dist\Blackjack-Windows"

if (-not (Test-Path $releaseFolder)) {
    Write-Host "ERROR: Release folder $releaseFolder does not exist." -ForegroundColor Red
    exit 1
}

# Copy player instructions into release folder
Copy-Item -Path "README_PLAYERS.txt" -Destination $releaseFolder -Force

# Create ZIP archive
$zipOutput = Join-Path $ScriptDir "dist\Blackjack-Windows-v1.0.0.zip"
if (Test-Path $zipOutput) { Remove-Item -Force $zipOutput }

# Zip the release folder
Compress-Archive -Path "$releaseFolder\*" -DestinationPath $zipOutput -CompressionLevel Optimal

$zipSizeMb = [math]::Round(((Get-Item $zipOutput).Length / 1MB), 2)

Write-Host "`n======================================================================" -ForegroundColor Green
Write-Host "                    BUILD COMPLETED SUCCESSFULLY!                     " -ForegroundColor Green
Write-Host "======================================================================" -ForegroundColor Green
Write-Host "Release Directory: $releaseFolder" -ForegroundColor White
Write-Host "itch.io ZIP Package: $zipOutput ($zipSizeMb MB)" -ForegroundColor White
Write-Host "`nNext Step: Upload '$zipOutput' directly to your itch.io dashboard!" -ForegroundColor Cyan
