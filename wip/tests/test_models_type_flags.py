# -*- coding: utf-8 -*-
"""Models 幾何類別 CheckListBox 預設勾選。"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import rhino.commands.objects as objects_command
from rhino.commands.models import (
    checklist_defaults,
    checklist_flags,
    selected_type_labels,
)


class ModelTypeChecklistTests(unittest.TestCase):
    def test_builtin_defaults_skip_point_curve(self):
        rows = dict(checklist_defaults())
        self.assertFalse(rows["Point"])
        self.assertFalse(rows["Curve"])
        self.assertTrue(rows["Mesh"])
        self.assertTrue(rows["Block / Instance"])
        self.assertTrue(rows["Brep / Polysurface / Surface"])

    def test_last_labels_override(self):
        rows = dict(checklist_defaults(["Point", "Mesh"]))
        self.assertTrue(rows["Point"])
        self.assertFalse(rows["Curve"])
        self.assertTrue(rows["Mesh"])
        self.assertFalse(rows["Block / Instance"])

    def test_tuple_results_use_the_check_flag(self):
        flags = checklist_flags([("[0] Point", False), ("[2] Mesh", True)])
        self.assertEqual(flags, [False, True])

    def test_bool_results_keep_mesh_and_skip_point(self):
        include, selected = selected_type_labels(
            ["Point", "Mesh"],
            [False, True],
            [{"point"}, {"mesh"}],
        )
        self.assertEqual(selected, ["Mesh"])
        self.assertEqual(include, {"mesh"})

    def test_objects_command_imports_current_export_helpers(self):
        self.assertTrue(callable(objects_command.publish_objects_once))


if __name__ == "__main__":
    unittest.main()
