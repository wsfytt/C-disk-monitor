# -*- coding: utf-8 -*-
"""
语言包：中英文对照。供网页报告（JS 动态切换）和命令行/txt 报告（config.LANG 控制）使用。
默认中文（zh），可切英文（en）。
"""

# 网页里固定界面文字的中英对照表（key -> {zh, en}）
UI = {
    "report_title": {"zh": "C 盘空间变化报告", "en": "C Drive Space Change Report"},
    "prev_label": {"zh": "上次记录", "en": "Previous"},
    "curr_label": {"zh": "本次记录", "en": "Current"},
    "used_label": {"zh": "本次已用", "en": "Used now"},
    "free_label": {"zh": "本次可用", "en": "Free now"},
    "change_label": {"zh": "空间变化", "en": "Change"},
    "tab_this": {"zh": "本次对比", "en": "This Compare"},
    "tab_history": {"zh": "历史对比", "en": "History"},
    "grew_title": {"zh": "变大的文件夹（空间减少的元凶，逐条）", "en": "Folders that grew (space hogs, per folder)"},
    "shrank_title": {"zh": "变小的文件夹（这段时间释放的空间，按减少量排序）", "en": "Folders that shrank (space freed, sorted by decrease)"},
    "col_no": {"zh": "#", "en": "#"},
    "col_path": {"zh": "文件夹路径", "en": "Path"},
    "col_what": {"zh": "是什么", "en": "What it is"},
    "col_grew": {"zh": "增长量", "en": "Grew"},
    "col_shrank": {"zh": "减少量", "en": "Shrank"},
    "col_prev": {"zh": "之前", "en": "Before"},
    "col_curr": {"zh": "现在", "en": "Now"},
    "col_level": {"zh": "删除建议", "en": "Delete?"},
    "col_tip": {"zh": "说明", "en": "Note"},
    "no_grew": {"zh": "没有检测到明显变大的文件夹。", "en": "No folders grew noticeably."},
    "no_shrank": {"zh": "没有检测到被清理的文件夹。", "en": "No folders were cleaned."},
    "history_title": {"zh": "历史对比", "en": "History Compare"},
    "history_sub": {"zh": "点选两个快照（先后顺序 = 时间顺序），下方自动显示对比结果", "en": "Click two snapshots (order = time order) to compare"},
    "history_hint": {"zh": "请选择两次扫描进行对比（点击两次）。", "en": "Select two scans to compare (click twice)."},
    "result_title": {"zh": "对比结果", "en": "Result"},
    "not_selected": {"zh": "尚未选择两次扫描。", "en": "No two scans selected yet."},
    "space_decrease": {"zh": "这段时间 C 盘空间减少了", "en": "C drive space decreased by"},
    "space_increase": {"zh": "这段时间 C 盘空间增加了", "en": "C drive space increased by"},
    "space_cleanup_ok": {"zh": "（清理见效）", "en": " (cleanup worked)"},
    "space_nochange": {"zh": "这段时间 C 盘空间基本没变化", "en": "C drive space barely changed"},
    "explained_label": {"zh": "已解释比例", "en": "Explained"},
    "explained_hint": {"zh": "已解释比例 =（顶层已识别目录的增长 ÷ 所有顶层目录的增长总和）×100%，按字节量算、父子目录去重，不是按条目个数算。越高说明识别库覆盖越好；偏低说明大部分增长来自「未识别文件夹」，建议扩充识别库。",
                       "en": "Explained ratio = (growth of top-level identified folders ÷ total growth of all top-level folders) × 100%, measured in bytes with parent/child dedup, not by entry count. Higher means better DB coverage; low means most growth comes from unrecognized folders — consider extending the DB."},
    "footer_note": {"zh": "说明：本报告对比两次快照，逐文件夹列出增长量超过 1MB 的目录，标明路径、是什么、增长多少、以及「建不建议删」。✅=可放心删，🟡=建议清理，🔴=谨慎（软件本体/游戏，删前确认）。删除前请确认数据已备份。",
                    "en": "This report compares two snapshots and lists folders that changed by >1MB, with path, what it is, how much, and whether it's safe to delete. ✅=safe, 🟡=cleanup, 🔴=caution (app/game, confirm first). Back up before deleting."},
    "lang_zh": {"zh": "中文", "en": "中文"},
    "lang_en": {"zh": "English", "en": "English"},
}

# 命令行 / 文本报告的翻译表（供 config.LANG 选择）
CLI = {
    "zh": {
        "banner_start": "C 盘空间监视器 启动",
        "monitor_drive": "监视盘符",
        "record_threshold": "记录阈值",
        "record_freq": "记录频率",
        "data_dir": "数据目录",
        "report_dir": "报告目录",
        "start_scan": "开始扫描 C 盘...",
        "scan_done": "扫描完成，快照已保存",
        "used_free": "C 盘已用",
        "once_done": "单次扫描完成，程序退出。",
        "gen_compare": "已生成对比报告",
        "text": "文本",
        "web": "网页",
        "space_decrease": "这段时间 C 盘空间减少",
        "space_increase": "这段时间 C 盘空间增加",
        "space_nochange": "这段时间 C 盘空间基本没变化",
        "top_cause": "最大元凶",
        "grew": "增长了",
        "overview_gen": "（暂只有 1 次快照，生成「占用盘点」报告）",
        "auto_open": "已自动打开报告",
        "auto_open_fail": "自动打开报告失败，请手动打开",
        "history_gen": "历史对比页面已生成",
        "history_insufficient": "快照不足 2 次，暂无历史对比可看。",
    },
    "en": {
        "banner_start": "C Drive Monitor started",
        "monitor_drive": "Drive",
        "record_threshold": "Record threshold",
        "record_freq": "Frequency",
        "data_dir": "Data dir",
        "report_dir": "Report dir",
        "start_scan": "Scanning C drive...",
        "scan_done": "Scan done, snapshot saved",
        "used_free": "Used",
        "once_done": "Single scan done, exiting.",
        "gen_compare": "Generated compare report",
        "text": "text",
        "web": "web",
        "space_decrease": "C drive space decreased by",
        "space_increase": "C drive space increased by",
        "space_nochange": "C drive space barely changed",
        "top_cause": "Top cause",
        "grew": "grew by",
        "overview_gen": "(only 1 snapshot, generated usage overview)",
        "auto_open": "Report opened automatically",
        "auto_open_fail": "Failed to auto-open report, open manually",
        "history_gen": "History page generated",
        "history_insufficient": "Less than 2 snapshots, nothing to compare.",
    },
}


def t(key, lang="zh"):
    """取命令行/文本报告里的翻译文案。"""
    table = CLI.get(lang, CLI["zh"])
    return table.get(key, CLI["zh"].get(key, key))
