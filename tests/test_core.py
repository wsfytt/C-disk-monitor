# -*- coding: utf-8 -*-
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
import reporter
from scanner import human_size

MB = 1024 * 1024


class TestHumanSize(unittest.TestCase):
    def test_values(self):
        self.assertEqual(human_size(None), "?")
        self.assertEqual(human_size(0), "0 B")
        self.assertEqual(human_size(1023), "1023 B")
        self.assertEqual(human_size(1024), "1.00 KB")
        self.assertEqual(human_size(1536), "1.50 KB")
        self.assertEqual(human_size(5 * 1024 * MB), "5.00 GB")


class TestIdentify(unittest.TestCase):
    def test_hit(self):
        self.assertEqual(config.identify(r"c:\program files\steamapps\common")["name"],
                         "Steam 游戏库")

    def test_longest_key_wins(self):
        # "steamapps"(9) 比 "steam"(5) 长，必须命中前者
        self.assertEqual(config.identify(r"c:\program files\steamapps")["name"],
                         "Steam 游戏库")
        self.assertEqual(config.identify(r"c:\program files\steam")["name"],
                         "Steam 平台")

    def test_miss(self):
        self.assertIsNone(config.identify(r"c:\my random folder"))

    def test_short_key_not_matched_inside_word(self):
        # 短键不能在更长的单词内部命中（下面每个路径里都藏着该短键）
        # "edge" 藏在 acknowledge 里
        self.assertIsNone(config.identify(r"C:\Users\x\data\acknowledge"))
        # "pip" 藏在 piping 里
        self.assertIsNone(config.identify(r"C:\Users\x\data\design\piping"))
        # "npm" 藏在 pnpm 里
        self.assertIsNone(config.identify(r"C:\Users\x\projects\app\pnpm-store"))
        # "go" 藏在 algorithms 里
        self.assertIsNone(config.identify(r"C:\Users\x\docs\algorithms"))

    def test_camel_case_boundary_still_matches(self):
        # FontCache 里的 "Cache" 是驼峰词首，必须仍然命中
        self.assertEqual(config.identify(
            r"C:\Users\x\AppData\Local\Microsoft\FontCache")["name"], "缓存目录")
        self.assertEqual(config.identify(
            r"C:\Program Files\Microsoft OfficePLUS")["name"], "Microsoft Office")


class TestDeletionLevel(unittest.TestCase):
    def test_levels(self):
        self.assertEqual(config.deletion_level("微信"), "cleanup")
        self.assertEqual(config.deletion_level("Steam 游戏库"), "caution")
        self.assertEqual(config.deletion_level("NVIDIA 显卡缓存"), "safe")
        self.assertEqual(config.deletion_level("不存在的软件"), "unknown")


