# -*- coding: utf-8 -*-
"""
报告生成器：对比两次快照，生成「空间减少原因 + 删除建议」报告。
支持纯文本(.txt)和网页(.html)两种格式。
"""

import os
import json
import datetime
import html as html_lib

import config
import scanner
import i18n
from scanner import human_size


def _slim_snapshots(snaps):
    """把快照精简成可内嵌到网页的 JSON（只留已识别目录 + ≥10MB 的未识别目录）。"""
    slim = []
    for s in snaps:
        dirs_slim = []
        for d in s["dirs"]:
            if "software_name" in d or d["size"] >= 10 * 1024 * 1024:
                dirs_slim.append({
                    "path": d["path"], "size": d["size"],
                    "software_name": d.get("software_name", ""),
                    "software_name_en": d.get("software_name_en", ""),
                    "company": d.get("company", ""),
                    "tip": d.get("tip", ""),
                    "tip_en": d.get("tip_en", ""),
                })
        slim.append({
            "time": s["time"],
            "disk_used": s["disk_used"],
            "disk_free": s["disk_free"],
            "disk_total": s["disk_total"],
            "dirs": dirs_slim,
        })
    return slim


def _history_data_block():
    """生成「历史对比」所需的精简快照 JSON 字符串（报告页内嵌用）。"""
    snaps = scanner.load_snapshots()
    slim = _slim_snapshots(snaps)
    return json.dumps(slim, ensure_ascii=False)


