# -*- coding: utf-8 -*-
"""Camera JSON 契約（schema_version=1；欄位對齊 1.x Lua）。"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from foundation.result import Result

SCHEMA_VERSION = 1
PRODUCER_RHINO = "r2o_rhino"

Vec3 = Tuple[float, float, float]


def _as_vec3(node: Any) -> Optional[Vec3]:
    if isinstance(node, Mapping):
        try:
            return (float(node["x"]), float(node["y"]), float(node["z"]))
        except (KeyError, TypeError, ValueError):
            return None
    if isinstance(node, Sequence) and not isinstance(node, (str, bytes)):
        if len(node) != 3:
            return None
        try:
            return (float(node[0]), float(node[1]), float(node[2]))
        except (TypeError, ValueError):
            return None
    return None


def _vec3_list(vec: Vec3) -> List[float]:
    return [float(vec[0]), float(vec[1]), float(vec[2])]


def build_camera_payload(
    *,
    position: Vec3,
    target: Vec3,
    up_vector: Vec3,
    fov_degrees: float,
    producer: str = PRODUCER_RHINO,
    document_name: str = "",
    revision: int = 1,
) -> Dict[str, Any]:
    """組出可發布的 Camera payload（陣列欄位對齊 1.x Lua）。"""
    return {
        "schema_version": SCHEMA_VERSION,
        "producer": producer,
        "document": document_name or "",
        "revision": int(revision),
        "position": _vec3_list(position),
        "target": _vec3_list(target),
        "up_vector": _vec3_list(up_vector),
        "fov_degrees": float(fov_degrees),
    }


def validate_camera_payload(data: Any) -> Optional[str]:
    """回傳錯誤字串；通過則 None。"""
    if not isinstance(data, Mapping):
        return "Camera JSON root must be an object"
    try:
        ver = int(data.get("schema_version"))
    except (TypeError, ValueError):
        return "Missing or invalid schema_version"
    if ver != SCHEMA_VERSION:
        return "Unsupported schema_version: {} (need {})".format(ver, SCHEMA_VERSION)
    for key in ("position", "target", "up_vector"):
        if _as_vec3(data.get(key)) is None:
            return "Field {} must be a numeric [x, y, z] array".format(key)
    try:
        float(data.get("fov_degrees"))
    except (TypeError, ValueError):
        return "Field fov_degrees must be numeric"
    try:
        int(data.get("revision", 0))
    except (TypeError, ValueError):
        return "Field revision must be an integer"
    return None


def parse_camera_payload(data: Any) -> Result:
    """Parse 成功回傳 data=正規化 dict；失敗不猜測。"""
    err = validate_camera_payload(data)
    if err:
        return Result.fail(err, stage="parse_camera")
    assert isinstance(data, Mapping)
    position = _as_vec3(data["position"])
    target = _as_vec3(data["target"])
    up_vector = _as_vec3(data["up_vector"])
    assert position and target and up_vector
    return Result.success(
        stage="parse_camera",
        data={
            "schema_version": SCHEMA_VERSION,
            "producer": str(data.get("producer") or ""),
            "document": str(data.get("document") or ""),
            "revision": int(data.get("revision", 0)),
            "position": position,
            "target": target,
            "up_vector": up_vector,
            "fov_degrees": float(data["fov_degrees"]),
        },
    )


def payload_pose(payload: Mapping[str, Any]) -> Optional[Tuple[float, ...]]:
    """抽出比對用姿態（position＋target＋up＋fov）；無效則 None。"""
    position = _as_vec3(payload.get("position"))
    target = _as_vec3(payload.get("target"))
    up_vector = _as_vec3(payload.get("up_vector"))
    if position is None or target is None or up_vector is None:
        return None
    try:
        fov = float(payload.get("fov_degrees"))
    except (TypeError, ValueError):
        return None
    return position + target + up_vector + (fov,)


def poses_equivalent(
    a: Optional[Tuple[float, ...]],
    b: Optional[Tuple[float, ...]],
    *,
    pos_eps: float = 1e-4,
    fov_eps: float = 1e-4,
) -> bool:
    """epsilon 內視為同一姿態（對齊 1.x EPS_POSITION／EPS_FOV）。"""
    if a is None or b is None or len(a) != 10 or len(b) != 10:
        return False
    for i in range(9):
        if abs(a[i] - b[i]) > pos_eps:
            return False
    return abs(a[9] - b[9]) <= fov_eps


def validate_camera_file(path) -> Optional[str]:
    """atomic publish 用：讀 pending 檔並驗證 JSON。"""
    import json
    from pathlib import Path

    try:
        text = Path(path).read_text(encoding="utf-8")
        data = json.loads(text)
    except Exception as exc:
        return "Camera pending could not be parsed: {}".format(exc)
    return validate_camera_payload(data)
