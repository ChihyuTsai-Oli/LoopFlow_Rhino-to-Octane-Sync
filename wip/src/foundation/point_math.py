# -*- coding: utf-8 -*-
"""Rhino → Octane 點位變換（凍結 1.x 數學；純 Python）。"""
from __future__ import annotations

from typing import Sequence, Tuple

from foundation.camera_math import rhino_to_octane_point

Xform12 = Tuple[float, float, float, float, float, float, float, float, float, float, float, float]

POINT_LAYER_ROOT = "R2O"
POINT_LAYER_PREFIX = POINT_LAYER_ROOT + "::"
POINT_NODE_GROUP = "R2O_Point"
POINT_NODE_PREFIX = "R2O_Point_"


def layer_is_under_point_root(layer_full: str) -> bool:
    """必須是 `R2O::…` 子圖層；根層 `R2O` 本身不掃。"""
    text = str(layer_full or "")
    return text.startswith(POINT_LAYER_PREFIX)


def type_id_from_layer(layer_full: str) -> str:
    """穩定身分＝完整圖層路徑。"""
    return str(layer_full or "").strip()


def display_name_from_layer(layer_full: str) -> str:
    text = str(layer_full or "")
    if "::" not in text:
        return text
    return text.split("::")[-1]


def node_key_from_type_id(type_id: str) -> str:
    """Octane 節點技術名：前綴＋把 `::` 換成 `__`（中文保留）。"""
    return POINT_NODE_PREFIX + str(type_id or "").replace("::", "__")


def identity_xform_at_point(x: float, y: float, z: float, meters_per_unit: float) -> Xform12:
    """Point 物件：位置＋單位旋轉。"""
    ox, oy, oz = rhino_to_octane_point(x, y, z, meters_per_unit)
    return (
        1.0, 0.0, 0.0, float(ox),
        0.0, 1.0, 0.0, float(oy),
        0.0, 0.0, 1.0, float(oz),
    )


def block_xform_from_rhino_matrix(
    m00: float, m01: float, m02: float, m03: float,
    m10: float, m11: float, m12: float, m13: float,
    m20: float, m21: float, m22: float, m23: float,
    meters_per_unit: float,
) -> Xform12:
    """Block instance：1.x `BlockInstanceXform` 軸轉換。"""
    scale = float(meters_per_unit)
    return (
        float(m00), float(m02), -float(m01), float(m03) * scale,
        float(m20), float(m22), -float(m21), float(m23) * scale,
        -float(m10), -float(m12), float(m11), -float(m13) * scale,
    )


def xform_to_list(xform: Sequence[float]) -> list:
    if len(xform) != 12:
        raise ValueError("xform must have 12 numbers")
    return [float(v) for v in xform]


def find_node_key_collisions(type_ids: Sequence[str]) -> list:
    """兩個不同 type_id 洗成同一個節點名則整批停止。"""
    buckets = {}
    for raw in type_ids:
        key = node_key_from_type_id(raw)
        buckets.setdefault(key, []).append(raw)
    collisions = []
    for key, sources in buckets.items():
        unique = []
        seen = set()
        for src in sources:
            if src not in seen:
                unique.append(src)
                seen.add(src)
        if len(unique) > 1:
            collisions.append({"node_key": key, "type_ids": unique})
    return collisions
