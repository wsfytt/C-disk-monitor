# C 盘空间监视器（c_disk_monitor）

一个纯 Python 的 Windows 工具：定时扫描 C 盘，找出「是哪个软件/公司的文件夹变大导致 C 盘空间减少」，并给出删除建议。

**只扫描、记录、出报告，绝不删除任何文件。**

## 功能

- 深度扫描 C 盘，逐文件夹统计大小，并识别所属软件/公司（Origin、EA、Steam、微信、QQ、Adobe、NVIDIA 等几十种常见「C 盘杀手」）
- 定时记录快照，对比两次快照，告诉你「这段时间 C 盘减少了多少、是哪个文件夹变大导致的」
- 报告里每个文件夹标明：完整路径、是什么、之前/现在大小、增减量、删除建议等级（✅ 可放心删 / 🟡 建议清理 / 🔴 谨慎）
- 支持查看任意两次历史扫描之间的对比（交互式网页）
- 可注册 Windows 计划任务，每天自动扫描一次
- 中英双语：网页报告带「中文 / English」切换按钮（默认中文）；命令行和 .txt 报告可用 `config.py` 的 `LANG` 开关切换

## 环境要求

- Windows（依赖 `os.scandir` 的 `st_file_attributes` 识别 junction，仅 Windows 有）
- Python 3.8+（标准库即可，无第三方依赖）

## 快速开始

```bash
# 立即扫描一次并保存快照
python monitor.py --once

# 扫描完自动打开报告（浏览器）
python monitor.py --once --open

# 常驻后台，每天记录一次（Ctrl+C 退出）
python monitor.py
```

Windows 用户也可以直接双击项目目录里的 `立即扫描一次.bat` / `启动监视.bat` / `注册每日自动扫描.bat`。

## 命令一览

```bash
python monitor.py                    # 常驻后台，每天记录一次
python monitor.py --once             # 立即扫描一次并保存快照
python monitor.py --once --open      # 扫描完自动打开报告
python compare.py                    # 列出所有历史快照
python compare.py 1 3                # 对比第 1 次和第 3 次快照
python compare.py --all              # 生成所有相邻快照的对比
python compare.py --last             # 对比最新两次
python monitor.py --report           # 不扫描，直接打开带「历史对比」标签的报告页
python overview.py                   # 生成「当前占用盘点」报告
python install_task.py               # 注册「每天自动扫描」计划任务
python install_task.py --uninstall   # 取消计划任务
```

### 查看任意两次扫描之间的对比

积累了多次扫描后，你可以对比**任意两次**，而不只是相邻两次。

**方式一（图形界面）：** 双击 `查看历史对比.bat`（或 `python monitor.py --report`）—— 不扫描 C 盘，直接打开带「历史对比」标签的报告页。页面上方列出所有历史扫描，点选两次（先早后晚），下方立即显示这两个时间点之间的对比。

**方式二（命令行）：**

```bash
compare.py           # 列出所有快照（带序号）
compare.py 1 3       # 对比第 1 次和第 3 次
compare.py --all     # 生成所有相邻两次的对比（1→2、2→3、3→4...）
compare.py --last    # 对比最新两次
```

## 数据存放位置

默认存放在 `%LOCALAPPDATA%\c_disk_monitor\`（`data/` 存快照，`reports/` 存报告），例如 `C:\Users\alice\AppData\Local\c_disk_monitor`。

如需自定义，设置环境变量 `CDM_DATA_DIR` 指向你的目录。

从旧版本（数据写在项目上一级）升级：把旧的 `c_disk_monitor_data` 整个移动到 `%LOCALAPPDATA%\c_disk_monitor`，或直接设置 `CDM_DATA_DIR` 指过去。旧的全量格式快照会在读取时自动对齐到当前记录口径，无需手工处理。

## 配置

在 `config.py` 中可调整：

- `MONITOR_DRIVE`：要监视的盘符（默认 `C:`）
- `MIN_DIR_SIZE_TO_RECORD`：记录阈值，低于此大小的目录不进快照和报告（默认 5 MB，调大让快照更小）
- `RECORD_INTERVAL_SECONDS`：常驻模式下的记录间隔
- `LANG`：命令行提示和 `.txt` 报告的语言（`"zh"` 中文默认 / `"en"` 英文）。网页报告自带头部「中文 / English」切换按钮，不受此开关影响
- 软件/公司识别库：已独立到 `software_db.json`（纯数据文件，见下文「扩充识别库」）

## 常见问题

**Q：为什么「Windows」目录没出现在报告里？**
A：系统目录（Windows、回收站等）默认跳过，因为这些用户不该手动删，删了会导致系统崩溃。

**Q：报告里出现「未识别文件夹」怎么办？**
A：说明这个文件夹名不在识别库里。打开 `software_db.json`，在 `software_db` 里加一条即可：

```
"你的文件夹名": {"name": "显示名", "company": "公司", "tip": "怎么处理它"},
```

键名用小写，匹配时按「路径包含该词」判定，越长的键优先。加完记得把 `name` 归到 `deletion_levels` 的某一档。

**Q：识别库怎么快速扩充？**
A：识别库是纯数据文件 `software_db.json`，很容易让 AI 帮你改。把本项目的 `SOFTWARE_DB_GUIDE.md` 丢给你的 AI（ChatGPT、Claude、DeepSeek 等），让它结合你这台电脑的实际软件 + 联网查询，自动帮你扩充、修正识别库。识别内容仅供参考，实际以软件内显示为准。

**Q：识别库怎么支持中英双语？**
A：`software_db.json` 里每条软件都有 `name`（中文名）/ `name_en`（英文名）和 `tip`（中文建议）/ `tip_en`（英文建议）四个字段。程序按 `config.LANG` 和网页上的语言按钮自动取对应语言。新增条目时记得中英两版都写全（详见 `SOFTWARE_DB_GUIDE.md`）。

**Q：删除建议安全吗？**
A：建议只是参考。删除任何东西前，请确认里面没有你要保留的数据。「缓存」「临时文件」这类一般可以放心删，游戏和软件目录请确认不再使用。

## 隐私说明

本工具只在本机运行，扫描结果（快照、报告）只保存在你本地，不会上传任何数据。

报告里的文件夹路径包含你的 Windows 用户名（例如 `C:\Users\alice\AppData\...`），**分享截图前请把含用户名的部分打码**。

请勿把 `data/`、`reports/` 或 `c_disk_monitor_data/` 目录提交到公开仓库——里面含有你本机的目录结构和用户名等个人信息（`.gitignore` 已默认排除）。

## 开发与测试

测试只依赖标准库：

```
python -m unittest discover -s tests -v
```

## 商标声明

本项目与文中提及的任何公司（EA、Valve、Epic Games、腾讯、阿里巴巴、字节跳动、Adobe、Google、Microsoft、NVIDIA 等）均无关联，也未获其背书。所有产品名称、软件名称与商标归其各自所有者，此处仅用于说明文件夹用途。

## 许可证

[MIT](./LICENSE)