def build_diff(prev, curr):
    """
    对比两次快照，生成对比结果。
    返回 dict：
    {
      "prev_time": 上次时间,
      "curr_time": 本次时间,
      "disk_used_change": 已用空间变化(字节，正=变多),
      "grew": [ {name, company, tip, prev_size, curr_size, change}, ... 增长列表按降序 ],
      "shrank": [ ... 减少列表 ],
      "new_software": [ 新出现的软件 ],
      "total_growth": 增长总和,
      "explained_ratio": 已解释比例,
    }
    """
    prev_map = {d["path"]: d for d in prev["dirs"]}
    curr_map = {d["path"]: d for d in curr["dirs"]}

    # 兜底：两侧 min_size 不一致时（用户中途调了阈值），按较大者再过滤一次，
    # 否则会出现「旧快照有、新快照没有」的假消失。幂等：口径相同时不改变任何东西。
    eff = max(prev.get("min_size", 0), curr.get("min_size", 0))
    if eff:
        prev = dict(prev)
        curr = dict(curr)
        prev["dirs"] = [d for d in prev["dirs"] if d.get("size", 0) >= eff]
        curr["dirs"] = [d for d in curr["dirs"] if d.get("size", 0) >= eff]
        prev_map = {d["path"]: d for d in prev["dirs"]}
        curr_map = {d["path"]: d for d in curr["dirs"]}

    grew = []
    shrank = []

    # 对比同一路径
    all_paths = set(prev_map.keys()) | set(curr_map.keys())
    for p in all_paths:
        p_prev = prev_map.get(p)
        p_curr = curr_map.get(p)
        if p_prev and p_curr:
            change = p_curr["size"] - p_prev["size"]
            if abs(change) >= 1 * 1024 * 1024:  # 变化超过 1MB 才记录
                item = {
                    "path": p,
                    "name": p_curr.get("name", ""),
                    "software_name": p_curr.get("software_name", "未识别文件夹"),
                    "software_name_en": p_curr.get("software_name_en", ""),
                    "company": p_curr.get("company", ""),
                    "tip": p_curr.get("tip", ""),
                    "tip_en": p_curr.get("tip_en", ""),
                    "prev_size": p_prev["size"],
                    "curr_size": p_curr["size"],
                    "change": change,
                }
                if change > 0:
                    grew.append(item)
                else:
                    shrank.append(item)
        elif p_curr and not p_prev:
            # 新出现的文件夹
            if p_curr["size"] >= 1 * 1024 * 1024:
                grew.append({
                    "path": p,
                    "name": p_curr.get("name", ""),
                    "software_name": p_curr.get("software_name", "未识别文件夹"),
                    "software_name_en": p_curr.get("software_name_en", ""),
                    "company": p_curr.get("company", ""),
                    "tip": p_curr.get("tip", ""),
                    "tip_en": p_curr.get("tip_en", ""),
                    "prev_size": 0,
                    "curr_size": p_curr["size"],
                    "change": p_curr["size"],
                })
        elif p_prev and not p_curr:
            # 消失的文件夹
            if p_prev["size"] >= 1 * 1024 * 1024:
                shrank.append({
                    "path": p,
                    "name": p_prev.get("name", ""),
                    "software_name": p_prev.get("software_name", "未识别文件夹"),
                    "software_name_en": p_prev.get("software_name_en", ""),
                    "company": p_prev.get("company", ""),
                    "tip": p_prev.get("tip", ""),
                    "tip_en": p_prev.get("tip_en", ""),
                    "prev_size": p_prev["size"],
                    "curr_size": 0,
                    "change": -p_prev["size"],
                })

    grew.sort(key=lambda x: -x["change"])
    shrank.sort(key=lambda x: x["change"])

    disk_used_change = curr["disk_used"] - prev["disk_used"]
    total_growth = sum(x["change"] for x in grew)

    # 已解释比例：在「能看到的总增长」里，识别库认出了多少。
    # 分母不用磁盘净变化（disk_used_change）：净变化会被同时发生的清理抵消，
    # 导致分子比分母大、比例超过 100%（实测过：临时目录涨 445MB、净减少只有 338MB）。
    # 这里统一用「顶层目录的增长总和」做分母，结果稳定落在 0~100%。
    grew_paths = {x["path"] for x in grew}
    top_growth_total = 0
    top_growth_identified = 0
    for x in grew:
        # 有祖先目录也在 grew 里的，跳过（它的增长已被祖先计入，避免父子目录重复计数）
        parent = os.path.dirname(x["path"])
        has_ancestor = False
        while parent != os.path.dirname(parent):
            if parent in grew_paths:
                has_ancestor = True
                break
            parent = os.path.dirname(parent)
        if has_ancestor:
            continue
        top_growth_total += x["change"]
        if x["software_name"] and x["software_name"] != "未识别文件夹":
            top_growth_identified += x["change"]

    explained = top_growth_identified / top_growth_total if top_growth_total > 0 else 0.0
    explained = min(max(explained, 0.0), 1.0)

    # 新出现的软件（上次没有、这次有的软件条目）
    prev_sw = set()
    for d in prev["dirs"]:
        if "software_name" in d:
            prev_sw.add(d["software_name"])
    curr_sw = set()
    for d in curr["dirs"]:
        if "software_name" in d:
            curr_sw.add(d["software_name"])
    new_software = list(curr_sw - prev_sw)

    return {
        "prev_time": prev["time"],
        "curr_time": curr["time"],
        "disk_used_change": disk_used_change,
        "grew": grew,
        "shrank": shrank,
        "new_software": new_software,
        "total_growth": total_growth,
        "explained_ratio": explained,
        "curr_used": curr["disk_used"],
        "curr_total": curr["disk_total"],
        "curr_free": curr["disk_free"],
    }


