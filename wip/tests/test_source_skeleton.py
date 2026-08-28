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
    "R2O_Camera.py",
    "R2O_Camera_Push.py",
)
REQUIRED_LUA = (
    "R2O_Camera.lua",
    "R2O_Point.lua",
    "R2O_Open.lua",
)


class SourceSkeletonTests(unittest.TestCase):
    def test_rhino_entrypoints_exist_and_compile(self):
        for name in REQUIRED_RHINO:
            path = ENTRYPOINTS / name
            self.assertTrue(path.is_file(), name)
            py_compile.compile(str(path), doraise=True)

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
        self.assertIn("SetTimer", camera)
        self.assertNotIn("sleep_ms", camera)
        self.assertNotIn("void Sleep", camera)

    def test_camera_command_mentions_perspective(self):
        text = (SRC / "rhino" / "commands" / "camera.py").read_text(encoding="utf-8")
        self.assertIn("IsPerspectiveProjection", text)
        self.assertIn("write_current_project_pointer", text)
        self.assertIn("CameraThrottleGate", text)