class TestBuildDiff(unittest.TestCase):
    def _snap(self, used, dirs):
        return {"time": "2026-01-01T00:00:00", "disk_total": 1000 * MB,
                "disk_free": 1000 * MB - used, "disk_used": used, "dirs": dirs}

    def test_growth(self):
        # 用识别库里真实存在的路径：名字现在按「当前库」解释，不再取快照里的旧值
        p = r"C:\Program Files\NVIDIA Corporation"
        prev = self._snap(100 * MB, [{"path": p, "name": "NVIDIA Corporation", "size": 10 * MB}])
        curr = self._snap(130 * MB, [{"path": p, "name": "NVIDIA Corporation", "size": 30 * MB}])
        diff = reporter.build_diff(prev, curr)
        self.assertEqual(diff["disk_used_change"], 30 * MB)
        self.assertEqual(len(diff["grew"]), 1)
        self.assertEqual(diff["grew"][0]["change"], 20 * MB)
        # 只有它在增长且当前库能识别 → 已解释比例 100%
        self.assertAlmostEqual(diff["explained_ratio"], 1.0, places=3)

    def test_explained_ratio_dedup(self):
        # 父子目录重复计数：NetEase 和 NetEase\CloudMusic 是同一份增长，分母不能被算两遍
        prev = self._snap(100 * MB, [
            {"path": r"C:\NetEase", "name": "NetEase", "size": 10 * MB, "software_name": "网易软件目录"},
            {"path": r"C:\NetEase\CloudMusic", "name": "CloudMusic", "size": 8 * MB, "software_name": "网易云音乐"},
            {"path": r"C:\Mystery", "name": "Mystery", "size": 10 * MB},
        ])
        curr = self._snap(130 * MB, [
            {"path": r"C:\NetEase", "name": "NetEase", "size": 30 * MB, "software_name": "网易软件目录"},
            {"path": r"C:\NetEase\CloudMusic", "name": "CloudMusic", "size": 28 * MB, "software_name": "网易云音乐"},
            {"path": r"C:\Mystery", "name": "Mystery", "size": 30 * MB},
        ])
        diff = reporter.build_diff(prev, curr)
        # grew 列表仍逐条列（含父子重复 20MB + 20MB + 20MB）
        self.assertEqual(diff["total_growth"], 60 * MB)
        # 已解释比例只按顶层算：已识别 20MB / 顶层总增长 40MB = 50%
        self.assertAlmostEqual(diff["explained_ratio"], 0.5, places=3)

    def test_explained_ratio_ignores_unrecognized(self):
        # 未识别文件夹的增长不计入分子
        prev = self._snap(100 * MB, [{"path": r"C:\A", "name": "A", "size": 10 * MB}])
        curr = self._snap(130 * MB, [{"path": r"C:\A", "name": "A", "size": 30 * MB}])
        diff = reporter.build_diff(prev, curr)
        self.assertEqual(diff["explained_ratio"], 0.0)

    def test_explained_ratio_never_exceeds_one(self):
        # 磁盘净变化被清理抵消时（增长 > 净减少），比例也不能超过 100%
        p = r"C:\Program Files\NVIDIA Corporation"
        prev = self._snap(200 * MB, [{"path": p, "name": "NVIDIA Corporation", "size": 100 * MB}])
        curr = self._snap(150 * MB, [{"path": p, "name": "NVIDIA Corporation", "size": 150 * MB}])
        diff = reporter.build_diff(prev, curr)
        self.assertLessEqual(diff["explained_ratio"], 1.0)
        self.assertEqual(diff["explained_ratio"], 1.0)

    def test_name_comes_from_current_db(self):
        # 名字按当前识别库解释，而不是照抄快照里扫描时写死的值
        p = r"C:\Program Files\NVIDIA Corporation"
        prev = self._snap(100 * MB, [{"path": p, "name": "X", "size": 10 * MB,
                                      "software_name": "旧名字"}])
        curr = self._snap(130 * MB, [{"path": p, "name": "X", "size": 30 * MB,
                                      "software_name": "旧名字"}])
        diff = reporter.build_diff(prev, curr)
        item = diff["grew"][0]
        self.assertEqual(item["software_name"], "NVIDIA 显卡缓存")
        # 旧名字保留下来，供界面显示「扫描时记为」
        self.assertEqual(item["scan_sw"], "旧名字")
        self.assertTrue(item["renamed"])

    def test_removed_db_entry_falls_back_to_unrecognized(self):
        # 库里删掉条目后，历史快照里的旧名字不再作为主显示，统一显示「未识别文件夹」，
        # 但旧名字仍保留在 scan_sw 里，不会被抹掉
        p = r"C:\ProgramData\Kaspersky Lab"
        self.assertIsNone(config.identify(p))
        prev = self._snap(100 * MB, [{"path": p, "name": "Kaspersky Lab", "size": 10 * MB,
                                      "software_name": "卡巴斯基"}])
        curr = self._snap(130 * MB, [{"path": p, "name": "Kaspersky Lab", "size": 30 * MB,
                                      "software_name": "卡巴斯基"}])
        diff = reporter.build_diff(prev, curr)
        item = diff["grew"][0]
        self.assertEqual(item["software_name"], "未识别文件夹")
        self.assertEqual(item["scan_sw"], "卡巴斯基")
        self.assertTrue(item["renamed"])

    def test_shrink_and_new(self):
        prev = self._snap(200 * MB, [{"path": r"C:\B", "name": "B", "size": 50 * MB}])
        curr = self._snap(180 * MB, [{"path": r"C:\B", "name": "B", "size": 40 * MB},
                                     {"path": r"C:\C", "name": "C", "size": 5 * MB}])
        diff = reporter.build_diff(prev, curr)
        self.assertEqual(diff["shrank"][0]["change"], -10 * MB)
        self.assertEqual(diff["grew"][0]["path"], r"C:\C")


