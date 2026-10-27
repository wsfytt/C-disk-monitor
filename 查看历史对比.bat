@echo off
title View History Compare
echo Opening report (with history compare, no scan)...
echo.
where python >nul 2>nul
if %errorlevel%==0 (
    python "%~dp0monitor.py" --report
) else (
    py "%~dp0monitor.py" --report
)
echo.
echo Done. If the page did not open, run it again.
pause
