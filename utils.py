# -*- coding: utf-8 -*-
"""跨平台打开文件、日志等通用小工具。"""
import os
import logging
import subprocess

_logger = None


def setup_logging(log_dir):
    """初始化日志：同时输出到控制台和日志文件（旋转 5 份，每份 1MB）。
    常驻/计划任务模式下，出错信息也能落到文件里，方便事后排查。"""
    global _logger
    if _logger is not None:
        return _logger
    try:
        os.makedirs(log_dir, exist_ok=True)
    except OSError:
        log_dir = None

    _logger = logging.getLogger("cdm")
    _logger.setLevel(logging.INFO)
    _logger.propagate = False

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    if log_dir:
        try:
            from logging.handlers import RotatingFileHandler
            fh = RotatingFileHandler(
                os.path.join(log_dir, "monitor.log"),
                maxBytes=1024 * 1024, backupCount=5, encoding="utf-8")
            fh.setFormatter(fmt)
            _logger.addHandler(fh)
        except OSError:
            pass

    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    _logger.addHandler(sh)
    return _logger


def log():
    """返回全局 logger（未初始化时退化为 root logger，避免报错）。"""
    return _logger if _logger is not None else logging.getLogger("cdm")


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
