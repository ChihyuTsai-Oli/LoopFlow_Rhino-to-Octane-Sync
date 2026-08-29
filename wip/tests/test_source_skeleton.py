# -*- coding: utf-8 -*-
"""來源骨架自動檢查（不依賴 Rhino／Octane GUI）。"""
from __future__ import annotations

import compileall
import py_compile
import sys
import unittest
from pathlib import Path

WIP = Path(__file__).resolve().parents[1]
SRC = WIP / "src"
ENTRYPOINTS = SRC / "rhino" / "entrypoints"
OCTANE_LUA = SRC / "octane" / "entrypoints"

REQUIRED_RHINO = (
    "ROCamera.py",
    "ROCameraPush.py",
    "ROPoint.py",
    "ROModels.py",
    "ROObjects.py",
    "ROOpen.py",
)
REQUIRED_LUA = (
    "R2O_Camera.lua",
    "R2O_Point.lua",
    "R2O_Open.lua",
    "__Open_Shortcuts.lua",
    "__Setup_Shortcuts.lua",
    "Auto_Align_Nodes.lua",
    "Auto_Convert_StdSurf_to_Universal.lua",
    "Auto_PBR_Switch_UV.lua",
    "Auto_PBR_Universal.lua",
)
AUTHORING_LUA = (
    "Auto_Align_Nodes.lua",
    "Auto_Convert_StdSurf_to_Universal.lua",
    "Auto_PBR_Switch_UV.lua",
    "Auto_PBR_Universal.lua",
)

INSTALL_PATH_MARKER = r"McNeel\Rhinoceros\8.0\scripts\LoopFlow_R2O"


