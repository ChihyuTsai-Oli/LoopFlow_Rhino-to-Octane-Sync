# -*- coding: utf-8 -*-
"""G02 yak spike：manifest、指令檔、含 Octane Lua templates（不依賴 Rhino GUI）。"""
from __future__ import annotations

import py_compile
import sys
import tempfile
import unittest
from pathlib import Path

WIP = Path(__file__).resolve().parents[1]
SPIKE = WIP / "packaging" / "g02-spike"
COMMANDS = SPIKE / "commands"
NAMES = SPIKE / "指令名稱.txt"
MANIFEST = SPIKE / "manifest.yml"
ENTRYPOINTS = WIP / "src" / "rhino" / "entrypoints"
if str(SPIKE) not in sys.path:
    sys.path.insert(0, str(SPIKE))

import command_locate  # noqa: E402

EXPECTED = (
    "ROCamera",
    "ROCameraPush",
    "ROModels",
    "ROObjects",
    "ROPoint",
    "ROOpen",
)


class G02SpikeTests(unittest.TestCase):
    def test_command_name_list(self):
        names = [
            line.strip()
            for line in NAMES.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertEqual(tuple(names), EXPECTED)

    def test_yak_command_files(self):
        for name in EXPECTED:
            path = COMMANDS / "{}.py".format(name)
            self.assertTrue(path.is_file(), path)
            text = path.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("#! python 3"), name)
            self.assertIn("def RunCommand(", text)
            self.assertIn("_run()", text)
            self.assertIn("PLUGIN_ID = \"{}\"".format(command_locate.PLUGIN_ID), text)
            self.assertIn("_from_yak_install", text)
            self.assertIn("sync_user_assets", text)
            self.assertIn("find_templates", text)
            self.assertIn("src_root=src", text)
            self.assertIn(".rhinocode", text)
            self.assertLess(
                text.index("_from_yak_install()"),
                text.index("_from_script(__file__)"),
            )
            self.assertLess(
                text.index("sync_user_assets(src_root=src)"),
                text.index("if _started:"),
            )
            self.assertNotIn("can_sync_user_assets", text)
            self.assertNotIn("_isolate.py", text)
            self.assertNotIn("octane/entrypoints", text)
            self.assertNotIn(".lua", text)
            self.assertNotIn("blender", text.lower())
            py_compile.compile(str(path), doraise=True)
        extras = {p.stem for p in COMMANDS.glob("*.py")} - set(EXPECTED)
        self.assertEqual(extras, set())
        point = (COMMANDS / "ROPoint.py").read_text(encoding="utf-8")
        self.assertIn('_CMD = "ROPoint"', point)
        self.assertNotIn("R2O_Point", point)

    def test_dev_entrypoints_unchanged_names(self):
        for name in EXPECTED:
            self.assertTrue((ENTRYPOINTS / "{}.py".format(name)).is_file(), name)

    def test_manifest_spike_identity(self):
        text = MANIFEST.read_text(encoding="utf-8")
        self.assertIn("name: loopflow-rhino-to-octanerender-sync", text)
        self.assertIn("version: 2.0.3", text)
        self.assertIn("Chihyu Tsai", text)
        self.assertIn("github.com/ChihyuTsai-Oli/LoopFlow_Rhino-to-Octane-Sync", text)
        self.assertIn("guid:2802e7cc-df95-447b-8adc-865628bfbda8", text)
        self.assertIn("platform: win", text)
        self.assertIn("Update models without breaking material links", text)
        self.assertNotIn("spike", text)
        self.assertNotIn("blender", text.lower())

    def test_build_script_drops_auto_rui(self):
        build = (SPIKE / "build.ps1").read_text(encoding="utf-8")
        self.assertIn("Remove-Item", build)
        self.assertIn(".rui", build)
        self.assertIn("yak", build.lower())
        self.assertIn("docs\\toolbar", build)
        self.assertIn("build\\rh8", build)
        self.assertIn("yak-stage", build)
        self.assertIn("templates", build)
        self.assertIn("Join-Path $Templates \"lua\"", build)
        self.assertIn("octane\\entrypoints", build)
        self.assertIn("matches rhp", build)
        self.assertIn(".txt", build)

    def test_script_directory_txt_in_entrypoints(self):
        path = WIP / "src" / "octane" / "entrypoints" / "Set_Octane_Script_Directory.txt"
        self.assertTrue(path.is_file(), path)
        text = path.read_text(encoding="utf-8")
        self.assertIn("Script directory", text)
        self.assertIn("Documents\\LoopFlow\\Rhino to OctaneRender Sync\\lua", text)
        self.assertIn("文件\\LoopFlow\\Rhino to OctaneRender Sync\\lua", text)
        self.assertIn("Reload mesh", text)

    def test_command_locate_compiles(self):
        py_compile.compile(str(SPIKE / "command_locate.py"), doraise=True)

    def test_command_locate_finds_libs_src(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = {"APPDATA": tmp, "LOCALAPPDATA": tmp}
            src = (
                Path(tmp)
                / "McNeel"
                / "Rhinoceros"
                / "packages"
                / "8.0"
                / command_locate.YAK_NAME
                / "0.1.0"
                / "libs"
                / "Abcd"
                / "src"
            )
            (src / "foundation").mkdir(parents=True)
            marker = src.joinpath(*command_locate.MARKER)
            marker.parent.mkdir(parents=True)
            marker.write_text("#", encoding="utf-8")
            hit = command_locate.from_yak_install(env)
            self.assertEqual(hit.resolve(), src.resolve())

    def test_spike_does_not_commit_lua(self):
        lua = [
            p
            for p in SPIKE.rglob("*.lua")
            if "build" not in p.parts
        ]
        self.assertEqual(lua, [])

    def test_product_rui_and_icon(self):
        rui = WIP / "docs" / "toolbar" / "LoopFlow_R2O.rui"
        text = rui.read_text(encoding="utf-8")
        self.assertIn("<tool_bar_group ", text)
        self.assertIn("Rhino to OctaneRender Sync", text)
        self.assertNotIn("SelectedToolbarSet", text)
        for cmd in EXPECTED:
            self.assertIn("! _{}".format(cmd), text)
        self.assertTrue((WIP / "docs" / "toolbar" / "icon.png").is_file())
        self.assertTrue((SPIKE / "loopflow-rhino-to-octanerender-sync.rhproj").is_file())


if __name__ == "__main__":
    unittest.main()
