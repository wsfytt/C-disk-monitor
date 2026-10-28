# -*- coding: utf-8 -*-
"""
配置：C 盘空间监视器
包含「软件/公司文件夹识别库」和各项可调参数。
"""

import os
import sys
import json

# ============ 要监视的盘符 ============
MONITOR_DRIVE = "C:"

# ============ 语言 ============
# 控制命令行提示和 .txt 文本报告的语言："zh"（中文，默认）/ "en"（英文）。
# 网页报告自带「中文 / English」切换按钮，不受此开关影响。
LANG = "zh"

# ============ 记录范围（不影响扫描耗时）============
# 遍历始终是全深度（否则父目录大小会算不准）。
# 这一项只决定「哪些目录会被写进快照和报告」。
# 注意：不要按目录深度限制记录范围，理由见开源改造方案 T2 的三行实测表：
# AppData 深处的 xwechat、NVIDIA、Code Cache 若按深度过滤会被静默丢掉，报告看着正常但内容是假的。
MIN_DIR_SIZE_TO_RECORD = 5 * 1024 * 1024   # 5 MB

# ============ 记录频率（秒）============
# 每天记录一次
RECORD_INTERVAL_SECONDS = 24 * 60 * 60  # 86400 秒 = 1 天

# ============ 快照与报告存放位置 ============
# 默认存放在用户目录 %LOCALAPPDATA%\c_disk_monitor\ 下（Windows），
# 而不是项目目录里——这样 clone/分享代码时，个人磁盘数据不会混进仓库，
# 也不会污染项目所在的目录。
# 如需自定义，可设置环境变量 CDM_DATA_DIR 指向你的目录（优先于默认值）。
# 资源目录：源码运行时是脚本所在目录；PyInstaller 打包成 exe 后是解包临时目录（sys._MEIPASS）。
# 注意：数据目录（DATA_ROOT）不复用这个变量，始终指向用户 AppData，避免每次运行换地方。
if getattr(sys, "frozen", False):
    BASE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(sys.executable)))
    EXE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    EXE_DIR = BASE_DIR

_env_data_root = os.environ.get("CDM_DATA_DIR", "").strip()
if _env_data_root:
    DATA_ROOT = _env_data_root
else:
    _user_root = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~/.local/share")
    DATA_ROOT = os.path.join(_user_root, "c_disk_monitor")

DATA_DIR = os.path.join(DATA_ROOT, "data")
REPORT_DIR = os.path.join(DATA_ROOT, "reports")

# ============ 软件 / 公司文件夹识别库 ============
# 识别库已独立到 software_db.json（纯数据、无代码，方便 AI 或人工直接增改）。
# 识别内容仅供参考，实际以软件内显示为准。
#
# 加载优先级（越靠前越优先）：
#   1. 环境变量 CDM_DB_FILE 指定的文件
#   2. exe 同目录下的 software_db.json（打包版用户自己放一份即可覆盖内置库）
#   3. 内置库（源码目录 / exe 内打包的那份）
# 解析失败会自动跳到下一个候选，不会因为用户改坏了 JSON 就退化成空库。
BUILTIN_DB_PATH = os.path.join(BASE_DIR, "software_db.json")
EXTERNAL_DB_PATH = os.path.join(EXE_DIR, "software_db.json")


def _db_candidates():
    cands = []
    env = os.environ.get("CDM_DB_FILE", "").strip()
    if env:
        cands.append(env)
    # 打包版：exe 同目录的库优先于内置库（用户可改）
    if getattr(sys, "frozen", False):
        cands.append(EXTERNAL_DB_PATH)
    cands.append(BUILTIN_DB_PATH)
    return cands


def _load_db():
    """按优先级找第一个能解析的识别库，返回 (数据, 路径)。"""
    for path in _db_candidates():
        try:
            with open(path, "r", encoding="utf-8") as f:
                db = json.load(f)
        except (OSError, ValueError):
            continue
        if isinstance(db, dict) and "software_db" in db:
            return db, path
    return None, None


_db, SOFTWARE_DB_FILE = _load_db()
if _db:
    SOFTWARE_DB = _db.get("software_db", {})
    DELETION_LEVELS = {k: set(v) for k, v in _db.get("deletion_levels", {}).items()}
else:
    # 三个候选都读不出来（文件缺失或全被改坏）：退化为空库，程序仍能运行
    SOFTWARE_DB = {}
    DELETION_LEVELS = {"safe": set(), "cleanup": set(), "caution": set()}


def _is_word_hit(key, path_lower, path_orig):
    """key 是否以「词」的形式出现在路径里。

    两侧必须满足其一：路径边界 / 非字母数字字符 / 原始路径该位置是大写字母（驼峰）。
    path_lower 与 path_orig 等长且位置一一对应。
    """
    start = 0
    while True:
        i = path_lower.find(key, start)
        if i < 0:
            return False
        j = i + len(key)
        left_ok = (i == 0
                   or not path_lower[i - 1].isalnum()
                   or path_orig[i].isupper())
        right_ok = (j == len(path_lower)
                    or not path_lower[j].isalnum()
                    or path_orig[j].isupper())
        if left_ok and right_ok:
            return True
        start = i + 1


def identify(path):
    """根据文件夹路径识别所属软件/公司。参数传原始大小写，内部统一转小写匹配。

    返回 {"name", "company", "tip", ...} 或 None。匹配越长的键越优先。
    """
    path_lower = path.lower()
    best = None
    best_len = 0
    for key, info in SOFTWARE_DB.items():
        if _is_word_hit(key, path_lower, path) and len(key) > best_len:
            best_len = len(key)
            best = info
    return best


def deletion_level(software_name):
    """根据软件名返回删除建议等级："safe" / "cleanup" / "caution" / "unknown"。
    支持中文名或英文名（英文名会先映射回中文名再查）。"""
    name = _NAME_EN_TO_ZH.get(software_name, software_name)
    for level, names in DELETION_LEVELS.items():
        if name in names:
            return level
    return "unknown"


# 英文名 -> 中文名 映射（用于把报告里的英文软件名映射回删除等级）
_NAME_EN_TO_ZH = {
    info.get("name_en"): info["name"]
    for info in SOFTWARE_DB.values() if info.get("name_en")
}


LEVEL_LABEL = {
    "safe": "✅ 可放心删",
    "cleanup": "🟡 建议清理",
    "caution": "🔴 谨慎（确认后再删）",
    "unknown": "— 自行判断",
}

# 英文版删除等级标签（切英文时使用）
LEVEL_LABEL_EN = {
    "safe": "✅ Safe to delete",
    "cleanup": "🟡 Cleanup",
    "caution": "🔴 Caution (confirm first)",
    "unknown": "— Use your judgment",
}
