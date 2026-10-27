@echo off
title Scan C Drive
echo Scanning C drive... (about 30 seconds)
echo The report will open automatically when done.
echo.
where python >nul 2>nul
if %errorlevel%==0 (
    python "%~dp0monitor.py" --once --open
) else (
    py "%~dp0monitor.py" --once --open
)
echo.
echo Done. Report opened in browser (if not, check the reports folder).
pause
