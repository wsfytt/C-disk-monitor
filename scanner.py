# -*- coding: utf-8 -*-
"""
扫描器：深度遍历 C 盘，计算每个文件夹大小，并识别所属软件/公司。

核心策略（一次遍历，避免重复计算）：
- 用一次显式栈 DFS 遍历整棵树（先收集目录树，再按路径深度倒序累加），不使用递归
- 沿途记录每个目录的 (路径, 大小)，同时识别软件/公司
- 跳过 Windows junction / 符号链接（reparse point），避免死循环
- 跳过系统关键目录（Windows、回收站等），这些用户不会去删
"""

import os
import time
import json
import datetime
from collections import defaultdict

import config

FILE_ATTRIBUTE_REPARSE_POINT = 0x400

# 快照格式版本：1 = 全量记录（旧版）；2 = 只记录 ≥ MIN_DIR_SIZE_TO_RECORD 的目录
SNAPSHOT_SCHEMA = 2

# 跳过这些目录（系统目录，用户不会也不应该手动删）
SKIP_DIRS = {
    "windows", "system volume information", "$recycle.bin",
    "$sysreset", "$winreagent", "recovery", "perflogs",
    "swapfile.sys", "pagefile.sys", "hiberfil.sys",
}

# 容器目录：它们只是「装东西的盒子」，内容会被子目录识别，
# 不应作为独立的对比项出现在报告里（否则报告里会有一堆 AppData/Users 这种没意义的条目）。
CONTAINER_DIRS = {
    "users", "program files", "program files (x86)", "programdata",
    "appdata", "local", "locallow", "roaming", "microsoft", "packages",
    "user data", "documents and settings",
}


def human_size(n):
    """字节数转成人类可读大小。"""
    if n is None:
        return "?"
    n = float(n)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if n < 1024.0 or unit == "TB":
            if unit == "B":
                return "%d B" % int(n)
            return "%.2f %s" % (n, unit)
        n /= 1024.0


def _is_reparse(entry):
    """判断 DirEntry 是否为 junction/符号链接。"""
    try:
        st = entry.stat(follow_symlinks=False)
        return bool(st.st_file_attributes & FILE_ATTRIBUTE_REPARSE_POINT)
    except (AttributeError, OSError):
        try:
            return entry.is_symlink()
        except OSError:
            return False


