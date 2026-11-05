# -*- coding: utf-8 -*-
"""
注册 / 取消 Windows 计划任务：
让你每次登录 Windows 后自动扫描一次（即使本程序没开着也能记录）。
用法：
  python install_task.py         # 注册登录时自动扫描
  python install_task.py --uninstall   # 取消计划任务
"""

import sys
import os
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# 用当前正在运行的 Python 解释器（不写死路径，适配不同电脑/虚拟环境）
PYTHON = sys.executable
MONITOR = os.path.join(BASE_DIR, "monitor.py")

TASK_NAME = "CDiskMonitor-AutoScan"
# 老版本注册的是 DAILY 触发、任务名不同。换方案后必须把旧的清掉，
# 否则新旧两个任务同时存在，一天会被扫好几次。
LEGACY_TASK_NAMES = ["CDiskMonitor-DailyScan"]

# 最小间隔（小时）：一天开关机好几次时，距上次快照不足这么久就跳过本次。
# 只对自动扫描生效，手动双击 bat 不受影响。
MIN_GAP_HOURS = 6

# 登录后延迟多少秒再扫：避开刚进桌面时启动项、杀毒软件抢磁盘的高峰。
LOGON_DELAY_SECONDS = 60

# 打包成 exe 后没有 python 和 monitor.py，计划任务直接调 exe 自己带参数
FROZEN = bool(getattr(sys, "frozen", False))
if FROZEN:
    TASK_PROGRAM = '"%s" --once --min-gap %d' % (sys.executable, MIN_GAP_HOURS)
else:
    TASK_PROGRAM = '"%s" "%s" --once --min-gap %d' % (PYTHON, MONITOR, MIN_GAP_HOURS)


def _delay_arg(seconds):
    """schtasks 的 /DELAY 只认 mmmm:ss（分钟:秒）这种写法。"""
    minutes, secs = divmod(int(seconds), 60)
    return "%04d:%02d" % (minutes, secs)


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
    # 先把旧方案留下的任务删掉（不存在会失败，忽略即可）
    for old in LEGACY_TASK_NAMES:
        run(["schtasks", "/Delete", "/TN", old, "/F"])

    # 登录时触发，登录后延迟 1 分钟再跑，避开开机高峰
    code, out = run([
        "schtasks", "/Create", "/TN", TASK_NAME, "/TR", TASK_PROGRAM,
        "/SC", "ONLOGON", "/DELAY", _delay_arg(LOGON_DELAY_SECONDS), "/F",
    ])
    if code == 0:
        print("✓ 计划任务已注册成功 / Task registered.")
        print("  Windows 将在你每次登录后约 %d 分钟自动扫描一次 C 盘。"
              % (LOGON_DELAY_SECONDS // 60))
        print("  It will scan the C drive about %d min after each logon."
              % (LOGON_DELAY_SECONDS // 60))
        print("  距上次扫描不足 %d 小时的会自动跳过，所以一天最多记一份。"
              % MIN_GAP_HOURS)
        print("  Skipped if the last scan was less than %d h ago — at most one record a day."
              % MIN_GAP_HOURS)
        print("  即使本程序没开着，也会自动运行。/ Runs even if the app is closed.")
        print("  想立刻扫就双击「立即扫描一次」，手动扫描不受间隔限制。")
        print("  To scan right now, just double-click \"Scan Now\" — manual runs are never skipped.")
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
    removed, last_out, any_ok = [], "", False
    for name in [TASK_NAME] + LEGACY_TASK_NAMES:
        code, out = run(["schtasks", "/Delete", "/TN", name, "/F"])
        if code == 0:
            removed.append(name)
            any_ok = True
        else:
            last_out = out
    if any_ok:
        print("✓ 计划任务已取消 / Task removed.")
        for name in removed:
            print("  - %s" % name)
    else:
        print("✗ 取消失败（可能本就没注册）/ Removal failed (maybe not registered):")
        print(last_out)
    return 0 if any_ok else 1


if __name__ == "__main__":
    if "--uninstall" in sys.argv:
        sys.exit(uninstall())
    else:
        sys.exit(install())
