@echo off
title C Drive Monitor
echo ============================================
echo   C Drive Monitor
echo   Keep this window open. It records once a day.
echo   Close this window to stop monitoring.
echo ============================================
echo.
where python >nul 2>nul
if %errorlevel%==0 (
    python "%~dp0monitor.py"
) else (
    py "%~dp0monitor.py"
)
pause