class SourceSkeletonTests(unittest.TestCase):
    def test_rhino_entrypoints_exist_and_compile(self):
        for name in REQUIRED_RHINO:
            path = ENTRYPOINTS / name
            self.assertTrue(path.is_file(), name)
            py_compile.compile(str(path), doraise=True)
            text = path.read_text(encoding="utf-8")
            self.assertIn("_prepare_src", text)
            self.assertIn("_isolate.py", text)
        self.assertTrue((ENTRYPOINTS / "_isolate.py").is_file())

    def test_foundation_compile(self):
        self.assertTrue(compileall.compile_dir(str(SRC / "foundation"), quiet=1))
        self.assertTrue(compileall.compile_dir(str(SRC / "rhino"), quiet=1))

    def test_octane_lua_present(self):
        for name in REQUIRED_LUA:
            self.assertTrue((OCTANE_LUA / name).is_file(), name)
        camera = (OCTANE_LUA / "R2O_Camera.lua").read_text(encoding="utf-8")
        self.assertNotIn("not implemented yet", camera.lower())
        self.assertNotIn("loadfile", camera)
        self.assertIn("current_project.json", camera)
        self.assertIn("camera.json", camera)
        self.assertIn("NT_CAM_THINLENS", camera)
        self.assertIn("Keep exactly one", camera)
        self.assertIn("config_root_short", camera)
        self.assertIn("Applied once", camera)
        self.assertIn("@shortcut Ctrl + Q", camera)
        self.assertNotIn("showWindow", camera)
        self.assertNotIn("dispatchGuiEvents", camera)
        self.assertNotIn("sleep_ms", camera)
        self.assertNotIn("void Sleep", camera)
        self.assertNotIn("TIMERPROC", camera)

        shortcuts_txt = (OCTANE_LUA / "R2O_Shortcuts.txt").read_text(encoding="utf-8")
        self.assertIn("R2O_Camera:", shortcuts_txt)
        active = "\n".join(
            ln for ln in shortcuts_txt.splitlines()
            if ln.strip() and not ln.lstrip().startswith("#")
        )
        self.assertIn("Auto_Align_Nodes:", active)
        self.assertIn("Auto_Convert_StdSurf_to_Universal:", active)
        self.assertIn("Auto_PBR_Switch_UV:", active)
        self.assertIn("Auto_PBR_Universal:", active)
        self.assertIn("1.x default", shortcuts_txt)

        for name in AUTHORING_LUA:
            auto = (OCTANE_LUA / name).read_text(encoding="utf-8")
            self.assertIn("@shortcut", auto, name)
            self.assertIn("R2O_Path.txt", auto, name)
        self.assertIn(
            "octane.gui",
            (OCTANE_LUA / "Auto_Align_Nodes.lua").read_text(encoding="utf-8"),
        )
        self.assertIn(
            "octane.gui",
            (OCTANE_LUA / "Auto_PBR_Universal.lua").read_text(encoding="utf-8"),
        )
        self.assertNotIn("octane.gui", camera)

        setup = (OCTANE_LUA / "__Setup_Shortcuts.lua").read_text(encoding="utf-8")
        self.assertIn("R2O_Shortcuts.txt", setup)
        self.assertIn("@shortcut", setup)
        self.assertNotIn(INSTALL_PATH_MARKER, setup)
        open_sc = (OCTANE_LUA / "__Open_Shortcuts.lua").read_text(encoding="utf-8")
        self.assertIn("R2O_Shortcuts.txt", open_sc)
        self.assertNotIn(INSTALL_PATH_MARKER, open_sc)

        point = (OCTANE_LUA / "R2O_Point.lua").read_text(encoding="utf-8")
        self.assertNotIn("not implemented yet", point.lower())
        self.assertNotIn("loadfile", point)
        self.assertIn("point.json", point)
        self.assertIn("NT_GEO_SCATTER", point)
        self.assertIn("A_TRANSFORMS", point)
        self.assertIn("getSceneGraph", point)
        self.assertIn("scatter(s) on the scene", point)
        self.assertIn("graphOwner = rootGraph", point)
        self.assertNotIn("octane.nodegraph.create", point)
        self.assertIn("config_root_short", point)
        self.assertIn("Applied once", point)
        self.assertIn("@shortcut", point)
        self.assertNotIn("Ctrl + Q", point)
        self.assertNotIn("showWindow", point)
        self.assertNotIn("dispatchGuiEvents", point)
        self.assertNotIn("octane.gui", point)

    def test_camera_command_mentions_perspective(self):
        text = (SRC / "rhino" / "commands" / "camera.py").read_text(encoding="utf-8")
        self.assertIn("IsPerspectiveProjection", text)
        self.assertIn("write_current_project_pointer", text)
        self.assertIn("CameraThrottleGate", text)

    def test_point_command_scans_r2o_prefix(self):
        text = (SRC / "rhino" / "commands" / "point.py").read_text(encoding="utf-8")
        self.assertIn("POINT_LAYER_PREFIX", text)
        self.assertIn("write_current_project_pointer", text)
        self.assertIn("identity_xform_at_point", text)
        self.assertIn("block_xform_from_rhino_matrix", text)

    def test_models_command_exports_usdz(self):
        text = (SRC / "rhino" / "commands" / "models.py").read_text(encoding="utf-8")
        self.assertIn("R2O.usdz", text)
        self.assertIn("promote_material_bindings_usdz", text)
        self.assertIn("atomic_publish_from_pending", text)
        self.assertIn("_-Export", text)
        self.assertNotIn("_-Save", text)
        self.assertIn("write_current_project_pointer", text)
        self.assertIn("doc.Modified", text)
        self.assertIn("pick_layer_path", text)
        self.assertIn("Exclude Token", text)
        self.assertIn("rhino_export_target", text)
        self.assertIn("DEFAULT_LAYER_EXCLUDE_TOKEN", text)
        self.assertNotIn("GetLayer", text)
        export_cmd = (SRC / "foundation" / "export_cmd.py").read_text(encoding="utf-8")
        self.assertNotIn("windows_short_path", export_cmd)
        self.assertIn("gettempdir", export_cmd)
        self.assertIn("export_name", export_cmd)
        picker = (SRC / "rhino" / "ui" / "layer_picker.py").read_text(encoding="utf-8")
        self.assertIn("pick_layer_path", picker)
        self.assertIn("TreeGridView", picker)

        entry = (ENTRYPOINTS / "ROModels.py").read_text(encoding="utf-8")
        self.assertIn("Close Octane and reopen", entry)
        self.assertIn("Reload mesh", entry)
        self.assertIn("Load new mesh", entry)
        self.assertNotIn("File > Replace", entry)

    def test_objects_command_exports_usdz(self):
        text = (SRC / "rhino" / "commands" / "objects.py").read_text(encoding="utf-8")
        self.assertIn("next_objects_path", text)
        self.assertIn("promote_material_bindings_usdz", text)
        self.assertIn("Select objects to export first", text)
        self.assertNotIn("_-Save", text)
        self.assertNotIn("MoveObject", text)
        self.assertNotIn("GetObjects", text)
        self.assertNotIn("map_block_stems", text)
        entry = (ENTRYPOINTS / "ROObjects.py").read_text(encoding="utf-8")
        self.assertIn("Reload mesh", entry)
        self.assertIn("standalone component", entry)
        self.assertNotIn("Close Octane and reopen", entry)

    def test_open_health_modules_compile(self):
        py_compile.compile(str(SRC / "foundation" / "health.py"), doraise=True)
        py_compile.compile(str(SRC / "foundation" / "docs.py"), doraise=True)
        py_compile.compile(str(SRC / "rhino" / "commands" / "open.py"), doraise=True)
        open_py = (SRC / "rhino" / "commands" / "open.py").read_text(encoding="utf-8")
        order = ("Open Config", "Open live", "Open models", "Open Docs")
        found = [open_py.find('"{}"'.format(name)) for name in order]
        self.assertTrue(all(i > 0 for i in found), found)
        self.assertEqual(found, sorted(found))
        self.assertNotIn('Text = "Close"', open_py)
        entry = (ENTRYPOINTS / "ROOpen.py").read_text(encoding="utf-8")
        self.assertIn("run_open", entry)
        self.assertIn("_CMD = \"ROOpen\"", entry)
