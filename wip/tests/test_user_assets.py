# -*- coding: utf-8 -*-
"""拷 yak templates/lua 到「文件\\LoopFlow」。"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from foundation.user_assets import KEEP_NAMES, STAMP_NAME, copy_tree, sync_user_assets


class UserAssetsTests(unittest.TestCase):
    def test_copy_tree_keeps_shortcuts(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "src"
            dest = Path(tmp) / "dest"
            src.mkdir()
            (src / "R2O_Camera.lua").write_text("-- cam", encoding="utf-8")
            (src / "R2O_Shortcuts.txt").write_text("official", encoding="utf-8")
            dest.mkdir()
            (dest / "R2O_Shortcuts.txt").write_text("user", encoding="utf-8")
            copied = copy_tree(src, dest, KEEP_NAMES)
            self.assertTrue(copied)
            self.assertEqual((dest / "R2O_Camera.lua").read_text(encoding="utf-8"), "-- cam")
            self.assertEqual((dest / "R2O_Shortcuts.txt").read_text(encoding="utf-8"), "user")

    def test_sync_copies_lua(self):
        with tempfile.TemporaryDirectory() as tmp:
            src_root = Path(tmp) / "pkg" / "libs" / "x" / "src"
            templates = Path(tmp) / "pkg" / "templates"
            payload = templates / "lua"
            payload.mkdir(parents=True)
            (payload / "R2O_Camera.lua").write_text("-- cam", encoding="utf-8")
            (templates / STAMP_NAME).write_text("0.1.1\n", encoding="utf-8")
            dest = Path(tmp) / "out" / "lua"
            first = sync_user_assets(src_root=src_root, dest=dest, open_folder=False)
            self.assertTrue(first)
            self.assertTrue((dest / "R2O_Camera.lua").is_file())
            second = sync_user_assets(src_root=src_root, dest=dest, open_folder=False)
            self.assertFalse(second)


if __name__ == "__main__":
    unittest.main()
