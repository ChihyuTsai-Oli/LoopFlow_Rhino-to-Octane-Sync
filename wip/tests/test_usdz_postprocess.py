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
    match_layer_for_material_prim,
    payload_name_for_final,
    promote_material_bindings_usda,
    promote_material_bindings_usdz,
    rewrite_material_prims,
    stable_material_prim,
    strip_material_tail,
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
        self.assertEqual(models_path(root).name, "R2O.usdz")
        self.assertEqual(models_path(root).parent.name, "models")
        self.assertEqual(pending_path_for(models_path(root)).name, "R2O_pending.usdz")
        self.assertEqual(payload_name_for_final(models_path(root)), "R2O.usda")

    def test_payload_renamed_to_final_stem(self):
        with tempfile.TemporaryDirectory() as tmp:
            pending = Path(tmp) / "R2O_pending.usdz"
            _write_usdz(pending, _SAMPLE_USDA, inner_name="R2O_pending.usda")
            r = promote_material_bindings_usdz(pending, payload_name="R2O.usda")
            self.assertTrue(r.ok, r.message)
            with zipfile.ZipFile(pending) as zf:
                names = zf.namelist()
            self.assertIn("R2O.usda", names)
            self.assertNotIn("R2O_pending.usda", names)


_GUIDED = """#usda 1.0
def Xform "Rhino"
{
    def Xform "Geometry"
    {
        def Xform "Metal_Black"
        {
            def Xform "M3D"
            {
                def Mesh "mesh0"
                {
                    rel material:binding = </Rhino/Materials/material_M3D__Metal_Black_BC2B9652_54A6_4FD0_E1AEDAD8>
                }
            }
        }
        def Xform "Mirror_Black"
        {
            def Xform "Mid"
            {
                def Xform "M3D"
                {
                    def Mesh "mesh1"
                    {
                        rel material:binding = </Rhino/Materials/material_M3D__Mid__Mirror_Black_2223B289_B6B3_40AF_E1AEDAD8>
                    }
                }
            }
        }
    }
    def "Materials"
    {
        def Material "material_M3D__Metal_Black_BC2B9652_54A6_4FD0_E1AEDAD8"
        {
            token outputs:surface.connect = </Rhino/Materials/material_M3D__Metal_Black_BC2B9652_54A6_4FD0_E1AEDAD8/shader0.outputs:surface>
            def Shader "shader0"
            {
                uniform token info:id = "UsdPreviewSurface"
            }
        }
        def Material "material_M3D__Mid__Mirror_Black_2223B289_B6B3_40AF_E1AEDAD8"
        {
            token outputs:surface.connect = </Rhino/Materials/material_M3D__Mid__Mirror_Black_2223B289_B6B3_40AF_E1AEDAD8/shader1.outputs:surface>
            def Shader "shader1"
            {
                uniform token info:id = "UsdPreviewSurface"
            }
        }
        def Material "material_Other_AAAA1111_BBBB_CCCC_DDDDDDDD"
        {
            token outputs:surface.connect = </Rhino/Materials/material_Other_AAAA1111_BBBB_CCCC_DDDDDDDD/shader2.outputs:surface>
            def Shader "shader2"
            {
                uniform token info:id = "UsdPreviewSurface"
            }
        }
    }
}
"""


