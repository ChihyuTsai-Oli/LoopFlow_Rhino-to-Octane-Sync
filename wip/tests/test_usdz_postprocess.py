# -*- coding: utf-8 -*-
"""USDZ 材質後處理自動測試（不依賴 Rhino／Octane）。"""
from __future__ import annotations

import io
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from foundation.atomic import atomic_publish_from_pending
from foundation.paths import MODELS_FILE_NAME, models_path, pending_path_for
from foundation.usdz_postprocess import (
    promote_material_bindings_usda,
    promote_material_bindings_usdz,
    validate_usdz_file,
)

_SAMPLE_USDA = """#usda 1.0
def Xform "Rhino"
{
    def Xform "Geometry"
    {
        def Xform "Wall"
        {
            def Mesh "mesh_0"
            {
                rel material:binding = </Rhino/Looks/Paint>
            }
            def Mesh "mesh_1"
            {
                rel material:binding = </Rhino/Looks/Paint>
            }
        }
    }
}
"""


def _write_usdz(path: Path, usda: str, inner_name: str = "model.usda") -> None:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as zf:
        zf.writestr(inner_name, usda.encode("utf-8"))
        zf.writestr("dummy.bin", b"xx")
    path.write_bytes(buf.getvalue())


class UsdzPostprocessTests(unittest.TestCase):
    def test_promote_shared_mesh_binding_to_xform(self):
        text, count = promote_material_bindings_usda(_SAMPLE_USDA)
        self.assertEqual(count, 1)
        self.assertIn('def Xform "Wall"', text)
        wall_idx = text.find('def Xform "Wall"')
        mesh_idx = text.find('def Mesh "mesh_0"')
        bind = "rel material:binding = </Rhino/Looks/Paint>"
        self.assertGreater(text.find(bind, wall_idx, mesh_idx), 0)
        mesh_block = text[mesh_idx:]
        self.assertNotIn("rel material:binding", mesh_block)

    def test_mixed_bindings_not_promoted(self):
        usda = """#usda 1.0
def Xform "Wall"
{
    def Mesh "mesh_0"
    {
        rel material:binding = </Rhino/Looks/Paint>
    }
    def Mesh "mesh_1"
    {
        rel material:binding = </Rhino/Looks/Wood>
    }
}
"""
        text, count = promote_material_bindings_usda(usda)
        self.assertEqual(count, 0)
        self.assertIn("</Rhino/Looks/Paint>", text)
        self.assertIn("</Rhino/Looks/Wood>", text)
        wall_bind = text.split('def Mesh')[0]
        self.assertNotIn("rel material:binding", wall_bind)

    def test_usdz_roundtrip_and_validate(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / MODELS_FILE_NAME
            _write_usdz(path, _SAMPLE_USDA)
            self.assertIsNone(validate_usdz_file(path))
            result = promote_material_bindings_usdz(path)
            self.assertTrue(result.ok, result.message)
            self.assertEqual(result.data["promoted"], 1)
            self.assertIsNone(validate_usdz_file(path))

    def test_missing_usda_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.usdz"
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as zf:
                zf.writestr("only.usdc", b"not ascii usd")
            path.write_bytes(buf.getvalue())
            err = validate_usdz_file(path)
            self.assertIsNotNone(err)
            result = promote_material_bindings_usdz(path)
            self.assertFalse(result.ok)

    def test_atomic_from_pending_keeps_last_good_on_validate_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            final = Path(tmp) / MODELS_FILE_NAME
            _write_usdz(final, _SAMPLE_USDA)
            pending = pending_path_for(final)
            pending.write_bytes(b"not-a-zip")

            def bad(_path: Path):
                return "fake usdz fail"

            r = atomic_publish_from_pending(final, pending_path=pending, validate=bad)
            self.assertFalse(r.ok)
            self.assertEqual(r.stage, "validate")
            self.assertTrue(final.is_file())
            self.assertGreater(final.stat().st_size, 32)
            self.assertFalse(pending.exists())

    def test_models_path_name(self):
        root = Path(r"C:\proj\_LoopFlow_Config\loopflow_R2O")
        self.assertEqual(models_path(root).name, "R2O_Models.usdz")
        self.assertEqual(models_path(root).parent.name, "models")
        self.assertEqual(pending_path_for(models_path(root)).name, "R2O_Models_pending.usdz")


if __name__ == "__main__":
    unittest.main()
