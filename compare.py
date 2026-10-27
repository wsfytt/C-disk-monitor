# -*- coding: utf-8 -*-
"""
对比任意两次扫描快照。
用法：
  python compare.py            # 列出所有历史快照
  python compare.py 1 3        # 对比第 1 次和第 3 次快照，生成报告并自动打开
  python compare.py --all      # 生成「相邻两次」的全部对比报告（1→2、2→3、3→4...）
  python compare.py --last     # 对比最新两次（等同默认行为）
"""

import sys
import os
import datetime

import config
import scanner
import reporter
from utils import open_report


def list_snapshots():
    """列出所有快照，返回 [(序号, 快照), ...]，序号从 1 开始。"""
    snaps = scanner.load_snapshots()
    print("历史扫描记录（共 %d 次）：" % len(snaps))
    print("-" * 55)
    for i, s in enumerate(snaps, 1):
        disk_used = scanner.human_size(s["disk_used"])
        disk_free = scanner.human_size(s["disk_free"])
        print("  %2d.  %s    已用 %s / 可用 %s" % (i, s["time"], disk_used, disk_free))
    print("-" * 55)
    print("用法示例：compare.py 1 3  （对比第 1 次和第 3 次）")
    return snaps


def compare(i1, i2, auto_open=True):
    """对比第 i1 次和第 i2 次快照（序号从 1 开始）。"""
    snaps = scanner.load_snapshots()
    if i1 < 1 or i2 < 1 or i1 > len(snaps) or i2 > len(snaps):
        print("错误：序号超出范围，共有 %d 次快照。" % len(snaps))
        return None
    prev, curr = snaps[i1 - 1], snaps[i2 - 1]
    txt, html, diff = reporter.generate_report(prev, curr)
    print("对比报告已生成：")
    print("  文本：%s" % txt)
    print("  网页：%s" % html)
    print("")
    print(reporter.render_text(diff))
    if auto_open and html:
        if open_report(html):
            print("\n已自动打开报告。")
    return html


def compare_all(auto_open=True):
    """生成所有「相邻两次」的对比报告。"""
    snaps = scanner.load_snapshots()
    if len(snaps) < 2:
        print("快照不足 2 次，无法对比。")
        return
    print("生成所有相邻快照的对比报告（共 %d 组）：" % (len(snaps) - 1))
    print("")
    htmls = []
    for i in range(len(snaps) - 1):
        prev, curr = snaps[i], snaps[i + 1]
        txt, html, diff = reporter.generate_report(prev, curr)
        htmls.append(html)
        change = diff["disk_used_change"]
        sign = "+" if change > 0 else ""
        print("  [%d→%d] %s → %s   空间变化 %s%s" % (
            i + 1, i + 2, prev["time"], curr["time"],
            sign, scanner.human_size(change)))
    print("")
    print("已生成 %d 份对比报告，保存在 reports 文件夹。" % len(htmls))
    if auto_open and htmls:
        if open_report(htmls[-1]):
            print("已自动打开最新一份。")
    return htmls


def main():
    args = sys.argv[1:]

    if not args:
        list_snapshots()
        return

    if args[0] == "--all":
        compare_all()
        return

    if args[0] == "--last":
        snaps = scanner.load_snapshots()
        if len(snaps) < 2:
            print("快照不足 2 次。")
            return
        compare(len(snaps) - 1, len(snaps))
        return

    # 两个数字参数：对比第 i1 次和第 i2 次
    if len(args) >= 2:
        try:
            i1 = int(args[0])
            i2 = int(args[1])
        except ValueError:
            print("参数错误：请用数字表示快照序号，如 compare.py 1 3")
            return
        compare(i1, i2)
        return

    print("参数错误。用法：")
    print("  compare.py            # 列出所有快照")
    print("  compare.py 1 3        # 对比第 1 次和第 3 次")
    print("  compare.py --all      # 生成所有相邻对比")
    print("  compare.py --last     # 对比最新两次")


if __name__ == "__main__":
    main()