def render_text(diff):
    """生成纯文本报告（语言跟随 config.LANG）。"""
    lang = config.LANG
    T = lambda k: i18n.t(k, lang)

    lines = []
    lines.append("=" * 60)
    lines.append("C 盘空间变化报告" if lang == "zh" else "C Drive Space Change Report")
    lines.append("=" * 60)
    lines.append(("上次记录：%s" if lang == "zh" else "Previous: %s") % diff["prev_time"])
    lines.append(("本次记录：%s" if lang == "zh" else "Current: %s") % diff["curr_time"])
    lines.append("")
    lines.append(("C 盘已用空间：%s" if lang == "zh" else "C drive used: %s") % human_size(diff["curr_used"]))
    lines.append(("C 盘可用空间：%s" if lang == "zh" else "C drive free: %s") % human_size(diff["curr_free"]))
    lines.append("")
    change = diff["disk_used_change"]
    if change > 0:
        lines.append((T("space_decrease") + " %s。") % human_size(change))
    elif change < 0:
        lines.append((T("space_increase") + " %s（清理见效）。") % human_size(-change))
    else:
        lines.append(T("space_nochange") + "。")
    lines.append("")

    if diff["grew"]:
        lines.append("-" * 60)
        lines.append(T("grew_title") + ("：" if lang == "zh" else ":"))
        lines.append("-" * 60)
        for i, g in enumerate(diff["grew"][:30], 1):
            sw = (g.get("software_name_en") if lang == "en" else None) or g.get("software_name") or ""
            tip = (g.get("tip_en") if lang == "en" else None) or g.get("tip", "")
            lvl = config.deletion_level(g.get("software_name") or sw) if (g.get("software_name") or sw) else "unknown"
            label = (config.LEVEL_LABEL_EN if lang == "en" else config.LEVEL_LABEL).get(lvl, "—")
            lines.append("%2d. %s  %s %s   [%s]" % (
                i, g["path"],
                ("增长了" if lang == "zh" else "grew"),
                human_size(g["change"]), label))
            if sw:
                lines.append(("    是什么：%s" if lang == "zh" else "    What: %s") % sw)
            lines.append(("    大小：%s -> %s" if lang == "zh" else "    Size: %s -> %s") % (
                human_size(g["prev_size"]), human_size(g["curr_size"])))
            if tip:
                lines.append(("    建议：%s" if lang == "zh" else "    Tip: %s") % tip)
            lines.append("")
    else:
        lines.append(T("no_grew"))

    if diff["shrank"]:
        lines.append("-" * 60)
        lines.append(T("shrank_title") + ("：" if lang == "zh" else ":"))
        lines.append("-" * 60)
        for i, s in enumerate(diff["shrank"][:30], 1):
            sw = (s.get("software_name_en") if lang == "en" else None) or s.get("software_name") or ""
            tag = sw if sw else s["name"]
            lines.append("%2d. %s  %s %s   [%s]" % (
                i, s["path"],
                ("减少了" if lang == "zh" else "shrank"),
                human_size(-s["change"]), tag))
            lines.append(("    大小：%s -> %s" if lang == "zh" else "    Size: %s -> %s") % (
                human_size(s["prev_size"]), human_size(s["curr_size"])))
            lines.append("")

    if diff["new_software"]:
        lines.append("")
        lines.append("本次新出现的软件/公司文件夹：" if lang == "zh" else "New software/company folders:")
        for n in diff["new_software"]:
            lines.append("  - %s" % n)

    lines.append("")
    lines.append("=" * 60)
    lines.append(("报告生成时间：%s" if lang == "zh" else "Generated: %s") % datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    lines.append("=" * 60)
    return "\n".join(lines)


def render_html(diff):
    """生成网页报告（含「本次对比」+「历史对比」双标签）。"""

    def _sw_zh(g):
        # 未识别时 software_name 字段在 build_diff 里被默认成了「未识别文件夹」，
        # 这里直接返回即可（中文显示「未识别文件夹」）。
        return g.get("software_name") or ""

    def _sw_en(g):
        # 优先英文名；若没有英文名但识别出中文名，则退回中文名；
        # 若连中文名都只是「未识别文件夹」占位（即真正未识别），显示英文占位。
        en = g.get("software_name_en") or ""
        if en:
            return en
        zh = g.get("software_name") or ""
        if zh and zh != "未识别文件夹":
            return zh
        return "Unrecognized folder"

    def _tip_zh(g):
        return g.get("tip", "") or "—"

    def _tip_en(g):
        return g.get("tip_en") or g.get("tip", "") or "—"

    def _label(g):
        sw = g.get("software_name") or ""
        lvl = config.deletion_level(sw) if sw else "unknown"
        return lvl, config.LEVEL_LABEL.get(lvl, "—"), config.LEVEL_LABEL_EN.get(lvl, "—")

    rows = []
    for i, g in enumerate(diff["grew"][:40], 1):
        sw_zh = _sw_zh(g)
        sw_en = _sw_en(g)
        tag_zh = sw_zh if sw_zh else g["name"]
        tag_en = sw_en if sw_en else g["name"]
        tip_zh = _tip_zh(g)
        tip_en = _tip_en(g)
        lvl, label_zh, label_en = _label(g)
        rows.append(
            "<tr><td>%d</td><td class='path'>%s</td><td><span data-zh>%s</span><span data-en style='display:none'>%s</span></td><td class='up'>+%s</td>"
            "<td>%s</td><td>%s</td><td class='lvl-%s'><span data-zh>%s</span><span data-en style='display:none'>%s</span></td><td><span data-zh>%s</span><span data-en style='display:none'>%s</span></td></tr>"
            % (i, html_lib.escape(g["path"]), html_lib.escape(tag_zh), html_lib.escape(tag_en), human_size(g["change"]),
               human_size(g["prev_size"]), human_size(g["curr_size"]), lvl, label_zh, label_en, html_lib.escape(tip_zh), html_lib.escape(tip_en))
        )

    shrink_rows = []
    for i, s in enumerate(diff["shrank"][:40], 1):
        sw_zh = _sw_zh(s)
        sw_en = _sw_en(s)
        tag_zh = sw_zh if sw_zh else s["name"]
        tag_en = sw_en if sw_en else s["name"]
        tip_zh = _tip_zh(s)
        tip_en = _tip_en(s)
        lvl, label_zh, label_en = _label(s)
        shrink_rows.append(
            "<tr><td>%d</td><td class='path'>%s</td><td><span data-zh>%s</span><span data-en style='display:none'>%s</span></td><td class='down'>-%s</td>"
            "<td>%s</td><td>%s</td><td class='lvl-%s'><span data-zh>%s</span><span data-en style='display:none'>%s</span></td><td><span data-zh>%s</span><span data-en style='display:none'>%s</span></td></tr>"
            % (i, html_lib.escape(s["path"]), html_lib.escape(tag_zh), html_lib.escape(tag_en), human_size(-s["change"]),
               human_size(s["prev_size"]), human_size(s["curr_size"]), lvl, label_zh, label_en, html_lib.escape(tip_zh), html_lib.escape(tip_en))
        )

    change = diff["disk_used_change"]
    if change > 0:
        change_txt = human_size(change)
    elif change < 0:
        change_txt = ('<span data-zh>增加 %s</span><span data-en style="display:none">Increased %s</span>'
                      % (human_size(-change), human_size(-change)))
    else:
        change_txt = '<span data-zh>无变化</span><span data-en style="display:none">No change</span>'

    shrink_html = ("<table><tr><th data-i18n='col_no'>#</th><th data-i18n='col_path'>文件夹路径</th><th data-i18n='col_what'>是什么</th><th data-i18n='col_shrank'>减少量</th><th data-i18n='col_prev'>之前</th><th data-i18n='col_curr'>现在</th><th data-i18n='col_level'>删除建议</th><th data-i18n='col_tip'>说明</th></tr>"
                   + "\n".join(shrink_rows) + "</table>") if shrink_rows else "<p data-i18n='no_shrank'>没有检测到被清理的文件夹。</p>"
    rows_html = "\n".join(rows)

    html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>C 盘空间变化报告</title>
<style>
  body { font-family: "Microsoft YaHei", sans-serif; margin: 0; background: #f5f6fa; color: #2c3e50; }
  .wrap { max-width: 1000px; margin: 24px auto; padding: 0 16px; }
  .card { background: #fff; border-radius: 10px; padding: 24px; margin-bottom: 16px; box-shadow: 0 1px 4px rgba(0,0,0,.08); }
  h1 { font-size: 22px; margin: 0 0 4px; }
  .sub { color: #7f8c8d; font-size: 13px; }
  .stats { display: flex; gap: 24px; flex-wrap: wrap; margin-top: 12px; }
  .stat { flex: 1; min-width: 140px; background: #f8f9fa; border-radius: 8px; padding: 16px; }
  .stat .label { font-size: 12px; color: #95a5a6; }
  .stat .val { font-size: 22px; font-weight: bold; margin-top: 4px; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th, td { padding: 10px 8px; text-align: left; border-bottom: 1px solid #eee; vertical-align: top; }
  th { background: #f0f2f5; color: #555; }
  .up { color: #e74c3c; font-weight: bold; }
  .down { color: #27ae60; font-weight: bold; }
  .path { font-family: Consolas, monospace; font-size: 12px; color: #34495e; word-break: break-all; }
  .lvl-safe { color: #27ae60; font-weight: bold; white-space: nowrap; }
  .lvl-cleanup { color: #e67e22; font-weight: bold; white-space: nowrap; }
  .lvl-caution { color: #e74c3c; font-weight: bold; white-space: nowrap; }
  .lvl-unknown { color: #95a5a6; white-space: nowrap; }
  ul { padding-left: 20px; }
  li { margin: 4px 0; }
  .tip { color: #555; font-size: 12px; }
  .tabs { display: flex; gap: 8px; margin-bottom: 16px; border-bottom: 2px solid #e0e0e0; }
  .tab { padding: 8px 16px; cursor: pointer; font-size: 14px; color: #7f8c8d; border: none; background: none; }
  .tab.active { color: #3498db; font-weight: bold; border-bottom: 2px solid #3498db; margin-bottom: -2px; }
  .tabview { display: none; }
  .tabview.active { display: block; }
  .snap-list { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }
  .snap { border: 2px solid #e0e0e0; border-radius: 8px; padding: 8px 12px; cursor: pointer; user-select: none; transition: all .15s; }
  .snap:hover { border-color: #3498db; }
  .snap.sel { border-color: #3498db; background: #ebf5fb; }
  .snap .idx { display: inline-block; background: #3498db; color: #fff; border-radius: 50%; width: 20px; height: 20px; text-align: center; line-height: 20px; font-size: 12px; margin-right: 6px; }
  .snap .t { font-size: 13px; margin-right: 8px; }
  .snap .sz { font-size: 12px; color: #95a5a6; }
  .hint { color: #7f8c8d; font-size: 13px; margin-top: 12px; }
  .empty { color: #95a5a6; padding: 20px; text-align: center; }
  .result-title { font-size: 15px; font-weight: bold; margin: 0 0 8px; }
  .change-line { font-size: 14px; margin: 8px 0; }
  .lang-switch { position: fixed; top: 12px; right: 16px; z-index: 99; }
  .lang-switch button { padding: 6px 14px; border: 1px solid #ccc; background: #fff; color: #555; cursor: pointer; font-size: 13px; border-radius: 6px; }
  .lang-switch button.on { background: #3498db; color: #fff; border-color: #3498db; }
</style>
</head>
<body>
<div class="lang-switch">
  <button id="btnZh" class="on" onclick="setLang('zh')">中文</button>
  <button id="btnEn" onclick="setLang('en')">English</button>
</div>
<div class="wrap">
  <div class="card">
    <h1 data-i18n="report_title">C 盘空间变化报告</h1>
    <div class="sub"><span data-i18n="prev_label">上次记录</span>：__PREV__ 　→　<span data-i18n="curr_label">本次记录</span>：__CURR__</div>
    <div class="stats">
      <div class="stat"><div class="label" data-i18n="used_label">本次已用</div><div class="val">__USED__</div></div>
      <div class="stat"><div class="label" data-i18n="free_label">本次可用</div><div class="val">__FREE__</div></div>
      <div class="stat"><div class="label" data-i18n="change_label">空间变化</div><div class="val" style="color:#e74c3c">__CHANGE__</div></div>
      <div class="stat"><div class="label" data-i18n="explained_label">已解释比例</div><div class="val">__EXPLAINED__</div></div>
    </div>
    <div class="sub" data-i18n="explained_hint">已解释比例 =（顶层已识别目录的增长 ÷ 所有顶层目录的增长总和）×100%，按字节量算、父子目录去重，不是按条目个数算。越高说明识别库覆盖越好；偏低说明大部分增长来自「未识别文件夹」，建议扩充识别库。</div>
  </div>

  <div class="tabs">
    <button class="tab active" data-i18n="tab_this" onclick="switchTab(0)">本次对比</button>
    <button class="tab" data-i18n="tab_history" onclick="switchTab(1)">历史对比</button>
  </div>

  <div id="view0" class="tabview active">
    <div class="card">
      <h2 style="font-size:16px;margin-top:0" data-i18n="grew_title">变大的文件夹（空间减少的元凶，逐条）</h2>
      <table>
        <tr><th data-i18n="col_no">#</th><th data-i18n="col_path">文件夹路径</th><th data-i18n="col_what">是什么</th><th data-i18n="col_grew">增长量</th><th data-i18n="col_prev">之前</th><th data-i18n="col_curr">现在</th><th data-i18n="col_level">删除建议</th><th data-i18n="col_tip">说明</th></tr>
        __ROWS__
      </table>
    </div>

    <div class="card">
      <h2 style="font-size:16px;margin-top:0" data-i18n="shrank_title">变小的文件夹（这段时间释放的空间，按减少量排序）</h2>
      __SHRINK__
    </div>

    <div class="card tip" data-i18n="footer_note">
      说明：本报告对比两次快照，逐文件夹列出增长量超过 1MB 的目录，标明路径、是什么、增长多少、
      以及「建不建议删」。✅=可放心删，🟡=建议清理，🔴=谨慎（软件本体/游戏，删前确认）。
      删除前请确认数据已备份。
    </div>
  </div>

  <div id="view1" class="tabview">
    <div class="card">
      <h2 style="font-size:16px;margin-top:0" data-i18n="history_title">历史对比</h2>
      <div class="sub" data-i18n="history_sub">点选两个快照（先后顺序 = 时间顺序），下方自动显示对比结果</div>
      <div class="snap-list" id="snapList"></div>
      <div class="hint" id="hint" data-i18n="history_hint">请选择两次扫描进行对比（点击两次）。</div>
    </div>
    <div class="card" id="resultCard">
      <div class="result-title" id="resultTitle" data-i18n="result_title">对比结果</div>
      <div class="change-line" id="changeLine"></div>
      <div id="resultBody"><div class="empty" data-i18n="not_selected">尚未选择两次扫描。</div></div>
    </div>
  </div>
</div>

<script>
const DATA = __DATA__;
const LEVELS = __LEVELS__;
const LABELS = __LABELS__;
const I18N = __I18N__;
const SAFE = new Set(LEVELS.safe), CLEANUP = new Set(LEVELS.cleanup), CAUTION = new Set(LEVELS.caution);
let curLang = 'zh';

function setLang(lang) {
  curLang = lang;
  document.getElementById('btnZh').classList.toggle('on', lang === 'zh');
  document.getElementById('btnEn').classList.toggle('on', lang === 'en');
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const k = el.getAttribute('data-i18n');
    if (I18N[k] && I18N[k][lang]) el.textContent = I18N[k][lang];
  });
  // 切换「本次对比」表格里的双份数据（软件名/建议/等级/变化量）
  document.querySelectorAll('[data-zh]').forEach(el => {
    el.style.display = (lang === 'zh') ? '' : 'none';
  });
  document.querySelectorAll('[data-en]').forEach(el => {
    el.style.display = (lang === 'en') ? '' : 'none';
  });
  // 刷新历史快照列表里的「已用」和已选提示、以及已显示的对比结果
  if (window._histInit) {
    initHistory();
    renderList();
    if (sel.length === 2) { compare(sel[0], sel[1]); }
    else { updateHint(); }
  }
}

function updateHint() {
  const hint = document.getElementById('hint');
  if (sel.length === 2) {
    hint.textContent = (curLang === 'zh' ? '正在对比：第 ' : 'Comparing: #') + (sel[0]+1) + (curLang === 'zh' ? ' 次 → 第 ' : ' → #') + (sel[1]+1) + (curLang === 'zh' ? ' 次' : '');
  } else if (sel.length === 1) {
    hint.textContent = curLang === 'zh' ? '已选第 '+(sel[0]+1)+' 次，请再选第二次。' : 'Selected #'+(sel[0]+1)+', pick a second one.';
  } else {
    hint.textContent = T('history_hint');
  }
}

function switchTab(n) {
  document.querySelectorAll('.tab').forEach((t, i) => t.classList.toggle('active', i === n));
  document.getElementById('view0').classList.toggle('active', n === 0);
  document.getElementById('view1').classList.toggle('active', n === 1);
  if (n === 1 && !window._histInit) { window._histInit = true; initHistory(); }
}

function levelOf(sw) {
  const L = LABELS[curLang] || LABELS.zh;
  if (!sw) return { lvl: 'unknown', label: L.unknown };
  if (SAFE.has(sw))    return { lvl: 'safe',    label: L.safe };
  if (CLEANUP.has(sw)) return { lvl: 'cleanup', label: L.cleanup };
  if (CAUTION.has(sw)) return { lvl: 'caution', label: L.caution };
  return { lvl: 'unknown', label: L.unknown };
}

function swName(d) {
  if (curLang === 'en') return d.software_name_en || d.software_name || '';
  return d.software_name || '';
}
function swTip(d) {
  if (curLang === 'en') return d.tip_en || d.tip || '';
  return d.tip || '';
}

function humanSize(n) {
  if (n == null) return '?';
  const units = ['B','KB','MB','GB','TB'];
  let v = n, i = 0;
  while (v >= 1024 && i < units.length - 1) { v /= 1024; i++; }
  return (i === 0 ? v.toFixed(0) : v.toFixed(2)) + ' ' + units[i];
}

function esc(s) {
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

let sel = [];

function initHistory() {
  const list = document.getElementById('snapList');
  list.innerHTML = '';
  DATA.forEach((s, i) => {
    const d = document.createElement('div');
    d.className = 'snap';
    d.dataset.idx = i;
    d.innerHTML = '<span class="idx">' + (i+1) + '</span>' +
                  '<span class="t">' + esc(s.time) + '</span>' +
                  '<span class="sz">' + (curLang === 'zh' ? '已用 ' : 'Used ') + humanSize(s.disk_used) + '</span>';
    list.appendChild(d);
  });
}

function renderList() {
  document.querySelectorAll('#snapList .snap').forEach(el => {
    el.classList.toggle('sel', sel.includes(parseInt(el.dataset.idx)));
  });
}

function T(k) { return (I18N[k] && I18N[k][curLang]) || k; }

function compare(a, b) {
  const prev = DATA[a], curr = DATA[b];
  const prevMap = {}, currMap = {};
  prev.dirs.forEach(d => prevMap[d.path] = d);
  curr.dirs.forEach(d => currMap[d.path] = d);

  const grew = [], shrank = [];
  const all = new Set([...Object.keys(prevMap), ...Object.keys(currMap)]);
  for (const p of all) {
    const pp = prevMap[p], cc = currMap[p];
    if (pp && cc) {
      const ch = cc.size - pp.size;
      if (Math.abs(ch) >= 1024*1024) {
        const item = { path: p, sw: swName(cc), sw_zh: cc.software_name||'', company: cc.company||'', tip: swTip(cc), prev: pp.size, curr: cc.size, change: ch };
        (ch > 0 ? grew : shrank).push(item);
      }
    } else if (cc && !pp && cc.size >= 1024*1024) {
      grew.push({ path: p, sw: swName(cc), sw_zh: cc.software_name||'', company: cc.company||'', tip: swTip(cc), prev: 0, curr: cc.size, change: cc.size });
    } else if (pp && !cc && pp.size >= 1024*1024) {
      shrank.push({ path: p, sw: swName(pp), sw_zh: pp.software_name||'', company: pp.company||'', tip: swTip(pp), prev: pp.size, curr: 0, change: -pp.size });
    }
  }
  grew.sort((x, y) => y.change - x.change);
  shrank.sort((x, y) => x.change - y.change);

  const diskChange = curr.disk_used - prev.disk_used;
  document.getElementById('resultTitle').textContent = T('result_title') + ': ' + prev.time + ' → ' + curr.time;
  const cl = document.getElementById('changeLine');
  if (diskChange > 0) cl.innerHTML = T('space_decrease') + ' <b style="color:#e74c3c">' + humanSize(diskChange) + '</b>';
  else if (diskChange < 0) cl.innerHTML = T('space_increase') + ' <b style="color:#27ae60">' + humanSize(-diskChange) + '</b>' + T('space_cleanup_ok');
  else cl.innerHTML = T('space_nochange');

  let body = '';
  if (grew.length) {
    body += '<table><tr><th>' + T('col_no') + '</th><th>' + T('col_path') + '</th><th>' + T('col_what') + '</th><th>' + T('col_grew') + '</th><th>' + T('col_prev') + '</th><th>' + T('col_curr') + '</th><th>' + T('col_level') + '</th><th>' + T('col_tip') + '</th></tr>';
    grew.slice(0, 50).forEach((g, i) => {
      const lv = levelOf(g.sw_zh || g.sw);
      const what = g.sw || (curLang === 'en' ? 'Unrecognized folder' : '未识别文件夹');
      body += '<tr><td>'+(i+1)+'</td><td class="path">'+esc(g.path)+'</td><td>'+esc(what)+'</td><td class="up">+'+humanSize(g.change)+'</td><td>'+humanSize(g.prev)+'</td><td>'+humanSize(g.curr)+'</td><td class="lvl-'+lv.lvl+'">'+lv.label+'</td><td>'+esc(g.tip||'—')+'</td></tr>';
    });
    body += '</table>';
  } else {
    body += '<div class="empty">' + T('no_grew') + '</div>';
  }

  if (shrank.length) {
    body += '<h3 style="font-size:14px;margin:16px 0 8px">' + T('shrank_title') + '</h3>';
    body += '<table><tr><th>' + T('col_no') + '</th><th>' + T('col_path') + '</th><th>' + T('col_what') + '</th><th>' + T('col_shrank') + '</th><th>' + T('col_prev') + '</th><th>' + T('col_curr') + '</th><th>' + T('col_level') + '</th><th>' + T('col_tip') + '</th></tr>';
    shrank.slice(0, 50).forEach((s, i) => {
      const lv = levelOf(s.sw_zh || s.sw);
      const what = s.sw || (curLang === 'en' ? 'Unrecognized folder' : '未识别文件夹');
      body += '<tr><td>'+(i+1)+'</td><td class="path">'+esc(s.path)+'</td><td>'+esc(what)+'</td><td class="down">-'+humanSize(-s.change)+'</td><td>'+humanSize(s.prev)+'</td><td>'+humanSize(s.curr)+'</td><td class="lvl-'+lv.lvl+'">'+lv.label+'</td><td>'+esc(s.tip||'—')+'</td></tr>';
    });
    body += '</table>';
  }

  document.getElementById('resultBody').innerHTML = body;
}

document.getElementById('snapList').addEventListener('click', (e) => {
  const el = e.target.closest('.snap');
  if (!el) return;
  const idx = parseInt(el.dataset.idx);
  if (sel.includes(idx)) {
    sel = sel.filter(x => x !== idx);
  } else {
    sel.push(idx);
    if (sel.length > 2) sel.shift();
  }
  sel.sort((a,b) => a-b);
  renderList();
  if (sel.length === 2) {
    compare(sel[0], sel[1]);
  } else {
    updateHint();
  }
});
</script>
</body>
</html>
"""
    # DELETION_LEVELS 的值是 set，json 不能直接序列化，转成 list 再注入
    levels_json = json.dumps(
        {k: sorted(v) for k, v in config.DELETION_LEVELS.items()},
        ensure_ascii=False)

    # 已解释比例：被识别出的增长 / 磁盘总增长（0~1，可能因舍入略超 1）
    explained_txt = ("%d%%" % round(min(max(diff["explained_ratio"], 0.0), 1.0) * 100))

    html = (html
            .replace("__PREV__", diff["prev_time"])
            .replace("__CURR__", diff["curr_time"])
            .replace("__USED__", human_size(diff["curr_used"]))
            .replace("__FREE__", human_size(diff["curr_free"]))
            .replace("__CHANGE__", change_txt)
            .replace("__EXPLAINED__", explained_txt)
            .replace("__ROWS__", rows_html)
            .replace("__SHRINK__", shrink_html)
            .replace("__DATA__", _history_data_block().replace("</", "<\\/"))
            .replace("__LEVELS__", levels_json)
            .replace("__LABELS__", json.dumps(
                {"zh": config.LEVEL_LABEL, "en": config.LEVEL_LABEL_EN}, ensure_ascii=False))
            .replace("__I18N__", json.dumps(i18n.UI, ensure_ascii=False)))
    return html


def generate_report(prev, curr):
    """生成报告，返回 (txt路径, html路径)。"""
    os.makedirs(config.REPORT_DIR, exist_ok=True)
    diff = build_diff(prev, curr)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    txt_path = os.path.join(config.REPORT_DIR, "report_%s.txt" % ts)
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(render_text(diff))

    html_path = os.path.join(config.REPORT_DIR, "report_%s.html" % ts)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(render_html(diff))

    return txt_path, html_path, diff


if __name__ == "__main__":
    from scanner import load_snapshots
    snaps = load_snapshots()
    if len(snaps) < 2:
        print("至少需要两次快照才能生成对比报告，目前有 %d 次。" % len(snaps))
    else:
        prev, curr = snaps[-2], snaps[-1]
        txt, html, diff = generate_report(prev, curr)
        print("报告已生成：")
        print("  文本：%s" % txt)
        print("  网页：%s" % html)
        print("\n" + render_text(diff))
