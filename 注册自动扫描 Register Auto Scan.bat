@echo off
title Register Auto Scan
chcp 936 >nul
rem ONLOGON 触发器必须提升权限才能创建，普通权限会报「错误: 拒绝访问」。
rem 先自检，没提升就用 UAC 重新拉起自己，点一下「是」即可。
net session >nul 2>&1
if not "%errorlevel%"=="0" (
    echo Requesting administrator rights. Please click "Yes" in the UAC dialog.
    echo 正在请求管理员权限，请在弹窗里点「是」。
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)
echo Registering Windows scheduled task (scan after every logon)...
echo 正在注册 Windows 计划任务（每次登录后自动扫描）...
echo It skips the run if the last scan was less than 6 hours ago.
echo 距上次扫描不足 6 小时会自动跳过，所以一天最多记一份。
echo.
where python >nul 2>nul
if %errorlevel%==0 (
    python "%~dp0install_task.py"
) else (
    py "%~dp0install_task.py"
)
echo.
pause
