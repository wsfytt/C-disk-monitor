# -*- coding: utf-8 -*-
"""跨平台打开文件的小工具。"""
import os
import subprocess


def open_report(path):
    """用系统默认程序打开文件，失败时静默返回 False。"""
    try:
        if os.name == "nt":
            os.startfile(path)  # type: ignore[attr-defined]
        else:
            subprocess.Popen(["xdg-open", path])
        return True
    except Exception:
        return False