def scan(progress_cb=None):
    """
    深度扫描 C 盘，返回快照。
    一次遍历整棵树，自底向上累加大小，沿途记录每个目录。

    返回：
    {
      "time", "disk_total", "disk_free", "disk_used",
      "dirs": [ {path, name, size, level, software_name?, company?, tip?}, ... ],
      "top_software": [ {software_name, company, size, tip}, ... ]
    }
    """
    drive = config.MONITOR_DRIVE
    root = drive + "\\"

    try:
        import shutil
        du = shutil.disk_usage(root)
        disk_total = du.total
        disk_free = du.free
    except Exception:
        disk_total = 0
        disk_free = 0

    dirs = []

    t0 = time.time()          # 计时必须从遍历开始，否则 scan_seconds 只算了去重那一段
    # 显式栈遍历（避免递归深度风险），第一遍 DFS 收集节点，第二遍按深度倒序累加。
    nodes = {}   # path -> {"level", "own", "children": [(name, path), ...], "total"}
    order = []
    stack = [(root, 0)]
    while stack:
        path, lv = stack.pop()
        node = {"level": lv, "own": 0, "children": [], "total": 0, "name": os.path.basename(path)}
        nodes[path] = node
        order.append(path)
        try:
            entries = os.scandir(path)          # 用生成器，不 list()
        except (PermissionError, OSError, FileNotFoundError):
            continue
        for entry in entries:
            try:
                if entry.is_dir(follow_symlinks=False):
                    if _is_reparse(entry):
                        continue                 # 跳过 junction / 符号链接
                    if entry.name.lower() in SKIP_DIRS:
                        continue                 # 跳过系统目录
                    node["children"].append((entry.name, entry.path))
                    stack.append((entry.path, lv + 1))
                elif entry.is_file(follow_symlinks=False):
                    node["own"] += entry.stat(follow_symlinks=False).st_size
            except OSError:
                pass

    # 按深度倒序累加：子目录一定比父目录先算完
    for path in sorted(order, key=lambda p: -p.count("\\")):
        node = nodes[path]
        node["total"] = node["own"] + sum(
            nodes[c[1]]["total"] for c in node["children"] if c[1] in nodes)

    # 生成记录（顺序不重要，后面会 sort）
    for path in order:
        node = nodes[path]
        if node["level"] == 0 or node["total"] == 0:
            continue
        sub_size = node["total"]
        if sub_size < config.MIN_DIR_SIZE_TO_RECORD:          # 只按大小过滤，绝不按深度
            continue
        name = node["name"]
        if name.lower() in CONTAINER_DIRS:
            continue
        if os.path.basename(os.path.dirname(path)).lower() == "users":
            continue
        record = {"path": path, "name": name, "size": sub_size, "level": node["level"]}
        info = config.identify(path)
        if info:
            record["software_name"] = info["name"]
            record["software_name_en"] = info.get("name_en", info["name"])
            record["company"] = info["company"]
            record["tip"] = info["tip"]
            record["tip_en"] = info.get("tip_en", info["tip"])
        dirs.append(record)
        if progress_cb:
            progress_cb(path, sub_size)

    # 按路径深度排序（浅的在前），这样父目录先处理
    dirs.sort(key=lambda x: (x["path"].count("\\"), -x["size"]))

    # ============ 去重 + 拆分逻辑 ============
    # 目标：逐文件夹列出，不做「按公司合并」。
    # 规则：
    #   1. 同一软件的父子目录：只保留最顶层（避免 Edge 下 EdgeCore/Application 重复算）。
    #   2. 笼统目录（公司名/通用词）如果下面有「更具体的软件」子目录，就拆开：
    #      笼统目录本身不列，改列它的具体子目录。
    #   3. 未识别目录：被某个已识别目录覆盖的去掉。

    # 笼统词：这类目录只是"容器"，下面往往藏着多个具体软件，需要拆开
    GENERIC_NAMES = {"腾讯系软件目录", "缓存目录", "Edge 浏览器", "Adobe 系列软件",
                     "Google 目录", "Microsoft Office", "NI 软件", "安装包缓存",
                     "公共文件目录", "Google Chrome 浏览器", "Firefox 浏览器"}

    identified = [d for d in dirs if "software_name" in d]
    path_map = {d["path"]: d for d in dirs}

    # 第一遍：找「同一软件」的父子重复。
    # 如果一个已识别目录，其某个祖先也被识别为同一软件，则该目录是重复的。
    covered = set()

    for d in identified:
        p = d["path"]
        sw = d["software_name"]
        parent = os.path.dirname(p)
        while parent != os.path.dirname(parent):  # 到根目录（dirname 不再变）即停
            pd = path_map.get(parent)
            if pd and "software_name" in pd:
                if pd["software_name"] == sw:
                    covered.add(p)  # 同软件祖先存在 → 重复
                # 无论同不同软件，找到最近的已识别祖先后就停止
                break
            parent = os.path.dirname(parent)

    # 第二遍：笼统目录拆分。若笼统目录下面有「被保留的不同具体软件」，笼统目录本身去掉。
    # 笼统目录：如果它有任何「被保留的不同软件子目录」，就拆开（去掉笼统目录本身）
    for d in identified:
        if d["path"] in covered:
            continue
        if d["software_name"] in GENERIC_NAMES:
            prefix = d["path"] + "\\"
            has_specific = False
            for d2 in identified:
                if d2["path"] in covered:
                    continue
                if d2["path"] == d["path"]:
                    continue
                if not d2["path"].startswith(prefix):
                    continue
                # d2 是 d 的后代，且是不同软件
                if d2["software_name"] != d["software_name"]:
                    has_specific = True
                    break
            if has_specific:
                covered.add(d["path"])

    # 组装最终列表
    final_dirs = []
    keep_paths = set()
    for d in identified:
        if d["path"] not in covered:
            keep_paths.add(d["path"])

    for d in dirs:
        if d["path"] in covered:
            continue
        if "software_name" in d:
            final_dirs.append(d)
        else:
            # 未识别目录：若其祖先是被保留的已识别目录，则去掉（已被覆盖）
            parent = os.path.dirname(d["path"])
            under = False
            while parent != os.path.dirname(parent):  # 到根即停
                if parent in keep_paths:
                    under = True
                    break
                parent = os.path.dirname(parent)
            if not under:
                final_dirs.append(d)

    # 每个已识别目录独立计数（不合并），同时统计 top_software 供概览用
    software_agg = defaultdict(lambda: {"size": 0, "company": "", "tip": ""})
    for d in final_dirs:
        if "software_name" in d:
            key = d["software_name"]
            software_agg[key]["size"] += d["size"]
            software_agg[key]["company"] = d.get("company", "")
            software_agg[key]["tip"] = d.get("tip", "")

    top_software = []
    for name, info in software_agg.items():
        top_software.append({
            "software_name": name,
            "company": info["company"],
            "size": info["size"],
            "tip": info["tip"],
        })
    top_software.sort(key=lambda x: -x["size"])
    final_dirs.sort(key=lambda x: -x["size"])

    snapshot = {
        "time": datetime.datetime.now().isoformat(timespec="seconds"),
        "scan_seconds": round(time.time() - t0, 1),
        "disk_total": disk_total,
        "disk_free": disk_free,
        "disk_used": disk_total - disk_free,
        "dirs": final_dirs,
        "top_software": top_software,
    }
    return snapshot


