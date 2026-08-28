# -*- coding: utf-8 -*-
"""Rhino Camera 通道：手動推一次／自動同步開／關。"""
from __future__ import annotations

import os
import time
from typing import Any, Optional

from foundation.atomic import atomic_publish_json, direct_overwrite_json
from foundation.camera_hotpath import CameraThrottleGate
from foundation.camera_math import (
    fov_degrees_from_lens_mm,
    rhino_to_octane_point,
    rhino_to_octane_vector,
)
from foundation.camera_payload import (
    build_camera_payload,
    payload_pose,
    validate_camera_file,
    validate_camera_payload,
)
from foundation.log import append_log
from foundation.paths import (
    camera_path,
    config_root_for_document,
    ensure_config_layout,
    require_saved_document_path,
)
from foundation.pointer import write_current_project_pointer
from foundation.result import Result

_STICKY_EVENT = "R2O2_Camera_Sync_Event"
_STICKY_IDLE = "R2O2_Camera_Sync_Idle"
_STICKY_PATH = "R2O2_CAMERA_JSON_PATH"
_STICKY_GATE = "R2O2_CAMERA_GATE"
_STICKY_REV = "R2O2_CAMERA_REVISION"
_STICKY_DOC = "R2O2_CAMERA_DOC_PATH"


def _sticky():
    import scriptcontext as sc  # type: ignore

    return sc.sticky


def _next_revision() -> int:
    sticky = _sticky()
    n = int(sticky.get(_STICKY_REV, 0)) + 1
    sticky[_STICKY_REV] = n
    return n


def capture_active_camera() -> Result:
    """從作用中透視視埠擷取相機；非透視則 blocked。"""
    import Rhino  # type: ignore

    doc = Rhino.RhinoDoc.ActiveDoc
    if not doc:
        return Result.fail("No active document", stage="capture_camera")
    view = doc.Views.ActiveView
    if not view:
        return Result.fail("No active view", stage="capture_camera")
    vp = view.ActiveViewport
    if not vp.IsPerspectiveProjection:
        return Result.blocked(
            "Active view is not perspective. Switch to a Perspective viewport.",
            stage="capture_camera",
        )

    scale = Rhino.RhinoMath.UnitScale(doc.ModelUnitSystem, Rhino.UnitSystem.Meters)
    loc = vp.CameraLocation
    tar = vp.CameraTarget
    up = vp.CameraUp
    payload = build_camera_payload(
        position=rhino_to_octane_point(loc.X, loc.Y, loc.Z, scale),
        target=rhino_to_octane_point(tar.X, tar.Y, tar.Z, scale),
        up_vector=rhino_to_octane_vector(up.X, up.Y, up.Z),
        fov_degrees=fov_degrees_from_lens_mm(float(vp.Camera35mmLensLength or 0.0)),
        document_name=os.path.basename(doc.Path or "") if doc.Path else "",
        revision=0,
    )
    return Result.success(stage="capture_camera", data=payload)


def _resolve_publish_target() -> Result:
    import scriptcontext as sc  # type: ignore

    doc = sc.doc
    path = getattr(doc, "Path", None) if doc else None
    saved = require_saved_document_path(path)
    if not saved.ok:
        return saved
    root = ensure_config_layout(config_root_for_document(saved.data))
    return Result.success(
        data={"root": root, "camera": camera_path(root), "document": saved.data},
        stage="resolve_path",
    )


def _stamp_revision(payload: dict) -> dict:
    out = dict(payload)
    out["revision"] = _next_revision()
    return out


def _write_pointer(target: dict) -> None:
    write_current_project_pointer(target["root"], target["document"])
    sticky = _sticky()
    sticky[_STICKY_DOC] = target["document"]


def publish_camera_once(payload: Optional[dict] = None) -> Result:
    """擷取（或使用既有 payload）並 atomic 發布 camera.json。"""
    if payload is None:
        cap = capture_active_camera()
        if not cap.ok:
            return cap
        payload = cap.data
    target = _resolve_publish_target()
    if not target.ok:
        return target
    payload = _stamp_revision(payload)
    final = target.data["camera"]
    root = target.data["root"]
    result = atomic_publish_json(final, payload, validate=validate_camera_file)
    if result.ok:
        _write_pointer(target.data)
        sticky = _sticky()
        gate = sticky.get(_STICKY_GATE)
        if isinstance(gate, CameraThrottleGate):
            gate.mark_written(payload_pose(payload), time.monotonic())
    append_log(root, "Camera publish: {} ({})".format(result.status, result.message))
    return result