class MaterialIdentityTests(unittest.TestCase):
    def test_longest_layer_prefix_wins(self):
        layers = {
            "M3D": "Root",
            "M3D::2_Mid": "Mid",
            "M3D::2_Mid::Metal_Black": "Metal_Black",
            "M3D::2_Mid::_Wall_White": "Wall White",
        }
        leaf = "material_M3D__2_Mid__Metal_Black_BC2B9652_54A6_4FD0_E1AEDAD8"
        wall = "material_M3D__2_Mid___Wall_White_BB535418_795_4D0B_E1AEDAD8"
        self.assertEqual(match_layer_for_material_prim(leaf, layers), "M3D::2_Mid::Metal_Black")
        self.assertEqual(match_layer_for_material_prim(wall, layers), "M3D::2_Mid::_Wall_White")
        self.assertIsNone(match_layer_for_material_prim("material_Other_AAAA", layers))

    def test_blank_name_uses_layer_path_and_same_name_merges(self):
        key_a, prim_a = stable_material_prim("Paint", "M3D::Metal_Black")
        key_b, prim_b = stable_material_prim("Paint", "M3D::Mid::Mirror_Black")
        self.assertEqual(key_a, key_b)
        self.assertEqual(prim_a, prim_b)
        self.assertEqual(prim_a, "material_Paint")
        _key, blank = stable_material_prim("", "M3D::2_Mid::Glass")
        self.assertEqual(blank, "material_M3D_2_Mid_Glass")
        _key, numbered = stable_material_prim("01", "M3D::A")
        self.assertEqual(numbered, "material_m_01")

    def test_rewrite_merges_same_material_and_keeps_unknown(self):
        layers = {
            "M3D": "Root",
            "M3D::Metal_Black": "Paint",
            "M3D::Mid::Mirror_Black": "Paint",
        }
        text, changed = rewrite_material_prims(_GUIDED, layers)
        self.assertEqual(changed, 3)
        self.assertEqual(text.count('def Material "material_Paint"'), 1)
        self.assertNotIn("shader0", text)
        self.assertNotIn("shader1", text)
        self.assertNotIn("shader2", text)
        self.assertEqual(text.count('def Shader "surface"'), 2)
        self.assertIn("/Rhino/Materials/material_Paint/surface.outputs:surface", text)
        self.assertNotIn("material_M3D__Metal_Black_", text)
        self.assertNotIn("material_M3D__Mid__Mirror_Black_", text)
        self.assertEqual(text.count("/Rhino/Materials/material_Paint>"), 2)
        self.assertIn('def Material "material_Other"', text)
        self.assertNotIn("material_Other_AAAA1111", text)

    def test_usdz_promotes_then_renames(self):
        layers = {
            "M3D::Metal_Black": "Paint",
            "M3D::Mid::Mirror_Black": "Paint",
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / MODELS_FILE_NAME
            _write_usdz(path, _GUIDED, inner_name="R2O.usda")
            result = promote_material_bindings_usdz(path, layer_materials=layers)
            self.assertTrue(result.ok, result.message)
            self.assertEqual(result.data["renamed"], 3)
            raw = zipfile.ZipFile(path).read("R2O.usda").decode("utf-8")
        self.assertNotIn('def Mesh "mesh0"\n                {\n                    rel material:binding', raw)
        self.assertIn('rel material:binding = </Rhino/Materials/material_Paint>', raw)
        self.assertEqual(raw.count('def Material "material_Paint"'), 1)


_TAILED = """#usda 1.0
def Xform "Rhino"
{
    def Mesh "mesh0"
    {
        rel material:binding = </Rhino/Materials/material_M3D__2_Mid___Wall_White_BB535418_795_4D0B_E1AEDAD8>
    }
    def Mesh "mesh1"
    {
        rel material:binding = </Rhino/Materials/material_M3D__Metal_Black_AAAA1111_BBBB_CCCC_DDDDDDDD>
    }
    def Mesh "mesh2"
    {
        rel material:binding = </Rhino/Materials/material_M3D__Metal_Black_11111111_2222_333_44444444>
    }
    def "Materials"
    {
        def Material "material_M3D__2_Mid___Wall_White_BB535418_795_4D0B_E1AEDAD8"
        {
            token outputs:surface.connect = </Rhino/Materials/material_M3D__2_Mid___Wall_White_BB535418_795_4D0B_E1AEDAD8/shader0.outputs:surface>
            def Shader "shader0"
            {
                uniform token info:id = "UsdPreviewSurface"
            }
        }
        def Material "material_M3D__Metal_Black_AAAA1111_BBBB_CCCC_DDDDDDDD"
        {
            token outputs:surface.connect = </Rhino/Materials/material_M3D__Metal_Black_AAAA1111_BBBB_CCCC_DDDDDDDD/shader4.outputs:surface>
            def Shader "shader4"
            {
                uniform token info:id = "UsdPreviewSurface"
            }
        }
        def Material "material_M3D__Metal_Black_11111111_2222_333_44444444"
        {
            token outputs:surface.connect = </Rhino/Materials/material_M3D__Metal_Black_11111111_2222_333_44444444/shader9.outputs:surface>
            def Shader "shader9"
            {
                uniform token info:id = "UsdPreviewSurface"
            }
        }
    }
}
"""


class MaterialTailTests(unittest.TestCase):
    def test_short_hex_group_is_a_tail(self):
        name = "material_M3D__2_Mid___Wall_White_BB535418_795_4D0B_E1AEDAD8"
        self.assertEqual(strip_material_tail(name), "material_M3D__2_Mid___Wall_White")
        self.assertEqual(strip_material_tail("material_Paint"), "material_Paint")

    def test_strip_tail_without_layer_map(self):
        text, changed = rewrite_material_prims(_TAILED, None)
        self.assertEqual(changed, 3)
        self.assertIn('def Material "material_M3D__2_Mid___Wall_White"', text)
        self.assertEqual(text.count('def Material "material_M3D__Metal_Black"'), 1)
        self.assertNotIn("shader0", text)
        self.assertNotIn("shader4", text)
        self.assertNotIn("shader9", text)
        self.assertNotIn("795", text)
        self.assertNotIn("E1AEDAD8", text)
        self.assertEqual(text.count('def Shader "surface"'), 2)
        self.assertEqual(text.count("/Rhino/Materials/material_M3D__Metal_Black>"), 2)
        self.assertIn(
            "/Rhino/Materials/material_M3D__2_Mid___Wall_White/surface.outputs:surface",
            text,
        )


if __name__ == "__main__":
    unittest.main()
