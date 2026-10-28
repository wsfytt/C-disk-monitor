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

# 打包成 exe 后没有 python 和 monitor.py，计划任务直接调 exe 自己带参数
FROZEN = bool(getattr(sys, "frozen", False))
if FROZEN:
    TASK_PROGRAM = '"%s" --once' % sys.executable
else:
    TASK_PROGRAM = '"%s" "%s" --once' % (PYTHON, MONITOR)


def run(cmd):
    # 传参数列表、不用 shell：避免 cmd.exe 对 \\" 的解析差异（干净机器上易注册失败）
    r = subprocess.run(cmd, capture_output=True)
    out = ""
    for stream in (r.stdout, r.stderr):
        if not stream:
            continue
        # 中文 Windows 的 schtasks 输出是 GBK，先按 GBK 解，失败再退回 UTF-8 并容错
        try:
            out += stream.decode("gbk") if os.name == "nt" else stream.decode("utf-8")
        except (UnicodeDecodeError, LookupError):
            out += stream.decode("utf-8", "replace")
    return r.returncode, out


def install():
    # 每天 12:00 触发一次扫描
    code, out = run([
        "schtasks", "/Create", "/TN", TASK_NAME, "/TR", TASK_PROGRAM,
        "/SC", "DAILY", "/ST", "12:00", "/F",
    ])
    if code == 0:
        print("✓ 计划任务已注册成功 / Task registered.")
        print("  Windows 将每天 12:00 自动扫描一次 C 盘，并生成对比报告。")
        print("  It will scan the C drive daily at 12:00 and generate a report.")
        print("  即使本程序没开着，也会自动运行。/ Runs even if the app is closed.")
        print("  任务以当前用户身份运行，一般无需管理员权限。/ Usually no admin rights needed.")
    else:
        print("✗ 注册失败，返回信息 / Registration failed:")
        print(out)
        print("")
        print("  多数情况无需管理员；如提示权限不足，请右键「以管理员身份运行」本脚本。")
        print("  If it reports permission denied, right-click and run as administrator.")
        print("  也可以不用计划任务，直接双击「启动监视」让程序常驻后台。")
        print("  Or skip the task and run the monitor window instead.")
    return code


def uninstall():
    code, out = run(["schtasks", "/Delete", "/TN", TASK_NAME, "/F"])
    if code == 0:
        print("✓ 计划任务已取消 / Task removed.")
    else:
        print("✗ 取消失败（可能本就没注册）/ Removal failed (maybe not registered):")
        print(out)
    return code


if __name__ == "__main__":
    if "--uninstall" in sys.argv:
        sys.exit(uninstall())
    else:
        sys.exit(install())