def _publish_camera_hot(json_path: str, payload: dict) -> bool:
    """自動同步熱路徑：直接覆蓋 final。"""
    err = validate_camera_payload(payload)
    if err:
        return False
    stamped = _stamp_revision(payload)
    return bool(direct_overwrite_json(json_path, stamped, indent=None).ok)


def _on_view_modified(sender: Any, e: Any) -> None:
    """視角一變就擷取；未變略過，間隔不足則留給 Idle trailing。"""
    try:
        sticky = _sticky()
        json_path = sticky.get(_STICKY_PATH)
        gate = sticky.get(_STICKY_GATE)
        if not json_path or gate is None:
            return
        cap = capture_active_camera()
        if not cap.ok:
            return
        pose = payload_pose(cap.data)
        action = gate.on_event(pose, cap.data, time.monotonic())
        if action == "skip":
            return
        if action == "defer":
            return
        if _publish_camera_hot(str(json_path), cap.data):
            gate.mark_written(pose, time.monotonic())
    except Exception:
        pass


def _on_idle(sender: Any, e: Any) -> None:
    """節流期間的最後一幀：安靜後補寫。"""
    try:
        sticky = _sticky()
        json_path = sticky.get(_STICKY_PATH)
        gate = sticky.get(_STICKY_GATE)
        if not json_path or not isinstance(gate, CameraThrottleGate):
            return
        now = time.monotonic()
        if not gate.trailing_due(now):
            return
        payload = gate.pending_payload
        pose = gate.pending_pose
        if not payload:
            return
        if _publish_camera_hot(str(json_path), payload):
            gate.mark_written(pose, time.monotonic())
    except Exception:
        pass


def camera_auto_on() -> Result:
    import Rhino  # type: ignore

    target = _resolve_publish_target()
    if not target.ok:
        return target
    cap = capture_active_camera()
    if not cap.ok:
        return cap

    sticky = _sticky()
    if _STICKY_EVENT in sticky:
        return Result.success("Camera auto sync already running", stage="camera_auto_on")

    path = str(target.data["camera"])
    sticky[_STICKY_PATH] = path
    sticky[_STICKY_GATE] = CameraThrottleGate()
    sticky[_STICKY_EVENT] = _on_view_modified
    sticky[_STICKY_IDLE] = _on_idle
    Rhino.Display.RhinoView.Modified += _on_view_modified
    Rhino.RhinoApp.Idle += _on_idle

    push = publish_camera_once(cap.data)
    append_log(target.data["root"], "Camera Auto On → {}".format(path))
    if push.ok:
        return Result.success("Camera auto sync on: {}".format(path), stage="camera_auto_on")
    return Result.success(
        "Camera auto sync on (first push: {})".format(push.message),
        stage="camera_auto_on",
    )


def camera_auto_off() -> Result:
    import Rhino  # type: ignore

    sticky = _sticky()
    if _STICKY_EVENT not in sticky:
        return Result.success("Camera auto sync was already off", stage="camera_auto_off")

    json_path = sticky.get(_STICKY_PATH)
    gate = sticky.get(_STICKY_GATE)
    if json_path and isinstance(gate, CameraThrottleGate) and gate.pending_payload:
        _publish_camera_hot(str(json_path), gate.pending_payload)

    func = sticky.get(_STICKY_EVENT)
    idle = sticky.get(_STICKY_IDLE)
    try:
        if func is not None:
            Rhino.Display.RhinoView.Modified -= func
    except Exception:
        pass
    try:
        if idle is not None:
            Rhino.RhinoApp.Idle -= idle
    except Exception:
        pass
    sticky.pop(_STICKY_EVENT, None)
    sticky.pop(_STICKY_IDLE, None)
    sticky.pop(_STICKY_PATH, None)
    sticky.pop(_STICKY_GATE, None)
    sticky.pop(_STICKY_DOC, None)
    return Result.success("Camera auto sync off", stage="camera_auto_off")


def camera_is_auto_on() -> bool:
    try:
        return _STICKY_EVENT in _sticky()
    except Exception:
        return False


def camera_toggle_auto() -> Result:
    """開／關自動同步（按一下切換）。"""
    if camera_is_auto_on():
        return camera_auto_off()
    return camera_auto_on()
