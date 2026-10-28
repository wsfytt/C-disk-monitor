# C 盘空间监视器 · C Drive Monitor

一个纯 Python 的 Windows 工具：定时扫描 C 盘，找出「是哪个软件/公司的文件夹变大导致 C 盘空间减少」，并给出删除建议。

A pure-Python Windows tool: periodically scans the C drive, finds out "which software/company folder grew and ate your C drive space", and gives deletion suggestions.

**只扫描、记录、出报告，绝不删除任何文件。**
**It only scans, records and reports — it never deletes any file.**

## 功能 · Features

- 深度扫描 C 盘，逐文件夹统计大小，并识别所属软件/公司（微信、WPS、Adobe、NVIDIA、Microsoft Office、Chrome 等上百条识别规则）
  Deeply scans the C drive, measures each folder, and identifies the owning software/company (over a hundred rules covering WeChat, WPS, Adobe, NVIDIA, Microsoft Office, Chrome, etc.)
- 定时记录快照，对比两次快照，告诉你「这段时间 C 盘减少了多少、是哪个文件夹变大导致的」
  Records snapshots on a schedule and diffs them, telling you "how much C drive space shrank and which folder grew"
- 报告里每个文件夹标明：完整路径、是什么、之前/现在大小、增减量、删除建议等级（✅ 可放心删 / 🟡 建议清理 / 🔴 谨慎）
  Each folder in the report shows: full path, what it is, before/now size, change, and a deletion level (✅ safe to delete / 🟡 consider cleaning / 🔴 caution)
- 支持查看任意两次历史扫描之间的对比（交互式网页）
  Compare any two historical scans (interactive web page)
- 可注册 Windows 计划任务，每天自动扫描一次
  Can register a Windows scheduled task to scan once a day
- 中英双语：网页报告带「中文 / English」切换按钮（默认中文）；命令行和 .txt 报告可用 `config.py` 的 `LANG` 开关切换
  Bilingual: the web report has a "中文 / English" toggle (Chinese by default); CLI and .txt reports use the `LANG` switch in `config.py`

## 环境要求 · Requirements

