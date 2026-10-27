# -*- coding: utf-8 -*-
"""
生成「当前 C 盘占用盘点」报告（逐文件夹列出，含删除建议等级）。
用法：python overview.py
"""

import os
import datetime
import html as html_lib

import config
import scanner
import i18n
from scanner import human_size


def render_overview_html(snap):
    """生成当前占用盘点的网页报告（逐文件夹列出）。"""
    lang = config.LANG
    labels = config.LEVEL_LABEL_EN if lang == "en" else config.LEVEL_LABEL

    def _sw(d):
        if lang == "en":
            return d.get("software_name_en") or d.get("software_name") or ""
        return d.get("software_name") or ""

    def _tip(d):
        if lang == "en":
            return d.get("tip_en") or d.get("tip", "") or "—"
        return d.get("tip", "") or "—"

    # 已识别的文件夹，按大小降序
    rec = [d for d in snap["dirs"] if "software_name" in d]
    rec.sort(key=lambda x: -x["size"])

    rows = []
    for i, d in enumerate(rec[:60], 1):
        sw_zh = d.get("software_name", "")
        lvl = config.deletion_level(sw_zh)
        label = labels.get(lvl, "—")
        tip = _tip(d)
        pct = (d["size"] / snap["disk_used"] * 100) if snap["disk_used"] else 0
        rows.append(
            "<tr><td>%d</td><td class='path'>%s</td><td>%s</td><td>%s</td>"
            "<td>%.1f%%</td><td class='lvl-%s'>%s</td><td>%s</td></tr>"
            % (i, html_lib.escape(d["path"]), html_lib.escape(_sw(d)),
               human_size(d["size"]), pct, lvl, label, html_lib.escape(tip))
        )

    # 未识别大目录
    unrec = [d for d in snap["dirs"] if "software_name" not in d]
    unrec.sort(key=lambda x: -x["size"])
    unrec = unrec[:30]
    unrec_rows = []
    for d in unrec:
        unrec_rows.append(
            "<tr><td class='path'>%s</td><td>%s</td><td>%s</td></tr>"
            % (html_lib.escape(d["path"]), human_size(d["size"]),
               ("未识别" if lang == "zh" else "Unrecognized"))
        )

    rows_html = "\n".join(rows)
    unrec_html = "\n".join(unrec_rows)

    used_pct = (snap["disk_used"] / snap["disk_total"] * 100) if snap["disk_total"] else 0

    # 固定文字的两种语言
    U = lambda k: i18n.UI.get(k, {}).get(lang, i18n.UI.get(k, {}).get("zh", k))

    html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>__TITLE__</title>
