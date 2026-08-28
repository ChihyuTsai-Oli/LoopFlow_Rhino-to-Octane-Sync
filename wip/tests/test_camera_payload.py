# -*- coding: utf-8 -*-
"""Camera payload／atomic 純 Python 測試。"""
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
from foundation.camera_payload import (
    SCHEMA_VERSION,
    build_camera_payload,
    parse_camera_payload,
    validate_camera_file,
    validate_camera_payload,
)
from foundation.paths import camera_path, ensure_config_layout


class CameraPayloadTests(unittest.TestCase):
    def test_build_and_parse_roundtrip(self):
        payload = build_camera_payload(
            position=(1, 2, 3),
            target=(0, 1, 0),
            up_vector=(0, 1, 0),
            fov_degrees=39.6,
            document_name="demo.3dm",
            revision=4,
        )
        self.assertEqual(payload["schema_version"], SCHEMA_VERSION)
        self.assertEqual(payload["producer"], "r2o_rhino")
        self.assertEqual(payload["position"], [1.0, 2.0, 3.0])
        self.assertIsNone(validate_camera_payload(payload))
        parsed = parse_camera_payload(payload)
        self.assertTrue(parsed.ok)
        self.assertEqual(parsed.data["position"], (1.0, 2.0, 3.0))
        self.assertEqual(parsed.data["revision"], 4)

    def test_reject_unknown_schema(self):
        payload = build_camera_payload(
            position=(0, 0, 0),
            target=(0, 0, 0),
            up_vector=(0, 1, 0),
            fov_degrees=40,
        )
        payload["schema_version"] = 99
        r = parse_camera_payload(payload)
        self.assertFalse(r.ok)
        self.assertIn("schema_version", r.message)

    def test_reject_legacy_lua_table_without_schema(self):
        legacy = {
            "position": [0, 0, 0],
            "target": [0, 0, 0],
            "up_vector": [0, 1, 0],
            "fov_degrees": 40,
        }
        self.assertIsNotNone(validate_camera_payload(legacy))

    def test_atomic_publish_camera(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = ensure_config_layout(Path(tmp) / "loopflow_R2O")
            final = camera_path(root)
            payload = build_camera_payload(
                position=(10, 20, 30),
                target=(0, 0, 0),
                up_vector=(0, 1, 0),
                fov_degrees=39.6,
            )
            r = atomic_publish_json(final, payload, validate=validate_camera_file)
            self.assertTrue(r.ok, r.message)
            loaded = json.loads(final.read_text(encoding="utf-8"))
            self.assertEqual(loaded["schema_version"], SCHEMA_VERSION)
            self.assertTrue(parse_camera_payload(loaded).ok)
            self.assertEqual(final.name, "camera.json")
            self.assertEqual(final.parent.name, "live")

    def test_sample_fixture(self):
        fixture = Path(__file__).resolve().parents[1] / "fixtures" / "camera.sample.json"
        data = json.loads(fixture.read_text(encoding="utf-8"))
        self.assertIsNone(validate_camera_payload(data))
