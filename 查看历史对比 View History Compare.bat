@echo off
title View History Compare
echo Opening report (with history compare, no scan)...
echo 正在打开报告（含历史对比，不重新扫描）...
echo.
where python >nul 2>nul
if %errorlevel%==0 (
    python "%~dp0monitor.py" --report
) else (
    py "%~dp0monitor.py" --report
)
echo.
echo Done. If the page did not open, run it again.
echo 完成。若页面未打开，请再运行一次。
pause