def save_snapshot(snapshot):
    """把快照存到 data 目录，文件名带时间戳。"""
    os.makedirs(config.DATA_DIR, exist_ok=True)
    snapshot["schema"] = SNAPSHOT_SCHEMA
    snapshot["min_size"] = config.MIN_DIR_SIZE_TO_RECORD
    # 记录扫描时生效的识别库指纹，便于以后追溯「这次的名字是按哪份库认的」。
    # 旧快照没有这个字段，读的时候按缺失处理即可。
    snapshot["db"] = config.db_info()
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(config.DATA_DIR, "snapshot_%s.json" % ts)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)
    return path


def _normalize(snap):
    """把任意版本的快照在内存里对齐到当前记录口径；磁盘文件不动。"""
    cur = config.MIN_DIR_SIZE_TO_RECORD
    # 取两者较大者：万一以后把阈值调小，旧快照仍按它自己当时的阈值对齐，避免新旧口径错位
    thr = max(cur, snap.get("min_size", 0))
    if snap.get("schema", 1) >= SNAPSHOT_SCHEMA and snap.get("min_size", 0) >= cur:
        return snap                       # 已是新口径，不必动
    snap = dict(snap)
    snap["dirs"] = [d for d in snap["dirs"] if d.get("size", 0) >= thr]
    snap["min_size"] = thr
    snap["schema"] = SNAPSHOT_SCHEMA
    return snap


def _fill_en_fields(snap):
    """给旧快照里缺失的英文字段（software_name_en / tip_en）按当前识别库补全。
    这样历史快照也能在英文模式下正确显示软件名和建议。磁盘文件不改。"""
    snap = dict(snap)
    dirs = []
    changed = False
    for d in snap["dirs"]:
        d = dict(d)
        sw = d.get("software_name")
        if sw and not d.get("software_name_en"):
            # 按中文名反查识别库，补英文名和英文建议
            for info in config.SOFTWARE_DB.values():
                if info.get("name") == sw:
                    d["software_name_en"] = info.get("name_en", sw)
                    d["tip_en"] = info.get("tip_en", d.get("tip", ""))
                    changed = True
                    break
        dirs.append(d)
    snap["dirs"] = dirs
    return snap


def load_snapshots():
    """读取所有历史快照，按时间排序返回 [快照, ...]（读时归一化，磁盘文件不动）。"""
    snapshots = []
    broken = 0
    if not os.path.isdir(config.DATA_DIR):
        return snapshots
    for fn in sorted(os.listdir(config.DATA_DIR)):
        if fn.startswith("snapshot_") and fn.endswith(".json"):
            p = os.path.join(config.DATA_DIR, fn)
            try:
                with open(p, "r", encoding="utf-8") as f:
                    snap = json.load(f)
            except (json.JSONDecodeError, OSError):
                continue
            if not isinstance(snap, dict) or "dirs" not in snap:
                broken += 1
                continue
            snapshots.append(_fill_en_fields(_normalize(snap)))
    if broken:
        print("提示：%d 个快照文件无法解析，已跳过（文件未删除）：%s" % (broken, config.DATA_DIR))
    return snapshots


def latest_snapshot():
    snaps = load_snapshots()
    return snaps[-1] if snaps else None


if __name__ == "__main__":
    print("开始深度扫描 C 盘（通常 15~60 秒，请耐心等待）...")
    t0 = time.time()
    snap = scan()
    print("扫描完成，耗时 %.1f 秒" % (time.time() - t0))
    print("C 盘总容量：%s" % human_size(snap["disk_total"]))
    print("C 盘可用：  %s" % human_size(snap["disk_free"]))
    print("C 盘已用：  %s" % human_size(snap["disk_used"]))
    print("\n--- 占用最大的软件/公司（前 20）---")
    for s in snap["top_software"][:20]:
        print("  %-30s %10s  (%s)" % (s["software_name"], human_size(s["size"]), s["company"]))
    p = save_snapshot(snap)
    print("\n快照已保存：%s" % p)
