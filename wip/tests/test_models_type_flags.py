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
    take_mesh_parameters,
    usd_export_choice,
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

    def test_usd_export_choice_defaults_match_rhino_prompt(self):
        choice = usd_export_choice("", 0, "", True)
        self.assertEqual(choice["block_handling"], "Embedded")
        self.assertEqual(choice["default_layer"], "")
        self.assertEqual(choice["model_name"], "")
        self.assertTrue(choice["include_user_strings"])

    def test_usd_export_choice_rejects_bad_block_index(self):
        choice = usd_export_choice("World", 9, "House", False)
        self.assertEqual(choice["block_handling"], "Embedded")
        self.assertEqual(choice["default_layer"], "World")
        self.assertEqual(choice["model_name"], "House")
        self.assertFalse(choice["include_user_strings"])

    def test_mesh_dialog_cancel_keeps_previous_parameters(self):
        self.assertEqual(take_mesh_parameters(1, "old", mutated="changed"), "old")
        self.assertEqual(take_mesh_parameters((1, "new"), "old"), "old")

    def test_mesh_dialog_ok_uses_returned_parameters(self):
        self.assertEqual(take_mesh_parameters((0, "r2o"), "old"), "r2o")
        self.assertEqual(take_mesh_parameters(0, "old", mutated="r2o"), "r2o")

    def test_objects_command_imports_current_export_helpers(self):
        self.assertTrue(callable(objects_command.publish_objects_once))


if __name__ == "__main__":
    unittest.main()