<style>
  body { font-family: "Microsoft YaHei", sans-serif; margin: 0; background: #f5f6fa; color: #2c3e50; }
  .wrap { max-width: 1200px; margin: 24px auto; padding: 0 16px; }
  .card { background: #fff; border-radius: 10px; padding: 24px; margin-bottom: 16px; box-shadow: 0 1px 4px rgba(0,0,0,.08); }
  h1 { font-size: 22px; margin: 0 0 4px; }
  .sub { color: #7f8c8d; font-size: 13px; }
  .stats { display: flex; gap: 24px; flex-wrap: wrap; margin-top: 16px; }
  .stat { flex: 1; min-width: 150px; background: #f8f9fa; border-radius: 8px; padding: 16px; }
  .stat .label { font-size: 12px; color: #95a5a6; }
  .stat .val { font-size: 22px; font-weight: bold; margin-top: 4px; }
  .bar { height: 18px; background: #e9ecef; border-radius: 9px; overflow: hidden; margin-top: 12px; }
  .bar-fill { height: 100%; background: linear-gradient(90deg, #e74c3c, #f39c12); }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th, td { padding: 10px 8px; text-align: left; border-bottom: 1px solid #eee; vertical-align: top; }
  th { background: #f0f2f5; color: #555; }
  .path { font-family: Consolas, monospace; font-size: 12px; color: #34495e; word-break: break-all; }
  .tip { color: #555; font-size: 12px; }
  .lvl-safe { color: #27ae60; font-weight: bold; white-space: nowrap; }
  .lvl-cleanup { color: #e67e22; font-weight: bold; white-space: nowrap; }
  .lvl-caution { color: #e74c3c; font-weight: bold; white-space: nowrap; }
  .lvl-unknown { color: #95a5a6; white-space: nowrap; }
  .legend { display: flex; gap: 16px; flex-wrap: wrap; margin-top: 12px; font-size: 13px; }
</style>
</head>
<body>
<div class="wrap">
  <div class="card">
    <h1>__H1__</h1>
    <div class="sub">__SUBTIME__　·　__SUBLIST__</div>
    <div class="stats">
      <div class="stat"><div class="label">__L_TOTAL__</div><div class="val">__TOTAL__</div></div>
      <div class="stat"><div class="label">__L_USED__</div><div class="val" style="color:#e74c3c">__USED__</div></div>
      <div class="stat"><div class="label">__L_FREE__</div><div class="val">__FREE__</div></div>
      <div class="stat"><div class="label">__L_PCT__</div><div class="val" style="color:#e74c3c">__PCT__</div></div>
    </div>
    <div class="bar"><div class="bar-fill" style="width:__BARW__%"></div></div>
    <div class="legend">
      <span class="lvl-safe">__L_SAFE__</span>（__L_SAFE_DESC__）
      <span class="lvl-cleanup">__L_CLEANUP__</span>（__L_CLEANUP_DESC__）
      <span class="lvl-caution">__L_CAUTION__</span>（__L_CAUTION_DESC__）
    </div>
  </div>

  <div class="card">
    <h2 style="font-size:16px;margin-top:0">__H2_TOP__</h2>
    <table>
      <tr><th>#</th><th>__TH_PATH__</th><th>__TH_WHAT__</th><th>__TH_SIZE__</th><th>__TH_PCT__</th><th>__TH_LEVEL__</th><th>__TH_TIP__</th></tr>
      __ROWS__
    </table>
  </div>

  <div class="card">
    <h2 style="font-size:16px;margin-top:0">__H2_UNREC__</h2>
    <table>
      <tr><th>__TH_PATH__</th><th>__TH_SIZE__</th><th>__TH_NOTE__</th></tr>
      __UNREC__
    </table>
  </div>

  <div class="card tip">
    __FOOTER__
  </div>
</div>
</body>
</html>
"""
    html = (html
            .replace("__TITLE__", ("C 盘占用盘点" if lang == "zh" else "C Drive Usage Overview"))
            .replace("__H1__", ("C 盘占用盘点" if lang == "zh" else "C Drive Usage Overview"))
            .replace("__SUBTIME__", ("扫描时间：%s" if lang == "zh" else "Scanned at: %s") % snap["time"])
            .replace("__SUBLIST__", ("按文件夹逐个列出" if lang == "zh" else "listed per folder"))
            .replace("__L_TOTAL__", ("总容量" if lang == "zh" else "Total"))
            .replace("__L_USED__", ("已用" if lang == "zh" else "Used"))
            .replace("__L_FREE__", ("可用" if lang == "zh" else "Free"))
            .replace("__L_PCT__", ("使用率" if lang == "zh" else "Usage"))
            .replace("__L_SAFE__", ("✅ 可放心删" if lang == "zh" else "✅ Safe to delete"))
            .replace("__L_SAFE_DESC__", ("缓存/临时文件，删了系统会自己重建" if lang == "zh" else "cache/temp, auto-rebuilt"))
            .replace("__L_CLEANUP__", ("🟡 建议清理" if lang == "zh" else "🟡 Cleanup"))
            .replace("__L_CLEANUP_DESC__", ("聊天/浏览器缓存，删了不影响功能" if lang == "zh" else "chat/browser cache, safe"))
            .replace("__L_CAUTION__", ("🔴 谨慎" if lang == "zh" else "🔴 Caution"))
            .replace("__L_CAUTION_DESC__", ("软件本体/游戏/个人数据，删前确认" if lang == "zh" else "apps/games/data, confirm first"))
            .replace("__H2_TOP__", ("占用最大的文件夹（逐条，前 60）" if lang == "zh" else "Largest folders (per folder, top 60)"))
            .replace("__H2_UNREC__", ("较大的未识别文件夹（可自行判断）" if lang == "zh" else "Large unrecognized folders"))
            .replace("__TH_PATH__", ("文件夹路径" if lang == "zh" else "Path"))
            .replace("__TH_WHAT__", ("是什么" if lang == "zh" else "What it is"))
            .replace("__TH_SIZE__", ("大小" if lang == "zh" else "Size"))
            .replace("__TH_PCT__", ("占已用比" if lang == "zh" else "% of used"))
            .replace("__TH_LEVEL__", ("删除建议" if lang == "zh" else "Delete?"))
            .replace("__TH_TIP__", ("说明" if lang == "zh" else "Note"))
            .replace("__TH_NOTE__", ("备注" if lang == "zh" else "Note"))
            .replace("__FOOTER__", (
                "说明：本报告逐文件夹列出 C 盘占用情况，不再按公司合并。每个文件夹标明了「是什么」「多大」「建不建议删」。"
                "「✅ 可放心删」的缓存/临时文件删掉后系统或软件会自动重建，最安全；「🔴 谨慎」的软件本体和游戏，删前请确认不再使用。删除任何数据前建议先备份。"
                if lang == "zh" else
                "This report lists C-drive usage per folder (not merged by company). Each folder shows what it is, how big, and whether it's safe to delete. "
                "✅=safe (cache/temp, auto-rebuilt), 🔴=caution (apps/games, confirm first). Back up before deleting."))
            .replace("__TOTAL__", human_size(snap["disk_total"]))
            .replace("__USED__", human_size(snap["disk_used"]))
            .replace("__FREE__", human_size(snap["disk_free"]))
            .replace("__PCT__", "%.1f%%" % used_pct)
            .replace("__BARW__", "%.1f" % used_pct)
            .replace("__ROWS__", rows_html)
            .replace("__UNREC__", unrec_html))
    return html


def main():
    print("开始扫描 C 盘（约 30 秒）...")
    snap = scanner.scan()
    os.makedirs(config.REPORT_DIR, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(config.REPORT_DIR, "overview_%s.html" % ts)
    with open(path, "w", encoding="utf-8") as f:
        f.write(render_overview_html(snap))
    print("占用盘点报告已生成：%s" % path)


if __name__ == "__main__":
    main()
