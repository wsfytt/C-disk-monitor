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
        # 曾经被 "edge" 命中，误判成 Edge 浏览器
        self.assertIsNone(config.identify(
            r"C:\Users\x\AppData\Local\CrewChiefV4\Sounds\voice\acknowledge"))
        # 曾经被 "pip" 命中
        self.assertIsNone(config.identify(
            r"C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2024\design library\routing\piping"))
        # 曾经被 "npm" 命中
        self.assertIsNone(config.identify(
            r"C:\Users\x\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\pnpm"))
        # 曾经被 "go" 命中
        self.assertIsNone(config.identify(r"C:\ProgramData\leigod_NN_7002"))

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
        prev = self._snap(100 * MB, [{"path": r"C:\A", "name": "A", "size": 10 * MB,
                                      "software_name": "A软件"}])
        curr = self._snap(130 * MB, [{"path": r"C:\A", "name": "A", "size": 30 * MB,
                                      "software_name": "A软件"}])
        diff = reporter.build_diff(prev, curr)
        self.assertEqual(diff["disk_used_change"], 30 * MB)
        self.assertEqual(len(diff["grew"]), 1)
        self.assertEqual(diff["grew"][0]["change"], 20 * MB)
        # A 是已识别的顶层目录，已解释比例 = 20MB / 30MB
        self.assertAlmostEqual(diff["explained_ratio"], 20 / 30, places=3)

    def test_explained_ratio_dedup(self):
        # 父子目录重复计数：NetEase 和 NetEase\CloudMusic 是同一份增长，不能被算两遍
        prev = self._snap(100 * MB, [
            {"path": r"C:\NetEase", "name": "NetEase", "size": 10 * MB, "software_name": "网易软件目录"},
            {"path": r"C:\NetEase\CloudMusic", "name": "CloudMusic", "size": 8 * MB, "software_name": "网易云音乐"},
        ])
        curr = self._snap(130 * MB, [
            {"path": r"C:\NetEase", "name": "NetEase", "size": 30 * MB, "software_name": "网易软件目录"},
            {"path": r"C:\NetEase\CloudMusic", "name": "CloudMusic", "size": 28 * MB, "software_name": "网易云音乐"},
        ])
        diff = reporter.build_diff(prev, curr)
        # 顶层 NetEase 增长 20MB，子目录 CloudMusic 增长 20MB（被父目录覆盖），去重后只算一次
        self.assertEqual(diff["total_growth"], 40 * MB)
        self.assertAlmostEqual(diff["explained_ratio"], 20 / 30, places=3)

    def test_explained_ratio_ignores_unrecognized(self):
        # 未识别文件夹的增长不计入已解释比例分子
        prev = self._snap(100 * MB, [{"path": r"C:\A", "name": "A", "size": 10 * MB}])
        curr = self._snap(130 * MB, [{"path": r"C:\A", "name": "A", "size": 30 * MB}])
        diff = reporter.build_diff(prev, curr)
        self.assertEqual(diff["explained_ratio"], 0.0)

    def test_shrink_and_new(self):
        prev = self._snap(200 * MB, [{"path": r"C:\B", "name": "B", "size": 50 * MB}])
        curr = self._snap(180 * MB, [{"path": r"C:\B", "name": "B", "size": 40 * MB},
                                     {"path": r"C:\C", "name": "C", "size": 5 * MB}])
        diff = reporter.build_diff(prev, curr)
        self.assertEqual(diff["shrank"][0]["change"], -10 * MB)
        self.assertEqual(diff["grew"][0]["path"], r"C:\C")


if __name__ == "__main__":
    unittest.main()
