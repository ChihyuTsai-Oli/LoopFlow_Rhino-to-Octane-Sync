# -*- coding: utf-8 -*-
"""Point payload／type_id／變換純 Python 測試。"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from foundation.atomic import atomic_publish_json
from foundation.paths import ensure_config_layout, point_path
from foundation.point_math import (
    block_xform_from_rhino_matrix,
    display_name_from_layer,
    find_node_key_collisions,
    identity_xform_at_point,
    layer_is_under_point_root,
    node_key_from_type_id,
    type_id_from_layer,
)
from foundation.point_payload import (
    SCHEMA_VERSION,
    build_item,
    build_point_payload,
    parse_point_payload,
    validate_point_file,
    validate_point_payload,
)


class PointMathTests(unittest.TestCase):
    def test_layer_root(self):
        self.assertTrue(layer_is_under_point_root("R2O::LT_Points::Downlight"))
        self.assertFalse(layer_is_under_point_root("R2O"))
        self.assertFalse(layer_is_under_point_root("USD::Chair"))
        self.assertFalse(layer_is_under_point_root("R2O_extra::x"))

    def test_type_id_is_full_path(self):
        path = "R2O::LT_Points::Downlight_A"
        self.assertEqual(type_id_from_layer(path), path)
        self.assertEqual(display_name_from_layer(path), "Downlight_A")
        self.assertEqual(
            node_key_from_type_id(path),
            "R2O_Point_R2O__LT_Points__Downlight_A",
        )

    def test_same_leaf_different_parent_are_two_types(self):
        a = "R2O::LT::Chair"
        b = "R2O::FUR::Chair"
        self.assertNotEqual(type_id_from_layer(a), type_id_from_layer(b))
        self.assertNotEqual(node_key_from_type_id(a), node_key_from_type_id(b))
        self.assertEqual(find_node_key_collisions([a, b]), [])

    def test_node_key_collision(self):
        a = "R2O::A::B"
        b = "R2O::A__B"
        hits = find_node_key_collisions([a, b])
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["node_key"], node_key_from_type_id(a))

    def test_identity_point_metres(self):
        xform = identity_xform_at_point(1.0, 2.0, 3.0, 1.0)
        self.assertEqual(xform[3], 1.0)
        self.assertEqual(xform[7], 3.0)
        self.assertEqual(xform[11], -2.0)
        self.assertEqual(xform[0], 1.0)

    def test_block_matrix_matches_1x(self):
        xform = block_xform_from_rhino_matrix(
            1, 2, 3, 4,
            5, 6, 7, 8,
            9, 10, 11, 12,
            2.0,
        )
        self.assertEqual(xform[0], 1.0)
        self.assertEqual(xform[1], 3.0)
        self.assertEqual(xform[2], -2.0)
        self.assertEqual(xform[3], 8.0)
        self.assertEqual(xform[4], 9.0)
        self.assertEqual(xform[5], 11.0)
        self.assertEqual(xform[6], -10.0)
        self.assertEqual(xform[7], 24.0)
        self.assertEqual(xform[8], -5.0)
        self.assertEqual(xform[9], -7.0)
        self.assertEqual(xform[10], 6.0)
        self.assertEqual(xform[11], -16.0)


class PointPayloadTests(unittest.TestCase):
    def test_build_and_validate(self):
        item = build_item(
            layer_full="R2O::LT_Points::Downlight_A",
            kind="point",
            xform=identity_xform_at_point(0, 0, 0, 1),
            guid="abc",
        )
        payload = build_point_payload([item], document_name="demo.3dm", revision=2)
        self.assertEqual(payload["schema_version"], SCHEMA_VERSION)
        self.assertIsNone(validate_point_payload(payload))
        self.assertTrue(parse_point_payload(payload).ok)

    def test_empty_items_ok(self):
        payload = build_point_payload([])
        self.assertIsNone(validate_point_payload(payload))

    def test_reject_collision(self):
        a = build_item(
            layer_full="R2O::A::B",
            kind="point",
            xform=identity_xform_at_point(0, 0, 0, 1),
        )
        b = build_item(
            layer_full="R2O::A__B",
            kind="point",
            xform=identity_xform_at_point(1, 0, 0, 1),
        )
        payload = build_point_payload([a, b])
        err = validate_point_payload(payload)
        self.assertIsNotNone(err)
        self.assertIn("collision", err.lower())

    def test_atomic_publish(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = ensure_config_layout(Path(tmp) / "loopflow_R2O")
            final = point_path(root)
            item = build_item(
                layer_full="R2O::LT_Points::Lamp",
                kind="point",
                xform=identity_xform_at_point(1, 2, 3, 1),
            )
            r = atomic_publish_json(
                final,
                build_point_payload([item]),
                validate=validate_point_file,
            )
            self.assertTrue(r.ok, r.message)
            loaded = json.loads(final.read_text(encoding="utf-8"))
            self.assertEqual(final.name, "point.json")
            self.assertTrue(parse_point_payload(loaded).ok)

    def test_sample_fixture(self):
        fixture = Path(__file__).resolve().parents[1] / "fixtures" / "point.sample.json"
        data = json.loads(fixture.read_text(encoding="utf-8"))
        self.assertIsNone(validate_point_payload(data))
        self.assertEqual(len(data["items"]), 2)
        self.assertNotEqual(data["items"][0]["type_id"], data["items"][1]["type_id"])
