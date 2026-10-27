@echo off
title Register Daily Scan
echo Registering Windows scheduled task (daily scan)...
echo If it asks for admin rights, right-click this file and choose "Run as administrator".
echo.
where python >nul 2>nul
if %errorlevel%==0 (
    python "%~dp0install_task.py"
) else (
    py "%~dp0install_task.py"
)
echo.
pause