- Windows（依赖 `os.scandir` 的 `st_file_attributes` 识别 junction，仅 Windows 有）
  Windows (relies on `os.scandir`'s `st_file_attributes` to detect junctions, Windows-only)
- Python 3.8+（标准库即可，无第三方依赖）
  Python 3.8+ (standard library only, no third-party dependencies)

## 下载即用（不用装 Python）· Download the ready-to-run build

不想装 Python？直接下载打包好的 Windows 版，解压后双击 bat 就能用：

- 打开 [Releases](https://github.com/wsfytt/C-disk-monitor/releases) 页面
- 下载 `C-Disk-Monitor-v0.1.0-win64.zip`
- 解压，双击 `立即扫描一次 Scan Now.bat`

Don't want to install Python? Grab the prebuilt Windows build:

- Open the [Releases](https://github.com/wsfytt/C-disk-monitor/releases) page
- Download `C-Disk-Monitor-v0.1.0-win64.zip`
- Unzip and double-click `立即扫描一次 Scan Now.bat`

> 说明：exe 由 PyInstaller 打包，部分杀毒软件会对这类程序报"未知风险"，属常见误报，源码完全公开可自行核对（也可用下面的源码方式运行）。
> Note: the exe is built with PyInstaller. Some antivirus tools flag such builds as unknown — a common false positive. The source is fully public, or just run from source below.

## 快速开始 · Quick Start

```bash
# 立即扫描一次并保存快照 / scan once and save a snapshot
python monitor.py --once

# 扫描完自动打开报告（浏览器）/ scan then auto-open the report
python monitor.py --once --open

# 常驻后台，每天记录一次（Ctrl+C 退出）/ run in background, record once a day (Ctrl+C to exit)
python monitor.py
```

Windows 用户也可以直接双击项目目录里的 `立即扫描一次 Scan Now.bat` / `启动监视 Start Monitor.bat` / `注册每日自动扫描 Register Daily Scan.bat`。

Windows users can also double-click `立即扫描一次 Scan Now.bat` / `启动监视 Start Monitor.bat` / `注册每日自动扫描 Register Daily Scan.bat` in the project folder.

## 命令一览 · Commands

```bash
python monitor.py                    # 常驻后台，每天记录一次 / run in background, record daily
python monitor.py --once             # 立即扫描一次并保存快照 / scan once and save a snapshot
python monitor.py --once --open      # 扫描完自动打开报告 / scan then auto-open the report
python compare.py                    # 列出所有历史快照 / list all snapshots
python compare.py 1 3                # 对比第 1 次和第 3 次快照 / diff snapshot 1 vs 3
python compare.py --all              # 生成所有相邻快照的对比 / diff every adjacent pair
python compare.py --last             # 对比最新两次 / diff the latest two
python monitor.py --report           # 不扫描，直接打开带「历史对比」标签的报告页 / open the report with a "History Compare" tab, no scan
python overview.py                   # 生成「当前占用盘点」报告 / generate a "current usage" report
python install_task.py               # 注册「每天自动扫描」计划任务 / register the daily-scan task
python install_task.py --uninstall   # 取消计划任务 / remove the scheduled task
python monitor.py --install-task     # 同上（打包成 exe 后用它注册）/ same, for the exe build
python monitor.py --uninstall-task   # 同上（取消）/ same, to remove
```

### 查看任意两次扫描之间的对比 · Compare any two scans

积累了多次扫描后，你可以对比**任意两次**，而不只是相邻两次。

After a few scans, you can compare **any two** scans, not just adjacent ones.

**方式一（图形界面）· Method 1 (GUI):** 双击 `查看历史对比 View History Compare.bat`（或 `python monitor.py --report`）—— 不扫描 C 盘，直接打开带「历史对比」标签的报告页。页面上方列出所有历史扫描，点选两次（先早后晚），下方立即显示这两个时间点之间的对比。

Double-click `查看历史对比 View History Compare.bat` (or `python monitor.py --report`) — opens the report page with a "History Compare" tab without scanning. Pick two scans at the top (earlier then later) and the diff appears below.

**方式二（命令行）· Method 2 (CLI):**

```bash
compare.py           # 列出所有快照（带序号）/ list all snapshots (numbered)
compare.py 1 3       # 对比第 1 次和第 3 次 / diff #1 vs #3
compare.py --all     # 生成所有相邻两次的对比（1→2、2→3、3→4...）/ diff every adjacent pair
compare.py --last    # 对比最新两次 / diff the latest two
```

## 数据存放位置 · Data location

默认存放在 `%LOCALAPPDATA%\c_disk_monitor\`（`data/` 存快照，`reports/` 存报告），例如 `C:\Users\alice\AppData\Local\c_disk_monitor`。

Stored by default in `%LOCALAPPDATA%\c_disk_monitor\` (`data/` for snapshots, `reports/` for reports), e.g. `C:\Users\alice\AppData\Local\c_disk_monitor`.

如需自定义，设置环境变量 `CDM_DATA_DIR` 指向你的目录。

To customize, set the `CDM_DATA_DIR` environment variable to your folder.

从旧版本（数据写在项目上一级）升级：把旧的 `c_disk_monitor_data` 整个移动到 `%LOCALAPPDATA%\c_disk_monitor`，或直接设置 `CDM_DATA_DIR` 指过去。旧的全量格式快照会在读取时自动对齐到当前记录口径，无需手工处理。

Upgrading from an older version (data written one level above the project): move the old `c_disk_monitor_data` into `%LOCALAPPDATA%\c_disk_monitor`, or point `CDM_DATA_DIR` at it. Old full-format snapshots are auto-aligned to the current schema on read.

## 配置 · Configuration

在 `config.py` 中可调整 / Tunable in `config.py`:

- `MONITOR_DRIVE`：要监视的盘符（默认 `C:`）/ the drive to monitor (default `C:`)
- `MIN_DIR_SIZE_TO_RECORD`：记录阈值，低于此大小的目录不进快照和报告（默认 5 MB，调大让快照更小）/ recording threshold; smaller dirs are skipped (default 5 MB; raise it for smaller snapshots)
- `RECORD_INTERVAL_SECONDS`：常驻模式下的记录间隔 / recording interval in resident mode
- `LANG`：命令行提示和 `.txt` 报告的语言（`"zh"` 中文默认 / `"en"` 英文）。网页报告自带头部「中文 / English」切换按钮，不受此开关影响 / language for CLI and `.txt` reports (`"zh"` default / `"en"`). The web report has its own toggle, unaffected by this switch
- 软件/公司识别库：已独立到 `software_db.json`（纯数据文件，见下文「扩充识别库」）/ the software/company identification DB is now a standalone `software_db.json` (pure data, see "Extending the DB" below)

## 常见问题 · FAQ

**Q：为什么「Windows」目录没出现在报告里？ / Why isn't the "Windows" folder in the report?**
A：系统目录（Windows、回收站等）默认跳过，因为这些用户不该手动删，删了会导致系统崩溃。
System folders (Windows, Recycle Bin, etc.) are skipped by default — they must not be deleted manually or the system will break.

**Q：报告里出现「未识别文件夹」怎么办？ / What about an "unrecognized folder" in the report?**
A：说明这个文件夹名不在识别库里。打开 `software_db.json`，在 `software_db` 里加一条即可：
It means the folder name isn't in the DB. Open `software_db.json` and add an entry:

```
"你的文件夹名": {"name": "显示名", "company": "公司", "tip": "怎么处理它"},
```

键名用小写，匹配时按「路径包含该词」判定，越长的键优先。加完记得把 `name` 归到 `deletion_levels` 的某一档。
Use lowercase keys; matching is "the path contains the word", longer keys first. Also assign its `name` to a tier in `deletion_levels`.

**Q：识别库怎么快速扩充？ / How do I quickly extend the DB?**
A：识别库是纯数据文件 `software_db.json`，很容易让 AI 帮你改。把本项目的 `SOFTWARE_DB_GUIDE.md` 丢给你的 AI（ChatGPT、Claude、DeepSeek 等），让它结合你这台电脑的实际软件 + 联网查询，自动帮你扩充、修正识别库。识别内容仅供参考，实际以软件内显示为准。
The DB is a pure data file `software_db.json`, easy to hand to an AI. Give this project's `SOFTWARE_DB_GUIDE.md` to your AI (ChatGPT, Claude, DeepSeek, etc.), have it combine your installed software + web search to extend/correct the DB. Identifications are for reference only; trust what the software itself shows.

**Q：识别库怎么支持中英双语？ / How does the DB stay bilingual?**
A：`software_db.json` 里每条软件都有 `name`（中文名）/ `name_en`（英文名）和 `tip`（中文建议）/ `tip_en`（英文建议）四个字段。程序按 `config.LANG` 和网页上的语言按钮自动取对应语言。新增条目时记得中英两版都写全（详见 `SOFTWARE_DB_GUIDE.md`）。
Each entry has four fields: `name` (CN) / `name_en` (EN) and `tip` (CN) / `tip_en` (EN). The program picks the language by `config.LANG` and the page's toggle. Fill in both languages for new entries (see `SOFTWARE_DB_GUIDE.md`).

**Q：删除建议安全吗？ / Are the deletion suggestions safe?**
A：建议只是参考。删除任何东西前，请确认里面没有你要保留的数据。「缓存」「临时文件」这类一般可以放心删，游戏和软件目录请确认不再使用。
Suggestions are advisory only. Before deleting anything, make sure it has nothing you want to keep. "Cache" / "temp" are generally safe; for games and software folders, confirm you no longer use them.

## 隐私说明 · Privacy

本工具只在本机运行，扫描结果（快照、报告）只保存在你本地，不会上传任何数据。

This tool runs locally only; scan results (snapshots, reports) stay on your machine and nothing is uploaded.

报告里的文件夹路径包含你的 Windows 用户名（例如 `C:\Users\alice\AppData\...`），**分享截图前请把含用户名的部分打码**。

Folder paths in reports contain your Windows username (e.g. `C:\Users\alice\AppData\...`) — **blur the username part before sharing screenshots**.

请勿把 `data/`、`reports/` 或 `c_disk_monitor_data/` 目录提交到公开仓库——里面含有你本机的目录结构和用户名等个人信息（`.gitignore` 已默认排除）。

Do not commit `data/`, `reports/` or `c_disk_monitor_data/` to a public repo — they contain your local directory structure and username (already excluded by `.gitignore`).

## 打包成 exe · Building the exe

用 [PyInstaller](https://pyinstaller.org/) 打成单文件 exe（含 `software_db.json`），发布包里的 bat 会调用它：

Pack a single-file exe with [PyInstaller](https://pyinstaller.org/) (bundling `software_db.json`); the bat launchers in the release zip call it:

```bash
pip install pyinstaller
pyinstaller --onefile --console --name "C盘空间监视器" ^
  --add-data "software_db.json;." ^
  --exclude-module tkinter --exclude-module unittest monitor.py
```

产物在 `dist\` 下。把 exe 和四个 bat 放到同一个文件夹里即为免安装版。

Output lands in `dist\`. Put the exe together with the four bat files in one folder — that's the portable build.

## 开发与测试 · Development & tests

测试只依赖标准库 / Tests use only the standard library:

```
python -m unittest discover -s tests -v
```

## 商标声明 · Trademarks

本项目与文中提及的任何公司（腾讯、阿里巴巴、字节跳动、Adobe、Google、Microsoft、NVIDIA、金山 等）均无关联，也未获其背书。所有产品名称、软件名称与商标归其各自所有者，此处仅用于说明文件夹用途。

This project is not affiliated with or endorsed by any company mentioned (Tencent, Alibaba, ByteDance, Adobe, Google, Microsoft, NVIDIA, Kingsoft, etc.). All product names, software names and trademarks belong to their respective owners and are used here only to describe folder purposes.

## 许可证 · License

[MIT](./LICENSE)