class TestSlimSnapshots(unittest.TestCase):
    """报告页内嵌快照的体积预算。

    快照每天累积，若全部内嵌，页面会从 3MB 一路涨到几十 MB，浏览器打不开。
    这里验证：体积有上限、保留的是最新的、至少留 2 份能对比。
    """

    def _snaps(self, n, dirs_per_snap=200):
        out = []
        for i in range(n):
            dirs = [{"path": r"C:\AppData\Folder%03d_of_snapshot_%02d" % (j, i),
                     "name": "Folder%03d" % j,
                     "size": (j + 1) * MB,
                     "software_name": "缓存目录"} for j in range(dirs_per_snap)]
            out.append({"time": "2026-10-26T12:00:%02d" % i,
                        "disk_used": 100 * MB, "disk_free": 50 * MB,
                        "disk_total": 150 * MB, "dirs": dirs})
        return out

    def test_keeps_all_when_under_budget(self):
        slim, total = reporter._slim_snapshots(self._snaps(5), budget=100 * MB)
        self.assertEqual(len(slim), 5)
        self.assertEqual(total, 5)

    def test_trims_oldest_when_over_budget(self):
        snaps = self._snaps(20)
        slim, total = reporter._slim_snapshots(snaps, budget=300_000, min_keep=2)
        self.assertEqual(total, 20)
        self.assertLess(len(slim), 20)
        # 被丢掉的必须是更早的，最后一份始终是最新那份
        self.assertEqual(slim[-1]["time"], snaps[-1]["time"])

    def test_always_keeps_two(self):
        slim, _ = reporter._slim_snapshots(self._snaps(10), budget=1, min_keep=2)
        self.assertEqual(len(slim), 2)

    def test_page_size_bounded_as_snapshots_grow(self):
        import json
        s10, _ = reporter._slim_snapshots(self._snaps(10), budget=300_000)
        s60, _ = reporter._slim_snapshots(self._snaps(60), budget=300_000)
        size10 = len(json.dumps(s10, ensure_ascii=False).encode("utf-8"))
        size60 = len(json.dumps(s60, ensure_ascii=False).encode("utf-8"))
        # 份数翻 6 倍，内嵌体积不应跟着翻
        self.assertLess(size10, 400_000)
        self.assertLess(size60, 400_000)
        self.assertLess(size60, size10 * 2)


class TestDbFingerprint(unittest.TestCase):
    """识别库指纹：内容相同 => 指纹相同；内容一变 => 指纹变。"""

    def test_fingerprint_ignores_key_order(self):
        a = {"software_db": {"x": {"name": "甲"}, "y": {"name": "乙"}}}
        b = {"software_db": {"y": {"name": "乙"}, "x": {"name": "甲"}}}
        self.assertEqual(config._db_fingerprint(a), config._db_fingerprint(b))

    def test_fingerprint_changes_with_content(self):
        a = {"software_db": {"x": {"name": "甲"}}}
        b = {"software_db": {"x": {"name": "甲改"}}}
        self.assertNotEqual(config._db_fingerprint(a), config._db_fingerprint(b))

    def test_fingerprint_shape(self):
        self.assertEqual(len(config.SOFTWARE_DB_ID), 12)
        self.assertTrue(all(c in "0123456789abcdef" for c in config.SOFTWARE_DB_ID))

    def test_db_info_fields(self):
        info = config.db_info()
        self.assertEqual(set(info), {"id", "count", "matcher", "source"})
        self.assertEqual(info["count"], len(config.SOFTWARE_DB))
        self.assertGreaterEqual(info["matcher"], 1)
        self.assertIn(info["source"], {"bundled", "external", "env", "none"})

    def test_archive_writes_one_file_per_content(self):
        import tempfile, os
        with tempfile.TemporaryDirectory() as d:
            p1 = config.archive_db(d)
            p2 = config.archive_db(d)          # 同库第二次：应复用同一份
            self.assertIsNotNone(p1)
            self.assertEqual(p1, p2)
            files = os.listdir(os.path.join(d, "dbs"))
            self.assertEqual(len(files), 1)
            self.assertIn(config.SOFTWARE_DB_ID, files[0])


if __name__ == "__main__":
    unittest.main()
