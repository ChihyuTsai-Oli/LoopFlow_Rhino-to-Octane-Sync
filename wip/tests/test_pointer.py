# -*- coding: utf-8 -*-
"""XF-ED-04 本機專案指標。"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from foundation.pointer import (
    POINTER_PRODUCT,
    build_pointer_payload,
    pointer_path,
    read_current_project_pointer,
    validate_pointer_payload,
    windows_short_path,
    write_current_project_pointer,
)


class PointerTests(unittest.TestCase):
    def test_payload_shape(self):
        payload = build_pointer_payload(
            config_root=r"E:\Dropbox (個人)\WIP\_LoopFlow_Config\loopflow_R2O",
            document_path=r"E:\Dropbox (個人)\WIP\案.3dm",
        )
        self.assertIsNone(validate_pointer_payload(payload))
        self.assertEqual(payload["product"], POINTER_PRODUCT)
        self.assertIn("個人", payload["config_root"])

    def test_write_and_read_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            old = os.environ.get("APPDATA")
            os.environ["APPDATA"] = tmp
            try:
                root = Path(tmp) / "proj" / "_LoopFlow_Config" / "loopflow_R2O"
                doc = Path(tmp) / "proj" / "demo.3dm"
                w = write_current_project_pointer(root, doc)
                self.assertTrue(w.ok, w.message)
                expected = pointer_path()
                self.assertEqual(expected, Path(tmp) / "LoopFlow" / "R2O" / "current_project.json")
                self.assertTrue(expected.is_file())
                r = read_current_project_pointer()
                self.assertTrue(r.ok, r.message)
                self.assertEqual(Path(r.data["config_root"]), root)
                loaded = json.loads(expected.read_text(encoding="utf-8"))
                self.assertEqual(loaded["schema_version"], 1)
            finally:
                if old is None:
                    os.environ.pop("APPDATA", None)
                else:
                    os.environ["APPDATA"] = old

    def test_unicode_root_gets_ascii_short_path(self):
        if os.name != "nt":
            self.skipTest("Windows only")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Dropbox (個人)" / "_LoopFlow_Config" / "loopflow_R2O"
            root.mkdir(parents=True)
            short = windows_short_path(root)
            self.assertIsNotNone(short)
            self.assertTrue(short.isascii())
            payload = build_pointer_payload(config_root=root, document_path=root / "a.3dm")
            self.assertIn("config_root_short", payload)
            self.assertTrue(payload["config_root_short"].isascii())
