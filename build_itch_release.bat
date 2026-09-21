@echo off
setlocal
cd /d "%~dp0"
echo Starting Blackjack itch.io build pipeline...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_itch_release.ps1"
if %ERRORLEVEL% neq 0 (
    echo Build failed with error code %ERRORLEVEL%.
    pause
    exit /b %ERRORLEVEL%
)
echo.
echo Press any key to exit...
pause >nul
