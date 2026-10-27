@echo off
title Scan C Drive
echo Scanning C drive... (about 30 seconds)
echo 正在扫描 C 盘...（约 30 秒）
echo The report will open automatically when done.
echo 完成后报告会自动打开。
echo.
where python >nul 2>nul
if %errorlevel%==0 (
    python "%~dp0monitor.py" --once --open
) else (
    py "%~dp0monitor.py" --once --open
)
echo.
echo Done. Report opened in browser (if not, check the reports folder).
echo 完成。报告已在浏览器打开（若没有，请查看 reports 文件夹）。
pause
