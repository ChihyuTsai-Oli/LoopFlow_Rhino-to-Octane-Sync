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

from foundation.user_assets import STAMP_NAME, copy_tree, sync_user_assets


class UserAssetsTests(unittest.TestCase):
    def test_copy_tree_skips_existing_keep_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "src"
            dest = Path(tmp) / "dest"
            src.mkdir()
            (src / "R2O_Camera.lua").write_text("-- cam", encoding="utf-8")
            (src / "keep.txt").write_text("official", encoding="utf-8")
            dest.mkdir()
            (dest / "keep.txt").write_text("user", encoding="utf-8")
            copied = copy_tree(src, dest, frozenset({"keep.txt"}))
            self.assertTrue(copied)
            self.assertEqual((dest / "R2O_Camera.lua").read_text(encoding="utf-8"), "-- cam")
            self.assertEqual((dest / "keep.txt").read_text(encoding="utf-8"), "user")

    def test_sync_copies_lua(self):
        with tempfile.TemporaryDirectory() as tmp:
            src_root = Path(tmp) / "pkg" / "libs" / "x" / "src"
            templates = Path(tmp) / "pkg" / "templates"
            payload = templates / "lua"
            payload.mkdir(parents=True)
            (payload / "R2O_Camera.lua").write_text("-- cam", encoding="utf-8")
            (templates / STAMP_NAME).write_text("2.0.0\n", encoding="utf-8")
            dest = Path(tmp) / "out" / "lua"
            from foundation.user_assets import can_sync_user_assets

            self.assertTrue(can_sync_user_assets(src_root))
            first = sync_user_assets(src_root=src_root, dest=dest, open_folder=False)
            self.assertTrue(first)
            self.assertTrue((dest / "R2O_Camera.lua").is_file())
            second = sync_user_assets(src_root=src_root, dest=dest, open_folder=False)
            self.assertFalse(second)

    def test_sync_noop_without_templates(self):
        with tempfile.TemporaryDirectory() as tmp:
            src_root = Path(tmp) / "src"
            src_root.mkdir()
            dest = Path(tmp) / "out" / "lua"
            from foundation.user_assets import can_sync_user_assets

            self.assertFalse(can_sync_user_assets(src_root))
            self.assertFalse(sync_user_assets(src_root=src_root, dest=dest, open_folder=False))


    def test_sync_replaces_folder_on_new_stamp(self):
        with tempfile.TemporaryDirectory() as tmp:
            src_root = Path(tmp) / "pkg" / "libs" / "x" / "src"
            templates = Path(tmp) / "pkg" / "templates"
            payload = templates / "lua"
            payload.mkdir(parents=True)
            (payload / "R2O_Camera.lua").write_text("-- cam", encoding="utf-8")
            (payload / "R2O_Shortcuts.txt").write_text("official", encoding="utf-8")
            (templates / STAMP_NAME).write_text("2.0.0\n", encoding="utf-8")
            dest = Path(tmp) / "out" / "lua"
            dest.mkdir(parents=True)
            (dest / "leftover.lua").write_text("-- old", encoding="utf-8")
            (dest / "R2O_Shortcuts.txt").write_text("user", encoding="utf-8")
            first = sync_user_assets(src_root=src_root, dest=dest, open_folder=False)
            self.assertTrue(first)
            self.assertFalse((dest / "leftover.lua").exists())
            self.assertEqual((dest / "R2O_Shortcuts.txt").read_text(encoding="utf-8"), "official")
            (dest / "extra.lua").write_text("-- extra", encoding="utf-8")
            same = sync_user_assets(src_root=src_root, dest=dest, open_folder=False)
            self.assertFalse(same)
            self.assertTrue((dest / "extra.lua").is_file())
            (payload / "R2O_Camera.lua").write_text("-- new", encoding="utf-8")
            (payload / "R2O_Shortcuts.txt").write_text("packaged", encoding="utf-8")
            (templates / STAMP_NAME).write_text("2.0.1\n", encoding="utf-8")
            upgraded = sync_user_assets(src_root=src_root, dest=dest, open_folder=False)
            self.assertTrue(upgraded)
            self.assertFalse((dest / "extra.lua").exists())
            self.assertEqual((dest / "R2O_Camera.lua").read_text(encoding="utf-8"), "-- new")
            self.assertEqual((dest / "R2O_Shortcuts.txt").read_text(encoding="utf-8"), "packaged")
            self.assertEqual((dest / STAMP_NAME).read_text(encoding="utf-8").strip(), "2.0.1")


if __name__ == "__main__":
    unittest.main()
