# -*- coding: utf-8 -*-
"""
主程序：C 盘空间监视器（后台常驻）
- 启动后立即记录第一次快照
- 之后每天自动记录一次快照
- 每次有两次以上快照时，自动生成对比报告
用法：
  python monitor.py           # 前台运行，Ctrl+C 退出
  python monitor.py --once    # 只扫描一次并保存快照，然后退出
  pythonw monitor.py          # Windows 下后台无窗口运行
"""

import sys
import time
import datetime
import os

import config
import scanner
import reporter
import overview
import i18n
from utils import open_report


def T(k):
    return i18n.t(k, config.LANG)


def do_scan():
    """执行一次扫描并保存快照，打印结果。"""
    print("[%s] %s" % (datetime.datetime.now().strftime("%H:%M:%S"), T("start_scan")))
    snap = scanner.scan()
    path = scanner.save_snapshot(snap)
    print("[%s] %s: %s" % (
        datetime.datetime.now().strftime("%H:%M:%S"), T("scan_done"), path))
    print("       %s %s / %s %s" % (
        T("used_free"), scanner.human_size(snap["disk_used"]),
        ("可用" if config.LANG == "zh" else "free"), scanner.human_size(snap["disk_free"])))
    return snap


def maybe_report(auto_open=False):
    """
    生成报告。
    - 有两次以上快照：生成对比报告
    - 只有一次快照：生成「占用盘点」报告
    返回报告 html 路径（供自动打开）。
    """
    snaps = scanner.load_snapshots()
    html_path = None
    if len(snaps) >= 2:
        prev, curr = snaps[-2], snaps[-1]
        txt, html, diff = reporter.generate_report(prev, curr)
        html_path = html
        print("       %s:" % T("gen_compare"))
        print("         %s: %s" % (T("text"), txt))
        print("         %s: %s" % (T("web"), html))
        change = diff["disk_used_change"]
        if change > 0:
            print("       %s %s" % (T("space_decrease"), scanner.human_size(change)))
            top = diff["grew"][0] if diff["grew"] else None
            if top:
                tag = top["software_name"] if top["software_name"] else top["name"]
                print("       %s: %s %s %s" % (T("top_cause"), tag, T("grew"), scanner.human_size(top["change"])))
        elif change < 0:
            print("       %s %s（清理见效）" % (T("space_increase"), scanner.human_size(-change)))
        else:
            print("       %s" % T("space_nochange"))
    else:
        # 只有一次快照，生成占用盘点报告
        print("       %s" % T("overview_gen"))
        snap = snaps[-1]
        os.makedirs(config.REPORT_DIR, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        html_path = os.path.join(config.REPORT_DIR, "overview_%s.html" % ts)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(overview.render_overview_html(snap))
        print("         %s" % html_path)

    if auto_open and html_path:
        if open_report(html_path):
            print("       %s: %s" % (T("auto_open"), html_path))
        else:
            print("       %s: %s" % (T("auto_open_fail"), html_path))
    return html_path


def main():
    once = "--once" in sys.argv
    auto_open = "--open" in sys.argv
    report_only = "--report" in sys.argv

    # 「只查看历史对比」模式：不扫描，直接读已有快照生成报告页并打开。
    if report_only:
        snaps = scanner.load_snapshots()
        if len(snaps) >= 2:
            prev, curr = snaps[-2], snaps[-1]
            txt, html, diff = reporter.generate_report(prev, curr)
            open_report(html)
            print(("已打开报告（含历史对比标签）：%s" if config.LANG == "zh" else "Opened report (with history tab): %s") % html)
        else:
            print(("快照不足 2 次，暂无历史对比可看。请先运行「立即扫描一次」。" if config.LANG == "zh"
                   else "Less than 2 snapshots. Run a scan first."))
        return

    print("=" * 60)
    print(T("banner_start"))
    print("%s: %s" % (T("monitor_drive"), config.MONITOR_DRIVE))
    print("%s: %s+" % (T("record_threshold"), scanner.human_size(config.MIN_DIR_SIZE_TO_RECORD)))
    print("%s: %s" % (T("record_freq"), ("每天一次" if config.LANG == "zh" else "once a day")))
    print("%s: %s" % (T("data_dir"), config.DATA_DIR))
    print("%s: %s" % (T("report_dir"), config.REPORT_DIR))
    print("=" * 60)

    if once:
        do_scan()
        maybe_report(auto_open=auto_open)
        print(T("once_done"))
        return

    # 常驻模式
    print("进入常驻监视模式（按 Ctrl+C 退出）。" if config.LANG == "zh" else "Entering monitor mode (Ctrl+C to quit).")
    print("")
    while True:
        try:
            do_scan()
            maybe_report(auto_open=False)  # 后台定时不弹窗
            print("")
            print(("下次记录时间：%s（约 %s 小时后）" if config.LANG == "zh" else "Next record: %s (~%s hours later)") % (
                (datetime.datetime.now() + datetime.timedelta(seconds=config.RECORD_INTERVAL_SECONDS)).strftime("%Y-%m-%d %H:%M:%S"),
                config.RECORD_INTERVAL_SECONDS // 3600))
            print("-" * 60)
            time.sleep(config.RECORD_INTERVAL_SECONDS)
        except KeyboardInterrupt:
            print("\n收到退出信号，程序结束。" if config.LANG == "zh" else "\nExit signal received, stopping.")
            break
        except Exception as e:
            print(("出错：%s" if config.LANG == "zh" else "Error: %s") % e)
            print("1 分钟后重试...")
            time.sleep(60)


if __name__ == "__main__":
    main()
