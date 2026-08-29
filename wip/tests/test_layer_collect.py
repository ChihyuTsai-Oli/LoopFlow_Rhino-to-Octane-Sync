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
    layer_path_is_excluded,
    layer_subtree_paths,
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

    def test_kind_filter(self):
        self.assertTrue(kind_is_included("brep", {"brep", "mesh"}))
        self.assertTrue(kind_is_included("Brep", {"brep"}))
        self.assertFalse(kind_is_included("point", {"brep", "mesh"}))


if __name__ == "__main__":
    unittest.main()
