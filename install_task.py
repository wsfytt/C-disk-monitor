# -*- coding: utf-8 -*-
"""
注册 / 取消 Windows 计划任务：
让 Windows 每天自动运行一次扫描（即使本程序没开着也能自动记录）。
用法：
  python install_task.py         # 注册每天自动扫描
  python install_task.py --uninstall   # 取消计划任务
"""

import sys
import os
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# 用当前正在运行的 Python 解释器（不写死路径，适配不同电脑/虚拟环境）
PYTHON = sys.executable
MONITOR = os.path.join(BASE_DIR, "monitor.py")
TASK_NAME = "CDiskMonitor-DailyScan"


def run(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def install():
    # 每天 12:00 触发一次扫描
    schtasks_cmd = (
        'schtasks /Create /TN "%s" /TR "\\"%s\\" \\"%s\\" --once" '
        '/SC DAILY /ST 12:00 /F'
        % (TASK_NAME, PYTHON, MONITOR)
    )
    code, out = run(schtasks_cmd)
    if code == 0:
        print("✓ 计划任务已注册成功。")
        print("  Windows 将每天 12:00 自动扫描一次 C 盘，并生成对比报告。")
        print("  即使本程序没开着，也会自动运行。")
        print("  任务以当前用户身份运行，一般无需管理员权限。")
    else:
        print("✗ 注册失败，返回信息：")
        print(out)
        print("")
        print("  多数情况无需管理员；如提示权限不足，请右键「以管理员身份运行」本脚本。")
        print("  也可以不用计划任务，直接双击「启动监视.bat」让程序常驻后台。")
    return code


def uninstall():
    cmd = 'schtasks /Delete /TN "%s" /F' % TASK_NAME
    code, out = run(cmd)
    if code == 0:
        print("✓ 计划任务已取消。")
    else:
        print("✗ 取消失败（可能本就没注册）：")
        print(out)
    return code


if __name__ == "__main__":
    if "--uninstall" in sys.argv:
        sys.exit(uninstall())
    else:
        sys.exit(install())
