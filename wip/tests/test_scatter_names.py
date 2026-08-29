# -*- coding: utf-8 -*-
"""Scatter 檔名：保留中文、碰撞硬停。"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from foundation.scatter_names import map_block_stems, scatter_file_stem


class ScatterNameTests(unittest.TestCase):
    def test_keeps_cjk(self):
        self.assertEqual(scatter_file_stem("李四的椅子"), "李四的椅子")

    def test_does_not_collapse_to_unnamed(self):
        a = scatter_file_stem("椅子A")
        b = scatter_file_stem("椅子B")
        self.assertNotEqual(a, b)
        self.assertTrue(a and b)

    def test_strips_illegal_windows_chars(self):
        self.assertEqual(scatter_file_stem(r"A:B/C"), "A_B_C")

    def test_empty_fails(self):
        r = map_block_stems(["  "])
        self.assertFalse(r.ok)
        self.assertEqual(r.stage, "scatter_names")

    def test_collision_fails_before_write(self):
        r = map_block_stems(["A/B", "A_B"])
        self.assertFalse(r.ok)
        self.assertIn("collision", r.message.lower())

    def test_unique_ok(self):
        r = map_block_stems(["Chair", "Sofa"])
        self.assertTrue(r.ok)
        self.assertEqual(r.data["Chair"], "Chair")
        self.assertEqual(r.data["Sofa"], "Sofa")


if __name__ == "__main__":
    unittest.main()
