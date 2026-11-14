# -*- coding: utf-8 -*-
"""Rhino _-Export 一律走 TEMP ASCII 檔。"""
from __future__ import annotations

import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from foundation.export_cmd import (
    pack_usda_as_usdz,
    rhino_export_target,
    usda_inner_name,
    use_rhino9_runtime,
)


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

    def test_rhino9_runtime_starts_at_major_9(self):
        self.assertFalse(use_rhino9_runtime(8))
        self.assertTrue(use_rhino9_runtime(9))
        self.assertTrue(use_rhino9_runtime(10))
        self.assertFalse(use_rhino9_runtime(None))

    def test_pack_usda_keeps_formal_inner_name(self):
        sample = "#usda 1.0\ndef Xform \"World\" {\n    def Xform \"Geometry\" {\n    }\n}\n"
        self.assertGreaterEqual(len(sample.encode("utf-8")), 32)
        with tempfile.TemporaryDirectory() as tmp:
            usda = Path(tmp) / "R2O_r1.usda"
            usda.write_text(sample, encoding="utf-8")
            usdz = Path(tmp) / "R2O_r1.usdz"
            inner = usda_inner_name("R2O.usdz", Path(tmp) / "R2O_pending.usdz")
            pack_usda_as_usdz(usda, usdz, inner)
            self.assertEqual(inner, "R2O.usda")
            with zipfile.ZipFile(usdz) as archive:
                self.assertEqual(archive.namelist(), ["R2O.usda"])
                self.assertTrue(archive.read("R2O.usda").startswith(b"#usda"))
                info = archive.getinfo("R2O.usda")
                self.assertEqual(info.compress_type, zipfile.ZIP_STORED)

    def test_objects_inner_name_uses_timestamp_stem(self):
        name = usda_inner_name(
            "R2O_Objects_260829_203329.usdz",
            Path("R2O_Objects_260829_203329_pending.usdz"),
        )
        self.assertEqual(name, "R2O_Objects_260829_203329.usda")

    def test_pack_rejects_short_usda(self):
        with tempfile.TemporaryDirectory() as tmp:
            usda = Path(tmp) / "short.usda"
            usda.write_text("#usda 1.0\n", encoding="utf-8")
            usdz = Path(tmp) / "short.usdz"
            with self.assertRaises(OSError):
                pack_usda_as_usdz(usda, usdz, "short.usda")


if __name__ == "__main__":
    unittest.main()
