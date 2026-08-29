# -*- coding: utf-8 -*-
"""foundation 純 Python 測試。"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from foundation.atomic import atomic_publish_json, atomic_publish_text
from foundation.log import append_log
from foundation.paths import (
    CAMERA_FILE_NAME,
    PRODUCT_DIR_NAME,
    camera_path,
    config_root_for_document,
    ensure_config_layout,
    models_path,
    pending_path_for,
    require_saved_document_path,
)
from foundation.result import Result


class FoundationResultTests(unittest.TestCase):
    def test_success_fail_blocked(self):
        self.assertTrue(Result.success("ok").ok)
        self.assertEqual(Result.fail("x", stage="s").status, "fail")
        self.assertEqual(Result.blocked("Save the Rhino file first").status, "blocked")
        self.assertFalse(Result.cancel().ok)


class FoundationPathTests(unittest.TestCase):
    def test_require_saved(self):
        self.assertEqual(require_saved_document_path(None).status, "blocked")
        self.assertEqual(require_saved_document_path("").status, "blocked")
        with tempfile.TemporaryDirectory() as tmp:
            doc = Path(tmp) / "demo.3dm"
            doc.write_bytes(b"x")
            r = require_saved_document_path(str(doc))
            self.assertTrue(r.ok)
            root = config_root_for_document(doc)
            self.assertEqual(root.name, PRODUCT_DIR_NAME)
            self.assertEqual(root.parent.name, "_LoopFlow_Config")
            self.assertEqual(camera_path(root).name, CAMERA_FILE_NAME)
            self.assertEqual(models_path(root).name, "models.usdz")

    def test_unicode_work_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / "Dropbox (個人)" / "WIP"
            work.mkdir(parents=True)
            doc = work / "案.3dm"
            doc.write_bytes(b"x")
            root = config_root_for_document(doc)
            self.assertIn("個人", str(root))
            self.assertTrue(str(root).endswith(str(Path("_LoopFlow_Config") / PRODUCT_DIR_NAME)))

    def test_pending_name(self):
        p = Path(r"C:\proj\_LoopFlow_Config\loopflow_R2O\live\camera.json")
        self.assertEqual(pending_path_for(p).name, "camera_pending.json")

    def test_ensure_layout(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = ensure_config_layout(Path(tmp) / "cfg")
            self.assertTrue((root / "live").is_dir())
            self.assertTrue((root / "models").is_dir())


class FoundationAtomicTests(unittest.TestCase):
    def test_publish_leaves_last_good_on_validate_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            final = Path(tmp) / "camera.json"
            final.write_text('{"keep": true}\n', encoding="utf-8")

            def bad_validate(_path: Path):
                return "fake validate fail"

            r = atomic_publish_text(final, '{"new": true}\n', validate=bad_validate)
            self.assertFalse(r.ok)
            self.assertEqual(r.stage, "validate")
            self.assertEqual(json.loads(final.read_text(encoding="utf-8"))["keep"], True)
            self.assertFalse(pending_path_for(final).exists())

    def test_publish_replaces_atomically(self):
        with tempfile.TemporaryDirectory() as tmp:
            final = Path(tmp) / "camera.json"
            r = atomic_publish_json(final, {"schema_version": 1})
            self.assertTrue(r.ok, r.message)
            loaded = json.loads(final.read_text(encoding="utf-8"))
            self.assertEqual(loaded["schema_version"], 1)
            self.assertFalse(pending_path_for(final).exists())


class FoundationLogTests(unittest.TestCase):
    def test_append_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "loopflow_R2O"
            r = append_log(root, "hello camera")
            self.assertTrue(r.ok, r.message)
            text = Path(r.data).read_text(encoding="utf-8")
            self.assertIn("hello camera", text)
            self.assertIn("[INFO]", text)
            self.assertTrue(text.endswith("\n"))
            self.assertIn("r2o.log", str(r.data))


if __name__ == "__main__":
    unittest.main()
