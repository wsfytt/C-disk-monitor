@echo off
title Register Daily Scan
echo Registering Windows scheduled task (daily scan)...
echo 正在注册 Windows 计划任务（每日扫描）...
echo If it asks for admin rights, right-click this file and choose "Run as administrator".
echo 如需管理员权限，请右键此文件并选择"以管理员身份运行"。
echo.
where python >nul 2>nul
if %errorlevel%==0 (
    python "%~dp0install_task.py"
) else (
    py "%~dp0install_task.py"
)
echo.
pause
