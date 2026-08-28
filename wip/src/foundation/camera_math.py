# -*- coding: utf-8 -*-
"""Rhino → Octane 相機座標／FOV（凍結 1.x 數學；純 Python）。"""
from __future__ import annotations

import math
from typing import Tuple

Vec3 = Tuple[float, float, float]

DEFAULT_LENS_MM = 50.0
SENSOR_WIDTH_MM = 36.0


def rhino_to_octane_point(x: float, y: float, z: float, meters_per_unit: float) -> Vec3:
    """點：`(x, z, -y)` 再乘公尺比例。"""
    scale = float(meters_per_unit)
    return (float(x) * scale, float(z) * scale, -float(y) * scale)


def rhino_to_octane_vector(x: float, y: float, z: float) -> Vec3:
    """方向／up：只轉軸，不乘單位。"""
    return (float(x), float(z), -float(y))


def resolve_lens_mm(lens_mm: float, default_lens_mm: float = DEFAULT_LENS_MM) -> float:
    """鏡頭 ≤ 0 時退回預設 50mm。"""
    try:
        value = float(lens_mm)
    except (TypeError, ValueError):
        return float(default_lens_mm)
    if value <= 0.0:
        return float(default_lens_mm)
    return value


def fov_degrees_from_lens_mm(
    lens_mm: float,
    *,
    sensor_width_mm: float = SENSOR_WIDTH_MM,
    default_lens_mm: float = DEFAULT_LENS_MM,
) -> float:
    """水平 FOV：`2 * atan(sensor / (2 * lens_mm))`，單位度。"""
    lens = resolve_lens_mm(lens_mm, default_lens_mm)
    return 2.0 * math.atan(float(sensor_width_mm) / (2.0 * lens)) * (180.0 / math.pi)
