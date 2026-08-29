# -*- coding: utf-8 -*-
"""Rhino 選取組件通道：目前選取 → models/R2O_Objects_時戳.usdz。"""
from __future__ import annotations

from typing import List

from foundation.atomic import atomic_publish_from_pending
from foundation.log import append_log
from foundation.paths import (
    config_root_for_document,
    ensure_config_layout,
    next_objects_path,
    pending_path_for,
    require_saved_document_path,
)
from foundation.pointer import write_current_project_pointer
from foundation.result import Result
from foundation.usdz_postprocess import (
    promote_material_bindings_usdz,
    validate_usdz_file,
)
from rhino.commands.models import (
    _export_selected_usdz,
    _restore_document,
    _snapshot_and_prepare,
)


def _selected_ids() -> List:
    import rhinoscriptsyntax as rs  # type: ignore

    try:
        ids = rs.SelectedObjects(include_lights=False, include_grips=False) or []
    except TypeError:
        ids = rs.SelectedObjects() or []
    except Exception:
        return []
    return list(ids)


def _resolve_root() -> Result:
    import scriptcontext as sc  # type: ignore

    doc = sc.doc
    path = getattr(doc, "Path", None) if doc else None
    saved = require_saved_document_path(path)
    if not saved.ok:
        return saved
    root = ensure_config_layout(config_root_for_document(saved.data))
    return Result.success(
        data={"root": root, "document": saved.data},
        stage="resolve_path",
    )


def publish_objects_once(*, interactive: bool = True) -> Result:
    """匯出目前選取為一份時戳 USDZ。沒選取＝擋住。不搬原點。"""
    import Rhino  # type: ignore
    import rhinoscriptsyntax as rs  # type: ignore

    target = _resolve_root()
    if not target.ok:
        return target
    root = target.data["root"]

    ids = _selected_ids()
    if not ids:
        return Result.blocked("Select objects to export first", stage="objects_select")

    doc = Rhino.RhinoDoc.ActiveDoc
    if not doc:
        return Result.fail("No active document", stage="publish_objects")

    try:
        final = next_objects_path(root)
    except RuntimeError as exc:
        return Result.fail(str(exc), stage="objects_name")
    pending = pending_path_for(final)

    snap = None
    rs.EnableRedraw(False)
    try:
        snap = _snapshot_and_prepare(doc, ids)
        exported = _export_selected_usdz(ids, pending)
        if not exported.ok:
            try:
                if pending.exists():
                    pending.unlink()
            except OSError:
                pass
            append_log(
                root,
                "Objects publish: {} ({})".format(exported.status, exported.message),
            )
            return exported

        promoted = promote_material_bindings_usdz(pending)
        if not promoted.ok:
            try:
                if pending.exists():
                    pending.unlink()
            except OSError:
                pass
            append_log(
                root,
                "Objects publish: {} ({})".format(promoted.status, promoted.message),
            )
            return promoted

        published = atomic_publish_from_pending(
            final, pending_path=pending, validate=validate_usdz_file
        )
        if published.ok:
            write_current_project_pointer(root, target.data["document"])
            published = Result.success(
                "Published {} selected object(s) → {}".format(len(ids), final),
                stage="publish_objects",
                data=str(final),
            )
        append_log(
            root,
            "Objects publish: {} ({}); count={}".format(
                published.status, published.message, len(ids)
            ),
        )
        return published
    except Exception as exc:
        try:
            if pending.exists():
                pending.unlink()
        except OSError:
            pass
        fail = Result.fail("Objects export failed: {}".format(exc), stage="publish_objects")
        append_log(root, "Objects publish: {} ({})".format(fail.status, fail.message))
        return fail
    finally:
        try:
            if snap is not None:
                _restore_document(doc, *snap)
        finally:
            rs.EnableRedraw(True)
