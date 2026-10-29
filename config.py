# -*- coding: utf-8 -*-
"""
配置：C 盘空间监视器
包含「软件/公司文件夹识别库」和各项可调参数。
"""

import os
import sys
import json
import hashlib

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


# ============ 识别库指纹（用于「这份报告依据哪份库」的追溯）============
# 指纹是什么：把库内容规范化（固定键序、去掉多余空格）后算 sha256，取前 12 位。
# 内容一样 => 指纹一样；改一个字 => 指纹变。它只是个「身份证号」，
# 真正的库内容会按指纹另存一份到 data/dbs/，两者配合才能查回当时的原样。
#
# 匹配规则版本：识别逻辑一改就要 +1，否则会出现「库没变、结果却变了」无法解释。
#   1 = 裸子串匹配（早期版本，有 acknowledge 命 edge 之类误判）
#   2 = 整词匹配 + 驼峰边界（当前）
MATCHER_VERSION = 2


def _db_fingerprint(db):
    """识别库内容指纹：规范化 JSON 后取 sha256 前 12 位。失败返回空串。"""
    try:
        raw = json.dumps(db, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"))
    except (TypeError, ValueError):
        return ""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


def _db_source(path):
    """库的来源：env（环境变量指定）/ external（exe 同目录）/ bundled（内置）/ none。"""
    if not path:
        return "none"
    env = os.environ.get("CDM_DB_FILE", "").strip()
    if env and os.path.abspath(path) == os.path.abspath(env):
        return "env"
    # 只有打包成 exe 时，「exe 同目录」才是独立于内置库的位置；
    # 源码运行时两者是同一个路径，应算内置库。
    if getattr(sys, "frozen", False) and \
            os.path.abspath(path) == os.path.abspath(EXTERNAL_DB_PATH):
        return "external"
    return "bundled"


SOFTWARE_DB_ID = _db_fingerprint(_db) if _db else ""
SOFTWARE_DB_COUNT = len(SOFTWARE_DB)
SOFTWARE_DB_SOURCE = _db_source(SOFTWARE_DB_FILE)


def db_info():
    """当前生效识别库的指纹信息。写进快照，并在报告里显示。"""
    return {
        "id": SOFTWARE_DB_ID,
        "count": SOFTWARE_DB_COUNT,
        "matcher": MATCHER_VERSION,
        "source": SOFTWARE_DB_SOURCE,
    }


def archive_db(data_dir=None):
    """按指纹把当前识别库另存一份到 data/dbs/，供以后回溯「当时是哪份库」。

    同指纹已存在则跳过；任何异常都静默（追溯功能不能影响主流程）。
    返回存档路径，未存档返回 None。
    """
    if not _db or not SOFTWARE_DB_ID:
        return None
    try:
        d = os.path.join(data_dir or DATA_DIR, "dbs")
        os.makedirs(d, exist_ok=True)
        path = os.path.join(d, "db_%s.json" % SOFTWARE_DB_ID)
        if os.path.exists(path):
            return path
        with open(path, "w", encoding="utf-8") as f:
            json.dump(_db, f, ensure_ascii=False, sort_keys=True, indent=2)
        return path
    except OSError:
        return None


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


def _match(path):
    """内部：返回 (命中的库条目, 命中的键)，未命中返回 (None, None)。

    命中规则：所有「以词出现」的键里取最长的那条（越具体越优先）。
    """
    path_lower = path.lower()
    best = None
    best_key = None
    best_len = 0
    for key, info in SOFTWARE_DB.items():
        if _is_word_hit(key, path_lower, path) and len(key) > best_len:
            best_len = len(key)
            best = info
            best_key = key
    return best, best_key


def identify(path):
    """根据文件夹路径识别所属软件/公司。参数传原始大小写，内部统一转小写匹配。

    返回 {"name", "company", "tip", ...} 或 None。匹配越长的键越优先。
    """
    return _match(path)[0]


def match_key(path):
    """返回路径命中的识别库键名（未命中返回 None）。

    报告页要「按当前库重新解释历史快照」，但网页端跑不了 Python 的匹配逻辑，
    所以在生成报告时用这个函数把「路径 → 键」算好内嵌进去，网页只做查表。
    """
    return _match(path)[1]


def resolve(path):
    """把一条路径解析成报告要显示的四元组；未识别时各字段为空。

    返回 {"key", "name", "name_en", "company", "tip", "tip_en", "level"}。
    """
    info, key = _match(path)
    if not info:
        return {"key": None, "name": "", "name_en": "", "company": "",
                "tip": "", "tip_en": "", "level": "unknown"}
    name = info.get("name", "")
    return {
        "key": key,
        "name": name,
        "name_en": info.get("name_en", ""),
        "company": info.get("company", ""),
        "tip": info.get("tip", ""),
        "tip_en": info.get("tip_en", ""),
        "level": deletion_level(name),
    }


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
