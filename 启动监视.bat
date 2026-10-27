@echo off
title C Drive Monitor
echo ============================================
echo   C Drive Monitor - C盘空间监视器
echo   Keep this window open. It records once a day.
echo   保持此窗口开启。它会每天记录一次。
echo   Close this window to stop monitoring.
echo   关闭此窗口即停止监视。
echo ============================================
echo.
where python >nul 2>nul
if %errorlevel%==0 (
    python "%~dp0monitor.py"
) else (
    py "%~dp0monitor.py"
)
pause
