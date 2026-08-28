# -*- coding: utf-8 -*-
"""相機自動同步閘：節流＋trailing。"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from foundation.atomic import direct_overwrite_json
from foundation.camera_hotpath import CameraThrottleGate
from foundation.camera_payload import build_camera_payload, payload_pose, poses_equivalent


def _payload_at(z: float):
    payload = build_camera_payload(
        position=(0, 0, z),
        target=(0, 0, 0),
        up_vector=(0, 1, 0),
        fov_degrees=39.6,
    )
    return payload, payload_pose(payload)


class CameraPoseTests(unittest.TestCase):
    def test_equivalent_within_eps(self):
        a = payload_pose(
            build_camera_payload(
                position=(1, 2, 3),
                target=(0, 0, 0),
                up_vector=(0, 1, 0),
                fov_degrees=35,
            )
        )
        b = payload_pose(
            build_camera_payload(
                position=(1 + 1e-9, 2, 3),
                target=(0, 0, 0),
                up_vector=(0, 1, 0),
                fov_degrees=35 + 1e-6,
            )
        )
        self.assertTrue(poses_equivalent(a, b))

    def test_different_location_not_equivalent(self):
        _, a = _payload_at(0.0)
        _, b = _payload_at(1.0)
        self.assertFalse(poses_equivalent(a, b))


class CameraThrottleGateTests(unittest.TestCase):
    def test_first_pose_writes(self):
        gate = CameraThrottleGate(min_interval=0.2)
        payload, pose = _payload_at(1.0)
        self.assertEqual(gate.on_event(pose, payload, 10.0), "write")
        gate.mark_written(pose, 10.0)

    def test_unchanged_skips(self):
        gate = CameraThrottleGate()
        payload, pose = _payload_at(1.0)
        gate.mark_written(pose, 1.0)
        self.assertEqual(gate.on_event(pose, payload, 2.0), "skip")

    def test_throttle_defers_then_trailing(self):
        gate = CameraThrottleGate(min_interval=0.2)
        p1, pose1 = _payload_at(1.0)
        self.assertEqual(gate.on_event(pose1, p1, 1.0), "write")
        gate.mark_written(pose1, 1.0)
        p2, pose2 = _payload_at(2.0)
        self.assertEqual(gate.on_event(pose2, p2, 1.05), "defer")
        self.assertFalse(gate.trailing_due(1.10))
        self.assertTrue(gate.trailing_due(1.25))
        self.assertEqual(gate.pending_payload["position"][2], 2.0)


class CameraHotpathPublishTests(unittest.TestCase):
    def test_direct_overwrite_compact_json(self):
        payload = build_camera_payload(
            position=(1, 2, 3),
            target=(0, 0, 0),
            up_vector=(0, 1, 0),
            fov_degrees=39.6,
        )
        with tempfile.TemporaryDirectory() as tmp:
            final = Path(tmp) / "camera.json"
            r = direct_overwrite_json(final, payload, indent=None)
            self.assertTrue(r.ok, r.message)
            text = final.read_text(encoding="utf-8")
            self.assertNotIn("\n  ", text)
            loaded = json.loads(text)
            self.assertEqual(loaded["fov_degrees"], 39.6)
