# -*- coding: utf-8 -*-
"""圖層排除記號與子樹。"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rhino.layer_collect import (
    DEFAULT_LAYER_EXCLUDE_TOKEN,
    kind_is_included,
    layer_ids_with_ancestors,
    layer_path_is_excluded,
    layer_subtree_paths,
    top_level_layer_paths,
    top_level_of,
)


class LayerCollectTests(unittest.TestCase):
    def test_default_token_is_double_slash(self):
        self.assertEqual(DEFAULT_LAYER_EXCLUDE_TOKEN, "//")

    def test_blank_token_never_excludes(self):
        self.assertFalse(layer_path_is_excluded("R2O::MDL//skip", ""))
        self.assertFalse(layer_path_is_excluded("R2O::MDL//skip", "   "))

    def test_token_in_path_excludes(self):
        self.assertTrue(layer_path_is_excluded("R2O::MDL//archive", "//"))
        self.assertFalse(layer_path_is_excluded("R2O::MDL::Architecture", "//"))

    def test_subtree_includes_root_and_children(self):
        paths = (
            "R2O",
            "R2O::MDL",
            "R2O::MDL::Architecture",
            "R2O::MDL::Architecture::Wall",
            "R2O::LT_Points",
        )
        sub = layer_subtree_paths(paths, "R2O::MDL::Architecture")
        self.assertEqual(
            sub,
            (
                "R2O::MDL::Architecture",
                "R2O::MDL::Architecture::Wall",
            ),
        )

    def test_subtree_skips_excluded_children(self):
        paths = (
            "R2O::MDL",
            "R2O::MDL::Architecture",
            "R2O::MDL::Architecture//old",
            "R2O::MDL::Architecture::Wall",
        )
        sub = layer_subtree_paths(paths, "R2O::MDL")
        self.assertEqual(sub, ("R2O::MDL", "R2O::MDL::Architecture", "R2O::MDL::Architecture::Wall"))
        self.assertNotIn("R2O::MDL::Architecture//old", sub)

    def test_excluded_root_returns_empty(self):
        paths = ("R2O::MDL//skip", "R2O::MDL//skip::Wall")
        self.assertEqual(layer_subtree_paths(paths, "R2O::MDL//skip"), ())

    def test_top_level_paths_drop_children(self):
        paths = ("Models", "Models::Wall", "R2O", "R2O::LT", "Site")
        self.assertEqual(top_level_layer_paths(paths), ("Models", "R2O", "Site"))

    def test_top_level_of_child_is_root_name(self):
        self.assertEqual(top_level_of("Models::Color::White"), "Models")
        self.assertEqual(top_level_of("Models"), "Models")
        self.assertEqual(top_level_of(""), "")

    def test_kind_filter(self):
        self.assertTrue(kind_is_included("brep", {"brep", "mesh"}))
        self.assertTrue(kind_is_included("Brep", {"brep"}))
        self.assertFalse(kind_is_included("point", {"brep", "mesh"}))

    def test_child_layer_includes_locked_parent(self):
        parents = {"root": None, "arch": "root", "wall": "arch"}
        got = set(layer_ids_with_ancestors(["wall"], parents))
        self.assertEqual(got, {"wall", "arch", "root"})

    def test_block_member_layer_includes_its_parent(self):
        parents = {
            "site": None,
            "instance_layer": "site",
            "usd": None,
            "chair_geo": "usd",
        }
        got = set(layer_ids_with_ancestors(["instance_layer", "chair_geo"], parents))
        self.assertEqual(got, {"instance_layer", "site", "chair_geo", "usd"})

    def test_ancestor_cycle_stops(self):
        parents = {"a": "b", "b": "a"}
        got = layer_ids_with_ancestors(["a"], parents)
        self.assertEqual(set(got), {"a", "b"})
        self.assertEqual(len(got), 2)


if __name__ == "__main__":
    unittest.main()
