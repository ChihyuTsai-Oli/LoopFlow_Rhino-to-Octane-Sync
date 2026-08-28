# -*- coding: utf-8 -*-
"""1.x 相機座標／FOV 數學。"""
from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from foundation.camera_math import (
    DEFAULT_LENS_MM,
    SENSOR_WIDTH_MM,
    fov_degrees_from_lens_mm,
    resolve_lens_mm,
    rhino_to_octane_point,
    rhino_to_octane_vector,
)


class CameraMathTests(unittest.TestCase):
    def test_point_meters(self):
        self.assertEqual(rhino_to_octane_point(1.0, 2.0, 3.0, 1.0), (1.0, 3.0, -2.0))

    def test_point_millimetres_to_metres(self):
        self.assertEqual(
            rhino_to_octane_point(1000.0, 0.0, 0.0, 0.001),
            (1.0, 0.0, 0.0),
        )

    def test_vector_unscaled(self):
        self.assertEqual(rhino_to_octane_vector(0.0, 1.0, 0.0), (0.0, 0.0, -1.0))

    def test_zero_lens_falls_back_to_50mm(self):
        self.assertEqual(resolve_lens_mm(0.0), DEFAULT_LENS_MM)
        self.assertEqual(resolve_lens_mm(-10.0), DEFAULT_LENS_MM)
        expected = 2.0 * math.atan(SENSOR_WIDTH_MM / (2.0 * DEFAULT_LENS_MM)) * (180.0 / math.pi)
        self.assertAlmostEqual(fov_degrees_from_lens_mm(0.0), expected, places=6)

    def test_known_50mm_fov(self):
        fov = fov_degrees_from_lens_mm(50.0)
        self.assertAlmostEqual(fov, 39.597755, places=5)
