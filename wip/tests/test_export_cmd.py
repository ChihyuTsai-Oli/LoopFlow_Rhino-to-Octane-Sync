# -*- coding: utf-8 -*-
"""Rhino _-Export 一律走 TEMP ASCII 檔。"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from foundation.export_cmd import rhino_export_target


class ExportCmdTests(unittest.TestCase):
    def test_always_temp_uses_final_stem(self):
        with tempfile.TemporaryDirectory() as tmp:
            pending = Path(tmp) / "Dropbox (個人)" / "R2O_pending.usdz"
            temp_dir = Path(tmp) / "temp_ascii"
            cmd, copy_to = rhino_export_target(
                pending,
                export_name="R2O.usdz",
                temp_dir=temp_dir,
            )
            self.assertEqual(copy_to, pending)
            self.assertEqual(Path(cmd), temp_dir / "R2O.usdz")
            self.assertNotIn("(", cmd)
            self.assertNotIn("pending", Path(cmd).name)
            cmd.encode("ascii")

    def test_retry_attempt_uses_suffix(self):
        with tempfile.TemporaryDirectory() as tmp:
            pending = Path(tmp) / "R2O_pending.usdz"
            temp_dir = Path(tmp) / "temp_ascii"
            cmd, copy_to = rhino_export_target(
                pending,
                export_name="R2O.usdz",
                attempt=1,
                temp_dir=temp_dir,
            )
            self.assertEqual(copy_to, pending)
            self.assertEqual(Path(cmd).name, "R2O_r1.usdz")

    def test_pending_stem_strips_pending(self):
        with tempfile.TemporaryDirectory() as tmp:
            pending = Path(tmp) / "R2O_pending.usdz"
            temp_dir = Path(tmp) / "temp"
            cmd, _copy = rhino_export_target(pending, temp_dir=temp_dir)
            self.assertEqual(Path(cmd).name, "R2O.usdz")

    def test_unicode_filename_falls_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            pending = Path(tmp) / "椅子_pending.usd"
            temp_dir = Path(tmp) / "temp_ascii"
            cmd, copy_to = rhino_export_target(pending, temp_dir=temp_dir)
            self.assertEqual(copy_to, pending)
            self.assertEqual(Path(cmd).name, "r2o_export.usd")
            self.assertNotIn("椅子", cmd)

    def test_objects_timestamp_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            pending = Path(tmp) / "R2O_Objects_260829_203329_pending.usdz"
            temp_dir = Path(tmp) / "temp"
            cmd, _copy = rhino_export_target(
                pending,
                export_name="R2O_Objects_260829_203329.usdz",
                temp_dir=temp_dir,
            )
            self.assertEqual(Path(cmd).name, "R2O_Objects_260829_203329.usdz")


if __name__ == "__main__":
    unittest.main()
