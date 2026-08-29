# -*- coding: utf-8 -*-
"""Rhino _-Export 指令路徑：8.3 或 TEMP，避開括號與中文。"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from foundation.export_cmd import TEMP_EXPORT_NAME, rhino_export_target


class ExportCmdTests(unittest.TestCase):
    def test_short_ascii_parent_writes_in_place(self):
        with tempfile.TemporaryDirectory() as tmp:
            pending = Path(tmp) / "models_pending.usdz"
            cmd, copy_to = rhino_export_target(
                pending,
                short_path_fn=lambda _p: r"C:\DROPBO~1\WIP\models",
            )
            self.assertIsNone(copy_to)
            self.assertEqual(cmd, r"C:\DROPBO~1\WIP\models\models_pending.usdz")
            self.assertNotIn("(", cmd)
            cmd.encode("ascii")

    def test_missing_short_path_uses_temp(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / "Dropbox (個人)" / "models"
            pending = work / "models_pending.usdz"
            temp_dir = Path(tmp) / "temp_ascii"
            cmd, copy_to = rhino_export_target(
                pending,
                short_path_fn=lambda _p: None,
                temp_dir=temp_dir,
            )
            self.assertEqual(copy_to, pending)
            self.assertEqual(Path(cmd), temp_dir / TEMP_EXPORT_NAME)
            self.assertNotIn("個人", cmd)
            self.assertNotIn("(", cmd)
            cmd.encode("ascii")

    def test_short_path_with_parens_falls_back_to_temp(self):
        with tempfile.TemporaryDirectory() as tmp:
            pending = Path(tmp) / "Dropbox (個人)" / "models_pending.usdz"
            temp_dir = Path(tmp) / "temp_ascii"
            cmd, copy_to = rhino_export_target(
                pending,
                short_path_fn=lambda _p: r"C:\Dropbox (x)\models",
                temp_dir=temp_dir,
            )
            self.assertEqual(copy_to, pending)
            self.assertEqual(Path(cmd).name, TEMP_EXPORT_NAME)
            self.assertNotIn("(", cmd)

    def test_unicode_short_path_falls_back_to_temp(self):
        with tempfile.TemporaryDirectory() as tmp:
            pending = Path(tmp) / "models_pending.usdz"
            temp_dir = Path(tmp) / "temp_ascii"
            cmd, copy_to = rhino_export_target(
                pending,
                short_path_fn=lambda _p: r"C:\Dropbox (個人)\models",
                temp_dir=temp_dir,
            )
            self.assertEqual(copy_to, pending)
            self.assertNotIn("個人", cmd)


if __name__ == "__main__":
    unittest.main()
