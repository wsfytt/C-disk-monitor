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
from utils import open_report, setup_logging, log


def T(k):
    return i18n.t(k, config.LANG)


def do_scan():
    """执行一次扫描并保存快照，打印结果（同时写日志）。"""
    log().info(T("start_scan"))
    snap = scanner.scan()
    path = scanner.save_snapshot(snap)
    log().info("%s: %s" % (T("scan_done"), path))
    log().info("%s %s / %s %s" % (
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


def export_db():
    """把当前使用的识别库导出到 exe（或脚本）同目录，方便用户直接编辑。

    打包成 exe 后识别库被封在 exe 内，用户改不了；导出到同目录后，程序会优先加载它。
    """
    import shutil
    src = config.SOFTWARE_DB_FILE
    dst = config.EXTERNAL_DB_PATH
    if not src or not os.path.isfile(src):
        log().error("找不到内置识别库，无法导出。" if config.LANG == "zh"
                    else "Built-in DB not found, cannot export.")
        return 1
    if os.path.abspath(src) == os.path.abspath(dst):
        log().info(("识别库已经是外部文件，直接编辑即可：%s" if config.LANG == "zh"
                    else "DB is already an external file, just edit it: %s") % dst)
        return 0
    if os.path.exists(dst) and "--force" not in sys.argv:
        log().warning(("目标已存在，未覆盖：%s" if config.LANG == "zh"
                       else "Target exists, not overwritten: %s") % dst)
        log().warning("如需覆盖请加 --force / add --force to overwrite")
        return 1
    try:
        shutil.copyfile(src, dst)
    except OSError as e:
        log().error(("导出失败：%s" if config.LANG == "zh" else "Export failed: %s") % e)
        return 1
    log().info(("已导出识别库到：%s" if config.LANG == "zh" else "DB exported to: %s") % dst)
    log().info("用文本编辑器或你的 AI 修改这个文件即可，改完直接运行，程序会优先用它。"
               if config.LANG == "zh" else
               "Edit it with any text editor or your AI; the app will prefer it on next run.")
    return 0


def main():
    once = "--once" in sys.argv
    auto_open = "--open" in sys.argv
    report_only = "--report" in sys.argv

    # 初始化日志（写到数据目录，常驻/计划任务出错也能留痕）
    setup_logging(config.DATA_ROOT)
    # 按指纹把当前识别库另存一份到 data/dbs/，以后能查回「当时用的是哪份库」。
    # 同指纹已存在会自动跳过；任何失败都不影响主流程。
    config.archive_db()

    # 计划任务注册 / 取消（打包成 exe 后，用同一个 exe 带参数即可完成，无需单独脚本）
    if "--install-task" in sys.argv or "--uninstall-task" in sys.argv:
        import install_task
        sys.exit(install_task.uninstall() if "--uninstall-task" in sys.argv
                 else install_task.install())

    # 把「当前正在用的识别库」导出到 exe 同目录（或指定路径），供用户用文本编辑器/AI 修改。
    # 打包成 exe 后识别库被封在 exe 里，导出后放到 exe 旁边即自动优先加载。
    if "--export-db" in sys.argv:
        sys.exit(export_db())

    # 「只查看历史对比」模式：不扫描，直接读已有快照生成报告页并打开。
    if report_only:
        snaps = scanner.load_snapshots()
        if len(snaps) >= 2:
            prev, curr = snaps[-2], snaps[-1]
            txt, html, diff = reporter.generate_report(prev, curr)
            open_report(html)
            log().info(("已打开报告（含历史对比标签）：%s" if config.LANG == "zh" else "Opened report (with history tab): %s") % html)
        else:
            log().warning(("快照不足 2 次，暂无历史对比可看。" if config.LANG == "zh"
                           else "Less than 2 snapshots, nothing to compare."))
        return

    log().info(T("banner_start"))
    log().info("%s: %s" % (T("monitor_drive"), config.MONITOR_DRIVE))
    log().info("%s: %s+" % (T("record_threshold"), scanner.human_size(config.MIN_DIR_SIZE_TO_RECORD)))
    log().info("%s: %s" % (T("record_freq"), ("每天一次" if config.LANG == "zh" else "once a day")))
    log().info("%s: %s" % (T("data_dir"), config.DATA_DIR))
    log().info("%s: %s" % (T("report_dir"), config.REPORT_DIR))

    if once:
        do_scan()
        maybe_report(auto_open=auto_open)
        log().info(T("once_done"))
        return

    # 常驻模式
    log().info("进入常驻监视模式（按 Ctrl+C 退出）。" if config.LANG == "zh" else "Entering monitor mode (Ctrl+C to quit).")
    while True:
        try:
            do_scan()
            maybe_report(auto_open=False)  # 后台定时不弹窗
            log().info(("下次记录时间：%s（约 %s 小时后）" if config.LANG == "zh" else "Next record: %s (~%s hours later)") % (
                (datetime.datetime.now() + datetime.timedelta(seconds=config.RECORD_INTERVAL_SECONDS)).strftime("%Y-%m-%d %H:%M:%S"),
                config.RECORD_INTERVAL_SECONDS // 3600))
            time.sleep(config.RECORD_INTERVAL_SECONDS)
        except KeyboardInterrupt:
            log().info("收到退出信号，程序结束。" if config.LANG == "zh" else "Exit signal received, stopping.")
            break
        except Exception as e:
            log().exception(("出错：%s" if config.LANG == "zh" else "Error: %s") % e)
            log().info("1 分钟后重试..." if config.LANG == "zh" else "Retrying in 1 minute...")
            time.sleep(60)


if __name__ == "__main__":
    main()
