# -*- coding: utf-8 -*-
"""Rhino Point 通道：掃 R2O:: 圖層，atomic 發布 live/point.json。"""
from __future__ import annotations

import json
import os
from typing import List

from foundation.atomic import atomic_publish_json
from foundation.log import append_log
from foundation.paths import (
    config_root_for_document,
    ensure_config_layout,
    point_path,
    require_saved_document_path,
)
from foundation.point_math import (
    POINT_LAYER_PREFIX,
    block_xform_from_rhino_matrix,
    identity_xform_at_point,
    layer_is_under_point_root,
)
from foundation.point_payload import (
    build_item,
    build_point_payload,
    validate_point_file,
    validate_point_payload,
)
from foundation.pointer import write_current_project_pointer
from foundation.result import Result

_KIND_POINT = 1
_KIND_BLOCK = 4096


def _resolve_publish_target() -> Result:
    import scriptcontext as sc  # type: ignore

    doc = sc.doc
    path = getattr(doc, "Path", None) if doc else None
    saved = require_saved_document_path(path)
    if not saved.ok:
        return saved
    root = ensure_config_layout(config_root_for_document(saved.data))
    return Result.success(
        data={"root": root, "point": point_path(root), "document": saved.data},
        stage="resolve_path",
    )


def _next_revision(final_path) -> int:
    path = final_path
    try:
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
            return int(data.get("revision", 0)) + 1
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        pass
    return 1


def _guid_text(obj_id) -> str:
    try:
        return str(obj_id)
    except Exception:
        return ""


def capture_point_items() -> Result:
    """掃場景 Point／Block；僅 `R2O::` 子圖層。"""
    import Rhino  # type: ignore
    import rhinoscriptsyntax as rs  # type: ignore

    doc = Rhino.RhinoDoc.ActiveDoc
    if not doc:
        return Result.fail("No active document", stage="capture_points")

    scale = Rhino.RhinoMath.UnitScale(doc.ModelUnitSystem, Rhino.UnitSystem.Meters)
    points = rs.ObjectsByType(_KIND_POINT) or []
    blocks = rs.ObjectsByType(_KIND_BLOCK) or []
    items = []
    skipped: List[str] = []

    for obj_id in list(points) + list(blocks):
        layer_full = rs.ObjectLayer(obj_id) or ""
        if not layer_is_under_point_root(layer_full):
            continue
        obj_type = rs.ObjectType(obj_id)
        try:
            if obj_type == _KIND_POINT:
                coord = rs.PointCoordinates(obj_id)
                xform = identity_xform_at_point(coord.X, coord.Y, coord.Z, scale)
                kind = "point"
            elif obj_type == _KIND_BLOCK:
                matrix = rs.BlockInstanceXform(obj_id)
                xform = block_xform_from_rhino_matrix(
                    matrix.M00, matrix.M01, matrix.M02, matrix.M03,
                    matrix.M10, matrix.M11, matrix.M12, matrix.M13,
                    matrix.M20, matrix.M21, matrix.M22, matrix.M23,
                    scale,
                )
                kind = "block"
            else:
                skipped.append("{} (unsupported object type)".format(layer_full))
                continue
        except Exception as exc:
            skipped.append("{} ({})".format(layer_full, exc))
            continue
        items.append(
            build_item(
                layer_full=layer_full,
                kind=kind,
                xform=xform,
                guid=_guid_text(obj_id),
            )
        )

    err = validate_point_payload(build_point_payload(items))
    if err:
        return Result.fail(err, stage="capture_points")
    return Result.success(
        stage="capture_points",
        data={"items": items, "skipped": skipped},
    )


def publish_points_once() -> Result:
    """掃點位並 atomic 發布 point.json。空清單仍發布，讓 Octane 清掉已刪類型。"""
    target = _resolve_publish_target()
    if not target.ok:
        return target
    cap = capture_point_items()
    if not cap.ok:
        return cap

    items = cap.data["items"]
    skipped = cap.data["skipped"]
    final = target.data["point"]
    root = target.data["root"]
    payload = build_point_payload(
        items,
        document_name=os.path.basename(target.data["document"] or ""),
        revision=_next_revision(final),
    )
    result = atomic_publish_json(final, payload, validate=validate_point_file)
    if result.ok:
        write_current_project_pointer(target.data["root"], target.data["document"])

    extra = ""
    if skipped:
        extra = "; skipped {}".format(len(skipped))
    message = "Published {} point item(s) under {}{}".format(
        len(items), POINT_LAYER_PREFIX, extra
    )
    if result.ok:
        result = Result.success(message, stage=result.stage, data=str(final))
    append_log(root, "Point publish: {} ({})".format(result.status, result.message))
    for line in skipped:
        print("[R2O_Point] skipped: {}".format(line))
    return result
